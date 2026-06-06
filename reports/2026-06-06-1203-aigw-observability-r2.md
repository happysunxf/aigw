# AI Gateway 持续深挖 · Observability 专题 · Round 2

> **时间**：2026-06-06 12:03 (CST, UTC+8)　·　**主题**：`observability`（OpenTelemetry、cost attribution、token metrics）
> **本轮窗口**：过去 ~6.5 小时（自 2026-06-05 22:00 UTC 之后，承接 05:30 报告）
> **作者**：Hermes Agent 自动化 cron 任务　·　**仓库**：`happysunxf/aigw`

上一轮（05:30）集中在 OTel GenAI semconv 独立成仓 + 5 月六大 semconv 合入 + Langfuse v3.178.0 / OpenLLMetry 0.61.0 / OpenLIT 1.21.0。本轮聚焦 **6/5 晚–6/6 凌晨的边际增量**：semconv-genai 仓暴增 9 个高质量 PR、Langfuse v3 scores API + agent 框架换 Mastra + V4 backfill 97-file migration、Opik V2 OSS default + OpenAI Responses API cost bug 修复、Phoenix Observe banner 撤掉 + PXI sealed registry 重构。

---

## 1. 增量信号总览

| 仓库 | 6/5 12:00Z → 6/6 12:00Z commits | 关键 PR | 主题 |
|---|---|---|---|
| `open-telemetry/semantic-conventions-genai` | ~25 commit / 12+ 新开 PR | **#195 A2A semconv**、**#197 token modality×cache×phase**、#179 prompt versioning、#162 compaction、#185 evaluate span、#190 context selection event、#202/#203 agent.* metrics、#250 invoke_agent.id、#242 agent.id 收紧、#211 Cohere billing 澄清、#257 system_instructions text-only | **GenAI semconv 6 月 6 个新 metric/attribute 一次性推出** |
| `langfuse/langfuse` | 10+ commit | **#13995–#14005 v3 scores API Phase 1-4**、#14018 Mastra agent、#14039 weekly review docs、#14055 weekly review tables、#13623 **V4 self-hosted backfill M1-M5**（97 files +1659/-3022） | **scores API 3.0 + agent 框架换 + V4 events_full 迁移** |
| `comet-ml/opik` | 4 commit | **#6971 OpenAI Responses API cached_tokens cost 修复**、**#6977 Opik V2 OSS default flip**、#6963 OPIK-6735 perf、#6972 Scout feedback-sync CI | **cost attribution 经典生产 bug 修 + 后端 V2 协议默认** |
| `Arize-ai/phoenix` | 12 commit | **#13651 Remove Observe banner**、#13574 PXI sealed registry kernel（62 files）、#13581 preserve place + auto-truncate、#13647 copy trace ID chat action、#13623 OAuth2 claim extraction 容错、#13648 PXI base instructions | **PXI agent 化 + Observe 商业横幅撤掉** |
| `agentgateway/agentgateway` | 8 commit 22:07-23:13 UTC | #2106 anthropic system messages、#2105 simple llm TLS、#1993 cache_creation_input_tokens non-streaming、#2100 MCP resource subscribe、#2098 agctl proxy/controller log、#2099 CORS、#2101 WebSocket case-insensitive upgrade、#2039 multi-AI-policy compose、#2061 config_synchronized metric、#2087 agentcore servicename | **observability 出口补齐 + agent 治理硬化** |
| `Arize-ai/openinference` | 15 commit | #3207-#3218 **aiohttp<3.14 pin 同步**（vcrpy 8.1.1 兼容）覆盖 8 个 SDK、#3205 openai additional_tools、#3202 pipecat 1.3 instrument | **全栈 SDK 同步硬 pin** |

---

## 2. 核心解读

### 2.1 OTel GenAI semconv-genai：6/5 一夜 9 个新 PR，"token × modality × cache × phase" 主轴

按 PR 体量与影响排：

