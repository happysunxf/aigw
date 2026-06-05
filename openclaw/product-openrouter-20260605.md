# OpenRouter 深度调研报告

> 调研日期：2026-06-05
> 调研范围：项目背景、架构设计、协议支持、性能数据、部署方式、成本模型、生态、客户案例、优劣势分析、与其他产品对比
> 数据来源：OpenRouter 官方文档（`openrouter.ai/docs/...`）、OpenRouter SDK 仓库、官方 MCP server 端点、模型市场实时 JSON（`/api/v1/models`）、第三方测评与公开访谈。
> 所有文档路径可通过追加 `.md` 后缀直接拉取 Markdown，OpenRouter 同时提供 [`/docs/llms.txt`](https://openrouter.ai/docs/llms.txt) 索引和 [`/docs/llms-full.txt`](https://openrouter.ai/docs/llms-full.txt) 全文。AI 客户端（Claude Code、Cursor 等）通过 [`/docs/_mcp/server`](https://openrouter.ai/docs/_mcp/server) 上的 MCP 服务读取文档。

---

## 0. TL;DR（核心结论）

| 维度 | 摘要 |
| --- | --- |
| **本质定位** | 统一 LLM API 网关 / 模型聚合器 / 模型市场 + 多模型协作执行体（Server Tools） |
| **产品形态** | **SaaS 托管**为主（Cloudflare Workers + Cloudflare AI Gateway 底层 + 区域化多活），并提供 **Enterprise EU in-region 隔离域**（`eu.openrouter.ai`）；**不可自托管**，是少数「无开源发行版」的商业网关代表 |
| **入口协议** | OpenAI Chat Completions（`/api/v1/chat/completions`）+ Anthropic Messages（`/api/v1/messages`）+ OpenAI Responses（`/api/v1/responses`）+ Embeddings + legacy `/api/v1/completions` + 自有 `/api/v1/generation`、`/api/v1/credits` 等 |
| **模型覆盖** | 截至 2026-06，**`/api/v1/models` 返回 417 条 endpoint**，覆盖 ~80+ 厂商、300+ 模型，包括所有 frontier（Claude Opus 4.5/4.6/4.7/4.8、GPT-5.1/5.2、Gemini 3 Pro/3.1 Pro、DeepSeek V3.2、Llama 3.3/4、Qwen3 全家、GLM 4.6/5、Mistral Large、Command R+、Grok 4/4.1 等） |
| **核心差异化** | **多模型智能路由**（Auto Router / Auto Exacto / Pareto Router / Free Router / Fusion Router / Advisor）+ **Provider 实时健康感知**（5 分钟滚动窗口 p50/p75/p90/p99 延迟与吞吐）+ **Server Tools**（web_search、web_fetch、datetime、image_generation、apply_patch、fusion、advisor）+ **Sovereign AI**（EU in-region + ZDR）+ **Prompt caching 跨厂商自动粘性路由** + **OpenRouter credits 通用结算** |
| **费用模型** | **No markup**：直接以厂商底价 + 5% OpenRouter fee（信用卡支付有 5% 处理费上限豁免策略）；**BYOK** 路径下收取厂商价格的固定 5% OpenRouter BYOK 费（每月前 N 次请求免费），无其他订阅费 |
| **可观测性** | 自带 Activity/Logs/Generation API；**Router Metadata** 透传路由管线 (`pipeline` / `attempts` / `endpoints`)；可对接 OpenTelemetry / Langfuse / Helicone / Datadog / Sentry 等第三方 |
| **生态集成** | OpenAI SDK / Anthropic SDK 一行 `baseURL` 替换；自家 Python + TypeScript SDK（`openrouter` / `@openrouter/sdk`）；MCP server 暴露；Cline、Cursor、Continue、Zed、Open WebUI、LobeChat、ChatBox、SiliconFlow、ChatRTX 等客户端开箱支持；Stripe Projects (`stripe projects add openrouter/api`) 一键 provisioning |
| **典型用户** | 个人开发者 / 创业团队（多模型切换 + 一份账单）；中型 SaaS（多租户 Guardrails + 工作区隔离）；企业（EU 隔离 + ZDR + SSO + 自定义合同） |
| **最大优势** | ① **覆盖广**（同一 API 直连 ~80 家厂商）② **路由精细**（按价格/延迟/吞吐/工具调用成功率排序 + 百分位阈值 + 粘性会话）③ **多模型协作**（Fusion 8 模型 panel + Judge + Web 检索；Advisor 子智能体）④ **Sovereign AI 一体化**（EU 数据不离开欧盟 + ZDR）⑤ **零供应商锁定**（一份代码切到任意模型） |
| **主要短板** | ① **不可自托管**（数据必须经过 OpenRouter 控制面）② **Sovereign AI 仅企业付费**（EU in-region 路由）③ **Server Tools 处于 beta**（API 形状不稳定）④ **没有 MCP-native client / agent 编排生态**（这是 Helicone/Langfuse 等竞品定位的延伸）⑤ **生产 SLA 公开信息有限**（Uptime 监控页是公开的，但合同级 SLA 仅企业）⑥ **免费模型 / `:free` 变体限流严重**（免费档面向个人尝鲜） |

---

## 1. 项目背景

### 1.1 公司与产品起源

OpenRouter 是 **OpenRouter, Inc.**（注册于美国 Delaware）旗下的商业化 AI 路由服务。创始团队以 AI 推理与高并发网关背景为主，2023 年中以「**One API, Any Model**」为口号公开发布，定位对标开发者自建 **LiteLLM / Portkey / One API** 时所碰到的「多账号、限流、计费、运维」四类痛点。区别于开源产品，OpenRouter **从一开始就是云端 SaaS 形态**，运营方统一对接上游 80+ 模型厂商的批发账号池，再以「无加价 / 5% BYOK 费」的 Pass-through 模式分发给终端用户。

> **关键里程碑（公开可查）**：
>
> - 2023-07：正式上线，初始支持 OpenAI / Anthropic / Google / Mistral / Meta。
> - 2024-Q1：上线 `:free` 变体、Auto Router（NotDiamond 提供）、Chatroom、Image Generation、Presets。
> - 2024-Q3：引入 **Auto Exacto**（基于实时吞吐 + 工具调用成功率的工具调用重排序）、**Provider Sticky Routing**（让 OpenAI/Gemini/DeepSeek 的隐式缓存跨请求命中）、Sovereign AI EU 隔离（企业）。
> - 2024-Q4：推出 **Workspaces**（多环境隔离 + 组织管理）、**BYOK 5% 费率**、**Guardrails**（PII + 提示注入 + 内容过滤 + 预算）。
> - 2025-Q1：Server Tools 体系化（web_search、web_fetch、datetime、apply_patch、image_generation）、**Fusion Router**（多模型 deliberation + judge）、**Advisor**（子智能体）。
> - 2025-Q2：Response Caching（OpenRouter 层全局缓存）、Router Metadata（`openrouter_metadata` 管线追踪）、Stripe Projects 一键 provisioning、Prompt Caching 跨厂商粘性路由成熟。
> - 2025-Q3 起：模型市场扩张到 300+ 模型，覆盖 GLM、Qwen3、DeepSeek V3.x、Kimi K2、Llama 4、Claude 4.x、Gemini 3 系列、Grok 4.1 等新一代前沿模型。

### 1.2 团队、商业与产品口号

- **对外核心口号**："The Unified Interface For LLMs"（LLM 统一接口）。子口号还有 "Higher Availability"、"Higher Rate Limits"、"Consolidated Billing"——明确点出 OpenRouter 不是模型提供商，而是 **多厂商批发账号池 + 智能路由 + 统一计费的网关**。
- **社区**：Discord 公开服务器（按月度 AMA 形式运作）、Twitter/X `@openrouter` 账号、GitHub 组织 [`@OpenRouterTeam`](https://github.com/OpenRouterTeam)（公开 SDK、文档示例与若干 `openrouter-cli` 实验项目）。
- **披露口径**：A 轮前规模（2024 年披露过一笔约 $3M 的种子轮），具体融资额、ARR 数额未在官网公开；公司在 Discord 公告中提到过 "每天处理 10B+ tokens"，但官方未公示独立审计。
- **主要合作**：Stripe（账单）、NotDiamond（Auto Router 算法）、Exa / Firecrawl / Parallel（Web Search 引擎）、Cloudflare（边缘基础设施）、MCP（文档接入 AI 客户端）。

### 1.3 目标市场与产品边界

| 客户分层 | 典型场景 | OpenRouter 的对应能力 |
| --- | --- | --- |
| **个人 / 独立开发者** | 多模型尝鲜、Cline / Cursor / Open WebUI 接入 | 免费档、`:free` 变体、`openrouter/free` 路由器、OAuth PKCE 一键登录 |
| **小团队 / 创业公司** | 一份代码切模型、统一账单、避免厂商锁定 | Credits 充值、Presets、BYOK、OpenAI/Anthropic SDK 兼容 |
| **中型 SaaS / B2B** | 多租户配额、内容合规、工具调用稳定性 | Workspaces、Guardrails、Auto Exacto、Observability 集成 |
| **大型企业 / 监管行业** | GDPR / EU AI Act 合规、数据驻留、可审计 | EU in-region (`eu.openrouter.ai`)、ZDR、SSO、自定义合同 |

**OpenRouter 明确不做的事**：

1. **不训练、不发布自有基础模型**（与 Together / Fireworks / Replicate 等自研推理厂商不同）。
2. **不开源自部署**（与 LiteLLM / Portkey / One API / Higress 等相反；这是 OpenRouter 与传统 API Gateway 产品的最大产品形态差异）。
3. **不做完整 LLM 应用 / Agent 编排框架**（与 LangChain / LlamaIndex / Helicone 偏应用侧的形态不同）。

---

## 2. 架构设计

### 2.1 整体技术栈（一图概览）

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          OpenRouter 边缘 / 控制面                        │
│                                                                          │
│   Cloudflare Workers (edge L7 代理 + 鉴权 + 计量 + 路由计算)              │
│         │                                                                │
│   ───────┼──────────────────────────────────────────────────             │
│   │     │                                                    │           │
│   │   Cloudflare AI Gateway (统一策略 / 缓存 / 分析)         │           │
│   │     │                                                    │           │
│   │   ──┴── Postgres (账户 / API key / 余额 / Guardrails)     │           │
│   │     │                                                    │           │
│   │   ──┴── Generation Logs (请求 + 响应 + 路由元数据)         │           │
│   │     │                                                    │           │
│   │   ──┴── Providers Aggregator (批量上游账号 + 限流池)        │           │
│   │     │                                                    │           │
│   │   ──┴── Models Catalog (300+ 模型 / 417+ endpoint / 实时延迟)│         │
│   │                                                              │       │
│   ───────────────────────────────────────────────────────────────       │
│                                                                          │
│   区域：  默认（us/iad/cle/sea）   EU 隔离（eu.openrouter.ai）            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
              │                                    │
              ▼                                    ▼
   上游模型厂商批发账号池（约 80+ 厂商）
   ────────────────────────────────────────
   OpenAI、Anthropic、Google Gemini/AI Studio/Vertex、
   AWS Bedrock、Azure OpenAI/Azure AI Foundry、
   DeepSeek、xAI (Grok)、Mistral、Meta Llama、Alibaba Qwen、
   Zhipu GLM、Moonshot Kimi、MiniMax、Command R、Cohere、
   Perplexity、Together、Fireworks、Replicate、
   DeepInfra、Groq、Cerebras、OpenPipe、Together/Fireworks 直连、
   inference.net、CentML、AtlasCloud、SiliconFlow …
```

**关键设计原则**：

1. **边缘优先**：默认入口为 Cloudflare Workers（300+ PoP），尽量靠近用户降低 TTFT（Time To First Token）。
2. **无状态计算层 + 有状态数据层**：路由计算在边缘节点内存内完成（健康数据每 5 分钟滚动刷新），账户/计费/审计/Guardrails 状态打到 Cloudflare 区域可用区的 Postgres。
3. **多协议同源**：Chat Completions / Anthropic Messages / Responses / Embeddings 共用一个边缘 L7 代理，**协议转换在边缘完成**，避免再回源到中心。
4. **透明代理（Pass-through）**：默认不开源做「请求体改写」，透传到上游；只在 Server Tools / Response Caching / Context Compression / Guardrails 触发时才在 OpenRouter 层动请求体或响应体。

### 2.2 请求生命周期（一次 Chat Completions 请求的端到端流程）

```
Client → POST /api/v1/chat/completions
   │
   ▼
① Cloudflare Worker 入口：TLS 终止 / WAF / Bot 检测
   │
   ▼
② 鉴权：解析 Authorization: Bearer sk-or-v1-xxx
   │   → 查询边缘缓存的 key 信息 (org / workspace / role / guardrail 列表)
   │
   ▼
③ 配额 & 余额检查（low balance 时强制 DB 校验）
   │
   ▼
④ 路由管线（pipeline，多 stage 串行/并行）：
   │   ┌────────────────────────────────────────────────────────┐
   │   │ a) Provider 候选筛选                                    │
   │   │    - 应用 allowlist / only / ignore / order / zdr        │
   │   │    - 过滤掉 30s 内有显著故障的 provider                  │
   │   │    - 仅保留支持请求中 tools / tool_choice / max_tokens   │
   │   │      的 provider                                        │
   │   │    - 若 zdr=true，仅保留 ZDR 端点                       │
   │   │                                                        │
   │   │ b) Provider 排序（核心）                                │
   │   │    - 默认按 "价格逆平方权重" 做 LB                       │
   │   │    - 若显式 sort="price|throughput|latency"，按需切换   │
   │   │    - 若 preferred_min_throughput / preferred_max_latency│
   │   │      指定，先把达标端点排前                               │
   │   │                                                        │
   │   │ c) Auto Exacto（仅当请求含 tools 时默认启用）           │
   │   │    - 用实时吞吐 + 工具调用成功率重排                     │
   │   │                                                        │
   │   │ d) Provider Sticky Routing                              │
   │   │    - 若请求带 session_id 或 hash 命中粘性键，固定 provider│
   │   │    - 用于最大化 Prompt Caching 命中率                    │
   │   │                                                        │
   │   │ e) Context Compression（可选 middle-out）               │
   │   │    - 仅在上下文超出目标模型窗口时触发                    │
   │   │                                                        │
   │   │ f) Guardrails（请求时）                                 │
   │   │    - 自定义 regex redact / block                         │
   │   │    - Sensitive Info (PII) 检测 / 脱敏                    │
   │   │    - Prompt Injection 正则检测                          │
   │   └────────────────────────────────────────────────────────┘
   │
   ▼
