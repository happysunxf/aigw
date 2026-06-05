# AI 网关 · 架构对比 / 性能基准 第 5 期

- 报告生成时间：2026-06-06 06:10（本地时）
- 主题：架构对比 / 性能基准
- 本期焦点：Envoy AI Gateway v0.6 控制面 2,000 路由基准 + 走向 v1.0 GA 的工程取舍
- 上期衔接：2026-06-06 05:30「可观测 · OpenTelemetry gen-ai semconv」对 LiteLLM v1.88-rc.1 的 typed semconv 落地做了展开，本期把同一份 v1.88-rc.1 放在跨网关架构视角里再过一遍，并把 Envoy 端的"配置规模"侧基准补齐。

## 一、为什么这一期盯 Envoy AI Gateway

过去 24 小时最值得写的一件事是 Envoy 社区终于给 Envoy AI Gateway 出了一份正经的"配置规模"基准 — 社区博客《Benchmarking Envoy AI Gateway Control Plane Scaling》（2026-02-23，作者 Hrushikesh Patil）。它不像以前的 throughput / latency 那种偏数据面数字，而是回答一个更工程化的问题：**一台 Gateway 实例能稳定地持有多少 AIGatewayRoute 资源，配置下发链路是不是瓶颈**。这个问题在 LiteLLM / Portkey 这种 Python 主控的网关里基本不存在（它们按 key 维度管理，几乎不在 K8s 控制面建 CRD），但在 Envoy AI Gateway / Higress 这种以 K8s CRD 为 source-of-truth 的网关里就是决定"能不能上生产"的一票否决。

作者把 2,000 条 AIGatewayRoute 灌进集群、用 mock cassette server 做后端、逐条发推理请求验证可达；过程中遇到一个真实的工程阻塞：xDS 配置 payload 涨到 4MB 之上，撞了 gRPC 默认消息大小上限，需要把扩展服务和 EG 的配置都调到 25Mi 才能继续。这个数字是这次基准里**最有传播价值**的"调参点" — 任何在生产上想跑上千条 AIGatewayRoute 的运维，第一件事就是把 extproc 的 `maxRecvMsgSize` 和 EG 的 `extensionManager.maxMessageSize` 配对调起来。

## 二、Envoy AI Gateway 控制面 2,000 路由基准要点

来自博客 + v0.6.0 release notes 交叉对照：

| 维度 | 数字 / 结论 | 含义 |
|---|---|---|
| 资源规模 | 2,000 × AIGatewayRoute 全量验证通过 | 当前控制面"配置规模"地板 |
| 路由就绪延迟 | 新建 route → 可服务 ~5s | 与规模无关；`filterapi.StartConfigWatcher` 默认 5s 轮询是设计选择 |
| 推理转发 | 0 失败 | 配置 watcher 拾取后即转发，无额外开销 |
| CPU（控制器） | 注入阶段线性爬升，完成后回落 | xDS translation 的瞬时成本 |
| 内存（控制器 + proxy） | 线性增长并保留在高位 | 必须主动持有 2,000 条 xDS 配置以服务流量 |
| gRPC 调参 | 4MB → 25MB（双向） | 唯一需要做的人为调参 |
| 隐藏地雷 | etcd 单对象 ~1MB 硬上限 | `headerMutation` 等会膨胀 per-route config，需预估 |
| 不测项 | `headerMutation` 开启后的体积 | 博客明确标注"off"作为基线 |

把这条线和近 30 天其他网关放在一张表里看，差异化就出来了：

| 网关 | "配置规模"瓶颈位置 | 是否需要 etcd 单对象调参 | 默认轮询周期 |
|---|---|---|---|
| Envoy AI Gateway v0.6 | xDS gRPC msg size + etcd 1MB | 是（两侧调 25MB） | 5s |
| Higress v2.2.2 | Envoy filter config；WASM 插件配置进 pod | 取决于 secret 路径 | n/a（push-based） |
| LiteLLM v1.88-rc.1 | 无 K8s CRD 路径，按 DB 配置 | 否 | n/a |
| Portkey v1.15.2 | 同样无 K8s CRD 路径 | 否 | n/a |

这张表给架构选型的人一个明确信号：**当 LLM 路由规则需要"被 K8s/gitops 看到 / 审计"时，Envoy AI Gateway 路径的"配置规模"上限是真实的工程指标，不能假装没看见**。

## 三、跨网关架构对比：v0.6 vs v2.2.2 vs v1.88-rc.1