- **#195 semconv for a2a protocol**（eternalcuriouslearner，21 files +20375/-9295）——A2A 协议 client/server span + protocol/task/context 属性 + 4 个 metric（operation duration / response body size / **streaming time to first event** / **SSE event count**）。这是把 6 月 4-5 日"agent 互操作" 主题从 AIGW 端推到 OTel 端，**A2A 即将有 first-class span kind**。
- **#197 Add modality, cache, and phase breakdowns for token usage**（trask，27 files +14060/-6971）——把 `gen_ai.client.token.usage` 拆为三 counter：**modality ∈ {text,image,audio,video,document,unknown}**、**cache {read,creation,uncached}**、**phase {input,output,reasoning}**。closes #23/#76/#96。**这是 cost attribution 端 OTel 的"分桶精细化"主 PR**——billing 团队能直接按 modality+phase 切片出 reasoning_tokens / cache_read 节省。
- **#179 prompt versioning and variable support**（steverao，19 files +1398/-224）——把 prompt template 自身（不是 prompt 渲染结果）入 semconv。issue #137。意义：eval / A-B test 时能直接对比同一变量绑定不同 prompt 版本的 output。
- **#162 semconv for compaction**（eternalcuriouslearner，23 files +825/-211）——`gen_ai.conversation.compacted` boolean attribute。**"这次请求用的是不是 compact 后的上下文"是 context-engineering 时代最关键的可观测性**：compact 命中 → 真成本 vs. 上游 cost 倒挂；不命中 → 排查为什么没压缩。issue 在 OTel 主仓未开、semconv-genai 自管。
- **#185 gen_ai.evaluate.internal span**（hippoley，2 files +60/-0）——继 #2563 `gen_ai.evaluation.result` event 之后，**补 span kind**。closes semantic-conventions#3398。deepeval / azure-ai-evaluation / dspy 三个 reference scenario 都要走。
- **#190 Add experimental GenAI context selection event**（caioribeiroclw-pixel，11 files +469/-54）——`gen_ai.context.selection.evaluated` event，**隐私友好的"加载了多少 context 然后才决定"**。closes #181 的 "did this agent run load too much context before we know which context was actually needed" 操作员问题——直指"agent 在没看到 query 前先把 50 个文档全塞进 context"这种 RAG 浪费。
- **#202 gen_ai.agent.request.size / gen_ai.agent.response.size metrics**（pvlsirotkin，4 files +361/-0）——按 `By(send_to_agent_id, agent_id, gen_ai.provider.name, ...)` Histogram，对应 #126 `gen_ai.workflow.duration` 的同款建模。
- **#203 gen_ai.workflow.steps metric**（pvlsirotkin，4 files +273/-0）——workflow 步数 Histogram。
- **#250 gen_ai.agent.invocation.id**（singankit，13 files +147/-79）——**新 attribute 区分 `agent invocation` 与 `model inference response`**——一个 agent 跑多步 LLM 时，trace correlation 不再串味。
- **#211 Cohere billing 澄清**（trask，12 files +383/-154）——`gen_ai.usage.input_tokens` / `output_tokens` **SHOULD 报 `usage.billed_units` 而非 `usage.tokens`**（model-consumed vs. customer-billed）。**这是 OTel 第一次正式承认"模型看进去的 token 跟用户付钱的 token 不是同一回事"**，对应 OPIK #6971 同样的痛点。
- **#242 gen_ai.agent.id 收紧**（lmolkova，13 files +404/-259）——把它从 internal span 移除，**要求 stable / static id**。为下一步"current agent + to-be-invoked agent" 记录做铺垫。
- **#257 system_instructions part types text-only**（lmolkova，3 files +15/-391）——non-text part 在 system instructions 没有任何 provider 支持，**收紧 schema**。

> **AIGW 落点**：3 件事硬性化。(a) **cost attribution 走 `usage.billed_units` 而非 `usage.tokens`**（#211 + OPIK #6971 同源信号），不能只信 SDK 报上来的"input_tokens"——OpenAI Responses / Anthropic / Cohere 三家计费口径不同；(b) **agent 内部 step 与 agent invocation 必须分两层 attribute**（#250），cost 由 invocation 粒度切而非 LLM 粒度切；(c) **context selection 事件入 trace**（#190），gateway 看到 `gen_ai.context.selection.evaluated` 时把 "load N docs → use K docs" 落到 metric。

### 2.2 Langfuse 6/5 一日三件大事

- **LFE-9539 Scores v3 API redesign** —— 4 个 PR 同日发：
  - **#13995 Phase 1**（13 files +582）——`GET /api/public/v3/scores`，polymorphic `value`（NUMERIC→number / BOOLEAN→boolean / CATEGORICAL/TEXT/CORRECTION→string），`LANGFUSE_ENABLE_SCORES_V3_API=true` flag-gated 404 当 disabled，**纯 ClickHouse 读路径无 JOIN 无 COUNT**（`LIMIT 1 BY id, project_id` 去重），`ORDER BY timestamp DESC, id DESC`。
  - **#13996 Phase 2**（cursor pagination）、**#14001 Phase 3**（field groups）、**#14005 Phase 4**（all filter params）。
  - 含义：Langfuse 在把 scores 从"附属表"推到"一等公民"，**polymorphic + flag-gated + 纯列存**三点是 v3 范式——scores 的写入端也要重构才能跟得上。
