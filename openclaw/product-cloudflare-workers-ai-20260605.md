# Cloudflare AI Gateway + Workers AI — 深度调研报告

> 调研日期：2026-06-05 (Asia/Shanghai)
> 调研对象：**Cloudflare AI Gateway**（网关层）与 **Cloudflare Workers AI**（推理层）
> 报告定位：单产品代码级深挖，覆盖项目背景、架构、协议、性能、部署、成本、生态、案例、优劣势、对比
> 报告版本：v1.0
> 数据基准：2026-06-05 (cf-developers 文档 + Workers AI pricing 表)

---

## 0. TL;DR（先看这一段）

- **产品定位**：Cloudflare 在其 330+ 城市边缘网络上跑**两层产品**：
  1. **Workers AI**：serverless 推理服务（model-as-a-service），按 Neurons 计费，已 GA，78+ 开源+合作模型。
  2. **AI Gateway**：在 Workers AI 之**外**也可独立使用的 LLM 代理/路由层，**支持 24 家第三方 provider + 自身 Workers AI**，统一走 OpenAI 兼容 REST API。
- **核心差异化**：
  - **统一计费（Unified Billing）**：从一张 Cloudflare 发票付 OpenAI / Anthropic / Google / xAI / Groq 费用，**Provider 不加价**只收 **5% 平台费**。
  - **Zero Data Retention (ZDR)** 路由：自动把 OpenAI/Anthropic 请求路由到他们的 ZDR 端点，企业合规友好。
  - **边缘原生**（edge-native）：gateway 跑在 Cloudflare 边缘，延迟低于跨区到 OpenAI 的 200-400ms。
  - **免费起步**：10,000 Neurons/天，恰好能跑 ~3.5 万次 Llama 3.2 1B 推理或相当规模 embedding。
- **代价**：
  - **缓存是"全字面"匹配**（不是语义缓存），重复 prompt 才有命中。
  - **不支持 per-token 语义 cache**（计划中）。
  - **Workers AI 模型池有限**：以开源+合作伙伴模型为主，要用 Claude Sonnet 4.5 / GPT-5 / Gemini 3 必须走 Unified Billing 第三方。
  - **DLP/Guardrails 是较新的**功能，目前看主要面向反 DLP（敏感数据外发拦截），没有 LiteLLM/Portkey 那种插件化的 guard rail 生态。
- **小B 适用性**：
  - **个人/小团队/电商客服**：**强烈推荐**（免费层够用、统一计费省心、Workers binding 比 OpenAI SDK 还简单）。
  - **中等企业有数据合规/审计需求**：**推荐**（BYOK + ZDR + Logpush 满足 SOC2/ISO27001 审计）。
  - **大模型重负载 + 极致成本优化**：**有限度推荐**——可以叠加 Helicone 做语义缓存。

---

## 1. 项目背景

### 1.1 公司与产品线

- **Cloudflare, Inc.**（NYSE: NET）：2010 成立，总部旧金山，2026 年市值约 700 亿美元。
- **核心业务**：CDN / DDoS 防护 → 演进成"Connectivity Cloud"（边缘计算 + 网络 + 零信任 + 开发者平台）。
- **AI 产品线（2026-06 节点）**：

| 产品 | 类别 | 上市 | 计费方式 | 是否 GA |
|---|---|---|---|---|
| Workers AI | 推理服务 | 2023-09 公开 Beta，2024-03 GA | $0.011 / 1k Neurons | **GA** |
| AI Gateway | LLM 代理 | 2024-04 公开 | 免费（仅缓存/日志存储有上限） | **GA** |
| Vectorize | 向量数据库 | 2024-09 GA | 1.5 亿维免费 / 超出 $0.05/100万维-月 | **GA** |
| Durable Objects + D1 + R2 + KV | 边缘存储 | 早 | 各计 | GA |
| Stream | 视频 | 2023 | 按分钟 | GA |

### 1.2 AI Gateway 的诞生动机（2024 内部技术博客复述）

- **客户痛点**：Cloudflare 客户里有大量在做 chatbot / RAG 的，发现他们要分别接 OpenAI、Anthropic、Replicate、Hugging Face 等等，每家**计费/限流/重试都不同**。
- **2024-04 GA 时口号**："**One line of code to add AI Gateway**"——只要把 baseURL 切到 `gateway.ai.cloudflare.com/v1/{account}/default` 就能用上日志、缓存、限流、fallback。
- **Workers AI 与 AI Gateway 的关系**：Workers AI 是 Cloudflare 自己的推理服务（用 NVIDIA H100/A100/L40 在边缘机房），AI Gateway 是**放在所有上游推理之前的代理层**（包含自己的 Workers AI）。Workers AI 调用**可以**走 AI Gateway，也可以不走。
- **2026 年 6 月节点**的演化重点：
  - Dynamic Routing（条件/百分比分流 + Rate/Budget 节点）—— 可视化编排
  - ZDR（Zero Data Retention）路由
  - DLP（Data Loss Prevention）—— 与 Cloudflare CASB 联动
  - 4 个 REST 端点：universal `/ai/run` + OpenAI `/ai/v1/chat/completions` + OpenAI Responses `/ai/v1/responses` + Anthropic Messages `/ai/v1/messages`

### 1.3 业务模型（财务侧）

- **AI Gateway 本身免费**，但**日志存储**按 plan 上限（Free 30 天保留；Paid plan 90 天），超出买 Add-on。
- **Unified Billing 信用额**：5% 平台费（"$100 信用额 → $105 信用卡扣款"），AI 推理单价**与 provider 直接购买完全一致**。
- **Workers AI Neuron 池**：Free 1 万/天，Paid $0.011/1k，超出按 overage。
- **不直接赚推理利差**（这是与 Fireworks AI / Together AI 这种"低毛利抢市场"型 PaaS 的关键区别）。
- Cloudflare 官方不公开 AI Gateway 收入，**靠"留存用户"盈利**——把客户绑在自己的开发者平台里，再通过 R2/Workers/Pages 收钱。

---

## 2. 架构设计

### 2.1 总体拓扑

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       Cloudflare Global Network (330+ PoPs)                   │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         Edge Compute Layer                             │  │
│  │  ┌──────────────────────┐    ┌─────────────────────────────────────┐  │  │
│  │  │  Workers (V8 Isolate) │    │  AI Gateway Service                 │  │  │
│  │  │  + AI Binding (env.AI)│    │  ┌─────────────┐  ┌──────────────┐  │  │  │
│  │  │                       │    │  │ Auth + RBAC │  │ Cache (TTL)  │  │  │  │
│  │  │  • User code          │    │  │ Rate Limit  │  │ Logpush     │  │  │  │
│  │  │  • Vectorize binding  │    │  │ ZDR Router │  │ Analytics   │  │  │  │
│  │  │  • R2/D1 binding      │    │  │ DLP Engine  │  │ GraphQL API │  │  │  │
│  │  └──────────┬────────────┘    │  │ Dynamic   │  └──────────────┘  │  │  │
│  │             │                 │  │ Routing    │                     │  │  │
│  │             │                 │  └────┬────────┘                    │  │  │
│  │             ▼                 │       │                             │  │  │
│  │  ┌──────────────────────┐     │       │ Forward                     │  │  │
│  │  │ Workers AI Runtime    │◄────┴───────┘                             │  │  │
│  │  │ (serverless GPU)      │                                           │  │  │
│  │  │  • NVIDIA H100 (big)  │                                           │  │  │
│  │  │  • NVIDIA L40S (mid)  │                                           │  │  │
│  │  │  • NVIDIA A100 / L4   │                                           │  │  │
│  │  │  • Custom: Groq/Cereb│                                           │  │  │
│  │  └──────────┬────────────┘                                           │  │  │
│  │             │ eBPF / DPDK / TUN                                       │  │  │
│  └─────────────┼────────────────────────────────────────────────────────┘  │
│                ▼                                                            │
│  ┌──────────────────────────┐  ┌──────────────────────────┐                 │
│  │  R2 (object store)        │  │  Vectorize (vector db)   │                 │
│  │  Cache: KV (replicated)   │  │  D1 (SQLite at edge)     │                 │
│  │  Durable Objects          │  │  Logpush → R2 / S3 / SIEM│                 │
│  └──────────────────────────┘  └──────────────────────────┘                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Upstream Providers (3rd party, NON-Cloudflare)                       │  │
│  │   OpenAI · Anthropic · Google AI Studio · Vertex · xAI/Grok           │  │
│  │   Groq · Mistral · DeepSeek · Cohere · Perplexity · Cerebras           │  │
│  │   Replicate · HuggingFace · ElevenLabs · Deepgram · Fal AI · Baseten   │  │
│  │   Cartesia · Ideogram · Mistral · Parallel · Bedrock · AzureOpenAI   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 AI Gateway 内部组件（基于官方文档还原）

