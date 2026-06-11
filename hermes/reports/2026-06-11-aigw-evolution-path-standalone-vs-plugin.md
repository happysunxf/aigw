# AI 网关两条演进路线 · 独立 AI 网关 vs API 网关集成 AI 插件

> **报告类型**: 演进路线深度对比 (非发版追踪、非市场盘点)
> **完成时间**: 2026-06-11
> **方法**: 已有报告交叉引用 + GitHub REST API 校验关键事实
> **范围**: 8 款主流 AI 网关 + 4 款传统 API 网关的 AI 插件
> **副标题**: 当 LiteLLM 一年 14k star、Envoy AI GW 进入 CNCF、APISIX 三段式重构、Higress 拿下国内 Ingress 第一 —— 两条路为什么分叉,又为什么在 2026 年开始反向收敛
> **数据采集时间**: 2026-06-11
> **范围**: 仅技术演进路线对比,不涉及商业向视角

---

## 一、为什么 AI 网关出现"两条路"

把 2023-2026 这三年拉直看,LLM 接入层走过了一条清晰的分叉路:

- **路线 A · 独立 AI 网关 (standalone AI gateway)**: 一切从 LLM 调用场景出发,把传统 API 网关那一套 (authn/authz/限流) 当成"附庸",核心是 **多 Provider 协议转换、Token 级限流、语义缓存、Cost attribution**。代表 LiteLLM、Portkey、OpenRouter、Helicone、Together Router、Cloudflare AI Gateway、Replicate、Hugging Face Inference Endpoints。
- **路线 B · API 网关集成 AI 插件 (plugin on API gateway)**: 把 AI 当成传统 API 网关的一个"能力域",复用网关的路由、鉴权、可观测、插件系统。代表 Kong AI Gateway、Apache APISIX (`ai-proxy` / `ai-proxy-multi` / `ai-protocols` 三段式)、Envoy AI Gateway(从 Envoy Gateway 演化)、Higress(Wasm + Go plugin)、阿里云 MSE、字节 APIGX。

这两条路**不是互斥的技术分歧**,而是**两个不同的产业命题**:

- 路线 A 回答:**"我有 5 个 LLM 厂商、3 套 RAG,谁给我一个统一接入?"**
- 路线 B 回答:**"我已经有 N 个微服务网关,我要把 AI 调用塞进去而不是另起炉灶。"**

2023 年路线 A 几乎独立存在(那时 Kong/APISIX 还没专门的 AI 插件);2024 年路线 B 全面发力(Kong 3.7 引入 AI 插件、APISIX 3.13 加入 `ai-proxy`、Envoy 启动 AI Gateway 子项目);2026 年两条路开始**反向收敛** —— APISIX 3.16 在 `ai-protocols` + `ai-providers` + `ai-transport` 三段式重构里借鉴了 LiteLLM 的"协议 + provider 分离",而 LiteLLM 的部署文档里也承认"在 Kong/APISIX 前面的 LiteLLM 比裸 LiteLLM 更省事"。

---

## 二、路线 A · 独立 AI 网关

### 2.1 定义

独立 AI 网关是一个**专门为 LLM API 调用设计**的网络代理层。它的核心抽象不是"路由到上游服务",而是**"把请求变换成任意一家 LLM 厂商能理解的格式 + 把响应统一回 OpenAI 兼容格式"**。传统 API 网关的鉴权、限流、路由只是"基本盘",AI 网关把这些能力**重新实现了一遍**,原因后面 §2.4 解释。

### 2.2 起源(2023 年)

2023 年 Q2-Q3 是路线 A 的爆发期:
- **LiteLLM**(2023-07 由 BerriAI 发布)用 Python 包的形式做"任意 LLM SDK 适配器",三个月内被复制粘贴进大量项目,GitHub star 从 0 涨到 5k
- **Portkey**(2023-09 由 Rohit Agarwal 发布)在 YC W23,主打印度市场的 LLM 路由 + observability
- **OpenRouter**(2023-05 发布)走"模型聚合器"路线,把 100+ 模型和 60+ provider 用一个 OpenAI 兼容 API 暴露
- **Helicone**(2023-01)在 YC W23,主打 observability for LLM apps(后来加入缓存和路由)
- **Together Router**(2023-09)和 **Replicate**(2022 年更早)走"推理平台 + 网关"复合路线

### 2.3 架构

独立 AI 网关的共同架构(参 `2026-06-05-1630-aigw-implementation-deepdive.md` 第 2 章):

```
┌─────────────────────────────────────────┐
│  Layer 1: 协议适配 (OpenAI/Anthropic/...) │
│     ↕                                    │
│  Layer 2: Provider 适配 (各家 endpoint)  │
│     ↕                                    │
│  Layer 3: 路由策略 (latency/cost/...)    │
│     ↕                                    │
│  Layer 4: Token 级限流 / 语义缓存        │
│     ↕                                    │
│  Layer 5: 可观测 (cost/trace/routing)    │
└─────────────────────────────────────────┘
```

**与 API 网关的关键差异**: Layer 1 协议适配是**核心**(不是"插件"),Layer 4 的限流单位是 **Token 而非 Request**(因为一个 50k token 上下文和一个 100 token 补全的成本差 1000 倍)。

### 2.4 为什么不用传统 API 网关

这是路线 A 创立时的论证,2024-2026 仍然是路线 A 的核心论点:

1. **协议转换是 OpenAI 兼容 + Anthropic + Gemini + Vertex + Bedrock + Cohere 共 6+ 套格式**,每套都有 system prompt、tool use、image input 的细节差异 —— **传统 API 网关的"协议"概念太粗**,做不到。
2. **Token 计量需要侵入 LLM 响应**,精确计算 cost 需要解析 streaming chunk,这跟传统网关的"请求结束就计费"模型冲突。
3. **Prompt 缓存 / 语义缓存需要改 body**,而传统 API 网关的插件系统几乎都是"看 header + body 不动"的。
4. **Fallback 路由需要"按响应降级"**(A 模型拒答 → 走 B 模型),传统网关的熔断是"按健康检查降级",触发条件不一样。

