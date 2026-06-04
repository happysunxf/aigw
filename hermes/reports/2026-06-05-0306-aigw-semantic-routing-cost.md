# AI 网关持续深挖 · 第 6 次 — 语义路由与成本优化

- 轮值时间(本地): 2026-06-05 03:06 CST
- 主题: 语义路由/成本优化(hour % 7 = 3)
- 轮换产品: Envoy AI Gateway v0.6.0(主) / OpenRouter / Portkey / Helicone(横向对比)
- 抓取窗口: 2026-05-01 ~ 2026-06-05 之间的发版与产品页
- 上一轮(2026-06-05 02:26): Agent Gateway 编排/trace 专题,本次延展到「路由决策 + 单价仲裁 + 缓存」链路

---

## 1. 一句话结论

「LLM gateway 正在从转发器变成**路由器 + 价格仲裁器**」,近 30 天最显眼的信号是
Envoy AI Gateway v0.6.0 把 *Anthropic / OpenAI / Gemini* 三家的 `reasoning_effort`、prefix
缓存和 `/v1/messages` 翻译统一到一把「单旋钮」;同时 OpenRouter 把
*Price / Throughput / Latency* 三种排序以及 *ZDR(Zero Data Retention)* 兜底直接暴露在
API 参数里,意味着「成本优化」已经不是网关的**附加项**,而是它对外承诺的核心契约。

---

## 2. 抓到的硬数据(均带日期与来源 URL)

### 2.1 Envoy AI Gateway v0.6.0(发版日期: 2026-05-05)

来源: GitHub Releases `envoyproxy/ai-gateway` tag `v0.6.0`

* **首个「生产可用 API 表面」**:核心 CRD `AIGatewayRoute / AIServiceBackend /
  BackendSecurityPolicy / GatewayConfig / MCPRoute` 全部进入 `v1beta1`。
* **统一 `reasoning_effort`**:同一参数 `low/medium/high/xhigh` 映射到
  Anthropic 的 thinking budget 与 Gemini 3 的 thinking 控制,**跨三家厂商一把旋钮**。
* **Prefix 缓存覆盖**:Gemini 现在支持 Anthropic 风格的 `cache_control` 前缀缓存;
  Anthropic、AWS Bedrock Claude 与 GCP Vertex AI 走同一套语义。
* **`/v1/messages` 跨协议翻译**:任何 OpenAI 兼容后端(OpenAI、Azure、第三方兼容服务)
  都能通过网关的 Anthropic Messages 端点暴露出来。
* **结构化输出(Schema)**:Claude 系列可在 Anthropic 与 AWS Bedrock 上接受 JSON
  schema 约束,Vertex AI Claude 暂未支持(等上游)。
* **`max_tokens` 缺省安全化**:Anthropic 请求漏传 `max_tokens` 时不再让 translator
  崩溃,直接转给上游报正常 4xx,移除了一个长期 footgun。
* **自适应 thinking(`claude-opus-4.6`)**:网关把 Adaptive thinking 端到端翻译出来,
  调用方不需要为新模型写专用代码。
* **Prompt 缓存成本节省**已在 v0.5 引入 Bedrock / Vertex Claude;v0.6 把同一思路
  扩展到 Gemini,形成「三巨头一致缓存语义」。
* **两个 breaking change**:
  1. `AIGatewayRoute.spec.filterConfig` 整个字段被删,external-processor 配置
     必须迁到 `GatewayConfig`(`aigateway.envoyproxy.io/gateway-config` 注解)。
  2. `VersionedAPISchema.version` 不再被当作 endpoint prefix,用 `prefix` 显式声明
     (例:`prefix: /v1beta/openai`、`prefix: /compatibility/v1`)。

> 结论:Envoy AI Gateway 这一波不是单点优化,而是把**跨厂商请求/响应合同**
> 收敛到「一份入参、一份出参、一份缓存键」。这正是「语义路由」能谈得起来的
> 前提——不同模型的 input/output 形状先被规整到同一棵 AST,后面的 router/cache
> 才不踩坑。

### 2.2 OpenRouter 路由策略显式化(产品页 2026-06 访问)

来源: `https://openrouter.ai/` 首页与 `openapi` 文档

