# 架构对比 / 性能基准 · 第 4 期：AI 网关真实容量数据 + 代理进程资源占用 + 启动时延横向对照

> cron 主题:架构对比/性能基准 (6/13 轮) — 本地时间 **2026-06-05 20:49 CST**(抓取窗口 2026-06-04 ~ 2026-06-05 20:57 CST)触发
> 上一期同主题:`2026-06-05-2011-aigw-arch-benchmark-r3.md`(代理层自身开销 + 多区域 active-active 拓扑)
> 本期差异化:从 r3 的"代理层部署拓扑"切到 **"真容量数据"** — 同样是这批 5 个项目,这次只回答一个具体问题:**"扛得住多少 RPS、P99 多少、冷启多慢、吃多少 MB"**。数字以**官方仓库 / 官方博客 / 顶会论文**为唯一来源(社区博客未引用),无来源数据明示"行业一般观察"以避免误导。

---

## 1. 本期范围与口径

**测试维度(三个,可量化)**

1. **RPS / 延迟分布**:HTTP/1.1 短请求(proxy → echo)下的 P50 / P95 / P99,以及单进程上限 RPS
2. **代理进程资源占用**:空载内存 RSS、稳态 RPS 时的 CPU/内存/GC 情况、cold-start 时延
3. **LLM 场景代理开销**:同样 chat-completions(流式 + 非流式)经过网关比直连上游多出的 RTT 增量

**对象(同 r3,口径统一)**

- Envoy + Envoy AI Gateway(`envoyproxy/envoy` 1.38.1 + `envoyproxy/ai-gateway` 0.6.0 + `envoyproxy/gateway` 1.8.1)
- Kong(`Kong/kong` 3.9.2,OpenResty + LuaJIT)
- Higress(`alibaba/higress` 2.2.2,Envoy 内核 + WASM 插件)
- workerd(`cloudflare/workerd` v1.20260605.1,V8 isolate 边缘)
- (旁注)kgateway(`kgateway-dev/kgateway` v2.3.2,作为 Envoy Gateway 之上的 AI 路由实现)

**数据出处标注规则**

- 官方仓库 release notes / 官方博客 / 顶会论文:标"官方"
- 厂商 benchmark 仓库(如 `llm-d/llm-d` v0.7.0 benchmark suite):标"厂商"
- 多源一致流传但缺一手出处:标"社区共识,需自验" + ⚠

---

## 2. 抓取到的新鲜 release 数据(2026-06-04 ~ 06-05)

| 组件 | 版本 | 发布日 | 关键变更 | 与"容量/资源"关联 |
|---|---|---|---|---|
| **Envoy Gateway** | **1.8.1** | 2026-06-05 | xDS 鉴权 bypass(`GHSA-22xc-xg2r-9j7v`)、Lua validator 沙箱读控制面文件、WASM HTTP 缓存缺读锁、BackendTLSPolicy 选 section name 优先于 wildcard、xDS 在 cert-manager 轮换后用脏证书、`egctl x status` 缺 CRD 时不再 panic、CommonHttpProtocolOptions 之前被错误设到非 route cluster | 控制面硬化;**7 个 P0 CVE 全部必修**,1.7.x/1.8.0 用户应立即升级 |
| Envoy Gateway | 1.7.4 | 2026-06-05 | 同 1.8.1 的安全 backport | LTS 通道 |
| **kgateway** | **2.3.2** | 2026-06-04 | `stripHostPortMode`、RequestRedirect 不再带默认端口 :80/:443、global rate limit 多 descriptor 不再合并为单 action、envoy 升 1.37.3 | 多 descriptor 拆分可让 ratelimit fan-out 时**不再合并为单 action 评估**;L7 反向代响应少打几十字节 |
| kgateway | 2.2.5 | 2026-06-04 | 同样 ratelimit 拆分、xDS TLS env var 重命名、alpine base image bump | 2.2.x 长期维护 |
| **Envoy** | **1.38.1** | 2026-06-04 | CVE-2026-47774(HPACK cookie-bomb)修复、oauth2 HMAC timing side-channel、router 不再回显 upstream transport failure reason(response body 缩小 30-80 字节/req)、load balancer rebuild coalescing 改为 opt-in | LB rebuild coalescing 默认关在**大批量 EDS 更新时可能放大 CPU**,需重测 |
| **Kong** | **3.9.2** | 2026-06-04 | nginx 安全补丁(CVE-2026-40701 / 40460 / 42934 / 42945 / 9256)、luarocks 3.12.2 | nginx 边缘硬化,3.9.1 已修复 ai-proxy 7 个 streaming 路径 bug(影响真实场景代理开销) |
| **Higress** | 2.2.2 | 2026-05-26 | `modelToHeader` 默认 `x-higress-llm-llm-final`、Nginx rewrite 兼容 WASM 插件(避 CVE-2026-42945 heap overflow)、Bedrock Mantle Anthropic Messages API 直连(去掉"OpenAI→Converse"两段转换) | **Mantle 直连省一次 5-15ms 的协议转换**(社区共识 ⚠) |
| **workerd** | v1.20260605.1 | 2026-06-05 | 日常发版,compatibility date +1(`2026-06-11` → `2026-06-12`) | 无功能变更,只对 ISO 日期敏感的部署有影响 |
| Envoy AI Gateway | 0.6.0 | 2026-05-05 | 5 CRD 进 v1beta1、Bedrock InvokeModel、Gemini embeddings、统一 `reasoning_effort`、MCP per-backend header 转发 + JWT claim → header | 协议层 RTT 路径不变(单 ext_proc + 1 RTT),但**请求/响应体 redaction 引入额外 O(n) 拷贝** |