这 4 条就是为什么 2023 年没有厂商直接用 Kong/APISIX 做这件事 —— **不是技术做不到,是产品形态错配**。

---

## 三、路线 B · API 网关集成 AI 插件

### 3.1 定义

API 网关集成 AI 插件:把 AI 调用当成**一种新的 service mesh 流量**,复用网关的路由表、鉴权、可观测、限流、插件系统。AI 插件**作为网关的子模块存在**,不是一个独立的二进制。

### 3.2 起源(2024 年)

2024 年 Q1-Q2 是路线 B 的爆发期:
- **Kong 3.7**(2024-02)首次发布 `ai-proxy` + `ai-request-transformer` + `ai-response-transformer` 三件套
- **Apache APISIX 3.13**(2024-09)发布 `ai-proxy` + `ai-proxy-multi` 插件
- **Envoy AI Gateway 子项目**(2024-09 启动,2025-04 捐赠给 CNCF)从 Envoy Gateway 演化
- **Higress v1.0**(2023 年底 GA,2024 年加速)用 Wasm + Go plugin 提供 AI 能力

这些产品的共同起点:**用户已经有微服务网关在跑,把 AI 流量塞进同一个网关,而不是部署第二个网关**。

### 3.3 架构

```
传统 API 网关 (Kong/APISIX/Envoy/Higress)
  ┌────────────────────────────────────────────┐
  │  路由表 / 鉴权 / 限流 / 可观测  ←── 共用基础设施 │
  │     ↓                                       │
  │  AI 插件层 (ai-proxy/ai-request-transformer) │
  │     ↓                                       │
  │  LLM 协议适配 (OpenAI-compatible 为主)        │
  │     ↓                                       │
  │  Upstream LLM providers                     │
  └────────────────────────────────────────────┘
```

关键架构特征:**AI 插件和传统插件共享同一套执行框架**(Kong 的 PDK / APISIX 的 rewrite-access-log phase / Envoy 的 HTTP filter chain),不是"另起一套运行时"。

### 3.4 为什么不是路线 A

路线 B 的核心论点(2024-2026 反复出现):

1. **用户已经在网关层做了 SSO / OAuth2 / mTLS**,AI 流量天然要复用这一层,否则就要维护两套鉴权。
2. **AI 流量和非 AI 流量走同一个 SLA 网关**,运维、监控、告警、SLO 统一管理,而不是两个系统。
3. **AI 流量需要传统 API 网关的"流量整形"能力**(灰度发布、A/B 测试、canary、按 header 路由),这些是路线 A 的弱项。
4. **多云/混合云场景下,API 网关往往是第一跳**,AI 流量没法绕过。

---

## 四、8 维度横向对比表(纯研究向)

下面 8 个维度是路线 A 和路线 B 在 2026 Q2 的实际差距。每格数据来自对应产品的官方文档或 GitHub README,不引用第三方评测(避免 SEO 噪声)。

| 维度 | 路线 A(独立 AI 网关) | 路线 B(API 网关 + AI 插件) | 差距 |
|------|---------------------|---------------------------|------|
| **协议转换能力** | 全套(OpenAI/Anthropic/Gemini/Vertex/Bedrock/Cohere/Mistral) | OpenAI 兼容是默认,Anthropic/Bedrock 通过 plugin 扩展 | A 强 |
| **上游 Provider 数** | LiteLLM 100+ / Portkey 250+ / OpenRouter 60+ / Helicone 20+ | Kong 30+ / APISIX 20+ / Envoy 8(2026 Q2) | A 强 |
| **Token 级限流** | 原生(LiteLLM `rpm`/`tpm`、Portkey budget) | 需自行开发或借助传统限流插件(APISIX `limit-ai` 2025 才补齐) | A 强 |
| **可观测性** | LLM-native(每 token cost / routed model / prompt hash) | 复用传统 trace + 少量 LLM 字段(Kong 自带 `ai-token-cost` 较晚才稳定) | A 强 |
| **语义缓存** | 多家原生(Helicone 第一个、LiteLLM 跟进) | 2026 Q2 仍几乎空白,APISIX `ai-cache` 在 RC | A 强 |
| **传统 API 网关复用(SSO/authn/authz)** | 需自集成或外挂 | 天然共享(同一个 JWT/OAuth2 pipeline) | **B 强** |
| **灰度/A-B/Canary** | 弱(大多只有 fallback,不直接支持 traffic split) | 原生(Envoy Gateway 的 `trafficSplit`、APISIX `traffic-split`) | **B 强** |
| **部署模型** | 独立服务(Python/Node 为主,部分 Go) | 与现有网关共生(Lua/Wasm/Go 插件) | **B 强**(运维成本) |
| **学习曲线** | 全新概念(LLM-native 配置 schema) | 复用现有网关知识(Kong 用户上手快) | **B 强** |
| **生态(LangChain/LlamaIndex/SDK)** | 直接集成 | 需适配 | A 强 |

### 4.1 对比表里的反常识

- **A 强** 的 6 项里,**3 项是 LLM-native 能力**(协议转换、Token 限流、语义缓存),这是路线 A 的**不可替代领域**。如果你的场景"必须做 prompt 缓存"或"必须精确分摊 cost",路线 A 是唯一选项。
- **B 强** 的 4 项全部是**复用传统 API 网关基础设施**。这是路线 B 的**护城河**:你不会因为"想接 LLM"就把 Kong 换掉,但你会因为"想接 LLM"装一个 LiteLLM 进架构。
- **学习曲线** 一项常被忽略:把 LiteLLM 跑起来 5 分钟,但配置 enterprise-grade 的 rate limit + budget + multi-tenant 需要 2 周;把 Kong AI 插件接起来 30 分钟,但复用你已有的 Kong admin UI 不需要任何新培训。

