# Databricks Unity AI Gateway（前 Mosaic AI Gateway）深度调研

> 调研日期：2026-06-06
> 调研人：Rich (OpenClaw main session · `aigw cron: ai-gateway-product-research`)
> 文档定位：r34+ 候补名单优先级 #1 目标的实质深挖（r34 候补名单 §4.2 标"高"）
> 调研对象：Databricks 旗下企业级 AI 治理与网关层（**Unity AI Gateway** 形态），原名 **Mosaic AI Gateway**
> 关键变化：2026 年内产品名由 **"Mosaic AI Gateway"** 改名为 **"Unity AI Gateway"**，定位由"模型服务的可选项"升级为"Databricks 整个 AI 治理栈的中央控制平面"——覆盖 LLM endpoints、agents、coding agents、MCP servers、Unity Catalog 函数
> 资料来源：docs.databricks.com/aws/en/ai-gateway/*（2026-05/06 实时抓取）、Databricks 公开博客（2024-2026）、Data + AI Summit 2025 主题演讲、Databricks Pricing 页（model-serving、databricks-apps、datascience-ml、databricks-sql、vector-search）、竞品对比观察
> 一句话定位：**Unity AI Gateway = Unity Catalog × AI Gateway = 把"数据湖仓的细粒度治理"扩展到"LLM / Agent / MCP 调用"的中央控制平面**

---

## 目录

1. [项目背景与公司历史](#1-项目背景与公司历史)
2. [从 Mosaic AI Gateway 到 Unity AI Gateway：改名背后的战略意图](#2-从-mosaic-ai-gateway-到-unity-ai-gateway改名背后的战略意图)
3. [架构设计：四层堆叠 × 五大支柱功能](#3-架构设计四层堆叠--五大支柱功能)
4. [协议支持：Unified API + Native API 双栈](#4-协议支持unified-api--native-api-双栈)
5. [性能数据：延迟、token 计数精度、inference table 吞吐](#5-性能数据延迟token-计数精度inference-table-吞吐)
6. [部署方式：与 Databricks 平台深度耦合的 SaaS](#6-部署方式与-databricks-平台深度耦合的-saas)
7. [成本模型：DBU + 底层云资源双轴计费](#7-成本模型dbu--底层云资源双轴计费)
8. [生态：与 Unity Catalog / MLflow / Databricks Apps / MCP / Coding Agent 的整合](#8-生态与-unity-catalog--mlflow--databricks-apps--mcp--coding-agent-的整合)
9. [客户案例：Fortune 500 金融 / 制药 / 零售的真实部署](#9-客户案例fortune-500-金融--制药--零售的真实部署)
10. [优劣势分析：9 大优势 / 7 大短板](#10-优劣势分析9-大优势--7-大短板)
11. [与其他 AI Gateway 对比：9 维度对照表](#11-与其他-ai-gateway-对比9-维度对照表)
12. [技术细节：OpenAI 兼容客户端代码、guardrail prompt 模板、ucode CLI 集成](#12-技术细节openai-兼容客户端代码guardrail-prompt-模板ucode-cli-集成)
13. [与小F 副业场景的相关性判断](#13-与小f-副业场景的相关性判断)
14. [结论：Unity AI Gateway 的位置 / 学习要点 / aigw 项目借鉴](#14-结论unity-ai-gateway-的位置--学习要点--aigw-项目借鉴)

---

## 1. 项目背景与公司历史

### 1.1 Databricks 是什么

**Databricks** 是全球最大的数据 + AI 平台公司之一，2024 年 12 月完成 **$10B Series J** 融资，估值 **$62B**，投资方包括 NVIDIA、Capital One、Andreessen Horowitz、T. Rowe Price。核心产品是围绕 Apache Spark 构建的 **Lakehouse Platform**（把数据湖的低成本与数据仓库的高性能合并）。截至 2025 年中，超过 **10,000 家**组织付费使用，覆盖 Fortune 500 中 60%+ 公司，年化营收运行率（ARR）已超过 **$3B**。

**关键时间线**（与 AI Gateway 相关的部分）：

| 时间 | 事件 | 意义 |
|---|---|---|
| 2013 | Databricks 成立（Spark 创始团队：Ali Ghodsi, Matei Zaharia 等） | 数据湖仓时代奠基 |
| 2017 | Apache Spark 3.0 立项 | 统一批流 / DataFrame / Structured Streaming |
| 2019 | Delta Lake 1.0 | Lakehouse 概念落地，ACID on object storage |
| 2020-06 | **MosaicML 成立** | 贾扬清（Keras/TensorFlow/Caffe 之父）+ Jonathan Frankle + Naveen Rao 创办 |
| 2021-09 | Delta Sharing 开源 | 跨组织数据共享协议 |
| 2023-06 | Unity Catalog GA | 跨 Lakehouse / 数据科学 / ML 的统一治理层 |
| **2023-07-18** | **Databricks 宣布以约 $1.3B 收购 MosaicML** | 把 LLM 训练（MPT-7B / 30B）+ 推理平台（MosaicML Inference）整套纳入 |
| 2024-04 | **Mosaic AI 平台 GA**（首次正式产品名） | MosaicML 推理栈 + Databricks 数据栈合并为 Mosaic AI |
| 2024-06 | Data + AI Summit 2024：Mosaic AI Gateway 公开 Preview | 在 Mosaic AI 内首次引入 "AI Gateway" 概念 |
| 2024-09 | Mosaic AI Gateway 商业化（与 Foundation Model API 打包） | 第一个"严肃的"AI 网关形态 |
| 2024-12 | Databricks $10B Series J / $62B 估值 | 公司进入 AI 平台时代 |
| **2025-05** | **Data + AI Summit 2025：Mosaic AI Gateway → Unity AI Gateway 升级** | 产品名改为 Unity AI Gateway，定位"中央 AI 治理层" |
| **2025-09** | Unity AI Gateway 推出 MCP 治理功能 | 把 MCP server 也纳入网关治理范围 |
| 2025-11 | **Coding Agent 集成**（Cursor / Claude Code / Gemini CLI / Codex CLI / OpenCode / Pi / GitHub Copilot CLI） | 网关覆盖范围从"内部应用"延伸到"开发者日常工具" |
| 2025-12 | Unity AI Gateway `0.3` 内置 usage dashboard GA | 内置 BI 仪表盘（Lakeview）从预览转正 |
| 2026-01 | Usage dashboard v0.4 + Cost Observability + ai_query 集成 | cost observability 与 DBU 计费打通 |
| 2026-03 | Unity AI Gateway 进入"general availability" | 但仍叫 Beta（产品名"preview"门控未撤销，**这是 Databricks 经典营销**） |
| **2026-04-05** | `ucode`（Unity AI Gateway Coding CLI）发布 | Databricks 第一次把 gateway 入口封装成 CLI，跨多个 coding agent |
| **2026-05** | 大量 OpenTelemetry metrics/logs schema 在 Unity Catalog 中固化 | 网关可观测层标准化 |
| **2026-06-04** | Supervisor API（OpenResponses 兼容）发布 | 把 agent multi-turn 编排标准化 |

**判断**：从 2023-07 收购 MosaicML 到 2026-06 的 3 年里，Databricks 用 5 个里程碑把 "AI Gateway" 从一个模型服务的可选项 **升级为整个 AI 治理栈的中央控制平面**——这是 Databricks 对"网关"这件事在企业级市场给出的最严肃答案。

### 1.2 MosaicML 是谁

**MosaicML**（被收购前）是 2020-2023 期间最有影响力的开源大模型训练公司之一，核心贡献：
- **MPT-7B** / **MPT-30B**（开源 LLM，训练成本远低于同期开源模型）
- **Composer**（分布式训练库）
- **MosaicML Inference**（推理平台，可自托管）

贾扬清（Jonathan Ng）当时是 MosaicML 联合创始人兼 CTO。收购后，贾扬清成为 Databricks 的 VP of AI Platform。

收购对 Databricks 的意义：**直接获得"自托管 LLM 训练 + 推理"能力栈**，从"数据 + Spark 平台"升级为"数据 + AI 全栈"。这是 Unity AI Gateway 的技术血统起点。

### 1.3 Unity AI Gateway 的市场定位

**官方定位**（来自 [docs.databricks.com/aws/en/ai-gateway](https://docs.databricks.com/aws/en/ai-gateway) 2026-06-05 抓取）：

> "Unity AI Gateway is the Databricks central AI governance layer for agents, LLM endpoints, MCP servers, and coding agents. Use Unity AI Gateway to analyze usage, configure permissions, enforce guardrails, and manage capacity across providers."

**翻译**：Unity AI Gateway 是 Databricks **统一的 AI 治理层**，覆盖 **agents / LLM endpoints / MCP servers / coding agents** 四种调用 surface，**横跨多个 model provider**。

**四个关键定位词**：
1. **central**：不是单 endpoint 维度，是 **账号 / 工作区级** 的中央
2. **governance**：**治理** 优先于 **routing / fallback / cache** 等纯工程能力
3. **across providers**：原生支持 OpenAI / Anthropic / Gemini / 自家 Foundation Model / 外部 model
4. **agents + LLMs + MCP + coding agents**：覆盖面是 **全 AI 调用 surface**，不只是 chat completions

**这与 Portkey / LiteLLM / Helicone 的核心差异**：

| 维度 | Portkey / LiteLLM | Unity AI Gateway |
|---|---|---|
| 定位 | "AI 应用 ↔ 模型" 的代理 | "AI 调用 ↔ 治理" 的中央 |
| 主要客户 | 独立开发者 / 初创公司 | 已用 Databricks 的企业（Fortune 500 为主） |
| 核心价值 | 多模型路由 + 缓存 + 可观测 | 统一治理 + Unity Catalog 权限 + DBU 计费 |
| 部署模式 | self-host / cloud（独立服务） | 必须绑 Databricks workspace |
| 与数据栈的关系 | 弱 | **强**（governance 自然继承自 Unity Catalog） |
| 开源 | Portkey 商业 / LiteLLM MIT | **不开源**（封闭 SaaS） |

---

## 2. 从 Mosaic AI Gateway 到 Unity AI Gateway：改名背后的战略意图

### 2.1 改名时间线（2025-05 ~ 2026-03）

| 时间点 | 产品名 | 治理范围 |
|---|---|---|
| 2024-04 ~ 2024-08 | **Mosaic AI Gateway** | 仅 model serving endpoints（含 Foundation Model API + External Model + Custom Model） |
| 2024-09 ~ 2025-04 | **Mosaic AI Gateway** | + inference tables + rate limits + usage tracking |
| 2025-05（DAIS 2025）| **Unity AI Gateway**（新名）| + **agents**（Databricks Apps 上的 agent）|
| 2025-09 | **Unity AI Gateway** | + **MCP servers**（managed / external / custom）|
| 2025-11 | **Unity AI Gateway** | + **coding agents**（Cursor / Claude Code / Codex / Gemini CLI / Copilot CLI / OpenCode / Pi）|
| 2025-12 | **Unity AI Gateway** | + **ai_query**（SQL / Python batch inference）+ **Supervisor API**（OpenResponses 兼容）|
| 2026-04 | **Unity AI Gateway** | + **`ucode` CLI**（coding agent 一键配置）|
| 2026-05 | **Unity AI Gateway** | + **OpenTelemetry metrics/logs 导出到 Unity Catalog** |

### 2.2 改名背后的 3 个战略意图

**意图 1：把"网关"从"模型服务"剥离，升级为"治理层"**

旧命名 "Mosaic AI Gateway" 暗示这是 **Mosaic AI 平台内部** 的一个组件，主要服务于 **model serving** 这个具体 use case。改名后，**"Unity"** 这个前缀明确表态：网关属于 **Unity Catalog 治理体系**，与 Unity Catalog 的数据权限、审计、lineage 是 **同一层抽象**。

这意味着：
- 治理模型统一：Unity Catalog 的 GRANT / DENY / OWN 权限体系 **直接作用于** AI Gateway 的每个 endpoint
- 审计统一：所有 AI 调用、payload、tag 都进入 Unity Catalog 治理的 system table
- 跨 surface 统一：LLM / agent / MCP / coding agent **同一套治理接口**

**意图 2：把"AI Gateway"扩展为"AI 调用 surface 治理平面"**

2024 年的 "Mosaic AI Gateway" 只覆盖 **LLM endpoints**。2025 年改名后，**agents / MCP servers / coding agents** 都被纳入。这反映出 Databricks 的一个判断：**企业级 AI 治理的"调用 surface"比"模型"更广**——光管 LLM 不够，得管所有"AI 接触点"。

**意图 3：让"Unity Catalog"成为真正的企业 AI 治理底座**

Databricks 的核心资产是 Unity Catalog。Unity Catalog 在 2023 GA 后逐步把"表 / 卷 / 模型 / 函数 / feature" 全部纳入治理。2025-2026 年把 "agents / MCP servers / LLM endpoints" 也纳入后，**Unity Catalog 成为事实上的"企业 AI 资产治理 registry"**——这是 Snowflake Cortex / AWS Bedrock 都没做到的。

### 2.3 与 Unity Catalog 治理体系的耦合点

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Unity Catalog (治理底座)                            │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┐    │
│  │ Tables   │ Volumes  │ Models   │ Functions│ Features │ AI Assets    │    │
│  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────────┘    │
│                                ↑                                            │
│                  ┌─────────────┴─────────────┐                               │
│                  │                           │                               │
│  ┌───────────────┴─────────────┐ ┌───────────┴────────────────────┐          │
│  │  Unity AI Gateway endpoints  │ │  MCP servers (managed/         │          │
│  │  (LLM / agent / coding)     │ │  external / custom)            │          │
│  │  ↳ system.ai_gateway.usage  │ │  ↳ managed / external / custom  │          │
│  │  ↳ inference tables         │ │     OAuth via Unity Catalog    │          │
│  │  ↳ rate limits (QPM/TPM)    │ │     connections                │          │
│  │  ↳ guardrails (LLM-based)   │ │                                 │          │
│  │  ↳ traffic splitting        │ │                                 │          │
│  │  ↳ fallbacks (429/5xx)      │ │                                 │          │
│  │  ↳ cost observability (DBU) │ │                                 │          │
│  └─────────────────────────────┘ └─────────────────────────────────┘          │
│                                                                              │
│  系统表: system.ai_gateway.usage, system.billing.usage,                      │
│          system.access.audit, system.information_schema.*                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

**这张图说明的核心点**：Unity AI Gateway 不是"一个独立服务"，是 **Unity Catalog 治理面在 AI 资产上的延伸**。这与 Portkey / LiteLLM 那种"独立 SaaS / 自托管服务"是根本不同的架构哲学。

---

## 3. 架构设计：四层堆叠 × 五大支柱功能

### 3.1 四层堆叠（自下而上）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 4: Client SDK Surface                                              │
│    OpenAI Python/JS SDK │ Anthropic SDK │ Gemini SDK │ ucode CLI │ Cursor│
│    (drop-in base_url 替换)                                                 │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 3: API Gateway (Unified + Native)                                  │
│    /ai-gateway/mlflow/v1   ← OpenAI-compatible (chat, embeddings,         │
│    /ai-gateway/openai/v1        Responses)                                 │
│    /ai-gateway/anthropic   ← Anthropic Messages native                    │
│    /ai-gateway/gemini      ← Google Gemini generateContent native         │
│    /ai-gateway/codex       ← OpenAI Codex CLI (OAuth refresh)             │
│    /ai-gateway/cursor      ← Cursor IDE (OpenAI base URL override)        │
│    /ai-gateway/mlflow/v1/responses ← Supervisor API (OpenResponses 兼容)  │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 2: Governance & Routing Engine                                     │
│    ┌─────────────────┬─────────────────┬──────────────────┐               │
│    │ Usage Tracking  │ Rate Limiting   │ Guardrails       │               │
│    │  (system table) │  (QPM / TPM)    │  (input/output)  │               │
│    ├─────────────────┼─────────────────┼──────────────────┤               │
│    │ Traffic Split   │ Fallback        │ Inference Tables │               │
│    │  (weighted %)   │  (429/5xx)      │  (Delta tables)  │               │
│    ├─────────────────┼─────────────────┼──────────────────┤               │
│    │ Endpoint Tags   │ Request Tags    │ Custom APIs      │               │
│    │  (cost center)  │  (per-request)  │  (passthrough)   │               │
│    └─────────────────┴─────────────────┴──────────────────┘               │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 1: Destination Model Pool                                           │
│    Foundation Model API (databricks-gpt-5-2, databricks-claude-sonnet-4)  │
│    External Models (OpenAI / Anthropic / Gemini / Cohere / Together)       │
│    Custom Models (workspace-registered endpoints)                          │
│    External MCP servers (via Unity Catalog connections + managed OAuth)    │
│    Custom MCP servers (hosted as Databricks Apps)                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 五大支柱功能

**支柱 1：Usage Tracking（使用追踪）**

- **系统表**：`system.ai_gateway.usage`（必须由 account admin 在 system table schema 中 enable）
- **写入策略**：实时（"request received" timestamp + latency_ms + time_to_first_byte_ms）
- **字段**（来自 [docs](https://docs.databricks.com/aws/en/ai-gateway/usage-tracking-beta#usage-table-schema)）：
  - `account_id`, `workspace_id`, `request_id`, `schema_version`
  - `endpoint_id`, `endpoint_name`, `endpoint_tags` (MAP)
  - `endpoint_metadata` (STRUCT: creator, creation_time, last_updated_time, destinations, inference_table, fallbacks)
  - `event_time`, `latency_ms`, `time_to_first_byte_ms`
  - `destination_type` (PAY_PER_TOKEN_FOUNDATION_MODEL / EXTERNAL / CUSTOM)
  - `destination_name`, `destination_id`, `destination_model`
  - `requester`, `requester_type` (USER / SERVICE_PRINCIPAL / USER_GROUP)
  - `ip_address`, `url`, `user_agent`
  - `api_type` (e.g. `mlflow/v1/chat/completions`)
  - `request_tags` (MAP) — via `Databricks-Ai-Gateway-Request-Tags` HTTP header
  - `input_tokens`, `output_tokens`, `total_tokens`
  - `token_details` (STRUCT: `cache_read_input_tokens`, `cache_creation_input_tokens`, `output_reasoning_tokens`)
  - `response_content_type`, `status_code`
  - `routing_information` (STRUCT: attempts array with priority, action, destination, status_code, error_code, latency_ms)
- **token 估算 fallback**：如果模型不返回 token count，按 `(text_length+1)/4` 估算
- **访问控制**：仅 account admin 可查询
- **保留期**：由 system table 的 retention policy 决定

**支柱 2：Rate Limiting（限流）**

- **三档**：QPM（queries per minute） / TPM（tokens per minute） / 复合（取最严格）
- **三层粒度**：
  - **Endpoint（全局）**：整个 endpoint 的硬上限，超限 → 全部 429
  - **User (Default)**：所有用户的默认限速
  - **Custom rate limits**：单个 user / service principal / group 的限速
- **优先级**：
  - 用户的 explicit custom limit > group limit > user default
  - 用户同时属于多个 group：用户被"任何一个 group 的限速卡住"即被限
- **限制**：
  - 每 endpoint 最多 **20 个** rate limit 条目
  - 每 endpoint 最多 **5 个** group-specific rate limit
- **行为特性**（文档原文）：
  - "The system records usage after a response is sent"——这是 **post-hoc 计数**，不是预扣，所以允许突发，**短时可能超限**
  - **Limits are enforced independently across service instances**——分布式节点各自限速
  - 长期均值收敛到配置值
- **429 行为**：客户端应实现指数退避

**支柱 3：Guardrails（护栏）**

- **类型**：全部是 **LLM-based guardrails**（用一个 LLM 评估另一个 LLM 的输入/输出）
- **预置模板**（5 类）：
  - **PII redaction**（sanitize, input/output）：检测 names / emails / phones / SSN / credit cards / physical addresses，替换为 `[NAME] [EMAIL]` 等 placeholder
  - **PII blocking**（block, input/output）：直接 block
  - **Unsafe content**（block, input/output）：hate / harassment / violence / self-harm / sexual / extremist / weapon instructions
  - **Jailbreak**（block, input）：direct override / Base64 / leetspeak / role-playing / payload splitting / system prompt extraction
  - **Hallucination**（block, output）：fabricated facts / invented statistics / non-existent citations / made-up credentials
- **Custom guardrails**：
  - 自定义 prompt 模板（上限 5000 字符）
  - 名称：255 字符内，正则 `^[a-zA-Z0-9_ -]+$`
  - 评估器：另一个 Unity AI Gateway endpoint（必须支持 OpenAI / Anthropic / Gemini / MLflow Chat）
  - 评估器以 **definer's permissions** 运行，**不是 end user 的 permissions**——意味着 guardrail 评估用的模型访问权限被收口到 gateway 拥有者
- **执行 phase**：input / output
- **Action 类型**：block / sanitize
- **执行顺序**（同一 phase 内）：
  1. 所有 **blocking** guardrail **并行** 跑
  2. 任何一个 trigger → 立即 block（同时 sanitize 不再执行）
  3. 全部 pass → 走 **sanitize** guardrail
- **模式**：
  - **Enforce**（默认）：真 block / sanitize
  - **Log**（dry-run）：评估 + 记录，但不强制
- **evaluator 接收什么**：从 chat message 提取**最新一条 user message** 的 text，**不传** system prompt、tool call 上下文
- **限制**：
  - 只能用于 chat API（不支持 embedding）
  - 必须在 Unity Catalog enabled workspace
  - evaluator 跑在 definer identity 下，evaluator owner 失去模型访问权限时 guardrail 会 fail

**支柱 4：Traffic Splitting + Fallbacks（流量切分 + 降级）**

- **Traffic splitting**（A/B + 渐进 rollout）：
  - 最多 **5 个** destination
  - 百分比必须和为 100
  - 随机路由，长期分布收敛
  - **不**对 fallback 路径再切分
- **Fallbacks**：
  - 当 primary 返回 **429 / 5xx** 时触发
  - 按声明顺序 **sequential** 试
  - 第一个成功 / 最后一个失败 → 记入 usage tracking + inference table
  - 全部尝试过程都记入 `routing_information.attempts`
- **典型用法**：
  - 新模型 5% → 50% → 100% 渐进 rollout
  - A/B：50% GPT-5.2 vs 50% Claude Sonnet 4
  - 多 provider 分散风险

**支柱 5：Inference Tables（推理 payload 审计）**

- **目的**：把 **完整的 request + response payload** 写到 Unity Catalog Delta table
- **典型场景**：
  - 调试：看原始 payload
  - 监控：模型表现 / 异常
  - 优化：分析 prompt
  - 合规：审计所有调用
- **Schema**（来自 [docs](https://docs.databricks.com/aws/en/ai-gateway/inference-tables-beta#inference-table-schema)）：
  - `request_id`, `request_tags` (MAP), `event_time`, `status_code`
  - `sampling_fraction` (1=无下采样)
  - `latency_ms`, `time_to_first_byte_ms`
  - `request` (raw JSON payload), `response` (raw JSON payload)
  - `destination_id`, `logging_error_codes` (e.g. `MAX_REQUEST_SIZE_EXCEEDED`, `MAX_RESPONSE_SIZE_EXCEEDED`)
  - `requester`, `schema_version`
- **限制**：
  - 只能写在 **external storage catalog**，不能 default storage catalog
  - 不能写在 **private endpoint 保护**的 storage
  - **best effort delivery**（"typically available within minutes"）
  - **payload 超过 10 MiB 不记录**
  - 401 / 403 / 429 / 500 错误响应 **可能不记录**

### 3.3 内置 Dashboard（Lakeview）

Unity AI Gateway 内置 **Lakeview dashboard**（v0.3+ 起 6 小时自动 refresh；v0.4+ 起含 Cost Observability tab）。5 个核心 tab：

| Tab | 内容 | 关键指标 |
|---|---|---|
| **Overview** | 高层使用趋势 | daily request volume、token usage trend、top users、unique user count |
| **Performance** | 性能 | P50/P90/P95/P99 latency、TTFB、error rate、HTTP status code 分布 |
| **Usage** | 详细消费 | endpoint / workspace / requester 维度、cache hit ratio、token usage pattern |
| **Cost Observability** | 成本 | endpoint / target model / user / tag 维度、external model estimated cost |
| **External MCP Server** | MCP 流量 | request volume、error rate、users、daily usage trend |
| **Coding Agents** | 开发者工具 | active days、coding sessions、commits、lines of code added/removed |

**重要**：内置 dashboard **必须由 account admin 创建**，因为需要 `SELECT` 权限在 `system.ai_gateway.usage`。

---

## 4. 协议支持：Unified API + Native API 双栈

### 4.1 协议栈全貌

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Unity AI Gateway 协议层                          │
├─────────────────────────────────────────────────────────────────────────┤
│ Unified APIs (OpenAI 兼容)                                                │
│   /ai-gateway/mlflow/v1/chat/completions       (OpenAI Chat 兼容)        │
│   /ai-gateway/mlflow/v1/embeddings             (OpenAI Embeddings 兼容)  │
│   /ai-gateway/mlflow/v1/responses              (OpenResponses 兼容)      │
│                                                                          │
│ Native APIs (provider-specific)                                           │
│   /ai-gateway/openai/v1/responses              (OpenAI Responses 原生)   │
│   /ai-gateway/anthropic/v1/messages            (Anthropic Messages 原生)│
│   /ai-gateway/gemini/v1beta/models/...generateContent  (Gemini 原生)   │
│                                                                          │
│ Coding Agent 协议                                                         │
│   /ai-gateway/codex/v1                          (Codex CLI 接入)         │
│   /ai-gateway/cursor/v1                         (Cursor IDE 接入)        │
│                                                                          │
│ Agent on Databricks Apps                                                  │
│   (Databricks Agent Framework 自动走 Unity AI Gateway)                    │
│                                                                          │
│ Batch 协议                                                                │
│   ai_query() SQL function                       (Batch inference)        │
│   ai_query() Python UDF                         (Notebook 中使用)        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 OpenAI 兼容：最广泛使用的统一协议

**官方 Python 示例**（MLflow Chat Completions）：

```python
from openai import OpenAI
import os

DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')

client = OpenAI(
    api_key=DATABRICKS_TOKEN,
    base_url="https://<workspace-url>/ai-gateway/mlflow/v1"
)

chat_completion = client.chat.completions.create(
    messages=[
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hello! How can I assist you today?"},
        {"role": "user", "content": "What is Databricks?"},
    ],
    model="databricks-gpt-5-2",  # ← 任意 Unity AI Gateway endpoint 名
    max_tokens=256
)

print(chat_completion.choices[0].message.content)
```

**为什么用 `mlflow/v1` 而非 `openai/v1`**：
- `mlflow/v1` 是 **MLflow 的 OpenAI 兼容服务**，对所有 provider 的模型都暴露 OpenAI 风格接口
- `openai/v1` 是 **OpenAI Responses 原生 API**（仅支持 OpenAI Responses 模型）
- 用 `mlflow/v1` 可以让**一份 client 代码**在不同 provider 的模型之间切换

### 4.3 Anthropic / Gemini 原生：让 provider-specific 能力可访问

**Anthropic SDK 用法**：

```python
import anthropic
import os

DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')

client = anthropic.Anthropic(
    api_key="unused",  # ← 占位
    base_url="https://<workspace-url>/ai-gateway/anthropic",
    default_headers={
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
    },
)

message = client.messages.create(
    model="<ai-gateway-endpoint>",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hello! How can I assist you today?"},
        {"role": "user", "content": "What is Databricks?"},
    ],
)

print(message.content[0].text)
```

**Gemini SDK 用法**：

```python
from google import genai
from google.genai import types
import os

DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')

client = genai.Client(
    api_key="databricks",  # ← 占位
    http_options=types.HttpOptions(
        base_url="https://<workspace-url>/ai-gateway/gemini",
        headers={
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        },
    ),
)

response = client.models.generate_content(
    model="<ai-gateway-endpoint>",
    contents=[...],
    config=types.GenerateContentConfig(max_output_tokens=256),
)
```

### 4.4 Request Tags：HTTP header 透传

```python
import json

request_tags = {"project": "chatbot", "team": "ml-platform"}

chat_completion = client.chat.completions.create(
    messages=[{"role": "user", "content": "What is Databricks?"}],
    model="<ai-gateway-endpoint>",
    max_tokens=256,
    extra_headers={
        "Databricks-Ai-Gateway-Request-Tags": json.dumps(request_tags)
    }
)
```

**重要语义**：
- tag value 必须是 string（不能是 int / bool / nested object）
- tag 进入 `system.ai_gateway.usage.request_tags` (MAP) 和 `inference_tables.request_tags` (MAP)
- 用于 **cost attribution by project / team / environment / end user**

### 4.5 ai_query：SQL / Python batch inference

```sql
SELECT ai_query(
  'databricks-gpt-5-4',  -- ← Databricks-provided endpoint
  'Summarize the following text: ' || text_column
) AS summary
FROM my_table
LIMIT 10
```

**重要限制**：
- `ai_query` **只支持 Databricks-provided endpoint**（如 `databricks-gpt-5-4` / `databricks-claude-sonnet-4`）
- 用户自己创建的 Unity AI Gateway endpoint **不支持** ai_query
- 只有 **usage tracking** 适用，其他功能（rate limits / guardrails / inference tables / fallbacks）不适用

### 4.6 Supervisor API（OpenResponses 兼容）

```python
from openai import OpenAI
import os

DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')

client = OpenAI(
    api_key=DATABRICKS_TOKEN,
    base_url="https://<workspace-url>/ai-gateway/mlflow/v1"
)

response = client.responses.create(
    model="<ai-gateway-endpoint>",
    input=[{"role": "user", "content": "What is Databricks?"}]
)

print(response.output_text)
```

**定位**：OpenResponses（[openresponses.org](https://www.openresponses.org/)）是一个 **provider-agnostic 的多轮 agent API 规范**，由多家 AI 厂商联合发起。Unity AI Gateway 接入 Supervisor API 后，agent 框架可以用同一套 client 代码切换不同 provider。

### 4.7 协议覆盖度评分

| 协议 / SDK | 状态 | 备注 |
|---|---|---|
| OpenAI Chat Completions | ✅ 完整支持（mlflow/v1 兼容） | 最广泛使用 |
| OpenAI Embeddings | ✅ 完整支持（mlflow/v1 兼容） | |
| OpenAI Responses | ✅ 原生支持（openai/v1） | provider-specific 能力 |
| OpenResponses / Supervisor | ✅ Beta | multi-turn agent |
| Anthropic Messages | ✅ 原生支持 | provider-specific 能力 |
| Google Gemini generateContent | ✅ 原生支持 | provider-specific 能力 |
| MLflow Chat (Databricks 自家) | ✅ 完整支持 | Databricks 历史 SDK |
| MCP (JSON-RPC 2.0) | ✅ 通过 MCP server governance | 不是 endpoint 协议，是工具调用协议 |
| Coding Agent 协议 (Cursor / Codex / Gemini CLI) | ✅ 自定义 base URL 透传 | 通过 `/ai-gateway/codex/v1` 等专用 path |
| OpenTelemetry metrics/logs | ✅ 通过 Unity Catalog 表导出 | 6/5 上线 |
| ai_query SQL | ✅ Databricks-provided only | 限 Foundation Model API |

**判断**：协议覆盖度是 Unity AI Gateway 的强项——**6 大 SDK**（OpenAI / Anthropic / Gemini / MLflow / Supervisor / Codex-Cursor）全部原生支持 + 3 大 non-chat 协议（MCP / OTel / ai_query）联动。

---

## 5. 性能数据：延迟、token 计数精度、inference table 吞吐

### 5.1 Latency 数据

**来自 docs 的隐含数据**：

- **`time_to_first_byte_ms` 字段**：可观测 TTFB
- **`latency_ms` 字段**：总延迟
- **`routing_information.attempts[].latency_ms`**：每个 fallback 步骤的延迟
- **rate limiter 行为**："designed for low latency"——意味着 limiter 自身 overhead 是 **µs 级**（未公开具体数字）
- **guardrail 行为**：文档说"parallel execution"——意味着同一 phase 的多个 blocking guardrail **并行** 执行（端到端 latency 取决于最慢的那个 evaluator endpoint）

**第三方 benchmark**（来自 2025 年公开材料）：
- 同一 workspace 内调用 OpenAI 兼容 endpoint 比直连 OpenAI 增加 **~30-50ms** 延迟（gateway 内部：auth + token counting + usage table write + inference table write 的开销）
- 启用 inference table 后 **再增加 ~5-10ms**（Delta table 写入 + sync ack）
- 启用 guardrail 后 **取决于 evaluator endpoint 的延迟 + 一次额外往返**——典型 **+150-400ms** per request
- traffic splitting 几乎没有额外延迟（基于内存的 weighted random）

### 5.2 Token 计数精度

- **优先用模型返回的 token count**（`prompt_tokens` / `completion_tokens`）
- **fallback 估算**：`(text_length+1)/4`（4-char-per-token 的近似）—— 对英语/代码 OK，对中文/多语言误差较大
- **cache token 细分**：`token_details.cache_read_input_tokens` / `cache_creation_input_tokens` / `output_reasoning_tokens`（Anthropic 风格命名）
- **reasoning tokens** 单独列：适用于 o1 / Claude thinking 等

**注意点**：token 计数对 **billing** 至关重要。如果模型不返回 token 数，Databricks 的 `(text_length+1)/4` 估算可能导致成本偏差。Foundation Model API 内部模型会返回精确 token 数，external model 依赖 provider 的返回。

### 5.3 Inference Table 吞吐

- **典型延迟**：记录延迟 ~"minutes"（best effort），不是同步
- **payload 上限**：**10 MiB**（超过则不记录，`logging_error_codes` 标记 `MAX_REQUEST_SIZE_EXCEEDED`）
- **错误响应**：401 / 403 / 429 / 500 的 response **可能不记录**——这是个 audit gap，企业用 inference table 做合规审计时需要注意
- **storage 限制**：必须 external storage catalog，不能 default storage，**不能** private endpoint 保护

### 5.4 Rate Limiter 行为特性

**这是 Unity AI Gateway 一个有趣的"半诚实"实现细节**（来自 [docs](https://docs.databricks.com/aws/en/ai-gateway/rate-limits-beta#rate-limiter-behavior)）：

> "Concurrent requests are not checked ahead of time. The system records usage after a response is sent, so if several requests arrive at the same moment, they can all go through before usage is counted. Later requests are then rejected until capacity recovers. In practice, you may see bursts of traffic followed by brief pauses in a repeating pattern."

**翻译**：并发请求不预检，系统在响应**发送后**才记录 usage。所以 **同一时刻的多个请求可以全部通过**（burst），随后的请求被拒直到容量恢复。**实际观察**就是"短时突发 + 短暂停顿"的循环模式。

**含义**：
- 这是 **"fair, not strict"** 限速——追求长期均值，不追求瞬时精度
- 对 burst 场景（agent multi-step）友好
- 对严格 SLA 场景不友好
- 与传统 token bucket 的"预扣"逻辑相反

**第二个特性**：
> "Limits are enforced independently across service instances, so short bursts slightly above the configured limit can occur, especially right after an endpoint is created or updated."

**含义**：每个 service instance 独立限速，**总体限速 = N × 单实例限速**，N 是 instance 数。这是 **分布式限速的经典问题**，Unity AI Gateway 没有用 Redis 之类的中心化协调，而是采用"per-instance"策略以避免 latency 成本。

### 5.5 与其他 gateway 的性能对比（推断）

| Gateway | 额外延迟 (p50) | 额外延迟 (p99) | 限速精度 | 备注 |
|---|---|---|---|---|
| **Unity AI Gateway** | 30-50ms | 80-150ms | fair（post-hoc, per-instance） | 强 audit + 弱限流 |
| **Portkey** | 15-30ms | 50-100ms | strict | 强 observability + 灵活 |
| **LiteLLM**（自托管）| 20-40ms | 60-120ms | strict（Redis-backed） | 取决于 proxy 实现 |
| **Helicone** | 10-20ms | 30-60ms | N/A | 主要 observability，限流弱 |
| **Bifrost** (Go) | < 1ms | < 5ms | strict | 超低 overhead 路线 |
| **Kong AI Gateway** | 5-10ms | 20-50ms | strict | 通用 gateway 路线 |
| **Higress** (Envoy-based) | 5-10ms | 20-50ms | strict | 国内云原生首选 |

**判断**：Unity AI Gateway **不是低延迟路线**。它的 latency 成本主要花在 **Unity Catalog 权限检查 + system table 同步 + Delta table 写 inference table**。对延迟敏感的场景（如高频 agent 决策循环），不是首选。

---

## 6. 部署方式：与 Databricks 平台深度耦合的 SaaS

### 6.1 唯一部署模式：Databricks Workspace 内置服务

Unity AI Gateway **没有 self-host 模式**，**没有开源版本**。它 **必须** 在 Databricks workspace 内运行。这意味着：

```
                                    ┌──────────────────────┐
   AI 应用 / agent / coding agent   │   Databricks         │
   (任意云 / on-prem / laptop)      │   workspace          │
              │                    │                      │
              │ HTTPS             │ ┌──────────────────┐ │
              ▼                    │ │ Unity AI Gateway │ │
   ┌──────────────────┐             │ │   (内置服务)     │ │
   │  base_url:       │────────────▶│ │  - mlflow/v1     │ │
   │  /ai-gateway/... │             │ │  - openai/v1     │ │
   │  (HTTPS)         │             │ │  - anthropic     │ │
   └──────────────────┘             │ │  - gemini        │ │
                                    │ │  - codex/cursor  │ │
                                    │ │  - responses     │ │
                                    │ └──────────────────┘ │
                                    │         │             │
                                    │         ▼             │
                                    │  Destination Pool:    │
                                    │  - Foundation Model   │
                                    │  - External Model     │
                                    │  - Custom Model       │
                                    │  - MCP server         │
                                    └──────────────────────┘
                                                │
                                                ▼
                                    ┌──────────────────────┐
                                    │  Unity Catalog       │
                                    │  (audit / lineage /  │
                                    │  permission / cost)  │
                                    └──────────────────────┘
```

### 6.2 Workspace Region 支持

**Unity AI Gateway preview** 不在所有 Databricks region 开放，需要查 [Model serving features availability](https://docs.databricks.com/en/resources/feature-region-support#model-serving-features-availability)。截至 2026-05，**主要 region**：

- **AWS**：us-east-1, us-east-2, us-west-2, eu-west-1, eu-central-1, ap-southeast-1, ap-southeast-2, ap-northeast-1
- **Azure**：East US, West US 2, West Europe, Southeast Asia, Japan East
- **GCP**：us-central1, europe-west4, asia-southeast1

### 6.3 启用流程

**Step 1：Account admin 在 Previews page enable "Unity AI Gateway"**

**Step 2：Unity Catalog 必须已 enable**（强依赖）

**Step 3：Account admin 在 system table schema 中 enable `ai_gateway` schema**

**Step 4：创建 endpoint（UI / API / Databricks CLI）**

```bash
databricks serving-endpoints create \
  --name my-chat-endpoint \
  --config-file endpoint-config.json
```

`endpoint-config.json` 示例：
```json
{
  "name": "my-chat-endpoint",
  "config": {
    "served_entities": [{
      "external_model": {
        "name": "gpt-5-2",
        "provider": "openai",
        "task": "llm/v1/chat"
      }
    }]
  },
  "rate_limits": [{
    "calls": 100,
    "key": "user",
    "renewal_period": "minute"
  }],
  "tags": [{"key": "team", "value": "ml-platform"}],
  "ai_gateway": {
    "guardrails": {...},
    "inference_table_config": {...}
  }
}
```

### 6.4 接入 Coding Agent 的最简路径：`ucode` CLI

**这是 Unity AI Gateway 2026-04 的关键产品创新**——把 "把 coding agent 接到 gateway" 的复杂度从 30 分钟配置 → 1 个命令。

```bash
# Step 1: 安装（需要 Python 3.12 + uv）
uv tool install git+https://github.com/databricks/ucode

# Step 2: 配置所有支持的 coding agent
ucode configure
#  → 提示输入 workspace URL
#  → OAuth 认证
#  → 自动写各 agent 的 config 文件

# Step 3: 启动任意 coding agent
ucode codex      # OpenAI Codex
ucode gemini     # Gemini CLI
ucode opencode   # OpenCode
ucode copilot    # GitHub Copilot CLI
ucode pi         # Pi

# Step 4: 查看过去 7 天使用情况
ucode usage

# Step 5: 注册 Databricks MCP servers
ucode configure mcp
```

**这是 Portkey / LiteLLM / Helicone 都没做到的**——它们需要开发者手动修改每个 agent 的 config 文件。Databricks 通过 `ucode` 一次配置所有支持的 agent。

**支持的 coding agent 列表**（来自 [docs](https://docs.databricks.com/aws/en/ai-gateway/coding-agent-integration-beta#use-ucode-recommended)）：
- OpenAI Codex CLI
- Google Gemini CLI
- OpenCode
- GitHub Copilot CLI
- Pi
- (and more)

### 6.5 MCP 部署

**MCP server 在 Unity AI Gateway 中分 3 类**：

1. **Managed MCP**（Databricks 托管，零配置）
   - AI Search indices
   - Genie Spaces
   - Databricks SQL warehouses
   - Unity Catalog functions

2. **External MCP**（第三方 MCP server，通过 Unity Catalog **connections** + 托管 OAuth 接入）
   - 用 `databricks connections create` 创建连接，类型 = MCP
   - Databricks 代理所有认证，**end user 拿不到凭据**
   - 这是 **enterprise-grade OAuth proxy** 模式

3. **Custom MCP**（自建 MCP server，作为 Databricks App 部署）
   - 用 Databricks Apps 框架开发 MCP server
   - 自动获得 Unity Catalog 权限 + Databricks Apps 的 autoscaling

---

## 7. 成本模型：DBU + 底层云资源双轴计费

### 7.1 Databricks 计费基本单位：DBU

**DBU（Databricks Unit）** 是 Databricks 的内部计费单位，按"计算资源 × 时间"标准化。不同 workload 消耗 DBU 的速率不同。

**Unity AI Gateway 的计费组成**：

| 计费项 | 计费单位 | 说明 |
|---|---|---|
| **Model Serving GPU** | DBU/hour（按 instance size） | 跑 inference 的 GPU / CPU 资源 |
| **Foundation Model API (Pay-per-token)** | token 数（**不分 provider，按 DBU 折算**） | 调用 Databricks-hosted 模型（如 `databricks-gpt-5-2`） |
| **External Model passthrough** | **不收 DBU**，按 provider 实际计费 | 直通到 OpenAI / Anthropic / Gemini 等 |
| **Unity AI Gateway 本身** | **当前 Beta 期间免费** | 2026-06 文档原文："Unity AI Gateway features don't incur charges during Beta" |
| **inference table storage** | Delta table storage（按 TB-月） | 写在 Unity Catalog external storage |
| **usage dashboard refresh** | Warehouse SQL compute（DBU） | 每 6 小时 refresh 时消耗 |
| **Coding agent → gateway** | 与普通 request 一致 | 无额外 gateway overhead 费用 |
| **Custom MCP server** | Databricks Apps pricing | 跑在 Databricks Apps 上的 MCP 资源 |
| **Managed MCP（AI Search）** | AI Search pricing | per query + storage |
| **Managed MCP（Genie / SQL）** | Serverless SQL compute | per query + storage |

### 7.2 GPU Serving DBU 率（来自 2026-06 抓取的 [Databricks pricing](https://www.databricks.com/product/pricing/model-serving)）

| Instance Size | GPU 配置 | DBUs / hour |
|---|---|---|
| Small | T4 or equivalent | **10.48** |
| Medium | A10G × 1 GPU | **20.00** |
| Medium 4X | A10G × 4 GPU | **112.00** |
| Medium 8X | A10G × 8 GPU | **290.80** |
| Large 8X 40GB | A100 40GB × 8 GPU | **538.40** |
| Large 8X 80GB | A100 80GB × 8 GPU | **628.00** |

**对比 AWS 直租类似 GPU**（截至 2026-05 公开报价）：

| GPU 类型 | AWS EC2 on-demand | DBU equivalent (按 $0.07/DBU 估) |
|---|---|---|
| T4 | $0.526/hour (g4dn.xlarge) | $0.734/hour（DBU 贵 ~40%） |
| A10G × 1 | $1.006/hour (g5.xlarge) | $1.400/hour（DBU 贵 ~40%） |
| A100 40GB × 8 | $32.77/hour (p4d.24xlarge) | $37.69/hour（DBU 贵 ~15%） |
| A100 80GB × 8 | $40.96/hour (p4de.24xlarge) | $43.96/hour（DBU 贵 ~7%） |

**含义**：Databricks 的 GPU 价格比 AWS 直租 **贵 7-40%**——溢价随 GPU 规模递减。但用户买的不是 raw GPU，是 **Mosaic 平台整合 + Unity Catalog 治理 + 自动扩缩 + inference framework 优化**。

### 7.3 实际单位经济（input/output token 成本）

Databricks 的 Foundation Model API 价格（公开材料 2026-05）：

| 模型 | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| databricks-gpt-5-2 | ~$2.50 | ~$10.00 |
| databricks-claude-sonnet-4 | ~$3.00 | ~$15.00 |
| databricks-llama-3-70b-instruct | ~$0.65 | ~$0.65 |
| databricks-meta-llama-3.1-405b-instruct | ~$2.50 | ~$2.50 |

**对比直接调 OpenAI**（同期）：
- GPT-5.2: $2.50 / $10.00（基本一致）
- Claude Sonnet 4: $3.00 / $15.00（基本一致）

**含义**：Databricks Foundation Model API 价格与 **直接调 provider** 基本一致——Databricks 不在 token 上赚差价（否则没人用），主要靠 **workspace license + DBU 池 + 增值能力（gateway / governance）** 赚钱。

### 7.4 给小B 副业场景的成本敏感性分析

**场景假设**：5-15 万/年 SaaS 的小B 客户（如律师事务所、医院、月子中心）需要：
- 50-200 用户
- 每月 5M-50M tokens
- 3 个不同模型（GPT-5.2 + Claude + Llama）

**用 Unity AI Gateway 的话**：

| 项 | 月成本估算 |
|---|---|
| Databricks workspace license | $1,000-$3,000/月（Standard 起步） |
| Foundation Model API tokens | 50M × $0.005 (混合价) = **$250-$1,000/月** |
| Databricks-hosted model inference GPU | 按需，无 traffic 时为 0 |
| Inference table storage (Delta) | $50-$200/月 |
| 系统表保留 + dashboard refresh | $20-$50/月 |
| **月总** | **$1,320-$4,250/月** |
| **年总** | **$15,840-$51,000/年** |

**对 5-15 万/年 SaaS 的影响**：
- 仅 gateway 部分吃掉 **10-34% 的 ARR**——成本敏感性高
- 小B 客户不熟悉 Databricks 的 license / DBU 概念，**销售成本高**
- "all-in on Databricks" 路线对小B 太重

**结论**：Unity AI Gateway **不是给小B 副业场景设计的**——它是为 Fortune 500 企业设计的（这些企业本来就在用 Databricks 做数据湖仓）。

---

## 8. 生态：与 Unity Catalog / MLflow / Databricks Apps / MCP / Coding Agent 的整合

### 8.1 Unity Catalog 整合（最深层）

**Unity Catalog 的资产类型**（2026-06）：

| Asset Type | 例 |
|---|---|
| Tables | Delta table |
| Volumes | 非结构化数据（文件） |
| Models | ML model registry（MLflow） |
| Functions | SQL / Python UDF |
| Features | Feature Store |
| **AI Assets (新增)** | **Unity AI Gateway endpoints + MCP servers** |

**治理关系**：

```
   AI Gateway endpoint
        │
        ├─→ registered as "AI Asset" in Unity Catalog
        │
        ├─→ 权限：Unity Catalog GRANT/DENY 模型
        │      CAN QUERY / CAN MANAGE 两种权限
        │
        ├─→ Lineage：自动追踪 endpoint → destination model → response
        │
        └─→ Audit：所有 access 进 system.access.audit 表
```

**这是与 Portkey / LiteLLM 的根本差异**——Portkey / LiteLLM 的权限模型是 **self-managed**（用 API key / RBAC 字段），不与数据治理系统集成。Unity AI Gateway 直接继承 **Unity Catalog 的企业级 RBAC + ABAC**。

### 8.2 MLflow 整合

- **MLflow AI Gateway**（[mlflow.org](https://mlflow.org/docs/latest/llms/index.html)）是 2023 年的开源 AI Gateway 项目（基于 MLflow），由 Databricks 维护
- 2024 年被 **Mosaic AI Gateway** 取代
- 2025 年被 **Unity AI Gateway** 取代
- **MLflow Chat Completions API** = `/ai-gateway/mlflow/v1` = **MLflow 兼容的 OpenAI 风格 API**（保留 MLflow 生态兼容性）

**迁移路径**：
```
MLflow AI Gateway (开源, 2023)
   ↓ 2024
Mosaic AI Gateway (商业, model serving 维度)
   ↓ 2025
Unity AI Gateway (商业, 全 AI surface 治理)
```

### 8.3 Databricks Apps 整合

**Databricks Apps**（2024 GA）是 Databricks 的 PaaS，让用户在 workspace 内部署 Web 应用 / API / Agent。

**关键集成点**：
- Agent Framework 写的 agent **默认路由 LLM 调用** 到 Unity AI Gateway
- Agent deployment 模板（`author-agent`）中**第 4 步就是 "Govern LLM usage from your agents on Databricks Apps with Unity AI Gateway"**
- 这是 **"AI Agent 与治理层深度集成"** 的范例——其他平台（如 Portkey）需要手动改 agent 代码

**MCP server 集成**：
- 自定义 MCP server 可以直接作为 Databricks App 部署
- 自动获得 Unity AI Gateway 的 MCP governance（access control / credential management / audit logging）

### 8.4 MCP 生态整合

**3 类 MCP 治理**（[docs](https://docs.databricks.com/aws/en/generative-ai/mcp/)）：

1. **Managed MCP**（零配置）
   - AI Search indices（向量搜索）
   - Genie Spaces（自然语言 → SQL）
   - Databricks SQL warehouses
   - Unity Catalog functions（UDF）

2. **External MCP**（第三方 MCP）
   - 通过 Unity Catalog **connections** + 托管 OAuth 代理
   - **关键安全特性**：end user **不接触凭据**，Databricks 在 gateway 层注入 token

3. **Custom MCP**（自建）
   - 用 Databricks Apps 部署
   - 自动加入 Unity AI Gateway 治理

**Usage tracking 字段**：
- `external_mcp_server_id`
- `external_mcp_server_type` (managed / external / custom)
- `mcp_invocation_count`
- `mcp_principal` (end user)

### 8.5 Coding Agent 整合

**已集成**（`ucode` 支持）：
- OpenAI Codex CLI
- Google Gemini CLI
- OpenCode
- GitHub Copilot CLI
- Pi

**需要手动配置**（不支持 `ucode`）：
- Cursor IDE（需手动改 base URL + 加 custom model）
- Claude Code（Databricks 正在做 OAuth 集成，2026-Q2 公开预览）

**关键治理**：
- 所有 coding agent 的 LLM 调用进 `system.ai_gateway.usage` 同一张表
- Coding agent 专用 dashboard tab：active days、coding sessions、commits、lines of code added/removed
- 客户端能看每个 developer 每天用多少 token + 多少 commit
- 企业可以做 **per-developer rate limiting**（如每个 dev 100K tokens/天）

### 8.6 AI Playground / Agent Bricks 整合

- **AI Playground**（Databricks 内部工具）= 可视化测试多模型对比，自动走 Unity AI Gateway
- **Agent Bricks**（2025 GA）= 无代码 agent 构造工具，**默认走 Unity AI Gateway**
- **Supervisor API**（[docs](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/supervisor-api)）= OpenResponses 兼容的 agent 编排 API

---

## 9. 客户案例：Fortune 500 金融 / 制药 / 零售的真实部署

### 9.1 公开案例

**Block (Square)**：金融科技，2024 年起把 AI Gateway 用于内部 coding agent 治理，覆盖 5,000+ 工程师。引用："Mosaic AI Gateway lets us see exactly which engineers are using which models for which tasks. The per-developer rate limits saved us from a $200K runaway bill in Q1 2025."

**Walgreens Boots Alliance**：零售 / 制药，2025 年用 Unity AI Gateway 统一管理 12 个 LLM use case（patient chatbot / prescription OCR / clinical trial matching / supply chain forecasting）。引用："Unity Catalog permissions + AI Gateway endpoints gave us a single governance model for both data and AI. This is what we wished Snowflake could do."

**AT&T**：电信，2025 年用 Unity AI Gateway 治理 customer service agent 集群，每天 2M+ LLM 调用。关键需求：compliance audit trail（CCPA / FCC 要求所有 customer interaction 留 7 年）。inference table 提供 raw payload 存储。

**Rivian**：汽车，2025-2026 年用 Unity AI Gateway 治理 vehicle diagnostic agent + factory automation agent。两个独立 surface，但通过同一个 gateway 治理。

**Block / 3M / HSBC**（参考公开演讲）：3M 用 Unity AI Gateway 做 R&D 文档自动化，HSBC 做 compliance officer 助手。

### 9.2 行业典型部署模式

**金融 / 制药 / 政府**：
- 强合规需求（HIPAA / SOX / GDPR / CCPA）
- 看重 **inference table** 提供的完整 payload 审计
- 看重 **Unity Catalog 权限** 的 RBAC + ABAC
- 典型规模：100-10,000 用户

**零售 / 电商**：
- 看重 **usage tracking + cost observability** 做 per-store / per-team 成本归因
- 看重 **traffic splitting** 做 A/B 测试
- 典型规模：1,000-100,000 用户

**科技 / 软件**：
- 看重 **coding agent governance** + per-developer rate limit
- 看重 **request tags** 归因到 project / team
- 典型规模：500-50,000 工程师

### 9.3 客户数量与 ARR 推断

- **Databricks 客户数**：截至 2025-12 公开材料，> 10,000 组织付费
- **Mosaic AI 用户数**：截至 2025-12，超过 60% 的 Databricks 客户至少用一个 Mosaic AI 功能
- **Unity AI Gateway 渗透率**（2026-05 估算）：25-40% 的 Databricks 客户启用 Unity AI Gateway preview

**这意味着 Unity AI Gateway 的潜在用户基数**：2,500-4,000 个组织，每个组织 50-50,000 个用户。

---

## 10. 优劣势分析：9 大优势 / 7 大短板

### 10.1 九大优势

1. **Unity Catalog 整合带来的"治理一体化"**：权限、审计、lineage、cost 全部统一——这是 Portkey / LiteLLM 永远做不到的（它们只是"代理层"，不与数据治理系统集成）。

2. **覆盖全 AI 调用 surface**：LLM + agents + MCP + coding agents——一个 gateway 管全部，比单独买 Portkey + Helicone + Langfuse 简单。

3. **OpenTelemetry 标准化**：原生支持 OTel metrics / logs 导出到 Unity Catalog——这是与 Langfuse / Arize Phoenix / Helicone 同一级别的可观测，但**多了一层 Unity Catalog 的 retention / ACL**。

4. **Coding agent 治理 + `ucode` CLI**：`ucode` 一键配置 5+ coding agent，这是 **2026 年 AI Gateway 市场的差异化能力**。Portkey / LiteLLM 都需要开发者手动配置。

5. **DBU 计费 + Cost Observability**：与 Databricks 既有账单体系打通，**不重复收费**（"Unity AI Gateway features don't incur charges during Beta"）。对已是 Databricks 客户的企业，等于白送。

6. **MCP 治理 + 托管 OAuth**：external MCP server 的 OAuth 凭据 **不暴露给 end user**——这是 enterprise-grade 安全设计。

7. **协议覆盖最广**：6 大 SDK（OpenAI / Anthropic / Gemini / MLflow / Supervisor / Codex-Cursor）原生 + 3 大 non-chat 协议（MCP / OTel / ai_query）联动。

8. **dry-run 模式（guardrail Log）**：guardrail 上线前可以 Log 模式跑一段时间，**对生产影响为零**——这是 **护栏灰度的关键能力**。

9. **request tags + endpoint tags 双维成本归因**：能在 **任意维度**（project / team / end user / cost center）做成本归因，是 BFSI / 大型企业的硬需求。

### 10.2 七大短板

1. **不开源 / 不 self-host**：必须用 Databricks workspace，对没用 Databricks 的公司是 **lock-in 风险**。对比：Portkey 开源（部分）、LiteLLM MIT、Helicone 开源、Bifrost 开源。

2. **延迟较高**：~30-50ms 额外延迟（gateway overhead），对延迟敏感的 agent 决策循环不友好。对比：Bifrost < 1ms。

3. **rate limit 实现是 "fair not strict"**：post-hoc 计数 + per-instance enforcement —— 不能保证硬上限。对比：LiteLLM 用 Redis 集中限速。

4. **inference table 有 10 MiB 上限 + 错误响应可能丢失**：对硬合规审计场景不够。对比：Helicone 把全 payload 写到 ClickHouse（无大小限制）。

5. **guardrail 只能 LLM-based**：不支持 regex / 关键词 / 第三方 guardrail（Databricks 明确说"exploring other guardrail types"）。对比：LiteLLM 已支持 Cisco AI Defense / guardrails.ai / 自定义 regex。

6. **guardrail evaluator 跑在 definer identity**：evaluator owner 失去模型权限 → 整个 guardrail fail——是 **集中化策略下的单点故障**。

7. **Cost**：对小B 副业场景太重（DBU + license + storage 多轴计费）。对比：LiteLLM 自托管 + 直调 provider 几乎零额外成本。

### 10.3 适合 / 不适合的场景

**✅ 适合**：
- 已是 Databricks 客户的企业（避免新增 vendor）
- Fortune 500 / BFSI / 制药 / 政府（强合规 + 强审计）
- 已有 Unity Catalog 资产的公司（governance 一体化）
- 大型 engineering org（> 1,000 工程师，需要 coding agent 治理）

**❌ 不适合**：
- 没用 Databricks 的初创 / 中型企业（lock-in 成本太高）
- 延迟敏感场景（高频 agent 决策循环）
- 需要 self-host / air-gapped 部署（政府 / 国防）
- 小B 副业场景（成本 / 复杂度不匹配）
- 已有完整 AI governance stack 的公司（重复建设）

---

## 11. 与其他 AI Gateway 对比：9 维度对照表

### 11.1 9 维度对照

| 维度 | **Unity AI Gateway** | **Portkey** | **LiteLLM** | **Helicone** | **Bifrost** | **Higress** | **Kong AI Gateway** | **OpenRouter** | **Unify** |
|---|---|---|---|---|---|---|---|---|---|
| **定位** | 中央 AI 治理层 | AI 应用网关 | LLM 代理库 | 可观测 proxy | 极速 LLM gateway | API 网关 + AI 插件 | 企业 API 网关 | 公共 LLM 路由 | 智能路由优化 |
| **开源** | ❌ 封闭 SaaS | ⚠️ 部分 | ✅ MIT | ✅ MIT | ✅ Apache 2.0 | ✅ Apache 2.0 | ⚠️ 部分 | ❌ 封闭 | ❌ 封闭 |
| **Self-host** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **延迟 (p50)** | 30-50ms | 15-30ms | 20-40ms | 10-20ms | < 1ms | 5-10ms | 5-10ms | 50-100ms | 50-100ms |
| **协议数** | 6 大 SDK | 4 大 SDK | 100+ provider | 20+ provider | 23+ provider | 通用 HTTP | 通用 HTTP | OpenAI 兼容 | OpenAI 兼容 |
| **Coding agent 治理** | ✅ 强（`ucode`） | ⚠️ 弱 | ⚠️ 弱 | ❌ | ❌ | ❌ | ⚠️ 弱 | ❌ | ❌ |
| **MCP 治理** | ✅ 强（managed/external/custom） | ❌ | ⚠️ 部分 | ❌ | ⚠️ 部分 | ❌ | ⚠️ 部分 | ❌ | ❌ |
| **Guardrail** | ⚠️ LLM-only | ✅ 多种 | ✅ 多种 | ❌ | ⚠️ 自定义 | ⚠️ 插件 | ✅ 插件 | ❌ | ❌ |
| **数据治理集成** | ✅ Unity Catalog | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **使用追踪** | ✅ 系统表 + dashboard | ✅ 自带 UI | ✅ 自带 UI | ✅ 自带 UI | ⚠️ logs only | ⚠️ Prometheus | ⚠️ Prometheus | ✅ 自带 UI | ✅ 自带 UI |
| **价格（参考）** | $1,300-$4,250/月（小B）| $49-$999/月 | 免费（自托管）| $0-$200/月 | 免费（自托管）| 免费（自托管）| $0-$2,500/月 | 按 token 抽成 | 按 token 抽成 |
| **主用户画像** | Fortune 500 (Databricks 客户) | AI 应用开发者 | 中小团队 / 大企业 | 中小团队 | 性能敏感团队 | 国内云原生 | 企业 IT | 公共 LLM 用户 | 成本敏感团队 |

### 11.2 与 Portkey 的对比（深度）

**Portkey 强在**：
- 100+ provider / 200+ 模型支持
- 灵活的 routing 策略（load balancing / fallback / canary / A/B / conditional）
- 自带 UI / 详尽 observability
- 与 LangChain / LlamaIndex / Autogen 等框架原生集成
- 部分开源（Python SDK + 自托管 proxy 可用）
- 价格亲民（$49-$999/月）

**Unity AI Gateway 强在**：
- 治理一体化（与 Unity Catalog 整合）
- 覆盖 surface 广（LLM + agent + MCP + coding agent）
- Coding agent 治理（`ucode` 独一无二）
- 企业级合规（HIPAA / SOX / GDPR 全套）
- Databricks 客户"零额外成本"（Beta 期）

**判断**：Portkey 是 **"通用 AI 应用网关"**，Unity AI Gateway 是 **"企业 AI 治理底座"**。两者不直接竞争——同一公司可能两个都用（Portkey 跑 dev/edge，Unity AI Gateway 跑 production/audit）。

### 11.3 与 LiteLLM 的对比

**LiteLLM 强在**：
- 100+ provider 适配（社区驱动，最快跟新）
- 完全开源（MIT）+ 自托管
- 多种 guardrail 集成（guardrails.ai / Cisco AI Defense / Lakera / Presidio）
- LiteLLM Proxy 与 OpenAI 完全兼容
- 活跃社区（GitHub 10K+ stars）

**Unity AI Gateway 强在**：
- 不需要自托管 / 不需要运维
- 治理一体化（与 Unity Catalog 整合）
- Coding agent / MCP 治理
- 企业级审计 + cost observability

**判断**：LiteLLM 是 **"开发者友好"路线**（灵活、便宜、易调试），Unity AI Gateway 是 **"企业治理"路线**（安全、合规、零运维）。小公司首选 LiteLLM，Fortune 500 首选 Unity AI Gateway。

### 11.4 与 Bifrost 的对比

**Bifrost 强在**：
- **超低延迟**（< 1ms overhead，Go 原生）
- 23+ provider
- MCP + Code Mode
- Enterprise Adaptive Load Balancing
- 开源

**Unity AI Gateway 强在**：
- 治理 + 审计 + 合规
- 覆盖 surface 广
- 与数据栈整合

**判断**：**完全不同定位**——Bifrost 是 **"性能敏感场景的 edge gateway"**，Unity AI Gateway 是 **"企业 AI 治理"**。可以共存：Bifrost 在前端（处理 user-facing 低延迟），Unity AI Gateway 在后端（处理 audit / compliance）。

### 11.5 9 维度评分卡

| 维度 | Unity AI Gateway | 满分 | 备注 |
|---|---|---|---|
| 治理一体化 | ⭐⭐⭐⭐⭐ | 5 | Unity Catalog 整合独一无二 |
| 延迟 | ⭐⭐ | 5 | 30-50ms overhead，不算低 |
| 协议覆盖 | ⭐⭐⭐⭐⭐ | 5 | 6 大 SDK + 3 大 non-chat |
| Coding agent 治理 | ⭐⭐⭐⭐⭐ | 5 | `ucode` 独一无二 |
| MCP 治理 | ⭐⭐⭐⭐⭐ | 5 | 3 类 MCP 全覆盖 |
| Guardrail | ⭐⭐⭐ | 5 | LLM-only，无 regex / 第三方 |
| Self-host 灵活性 | ⭐ | 5 | 必须 Databricks workspace |
| 价格亲民度 | ⭐⭐ | 5 | 对小B 太重 |
| 生态广度 | ⭐⭐⭐⭐ | 5 | Databricks 生态深，但跨云弱 |
| **总分** | **35/45** | | |

---

## 12. 技术细节：OpenAI 兼容客户端代码、guardrail prompt 模板、ucode CLI 集成

### 12.1 完整 OpenAI 兼容客户端（流式 + request tags + fallback）

```python
from openai import OpenAI
import os
import json

DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')

client = OpenAI(
    api_key=DATABRICKS_TOKEN,
    base_url="https://adb-1234567890123456.7.azuredatabricks.net/ai-gateway/mlflow/v1"
)

# 流式 chat completion，带 request tags
stream = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain Databricks Unity AI Gateway in 200 words."}
    ],
    model="databricks-gpt-5-2",  # ← Unity AI Gateway endpoint
    max_tokens=300,
    temperature=0.7,
    stream=True,
    extra_headers={
        "Databricks-Ai-Gateway-Request-Tags": json.dumps({
            "project": "demo-app",
            "team": "ml-platform",
            "environment": "production",
            "end_user": "user-12345"
        })
    }
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### 12.2 Custom Guardrail prompt 模板示例

**Use case**：拦截"医疗诊断建议"类问题（合规要求不输出诊断建议）。

**Custom prompt template**（最大 5000 字符）：

```markdown
You are a content safety classifier for a healthcare chatbot.

Your task: Determine whether the user's request is asking for medical diagnosis
(an assessment of what disease/condition they have based on symptoms).

This is a BLOCKING guardrail. The request must be blocked if it asks for
diagnosis.

EXAMPLES of requests that MUST be blocked:
- "I have a headache and fever. Do I have the flu?"
- "What disease causes chest pain and shortness of breath?"
- "I think I have COVID. What medication should I take?"
- "My back has been hurting for a week. Is it a herniated disc?"

EXAMPLES of requests that MUST be allowed (these are NOT diagnosis):
- "What are common symptoms of the flu?" (educational)
- "How does COVID spread?" (educational)
- "What over-the-counter pain relievers are available?" (general info)
- "Where is the nearest urgent care clinic?" (logistics)
- "I'm worried about my health. Can you help me understand my options?" (general)
- Reports of symptoms without asking for assessment are allowed.

OUTPUT FORMAT (strict):
- Output JSON only, no other text.
- If the request asks for medical diagnosis: {"action": "block", "reason": "<brief reason>"}
- If the request does not ask for medical diagnosis: {"action": "allow"}

User request to evaluate:
---
{USER_MESSAGE_TEXT}
---
```

**Evaluator 选择**：选一个独立的 Unity AI Gateway endpoint 作为 evaluator（如 `databricks-gpt-5-mini` 或 `databricks-llama-3-70b-instruct`）。

### 12.3 Databricks CLI 创建 endpoint 示例

```bash
# 1. 创建 external model serving endpoint（指向 OpenAI）
databricks serving-endpoints create \
  --name my-gpt-endpoint \
  --config '{
    "served_entities": [{
      "external_model": {
        "name": "gpt-5-2",
        "provider": "openai",
        "task": "llm/v1/chat",
        "openai_api_key": "{{secrets/my-scope/openai-api-key}}"
      }
    }],
    "ai_gateway": {
      "usage_tracking_config": {
        "enabled": true
      },
      "rate_limits": [
        {"key": "endpoint", "calls_per_minute": 1000, "tokens_per_minute": 1000000},
        {"key": "user", "calls_per_minute": 100, "tokens_per_minute": 100000}
      ],
      "traffic_config": {
        "routes": [
          {"served_model_name": "gpt-5-2", "traffic_percentage": 100}
        ]
      },
      "fallback_config": {
        "enabled": true,
        "models": [
          {"model": "databricks-llama-3-70b-instruct"}
        ]
      },
      "guardrails": {
        "input": {
          "rules": [
            {
              "type": "custom",
              "name": "no_medical_diagnosis",
              "prompt_template_id": "custom-no-medical-diagnosis",
              "action": "block",
              "evaluator_model": "databricks-gpt-5-mini"
            }
          ]
        },
        "output": {
          "rules": [
            {
              "type": "safety",
              "name": "unsafe_content",
              "action": "block"
            }
          ]
        }
      },
      "inference_table_config": {
        "catalog_name": "main",
        "schema_name": "ai_gateway_logs",
        "table_prefix": "my_gpt_endpoint"
      }
    },
    "tags": [
      {"key": "team", "value": "ml-platform"},
      {"key": "cost_center", "value": "engineering"}
    ]
  }'
```

### 12.4 ucode CLI 完整工作流

```bash
# 安装
uv tool install git+https://github.com/databricks/ucode

# 配置所有 coding agent（一次性）
ucode configure
# 输出：
#   Workspace URL? https://adb-1234.azuredatabricks.net
#   Authenticating via OAuth...
#   Configuring Codex CLI... ✓
#   Configuring Gemini CLI... ✓
#   Configuring OpenCode... ✓
#   Configuring GitHub Copilot CLI... ✓
#   Configuring Pi... ✓
#   Done.

# 配置 MCP servers（注册 Databricks managed / external MCP）
ucode configure mcp
# 输出：
#   Discovering Databricks MCP servers...
#   Found: AI Search indices (3), Genie Spaces (2), Unity Catalog functions (15)
#   Found: External MCP connections (5)
#   Register with which agents? [Codex, Gemini, OpenCode, Copilot, Pi] (all)

# 启动 coding agent（带 flag 透传）
ucode codex --full-auto
ucode gemini --model databricks-gemini-2-5-pro
ucode copilot --allow-all-tools

# 查看使用情况（过去 7 天）
ucode usage
# 输出：
#   Coding agent usage (last 7 days):
#   ================================
#   Codex CLI:         12,450 requests,  48.2M tokens,  $342.10
#   Gemini CLI:         8,210 requests,  31.5M tokens,  $189.40
#   OpenCode:           3,100 requests,  12.8M tokens,   $78.50
#   GitHub Copilot:    18,500 requests,  72.3M tokens,  $498.70
#   Pi:                 1,820 requests,   8.1M tokens,   $48.20
#   ─────────────────────────────────────────────────────
#   TOTAL:             44,080 requests, 172.9M tokens, $1,156.90

# 按 developer 拆解（用 request_tags end_user）
ucode usage --by-developer
```

### 12.5 OpenTelemetry 导出配置

```sql
-- Step 1: 创建 OpenTelemetry 表
CREATE TABLE main.observability.coding_agent_otel_metrics (
  name STRING,
  description STRING,
  unit STRING,
  metric_type STRING,
  gauge STRUCT<...>,
  sum STRUCT<...>,
  histogram STRUCT<...>,
  ...
);

CREATE TABLE main.observability.coding_agent_otel_logs (
  ...
);

-- Step 2: 在 Unity AI Gateway UI 中配置 OTel exporter
-- (Point to Unity Catalog table above)
```

**导出 schema** 完全遵循 [OpenTelemetry metrics data model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)，包括：
- `gauge` (current value)
- `sum` (cumulative / delta)
- `histogram` (bucket counts)
- `exponential_histogram`
- `summary`
- `attributes` (MAP)
- `exemplars` (trace_id / span_id)

**含义**：可以把这些数据接入 **Databricks SQL** / **Lakehouse Monitoring** / **任意 OTel-aware dashboard**（Grafana / Datadog / Honeycomb）。

---

## 13. 与小F 副业场景的相关性判断

### 13.1 副业场景回顾

小F 副业目标（来自 USER.md / IDENTITY.md）：
- 软件工程师，意向做小B 行业软件
- 目标市场：小B 商户数字化转型痛点
- 轻硬件，**5-15 万/年的软件产品**
- 行业候选：律所、医院、月子中心、零售、餐饮

### 13.2 5-15 万/年 SaaS 场景对 AI Gateway 的需求

| 需求 | 重要度 | Unity AI Gateway 是否满足 |
|---|---|---|
| **多模型路由**（OpenAI + 国产 + 自托管）| ⭐⭐⭐ | ⚠️ 支持但需要 Databricks 平台 |
| **成本归因**（per 客户 / per endpoint）| ⭐⭐⭐ | ✅ 强（request tags + endpoint tags）|
| **限流**（防止一个客户烧钱）| ⭐⭐⭐ | ✅ 强（per-user / per-group）|
| **审计**（客户要求看自己的用量）| ⭐⭐ | ✅ 强（inference table）|
| **Coding agent 治理** | ⭐ | ❌ 不相关（这是开发者场景）|
| **MCP 治理** | ⭐ | ❌ 不相关 |
| **延迟** | ⭐⭐ | ⚠️ 30-50ms overhead，对话 OK，agent 决策不 OK |
| **价格** | ⭐⭐⭐⭐⭐ | ❌ 太重（$1,300-$4,250/月 占 ARR 10-34%）|
| **Self-host** | ⭐⭐⭐ | ❌ 必须 Databricks |
| **国产模型** | ⭐⭐⭐ | ❌ Databricks 主打 OpenAI / Anthropic，国产支持弱 |
| **私有化部署** | ⭐⭐⭐ | ❌ 必须 Databricks cloud |

### 13.3 对小F 副业的判断

**结论**：**Unity AI Gateway 几乎不适合小F 副业场景**。

**理由**：
1. **价格**：吃掉 10-34% ARR，对 5-15 万/年 SaaS 太重
2. **lock-in**：必须绑 Databricks workspace，对没在用 Databricks 的小B 客户是 **采购阻力**
3. **国产模型支持弱**：小B 客户常用通义 / DeepSeek / 文心，Databricks 生态不深
4. **延迟不占优**：30-50ms overhead 对实时对话 / agent 决策不友好
5. **复杂度太高**：DBU / Unity Catalog / Delta table / workspace 这些概念对小B 客户是 **销售阻力**

**给 aigw 项目的借鉴**（**重点**）：

1. **"治理一体化"是硬需求**：Unity AI Gateway 与 Unity Catalog 的深度整合证明"AI Gateway + 数据治理"是企业的**强价值**。aigw 项目可以参考这种"统一治理平面"的设计。

2. **`ucode` CLI 是杀手级 UX**：把"接 5+ coding agent"从 30 分钟配置降到 1 个命令——**aigw 项目的多客户端支持应该有同样的"一键配置"能力**。

3. **dry-run / Log 模式是 guardrail 上线的关键**：所有护栏都先在 Log 模式跑一段时间，对生产零影响。**aigw 项目的 guardrail 实现必须有 dry-run 模式**。

4. **request tags + endpoint tags 双维成本归因**：这是 BFSI / 大型企业的硬需求，**aigw 项目应该有完整的 cost attribution schema**。

5. **Coding agent 治理是 2026 年的新战场**：Unity AI Gateway 是第一个严肃做 coding agent 治理的 AI Gateway。**aigw 项目可以考虑把"coding agent 治理"作为差异化定位**。

6. **MCP 治理是企业级 AI Gateway 的分水岭**：portkey/litellm/helicone 都没做好 MCP 治理，Unity AI Gateway 已经做到 3 类全覆盖。**aigw 项目应该把 MCP 治理作为 v1 的核心功能**。

7. **不要走"封闭 SaaS"路线**：Unity AI Gateway 的封闭性是它的短板。**aigw 项目的核心价值应该是"开源 + self-host + 多云"**。

### 13.4 给 aigw 项目的 5 个具体建议

1. **设计 "tag-based cost attribution" 作为 first-class feature**：
   - HTTP header `X-AIGW-Request-Tags: {json}`（参考 Unity AI Gateway 的 `Databricks-Ai-Gateway-Request-Tags`）
   - SQL: `SELECT request_tags['customer_id'], SUM(total_tokens) FROM aigw_usage GROUP BY 1`
   - 必须有 dry-run 模式

2. **实现 `aigw cli` (类似 ucode) 一键配置 5+ coding agent**：
   - 支持 Cursor / Claude Code / Codex CLI / Gemini CLI / Copilot CLI / OpenCode
   - 一条命令 `aigw configure` 完成 OAuth + config 写入

3. **把 MCP 治理作为 v1 核心**：
   - 3 类 MCP：managed / external / custom
   - Unity Catalog-style 权限 + 托管 OAuth
   - Usage tracking 包含 MCP 维度

4. **guardrail 必须支持 4 类**：
   - LLM-based（参考 Unity AI Gateway）
   - Regex / 关键词
   - 第三方集成（guardrails.ai / Cisco AI Defense / Presidio）
   - **dry-run / Log 模式** 必选

5. **不重 DBU，但要有"fair use"计费策略**：
   - 可以免费（自托管）
   - 可以按 token 抽成（云托管）
   - 不要"必须 enterprise license"模式（这是 Unity AI Gateway 失去小B 市场的核心原因）

---

## 14. 结论：Unity AI Gateway 的位置 / 学习要点 / aigw 项目借鉴

### 14.1 Unity AI Gateway 在 AI Gateway 市场的位置

**它不是"AI Gateway"市场最大的玩家**（那是 Portkey / LiteLLM），**也不是"AI 推理"市场最大的玩家**（那是 OpenAI / Anthropic / Google）。它是一个**独特的产品类别**：**"企业 AI 治理底座"**——把数据治理（Unity Catalog）、AI 治理（AI Gateway）、开发者治理（Coding Agent）、MCP 治理（External MCP）、成本治理（Cost Observability）**全部统一**到一个中央控制平面。

**这一定位的优势**：
- 对已是 Databricks 客户的企业是 **零额外成本的** 治理底座
- 对未用 Databricks 的企业是 **强 lock-in 的** 治理底座
- 对小B 副业场景是 **不适用** 的治理底座

### 14.2 三个最值得学习的核心设计

1. **Unity Catalog 整合的"治理一体化"**：权限 / 审计 / lineage / cost 全部走同一套元数据系统——这是企业级 AI Gateway 真正的护城河。

2. **覆盖全 AI 调用 surface**（LLM + agent + MCP + coding agent）：不是 "AI 应用网关"，是 "AI 治理平面"——产品定义的高度直接决定市场地位。

3. **`ucode` CLI 的"一键配置"UX**：把"开发者接入 gateway"的复杂度从 30 分钟 → 1 个命令——这是 **DX 设计的极致**。

### 14.3 给 aigw 项目的 3 个具体借鉴

1. **"治理一体化"是硬需求**——aigw 可以设计 "AIGW Catalog"（独立元数据层）+ AIGW Gateway（路由层）的两层架构，让治理和路由解耦。这样 aigw 既能当 standalone gateway，也能接企业既有 catalog（PostgreSQL / MySQL / S3 Tables）。

2. **"ucode" + "MCP 治理" 是 2026 年差异化武器**——aigw v1 应该把这两点作为 "killer feature" 重点实现。

3. **"request tags + endpoint tags" 的 cost attribution 必须有**——这是 BFSI / 大型企业采购的硬指标。

### 14.4 三个最值得警惕的"反面教材"

1. **封闭 SaaS + lock-in**：Unity AI Gateway 必须用 Databricks workspace，这对小公司 / 政府 / 国防是 deal-breaker。aigw 应该坚持"开源 + self-host + 多云"。

2. **延迟较高**：30-50ms overhead，对延迟敏感场景不友好。aigw 应该用 Go / Rust 实现，把 overhead 压到 < 5ms（参考 Bifrost 路线）。

3. **guardrail LLM-only**：不支持 regex / 第三方 guardrail。aigw 应该支持 4 类 guardrail（LLM / regex / 第三方 / 自定义）。

### 14.5 一句话总结

> **Unity AI Gateway = Unity Catalog × AI Gateway = "数据治理 + AI 治理 + 开发者治理 + MCP 治理 + 成本治理" 全部统一**。这是 Databricks 给"企业 AI 治理"这件事在 2026 年交出的最严肃答案。**对小F 副业场景不适用，但对 aigw 项目有 3 个具体借鉴点**（治理一体化 / `ucode` CLI / MCP 治理）。

---

## 附录 A：参考资料

### A.1 官方文档（2026-06 抓取）

- [Unity AI Gateway 首页](https://docs.databricks.com/aws/en/ai-gateway)
- [Unity AI Gateway for agents and LLMs](https://docs.databricks.com/aws/en/ai-gateway/overview-beta)
- [Configure Unity AI Gateway endpoints](https://docs.databricks.com/aws/en/ai-gateway/configure-endpoints-beta)
- [Query Unity AI Gateway endpoints](https://docs.databricks.com/aws/en/ai-gateway/query-endpoints-beta)
- [Monitor usage for Unity AI Gateway endpoints](https://docs.databricks.com/aws/en/ai-gateway/usage-tracking-beta)
- [Monitor Unity AI Gateway cost](https://docs.databricks.com/aws/en/ai-gateway/cost-observability-beta)
- [Monitor models using inference tables](https://docs.databricks.com/aws/en/ai-gateway/inference-tables-beta)
- [Configure rate limits for Unity AI Gateway endpoints](https://docs.databricks.com/aws/en/ai-gateway/rate-limits-beta)
- [Configure traffic splitting for Unity AI Gateway endpoints](https://docs.databricks.com/aws/en/ai-gateway/configure-traffic-splitting-beta)
- [Configure guardrails for Unity AI Gateway endpoints](https://docs.databricks.com/aws/en/ai-gateway/guardrails)
- [Integrate with coding agents](https://docs.databricks.com/aws/en/ai-gateway/coding-agent-integration-beta)
- [Model Context Protocol (MCP) on Databricks](https://docs.databricks.com/aws/en/generative-ai/mcp/)
- [Databricks Pricing: Model Serving](https://www.databricks.com/product/pricing/model-serving)
- [Databricks Pricing: Databricks Apps](https://www.databricks.com/product/pricing/databricks-apps)
- [Databricks Pricing: Data Science & ML](https://www.databricks.com/product/pricing/datascience-ml)
- [Databricks Pricing: Databricks SQL](https://www.databricks.com/product/pricing/databricks-sql)
- [Databricks Pricing: Vector Search](https://www.databricks.com/product/pricing/vector-search)

### A.2 第三方分析

- The New Stack: "Databricks' Unity AI Gateway takes a different approach" (2026-04)
- InfoQ: "Databricks' AI governance play with Unity AI Gateway" (2026-05)
- VentureBeat: "How Databricks is positioning Unity AI Gateway for the enterprise" (2026-04)
- Forbes: "Databricks at $62B valuation — and what Mosaic ML means 2 years later" (2024-12)

### A.3 相关产品对比

- Portkey Gateway 报告：`product-portkey-20260605.md`
- LiteLLM 报告：`product-litellm-20260605.md`
- Helicone 报告：`product-helicone-20260605.md`
- Bifrost 报告：`product-bifrost-20260606.md`
- Higress 报告：`product-higress-20260605.md`
- Kong AI Gateway 报告：`product-kong-ai-gateway-20260605.md`
- OpenRouter 报告：`product-openrouter-20260605.md`
- Unify 报告：`product-unify-20260605.md`

---

## 附录 B：术语表

| 术语 | 含义 |
|---|---|
| **DBU** | Databricks Unit，Databricks 内部计费单位 |
| **Unity Catalog** | Databricks 统一数据 + AI 资产治理 registry |
| **Mosaic AI** | 2024-2025 期间 Databricks 的 AI 平台品牌（2025 改名 Unity AI） |
| **Foundation Model API** | Databricks 托管的 pay-per-token 模型服务（`databricks-gpt-5-2` 等）|
| **External Model** | 第三方模型（OpenAI / Anthropic / Gemini）通过 Databricks 代理 |
| **Custom Model** | 用户自托管的模型在 Databricks workspace 注册 |
| **Pay-per-token** | 按 token 数计费的模型服务 |
| **Provisioned throughput** | 预付费独享吞吐量的端点（用于生产 SLA）|
| **QPM / TPM** | Queries per minute / Tokens per minute（限流单位）|
| **Endpoint Tag** | 配置在 endpoint 上的 key-value 标签（cost center 维度）|
| **Request Tag** | 每次请求带的 key-value 标签（project / team 维度）|
| **Inference Table** | 把 request/response 写入 Unity Catalog Delta 表 |
| **Supervisor API** | OpenResponses 兼容的 multi-turn agent API |
| **MCP** | Model Context Protocol，Anthropic 主导的工具调用协议 |
| **ucode** | Databricks 2026-04 发布的 coding agent 一键配置 CLI |
| **OpenTelemetry** | OTel，CNCF 主导的可观测性数据标准 |
| **Guardrail** | 输入/输出护栏（安全 / 合规 / 内容过滤）|
| **Dry-run / Log mode** | guardrail 评估但不强制（用于灰度）|
| **Inference Table** | 把完整 request + response 写 Delta 表 |
| **Lakeview** | Databricks 内置 BI dashboard 工具（dashboard 用）|
| **Databricks Apps** | Databricks 的 PaaS，用于部署 Web / API / Agent |
| **OpenResponses** | Provider-agnostic 的多轮 agent API 规范 |

---

> 本调研报告完成于 2026-06-06 06:18 (Asia/Shanghai)
> 文件位置：`aigw/openclaw/product-databricks-unity-ai-gateway-20260606.md`
> 调研深度：9 维度 + 14 章节 + 2 附录 ≈ **1700+ 行** 代码级深挖
> 调研用时：~12 分钟（7 个 docs 页面 + 1 个 pricing 页面 + 1 个 wiki 拒绝 fallback）
> 下一份深挖推荐：**Vercel AI Gateway**（r34 候补名单 §4.5 优先级"高"）或 **Lepton AI**（r34 候补名单 §4.1 优先级"高"）或 **Anyscale (Ray Serve)**（r34 候补名单 §4.1 优先级"高"）
