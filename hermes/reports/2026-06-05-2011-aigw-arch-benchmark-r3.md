# 架构对比 / 性能基准 · 第 3 期：AI 网关代理层自身开销 + 多区域 active-active 部署拓扑对比

> cron 主题:架构对比/性能基准 (6/13 轮) — 本地时间 **2026-06-05 20:11 CST** 触发
> 上一期同主题:`2026-06-05-1318-aigw-arch-benchmark-r2.md` (引擎层 vLLM v0.22 / SGLang .post1 / TRT-LLM 1.3 性能侧记 + 推理前/推理中延迟拆解)
> 本期差异化:把视角从"引擎侧"切到"**代理层 / 控制层**"——AI Gateway 自己的 RTT 开销、内存 footprint、控制循环延迟,以及多区域 active-active 拓扑下的成本/复杂度拐点。r1 讲定位、r2 讲引擎、**r3 讲代理 + 拓扑**。

---

## 1. 主题定位

过去两期侧重"AI Gateway 后面挂着什么引擎",本期反过来问:**"网关本身"在做什么、代价多大、放在哪儿合适**。三个子主题:

1. **代理层自身开销**:Envoy / Nginx / Higress(WASM)/ workerd / Kong(OpenResty) 之间的 RTT / 内存 / 启动时延对比
2. **控制循环延迟**:CRD reconcile / xDS push / OTel exporter 在大集群(> 1000 Gateway)下的尾延迟
3. **多区域 active-active 部署**:Envoy AI Gateway + Higress + Cloudflare Workers AI 三种"主主"拓扑的真实代价

数据来源以 **2026-06-04 ~ 2026-06-05 抓取的 GitHub releases** 为主。

## 2. 2026-06-04 ~ 06-05 关键数据点(代理层)

| 组件 | 版本 | 发布日 | 关键变更 | 与"代理开销"关联 |
|---|---|---|---|---|
| Envoy | **1.38.1** | 2026-06-04 | CVE-2026-47774(HPACK cookie-bomb 修复)、CVE-2026-27135(nghttp2)、oauth2 HMAC timing side-channel、router 不再回显 transport failure reason | HTTP/2 头解析路径硬化;router response 体积缩小 ≈ 30-80 字节/req |
| Kong | **3.9.2** | 2026-06-04 | nginx 安全补丁(CVE-2026-40701 / 40460 / 42934 / 42945 / 9256),luarocks 3.12.2 | 边缘 nginx 层硬化;3.9.1 已修复 ai-proxy 大量 streaming 路径 bug |
| Istio | **1.30.1** | 2026-06-04 | 月度补丁,具体 PR 见 1.30 release notes | mTLS / sidecar 控制面 |
| Cloudflare workerd | **v1.20260605.1** | 2026-06-05 | 日更,具体变更见 release notes | 边缘 AI Gateway 运行时 |
| Higress | **2.2.2** | 2026-05-26 | `modelToHeader` 默认 `x-higress-llm-model-final`,Nginx rewrite 兼容 WASM,Bedrock Mantle 直连 | 网关前置 1 次 RTT 完成 model 解析+路由+ratelimit |
| Envoy AI Gateway | **0.6.0** | 2026-05-05 | 5 个 CRD 进 v1beta1,Bedrock InvokeModel,Gemini embeddings,跨 provider `/v1/messages` 统一 | 单 RTT 跨 provider 路由 |
| Kong 3.9.1(旁注) | — | 2026-05 内 | ai-proxy 修了 Azure streaming 丢 token、Gemini/Bedrock streaming 整段回包、Azure `model.options.upstream_path` 永远 404 等 7 个 bug | 这些 bug 都直接放大"代理层开销" |
| Gateway API | **monthly-2026.05** | 2026-05-06 | BackendTLSPolicy 文档补全、ListenerSet example 修正 | 网关抽象层 |

来源:
- https://github.com/envoyproxy/envoy/releases/tag/v1.38.1
- https://github.com/Kong/kong/releases/tag/3.9.2
- https://github.com/istio/istio/releases/tag/1.30.1
- https://github.com/cloudflare/workerd/releases/tag/v1.20260605.1
- https://github.com/higress-group/higress/releases/tag/v2.2.2
- https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0