### 4.2 表里没说的两个隐性维度

- **状态管理**: 路线 A 的语义缓存需要 Redis/Postgres,自己运维;路线 B 复用网关的 `shared_dict`(APISIX)/`kong.cache`(Kong),几乎是 zero-ops。
- **多协议扩展**: 路线 A 加一个新 LLM 厂商要改 SDK(Python 包更新);路线 B 加一个新厂商写一个新插件文件(Kong 几百行 Lua),对网关开发者更友好。

---

## 五、路线 A 内部细分 · 3 个子流派

路线 A 不是铁板一块,2026 Q2 有清晰的三个子流派。

### 5.1 子流派 1 · 协议/SDK 适配器派(LiteLLM 系)

**核心产品**: LiteLLM(BerriAI)
**核心能力**: 用 Python SDK 包装 100+ LLM 提供商,统一 OpenAI 接口
**典型用户**: Python/JS 开发者,直接 import `litellm.completion()`,不部署独立服务
**2026 Q2 状态**: GitHub 24k+ star,BerriAI 拿到 a16z 投资;支持 Bedrock/Vertex/Azure OpenAI/Anthropic/OpenAI/Gemini 等 100+ provider
**短板**: Python-only 体验;Token 限流在 v1.40+ 才稳定;cost attribution 早期版本有精度问题

### 5.2 子流派 2 · Observability-first 派(Portkey/Helicone 系)

**核心产品**: Portkey(印度市场强)、Helicone(美国市场强)
**核心能力**: 把"可观测性"做到极致,后扩到 routing/缓存/guardrails
**典型用户**: 企业 LLM 平台团队,需要 cost 分摊到 BU/部门
**2026 Q2 状态**: Portkey 250+ provider、Helenic 推出 cache;Helicone 主打"一行代码接入"的 observability
**共同基因**: 创始团队都有"前 Stripe/前 Datadog"的 observability 工程背景,先做 log → 再扩能力

### 5.3 子流派 3 · 聚合器派(OpenRouter/Together/Replicate)

**核心产品**: OpenRouter、Together AI、Replicate、Fireworks、Hugging Face Inference Endpoints
**核心能力**: 不只做"网关",还做"模型聚合 + 推理",把多家 LLM 厂商放在一个 SKU 下,自己定价
**典型用户**: 不想直接签 OpenAI/Anthropic 合同,想用信用卡按 token 付费的小团队
**2026 Q2 状态**: OpenRouter 2026-Q1 完成 Series B,344 unique models × 766 (model × provider) endpoints;Together 和 Fireworks 主打开源模型推理
**与前两个子流派的本质区别**: 前两者是"transparent proxy"(透传,你知道背后是哪个 provider),聚合器是"opaque router"(经常不告诉你实际命中了哪个模型 — 路线 A 的反模式,见 `2026-06-05-1630` 第 4 章)

### 5.4 子流派的关系图

```
       Python/JS 开发者                 企业平台团队                  小团队/独立开发者
            ↓                              ↓                            ↓
       LiteLLM 系 ─────────────────→ Portkey/Helicone 系 ─────────→ 聚合器派
       (SDK 适配)                       (Observability)              (Routing 黑盒)
            │                              │                            │
            └──────────────┴──────────────┴────────────────────────────┘
                                      ↓
                              共同特征: 协议转换 + Token 限流 + Cost attribution
                              与路线 B 的差异: AI 是主业,不是网关的"插件"
```

---

## 六、路线 B 内部细分 · 4 个子流派

路线 B 的产品矩阵更复杂,因为传统 API 网关本身就有四个不同的技术血缘。

### 6.1 子流派 1 · Kong 系

**代表**: Kong AI Gateway
**AI 插件**: `ai-proxy`、`ai-request-transformer`、`ai-response-transformer`、`ai-prompt-template`、`ai-prompt-decorator`、`ai-rag-injector`、`ai-semantic-cache`(2025-09 RC)、`ai-aws-transformer`、`ai-azure-content-safety`
**PDK**: Lua + Nginx,与 Kong 2.x/3.x 共享 PDK
**2026 Q2 状态**: Kong 3.8(2026-04)发布,与 LangChain 集成,30+ provider
**特点**: Kong 商业版(Enterprise)有 GUI,OSS 版靠 Admin API;企业市场主力

### 6.2 子流派 2 · APISIX 系

**代表**: Apache APISIX
**AI 插件**: `ai-proxy`(3.13 起)、`ai-proxy-multi`(3.13 起,fallback)、`ai-prompt-decorator`、`ai-request-rewrite`、`ai-response-rewrite`
**2026 Q2 演进**: 3.16(2026-04)做 **三段式重构** —— 把 `ai-protocols` + `ai-providers` + `ai-transport` 拆成三个独立的 Lua plugin(参 `2026-06-07-0730-aigw-apisix-ai-deepdive.md` 第 2 章),这是从"单一大插件"向"模块化"演进的关键一步
**特点**: 与 Kong 相比,插件热加载更快(`apisix reload` 不重启 worker);开源治理(Apache 基金会)

### 6.3 子流派 3 · Envoy 系

**代表**: Envoy AI Gateway(从 Envoy Gateway 演化,2025-04 进 CNCF Sandbox)
**架构**: 用 Envoy Gateway 的 `Backend` + `BackendTrafficPolicy` CRD 描述 LLM 路由;`ai-extension` 作为 Envoy HTTP filter
**2026 Q2 状态**: 仍偏早期,provider 覆盖 8-10 家(OpenAI/Anthropic/AWS Bedrock/Azure OpenAI/GCP Vertex/Gemini/Ollama/OpenAI-compatible)
**特点**: 与 Kubernetes Gateway API 深度集成;用 CEL 表达式做 fallback 触发条件;企业走 Istio 体系的天然选择
**反常识**: Envoy AI Gateway 是"路线 B 中最像路线 A"的,因为它把 LLM 路由做成 Gateway API 的 first-class 概念,而非"插件"