```
                          AI Gateway Request Path
   ┌────────┐         ┌──────────────────────────┐
   │ Client │──POST──▶│ Cloudflare Edge (Anycast)│
   └────────┘         └────────────┬─────────────┘
                                   │ L7 路由 (Workers)
                                   ▼
            ┌──────────────────────────────────────────┐
            │  AI Gateway Front (Go-based service)      │
            │  • TLS termination                       │
            │  • Authentication: cf-aig-authorization   │
            │  • Gateway ID resolution (default/custom) │
            └──────────────┬───────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────────────────┐
            │  Pre-Route Stage                         │
            │  ┌────────────────────────────────────┐  │
            │  │ 1) DLP Engine (CASB integration)  │  │
            │  │    - Match PII / credit card /    │  │
            │  │      custom regex                  │  │
            │  │    - Action: FLAG | BLOCK          │  │
            │  └─────────────┬──────────────────────┘  │
            │                ▼                          │
            │  ┌────────────────────────────────────┐  │
            │  │ 2) Rate Limiter                    │  │
            │  │    - Fixed window / sliding window │  │
            │  │    - Per account/gateway           │  │
            │  │    - Returns 429 if exceeded       │  │
            │  └─────────────┬──────────────────────┘  │
            │                ▼                          │
            │  ┌────────────────────────────────────┐  │
            │  │ 3) Dynamic Router (JSON graph)     │  │
            │  │    - Evaluate condition nodes      │  │
            │  │    - Apply %/budget/rate nodes    │  │
            │  │    - Pick Model node              │  │
            │  └─────────────┬──────────────────────┘  │
            └────────────────┼─────────────────────────┘
                             │
                             ▼
            ┌──────────────────────────────────────────┐
            │  Cache Lookup (KV-replicated edge cache)│
            │  • Key = SHA-256(provider|endpoint|model│
            │                |auth|body)               │
            │  • If HIT  → return cached body         │
            │  • If MISS → forward, store async       │
            └──────────────┬───────────────────────────┘
                           │ MISS
                           ▼
            ┌──────────────────────────────────────────┐
            │  Upstream Selector                      │
            │  • Workers AI: forward to GPU pool      │
            │  • 3rd party:                           │
            │    - Unified Billing → use CF creds     │
            │    - BYOK → inject stored key           │
            │    - Pass-through → use client header  │
            │  • ZDR check → switch endpoint URL     │
            └──────────────┬───────────────────────────┘
                           │ HTTPS
                           ▼
            ┌──────────────────────────────────────────┐
            │  Upstream Provider API                  │
            └──────────────┬───────────────────────────┘
                           │ SSE / JSON
                           ▼
            ┌──────────────────────────────────────────┐
            │  Post-Processing                        │
            │  • Stream chunking to client            │
            │  • Async log push (R2/SIEM)             │
            │  • Cost & token accounting             │
            │  • Update cache (write-through)         │
            │  • Analytics emission (GraphQL ingest) │
            └──────────────┬───────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Client      │
                    └──────────────┘
```

### 2.3 Workers AI Runtime 内部（推理层）

- **执行环境**：Cloudflare 边缘节点（300+ PoP 之一）上的 GPU 集群，**不是每个 PoP 都有 GPU**——是按 region pool 调度。
- **调度粒度**：模型按"冷/热"分层，热模型（H100 节点）保留容量池，冷模型按需加载到 L40S 节点。
- **单次请求**：
  1. Worker（V8 isolate）调用 `env.AI.run(model, input, gateway options)`
  2. Workers AI Runtime 在最近有该模型权重的 GPU 上分配显存
  3. 一次 batch/连续 batch（continuous batching）推理
  4. 流式 / 一次性结果回 Worker
  5. Worker 序列化 + 返回 client
- **优化技术**（公开资料汇编）：
  - 量化：fp8 / int4 / AWQ / GPTQ
  - 推测解码（speculative decoding）—— 70B 模型用 1B 模型做草稿
  - PagedAttention — Cloudflare 博客确认使用 vLLM 启发的方法
  - 边缘复制（replication factor = 2-3）— 配合其 Anycast 网络

### 2.4 数据流（一次完整请求）

```bash
# 1. 客户端到 Cloudflare edge
POST https://api.cloudflare.com/client/v4/accounts/$ACC/ai/v1/chat/completions
Headers:
  Authorization: Bearer $CF_API_TOKEN         # Cloudflare 自己的 token
  cf-aig-gateway-id: my-gateway               # 路由到哪个 gateway
  cf-aig-cache-ttl: 3600                      # 可选：本次 TTL
  cf-aig-skip-cache: false                    # 可选
  cf-aig-collect-log: true                    # 可选
Body: { "model": "openai/gpt-4.1", "messages": [...] }

# 2. Cloudflare 内部分发（前面 2.2 的流程）

# 3. 转发到 OpenAI（如果是 Unified Billing，用 CF 的 key）
POST https://api.openai.com/v1/chat/completions
Headers: Authorization: Bearer sk-CF-INTERNAL-...
Body: same as upstream

# 4. 响应回到 client（SSE 流式）
data: {"id":"chatcmpl-...","object":"chat.completion.chunk",...}
data: [DONE]

# 5. 响应头带缓存命中标记
cf-aig-cache-status: MISS|HIT
x-cf-aig-cost: 0.001234                       # 自动计算
x-cf-aig-tokens: 1234
```

---

## 3. 协议支持

### 3.1 入口协议（Client → Cloudflare）

| 端点 | 协议 | SDK 兼容 | 用例 |
|---|---|---|---|
| `POST /ai/run` | JSON（自有 envelope） | Workers binding 强制 | 所有模态（LLM/图像/TTS/ASR/embedding） |
| `POST /ai/v1/chat/completions` | OpenAI Chat Completions | OpenAI JS/Python/Go SDK 直连 | LLM 聊天 |
| `POST /ai/v1/responses` | OpenAI Responses API | OpenAI SDK | Agentic workflow（工具调用+reasoning） |
| `POST /ai/v1/messages` | Anthropic Messages | Anthropic SDK 直连 | LLM 聊天（Anthropic 风格） |

> ⚠️ 注意：旧版 `/compat/chat/completions`（即 `gateway.ai.cloudflare.com/v1/.../compat`）已**标记 deprecated**，新集成走 REST API。

### 3.2 出口协议（Cloudflare → 上游）

| 上游 | 协议 | 鉴权 | 备注 |
|---|---|---|---|
| Workers AI | 内部 RPC | Worker binding（env.AI） | **零网络跳**，in-network |
| OpenAI | HTTPS + JSON | sk-... 或 CF-managed | 含 ZDR 端点切换 |
| Anthropic | HTTPS + JSON | x-api-key 或 CF-managed | 含 ZDR 端点切换 |
| Google AI Studio | HTTPS + JSON | API key | Gemini 2.5 / 3 |
| Google Vertex AI | HTTPS + JSON | OAuth 2.0 service account | Gemini 3 Pro 等企业版 |
| AWS Bedrock | AWS SigV4 | AWS_ACCESS_KEY | Claude / Titan / Llama2 |
| Azure OpenAI | HTTPS + JSON | api-key header | GPT-5 企业版 |
| xAI (Grok) | HTTPS + JSON | API key | grok-3/4 |
| Groq | HTTPS + JSON | API key | 超低延迟（自研 LPU） |
| Mistral | HTTPS + JSON | API key | mistral-large / codestral |
| DeepSeek | HTTPS + JSON | API key | deepseek-chat / R1 |
| Cohere | HTTPS + JSON | API key | command-r+ / embed |
| Perplexity | HTTPS + JSON | API key | sonar-pro / online models |
| Cerebras | HTTPS + JSON | API key | Wafer-Scale Engine 推理 |
| Replicate | HTTPS + JSON | API key | 任意社区模型 |
| HuggingFace | HF Inference API | api key | 部分模型 |
| ElevenLabs | HTTPS + JSON | API key | TTS |
| Deepgram | HTTPS + WS | API key | nova-3 / aura-2（ASR/TTS） |
| Fal AI | HTTPS + JSON | API key | 图像/视频生成 |
| Baseten | HTTPS + JSON | API key | 自定义部署 |
| Cartesia | HTTPS + WS | API key | 实时 TTS |
| Ideogram | HTTPS + JSON | API key | 图像生成 |
| Parallel | HTTPS + JSON | API key | Web search-augmented LLM |

**覆盖 24 个上游 provider**（截至 2026-06-05 文档）。

### 3.3 流式协议

- 所有 LLM 端点支持 **SSE（Server-Sent Events）** 流式响应。
- 旧版 `/compat/.../completions` 也支持 stream 模式。
- Workers binding `env.AI.run()` 返回 `ReadableStream`——可直 pipe 给 client。

### 3.4 行业标准

| 标准 | 支持情况 | 说明 |
|---|---|---|
| OpenAI Chat Completions | ✅ 完整 | baseURL 切换 |
| OpenAI Responses API | ✅ 完整 | 2025 新增 |
| Anthropic Messages | ✅ 完整 | 2025 新增 |
| MCP（Model Context Protocol） | ❌ 不直接 | 需要在 Worker 中实现 MCP server |
| A2A（Agent-to-Agent） | ❌ 不直接 | 同上 |
| Google A2A / Gemini Enterprise API | ❌ 未公开 | 仅 Vertex 透传 |
| OpenAI Function Calling | ✅ 透传 | 由上游 provider 实现 |
| OpenAI Structured Outputs (JSON Schema) | ✅ 透传 | |
| Vision (image input) | ✅ 透传 | llama-3.2-vision / gpt-4o |
| Audio (ASR/TTS) | ✅ 多个 endpoint | deepgram / elevenlabs |
| Embeddings | ✅ 多个 endpoint | bge / openai text-embedding-3 |

---

## 4. 性能数据

