# AI 网关可观测与监控专题（2026-06-05 05:06）

> 本期主题：**可观测 & 监控**（cron 主题编号 h%7==5）
> 本次抓取时间：2026-06-05 05:06 (UTC+8, 本地 `date` 命令)
> 范围：Helicone、Langfuse、OpenLLMetry、OpenLIT、Portkey Gateway、OpenTelemetry GenAI Semantic Conventions

---

## TL;DR

- **市场层最大事件**：LLM 可观测赛道"老兵"Helicone **被 Mintlify 收购**，进入 maintenance 模式；Mintlify 想把"agent 调用的知识源"做成新护城河。
- **Langfuse v3.176 → v3.178（5-28 → 6-02）** 连续三周高密度迭代：MCP 服务化（metrics / scores / media / health 全部暴露给 MCP）、in-app agent API keys（短期 + 仅 MCP 范围）、audit log 权限收紧到 `auditLogs:read` 授权。
- **OpenLLMetry 0.61.0（5-31）** 全面对齐 OTel GenAI semconv：OpenAI Agents / Bedrock / Vector-DB / MCP / ChromaDB 等十余个 instrumentation 修复 ERROR span 状态、token 用量与 embeddings_count 归一化。
- **OpenLIT 1.21.0（5-27） + 1.21.1 + otel-gpu-collector 0.0.6（6-03）** 三件套：guardrails 改造、offline evals、Trace UI 重写，再加 GPU collector 走 OTel 协议收硬件 metrics。
- **OTel semconv 侧** 5 月动作密集：5-05 把 GenAI 规范搬到独立仓库（PR #3696）、5-18 `apply_guardrail` + finding event 落地、4-27 reasoning tokens attribute 进入 spec，v1.41.1 是当前最新 tag。
- **Portkey Gateway** 5-19 一波安全加固：去掉 admin token 默认值、给 public routes 加 auth 校验、provider options 在日志里 redact，5-11 把 request metadata 透传到 CrowdStrike AIDR。

---

## 1. Helicone → Mintlify：可观测赛道开始整合

来源：<https://www.helicone.ai/blog/joining-mintlify>（Cole Gottdank, 2026-03-03）

核心事实：

- Helicone 整个团队并入 Mintlify（YC W23 出身，三年累计 14.2 万亿 token、16,000 家组织、33M+ 终端用户，YC 公司中使用率第一）。
- 产品进入 **maintenance 模式**：安全更新、新模型、bug/perf 修复继续，但**不再有大版本新功能**。
- Mintlify 自身定位是"agent 调用的知识源"层 —— 收购 Helicone 的逻辑是"agents 行动时从哪里拉取，决定了它的能力上限"，可观测平台是 Mintlify 现成的高质量 AI 用户行为数据。

观察：

1. **对正在选 LLM observability 工具的团队**：Helicone 仍然可用、SDK 仍维护、计费不变，但长期演进路径已经断，新功能不会来。**新项目优先评估 Langfuse / OpenLIT / Arize Phoenix / Portkey logs**。
2. **对自建可观测体系**：Helicone 之前是"开箱即用 + 月费友好"的代表，少了这一档定位，**Portkey 的 logs 子模块 + Langfuse self-host** 现在覆盖了原 Helicone 的大部分场景。
3. **对收购方 Mintlify**：MCP 化、agent-native 的产品叙事是主轴，Helicone 的 OTel 兼容层大概率会被 Mintlify 文档平台消化。

> 注：Helicone 的 GitHub `releases` 接口自 2025-08-21 之后没有新 tag（v2025.08.21-1），但 `main` 分支 commit 持续到 2026-05-18，节奏与"maintenance mode"完全吻合。

---

## 2. Langfuse：MCP 服务化 + 审计收紧

源 release tags：v3.178.0（6-02）、v3.177.1（6-01）、v3.177.0（6-01）、v3.176.0（5-28）、v3.175.0（5-21）

### 2.1 v3.176（5-28）一次性补完 MCP 全栈