* 在 `/api/v1/chat/completions` 请求体里允许 `provider.sort`(枚举):
  `Price` / `Throughput` / `Latency` / `Exacto`。
* `provider.only` 白名单 / `provider.ignore` 黑名单 / `provider.require_parameters`
  把「选模型」下沉到 API 自身。
* `provider.zdr`(boolean)兜底为「只把流量路由到承诺 Zero Data Retention 的端点」,
  这是把**安全/合规**作为路由第一约束的典型做法。
* 模型总数 **346 个**,首页宣称 *100T monthly tokens / 8M+ users / 60+ providers*,
  仍以「统一接口 + 自动挑最便宜可用」为定位。

> 结论:OpenRouter 的路线与 Envoy 互补——OpenRouter 是「用户面对的 SaaS 层
> 路由」,Envoy 是「企业自建里的数据面 + 控制面」。**两者的 sort 维度是同构的**
> (price / latency / throughput),说明这个抽象是行业事实标准,不是某家发明。

### 2.3 Portkey 的策略矩阵(2026-06 访问 docs.portkey.ai)

来源: `docs.portkey.ai` product ai-gateway 文档

* 显式列出的能力栈:**Cache (Simple & Semantic)** / **Conditional Routing** /
  **Multimodal** / **Fallbacks** / **Automatic Retries** / **Circuit Breaker** /
  **Load Balancing** / **Canary Testing** / **Virtual Keys**。
* 路由策略写法(节选自 docs):
  ```jsonc
  {
    "strategy": { "mode": "fallback" },
    "targets": [
      { "provider": "@openai-prod",  "default_params": {"temperature": 0.7} },
      { "provider": "@anthropic-prod" }
    ]
  }
  ```
* 「Passthrough」模式(只定义路由策略、不绑 provider)允许把路由策略**与密钥解耦**,
  这是把 config 当成 SaaS 内一类资源来卖的常见做法。
* Admin API 暴露细粒度遥测:`get-cache-hit-rate-data`、`get-cost-data`、
  `get-rescued-requests-data`、`get-weighted-feedback-data` 等 30+ 端点,
  直接为成本归因做数据底座。

### 2.4 Helicone 的横向对比(2025-11~12 公开博文)

来源: `helicone.ai/blog/openrouter-alternatives-2025`、
`helicone.ai/blog/top-5-llm-gateways-2025`

* 评测维度明确把「intelligent load balancing、cost reduction、99.99% uptime」列为
  生产级路由基础设施的三件套。
* 对 OpenRouter 的评价:「再也不是『默认便宜的万能入口』,而是要在延迟、合规、
  路由透明性上和自建网关做 trade-off」——佐证了「价格/成本」只是路由**目标函数**之一。

---

## 3. 主题聚焦:四件成本优化的「回路」

把上面 4 个产品的能力对照,发现每家都在做**这四件事**,只是实现深度不同:

| 回路 | Envoy AI GW | OpenRouter | Portkey | Helicone |
| --- | --- | --- | --- | --- |
| ① **价格仲裁(price sort)** | 由 admin 通过 CRD 配 | API 内置 `sort=price` | Config 显式配 provider | Gateway 决策层 |
| ② **Prefix / 语义缓存** | `cache_control` 三家一致 | 隐式(provider 自带) | 显式 Simple & Semantic | 自带 cache 模块 |
| ③ **Fallback / Circuit** | MCPRoute 多个 backend | 隐式(provider 列表) | `strategy.mode=fallback` | built-in |
| ④ **成本归因数据** | Prometheus + OTel | GraphQL/Admin | 30+ admin analytics API | 内置 dashboard |

「**语义路由**」在 2026 上半年的真正含义,已经不是「用一个 embedding 把 query
路由到合适模型」那么狭窄,而是把上面 4 个回路收成**一个策略对象**:

```
   sort = { cost | latency | throughput }   # 选路
   cache = { simple | semantic(prefix) }     # 复用
   fallback = [provider_b, provider_c, ...]  # 兜底
   attribution = { tenant, feature, model }  # 分账
```

Envoy v0.6.0 的「跨厂商 prefix cache」「统一 `reasoning_effort`」让 ② 真正可移植;
OpenRouter 的 `provider.sort` 把 ① 变成 API 一等公民;Portkey 的 Admin API 把 ④
做成可观测的「计费面板」;Helicone 把前三者组装成「评测/对比」用例。