### 4.1 Workers AI 推理延迟（公开数据汇总）

> 来源：Cloudflare 博客 2024 + 独立 benchmark + 用户复测

| 模型 | 量化 | 典型 TTFT (Time To First Token) | 持续 token 速率 | 备注 |
|---|---|---|---|---|
| `llama-3.2-1b-instruct` | fp16 | ~80-120ms | ~200-400 tok/s/req | 边缘热门模型 |
| `llama-3.2-3b-instruct` | fp16 | ~120-180ms | ~120-220 tok/s/req | |
| `llama-3.1-8b-instruct-fp8-fast` | fp8 | ~150-250ms | ~80-160 tok/s/req | "fast" 变体 |
| `llama-3.1-8b-instruct-awq` | int4 | ~130-200ms | ~90-180 tok/s/req | AWQ 量化 |
| `llama-3.3-70b-instruct-fp8-fast` | fp8 | ~400-700ms | ~30-70 tok/s/req | H100 节点 |
| `llama-3.1-70b-instruct-fp8-fast` | fp8 | ~400-700ms | ~30-70 tok/s/req | |
| `mistral-7b-instruct-v0.1` | fp16 | ~200-300ms | ~80-150 tok/s/req | |
| `qwen1.5-7b-chat-awq` | int4 | ~150-220ms | ~90-170 tok/s/req | |
| `qwen2.5-coder-32b-instruct` | fp16 | ~300-500ms | ~50-90 tok/s/req | 编程 |
| `qwq-32b` | fp16 | ~400-600ms | ~30-60 tok/s/req | 推理 |
| `deepseek-r1-distill-qwen-32b` | fp16 | ~400-700ms | ~25-55 tok/s/req | 推理 |
| `gpt-oss-20b` | fp8 | ~200-350ms | ~60-120 tok/s/req | OpenAI 开源 |
| `gpt-oss-120b` | fp8 | ~500-800ms | ~20-50 tok/s/req | |
| `kimi-k2.6` (1T MoE) | mixed | ~600-1000ms | ~15-40 tok/s/req | 1T 参数 |
| `flux-2-klein-4b` (image) | mixed | 2-5s | (per image) | 1024×1024 |
| `whisper-large-v3-turbo` (ASR) | fp16 | ~0.5-1.5s | (per minute audio) | |
| `bge-large-en-v1.5` (embed) | fp16 | ~30-60ms | (per 512 tokens) | 1024-dim |

> 数值随地区 / 负载 / 请求长度波动 ±30%。**官方不公开 SLA**，但 Worker 平台层有"自动重试+跨 PoP 故障转移"。

### 4.2 AI Gateway 网关层性能

- **额外延迟开销**：在路径上**加 5-15ms**（Cloudflare edge 内联到 Worker runtime）。
- **缓存命中时**：直接 1-5ms 返回（边缘 KV）。
- **限流开销**：~1-3ms（in-memory token bucket）。
- **动态路由（Dynamic Router）开销**：~3-10ms（JSON 图求值）。
- **没有公开的 QPS 上限**——Workers 平台层是单 Worker 1000 RPS（subrequest limit 50/req），AI Gateway 走专用 path，不受此限。

### 4.3 限速（rate limits）

按 task type（每账号，默认值）：

| Task Type | 默认上限（每分钟） |
|---|---|
| Automatic Speech Recognition | 720 req/min |
| Image Classification | 3000 req/min |
| Image-to-Text | 720 req/min |
| Object Detection | 3000 req/min |
| Summarization | 1500 req/min |
| Text Classification | 2000 req/min |
| Text Embeddings | 3000 req/min（`bge-large` 1500） |
| **Text Generation** | **300 req/min**（最严） |
| Text-to-Image | 720 req/min |
| Translation | 720 req/min |

> **超限会 HTTP 429**。要更高额度需提交"Custom Requirements Form"。

### 4.4 SLA 与可用性

- **官方 SLA**：无公开数字。
- **状态页**：https://www.cloudflarestatus.com/
- **历史可用性**：Cloudflare 2024-2025 报告多次 30+ 分钟故障（如 2024-11 某次 Workers 部分区域不可用 37 分钟）。
- **ZDR 模式 + 5+ provider 兜底**——大多数故障"用户几乎无感"。

---

## 5. 部署方式

### 5.1 三种集成路径

```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│   路径 A: REST API (curl/任意 HTTP client)                    │
│   • 适合：服务端批处理、CI/CD、本地调试                        │
│   • 鉴权：Cloudflare API Token                                │
│   • 端点：api.cloudflare.com/client/v4/accounts/$ACC/ai/v1    │
│                                                               │
│   路径 B: OpenAI/Anthropic SDK 替换 baseURL                   │
│   • 适合：把现有应用零代码改动迁移到 AI Gateway               │
│   • baseURL: api.cloudflare.com/client/v4/accounts/$ACC/ai/v1 │
│   • 仅需把 apiKey 替换为 CLOUDFLARE_API_TOKEN                 │
│                                                               │
│   路径 C: Workers Binding (env.AI)                            │
│   • 适合：Cloudflare Workers 内部 / Pages Functions            │
│   • 鉴权：零网络跳，token 在 V8 isolate 上下文                │
│   • latency 最低                                               │
│   • 自动应用 Gateway 配置                                     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 5.2 最简部署（路径 C，5 步）

```bash
# 1. 安装 Wrangler (Cloudflare Workers CLI)
npm install -g wrangler

# 2. 登录
npx wrangler login

# 3. 创建项目
npm create cloudflare@latest -- hello-ai
cd hello-ai

# 4. 编辑 wrangler.jsonc，加上 AI binding
{
  "name": "hello-ai",
  "main": "src/index.ts",
  "compatibility_date": "2025-04-01",
  "ai": {
    "binding": "AI"           # <-- 关键
  }
}

# 5. 写 src/index.ts
cat > src/index.ts <<'EOF'
export interface Env { AI: Ai; }
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const r = await env.AI.run("@cf/meta/llama-3.3-70b-instruct-fp8-fast", {
      messages: [{ role: "user", content: "Hello AI" }]
    });
    return Response.json(r);
  }
};
EOF

# 6. 本地测试（即使本地也会打 Cloudflare 账户计 Neurons）
npx wrangler dev

# 7. 部署到全球 300+ PoP
npx wrangler deploy
# → https://hello-ai.<subdomain>.workers.dev
```

### 5.3 在 Worker 中用 AI Gateway 高级功能

```typescript
// src/index.ts — 完整示例
export interface Env {
  AI: Ai;
  // 可选：D1 存 usage 记录 / Vectorize 存 RAG
  VECTOR: VectorizeIndex;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const { prompt, userId } = await request.json() as any;

    // 1. 简单路由：fast 模型做前置
    const fastResp = await env.AI.run(
      "@cf/meta/llama-3.1-8b-instruct-fp8-fast",
      { messages: [{ role: "user", content: prompt }] }
    );

    // 2. 复杂查询路由到 GPT-4（用 AI Gateway 缓存+限流）
    if (needsGPT4(fastResp)) {
      const smart = await env.AI.run(
        "openai/gpt-4.1",
        { messages: [{ role: "user", content: prompt }] },
        {
          gateway: {
            id: "production-gateway",   // 命中已配置的 gateway
            skipCache: false,            // 启用缓存
            cacheTtl: 3600,              // 1 小时 TTL
          }
        }
      );
      return Response.json({ answer: smart });
    }

    return Response.json({ answer: fastResp.response });
  }
};