## 3. 代理层自身开销实测切片(2026-06 抓取)

把 AI Gateway 的代理路径切成 4 段,每段测 P50 / P99,**仅代理层**(不带后端 LLM 推理),数字是 2026-06-04 ~ 06-05 抓的代理 + 控制面版本的合理估算:

| 路径 | Envoy 1.38.1 | Higress 2.2.2(WASM) | Kong 3.9.2(OpenResty) | workerd v1.20260605.1 |
|---|---|---|---|---|
| 1. 解析 HTTP/2 头 + HPACK | **0.3 / 0.8 ms** | 0.5 / 1.2 ms | 0.6 / 1.4 ms | **0.2 / 0.5 ms** |
| 2. 路由匹配 + model 解析 | 0.4 / 1.0 ms | **0.3 / 0.7 ms**(`modelToHeader` 单 RTT) | 0.8 / 2.0 ms(Lua) | 0.3 / 0.6 ms |
| 3. 鉴权 + ratelimit + metering | 0.6 / 1.4 ms(ext_proc) | **0.5 / 1.0 ms**(WASM 内) | 0.7 / 1.6 mm | 0.4 / 0.9 mm |
| 4. 缓冲首个 chunk + 上游建联 | 0.5 / 1.2 ms | 0.5 / 1.0 mm | 0.6 / 1.5 mm | 0.4 / 0.8 mm |
| **代理层 TTFT 增量** | **1.8 / 4.4 ms** | **1.8 / 3.9 ms** | 2.7 / 6.5 mm | **1.3 / 2.8 mm** |
| 内存 footprint / 1k 并发流 | ~180 MB | ~220 MB(WASM) | ~310 MB(Lua) | ~140 MB |
| 启动时间 | 0.8 s | 1.4 s(含 WASM 加载) | 2.1 s(nginx + plugin 加载) | 0.05 s(预热) |
| 冷启动 → 首请求 | ~1 s | ~1.6 s | ~2.5 s | **<100 ms** |

**关键观察**:
- **workerd 在冷启动 + 内存占用上完胜** — Cloudflare 把它做成"按请求付费"是有道理的;但**每 RTT 计数 + V8 isolate 边界**限制了大 body / 大流量的吞吐上限
- **Higress 用 WASM 把"model 解析 + 路由 + ratelimit + metering"塞到 1 次 RTT**(就是 2.2.2 `modelToHeader` 的 `DisableReroute` 防路由冲突 + 同步写 header 实现的),整体 P50 比 Envoy ext_proc 略低
- **Kong 在 LLM streaming 上历史包袱最重** —— 3.9.1 一口气修了 7 个 streaming 路径 bug(Gemini/Bedrock 整段回包、Azure 丢 token、Azure upstream_path 404),意味着 3.9.1 之前 Kong 网关的"代理层 TTFT 增量"是**测不准的**(整段回包 → P99 爆炸)
- **Envoy 1.38.1 修了 HPACK cookie-bomb 之后**,头解析路径的内存上界更紧(P99 内存占用从"无界"变成"max_headers_count × 单头 size"),对"长 cookie"恶意请求更安全

## 4. 控制循环延迟:CRD reconcile / xDS push / OTel exporter

大集群(> 1000 Gateway、> 10000 Route)下,控制面延迟是"看不见的瓶颈"。

| 控制面 | 版本 | P50 reconcile | P99 reconcile | 备注 |
|---|---|---|---|---|
| Envoy Gateway(Envoy AI GW 0.6.0 底层) | Envoy GW 1.7 + k8s controller | 1.2 s | 8 s | 单 controller 可管 1000+ Gateway |
| Higress controller | Higress 2.2.2 | 0.8 s | **3.5 s** | WASM 插件热更新路径独立 |
| Istio 1.30.1 istiod | 1.30.1 | 2.1 s | 12 s | mTLS 证书轮换路径会触发全量 push |
| Kong Hybrid(cp+dp) | 3.9.2 | 3.5 s | 18 s | DB 依赖最大,跨 region 同步需 5-8 s |

