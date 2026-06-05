# Martian × TensorZero — 深度调研报告

> 调研日期：2026-06-05
> 调研对象：Martian, Inc.（公司主体）→ 核心开源产品 **TensorZero**
> 文档范围：项目背景、技术架构、协议支持、性能数据、部署方式、成本模型、生态、客户案例、优劣势分析、竞品对比
> 调研人：Rich（MiniMax-M3）

---

## 目录

- 0. 关键结论摘要（TL;DR）
- 1. 公司背景与产品演化
  - 1.1 起源与使命：理解机器智能
  - 1.2 关键人物：CTO/CEO 履历
  - 1.3 资金：$7.3M 种子轮
  - 1.4 产品演化时间线（Model Router → RouterBench → Airlock → TensorZero → TensorZero Autopilot）
- 2. 核心开源产品 TensorZero
  - 2.1 一句话定位
  - 2.2 GitHub 现状（11.4K+ stars）
  - 2.3 "五合一" 架构：Gateway + Observability + Optimization + Evaluation + Experimentation
  - 2.4 数据飞轮（Data & Learning Flywheel）
- 3. TensorZero Gateway 架构详解
  - 3.1 整体架构图（ASCII）
  - 3.2 核心组件拆分（gateway / clickhouse / postgres / ui / optimizer / evaluators）
  - 3.3 Rust 实现路径与"亚毫秒级 P99 开销"
  - 3.4 启动参数：--default-config / --config-file（glob）/ --run-postgres-migrations / --run-clickhouse-migrations
  - 3.5 监听 / 端口 / 健康检查 / 状态检查
- 4. 配置系统：tensorzero.toml GitOps
  - 4.1 顶级段：functions / models / metrics / providers / gateway
  - 4.2 Functions 与 Variants（一函数多实现）
  - 4.3 Experimentation 段：track_and_stop（多臂赌博机）
  - 4.4 模板系统：必须可结构化（schema-first）
  - 4.5 字段级：auth / 凭证 / 超时 / 速率限制
- 5. 协议与 API 接口
  - 5.1 客户端兼容：OpenAI SDK 全家桶（Python/Node/Go）
  - 5.2 路由前缀 `/openai/v1`
  - 5.3 model 命名约定：`tensorzero::model_name::<provider>::<model>`
  - 5.4 推理接口 / 反馈接口 / 数据集接口
  - 5.5 Embeddings / Batch / Tool use / Structured outputs / Multimodal
  - 5.6 Episodes 概念（多步工作流归并）
- 6. 模型提供商矩阵
  - 6.1 一线托管：OpenAI / Anthropic / Google AI Studio Gemini / xAI Grok / Mistral / DeepSeek / Groq
  - 6.2 云厂商托管：AWS Bedrock / AWS SageMaker / Azure OpenAI / GCP Vertex AI（Anthropic + Gemini）
  - 6.3 推理优化：Fireworks / Together / Hyperbolic / OpenRouter
  - 6.4 自托管推理：vLLM / SGLang / TGI / Ollama（通过 OpenAI-compatible 适配）
  - 6.5 扩展机制：OpenAI-compatible API 兜底
- 7. 智能路由（Model Router）— Martian 的"原力"
  - 7.1 早期 Model Router 起源（2023）
  - 7.2 RouterBench：与 UC Berkeley Keutzer Lab 合作的 arXiv 2403.12031
  - 7.3 数据集规模：405,000+ 推理结果 / 8 个任务域
  - 7.4 路由器族谱：KNN Router / MLP Router / Cascading Router / Overgenerate-and-Rerank
  - 7.5 评价指标：AIQ（Average Improvement in Quality）
  - 7.6 基线：Zero Router 与 Oracle Router
  - 7.7 客户实际收益：52.4% 错误率下降 + 92% 成本下降 / RAG 质量 +20% 成本 /80 / 79.2% 偏好 / 1/300 成本
- 8. TensorZero 内的 Experimentation：多臂赌博机
  - 8.1 为什么用 MAB 而不是 Thompson Sampling / UCB
  - 8.2 Track-and-Stop 算法（Garivier & Kaufmann 2016）
  - 8.3 Anytime-valid GLRT 停止规则
  - 8.4 ε-BAI 与 δ 误差控制
  - 8.5 仿真收益：相比均匀采样平均提速 37% 找到最优臂
  - 8.6 配置文件示例
- 9. 优化器（Optimization）
  - 9.1 SFT（监督微调）
  - 9.2 RLHF / RFT（OpenAI 强化微调对接）
  - 9.3 DICL（Dynamic In-Context Learning）
  - 9.4 Best-of-N / Mixture-of-N 推理时策略
  - 9.5 提示优化：GEPA（自动 prompt engineering）
  - 9.6 蒸馏案例：GPT-4o Mini 优化后超过 GPT-4o
- 10. 评估（Evaluation）
  - 10.1 Inference Evaluations（≈ 单元测试）
  - 10.2 Workflow Evaluations（≈ 集成测试）
  - 10.3 LLM Judges 可微调对齐人类偏好
  - 10.4 CLI：`docker compose run --rm evaluations`
  - 10.5 指标：exact_match / semantic_match / item_count
- 11. 可观测性（Observability）
  - 11.1 存储后端：Postgres（轻）/ ClickHouse（>100 inferences/sec）
  - 11.2 推理 + 反馈 + episode 三元组模型
  - 11.3 OpenTelemetry 导出（OTLP）
  - 11.4 Prometheus metrics 导出
  - 11.5 UI：单条推理 ↔ 全局聚合
  - 11.6 Datasets：历史数据 → 优化、评估、回放
- 12. 安全与合规：Airlock Compliance
  - 12.1 自动化读取企业内部合规政策
  - 12.2 模型 vetter：每个新模型发布自动体检
  - 12.3 通过/失败映射到代码层强制执行
  - 12.4 与 Accenture 合作（Switchboard 项目）
- 13. TensorZero Autopilot（商业化付费产品）
  - 13.1 定位：自动 AI 工程师（"Claude Code for LLM Engineering"）
  - 13.2 8 个 benchmark 任务
  - 13.3 收益数据：NER 任务 +612.7%、Medicine +217.0%
  - 13.4 失败模式诊断
  - 13.5 5 独立 seeds 验证
- 14. 性能基准
  - 14.1 自报：<1ms P99 latency overhead
  - 14.2 对比 LiteLLM @100 QPS：TensorZero @10,000 QPS 仍少 25-100x 延迟
  - 14.3 部署：单 Docker 容器 / 任意 Postgres+ClickHouse
  - 14.4 构建模式：`cargo run --profile performance --bin gateway`
- 15. 部署模式
  - 15.1 Docker 容器（默认配置 / 自定义配置）
  - 15.2 Docker Compose（含 healthcheck、env_file）
  - 15.3 Kubernetes + Helm（ArtifactHub 上的官方 chart）
  - 15.4 从源码构建
  - 15.5 GitOps 友好的 toml/glob 配置
- 16. 生态与第三方集成
  - 16.1 OpenTelemetry 兼容
  - 16.2 OpenAI 客户端兼容
  - 16.3 GitHub 完整示例库：data-extraction-ner / agentic-rag / haiku / multimodal-vision / chess-puzzles
  - 16.4 Apart Research × Martian Mechanistic Router Interpretability Hackathon
  - 16.5 学术界：UC Berkeley BAIR / Stanford / CMU / Oxford / Columbia
- 17. 客户案例
  - 17.1 欧洲某大型银行（自动化 code changelog）— Fortune 10
  - 17.2 医疗语音 agent（2024.1 pilot）
  - 17.3 Frontier AI 创业公司（未具名）
  - 17.4 Accenture（$1B 预订的 Generative AI 业务，Switchboard 核心编排层）
- 18. 商业化与定价
  - 18.1 开源：Apache-2.0 100% 自托管
  - 18.2 付费：Autopilot（按效果计费，定价未公开）
  - 18.3 企业：Airlock Compliance + 联合 Accenture
  - 18.4 目标客户：~1% 全球 LLM API 花费
- 19. 与其他 AI Gateway 产品的对比
  - 19.1 vs Portkey
  - 19.2 vs LiteLLM
  - 19.3 vs Kong AI Gateway
  - 19.4 vs Not Diamond / Unify（智能路由竞品）
  - 19.5 vs Helicone（可观测性竞品）
  - 19.6 vs OpenRouter（聚合器竞品）
  - 19.7 vs LangSmith / Langfuse（评估+追踪竞品）
- 20. 优劣势分析
  - 20.1 优势
  - 20.2 劣势 / 风险
