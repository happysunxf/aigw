# 2026-06-06 19:40 · AIGW 持续深挖 · Observability r4

> 主题：observability & 监控（hour 19 % 7 = 5）· 范围：r3（12:42）后 7 小时
> 切入：OTel `semantic-conventions-genai` 独立仓"协议化"冲刺 + langfuse v3.178 后 36h 关键工程收尾

## TL;DR

1. **`semantic-conventions-genai` 18+ open PR 集中冲刺**：5/5 独立成仓 32 天内已合 16 commit + 18 open PR，**协议化"agent / workflow / evaluation / A2A"四大块同时收口**。本轮 5 条新信号：#258 `gen_ai.request.reasoning_effort`、#238 `gen_ai.agent.finish_reason`、#144 `BlobPart.stripped_reason`（fail-closed 多模态）、#190 `gen_ai.context.selection.evaluated`（隐私保留 context 选择）、#185 `gen_ai.operation.name: "evaluation"` + `gen_ai.evaluate.internal` span。
2. **langfuse v3.178.0（6/2）后 4 天 9+ 关键 PR**：(a) **#13874 Monitors Worker**（+11758/-1282，113 files）——FOR UPDATE SKIP LOCKED + three-valued-logic 修 NULL 复制 run bug + bigint schema-as-codec 跨 BullMQ JSON 边界；(b) **#14058 unstable public evaluator endpoints**（+2060/-399）——公开 API 创建 `code` / `llm_as_judge` evaluator；(c) **#13342 protobufjs 7.5 `int64` 回归**——所有 `intValue` / `startTimeUnixNano` 变 `{low, high, unsigned}` 原始 shape，1 行 `{ longs: String }` 修；与 r3 #14047 是**两条入口的同型 bug**——protobuf + JSON 端都要走 OTLP spec 的 decimal string。
3. **OpenLLMetry 0.61.0 后 5 天主仓无新 commit**（0.60→0.61 间隔 42 天，0.62 大概率 7 月初）。**OpenLit** 进入 `otel-gpu-collector 0.0.6` 收尾期。
4. **协议层 vs 实现层节奏错位**：OTel semconv-genai 32 天新开 18+ PR 集中收口；langfuse / OpenLLMetry / OpenLit / LiteLLM `LITELLM_OTEL_V2` 发版后进入"等 spec final"消化期。**接下来 30 天是"协议层抢 final / 实现层抢 ship / 网关层抢落"三轨并行期**。

---

## 1. `semantic-conventions-genai` 本轮（6/4 → 6/6）关键 PR

### 1.1 协议属性（registry）

- **#258** `gen_ai.request.reasoning_effort`（+462/-216，16 files）——请求侧推理 effort（`low`/`medium`/`high`/`maximum`），与 `gen_ai.usage.reasoning.output_tokens`（使用侧）配对。Provider：OpenAI `reasoning.effort` / Google `thinking_level` / Anthropic `effort`
- **#238** `gen_ai.agent.finish_reason`（+573/-120，14 files）——agent 循环终止（`completed`/`max_iterations`/`guardrail`），与 `gen_ai.response.finish_reasons` 对偶
- **#144** `BlobPart.stripped_reason`（+84/-7，4 files）——**fail-closed observability for inline blobs**：`content` 变 optional + `stripped_reason`，top-level `anyOf` 强制 "content XOR stripped_reason"
- **#257** 限 `system_instructions` 为 text-only（+15/-391，3 files）——删 6 种不支持 part type，spec 卫生
- **#242** `gen_ai.agent.id` 限稳定标识（+404/-259，13 files）——**从 `invoke_agent.internal` span 移除**（crewAI 默认 GUID 是 high-cardinality，**和 hosted agent 稳定 ID 概念不同**）

### 1.2 指标 / 事件

