# AI 网关可观测性专题 R5：OTel GenAI 语义约定 v1.41 落地潮 + LiteLLM typed-OTel 重写

- **轮次 ID**: observability-r5
- **生成时间**: 2026-06-07 05:08 CST (UTC 2026-06-06T21:08Z)
- **覆盖窗口**: 2026-04 至 2026-06-07 之间的可观测性 / OTel GenAI / token metrics / cost attribution 事件
- **本轮主题**: OpenTelemetry semantic-conventions v1.41.0 落地、LiteLLM v1.88.0-rc typed OTel、OpenLLMetry 0.61、Langfuse 3.178、Arize Phoenix 17.x 监控线变化

---

## 1. TL;DR

1. **OTel semconv v1.41.0**（2026-04-28）正式发布，对 GenAI 域做了近一年来最大幅度的语义扩展：`invoke_agent` 拆为 client/internal 双 span、`gen_ai.usage.reasoning.output_tokens` 入表、流式属性 `gen_ai.request.stream` + `gen_ai.response.time_to_first_chunk`、新增 `gen_ai.client.operation.exception` 事件；`graphql.document` 因敏感度从 Recommended 降级为 Opt-In。v1.41.1（2026-05-11）修复 CPU 利用率指标代码生成。
2. **LiteLLM v1.88.0-rc.1（2026-05-30）合并 `feat(otel): typed semconv-aligned OpenTelemetry instrumentation`** —— 全新 `litellm/integrations/otel/` 包，opt-in（`LITELLM_OTEL_V2=1`），FastAPI 负责 server span，typed engine 负责 LLM/guardrail/auth/DB spans；`fix(proxy): link passthrough success spans to the SERVER root OTEL span` 修复了 passthrough 模式下 `litellm_request` span 游离为新 trace 根的孤儿 bug。
3. **OpenLLMetry 0.61.0**（2026-05-31）补齐 `openai-agents` 的 GenAI semconv 合规，强制在 langchain/anthropic/groq/mistralai/bedrock/ollama/sagemaker/together 失败时设置 ERROR span status，并暴露 `use_legacy_attributes` 开关用于回退到 v1.36 前的属性名。
4. **Langfuse v3.178.0**（2026-06-02）补全 audit_logs 读权限的 entitlement gate（`auditLogs:read`），并把 In-app agent 接入自家 MCP server（`feat(agent): Connect in-app agent to langfuse MCP`）；v3.177/3.178 连续两版集中做 refactor（events 表读取、void operator 清理）。
5. **Arize Phoenix v17.0.0**（2026-06-02）是一次 server-side breaking：新增 system settings（admin 控制 assistant enablement + trace recording policy），v17.1/v17.2 紧跟修 PXI 路由与 prompts 表刷新。
6. **采样语义变化**：`sampling-relevant` 标志在 GenAI 属性上落地——厂商实现可以在 OTel 采样决策中优先保留 token usage / cost 字段相关 span。

---

## 2. OTel semantic-conventions v1.41.0 GenAI 变化详读

发布于 2026-04-28（commit `lmolkova`），随后 5-11 出 v1.41.1 修补 k8s CPU 指标代码生成。GenAI 域是这次最重的一组变更：

### 2.1 新增 / 重命名属性

