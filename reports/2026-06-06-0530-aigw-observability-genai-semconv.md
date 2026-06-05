---
title: "AI 网关可观测与监控专题 · GenAI SemConv 分叉与 token 维度精细化"
cron_id: aigw-observability-genai-semconv
generated_at_local: 2026-06-06 05:30 CST
generated_at_utc: 2026-06-06T05:30:00Z
topic_index: 5
---

# 可观测 & 监控 · GenAI SemConv 分叉 / token 维度精细化

> hour 5 触发 `observability` 主题（hour % 7 = 5）。核心观察：**OpenTelemetry GenAI 语义约定 5/5 完成从 `semantic-conventions` 仓库剥离、迁入独立 `semantic-conventions-genai` 仓库**（PR#3696），独立后 SIG 节奏明显加快——5/26–6/5 新仓 18 个 open PR 覆盖 token 维度、agent 协议（A2A/MCP）、多模态拆分。本报告聚焦：(1) semconv 分叉背景、(2) 5 月合入的六大 token/semantic 维度规范化、(3) 6 月新开草案、(4) 上游（openllmetry 0.61.0 / openlit 1.21.0 / Langfuse v3.178.0）落地。

## 1. GenAI SemConv 独立成仓（PR#3696, 5/5）

- **动作**：5/5 16:12 UTC lmokova 合入 [semantic-conventions#3696](https://github.com/open-telemetry/semantic-conventions/pull/3696)，新仓 [`semantic-conventions-genai`](https://github.com/open-telemetry/semantic-conventions-genai) 当下 52 ★、与原仓共生。
- **副效应**：[opentelemetry-python-contrib PR#4611](https://github.com/open-telemetry/opentelemetry-python-contrib/commit/a341399)（5/22）在 `instrumentation-genai/` 9 个子包 README 顶部加"contrib notice"指向新库——Anthropic、Claude Agent SDK、Google GenAI、LangChain、OpenAI Agents v2、OpenAI v2、VertexAI、Weaviate、util-genai 共 9 个 instrumentation 包将由新库托管。
- **节奏变化**：5/5 之前主仓 `#area:gen-ai` issue 大量 stale；独立后新仓 6/4–6/5 一周内 12 commit 全是 documentation/dashboard/MCP context 校准——**SIG 把"治理"前置了**。
- **Gateway 含义**：AIGW 自研 trace→OTel 出口时，**`gen_ai.*` 命名空间现在以 `semantic-conventions-genai` 为准**，旧主仓只承担 HTTP/DB/Network/RPC 等基础设施维度。

## 2. 5 月合入的六大 semconv 改动（已稳定）

| 维度 | 属性 | 合入 PR | 价值 |
|---|---|---|---|
| **Cache** | `gen_ai.token.cache` ∈ {read,creation,uncached} | [sc#3624](https://github.com/open-telemetry/semantic-conventions/issues/3624) 5/5 | Anthropic cache 三态统一可加性，**避免 sum 重叠** |
| **Reasoning** | `gen_ai.token.reasoning` (bool) | 同 #3624 | 单独标记 output 推理，**为 o-series / Gemini 2.5+ 推理计费分流** |
| **Workflow duration** | `gen_ai.client.operation.duration` workflow 适配 | [sc#3565](https://github.com/open-telemetry/semantic-conventions/issues/3565) 5/10 | 端到端多步骤 agent 时间 |
| **Multimodal** | `document` Modality + `byte_size` + `StrippedPart` | [sc#3673](https://github.com/open-telemetry/semantic-conventions/issues/3673) 5/11 | BFSI KYC PDF、redactor/fail-closed 可观察 |
| **Security guardian** | `apply_guardrail` span + finding event | [sc#3233](https://github.com/open-telemetry/semantic-conventions/issues/3233) 5/18 | Guardrail span 与 `chat`/`execute_tool` 平级、可链式 |
| **Memory ops** | `create_memory_store`/`search_memory`/`update_memory`/`delete_memory` | [sc#3250](https://github.com/open-telemetry/semantic-conventions/issues/3250) 5/11 | LangChain/LlamaIndex long-term memory |

**核心数据点**（PR#3624 body）："Modern providers report richer token data than just input vs output. Anthropic gives cache read/creation/uncached counts, OpenAI reports cached input and reasoning output tokens. Right now there's no way to capture this in the metric without losing additivity." → 修复要求 **emit partitioned data points that sum to the total**——**给 AIGW 的硬要求：不要发一行 total + 一行 cache 子集**，否则破坏 OTel aggregator 可加性。

## 3. 6 月新开草案（未合，影响 gateway 设计）

新仓 18 个 open PR 中关键四条：

- **[PR#197](https://github.com/open-telemetry/semantic-conventions-genai/pull/197)** `Add modality, cache, and phase breakdowns for token usage`（5/26）——把 `gen_ai.client.token.usage` histogram 拆为三 counter：
  - `gen_ai.client.inference.tokens`（按 `token.type` + `token.modality`）
  - `gen_ai.client.inference.input_tokens_by_cache`（按 `token.cache` + `token.modality`）
  - `gen_ai.client.inference.output_tokens_by_phase`（按 `token.phase`）
  - 新增 enum：`modality ∈ {text,image,audio,video,document,unknown}`、`cache ∈ {uncached,read,write}`、`phase ∈ {response,reasoning}`。**"Operators need to attribute spend and forecast capacity by the dimensions that actually drive cost"**。
- **[PR#195](https://github.com/open-telemetry/semantic-conventions-genai/pull/195)** `semconv for a2a protocol`（5/26）——A2A client/server span + protocol attr + streaming **time-to-first-event** + SSE event 计数。**"HTTP semantic conventions ... do not identify the A2A method, task state, context, streaming behavior, or task-level outcomes."** 对位 6/4 Kong 3.14 A2A 插件、agentgateway A2A 流量。
- **[PR#252](https://github.com/open-telemetry/semantic-conventions-genai/pull/252)** `Add gen_ai.invoke_agent.server span (SERVER kind)`（6/5）——与客户端 span 对偶，给远端 agent runtime 准备。
- **[PR#220](https://github.com/open-telemetry/semantic-conventions-genai/pull/220)** `Clarify MCP context propagation`（6/4 已合）——`docs/gen-ai/mcp.md` 显式推荐 W3C propagator，明确 `_meta` DNS 前缀是 trace context key 的豁免列表——**对应 `0410-aigw-guardrails-prompt-injection-middleware` 提到的 MCP 间接注入硬化**：context propagation 与反间接注入是同一个表面的两面。

## 4. 上游落地（5/14–6/5）

### 4.1 Langfuse v3.178.0（6/2）
- `feat(agent): Connect in-app agent to langfuse MCP`（[PR#13747](https://github.com/langfuse/langfuse/pull/13747)）——Langfuse agent 接 MCP，**trace 查询可被外部 agent 调用**，observability 从"被动 dashboard"推向"主动 agent surface"。
- `fix(security): enforce auditLogs:read`（[PR#13980](https://github.com/langfuse/langfuse/pull/13980)）——审计日志 batch export 需显式 entitlement。
- **5 月 cost/cache 关键 PR**：
  - [PR#13572](https://github.com/langfuse/langfuse/pull/13572)（5/14）"fix(otel): recognize OpenInference `llm.token_count.prompt_details.cache_read/cache_write`"——OpenInference 命名空间在 `extractGenericGenAiUsageDetails` 加白名单，归一化进 `input_cached_tokens` / `input_cache_creation`。**这是 cache 维度跨规范归一化的样板**。
  - [PR#13716](https://github.com/langfuse/langfuse/pull/13716)（5/21）"refactor(blob-export): gate pricing fields on model group, not usage"——blob export 的 pricing 字段基于 model group 而非 usage 计算。**说明 Langfuse 内部计费从"按 usage 计算"转"按 model group 锁价"**——给 AIGW 反向警示：cost 数据语义应**早绑 model group**。

### 4.2 Traceloop OpenLLMetry 0.61.0（5/31）
[Release 0.61.0](https://github.com/traceloop/openllmetry/releases/tag/0.61.0) 把 30+ 修复推到 instrumentation：
- **Cache/reasoning 落地**：`openai-agents` #4130 emit `cache_read.input_tokens` 与 `reasoning_tokens`；#4131 把 `response.instructions` 当 system prompt 入 generation span。
- **ERROR status 统一**：[#4101](https://github.com/traceloop/openllmetry/pull/4101) 一次性给 9 个 instrumentation（langchain/anthropic/groq/mistralai/bedrock/ollama/sagemaker/together）补 `record exceptions + set ERROR status`——**过去这些 SDK 异常时 span status 是 UNSET**。
- **GenAI semconv 合规**：[#3837](https://github.com/traceloop/openllmetry/pull/3837) `openai-agents` 切到 GenAI semconv；[#4103](https://github.com/traceloop/openllmetry/pull/4103) `mcp` 协议层 tool error 加 `error.type`——**MCP 协议层 error 第一次在 OTel 中标准化**。
- **exporter/processor 冲突**：[#4137](https://github.com/traceloop/openllmetry/pull/4137) SDK 启动 warn 双配——**OTel SDK 历史坑**：SpanExporter + SpanProcessor 同时配会双重处理。

### 4.3 OpenLIT 1.21.0（5/27）+ otel-gpu-collector 0.0.6（6/3）
[openlit 1.21.0](https://github.com/openlit/openlit/releases/tag/openlit-1.21.0) 主题：**闭环**——把"trace→分析→改 prompt"流程闭合。
- **PR#1185** "Support offline evals and remove LLM based evals"——线上 eval 不再调 LLM，**用规则/启发式离线跑**，eval 自身不再引入 cost + 延迟。
- PR#1187 guardrails logic、PR#1192 remote agent lifecycle、PR#1200 telemetry views、PR#1205 Otter trace 深链。
- **PR#1202** "Close the loop with AI analysis for traces, spans, and prompt improvement"——用 trace 反推 prompt 改进建议。
- [otel-gpu-collector 0.0.6](https://github.com/openlit/openlit/releases/tag/otel-gpu-collector-0.0.6)（6/3）——**OTel Collector 形态的 GPU telemetry**：5 天内 0.0.5→0.0.6，arm64 native build (#1252)、CGO for linux release (#1224)、arm64 eBPF bindings (#1213)——**LLM 推理侧 GPU 利用率可被 OTel 收集**，与 Langfuse 的"前端 OTel 化"对应，**OpenLIT 在做"GPU 端 OTel 化"**。

## 5. 给 AI 网关的四条建议

1. **Token metric 形态**：以 PR#3624 + PR#197 为目标——`gen_ai.client.inference.{input,output}_tokens` 走 counter，attribute 带 `gen_ai.token.{type,cache,phase,modality}`。**禁用 total+子集双发**。
2. **跨规范归一化层**：OpenInference 仍 emit `llm.token_count.prompt_details.cache_read`（[Arize-ai/openinference 6/5 一次性 7 个 fix PR #3208-#3214](https://github.com/Arize-ai/openinference/commits?per_page=8&since=2026-05-15T00:00:00Z)），AIGW 收到 OpenInference trace 也要在 ingestion 阶段做 cache 归一化（参考 Langfuse PR#13572）。
3. **MCP context propagation**：跟随新仓 PR#220 推荐 **W3C propagator** + `_meta` DNS 前缀豁免——自家 MCP 客户端把 trace context 注入到 MCP `_meta` 字段。
4. **A2A trace schema 前瞻**：新仓 PR#195 草案已就位。agentgateway 已有 A2A 流量（Kong 3.14 同日上 A2A 插件）——SDK 层先 emit `a2a.method` / `a2a.task.id` / `a2a.task.state` 私有 attribute，等 PR#195 合入后平滑切换。

## 6. 与前几轮呼应

- 04:50 guardrails-SLO 的"被拦要可观察"——本轮 PR#3233 `apply_guardrail` span 已经把 `gen_ai.guardian.{id,name,version,provider.name}` 全 attribute 化。
- 04:10 guardrails-middleware 的"MCP `getAgent` 字段过滤"——本轮 PR#220 把 MCP context propagation 规则化，trace context 不再静默丢失。
- 03:28 semantic-routing 的"模型层行为回归"——本轮 PR#3624 解决了"切换 model 时 token metric 命名空间变了导致成本对照失效"的部分痛点。

## 引用与数据来源

- OTel semconv 仓库迁移：https://github.com/open-telemetry/semantic-conventions/pull/3696
- 新仓：https://github.com/open-telemetry/semantic-conventions-genai
- 5 月合入 PR：https://github.com/open-telemetry/semantic-conventions/issues/3624, /3233, /3250, /3673, /3565, /3336
- 6 月新开 PR：https://github.com/open-telemetry/semantic-conventions-genai/pull/197, /195, /252, /220（已合）, /250, /242, /238
- 上游 release：https://github.com/openlit/openlit/releases/tag/openlit-1.21.0, /tag/otel-gpu-collector-0.0.6, https://github.com/traceloop/openllmetry/releases/tag/0.61.0, https://github.com/langfuse/langfuse/releases/tag/v3.178.0
- Langfuse cost/cache：https://github.com/langfuse/langfuse/pull/13572, /13716, /13980, /13747
- 关联 commit：https://github.com/open-telemetry/opentelemetry-python-contrib/commit/a341399, https://github.com/open-telemetry/semantic-conventions-genai/commit/c450371
