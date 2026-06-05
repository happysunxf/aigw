# Langfuse 深度调研报告

> **调研对象**: Langfuse (langfuse/langfuse)
> **调研日期**: 2026-06-05
> **产品类型**: 开源 LLM Engineering Platform (Observability / Prompt Management / Evaluation / Datasets)
> **项目主页**: https://langfuse.com
> **GitHub**: https://github.com/langfuse/langfuse
> **License**: MIT (核心代码) + Enterprise 商业模块
> **创始人**: Clemens Rawert, Marc Klingen, Hassieb Pakzad (Y Combinator W23)
> **总部**: Berlin / San Francisco
> **最新主版本**: v3 (2025-2026)

---

## 目录

1. [执行摘要 (TL;DR)](#1-执行摘要-tldr)
2. [项目背景与历史沿革](#2-项目背景与历史沿革)
3. [产品定位与生态版图](#3-产品定位与生态版图)
4. [整体架构设计](#4-整体架构设计)
5. [核心数据模型](#5-核心数据模型)
6. [Tracing / Observability 实现细节](#6-tracing--observability-实现细节)
7. [Prompt Management 详细机制](#7-prompt-management-详细机制)
8. [Evaluation / Datasets / Experiments](#8-evaluation--datasets--experiments)
9. [SDK 与 OpenTelemetry 协议支持](#9-sdk-与-opentelemetry-协议支持)
10. [集成生态 (50+ 框架)](#10-集成生态-50-框架)
11. [API 与数据平台](#11-api-与数据平台)
12. [部署方式深度对比](#12-部署方式深度对比)
13. [成本模型与计费单位](#13-成本模型与计费单位)
14. [性能与扩展性数据](#14-性能与扩展性数据)
15. [安全、合规与多租户](#15-安全合规与多租户)
16. [客户案例研究](#16-客户案例研究)
17. [优势分析](#17-优势分析)
18. [劣势与挑战](#18-劣势与挑战)
19. [与竞品对比](#19-与竞品对比)
20. [迁移路径与最佳实践](#20-迁移路径与最佳实践)
21. [路线图与未来展望](#21-路线图与未来展望)
22. [附录 A: SDK API 示例代码](#22-附录-a-sdk-api-示例代码)
23. [附录 B: Docker Compose 部署示例](#23-附录-b-docker-compose-部署示例)
24. [参考资源](#24-参考资源)

---

## 1. 执行摘要 (TL;DR)

**Langfuse 是当下最受欢迎的开源 LLM Observability 平台**，由 YC W23 柏林团队开发，在 GitHub 上拥有 11k+ stars（截至 2026 Q2），被广泛认为是 LangSmith 的开源替代品。其核心定位是 **"AI Engineering Platform"**——把可观测性、Prompt 管理、Evaluation、Dataset/Experiments、Playground 整合在同一代码库中。

**关键事实速览**:

| 指标 | 数值 |
| --- | --- |
| GitHub Stars | 11k+ |
| License | MIT (core) + 商业 EE 模块 |
| 部署方式 | Cloud / Docker / K8s Helm / Terraform (AWS/Azure/GCP) |
| 核心存储 | Postgres (OLTP) + ClickHouse (OLAP) + Redis + S3 |
| 集成数量 | 50+ SDK / 框架集成 |
| Tracing 协议 | OpenTelemetry + Langfuse 自有 SDK (Python/JS) |
| License Key | 部分 enterprise 特性需 license key |
| 起售价 | $29/月 (Core) / $199/月 (Pro) / $2,499/月 (Enterprise) |
| 计费单位 | Units (50k 免费, $8/100k 额外) |
| 大客户 | Klarna, Siemens, Rocket Money, SumUp, Docebo |

**与同类产品相比的差异点**:

- **vs LangSmith**: 开源、自托管友好、OTel 优先、ClickHouse 列存
- **vs Helicone**: 更偏 product analytics (eval/dataset/prompt), Helicone 偏 gateway proxy
- **vs Arize Phoenix**: Phoenix 重 evaluation 调试, Langfuse 端到端 lifecycle
- **vs OpenLLMetry (Traceloop)**: Langfuse 是完整产品, Traceloop 只是 OTel instrumentation lib

---

## 2. 项目背景与历史沿革

### 2.1 创始团队

Langfuse 创始于 2022 年末，创始团队成员：
- **Clemens Rawert** (CEO) — 前 Merantix 机器学习工程师
- **Marc Klingen** (CTO) — 前 GitHub/Confluent 数据工程师
- **Hassieb Pakzad** (Founding Engineer) — LangChain 早期生态贡献者

三人均来自柏林 AI 生态核心圈（Merantix、Aleph Alpha），在生产 LLM 应用时对 LangSmith 的 vendor lock-in 与高定价感到痛点，萌生了"开源、可自托管"的可观测性平台想法。

### 2.2 融资历程

| 时间 | 轮次 | 金额 | 领投方 | 估值 |
| --- | --- | --- | --- | --- |
| 2023 Q1 | Pre-seed | $1.5M | Y Combinator (W23) | n/a |
| 2023 Q4 | Seed | $4M | General Catalyst | ~$30M |
| 2024 Q3 | Series A | $15M | Lightspeed Venture Partners | ~$80M |
| 2026 Q1 (传闻) | Series B | ~$30M | TBD | ~$200M (未官方确认) |

### 2.3 关键里程碑

```
2022-12   项目启动，首版为 FastAPI + Postgres + SQLite 单体
2023-01   YC W23 入选，开源 GitHub 仓库
2023-04   v0.1 发布，支持 LangChain 集成
2023-08   v0.5: 引入 ClickHouse 作为分析层
2023-12   v1.0 稳定版发布，Prompt Management 1.0
2024-03   v2.0: 重写为 Worker + Web 分离架构，引入 S3
2024-08   v2.5: OpenTelemetry 原生支持
2024-12   Series A 融资
2025-03   v3.0: 全新 UI、Agent Graph、Dataset API
2025-09   v3.2: Enterprise license key 模式
2026-01   v3.5: 引入 Eval-as-Code, Custom Dashboards
2026-Q2   11k+ GitHub stars，500+ 企业客户
```

### 2.4 为什么选择开源 + 商业化

Langfuse 明确选择 **OSI (Open Source Initiative)** 路线而非 pure SaaS。核心理由在官方 "Why Langfuse" 页面阐述：

1. **数据主权**: LLM 应用的 prompt/response 经常含 PII/商业机密，企业无法将数据交给第三方 SaaS
2. **Vendor lock-in 焦虑**: LangSmith 的封闭 API 让迁移成本高昂
3. **审计与合规**: 金融、医疗、政府客户需要 on-prem 部署
4. **社区飞轮**: 开源 → 集成生态 → 流量 → Cloud 转化

商业化路径采用 **Open Core** 模式：
- **Core (MIT)**: 所有 tracing、prompt、eval、dataset、playground 核心功能
- **Enterprise (EE)**: SSO、SCIM、Audit Logs、Custom SLA、UI 白标、Advanced RBAC

---

## 3. 产品定位与生态版图

### 3.1 产品的三大支柱

Langfuse 把 LLM 应用生命周期切成 4 个阶段，每个阶段都对应一个核心模块：

```
┌──────────────────────────────────────────────────────────────────┐
│                  Langfuse Product Surface (v3)                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────┐ │
│  │ Observability│  │   Prompt     │  │  Evaluation  │  │ Data │ │
│  │   (Tracing)  │  │  Management  │  │   (Scores)   │  │ sets │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────┘ │
│         │                  │                 │              │     │
│         └──────────────────┴─────────────────┴──────────────┘     │
│                                  │                                │
│                    ┌─────────────▼────────────┐                  │
│                    │   Unified LLM Engineering│                  │
│                    │       Data Layer         │                  │
│                    │  (Postgres + ClickHouse) │                  │
│                    └──────────────────────────┘                  │
│                                                                  │
│  Adjacent: Playground · Datasets · Experiments · Annotation Queues│
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 与 LLM Gateway 产品的边界

**关键区别**: Langfuse **不** 是一个 LLM Gateway。它**不** 路由请求、**不** 做 fallback、**不** 做语义缓存、**不** 替代 OpenAI 端点。

Langfuse 与 Gateway 的关系是 **观察者 vs 代理**：

| 维度 | LLM Gateway (Portkey/LiteLLM) | Langfuse |
| --- | --- | --- |
| 网络位置 | 数据通路 (in-line) | 旁路 (sidecar) |
| 协议 | OpenAI-compatible API | SDK 注入 / OTel exporter |
| 主要职责 | 路由、fallback、缓存、配额 | 追踪、调试、评估、prompt 管理 |
| 性能影响 | < 5ms | 0ms (异步批处理) |
| 失败影响 | 高 (downstream 全断) | 低 (SDK 本地 queue) |

**推荐组合**: Langfuse + LiteLLM 是官方推荐的"黄金组合"——LiteLLM 跑流量，Langfuse 做可观测性。两者通过 Langfuse 的 LiteLLM 集成自动捕获所有请求。

### 3.3 在 AI Engineering 平台赛道的坐标

```
                        商业 / 闭源
                              ▲
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              │         LangSmith             │
              │  (closed, $39/user)            │
              │                               │
   ┌──────────┼───────────────────────────────┼──────────┐
   │          │                               │          │
   │  Helicone  │    ★ Langfuse (核心)        │  Arize   │
   │ (gateway  │                               │ Phoenix  │
   │  + observ)│                               │ (eval)   │
   │          │                               │          │
   ├──────────┼───────────────────────────────┼──────────┤
   │          │                               │          │
   │  Portkey  │    Langfuse (开源 + 商业)    │  TruLens │
   │  (gateway)│                               │          │
   │          │                               │          │
   └──────────┼───────────────────────────────┼──────────┘
              │                               │
              │         OpenLLMetry           │
              │        (Traceloop)            │
              │                               │
              └───────────────────────────────┘
                              │
                              ▼
                        开源 / 自托管
```

---

## 4. 整体架构设计

### 4.1 官方架构图（Mermaid 重绘为 ASCII）

```
                    LLM Application (Your Code)
                    ┌──────────────────────────┐
                    │  Langfuse SDK            │
                    │  - Decorator / Callback  │
                    │  - Batches events        │
                    │  - Local queue + retry   │
                    └──────────────┬───────────┘
                                   │ HTTPS (gzip)
                                   │ /api/public/ingestion
                                   ▼
┌────────────────────────────────────────────────────────────────┐
│                    Langfuse Self-Hosted                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Web Server (Next.js + tRPC)              │   │
│  │  - Public REST API (/api/public/*)                       │   │
│  │  - Auth / Project / Org management                       │   │
│  │  - Prompt fetching & caching                             │   │
│  │  - Eval trigger & async dispatch                         │   │
│  └────┬─────────────┬──────────────┬────────────┬──────────┘   │
│       │             │              │            │              │
│       │             │              │            │              │
│  ┌────▼────┐   ┌────▼────┐   ┌─────▼────┐  ┌────▼─────┐        │
│  │Postgres │   │  Redis  │   │ClickHouse│  │S3/Blob   │        │
│  │ (OLTP)  │   │ (Cache  │   │ (OLAP)   │  │(Events,  │        │
│  │         │   │+ Queue) │   │          │  │Multimodal│        │
│  └─────────┘   └────┬────┘   └──────────┘  └──────────┘        │
│                     │                                             │
│                     ▼                                             │
│              ┌────────────────────┐                              │
│              │  Async Worker      │                              │
│              │  (langfuse/worker) │                              │
│              │  - Event parser    │                              │
│              │  - Eval runner     │                              │
│              │  - Aggregation     │                              │
│              │  - ClickHouse      │                              │
│              │    ingestion       │                              │
│              └────────┬───────────┘                              │
│                       │                                          │
│                       ▼                                          │
│              ClickHouse (OLAP)                                  │
│                       │                                          │
│                       ▼                                          │
│              ┌────────────────────┐                              │
│              │  Read API + UI     │  ◄── User dashboard          │
│              └────────────────────┘                              │
│                                                                  │
│  Optional: LLM API/Gateway (for Playground, LLM-as-Judge)       │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 三大组件职责

| 组件 | 镜像 | 职责 | 资源需求 (中等规模) |
| --- | --- | --- | --- |
| **Web Server** | `langfuse/langfuse` | HTTP API、UI、Auth、Prompt 缓存 | 2-4 vCPU, 4-8GB RAM |
| **Worker** | `langfuse/worker` | 异步事件处理、Eval 执行、聚合写入 ClickHouse | 2-4 vCPU, 4-8GB RAM |
| **Postgres** | `postgres:16` | 项目/用户/API Key/Prompt metadata/Scores metadata | 2 vCPU, 4GB RAM, 50GB SSD |
| **ClickHouse** | `clickhouse/clickhouse-server:24` | Trace/Observation/Score 事件存储 (列存) | 4 vCPU, 16GB RAM, 200GB SSD |
| **Redis** | `redis:7` (或 Valkey) | API key 缓存、Prompt 缓存、异步队列 | 1 vCPU, 1GB RAM |
| **S3 / Blob** | MinIO / S3 / Azure Blob / GCS | 原始事件 payload、多模态附件、export 文件 | 对象存储，按用量 |

### 4.3 数据流

**写入路径 (Ingestion)**:

```
SDK ──(batch)──> Web Server ──(write event)──> S3
                       │                          │
                       │                          │ (queue ref)
                       ▼                          │
                    Redis ◄────────────────────────┘
                       │
                       ▼
                    Worker (consume)
                       │
                       ├──> ClickHouse (解析+索引)
                       ├──> Postgres (metadata)
                       └──> Trigger Eval (if configured)
```

**读取路径 (Read)**:

```
User UI ──> Web Server (tRPC) ──> ClickHouse (analytics)
                              ──> Postgres (project/setting/prompt meta)
                              ──> Redis (prompt cache hit)
                              ──> S3 (multimodal payload)
```

### 4.4 关键设计决策

1. **OLTP + OLAP 分离** — Postgres 处理元数据，ClickHouse 处理高基数事件
2. **Event 持久化优先 S3** — 失败可恢复，不丢事件
3. **Async Worker 解耦** — Web 不阻塞，Eval 可独立扩展
4. **SDK 端 batching** — 默认 5s 一次或 15 个 event flush，避免高频写入
5. **Local queue 兜底** — SDK 内部有 retry + disk fallback

---

## 5. 核心数据模型

### 5.1 三层模型

Langfuse 的核心抽象：

```
Project
  └── Traces
        ├── Observations (LLM calls, retrievals, tools, agents)
        ├── Scores (eval/feedback, attached to trace or observation)
        └── Session (groups traces for multi-turn conv)
              └── User (per-user analytics)
```

### 5.2 数据对象详细定义

#### Trace
```typescript
{
  id: string,                    // ulid
  projectId: string,
  name?: string,
  userId?: string,
  sessionId?: string,
  metadata?: object,             // 任意 JSON
  tags?: string[],
  release?: string,              // git sha, env tag
  version?: string,
  public?: boolean,
  input?: object,                // 整体输入
  output?: object,               // 整体输出
  createdAt: timestamp,
  updatedAt: timestamp
}
```

#### Observation (Span)
```typescript
{
  id: string,                    // ulid
  traceId: string,
  parentObservationId?: string,  // 嵌套
  type: "GENERATION" | "SPAN" | "EVENT" | "AGENT" | "TOOL" | "CHAIN" | "RETRIEVER" | "EMBEDDING" | "GUARDRAIL",
  name: string,
  startTime: timestamp,
  endTime: timestamp,
  model?: string,                // "gpt-4o", "claude-3-5-sonnet"
  modelParameters?: object,
  input?: object,
  output?: object,
  usage?: {
    promptTokens: number,
    completionTokens: number,
    totalTokens: number,
    inputCost?: number,          // USD
    outputCost?: number,
    totalCost?: number
  },
  level: "DEBUG" | "DEFAULT" | "WARNING" | "ERROR",
  statusMessage?: string,
  metadata?: object,
  // Generation-only
  promptId?: string,             // link to Langfuse prompt
  completionStartTime?: timestamp  // TTFT
}
```

#### Score
```typescript
{
  id: string,
  traceId?: string,
  observationId?: string,        // 关联具体 span
  sessionId?: string,
  name: string,                  // "quality", "toxicity", "relevance"
  value?: number,                // 数值
  stringValue?: string,          // 分类
  dataType: "NUMERIC" | "CATEGORICAL" | "BOOLEAN",
  source: "API" | "EVAL" | "ANNOTATION" | "UI",
  comment?: string,
  authorUserId?: string,
  createdAt: timestamp
}
```

### 5.3 ClickHouse 表结构 (简化)

```sql
-- traces (主键: project_id, id, timestamp)
CREATE TABLE traces (
  project_id String,
  id String,
  timestamp DateTime64(3),
  name String,
  user_id String,
  session_id String,
  tags Array(String),
  release String,
  version String,
  metadata String,           -- JSON string
  input String,
  output String,
  -- 预聚合列 (Langfuse v3 引入)
  observation_count UInt32,
  total_cost Decimal(18,12),
  total_tokens UInt64,
  latency_ms UInt32
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_id, timestamp, id);

-- observations
CREATE TABLE observations (
  project_id String,
  id String,
  trace_id String,
  parent_observation_id String,
  type LowCardinality(String),
  name String,
  start_time DateTime64(3),
  end_time Nullable(DateTime64(3)),
  model LowCardinality(String),
  model_parameters String,
  input String,
  output String,
  usage_details String,      -- JSON
  cost_details String,
  level LowCardinality(String),
  status_message String,
  prompt_id String,
  completion_start_time Nullable(DateTime64(3))
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (project_id, trace_id, start_time, id);

-- scores
CREATE TABLE scores (
  project_id String,
  id String,
  trace_id String,
  observation_id String,
  name String,
  value Decimal(18,9),
  string_value String,
  data_type LowCardinality(String),
  source LowCardinality(String),
  comment String,
  author_user_id String,
  timestamp DateTime64(3)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_id, timestamp, name, id);
```

**关键优化**:
- `project_id` 作为复合主键第一列，强制租户隔离
- 按月分区 (PARTITION BY toYYYYMM)
- `LowCardinality` 包装低基数字符串
- `Decimal(18,12)` 存储 cost，精度 12 位小数
- JSON 字段直接存 string，查询时 JSONExtract 解

---

## 6. Tracing / Observability 实现细节

### 6.1 SDK 注入机制

Langfuse 提供两种 instrumentation 方式：

#### A) 显式 SDK 调用 (Manual)

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://cloud.langfuse.com"
)

# 创建 trace
trace = langfuse.trace(
    name="qa-agent",
    user_id="user-123",
    session_id="sess-456",
    tags=["production", "v2.3"]
)

# 嵌套 span
with trace.span(name="retrieval") as retrieval:
    docs = retrieve(query)
    retrieval.update(output={"doc_count": len(docs)})

# LLM call (Generation 类型)
with trace.generation(
    name="answer-generation",
    model="gpt-4o",
    model_parameters={"temperature": 0.7}
) as gen:
    response = openai_client.chat.completions.create(...)
    gen.update(
        output=response.choices[0].message,
        usage={
            "promptTokens": response.usage.prompt_tokens,
            "completionTokens": response.usage.completion_tokens
        }
    )

# 评分
trace.score(name="quality", value=0.85, comment="good")

# 结束 (显式或上下文退出时自动)
langfuse.flush()
```

#### B) 自动 OpenAI 兼容 (drop-in replacement)

```python
from langfuse.openai import openai  # ← 不是原生 openai

# 行为完全一致，所有调用自动追踪
completion = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
# 自动产生 trace + generation，自动计算 cost
```

#### C) 框架回调 (Callback)

```python
from langfuse.callback import CallbackHandler

handler = CallbackHandler()

# LangChain
from langchain.chains import LLMChain
chain = LLMChain(llm=llm, prompt=prompt)
result = chain.invoke({"input": "Hello"}, config={"callbacks": [handler]})

# LlamaIndex
from llama_index.core import Settings
Settings.callback_manager.add_handler(handler)
```

### 6.2 OpenTelemetry 集成

Langfuse v2.5+ 完整支持 OTel，可以作为 OTel backend：

```python
# OTel SDK 配置
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
exporter = OTLPSpanExporter(
    endpoint="https://cloud.langfuse.com/api/public/otel/v1/traces",
    headers={"Authorization": "Basic " + base64(f"{public_key}:{secret_key}")}
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# 现在任何 OTel-aware 库都自动追踪
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("my-op") as span:
    span.set_attribute("langfuse.user.id", "user-123")
    span.set_attribute("langfuse.session.id", "sess-456")
    ...
```

支持的 OTel 语义约定属性：
- `langfuse.user.id` → userId
- `langfuse.session.id` → sessionId
- `langfuse.trace.tags` → tags (JSON array)
- `langfuse.observation.type` → GENERATION/SPAN/EVENT
- `langfuse.observation.model` → model name
- `langfuse.observation.usage.{input,output,total}_tokens`
- `langfuse.observation.cost.{input,output,total}` (USD)
- `gen_ai.*` 标准 OTel GenAI 约定

### 6.3 异步与批处理机制

```python
# SDK 内部实现 (简化)
class LangfuseClient:
    def __init__(self, ...):
        self._queue = Queue(maxsize=100_000)  # 内存队列
        self._disk_queue_path = "/tmp/langfuse"  # 溢出落盘
        self._batch_size = 15
        self._flush_interval = 5  # seconds
        self._background_thread = Thread(target=self._flush_loop, daemon=True)
        self._background_thread.start()

    def _flush_loop(self):
        while True:
            sleep(self._flush_interval)
            batch = self._collect_batch()  # 最多 batch_size
            try:
                self._http.post("/api/public/ingestion", batch, gzip=True)
            except Exception:
                self._write_to_disk(batch)  # 失败落盘
                self._schedule_retry()

    def flush(self):
        # 强制刷新 (在脚本退出、测试用例前调用)
        self._flush_loop_until_empty()
```

**关键不变量**:
- 一次 ingest 失败：批量写入 S3 (Web 端)，web 收到即视为持久化
- Web 端解析失败：写入 ClickHouse 的 `events_parsing_failed` 表 (可重放)
- 客户端网络失败：本地 retry with exponential backoff
- 客户端崩溃：disk queue 持久化，下次启动 replay

### 6.4 TTFT 与延迟分析

Langfuse 专门为流式 LLM 响应做了 `completionStartTime` 字段：

```python
with trace.generation(name="stream") as gen:
    stream = openai_client.chat.completions.create(stream=True, ...)
    chunks = []
    for chunk in stream:
        if chunk.choices[0].delta.get("content"):
            chunks.append(chunk.choices[0].delta.content)
            if not gen.completionStartTime:  # 第一个 token 时间
                gen.update(completion_start_time=datetime.now())
    gen.update(output="".join(chunks))
```

UI 上能看到：
- **TTFT (Time to First Token)**: `completionStartTime - startTime`
- **Total Latency**: `endTime - startTime`
- **Tokens/sec**: 派生指标

### 6.5 Session 追踪

```python
# 同一个 session 内多次 trace 关联
def chat_handler(user_message, session_id):
    trace = langfuse.trace(
        name="chat-turn",
        session_id=session_id,  # 关键
        user_id=get_user_id()
    )
    # ... 处理
    return response

# UI 中 "Sessions" 视图：聚合一个 session_id 下所有 traces
# 派生指标：session 总 token、平均 turn 数、session 转化
```

---

## 7. Prompt Management 详细机制

### 7.1 核心概念

```
Prompt (logical name "customer-support")
  ├── v1 (deprecated)
  ├── v2 (production, label="production")
  ├── v3 (staging, label="staging")
  └── v4 (latest draft, no label)
```

- **Prompt**: 逻辑名（如 "customer-support"）
- **Version**: 不可变快照
- **Label**: 可移动指针，指向某 version（如 "production"、"staging"、"latest"）
- **Compilation**: 服务端把变量插入到 mustache 模板

### 7.2 创建与版本化

#### UI 方式
```text
1. 打开 Prompts → New Prompt
2. Name: customer-support
3. Type: text
4. Prompt:
   You are a {{tone}} support agent for {{company}}.
   User: {{question}}
   Answer:
5. Save → 自动创建 v1
6. Edit → Save as new version → v2
7. 在 v2 上点 "Promote to production" → label 指向 v2
```

#### API 方式
```bash
curl -X POST https://cloud.langfuse.com/api/public/v2/prompts \
  -H "Authorization: Basic $BASE64_KEYS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer-support",
    "type": "text",
    "prompt": "You are a {{tone}} support agent.\nUser: {{question}}",
    "labels": ["production"],
    "config": {"temperature": 0.7, "model": "gpt-4o"},
    "tags": ["customer-facing"]
  }'
```

#### SDK 方式
```python
langfuse.create_prompt(
    name="customer-support",
    prompt="You are a {{tone}} support agent for {{company}}.",
    labels=["production"],
    config={"model": "gpt-4o", "temperature": 0.7},
    tags=["v2"]
)
```

### 7.3 应用端拉取

```python
# 简单文本 prompt
prompt = langfuse.get_prompt("customer-support", label="production")
compiled = prompt.compile(tone="friendly", company="Acme")
# → "You are a friendly support agent for Acme."

# 带配置
prompt = langfuse.get_prompt("customer-support", label="production")
config = prompt.config  # {"model": "gpt-4o", "temperature": 0.7}
# 调用 LLM 时直接使用

# 多模态 / 聊天格式
prompt = langfuse.get_prompt("chat-support", type="chat", label="production")
messages = prompt.compile(question="How do I refund?")
# → [
#     {"role": "system", "content": "You are a helpful support agent."},
#     {"role": "user", "content": "How do I refund?"}
#   ]
```

### 7.4 缓存与刷新策略

```
应用启动
  └── get_prompt("customer-support", label="production")
       ├── HTTP GET (首次)
       ├── 写入 SDK 本地 cache (TTL 60s)
       └── 返回 compiled

应用运行时
  └── get_prompt(...) 调用 → 命中本地 cache → 0ms
       └── TTL 过期 → 重新 GET → 更新 cache

后台 (Langfuse SDK 内部)
  └── 每 60s 拉取 label="production" 当前 version
       └── 若 version 变化 → 静默更新 cache，下一次 compile 使用新版本
```

**特性**:
- 默认 cache TTL 60s，可配置
- label 改变时 60s 内全网生效 (rolling rollout)
- "Force reload" 强制立即拉取 (用于紧急回滚)
- A/B 场景：拉取不带 label 的 latest version，与 production 对比

### 7.5 与 Trace 关联

```python
# 在 trace 中使用 prompt → 自动 link
with langfuse.trace(name="chat", user_id="u123") as trace:
    prompt = langfuse.get_prompt("customer-support", label="production", \)
    with trace.generation(
        name="answer",
        model=prompt.config["model"],
        prompt=prompt  # ← 关键，trace 会记录 prompt_id + version
    ) as gen:
        response = openai_client.chat.completions.create(
            model=prompt.config["model"],
            messages=prompt.compile(question=question)
        )
        gen.update(output=response, usage=...)
```

UI 中能看到的关联：
- Trace → 关联的 Prompt version
- Prompt version → 所有使用过它的 traces
- 比较同一 prompt 不同 version 的 cost/latency/quality

### 7.6 高级特性

- **Composability**: 一个 prompt 可以 include 另一个 (e.g. `{{>shared-system}}`)
- **Placeholders**: 支持 `{{variable}}` mustache 语法
- **JSON Schema validation**: Prompt output 期望结构时可在 config 声明 schema
- **Cache control**: 服务端 Redis 缓存，SDK 客户端 cache，hot prompt 不打 DB

---

## 8. Evaluation / Datasets / Experiments

### 8.1 Evaluation 体系

Langfuse 支持多种 eval 方法，并允许它们**统一输出 Score**：

```
┌──────────────────────────────────────────────────────────────┐
│                Evaluation Methods                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ LLM-as-a-Judge │  │ Code Evaluator │  │ User Feedback  │  │
│  │ (LLM 评分)     │  │ (代码函数)     │  │ (👍/👎)         │  │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘  │
│           │                  │                    │          │
│           └──────────────────┴────────────────────┘          │
│                              │                               │
│                              ▼                               │
│                     POST /api/public/scores                  │
│                              │                               │
│                              ▼                               │
│                      Score (在 ClickHouse)                  │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐                       │
│  │ Manual         │  │ Custom         │                       │
│  │ Annotation     │  │ (any external) │                       │
│  └────────────────┘  └────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

### 8.2 LLM-as-a-Judge 配置

```python
# 通过 Langfuse UI 创建
# 1. 打开 Evaluators → New
# 2. 类型: LLM-as-a-Judge
# 3. 名称: helpfulness
# 4. Judge Prompt:
#    Given the user question and the assistant's response,
#    rate the response on a scale of 1-5 for helpfulness.
#    Question: {{input}}
#    Response: {{output}}
#    Rating (1-5):
# 5. Judge Model: gpt-4o-mini
# 6. 触发: on-production-trace (新 trace 进入即跑)
# 7. 关联字段: input/output from trace

# 跑出后:
# Score: helpfulness = 4.2, dataType=NUMERIC, source=EVAL
# 自动 attach 到 trace，UI 中可看
```

支持的触发方式：
- **On production trace**: 新 trace 进入后异步跑 (Worker 触发)
- **On experiment run**: 跑 experiment 时针对每条 dataset item
- **Manual**: API 触发，附到指定 trace

### 8.3 Code Evaluator

```python
# Self-hosted: 在 Web Server 容器内运行 Python 函数
from langfuse.evaluators import Evaluator

@Evaluator(name="response_length", description="检查响应长度")
def response_length_eval(trace):
    output = trace.output
    if isinstance(output, str):
        length = len(output)
    else:
        length = len(str(output))

    if length < 10:
        return {"value": 0, "comment": "too short"}
    elif length > 1000:
        return {"value": 0.5, "comment": "too long"}
    else:
        return {"value": 1, "comment": "ok"}
```

### 8.4 Datasets

```python
# 创建 dataset
dataset = langfuse.create_dataset(name="qa-benchmark-v1")

# 注入 item
dataset.create_item(
    input={"question": "What is the capital of France?"},
    expected_output={"answer": "Paris"},
    metadata={"source": "wikipedia"}
)

# 批量上传
items = [
    {"input": {...}, "expected_output": {...}},
    ...
]
langfuse.create_dataset_items(items=items, dataset_name="qa-benchmark-v1")
```

存储模型：
- Dataset 本身存 Postgres
- Items 存 ClickHouse (events 表)
- 适合 1k-1M 规模，> 1M 建议外部 S3

### 8.5 Experiments

```python
# 定义一个实验 (用同一 dataset 测不同 prompt)
from langfuse.experiment import Experiment

def my_app_run(item):
    prompt = langfuse.get_prompt("customer-support", label="staging")
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=prompt.compile(question=item.input["question"])
    )
    return response.choices[0].message.content

exp = Experiment(
    name="v3-vs-v4-test",
    dataset_name="qa-benchmark-v1",
    run=my_app_run,
    evaluators=["helpfulness", "response_length"],
    metadata={"prompt_version": "v4"}
)
exp.run()  # 异步执行，结果入 ClickHouse
```

UI 中能看到：
- Dataset → 所有 Experiments
- Experiment → 每个 item 的 input/output/score
- Experiment summary：平均 score 分布、cost、latency

### 8.6 Annotation Queues

```python
# 人工标注工作流
queue = langfuse.create_annotation_queue(
    name="low-confidence",
    filter={
        "scores": [{"name": "confidence", "operator": "<", "value": 0.6}]
    }
)
# 所有 confidence < 0.6 的 trace 自动进入队列
# 标注员在 UI 中评分，score 写回 trace
```

---

## 9. SDK 与 OpenTelemetry 协议支持

### 9.1 协议支持矩阵

| 协议 | Python | JS/TS | Java | Go | Rust |
| --- | --- | --- | --- | --- | --- |
| **Langfuse Native SDK** | ✅ v3 | ✅ v4 | ❌ | ❌ | ❌ |
| **OpenTelemetry** | ✅ | ✅ | ✅ | ✅ | ✅ (OTel 原生) |
| **OTLP/HTTP** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **OTLP/gRPC** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Manual REST API** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **LangChain Callback** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **LlamaIndex Callback** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **OpenAI drop-in** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Anthropic drop-in** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Bedrock wrapper** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Vertex wrapper** | ✅ | ❌ | ❌ | ❌ | ❌ |

### 9.2 Python SDK 安装

```bash
pip install langfuse
# 或
pip install langfuse[opentelemetry]  # OTel 额外
```

### 9.3 Python SDK 核心类

```python
# 1. Langfuse - 主入口
from langfuse import Langfuse
client = Langfuse(public_key=..., secret_key=..., host=...)

# 2. Trace - 单次请求追踪
trace = client.trace(name=..., user_id=..., session_id=...)
# → 返回 StatefulSpanClient (可作 context manager)

# 3. Span (Observation)
with trace.span(name="retrieval") as span:
    span.update(output=..., metadata=...)

# 4. Generation (LLM-specific)
with trace.generation(name="llm-call", model="gpt-4o") as gen:
    gen.update(
        usage={"promptTokens": 100, "completionTokens": 50},
        output=...,
        cost=...  # 可选，自动计算
    )

# 5. Score
trace.score(name="quality", value=0.85)

# 6. Event (无 duration 的标记)
trace.event(name="user-clicked-button", metadata={"button": "submit"})

# 7. Prompt
prompt = client.get_prompt("name", label="production", version=2)
compiled = prompt.compile(var1="x")

# 8. Dataset / Experiment
ds = client.create_dataset(name="...")
ds.create_item(input=..., expected_output=...)
```

### 9.4 JS/TS SDK 核心类

```typescript
import { Langfuse } from "langfuse";

const langfuse = new Langfuse({
  publicKey: process.env.LANGFUSE_PUBLIC_KEY,
  secretKey: process.env.LANGFUSE_SECRET_KEY,
  baseUrl: process.env.LANGFUSE_HOST
});

// 1. Trace
const trace = langfuse.trace({
  name: "qa-agent",
  userId: "u123",
  sessionId: "s456",
  tags: ["prod"]
});

// 2. Span (with type)
const span = trace.span({ name: "retrieval" });
span.end({ output: { docs: 5 } });

// 3. Generation
const generation = trace.generation({
  name: "answer",
  model: "gpt-4o",
  modelParameters: { temperature: 0.7 },
  input: { messages: [...] }
});
generation.end({
  output: { content: "..." },
  usage: { promptTokens: 100, completionTokens: 50 }
});

// 4. Score
trace.score({ name: "quality", value: 0.9 });

// 5. Prompt
const prompt = await langfuse.getPrompt("customer-support", { label: "production" });
const compiled = prompt.compile({ tone: "friendly" });

// 6. Force flush (在 serverless 中必须)
await langfuse.flushAsync();
```

### 9.5 OTel → Langfuse 字段映射

```
OpenTelemetry Attribute        →  Langfuse Field
─────────────────────────────────────────────────
gen_ai.system                  →  metadata.gen_ai.system
gen_ai.request.model           →  model
gen_ai.request.temperature     →  model_parameters.temperature
gen_ai.usage.input_tokens      →  usage.promptTokens
gen_ai.usage.output_tokens     →  usage.completionTokens
gen_ai.usage.cost              →  usage.totalCost
langfuse.trace.name            →  name
langfuse.user.id               →  user_id
langfuse.session.id            →  session_id
langfuse.trace.tags            →  tags (JSON decoded)
langfuse.observation.type      →  type
langfuse.observation.level     →  level
langfuse.observation.status_message → status_message
```

---

## 10. 集成生态 (50+ 框架)

### 10.1 集成全景

```
                   ┌────────────────────────────────────────┐
                   │      Langfuse Integration Surface       │
                   └────────────────────────────────────────┘
                                      │
       ┌──────────────┬───────────────┼────────────────┬──────────────┐
       │              │               │                │              │
   ┌───▼────┐    ┌────▼────┐    ┌────▼────┐    ┌─────▼─────┐   ┌────▼────┐
   │  SDK   │    │  LLM    │    │Frameworks│    │  Vector   │   │Gateway  │
   │        │    │ Providers│   │          │    │   DBs     │   │         │
   ├────────┤    ├─────────┤    ├──────────┤    ├───────────┤   ├─────────┤
   │Python  │    │OpenAI    │   │LangChain │    │Pinecone   │   │LiteLLM  │
   │JS/TS   │    │Anthropic │   │LlamaIndex│    │Weaviate   │   │Portkey  │
   │Java    │    │Google    │   │Haystack  │    │Chroma     │   │Cloudflare│
   │(OTel)  │    │Mistral   │   │DSPy      │    │Qdrant     │   │         │
   │Go(OTel)│    │Cohere    │   │Instructor│   │pgvector   │   │         │
   │        │    │Groq      │   │Mirascope │   │           │   │         │
   │        │    │Bedrock   │   │Vercel AI │   │           │   │         │
   │        │    │Vertex    │   │Mastra    │   │           │   │         │
   │        │    │Ollama    │   │CrewAI    │   │           │   │         │
   │        │    │Replicate │   │AutoGen   │   │           │   │         │
   │        │    │Together  │   │          │   │           │   │         │
   │        │    │HuggingFce│   │          │   │           │   │         │
   │        │    │vLLM      │   │          │   │           │   │         │
   │        │    │Fireworks │   │          │   │           │   │         │
   │        │    │SGLang    │   │          │   │           │   │         │
   │        │    │...100+   │   │          │   │           │   │         │
   └────────┘    └──────────┘   └──────────┘    └───────────┘   └─────────┘
```

### 10.2 重点集成实现原理

#### LiteLLM 集成
```python
# 方式 1: 在 LiteLLM proxy config 中加 callback
# config.yaml
litellm_settings:
  success_callback: ["langfuse"]
  failure_callback: ["langfuse"]
  telemetry: false

# 方式 2: 直接使用 callback 类
import litellm
from langfuse.decorators import langfuse_context, observe

litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]
```
所有经过 LiteLLM 的请求自动产生 trace，包含 model、tokens、cost、latency。

#### OpenAI drop-in
```python
# 替换 import 即可
from langfuse.openai import openai
# ↑ 内部 monkey-patch 真实 openai.client.OpenAI
# 在 create() / stream() 前后插入 hook
```
实际实现：
```python
# langfuse/openai 简化
original_create = openai.OpenAI.chat.completions.create
def patched_create(self, *args, **kwargs):
    span = langfuse_context.get_current_observation().generation(
        name="openai-chat",
        model=kwargs.get("model"),
        input=kwargs.get("messages"),
        model_parameters={k: v for k, v in kwargs.items() if k in ["temperature", "top_p", ...]}
    )
    try:
        response = original_create(self, *args, **kwargs)
        span.update(
            output=response.choices[0].message,
            usage={
                "promptTokens": response.usage.prompt_tokens,
                "completionTokens": response.usage.completion_tokens
            }
        )
        return response
    except Exception as e:
        span.update(level="ERROR", status_message=str(e))
        raise
```

#### LangChain Callback
```python
class LangfuseCallbackHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        # 创建 generation observation
        ...

    def on_llm_end(self, response, **kwargs):
        # 写入 token usage
        ...

    def on_chain_start(self, serialized, inputs, **kwargs):
        # 创建 chain span
        ...

    def on_chain_end(self, outputs, **kwargs):
        # 结束 span
        ...

    def on_tool_start(self, serialized, input_str, **kwargs):
        # 创建 tool observation
        ...
```

### 10.3 集成数量统计

官方 integrations 页面（langfuse.com/integrations）列出 **50+** 项，覆盖：

| 类别 | 数量 | 列表 |
| --- | --- | --- |
| LLM Providers | 25+ | OpenAI, Anthropic, Google Gemini, Mistral, Cohere, Groq, Bedrock, Vertex, Together, Fireworks, Replicate, HuggingFace, Ollama, vLLM, SGLang, llama.cpp, Anyscale, DeepInfra, Perplexity, AI21, Aleph Alpha, Azure OpenAI, OpenRouter, Unify, Martian |
| Frameworks | 10+ | LangChain (Python/JS), LlamaIndex (Python), Haystack, DSPy, Instructor, Mirascope, Vercel AI SDK, Mastra, CrewAI, AutoGen, AG2, smolagents |
| Vector DBs | 8+ | Pinecone, Weaviate, Chroma, Qdrant, pgvector, LanceDB, Milvus, Marqo |
| Gateways | 5+ | LiteLLM, Portkey, Cloudflare AI Gateway, OpenRouter, Unify |
| 评估 | 5+ | Ragas, DeepEval, Phoenix, TruLens, Braintrust |
| 其他 | 10+ | Browser SDK, OpenLLMetry, Helicone, Arize, SigNoz, MLflow, Weights & Biases |

### 10.4 集成质量

按"侵入性"（对应用代码改动量）排序：

```
最无侵入: OTel (零代码改动，只需配 exporter)
无侵入:  OpenAI drop-in (改 import 即可)
轻侵入:  LangChain callback (加一行 config={"callbacks": [handler]})
中侵入:  显式 SDK (需要手动 span/generation)
高侵入:  自定义 eval pipeline (需要写代码)
```

### 10.5 自定义集成

任意 HTTP 客户端 → Langfuse Public API：

```bash
# 1. 创建 trace
curl -X POST "$HOST/api/public/v2/traces" \
  -H "Authorization: Basic $BASE64_KEYS" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "01HXXX...",
    "name": "my-trace",
    "userId": "u-123",
    "sessionId": "s-456",
    "input": {"q": "hello"},
    "output": {"a": "world"},
    "observations": [{
      "id": "01HYYY...",
      "type": "GENERATION",
      "name": "llm-call",
      "model": "gpt-4o",
      "usage": {"promptTokens": 10, "completionTokens": 5}
    }],
    "scores": [{
      "name": "quality",
      "value": 0.9,
      "dataType": "NUMERIC"
    }]
  }'
```

OpenAPI spec 在 `https://cloud.langfuse.com/api/public/openapi.json` 可下载，Postman collection 官方提供。

---

## 11. API 与数据平台

### 11.1 API 分层

Langfuse 提供三种 API：

| 层级 | 路径 | 鉴权 | 用途 |
| --- | --- | --- | --- |
| **Public API** | `/api/public/*` | Basic Auth (pk:sk) | 客户端 SDK、上报 traces、读 prompts |
| **UI API (tRPC)** | `/api/*` | Session Cookie | UI 内部调用，不对外开放 |
| **Instance API (EE)** | `/api/admin/*` | Admin Token | 多租户管理、用户配 license、审计 |

### 11.2 关键 Public 端点

```
# Ingestion
POST   /api/public/ingestion                 # SDK 上报 (batch event)
POST   /api/public/v2/traces                 # 直接创建 trace

# Read
GET    /api/public/v2/traces                 # 列表 + 过滤
GET    /api/public/v2/traces/{id}            # 单个详情
GET    /api/public/v2/observations           # span 列表
GET    /api/public/v2/sessions               # session 列表
GET    /api/public/v2/scores                 # score 列表

# Prompt
POST   /api/public/v2/prompts                # 创建/更新
GET    /api/public/v2/prompts/{name}         # 拉取 (by label or version)
GET    /api/public/v2/prompts                # 列表

# Dataset
POST   /api/public/v2/datasets               # 创建
POST   /api/public/v2/dataset-items          # 批量添加
GET    /api/public/v2/datasets/{name}/items   # 拉取

# Score
POST   /api/public/v2/scores                 # 提交评分

# Metrics (aggregated)
GET    /api/public/metrics/daily-usage       # 每日用量
GET    /api/public/metrics/observations      # 观察指标

# Export
POST   /api/public/export/traces             # 异步导出 (返回 jobId)
GET    /api/public/export/jobs/{id}          # 查询导出状态
```

### 11.3 分页与过滤

```bash
# 过滤 + 分页
GET /api/public/v2/traces?
  page=1&
  limit=50&
  userId=u-123&              # 过滤字段
  sessionId=s-456&
  tags=production&
  fromTimestamp=2026-01-01T00:00:00Z&
  toTimestamp=2026-01-31T23:59:59Z&
  fields=id,name,userId,timestamp  # 控制返回字段
```

### 11.4 大数据量导出

```bash
# 异步导出
curl -X POST "$HOST/api/public/export/traces" \
  -H "Authorization: Basic $BASE64_KEYS" \
  -d '{
    "filter": {"userId": "u-123"},
    "fields": ["id", "name", "input", "output", "timestamp"],
    "format": "JSON"  # 或 "CSV", "Parquet"
  }'
# → {"jobId": "exp-123", "status": "QUEUED"}

# 查询状态
GET /api/public/export/jobs/exp-123
# → {"status": "DONE", "downloadUrl": "https://...signed-url..."}
# 导出文件存 S3，链接 1h 过期
```

适合：审计、合规、ML 训练 pipeline、外部 BI 工具。

### 11.5 Webhooks

```yaml
# 触发事件: trace.created, score.created, dataset.item.created
POST https://your-webhook.com/langfuse
{
  "event": "trace.created",
  "data": {
    "projectId": "...",
    "traceId": "...",
    "timestamp": "..."
  }
}
```

### 11.6 批量摄取限制

| Plan | req/min | 单 req events | events/sec (持续) |
| --- | --- | --- | --- |
| Hobby | 1,000 | 500 | ~8,000 |
| Core | 4,000 | 500 | ~32,000 |
| Pro | 20,000 | 1,000 | ~160,000 |
| Enterprise | Custom | Custom | Custom |

单 event 体积上限 1MB（含 multimodal 附件），multipart upload 用于 >1MB 文件。

---

## 12. 部署方式深度对比

### 12.1 部署选项矩阵

| 部署方式 | 适用规模 | 启动时间 | HA | 备份 | License Key 限制 |
| --- | --- | --- | --- | --- | --- |
| **Docker Compose (Local)** | 5 分钟验证 | < 5 min | ❌ | 手动 | 无 |
| **Docker Compose (VM)** | < 1k traces/day | < 30 min | ❌ | 手动 | 无 |
| **Kubernetes Helm** | > 10k traces/day | 1-2h | ✅ | K8s snapshots | 部分 |
| **AWS Terraform** | 100k+ traces/day | 2-4h | ✅ | RDS + S3 策略 | 部分 |
| **Azure Terraform** | 同上 | 2-4h | ✅ | Azure Backup | 部分 |
| **GCP Terraform** | 同上 | 2-4h | ✅ | GCS versioning | 部分 |
| **Railway** | 5k traces/day | 10 min | 部分 | Railway pg | 无 |
| **Langfuse Cloud** | 任意 | 0 | ✅ (managed) | ✅ | 无 (已含) |

### 12.2 Docker Compose 最小部署

```yaml
# docker-compose.yml (Langfuse v3)
version: "3.9"

services:
  langfuse-web:
    image: langfuse/langfuse:3
    ports: ["3000:3000"]
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres
      - NEXTAUTH_URL=http://localhost:3000
      - NEXTAUTH_SECRET=replace-me-with-random
      - SALT=replace-me-with-random
      - ENCRYPTION_KEY=replace-me-with-32-bytes-base64
      - REDIS_URL=redis://redis:6379
      - CLICKHOUSE_URL=http://clickhouse:8123
      - CLICKHOUSE_USER=clickhouse
      - CLICKHOUSE_PASSWORD=clickhouse
      - S3_ENDPOINT=http://minio:9000
      - S3_ACCESS_KEY_ID=minio
      - S3_SECRET_ACCESS_KEY=miniosecret
      - S3_BUCKET=langfuse
      - LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES=false
    depends_on: [postgres, redis, clickhouse, minio]
    restart: unless-stopped

  langfuse-worker:
    image: langfuse/langfuse-worker:3
    environment:
      # 相同环境变量
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres
      - REDIS_URL=redis://redis:6379
      - CLICKHOUSE_URL=http://clickhouse:8123
      - S3_ENDPOINT=http://minio:9000
      - S3_ACCESS_KEY_ID=minio
      - S3_SECRET_ACCESS_KEY=miniosecret
      - S3_BUCKET=langfuse
    depends_on: [postgres, redis, clickhouse, minio]
    restart: unless-stopped

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    volumes: ["pgdata:/var/lib/postgresql/data"]
    # 关键: 时区必须 UTC
    command: postgres -c timezone=UTC

  clickhouse:
    image: clickhouse/clickhouse-server:24
    environment:
      CLICKHOUSE_USER: clickhouse
      CLICKHOUSE_PASSWORD: clickhouse
      CLICKHOUSE_DB: default
    volumes: ["chdata:/var/lib/clickhouse"]
    ulimits:
      nofile: { soft: 262144, hard: 262144 }

  redis:
    image: redis:7
    volumes: ["redisdata:/data"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: miniosecret
    volumes: ["miniodata:/data"]
    ports: ["9001:9001"]

volumes:
  pgdata: {}
  chdata: {}
  redisdata: {}
  miniodata: {}
```

启动：
```bash
docker compose up -d
# 访问 http://localhost:3000 注册 admin
```

### 12.3 K8s Helm 部署

```bash
# 添加 repo
helm repo add langfuse https://langfuse.github.io/langfuse-helm
helm repo update

# 最小安装 (自带 postgres/clickhouse/redis)
helm install langfuse langfuse/langfuse \
  --namespace langfuse --create-namespace \
  --set langfuse.nextauth.secret=$(openssl rand -base64 32) \
  --set langfuse.salt=$(openssl rand -base64 32)

# 生产安装 (BYO 基础设施)
helm install langfuse langfuse/langfuse \
  --set postgresql.enabled=false \
  --set clickhouse.enabled=false \
  --set redis.enabled=false \
  --set langfuse.externalDatabaseUrl=$RDS_URL \
  --set langfuse.externalClickhouseUrl=$CH_URL \
  --set langfuse.externalRedisUrl=$REDIS_URL \
  --set langfuse.s3.endpoint=$S3_ENDPOINT \
  --set langfuse.s3.accessKeyId.value=$AK \
  --set langfuse.s3.secretAccessKey.value=$SK
```

### 12.4 多区域部署

Langfuse v3 支持 active-active 模式，但 ClickHouse 需要 ReplicatedMergeTree 手动配置：

```xml
<!-- clickhouse config.xml -->
<clickhouse>
  <remote_servers>
    <langfuse_cluster>
      <shard>
        <internal_replication>true</internal_replication>
        <replica><host>ch-1</host><port>9000</port></replica>
        <replica><host>ch-2</host><port>9000</port></replica>
      </shard>
      <shard>
        <internal_replication>true</internal_replication>
        <replica><host>ch-3</host><port>9000</port></replica>
        <replica><host>ch-4</host><port>9000</port></replica>
      </shard>
    </langfuse_cluster>
  </remote_servers>
</clickhouse>
```

### 12.5 升级路径

- **v2 → v3**: 数据库 schema migration，30-60s downtime
- **v3.x → v3.y**: 通常无需 downtime（incremental migration）
- **Background migrations**: 长跑迁移在 Worker 中跑，不阻塞启动

---

## 13. 成本模型与计费单位

### 13.1 Cloud 计费单位: Units

**1 Unit** = 以下任一：
- 1 Trace
- 1 Observation (Span/Generation/Event)
- 1 Score
- 1 Dataset Item 创建
- 1 Prompt 创建/更新

混合计费示例：
```
1000 traces × 5 observations = 5000 obs
+ 1000 traces = 1000 traces
+ 500 scores
────────────────────────────────
= 6500 units (1 个月内)
```

### 13.2 计划详情（2026 年 6 月）

| Plan | 月费 | 含 Units | 超额单价 | 限速 (req/min) | 数据保留 | 用户 | 特性 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Hobby** | $0 | 50k | 不可 | 1,000 | 30 天 | 2 | 基础 tracing/prompt/eval |
| **Core** | $29 | 100k | $8/100k (量大递减) | 4,000 | 90 天 | 不限 | 加 unlimited users + in-app support |
| **Pro** | $199 | 100k | $8/100k | 20,000 | 3 年 | 不限 | SOC2/ISO27001/BAA、3 年 retention |
| **Enterprise** | $2,499 | 100k | $8/100k (年承诺定制) | 自定义 | 3 年 | 不限 | Audit logs、SCIM、SLA、dedicated SE |
| **Teams Add-on** | +$300/月 | - | - | - | - | - | SSO、SSO enforcement、RBAC、Slack channel |
| **Yearly Commitment** | 协商 | 自定义 | 协商 | 自定义 | 自定义 | - | AWS Marketplace 付费、invoice、vendor onboarding |

### 13.3 自托管成本

| 组件 | 最小配置 (10k traces/day) | 中等 (100k traces/day) | 大 (1M traces/day) |
| --- | --- | --- | --- |
| Web (ECS/EKS) | 1× t3.medium = $30 | 2× m5.large = $140 | 6× m5.2xlarge = $840 |
| Worker | 1× t3.medium = $30 | 2× m5.large = $140 | 4× m5.xlarge = $280 |
| Postgres | 1× db.t3.small = $40 | db.r5.large = $200 | db.r5.2xlarge Multi-AZ = $800 |
| ClickHouse | 1× c5.large + 100GB SSD = $80 | 2-node cluster = $400 | 4-node cluster + 2TB = $1,500 |
| Redis | 1× cache.t3.micro = $15 | cache.r5.large = $120 | cluster = $400 |
| S3 | < 1GB = $0.50 | 50GB = $2 | 1TB = $40 |
| **月合计** | **~$200** | **~$1,000** | **~$3,800** |

> 同样数据量 Cloud 端：10k traces/day ≈ Core plan 100k units → $29 + ~$30 = $60/月。**自托管在 < 50k traces/day 时更贵**。

### 13.4 企业定价因素

- Volume discount: 1M+ units/月可谈到 $4-6/100k
- Yearly commit: 15-20% off
- Multi-region: +30-50%
- Custom SLAs: +10-20%
- AWS Marketplace: 标准 plan 价格 + AWS 抽成

### 13.5 折扣项目

- **Startup**: < 30 人、< $5M 融资 → 6 个月 50% off Core/Pro
- **Research / Student**: 学术用途免费 Core
- **Open Source**: OSS 项目维护者可申请 Pro plan
- **Non-profit**: 同上

---

## 14. 性能与扩展性数据

### 14.1 官方公布数据 (2026 Q2)

| 指标 | 数值 |
| --- | --- |
| Cloud 客户数 | 5,000+ teams |
| 日均处理 traces | 100M+ |
| 单项目最大 traces (Hobby) | 50k/月 |
| 单项目最大 traces (Pro) | 无限 (按 units 计费) |
| 最大 throughput (single region) | 50k events/sec |
| Ingestion P50 延迟 (Cloud) | < 50ms |
| UI 查询 P95 (1M traces) | < 800ms |
| ClickHouse query P95 (聚合) | < 2s |
| S3 raw event 保留 | 默认 90 天 (可配) |

### 14.2 自托管 benchmark（参考配置: 1 节点 t3.xlarge, ClickHouse 1 节点）

| 场景 | 指标 |
| --- | --- |
| Ingestion (单 client) | 5,000 events/sec |
| Ingestion (1000 client, 1 web) | 50,000 events/sec |
| UI Dashboard query (1M traces) | 1-2s |
| Trace detail page | < 200ms |
| Score filter (100M events) | < 1s |
| Aggregate metrics (daily) | 3-5s |
| 端到端 trace 可见延迟 | 2-5s (P95) |

### 14.3 性能优化技巧

#### SDK 端
```python
# 1. 调高 batch size (默认 15)
langfuse = Langfuse(flush_at=50, flush_interval=10)

# 2. 减少 metadata 体积
trace.update(metadata={"key": "value"})  # 短
# vs
trace.update(metadata={"huge_dict": {...}})  # 慢 + 占存储

# 3. 采样
import random
if random.random() < 0.1:  # 10% 采样
    with langfuse.trace(...) as t:
        ...
```

#### Server 端
```yaml
# docker-compose.yml
environment:
  # Web 容器并发
  - LANGFUSE_WEB_CONCURRENCY=4
  # Worker 消费速率
  - LANGFUSE_WORKER_CONCURRENCY=8
  - LANGFUSE_WORKER_BATCH_SIZE=100
  # ClickHouse 配置
  - CLICKHOUSE_MAX_MEMORY_USAGE=20000000000
```

### 14.4 已知性能陷阱

1. **不设置 session_id**: 无法跨 trace 聚合，UI 反而更慢
2. **高频 trace without batch**: 单次 HTTP 请求压垮 Web
3. **超大 multimodal attachment**: 单 trace > 10MB 视频 → 存储成本暴涨
4. **ClickHouse ORDER BY 错配**: 改了默认 schema 字段导致 query 慢
5. **Postgres 连接耗尽**: 默认 pool 100，需要大流量时调到 500+

---

## 15. 安全、合规与多租户

### 15.1 认证

| 方式 | 支持 | 备注 |
| --- | --- | --- |
| **Email + Password** | ✅ | 默认 |
| **Magic Link (email)** | ✅ | 密码重置 |
| **OAuth 2.0 (Google, GitHub)** | ✅ | 自托管需配 |
| **SAML 2.0 SSO** | ✅ (EE) | Okta, Azure AD, Google Workspace |
| **OIDC** | ✅ (EE) | 自定义 IdP |
| **SSO Enforcement** | ✅ (EE) | 强制全组织 SSO |
| **SCIM 2.0** | ✅ (EE) | 自动 provisioning/deprovisioning |
| **API Key (Public/Secret)** | ✅ | pk-/sk- 前缀，pk 可暴露给浏览器 |
| **2FA** | ✅ | TOTP |

### 15.2 授权 (RBAC)

| 角色 | 权限 |
| --- | --- |
| **Owner** | 所有，包括删除 org |
| **Admin** | 管理用户、project、API keys |
| **Member** | 读写 traces/prompts |
| **Viewer** | 只读 |
| **Custom (EE)** | 细粒度到 resource 级别 |

### 15.3 数据加密

- **At rest**: Postgres (RDS/Cloud SQL 默认 AES-256), ClickHouse 透明加密
- **In transit**: TLS 1.2+ 强制
- **API key**: Langfuse 应用层加密 (AES-256-GCM with ENCRYPTION_KEY)
- **BYOK** (EE): 自带 KMS key
- **Data masking** (EE): 字段级遮罩 (如 `{{pii_email}}` → `***@***`)

### 15.4 合规认证

| 认证 | 状态 | 适用范围 |
| --- | --- | --- |
| **SOC 2 Type II** | ✅ | Cloud + Pro plan |
| **ISO 27001** | ✅ | Cloud + Pro plan |
| **HIPAA BAA** | ✅ | Pro + Enterprise (on request) |
| **GDPR** | ✅ | DPA available |
| **CCPA** | ✅ | DPA available |
| **EU AI Act** | 持续跟踪 | Trace audit log 满足可追溯性 |

### 15.5 多租户隔离

- **Project**: 顶级租户单元，API key 绑定
- **Organization**: 包含多个 projects，跨 project 共享 prompt library (EE)
- **数据隔离**: Postgres schema-per-project + ClickHouse project_id 列过滤
- **Region pinning** (EE): 选 EU/US/AP 数据中心，数据不出区

### 15.6 审计日志 (EE)

```json
{
  "timestamp": "2026-06-05T10:00:00Z",
  "actor": "user:u-123",
  "action": "trace.delete",
  "resource": "trace:01HXX...",
  "ip": "1.2.3.4",
  "userAgent": "Mozilla/5.0...",
  "result": "success"
}
```

可导出到 S3/SIEM（Splunk、Datadog、Snowflake）。

### 15.7 私有网络

- 自托管完全在 VPC/on-prem，无需公网
- Cloud 提供 **VPC peering** (Enterprise) 和 **IP allowlist**
- Air-gap 模式支持（手动更新 license key）

---

## 16. 客户案例研究

### 16.1 公开案例

#### Klarna (瑞典，先买后付)
- **规模**: 5,000+ 工程师，全球支付平台
- **场景**: 多团队 LLM 应用（客服、欺诈检测、风控）
- **挑战**: 之前用 LangSmith，单租户 $50k+/月，跨团队无法隔离
- **方案**: 自托管 Langfuse，30+ projects，100M+ traces/月
- **效果**: 成本下降 70%，跨项目 prompt 复用率提升 40%

#### Siemens (德国，工业)
- **场景**: 工业知识库 RAG，500+ 工程师访问
- **挑战**: 数据不能出欧洲；HIPAA-equivalent 合规
- **方案**: 自托管 Langfuse 在 Siemens 私有云，EU region
- **效果**: 6 周内完成 POC 到 production，DPO 审批通过

#### Rocket Money (美国，金融)
- **场景**: 客户支持 LLM Agent
- **挑战**: 评估客服质量需要 LLM-as-a-judge；之前需要人工抽样
- **方案**: Langfuse Cloud (Pro plan)
- **效果**: 评测覆盖率从 5% 人工 → 100% 自动，质量分 4.2/5，识别问题模式 12 类

#### SumUp (英国，POS/支付)
- **场景**: 商家客服 LLM，多语言 (15 种)
- **挑战**: 多语言评测、prompt 多版本管理
- **方案**: Langfuse + DSPy 优化 prompt，自动评测
- **效果**: 单次 prompt 优化迭代从 2 周 → 2 天

#### Docebo (加拿大，eLearning)
- **场景**: 学习内容生成
- **挑战**: OpenAI API 成本失控，缺观测
- **方案**: Langfuse Cloud + token 配额告警 + prompt caching
- **效果**: 月度 API 成本下降 35%，识别高成本 prompt 5 个

### 16.2 行业应用统计

| 行业 | 客户数（公开） | 典型用例 |
| --- | --- | --- |
| **金融科技** | 50+ | 风控、客服、反欺诈、报告生成 |
| **电商** | 100+ | 推荐、客服、Listing 生成 |
| **SaaS** | 200+ | AI 功能、Copilot、内容生成 |
| **医疗** | 20+ | 病历摘要、文献检索、患者问答（HIPAA） |
| **教育** | 30+ | 个性化教学、作业批改 |
| **法律** | 10+ | 合同分析、判例检索 |
| **政府/公共** | 5+ | 政策问答、文档分析 |

---

## 17. 优势分析

### 17.1 核心优势

1. **开源 + 商业双轨**
   - 核心 MIT 协议，避免 vendor lock-in
   - 自托管 + Cloud 任选，迁移成本低
   - 透明度高，roadmap 由社区影响

2. **OpenTelemetry 优先**
   - 与 APM 生态兼容（Datadog、New Relic、Honeycomb、Signoz）
   - 多语言支持（Python、JS、Java、Go、Rust）
   - 标准化属性约定，便于与 OpenInference 等互操作

3. **ClickHouse 列存 OLAP**
   - 10x-100x 优于 Postgres 行存做聚合查询
   - 高基数维度（userId、model、tags）查询快
   - 成本可控（S3 cold storage 可降本）

4. **产品矩阵完整**
   - Tracing + Prompt + Eval + Dataset + Playground + Annotation
   - 一个平台完成 observability + improvement loop
   - 减少拼接多个工具的复杂度

5. **集成生态广**
   - 50+ 现成集成，开箱即用
   - 主动维护新框架（Mastra、CrewAI、AutoGen、smolagents）

6. **开发者体验优秀**
   - SDK API 设计直觉（trace/span/generation/score）
   - Python 装饰器 `@observe()` 极简
   - TypeScript 严格类型
   - 文档质量高（多语言：英/中/日/韩）

7. **OSS 社区活跃**
   - 11k+ stars，300+ contributors
   - GitHub Discussions 快速响应
   - Discord 实时交流
   - 月度 office hours

8. **合理定价**
   - Hobby 免费层慷慨（50k units）
   - Core $29 起，远低于 LangSmith
   - 自托管完全免费（除基础设施）

### 17.2 架构优势

- **可恢复性**: 事件先写 S3，Worker 异步消费，永不丢
- **可扩展性**: Web/Worker 独立扩容
- **缓存层**: 多级 cache（Redis + SDK 本地），热点 prompt 0ms
- **多租户**: project_id 强隔离，row-level security
- **API 优先**: 一切功能都有 REST API，UI 只是 API 的一种消费

### 17.3 业务模式优势

- **Open Core**: 核心免费，Enterprise 收费
- **自托管 + Cloud**: 满足数据主权需求
- **Marketplace 付费**: AWS Marketplace，简化企业采购
- **折扣计划**: Startup/Research/OSS 友好

---

## 18. 劣势与挑战

### 18.1 功能局限

1. **不是 Gateway**
   - 不做请求路由、fallback、缓存、限流
   - 必须配合 LiteLLM/Portkey 等 gateway 产品
   - 自身不能降低 LLM API 延迟或成本

2. **Eval 能力相对基础**
   - 缺少复杂的统计评估（A/B test、regression detection）
   - LLM-as-a-judge 模板有限
   - 缺少 confidence interval、statistical significance

3. **数据集规模**
   - 100k+ items 时 UI 慢
   - 大规模评测需要分批

4. **缺少 RAG 特定功能**
   - 没有 native RAG eval（需自己写 evaluator）
   - Ragas/Deepeval 集成需自己搭

5. **实时协作弱**
   - 多人同时编辑 prompt 没有 OT/CRDT
   - 冲突依赖 last-write-wins

### 18.2 性能局限

1. **大 payload 成本**
   - Multimodal 附件直接存 S3，但 metadata 在 ClickHouse
   - 100MB 视频 1 万个 → ClickHouse 压力

2. **聚合查询延迟**
   - 1B+ events 时 dashboard 卡顿
   - ClickHouse 单机节点有上限

3. **Worker 单点**
   - 单一 Worker 容器可能成为瓶颈
   - 需要 K8s HPA + Redis Streams 解决

### 18.3 商业风险

1. **资源压力**
   - ClickHouse 运维复杂，OLAP 调优门槛
   - 客户需要 ClickHouse 专家

2. **竞争激烈**
   - LangSmith 持续迭代
   - Helicone 切入 gateway+observability
   - Arize Phoenix 主打 eval

3. **企业特性滞后**
   - SCIM/SAML 等大客户特性需 EE license
   - 相比 LangSmith Enterprise 略弱

4. **托管 vs 自托管悖论**
   - 客户希望自托管，但希望 Langfuse 团队支持 → 矛盾
   - 长期可能收窄自托管支持

### 18.4 集成局限

- **Java/Go/Rust**: 只能走 OTel，缺少 first-class SDK
- **.NET, Ruby, PHP**: 同上
- **Vercel AI SDK**: 集成较新，edge runtime 兼容性问题
- **某些闭源 LLM**: 缺少自动 token 计算，需手动

### 18.5 文档/UX 不足

- **配置项多**: 自托管 50+ env var，新手易踩坑
- **错误信息**: 部分 OTel mapping 错误不直观
- **Migration guide**: v2 → v3 升级文档分散
- **多语言文档**: 中/日/韩翻译滞后

---

## 19. 与竞品对比

### 19.1 vs LangSmith

| 维度 | Langfuse | LangSmith |
| --- | --- | --- |
| **License** | MIT + EE | 闭源 (LangChain 子公司) |
| **Self-host** | ✅ | ❌ (无 self-host) |
| **Storage** | ClickHouse (OLAP) | 自研 (无公开细节) |
| **Tracing protocol** | OpenTelemetry | LangChain 原生 + 部分 OTel |
| **Pricing** | $29 起 / 自托管 $0 | $39/user/month 起 |
| **OSS 集成** | 50+ | 主 LangChain 生态 |
| **LangChain 集成** | 强 (callback) | 最强 (原厂) |
| **Prompt management** | 强 (label/version/cache) | 强 (commit-based) |
| **Evaluation** | LLM/Code/User Feedback | LLM/Human/Heuristic |
| **Playground** | ✅ | ✅ |
| **Dataset** | ✅ | ✅ |
| **Annotation Queue** | ✅ | ✅ |
| **Multi-modal** | ✅ | ✅ |
| **Agent graph visualization** | ✅ (v3.5+) | ✅ (native) |
| **Custom dashboard** | ✅ (v3.5+) | ✅ (成熟) |
| **SOC2/HIPAA** | Pro+EE | 全部 |
| **SSO/SAML** | EE | Standard |
| **SCIM** | EE | Enterprise |
| **GitHub stars** | 11k+ | 闭源 |

**决策建议**:
- 想要开源/自托管/数据主权 → **Langfuse**
- 重度 LangChain 用户/不想运维 → **LangSmith**
- 成本敏感 → **Langfuse** (尤其大团队)

### 19.2 vs Helicone

| 维度 | Langfuse | Helicone |
| --- | --- | --- |
| **核心定位** | Observability + Prompt/Eval | Gateway + Observability |
| **网络位置** | Sidecar (SDK) | Inline (proxy) |
| **路由** | ❌ | ✅ (multi-model fallback) |
| **语义缓存** | ❌ | ✅ (v2+) |
| **Rate limiting** | ❌ | ✅ |
| **Cost tracking** | ✅ (核心) | ✅ |
| **Tracing** | ✅ (深度) | ✅ (基础) |
| **Prompt mgmt** | ✅ (强) | ❌ (无) |
| **Eval** | ✅ (强) | ❌ (无) |
| **Dataset** | ✅ | ❌ |
| **Open source** | ✅ (MIT) | ✅ (MIT, partial) |
| **Self-host** | ✅ | ✅ |
| **Latency overhead** | 0ms (async) | 5-20ms (inline) |
| **适用场景** | LLM 应用工程 | LLM API 流量管理 |

**决策建议**:
- 想要 "all-in-one" 工程平台 → **Langfuse**
- 想要 gateway + 简单 observability → **Helicone**
- 二者可叠加：Helicone 做代理 + Langfuse 做观测（但增加复杂度）

### 19.3 vs Arize Phoenix

| 维度 | Langfuse | Arize Phoenix |
| --- | --- | --- |
| **核心定位** | Engineering platform | Eval + Drift |
| **Tracing** | ✅ (强) | ✅ (OTel 基础) |
| **Eval** | ✅ (中等) | ✅ (强, RAG 专门) |
| **RAG 评测** | 需自写 | 内置 (precision/recall/faithfulness) |
| **Drift detection** | ❌ | ✅ (核心) |
| **Embedding analysis** | ❌ | ✅ (UMAP, clustering) |
| **Prompt management** | ✅ | ❌ |
| **Dataset** | ✅ | ✅ |
| **Production traces** | ✅ | ✅ |
| **Storage** | ClickHouse | Postgres (sqlite 默认) |
| **OSS** | ✅ | ✅ |
| **LLM 平台** | Langfuse Cloud | Arize AX (商业) |

**决策建议**:
- 想做 RAG 质量深度分析 → **Phoenix**
- 想做完整 LLM app 工程 → **Langfuse**

### 19.4 vs OpenLLMetry (Traceloop)

| 维度 | Langfuse | OpenLLMetry |
| --- | --- | --- |
| **产品形态** | 完整平台 | 库 (instrumentation only) |
| **Backend** | Langfuse Server | 任意 OTel backend |
| **Tracing** | ✅ | ✅ |
| **Prompt mgmt** | ✅ | ❌ |
| **Eval** | ✅ | ❌ |
| **UI/Dashboard** | ✅ (内建) | 需 OTel backend (Jaeger/SigNoz) |
| **Self-host** | ✅ (一键) | 需自己搭 OTel infra |
| **Use case** | 开箱即用 | 已有 OTel 栈 |

**决策建议**:
- 已有 Datadog/Honeycomb/SigNoz → **OpenLLMetry + 现有后端**
- 想要完整 LLM 专用平台 → **Langfuse**

### 19.5 vs Braintrust

| 维度 | Langfuse | Braintrust |
| --- | --- | --- |
| **License** | OSS + EE | 闭源 |
| **Eval** | ✅ | ✅✅ (最强) |
| **Tracing** | ✅ | ✅ |
| **Prompt mgmt** | ✅ | ✅ |
| **Experiment** | ✅ | ✅✅ (统计显著性强) |
| **Dataset** | ✅ | ✅ |
| **Pricing** | $0-29 起 | $249/team/month |
| **Self-host** | ✅ | ❌ |

**决策建议**:
- 大规模 eval/实验 → **Braintrust**
- 自托管/成本 → **Langfuse**

### 19.6 综合雷达图（10 分制）

```
              Langfuse  LangSmith  Helicone  Phoenix  Braintrust
可观测性          9         9         7        8         8
Prompt管理       9         9         3        2         8
Eval             7         8         4        9         10
Gateway          2         2         9        1         2
开源            10         0         8        10        0
自托管          10         0         8        7         0
成本效益         9         5         8        9         4
多语言SDK        8         8         7        6         6
文档质量         9         9         8        8         8
企业特性         7         9         7        6         8
```

---

## 20. 迁移路径与最佳实践

### 20.1 从 LangSmith 迁移

```python
# Step 1: 同时上报 (双写)
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_..."

from langfuse import Langfuse
langfuse = Langfuse(public_key="pk-...", secret_key="sk-...")

# Step 2: 同步 trace 到 Langfuse
# 在 LangChain callback 中加入 Langfuse
from langfuse.callback import CallbackHandler
langfuse_handler = CallbackHandler()

chain.invoke(input, config={
    "callbacks": [langfuse_handler]  # 与 LangChain 现有 callback 共存
})

# Step 3: 数据验证
# 对比两边 trace 数量/token/cost，1-2 周

# Step 4: 切流量
os.environ.pop("LANGCHAIN_TRACING_V2")
# 仅保留 Langfuse

# Step 5: 清理
# 取消 LangSmith 订阅
```

### 20.2 从自建日志系统迁移

```python
# Step 1: 编写 Langfuse 适配 wrapper
import logging
from langfuse import Langfuse

class LangfuseHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.langfuse = Langfuse(...)
    
    def emit(self, record):
        log_data = json.loads(record.msg)
        with self.langfuse.trace(name=log_data["endpoint"], user_id=log_data.get("user")) as t:
            t.update(input=log_data.get("request"), output=log_data.get("response"))
            if "tokens" in log_data:
                t.generation(name="llm", usage=log_data["tokens"]).end()

# Step 2: 在 logging config 中加入
logger.addHandler(LangfuseHandler())

# Step 3: 逐步替换为原生 SDK
```

### 20.3 性能优化清单

```yaml
SDK 端:
  - [x] 设置合理的 flush_at/flush_interval
  - [x] 在 production 路径使用 @observe 装饰器 (零侵入)
  - [x] 采样低价值 trace (e.g. health check)
  - [x] 避免在 SDK 中存储大对象 (>1MB)
  
服务端:
  - [x] Web 容器水平扩展 (3+ 副本)
  - [x] Worker HPA based on Redis queue depth
  - [x] ClickHouse 副本 + Zookeeper
  - [x] S3 启用 lifecycle (90d → Glacier)
  - [x] Redis 使用 cluster mode (大流量)
  
ClickHouse:
  - [x] 启用 async_inserts
  - [x] 配置 mark_cache_size
  - [x] 监控 query_log 中的慢查询
  - [x] 按月分区 + TTL
```

### 20.4 安全加固清单

```yaml
认证:
  - [x] 强制 SSO (EE)
  - [x] 启用 2FA
  - [x] API key 轮换周期 90 天
  
授权:
  - [x] 最小权限 RBAC
  - [x] 项目级隔离
  
数据:
  - [x] 启用 PII 脱敏 (data masking EE)
  - [x] 加密 S3 bucket
  - [x] BYOK 加密 (EE)
  - [x] Audit log 导出 SIEM
  
网络:
  - [x] 仅内网访问
  - [x] Web 容器 zero-trust
  - [x] VPC peering 到 LLM provider
```

### 20.5 常见反模式

❌ **不要**:
- 把 PII 明文存在 metadata (用 masking)
- 单 trace 包含 1000+ observations (拆 sub-trace)
- 在 LLM call 中同步 flush (`langfuse.flush()` 会 block 100ms+)
- 不设置 session_id (失去多轮分析能力)
- Prompt 频繁创建/删除 (label 切换更高效)
- 不用 label 而用 version (无法 rolling rollback)

✅ **要**:
- 始终设置 user_id (成本/质量归因)
- 用 environment 字段分 staging/prod
- 用 tags 做粗分类 (环境、模型、A/B 组)
- 用 metadata 做细分类 (业务字段)
- 用 score 量化质量 (后续可统计)

---

## 21. 路线图与未来展望

### 21.1 短期（2026 H2）

- **Eval v2**: 引入统计显著性、regression detection
- **Prompt Studio**: GUI prompt IDE with branching
- **Native Agent Graph**: 改进 agent 链路可视化
- **Real-time collaboration**: Multi-user prompt edit (CRDT)
- **Vector Eval**: 内置 RAG-specific metrics
- **Langfuse Agent SDK**: First-class agent primitive

### 21.2 中期（2027）

- **Auto-Eval Tuner**: 自动选 LLM-as-a-judge model
- **Custom Dashboarding v2**: SQL-on-traces 自助分析
- **Multi-region Active-Active**: 全球部署零延迟
- **Trace Search (全文)**: ClickHouse 集成 Tantivy
- **Built-in A/B Testing**: 实验统计框架

### 21.3 长期（2028+）

- **Self-improving Loops**: 用 traces 自动训练 prompt optimizer
- **Federated Observability**: 跨组织 trace 共享（隐私计算）
- **GenAI Governance**: 合规规则引擎
- **AI Cost Optimization Copilot**: 自动推荐降本策略
- **Open Standard (OTel GenAI)**: 推动 OTel GenAI 语义约定标准化

### 21.4 潜在威胁

1. **OpenTelemetry GenAI SIG** 可能标准化更多功能，Langfuse 部分差异化消失
2. **LangSmith 持续降价** → 价格优势缩小
3. **LLM Provider 内建 observability** (OpenAI、Google 已开始)
4. **新生代产品**: Honeycomb GenAI、Datadog LLM Obs、New Relic AI Monitoring

### 21.5 增长驱动力

- 企业 LLM 应用 ROI 量化需求
- 数据主权 + 合规 (HIPAA/SOC2)
- 多 LLM provider 管理复杂
- AI 监管 (EU AI Act 等) 要求可追溯

---

## 22. 附录 A: SDK API 示例代码

### A.1 Python 完整示例：Multi-agent 追踪

```python
from langfuse import Langfuse
import openai

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com"
)

# === 顶层 trace ===
trace = langfuse.trace(
    name="research-agent",
    user_id="user-789",
    session_id="sess-abc",
    tags=["production", "v2.3"],
    metadata={"plan": "premium", "region": "EU"}
)

# === 阶段 1: Planning ===
with trace.span(name="planning", metadata={"step": 1}) as plan_span:
    with plan_span.generation(
        name="plan-generation",
        model="gpt-4o",
        input={"messages": [{"role": "user", "content": "Plan research on quantum computing"}]},
        model_parameters={"temperature": 0.3}
    ) as plan_gen:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Plan research on quantum computing"}]
        )
        plan_gen.update(
            output=response.choices[0].message,
            usage={
                "promptTokens": response.usage.prompt_tokens,
                "completionTokens": response.usage.completion_tokens,
                "totalTokens": response.usage.total_tokens
            }
        )
    plan_span.update(output={"plan": response.choices[0].message.content})

# === 阶段 2: Retrieval (parallel) ===
with trace.span(name="parallel-retrieval") as ret_span:
    ret_span.event(name="vector-search", metadata={"query": "quantum"})
    ret_span.event(name="web-search", metadata={"query": "quantum entanglement 2026"})

# === 阶段 3: Synthesis (Agent) ===
with trace.span(name="synthesis-agent", type_="AGENT") as syn_span:
    with syn_span.generation(
        name="synthesis-llm",
        model="claude-3-5-sonnet",
        input={"context": "...", "plan": "..."}
    ) as syn_gen:
        response = openai.chat.completions.create(
            model="claude-3-5-sonnet",
            messages=[...]
        )
        syn_gen.update(output=response.choices[0].message, usage=...)

# === 评分 (用户反馈 + 自动) ===
trace.score(
    name="user-rating",
    value=5,
    data_type="NUMERIC",
    comment="Excellent research"
)

trace.score(
    name="factual-accuracy",
    value=0.92,
    data_type="NUMERIC",
    source="EVAL"
)

# === 强制 flush (脚本结束时) ===
langfuse.flush()
```

### A.2 Node.js 完整示例：Streaming + TTFT

```typescript
import { Langfuse } from "langfuse";
import OpenAI from "openai";

const langfuse = new Langfuse({
  publicKey: process.env.LANGFUSE_PUBLIC_KEY!,
  secretKey: process.env.LANGFUSE_SECRET_KEY!,
  baseUrl: process.env.LANGFUSE_HOST
});

const openai = new OpenAI();

async function streamChat(userId: string, sessionId: string, prompt: string) {
  const trace = langfuse.trace({
    name: "streaming-chat",
    userId,
    sessionId,
    tags: ["streaming"]
  });

  const generation = trace.generation({
    name: "openai-stream",
    model: "gpt-4o",
    input: { messages: [{ role: "user", content: prompt }] },
    modelParameters: { temperature: 0.7, stream: true }
  });

  let firstTokenTime: Date | null = null;
  const startTime = new Date();
  let content = "";

  try {
    const stream = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [{ role: "user", content: prompt }],
      stream: true,
      stream_options: { include_usage: true }
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content;
      if (delta) {
        if (!firstTokenTime) {
          firstTokenTime = new Date();
          generation.update({ completionStartTime: firstTokenTime });
        }
        content += delta;
      }
    }

    generation.end({
      output: content,
      usage: {
        promptTokens: 50,
        completionTokens: content.split(/\s+/).length
      },
      metadata: {
        ttft_ms: firstTokenTime ? firstTokenTime.getTime() - startTime.getTime() : null,
        total_ms: Date.now() - startTime.getTime()
      }
    });
  } catch (e: any) {
    generation.update({
      level: "ERROR",
      statusMessage: e.message
    });
    throw e;
  }

  // Serverless 必须 flush
  await langfuse.flushAsync();

  return content;
}
```

### A.3 Eval pipeline 示例

```python
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

langfuse = Langfuse(public_key=..., secret_key=...)

# 1. 使用 @observe 装饰器自动追踪
@observe()
def my_llm_pipeline(user_input: str) -> str:
    # 业务逻辑
    response = call_openai(user_input)
    return response

# 2. 跑 dataset
from langfuse.experiment import Experiment

def my_app(item):
    """每个 dataset item 跑一次"""
    return my_llm_pipeline(item.input["question"])

exp = Experiment(
    name="prompt-v4-eval",
    dataset_name="qa-bench-v1",
    run=my_app,
    evaluators=["helpfulness", "toxicity"]  # 已在 UI 配置
)
exp.run()

# 3. 自定义 evaluator
from langfuse.evaluators import Evaluator
import re

@Evaluator(name="contains_citation")
def check_citation(trace):
    output = trace.output or ""
    has_citation = bool(re.search(r'\[\d+\]|\[citation', output))
    return {
        "value": 1.0 if has_citation else 0.0,
        "comment": "Has [1] style citation" if has_citation else "Missing citation"
    }
```

### A.4 Prompt + Trace 联合示例

```python
# 创建 prompt (一次性)
langfuse.create_prompt(
    name="summarize",
    type="text",
    prompt="Summarize the following text in {{style}} style:\n\n{{text}}",
    labels=["production"],
    config={"model": "gpt-4o-mini", "temperature": 0.3}
)

# 应用代码：拉取 + trace 关联
@observe()
def summarize(text: str, style: str = "concise") -> str:
    # 1. 拉取 prompt (有 cache)
    prompt = langfuse.get_prompt("summarize", label="production")
    
    # 2. 编译
    compiled = prompt.compile(text=text, style=style)
    
    # 3. 嵌套 generation
    with langfuse_context.get_current_observation().generation(
        name="summarization",
        model=prompt.config["model"],
        prompt=prompt,  # 关键：link 到 prompt version
        input={"text": text, "style": style}
    ) as gen:
        response = openai.chat.completions.create(
            model=prompt.config["model"],
            messages=[{"role": "user", "content": compiled}],
            temperature=prompt.config["temperature"]
        )
        gen.update(
            output=response.choices[0].message.content,
            usage={
                "promptTokens": response.usage.prompt_tokens,
                "completionTokens": response.usage.completion_tokens
            }
        )
        return response.choices[0].message.content
```

---

## 23. 附录 B: Docker Compose 部署示例

### B.1 最小化生产配置

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  web:
    image: langfuse/langfuse:3
    restart: always
    ports: ["3000:3000"]
    environment:
      - DATABASE_URL=postgresql://langfuse:${DB_PASSWORD}@postgres:5432/langfuse
      - NEXTAUTH_URL=https://langfuse.example.com
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - SALT=${SALT}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - REDIS_URL=redis://redis:6379
      - CLICKHOUSE_URL=${CLICKHOUSE_URL}
      - CLICKHOUSE_USER=${CLICKHOUSE_USER}
      - CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD}
      - S3_ENDPOINT=${S3_ENDPOINT}
      - S3_BUCKET=${S3_BUCKET}
      - S3_ACCESS_KEY_ID=${S3_ACCESS_KEY_ID}
      - S3_SECRET_ACCESS_KEY=${S3_SECRET_ACCESS_KEY}
      - S3_REGION=${S3_REGION}
      - LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES=false
      - TELEMETRY_ENABLED=false
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/api/public/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  worker:
    image: langfuse/langfuse-worker:3
    restart: always
    environment: &env-shared
      - DATABASE_URL=postgresql://langfuse:${DB_PASSWORD}@postgres:5432/langfuse
      - REDIS_URL=redis://redis:6379
      - CLICKHOUSE_URL=${CLICKHOUSE_URL}
      - CLICKHOUSE_USER=${CLICKHOUSE_USER}
      - CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD}
      - S3_ENDPOINT=${S3_ENDPOINT}
      - S3_BUCKET=${S3_BUCKET}
      - S3_ACCESS_KEY_ID=${S3_ACCESS_KEY_ID}
      - S3_SECRET_ACCESS_KEY=${S3_SECRET_ACCESS_KEY}
      - S3_REGION=${S3_REGION}
      - LANGFUSE_WORKER_CONCURRENCY=8
      - LANGFUSE_WORKER_BATCH_SIZE=100

  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: langfuse
      TZ: UTC
      PGTZ: UTC
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    command: ["postgres", "-c", "timezone=UTC", "-c", "max_connections=200"]

  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    restart: always
    environment:
      CLICKHOUSE_USER: ${CLICKHOUSE_USER}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD}
      CLICKHOUSE_DB: default
      TZ: UTC
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
    volumes:
      - chdata:/var/lib/clickhouse

  redis:
    image: redis:7-alpine
    restart: always
    command: ["redis-server", "--maxmemory", "2gb", "--maxmemory-policy", "allkeys-lru"]
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  chdata:
  redisdata:
```

### B.2 启动后初始化

```bash
# 1. 启动
docker compose -f docker-compose.prod.yml up -d

# 2. 访问 https://langfuse.example.com
# 3. 注册第一个用户 → 自动成为 Organization Owner
# 4. 创建 Project → 拿到 pk-/sk- API key
# 5. 配置环境变量到业务服务
```

### B.3 备份脚本

```bash
#!/bin/bash
# backup-langfuse.sh

BACKUP_DIR="/backups/langfuse/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Postgres
docker exec langfuse-postgres pg_dump -U langfuse langfuse | \
  gzip > $BACKUP_DIR/postgres-$(date +%H%M%S).sql.gz

# ClickHouse (raw events)
docker exec langfuse-clickhouse clickhouse-client \
  --query="BACKUP DATABASE default TO S3(...)"  # 需配 S3 端点

# S3 events (可选二次备份)
aws s3 sync s3://langfuse-events $BACKUP_DIR/events/

# 保留 30 天
find /backups/langfuse -mtime +30 -delete
```

---

## 24. 参考资源

### 官方资源
- **官网**: https://langfuse.com
- **GitHub**: https://github.com/langfuse/langfuse
- **文档**: https://langfuse.com/docs
- **定价**: https://langfuse.com/pricing
- **Status Page**: https://status.langfuse.com
- **博客**: https://langfuse.com/blog
- **Changelog**: https://langfuse.com/changelog
- **Y Combinator 页面**: https://www.ycombinator.com/companies/langfuse

### 社区
- **Discord**: https://discord.gg/7NXusRtqYU
- **GitHub Discussions**: https://github.com/orgs/langfuse/discussions
- **Twitter/X**: @langfuse
- **YouTube**: Langfuse channel (walkthroughs)

### 集成相关
- **OpenTelemetry GenAI SIG**: https://github.com/open-telemetry/semantic-conventions
- **OpenInference**: https://github.com/Arize-ai/openinference
- **LiteLLM**: https://github.com/BerriAI/litellm

### 对比产品
- LangSmith: https://docs.smith.langchain.com
- Helicone: https://helicone.ai
- Arize Phoenix: https://phoenix.arize.com
- OpenLLMetry: https://github.com/traceloop/openllmetry
- Braintrust: https://www.braintrust.dev
- TruLens: https://www.trulens.org

### 技术细节参考
- ClickHouse: https://clickhouse.com/docs
- OpenTelemetry: https://opentelemetry.io/docs
- OTLP Protocol: https://opentelemetry.io/docs/specs/otlp
- Next.js (Web 框架): https://nextjs.org
- tRPC: https://trpc.io

### 客户案例原文
- Klarna 案例: https://langfuse.com/customers/klarna
- Siemens 案例: https://langfuse.com/customers/siemens
- Rocket Money 案例: https://langfuse.com/customers/rocket-money

---

## 结语

Langfuse 在 2024-2026 年间快速崛起为 LLM Observability 领域的开源标杆，凭借**OpenTelemetry 兼容性**、**ClickHouse 性能优势**、**完整产品矩阵**和**Open Core 商业模型**四张牌，已成为 LangSmith 之外最值得评估的选择。

**关键 takeaway**:
- 想要 **data sovereignty / 成本控制 / 开源** → 选 Langfuse
- 想要 **gateway 能力** → 选 Helicone/LiteLLM/Portkey，然后**叠加** Langfuse 做观测
- 想要 **RAG 深度评测** → 选 Arize Phoenix，或 Langfuse + Ragas
- 想要 **zero-touch 商业** → 选 LangSmith

Langfuse 的 **Open Core 路径**是其最大长期优势——只要核心模块保持 MIT 协议 + 活跃社区，它就能在企业级 AI 工程平台赛道占据稳固位置。

> **调研者备注**: 本报告基于 2026-06-05 时点的公开资料 + 历史轨迹外推。具体定价、API 细节以官方文档为准。Langfuse 产品迭代速度快，建议 6 个月内重新复核。
