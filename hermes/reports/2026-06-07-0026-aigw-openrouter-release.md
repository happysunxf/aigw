# AI 网关持续深挖 · OpenRouter 发版与产品信号追踪（2026-06-07）

> **轮次**：2026-06-07 00:26 CST · `release` 主题 · OpenRouter
> **数据窗口**：过去 30 天（2026-05-08 → 2026-06-07）OpenRouter 主战场
> **来源**：`/api/v1/models`（341 模型 created 真实）、`/blog/feed.xml`（63 条）、5 篇主博客正文、GitHub `ai-sdk-provider` / `go-sdk` 仓

## 0. 一句话总结

**OpenRouter 在 2026 H1 完成「模型聚合」→「生产 AI 基础设施」叙事跃迁。** 5/28 $113M Series B（CapitalG 领投，NVentures + ServiceNow/MongoDB/Snowflake/Databricks Ventures 战略跟投），周路由量 5T → 25T tokens。5 月发 Guardrails / Model Fusion / Audio APIs / Response Caching / Session-id Stickiness / Auto router `cost_quality_tradeoff` 五条生产级能力。6 月 8 个新模型（含 NVIDIA Nemotron 3 Ultra 550B-A55B 首个 MoE hybrid Mamba-Transformer、Claude Opus 4.8、Qwen3.7-Plus）。

## 1. 30 天真实新增模型（`created` 字段排序）

数据源 `https://openrouter.ai/api/v1/models`，created 是 unix 秒级。14d 窗口 8 个新/更：

| created (UTC) | 模型 ID | 提供方 | 模态 | ctx | in/out ($/M) | 备注 |
|---|---|---|---|---|---|---|
| 2026-05-27 12:44 | `anthropic/claude-opus-4.8` | Anthropic | text+image+file → text | 1M | 5/25 | Opus 4.8 主线 |
| 2026-05-27 12:44 | `anthropic/claude-opus-4.8-fast` | Anthropic | text+image+file → text | 1M | 10/50 | 2× 主线价 Fast，moderated=true |
| 2026-05-28 16:17 | `stepfun/step-3.7-flash` | StepFun | text+image+video → text | 256k | 0.20/1.15 | 196B-A11B MoE |
| 2026-05-31 14:36 | `minimax/minimax-m3` | MiniMax | text+image+video → text | 1M | 0.30/1.20 | 自家 M3 |
| 2026-06-03 13:03 | `qwen/qwen3.7-plus` | Qwen | text+image → text | 1M | 0.40/1.60 | Qwen3.7 经济档 |
| 2026-06-04 05:33 | `nvidia/nemotron-3-ultra-550b-a55b` | NVIDIA | text → text | 1M | 0.5/2.5 | **550B-A55B MoE + hybrid Mamba-Transformer** |
| 2026-06-04 05:33 | `nvidia/nemotron-3-ultra-550b-a55b:free` | NVIDIA | text → text | 1M | 0/0 | 免费版 max_completion 16k |
| 2026-06-04 14:04 | `nvidia/nemotron-3.5-content-safety:free` | NVIDIA | text+image → text | 128k | 0/0 | 4B guardrail，fine-tune 自 Gemma-3-4B |

> **5 月 Spotlight 写"20 new model launches"，本表真实 8 个**——前 12 个（Gemini 3.5 Flash / Ring-2.6-1T / CoBuddy / Perceptron Mk1 / GPT Chat Latest 等）created 都不在 14d 窗口，**营销话术放大或批量导入**。**AIGW 不能直接信平台"上月新发 X 个"宣称，要看 created 字段二次验证**。

## 2. 五篇主博客

### 2.1 5/28 · Series B — `openrouter.ai/blog/series-b`

**CapitalG 领投**（Alphabet 独立增长基金），NVentures（NVIDIA VC）+ ServiceNow/MongoDB/Snowflake/Databricks Ventures + AMP PBC + Pace Capital 跟投，a16z / Menlo 老股东跟投。**6 个月周路由量 5T → 25T tokens**（5×），年度 1 quadrillion tokens，**8M+ 开发者 / 400+ 模型**。**6 家战投 = 5 大企业基础设施栈同时下注**（NVIDIA 算力 + ServiceNow 工作流 + MongoDB 数据 + Snowflake 仓 + Databricks lakehouse）。

### 2.2 5/29 · Guardrails — `openrouter.ai/blog/guardrails`（作者 Cailee Moberg）

Workspace 五件套 + 管理 API（`POST /guardrails`）：(1) **Budget**：daily/weekly/monthly reset，per-key + per-member 双层独立，超限 **402 Payment Required**；(2) **ZDR + model/provider restriction**：一键关停保留/训练端点，按 model 或 provider allowlist 锁，**违反 404**（**不是 403**——**故意隐藏端点存在性，防 enumeration attack**）；(3) **Prompt injection defense**：30 条 regex 派生自 OWASP LLM Prompt Injection Prevention Cheat Sheet，**检测在请求出 OpenRouter 之前完成**；(4) **DLP**：7 类内置（**正则近零延迟**）+ 自定义 regex；**姓名/地址走 Presidio NLP**（与 input size 成正比延迟）；(5) **Workspace default guardrail** + per-key/per-member 叠加 guardrails——**只能更严格、不能更宽松**。