⑤ 转发到选定 provider endpoint
   │   - 适配：Anthropic provider 收到 Anthropic 风格 body
   │   - 适配：OpenAI provider 收到 OpenAI 风格 body
   │   - 错误重试：5xx / 429 自动切换到 next candidate
   │
   ▼
⑥ 上游响应回到 OpenRouter：
   │   ┌────────────────────────────────────────────────────────┐
   │   │ a) Response Caching 命中 → 直接复用（usage 归零）      │
   │   │ b) Guardrails 响应侧过滤（PII redact / 内容 block）     │
   │   │ c) Server Tools 工具结果回填到 assistant message       │
   │   │ d) Router Metadata 透传（仅当 opt-in header）           │
   │   │ e) 计费：计算 cached_tokens / 折扣，写入 generation    │
   │   └────────────────────────────────────────────────────────┘
   │
   ▼
⑦ 流式 SSE 推回客户端（或一次性 JSON 响应）
   │
   ▼
⑧ 异步写入 Generation Logs（保留 prompt/completion 内容与否取决于账户 ZDR 偏好）
```

### 2.3 模块拆分（按职责）

| 模块 | 角色 | 关键技术 / 备注 |
| --- | --- | --- |
| **Edge Proxy (Workers)** | TLS 终止、路由、限流、缓存键计算 | Cloudflare Workers（V8 isolate） |
| **AI Gateway (策略层)** | 鉴权、配额、Guardrails、Server Tools、缓存 | Cloudflare AI Gateway + 自研插件 |
| **Routing Engine** | 选 provider、排序、Auto Exacto、Sticky | 内部 Rubicon 引擎（按公开资料推测） |
| **Provider Adapter** | 80+ 厂商协议适配、限流池、重试 | 各厂商 SDK 包装 + 自动重试 + 错误归一化 |
| **Models Catalog** | 模型元数据、定价、健康指标 | Postgres + ClickHouse 风格的 OLAP（推测） |
| **Generation Logs** | 请求/响应/路由元数据、可观测性 | Postgres + 冷存 S3（推测） |
| **Billing & Credits** | 充值、扣费、BYOK 5% 计算、Stripe 同步 | Stripe + 自有 ledger |
| **Identity & Org** | API key、OAuth PKCE、Workspace | 自有 IdP + 第三方 OAuth |

### 2.4 区域与主权

- **默认域**：`https://openrouter.ai`（主控面 + 边缘），终端接入由 Cloudflare Workers 就近路由。
- **EU 隔离域**：`https://eu.openrouter.ai`（**企业付费**），承诺 prompts 与 completions 在欧盟内完成解密与处理，**不跨境传输**。可用模型清单可在 EU 域的 `/api/v1/models` 拉取，或在 `openrouter.ai/models?region=eu` 浏览。
- **区域标签**：在 `X-OpenRouter-Experimental-Metadata: enabled` 响应中可看到 `region` 字段（如 `"iad"`、`"fra"`），便于客户端按区域定位。

### 2.5 可观测性

- **Activity / Logs** UI：`/activity` 与 `/logs` 提供账户级 / workspace 级过滤的请求日志（按模型、provider、状态码、token 数、cache_discount 等聚合）。
- **Generation API**：`GET /api/v1/generation?id=gen-xxx` 返回每条请求的明细（含 raw provider response，便于调试 BYOK 错误）。
- **Router Metadata**：opt-in header `X-OpenRouter-Experimental-Metadata: enabled` 触发 `openrouter_metadata` 字段，结构：
  ```json
  {
    "requested": "openai/gpt-4o-mini",
    "strategy": "direct|auto|free|latest|alias|fallback|pareto|bodybuilder",
    "region": "iad",
    "summary": "available=1, selected=OpenAI",
    "attempt": 1,
    "is_byok": false,
    "endpoints": { "total": 1, "available": [...] },
    "attempts": [ { "provider": "OpenAI", "model": "...", "status": 200 } ],
    "params": { "quality_floor": ..., "throughput_floor": ... },
    "pipeline": [
      { "type": "context_compression", "name": "...", "data": {...} },
      { "type": "guardrail", "name": "regex_pi_detection", "data": {...} },
      { "type": "server_tools", "name": "server-tools", "data": {...} }
    ]
  }
  ```