- `feat(mcp): Make metrics / scores / media / comments / datasets / annotation queues / health available via MCP`
- `feat(auth): In-app agent API keys` —— 这是与 v3.178 呼应的前置 PR
- `feat(dashboards): import/export widget configs`
- `feat(evals): code-based eval`（v3.176 起开始成型）
- `feat: initial FTS implementation`（ClickHouse 全文搜索）
- `feat(email): support AWS SES transport via default credential chain`
- `feat(ingestion): add app root detection`
- 安全 / 修正：`fix(tracing): sanitize external urls wholistically`、`fix(tool-calls): parse available tools and map them to input object`、`fix(mcp): inject root type: object so Tool.inputSchema satisfies MCP SDK`

### 2.2 v3.177（6-01）

- `LANGFUSE_DISABLE_LEGACY_TRACING_IO_SEARCH` 旗标，**v4 迁移开始给出逃生通道**（可以关掉 v3 表的 FTS）。
- `feat(ai): Add toggle for AI telemetry`（in-app agent 用，可以独立开关）。
- 文档警告：`docs(agents): warn against is_deleted filter on ClickHouse reads`。

### 2.3 v3.178（6-02）

- `feat(agent): Connect in-app agent to langfuse MCP`（PR #13747）—— **每个 agent session 创建一个 ephemeral project API key、只授权 MCP 端点 + 显式 `allowInAppAgentKey` 的工具、stream 结束立刻删**。这是非常干净的安全模式：临时、低权限、终态清理。代码细节包括 `withInAppAgentMcpApiKeyCleanup` 包装层 + 把 `closed / subscription / abortHandler` 提到外层 scope 让 `cancel()` 能对称清理。
- `feat(web): derive code eval support from dispatcher` + `feat(mcp): Add optional id to upsertDataset`
- **审计安全**：`fix(security): enforce auditLogs:read and audit-logs entitlement for audit_logs batch exports`（PR #13980）—— 之前 audit log 的 batch export 没校验权限。
- 数据访问：`refactor(comments): Make comment TRPC routes read from events table`（不再走老的注释表）
- 性能：`fix: route more queries to readonly pools`
- 后续补丁：`fix(datasets): Add callout for v4 if dataset run items are loading too long`

**对使用方的影响**：
- 选 Langfuse 做观测底座的产品，**MCP 自动成为一等公民** —— agent、metrics、scores、media、comments、datasets 都能从 Claude/Cursor 等 MCP 客户端直接查询，相当于把 Langfuse 自己的 UI 暴露成 MCP 工具。
- 审计 / 合规视角，`auditLogs:read` 权限成为强制，**之前"普通 token 能拉 audit logs" 的隐性越权被堵上**。
- v4 数据迁移已经在做（dataset 慢加载时会出现 v4 callout），自部署用户得开始评估 v4 schema。

---

## 3. OpenLLMetry 0.61.0（5-31）—— 全面对齐 OTel GenAI semconv

源：<https://github.com/traceloop/openllmetry/releases/tag/0.61.0>

要点（精简核心 Feat / Fix）：

- **新能力**
  - `sdk`: `use_legacy_attributes` 暴露到 `Traceloop.init()`（PR #4133）—— 旧属性 / 新属性可切换
  - `bedrock`: aioboto3 异步支持（#4135）
  - `openai-agents`: GenAI semconv 合规（#3837）
- **错误处理归一化**（一整批：#4101 / #4102）
  - `langchain, anthropic, groq, mistralai, bedrock, ollama, sagemaker, together` 在 span 失败时记录异常并把 status 设为 ERROR
  - 同样规则应用到 `chromadb, lancedb, weaviate, pinecone`
- **token / 计量修正**
  - `openai-agents`: emit `cache_read.input_tokens` 与 `reasoning_tokens`（#4130）
  - `openai-agents`: capture `response.instructions` 作为 system prompt（#4131）
  - `anthropic`: streaming 时 token usage 始终用 API 数据（#3949 / #3976）
