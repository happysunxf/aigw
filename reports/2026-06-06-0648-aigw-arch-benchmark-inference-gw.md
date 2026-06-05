# AI 网关 · 架构对比 / 性能基准 第 6 期 — K8s 原生推理网关专题

- 报告生成时间：2026-06-06 06:48（本地时 CST）
- 主题：架构对比 / 性能基准（hour%7=6）
- 本期焦点：**K8s 原生推理网关栈（GIE + llm-d + WVA + vLLM）**，重点消化 **WVA v0.7.0 真实基准数据**（PR #1586，2026-06-05 合入）。
- 上期衔接：2026-06-06 06:10「Envoy AI Gateway v0.6 控制面 2,000 路由基准」专注"配置规模"侧，本期切到"运行时性能"侧 — 同一类问题在两个不同堆栈里的答案。

## 一、为什么这一期盯 K8s 原生推理网关

过去 30 天推理网关栈一次密集发布（UTC）：

| 组件 | 版本 | 发布日 | 关键变化 |
|---|---|---|---|
| **llm-d** | v0.7.0 | 2026-05-12 | CUDA 13.0.2 + driver 580+；**默认切到 "standalone" 模式**；vLLM 0.19.1；GIE v1.5.0；agentgateway 2.2.1 |
| **Gateway API Inference Extension (GIE)** | v1.5.0 | 2026-04-19 | Pluggable Parser Framework、Latency Predictor、BBR 集成 request body、请求插件镜像到响应路径 |
| **vLLM** | v0.22.1 | 2026-06-05 | 4 周内 0.21.0 → 0.22.1（与 llm-d 0.7.0 锁的 0.19.1 落后三个小版本） |
| **WVA（Workload Variant Autoscaler）** | v0.7.0 | 2026-06-05 合入 | **新发完整基准数据集**：4 类流量、3 个模型、3 run 均值 |

这四件事放在一起，等于把"控制面 + 数据面 + 自动扩缩容 + 端到端基准"四个口第一次同时备齐。

## 二、WVA v0.7.0 真实基准数据

