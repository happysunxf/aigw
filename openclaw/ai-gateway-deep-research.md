# AI Gateway 深度研究：架构、原理与演进

> 性质：纯技术研究综述（不涉及采购选型、报价、ROI）
> 目标读者：AI 架构师、平台工程师、技术 Lead
> 价值主张：讲清楚 AI Gateway 在 LLM Infra 栈里的**位置**、**原理**、**设计哲学**与**演进方向**
> 编写时间：2026-06

---

## 目录

- [一、AI Gateway 在 LLM Infra 栈中的位置](#一ai-gateway-在-llm-infra-栈中的位置)
- [二、与传统 API 网关的本质区别](#二与传统-api-网关的本质区别)
- [三、核心能力的实现原理](#三核心能力的实现原理)
- [四、主流产品的架构拆解](#四主流产品的架构拆解)
- [五、设计哲学对比](#五设计哲学对比)
- [六、性能与可扩展性研究](#六性能与可扩展性研究)
- [七、关键技术挑战与未解难题](#七关键技术挑战与未解难题)
- [八、演进方向：2026 及之后](#八演进方向2026-及之后)
- [九、值得关注的开源与标准](#九值得关注的开源与标准)
- [十、给研究者的问题清单](#十给研究者的问题清单)
- [十一、参考资料](#十一参考资料)

---

## 一、AI Gateway 在 LLM Infra 栈中的位置

### 1.1 整体栈视图

```
┌────────────────────────────────────────────────────────────────┐
│ 应用层 (Applications)                                          │
│   Chat / Agent / Copilot / RAG / Code Assistant                │
└────────────────────────────┬───────────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────────┐
│ 编排层 (Orchestration)                                         │
│   LangChain / LlamaIndex / Semantic Kernel / Dify / Coze       │
└────────────────────────────┬───────────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────────┐
│ 网关层 (AI Gateway)   ◀── 本报告研究对象                        │
│   鉴权 / 路由 / 限流 / 缓存 / 可观测 / Guardrails / 模板       │
└────────────────────────────┬───────────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────────┐
│ 模型层 (Model Serving)                                         │
│   OpenAI / Anthropic / 自托管 (vLLM / TGI / Triton) / 国产模型 │
└────────────────────────────┬───────────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────────┐
│ 基础设施 (Infra)                                               │
│   K8s / Envoy / Service Mesh / Edge Network / Observability     │
└────────────────────────────────────────────────────────────────┘
```

### 1.2 网关层的"三明治"位置

AI Gateway **既不属于应用层，也不属于模型层**——它是**横向能力**。这一位置决定了它的几个本质特征：

1. **协议多**：必须同时懂 OpenAI 协议、Anthropic 协议、Google Gemini 协议、HuggingFace Inference Endpoint、私有协议
2. **状态多**：要管理 key、用户、配额、缓存、灰度策略
3. **可插拔**：能力必须可组合（用户可能只要鉴权 + 路由，不要 Guardrails）
4. **对延迟敏感**：每多一跳都直接影响用户体验

### 1.3 与相邻层的关系

| 与编排层关系 | 与模型层关系 |
|---|---|
| 网关**不应该**承担"业务编排"职责（这是 LangChain 的活）| 网关**可以**做"模型路由决策"，但**不应该**做"模型推理" |
| 编排层**调用**网关，**而不是反过来** | 模型层对网关是**被代理**关系 |
| 共同点：都管"调用" | 共同点：都涉及"模型" |

---

## 二、与传统 API 网关的本质区别

### 2.1 表面相似 vs 深层差异

| 维度 | 传统 API 网关 | AI Gateway |
|---|---|---|
| 协议 | HTTP/REST、gRPC、GraphQL | **OpenAI 协议 / Anthropic 协议 / SSE 流式** |
| 请求体 | 结构化（JSON Schema） | **半结构化 + 自由文本**（prompt） |
| 响应 | 同步、确定大小 | **流式 / 长度不可预测**（SSE、token-by-token） |
| 限流维度 | QPS、并发数 | **QPS + Token/s + 成本/$ + 单用户配额** |
| 路由粒度 | 路径、Header | **按 prompt 内容、按模型能力、按成本** |
| 缓存 | HTTP 缓存（Vary、ETag） | **语义缓存**（prompt 向量化 + 相似度） |
| 鉴权 | OAuth2 / API Key | **API Key + 用户维度 + 模型访问权限** |
| 可观测 | RT、错误率、状态码 | **Token 消耗、成本、prompt 长度、模型选择分布** |
| 失败语义 | 5xx 重试 | **Fallback 模型、模型降级、prompt 重写** |

### 2.2 关键差异点深度剖析

#### 差异 1：流式响应是第一性挑战

传统 API 网关按"请求-响应"模型设计。LLM 的 SSE 流式响应带来：

- **不能等响应结束再限流**——必须 token-by-token 计量
- **不能等响应结束再缓存**——必须做 partial response 处理
- **错误处理粒度变细**——前 50 token 成功、后 50 token 失败，语义完全不同
- **HTTP/1.1 chunked + HTTP/2 + SSE 兼容**——网关必须正确透传 streaming

这直接淘汰了一批"老牌"网关（Kong 的某些版本、Zuul 1.x）。

#### 差异 2：成本是第一性指标

传统 API 网关的"成本"是基础设施成本（CPU、内存、带宽）。AI Gateway 的"成本"是：

```
单次请求成本 = prompt_tokens × prompt_price + completion_tokens × completion_price
              + 缓存未命中成本 + 路由失败回退成本
```

这导致**计费精度**成为关键能力——必须能精确到 token 级、用户级、模型级。

#### 差异 3：缓存维度革命

传统缓存按"请求 URL + 参数哈希"做 key。LLM 缓存维度：

- **精确缓存**（同 prompt → 同 response）——简单
- **前缀缓存**（prompt 前缀相同）——vLLM 等推理引擎的 KV cache 复用
- **语义缓存**（prompt 语义相似）——embedding 检索 + 阈值判断
- **工具调用结果缓存**（Agent 场景）——结构化

#### 差异 4：可观测的"内容维度"

传统网关只关心"这次请求花了多久、传了多少字节"。AI Gateway 还要关心：

- 这次请求**用了什么 prompt**（可能含敏感信息）
- 这次请求**返回了什么内容**（合规审计）
- **谁**用了多少（按用户/部门归因）
- **为什么**这次调用这个模型（路由决策溯源）

这意味着**可观测不只是 metrics + logs，还要存"请求体 + 响应体"**，对存储和隐私都提出新挑战。

---

## 三、核心能力的实现原理

### 3.1 协议翻译

**核心思想**：把所有模型 API 都翻译成 OpenAI Chat Completions 协议（或反之）。

**实现路径**：

```
Client (OpenAI SDK) 
    │
    ▼
[AI Gateway]  ── 统一协议层 ──▶  各家模型原生 API
                                 │
                                 ├── OpenAI: 透传
                                 ├── Anthropic: system / messages 转换
                                 ├── Gemini:  role + parts 转换
                                 ├── Cohere:  prefix / message 转换
                                 └── 自托管:  OpenAI 协议兼容 vLLM/TGI
```

**关键设计点**：
- **请求归一化**：把 `messages[]`、`temperature`、`max_tokens` 等统一
- **响应归一化**：把各家流式 chunk 序列化成统一格式
- **多模态扩展**：图像、音频、PDF 的 base64 / URL 处理各家不同
- **工具调用归一化**：`tool_calls` 字段各家命名差异（OpenAI 用 `tool_calls`，Anthropic 用 `tool_use`）
- **结构化输出归一化**：`response_format` / `json_schema` 的差异处理

### 3.2 模型路由

**路由策略**（从简单到复杂）：

| 策略 | 描述 | 实现难度 |
|---|---|---|
| **静态路由** | 按 model 字段转发 | ★ |
| **A/B 测试** | 按比例分流到两个模型 | ★★ |
| **Fallback 链** | 主模型失败 → 备模型 | ★★ |
| **负载均衡** | 多 key 轮询 / 加权 | ★★ |
| **成本优先** | 在能用的模型里选最便宜的 | ★★★ |
| **延迟优先** | 在能用的模型里选 P99 最优的 | ★★★ |
| **智能路由** | 按 query 内容自动选模型 | ★★★★ |
| **能力路由** | 按任务类型（代码、翻译、摘要）选擅长模型 | ★★★★ |

**智能路由的典型实现**（参考 Not Diamond / Unify）：
1. 用一个小模型（或 BERT 类）做 query 分类
2. 维护一个"任务类型 → 最优模型"的统计表
3. 每次请求先分类，再选模型
4. 收集反馈（用户是否接受、是否有 retry）持续优化

### 3.3 Token 级缓存

#### 精确缓存

```python
key = hash(model + messages + temperature + tools)
if cache.hit(key):
    return cache.get(key)
```

**难点**：prompt 里的时间戳、随机数、用户上下文需要先"脱敏"再 hash。

#### 语义缓存

```
1. 客户端发 prompt
2. Gateway 把 prompt 编码为 embedding（用 sentence-transformers 或类似模型）
3. 在向量库（Redis / pgvector / Qdrant）里 ANN 检索 Top-K
4. 相似度 > 阈值 → 命中缓存
5. 阈值通常 0.92-0.95
```

**难点**：
- 阈值难调（高了不命中、低了不准）
- 缓存粒度（要不要按 model 分桶？）
- 失效策略（模型升级了，缓存要不要全清？）

#### 前缀缓存（与推理引擎配合）

vLLM、TGI 等推理引擎实现了 **prefix caching**（同一 prefix 的 KV cache 复用）。AI Gateway 可以：

- 在 router 层**不破坏**这种优化（透传 prompt 顺序）
- 甚至**主动重排**多个并发请求，让相同 prefix 走同一个推理实例
- 这是 AI Gateway 与传统网关的本质差异点之一

### 3.4 可观测

**三大支柱**：

| 类型 | 工具 | 关注点 |
|---|---|---|
| **Metrics** | Prometheus / OTel | QPS、延迟、Token/s、$/min、错误率 |
| **Logs** | 结构化日志 / ClickHouse | 请求体、响应体、路由决策 |
| **Traces** | OpenTelemetry / OpenLLMetry | 调用链（Agent 多步调用特别重要） |

**OpenLLMetry**（基于 OTel 的 LLM 扩展）正在成为事实标准——定义了 `llm.usage.*`、`llm.request.*`、`llm.completion.*` 等标准 attribute。

### 3.5 Guardrails

**两种实现路径**：

1. **网关层做**（轻量、通用）：
   - PII 检测（正则 / Presidio）
   - 关键词黑名单
   - 输出长度限制
   - 内容分类（toxic / safe）

2. **模型层做**（重量、专业）：
   - Llama Guard（Meta）
   - ShieldGemma（Google）
   - NeMo Guardrails（NVIDIA）
   - 自训练分类器

**常见架构**：网关做第一道粗筛（拒绝明显违规），模型层做第二道精筛（语义判断）。

### 3.6 Prompt 模板与版本管理

**关键问题**：
- 模板如何参数化（Jinja2 / f-string / structured）
- 模板如何版本化（Git / DVC / 内部 registry）
- 模板如何 A/B 测试（不同 prompt 路由不同流量）
- 模板如何灰度（10% → 50% → 100%）
- 模板如何回滚

**Portkey 的做法**：把 prompt 当作"基础设施资源"，与 config / model / guardrail 一起管理。

---

## 四、主流产品的架构拆解

### 4.1 LiteLLM（Python 派）

**架构**：
```
LiteLLM Router
    ├── 100+ Provider Adapters（每个一个类）
    ├── Routing Strategies（simple-shuffle, usage-based, latency-based）
    ├── Caching Layer（Redis / in-memory / Qdrant）
    └── Observability（Langfuse / OpenTelemetry / Sentry）
```

**核心设计**：
- **Python 类继承体系**：每个 provider 一个 `BaseLLM` 子类
- **Callback 机制**：请求/响应/错误都有 hook
- **Config 驱动**：`config.yaml` 描述所有路由
- **OpenAI 协议兼容**：直接替换 `base_url` 就能用 OpenAI SDK

**优劣**：
- ✅ 协议覆盖最全、接入最快、Python 生态友好
- ❌ 性能不如 Go 实现（高 QPS 下 P99 偏高）
- ❌ 企业特性弱（多租户、审计需自研）

### 4.2 Portkey Gateway（Go 派）

**架构**：
```
Portkey Gateway (Go)
    ├── Middleware Chain（鉴权 → 限流 → 缓存 → 路由 → Guardrail → 日志）
    ├── Config Provider（本地 / 远端 API）
    ├── Provider Adapters（50+ 主流 provider）
    └── 集成：Langfuse / OpenLLMetry / Helicone
```

**核心设计**：
- **中间件链**：所有能力都做成中间件，组合灵活
- **Config 优先**：所有路由/限流/缓存策略都是 config 声明式
- **AI 厂商中立**：明确不绑任何模型厂商
- **可观测深度集成**：原生对接 Langfuse / Opik / Helicone

**优劣**：
- ✅ 性能好、灵活、企业特性完整
- ❌ 自部署运维有门槛
- ❌ 国内模型覆盖弱

### 4.3 Higress（Envoy 派）

**架构**：
```
Higress
    ├── Envoy 内核（HTTP / HTTP2 / gRPC / SSE 透传）
    ├── AI 插件体系（Wasm 插件）
    │     ├── ai-router（模型路由）
    │     ├── ai-rate-limiting（Token 级限流）
    │     ├── ai-statistics（Token 统计）
    │     └── ai-prompt-template（Prompt 模板）
    ├── Istio 控制面集成
    └── Ingress Gateway / 微服务网关双形态
```

**核心设计**：
- **Envoy 底座**：复用 Service Mesh 的稳定性、流量控制、可观测
- **Wasm 插件**：用 Go / Rust 写插件，热加载，沙箱安全
- **K8s 原生**：CRD 管理所有配置
- **国内模型深度优化**：通义/百炼/豆包/DeepSeek 都有官方插件

**优劣**：
- ✅ 性能极佳（Envoy C++ 内核）、K8s 友好
- ✅ 阿里云背书、稳定性强
- ❌ 概念多、学习曲线陡
- ❌ 非 K8s 场景优势不明显

### 4.4 One API / New API（轻量 Go 派）

**架构**：
```
One API
    ├── 渠道（Channel）管理：每个渠道 = 一个上游 API
    ├── 用户（User）管理：每个用户绑定渠道 + 配额
    ├── 分发（Dispatch）逻辑：按用户/模型选渠道
    └── 计量（Billing）系统：按 token 计费
```

**核心设计**：
- **渠道模型**："用户购买 token → 在多个渠道里分发"，本质是"二级代理商"思路
- **极轻部署**：单二进制 + SQLite，五分钟跑起来
- **OpenAI 协议**：完全兼容

**优劣**：
- ✅ 极轻、自托管最简单
- ✅ 国内模型渠道全
- ❌ 偏"转售"、企业特性弱
- ❌ 路由策略简单（按渠道轮询，不做智能路由）

### 4.5 Helicone（可观测派）

**架构**：
```
Helicone Proxy
    ├── 请求拦截（反向代理）
    ├── 结构化日志（ClickHouse）
    ├── 异步上报（批处理）
    └── 用户/请求维度分析
```

**核心设计**：
- **日志优先**：把所有请求/响应/Token 都结构化存下来
- **异步批处理**：不影响主链路延迟
- **ClickHouse 列存**：海量日志低成本
- **可观测 > 路由**：把"看清用在哪"放在第一位

**优劣**：
- ✅ 数据洞察强、成本归因清晰
- ✅ 自托管 + SaaS 双形态
- ❌ 路由/限流等"控制"能力弱
- ❌ Guardrails 需外挂

### 4.6 Cloudflare AI Gateway（边缘派）

**架构**：
```
Cloudflare Edge Network
    ├── 边缘缓存（精确 + 语义）
    ├── 边缘日志（Workers Analytics）
    ├── 边缘限流（每个 PoP 独立）
    └── 边缘安全（DDoS / WAF）
```

**核心设计**：
- **边缘缓存**：请求根本不打回源站，缓存命中直接返回
- **Workers 生态**：用 JavaScript 写自定义逻辑
- **全球分布**：300+ PoP，延迟天然低

**优劣**：
- ✅ 边缘优势碾压（延迟、缓存、成本）
- ✅ 零运维、按用量付费
- ❌ 深度自定义受限
- ❌ 私有化合规弱

---

## 五、设计哲学对比

### 5.1 四种哲学

| 哲学 | 代表 | 核心信念 |
|---|---|---|
| **协议翻译之王** | LiteLLM | "什么模型都能塞进来" |
| **中间件灵活** | Portkey | "能力可组合、配置驱动" |
| **基础设施派** | Higress / Envoy | "基于成熟的 Service Mesh" |
| **可观测先行** | Helicone | "先看清数据，再说控制" |
| **边缘最优** | Cloudflare | "请求别回源" |
| **渠道分发** | One API | "多渠道、多用户、多账单" |

### 5.2 哲学背后的取舍

- **协议翻译之王** → 牺牲性能、企业特性换兼容性
- **中间件灵活** → 牺牲简单性、概念多换扩展性
- **基础设施派** → 牺牲轻量性、学习成本换稳定性
- **可观测先行** → 牺牲控制粒度换洞察深度
- **边缘最优** → 牺牲控制力换延迟 / 成本
- **渠道分发** → 牺牲智能路由换极简部署

**没有银弹**——选择哲学 = 选择你最在意的"维度"。

---

## 六、性能与可扩展性研究

### 6.1 性能关键指标

| 指标 | 含义 | 数量级 |
|---|---|---|
| **P50 延迟增量** | 网关引入的延迟 | 5-30 ms |
| **P99 延迟增量** | 长尾延迟 | 50-200 ms |
| **吞吐** | 每秒处理请求数 | 100-10k RPS（单实例） |
| **Token/s** | 每秒处理的 token 数 | 视实现 |
| **内存占用** | 单实例内存 | 100 MB - 2 GB |
| **冷启动** | 首次启动时间 | 1-30 s |

### 6.2 实现差异

- **Go 实现**（Portkey、Higress、One API）：吞吐高、P99 低、内存小
- **Python 实现**（LiteLLM）：吞吐中等、冷启动慢
- **Envoy C++ 实现**（Higress 内核）：吞吐最高、内存控制好

### 6.3 性能优化技巧

1. **流式透传**：不要 buffer 完整响应再转发，要 chunk-by-chunk
2. **连接池**：复用上游 HTTP 连接（HTTP/2 multiplexing）
3. **缓存热点**：用 LRU + 语义缓存双层
4. **异步日志**：日志写入异步化、不阻塞主链路
5. **限流算法**：用 token bucket 不用滑动窗口（GC 友好）
6. **向量化批处理**：embedding 检索要 batch

### 6.4 可扩展性架构

```
                    ┌─ Gateway Node 1 ─┐
Client ──LB──▶     ├─ Gateway Node 2 ─┤ ──▶ 上游模型
                    └─ Gateway Node N ─┘
                            │
                    ┌───────┴───────┐
                    │   共享状态    │
                    │  Redis/PG/   │
                    │  ClickHouse  │
                    └───────────────┘
```

**关键设计**：
- 限流计数共享（Redis 原子操作）
- 缓存共享（Redis Cluster）
- 配置中心化（etcd / Consul / DB）
- 日志/指标中心化（OTel Collector）

---

## 七、关键技术挑战与未解难题

### 7.1 已部分解决

| 难题 | 现状 |
|---|---|
| 多协议兼容 | ✅ 几乎解决（OpenAI 协议已成事实标准） |
| Token 级计量 | ✅ 各家都实现 |
| 流式响应透传 | ✅ 主流都支持 |
| 基础限流 | ✅ Token bucket 够用 |
| 基础缓存 | ✅ 精确缓存成熟 |
| 可观测 | ✅ OpenLLMetry 标准在推 |

### 7.2 仍未解决（研究热点）

#### 难题 1：语义缓存的"准与快"权衡
- 阈值高了不命中、低了误命中
- Embedding 模型本身在演进
- 多模态输入（图像 + 文本）如何做语义缓存？
- **研究前沿**：用 LLM 自身做"是否可缓存"判断

#### 难题 2：智能路由的"决策成本"
- 用一个模型做路由决策，本身就要花钱、要有延迟
- 在边缘场景（10ms 预算）根本来不及
- 决策质量难以离线评估
- **研究前沿**：小模型蒸馏路由决策 / 用统计 + 规则代替 LLM 决策

#### 难题 3：Agent 多步调用的可观测
- 一个 Agent 任务可能 10+ 步 LLM 调用
- 失败定位、token 归因、成本分摊都难
- **研究前沿**：标准化的 Agent tracing（LangSmith / OpenLLMetry 都在做）

#### 难题 4：跨模型的成本-质量-延迟三维优化
- 理论上 Pareto 前沿可以算
- 实际中"质量"难量化（人类偏好 / 任务成功率）
- **研究前沿**：用 LLM-as-a-Judge 做在线质量评估

#### 难题 5：Guardrails 的"过度拦截 vs 漏放"
- 高敏感场景（医疗、金融）漏放代价大
- 过度拦截又影响业务
- 阈值 + 多模型组合是常见做法，但成本高
- **研究前沿**：分级 Guardrail（网关粗筛 + 模型精筛 + 人工兜底）

#### 难题 6：缓存与隐私的冲突
- 语义缓存把 prompt 编码存起来 → 可能泄露
- 跨租户缓存隔离 vs 命中率
- **研究前沿**：差分隐私 / 同态加密的语义缓存（早期）

#### 难题 7：流式响应下的限流与计费
- 请求还在流式返回 → 用户可能断连
- 已经消耗的 token 算谁的？
- **研究前沿**：流式响应提前终止的 token 估算模型

---

## 八、演进方向：2026 及之后

### 8.1 短期（1-2 年）

- **标准化加速**：OpenLLMetry 成熟，跨厂商可观测可移植
- **Agent 专属网关**：单独一类，处理多步调用、工具调用、状态管理
- **多模态原生**：图像、音频、视频的统一代理（当前多是文本）
- **边缘 AI Gateway**：类似 Cloudflare 模式的边缘缓存普及

### 8.2 中期（3-5 年）

- **LLM-as-a-Router 成熟**：用 LLM 做实时智能路由，质量稳定
- **自适应限流**：根据模型价格、延迟动态调整策略
- **统一模型协议**：可能形成新的事实标准（OpenAI 协议后继者）
- **细粒度语义缓存**：embedding 模型与缓存策略联合优化
- **可解释路由决策**：能回放"为什么选了这个模型"

### 8.3 长期（5+ 年，未知）

- **推理引擎 + 网关融合**：vLLM 等推理引擎内嵌网关能力
- **浏览器原生 LLM 协议**：减少一跳
- **联邦学习 + 路由**：在隐私约束下做模型选择
- **AI Gateway 自身的 AI 化**：用 LLM 优化 LLM 调用

### 8.4 几个值得关注的趋势

| 趋势 | 信号 |
|---|---|
| **CNCF 接管** | Envoy AI Gateway 出现 → 服务网格派系进场 |
| **云厂商绑定** | 阿里云 Higress 商业版 / Apigee AI → 上云企业被锁定 |
| **SaaS 化加速** | Portkey Cloud / Helicone 增长 → 自托管门槛在提高 |
| **Agent 框架自建网关** | LangChain / LlamaIndex 都有内置代理 → 编排层下沉 |
| **国产化深入** | Higress / APISIX / One API 都吃信创红利 |

---

## 九、值得关注的开源与标准

### 9.1 必看开源项目

| 项目 | 价值 |
|---|---|
| github.com/Portkey-AI/gateway | 中间件派最佳实践 |
| github.com/BerriAI/litellm | 协议翻译范本 |
| github.com/songquanpeng/one-api | 极轻自托管范本 |
| github.com/alibaba/higress | 基础设施派范本 |
| github.com/Helicone/helicone | 可观测派范本 |
| github.com/envoyproxy/ai-gateway | 标准化路线 |
| github.com/traceloop/opentelemetry-llm | OpenLLMetry 标准实现 |

### 9.2 关注的标准

- **OpenAI Chat Completions API** —— 事实标准
- **Anthropic Messages API** —— 第二大生态
- **OpenLLMetry**（OpenTelemetry LLM 扩展）—— 可观测标准
- **MCP（Model Context Protocol）** —— 工具调用标准（Anthropic 主推）
- **A2A（Agent-to-Agent）** —— Google 推的 agent 通信

### 9.3 关键论文 / 博客

- "The AI Gateway Stack"（a16z）
- OpenLLMetry 设计文档
- Cloudflare AI Gateway 架构博客
- Higress 架构白皮书
- vLLM PagedAttention 论文（理解推理引擎）

---

## 十、给研究者的问题清单

如果你要在这个方向做研究/写文章/做演讲，下面这些问题值得思考：

### 10.1 架构层

1. AI Gateway 与编排层（LangChain）的职责边界到底应该在哪？
2. 未来 AI Gateway 会不会被推理引擎吸收？
3. 多 Agent 场景下，"网关"和"编排器"是不是同一回事？

### 10.2 性能层

4. 流式响应下，限流精度的极限是多少？
5. 语义缓存能贡献多少命中率？阈值应该怎么自适应？
6. 边缘 AI Gateway 与中心 AI Gateway 的延迟差异有多大？

### 10.3 经济层

7. 智能路由决策本身的花销值得吗？（路由决策成本 vs 路由带来的节省）
8. 缓存命中率的边际收益曲线？
9. Token 级计费的精度极限？

### 10.4 安全 / 合规层

10. 网关层 Guardrails 的拦截率与误报率关系？
11. 跨租户语义缓存的隐私隔离怎么做？
12. 模型输出审计的法律风险如何技术性规避？

### 10.5 标准化层

13. OpenAI 协议会不会在 5 年内被新协议取代？
14. OpenLLMetry 能否成为真正的"LLM 可观测标准"？
15. MCP 能不能统一工具调用协议？

### 10.6 演进层

16. AI Gateway 自身的"AI 化"会是什么样的？
17. 推理引擎（vLLM）+ 网关是否会融合成一个新物种？
18. Agent 时代的网关需要哪些新能力？

---

## 十一、参考资料

### 11.1 必读仓库

- github.com/Portkey-AI/gateway
- github.com/BerriAI/litellm
- github.com/songquanpeng/one-api
- github.com/alibaba/higress
- github.com/api7/apisix
- github.com/envoyproxy/ai-gateway
- github.com/Helicone/helicone
- github.com/traceloop/opentelemetry-llm

### 11.2 文档

- docs.portkey.ai
- docs.litellm.ai
- higress.cn
- developers.cloudflare.com/ai-gateway
- openllmetry.io
- modelcontextprotocol.io（MCP）

### 11.3 行业研究

- a16z: "The AI Gateway Stack"
- LangChain State of AI Agents
- Solo.io blog（Envoy AI Gateway）
- Cloudflare Radar 数据
- 沙丘智库 / 甲子光年（国内 LLM Infra 报告）

---

## 报告维护

- 报告版本：v1.0
- 性质：纯技术研究综述（**不**提供采购建议）
- 维护人：Rich + 小F
- 下次更新：网络工具恢复后补充 2026 Q2 最新动态