- **#202** `gen_ai.agent.{request,response}.size`（+361/0，4 files）——agent 边界 payload 字节级 histogram（`{name, version}` 维度）。**非纯文本 agent token 数是糟糕的 wire size 代理**
- **#203** `gen_ai.workflow.steps`（+273/0，4 files）——`{step}` histogram，**per-agent 计数时排除 sub-agent / parent workflow events**
- **#185** `gen_ai.operation.name: "evaluation"` + `gen_ai.evaluate.internal` span（+60/0，2 files）——评测 span 之前没法按 `gen_ai.operation.name` 过滤；OpenSearch SDK 已自定义 `"evaluation"`，**生态碎片化 → 标准化**
- **#190** `gen_ai.context.selection.evaluated`（+469/-54，11 files）——**实验性** counts-only 隐私保留 context 选择信号。`candidate`/`selected`/`suppressed`/`delivered-context-hash` + 低基数 `reason`/`policy`。**明确不收** prompt / context 文本、tool outputs、memory bodies、repo excerpts
- **#98** handoff → `execute_tool`（+633/-66，10 files）——openai-agents handoff 建模成 `execute_tool` span + `gen_ai.agent.handoff.{source,target}.name`，**删** 之前提的 `gen_ai.agent.invocation.trigger`
- **#211** Cohere `billed_units` 优先（+383/-154，12 files）——Cohere 同时报 `usage.tokens` + `usage.billed_units`，**spec 明确应报 billed count**
- **#162** `gen_ai.conversation.compacted` + `CompactionPart`（+825/-211，23 files）——**compaction 是 2026 H2 多轮 agentic 必经**——长会话超 context window 后 summarize / prune。布尔 attribute + `type: "compaction"` part；**故意只 scope 到 inference span**
- **#197** modality × cache × phase token 三 counter（**+14060/-6971**，27 files，本轮最重 PR）——`gen_ai.client.token.usage` histogram → 三 counter：① `inference.tokens`（by `type` × `modality`）② `input_tokens_by_cache`（by `cache` × `modality`）③ `output_tokens_by_phase`（by `phase`）+ per-op opt-in histogram。Enum：`modality ∈ {text, image, audio, video, document, unknown}` / `cache ∈ {uncached, read, write}` / `phase ∈ {response, reasoning}`

### 1.3 协议层 / 跨组件

- **#195 A2A semantic conventions**（+20375/-9295，21 files）——A2A client + server spans + protocol attributes + task/context attrs；4 metric：operation duration / response body size / streaming TTFT / SSE event count；6 低基数 attr（`a2a.method.name` / `a2a.protocol.version` / `a2a.task.state`）。Reference 走 `a2a-sdk==1.0.3`
- **#179 prompt versioning + variable support**（+1398/-224，19 files）——把 prompt versioned identifier + template variables 加进 GenAI attributes
- 6/4–6/5 主仓 7 commits 全部 doc / dashboard / MCP context 校准。**"治理"前置**——SIG 把 review tooling、PR dashboard、CI gate 放最前
- 5/22 `opentelemetry-python-contrib#4611` 合入：9 个 `instrumentation-genai/` 子包 README 加 "contrib notice" 指向新库

---

## 2. Langfuse v3.178.0（6/2）后 4 天关键 PR

### 2.1 #13874 Monitors Worker — scheduler + processor + dispatcher [PR](https://github.com/langfuse/langfuse/pull/13874) | +11758/-1282 | **113 files** | LFE-9812/9815

**Scheduler** 走 `FOR UPDATE SKIP LOCKED` 抢行 + 推进 `next_run_at` 到 cadence-aligned 下一个 boundary（加 `(scheduler_batch_id % 60)` 秒 jitter 防 thundering herd）。重命名 `scheduledAt` → `runAt`，词根统一。`next_run_at` 改 nullable 让新建 monitor 立即可被调度器 tick 抢到。**修 three-valued-logic 真 bug**：`runIsPending` 中 `last_completed_run_at < last_published_run_at` 在 NULL 时 evaluate 成 `NULL`，`AND` 链短路让 CASE 把 `last_published_run_at` 再 stamp 一遍——**worker 还在跑第一个 job 时第二个 duplicate run 已经 publish**。修法：NULL 当 never-completed。

**Schema-as-codec**（**反常识**）：scheduler emit `schedulerBatchId` **用 string**（bigint **绝不**进 BullMQ `JSON.stringify`——会丢精度），`MonitorQueueEventSchema` 用 `z.coerce.bigint()`，消费者端还原。

**Processor**：删 RFC 的 Redis lock 改 **row-level `last_claimed_run_at` CAS**（新列）。Conditional UPDATE 三 clause：(1) 拒 stale republish of a different `runAt`；(2) 拒 already completed runs；(3) 拒 live claim of the same publish 除非 per-processor TTL（锚定 `last_published_run_at`，配 scheduler rescue window）已过。**跨 worker idempotent**。

**AIGW 含义**：(1) `next_run_at` nullable + 调度器首次 stamp；(2) `runAt`/`next_run_at`/`last_published_run_at` 词根统一；(3) `last_claimed_run_at` 替代 Redis lock；(4) BullMQ 边界 bigint → string 进出。

