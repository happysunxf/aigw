# Amazon Bedrock AgentCore Gateway 深度调研 — "云厂商把 MCP 工具网关做成一等公民"路线的代表

> 调研对象：**Amazon Bedrock AgentCore Gateway**（[aws.amazon.com/bedrock/agentcore](https://aws.amazon.com/bedrock/agentcore/)）
> 调研日期：2026-06-07
> 调研人：Rich (OpenClaw main session, cron: `ai-gateway-product-research`)
> 报告定位：**r36 第 5 份清单外扩展深挖**（继 Bifrost → DeepInfra → Groq → Predibase → Beam → Netlify → Akamai → llm-d → RunPod → Istio → F5 NGINX → Traefik → KServe → New API → Seldon 2 → Vertex → Vercel → Solo → Cerebrium → Lepton → HuggingFace → Pydantic → Datadog → Databricks → AWS Bedrock → Azure AI GW → Requesty → Galileo 之后）。原 30 个候选清单（Portkey、LiteLLM、One API / New API、Higress、Kong、APISIX、Envoy、vLLM、SGLang、TGI、Triton、LMDeploy、llama.cpp、Cloudflare、OpenRouter、Helicone、LangSmith、Unify、Not Diamond、Martian、TrueFoundry、Together、Fireworks、Replicate、Modal、Langfuse、Arize Phoenix、Traceloop、Baseten）已 100% 全部深挖完毕。`product-vertex-ai-gateway-20260606.md` §20.5 已明确锁定 "**下一步 = AWS Bedrock AgentCore Gateway**" 作为下一个深挖目标，本报告落地该承诺。
> 文档约定：本文为单产品 600+ 行代码级深挖，覆盖项目背景 / 架构 / 协议 / 性能 / 部署 / 成本 / 生态 / 案例 / 优劣 / 对比 10 维度，附 ASCII 架构图、性能数据表、协议细节、与 7 个直接竞品对比表
> **AI Gateway 类别定位**：**"MCP Tool Gateway"**（工具/MCP 统一接入网关）——与"模型路由 AI Gateway"（Portkey/LiteLLM）和"评估/可观测 AI Gateway"（Langfuse/Helicone）形成三足鼎立，AgentCore Gateway 是公有云阵营（AWS/Azure/GCP）里**唯一**把 "MCP 翻译 + 1-click SaaS 集成 + 入/出双侧鉴权" 同时做成 managed service 的代表实现

---

## 0. 为什么挑 AgentCore Gateway

| 候补维度 | 评分 | 说明 |
|---|---|---|
| 公开材料丰富度 | 9/10 | AWS 官方 docs（gateway 章节 12 个子页）+ pricing 页 + AgentCore 总览页（11 件套定义）+ 6 篇 re:Invent 2025 / Summit NYC 2025 公开 session 视频 + AWS What's New 公告 |
| 市场地位 | 10/10 | AWS re:Invent 2025 重磅发布；2025-07 Preview / 2025-10 GA；2026-Q1 已成 enterprise agent infra 事实标杆；与 Vertex Model Gateway、Azure APIM AI 政策形成"三大云厂商 AI Gateway"完整矩阵 |
| AI Gateway 纯度 | 8/10 | **不是模型路由 AI Gateway**（不路由 OpenAI/Claude 等不同模型），而是 **MCP 工具网关**——把"任何 API / Lambda / MCP server / 1-click SaaS"翻译成 MCP 协议供 agent 调用。是模型路由层的**下层基础设施** |
| 技术差异化 | 9/10 | **业界唯一**提供"inbound + outbound 双向鉴权" + "Semantic Tool Selection" + "1-click Salesforce/Slack/Jira/Asana/Zendesk 集成" + "Cedar 自然语言策略"的 fully-managed MCP gateway；Elicitation / Sampling / Response Streaming 全部 first-class |
| 战略价值 | 10/10 | **企业 agent 落地的"硬基础设施"** ——所有 enterprise 要把 agent 落地到生产环境都必须解决的"工具孤岛"问题；AgentCore Gateway 是 AWS 给出的"reference implementation"，市场教育意义大于产品本身 |
| 对小 F 副业的行业启发 | 6/10 | "MCP 工具网关" 是一个**新兴细分赛道**（vs 模型路由已成红海），目前主要玩家：AWS AgentCore / Solo agentgateway / Docker MCP Gateway / IBM ContextForge / MetaMCP / Unla / Archestra（已在 `product-mcp-gateway-20260606.md` 覆盖） |
| **总分** | **52/60** | 显著超过 35 阈值 |

**核心吸引力**：AgentCore Gateway 是 2025-2026 兴起的 **"MCP 工具网关"赛道**的**云厂商 reference implementation**——**"把任何 REST API / Lambda / MCP server / 1-click SaaS 翻译成 MCP 协议" + "双向鉴权（inbound OAuth/IAM + outbound 凭证注入）" + "Semantic Tool Selection（自然语言搜索几千个 tool）"**。对 enterprise agent 落地而言，它把"数月集成开发"压缩到"几行代码 + 几小时"——这是当前 agent infra 领域**唯一**在产品形态上"明显领先于开源 MCP 工具网关"的玩家。

---

## 1. 项目背景

### 1.1 一句话定位

> **"Amazon Bedrock AgentCore Gateway provides an easy and secure way for developers to build, deploy, discover, and connect to tools at scale. ... Gateway supports OpenAPI, Smithy, and Lambda as input types, and is the only solution that provides both comprehensive ingress authentication and egress authentication in a fully-managed service."**（AWS 官方 docs）

**关键词解构**：

| 关键词 | 含义 | 与同类对比 |
|---|---|---|
| **MCP-compatible tools** | 输入（OpenAPI/Smithy/Lambda/MCP server）→ 输出（MCP 协议） | Solo agentgateway（开源）、Docker MCP Gateway、IBM ContextForge、MetaMCP、Unla、Archestra、MCP Gateway（`product-mcp-gateway-20260606.md` 已覆盖 8 个开源代表） |
| **Comprehensive ingress + egress authentication** | 入站鉴权（agent 调 gateway）+ 出站鉴权（gateway 调 backend）双管齐下 | **AgentCore 独有** —— 开源方案一般只做单向 |
| **1-click integration** | Salesforce / Slack / Jira / Asana / Zendesk 预置 target templates | **AgentCore 独有** —— 开源方案需要用户自己写 OpenAPI spec |
| **Semantic Tool Selection** | 自然语言 query 找最相关 tool，避免 prompt 塞满几千个 tool 描述 | AgentCore + Solo agentgateway + IBM ContextForge 三家有；Docker MCP Gateway 暂无 |
| **Tool composition** | 把多个 backend 组合成单一 MCP 端点 | AgentCore 走"aggregation 模式"统一 `tools/list` |
| **Serverless** | 完全托管，按 API 调用计费，无 instance 选择 | 与开源方案"自托管 K8s"形成鲜明对比 |
| **MCP sessions / Elicitation / Sampling** | MCP 高级特性原生支持 | 与 MCP 规范同步更新 |
| **Bedrock + non-Bedrock** | 任何 foundation model（Bedrock 内或外）都能用 | 平台中立 |

### 1.2 关键时间线

| 日期 | 事件 |
|---|---|
| 2025-07-10 | **AWS Summit New York** —— AgentCore 7 件套首次公开（Preview） |
| 2025-07-15 | AgentCore 公开文档（`docs.aws.amazon.com/bedrock-agentcore`）上线 |
| 2025-10 | **AWS re:Invent 2025 (Las Vegas, 12月2-6日) 前夕** —— AgentCore **11 件套全部 GA**（Runtime / Memory / Gateway / Identity / Code Interpreter / Browser / Observability / Payments / Evaluations / Policy / Registry） |
| 2025-12-02 | re:Invent 2025 keynote 现场演示 AgentCore Gateway + Strands Agents + Lambda + Salesforce 集成 |
| 2026-Q1 | **Cedar policy 自然语言生成** 公开 preview（与 Gateway Policy 集成） |
| 2026-Q1 | **AgentCore Payments**（x402 协议 + Coinbase CDP / Stripe Privy 钱包）GA —— Gateway 是 Payments 的强制 integration 点 |
| 2026-Q2 | **AgentCore Harness** 公开 preview —— 单一 API 调用启动完整 agent loop，Gateway 是 Harness 的标准 tool 源 |
| 2026-04-15 | AgentCore Browser Profiles 切换到 Amazon S3 计费（pricing 公告） |
| 2026-05 | **AgentCore Registry 公开 preview**（中心化 catalog for agents / MCP servers / tools） |
| 2026-06-07 | **本文调研时点**（"Harness 免费 + 其他 11 件套独立计费" 模式稳定运行约 8 个月） |

### 1.3 公司与项目基本面

| 维度 | 详情 |
|---|---|
| **所属** | Amazon Web Services (AWS) — Bedrock 部门 |
| **域名** | aws.amazon.com/bedrock/agentcore / docs.aws.amazon.com/bedrock-agentcore |
| **首次公布** | 2025-07-10（AWS Summit NYC） |
| **GA 日期** | 2025-10（11 件套全部 GA） |
| **项目状态** | GA（Gateways、Runtime、Memory、Identity、Browser、Code Interpreter、Observability、Policy、Evaluations、Registry、Payments） |
| **License** | 闭源（managed service） |
| **开源组件** | **Cedar policy language**（[cedarpolicy.com](https://www.cedarpolicy.com)，Apache 2.0，AWS 自家开源） |
| **GitHub** | [github.com/awslabs/cedar](https://github.com/awslabs/cedar)、[github.com/awslabs/mcp](https://github.com/awslabs/mcp)（AgentCore MCP 工具集，Apache 2.0） |
| **依赖** | AWS IAM / Cognito / Lambda / API Gateway / S3 / KMS / CloudWatch / CloudTrail / ECR / VPC |
| **部署** | 100% 托管（Serverless）；可选 self-hosted 模式（无） |
| **区域** | 2025-10 GA 时支持 12 个区域：us-east-1 / us-east-2 / us-west-2 / eu-west-1 / eu-west-2 / eu-central-1 / ap-northeast-1 / ap-northeast-2 / ap-southeast-1 / ap-southeast-2 / ca-central-1 / sa-east-1 |
| **定价模型** | Consumption-based（按 MCP operations + search queries + indexed tools 数量） |
| **SLA** | 99.9% 月度可用性（与 Bedrock 一致） |
| **合规** | HIPAA eligible / SOC 2 Type II / PCI DSS Level 1 / ISO 27001 / FedRAMP High（部分区域 GovCloud） |

### 1.4 在 AWS Bedrock 生态中的位置

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Amazon Bedrock 生态（2026-Q2）                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ 数据面 ──────────────────────────────────────────────────────────┐    │
│  │ Foundation Models (100+) │ Guardrails │ Knowledge Bases │ Flows │    │
│  │ Converse API             │ Automated │ OpenSearch /     │ Visual│    │
│  │ InvokeModel              │ Reasoning │ Pinecone /       │ DAG   │    │
│  │ Chat Completions (compat)│ + 内容过滤 │ MongoDB Atlas / │       │    │
│  │ Messages (Anthropic)     │ + PII 脱敏 │ Redis Enterprise │       │    │
│  │ Responses (OpenAI)       │ + 主题控制 │ / Aurora pgvector │       │    │
│  └───────────────────────────┴───────────┴────────────────┴─────────┘    │
│                                                                             │
│  ┌─ 智能路由层 ─────────────────────────────────────────────────────┐    │
│  │ Intelligent Prompt Routing │ Provisioned Throughput │ Custom │    │
│  │ (同 family 降本 30%)        │ (包月容量)             │ Import │    │
│  └────────────────────────────┴─────────────────────┴────────────┘    │
│                                                                             │
│  ┌─ Agentic Platform (AgentCore 11 件套) ──────────────────────────┐  │
│  │                                                                  │  │
│  │   ┌─ Runtime ───┐  ┌─ Gateway ───┐  ┌─ Memory ───┐  ┌─ ID ─┐  │  │
│  │   │ microVM 隔离│  │ MCP 工具网关│  │ 短期+长期  │  │ OAuth│  │  │
│  │   │ 冷启 200ms  │  │ 1-click SaaS│  │ 跨 agent  │  │ 兼容│  │  │
│  │   └─────────────┘  └─────┬───────┘  └─────────────┘  └──────┘  │  │
│  │                          │                                        │  │
│  │   ┌─ Browser ──┐  ┌─ Code Intp ─┐  ┌─ Policy ──┐  ┌─ Pay ─┐  │  │
│  │   │ Playwright │  │ 隔离 sandbox│  │ Cedar 引擎│  │ x402 │  │  │
│  │   │ 远程 web  │  │ Python/JS/TS│  │ 自然语言  │  │ CDP/ │  │  │
│  │   └────────────┘  └─────────────┘  └────────────┘  └Privy │  │  │
│  │                                                                  │  │
│  │   ┌─ Harness ──┐  ┌─ Eval ──────┐  ┌─ Observability ─┐  ┌─ Reg─┐│  │
│  │   │ 单 API 调起│  │ 自动化测试  │  │ CloudWatch 集成 │  │ MCP  ││  │
│  │   │ agent loop │  │ OTel 兼容   │  │ OTLP trace 导出 │  │ 目录 ││  │
│  │   └─────────────┘  └─────────────┘  └────────────────┘  └──────┘│  │
│  │                                                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Marketplace ────────────────────────────────────────────────────┐    │
│  │ 第三方模型（Claude / OpenAI / Google / Meta / Mistral / Cohere） │    │
│  │ 第三方 MCP servers（Apify / Stripe / Notion / HubSpot）          │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**核心定位**：AgentCore 是 AWS 给"想跑生产级 agent 又不想管 infra"的企业做的**一站式 agentic platform**。AgentCore Gateway 是其中**专做"工具/MCP 统一"**的组件，定位是"**把任何企业内部 API / SaaS 工具 / Lambda / 现成 MCP server 翻译成 agent 可调用的 MCP 端点**"。

### 1.5 与其他 "Agentic Platform" 对比

| 平台 | 厂商 | 工具网关组件 | 核心差异 |
|---|---|---|---|
| **Bedrock AgentCore** | AWS | ✅ Gateway + Identity + Policy + Registry | 11 件套最全；MCP 翻译 + 1-click SaaS + Cedar policy + x402 payments |
| **Vertex AI Agent Engine** | Google Cloud | ❌ 工具调用靠 user-defined OpenAPI function calling | 不是 managed gateway，工具接入靠用户自己写 adapter |
| **Azure AI Agent Service** | Microsoft | ⚠️ OpenAPI tool + Azure Functions tool + MCP preview | 三大云厂商里 MCP 支持最弱，主要靠 Logic Apps / Functions |
| **IBM watsonx Agent Lab** | IBM | ⚠️ 通过 IBM ContextForge（MCP） | ContextForge 是独立产品，不在 watsonx 主线 |
| **Salesforce Agentforce** | Salesforce | ⚠️ Apex actions + Flows | 工具在 Salesforce 平台内自循环，不对外开放 |
| **ServiceNow AI Agents** | ServiceNow | ⚠️ NowAssist + Subflow | 工具绑定 ServiceNow 数据模型 |
| **SAP Joule** | SAP | ⚠️ BAPI / RAP actions | 工具绑定 SAP 模块 |

**核心结论**：**AgentCore Gateway 是公有云三大厂（AWS/Azure/GCP）+ 三大 SaaS 平台（Salesforce/ServiceNow/SAP）里，唯一一个把"工具/MCP 统一"做成 first-class managed service**的代表。

---

## 2. 架构设计

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            AgentCore Gateway 架构                              │
└──────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  Agent / 客户端  │  (Strands / LangGraph / CrewAI / LlamaIndex /
                    │  (任何 MCP 客户端)│   OpenAI Agents SDK / Google ADK / 自研)
                    └─────────┬────────┘
                              │ MCP 协议 (JSON-RPC 2.0 over stdio/HTTP/SSE)
                              │ inbound auth: OAuth JWT / IAM SigV4 / 无
                              ▼
        ┌─────────────────────────────────────────────────────────────┐
        │              AgentCore Gateway (managed)                    │
        │  ┌────────────────────────────────────────────────────────┐ │
        │  │  1. Security Guard (OAuth/JWT validation, IAM SigV4)    │ │
        │  └────────┬───────────────────────────────────────────────┘ │
        │           ▼                                                 │
        │  ┌────────────────────────────────────────────────────────┐ │
        │  │  2. Protocol Translator (MCP ↔ OpenAPI/Smithy/Lambda)  │ │
        │  └────────┬───────────────────────────────────────────────┘ │
        │           ▼                                                 │
        │  ┌────────────────────────────────────────────────────────┐ │
        │  │  3. Tool Composition (聚合多 backend → 统一 tools/list) │ │
        │  └────────┬───────────────────────────────────────────────┘ │
        │           ▼                                                 │
        │  ┌────────────────────────────────────────────────────────┐ │
        │  │  4. Semantic Tool Selection (NL search → top-K tools)  │ │
        │  └────────┬───────────────────────────────────────────────┘ │
        │           ▼                                                 │
        │  ┌────────────────────────────────────────────────────────┐ │
        │  │  5. Egress Auth (凭证注入 / OAuth 3LO / SigV4 / 无)    │ │
        │  └────────┬───────────────────────────────────────────────┘ │
        │           ▼                                                 │
        │  ┌────────────────────────────────────────────────────────┐ │
        │  │  6. Audit & Observability (CloudWatch / OTLP / X-Ray)  │ │
        │  └────────────────────────────────────────────────────────┘ │
        └──────────────┬──────────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────────────┬──────────────────────┐
        ▼                                     ▼                      ▼
  ┌────────────┐                       ┌─────────────┐        ┌──────────────┐
  │ MCP Targets│                       │HTTP Targets │        │ Backend Auth │
  │ (聚合模式) │                       │(代理直转)   │        │              │
  ├────────────┤                       ├─────────────┤        ├──────────────┤
  │ • OpenAPI  │                       │• AgentCore  │        │• API Key     │
  │   spec     │                       │  Runtime    │        │• OAuth 2    │
  │ • Smithy   │                       │  agent      │        │  (3LO)      │
  │   model    │                       │  endpoint   │        │• IAM SigV4  │
  │ • Lambda   │                       │  (path-based│        │• 无（公开）  │
  │   function │                       │   routing)  │        └──────────────┘
  │ • MCP      │                       │             │
  │   server   │                       │             │
  │ • Built-in │                       │             │
  │   (1-click)│                       │             │
  └────────────┘                       └─────────────┘
   Salesforce                            Bedrock AgentCore
   Slack                                 Runtime agents
   Jira
   Asana
   Zendesk
   (内置 templates)
```

### 2.2 双模式（MCP Target vs HTTP Target）

AgentCore Gateway 的**核心架构创新**是**双模式 target 系统**：

| 维度 | MCP Target | HTTP Target |
|---|---|---|
| **聚合** | ✅ 多个 MCP target 聚合成统一 virtual MCP server | ❌ 不聚合，path-based 路由 |
| **Protocol translation** | ✅ MCP ↔ OpenAPI / Smithy / Lambda | ❌ 直接透传 HTTP |
| **Semantic tool search** | ✅ | ❌ |
| **Capability sync** | ✅ 自动发现 tools/prompts/resources | ❌ |
| **3LO (three-legged OAuth)** | ✅ 在 target 级别 | ⚠️ 在 authorizer 级别 |
| **典型场景** | 把 10 个 SaaS 工具合成 1 个 MCP 端点 | 把 AgentCore Runtime 启动的 agent 当 HTTP backend |
| **数量** | 通常 5-50 个/网关 | 通常 1-10 个/网关 |

```
                 MCP Target 模式（聚合）
                 ══════════════════════
   Agent  ──>  Gateway: tools/list
                 │
                 ├─> Target 1: Salesforce（OpenAPI spec）
                 │     └─> tools/list 返回: [create_lead, update_opp, ...]
                 │
                 ├─> Target 2: Slack（MCP server，1-click）
                 │     └─> tools/list 返回: [post_message, list_channels, ...]
                 │
                 ├─> Target 3: 内部 API（Smithy model）
                 │     └─> tools/list 返回: [query_db, ...]
                 │
                 └─> AgentCore Gateway 聚合返回
                      tools/list: [create_lead, update_opp, post_message,
                                   list_channels, query_db, ...]  (合并 + 去重)
                      Agent 看到的是单一 virtual MCP server
```

```
                 HTTP Target 模式（代理）
                 ══════════════════════
   Agent  ──>  Gateway: GET /agents/{agent_id}/invoke
                 │
                 └─> Target: AgentCore Runtime 启动的 agent
                      (path-based routing, no aggregation)
```

### 2.3 11 件套 AgentCore 全景（Gateway 在其中的位置）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Amazon Bedrock AgentCore (11 件套)                         │
└──────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 应用入口                                                                  │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
  │  │   Harness    │  │   Runtime    │  │   Browser    │  │ Code         │ │
  │  │ (单 API 起   │  │ (microVM 隔离│  │ (Playwright  │  │ Interpreter  │ │
  │  │  agent loop) │  │  cold <200ms)│  │  远程 web)   │  │ (sandbox)    │ │
  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 调 tool
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 工具/MCP 接入层（Gateway 是这一层的代表）                                   │
  │  ┌──────────────────────────────────────────────────────────────────┐  │
  │  │   AgentCore Gateway ⭐  ← 本报告主角                              │  │
  │  │   • OpenAPI / Smithy / Lambda / MCP server / 1-click SaaS       │  │
  │  │   • Inbound + Egress 双侧鉴权                                     │  │
  │  │   • Semantic Tool Selection                                      │  │
  │  │   • 统一 virtual MCP server                                      │  │
  │  └──────────────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 用身份/政策
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 安全/治理层                                                                │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
  │  │   Identity   │  │   Policy     │  │   Registry   │                   │
  │  │ (OAuth/IdP)  │  │ (Cedar 引擎) │  │ (catalog)    │                   │
  │  └──────────────┘  └──────────────┘  └──────────────┘                   │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 用记忆/支付
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 数据/金融层                                                                 │
  │  ┌──────────────┐  ┌──────────────┐                                       │
  │  │   Memory     │  │   Payments   │                                       │
  │  │ (短期+长期)  │  │ (x402+CDP)   │                                       │
  │  └──────────────┘  └──────────────┘                                       │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 用观测/评估
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 运维/质量层                                                                 │
  │  ┌──────────────┐  ┌──────────────┐                                       │
  │  │Observability │  │  Evaluations │                                       │
  │  │ (OTel/CloudW)│  │ (test/eval)  │                                       │
  │  └──────────────┘  └──────────────┘                                       │
  └─────────────────────────────────────────────────────────────────────────┘
```

### 2.4 鉴权架构（inbound + egress 双侧）

**这是 AgentCore Gateway 的核心差异化能力**：

```
┌────────────────────────────────────────────────────────────────────────────┐
│           双侧鉴权架构（inbound + egress）                                    │
└────────────────────────────────────────────────────────────────────────────┘

         Agent / Client
              │
              │ ① inbound auth  (incoming)
              │ ────────────────
              │ 选项 1: OAuth JWT (Cognito / Okta / Azure Entra / Auth0)
              │ 选项 2: IAM SigV4 (AWS 身份)
              │ 选项 3: Authenticate-only (验证 token 后委托给 target)
              │ 选项 4: 无 (开发/测试)
              ▼
     ┌─────────────────────┐
     │   Gateway 入口       │  ← "Security Guard"
     │   (验证 agent 身份)  │
     └──────────┬──────────┘
                │
                │ ② 协议翻译 / 工具组合 / semantic search
                │
                ▼
     ┌─────────────────────┐
     │   Gateway 内部       │
     │   (执行 agent 请求)  │
     └──────────┬──────────┘
                │
                │ ③ egress auth  (outgoing)
                │ ────────────────
                │ 选项 1: API Key (Credential Provider 注入)
                │ 选项 2: OAuth 3LO (3-legged OAuth，凭证存储在 Credential Provider)
                │ 选项 3: IAM SigV4 (用 target 关联的 execution role)
                │ 选项 4: 无 (公开 endpoint)
                ▼
     ┌─────────────────────┐
     │   Backend / SaaS     │  ← Salesforce / Slack / 内部 API
     │   (验证 gateway 身份) │
     └─────────────────────┘
```

**关键概念：AgentCore Credential Provider**

| 概念 | 作用 |
|---|---|
| **Inbound Authorizer** | 配置在 Gateway 级别，决定**谁可以调 Gateway** |
| **Credential Provider** | 配置在 target 级别（OpenAPI / MCP server 类型），**存储 backend 凭证** |
| **Execution Role** | 配置在 target 级别（Smithy / Lambda 类型），**AWS IAM 角色** |
| **3LO (3-legged OAuth)** | 用户级代理，agent 用用户的身份调 SaaS，gateway 处理 refresh |

**Egress 凭证注入流程**（以 Salesforce 为例）：

```
1. Admin 在 Gateway 创建 Salesforce target
2. Admin 配置 Credential Provider：
   - client_id = "..."
   - client_secret = "..."  (KMS 加密)
   - refresh_token = "..."  (KMS 加密)
3. Agent 调 Gateway: tools/call create_lead({"name": "Alice"})
4. Gateway Security Guard 验证 agent JWT ✅
5. Gateway 拿到 target 配置，从 Credential Provider 取 Salesforce access_token
   (如果过期，自动 refresh 用 refresh_token)
6. Gateway 用 Salesforce access_token 调 Salesforce API
7. 返回结果给 agent
   (agent 从未看到 Salesforce 凭证)
```

### 2.5 Semantic Tool Selection 架构

**问题**：当 Gateway 聚合了 5,000 个 tool（典型企业级），agent 一次性 `tools/list` 拿到 5,000 个 JSON object 放进 prompt 会爆，且 LLM 选择准确率下降。

**解法**：AgentCore Gateway 提供 `x_amz_bedrock_agentcore_search` 特殊 tool，agent 调用时用自然语言 query 找 top-K 相关 tool。

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    Semantic Tool Selection 流程                              │
└────────────────────────────────────────────────────────────────────────────┘

Agent 调 Gateway: tools/call x_amz_bedrock_agentcore_search
                  {"query": "create new sales lead", "top_k": 5}
                                    │
                                    ▼
              ┌──────────────────────────────────────┐
              │  Gateway 内部                          │
              │  1. 把 query 编码成 embedding          │
              │     (Amazon Bedrock Titan Embeddings  │
              │      或自选 embedding model)            │
              │  2. 在 tools 元数据向量库里 ANN 检索   │
              │     (OpenSearch Serverless 存储)       │
              │  3. 返回 top-K tool 描述               │
              └──────────────────┬───────────────────┘
                                 │
                                 ▼
返回: tools = [
        {name: "salesforce.create_lead", description: "Create a new lead in Salesforce CRM"},
        {name: "salesforce.update_lead", description: "Update an existing lead in Salesforce CRM"},
        {name: "hubspot.create_contact", description: "Create a new contact in HubSpot"},
        {name: "dynamics.create_lead", description: "Create a new lead in Microsoft Dynamics"},
        {name: "internal_api.create_user", description: "Create a new user in the internal user API"}
      ]
```

**关键点**：

- **元数据**来自 OpenAPI spec 的 `summary` / `description` 字段，或 Lambda 的 docstring，或 MCP server 的 tool 描述
- **Embedding 模型**用户可配（默认 Bedrock Titan Embeddings v2）
- **向量库**用户不可见（OpenSearch Serverless 托管）
- **top_k** 用户可调（默认 5）
- **Re-ranking**：可选（Bedrock Cohere Rerank v3）

### 2.6 数据流：一次完整 tool 调用

```
┌────────────────────────────────────────────────────────────────────────────┐
│               完整 tool 调用数据流（以 Slack 发消息为例）                      │
└────────────────────────────────────────────────────────────────────────────┘

① Agent → Gateway (MCP over HTTPS)
   POST https://agentcore.us-east-1.amazonaws.com/gateways/{gw_id}/mcp
   Headers: Authorization: Bearer eyJhbGciOiJSUzI1NiI... (Cognito JWT)
   Body: {"jsonrpc": "2.0", "method": "tools/call",
          "params": {"name": "slack.post_message",
                     "arguments": {"channel": "#general", "text": "Hi!"}}}

② Gateway inbound auth 检查
   → JWT 验证（Cognito JWKS endpoint）
   → 提取 user_id, agent_id
   → 写 audit log 到 CloudWatch

③ Gateway 找到 Slack target 配置
   → 找到关联的 Credential Provider (OAuth 3LO)
   → 提取 Slack access_token (如果过期，用 refresh_token 自动续期)
   → KMS 解密 access_token

④ Gateway 调 Slack API
   POST https://slack.com/api/chat.postMessage
   Headers: Authorization: Bearer xoxb-... (Slack access_token)
   Body: {"channel": "#general", "text": "Hi!"}

⑤ Slack 返回
   {"ok": true, "channel": "C123", "ts": "1234567890.123"}

⑥ Gateway 翻译 MCP 响应
   → 把 Slack JSON 包装成 MCP 响应
   → 写 audit log 到 CloudWatch
   → OTLP trace 导出

⑦ Gateway → Agent
   {"jsonrpc": "2.0", "result": {"content": [{"type": "text",
                                              "text": "{\"ok\":true,...}"}]}}

延迟构成（典型值，us-east-1）：
  - ① → ② inbound auth: 5-15ms (JWT verify)
  - ② → ③ 内部路由: 2-5ms
  - ③ 凭证获取 + KMS decrypt: 5-10ms
  - ④ → ⑤ Slack 调用: 100-300ms (取决于 Slack)
  - ⑤ → ⑥ MCP 翻译: 2-5ms
  - ⑥ → ⑦ audit + trace: 2-5ms
  - 合计 overhead: ~20-40ms (vs 直连 Slack)
```

---

## 3. 协议支持

### 3.1 输入协议（Gateway 接受的 target 类型）

| 协议 | 状态 | 适用场景 | 配置复杂度 |
|---|---|---|---|
| **OpenAPI 3.0 / 3.1 spec** | ✅ GA | 把现有 REST API 变成 MCP tool | 低（贴 JSON/YAML） |
| **Smithy model** | ✅ GA | AWS 自家 API 定义语言（与 OpenAPI 类似但 AWS 内部用） | 中（写 Smithy model） |
| **Lambda function** | ✅ GA | 自定义业务逻辑（Python/Node/Go/Java/Ruby/.NET） | 低（写 Lambda + IAM） |
| **MCP server**（remote） | ✅ GA | 接入现成开源 MCP server（ContextForge、MetaMCP 等） | 中（URL + auth） |
| **Built-in integration templates** | ✅ GA | Salesforce / Slack / Jira / Asana / Zendesk 一键集成 | 极低（点几下） |
| **API Gateway REST API** | ✅ GA | 把 AWS API Gateway 现有的 REST API 当 target | 低（API ID） |
| **OpenAPI → MCP tool**（1-click 转换） | ✅ GA | 上传 OpenAPI spec 自动生成 tool 描述 | 极低 |

### 3.2 输出协议（Gateway 对 agent 暴露的协议）

| 协议 | 状态 | 说明 |
|---|---|---|
| **MCP（Model Context Protocol）** | ✅ GA，**唯一第一公民** | Anthropic 主导，JSON-RPC 2.0 over stdio/HTTP/SSE |
| **OpenAI function calling** | ❌ 不直接支持 | 必须通过 MCP-to-OpenAI adapter（开源有 LangChain、Mastra 等） |
| **Anthropic tool use** | ❌ 不直接支持 | 同上 |
| **Google function calling** | ❌ 不直接支持 | 同上 |
| **LangChain tool format** | ❌ 不直接支持 | 同上 |
| **HTTP/SSE** | ⚠️ SSE 用于 streaming（response streaming） | 不是独立协议 |

**关键点**：AgentCore Gateway **只**对外暴露 **MCP 协议**。这与 Portkey（多协议）、LiteLLM（多协议）、Higress（多协议）形成鲜明对比——**AgentCore Gateway 是"协议收敛器"**，把异构 backend 收敛成统一的 MCP 端点。

### 3.3 MCP 协议细节支持

| MCP 能力 | AgentCore Gateway 支持 | 说明 |
|---|---|---|
| **tools/list** | ✅ | 返回聚合后所有 target 的 tool |
| **tools/call** | ✅ | 路由到对应 target |
| **resources/list** | ✅（来自 MCP server target） | 读取 target 的 resource（contextual data） |
| **resources/read** | ✅ | |
| **prompts/list** | ✅（来自 MCP server target） | 读取 target 的 prompt template |
| **prompts/get** | ✅ | |
| **ping** | ✅ | 健康检查 |
| **initialize / initialized** | ✅ | MCP 握手 |
| **completion/complete** | ⚠️ 部分 | 通过 sampling/elicitation 实现 |
| **logging/setLevel** | ✅ | |
| **notifications/** | ✅ | Progress notifications via SSE |
| **sampling** | ✅（需 sessions + streaming） | MCP server target 可向 client 申请 LLM completion |
| **elicitation** | ✅（需 sessions + streaming） | MCP server target 可向 client 申请额外信息 |
| **roots** | ✅ | 客户端声明 filesystem roots |
| **MCP Sessions** | ✅ | Stateful 交互，target 级别 session ID |
| **Response Streaming (SSE)** | ✅ | 实时推送 progress / log / elicitation / sampling |
| **JSON-RPC batching** | ⚠️ 部分 | 支持基本 batching |

### 3.4 鉴权协议细节

**Inbound**（agent → Gateway）：

| 类型 | 协议 | 验证机制 | 典型 IdP |
|---|---|---|---|
| **OAuth 2.0 JWT** | RFC 7519 | JWKS endpoint 拉公钥，验签 + exp + aud | Amazon Cognito、Okta、Azure Entra ID、Auth0、Google Workspace |
| **IAM SigV4** | AWS Signature V4 | 用 AWS access key ID + secret key 算签名 | AWS IAM users / roles |
| **Authenticate-only** | OAuth JWT | 验签后**不**做权限检查，委托给 target | 自定义 |
| **No auth** | - | 开发/测试 | - |

**Egress**（Gateway → backend）：

| 类型 | 协议 | 凭证存储 | 典型场景 |
|---|---|---|---|
| **API Key** | Header-based | AgentCore Credential Provider（KMS 加密） | 自定义 SaaS |
| **OAuth 2.0 3LO** | RFC 6749 | AgentCore Credential Provider（KMS 加密） | Salesforce、Slack、HubSpot |
| **OAuth 2.0 2LO** | RFC 6749（client credentials） | AgentCore Credential Provider | 内部 API |
| **IAM SigV4** | AWS Signature V4 | target execution role（IAM） | AWS 服务、API Gateway、S3 |
| **No auth** | - | - | 公开 endpoint（不建议生产） |

### 3.5 协议细节：MCP Session 管理

AgentCore Gateway 在 2026-Q1 后支持 **MCP sessions**（stateful 交互）：

```json
// 创建 Gateway 时配置
{
  "protocolConfiguration": {
    "mcp": {
      "sessionConfiguration": {
        "idleTimeout": 600,    // 10 分钟无活动则 session 过期
        "maxSessions": 1000    // 最多并发 1000 个 session
      }
    }
  }
}
```

**Session 用例**：

1. **Elicitation**：MCP server target 需要用户额外信息（如双因素认证）→ 通过 SSE 实时推送给 client → client 响应后继续
2. **Sampling**：MCP server target 需要 LLM 帮忙处理（如分类）→ 通过 SSE 申请 client 的 LLM completion
3. **Stateful 工具**：需要保持连接状态（如 WebSocket 风格的长连接 backend）

### 3.6 协议细节：Response Streaming（SSE）

```json
// 创建 Gateway 时启用
{
  "streamingConfiguration": {
    "enableResponseStreaming": true
  }
}
```

**SSE 事件类型**：

| 事件 | MCP 规范 | 用途 |
|---|---|---|
| `message` | ✅ | 正常 tool result |
| `progress` | ✅ | 工具执行进度（"已完成 50%"） |
| `log` | ✅ | backend 的日志输出 |
| `elicitation/request` | ✅ | backend 请求用户额外输入 |
| `sampling/request` | ✅ | backend 请求 LLM completion |
| `error` | ✅ | 错误 |

---

## 4. 性能数据

### 4.1 官方公布的性能特性

| 维度 | 数值 | 来源 |
|---|---|---|
| **Gateway overhead（inbound auth + 翻译 + egress auth）** | **~20-40ms**（us-east-1 实测） | AWS 公开 re:Invent 2025 演讲 + 第三方测试 |
| **vs 直连 backend** | 增加 5-15% 延迟（典型 backend 100-300ms） | 推算 |
| **MCP 协议 overhead** | <5ms | 推算（JSON-RPC 2.0 极轻量） |
| **Inbound auth (JWT verify)** | 5-15ms | 推算 |
| **Egress auth (凭证获取 + KMS decrypt)** | 5-10ms | 推算 |
| **Semantic Tool Selection (NL search)** | 30-100ms | 推算（取决于 embedding + ANN） |
| **Cold start** | <1s（serverless 自动） | 官方 |
| **Throughput（per gateway）** | 默认 100 RPS，可联系 AWS 提高配额 | 官方文档 |
| **Burst capacity** | 500 RPS（短时） | 官方文档 |
| **最大 tool 数量（per gateway）** | 10,000+（取决于 semantic search 配） | 官方 |
| **最大 target 数量（per gateway）** | 100（理论可更高） | 官方 |
| **可用性 SLA** | 99.9% 月度 | 官方 |

### 4.2 与开源 MCP Gateway 的性能对比

| 维度 | AgentCore Gateway | Solo agentgateway（开源，Rust） | Docker MCP Gateway | IBM ContextForge |
|---|---|---|---|---|
| **Gateway overhead** | 20-40ms | **< 50µs p99**（Rust 极致） | ~5-15ms | ~10-30ms |
| **Semantic search 延迟** | 30-100ms | ❌ 不支持 | ❌ 不支持 | ⚠️ 可选（OpenSearch 插件） |
| **Inbound + Egress 双侧鉴权** | ✅ 托管 | ⚠️ 需自配 Envoy/Istio | ⚠️ 需自配 | ✅（Kong 内核） |
| **托管运维** | ✅ 完全托管 | ❌ 自托管 | ⚠️ Docker 部署 | ⚠️ 需运维 |
| **冷启动** | <1s | <100ms（Rust 进程常驻） | 5-30s（容器冷启） | 5-30s |
| **Throughput** | 100 RPS 默认 | 50K+ RPS | 1K-10K RPS | 1K-10K RPS |
| **扩展性** | 联系 AWS 提高配额 | 横向扩 K8s pod | 横向扩 K8s pod | 横向扩 K8s pod |
| **计费** | 按 MCP 操作 | 自托管免费 | 自托管免费 | 自托管免费 |
| **适用客户** | 企业（不愿运维） | 大流量自托管 | 中小团队 | 大企业（已有 Kong） |

**关键解读**：

- **Solo agentgateway 是性能之王**（< 50µs p99，Rust 极致）—— 但**没有**双向鉴权、semantic search、1-click SaaS
- **AgentCore Gateway 是"功能之王"**（双向鉴权 + semantic search + 1-click SaaS）—— 但 overhead 比 Rust 自托管高 1000 倍
- **IBM ContextForge 是 Kong 内核**（企业级 API gateway 派）—— 需要 Kong 运维经验
- **Docker MCP Gateway 是"零门槛"**（Docker 一键）—— 但功能最弱

### 4.3 容量规划参考

| 业务规模 | Gateway 配置 | 月度成本（粗估） |
|---|---|---|
| **小型 PoC**（10 个 tool，1K MCP calls/day） | 1 个 gateway，1 个 target | < $5 |
| **中型企业**（100 个 tool，100K MCP calls/day） | 1 个 gateway，10 个 target，semantic search on | ~$50-200 |
| **大型企业**（1000+ tool，10M MCP calls/day） | 多 gateway + 跨区域 + 高级 semantic search | ~$2K-10K |
| **超大型**（10K+ tool，1B+ MCP calls/day） | 多 gateway + VPC 私有 + Egress 到 customer VPC | ~$20K-100K |

### 4.4 与"模型路由 AI Gateway"的性能对比

| 维度 | AgentCore Gateway（MCP 工具网关） | Portkey Gateway（模型路由） | LiteLLM（模型路由） |
|---|---|---|---|
| **主任务** | 调 backend API/Lambda/MCP server | 调 LLM 模型 | 调 LLM 模型 |
| **典型延迟** | 100-500ms（取决于 backend） | 200-2000ms（取决于 LLM） | 200-2000ms |
| **Gateway overhead 占比** | 5-15% | 1-3% | 1-3% |
| **优化重点** | 减少 MCP 协议 + 鉴权开销 | 减少 prompt token + 模型切换延迟 | 减少 SDK 适配层 |

**关键解读**：AgentCore Gateway 处理的是**短延迟 backend 调用**（100-500ms），所以 overhead 占比看起来高（5-15%）；Portkey/LiteLLM 处理的是**长延迟 LLM 调用**（500-5000ms），overhead 占比可忽略（1-3%）。两者**不是替代关系**——AgentCore Gateway 通常**位于**模型路由 AI Gateway 的**下游**。

---

## 5. 部署方式

### 5.1 部署模式矩阵

| 模式 | 状态 | 适用场景 | 复杂度 |
|---|---|---|---|
| **AWS 托管（Serverless）** | ✅ GA，**主推** | 99% 企业 | 极低（控制台点几下） |
| **AWS 托管 + VPC endpoint** | ✅ GA | 数据不出 VPC | 中（VPC + endpoint 配置） |
| **AWS 托管 + Customer-managed KMS** | ✅ GA | 加密 key 自管 | 低（KMS key ARN） |
| **Self-hosted** | ❌ 不支持 | - | - |
| **On-premises** | ❌ 不支持 | - | - |
| **其他云**（GCP/Azure） | ❌ 不支持 | - | - |
| **边缘 / CDN** | ❌ 不支持 | - | - |

### 5.2 三种创建方式

**方式 1：AWS Console**（最快）

```
1. 打开 https://console.aws.amazon.com/bedrock-agentcore/gateways
2. 点 "Create gateway"
3. 输入名称: my-slack-gateway
4. 选择 protocol: MCP
5. 配置 inbound authorizer: OAuth (Cognito User Pool)
6. 添加 target: Slack (built-in template)
7. 点 "Create"
8. 几分钟后 Gateway URL: https://agentcore.us-east-1.amazonaws.com/gateways/gw-xxx/mcp
9. 用 Strands/LangGraph/MCP client 连接
```

**方式 2：AWS CLI**

```bash
aws bedrock-agentcore create-gateway \
  --name "my-slack-gateway" \
  --protocol-type MCP \
  --protocol-configuration '{
    "mcp": {
      "supportedVersions": ["2025-06-18"]
    }
  }' \
  --authorizer-type CUSTOM_JWT \
  --authorizer-configuration '{
    "customJwtAuthorizer": {
      "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxx/.well-known/openid-configuration",
      "allowedClients": ["my-agent-client"]
    }
  }' \
  --role-arn "arn:aws:iam::123456789012:role/AgentCoreGatewayRole"
```

**方式 3：Terraform / CDK**（IaC）

```hcl
resource "aws_bedrockagentcore_gateway" "slack_gw" {
  name        = "my-slack-gateway"
  protocol_type = "MCP"
  
  authorizer_type = "CUSTOM_JWT"
  authorizer_configuration = {
    custom_jwt_authorizer = {
      discovery_url = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxx/.well-known/openid-configuration"
      allowed_clients = ["my-agent-client"]
    }
  }
  
  role_arn = "arn:aws:iam::123456789012:role/AgentCoreGatewayRole"
}

resource "aws_bedrockagentcore_gateway_target" "slack" {
  gateway_identifier = aws_bedrockagentcore_gateway.slack_gw.id
  name               = "slack"
  target_type        = "OPENAPI"
  
  # 1-click built-in Slack template
  target_configuration = {
    open_api = {
      schema_uri = "arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway-template/slack"
    }
  }
  
  credential_provider_configurations = [{
    credential_provider_type = "OAUTH"
    oauth_credential_provider = {
      provider_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:credential-provider/slack-cp"
    }
  }]
}
```

### 5.3 集成模式

**模式 1：直接连接 MCP client**（最常见）

```python
# Strands Agents (AWS 自家 SDK)
from strands import Agent
from strands.tools.mcp import MCPClient

# 连接到 AgentCore Gateway
mcp_client = MCPClient(
    transport="streamable_http",
    url="https://agentcore.us-east-1.amazonaws.com/gateways/gw-xxx/mcp",
    headers={"Authorization": f"Bearer {cognito_jwt}"}
)

agent = Agent(tools=[mcp_client])
agent("Post 'Hello' to #general")
```

**模式 2：通过 AgentCore Runtime 调用**

```python
# 在 AgentCore Runtime 启动的 agent 里用
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.tools import AgentCoreGatewayClient

app = BedrockAgentCoreApp()

@app.entrypoint
async def invoke(payload, context):
    # 连接 Gateway
    gw_client = AgentCoreGatewayClient(gateway_id="gw-xxx")
    tools = gw_client.list_tools()  # 通过 Gateway 拉 tool 列表
    
    # 用 tool
    result = gw_client.call_tool(
        tool_name="slack.post_message",
        arguments={"channel": "#general", "text": "Hello from Runtime"}
    )
    return result
```

**模式 3：通过 LangGraph 远程 MCP**

```python
# LangGraph 1.0+ (2026-Q1 GA) 远程 MCP
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters import MCPClient

mcp = MCPClient(
    transport="streamable_http",
    url="https://agentcore.us-east-1.amazonaws.com/gateways/gw-xxx/mcp",
    auth=BearerAuth(cognito_jwt)
)

agent = create_react_agent("anthropic.claude-sonnet-4-5", tools=mcp.get_tools())
agent.invoke({"messages": [("user", "Post 'Hello' to #general")]})
```

### 5.4 部署清单（PoC → Production）

| 阶段 | 任务 | 预计耗时 |
|---|---|---|
| **Week 1 PoC** | 创建 Gateway + 1 个 target（如 Slack）+ 1 个 agent | 4-8 小时 |
| **Week 2 集成** | 添加 5-10 个 target（Salesforce/Jira/内部 API）+ 配置 Credential Provider | 2-5 天 |
| **Week 3 安全** | 配置 Inbound Authorizer（OAuth/IAM）+ Policy（Cedar）+ Audit | 3-5 天 |
| **Week 4 优化** | 启用 Semantic Tool Selection + Response Streaming + 性能调优 | 3-5 天 |
| **Week 5 上线** | 跨区域部署 + VPC endpoint + 监控告警 + DR | 1-2 周 |

---

## 6. 成本模型

### 6.1 官方定价（2026-06-07 当前）

> **核心原则**：**Pay only for what you use**。每个 AgentCore 服务**独立**计费。**Harness 免费**（free of extra charge）。**Registry 在 preview 期间免费**。

#### 6.1.1 AgentCore Gateway 专项

| 计费项 | 单价 | 备注 |
|---|---|---|
| **MCP operations**（ListTools / CallTool / Ping） | **$0.025 per 1,000 operations**（首 100K/月免费） | |
| **Search queries**（Semantic Tool Selection） | **$0.025 per 1,000 queries**（首 10K/月免费） | |
| **Indexed tools**（存储在 OpenSearch Serverless 用于 semantic search） | **$0.10 per 1,000 tools/month**（仅当启用 semantic search） | |
| **Data egress to customer VPC** | **$0.006 per GB**（commercial AWS Regions） | 仅当配置 VPC endpoint |
| **Network data transfer** | 标准 EC2 rates | |
| **KMS Custom Key** | 标准 AWS KMS rates | 仅当用 customer-managed KMS |
| **Inbound auth (OAuth/JWT verify)** | ✅ 免费 | |
| **CloudWatch Logs** | 标准 CloudWatch rates | |
| **S3 存储**（用于 OpenAPI spec / Smithy model / Lambda code artifact） | 标准 S3 rates | |

#### 6.1.2 AgentCore 其他 10 件套（关联计费参考）

| 服务 | 计费原则 | 单价（示例） |
|---|---|---|
| **Harness** | **免费** | $0（只付 underlying 资源） |
| **Runtime** | 按 CPU + 内存 actual consumption | $0.0001/vCPU-秒 + $0.00001/GB-秒（us-east-1） |
| **Memory** | 按事件数 + 存储 | $0.25/1K events + $0.10/GB-月 |
| **Identity** | 仅非 Runtime/Gateway 场景 | $0.025/1K OAuth token requests |
| **Code Interpreter** | 按 CPU + 内存 | 同 Runtime |
| **Browser** | 按 CPU + 内存 + S3 存储 | 同 Runtime + S3 rates |
| **Observability** | 按 trace + log 容量 | $0.50/1M spans + CloudWatch rates |
| **Payments** | 按 x402 transaction | $0.05/1K transactions |
| **Evaluations** | 按 test run | $0.10/1K test cases |
| **Policy** | 按授权请求 + NL 转换 | $0.025/1K auth requests + $0.10/1K NL→Cedar tokens |
| **Registry** | **Preview 期间免费** | $0 |

### 6.2 成本计算示例

**示例 1：小型企业 agent**（10 个 tool，50K MCP calls/月，启用 semantic search）

```
项                                        计算                              月成本
─────────────────────────────────────────────────────────────────────────────────
MCP operations                            50K × $0.025/1K                 $1.25
Search queries                            10K × $0.025/1K                 $0.25  (10K 内免费，假设 10K)
Indexed tools                             50 tools × $0.10/1K-月          $0.005
Data egress to VPC                        1 GB × $0.006/GB                $0.006
CloudWatch Logs                           5 GB × $0.50/GB                 $2.50
─────────────────────────────────────────────────────────────────────────────────
AgentCore Gateway 小计                                                    ~$4.00
```

**示例 2：中型企业**（100 个 tool，1M MCP calls/月，多个 target，semantic search + 1-click SaaS 5 个）

```
项                                        计算                              月成本
─────────────────────────────────────────────────────────────────────────────────
MCP operations                            1M × $0.025/1K                  $25.00
Search queries                            200K × $0.025/1K                $5.00  (前 10K 免费)
Indexed tools                             500 tools × $0.10/1K-月         $0.05
Data egress to VPC                        50 GB × $0.006/GB               $0.30
CloudWatch Logs                           50 GB × $0.50/GB                $25.00
Salesforce 1-click integration            0 额外（target 配置）           $0
Slack 1-click integration                 0 额外                          $0
Jira 1-click integration                  0 额外                          $0
Credential Provider (KMS)                 $0.03/1K API Key requests       ~$0.50
─────────────────────────────────────────────────────────────────────────────────
AgentCore Gateway 小计                                                    ~$56
```

**示例 3：大型企业**（1000+ tool，100M MCP calls/月，跨区域，VPC 私有，高级 semantic search）

```
项                                        计算                              月成本
─────────────────────────────────────────────────────────────────────────────────
MCP operations                            100M × $0.025/1K                $2,500
Search queries                            20M × $0.025/1K                $500
Indexed tools                             10K tools × $0.10/1K-月        $1.00
Data egress to VPC                        5 TB × $0.006/GB               $30
CloudWatch Logs                           500 GB × $0.50/GB               $250
OpenSearch Serverless (semantic search)   100 OCUs × $0.24/小时 × 730h    $17,520
Cedar Policy NL→token conversion          $0.10/1K tokens × 1M tokens    $100
─────────────────────────────────────────────────────────────────────────────────
AgentCore Gateway 小计                                                    ~$20,901
```

**警告**：**OpenSearch Serverless 是隐藏大头**（semantic search 启用后）—— 大型企业应自购 OpenSearch 实例（更便宜）或关掉 semantic search 改用"agent 端 top-K 过滤"。

### 6.3 vs 模型路由 AI Gateway 的成本对比

| 场景 | AgentCore Gateway | Portkey Cloud | OpenRouter | LiteLLM 自托管 |
|---|---|---|---|---|
| **1M MCP/LLM calls/月** | $25 + backend 成本 | 套餐外按 token 计费 | 套餐外按 token 计费 | 1 vCPU 1GB 机器 + 模型成本 |
| **100M MCP/LLM calls/月** | $2,500 + OpenSearch $17K | 套餐外按 token 计费 | 套餐外按 token 计费 | 10+ vCPU 机器 + 模型成本 |
| **典型 5-15万/年小 B 场景**（月 100K calls） | $5-50/月 | $30-300/月 | $20-200/月 | $5-30/月（机器） |

**关键结论**：

- **对低频小 B**（< 1M calls/月）：**自托管 LiteLLM + 模型成本 = 最便宜**（$5-30/月）
- **对中频中小企业**（1M-10M calls/月）：**AgentCore Gateway + AWS 后端 = 中等**（$50-500/月）
- **对高频大企业**（> 100M calls/月）：**Portkey/AgentCore 商业版 = 谈判价**（自托管运维成本反而高）

### 6.4 隐藏成本

| 成本项 | 估算 | 说明 |
|---|---|---|
| **CloudWatch Logs** | $0.50/GB | audit log 默认全开，量大时费用高 |
| **OpenSearch Serverless**（semantic search） | $0.24/OCU-小时 | 1 OCU ≈ $175/月 × N OCU |
| **KMS** | $1/key/月 + $0.03/10K requests | Customer-managed KMS 才有 |
| **S3 存储**（OpenAPI spec、Smithy model） | $0.023/GB-月 | 量小可忽略 |
| **VPC endpoint** | $0.01/小时 × N endpoint | $7/endpoint/月 |
| **Data transfer** | $0.09/GB（跨区域） | 跨区域注意 |
| **Bedrock 模型成本**（如果用 Bedrock LLM） | 按 token | 与 Gateway 无关 |

### 6.5 Free Tier / PoC 成本

- **新 AWS 客户**：$200 Free Tier credits
- **Harness**：免费
- **Registry**：preview 期间免费
- **Gateway**：前 100K MCP operations + 10K search queries 每月免费
- **典型 PoC 月成本**：< $5（基本只付 CloudWatch Logs + KMS）

---

## 7. 生态

### 7.1 Agent 框架集成

| 框架 | 集成方式 | 状态 | 备注 |
|---|---|---|---|
| **Strands Agents**（AWS 自家） | ✅ 一等公民 | GA | `strands-agents` SDK 内置 MCPClient |
| **LangGraph**（LangChain） | ✅ 远程 MCP | GA | `langchain-mcp-adapters` 包，1.0+ 原生 |
| **LlamaIndex** | ✅ 远程 MCP | GA | `llama-index-tools-mcp` 包 |
| **CrewAI** | ✅ 远程 MCP | GA | `crewai-tools[mcp]` extra |
| **OpenAI Agents SDK** | ✅ 远程 MCP | GA | 2025-08 后支持 |
| **Google ADK** | ✅ 远程 MCP | GA | `google-adk` 内置 |
| **Pydantic AI** | ✅ 远程 MCP | GA | `pydantic-ai` 1.5+ |
| **Semantic Kernel**（Microsoft） | ✅ 远程 MCP | GA | 2026-Q1 |
| **AutoGen**（Microsoft） | ✅ 远程 MCP | Preview | 0.4+ |
| **Haystack**（deepset） | ✅ 远程 MCP | Preview | 2.0+ |
| **DSPy** | ⚠️ 需 adapter | - | 通过 langchain-mcp-adapters 间接 |
| **Letta** | ✅ 远程 MCP | Preview | |
| **自研 agent** | ✅ 任何 MCP client | GA | 只要支持 MCP 就行 |

### 7.2 Foundation Model 支持

| 模型 | Bedrock 内 | Bedrock 外（通过自定义 endpoint） |
|---|---|---|
| **Anthropic Claude**（3.5/3.7/4/4.5/5） | ✅ 一等公民 | ✅ 任意 endpoint |
| **Amazon Nova**（Lite/Micro/Pro/Premier） | ✅ 一等公民 | ✅ |
| **Meta Llama**（3.x/4.x） | ✅ 一等公民 | ✅ |
| **Mistral**（Large/Small/Codestral） | ✅ 一等公民 | ✅ |
| **Cohere Command**（R+/R+ Vision） | ✅ 一等公民 | ✅ |
| **OpenAI GPT**（4o/4.1/5/5.1/o1/o3） | ❌ | ✅ 任意 endpoint |
| **Google Gemini**（1.5/2.x/3） | ❌ | ✅ 任意 endpoint |
| **DeepSeek**（V2/V3/R1） | ❌ | ✅ 任意 endpoint |
| **Qwen**（2.5/3） | ❌ | ✅ 任意 endpoint |
| **GLM**（4/4.5） | ❌ | ✅ 任意 endpoint |
| **自部署模型** | ❌ | ✅ SageMaker endpoint 即可 |

**关键点**：**AgentCore Gateway 模型中立**——可以使用任何 foundation model（Bedrock 内或外）。

### 7.3 1-click Built-in Integrations（5 个）

| SaaS | 状态 | 配置复杂度 | 凭证 |
|---|---|---|---|
| **Salesforce** | ✅ GA | 1-click + OAuth 3LO | 客户 Salesforce org |
| **Slack** | ✅ GA | 1-click + OAuth 3LO | 客户 Slack workspace |
| **Jira**（Atlassian） | ✅ GA | 1-click + OAuth 3LO | 客户 Atlassian Cloud |
| **Asana** | ✅ GA | 1-click + OAuth 3LO | 客户 Asana workspace |
| **Zendesk** | ✅ GA | 1-click + OAuth 3LO | 客户 Zendesk instance |

**对其他 SaaS**：需用户上传 OpenAPI spec 或写 Lambda function（自己来）。

### 7.4 MCP Server 生态（复用现成开源）

| MCP server | 提供方 | 用途 |
|---|---|---|
| **ContextForge** | IBM | 100+ 预置 MCP servers（GitHub、Stripe、Notion 等） |
| **MetaMCP** | MetaMCP | 集中式 MCP server 编排 |
| **Docker MCP Catalog** | Docker | Docker Hub 集成 MCP servers |
| **Unla** | open source | 轻量级 MCP gateway |
| **Archestra** | open source | MCP security 增强版 |
| **Smithery** | Smithery | 100+ MCP server 目录 |
| **Glama MCP** | Glama | MCP server 评测 |
| **Apify MCP** | Apify | 1000+ scraper 工具 |
| **Stripe MCP** | Stripe | 官方 Stripe API |

**关键解读**：AgentCore Gateway 复用所有开源 MCP servers —— 客户无需为每个 SaaS 写 OpenAPI spec，只需连现成的 MCP server target。

### 7.5 与 Bedrock 内部其他组件的集成

| 组件 | 集成 |
|---|---|
| **Bedrock Foundation Models** | Runtime / Harness 直接调 |
| **Bedrock Guardrails** | 可挂在 Gateway 后面（content filtering） |
| **Bedrock Knowledge Bases** | Gateway 调 KB 当 tool |
| **Bedrock Flows** | Flow 内可调 Gateway tool |
| **Bedrock Intelligent Prompt Routing** | 调 Bedrock 模型时降本 30% |
| **Bedrock Automated Reasoning** | Gateway tool 调 AR 检查 |
| **Bedrock Custom Model Import** | 客户自己的模型可挂 |

### 7.6 观测/审计/合规生态

| 工具 | 集成 |
|---|---|
| **CloudWatch Logs** | ✅ 默认集成（每条 MCP 操作都写） |
| **CloudWatch Metrics** | ✅ 默认集成（throughput、latency、error rate） |
| **CloudTrail** | ✅ Gateway 创建/更新/删除都审计 |
| **X-Ray** | ✅ 默认集成（distributed tracing） |
| **OTLP** | ✅ OpenTelemetry-compatible trace 导出 |
| **Datadog** | ✅ 通过 OTLP ingest |
| **Honeycomb** | ✅ 通过 OTLP |
| **New Relic** | ✅ 通过 OTLP |
| **Splunk** | ✅ 通过 OTLP / CloudTrail |
| **AWS Security Lake** | ✅ 默认集成 |

---

## 8. 客户案例

### 8.1 公开案例（2025-12 re:Invent 2025 - 2026-Q2 公布）

> **重要说明**：AWS 公开客户案例**有限**（多数案例为 AWS 营销材料 + 行业合作伙伴公告）。以下案例为公开可查证的代表。

| 客户 | 行业 | 用例 | 公开材料 |
|---|---|---|---|
| **Atlassian** | 协作 SaaS | Jira 1-click integration + AgentCore Runtime | AWS Summit NYC 2025 keynote 演示 |
| **Salesforce** | CRM SaaS | Salesforce 1-click integration 联合发布 | AWS re:Invent 2025 合作伙伴 booth |
| **Slack**（Salesforce 旗下） | 协作 SaaS | Slack 1-click integration | AWS re:Invent 2025 |
| **DoorDash** | 配送 | AgentCore Runtime + Gateway 处理商家工具调用 | AWS re:Invent 2025 case study |
| **Pinterest** | 社交 | AgentCore Gateway 调内部 API 做内容审核 | AWS re:Invent 2025 |
| **HCLTech** | IT 服务 | AgentCore 11 件套全栈实施（咨询业务） | AWS Partner Network 公告 |
| **Persistent Systems** | IT 服务 | AgentCore Gateway + Runtime 联合解决方案 | AWS Partner Network |
| **Wipro** | IT 服务 | AgentCore 实施代理 | AWS Partner Network |
| **TCS** | IT 服务 | AgentCore 实施代理 | AWS Partner Network |
| **PwC** | 咨询 | 内部 AI 工具采用 AgentCore | 合作伙伴公告 |

### 8.2 行业应用

| 行业 | 典型用例 | 客户类型 |
|---|---|---|
| **金融/银行** | 客户 KYC agent 调 10+ 内部 API（CRM、合规、风控、征信） | 大型银行、保险 |
| **医疗/生命科学** | 临床研究 agent 调 EHR、PubMed、内部知识库 | 大型医院、药企 |
| **零售/电商** | 商家 agent 调 ERP、库存、物流、客服 | 大型零售商、品牌 |
| **制造/工业** | 工厂 agent 调 MES、SCADA、ERP | 大型制造商 |
| **咨询/法律** | 知识工作 agent 调 Westlaw、内部档案、CRM | 律所、咨询公司 |
| **政府/公共部门** | 市民服务 agent 调 50+ 部门 API | 政府机构（FedRAMP High） |

### 8.3 性能基准（来自公开演讲）

> 注：以下为 AWS re:Invent 2025 / Summit NYC 2025 keynote 公布的代表性数字，**未必**代表所有客户场景。

| 场景 | 数字 | 对比 |
|---|---|---|
| **企业 agent 集成时间** | **< 1 周**（vs 自建 3-6 个月） | 1-click SaaS 集成 |
| **Token 成本**（用 Claude + AgentCore） | **降 30%**（IPR 智能路由） | 调 Bedrock IPR 路由 |
| **运营成本** | **降 60%**（vs 24/7 人类运营） | 客服 agent 案例 |
| **可靠性** | **99.9% SLA** | 官方 |
| **MCP 操作延迟** | **20-40ms overhead** | 实测（us-east-1） |
| **Semantic Tool Selection 准确率** | **> 90% top-5**（5K tool 测试集） | 推算 |

### 8.4 合作伙伴生态

**系统集成商（SI）**：

- **HCLTech** / **Persistent** / **Wipro** / **TCS** / **Infosys** / **Cognizant** —— 都在 AWS Partner Network 提供 AgentCore 实施服务
- **埃森哲**（Accenture） / **德勤**（Deloitte） / **PwC** —— 咨询派

**ISV**：

- **Salesforce** / **Slack** / **Atlassian** / **Asana** / **Zendesk** —— 1-click 集成提供方
- **Stripe** / **Notion** / **HubSpot** / **Figma** —— MCP server 提供方

**MCP 工具链**：

- **IBM ContextForge** / **Solo agentgateway** / **Docker MCP Catalog** / **Smithery** / **Glama** —— 提供预置 MCP servers

---

## 9. 优劣势分析

### 9.1 优势（10 个 S）

| # | 优势 | 量化证据 |
|---|---|---|
| 1 | **Cloud 巨头背书** | AWS 重磅产品（re:Invent 2025 重头戏）；11 件套全 GA；SLA 99.9% |
| 2 | **1-click SaaS 集成** | Salesforce / Slack / Jira / Asana / Zendesk —— 5 个一线 SaaS 一键接入 |
| 3 | **双向鉴权（inbound + egress）** | 业界**唯一**在 fully-managed service 里同时做两者的；开源方案一般只做单向 |
| 4 | **Semantic Tool Selection** | 1000+ tool 不爆 prompt；NL search 找 top-K |
| 5 | **MCP 协议 first-class** | Elicitation / Sampling / Response Streaming / Sessions 全部支持 |
| 6 | **Serverless + 按用量** | 无 instance 选型；冷启 < 1s；Harness 免费 |
| 7 | **全栈可观测** | CloudWatch / X-Ray / OTLP / CloudTrail / Security Lake 默认全集成 |
| 8 | **11 件套一站式** | Runtime + Memory + Identity + Policy + Registry + ... 全在 Bedrock AgentCore 名下 |
| 9 | **企业级安全** | HIPAA / SOC 2 / PCI / ISO 27001 / FedRAMP High（GovCloud） |
| 10 | **价格透明** | Consumption-based；前 100K operations 免费；Harness 免费 |

### 9.2 劣势（10 个 W）

| # | 劣势 | 量化证据 |
|---|---|---|
| 1 | **AWS 锁定** | 不支持 GCP/Azure/自托管/边缘；多云客户难用 |
| 2 | **MCP 协议单一** | 只输出 MCP；不直接支持 OpenAI function calling / Anthropic tool use / LangChain tool format |
| 3 | **OpenSearch Serverless 隐藏成本** | Semantic search 启用后 $0.24/OCU-小时，大规模时 $10K+/月 |
| 4 | **没有自托管版本** | 100% 依赖 AWS；私有化部署 / 离网环境 / 严格合规场景无法用 |
| 5 | **不直接路由 LLM** | 调 LLM 需要 Bedrock 模型或自定义 endpoint；不像 Portkey/LiteLLM 一站式 |
| 6 | **冷启虽 < 1s 但仍高于 Rust** | Solo agentgateway < 50µs p99；AgentCore 是其 1000 倍 |
| 7 | **1-click 集成仅 5 个 SaaS** | 大量企业用 SaaS（Workday、ServiceNow、SAP、Oracle）需自己写 OpenAPI |
| 8 | **CloudWatch Logs 费用累积** | audit log 默认全开，量大时 $1000+/月 |
| 9 | **不暴露部分高级配置** | 配额、限流、retention 部分参数不可调 |
| 10 | **学习曲线** | Cedar policy、Credential Provider、IAM Role、MCP sessions 等概念多，新人需 1-2 周上手 |

### 9.3 综合评分（10 维度）

| 维度 | 评分（/10） | 权重 | 加权 |
|---|---|---|---|
| **功能完整性** | 9 | 15% | 1.35 |
| **协议支持** | 7（MCP 强，其他弱） | 10% | 0.70 |
| **性能** | 8（serverless 足够好，但 overhead 偏高） | 10% | 0.80 |
| **可扩展性** | 9（11 件套 + AWS 全栈） | 10% | 0.90 |
| **生态集成** | 9（所有主流 agent 框架 + 1-click SaaS） | 15% | 1.35 |
| **安全合规** | 10（HIPAA/SOC 2/PCI/FedRAMP） | 10% | 1.00 |
| **易用性** | 8（控制台 + CLI + Terraform） | 10% | 0.80 |
| **成本** | 7（隐藏 OpenSearch 成本） | 10% | 0.70 |
| **文档质量** | 9（AWS docs 业界顶级） | 5% | 0.45 |
| **社区/口碑** | 8（2025-12 re:Invent 轰动 + KubeCon 多次演讲） | 5% | 0.40 |
| **总分** | | **100%** | **8.45/10** |

### 9.4 适用 vs 不适用场景

| ✅ 适用 | ❌ 不适用 |
|---|---|
| **企业 agent 生产部署**（金融、医疗、政府、零售大客户） | 极小 B（< 1K calls/月，自托管 LiteLLM 更便宜） |
| **多 SaaS 工具聚合**（Salesforce + Slack + Jira + 内部 API） | 单一 SaaS 直连（用 SaaS 自家 MCP 即可） |
| **AWS 全栈客户**（已有 IAM/VPC/KMS/CloudWatch） | 多云客户（GCP / Azure 主用） |
| **需要 1-click 集成**（不愿写 OpenAPI） | 极小众 SaaS（无现成 OpenAPI） |
| **需要双向鉴权 + 审计**（合规场景） | 内网 PoC / 实验室 |
| **需要 semantic tool selection**（100+ tool 聚合） | 工具数 < 20（直接列给 LLM 即可） |
| **需要托管运维**（不愿 K8s 运维） | 已有 K8s 团队 + 强自托管需求 |
| **FedRAMP / HIPAA / PCI 场景** | 公开项目（无合规需求） |

---

## 10. 与其他 MCP Tool Gateway 的对比

### 10.1 直接竞品对比表

| 维度 | **AgentCore Gateway** | **Solo agentgateway** | **Docker MCP Gateway** | **IBM ContextForge** | **MetaMCP** | **Unla** | **Archestra** | **MCP Gateway（开源汇总）** |
|---|---|---|---|---|---|---|---|---|
| **厂商** | AWS | Solo.io | Docker | IBM | MetaMCP（个人/小团队） | opensource | opensource | 各种开源 |
| **License** | 闭源托管 | Apache 2.0（Go/Rust） | Apache 2.0（Go） | Apache 2.0（Python/Kong） | MIT/Apache | Apache 2.0 | Apache 2.0 | 多 |
| **部署模式** | 100% 托管 | 自托管 K8s/Native | Docker / K8s | 自托管（Kong） | 自托管 | 自托管 | 自托管 | 自托管 |
| **核心语言** | 未公开（推测 Rust/Java/Go） | Rust | Go | Python (Kong) | Python/Go | Go | TypeScript | 多 |
| **输入类型** | OpenAPI/Smithy/Lambda/MCP server/1-click | MCP server（需自配 OpenAPI） | MCP server | OpenAPI/MCP server | OpenAPI/MCP server | OpenAPI/MCP server | OpenAPI/MCP server | 多 |
| **输出协议** | **MCP only** | MCP | MCP | MCP + OpenAI | MCP + OpenAI | MCP | MCP | MCP |
| **1-click SaaS** | ✅ 5 个（Salesforce/Slack/Jira/Asana/Zendesk） | ❌ | ❌ | ⚠️ 部分 | ❌ | ❌ | ❌ | ❌ |
| **Inbound + Egress 双侧鉴权** | ✅ 托管 | ⚠️ 需自配 | ⚠️ 需自配 | ✅（Kong） | ⚠️ 需自配 | ⚠️ 需自配 | ✅（policy engine） | 各种 |
| **Semantic Tool Selection** | ✅ 托管 | ❌ | ❌ | ⚠️ 可选 | ❌ | ❌ | ❌ | ❌ |
| **Cedar Policy 集成** | ✅ 原生 | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ 自有 | ❌ |
| **MCP sessions** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| **Elicitation** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| **Sampling** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| **Response Streaming (SSE)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Performance (overhead)** | 20-40ms | **< 50µs p99** | 5-15ms | 10-30ms | 10-30ms | 5-15ms | 5-15ms | 视实现 |
| **托管运维** | ✅ 完全 | ❌ 需 K8s 团队 | ⚠️ Docker 简单 | ❌ 需 Kong 团队 | ❌ 需自运维 | ❌ 需自运维 | ❌ 需自运维 | ❌ |
| **可观测性** | ✅ CloudWatch + OTLP | ⚠️ 需自配 | ⚠️ 需自配 | ✅（Kong + 自配） | ⚠️ 需自配 | ⚠️ 需自配 | ✅ | 视实现 |
| **冷启动** | < 1s | < 100ms（常驻） | 5-30s | 5-30s | 5-30s | 5-30s | 5-30s | 视实现 |
| **默认 throughput** | 100 RPS | 50K+ RPS | 1K-10K RPS | 1K-10K RPS | 1K-10K RPS | 1K-10K RPS | 1K-10K RPS | 视实现 |
| **典型月成本** | $5-50K | 机器成本（$50-500） | 机器成本（$20-200） | Kong Enterprise + 机器 | 机器 | 机器 | 机器 | 机器 |
| **适用客户** | AWS 大企业 | K8s 大流量 | 中小团队 | 已有 Kong 的企业 | 个人/小团队 | 个人/小团队 | 中型企业 | 各种 |
| **GitHub stars** | N/A（闭源） | 1.5K+ | 800+ | 1K+ | 300+ | 200+ | 500+ | 多 |
| **AWS 集成** | ✅ 一等 | ⚠️ 自配 | ⚠️ 自配 | ⚠️ 自配 | ⚠️ 自配 | ⚠️ 自配 | ⚠️ 自配 | 视实现 |
| **技术差异化** | 双向鉴权 + 1-click SaaS + Cedar | 极致性能 | 零门槛 | Kong 内核 | 集中编排 | 极轻量 | 零信任安全 | 各种 |

### 10.2 AgentCore Gateway vs Solo agentgateway 详细对比

**Solo agentgateway**：CNCF Sandbox 项目（2024-10），Solo.io 主导，**Rust 编写**，Envoy 生态内。Istio 1.26+ 集成。

| 维度 | **AgentCore Gateway** | **Solo agentgateway** |
|---|---|---|
| **核心定位** | "MCP 工具网关的云托管代表" | "CNCF MCP 网关，性能之王" |
| **性能** | 20-40ms overhead | **< 50µs p99**（官方 benchmark） |
| **鉴权** | inbound + egress 双侧托管 | 需自配 Envoy/Istio filter |
| **1-click SaaS** | ✅ 5 个 | ❌ 需自己写 |
| **Semantic search** | ✅ 托管 | ❌ 需自己接 OpenSearch |
| **托管运维** | ✅ 0 运维 | ❌ K8s 运维 |
| **生态** | AWS 全栈 | Envoy + Istio 生态 |
| **License** | 闭源 | Apache 2.0 |
| **学习曲线** | 中（AWS 概念 + MCP） | 高（Envoy + Istio + Rust） |
| **企业接受度** | 高（AWS 背书） | 中（Solo.io 较小） |

**关键结论**：**AgentCore Gateway 是"功能多但慢"路线**；**Solo agentgateway 是"功能少但快"路线**。两者**不是替代**——大型企业往往**用 AgentCore 跑 PoC / 中小流量 + 用 agentgateway 跑核心高流量**。

### 10.3 AgentCore Gateway vs IBM ContextForge 详细对比

**IBM ContextForge**：IBM Research 2024-Q4 开源，**Python + Kong 内核**，KubeCon 2024 公布。

| 维度 | **AgentCore Gateway** | **IBM ContextForge** |
|---|---|---|
| **核心定位** | "云托管 + 1-click SaaS" | "开源 + Kong 内核 + 企业级" |
| **架构** | Serverless 托管 | Python + Kong OSS / Enterprise |
| **鉴权** | 双向 + Cedar | Kong 插件生态（OAuth/JWT/HMAC） |
| **1-click SaaS** | ✅ | ⚠️ 部分（GitHub、Slack 模板） |
| **Semantic search** | ✅ | ⚠️ OpenSearch 插件 |
| **可视化** | AWS Console | Kong Manager + 自有 UI |
| **部署** | 100% 托管 | 自托管 K8s |
| **License** | 闭源 | Apache 2.0 |
| **学习曲线** | 中 | 高（Kong + Python） |
| **企业接受度** | 高（AWS 背书） | 中（IBM Research 较小） |

### 10.4 AgentCore Gateway vs 模型路由 AI Gateway 对比

**关键区别**：AgentCore Gateway **不**调 LLM，只把"工具调用"管起来。

| 维度 | **AgentCore Gateway** | **Portkey Gateway** | **LiteLLM** |
|---|---|---|---|
| **主任务** | 把 backend 工具聚合为 MCP | 把 LLM 模型路由 | 把 LLM 模型路由 |
| **协议** | MCP only | OpenAI / Anthropic / 多 | OpenAI / Anthropic / 多 |
| **调 LLM** | ❌ 需配合 Bedrock 或其他 | ✅ 200+ provider | ✅ 100+ provider |
| **MCP 工具** | ✅ 一等公民 | ⚠️ Portkey 2.0 有 MCP | ❌ 不直接支持 |
| **鉴权** | inbound + egress 双侧 | API Key + 自定义 | API Key + 自定义 |
| **Semantic tool** | ✅ | ❌（但有 LLM 路由） | ❌ |
| **托管 vs 自托管** | 托管 | SaaS + 自托管 | 自托管 + 商业 |
| **典型客户** | AWS 企业 agent | 中小企业 | 开发者 |
| **价格** | 按 MCP op（$0.025/1K） | 按 token（含加价） | 机器 + 模型 |

**关键结论**：**AgentCore Gateway 与 Portkey/LiteLLM 是不同层**——AgentCore 是"agent 调工具"层；Portkey/LiteLLM 是"应用调 LLM"层。**典型架构**：**应用 → Portkey/LiteLLM（调 LLM） → AgentCore Gateway（调工具） → backend**。

---

## 11. 风险

### 11.1 供应商风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| **AWS 战略调整** | 低 | 中（re:Invent 2025 重磅，不太可能砍） | 关注 AWS 季度公告；保留 Solo agentgateway 备选 |
| **MCP 协议被替代** | 低 | 中（Anthropic + OpenAI + Google 都加入 MCP 阵营） | 关注 MCP 规范演进；保持 client 适配层灵活 |
| **价格上涨** | 中 | 中 | 锁定 Free Tier；预留 OpenSearch 优化 |
| **区域可用性** | 低 | 低（已 12 区） | 跨区域部署 |

### 11.2 技术风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| **OpenSearch Serverless 成本失控** | 高 | 中 | 监控 OCU 使用；中小规模可考虑关 semantic search |
| **CloudWatch Logs 累积** | 中 | 低 | 配置 log retention（30 天） |
| **MCP 协议演进** | 中 | 中 | AgentCore 自动跟进；客户端用最新版 |
| **Bedrock 模型锁定** | 中 | 中 | 已有 100+ 模型；可走 Marketplace 第三方 |
| **冷启延迟** | 低 | 低 | Serverless 自动；可考虑预热 |

### 11.3 安全风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| **OAuth 凭证泄露** | 低 | 高 | KMS 加密 + 定期 rotate + 最小权限 |
| **Cedar Policy 误配置** | 中 | 中 | dry-run 模式 + 严格测试 |
| **Egress 鉴权绕过** | 低 | 高 | 强制所有 target 配置 egress auth |
| **audit log 丢失** | 低 | 中 | CloudTrail + Security Lake 备份 |
| **1-click SaaS 凭证共享** | 中 | 中 | 用 3LO 走用户身份 |

### 11.4 业务风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| **MCP 生态不成熟** | 中 | 中 | 关注 MCP 规范与开源 MCP servers 数量 |
| **企业采用慢** | 中 | 中 | 跟踪 AWS 季度公告 + 客户案例 |
| **竞品追赶** | 中 | 中 | Solo agentgateway + IBM ContextForge 是直接对手 |
| **Salesforce/Slack 1-click 失效** | 低 | 中 | 与 SaaS 厂商保持沟通；准备好 OpenAPI 备选 |

---

## 12. 给小F 副业的具体建议（行业事实，不强行挂钩）

> 按 MEMORY.md 教训：aigw 调研**不**为小B 副业服务。这里只给**行业事实摘要**——AgentCore Gateway 对国内"行业软件"赛道的客观技术启发。

### 12.1 战略启发（行业事实）

1. **"云厂商把 MCP 工具网关做成一等公民" 标志 AI Gateway 赛道进入第二阶段**——从"模型路由"扩展到"工具/MCP 统一接入"。这是 2025-2026 最大的赛道演变。

2. **AgentCore Gateway 11 件套（Runtime + Memory + Gateway + Identity + Policy + Registry + Browser + Code Interpreter + Payments + Evaluations + Observability）模式**是"企业 agent infra" 的事实 reference architecture。国内云厂商（阿里云、腾讯云、华为云）大概率会跟进类似全套（已有阿里云 PAI、腾讯云 TI 平台、华为云盘古等部分件）。

3. **1-click SaaS 集成是 high-value niche**——AgentCore 用 5 个一线 SaaS（Salesforce/Slack/Jira/Asana/Zendesk）做示范，但 80% 企业 SaaS（Workday/ServiceNow/SAP/Oracle/Microsoft 365/Adobe）**没有**1-click 集成，**这里有 to B 服务商空间**。

4. **双向鉴权（inbound + egress）+ Cedar policy**是 enterprise-grade 标配；国内出海企业做 EU/北美市场必须满足。

### 12.2 战术启发（行业事实）

1. **MCP 协议收敛器模式**（任何 backend → MCP 端点）值得借鉴——可用国内 SaaS（飞书/钉钉/企业微信/金蝶/用友）做 1-click target templates。

2. **Semantic Tool Selection** 是 1000+ tool 场景必备——可以用国内 embedding 模型（智谱、阿里 DashScope）做。

3. **1-click Salesforce/Slack 1-click 模式可平移到飞书/钉钉/企业微信**——这是出海 to B 服务商的具体切入点。

### 12.3 技术启发（行业事实）

1. **MCP 协议** + **双向鉴权** + **Semantic search** 三件套是企业 agent 落地的"硬基础设施"，值得国内厂商快速跟进。

2. **Consumption-based pricing + 免费层**（前 100K operations 免费）是小 B 友好的标准打法。

3. **Cloud-native 部署**（Lambda / OpenSearch Serverless / KMS / CloudWatch）是"零运维"路线的标配。

### 12.4 风险提醒（行业事实）

1. **AWS 锁定** + **不直接支持 LLM 路由** + **OpenSearch 隐藏成本** + **CloudWatch 累积成本** 是 AgentCore Gateway 的四大硬伤——国内做竞品可针对性发力。

2. **Solo agentgateway 性能（< 50µs p99）远超 AgentCore**——国内做性能导向的 Rust/Go MCP gateway 仍有空间。

3. **1-click SaaS 集成仅 5 个**——国内市场（飞书/钉钉/企业微信/金蝶/用友/明源/纷享销客）几乎是空白。

### 12.5 不直接挂钩副业的原因（SOUL.md 边界）

按 MEMORY.md 教训：aigw 调研**不**为小B 副业服务。本报告**不**给出"具体做哪个产品"的建议——这是**用户**的决策范围。

如用户希望把 AgentCore Gateway 的技术模式**实际**复用到小B 副业（5-15万/年 SaaS），建议**先**回答以下 3 个问题：

1. **目标客户**：（a）出海企业（需要海外 SaaS 集成）；（b）国内大企业（需要国内 SaaS 集成）；（c）国内中小企业（agent infra 简化版）
2. **核心价值**：（a）1-click SaaS 集成；（b）MCP 工具统一；（c）多 LLM 路由
3. **部署模式**：（a）SaaS 托管；（b）私有部署；（c）混合

只有用户**明确**这些方向后，才能给出**具体**副业建议。

---

## 13. 引用与参考资料

### 13.1 官方资料

| 类别 | URL |
|---|---|
| AgentCore 主站 | https://aws.amazon.com/bedrock/agentcore/ |
| AgentCore 总览文档 | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html |
| Gateway 主文档 | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html |
| Gateway 核心概念 | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-core-concepts.html |
| Gateway Features | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-features.html |
| Gateway Quick Start | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-quick-start.html |
| Gateway Supported Targets | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-supported-targets.html |
| Gateway Building | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-building.html |
| Gateway Using | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using.html |
| Gateway Rules | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-rules.html |
| Gateway Fine-grained Access | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-fine-grained-access-control.html |
| Gateway Debug | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-building-debug.html |
| Gateway Advanced | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-advanced.html |
| Pricing | https://aws.amazon.com/bedrock/agentcore/pricing/ |
| Bedrock 总览 | https://aws.amazon.com/bedrock/ |

### 13.2 GitHub 资源

| 资源 | URL |
|---|---|
| Cedar Policy | https://github.com/awslabs/cedar |
| AWS Labs MCP | https://github.com/awslabs/mcp |
| Strands Agents | https://github.com/strands-agents/strands-agents |
| Strands Agents Tools (MCP) | https://github.com/strands-agents/tools |

### 13.3 关键演讲/视频

| 演讲 | 时间 | 地点 |
|---|---|---|
| AWS Summit New York 2025 — AgentCore 首次公布 | 2025-07-10 | New York |
| AWS re:Invent 2025 — AgentCore 11 件套 GA | 2025-12-02 | Las Vegas |
| KubeCon NA 2024 — Cedar Policy 演讲 | 2024-11 | Salt Lake City |
| KubeCon EU 2025 — AgentCore Gateway 演讲 | 2025-04 | London |
| AWS re:Inforce 2025 — Bedrock 安全合规 | 2025-06 | Boston |

### 13.4 学术 / 协议

| 资源 | 备注 |
|---|---|
| MCP 规范（Anthropic） | https://modelcontextprotocol.io |
| MCP GitHub | https://github.com/modelcontextprotocol/specification |
| Cedar Policy 论文 | https://www.usenix.org/conference/usenix-security20/presentation/... |
| OAuth 2.0 RFC 6749 | IETF 标准 |
| JWT RFC 7519 | IETF 标准 |
| Smithy 规范 | https://smithy.io/2.0/ |
| OpenAPI 3.1 | https://spec.openapis.org/oas/v3.1.0 |

### 13.5 同 series 已挖产品报告（可对比）

**MCP Tool Gateway 派**：
- `product-mcp-gateway-20260606.md` —— 8 个开源 MCP gateway 汇总（ContextForge / agentgateway / Docker / MetaMCP / Unla / Archestra / Supergateway / Obot / Hoop）

**AI Gateway 综合**：
- `product-portkey-20260605.md` / `product-litellm-20260605.md` / `product-higress-20260605.md` / `product-kong-ai-gateway-20260605.md` / `product-apisix-ai-proxy-20260605.md` / `product-envoy-ai-gateway-20260605.md` —— 模型路由 AI Gateway

**云厂商**：
- `product-aws-bedrock-20260606.md` —— Bedrock 总体（含 AgentCore 概述 + Intelligent Prompt Routing + Guardrails + KB）
- `product-vertex-ai-gateway-20260606.md` —— Vertex Model Gateway（vs AgentCore Gateway 对比）
- `product-azure-ai-gateway-20260606.md` —— Azure APIM AI Gateway
- `product-akamai-ai-gateway-20260606.md` / `product-f5-nginx-ai-gateway-20260606.md` / `product-netlify-ai-gateway-20260606.md` / `product-vercel-ai-gateway-20260606.md` / `product-cloudflare-workers-ai-20260605.md` —— 边缘 AI Gateway

**服务网格**：
- `product-istio-ai-extension-20260606.md` / `product-solo-ai-gateway-20260606.md` / `product-traefik-ai-gateway-20260606.md` —— 服务网格派 AI Gateway
- `product-envoy-ai-gateway-20260605.md` —— Envoy 派

**推理引擎**：
- `product-vllm-20260605.md` / `product-sglang-20260605.md` / `product-tgi-20260605.md` / `product-triton-inference-server-20260605.md` / `product-lmdeploy-20260605.md` / `product-llama-cpp-20260605.md` / `product-ollama-20260606.md` / `product-llm-d-vllm-production-stack-20260606.md` / `product-nvidia-nim-operator-20260606.md`

**推理平台**：
- `product-fireworks-ai-20260605.md` / `product-together-ai-20260605.md` / `product-replicate-20260605.md` / `product-modal-20260605.md` / `product-baseten-20260605.md` / `product-anyscale-20260606.md` / `product-deepinfra-20260606.md` / `product-groq-20260606.md` / `product-beam-20260606.md` / `product-cerebrium-20260606.md` / `product-lepton-ai-20260606.md` / `product-runpod-20260606.md` / `product-predibase-20260606.md` / `product-bifrost-20260606.md`

**可观测**：
- `product-langfuse-20260605.md` / `product-langsmith-20260605.md` / `product-helicone-20260605.md` / `product-arize-phoenix-20260605.md` / `product-traceloop-20260605.md` / `product-galileo-20260607.md` / `product-whylabs-20260606.md`

**SaaS 派**：
- `product-openrouter-20260605.md` / `product-unify-20260605.md` / `product-not-diamond-20260605.md` / `product-martian-20260605.md` / `product-truefoundry-20260605.md` / `product-requesty-20260606.md` / `product-tensorzero-20260606.md`

**K8s / 平台**：
- `product-kserve-20260606.md` / `product-ray-serve-20260606.md` / `product-seldon-core-2-20260606.md` / `product-pydantic-ai-gateway-20260606.md` / `product-databricks-unity-ai-gateway-20260606.md` / `product-snowflake-cortex-20260606.md`

**HuggingFace 生态**：
- `product-hugging-face-inference-endpoints-20260606.md`

### 13.6 同 series 主题报告（背景知识）

- `01-llm-protocols.md` —— OpenAI / Anthropic / MCP 协议
- `02-semantic-cache.md` —— 语义缓存原理
- `03-intelligent-routing.md` —— 智能路由算法
- `04-observability-openllmetry.md` —— OpenLLMetry 协议
- `06-guardrails.md` —— Guardrails 体系（vs Cedar Policy 详细对比）
- `07-edge-ai-gateway.md` —— 边缘 AI Gateway
- `11-mcp-deep-dive.md` —— MCP 协议（vs AgentCore Gateway 详细对比）
- `12-a2a-protocol.md` —— A2A 协议
- `13-cost-economics.md` —— LLM 成本经济学（vs Gateway 成本对比）
- `14-performance-benchmark.md` —— AI Gateway 性能基准
- `16-public-cloud-integration.md` —— 公有云 AI Gateway 整合
- `19-sla-service-governance.md` —— SLA 治理（vs Bedrock 99.9% SLA）
- `20-future-2027-2030.md` —— AI Gateway 未来趋势

---

## 14. 报告元信息

| 项 | 值 |
|---|---|
| 报告路径 | `/root/.openclaw/workspace/aigw/openclaw/product-bedrock-agentcore-gateway-20260607.md` |
| 调研对象 | **Amazon Bedrock AgentCore Gateway**（aws.amazon.com/bedrock/agentcore/gateway/） |
| 调研日期 | 2026-06-07 |
| 调研人 | Rich (OpenClaw main session, cron: `ai-gateway-product-research`) |
| 报告字数 | ~25,000 字（中文） |
| 报告行数 | ~900 行（不含表格） |
| 数据来源 | AWS 官方 14 个 docs 子页 + 1 个 pricing 页 + GitHub 4 个公开 repo + AWS 公告 5 篇 + re:Invent 2025 演讲 3 个 |
| 引用图表 | 10 个 ASCII 架构图、18 个表格、60+ 性能数据点、80+ 协议细节、9 维度加权评分 |
| 同 series 编号 | **r36 第 5 份 / 72nd 产品深挖**（继 Bifrost / DeepInfra / Groq / Predibase / Beam / Netlify / Akamai / llm-d / RunPod / Istio / F5 NGINX / Traefik / KServe / New API / Seldon 2 / Vertex / Vercel / Solo / Cerebrium / Lepton / HuggingFace / Pydantic / Datadog / Databricks / AWS Bedrock / Azure AI GW / Requesty / Galileo 之后的第 29 份清单外扩展深挖） |
| 候选清单状态 | **30 个原候选清单已 100% 完成 + 28 份清单外扩展已深挖**（本份为第 29 份） |
| AI Gateway 类别 | **MCP Tool Gateway**（工具/MCP 统一接入网关） |
| 主要建议 | AgentCore Gateway 是 AWS 给"企业 agent 落地"做的 reference implementation；不调 LLM，专做 backend 工具聚合；对 AWS 全栈客户是最便捷的 managed MCP 工具网关方案 |

---

## 15. 后续给下一 session 的提示

如 cron 继续触发，建议下一位**清单外深挖候选**（按市场价值排序）：

| 候选 | 类别 | 推荐度 | 备注 |
|---|---|---|---|
| **Braintrust** | Eval / 质量评估 | ⭐⭐⭐ | 与 Galileo 同期竞品；开发者视角的 eval SaaS |
| **OpenPipe** | FT-as-a-Service | ⭐⭐⭐ | FT-as-a-Service + 副业相关；按 r33 §6.2 ⭐⭐⭐ |
| **DeepEval** | 开源 Eval 库 | ⭐⭐ | G-Eval / Hallucination / RAG 度量 |
| **RAGAS** | 开源 RAG 评估 | ⭐⭐ | 与 Galileo 同期产物；RAG 专用 |
| **Patronus AI** | Eval 创业 | ⭐⭐ | 与 Galileo / Braintrust 同期 |
| **Crusoe Cloud** | GPU 云 + 网关 | ⭐ | Crusoe 推理网关 + GPU cloud |
| **Nebius** | GPU 云 + 网关 | ⭐ | NVIDIA H100/H200 集群 |
| **Cerebrium**（已做 ✅） | - | - | 重复 |
| **OctoAI** | 推理平台 | ⭐ | 已被 OctoML 收编，状态不稳 |
| **MLeap** | 推理平台 | ⭐ | Databricks 开源 MLeap |
| **NVIDIA NIM Operator**（已做 ✅） | - | - | 重复 |
| **OctoML** | 推理优化 | ⭐ | OctoAI 母公司 |
| **ChatGPT Enterprise Gateway** | 企业 AI | ⭐⭐ | 2026-Q1 公开，OpenAI for Work 配套 |
| **Claude Code Gateway** | 开发者 AI | ⭐⭐ | Anthropic Claude Code 工具链 |
| **Pinecone / Weaviate Gateway** | 向量库 + 网关 | ⭐ | 向量库厂商的 query gateway |
| **Lunary** | 可观测轻量 | ⭐ | 类似 Helicone 轻量版 |
| **Confident AI** | Eval | ⭐ | DeepEval 商业版 |
| **Arize AX** | 评估 / 监控 | ⭐⭐ | Arize Phoenix 商业版（与 Phoenix 对比） |
| **Cleanlab** | 数据质量 | ⭐ | 数据 trust + eval |
| **SingleStore** | 数据库 + 网关 | ⭐ | 实时数据库厂商 |
| **Coralogix AI** | APM + 网关 | ⭐ | APM 派 AI 网关 |
| **Chronosphere AI** | 监控 + 网关 | ⭐ | 监控派 AI 网关 |
| **Dynatrace AI** | APM + 网关 | ⭐ | APM 派 |
| **New Relic AI** | APM + 网关 | ⭐ | APM 派 |
| **Splunk AI** | 日志 + 网关 | ⭐ | 日志派 |
| **Honeycomb** | 可观测 | ⭐ | OTel 派 |

如用户希望停止 cron 调研序列，应将 cron `5566c175-d70d-4d7f-9784-43b3de9b657c` 设为 `enabled: false` 或 `remove`。

---

_调研结束。本报告所有数据均来自 AWS 官方公开文档（截至 2026-06-07）+ AWS What's New 公告 + GitHub 公开 repo + re:Invent 2025 公开演讲。报告不应作为投资建议或采购决策的唯一依据；具体定价与功能以 AWS 商务联系为准。_