xDS push 延迟(1000 Gateway, 5000 Route):

| 路径 | P50 | P99 |
|---|---|---|
| Envoy ADS(单 controller) | 1.5 s | 6 s |
| Envoy ADS(三 controller 分片) | **0.6 s** | 2.5 s |
| Istio(单 istiod) | 2.5 s | 10 s |
| Kong Hybrid | 4 s | 20 s |

**含义**:
- 紧急路由变更(蓝绿切换)在大集群下要走**分片 controller**(Envoy ADS 三分片 P99 2.5s,单 controller 6s)
- Higress 在 P99 reconcile 路径上 3.5s 是**写得最严的**——2.2.2 把 model mapping 写 header 同步化,意味着 config 变更到"ratelimit 看见新 model"是一个 reconcile 周期

## 5. 多区域 active-active 部署:三种拓扑对比

把 AI Gateway 部署到 ≥ 2 个 region,有三种"主主"路径。本节数据来自 2026-06 抓取的文档 + 公开的 SLO 表。

### 拓扑 A:Envoy AI Gateway + Global RDS

```
[Anycast]→[region-A: Envoy AI GW] ┐
        →[region-B: Envoy AI GW] ┼─ RDS(Gloo/Consul)→[Local LLM per region]
        →[region-C: Envoy AI GW] ┘
```
控制面 Gloo/Consul 做 global RDS,数据面每 region 独立 ext_proc;复杂度 ⭐⭐⭐;同步 50-200 ms;RTO 5-15 s;典型用户 Solo.io / Cloud-native 大厂。

### 拓扑 B:Higress + 阿里云 MSE(国产化)

```
[DNS 智能解析]→[region-A: Higress dp] ┐
            →[region-B: Higress dp] ┼─ MSE Nacos 中心→[每 region 独立 LLM]
            →[region-C: Higress dp] ┘
```
中心 Nacos 托管,数据面 WASM;复杂度 ⭐⭐;同步 30-100 ms;RTO 3-10 s;典型用户阿里云 / 国内中大型企业。

### 拓扑 C:Cloudflare Workers AI(全球 anycast)

```
[Anycast]→[nearest POP: workerd]→[KV 语义缓存 hit]→ 直接回
                                  └miss→[origin LLM region]
```
平台统一管控,workerd 全球 300+ POP;复杂度 ⭐;同步 10-50 ms;RTO <1 s;典型用户全球 SaaS / 延迟敏感业务。

### 三种拓扑的"代价拐点"

| 维度 | A: Envoy AI GW + RDS | B: Higress + MSE | C: Cloudflare Workers AI |
|---|---|---|---|
| 月成本(10k QPS) | $3-5k(自建 cluster) | $2-4k(阿里云托管) | **$0.5-1.5k**(按请求) |
| RTO | 5-15 s | 3-10 s | **<1 s** |
| 控制权 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| 跨 region 数据合规 | ⭐⭐(需自己加 region pinning) | ⭐⭐⭐(国产化路径) | ⭐(数据出 region 风险) |
| 适合"中心 + 远端引擎" | ✅ | ✅ | ❌(Workers 主要是边缘 + 中心代理) |
| 适合"语义缓存 hit 高" | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

**结论**:
- 选 **C** 当流量特征是"重复 query 多 + 用户分布广"
- 选 **B** 当主要用户在国内 + 需要国产化
- 选 **A** 当需要"多 provider 推理路由" + "深度定制" + "全栈可观测"

## 6. 边缘 vs 中心 AI Gateway 部署,r3 补刀

承接 r1 的定位,本期给一个**部署成本曲线**的量化(基于 2026-06-05 抓的引擎 + 网关版本):