> 与 r17 (LiteLLM `safe_merge_extra_body`) 对比：LiteLLM 是 client 防注入；OpenRouter Guardrails 是「**出网关前由网关代用户拦**」+ **402/404 fail-closed 响应码**——**两条独立硬化路径**。

### 2.3 6/1 · May Release Spotlight — `openrouter.ai/blog/may-release-spotlight`（作者 Nick Livermore）

**(a) Speech & Transcription API**：Whisper + GPT-4o Mini Transcribe + Voxtral（STT）；TTS 通过 `supported_voices` 暴露；**provider failover + upstream error handling**——同一 API key 切换多家 STT/TTS。**(b) Model Fusion**：同 prompt 并行打到多模型 + 合成单一更高质量回答；**三种入口：API plugin / server tool / chatroom composer**；**MoA (Mixture of Agents) 进商用网关一等公民**。**(c) Model Comparison Page v2**：5 模型横评，"Highlight best" toggle，**Intelligence / Coding / Agentic** 三类指标——**Agentic 指标 2026 H1 新增**，对应 OTel semconv-genai `#195` A2A 协议属性。**(d) Private Models（Enterprise）**：自有 fine-tuned / dedicated endpoint 通过标准 completions + responses API 暴露，**继承 Guardrails / observability / billing**——OpenRouter 不碰权重只做"路由 + 治理 + 计费"层，差异点 = 400+ 模型同时存在做 fallback。**(e) Workspace Tools 五件套**：(1) **Presets API** 从 inference request body 直接 create / version preset，**新增 Anthropic Messages + Responses skins** + TS/Python SDK；(2) **Human-in-the-loop tools**（与 5/8 博客同主线）：SDK 新类型 `human-in-the-loop`，**agent 自动 resolve 常规 decision + 高 stakes pause 等人**；(3) **Session-id provider stickiness**：同 `session_id` **锁同 provider + 锁同 concrete model**——**目的是提 provider 端 prompt cache 命中率**（与 4/30 Response Caching 互补：prompt cache 在 provider 端，response cache 在 OpenRouter 边缘）；(4) **Auto router `cost_quality_tradeoff`**：**0-10 整数**替代原 binary——**与 r15 Pareto Code Router `min_coding_score` 拼成"连续参数化"**；(5) **Requests tab in logs**：与 generations 同界面，**request ID 过滤 + time picker 简写**（15min / 1h / 3d）。**(f) Coding agent attribution**：Cursor / GitHub Copilot / Cline / RooCode / Kilo Code / Zed / OpenCode **7 个 agent 在 activity log 中正确识别**。

### 2.4 5/8 · Human-in-the-Loop Tools for the Agent SDK — `openrouter.ai/blog/human-in-the-loop-tools`

SDK 引入 `human-in-the-loop` 工具类型。**两个 hook**（pre-call + post-resolution 推断）= agent 自动处理 routine decision，**高 stakes pause 等人**。**零 loop-management 代码**——SDK 内置 state machine。> 与 5/29 Guardrails 网关层互补：**SDK 内 gate = "agent 主动请求"**；**Guardrails = "网关强制 gate"**。

### 2.5 6/4 · Royale: Last Agent Standing — `openrouter.ai/blog/royale-last-agent-standing`（作者 Jacky Liang，第一周作品）

**11 LLM × 30 局 2D Battle Royale**，$482 推理费。**Grok 4.1 Fast**：13 胜，**$0.97/胜**（冠军）。**Claude Sonnet 4.6**：5 胜，**$26.78/胜**（27× cost-per-win 差）。**GPT 5.4**：38 杀（最多），仅 2 胜（"most kills ≠ winner"）。**GPT 5.4-mini / DeepSeek 4 Flash / Kimi K2.6**：3 个共 $57，**0 胜**。**关键发现**：**(a) 「alignment tax」在 zero-sum game 里直接表现为失败**——Sonnet 4.6 4 次主动请求组队在零和里没意义，**8 次 zone death**。**(b) AA benchmark 不能预测 winner**——Grok 在「top-model list 之外」以 27× cost 优势赢 Sonnet 4.6。**(c) xAI Grok "anti-woke" 训练范式**：less filtering + 无 self-check → 自创 car-ramming trick 写进 soul file，30 局沿用。**AIGW 含义**：**routing customer 关心 "right model + right cost for this use case"**，**不是 "best on benchmarks"**——验证 Auto router 0-10 整数比 binary 更贴近客户决策。**没参赛 frontier**（Opus 4.7 / GPT-5.5 / Gemini Ultra）跑 30 局要 ~$3,000。

## 3. SDK / 仓更新节奏