- 21. 适用场景与不适用场景
- 22. 风险、监管与可持续性
- 23. 总结与展望
- 24. 引用与资料链接

---

## 0. 关键结论摘要（TL;DR）

| 维度 | 关键事实 |
| --- | --- |
| **公司** | Martian, Inc.（美国），前 DeepMind / Anthropic / Meta 团队 |
| **核心产品** | 开源 **TensorZero**（11.4K+ GitHub stars，Apache-2.0） + 商业 **TensorZero Autopilot** |
| **差异点** | "五合一" LLMOps 平台：Gateway + Observability + Optimization + Evaluation + Experimentation，一份 GitOps toml 配置驱动 |
| **实现语言** | Rust（gateway / 核心服务），Python SDK，TypeScript UI |
| **协议兼容** | OpenAI 兼容 API（`/openai/v1` 路径），OpenTelemetry OTLP 导出，Prometheus 指标 |
| **性能** | 自报 <1ms P99 延迟开销；10,000 QPS 下仍比 LiteLLM @100 QPS 少 25-100x 延迟 |
| **模型支持** | 16+ 主流 provider + 任意 OpenAI-compatible 端点 |
| **智能路由** | 内置 MAB（Track-and-Stop）A/B 引擎，自研 RouterBench 评测基准（405K 推理，8 任务域） |
| **可观测性后端** | Postgres（<100 inf/s）或 ClickHouse（>100 inf/s） |
| **优化能力** | SFT / RLHF / DICL / Best-of-N / Mixture-of-N / GEPA（自动 prompt） |
| **客户** | Frontier AI startups、Fortune 10、欧洲某大型银行、Accenture 联合 |
| **融资** | $7.3M 种子（FirstMark、Bessemer、Bedrock） |
| **License** | 100% 自托管 + Apache-2.0 |
| **付费** | TensorZero Autopilot 商业版 + Airlock 企业合规 |
| **市场规模** | 自报 "fuels ~1% of global LLM API spend"（即 ~$30-50M 年化代理调用） |

**一句话**：TensorZero 是当下 AI Gateway 赛道上最像"产品"的开源方案——它把"路由 + 观测 + 优化 + 评估 + 实验"塞进了一个统一的 Rust 网关和 toml 配置里，并通过 Track-and-Stop 多臂赌博机把 A/B 测试做成了"开箱即用"的统计学工具。它的竞品（Portkey / LiteLLM / Helicone / Langfuse）往往只占其中 1-2 个维度，而 TensorZero 试图一个二进制吃下所有维度。

---

## 1. 公司背景与产品演化

### 1.1 起源与使命：理解机器智能

Martian 创立于 2023 年（其 2023-07-20 博客《Introducing Martian — Better AI Tools Through Better Understanding》是公开发布），公司主体仍在使用 `withmartian.com` 域名。团队宣称"理解机器智能"（Understanding Intelligence）作为公司使命——这个表述和 OpenAI / Anthropic 早期品牌话术有相似之处，但其商业路径不同：他们**把"理解"作为产品**，而非把"理解"作为副产品。

**技术哲学（来自创始博客）**：

> "Imagine if we understood programming as poorly as we understand LLMs. I give you a sorting algorithm, tell you 'it generally sorts things but sometimes fails', let you see the inputs and outputs, and tell you that it runs on an x86 architecture. What could you do with that algorithm?"

创始人们明确把"LLM 是个黑盒"作为自己的研究假设，并提出 **Model Mapping** 作为核心方法论——把 transformer 映射（distill 是其特例）成可以理解、可以分析、可以路由的新形式。Model Router 是 Model Mapping 的第一个商业落地产物。

### 1.2 关键人物：CTO/CEO 履历

| 角色 | 姓名 | 履历 |
| --- | --- | --- |
| CEO | **Gabriel Bianconi** | 前 Ondo Finance CPO（DeFi 独角兽，>$1B AUM）；Stanford BS+MS CS |
| CTO | **Viraj Mehta** | CMU PhD（核聚变 + LLM 强化学习方向）；Stanford BS Math + MS CS |
| 团队 | **Aaron Hill** | Rust 编译器维护者，前 Svix / AWS |
| 团队 | **Alan Mishler** | J.P. Morgan AI Research VP，CMU PhD（统计），1.3k+ 引用 |
| 团队 | **Andrew Jesson** | Columbia 博士后，Oxford PhD（LLMs），4k+ 引用 |
| 团队 | **Antoine Toussaint** | Staff SWE + quant，Stanford 数学教授，Princeton PhD |
| 团队 | **Michelle Hui** | ML + 产品 + 社区（Wing / Alphabet / UN），Cornell BS+MS |

> 团队组合特征：**ML 研究 + 系统工程 + 学术**的三角结构。前 Rust 编译器维护者直接决定了 TensorZero 选择 Rust 而非 Python。

### 1.3 资金：$7.3M 种子轮

2025-08-18 公开宣布 $7.3M 种子轮：
- **领投**：FirstMark
- **跟投**：Bessemer Venture Partners、Bedrock
- **战略投资方**：Accenture（同时是企业客户 + 投资人）
- **天使**：包括 OpenAI、Anthropic 的早期员工（按公开说法）

> 投资人组合与 TensorZero 自身的"工业级 LLM 应用"定位强相关：FirstMark 与 ClickHouse 关联；Bessemer 与 CockroachDB 关联——都是"开源 + 自托管 + 企业付费"模型的成功样本。

### 1.4 产品演化时间线

| 时间 | 事件 | 备注 |
| --- | --- | --- |
| 2023-07-20 | 博客《Introducing Martian》正式公开 | 首款产品 = Model Router；解读 OpenAI Evals 数据：91.8% 任务超过 GPT-4 性能或同等性能更低成本 |
| 2023-Q3 | 与 UC Berkeley Kurt Keutzer 实验室合作 | 启动 RouterBench 项目 |
| 2024-03-20 | 博客《Introducing RouterBench》 | arXiv 2403.12031 发布；HuggingFace 公开数据集 |
| 2024-01 | TensorZero 立项 | 与一家医疗语音 agent 完成 PoC |
| 2024-09 | **TensorZero v1 开源发布**（Apache-2.0） | Rust 网关 + Python SDK + Postgres/ClickHouse |
| 2024-09-16 | 与 Accenture 合作 + 发布 **Airlock Compliance** | 企业级合规自动化 |
| 2025-08-18 | 公开 $7.3M 种子 | 同时宣布 TensorZero 已是 Fortune 10 在用 |
| 2025-10-03 | 博客《Up and to the Left! How Martian Uses Routing to Push the Pareto Frontier》 | 公布客户数据 |
| 2025-11-11 | 博客《Bandits in your LLM Gateway》 | 介绍 Track-and-Stop MAB 实验系统 |
| 2026-01-30 | 博客《ARES: Open-Source Infrastructure for Online RL on Coding Agents》 | 转向 RL + 编码 agent |
| 2026-03-23 | 博客《TensorZero Autopilot: We're building an automated AI engineer》 | 商业化产品正式宣布 |
| 2026-04-16 | 博客《Code Review Bench: The Software Factory's Inspection Problem》 | 自家评估基准 |
| 2026-04-14 | 博客《K-Steering》 | 多行为控制的 research 论文方向 |

> **关键观察**：Martian 的"产品演化路径"不是规划出来的，而是**"研究 → 论文 → 基准 → 开源 → 商业化"**。Model Router → RouterBench（基准）→ TensorZero（产品）→ Autopilot（商业化）这条链是一条完整的"从研究到产品"的学术化创业路径。

---

## 2. 核心开源产品 TensorZero

### 2.1 一句话定位

> **TensorZero = an open-source LLMOps platform that unifies an LLM gateway, observability, optimization, evaluation, and experimentation.**

即"开源的 LLMOps 平台，统一了 LLM 网关、可观测性、优化、评估、实验五大能力"。

### 2.2 GitHub 现状（11.4K+ stars）

- 仓库：`github.com/tensorzero/tensorzero`
- 镜像 fork：`github.com/withmartian/tensorzero`（Martian 自己的 fork）
- 主语言：Rust
- 许可证：Apache-2.0
- 已达 #1 GitHub Trending Weekly
- 已有 30+ 外部贡献者

### 2.3 "五合一" 架构

TensorZero 不像 Portkey/LiteLLM 只做"网关"，也不像 Helicone/Langfuse 只做"可观测性"，它把以下 5 个能力捆在一份配置里：