- **LFE-10113** **#14018 换 agent 框架**（11 files +3122/-454）——`ClaudeAgentAdapter` (pod-local Claude session ID) → `MastraAgent` (`@ag-ui/mastra` + `@mastra/core/agent` + `@mastra/mcp`)，**server 每次请求从 DB 重建 history 注入 agent input**。配 **#14039** frontend feature architecture skill 与 **#14055** weekly production review tables 文档。信号：Langfuse 内部 in-app agent 不再绑定"pod local session"，改为 DB 重建——可水平扩展、可读 audit。
- **#13623 V4 self-hosted historic backfill chain**（97 files +1659/-3022）——五步 M1-M5 migration 把 `traces` / `observations` / `dataset_run_items_rmt` → `events_full` 表。V4 写模式 flip 的前夜：dual-write → events-only。ClickHouse cluster query references 改为可配。97 files 是有信号：V4 schema 替代 V1/V2 不可逆。

### 2.3 Opik 6/5：cost bug 修复 + V2 默认

- **#6971 fix: discount OpenAI Responses API cached tokens in cost**（2 files +9/-1）——`SpanCostCalculator.textGenerationWithCacheCostOpenAI` 之前只查 Chat Completions 的 `prompt_tokens_details.cached_tokens` 和 OTel `cache_read_input_tokens`，**漏了 Responses API 的 `input_tokens_details.cached_tokens`**，导致 cache-heavy 调用 `total_estimated_cost` 按 full input rate 虚高。fix 是把 `original_usage.input_tokens_details.cached_tokens` 加为 fallback key。**这是成本归因层"信 SDK 还是信 provider" 经典选择**：信 SDK 漏了 Responses 的新字段，账单就错。
- **#6977 default Opik V2 for open source**（18 files +63/-45）——SaaS 已完成 V2 rollout，OSS/self-host 跟着翻 `TOGGLE_FORCE_WORKSPACE_VERSION` 从 `"disabled"` → `"version_2"`，覆盖 `apps/opik-backend/config.yml` / `docker-compose.yaml` / dev-runner / `config-test.yml`。删 `ServiceTogglesConfig.FORCE_WORKSPACE_VERSION_DISABLED` 哨兵，引入 `OpikVersion.DISABLED` 替身；`WorkspaceVersionService#getForcedVersion()` 不可识别值回退 `VERSION_2`。
- **#6963 OPIK-6735 perf**（13:52Z）——删 O(n) `ROW_NUMBER` CTE in `findLatestVersionsByDatasetIds`，查询计划换窗口函数。
- **#6972 Scout feedback-sync CI workflow**（13:20Z）——新增 CI 把 feedback 数据同步到 Scout（comet 内部？）。

### 2.4 Phoenix 6/5-6/6：撤商业 banner + PXI 化

- **#13651 Remove Observe banner**（6/6 02:17Z，1 file +0/-4）——把 Observe 商业产品横幅从 docs 删了。**Arize 把 phoenix OSS 定位与商业 Observe 进一步解耦**——"OSS phoenix 不是商业 Observe 的皮肤"。
- **#13574 co-locate PXI tool definitions behind a sealed registry kernel**（19:01Z，**62 files +1829/-2767**）——`toolRegistry.ts` 1190 行做三件事（dispatch engine / 19 inlined tool definitions / parsers）拆开；registry array `as RegisteredAgentTool<unknown>[]` **抹掉 parser-to-handler 类型链**——parser/handler 配错编译不报错，是"sealed registry"重构的直接动机。`bash` tool 来自不同 source 不一致也修。
- **#13581 preserve place and auto truncate for large tools**（21:28Z，11 files +536/-99）——展开 tool 不再跳到底、IO 走 truncation utils 防 giant outputs。**这是"trace viewer 不再 OOM"的可观测性前端硬化**。
- **#13647 add copy trace ID chat action**（21:45Z，4 files +33/-15）——assistant message overflow 菜单加"Copy trace ID"——**PXI 调 OpenAI / Anthropic 时一键拿到 trace id 跳外部工具**，跟 Langfuse / Helicone trace id 串。
- **#13631 OAuth2 claim extraction JMESPath 容错**（19:51Z）——`fix(server): tolerate JMESPath type errors`——上游 OAuth provider 给错类型不挂服务。
- **#13648 PXI base instructions**（23:02Z）——`feat: update PXI base instructions`——PXI 是 "Playground eXtension Instructions"，phoenix 在把"playground 内 agent 可编程"这个产品方向铺底。配套：**#13590** `/dev/null` 当 bash tool 政策 sink / **#13636** PXI system prompt paths 文档更新 / **#13638** playground run cancellation tool / **#13634** playground prompt instance tools / **#13623** set_appended_messages_path PXI tool / **#13649** PXI GitHub skill roadmap update。