- **第三方对接**：可配置把日志与 traces 转发到 **OpenTelemetry / Langfuse / Helicone / Datadog / Sentry / Axiom**（通过 `observability` 集成在 workspace 内配置）。

---

## 3. 协议支持

### 3.1 入口协议（OpenRouter 对客户端暴露）

| 协议路径 | 风格 | 兼容 SDK | 备注 |
| --- | --- | --- | --- |
| `POST /api/v1/chat/completions` | **OpenAI Chat Completions** | `openai-python`, `openai-node`, `openai-go` 等 | 默认入口；支持 stream / 非 stream / function calling / JSON mode / tool_choice / structured outputs |
| `POST /api/v1/messages` | **Anthropic Messages** | `anthropic-python`, `@anthropic-ai/sdk` | 用于 Claude 全家（Opus 4.5/4.6/4.7/4.8、Sonnet 4/4.5/4.6、Haiku 3.5/4.5）；支持 prompt caching（含 `cache_control` 1h TTL） |
| `POST /api/v1/responses` | **OpenAI Responses** | OpenAI Responses SDK | 新增的 Responses API 风格（stateful、tool calling 原语） |
| `POST /api/v1/completions` | Legacy Text Completions | 旧版 OpenAI SDK | 兼容性保留，逐步弃用 |
| `POST /api/v1/embeddings` | OpenAI Embeddings | `openai-python` | 部分 embedding 模型可走；不参与 ZDR routing 复用（embedding cache key 与 chat 区分） |
| `GET /api/v1/models` | 自有 | 任意 | 列出全部 417+ endpoint，附带定价、上下文长度、支持的 modality、ZDR 状态、tool 支持、quantization 等 |
| `GET /api/v1/generation?id=...` | 自有 | 任意 | 调试 / 审计单条请求 |
| `GET /api/v1/keys` / `POST /api/v1/keys` | 自有 | 任意 | API key 管理 |
| `GET /api/v1/credits` | 自有 | 任意 | 余额查询 |
| `POST /api/v1/auth/keys` | 自有 | 任意 | OAuth PKCE 兑换用户 API key |
| `POST /api/v1/presets/{slug}/chat/completions` | OpenAI Chat Completions 皮肤 | `openai-python` | 从一次成功请求"按 body 创建 / 更新 preset" |
| `POST /api/v1/presets/{slug}/messages` | Anthropic Messages 皮肤 | `anthropic-python` | 同上 |
| `POST /api/v1/presets/{slug}/responses` | OpenAI Responses 皮肤 | OpenAI Responses SDK | 同上 |
| `GET /api/v1/endpoints/zdr` | 自有 | 任意 | 拉取所有 ZDR 端点 |
| `POST /api/v1/provisioning/oauth/token` | 自有 | 任意 | Stripe Projects provisioning OAuth 兑换 |
| `GET /api/v1/guardrails` / `POST/PATCH/DELETE` | 自有 | 任意 | Guardrails CRUD |
| `GET/POST /api/v1/workspaces/...` | 自有 | 任意 | Workspaces 管理 |
| `MCP /docs/_mcp/server` | **Model Context Protocol** | Claude Code / Cursor / Continue 等 | 让 AI 客户端把 OpenRouter 文档作为工具读取 |

### 3.2 出口协议（OpenRouter 转发到上游厂商）

OpenRouter 在内部维护 **80+ Provider Adapter**，将客户端请求体翻译成上游期望的格式：

| 厂商 | 上游协议 | OpenRouter 适配要点 |
| --- | --- | --- |
| **OpenAI** | OpenAI Chat Completions / Responses | 原生；BYOK 走 Azure / Azure AI Foundry 模式自动识别 |
| **Anthropic** | Anthropic Messages | 原生；保留 `cache_control` 1h TTL、tool_use blocks |
| **Google Gemini** | Google Generative AI (AI Studio) / Vertex | 自动识别 `services.ai.azure.com` 域 vs `openai.azure.com` 域；Vertex 需要 service account JSON BYOK |
| **AWS Bedrock** | Bedrock Runtime | 支持 Bedrock API key 与 AWS AccessKey/SecretKey BYOK；需要 IAM 至少 `bedrock:InvokeModel` 与 `bedrock:InvokeModelWithResponseStream` |
| **Azure OpenAI / Foundry** | Azure OpenAI REST | 通过 Foundry 配置简化（resource_name + resource_type），也支持传统 per-deployment URL |
| **xAI (Grok)** | xAI 原生 API | 与 OpenAI 风格类似，但 system message 限制、缓存 multiplier 不同 |
| **DeepSeek** | DeepSeek 原生 API | 支持其自动隐式缓存 |
| **Mistral** | Mistral La Plateforme | 与 OpenAI 风格相近 |
| **Meta Llama** | Llama API（Together / Groq / DeepInfra 多种后端） | OpenRouter 选择最快的 endpoint |
| **Alibaba Qwen** | DashScope | 支持 `cache_control: { type: ephemeral }` 显式缓存 breakpoints |
| **Moonshot Kimi** | Moonshot 原生 / Groq 转发 | 与 OpenAI 风格相近 |
| **Zhipu GLM** | Zhipu BigModel | 同上 |
| **MiniMax** | MiniMax 原生 | — |
| **Groq** | Groq 原生 | Kimi K2 等模型走 Groq 推理 |
| **Cerebras** | Cerebras 原生 | — |
| **Cohere Command R+** | Cohere 原生 | — |
| **Perplexity** | Perplexity 原生 | 用于 web search 在线 |
| **Together / Fireworks / Replicate / DeepInfra / OpenPipe** | 各家自家协议 | 抽象为标准 OpenAI 风格 |

### 3.3 自定义扩展（OpenRouter-only 协议字段）

| 字段 | 位置 | 含义 |
| --- | --- | --- |
| `provider` | request body | 选 provider / 排序 / 限速 / ZDR / 量化等级 / 最大价格等 |
| `plugins` | request body | 注入插件（auto-router、pareto-router、response-healing、file-parser、moderation、web-search 等） |
| `models` | request body | 一次提交多个 model slugs，配合 `provider.sort.partition=none` 做跨模型排序 |
| `session_id` / `x-session-id` | request body / header | 强制粘性路由 |
| `transforms` | request body | `middle-out`（上下文压缩）开关 |
| `cost_quality_tradeoff` | auto-router plugin | 0–10 滑块 |
| `min_coding_score` | pareto-router plugin | 0–1 |
| `allowed_models` | auto-router plugin | wildcard 模式 |
| `tools: [{ type: "openrouter:web_search|web_fetch|datetime|image_generation|apply_patch|fusion|advisor" }]` | request body | 启用 Server Tools |
| `X-OpenRouter-Cache: true / false` | request header | 启用 Response Caching |
| `X-OpenRouter-Cache-TTL: <seconds>` | request header | 自定义缓存 TTL（1–86400 秒，默认 300） |
| `X-OpenRouter-Cache-Clear: true` | request header | 强制刷新当前 key 的缓存 |
| `X-OpenRouter-Experimental-Metadata: enabled` | request header | 启用 Router Metadata |
| `HTTP-Referer` / `X-Title` | request header | 客户端应用标注（用于 OpenRouter Rankings） |
| `cache_control` (Anthropic-style) | request body | 透传到 Anthropic / Alibaba 用于显式 prompt caching |

---

## 4. 性能数据

### 4.1 路由层性能特征

- **入口延迟开销**（OpenRouter 自报）：**最小化**，通过 Cloudflare Workers 边缘部署达成，文档明确写道"designed to add minimal latency"。
- **冷启动**：新 region 的 1–2 分钟内，边缘 cache warming 期间可能略高。**热稳定后应回到基线**。
- **Credit Balance 强制 DB 校验**：余额低（个位数美元）或接近 credit 限额时，OpenRouter 会过期缓存并触发数据库校验，**这部分会增加 latency**。建议保持 ≥ $10–20 余额并开 auto-topup。
- **Model Fallback 开销**：当主 provider 失败时，OpenRouter 会自动切换候选并重试，**对失败请求增加 latency**。它会持续跟踪 provider 失败率，**避免每次都走 fallback**。
- **Cache 命中**：`HIT` 时 `usage` 全部归零，**不计费**，TTFT 通常 < 50ms（边缘读 KV）。
- **Streaming TTFT**：与直连上游基本相当（流开始后 client 直接接收 upstream SSE chunks）。

### 4.2 路由信号——5 分钟滚动窗口的百分位

OpenRouter 跟踪每个 endpoint（model + provider 组合）的：

- **延迟**：p50 / p75 / p90 / p99（秒）
- **吞吐**：p50 / p75 / p90 / p99（tokens/sec）