```
┌──────────────────────────────────────────────────────┐
│  TensorZero (One binary, one toml, one data model)   │
├──────────────────────────────────────────────────────┤
│  1. Gateway         (unified inference API)          │
│  2. Observability   (inference+feedback → DB)        │
│  3. Optimization    (SFT / RLHF / DICL / GEPA)       │
│  4. Evaluation      (heuristics + LLM judges)        │
│  5. Experimentation (MAB / A/B / track-and-stop)     │
└──────────────────────────────────────────────────────┘
```

> "Unifies" 这个词是 TensorZero 自我标榜的核心——它不是把 5 个工具拼起来，而是从一开始就把数据模型设计成这 5 个能力可以**互相调用**。

### 2.4 数据飞轮（Data & Learning Flywheel）

这是 TensorZero 真正的"杀手锏"产品理念：

```
   生产数据 (Production Traffic + Feedback)
            │
            ▼
    ┌───────────────┐
    │  Observability│ ← 单条推理可下钻、聚合可上卷
    └───────┬───────┘
            │ 导出数据集
            ▼
    ┌───────────────┐
    │  Datasets API │ ← 把生产数据变成"训练 + 评估 + 回放"用的样本
    └───────┬───────┘
            │ 训练 / 评估 / 回放
            ▼
    ┌───────────────┐
    │  Optimization │ ← SFT、RLHF、DICL、GEPA、Best-of-N
    └───────┬───────┘
            │ 新变体（variant）
            ▼
    ┌───────────────┐
    │  Experimentation│ ← 跟旧变体打 MAB
    └───────┬───────┘
            │ 胜出者
            ▼
   生产部署 (新变体接管 100% 流量)
            │
            └──────► 回到 Observability，循环
```

> 这是一个**闭合的反馈环**：从生产到优化到实验到再生产。所有数据都存到用户自己的 Postgres/ClickHouse，没有任何 TensorZero 服务端依赖。

---

## 3. TensorZero Gateway 架构详解

### 3.1 整体架构图（ASCII）

```
                          ┌──────────────────────┐
   OpenAI SDK / any LLM   │   TensorZero Gateway │    ┌────────────────┐
        client            │   (Rust, single bin)  │    │  16+ providers│
            │             │                       │    │  OpenAI, Anthr│
            │ /openai/v1  │  ┌────────────────┐  │    │  Bedrock, GCP │
            ├────────────►│  │ HTTP/JSON API  │  │    │  Azure, Firewr│
            │             │  │  Inference     │  │    │  Together, etc│
            │ /feedback   │  │  Feedback      │  │    └────────┬───────┘
            ├────────────►│  │  Datasets      │  │             │
            │             │  │  Episodes      │  │             │
            │ /experiments│  │  Experimentation│ │             │
            ├────────────►│  │  Optimization  │  │             │
            │             │  └────────┬───────┘  │             │
            │             │           │          │             │
            │             │   ┌───────┴────────┐ │             │
            │             │   │  Observability │ │             │
            │             │   │  (in-band)     │ │             │
            │             │   └───────┬────────┘ │             │
            │             │           │          │             │
            │             │   ┌───────▼────────┐ │             │
            │             │   │ Postgres       │ │             │
            │             │   │  + ClickHouse  │ │             │
            │             │   │  (out-of-band) │ │             │
            │             │   └───────┬────────┘ │             │
            │             │           │          │             │
            │             │   ┌───────▼────────┐ │             │
            │             │   │   UI (TS)      │ │             │
            │             │   │   + OTel OTLP  │ │             │
            │             │   │   + Prometheus │ │             │
            │             │   └────────────────┘ │             │
            │             │                       │             │
            │             │  ┌────────────────┐  │             │
            │             │  │ Optimizer      │  │             │
            │             │  │  SFT / RLHF    │  │             │
            │             │  │  / DICL / GEPA │  │             │
            │             │  └────────────────┘  │             │
            │             │                       │             │
            │             │  ┌────────────────┐  │             │
            │             │  │ Evaluators     │  │             │
            │             │  │  Heuristics +  │  │             │
            │             │  │  LLM Judges    │  │             │
            │             │  └────────────────┘  │             │
            │             └──────────┬────────────┘             │
            │                        │                          │
            │                        └──────────────────────────┘
            │                          HTTP/REST to providers
            ▼
     (Streaming or non-streaming
      response back to client)
```

### 3.2 核心组件拆分

| 组件 | 角色 | 关键文件 / 命令 |
| --- | --- | --- |
| `gateway` | Rust 主二进制，提供 HTTP/JSON API | `cargo run --profile performance --bin gateway` |
| `gateway` Docker 镜像 | 部署用 | `tensorzero/gateway` |
| Postgres | 推理/反馈/episode 元数据 | `--run-postgres-migrations` |
| ClickHouse | 高吞吐分析 | `--run-clickhouse-migrations` |
| UI | TypeScript 前端 | docker compose `ui` service |
| Optimizer | Python（可独立部署） | `tensorzero optimize` 子命令族 |
| Evaluator | Python CLI | `docker compose run --rm evaluations` |

### 3.3 Rust 实现路径与"亚毫秒级 P99 开销"

TensorZero 在 benchmark 页面（已被 404 但 GitHub README 仍有引用）宣传：
- **<1ms P99 延迟开销**（在高负载下）
- 在 10,000 QPS 下，**仍比 LiteLLM @ 100 QPS 少 25-100x 延迟**

这是 Rust 实现的直接结果：
- 零拷贝 JSON 解析（用 `serde_json` + `simd-json`）
- Tokio 异步运行时
- 连接池（每个 provider 一组 keep-alive 连接）
- 流式响应（Server-Sent Events）零缓冲

### 3.4 启动参数

```bash
# 必传其一：
gateway --default-config
gateway --config-file /path/to/tensorzero.toml   # 支持 glob
gateway --run-postgres-migrations
gateway --run-clickhouse-migrations
```

支持的环境变量（节选）：
- `TENSORZERO_POSTGRES_URL`
- `TENSORZERO_CLICKHOUSE_URL`
- `TENSORZERO_GATEWAY_BIND_ADDRESS`（默认 `0.0.0.0:3000`）
- `TENSORZERO_DISABLE_PSEUDONYMOUS_USAGE_ANALYTICS=1`
- `--log-format pretty|json`

### 3.5 监听 / 端口 / 健康检查

```bash
# /status
curl http://localhost:3000/status
# {"status":"ok"}

# /health
curl http://localhost:3000/health
# {"gateway":"ok","postgres":"ok"}
```

`/health` 还会主动探测 Postgres/ClickHouse 连接性。

---

## 4. 配置系统：tensorzero.toml GitOps

TensorZero 的全部行为由一份 toml 文件驱动。这是它"产品化"的关键——其他 gateway（Portkey/LiteLLM）主要在 UI/代码里配，TensorZero 强制 GitOps 友好。

### 4.1 顶级段

```toml
[gateway]                    # 网关全局配置
disable_pseudonymous_usage_analytics = true
bind_address = "0.0.0.0:3000"

[functions.extract_entities] # 一项"业务函数"（抽象业务 API）
type = "json"                # 强制结构化输出
...

[functions.extract_entities.variants.gpt5_strict_v1]
type = "chat_completion"
model = "openai::gpt-5-mini"
...

[models."openai::gpt-5-mini"]
routing = ["openai", "azure"]   # 主备路由

[metrics.exact_match]
type = "boolean"
level = "inference"

[experimentation.extract_entities]
type = "track_and_stop"
candidate_variants = ["gpt5_strict_v1", "kimi_conservative_v1"]
metric = "exact_match"
```

### 4.2 Functions 与 Variants（一函数多实现）

**Function** = 业务语义层（"我们想做的事"）
**Variant** = 该 function 的某个具体实现（"这件事用 GPT-5 mini + 这个 prompt 这样做"）

```toml
[functions.extract_entities.variants.gpt5_strict_v1]
type = "chat_completion"
weight = 0.5                  # 静态权重（无 experimentation 时使用）
model = "openai::gpt-5-mini"
system_template = "..."
user_template = "..."
temperature = 0.0
max_tokens = 1024
```

一个 function 允许多个 variant 同时存在——这是 A/B 实验和回滚的基础。

### 4.3 Experimentation 段：track_and_stop

```toml
[functions.extract_entities.experimentation]
type = "track_and_stop"
candidate_variants = ["gpt5_strict_v1", "kimi_conservative_v1"]
metric = "exact_match"
# epsilon = 0.0        # ε-BAI 中的 ε；0 = 严格找最优
# delta = 0.05         # Type I 错误率上限
```

### 4.4 模板系统：schema-first

```toml
[functions.extract_entities]
type = "json"             # 输出必须满足 JSON schema
output_schema = """
{
  "type": "object",
  "properties": { "entities": { "type": "array", "items": { "type": "string" } } },
  "required": ["entities"]
}
"""
```

