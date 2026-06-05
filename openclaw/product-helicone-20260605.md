# Helicone 深度调研（2026-06）

> 系列：AI Gateway 单产品深挖 · 第 N 篇
> 目标项目：[Helicone / helicone](https://github.com/Helicone/helicone)
> 调研日期：2026-06-05
> 性质：单产品深挖（覆盖项目背景、架构、协议、性能、部署、成本、生态、案例、对比）
> 信息来源：Helicone 官方文档（docs.helicone.ai）、GitHub README、Helicone Pricing 页面、Mintlify 收购公告（2025-11）、Helicone 官方博客、既往 00-20 系列报告中的相关章节

---

## 目录

- [〇、最重要的前置事实：Helicone 已被 Mintlify 收购（2025-11）](#〇最重要的前置事实helicone-已被-mintlify-收购2025-11)
- [一、项目速览与定位](#一项目速览与定位)
- [二、项目背景与公司](#二项目背景与公司)
- [三、架构设计：六服务边缘架构](#三架构设计六服务边缘架构)
- [四、协议支持：OpenAI 兼容 + 多 Provider 翻译层](#四协议支持openai-兼容--多-provider-翻译层)
- [五、AI Gateway 与 Provider Routing](#五ai-gateway-与-provider-routing)
- [六、Sessions：面向 Agent 的多步追踪](#六sessions面向-agent-的多步追踪)
- [七、缓存体系：边缘缓存 + Provider Prompt Cache 双层](#七缓存体系边缘缓存--provider-prompt-cache-双层)
- [八、LLM Security：内置护栏（Prompt Guard + Llama Guard）](#八llm-security内置护栏prompt-guard--llama-guard)
- [九、可观测性：HQL、自定义属性、Alerts、Reports](#九可观测性hql自定义属性alertsreports)
- [十、Prompt Management V2](#十prompt-management-v2)
- [十一、性能数据与延迟](#十一性能数据与延迟)
- [十二、部署方式：Docker / Helm / SaaS / BYOK](#十二部署方式docker--helm--saas--byok)
- [十三、成本模型：定价、Credits 与 TCO](#十三成本模型定价credits-与-tco)
- [十四、生态集成：100+ Provider 与框架](#十四生态集成100-provider-与框架)
- [十五、客户案例与典型用户](#十五客户案例与典型用户)
- [十六、优劣势分析](#十六优劣势分析)
- [十七、与其他 AI Gateway 对比](#十七与其他-ai-gateway-对比)
- [十八、维护模式下的产品风险与机会](#十八维护模式下的产品风险与机会)
- [十九、最佳实践与反模式](#十九最佳实践与反模式)
- [二十、未来展望（2026-2028）](#二十未来展望2026-2028)
- [二十一、参考资料与调研备注](#二十一参考资料与调研备注)

---

## 〇、最重要的前置事实：Helicone 已被 Mintlify 收购（2025-11）

在进入产品细节之前，必须先讲清楚影响 Helicone 长期价值的一个**根本性事件**：

> **2025-11，Helicone 团队整体加入 Mintlify。Helicone 的服务"for the foreseeable future"在 maintenance mode 持续运行 —— 包括安全更新、新模型接入、bug 与性能修复 —— 但新功能开发将围绕 Mintlify 的产品战略进行。**
>
> —— Justin & Cole（Helicone 联合创始人），2025-11

### 0.1 收购方背景

- **Mintlify** 是面向开发者的 AI 文档平台（mintlify.com），产品方向是 "AI agents 时代的实时知识层"。
- 创始团队：Han Wang / Hahnbee Lee。
- 投资方包括 YC。

### 0.2 收购的具体含义

| 维度 | 状态 |
|---|---|
| 核心服务可用性 | ✅ 继续运行（maintenance mode） |
| 安全更新 | ✅ 持续 |
| 新模型接入 | ✅ 持续 |
| Bug / 性能修复 | ✅ 持续 |
| **新功能开发** | ⚠️ 转向 Mintlify 整体战略（文档中心化、AI Agent 知识层） |
| 团队去向 | 全员加入 Mintlify（San Francisco） |
| 自托管/开源 | ✅ Apache v2.0 仍可 fork（GitHub 仓库继续） |
| 企业级 SLA | ⚠️ 不再主动签大客户长约，存量客户保留 |
| 客户数 | 截至收购：**16,000+ 组织**、**14.2 万亿+ token** 处理、**3,300 万+** 终端用户 |

### 0.3 为什么这条信息至关重要

1. **风险信号**：对生产环境用户，maintenance mode 意味着 Helicone 作为**独立产品**的长期演进已经基本结束。如果你的业务依赖 Helicone 持续的功能迭代（如与最新 Agent 框架、模型协议对齐），需要评估替代品。
2. **机会信号**：开源 Apache 2.0 协议 + 16k 客户积累 + 14.2T token 的产品打磨 = 一个**可被 fork / 私有化部署**的成熟平台。中大型企业可以"自接盘"维护自己的分叉。
3. **生态信号**：Mintlify 主营是文档平台，Helicone 主营是 LLM 观测。两家合并的真实逻辑是 **"AI Agent 的知识来源（文档）+ AI Agent 的行为观测（Helicone）"** —— 一个面向 Agent 全生命周期。

> 本报告对 Helicone 的技术分析保持中立，但**任何 2026 年后的采购决策**都必须把"maintenance mode"这一前提考虑在内。

---

## 一、项目速览与定位

**一句话定位**：Helicone 是一个**面向 LLM 应用的开源 AI Gateway + 可观测性平台**，通过 OpenAI 兼容的统一 API 访问 100+ 模型、Cloudflare 边缘部署、内置缓存、Session 追踪、LLM Security、Prompt 管理能力。曾经是 YC 系最受欢迎的 LLM 观测工具。

| 维度 | 数据 / 描述 |
|---|---|
| 项目名 | `Helicone/helicone` |
| 商业实体 | Helicone, Inc.（**2025-11 起并入 Mintlify**） |
| 创立 | 2023（YC W23） |
| 开源协议 | **Apache v2.0** |
| GitHub Stars | 约 3.5K ⭐（org），核心 `helicone` 仓库（截至 2026-06） |
| 用户数 | 16,000+ 组织（截至收购公告） |
| 处理量 | 14.2 万亿+ token（截至收购公告） |
| 终端用户 | 3,300 万+ |
| 部署形态 | Hosted SaaS（ai-gateway.helicone.ai）+ Docker 一体化镜像 + Helm Chart |
| 主语言 | TypeScript（Web / Worker / Jawn） + Cloudflare Workers 边缘 |
| 关键卖点 | "Open source LLM observability" + "100+ models, 1 API" + 0% markup 定价 |
| 2026 重大事件 | **被 Mintlify 收购**，进入 maintenance mode |

### 1.1 产品矩阵

Helicone 由多个相互独立又互相补强的模块组成：

| 模块 | 角色 | 是否开源 | 备注 |
|---|---|---|---|
| **AI Gateway** | 统一 API 接入、路由、Failover | ✅（核心） | `https://ai-gateway.helicone.ai` |
| **Observability** | 请求 / Session / Cost / Latency 可视化 | ✅ | ClickHouse 驱动 |
| **Sessions** | Agent 多步追踪（traces） | ✅ | 三 Header 实现 |
| **Caching** | 边缘 KV 缓存 + Provider Cache | ✅ | Cloudflare Workers KV |
| **LLM Security** | Prompt Guard + Llama Guard 集成 | ✅ | 仅 OpenAI 模型 |
| **Prompts** | Prompt 版本化、变量化、Gateway 部署 | ✅ | 2025-07 V2 重写 |
| **Datasets** | 训练 / 评估数据集导出 | ✅ | |
| **Custom Properties** | 自定义元数据标签 | ✅ | |
| **User Metrics** | 用户级使用与成本归因 | ✅ | |
| **Alerts / Reports** | 阈值告警、周报 | ✅ | |
| **HQL** | SQL 风格的查询语言 | ✅ | |
| **Webhooks** | 异步事件分发 | ✅ | |
| **Fine-tuning 集成** | 跳转 OpenPipe / Autonomi | ⚠️ 外部 | |
| **Model Registry / Cost API** | 300+ 模型定价库 | ✅ | helicone.ai/llm-cost |
| **MCP Server** | 数据管理 MCP 端点 | ✅ | |
| **Enterprise** | SLA / SOC2 / HIPAA / SSO | ❌ SaaS | 需联系销售 |

### 1.2 与"竞品"的边界

| 边界 | Helicone 的位置 |
|---|---|
| 单纯的 Proxy | ❌ 远超 Proxy |
| 可观测性平台 | ✅ 核心能力 |
| AI Gateway | ✅ 2024 后扩展 |
| 提示词 / 实验平台 | ✅ Prompts V2 + Playground |
| LLM 安全网关 | ✅ 内置 Prompt Guard / Llama Guard |
| 一站式 LLM App 平台 | ⚠️ 部分（Heli 1.x 时代曾尝试，后聚焦 Gateway + Observability） |

> 横向看：Helicone 的真实对手不是 Portkey（更偏控制面板），也不是 Langfuse（更偏 trace 协议）—— **Helicone 是"AI Gateway + 观测 + 缓存 + 安全"的合体形态**，在功能边界上最接近 Portkey + Langfuse 合并后再砍掉 LangChain 强耦合的形态。

---

## 二、项目背景与公司

### 2.1 创立故事

- **2023-01 / YC W23**：Justin Torre-Hahn 和 Cole Gottdank 在 YC W23 创立 Helicone。
- **背景判断**：YC W23 同期出现大量"GPT Wrapper"创业潮，LLM 观测市场尚是空白。
- **切入点**：所有 LLM 应用的"日志 + 成本 + 延迟"是基础设施级需求，类比于 Web 时代的 Datadog / Sentry。
- **产品哲学**："一行代码就能接入"的 Proxy 形态（改 `baseURL`），降低开发者迁移成本。
- **早期杀手锏**：实时仪表盘 + 极简集成（很多竞品如 LangSmith 强耦合 LangChain）。
- **2024 末 / 2025 初**：从"可观测性"扩展为"AI Gateway"，上线 100+ 模型统一接入、Credits 0% markup。
- **2025-11**：被 Mintlify 收购，进入 maintenance mode。

### 2.2 关键时间线

```
2023-01 ──  YC W23 加入
2023      ──  v0.x：以 OpenAI Proxy + Cloudflare Worker 为主
2023-Q3   ──  Prompt Management v1
2024-Q1   ──  Sessions 功能上线
2024-Q2   ──  Provider Routing 增强
2024-Q3   ──  AI Gateway 重塑（多 Provider 翻译层）
2024-Q4   ──  Credits 0% markup 模型
2025-02   ──  Prompt Management V2（重写）
2025-08   ──  GPT-5 / Claude Opus 4.1 接入
2025-11   ──  🔴 被 Mintlify 收购，进入 maintenance mode
2026-06   ──  本调研抓取：服务依然在线，但增长曲线扁平化
```

### 2.3 商业模型演化

- **v0.x**（2023）：完全免费，靠品牌与社区积累。
- **v1.0**（2024 早期）：引入 Hobby / Pro / Team / Enterprise 分层。
- **Credits 体系**（2024-末）：引入"托管 API Key + 0% markup"模式，类似 OpenRouter 但不加价。
- **定价迭代**：到 2025 末稳定为 Hobby $0 / Pro $79/月 / Team $799/月 / Enterprise 联系销售。

### 2.4 团队

- 创始：Justin Torre-Hahn（CEO）、Cole Gottdank（CTO）
- 团队规模：截至 2025-11 收购约 20-30 人（公开信息未给精确数字）。
- 文化信号（来自博客与 Discord）：极客文化，强 YC 社区链接（"most-used LLM observability platform by YC companies"）。

---

## 三、架构设计：六服务边缘架构

### 3.1 整体架构图（ASCII）

```
                          ┌─────────────────────────────────────────────┐
                          │      Browser / Mobile / Server SDK          │
                          │  (OpenAI / Anthropic / LangChain / 自研)   │
                          └────────────────────┬────────────────────────┘
                                               │ HTTPS (baseURL rewrite)
                                               ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │                  Cloudflare Global Network (300+ PoPs)                   │
   │  ┌────────────────────────────────────────────────────────────────┐      │
   │  │  Helicone Worker (Cloudflare Worker)                           │      │
   │  │  - LLM 反向代理 / 协议翻译                                      │      │
   │  │  - 边缘缓存 (Workers KV)                                       │      │
   │  │  - 路由决策 (BYOK vs Managed Credits)                          │      │
   │  │  - LLM Security 头道筛查 (Prompt Guard 86M)                   │      │
   │  │  - Session 头解析 / 路径层级                                    │      │
   │  │  - Provider 故障转移                                           │      │
   │  └────────────┬────────────────────────────────────┬──────────────┘      │
   │               │ 命中缓存                            │ 转发到 Provider    │
   │               ▼                                    ▼                     │
   │  ┌─────────────────────────┐    ┌────────────────────────────────┐       │
   │  │ Workers KV (缓存层)      │    │ Upstream Providers             │       │
   │  │ - 完整响应体              │    │ - OpenAI  / Anthropic          │       │
   │  │ - 7 天默认 TTL           │    │ - Google (Gemini / Vertex)     │       │
   │  │ - 300+ PoP 分布          │    │ - AWS Bedrock                  │       │
   │  └─────────────────────────┘    │ - Azure OpenAI                 │       │
   │                                 │ - Groq / Together / Fireworks  │       │
   │                                 │ - Anyscale / DeepInfra         │       │
   │                                 │ - Ollama / OpenRouter / 其他  │       │
   │                                 └────────────┬───────────────────┘       │
   └────────────────────────────────────────────────┼──────────────────────────┘
                                                    │ 响应回流
                                                    ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │                       Jawn Service (Express + Tsoa)                    │
   │  - 接收 Worker 上报的请求 / 响应 metadata                                │
   │  - 写入 PostgreSQL (元数据) + ClickHouse (分析) + MinIO (请求体)         │
   │  - 暴露 REST API 给 Web 端 (请求列表、会话、Alert、报表)                 │
   │  - 触发 Webhook / Alert / HQL 查询                                      │
   └────┬──────────────┬──────────────┬──────────────┬─────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   ┌─────────┐  ┌────────────┐  ┌─────────────┐  ┌─────────┐
   │Postgres │  │ClickHouse  │  │   MinIO     │  │Supabase │
   │(Supabase│  │(分析 + HQL)│  │(请求/响应体)│  │(Auth+   │
   │ 替代品) │  │            │  │  S3 兼容    │  │ 用户)   │
   └─────────┘  └────────────┘  └─────────────┘  └─────────┘
        ▲
        │
   ┌────┴────────────────────────────────────────────────────┐
   │   Web (Next.js) — 用户控制台 / Playground / Prompt Editor│
   └─────────────────────────────────────────────────────────┘
```

### 3.2 六大服务组件

#### 3.2.1 Web（Next.js）
- 前端控制台：请求 / Session / Prompt / Cost / Alert 配置。
- 技术栈：Next.js（App Router）+ TypeScript。
- 部署：可独立部署在 Vercel / 任意 Node 环境。

#### 3.2.2 Worker（Cloudflare Workers）
- **核心数据面**：处理所有 LLM 代理请求。
- **核心职责**：
  - 协议翻译（OpenAI 格式 ↔ Anthropic 格式 ↔ Gemini 格式）。
  - 边缘缓存读写（KV）。
  - 路由决策（BYOK vs Managed Keys）。
  - LLM Security 一级筛查。
  - 异步日志上送（不阻塞主路径）。
- **延迟贡献**：~50ms（Cloudflare 边缘）。
- **冷启动**：几乎无（V8 Isolates 启动 < 5ms）。

#### 3.2.3 Jawn（Express + Tsoa）
- 业务 API 服务。
- 使用 [Tsoa](https://github.com/lukeautry/tsoa) 自动生成 OpenAPI 文档。
- 接收 Worker 上报的事件并写入存储。
- 处理 HQL 查询、Alert 计算、Webhook 触发。

#### 3.2.4 Supabase（Application DB + Auth）
- 替代品：自托管可换为独立 Postgres + Better-Auth。
- 存：用户、组织、Organization Member、API Key、Prompt 元数据。

#### 3.2.5 ClickHouse（Analytics DB）
- 存：所有请求的 cost、latency、token、模型、provider、custom properties。
- 列式存储，擅长聚合分析（按日 / 按模型 / 按用户 / 按国家）。
- HQL 直接转译为 ClickHouse SQL。

#### 3.2.6 MinIO（Object Storage）
- S3 兼容。
- 存：完整请求体 / 响应体（用于调试与回放）。
- 默认 bucket：`request-response-storage`。

### 3.3 部署拓扑变体

| 部署形态 | Web | Worker | Jawn | Postgres | ClickHouse | MinIO | 鉴权 |
|---|---|---|---|---|---|---|---|
| **SaaS（默认）** | Cloudflare Pages | Cloudflare Workers（边缘） | 容器化（多区域） | Supabase 托管 | 托管 ClickHouse | 托管 MinIO | 托管 |
| **Docker（all-in-one）** | 容器内 | 不适用 | 容器内 | 容器内 | 容器内 | 容器内 | 自管 |
| **Helm（Enterprise）** | K8s Pod | Cloudflare Workers（仍可连外部）| K8s Pod | 可接外部 RDS | 可接外部 ClickHouse | 可接外部 S3 | 集成企业 IdP |

> 关键点：**Worker 始终是 Cloudflare Workers**，即使自托管也通过外连 CF Worker 复用边缘能力。这是 Helicone 性能优势的关键。

### 3.4 数据流路径

#### 3.4.1 写路径（请求发起）

```
User App 
  → (HTTPS) Cloudflare Edge (Worker)
  → 检查 Session Headers / Cache Headers
  → 若命中 KV Cache: 直接返回（路径 = CACHE_HIT）
  → 若启用 LLM Security: 调 Prompt Guard 86M (同步)
  → 决策路由:
      ├─ 有 BYOK → 用 BYOK 调 Provider
      └─ 无 BYOK  → 用 Managed Credits 调 Provider
  → 拿到 Response
  → 若启用 LLM Security Advanced: 异步调 Llama Guard 3.8B
  → 异步上送 metadata + body 到 Jawn
  → Jawn 写入 Postgres + ClickHouse + MinIO
  → (Web 端轮询 / WebSocket 拉新数据，UI 实时刷新)
  → Response 返回给 User
```

#### 3.4.2 读路径（Dashboard 查询）

```
User → Web (Next.js) → Jawn REST API
  ├─ 列表请求 → Postgres + ClickHouse
  ├─ Session Tree → ClickHouse GROUP BY session_id, path
  ├─ HQL → ClickHouse SQL（行级权限）
  ├─ Cost 聚合 → ClickHouse
  └─ Playground 调 LLM → 走 Worker（同写路径）
```

### 3.5 关键设计取舍

1. **Worker 必须依赖 Cloudflare**：意味着自托管用户也要"出网"到 CF 边缘。这是性能与控制权的权衡。
2. **冷存储用 MinIO / S3**：完整请求体通常很大（10MB+），不适合存 Postgres。
3. **ClickHouse 而非 Postgres 做分析**：请求量大、聚合查询多，列式存储效率高 10x+。
4. **Worker 异步日志**：使用 `ctx.waitUntil()` 模式，主路径不阻塞。
5. **Session 标识走 HTTP Header 而非业务字段**：避免破坏 OpenAI SDK 接口兼容性。

---

## 四、协议支持：OpenAI 兼容 + 多 Provider 翻译层

### 4.1 协议矩阵

| 协议 / 端点 | 支持情况 | 备注 |
|---|---|---|
| **OpenAI Chat Completions** | ✅ 主推 | `/v1/chat/completions`（`/chat/completions` 别名） |
| **OpenAI Responses API** | ✅ | 2025 后期补齐（`/gateway/concepts/responses-api.md`） |
| **OpenAI Image Generation** | ✅ | `/gateway/concepts/image-generation.md` |
| **Anthropic Messages** | ✅ | `/v1/gateway/anthropic/v1/messages` |
| **Anthropic Web Search (`:online`)** | ✅ | 通过 `:online` 后缀激活 |
| **Google Gemini / Vertex** | ✅ | 翻译为 OpenAI 格式 + 原生格式 |
| **AWS Bedrock** | ✅ | 翻译层 |
| **Azure OpenAI** | ✅ | 支持自定义 deployment ID |
| **Streaming (SSE)** | ✅ | 默认透传 |
| **Reasoning / Thinking Blocks** | ✅ | 2025 中加入 |
| **Tool Use / Function Calling** | ✅ | 翻译层 |
| **Context Editing** | ✅ | `/gateway/concepts/context-editing.md` 自动清理旧 tool use |
| **Prompt Caching (Provider 侧)** | ✅ | 透传 `prompt_cache_key` |
| **MCP** | ✅ | 数据管理 MCP server |

### 4.2 翻译层细节

Helicone 的 AI Gateway 核心是**协议翻译**。当你用 OpenAI 格式请求 `claude-sonnet-4` 时，Worker 内部分别做：

```
OpenAI 格式请求
  → [Helicone Worker 解析]
  → 识别 model = "claude-sonnet-4"
  → 目标 Provider = Anthropic
  → 转换为 Anthropic Messages 格式:
      {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": <OpenAI max_tokens 转译>,
        "system": <OpenAI system message 转译>,
        "messages": [...]
      }
  → 调 Anthropic API
  → 拿响应 → 翻译回 OpenAI ChatCompletion 格式
  → 返回给调用方
```

#### 4.2.1 关键翻译点

| 字段 | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| `messages[0].role=system` | ✅ 顶层 | ✅ `system` 字段 | ✅ `systemInstruction` |
| `max_tokens` | ✅ | ✅（必填） | ✅ `maxOutputTokens` |
| `temperature` | ✅ | ✅ | ✅ |
| `stream` | ✅ | ✅ | ✅ |
| `tools` / `functions` | `tools[]` | `tools[]` | `tools[]`（结构略不同） |
| `response_format` (JSON) | ✅ | ✅（System + 提示词） | ✅ `responseSchema` |
| `stop` | 数组 / 字符串 | ✅ | ✅ |
| `seed` | ✅ | ✅ | ⚠️ 部分支持 |
| `logprobs` | ✅ | ❌ | ⚠️ |
| `user` | ✅ | ❌ | ❌ |

### 4.3 自定义 Headers（Helicone 扩展协议）

Helicone 通过 HTTP Headers 暴露其能力，不破坏 OpenAI SDK 兼容性：

| Header | 类型 | 作用 |
|---|---|---|
| `Helicone-Auth` | `Bearer <HELICONE_API_KEY>` | 必填（Hosted 模式） |
| `Helicone-User-Id` | string | 用户级归因 |
| `Helicone-Session-Id` | UUID | Session 唯一标识 |
| `Helicone-Session-Path` | path-like | Session 层级路径 |
| `Helicone-Session-Name` | string | Session 类型名 |
| `Helicone-Cache-Enabled` | "true"/"false" | 开启边缘缓存 |
| `Helicone-Cache-Seed` | string | 缓存命名空间 |
| `Helicone-Cache-Bucket-Max-Size` | int | 多响应缓存桶大小 |
| `Helicone-Cache-Ignore-Keys` | csv | 缓存键忽略字段 |
| `Helicone-LLM-Security-Enabled` | "true" | 启用 Prompt Guard |
| `Helicone-LLM-Security-Advanced` | "true" | 启用 Llama Guard |
| `Helicone-Moderations-Enabled` | "true" | 启用 OpenAI Moderation |
| `Helicone-Property-...` | string | 自定义属性（任意 key） |
| `Helicone-Prompt-Id` | string | 引用 Prompt V2 模板 |
| `Helicone-Request-Id` | UUID | 手动指定 request ID |
| `Helicone-Prompt-Cache-Key` | string | 透传给 Provider 的 cache key |

> 任何合法的 OpenAI/Anthropic SDK 都不需要修改代码——只需在 `defaultHeaders` 加几行配置。

### 4.4 Anthropic Web Search (`:online`)

2025 年新增的差异化能力：

```typescript
const response = await client.messages.create({
  model: "claude-sonnet-4:online",  // 激活 Web Search
  // ...
});
```

Helicone 内部识别 `:online` 后缀，注入 Anthropic 的 `web_search_20250305` 工具。

---

## 五、AI Gateway 与 Provider Routing

### 5.1 路由策略

Helicone 的 AI Gateway 路由策略非常简洁（**零配置智能路由**）：

```
优先级:
  1. 用户 BYOK（Provider Settings 配置）→ 优先用 BYOK
  2. 零配置默认 → 选最便宜的可用 Provider
  3. 同价 → 负载均衡
  4. 错误 → 立即 failover 到下一个
```

#### 5.1.1 Failover 触发器

| HTTP Status | 含义 |
|---|---|
| 429 | Rate Limit |
| 401 | Auth Failure |
| 400 | Context Length Exceeded |
| 408 | Timeout |
| 500+ | Server Error |

#### 5.1.2 Model 字符串语法

Helicone 允许用 `/` 显式控制路由：

| 语法 | 含义 |
|---|---|
| `"gpt-4o-mini"` | 智能路由（最便宜 → failover） |
| `"gpt-4o-mini/openai"` | 锁定 OpenAI（不 failover） |
| `"gpt-4o-mini/azure/<deployment-id>"` | 锁定你的 Azure 部署 |
| `"gpt-4o-mini/azure,gpt-4o-mini"` | 先 Azure，再智能路由 |
| `"!openai,gpt-4o-mini"` | 排除 OpenAI，智能路由其他 |

### 5.2 Credits 体系（0% Markup）

```
User → 加 credits 到 Helicone 账户
  → 用 HELICONE_API_KEY 请求 `https://ai-gateway.helicone.ai`
  → Worker 看到无 BYOK
  → 用 Helicone 托管的 Provider API key 调用
  → 按 Provider 官方价计费（0% 加价）
  → Dashboard 同步扣减 Credits
```

**为什么 0%**：Helicone 通过模型使用费（不是 token 加价）赚钱。

- 用户支付：Provider 官方价格（与直接走 Provider 一致）。
- Helicone 收入：托管信用利差？协议层收入？合同收入？实际公开数据未披露。**猜测**：
  - 一部分大客户走 Enterprise 合同；
  - 一部分长期未使用 Credits 的余额可视为"沉睡资金"；
  - 与 Provider 可能有批量折扣分成（未公开）。

### 5.3 BYOK 模式

```typescript
// 在 Provider Settings 页面配置你自己的 Provider API Keys
// 然后代码无任何变化
const response = await client.chat.completions.create({
  model: "gpt-4o-mini",
  messages: [...]
});
// Worker 自动优先用你的 OpenAI key
// 如果 401/429/timeout → fallback 到 Managed Credits
```

### 5.4 已知路由限制

- 智能路由只对**模型注册表中已有**的 model 有效。未知 model 只能走 BYOK。
- 故障转移**不重试原 Provider**，直接跳下一个，避免雪崩。
- 当前**不支持权重路由**（如 70% GPT-4 / 30% Claude）；如需此类策略，需要在客户端做。

---

## 六、Sessions：面向 Agent 的多步追踪

### 6.1 核心问题

LLM Agent 的一个"任务"通常包含多次 LLM 调用 + 工具调用 + 向量检索。传统观测工具只能看到 N 条独立请求，无法看到整体流程。

### 6.2 Sessions 三大 Header

```typescript
{
  "Helicone-Session-Id": "550e8400-e29b-41d4-a716-446655440000",  // 唯一标识
  "Helicone-Session-Path": "/task/research/web_search",            // 层级路径
  "Helicone-Session-Name": "Trip Planning Agent"                   // 类型名
}
```

#### 6.2.1 Path 命名哲学

官方建议**按功能命名**而非按时间：
- ✅ `/task/research/web_search`（同一类工作复用同一路径）
- ❌ `/step1`, `/step2`（破坏可对比性）

#### 6.2.2 实际 UI 展示

```
Trip Planning Agent  ── /task
                          ├── /task/research        (1.2s, $0.0023, 342 tokens)
                          │   ├── /task/research/web_search
                          │   └── /task/research/summarize
                          ├── /task/plan             (0.8s, $0.0018, 256 tokens)
                          │   ├── /task/plan/draft
                          │   └── /task/plan/refine
                          └── /task/answer           (1.5s, $0.0031, 412 tokens)

Total: 4.2s | $0.0124 | 1,847 tokens
```

Dashboard 看到：
- Session 树形结构
- 每个节点的延迟 / 成本 / token 分布
- 失败节点高亮
- 重放整个 Session

### 6.3 Sessions 追踪的范围

| 类型 | 是否追踪 |
|---|---|
| LLM 调用 | ✅ |
| Vector DB 查询 | ✅（通过 Vector DB Logger SDK） |
| Tool Calls | ✅（通过 Tools Logger SDK） |
| 自定义事件 | ✅（任意 POST 到 Jawn `/v1/trace`） |
| 跨进程 / 跨服务 | ⚠️ 需要共享 Session-Id |

### 6.4 与 LangSmith / Langfuse Sessions 的对比

| 维度 | Helicone | LangSmith | Langfuse |
|---|---|---|---|
| Header 协议 | ✅ 极简 | ❌ 用 LangChain SDK | ✅ `session_id` 等元数据 |
| Tree 视图 | ✅ 路径语法 | ✅ 自动推断 | ✅ 手动 nest |
| 跨服务 | ⚠️ 共享 Header | ❌ LangChain 内 | ✅ |
| 实时性 | ✅ Worker 异步推送 | ⚠️ 缓存延迟 | ✅ |
| 多模态 | ✅ | ✅ | ✅ |

---

## 七、缓存体系：边缘缓存 + Provider Prompt Cache 双层

Helicone 的缓存是**双层架构**，这是它性能/成本优势的关键。

### 7.1 第一层：边缘响应缓存（Cloudflare Workers KV）

#### 7.1.1 工作机制

```
请求到达 Worker
  → 计算 cache key = hash(cache_seed + URL + body + relevant_headers + bucket_index)
  → KV.lookup(key)
      ├─ HIT → 直接返回（路径耗时 < 50ms，跨 300+ PoP）
      └─ MISS → 转发到 Provider → 拿到 Response → KV.set(key, response, ttl)
```

#### 7.1.2 默认配置

| 参数 | 默认 | 备注 |
|---|---|---|
| `Helicone-Cache-Enabled` | false | 需显式开启 |
| `Cache-Control: max-age` | `604800`（7 天） | 标准 HTTP 缓存控制 |
| Bucket 大小 | 1 | 同请求缓存几个不同响应 |
| 存储后端 | Cloudflare Workers KV | 全球分布 |

#### 7.1.3 适用场景

- 开发 / 调试期间相同请求反复重发。
- 用户级配置查询（"我账户余额是多少？"）。
- 系统提示词固定的 few-shot。
- Rate Limit 触发时的紧急缓刑。

#### 7.1.4 限制

- **不是语义缓存**：`Hi` ≠ `Hello`。
- **不节省 Prompt Cache 配额**：只缓存完整响应。
- **不保证强一致**：边缘节点间可能短暂不一致。

### 7.2 第二层：Provider 侧 Prompt Cache

针对 Anthropic / OpenAI 提供的原生 prompt cache（如 Anthropic 的 `cache_control` 块、OpenAI 的 `prompt_cache_key`）：

```typescript
const response = await client.chat.completions.create(
  {
    model: "claude-3.5-sonnet",
    messages: [{ role: "user", content: "..." }],
    prompt_cache_key: `doc-analysis-${docId}`
  },
  {
    headers: {
      "Helicone-Cache-Enabled": "true",
      "Helicone-Cache-Ignore-Keys": "prompt_cache_key",  // 关键！
      "Cache-Control": "max-age=3600"
    }
  }
);
```

`Helicone-Cache-Ignore-Keys` 让 Helicone KV 缓存**忽略** `prompt_cache_key` 字段，**但**仍然透传给 Provider 触发其原生 cache。

#### 7.2.1 协同效应

| 缓存层 | 节省 | 适用 |
|---|---|---|
| Helicone KV | **整个响应**的 token + 时间 | 整请求完全相同 |
| Provider Prompt Cache | **系统提示词 / 长上下文**的输入 token | 上下文相同但 query 略变 |

两者叠加：同一文档 + 同一查询 → KV 命中；同一文档 + 不同查询 → Provider cache 命中。

### 7.3 与 Portkey / LiteLLM 的缓存对比

| 能力 | Helicone | Portkey | LiteLLM |
|---|---|---|---|
| 边缘 KV 缓存 | ✅ CF Workers | ✅（自托管 Redis） | ❌（内存 / Redis） |
| 语义缓存 | ❌ | ✅（pgvector） | ✅（可选 Redis + embedding） |
| Provider Prompt Cache 透传 | ✅ | ✅ | ✅ |
| 缓存命中可视化 | ✅ | ✅ | ❌ |
| 缓存桶（多响应） | ✅ | ✅ | ❌ |
| 自定义 TTL | ✅ | ✅ | ✅ |

---

## 八、LLM Security：内置护栏（Prompt Guard + Llama Guard）

### 8.1 设计目标

LLM Security 是 Helicone 在 2024-2025 加的内置安全层，目标：

- 检测 prompt injection / jailbreak。
- 检测数据外泄企图。
- 阻止钓鱼生成。

### 8.2 两层模型

#### 8.2.1 Tier 1：Prompt Guard 86M（Meta）

- 参数：86M（极轻量）。
- 任务：检测直接 / 间接 prompt injection、jailbreak、8 语言恶意内容。
- 延迟：~10-30ms（同步调）。
- 准确率：> 97% jailbreak 检测。

#### 8.2.2 Tier 2：Llama Guard 3.8B（Meta）

- 参数：3.8B。
- 任务：14 类深度内容审核（暴力、犯罪、隐私、知识产权、武器、仇恨、自残、色情、选举、代码滥用……）。
- 延迟：~100-300ms（异步 / 同步可选）。
- 触发条件：`Helicone-LLM-Security-Advanced: true`。

### 8.3 启用方式

```bash
curl https://ai-gateway.helicone.ai/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HELICONE_API_KEY" \
  -H "Helicone-LLM-Security-Enabled: true" \
  -H "Helicone-LLM-Security-Advanced: true" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "How do I enable LLM security?"}]
  }'
```

### 8.4 拦截响应

```json
{
  "success": false,
  "error": {
    "code": "PROMPT_THREAT_DETECTED",
    "message": "Prompt threat detected. Your request cannot be processed.",
    "details": "See your Helicone request page for more info."
  }
}
```

### 8.5 已知限制

- **仅支持 OpenAI 模型**（gpt-4、gpt-3.5-turbo 等）。
- 阻止后，**Provider 的费用仍可能被计费**（取决于请求是否已发出）—— 官方未明确。
- 误报率与漏报率官方未公开数字。
- 与 Provider 自带 moderation 重复，可能双计费。

### 8.6 对比

| 能力 | Helicone | Portkey | NeMo Guardrails | Lakera |
|---|---|---|---|---|
| 内置 prompt injection 检测 | ✅ Prompt Guard | ✅（多模型可选） | ✅（规则 + LLM） | ✅（专用） |
| 内置内容分类 | ✅ Llama Guard | ✅ | ✅ | ⚠️ |
| 同步 / 异步 | ✅ 双选 | ✅ | ✅ | ✅ |
| 多语言 | ✅ 8 种 | ⚠️ | ⚠️ | ⚠️ |
| 与 Gateway 集成 | ✅ 原生 | ✅ 原生 | ❌ 独立 | ❌ 独立 |

---

## 九、可观测性：HQL、自定义属性、Alerts、Reports

### 9.1 标准可观测字段

每条请求自动采集：

| 字段 | 类型 | 用途 |
|---|---|---|
| `request_id` | UUID | 唯一 ID |
| `session_id`, `session_path`, `session_name` | string | Session 关联 |
| `user_id` | string | 用户级归因 |
| `model` | string | 实际调用的 model |
| `provider` | string | 实际 Provider（OpenAI / Anthropic / …） |
| `request_body` | JSON | 完整请求体 |
| `response_body` | JSON | 完整响应体 |
| `prompt_tokens` | int | 输入 token |
| `completion_tokens` | int | 输出 token |
| `total_tokens` | int | 总 token |
| `cost` | float | 美元 |
| `latency_ms` | int | 端到端延迟 |
| `time_to_first_token_ms` | int | 流式首 token 延迟 |
| `status_code` | int | HTTP status |
| `country_code` | string | 调用方地区（基于 CF PoP） |
| `created_at` | timestamp | 时间戳 |
| `custom_properties.*` | any | 用户自定义标签 |
| `cache_hit` | bool | 是否缓存命中 |
| `cache_lookup_time` | int | 缓存查找时间 |
| `moderation_*` | various | 审核结果 |

### 9.2 Custom Properties

```typescript
const response = await client.chat.completions.create(
  { /* ... */ },
  {
    headers: {
      "Helicone-Property-Environment": "production",
      "Helicone-Property-Feature": "code-completion",
      "Helicone-Property-User-Tier": "premium",
      "Helicone-Property-Experiment": "variant-A"
    }
  }
);
```

任意业务字段都可以贴标签，后续做切片分析。

### 9.3 HQL（Helicone Query Language）

类 SQL 语法，直接查 ClickHouse：

```sql
SELECT
  model,
  count(*) as n,
  avg(latency_ms) as avg_latency,
  sum(cost) as total_cost
FROM requests
WHERE user_id = 'premium-tier'
  AND created_at > now() - interval 7 day
GROUP BY model
ORDER BY total_cost DESC
LIMIT 10
```

- 行级权限（用户只能查自己组织的数据）。
- 内置 limits 防扫库。
- 支持保存为 dashboard panel。

### 9.4 Alerts

| Alert 类型 | 触发条件示例 |
|---|---|
| 错误率 | `error_rate > 5%` over 5min |
| 成本 | `cost_per_hour > $50` |
| 延迟 P95 | `latency_p95 > 3000ms` |
| 自定义 | 基于 HQL 任意查询 |

通知渠道：Email、Slack、Webhook。

### 9.5 Reports

每周自动汇总：总成本、按模型拆分、按用户拆分、异常请求 Top 10。投递到 Email / Slack。

### 9.6 User Metrics & Analytics

- 按 `user_id` 聚合：调用次数、成本、latency、cache hit rate。
- 用于：识别高价值用户、识别滥用、计费用量。

---

## 十、Prompt Management V2

### 10.1 解决的问题

传统 prompt 写在代码里：
- 修改需要 re-deploy。
- 无法 A/B 测试。
- 无版本控制。
- 团队协作混乱。

### 10.2 V2 特性（2025-07 重写）

| 特性 | 描述 |
|---|---|
| 强类型变量 | `{{hc:customer_name:string}}` 语法 |
| 多场景变量 | System / User / Tool Schema / Response Format |
| 版本控制 | 历史版本可回滚 |
| 零代码部署 | 通过 AI Gateway `prompt_id` 引用 |
| Playground 测试 | UI 实时测试不同模型 / 参数 |
| Dynamic Schemas | 变量在 JSON Schema 中可用 |
| TypeScript 类型安全 | `@helicone/helpers` 提供类型 |

### 10.3 使用流程

```
1. 在 Dashboard 创建 Prompt 模板
   system: "You are a {{hc:role:string}} assistant for {{hc:company:string}}."
   user: "Help me with {{hc:topic:string}}."

2. 在 Playground 测试
   选 model = gpt-4o-mini
   填 inputs = { role: "HR", company: "Acme", topic: "onboarding" }
   看输出

3. 在代码中引用（通过 AI Gateway）
   const response = await openai.chat.completions.create({
     model: "gpt-4o-mini",
     prompt_id: "abc123",
     inputs: { role: "HR", company: "Acme", topic: "onboarding" }
   });
```

### 10.4 关键能力：运行时编译

Helicone Worker 收到 `prompt_id` 后：
1. 从 Postgres 拉取模板。
2. 用 `inputs` 编译模板 → 实际 messages。
3. 注入到对 Provider 的请求。

更新 prompt → 立即生效（无需 re-deploy）。

### 10.5 与其他方案对比

| 维度 | Helicone Prompts V2 | Portkey Prompts | LangSmith Hub | Vercel AI SDK |
|---|---|---|---|---|
| 部署 | 任意 HTTP 客户端 | 任意 HTTP 客户端 | 任意 HTTP 客户端 | 需 Node.js |
| 版本控制 | ✅ | ✅ | ✅ | ❌ |
| 运行时编译 | ✅ | ✅ | ✅ | ❌ |
| Playground | ✅ | ✅ | ✅ | ❌ |
| 与观测集成 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ⚠️ 需配 Helicone |
| 计费挂钩 | ✅ 自动计费 | ✅ | ❌ | ❌ |

---

## 十一、性能数据与延迟

### 11.1 官方公布的关键数字

来自 Helicone 官方博客《LangSmith vs Helicone》（截至 2025）：

> "Helicone is built on the edge using Cloudflare Workers to minimize time to response. This adds only **~50 ms** for about **95% of the world's Internet-connected population**. We're also proud of our **99.99% uptime in the last year**."

### 11.2 延迟分解

| 阶段 | 延迟（典型） | 备注 |
|---|---|---|
| Client → CF Edge | 10-30ms | 取决于地理位置 |
| Worker 解析 Headers | 1-3ms | V8 Isolates |
| 缓存查找（KV） | 5-15ms | 命中时省 100-2000ms |
| 路由决策 | 1-2ms | BYOK vs Credits |
| LLM Security（基础） | 10-30ms | Prompt Guard 86M |
| 转发到 Provider | 取决于 Provider | GPT-4 200-1500ms |
| Response 回流 | 同上 | |
| Worker 异步日志 | 0ms（waitUntil） | 不阻塞 |
| **总开销** | **~50ms** | 不含 Provider 时间 |

### 11.3 缓存命中场景

| 场景 | 延迟 |
|---|---|
| 完全 Cache Hit | **< 50ms**（全球分布） |
| 冷 Cache + GPT-4o-mini | 500-1500ms |
| 冷 Cache + Claude Sonnet 4 | 800-3000ms |
| Cache Hit + 流式首 token | 30-80ms |

### 11.4 可用性

- 99.99% uptime（过去一年）。
- 多 Provider failover 兜底 Provider 故障。

### 11.5 性能劣势场景

- **Cold Start 无所谓**（V8 Isolates）。
- **大 body 上传**（> 10MB 请求体）会拖慢 Worker 解析。
- **同步 LLM Security 高级模式**会引入 100-300ms 额外延迟。

### 11.6 与同类对比

| Gateway | 边缘延迟开销 | Provider failover | 缓存层 |
|---|---|---|---|
| Helicone | ~50ms（CF） | ✅ | KV |
| Portkey | ~30-100ms（多区域） | ✅ | Redis |
| Cloudflare AI Gateway | ~10-30ms | ✅ | KV |
| LiteLLM（自托管） | 取决于服务器 | ✅ | 内存/Redis |
| OpenRouter | 100-200ms | ✅ | 内存 |

---

## 十二、部署方式：Docker / Helm / SaaS / BYOK

### 12.1 SaaS（默认推荐）

```
$ npm install openai
$ export HELICONE_API_KEY=...
$ # 修改 baseURL 即可
```

> 时间到首次日志：< 2 分钟。

### 12.2 Docker（一键一体化）

```bash
docker pull helicone/helicone-all-in-one:latest
docker run -d \
  --name helicone \
  -p 3000:3000 \   # Web Dashboard
  -p 8585:8585 \   # Jawn API + LLM Proxy
  -p 9080:9080 \   # MinIO S3
  helicone/helicone-all-in-one:latest
```

> 包含：Web (Next.js)、Jawn、PostgreSQL、ClickHouse、MinIO。

#### 12.2.1 远程部署（生产）

需要额外环境变量指向公网 URL：

```bash
export PUBLIC_URL="https://helicone.your-domain.com"
export JAWN_URL="https://helicone.your-domain.com:8585"
export S3_URL="https://helicone.your-domain.com:9080"

docker run -d \
  --name helicone \
  -p 3000:3000 -p 8585:8585 -p 9080:9080 \
  -e SITE_URL="$PUBLIC_URL" \
  -e BETTER_AUTH_URL="$PUBLIC_URL" \
  -e BETTER_AUTH_SECRET="$(openssl rand -base64 32)" \
  -e NEXT_PUBLIC_APP_URL="$PUBLIC_URL" \
  -e NEXT_PUBLIC_HELICONE_JAWN_SERVICE="$JAWN_URL" \
  -e NEXT_PUBLIC_IS_ON_PREM=true \
  -e S3_ENDPOINT="$S3_URL" \
  helicone/helicone-all-in-one:latest
```

#### 12.2.2 数据持久化（必须挂载卷）

```bash
-v helicone-postgres:/var/lib/postgresql/data
-v helicone-clickhouse:/var/lib/clickhouse
-v helicone-minio:/data
```

#### 12.2.3 自托管支持范围

| Provider | Docker |
|---|---|
| OpenAI | ✅ |
| Anthropic | ✅ |
| Azure OpenAI | ❌ |
| Vertex AI | ❌ |
| AWS Bedrock | ❌ |

> **重要限制**：自托管版本**只支持 OpenAI + Anthropic**，其他 Provider 需要 SaaS。

#### 12.2.4 安全注意事项

- Port 8585 默认**无鉴权**（直连即可代理 LLM）。生产必须用防火墙限制。
- HTTPS 需要自接反向代理（Caddy / nginx / Traefik）。
- 容器内邮件服务未启动，需手动 SQL 验证用户邮箱。

### 12.3 Kubernetes / Helm

```bash
# 联系 enterprise@helicone.ai 获取 Helm chart
```

适合：
- 大规模自托管（> 1B 请求/月）。
- 与企业内部 IdP / 数据合规要求对接。
- 自定义 Provider 接入。

### 12.4 BYOK（Bring Your Own Key）

不是部署形态，而是**部署在 SaaS 内的密钥管理**：
- 在 Provider Settings 配置 Provider API Keys。
- Worker 优先用 BYOK，失败回落到 Managed Credits。
- 适合：想用 Provider 信用 / 想要数据驻留特定区域 / 已有 Provider 合同。

### 12.5 部署形态对比

| 维度 | SaaS | Docker | Helm |
|---|---|---|---|
| 启动时间 | < 2min | 5-10min | 数小时 |
| 维护成本 | 零 | 中 | 高 |
| 数据控制 | ❌（Helicone 持有） | ✅ | ✅ |
| 自定义 Provider | ❌ | ⚠️ 只 OpenAI/Anthropic | ✅ |
| 升级 | 零成本 | 镜像更新 | Helm 升级 |
| 适合 | 中小企业 / 个人 | PoC / 小团队 | 大企业 |

---

## 十三、成本模型：定价、Credits 与 TCO

### 13.1 订阅价

| 套餐 | 月费 | 关键能力 |
|---|---|---|
| **Hobby** | **$0** | 10K 请求/月，1 GB 存储，1 seat，1 org，7 天 retention，10 logs/min |
| **Pro** | **$79/月** | 无限 seats，Alerts，Reports，HQL，1 月 retention，1K logs/min，60 API calls/min |
| **Team** | **$799/月** | 5 orgs，SOC-2 & HIPAA，Private Slack，3 月 retention，15K logs/min，1K API calls/min |
| **Enterprise** | 联系销售 | 无限 orgs，SAML SSO，On-prem，Custom MSA，Forever retention，30K logs/min |

### 13.2 用量计费

订阅费**之外**还有 usage-based 计费（具体单价需查 Dashboard 估算器）：

| 维度 | 估算 |
|---|---|
| 每 10K 请求 | $0（订阅内） + 超出单价 |
| 存储 | $0.97/GB·月（Dashboard 估算器示例） |
| API call | 按订阅档位定 |

### 13.3 Credits（Provider Token 预付费）

| 项目 | 详情 |
|---|---|
| 概念 | 在 Helicone 充值，用于通过托管 Key 调 Provider |
| 加价 | **0% markup**（与 Provider 官方价一致） |
| 优势 | 不需 5 个 Provider 各开账户、计费合并、自动 failover |
| 支付 | Stripe / 信用卡 |
| 退款 | 按官方政策 |

### 13.4 TCO 估算示例（10M 请求/月）

假设：
- 月 10M 请求
- 平均 1K input + 500 output tokens
- 70% 走 OpenAI GPT-4o-mini，30% 走 Anthropic Claude Sonnet 4

| 项 | 月成本估算 |
|---|---|
| Helicone Pro 订阅 | $79 |
| 用量超出 | 视具体细则（估算 ~$50-200） |
| Provider token（GPT-4o-mini） | 7M × 1500 tokens × $0.15/1M = $1,575 |
| Provider token（Sonnet 4） | 3M × 1500 tokens × $3/1M ≈ $13,500 |
| 缓存节省（按 20% 命中率） | ~-$3,000 |
| **Helicone 自身成本** | **$130-280** |
| **总成本** | ~$15,000（占 Provider 成本 1-2%） |

> 对比 LangSmith：Helicone 官方博客给出的对比表显示，在 2M logs/月和 15M logs/月，Helicone 分别便宜 36% 和 69%。

### 13.5 与 LangSmith 价格对比（官方数据）

| Logs/月 | Helicone | LangSmith |
|---|---|---|
| 10K | Free | Free |
| 25K | $24 | $7.50 |
| 50K | $44 | $20 |
| 100K | $61.50 | $45 |
| 2M | **$631.50** | **$995** |
| 15M | **$2,321.50** | **$7,495** |

> 价格优势在大体量时明显。**但请注意：此对比来自 Helicone 官方博客，可能存在最优计费档位选择偏差。**

### 13.6 折扣政策

| 类型 | 折扣 |
|---|---|
| Startup（< 2 年，<$5M 融资） | 50% 首年 |
| 非营利 | 按规模 |
| 开源公司 | $100 信用（首年） |
| 学生 / 教育 | 大多免费 |

### 13.7 隐藏成本

| 项目 | 备注 |
|---|---|
| Provider token 成本 | **主要成本**（不算 Helicone 订阅） |
| 存储（请求体） | MinIO 容量增长快 |
| 出口带宽 | 自托管需要算带宽 |
| LLM Security 高级模式 | 可能双计费（Provider + Helicone） |
| 自托管运维 | 1-2 人天/月 |

---

## 十四、生态集成：100+ Provider 与框架

### 14.1 Provider（截至 2026-06）

| Provider | Gateway 支持 | 自托管支持 |
|---|---|---|
| OpenAI | ✅ | ✅ |
| Anthropic | ✅ | ✅ |
| Azure OpenAI | ✅ | ❌ |
| Google Gemini | ✅ | ❌ |
| Google Vertex AI | ✅ | ❌ |
| AWS Bedrock | ✅ | ❌ |
| Groq | ✅ | ❌ |
| Together AI | ✅ | ❌ |
| Fireworks AI | ✅ | ❌ |
| Anyscale | ✅ | ❌ |
| Hyperbolic | ✅ | ❌ |
| DeepInfra | ✅ | ❌ |
| Ollama | ✅ | ⚠️（本地直连） |
| OpenRouter | ✅ | ❌ |
| Perplexity | ✅ | ❌ |
| Mistral | ✅ | ❌ |
| DeepSeek | ✅ | ❌ |
| Nebius Token Factory | ✅ | ❌ |
| Novita AI | ✅ | ❌ |

> 自托管 Docker 镜像只内置 OpenAI + Anthropic 的转译逻辑，其他 Provider 走 SaaS。

### 14.2 框架集成

| 框架 | 支持 |
|---|---|
| **LangChain** (JS/Python) | ✅ |
| **LlamaIndex** | ✅ |
| **LangGraph** | ✅ |
| **Vercel AI SDK** | ✅ |
| **Semantic Kernel** (C# / Python) | ✅ |
| **CrewAI** | ✅ |
| **ModelFusion** | ✅ |
| **OpenAI Agents SDK** | ✅ |
| **Claude Agent SDK** | ✅ |
| **OpenAI Codex** | ✅ |
| **DSPy** | ✅ |
| **n8n** | ✅（自定义节点） |
| **Zapier** | ✅（Zap） |
| **PostHog** | ✅（数据导出） |
| **RAGAS** | ✅（评估） |
| **Open WebUI** | ✅ |
| **MetaGPT** | ✅（YAML） |
| **Open Devin** | ✅（Docker） |
| **Mem0 EmbedChain** | ✅ |

### 14.3 异步日志（OpenLLMetry）

不通过 Proxy 而是直连 Jawn 上报：

```typescript
import { OpenAI } from "openai";
import { HeliconeAsyncLogTransport } from "@helicone/helicone";

const openai = new OpenAI();
// 走正常请求
// 异步 transport 把你调用的 OpenAI 请求日志送到 Helicone
```

适合：
- 不希望请求经过代理的场景。
- 已有 OpenTelemetry 栈。
- 多 Provider 混合调用。

### 14.4 MCP Server（数据管理）

Helicone 暴露 MCP server 让 Agent 可直接查询 Helicone 数据：

```
- 列出请求
- 导出训练数据
- 触发 Alert
- 查模型定价
```

### 14.5 Manual Logger（任意 Provider 接入）

提供 Python / TS / Go / cURL 的 manual logger，**任何自定义 LLM endpoint 都能记录到 Helicone**。

---

## 十五、客户案例与典型用户

### 15.1 官方公开数据

| 指标 | 数字 |
|---|---|
| 组织数 | **16,000+** |
| 处理 token | **14.2 万亿+** |
| 终端用户 | **3,300 万+** |
| YC 公司 | "most-used LLM observability platform"（自评） |
| Product Hunt | #1 |

### 15.2 典型用例（基于文档和博客推断）

| 行业 | 典型用户类型 |
|---|---|
| **SaaS 创业公司** | LLM 驱动的产品（客服、Copilot、生成式工具） |
| **YC 创业公司** | 早期 LLM 应用 |
| **企业内部 LLM 平台** | 自建 AI Gateway |
| **教育 / 学生项目** | Free tier 重度用户 |
| **RAG / Agent 开发者** | Session 追踪重度用户 |

### 15.3 公开案例

Helicone 公开的案例较少（与 LangSmith 大量 enterprise 案例形成对比）。最显眼的"案例"是其**与 YC 的强关联**：
- YC W23 同期公司大量使用。
- Product Hunt #1 反映了 Hacker News 社区的高认知度。

### 15.4 适合的"反例"用户

Helicone **不是**为以下场景设计：
- 大型企业（> 1B 请求/月）需 SLA → 走 Enterprise 谈判。
- 强 LangChain 绑定用户 → LangSmith 集成更紧。
- 已经在用 Datadog/Honeycomb 做 trace → 与 Helicone 重复，迁移价值不大。
- 需要语义缓存 → Portkey 更强。

---

## 十六、优劣势分析

### 16.1 优势

| # | 优势 | 详情 |
|---|---|---|
| 1 | **开箱即用，零代码迁移** | 改 `baseURL` 即可接入 |
| 2 | **OpenAI 协议兼容性** | 100+ 模型统一格式 |
| 3 | **Cloudflare 边缘部署** | ~50ms 延迟，99.99% 可用性 |
| 4 | **内置 LLM Security** | Prompt Guard + Llama Guard 集成 |
| 5 | **Apache 2.0 开源** | 可 fork、自托管、二次开发 |
| 6 | **Session 追踪** | Agent 多步追踪体验好 |
| 7 | **实时 Dashboard** | 几乎无延迟 |
| 8 | **定价透明** | 0% markup 概念易理解 |
| 9 | **生态广** | 100+ Provider、20+ 框架 |
| 10 | **YC 社区认可** | 在 YC 圈品牌强 |
| 11 | **Credits 体系** | 一个账户访问 100+ 模型 |

### 16.2 劣势

| # | 劣势 | 详情 |
|---|---|---|
| 1 | **🔴 被 Mintlify 收购** | maintenance mode，新功能放缓 |
| 2 | **依赖 Cloudflare** | 数据必须出网到 CF 边缘 |
| 3 | **自托管功能受限** | 只支持 OpenAI + Anthropic |
| 4 | **缺乏语义缓存** | 只精确匹配 |
| 5 | **缺乏权重路由** | 不支持 70/30 比例分流 |
| 6 | **没有内置评估** | 评估需靠 RAGAS 集成 |
| 7 | **企业级案例少** | 公开的 enterprise 部署案例少 |
| 8 | **双计费风险** | LLM Security 高级模式 + Provider 双重收费 |
| 9 | **没有 MCP 网关** | 只支持数据管理 MCP，缺少工具调用 MCP 网关（与 Portkey MCP Gateway 差距） |
| 10 | **Prompts V2 还在打磨** | 2025-07 才重写，生态迁移中 |
| 11 | **大客户支持能力下降** | 团队并入 Mintlify，大客户关系可能受影响 |
| 12 | **没有公开的金融级 SLA** | 不适合 mission-critical |

### 16.3 SWOT 综合

```
                 Internal
                 
Helicone  Strengths (强)        Weaknesses (弱)
  ▲         - 边缘性能             - 被收购
  │         - 开源                - 自托管功能窄
  │         - 协议兼容              - 无语义缓存
  │         - 生态广               - 无权重路由
  │         - 价格透明              - 无内置评估
  │         - 内置安全              
  │
  │         Opportunities (机)    Threats (威)
  │         - Agent 时代            - Langfuse 快速崛起
  │         - 多模态 (图像/语音)    - Portkey 被 Palo Alto 收购（也有风险）
External    - Edge AI Gateway 趋势  - 自建可观测栈的厂商
            - Mintlify 文档生态     - 模型价格战压缩利润
            - 开源 fork 生态
```

---

## 十七、与其他 AI Gateway 对比

### 17.1 横向对比矩阵

| 维度 | **Helicone** | **Portkey** | **OpenRouter** | **LiteLLM** | **Cloudflare AI GW** | **Langfuse** | **Higress** |
|---|---|---|---|---|---|---|---|
| **定位** | Gateway+观测 | 控制面板 | 模型市场 | 统一 SDK | 边缘代理 | 观测+Gateway | API 网关+AI |
| **开源** | ✅ Apache | ✅ MIT | ❌ | ✅ MIT | ❌（CF 闭源） | ✅ MIT | ✅ Apache |
| **Provider 数** | 100+ | 1600+ | 200+ | 100+ | 数十 | 数十（仅观测） | 数十 |
| **加价** | 0% | 0% | 5.5% | 无 | 无 | 无 | 无 |
| **边缘性能** | ✅ ~50ms | ✅ 多区域 | ⚠️ 中等 | ❌ 取决于主机 | ✅ ~10-30ms | ❌ | ❌ |
| **LLM Security** | ✅ 内置 | ✅ 内置 | ❌ | ⚠️ 插件 | ❌ | ❌ | ⚠️ 插件 |
| **缓存** | ✅ KV | ✅ Redis + 语义 | ❌ | ⚠️ 内存 | ✅ KV | ⚠️ 外部 | ⚠️ 外部 |
| **Session Trace** | ✅ | ✅ | ❌ | ⚠️ 需配 | ❌ | ✅ 强 | ❌ |
| **权重路由** | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **语义路由** | ❌ | ✅（Martian 集成） | ✅ | ⚠️ 插件 | ❌ | ❌ | ⚠️ 插件 |
| **Prompt 管理** | ✅ V2 | ✅ | ❌ | ⚠️ 基础 | ❌ | ✅ | ❌ |
| **MCP** | ⚠️ 数据 MCP | ✅ Gateway | ❌ | ⚠️ 第三方 | ❌ | ⚠️ 客户端 | ✅ 插件 |
| **语义缓存** | ❌ | ✅ | ❌ | ✅ 插件 | ❌ | ❌ | ❌ |
| **Eval** | ⚠️ RAGAS | ✅ 自带 | ❌ | ⚠️ | ❌ | ✅ 强 | ❌ |
| **可观测后端** | ClickHouse | 自研 | 自研 | 无 | Workers Analytics | Postgres + ClickHouse | 任意 |
| **被收购** | ✅ Mintlify | ✅ Palo Alto | ❌ | ❌ | ❌ | ❌ | ❌（阿里） |
| **维护状态** | maintenance | 持续 | 持续 | 持续 | 持续 | 活跃 | 活跃 |
| **典型用户** | YC / SaaS | 企业 | 个人 / 长尾 | 自建 | 性能敏感 | 团队 / 合规 | 阿里系 |

### 17.2 与 LangSmith 的细节对比

| 维度 | Helicone | LangSmith |
|---|---|---|
| 开源 | ✅ | ❌ |
| 自托管 | ✅ Docker + Helm | ❌（仅 Enterprise） |
| 集成方式 | Proxy / Async SDK | Async SDK |
| 实时 Dashboard | ✅ 实时 | ⚠️ 缓存延迟 |
| 缓存 | ✅ | ❌ |
| Prompt 管理 | ✅ | ✅ |
| Tracing | ✅ | ✅（LangChain 强） |
| 实验 | ✅ | ✅ |
| 评分（Scoring） | ⚠️ RAGAS 集成 | ✅ 内置 |
| 用户追踪 | ✅ | ⚠️ 基础 |
| 安全 | ✅ Key Vault + Threat | ⚠️ 基础 |
| 价格 | $20/seat（最低） | $39/seat |

### 17.3 与 Portkey 的细节对比

| 维度 | Helicone | Portkey |
|---|---|---|
| 边缘部署 | ✅ Cloudflare | ⚠️ 多区域自建 |
| 加价 | 0% | 0% |
| Configs 抽象 | ❌ | ✅ 强 |
| 语义缓存 | ❌ | ✅ pgvector |
| 权重路由 | ❌ | ✅ |
| 集成 Guardrails | ✅（自带） | ✅（40+ 集成） |
| MCP Gateway | ❌ | ✅ |
| Prompt 编排 | ✅ V2 | ✅ |
| 商业 | maintenance | Palo Alto 旗下（被收购） |
| 适合 | 个人 / 早期团队 | 企业 / 合规 |
| 价格（2M logs/月） | $631 | 类似 |

### 17.4 与 Langfuse 的细节对比

| 维度 | Helicone | Langfuse |
|---|---|---|
| 核心定位 | Gateway + 观测 | 观测 + 轻量 Gateway |
| 自托管 | ✅ | ✅ |
| 边缘性能 | ✅ | ⚠️ 取决于部署 |
| Trace 协议 | OpenTelemetry / 自有 | OpenTelemetry（强） |
| 评估 | ⚠️ RAGAS | ✅ 内置 |
| 提示版本 | ✅ V2 | ✅ V1 |
| 实验管理 | ✅ | ✅ |
| 协议兼容 | ✅ 100+ 模型 | ⚠️ 需客户端 SDK |
| 收购 | ✅ Mintlify | ❌（独立） |
| 维护活跃度 | 慢 | 高 |

### 17.5 选型决策树

```
需要 LLM Security / 边缘性能 / 简单接入？
  → 是 → Helicone / Cloudflare AI Gateway
  → 否 ↓

需要 Config 抽象 / MCP Gateway / 语义缓存？
  → 是 → Portkey
  → 否 ↓

需要 OpenTelemetry 兼容 / 评估 / 提示实验？
  → 是 → Langfuse
  → 否 ↓

需要 200+ 长尾模型 / 个人开发者？
  → 是 → OpenRouter
  → 否 ↓

需要云原生 / 阿里系生态？
  → 是 → Higress
  → 否 → LiteLLM（自托管）
```

---

## 十八、维护模式下的产品风险与机会

### 18.1 风险盘点

| 风险 | 等级 | 说明 |
|---|---|---|
| **核心团队流失** | 🟡 中 | 全员加入 Mintlify，但社区维护者可接盘 |
| **新功能停滞** | 🟠 中-高 | maintenance mode 意味着不主动加新功能 |
| **收购方战略漂移** | 🟠 中-高 | Mintlify 主业是文档，LLM 观测非核心 |
| **Provider 新模型支持延迟** | 🟡 中 | "new models keep shipping" 是承诺，但速度可能放缓 |
| **价格变动** | 🟢 低 | 短期不会变 |
| **服务可用性** | 🟢 低 | "remain live for the foreseeable future" |
| **SLA 不可签** | 🟠 中-高 | 大客户签长约困难 |
| **竞品反超** | 🟠 中-高 | Langfuse、Portkey 都在加速 |

### 18.2 机会盘点

| 机会 | 等级 | 说明 |
|---|---|---|
| **开源 fork** | 🟢 高 | Apache 2.0，可直接 fork |
| **私有化部署** | 🟢 高 | Docker / Helm 完整 |
| **与 Mintlify 整合** | 🟡 中 | 文档 + 观测 + Agent = 完整工具链 |
| **Agent 时代基础设施** | 🟡 中 | LLM 观测是 AI Agent 必需 |
| **YC 校友网络** | 🟢 高 | 16k 客户 + YC 背书 |

### 18.3 决策建议

| 你的角色 | 建议 |
|---|---|
| **个人 / 早期项目** | ✅ 放心用，maintenance mode 足够用 1-2 年 |
| **中型 SaaS（< 100K req/day）** | ⚠️ 用，但准备迁出方案（导出日志到自建 ClickHouse） |
| **大型企业** | ❌ 不建议，已签合同的需评估退出 |
| **AI Agent 工具** | ✅ 仍可考虑，Session 追踪体验好 |
| **开源自部署** | ✅ 适合，Apache 2.0 仍可长期维护 |

---

## 十九、最佳实践与反模式

### 19.1 最佳实践

#### 19.1.1 必填 Header

```typescript
const client = new OpenAI({
  baseURL: "https://ai-gateway.helicone.ai",
  apiKey: process.env.HELICONE_API_KEY,
  defaultHeaders: {
    "Helicone-User-Id": userId,
    "Helicone-Property-Environment": process.env.NODE_ENV,
    "Helicone-Property-Feature": "code-completion"
  }
});
```

#### 19.1.2 Session 化 Agent

```typescript
const sessionId = crypto.randomUUID();

for (const step of workflowSteps) {
  await client.chat.completions.create(
    { /* ... */ },
    {
      headers: {
        "Helicone-Session-Id": sessionId,
        "Helicone-Session-Path": `/workflow/${step.name}`,
        "Helicone-Session-Name": "User Onboarding"
      }
    }
  );
}
```

#### 19.1.3 开发期开启缓存

```typescript
defaultHeaders: {
  "Helicone-Cache-Enabled": "true",
  "Cache-Control": "max-age=86400"  // 1 天
}
```

#### 19.1.4 用户级缓存命名空间

```typescript
{
  "Helicone-Cache-Enabled": "true",
  "Helicone-Cache-Seed": `user-${userId}`,
  "Cache-Control": "max-age=3600"
}
```

#### 19.1.5 双层缓存组合

```typescript
{
  "Helicone-Cache-Enabled": "true",
  "Helicone-Cache-Ignore-Keys": "prompt_cache_key",
  prompt_cache_key: `doc-${docId}`  // 透传给 Provider
}
```

#### 19.1.6 用 Custom Properties 切片

```typescript
{
  "Helicone-Property-Tier": "premium",
  "Helicone-Property-Region": "us-east",
  "Helicone-Property-A-B": "variant-A"
}
```

#### 19.1.7 Failover 策略

```typescript
{
  model: "gpt-4o-mini/azure,gpt-4o-mini"  // 先 Azure，再通用路由
}
```

### 19.2 反模式

#### 19.2.1 ❌ 用单一 API Key 跑全公司

```typescript
// ❌ 一个 key 所有人共用
apiKey: process.env.SHARED_HELICONE_KEY
```

→ 没有 user 归因、无法做计费、无法限流。

#### 19.2.2 ❌ 缓存用 random 字段当 key

```typescript
{
  "Helicone-Cache-Ignore-Keys": "request_id,timestamp"  // 缓存会失效
}
```

#### 19.2.3 ❌ LLM Security 高级模式用于生产热路径

```
Helicone-LLM-Security-Advanced: true  // +100-300ms 延迟
```

→ 应在 Playground / 内部工具用，生产热路径只用基础模式。

#### 19.2.4 ❌ 把 Helicone 当唯一 Cache

Helicone 缓存**不是**持久化层。重要数据要业务侧持久化。

#### 19.2.5 ❌ Session-Id 用固定字符串

```typescript
// ❌ 所有用户共享一个 session
"Helicone-Session-Id": "my-app"

// ✅ 每个会话独立
const sessionId = crypto.randomUUID();
```

#### 19.2.6 ❌ 自托管却只用默认密码

```bash
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin  # ⚠️ 必须改
BETTER_AUTH_SECRET=change-me-in-production  # ⚠️ 必须改
```

---

## 二十、未来展望（2026-2028）

### 20.1 短期（2026 内）

| 方向 | 概率 | 备注 |
|---|---|---|
| 维护模式持续 | 🟢 高 | 官方明确 |
| 安全更新 | 🟢 高 | 持续 |
| 新模型接入 | 🟢 高 | 公告承诺 |
| **新功能迭代** | 🔴 低 | 转向 Mintlify 战略 |
| 与 Mintlify 文档生态整合 | 🟡 中 | 团队会推动 |
| **Agent Tracing 升级** | 🟡 中 | 可能以"Agent 知识层"形态出现 |
| 价格上调 | 🟡 中 | maintenance 期间为对冲成本 |

### 20.2 中期（2027）

| 方向 | 概率 | 备注 |
|---|---|---|
| **产品并入 Mintlify** | 🟠 中-高 | maintenance 模式是过渡，不是终态 |
| 客户流失给 Langfuse | 🟠 中-高 | Langfuse 是当前最大对手 |
| 客户流失给自建 | 🟡 中 | 大客户自建 |
| **开源社区 fork 出现** | 🟡 中 | 16k 客户中一部分会自接盘 |

### 20.3 长期（2028+）

| 方向 | 概率 | 备注 |
|---|---|---|
| **Helicone 品牌消失** | 🟡 中 | 可能完全并入 Mintlify |
| **开源遗产延续** | 🟢 高 | Apache 2.0 + 16k 客户知识 |
| **AI Agent 可观测性标准** | 🟡 中 | Helicone 早期定义的概念会沉淀为行业标准 |

### 20.4 对自托管用户的建议

- 锁定当前版本（git tag）。
- 定期同步上游更新。
- 准备 LLM Security 替代（NeMo / Lakera / 自建）。
- 不要依赖 OpenTelemetry 自动探针以外的"新功能"。

---

## 二十一、参考资料与调研备注

### 21.1 官方一手资料

| 来源 | URL | 抓取日期 |
|---|---|---|
| GitHub README | https://github.com/Helicone/helicone | 2026-06-05 |
| 文档首页 | https://docs.helicone.ai/ | 2026-06-05 |
| AI Gateway Overview | https://docs.helicone.ai/gateway/overview | 2026-06-05 |
| Provider Routing | https://docs.helicone.ai/gateway/provider-routing | 2026-06-05 |
| Sessions | https://docs.helicone.ai/features/sessions | 2026-06-05 |
| Caching | https://docs.helicone.ai/features/advanced-usage/caching | 2026-06-05 |
| LLM Security | https://docs.helicone.ai/features/advanced-usage/llm-security | 2026-06-05 |
| Docker 自托管 | https://docs.helicone.ai/getting-started/self-host/docker | 2026-06-05 |
| Quickstart | https://docs.helicone.ai/getting-started/quick-start | 2026-06-05 |
| 文档 llms.txt | https://docs.helicone.ai/llms.txt | 2026-06-05 |
| Pricing | https://www.helicone.ai/pricing | 2026-06-05 |
| Changelog | https://www.helicone.ai/changelog | 2026-06-05 |
| Mintlify 收购公告 | https://www.helicone.ai/blog/joining-mintlify | 2026-06-05 |
| LangSmith 对比博客 | https://www.helicone.ai/blog/langsmith-vs-helicone | 2026-06-05 |

### 21.2 二手 / 行业资料

- YC 官网：https://www.ycombinator.com/companies/helicone
- Mintlify 官网：https://mintlify.com
- 行业分析：既往 00-20 系列报告中的 "可观测性" 与 "AI Gateway" 章节

### 21.3 调研方法论备注

- **数据时效**：所有数字截至 2026-06-05。Helicone 在 maintenance mode，数据快照可能在数月内稳定。
- **未抓取**：未抓取 `https://www.helicone.ai/models` 完整模型列表（页面 JS 动态加载），引用其 "100+ 模型" 表述。
- **未涉及**：未实际部署测试 Docker 镜像；自托管细节基于官方文档。
- **信息缺口**：
  - Enterprise 套餐的准确价格。
  - Credits 体系的实际营收模式。
  - LLM Security 的误报率官方数字。
  - 内部架构（如 Worker 内部多 Provider 翻译器的具体实现）。
  - 各 Provider 的实际 token 路由成功率。

### 21.4 调研结论（一句话）

> Helicone 是一个**曾经领先、产品成熟、生态广**的 AI Gateway + 可观测性平台，**2025-11 被 Mintlify 收购后进入 maintenance mode**。对个人 / 早期团队仍值得用，对大企业 / 强合规需求需评估退出方案，对开源自托管用户是**可 fork 的成熟基座**。

---

> 本报告为 "AI Gateway 单产品深挖" 系列第 N 篇，与既往 00-20 系列报告交叉引用：
> - 与 "可观测性" 相关：见 `04-observability-openllmetry.md`、`09-multimodal-gateway.md`
> - 与 "AI Gateway 协议" 相关：见 `01-llm-protocols.md`
> - 与 "成本模型" 相关：见 `13-cost-economics.md`
> - 与 "性能基准" 相关：见 `14-performance-benchmark.md`
> - 与 "竞品对比" 相关：见 `product-portkey-20260605.md`、`product-openrouter-20260605.md`、`product-litellm-20260605.md` 等

— 完 —