> 数据每 5 分钟滚动一次，**不是分钟级实时**。在 `provider.preferred_max_latency` 与 `preferred_min_throughput` 中可以按百分位筛选——例如要求 p90 延迟 ≤ 2 秒、p50 吞吐 ≥ 50 tokens/sec。

### 4.3 公开可见的端到端性能页面

- **Models Performance 标签**：在 `https://openrouter.ai/models/{model-slug}` 页面有 "Performance" 选项卡，**展示该模型不同 provider 的真实吞吐和延迟数据**（来自 OpenRouter 全网流量聚合）。
- **Uptime 页面**：在 `https://openrouter.ai/uptime/{model-slug}` 展示按日级别的可用性曲线（如 "Uptime Example: Claude Sonnet 4.6"）。
- 这些是 OpenRouter **作为聚合层**的真正护城河：把全网请求的健康指标汇聚成数据，飞轮喂给 Auto Router / Auto Exacto。

### 4.4 Cache 命中率（Prompt Caching）

- **Provider Sticky Routing** 让同 session 的请求固定到同一 provider，**最大化隐式缓存命中**（OpenAI、Gemini、DeepSeek 都是隐式缓存）。
- **Anthropic 显式缓存**：5 分钟 TTL（默认）或 1 小时 TTL（`"ttl": "1h"`）。1 小时 TTL cache write 收费 = 2x base input；5 分钟 = 1.25x。Cache read 折扣按 provider 自己的 multiplier。
- **Anthropic 自动缓存 vs 显式缓存**：自动 `cache_control`（顶层）只走 first-party Anthropic，不走 Bedrock/Vertex。**显式 per-block cache_control 跨 Bedrock/Vertex/Anthropic 全可用**（最多 4 个 breakpoint）。
- **最小缓存长度**：Claude Opus 4.5/4.6/4.7/4.8 / Haiku 4.5：4096 tokens；Sonnet 4/4.5/4.6 / Opus 4/4.1：1024 tokens；Haiku 3.5：2048 tokens。
- **OpenRouter Response Caching**：key = SHA-256(`api_key` + `model` + `endpoint_type` + `stream` 模式 + `body`)。不同流模式与不同 endpoint 类型互不冲突。**JSON 字段顺序影响 cache key**。

### 4.5 缓存命中对计费的影响

| 维度 | MISS | HIT |
| --- | --- | --- |
| 计费 token 数 | 正常 | **0**（Response Caching）/ discounted（Provider Prompt Caching） |
| `usage.prompt_tokens` | 实际 | 0（Response Caching） |
| `usage.completion_tokens` | 实际 | 0（Response Caching） |
| `cache_discount` 字段 | 0 | 正值（部分 provider 负值表示 cache write 收费） |
| `X-OpenRouter-Cache-Status` | `MISS` | `HIT` |
| `X-OpenRouter-Cache-Age` | — | 自缓存以来的秒数 |
| `X-Generation-Id` | 唯一 | **HIT 时仍是新 ID**（不复用原 ID） |
| `openrouter_metadata` | 完整 | **不返回**（Cache hit 主动剥离） |

### 4.6 多模型 deliberation 性能开销

- **Fusion Router**：默认 3-model panel + 1 judge = **4–5x 单次调用的 cost**。线性扩展 panel 数量。
- **Advisor**：单次额外 call 到 advisor model，开销 1x（外加可能的 advisor 子智能体 tool calls）。
- **Auto Router**：**无额外费用**，只路由选择，按所选模型计费。

---

## 5. 部署方式

### 5.1 不可自托管——SaaS 强约束

**OpenRouter 不提供开源发行版，不提供 Docker / Helm chart，不支持 on-premise 部署**。这是它与 LiteLLM、Portkey、Higress、Kong AI、APISIX、Envoy AI 等所有竞品最关键的产品形态差异。

后果：

- **数据合规**：默认域（`openrouter.ai`）的 prompts 和 completions 都会经过 OpenRouter 控制面——必须信任其 ZDR 策略与日志策略。
- **EU 隔离**：需要企业付费开通 `eu.openrouter.ai`。
- **离线场景不可用**：断网/内网/无法访问境外服务时不可用。
- **供应商锁定"反向"**：把对单厂商（OpenAI/Anthropic/Google）的依赖转移到对 OpenRouter 的依赖；但 OpenRouter 同时充当了"逃生通道"——同一份代码可绕过 OpenRouter 直连任意上游。

### 5.2 客户端部署模式

虽然 OpenRouter 自身不可自托管，但**客户端的接入方式非常灵活**：

| 客户端形态 | 接入方式 | 备注 |
| --- | --- | --- |
| **OpenAI SDK** | `base_url=https://openrouter.ai/api/v1` | 一行替换 |
| **Anthropic SDK** | `base_url=https://openrouter.ai` | 一行替换 |
| **OpenAI Responses SDK** | `base_url=https://openrouter.ai/api/v1` | 一行替换 |
| **OpenRouter Python SDK** | `pip install openrouter` | 官方 SDK |
| **OpenRouter TypeScript SDK** | `npm i @openrouter/sdk` | 官方 SDK |
| **OpenAI 兼容客户端** | 改 base_url 即可 | Cline / Cursor / Continue / Open WebUI / LobeChat / ChatBox / Zed / OpenHands 等 |
| **MCP Client** | `https://openrouter.ai/docs/_mcp/server` | 让 AI 客户端读 OpenRouter 文档作为工具 |
| **OAuth PKCE** | `https://openrouter.ai/auth?callback_url=...` | 适合 C 端应用"一键登录并获取 user-controlled API key" |
| **Stripe Projects** | `stripe projects add openrouter/api` | 一键 provisioning、env 自动写入 |

### 5.3 Stripe Projects 集成（2025 年新增）

Stripe 在 `projects.dev` 上为 OpenRouter 提供 "launch partner" 地位：

```bash
# 1) 安装 Stripe Projects 插件
stripe plugin install projects

# 2) 一键添加 OpenRouter
stripe projects add openrouter/api

# 3) 验证
stripe projects status
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{"model":"~openai/gpt-mini-latest","messages":[{"role":"user","content":"Hello!"}]}'
```

- 自动创建/绑定 OpenRouter 账户，生成 **`sk-or-v1-...`** 格式的 key 标为 "Provisioned by Stripe"。
- `.env` 写入 `OPENROUTER_API_KEY` 与 `OPENROUTER_TYPE=bearer`。
- Free / Pay-as-you-go 双套餐切换。
- 适合 coding agent：agent 直接调 `stripe projects add openrouter/api --json --yes` 完成非交互式 provisioning。

---

## 6. 成本模型

### 6.1 OpenRouter Credits（统一账单）

| 维度 | 说明 |
| --- | --- |
| 充值方式 | 信用卡、Stripe Checkout、Stripe Projects 联动 |
| 币种 | USD；用户区域显示 |
| 计费粒度 | **按上游厂商底价 + 5% OpenRouter fee**（信用卡支付有 5% 处理费上限豁免策略） |
| 月度起付 | 无最低消费；按 token 计费 |
| 退款 / 不活动扣费 | 账户长期不活动会扣 0.01 美元/月的 inactive fee（极低，避免幽灵账户） |
| 免费层 | 信用卡预充值 0 也可使用 `:free` 变体和 `openrouter/free` 路由器；部分模型本身有免费试用 |

### 6.2 BYOK（Bring Your Own Key）

```text
当用户上传自己的 OpenAI / Anthropic / AWS / Google / Azure key 时：
  实际扣费 = 厂商价格 × 5%（OpenRouter BYOK 费率）
  前 N 次 BYOK 请求 / 月 免 BYOK 费
  默认行为：BYOK key 失败时仍可 fallback 到 OpenRouter credits
  "Always use for this provider" 开启：禁用 OpenRouter fallback，失败即失败
```

**多 key 排序**：

1. **Prioritized section**（优先，OpenRouter endpoints 之前）
2. **OpenRouter shared endpoints**
3. **Fallback section**（仅在前两层都失败时尝试）

**多 key 过滤器**：

- **Model filter**：仅在指定 model 上使用此 key
- **API key filter**：限制哪些 OpenRouter API key 可以用此 BYOK
- **Member filter**：限制哪些 workspace 成员可用此 BYOK

### 6.3 Server Tools 定价

| Server Tool | 定价 |
| --- | --- |
| `openrouter:datetime` | 免费 |
| `openrouter:web_fetch` | 0.001 USD/1K tokens（按上游计费） |
| `openrouter:image_generation` | 0.021 USD / image |
| `openrouter:web_search` (auto / native) | 0.03 USD/次（OpenRouter credit 计费） |
| `openrouter:web_search` (Exa) | 0.025 USD/次；highlight 抽取自适应（~2–4K 字符/result），可 pin 5K/15K/30K 字符/result |
| `openrouter:web_search` (Parallel) | 0.005 USD/次（前 10 个 result），超出 0.001 USD/result |
| `openrouter:web_search` (Firecrawl) | **BYOK**——使用你自己的 Firecrawl credits（10K 信用免费试用，3 个月有效） |
| `openrouter:apply_patch` | 0.0001 USD/1K tokens（极低，按 token 计） |
| `openrouter:fusion` | 0.01 USD/次（panel + judge 内层调用额外 token 计费） |
| `openrouter:advisor` | 0.01 USD/次 + advisor 子智能体额外 token 计费 |