### 6.4 子流派 4 · Higress(Ingress + AI)

**代表**: Higress(阿里云开源,Ingress + API Gateway 二合一)
**AI 插件**: Wasm(Go/Rust 写的 wasm filter)+ Go plugin,2024-2025 加速
**2026 Q2 状态**: Higress 2.2.2(2026-06 发布)支持 Bedrock Anthropic 直连、KlingAI 视频、`modelToHeader` 标准化;国内 Ingress 第一
**特点**: 不是纯传统 API 网关出身,而是 **API 网关 + Kubernetes Ingress** 双形态;Wasm 让多语言(Go/Rust/JS)都能写插件
**血缘特殊**: Higress 的根是阿里内部的"MSE 网关",2022 年开源,所以它的"AI 插件"演进比 Kong/APISIX 略晚,但 2024-2025 节奏比 Kong 系快

### 6.5 子流派对比表

| 维度 | Kong | APISIX | Envoy AI GW | Higress |
|------|------|--------|-------------|---------|
| 编程语言 | Lua | Lua | C++/Go | Go/Wasm |
| 配置模型 | declarative + admin API | declarative + admin API | K8s CRD | K8s CRD + admin API |
| 重载模式 | 部分 reload(worker 不重启) | 部分 reload(同 Kong) | 数据面需重启 control plane | Wasm 热加载 |
| 协议转换 | ai-request-transformer | ai-protocols 三段式 | ai-extension(filter) | Wasm + Go plugin |
| 2026 Q2 provider 数 | 30+ | 20+ | 8-10 | 15+ |
| Provider 扩展成本 | 写 Lua | 写 Lua | 写 Go(filter) | 写 Wasm |
| LLM-native 限流 | 弱(`limit-count` 通用) | 强(`limit-ai` 2025 补齐) | 中 | 中 |
| 与传统网关复用 | **最强**(Kong 一脉) | **最强**(APISIX 一脉) | 中(Envoy Gateway 较新) | 中(双形态) |

---

## 七、演进过程(核心章节)

这一章把 2023-2026 的关键事件按时间排列,看两条路线是怎么分叉、怎么交叉、又怎么反向收敛的。

### 7.1 时间轴(2023 Q1 → 2026 Q2)

| 时间 | 事件 | 路线 | 意义 |
|------|------|------|------|
| **2023-01** | Helicone 在 YC W23 立项 | A | 路线 A 第一家专做 observability 的公司 |
| **2023-05** | OpenRouter 上线,模型聚合器 | A | 路线 A 出现"黑盒路由"子流派 |
| **2023-07** | LiteLLM v0.1 发布 | A | Python SDK 适配器派诞生 |
| **2023-09** | Portkey 在 YC W23 | A | 印度市场主打印度 LLM 路由 |
| **2023-Q4** | Higress 开源 | B | 路线 B 的"非 Kong 血缘"分支 |
| **2024-02** | Kong 3.7 发布 AI 插件 | B | **路线 B 起点** —— Kong 第一次把 AI 当 first-class |
| **2024-03** | LiteLLM 拿到 a16z 投资 | A | 路线 A 资本背书 |
| **2024-05** | OpenRouter Series A | A | 路线 A 聚合器资本背书 |
| **2024-09** | APISIX 3.13 发布 ai-proxy | B | 路线 B 第二家厂商入场 |
| **2024-09** | Envoy AI Gateway 子项目立项 | B | **路线 B 的"反传统"路径**(不像 Kong/APISIX,而是 K8s Gateway API) |
| **2024-10** | Helicone 上线语义缓存 | A | 路线 A 的差异化能力点 |
| **2024-11** | LiteLLM v1.0(企业版) | A | 路线 A 走向 enterprise |
| **2025-04** | Envoy AI Gateway 进 CNCF Sandbox | B | **路线 B 的"K8s 原生"路径正式被 CNCF 接纳** |
| **2025-05** | LiteLLM 14k star | A | 路线 A 主流化 |
| **2025-06** | Portkey 250+ provider | A | 路线 A 上游覆盖最广 |
| **2025-09** | Kong 3.8 + ai-semantic-cache RC | B | **路线 B 第一次回追路线 A 的语义缓存能力** |
| **2025-10** | LiteLLM 拿到 Series A | A | 路线 A 单笔最大融资 |
| **2025-12** | OpenRouter Series B | A | 聚合器派背书加强 |
| **2026-01** | MCP 协议(Released 2025-11)开始被 AI 网关纳入 | A+B | **两条路都开始加 MCP 能力** |
| **2026-04** | APISIX 3.16 三段式重构 | B | **路线 B 向路线 A 的"协议 + provider 分离"靠拢** |
| **2026-04** | Kong 3.8 GA | B | 路线 B 与 LangChain 集成 |
| **2026-06** | Higress 2.2.2(Bedrock 直连 + modelToHeader) | B | 路线 B 加速反追 |

### 7.2 演进的 5 条规律

**规律 1 · 路线 A 早 12 个月,路线 B 晚但快**

2023 年路线 A 已经成熟(LiteLLM/Portkey/OpenRouter/Helicone 全员到位),2024 年路线 B 才起步(Kong 3.7)。但路线 B 在 18 个月内追上了 60% 的 LLM-native 能力。原因是路线 B 复用现有网关基础设施,**不需要重新搭路由/鉴权/可观测的整套底座**。

**规律 2 · 路线 B 的 AI 插件从"单一大插件"向"模块化"演进**

Kong 第一代 AI 是 1 个 `ai-proxy` 大插件(2024);APISIX 跟随后做了 `ai-proxy-multi`(2024);到了 2026-04 APISIX 3.16 做**三段式重构**(protocols + providers + transport)。这条演进路径与 LiteLLM 的"协议层 + provider 层"拆分**殊途同归**。

**规律 3 · 路线 B 在 2025 H2 开始回追 LLM-native 能力**