### 1. 控制面路径

- **Envoy AI Gateway v0.6**：CRD（`AIGatewayRoute` / `AIServiceBackend` / `BackendSecurityPolicy` / `MCPRoute` / `GatewayConfig`）全部升到 `v1beta1` — 这是 v1.0 GA 前的最后一个稳定 API。`filterConfig` 字段在 v0.5 弃用、在 v0.6 删除，所有外部处理器配置都迁到 `GatewayConfig` 资源（`aigateway.envoyproxy.io/gateway-config` annotation 引用）。这是个干净的拆家：路由层不再混着 extproc 资源声明。
- **Higress v2.2.2**：Higress 不走 K8s CRD 主导，配置进 Envoy 集群内，但**本周入了几个对架构有长远影响的点**：（a）`modelToHeader`（默认 `x-higress-llm-model-final`）把"newModel 解析结果"同步到 header，并配合 `DisableReroute` 防止 routing 冲突 — 这等于把"模型名 ↔ header ↔ 限流/计量"三者显式串起来；（b）Bedrock `/v1/messages` 改成**直连原生 Mantle Anthropic Messages API**，不再 OpenAI→Converse 二次转换；（c）nginx-rewrite 兼容插件，避开 CVE-2026-42945 堆溢出，把"从 Nginx 迁过来"的安全风险收口。
- **LiteLLM v1.88-rc.1**：纯 Python 控制面，但 v1.88-rc.1 这一刀切到可观测性：typed semconv OTel 落地（`feat(otel): typed semconv-aligned OpenTelemetry instrumentation`，2026-05-30 合并到 rc.1）。所有改动默认**关闭**，靠 `LITELLM_OTEL_V2` 开关；它把 SERVER / INTERNAL / CLIENT 三层 span 的 parent 关系在代码里**显式锚定**到 request root span（`set_request_root_span` 一次性捕获、随后 `resolve_request_span_context` 读出来），而不是用纯 ambient 模式 — 解决的是"auth 阶段活 span 把 LLM span 错挂到 auth 下"这种真出过事故的 parent 错乱。v1.88-rc.2 / rc.3 紧跟着的修复也都在这层（session-token 预算豁免、key 生成硬化、passthrough span 接到 SERVER root）。

### 2. 数据面路径

- **Envoy AI Gateway**：依然是 EG 1.7 基线（v0.6 跑的是 EG 1.7 + Envoy 1.37 + Go 1.26.2），v1.0 GA 锁定 EG 1.8 升级。extproc 在 v0.6 仍是**静态**部署，没切到 dynamic modules（road-to-ga 跟踪里 `Migrate extproc to dynamic modules` 仍是 open）。
- **Higress**：Higress 走的是 Envoy + WASM 双轨（`WasmPlugin` 体系）。这次 `modelToHeader` 的实现是把"路由前改写"放到 WASM 插件的 on-headers 阶段、用 `DisableReroute` 防止再走一遍路由 — 这其实是把"请求改写"的责任从 Lua 脚本搬到了 WASM 沙箱里，符合 Higress 长期主线（"所有用户可写逻辑进 WASM"）。
- **LiteLLM**：Python + Rust core 双轨。这次 v1.88-rc.1 的 OTel 改造**没动** Rust 核心，OTel 全部在 Python proxy 层通过 `CustomLogger` adapter 注入 — 这跟 Higress / Envoy 路径比是个"应用层 OTel"而不是"数据面 OTel"。代价是 span 完整度受限于 Python logger 回调点，但好处是改动面小、回滚成本极低（一个 env var 就能切回 v1 行为）。

### 3. 安全 / 凭据

- **Envoy AI Gateway v0.6**：入 `BackendSecurityPolicy` v1beta1（一直在），加 AWS Bedrock 的 GKE Workload Identity（ADC 链路），并加了 request/response body redaction — 这在 MCP 走"工具调用 body 可见"路径时是必须项。
- **Higress v2.2.2**：nginx-rewrite 走 WASM 沙箱明确收口 CVE-2026-42945 堆溢出；这是"安全债转架构债"的典型例子。
- **LiteLLM v1.88-rc.1**：v1.88-rc.1/rc.2/rc.3 三个 rc 的修复集中在 `GHSA-q775` — session-token 豁免硬化、default_key_generate_params 边界；PR 节奏显示社区把"key 生成"作为重点加固面。

## 四、Envoy AI Gateway v1.0 GA 路线图（2026-06-30 目标）

