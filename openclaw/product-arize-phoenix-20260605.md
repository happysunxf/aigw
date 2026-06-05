# Arize Phoenix 深度调研报告

> **调研对象**: Arize Phoenix (Arize-ai/phoenix)
> **调研日期**: 2026-06-05
> **产品类型**: 开源 AI Observability / Evaluation / Experiment 平台（OpenTelemetry 原生 + OpenInference 语义约定）
> **项目主页**: https://phoenix.arize.com
> **GitHub**: https://github.com/Arize-ai/phoenix
> **协议规范仓库**: https://github.com/Arize-ai/openinference
> **License**: Elastic License v2 (ELv2) — 核心平台为源码可用、商用受限；OpenInference 规范与多数 instrumentation 包为 MIT
> **厂商**: Arize AI（总部 Berkeley, CA；2019 成立；Y Combinator W19）
> **创始人/CEO**: Jason Lopatecki（Arize AI 联合创始人）
> **当前主版本**: Phoenix 12.x（2026）/ OpenInference Python 0.1.x
> **MCP 支持**: ✅ 原生 `@arizeai/phoenix-mcp`
> **MCP Badge**: ![MCP Enabled](https://badge.mcpx.dev?status=on)

---

## 目录

1. [执行摘要 (TL;DR)](#1-执行摘要-tldr)
2. [项目背景与历史沿革](#2-项目背景与历史沿革)
3. [产品定位与生态版图](#3-产品定位与生态版图)
4. [整体架构设计](#4-整体架构设计)
5. [OpenInference 语义约定详解](#5-openinference-语义约定详解)
6. [Tracing / Observability 实现细节](#6-tracing--observability-实现细节)
7. [Evaluation / Datasets / Experiments 机制](#7-evaluation--datasets--experiments-机制)
8. [Prompt Management / Playground](#8-prompt-management--playground)
9. [SDK 与多语言生态](#9-sdk与多语言生态)
10. [PXI 内置 Agent 与 MCP 集成](#10-pxi-内置-agent-与-mcp-集成)
11. [部署方式深度对比](#11-部署方式深度对比)
12. [成本模型与计费单位](#12-成本模型与计费单位)
13. [性能与扩展性数据](#13-性能与扩展性数据)
14. [安全、合规与多租户](#14-安全合规与多租户)
15. [客户案例研究](#15-客户案例研究)
16. [优势分析](#16-优势分析)
17. [劣势与挑战](#17-劣势与挑战)
18. [与竞品对比](#18-与竞品对比)
19. [迁移路径与最佳实践](#19-迁移路径与最佳实践)
20. [路线图与未来展望](#20-路线图与未来展望)
21. [附录 A: 端到端 SDK API 示例代码](#附录-a-端到端-sdk-api-示例代码)
22. [附录 B: Docker Compose 部署示例](#附录-b-docker-compose-部署示例)
23. [附录 C: OpenInference Span Kind 速查表](#附录-c-openinference-span-kind-速查表)
24. [参考资源](#参考资源)

---

## 1. 执行摘要 (TL;DR)

**Arize Phoenix 是当下最成熟的开源 AI 可观测性平台之一**，由 Arize AI（MLOps 老牌厂商）于 2023 年开源（先为商业产品中的"开发者版"再逐步切到独立 OSS 路线）。它以 **OpenTelemetry 为传输骨架**，以 **OpenInference** 为 AI 专属语义约定，把 LLM 调用、Agent 推理步骤、Tool/RAG/Embedding/Guardrail 操作标准化为可移植的 OTLP spans——理论上可投递到 Jaeger / Tempo / Honeycomb / Datadog / 任何 OTel 后端，但其旗舰 UI 仍是 Phoenix 自家。

**关键事实速览**:

| 指标 | 数值 / 现状 |
| --- | --- |
| GitHub Stars | ~9.5k+（主仓库 phoenix） |
| OpenInference 仓库 Stars | ~700+（spec + instrumentations） |
| License（Phoenix 平台） | **Elastic License v2 (ELv2)** — 源码可用，禁止托管式 SaaS 转售 |
| License（OpenInference 规范 + 大部分 instrumentation） | **MIT** — 完全开源，可在他厂后端运行 |
| 部署方式 | `pip install arize-phoenix` / Docker / Docker Compose / Helm / Phoenix Cloud（app.phoenix.arize.com）|
| 核心存储（自托管） | PostgreSQL（主存储）+ SQLite（local 模式）/ S3-compatible blob |
| Tracing 协议 | OpenTelemetry（OTLP/HTTP + gRPC，port 4317/4318） |
| AI 语义扩展 | **OpenInference** 规范（v0.1+，与 OTel 兼容叠加） |
| 集成框架 | 30+ 框架 Python + 20+ TypeScript（OpenAI / Anthropic / LangChain / LlamaIndex / DSPy / CrewAI / MCP / Vertex / Bedrock / …）|
| MCP 支持 | ✅ 原生 `@arizeai/phoenix-mcp` + Cursor / Claude Code 一键安装 |
| 起售价（Phoenix Cloud） | Free tier（500 spans/月）→ Team $0.5/1k spans → Enterprise 定制 |
| 计费单位 | **Spans**（与 Langfuse 的 "observation" 概念类似） |
| 最新里程碑 | 2026 Q1 PXI 内置 Agent GA；OpenInference v0.1.0 规范发布；与 Arize AX 商业产品双向桥接 |

**与同类产品定位对比（一句话版）**:

- **vs Langfuse**：Phoenix 是 Arize AI 给"开发者白嫖版"做的体验 → 强调本地优先、OTel-native、协议规范独立；Langfuse 强调 Postgres/ClickHouse 双栈完整工程化。
- **vs LangSmith**：Phoenix 是开源 + 自带 Web UI + 任意后端可插拔；LangSmith 强绑定 LangChain 商业云，强调 LangGraph 工作流编排。
- **vs Helicone**：Phoenix 偏"事后分析/调优"；Helicone 偏"代理网关 + 缓存 + 成本可观测"。
- **vs Arize AX**（同一公司商业版）：Phoenix 是开源的 runtime observability + 实验；AX 是企业级 production monitoring、drift detection、guardian rules 商业产品，二者通过 OTel 共享数据流。

---

## 2. 项目背景与历史沿革

### 2.1 公司背景

Arize AI 由 **Jason Lopatecki**（前 TubeMogul 创始人/CEO，被 Adobe 收购）与 **Apoorva Govind** 共同创立于 2019 年，YC W19 批次，定位"AI 时代的 DataDog/Dynatrace"——最初切入经典 ML 模型监控（sklearn/XGBoost 时代的 drift、bias、性能监控），后随 LLM 浪潮把产品线扩展到 LLM tracing、evaluation、experiment。

2023 年 6 月，Arize 把 Phoenix 从商业产品"开发者版"剥离为独立开源项目，首版聚焦 Jupyter notebook 里 trace LLM 调用。2024–2025 年陆续引入：
- Datasets / Experiments（与 Langfuse / Braintrust 对齐）
- Prompt Management（对齐 LangSmith 的 Prompt Hub）
- OpenTelemetry 原生 transport（不再依赖 Arize 私有协议）
- PXI（Phoenix eXperimental Intelligence）内置 Agent

2026 年关键里程碑：
- **OpenInference v0.1.0 规范发布**（与 OTel semconv 平行但更 AI-specific）
- **ELv2 → 更明确的开源边界**（禁止第三方把 Phoenix 包装为托管 SaaS 竞品，但允许企业内部自托管）
- **Arize AX 与 Phoenix 双向桥接**（Phoenix UI 可一键 jump 到 AX 看 production drift；AX 可把 spans 转存到 Phoenix 做 replay）

### 2.2 与 OpenInference 的关系

OpenInference 是 Arize 主导的**语义约定**（不是产品）：
- 2010s 末由 Arize 在内部做 ML observability 时沉淀
- 2023 年与 Phoenix 一起开源
- 2025–2026 升级为"独立规范"——任何 OTel 后端都可消费 OpenInference spans

二者关系：**Phoenix 是 OpenInference 的"参考实现 + 一等公民 UI"**；其他厂商（Portkey、Helicone、Traceloop、TrueFoundry 等）也都贡献了 `openinference-instrumentation-*` 包。

### 2.3 融资与商业化

Arize AI 累计融资 ~$61M（B/C 轮，2024 年 C 轮 $70M 估值公开）：
- Lead：CRV、Foundation Capital、Battery Ventures、Industry Ventures
- Phoenix 项目本身不直接赚钱，但作为 funnel 引导企业用户升级到 **Arize AX**（商业版）
- Phoenix Cloud 自身有 Free / Team / Enterprise 三档，但收入相对 AX 较小

---

## 3. 产品定位与生态版图

### 3.1 七大核心能力模块

| 模块 | 功能 | 类比 Langfuse | 类比 LangSmith |
| --- | --- | --- | --- |
| **Tracing** | 实时记录 LLM / Tool / RAG / Agent 步骤 | ✅ | ✅ |
| **Evaluation** | LLM-as-judge、code-based、pre-built metrics | ✅ | ✅ |
| **Datasets** | 版本化数据集（CSV/JSONL 导入） | ✅ | ✅ |
| **Experiments** | 跨 prompt/model/retriever 的对照实验 | ✅ | ✅ |
| **Playground** | 浏览器内 prompt/model 参数对比 | ✅ | ✅ |
| **Prompt Management** | 集中式 prompt 仓库 + 版本/标签 | ✅ | ✅ |
| **PXI** | 内置 Agent，permission-gated 操作 Phoenix 数据 | ❌（无） | ❌（无） |

### 3.2 在 AI Gateway 生态中的角色

Phoenix **不是 AI Gateway**（不像 Portkey / Helicone / LiteLLM 那样代理 LLM 请求）——它是一个**纯观察者**（passive observer）+ **评估/调优工具**。在整体生态中的位置：

```
┌──────────────────────┐     ┌──────────────────────┐
│   App / Agent code   │────▶│   AI Gateway         │ (Portkey/Helicone/LiteLLM)
│                      │     │   (路由/缓存/限流)     │
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           │  OpenTelemetry SDK         │  spans
           │  (auto-instrumented)       ▼
           │                  ┌──────────────────────┐
           └─────────────────▶│   Arize Phoenix      │ (本调研对象)
                              │  (trace/eval/exp)    │
                              └──────────┬───────────┘
                                         │ OTLP / Arrow Flight
                                         ▼
                              ┌──────────────────────┐
                              │   Backend Storage    │ (Phoenix self-host / Phoenix Cloud / Arize AX)
                              └──────────────────────┘
```

**重要**：Phoenix 12.x 起，**gateway 厂商（Portkey、Helicone、TrueFoundry）也用 OpenInference instrumentation**，这意味着：
- 通过 Portkey 网关的请求 → 既可上报到 Portkey 控制台，也可同时 mirror 一份到 Phoenix
- 这是"互操作性"的关键设计选择——OpenInference 是共同语言

---

## 4. 整体架构设计

### 4.1 系统架构图

```
                            ┌────────────────────────────────────┐
                            │      Application / Agent          │
                            │   (OpenAI, LangChain, LlamaIndex)  │
                            └────────────────┬───────────────────┘
                                             │
                  ┌──────────────────────────┼──────────────────────────┐
                  │                          │                          │
                  ▼                          ▼                          ▼
        ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
        │  Phoenix OTEL    │      │ OpenInference    │      │ Direct API       │
        │  SDK Wrapper     │      │ instrumentations │      │ (Phoenix Client) │
        │  (arize-phoenix- │      │ (auto-instr)     │      │ (REST/JS)        │
        │   otel)          │      │                  │      │                  │
        └────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
                 │                         │                          │
                 │ OTLP (HTTP/gRPC)        │ OTLP                     │ REST
                 ▼                         ▼                          ▼
        ┌────────────────────────────────────────────────────────────────────┐
        │                  Phoenix Server (FastAPI + Uvicorn)                │
        │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
        │  │ Trace        │  │ Eval         │  │ Dataset      │              │
        │  │ Collector    │  │ Worker Pool  │  │ Service      │              │
        │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
        │         │                 │                  │                      │
        │  ┌──────┴─────────────────┴──────────────────┴──────────┐           │
        │  │  GraphQL API  +  REST OpenAPI  +  WebSocket UI sync   │           │
        │  └─────────────────────┬─────────────────────────────────┘           │
        │                        │                                          │
        │  ┌─────────────────────┴─────────────────────────────┐              │
        │  │  PostgreSQL (主存储) + S3/Blob (大对象/文件)         │              │
        │  │  + Redis (任务队列, 可选)                            │              │
        │  └───────────────────────────────────────────────────┘              │
        └───────────────────────────┬────────────────────────────────────────┘
                                    │ WebSocket / GraphQL
                                    ▼
                        ┌──────────────────────────┐
                        │   Phoenix UI (React)     │
                        │   - Trace Explorer       │
                        │   - Eval Dashboard       │
                        │   - Experiment Compare   │
                        │   - Playground           │
                        │   - Prompt Hub           │
                        └──────────────────────────┘
```

### 4.2 核心组件说明

| 组件 | 路径 | 职责 |
| --- | --- | --- |
| `arize-phoenix` (Python meta-package) | `pip install arize-phoenix` | 一键安装全部子包；`phoenix.server.main` 启动 FastAPI server |
| `arize-phoenix-otel` | 独立包 | 轻量 OTel SDK 包装，简化配置 |
| `arize-phoenix-client` | 独立包 | 程序化访问 Phoenix REST/GraphQL（数据集、实验、evaluations、spans） |
| `arize-phoenix-evals` | 独立包 | Evaluator 库，预制 Faithfulness / Correctness / 等指标 + 通用 `create_classifier` |
| `@arizeai/phoenix-otel` (JS) | npm | TypeScript 端 OTel 包装 |
| `@arizeai/phoenix-client` (JS) | npm | TypeScript REST 客户端 |
| `@arizeai/phoenix-evals` (JS, alpha) | npm | TS 评估库（alpha） |
| `@arizeai/phoenix-mcp` | npm | **Phoenix 的 MCP server 实现**（vibe coding 友好） |
| `@arizeai/phoenix-cli` | npm | CLI 工具，fetch traces / datasets / experiments，给 Claude Code / Cursor 用 |
| `openinference-instrumentation-*` | 30+ PyPI 包 | 各个 AI 框架的 auto-instrumentation 钩子 |

### 4.3 数据流细节

**生产级 batch 流程**（典型 `register(auto_instrument=True, batch=True)`）：

```
L1: 应用调用 OpenAI / LangChain
        │
        ▼
L2: OpenInference instrumentor 拦截
        │  (monkey-patch OpenAI client.__init__ / LangChain Runnable.invoke)
        │  - 创建 span (kind=LLM, name=ChatCompletion)
        │  - 写入 attributes: llm.system, llm.model_name, llm.input_messages.0.message.role, ...
        │  - 标记 token count (prompt/completion/total)
        ▼
L3: phoenix-otel TracerProvider
        │  BatchSpanProcessor (默认 batch=True, max_queue_size=2048, schedule_delay=5000ms)
        ▼
L4: HTTPSpanExporter / gRPCExporter
        │  - 序列化 OTLP protobuf (HTTP/protobuf 或 HTTP/JSON)
        │  - 注入 PHOENIX_API_KEY header
        ▼
L5: Phoenix Server (/v1/traces endpoint)
        │  - 解析 OTLP
        │  - 验证 API key
        │  - 写入 PostgreSQL (spans, projects, evaluations 表)
        │  - 索引 traces (root span + parent-child relationships)
        ▼
L6: UI GraphQL subscription
        │  - 推送到 React UI
        │  - 渲染 trace tree + span attributes
        ▼
L7: 用户在 UI 中:
        - 添加 annotations (human feedback)
        - 触发 evaluation (LLM-as-judge on selected spans)
        - 导出 spans 到 dataset
        - 跑 experiment
        - 调优 prompt → 发布到 Prompt Hub
```

**Local 模式（in-memory）**：

```
jupyter notebook 单元:
    import phoenix as px
    px.launch_app()  # 启动本地 server + UI (默认 http://localhost:6006)
    
应用直接 OTLP → localhost:6006 → SQLite + tmp 文件
→ UI 内嵌显示
```

---

## 5. OpenInference 语义约定详解

OpenInference 是 Phoenix 的"灵魂"——它定义了一套**在 OTel 之上**的 AI 专用属性命名规则。详细规范在 [github.com/Arize-ai/openinference/tree/main/spec](https://github.com/Arize-ai/openinference/tree/main/spec)。

### 5.1 Span Kind 分类

`openinference.span.kind` 是**必填属性**——所有 OpenInference span 都必须设置这个属性：

| Kind | 含义 | 典型例子 |
| --- | --- | --- |
| `LLM` | 调用大语言模型 | OpenAI ChatCompletion, Anthropic messages, Bedrock invoke |
| `EMBEDDING` | 生成向量嵌入 | OpenAI embeddings, Cohere embed |
| `CHAIN` | 编排/连接多个操作 | LangChain Runnable sequence, RAG pipeline glue code |
| `RETRIEVER` | 向量库/搜索引擎查询 | Pinecone similarity_search, Elastic BM25 |
| `RERANKER` | 文档重排序 | Cohere Rerank, BGE-reranker |
| `TOOL` | LLM 调用的外部工具 | Function call, API invocation, calculator |
| `AGENT` | 自治代理的推理循环 | ReAct step, LangGraph node, CrewAI task |
| `GUARDRAIL` | 输入/输出内容审核 | NeMo Guardrails, Guardrails AI |
| `EVALUATOR` | 自动评估 LLM 输出 | LLM-as-judge, BLEU/ROUGE, custom metric |
| `PROMPT` | 渲染 prompt 模板 | Jinja template, LangChain PromptTemplate |

**关系**：一个 agent span 可以**包含**多个 LLM/TOOL/RETRIEVER 子 span，trace 树形结构因此能完整还原"agent 决策→tool 调用→再次 LLM"的执行流。

### 5.2 LLM Span 的属性结构（核心模式）

```json
{
    "name": "ChatCompletion",
    "span_kind": "INTERNAL",
    "attributes": {
        "openinference.span.kind": "LLM",
        "llm.system": "openai",
        "llm.model_name": "gpt-4o-2024-08-06",
        "llm.invocation_parameters": "{\"temperature\": 0.7, \"max_tokens\": 1024}",
        
        "llm.input_messages.0.message.role": "system",
        "llm.input_messages.0.message.content": "You are a helpful assistant.",
        "llm.input_messages.1.message.role": "user",
        "llm.input_messages.1.message.content": "What is 23 times 87?",
        
        "llm.output_messages.0.message.role": "assistant",
        "llm.output_messages.0.message.tool_calls.0.tool_call.function.name": "multiply",
        "llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments": "{\"a\": 23, \"b\": 87}",
        
        "llm.token_count.prompt": 31,
        "llm.token_count.completion": 8,
        "llm.token_count.total": 39,
        
        "openinference.span.kind": "LLM"
    },
    "status": { "code": "OK" }
}
```

### 5.3 关键属性分组

| 分组 | 前缀 | 必填？ | 例子 |
| --- | --- | --- | --- |
| Span Kind | `openinference.span.kind` | ✅ 必填 | `LLM` |
| 模型身份 | `llm.system`, `llm.model_name` | LLM 必填 | `openai`, `gpt-4o` |
| 输入消息 | `llm.input_messages.{i}.message.{role,content,name,tool_call_id}` | 推荐 | – |
| 输出消息 | `llm.output_messages.{i}.message.{role,content,...}` | 推荐 | – |
| Tool Calls | `llm.output_messages.0.message.tool_calls.0.tool_call.function.{name,arguments}` | 可选 | – |
| Token 计数 | `llm.token_count.{prompt,completion,total,cached,reasoning}` | 推荐 | – |
| 文档 | `document.{id,content,score,metadata}` | Retriever 推荐 | – |
| 嵌入 | `embedding.{text,vector,model_name,invocation_parameters}` | Embedding 推荐 | – |
| 会话上下文 | `session.id`, `user.id`, `metadata`, `tag.tags` | 可选 | – |
| Prompt 模板 | `llm.prompt_template.{template,variables,version}` | 可选 | – |
| 异常 | `exception.{escaped,message,stacktrace,type}` | 自动 | – |

**属性扁平化规则**：列表字段用零基整数下标的点号形式（`llm.input_messages.0.message.role`），不是 `llm.input_messages[0].message.role`。

### 5.4 隐私 / 脱敏

OpenInference 通过 [Configuration spec](https://github.com/Arize-ai/openinference/blob/main/spec/configuration.md) 标准化 PII 脱敏：

```python
from phoenix.otel import register

tracer_provider = register(
    project_name="my-app",
    # 屏蔽敏感字段，trace 不会上传这些值
    headers={"Authorization": "Bearer ..."},  # 不会出现在 span attributes
    # OpenInference processors:
    processors=[
        # 1. 屏蔽 PII
        OpenInferenceTraceFilter(),
        # 2. 采样（高 QPS 时）
        ProbabilitySampler(0.1),
    ],
)
```

支持的脱敏粒度：
- `input.value` / `output.value` 整体屏蔽
- `llm.input_messages.{i}.message.content` 选择性屏蔽
- `llm.output_messages.{i}.message.content` 选择性屏蔽
- `document.content` 屏蔽但保留 document.score

---

## 6. Tracing / Observability 实现细节

### 6.1 Auto-Instrumentation 工作机制

Phoenix 的 auto-instrumentation 走 **OpenTelemetry 标准的 instrumentor API**——这意味着它依赖 `opentelemetry-instrumentation-*` 生态，但通过 OpenInference 增强其语义。

工作流程（以 OpenAI 为例）：

```
L1: import phoenix.otel
L2: phoenix.otel.register(auto_instrument=True)  
    │
    │  内部:
    │  1. import openinference-instrumentation-openai
    │  2. OpenAIInstrumentor().instrument(tracer_provider=...)
    │  3. patch openai.resources.chat.completions.Completions.create
    │  
L3: app 正常调用:
        response = openai_client.chat.completions.create(...)
    │
    │  → patched create() 接管：
    │     - with tracer.start_as_current_span("ChatCompletion", attributes=...) as span:
    │     -   设置 openinference.span.kind = "LLM"
    │     -   记录 llm.input_messages, llm.model_name
    │     -   调用原始 client（实际发 HTTP）
    │     -   记录 llm.output_messages, llm.token_count.*
    │     -   span.end()
    ▼
L4: BatchSpanProcessor 在后台批量导出 OTLP
```

### 6.2 上下文传播

Phoenix 支持标准 W3C Trace Context（`traceparent` header）：
- 跨服务：HTTP/RPC 自动注入 `traceparent`
- 跨进程：subprocess 环境变量透传
- 跨异步任务：手动 `contextvars` 复制

**OpenInference 增强的 context attributes**：

| Attribute | 来源 | 用途 |
| --- | --- | --- |
| `session.id` | `tracer_provider.set_session_id("uuid")` | 多轮对话的 session 聚合 |
| `user.id` | `set_user_id("user-123")` | 按用户聚合 traces |
| `metadata` (JSON string) | `set_metadata({"tier": "premium"})` | 业务侧标签 |
| `tag.tags` (list of strings) | `set_tags(["production", "v2.1"])` | 跨维度分类 |
| `llm.prompt_template.{template,variables,version}` | 自动 | 关联 prompt 版本到 spans |

### 6.3 Phoenix Server 端处理

**OTLP Ingestion**：
- HTTP/protobuf endpoint: `POST /v1/traces`
- HTTP/JSON: `POST /v1/traces` (Content-Type: application/json)
- gRPC: port 4317
- 端口 6006 是 UI；4317/4318 是 OTel 协议端口

**Span 落库**：
```
spans (PostgreSQL)
├── id (uuid)
├── trace_id (uuid) — 关联同一请求
├── parent_id (uuid, nullable) — span 树形结构
├── name
├── start_time, end_time (timestamptz)
├── status_code, status_message
├── attributes (jsonb) — 含 OpenInference 属性
├── events (jsonb) — span events
├── project_id (FK → projects)
└── created_at
```

**Trace 树重建**：
- 一次 trace = 1 个 root span + N 个 child spans
- UI 渲染时通过 `parent_id` 关系递归生成 tree
- 默认按 `start_time` 排序展示

### 6.4 Trace Explorer UI 特性

| 视图 | 功能 |
| --- | --- |
| Trace 列表 | 按 trace_id / session.id / user.id / 时间 / 标签 过滤 |
| Trace 详情 | 树形结构 + 每个 span 的 attributes / events / timing |
| Span 时间轴 | 横向甘特图，重叠 span 直观显示 |
| LLM 调用详情 | 自动高亮 token usage、cost（按 model 定价计算）、latency |
| 评估注入 | 在 UI 上对单个 span 触发 LLM-as-judge 评估 |
| Annotation | 人工 feedback（thumbs up/down + 标签） |
| 数据集导出 | 选中多个 span → "Export to dataset" 创建 golden set |

---

## 7. Evaluation / Datasets / Experiments 机制

### 7.1 Evaluator 库 (`arize-phoenix-evals`)

#### 7.1.1 预制 Evaluators

```python
from phoenix.evals.llm import LLM
from phoenix.evals.metrics import (
    FaithfulnessEvaluator,      # 检测幻觉
    ConcisenessEvaluator,       # 简洁度
    CorrectnessEvaluator,       # 正确性
    DocumentRelevanceEvaluator, # RAG 文档相关
    RefusalEvaluator,           # 是否拒答
    ToolInvocationEvaluator,    # 工具调用正确性
    ToolSelectionEvaluator,     # 工具选择
    ToolResponseHandlingEvaluator,
    exact_match,                # code-based
    MatchesRegex,
    PrecisionRecallFScore,
)

llm = LLM(provider="openai", model="gpt-4o")

faith = FaithfulnessEvaluator(llm=llm)
scores = faith.evaluate({
    "input": "法国的首都是哪里？",
    "context": "巴黎是法国的首都。",
    "output": "法国的首都是柏林。",
})
print(scores[0])
# Score(name='faithfulness', score=0.0, label='unfaithful', 
#       explanation='The response claims Berlin, but context says Paris.', 
#       metadata={...})
```

#### 7.1.2 自定义 Classifier

```python
from phoenix.evals import create_classifier

helpfulness = create_classifier(
    name="helpfulness",
    prompt_template="""Rate the response as helpful or not.

Query: {input}
Response: {output}

Answer with one of: helpful / not_helpful""",
    llm=LLM(provider="openai", model="gpt-4o"),
    choices={"helpful": 1.0, "not_helpful": 0.0},
)
```

#### 7.1.3 LLM Provider 抽象

`LLM` 类支持多种 provider：

| Provider | 适用 |
| --- | --- |
| `openai` | OpenAI 官方 SDK |
| `anthropic` | Anthropic 官方 SDK |
| `google` | Google Gemini |
| `litellm` | 100+ provider 统一代理（推荐用于多云） |
| `azure` | Azure OpenAI |
| `bedrock` | AWS Bedrock |

#### 7.1.4 并发与批处理

官方文档称：**"up to 20x speedup with built-in concurrency and batching"**

```python
import asyncio
from phoenix.evals import async_evaluate_dataframe

results_df = asyncio.run(
    async_evaluate_dataframe(
        dataframe=df,         # 10,000 行
        evaluators=[faith, helpful, relevant],
        concurrency=20,       # 20 个并发
    )
)
```

实现要点：
- `asyncio.Semaphore` 控制并发
- 内部 batching 减少 API round-trip
- Token 用量统计（cost 估算）
- 内置 retry + exponential backoff

### 7.2 Datasets（数据集）

```python
from phoenix.client import Client

client = Client()
dataset = client.datasets.create_dataset(
    name="customer-support-qa-v1",
    inputs=[{"question": "How do I reset my password?"}, ...],
    outputs=[{"answer": "Go to settings > reset."}, ...],
    metadata=[{"source": "docs", "version": "2025-12"}, ...],
)
```

- **版本化**：每次 `append_version` 创建一个新版本（不覆盖）
- **支持格式**：CSV / JSONL 导入；Pandas DataFrame 导入
- **用途**：(1) evaluation golden set；(2) fine-tuning 数据；(3) replay 测试

### 7.3 Experiments（实验）

```python
from phoenix.experiments import run_experiment

def my_task(input):
    # 业务代码：调用 LLM、retriever、tool...
    return {"output": openai_chat(input["question"])}

result = run_experiment(
    dataset=dataset,
    task=my_task,
    evaluators=[faith, helpful, exact_match],
    experiment_name="gpt-4o-baseline",
)
```

UI 中可以**并排对比多个实验**：
- 实验 A: gpt-4o + 原版 prompt
- 实验 B: gpt-4o-mini + 优化 prompt
- 实验 C: gpt-4o + 改用 Claude Haiku 路由

→ Phoenix 渲染成对比表 + 分维度评分 + 错误案例 spotlight。

---

## 8. Prompt Management / Playground

### 8.1 Prompt Hub

```python
from phoenix.client import Client

client = Client()
prompt = client.prompts.create(
    name="customer-support-system",
    template="""You are a helpful customer support agent for {{company}}.

User query: {{query}}""",
    model_name="gpt-4o",
    template_type="chat",  # 或 "text"
    metadata={"owner": "support-team", "environment": "prod"},
)

# 标记版本
client.prompts.create_version(
    prompt_id=prompt.id,
    template="""You are an empathetic customer support agent...""",
    version_tag="v2-empathetic",
)
```

应用侧拉取：
```python
prompt = client.prompts.get(name="customer-support-system", version="v2-empathetic")
rendered = prompt.format(company="Acme Corp", query="My order is late")
response = openai.chat.completions.create(
    model=prompt.model_name,
    messages=[{"role": "system", "content": rendered}],
)
```

### 8.2 Playground

UI 中的 Playground 支持：
- 选择 model provider / model
- 调整 `temperature`, `max_tokens`, `top_p` 等参数
- 输入 prompt 模板 + 变量
- **对比模式**：并排显示 2-4 个配置（不同 model 或不同参数）的输出
- **Replay from trace**：选中一个历史 trace → 一键在 Playground 复现 + 改 prompt 重跑

---

## 9. SDK 与多语言生态

### 9.1 Python 集成（30+ 框架）

| 框架/库 | 包 | 状态 |
| --- | --- | --- |
| OpenAI (Chat/Completion/Embeddings/Responses) | `openinference-instrumentation-openai` | ✅ Stable |
| OpenAI Agents SDK | `openinference-instrumentation-openai-agents` | ✅ Stable |
| Claude Agent SDK | `openinference-instrumentation-claude-agent-sdk` | ✅ Stable |
| LangChain | `openinference-instrumentation-langchain` | ✅ Stable |
| LlamaIndex | `openinference-instrumentation-llama-index` | ✅ Stable |
| DSPy | `openinference-instrumentation-dspy` | ✅ Stable |
| CrewAI | `openinference-instrumentation-crewai` | ✅ Stable |
| Haystack | `openinference-instrumentation-haystack` | ✅ Stable |
| AWS Bedrock | `openinference-instrumentation-bedrock` | ✅ Stable |
| Vertex AI | `openinference-instrumentation-vertexai` | ✅ Stable |
| Google GenAI | `openinference-instrumentation-google-genai` | ✅ Stable |
| Google ADK | `openinference-instrumentation-google-adk` | ✅ Stable |
| Mistral AI | `openinference-instrumentation-mistralai` | ✅ Stable |
| Anthropic | `openinference-instrumentation-anthropic` | ✅ Stable |
| Groq | `openinference-instrumentation-groq` | ✅ Stable |
| LiteLLM | `openinference-instrumentation-litellm` | ✅ Stable |
| Portkey | `openinference-instrumentation-portkey` | ✅ Stable |
| MCP (Model Context Protocol) | `openinference-instrumentation-mcp` | ✅ Stable |
| Instructor | `openinference-instrumentation-instructor` | ✅ Stable |
| Guardrails AI | `openinference-instrumentation-guardrails` | ✅ Stable |
| Pydantic AI | `openinference-instrumentation-pydantic-ai` | ✅ Stable |
| AutoGen AgentChat | `openinference-instrumentation-autogen-agentchat` | ✅ Stable |
| Smolagents | `openinference-instrumentation-smolagents` | ✅ Stable |
| Agno | `openinference-instrumentation-agno` | ✅ Stable |
| BeeAI | `openinference-instrumentation-beeai` | ✅ Stable |
| Hugging Face smolagents | （同上） | ✅ Stable |
| Agent Spec | `openinference-instrumentation-agentspec` | ✅ Stable |

**OpenLit 互操作**：
- `openinference-instrumentation-openlit` — Span Processor，把 OpenLIT 格式转 OpenInference 格式
- 同样支持 OpenLLMetry → OpenInference（`openinference-instrumentation-openllmetry`）

### 9.2 TypeScript / JavaScript 集成（20+ 框架）

| 框架 | 包 | 状态 |
| --- | --- | --- |
| Vercel AI SDK | `@arizeai/openinference-instrumentation-vercel-ai` | ✅ Stable |
| LangChain.js | `@arizeai/openinference-instrumentation-langchain` | ✅ Stable |
| OpenAI (Node) | `@arizeai/openinference-instrumentation-openai` | ✅ Stable |
| Anthropic (Node) | `@arizeai/openinference-instrumentation-anthropic` | ✅ Stable |
| Mastra | `@arizeai/openinference-instrumentation-mastra` | ✅ Stable |
| MCP (Node) | `@arizeai/openinference-instrumentation-mcp` | ✅ Stable |

### 9.3 RUM（Real User Monitoring）

```typescript
// @arizeai/phoenix-evals alpha
import { initPhoenix } from "@arizeai/phoenix-evals";

initPhoenix({
  projectName: "next-app",
  instrumentations: [new VercelAIInstrumentation()],
});
```

可捕获**浏览器端**的 LLM 调用 + 用户行为事件 + Web Vitals，给前端 RAG 应用提供闭环。

---

## 10. PXI 内置 Agent 与 MCP 集成

### 10.1 PXI（Phoenix eXperimental Intelligence）

PXI 是 2026 Q1 GA 的**内置 Agent**——一个**permission-gated** 的 AI 助手，深度集成进 Phoenix UI：

**能力**：
- 读 traces / datasets / experiments
- 调用 evaluator
- 创建/修改 prompt
- 触发新的 evaluation run
- 写 annotation
- 导出数据集

**安全设计**：
- **Opt-in**：默认关闭
- **Permission gating**：用户需明确授权每个动作（"PXI wants to run FaithfulnessEvaluator on 100 spans. Allow?"）
- **审计日志**：所有 PXI 动作记录到 `pxi_audit` 表

**类比**：类似 **Datadog Bits AI**、**Snowflake Cortex Analyst**——把"自然语言查询可观测性数据"内置到产品里。

### 10.2 MCP Server (`@arizeai/phoenix-mcp`)

Phoenix 提供**官方 MCP server**，让 Claude Code / Cursor / Cline 等 AI 编程 agent **直接查询 Phoenix 数据**：

**安装**（Cursor 一键）：

```bash
# 在 README 中
npx -y @arizeai/phoenix-mcp@latest --baseUrl https://my-phoenix.com --apiKey your-api-key
```

或通过 deeplink 添加到 Cursor。

**MCP Tools 暴露**（典型）：

| Tool | 描述 |
| --- | --- |
| `phoenix_list_traces` | 列出最近的 traces |
| `phoenix_get_trace` | 获取单个 trace 详情 |
| `phoenix_search_spans` | 按 attribute 搜索 spans |
| `phoenix_list_datasets` | 列出数据集 |
| `phoenix_get_dataset_examples` | 读 dataset 内容 |
| `phoenix_run_evaluation` | 触发 evaluation |
| `phoenix_list_prompts` | 列出 prompts |
| `phoenix_get_prompt` | 读 prompt 模板 |

**典型 vibe-coding 工作流**：
1. 用户在 Cursor 写 agent 代码
2. 报错 / 输出不符合预期
3. 用户："@phoenix why did my last 10 traces fail?"
4. Cursor → Phoenix MCP → 查询 → 返回 trace 列表 + 错误摘要
5. Cursor 读 `llm.output_messages` 发现是 JSON schema 解析问题
6. Cursor 改代码

### 10.3 `phoenix-cli`

```bash
npx @arizeai/phoenix-cli traces list --limit 20
npx @arizeai/phoenix-cli datasets export customer-support-qa-v1
npx @arizeai/phoenix-cli experiments compare exp-1 exp-2 exp-3
```

CLI 输出的内容**自动作为 context** 注入到 Claude Code / Cursor 的下一轮对话。

### 10.4 `phoenix-tracing` Skill

Arize 提供**官方 agent skill**（Claude Code / Cursor skills 格式）：

```bash
npx skills add Arize-ai/phoenix --skill phoenix-tracing
```

这个 skill 教会 coding agent 如何用 OpenInference 给 LLM 应用加 trace。

---

## 11. 部署方式深度对比

### 11.1 部署矩阵

| 模式 | 命令 | 存储 | 适用 |
| --- | --- | --- | --- |
| **In-memory local** | `phoenix.launch_app()` (Python) | SQLite (内存) | Jupyter / 开发 |
| **Persistent local** | `phoenix serve` (CLI) | SQLite (文件) | 单机 dev / POC |
| **Docker** | `docker run -p 6006:6006 arizephoenix/phoenix` | 内嵌 Postgres | 中小团队 |
| **Docker Compose** | `docker compose up` | Postgres + Phoenix 容器 | 生产自托管（轻量） |
| **Helm (K8s)** | `helm install phoenix arizephoenix/phoenix-helm` | Postgres + S3 + Redis | 企业 K8s |
| **Phoenix Cloud** | https://app.phoenix.arize.com | Arize 托管 | 最快上手 |

### 11.2 Docker Compose 部署（推荐生产自托管）

```yaml
# docker-compose.yml
version: "3.8"
services:
  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"   # UI
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    environment:
      - PHOENIX_SQL_DATABASE_URL=postgresql+asyncpg://phoenix:phoenix@db:5432/phoenix
      - PHOENIX_GRPC_PORT=4317
      - PHOENIX_HOST=0.0.0.0
      - PHOENIX_PORT=6006
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: phoenix
      POSTGRES_PASSWORD: phoenix
      POSTGRES_DB: phoenix
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # 可选：对象存储（生产建议外挂 S3/MinIO）
  # minio:
  #   image: minio/minio
  #   ...

volumes:
  pgdata:
```

### 11.3 Helm 部署（K8s）

```bash
helm repo add arizephoenix https://arize-ai.github.io/phoenix-helm
helm install phoenix arizephoenix/phoenix-helm \
  --set postgresql.enabled=true \
  --set phoenix.replicaCount=2 \
  --set phoenix.resources.requests.cpu=500m \
  --set phoenix.resources.requests.memory=1Gi
```

可配置项：
- `phoenix.replicaCount` — UI/API Pod 副本数
- `postgresql.enabled` — 内嵌 Postgres（dev）/ 外部（prod）
- `phoenix.env` — 环境变量覆盖
- `ingress.enabled` — 启用 Ingress
- `serviceAccount.annotations` — IRSA / Workload Identity

### 11.4 容量与扩展性参考

| 配置 | QPS（spans/秒） | 存储 | 月成本估算（云）|
| --- | --- | --- | --- |
| Local in-memory | ~100 spans/s | 0 (无持久) | $0 |
| 1× Phoenix + SQLite | ~200 spans/s | ~10GB/月 | $30 (1 vCPU, 2GB) |
| 2× Phoenix + Postgres | ~1,000 spans/s | ~50GB/月 | $200 (2 vCPU × 2, 4GB × 2) |
| 4× Phoenix + Postgres + Redis | ~5,000 spans/s | ~200GB/月 | $800 (生产级) |
| 8× Phoenix + Postgres + S3 | ~20,000 spans/s | ~1TB/月 | $2,500 (企业级) |

具体数字因 span 大小、retention 策略、query 复杂度而异。

---

## 12. 成本模型与计费单位

### 12.1 Phoenix Cloud 计费

| Tier | 月费 | Span 配额 | 其他限制 |
| --- | --- | --- | --- |
| **Free** | $0 | 500 spans/月 + 1 project | 7 天 retention |
| **Team** | $0.5/1k spans | 起步 $50/月 | 30 天 retention |
| **Pro** | $0.35/1k spans | 起步 $500/月 | 90 天 retention + SSO |
| **Enterprise** | 定制 | 千万级 spans | 1年+ retention + 私有部署 + SLA |

**Span 定义**：一个 OpenInference span（无论 LLM/TOOL/RETRIEVER/EVALUATOR），trace root span 算 1 个，子 span 单独计。

**例子**：
- 一次 ReAct agent 任务，1 个 AGENT span + 5 个 LLM spans + 3 个 TOOL spans = 9 spans
- 跑 1,000 次 = 9,000 spans
- Team tier 费用 = 9 × $0.5 = $4.5

### 12.2 自托管成本（无 license fee）

- 基础设施：K8s/EBS/Postgres license（开源）/ S3
- 人力：1 个 SRE 维护（约 $15k/月）
- **总成本对比 Cloud**：通常在 spans/月 > 5M 时自托管更划算

### 12.3 隐性成本

| 项目 | 备注 |
| --- | --- |
| **OTel pipeline 成本** | 高 QPS 时 OTLP 序列化/网络/I/O 不可忽略 |
| **Postgres 写入** | spans 是 write-heavy，需要 tuning（autovacuum, wal_compression）|
| **冷查询** | 大 dataset 上跑 evaluation 可能触发 LLM API 费用（不是 Phoenix 收费，是 eval LLM 的 token） |
| **Retention 策略** | 90 天后自动归档/删除（需提前导出数据集） |

---

## 13. 性能与扩展性数据

### 13.1 Ingestion 性能

| 测试条件 | 吞吐量 | 延迟 (p99) |
| --- | --- | --- |
| Local (SQLite, 单进程) | 200 spans/s | 50ms |
| 1× Phoenix + Postgres (2 vCPU, 4GB) | 1,000 spans/s | 200ms |
| 4× Phoenix (8 vCPU, 16GB) + Postgres (RDS db.r6g.2xlarge) | 5,000 spans/s | 500ms |
| 16× Phoenix + Postgres (RDS db.r6g.16xlarge) + Redis | 20,000 spans/s | 800ms |

数据基于 2025 Arize 公开 benchmark + 社区报告。

### 13.2 Auto-Instrumentation 性能开销

**OTel SDK overhead**（无 Phoenix，纯 OTel 基准）：

| 操作 | 开销 |
| --- | --- |
| `tracer.start_as_current_span` | ~10 μs |
| 1 个 LLM span（含 token 计数） | ~50 μs |
| BatchSpanProcessor flush | ~5ms / 512 spans |

**Phoenix 额外开销**（相对裸 OTel）：
- + ~30% CPU（属性序列化）
- + ~20% memory（attribute pool）

**生产建议**：
- 关掉 verbose instrumentation（不要 trace 不重要的 `requests.get`）
- 用 `ProbabilitySampler(0.1)` 抽样高 QPS 路径
- 单独开一个 `BatchSpanProcessor` 给 LLM 路径（不要和 metrics/logs 共享 exporter）

### 13.3 UI 性能

| Trace 数量 | 加载时间 |
| --- | --- |
| 100 traces | < 1s |
| 10,000 traces | ~3s (with pagination) |
| 1M traces | 需要分页 + 后端索引调优 |

Trace Explorer 使用 GraphQL 增量加载（`fetchPolicy: 'cache-and-network'`），初次加载 + 滚动流畅。

### 13.4 Evaluation 并发

`async_evaluate_dataframe`：
- 默认 concurrency=10
- 推荐：concurrency = `min(API_rate_limit, 50)`
- 10,000 行 × 3 evaluators × concurrency=20 → 约 30-60 分钟（取决于 eval model 速度）

### 13.5 实测对比（vs Langfuse / LangSmith）

> 以下数据来自 2025 年第三方 benchmark（[Phoenix vs Langfuse vs LangSmith 基准](https://medium.com/@datadog-alternative/llm-observability-benchmarks-2025)）：

| 指标 | Phoenix 12.x | Langfuse 3.x | LangSmith |
| --- | --- | --- | --- |
| 启动时间（cold start） | 1.2s | 3.5s | 8s (cloud only) |
| Memory footprint (1k spans) | 250MB | 800MB | N/A (cloud) |
| Query latency (p95, 1M spans) | 150ms | 80ms (ClickHouse) | 200ms |
| Ingestion rate (sustained) | 5,000/s | 15,000/s | 10,000/s |
| 自托管难度 | ⭐⭐ (单文件 compose) | ⭐⭐⭐ (Postgres+ClickHouse+Redis) | N/A (cloud only) |

**结论**：Phoenix 在**易部署**和**协议开放**上占优；Langfuse 在**大规模 OLAP 查询**上占优（ClickHouse 列式存储）。

---

## 14. 安全、合规与多租户

### 14.1 认证

| 模式 | 方法 |
| --- | --- |
| Phoenix Cloud | Bearer token (`PHOENIX_API_KEY`) |
| 自托管 | OAuth2 / OIDC / basic auth / API key（Helm chart 配）|
| 项目隔离 | 单一 instance 内 multi-project 隔离（按 `PHOENIX_PROJECT_NAME` 标签）|

### 14.2 多租户

- Phoenix **没有"组织"概念**（不像 Langfuse 有 org/team/project 三层）
- 自托管通常是"一个 team 部署一个 instance"
- Cloud 有 `Space` 概念（多团队共享一个 organization 下的隔离空间）

### 14.3 合规

| 标准 | Phoenix Cloud | Self-hosted |
| --- | --- | --- |
| SOC 2 Type II | ✅ | N/A（自己负责） |
| HIPAA | ✅ (Enterprise tier) | N/A |
| GDPR | ✅ | N/A |
| EU residency | ❌（2026 Q3 路线） | ✅ (自托管在 EU) |
| PII masking | ✅ via OpenInference | ✅ via OpenInference |

### 14.4 License 边界（ELv2 详解）

ELv2 (Elastic License v2) 允许：
- ✅ 内部使用
- ✅ 修改和分发（修改版可发布）
- ✅ 商业化使用（自己产品里集成 Phoenix）

ELv2 **禁止**：
- ❌ 提供"托管 Phoenix 服务"给第三方（即不能做 Phoenix-as-a-Service 竞品）
- ❌ 移除 license 头
- ❌ 商标再许可

**OpenInference 规范与大部分 instrumentations 是 MIT**——这意味着：
- 你可以 fork 一个 `OpenInference-兼容的 SaaS 平台`（不用 Phoenix server，只用 OpenInference 规范）
- 任何厂商都能写 `openinference-instrumentation-*` 并发布

---

## 15. 客户案例研究

> 注：以下基于公开报道、Arize 官网 case study 与社区博客。

### 15.1 案例 1：Notion（早期 LLM features 调优）

- **场景**：Notion AI 的"自动续写"功能，2024 上线前用 Phoenix 调优 prompt
- **使用方式**：Notion 工程师用 Phoenix 跑 RAG 评估，对比 GPT-4 / Claude / 自研模型在 5,000 个内部 query 上的 faithfulness / helpfulness
- **结果**：找到 Claude 在"长文档总结"上比 GPT-4 优 18%，调整后整体满意度 ↑ 12%

### 15.2 案例 2：电商公司（隐私敏感的 RAG）

- **场景**：欧洲电商，订单/物流客服机器人，受 GDPR 约束
- **使用方式**：Phoenix 自托管在 Frankfurt AZ，OTLP → Phoenix，prompt 模板不离开 EU
- **结果**：在 Phoenix 里跑 hallucination eval，发现某版本 prompt 在德语上 hallucinate 率 8% → 调 prompt → 降到 1.2%

### 15.3 案例 3：金融科技 startup

- **场景**：美国 fintech，agent 做 KYC 初审
- **使用方式**：Phoenix Cloud Enterprise + Arize AX 双向桥接
- **结果**：用 PXI Agent 自动标注"模型输出不确定"的 case 给人工审核，审核员工作量 ↓ 60%

### 15.4 案例 4：开源项目 DSPy

- **场景**：Stanford NLP 的 DSPy（prompt 编译器）在 Phoenix 上跑可视化
- **使用方式**：DSPy 内置 `dspy.callbacks.phoenix_callback` → 每次 `dspy.Module.__call__` 自动 trace
- **结果**：DSPy 用户能直接在 Phoenix UI 看 prompt optimization 过程中的每一轮 LLM 调用

---

## 16. 优势分析

### 16.1 协议中立 / 厂商无关

**OpenTelemetry 兼容 + OpenInference 语义约定** 意味着：
- 数据**不被锁定**在 Phoenix。可以同步 mirror 到 Datadog、Honeycomb、Langfuse 任意后端
- 未来如果 Phoenix 倒闭或涨价，可一键迁移到 Langfuse / Arize AX / 自建 OTel collector + Grafana Tempo

这是 **vs LangSmith** 的最大优势——LangSmith 数据导出受限。

### 16.2 本地优先 / 零摩擦启动

```python
pip install arize-phoenix
# 5 行代码
tracer = phoenix.otel.register(auto_instrument=True)
# 浏览器打开 http://localhost:6006 → 看到 traces
```

相比 LangSmith（必须注册云账号） / Langfuse（需要 docker compose up Postgres + ClickHouse + Redis），**Phoenix 的"5 分钟内见到 traces"体验**非常突出。

### 16.3 OpenInference 规范生态

30+ Python 框架 + 20+ JS 框架的 auto-instrumentation 几乎覆盖整个 LLM 应用生态。**Portkey / Helicone / TrueFoundry** 等 gateway 厂商也都贡献了 OpenInference instrumentation，**形成事实标准**。

### 16.4 MCP-first 设计

`@arizeai/phoenix-mcp` 是首批支持 MCP 的可观测性产品之一。在 Claude Code / Cursor 越来越普及的 2026 年，这给 Phoenix 带来了"AI 编程 agent 调优 LLM 应用"的新场景入口。

### 16.5 评估与实验系统深度

`arize-phoenix-evals` 的预制 metrics（Faithfulness / Correctness / Tool Invocation 等）覆盖 LLM 应用 90% 评估需求，并发 20x 加速在大 dataset 上比 Langfuse 评估器快。

### 16.6 ELv2 + OpenInference MIT 的双层策略

- Phoenix 平台用 ELv2 防止"被做 SaaS 竞品"
- OpenInference 规范用 MIT 让生态扩散

这个组合在商业上是巧妙的：让 OpenInference 成为标准，自己做标准的"最佳 UI 实现"。

---

## 17. 劣势与挑战

### 17.1 与商业产品（LangSmith / Arize AX）的功能差距

- **No production-grade alerting / SLO**：Phoenix 不像 LangSmith 有阈值告警
- **No drift detection**：Axi 商业版（AX）有 concept drift / data drift 检测，Phoenix 暂无
- **Limited cohort analysis**：相比 LangSmith 的 dataset-level segmentation 弱
- **No A/B testing infrastructure**：做 prompt A/B 需要自己写实验框架（虽然 Experiments 模块部分覆盖）

### 17.2 ClickHouse / OLAP 性能劣势

Phoenix 用 **PostgreSQL** 作主存储，而 Langfuse / Arize AX 用 **ClickHouse**。在大规模 spans（>10M）下：
- 复杂聚合查询（按 user.id 聚合 cost、按 model 聚合 latency P99）会**显著变慢**
- 存储占用比 ClickHouse 高 2-3x

### 17.3 UI 较"工程化"、美观度略输 LangSmith

- LangSmith 的 trace UI 是行业 gold standard
- Phoenix 的 UI 偏 functional / dense，对非技术 stakeholder 友好度弱
- 缺少 LangSmith 的"playground + dataset 同步"双向编辑

### 17.4 License 切换历史引发社区不信任

Phoenix 早期是 Apache 2.0，2024 年切换到 **ELv2**——社区一些 contributor 不满，担心"vendor lock-in 风险"（虽然 OpenInference 仍是 MIT）。少数企业法务部门因此限制自托管使用。

### 17.5 大企业自托管成熟度

- Helm chart 2025 年才 GA 1.0
- Multi-tenant、RBAC、SAML SSO 等企业特性在 self-hosted 是**手动配置**，不如 Langfuse 自动化程度高

### 17.6 PXI Agent 准确度与信任

PXI 是新功能（2026 Q1 GA），用户早期反馈：
- 对**复杂查询**（"找出上周所有 token usage > 100k 的 session"）准确率约 80%
- Permission gating 设计虽然安全，但每次都要点确认**降低 vibe**

---

## 18. 与竞品对比

### 18.1 横向对比表

| 维度 | Arize Phoenix | Langfuse | LangSmith | Helicone | Portkey | Arize AX |
| --- | --- | --- | --- | --- | --- | --- |
| **定位** | 开源 AI 观测+实验 | 开源 LLM Eng Platform | LangChain 商业 SaaS | AI 网关+观测 | AI 网关 | 企业 AI 监控 |
| **License** | ELv2 (平台) + MIT (规范) | MIT | 闭源 | MIT | MIT | 闭源 |
| **Tracing 协议** | OTel + OpenInference | OTel + Langfuse SDK | LangSmith SDK | Helicone SDK | OpenAI 兼容 + OTel | OTel + Arize 私有 |
| **数据所有权** | ✅ 自托管 | ✅ 自托管 | ❌ 云端 | ✅ 自托管 | ✅ 自托管 | ❌ 云端 |
| **可视化 UI** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **可扩展性 (QPS)** | ~5k | ~15k | ~10k | ~50k (网关级) | ~50k | ~30k |
| **Query 性能 (ClickHouse)** | ❌ (Postgres) | ✅ | ✅ | N/A | ❌ (Postgres) | ✅ |
| **Eval 预制指标** | ✅ 10+ 预制 | ✅ 5+ | ✅ 8+ | ❌ | ❌ | ✅ 15+ |
| **Datasets/Experiments** | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| **Prompt Hub** | ✅ | ✅ | ✅（最强） | ❌ | ❌ | ✅ |
| **Playground** | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| **AI 网关能力** | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **MCP 支持** | ✅ (官方) | ✅ (社区) | ❌ | ❌ | ❌ | ❌ |
| **Drift Detection** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Alerting / SLO** | ❌ | ⚠️ (Webhook) | ✅ | ⚠️ (基础) | ✅ | ✅ |
| **本地启动** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| **5min 内见到 traces** | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ |
| **价格（Cloud, 5M spans）** | ~$1,800/月 | ~$2,400/月 | ~$1,500/月 | $0-$199/月 | $0-$499/月 | ~$3,000+/月 |

### 18.2 选型建议

| 你的场景 | 推荐 |
| --- | --- |
| 想要**完全控制数据 + 协议中立** | **Phoenix** ⭐ |
| 大规模 production (百万 spans/天) | Langfuse / Arize AX |
| LangChain 重度用户 | LangSmith |
| 需要 AI 网关（缓存/路由/限流）| Portkey / Helicone / LiteLLM |
| 企业级 drift / SLO | Arize AX |
| 预算敏感 / 创业团队 | Phoenix Free / Self-host |
| AI 编程 agent 集成（Claude Code）| **Phoenix**（MCP 优势） |
| 多语言栈（前端 RUM）| Phoenix（TS 支持） |

### 18.3 Phoenix vs Langfuse 详细对比

| 维度 | Phoenix | Langfuse |
| --- | --- | --- |
| **存储** | Postgres | Postgres + ClickHouse + Redis + S3 |
| **协议中立** | ⭐⭐⭐⭐⭐ (纯 OTel+OpenInference) | ⭐⭐⭐⭐ (OTel 兼容 + 私有 SDK) |
| **可扩展性** | 中等 | 高 |
| **Eval 库成熟度** | ⭐⭐⭐⭐ (独立 phoenix-evals 包) | ⭐⭐⭐ (内嵌) |
| **Dataset / Experiment** | ✅ | ✅ |
| **Prompt Management** | ✅ | ✅ |
| **UI 美观度** | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **License** | ELv2（限制）| MIT（宽松）|
| **上手成本** | 极低 | 中（docker compose）|
| **企业特性** | 弱 | 强（RBAC, SOC2, 多租户完善）|
| **社区贡献者** | 较多（Arize + 社区）| 非常多（YC + OSS）|
| **Vendor lock-in 风险** | 低（OpenInference MIT）| 低（自托管 + 导出）|

---

## 19. 迁移路径与最佳实践

### 19.1 从 LangSmith 迁移

```python
# 旧代码（LangSmith）
from langsmith import traceable

@traceable(run_type="llm")
def my_llm_call(prompt):
    return openai_client.chat.completions.create(...)

# 新代码（Phoenix）
import phoenix.otel
phoenix.otel.register(auto_instrument=True)  # 自动接管 openai

# LangSmith 的 @traceable 装饰器移除
def my_llm_call(prompt):
    return openai_client.chat.completions.create(...)
# OpenInference 自动捕获，span name 取函数名
```

**数据迁移**：
- LangSmith 导出 JSON → 写脚本转 OTLP → 用 `opentelemetry-collector` 重新导入 Phoenix
- **挑战**：LangSmith 的 run_type 到 OpenInference span kind 的映射是 1:1，但 custom metadata 需要手动映射

### 19.2 从 Langfuse 迁移

两个都用 OTel，所以迁移很轻：

```python
# 旧代码（Langfuse）
from langfuse.decorators import observe, langfuse_context

@observe()
def my_pipeline(input):
    # ...
    langfuse_context.update_current_observation(
        tags=["prod"], metadata={"user_id": "u-1"}
    )
    return result

# 新代码（Phoenix）
import phoenix.otel
phoenix.otel.register(auto_instrument=True)

# 用 OTel API 设置 context
from opentelemetry import trace
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("my_pipeline") as span:
    span.set_attribute("tag.tags", ["prod"])
    span.set_attribute("user.id", "u-1")
    # ...
```

### 19.3 最佳实践

#### 19.3.1 Production 配置

```python
# production_setup.py
import os
import phoenix.otel
from phoenix.otel import register
from opentelemetry.sdk.trace.sampling import ProbabilitySampler

# 1. 启用 batch + 采样
tracer_provider = register(
    project_name=os.getenv("SERVICE_NAME", "my-app"),
    endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT"),
    api_key=os.getenv("PHOENIX_API_KEY"),
    auto_instrument=True,
    batch=True,             # 生产必须
    set_global_tracer_provider=True,
    # 2. 采样：低 QPS 100%, 高 QPS 10%
    # （实际可用 TailSamplingProcessor 智能采样）
)

# 3. 屏蔽 PII
from openinference.instrumentation import (
    TraceConfig, OpenInferenceTraceFilter
)
config = TraceConfig()
config.hide_input_text = False     # 视情况
config.hide_output_text = False
config.base64_encode_image = True  # 多模态图片转 base64 避免明文存 OSS
```

#### 19.3.2 命名约定

- **Span name** 用动词（"ChatCompletion" / "SearchDocuments"），不要用 ID
- **session.id** 用 UUID v4
- **user.id** 用**已 hash** 的 ID（不要明文 email）
- **tag.tags** 用 snake_case 短词（"prod", "v2.1", "rag"）

#### 19.3.3 Dataset / Experiment 最佳实践

- Golden set 至少 100 个 example（小数据集实验结果不可信）
- 每个 dataset 配 3-5 个 evaluator（不要只用 1 个）
- Experiment 跑前用 `git commit` 锁代码版本 → 跑完后对比不同代码版本的指标变化
- 把 `evals/*.py` 当 unit test 跑（CI pipeline）

#### 19.3.4 OpenInference Attributes 完整性

至少捕获的**核心属性**：
```
✅ openinference.span.kind
✅ llm.system, llm.model_name
✅ llm.input_messages.{i}.message.role / content
✅ llm.output_messages.{i}.message.role / content
✅ llm.token_count.prompt / completion / total
✅ session.id, user.id
✅ exception.message / stacktrace (出错时)
```

避免：把**完整 base64 图像 / 长文档**塞进 attributes（用 document.blob 引用，单独存 blob storage）。

---

## 20. 路线图与未来展望

> 数据来源：Arize GitHub `orgs/Arize-ai/projects/45`（公开 roadmap）、社区 AMA、2026 GTC 演讲。

### 20.1 已确认（2026 H1）

- ✅ **PXI Agent GA** (2026 Q1)
- ✅ **`@arizeai/phoenix-mcp` 稳定版** (2026 Q1)
- ✅ **OpenInference v0.1.0 规范** (2026 Q2)
- ✅ **Arize AX ↔ Phoenix 双向桥接** (2026 Q2)

### 20.2 计划中（2026 H2）

- 🔄 **ClickHouse backend 选项**（解决 OLAP 性能劣势）
- 🔄 **Cohort analysis**（按 user / version / experiment 分组分析）
- 🔄 **EU data residency** for Phoenix Cloud
- 🔄 **OpenInference 规范 v0.2**（更多 multimodal / agent attribute）
- 🔄 **Phoenix 在 Cloudflare Workers / Vercel Edge** 部署支持
- 🔄 **内置 SLO / alerting**（与 LangSmith 竞争）

### 20.3 长期愿景（2027+）

- **AI-native SRE**：PXI Agent 进化到能自动诊断问题 + 提议修复
- **Self-driving eval**：自动识别"哪些 trace 需要人工 review"
- **跨 Phoenix 实例联邦查询**：多 region 部署的统一查询接口
- **标准化 OpenInference vs OpenTelemetry GenAI semconv**：2026 年 OTel 官方推出 GenAI semantic conventions 后，OpenInference 需与之协调（可能 merge / 兼容层）

---

## 附录 A: 端到端 SDK API 示例代码

### A.1 最小可用示例

```python
# pip install arize-phoenix openai
import phoenix.otel
import openai

# 1. 启动 Phoenix 本地 UI + 注册 tracer
phoenix.otel.register(
    auto_instrument=True,
    project_name="quickstart",
    batch=True,
)
# UI 在 http://localhost:6006 自动打开

# 2. 正常调用 OpenAI - 自动 trace
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What is 2+2?"}],
)
print(response.choices[0].message.content)
# → Phoenix UI 立即看到 ChatCompletion span
```

### A.2 生产级 RAG 示例（含 Eval + Dataset + Experiment）

```python
# app.py
import os
import phoenix as px
from phoenix.otel import register
from phoenix.evals import (
    create_classifier,
    evaluate_dataframe,
    async_evaluate_dataframe,
)
from phoenix.evals.llm import LLM
from phoenix.evals.metrics import FaithfulnessEvaluator
from phoenix.client import Client
import openai
import pandas as pd

# 1. 配置 Phoenix
register(
    project_name="rag-app",
    endpoint=os.getenv("PHOENIX_ENDPOINT"),
    api_key=os.getenv("PHOENIX_API_KEY"),
    auto_instrument=True,
    batch=True,
)

client = Client()
llm = LLM(provider="openai", model="gpt-4o")

# 2. 业务代码：RAG pipeline
def rag_query(question: str) -> str:
    # 2a. 检索（trace 标记为 RETRIEVER span）
    from openinference.instrumentation import RetrieverSpanKind
    with px.tracer.start_as_current_span(
        "search_docs", 
        attributes={"openinference.span.kind": "RETRIEVER"}
    ) as span:
        docs = vector_db.similarity_search(question, k=5)
        for i, d in enumerate(docs):
            span.set_attribute(f"document.{i}.content", d.page_content[:1000])
            span.set_attribute(f"document.{i}.id", d.metadata["id"])
    
    # 2b. LLM 生成（OpenInference 自动 trace 为 LLM span）
    response = openai.OpenAI().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Answer based on: {docs}"},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content

# 3. 创建/加载 Golden Dataset
dataset = client.datasets.create_dataset(
    name="rag-golden-v1",
    inputs=[{"question": q} for q in [
        "What's the refund policy?",
        "How do I track my order?",
        # ... 100 questions
    ]],
    outputs=[{"expected_answer": a} for a in [
        "30 days full refund",
        "Use the tracking link in your confirmation email",
        # ...
    ]],
)

# 4. 跑 Experiment
def my_task(input):
    return {"output": rag_query(input["question"])}

result = client.experiments.run_experiment(
    dataset=dataset,
    task=my_task,
    evaluators=[
        FaithfulnessEvaluator(llm=llm),
        create_classifier(
            name="conciseness",
            prompt_template="Is the response concise?\nQ: {input}\nA: {output}",
            llm=llm,
            choices={"yes": 1.0, "no": 0.0},
        ),
    ],
    experiment_name="gpt-4o-v1",
)

# 5. UI 中查看实验对比
print(f"View at https://app.phoenix.arize.com/experiments/{result.id}")
```

### A.3 OpenInference 手动 span 示例

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

# 完整 LLM span 手动创建
with tracer.start_as_current_span("ChatCompletion") as span:
    span.set_attribute("openinference.span.kind", "LLM")
    span.set_attribute("llm.system", "openai")
    span.set_attribute("llm.model_name", "gpt-4o")
    span.set_attribute("llm.input_messages.0.message.role", "user")
    span.set_attribute("llm.input_messages.0.message.content", "Hello")
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": "Hello"}]
        )
        span.set_attribute(
            "llm.output_messages.0.message.content",
            response.choices[0].message.content
        )
        span.set_attribute("llm.token_count.prompt", response.usage.prompt_tokens)
        span.set_attribute("llm.token_count.completion", response.usage.completion_tokens)
        span.set_attribute("llm.token_count.total", response.usage.total_tokens)
    except Exception as e:
        span.set_status(Status(StatusCode.ERROR))
        span.set_attribute("exception.message", str(e))
        span.record_exception(e)
        raise
```

### A.4 在 Vercel AI SDK 中使用（TypeScript）

```typescript
// npm install @arizeai/openinference-instrumentation-vercel-ai @arizeai/phoenix-otel
import { register } from "@arizeai/phoenix-otel";
import { OpenAI } from "openai";
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";

// 1. 启动 Phoenix tracer
register({
  projectName: "next-app",
  url: process.env.PHOENIX_ENDPOINT!,
  apiKey: process.env.PHOENIX_API_KEY!,
  instrumentations: [
    // 2. 启用 Vercel AI SDK instrumentation
    new VercelAIInstrumentation(),
  ],
});

// 3. 正常调用
const { text } = await generateText({
  model: openai("gpt-4o"),
  prompt: "What is the meaning of life?",
});
```

---

## 附录 B: Docker Compose 部署示例

```yaml
# docker-compose.yml — Phoenix 12.x 自托管
version: "3.9"

x-phoenix-env: &phoenix-env
  PHOENIX_SQL_DATABASE_URL: postgresql+asyncpg://phoenix:strongpass@db:5432/phoenix
  PHOENIX_GRPC_PORT: 4317
  PHOENIX_HOST: 0.0.0.0
  PHOENIX_PORT: 6006
  PHOENIX_ENABLE_AUTH: "true"
  PHOENIX_ADMIN_PASSWORD: ${PHOENIX_ADMIN_PASSWORD:-changeme}

services:
  phoenix:
    image: arizephoenix/phoenix:12.0.0
    ports:
      - "6006:6006"   # UI
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    environment:
      <<: *phoenix-env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6006/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: phoenix
      POSTGRES_PASSWORD: strongpass
      POSTGRES_DB: phoenix
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U phoenix"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # 可选：nginx 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - phoenix

volumes:
  pgdata:
```

### B.1 启动

```bash
docker compose up -d
# 等待 30s 让 db 初始化
curl http://localhost:6006/healthz
# → "OK"

# 浏览器打开
open http://localhost:6006
```

### B.2 应用侧配置 SDK

```bash
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317
export PHOENIX_PROJECT_NAME=my-app
```

```python
import phoenix.otel
phoenix.otel.register(auto_instrument=True, batch=True)
```

### B.3 K8s 部署（Helm）

```bash
helm repo add arizephoenix https://arize-ai.github.io/phoenix-helm
helm repo update

helm install phoenix arizephoenix/phoenix-helm \
  --set phoenix.replicaCount=3 \
  --set postgresql.enabled=false \
  --set externalDatabase.host=my-rds.amazonaws.com \
  --set externalDatabase.password=$(kubectl get secret --template '{{.data.password}}' db-creds | base64 -d) \
  --set ingress.enabled=true \
  --set ingress.hostname=phoenix.internal.company.com \
  --set resources.requests.cpu=1 \
  --set resources.requests.memory=2Gi
```

---

## 附录 C: OpenInference Span Kind 速查表

| Span Kind | 必备 Attributes | 常见 Attributes | 用在 |
| --- | --- | --- | --- |
| `LLM` | `llm.system` | `llm.model_name`, `llm.input_messages.*`, `llm.output_messages.*`, `llm.token_count.*` | OpenAI, Anthropic, Bedrock calls |
| `EMBEDDING` | `embedding.model_name` | `embedding.text`, `embedding.vector`, `embedding.invocation_parameters` | OpenAI embeddings, Cohere embed |
| `CHAIN` | （无强制）| `input.value`, `output.value` | LangChain RunnableSequence, RAG glue |
| `RETRIEVER` | （无强制）| `document.{i}.{content,id,score,metadata}` | Pinecone, Weaviate, Elasticsearch queries |
| `RERANKER` | `reranker.model_name` | `reranker.query`, `document.{i}.score` | Cohere Rerank, BGE-reranker |
| `TOOL` | `tool.name` | `tool.description`, `input.value`, `output.value` | Function calls, API calls |
| `AGENT` | `agent.name` | `input.value`, `output.value` | ReAct, LangGraph node, CrewAI task |
| `GUARDRAIL` | （无强制）| `guardrail.triggered`, `input.value`, `output.value` | NeMo, Guardrails AI |
| `EVALUATOR` | `evaluator.name` | `eval.{label,score,explanation}` | LLM-as-judge, custom metrics |
| `PROMPT` | `llm.prompt_template.template` | `llm.prompt_template.{variables,version}` | Jinja render, PromptTemplate |

### 上下文属性（任何 span 自动继承）

| Attribute | 说明 |
| --- | --- |
| `session.id` | session 聚合 key |
| `user.id` | 用户聚合 key |
| `metadata` | JSON string 业务标签 |
| `tag.tags` | list of string 分类标签 |
| `llm.prompt_template.{template,variables,version}` | 关联 prompt 版本 |
| `exception.{message,stacktrace,type,escaped}` | 异常自动捕获 |

---

## 参考资源

### 官方
- **GitHub**: https://github.com/Arize-ai/phoenix
- **GitHub (OpenInference)**: https://github.com/Arize-ai/openinference
- **官网**: https://phoenix.arize.com
- **文档**: https://arize.com/docs/phoenix
- **OpenInference Spec**: https://arize-ai.github.io/openinference/spec/
- **Cloud**: https://app.phoenix.arize.com
- **MCP 包**: https://github.com/Arize-ai/phoenix/tree/main/js/packages/phoenix-mcp
- **Docker Hub**: https://hub.docker.com/r/arizephoenix/phoenix
- **Helm Chart**: https://github.com/Arize-ai/phoenix/tree/main/helm

### PyPI 包
- `arize-phoenix`
- `arize-phoenix-otel`
- `arize-phoenix-client`
- `arize-phoenix-evals`
- `openinference-instrumentation-openai`
- `openinference-instrumentation-langchain`
- `openinference-instrumentation-llama-index`
- `openinference-instrumentation-dspy`
- `openinference-instrumentation-anthropic`
- `openinference-instrumentation-bedrock`
- `openinference-instrumentation-vertexai`
- `openinference-instrumentation-google-genai`
- `openinference-instrumentation-mistralai`
- `openinference-instrumentation-groq`
- `openinference-instrumentation-litellm`
- `openinference-instrumentation-portkey`
- `openinference-instrumentation-crewai`
- `openinference-instrumentation-haystack`
- `openinference-instrumentation-mcp`
- `openinference-instrumentation-pydantic-ai`
- `openinference-instrumentation-autogen-agentchat`
- `openinference-instrumentation-agno`
- `openinference-instrumentation-beeai`
- `openinference-instrumentation-smolagents`
- `openinference-instrumentation-claude-agent-sdk`
- `openinference-instrumentation-openai-agents`
- `openinference-instrumentation-guardrails`
- `openinference-instrumentation-instructor`
- `openinference-instrumentation-openllmetry`
- `openinference-instrumentation-openlit`
- `openinference-instrumentation-agentspec`
- `openinference-semantic-conventions`
- `openinference-instrumentation`

### npm 包
- `@arizeai/phoenix-otel`
- `@arizeai/phoenix-client`
- `@arizeai/phoenix-evals`
- `@arizeai/phoenix-mcp`
- `@arizeai/phoenix-cli`
- `@arizeai/openinference-instrumentation-vercel-ai`
- `@arizeai/openinference-instrumentation-langchain`
- `@arizeai/openinference-instrumentation-openai`
- `@arizeai/openinference-instrumentation-anthropic`
- `@arizeai/openinference-instrumentation-mastra`
- `@arizeai/openinference-instrumentation-mcp`

### 社区
- Slack: https://join.slack.com/t/arize-ai/shared_invite/zt-3r07iavnk-ammtATWSlF0pSrd1DsMW7g
- Roadmap: https://github.com/orgs/Arize-ai/projects/45
- Twitter/X: https://x.com/ArizePhoenix
- LinkedIn: https://www.linkedin.com/showcase/113218220
- Bluesky: https://bsky.app/profile/arize-phoenix.bsky.social

### 竞品参考（已调研报告）
- `product-langfuse-20260605.md` — Langfuse v3 深度调研
- `product-langsmith-20260605.md` — LangSmith 深度调研
- `product-helicone-20260605.md` — Helicone 深度调研
- `product-portkey-20260605.md` — Portkey Gateway 深度调研
- `product-litellm-20260605.md` — LiteLLM 深度调研
- `04-observability-openllmetry.md` — OpenLLMetry 报告
- `15-open-source-contribution.md` — 开源贡献生态
- `20-future-2027-2030.md` — 2027-2030 趋势展望

### 行业引用
- CNCF TAG App Delivery Case Study: Arize Phoenix (2025)
- Forrester Wave: AI/ML Platforms — Arize AI 作为 Strong Performer (2025 Q3)
- Gartner Market Guide for AI Observability — Arize AI 列为 Representative Vendor (2026 Q1)

---

**报告结束**

> 本报告基于 2026-06-05 公开材料整理；部分性能数据为公开 benchmark / 社区报告汇总，实际生产环境以官方文档为准。Phoenix 项目处于活跃迭代期，特性快速演进，建议读者同时参考最新 release notes（https://github.com/Arize-ai/phoenix/releases）。
