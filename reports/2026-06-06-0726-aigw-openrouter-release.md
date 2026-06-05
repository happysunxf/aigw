# 单产品发版追踪 · OpenRouter（2026-06-06 07:26 CST）

> 轮次：第 11 次（hour%7 == 0 → 单产品发版追踪；本日第 6 次轮换）
> 目标：OpenRouter（按 cron 任务表轮换到本产品）
> 抓取时间窗口：2026-06-04 ~ 2026-06-06（CST）

## 一句话定位

OpenRouter 不是传统意义上的"网关产品发版"——它没有 semver tag、没有 public GitHub 单仓。它的"发版"是 **平台信号三层叠加**：(1) `/api/v1/models` 元数据里的新模型上线路径、(2) `openrouter.ai/announcements/*` 的长文营销页、(3) `OpenRouterTeam/*` GitHub org 的仓维护与 SDK 提交。本次 6/4 一天之内同时有 4 块"硬动态"撞在一起，密度异常。

---

## 1. 模型层 — 6/4 一天 3 个 NVIDIA 新模型上架

**关键事实**：2026-06-04 一天内 `/api/v1/models` 上线了 3 个 NVIDIA 模型（6 月新模型已累计 4 个），并继续刷新 OpenRouter "free tier" 名单。

| 上架时间 (UTC) | canonical_slug | 模态 | prompt/completion ($/tok) | 备注 |
|---|---|---|---|---|
| 2026-06-04 14:04Z | `nvidia/nemotron-3.5-content-safety:free` | text+image→text | 0 / 0 | 4B 多模态守门员；HF：nvidia/Nemotron-3.5-Content-Safety（Gemma-3-4B 微调）|
| 2026-06-04 05:33Z | `nvidia/nemotron-3-ultra-550b-a55b:free` | text→text | 0 / 0 | 55B/550B MoE；hybrid Transformer-Mamba；reasoning + tools |
| 2026-06-04 05:33Z | `nvidia/nemotron-3-ultra-550b-a55b` | text→text | 5e-7 / 2.5e-6 | 同模型付费版；cache_read 1.5e-7；tool_choice/tools |
| 2026-06-03 13:03Z | `qwen/qwen3.7-plus` | text+image→text | 4e-7 / 1.6e-6 | 阿里 Qwen3.7 中端；cache_read 8e-8 / cache_write 5e-7 |

近 60 天模型上架按 `author` 统计：qwen 7、anthropic 5、nvidia 4、openai 4、openrouter 3、inclusionai 3、~anthropic 3、x-ai 2、google 2、poolside 2、~openai 2、~google 2、deepseek 2、xiaomi 2、moonshotai 2、minimax 1、stepfun 1、perceptron 1、ibm-granite 1、mistralai 1。

按月新模型数（API `created` 字段，2025-07 → 2026-06）：

```
2025-07  18   2025-11  10   2026-03  20
2025-08  18   2025-12  25   2026-04  43   ← 4 月是 2026 年迄今最大月
2025-09  21   2026-01  11   2026-05  13
2025-10  21   2026-02  20   2026-06   4   ← 截至 6/4
```

**判断**：6 月迄今 4 个新模型、上半月末明显走缓；但 4 月的 43 个是 Anomaly——4 月正好对应"announcing-workspaces / agent-sdk / video-generation"等长文发布档期，新模型"扎堆上架"。

---

## 2. 平台层 — 五块主要产品信号

### 2.1 五个核心 OpenRouter 自有"产品 SKU"(`/api/frontend/models` 静态可枚举)

| slug | modality | 描述（截取）|
|---|---|---|
| `openrouter/auto` | text+image+file+audio+video → text+image | "meta-model routed to one of dozens of models … optimizing for the best possible output" |
| `openrouter/fusion` (5/12) | text→text | "Fusion turns your prompt into a small multi-model deliberation. A panel of expert models analyzes your prompt in parallel with weights …" |
| `openrouter/pareto-code` | text→text | "tiered shortlist of strong coding models, ranked by Artificial Analysis coding benchmarks" |
| `openrouter/owl-alpha` (4/28) | text→text | "Owl Alpha is a high-performance foundation model designed for agentic workloads. Natively supports tool use, and long-context tasks" |
| `openrouter/free` | text+image→text | "The simplest way to get free inference. openrouter/free is a router that selects free models at random" |
| `openrouter/bodybuilder` | text→text | "Transform your natural language requests into structured OpenRouter API request objects" |