- **`ai-sdk-provider` v2.9.0**（2026-04-28 20:41 UTC）——Vercel AI SDK 适配器，**之后 40 天无新 tag**。同期 commits：dedup tool-call events on trailing-whitespace deltas / opt out `response_format` strict / image URL regex 允许 query string + fragment / preserve empty `reasoning_details` in multi-turn / `VideoModelV3` / Anthropic `eager_input_streaming` / `temperature` model-level config / defensive usage fallback in streaming flush。
- **`go-sdk` v0.4.1**（2026-04-21 21:16 UTC）——之后 **OpenAPI sync bot 每天 1 个 commit**（5/26 → 6/5 累计 15 个 `chore: update OpenAPI spec [sdk-bot]`），**SDK 代码无新发版**。
- **`openrouter-runner`**：**2025-08-21 后无新 release**——OpenRouter 已从 in-house inference 切到「pure routing layer」，Runner 是 deprecated。
- **`agent-skills`**（**新仓**）：`feat: add create-agent skill for building modular AI agents`（1/31 后无新 commit）——对应 5/8 HITL 工具。
- **`docs` 仓**：3/26 初始建仓；OpenRouter 官方文档已迁到 **buildwithfern.com** 渲染，不在 GitHub 主仓维护。

## 4. 与已写轮次的连接

- **r2 / r3 (Helicone / Portkey) release 主题**：本轮对照——**Portkey v1.15.2 后 5 个月不发版 + Helicone 285 天未发 tag** vs **OpenRouter 4 周内 5 篇主博客 + Series B + 8 个新模型**——**两条完全不同的产品节奏**。
- **r23 (agent gateway 6/6)**：本轮 Guardrails = OpenRouter **网关层对应物**——agent gateway 是「数据平面 + 控制平面合一 in-cluster」；OpenRouter Guardrails 是「纯控制平面 + 远端推理 cloud」。
- **r15 (semantic routing)**：OpenRouter `cost_quality_tradeoff` 0-10 整数 = **r15 Pareto Code Router `min_coding_score` 的「商用版」**——连续参数比 binary 更贴近真实生产决策。
- **r17 (guardrails 6/5)**：OpenRouter Guardrails = **r17 (LiteLLM 1.87.x safety / Cisco AI Defense / Anthropic CMA-MCP) 的「网关级 fail-closed 404」**——**402/404 fail-closed 响应码**，**不可注入 enumeration attack 表面**。

## 5. 反常识 / AIGW 硬要求（OR-1~OR-6）

(OR-1) **created 字段 ≠ 营销话术**——5 月 Spotlight 写 20 个新模型，14d created 窗口只能验证 8 个。**AIGW 自部署报表应自建 `created` 字段 ≠ 平台宣称计数**。

(OR-2) **OpenRouter 6 大 enterprise capability 完整闭环**：Guardrails + Private Models + Workspace presets + Session-id stickiness + Auto router + Rankings daily dataset = **「生产 AI 基础设施 6 件套」**——任何 2026 H2 自部署 AI Gateway 都要按这 6 件套对照查 gap。

(OR-3) **Model Fusion + Auto router 0-10 + Pareto Code Router + Session-id stickiness = 4 件套**——r15 vllm-sr PRISM 合法性层 + SIGNAL_GROUP/冲突检测是 in-cluster 版本，**OpenRouter 是云端版本**。**「in-cluster + cloud」两边要 plan 一致升级路径**。

(OR-4) **OpenRouter Guardrails 选 402/404 而非 403**——避免 enumeration attack。**AIGW 自部署要把 403 → 404 替换**，不暴露 allowlist 内容。

(OR-5) **Human-in-the-Loop 工具** = **OpenRouter Agent SDK 把"AI workflow 内嵌 human gate"做成 first-class**——**human gate 在 SDK 层比在网关层更自然**。自部署 AIGW 应在 SDK 层暴露 HITL 工具，**避免 SDK → 网关 → 后端 三段式 human gate 引入 latency**。

(OR-6) **Battle Royale 评测** = **AIGW 选模型需要 "use case benchmark" 而非 "general benchmark"**——Grok 4.1 Fast 在 AA benchmark 不在 top 但在 battle royale 27× 性价比胜出。**AIGW 应暴露 `use_case_benchmark` API**（rankings daily dataset 是雏形，**需扩到 use-case 维度**）。

## 6. 引用与数据来源

- `https://openrouter.ai/api/v1/models`（341 个，2026-06-07 00:19 CST 抓取）
- `https://openrouter.ai/blog/feed.xml`（63 条 RSS，2026-06-07 00:21 CST）
- 5 篇主博客正文：`openrouter.ai/blog/{series-b, guardrails, may-release-spotlight, human-in-the-loop-tools, royale-last-agent-standing}`
- 辅助博客：`openrouter.ai/blog/{response-caching, announcing-audio-apis, april-release-spotlight}`
- `github.com/OpenRouterTeam/ai-sdk-provider/releases/tag/v2.9.0`（2026-04-28 20:41 UTC）
- `github.com/OpenRouterTeam/go-sdk/releases/tag/v0.4.1`（2026-04-21 21:16 UTC）
- `app.buildwithfern.com/?host=openrouter.docs.buildwithfern.com`（docs 渲染栈）
- 前轮 r17 / r23 / r15 报告：`hermes/reports/2026-06-06-*`（已索引）