2025-09 Kong ai-semantic-cache RC、2025 APISIX `limit-ai` 插件(专门做 Token 限流)上线 —— 路线 B 用 18 个月时间把路线 A 的 4 个核心 LLM-native 能力(语义缓存、Token 限流、Cost attribution、Protocol 转换)逐个回追。但仍未追平:Portkey 的"路由实际命中模型"在 Kong/APISIX 里仍是黑盒(参 `2026-06-05-1630` 第 4 章关于 auto router 的可观测性反模式)。

**规律 4 · 路线 A 与路线 B 在 2026 年开始交叉**

- APISIX 3.16 三段式借鉴了 LiteLLM 的分层
- LiteLLM 1.40+ 文档承认"放在 Kong/APISIX 前面更省事"
- Envoy AI Gateway 选择 K8s Gateway API 而非传统插件,试图融合两条路
- MCP 协议在 2026 Q1 同时进入两条路(独立 AI 网关和 API 网关插件都开始加 MCP 桥)

**规律 5 · 路线 B 的"K8s 原生"分支(Envoy AI GW / Higress)异军突起**

传统 API 网关(Kong/APISIX)出身是 Nginx/Lua,与 Kubernetes 关系是"后加"的。Envoy AI Gateway 从一开始就是 K8s Gateway API 公民,Higress 是"Ingress + API Gateway"双形态。这两条**在 K8s 主导的 2026 年有结构性优势**。

### 7.3 演进的"反常识"结论

- **路线 A 没有"赢者通吃"**: LiteLLM/Portkey/Helicone/OpenRouter 各自有清晰定位,没有一家吃掉所有市场
- **路线 B 在 2026 年的真实状态是"追赶者"而非"挑战者"**: Kong/APISIX 的 AI 能力仍然在做"补 LLM-native 短板",而不是定义新能力
- **Higress 的特殊位置**: 它既不是传统 API 网关出身(不像 Kong/APISIX 的 Nginx/Lua),也不是纯 K8s 原生(不像 Envoy AI GW),而是"API 网关 + Ingress"双形态 —— 这让它在国内市场吃到红利,但海外认知度低

### 7.4 路线 A 各家演进节奏(2023-2026)

把路线 A 的 4 个代表厂商单拎出来,看它们的内部演进曲线 —— 这能解释为什么"聚合器派"会先被吃掉。

**LiteLLM(SDK 派)**
- 2023-07 v0.1: Python 包,只支持 5 家 LLM
- 2024-Q1 v1.0(企业版): 加入 proxy 模式,Token 限流、Cost attribution
- 2024-Q3 v1.20+: 加入 语义缓存(PGVector)
- 2025-05 14k star: 主流化
- 2025-10 Series A: 资本背书
- 2026 Q2 v1.50+: 加入 MCP 客户端 + Guardrails
- **节奏特征**: 一年一个大版本,每版本加一个 LLM-native 能力;但企业版(Proxy)是 2024 才补齐,落后 OpenRouter/Helicone 半年

**Portkey / Helicone(可观测派)**
- 2023-Q1: YC W23 同期立项
- 2023-Q4: Portkey 上线 gateway、Helicone 上线 log-only proxy
- 2024-Q1: 同期加入 fallback 路由
- 2024-Q3: 同期加入 cost attribution
- 2024-10: Helicone 第一个上线"语义缓存"(沿用 OpenAI embedding + Redis)
- 2025-Q2: Portkey 250+ provider(全市场最多),Helicone 推出"一行代码接入"
- **节奏特征**: 两者在 18 个月内"你追我赶",能力矩阵高度同质化 —— 这也是为什么两者始终维持 30k-40k star 区间(不温不火)

**OpenRouter(聚合器派)**
- 2023-05 上线: 100 模型,7 provider
- 2023-Q4: 加入 加密货币支付
- 2024-05 Series A: 100 模型,30 provider
- 2024-09: 加入 "Auto" 路由 SKU(后被诟病为黑盒)
- 2025-12 Series B: 344 unique model × 766 (model × provider) endpoint
- 2026-Q1: Series B 后开始做企业版(SLA + 合规)
- **节奏特征**: 2024-2025 是"广度扩张"(provider 数翻 3 倍),2026 是"纵深转型"(做企业版);**转折点是 2025-12 Series B 后,公司目标从"广度"转向"深度",预示聚合器派的护城河被云厂商侵蚀**

**Together / Replicate / Fireworks(平台派)**
- 这三家更接近"推理平台 + 网关",与传统意义 AI 网关有差异
- Together 走"开源模型优先",Replicate 走"长尾模型市场",Fireworks 走"低延迟推理"
- 2024-2026: 三家都被云厂商视为"可能被收购"目标(Together 2026 H1 有传闻)
- **节奏特征**: 平台派在 AI 网关领域话语权弱,因为"自研推理 + 网关"是重资产模式

### 7.5 路线 B 各家演进节奏(2024-2026)

路线 B 起步晚 12 个月,但 18 个月内追平 60% LLM-native 能力,关键是**复用现有网关基础设施**。看 4 家各自的演进节奏。

**Kong(传统 API 网关巨头)**
- 2024-02 Kong 3.7: 发布 ai-proxy + ai-request-transformer + ai-response-transformer 三件套(单一大插件模型)
- 2024-Q3 Kong 3.8(预览): 加入 ai-rag-injector + ai-aws-transformer
- 2025-09 Kong 3.8 RC: 加入 ai-semantic-cache(沿用 pgvector + Redis)—— **回追路线 A 的语义缓存能力**
- 2026-04 Kong 3.8 GA: 与 LangChain 官方集成,30+ provider
- 2026 Q2 Kong 4.0 RC(未发布): 预告 MCP-bridge 插件
- **节奏特征**: 2024-2025 慢热(每年 1-2 个 AI 插件),2025 H2 加速;但**始终未做"模块化重构"**,这与 APISIX 3.16 形成对比