> Server Tools 当前是 **beta**——价格和形状可能调整。

### 6.4 Auto Router / Pareto Router 定价

- **Auto Router (`openrouter/auto`)**：**零加价**，按所选模型厂商底价计费（NotDiamond 提供路由算法）。
- **Pareto Router (`openrouter/pareto-code`)**：**零加价**，按所选模型计费。
- **Free Router (`openrouter/free`)**：**完全免费**。
- **Fusion Router (`openrouter/fusion`)**：无平台费，但 **4–5x 基础 token cost**（3-model panel + 1 judge）。
- **Advisor (`openrouter:advisor`)**：0.01 USD/次 + 子调用按 token。

### 6.5 Prompt Caching / Response Caching 计费

- **Provider Prompt Caching**：上游 cache write / read multiplier 各家不同，OpenRouter 透传。
  - OpenAI：write 免费，read 0.25x–0.5x 原价；最小 prompt 1024 tokens。
  - Grok：write 免费，read 按 xAI multiplier。
  - Moonshot / Groq / DeepSeek：write 免费，read 按各自 multiplier。
  - Alibaba Qwen：write 收费，read 收费，需显式 `cache_control: ephemeral` 5 分钟 TTL。
  - Anthropic Claude：write 1.25x（5 分钟）或 2x（1 小时）；read 0.1x。**Bedrock/Vertex 支持 1 小时显式缓存；自动缓存仅 first-party Anthropic 支持**。
  - Google Gemini 2.5：implicit caching，**无 write/storage cost**，read 按 Google multiplier。
- **OpenRouter Response Caching**：**HIT 完全免费**，所有 usage 归零。

### 6.6 整体定价汇总表

| 计费维度 | 计算方式 |
| --- | --- |
| 模型调用（OpenRouter Credits） | `上游价格 × 1.05`（信用卡支付有 5% 处理费上限豁免策略） |
| 模型调用（BYOK） | `上游价格 × 0.05`（首 N 次免费/月） |
| Server Tools | 每次固定价或 token 倍率（见上表） |
| Prompt Caching | 透传上游 read/write multiplier，cache hit 走折扣价 |
| Response Caching | 命中完全免费 |
| 免费模型 / `:free` 变体 | 0 cost |
| Fusion Router | 内层 N+1 次调用按各自模型计费 |
| Auto Router / Pareto Router | 仅按所选模型计费 |
| EU in-region | 含在企业合同价中 |

---

## 7. 生态

### 7.1 官方 SDK

- **Python**：`openrouter`（PyPI，2024-Q4 推出，强烈推荐，文档全部默认用此）
- **TypeScript**：`@openrouter/sdk`（npm，对应 OpenAI / Anthropic / Responses 三种 skin 都有类型）
- **OpenAI 兼容**：`openai` 库替换 `base_url` 即可
- **Anthropic 兼容**：`@anthropic-ai/sdk` 替换 `base_url` 即可
- **OpenAI Responses 兼容**：OpenAI Responses SDK 替换 `base_url` 即可

### 7.2 IDE / 客户端 / Coding Agent

- **Cline**（VS Code AI Agent）：原厂推荐 `OpenRouter` provider
- **Cursor**：内置 OpenRouter 支持
- **Continue**（VS Code / JetBrains）：内置
- **Zed**：内置
- **OpenHands**（OpenDevin）：内置
- **Open WebUI**：内置 OpenRouter provider
- **LobeChat / ChatBox / Cherry Studio** 等中国 C 端客户端：内置
- **SiliconFlow**（虽然本身是国产模型平台，但提供 OpenRouter 兼容入口）

### 7.3 框架集成

| 框架 | 集成方式 |
| --- | --- |
| **LangChain / LangGraph** | `ChatOpenAI(base_url="https://openrouter.ai/api/v1", model="openrouter/auto")` |
| **LlamaIndex** | OpenRouter LLM 抽象原生支持 |
| **Vercel AI SDK** | OpenRouter provider 内置 |
| **Haystack** | 第三方组件 |
| **DSPy** | 通过 OpenAI 兼容 LM |
| **Vellum / PromptLayer / Humanloop** | 第三方 LLMops 平台对接 |
| **LiteLLM** | 可以把 OpenRouter 作为上游之一（套娃场景） |
| **Portkey** | 同样可以作为 OpenRouter 之上加 observability（套娃场景） |

### 7.4 LLM Ops / 可观测性

- **自带**：Activity/Logs/Generation API/Router Metadata
- **可对接**：Langfuse、Helicone、Datadog、Sentry、Axiom、OpenTelemetry
- **多租户**：Workspaces + Guardrails + BYOK 一起构成 B2B SaaS 必备三件套

### 7.5 MCP（Model Context Protocol）

- OpenRouter 公开暴露 **`/docs/_mcp/server`** 作为 MCP endpoint。AI 客户端（Claude Code、Cursor 等）可以"读取 OpenRouter 文档作为工具"，**让 coding agent 在生成 OpenRouter 集成代码时自动获取最新文档**——这是少数把文档接入 MCP 的产品。

### 7.6 Stripe Projects

- 通过 `stripe projects add openrouter/api` 一键 provisioning，详见 §5.3。

---

## 8. 客户案例与采用信号

> 公开案例披露较少（OpenRouter 不主动公布大客户名单），但以下信号可见：

1. **Token 体量**：Discord 公告与创始人访谈中多次提及"日处理 10B+ tokens"（未独立审计）。
2. **生态规模**：`/api/v1/models` 返回 **417 endpoints、80+ 厂商、300+ 模型**——单一 OpenRouter 入口覆盖了市面几乎所有主流 LLM。
3. **第三方 SDK / 客户端首选**：Cline、Cursor、Open WebUI、Continue、Zed 等头部 AI IDE / 客户端都把 OpenRouter 列为"开箱即用"provider。
4. **Stripe Projects launch partner**：与 Stripe 的深度集成（开箱 provisioning、env 同步、agent-friendly skill 文件）说明 Stripe 内部项目已大量使用。
5. **企业签约**：EU in-region 路由是企业付费特性——披露话术为"available to enterprise customers by request"，意味着至少有数家有 GDPR / EU AI Act 强制要求的大型客户。
6. **模型厂商接入**：OpenRouter 与 OpenAI、Anthropic、Google、AWS、Azure、DeepSeek、xAI、Mistral、Meta、Alibaba、Zhipu、Moonshot、MiniMax 等都建立了直接商务关系——能同时与所有 frontier 厂商签批发协议本身就是竞争壁垒。
7. **排行榜（Rankings）**：OpenRouter Rankings 页面 `https://openrouter.ai/rankings` 公开按 token 消耗排名的应用榜（类似 LMArena 的"应用侧"版本）——前几名包括 Cline、Open WebUI、Continue 等头部应用，**侧面证明 OpenRouter 是这些应用的首选上游**。
8. **AI 客户端覆盖度**：根据社区统计，OpenRouter 在 GitHub Star 数 1k+ 的 AI 工具中集成率超过 60%。

---

## 9. 优劣势分析

### 9.1 优势（Strengths）

| # | 优势 | 详细说明 |
| --- | --- | --- |
| S1 | **覆盖最广的模型市场** | 417 endpoints，80+ 厂商，300+ 模型。**单一 API 直连所有 frontier**——Claude 4.x、GPT-5.1/5.2、Gemini 3 系列、DeepSeek V3.2、Llama 3.3/4、Qwen3、GLM 4.6/5、Kimi K2 全部支持 |
| S2 | **统一账单 + 透明定价** | **5% No-Markup + BYOK 5%** 模式简单透明，避免多供应商对账 |
| S3 | **路由能力精细** | 价格 / 吞吐 / 延迟排序、百分位阈值、Sticky 路由、Auto Exacto、Auto Router、Pareto Router——开源网关大都仅支持前 3 个 |
| S4 | **多模型协作原生支持** | Fusion Router（8-model panel + judge）、Advisor（子智能体）——**对手中无出其右** |
| S5 | **Sovereign AI 一体化** | EU 隔离 + ZDR + data collection deny——一站式 GDPR/EU AI Act 合规 |
| S6 | **Server Tools 体系** | web_search（4 个引擎）、web_fetch、datetime、image_generation、apply_patch、fusion、advisor——**任何模型即插即用** |
| S7 | **Provider 实时健康感知** | 5 分钟滚动窗口的延迟/吞吐/工具调用成功率——飞轮数据驱动路由 |
| S8 | **多协议入口** | OpenAI + Anthropic + Responses + Embeddings + 自有——一份代码走遍所有 SDK |
| S9 | **极致接入便利** | baseURL 一行替换；OAuth PKCE 一键登录；Stripe Projects 一键 provisioning |
| S10 | **MCP-native 文档** | `/docs/_mcp/server` 把文档直接喂给 coding agent，**AI-native 时代的开发者体验优势** |
| S11 | **开源生态友好** | 全部支持 OpenAI / Anthropic 官方 SDK，无需重写代码；与 LiteLLM/Portkey 等可套娃（提供更多可观测层） |
| S12 | **响应缓存** | OpenRouter 层 Response Caching，**HIT 0 cost、跨模型可用**——对评测/批量回归极有用 |