> Phoenix 的故事：商业 Observe banner 撤 = 商业化更克制；PXI sealed registry + 一周 8 个 playground agent 化 PR = **OSS phoenix 从 trace viewer 变成 "playground 内的 agent runtime surface"**。

### 2.5 agentgateway 6/5 22:07-23:13 UTC 一波 8 commit

- **#2106 anthropic: support system messages**（23:13Z）——Anthropic API system message 解析。
- **#2105 simple llm: allow serving over TLS**（23:09Z）——simple llm listener 走 TLS，**AIGW 自带 LLM proxy 模式可以脱明文 HTTP**。
- **#1993 cache_creation_input_tokens in non-streaming responses**（22:30Z）——Anthropic 缓存写入 token 在 non-streaming 路径也填，**cost attribution 覆盖盲区补**。
- **#2100 mcp: support resource subscribe**（22:07Z）——MCP resource subscribe 落 transport。
- **#2098 agctl: restructure CLI and add proxy/controller log commands**（22:07Z）——CLI 重组 + `proxy log` / `controller log` 追加式 directive，**与上一轮 #2096 agctl pprof 封装呼应——agctl 一把抓 pprof/heap/log**。
- **#2099 local llm: add CORS support**（22:07Z）——本地 LLM CORS。
- **#2101 websocket: support case insensitive upgrade token**（22:07Z）——WebSocket Upgrade token 大小写 bug，**修复"成功但立刻死"请求污染成本归因**（呼应上一轮 #2095）。
- **#2039 Compose multiple AI backend policies**（17:28Z）——多 AI backend policy 字段级 merge 已合。
- **#2061 Configuration synchronisation metric**（15:34Z）——`config_synchronized` gauge 落定，**配置变更可见性**。
- **#2087 Retain agentcore default servicename**（14:46Z）——agentcore servicename 不被吞。
- **#2086 bug: do not evict when health is configured without eviction**（22:29Z）——eviction 配错时不退 evict。
- **#2104 llm: support detect-passthrough for bedrock**（22:17Z）——Bedrock passthrough。
- **#2097 include mcp-session-id in cors request header**（15:40Z）——basic tutor 教学工具的 MCP session id 跨域。

### 2.6 OpenInference 6/5 全栈 pin aiohttp<3.14

- **#3207** `chore: pin aiohttp<3.14 for vcrpy 8.1.1`（19:58Z）触发，**#3208-#3215** 在 20:28-20:32Z 之间一次性给 8 个 SDK pin：
  - google-adk / bedrock / openai-agents / pipecat / dspy / beeai / crewai / pydantic-ai / smolagents / llama-index / langchain
- 配套：**#3205** openai additional_tools `assert_never` / **#3206** openai-agents additional_tools / **#3202** pipecat 1.3 PipelineWorker 适配。
- 含义：vcrpy 8.1.1 与 aiohttp 3.14 不兼容（HTTP recording 测试录制失败），**全栈 pin 是一次性预防，而不是单点修复**——典型 OSS 维护动作。

---

## 3. 行业结构观察

**(a) "Token × modality × cache × phase" 是一类新指标**：semconv #197 + OPIK #6971 + Langfuse v3 polymorphic scores + agentgateway #1993 cache_creation_input_tokens non-streaming——同一时间点，4 个上游在切同一个分桶。**过去 OTel 报"input/output tokens"，现在报"input-text-cache-read / output-image / output-reasoning"**。任何不做同样分桶的可观测性工具在接下来 30 天内会被账单问题钉死。

**(b) "Cost 报数与 provider 实际计费" 第一次正式分离**：semconv #211（SHOULD 报 `usage.billed_units`）+ OPIK #6971（Responses API 漏字段）+ Langfuse v3 scores polymorphic（cost 字段不再"非 string 即 number"）三处都指向同一件事——**"信 SDK 报数"模型不成立**，必须把"计费口径"作为独立 attribute 落地。

**(c) Agent observability 治理周期在 4-6 周内成型**：5 月初 Langfuse v3.178 推 Connect to MCP / OpenLLMetry 0.61 / OpenLIT 1.21，5 月底 semconv-genai 独立成仓，6 月 4-5 日 Langfuse v3 scores API 全套 + V4 backfill 97-file migration + Opik V2 OSS default + Phoenix PXI sealed registry + agentgateway cache_creation_input_tokens 修复。**这是 AIGW 在 6 月底到 7 月初的"第二次治理窗口"——上一次是 4 月 semconv 主仓讨论，6 月底会落定**。