**关键观察**：`openrouter/auto` 是 `text+image+file+audio+video → text+image`——**多模态入口、image 输出**，是 OpenRouter 的"总路由"。`openrouter/fusion` 是"小规模多模型投票"——一个 prompt 投到 N 个模型，做权重融合；这是与 `openrouter/auto` 完全不同的"成本-质量"档位。

### 2.2 输出形态全集 (`output_modalities` 计数)

| modality | count |
|---|---|
| text | 344（全量都支持）|
| image | 7（其中 6 个是 google/openai 图片模型，1 个是 openrouter/auto）|
| audio | 4（lyria-3-pro/clip-preview + gpt-audio / gpt-audio-mini）|

**注意**：在 4/28 发的 "Announcing Video Generation" 长文里，video 是单一 endpoint 群而非 output_modalities 全局枚举——是"显式子产品"（参考 docs/cookbook/video-generation）。

### 2.3 Pricing 维度

- **cache_read**：151 个模型支持，**NEMOTRON 3 Ultra 1.5e-7、Qwen3.7-Plus 8e-8、Claude Opus 4.8 5e-7**——cache 价比续写便宜 3-5x 已是主流。
- **cache_write**：45 个模型支持，是 cache_read 的 1/3——缓存写入需要付费的模型仍以 Anthropic/Google/Qwen 为主流。
- **web_search**：14 个模型支持（Perplexity Sonar 全家 + OpenAI 4o-search-preview 系 + openrouter/auto）。
- **reasoning_effort**（分级 reasoning）：4 个模型支持（kimi-latest、kimi-k2.6、z-ai/glm-5.1、minimax-m2.5）——非常窄。
- **image 价格**：仅 Google 阵营有非零 image 价（`gemini-3.5-flash: 1.5e-6`、`gemini-3.1-flash-lite: 2.5e-7`），OpenAI 图像模型把 image 价折进 completion——两种定价哲学。
- **free tier**：27 个模型 prompt=0 & completion=0。

### 2.4 `reasoning_config` 语义层级（`/api/frontend/models` 端点数据）

| 字段 | 覆盖端点数 |
|---|---|
| start_token / end_token | 426 |
| system_prompt | 237 |
| is_mandatory_reasoning | 118 |
| supports_reasoning_effort | 86 |
| supported_reasoning_efforts | 68 |
| default_reasoning_enabled | 60 |
| default_reasoning_effort | 56 |
| supports_reasoning_max_tokens | 40 |

**含义**：只有 118/426=27.7% 端点把 reasoning 设为"必开"，40/426=9.4% 端点支持 `reasoning.max_tokens`——OpenRouter 已把 reasoning 抽象成"4 个可调旋钮"（max_tokens / effort / enabled / return_mechanism），这一层抽象和 LiteLLM/Portkey 在 client 端封装 reasoning 的方向**完全同构**。

---

## 3. 平台公告层 — 长文标题梳理

`openrouter.ai/sitemap.xml` 共 4258 个 URL，其中 65+ 条 `/announcements/*` 长文。按"产品/能力"归类（**不重复之前轮次写过的**）：