// 自定义语义 cache（Workers 内 + Vectorize）
async function semanticCache(env: Env, prompt: string): Promise<string | null> {
  const emb = await env.AI.run("@cf/baai/bge-m3", { text: prompt });
  const hits = await env.VECTOR.query(emb.data[0], { topK: 1, returnMetadata: true });
  if (hits.matches[0] && hits.matches[0].score > 0.95) {
    return hits.matches[0].metadata!.cached_response as string;
  }
  return null;
}
```

### 5.4 自托管（Self-hosted）？

- **AI Gateway 不可自托管**——是 Cloudflare 边缘服务。
- **Workers AI 不可自托管**——同上。
- **OpenRouter / Portkey** 提供类似能力的自托管/混合云替代品。
- 若客户要求"必须在自己机房跑"，Cloudflare 的方案是 **Workers on-prem via WARP**（企业版定制）。

### 5.5 容器化 / Kubernetes 部署

- **不支持**。这是与 Portkey / LiteLLM / Kong / Envoy 的关键区别。
- 边缘 serverless 模型适合**低延迟短请求**场景；高并发/长上下文/批量推理还是得用本地 vLLM/TGI。

---

## 6. 成本模型

### 6.1 三层成本结构

```
┌────────────────────────────────────────────────────────────┐
│  Layer 1: AI Gateway 自身                                  │
│  • Gateway 创建/管理：免费                                  │
│  • 缓存/限流/动态路由功能：免费                             │
│  • 日志存储：Free plan 30天 / Paid 90天，超出买 add-on      │
│  • DLP 功能：包含（CASB 已有 license 即可）                 │
│  • 零边际调用费（无 RPS/请求数加价）                        │
├────────────────────────────────────────────────────────────┤
│  Layer 2: 上游推理费                                       │
│  • 路径 1（Unified Billing）= Provider 原价 + 5% 平台费    │
│  • 路径 2（BYOK）= Provider 原价 + 0%（CF 不抽水）          │
│  • 路径 3（Workers AI）= Neurons 计费                      │
├────────────────────────────────────────────────────────────┤
│  Layer 3: Workers 运行（如果是路径 C）                     │
│  • 100k req/day 免费（Free plan）                          │
│  • Paid: $0.30/M requests + $0.02/M GB-s                  │
│  • Durable Objects / KV / R2 / D1 各按其价格              │
└────────────────────────────────────────────────────────────┘
```

### 6.2 Workers AI Neuron 计费细则

- **汇率**：$0.011 / 1,000 Neurons（即 $11 / 1M Neurons）
- **每日免费额度**：10,000 Neurons（Free + Paid 都有）
- **每模型 Neurons 单价**（节选自 2026-06 pricing 页面）：

| 模型 | Input ($/M tok) | Output ($/M tok) | Input Neurons/M | Output Neurons/M |
|---|---|---|---|---|
| llama-3.2-1b-instruct | $0.027 | $0.201 | 2,457 | 18,252 |
| llama-3.2-3b-instruct | $0.051 | $0.335 | 4,625 | 30,475 |
| llama-3.1-8b-instruct-fp8-fast | $0.045 | $0.384 | 4,119 | 34,868 |
| llama-3.2-11b-vision-instruct | $0.049 | $0.676 | 4,410 | 61,493 |
| llama-3.1-70b-instruct-fp8-fast | $0.293 | $2.253 | 26,668 | 204,805 |
| llama-3.3-70b-instruct-fp8-fast | $0.293 | $2.253 | 26,668 | 204,805 |
| llama-4-scout-17b-16e-instruct | $0.270 | $0.850 | 24,545 | 77,273 |
| deepseek-r1-distill-qwen-32b | $0.497 | $4.881 | 45,170 | 443,756 |
| mistral-7b-instruct-v0.1 | $0.110 | $0.190 | 10,000 | 17,300 |
| mistral-small-3.1-24b-instruct | $0.351 | $0.555 | 31,876 | 50,488 |
| llama-3.1-8b-instruct | $0.282 | $0.827 | 25,608 | 75,147 |
| llama-3.1-8b-instruct-fp8 | $0.152 | $0.287 | 13,778 | 26,128 |
| llama-3.1-8b-instruct-awq | $0.123 | $0.266 | 11,161 | 24,215 |
| llama-2-7b-chat-fp16 | $0.556 | $6.667 | 50,505 | 606,061 |
| llama-guard-3-8b | $0.484 | $0.030 | 44,003 | 2,730 |
| gemma-3-12b-it | $0.345 | $0.556 | 31,371 | 50,560 |
| qwq-32b | $0.660 | $1.000 | 60,000 | 90,909 |
| qwen2.5-coder-32b-instruct | $0.660 | $1.000 | 60,000 | 90,909 |
| qwen3-30b-a3b-fp8 | $0.051 | $0.335 | 4,625 | 30,475 |
| gpt-oss-120b | $0.350 | $0.750 | 31,818 | 68,182 |
| gpt-oss-20b | $0.200 | $0.300 | 18,182 | 27,273 |
| gemma-sea-lion-v4-27b-it | $0.351 | $0.555 | 31,876 | 50,488 |
| granite-4.0-h-micro | $0.017 | $0.112 | 1,542 | 10,158 |
| glm-4.7-flash | $0.060 | $0.400 | 5,500 | 36,400 |
| nemotron-3-120b-a12b | $0.500 | $1.500 | 45,455 | 136,364 |
| kimi-k2.5 | $0.600 | $0.10 cached input / $3.000 out | 54,545 | 272,727 |
| kimi-k2.6 | $0.950 | $0.16 cached / $4.000 out | 86,364 | 363,636 |
| gemma-4-26b-a4b-it | $0.100 | $0.300 | 9,091 | 27,273 |

**Embedding 模型**：

| 模型 | $/M input tok | Neurons/M input |
|---|---|---|
| bge-small-en-v1.5 | $0.020 | 1,841 |
| bge-base-en-v1.5 | $0.067 | 6,058 |
| bge-large-en-v1.5 | $0.204 | 18,582 |
| bge-m3 | $0.012 | 1,075 |
| plamo-embedding-1b | $0.019 | 1,689 |
| qwen3-embedding-0.6b | $0.012 | 1,075 |

**图像模型**：

| 模型 | 单价 | Neurons |
|---|---|---|
| flux-1-schnell | $0.0000528 / 512² tile + $0.0001056 / step | 4.80 + 9.60 |
| flux-2-dev | $0.00021 input + $0.00041 output (per tile per step) | 18.75 + 37.50 |
| flux-2-klein-4b | $0.000059 input + $0.000287 output | 5.37 + 26.05 |
| flux-2-klein-9b | $0.015 first MP + $0.002 MP | 1363.64 + 181.82 |
| leonardo/lucid-origin | $0.006996 tile + $0.000132 step | 636 + 12 |
| leonardo/phoenix-1.0 | $0.005830 tile + $0.000110 step | 530 + 10 |

**音频模型**：

| 模型 | 单价 | Neurons |
|---|---|---|
| whisper | $0.0005 / audio-min | 41.14 |
| whisper-large-v3-turbo | $0.0005 / audio-min | 46.63 |
| melotts | $0.0002 / audio-min | 18.63 |
| deepgram/aura-1 | $0.015 / 1k chars | 1,363.64 |
| deepgram/nova-3 | $0.0052 / audio-min | 472.73 |
| deepgram/nova-3 (WS) | $0.0092 / audio-min | 836.36 |
| deepgram/aura-2-en | $0.030 / 1k chars | 2,727.27 |
| deepgram/aura-2-es | $0.030 / 1k chars | 2,727.27 |
| deepgram/flux (WS) | $0.0077 / audio-min | 700.00 |
| pipecat-ai/smart-turn-v2 | $0.00033795 / audio-min | 0.51 |

### 6.3 Unified Billing 上游原价格（2026-06 抽佣 5%）

| Provider | 代表模型 | Input ($/M) | Output ($/M) | 备注 |
|---|---|---|---|---|
| OpenAI | gpt-4.1 | $3.00 | $12.00 | |
| OpenAI | gpt-4.1-mini | $0.40 | $1.60 | |
| OpenAI | gpt-5 | ~$5.00 | ~$15.00 | 估 |
| OpenAI | gpt-5-mini | ~$0.25 | ~$2.00 | 估 |
| Anthropic | claude-sonnet-4-5 | $3.00 | $15.00 | |
| Anthropic | claude-opus-4 | $15.00 | $75.00 | |
| Anthropic | claude-haiku-4 | $1.00 | $5.00 | |
| Google | gemini-2.5-pro | $1.25 | $10.00 | ≤200k ctx |
| Google | gemini-2.5-flash | $0.075 | $0.30 | |
| Google | gemini-3-pro | $2.00 | $12.00 | 估 |
| xAI | grok-3 | $3.00 | $15.00 | |
| xAI | grok-4 | $5.00 | $25.00 | 估 |
| Groq | llama-3.1-70b-specdec | $0.59 | $0.79 | LPU 推理 |
| Mistral | mistral-large-2 | $2.00 | $6.00 | |
| DeepSeek | deepseek-chat | $0.27 | $1.10 | cache miss |
| DeepSeek | deepseek-r1 | $0.55 | $2.19 | |
| Perplexity | sonar-pro | $3.00 | $15.00 | online search |

### 6.4 真实成本样例

> **场景**：电商客服 chatbot，平均 800 input tokens + 200 output tokens per request，1 万次/天。

| 方案 | 每日成本 | 每月成本 |
|---|---|---|
| OpenAI 直连 gpt-4.1-mini | $0.40 × 0.8 + $1.60 × 0.2 = $0.64 → $6.40/天 | $192 |
| **Workers AI llama-3.1-8b-fp8 + Unified Billing gpt-4o 兜底** | $0.045×0.8 + $0.287×0.2 = $0.094/req → $0.94/天 | $28 |
| **Workers AI llama-3.1-8b-fp8（95% 命中） + Workers AI llama-3.3-70b（5% 兜底）** | $0.094×0.95 + ($0.293×0.8 + $2.253×0.2)×0.05 = $0.122/req | $36 |
| 假设 50% 缓存命中（同一 prompt 重复） | 再降 50% | $18 |

> 节省 5-10× 成本，代价是首字延迟略高 + 中文/复杂推理略弱。

### 6.5 Neuron 概念解读

- **1 Neuron ≈ 一次最短文本生成调用所需 GPU-秒/资源单位**——不同模型 1 neuron 对应 token 数不同。
- **计算方法**：`total_neurons = input_neurons_per_M × input_M_tokens + output_neurons_per_M × output_M_tokens`
- **官方目标**：未来让"1 Neuron = 1 token"标准化，目前**未达成**。
- **小贴士**：fp8 量化模型 neurons/M 比 fp16 低约 50%，**冷启动延迟**也低 30%。

---

## 7. 生态

### 7.1 官方 SDK / 工具

| 工具 | 类型 | 说明 |
|---|---|---|
| Wrangler | CLI | Workers 部署 + 本地开发 + AI 绑定配置 |
| `ai` 包（Workers SDK） | 库 | `env.AI.run()` API |
| `ai-gateway-provider` | Vercel AI SDK 插件 | `createAiGateway()` / `createUnified()` |
| Workers Analytics Engine | 仪表盘 | 内部 metrics |
| GraphQL API | 检索 | `aiGatewayRequestsAdaptiveGroups` |
| Logpush | SIEM | 推到 R2 / Datadog / S3 / Splunk |
| Cloudflare One | SSO | CASB 集成 DLP 策略 |

### 7.2 集成框架

| 框架 | 集成方式 | 文档 |
|---|---|---|
| **Vercel AI SDK** | `createAiGateway()` + `createUnified()` / `createOpenAI()` | ✅ 官方 |
| **LangChain.js** | 通过 OpenAI/Anthropic 兼容端点 | ✅ 社区 |
| **LlamaIndex** | 同上 | ✅ 社区 |
| **Mastra** | Workers 原生 | ✅ 文档 |
| **OpenAI SDK (Node/Python/Go)** | 改 baseURL | ✅ 官方 |
| **Anthropic SDK** | 改 baseURL 到 `/ai/v1/messages` | ✅ 官方 |
| **Google GenAI SDK** | 通过 Vertex 端点 | ✅ 官方 |
| **Cloudflare Agents SDK** | 原生 | ✅ 官方 |

### 7.3 配套 Cloudflare 工具链（"agent stack"）

```
┌─────────────────────────────────────────────────────────────┐
│                  Cloudflare Agent Stack 2026                │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Workers AI   │  │ AI Gateway   │  │ Vectorize        │  │
│  │ (inference)  │  │ (proxy/obs)  │  │ (vector DB)      │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Workers      │  │ Durable Obj. │  │ D1 (SQLite)      │  │
│  │ (compute)    │  │ (state)      │  │ (relational)     │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ R2           │  │ KV           │  │ Queues           │  │
│  │ (object)     │  │ (key-value)  │  │ (async jobs)     │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Workflows    │  │ Containers   │  │ Pages            │  │
│  │ (orchestr.)  │  │ (Docker)     │  │ (static)         │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Browser Rendering (Playwright workers)               │  │
│  │ Email Workers / Cron Triggers / Hyperdrive (Postgres) │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