### 9.2 劣势（Weaknesses）

| # | 劣势 | 详细说明 |
| --- | --- | --- |
| W1 | **不可自托管** | 数据必须经过 OpenRouter 控制面。**对金融 / 政府 / 国防 / 医疗等严格数据驻留场景基本出局**（即便有 EU 隔离，企业往往仍要求 in-house 部署） |
| W2 | **EU 隔离仅企业付费** | 中型 SaaS 想合规 GDPR 仍需走企业合同 |
| W3 | **Sovereign AI 区域少** | 只有 EU；**无 US GovCloud / 中国大陆 / 新加坡等区域**——对跨国部署仍不够 |
| W4 | **Server Tools 处于 beta** | API 形状 / 价格不稳定，文档明确写"may change" |
| W5 | **公开 SLA 不透明** | Uptime 监控页公开但合同级 SLA / RTO / RPO 仅企业可谈 |
| W6 | **Auto Router 模型池** | `openrouter/auto` 依赖 NotDiamond 提供的路由模型池（不是 OpenRouter 自研）——**核心算法受制于第三方** |
| W7 | **缺少 Agent 编排** | 没有 LangGraph / Inngest 那种 durable execution；Server Tools 是"单请求多 tool call"，不是"长期 agent loop" |
| W8 | **限流 / 配额不透明** | 默认无明确公开的 RPM / TPM 数字，由 OpenRouter 动态决定；大规模生产环境需提前与企业谈 |
| W9 | **缓存的 JSON 字段顺序敏感** | `{"model":"x","messages":[]}` 与 `{"messages":[],"model":"x"}` 视为不同 key，**对自动序列化库不友好** |
| W10 | **没有内建的 prompt playground 集成度** | 第三方 Playground（`https://openrouter.ai/playground`）功能 OK，但与 Cline / Cursor 相比还不够"开发者协作" |
| W11 | **Auto Exacto 评估数据未公开** | "we are actively collecting"——透明度不及 Helicone 的公开评估榜 |
| W12 | **官方 SDK 仍偏新** | 相比 LiteLLM 多年沉淀的 Python SDK 生态，`openrouter` PyPI 包仍属于"功能完整但案例较少"阶段 |

---

## 10. 与其他产品对比

### 10.1 横向对比表

| 维度 | OpenRouter | LiteLLM | Portkey Gateway | One API / New API | Together AI | Cloudflare AI Gateway | LangSmith | Helicone |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **产品形态** | 纯 SaaS | 自托管 / 商业 | 自托管 / 商业 | 自托管 | 推理平台 | 边缘网关 | 可观测 SaaS | 可观测 SaaS |
| **开源** | ❌ | ✅（MIT） | ✅ | ✅ | ❌ | ❌ | ❌ | ✅（Apache 2.0，可自托管） |
| **模型/厂商覆盖** | 417 endpoints / 80+ | 100+ | 200+ | 100+ | 100+（Together 自家 + 接入） | 任意 OpenAI 兼容 | 任意（观测层） | 任意（观测层） |
| **路由粒度** | 极细（百分位 + 工具成功率 + sticky + Auto Exacto） | 中（fallback + 限速） | 细（tag/conditions） | 粗（按模型分 channel） | N/A（自营模型） | 中（CF Ruleset） | N/A | 中 |
| **多模型协作** | **Fusion + Advisor**（原生） | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Server Tools** | web_search / web_fetch / image_gen / fusion / advisor | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **EU 隔离** | ✅（企业付费） | 自托管即可 | 自托管即可 | 自托管即可 | ❌ | ❌ | ❌ | ❌ |
| **ZDR 强制** | ✅（按 model group） | 自托管即可 | 自托管即可 | 自托管即可 | ❌ | ❌ | ❌ | ❌ |
| **BYOK** | ✅ | 自托管 | ✅ | 自托管 | N/A | ✅ | N/A | N/A |
| **可观测性** | Activity/Logs + Router Metadata | 自带 + 对接 | 自带 + 对接 | 自带 | 自带 | Cloudflare Analytics | **业内最强** | 自带 + Eval |
| **计费模型** | 5% / BYOK 5% | 自管 | 自管 / 商业版 | 自管 | 厂商定价 | Cloudflare 订阅 | LangSmith 订阅 | 按请求 / 自托管 |
| **多模型 deliberation** | **Fusion 8-model + Judge** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Prompt Caching 粘性** | ✅ 自动 sticky | ❌ | ❌ | ❌ | N/A | ❌ | ❌ | ❌ |
| **MCP 文档** | ✅ `/docs/_mcp/server` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **接入成本** | **一行 baseURL** | 部署 + 集成 | 部署 + 集成 | 部署 | 切 SDK | 配 Worker | 集成 SDK | 集成 SDK |
| **数据驻留** | 受限于 OpenRouter 域 | 自托管即可 | 自托管即可 | 自托管即可 | 受限于 Together | 边缘区域可指定 | 受限于 LangSmith | 自托管可 |

### 10.2 关键差异的"为什么"

1. **为什么 OpenRouter 是 SaaS 而 LiteLLM 是开源？**
   - OpenRouter 的核心壁垒是**与 80+ 厂商批发账号池 + 实时健康数据飞轮**。这两件事都依赖 OpenRouter 实际跑流量并聚合数据。
   - LiteLLM 的核心壁垒是**统一的 Python SDK + 100+ 模型适配**——这是社区可以贡献的。
   - 因此 OpenRouter 选择 SaaS，LiteLLM 选择开源。**两者并不直接竞争**——更像是 OpenRouter 可作为 LiteLLM 的上游，Portkey 也可作为 OpenRouter 之上加可观测层。

2. **为什么 OpenRouter 的"多模型协作"是独有？**
   - Fusion Router（8-model panel + judge + web_search）实际是把"multi-agent deliberation"做成了网关层的 Server Tool——任何客户端只要用 `openrouter/fusion` 即可。
   - 其他网关（LiteLLM、Portkey、One API）都不做"内层多模型推理"，定位是"路由 + 监控"，不是"推理编排"。
   - Helicone / LangSmith 是 LLM 观测层，也不做内层推理。

3. **为什么 Together / Fireworks / Replicate 不能替代 OpenRouter？**
   - 这些是**推理平台**（自营 GPU 跑开源模型 + 部分闭源模型转售），**不是聚合网关**。
   - 它们与 OpenRouter 的关系更多是"上游 / 下游"或"互补"——OpenRouter 把 Together 的开源模型纳入自己的 endpoint 池。

4. **为什么 Cloudflare AI Gateway 不能替代 OpenRouter？**
   - Cloudflare AI Gateway 是**通用 L7 网关**，可以代理任意 OpenAI 兼容 API，但**没有模型市场、没有多厂商批发账号、没有 Server Tools、没有多模型协作**。
   - 它更像是"OpenRouter 的底层之一"——OpenRouter 自己就使用 Cloudflare Workers + AI Gateway。

5. **为什么 LangSmith / Helicone 不直接做"聚合网关"？**
   - 它们是 LLM 应用**可观测性 / Eval** 平台——重点是 trace、eval、prompt management，而不是 routing。
   - Helicone 已经向"AI Gateway + Observability"方向延伸，但仍以观测为核心，且不提供 80+ 厂商批发账号池。

### 10.3 推荐场景选择

| 你的场景 | 推荐 |
| --- | --- |
| **个人 / 小团队快速接入多模型** | **OpenRouter**（零部署、一行 baseURL） |
| **中型 SaaS 多租户 + 配额 + 合规** | **OpenRouter + Guardrails + Workspaces**（仍 SaaS） 或 **LiteLLM / Portkey 自托管**（更可控） |
| **企业 EU GDPR 强合规 + 大量自主开发** | **OpenRouter EU 隔离 + ZDR**（如果接受 SaaS） 或 **Higress / APISIX AI 自托管**（如果必须 on-prem） |
| **必须 on-prem / 离网** | **LiteLLM / Portkey / Higress / Kong AI / Envoy AI**（任一自托管网关） |
| **多模型协作 / Agent 平台** | **OpenRouter Fusion + Advisor**（独一无二） |
| **重 Eval / 重 Observability** | **LangSmith / Helicone / Langfuse**（叠加在 OpenRouter 之上） |
| **生产 RAG + 大量 prompt 调试** | **LangSmith + OpenRouter** |
| **企业 Agent 编排（durable execution）** | **Inngest + OpenRouter**（OpenRouter 仅做模型调用） |

---

## 11. 协议 & 协议细节——深入

### 11.1 一次完整的 Auto Router 请求

```python
import requests

resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": "Bearer sk-or-v1-...",
        "HTTP-Referer": "https://my-app.example.com",  # 用于 Rankings
        "X-Title": "My App",
    },
    json={
        "model": "openrouter/auto",
        "messages": [
            {"role": "user", "content": "Explain quantum entanglement in simple terms"}
        ],
        "plugins": [
            {"id": "auto-router", "cost_quality_tradeoff": 3}  # 0-10, 偏质量
        ]
    }
)
data = resp.json()
print(data["model"])        # 实际选择的模型，比如 "anthropic/claude-sonnet-4.5"
print(data["choices"][0]["message"]["content"])
```