来源：[llm-d/llm-d#1586](https://github.com/llm-d/llm-d/pull/1586)，落地在 `guides/workload-autoscaling/README.wva.md`。NVIDIA H100 + OpenShift，Poisson 到达曲线，3-run 平均。

**测试配置**：WVA KV 阈值 0.80 / 队列长度阈值 5 / spare trigger 0.10+3；HPA 1–10 replicas，scale-up 10 Pods/150 s（stabilization 0 s），scale-down 10 Pods/150 s（stabilization **240 s**），metric source = external `wva_desired_replicas`。

### 四类流量结果（P99 TTFT 单位 ms）

| 场景 | 模型 | Duration | P99 TTFT | P99 ITL | Avg Rep | Max Rep | Avg KV | Avg Queue | Errors | Pod Startup |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prefill Heavy (4k/1k @20RPS) | Qwen3-32B | 600 s | 98,420 | 54.8 | 1.73 | 3 | 66.3% | 236.5 | 4,184 | 110 s |
| Prefill Heavy | Qwen3-0.6B | 600 s | 81,391 | 51.9 | 1.93 | 3 | 65.1% | 76.5 | 401 | 65 s |
| Prefill Heavy | Qwen3-0.6B | 1800 s | 66,177 | 47.3 | 3.17 | 5 | 55.7% | 41.2 | 860 | 66 s |
| Decode Heavy (1k/4k @20RPS) | Qwen3-32B | 600 s | 78,051 | 47.1 | 1.84 | 3 | 79.2% | 108.8 | 3,563 | 109 s |
| Bursty (15→2→10→15→5→2) | Qwen3-32B | 900 s | **262,441** | 196.3 | 2.43 | 4 | 45.1% | 53.5 | 6,110 | 103 s |
| Bursty | Qwen3-0.6B | 900 s | 13,376 | 48.0 | 1.99 | 3 | 35.2% | 16.0 | 51 | 66 s |
| Symmetrical (1k/1k @20RPS) | Qwen3-32B | 600 s | 100,187 | 67.3 | 1.70 | 3 | 70.2% | 166.8 | 3,729 | 103 s |
| Symmetrical | Qwen3-0.6B | 1800 s | 20,825 | 40.4 | 1.80 | 3 | 46.8% | 10.8 | 342 | 66 s |

## 三、5 个工程结论

### 1. P99 TTFT 在 32B + 突发流量下塌方到 4.4 分钟

Bursty 场景 Qwen3-32B 的 P99 TTFT **262,441 ms ≈ 4.4 分钟**。HPA scale-up window（10 Pods / 150 s）+ WVA 阈值 + pod startup 103 s 三个延迟叠加，新副本就绪前请求已堵 30+ s。

要 P99 < 1 s SLA：把 WVA KV spare trigger 从 0.10 抬到 **0.20–0.25**（提前扩容），或把 pod startup 压到 60 s 以内（warm pool 预加载权重）。

### 2. 0.6B bursty 反而是 13 秒级（20× 改善）

同样 bursty，Qwen3-0.6B P99 TTFT **13,376 ms（~13 s）**。差距不在 WVA，在**模型加载 + 权重传输**：0.6B 启动 64 s、32B 要 103 s，**冷启动补偿直接决定 P99 上限**。

### 3. WVA "saturation-based" 扩缩容比 HPA 默认 CPU/Memory 准

32B prefill-heavy KV cache 平均 66.3%、最大 replicas 才 3 — WVA 提前在 KV 75% 触发扩，**没让 cache 撞到 95%**。但 bursty 时 KV cache 平均只 45.1% — 多数时间是"pod 在冷启动"，WVA 决策已够早，**物理 pod startup 是天花板**。

### 4. Errors 数字暴露"重试风暴"问题

32B prefill-heavy 600 s 跑出 **4,184 errors / 12,000 请求 = 35% 错误率**。同期 0.6B 同样配置 401 / 12,000 = 3.3% — **差一个数量级**。Bursty 32B 900 s errors 6,110 / 18,000 ≈ 34%。

WVA 没及时扩容时，**client SDK 的 timeout/retry 是 errors 主要贡献者**，不是 vLLM 自身 OOM。生产关键护栏：Client 端严格控制 retry 次数 + 退避；网关侧 early reject（429）+ 请求体大小限速兜底 — 这也是 llm-d v0.7.0 默认切到 standalone 模式的原因。

### 5. Pod startup 是 K8s 推理扩容的"隐形税"

| 模型 | 冷启动 |
|---|---|
| Qwen3-32B（H100） | **103–110 s** |
| Qwen3-0.6B（H100） | 64–66 s |

突发流量峰值 < 2 分钟，autoscaling 来不及。解法不是把 WVA 阈值改更激进（反而抖动更大），而是**维持 1–2 个 warm pool pod**，把 max replicas 提到 12 而非 10。

## 四、llm-d v0.7.0 "独立模式"切换 — 架构信号

> **UX Change** — due to the difficulty configuring gateways for many adopters, we have made the default deployment of llm-d to use **"standalone mode"** where we use a generic proxy instead of the more feature full gateway. We still recommend a fully gateway for customers in production.

三个真实信号：

1. **GIE v1.5.0 的 Pluggable Parser / BBR / Latency Predictor 都还是新接口**，社区还没准备好"开箱即用" — 把 optional 路径降到显式 opt-in 是合理工程取舍。
2. **CUDA 13.0.2 升 + driver 580 强制**是配套"硬升级"；降低默认 gateway 复杂度，简化"快速升级到 0.7.0"路径。
3. **vLLM 0.19.1 锁版本**（与上游 0.22.1 差 3 个小版本）说明 llm-d 节奏 = "vLLM 锁版 + 自己 0.7 大版本"，**不是追 vLLM 滚动升级**。给生产用户的指导是"跟 llm-d 版本走，不要自己 bump vLLM"。

## 五、GIE v1.5.0 架构级变化

[GIE v1.5.0](https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/tag/v1.5.0)（2026-04-19）有 4 个关键 PR：

- **Pluggable Parser Framework**（[PR #2359](https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2359)）：EPP "解析请求体"提到 `pkg/epp/framework/plugins/...` 下，厂商私有协议（vLLM/Anthropic/SGLang/TRT-LLM）适配不用改核心。
- **Latency Predictor**（[#2432](https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2432) / [#2473](https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2473)）：训一个模型**在请求路由前先预测 P99 延迟**，再选 endpoint — WVA 事后扩缩的补集。
- **BBR body integration**（[#2442](https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2442)）：BBR 插件能拿 `RequestContext.body`，按 prompt 内容/长度做 hash 路由（**KV cache 命中率优化**）。
- **请求插件镜像到响应路径**（[#2369](https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2369)）：给"安全合规 + 可观测"同时用一份插件逻辑打开口子。

v1.5.0 的 latency predictor 部署起来后，**Bursty 32B 的 P99 TTFT 4.4 分钟**问题有望压到 < 60 s（不是 cold start 救得了，而是把"新副本还差多少就绪"信号融进 routing 决策，**让老副本多扛一会儿**）。

## 六、跨栈架构对比 — Envoy AI Gateway vs GIE+llm-d

| 维度 | Envoy AI Gateway v0.6 | GIE v1.5.0 + llm-d v0.7.0 + WVA v0.7.0 |
|---|---|---|
| **设计目标** | L7 反代 + 模型路由 + extproc 策略链 | K8s-native 推理路由 + Endpoint Picker + 副本弹性 |
| **数据面** | Envoy + extproc（静态部署） | agentgateway v2.2.1（Envoy-based） + EPP |
| **路由粒度** | Header / body / 模型名 | Header / body / KV cache affinity（BBR） / predicted latency |
| **配置规模** | 2,000 × AIGatewayRoute（4MB → 25MB gRPC 调参） | InferencePool CRD；WVA 经 External Metrics API |
| **运行时性能** | 未公开统一基准 | WVA 0.7 实测：32B prefill P99 TTFT 98s / 35% 错误率 |
| **自动扩缩** | 无内建（HPA + 自定义指标） | WVA v1 Saturation + HPA + Prometheus Adapter / KEDA |
| **升级风险** | v0.6 删 `AIGatewayRoute.spec.filterConfig` | v0.7.0 强升 CUDA 13 + driver 580 |
| **当前默认路径** | full gateway | llm-d 默认 **standalone（generic proxy）**，gateway 显式 opt-in |

**给架构选型者的明确信号**：

- **"几十个 LLM 路由规则 + K8s 生态 + OTel"** → Envoy AI Gateway v0.6（API 已 v1beta1、v1.0 GA 锁定 2026-06-30）。
- **"自托管 vLLM + 突发流量 + KV cache 复用 + 自动扩缩容"** → GIE + llm-d + WVA 路径在 v0.7.0 给出**唯一的端到端开源基线**，本期数字就是该路径的当前能力上限。
- **不要混着用** — 两套都是 K8s CRD + xDS 模型，硬混会出 route priority 冲突，参见上期 Envoy AI Gateway v0.6 "filterConfig 弃用"教训。

## 七、给生产 SRE 的三条硬约束

1. **32B + bursty 流量必须配 warm pool**：HPA max replicas 提到 12+1（1 个常驻 warm），接受空闲成本换 P99 SLA。100 s 冷启动是不可绕过的物理上限。
2. **Client SDK 必须禁掉默认 retry**（OpenAI/Anthropic SDK `max_retries=2` 默认值）— 35% 错误率在"客户端无脑重试"下会变成 200% 等效请求，把可用副本打挂。
3. **监控必须看 `wva_desired_replicas` 而非 HPA 实际 replicas**：HPA 默认 240 s scale-down stabilization，WVA 早已说要降副本但 HPA 还没执行，这段"假性扩容"是真实成本黑洞。

## 八、本期不做

- 不展开 vLLM 0.22.1 内部变化（与 llm-d 0.7.0 锁的 0.19.1 落后三个版本，生产上不跟）；
- 不展开 Latency Predictor 训练侧细节（要等下个版本端到端 P99 对比数据）；
- 不评估 GPU provider（GB200 / TPU / XPU / HPU）横向比较 — llm-d v0.7.0 出了 image variant，但实测数据还没看到。

## 引用与数据来源

- llm-d v0.7.0 release：<https://github.com/llm-d/llm-d/releases/tag/v0.7.0>
- llm-d#1586「Add WVA benchmark data」：<https://github.com/llm-d/llm-d/pull/1586>
- WVA Benchmark README：<https://github.com/llm-d/llm-d/blob/main/guides/workload-autoscaling/README.wva.md>
- llm-d#1688「migrate precise-prefix-cache-scorer」：<https://github.com/llm-d/llm-d/pull/1688>
- llm-d#1655「Prometheus Adapter deprecation note」：<https://github.com/llm-d/llm-d/pull/1655>
- llm-d#1700「TPU benchmark test」：<https://github.com/llm-d/llm-d/pull/1700>
- GIE v1.5.0 release：<https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/tag/v1.5.0>
- GIE Pluggable Parser PR #2359：<https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2359>
- GIE Latency Predictor PR #2432 / #2473：<https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2432> · <https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2473>
- GIE BBR body PR #2442：<https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2442>
- GIE 插件镜像响应 PR #2369：<https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2369>
- vLLM v0.22.1：<https://github.com/vllm-project/vllm/releases/tag/v0.22.1>
- 上期（06-10）Envoy AI Gateway v0.6 基准：<https://github.com/happysunxf/aigw/blob/main/reports/2026-06-06-0610-aigw-arch-benchmark-r5.md>
