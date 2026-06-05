# LangSmith 深度调研（2026-06）

> 系列：AI Gateway 单产品深挖 · 第 18 篇
> 目标项目：[LangSmith](https://docs.langchain.com/langsmith/home) ——  LangChain 商业公司推出的 LLM 观测 + 评估 + 部署一体化平台
> 调研日期：2026-06-05
> 性质：单产品深挖（覆盖项目背景、架构、协议、性能、部署、成本、生态、案例、对比）
> 信息来源：LangSmith 官方文档（docs.langchain.com/langsmith/*）、LangChain Pricing 页面、LangSmith Trust Center、LangChain 官方博客、既往 00-20 系列报告中 LangSmith 相关章节（01-llm-protocols / 04-observability-openllmetry / 05-agent-multi-step / 19-sla-service-governance）

---

## 目录

- [〇、关键前置判断：LangSmith 不是传统 AI Gateway，而是"观测 + 评估 + 部署 + Fleet + Engine"五合一的 Agent 平台](#〇关键前置判断langsmith-不是传统-ai-gateway而是观测--评估--部署--fleet--engine-五合一的-agent-平台)
- [一、项目速览与定位](#一项目速览与定位)
- [二、项目背景与公司](#二项目背景与公司)
- [三、产品矩阵：5 大子产品 + 1 个底座](#三产品矩阵5-大子产品--1-个底座)
- [四、架构设计：六服务 + 四存储的微服务架构](#四架构设计六服务--四存储的微服务架构)
- [五、协议支持：OpenTelemetry 兼容 + 多 Provider SDK](#五协议支持opentelemetry-兼容--多-provider-sdk)
- [六、AI Gateway 维度：Playground 转发 + Deployment 代理](#六ai-gateway-维度playground-转发--deployment-代理)
- [七、Trace 数据模型：Project / Trace / Run / Thread / Feedback](#七trace-数据模型project--trace--run--thread--feedback)
- [八、Evaluation：Online / Offline / Human-in-the-loop](#八evaluationonline--offline--human-in-the-loop)
- [九、Prompt Engineering 与 Hub](#九prompt-engineering-与-hub)
- [十、LangSmith Deployment：控制面 + 数据面 + LangGraph Platform](#十langsmith-deployment控制面--数据面--langgraph-platform)
- [十一、LangSmith Engine：自动故障诊断与修复建议](#十一langsmith-engine自动故障诊断与修复建议)
- [十二、LangSmith Fleet：无代码 Agent 构建器](#十二langsmith-fleet无代码-agent-构建器)
- [十三、LangSmith Sandboxes：Agent 代码执行沙箱](#十三langsmith-sandboxesagent-代码执行沙箱)
- [十四、性能数据、Trace 限额与延迟](#十四性能数据trace-限额与延迟)
- [十五、部署方式：Cloud / Hybrid / Self-Hosted / Standalone Server](#十五部署方式cloud--hybrid--self-hosted--standalone-server)
- [十六、成本模型：2026 年最新定价（Developer / Plus / Enterprise）](#十六成本模型2026-年最新定价developer--plus--enterprise)
- [十七、生态集成：100+ Provider 与框架](#十七生态集成100-provider-与框架)
- [十八、客户案例与典型用户](#十八客户案例与典型用户)
- [十九、优劣势分析](#十九优劣势分析)
- [二十、与其他 AI Gateway / 观测平台对比](#二十与其他-ai-gateway--观测平台对比)
- [二十一、最佳实践与反模式](#二十一最佳实践与反模式)
- [二十二、未来展望（2026-2028）](#二十二未来展望2026-2028)
- [二十三、参考资料与调研备注](#二十三参考资料与调研备注)

---

## 〇、关键前置判断：LangSmith 不是传统 AI Gateway，而是"观测 + 评估 + 部署 + Fleet + Engine"五合一的 Agent 平台

在进入产品细节之前，必须先讲清楚一个**根本性定位差异**，否则后文所有对比都会失焦：

> **LangSmith 不是一个 AI Gateway。**
> 它是一个**"LLM / Agent 应用的开发-调试-评估-部署-运维全生命周期平台"**。
> 其中只有很小一部分（LangSmith Playground、LangSmith Deployment 的代理层、SDK 内部的 OpenAI / Anthropic 客户端包装器）沾边"网关"概念。

### 0.1 与传统 AI Gateway 的能力对照

| 能力 | 典型 AI Gateway（Portkey / LiteLLM / One API / Kong / Envoy / APISIX / Higress） | LangSmith |
|---|---|---|
| OpenAI 兼容统一端点 | ✅ 核心能力 | ⚠️ 通过 wrap_openai / wrap_anthropic / wrap_gemini 间接提供；**LangSmith 端点本身不是 chat completions 端点** |
| 多 Provider 路由 | ✅ 核心能力 | ❌ 路由由业务代码自己选；LangSmith 不做"按价格/延迟自动选 provider" |
| Fallback / Retry / Circuit Breaker | ✅ 核心能力 | ❌ 需业务侧实现；Engine 提供**离线**修复建议，不是在线策略 |
| 语义缓存 / 精确缓存 | ✅ 核心能力 | ❌ 不做 |
| 速率限制（per-tenant QPS / TPM） | ✅ 核心能力 | ⚠️ 有平台级 ingest 限额（per-organization / per-hour），**不是 per-tenant 业务限流** |
| 成本归因 / 预算告警 | ✅ 核心能力 | ✅ 通过 trace metadata + dashboards 做归因；预算超支通过 Rules + webhook 通知 |
| Provider Key 集中托管 | ✅ 核心能力 | ⚠️ Playground 转发支持；业务侧仍持自己 key |
| **Trace / Span 采集** | ⚠️ 大多支持 OpenTelemetry 透传 | ✅ 核心能力，自有 RunTree 数据模型（OTel 概念同构） |
| **Evaluation 框架** | ⚠️ 少数支持（Portkey 实验） | ✅ 核心能力，Online + Offline + Human Annotation Queue |
| **Prompt 版本管理 / Hub** | ⚠️ 少数支持（Helicone V2、Portkey） | ✅ Prompt Hub + Playground + 协作 |
| **Dataset 管理** | ❌ 大多无 | ✅ 核心能力，Dataset 可无限期保留（即使 trace 已过期） |
| **Agent 部署平台** | ❌ 大多无 | ✅ LangSmith Deployment（控制面 + 数据面 + KEDA 自动扩缩） |
| **自动故障聚类 / 修复建议** | ❌ 无 | ✅ LangSmith Engine（仅 Plus / Enterprise） |
| **无代码 Agent 构建器** | ❌ 无 | ✅ LangSmith Fleet（仅 Plus / Enterprise） |
| **Agent 代码沙箱** | ❌ 无 | ✅ LangSmith Sandboxes（仅 Enterprise） |
| **OpenTelemetry 端点** | ✅ 多数支持 | ✅ OTel 语义对齐，但有自有 RunTree 数据模型（trace/run 一一对应） |
| **Self-hosted** | ✅ 多数可（K8s / Docker） | ✅ 可（K8s + Helm + KEDA + 外部 ClickHouse/Postgres/Redis），需 Enterprise license |
| **定价** | 多为免费 + BYOK；或按 token | **按 trace + 部署运行时间 + LCU + Sandbox 用量**计费，模型 token 单独付给 provider |

### 0.2 那 LangSmith 算什么？—— 重新定位

如果我们把"AI 应用的中间件栈"画成一张分层图：

```
┌─────────────────────────────────────────────────────────────┐
│  Application Code (LangChain / LlamaIndex / CrewAI / 自研)  │
├─────────────────────────────────────────────────────────────┤
│  AI Gateway 层     (Portkey / LiteLLM / One API / Kong…)   │ ← 流量代理
├─────────────────────────────────────────────────────────────┤
│  LLM Observability (LangSmith / Arize Phoenix / Langfuse)   │ ← 观测 & 评估
├─────────────────────────────────────────────────────────────┤
│  Agent 运行时      (LangGraph Platform / Temporal / …)      │ ← 状态机
├─────────────────────────────────────────────────────────────┤
│  LLM Provider      (OpenAI / Anthropic / Bedrock / vLLM)    │ ← 模型推理
└─────────────────────────────────────────────────────────────┘
```

**LangSmith 的独特之处在于：它同时覆盖了"观测层"和"Agent 运行时"两层**，并且在 2025-2026 年通过 **LangSmith Deployment / Fleet / Engine / Sandboxes / Insights / Chat** 6 个新模块向"端到端 Agent 平台"演进。它没有把 Portkey / LiteLLM 当作"对手"，而是默认业务侧**自己**用这些 AI Gateway 或直接调用 provider SDK，LangSmith 在旁路做观测 + 评估 + 部署。

### 0.3 为什么这个判断对采购决策至关重要

1. **不要把 LangSmith 当 AI Gateway 买**：如果你需要"统一 OpenAI 兼容端点 + Provider 路由 + Fallback + 缓存 + 限流"，LangSmith **不是答案**，应该看 Portkey / LiteLLM / One API / Kong / Envoy / APISIX / Higress。
2. **不要把 LangSmith 当纯观测工具买**：它已经有 Deployment / Fleet / Engine，2025-2026 年的定位是**"Agent 工厂"**，不是"trace viewer"。
3. **LangSmith 真正的杀手锏**：**与 LangChain / LangGraph 生态最深度的集成**（@traceable 装饰器、@langchain 集成、LangGraph Platform 控制面、Agent Protocol 标准的提出方之一）。
4. **价格模型独特**：**按 trace + 部署运行时间**计费，而非按 token。对于一个每天 100 万次 trace、每次 trace 平均 10 个 run 的应用，**月成本可能轻松超过 $1 万**（$0.0025/extended trace）。这与 Helicone（按 token）/ Langfuse（自托管免费）形成显著差异。

> 本报告对 LangSmith 的技术分析保持中立，但任何采购决策都必须把"它不是 AI Gateway、它正在演化为 Agent 平台"这两个前提考虑在内。

---

## 一、项目速览与定位

**一句话定位**：LangSmith 是 LangChain 商业公司推出的 **"AI Agent 与 LLM 应用的全生命周期平台"**，核心能力包括：Trace 观测、Evaluation 评估、Prompt Hub、Agent 部署（Deployment）、无代码 Agent（Fleet）、自动故障诊断（Engine）、Agent 代码沙箱（Sandboxes），提供 Cloud / Hybrid / Self-Hosted 三种部署形态，按 trace + 部署运行时间 + LCU + Sandbox 用量计费。

| 维度 | 数据 / 描述 |
|---|---|
| **厂商** | LangChain, Inc.（旧称 LangChain.ai / LangChain Labs） |
| **首次发布时间** | 2023-07（与 LangChain 1.0 同步开放） |
| **当前版本** | LangSmith 平台 v0.12+（截至 2026-06，Helm chart 持续迭代） |
| **当前状态** | ✅ Active 主导模式（**不是**维护模式，与 Helicone 被 Mintlify 收购形成对比） |
| **License** | **专有 SaaS** + Enterprise 自托管（Helm chart 公开但需 License Key） |
| **开源情况** | ⚠️ 仅 SDK 开源（`langsmith` PyPI / `langsmith` npm / `langsmith-java` Maven）；平台后端与 UI **闭源** |
| **GitHub** | `langchain-ai/langsmith-sdk`（SDK）；`langchain-ai/helm`（Helm chart） |
| **主要语言** | Python、TypeScript / JavaScript、Java / Kotlin |
| **核心架构** | 6 服务 + 4 存储：frontend (Nginx) / backend / platform-backend / queue / playground / ACE backend；ClickHouse / PostgreSQL / Redis / Blob |
| **支持 Provider** | OpenAI、Anthropic、Google Gemini、AWS Bedrock、Azure OpenAI、Mistral、Cohere、HuggingFace、Fireworks、Together、Groq、Ollama、vLLM 等 |
| **支持 Agent 框架** | LangChain、LangGraph、CrewAI、AutoGen、LlamaIndex、Pydantic AI、Vercel AI SDK、OpenAI Agents SDK、Semantic Kernel 等 30+ |
| **核心数据模型** | Project → Trace → Run（=OTel Span）→ Feedback；外加 Dataset / Experiment / Annotation Queue / Prompt |
| **部署形态** | Cloud（US / EU / APAC / AWS US）、Hybrid（控制面 SaaS + 数据面自托管）、Self-Hosted（K8s + Helm） |
| **数据保留** | SaaS 默认 400 天；自托管按存储配额 |
| **定价模型** | 按 trace 数 + 部署运行时间 + LCU（LangChain Compute Unit）+ Sandbox vCPU·h / GiB·h |
| **适用场景** | LangChain / LangGraph 项目的首选观测 + 评估 + 部署平台；自托管的合规与多租户隔离场景 |
| **主要竞品** | Langfuse（开源 + 自托管，免费）、Arize Phoenix（开源）、Helicone（维护模式）、Weights & Biases Weave、Galileo、Patronus、Comet、Datadog LLM Observability、New Relic AI Monitoring |

---

## 二、项目背景与公司

### 2.1 公司沿革

| 时间 | 事件 |
|---|---|
| 2022-10 | Harrison Chase 创立 LangChain（最初只是 GitHub README 的 Python 工具） |
| 2023-01 | LangChain 仓库 viral，GitHub stars 一个月破 20k |
| 2023-04 | LangChain 拿到 Benchmark Capital 领投的 $1,000 万 A 轮 |
| 2023-07 | **LangSmith 发布 Private Beta**，定位"LangChain 的商业控制台" |
| 2023-09 | LangSmith GA 公开（9 月宣布与 LangChain 1.0 整合） |
| 2023-12 | LangChain 完成 $3,500 万 B 轮（Sequoia 领投，估值 $2 亿） |
| 2024-02 | LangSmith 自托管（Self-Hosted）GA（Enterprise 计划） |
| 2024-06 | LangChain 完成 $7,500 万 C 轮（IVP 领投），估值 $3.5 亿 |
| 2024-10 | LangSmith **LangGraph Platform 公开预览**（即 LangSmith Deployment 前身） |
| 2025-01 | LangSmith 引入 **Online Evaluations**（自动评分） + **Rules**（Webhook 触发动作） |
| 2025-04 | LangChain 完成 $1.25 亿 D 轮（IVP / CapitalG / Sapphire 跟投），估值 **$11 亿**（独角兽） |
| 2025-06 | **LangSmith Engine** 公开预览（自动故障聚类 + 修复建议） |
| 2025-09 | **LangSmith Fleet** 公开预览（无代码 Agent 构建器） |
| 2025-11 | **LangSmith Deployment GA**（旧名 LangGraph Platform 重命名；控制面 + 数据面架构） |
| 2025-12 | **LangSmith Insights**（AI 驱动的 trace 分析）+ **LangSmith Chat**（工作区内的对话式分析） |
| 2026-01 | **LangSmith Sandboxes**（Agent 代码沙箱）发布 |
| 2026-03 | 自托管平台升级为 **Hybrid 模式**（控制面 SaaS + 数据面自托管），降低合规客户接入门槛 |
| 2026-05 | 当前状态：LangSmith 已成为 LangChain 公司的**核心商业产品线**（与 LangChain Open Source、LangGraph Open Source 并列的"三大产品线"） |

### 2.2 公司财务

- 累计融资：超过 **$2.25 亿**（A→B→C→D 轮 + 战略投资）
- 最新估值：**$11 亿**（2025-04 D 轮）
- 投资人：Benchmark、Sequoia、IVP、CapitalG、Sapphire Ventures、Bedrock
- 员工：约 200 人（2026-06，含 GTM、研发、产品）
- 客户数：未公开具体数字，但官方网站显示 **"Trusted by AI-native companies"** 包括 Klarna、Replit、Vellum、Rippling、JetBlue、Ally、Uber 等数百家企业

### 2.3 与 LangChain 开源生态的关系

这是 LangSmith 最大的**护城河**也是最大的**争议点**：

- **护城河**：LangChain / LangGraph 是 GitHub 上 star 数最高的 LLM 框架（LangChain 100k+ stars，LangGraph 15k+）。LangSmith 与它们的**集成是"开箱即用 1 个 env var"**：

  ```bash
  export LANGSMITH_TRACING=true
  export LANGSMITH_API_KEY=<key>
  # 任何 LangChain / LangGraph 应用立即把 trace 发到 LangSmith
  ```

- **争议点**：社区长期存在"LangChain 是不是在向 LangSmith 卖数据" / "LangSmith 是不是要 lock-in 用户"的讨论。LangChain 的应对是：**LangSmith SDK 完全开源**（`langchain-ai/langsmith-sdk`），任何厂商可以自部署采集后端；同时推出 **OpenTelemetry 兼容** 模式，让用户能把 trace 发到自己的 OTel collector，再转发到任意后端（LangSmith、Langfuse、Datadog、Jaeger 等）。

### 2.4 定位 vs 友商

| 平台 | 厂商 | 开源 | 定位 | 差异化 |
|---|---|---|---|---|
| **LangSmith** | LangChain | ❌（SDK 开源、平台闭源） | 全生命周期 Agent 平台 | 与 LangChain 生态最深度的集成；自带的 Deployment / Fleet / Engine / Sandboxes |
| **Langfuse** | Langfuse GmbH | ✅ MIT | 开源 LLM 观测 + 评估 | 自托管免费；Y Combinator；多模态评分 |
| **Arize Phoenix** | Arize AI | ✅ Apache 2.0 | 开源 LLM 观测 + 评估 | 强 evaluation；OpenInference 协议；自托管或云 |
| **Helicone** | Helicone（已被 Mintlify 收购） | ✅ Apache 2.0 | 轻量 LLM 观测 + 缓存 | 边缘部署；已被收购，处于 maintenance mode |
| **W&B Weave** | Weights & Biases | ❌ | ML 平台 + LLM 观测 | 强实验跟踪；与 W&B 模型注册集成 |
| **Galileo** | Galileo | ❌ | 评估 + 幻觉检测 | 强 hallucination / factuality 评估 |
| **Patronus** | Patronus AI | ❌ | 评估 + 模型对比 | 强 LLM-as-judge；production monitoring |
| **Datadog LLM Observability** | Datadog | ❌ | APM 厂商的 LLM 附加 | 与 Datadog APM/Logs 整合；企业级 |
| **New Relic AI Monitoring** | New Relic | ❌ | APM 厂商的 LLM 附加 | 与 New Relic APM 整合；OTel 端点 |

---

## 三、产品矩阵：5 大子产品 + 1 个底座

2025-2026 年 LangSmith 已经演化为**多产品矩阵**。理解这些子产品对采购决策至关重要。

### 3.1 矩阵总览

```
┌───────────────────────────────────────────────────────────────────┐
│                        LangSmith 平台                            │
│                      (Observability + Eval 底座)                 │
├───────────────────────────────────────────────────────────────────┤
│  1. Observability        2. Evaluation         3. Prompt Hub     │
│     (Trace 采集/查询)       (Online/Offline)     (Prompt 版本)  │
├───────────────────────────────────────────────────────────────────┤
│  4. LangSmith Deployment                                    ⭐     │
│     (控制面 + 数据面 + KEDA 自动扩缩)                          │
├───────────────────────────────────────────────────────────────────┤
│  5. LangSmith Fleet (无代码 Agent)                              ⭐ │
├───────────────────────────────────────────────────────────────────┤
│  6. LangSmith Engine (自动故障诊断)                             ⭐ │
├───────────────────────────────────────────────────────────────────┤
│  7. LangSmith Insights (AI 驱动分析) + Chat (工作区对话)         ⭐ │
├───────────────────────────────────────────────────────────────────┤
│  8. LangSmith Sandboxes (Agent 代码沙箱)                        ⭐ │
└───────────────────────────────────────────────────────────────────┘
                                                                  ⭐ 2025-2026 新增
```

### 3.2 各子产品一句话定位

| 子产品 | 一句话 | 适用人群 | 收费层级 |
|---|---|---|---|
| **Observability** | 采集、查询、可视化 LLM / Agent 应用的 trace 与 run | 所有 LLM 应用开发者 | Developer 免费 5k traces / 月 |
| **Evaluation** | Online（线上自动评分）+ Offline（数据集回放）+ Human（人工标注队列） | Prompt 工程师、应用负责人 | Plus / Enterprise |
| **Prompt Hub** | Prompt 版本管理、协作、Playground 调试 | Prompt 工程师 | Developer / Plus / Enterprise |
| **Deployment** | 把 LangGraph Agent 一键部署为生产服务（含 KEDA 自动扩缩、30+ API、Cron、Auth） | Agent 平台工程师 | Plus（1 个 Dev 部署）/ Enterprise（生产） |
| **Fleet** | 无代码 Agent 构建器（自然语言描述 + 模板 + 远程 MCP） | 业务方、PM | Plus / Enterprise |
| **Engine** | 自动 trace 故障聚类 → 根因诊断 → 修复建议 → 自动建 eval | Agent 平台 SRE | Plus / Enterprise |
| **Insights** | AI 驱动的 trace 趋势分析 | 应用负责人 | Plus / Enterprise |
| **Chat** | 工作区内的对话式 trace / prompt / 实验分析 | 所有用户 | Plus / Enterprise |
| **Sandboxes** | Agent 生成代码的隔离执行环境（vCPU·h + GiB·h + Storage·h 计费） | Coding Agent 开发者 | Enterprise |

### 3.3 子产品之间的关系

```
                        ┌─────────────────────┐
                        │   Business User     │
                        │  (PM / 业务方)      │
                        └─────────┬───────────┘
                                  │ 自然语言
                                  ▼
                        ┌─────────────────────┐
                        │   LangSmith Fleet   │  ← 无代码 Agent 构建
                        │  (Templates + MCP)  │
                        └─────────┬───────────┘
                                  │ 生成的 Agent
                                  ▼
┌──────────┐    ┌────────────────────────────────────────┐    ┌──────────┐
│  LangChain│    │      LangSmith Deployment              │    │ LLM      │
│  / LangG. │───▶│  (控制面 + 数据面 + KEDA + Ingress)    │───▶│ Provider │
│  App     │    │  30+ API endpoints (state, memory, ...) │    │ (OpenAI/ │
│  (Trace) │───▶│                                        │    │ Anthropic│
│          │    └────────┬───────────────────────────────┘    │ / ...)   │
└──────────┘             │ Trace                                └──────────┘
                         ▼
                   ┌─────────────────┐         ┌─────────────────┐
                   │   LangSmith     │ ──────▶ │  LangSmith      │
                   │  Observability  │  触发    │   Engine        │
                   │   (Trace 存储)  │         │ (聚类→诊断→修复)│
                   └────────┬────────┘         └─────────────────┘
                            │
                            ▼
                   ┌─────────────────┐         ┌─────────────────┐
                   │  LangSmith      │         │  LangSmith      │
                   │  Insights / Chat│         │  Sandboxes      │
                   │ (AI 分析)       │         │ (代码沙箱)      │
                   └─────────────────┘         └─────────────────┘
```

---

## 四、架构设计：六服务 + 四存储的微服务架构

LangSmith 自托管架构由 LangChain 官方维护的 Helm chart 描述，是公开的（但实际后端代码闭源）。

### 4.1 服务清单

来源：[Self-hosted LangSmith 官方文档](https://docs.langchain.com/langsmith/self-hosted)

| 服务 | 角色 | 技术栈（推测） | 公开端口 |
|---|---|---|---|
| **LangSmith Frontend** | Nginx + UI；API 入口；唯一需对外暴露 | Nginx + React/Vite | 80 / 443 |
| **LangSmith Backend** | CRUD API 入口；处理 frontend/SDK 请求；trace 预 ingest | Python（FastAPI 或类似） | 内部 |
| **LangSmith Platform Backend** | 认证、run ingest、其他高吞吐任务 | Python | 内部 |
| **LangSmith Queue** | 异步 ingest trace / feedback，处理重试与数据完整性 | Python + Redis Streams / Celery | 内部 |
| **LangSmith Playground** | 转发请求到各 LLM Provider；支持自定义 model server | Python + httpx | 内部 |
| **LangSmith ACE Backend**（Arbitrary Code Execution） | 在隔离环境执行用户自定义代码（Evaluation、Dataset 处理） | Python + 沙箱 | 内部 |

### 4.2 存储服务

| 存储 | 用途 | 推荐 |
|---|---|---|
| **ClickHouse** | 存储 trace / run / feedback（高吞吐 OLAP） | 强烈推荐外部托管（如 ClickHouse Cloud / AWS 托管） |
| **PostgreSQL** | 业务数据：Project、Dataset、Experiment、Prompt、User、Org | 强烈推荐外部（如 AWS RDS / Cloud SQL） |
| **Redis** | 队列、缓存、session 状态 | 强烈推荐外部 |
| **Blob Storage**（S3 / GCS / Azure Blob / MinIO） | 存储大体积 trace payload、Attachment、Artifact | 强烈推荐外部 |

> 文档原话："LangSmith will bundle all storage services by default. You can configure it to use external versions of all storage services. In a production setting, we **strongly recommend using external storage services**."

### 4.3 架构图（ASCII）

```
                                ┌──────────────────────────┐
                                │   Browser / SDK Client   │
                                │  (langsmith-py / -js /    │
                                │   -java SDK)             │
                                └────────────┬─────────────┘
                                             │ HTTPS
                                             ▼
                                ┌──────────────────────────┐
                                │   LangSmith Frontend     │
                                │   (Nginx + UI)           │
                                │   唯一对外暴露端点        │
                                └────────────┬─────────────┘
                                             │
                ┌────────────────────────────┼────────────────────────────┐
                │                            │                            │
                ▼                            ▼                            ▼
   ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
   │  LangSmith Backend     │  │  LangSmith Platform    │  │  LangSmith Playground  │
   │  (CRUD API)            │  │  Backend               │  │  (LLM Provider 转发)  │
   │  - Project/Dataset     │  │  - Auth/SSO            │  │  - OpenAI/Anthropic/  │
   │  - Prompt Hub          │  │  - Run Ingest          │  │    Bedrock/etc        │
   │  - Eval orchestration  │  │  - Run 预校验          │  │  - 自定义 model server│
   │  - Hub API             │  │  - 高吞吐路径          │  │                        │
   └────────────┬───────────┘  └──────────┬─────────────┘  └────────────┬───────────┘
                │                         │                             │
                │                         ▼                             │
                │            ┌────────────────────────┐                │
                │            │  LangSmith Queue       │                │
                │            │  (异步 trace 持久化)   │                │
                │            │  - 重试 / 完整性校验   │                │
                │            │  - 背压               │                │
                │            └────────────┬───────────┘                │
                │                         │                            │
                │                         ▼                            │
                │            ┌────────────────────────┐                │
                │            │  LangSmith ACE Backend │                │
                │            │  (Eval / Dataset 代码) │                │
                │            │  - 隔离沙箱            │                │
                │            └────────────┬───────────┘                │
                │                         │                            │
                ▼                         ▼                            ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                         Storage Layer                                 │
   ├──────────────────┬──────────────────┬──────────────────┬──────────────┤
   │   PostgreSQL     │   ClickHouse     │     Redis        │ Blob Storage │
   │   (业务数据)     │   (trace/run/   │   (queue/cache/  │ (大 payload) │
   │   Project/Dataset│    feedback OLAP)│    session)      │   S3/GCS/    │
   │   Experiment/    │                  │                  │   MinIO      │
   │   Prompt/User)   │                  │                  │              │
   └──────────────────┴──────────────────┴──────────────────┴──────────────┘

   ┌──────────────────────────────────────────────────────────────────────┐
   │   LangSmith Deployment Add-on (Enterprise / Plus)                    │
   │   - listener (监听 control plane 变更)                                │
   │   - operator (K8s CRD operator)                                      │
   │   - host-backend (control plane)                                      │
   │   - KEDA (事件驱动自动扩缩)                                           │
   │   - LangGraph Platform CRD                                            │
   └──────────────────────────────────────────────────────────────────────┘
```

### 4.4 数据流（Trace 采集）

```
1. SDK Client 调用 wrapped OpenAI/Anthropic
   └─▶ 客户端生成 RunTree（OpenTelemetry Span 同构）
        └─▶ batched async sender（默认 5s / 100 runs 一批）
             └─▶ POST https://api.smith.langchain.com/api/v1/runs/batch
                  └─▶ LangSmith Frontend (Nginx) 路由
                       └─▶ LangSmith Platform Backend
                            ├─ 预校验 (schema, size, project)
                            ├─ 写入 Redis Stream
                            └─ 返回 202 Accepted
                  └─▶ LangSmith Queue consumer
                       └─▶ ClickHouse INSERT
                            └─▶ PostgreSQL 更新 project metadata
```

**关键点**：

- **异步批处理**：SDK 默认 5s / 100 runs 一批，避免阻塞业务调用。
- **失败不致命**：网络错误 / 5xx 会在本地持久化（`/tmp/langsmith.db` 之类）并重试。
- **采样（sampling）**：可通过 `LANGSMITH_TRACING_SAMPLING_RATE` 控制 trace 采集比例。
- **单 trace 限额**：每个 trace 最多 25,000 个 run，超过会被拒。

### 4.5 单 trace 数据模型（OTel Span 同构）

```json
{
  "id": "run_01HXY...",
  "trace_id": "trace_01HXY...",
  "parent_run_id": null,
  "dotted_order": "20260605T000000.000000Z.0001.0001",
  "name": "ChatOpenAI",
  "run_type": "llm",
  "start_time": "2026-06-05T00:00:00.000Z",
  "end_time": "2026-06-05T00:00:01.234Z",
  "extra": {
    "metadata": {
      "ls_provider": "openai",
      "ls_model_name": "gpt-4o",
      "ls_model_type": "chat",
      "ls_temperature": 0.7,
      "ls_max_tokens": 1024
    },
    "invocation_params": {
      "model": "gpt-4o",
      "messages": [...]
    }
  },
  "inputs": {
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello"}
    ]
  },
  "outputs": {
    "generations": [
      [{"text": "Hi! How can I help?", "generation_info": {"finish_reason": "stop"}}]
    ]
  },
  "error": null,
  "tags": ["production", "chat"],
  "feedback": null,
  "session_id": "thread_abc123",
  "thread_id": "thread_abc123"
}
```

字段与 OpenTelemetry Span 的对应关系：

| OTel Span 字段 | LangSmith 字段 |
|---|---|
| trace_id | `trace_id` |
| span_id | `id` |
| parent_span_id | `parent_run_id` |
| name | `name` |
| start_time_unix_nano | `start_time` |
| end_time_unix_nano | `end_time` |
| kind | `run_type`（llm / tool / chain / retriever / embedding / prompt） |
| attributes | `extra.metadata` + `tags` + 部分 `inputs` |
| events | `extra.events` |
| status | `error` 字段（null = OK） |

---

## 五、协议支持：OpenTelemetry 兼容 + 多 Provider SDK

### 5.1 OpenTelemetry（OTel）兼容

LangSmith 2024 年开始支持 **OpenTelemetry Traces** 端点：

```bash
# 方式 1：使用 LangSmith SDK（推荐）
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<key>
# 任何 LangChain/LangGraph/CrewAI 应用自动采集

# 方式 2：通过 OTel Collector 转发
# otel-collector-config.yaml
exporters:
  otlphttp/langsmith:
    endpoint: https://api.smith.langchain.com/otel/v1/traces
    headers:
      x-api-key: ${env:LANGSMITH_API_KEY}
      Langsmith-Project: my-project

# 方式 3：直接用 OTel SDK 发 trace（语言无关）
# Python / JS / Go / Java / Rust 都可以
```

支持的 OTel 语义约定（Semantic Conventions）：

- `gen_ai.system` (OpenInference 兼容)
- `gen_ai.request.model`
- `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`
- `gen_ai.response.finish_reason`

> 注意：LangSmith 主推自己的 RunTree 数据模型，OTel 是**兼容端点**而非默认路径。要享受 LangSmith 的 Evaluation / Dataset / Prompt Hub 等能力，仍推荐用 LangSmith SDK。

### 5.2 多 Provider SDK 包装器

LangSmith SDK 提供 **40+ Provider 的自动 trace 包装器**：

```python
# Python
from openai import OpenAI
from langsmith.wrappers import wrap_openai
from langsmith import traceable, Client

# OpenAI
client = wrap_openai(OpenAI())

# Anthropic
from langsmith.wrappers import wrap_anthropic
client = wrap_anthropic(Anthropic())

# Google Gemini
from langsmith.wrappers import wrap_gemini
client = wrap_gemini(genai.Client())

# AWS Bedrock
from langsmith.wrappers import wrap_bedrock
client = wrap_bedrock(boto3.client("bedrock-runtime"))

# Mistral / Groq / Cohere / Together / Fireworks / Ollama / HuggingFace...
# 详见 https://docs.langchain.com/langsmith/integrations
```

```typescript
// TypeScript
import { OpenAI } from "openai";
import { wrapOpenAI } from "langsmith/wrappers";

const client = wrapOpenAI(new OpenAI());
// 所有 OpenAI 调用自动 trace
```

### 5.3 多 Agent 框架集成

| 框架 | 集成方式 |
|---|---|
| **LangChain** | 1 env var：`LANGSMITH_TRACING=true` |
| **LangGraph** | 1 env var：同上 + 自动跟踪 graph 节点 |
| **CrewAI** | 1 env var：`LANGSMITH_TRACING=true` |
| **AutoGen** | `autogen.langchain_integration` adapter |
| **OpenAI Agents SDK** | `tracing_processor` adapter |
| **Pydantic AI** | `instrument_pydantic_ai()` |
| **Vercel AI SDK** | `experimental_telemetry` |
| **LlamaIndex** | `LlamaIndexInstrumentor`（基于 OTel） |
| **Semantic Kernel** | `add_filter` + LangSmith SDK |
| **Haystack** | Haystack tracing → LangSmith |
| **DSPy** | `dspy.configure(langsmith_tracing=True)` |
| **自研 / 其他** | `@traceable` 装饰器 / `trace` context manager / `RunTree` 低阶 API |

### 5.4 不做的事

LangSmith SDK **不**做：

- ❌ OpenAI 兼容的统一 `/v1/chat/completions` 端点（业务代码要直接调 provider）
- ❌ 智能路由（按价格 / 延迟 / 健康度选 provider）
- ❌ Fallback / Retry / Circuit Breaker（业务侧自己实现）
- ❌ 语义缓存 / 精确缓存
- ❌ Token 限流（仅平台级 ingest 速率限制）

> **LangSmith 的设计哲学：透明（transparent）观测，不做流量代理**。所有"网关型"能力都被刻意排除，让用户在自己的 AI Gateway / provider SDK 上跑业务，LangSmith 在旁路采集 trace。

---

## 六、AI Gateway 维度：Playground 转发 + Deployment 代理

虽然 LangSmith 不是 AI Gateway，但有两块功能**沾边网关**：

### 6.1 LangSmith Playground

Playground 是 LangSmith UI 内的一个"调试沙盒"，允许用户在 UI 中：

- 选择一个 Prompt 模板（来自 Prompt Hub）
- 选择一个模型（OpenAI、Anthropic、Bedrock、Gemini、Ollama、自定义 endpoint）
- 输入变量 → 触发模型调用 → 查看输出

**Playground 的实现**就是"LangSmith 内部的一个 LLM 代理服务"（`langsmith-playground` 服务）：

- 接收 Playground 内部的 chat completions 请求
- 转发到对应 provider（OpenAI API、Anthropic API 等）
- 业务侧的 provider key 存在 LangSmith 后端（encrypted at rest）

**Playground 不是给生产用**：

- ❌ 没有 SLA
- ❌ 没有速率限制（限流到 provider key）
- ❌ 没有缓存
- ❌ 公开文档明确说"For the Playground feature"

### 6.2 LangSmith Deployment 的代理层

LangSmith Deployment 把 LangGraph Agent 部署为生产服务时，**数据面组件**会：

- 暴露 LangGraph SDK 兼容 API（30+ endpoints）
- 暴露 **OpenAI 兼容的 `/v1/chat/completions`** 端点（让 LangGraph Agent 也能被 OpenAI 客户端调用）
- 支持 **MCP Server** 模式（把 Agent 暴露为 MCP server）
- 支持 **streaming**（SSE）

> 这里的"OpenAI 兼容端点"**是给 LangGraph Agent 用的**，不是给多 Provider 路由用的。LangSmith 明确不把 Deployment 当 AI Gateway 卖。

### 6.3 与 AI Gateway 产品的本质区别

| 维度 | AI Gateway (Portkey / LiteLLM / Kong…) | LangSmith Deployment |
|---|---|---|
| 主要目的 | 多 provider 路由 + 限流 + 缓存 | 部署 LangGraph Agent 为生产服务 |
| 端点形态 | OpenAI 兼容统一端点 | LangGraph SDK + OpenAI 兼容 + MCP server |
| 路由能力 | ✅ 核心 | ❌ 无 |
| Fallback | ✅ 核心 | ❌ 无（业务代码自己 try/except） |
| 缓存 | ✅ 核心 | ❌ 无 |
| 限流 | ✅ 核心 | ⚠️ KEDA 按队列扩缩（不是 per-user 限流） |
| 可观测性 | 透传 trace 到 OTel / 自身采集 | 自动把 trace 发到 LangSmith |

---

## 七、Trace 数据模型：Project / Trace / Run / Thread / Feedback

LangSmith 的核心数据模型与 OpenTelemetry 同构但有自己的命名习惯。

### 7.1 概念层级

```
Organization (组织)
  └── Workspace (工作区)         ← Plus / Enterprise 才有
        └── Project (项目)         ← trace 容器
              ├── Trace           ← 一次请求
              │     ├── Run        ← 一次 LLM/tool/chain 调用
              │     ├── Run
              │     └── ...
              ├── Dataset          ← ground truth 数据集
              │     ├── Example
              │     └── ...
              ├── Experiment       ← 一次评估运行
              │     └── ExampleResult
              ├── Annotation Queue ← 人工标注队列
              ├── Prompt           ← Prompt Hub 中的 prompt
              └── Deployment       ← 部署的 LangGraph Agent
```

### 7.2 Trace 与 Run 的关键约束

| 约束 | 数值 | 来源 |
|---|---|---|
| 单 trace 最多 run 数 | **25,000** | docs.langchain.com/langsmith/observability-concepts |
| 默认数据保留 | 400 天（SaaS） | docs.langchain.com/langsmith/administration-overview |
| 单 trace 最大 size | 1 MB / run | administration-overview |
| 默认批处理间隔 | 5s / 100 runs | SDK 默认值 |
| 失败重试 | 指数退避，最多重试 6 次 | SDK 实现 |
| 离线缓存 | 失败时本地持久化（SQLite） | SDK 实现 |
| 采样率 | `LANGSMITH_TRACING_SAMPLING_RATE=0.1` | 环境变量 |

### 7.3 Run 的 `run_type` 类型

| run_type | 含义 | 例子 |
|---|---|---|
| `llm` | LLM 调用 | OpenAI ChatCompletion, Anthropic Message |
| `tool` | 工具调用 | `get_weather`, `search_db` |
| `chain` | 业务链 | ReAct chain, SQL chain |
| `retriever` | 检索调用 | Vector store query, BM25 search |
| `embedding` | Embedding 调用 | OpenAI embeddings, Cohere embed |
| `prompt` | Prompt 模板渲染 | `PromptTemplate.format()` |
| `parser` | 输出解析 | `StrOutputParser`, `PydanticOutputParser` |
| `agent` | Agent 整体 | 一个 LangGraph agent.run() |
| `custom` | 用户自定义 | 任意业务函数 |

### 7.4 Thread：多轮对话追踪

通过在 metadata 中传 `session_id` / `thread_id` / `conversation_id` 中的任意一个，多个 trace 会被关联为同一个 Thread：

```python
from langsmith import traceable

@traceable
def chat_turn(user_input: str, thread_id: str):
    # 业务逻辑：读历史 → 调 LLM → 返回
    return response

chat_turn("Hello", thread_id="user_42")
chat_turn("What did I say?", thread_id="user_42")  # 同一个 thread
```

UI 端可在 "Threads" 视图看到整个会话的 trace 序列。

### 7.5 Feedback：人工 + 自动评分

Feedback 是 LangSmith 的**评估核心**。每条 feedback 绑定到某个 run：

```python
from langsmith import Client
client = Client()

# 人工反馈
client.create_feedback(
    run_id="run_01HXY...",
    key="correctness",
    score=1,  # 0/1 二值
    comment="响应正确"
)

# LLM-as-judge 自动反馈
from langchain.evaluation import load_evaluator
evaluator = load_evaluator("labeled_criteria", criteria="correctness")
client.create_feedback(
    run_id="run_01HXY...",
    key="llm_judge_correctness",
    score=evaluator.evaluate_strings(...)["score"]
)

# 类别反馈（categorical）
client.create_feedback(
    run_id="run_01HXY...",
    key="category",
    value="user_frustrated"  # 不是 score
)
```

Feedback 的关键设计：

- **绑定 run**：每条 feedback 必须有 `run_id`
- **可聚合**：UI 中可按 feedback 维度做趋势分析
- **可触发规则**：feedback < 0.5 时可触发 webhook → 重新评估 / 报警
- **可作为 Online Eval 的 ground truth**

---

## 八、Evaluation：Online / Offline / Human-in-the-loop

LangSmith 的 Evaluation 是它与 Helicone / Langfuse / Arize Phoenix **拉开差距**的核心能力。

### 8.1 Evaluation 三种模式

```
┌──────────────────────────────────────────────────────────┐
│                    LangSmith Evaluation                  │
├──────────────────┬──────────────────┬────────────────────┤
│  Offline Eval   │   Online Eval    │  Human Annotation  │
│  (回放数据集)    │  (实时评分)      │  (人工标注队列)    │
├──────────────────┼──────────────────┼────────────────────┤
│  Dataset 中有    │  每个生产 trace   │  抽样 + 标注       │
│  ground truth    │  立即打分        │  UI 标注 + 反馈    │
│  → 跑 Agent     │  → 触发规则      │  → 进 Dataset      │
│  → 比对结果     │  → 报警/重新评估  │  → 进 Experiment   │
└──────────────────┴──────────────────┴────────────────────┘
```

### 8.2 Offline Evaluation

把 Dataset + Experiment + Evaluator 组合起来跑批：

```python
from langsmith import Client
from langsmith.evaluation import evaluate
from langchain.evaluation import load_evaluator

client = Client()

# 1. 准备 Dataset
dataset = client.create_dataset("qa_v1")
client.create_examples(
    inputs=[
        {"question": "LangSmith 是什么？"},
        {"question": "LangChain 是谁创立的？"},
    ],
    outputs=[
        {"answer": "LangChain 公司推出的 LLM 观测平台"},
        {"answer": "Harrison Chase"},
    ],
    dataset_id=dataset.id,
)

# 2. 定义 target function
def target(inputs: dict) -> dict:
    return {"answer": openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": inputs["question"]}]
    ).choices[0].message.content}

# 3. 跑 Evaluation
results = evaluate(
    target,
    data=dataset.name,
    evaluators=[
        load_evaluator("labeled_criteria", criteria="correctness"),
        load_evaluator("qa"),  # built-in
    ],
    experiment_prefix="gpt-4o-baseline",
)

# UI 中会看到：每个 example 的输入、目标输出、模型输出、所有 evaluator 分数
```

### 8.3 Online Evaluation

Online Eval 是在**生产 trace 进入**时自动跑的评估器（不需 Dataset）：

```python
from langsmith.evaluation import evaluate, RunEvaluator

class LengthCheckEvaluator(RunEvaluator):
    def evaluate_run(self, run, example=None):
        output = run.outputs["choices"][0]["message"]["content"]
        return {
            "key": "response_length_ok",
            "score": 1 if 50 < len(output) < 500 else 0
        }

# 在 UI 的 Project → Settings → Online Evaluators 中配置
# 支持的 evaluator：内置 (qa, criteria, labeled_criteria, embedding_distance, string_distance)
# 自定义 evaluator（通过 Python SDK / Webhook）
# LLM-as-judge evaluator
```

Online Eval 的输出会：

- 写入 ClickHouse
- 触发 Rules（webhook）
- 出现在 Insights 仪表盘

### 8.4 Human Annotation Queue

把生产 trace 抽样 → 人工标注：

1. 配置 sampling rate（10% / 100% / 按规则）
2. 配置标注 schema（多选、单选、文本）
3. 标注员在 UI 中给 run 打分
4. 标注结果写入 Dataset → 跑 Offline Eval
5. 形成"human-in-the-loop"持续评估闭环

### 8.5 Experiment Comparison

LangSmith UI 中可**并排比较**多个 experiment：

- 横轴：experiment
- 纵轴：evaluator + 分数
- 单元格颜色：绿（高分）/ 红（低分）
- 点击单元格 → 跳到该 example 的 trace

这是 LangSmith 相对 Langfuse / Arize Phoenix 的**显著优势**。

---

## 九、Prompt Engineering 与 Hub

### 9.1 Prompt Hub

Prompt Hub 是 LangSmith 的**Prompt 版本管理 + 协作**系统。

```python
from langchain import hub

# 拉取公开 prompt
prompt = hub.pull("rlm/reduce-custom-calls")

# 推送自己的 prompt
from langsmith import Client
client = Client()
client.push_prompt(
    "customer-support-v1",
    object=ChatPromptTemplate.from_messages([
        ("system", "You are a helpful customer support agent."),
        ("human", "{question}")
    ])
)

# 在 LangSmith UI 中查看、版本化、协作
# 公开/私有、tag、owner、commit message
```

Prompt Hub 的关键能力：

- **版本化**：每次 push 是一个 immutable 版本（commit hash）
- **协作**：支持 owner、tag、commit message
- **公开/私有**：可以发布到公共 Hub（类似 HuggingFace）
- **Playground 集成**：UI 中直接选 prompt + 选模型 + 调试
- **拉取即用**：`hub.pull("owner/name@v1.2")` 指定版本

### 9.2 Playground

UI 中的 Prompt 调试沙盒：

- 选 prompt 模板
- 选模型（OpenAI / Anthropic / Bedrock / Gemini / 自定义）
- 填变量
- 看输出
- 多模型对比（左 Claude 右 GPT-4o 同一 prompt）
- 输出 → Dataset（把 playground 输出保存为 ground truth）

### 9.3 Prompt Caching 与 Commit

Prompt Hub 的"commit"机制（2024-2025 引入）：

- 每个 commit 是一个 immutable snapshot
- commit hash 引用具体的 template 字符串 + 模型配置
- 业务代码可锁定 commit（`@v1.2`），不会因为新 push 而意外变更
- 支持 A/B 测试（用不同 commit 跑同一个 experiment）

---

## 十、LangSmith Deployment：控制面 + 数据面 + LangGraph Platform

LangSmith Deployment 是 2025-11 GA 的旗舰子产品，把 LangGraph Agent 一键部署为生产服务。

### 10.1 架构：控制面 + 数据面

```
                    ┌──────────────────────────────────┐
                    │         Control Plane            │
                    │  (LangSmith SaaS 托管 或 自托管)  │
                    │                                  │
                    │  - Deployment 配置存储           │
                    │  - 版本管理                      │
                    │  - 审计日志                     │
                    │  - UI/API                       │
                    └──────────────┬───────────────────┘
                                   │ 监听变更
                                   ▼
                    ┌──────────────────────────────────┐
                    │         Data Plane               │
                    │  (用户的 K8s 集群)                │
                    │                                  │
                    │  - listener (CRD operator)       │
                    │  - operator                      │
                    │  - LangGraph CRD                 │
                    │  - Agent Pods (用户代码)          │
                    │  - KEDA (事件驱动扩缩)            │
                    └──────────────────────────────────┘
```

### 10.2 部署一个 LangGraph Agent

```python
# langgraph_agent.py
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph_sdk import get_client

# 定义 graph
def should_continue(state: MessagesState):
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END

graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode([get_weather]))
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")
app = graph.compile()
```

```bash
# 用 LangGraph CLI 部署
pip install langgraph-cli
langgraph build -t my-agent:latest
langgraph deploy --config langgraph.json

# 部署后获得一个 URL
# https://my-deployment.us.langgraph.app
# 提供 30+ API endpoints
```

### 10.3 部署后暴露的 API（30+）

| Endpoint | 用途 |
|---|---|
| `/threads` | 创建/查询/删除 thread（多轮对话） |
| `/threads/{thread_id}/state` | 读/写 thread state |
| `/threads/{thread_id}/history` | 读 thread 历史 |
| `/threads/search` | 按 metadata 搜索 thread |
| `/runs` | 同步运行（streaming） |
| `/runs/stream` | SSE 流式运行 |
| `/runs/wait` | 等待运行完成 |
| `/runs/cancel` | 取消运行 |
| `/assistants` | CRUD assistants（=部署的 graph） |
| `/assistants/search` | 搜索 assistants |
| `/store` | 长期 memory 存储 |
| `/store/search` | 搜索 memory |
| `/cron` | Cron 调度（按 schedule 触发 run） |
| `/mcp` | 把整个 assistant 暴露为 MCP server |
| `/v1/chat/completions` | OpenAI 兼容端点（用 graph 处理请求） |
| `/feedback` | 提交 feedback |
| ... | 共 30+ |

### 10.4 自动扩缩：KEDA

```yaml
# KEDA ScaledObject
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-agent-scaler
spec:
  scaleTargetRef:
    name: my-agent-deployment
  triggers:
  - type: langgraph-queue
    metadata:
      queueLength: "5"  # 队列里 5 个待处理任务就扩容
      activationQueueLength: "1"
```

KEDA 监听 LangSmith 内部的 task queue，**按队列长度自动扩缩**（0 → N）。

### 10.5 与 LangGraph Platform 的关系

2025-11 前，LangGraph Platform 是独立产品；2025-11 后被**吸收**为 LangSmith Deployment。变化：

- 旧 LangGraph Platform 用户 → 自动迁移到 LangSmith Deployment
- API 完全兼容（`langgraph-sdk` Python / JS）
- 增加了与 LangSmith Observability 的**深度集成**（部署的 Agent 自动把 trace 发到 LangSmith）

### 10.6 部署模式

| 模式 | 适用 | 价格 |
|---|---|---|
| **Cloud（LangChain 托管）** | 不想运维 K8s 的团队 | Plus（$0.0036/min production, $0.0007/min development） |
| **Self-Hosted（用户 K8s）** | 已有 K8s 集群 + 合规要求 | Enterprise license（contact sales） |
| **Standalone Server** | 单机/单 VM 部署（无 K8s） | 轻量级替代方案 |

---

## 十一、LangSmith Engine：自动故障诊断与修复建议

LangSmith Engine 是 2025-06 公开预览的**AI-driven**子产品，定位是"自动 trace 故障聚类 → 根因诊断 → 修复建议"。

### 11.1 工作流

```
1. Trace 流入 LangSmith
     ↓
2. Engine 后台每天/每小时聚类
   - 把"相似失败模式"的 trace 聚为一组
   - 例子：所有 "tool call 返回 500" 的 trace
     ↓
3. 对每个 cluster 做根因分析
   - LLM-as-judge 分析 sample trace
   - 提取常见模式（错误类型 / 触发条件 / 影响范围）
     ↓
4. 生成修复建议
   - 修改 prompt
   - 加 retry
   - 调整 tool schema
   - 换 provider
     ↓
5. 创建 Eval 自动验证
   - 修复建议 → 生成 Dataset
   - 跑 Offline Eval 验证修复有效
     ↓
6. 用户审阅 / 应用修复
   - 一键应用（修改 prompt）
   - 手动应用（修改代码）
```

### 11.2 关键能力

| 能力 | 描述 |
|---|---|
| **Cluster Agent Behavior** | 把相似 trace 聚类为 issues（自动发现"3% 的用户遇到 tool timeout"） |
| **Diagnose Code Failures** | LLM-as-judge 读 sample trace + 代码 → 推测根因 |
| **Recommend Fixes** | 生成"修改 prompt X 段"、"加 retry 3 次"等可执行建议 |
| **Create Datasets** | 把失败 trace 转为 Dataset（用于后续 regression test） |
| **Create Online/Offline Evals** | 把根因转为 Eval（防止回归） |

### 11.3 与传统 Observability 的区别

| 维度 | 传统 Observability (Datadog / Honeycomb) | LangSmith Engine |
|---|---|---|
| 故障发现 | 人眼看 dashboard | 自动聚类 |
| 根因分析 | 人工 debug | LLM-as-judge 推测 |
| 修复建议 | 无 | 自动生成 |
| 回归保护 | 无 | 自动建 Eval |

> **这是 LangSmith 真正的"AI-native"差异化**：把"运维"也变成 AI 驱动。

---

## 十二、LangSmith Fleet：无代码 Agent 构建器

LangSmith Fleet 是 2025-09 公开预览的**无代码 Agent**子产品。

### 12.1 定位

- **目标用户**：业务方、PM、非工程师
- **使用方式**：自然语言描述 Agent → Fleet 自动构建 → 部署
- **能力**：模板、远程 MCP server、API trigger、模型选择

### 12.2 典型流程

```
1. 选模板（"Customer Support"、"Research Assistant"、"Data Analyst"）
   或从自然语言开始描述
2. 配置工具（通过远程 MCP server 添加）
3. 选模型（gpt-4o / claude-3.5-sonnet / 用户自选）
4. 描述 Agent 行为（自然语言）
5. 部署（点击 "Deploy"）
6. 触发：API / Webhook / Schedule
7. Trace 自动进入 LangSmith Observability
```

### 12.3 价格

- **Developer plan**：1 个 Fleet Agent
- **Plus plan**：500 / 月 included，额外 $0.05/Fleet run
- **Enterprise**：custom

> **争议点**：Fleet 实质上是"业务方绕过工程团队"的产品，可能引起工程团队反感。但 LangChain 官方立场是"Fleet 让 PM 也能快速验证 idea，然后工程团队可以接管"。

---

## 十三、LangSmith Sandboxes：Agent 代码执行沙箱

LangSmith Sandboxes 是 2026-01 发布的**Agent 代码执行环境**子产品。

### 13.1 定位

- **目标场景**：Coding Agent（如 Devin、Cognition、Replit Agent 的代码生成）
- **核心需求**：Agent 生成的代码需要在隔离环境执行
- **LangSmith Sandboxes 提供**：vCPU + Memory + Storage + 自定义 image + 端口隧道

### 13.2 能力

| 能力 | 描述 |
|---|---|
| **Ephemeral, isolated** | 每个 session 一个隔离环境 |
| **Scale to 1000s on demand** | 弹性扩缩到上千个并发 |
| **Bring your own image** | 自定义 Docker image |
| **Configurable TTLs** | 短任务（10s）到长任务（24h） |
| **Snapshot and fork** | 状态可保存 + 分叉（类似 Git branch） |
| **Port tunneling** | 把远程端口映射到本地 |
| **Sandbox CLI** | `langsmith sandbox create/exec/snapshot/fork` |
| **Auth proxy** | 自定义 auth callback（控制 sandbox 访问外部资源） |

### 13.3 价格

| 资源 | 价格 |
|---|---|
| vCPU | $0.0576 / vCPU-hr |
| Memory | $0.0185 / GiB-hr |
| Storage | $0.000123 / GiB-hr |
| 计费粒度 | 秒 |

### 13.4 与同类对比

| 平台 | 定位 | 差异 |
|---|---|---|
| **LangSmith Sandboxes** | LangSmith 内的 Coding Agent 沙箱 | 与 LangSmith Observability 深度集成 |
| **E2B** | 通用 AI 代码沙箱 | 独立产品，更通用 |
| **Modal** | GPU 沙箱 + serverless compute | 强调 GPU |
| **Replicate** | 推理 API + cog 容器 | 强调 ML 模型 |
| **Cloudflare Workers** | Edge compute | 强调边缘 |
| **AWS Fargate / Cloud Run** | 通用容器 | 强调云原生 |

---

## 十四、性能数据、Trace 限额与延迟

### 14.1 平台级 Trace Ingest 速率限制

| 限制 | 数值 |
|---|---|
| Trace Ingest Rate (Plus) | **5,000 traces / 小时**（可申请提升） |
| Trace Ingest Rate (Enterprise) | Custom |
| Trace Size Limit | **1 MB / trace** |
| Single Run Size Limit | 1 MB / run |
| Trace 最多 Run 数 | 25,000 / trace |
| Single Project 最多 Run 数 | Unlimited（受 ingest 速率限制） |
| API Rate Limit | 10,000 req/min（默认） |
| Webhook Rate Limit | 100 req/min / org |

### 14.2 SDK 端延迟

LangSmith SDK 的设计目标是**对业务延迟 < 5%**：

| 指标 | 数值 |
|---|---|
| **wrap_openai 调用额外延迟** | ~5-10ms（p50），~20-30ms（p99） |
| **批处理间隔** | 5s（可配 `LANGSMITH_BATCH_SIZE` / `LANGSMITH_BATCH_INTERVAL_MS`） |
| **批大小** | 100 runs（可配） |
| **SDK 内存占用** | 约 30-50 MB（trace 缓存） |
| **网络上传** | 异步，不阻塞业务 |
| **失败重试** | 指数退避，6 次 |
| **离线持久化** | 失败时写入本地 SQLite，重连后上传 |

### 14.3 平台端查询性能

| 指标 | 数值 |
|---|---|
| **Trace 写入 → UI 可查** | ~1-3 秒 |
| **简单查询（project 全部 trace）** | < 500ms（p99） |
| **复杂查询（多 filter + 全文搜索）** | 1-3s（p99） |
| **Dashboards 加载** | 2-5s（ClickHouse 聚合） |
| **Bulk export** | 10万 trace / min |

### 14.4 部署后 Agent 性能

| 指标 | 数值 |
|---|---|
| **Deployment 冷启动** | ~3-10s（拉镜像） |
| **Deployment 热启动** | < 1s |
| **KEDA 扩缩时间** | 30-60s（从 0 → N） |
| **Stream first token 延迟** | ~100-300ms（业务侧 LLM 调用决定） |
| **Deployment 内存基线** | 500 MB / pod |

### 14.5 性能数据来源说明

⚠️ **坦白**：上述性能数据是**从官方文档 + 公开博客 + 客户案例 + LangChain 工程师公开演讲**汇总的估算，**不是 LangChain 官方 benchmark 报告**。建议在采购决策前要求 LangChain 销售提供**自己 workload 的 POC 数据**。

---

## 十五、部署方式：Cloud / Hybrid / Self-Hosted / Standalone Server

### 15.1 Cloud

```bash
# 业务代码侧
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=lsv2_...
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com  # US 默认
# 或 EU：https://eu.api.smith.langchain.com
# 或 APAC：https://apac.api.smith.langchain.com
# 或 AWS US：https://aws.api.smith.langchain.com
```

- 数据存在 LangChain 托管的 ClickHouse/PostgreSQL/Redis
- 多区域：US（默认）、EU（GDPR 友好）、APAC、AWS US
- 数据保留：默认 400 天
- 合规：SOC 2 Type 2、HIPAA、GDPR

### 15.2 Hybrid（2026-03 引入）

```
┌─────────────────────┐         ┌─────────────────────┐
│   Control Plane     │         │   Data Plane        │
│   (LangChain SaaS)  │ ──API──▶│   (用户 VPC)         │
│                     │         │                     │
│  - UI               │         │  - ClickHouse       │
│  - API              │         │  - PostgreSQL       │
│  - Auth             │         │  - Redis            │
│  - Deployment mgmt  │         │  - Blob Storage     │
└─────────────────────┘         └─────────────────────┘
```

- 控制面：LangChain SaaS（管理 UI / 部署配置）
- 数据面：用户 VPC（所有 trace 数据）
- **优势**：合规 + 不用自己运维 LangSmith 平台
- **价格**：Enterprise（custom）

### 15.3 Self-Hosted（K8s + Helm）

```bash
# 1. 准备 K8s 集群
# - AWS EKS / GCP GKE / Azure AKS / 自建 K8s
# - 至少 3 个 worker node
# - Persistent Volume 支持
# - LoadBalancer / Ingress

# 2. 拉取 Helm chart
helm repo add langchain https://langchain-ai.github.io/helm
helm repo update

# 3. 准备 config
cat > langsmith_config.yaml <<EOF
config:
  hostname: langsmith.example.com
  auth:
    enabled: true
    google: { enabled: true, ... }
    github: { enabled: true, ... }

# External storage (强烈推荐)
postgres:
  external: true
  url: postgresql://user:pass@rds-host:5432/langsmith

clickhouse:
  external: true
  url: clickhouse://user:pass@clickhouse-host:9000/langsmith

redis:
  external: true
  url: redis://redis-host:6379

blobStorage:
  external: true
  s3:
    bucket: langsmith-blobs
    region: us-east-1
    accessKey: ...
    secretKey: ...
EOF

# 4. 安装
helm upgrade -i langsmith langchain/langsmith \
  --values langsmith_config.yaml \
  --version 0.12.x \
  -n langsmith --create-namespace --wait --debug

# 5. 验证
kubectl get pods -n langsmith
```

### 15.4 Standalone Server（轻量级部署）

2025 年 12 月新增的部署模式——**不需要 K8s**，单机/单 VM 即可跑 LangSmith：

- 适用于：< 5 个 trace / 秒的小团队；本地开发；CI 环境
- 不支持：Deployment 自动化、KEDA、Cluster 模式
- 官方 docker image：`langchain/langsmith-standalone`

### 15.5 部署对比表

| 维度 | Cloud | Hybrid | Self-Hosted | Standalone |
|---|---|---|---|---|
| 控制面 | LangChain SaaS | LangChain SaaS | 用户 K8s | 单机 |
| 数据面 | LangChain SaaS | 用户 VPC | 用户 K8s | 单机 |
| 运维负担 | 零 | 中 | 高 | 极低 |
| 数据合规 | 一般（多区域可选） | 强 | 强 | 强 |
| 支持 Deployment | ✅ | ✅ | ✅ | ❌ |
| 支持 Fleet | ✅ | ✅ | ✅ | ❌ |
| 支持 Engine | ✅ | ✅ | ✅ | ⚠️ 部分 |
| 适用规模 | 任意 | 中大 | 大 | 小 |
| 价格 | Plus / Enterprise | Enterprise | Enterprise | Plus 起 |

---

## 十六、成本模型：2026 年最新定价（Developer / Plus / Enterprise）

### 16.1 订阅层级

| 维度 | Developer | Plus | Enterprise |
|---|---|---|---|
| **价格** | **免费** | **$39/座/月**（unlimited seats） | **Custom**（按 trace + 部署 + LCU + Sandbox） |
| **目标用户** | 个人开发者、PoC | 团队、中小企业 | 大企业、合规需求 |
| **Trace 基础额度** | 5,000 traces / 月 | 10,000 traces / 月 | Custom |
| **超出单价** | $0.0025/extended trace | $0.0025/extended trace | Custom |
| **数据保留** | 14 天 | 400 天 | Custom（可设无限） |
| **Seats** | 1 | Unlimited | Unlimited |
| **SSO** | Google / GitHub | Custom SSO | Custom SSO（OIDC/SAML） |
| **Self-Hosted** | ❌ | ❌ | ✅（add-on） |
| **Deployment** | ❌ | 1 free Dev | Custom |
| **Fleet** | 1 Agent | 500 / 月 included | Custom |
| **Engine** | ❌ | ✅ | ✅ |
| **Sandboxes** | ❌ | ❌ | ✅ |
| **支持** | Community | Email | Deployed engineers + SLA |

### 16.2 用量计费

| 资源 | 单价 | 计费方式 |
|---|---|---|
| **Trace**（超出基础额度） | **$0.0025/extended trace** | 每 trace |
| **Deployment 运行（生产）** | **$0.0036 / 分钟** | 每 deployment 实时计费 |
| **Deployment 运行（开发）** | **$0.0007 / 分钟** | 每 deployment 实时计费 |
| **Fleet Run**（超出 500/月） | **$0.05 / Fleet run** | 每次 |
| **Engine（LangChain Compute Unit, LCU）** | **$1.50 / LCU** | 按使用 |
| **Sandbox vCPU** | **$0.0576 / vCPU-hr** | 每秒计费 |
| **Sandbox Memory** | **$0.0185 / GiB-hr** | 每秒计费 |
| **Sandbox Storage** | **$0.000123 / GiB-hr** | 每秒计费 |
| **Bulk Data Export** | Free | — |
| **LLM Token 用量** | 直接付给 provider（不在 LangSmith 账单） | — |

### 16.3 真实成本估算

#### 场景 A：小型初创（10 个开发者，10 万 traces/月）

| 项目 | 数量 | 单价 | 月成本 |
|---|---|---|---|
| Plus 订阅 | 10 座 × $39 | $39/座 | **$390** |
| 基础 trace | 10 万 traces - 1 万 = 9 万 | $0.0025 | **$225** |
| 1 个 Dev Deployment | 全月运行 14400 min | $0.0007/min | **$10** |
| 500 Fleet run | 0 超出 | $0.05 | **$0** |
| **小计** | | | **$625** |
| LLM token（OpenAI） | ~$0.01/trace × 10 万 | — | $1,000 |
| **总计** | | | **~$1,625/月** |

#### 场景 B：中型企业（100 座，1000 万 traces/月，5 个生产 deployment）

| 项目 | 数量 | 单价 | 月成本 |
|---|---|---|---|
| Plus 订阅 | 100 座 × $39 | $39/座 | **$3,900** |
| 基础 trace | 1000 万 - 1 万 ≈ 999 万 | $0.0025 | **$24,975** |
| 5 个生产 Deployment | 5 × 14400 min × 30 天 | $0.0036/min | **$7,776** |
| 100 万 Fleet run | 100 万 - 500 = 99.95 万 | $0.05 | **$49,975** |
| Engine LCU | 1000 LCU | $1.50 | **$1,500** |
| **小计** | | | **~$88,000** |
| LLM token | ~$0.01/trace × 1000 万 | — | $100,000 |
| **总计** | | | **~$188,000/月 ≈ $2.26M/年** |

> ⚠️ **关键发现**：LangSmith 的成本模型对**高 trace 量 + 多 deployment + 多 fleet** 的企业**非常不友好**。一个 1000 万 trace/月的中型企业，**LangSmith 平台费用可超过 $88,000/月**，**比 LLM token 本身贵**（$100,000）。这与 Langfuse（自托管免费）/ Helicone（已被收购，maintenance mode）形成显著差异。

#### 场景 C：超大型企业（1000 万 trace/月，自托管）

| 项目 | 成本 |
|---|---|
| Enterprise License | $100k-300k/年（custom） |
| K8s 集群（10 node × m5.4xlarge） | $15k/月 |
| ClickHouse 集群（10 node × 16vCPU/64GB） | $8k/月 |
| RDS PostgreSQL（db.r6g.4xlarge） | $3k/月 |
| ElastiCache Redis | $2k/月 |
| S3 存储 | $1k/月 |
| 运维人天（1 FTE） | $20k/月 |
| **小计** | **~$50-70k/月 ≈ $600k-840k/年** |

> 自托管仍需 Enterprise license + 实际 K8s/存储/运维成本，**总成本可能比 Cloud 模式便宜，也可能更贵**（取决于规模）。

### 16.4 与竞品价格对比

| 平台 | 1000 万 trace/月 估算成本 |
|---|---|
| **LangSmith** | $25k-90k/月（仅平台费） |
| **Langfuse Self-Hosted** | $0-3k/月（K8s + 存储） |
| **Arize Phoenix Self-Hosted** | $0-3k/月 |
| **Helicone** | $0-1k/月（已被收购，maintenance mode） |
| **Datadog LLM Observability** | $5k-30k/月（按 ingested span 计费） |
| **W&B Weave** | $1k-20k/月（按 seat + usage） |

> **LangSmith 是当前 LLM 观测/评估赛道中"最贵"的主流选择**。它的价值在"产品完整度 + 生态集成"，但对小团队 / 自托管偏好的客户，Langfuse / Arize Phoenix 是更经济的选择。

---

## 十七、生态集成：100+ Provider 与框架

### 17.1 Provider 列表

LangSmith 支持**几乎所有主流 LLM Provider**作为 trace 来源（SDK wrap）：

**商业模型**：
- OpenAI（GPT-4o, GPT-4.1, o1, o3）
- Anthropic（Claude 3.5 Sonnet, Claude 3.7 Sonnet, Claude 4）
- Google Gemini（Gemini 2.0, Gemini 2.5）
- AWS Bedrock（Anthropic / Mistral / Cohere / Meta）
- Azure OpenAI
- Mistral AI
- Cohere（Command R+）
- xAI（Grok）
- DeepSeek
- Reka
- Writer

**开源 / 自托管**：
- HuggingFace Inference Endpoints
- Ollama（本地）
- vLLM（自部署）
- LMStudio
- llama.cpp（通过 OpenAI 兼容端点）
- TGI（Text Generation Inference）
- SGLang
- Triton Inference Server
- Modal
- Replicate
- Together AI
- Fireworks AI
- Groq
- Anyscale Endpoints
- Lepton AI

### 17.2 Agent 框架

| 框架 | 集成方式 |
|---|---|
| LangChain | 1 env var |
| LangGraph | 1 env var |
| CrewAI | 1 env var |
| AutoGen | 1 env var |
| OpenAI Agents SDK | 1 env var |
| Pydantic AI | 1 env var |
| Vercel AI SDK | 1 env var |
| LlamaIndex | OTel adapter |
| Semantic Kernel | LangSmith SDK |
| Haystack | Haystack callback |
| DSPy | `dspy.configure` |
| Letta | Letta tracing |
| Atomic Agents | 集成 |
| Atomic-agents | 集成 |
| MemGPT | 集成 |
| Guidance | 集成 |
| Outlines | 集成 |
| Instructor | 集成 |
| Marvin | 集成 |
| TaskWeaver | 集成 |
| Fixpoint | 集成 |
| Browsergym | 集成 |

### 17.3 与第三方 LLM Gateway 的关系

LangSmith 与主流 AI Gateway 产品的关系是**"互不冲突、可以共存"**：

```
业务代码 → Portkey (统一端点 / 路由 / 缓存) → OpenAI/Anthropic
     │
     └─ trace 旁路 → LangSmith SDK → LangSmith
```

实际集成示例：

```python
# 用 Portkey 做统一端点 + 路由
from portkey_ai import Portkey
portkey = Portkey(api_key="...", config="...")

# wrap_portkey 后，Portkey 的每次调用都进 LangSmith
from langsmith.wrappers import wrap_portkey
client = wrap_portkey(portkey)

# 所有调用自动 trace 到 LangSmith
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
```

类似地：
- `wrap_litellm(litellm_completion)`
- `wrap_ai21(ai21_client)`
- ... 共 30+ 包装器

### 17.4 集成生态总览图

```
┌────────────────────────────────────────────────────────────────────┐
│                     你的 AI Application                            │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐         ┌────────────┐
   │  LangChain│         │  Portkey  │         │  LangSmith  │
   │  /LangGr.│         │  (统一端点)│         │   (观测)   │
   │  /CrewAI │         │           │         │             │
   └────┬────┘         └─────┬────┘         └──────┬──────┘
        │                    │                     │
        └────────┬───────────┘                     │
                 │                                  │
                 ▼                                  ▼
         ┌────────────────┐                ┌──────────────────┐
         │  LLM Provider  │                │  LangSmith       │
         │  OpenAI /      │                │  ClickHouse/PG/  │
         │  Anthropic /   │                │  Redis/S3        │
         │  Bedrock /     │                │                  │
         │  vLLM / ...    │                │                  │
         └────────────────┘                └──────────────────┘
```

---

## 十八、客户案例与典型用户

### 18.1 公开客户列表（来自 LangChain 官网）

| 客户 | 行业 | 规模 | 使用场景 |
|---|---|---|---|
| **Klarna** | Fintech | 5000+ 员工 | AI 客服、欺诈检测（多个 LangGraph Agent） |
| **Replit** | Dev Tools | 500+ 员工 | Replit Agent 的 trace 观测 |
| **JetBlue** | 航空 | 20000+ 员工 | 客户服务 Copilot |
| **Ally** | 银行 | 10000+ 员工 | 内部 AI 助手 |
| **Uber** | 出行 | 30000+ 员工 | 多个内部 LangGraph 应用 |
| **Rippling** | HR SaaS | 3000+ 员工 | HR 流程自动化 |
| **Vellum** | LLM 工具 | 100+ 员工 | Prompt 管理 + 评估 |
| **Cognition (Devin)** | Coding Agent | 200+ 员工 | Devin 的 trace 与 eval |
| **Vanguard** | 金融 | 30000+ 员工 | 投资顾问 AI |
| **Snowflake** | 数据云 | 8000+ 员工 | Cortex Agents |
| **Pepsico** | 消费品 | 300000+ 员工 | 内部 AI 平台 |
| **Morningstar** | 金融数据 | 10000+ 员工 | 投研 AI |
| **Moody's** | 金融数据 | 14000+ 员工 | 信用分析 AI |
| **Docusign** | 合同管理 | 5000+ 员工 | 合同审阅 AI |
| **Rakuten** | 电商 | 30000+ 员工 | 客服 + 推荐 |
| **Franklin Templeton** | 资管 | 10000+ 员工 | 投研 AI |

### 18.2 典型使用场景

#### 场景 1：客服 Copilot（JetBlue / Klarna）

- **业务**：10 万次 / 月客服对话
- **技术栈**：LangGraph Agent（多轮 + 工具调用 + RAG）
- **LangSmith 价值**：
  - Trace 100% 采集
  - Online Eval（满意度、解决率）
  - Thread 视图（看完整多轮对话）
  - Annotation Queue（人工 review 5% 抽样）
  - 故障时 Engine 自动聚类 + 报警

#### 场景 2：Coding Agent（Cognition Devin）

- **业务**：长任务 Coding Agent
- **技术栈**：LangGraph 状态机 + 100+ 步工具调用
- **LangSmith 价值**：
  - **Sandboxes** 跑生成代码（1000s 并发）
  - **Deployment** 自动扩缩（KEDA）
  - Trace 含完整工具调用链
  - **Engine** 自动检测 "tool 失败模式" 聚类

#### 场景 3：RAG 应用（Vellum / VANGUARD）

- **业务**：内部知识库问答
- **技术栈**：LangChain + LangGraph + 向量库
- **LangSmith 价值**：
  - Trace 包含 retriever 步骤
  - Dataset + Offline Eval（10 万 question/answer 对）
  - **Prompt Hub** 版本管理
  - Online Eval（faithfulness, relevance, hallucination）

#### 场景 4：金融分析 AI（Moody's / Franklin Templeton）

- **业务**：自动分析财报 + 出报告
- **技术栈**：LangGraph 多 Agent + MCP tool
- **LangSmith 价值**：
  - **Self-Hosted** 满足合规（数据不出 VPC）
  - **Hybrid** 模式（控制面 SaaS，数据面自托管）
  - SOC 2 / HIPAA 合规
  - **Custom SSO** 集成企业内部 IdP

### 18.3 已知失败 / 迁移案例

- **Klarna**：2024 年公开过在 LangSmith 上跑 AI 客服的场景，但 2025 年也公开砍过一些 AI 项目（不影响 LangSmith 使用）
- **Replit Agent**：仍在用 LangSmith，但 Replit 内部有自研观测栈
- **多家被报道**用 LangSmith 做 PoC 后，因价格 / 锁定原因迁回自建栈

> **关键观察**：LangSmith 在**早期 PoC**阶段优势巨大（与 LangChain 集成最丝滑），但**大规模生产**阶段会因价格 / 锁定而面临客户流失。

---

## 十九、优劣势分析

### 19.1 优势

| # | 优势 | 详细 |
|---|---|---|
| 1 | **与 LangChain / LangGraph 生态最深度的集成** | 1 个 env var 启用 trace；@traceable 装饰器；LangGraph Platform 控制面 + 数据面；Agent Protocol 标准提出方之一 |
| 2 | **产品完整度** | Observability + Evaluation + Prompt Hub + Deployment + Fleet + Engine + Sandboxes + Insights + Chat——9 大能力一站式 |
| 3 | **Deployment 平台** | 唯一提供"Agent 一键部署 + KEDA 自动扩缩 + 30+ API + Cron + Auth"的 LLM 平台 |
| 4 | **Evaluation 能力** | Online + Offline + Human 三合一；Experiment Comparison UI；LLM-as-judge 模板 |
| 5 | **OTel 兼容** | 支持 OpenTelemetry trace 端点（2024+），可与 Datadog / Honeycomb / Jaeger 共存 |
| 6 | **企业级部署** | Self-Hosted + Hybrid + Cloud 三模式；SOC 2 / HIPAA / GDPR 合规；多区域 |
| 7 | **自动故障诊断 (Engine)** | LLM-driven 的 trace 故障聚类 + 根因 + 修复建议——竞品无此能力 |
| 8 | **代码沙箱 (Sandboxes)** | 唯一一个把"Agent 代码沙箱"也集成到同一平台的产品 |
| 9 | **活跃维护** | 持续每月发版（vs Helicone maintenance mode） |
| 10 | **多语言 SDK** | Python / TypeScript / Java / Kotlin / Go（OTel） |

### 19.2 劣势

| # | 劣势 | 详细 |
|---|---|---|
| 1 | **不是 AI Gateway** | 没有统一 OpenAI 端点、没有路由、没有 fallback、没有缓存、没有 per-tenant 限流 |
| 2 | **价格贵** | $0.0025/trace + $0.0036/min deployment + $1.50/LCU + Sandbox vCPU·h——对中高 trace 量客户，**比 LLM token 本身还贵** |
| 3 | **平台闭源** | 后端 / UI 完全闭源；只 SDK 开源；客户无法 fork 平台 |
| 4 | **锁定风险** | 数据模型（Project / Run / Feedback / Thread）是 LangSmith 私有的；迁出需重建数据 |
| 5 | **复杂部署** | Self-Hosted 需要 K8s + ClickHouse + Postgres + Redis + S3 + KEDA——小团队难运维 |
| 6 | **数据保留限制** | SaaS 默认 400 天，Dev plan 仅 14 天 |
| 7 | **单 trace 25,000 run 上限** | 长任务 Coding Agent 可能触及；超过被拒 |
| 8 | **Bulk Export 需 UI 操作** | API 导出有限制 |
| 9 | **Fleet 模糊定位** | "无代码 Agent"可能与工程团队冲突 |
| 10 | **Sandboxes 仅 Enterprise** | 中小客户用不到，需要自己用 E2B / Modal 替代 |
| 11 | **LangChain 中心化** | 工具链紧密耦合 LangChain；对非 LangChain 项目的"边际价值"降低 |
| 12 | **公开性能 benchmark 缺失** | 没有官方 latency / throughput / cost 数字，采购决策要靠 POC |

### 19.3 与"中立第三方 OTel 后端"对比的取舍

| 维度 | LangSmith | 通用 OTel 后端 (Datadog / Honeycomb / Grafana) |
|---|---|---|
| LLM 特定语义 | ✅ 丰富（Run type / feedback / eval） | ⚠️ 需自己建 dashboard |
| Eval 能力 | ✅ 内置 | ❌ 需自己实现 |
| Agent 部署 | ✅ 一体化 | ❌ 不涉及 |
| 多语言统一 | ⚠️ 偏 Python/TS | ✅ OTel 通用 |
| 成本可预测 | ⚠️ 按 trace 难预测 | ✅ 按 span 透明 |
| 退出成本 | ⚠️ 私有数据模型 | ✅ 标准 OTel 格式 |

---

## 二十、与其他 AI Gateway / 观测平台对比

### 20.1 横向对比表

| 维度 | **LangSmith** | **Langfuse** | **Arize Phoenix** | **Helicone** | **Portkey** | **Datadog LLM Obs.** |
|---|---|---|---|---|---|---|
| **License** | ❌ 闭源（SDK 开源） | ✅ MIT / 自托管 | ✅ Apache 2.0 | ✅ Apache 2.0 | ❌ 闭源 | ❌ 闭源 |
| **定位** | Agent 全生命周期平台 | 开源 LLM 观测 + Eval | 开源 LLM 观测 + Eval | 轻量观测 + 缓存 | AI Gateway + 观测 | APM 厂商的 LLM 附加 |
| **AI Gateway** | ❌ | ❌ | ❌ | ⚠️ 简单 | ✅ 核心 | ❌ |
| **Trace 模型** | RunTree | Span | Span (OpenInference) | Request / Response | Trace / Span | Span (OTel) |
| **OTel 兼容** | ✅ 端点 | ✅ 通过 OTel collector | ✅ 原生 | ❌ | ✅ 透传 | ✅ 原生 |
| **Eval 能力** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Deployment 平台** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **代码沙箱** | ✅ Sandboxes | ❌ | ❌ | ❌ | ❌ | ❌ |
| **故障聚类** | ✅ Engine | ⚠️ 简单 | ⚠️ 简单 | ❌ | ❌ | ✅ APM-grade |
| **Self-Hosted** | ✅（Enterprise） | ✅（推荐） | ✅（推荐） | ✅ | ⚠️（独立版） | ❌ |
| **价格** | $39/seat + usage | 免费（自托管）/ $0.10/1k events | 免费（自托管） | $0/Pro | $0/$20/$499+ | $0.05/1M spans |
| **客户数** | 数百（Enterprise） | 数千 | 数千 | 16k（已收购） | 数千 | 数十万（Datadog 整体） |
| **LangChain 集成** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **生产稳定性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 20.2 典型采购决策树

```
                        ┌────────────────────────────┐
                        │ 你的 LLM 应用类型？         │
                        └────────┬───────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
   ┌─────────┐             ┌─────────┐              ┌──────────┐
   │ LangCh. │             │ 多 Provider│            │  Coding  │
   │ /LangGr.│             │ + 路由    │            │  Agent   │
   │ 中心化  │             │ 优先      │            │ (长任务) │
   └────┬────┘             └────┬────┘              └─────┬────┘
        │                       │                         │
        ▼                       ▼                         ▼
   ┌──────────┐           ┌──────────┐              ┌──────────┐
   │ LangSmith│           │ Portkey  │              │ LangSmith│
   │ (一站式) │           │ / LiteLLM│              │ Deployment│
   │          │           │ (网关)   │              │ + Sandbox│
   └────┬─────┘           └────┬─────┘              └────┬─────┘
        │                      │                         │
        │ 评估/观测          │ 评估/观测                 │
        ▼                      ▼                         ▼
   ┌──────────────────────────────────────────────────────────┐
   │  评估/观测需求？                                          │
   │  - 自托管省钱 → Langfuse / Arize Phoenix                  │
   │  - 企业级 + 一站式 → LangSmith                            │
   │  - APM 集成 → Datadog / New Relic                         │
   └──────────────────────────────────────────────────────────┘
```

### 20.3 LangSmith vs Langfuse：开源 vs 闭源的关键权衡

| 维度 | LangSmith | Langfuse |
|---|---|---|
| **价格 1000 万 trace/月** | ~$25k-90k | ~$1k-3k（自托管）/ $1k-10k（SaaS） |
| **数据自托管** | ⚠️ Self-Hosted 复杂 | ✅ 一键 Docker / K8s |
| **SDK 易用性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Eval 能力** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **部署平台** | ✅ | ❌ |
| **生态锁定** | ⚠️ 中 | ✅ 低（自托管） |
| **持续维护** | ✅ 主导 | ✅ 主导 |
| **Vendor Lock-in** | ⚠️ 高 | ✅ 低（MIT + 标准 OTel） |
| **适合** | LangChain 中心 / 大企业 | 自托管偏好 / 中小企业 |

### 20.4 LangSmith vs Portkey：观测 vs 网关

**这两者其实不冲突**——LangSmith 偏观测 + 评估 + 部署，Portkey 偏 AI Gateway。但**当你只需要其中之一**时：

| 需求 | 选 LangSmith | 选 Portkey |
|---|---|---|
| 统一 OpenAI 端点 | ❌ | ✅ |
| 多 Provider 路由 | ❌ | ✅ |
| Fallback / Retry | ❌ | ✅ |
| 限流 / 配额 | ❌ | ✅ |
| 缓存 | ❌ | ✅ |
| Trace / 观测 | ✅ 核心 | ✅ 基础 |
| Eval 能力 | ✅ 核心 | ⚠️ 基础 |
| Agent 部署 | ✅ | ❌ |
| 故障自动诊断 | ✅ Engine | ❌ |
| Prompt 版本管理 | ✅ Hub | ⚠️ 基础 |
| 价格 1000 万 trace/月 | $25k+ | $499/月（Pro 计划） |
| **组合方案** | **LangSmith 观测 + Portkey 网关** | |

---

## 二十一、最佳实践与反模式

### 21.1 最佳实践

#### 1. 始终开启 Sampling 控制成本

```bash
# 生产环境：只采集 10% 的 trace
export LANGSMITH_TRACING_SAMPLING_RATE=0.1

# 但所有 100% 的 trace + feedback 仍记录（通过 Rules）
```

#### 2. 用 Metadata 而非 stringly-typed tag 区分环境

```python
@traceable(
    metadata={
        "env": "prod",
        "version": "1.2.3",
        "user_segment": "premium"
    },
    tags=["chat", "rag"]
)
def my_chain(...): ...
```

#### 3. 用 Thread 追踪多轮对话

```python
@traceable
def chat_turn(user_input: str, thread_id: str):
    return response

# 业务代码确保同一会话的 thread_id 一致
chat_turn("Hello", thread_id="user_42")
chat_turn("Follow up", thread_id="user_42")
```

#### 4. 用 Dataset + Offline Eval 做 PR 验收

```yaml
# .github/workflows/eval.yml
- name: Run offline eval
  run: |
    python eval.py --dataset qa_v1 --target gpt-4o-baseline
- name: Compare to baseline
  run: |
    python compare_experiments.py --baseline gpt-4o-baseline --current pr-${{ github.event.number }}
```

#### 5. 用 Online Eval + Rules 触发报警

```yaml
# UI: Project → Rules
# 触发条件: feedback.correctness < 0.5
# 动作: webhook to PagerDuty / Slack
```

#### 6. 锁定 Prompt Hub commit hash

```python
# 永远不要用 latest
prompt = hub.pull("customer-support@v1.2.3")
# 而非
prompt = hub.pull("customer-support")  # ⚠️ 可能漂移
```

#### 7. 把 Engine 当 AI SRE 用

- 让 Engine 自动聚类失败 trace
- 让 Engine 生成的 Eval 防止回归
- 让 Engine 推荐的 prompt 改动走 A/B test

#### 8. Self-Hosted 用外部托管存储

```yaml
# 不要用 LangSmith bundled ClickHouse / Postgres / Redis
# 用 AWS RDS / ClickHouse Cloud / ElastiCache
postgres:
  external: true
clickhouse:
  external: true
redis:
  external: true
```

#### 9. Hybrid 模式是合规场景的最佳选择

- 数据面在用户 VPC（合规）
- 控制面在 LangChain SaaS（免运维 UI/API）
- 适合金融、医疗、政府客户

#### 10. 不要用 Fleet 取代工程团队

- Fleet 适合"快速 PoC"
- 生产 Agent 应由工程团队用 LangGraph 写代码

### 21.2 反模式

#### ❌ 反模式 1：把 LangSmith 当 AI Gateway

```python
# 错误：以为 LangSmith 端点 = OpenAI 兼容端点
import openai
client = openai.OpenAI(
    base_url="https://api.smith.langchain.com",  # ❌ 不是 chat completions
    api_key=...
)
# 报错：404
```

#### ❌ 反模式 2：不设采样

```python
# 错误：生产环境 100% 采集
@traceable
def chat(...): ...  # 每天 1 亿次调用
# 月成本爆炸
```

#### ❌ 反模式 3：把所有数据塞进 trace

```python
# 错误：把整本电子书塞进 inputs
@traceable
def rag(question: str):
    context = read_entire_book()  # 5MB
    return llm_call(question, context)
# 触发 1MB/run 限制
```

#### ❌ 反模式 4：自托管但用 bundled 存储

```yaml
# 错误：Helm 安装时用 LangSmith bundled 的 ClickHouse
# 生产环境会很惨
```

#### ❌ 反模式 5：不锁 Prompt 版本

```python
prompt = hub.pull("my-prompt")  # 今天拉的是 v1，明天可能变 v2
```

#### ❌ 反模式 6：用 Engine 但不审阅

```python
# 错误：让 Engine 自动应用 prompt 修复
# 正确：审阅 Engine 建议 + A/B test
```

#### ❌ 反模式 7：忽略 Engine LCU 成本

```python
# Engine 在后台跑，LCU 用量可能爆
# 正确：设置 Engine 配额 + 监控
```

#### ❌ 反模式 8：Fleet run 计费忽视

```python
# 500 Fleet run / 月 included
# 超过 = $0.05/次
# 业务方刷一晚上 → 月底 $50,000 账单
```

#### ❌ 反模式 9：把 LangSmith 端点当 OpenAI 兼容

```python
# 错误
client = openai.OpenAI(base_url="https://api.smith.langchain.com/v1")
# 正确：用 LangSmith SDK 的 wrap_openai，把 trace 发到 LangSmith
```

#### ❌ 反模式 10：自托管 LangSmith 但不准备 K8s 专家

```python
# 错误：让一个 Python 开发去运维 K8s + ClickHouse + LangSmith
# 正确：要么用 Cloud，要么请 DevOps 团队
```

---

## 二十二、未来展望（2026-2028）

### 22.1 LangChain 战略主线

LangChain 公司在 2025-2026 年明确了**三大产品线战略**：

```
┌──────────────────────────────────────────────────────┐
│  1. LangChain Open Source                            │
│     - langchain / langgraph 开源框架                  │
│     - 维护者 + 社区贡献                               │
├──────────────────────────────────────────────────────┤
│  2. LangSmith Platform                              │
│     - 商业化核心                                     │
│     - Observability + Eval + Deployment + Engine    │
│     - 目标：成为"Agent 时代的 Datadog"                │
├──────────────────────────────────────────────────────┤
│  3. LangChain Open Source + Enterprise               │
│     - 自托管 LangChain 框架 + LangSmith              │
│     - 目标：大企业 / 政府 / 金融                      │
└──────────────────────────────────────────────────────┘
```

### 22.2 2026-2028 路线图（基于公开信号推测）

| 时间 | 预期发布 | 影响 |
|---|---|---|
| 2026 H2 | **LangSmith Studio 2.0**（visual agent builder） | 与 Fleet 形成"代码 + 无代码"双轨 |
| 2026 H2 | **LangSmith Trace v2**（OTel 原生作为一等公民） | 降低非 LangChain 用户的接入门槛 |
| 2026 Q4 | **LangSmith Engine GA** | 自动故障诊断 + 修复闭环成为核心 |
| 2027 H1 | **LangSmith Marketplace**（prompt / agent / tool 公开市场） | 类似 HuggingFace 的商业化 |
| 2027 H1 | **LangSmith Multi-Modal**（视频 / 音频 trace 原生支持） | 应对 Gemini 3 / GPT-5 多模态趋势 |
| 2027 H2 | **LangSmith Fine-Tune**（在 LangSmith 内做 LoRA / DPO） | 完整覆盖 LLM 生命周期 |
| 2028 H1 | **LangSmith Edge**（在 Cloudflare / Vercel Edge 跑 Agent） | 应对边缘 AI 趋势 |
| 2028 H2 | **Agent Marketplace**（标准化 agent 交易） | 长尾场景商业化 |

### 22.3 关键趋势与挑战

| 趋势 | 对 LangSmith 的影响 |
|---|---|
| **Agent 成为 LLM 应用主流形态** | ✅ 利好（Deployment / Engine / Sandboxes） |
| **OpenTelemetry 成为 LLM 观测标准** | ⚠️ 挑战（需继续投入 OTel 兼容） |
| **开源观测工具持续成熟 (Langfuse / Phoenix)** | ⚠️ 挑战（价格压力） |
| **企业 AI 合规要求提升** | ✅ 利好（Self-Hosted / Hybrid / SOC 2） |
| **LLM 成本下降 + 应用规模扩大** | ✅ 利好（trace 量增加 → 收入增加） |
| **多 Agent / Agent 协作成为主流** | ✅ 利好（LangGraph 集成） |
| **本地 LLM 普及** | ✅ 利好（支持 Ollama / vLLM / llama.cpp） |
| **Coding Agent 爆发** | ✅ 利好（Sandboxes / Deployment） |
| **价格战 / 客户流失** | ⚠️ 风险（需持续降本） |

### 22.4 LangSmith 的"终极形态"预测

如果按"端到端 Agent 平台"演进，LangSmith 在 2028 年可能成为：

```
┌──────────────────────────────────────────────────────┐
│              LangSmith (2030 Vision)                 │
├──────────────────────────────────────────────────────┤
│  Build   → Studio + Fleet (无/低代码 Agent 构建)     │
│  Deploy  → Deployment (K8s + KEDA + 多区域)          │
│  Run     → Sandboxes (代码沙箱) + 状态机 (LangGraph)  │
│  Trace   → Observability (RunTree + OTel)            │
│  Eval    → Online + Offline + Human + Engine         │
│  Iterate → Prompt Hub + Dataset + A/B                │
│  Operate → Engine (自动 SRE) + Insights + Chat        │
│  Govern  → RBAC + Audit + SOC 2 + HIPAA + GDPR        │
│  Sell    → Marketplace (Agent / Prompt / Tool)        │
└──────────────────────────────────────────────────────┘
```

**核心风险**：

1. **被开源观测工具蚕食**（Langfuse / Phoenix / OpenLLMetry）
2. **被通用 APM 厂商挤压**（Datadog / New Relic / Grafana 都在做 LLM 观测）
3. **被 OpenAI / Anthropic 自家的 Agent 平台**取代（OpenAI Agents SDK 已经有 trace）
4. **被 LangChain 开源框架的"去 LangSmith 化"运动**削弱（社区有人推动用 OTel 通用后端）

### 22.5 LangChain 公司的长期赌注

LangChain 2025-2026 年的核心战略是**"让 LangSmith 成为 Agent 时代的 Datadog"**：

- **Datadog** 之于 DevOps = LangSmith 之于 Agent
- **核心壁垒**：与 LangChain 生态最深度的集成 + 9 大子产品矩阵
- **核心风险**：如果 LangChain 框架失势，LangSmith 也会失势

---

## 二十三、参考资料与调研备注

### 23.1 一手资料（2026-06-05 抓取）

| 资料 | URL |
|---|---|
| LangSmith 文档首页 | https://docs.langchain.com/langsmith/home |
| LangSmith Pricing | https://www.langchain.com/pricing |
| Platform Setup | https://docs.langchain.com/langsmith/platform-setup |
| Self-Hosted | https://docs.langchain.com/langsmith/self-hosted |
| Observability Concepts | https://docs.langchain.com/langsmith/observability-concepts |
| Observability Quickstart | https://docs.langchain.com/langsmith/observability-quickstart |
| Deploy Self-Hosted Full Platform | https://docs.langchain.com/langsmith/deploy-self-hosted-full-platform |
| Kubernetes 安装 | https://docs.langchain.com/langsmith/kubernetes |
| LangChain Trust Center | https://trust.langchain.com/ |
| LangChain GitHub | https://github.com/langchain-ai |
| LangSmith Helm Chart | https://github.com/langchain-ai/helm |
| LangSmith SDK | https://github.com/langchain-ai/langsmith-sdk |

### 23.2 既往 00-20 系列报告中的相关章节

| 报告 | 相关章节 |
|---|---|
| 01-llm-protocols.md | LangSmith 的 OTel 端点 / RunTree 协议 |
| 04-observability-openllmetry.md | LangSmith vs OpenLLMetry 对比 |
| 05-agent-multi-step.md | LangSmith Deployment / LangGraph Platform |
| 08-inference-engine-coordination.md | LangSmith + LangGraph 状态机 |
| 09-multimodal-gateway.md | 多模态 trace 支持现状 |
| 10-open-source-ecosystem.md | LangSmith 在 LLM 生态中的位置 |
| 11-mcp-deep-dive.md | LangSmith Fleet 的远程 MCP 集成 |
| 12-a2a-protocol.md | LangSmith Engine 与 Agent 协作 |
| 13-cost-economics.md | LangSmith 定价详细分析 |
| 14-performance-benchmark.md | LangSmith trace ingest 速率 |
| 16-public-cloud-integration.md | LangSmith Cloud 区域（US / EU / APAC / AWS US） |
| 19-sla-service-governance.md | LangSmith SLA / SOC 2 / HIPAA / GDPR |
| 20-future-2027-2030.md | LangSmith 2030 愿景 |

### 23.3 调研备注

1. **本报告完成时间**：2026-06-05（基于截至该日期的公开信息）
2. **本报告覆盖版本**：LangSmith Platform v0.12+（Helm chart 当前 latest tag）
3. **性能数据来源**：官方文档 + 公开博客 + 客户案例 + 工程师公开演讲汇总估算，**非官方 benchmark**
4. **价格数据来源**：https://www.langchain.com/pricing（2026-06-05 抓取）
5. **未深入讨论的话题**：
   - LangSmith 的 **EU / APAC 数据驻留**详细配置（合规相关，建议联系销售）
   - LangSmith 与 **Snowflake Cortex** / **Databricks Mosaic AI** 的具体集成
   - LangSmith **Fine-Tune** 能力（尚未发布）
   - LangSmith **Marketplace**（尚未发布）
6. **后续 deep dive 候选**：
   - **Unify**（按质量 + 价格智能路由的代表）
   - **Not Diamond**（AI-driven 路由的代表）
   - **TrueFoundry**（企业级 LLM 平台）
   - **Langfuse**（LangSmith 最大开源竞品）
   - **Arize Phoenix**（开源 + OpenInference 标准的提出方）

### 23.4 一句话总结

> **LangSmith 是 LangChain 商业公司推出的"Agent 全生命周期平台"（Observability + Evaluation + Prompt Hub + Deployment + Fleet + Engine + Sandboxes + Insights + Chat），与 LangChain / LangGraph 生态有最深度的集成（1 个 env var 启用 trace），但它**不是 AI Gateway**（没有统一 OpenAI 端点、没有路由、没有 fallback、没有缓存），价格按 trace + 部署运行时间 + LCU + Sandbox 用量计费，对中高 trace 量客户**比 LLM token 本身还贵**，适合 LangChain 中心化的大型企业 / 金融 / 医疗 / 政府客户，2025-2026 年正向"Agent 时代的 Datadog"演进。**

---

_本报告基于截至 2026-06-05 的公开资料整理，不构成商业建议。采购决策前请直接联系 LangChain 销售团队获取最新报价与 POC 数据。_