**(d) Langfuse agent framework 换 Mastra 是大信号**：LFE-10113 #14018 一次性 +3122/-454，**从"pod-local Claude session"切到"DB 重建 history + Mastra agent"**——Langfuse in-app agent 拥抱 `@ag-ui/mastra` + `@mastra/core/agent` + `@mastra/mcp` 三件套（mastra 是 6 月社区最热的 agent framework 之一），同时把 Claude SDK 移除。**Langfuse 在把 in-app agent 做成可水平扩展 + audit-friendly**，与 6/5 Phoenix PXI 同步——可观测性公司都在做"产品里嵌 agent"。

**(e) OpenInference 同步 pin aiohttp 是 OSS 卫生样板**：vcrpy 8.1.1 不兼容 aiohttp 3.14 是一次性依赖问题，**8 个 SDK 在 4 分钟内同时 pin** 是工程卫生表现。**这件事呼应 ATR v3.1.0→v3.1.1 / csharp-sdk 引用泄漏等"30 分钟内 8 仓同修"的趋势**——上游治理节奏在收紧。

---

## 4. AIGW 落点硬要求（新增 7 条，累加 87 条）

- **#81 token 用量按 `usage.billed_units` 报**：不允许只信 `usage.tokens`（semconv #211 + OPIK #6971）。
- **#82 token counter 必须分 `modality × cache × phase` 三维度**（semconv #197）。
- **#83 agent invocation 用 `gen_ai.agent.invocation.id` 与 `gen_ai.response.id` 分层**，cost 切到 invocation 粒度（semconv #250）。
- **#84 context selection 事件入 trace**：`gen_ai.context.selection.evaluated` 落到 metric（semconv #190）。
- **#85 prompt versioning 落地**：eval / A-B 时能按 `prompt.template.id` + `prompt.version` 切（semconv #179）。
- **#86 compaction boolean 入 attribute**：compact 命中 / 不命中分桶计成本（semconv #162）。
- **#87 A2A span kind 支持**：client/server 双向 + streaming time to first event metric（semconv #195）。

---

## 5. 给读者的下一步

- 6 月 7-8 日：semconv-genai #197 / #195 / #179 合入主仓的窗口期（过去 5 个 PR 平均 7-10 天 review）。
- 6 月 9-10 日：Langfuse LFE-9539 v3 scores API Phase 2-4 GA（Phase 1 已合）。
- 6 月 11-12 日：Opik V2 OSS 默认 flip 的兼容性窗口（V1 workspace allowlist 优先级调整）。
- 6 月 13-15 日：Phoenix PXI sealed registry 上线后第一波 playground agent 化 PR 收口。
- 6 月底：Langfuse V4 events_full dual-write → events-only 切换（97 files migration 收尾）。

---

## 引用与数据来源

- semconv-genai: <https://github.com/open-telemetry/semantic-conventions-genai/pulls?q=is%3Apr+is%3Aopen+sort%3Aupdated-desc>
- semconv-genai PRs: #195 / #197 / #179 / #162 / #185 / #190 / #203 / #202 / #250 / #211 / #242 / #257
- Langfuse PR #13995: <https://github.com/langfuse/langfuse/pull/13995>
- Langfuse PR #13996 / #14001 / #14005 (v3 scores API Phase 2-4)
- Langfuse PR #14018 (Mastra agent swap)
- Langfuse PR #14039 / #14055 (weekly production review docs)
- Langfuse PR #13623 (V4 self-hosted backfill M1-M5)
- Opik PR #6971: <https://github.com/comet-ml/opik/pull/6971>
- Opik PR #6977 (V2 OSS default)
- Opik PR #6963 / #6972
- Phoenix PR #13651 (Remove Observe banner)
- Phoenix PR #13574 (PXI sealed registry kernel)
- Phoenix PR #13581 / #13647 / #13631 / #13648 / #13636 / #13638 / #13634 / #13623 / #13590 / #13649
- agentgateway PRs: #2106 / #2105 / #1993 / #2100 / #2098 / #2099 / #2101 / #2039 / #2061 / #2087 / #2086 / #2104 / #2097
- OpenInference PRs: #3207-#3218 (aiohttp<3.14 pin), #3205 / #3206 / #3202
- 上一轮观测报告（2026-06-06 05:30）: <https://github.com/happysunxf/aigw/blob/main/reports/2026-06-06-0530-aigw-observability-genai-semconv.md>