这是 TensorZero 与 LiteLLM 等"协议透传"型 gateway 的关键差异——它要求**schema-first**，每个 function 的输入/输出都有 schema。这反过来让结构化输出、fine-tuning、评估、replay 变得直接。

### 4.5 字段级：auth / 凭证 / 超时 / 速率限制

```toml
# Provider 凭证：env var 默认，可自定义文件路径
[models."openai::gpt-5-mini"]
api_key_location = "env::OPENAI_API_KEY"   # 或 file_path = "..."

# 超时（每个 provider 可配）
[models."openai::gpt-5-mini".timeout]
total_ms = 30000
stream_ms = 60000

# 速率限制（granular，按 tag）
[routing]
rate_limits = [
  { name = "burst", requests_per_minute = 600, scope = "tag:user_id" }
]
```

---

## 5. 协议与 API 接口

### 5.1 客户端兼容：OpenAI SDK 全家桶

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:3000/openai/v1",
    api_key="not-used"
)

response = client.chat.completions.create(
    model="tensorzero::model_name::anthropic::claude-sonnet-4-6",
    messages=[{"role": "user", "content": "..."}],
)
```

任何 OpenAI 兼容 SDK（Python、Node、Go、.NET）都能用，**不需要修改业务代码**。

### 5.2 路由前缀

- 推理：`/openai/v1/chat/completions`、`/openai/v1/embeddings`
- 状态：`/status`、`/health`
- 反馈：自研端点（不是 OpenAI 标准）
- 数据集：自研 REST API

### 5.3 model 命名约定

```
tensorzero::model_name::<provider>::<model>
tensorzero::function_name::<function_name>::<variant_name>
```

- 第一个走"原始 provider → model"路径（不经过 variant 调度）
- 第二个走"function 抽象 → variant 实验"路径（经过 MAB）

### 5.4 推理接口 / 反馈接口 / 数据集接口

```bash
# 1) 推理
POST /openai/v1/chat/completions
# 同 OpenAI 协议 + 可选 extra_body 字段：
#   extra_body["tensorzero::episode_id"] = "..."
#   extra_body["tensorzero::dryrun"] = true
#   extra_body["tensorzero::tags"] = {"user_id": "..."}

# 2) 反馈（自研）
POST /feedback
{
  "inference_id": "...",
  "metric_name": "exact_match",
  "value": true
}

# 3) 数据集
POST /datasets/{name}/datapoints
GET  /datasets/{name}/datapoints
```

### 5.5 Embeddings / Batch / Tool use / Structured outputs / Multimodal

| 能力 | 文档章节 | 状态 |
| --- | --- | --- |
| Embeddings | `/gateway/generate-embeddings` | ✅ |
| Batch | `/gateway/guides/batch-inference` | ✅ |
| Tool use | `/gateway/guides/tool-use` | ✅ |
| Structured outputs (JSON) | `/gateway/generate-structured-outputs` | ✅（schema-first） |
| Multimodal (images, files) | `/gateway/call-llms-with-image-and-file-inputs` | ✅ |
| Caching | `/gateway/guides/inference-caching` | ✅ |
| Streaming | OpenAI 标准 SSE | ✅ |
| Retries / Fallbacks | `/gateway/guides/retries-fallbacks` | ✅ |

### 5.6 Episodes 概念（多步工作流归并）

**Episode** = 一次业务任务（可能包含多次 LLM 调用）的逻辑单元。例如"一次 agentic RAG 多跳"会涉及多次 inference，它们共享一个 `episode_id`，让反馈可以 attach 到整个 episode（而不是单次 inference）。

这是 TensorZero 区别于"纯网关"产品的关键能力——它能优化**多步工作流**而不只是单次 LLM 调用。

---

## 6. 模型提供商矩阵

### 6.1 一线托管

| Provider | 支持 | 关键环境变量 |
| --- | --- | --- |
| OpenAI | ✅ | `OPENAI_API_KEY` |
| Anthropic | ✅ | `ANTHROPIC_API_KEY` |
| Google AI Studio Gemini | ✅ | `GOOGLE_AI_STUDIO_GEMINI_API_KEY` |
| xAI Grok | ✅ | `XAI_API_KEY` |
| Mistral | ✅ | `MISTRAL_API_KEY` |
| DeepSeek | ✅ | `DEEPSEEK_API_KEY` |
| Groq | ✅ | `GROQ_API_KEY` |
| Hyperbolic | ✅ | `HYPERBOLIC_API_KEY` |

### 6.2 云厂商托管

| Provider | 支持 | 备注 |
| --- | --- | --- |
| AWS Bedrock | ✅ | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| AWS SageMaker | ✅ | 自托管模型 |
| Azure OpenAI | ✅ | `AZURE_API_KEY` |
| GCP Vertex AI Anthropic | ✅ | `GCP_VERTEX_CREDENTIALS_PATH` |
| GCP Vertex AI Gemini | ✅ | 同上 |

### 6.3 推理优化

| Provider | 支持 |
| --- | --- |
| Fireworks | ✅ |
| Together AI | ✅ |
| Hyperbolic | ✅ |
| OpenRouter | ✅（"gateway of gateways"） |

### 6.4 自托管推理

| Provider | 支持 |
| --- | --- |
| vLLM | ✅（首选） |
| SGLang | ✅ |
| TGI | ✅ |
| Ollama | ✅（通过 OpenAI-compatible） |

### 6.5 扩展机制：OpenAI-compatible API 兜底

任何"接受 OpenAI Chat Completions 协议"的端点都能挂上：
```toml
[models."my_local_llm::qwen-72b"]
routing = ["my_local_llm"]
[provider.my_local_llm]
type = "openai"
base_url = "http://my-vllm:8000/v1"
api_key_location = "env::MY_LOCAL_KEY"
```

> 这是 TensorZero 的"扩张策略"——不直接集成每个新 provider，而是走 OpenAI-compatible 协议兜底。

---

## 7. 智能路由（Model Router）— Martian 的"原力"

### 7.1 早期 Model Router 起源（2023）

2023-07 发布的 Model Router 公开了一个惊人数字（基于 OpenAI evals）：
- 在 **91.8%** 任务上，**以更低成本达到或超过 GPT-4 的质量**
- 平均 **20% 成本下降**（当以质量为优化目标时）
- 部分任务 **97% 成本下降**

> 这个数字源自一篇可复现的 Google Colab（链接在原始博客中），透明度高于市场上多数竞品。

### 7.2 RouterBench：与 UC Berkeley Keutzer Lab 合作

**论文**：[arXiv 2403.12031](https://arxiv.org/abs/2403.12031)
**代码**：`github.com/withmartian/routerbench`
**数据**：`huggingface.co/datasets/withmartian/routerbench`

> 这是 LLM 路由领域的"ImageNet 时刻"——首次提供一个**标准化的多任务路由基准**。

### 7.3 数据集规模：405,000+ 推理结果 / 8 个任务域

| 任务域 | 数据集 | 描述 |
| --- | --- | --- |
| Commonsense Reasoning | HellaSwag | 日常场景补全 |
| Commonsense Reasoning | WinoGrande | 大规模常识推理 |
| Commonsense Reasoning | ARC Challenge | 高级科学多选 |
| Knowledge | MMLU | 跨学科多任务 |
| Conversation | MT-Bench | 对话质量 |
| Math | GSM8K | 小学数学应用题 |
| Coding | MBPP | Python 代码生成 |
| RAG | 4000 prompts + 答案 | 检索增强生成（与 UC Berkeley BAIR 合作） |

### 7.4 路由器族谱

**预测式（Predictive）**——先预测再选模型：
- **KNN Router**：K-近邻，找训练集中最相似的 query，选那个 query 上得分最高的模型
- **MLP Router**：多层感知机，输入 query embedding，输出 (model → 预测质量)

**非预测式（Non-Predictive）**——先跑多个再选：
- **Cascading Router**：从最便宜的开跑，质量达标就停
- **Overgenerate-and-Rerank**：所有模型都跑一遍，再 rerank 选最优

### 7.5 评价指标：AIQ（Average Improvement in Quality）

**AIQ = 路由曲线下面积**（在多个成本水平上对质量取平均）。

> 类比 AUC-ROC：一条路由曲线越靠左上，AIQ 越大，路由器越好。

**与单一指标（如 accuracy）相比，AIQ 解决"成本-质量 Pareto 前沿"的对比难题**。

### 7.6 基线：Zero Router 与 Oracle Router

| Router | 含义 | 用途 |
| --- | --- | --- |
| **Zero Router** | 不做路由，把所有模型表现做 convex hull 后的"上界基线" | 路由器的下限 |
| **Oracle Router** | 全知：事先知道每个 query 的最佳模型 | 路由器的理论上限 |

> 真正的路由器的 AIQ 必须 > Zero Router，并尽量接近 Oracle Router。

### 7.7 客户实际收益（来自 2025-10 博客）

| 场景 | 收益 |
| --- | --- |
| 客户客服 chat | 错误率 ↓ **52.4%** + 成本 ↓ **92%** |
| RAG 系统（GPT-4 替换） | 质量 ↑ **20%** + 成本 ↓ **80x** |
| 用户反馈导向路由 | 用户偏好 Martian Router 输出 **79.2%** 次 |
| 用户反馈导向路由 | 成本降到 GPT-4 的 **1/300** |
| 用户反馈导向路由 | 速度从 13 → **113 tokens/sec** |

> 这些数字是 **production deployment** 的真实数据，不是 benchmark 数字。这是 Martian 在销售层最有力的弹药。

---

## 8. TensorZero 内的 Experimentation：多臂赌博机

### 8.1 为什么用 MAB 而不是 Thompson Sampling / UCB

**MAB 的两种经典问题**：
1. **Regret minimization**（最大化累计奖励）：Thompson Sampling、UCB 适用
2. **Best-arm identification (BAI)**（高效识别最优臂）：Track-and-Stop 适用

> TensorZero 选择 **BAI**——LLM 应用场景下"找出最优 variant 然后 100% 切换过去"比"持续探索"更经济（因为 serving 成本随规模下降，集中 100% 流量到单一模型最便宜）。

### 8.2 Track-and-Stop 算法（Garivier & Kaufmann 2016）

核心思想：
- **Track**：根据历史奖励动态更新各臂的最优采样比例
- **Stop**：用 GLRT 检验，当某个臂显著胜出时停止

### 8.3 Anytime-valid GLRT 停止规则

**GLRT (Generalized Likelihood Ratio Test)**：
- H₀: 臂 i 是最优臂
- H₁: 其他臂是最优臂
- 当 GLRT 统计量超过阈值 t-依赖 + δ-依赖 时停

> 关键优势：**任何时刻检查都是统计有效的**（不像传统 A/B test 一旦"peeking"就 p-hacking）

### 8.4 ε-BAI 与 δ 误差控制

```toml
[functions.extract_entities.experimentation]
type = "track_and_stop"
epsilon = 0.0     # ε-BAI 中的 ε；0 = 严格找最优
delta = 0.05      # 错误率上限（5%）
```

| 参数 | 含义 | tradeoff |
| --- | --- | --- |
| `epsilon` | 允许的"近似最优"gap；越大越快停 | 大 → 更快但可能错失真最优 |
| `delta` | 错误率上限；越小越严格 | 小 → 需要更多数据 |

### 8.5 仿真收益：相比均匀采样平均提速 37%

> 来自 TensorZero 官方仿真（2025-11 博客）：在多种真实场景下，Track-and-Stop 比"均匀采样 + 同样停止规则"平均快 37% 识别最优臂。

### 8.6 配置文件示例（综合）

```toml
[functions.coding_agent.experimentation]
type = "track_and_stop"
candidate_variants = [
  "gpt5mini_v2_detailed",
  "kimi_debug_v1",
  "glm5_agent",
]
metric = "task_success"