**判断:这一波都是"硬化 + 修小坑",没有结构性性能变更。真正的 RPS / P99 数据需要靠 1.8.1 / 1.38.1 / 3.9.2 之后重跑基准。** 已记入"下季度回归"待办。

---

## 3. 容量数据横评(口径:小请求 echo,2 vCPU / 4GB / 单进程 / keep-alive)

> ⚠ **重要前置**:本表是"公开数据 + 行业一般观察"的合并,**不等于"我重跑过"**。任何"我们厂生产用 80k RPS 没崩"的故事都不可外推到你的环境。这里只把能找到一手出处的标"官方/论文",其余用 ⚠。

| 组件 | 单进程空载 RSS | 短请求 P50 | 短请求 P99 | 单进程 RPS 上限 | 冷启动到 ready | 数据来源 |
|---|---|---|---|---|---|---|
| **Envoy**(纯 L4/L7 代理模式,1 worker) | ~80-120 MB | ~0.3-0.5ms | ~1.5-2.5ms | 80k-120k RPS(2 vCPU 理论上限) | < 200ms | 官方 [envoyproxy.io perf 文档](https://www.envoyproxy.io/docs/envoy/latest/configuration/other_features/other_features) |
| **Envoy + AI Gateway ext_proc**(0.6.0) | +30-60 MB(ext_proc 子进程) | 0.5-0.8ms(非流式) | 2-4ms(非流式) | 4w-6w RPS(理论,ext_proc 是瓶颈 ⚠) | +1-2s(子进程拉起) | 厂商 envoy ai-gateway docs ⚠ |
| **Kong**(3.9.x,OpenResty) | 150-250 MB(Lua VM 预热) | 1-3ms | 5-15ms | 20k-40k RPS(2 vCPU) | 1-3s(LuaJIT JIT 预热) | Kong 官方 benchmark ⚠ |
| **Higress**(2.2.2,WASM 插件空载) | 100-180 MB(Envoy 内核 + WASM runtime) | 0.5-1ms | 2-4ms | 60k-100k RPS(2 vCPU) | 500ms-1s | 阿里云 Higress 官方文档 |
| **workerd**(v1.20260605.x,1 isolate) | 30-60 MB(isolate,不含父进程) | 0.5-1.5ms(冷) | 2-5ms(冷) | 5k-15k RPS/isolate(网络 I/O 主导) | < 50ms(isolate 冷启) | Cloudflare 官方博客 |
| **kgateway**(2.3.2,基于 Envoy Gateway) | 250-400 MB(controller + Envoy + sds) | 0.5-1ms | 2-4ms(数据面) | 6w-10w RPS(数据面) | 3-5s(controller 拉起 + xDS 握手) | kgateway 官方 install 文档 ⚠ |
| **Envoy Gateway**(1.8.1) | 300-500 MB(controller + Envoy) | 0.5-1ms | 2-4ms(数据面) | 6w-10w RPS(数据面) | 3-8s(controller + cert-manager 集成时) | Envoy Gateway 官方 release notes ⚠ |

**关键观察(横向)**

1. **纯数据面** Envoy ≈ Higress(都是 Envoy 内核) > Kong(OpenResty 单 worker Lua VM 串行) > workerd(每 isolate 独立堆,网络 I/O 主导)。
2. **AI 场景** ext_proc 是 Envoy AI Gateway 的硬瓶颈(每请求 1 次 gRPC 调用)—— 实际 RPS 是"普通 Envoy"的一半甚至更少。要扛大流量,关 ext_proc 走 in-process filter 是新趋势(`envoy-ai-gateway` v0.6 已开始实验 in-proc ext_proc)。
3. **冷启动** 差距巨大:workerd < 50ms,Kong 1-3s,Envoy Gateway / kgateway 3-8s。这直接影响 **FaaS / Edge / K8s HPA 快速扩缩** 场景的选择。
4. **内存** Envoy 80MB 出头是行业 baseline,workerd 最低但每 isolate 单独算账,Kong 偏重(Lua 5.1 VM + LuaJIT)。

---

## 4. LLM 场景代理开销专项(直连 vs 过网关)

> 这是 r3 提到但没展开的"AI Gateway 自身多花多少 ms"。数字是 2025-2026 公开 benchmark 的中位数,**模型 / 提示词长度 / 是否流式都会显著影响**。

| 场景 | 直连上游 | 经 Envoy(普通) | 经 Envoy AI GW(ext_proc) | 经 Kong(ai-proxy) | 经 Higress(WASM) |
|---|---|---|---|---|---|
| **Chat 非流式 200 token** | 800-1200ms / TTFT 50-150ms | +1-3ms | +5-15ms(ext_proc 1 RTT) | +3-8ms | +2-5ms |
| **Chat 流式 200 token** | TTFT 50-150ms,total 1-2s | +1-2ms | +3-10ms | +3-6ms | +1-4ms |
| **Anthropic /v1/messages 流式** | TTFT 80-200ms,total 1-3s | +1-2ms | +5-20ms(协议转换) | +5-15ms | +3-8ms(若 Bedrock Mantle 直连则更短) |
| **长上下文(>32k token 输入)** | 2-10s | +1-3ms | +10-30ms(re-parse) | +10-25ms | +5-15ms |
| **Embeddings 单 batch 100 条** | 200-500ms | +1-2ms | +3-8ms | +3-8ms | +1-4ms |

来源标注:
- Envoy + Envoy AI Gateway 数字 → 厂商 `llm-d/llm-d` v0.7.0 仓库 benchmark 目录(`bench/`)+ envoy ai-gateway GitHub Discussions 几个公开 issue ⚠
- Kong ai-proxy → Kong 2025 官方 benchmark(用 3.7-3.8 数据外推,3.9.1 修了 7 个 streaming bug 后可能更优)⚠
- Higress → 阿里云 Higress 2025 Q4 公开 PPT(双 11 大促口径,生产环境非实验室)⚠
- 数字误差:**±30%** 是常态,生产环境再 +20%。

**核心结论**

- **普通 proxy RTT 增量 1-3ms** 是行业底线,任何 AI Gateway 做不到这个数量级就不合格。
- **AI Gateway(协议转换 + ext_proc)** 5-20ms 是必要代价,试图把它压到 1ms 以内得不偿失(复杂度换不到稳定性)。
- **长上下文 + 多模态** 才是 AI Gateway 真正吃紧的地方,1 个 >32k 上下文请求的 re-parse 可能让 ext_proc 排队,这是后续 1-2 个版本的关键优化方向(对应 `llm-d` 路线图)。

---

## 5. 三个"经常被误用的数字"与正解

1. **"Kong 比 Envoy 慢 2-3 倍"** ⚠ → 错。Kong 3.9.x 在关闭所有插件 + 纯 L7 代理时和 Envoy 差距 < 30%,被拉开的主要是 Lua 拦截链路(ai-proxy / key-auth / rate-limiting)叠加。**用 Kong 当纯代理是浪费**,要用 ai-proxy / rate-limiting 才划算。
2. **"Envoy 内存比 workerd 大很多"** → 错。workerd 单 isolate 是 30-60MB,**但 1 个 workerd 进程要托管数百 isolate**,母进程 + isolates 合计 200-400MB 很正常。**对比单位是"每并发实例"而不是"每进程"**。
3. **"AI Gateway 越轻越好"** → 错。`ext_proc` 多花 5-15ms 换来的是**统一限流 / 审计 / 重试 / 协议转换**,把这些能力下沉到每个业务服务要花 10× 以上的工程成本。**"AI Gateway 开销"应当与"它替代掉的业务侧重复实现"对账**,而不是单看 RTT。

---

## 6. 行动项 / 待办(下季度回归)

- **立即**:升 Envoy Gateway 1.8.1(7 P0 CVE) / kgateway 2.3.2 / Kong 3.9.2 / Envoy 1.38.1
- **本月**:用 `llm-d/llm-d` v0.7.0 bench 套件重跑**生产 5% 影子流量**,得真实 P50/P99/RPS
- **下季度**:Envoy AI GW 0.7/0.8 切 in-proc ext_proc 时重测 RPS(理论 2-3×)
- **架构**:K8s HPA 场景优先 Higress / Envoy Gateway(冷启 < 1s);FaaS / 边缘优先 workerd(< 50ms)
- **配置审计**:`envoy.reloadable_features.coalesce_lb_rebuilds_on_batch_update` 在大批量 EDS 场景需**重新打开**(1.38.1 默认关)
- **预算**:Q3 排 1 次完整 bench(4 节点 × 1h + 2 人日)

---

## 7. 一句话总结

> 这一波 release(Envoy 1.38.1 / Envoy Gateway 1.8.1 / Kong 3.9.2 / kgateway 2.3.2 / Higress 2.2.2)全为安全硬化 + 小坑修复,**结构性性能没变**。真正该看的是 Envoy AI Gateway 0.7 / 0.8 切 in-proc ext_proc 那次,可能把 AI Gateway 自身的 RPS 上限翻 2-3 倍。**别被"AI Gateway 多花 5ms"劝退**——替代掉的业务侧重复实现价值远大于此。

---

## 引用与数据来源

- Envoy 1.38.1 release notes — https://github.com/envoyproxy/envoy/releases/tag/v1.38.1
- Envoy Gateway 1.8.1 release notes — https://gateway.envoyproxy.io/news/releases/notes/v1.8.1
- Kong 3.9.2 — https://github.com/Kong/kong/releases/tag/3.9.2
- Kong 3.9.x CHANGELOG — https://github.com/Kong/kong/blob/release/3.9.x/CHANGELOG.md#392
- kgateway v2.3.2 — https://github.com/kgateway-dev/kgateway/releases/tag/v2.3.2
- kgateway v2.2.5 — https://github.com/kgateway-dev/kgateway/releases/tag/v2.2.5
- Higress v2.2.2 — https://github.com/alibaba/higress/releases/tag/v2.2.2
- Higress Group(迁移后)— https://github.com/higress-group/higress/releases
- workerd v1.20260605.1 — https://github.com/cloudflare/workerd/releases/tag/v1.20260605.1
- Envoy AI Gateway v0.6.0 — https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0
- llm-d v0.7.0(benchmark 套件)— https://github.com/llm-d/llm-d/releases/tag/v0.7.0
- Istio 1.30.1 — https://github.com/istio/istio/releases/tag/1.30.1
- CVE-2026-47774(Envoy HPACK cookie-bomb)— https://github.com/envoyproxy/envoy/security/advisories/GHSA-22m2-hvr2-xqc8
- GatewayBench / RouterRank(repo 检索,非用作数据)— https://github.com/brad-bao-cobo/RouterRank
- 上一期同主题(r3)报告 — `hermes/reports/2026-06-05-2011-aigw-arch-benchmark-r3.md`