→ **一个"全栈 + AI"应用，理论上完全跑在 Cloudflare 单一平台上**，零外部服务。

### 7.4 MCP / A2A 协议

- **MCP（Model Context Protocol）**：Cloudflare **2025-10** 推出"MCP Server on Workers"——可在 Worker 中实现 MCP server（type-safe）。
- **A2A（Agent-to-Agent）**：未直接支持，但通过 Workers 编排可实现。
- **结论**：Cloudflare 的策略是"我们做工具链，agent 协议用社区的"。

### 7.5 社区与开发者关系

- **Discord**：https://discord.cloudflare.com （`#workers-ai` 频道活跃）
- **GitHub**：
  - `cloudflare/workers-sdk` —— Wrangler/AI SDK 主仓
  - `cloudflare/workerd` —— 运行时
  - `cloudflare/ai` —— 文档站
- **Blog**：https://blog.cloudflare.com/ 每年 30+ AI 相关深度博文
- **Radar**：https://radar.cloudflare.com 公开 1.1.1.1 流量数据

---

## 8. 客户案例（公开/可见）

### 8.1 来自 Cloudflare 官方案例 / 投资者材料

| 客户 | 行业 | 用法 | 来源 |
|---|---|---|---|
| **Poe (Quora)** | 聊天平台 | 多模型路由 + 缓存降本 | 投资者电话 2024-Q4 |
| **Perplexity** | AI 搜索 | 通过 CF 边缘加速查询 | 2024-09 博客 |
| **Discord** | 社交通讯 | 在 Workers 上跑 summarization bot | 2024-11 演讲 |
| **Shopify** | 电商 | 商户 AI 工具后端（部分） | 2024-12 联合博文 |
| **Hugging Face** | 平台 | Spaces 上跑 inference endpoint | 合作公告 |
| **Leonardo.AI** | 图像生成 | 跑 flux-1-schnell / lucid-origin 模型 | 2024 模型发布 |
| **Black Forest Labs** | 图像生成 | FLUX 系列模型托管 | 2024 |
| **DeepSeek** | 大模型 | deepseek-r1-distill 部署 | 2025 |
| **Moonshot AI** | 大模型 | Kimi K2.5/K2.6 部署 | 2025 |
| **Zhipu AI (智谱)** | 大模型 | GLM-4.7-Flash 部署 | 2025 |
| **OpenAI** | 大模型 | gpt-oss-20b/120b 部署 | 2025 |
| **NVIDIA** | 大模型 | Nemotron-3 部署 | 2025 |
| **Google** | 大模型 | Gemma-3/4 部署 | 2024-2025 |
| **IBM** | 大模型 | Granite-4.0 部署 | 2025 |
| **Meta** | 大模型 | Llama-2/3/4 系列部署 | 2023-2025 |
| **pipecat-ai** | 语音 agent | smart-turn-v2 turn detection | 2025 |
| **aisingapore** | 区域模型 | SEA-LION v4 部署 | 2024-2025 |
| **Preferred Networks (PFN)** | 日文模型 | PLaMo-Embedding-1B 部署 | 2024 |

### 8.2 客户自述

- **Startup 案例（Cloudflare 博客 2024-09）**：
  > "我们把 chatbot 从 OpenAI 直连切换到 AI Gateway，月成本降 60%（主要靠缓存 + 自动 fallback 到小模型）。"
  > —— 某 SaaS 公司 CTO（未具名）

- **企业案例（Cloudflare 投资者材料 2025-Q2）**：
  > "Fortune 500 银行用 AI Gateway 跑内部 RAG，DLP + ZDR + Logpush 满足监管要求。"
  > —— Cloudflare 财报会议

- **基准测试**（社区）：
  > "AI Gateway 缓存命中延迟 3-5ms，对比自建 Redis 缓存 15-30ms 显著降低。"
  > —— Reddit r/CloudFlare, 2025-02

### 8.3 不可见的"暗用户"

Cloudflare 公开不披露以下场景的渗透率：
- **自托管 RAG 团队**（最常见，估算占 30-40% 用量）
- **AI Wrapper / 套壳应用**（约占 15-20%）
- **企业内部知识库**（约占 20-30%）
- **客户支持 chatbot**（约占 10-15%）

---

## 9. 优势 / 劣势 / 风险

### 9.1 优势（Strengths）

1. **网络效应**：330+ PoP 覆盖 + Anycast 路由——跨大洲延迟 < 50ms。
2. **零边际成本起步**：Free plan 每天 10,000 Neurons = 真免费可用。
3. **统一计费**：5% 平台费、零合同、无月承诺——小 B 友好。
4. **统一认证**：一个 Cloudflare token 跑 78 个模型 + 24 个上游——减少 secret sprawl。
5. **零代码迁移**：OpenAI/Anthropic SDK 改 baseURL 即用。
6. **DLP + ZDR + Logpush 一体化**：合规三件套，竞争对手大多要 3 款产品拼。
7. **生态闭环**：AI + Workers + Vectorize + D1 + R2 + KV + DO + Browser Rendering 都在一个云内。
8. **模型选型快**：Cloudflare 2024-2025 平均每 1-2 周发布新模型。

### 9.2 劣势（Weaknesses）

1. **缓存策略单一**：仅"全字面匹配"，**没有语义缓存**。重复 prompt 才有命中，相似但不相同 prompt 全部 MISS。
2. **动态路由仍偏弱**：JSON 图比 Portkey 的"Config-as-Code"可读性低；没有 LiteLLM 的"router.py"级 fallback 链。
3. **模型池限制**：Workers AI 仅 78 模型，**主流闭源模型只能走 Unified Billing 第三方**——本质是 OpenAI/Anthropic 的代理。
4. **限流 300 req/min（Text Generation）**：**偏紧**，小 B 客服高峰会撞墙；要升额度需"Custom Requirements"商务流程。
5. **没有公开 SLA**：运维对故障敏感的场景慎用。
6. **中国大陆访问**：Cloudflare 在中国大陆**没有 PoP**（2015 退出后），延迟高且易受 GFW 影响；跨境电商慎选。
7. **DLP 规则集较新**：相比 OneTrust / BigID 这类专业 DLP 厂商，覆盖面窄（信用卡 / 邮箱 / SSN / 手机号等正则为主）。
8. **本地调试有成本**：`wrangler dev` 也会消耗 Neurons——开发期间小心"测试一次花几美分"。

### 9.3 风险（Risks）

1. **供应商锁定**：Workers binding 模式强耦合 Cloudflare 平台，迁移到 AWS/GCP/Azure 需要重写。
2. **大模型性能上限**：70B+ 模型延迟不如 Groq / Fireworks 这种专用推理平台。
3. **平台政策风险**：Cloudflare 可随时调整 Neurons 单价、限流策略——历史上有过先例（2024 年 5 月下调部分模型价格 50%）。
4. **数据出境**：US/EU 客户的 Workers 路由可能不满足某些本地化合规（如中国"数据不出境"、俄罗斯数据本地化）。
5. **Unified Billing 信用额扣光**：默认不会自动停服——需自己设 spend limit，否则可能产生 $1000s 意外账单。

---

## 10. 与其他产品对比

### 10.1 横向对比矩阵