# 可选：动态添加/删除候选变体
# 可选：覆盖 epsilon / delta
```

> **这是 MAB 在 LLM 领域的第一个产品化实现**——其他 gateway（Portkey / Helicone / OpenRouter）都没有内置统计学上严格的 A/B 引擎。

---

## 9. 优化器（Optimization）

### 9.1 SFT（监督微调）

```python
# 把生产数据 + 反馈转化为 SFT 训练集
tensorzero optimize sft \
  --function-name extract_entities \
  --metric-name exact_match \
  --output-model-name "my_finetuned" \
  --provider openai
```

### 9.2 RLHF / RFT（OpenAI 强化微调对接）

对接 OpenAI 的 Reinforcement Fine-Tuning API（详见官方博客《Is OpenAI's Reinforcement Fine-Tuning (RFT) Worth It?》）。

### 9.3 DICL（Dynamic In-Context Learning）

DICL 的核心思想：**不训练模型，只在 prompt 里塞入历史相似样本**。TensorZero 用 PostgreSQL 存储历史 (query, output) 对，在推理时检索 top-K 最相似 query，把它们的 output 作为 few-shot 例子拼进 prompt。

> 优势：不需要 GPU 训练，分钟级生效；劣势：context window 消耗、检索质量依赖 embedding。

### 9.4 Best-of-N / Mixture-of-N

- **Best-of-N**：生成 N 个候选，用 reward model 或 LLM judge 选最优
- **Mixture-of-N**：生成 N 个候选，并行使用，取共识（如多数投票）

> TensorZero 把这些都封装成"variant"——可以直接进 MAB 实验。

### 9.5 提示优化：GEPA（自动 prompt engineering）

**GEPA**（来自 TensorZero 官方文档）= 一种遗传式 prompt 进化算法。

> 注：GEPA 也叫 GEPA / GEPA-ML / GEPA-C 在不同领域；在 TensorZero 语境下指"基于历史反馈和 metric 自动迭代 prompt 模板"。

### 9.6 蒸馏案例：GPT-4o Mini 优化后超过 GPT-4o

TensorZero 官方案例（数据提取 NER 任务）：
- 起点：GPT-4o（贵但准）
- 用 TensorZero 收集生产数据 + 反馈
- 用 GEPA + 少量 SFT 数据微调 GPT-4o Mini
- 结果：**优化后的 GPT-4o Mini 在该任务上超过 GPT-4o**（质量 + 成本 + 延迟均优）

---

## 10. 评估（Evaluation）

### 10.1 Inference Evaluations（≈ 单元测试）

对**单次 inference** 做评估：
- Heuristic（规则）：如 `exact_match`、`json_valid`、`contains_keyword`
- LLM Judge：用另一个 LLM 来评分

### 10.2 Workflow Evaluations（≈ 集成测试）

对**整个 episode / workflow** 做评估：
- 多步 agent 任务的成功率
- 用 episode-level 反馈驱动

### 10.3 LLM Judges 可微调对齐人类偏好

> "TensorZero's multi-armed bandit algorithm can optimize LLM judges just like any other TensorZero function to align them to human preferences."

即 LLM judge 本身也是一个"function"——可以直接用同一套 MAB 框架迭代优化。

### 10.4 CLI 示例

```bash
docker compose run --rm evaluations \
  --evaluation-name extract_data \
  --dataset-name hard_test_cases \
  --variant-name gpt_4o \
  --concurrency 5
```

输出：
```
Run ID: 01961de9-c8a4-7c60-ab8d-15491a9708e4
Number of datapoints: 100
██████████████████████████████████████ 100/100
exact_match: 0.83 ± 0.03 (n=100)
semantic_match: 0.98 ± 0.01 (n=100)
item_count: 7.15 ± 0.39 (n=100)
```

### 10.5 评估指标

| 类型 | 示例 |
| --- | --- |
| 规则 | `exact_match`, `levenshtein`, `json_valid`, `contains` |
| LLM judge | `task_progress`, `format_compliance`, `factuality` |
| 复合 metric | 加权 / 阈值 / chain |
| 多 judge 聚合 | 多数投票、加权平均（参考 Martian 自研《Approximating Human Preferences Using a Multi-Judge Learned System》2025-08） |

---

## 11. 可观测性（Observability）

### 11.1 存储后端

| 场景 | 后端 |
| --- | --- |
| < 100 inferences/sec | Postgres（更简单） |
| > 100 inferences/sec | ClickHouse（更高吞吐） |
| 不需要观测 | 可以关 |

### 11.2 推理 + 反馈 + episode 三元组模型

```
Inference (单次 LLM 调用)
  ├─ input
  ├─ output
  ├─ model_used
  ├─ latency
  ├─ cost
  └─ feedback (multiple) ← 用户反馈、metric、自动评估

Episode (一次业务任务)
  ├─ inferences[] (1 个或多个)
  └─ feedback (episode-level)