- **Vector-DB 归一化**（#1870 / #4156）：Pinecone + Milvus 现在统一发 `embeddings_count / result_count / similarity` 属性。
- **MCP 协议层错误**（#4103）：tool 错误现在会写 `error.type` 属性。
- **SDK 工程性**
  - `chromadb`: 一个 query 多个 document → 每个 document 发一条 result event（#4105）
  - `langchain`: 处理 wrapt v1/v2 不兼容、`ToolNode` 在 `create_react_agent` 的 tool iteration（#4081 / #4082）
  - `openai`: 干掉冗余 try/finally、AsyncAPIResponse 缺 `.id` 时不再 crash（#4078 / #4080）
  - `anthropic`: 防止 streaming tool use delta handler 出现 KeyError/IndexError（#4079）
  - 替换已废弃的 Pydantic `.json()` / `.model_dump_json()`（#4098）
  - exporter + processor 同传时给 warning（#4137）
  - 评估器 PII detector 返回值加上 reason（#4026）

**意义**：OpenLLMetry 实际上是把 OTel GenAI semconv 落地到所有主流 SDK 的"翻译层"，v0.61 把"失败 span 也要正确标 ERROR"这种基础工程做扎实了 —— 之后做 SLO / alert 才有意义。

---

## 4. OpenLIT 1.21.x（5-27 → 5-28） + otel-gpu-collector

### 4.1 openlit-1.21.0（5-27）

- `feat: Support offline evals and remove LLM based evals`（#1185）—— **OpenLIT 明确转向"离线评估"**，不再把 LLM-based eval 当主路径（成本 + 决定性都更友好）。
- `feat: Update guardrails logic`（#1187）
- `feat: support remote agent lifecycle`（#1192）
- `Feat: Revamp telemetry data views and trace detail experience`（#1200）—— UI 重写
- `Feat: Close the loop with AI analysis for traces, spans, and prompt improvement`（#1202）—— 自动用 AI 给 trace 写注释 + 改 prompt

### 4.2 openlit-1.21.1（5-28）

- `chore added events for ai and otter`（#1206）—— 事件层扩张

### 4.3 otel-gpu-collector-0.0.6（6-03） / 0.0.5（6-02）

- `feat: Make otel-gpu-collector contributions easier`（#1228）
- `feat(python): add agent threat event helper`（#1204）—— 这是个"agent 威胁事件"的 Python 助手，与 OTel semconv 5-18 的 `apply_guardrail` + finding event 互相呼应

`ts-1.13.0`（5-08）加了 **Cursor SDK Instrumentation** —— Cursor 编辑器里的 LLM 调用现在能直接被 OpenLIT 收。

观察：OpenLIT 走的是"全场景覆盖"路线（UI + GPU + agent 威胁 + Cursor），而 Langfuse 在做"严肃的企业级"路线（MCP、v4、审计权限），两者差异越来越明显。

---

## 5. OpenTelemetry GenAI Semantic Conventions（5 月动态）

源：<https://github.com/open-telemetry/semantic-conventions> + PR 搜索

- **5-05 #3696** *Move GenAI semantic conventions to its own dedicated repository* —— **GenAI semconv 准备独立成仓**，但 PR 状态看还在推进中，5-20 有 "Invoke agent server span" closed PR、5-18 "gen-ai: add security guardian (apply_guardrail) span + finding event" closed PR、5-11 `[chore] Prepare release v1.42.0`。
- **4-27 #3383** *genai: define reasoning tokens attribute* —— **reasoning_tokens 作为 spec 级的属性落地**（这正好对应 OpenLLMetry 0.61 在 openai-agents 里 emit `reasoning_tokens`）。
- **5-11 #3378** *Add JSON Schema Definition for gen_ai.tool.definitions* —— tool 定义有了正式 JSON Schema 描述能力。
- **4-27 #3463** `[chore] Switch toc generation to doctoc` —— 文档工具栈切到 doctoc。
- **4-22 #3623** *error.type and exception.type MAY unwrap uninformative wrapper types* —— 错误属性语义修订。
- **4-18 #3607** *Adding client side streaming attributes for inference span* —— 流式推理 span 属性扩展。
- **4-03 PR** *Split `invoke_agent` into separate client and internal spans, and split attributes* —— `invoke_agent` 被拆成 client / internal 两段。
- **3-25 #3518** *Run cspell on docs* —— 拼写检查加进 CI。
- 当前 tag 最新是 **v1.41.1**（v1.42 准备中），最近一个月内未发版。