依据 tracking issue #2083「Road to v1.0 GA (June 2026)」：

| 决策 | 锁定结论 |
|---|---|
| CRD 版本 | v1beta1（v1 推到 post-GA） |
| MCPRoute 稳定标签 | Stable（v0.6 升 v1beta1） |
| 目标 EG 版本 | 1.8 |
| `aigw` CLI 范围 | GA surface |
| Upstream Envoy MCP（envoy#39174） | **不在 v1.0 依赖里** |
| Release Manager | 仍 open |

里程碑：

- v0.6.0（2026-04-25，已发）✅
- v0.7.0（2026-05-22，QuotaPolicy v1beta1 + 存储迁移 + benchmarks）— **进行中**
- v1.0.0-rc1（2026-06-12，main 分支冻结、RC cycle）
- v1.0.0（2026-06-30 GA）🎯

值得运维注意的 4 件事：

1. **v1.0.0-rc1 之前有一周分支冻结窗口**（6/12 起），要赶 v1.0.0-rc.1 的兼容性 PR 必须在那之前合；
2. **v0.6 已删字段**：`AIGatewayRoute.spec.filterConfig` 已删除、`VersionedAPISchema.version` 不再当 endpoint prefix 用 — 升 v0.6 的用户必须先做迁移；
3. **extproc 暂不上 dynamic modules**，意味着 v1.0 时期 extproc 升级仍要重启 pod — 这是 GA 前的"已知不退"清单；
4. **v0.7 的 QuotaPolicy v1beta1** 是 v1.0 前的最后一块"业务策略"拼图，目前还没看到生产侧 SLA 数据，本期不展开。

## 五、给架构选型者的三点结论

1. **以 K8s CRD 为路由 source-of-truth 的网关，"配置规模"是个独立的工程指标**，不能被"延迟多少 ms"的吞吐基准替代。Envoy AI Gateway 给的 2,000 路线 + 25MB gRPC 调参是当前唯一公开的工程基线，要在这个量级以下运行就放心用 v0.6，往上就先小规模 POC。
2. **可观测性是 2026 上半年的"主战场"**。Envoy 走 EG 1.8 + OpenInference 集成（社区博客有专文），LiteLLM 走 typed semconv OTel（v1.88-rc.1），Higress 走自建 span header。差异点：Envoy / LiteLLM 的 OTel 都能在 Jaeger / Tempo 里直接看到 gen-ai 语义属性，Higress 路径需要自建 span-name 约定。
3. **安全加固的"高 ROI 地带"在 key/凭据管理面**。LiteLLM v1.88 三个 rc 集中在 `GHSA-q775` 修复，Higress 把 nginx-rewrite 收口到 WASM 沙箱，Envoy 加了 body redaction — 这三件事放在一起说明"网关凭据 + 改写逻辑"是行业共识的高危区。

## 六、本期不做

- 暂不展开 QuotaPolicy v1beta1 细节（要等 v0.7 GA 后才有端到端的 spec 文档）；
- 暂不展开 `aigw` CLI 的 subcommand 列表（v0.6 已经把它升为 GA surface，但 product-team 文档要 6/12 RC 一起发）；
- 暂不评估 GPU provider（如 vLLM、OpenLLMetry）的多模态路由路径。

## 引用与数据来源

- Envoy AI Gateway 官方博客「Benchmarking Envoy AI Gateway Control Plane Scaling」：<https://aigateway.envoyproxy.io/blog/benchmarking-control-plane-scaling>
- Envoy AI Gateway v0.6.0 release notes：<https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0>
- Envoy AI Gateway 官方文档 v0.6：<https://aigateway.envoyproxy.io/docs/0.6/>
- Tracking: Road to v1.0 GA (June 2026) — issue #2083：<https://github.com/envoyproxy/ai-gateway/issues/2083>
- LiteLLM v1.88.0-rc.1 release notes：<https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.1>
- LiteLLM v1.88.0-rc.2 release notes：<https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.2>
- LiteLLM v1.88.0-rc.3 release notes：<https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3>
- LiteLLM v1.87.1 release notes：<https://github.com/BerriAI/litellm/releases/tag/v1.87.1>
- LiteLLM feat(otel): typed semconv-aligned OpenTelemetry instrumentation — PR #28909：<https://github.com/BerriAI/litellm/pull/28909>
- Higress v2.2.2 release notes：<https://github.com/higress-group/higress/releases/tag/v2.2.2>
- Portkey Gateway releases：<https://github.com/Portkey-AI/gateway/releases>