---

## 4. 选型速记(本次主题的 take-away)

1. **如果你在做 SaaS 内部网关** — 抄 Envoy AI Gateway 的 schema 抽象:把
   `provider、model、reasoning、cache_control` 收敛到一份请求规格,可以省下
   大量「为每个模型写一遍客户端」的代码。
2. **如果你在做 to-C 路由/分流** — 抄 OpenRouter 的「`provider.sort` +
   `provider.zdr`」设计:把**目标函数**和**约束**(成本/合规)都放进请求体,
   客户端可以自助路由,不需要后端改 config。
3. **如果你的瓶颈是「成本归因」** — 抄 Portkey 的 admin API 拆分:把
   `cost、cache、rescued、feedback` 做成时间序列/分组 API,而不是塞进通用
   analytics 端点。
4. **避免的陷阱**:
   * 不要把「语义路由」等同于「用一个小模型把 query 分到 4 个目标模型」。
     真正的语义路由是 **prefix 缓存键 + 价格索引 + fallback 表** 三者交叉。
   * 不要把 `reasoning_effort` 当成「旋钮换名字」,不同厂商的实际语义差异巨大
     (Anthropic = thinking budget;Gemini 3 = 离散档位)。网关要做的是**字段映射**,
     不是「值传递」。

---

## 5. 待观察(下次主题:G Guardrails & 安全, hour%7=4)

* v0.6.0 引入的 *request/response body redaction* 落在网关数据面还是控制面?会不会
  误伤 streaming / function calling 的 tool call payload?(下次安全专题会重点看)
* OpenRouter 的 `Exacto` 排序是「按 SLA 价格」还是「按 token 实际成交价」?需要
  找一份近 30 天的 changelog 进一步确认。
* Anthropic prompt caching 在网关层做 `cache_control` 拼接时,key 是不是按
  `system + tools` 哈希?如果不同工具描述导致命中率 0,需要单独写一份 cache 调优。

---

## 引用与数据来源

1. Envoy AI Gateway v0.6.0 release notes — `https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0`(2026-05-05)
2. Envoy AI Gateway v0.6.0-rc1 — `https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0-rc1`(2026-04-30)
3. Envoy AI Gateway v0.5.0 release notes — `https://github.com/envoyproxy/ai-gateway/releases/tag/v0.5.0`(2026-01-23, prompt caching 引入)
4. Envoy AI Gateway blog index — `https://aigateway.envoyproxy.io/blog/`(2026-06 访问)
5. OpenRouter 官网 — `https://openrouter.ai/`(2026-06-05 访问;346 个模型,100T tokens/月,60+ providers)
6. OpenRouter `/api/v1/models` — `https://openrouter.ai/api/v1/models`(2026-06-05 访问)
7. Portkey docs home — `https://portkey.ai/docs`(2026-06-05 访问,含 AI Gateway / Agent Gateway / MCP Gateway / Cache(Simple & Semantic)等菜单)
8. Portkey llms.txt 索引 — `https://portkey.ai/docs/llms.txt`(2026-06-05 访问,admin analytics 端点清单)
9. Portkey configs & strategies 文档 — `https://docs.portkey.ai/docs/product/ai-gateway-streamline-llm-integrations/configs`(2026-06-05 访问)
10. Helicone blog index — `https://www.helicone.ai/blog`(2025-11~12 多篇 gateway 对比/选型)
11. Helicone「OpenRouter Alternatives 2025」— `https://www.helicone.ai/blog/openrouter-alternatives-2025`(2025-12)
12. Helicone「Top 5 LLM Gateways 2025」— `https://www.helicone.ai/blog/top-5-llm-gateways-2025`(2025-11)
13. GitHub API rate limit 自查 — `https://api.github.com/rate_limit`(本次 token 4982/5000 剩余,2026-06-05 03:08 CST)

> 本次未触及的子主题(per-topic rule):multi-agent 编排(下次 4 时/12 时 Guardrails 之后
> 的 agent gateway 专题会覆盖);MCP 路由安全(在 03 时 MCP 专题里覆盖);
> OpenTelemetry/成本归因的工程实现在 hour%7=5 的可观测专题里展开。