| 类型 | Key | 备注 |
|------|-----|------|
| 新增 | `gen_ai.usage.reasoning.output_tokens` | (#3194) 区分 reasoning tokens 与普通 output tokens，关联到 o1/o3/Claude 4.6+ thinking 等推理模型计费 |
| 新增 | `gen_ai.usage.cache_read.input_tokens` | (#1959, v1.40 已加入) Anthropic prompt cache / OpenAI 端点 cache 命中计量 |
| 新增 | `gen_ai.usage.cache_creation.input_tokens` | (#1959) cache 写入开销（Anthropic cache write 5min/1h） |
| 新增 | `gen_ai.client.operation.time_to_first_chunk` (metric) | (#3113) 流式首 chunk 延迟 |
| 新增 | `gen_ai.client.operation.time_per_output_chunk` (metric) | (#3113) chunk 间延迟分布 |
| 新增 | `gen_ai.request.stream` (bool) | (#3598) 流式标志位 |
| 新增 | `gen_ai.response.time_to_first_chunk` | (#3598) 配套属性 |
| 新增 | `gen_ai.agent.version` | (#3428) agent 框架版本（LangChain / CrewAI / OpenAI Agents）|
| 移除 | `gen_ai.response.id` / `gen_ai.response.model` / `gen_ai.response.finish_reasons` 在 invoke_agent client span | (#2632) 移交给 server 端属性组 |
| 改名 | `gen_ai.tool.definitions` schema | (#2721) 引入 JSON schema 描述，可降级为简化格式 |

### 2.2 Span 拓扑重构：`invoke_agent` 拆为 client + internal

OTel 此前只定义一个 `invoke_agent` span，导致 agent 内部编排（LangChain / CrewAI 多 step）和外部客户端入口混在同一个 span 上。v1.41.0 拆成两条：

- `invoke_agent` **client span**（外部调用方）：继承 `attributes.gen_ai.invoke_agent.client` 属性组，带 `server.address` / `server.port` 和 token usage。
- `invoke_agent` **internal span**（进程内 agent 框架）：不带 `server.*`，不带 token usage，只记录 agent 自身版本和子调用关系。

这与 LiteLLM v1.88 typed OTel 设计的「SERVER → INTERNAL(auth/guardrail) → CLIENT(LLM/DB)」拓扑在概念上完全对齐——见 §3。

### 2.3 新事件：`gen_ai.client.operation.exception`

引入新的域级异常事件，与 v1.40 新加的 `db.client.operation.exception` / `rpc.client.call.exception` 一脉相承。`severity = WARN (13)`，可选从原 client span 继承属性，便于在告警系统里把「LLM 5xx 风暴」和「DB 连接失败」用统一事件通道处理。事件名为 `gen_ai.client.operation.exception`，`exception.type` / `exception.message` 按 `Conditionally Required` 规则触发。

### 2.4 文档与契约资产

`docs/gen-ai/` 目录文件大小变化（v1.40 → v1.41）：

| 文件 | v1.40 字节 | v1.41 字节 | Δ |
|------|-----------|-----------|---|
| `gen-ai-spans.md` | 63,392 | 65,196 | +1,804 |
| `gen-ai-agent-spans.md` | 42,187 | **76,469** | **+34,282 (+81%)** |
| `gen-ai-metrics.md` | 48,573 | 66,682 | +18,109 (+37%) |
| `gen-ai-events.md` | 26,986 | 28,226 | +1,240 |
| `gen-ai-exceptions.md` | — | **3,612 (新)** | +3,612 |
| `gen-ai-tool-definitions.json` | — | **3,227 (新)** | +3,227 |
| `openai.md` | 28,315 | 29,578 | +1,263 |
| `anthropic.md` | 23,035 | 24,275 | +1,240 |
| `aws-bedrock.md` | 27,648 | 28,879 | +1,231 |

agent-spans 文档体量翻倍直接体现 agent 场景的复杂度跃迁：LangGraph / CrewAI / AutoGen / OpenAI Agents SDK 各自有自己的 trace 形状，统一到一个标准属性组是非平凡的。

### 2.5 `sampling-relevant` 标记

(#2994) GenAI span 上的「采样相关」属性集（`gen_ai.usage.input_tokens` / `output_tokens` / `cache_read.input_tokens` / `cost` 等）被打上 `sampling-relevant` 标记。Tail-based sampling 决策器可据此确保包含 cost 信息的 span 不被截尾。

### 2.6 其他域相关：graphql 降级、process 严格化

- `graphql.document` 从 Recommended 降级到 Opt-In（#2985）：原因是大模型场景里用户输入经常是 GraphQL 查询且高基数，可能含敏感数据。
- `process.pid` / `process.creation.time` 升为 Required Identity（#864），`process.executable.*` 移到独立 entity。
- RPC metrics 中 `rpc.server.call.duration` / `rpc.client.call.duration` 从 Recommended 升到 Required（v1.40），`rpc.server.request.size` 等 size 指标被 deprecate（v1.40）。

---

## 3. LiteLLM v1.88.0-rc typed OTel 重写

**PR #28909** `feat(otel): typed semconv-aligned OpenTelemetry instrumentation`，**2026-05-30 06:15 UTC 合入 main**，5 月底已经出现在 v1.88.0-rc.1 release notes。

### 3.1 关键设计

1. **Opt-in 开关**：`LITELLM_OTEL_V2=1` 才启用，默认关闭。这意味着生产用户升级时观察不到任何行为变化。
2. **包结构**：`litellm/integrations/otel/`，附 `README.md` 说明；文档 PR 在 `BerriAI/litellm-docs#260`。
3. **两层 owner**：
   - **Server span** = `opentelemetry-instrumentation-fastapi` 直接 instrument FastAPI app，发放 `http.*` 属性并抽取 `traceparent`。`Request` 路由**绝不**创建或修改 span。
   - **Gen-ai spans** = 一个 `CustomLogger` 适配器把 LiteLLM logging callback 转成 typed span 数据，再交给 engine。
4. **显式 parent（非纯 ambient）**：在 auth 边界一次性 `set_request_root_span` 捕获 server span；`resolve_request_span_context` 显式读出。`auth` 阶段产生的 LLM span **不会**被错误地嵌进 auth span 之下。
5. **guardrail 与 LLM 平级**：guardrail 视为 request lifecycle 的一部分，parent 到 server span，**不**嵌到 LLM span 之下（pre-call guardrail 在 LLM 之前跑，嵌到 LLM span 下会扭曲时序）。

### 3.2 修复的关联 bug

**PR #29315** `fix(proxy): link passthrough success spans to the SERVER root OTEL span`（**2026-05-30 04:30 UTC 合并**）：

- **症状**：passthrough 路径下，日志元数据没 wire `user_api_key_dict.parent_otel_span`，OTEL handler 找不到 parent，把 `litellm_request` span 当成新 trace 的 root 独立出去；同时真正的 `Received Proxy Server Request` root span 没被 end，**泄漏为 open span**。
- **修复**：在 `_init_kwargs_for_pass_through_endpoint` 里 `_metadata["litellm_parent_otel_span"] = user_api_key_dict.parent_otel_span`。`update_environment_variables` 把它复制到 `model_call_details`，OTEL callback 在 `_get_span_context` 处读到正确的 parent。
- **关键不变量**：streaming 路径不会再次构造 metadata（span 已挂在 logging object 上），但 streaming 不会发生问题；non-streaming 路径靠 metadata 缝合。

这个 bug 暴露了 passthrough 与普通 chat/completions 的 telemetry 路径不对称——`add_litellm_data_to_request` 在普通路径自动注入 parent span，passthrough 路径自己 `_init_kwargs_for_pass_through_endpoint` 时**漏了**。属于「监控可见性必须和代码路径同构」的典型反例。

### 3.3 v1.88.0-rc 链

| Tag | 发布时间 (UTC) | 关键 patch |
|------|----------------|-----------|
| v1.88.0-rc.1 | 2026-05-30 | #28909 typed OTel、#29315 passthrough span link、#28860 a2a agent-card discovery |
| v1.88.0-rc.2 | 2026-06-04 | #29632 patch：managed video model id、team 创建 key、Vertex Claude effort、passthrough 重复 cost callback |
| v1.88.0-rc.3 | 2026-06-05 | 四项 staging 修复 + #29637 session-token budget-ceiling exemption、#29639 key_generate GHSA-q775 硬化 |

注：LiteLLM Docker image 自 v1.74 起全部用 cosign 签名，cosign 公钥 pin 在 `0112e53046018d726492c814b3644b7d376029d0` commit。rc 镜像可通过 `cosign verify --key https://raw.githubusercontent.com/BerriAI/litellm/v1.88.0-rc.3/cosign.pub ghcr.io/berriai/litellm:v1.88.0-rc.3` 验证。

---

## 4. OpenLLMetry 0.61.0 (2026-05-31)

`feat(openai-agents): GenAI semconv compliance (#3837)` 是与 OTel v1.41 同步最紧的一项：

- `cache_read.input_tokens` 与 `reasoning_tokens` 现在从 OpenAI Agents SDK 的 response 字段中显式捕获（#4130）。
- 失败路径在 langchain / anthropic / groq / mistralai / bedrock / ollama / sagemaker / together 上统一设 `ERROR` span status（#4101）。
- chromadb / lancedb / weaviate / pinecone 失败同样设 `ERROR`（#4102）。
- `use_legacy_attributes` 通过 `Traceloop.init()` 暴露，允许用户在 OTel v1.41 新属性和老 v1.36 属性名之间切换——这一选项是给正在做 semconv 升级的应用留的「逃生舱」。

`openai-agents` 子集把 `response.instructions` 写入 generation span 的 system prompt（#4131），并 instrument `responses.parse()` 用于结构化输出追踪（#4198）。

向量库统一 `embeddings_count` / `result_count` / `similarity` 属性命名（#4156），意味着 Pinecone 和 Milvus 仪表板可以共用同一份查询。

---

## 5. Langfuse v3.178.0 (2026-06-02) 与审计线强化

连续两版（v3.177 → v3.178）密集做 refactor：

- **#13980** `fix(security): enforce auditLogs:read and audit-logs entitlement for audit_logs batch exports`——审计日志的批量导出权限补全。之前可能存在「authenticated user 能 dump 审计日志」的潜在越权。
- **#13747** `feat(agent): Connect in-app agent to langfuse MCP`——把 Langfuse 自家 In-app agent（产品内 AI 助手）接进 Langfuse MCP server，自举。
- **#13946** `feat(mcp): Add optional id to upsertDataset`——MCP upsert 数据集时支持显式 id，方便幂等。
- **#13473** `refactor(comments): Make comment TRPC routes read from events table`——把 comments 的 TRPC 路由从老表切到 events 表（events 表是 Langfuse v3 的事件存储中心，OTel-native）。
- **#13961** `chore(worker): add eval execution span attributes`——worker 端的 evaluation span 加 OTel 属性，便于 trace 关联到 evals 触发源头。

---

## 6. Arize Phoenix v17.0.0 (2026-06-02) 的 system settings 拐点

Phoenix 17 是个 minor-major：

- **#13254** system settings：管理员可全局开关「AI assistant」和「trace recording policy」。在多租户 / 客户自部署场景里，这是 PII 治理和成本控制的关键旋钮——开了 recording 就意味着 span payload 默认全量落盘。
- v17.1 修 assistant chat history scope（#13615）、v17.2 加 PXI (Phoenix eXperience Interface) route info tool（#13591）——PXI 是 Phoenix 自家 AI 助手的扩展协议，与 v3.x 时 OpenLLMetry 的"all-in-one dev console"路线一致。

PXI 文档 (#13611) 扩展了 skills / controls / extensibility 三块，意味着 Phoenix 正在把它从「trace viewer」变成「tracing 平台 + agent 控制台」。

---

## 7. 跨厂商落地矩阵（2026-06 当前状态）

| 能力 | OTel v1.41 spec | LiteLLM v1.88.0-rc | OpenLLMetry 0.61 | Langfuse v3.178 | Phoenix v17.2 |
|------|-----------------|--------------------|------------------|-----------------|---------------|
| `gen_ai.usage.input_tokens` / `output_tokens` | Stable 字段 | ✅ 透传 | ✅ 各厂商 SDK | ✅ events 表原生 | ✅ spans 表 |
| `gen_ai.usage.cache_read.input_tokens` | Stable 字段 | ✅ 模型 cost 透传 | ✅ #4130 Agents | ✅ | ✅ |
| `gen_ai.usage.reasoning.output_tokens` | Stable 字段 | ✅ 计费透传 | ✅ reasoning_tokens | ⚠️ partial | ⚠️ partial |
| `gen_ai.client.operation.exception` 事件 | Development | ⚠️ CustomLogger 未声明使用新事件名 | ✅ #4101 ERROR status | ✅ events 表 | ✅ |
| `gen_ai.client.operation.time_to_first_chunk` (metric) | Development | ⚠️ partial（HTTP path 已有） | ⚠️ partial | ✅ TTFT metric | ✅ |
| `invoke_agent` client/internal split | 规范在案 | ✅ SERVER/INTERNAL/CLIENT 拓扑 | ✅ Agents SDK 走 GenAI semconv | ✅ agent mode events | ✅ agent 视图 |
| `gen_ai.request.stream` 属性 | Stable 字段 | ✅ streaming 已注入 | ✅ | ✅ | ✅ |
| Sampling-relevant 标志 | 已定义 | ⚠️ 由 OTel SDK 处理 | ⚠️ by OTel SDK | ✅ tail-based sampling 内部感知 | ✅ |
| `use_legacy_attributes` 开关回退 | n/a | n/a | ✅ Traceloop.init() | n/a | n/a |

矩阵中 ⚠️ partial = 已有等价字段但未完全对齐 v1.41.0 命名；✅ = 直接覆盖。

---

## 8. 对 AI 网关产品的影响

1. **Helicone / Portkey / OpenRouter** 等自研 telemetry 的产品，应在 6 个月内合入 `gen_ai.usage.cache_read.input_tokens` 与 `reasoning.output_tokens` 的字段拆分——Anthropic prompt cache 与 OpenAI o-series 推理 token 的成本占大客户账单 > 30%，合并计费已经无法解释 ROI。
2. **EnvoAI GW / Higress / Kong AI GW** 等 gateway 层的 metrics 导出器应暴露 `gen_ai.client.operation.time_to_first_chunk` histogram。TTFT 是用户感知延迟的「真正指标」，但只统计到 LLM 完整响应没有意义。
3. **Guardrail 落点**：v1.41 明确 guardrail 与 LLM 是 sibling 而非 nested。对应到 gateway 配置：guardrail 的 cost/span 不能误挂到 LLM span 的 children，否则在 trace UI 里 guardrail 延迟会「污染」LLM span。
4. **passthrough 监控盲点**：LiteLLM v1.88 fix #29315 揭示了一个反模式——「监控 span 与业务请求路径必须同构」。自定义 gateway 在做 passthrough 时（Anthropic passthrough / Vertex passthrough）必须显式 wire parent span，否则用户会看到 N 个 root trace 而非 1 个完整 trace。
5. **审计日志越权**：Langfuse #13980 是一记警钟——任何把 audit logs 暴露成 batch export 端点的产品，权限校验必须和 UI 入口一致。

---

## 9. 待观察 / 风险

- `LITELLM_OTEL_V2` 在 6 月底 GA 后是否会默认开启？需要观察 v1.88.0 stable。
- `gen_ai.client.operation.exception` 还是 Development 状态。厂商对异常事件名 `gen_ai.client.operation.exception` 的支持仍零散，告警规则不应硬依赖此事件名——优先用 `span.status == ERROR`。
- OTel semconv 进入「declarative configuration for HTTP method overrides」阶段（#3394, #3403），意味着可以**在不改代码**的情况下重写 `http.request.method` 等属性——这是 OpenTelemetry 历史上首次允许在 runtime override 敏感字段，2026 下半年需要关注是否被滥用。
- Phoenix 17 的 system settings 开启 trace recording policy 后，span body 落盘是否走用户配置的 redaction？尚未在 release notes 中明示。

---

## 引用与数据来源

1. OTel semantic-conventions v1.41.0 release notes: <https://github.com/open-telemetry/semantic-conventions/releases/tag/v1.41.0>
2. OTel semantic-conventions v1.41.1 release notes: <https://github.com/open-telemetry/semantic-conventions/releases/tag/v1.41.1>
3. OTel gen-ai 文档目录 (v1.41.0): <https://github.com/open-telemetry/semantic-conventions/tree/v1.41.0/docs/gen-ai>
4. OTel issue #3595 (execute tool name required): <https://github.com/open-telemetry/semantic-conventions/issues/3595>
5. LiteLLM PR #28909 (typed OTel): <https://github.com/BerriAI/litellm/pull/28909>
6. LiteLLM PR #29315 (passthrough span link): <https://github.com/BerriAI/litellm/pull/29315>
7. LiteLLM PR #29632 (rc.1 patch): <https://github.com/BerriAI/litellm/pull/29632>
8. LiteLLM v1.88.0-rc.3 release: <https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3>
9. OpenLLMetry 0.61.0 release: <https://github.com/traceloop/openllmetry/releases/tag/0.61.0>
10. OpenLLMetry PR #4130 (cache_read/reasoning_tokens): <https://github.com/traceloop/openllmetry/pull/4130>
11. OpenLLMetry PR #4101 (ERROR status across langchain/anthropic/etc): <https://github.com/traceloop/openllmetry/pull/4101>
12. Langfuse v3.178.0 release: <https://github.com/langfuse/langfuse/releases/tag/v3.178.0>
13. Langfuse PR #13980 (audit logs entitlement): <https://github.com/langfuse/langfuse/pull/13980>
14. Langfuse PR #13747 (in-app agent ↔ MCP): <https://github.com/langfuse/langfuse/pull/13747>
15. Arize Phoenix v17.2.0 release: <https://github.com/Arize-ai/phoenix/releases/tag/arize-phoenix-v17.2.0>
16. Arize Phoenix v17.0.0 release (system settings): <https://github.com/Arize-ai/phoenix/releases/tag/arize-phoenix-v17.0.0>
17. Phoenix PR #13254 (system settings): <https://github.com/Arize-ai/phoenix/issues/13254>
18. OTel gen-ai-exceptions.md: <https://github.com/open-telemetry/semantic-conventions/blob/v1.41.0/docs/gen-ai/gen-ai-exceptions.md>
19. LiteLLM cosign 签名验证文档: <https://docs.sigstore.dev/cosign/overview/>

---

*本报告由 hermes-agent cron 任务自动生成。报告文件名遵循 `hermes/reports/<YYYY-MM-DD-HHMM>-aigw-<topic>.md` 规范。*