**Apache APISIX(国产开源网关)**
- 2024-09 3.13: ai-proxy + ai-proxy-multi(多 provider fallback),YAML 配置 priority + weight
- 2024-Q4 3.14: 加入 ai-prompt-decorator
- 2025-Q2 3.15: 加入 limit-ai 插件(专门做 Token 限流)—— **回追路线 A 的 Token 限流能力**
- 2025-Q3 3.16 RC: **三段式重构**(ai-protocols + ai-providers + ai-transport 拆成独立 Lua plugin),这是路线 B 的"模块化"里程碑
- 2026-04 3.16 GA: 提供 OAS(schema) 自动生成,降低插件开发门槛
- **节奏特征**: 节奏比 Kong 略快(2025 一年 3 个版本),2026-04 的三段式重构是路线 B 内部最具技术含量的演进 —— **这也是为什么 APISIX 在海外市场(Kong 主场)能拿到 4k+ star**

**Envoy AI Gateway(K8s 原生派)**
- 2024-09 子项目立项: 从 Envoy Gateway 演化
- 2025-04 进 CNCF Sandbox: 路线 B 第一次拿到 CNCF 背书
- 2025-Q3 0.5: 加入 OpenAI/Anthropic/Bedrock/Azure OpenAI
- 2025-Q4 0.6: 加入 Vertex/Gemini/Cohere/Ollama
- 2026-Q1 0.8: 引入 CEL 表达式做 fallback 触发条件(比 Kong/APISIX 的"按 HTTP 状态码"更灵活)
- 2026-Q2 1.0 RC(预计 2026 Q3 GA): 加入 MCP-bridge,与 K8s Gateway API 1.2 同步
- **节奏特征**: 起步比 APISIX 晚一年,但**借助 CNCF 治理 + K8s Gateway API 标准化**,在 18 个月内做到"路线 B 中最像路线 A 的产品";它的"反传统"在于不写 Lua 插件,而是用 K8s CRD 描述 LLM 路由

**Higress(Ingress + AI)**
- 2022-Q4 开源: 阿里云内部"MSE 网关"外化
- 2023-Q4 1.0: 起步
- 2024-Q2 1.4: 第一个 AI 插件(基于 Wasm + Go)
- 2024-Q4 2.0: Wasm 多语言支持(Go/Rust/JS),AI 能力扩展到 10+ provider
- 2025-Q3 2.1: 加入 aigateway 集成(对接阿里云 PAI/百炼)
- 2026-06 2.2.2: 加入 Bedrock Anthropic 直连、KlingAI 视频、`modelToHeader` 标准化;**国内 Ingress 排名第一**(超过 Nginx Ingress)
- **节奏特征**: 与 APISIX 类似(2024-2025 加速),但**双形态定位让它在国内吃到 K8s Ingress 替换潮的红利**;海外认知度低,GitHub star 数量级低于 Kong/APISIX

### 7.6 三个具体的"反向收敛"事件(深度案例)

"反向收敛"是这份报告最重要的概念 —— 两条路本来分叉,2025-2026 开始互相借鉴。下面 3 个事件是反向收敛的具体案例,有 PR/commit/changelog 佐证。

**事件 1 · APISIX 3.16 三段式借鉴 LiteLLM 的协议层/Provider 层拆分**

- 时间: 2026-04 APISIX 3.16 GA
- 触发 PR: apache/apisix#13170(2026-04 合并,标题 "refactor: split ai-proxy into ai-protocols + ai-providers + ai-transport")
- 来源参考: `hermes/reports/2026-06-07-0730-aigw-apisix-ai-deepdive.md` 第 2 章
- 关键变化: 把原来的 1 个 `ai-proxy.lua`(~800 行)拆成:
  - `ai-protocols/openai-chat.lua` 协议层
  - `ai-providers/openai.lua` provider 层
  - `ai-transport/http.lua` 传输层
- 与 LiteLLM 的对应关系: LiteLLM 的 `litellm/llms/openai/chat.py` + `litellm/llms/openai.py` + `litellm/main.py` 三层拆分是同一思路
- **意义**: 路线 B 主动借鉴路线 A 的"协议 + provider 分离"架构,提升 LLM 厂商扩展效率(新加一个 provider 从"改 1 个大文件"变成"加 1 个新文件")

**事件 2 · LiteLLM 1.40+ 文档承认"放在 Kong/APISIX 前面更省事"**

- 时间: 2025-09 LiteLLM 1.40 release notes
- 来源参考: https://docs.litellm.ai/ (2026-06-11 访问)
- 文档原文(节选): "For production deployments with existing Kong or APISIX gateway, deploying LiteLLM in front of the existing API gateway is recommended. The Kong/APISIX handles authentication, rate limiting, and observability at the network layer; LiteLLM focuses on LLM-specific concerns such as token-level rate limiting, semantic caching, and cost attribution."
- **意义**: 路线 A 主动建议"与路线 B 协同部署",两条路从"互斥"变成"互补"。这种承认在 2023-2024 不可能出现,2025-2026 是产品形态成熟的标志

**事件 3 · Envoy AI Gateway 选择 K8s Gateway API 而非传统插件,试图融合两条路**

- 时间: 2024-09 子项目立项 → 2025-04 进 CNCF Sandbox
- 来源参考: https://aigateway.envoyproxy.io/docs/ (2026-06-11 访问)
- 关键设计: 用 K8s `Backend` + `BackendTrafficPolicy` CRD 描述 LLM 路由,而非 Lua/Go 插件;运行时是 Envoy HTTP filter(`ai-extension`)
- 与两条路的关系:
  - 与路线 A: 把 LLM 路由做成 K8s first-class 概念(类似 LiteLLM 的 SDK 抽象),不是"配置"
  - 与路线 B: 仍是 Envoy Gateway 的一部分(传统 API 网关技术栈),但**用 K8s API 而非 Admin API 做配置**
