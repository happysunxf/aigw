---
title: "AI 网关可观测性专题 R6：semconv-genai 18+ open PR 深读 + Cohere billed_units + agent.id 收窄"
cron_id: aigw-observability-r6
generated_at_local: 2026-06-07 05:43 CST
generated_at_utc: 2026-06-07T05:43:00Z
topic_index: 5
hour_mod7: 5
status: complete
---

# 可观测 & 监控 R6 · semconv-genai 18+ open PR 深读 + 上游收尾

> hour 5 触发 `observability` 主题（hour % 7 = 5）。R5 401 push 失败留 PENDING，本轮 token 仍 401 → 不重试 r5。
> 覆盖窗口 **2026-05-26 ~ 2026-06-07**。重点是 [semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) 自 5/5 独立以来累计 **18+ open PR** 的**逐条详细解读**（R3/R4/R5 只列 ID）。

## 1. 整体观察

- **6/3-6/5 集中合入 5 条**（r3 已记）→ **6/5 23:41-6/6 18:53 UTC 三批推送**：
  - [#144 BlobPart `stripped_reason`](https://github.com/open-telemetry/semantic-conventions-genai/pull/144) 6/6 00:41（+84/-7/4 files）
  - [#238 `gen_ai.agent.finish_reason`](https://github.com/open-telemetry/semantic-conventions-genai/pull/238) 6/6 06:33（+573/-120/14）
  - [#258 `gen_ai.request.reasoning_effort`](https://github.com/open-telemetry/semantic-conventions-genai/pull/258) 6/6 18:53（+462/-216/16）
- **6/5 18:01-23:41** 三个 closed 全是仓库治理（`#226` Jupyter→Python / `#256` Slack user map / `#255` PR dashboard）—— **SIG 6/5 收尾后 6/6 全力推信号设计 PR**。
- **18 open PR 5/26-6/6 集中，6/6-6/7 0 新开** —— 进 freeze 状态等 review。

## 2. 18 open PR 详细解读

### 2.1 [#197 token usage 拆三 counter（+14060/-6971/27 files，5/26）](https://github.com/open-telemetry/semantic-conventions-genai/pull/197)
- **拆三 counter**：
  - `gen_ai.client.inference.tokens`（按 `gen_ai.token.type` × `gen_ai.token.modality`）
  - `gen_ai.client.inference.input_tokens_by_cache`（按 `gen_ai.token.cache` × `gen_ai.token.modality`）
  - `gen_ai.client.inference.output_tokens_by_phase`（按 `gen_ai.token.phase`）
- **新 enum**：`modality ∈ {text, image, audio, video, document, unknown}` / `cache ∈ {uncached, read, write}` / `phase ∈ {response, reasoning}`
- **正文金句**：「image/audio tokens often cost more than text, cache hits (cached input is billed at a discount), and reasoning output (priced separately from response output on o-series and Gemini 2.5+)」。
- **Resolves** `#23 / #76 / #96` —— 三个 issue 集中爆破，**Modality+Cache+Phase 三正交维度就是这三个 issue 各自的呼声**。

### 2.2 [#258 `gen_ai.request.reasoning_effort`（+462/-216/16 files，6/6 18:53）](https://github.com/open-telemetry/semantic-conventions-genai/pull/258)
- **请求侧 effort 等级**，与 R5 v1.41.0 已稳定的 `gen_ai.usage.reasoning.output_tokens`（使用侧）配对。
- **三家概念对齐**（PR body table）：
  - OpenAI `reasoning.effort`: `low/medium/high`
  - Google Gemini `thinking_level`: `minimal/low/medium/high`
  - Anthropic `effort`: `low/medium/high`
- **设计决策**：**free-form string** 不强制 enum，**保留** `"xhigh"` / `"max"` / 厂商私有值。

### 2.3 [#238 `gen_ai.agent.finish_reason`（+573/-120/14 files，6/6 06:33）](https://github.com/open-telemetry/semantic-conventions-genai/pull/238)
- **三值 enum（open）**：`completed` / `max_iterations` / `guardrail`。
- **与 `gen_ai.response.finish_reasons` 对偶** —— 后者只解释单次 completion 停止原因，本 PR 给 agent loop 级别解释。
- **SDK 实证**：openai-agents 0.14.1 `MaxTurnsExceeded` / `InputGuardrailTripwireTriggered` / `OutputGuardrailTripwireTriggered`。
- **注册表文本 vendor-neutral**（无 SDK 名 / 文件路径）—— **SDK 实证只作 review context**。

### 2.4 [#202 `gen_ai.agent.{request,response}.size`（+361/0/4 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/202)
- **两个 Histogram `By`**：字节级入参 / 字节级出参，维度 `gen_ai.agent.name` + `gen_ai.agent.version`。
- **金句**：「token counts are also a poor proxy for the actual bytes-on-wire that the agent processes」—— multimodal agent 尤其重要。
- **与 #197 配合**：`#197` 是 model-side token 维度（model span），`#202` 是 agent-side 字节维度（agent span）—— **两层抽象不可互相替代**。

### 2.5 [#203 `gen_ai.workflow.steps`（+273/0/4 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/203)
- **Histogram `{step}`**，维度 `gen_ai.workflow.name`，**当设了 `gen_ai.agent.name` 时必须只数该 agent 归因的 step**（显式 exclude sub-agents + parent workflow events）。
- **「step」是 framework-defined**：ADK 的 tool call/result/response = 1 step；LangGraph 的 node execution = 1 step。

### 2.6 [#190 `gen_ai.context.selection.evaluated` event（+469/-54/11 files，**实验性**）](https://github.com/open-telemetry/semantic-conventions-genai/pull/190)
- **Resolves #181** —— "agent 在知道哪个 context 决策相关前是不是 load 太多 context？"
- **counts-only 隐私保留**：candidate / selected / suppressed / delivered-context hash count / low-cardinality reason。
- **显式不做**：raw prompt / context text / tool outputs / memory bodies / repo excerpts。
- **与 #144 BlobPart `stripped_reason` 同一脉络的 fail-closed observability**。

### 2.7 [#144 BlobPart `stripped_reason`（+84/-7/4 files，6/6 00:41）](https://github.com/open-telemetry/semantic-conventions-genai/pull/144)
- `BlobPart.content` 变 optional，加 `stripped_reason: string` optional。
- **fail-closed 约束**：top-level `anyOf` 强制 **content XOR stripped_reason** 至少一个非空。
- **Scope 收窄**：只 scope 到 `gen_ai.input.messages` 的 `BlobPart`；**后续路线** 复制到 `FilePart` / `UriPart`（参考 #143）→ `gen_ai.output.messages` / `gen_ai.system_instructions`。

### 2.8 [#211 Cohere `billed_units` 优先（+383/-154/12 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/211)
- **Resolves #13**（开了 13 个月以上）—— Cohere 上报 `usage.tokens`（model-consumed）与 `usage.billed_units`（customer-billed）两套。
- **改动**：`gen_ai.usage.input_tokens` / `output_tokens` 加 note："instrumentation SHOULD report the billed count when a provider reports both"；Cohere reference scenario 改用 `billed_units`。
- **AIGW 含义**：**必须把 `billed_units` 写进 usage**，否则客户实付与 gateway 报账裂痕。

### 2.9 [#242 `gen_ai.agent.id` 收窄（+404/-259/13 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/242)
- **核心改动**：`gen_ai.agent.id` **从 internal span 移除**；brief 改要求 **stable id**。
- **两类 agent 矛盾**：
  - **Hosted agent**（Bedrock / GCP / Azure / Claude / OpenAI Assistants）`agent.id` 是**创建时分配的 stable 标识**，**标识一组 setting 与 config**
  - **Framework agent**（crewAI）默认 GUID = **high-cardinality id**、**完全不同概念**
- **决议**：**drop framework agent.id** —— stable id 走 metrics 维度（hosting 端 resource / 客户端显式 attribute）。
- **铺垫** [Issue #243](https://github.com/open-telemetry/semantic-conventions-genai/issues/243)：同一 telemetry item 上同时记录"当前 agent"与"将要被它 invoke 的 agent"。

### 2.10 [#185 `gen_ai.operation.name: "evaluation"` + `gen_ai.evaluate.internal` span（+60/0/2 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/185)
- **Closes** [semantic-conventions#3398](https://github.com/open-telemetry/semantic-conventions/issues/3398)。
- **两具体问题**：
  1. **Dashboard 不可见** —— evaluation span 之前没法按 `gen_ai.operation.name` 过滤
  2. **生态碎片化** —— [OpenSearch genai-observability-sdk-py](https://github.com/opensearch-project/opensearch-genai-observability-py) 已自定义 `"evaluation"`
- **改动**：`registry.yaml` 加 `evaluation` enum；新 span `gen_ai.evaluate.internal`。

### 2.11 [#250 `gen_ai.agent.invocation.id`（+147/-79/13 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/250)
- **新 attribute**，加入 `invoke_agent.common`（`recommended: when available`），**同时覆盖 client 和 internal invoke_agent span**。
- **关键区分**：
  - `gen_ai.agent.invocation.id` —— **run-level**（agent 一次 invocation 整体）
  - `gen_ai.response.id` —— **completion-level**（单次 LLM call）
- **Reference scenarios**：AWS Bedrock Agents `ResponseMetadata.RequestId` / OpenAI Assistants `run.id` / Azure AI Foundry `response.id`。
- **Capture gap 明写**：**OpenAI Agents SDK 无独立 run ID**。

### 2.12 [#195 A2A semconv（+20375/-9295/21 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/195)
- **Fixes #70**。
- **A2A client + server spans + protocol attr**；**4 metric**：operation duration / response body size / streaming time to first event / SSE event count。
- **6 低基数 attr**：`a2a.method.name` / `a2a.protocol.version` / `a2a.task.state` / ……
- **Reference scenario**：`a2a-sdk==1.0.3` Python 包。

### 2.13 [#179 prompt versioning + variable support（+1398/-224/19 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/179)
- **Related** [#137](https://github.com/open-telemetry/semantic-conventions-genai/issues/137)。
- 19 文件量大；prompt versioned identifier + template variables。

### 2.14 [#257 `gen_ai.system_instructions` text-only（+15/-391/3 files）](https://github.com/open-telemetry/semantic-conventions-genai/pull/257)
- **Follow up to #226**（Jupyter→Python + JSON CI）。
- **金句**：「None of the model providers support non-text parts」（system instructions 限 text-only）。

### 2.15 其它（ID-level）
- `#252` `invoke_agent.server`（SERVER kind，与 client/internal 三件套配齐）
- `#162` `gen_ai.conversation.compacted` + `CompactionPart`（仅 scope inference span）
- `#98` handoff → `execute_tool`（openai-agents 建模）
- `#220` MCP context propagation 文字定稿（已 merge）

## 3. 上游收尾（6/5-6/7）

### 3.1 Langfuse
- **[#13623 V4 self-hosted historic backfill chain](https://github.com/langfuse/langfuse/pull/13623)**（+1659/-3022/97 files，6/5 合入）—— **五步后台迁移 M1-M5**：
  - **M1** 从 traces 创建虚拟 root span
  - **M2** observations 重写到 sort-key 优化 scratch table
  - **M3** scratch table JOIN live traces，写 child span 到 `events_full`
  - **M4** 通过 DRI cursor pagination 丰富 experiment-tagged span
  - **M5** v4 path 健康后 DROP scratch table
  - **envGate 机制**：`BackgroundMigrationManager` 用 active gate env var 过滤 Prisma query，**dormant gated row 不会 head-of-line block ungated migration**。
  - **V4 write-mode flags**：`LANGFUSE_MIGRATION_V4_WRITE_MODE` + `LANGFUSE_MIGRATION_V4_NATIVE_OTEL_BEHAVIOUR` 控制写目的地，**boot-time validation 拒绝不合法组合**。
  - **Greptile confidence 3/5** —— dormant opt-in，M3 query bug 暂不影响 live traffic，**但任何激活 gate 的 self-hoster 都会 M3 fail**。
- **6/5 同步 4 大 v3 scores API 阶段**（[#13995](https://github.com/langfuse/langfuse/pull/13995) Phase 1 polymorphic value flag-gated → [#13996](https://github.com/langfuse/langfuse/pull/13996) Phase 2 cursor tuple → [#14001](https://github.com/langfuse/langfuse/pull/14001) Phase 3 field groups → [#14005](https://github.com/langfuse/langfuse/pull/14005) Phase 4 filter params）。
- **[#14018 agent 框架切换](https://github.com/langfuse/langfuse/pull/14018)** ClaudeAgentAdapter → MastraAgent（`@ag-ui/mastra` + `@mastra/core/agent` + `@mastra/mcp`），**conversation continuity 不再靠 pod-local session ID**。
- **[#14056](https://github.com/langfuse/langfuse/pull/14056)** delete mask cleaner 等待 submitted mutations 出现。
- **[#14051](https://github.com/langfuse/langfuse/pull/14051)** Bedrock 默认 use haiku 4.5。

### 3.2 OpenLLMetry 0.61.0 后 6 天收尾
- 0.61.0（5/31 4643b882）后 main **无新 feature commit**；当前 main commits 是 GHA 依赖 bump（`#4034` 12 updates / `#3877` 8 / `#3951` 7）—— **进入 0.62 准备期**。
- **例外**：[#3409](https://github.com/traceloop/openllmetry/pull/3409) `traceloop-sdk` 加 `sampling_rate` 参数控 trace 量 —— 客户端采样，**生产降本路径**。

### 3.3 OpenLIT 1.21.1（5/28）+ otel-gpu-collector 0.0.6（6/3）
- 6/2-6/3 otel-gpu-collector **5 天双发**：arm64 native build + CGO + eBPF bindings 全到位。
- **6/3-6/7 主仓静默**，**1.21.x 收尾期**。
- **新动向**：[#1256 `feat(ts-sdk): add Astra DB (DataStax) auto-instrumentation`](https://github.com/openlit/openlit/pull/1256) —— **新 SDK 集成**（TS SDK），主仓 6/3 后唯一非 GHA 的新 PR。

### 3.4 Arize Phoenix 17.x 收尾
- **v17.0.0 / v17.1.0 / v17.2.0 两天三发**（6/2-6/3），R5 已记 v17.0 breaking changes，v17.1/v17.2 修 PXI 路由 + prompts 表刷新。

## 4. 5 个反常识

1. **`#197` 三 counter 把 `#3624` 五月合入的 cache 子集升级为正交维度** —— cache 之前是 attribute 现在变 enum，**counter + 维度直方才是 cost allocation + capacity planning 的正确抽象**。
2. **`#242` 把 framework agent.id 整个 drop** —— hosted agent stable id 与 framework agent high-cardinality GUID 是**两个不同物种**，**强制同名是反模式**。
3. **`#144` BlobPart `stripped_reason` 与 `#190` context selection event 是同一脉络** —— "不引入隐私负担的可观察性"：**结构上拒绝 empty part** 是 JSON schema 层的强制。
4. **`#211` Cohere `billed_units` SHOULD 优先** —— 不是 MUST、但 SHOULD；**Resolves 一个 13 个月 issue** 说明"计费 vs 上报"是长期未对齐的脏数据源。
5. **`#13623` Langfuse V4 backfill M1-M5 全程 dormant opt-in** —— **dormant gated row 不能 head-of-line block ungated migration** 是 BackgroundMigrationManager 的关键设计。**`boot-time validation` 拒绝不合法 env var 组合** 避免运维误配。

## 5. AIGW 5 条新硬要求 → 累加 122 条

(O-117) gateway `usage` 字段按 `{modality, cache, phase}` 三正交维度填充（`#197`），**禁用 total+子集双发**（与 #3624 一致）。
(O-118) 自生成 `gen_ai.agent.invocation.id`（UUIDv7）作 run-level 主键（`#250`），**不依赖 SDK 提供**（OpenAI Agents capture gap）。
(O-119) AIGW 透传 A2A 流量先 emit 私有 `a2a.method.name` / `a2a.task.id` / `a2a.task.state`（`#195` 合入前），合入后平滑切换。
(O-120) Cohere 上游走 `billed_units` 作 usage（`#211`），**避免客户实付与 gateway 报账裂痕**。
(O-121) framework agent 的 high-cardinality GUID **不** emit 作 `gen_ai.agent.id`（`#242`），**只 emit hosted agent 的 stable id**。

## 引用与数据来源

- OTel semconv-genai 仓 PR（按 updated_at desc，6/7 拉取）：
  - [PR#258 reasoning_effort](https://github.com/open-telemetry/semantic-conventions-genai/pull/258)（6/6 18:53，+462/-216/16）
  - [PR#238 finish_reason](https://github.com/open-telemetry/semantic-conventions-genai/pull/238)（6/6 06:33，+573/-120/14）
  - [PR#144 BlobPart stripped_reason](https://github.com/open-telemetry/semantic-conventions-genai/pull/144)（6/6 00:41，+84/-7/4）
  - [PR#257 system_instructions text-only](https://github.com/open-telemetry/semantic-conventions-genai/pull/257)（6/5 23:57，+15/-391/3）
  - [PR#242 agent.id 收窄](https://github.com/open-telemetry/semantic-conventions-genai/pull/242)（6/5 23:20，+404/-259/13）
  - [PR#202 agent.{request,response}.size](https://github.com/open-telemetry/semantic-conventions-genai/pull/202)（6/5 22:25，+361/0/4）
  - [PR#190 context.selection.evaluated](https://github.com/open-telemetry/semantic-conventions-genai/pull/190)（6/5 22:25，+469/-54/11）
  - [PR#185 evaluation operation name](https://github.com/open-telemetry/semantic-conventions-genai/pull/185)（6/5 22:25，+60/0/2）
  - [PR#203 workflow.steps](https://github.com/open-telemetry/semantic-conventions-genai/pull/203)（6/5 22:25，+273/0/4）
  - [PR#195 A2A semconv](https://github.com/open-telemetry/semantic-conventions-genai/pull/195)（6/5 20:50，+20375/-9295/21）
  - [PR#197 token usage 三 counter](https://github.com/open-telemetry/semantic-conventions-genai/pull/197)（6/5 18:30，+14060/-6971/27）
  - [PR#211 Cohere billed_units](https://github.com/open-telemetry/semantic-conventions-genai/pull/211)（6/5 18:25，+383/-154/12）
  - [PR#250 agent.invocation.id](https://github.com/open-telemetry/semantic-conventions-genai/pull/250)（6/5 06:59，+147/-79/13）
  - [PR#179 prompt versioning](https://github.com/open-telemetry/semantic-conventions-genai/pull/179)（6/5 03:58，+1398/-224/19）
  - 治理 closed（6/5）：[#226](https://github.com/open-telemetry/semantic-conventions-genai/pull/226) / [#256](https://github.com/open-telemetry/semantic-conventions-genai/pull/256) / [#255](https://github.com/open-telemetry/semantic-conventions-genai/pull/255)
- 上游收尾：
  - [Langfuse #13623 V4 backfill M1-M5](https://github.com/langfuse/langfuse/pull/13623)（+1659/-3022/97，6/5 合入）
  - [Langfuse v3 scores 4 阶段](https://github.com/langfuse/langfuse/pulls?q=is%3Apr+author%3Abezbac+scores+Phase)
  - [Langfuse #14018 agent 框架切换 MastraAgent](https://github.com/langfuse/langfuse/pull/14018)（6/5）
  - [OpenLLMetry 0.61.0 release](https://github.com/traceloop/openllmetry/releases/tag/0.61.0)（5/31）
  - [OpenLLMetry #3409 sampling_rate](https://github.com/traceloop/openllmetry/pull/3409)
  - [OpenLIT 1.21.1 release](https://github.com/openlit/openlit/releases/tag/openlit-1.21.1)（5/28）
  - [OpenLIT otel-gpu-collector 0.0.6 release](https://github.com/openlit/openlit/releases/tag/otel-gpu-collector-0.0.6)（6/3）
  - [OpenLIT #1256 Astra DB auto-instrumentation](https://github.com/openlit/openlit/pull/1256)
  - [Arize Phoenix v17.0/v17.1/v17.2](https://github.com/Arize-ai/phoenix/releases)（6/2-6/3）
- 内部历史报告：
  - [r3 observability](file:///home/ubuntu/hermes/reports/2026-06-06-1242-aigw-observability-r3.md)
  - [r4 observability](file:///home/ubuntu/hermes/reports/2026-06-06-1940-aigw-observability-r4.md)
  - [r5 observability（pending push）](file:///home/ubuntu/hermes/reports/2026-06-07-0508-aigw-observability-r5.md)
  - [genai-semconv](file:///home/ubuntu/hermes/reports/2026-06-06-0530-aigw-observability-genai-semconv.md)