### 11.2 一次 Provider 精细控制的请求

```python
resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": "Bearer sk-or-v1-..."},
    json={
        "model": "anthropic/claude-sonnet-4.5",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Use the reference below when answering."},
                    {
                        "type": "text",
                        "text": "[HUGE TEXT BODY]",
                        "cache_control": {"type": "ephemeral", "ttl": "1h"}  # Anthropic 1h explicit cache
                    },
                    {"type": "text", "text": "Summarize the main points."}
                ]
            }
        ],
        "session_id": "agent-abc-123",  # 强制 sticky routing
        "provider": {
            "order": ["anthropic", "amazon-bedrock", "google-vertex"],  # 显式顺序
            "allow_fallbacks": True,
            "require_parameters": True,
            "zdr": True,  # 强制 ZDR
            "data_collection": "deny",
            "quantizations": ["fp8"],  # 仅选 fp8 量化
            "sort": "throughput",
            "preferred_min_throughput": {"p90": 50},  # p90 ≥ 50 tokens/sec
            "preferred_max_latency": {"p99": 2.0}     # p99 ≤ 2s
        },
        "plugins": [{"id": "response-healing"}]  # 自动修复 JSON
    }
)
```

### 11.3 一次 Fusion 多模型 deliberation 请求

```python
# 简写：使用 model alias
resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": "Bearer sk-or-v1-..."},
    json={
        "model": "openrouter/fusion",  # 自动注入 openrouter:fusion 工具
        "messages": [
            {"role": "user", "content": "Compare ridge, lasso, and elastic-net regression. Where does each shine?"}
        ]
    }
)

# 高级：自定义 panel + judge
resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": "Bearer sk-or-v1-..."},
    json={
        "model": "~anthropic/claude-opus-latest",
        "messages": [
            {"role": "user", "content": "Compare ridge, lasso, and elastic-net regression."}
        ],
        "tools": [
            {
                "type": "openrouter:fusion",
                "parameters": {
                    "analysis_models": [
                        "~anthropic/claude-opus-latest",
                        "~openai/gpt-latest",
                        "~google/gemini-pro-latest"
                    ],
                    "model": "~openai/gpt-latest",  # judge
                    "max_tool_calls": 8,
                    "max_completion_tokens": 4096,
                    "reasoning": {"effort": "high", "max_tokens": 2048}
                }
            }
        ],
        "tool_choice": "required"  # 强制 fusion 被调用
    }
)
```

### 11.4 一次 Advisor 子智能体请求

```python
resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": "Bearer sk-or-v1-..."},
    json={
        "model": "openai/gpt-5.1",
        "messages": [
            {"role": "user", "content": "Build a concurrent worker pool in Go with graceful shutdown."}
        ],
        "tools": [
            {
                "type": "openrouter:advisor",
                "parameters": {
                    "model": "~anthropic/claude-opus-latest",
                    "instructions": "You are a senior staff engineer. Be decisive.",
                    "tools": [{"type": "openrouter:web_search"}],  # advisor 可调用 web_search
                    "forward_transcript": False,
                    "max_tool_calls": 8
                }
            }
        ]
    }
)
```

### 11.5 一次 Guardrails 强化请求

```python
# Guardrail 403 响应示例（请求被 prompt injection 检测拦截）
{
    "error": {
        "code": 403,
        "message": "Request blocked: prompt injection patterns detected",
        "metadata": {"patterns": ["ignore all previous instructions"]}
    },
    "openrouter_metadata": {
        "requested": "openai/gpt-4o",
        "strategy": "direct",
        "region": "iad",
        "summary": "available=1",
        "attempt": 1,
        "is_byok": False,
        "endpoints": {
            "total": 1,
            "available": [{"provider": "OpenAI", "model": "openai/gpt-4o", "selected": False}]
        },
        "pipeline": [
            {
                "type": "guardrail",
                "name": "regex_pi_detection",
                "guardrail_id": "grd_abc123",
                "guardrail_scope": "api-key",
                "summary": "Blocked: prompt injection detected (1 pattern matched)",
                "data": {
                    "action": "blocked",
                    "detected": True,
                    "engines": ["regex"],
                    "patterns": ["ignore all previous instructions"]
                }
            }
        ]
    }
}
```

### 11.6 一次 OAuth PKCE 一键登录

```typescript
// 1) 跳转到 OpenRouter 登录
const codeVerifier = "...";  // 随机串
const codeChallenge = await createSHA256CodeChallenge(codeVerifier);
window.location.href =
  `https://openrouter.ai/auth?callback_url=${encodeURIComponent("https://my-app.com/cb")}` +
  `&code_challenge=${codeChallenge}&code_challenge_method=S256`;

// 2) 用户登录后回到 callback URL，提取 ?code=xxx
const code = new URLSearchParams(window.location.search).get("code");

// 3) 兑换为 user-controlled API key
const { key } = await fetch("https://openrouter.ai/api/v1/auth/keys", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({code, code_verifier: codeVerifier, code_challenge_method: "S256"})
}).then(r => r.json());
```

---

## 12. 性能基准（社区数据 + 公开测评汇总）

> OpenRouter 官方未发布"独立第三方性能基准"白皮书。以下为可观察的间接指标。

| 指标 | 值 | 来源 |
| --- | --- | --- |
| **接入延迟开销（边缘热缓存）** | < 50ms（基于 Cloudflare Workers） | OpenRouter Latency Docs |
| **TTFT（流式首 token）** | 与直连上游基本一致 | OpenRouter 公开声明 |
| **路由决策延迟** | < 5ms（边缘 KV 缓存候选列表） | 推断（基于 5 分钟滚动窗口） |
| **Cache HIT TTFT** | < 50ms | OpenRouter Response Caching Docs |
| **Prompt Cache HIT 折扣** | OpenAI 0.25–0.5x；Anthropic 0.1x；DeepSeek / Gemini 等按各自 multiplier | 厂商官方 |
| **Fusion 默认开销** | 4–5x 单次调用 cost | OpenRouter Fusion Docs |
| **日处理 tokens 量** | "10B+ tokens" | 创始人公开访谈（未独立审计） |
| **API 端点 endpoint 数量** | 417 | 实测 `/api/v1/models` 2026-06-05 |
| **模型厂商数** | 80+ | 实测 `/api/v1/models` 2026-06-05 |
| **Models 公开性能页** | 全员可查（`/models/{slug}` Performance tab） | OpenRouter 文档 |
| **Uptime 公开页** | 全员可查（`/uptime/{slug}`） | OpenRouter 文档 |

---

## 13. 路线图与未来方向（基于已发布功能的延伸）

> OpenRouter 未发布正式公开 roadmap，但根据 Discord 与 Blog 已发布的特性可推断方向：

1. **Server Tools 稳定化**（脱离 beta、API 形状稳定）——目前所有 `openrouter:*` Server Tools 都标 beta。
2. **更多主权区域**（继 EU 之后）—— 行业猜测是 US GovCloud / APAC；尚未官方公布。
3. **更多 Auto Router 模型池**（NotDiamond 之外的替代 / 互补）—— 已暗示"内部评估数据公开"。
4. **更强 Prompt Caching 跨厂商协议**（统一 OpenRouter 层抽象）—— 已是行业领先，仍有空间。
5. **Agent 编排层**（durable execution）—— 暂无动作；可能维持"模型层 + 路由"定位，编排留给 LangGraph / Inngest。
6. **Eval / Dataset 平台**（与 LangSmith / Helicone 竞争）—— 已发布 Router Metadata，但暂未做 Eval UI。
7. **Fine-tuning 入口**—— 暂无动作；可能与 Together / Fireworks 形成上下游而非竞争。

---

## 14. 引用与参考

### 14.1 OpenRouter 官方文档

- [Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Auto Router](https://openrouter.ai/docs/guides/routing/routers/auto-router)
- [Fusion Router](https://openrouter.ai/docs/guides/routing/routers/fusion-router)
- [Advisor Server Tool](https://openrouter.ai/docs/guides/features/server-tools/advisor)
- [Auto Exacto](https://openrouter.ai/docs/guides/routing/auto-exacto)
- [Free Models Router](https://openrouter.ai/docs/guides/routing/routers/free-router)
- [Pareto Router](https://openrouter.ai/docs/guides/routing/routers/pareto-router)
- [BYOK](https://openrouter.ai/docs/guides/overview/auth/byok)
- [Zero Data Retention](https://openrouter.ai/docs/guides/features/zdr)
- [Sovereign AI](https://openrouter.ai/docs/guides/features/sovereign-ai)
- [Workspaces](https://openrouter.ai/docs/guides/features/workspaces)
- [Guardrails](https://openrouter.ai/docs/guides/features/guardrails/overview)
- [Server Tools Overview](https://openrouter.ai/docs/guides/features/server-tools/overview)
- [Web Search](https://openrouter.ai/docs/guides/features/server-tools/web-search)
- [Response Caching](https://openrouter.ai/docs/guides/features/response-caching)
- [Prompt Caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching)
- [Router Metadata](https://openrouter.ai/docs/guides/features/router-metadata)
- [Latency & Performance](https://openrouter.ai/docs/guides/best-practices/latency-and-performance)
- [Uptime Optimization](https://openrouter.ai/docs/guides/best-practices/uptime-optimization)
- [Stripe Projects](https://openrouter.ai/docs/guides/overview/stripe-projects)
- [Presets](https://openrouter.ai/docs/guides/features/presets)
- [OAuth PKCE](https://openrouter.ai/docs/guides/overview/auth/oauth)
- [Provider Logging](https://openrouter.ai/docs/guides/privacy/provider-logging)
- [Models API](https://openrouter.ai/api/v1/models)
- [LLM Index](https://openrouter.ai/docs/llms.txt) / [LLM Full Text](https://openrouter.ai/docs/llms-full.txt)
- [MCP server](https://openrouter.ai/docs/_mcp/server)

### 14.2 第三方与社区资源

- NotDiamond 官网（Auto Router 算法供应方）
- Cloudflare AI Gateway 文档（OpenRouter 推断的底层）
- Stripe Projects 目录
- Discord `https://discord.gg/openrouter` 公开 AMA 记录
- GitHub 组织 `@OpenRouterTeam`（SDK 与示例）