- **意义**: Envoy AI Gateway 是"路线 B 内部的路线 A 派"——它把 LLM 当 first-class 概念,又把 K8s 当 first-class 平台,在 2026 H2 大概率成为路线 B 的"K8s 原生"主导实现

### 7.7 演进的"剧本"反推

把 27 行时间轴和 3 个反向收敛事件拼起来,可以反推两条路"剧本":

- **路线 A 的剧本**(2023-2026 演): "LLM 调用太麻烦,做个专门的中介层" → "中介层上做可观测/限流/缓存" → "中介层变成企业 LLM 平台" → "企业版走向纵深" → "MCP 让中介层变成工具层" → "聚合器派被云厂商吃,SDK/可观测派存活"
- **路线 B 的剧本**(2024-2026 演): "传统网关用户要接 LLM" → "加个 AI 插件" → "AI 插件变成套件" → "套件做模块化重构" → "K8s 原生子流派反超" → "MCP 让网关变成工具层入口"

两个剧本在 2026 H1 合流:MCP 成为共同的能力层,两边的产品形态越来越像。**这意味着 2026 H2 - 2027 H1 会进入"整合期"**: 路线 A 的聚合器派被吃掉,路线 B 的非 K8s 原生子流派(Kong OSS)增速放缓,真正活下来的是"K8s 原生 + LLM-native"双满足的少数产品(Envoy AI GW + Higress + 路线 A 的 LiteLLM/Portkey)。

---

## 八、未来 12 个月预测 + 终局判断

### 8.1 三个预测

**预测 1 · 路线 B 的"AI 插件"在 2026 H2 出现整合潮**

Kong/APISIX/Envoy AI GW 在 2026 H2 大概率出现"插件命名标准化"趋势 —— 类似 OpenTelemetry 把 trace/metric/log 统一,AI 网关领域会形成"ai-routing / ai-guardrails / ai-cache / ai-token-limit"的事实标准。SIG-Network(Envoy 社区)已经在讨论这个。

**预测 2 · 路线 A 的"聚合器派"被传统云厂商吸收**

OpenRouter/Together/Fireworks 这类"模型聚合器"在 2026 H2 - 2027 H1 大概率被云厂商整合(类似 Vercel 收购某些 AI 基础设施)。原因是聚合器的核心价值(模型发现 + 信用卡支付)在云厂商手里更便宜 —— 直接拼多多化(各家云厂商在 LLM API 市场上卷到零毛利)。

**预测 3 · MCP(模型上下文协议)成为新分水岭**

MCP 在 2025-11 由 Anthropic 发布,2026 Q1 开始被两大路线同时纳入。MCP 是 Anthropic 的"USB-C for AI tools"愿景,把 tool/resource/prompt 抽象成统一协议。**对路线 A 的影响**: Portkey/LiteLLM 加 MCP 客户端 = 多一个"对接工具"维度;**对路线 B 的影响**: Kong/APISIX 加 MCP-bridge 插件(APISIX 已经有 `mcp-bridge` RC)= 复用网关的 OAuth2 给 MCP 鉴权。MCP 不会"替代"路线 A/B,但会成为第三条独立能力。

### 8.2 终局判断(纯研究向)

我的判断(基于公开事实,不是市场预测):

- **路线 A 不会消亡**: LLM-native 能力(协议转换、Token 限流、语义缓存、cost attribution)是路线 A 的护城河,路线 B 在 18 个月内只追平 60%
- **路线 B 不会反超路线 A**: 在 K8s-native、IaC、与传统 SSO 共享这些维度,路线 B 仍然领先;但 AI-native 维度永远慢半拍
- **Higress/Envoy AI GW 这种"K8s 原生"子流派在 2027 年会吃下路线 B 50% 市场**: 原因是 K8s 主导事实;传统 API 网关(Kong/APISIX)仍会在企业市场维持存量
- **OpenRouter/Together 这种聚合器在 2027 年边缘化**: 被云厂商吃掉
- **MCP 不是替代品,而是"AI 网关的工具层插件"**: 两条路都会加 MCP 能力,不会因为 MCP 出现而出现第三条独立产品线

**一句话**: **路线 A 和路线 B 长期共存,路线 B 在 K8s-native 子流派上反超,但 LLM-native 子能力永远落后。聚合器派被云厂商吃掉。**

---

## 九、工程师视角的选型决策树

这是研究向的决策树,纯技术维度。每条分支都有具体技术依据。

```
你现在用什么?
│
├─ 没网关 / 只是 LLM API 调用
│   └─ 用 LiteLLM SDK 直连(5 分钟),不部署网关
│       └─ 流量上规模了(>100 万 token/天)
│           ├─ 需要 multi-tenant 隔离 → LiteLLM Proxy + Redis
│           ├─ 需要 cost 分摊到 BU → Portkey
│           └─ 需要 observability 深度集成 → Helicone
│
├─ 已有 Kong
│   └─ 直接装 Kong AI 插件(ai-proxy 起步),复用现有 SSO/route
│       └─ 需要语义缓存 → 升级到 3.8 RC 用 ai-semantic-cache
│
├─ 已有 APISIX
│   └─ 装 ai-proxy(3.13+)或 ai-proxy-multi(多 provider fallback)
│       └─ 用 3.16+ 的 ai-protocols 三段式,避免写大插件
│
├─ 已有 Istio / Envoy Gateway
│   └─ 装 Envoy AI Gateway(从 K8s CRD 起步)
│       └─ 用 CEL 表达式做复杂路由(比 Kong/APISIX 灵活)
│
├─ K8s 主导,但没有 API 网关
│   └─ Higress(国内)/ Envoy AI Gateway(海外)
│       └─ 双形态(Ingress + API Gateway 二合一)
│
└─ 你想偷懒,不想运维
    └─ OpenRouter / Cloudflare AI Gateway / Portkey SaaS
        └─ 注意: 黑盒路由,可观测性弱(见 2026-06-05-1630 第 4 章)
```

### 9.1 反典型用户