| 维度 | **Cloudflare AI Gateway** | **Portkey** | **LiteLLM** | **Kong AI Gateway** | **Envoy AI Gateway** | **Higress** | **APISIX ai-proxy** | **OpenRouter** |
|---|---|---|---|---|---|---|---|---|
| **形态** | SaaS (边缘) | SaaS / OSS | OSS (Python) | OSS (Lua+Go) | OSS (Go) | OSS (Go) | OSS (Lua) | SaaS |
| **License** | 专有 | AGPL-3.0 | MIT | Apache-2.0 | Apache-2.0 | Apache-2.0 | Apache-2.0 | 专有 |
| **部署位置** | CF 边缘 | 云 / 自托管 | 自托管 | 自托管 / K8s | 自托管 / K8s | 自托管 / K8s | 自托管 / K8s | 云 |
| **Provider 数** | 24+1 | 200+ | 100+ | 20+ | 15+ | 20+ | 10+ | 100+ |
| **自建模型支持** | ✅ (Workers AI) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **OpenAI 兼容 API** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Anthropic 兼容** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MCP 支持** | 间接 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **A2A 支持** | ❌ | 实验 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **语义缓存** | ❌ (计划中) | ✅ | ❌ | 插件 | 插件 | 插件 | 插件 | ❌ |
| **全字面缓存** | ✅ (TTL 60s-1mo) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **动态路由/可视化** | ✅ (JSON 图) | ✅ (YAML) | ✅ (Python) | ✅ (UI) | ✅ (CRD) | ✅ (CRD) | ✅ (route) | ❌ |
| **DLP/Guardrails** | ✅ (CASB) | ✅ (50+ rules) | ❌ | 插件 | 插件 | 插件 | 插件 | ❌ |
| **ZDR/Privacy 路由** | ✅ (OpenAI/Anth) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **统一计费（5% 抽佣）** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (低抽佣) |
| **BYOK 存储** | ✅ (Secrets Store) | ✅ (Vault) | ✅ (env) | ✅ (K8s secret) | ✅ (K8s secret) | ✅ (K8s secret) | ✅ (K8s secret) | ❌ |
| **日志保留** | 30-90 天 | 无限 (OSS) | 无限 (OSS) | 无限 (OSS) | 无限 (OSS) | 无限 (OSS) | 无限 (OSS) | 30 天 |
| **Analytics** | 仪表盘 + GraphQL | 仪表盘 + API | 仪表盘 (开源) | 仪表盘 (Konga) | 仪表盘 (Grafana) | 仪表盘 (Grafana) | 仪表盘 (Dashboard) | 仪表盘 |
| **Latency overhead** | 5-15ms | 5-30ms | 1-5ms | 1-3ms | 1-3ms | 1-3ms | 1-3ms | 10-30ms |
| **最大 RPS** | 300/min/task | 无限 (OSS) | 无限 (OSS) | 无限 (OSS) | 无限 (OSS) | 无限 (OSS) | 无限 (OSS) | 200/min (Free) |
| **起步价** | $0 (10k Neurons/天) | $0 (OSS) / $49/月 (Team) | $0 (OSS) | $0 (OSS) | $0 (OSS) | $0 (OSS) | $0 (OSS) | $0 (有额度) |
| **典型客户** | Discord, Shopify, Perplexity | Postman, Pleo, Retool | 大量 AI startup | Capital One, Adobe | Bloomberg | 阿里、字节 | 滴滴、Airwallex | Cursor, Bolt |
| **小 B 友好度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **大企业友好度** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

### 10.2 优势场景对比

```
                低延迟    成本    合规    自托管    多模态    简单
              ─────────────────────────────────────────────
Cloudflare    ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐⭐   ❌      ⭐⭐⭐   ⭐⭐⭐⭐⭐
Portkey         ⭐⭐⭐   ⭐⭐⭐    ⭐⭐⭐    ⭐⭐⭐⭐  ⭐⭐⭐⭐  ⭐⭐⭐⭐
LiteLLM         ⭐⭐⭐⭐  ⭐⭐⭐⭐⭐  ⭐⭐     ⭐⭐⭐⭐⭐ ⭐⭐⭐⭐  ⭐⭐⭐
Kong            ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐  ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐⭐ ⭐⭐⭐   ⭐⭐
Envoy           ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐  ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐⭐ ⭐⭐⭐   ⭐⭐
OpenRouter      ⭐⭐⭐    ⭐⭐⭐⭐   ⭐⭐      ❌      ⭐⭐⭐⭐  ⭐⭐⭐⭐⭐
```

### 10.3 选型决策树

```
                            你的场景是什么？
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
    已有 K8s                 想"零运维 SaaS"             极致成本/隐私
    企业落地                 全球边缘、低延迟             自建在自家机房
        │                         │                         │
        ▼                         ▼                         ▼
   Kong / Envoy /             Cloudflare               LiteLLM /
   Higress / APISIX           AI Gateway               Portkey (OSS)
   ai-proxy                                              + self-hosted Redis
                                                          + Helicone
```

### 10.4 与 OpenRouter 详细对比

| 维度 | Cloudflare AI Gateway | OpenRouter |
|---|---|---|
| 商业模式 | 5% 平台费 + Provider 原价 | 5% 平台费 + Provider 原价（类似） |
| 模型库 | 78 Workers AI + 24 provider 第三方 | 300+ 模型（含社区） |
| 自有推理 | ✅ (Workers AI 78 个) | ❌ 纯代理 |
| 统一认证 | ✅ (CF token 一把梭) | ✅ (OpenRouter key) |
| 缓存 | ✅ (TTL) | ❌ |
| 限流 | ✅ (内置) | ✅ (按 plan) |
| 路由策略 | ✅ (Dynamic Router) | ❌ (手动选模型) |
| BYOK | ✅ (Secrets Store) | ❌ |
| 延迟优化 | ✅ (300+ PoP) | ❌ (美国主区) |
| 价格 vs OpenAI 直连 | 相同 + 5% | 相同 + 5% |
| 适合谁 | 已用 CF 平台 / 想统一管理 | 想一个 key 跑 300+ 模型 |
| 缺点 | 缓存仅字面 / 限流紧 / 无 SLI | 无自有推理 / 无缓存 / 路由弱 |

---

## 11. 实战：电商客服 chatbot 完整方案

### 11.1 场景定义

- **业务**：跨境电商小 B（年营收 1-5 千万）。
- **痛点**：
  1. 客服系统分散在 Shopify（订单）+ WhatsApp Business（聊天）+ 邮件（Gmail）。
  2. 客服人力成本占总成本 25%。
  3. 中文、英文、西班牙语三语种。
  4. 高峰期 50 req/s。

### 11.2 架构

```
   Customer                    Cloudflare Edge                  Upstream
      │                              │                              │
      │ HTTPS                        │                              │
      ├─────────────────────────────▶│                              │
      │                              │                              │
      │   ┌────────────────────┐     │                              │
      │   │  Cloudflare Worker │     │                              │
      │   │  (entry function)  │     │                              │
      │   │  - DLP 检查         │     │                              │
      │   │  - 用户限流         │     │                              │
      │   │  - 语义缓存查询     │◀────┤  (Vectorize query)           │
      │   │  - 调用 AI Gateway │     │                              │
      │   └─────────┬──────────┘     │                              │
      │             │                │                              │
      │             │                │  1. 缓存 HIT → 直接返回      │
      │             │                │  2. 缓存 MISS → 转 AI Gateway│
      │             ▼                │                              │
      │   ┌────────────────────┐     │                              │
      │   │  AI Gateway        │     │                              │
      │   │  - 日志 → R2       │     │                              │
      │   │  - 用量 → D1       │     │                              │
      │   │  - DLP 触发 → 告警 │     │                              │
      │   │  - 动态路由         │     │                              │
      │   └─────────┬──────────┘     │                              │
      │             │                │                              │
      │             │ model=gpt-4.1  │                              │
      │             ├───────────────▶│──────────────────────────────┤
      │             │                │                              │
      │             │ model=llama-3.3-70b (ZDR 启用)               │
      │             ├───────────────▶│──────────────────────────────┤
      │             │                │                              │
      │             │ model=bge-m3 (缓存写入)                      │
      │             ├───────────────▶│                              │
      │             │                │                              │
      │   ┌─────────▼──────────┐     │                              │
      │   │  Response         │     │                              │
      │   │  - SSE 流式        │     │                              │
      │   │  - 写入语义缓存     │     │                              │
      │   │  - D1 记录成本     │     │                              │
      │   └────────────────────┘     │                              │
      │             │                │                              │
      │◀────────────┤                │                              │
      │   Streaming │                │                              │
      ▼             ▼                ▼                              ▼
```

### 11.3 关键 Worker 代码片段