> 关注点：5-18 的 `apply_guardrail` + finding event 进了 gen-ai 规范后，guardrails 报告（命中规则、严重度、是否阻断）会通过标准 OTel 事件流暴露 —— 这意味着未来做"可观测 + guardrails"时可以复用同一根 trace，不必拼两套。

---

## 6. Portkey Gateway：安全补漏 + CrowdStrike AIDR 集成

源：<https://github.com/Portkey-AI/gateway> commits

- 5-19 一波安全 patch：
  - `remove admin token default`（默认移除）
  - `add auth validation for public routes`（PR #1657）
  - `disable logs when admin token not set`（无 admin token 时不写日志）
  - `redact provider options in logs`（provider options 在日志里 redact）
- 5-11 `feat: forward request metadata to CrowdStrike AIDR` —— 把请求 metadata 透传到 CrowdStrike AI Detection & Response 平台。
- 5-18 `feat: forward additional context to CrowdStrike AIDR`（PR #1642）

意义：Portkey 在 logs 路径上做了**默认安全**（redact + disable-when-no-auth + 显式 auth validation），给监管/合规场景一个比较干净的默认值。

---

## 7. 给"AI 网关 + 可观测"选型的一句话建议

- **要 OSS + 自部署 + 企业级**：Langfuse（v3.176+ 已 MCP 化） + OpenLLMetry 0.61 作为 SDK 插桩层。
- **要快、要省心、不在乎未来功能**：OpenLIT（一站式 UI + GPU + agent 威胁 + Cursor 覆盖）。
- **要 LLM 路由 + 日志 + Guardrails 一体**：Portkey（admin token 安全 + CrowdStrike AIDR 集成 + 提供商 redaction 是亮点）。
- **要看 LLM 路由的 vendor-side 日志**：Helicone 短期仍可用，但**新项目不建议把命脉压上去**。
- **想自己拼**：OTel Collector + OpenLLMetry 0.61 + Grafana / ClickHouse 看板，留意 GenAI semconv 1.42 的 `apply_guardrail` 与 reasoning_tokens。

---

## 引用与数据来源

- Helicone blog: <https://www.helicone.ai/blog/joining-mintlify>
- Helicone blog 列表: <https://www.helicone.ai/blog>
- Helicone repo commits: <https://github.com/Helicone/helicone/commits>
- Langfuse v3.178.0 release: <https://github.com/langfuse/langfuse/releases/tag/v3.178.0>
- Langfuse v3.177.1 / 3.177.0 / 3.176.0: <https://github.com/langfuse/langfuse/releases>
- Langfuse PR #13747 (in-app agent MCP): <https://github.com/langfuse/langfuse/pull/13747>
- Langfuse PR #13980 (audit log entitlement): <https://github.com/langfuse/langfuse/pull/13980>
- Langfuse changelog: <https://langfuse.com/changelog>
- OpenLLMetry 0.61.0 release: <https://github.com/traceloop/openllmetry/releases/tag/0.61.0>
- OpenLIT 1.21.0 release: <https://github.com/openlit/openlit/releases/tag/openlit-1.21.0>
- OpenLIT 1.21.1 release: <https://github.com/openlit/openlit/releases/tag/openlit-1.21.1>
- OpenLIT otel-gpu-collector 0.0.6: <https://github.com/openlit/openlit/releases/tag/otel-gpu-collector-0.0.6>
- OpenLIT ts-1.13.0 (Cursor SDK): <https://github.com/openlit/openlit/releases/tag/ts-1.13.0>
- OTel semconv repo: <https://github.com/open-telemetry/semantic-conventions>
- OTel semconv tags: <https://github.com/open-telemetry/semantic-conventions/tags>
- OTel semconv PR #3696 (GenAI 拆分): <https://github.com/open-telemetry/semantic-conventions/pull/3696>
- OTel semconv PR #3383 (reasoning tokens): <https://github.com/open-telemetry/semantic-conventions/pull/3383>
- Portkey Gateway repo: <https://github.com/Portkey-AI/gateway>
- Portkey Gateway commits: <https://github.com/Portkey-AI/gateway/commits>
- Portkey Gateway PR #1657 (auth validation): <https://github.com/Portkey-AI/gateway/pull/1657>
- Portkey docs 首页: <https://portkey.ai/docs>
