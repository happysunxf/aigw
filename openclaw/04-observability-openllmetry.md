# 可观测与 OpenLLMetry：标准、实践与研究前沿

> 系列：AI Gateway 持续深挖 · 第 4 篇
> 性质：纯技术研究
> 范围：LLM 可观测的"三大支柱"、OpenLLMetry 标准、网关层可观测设计、隐私权衡

---

## 目录

- [一、为什么 LLM 场景的可观测是"新问题"](#一为什么-llm-场景的可观测是新问题)
- [二、可观测三大支柱：Metrics / Logs / Traces](#二可观测三大支柱metrics--logs--traces)
- [三、OpenTelemetry 基础回顾](#三opentelemetry-基础回顾)
- [四、OpenLLMetry 标准深入](#四openllmetry-标准深入)
- [五、关键 Span 与 Attribute 详解](#五关键-span-与-attribute-详解)
- [六、流式响应的可观测](#六流式响应的可观测)
- [七、网关层可观测的特有维度](#七网关层可观测的特有维度)
- [八、存储与查询：可观测的"成本"问题](#八存储与查询可观测的成本问题)
- [九、隐私与合规：日志的"内容维度"困境](#九隐私与合规日志的内容维度困境)
- [十、主流实现对比](#十主流实现对比)
- [十一、未解难题与研究前沿](#十一未解难题与研究前沿)
- [十二、参考资料](#十二参考资料)

---

## 一、为什么 LLM 场景的可观测是"新问题"

### 1.1 传统可观测解决什么

传统应用：Metrics + Logs + Traces  
核心问题：**这个请求花了多久？调了哪些服务？有没有报错？**

### 1.2 LLM 场景多了什么

| 维度 | 传统应用 | LLM 应用 |
|---|---|---|
| 业务指标 | RT、QPS、错误率 | **任务完成率、用户接受率** |
| 资源消耗 | CPU、内存、带宽 | **Token 数、$ 成本** |
| 输入输出 | 结构化（JSON Schema） | **半结构化 + 自由文本** |
| 质量评估 | 单元测试 | **LLM-as-Judge、人类评分** |
| 决策追溯 | 调用栈 | **路由决策 / 提示词版本** |
| 安全审计 | 访问日志 | **PII 检测、内容过滤** |

### 1.3 "可观测"在 LLM 时代的边界

```
可观测 = 看得见（Metrics）
       + 看得清（Logs）
       + 追得回（Traces）
       + 量得准（成本/质量）
       + 找得到（业务归因）
       + 守得住（合规审计）
```

---

## 二、可观测三大支柱：Metrics / Logs / Traces

### 2.1 Metrics

**核心指标**：

| 指标 | 含义 | 单位 |
|---|---|---|
| `llm.requests.total` | 总请求数 | count |
| `llm.tokens.prompt` | Prompt token 数 | tokens |
| `llm.tokens.completion` | Completion token 数 | tokens |
| `llm.tokens.total` | 总 token 数 | tokens |
| `llm.cost.usd` | 单次请求成本 | USD |
| `llm.latency.first_token` | 首 token 延迟 | ms |
| `llm.latency.total` | 总延迟 | ms |
| `llm.errors.total` | 错误数 | count |
| `llm.cache.hits` | 缓存命中数 | count |
| `llm.cache.misses` | 缓存未命中数 | count |

**标签维度**（`tags` / `labels`）：
- `model`
- `provider`
- `user_id`
- `tenant_id`
- `route_strategy`
- `cache_status`

### 2.2 Logs

**结构化日志字段**：

```json
{
  "timestamp": "2026-06-05T10:30:00Z",
  "request_id": "req-abc123",
  "user_id": "user-456",
  "tenant_id": "tenant-789",
  "model": "gpt-4o",
  "provider": "openai",
  "request": {
    "messages": [...],
    "temperature": 0.7,
    "max_tokens": 1000
  },
  "response": {
    "content": "...",
    "finish_reason": "stop",
    "usage": {...}
  },
  "latency_ms": 1500,
  "cost_usd": 0.012,
  "route_decision": "fallback_to_claude_because_gpt4_rate_limit",
  "cache_status": "miss"
}
```

**日志的"内容"困境**：
- ✅ 想要：完整的请求/响应，便于回放
- ❌ 担心：PII、合规、存储成本
- 折中：可选开启"详细日志"，加 retention 策略

### 2.3 Traces

**调用链结构**（典型 LLM 应用）：

```
HTTP Request: POST /api/chat
└── Span: handle_chat_request        [50ms total]
    ├── Span: load_user_context      [5ms]
    ├── Span: classify_intent         [20ms]   (LLM call #1)
    ├── Span: retrieve_documents      [200ms]  (vector db)
    ├── Span: build_prompt            [2ms]
    ├── Span: llm_call                [1500ms] (LLM call #2)
    │   ├── Attributes: model=gpt-4o
    │   ├── Attributes: tokens=1200+800
    │   ├── Attributes: cost=$0.012
    │   └── Events: first_token_at=200ms
    ├── Span: post_process            [10ms]
    └── Span: write_to_db             [15ms]
```

**关键 Span 事件**（`Span Events`）：
- `gen_ai.choice` — 模型返回
- `gen_ai.user.message` — 用户消息
- `gen_ai.system.message` — 系统消息
- `gen_ai.tool.message` — 工具返回

---

## 三、OpenTelemetry 基础回顾

### 3.1 OTel 是什么

**OpenTelemetry** = CNCF 的可观测标准，**统一**了 Metrics / Logs / Traces 的 API、SDK、数据格式。

### 3.2 三件套

| 组件 | 作用 |
|---|---|
| **API** | 编程语言层面的接口 |
| **SDK** | API 的实现，配置导出 |
| **Collector** | 接收、处理、转发 telemetry 数据 |

### 3.3 核心概念

- **Span**：一个工作单元（一次函数调用、一次 RPC、一次 LLM 调用）
- **Trace**：一组 Span 组成的有向无环图（DAG）
- **Attribute**：Span 上的 key-value 标签
- **Event**：Span 时间线上的事件
- **Context**：跨服务传播的 trace 标识

### 3.4 数据格式

- **OTLP**（OpenTelemetry Protocol）—— 跨服务传输
- **Jaeger Thrift** —— 老格式
- **Zipkin v2** —— 老格式
- OTLP 是未来方向

---

## 四、OpenLLMetry 标准深入

### 4.1 是什么

**OpenLLMetry** = OpenTelemetry 的 LLM 扩展，**Traceloop**（现合并入 ServiceNow）主导。  
官方：openllmetry.io

### 4.2 设计目标

- 在 OTel 标准之上定义 LLM 特定的 attribute 和 event
- 不破坏 OTel 兼容性
- 让任何 LLM 框架都能用同一套可观测数据

### 4.3 标准化范围

```
OpenLLMetry
    ├── Instrumentation（自动埋点）
    │     ├── OpenAI
    │     ├── Anthropic
    │     ├── Cohere
    │     ├── HuggingFace
    │     ├── Bedrock
    │     ├── Vertex AI
    │     ├── Replicate
    │     ├── Together
    │     ├── Mistral
    │     ├── Ollama
    │     └── ...
    ├── Semantic Conventions（语义约定）
    └── Exporters（导出器）
          ├── OTLP
          ├── Langfuse
          ├── Honeycomb
          ├── Datadog
          └── ...
```

### 4.4 关键 Span 类型

```yaml
# GenAI 客户端 Span
- name: "openai.chat"
  kind: CLIENT
  attributes:
    gen_ai.system: "openai"
    gen_ai.request.model: "gpt-4o"
    gen_ai.request.max_tokens: 1000
    gen_ai.request.temperature: 0.7
    gen_ai.usage.input_tokens: 200
    gen_ai.usage.output_tokens: 150
    gen_ai.response.model: "gpt-4o-2024-08-06"
    gen_ai.response.finish_reasons: ["stop"]

# Embedding Span
- name: "openai.embeddings"
  attributes:
    gen_ai.system: "openai"
    gen_ai.request.model: "text-embedding-3-small"
    gen_ai.usage.input_tokens: 100

# Tool Span
- name: "execute_tool get_weather"
  attributes:
    gen_ai.tool.name: "get_weather"
    gen_ai.tool.description: "Get current weather"
    gen_ai.tool.call_id: "call_xxx"
```

### 4.5 标准化属性（部分）

#### 请求属性

| Attribute | 含义 |
|---|---|
| `gen_ai.system` | 提供商（openai / anthropic / ...） |
| `gen_ai.request.model` | 请求的模型 |
| `gen_ai.request.max_tokens` | 最大 token |
| `gen_ai.request.temperature` | 温度 |
| `gen_ai.request.top_p` | top_p |
| `gen_ai.request.frequency_penalty` | frequency penalty |
| `gen_ai.request.presence_penalty` | presence penalty |
| `gen_ai.request.stop_sequences` | 停止序列 |
| `gen_ai.request.seed` | 随机种子 |
| `gen_ai.request.encoding_formats` | embedding 编码格式 |

#### 响应属性

| Attribute | 含义 |
|---|---|
| `gen_ai.response.model` | 实际使用的模型 |
| `gen_ai.response.id` | 响应 ID |
| `gen_ai.response.finish_reasons` | 终止原因 |
| `gen_ai.usage.input_tokens` | 输入 token |
| `gen_ai.usage.output_tokens` | 输出 token |

#### 内容属性（可选）

| Attribute | 含义 |
|---|---|
| `gen_ai.content.prompt` | 完整 prompt |
| `gen_ai.content.completion` | 完整 completion |
| `gen_ai.content.tool_calls` | 工具调用 |

> 注意：内容属性默认是 **关闭的**（隐私）

---

## 五、关键 Span 与 Attribute 详解

### 5.1 标准 Span 层次

```
Trace: handle_user_query
├── Span: receive_request              [HTTP server]
│   attributes: http.method, http.route
├── Span: load_user_context            [DB]
├── Span: classify_intent              [LLM client]
│   attributes: gen_ai.system=openai, gen_ai.request.model=gpt-4o-mini
│   events:
│     - gen_ai.choice (model output)
├── Span: retrieve_documents           [Vector DB]
│   attributes: db.system=pinecone
├── Span: generate_response            [LLM client]
│   attributes: gen_ai.system=openai, gen_ai.request.model=gpt-4o
│   events:
│     - gen_ai.system.message
│     - gen_ai.user.message
│     - gen_ai.choice
│     - gen_ai.choice (streaming chunks aggregated)
├── Span: stream_to_client              [HTTP server]
│   attributes: http.content_type=text/event-stream
```

### 5.2 关键 Event 类型

```python
# 用户消息事件
span.add_event("gen_ai.user.message", {
    "content": "How is the weather in SF?"
})

# 助手消息事件
span.add_event("gen_ai.choice", {
    "index": 0,
    "finish_reason": "stop",
    "message": {"role": "assistant", "content": "It's 65°F and sunny"}
})

# 工具调用事件
span.add_event("gen_ai.tool.message", {
    "id": "call_xxx",
    "name": "get_weather",
    "content": '{"temp": 65, "condition": "sunny"}'
})
```

### 5.3 多模态扩展

```yaml
# 图像输入
gen_ai.content.prompt:
  - type: text
    text: "What's in this image?"
  - type: image
    source: {type: "url", url: "https://..."}
  - type: image
    source: {type: "base64", media_type: "image/png", data: "..."}

# 语音输入
gen_ai.content.prompt:
  - type: audio
    source: {type: "base64", media_type: "audio/mp3", data: "..."}
```

OpenLLMetry 正在与 **OpenTelemetry GenAI SIG** 一起定义多模态约定。

---

## 六、流式响应的可观测

### 6.1 难点

| 难点 | 描述 |
|---|---|
| **延迟** | 流式响应持续几秒到几十秒 |
| **Token 统计** | 流式 chunk 增量到达 |
| **错误处理** | 流到一半断连 |
| **Span 生命周期** | Span 何时结束？ |
| **事件粒度** | 每个 chunk 都发事件吗？ |

### 6.2 三种实现模式

#### 模式 A：聚合事件

```python
with tracer.start_as_current_span("llm_call") as span:
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    
    # 流结束后，一次性记录
    span.set_attribute("gen_ai.usage.output_tokens", count_tokens(chunks))
    span.add_event("gen_ai.choice", {
        "content": aggregate(chunks)
    })
```

**优点**：Span 生命周期清晰、事件数少  
**缺点**：无法看到流式过程、TTFT 难算

#### 模式 B：增量事件

```python
with tracer.start_as_current_span("llm_call") as span:
    first_token_time = None
    output_tokens = 0
    async for chunk in stream:
        if first_token_time is None:
            first_token_time = time.time()
            span.add_event("gen_ai.first_token")
        output_tokens += 1
        span.add_event("gen_ai.chunk", {"content": chunk.content})
    
    span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
    span.set_attribute("gen_ai.latency.first_token_ms", 
                        (first_token_time - start) * 1000)
```

**优点**：能看到完整流式过程、TTFT 准确  
**缺点**：事件数巨大、存储成本高

#### 模式 C：混合（推荐）

```python
with tracer.start_as_current_span("llm_call") as span:
    # 关键事件
    first_token_event = None
    output_tokens = 0
    aggregated_content = ""
    
    async for chunk in stream:
        if first_token_event is None and chunk.content:
            first_token_event = time.time()
        output_tokens += 1
        aggregated_content += chunk.content
    
    # Span 结束时一次性记录关键信息
    span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
    span.set_attribute("gen_ai.latency.first_token_ms", 
                        (first_token_event - start) * 1000)
    
    # 完整内容作为最后一个 event
    span.add_event("gen_ai.choice", {
        "index": 0,
        "finish_reason": "stop",
        "content": aggregated_content
    })
```

### 6.3 TTFT 与 ITL

| 指标 | 含义 | 测量方式 |
|---|---|---|
| **TTFT** (Time To First Token) | 第一个 token 延迟 | 第一个非空 chunk 到达时间 |
| **ITL** (Inter-Token Latency) | token 间延迟 | 相邻 chunk 时间差 |
| **TPOT** (Time Per Output Token) | 平均每 token 延迟 | 总输出时间 / token 数 |

---

## 七、网关层可观测的特有维度

### 7.1 网关 vs 应用层可观测

| 维度 | 应用层 | 网关层 |
|---|---|---|
| **可见性** | 单个应用的请求 | 跨应用、跨用户、跨模型 |
| **归一化** | 不归一化 | 统一协议、统一指标 |
| **成本归因** | 单应用成本 | **按用户/租户/团队归因** |
| **路由决策** | 业务路由 | **模型路由决策** |
| **缓存** | 业务缓存 | **跨应用语义缓存** |
| **PII 检测** | 应用内 | **网关层 PII 拦截** |

### 7.2 网关特有 Span

```yaml
- name: "ai_gateway.request"
  attributes:
    gateway.route_strategy: "cost_optimized"
    gateway.selected_model: "gpt-4o-mini"
    gateway.fallback_used: false
    gateway.cache_status: "hit"
    gateway.semantic_cache_similarity: 0.94
    gateway.guardrail_triggered: false
    gateway.pii_detected: false
    gateway.tokens_saved: 850
    gateway.cost_saved_usd: 0.008
    gateway.user_id: "user-456"
    gateway.tenant_id: "tenant-789"
    gateway.api_key_id: "key-abc"
```

### 7.3 路由决策可观测

```python
span.add_event("gateway.route_decision", {
    "strategy": "cost_optimized",
    "candidates": ["gpt-4o", "gpt-4o-mini", "claude-haiku"],
    "scores": {
        "gpt-4o": 0.82,
        "gpt-4o-mini": 0.75,
        "claude-haiku": 0.73
    },
    "selected": "gpt-4o",
    "reason": "highest quality score within cost budget"
})
```

### 7.4 成本归因

```
总成本 = $1000/day
├── 部门 A: $600 (60%)
│     ├── 项目 X: $400
│     ├── 项目 Y: $200
├── 部门 B: $300 (30%)
└── 部门 C: $100 (10%)
```

通过 `tenant_id`、`project_id`、`user_id` 三个 label 维度归因。

---

## 八、存储与查询：可观测的"成本"问题

### 8.1 存储选型

| 工具 | 用途 | 规模 |
|---|---|---|
| **Prometheus** | Metrics | 中小规模 |
| **ClickHouse** | Logs / Traces | 海量（成本最低） |
| **Elasticsearch** | Logs（带全文搜索） | 中大规模 |
| **Jaeger** | Traces | 中等规模 |
| **Tempo** | Traces（低成本） | 大规模 |
| **Langfuse** | LLM-specific | 中等规模 |
| **Phoenix (Arize)** | LLM-specific | 中等规模 |
| **Helicone** | LLM SaaS | 任意 |

### 8.2 成本估算

假设每天 100 万次 LLM 请求：

| 数据类型 | 单条大小 | 总量/天 | 月成本（ClickHouse 自建） |
|---|---|---|---|
| Metrics | ~1 KB | 1 GB | 极低 |
| Traces（不含内容） | ~5 KB | 5 GB | 低 |
| Logs（不含内容） | ~2 KB | 2 GB | 低 |
| Logs（含内容） | ~20 KB | 20 GB | 中 |
| Logs（含内容 + 多模态） | ~500 KB | 500 GB | **高** |

### 8.3 存储策略

#### 策略 1：分级存储

```
Hot（7 天）：ClickHouse SSD，详细数据
Warm（30 天）：ClickHouse HDD，只保留指标
Cold（永久）：S3 / OSS，压缩归档
```

#### 策略 2：采样

- **完整采样**：1%（重放需要）
- **指标采样**：100%（聚合数据便宜）
- **错误采样**：100%（排查问题）

#### 策略 3：内容可选

```python
# 配置项
LOG_LEVEL = "full"  # full / metadata / metrics-only

# 业务关键请求 → full
# 普通请求 → metadata
# 健康检查 → metrics-only
```

---

## 九、隐私与合规：日志的"内容维度"困境

### 9.1 三大冲突

| 想要 | 担心 |
|---|---|
| 完整的请求/响应（便于回放） | PII 泄露 |
| 长期存储（趋势分析） | GDPR / 数据保护法 |
| 用户行为分析（提升产品） | 用户隐私 |

### 9.2 应对策略

#### 策略 1：PII 检测与脱敏

```python
from presidio_analyzer import AnalyzerEngine

def redact_pii(text):
    analyzer = AnalyzerEngine()
    results = analyzer.analyze(text=text, language='en')
    for r in results:
        text = text.replace(text[r.start:r.end], f"[{r.entity_type}]")
    return text

# 存储前脱敏
log_request = {
    "request": redact_pii(original_request),
    "response": redact_pii(original_response),
}
```

#### 策略 2：内容哈希存储

```python
# 不存原文，只存 hash + 统计
log_entry = {
    "request_hash": hash(request),
    "request_length": len(request),
    "response_hash": hash(response),
    "response_length": len(response),
    # 关键内容片段（截断）
    "request_excerpt": request[:200],
    "response_excerpt": response[:200],
}
```

#### 策略 3：租户隔离日志存储

```
租户 A 的日志 → 存储 A
租户 B 的日志 → 存储 B
绝不混存
```

#### 策略 4：可配置日志保留

```python
# 配置
LOG_RETENTION = {
    "metrics": 90,        # 天
    "traces_no_content": 30,
    "traces_with_content": 7,  # 7 天就过期
    "pii_free_logs": 365,
}
```

### 9.3 合规框架

| 法规 | 要求 |
|---|---|
| **GDPR** | 数据可删除、可访问、最小化 |
| **CCPA** | 加州用户数据权利 |
| **HIPAA** | 医疗数据保护（强） |
| **等保 2.0** | 国内安全等级保护 |
| **SOC 2** | SaaS 审计标准 |

---

## 十、主流实现对比

### 10.1 商业方案

| 产品 | 特点 | 价格 |
|---|---|---|
| **LangSmith** | LangChain 一体化 | 订阅 |
| **Langfuse (Cloud)** | 开源 + 云 | 免费层 + 用量 |
| **Helicone** | 极简接入 | 免费层 + 用量 |
| **Arize Phoenix** | 开源 + 云 | 免费 + 订阅 |
| **Datadog LLM Observability** | 大而全 | 贵 |
| **New Relic AI Monitoring** | 大而全 | 贵 |
| **Honeycomb** | 高基数查询 | 订阅 |
| **Signoz** | OTel 原生 | 开源 + 云 |

### 10.2 自托管开源

| 项目 | 特点 |
|---|---|
| **Langfuse** | LLM 专用，功能最全 |
| **Phoenix (Arize)** | LLM 评估 + 可观测 |
| **OpenLLMetry** | 标准 + instrumentation |
| **Traceloop** | OpenLLMetry 商业版 |
| **Signoz** | OTel 通用 |
| **Jaeger + ClickHouse** | 自建组合 |

### 10.3 选择决策

| 需求 | 推荐 |
|---|---|
| 快速验证 | Helicone / Langfuse Cloud |
| LangChain 为主 | LangSmith |
| 自托管 + LLM 专用 | Langfuse / Phoenix |
| 大规模 + 低成本 | ClickHouse + OTLP + 自建 |
| 已有 Datadog | Datadog LLM 监控 |

---

## 十一、未解难题与研究前沿

### 11.1 标准层

1. **OpenLLMetry 与 OTel GenAI SIG 的关系**——会不会合并？
2. **多模态可观测的标准化**（图像/音频/视频 attribute）
3. **Agent 多步调用的 trace 标准化**——MCP / A2A 怎么观测？
4. **路由决策可观测**应不应该进标准 attribute？
5. **缓存命中/未命中**应不应该进 span event？

### 11.2 流式层

6. **流式响应的 span 粒度最优解**——每 chunk 一 event vs 聚合？
7. **TTFT、ITL 的标准测量方法**？
8. **流式错误**（流到一半断）怎么在 trace 中表达？
9. **流式响应的成本归因**（用户断连前消耗的 token 算谁的）？

### 11.3 评估层

10. **LLM-as-Judge 与路由 LLM 是否会"串通"**？
11. **离线评测 vs 在线反馈的偏差**如何量化？
12. **多评估器一致性**（LLM 评分员之间）的校准？
13. **评估成本**——评估本身也花钱

### 11.4 存储 / 成本层

14. **大模型时代的可观测存储**该怎么选？
15. **可观测本身的"成本优化"**——采样策略自适应？
16. **冷热数据分级**的自动化？
17. **回放能力 vs 存储成本**的权衡？

### 11.5 隐私 / 合规层

18. **"可观测必要 vs 隐私必要"的边界**——谁来定？
19. **PII 脱敏的召回率 / 精度**如何量化？
20. **差分隐私的可观测**——技术上可行吗？
21. **联邦可观测**——跨组织 trace 共享而不泄露内容？
22. **AI 输出的可观测责任**——输出错的合规责任归谁？

### 11.6 调试 / 诊断层

23. **AI 应用调试**——从用户反馈反推到 prompt 缺陷？
24. **路由决策的"为什么"**——可解释路由的标准化？
25. **跨多个 LLM 的对话一致性诊断**？
26. **Agent 行为回放**——多步调用的"录像"机制？

### 11.7 未来形态

27. **可观测自身 AI 化**——用 LLM 总结异常、用 LLM 生成诊断？
28. **可观测的"预测性"**——预测 token 消耗、预测成本超支
29. **可观测的"自适应采样"**——异常时自动提高采样率
30. **可观测 + Eval 融合**——不再分"可观测"和"评估"

---

## 十二、参考资料

### 12.1 必读

- openllmetry.io（官方）
- opentelemetry.io（基础）
- github.com/traceloop/openllmetry
- github.com/open-telemetry/semantic-conventions（GenAI）
- github.com/Arize-ai/phoenix

### 12.2 论文 / RFC

- "OpenLLMetry: OpenTelemetry for LLM Applications" (Traceloop, 2024)
- OTel GenAI Semantic Conventions
- "Towards Observability for LLM Applications" (Langfuse 博客)
- "LLM Observability: A Survey" (2024)

### 12.3 工具仓库

- github.com/langfuse/langfuse
- github.com/Arize-ai/phoenix
- github.com/Helicone/helicone
- github.com/signoz/signoz
- github.com/jaegertracing/jaeger
- github.com/openobserve/openobserve

### 12.4 关键博客

- Honeycomb "Observability for LLM"
- Datadog "LLM Observability"
- Traceloop "Building OpenLLMetry"
- Langfuse "Open source LLM observability"
- Arize "Phoenix architecture"

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 4 篇
- 主题：可观测与 OpenLLMetry
- 上一份：03-intelligent-routing.md
- 下一份预告：Agent 时代的多步调用与状态管理