### 2.2 #14058 unstable public evaluator endpoints [PR](https://github.com/langfuse/langfuse/pull/14058) | +2060/-399 | 22 files | LFE-9856

公开 API 创建 / 返回 `llm_as_judge` + `code` evaluator，**`type` 字段缺省 `llm_as_judge`（向后兼容）**。Evaluation-rule 公开 endpoint 引用 code evaluators，**Langfuse 持有 fixed runtime mappings**，**用户不可注入** code rule 的 mappings（防任意代码映射到生产 prompt eval）。UI/tRPC 与 public API 共享 code evaluator job-config **preflight validation**，**active code rules 在 create/update 前必跑**。

**AIGW 含义**：**code evaluators 在 SaaS LLM eval 平台是 first-class surface**——"eval = 黑盒 LLM judge" 拆成 "LLM judge + code rule + reference scenario"。

### 2.3 #13342 protobufjs 7.5 `int64` 回归 [PR](https://github.com/langfuse/langfuse/pull/13342) | +8/0 | 1 file | Fixes #13295

[#13232](https://github.com/langfuse/langfuse/pull/13232) 把 protobufjs 7.4→7.5 后，**所有 OTLP/protobuf ingestion 的 `int64` 字段**（`intValue` / `startTimeUnixNano` / `endTimeUnixNano` / `timeUnixNano`）开始序列化成 protobufjs 内部 Long shape `{"low": ..., "high": ..., "unsigned": ...}`。下游 server-side ingestion masking callback 拿到这 shape 就崩。根因：`web/src/pages/api/public/otel/v1/traces/index.ts:96` 调 `toObject(parsed)` **没传 `longs` option**——7.4 `util.Long` 永远没初始化（long.js 解析不到），**`int64` 静默 fall back 到 plain JS number**；7.5 创建内部 fallback Long class（long.js 缺失时），**这个 class 没实现 `toJSON()`**，**`JSON.stringify` 直接输出 enumerable `{low, high, unsigned}`**。

**修复**：`{ longs: String }` → `int64` 字段以 decimal string 出来，**匹配 OTLP/JSON spec**，nanosecond 时间戳（`Number.MAX_SAFE_INTEGER` 之外）安全。

**与 r3 #14047 是同型 bug 两条入口**：r3 是 OTLP/JSON 端 string-encoded int64 被 `high * 2^32 + low` 求 `high` undefined → NaN → 拒收；**本轮是 OTLP/protobuf 端 protobufjs 7.5 bump 让 int64 长成 object shape**。**AIGW 凡自研 OTLP ingestion 必须做这层 normalize**。

### 2.4 配套 PR

- **#13748** in-app agent trace（+869/-40，8 files）——`InAppAgentInstrumentation` 接进 `createAgUiStream`，**`ended` guard 防多 terminal path 双重记录**（error/abort/cancel/RUN_ERROR/normal completion，**全部必须 end/endWithError exactly once** + 触发 flush）。`aiTelemetryEnabled` + `targetProjectId` 门控
- **#14066** CI 跑最新 ClickHouse 版本——防 ClickHouse 升级导致 ingest 回归
- **#13882** `scores.all` 在 self-hosted ClickHouse 跑 `scoresTableUiColumnDefinitions` 出的 `timestamp` / `environment` **不带 `s.` 前缀**，**FROM `scores s`** 时 ClickHouse 报 "column not found" → **Scores UI 在 self-hosted 加载失败**。修法：14 个 scores-native 列加 `queryPrefix: "s"`。Issue #13809 / #13872 是同一 bug duplicate
- **Bug tracker**：#13809 `column not found for scores route`（6/6 09:07，#13882 已 fix）/ #13292 `ADK integration does not have pretty traces`（6/6 02:17，Google ADK v2.2.0 升级后 span 渲染异常，**多模态 / agent 化 ADK trace UX** 仍未跟上）

---

## 3. r3 PR 走向 + 横向节奏

### 3.1 r3 PR 走向

- **#220 MCP context propagation** ✅ **merged** 6/4 15:47, c4503710——本轮 c4503710 / 0b4076fd / 24cdda01 周边 6 commits 全是 doc + dashboard 收尾
- **#197 token modality × cache × phase** 仍 open（+14060/-6971，27 files），#258 reasoning_effort 紧跟其后落地是配套信号——token + reasoning 维度两条同步推
- **#195 A2A** 仍 open（+20375/-9295，21 files），与 #98 handoff `execute_tool` + #250 `gen_ai.agent.invocation.id` + #252 `invoke_agent.server` 形成"A2A / agent 协议化矩阵"
- **#252 `invoke_agent.server`**（SERVER kind，6/5 00:43 update）仍 open，与 #250 `gen_ai.agent.invocation.id` 配对落地

**r3 后新冒头 4 条**（§1 详述）：#258 reasoning_effort / #238 agent.finish_reason / #190 context.selection.evaluated / #185 evaluation operation name + span。

### 3.2 横向节奏

| 项目 | 上次 commit / release | 距今 | 状态 |
|---|---|---|---|
| **OTel `semantic-conventions-genai`** | 6/5 23:40（#226 → 0c9acdef）| ~20h | **最活跃**——18+ open PR 集中冲刺 |
| **langfuse** | 6/6 08:57（#14066）| ~11h | 仍活跃，**#13874 monitors + #14058 code evaluators 是两条主线工程** |
| **OpenLLMetry** | 5/31 07:26（0.61.0）| 6.5 天 | 0.60→0.61 间隔 42 天，0.62 大概率 7 月初 |
| **OpenLit 主仓** | 6/3 07:15（#1252）| 3.5 天 | 静默期，0.0.6 已 GA |
| **Helicone** | 5/18 23:17（#5683）| 19 天 | 静默期；AWS Bedrock 事件已 banner resolved |
| **LiteLLM `LITELLM_OTEL_V2`** | 5/30（#28909）| 7 天 | 1.88 RC 收尾 |

**AIGW 含义**——网关层想落地 GenAI semconv，**锁一个 spec 版本**（建议 OTel `semconv-conventions-genai` 主仓 tag 或 [python-contrib genai-util 0.2x](https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/util/opentelemetry-util-genai)），**等协议层 final 再大改**。

---

## 4. 5 个反常识

(a) **协议属性"删比加难"**——PR #242 把 `gen_ai.agent.id` 从 `invoke_agent.internal` span **移除** 用了 +404/-259 / 13 files。crewAI 默认 GUID 是 high-cardinality、**和 hosted agent 稳定 ID 概念冲突**——**"稳定 ID" 在多租户平台是治理底线**。(b) **`BlobPart.stripped_reason`** 把 "multipart content 缺字节" 转成 "结构化 strip 原因"——**fail-closed observability 范式**："我不知道 content 是什么" 合法，**"我不知道 content 是什么但假装合规"** 不合法。(c) **PR #190 `context.selection.evaluated` counts-only 不收原始文本**——"harness upstream 选太多 context" 是 2026 H2 浪费信号大头，**不用 raw content capture 也能查**。(d) **`gen_ai.client.token.usage` 从 histogram → 三 counter**（PR #197）——histogram 把 cost / cache / modality 维度压扁，**counter + 维度直方才是 cost allocation + capacity planning 的正确抽象**。(e) **langfuse #13342 与 r3 #14047 是同型 bug 两条入口**——**protobuf 端** `intValue` 变 `{low, high, unsigned}` / **JSON 端** string-encoded int64 求 `high` undefined → NaN —— **都走 OTLP spec 的 decimal string 才正确**。

---

## 5. AIGW 6 条新硬要求 → 累加 124 条

(O-1) **锁 spec 版本**（**新增**）：网关层**不要在大改期追 OTel main head**，锁 `semantic-conventions-genai` tag（如 v0.5.0）+ `opentelemetry-util-genai` Python 0.2x；7 月-8 月协议层 6-8 条 final 后**一次性升级**。(O-2) **`gen_ai.client.token.usage` 字段按三 counter 走**（**PR #197 范式**）：`{type, cache, phase, modality}` 四正交维度，**counter 不打 histogram**。(O-3) **`gen_ai.request.reasoning_effort`**（**PR #258 范式**）：所有 GenAI instrumentation **请求侧** 必 emit 推理 effort attribute（OpenAI / Gemini / Anthropic 三个 provider 同时支持），与 `gen_ai.usage.reasoning.output_tokens`（使用侧）**配对分析**。(O-4) **`BlobPart.stripped_reason` + `gen_ai.conversation.compacted` + `gen_ai.agent.finish_reason`**（**三 fail-closed 范式**）：**结构上不可"空 part / 假装 compact / 假装 agent 终止"**——任何 stripped / compacted / agent-terminated 信号必带 reason + version 字段，**否则结构上拒绝**。(O-5) **OTLP int64 ingestion 双归一**（**#13342 + #14047 范式**）：**protobuf 端** `toObject({ longs: String })` + **JSON 端** `"high" * 2^32 + "low"` string-encoded 都用 **decimal string** 落到下游 writer，nanosecond 时间戳不丢精度。(O-6) **AIGW 监控派发器走"DB row CAS + SKIP LOCKED"**（**langfuse #13874 范式**）：`FOR UPDATE SKIP LOCKED` 抢 + `next_run_at` nullable + 调度器首次 stamp + `runAt`/`next_run_at`/`last_published_run_at` 词根统一 + 删 `calculateLastRunAt` 把 slot alignment 收归调度器 + **`last_claimed_run_at` CAS 替代 Redis 分布式锁** + BullMQ 边界 bigint → string 进出。

---

## 引用与数据来源

- [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) — PR [#258](https://github.com/open-telemetry/semantic-conventions-genai/pull/258) / [#238](https://github.com/open-telemetry/semantic-conventions-genai/pull/238) / [#144](https://github.com/open-telemetry/semantic-conventions-genai/pull/144) / [#257](https://github.com/open-telemetry/semantic-conventions-genai/pull/257) / [#242](https://github.com/open-telemetry/semantic-conventions-genai/pull/242) / [#202](https://github.com/open-telemetry/semantic-conventions-genai/pull/202) / [#203](https://github.com/open-telemetry/semantic-conventions-genai/pull/203) / [#185](https://github.com/open-telemetry/semantic-conventions-genai/pull/185) / [#190](https://github.com/open-telemetry/semantic-conventions-genai/pull/190) / [#98](https://github.com/open-telemetry/semantic-conventions-genai/pull/98) / [#211](https://github.com/open-telemetry/semantic-conventions-genai/pull/211) / [#162](https://github.com/open-telemetry/semantic-conventions-genai/pull/162) / [#197](https://github.com/open-telemetry/semantic-conventions-genai/pull/197) / [#195](https://github.com/open-telemetry/semantic-conventions-genai/pull/195) / [#179](https://github.com/open-telemetry/semantic-conventions-genai/pull/179)
- [langfuse/langfuse](https://github.com/langfuse/langfuse) — [v3.178.0](https://github.com/langfuse/langfuse/releases/tag/v3.178.0) / [v3.177.x](https://github.com/langfuse/langfuse/releases)；PR [#13874](https://github.com/langfuse/langfuse/pull/13874) / [#14058](https://github.com/langfuse/langfuse/pull/14058) / [#13342](https://github.com/langfuse/langfuse/pull/13342) / [#13748](https://github.com/langfuse/langfuse/pull/13748) / [#14066](https://github.com/langfuse/langfuse/pull/14066) / [#13882](https://github.com/langfuse/langfuse/pull/13882)；issue [#13809](https://github.com/langfuse/langfuse/issues/13809) / [#13292](https://github.com/langfuse/langfuse/issues/13292) / [#13295](https://github.com/langfuse/langfuse/issues/13295)
- [traceloop/openllmetry](https://github.com/traceloop/openllmetry) — [0.61.0](https://github.com/traceloop/openllmetry/releases/tag/v0.61.0) / [0.60.0](https://github.com/traceloop/openllmetry/releases/tag/v0.60.0)
- [openlit/openlit](https://github.com/openlit/openlit) — [otel-gpu-collector 0.0.6](https://github.com/openlit/openlit/releases)
- [opentelemetry-python-contrib](https://github.com/open-telemetry/opentelemetry-python-contrib) — [PR #4611](https://github.com/open-telemetry/opentelemetry-python-contrib/pull/4611)
- [opentelemetry/semantic-conventions](https://github.com/open-telemetry/semantic-conventions) — 5/5 16:12 UTC 迁库点（[#3696](https://github.com/open-telemetry/semantic-conventions/pull/3696)）
- [Helicone/helicone](https://github.com/Helicone/helicone) — [commit 094b210b #5683](https://github.com/Helicone/helicone/commit/094b210b) AWS banner resolved
- 上轮参照：[reports/2026-06-06-1242-aigw-observability-r3.md](reports/2026-06-06-1242-aigw-observability-r3.md) / [reports/2026-06-06-1203-aigw-observability-r2.md](reports/2026-06-06-1203-aigw-observability-r2.md)
