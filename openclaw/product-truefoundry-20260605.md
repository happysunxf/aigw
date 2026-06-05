# TrueFoundry 深度调研 — 企业级 AI Gateway + Agent 部署平台

> 调研日期：2026-06-05（Asia/Shanghai）
> 版本：v1.0（基于公开资料 + 一手 GitHub / 官网 / llms.txt 抓取）
> 分类：Enterprise AI Gateway + Agent Platform（多产品矩阵）
> 协议：OpenAI-compatible / MCP / A2A / OpenTelemetry
> 部署：SaaS / VPC / On-Prem / Air-gapped / 公有云

---

## 0. TL;DR（60 秒读完）

TrueFoundry 是一家位于旧金山 + 班加罗尔的 **企业级 AI 基础设施公司**，在 2025 年完成 19M USD A 轮（Intel Capital 领投，Peak XV / Eniac / Jump 跟投），被 Gartner 2025《AI Gateway Market Guide》点名，被 Gartner 2026《优化 GenAI 成本十大最佳实践》收录，G2 评分 9.9/10。

它的核心产品矩阵由三块组成：

1. **AI Gateway** — 统一代理层，统一 1000+ LLM 的 OpenAI 兼容 API；内置 RBAC / 路由 / Fallback / 缓存 / Guardrails / 配额 / 预算 / OTel 观测；底层基于 **Hono 框架 + 零外部依赖 + NATS 配置同步**；性能数据：**1 vCPU/1GB RAM 跑 250–350 RPS，P95 延迟 3–4 ms**。
2. **MCP Gateway** — 集中式 Model Context Protocol 服务器注册表 + 联邦身份认证（OAuth 2.0 / Okta / Azure AD）+ Virtual MCP Server（把多个 MCP server 工具拼成一个 endpoint）+ RBAC on tools；预置 Slack / Confluence / Datadog / Sentry 等企业 MCP server。
3. **Agent Gateway** — 2026 年捐献给 **Linux Foundation** 的开源项目 [`agentgateway/agentgateway`](https://github.com/agentgateway/agentgateway)（Rust 编写，3.1k stars），同时支持 **MCP + A2A** 双协议，是 agent mesh 的 data plane。

附属开源产品：
- `cognita` (Python RAG 框架，4.4k stars)
- `llm-locust` (TypeScript LLM 压测工具，29 stars)
- `models` (YAML/CUE schema 的 19 家供应商 1000+ 模型注册表)
- `KubeElasti` / `CruiseKube`（Kubernetes scale-to-zero + 资源优化）
- `infra-charts` (Helm chart for 私有部署)

核心客户：**NVIDIA**（80% GPU 利用率提升）、Whatfix（35% 成本节约）、Innovaccer（5x 加速 / 50% 成本下降）、Adopt AI（15M+ req/月，40B+ tokens 集中路由）、Games24x7（200+ RPS, 1 亿用户）、Aviva、Wadhwani AI、Aviso AI、JanitorAI。

**差异化定位**：和 LiteLLM 走"开源多供应商 SDK + 自托管"路线不同，TrueFoundry 走的是 **"企业级 SaaS + 任意环境自部署（VPC/On-prem/Air-gapped）+ 完整 LLMOps 平台（gateway + 模型部署 + GPU 编排 + observability）+ 开源周边生态"** 的路线。它的对手不是 LiteLLM，而是 **Portkey 企业版 + 部分 Anyscale / BentoML / AWS SageMaker 的功能切片**。**短结论**：如果你需要的是一个"既能 SaaS 一键用、又能在自家 VPC 私有化部署、并且覆盖 LLM 路由 + MCP 工具联邦 + Agent 编排 + GPU 调度"的一站式平台，TrueFoundry 是当前市场上少有的端到端选择；如果你只需要 LLM 路由 + 缓存，LiteLLM / Portkey 开源版更轻量；如果你在云厂商生态深度绑定，AWS Bedrock / Azure AI Foundry 的自带 gateway 更省事。

---

## 1. 公司背景与发展轨迹

### 1.1 创始与定位

- **公司名**：TrueFoundry, Inc.
- **总部**：San Francisco, USA + Bangalore, India
- **创始人**：Aniket Tripathi（CEO，前 LinkedIn Staff Engineer） + 联合创始人团队（曾就职 LinkedIn、Microsoft、Google）
- **公司年龄**：成立于 2021 年（Medium 博客链接 `abhishekch09.medium.com/d8e159743a4b` 可追溯到早期愿景文档）

> 原文（来自 `truefoundry.com/blog/truefoundry`）：
> "Overall Vision: A developer platform that eases creation and management of services following all best practices and gives complete overall picture of infrastructure including monitoring of systems, data, cost and impact with initial focus on Machine Learning!"

最初的定位是 **"ML 平台 + Service PaaS"**（参考 Medium 早期文章），核心痛点是：

1. ML 平台各组件（训练 / Serving / Feature Store / 监控）拼装成本高，多角色协作（Data Engineer / DS / MLE / DevOps / PM）摩擦大。
2. Kubernetes 抽象太底层，Data Scientist 不想写 Helm chart。

### 1.2 关键里程碑

| 时间 | 事件 |
|---|---|
| 2021 | 创立，最初做 ML PaaS（ServiceFoundry） |
| 2022 | 上线 first model serving 产品（self-hosted） |
| 2023 | Games24x7、Whatfix 等客户落地；进入 LLM Gateway 赛道 |
| 2024 | AI Gateway 1.0 发布；进入 LLM Gateway 行业前列 |
| 2025 | **$19M Series A**，Intel Capital 领投；被 Gartner Market Guide for AI Gateways 收录；G2 评分 9.9 |
| 2025 H2 | 发布 MCP Gateway；与 NVIDIA 在 GPU 调度上深度合作 |
| 2026 Q1 | **agentgateway 项目捐献给 Linux Foundation**（这是报告里非常关键的信号 — 见 §2.3） |
| 2026 Q2 | 推出 "Agent Gateway" + "Tracing" 产品线；Gartner 10 Best Practices 收录 |

### 1.3 资本结构

- **A 轮**：$19M USD（2025 年）
- **领投**：Intel Capital
- **跟投**：Peak XV Partners（即 Sequoia India）、Eniac Ventures、Jump Capital
- **估值**：未公开（推测 A 轮 80–120M 区间）
- **客户数**：Fortune 500 横跨支付、半导体、电信、制药、医疗，包括 NVIDIA、Aviva、Cargill、Mavenir、Whatfix、Innovaccer、Games24x7、JanitorAI 等

### 1.4 行业认可

- **Gartner 2025 Market Guide for AI Gateways** — 被列为代表厂商
- **Gartner 2026 "10 Best Practices for Optimizing Generative & Agentic AI Costs"** — 引用其方法论
- **G2 评分 9.9/10**（"Best Results"、"Easiest to Use"、"Most Implementable" 多个细分榜单）
- 季度净新收入 2025 年 Q-over-Q 翻倍

---

## 2. 产品矩阵全景

TrueFoundry 的产品体系不是单一 AI Gateway，而是 **"AI Gateway + MCP Gateway + Agent Gateway + Deployment Platform + Observability"** 五件套：

### 2.1 产品矩阵图（ASCII）

```
                        ┌────────────────────────────────────────────┐
                        │       TrueFoundry 统一控制台 (Web UI)       │
                        │  Playground / Models / Logs / Tracing /... │
                        └──────────────────┬─────────────────────────┘
                                           │
            ┌──────────────────────────────┼──────────────────────────────┐
            │                              │                              │
            ▼                              ▼                              ▼
   ┌────────────────┐            ┌────────────────┐            ┌────────────────┐
   │  AI Gateway    │            │  MCP Gateway   │            │ Agent Gateway  │
   │  (LLM proxy)   │            │  (tools/MCP)   │            │  (A2A + MCP)   │
   │                │            │                │            │   (LF 项目)    │
   │  • LLM 路由    │            │  • 注册表      │            │  • agent mesh  │
   │  • Fallback    │            │  • OAuth 2.0   │            │  • 协议转换    │
   │  • 缓存/语义   │            │  • RBAC        │            │  • 安全/观测   │
   │  • Guardrails  │            │  • Virtual MCP │            │  • 会话感知    │
   │  • RBAC/Quota  │            │  • Pre-built   │            │                │
   └────────┬───────┘            └────────┬───────┘            └────────┬───────┘
            │                             │                             │
            ▼                             ▼                             ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │                 Control Plane (Postgres + ClickHouse + NATS)              │
   └──────────────────────────────────────────────────────────────────────────┘
            │
            ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  Deployment Platform — 模型 Serving / Jobs / Notebooks / Fine-tuning      │
   │  (vLLM / TGI / Triton 后端) + GPU 编排 (KubeElasti / CruiseKube)         │
   └──────────────────────────────────────────────────────────────────────────┘
            │
            ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  Observability (Tracing) — OTel-native → Grafana / Datadog / Prometheus   │
   └──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 AI Gateway — 核心产品

#### 2.2.1 架构设计（核心！）

下面是 TrueFoundry 官方博客披露的 AI Gateway 架构（`/blog/how-to-think-about-ai-gateway-architecture-in-the-generative-ai-stack`）：

```
                       ┌────────────────────────────────────────────┐
                       │         Control Plane (Region: US)         │
                       │                                            │
   ┌─────────┐         │  ┌──────────┐  ┌────────────┐  ┌────────┐  │
   │  Admin  │────────▶│  │  Web UI  │  │  Postgres  │  │ Backend│  │
   │ (User)  │ HTTPS   │  │  (Play-  │  │  (config)  │  │Service │  │
   └─────────┘         │  │  ground)│  │            │  │        │  │
                       │  └──────────┘  └────────────┘  └───┬────┘  │
                       │       │              │             │       │
                       │       │              │             │       │
                       │       │              ▼             │       │
                       │       │       ┌────────────┐       │       │
                       │       │       │ NATS Queue │◀──────┘       │
                       │       │       │ (config    │               │
                       │       │       │  sync bus) │               │
                       │       │       └──────┬─────┘               │
                       └───────┼──────────────┼─────────────────────┘
                               │              │
                  Config push  │              │  Config push
                               ▼              ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                Gateway Pods (Stateless, in-region)               │
   │                                                                  │
   │  ┌────────────────────────────────────────────────────────────┐  │
   │  │  Hono Framework (TypeScript, edge-optimized)                │  │
   │  │                                                            │  │
   │  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
   │  │  │ Auth/Authz  │  │ Rate Limit   │  │ Load Balancer   │  │  │
   │  │  │ (in-mem)    │  │ (in-mem)     │  │ (weight/lat/pri)│  │  │
   │  │  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘  │  │
   │  │         │                │                   │           │  │
   │  │         ▼                ▼                   ▼           │  │
   │  │  ┌─────────────────────────────────────────────────────┐  │  │
   │  │  │  In-Memory Decision Engine                          │  │  │
   │  │  │  (sub-millisecond, no I/O)                          │  │  │
   │  │  └─────────────────────┬───────────────────────────────┘  │  │
   │  │                        │                                  │  │
   │  │                        ▼                                  │  │
   │  │  ┌─────────────────────────────────────────────────────┐  │  │
   │  │  │  Upstream Call (OpenAI / Anthropic / Bedrock /...) │  │  │
   │  │  └─────────────────────┬───────────────────────────────┘  │  │
   │  │                        │                                  │  │
   │  │                        ▼ (async, non-blocking)             │  │
   │  │  ┌─────────────────────────────────────────────────────┐  │  │
   │  │  │  Async Logger ────▶ NATS ──▶ ClickHouse (logs/metrics)│  │  │
   │  │  └─────────────────────────────────────────────────────┘  │  │
   │  └────────────────────────────────────────────────────────────┘  │
   │                                                                  │
   │  资源占用：1 vCPU / 1GB RAM / ~250 RPS                             │
   └──────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
                  ┌─────────────────────────────────────┐
                  │  LLM Providers (Upstream)           │
                  │  OpenAI / Anthropic / Bedrock /     │
                  │  Gemini / vLLM / TGI / Triton /... │
                  └─────────────────────────────────────┘
```

#### 2.2.2 关键架构原则（官方明确列出）

> 来自 `truefoundry.com/blog/how-to-think-about-ai-gateway-architecture-in-the-generative-ai-stack`：

| 原则 | 实现细节 |
|---|---|
| **High Availability** | 即使 DB / Queue 故障，gateway 仍能继续服务（in-memory state） |
| **Low Latency** | 1 vCPU 下 P95 延迟 ~3–4 ms（TTFT 额外开销 <10ms） |
| **High Throughput** | 单 pod 350 RPS；水平扩展可达 tens of thousands RPS |
| **No External Calls in Hot Path** | 请求路径上零外部调用（除非开启 semantic cache） |
| **In-Memory Decision Making** | 认证 / 授权 / 限流 / 路由决策全部内存中执行 |
| **Separation of Control & Data Plane** | 控制面和代理面解耦，支持区域级故障隔离 |

#### 2.2.3 核心特性清单

- **统一 API 接入 1000+ LLM**：OpenAI、Anthropic、Google Gemini、AWS Bedrock、Azure OpenAI、Groq、Mistral、Cohere、自托管模型
- **多模型路由**：
  - Weight-based（按权重）
  - Latency-based（按实时延迟）
  - Priority-based（按优先级）
- **Fallback chain**：自动重试 + 跨供应商故障转移
- **RBAC**：用户 / 团队 / 模型 / 环境粒度
- **Rate limiting + Budget**：
  - 用户级 / 团队级 / 模型级 / 应用级 / 环境级
  - 超额可配置：throttle、downgrade 到便宜模型、block
- **Caching**：
  - Exact cache（精确匹配）
  - Semantic cache（语义匹配，节省 token）
- **Observability (OTel-native)**：
  - Token usage / Cost / Latency (P50/P90/P99) / Time-to-First-Token / Inter-token latency
  - Error rate / 模型路由 / Fallback 链 / Guardrail 决策全可追踪
- **Logging**：
  - Request + Response 完整记录
  - 元数据 tagging（user_id / team / customer / environment）
- **MCP Server 集成**：
  - 原生支持 MCP server 注册表 + OAuth 2.0
- **Agent Playground**：
  - 交互式 UI，可即时测试 LLM / Prompt / MCP tool
  - 自动生成 OpenAI client / LangChain 代码片段
- **Prompt Lifecycle Management**：
  - 版本化、变量、rollback、发布（Agent App）
- **Guardrails**：
  - 输入：PII / 提示词注入 / 禁用话题检测
  - 输出：toxicity / 偏见 / 幻觉 / 策略违规 / 数据泄露
  - 集成：OpenAI Moderation、AWS Bedrock Guardrails、Azure Content Safety、Azure PII detection
  - 支持 custom Python 规则
- **GitOps**：YAML 配置 + TrueFoundry CLI 声明式
- **部署模式**：SaaS / VPC / On-prem / Air-gapped

#### 2.2.4 性能基准（官方公布）

> 来自同一篇博客：

| 指标 | 数值 |
|---|---|
| 单 pod 吞吐量（1 vCPU / 1GB RAM） | **250 RPS**（官方数据） |
| 单 pod 饱和点 | **350 RPS**（CPU 饱和） |
| 水平扩展能力 | tens of thousands RPS（多 pod 跨区域） |
| 单请求额外延迟 | **~3 ms P95**（TTFT 额外 < 10ms） |
| 内存占用 | < 200 MB（TypeScript runtime） |
| 启动时间 | < 1s（stateless, 无外部依赖） |
| 高负载下 P99 抖动 | 几乎无（多限流/路由规则下不增加延迟） |

> 对比 LiteLLM 官方定位（TrueFoundry 营销文）："TrueFoundry AI Gateway delivers ~3-4 ms latency, handles 350+ RPS on 1 vCPU, scales horizontally with ease, and is production-ready, while LiteLLM suffers from high latency, struggles beyond moderate RPS, lacks built-in scaling, and is best for light or prototype workloads." —— 这是厂方说法，客观上看 LiteLLM 在我们的调研中确实没有公布类似 RPS 基准，所以单看 TrueFoundry 数据，需要在自己的 workload 下复测。

### 2.3 Agent Gateway — 开源捐献 Linux Foundation

#### 2.3.1 关键事实

- **项目名**：`agentgateway`
- **GitHub**：`github.com/agentgateway/agentgateway`
- **组织**：独立的 GitHub 组织（不是 TrueFoundry org 下）
- **许可**：Apache-2.0
- **语言**：**Rust**（性能优先）
- **Stars**：3.1k（2026-06 调研时）
- **Forks**：511
- **状态**：Active development
- **治理**：Linux Foundation 项目（来自 `truefoundry.com/agent-gateway` 原文："The agent gateway project is a Linux Foundation Project"）

> 注：截至 2026-06-05，我们没能在 `linuxfoundation.org/projects/agentgateway` 找到正式项目页（404），可能仍在 incubator 阶段或刚提交。但 GitHub Organization 已经是独立的——这通常意味着治理权已经从 TrueFoundry 转移到中立基金会。

#### 2.3.2 核心能力

- **LLM Gateway** — 通过统一 OpenAI-compatible API 路由到 OpenAI / Anthropic / Gemini / Bedrock 等；带预算 / 限流 / Prompt 增强 / 负载均衡 / Fallback
- **MCP Gateway** — 联邦多个 MCP server；支持 stdio / HTTP / SSE / Streamable HTTP 传输；OpenAPI → MCP server 转换；OAuth 认证
- **A2A Gateway** — agent-to-agent 通信（基于 Google A2A 协议）；capability discovery / modality negotiation / task collaboration
- **Inference Routing** — 智能路由到自托管模型，使用 Kubernetes Inference Gateway 扩展，决策依据 GPU 利用率 / KV cache / LoRA 适配器 / 队列深度
- **Guardrails** — 多层内容过滤：regex、OpenAI Moderation、AWS Bedrock Guardrails、Google Model Armor、自定义 webhook
- **Security & Observability** — JWT / API key / OAuth 认证；CEL 策略引擎的细粒度 RBAC；限流；TLS；OpenTelemetry 指标 / 日志 / 追踪

#### 2.3.3 部署模式

- **Standalone**：本地 / 单机部署（`agentgateway.dev/docs/quickstart`）
- **Kubernetes**：通过内置 controller + Gateway API（`agentgateway.dev/docs/kubernetes/latest`）
- **Built-in UI**：自带 dashboard 可探索 agent-to-agent / agent-to-tool 连接

#### 2.3.4 战略意义

把 Agent Gateway 独立 + 捐给 Linux Foundation 是一个非常聪明的策略：

1. **建立行业标准**：让 agent mesh 协议被广泛接受 → TrueFoundry 控制平面 + 商业版的差异化护城河更厚
2. **避免厂商锁定担忧**：企业敢用，因为核心是开源 + 中立治理
3. **扩大开发者社区**：Rust 性能 + 协议中立会吸引更多贡献者
4. **与 MCP / A2A 生态深度绑定**：TrueFoundry 是 MCP 协议的早期重度玩家，A2A 协议（Google 主推）也第一时间支持

### 2.4 MCP Gateway（商业版）

> 注意：MCP Gateway 商业版是 TrueFoundry 控制台里的产品，和开源 `agentgateway/agentgateway` 的 MCP 模块是关联但不同的产品线。商业版提供企业级：注册表 UI、Virtual MCP Server、跨 region 高可用、合规审计。

核心特性：
- **集中式 MCP server 注册表**
- **OAuth 2.0 联邦身份** — 一 user 一 token，跨所有 MCP server 自动 refresh
- **Virtual MCP Server** — 把多个 MCP server 的工具子集拼成单一 endpoint
- **预置 MCP server**：Slack、Confluence、Sentry、Datadog
- **OpenAPI → MCP server 转换**：自动包装现有 REST API
- **MCP Guardrails**：pre-call / post-call 策略执行
- **请求级追踪 + 审计日志**
- **多框架兼容**：LangChain / LangGraph / CrewAI / AutoGen

### 2.5 Deployment Platform

> 这块不在 AI Gateway 范畴内，但属于 TrueFoundry 整体拼图，简要说明。

- **模型 Serving**：vLLM / TGI / Triton 后端
- **Jobs**：定时任务、event-driven
- **Notebooks**：Jupyter 集成
- **Fine-tuning**：launch job on your data, track experiments
- **GPU 编排**：
  - KubeElasti：scale-to-zero with zero traffic loss
  - CruiseKube：智能 Kubernetes 资源优化（right-sizing）
  - MIG / time-slicing 支持
- **CI/CD**：GitOps + YAML 声明式
- **ML Repository**：模型 / artifact / prompt 版本化

### 2.6 Observability (Tracing)

- **Framework-agnostic 追踪** — prompt → tool → model 完整链路
- **OpenTelemetry 兼容** → Grafana / Datadog / Prometheus / 内部 observability stack
- **GPU / CPU / Cluster 监控** — 包括 GPU memory、节点健康、扩缩容行为
- **告警** — latency / throughput / token usage / cost / GPU utilization

---

## 3. 协议支持

### 3.1 LLM 协议

| 协议 | 支持情况 | 备注 |
|---|---|---|
| **OpenAI Chat Completions API** | ✅ 完全兼容 | 主推端点（统一） |
| **OpenAI Responses API** | ✅ 兼容 | 通过 OpenAI 适配 |
| **Anthropic Messages API** | ✅ 通过适配层 | Anthropic → OpenAI 协议转换 |
| **Google Gemini API** | ✅ 通过适配层 | Gemini → OpenAI 协议转换 |
| **AWS Bedrock InvokeModel** | ✅ 通过适配层 | Bedrock → OpenAI 协议转换 |
| **Azure OpenAI** | ✅ 原生支持 | API 风格一致 |
| **Cohere Rerank** | ✅ 支持 | 独立端点 |
| **Embeddings API** | ✅ OpenAI 兼容 | 跨 provider |
| **Image generation (DALL-E / SD)** | ✅ 支持 | 通过 chat mode 标识 |
| **TTS (ElevenLabs / OpenAI)** | ✅ 支持 | model mode = text_to_speech |
| **STT (Deepgram)** | ✅ 支持 |  |
| **SSE (Server-Sent Events)** | ✅ 流式响应 |  |
| **WebSocket** | ✅ 部分场景 | 实时双向 |

### 3.2 Agent / Tool 协议

| 协议 | 支持情况 | 备注 |
|---|---|---|
| **MCP (Model Context Protocol)** | ✅ 深度支持 | MCP Gateway + Agent Gateway 都支持 |
| **A2A (Agent-to-Agent)** | ✅ 支持 | 通过 agentgateway 项目 |
| **stdio / HTTP / SSE / Streamable HTTP** | ✅ MCP 多种传输 |  |
| **OpenAPI → MCP 转换** | ✅ 自动包装 REST API |  |

### 3.3 Observability 协议

| 协议 | 支持情况 |
|---|---|
| **OpenTelemetry (OTel)** | ✅ 原生 — metrics / logs / traces |
| **Prometheus remote write** | ✅ |
| **StatsD / DogStatsD** | ✅ 间接通过 OTel collector |
| **Grafana / Datadog** | ✅ 通过 OTel exporter |

### 3.4 认证协议

| 协议 | 支持情况 |
|---|---|
| **API Key (静态)** | ✅ |
| **OAuth 2.0** | ✅ 联邦 + Token refresh |
| **JWT** | ✅ |
| **SSO (SAML / OIDC)** | ✅ Okta / Azure AD / 自定义 |
| **Personal Access Token (PAT)** | ✅ |
| **System Token** | ✅ 跨服务调用 |
| **Audit logging** | ✅ 不可篡改 |

---

## 4. 模型与生态

### 4.1 官方 models 注册表（开源）

`github.com/truefoundry/models` 是一个 **MIT 协议、社区维护的 19+ provider 1000+ 模型的 YAML 注册表**：

| Provider | 模型数 | 备注 |
|---|---|---|
| **OpenRouter** | 769 | 开源模型统一 API |
| **Google Vertex AI** | 403 | Gemini, PaLM |
| **Together AI** | 338 | 开源模型托管 |
| **AWS Bedrock** | 208 | Claude / Llama / Titan / Mistral |
| **DeepInfra** | 201 | 开源模型托管 |
| **Azure OpenAI** | 189 | OpenAI on Azure |
| **Deepgram** | 143 | STT / TTS |
| **OpenAI** | 141 | GPT-4 / GPT-4o / GPT-5 / o1 / o3 / DALL-E / Whisper / TTS |
| **xAI** | 86 | Grok |
| **Mistral AI** | 85 | Mistral / Mixtral / Codestral |
| **Google Gemini** | 70 | Gemini Pro / Ultra / Flash |
| **Azure AI Foundry** | 68 | Azure AI 模型 |
| **Cohere** | 37 | Command / Embed |
| **Databricks** | 31 |  |
| **SambaNova** | 30 | 企业 AI |
| **Anthropic** | 24 | Claude 3 / 3.5 / 4 |
| **Perplexity** | 24 | 搜索增强 |
| **Groq** | 22 | 快速推理 |
| **AI21** | 12 | Jamba |
| **ElevenLabs** | 10 | 语音 |
| **Cerebras** | 5 | 快速推理 |

**schema 关键字段**（YAML + CUE 校验）：

```yaml
# 必需
model: gpt-5.4-mini-2026-03-17
mode: chat  # chat / embedding / image / text_to_speech

# 定价 — 数组格式（支持 region 维度）
costs:
  - region: "*"  # "*" = 全局
    input_cost_per_token: 7.5e-7
    output_cost_per_token: 0.0000045
    cache_read_input_token_cost: 7.5e-8

# 上下文窗口
limits:
  context_window: 400000
  max_output_tokens: 128000

# 特性
features: [function_calling, prompt_caching, structured_output, system_messages]

# 模态
modalities:
  input: [text, image]
  output: [text]

# 推理 / thinking
thinking: true

# 来源
sources:
  - https://developers.openai.com/api/docs/pricing
```

**目录结构**：

```
models/
├── providers/
│   ├── <provider>/
│   │   ├── default.yaml
│   │   ├── <model>.yaml
│   │   └── ...
└── ...
```

### 4.2 自托管推理后端支持

| 后端 | 状态 | 用途 |
|---|---|---|
| **vLLM** | ✅ 深度集成 | LLM 推理首选 |
| **TGI (Text Generation Inference)** | ✅ 支持 | HuggingFace 推理 |
| **Triton Inference Server** | ✅ 支持 | NVIDIA 多框架推理 |
| **LMDeploy** | ⚠️ 间接 | 通过 custom deployment |
| **SGLang** | ⚠️ 间接 | 通过 custom deployment |
| **llama.cpp** | ⚠️ 间接 | 通过 custom container |

### 4.3 Guardrail 集成

| 提供商 | 集成方式 |
|---|---|
| **OpenAI Moderation** | 内置 |
| **AWS Bedrock Guardrails** | 内置 |
| **Azure Content Safety** | 内置 |
| **Azure PII Detection** | 内置 |
| **Google Model Armor** | 通过 agentgateway |
| **Regex 自定义** | 通过配置 |
| **Custom Webhook** | 通过 agentgateway |
| **Custom Python** | 通过 `integrations-custom-guardrails` 仓库 |

---

## 5. 性能与基准

### 5.1 AI Gateway 数据平面性能

| 指标 | 数值 | 备注 |
|---|---|---|
| 1 vCPU / 1GB RAM 吞吐量 | **250 RPS** | 持续 |
| 1 vCPU / 1GB RAM 饱和点 | **350 RPS** | CPU-bound |
| 水平扩展上限 | tens of thousands RPS | 多 pod 跨 region |
| 单请求额外延迟 (TTFT) | **3–4 ms P95** | < 10ms hard cap |
| 内存占用 | < 200 MB | TypeScript runtime |
| 启动时间 | < 1s |  |
| 高并发下 P99 抖动 | 几乎无 | 多限流/路由规则下不增延迟 |

### 5.2 性能 vs 竞品（TrueFoundry 自家数据，需独立复测）

| Gateway | 1 vCPU 吞吐量 | 额外延迟 | 备注 |
|---|---|---|---|
| **TrueFoundry AI Gateway** | 250–350 RPS | 3–4 ms | 官方数据 |
| **LiteLLM Proxy (Python)** | 50–150 RPS（社区 benchmark） | 10–50 ms | 单进程，asyncio |
| **Portkey Gateway (Node.js)** | 200–300 RPS | 5–15 ms | 社区 benchmark |
| **One API (Go)** | 500–1000 RPS | < 5 ms | 性能最强但功能弱 |
| **Higress (Envoy + Go plugin)** | 1000+ RPS | < 1 ms | 高性能 API gateway |
| **Kong AI Gateway** | 200–500 RPS | 5–10 ms | 商业版 |

> 提示：上述对比除 TrueFoundry 官方外，其他数据来自社区散落 benchmark，可能不严谨。在你的工作负载下做压测（建议用 `llm-locust`）再下结论。

### 5.3 存储与分析层

| 组件 | 用途 | 性能 |
|---|---|---|
| **Postgres** | 配置 + 元数据 | 标准 RDBMS |
| **ClickHouse** | 日志 + metrics + 用量分析 | 列存，10x+ 写入性能 |
| **NATS** | 配置同步总线 | 实时推送，sub-ms 延迟 |

### 5.4 Benchmark 工具：LLM Locust

`github.com/truefoundry/llm-locust`（TypeScript，29 stars）是基于 Locust 的 LLM 压测工具：

- 核心文件：`api.py`, `clients.py`, `metrics.py`, `metrics_collector.py`, `prompt.py`, `user.py`, `user_spawner.py`, `utils.py`
- WebUI：`webui/` 目录
- 特性：支持 SSE streaming metrics、TTFT 测量、token-level 监控、inter-token latency

---

## 6. 部署方式

### 6.1 部署模式矩阵

| 模式 | 适用场景 | 数据驻留 | 部署时长 | 起步成本 |
|---|---|---|---|---|
| **SaaS**（`*.truefoundry.cloud`） | 快速开始 | TrueFoundry 基础设施 | 10 min | $0 (Developer) |
| **VPC-hosted** | 多数企业 | 客户云账号内 | 1–3 天 | 包含在 Enterprise |
| **On-premise** | 高度合规 | 客户数据中心 | 1–2 周 | Custom |
| **Air-gapped** | 国防、医疗、政府 | 完全隔离 | 2–4 周 | Custom |
| **多云 / 跨 region** | 全球化 | 多 region | 2–4 周 | Custom |

### 6.2 部署架构选择（官方说明）

> 来自 `truefoundry.com/pricing` FAQ：

```
1. AI Gateway SaaS only                              → 最快，最低成本
2. SaaS AI Gateway + your own storage               → 控制面 SaaS，数据自托管
3. Gateway Plane only                                → 自托管数据面
4. Control Plane + Gateway Plane                     → 完全自托管
```

### 6.3 私有化部署组件

Helm charts (`github.com/truefoundry/infra-charts`)：
- AI Gateway 组件（Hono-based gateway pods）
- MCP Gateway 组件
- Agent Gateway 组件（agentgateway Helm chart）
- 控制面：Postgres + ClickHouse + NATS
- 监控：OTel collector + Prometheus / Grafana

Terraform provider：`github.com/truefoundry/terraform-kubernetes-truefoundry-helm`（Apache-2.0）

### 6.4 部署规模参考

> 来自客户案例：

- **Games24x7**：200+ RPS, 1 亿用户
- **Adopt AI**：15M+ req/月，40B+ input tokens 集中路由
- **Innovaccer**：PHI 重负载下，5x faster 平台交付
- **Whatfix**：80% 缩短模型上线时间

---

## 7. 成本模型

### 7.1 定价方案（2026 年最新）

| 套餐 | 价格 | 请求数/月 | 用户数 | 关键能力 |
|---|---|---|---|---|
| **Developer** | **$0** | 50k | 3 | Universal API、RBAC、虚拟模型、Playground、weight 路由、fallback、Guardrails 集成 |
| **Pro** | **$499**/月 | 1M | 10 | 全部 + semantic cache、latency/priority 路由、budget 限流、observability、5 个 MCP server |
| **Pro Plus** | **$2,999**/月 | 1M | 25 | 全部 + advanced auth、self-hosted MCPs、self-hosted 部署、25 个 MCP server、5M tool calls |
| **Enterprise** | **Custom** | 10M+ | Custom | 全部 + air-gapped、custom SLA、multi-region、audit log、SSO/SOC2/HIPAA/ITAR |

### 7.2 关键计费规则

- **Pro 套餐超出**：每 2M 请求 + 5 个 API key 增加 $499
- **Pro Plus 超出**：联系销售
- **自托管**：仅 SaaS AI Gateway 零托管费；自托管 Control + Gateway Plane 大约 $600–$1,000/月（云资源成本）
- **数据导出**：可导出到客户自有 S3/GCS/Azure Blob（数据湖导出功能）
- **计费依据**：使用量（请求数）+ 用户数 + 深度（AI Gateway / MCP Gateway / Agent Gateway 启用情况）

### 7.3 隐藏成本注意

- 私有化部署需要 Kubernetes 集群（≥3 节点）+ Postgres + ClickHouse + NATS 的运维成本
- 大量语义缓存的 vector DB 成本（如果开 semantic cache）
- 自定义 Guardrail / MCP server 开发的工程成本

### 7.4 ROI 案例（官方公布）

- **Whatfix**：35% 云成本节约（vs AWS SageMaker）
- **Innovaccer**：50% 云成本下降
- **Wadhwani AI**：50% 成本节约，10x 扩展能力
- **Neurobit**：60% 云成本节约
- **NVIDIA**：80% GPU 利用率提升，节省 idle compute 成本"以百万美元计"

---

## 8. 客户案例与生态

### 8.1 主要客户

| 客户 | 行业 | 关键数据 | 案例链接 |
|---|---|---|---|
| **NVIDIA** | 半导体 | 80% GPU 利用率提升，节省 idle compute 百万级 | `case-studies` |
| **Innovaccer** | 医疗（PHI） | 5x 内部 AI 平台交付加速，50% 云成本下降 | `case-studies` |
| **Aviva Credito** | 金融 | 多云 LLM 集中管控 + 成本可见性 | `case-studies` |
| **Fortune 50 Healthcare** | 医疗 | 1 年内 30+ LLM use case 上线 | `case-studies` |
| **Adopt AI** | 企业 Agent | 15M+ req/月，40B+ input tokens 集中路由 | `case-studies` |
| **Whatfix** | 数字采纳 | 80% 缩短上线时间，35% 云成本节约 | `case-studies` |
| **Games24x7** | 游戏 | 200+ RPS，1 亿用户，10x 规模 | `case-studies` |
| **Wadhwani AI** | 教育/公益 | 50% 成本节约，10x 扩展，百万学生 | `case-studies` |
| **Aviso AI** | 销售 | 自研 LLM（MIKI）部署，GenAI ready | `case-studies` |
| **Neurobit** | 健康 | 60% 云成本节约，睡眠数据分析 | `case-studies` |
| **Online Drug Marketplace** | 医药电商 | 8M+ 月活，增收 $1.5M | `case-studies` |

### 8.2 社区引用

> **Vibhas Gejji**（Staff ML Engineer，引用 `truefoundry.com/pricing`）：
> "TrueFoundry's AI Gateway gave us a unified layer to manage model access, routing, guardrails, and cost controls across teams. It has accelerated productionization, increased visibility into spend and performance, and enabled us to scale AI experimentation safely across the organization."

> **Indroneel G.**（Intelligent Process Leader）：
> "With TrueFoundry's AI Gateway, we finally have one consistent interface for all model providers, policies, and telemetry. It eliminated the overhead of managing keys, routing logic, and scattered observability."

> **Nilav Ghosh**（Senior Director, AI）：
> "TrueFoundry's AI Gateway standardized how every team interacts with LLMs, embeddings, and RAG components. Instead of scattered integrations, we now control access, routing policies, and safety guardrails centrally."

### 8.3 开源生态

| 仓库 | Stars | 用途 |
|---|---|---|
| `agentgateway/agentgateway` | 3.1k | Rust 写的 agent mesh proxy（LF 项目） |
| `truefoundry/cognita` | 4.4k | RAG 框架（Python） |
| `truefoundry/models` | 10 | 19 provider 1000+ 模型 YAML 注册表 |
| `truefoundry/llm-locust` | 29 | LLM 压测工具（TypeScript） |
| `truefoundry/KubeElasti` | - | K8s scale-to-zero |
| `truefoundry/CruiseKube` | 69 | K8s 资源优化 |
| `truefoundry/infra-charts` | 5 | Helm charts |
| `truefoundry/terraform-kubernetes-truefoundry-helm` | 0 | Terraform |
| `truefoundry/mcp-servers` | 2 | MCP server 示例 |
| `truefoundry/mcp-servers-api` | 0 | MCP server API SDK |
| `truefoundry/tfy-mcp-server-deployment-example` | 1 | MCP 部署示例 |
| `truefoundry/integrations-custom-guardrails` | 0 | Custom Guardrail 集成示例 |
| `truefoundry/truefoundry-python-sdk` | 0 | Python SDK |
| `truefoundry/truefoundry-typescript-sdk` | - | TypeScript SDK |

### 8.4 商业生态

- **AWS Partner** — 集成 Bedrock
- **Azure Partner** — 集成 Azure OpenAI
- **GCP Partner** — 集成 Vertex AI
- **NVIDIA Inception** — 合作优化 GPU 利用率
- **Intel Capital** — 投资方 + 战略合作

---

## 9. 安全与合规

### 9.1 认证标准

| 标准 | 状态 |
|---|---|
| **SOC 2 Type II** | ✅ 持有 |
| **HIPAA** | ✅ 部署就绪 + 证书 |
| **GDPR** | ✅ 部署就绪 + 证书 |
| **ITAR** | ✅ 部署就绪 + 证书（企业版） |
| **ISO 27001** | ⚠️ 未明确公布 |
| **FedRAMP** | ⚠️ 未明确公布 |

### 9.2 安全特性

- **RBAC** — 用户 / 团队 / 模型 / 应用 / 环境多维度
- **SSO** — Okta / Azure AD / 自定义 OIDC
- **审计日志** — 不可篡改（immutable），包含 model usage / user access / config changes
- **数据驻留** — 可选 EU / US / APAC region；VPC 部署零数据出域
- **加密** — TLS 1.3 in transit；AES-256 at rest
- **PII 处理** — 输入/输出 guardrail 自动 mask / redact
- **提示词注入防护** — 内置检测 + 自定义 webhook
- **限流 / 配额** — 防止滥用
- **预算告警** — 超额前提前告警
- **Token rotation** — 实时 rotate / revoke 不影响服务

### 9.3 合规场景

- **医疗 PHI**（Innovaccer 案例）
- **金融合规**（Aviva，AML agentic）
- **政府 / 国防**（ITAR + air-gapped）
- **跨 region 数据驻留**（GDPR）
- **支付**（Fortune 500 支付公司）

---

## 10. 优劣势分析

### 10.1 优势（Strengths）

| 维度 | 优势 |
|---|---|
| **架构** | 基于 Hono + 零外部依赖 + 内存决策，P95 3–4ms 是第一梯队 |
| **多产品** | AI Gateway + MCP Gateway + Agent Gateway + Deployment + Tracing 统一控制台，竞品少见 |
| **Agent 协议** | 第一个同时支持 MCP + A2A + Kubernetes Inference Gateway 的产品 |
| **开源** | `agentgateway` 捐给 LF、`cognita` 4.4k stars、`models` 注册表 |
| **部署灵活性** | SaaS / VPC / On-prem / Air-gapped 全部支持 |
| **合规** | SOC 2 / HIPAA / GDPR / ITAR 完整 |
| **性能** | 1 vCPU 350 RPS，单 pod 资源占用低 |
| **客户** | NVIDIA / Whatfix / Innovaccer / Games24x7 / Aviva 质量高 |
| **资本** | Intel Capital + Peak XV + Eniac，财务健康 |
| **行业认可** | Gartner 收录 + G2 9.9/10 |
| **自托管推理** | vLLM / TGI / Triton 原生集成，GPU 编排工具完善（KubeElasti / CruiseKube） |
| **GitOps** | YAML 声明式 + CLI，DevOps 友好 |
| **模型覆盖** | 1000+ LLM（含 OpenRouter 769 个），统一 API |
| **Fintune 集成** | 训练 → serving 一条龙 |

### 10.2 劣势（Weaknesses）

| 维度 | 劣势 |
|---|---|
| **核心网关不开源** | AI Gateway 商业版不开源（agentgateway 是数据面，但控制面是 SaaS），和 Portkey / LiteLLM 路线相反 |
| **价格** | $499/月起对个人开发者门槛较高，Pro Plus $2999/月 vs LiteLLM（免费自托管）差距明显 |
| **vendor lock-in 风险** | Agent Apps、Prompt Management、Playground 等都绑在控制面 |
| **新人 / 文档** | 相对 LiteLLM / Portkey 社区，开发者社区小，docs 偏 marketing-style |
| **复杂栈** | 5 个产品（AI Gateway / MCP / Agent / Deployment / Tracing）选型需要时间消化 |
| **第三方 benchmark 缺** | 性能数据基本只来自 TrueFoundry 自家 |
| **Rust 工具链** | agentgateway 是 Rust，二次开发门槛高于 Python / Go |
| **缺少某些竞品特性** | 比如缺少 LiteLLM 的 `completion()` 统一方法层、缺少 Helicone 的开源观测、缺少 LangSmith 的 deep agent trace 视图（虽然有自己的 Tracing） |
| **早期项目** | 2021 年成立，相对 Anyscale / BentoML / Databricks 还年轻 |
| **学习曲线** | 概念多：Virtual MCP Server、Virtual Model、Agent App、Route 策略，初学者易混淆 |
| **GitHub 活跃度** | 主仓 star 较少（除 agentgateway 3.1k + cognita 4.4k 外），开源存在感不如 Portkey / LiteLLM |

### 10.3 风险（Risks）

1. **AI Gateway 闭源** — 迁移到 TrueFoundry 意味数据 + 配置都在它控制面，退出成本高
2. **agentgateway LF 治理成熟度** — LF 治理文档 / 委员会 / 投票流程细节尚未公开
3. **竞争激烈** — LiteLLM / Portkey / Kong / Higress / Cloudflare / AWS / Azure / GCP 都在加 AI Gateway 功能
4. **价格压力** — 开源替代品成熟后，企业可能回退到 LiteLLM 自托管 + 自建观测
5. **区域可用性** — 中国大陆 / 部分主权国家需要确认合规与数据驻留

---

## 11. 与其他产品对比

### 11.1 关键产品对比矩阵

| 维度 | TrueFoundry | LiteLLM | Portkey | One API | Higress | Kong AI Gateway | Cloudflare AI Gateway | Envoy AI Gateway |
|---|---|---|---|---|---|---|---|---|
| **核心定位** | 企业级 AI/MCP/Agent 网关 + 部署平台 | 开源多供应商 SDK + Proxy | AI Gateway + Observability | 开源多供应商 Proxy | API Gateway + AI plugin | API Gateway + AI plugin | 边缘 AI Gateway | Service Mesh + AI |
| **开源** | ❌（数据面 agentgateway 开源） | ✅ MIT（核心） | ✅ MIT（核心） | ✅ MIT | ✅ Apache-2.0 | ⚠️ 部分 | ❌ 商业 | ✅ Apache-2.0 |
| **部署模式** | SaaS/VPC/On-prem/Air-gapped | 自托管 | SaaS + 自托管 | 自托管 | 自托管 | SaaS + 自托管 | SaaS | 自托管 |
| **核心语言** | TypeScript (Hono) + Rust (agentgateway) | Python | Node.js / TypeScript | Go | Go | Lua / Go | Workers (Rust) | Go |
| **性能 (1 vCPU)** | 250–350 RPS, 3–4ms | 50–150 RPS, 10–50ms | 200–300 RPS, 5–15ms | 500–1000 RPS, <5ms | 1000+ RPS, <1ms | 200–500 RPS, 5–10ms | 边缘性能优秀 | 1000+ RPS, <1ms |
| **MCP 支持** | ✅ 深度 | ⚠️ 基础 | ⚠️ 基础 | ❌ | ⚠️ 基础 | ⚠️ 基础 | ❌ | ❌ |
| **A2A 支持** | ✅（agentgateway） | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Virtual MCP Server** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Guardrails 集成** | ✅ 多家 | ⚠️ 基础 | ✅ | ❌ | ⚠️ | ✅ | ✅ | ❌ |
| **语义缓存** | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Fallback 链** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **RBAC 细粒度** | ✅✅ 团队/模型/应用 | ⚠️ 基础 | ✅ 团队 | ⚠️ 基础 | ✅ | ✅✅ | ✅ | ⚠️ |
| **Budget 限流** | ✅✅ 多维度 | ⚠️ token 限流 | ✅ | ⚠️ | ✅ | ✅ | ✅ | ⚠️ |
| **Semantic Routing** | ✅ | ⚠️ | ✅ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ |
| **Prompt 管理** | ✅ 版本化 | ⚠️ 基础 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Tracing / OTel** | ✅✅ | ⚠️ | ✅✅ | ❌ | ✅ | ✅ | ✅ | ✅✅ |
| **Playground UI** | ✅ | ✅ | ✅ | ❌ | ❌ | ⚠️ | ❌ | ❌ |
| **自托管推理** | ✅ vLLM/TGI/Triton | ❌ | ⚠️ 间接 | ❌ | ⚠️ | ⚠️ | ❌ | ✅ |
| **GPU 编排** | ✅✅ KubeElasti/CruiseKube | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ |
| **Fine-tuning** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Air-gapped** | ✅ | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ❌ | ✅ |
| **企业 SLA** | ✅✅ | ⚠️ 社区版无 | ✅ | ❌ | ⚠️ | ✅ | ✅ | ⚠️ |
| **SOC 2 / HIPAA** | ✅✅ | ⚠️ 自托管责任 | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ |
| **价格起步** | $499/月（Pro） | 免费（自托管） | $0 + 用量 | 免费（自托管） | 免费（自托管） | $0（OSS）/ 商业版 contact | $5/月+ 用量 | 免费（自托管） |
| **GitHub Stars** | 数据面 3.1k (agentgateway) | 24k+ | 6k+ | 22k+ | 5k+ | 40k+ (Kong) | - | 2.5k+ |
| **客户亮点** | NVIDIA、Innovaccer | 三星、Discord | 全美 50 强 | 个人 / 中小企业 | 阿里 | 摩根大通、Sony | Cloudflare 全平台 | Tetrate、Cisco |

### 11.2 选型建议

**选 TrueFoundry 的场景：**
- 企业级合规要求（SOC 2 / HIPAA / GDPR / ITAR）
- 需要 SaaS 一键开箱 + 私有化双模
- 同时使用 LLM + MCP + Agent 多种协议
- 想要一个供应商覆盖 AI Gateway + 模型部署 + GPU 编排
- 想要 agent mesh 协议（agentgateway）的早期生态
- 团队对 Rust / TypeScript 技术栈接受度高

**不选 TrueFoundry 的场景：**
- 预算敏感 / 个人开发者（→ LiteLLM 自托管）
- 已经有 Kong / Higress / Envoy 等成熟 API gateway（→ 加 AI plugin）
- 单一云厂商深度绑定（→ 用厂商自带 gateway，如 Azure APIM + Azure OpenAI）
- 需要完全开源控制面（→ Portkey + 自建观测）
- 中国大陆企业（→ 推荐 Higress / One API）
- 已经在用 Datadog / New Relic 等全栈观测（→ 用 Portkey / Helicone + 现有观测栈）

### 11.3 不同竞品的独特优势

- **LiteLLM** — 100+ provider 兼容，Python SDK 友好，community 巨大，最适合快速集成
- **Portkey** — observability + prompt management 业界领先，UI 美观
- **One API** — 性能 + Go 单二进制，部署最简单
- **Higress** — 阿里系云原生 + AI plugin，国内最佳
- **Kong AI Gateway** — 现有 Kong 客户最平滑，强大的 plugin 生态
- **Cloudflare Workers AI** — 边缘部署 + 全球 CDN，最适合 latency-critical
- **Envoy AI Gateway** — service mesh + Kubernetes 集成最自然

---

## 12. 关键发现与战略洞察

### 12.1 三个最值得关注的发现

#### 12.1.1 把 agent gateway 捐给 Linux Foundation 是一个深远的布局

TrueFoundry 不是单纯"卖 AI Gateway 软件"，它在 **定义下一代的 agent mesh 协议**。agentgateway 项目（Rust, 3.1k stars, LF 治理）的核心价值不在于"开源一个网关"，而在于：

1. **MCP + A2A 协议的事实标准争夺** — 当 agent 通信协议还没有"TCP/IP"级别的标准时，谁先建中立开源项目 + LF 治理，谁就握有未来 5 年的话语权
2. **Kubernetes Inference Gateway 扩展** — 集成 K8s 生态，把 GPU 调度、KV cache、LoRA 适配器决策纳入 gateway 决策因素，这是真正工程化"AI-native proxy"
3. **企业级差异化** — 数据面免费开源 + 控制面商业版是经典的 "open core" 模式（MongoDB、Elastic、Confluent 都走过这条路径）

#### 12.1.2 "三件套 + LF 项目"的产品矩阵是显著差异化

| 产品 | 对手 | 差异 |
|---|---|---|
| AI Gateway | LiteLLM / Portkey / Kong | 性能 + 部署灵活性 + 企业合规 |
| MCP Gateway | 几乎没有直接竞品 | OAuth 联邦 + Virtual MCP + 预置 server |
| Agent Gateway | agentgateway（开源中立）| Rust 性能 + A2A + K8s Inference |
| Deployment | BentoML / Anyscale | KubeElasti + CruiseKube + Fine-tuning |
| Tracing | LangSmith / Helicone | OTel-native + GPU-aware |

一个 vendor 覆盖 5 层 + 1 个 LF 项目，竞品中只有 Databricks（覆盖全栈但贵且云绑定）和 Anyscale（部分覆盖）接近。

#### 12.1.3 客户质量与场景深度

不像很多 AI Gateway 厂商只有"几个 startup 用用"的客户，TrueFoundry 的客户：
- **NVIDIA**（半导体龙头，用它的 GPU 调度）
- **Innovaccer**（医疗 PHI 重负载）
- **Aviva**（金融合规 + 跨云）
- **Whatfix**（SaaS 龙头的生产部署）
- **Games24x7**（200 RPS + 1 亿用户）
- **Fortune 50 医疗**（30+ LLM use case 一年）

这些客户的痛点都集中在 **合规 + 多供应商 + 私有部署 + 大量 GPU 调度**——恰好是 TrueFoundry 强项。这不是偶然。

### 12.2 风险与机会

**机会**：
- 2026-2028 年 agent mesh 协议标准化窗口期 — 谁先 LF，谁定义标准
- 中国 / 印度 / 欧洲数据驻留需求增长 — VPC / On-prem / Air-gapped 部署灵活
- MCP 协议继续主流化（Anthropic 主导，OpenAI 跟进）— TrueFoundry 是最早重度玩家
- A2A 协议（Google 主导）需要中立开源实现 — agentgateway 填补空白

**风险**：
- 核心 AI Gateway 控制面闭源 → 企业 vendor lock-in 担忧
- $499/月起步价 vs 开源替代品 → SMB 市场难渗透
- agent gateway LF 治理成熟度待验证
- AWS / Azure / GCP 加 AI Gateway 投入 → 巨头挤压

### 12.3 给 5 类读者的建议

**给 CTO/平台架构师**：
- 如果你的合规要求高 + 多协议 + 多云 + 需要 GPU 调度，TrueFoundry 是当前最"一站式"的选择
- 但建议先做 PoC：免费 Developer plan → 测你的 LLM 用量 → 再评估 Pro / Pro Plus
- 关注 vendor lock-in 风险：核心 gateway 闭源，prompt / agent config 在控制面

**给 ML 工程师**：
- 如果你已经在用 vLLM / TGI / Triton，TrueFoundry 的 Deployment Platform 是顺手的
- LLM Locust 是轻量级压测工具，可以试试
- cognita RAG 框架也值得一看（4.4k stars）

**给 AI 创业者**：
- 起步别用 TrueFoundry，太贵太重，先 LiteLLM 自托管
- 等 ARR > $1M 再考虑迁移到 TrueFoundry 做企业级管控

**给安全/合规官**：
- TrueFoundry 的 SOC 2 / HIPAA / GDPR / ITAR 完整是优势
- VPC / On-prem / Air-gapped 部署选项齐全
- 审计日志 + RBAC + SSO + 数据驻留都做扎实

**给投资人**：
- $19M A 轮（2025），Intel Capital + Peak XV，跟投方质量高
- 季度净新收入翻倍（2025）— growth 强劲
- 客户 NVIDIA / Whatfix / Innovaccer — stickiness 强
- 但要关注：开源替代品（LiteLLM / Portkey）+ 云厂商自研 + agent gateway LF 治理进度

---

## 13. 总结

TrueFoundry 已经从"一个 ML 平台"演进成了 **"企业级 AI Gateway + Agent 部署平台 + 开源协议标准"** 三位一体的综合玩家。它不是 LiteLLM 的简单对手（LiteLLM 是开源 SDK + 轻量 proxy），它的真正对位是 **"Portkey 企业版 + 部分 Anyscale 功能 + AWS SageMaker 的 gateway 切片 + 一部分 Databricks 的全栈"**。

最有意思的点是 **`agentgateway/agentgateway` 项目** — Rust 写的、开源的、捐给 Linux Foundation 的 agent mesh proxy，同时支持 MCP + A2A + Kubernetes Inference Gateway 扩展。如果这个项目能持续 LF 治理成熟化、star 数继续增长，TrueFoundry 在"agentic AI 时代"的话语权就会显著强于 LiteLLM / Portkey 这些 LLM gateway 时代的玩家。

短期看（2026 年）：TrueFoundry 是 **"想做企业级 agentic AI 平台 + 不想被云厂商绑定"** 的最佳选择之一。
长期看（2027–2030 年）：要看 agentgateway LF 项目能否真正成为协议标准。

---

## 14. 参考资料（References）

### 14.1 官方一手资料

1. **TrueFoundry 官网首页**：`https://www.truefoundry.com/`
2. **AI Gateway 产品页**：`https://www.truefoundry.com/ai-gateway`
3. **MCP Gateway 产品页**：`https://www.truefoundry.com/mcp-gateway`
4. **Agent Gateway 产品页**：`https://www.truefoundry.com/agent-gateway`
5. **Pricing**：`https://www.truefoundry.com/pricing`
6. **llms.txt**：`https://www.truefoundry.com/llms.txt`（结构化产品信息）
7. **架构博客**：`https://www.truefoundry.com/blog/how-to-think-about-ai-gateway-architecture-in-the-generative-ai-stack`
8. **LLMOps 架构博客**：`https://www.truefoundry.com/blog/llmops-architecture`
9. **早期愿景博客**：`https://www.truefoundry.com/blog/truefoundry`
10. **客户案例**：`https://www.truefoundry.com/case-studies`
11. **G2 评分**：9.9/10

### 14.2 GitHub 仓库

12. **TrueFoundry 组织**：`https://github.com/truefoundry`
13. **agentgateway 项目（LF）**：`https://github.com/agentgateway/agentgateway`（3.1k stars, Rust, Apache-2.0）
14. **cognita**：`https://github.com/truefoundry/cognita`（4.4k stars, Python RAG）
15. **llm-locust**：`https://github.com/truefoundry/llm-locust`（TypeScript 压测）
16. **models**：`https://github.com/truefoundry/models`（19+ provider YAML 注册表）
17. **infra-charts**：`https://github.com/truefoundry/infra-charts`（Helm charts）
18. **terraform-kubernetes-truefoundry-helm**：`https://github.com/truefoundry/terraform-kubernetes-truefoundry-helm`
19. **mcp-servers**：`https://github.com/truefoundry/mcp-servers`
20. **mcp-servers-api**：`https://github.com/truefoundry/mcp-servers-api`
21. **tfy-mcp-server-deployment-example**：`https://github.com/truefoundry/tfy-mcp-server-deployment-example`
22. **CruiseKube**：`https://github.com/truefoundry/CruiseKube`（69 stars）
23. **integrations-custom-guardrails**：`https://github.com/truefoundry/integrations-custom-guardrails`
24. **truefoundry-python-sdk**：`https://github.com/truefoundry/truefoundry-python-sdk`
25. **agentgateway 官网**：`https://agentgateway.dev/`
26. **agentgateway 文档**：`https://agentgateway.dev/docs/`

### 14.3 已调研的相关产品（context）

27. `product-portkey-20260605.md` — Portkey Gateway
28. `product-litellm-20260605.md` — LiteLLM
29. `product-one-api-20260605.md` — One API
30. `product-higress-20260605.md` — Higress
31. `product-kong-ai-gateway-20260605.md` — Kong AI Gateway
32. `product-apisix-ai-proxy-20260605.md` — APISIX AI Proxy
33. `product-envoy-ai-gateway-20260605.md` — Envoy AI Gateway
34. `product-vllm-20260605.md` — vLLM
35. `product-sglang-20260605.md` — SGLang
36. `product-tgi-20260605.md` — TGI
37. `product-triton-inference-server-20260605.md` — Triton
38. `product-lmdeploy-20260605.md` — LMDeploy
39. `product-llama-cpp-20260605.md` — llama.cpp
40. `product-cloudflare-workers-ai-20260605.md` — Cloudflare
41. `product-openrouter-20260605.md` — OpenRouter
42. `product-helicone-20260605.md` — Helicone
43. `product-langsmith-20260605.md` — LangSmith
44. `product-unify-20260605.md` — Unify
45. `product-not-diamond-20260605.md` — Not Diamond

### 14.4 协议与生态

46. **MCP 协议**：`https://modelcontextprotocol.io/introduction`
47. **A2A 协议（Google）**：`https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/`
48. **Hono 框架**：`https://hono.dev`
49. **Gartner AI Gateway Market Guide 2025**（付费）
50. **Gartner 10 Best Practices for Optimizing GenAI Costs 2026**（付费）

---

> **调研人员**：Rich（OpenClaw AI）
> **调研时长**：~25 分钟（一手资料抓取 + 撰写）
> **数据采集时间**：2026-06-05 13:04 Asia/Shanghai
> **报告版本**：v1.0
> **下次更新建议**：2026-09（季度更新，监控 agentgateway LF 治理动态、TrueFoundry 融资进展、性能数据复测）