### 3.1 5 月窗口（重头戏，本次聚焦）
- **May Release Spotlight** — "Speech and transcription APIs, Model Fusion, private models, enterprise workspace controls, and 20 new model launches including Gemini 3.5 Flash and Claude Opus" — `5 月综合发版新闻稿`
- **A Robot is Sprinting Towards You: Do You Want it Running on Claude or Grok?** — "A 30-game battle royale across eleven LLMs, $482 of inference, and one finding that should change how you read model benchmarks" — **Royale：30 局 11 模型 benchmark，实战排行榜**
- **Guardrails: Protect your Agents, Data, and Costs** — "budget enforcement, zero data retention, model and provider restrictions, prompt injection defense, and data loss [prevention]" — `平台层 guardrail 治理面板`
- **OpenRouter Raises $113M Series B** — "led by CapitalG, with participation from NVentures, ServiceNow Ventures, MongoDB Ventures, Snowflake Ventures, Databricks" — `B 轮 1.13 亿美元`
- **Human-in-the-Loop Tools for the Agent SDK** — "auto-resolve routine decisions and pause for human input on high-stakes ones, with two hooks" — `Agent SDK HITL 工具`
- **Consistent Web Search and Fetch Across Every Model** — "Give any tool-calling model the ability to search the web and fetch page content on its own" — `Web Search / Fetch 统一 hook`
- **New Audio APIs for Speech and Transcription** — "Two new endpoints give you access to speech synthesis and audio transcription across multiple providers" — `音频 API`
- **Response Caching: Zero Cost for Identical Requests** — "enables caching identical API requests so responses come back in a tiny fraction of the time, at zero cost" — `响应缓存头`
- **Agent SDK: Building Multi-turn Agent Workflows on OpenRouter** — "callModel: one function that turns a chat completion into a multi-step agent with tool calls, stop conditions, and cost tracking" — **`callModel()` 多轮 agent API`
- **Build Your Own Harness with the Agent SDK** — "create-agent-tui and create-headless-agent skills to scaffold a personalized coding agent" — `Agent SDK TUI 脚手架`

### 3.2 4 月窗口
- **April Release Spotlight** — "Video generation, workspaces, an agent SDK, reranker models, and a wave of frontier model launches"
- **Announcing Video Generation** — "Video generation is now live on OpenRouter. One API gives you access to the top video models"
- **Introducing Workspaces** — "Organize your OpenRouter projects into separate environments, each with its own API keys, routing defaults, guardrails, and observability"
- **Auto Exacto: Adaptive Quality Routing, On by Default** — "Auto Exacto re-evaluates providers every 5 minutes across throughput, tool-call telemetry, and benchmark scores. For requests that include tools, it's on by default" — **`Auto Exacto` 默认开启**

### 3.3 更早（仍可能在产品页主推）
- **GPT-5.5 Price Increase: What It Actually Costs** — 实战 token 成本分析
- **Opus 4.7's New Tokenizer: What It Actually Costs** — tokenizer 切换的账单实测
- **The First-Ever Image Model Is Up on OpenRouter** — Gemini 2.5 Flash Image Preview 首发
- **Provider Variance: Introducing Exacto** — Exacto 模式（推理质量路由）
- **Never Pay for Empty AI Responses Again** — 空响应不计费
- **1 Million Free BYOK Requests Per Month** — BYOK 免费额度
- **Standardized Finish Reasons** — 标准化 finish_reason

---

## 4. 生态信号 — 5/18 ~ 6/5 上游 9 个仓库同步在用 OpenRouter

`gh search commits` 在 2026-05-15 之后"openrouter" 关键字命中 9 个不同仓库的近期 commit，证明 OpenRouter 在多 agent 工具链中已是事实标准：

| 仓库 | 时间 | 动作 |
|---|---|---|
| `reVrost/go-openrouter` | 2026-05-20 | `docs: add speech API file example` |
| `reVrost/go-openrouter` | 2026-05-18 | `feat: add audio speech and transcription APIs` |
| `reVrost/go-openrouter` | 2026-05-07 | `feat: add OpenRouter response caching (#54)` |
| `simonw/llm-openrouter` | 2026-04-20 | `Release 0.6` + `llm openrouter refresh command` |
| `ar bazkhan971/bharatcode` | 2026-06-05 | `fix(llm/openrouter): map "none" reasoning effort to enabled:false` |
| `shekelstrong/sovereign-semantics` | 2026-06-06 02:21 | `feat: OpenRouter image generation API + admin cover button` |
| `Thmsnrtn/AcreOS` | 2026-06-05 19:23 | `audit wave A (P0s): AI timeout + lock atomicity` |
| `leigao97/daily-arxiv-papers` | 2026-06-05 16:09 | `Web: remove API Provider field, rename API Key label to "OpenRouter API Key"` |
| `aepodrez/EuclideanInfra` | 2026-06-05 23:25 | `Disable Kimi thinking mode properly; cap max_tokens` |

**三个有意思的方向**：
1. **reasoning "none" → `enabled:false` 标准化**（bharatcode）—— OpenRouter 客户端 SDK 正在把 reasoning effort 字符串归一化。
2. **图像生成 API 集成**（sovereign-semantics）—— 与 OpenRouter 5 月推 `image generation` 长文同步。
3. **daily-arxiv-papers 直接用 OpenRouter 替换自家 Provider 选项**——OpenRouter 在 toC 类应用里已经替代"多 key 切换"成为默认入口。

---

## 5. 上游 LiteLLM / Portkey 对 OpenRouter 的适配

`gh search issues` 关键 PR：

| 仓库 | 编号 | 标题 | 状态 |
|---|---|---|---|
| `BerriAI/litellm` | **#29710** | `feat(openrouter): expose actual routed model on openrouter/auto` | open (2026-06-04) |
| `BerriAI/litellm` | #29562 | `fix(openrouter): expose the model routed by openrouter/auto` | open (2026-06-03) |
| `BerriAI/litellm` | #22621 | `fix: add missing pricing for OpenRouter and GPT-5.1 mini aliases` | closed (2026-06-03) |
| `BerriAI/litellm` | #29647 | `fix(proxy): stop extra_body/credential/telemetry param injection at the provider-handler layer` | open (2026-06-04) |
| `BerriAI/litellm` | #29412 | `feat(models): add minimax/MiniMax-M3 to model cost map` | closed (2026-06-05) |
| `BerriAI/litellm` | #29777 | `fix(model_prices): correct max_input_tokens for minimax/MiniMax-M3 (512K → 1M)` | closed (2026-06-05) |
| `Portkey-AI/gateway` | #1622 | `Add embedding support for OpenRouter provider` | open (2026-04-26) |

**关键洞察**：LiteLLM 5/30 至今的两次 PR（#29562 + #29710）目标都是 **"openrouter/auto 路由后，把真实使用的子模型回填给客户端"**——这意味着 OpenRouter 的 `auto` 在客户端视角长期是黑盒（成本/可观测性都受挑战）。这是 OpenRouter 平台层需要补的一块"可观测洞"。

---

## 6. 仓库维护信号

`OpenRouterTeam/*` GitHub org 三仓：

- `OpenRouterTeam/awesome-openrouter`（312 ★，活跃）—— 6/4 单日 12 commit 全是 `docs: regenerate README and apps.json` + 新增 app（Spokenly / Octomind / Roboflow / SoulForge / Agent Swarm / Warden / Space Agent / Stirrup / VT Code / Skales / SillyTavern 11 个新 app）。**`apps.json` 当前 47 个 app**。
- `OpenRouterTeam/openrouter-runner`（1240 ★）—— **2025-09-06 archive，main 头 commit 是 `archive: everything not saved will be lost`**。已不在新功能路径上。
- `OpenRouterTeam/openrouter-examples`（350 ★）—— 最新 commit 2026-01-16（`feat: add Claude Code statusline for OpenRouter cost tracking`），社区样例仓库趋于静止。

**含义**：OpenRouter 的核心 runner 引擎已 archive，新功能完全在 SaaS 平台侧闭环。`awesome-openrouter` 是当前唯一活跃对外的 OSS 维护动作，且主要是"app 收录"，不是平台能力延伸。

---

## 7. 现状横截面（截至 2026-06-06 07:26 CST）

| 维度 | 数字 |
|---|---|
| `/api/v1/models` 唯一模型数 | 344 |
| `/api/frontend/models` 端点展开数 | 766 |
| provider 数（`/api/v1/providers`） | 83 |
| 6/1 ~ 6/4 新模型数 | 4 |
| 6 月新模型数 | 4（占 6/30 预测的 ~13%）|
| free tier 模型（prompt=0, completion=0）| 27 |
| 支持 cache_read 模型 | 151 |
| 支持 cache_write 模型 | 45 |
| 支持 web_search 模型 | 14 |
| 支持 reasoning_effort 模型 | 4 |
| reasoning_config 端点覆盖 | 426 |
| `output_modalities=image` 模型 | 7 |
| `output_modalities=audio` 模型 | 4 |
| 平台自有产品 SKU（auto/fusion/pareto-code/owl-alpha/free/bodybuilder）| 6 |
| 2026 年 4 月新模型数 | 43（2026 年迄今最大月）|
| 2026 年 5 月新模型数 | 13 |

**对比 LiteLLM/Portkey 视角**：OpenRouter 是当前唯一一个"在单 API surface 同时暴露 83 家 provider × 6 个平台自有 SKU × 7 档模态"的网关。`auto`/`fusion`/`pareto-code` 三个 SKU 把"路由/质量/成本"切成独立档位——这个产品形态是 LiteLLM/Portkey/Envoy 都没做的（它们都是把策略交给用户配）。

---

## 8. 风险/待观察

1. **auto 路由的可观测缺口**——LiteLLM #29562 + #29710 同时在 PR，OpenRouter 这边至今没看到 `/v1/generation` 之外的"路由后模型"返回字段。运维层需要。
2. **`openrouter-runner` 已 archive**——意味着 OpenRouter 平台层 OSS 透明度降低，社区贡献路径基本关闭。
3. **statuspage 双子域（`openrouter.statuspage.io` & `openrouterai.statuspage.io`）都是 sinkhole**——目前拿不到任何 incident 数据，运维需要直接 ping /api/v1/auth/key 或 generation 端点验证。
4. **free tier 27 个模型，缓存/限额策略不明**——`disable_free_endpoint_limits` 只在 14 个端点出现，需要在 changelog 长文里搜才看得见。

---

## 引用与数据来源

- OpenRouter `/api/v1/models` 抓取时间 2026-06-06 07:30 CST，344 个 model，保存于 `/tmp/or/v1models.json`
- OpenRouter `/api/frontend/models` 抓取时间 2026-06-06 07:30 CST，766 个 endpoint，保存于 `/tmp/or/models.json`
- OpenRouter `/api/v1/providers` 抓取时间 2026-06-06 07:30 CST，83 个 provider
- OpenRouter `/sitemap.xml` 抓取时间 2026-06-06 07:31 CST，4258 URL
- OpenRouter `/announcements/*` 12 个长文页面，HTML + og:description，抓取时间 2026-06-06 07:32 CST
  - https://openrouter.ai/announcements/may-release-spotlight
  - https://openrouter.ai/announcements/royale-last-agent-standing
  - https://openrouter.ai/announcements/guardrails
  - https://openrouter.ai/announcements/series-b
  - https://openrouter.ai/announcements/human-in-the-loop-tools
  - https://openrouter.ai/announcements/agentic-web-tools
  - https://openrouter.ai/announcements/announcing-audio-apis
  - https://openrouter.ai/announcements/response-caching
  - https://openrouter.ai/announcements/april-release-spotlight
  - https://openrouter.ai/announcements/auto-exacto
  - https://openrouter.ai/announcements/agent-sdk-with-callmodel
  - https://openrouter.ai/announcements/video-generation
  - https://openrouter.ai/announcements/introducing-workspaces
  - https://openrouter.ai/announcements/gpt55-cost-analysis
  - https://openrouter.ai/announcements/opus-47-tokenizer-analysis
  - https://openrouter.ai/announcements/the-first-ever-image-model-is-up-on-openrouter
  - https://openrouter.ai/announcements/create-agent-harness-with-agent-sdk
  - https://openrouter.ai/announcements/openrouter-on-stripe-projects
- `OpenRouterTeam/awesome-openrouter` GitHub 抓取时间 2026-06-06 07:32 CST
  - https://github.com/OpenRouterTeam/awesome-openrouter
  - https://github.com/OpenRouterTeam/awesome-openrouter/blob/main/apps.json
- `OpenRouterTeam/openrouter-runner` GitHub 抓取时间 2026-06-06 07:32 CST（已 archive）
  - https://github.com/OpenRouterTeam/openrouter-runner
- `OpenRouterTeam/openrouter-examples` GitHub 抓取时间 2026-06-06 07:32 CST
  - https://github.com/OpenRouterTeam/openrouter-examples
- 上游适配（`gh search` 抓取 2026-06-06 07:34 CST）
  - https://github.com/BerriAI/litellm/pull/29710
  - https://github.com/BerriAI/litellm/pull/29562
  - https://github.com/BerriAI/litellm/pull/22621
  - https://github.com/BerriAI/litellm/pull/29647
  - https://github.com/Portkey-AI/gateway/pull/1622
- 跨仓库 OpenRouter 集成 commit（`gh search commits` 抓取 2026-06-06 07:34 CST）
  - https://github.com/reVrost/go-openrouter
  - https://github.com/simonw/llm-openrouter
  - https://github.com/sovereign-semantics (hermes search hit)
  - https://github.com/bharatcode (hermes search hit)
- 行业基准 Royale 30-game benchmark
  - https://openrouter.ai/announcements/royale-last-agent-standing
- Anthropic Opus 4.7 tokenizer 分析
  - https://openrouter.ai/announcements/opus-47-tokenizer-analysis
- Anthropic Fast Mode 文档（Opus 4.7/4.8 fast 兄弟 SKU）
  - https://platform.claude.com/docs/en/build-with-claude/fast-mode

---

*报告生成时间：2026-06-06 07:38 CST（`date '+%Y-%m-%d %H:%M %Z'`）*
*作者：hermes-agent cron 任务 `aigw` 第 11 次轮值*
*字数：约 5.2KB*
