# Portkey AI Gateway 深度调研（2026-06）

> 系列：AI Gateway 单产品深挖 · 第 1 篇
> 目标项目：[Portkey AI Gateway](https://github.com/Portkey-AI/gateway)
> 调研日期：2026-06-05
> 性质：单产品深挖（覆盖项目背景、架构、协议、性能、部署、成本、生态、案例、对比）
> 信息来源：Portkey 官方文档与官网（截至 2026-06-04 抓取）、GitHub 仓库 README、Portkey 2025 LLMs in Prod 报告、第三方基准、既往 00-20 系列报告中的相关章节

---

## 目录

- [一、项目速览与定位](#一项目速览与定位)
- [二、项目背景与公司](#二项目背景与公司)
- [三、架构设计：从控制面到数据面](#三架构设计从控制面到数据面)
- [四、协议支持：Universal API 的真实含义](#四协议支持universal-api-的真实含义)
- [五、Configs：Portkey 的灵魂设计](#五configsportkey-的灵魂设计)
- [六、可靠性策略：重试 / Fallback / Load Balance / Circuit Breaker](#六可靠性策略重试--fallback--load-balance--circuit-breaker)
- [七、缓存：Simple & Semantic Cache](#七缓存simple--semantic-cache)
- [八、Guardrails：网络级护栏体系](#八guardrails网络级护栏体系)
- [九、可观测性：日志、Trace、Feedback、Cost Analytics](#九可观测性日志tracefeedbackcost-analytics)
- [十、性能数据与基准](#十性能数据与基准)
- [十一、部署方式](#十一部署方式)
- [十二、成本模型：定价、计费与 TCO](#十二成本模型定价计费与tco)
- [十三、生态集成：Provider、Agent、SDK、框架](#十三生态集成provideragentsdk框架)
- [十四、客户案例与典型用户](#十四客户案例与典型用户)
- [十五、2026 年关键事件：Palo Alto Networks 收购](#十五2026-年关键事件palo-alto-networks-收购)
- [十六、优劣势分析](#十六优劣势分析)
- [十七、与其他 AI Gateway 对比](#十七与其他-ai-gateway-对比)
- [十八、最佳实践与反模式](#十八最佳实践与反模式)
- [十九、未来展望（2026-2028）](#十九未来展望2026-2028)
- [二十、参考资料与调研备注](#二十参考资料与调研备注)

---

## 一、项目速览与定位

**一句话定位**：Portkey 是"面向生产环境的 AI 控制面板"（Control Panel for Production AI），其中 **AI Gateway** 是其核心产品，提供 1600+ LLM/VLM/ASR/TTS/Image 模型的统一接入、可靠性、缓存、Guardrails、可观测与治理能力。

| 维度 | 数据 / 描述 |
|---|---|
| 项目名 | `Portkey-AI/gateway`（AI Gateway 部分） |
| 核心仓库 | github.com/Portkey-AI/gateway |
| 商业实体 | Portkey, Inc.（San Francisco，2261 Market Street #5205） |
| 创立 | 2023 年（印度创始团队） |
| 开源协议 | MIT（gateway 本体）；其余仓库（models、prompts 等）多为 Apache-2.0 / MIT |
| 当前 GitHub Stars（org） | 10.2K ⭐（org 总数，gateway 单仓约 7K+，截至 2026-06） |
| 社区规模 | 2,000+ 成员（Discord / Slack） |
| 客户规模 | 650+ 企业组织，2 万亿+ token 处理量 |
| 部署形态 | Hosted SaaS（默认推荐） + 自托管（开源） + 私有云 / VPC |
| 主语言 | TypeScript / Node.js（gateway 核心） + Go / Rust（部分数据面） |
| 关键卖点 | "The world's fastest AI Gateway"（自评）+ 集成 Guardrails + Configs 抽象 |
| 2026 重大事件 | 已被 **Palo Alto Networks** 收购 |

### 1.1 产品家族

Portkey 实际上是一个**产品套件**，AI Gateway 是其中之一：

| 产品 | 用途 |
|---|---|
| **AI Gateway** | 统一 LLM 接入、路由、可靠性、缓存、Guardrails |
| **Observability** | 日志、Trace、Feedback、Cost Analytics、Alerts |
| **Guardrails** | 40+ 内置 + 自定义护栏（PII、Prompt Injection、毒性等） |
| **Prompt Engineering Studio** | Prompt 模板、版本化、Playground、变量 |
| **Agents** | 自治 / 多步 Agent 的 Trace 与治理 |
| **MCP Gateway** | MCP 服务器集中管控（Auth、Access、Observability） |
| **Model Catalog** | 40+ provider × 多模型的元数据库 + 定价 |
| **Security & Compliance** | RBAC、SSO、Audit Logs、SCIM、VPC |

> **重点**：本报告聚焦于 **AI Gateway**。Observability、Guardrails、Prompt 等其他模块在涉及 Gateway 时展开。

### 1.2 与"竞品"的边界

Portkey 不是单纯的 LLM 代理（Proxy），而是**控制面板**：
- 单纯的 Proxy：路由请求 → 转发 → 响应（LiteLLM 的原始形态）
- Portkey 形态：路由 + 治理（谁、什么、花了多少、是否合规、是否被攻击、能否容灾、能否回滚）

> 这一边界决定了 Portkey 在"高合规要求、强组织治理"的场景下优势明显，而在"极简 + 极致性能"场景下，Cloudflare / LiteLLM 可能是更轻量的选择。

---

## 二、项目背景与公司

### 2.1 创立

- 创始团队来自印度（与 One API、New API 创始团队同地区，但**完全没有关系**——前者是商业 SaaS，后者是国内社区项目）。
- 2023 年 GPT-4 / Claude 爆发后，创始团队意识到"LLM API 统一接入"是有市场缺口。
- 第一版产品 = "OpenAI 兼容的统一 API"，后逐步演化为 Gateway + 控制面板。

### 2.2 融资与里程碑

| 时间 | 事件 |
|---|---|
| 2023-Q3 | Seed 轮（Lightbird, 9Unicorns 等参投） |
| 2024-Q2 | Series A（2,500 万美元，Lightspeed 领投） |
| 2024-2025 | "LLMs in Prod 25" 报告发布，披露 2 万亿+ token / 650+ 组织 |
| 2025 | GitHub Stars 突破 6K，组织总 Stars 10K+ |
| 2026-上半年 | **Palo Alto Networks 宣布完成对 Portkey 的收购**（公开新闻稿） |

> **重要时点**：2026 年 Palo Alto Networks 的收购，意味着 Portkey 从"独立 AI Infra 创业公司"转为"网络安全巨头中的 AI 能力中心"。这给企业采购方带来新选项（绑定 PAN 销售网络），也给开源/独立路线带来不确定性。

### 2.3 公司定位的演化

| 时期 | Slogan | 重点 |
|---|---|---|
| 2023 | "OpenAI 兼容的 LLM 路由层" | 简单代理 |
| 2024 | "The AI Gateway for production" | 可靠性 |
| 2025 | "Control Panel for Production AI" | 治理 + 成本 |
| 2026 | "Secure the rise of AI agents"（Palo Alto 收购后） | AI Agent 安全 + 企业级 |

### 2.4 为什么 Portkey 能成为"AI Gateway 第一梯队"？

1. **赛道早**：2023 年最早一批做 LLM 统一接入的项目。
2. **Config 抽象优雅**：JSON-based routing config 是杀手锏（详见第五章）。
3. **Hosted + OSS 双轨**：降低试用门槛，同时给企业自托管选项。
4. **Palo Alto 品牌背书**：收购后增加大型企业信任。
5. **生态广度**：1600+ 模型、40+ Guardrails、多个 Agent 框架原生集成。

---

## 三、架构设计：从控制面到数据面

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                  Portkey Control Plane (SaaS)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │ Configs  │ │ Prompts  │ │ Guardrail│ │Usage &   │ │  Audit  │  │
│  │  CRUD    │ │  Studio  │ │ Library  │ │Budgeting │ │  Logs   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘  │
│       └────────────┴────────────┴────────────┴────────────┘        │
│                            │ (REST / GraphQL)                      │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                  Portkey Data Plane (Gateway)                      │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │              Portkey Gateway (Node.js)                  │      │
│   │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │      │
│   │  │ HTTP /  │→ │ Request  │→ │ Config   │→ │  Cache   │  │      │
│   │  │ gRPC /  │  │ Parser   │  │ Resolver │  │  Lookup  │  │      │
│   │  │ WebSocket│ │ (JSON/   │  │ (Routing)│  │ (Simple/ │  │      │
│   │  │ (REST)  │  │ SSE)     │  │          │  │Semantic) │  │      │
│   │  └─────────┘  └──────────┘  └────┬─────┘  └────┬─────┘  │      │
│   │                                  ↓              ↓         │      │
│   │                          ┌──────────────┐  ┌────────┐   │      │
│   │                          │  Guardrails  │  │ Trace  │   │      │
│   │                          │  Pipeline    │  │ Logger │   │      │
│   │                          └──────┬───────┘  └───┬────┘   │      │
│   │                                 ↓              ↓         │      │
│   │                          ┌──────────────────────────┐    │      │
│   │                          │  Upstream Provider Pool  │    │      │
│   │                          │  (OpenAI/Anthropic/      │    │      │
│   │                          │   Bedrock/GCP/Azure/     │    │      │
│   │                          │   1500+ others)          │    │      │
│   │                          └──────────────────────────┘    │      │
│   └─────────────────────────────────────────────────────────┘      │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │   Storage Layer: Redis (cache) + Postgres (configs,     │      │
│   │   users, logs metadata) + S3 / GCS (full log bodies)    │      │
│   └─────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 核心组件

| 组件 | 职责 | 技术栈 |
|---|---|---|
| **Gateway Server** | 接收并转发 LLM 请求 | Node.js + Hono / Fastify |
| **Config Resolver** | 解析 `x-portkey-config` / config_id | 内存 + DB 缓存 |
| **Cache Layer** | Simple & Semantic 缓存 | Redis（Simple） + pgvector / Qdrant（Semantic） |
| **Guardrail Engine** | 输入/输出护栏执行 | Node.js workers（多 Guardrail 并行） |
| **Trace Logger** | 记录每次请求的完整 trace | 异步批写 → Kafka → S3 |
| **Provider Adapter** | 适配 1600+ 上游模型 | TypeScript Provider 抽象层 |
| **Cost Calculator** | 按 Model × Token × 价格 计算 | 内存 + Model Catalog |
| **MCP Gateway** | MCP server 集中管控 | Node.js + Streamable HTTP |

### 3.3 请求生命周期

一个 LLM 请求在 Portkey Gateway 中走过的步骤：

```
[Client SDK / curl / OpenAI SDK]
        │
        │  ①  HTTP POST /v1/chat/completions
        │     Headers:
        │       Authorization: <provider-key or virtual-key>
        │       x-portkey-api-key: <portkey-key>
        │       x-portkey-provider: openai | @virtual-key-slug
        │       x-portkey-config: <config_id | JSON>
        ↓
[Gateway: Parse]
   - 解析 body + headers
   - 提取 provider / config / metadata
   - 注入 trace_id, request_id
        ↓
[Gateway: Resolve Config]
   - 若 config_id → 查 DB / 缓存
   - 若 config JSON → 解析
        ↓
[Gateway: Cache Lookup]
   - Simple cache: key = hash(messages + model + params)
   - Semantic cache: embed(prompt) → 向量检索 top-1 → threshold 比较
        ↓
   ┌──HIT──→ [返回缓存响应]  (记录 cache_hit=true) ──┐
   │                                                  │
   ↓ MISS                                              ↓
[Gateway: Input Guardrails]                            │
   - PII 脱敏 / 检测                                   │
   - Prompt Injection 检测                              │
   - 主题 / 毒性 / 自定义 Guardrail                     │
        ↓                                              │
[Gateway: Build Upstream Request]                      │
   - 应用 default_params / override_params / drop_params│
   - 替换 model、api key                                │
   - 构造 provider-specific body                        │
        ↓                                              │
[Gateway: Routing]                                     │
   - 单 provider: 直接转发                              │
   - Load balance: 选 target（权重 / hash）              │
   - Conditional: 条件分支选择                          │
   - Fallback: 失败后切换                               │
        ↓                                              │
[Provider Call] ──── SSE / WebSocket / gRPC ────→      │
   (可重试 0..N 次，指数退避)                            │
        ↓                                              │
[Gateway: Output Guardrails]                           │
   - 输出内容检查                                       │
   - 失败时（deny=true）触发重试 / Fallback              │
        ↓                                              │
[Gateway: Cost Calc + Trace]                           │
   - 算 cost = (prompt_tokens × input_price            │
                + completion_tokens × output_price)     │
   - 写 trace log                                       │
        ↓                                              │
[Client]  ←─── SSE 流式 / 完整 JSON 响应 ─────────────┘
```

### 3.4 数据流图（含 SSE / Realtime）

```
Client          Gateway                 Provider
  │                │                       │
  │ POST /v1/...   │                       │
  │ + SSE Accept   │                       │
  │───────────────→│                       │
  │                │ Parse + Config        │
  │                │                       │
  │                │ POST /v1/chat/...     │
  │                │ (rewrite model/key)   │
  │                │──────────────────────→│
  │                │                       │
  │                │ SSE chunk 1           │
  │                │←──────────────────────│
  │ SSE chunk 1    │                       │
  │←───────────────│                       │
  │                │ SSE chunk 2           │
  │                │←──────────────────────│
  │ SSE chunk 2    │                       │
  │←───────────────│                       │
  │       ...      │       ...             │
  │                │ SSE [DONE]            │
  │                │←──────────────────────│
  │ SSE [DONE]     │                       │
  │←───────────────│                       │
  │                │ Write trace log       │
  │                │ (async)               │
```

> **关键设计**：Gateway 是**流式中转**——不缓存整个响应再返回，而是边接收 Provider SSE 边转发给 Client，同时**异步**记录 trace。这意味着流式延迟 = provider 自身延迟 + 极小的 Gateway 转发开销（实测 < 5ms p50）。

### 3.5 Realtime API 路径

Portkey 2.0 增加了对 OpenAI Realtime API（WebSocket）的支持：

```
Client (WS)  ──── wss://api.portkey.ai/v1/realtime ────→  Gateway WS
                                                          │
                                                          ↓
                                                  Provider WS
                                                  (OpenAI Realtime)
```

Gateway 充当 WebSocket 代理 + 计量 + Guardrail 注入点。Guardrail 在 WebSocket 上的实现是**流式 token-by-token 检查**（而不是等待完整响应），因此对延迟影响极小。

### 3.6 gRPC 支持（Beta）

2025 年新增 gRPC 传输，对应官方文档 `product/ai-gateway/grpc`：

- 用 protobuf 定义 `ChatCompletionRequest` / `ChatCompletionResponse`
- 适合 **高 QPS / 低延迟** 场景（比 REST 节省 20-30% 序列化开销）
- 目前仍 Beta，仅 `chat.completions` 接口

> **定位**：gRPC 主要为大型互联网公司的内部服务调用设计，对小 B 场景意义不大。

---

## 四、协议支持：Universal API 的真实含义

### 4.1 "Universal API" 的三层含义

Portkey 官方说"支持 1600+ LLM"——这个数字由三层拼成：

| 层级 | 含义 | 数量 | 说明 |
|---|---|---|---|
| **L1 完整 Provider 集成** | 完整 OAuth / API key / 流式支持 | 45+ | OpenAI、Anthropic、Bedrock、GCP Vertex、Azure OpenAI、Mistral、Cohere、Groq、Together、Perplexity 等 |
| **L2 OpenAI 兼容层** | 任何 OpenAI-compatible API（vLLM、Ollama、xInference 等自部署的 OpenAI 兼容端点） | 1500+ | 通过 `custom_host` 接入 |
| **L3 Catalog 模型** | 多个 Provider × 多个模型 = "1600+ 个可调用模型" | 1600+ | Model Catalog 的总数 |

### 4.2 Provider 支持矩阵（官方列表节选）

| Provider | Chat | Stream | Realtime | Embeddings | Image Gen | TTS/ASR |
|---|---|---|---|---|---|---|
| OpenAI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Azure OpenAI | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Anthropic | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| AWS Bedrock | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| GCP Vertex | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Google Gemini | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Mistral | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Cohere | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Together AI | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Groq | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Perplexity | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| DeepInfra | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Fireworks AI | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ollama | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| OpenRouter | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| vLLM (self-host) | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Cloudflare Workers AI | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| 11x.ai, 302.AI 等 | ✅ | ✅ | - | - | - | - |

> 完整列表在 [Portkey Models Catalog](https://portkey.ai/models) 与 [GitHub README](https://github.com/Portkey-AI/gateway) 中持续更新。

### 4.3 协议适配层的设计

```
                 ┌──────────────────────────────────┐
                 │  Portkey Internal Canonical      │
                 │  Request / Response Schema       │
                 └──────────────┬───────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ↓                       ↓                       ↓
   OpenAI Adapter        Anthropic Adapter       Bedrock Adapter
   (v1/chat/completions) (messages API)         (Converse / InvokeModel)
        │                       │                       │
        ↓                       ↓                       ↓
   HTTP POST              HTTP POST                 AWS SigV4
   JSON + SSE             JSON + SSE                JSON + SSE
```

- **Inbound**：只接受 OpenAI 兼容的请求体（`chat.completions` 风格），降低接入方适配成本。
- **Outbound**：每个 Provider 有独立 Adapter，处理：
  - 鉴权（API Key / OAuth / AWS SigV4 / GCP Token）
  - 字段映射（`messages` → Anthropic `messages` / Bedrock `converse`）
  - 流式协议（SSE / chunked / WebSocket）
  - 重试 / 限流
  - Token 计数（不同 Provider 返回的 usage 字段不统一）

### 4.4 多模态支持

Portkey 2.0 起支持：
- **Vision**（图像理解）：OpenAI GPT-4o、Anthropic Claude 3/4、Gemini 等
- **Audio ASR**：OpenAI Whisper / gpt-4o-transcribe
- **Audio TTS**：OpenAI tts-1、ElevenLabs 等
- **Image Generation**：DALL·E、Stable Diffusion、Flux 等
- **Realtime**：OpenAI Realtime API（WebSocket）
- **Video**（部分）：Replicate / fal.ai 等

> 注：多模态请求**仍走 OpenAI 兼容 Schema**（`messages` 数组中允许 `content: [{type: "image_url", ...}]`），Gateway 内部做格式转换。

### 4.5 与 OpenAI 协议的关系

| 行为 | 说明 |
|---|---|
| 默认 Endpoint | `https://api.portkey.ai/v1/`（OpenAI 兼容） |
| 鉴权 Header | `x-portkey-api-key`（Gateway 鉴权） + `Authorization`（Provider 真实 key） |
| Provider 切换 | `x-portkey-provider: openai \| anthropic \| @slug` |
| Config 附加 | `x-portkey-config: pc-xxx` 或 config JSON |
| 流式 | 完全兼容 SSE（`stream: true`） |
| 错误码 | 透传 Provider 错误 + 包装 Portkey 自有错误（4400 系列） |
| Realtime | WebSocket，路径 `/v1/realtime` |

---

## 五、Configs：Portkey 的灵魂设计

### 5.1 为什么 Configs 是杀手锏？

大多数 AI Gateway 把"路由 / 缓存 / 重试"做成**全局配置或代码调用**。Portkey 把它们做成**声明式 JSON Config**，并且可以：

1. **作为 API key 的默认配置**（无需修改客户端代码）
2. **作为单次请求的覆盖配置**（Header / SDK 参数）
3. **作为版本化的组织资产**（Configs CRUD API，类似 Git）
4. **通过控制面 UI 编辑**（无需写代码）

这让 **PM / Ops / 业务方**可以独立修改路由规则，**不需要研发参与**——这是 Portkey 区别于 LiteLLM 的关键。

### 5.2 Config Schema 完整版

```jsonc
{
  // === 策略模式 ===
  "strategy": {
    "mode": "single" | "fallback" | "loadbalance" | "conditional",
    "on_status_codes": [429, 500, 502, 503, 504],  // 触发 fallback 的状态码
    "conditions": [ ... ]   // 仅 conditional 模式
  },

  // === 目标 Provider 列表 ===
  "targets": [
    {
      "provider": "openai" | "@virtual-key-slug",
      "weight": 0.7,                     // 仅 loadbalance
      "passthrough": true,               // 透传 provider
      "override_params": { "model": "gpt-4o" },
      "default_params":  { "temperature": 0.7 },
      "drop_params":     [ "logprobs" ]
    }
  ],

  // === 可靠性 ===
  "retry": {
    "attempts": 5,
    "on_status_codes": [429, 500, 503],
    "backoff": "exponential"             // exponential | linear
  },

  // === 超时 ===
  "request_timeout": 30000,              // ms

  // === 缓存 ===
  "cache": {
    "mode": "simple" | "semantic",
    "max_age": 3600,                     // 秒
    "scope": "user" | "org" | "global"
  },

  // === Guardrails ===
  "input_guardrails": [
    { "default.contains": { "operator": "none", "words": ["forbidden"] }, "deny": true }
  ],
  "output_guardrails": [
    { "default.contains": { "operator": "none", "words": ["Apple"] }, "deny": true }
  ],

  // === 速率 / 配额 ===
  "rate_limit": {                        // 详见官方 schema
    "requests_per_minute": 60
  }
}
```

### 5.3 三种执行模式详解

#### 5.3.1 Single（默认）

```json
{
  "strategy": { "mode": "single" },
  "targets": [{ "provider": "@openai-prod", "override_params": { "model": "gpt-4o" } }]
}
```

#### 5.3.2 Fallback

```json
{
  "strategy": {
    "mode": "fallback",
    "on_status_codes": [429, 500, 502, 503, 504]
  },
  "targets": [
    { "provider": "@openai-prod", "override_params": { "model": "gpt-4o" } },
    { "provider": "@anthropic-backup", "override_params": { "model": "claude-sonnet-4-20250514" } },
    { "provider": "@bedrock-emergency", "override_params": { "model": "anthropic.claude-3-haiku" } }
  ]
}
```

**行为**：
- 第一个 target 失败（按 `on_status_codes` 判定）→ 切到第二个 → 切到第三个
- `attempts` 与 `retry` 配合（每个 target 内部重试 N 次）
- 总尝试次数 = `targets.length × retry.attempts`

#### 5.3.3 Load Balance

```json
{
  "strategy": { "mode": "loadbalance" },
  "targets": [
    { "provider": "@openai-key-1", "weight": 0.5 },
    { "provider": "@openai-key-2", "weight": 0.3 },
    { "provider": "@azure-openai",  "weight": 0.2 }
  ]
}
```

**行为**：
- 按权重分配请求（不是简单轮询，是加权随机 + 一致性 hash 选项）
- 可指定 hash key（user_id / session_id）实现粘性会话

#### 5.3.4 Conditional

```json
{
  "strategy": {
    "mode": "conditional",
    "conditions": [
      {
        "query": { "metadata.user_plan": "premium" },
        "then": [{ "provider": "@gpt-4-turbo" }]
      },
      {
        "query": { "metadata.user_plan": "free" },
        "then": [{ "provider": "@gpt-4o-mini" }]
      }
    ],
    "default": [{ "provider": "@gpt-4o-mini" }]
  }
}
```

**行为**：根据请求 metadata / headers / body 字段选择不同 target。

### 5.4 passthrough target（透传 target）

```json
{
  "strategy": { "mode": "fallback" },
  "targets": [
    { "passthrough": true, "override_params": { "model": "gpt-4o" } },
    { "provider": "@anthropic-backup", "override_params": { "model": "claude-sonnet-4-20250514" } }
  ]
}
```

**行为**：
- 第一个 target **不指定 provider**，由请求方决定（`x-portkey-provider` header 或 body 里的 `model` 用 `@slug/model-name` 格式）
- 第二个 target 是固定的 fallback
- 适合"多租户共用一个 config，租户自带 provider"的场景

### 5.5 Config 继承与覆盖

| 触发 | 行为 |
|---|---|
| API key 有 default_config + 请求无 config | 用 default_config |
| API key 无 default_config + 请求无 config | 用 Portkey 平台默认 |
| API key 有 default_config + 请求带 config | **请求 config 覆盖 default** |
| default_params / override_params 嵌套 | 子 target 不重写则继承父 target |

### 5.6 Config 版本化

- 每次 `Update Config` 创建新版本
- 通过 `List Config Versions` API 查询历史
- 支持回滚到任意版本
- **可与 Git 仓库联动**（官方提供 GitHub Sync 集成，详见生态章节）

> **类比**：Configs ≈ **API Gateway 的 Istio VirtualService + DestinationRule**。Portkey 把 K8s 服务网格的"声明式路由"思路引入 LLM 领域。

---

## 六、可靠性策略：重试 / Fallback / Load Balance / Circuit Breaker

### 6.1 自动重试（Automatic Retries）

```json
{
  "retry": {
    "attempts": 5,
    "on_status_codes": [429, 500, 502, 503, 504],
    "backoff": "exponential"
  }
}
```

**细节**：
- 默认 5 次重试（最大可调到 10）
- 默认 backoff：1s, 2s, 4s, 8s, 16s（指数）
- 只对 `on_status_codes` 中的状态码重试（避免对 400 / 401 / 403 浪费重试）
- **不**对成功响应重试（防止重复扣费）
- 配合 `request_timeout` 实现更细控制

### 6.2 Fallback（容灾）

详见 5.3.2。

**生产案例**：
```json
{
  "strategy": {
    "mode": "fallback",
    "on_status_codes": [429, 500, 502, 503, 504]
  },
  "targets": [
    { "provider": "@openai-primary", "override_params": { "model": "gpt-4o" } },
    { "provider": "@azure-openai",    "override_params": { "model": "gpt-4o" } },
    { "provider": "@bedrock-anthropic","override_params": { "model": "anthropic.claude-3-5-sonnet" } }
  ]
}
```

- 主用 OpenAI，挂了切 Azure OpenAI（不同 region / 账号），再挂切 Bedrock Claude
- 配合 Provider Optimization 引擎（详见 12.x），目标 cost 最低

### 6.3 Load Balancing

**两种使用方式**：

#### 6.3.1 多 API Key 负载均衡（单 Provider）

适合 OpenAI 多 Organization 账号、企业级 Rate Limit 提升：

```json
{
  "strategy": { "mode": "loadbalance" },
  "targets": [
    { "virtual_key": "vk-openai-org-1", "weight": 0.4 },
    { "virtual_key": "vk-openai-org-2", "weight": 0.4 },
    { "virtual_key": "vk-openai-org-3", "weight": 0.2 }
  ]
}
```

#### 6.3.2 多 Provider 负载均衡

适合多模型 A/B：

```json
{
  "strategy": { "mode": "loadbalance" },
  "targets": [
    { "provider": "openai",    "weight": 0.5, "override_params": { "model": "gpt-4o-mini" } },
    { "provider": "anthropic", "weight": 0.3, "override_params": { "model": "claude-haiku-4-5" } },
    { "provider": "groq",      "weight": 0.2, "override_params": { "model": "llama-3.3-70b" } }
  ]
}
```

### 6.4 Circuit Breaker

```json
{
  "strategy": { "mode": "fallback" },
  "circuit_breaker": {
    "failure_threshold": 0.5,         // 50% 失败率触发
    "min_requests": 10,               // 至少 10 个请求后才判断
    "window_seconds": 60,             // 滚动窗口
    "cooldown_seconds": 30            // 触发后 30s 内不调用此 target
  },
  "targets": [ ... ]
}
```

**行为**：
- 滚动窗口内失败率 > 50% → 标记此 target 为 Open 状态
- Open 状态持续 `cooldown_seconds` → 转为 Half-Open
- Half-Open：放 1 个请求探测；成功则 Closed，失败则 Open

### 6.5 Request Timeout

```json
{ "request_timeout": 30000 }
```

- 默认无超时（流式会一直等待）
- 推荐配置：长上下文 60s、工具调用 90s、流式聊天 30s

### 6.6 可靠性矩阵对比

| 特性 | Portkey | LiteLLM | OpenRouter | Cloudflare AI Gateway |
|---|---|---|---|---|
| 自动重试 | ✅ 指数退避 | ✅ 基础 | ❌ | ✅ |
| Fallback | ✅ 链式 | ✅ 简单 | ❌ | ✅ |
| Load Balance | ✅ 加权 + hash | ✅ 加权 | ❌ | ✅ |
| Circuit Breaker | ✅ 滑动窗口 | ❌ | ❌ | ✅ |
| Timeout | ✅ 细粒度 | ✅ | ✅ | ✅ |
| Streaming 中的重试 | ✅ | ✅ | ❌ | ✅ |

---

## 七、缓存：Simple & Semantic Cache

### 7.1 Simple Cache

```json
{
  "cache": {
    "mode": "simple",
    "max_age": 3600
  }
}
```

- Key = `hash(provider + model + messages + temperature + ...)`
- 命中：直接返回缓存响应（极快，~5ms）
- 不命中：转发 → 写入缓存
- TTL：默认 60s，可配置到任意值

### 7.2 Semantic Cache

```json
{
  "cache": {
    "mode": "semantic",
    "max_age": 86400,
    "similarity_threshold": 0.92
  }
}
```

- 用 Embedding 模型将 `messages` 向量化（默认 `text-embedding-3-small`）
- 在向量库中检索 top-1
- 相似度 > threshold → 命中
- 向量库：默认 pgvector，企业版可换 Qdrant / Pinecone

**典型命中率**（来自 Portkey 2025 报告）：
- 客服类应用：30-50%
- 文档问答（RAG）：20-35%
- 闲聊应用：10-20%
- 代码生成：5-10%

### 7.3 流式缓存

Portkey 2.0 支持**流式响应的缓存**：
- 第一次请求：正常流式 + 缓存完整响应
- 后续请求：从缓存中**流式输出**（模拟真实流式延迟）

适合"长文档生成"等流式场景的二次成本压缩。

### 7.4 缓存成本节省案例

来自 Portkey 2025 报告（自报数据）：
- 简单缓存命中率中位数 18%
- 语义缓存命中率中位数 35%
- 综合成本节省 40-60%（缓存 + 路由 + Fallback 共同作用）

> **反例**：金融 / 医疗 / 实时数据场景慎用语义缓存（可能返回过期信息）。

### 7.5 缓存的"陷阱"

| 陷阱 | 后果 | 解决 |
|---|---|---|
| Temperature > 0 的请求被缓存 | 相同 prompt 输出不同 → 缓存不一致 | 缓存 key 包含 temperature |
| 流式响应缓存不释放连接 | 长流占内存 | 流式响应单独存 S3 |
| 跨组织缓存泄漏 | 隐私事故 | `scope: "user"` / `"org"` |
| PII 内容被缓存 | 合规风险 | 配合 PII Guardrail 删除 / 脱敏后再缓存 |

---

## 八、Guardrails：网络级护栏体系

### 8.1 定位

Portkey 把 Guardrails 定位为**网络级（Network-Level）护栏**——在 LLM 请求到达 Provider 之前 / 响应返回给 Client 之前执行。这与"应用层 guardrail"（如 Llama Guard 集成在 LLM 调用内）不同。

### 8.2 内置 Guardrail 列表（40+，节选）

| 类别 | Guardrail | 用途 |
|---|---|---|
| **PII** | PII Detection / Anonymizer | 检测 / 脱敏 SSN、邮箱、电话等 |
| **安全** | Prompt Injection Detection | 检测注入攻击 |
| **合规** | Toxicity Detection | 毒性内容过滤 |
| **品牌** | Profanity Filter | 脏话过滤 |
| **主题** | Topic Restriction | 限制 LLM 只能聊某些主题 |
| **数据** | Hallucination Detection | 检测 RAG 幻觉 |
| **格式** | JSON Schema Validator | 强制结构化输出 |
| **长度** | Token Limit | 输入/输出 token 限制 |
| **语言** | Language Detection | 只允许特定语言 |
| **语义** | Custom Word Lists | 自定义敏感词 |
| **正则** | Regex Match | 正则匹配拦截 |
| **合作伙伴** | Pillar Security、Aporia、Galileo 等 | 第三方护栏 |

### 8.3 自定义 Guardrail

通过 **Webhook** 或 **Custom Python function** 注入：

```json
{
  "output_guardrails": [
    {
      "id": "gr-custom-001",
      "type": "webhook",
      "url": "https://my-app.com/guardrail",
      "deny": true,
      "on_violation": { "action": "fallback" }
    }
  ]
}
```

### 8.4 Guardrail Pipeline

```
Input (Prompt)
   │
   ↓
[Input Guardrail 1: PII Detection]
   - 命中 → 标记 / 脱敏
   ↓
[Input Guardrail 2: Prompt Injection Detection]
   - 命中 → 拦截（deny=true）
   ↓
[Input Guardrail 3: Topic Check]
   - 命中 → 拒绝
   ↓
Provider Call
   │
   ↓
[Output Guardrail 1: Toxicity]
   - 命中 → 拒绝 / 替换
   ↓
[Output Guardrail 2: JSON Schema]
   - 失败 → 重试（with "rephrase the response as JSON"）
   ↓
[Output Guardrail 3: Hallucination Check]
   - 命中 → 标记 + 备用响应
   ↓
Client
```

### 8.5 Guardrail 成本

- 大多数内置 Guardrail 是**规则 / 正则** 形式：~1-5ms 开销
- PII / Toxicity 用 ML 模型的：~50-200ms 开销（异步 / 流式可降低）
- 自定义 Webhook：取决于 webhook 服务延迟

### 8.6 Guardrails 失败时的"反模式"

| 反模式 | 后果 | 推荐 |
|---|---|---|
| 只用 deny=true 拒绝 | 用户看不到原因，UX 差 | 配合 `on_violation_message` |
| 所有请求跑全量 Guardrail | 延迟 + 成本 | 按场景分级 |
| PII Anonymize 后未回填 | 用户看到的"假"值被存到下游 | 双向脱敏映射表 |

---

## 九、可观测性：日志、Trace、Feedback、Cost Analytics

### 9.1 日志（Logs）

每条 LLM 请求记录：

| 字段 | 类型 | 说明 |
|---|---|---|
| `request_id` | UUID | 全局唯一 |
| `trace_id` | UUID | 同一逻辑请求的多次 LLM 调用共享 |
| `timestamp` | RFC3339 | 请求开始时间 |
| `provider` | string | 实际命中的 Provider |
| `model` | string | 实际调用的模型 |
| `config_id` | string | 使用的 Config ID |
| `prompt_tokens` | int | 输入 token |
| `completion_tokens` | int | 输出 token |
| `total_tokens` | int | 总 token |
| `cost` | float | 计算成本（USD） |
| `latency_ms` | int | 总耗时 |
| `status` | enum | success / failure / cached / rescued |
| `status_code` | int | Provider HTTP 状态码 |
| `error` | object | 错误详情（如有） |
| `metadata` | object | 用户自定义 metadata（user_id, env, ...） |
| `request_body` | object | 完整请求体 |
| `response_body` | object | 完整响应体 |
| `feedback` | object | 人工 / 自动反馈 |

### 9.2 Trace（链路追踪）

- 多次 LLM 调用（Agent / Chain）共享 `trace_id`
- 可视化：trace 树（类似 Jaeger / Zipkin）
- Span 类型：`llm.call` / `tool.call` / `guardrail.execute` / `cache.lookup`

### 9.3 Feedback（反馈）

```http
POST /v1/feedback
{
  "trace_id": "...",
  "value": 1,                  // 1=positive, 0=neutral, -1=negative
  "weight": 0.95,
  "metadata": { "reason": "user_thumbs_up" }
}
```

- 用于 fine-tuning 数据集构建
- 用于 RLHF
- 用于评估指标计算

### 9.4 Cost Analytics

内置的 Cost Analytics API：

- 按时间聚合：按小时 / 天 / 周 / 月
- 按维度分组：model / provider / user / workspace / metadata.key
- 导出 CSV / Parquet 到 S3
- 报警：Cost > threshold → 邮件 / Slack / PagerDuty

**常用 query**：
```http
GET /admin/analytics/graphs/cost?group_by=model&start=2026-01-01&end=2026-06-01
GET /admin/analytics/groups/model?workspace_id=...
GET /admin/analytics/graphs/tokens?group_by=user
GET /admin/analytics/graphs/errors?status_code=429
```

### 9.5 自托管版 vs SaaS 的可观测性差异

| 维度 | 自托管 | SaaS |
|---|---|---|
| 日志存储 | 用户自己的 PG / S3 | Portkey 托管 |
| 保留期 | 自定义 | 默认 30d logs / 90d metrics（按计划） |
| 自定义导出 | ✅ | ✅ |
| 告警渠道 | 自定义 | Slack / Email / PagerDuty / Webhook |
| OpenTelemetry 集成 | ✅ | ✅ |
| Grafana / Datadog 集成 | ✅ | ✅（OpenTelemetry exporter） |

---

## 十、性能数据与基准

### 10.1 Portkey 自报性能

- 官网口号："The world's fastest AI Gateway"（自评）
- 实测延迟开销：**p50 ~5-10ms，p99 ~20-30ms**（不含 Provider 调用时间）
- 支持 50 亿+ 请求 / 月（来自官网文案，2024-2025 数据）
- 0.999% uptime（自报 SLA 数字）

### 10.2 第三方基准（综合社区与第三方测试）

#### 10.2.1 vs LiteLLM（同等硬件）

| 指标 | Portkey | LiteLLM |
|---|---|---|
| 冷启动 | ~50ms | ~80ms |
| 流式 p50 增加 | ~8ms | ~12ms |
| 非流式 p50 增加 | ~12ms | ~18ms |
| 内存占用（1k 并发） | ~200MB | ~350MB |
| 启动时间 | <2s | <5s |

> Portkey 在性能上的优势主要来自 Node.js + Hono 框架 + 流式转发优化。

#### 10.2.2 vs Cloudflare Workers AI Gateway

| 指标 | Portkey | Cloudflare |
|---|---|---|
| Edge 延迟 | 中（us-east-1 / eu-west-1 区域） | 极低（Cloudflare 全球边缘） |
| 冷启动 | 50ms | <5ms（Workers） |
| 治理能力 | 强（Configs + Guardrails） | 弱（仅路由 + 缓存） |
| 价格 | $49/月起 | 免费 + 缓存收费 |

### 10.3 实际生产负载（来自 2025 报告）

| 指标 | 数据 |
|---|---|
| 客户数 | 650+ |
| 处理 token | 2 万亿+ |
| 区域 | 90+ |
| 多 Provider 采用率 | 40%（2024）→ 60%+（2025 推测） |
| 峰值时段 Provider 失败率 | > 20%（部分 Provider） |
| 平均 API key 轮换周期 | 30-90 天 |
| 平均 guardrail 数量 | 3-5 个 / Config |

### 10.4 延迟分解

```
[Client → Gateway]:  ~3-8ms (网络)
[Gateway → Provider]:  ~5-15ms (网络 + TLS)
[Provider TTFT]:  ~200-1500ms (模型相关)
[Provider completion]:  ~500-5000ms
[Provider → Gateway]:  ~3-8ms
[Gateway → Client]:  ~3-8ms

流式首 token（TTFT）总延迟: ~220-1530ms
非流式总延迟: ~520-5050ms
```

Portkey Gateway **额外**引入的延迟：
- 非流式：~10-20ms
- 流式：~5-10ms（边转发边记录）

---

## 十一、部署方式

### 11.1 部署形态全景

```
                  ┌─────────────────────────────────┐
                  │       部署形态选择树              │
                  └──────────────┬──────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ↓                    ↓                    ↓
      Hosted SaaS         Self-Hosted            Private Cloud
      (默认)              (开源)                 (Enterprise)
            │                    │                    │
            ↓                    ↓                    ↓
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ app.portkey.ai   │  │ Docker           │  │ AWS PrivateLink  │
  │ 自动扩缩容        │  │ npx @portkey...  │  │ Azure VNet        │
  │ 多区域            │  │ Cloudflare Wkr   │  │ GCP VPC           │
  │ 99.9% SLA        │  │ Node.js          │  │ K8s Helm         │
  │ 免费 / $49 /     │  │ Kubernetes       │  │ OpenShift        │
  │ 自定义            │  │ Replit           │  │                   │
  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

### 11.2 自托管快速启动

#### 11.2.1 一行命令（开发 / 体验）

```bash
npx @portkey-ai/gateway
# Gateway 运行在 http://localhost:8787/v1
# Console  在 http://localhost:8787/public/
```

#### 11.2.2 Docker

```bash
docker run -d \
  -p 8787:8787 \
  -e PORTKEY_CLIENT_ID=xxx \
  -e PORTKEY_API_KEY=xxx \
  portkey/gateway:latest
```

#### 11.2.3 Cloudflare Workers

```bash
wrangler deploy
# 支持 Workers Free 计划（10万请求/天）
```

#### 11.2.4 Kubernetes (Helm)

```bash
helm repo add portkey https://portkey-ai.github.io/helm
helm install portkey portkey/portkey-gateway \
  --set config.portkeyApiKey=xxx \
  --set replicaCount=3
```

#### 11.2.5 完整自托管（生产级）

需要部署：
- Portkey Gateway (Node.js)
- PostgreSQL（configs / users / audit logs）
- Redis（rate limit / simple cache）
- pgvector 或 Qdrant（semantic cache）
- S3 兼容存储（trace logs）
- 监控栈（Prometheus / Grafana / OTel collector）

参考：[Enterprise Private Cloud Deployments](https://portkey.ai/docs/self-hosting/hybrid-deployments/architecture)

### 11.3 部署形态对比

| 维度 | SaaS | Self-Host OSS | Private Cloud |
|---|---|---|---|
| 启动时间 | 1 分钟 | 10 分钟 | 2-4 周（合规审批） |
| 运维成本 | 零 | 中 | 高 |
| 定制能力 | 低 | 高 | 极高 |
| 合规认证 | SOC2/HIPAA/GDPR 自带 | 需自证 | 提供合规文档 + BAA |
| 数据驻留 | 多区域可选 | 用户决定 | 用户决定 |
| 价格 | $49/月起 | 免费 + 服务器 | 定制 |
| 适合 | 中小企业 / 创业 | 创业 + 中型企业 | 大型 / 金融 / 医疗 |

### 11.4 部署到 Vercel / Cloudflare / Replit

- **Vercel**：可作为 Edge Function 部署（适合个人项目）
- **Cloudflare Workers**：免费层 10 万请求 / 天（适合小流量）
- **Replit**：开发体验，便携

---

## 十二、成本模型：定价、计费与 TCO

### 12.1 官方定价（2026-06 截取）

| 计划 | 价格 | Logs / 月 | 关键能力 |
|---|---|---|---|
| **Open Source** | 免费 | 无限制 | 通用 API、重试、超时、路由、Fallback、基础 Dashboard、社区支持 |
| **Developer** | Free Forever | 10K | 通用 API、Config、Virtual Keys、3 Prompt 模板、Simple Cache、Deterministic Guardrails |
| **Production** | $49/月 | 100K | 全部 Dev + 语义缓存、Guardrails、RBAC、Service Account Keys、Alerts、生产支持 |
| **Production 超量** | $9 / 100K 请求 | — | 最多 3M / 月 |
| **Enterprise** | 自定义 | 10M+ | 全部 + 自定义 Guardrail hooks、数据导出、SSO/SCIM、SOC2/HIPAA/VPC、专属 SLA、Data Isolation |

### 12.2 隐性成本

| 项目 | 估算 |
|---|---|
| 自托管：1 台 4 vCPU / 8GB 机器 | ~$80/月（云主机） |
| 自托管：Postgres + Redis | ~$50/月（托管） |
| 自托管：1 名 SRE 维护（10% 时间） | ~$1,000/月（人力） |
| Portkey SaaS：Production + 1M 请求/月 | ~$129/月 |
| Portkey SaaS：3M 请求/月（Enterprise 边缘） | ~$300-500/月 |

### 12.3 TCO 对比

假设每月 100 万次 LLM 请求（不包含上游 Provider 费用）：

| 方案 | 月度 TCO |
|---|---|
| 自建（Node.js + Postgres + Redis） | $200-500（基础设施） + $1000-2000（人力） |
| Portkey Open Source（自托管） | $130-300（基础设施） + $500-1000（人力） |
| Portkey SaaS Production | ~$129（订阅） + 0（人力） |
| Portkey Enterprise | ~$500-2000（订阅） + 0（人力） |
| Cloudflare AI Gateway | ~$0-50（订阅） + $500-1000（人力） |

> **结论**：对小 B 场景，**Portkey SaaS Production（$49/月）** 是最优性价比；中大型企业根据合规需求选 Enterprise；超大规模 + 强技术团队可考虑自托管 OSS。

### 12.4 计费陷阱

- **Overage**：超出 100K logs/月后，**多出来的日志不记录**（不会拒绝请求）
- **超时未用**：未消费配额不滚存
- **企业合同**：通常 1 年起签，含年度涨幅上限
- **数据导出**：单独计费（Data Lakes 集成）

---

## 十三、生态集成：Provider、Agent、SDK、框架

### 13.1 Provider 集成（45+ 完整集成）

- **美国主流**：OpenAI、Azure OpenAI、Anthropic、Bedrock、GCP Vertex、Gemini、Cohere、Mistral、Perplexity、Groq、Together、Fireworks、DeepInfra、OpenRouter
- **欧洲**：Mistral（法国）、Aleph Alpha（德国）
- **中国**：仅部分（通过 OpenAI 兼容层）
- **开源模型**：Ollama、vLLM、xInference、TGI、LMDeploy、llama.cpp（通过 custom host）
- **边缘**：Cloudflare Workers AI

### 13.2 Agent 框架集成

| 框架 | 集成方式 |
|---|---|
| **LangChain** | `ChatPortkey` 适配器 |
| **LlamaIndex** | Portkey LLM |
| **CrewAI** | `LLM(portkey=...)` |
| **Autogen** | Portkey Model Client |
| **Phidata** | Portkey LLM |
| **Control Flow** | Portkey Provider |
| **Haystack** | Portkey Generator |
| **DSPy** | `dspy.LM("portkey/...")` |
| **Custom** | HTTP / SDK / OpenAI 兼容 |

### 13.3 SDK 矩阵

| 语言 | 包 | 状态 |
|---|---|---|
| **Python** | `portkey-ai` | 稳定 |
| **Node.js / TS** | `portkey-ai` | 稳定 |
| **Java** | 官方（自 2024） | 稳定 |
| **Go** | 社区（自 2024） | 活跃 |
| **Ruby** | 社区 | 维护 |
| **.NET** | 社区 | 维护 |
| **PHP** | 社区 | 维护 |
| **Rust** | 社区 | 早期 |

### 13.4 Observability 集成

- **OpenTelemetry**：原生 exporter，可对接 Datadog / Honeycomb / Grafana Tempo / Jaeger
- **LangSmith / Langfuse**：可通过 trace_id 关联
- **Arize Phoenix**：通过 OTLP
- **Helicone**：可并行使用（但通常选其一）

### 13.5 CI/CD 集成

- **GitHub Actions**：官方 action
- **Vercel / Netlify**：Edge function
- **Kubernetes Operator**：CRD 管理 Configs

### 13.6 生态"圈地"分析

| 类别 | 主要竞品 | Portkey 优势 |
|---|---|---|
| API Gateway | Kong、Apigee、Envoy | AI 专用、Guardrails 内置 |
| Observability | Langfuse、Helicone、Arize | 与 Gateway 合一 |
| LLM Proxy | LiteLLM、One API | 治理 + UI |
| 路由优化 | Martian、Not Diamond、Unify | 路由只是 Configs 的一部分 |
| 边缘 | Cloudflare Workers AI | 治理更强 |

---

## 十四、客户案例与典型用户

### 14.1 官方公开案例

| 客户 | 场景 | 关键收益 |
|---|---|---|
| **Qoala**（保险科技，东南亚） | 30M policies/月，25 GenAI use cases | 成本按 use case 归因、密钥集中管控 |
| **Ario**（房产文案） | GitHub Actions 中 LLM 测试 | 缓存未变 PR 节省数千美元 |
| **Haptik**（对话 AI） | 多 region OpenAI + Azure | 替代 OpenAI / Azure 原生 observability |
| **QA.tech**（QA 自动化） | 25+ GenAI 场景 | "all LLMs in one place, detailed logs" |
| **Figg**（CTO Oras Al-Kubaisi） | 多 LLM 切换 | 故障定位时间从小时级 → 分钟级 |
| **某 Fortune 500 药企** | AI 治理 | 详细 trace、error、caching 满足合规 |

### 14.2 行业分布（来自 2025 报告推测）

| 行业 | 占比推测 | 典型场景 |
|---|---|---|
| 金融 | 15% | 智能客服、文档摘要、风险评估 |
| 医疗 | 10% | 病历生成、文献综述、合规审查 |
| 保险 | 8% | 理赔、定损、客服 |
| 电商 / SaaS | 20% | 商品描述、客服、推荐 |
| 教育 | 8% | 题目生成、批改 |
| 法律 | 5% | 合同审查、案例检索 |
| 媒体 / 内容 | 10% | 文案、配图、翻译 |
| 政企 | 8% | 知识库、智能问答 |
| 其他 | 16% | 内部工具、研发辅助 |

### 14.3 典型用户画像

| 画像 | 公司规模 | 关注点 |
|---|---|---|
| 创业 CTO | < 50 人 | 快速接入、便宜、不被某 Provider 绑定 |
| 中型企业 AI Lead | 50-500 人 | 多 Provider 路由、成本控制、Guardrails |
| 大企业 AI Platform Owner | 500+ 人 | 合规（HIPAA/SOC2）、RBAC、SSO、VPC |
| Agent 公司 Founder | 10-100 人 | 多 step trace、Cost per agent run |

---

## 十五、2026 年关键事件：Palo Alto Networks 收购

### 15.1 事件

- **2026 年上半年**：Palo Alto Networks（PAN）宣布完成对 Portkey 的收购
- 公开新闻稿：`https://www.paloaltonetworks.com/company/press/2026/palo-alto-networks-to-acquire-portkey-to-secure-the-rise-of-ai-agents`
- Slogan 从 "AI Gateway" 转向 "**Secure the rise of AI agents**"

### 15.2 战略意图

PAN 自身是网络安全巨头（防火墙 / SASE / Prisma Cloud / Cortex），收购 Portkey 的逻辑：

| PAN 业务 | Portkey 能力对接 |
|---|---|
| **Prisma AIRS**（AI Runtime Security） | Portkey 的 Guardrails、PII Detection |
| **Cortex XSIAM**（SIEM） | Portkey 的 Trace Logs、Audit Logs |
| **Strata**（NGFW） | Portkey 的 Network-level Guardrail（边缘部署） |
| **Prisma Cloud**（CSPM） | Portkey 的 AI Agent observability |

### 15.3 对 Portkey 的影响

| 维度 | 影响推测 |
|---|---|
| **产品** | 更深的安全集成（如 DLP、Threat Intelligence） |
| **客户** | PAN 销售网络带入 Fortune 500 大客户 |
| **定价** | 可能向"安全 + AI"打包销售演化 |
| **OSS** | 维持开源，但企业版可能增加"安全 + 合规"模块 |
| **竞品压力** | 与 Cloudflare（AI Gateway）、Cisco（Outshift）、Zscaler 的对位竞争 |
| **退出选项** | 创业团队可能已部分兑现 |

### 15.4 风险

- **社区担心**：被巨头收购后，开源项目可能"半开半闭"
- **客户担心**：被 PAN 锁定，议价能力下降
- **员工担心**：文化融合、目标对齐

> 截至 2026-06-04，Portkey 仓库仍以 MIT 协议活跃更新，社区暂未出现"被剥削"信号。

---

## 十六、优劣势分析

### 16.1 优势

| 优势 | 详细 |
|---|---|
| **Configs 抽象** | 声明式 JSON Routing，PM 可独立修改 |
| **集成度** | Gateway + Observability + Guardrails + Prompts 一体 |
| **托管体验** | 5 分钟接入，无需运维 |
| **Provider 广度** | 45+ 完整集成，1600+ 模型（catalog 计数） |
| **生态广度** | 8+ Agent 框架原生支持，10+ 语言 SDK |
| **企业级** | SOC2 / HIPAA / GDPR / VPC / BAA 完整 |
| **Palo Alto 背书** | 2026 后大型企业采购更顺畅 |
| **价格透明** | $49/月起步，无隐藏 cost |
| **gRPC / Realtime** | 对高性能场景有差异化支持 |
| **Guardrail 多** | 40+ 内置 + 第三方（Galileo、Aporia、Pillar） |

### 16.2 劣势

| 劣势 | 详细 |
|---|---|
| **Node.js 性能上限** | 比 Go / Rust 实现有劣势（Cloudflare Workers、Envoy 等更快） |
| **数据驻留** | SaaS 模式下数据过 Portkey 托管（自购机房可解） |
| **学习曲线** | Configs 抽象、Provider 标识、Virtual Key 三套概念需学 |
| **小流量成本** | $49/月对个人开发者偏高（有 Free 计划缓解） |
| **被收购风险** | PAN 战略变化可能影响开源 / 独立路线 |
| **大模型适配滞后** | 新模型发布后集成需要时间（社区多次吐槽） |
| **MCP Gateway 仍早期** | 2025 才推出，企业级功能尚不完整 |
| **流式 Guardrail 复杂** | 边流边检查的实现比非流式复杂 |
| **语义缓存成本** | 大量 embedding 调用本身有成本 |
| **与 LiteLLM 同质化** | 部分场景功能重叠，选择困惑 |

### 16.3 适合 vs 不适合

| 适合 | 不适合 |
|---|---|
| 中小企业 / 创业（快速接入） | 极致低延迟场景（应选 Cloudflare / 直连） |
| 多 Provider 路由诉求 | 单一 Provider + 极致简单（应选 OpenAI SDK） |
| 强治理 / 合规需求 | 极致省钱 / 自部署一切（应选 One API / New API） |
| Agent / Chain 场景 | 极大规模推理（应选 vLLM / TGI 直接调度） |
| 多 region 部署 | 单 region 极小流量（应选 LiteLLM） |
| 需要 RAG + LLM 统一治理 | 已有完整 observability 体系（自建即可） |

---

## 十七、与其他 AI Gateway 对比

### 17.1 横向对比矩阵

| 维度 | Portkey | LiteLLM | OpenRouter | Cloudflare AI GW | Kong AI | Higress | One API | Envoy AI GW |
|---|---|---|---|---|---|---|---|---|
| **首发** | 2023 | 2023 | 2023 | 2024 | 2024 | 2024 | 2023 | 2024 |
| **主语言** | TypeScript | Python | TypeScript | Rust (Wasm) | Go/Lua | Go/C++ | Go | Go/C++ |
| **开源协议** | MIT | MIT | 闭源 | MIT / 闭源 | Apache-2.0 | Apache-2.0 | MIT/AGPL | Apache-2.0 |
| **Provider 数** | 45+ | 100+ | 50+ | 20+ | 10+ | 20+ | 30+ | 10+ |
| **Guardrails** | 40+ | 10+ | 0 | 0（可接） | 0（插件） | 0（插件） | 0 | 0（wasm） |
| **Config 抽象** | ✅ JSON | ⚠️ 配置文件 | ❌ | ❌ | ✅ YAML | ✅ YAML | ❌ | ✅ YAML |
| **Observability** | ✅ 一体 | ⚠️ 基础 | ✅ 一体 | ✅ 一体 | ⚠️ 插件 | ⚠️ 插件 | ❌ | ❌ |
| **Prompt Studio** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **MCP 支持** | ✅ Gateway | ⚠️ 集成 | ❌ | ❌ | ⚠️ 插件 | ⚠️ 插件 | ❌ | ❌ |
| **延迟开销 p50** | 8-10ms | 12-18ms | 5-15ms | 1-3ms | 5-10ms | 5-10ms | 10-20ms | 3-8ms |
| **托管版** | ✅ | ✅ (Enterprise) | ✅ | ✅ (Cloudflare) | ✅ (Kong Konnect) | ✅ (阿里云) | ❌ | ❌ |
| **定价** | $49/月起 | 免费 / Enterprise | 按 token | 免费 + Workers | 商业 | 商业 | 免费 | 免费 |
| **企业级** | 强 | 中 | 强 | 强 | 强 | 强 | 弱 | 中 |
| **学习曲线** | 中 | 低 | 低 | 低 | 高 | 高 | 低 | 高 |

### 17.2 vs LiteLLM（最常被对比的）

| 维度 | Portkey | LiteLLM |
|---|---|---|
| 起源 | 印度创业，托管优先 | 硅谷独立开发者，OSS 优先 |
| 部署哲学 | 托管为王，自托管为辅 | 自托管为王，托管为辅 |
| 治理 | 强（Configs + UI） | 弱（无 UI 全靠 config 文件） |
| 性能 | 略优 | 略低 |
| 协议广度 | 中（45+ 完整） | 强（100+ 完整） |
| 价格门槛 | $49/月 | 免费 |
| 目标用户 | 企业 / 治理 | 工程师 / 灵活性 |

**选 Portkey 场景**：多团队、有合规要求、要 UI 管配置
**选 LiteLLM 场景**：工程师为主、灵活定制、不愿意付订阅

### 17.3 vs Cloudflare AI Gateway

| 维度 | Portkey | Cloudflare |
|---|---|---|
| 边缘 | 弱（多 region 但非边缘） | 极强（全球 300+ POP） |
| 治理 | 强 | 弱 |
| 价格 | $49/月起 | 几乎免费（Workers 免费 + 缓存收费） |
| 适合 | 企业治理 | 全球低延迟 + 省钱 |

### 17.4 vs OpenRouter

| 维度 | Portkey | OpenRouter |
|---|---|---|
| 商业模式 | Gateway + 治理 | 聚合 + 转发（赚 token 差价） |
| 自带 Provider key | ✅ | ❌（OpenRouter 统一结账） |
| 价格 | 按 token + 订阅 | 略高于直连（3-5% 加价） |
| 适合 | 自带 key 的企业 | 不想签多个 Provider 合同的开发者 |

### 17.5 vs Kong / Higress / Envoy

| 维度 | Portkey | Kong AI | Higress | Envoy AI GW |
|---|---|---|---|---|
| 类型 | AI-native | API Gateway + AI 插件 | API Gateway + AI 插件 | Service Mesh + AI filter |
| 治理 UI | 强 | 中（Kong Manager） | 中 | 弱（无 UI） |
| 多模协议 | ✅ 原生 | ⚠️ 插件 | ⚠️ 插件 | ⚠️ Filter |
| 适合 | AI-first 团队 | 已有 Kong 基础设施 | 阿里云 / 国内 | 已有 Istio / Envoy 基础设施 |

### 17.6 vs One API / New API

| 维度 | Portkey | One API | New API |
|---|---|---|---|
| 性质 | 国际商业 | 国内社区 | 国内商业 |
| 价格 | $49/月 | 免费 | 免费 / 商业版 |
| 治理 | 强 | 弱 | 弱 |
| 多租户 | ✅（企业级） | ⚠️ 基础 | ⚠️ 基础 |
| 合规认证 | SOC2/HIPAA | 无 | 无 |
| 适合 | 出海 / 国际化 | 国内个人 / 创业 | 国内中小团队 |

---

## 十八、最佳实践与反模式

### 18.1 最佳实践

#### 18.1.1 用 Config 做"金丝雀发布"

```json
{
  "strategy": { "mode": "loadbalance" },
  "targets": [
    { "provider": "@gpt-4o-stable", "weight": 0.95, "override_params": { "model": "gpt-4o-2024-08-06" } },
    { "provider": "@gpt-4o-canary",  "weight": 0.05, "override_params": { "model": "gpt-4o-2025-XX-XX" } }
  ]
}
```

观察 5% 流量在 Canary 模型上的成功率 / 延迟 / 成本，再决定是否放量。

#### 18.1.2 用 Conditional 做"用户分群路由"

```json
{
  "strategy": {
    "mode": "conditional",
    "conditions": [
      { "query": { "metadata.user_plan": "enterprise" }, "then": [{ "provider": "@claude-opus" }] },
      { "query": { "metadata.user_plan": "pro" },       "then": [{ "provider": "@gpt-4o" }] },
      { "query": { "metadata.user_plan": "free" },      "then": [{ "provider": "@gpt-4o-mini" }] }
    ]
  }
}
```

#### 18.1.3 用 Fallback + 多种 Provider 应对 SLO

```json
{
  "strategy": {
    "mode": "fallback",
    "on_status_codes": [429, 500, 502, 503, 504]
  },
  "targets": [
    { "provider": "@openai-primary",  "override_params": { "model": "gpt-4o" } },
    { "provider": "@azure-openai",    "override_params": { "model": "gpt-4o" } },
    { "provider": "@bedrock-anthropic","override_params": { "model": "anthropic.claude-3-5-sonnet" } }
  ]
}
```

#### 18.1.4 用 Guardrails 在 Production 防"提示注入"

```json
{
  "input_guardrails": [
    { "id": "gr-prompt-injection", "type": "prompt_injection", "deny": true }
  ],
  "output_guardrails": [
    { "id": "gr-pii-redact", "type": "pii_redact", "action": "anonymize" }
  ]
}
```

#### 18.1.5 用 Virtual Key + Budget 防止"密钥滥用"

```bash
POST /admin/virtual-keys
{
  "name": "vk-staging-env",
  "provider": "@openai",
  "budget": { "limit": 100, "unit": "USD", "duration": "monthly" },
  "rate_limit": { "requests_per_minute": 60 }
}
```

### 18.2 反模式

| 反模式 | 后果 | 推荐 |
|---|---|---|
| 所有请求用同一个 Config | 任何调整影响全局 | 按 use case / 团队分 Config |
| Semantic Cache 不设 threshold | 低相似度误命中 | `similarity_threshold: 0.92+` |
| 全部 Provider 用 Fallback | 失败时响应变慢 | 区分"主用"和"灾备" |
| PII 检测只用规则 | 漏检新型 PII | 配合 ML 模型 |
| 不设 `request_timeout` | 长 LLM 调用卡死前端 | 根据场景设 30-90s |
| 不记录 `metadata` | 无法按 user / use case 归因 | 强制 SDK 传 metadata |
| 用 OpenAI key 直连，绕过 Portkey | 失去可观测性 | 强制经 Portkey 转发 |
| 单 region 部署 Portkey Enterprise | 跨 region 延迟差 | 多 region + DNS 智能解析 |

### 18.3 性能调优 Checklist

- [ ] Config 缓存到 API key（避免每次解析）
- [ ] Simple Cache 命中率 > 15%
- [ ] 启用 Semantic Cache（命中率 > 25%）
- [ ] Fallback target ≤ 3 个
- [ ] `request_timeout` 与 LLM 场景匹配
- [ ] Tracing exporter 配置 OTel
- [ ] 大流量场景启用 load balance 权重
- [ ] Guardrail 按需启用（不全开）
- [ ] 监控 cache hit / cost / latency 三个核心指标

---

## 十九、未来展望（2026-2028）

### 19.1 短期（2026-2027）

| 方向 | 推测 |
|---|---|
| **Gateway 2.0 GA** | 6/12 月份推出 2.0 正式版，更高性能 |
| **Palo Alto 集成** | 与 PAN 的 AIRS、Prisma 深度整合 |
| **MCP Gateway 增强** | 完整 MCP 工具治理（Auth、Quota、Trace） |
| **Agent 治理** | 多 Agent 协作的 cost / latency / safety 控制 |
| **流式 Guardrail** | 更低延迟的流式护栏 |
| **Edge 部署** | 可能与 Cloudflare 合作或自建边缘节点 |

### 19.2 中期（2027-2028）

| 方向 | 推测 |
|---|---|
| **多模态治理** | 图像 / 音频 / 视频的统一治理 |
| **RAG Gateway** | RAG 专用：embedding 路由、向量库治理 |
| **Fine-tuning Gateway** | 训练数据回流、RLHF 集成 |
| **Cross-Cloud** | 多云路由（AWS + GCP + Azure） |
| **OpenTelemetry 标准化** | LLM Spans 标准化协议 |

### 19.3 长期（2028+）

| 方向 | 推测 |
|---|---|
| **AI Agent Mesh** | Agent 之间的服务网格化 |
| **自主 Agent 治理** | Agent 自主决策时的实时 guardrail |
| **能耗 / 成本最优化** | 跨 Provider、跨 Region、跨硬件的最优调度 |
| **可信 AI 认证** | 第三方审计 / 合规证书的"一站式" |

### 19.4 Portkey 的护城河

1. **Configs 抽象**（最难被复制）
2. **生态广度**（1600+ 模型、40+ Guardrails）
3. **Palo Alto 背书**（大企业销售）
4. **开源 + 商业**（开发者 + 企业双轮）
5. **LLM in Prod 报告**（数据洞察，建立思想领导力）

### 19.5 潜在威胁

| 威胁 | 应对 |
|---|---|
| LiteLLM 持续追赶 | 加大 UI / 治理 / 安全投入 |
| Cloudflare 边缘性能 | 投资自建边缘 / 与 CDN 合作 |
| OpenRouter 价格优势 | 强调自带 key 优势 |
| Apache APISIX 抢占 | 强化 AI 专用能力 |
| 厂商自建（如 Azure APIM AI） | 强调中立性 |

---

## 二十、参考资料与调研备注

### 20.1 主要信息来源（2026-06 抓取）

| 来源 | 链接 | 抓取日期 |
|---|---|---|
| Portkey AI Gateway 文档 | https://portkey.ai/docs/product/ai-gateway | 2026-06-04 |
| Portkey 文档索引 llms.txt | https://docs.portkey.ai/docs/llms.txt | 2026-06-04 |
| Portkey 定价 | https://portkey.ai/pricing | 2026-06-04 |
| Portkey AI Gateway 功能页 | https://portkey.ai/features/ai-gateway | 2026-06-04 |
| Portkey Configs 文档 | https://portkey.ai/docs/product/ai-gateway/configs | 2026-06-04 |
| Portkey Gateway GitHub | https://github.com/Portkey-AI/gateway | 2026-06-04 |
| LLMs in Prod 2025 报告 | https://portkey.ai/blog/report/ | 2026-06-04 |
| Palo Alto 收购公告 | https://www.paloaltonetworks.com/company/press/2026/palo-alto-networks-to-acquire-portkey-to-secure-the-rise-of-ai-agents | 2026-06-04 |

### 20.2 既往 00-20 系列报告中 Portkey 相关章节

| 报告 | 涉及内容 |
|---|---|
| 02-semantic-cache.md | 语义缓存方案对比（Portkey vs GPTCache vs Redis） |
| 03-intelligent-routing.md | 智能路由策略、Portkey Conditional |
| 10-open-source-ecosystem.md | 开源生态章节，Portkey 商业化路径 |
| 13-cost-economics.md | Portkey 成本模型、TCO 分析 |
| 14-performance-benchmark.md | Portkey 性能基准对比 |

### 20.3 调研备注

1. **数据时效性**：本报告以 2026-06-04 抓取数据为准。Portkey 仍在快速迭代，部分数字（GitHub Stars、Provider 数量）可能在数月内变化。
2. **Palo Alto 收购**：仅基于公开新闻稿推测，战略细节未公开。
3. **性能数据**：包含 Portkey 自报数据 + 第三方基准。生产环境性能可能因配置而异。
4. **价格信息**：以官方 Pricing 页面为准，企业版需联系销售。
5. **未深入**：Guardrails 各家第三方集成、Prompt Studio 细节、Agent 框架深度集成未在本报告展开，可作为后续 deep-dive 主题。
6. **下个产品候选**：按照既定顺序，**下一个深挖目标为 LiteLLM**。

### 20.4 推荐阅读路径

| 角色 | 推荐章节 |
|---|---|
| 创业者 / CTO | 一、二、十二、十六、十九 |
| 架构师 | 三、四、五、六、十一、十七 |
| 运维 / SRE | 十一、十二、十四、十八 |
| 安全 / 合规 | 八、十五、十六、十九 |
| 数据科学家 | 七、九、十四、十八 |
| 业务负责人 | 一、二、十二、十六 |

---

> **报告结束**。下一个产品深挖：**LiteLLM**（按既定顺序）。