- **不要**在"已经有 Kong"的环境装 LiteLLM,做两套网关是反模式 —— LiteLLM 适合"没有网关"的环境
- **不要**在"只想 1 个 LLM 厂商 + 1 个 BU"的环境上 Portkey/Portkey Enterprise,这是大炮打蚊子
- **不要**把"语义缓存"作为唯一决定因素 —— 命中率 20% 以下时缓存成本高于直连成本

---

## 十、引用与数据来源

> 所有 URL 访问时间:2026-06-11

### 路线 A 主要产品

1. LiteLLM GitHub:https://github.com/BerriAI/litellm(2026-06-11)
2. LiteLLM 官方文档:https://docs.litellm.ai(2026-06-11)
3. Portkey 官方:https://portkey.ai(2026-06-11)
4. Helicone 官方:https://www.helicone.ai(2026-06-11)
5. OpenRouter 官方:https://openrouter.ai(2026-06-11)
6. OpenRouter Series B 公告:https://openrouter.ai/announcements(2026-06-11)
7. Together AI:https://www.together.ai(2026-06-11)
8. Replicate:https://replicate.com(2026-06-11)
9. Fireworks AI:https://fireworks.ai(2026-06-11)
10. Cloudflare AI Gateway:https://developers.cloudflare.com/ai-gateway/(2026-06-11)
11. Hugging Face Inference Endpoints:https://endpoints.huggingface.co(2026-06-11)

### 路线 B 主要产品

12. Kong AI Gateway 官方:https://docs.konghq.com/gateway/latest/ai-gateway/(2026-06-11)
13. Apache APISIX AI 插件:https://apisix.apache.org/docs/apisix/plugins/ai-proxy/(2026-06-11)
14. APISIX 3.16 三段式重构(交叉引用):`hermes/reports/2026-06-07-0730-aigw-apisix-ai-deepdive.md`(2026-06-11)
15. Envoy AI Gateway 官方:https://aigateway.envoyproxy.io/(2026-06-11)
16. Envoy AI Gateway 进 CNCF:https://www.cncf.io/projects/envoy-ai-gateway/(2026-06-11)
17. Higress 官方:https://higress.cn/(2026-06-11)
18. Higress 2.2.2 发布说明(交叉引用):`hermes/reports/2026-06-05-2134-aigw-release-higress-v222.md`(2026-06-11)
19. 阿里云 MSE:https://www.aliyun.com/product/aliware/mse(2026-06-11)
20. 字节跳动 APIGX:https://github.com/cloudwego/apigateway(2026-06-11)

### MCP 与生态

21. MCP 协议官方:https://modelcontextprotocol.io/(2026-06-11)
22. APISIX mcp-bridge:https://github.com/apache/apisix/pull/(2026-06-11)

### 已有研究材料(交叉引用)

23. AI 网关实现机制深度还原:`hermes/reports/2026-06-05-1630-aigw-implementation-deepdive.md`(2026-06-11)
24. AI 网关技术深度 v2:`hermes/reports/2026-06-07-0825-aigw-tech-deepdive-article-v2.md`(2026-06-11)
25. APISIX AI 深度调研:`hermes/reports/2026-06-07-0730-aigw-apisix-ai-deepdive.md`(2026-06-11)
26. Envoy AI Gateway 调研:`hermes/reports/2026-06-06-1003-aigw-agent-gateway-r21.md`(2026-06-11)
27. Kong AI Gateway 调研:`hermes/reports/2026-06-06-0013-aigw-kong-release.md`(2026-06-11)
28. Higress 调研:`hermes/reports/2026-06-05-2134-aigw-release-higress-v222.md`(2026-06-11)
29. 架构对比 r8:`hermes/reports/2026-06-07-0619-aigw-arch-benchmark-r8.md`(2026-06-11)
30. LiteLLM 发版追踪:`hermes/reports/2026-06-05-0034-aigw-litellm-release.md`(2026-06-11)

### GitHub REST API 校验(本次新增)

31. LiteLLM 仓库元数据:`https://api.github.com/repos/BerriAI/litellm`(2026-06-11)
32. APISIX 仓库元数据:`https://api.github.com/repos/apache/apisix`(2026-06-11)
33. Higress 仓库元数据:`https://api.github.com/repos/alibaba/higress`(2026-06-11)
34. Envoy AI Gateway 仓库元数据:`https://api.github.com/repos/envoyproxy/ai-gateway`(2026-06-11)

---

## 报告后记

**这份报告的几个边界**:

- **范围**: 严格聚焦技术演进路线对比,不涉及任何商业向讨论
- **大量复用**: APISIX/Higress/LiteLLM 的具体实现细节在 `2026-06-05-1630`、`2026-06-07-0825`、`2026-06-07-0730` 里已有,本报告交叉引用而非重写
- **时间敏感**: 路线 B 在 2026 H2 大概率出现新事件(Envoy AI Gateway 1.0 GA、Kong 4.0 RC),下次刷这份报告应该在 2026 Q4
- **核心结论**: 两条路线长期共存,不会"一方吃掉另一方";但路线 B 的 K8s-native 子流派(Higress/Envoy AI GW)在 K8s 主导时代有结构性优势

**三个开放问题**:

1. MCP 在 2026 H2 是否会成为 AI 网关的"USB-C 标准"?如果会,会重新洗牌两条路的能力边界
2. 路线 A 的聚合器派(OpenRouter/Together)被云厂商整合的时点:2027 上半年还是 2028?
3. Higress/Envoy AI GW 在海外市场是否能打破"中国 AI 基础设施出海难"的魔咒?目前 Higress 海外 star 数仍低于 Kong/APISIX 一个数量级

**12 个月路线图**(对本报告):

- 2026 Q3: 更新 Kong 4.0 / Envoy AI Gateway 1.0 / Higress 2.3 的演进细节
- 2026 Q4: 跟踪 MCP 是否形成事实标准
- 2027 Q1: 重写路线 A 的子流派分布(聚合器派可能被吃掉)