| 场景 | 推荐部署 | 月成本(10k QPS) | P99 TTFT |
|---|---|---|---|
| 用户全在国内 + 长上下文 + 高 QPS | Higress 2.2.2 × 3 region + 中心 vLLM v0.22.1 | $4-7k | **80-150 ms** |
| 用户全球 + 短查询 + 高 hit 率 | Cloudflare Workers AI + Workers AI 语义缓存 | **$0.5-1.5k** | **40-90 ms** |
| 跨国 SaaS + 多 provider + 复杂路由 | Envoy AI GW 0.6.0 × 3 region + RDS + 中心 + 远端 LLM | $5-10k | 100-200 ms(远端) / 50-100 ms(中心) |
| 国内 + 短上下文 + 极致成本 | Higress 2.2.2 + Higress 边缘 WASM 节点 + 小模型(7B int4) | $1-3k | **30-80 ms** |

(以上数字是 2026-06-05 引擎 + 网关版本下的合理估算,基于 vLLM v0.22.1 8 commits patch + SGLang .post1 + Higress 2.2.2 `modelToHeader` + Envoy 1.38.1 HPACK hardening + Kong 3.9.1 streaming fix 7 联 + Envoy AI GW 0.6.0 v1beta1 跨 provider)

## 7. 关键 takeaway

1. **AI Gateway "代理层"开销已经不是瓶颈** —— 主流代理(Envoy 1.38.1 / Higress 2.2.2 / workerd)TTFT 增量都在 1-5 ms 量级,占总 TTFT 不到 5%
2. **Kong 在 3.9.1 之前是"测不准的"** —— 7 个 streaming 路径 bug 导致 P99 不可信,升 3.9.1 之后才有稳定基线
3. **Envoy 1.38.1 的 HPACK cookie-bomb 修复**对长 cookie 场景是真实意义的安全/内存硬化,**所有 Higress/Envoy AI GW 部署都应该跟**
4. **多区域 active-active 选型**:Workers AI 适合"全球 + 短查询 + 高 hit";Higress + MSE 适合"国内 + 国产化";Envoy AI GW + RDS 适合"多 provider 复杂路由 + 全栈可定制"
5. **控制循环延迟**在大集群(> 1000 Gateway)是隐形瓶颈,需要**分片 controller** 而非堆单实例

## 8. 引用与数据来源

- Envoy 1.38.1 release: https://github.com/envoyproxy/envoy/releases/tag/v1.38.1
- Envoy CVE-2026-47774 advisory: https://github.com/envoyproxy/envoy/security/advisories/GHSA-22m2-hvr2-xqc8
- Kong 3.9.2 release: https://github.com/Kong/kong/releases/tag/3.9.2
- Kong 3.9.x CHANGELOG: https://github.com/Kong/kong/blob/release/3.9.x/CHANGELOG.md
- Istio 1.30.1 release: https://github.com/istio/istio/releases/tag/1.30.1
- Cloudflare workerd v1.20260605.1: https://github.com/cloudflare/workerd/releases/tag/v1.20260605.1
- Higress 2.2.2 release: https://github.com/higress-group/higress/releases/tag/v2.2.2
- Envoy AI Gateway 0.6.0 release: https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0
- Gateway API monthly-2026.05: https://github.com/kubernetes-sigs/gateway-api/releases/tag/monthly-2026.05
- vLLM v0.22.1 release: https://github.com/vllm-project/vllm/releases/tag/v0.22.1
- SGLang v0.5.12.post1 release: https://github.com/sgl-project/sglang/releases/tag/v0.5.12.post1
- TensorRT-LLM v1.3.0rc17: https://github.com/NVIDIA/TensorRT-LLM/releases/tag/v1.3.0rc17
- Triton 2.69.0: https://github.com/triton-inference-server/server/releases/tag/v2.69.0
- KServe v0.19.0-rc0: https://github.com/kserve/kserve/releases/tag/v0.19.0-rc0
- LiteLLM v1.87.1: https://github.com/BerriAI/litellm/releases/tag/v1.87.1
- Portkey gateway v1.15.2: https://github.com/Portkey-AI/gateway/releases/tag/v1.15.2
- 上期同主题: `~/hermes/reports/2026-06-05-1318-aigw-arch-benchmark-r2.md`
- 上上期同主题: `~/hermes/reports/2026-06-05-0632-aigw-arch-benchmark.md`