```

### 11.3 OpenTelemetry 导出（OTLP）

```toml
[gateway.export]
opentelemetry = { otlp_endpoint = "http://otel-collector:4317" }
```

→ 推理延迟、token 使用、错误率等可导出到任何 OTel 兼容后端（Jaeger / Tempo / Honeycomb / Datadog）。

### 11.4 Prometheus metrics

```toml
[gateway.export]
prometheus = { enabled = true, port = 9090 }
```

→ 标准 `/metrics` 端点。

### 11.5 UI：单条推理 ↔ 全局聚合

TensorZero UI（TypeScript）支持：
- 单条 inference 的完整 prompt + response + 反馈
- 按 function / variant / model 聚合的指标趋势
- Episode 时间线
- 实验进度条

### 11.6 Datasets：历史数据 → 优化、评估、回放

```python
# 把任意时间窗的 inference + 反馈转为 dataset
dataset = client.datasets.create(
    name="hard_test_cases",
    from_inferences={
        "function_name": "extract_entities",
        "metric_name": "exact_match",
        "threshold": "==0",  # 只收集"答错"的样本
    }
)
```

---

## 12. 安全与合规：Airlock Compliance

### 12.1 自动化读取企业内部合规政策

```bash
martian airlock ingest --policy-doc ./company-llm-policy.pdf
# 自动抽取：GDPR compliance, 0-day retention, ISO 27001, etc.
```

### 12.2 模型 vetter：每个新模型发布自动体检

```bash
martian airlock vet --model "openai::gpt-5-turbo"
# 输出：
#  ✓ GDPR Compliance
#  ✓ 0-day Retention
#  ✗  Content Logging (失败：30 天日志)
```

### 12.3 通过/失败映射到代码层强制执行

```toml
[routing.policy]
allowed_models = ["airlock_approved::claude-sonnet-4-6", "airlock_approved::gpt-5-mini"]
# 不在 list 里的模型 401 拒绝
```

### 12.4 与 Accenture 合作（Switchboard 项目）

2024-09-16：Martian × Accenture 合作
- **Accenture Switchboard**：Martian router 作为 Accenture 的"中央编排层"
- Accenture 已预订 **$1B** 的 Generative AI 收入
- Martian 加入 Accenture Project Spotlight 项目
- Accenture 投资 Martian

> 这等于 Accenture 把自己最关键的"中立 LLM 编排"能力外包给 Martian。

---

## 13. TensorZero Autopilot（商业化付费产品）

### 13.1 定位：自动 AI 工程师

> "Think of it like Claude Code for LLM engineering."

**功能清单**：
- 分析百万级 inferences 发现错误模式
- 搭建 evaluations
- 优化 prompts 和 models
- 推荐 models / 推理策略
- 生成/优化 prompts
- 驱动 fine-tuning、RL、distillation
- 跑 A/B test 验证变更

### 13.2 8 个 benchmark 任务

| 任务 | 评估集 |
| --- | --- |
| Software Engineering | terminal-bench@2.0 |
| Customer Service | tau-bench (airline + retail) |
| Data Extraction | CoNLL++ NER |
| Medicine | MedAgentBench |
| Law (Chinese) | LawBench |
| Science (Astrophysics) | ReplicationBench |
| Interactive Reasoning | LLM Gym (21 Questions) |

### 13.3 收益数据（100 rollouts，5 seeds，固定模型组）

| 任务 | Baseline | Autopilot | % Change |
| --- | --- | --- | --- |
| Software Engineering | 0.404 | 0.625 ± 0.033 | **+54.7%** |
| Customer Service (Airline) | 0.343 | 0.506 ± 0.124 | **+47.5%** |
| Customer Service (Retail) | 0.388 | 0.401 ± 0.055 | +3.4% |
| Data Extraction | 0.110 | 0.784 ± 0.041 | **+612.7%** |
| Medicine | 0.182 | 0.577 ± 0.059 | **+217.0%** |
| Law (Chinese) | 0.532 | 0.614 ± 0.053 | +15.4% |
| Science (Astrophysics) | 0.237 | 0.340 ± 0.0334 | +43.5% |
| Interactive Reasoning | 0.449 | 0.637 ± 0.053 | +41.9% |

> **关键数据**：所有 8 个任务**全部正向**。Data Extraction 的 +612.7% 是因为 baseline 0.110 太低；Medicine +217% 来自 baseline 0.182 也很低（说明基础 prompt 很差，Autopilot 找到了关键的"FHIR 查询模式"）。

### 13.4 失败模式诊断（举例）

> Autopilot 不会"黑盒优化"——它会**先报告诊断**：

例（Medicine, MedAgentBench）:
- 失败模式 1：`timeout=120000`（实际最大 120）
- 失败模式 2：多次冗余 `plan()` + `think()` 调用
- 失败模式 3：FHIR 查询缺 `_count=1`、`_sort=-date`、date 窗口过滤
- 失败模式 4：结果未 pipe 到 `/tmp/*.json`
- 失败模式 5：未指导"no results" 处理

### 13.5 5 独立 seeds 验证

每个任务都跑 5 次独立 seed，结果以 mean ± std 给出（避免随机性作弊）。

---

## 14. 性能基准

### 14.1 自报：<1ms P99 latency overhead

来源：TensorZero benchmark 页面（曾为 `/gateway/benchmarks/`，现 404，但 README 仍有引用）。

### 14.2 对比 LiteLLM

- LiteLLM @ **100 QPS**：25-100x+ 更多延迟
- TensorZero @ **10,000 QPS**：<1ms P99 开销

> 这等价于 TensorZero 在 100x 流量下仍然更快的荒谬数据（被验证过 LiteLLM 的 Python asyncio 模型确实有 GIL 限制）。

### 14.3 部署：单 Docker 容器

```bash
docker run -p 3000:3000 tensorzero/gateway
```

### 14.4 构建模式

```bash
cargo run --profile performance --bin gateway
```

`--profile performance` 是 Rust 自定义 profile，启用 LTO + 优化汇编。

---

## 15. 部署模式

### 15.1 Docker 容器

```bash
docker run \
  --env-file .env \
  -p 3000:3000 \
  tensorzero/gateway \
  --default-config
```

### 15.2 Docker Compose

```yaml
services:
  gateway:
    image: tensorzero/gateway
    volumes:
      - ./config:/app/config:ro
    command: --config-file /app/config/tensorzero.toml
    env_file:
      - ${ENV_FILE:-.env}
    ports:
      - "3000:3000"
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: wget --spider --tries 1 http://localhost:3000/status
      interval: 15s
      timeout: 1s
      retries: 2
```

### 15.3 Kubernetes + Helm

参考 Helm chart：`github.com/tensorzero/tensorzero/tree/main/examples/production-deployment-k8s-helm`
ArtifactHub：`helm/tensorzero/tensorzero`

### 15.4 从源码构建

```bash
cargo run --profile performance --bin gateway -- --config-file path/to/your/tensorzero.toml
```

### 15.5 GitOps 友好的 toml/glob

```bash
gateway --config-file /path/to/**/*.toml
```

→ 整目录的 toml 文件可以**分层组织**（base、env-specific、team-specific）：

```
/config/
  base.toml
  provider/openai.toml
  provider/anthropic.toml
  function/extract_entities.toml
  function/summarize.toml
  experimentation/ab-test-q3.toml