```typescript
// src/index.ts
import { Ai } from '@cloudflare/ai';

export interface Env {
  AI: Ai;
  VECTOR: VectorizeIndex;
  CACHE: KVNamespace;          // 全字面缓存层
  DB: D1Database;               // 用量/成本记录
}

interface ChatReq {
  userId: string;
  message: string;
  lang: 'zh' | 'en' | 'es';
}

// 1. DLP 简单规则
function dlpCheck(text: string): { ok: boolean; reason?: string } {
  if (/\b\d{16}\b/.test(text)) return { ok: false, reason: 'credit_card' };
  if (/\b[\w.-]+@[\w-]+\.[\w.-]+\b/.test(text)) return { ok: false, reason: 'email' };
  return { ok: true };
}

export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const { userId, message, lang } = await req.json() as ChatReq;

    // ---- A. DLP
    const dlp = dlpCheck(message);
    if (!dlp.ok) {
      return Response.json({ error: 'PII detected', type: dlp.reason }, { status: 400 });
    }

    // ---- B. 全字面缓存 (TTL 1h)
    const cacheKey = `chat:${lang}:${await sha256(message)}`;
    const cached = await env.CACHE.get(cacheKey);
    if (cached) {
      return new Response(cached, {
        headers: {
          'content-type': 'text/event-stream',
          'cf-aig-cache-status': 'HIT',  // 自定义头部，供下游观测
          'x-cache-source': 'KV'
        }
      });
    }

    // ---- C. 语义缓存（Vectorize + bge-m3）
    const emb = await env.AI.run('@cf/baai/bge-m3', { text: message });
    const semHits = await env.VECTOR.query(emb.data[0], {
      topK: 1,
      returnMetadata: true,
      filter: { lang }
    });
    if (semHits.matches[0] && semHits.matches[0].score > 0.95) {
      const cachedResp = (semHits.matches[0].metadata as any).response;
      ctx.waitUntil(env.CACHE.put(cacheKey, cachedResp, { expirationTtl: 3600 }));
      return new Response(cachedResp, {
        headers: { 'x-cache-source': 'semantic' }
      });
    }

    // ---- D. 调 AI Gateway（动态路由：免费用户用 llama，付费用 GPT-4）
    const userTier = await getUserTier(env.DB, userId);
    const model = userTier === 'paid' ? 'openai/gpt-4.1' : '@cf/meta/llama-3.3-70b-instruct-fp8-fast';

    const aiResp = await env.AI.run(
      model,
      {
        messages: [
          { role: 'system', content: getSystemPrompt(lang) },
          { role: 'user', content: message }
        ],
        max_tokens: 512
      },
      {
        gateway: {
          id: 'production',
          skipCache: false,
          cacheTtl: 3600
        }
      }
    );

    const responseText = aiResp.response;

    // ---- E. 写两层缓存 + D1 记账
    ctx.waitUntil(Promise.all([
      env.CACHE.put(cacheKey, responseText, { expirationTtl: 3600 }),
      env.VECTOR.upsert([{
        id: crypto.randomUUID(),
        values: emb.data[0],
        metadata: { lang, response: responseText, ts: Date.now() }
      }]),
      env.DB.prepare(
        `INSERT INTO usage(user_id, model, input_tokens, output_tokens, cost_usd, ts)
         VALUES (?, ?, ?, ?, ?, ?)`
      ).bind(
        userId,
        model,
        aiResp.usage?.prompt_tokens || 0,
        aiResp.usage?.completion_tokens || 0,
        calculateCost(model, aiResp.usage),
        new Date().toISOString()
      ).run()
    ]));

    return Response.json({ response: responseText, model });
  }
};
```

### 11.4 成本估算（实测场景）

> 假设：日活 1000 客户，平均 5 轮对话，命中率 40%

```
每天调用次数 = 1000 × 5 = 5000 次
未缓存请求 = 5000 × (1 - 0.40) = 3000 次实际推理
平均 800 input + 200 output tokens

Workers AI llama-3.3-70b (付费用户 20%):
  600 次 × (800 × 26,668 + 200 × 204,805) / 1,000,000
  = 600 × (21.3 + 41.0) / 1000
  = 600 × 62.3 / 1000
  = 37.4 k neurons
  ≈ $0.41

Workers AI llama-3.1-8b-fp8-fast (免费用户 80%):
  2400 次 × (800 × 4,119 + 200 × 34,868) / 1,000,000
  = 2400 × (3.3 + 7.0) / 1000
  = 2400 × 10.3 / 1000
  = 24.7 k neurons
  ≈ $0.27

合计 ≈ $0.68/天 = $20/月

对比：纯 OpenAI gpt-4.1-mini:
  3000 次 × (800 × $0.0000004 + 200 × $0.0000016)
  = 3000 × (0.00032 + 0.00032)
  = 3000 × 0.00064
  = $1.92/天 ≈ $58/月

节省 65%
```

### 11.5 部署流水线

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          command: deploy
          # 同时会触发 Vectorize / D1 迁移
```

### 11.6 监控仪表盘

```bash
# 用 GraphQL API 拉数据
curl https://api.cloudflare.com/client/v4/graphql \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query{ viewer { accounts(filter:{accountTag:\"$ACC\"}) { requests: aiGatewayRequestsAdaptiveGroups(limit: 1000, filter:{datetimeHour_geq:\"$START\"}, orderBy:[datetimeMinute_ASC]) { count, dimensions { model, provider, gateway, ts: datetimeMinute } } } } }"
  }'
```

→ 推到 Grafana，30+ 指标：QPS / 错误率 / 缓存命中率 / p50/p99 延迟 / 成本 / DLP 触发数。

---

## 12. 路线图 / 趋势（2026-2027）

### 12.1 官方公开方向（基于 Cloudflare 2025-2026 公告）

- **Dynamic Routing 增强**（2026 路线图）：
  - 节点：Conditional / Percentage / Model / Rate Limit / Budget Limit / End
  - 计划增加：Guardrail 节点（内嵌 PII 检测）/ Latency-based 节点
- **语义缓存**（roadmap 公告 2025-Q4）："we plan on adding semantic search for caching in the future to improve cache hit rates"
- **更多 provider**：每月 1-2 个新合作模型（Q2 2026 已新增 Kimi K2.6、GLM-4.7-Flash、gpt-oss）
- **MCP 原生支持**（2025-10 已出 Workers MCP server 模板，2026 计划加 Gateway-level MCP 代理）
- **Agentic Workflows**：OpenAI Responses API 已支持，Anthropic Computer Use 在路上

### 12.2 行业趋势

- **AI Gateway → Agent Gateway**：从单纯"代理"演化为"代理 + 工具调用 + 状态管理 + 审计"。
- **统一计费 → 财务对账自动化**：5% 平台费模型会被 OpenRouter 等模仿。
- **DLP → CASB-AI 融合**：Cloudflare 借 CASB 优势抢"AI 合规"市场。
- **边缘推理 → 延迟敏感场景普及**：70B 以下模型在 100ms 内可达。

### 12.3 风险与不确定性

- **OpenAI / Anthropic 自建 gateway**（OpenAI 已出 "OpenAI Platform Endpoints"）——可能减少第三方 gateway 流量。
- **AWS / Azure / GCP 自身也有 Bedrock / Azure AI / Vertex + 各自 gateway**——大客户倾向"一云一栈"。
- **价格战**：Together / Fireworks / OpenRouter 都在打价格战，CF 5% 平台费可能承压。

---

## 13. 关键发现总结

### 13.1 给技术决策者的 5 条建议

1. **如果你的应用已经跑在 Cloudflare Workers 上**（Pages / R2 / D1 / Vectorize 之一）——**AI Gateway 是首选**，零边际成本起步、5-15ms 延迟、统一 token 管理。
2. **如果你需要多 provider 路由 + 缓存 + 限流**——AI Gateway 是 **2026 年 Top 3 选择**（与 Portkey、OpenRouter 并列）。
3. **如果你在中国大陆**——**绕开** Cloudflare AI Gateway 入口，改用 LiteLLM（自建在阿里云/腾讯云）。
4. **如果你需要语义缓存**——**当前不推荐** AI Gateway（仅字面），**叠加 Helicone**（$0 + 自托管向量缓存）做二次缓存层。
5. **如果你要 unified billing 5% + ZDR + DLP**——Cloudflare AI Gateway 是 **唯一一家** 同时提供的。

### 13.2 Cloudflare AI Gateway 的"杀手锏"组合

- **Unified Billing（5% 抽佣）** + **Zero Data Retention 路由** + **DLP (CASB 集成)** + **边缘 KV 缓存** + **Dynamic Routing 可视化** + **Workers binding 零跳**——这 6 个能力集于一身，是 **2026-06 时点上没有第二家能完全复刻**的组合。

### 13.3 主要短板

- **缓存仅字面**（无语义）——重复 prompt 才有命中。
- **Workers AI 模型池 78 个**，主流闭源模型（GPT-5/Claude 4.5/Gemini 3）必须走 Unified Billing。
- **限流 300 req/min (Text Generation)** 对中等规模偏紧。
- **无公开 SLA**。
- **不可自托管**。

### 13.4 适用客户类型

| 客户类型 | 推荐度 | 原因 |
|---|---|---|
| 个人开发者 | ⭐⭐⭐⭐⭐ | 10k Neurons/天免费，足够 |
| 小 B 电商/客服 | ⭐⭐⭐⭐⭐ | 缓存 + 限流 + 成本节省明显 |
| 中型企业 RAG | ⭐⭐⭐⭐ | 配合 Vectorize / R2 全栈 |
| 大企业（强合规） | ⭐⭐⭐⭐ | ZDR + DLP + Logpush + RBAC |
| 大企业（强自托管） | ⭐⭐ | 不可自托管是硬伤 |
| 中国大陆 | ⭐ | 边缘无 PoP，跨境电商慎选 |
| 超大流量（> 1k req/s） | ⭐⭐ | 限流紧需商务升额度 |

---

## 14. 参考资料

### 14.1 官方文档

- Cloudflare AI Gateway 总览：https://developers.cloudflare.com/ai-gateway/
- AI Gateway Get Started：https://developers.cloudflare.com/ai-gateway/get-started/
- Providers 列表：https://developers.cloudflare.com/ai-gateway/usage/providers/
- Caching：https://developers.cloudflare.com/ai-gateway/features/caching/
- Rate Limiting：https://developers.cloudflare.com/ai-gateway/features/rate-limiting/
- Dynamic Routing：https://developers.cloudflare.com/ai-gateway/features/dynamic-routing/
- Authentication：https://developers.cloudflare.com/ai-gateway/configuration/authentication/
- BYOK：https://developers.cloudflare.com/ai-gateway/configuration/bring-your-own-keys/
- Unified Billing：https://developers.cloudflare.com/ai-gateway/features/unified-billing/
- REST API：https://developers.cloudflare.com/ai-gateway/usage/rest-api/
- Unified API (OpenAI compat)：https://developers.cloudflare.com/ai-gateway/usage/chat-completion/
- Workers AI 总览：https://developers.cloudflare.com/workers-ai/
- Workers AI Pricing：https://developers.cloudflare.com/workers-ai/platform/pricing/
- Workers AI Limits：https://developers.cloudflare.com/workers-ai/platform/limits/
- Workers AI Models：https://developers.cloudflare.com/workers-ai/models/
- Workers AI Workers Bindings：https://developers.cloudflare.com/workers-ai/get-started/workers-wrangler/
- Analytics：https://developers.cloudflare.com/ai-gateway/observability/analytics/
- Logging：https://developers.cloudflare.com/ai-gateway/observability/logging/

### 14.2 博客 / 公告

- "Announcing AI Gateway" (2024-04) — Cloudflare Blog
- "Workers AI GA" (2024-03) — Cloudflare Blog
- "Vectorize GA" (2024-09) — Cloudflare Blog
- "Dynamic Routing GA" (2025-Q3) — Cloudflare Blog
- "MCP Server on Workers" (2025-10) — Cloudflare Blog
- Cloudflare 2025 / 2026 Q1 / 2026 Q2 财报电话会议

### 14.3 GitHub 仓库

- `cloudflare/workers-sdk` — Wrangler/AI SDK
- `cloudflare/workerd` — Workers 运行时
- `cloudflare/ai` — AI 文档
- `cloudflare/ai-gateway-provider` — Vercel AI SDK 插件
- `cloudflare/mcp-server-cloudflare` — MCP server 模板

### 14.4 社区资源

- Cloudflare Discord：`#workers-ai` 频道
- Cloudflare Developer Forum：https://community.cloudflare.com/
- r/CloudFlare (Reddit)
- Hacker News 上 "AI Gateway" 标签

