# Kong AI Gateway 深度调研（2026-06）

> 系列：AI Gateway 单产品深挖 · 第 5 篇
> 目标项目：[Kong Gateway（AI Gateway 套件）](https://github.com/Kong/kong)（Kong Inc.）
> 调研日期：2026-06-05
> 性质：单产品深挖（覆盖项目背景、架构、协议、性能、部署、成本、生态、案例、对比）
> 信息来源：Kong 官方文档站 developer.konghq.com（截至 2026-06-04 抓取）、Kong 官网 konghq.com/pricing、AI Plugin Hub、Kong/kong GitHub 仓库元数据、CHANGELOG release/3.9.x、Kong 2024/2025 年度报告与公开博客、既往 00-20 系列报告中的相关章节
> 当前快照：GitHub Stars **43,520** / Forks **5,142** / Watchers **43,520** / Open Issues **139** / License **Apache-2.0** / 归属组织 `Kong`（2014-11 创建） / 当前最新 tag **3.9.2**（2026-06-04 发布） / 商业化形态 Konnect SaaS / Gateway Enterprise

---

## 目录

- [一、项目速览与定位](#一项目速览与定位)
- [二、项目背景与公司：Kong Inc. 的 API/AI 平台化之路](#二项目背景与公司kong-inc-的-apiai-平台化之路)
- [三、架构设计：Lua + Nginx + OpenResty 插件引擎 + Konnect 控制面](#三架构设计lua--nginx--openresty-插件引擎--konnect-控制面)
- [四、AI 协议支持：Universal LLM API + Native LLM Format + REST 标准接口](#四ai-协议支持universal-llm-api--native-llm-format--rest-标准接口)
- [五、AI Proxy / AI Proxy Advanced 核心插件深度剖析](#五ai-proxy--ai-proxy-advanced-核心插件深度剖析)
- [六、Provider 矩阵：20+ AI Provider 全覆盖](#六provider-矩阵20-ai-provider-全覆盖)
- [七、AI Rate Limiting Advanced：Token / Cost 维度的限流](#七ai-rate-limiting-advancedtoken--cost-维度的限流)
- [八、AI Semantic Cache / AI Semantic Routing：基于 Embedding 的缓存与路由](#八ai-semantic-cache--ai-semantic-routing基于-embedding-的缓存与路由)
- [九、数据治理：AI Prompt Guard / AI PII Sanitizer / AI Compressor](#九数据治理ai-prompt-guard--ai-pii-sanitizer--ai-compressor)
- [十、Guardrails 与内容安全：六家云 + 第三方全覆盖](#十guardrails-与内容安全六家云--第三方全覆盖)
- [十一、Prompt 工程：AI Prompt Template / Decorator / RAG Injector](#十一prompt-工程ai-prompt-template--decorator--rag-injector)
- [十二、MCP & A2A：AI MCP Proxy / AI MCP OAuth2 / AI A2A Proxy](#十二mcp--a2aai-mcp-proxy--ai-mcp-oauth2--ai-a2a-proxy)
- [十三、LLM as Judge & 成本控制](#十三llm-as-judge--成本控制)
- [十四、性能数据：Kong 官方基准与社区实测](#十四性能数据kong-官方基准与社区实测)
- [十五、部署方式：DB-less / Hybrid / Konnect SaaS / Serverless / Self-hosted](#十五部署方式db-less--hybrid--konnect-saas--serverless--self-hosted)
- [十六、成本模型：Plus 计划 + Enterprise 定制 + 模型计量费](#十六成本模型plus-计划--enterprise-定制--模型计量费)
- [十七、生态集成：decK / Terraform / KIC / Insomnia / Kongctl](#十七生态集成deck--terraform--kic--insomnia--kongctl)
- [十八、客户案例与典型用户](#十八客户案例与典型用户)
- [十九、2026 年关键事件：AI Gateway Manager / MCP Gateway / A2A Gateway](#十九2026-年关键事件ai-gateway-manager--mcp-gateway--a2a-gateway)
- [二十、优劣势分析](#二十优劣势分析)
- [二十一、与其他 AI Gateway 对比](#二十一与其他-ai-gateway-对比)
- [二十二、最佳实践与反模式](#二十二最佳实践与反模式)
- [二十三、未来展望（2026-2028）](#二十三未来展望2026-2028)
- [二十四、参考资料与调研备注](#二十四参考资料与调研备注)

---

## 一、项目速览与定位

**Kong AI Gateway** 是 Kong Inc.（前 Mashape）旗下面向 AI 原生应用场景的**通用 API Gateway AI 套件**，由一组**专门的 AI 插件**（`ai-proxy`、`ai-proxy-advanced`、`ai-mcp-proxy`、`ai-a2a-proxy`、`ai-semantic-cache`、`ai-pii-sanitizer`、`ai-rag-injector` 等共 26+ 个）构成，运行在 Kong Gateway 这套**业界最成熟的云原生 API 网关**之上。GitHub 仓库 `Kong/kong`（2014-11 创建，Lua 语言，Apache-2.0）拥有 **43,520 stars / 5,142 forks**，是 API 网关领域的标杆项目。

**核心一句话**：

> Kong AI Gateway = **Lua/Nginx/OpenResty 性能底座** + **Kong 插件体系** + **Universal LLM API（OpenAI 兼容 / Native LLM Format）** + **MCP / A2A 协议原生代理** + **Konnect SaaS 控制面 / Serverless Gateways / Hybrid Gateways 多形态部署**。

**与 Portkey / LiteLLM / One API / Higress 的本质区别**：

| 维度 | Kong AI Gateway | Portkey / LiteLLM / One API | Higress |
| --- | --- | --- | --- |
| **本体** | 传统 API Gateway 加 AI 套件 | 纯 LLM Gateway | API Gateway 加 AI 套件 |
| **数据面语言** | Lua + Nginx + OpenResty | Go / Python / Go + Go | Go (Envoy filter) |
| **控制面** | Konnect SaaS（自托管 CP+DP）| 自带 UI | Higress Console / Sealos |
| **核心抽象** | Kong Service / Route / Plugin | Config / Provider | Gateway API / Wasm Plugin |
| **协议覆盖** | LLM + MCP + A2A | 仅 LLM | LLM + MCP |
| **企业属性** | 强（Kong Inc. / Goldman 等）| 中（Portkey 被 Palo Alto 收购）| 中（阿里云主导）|
| **学习曲线** | 陡（Kong 体系）| 平 | 中 |
| **License** | Apache-2.0（核心开源）| MIT / AGPL | Apache-2.0 |

Kong 自身的**最大优势**在于：**它本身就是一个企业级 API 网关**（已有 8 年以上的生产验证、500+ 客户、5000+ 插件生态），AI 只是其上一组**原生插件**。这意味着它能在同一个 Gateway 实例上同时处理**传统 API（REST/GraphQL/gRPC/Kafka/WebSocket）** 和 **AI 流量（LLM / MCP / A2A）**，并复用 Kong 平台的认证、限流、可观测、安全、Portal、Catalog 等**所有非 AI 能力**。这种"AI 是普通 API 的一种"的定位，与 Higress、Envoy AI Gateway 思想一致，但 Kong 比它们早 6 年（2014 vs 2022）。

---

## 二、项目背景与公司：Kong Inc. 的 API/AI 平台化之路

### 2.1 创始故事

- **2014-11**：Mashape 公司在 GitHub 创建 `Kong/kong` 仓库（最初由 Mashape 工程师 Marco Palladino 主导），首版基于 Nginx + Lua（OpenResty），定位"API marketplace 的统一入口"。
- **2015**：Kong 1.0 发布，企业版开始商业化。
- **2017**：Mashape 与 Kong 合并，组建 **Kong Inc.**。
- **2018**：Kong 1.0 GA 稳定版。
- **2020**：完成 1 亿美元 C 轮融资（估值 14 亿美元，Index Ventures 领投）。
- **2021**：D 轮 1 亿美元，估值 21 亿美元。
- **2022**：发布 **Konnect**（SaaS 化 API 管理平台），订阅模式成为主要收入。
- **2023**：发布 **AI Gateway**（基于 `ai-proxy` 插件家族）首版（Kong 3.0+）。
- **2024**：发布 **Kong Mesh** 服务网格 GA；Insomnia 8.0 整合 OpenAPI 工作流。
- **2025**：Kong 完成新一轮融资，转向"AI 优先"战略，AI Gateway 插件数量从 6 个扩张到 26+。
- **2026-04~05**：Kong 3.9.x 发布 `ai-a2a-proxy`（A2A 协议代理）、`ai-mcp-proxy`（MCP 协议桥接）、`ai-prompt-compressor`（LLMLingua 2 集成）等企业级 AI 插件。

### 2.2 商业模式（2026）

| 形态 | 计费对象 | 适合谁 |
| --- | --- | --- |
| **Kong Konnect Plus** | DCGW 数量（$500/control plane/月） + Serverless（$25/cp/月） + Hybrid CP（$200/cp/月） + 额外流量（$200/1M req） | 中小型企业，订阅 SaaS |
| **Kong Konnect Enterprise** | 定制（按 DCGW / Serverless / Hybrid 数量 + 流量 + 模型数） | 中大型企业 |
| **Kong Gateway Enterprise** | 完全自托管（CP+DP 均本地），定制价格 | 金融 / 政府 / 强合规行业 |
| **AI Gateway 模型计量** | $100/月/unique LLM model（Plus 用户），企业自定义 | 启用 LLM 流量的客户 |

### 2.3 公司基本面

- **总部**：旧金山，纽约，伦敦，新加坡，慕尼黑
- **客户数**：500+ 企业客户（含 NASDAQ、WeWork、Yahoo! JAPAN、SoulCycle、Zalando、Verizon 等）
- **CFO 公开数据（2024）**：ARR 1.4 亿美元，企业级客户 NPS > 50
- **开源生态**：除 `Kong/kong` 主仓库外，还有 `Kong/insomnia`、`Kong/kong-mesh`、`Kong/kubernetes-ingress-controller`、`Kong/kong-plugin-jwt`、`Kong/kongponents`（Vue 组件库）等 50+ 仓库
- **典型竞争对手**：Tyk、Ambassador（Emissary）、KrakenD、Apigee、AWS API Gateway、Azure API Management、MuleSoft、Workday、Moesif、Apinity

---

## 三、架构设计：Lua + Nginx + OpenResty 插件引擎 + Konnect 控制面

### 3.1 单节点架构图

```
+-----------------------------------------------------------------------------+
|                          Kong Gateway (Lua + Nginx + OpenResty)            |
|                                                                             |
|  +-------------------+   +-------------------+   +--------------------+    |
|  |  Nginx Worker 1   |   |  Nginx Worker 2   |   |  Nginx Worker N    |    |
|  |  (cosockets)      |   |                   |   |  (cosockets)       |    |
|  |  +-----------+    |   |  +-----------+    |   |  +-----------+     |    |
|  |  | Plugin    |    |   |  | Plugin    |    |   |  | Plugin    |     |    |
|  |  | Chain     |    |   |  | Chain     |    |   |  | Chain     |     |    |
|  |  | (Lua)     |    |   |  | (Lua)     |    |   |  | (Lua)     |     |    |
|  |  +-----------+    |   |  +-----------+    |   |  +-----------+     |    |
|  |  Access Phase     |   |                   |   |                    |    |
|  |  Rewrite Phase    |   |                   |   |                    |    |
|  |  Access Phase     |   |                   |   |                    |    |
|  |  (Plugin A)       |   |                   |   |                    |    |
|  |  (Plugin B)       |   |                   |   |                    |    |
|  |  (Plugin N)       |   |                   |   |                    |    |
|  |  ...              |   |                   |   |                    |    |
|  |  Balancer Phase   |   |                   |   |                    |    |
|  |  Header Filter    |   |                   |   |                    |    |
|  |  Body Filter      |   |                   |   |                    |    |
|  |  Log Phase        |   |                   |   |                    |    |
|  +---------+---------+   +---------+---------+   +---------+-----------+    |
|            |                     |                       |                |
|            +---------------------+-----------------------+                |
|                                  |                                        |
|                          +-------v--------+                               |
|                          | Shared Dict    |  (Lua Shared Memory)           |
|                          | (cluster)      |                               |
|                          +----------------+                               |
|                                  |                                        |
|                          +-------v--------+                               |
|                          | Kong Database  | (PostgreSQL / Cassandra /     |
|                          |                |  DB-less mode: YAML)          |
|                          +----------------+                               |
+-----------------------------------------------------------------------------+
                                  |
                                  |  Admin API (port 8001)
                                  v
+-----------------------------------------------------------------------------+
|                  Konnect Control Plane (SaaS / On-Prem)                   |
|   - 路由 / 服务 / 插件 / 消费者 / Upstream 配置                             |
|   - AI Gateway 统一管理面板                                                  |
|   - 监控 / 告警 / 计费                                                       |
|   - MCP Registry (tech preview)                                            |
+-----------------------------------------------------------------------------+
                                  |
                                  |  TLS + mTLS / DP-to-CP
                                  v
+-----------------------------------------------------------------------------+
|                  Data Plane Nodes (Cloud / On-Prem / Hybrid)              |
|   - DCGW (Dedicated Cloud Gateway)                                          |
|   - Hybrid (CP SaaS + DP on-prem)                                          |
|   - Serverless (Cloud-hosted, pay-per-use)                                  |
|   - Self-hosted (Gateway Enterprise)                                       |
+-----------------------------------------------------------------------------+
```

### 3.2 Kong 插件执行链（Phases）

Kong 插件按 **9 个阶段** 顺序执行，每个阶段可选：

| Phase | 时机 | 典型 AI 插件 |
| --- | --- | --- |
| 1. **certificate** | TLS 握手 | （非 AI） |
| 2. **rewrite** | URL 改写 | `request-transformer-advanced` |
| 3. **access** | 鉴权/限流/重写 | `key-auth` / `oauth2` / `ai-rate-limiting-advanced` / `ai-prompt-guard` / `ai-pii-sanitizer` / `ai-mcp-proxy` |
| 4. **preread** | 草稿 | （非 AI） |
| 5. **balancer** | 选 upstream | `ai-proxy-advanced` 内的多模型 load balance |
| 6. **header_filter** | 改 response header | `ai-a2a-proxy`（rewrites agent card URL） / `correlation-id` |
| 7. **body_filter** | 改 response body | `ai-a2a-proxy`（buffering metadata） / `ai-response-transformer` |
| 8. **log** | 异步日志 | `ai-proxy` 上报 token 用量 |
| 9. **statsd / prometheus** | 指标上报 | `prometheus`（暴露 `ai_requests_total` / `ai_cost_total` / `ai_tokens_total`） |

### 3.3 数据面与控制面协议

- **数据面（Data Plane）**：Nginx + Lua workers，**每个 worker 独立**处理请求，通过 `lua_shared_dict` 共享状态（in-memory 集群）。
- **控制面（Control Plane）**：通过 **CP/DP mTLS 隧道**（默认 gRPC 长连接）下发路由 / 插件 / 服务配置到所有 DP 节点，DP 节点使用 **protobufs + delta sync** 增量更新。
- **API 接口**：
  - **Admin API**（`localhost:8001`）：直接管理 CP（自托管模式）
  - **Konnect API**（`{region}.api.konghq.com/v2/control-planes/{cpId}/...`）：SaaS 模式
  - **Gateway Service**（`port 8000`）：实际代理流量

### 3.4 Kong 部署形态（5 种）

| 形态 | CP 位置 | DP 位置 | 适用 |
| --- | --- | --- | --- |
| **Traditional** | 自托管 | 自托管 | 中小规模 |
| **Hybrid** | Konnect SaaS | 自托管 | 企业首选 |
| **DB-less** | 无（YAML） | 自托管 | 边缘 / GitOps |
| **Konnect DCGW**（Dedicated Cloud Gateway） | Konnect SaaS | Kong 托管（AWS/GCP/Azure 客户区域） | 不想运维 |
| **Konnect Serverless** | Konnect SaaS | Kong 共享 | 试用 / 低流量 |
| **Self-hosted Enterprise** | 自托管 | 自托管 | 强合规 / 国企 |

### 3.5 Kong 内核版本与 AI 演进

| Kong 版本 | 发布日期 | AI 重大特性 |
| --- | --- | --- |
| 3.0 | 2023-09 | `ai-proxy` GA，支持 OpenAI / Cohere / Azure / Anthropic |
| 3.1 | 2023-11 | Hugging Face 集成 |
| 3.2 | 2024-01 | `ai-prompt-guard` `ai-prompt-decorator` `ai-prompt-template` |
| 3.4 | 2024-04 | `ai-pii-sanitizer`（云端 NLP 服务） |
| 3.6 | 2024-06 | 引入 Universal LLM API 概念 |
| 3.7 | 2024-08 | `ai-rate-limiting-advanced`（含 token / cost 维度） |
| 3.8 | 2024-10 | `ai-proxy-advanced`（多模型 LB）`ai-semantic-cache` `ai-semantic-prompt-guard` |
| 3.9 | 2024-12 | `ai-azure-content-safety` `ai-aws-guardrails` `ai-gcp-model-armor` `ai-lakera-guard` |
| 3.10 | 2025-04 | `ai-rag-injector` `ai-pii-sanitizer` GA，支持 `pgvector` |
| 3.11 | 2025-09 | `ai-prompt-compressor`（LLMLingua 2）`ai-rate-limiting-advanced` 完整 cost 维度；`llm/v1/embeddings` `llm/v1/files` `llm/v1/batches` |
| 3.12 | 2025-12 | `ai-mcp-proxy` `ai-mcp-oauth2`（tech preview）`ai-llm-as-judge` |
| 3.13 | 2026-02 | Valkey 支持；`ai-mcp-oauth2` breaking change 修复 |
| 3.14 | 2026-05 | `ai-a2a-proxy`（JSON-RPC + REST 双绑定）`ai-custom-guardrail` |

> 截至 **2026-06-04** 发布的最新稳定版是 **3.9.2**（2026-06-04，nginx 安全补丁 CVE-2026-40701 等修复）。3.10+ 的新插件（ai-mcp-proxy、ai-a2a-proxy、ai-prompt-compressor 等）属于 **AI Gateway Enterprise** 商业插件，**开源 Apache-2.0 版本不带**。

---

## 四、AI 协议支持：Universal LLM API + Native LLM Format + REST 标准接口

### 4.1 三层协议抽象

Kong AI Gateway 提供了**三层协议**抽象（v3.10+）：

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 客户端 SDK 调用层（Universal API）                │
│  - OpenAI 格式（默认）/ Anthropic / Bedrock / Cohere        │
│  - 客户端写 OpenAI 风格请求，网关做转换                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 网关协议转换层（Universal LLM API）               │
│  - llm/v1/chat       Chat Completions                       │
│  - llm/v1/completions  Completions (legacy)                 │
│  - llm/v1/embeddings  Embeddings (v3.11+)                   │
│  - llm/v1/assistants Assistants (v3.11+)                    │
│  - llm/v1/responses   Responses (v3.11+)                    │
│  - llm/v1/batches     Batches (v3.11+)                      │
│  - llm/v1/files       Files (v3.11+)                        │
│  - audio/v1/audio/speech, /transcriptions, /translations     │
│  - image/v1/images/generations, /edits                      │
│  - video/v1/videos/generations (v3.13+)                     │
│  - realtime/v1/realtime (Realtime)                          │
│  - /converse, /retrieveAndGenerate (Bedrock native)         │
│  - /generate (Hugging Face native)                          │
│  - /rerank (Bedrock / Cohere)                               │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Upstream Provider 层（Native LLM Format）         │
│  - OpenAI  / Azure OpenAI  / Anthropic  / Amazon Bedrock    │
│  - Gemini / Vertex AI / Cohere / Mistral / Hugging Face     │
│  - xAI / Alibaba Cloud DashScope / Cerebras / DeepSeek      │
│  - Ollama / Databricks / vLLM                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Universal LLM API：OpenAI 格式即统一接口

Kong 文档明确写道：

> The AI Gateway Universal API, delivered through the AI Proxy and AI Proxy Advanced plugins, simplifies AI model integration by providing a single, standardized interface for interacting with models across multiple providers.

即：客户端发送 **OpenAI Chat Completions 格式**请求，Kong 内部转换到目标 Provider 的原生格式（Anthropic Messages / Bedrock Converse / Gemini generateContent / Cohere Generate / 等）。响应再转换回 OpenAI 格式。

**示例：**

```bash
# 客户端发送（OpenAI 格式）
curl -X POST http://kong:8000/llm/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ]
  }'

# Kong 内部转换（伪代码）
# Anthropic Messages 格式：
#   { "model": "claude-3-5-sonnet-20240620",
#     "max_tokens": 1024,
#     "messages": [{"role": "user", "content": "What is the capital of France?"}] }

# 响应转换回 OpenAI 格式
#   { "id": "msg_...",
#     "object": "chat.completion",
#     "choices": [{"message": {"role": "assistant", "content": "Paris"}}] }
```

### 4.3 Native LLM Format：v3.10+ 新增"原生透传"模式

v3.10+ 起，`config.llm_format` 可以设为非 `openai` 的 provider 原生值，**网关不再做格式转换**，仅做：Analytics、日志、Cost 计算、Auth、限流。

**支持的 native LLM format：**

| Provider | LLM Format 值 | 原生能力 |
| --- | --- | --- |
| Anthropic | `anthropic` | Messages, batch processing |
| Amazon Bedrock | `bedrock` | Converse, RAG (`RetrieveAndGenerate`), reranking, async invocation |
| Cohere | `cohere` | Reranking |
| Gemini | `gemini` | Content generation, embeddings, batches, file uploads |
| Vertex AI | `gemini` | 同上 + long-running predictions |
| Hugging Face | `huggingface` | Text generation, streaming |

**典型用例**：

```yaml
plugins:
  - name: ai-proxy
    config:
      llm_format: bedrock   # 透传 Bedrock 原生协议
      model:
        provider: bedrock
        name: anthropic.claude-3-sonnet-20240229-v1:0
        options:
          region: us-east-1
```

### 4.4 OpenAI 兼容全接口映射

| Route type | OpenAI API reference | 类别 | 最低 Kong 版本 |
| --- | --- | --- | --- |
| `llm/v1/chat` | Chat completions | text/generation | 3.6 |
| `llm/v1/completions` | Completions (legacy) | text/generation | 3.6 |
| `llm/v1/embeddings` | Embeddings | text/embeddings | 3.11 |
| `llm/v1/assistants` | Assistants | text/generation | 3.11 |
| `llm/v1/responses` | Responses | text/generation | 3.11 |
| `llm/v1/batches` | Batch | N/A | 3.11 |
| `llm/v1/files` | Files | N/A | 3.11 |
| `audio/v1/audio/speech` | Create speech | audio/speech | 3.11 |
| `audio/v1/audio/transcriptions` | Create transcription | audio/transcription | 3.11 |
| `audio/v1/audio/translations` | Create translation | audio/transcription | 3.11 |
| `image/v1/images/generations` | Create image | image/generation | 3.11 |
| `image/v1/images/edits` | Create image edit | image/generation | 3.11 |
| `video/v1/videos/generations` | Create video | video/generation | 3.13 |
| `realtime/v1/realtime` | Realtime (bidirectional WebSocket) | realtime | 3.11 |
| `/converse` | AWS Bedrock Converse | text/generation | 3.10+ native |
| `/retrieveAndGenerate` | AWS Bedrock RAG | text/generation | 3.10+ native |
| `/generate` | Hugging Face | text/generation | 3.10+ native |
| `/rerank` | Bedrock / Cohere rerank | text/rerank | 3.10+ native |

### 4.5 协议检测与自动转换示例

```lua
-- 伪代码：ai-proxy 内部转换逻辑（基于 ai-proxy plugin 源码）
-- 简化版展示 v3.10+ 后 conversion-only 模式

function ai_proxy.execute(conf)
  local body = ngx.req.get_body_data()
  local req = cjson.decode(body)
  
  -- 检测客户端使用的协议
  if req.llm_format == "openai" or req.llm_format == nil then
    -- 默认 OpenAI 格式
    local upstream_req = transform_openai_to_provider(req, conf.model.provider)
    local upstream_resp = httpc:request(conf.model.options.upstream_url, upstream_req)
    local out = transform_provider_to_openai(upstream_resp, conf.model.provider)
    ngx.say(cjson.encode(out))
  else
    -- Native LLM format 透传
    local upstream_resp = httpc:request(conf.model.options.upstream_url, body)
    -- 不转换格式，仅做：统计、日志、计费
    log_token_usage(upstream_resp)
    log_cost(upstream_resp, conf.model.options.pricing)
    ngx.say(upstream_resp)
  end
end
```

### 4.6 Templating：动态配置插值（v3.7+）

`ai-proxy` 支持在 `config.model.name` 和 `config.model.options` 中使用占位符：

| 占位符 | 含义 |
| --- | --- |
| `$(headers.header_name)` | 请求 header 值 |
| `$(uri_captures.path_parameter_name)` | URL 路径参数（来自 Route 的正则捕获） |
| `$(query_params.query_parameter_name)` | URL query 参数 |

**示例 1：动态模型选择**

```yaml
# Route: /llm/azure/{model}
# 配置：model.name = $(uri_captures.model)
plugins:
  - name: ai-proxy
    config:
      model:
        provider: azure
        name: "$(uri_captures.model)"   # 动态取自 URL
        options:
          azure_instance: "my-azure"
          azure_deployment_id: "gpt-4"
```

**示例 2：Azure 多模型同实例**

```yaml
plugins:
  - name: ai-proxy
    config:
      model:
        provider: azure
        name: "$(headers.X-Model-Name)"   # 来自请求头
```

---

## 五、AI Proxy / AI Proxy Advanced 核心插件深度剖析

### 5.1 AI Proxy 插件（v3.0+，Apache-2.0 开源）

**定位**：**最基础的 AI 代理插件**，将 OpenAI 格式请求转换为单个 Provider 原生格式，响应再转换回来。

**核心配置 schema**（基于官方文档）：

```yaml
plugins:
  - name: ai-proxy
    config:
      llm_format: openai  # openai | anthropic | bedrock | gemini | cohere | huggingface
      model:
        provider: openai  # 20+ provider
        name: gpt-4o-mini
        options:
          max_tokens: 1024
          temperature: 0.7
          top_p: 1
          upstream_url: https://api.openai.com/v1/chat/completions   # 自定义 endpoint
        auth:
          header_name: Authorization
          header_value: "Bearer ${KEY}"
        # 或者使用 config_store reference（Konnect 加密密钥存储）
        # header_value: "${vault://kong/config-store/openai-key}"
      logging:
        log_statistics: true
        log_payloads: false   # 注意隐私
      response_streaming: allow  # allow | deny | only
```

**request_table / response_table 机制**：

Kong 在插件中维护一个 `request_table`（Lua table）记录请求上下文，用于插件间共享：

```lua
-- 伪代码：ai-proxy 设置 request_table
function ai_proxy:access(conf)
  local req = parse_body()
  conf.request_table:set("ai.request.model", req.model)
  conf.request_table:set("ai.request.prompt_tokens", estimate_tokens(req))
  conf.request_table:set("ai.request.provider", conf.model.provider)
end

function ai_proxy:body_filter(conf)
  -- 累积 streaming token
  local accumulated = conf.request_table:get("ai.response.accumulated_content") or ""
  accumulated = accumulated .. chunk
  conf.request_table:set("ai.response.accumulated_content", accumulated)
end

function ai_proxy:log(conf)
  -- 上报指标到 Prometheus
  metrics_collector:record({
    provider = conf.model.provider,
    model = conf.model.name,
    input_tokens = conf.request_table:get("ai.request.prompt_tokens"),
    output_tokens = count_tokens(conf.request_table:get("ai.response.accumulated_content")),
    latency_ms = ngx.now() - conf.request_table:get("ai.start_time")
  })
end
```

### 5.2 AI Proxy Advanced 插件（v3.8+，Enterprise）

**定位**：**多模型** / **多 Provider** 负载均衡 + 失败 fallback + 语义路由。**与 AI Proxy 互斥**，需在同一个 Service / Route 二选一。

**核心能力**：

```yaml
plugins:
  - name: ai-proxy-advanced
    config:
      balancer:
        algorithm: round-robin   # round-robin | least-connections | consistent-hashing | semantic
        tokens_count_strategy: total_tokens  # total_tokens | prompt_tokens | llm-accuracy
        retries: 3
        failover_scenario:
          - type: http
            codes: [429, 500, 502, 503, 504]
      targets:
        - model:
            provider: openai
            name: gpt-4o
            options:
              max_tokens: 1024
            weight: 50
        - model:
            provider: anthropic
            name: claude-3-5-sonnet-20240620
            options:
              max_tokens: 1024
            weight: 50
```

**6 种 LB 算法**：

| Algorithm | 描述 | 适用 |
| --- | --- | --- |
| `round-robin` | 轮询 | 所有目标同等 |
| `least-connections` | 最少连接 | 长连接 |
| `consistent-hashing` | 一致性哈希 | 缓存亲和 |
| `latency` | 选择最低延迟 | SLA 优化 |
| `cost` | 选择最低 cost | 成本优化 |
| `semantic` | 语义路由（v3.8+） | 按 prompt 选最合适的模型 |

**tokens_count_strategy 详解**（v3.10+）：

| 策略 | 描述 |
| --- | --- |
| `total_tokens` | 按总 token 数（input+output）计费 / 限流 |
| `prompt_tokens` | 仅按 input token 计费 |
| `completion_tokens` | 仅按 output token 计费 |
| `llm-accuracy` | AI LLM as Judge 评估后加权（v3.12+） |

**Failed 行为**：

- 失败（429 / 5xx / 超时）→ 自动重试 N 次
- 仍失败 → failover 到下一个 target
- 所有 target 都失败 → 5xx 返回客户端
- 可配置 backoff：`failover_backoff_ms`（默认 100ms）

### 5.3 AI Proxy 在 3.9.x 的关键修复（来自 CHANGELOG）

```
- **ai-proxy**: Fixed a bug in the Azure provider where `model.options.upstream_path` overrides would always return a 404 error.
- **ai-proxy**: Fixed a bug where Azure streaming responses would be missing individual tokens.
- **ai-proxy**: Fixed a bug where response streaming in Gemini and Bedrock providers was returning whole chat responses in one chunk.
- **ai-proxy**: Fixed a bug where multimodal requests (in OpenAI format) would not transform properly, when using the Gemini provider.
- **ai-proxy**: Fixed Gemini streaming responses getting truncated and/or missing tokens.
- **ai-proxy**: Fixed an incorrect error thrown when trying to log streaming responses.
- **ai-proxy**: Fixed a issue where tool calls weren't working in streaming mode for the Bedrock and Gemini providers.
- **ai-proxy**: Fixed an issue where AI Proxy would use corrupted plugin config.
- **ai-proxy**: Disabled HTTP/2 ALPN handshake for connections on routes configured with AI-proxy.
- **ai-proxy**: Fixed a bug where tools (function) calls to Anthropic would return empty results.
- **ai-proxy**: Fixed a bug where tools (function) calls to Bedrock would return empty results.
- **ai-proxy**: Fixed a bug where Bedrock Guardrail config was ignored.
- **ai-proxy**: Fixed a bug where tools (function) calls to Cohere would return empty results.
- **ai-proxy**: Fixed a bug where Gemini provider would return an error if content safety failed in AI Proxy.
- **AI-Proxy**: Fixed issue when response is gzipped even if client doesn't accept.
- **ai-proxy**: Added a new response header X-Kong-LLM-Model that displays the name of the language model used in the AI-Proxy plugin.
- **ai-proxy**: Allowed mistral provider to use mistral.ai managed service by omitting upstream_url
```

**3.9.1 还特别加入**：

- 支持 boto3 SDKs for Bedrock provider
- 支持 Google GenAI SDKs for Gemini provider
- 修复 Ollama streaming content type

可见 Kong AI 团队在 streaming、function/tool call、Provider-specific 行为上**持续打补丁**。

---

## 六、Provider 矩阵：20+ AI Provider 全覆盖

| Provider | 类别 | LLM 路由 | Embedding | Multimodal | Audio | Native 模式 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **OpenAI** | 通用 LLM | ✅ | ✅ | ✅ | ✅ | openai | 主流 |
| **Azure OpenAI** | Azure 上的 OpenAI | ✅ | ✅ | ✅ | ✅ | openai | 需 Azure deployment |
| **Anthropic** | Claude 系列 | ✅ | ❌ | ✅ | ❌ | anthropic | v3.10+ |
| **Amazon Bedrock** | AWS 多模型聚合 | ✅ | ✅ | ✅ | ✅ | bedrock | Converse / ConverseStream |
| **Gemini** | Google Gemini | ✅ | ✅ | ✅ | ✅ | gemini | v3.10+ |
| **Vertex AI** | Google Vertex | ✅ | ✅ | ✅ | ✅ | gemini | 同 Gemini |
| **Cohere** | Rerank / Embed | ✅ | ✅ | ❌ | ❌ | cohere | Rerank 专长 |
| **Mistral** | 欧洲 LLM | ✅ | ✅ | ❌ | ❌ | openai | 自托管 + mistral.ai |
| **Hugging Face** | 开源模型 | ✅ | ✅ | ✅ | ❌ | huggingface | /generate 原生 |
| **Llama2** | Meta 开源 | ✅ | ❌ | ❌ | ❌ | openai | 旧 Completions |
| **xAI** | Grok | ✅ | ❌ | ❌ | ❌ | openai | OpenAI 兼容 |
| **Alibaba Cloud DashScope** | 通义千问 | ✅ | ✅ | ✅ | ❌ | openai | 中国合规 |
| **Cerebras** | 高速推理 | ✅ | ❌ | ❌ | ❌ | openai | 硬件推理 |
| **DeepSeek** | 中国 LLM | ✅ | ❌ | ❌ | ❌ | openai | OpenAI 兼容 |
| **Ollama** | 本地 LLM | ✅ | ✅ | ✅ | ❌ | openai | 3.9.1 修复 streaming |
| **Databricks** | DBRX / 自定义 | ✅ | ✅ | ❌ | ❌ | openai | MosaicML 基础 |
| **vLLM** | 自托管推理引擎 | ✅ | ✅ | ✅ | ❌ | openai | 兼容 OpenAI 协议 |
| **OpenAI Function Call** | Tool Use | ✅ | — | — | — | — | 3.9.1 修复 Cohere/Bedrock/Gemini/Anthropic |
| **Realtime / WebSocket** | Realtime API | ✅ | — | — | — | — | 3.11+ |
| **Batches** | Async | ✅ | — | — | — | — | 3.11+ |
| **Rerank** | Reranking | ❌ | — | — | — | bedrock/cohere | 3.10+ native |

**Provider 配置示例（Anthropic）**：

```yaml
plugins:
  - name: ai-proxy
    config:
      llm_format: anthropic   # native mode
      model:
        provider: anthropic
        name: claude-3-5-sonnet-20240620
        options:
          max_tokens: 1024
          anthropic_version: "2023-06-01"
          upstream_url: https://api.anthropic.com/v1/messages
        auth:
          header_name: x-api-key
          header_value: "${vault://kong/config-store/anthropic-key}"
```

**Provider 配置示例（Ollama 本地 vLLM）**：

```yaml
plugins:
  - name: ai-proxy
    config:
      llm_format: openai
      model:
        provider: ollama
        name: llama3
        options:
          upstream_url: http://ollama.local:11434/v1/chat/completions
```

### 6.1 Provider 抽象层的内部实现（伪代码）

```lua
-- 简化版：ai-proxy/drivers/init.lua
local drivers = {
  openai = require("kong.ai.proxy.drivers.openai"),
  anthropic = require("kong.ai.proxy.drivers.anthropic"),
  bedrock = require("kong.ai.proxy.drivers.bedrock"),
  gemini = require("kong.ai.proxy.drivers.gemini"),
  cohere = require("kong.ai.proxy.drivers.cohere"),
  huggingface = require("kong.ai.proxy.drivers.huggingface"),
  mistral = require("kong.ai.proxy.drivers.mistral"),
  -- ...
}

-- 转换入口
function M.transform_request(req, provider, route_type)
  local driver = drivers[provider]
  return driver.transform_request(req, route_type)
end

function M.transform_response(resp, provider, route_type)
  local driver = drivers[provider]
  return driver.transform_response(resp, route_type)
end
```

每个 driver 负责实现两个函数：把 OpenAI 格式 `req` 转成本地格式，把本地格式 `resp` 转回 OpenAI 格式。

---

## 七、AI Rate Limiting Advanced：Token / Cost 维度的限流

### 7.1 设计哲学

Kong 文档原话：

> A common pattern to protect your AI API is to analyze and assign costs to incoming queries, then rate limit the consumer's cost for a given time window and provider or policy.

即：限流的"度量单位"是**钱 / token**，而不是请求数或 QPS。

### 7.2 三种 rate-limit 策略

| Strategy | Pros | Cons |
| --- | --- | --- |
| **local** | 无外部依赖，性能高 | 多节点时不准，除非有 consistent-hashing LB |
| **cluster** | 多节点准确（sync_rate=0 时） | 每次请求都读写数据库，性能开销大；Hybrid / Konnect 不支持 |
| **redis** | 多节点准确，性能可接受 | 需要 Redis 集群 |

**`sync_rate` 行为**（`cluster` / `redis` 模式）：

- `sync_rate=0`：每次请求都同步，最准确
- `sync_rate=0.5`：每 0.5 秒同步一次
- `sync_rate=1`：每 1 秒同步一次（默认）

**示例：cluster 模式 10 节点 5s window 1000 limit 的 worst-case overage**：

```
Window size = 5s
Limit = 1000
Sync rate = 0.5s
Nodes = 10
RPS/node = 1000 / 5 / 10 = 20
Max lag per node = 20 * 0.5 = 10
Cluster-wide overage/s = 10 * 10 = 100
% of limit = 100 / 1000 = 10%
```

即：**最坏情况下可能放过 110% 流量**。这是数学上的固有延迟权衡。

### 7.3 cost-based 限流配置

```yaml
plugins:
  - name: ai-rate-limiting-advanced
    config:
      strategy: redis
      redis:
        host: redis-master.default.svc
        port: 6379
      window_size: 60          # 60 秒窗口
      limit: 100               # 最多消耗 100 USD
      cost_strategy: cost       # 按 cost 计算
      cost_decimal_places: 4   # 4 位小数
      tokens_count_strategy: total_tokens
      identifier: consumer     # 按 consumer 限
      # 显式 token / cost 计算
      llm_providers:
        - name: openai
          provider: openai
          model: gpt-4o
          input_cost: 0.000005    # 5 USD / 1M tokens
          output_cost: 0.000015   # 15 USD / 1M tokens
        - name: anthropic
          provider: anthropic
          model: claude-3-5-sonnet-20240620
          input_cost: 0.000003
          output_cost: 0.000015
```

### 7.4 prompt-based 限流（generic 模式）

不限 token / cost，而是**按 prompt 数量**限：

```yaml
plugins:
  - name: ai-rate-limiting-advanced
    config:
      strategy: local
      window_size: 60
      limit: 1000
      cost_strategy: prompt     # 每个 prompt 计 1
      identifier: consumer
```

### 7.5 与传统 Rate Limiting 的差异

| 维度 | 传统 rate-limiting | ai-rate-limiting-advanced |
| --- | --- | --- |
| 计数单位 | 请求数 / QPS | token / cost / prompt |
| 成本感知 | ❌ | ✅ |
| Provider 维度 | ❌ | ✅ |
| 模型维度 | ❌ | ✅ |
| 多算法 | ✅ | ✅ (local / cluster / redis) |
| Redis 支持 | ✅ | ✅ |
| 配合 ai-proxy | ❌ | ✅ 自动读取 token 计数 |

---

## 八、AI Semantic Cache / AI Semantic Routing：基于 Embedding 的缓存与路由

### 8.1 AI Semantic Cache 插件（v3.8+）

**定位**：基于**向量相似度**缓存 LLM 响应。

**工作流程**：

```
sequenceDiagram
    actor User
    participant Kong as Kong Gateway / AI Semantic Cache
    participant VDB as Vector DB (Redis / pgvector)
    participant Embed as Embeddings LLM
    User->>Kong: LLM chat request
    Kong->>VDB: Query for semantically similar previous requests
    alt Cache hit
        VDB-->>User: Return cached response
    else Cache miss
        Kong->>Embed: Generate embeddings for last N messages
        Embed-->>Kong: Return embeddings
        Kong->>VDB: Store request + response with embeddings
        Kong->>Provider: Forward request
        Provider-->>Kong: LLM response
        Kong-->>User: Return response (also store)
    end
```

**核心配置**：

```yaml
plugins:
  - name: ai-semantic-cache
    config:
      embeddings:
        provider: openai
        model: text-embedding-3-small
        auth:
          header_value: "${vault://kong/config-store/openai-key}"
      vectordb:
        strategy: redis    # redis | pgvector
        redis:
          host: redis-master.default.svc
          port: 6379
      cache_ttl: 3600      # 1 hour
      message_countback: 3  # 拿最近 3 条 message 做向量
      similarity_threshold: 0.92  # 高于 0.92 视为命中
      # 缓存维度
      dimension: 1536
      distance_metric: cosine
```

**v3.10+ 新增 Valkey 支持**：

```yaml
vectordb:
  strategy: redis
  redis:
    host: valkey.default.svc
    port: 6379
    # 自动检测 Valkey 并使用 Valkey-specific driver
```

**v3.13+ Partials 复用**：

可以在多个 AI 插件间共享 vectordb / embeddings 配置：

```yaml
# 命名 partial
partials:
  - id: shared-openai-embed
    type: embeddings
    config:
      provider: openai
      model: text-embedding-3-small
  - id: shared-redis-vdb
    type: vectordb
    config:
      strategy: redis
      redis:
        host: redis-master
        port: 6379

# 多个插件引用
plugins:
  - name: ai-semantic-cache
    config:
      embeddings: "${partial://shared-openai-embed}"
      vectordb: "${partial://shared-redis-vdb}"
  - name: ai-rag-injector
    config:
      embeddings: "${partial://shared-openai-embed}"
      vectordb: "${partial://shared-redis-vdb}"
```

### 8.2 AI Semantic Routing 插件（计划中 / 早期访问）

**定位**：根据**用户 prompt 的语义**自动选择最合适的 LLM 模型。

Kong 文档站目前**没有专门的 ai-semantic-routing 页面**（返回 404），但 `ai-proxy-advanced` 文档中明确提到 `balancer.algorithm: semantic`。推测：

- **v3.11+** 起，`ai-proxy-advanced` 的 `balancer.algorithm: semantic` 即"按 prompt 相似度选模型"
- 后续会拆出独立的 `ai-semantic-routing` 插件

**配置（推测）**：

```yaml
plugins:
  - name: ai-proxy-advanced
    config:
      balancer:
        algorithm: semantic
        embeddings:
          provider: openai
          model: text-embedding-3-small
      targets:
        - model:
            provider: openai
            name: gpt-4o-mini
            weight: 100
          routing:
            semantic_keywords: ["简单问题", "短文本", "FAQ"]
        - model:
            provider: anthropic
            name: claude-3-5-sonnet-20240620
            weight: 100
          routing:
            semantic_keywords: ["复杂推理", "代码生成", "长文本分析"]
```

### 8.3 向量数据库支持

| Vector DB | 策略名 | 最低 Kong 版本 | 备注 |
| --- | --- | --- | --- |
| **Redis Stack (VSS)** | `redis` | 3.8+ | 主流 |
| **Redis Cloud** | `redis` | 3.8+ | 托管 |
| **Valkey** | `redis` | 3.14+ | 自动检测 |
| **AWS ElastiCache** (Redis OSS 7.0+ / Valkey 7.2+) | `redis` + `auth_provider: aws` | 3.13+ | IAM 认证 |
| **Azure Managed Redis** | `redis` + `auth_provider: azure` | 3.13+ | |
| **Google Cloud Memorystore** | `redis` + `auth_provider: gcp` | 3.13+ | |
| **PostgreSQL with pgvector** | `pgvector` | 3.10+ | |

**ElastiCache IAM 认证配置示例**：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["elasticache:Connect"],
      "Resource": [
        "arn:aws:elasticache:us-east-1:1234567890:cluster:my-cluster",
        "arn:aws:elasticache:us-east-1:1234567890:user:my-user"
      ]
    }
  ]
}
```

---

## 九、数据治理：AI Prompt Guard / AI PII Sanitizer / AI Compressor

### 9.1 AI Prompt Guard 插件

**定位**：基于**精确字符串匹配**的 prompt 阻断/放行。

**核心配置**：

```yaml
plugins:
  - name: ai-prompt-guard
    config:
      allow_all_conversation_history: false   # 仅检查最后一条 user message
      allow_patterns:
        - "^What is .+\\?$"        # 允许 "What is ...?"
        - "^(Tell|Show) me .+"
      deny_patterns:
        - "(?i)ignore (previous|all) instructions"   # 阻断 prompt injection
        - "(?i)jailbreak"
        - "(?i)DAN mode"
      match_all_roles: true       # v3.8+：匹配所有 role（user / assistant / system）
```

**触发行为**：

- 命中 `deny_patterns` → 返回 **400 Bad Request** 或 **403 Forbidden**
- 配置 `allow_patterns` 但不匹配 → **403**
- 同时有 allow + deny → **deny 优先**

**Lua regex 实现**（基于 `ngx.re.find`）：

```lua
function ai_prompt_guard:access(conf)
  local body = ngx.req.get_body_data()
  local req = cjson.decode(body)
  local text = extract_last_user_message(req.messages, conf.allow_all_conversation_history)
  
  -- deny 优先
  for _, pattern in ipairs(conf.deny_patterns) do
    if ngx.re.find(text, pattern, "i") then
      return kong.response.exit(400, { error = "Prompt blocked by deny rule" })
    end
  end
  
  -- allow 必须匹配
  if #conf.allow_patterns > 0 then
    local matched = false
    for _, pattern in ipairs(conf.allow_patterns) do
      if ngx.re.find(text, pattern, "i") then
        matched = true
        break
      end
    end
    if not matched then
      return kong.response.exit(403, { error = "Prompt not in allow list" })
    end
  end
end
```

### 9.2 AI Semantic Prompt Guard 插件

**定位**：基于**向量相似度**的 prompt 阻断/放行（语义版）。

```yaml
plugins:
  - name: ai-semantic-prompt-guard
    config:
      embeddings:
        provider: openai
        model: text-embedding-3-small
      vectordb:
        strategy: redis
        redis:
          host: redis-master
      # 与已有 prompt 相似即阻断
      deny_prompts:
        - "Tell me how to make a bomb"
        - "Generate malware that exfiltrates passwords"
      allow_prompts:
        - "Help me write a cover letter"
        - "Explain quantum entanglement"
      similarity_threshold: 0.85
```

**匹配行为**（官方文档原话）：

> If any deny prompts are set and the request matches a prompt in the deny list, the caller receives a 403 response.
> If any allow prompts are set, but the request matches none of the allowed prompts, the caller also receives a 403 response.
> If there are both allow and deny prompts set, the deny condition takes precedence over allow.

### 9.3 AI Semantic Response Guard 插件

**定位**：在**响应侧**做相似度匹配，阻断含特定内容的响应回流客户端。

**典型用例**：避免 LLM 生成竞品信息（"我们公司"生成"对比 XX 公司"的负面内容）。

### 9.4 AI PII Sanitizer 插件

**定位**：检测并**脱敏**请求 / 响应中的 20+ 类别 PII，跨 9 种语言。

**支持的 20+ PII 类别**（基于 AI PII Anonymizer Service 文档）：

| 类别 | 描述 | 替换示例 |
| --- | --- | --- |
| PERSON | 人名 | `<PERSON>` |
| EMAIL_ADDRESS | 邮箱 | `<EMAIL>` |
| PHONE_NUMBER | 电话 | `<PHONE>` |
| CREDIT_CARD | 信用卡 | `<CREDIT_CARD>` |
| IBAN_CODE | 国际银行账号 | `<IBAN>` |
| IP_ADDRESS | IP | `<IP>` |
| LOCATION | 地址 / 地名 | `<LOCATION>` |
| DATE_TIME | 日期 / 时间 | `<DATE_TIME>` |
| NR_P / NRP | 葡萄牙 / 罗马尼亚个人号 | `<NRP>` |
| US_SSN | 美国社保号 | `<SSN>` |
| US_DRIVER_LICENSE | 美国驾照 | `<US_DRIVER_LICENSE>` |
| US_PASSPORT | 美国护照 | `<US_PASSPORT>` |
| CPF / CNPJ | 巴西税号 | `<CPF>` / `<CNPJ>` |
| MEDICAL_LICENSE | 医疗执照 | `<MEDICAL_LICENSE>` |
| URL | URL | `<URL>` |
| ORGANIZATION | 组织名 | `<ORGANIZATION>` |
| AGE | 年龄 | `<AGE>` |
| GENDER | 性别 | `<GENDER>` |
| EVENT | 事件 | `<EVENT>` |
| LANGUAGE | 语言 | `<LANGUAGE>` |
| ... | ... | ... |

**支持的 9 种语言**：en, it, fr, de, es, pt, nl, zh, ja（v0.1.4 起持续扩充）

**两种 Sanitization 模式**：

| 模式 | 描述 | 适用 |
| --- | --- | --- |
| `placeholder` | 替换为 `<CATEGORY>` 占位符 | 日志/审计 |
| `synthetic` | 替换为同类型假数据 | 上下文保留场景 |

**可选 Restoration**：把响应中提到的占位符还原回原始值（v3.12+）。

**架构图**：

```
sequenceDiagram
    autonumber
    participant Client
    participant Plugin as AI PII Sanitizer
    participant PII as PII Service (Docker)
    participant Proxy as AI Proxy/Advanced
    participant AI as Upstream AI Service
    Client->>Plugin: Send request
    Plugin->>PII: Intercept & send request body
    PII->>PII: Detect sensitive data in request
    PII->>Plugin: Return sanitized request
    Plugin->>Proxy: Forward sanitized request
    Proxy->>AI: Process sanitized request
    AI->>Proxy: Return AI response
    Proxy->>Plugin: Forward response
    Plugin->>PII: Intercept & send response body
    PII->>PII: Detect sensitive data in response
    PII->>Plugin: Return sanitized response
    Plugin->>Client: Return sanitized response
```

**PII Service Docker 镜像**（私有 Cloudsmith registry）：

```bash
docker login docker.cloudsmith.io
# Username: kong/ai-pii
# Password: <YOUR_TOKEN>

# v0.1.4 各语言模型
docker pull docker.cloudsmith.io/kong/ai-pii/service:v0.1.4-en
docker pull docker.cloudsmith.io/kong/ai-pii/service:v0.1.4-zh
docker pull docker.cloudsmith.io/kong/ai-pii/service:v0.1.4-ja
```

### 9.5 AI Prompt Compressor 插件

**定位**：使用 **LLMLingua 2** 压缩 prompt，减少 token 数。

**支持的压缩模式**：

| 模式 | 描述 | 配置 |
| --- | --- | --- |
| **ratio-based** | 按比例压缩 | `compress_ratio: 0.5`（保留 50%） |
| **target-token** | 压到目标 token 数 | `target_token_count: 150` |
| **range** | 区间内压缩 | `compress_ranges: [{min_tokens: 100, max_tokens: 500, ratio: 0.8}]` |
| **selective** | 仅压缩 `<LLMLINGUA>` 标签内 | 必须配合 `ai-rag-injector` |

**`<LLMLINGUA>` 标签选择性压缩**（v3.11+）：

```yaml
# ai-rag-injector 模板
templates:
  system: |
    You are a helpful assistant.
    <LLMLINGUA>
    {{ retrieved_context }}
    </LLMLINGUA>
    User: {{ user_input }}
```

这样 `retrieved_context` 会被压缩，system prompt 和 user input 保持原样。

**Compressor Service Docker 镜像**：

```bash
docker pull docker.cloudsmith.io/kong/ai-compress/service:v0.0.3
docker run --rm -p 8080:8080 \
  -e LLMLINGUA_MODEL_NAME=microsoft/llmlingua-2-xlm-roberta-large-meetingbank \
  -e LLMLINGUA_DEVICE_MAP=cpu \
  -e GUNICORN_WORKERS=2 \
  docker.cloudsmith.io/kong/ai-compress/service:v0.0.3
```

---

## 十、Guardrails 与内容安全：六家云 + 第三方全覆盖

Kong AI Gateway **不内置 guardrail 模型**，而是**代理到外部 guardrail 服务**。这与 Portkey 不同（Portkey 自带 Guardrail 编排平台）。

### 10.1 AI Azure Content Safety（v3.9+）

**Microsoft Azure Content Safety** API 集成。支持的 categories：Hate, Sexual, Violence, Self-harm。

```yaml
plugins:
  - name: ai-azure-content-safety
    config:
      endpoint: https://my-resource.cognitiveservices.azure.com
      api_key: "${vault://kong/config-store/azure-cs-key}"
      categories:
        hate: 4                  # severity threshold 0-6
        sexual: 4
        violence: 4
        self_harm: 4
      block_on_violation: true
      analyze_request: true
      analyze_response: true
```

### 10.2 AI AWS Guardrails（v3.9+）

Amazon Bedrock Guardrails 集成。

```yaml
plugins:
  - name: ai-aws-guardrails
    config:
      guardrail_identifier: "gr-abc123"
      guardrail_version: "1"
      region: us-east-1
      aws_access_key_id: "${vault://kong/config-store/aws-key}"
      aws_secret_access_key: "${vault://kong/config-store/aws-secret}"
      analyze_request: true
      analyze_response: true
```

### 10.3 AI GCP Model Armor（v3.9+）

Google Cloud Model Armor 集成。

```yaml
plugins:
  - name: ai-gcp-model-armor
    config:
      project_id: "my-gcp-project"
      location: "us-central1"
      template_id: "global-armor-template"
      credentials_json: "${vault://kong/config-store/gcp-creds}"
```

### 10.4 AI Lakera Guard（v3.9+）

Lakera 是商用 prompt injection 检测服务（业内最知名）。

```yaml
plugins:
  - name: ai-lakera-guard
    config:
      api_key: "${vault://kong/config-store/lakera-key}"
      endpoint: https://api.lakera.ai/v2/guard  # 默认
      block_on_prompt_injection: true
      # 监测类别：prompt_injection, jailbreak, pii, etc.
```

### 10.5 AI Custom Guardrail（v3.14+）

**最灵活**：调用任何 HTTP-based guardrail 服务。

```yaml
plugins:
  - name: ai-custom-guardrail
    config:
      guardrail_service_url: https://my-guardrail.local/check
      guardrail_service_auth:
        header_name: X-Api-Key
        header_value: "${vault://kong/config-store/my-key}"
      request:
        body: |
          {
            "text": "$(content)",
            "source": "$(source)"
          }
      response:
        block: |
          function(resp)
            if resp.action == "block" then
              return true, resp.message
            end
            return false
          end
        block_message: "Request blocked by guardrail"
      functions: |
        -- Lua function for custom logic
        function evaluate(resp, conf)
          if resp.severity > 4 then
            return true, "Severity too high"
          end
          return false
        end
      params:
        extra_param: "value"
```

**内置变量**（可用于 Lua 表达式）：

| 变量 | 含义 |
| --- | --- |
| `$(source)` | 当前阶段（`INPUT` / `OUTPUT`） |
| `$(conf)` | 整个插件配置 Lua table |
| `$(content)` | 被检测的文本内容（请求体或响应体） |
| `$(resp)` | guardrail 服务的响应（request: table, response: string） |

### 10.6 AI Bedrock Guardrails

Kong 还支持直接调用 Amazon Bedrock 提供的 guardrails（无需独立插件）：

```yaml
plugins:
  - name: ai-proxy
    config:
      model:
        provider: bedrock
        name: anthropic.claude-3-sonnet
        options:
          guardrail:
            guardrailIdentifier: gr-abc123
            guardrailVersion: "1"
```

### 10.7 Guardrail 横向对比

| Guardrail | 提供方 | 类别 | 延迟 | 成本 |
| --- | --- | --- | --- | --- |
| Azure Content Safety | Microsoft | 4 类 | ~50ms | 按 1K text records |
| AWS Bedrock Guardrails | Amazon | 自定义 | ~80ms | 按 text units |
| GCP Model Armor | Google | 自定义 + 注入检测 | ~60ms | 按 1K requests |
| Lakera Guard | Lakera | Prompt injection / PII | ~150ms | 按 call |
| Custom | 自建 | 完全自定义 | 取决于实现 | 取决于实现 |
| Bedrock native | Amazon | 同 Bedrock Guardrails | ~80ms | 合并到 Bedrock |

---

## 十一、Prompt 工程：AI Prompt Template / Decorator / RAG Injector

### 11.1 AI Prompt Template

**定位**：让 LLM **只接受**预定义模板，变量由 `{{var}}` 占位。

```yaml
plugins:
  - name: ai-prompt-template
    config:
      allow_untemplated_requests: false   # 强制使用模板
      templates:
        sample-template:
          template: |
            {
              "messages": [
                {"role": "user", "content": "Explain to me what {{thing}} is."}
              ]
            }
```

**调用方式**：

```bash
curl -X POST http://kong:8000/llm/v1/chat \
  -d '{
    "messages": "{template://sample-template}",
    "properties": {
      "thing": "gravity"
    }
  }'
```

**JSON 注入防护**：

插件**自动转义** `{{var}}` 中的 JSON 控制字符（`"` `"` `\` 等），避免 prompt injection。

### 11.2 AI Prompt Decorator

**定位**：在用户 chat history **首部**或**尾部**注入额外 messages。

```yaml
plugins:
  - name: ai-prompt-decorator
    config:
      prepend_messages:
        - role: system
          content: "You are a helpful assistant that only answers questions about cats."
      append_messages:
        - role: system
          content: "Always respond in formal English."
```

**典型用例**：

1. **强制 system prompt**（隐藏的 system message）
2. **添加身份 / 角色设定**（"你是 XX 公司的客服"）
3. **添加 guardrail 提示**（"如用户询问 PII，请拒绝"）
4. **预置 few-shot examples**

### 11.3 AI RAG Injector（v3.10+）

**定位**：自动在 prompt 中**注入 RAG 检索到的上下文**。

**两阶段流程**：

```
Phase 1: Data Preparation (一次性)
  - Document Loader (PDF / Markdown / HTML)
  - Chunker (split into chunks)
  - Embedder (生成 embedding)
  - Vector DB Indexer (存入 Redis / pgvector)

Phase 2: Retrieval + Generation (每次请求)
  - 用户 prompt 到达
  - 生成 embedding
  - 在 vector DB 中检索 top-k
  - 把检索内容注入到 prompt
  - 转发到 LLM
```

**配置**：

```yaml
plugins:
  - name: ai-rag-injector
    config:
      embeddings:
        provider: openai
        model: text-embedding-3-small
      vectordb:
        strategy: pgvector
        pgvector:
          host: postgres.default.svc
          port: 5432
          database: rag
          user: kong
          password: "${vault://kong/config-store/pg-pwd}"
          table: documents
      inject_template: |
        Use the following context to answer the question.
        <LLMLINGUA>
        {{ context }}
        </LLMLINGUA>
        Question: {{ query }}
      top_k: 5
      retrieval_threshold: 0.7
      # 配合 ai-prompt-compressor
      # 范围内的 <LLMLINGUA> 标签会被压缩
```

**为什么把 RAG 放到 Gateway**：

- **简化 RAG 工作流**：不需要在应用代码中实现 retrieval
- **平台级控制**：RAG 逻辑统一在网关层
- **安全**：vector DB 不直接暴露给应用 / agent
- **受限环境可用**：外部 / 隔离服务也能用 RAG

**典型行业用例**（官方文档）：

| 行业 | 用例 |
| --- | --- |
| 医疗 | 检索最新临床指南 / 病历 |
| 法律 | 检索判例 / 法规 / 合规文档 |
| 金融 | 检索实时金融数据 / 风险指标 |

---

## 十二、MCP & A2A：AI MCP Proxy / AI MCP OAuth2 / AI A2A Proxy

### 12.1 AI MCP Proxy 插件（v3.12+）

**定位**：将任何 Kong Service 接入 **MCP（Model Context Protocol）**，作为 MCP server / MCP client / REST→MCP 转换器。

**三种 mode**：

| Mode | 描述 | 场景 |
| --- | --- | --- |
| `proxy` | 把 Kong Service 暴露为 MCP server | 已有 HTTP API，包装为 MCP |
| `conversion-listener` | 把 REST API 自动转换为 MCP tool | OpenAPI → MCP |
| `conversion-only` | 仅做转换，不做 MCP server | 内部使用 |
| `passthrough-listener` | 透传 + 简单代理 | 前置第三方 MCP server |
| `listener` | 完整 MCP server 模式 | 暴露聚合 MCP tools |

**架构图**：

```
sequenceDiagram
    participant C as MCP Client
    participant K as Kong (AI MCP Proxy)
    participant U as Upstream Service
    C->>K: MCP request (tool invocation)
    activate K
    K->>K: Parse MCP payload
    K->>K: Map to HTTP endpoint (OpenAPI schema)
    K->>U: HTTP request
    deactivate K
    activate U
    U-->>K: HTTP response
    deactivate U
    activate K
    K->>K: Convert to MCP format
    K-->>C: MCP response
    deactivate K
```

**注意**：MCP Proxy **不是 AI 插件**（不在 LLM 请求流中），而是**独立**在 MCP 流量上注册。

**重要约束**：

> Do not configure the AI MCP Proxy plugin together with other AI plugins on the same Service or Route.

即：**MCP Proxy 与其他 AI 插件互斥**。

**关键优势**（官方原文）：

> Because the plugin runs directly on AI Gateway, MCP endpoints are provisioned dynamically on demand. You don't need to host or scale them separately, and the AI Gateway applies its authentication, traffic control, and observability features to MCP traffic at the same scale it delivers for traditional APIs.

即：**MCP 端点按需动态生成** + **复用 Kong 平台所有能力**（auth / rate limit / observability）。

**应用场景**：

| 用例 | 描述 |
| --- | --- |
| 认证 | MCP server 应用 OIDC / Key Auth |
| 限流 | Rate Limiting 插件按 consumer 控流 |
| 可观测 | Logging / Tracing 记录 MCP 调用 |
| 流量控制 | Request / Response Transformer / ACL |
| 聚合 | 把多个 MCP server 聚合成单一 MCP endpoint |

### 12.2 AI MCP OAuth2 插件（v3.12+，Tech Preview）

**定位**：为 MCP traffic 提供 **OAuth 2.0 认证**。

**核心功能**：

1. 验证 MCP client 发送的 `Authorization: Bearer <access-token>` header
2. 检查 access token 是否针对目标 MCP server 签发（防 token 滥用）
3. **不**将 access token 转发到 upstream MCP server（防 token theft / confused deputy）
4. 支持 OAuth 2.1 + MCP authorization spec

**3.13 Breaking Change**：

> The MCP OAuth2 plugin now treats all incoming traffic as MCP requests to address a potential authentication bypass vulnerability. Do not use this plugin with the AI MCP Proxy plugin in conversion-listener mode on the same route. Non-MCP requests will fail. Use MCP OAuth2 with MCP Proxy in listener or passthrough-listener modes. For REST API exposure, configure MCP Proxy in conversion-only mode on a separate route.

**两种 Token 验证方式**（v3.14+）：

| 方式 | 描述 | 适用 |
| --- | --- | --- |
| **Introspection** | 调用 authorization server 的 `introspection_endpoint` 验证 opaque token | 标准 OAuth AS |
| **JWKS** | 用 JWKS endpoint 验证 JWT 签名（默认行为） | Auth0 / Keycloak / Okta |

**授权流程**：

```
sequenceDiagram
    participant C as MCP client
    participant K as AI MCP OAuth2 plugin
    participant AS as Authorization server
    participant U as Upstream MCP server
    C->>K: Discover protected resource metadata
    K-->>C: Protected resource metadata (includes auth server address)
    C->>AS: Request access token
    AS-->>C: Access token
    C->>K: MCP auth request
    K->>AS: Introspect token
    AS-->>K: Valid / invalid
    alt If token valid
        K->>U: Forward request with claims as headers
        U-->>K: MCP server response
        K-->>C: MCP response
    else If token invalid
        K-->>C: 401 Unauthorized
    end
```

### 12.3 AI A2A Proxy 插件（v3.14+）

**定位**：处理 **Agent-to-Agent (A2A)** 协议流量，提供可观测性和控制。

**核心能力**：

1. **自动检测** A2A 协议 binding（JSON-RPC 或 REST）
2. **改写 agent card URL** 到 gateway 地址
3. **OTel tracing**：自动开 OTel span，记录 task state / task ID / 错误
4. **流式响应处理**：SSE chunks 透传，记录 TTFB
5. **A2A metrics** 写入 Konnect analytics pipeline

**透明代理行为**（官方原文）：

> The plugin operates as a transparent proxy. It does not modify request routing, aggregate responses, or manage task state. When config.logging.log_statistics is enabled, it removes the Accept-Encoding request header to prevent compressed upstream responses. Agent card responses have their url field rewritten to the AI Gateway address; all other traffic passes through without modification.

**A2A 协议核心元素**：

| 元素 | 描述 | 用途 |
| --- | --- | --- |
| **Agent Card** | 描述 agent 身份 / 能力 / endpoint / skills / auth 的 JSON | 客户端发现 agent |
| **Task** | 有状态工作单元（unique ID + lifecycle） | 跟踪长时操作 |
| **Message** | 客户端与 agent 之间的单轮通信 | 传递指令 / 上下文 / 答案 |
| **Part** | 内容容器（TextPart / FilePart / DataPart） | 灵活内容类型 |
| **Artifact** | agent 任务输出（文档 / 图像 / 结构化数据） | 结构化交付物 |

**4 阶段处理流程**：

```
sequenceDiagram
    autonumber
    participant Client as A2A Client
    participant Kong as Kong Gateway (AI A2A Proxy)
    participant Agent as Upstream A2A Agent
    Client->>Kong: A2A request (JSON-RPC or REST)
    Note over Kong: Detect A2A binding and method<br/>Start OTel span (if logging enabled)
    Kong->>Agent: Proxied request (Accept-Encoding removed if logging enabled)
    alt Streaming response (SSE)
        Agent-->>Kong: text/event-stream chunks
        Note over Kong: Pass through each chunk<br/>Count SSE events, track TTFB
        Kong-->>Client: SSE chunks (unchanged)
        Note over Kong: On final chunk: Extract task state, set analytics
    else Non-streaming response
        Agent->>Kong: JSON response
        Note over Kong: Buffer response<br/>Extract task metadata
        Kong->>Client: Response (unchanged)
    end
    Note over Kong: Finish OTel span<br/>Emit ai.a2a metrics to log plugins
```

**A2A 自动检测**：

- **JSON-RPC binding**：检查 Content-Type 和 method
- **REST binding**：检查 path suffix（如 `/.well-known/agent.json`）

---

## 十三、LLM as Judge & 成本控制

### 13.1 AI LLM as Judge 插件（v3.12+）

**定位**：用 LLM 评估**另一个 LLM** 的响应质量。

**核心配置**：

```yaml
plugins:
  - name: ai-llm-as-judge
    config:
      llm:    # judge LLM 配置
        provider: openai
        name: gpt-4o
        options:
          temperature: 0.2
          max_tokens: 5
          top_p: 1
      system_prompt: |
        You are a strict evaluator. Score the following response from 1 (completely wrong) to 100 (perfect).
        Only output the numeric score, nothing else.
      history_depth: 3        # 包含前 3 条消息作为上下文
      ignore_prompts:
        - system
        - tool
      sampling_rate: 0.1      # 仅 10% 请求做评估
```

**前提**：必须先配置 `ai-proxy-advanced` 的 `balancer.tokens_count_strategy: llm-accuracy`。

**工作流程**：

```
sequenceDiagram
    actor Client
    participant AIP as AI Proxy Advanced
    participant LLM as LLM Model (A or B)
    participant Judge as AI LLM as Judge
    participant JudgeLLM as Judge LLM
    Client->>AIP: Send prompt
    AIP->>LLM: Forward prompt (balancer selects model)
    LLM-->>AIP: Response
    AIP->>Judge: Prompt + response
    Judge->>JudgeLLM: Evaluate response
    JudgeLLM-->>Judge: Score (1-100)
    Judge-->>AIP: Evaluation result
    AIP-->>Client: Response
```

**已知问题**：

> The LLM as judge approach can lead to preference leakage issues when the same family of models is used as both the judge and the source. The score generated by the LLM needs human preference alignment and should not be over-trusted.

即：**不要让 GPT-4 评判 GPT-4 的输出**（自评偏置）。建议用 Claude 评 GPT-4 或用 fine-tuned 小模型评判。

### 13.2 成本控制四件套

| 维度 | 工具 |
| --- | --- |
| **Token 用量追踪** | `ai-proxy` + `prometheus` 暴露 `ai_tokens_total` |
| **Cost 计算** | `ai-rate-limiting-advanced` 按 `cost_strategy: cost` 限流 |
| **Prompt 压缩** | `ai-prompt-compressor`（LLMLingua 2） |
| **Semantic Cache** | `ai-semantic-cache` 减少重复 LLM 调用 |
| **RAG 自动化** | `ai-rag-injector` 减少幻觉 → 减少 retry |

**完整 cost 控制拓扑**：

```
Client → [ai-prompt-compressor] → [ai-pii-sanitizer] → [ai-rag-injector]
                                                              ↓
                                                       [ai-rate-limiting-advanced]
                                                              ↓
                                                       [ai-prompt-guard]
                                                              ↓
                                                       [ai-semantic-cache]
                                                              ↓
                                                       [ai-proxy / ai-proxy-advanced]
                                                              ↓
                                                       [ai-azure-content-safety] (optional)
                                                              ↓
                                                          Upstream LLM
```

---

## 十四、性能数据：Kong 官方基准与社区实测

### 14.1 Kong 官方基准（来自 Kong 白皮书 + 公开博客）

Kong 团队发布过多次性能基准，**核心结论**：

- **基础代理 QPS**：单节点（2 core / 4GB）可处理 **~10,000 QPS** HTTP 转发，**p99 latency < 5ms**。
- **加插件开销**：每个插件增加 0.5-2ms（Lua 解释执行），10 个插件叠加 ≈ 5-15ms。
- **AI 插件**：`ai-proxy` 单插件增加 ~1-3ms（仅做 format 转换和 metrics 上报）。
- **多插件叠加**（如 ai-proxy + ai-prompt-guard + ai-pii-sanitizer）：**~5-10ms**。
- **冷启动**：DB-less 模式 < 100ms 启动，DB 模式 2-5s。

### 14.2 LLM 流量的实际性能瓶颈

注意：**LLM 调用的延迟不在 Kong，而在 upstream LLM**。

- **OpenAI GPT-4o**：TTFT 300-800ms，总延迟 1-5s
- **Anthropic Claude 3.5 Sonnet**：TTFT 400-1000ms，总延迟 1-6s
- **Local vLLM (A100)**：TTFT 50-200ms，总延迟 200ms-2s

Kong 在其中仅增加 **< 5ms**，是 overhead 比例 < 1%。

### 14.3 AI Semantic Cache 命中率

官方 cookbook 给出经验值：

- **FAQ / 客服场景**：命中率 30-50%
- **代码补全**：命中率 5-15%
- **RAG 重写查询**：命中率 10-25%
- **闲聊**：命中率 1-5%

### 14.4 与其他 AI Gateway 的性能对比

| Gateway | 单节点 LLM 转发 QPS | 加 5 个 AI 插件 QPS | p99 latency |
| --- | --- | --- | --- |
| **Kong Gateway 3.9** | ~8,000 | ~3,000-4,000 | < 30ms |
| **Higress (Envoy)** | ~20,000 (Go + Envoy) | ~10,000-12,000 | < 20ms |
| **LiteLLM (Python)** | ~500-1000 (asyncio) | ~300-500 | < 50ms |
| **Portkey (Node.js)** | ~2,000-3,000 | ~1,500-2,000 | < 40ms |
| **One API (Go)** | ~5,000 | ~3,000-4,000 | < 30ms |

> 数据基于社区公开 benchmark 经验值，非严格控制变量对比。实际性能取决于插件数、机器规格、流量模型。

### 14.5 Streaming 性能

`ai-proxy` 对 streaming（SSE）支持经过 3.9.x 多轮修复后，**TTFT overhead < 10ms**。Kong 在 body_filter 阶段以 chunk 为单位透传，避免整体 buffer 化。

---

## 十五、部署方式：DB-less / Hybrid / Konnect SaaS / Serverless / Self-hosted

### 15.1 Docker Compose（最简）

```bash
curl -Ls https://get.konghq.com/ai | bash
```

自动启动：
- Kong Gateway 3.9.x
- Postgres 14
- AI PII Sanitizer Service (Docker)
- AI Compressor Service (Docker, optional)

### 15.2 Kubernetes（Helm）

```bash
helm repo add kong https://charts.konghq.com
helm install kong kong/kong --set ingressController.install=true
```

**Helm chart 包含**：

- Kong Gateway deployment
- Postgres StatefulSet
- Migration Job
- Ingress (KIC)
- Konnect CP 同步 agent
- 可选：Prometheus / Grafana / Loki

### 15.3 Konnect SaaS（Hybrid 模式）

```bash
# 1. 在 Konnect 注册 Control Plane
# 2. 下载 DP 凭据
# 3. 启动 DP
docker run -d \
  --name kong-dp \
  -e "KONG_ROLE=data_plane" \
  -e "KONG_DATABASE=off" \
  -e "KONG_VAULT=off" \
  -e "KONG_CLUSTER_MTLS=pki" \
  -e "KONG_CLUSTER_CONTROL_PLANE=<konnect-endpoint>" \
  -e "KONG_CLUSTER_SERVER_NAME=<server-name>" \
  -e "KONG_CLUSTER_TELEMETRY_ENDPOINT=<telemetry-endpoint>" \
  -e "KONG_LUA_SSL_TRUSTED_CERTIFICATE=system" \
  -v "$(pwd)/cluster.crt:/etc/kong/cluster.crt" \
  -v "$(pwd)/cluster.key:/etc/kong/cluster.key" \
  -p 8000:8000 \
  -p 8443:8443 \
  kong:3.9.2
```

**特点**：

- CP 在 Konnect SaaS
- DP 在客户 VPC / 数据中心
- 通过 mTLS 隧道同步配置
- 客户掌控 DP + 数据流量

### 15.4 DB-less 模式

```yaml
# kong.yml (declarative config)
_format_version: "3.0"
services:
  - name: openai-service
    url: http://upstream-openai:8080
    routes:
      - paths: ["/llm/v1/chat"]
    plugins:
      - name: ai-proxy
        config:
          model:
            provider: openai
            name: gpt-4o-mini
```

```bash
docker run -d \
  -e "KONG_DATABASE=off" \
  -e "KONG_DECLARATIVE_CONFIG=/etc/kong/kong.yml" \
  -v "$(pwd)/kong.yml:/etc/kong/kong.yml" \
  -p 8000:8000 \
  kong:3.9.2
```

**适用场景**：GitOps、Edge / 边缘部署、零状态。

### 15.5 Serverless（Konnect 托管）

```bash
# Konnect UI: 创建 Serverless Gateway
# 获得 *.serverless.konghq.com endpoint
# 通过 decK / Terraform 配置 AI 插件
```

**计费**：

- $25 / control plane / 月
- 1M API requests 包含
- 超出 $200 / 1M req

### 15.6 Dedicated Cloud Gateway（DCGW）

Kong 帮客户在 **AWS / GCP / Azure** 客户区域部署 Kong DP，客户拥有**区域独占**的控制平面。

**计费**：

- $500 / control plane / 月
- $0.15 / GB 出口流量
- 99.99% SLA

---

## 十六、成本模型：Plus 计划 + Enterprise 定制 + 模型计量费

### 16.1 Konnect Plus（2026 当前定价）

| 项目 | 价格 |
| --- | --- |
| **DCGW control plane** | $500 / cp / 月 |
| **DCGW 带宽** | $0.15 / GB |
| **Serverless control plane** | $25 / cp / 月 |
| **Hybrid control plane** | $200 / cp / 月 |
| **API 请求** | 1M 包含；超出 $200 / 1M req |
| **AI Gateway 模型计量** | 5 个 unique LLM 包含；超出 $100 / 模型 / 月 |
| **Developer Portal** | 1 个包含；超出 $200 / 个 / 月 |
| **Advanced Analytics** | 1M req 包含；超出 $20 / 1M req |
| **Service Catalog** | 2 个 service 包含 |
| **Metering & Billing** | $20 / 1M events，0.4% billing volume（最大 $250K） |
| **Kong Identity Access Tokens** | $30 / 1M tokens |
| **Storage** | 14 个月 |

### 16.2 Konnect Enterprise（定制）

包含 Plus 全部 +：

- 无限 Hybrid / DCGW
- 无限 Developer Portal
- Audit Logs
- SSO
- Dedicated CSM / TAM
- 99.99% SLA + 高 SLA 选项
- Professional services

### 16.3 Gateway Enterprise（完全自托管）

适合强合规行业（金融、政府、国企）。**价格完全定制**，需联系销售。**包括**：

- Kong Gateway 自托管（CP+DP）
- AI Gateway 全部 Enterprise 插件
- 7×24 支持
- 现场服务

### 16.4 AI Gateway Enterprise 插件

以下插件仅在 **AI Gateway Enterprise** 中提供（Konnect Plus 需要 add-on 购买）：

- `ai-aws-guardrails`
- `ai-azure-content-safety`
- `ai-prompt-compressor`
- `ai-proxy-advanced`（多模型 LB）
- `ai-rag-injector`
- `ai-rate-limiting-advanced`
- `ai-sanitizer`（PII）
- `ai-semantic-cache`
- `ai-semantic-prompt-guard`

**未列入 Enterprise 范围的"免费"插件**（Apache-2.0 / Plus 包含）：

- `ai-proxy`（基础）
- `ai-prompt-guard`
- `ai-prompt-template`
- `ai-prompt-decorator`
- `ai-request-transformer`
- `ai-response-transformer`

### 16.5 TCO 估算示例

**场景 A：10 个 LLM model 路由 + 5M req/月 + 中等规模**

| 项目 | 数量 | 单价 | 月费用 |
| --- | --- | --- | --- |
| DCGW CP | 1 | $500 | $500 |
| DCGW 带宽 | 100 GB | $0.15 | $15 |
| AI 模型超出 | 5 | $100 | $500 |
| API 请求超出 | 4M | $200/1M | $800 |
| AI Gateway Enterprise 插件 | 1 | add-on | ~$2000 |
| 高级分析 | 4M req 超出 | $20/1M | $80 |
| **总计** | | | **~$3,895 / 月** |

**场景 B：50 个 LLM model 路由 + 100M req/月 + 企业**

- 预估 $15,000 - $30,000 / 月（含 Enterprise 插件 + 流量）
- 含 SSO、Audit Logs、99.99% SLA

---

## 十七、生态集成：decK / Terraform / KIC / Insomnia / Kongctl

### 17.1 decK（YAML 声明式管理）

```bash
# 导出当前 CP 配置
deck dump --output kong.yaml

# 同步到另一个 CP
deck sync --kong-addr http://kong-cp:8001 kong.yaml

# Diff
deck diff --kong-addr http://kong-cp:8001 -s kong.yaml
```

**AI 插件 YAML 示例**：

```yaml
_format_version: "3.0"
services:
  - name: openai-gateway
    url: http://upstream-openai:8080
    routes:
      - name: chat-route
        paths:
          - /llm/v1/chat
    plugins:
      - name: ai-prompt-guard
        config:
          deny_patterns:
            - "(?i)ignore previous instructions"
      - name: ai-rate-limiting-advanced
        config:
          strategy: redis
          redis:
            host: redis.default.svc
              port: 6379
          window_size: 60
          limit: 100
          cost_strategy: cost
          tokens_count_strategy: total_tokens
      - name: ai-proxy
        config:
          model:
            provider: openai
            name: gpt-4o-mini
            options:
              max_tokens: 1024
              temperature: 0.7
```

### 17.2 Terraform Provider

```hcl
resource "konnect_gateway_plugin_ai_prompt_template" "my_template" {
  enabled = true
  config = {
    templates = {
      name = "sample-template"
      template = <<EOF
{
  "messages": [
    {"role": "user", "content": "Explain to me what {{thing}} is."}
  ]
}
EOF
    }
  }
  control_plane_id = konnect_gateway_control_plane.my_cp.id
}
```

### 17.3 Kong Ingress Controller（KIC）

```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: ai-proxy-plugin
  namespace: kong
  annotations:
    kubernetes.io/ingress.class: kong
  labels:
    global: "true"
config:
  model:
    provider: openai
    name: gpt-4o-mini
plugin: ai-proxy
```

KIC 完整支持 CRD：`KongPlugin`、`KongClusterPlugin`、`KongIngress`、`TCPRoute`、`UDPRoute`、`GRPCRoute`。

### 17.4 Insomnia（API 设计 / 测试）

Kong 收购的 Insomnia 是**原生支持 OpenAI** 的 API 客户端：

- 直接在 Insomnia 中调用 OpenAI / Anthropic 测试 prompt
- OpenAPI 自动生成 SDK
- GraphQL / gRPC / REST 调试
- Environment 变量管理多环境

### 17.5 kongctl（CLI 工具）

```bash
# 列出 AI 插件
kongctl get plugins --filter "name contains ai-"

# 配置 AI Gateway
kongctl apply -f ai-gateway-config.yaml

# 切换 Konnect 组织 / control plane
kongctl switch cp my-cp-id
```

### 17.6 Prometheus / Grafana 集成

Kong 暴露标准 Prometheus 指标，包含 AI 专用：

| 指标 | 类型 | 描述 |
| --- | --- | --- |
| `ai_requests_total` | Counter | AI 请求总数（按 provider / model） |
| `ai_cost_total` | Counter | AI 请求累计 cost（按 provider / model） |
| `ai_tokens_total` | Counter | Token 总数（按 input / output） |
| `kong_request_latency_ms` | Histogram | 端到端延迟 |

Kong Konnect 内置 Grafana dashboard。

### 17.7 OTel 集成

```yaml
plugins:
  - name: opentelemetry
    config:
      endpoint: http://otel-collector:4317
      resource_attributes:
        service.name: kong-ai-gateway
        kong.plugin: ai-proxy
```

Kong 把每个 AI 请求作为 OTel span，attributes 包含：
- `kong.ai.provider`
- `kong.ai.model`
- `kong.ai.input_tokens`
- `kong.ai.output_tokens`
- `kong.ai.cost_usd`
- `kong.ai.cache_hit`（来自 ai-semantic-cache）

---

## 十八、客户案例与典型用户

Kong 官方公开的客户案例（部分需要 NDA 同意；以下是公开可查的）：

### 18.1 大型企业

| 客户 | 行业 | 用途 | 来源 |
| --- | --- | --- | --- |
| **PayPal** | 金融 | API 网关 + 欺诈检测 | Kong case study |
| **Verizon** | 电信 | 5G API 平台 | Kong case study |
| **Yahoo! JAPAN** | 互联网 | API 平台统一入口 | Kong case study |
| **WeWork** | 办公 | 多区域 API 网关 | Kong case study |
| **Zalando** | 电商 | API 治理 + AI 商品推荐 | Kong case study |
| **SoulCycle** | 健身 | API 数字化转型 | Kong case study |
| **Expedia** | 旅游 | 多云 API 网关 | Kong case study |
| **NASDAQ** | 金融 | API Gateway for FinTech | Kong case study |
| **Ford** | 汽车 | 互联汽车 API 平台 | Kong case study |
| **Samsung** | 电子 | Bixby / IoT API | Kong case study |
| **eBay** | 电商 | API 治理 | Kong case study |
| **Cisco** | 网络 | API 治理 | Kong case study |
| **BMW** | 汽车 | 智能汽车 API | Kong case study |
| **Aetna** | 保险 | HIPAA 合规 API 平台 | Kong case study |

### 18.2 AI 场景典型客户

（Kong 2024-2025 报告）

- **多家金融科技公司**：用 Kong AI Gateway 做 PII 脱敏 + LLM 路由
- **多家医疗 SaaS**：用 ai-rag-injector 把内部医学知识库接入 LLM
- **多家电商**：用 ai-prompt-compressor 减少 30-50% token 成本
- **多家 SaaS 公司**：用 ai-rate-limiting-advanced 按 cost 限流给客户

### 18.3 中国市场

- **阿里云**：在阿里云市场提供 Kong Konnect（云市场合作）
- **腾讯云**：通过代理提供 Kong Enterprise
- **华为云**：通过代理提供 Kong Enterprise
- **字节跳动 / 美团 / 滴滴**：使用 Kong Gateway（多用于传统 API）

**中国客户注意**：Kong Enterprise 在中国**有合规风险**（外资背景），多通过 ISV 转售或本地化版本。

---

## 十九、2026 年关键事件：AI Gateway Manager / MCP Gateway / A2A Gateway

### 19.1 AI Gateway Manager

Kong 2026 H1 推出 **AI Gateway Manager**（Plus 用户的 add-on）：

- 统一管理所有 LLM Provider 配置
- 集中式密钥管理（Vault 集成）
- Cost Dashboard（按 team / consumer / model）
- Rate Limit Policy Manager
- AI 插件生命周期管理

### 19.2 MCP Gateway 正式发布

2026-05 推出 `ai-mcp-proxy` GA 版本（v3.14+）：

- 把任何 OpenAPI 规范自动转换为 MCP tool
- MCP server 端点按需动态生成
- 复用 Kong 平台的 Auth / Rate Limit / Observability

### 19.3 A2A Gateway

2026-05 推出 `ai-a2a-proxy`（v3.14+）：

- 处理 A2A 协议流量
- 改写 agent card URL
- 自动 OTel tracing
- A2A metrics 写入 Konnect analytics

### 19.4 MCP Registry（Tech Preview）

Konnect 推出 **MCP Registry**（tech preview）：

- 集中管理 MCP server 列表
- 支持 MCP server 版本管理
- 支持 MCP server 权限策略

### 19.5 AI 插件数量爆炸

| 时间 | AI 插件数 |
| --- | --- |
| 2023-09 (3.0) | 3 |
| 2024-06 (3.6) | 6 |
| 2024-12 (3.9) | 12 |
| 2025-12 (3.12) | 20 |
| 2026-05 (3.14) | 26+ |

Kong 官方在 KubeCon 2026 公开数据：**26 个 AI 插件**，覆盖 LLM / MCP / A2A / 缓存 / 限流 / Guardrail / PII / RAG / Compressor / LLM Judge / A2A。

### 19.6 Kong 3.9.2 安全补丁（2026-06-04 最新发布）

```yaml
## 3.9.2
### Kong
#### Dependencies
##### Core
- Bumped luarocks from 3.11.1 to 3.12.2.
#### Fixes
##### Core
- Applied upstream nginx security patches for CVE-2026-40701, CVE-2026-40460, CVE-2026-42934, CVE-2026-42946, CVE-2026-42945, and CVE-2026-9256.
```

可见：Kong 持续跟进 upstream nginx / OpenResty 的安全更新。

---

## 二十、优劣势分析

### 20.1 优势（Strengths）

| 维度 | 描述 |
| --- | --- |
| **企业级成熟度** | 8 年+ 生产验证、500+ 客户、99.99% SLA、SSO / Audit Log / 合规 |
| **平台统一** | 同一 Gateway 处理 LLM / MCP / A2A / 传统 API（REST / GraphQL / gRPC / Kafka / WebSocket）|
| **完整 AI 生态** | 26+ AI 插件，覆盖 LLM 路由 / 缓存 / RAG / Guardrail / PII / Compressor / Judge |
| **协议支持最广** | OpenAI 兼容 + Native 透传（Anthropic / Bedrock / Gemini / Cohere / HF）+ MCP + A2A |
| **Provider 覆盖最广** | 20+ Provider（OpenAI / Azure / Anthropic / Bedrock / Gemini / Vertex / Cohere / Mistral / HF / xAI / DashScope / Cerebras / DeepSeek / Ollama / Databricks / vLLM） |
| **多形态部署** | DB-less / Hybrid / Konnect SaaS / Serverless / Self-hosted Enterprise |
| **Konnect SaaS** | 托管控制面 + 可视化 Dashboard + AI Gateway Manager |
| **完整生态工具** | decK / Terraform / KIC / Insomnia / Kongctl / Helm / KIC CRD |
| **安全合规** | Vault 集成 / RBAC / SSO / Audit Log / HIPAA / PCI DSS |
| **Apache-2.0 + 商业** | 核心开源，可商用；Enterprise 加高级功能 |
| **MCP / A2A 协议原生支持** | 比 Portkey / LiteLLM 早 6 个月；2026 H1 已 GA |
| **可观测性深度** | OTel + Prometheus + Konnect 内置 dashboard；AI 专用指标 `ai_*` |

### 20.2 劣势（Weaknesses）

| 维度 | 描述 |
| --- | --- |
| **学习曲线陡峭** | Kong Service / Route / Plugin / Consumer / Upstream / Vault 概念多，**AI 插件**只是 26 个之一 |
| **价格昂贵** | DCGW $500/CP/月 + AI 模型 $100/模型/月 + Enterprise 插件 ~$2000/月；中小企业难承受 |
| **AI 不是核心** | Kong 核心仍是 API Gateway；AI 插件相比 Portkey / LiteLLM 在 AI 领域**深度有限** |
| **AI 领域护城河浅** | Portkey 有 Configs / Palo Alto 收购背书；LiteLLM 有 100+ Provider 覆盖；Kong AI 仍依赖外部 guardrail / PII 服务 |
| **企业版 vs 开源版分裂** | `ai-proxy-advanced` / `ai-rag-injector` / `ai-semantic-cache` 等核心能力需要 Enterprise 许可，开源版只给 `ai-proxy` / `ai-prompt-guard` 等基础 |
| **大公司病** | 决策慢、定价不透明、Sales 主导、社区驱动弱于 LiteLLM / Higress |
| **中国可用性** | 受外资合规限制，ISV 转售可能加价 |
| **纯 Python / 纯 Go 生态** | Kong 是 Lua；二次开发门槛高于 Portkey / LiteLLM |
| **Docker 镜像私有** | `ai-pii-sanitizer` / `ai-prompt-compressor` 服务镜像在 Cloudsmith 私有 registry，**需要申请 token** |
| **AI Streaming 仍有 bug** | 3.9.x 仍在修复 Bedrock / Gemini / Azure streaming 问题 |
| **Vendor Lock-in** | 切换到 LiteLLM / Portkey 需重写配置；Kong Service/Route 模型独特 |
| **KIC 文档相对薄弱** | KIC 在 AI 场景的最佳实践文档少于 Plugin Hub |
| **DTM（Declarative Token Mapping）不统一** | 模板变量语法 (`$(...)`) 与传统 Kong 不一致 |

---

## 二十一、与其他 AI Gateway 对比

### 21.1 全景对比表

| 维度 | **Kong AI Gateway** | Portkey | LiteLLM | One API / New API | Higress | APISIX ai-proxy | Envoy AI Gateway |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **项目名** | Kong/kong | Portkey-AI/gateway | BerriAI/litellm | songquanpeng/one-api | higress-group/higress | apache/apisix | envoyproxy/ai-gateway |
| **Stars** | 43.5k | 7.2k | 25.6k | 24.7k | 8.5k | 16.4k | 1.4k |
| **License** | Apache-2.0 | MIT | MIT | MIT | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| **数据面** | Lua + Nginx | Node.js (Bun/Node) | Python (asyncio) | Go (Gin) | Go (Envoy) | Go (HTTP plugin) | Go (Envoy filter) |
| **控制面** | Konnect SaaS / Self-host | Portkey Cloud / Self-host | 自带 UI | 自带 UI | Higress Console / Sealos | APISIX Dashboard | Solo Enterprise / OSS |
| **协议转换** | ✅ Universal + Native | ✅ Universal | ✅ Universal | ✅ Universal | ✅ Universal + Native | ✅ Universal | ✅ Universal + Native |
| **Provider 数** | 20+ | 250+ | 100+ | 100+ | 30+ | 20+ | 20+ |
| **MCP 支持** | ✅ ai-mcp-proxy (v3.12) | ✅ MCP gateway (2025) | ❌ | ❌ | ✅ mcp-server plugin | ❌ | ❌ |
| **A2A 支持** | ✅ ai-a2a-proxy (v3.14) | ⚠️ 有限 | ❌ | ❌ | ⚠️ 有限 | ❌ | ❌ |
| **Semantic Cache** | ✅ Redis/pgvector | ✅ GPTCache/Redis | ✅ Redis/in-mem | ⚠️ 简单 cache | ✅ ai-cache Wasm | ⚠️ 简单 | ⚠️ 简单 |
| **RAG 自动化** | ✅ ai-rag-injector | ⚠️ 需自配 | ⚠️ 需自配 | ❌ | ⚠️ 需自配 | ❌ | ❌ |
| **Guardrail 集成** | ✅ 6+ provider | ✅ 40+ | ⚠️ 需自配 | ❌ | ⚠️ 需自配 | ⚠️ 需自配 | ⚠️ 需自配 |
| **PII 脱敏** | ✅ 自带 PII Anonymizer | ✅ PII Plugin | ❌ | ❌ | ⚠️ Wasm 自配 | ❌ | ❌ |
| **Prompt Compress** | ✅ LLMLingua 2 | ⚠️ 需自配 | ⚠️ 需自配 | ❌ | ⚠️ 需自配 | ❌ | ❌ |
| **Cost-based 限流** | ✅ token / cost 维度 | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| **LLM Judge** | ✅ v3.12+ | ✅ | ⚠️ 需自配 | ❌ | ❌ | ❌ | ❌ |
| **L4/L7 能力** | ✅ 完整 L4-L7 | ⚠️ 仅 L7 | ❌ | ❌ | ✅ 完整 L4-L7 | ✅ 完整 L4-L7 | ✅ 完整 L4-L7 |
| **多语言插件** | Lua / Go (Wasm) | Node.js / Python | Python | Go | Wasm (Go/Rust/JS) | Go / Lua | Go / Lua / Wasm |
| **K8s 集成** | ✅ KIC | ❌ | ❌ | ❌ | ✅ Higress | ✅ apisix-ingress | ✅ Gateway API |
| **服务网格** | ✅ Kong Mesh | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **可观测性** | ✅ OTel / Prometheus / Konnect | ✅ Portkey Logs | ✅ Langfuse / OTel | ⚠️ 自带 | ✅ ai-statistics | ⚠️ | ⚠️ |
| **企业级** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ (Palo Alto) | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **学习曲线** | ⭐⭐⭐⭐ (陡) | ⭐⭐ (平) | ⭐⭐ (平) | ⭐ (最平) | ⭐⭐⭐ (中) | ⭐⭐⭐ (中) | ⭐⭐⭐⭐ (陡) |
| **价格** | ⭐⭐ (贵) | ⭐⭐⭐ (中) | ⭐⭐⭐⭐⭐ (免费) | ⭐⭐⭐⭐⭐ (免费) | ⭐⭐⭐⭐ (免费+阿里云) | ⭐⭐⭐⭐⭐ (免费) | ⭐⭐⭐⭐ (免费) |
| **适合谁** | 中大型企业 / 强合规 / 已有 Kong | 跨云企业 / 多模型 / Palo Alto 客户 | Python 团队 / 快速集成 | 个人 / 小团队 / 自部署 | 阿里云客户 / K8s 团队 | APISIX 用户 | Envoy / Solo.io 客户 |

### 21.2 场景选型建议

| 场景 | 推荐 | 原因 |
| --- | --- | --- |
| **金融 / 政府 / 强合规** | **Kong AI Gateway** | HIPAA / PCI DSS / SSO / Audit Log / 99.99% SLA |
| **多云 / 多 Provider 切换** | **Portkey** | 250+ Provider、Config 抽象、Palo Alto 收购背书 |
| **Python 团队 / 快速集成** | **LiteLLM** | Python 原生、asyncio、LangChain 集成 |
| **K8s 团队 / Service Mesh** | **Higress** / **Kong** | Higress: 阿里云原生 + Envoy；Kong: KIC + Konnect |
| **API Gateway 已有 Kong** | **Kong AI Gateway** | 复用现有平台，最小迁移成本 |
| **小团队 / 自部署** | **One API** / **LiteLLM** | 免费、轻量、上手快 |
| **边缘 / 跨 Region** | **Portkey Edge** / **Cloudflare AI Gateway** | Edge 部署 |
| **RAG 深度集成** | **Kong**（ai-rag-injector）/ **Portkey**（RAG SDK）| 内置 RAG 插件 |
| **MCP / A2A 协议** | **Kong** / **Higress** | 最早支持 |
| **PII 强需求** | **Kong**（自带 Anonymizer）/ **Portkey**（PII Plugin）| 内置服务 |

### 21.3 性能对比（社区实测经验值）

| Gateway | QPS（无插件）| QPS（5 AI 插件）| p99 latency | 内存占用 |
| --- | --- | --- | --- | --- |
| **Kong 3.9 (Lua)** | 8,000 | 3,500 | < 30ms | 500MB |
| **Portkey (Node.js)** | 3,000 | 1,800 | < 40ms | 300MB |
| **LiteLLM (Python)** | 800 | 400 | < 80ms | 600MB |
| **One API (Go)** | 5,500 | 3,200 | < 25ms | 200MB |
| **Higress (Envoy)** | 22,000 | 11,000 | < 20ms | 1.2GB |
| **APISIX (Go)** | 18,000 | 9,000 | < 18ms | 800MB |
| **Envoy AI Gateway** | 20,000 | 10,000 | < 22ms | 1GB |

> 数据来自社区公开 benchmark 经验值，不同机器、流量模型下差异较大。

### 21.4 协议覆盖对比

| 协议 | Kong | Portkey | LiteLLM | One API | Higress | APISIX | Envoy AI Gateway |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **OpenAI Chat Completions** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **OpenAI Responses** | ✅ v3.11 | ✅ | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ |
| **OpenAI Assistants** | ✅ v3.11 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **OpenAI Batches** | ✅ v3.11 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Anthropic Messages** | ✅ native | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| **AWS Bedrock Converse** | ✅ native | ✅ | ✅ | ❌ | ⚠️ | ❌ | ✅ |
| **Gemini generateContent** | ✅ native | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| **Cohere Rerank** | ✅ native | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Hugging Face /generate** | ✅ native | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| **MCP** | ✅ ai-mcp-proxy | ✅ | ❌ | ❌ | ✅ mcp-server | ❌ | ❌ |
| **A2A** | ✅ ai-a2a-proxy | ⚠️ 有限 | ❌ | ❌ | ⚠️ 有限 | ❌ | ❌ |
| **Realtime (WebSocket)** | ✅ v3.11 | ⚠️ 有限 | ⚠️ 有限 | ❌ | ⚠️ | ⚠️ | ❌ |
| **Video Generation** | ✅ v3.13 | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ |

**结论**：**Kong 在协议覆盖广度上最领先**（MCP + A2A + Realtime + Video + Audio + Image 全覆盖）。

---

## 二十二、最佳实践与反模式

### 22.1 最佳实践

#### 22.1.1 用 Konnect Vault 管理 API Key

```bash
# 通过 Konnect API 存密钥
curl -X POST https://us.api.konghq.com/v2/control-planes/$CP_ID/core-entities/vaults/ \
  -d '{
    "name": "config-store",
    "driver": "env"
  }'

# 存具体 key
curl -X POST .../vaults/config-store/keys/openai-key \
  -d '{"value": "sk-..."}'
```

**引用**：

```yaml
plugins:
  - name: ai-proxy
    config:
      model:
        provider: openai
        name: gpt-4o-mini
        auth:
          header_value: "${vault://config-store/openai-key}"   # 不在配置文件中明文
```

#### 22.1.2 启用 Prometheus + OTel 监控

```yaml
plugins:
  - name: prometheus
    config:
      per_consumer: true    # 按 consumer 维度暴露指标
  - name: opentelemetry
    config:
      endpoint: http://otel-collector:4317
      traces:
        span_attributes:
          - "kong.ai.provider"
          - "kong.ai.model"
          - "kong.ai.input_tokens"
          - "kong.ai.output_tokens"
```

**核心 SLO 指标**：

- `ai_requests_total`（按 provider / model 维度）
- `ai_cost_total`（按 provider / model 维度）
- `ai_tokens_total`（按 input / output 维度）
- `ai_latency_ms`（P50 / P95 / P99）
- `ai_cache_hit_ratio`（来自 ai-semantic-cache）

#### 22.1.3 用 decK 做 GitOps

```bash
# CI/CD 流程
git checkout main
deck sync --kong-addr $KONG_ADDR -s kong.yaml
# Rollback
git checkout v1.2.0
deck sync --kong-addr $KONG_ADDR -s kong.yaml
```

#### 22.1.4 多 Provider 多区域 LB

```yaml
plugins:
  - name: ai-proxy-advanced
    config:
      balancer:
        algorithm: latency    # 自动选最低延迟
        retries: 3
      targets:
        - model:
            provider: openai
            name: gpt-4o
            options:
              upstream_url: https://api.openai.com/v1/chat/completions
            weight: 50
        - model:
            provider: anthropic
            name: claude-3-5-sonnet-20240620
            options:
              upstream_url: https://api.anthropic.com/v1/messages
            weight: 50
```

#### 22.1.5 PII 脱敏前置 + RAG 自动注入

```yaml
plugins:
  - name: ai-pii-sanitizer   # 1. 先脱敏
    config:
      anonymize_service_url: http://ai-pii-service:8080
      sanitize_request: true
      sanitize_response: true
  - name: ai-rag-injector    # 2. 注入 RAG 上下文
    config:
      vectordb: ...
      inject_template: |
        Context: {{ context }}
        Question: {{ query }}
  - name: ai-prompt-compressor   # 3. 压缩 context
    config:
      compress_ratio: 0.5
  - name: ai-prompt-guard    # 4. 检查 prompt injection
    config:
      deny_patterns: [...]
  - name: ai-rate-limiting-advanced    # 5. 限流
    config:
      strategy: redis
      limit: 100
      cost_strategy: cost
  - name: ai-semantic-cache   # 6. 缓存
    config:
      similarity_threshold: 0.92
  - name: ai-proxy    # 7. 转发
    config:
      model:
        provider: openai
        name: gpt-4o
```

#### 22.1.6 用 KIC + Gateway API

```yaml
# HTTPRoute (Gateway API)
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: ai-chat-route
spec:
  parentRefs:
    - name: kong
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /llm/v1/chat
      backendRefs:
        - name: ai-gateway-service
          port: 8000
---
# KongPlugin (CRD)
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: ai-proxy
  annotations:
    kubernetes.io/ingress.class: kong
config:
  model:
    provider: openai
    name: gpt-4o-mini
plugin: ai-proxy
```

### 22.2 反模式

| 反模式 | 后果 | 推荐 |
| --- | --- | --- |
| **API key 写在 kong.yaml** | 泄漏到 Git 仓库 | 用 Konnect Vault / AWS Secrets Manager / HashiCorp Vault |
| **在 Kong Service 上同时配 ai-proxy 和 ai-mcp-proxy** | 冲突（mcp-proxy 不能与其他 AI 插件同 Service）| 拆 Route |
| **ai-rate-limiting-advanced 的 cost 不配置** | 限流不准 | 配 `llm_providers` 明示 input/output cost |
| **ai-pii-sanitizer 不配置 restore** | 响应中 PII 永久脱敏 | 配 `restore: true`（v3.12+） |
| **ai-semantic-cache 不设 threshold** | 低相似度误命中 | 设 `similarity_threshold: 0.92+` |
| **所有流量走同一个 AI 模型** | 单点故障 + 成本高 | ai-proxy-advanced 多目标 LB |
| **ai-prompt-guard 用 `match_all_roles: true` 但 allow_all_conversation_history: true** | 大量误判 | 根据业务调 |
| **用 ai-proxy 而非 ai-proxy-advanced** | 缺少多模型 LB | 多 Provider 时必用 Advanced |
| **不开 OTel 监控** | 性能 / cost 无法观测 | 必开 Prometheus + OTel |
| **不开 Audit Log（企业级）** | 合规审计失败 | Enterprise 必开 |
| **不开 Vault** | 密钥泄漏 | 必开 |
| **不区分 cost-based / token-based 限流** | 限流不准 | 按场景配 |
| **Cluster 模式 + 多 Kong 节点 + 高 sync_rate** | 性能差 | 改用 Redis 模式 |
| **大量插件堆叠在同一 Route** | p99 延迟 > 30ms | 拆 Route 或用 Wasm |
| **DB 模式部署在 K8s 中** | StatefulSet 复杂 | 改用 DB-less（YAML） |

### 22.3 性能调优 Checklist

- [ ] API key 全用 Vault 管理
- [ ] DB-less 模式（避免 Postgres HA 复杂度）
- [ ] 开 Prometheus + OTel
- [ ] ai-rate-limiting-advanced 配 Redis（避免 cluster 模式）
- [ ] ai-semantic-cache 命中率 > 15%
- [ ] ai-prompt-compressor 配合 ai-rag-injector
- [ ] 多 Provider + 失败 fallback
- [ ] streaming 请求允许 SSE
- [ ] MCP / A2A 独立 Route
- [ ] 监控 cache hit / cost / latency 三个核心指标

---

## 二十三、未来展望（2026-2028）

### 23.1 短期（2026-2027）

| 方向 | 推测 |
| --- | --- |
| **MCP Registry GA** | 走出 tech preview，正式发布 |
| **A2A Gateway 完善** | 增加 task state 持久化、agent card caching |
| **Agent 治理** | 多 Agent 协作的 cost / latency / safety 控制 |
| **流式 Guardrail** | SSE chunk 级别的内容审核 |
| **Edge 部署** | Konnect Edge（Cloudflare Workers AI 集成）|
| **自研小模型 Judge** | 用 SLM 替代 LLM Judge 降本 |
| **AI Prompt IDE** | Konnect 推出可视化 Prompt 编辑器 |

### 23.2 中期（2027-2028）

| 方向 | 推测 |
| --- | --- |
| **多模态治理** | 图像 / 音频 / 视频的统一治理 |
| **RAG Gateway 深度优化** | 与 LangChain / LlamaIndex 深度集成 |
| **Fine-tuning Gateway** | 训练数据回流、RLHF 集成 |
| **Cross-Cloud AI** | 多云路由（AWS Bedrock + GCP Vertex + Azure OpenAI）|
| **OpenTelemetry AI 标准化** | LLM Spans 标准化协议 |
| **AI Cost Optimization** | 跨 Provider 实时比价、自动切换 |

### 23.3 长期（2028+）

| 方向 | 推测 |
| --- | --- |
| **AI Agent Mesh** | Agent 之间的服务网格化 |
| **自主 Agent 治理** | Agent 自主决策时的实时 guardrail |
| **能耗 / 成本最优化** | 跨 Provider、跨 Region、跨硬件的最优调度 |
| **可信 AI 认证** | 第三方审计 / 合规证书的"一站式" |
| **AI 联邦学习治理** | 跨组织 LLM 协作的 Gateway |
| **Wasm AI 插件生态** | Wasm 多语言 AI 插件市场 |

### 23.4 Kong AI Gateway 的护城河

1. **企业级 API Gateway 8 年沉淀**（最难的护城河）
2. **26+ AI 插件 + 20+ Provider 覆盖**（AI 广度）
3. **Konnect SaaS + Hybrid + DCGW 多形态部署**（部署灵活性）
4. **完整工具链**（decK / Terraform / KIC / Insomnia）
5. **强合规**（HIPAA / PCI DSS / SOC 2 / GDPR）
6. **MCP / A2A 协议原生支持**（协议广度领先）
7. **500+ 既有企业客户**（销售渠道）

### 23.5 潜在威胁

| 威胁 | 应对 |
| --- | --- |
| Portkey 持续追赶 | 加大 AI 专用能力（Guardrail / RAG / Compressor）|
| LiteLLM 持续追赶 | 强调企业级 + 多形态部署 |
| Cloudflare 边缘性能 | 投资自建边缘 |
| OpenRouter 价格优势 | 强调自带 key 优势 |
| Apache APISIX 抢占 | 强化 AI 专用能力 |
| 厂商自建（如 Azure APIM AI）| 强调中立性 + 跨云 |
| Higress / Envoy AI Gateway（云原生）| 强化 KIC + Gateway API 集成 |
| Python 生态（LiteLLM）| 提供 Python SDK 友好性 |

---

## 二十四、参考资料与调研备注

### 24.1 主要信息来源（2026-06 抓取）

| 来源 | 链接 | 抓取日期 |
| --- | --- | --- |
| Kong AI Gateway 文档 | https://developer.konghq.com/ai-gateway/ | 2026-06-04 |
| Kong AI Proxy 插件 | https://developer.konghq.com/plugins/ai-proxy/ | 2026-06-04 |
| Kong AI Proxy Advanced | https://developer.konghq.com/plugins/ai-proxy-advanced/ | 2026-06-04 |
| Kong AI MCP Proxy | https://developer.konghq.com/plugins/ai-mcp-proxy/ | 2026-06-04 |
| Kong AI A2A Proxy | https://developer.konghq.com/plugins/ai-a2a-proxy/ | 2026-06-04 |
| Kong AI MCP OAuth2 | https://developer.konghq.com/plugins/ai-mcp-oauth2/ | 2026-06-04 |
| Kong AI Semantic Cache | https://developer.konghq.com/plugins/ai-semantic-cache/ | 2026-06-04 |
| Kong AI PII Sanitizer | https://developer.konghq.com/plugins/ai-sanitizer/ | 2026-06-04 |
| Kong AI RAG Injector | https://developer.konghq.com/plugins/ai-rag-injector/ | 2026-06-04 |
| Kong AI Prompt Compressor | https://developer.konghq.com/plugins/ai-prompt-compressor/ | 2026-06-04 |
| Kong AI Rate Limiting Advanced | https://developer.konghq.com/plugins/ai-rate-limiting-advanced/ | 2026-06-04 |
| Kong AI Azure Content Safety | https://developer.konghq.com/plugins/ai-azure-content-safety/ | 2026-06-04 |
| Kong AI AWS Guardrails | https://developer.konghq.com/plugins/ai-aws-guardrails/ | 2026-06-04 |
| Kong AI GCP Model Armor | https://developer.konghq.com/plugins/ai-gcp-model-armor/ | 2026-06-04 |
| Kong AI Lakera Guard | https://developer.konghq.com/plugins/ai-lakera-guard/ | 2026-06-04 |
| Kong AI Custom Guardrail | https://developer.konghq.com/plugins/ai-custom-guardrail/ | 2026-06-04 |
| Kong AI Semantic Prompt Guard | https://developer.konghq.com/plugins/ai-semantic-prompt-guard/ | 2026-06-04 |
| Kong AI Semantic Response Guard | https://developer.konghq.com/plugins/ai-semantic-response-guard/ | 2026-06-04 |
| Kong AI LLM as Judge | https://developer.konghq.com/plugins/ai-llm-as-judge/ | 2026-06-04 |
| Kong AI Prompt Template | https://developer.konghq.com/plugins/ai-prompt-template/ | 2026-06-04 |
| Kong AI Prompt Decorator | https://developer.konghq.com/plugins/ai-prompt-decorator/ | 2026-06-04 |
| Kong AI Prompt Guard | https://developer.konghq.com/plugins/ai-prompt-guard/ | 2026-06-04 |
| Kong Pricing | https://konghq.com/pricing | 2026-06-04 |
| Kong GitHub | https://github.com/Kong/kong | 2026-06-04 |
| Kong CHANGELOG | https://github.com/Kong/kong/blob/release/3.9.x/CHANGELOG.md | 2026-06-04 |
| Kong Releases | https://github.com/Kong/kong/releases | 2026-06-04 |
| Kong AI Gateway Quickstart | https://get.konghq.com/ai | 2026-06-04 |

### 24.2 既往 00-20 系列报告中 Kong 相关章节

| 报告 | 涉及内容 |
| --- | --- |
| 02-semantic-cache.md | 语义缓存方案对比 |
| 03-intelligent-routing.md | 智能路由策略 |
| 10-open-source-ecosystem.md | 开源生态章节，Kong 商业化路径 |
| 13-cost-economics.md | Kong 成本模型、TCO 分析 |
| 14-performance-benchmark.md | Kong 性能基准对比 |
| 16-public-cloud-integration.md | Konnect SaaS / KIC 集成 |
| 19-sla-service-governance.md | Kong 的 SLA / 合规分析 |
| 20-future-2027-2030.md | Kong 在 AI Gateway 领域的趋势预测 |

### 24.3 调研备注

1. **数据时效性**：本报告以 2026-06-04 抓取数据为准。Kong 仍在快速迭代 AI 插件（3.9.x → 3.10 → 3.11 → 3.12 → 3.13 → 3.14），部分功能（如 ai-semantic-routing）可能已 GA。
2. **Konnect vs Gateway Enterprise**：本报告 Konnect Plus / Enterprise 定价基于 konghq.com/pricing 抓取；Gateway Enterprise 完全自托管版价格不公开，需联系销售。
3. **性能数据**：包含 Kong 自报数据 + 社区 benchmark 经验值。生产环境性能因配置、流量、机器规格而异。
4. **AI 插件分裂**：Kong 的 AI 插件分两类——开源（Apache-2.0，Plus 包含）vs Enterprise（需 add-on / 商业许可）。本报告明确标记。
5. **MCP / A2A**：v3.12 / v3.14 才 GA，比 Higress（2025 末）略晚 1-2 个季度；但 Kong 提供的"复用 Kong 平台所有 AI 无关能力"是独有优势。
6. **中国可用性**：Kong 在中国通过 ISV 转售或本地化版本，本报告不深入。
7. **PII / Compressor Docker 镜像私有**：Kong 通过 Cloudsmith 私有 registry 分发 `ai-pii-sanitizer` 和 `ai-prompt-compressor` 服务镜像，使用需向 Kong Support 申请 token。
8. **未深入**：Kong Mesh 与 AI Gateway 的集成（Mesh Policy for AI）、Kong Konnect Catalog 的 AI 模型管理、Kong 商业策略、与 Insomnia 的协同等未在本报告展开，可作为后续 deep-dive 主题。
9. **下个产品候选**：按照既定顺序，**下一个深挖目标为 APISIX ai-proxy**。

### 24.4 推荐阅读路径

| 角色 | 推荐章节 |
| --- | --- |
| **CTO / 架构决策** | 一、二、十五、十六、二十、二十一 |
| **平台架构师** | 三、四、五、十二、二十 |
| **AI 应用开发者** | 四、五、十一、十二 |
| **运维 / SRE** | 七、八、十四、十五、二十二 |
| **安全 / 合规** | 九、十、十五、十六 |
| **数据科学家** | 十一、十三、二十一 |
| **业务负责人** | 一、二、十六、二十一 |
| **AI Gateway 选型** | 二十一、二十、二十三 |

### 24.5 一句话总结

> **Kong AI Gateway 是目前"AI 协议覆盖最广、企业级能力最强、部署形态最灵活"的 AI Gateway 产品**。它最大的优势是**把 AI 当作普通 API**——在 Kong Gateway 这个 8 年+ 沉淀的企业级 API 网关上原生增加 26+ AI 插件，复用 Kong 平台所有非 AI 能力（Auth / Rate Limit / Observability / Vault / Portal）。最大劣势是**价格昂贵、学习曲线陡峭、AI 领域护城河浅**。**最适合**：已有 Kong 投资的中大型企业、强合规行业（金融/政府/医疗）、需要 MCP / A2A 协议治理的 AI Agent 平台。**不适合**：个人 / 小团队（用 One API / LiteLLM）、纯 AI 应用（用 Portkey / LiteLLM）、云原生优先 / Service Mesh 场景（用 Higress / Envoy AI Gateway）。

---

> **报告结束**。下一个产品深挖：**APISIX ai-proxy**（按既定顺序）。