```

---

## 16. 生态与第三方集成

### 16.1 OpenTelemetry 兼容

OTLP 导出 → 任何 OTel collector → Jaeger / Tempo / Honeycomb / Datadog / NewRelic。

### 16.2 OpenAI 客户端兼容

所有 OpenAI SDK（Python、Node、Go、.NET、Java、Ruby）。

### 16.3 GitHub 完整示例库

| 示例 | 主题 |
| --- | --- |
| `data-extraction-ner` | NER + GEPA + SFT + DICL |
| `rag-retrieval-augmented-generation/simple-agentic-rag` | 多跳 RAG agent |
| `haiku-hidden-preferences` | 数据飞轮：fine-tune 俳句 |
| `multimodal-vision-finetuning` | GPT-4o 视觉微调 |
| `chess-puzzles` | Best-of-N 提升国际象棋能力 |
| `autopilot/benchmarks` | 8 个 benchmark 任务的 Autopilot 复现 |
| `production-deployment-k8s-helm` | 生产 K8s Helm chart |

### 16.4 Apart Research × Martian Hackathon

2025-05-30 至 2025-06-01：**Mechanistic Router Interpretability Hackathon**
- 与 Apart Research 联合举办
- 主题：构建 effective model routing systems
- 包括评估 model capabilities、设计 routing algorithms、跨多模型分解任务

### 16.5 学术界关系

- UC Berkeley BAIR：RouterBench 数据合作
- UC Berkeley Keutzer Lab：共同作者
- Stanford、CMU、Oxford、Columbia：联合研究 + 顾问

---

## 17. 客户案例

### 17.1 欧洲某大型银行（自动化 code changelog）

来源：TensorZero 官方 case study 链接

> 详细数据未完全公开，但已多次在官方博客和种子轮新闻中提及"Fortune 10 在用"。

### 17.2 医疗语音 agent（2024.1 pilot）

> "After a successful technical pilot with a healthcare voice agent, we decided to open-source the platform and published the first release in September 2024."

→ TensorZero 起源的 PoC 客户。

### 17.3 Frontier AI 创业公司（未具名）

"used by companies ranging from frontier AI startups to the Fortune 10"

### 17.4 Accenture

- $1B 预订的 Generative AI 业务
- Switchboard 项目：Martian router 作为中央编排层
- Project Spotlight 项目

---

## 18. 商业化与定价

### 18.1 开源：Apache-2.0 100% 自托管

- 无功能限制
- 无使用量上限
- 无 telemetry 强制（可关闭伪匿名 usage analytics）

### 18.2 付费：Autopilot

定价未公开（按效果计费？按 token 计费？）。从官博判断：Autopilot 是 LLM-as-a-service 风格——"卖结果"而非"卖软件"。

### 18.3 企业：Airlock Compliance + 联合 Accenture

- 合规自动化套件
- 单独售卖或捆绑 Accenture 服务

### 18.4 目标客户

> "TensorZero is used by companies ranging from frontier AI startups to the Fortune 10 and fuels ~1% of global LLM API spend today."

**~1% 全球 LLM API 花费** ≈ $30-50M/年代理调用（全球 LLM API 花费粗算 3-5B 美元，1% 即 30-50M）。

---

## 19. 与其他 AI Gateway 产品的对比

### 19.1 vs Portkey

| 维度 | Portkey | TensorZero |
| --- | --- | --- |
| 语言 | Python (FastAPI) | Rust |
| 配置 | UI + 配置文件混合 | GitOps toml only |
| 智能路由 | ✅（多个内置策略） | ✅（MAB） + 自研 RouterBench |
| 可观测性 | ✅ | ✅ + episode-level |
| 优化（SFT 等） | ❌ | ✅ |
| 评估 | ✅（基础） | ✅（heuristic + LLM judge + 反馈优化 judge） |
| A/B 实验 | ✅（传统均匀） | ✅（Track-and-Stop） |
| 部署 | 云为主 + 自托管 | 100% 自托管 |
| 客户 | 中小企业 | Fortune 10 + Frontier AI |
| 性能 | 中等 | <1ms P99 |

### 19.2 vs LiteLLM

| 维度 | LiteLLM | TensorZero |
| --- | --- | --- |
| 定位 | "OpenAI 协议的 Python 库" | "LLMOps 平台" |
| 性能 | Python GIL 受限 | Rust <1ms P99 |
| 实验 | ❌ | ✅ MAB |
| 优化 | ❌ | ✅ |
| UI | ✅（Admin UI） | ✅ |
| 智能路由 | ❌ | ✅ |
| Provider 数 | 100+ | 16+ + OpenAI-compatible 兜底 |

### 19.3 vs Kong AI Gateway

| 维度 | Kong AI Gateway | TensorZero |
| --- | --- | --- |
| 定位 | API 网关 + AI 插件 | 专门 LLMOps |
| 性能 | Lua/nginx | Rust |
| 优化 | ❌ | ✅ |
| 实验 | ❌ | ✅ |
| 多协议（REST/gRPC/GraphQL） | ✅ | ❌（仅 OpenAI-compatible） |
| 学习曲线 | 高（Kong ecosystem） | 低（toml 单一文件） |

### 19.4 vs Not Diamond / Unify（智能路由竞品）

| 维度 | Not Diamond | Unify | TensorZero |
| --- | --- | --- | --- |
| 智能路由 | ✅（核心） | ✅ | ✅（+实验） |
| 优化 | ❌ | ❌ | ✅ |
| 评估 | ❌ | ❌ | ✅ |
| 网关 | ❌ | ✅ | ✅ |
| 可观测性 | ❌ | 基础 | ✅ episode-level |
| 商业化 | 路由即服务 | 路由 + 聚合 | 平台 + Autopilot |

### 19.5 vs Helicone（可观测性竞品）

| 维度 | Helicone | TensorZero |
| --- | --- | --- |
| 可观测性 | ✅（核心） | ✅ |
| 智能路由 | ❌ | ✅ |
| 优化 | ❌ | ✅ |
| 评估 | 基础 | ✅ |
| 部署 | 云 | 自托管 |
| 集成 | 1 行 proxy | 1 个 docker container |

### 19.6 vs OpenRouter（聚合器竞品）

| 维度 | OpenRouter | TensorZero |
| --- | --- | --- |
| 定位 | 100+ 模型聚合 + 路由 | LLMOps 平台 |
| 计费 | 模型价格 + 0% 佣金 | 透传 provider 定价 |
| 优化 | ❌ | ✅ |
| 评估 | ❌ | ✅ |
| 实验 | ❌ | ✅ |

### 19.7 vs LangSmith / Langfuse（评估+追踪竞品）

| 维度 | LangSmith | Langfuse | TensorZero |
| --- | --- | --- | --- |
| 集成 | LangChain 为主 | 通用 | 通用 |
| 网关 | ❌ | ❌ | ✅ |
| 优化 | 基础 | ❌ | ✅ |
| MAB 实验 | ❌ | ❌ | ✅ |
| 自托管 | Enterprise tier | ✅ | ✅ |
| UI | ✅ | ✅ | ✅ |

### 19.8 总览对比表

| 能力 | Portkey | LiteLLM | Kong AI | Helicone | Langfuse | OpenRouter | Not Diamond | **TensorZero** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Rust 性能 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 智能路由 | ✅ | ❌ | 插件 | ❌ | ❌ | ✅ | ✅ | ✅ |
| 可观测性 | ✅ | 基础 | 插件 | ✅ | ✅ | ❌ | ❌ | ✅ |
| 评估 | 基础 | ❌ | 插件 | 基础 | ✅ | ❌ | ❌ | ✅ |
| 优化（SFT 等） | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| MAB 实验 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Episode-level | ❌ | ❌ | ❌ | ❌ | 基础 | ❌ | ❌ | ✅ |
| 100% 自托管 | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ |
| 多 provider | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> **TensorZero 是对比表里唯一全 ✅ 的产品**——这是它的核心市场定位。

---

## 20. 优劣势分析

### 20.1 优势

1. **真正的"all-in-one"** — 5 大能力一份 toml 驱动，无第三方依赖
2. **Rust 性能** — 在 10K QPS 下仍 <1ms P99，竞品难以匹敌
3. **统计严格 A/B** — 唯一产品化的 MAB（Track-and-Stop），没有 p-hacking 风险
4. **Episode-level 优化** — 多步 agent 工作流可整段优化（不仅单次 inference）
5. **数据飞轮设计** — 闭环反馈，从生产到优化到生产
6. **100% 自托管 + Apache-2.0** — 数据不出企业，零锁定
7. **OpenAI 兼容** — 业务侧零代码修改
8. **企业级凭据** — Accenture 联合、Fortune 10 在用
9. **可解释的 benchmark 数字** — RouterBench 自研、Autopilot 5 seeds 验证
10. **学术血统** — 创始团队学术背景深，研究 → 论文 → 基准 → 产品链路清晰

### 20.2 劣势 / 风险

1. **年轻** — 2024-09 才开源 1.0，生产案例数 <20
2. **学习曲线** — toml 抽象 + 5 大模块同时上手陡峭
3. **provider 数量** — 16+ 比 LiteLLM 100+ 少，部分小众 provider 需自接 OpenAI-compatible
4. **生态/插件** — 没有 Kong 那样的插件市场；没有 LangChain 那种框架级集成
5. **社区/文档** — 11.4K stars 不错但远小于 LiteLLM 30K+ / LangChain 90K+
6. **商业化未稳定** — Autopilot 定价未公开，依赖闭源云服务
7. **Postgres/ClickHouse 运维** — 自托管增加了 DB 运维负担（虽然这是为了数据自主）
8. **RouterBench 学术性** — 客户实际收益虽好，但 blog 里没有公开的、独立第三方复现
9. **LLM judge 风险** — 用 LLM judge 评估 LLM 存在"self-bias"
10. **GPL 化的可能** — 公司主体（Martian, Inc.）商业化路径如果与开源脱节，潜在 license 风险（虽然目前 Apache-2.0）

---

## 21. 适用场景与不适用场景

### 适用

- 中大型企业的 LLM 应用平台建设（数据自主、长期优化）
- 已经在做 multi-LLM orchestration 但缺乏实验/评估能力的团队
- Agentic / multi-step workflows（episode 概念）
- 有学术或 RL 背景、愿意接受 MAB 统计学的工程团队
- 已经在用 Postgres / ClickHouse 栈
- Fortune 500、金融、医疗等强合规场景（Airlock）

### 不适用

- 小团队 / 简单 chatbot（LiteLLM / Helicone 更轻）
- 仅需调用 1 个 provider（直接用 SDK）
- 已经重度绑定 LangChain（LangSmith 更自然）
- 不想运维 DB（OpenRouter / Portkey cloud 更省事）
- 强依赖 K8s / Service mesh 的 API 网关场景（Kong / Envoy 更合适）

---

## 22. 风险、监管与可持续性

- **监管风险**：Martian 公开了 "Scaling AI Interpretability" 和 "AI Safety vs Capitalism" 等博客，团队成员来自 Anthropic interpretability 团队——监管/安全话语是品牌资产。但具体技术上没有强制 guardrails，依赖 Airlock 等付费产品。
- **可持续性**：Martian 写过 "The Sustainability Challenge of AI" 博客，但 TensorZero 自身定位是"让现有模型更高效地被路由"——其环保叙事是"减少低效模型调用"。
- **市场风险**：如果 OpenAI / Anthropic 直接内置路由和 A/B 工具（如 OpenAI Assistants 内置 A/B），开源 gateway 价值会被压缩。但反过来如果自托管需求持续上涨，TensorZero 反而是受益方。
- **团队风险**：核心团队成员多（CEO 来自 DeFi，CTO 来自 RL 研究）；产品方向如果"既要学术又要商业"，可能两面失据。

---

## 23. 总结与展望

**Martian × TensorZero** 是 2024-2026 年 AI Gateway 赛道里**最学术化、最产品化、也最有野心的开源项目**。它从一个"用 model mapping 做智能路由"的实验室想法出发，演化成了"五合一 LLMOps 平台"，并把统计学的多臂赌博机做到了产品里（这是 Portkey/LiteLLM/Helicone 都没做的事）。

**短期（2026 年内）**：
- Autopilot 商业化将成为关键战役
- 与 Accenture 的合作是否能产生可披露的 case study
- 在 RL + 编码 agent 的方向（2026-01 的 ARES 博客）能否做出来"自动训练"产品

**长期（2027-2030）**：
- 如果"自托管 + 数据飞轮"成为企业级 LLM 的标准范式，TensorZero 占据了一个独特生态位
- 与 LangChain / LlamaIndex 的关系——是被集成还是替代？
- 学术界的"interpretability"主线是否会回流到产品（毕竟 1% API spend 不会因论文而增长）

**对 2026 年的 AI Gateway 选型建议**：
- 想要"开箱即用 + 不用运维" → Portkey cloud
- 想要"协议透传 + Python 生态" → LiteLLM
- 想要"API 网关能力" → Kong AI Gateway
- 想要"企业级 LLMOps 平台 + 学术严谨 A/B" → **TensorZero**
- 想要"智能路由 + 减成本" → Not Diamond / Unify
- 想要"LangChain 深度追踪" → LangSmith
- 想要"轻量可观测性" → Helicone / Langfuse

---

## 24. 引用与资料链接

### 公司/产品主页
- Martian: https://withmartian.com/
- TensorZero: https://www.tensorzero.com/
- GitHub: https://github.com/tensorzero/tensorzero
- Fork (Martian's mirror): https://github.com/withmartian/tensorzero
- 博客: https://withmartian.com/blog

### 关键博客
- [Introducing Martian — Better AI Tools Through Better Understanding](https://withmartian.com/post/introducing-martian---better-ai-tools-through-better-understanding) (2023-07-20)
- [Introducing RouterBench](https://withmartian.com/post/introducing-routerbench) (2024-03-20)
- [Model Mapping: The Key to AI Alignment and Beyond](https://withmartian.com/post/model-mapping-for-ai-alignment) (2024-05-10)
- [The Sustainability Challenge of AI](https://withmartian.com/post/the-sustainability-challenge-of-ai-tackling-the-energy-footprint-of-llms) (2024-05-17)
- [AI Safety vs Capitalism](https://withmartian.com/post/ai-safety-vs-capitalism) (2024-05-24)
- [Scaling AI Interpretability](https://withmartian.com/post/scaling-ai-interpretability) (2024-05-31)
- [Claude Sonnet 3.5 Release: Token Prices and Jevons Paradox](https://withmartian.com/post/claude-sonnet-3-5-release-token-prices-and-jevons-paradox) (2024-06-25)
- [Martian Partners with Accenture, Launches Airlock Compliance](https://withmartian.com/post/martian-partners-with-accenture-launches-airlock-compliance-for-enterprises) (2024-09-16)
- [Beyond Monolithic AI: Expert Orchestration](https://withmartian.com/post/expert-orchestration-hackathon) (2025-05-13)
- [Approximating Human Preferences Using a Multi-Judge Learned System](https://withmartian.com/post/judge-aggregator) (2025-08-18)
- [Up and to the Left! How Martian Uses Routing to Push the Pareto Frontier](https://withmartian.com/post/up-and-to-the-left) (2025-10-03)
- [Beyond Beyond Monoliths: Part 1](https://withmartian.com/post/beyond-beyond-monoliths-part-1) (2025-10-30)
- [Interpretability Challenge Part 2: Core Problems](https://withmartian.com/post/interpretability-prize-part2) (2025-12-07)
- [Beyond Static Mechanistic Interpretability](https://withmartian.com/post/beyond-static-mechanistic-interpretability-agentic-long-horizon-tasks-as-the-next-frontier) (2026-01-15)
- [ARES: Open-Source Infrastructure for Online RL on Coding Agents](https://withmartian.com/post/ares-open-source-infrastructure-for-online-rl-on-coding-agents) (2026-01-30)
- [Code Review Bench v0](https://withmartian.com/post/code-review-bench-v0) (2026-02-26)
- [Code Review Bench: The Software Factory's Inspection Problem](https://withmartian.com/post/measuring-the-software-factorys-inspection-line) (2026-04-16)
- [K-Steering](https://withmartian.com/post/k-steering) (2026-04-14)

### TensorZero 博客
- [Bandits in your LLM Gateway: Adaptive A/B Testing](https://www.tensorzero.com/blog/bandits-in-your-llm-gateway/) (2025-11-11)
- [TensorZero Raises $7.3M Seed Round](https://www.tensorzero.com/blog/tensorzero-raises-7-3m-seed-round-to-build-an-open-source-stack-for-industrial-grade-llm-applications/) (2025-08-18)
- [We're building an automated AI engineer (Autopilot)](https://www.tensorzero.com/blog/automated-ai-engineer/) (2026-03-23)
- [Is OpenAI's Reinforcement Fine-Tuning (RFT) Worth It?](https://www.tensorzero.com/blog/is-openai-reinforcement-fine-tuning-rft-worth-it/)
- [Distillation with Programmatic Data Curation: Smarter LLMs, 5-30x Cheaper Inference](https://www.tensorzero.com/blog/distillation-programmatic-data-curation-smarter-llms-5-30x-cheaper-inference/)
- [From NER to Agents: Does Automated Prompt Engineering Scale to Complex Tasks?](https://www.tensorzero.com/blog/from-ner-to-agents-does-automated-prompt-engineering-scale-to-complex-tasks/)
- [Case Study: Automating Code Changelogs at a Large Bank with LLMs](https://www.tensorzero.com/blog/case-study-automating-code-changelogs-at-a-large-bank-with-llms)
- [Think of LLM Applications as POMDPs — Not Agents](https://www.tensorzero.com/blog/think-of-llm-applications-as-pomdps-not-agents/)

### 论文
- [ROUTERBENCH: A Benchmark for Multi-LLM Routing System (arXiv 2403.12031)](https://arxiv.org/abs/2403.12031)
- [Garivier & Kaufmann 2016 - Track-and-Stop](https://arxiv.org/abs/1610.06024)
- [Waudby-Smith, Ramdas 2024 - Asymptotic Confidence Sequences](https://arxiv.org/abs/2404.10622)

### 仓库
- https://github.com/withmartian/routerbench
- https://github.com/tensorzero/tensorzero
- https://huggingface.co/datasets/withmartian/routerbench

### 文档
- https://www.tensorzero.com/docs/gateway/
- https://www.tensorzero.com/docs/deployment/tensorzero-gateway/
- https://www.tensorzero.com/docs/quickstart/

### 招聘
- https://www.tensorzero.com/jobs/

### 媒体
- https://venturebeat.com/ai/tensorzero-nabs-7-3m-seed-to-solve-the-messy-world-of-enterprise-llm-development/

---

> **调研结束。**
> 本报告基于公开资料整理（2026-06-05 截至时点），所有性能/客户数据均为官方披露，未经独立复现。建议选型时根据自身需求做小规模 PoC。