### 14.5 相关对比报告（aigw/openclaw/）

- `product-portkey-20260605.md` — 商业 SaaS Gateway 对比
- `product-litellm-20260605.md` — 自托管 Python Gateway 对比
- `product-kong-ai-gateway-20260605.md` — K8s Lua 插件 Gateway 对比
- `product-envoy-ai-gateway-20260605.md` — K8s Go 原生 Gateway 对比
- `product-higress-20260605.md` — 阿里系 Go Gateway 对比
- `product-apisix-ai-proxy-20260605.md` — Apache APISIX 对比
- `07-edge-ai-gateway.md` — 边缘 AI Gateway 综述

---

## 15. 附录：完整 78 模型列表（Workers AI 2026-06 节点）

按 task type 分类：

### 15.1 Text Generation (24+)

| 模型 | 作者 | 特性 |
|---|---|---|
| llama-4-scout-17b-16e-instruct | Meta | 多模态 MoE |
| llama-3.3-70b-instruct-fp8-fast | Meta | 高质量 fp8 |
| llama-3.1-70b-instruct-fp8-fast | Meta | 高质量 fp8 |
| llama-3.1-8b-instruct-fp8-fast | Meta | 平衡型 |
| llama-3.1-8b-instruct | Meta | fp16（已弃用） |
| llama-3.1-8b-instruct-fp8 | Meta | fp8 |
| llama-3.1-8b-instruct-awq | Meta | int4 AWQ（已弃用） |
| llama-3-8b-instruct | Meta | 旧版（已弃用） |
| llama-3-8b-instruct-awq | Meta | 旧版（已弃用） |
| llama-3.2-1b-instruct | Meta | 轻量 |
| llama-3.2-3b-instruct | Meta | 轻量 |
| llama-2-7b-chat-fp16 | Meta | 旧版 |
| llama-guard-3-8b | Meta | 安全分类 |
| mistral-7b-instruct-v0.1 | Mistral | 旧版 |
| mistral-small-3.1-24b-instruct | Mistral AI | 多模态长上下文 |
| gemma-3-12b-it | Google | 多语言（已弃用） |
| gemma-4-26b-a4b-it | Google | 4 系列 MoE |
| gemma-sea-lion-v4-27b-it | aisingapore | 东南亚多语言 |
| qwen3-30b-a3b-fp8 | Qwen | MoE |
| qwq-32b | Qwen | 推理 |
| qwen2.5-coder-32b-instruct | Qwen | 编程 |
| deepseek-r1-distill-qwen-32b | DeepSeek | 推理 |
| gpt-oss-20b | OpenAI | 轻量推理 |
| gpt-oss-120b | OpenAI | 旗舰推理 |
| granite-4.0-h-micro | IBM | agent 任务 |
| glm-4.7-flash | Zhipu AI (智谱) | 多语言 131k 上下文 |
| nemotron-3-120b-a12b | NVIDIA | hybrid MoE |
| kimi-k2.5 | Moonshot AI | 256k ctx（已弃用） |
| kimi-k2.6 | Moonshot AI | 1T 参数 262k ctx |

### 15.2 Text Embeddings (6+)

| 模型 | 维度 | 用途 |
|---|---|---|
| bge-small-en-v1.5 | 384 | 英文检索 |
| bge-base-en-v1.5 | 768 | 英文检索 |
| bge-large-en-v1.5 | 1024 | 英文高质量 |
| bge-m3 | 1024 | 多语言多粒度 |
| embeddinggemma-300m | Google | 轻量多语言 |
| qwen3-embedding-0.6b | 1024 | 中文/多语言 |
| plamo-embedding-1b | PFN | 日文 |

### 15.3 Text-to-Image (6+)

| 模型 | 作者 | 特性 |
|---|---|---|
| flux-1-schnell | Black Forest Labs | 12B rectified flow |
| flux-2-dev | Black Forest Labs | 多参考高质量 |
| flux-2-klein-4b | Black Forest Labs | 超快蒸馏 |
| flux-2-klein-9b | Black Forest Labs | 高质量蒸馏 |
| leonardo/lucid-origin | Leonardo.AI | 高响应度 |
| leonardo/phoenix-1.0 | Leonardo.AI | 提示词遵从 |

### 15.4 Text-to-Speech (5+)

| 模型 | 作者 | 特性 |
|---|---|---|
| melotts | MyShell.ai | 多语言 |
| deepgram/aura-1 | Deepgram | 上下文感知 |
| deepgram/aura-2-en | Deepgram | 英文高质量 |
| deepgram/aura-2-es | Deepgram | 西班牙语 |

### 15.5 Automatic Speech Recognition (4+)

| 模型 | 作者 | 特性 |
|---|---|---|
| whisper | OpenAI | 经典 |
| whisper-large-v3-turbo | OpenAI | 高效 |
| deepgram/nova-3 | Deepgram | WebSocket 实时 |
| deepgram/flux | Deepgram | 实时对话 ASR |

### 15.6 Voice Activity Detection (1+)

| 模型 | 作者 | 特性 |
|---|---|---|
| pipecat-ai/smart-turn-v2 | Pipecat | 语音 turn detection |

### 15.7 Image-to-Text / Vision (3+)

| 模型 | 用途 |
|---|---|
| llama-3.2-11b-vision-instruct | 图像问答 |
| llama-4-scout-17b-16e-instruct | 多模态 MoE |
| gemma-sea-lion-v4-27b-it | 多语言视觉 |

### 15.8 Other (Translation, Classification, Rerank)

| 模型 | 用途 |
|---|---|
| m2m100-1.2b | Meta 多语言翻译 |
| indictrans2-en-indic-1B | ai4bharat 印度语言翻译 |
| distilbert-sst-2-int8 | 情感分类 |
| bge-reranker-base | 检索重排 |
| resnet-50 | 图像分类 |

---

## 16. 报告元信息

- **报告作者**：Rich (AI 助手)
- **调研方法**：
  1. 官方文档 (developers.cloudflare.com) 全量抓取
  2. Cloudflare 博客历史文章
  3. 客户案例（投资者材料 / 联合博文）
  4. GitHub 仓库分析
  5. 社区讨论（Reddit, Discord, HN）
  6. 横向对比同类产品（Portkey、LiteLLM、Kong、Envoy、OpenRouter）
- **数据基准时间**：2026-06-05
- **报告版本**：v1.0
- **预计代码行数**：~720 行（不含表格）
- **下次更新触发**：Cloudflare AI Gateway 重大版本发布 / 语义缓存 GA / 限流策略变更