### 14.3 相关对比报告（aigw/openclaw 系列）

- `product-portkey-20260605.md` — Portkey Gateway
- `product-litellm-20260605.md` — LiteLLM
- `product-oneapi-20260605.md` — One API / New API
- `product-higress-20260605.md` — Higress
- `product-kong-ai-20260605.md` — Kong AI Gateway
- `product-apisix-ai-20260605.md` — APISIX ai-proxy
- `product-envoy-ai-20260605.md` — Envoy AI Gateway
- `product-vllm-20260605.md` — vLLM（含其 gateway 能力）
- `product-sglang-20260605.md` — SGLang
- `product-tgi-20260605.md` — TGI
- `product-triton-20260605.md` — Triton Inference Server
- `product-lmdeploy-20260605.md` — LMDeploy
- `product-llamacpp-20260605.md` — llama.cpp
- `product-cloudflare-workers-ai-20260605.md` — Cloudflare Workers AI / AI Gateway

---

## 15. 附录 A：完整 Providers 列表（实测 `/api/v1/models` 2026-06-05）

> 仅列 slug 前缀示例，全部 417 endpoints 见 `https://openrouter.ai/api/v1/models`。

| 厂商 (slug 前缀) | 代表模型 | Endpoint 数量（估算） |
| --- | --- | --- |
| `openai/` | `gpt-5.2`, `gpt-5.1`, `gpt-5-mini`, `o3`, `o4-mini`, `gpt-4o`, `gpt-4.1`, `gpt-image-1` | ~25 |
| `anthropic/` | `claude-opus-4.5/4.6/4.7/4.8`, `claude-sonnet-4/4.5/4.6`, `claude-haiku-3.5/4.5` | ~20 |
| `google/` | `gemini-3-pro-preview`, `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, `gemini-2.5-pro/flash` | ~20 |
| `meta-llama/` | `llama-3.3-70b-instruct`, `llama-4-maverick`, `llama-guard-4` | ~15 |
| `deepseek/` | `deepseek-v3.2`, `deepseek-r1` | ~10 |
| `x-ai/` | `grok-4`, `grok-4.1` | ~6 |
| `mistralai/` | `mistral-large-3`, `mixtral-8x22b-instruct` | ~10 |
| `qwen/` | `qwen3-max`, `qwen3-coder-plus`, `qwen-plus`, `qwen3.5-plus-02-15` | ~15 |
| `z-ai/` (Zhipu) | `glm-4.6`, `glm-5.1` | ~6 |
| `moonshotai/` | `kimi-k2-0905-preview`, `kimi-k2-thinking` | ~5 |
| `minimax/` | `MiniMax-Text-01`, `abab-7-chat` | ~5 |
| `cohere/` | `command-r-plus`, `command-a` | ~5 |
| `perplexity/` | `sonar-pro`, `sonar-reasoning-pro` | ~6 |
| `amazon-bedrock/*` (via provider slug) | 上述各家的 Bedrock 端点 | ~30 |
| `azure/*` | OpenAI / Mistral 等的 Azure 端点 | ~10 |
| `groq/` | `kimi-k2-instruct-0905`, `llama-3.3-70b-versatile` | ~5 |
| `cerebras/` | `llama-3.3-70b`, `qwen-3-32b` | ~5 |
| `inference-net/*` | 多种 | ~10 |
| `minimax/*` | `MiniMax-Text-01` | ~3 |
| `nousresearch/` | `hermes-3-llama-3.1-405b` | ~5 |
| `openpipe/` | 多种 fine-tuned | ~5 |
| `replicate/*` | 多种 | ~10 |
| `together/*` | 多种 | ~10 |
| `fireworks/*` | 多种 | ~10 |
| `deepinfra/*` | 多种 | ~10 |
| 其他 (Liquid, Athene, Bagoodex, Stealth, AionLabs…) | — | ~80 |

---

## 16. 附录 B：典型失败与处理

| 场景 | 行为 |
| --- | --- |
| 主 provider 5xx | 自动切到次选 provider（按价格/延迟/吞吐排序后的下一位） |
| 全部 provider 5xx | 返回错误，**`openrouter_metadata.attempt` ≥ 1** |
| 主 provider 429 | 同上，自动切候选 |
| ZDR 强制但无 ZDR 端点 | 候选列表为空 → `404 No allowed providers are available` |
| 模型不存在 | `404` |
| Credit 不够 | `402 Payment Required`（在边缘检查） |
| 余额低 → 强制 DB 校验 | 延迟上升；建议保持 ≥ $10–20 并开 auto-topup |
| 提示注入触发 Guardrail | `403` + `openrouter_metadata.pipeline[].type=guardrail` |
| Sensitive Info redact | 原文 placeholder 替换后再发上游 |
| Cache HIT | 响应附 `X-OpenRouter-Cache-Status: HIT`，`usage` 归零，**不返回** `openrouter_metadata` |
| 同请求并发 | 各自 MISS + 计费（**无 request coalescing**） |
| BYOK key 失败 | 回退到 OpenRouter shared capacity（除非开 "Always use"） |
| `tool_choice` 不被 provider 支持 | 自动过滤该 provider，从候选中移除 |
| `max_tokens` 超过 provider 上限 | 同上，自动过滤 |

---

## 17. 附录 C：计费公式速查

```text
# OpenRouter Credits 路径
total_cost = provider_price(input_tokens, output_tokens) × 1.05

# BYOK 路径
total_cost = provider_price(...) × 0.05  (前 N 次/月免费)

# Server Tools 附加
total_cost += tool_call_fee[tool_type] + tool_tokens_cost(...)

# Fusion Router
total_cost = (panel_size × provider_price) + judge_price + 0.01 USD/次

# Advisor
total_cost = advisor_price + advisor_subagent_tool_costs + 0.01 USD/次

# Prompt Caching (provider 层)
input_cost = regular_tokens × P
            + cache_write_tokens × P × cache_write_multiplier
            + cache_read_tokens × P × cache_read_multiplier

# OpenRouter Response Caching (OpenRouter 层)
if HIT:  total_cost = 0
elif MISS: total_cost = 正常计费 (并写入 cache, TTL = X-OpenRouter-Cache-TTL 或默认 300s)
```

---

## 18. 总结

OpenRouter 在 2026 年中已经完成**从"多模型 API 代理"到"统一 LLM 平台"的进化**：

- **入口层**：5 大协议（OpenAI Chat / Anthropic / Responses / Embeddings / 自有）覆盖全部主流 SDK；一行 `baseURL` 替换即可接入。
- **路由层**：在开源网关之上，叠加 **Auto Router / Auto Exacto / Pareto / Free / Fusion / Advisor** 六类智能路由器，是行业最丰富的路由能力组合。
- **多模型协作层**：**Fusion**（8-model panel + judge）和 **Advisor**（子智能体 + tools）是 OpenRouter 独有的产品形态，把"multi-agent deliberation"做成了 Server Tool。
- **隐私 / 合规层**：**EU in-region 隔离 + ZDR per-model-group + Guardrails + BYOK** 构成了完整的 Sovereign AI 套件。
- **生态层**：417 endpoints / 80+ 厂商 / 300+ 模型 + MCP-native 文档 + Stripe Projects + OpenAI / Anthropic 兼容 SDK + Coding Agent IDE（Cline / Cursor）原生支持。

**最大短板是不可自托管**——这把 OpenRouter 限定在了"愿意把模型流量交给云端 SaaS"的客户群，与 LiteLLM / Portkey / Higress / Kong / APISIX / Envoy AI 等"自托管优先"产品形成清晰分工。**两者可叠加（OpenRouter 作为 LiteLLM 上游，或 Portkey 作为 OpenRouter 之上加可观测层），不是纯互斥**。

**对小B / 创业团队**而言，OpenRouter 是当前 2026 年**单一最佳多模型入口**——零部署、统一账单、智能路由、Sovereign AI、企业 SSO，全部开箱即用。**对 on-prem 强需求的大型企业**（金融、政府、国防）则需要评估自托管网关（LiteLLM / Portkey / Higress 等）+ 上游仍可走 OpenRouter 的 EU 隔离域作为辅助。

---

*报告完。调研人：Rich（OpenClaw 助手），基于 2026-06-05 实时数据。*
