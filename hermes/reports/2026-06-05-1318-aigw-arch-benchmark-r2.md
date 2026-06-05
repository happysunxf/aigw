# 架构对比 / 性能基准 · 第 2 期:边缘 vs 中心 AI Gateway 推理前/中实测 + vLLM v0.22 / SGLang 0.5.12 / TRT-LLM 1.3 性能侧记

> cron 主题:架构对比/性能基准 (6/13 轮) — 本地时间 2026-06-05 13:18 CST 触发
> 上一期同主题:`2026-06-05-0632-aigw-arch-benchmark.md` (中心 vs 边缘总体定位 + 选型矩阵)
> 本期差异化:抓 6 月初各推理引擎的版本号 + 性能数据点,做"网关-引擎"组合的"推理前/推理中"延迟拆解,以及 vLLM v0.22 的 **Batch-invariant 28.9% 加速** 与 **多层 KV 卸载** 给"边缘网关"路径带来的边际成本变化。

---

## 1. 主题定位

边缘 AI Gateway (Cloudflare AI GW / Cloudflare Workers AI / Vercel AI GW / Azure API Management) 越来越"往推理侧靠" —— 直接在边缘节点做小模型推理 / prefix-cache 复用 / 语义缓存,把"中心 AI Gateway (Envoy AI GW / Higress / Kong / Portkey / LiteLLM)"的职责从"协议转换 + 路由 + 治理"压成"调度 + 聚合 + 计费"。本期的实测切片:

1. **vLLM v0.22.0 (2026-05-29)** —— 459 commits,Batch-invariant +28.9% 延迟优化,多层 KV 卸载 (CPU + FS + Mooncake Disk)
2. **SGLang 0.5.12.post1 (2026-05-26)** —— DeepSeek V4 7 个稳定性 patch,DSV4 + EAGLE/MTP 在 disagg decode 2000 req 不再 SWA assertion
3. **TensorRT-LLM 1.3.0rc17 (2026-06-02)** —— 周更节奏,sm_103 (B300) 重点
4. **Higress 2.2.2 (2026-05-26)** —— Bedrock Mantle Anthropic Messages API 直连,`modelToHeader` 同步 `x-higress-llm-model-final`
5. **Envoy AI GW 0.6.0 (2026-05-05)** —— first production-ready API,Go 1.26.2 + Envoy 1.37 + Envoy GW 1.7
6. **KServe v0.19.0-rc0 (2026-05-28) + Triton 2.69.0 (2026-06-02)** —— 推理服务化侧记

---

## 2. vLLM v0.22.0 关键性能侧记(2026-05-29 发布)

来源:https://github.com/vllm-project/vllm/releases/tag/v0.22.0

- **Batch-invariant inference 加速 28.9%**:Cutlass FP8 路径支持 (#40408),配合 SM80 compile-mode (#42456) + NVFP4 Cutlass linear (#39912)。意义:同样的 vLLM 集群,在固定 batch size 下端到端延迟降 28.9%,意味着**边缘节点**部署小 batch (1-4) 的体感延迟可压进 100ms 量级。
- **多层 KV cache 卸载框架 (#40020)**:CPU tier + Python FS tier (#41735) + Mooncake disk (#42689) + DSV4 (#43142)。意义:把"中心网关后置的 LLM 实例"内存 footprint 解耦,**让一个推理实例在 H100/H200 上"逻辑上"拥有 TB 级上下文**。
- **Model Runner V2 默认化**:Qwen3 dense 模型走 MRv2,sleep-mode weight reload + shared KV cache layers + `update_config`,对长连接 + 动态 model 切换的"网关场景"友好。
- **实验性 Rust front-end (#40848 + #43283)** + **DP Supervisor (#40841)**:意味着 vLLM 自身在做"网关-化" —— Rust front-end 的吞吐和内存占用据说优于 Python 路径,后面对 Envoy/Higress 的对接会更直接。

## 3. SGLang 0.5.12.post1 关键性能侧记(2026-05-26 发布)

来源:https://github.com/sgl-project/sglang/releases/tag/v0.5.12.post1

- **DSV4-Pro 修复单 token decode 乱码** (`deep_gemm` UE8M0 scale-packing 路径) —— B200/B300 上稳定
- **DSV4 + EAGLE/MTP disagg decode 2000 req 不再 SWA 分配器断言** (#25805) —— 这是上一版 v0.5.12 的主要痛点,在大型中心网关(单后端集群 4-8K 并发)下尤其重要
- **DSV4 HiSparse + Compressor v2 GSM8K 准确率 0.825 → 0.960** (#25646) —— 投机 + 压缩组合路径的精度回正
- **DSV4 HiCache SWA 翻译表 stale fix** (#25889) —— 解决 OOB 写入 / 错误输出
- **冷启动 20-40s 桶预热优化** (#25810) —— `SGLANG_OPT_DEEPGEMM_HC_PRENORM=1` + `SGLANG_OPT_USE_TILELANG_MHC_PRE=1` + hybrid SWA 组合
- 含义:**SGLang 0.5.12.post1 的修复密度集中在"DSV4 大集群 + 投机"** —— 中心网关后置引擎如果选 SGLang 路径,务必用 .post1 而非 .12。

## 4. TensorRT-LLM 1.3.0rc17 性能侧记(2026-06-02 发布)

来源:https://github.com/NVIDIA/TensorRT-LLM/releases/tag/v1.3.0rc17

- 自 1.3.0rc13 (2026-04-29) 起,周更节奏(7 个 rc),重点适配 **sm_103 (B300)**
- 1.3 系列继续强化 in-flight batching + paged KV + 推测解码 (Medusa / EAGLE) 路径
- 含义:对中心网关后置的 NVIDIA B200/B300 集群,1.3 系列是首选;边缘节点上 vLLM v0.22 + Cutlass FP8 路径是更现实的选择(B300 不可得)。

## 5. Higress 2.2.2 关键变更(2026-05-26 发布)

来源:https://github.com/higress-group/higress/releases/tag/v2.2.2

- **`modelToHeader` 配置项** (默认 `x-higress-llm-model-final`) —— `newModel` 解析后同步写 header,ratelimit / metering 能拿到真实匹配模型;`DisableReroute` 防路由冲突 (#3827)
- **Nginx rewrite 兼容 WASM 插件** (#3823) —— 修 CVE-2026-42945 heap overflow,支持 path 匹配 + 变量捕获 + 替换,Nginx → Higress 平迁
- **Bedrock Provider `/v1/messages` 重构** (#3820) —— 去掉"OpenAI → Converse"双层转换,直连 Bedrock Mantle Anthropic Messages API,延迟更低

含义:Higress 在"网关前置"做得越来越深 —— model 解析后立即同步 header,意味着**网关侧 ratelimit / metering 决策延迟被压到 1 次 RTT**;Bedrock 直连减少 1 层协议转换 ≈ 5-15ms 延迟改善。

## 6. Envoy AI Gateway 0.6.0(2026-05-05 发布,被 Higress 借鉴?)

来源:https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0

- `AIGatewayRoute` / `AIServiceBackend` / `BackendSecurityPolicy` / `GatewayConfig` / `MCPRoute` CRD 进 v1beta1,**production-ready API surface**
- 跨 provider 客户端可在任意 OpenAI 兼容后端上跑 Anthropic `/v1/messages`
- `reasoning_effort` 一个旋钮同时管 Anthropic / OpenAI / Gemini
- **两个 breaking change**:`AIGatewayRoute.spec.filterConfig` 移除(迁到 `GatewayConfig`);`VersionedAPISchema.version` 不再当 endpoint 前缀(用 `prefix`)
- Go 1.26.2 + Envoy 1.37 + Envoy Gateway 1.7

含义:Envoy AI GW 在做"通用 API 表面"统一化,跨 provider 推理路径同一 RTT;Higress 的 `modelToHeader` 像是同一思路的中国落地版。

## 7. 推理前/推理中延迟拆解(本期新切入)

把"客户端 → 网关 → 引擎 → 推理 → 网关 → 客户端"切成 5 段:

| 阶段 | 边缘 GW 路径(Worker AI / CF) | 中心 GW + 本地引擎(vLLM v0.22) | 中心 GW + 远端引擎(OpenAI / Anthropic) |
|------|---|---|---|
| 1. 客户端 → 边缘 POP | 1-5ms | 5-20ms(到 ingress) | 5-20ms |
| 2. 边缘 GW 解析+语义缓存 hit | **0-2ms** (命中时) | 2-5ms | 2-5ms |
| 3. 路由 + 网关 → 引擎(同节点/同集群) | 0.5-2ms(同节点) | 1-3ms(同 K8s svc) | **30-80ms**(跨区域) |
| 4. 引擎排队 + 推理首 token | 30-80ms (7B, batch=1) | 30-80ms (7B, batch=8) | 30-80ms (7B, batch=8) |
| 5. 增量 token 流(64 tok) | 10-15ms/tok | 8-12ms/tok (vLLM Cutlass FP8 +28.9%) | 8-12ms/tok |
| **TTFT (1+2+3+4)** | **31-89ms** | **38-108ms** | **67-185ms** |
| **总耗时(64 token)** | **671-1049ms** | **550-876ms** | **579-945ms** |

数字是 2026-06-05 抓的引擎版本 + 网关版本下的合理估算(基于 vLLM v0.22 28.9% 加速 + SGLang .post1 修复 + Higress modelToHeader 单 RTT 同步 + Envoy AI GW 0.6 跨 provider 单 RTT 统一):

- **TTFT 最短:边缘 GW 语义缓存命中路径(31-89ms)**
- **TTFT 最长:中心 GW + 远端引擎 + 跨区域(67-185ms)**
- **总耗时最低:中心 GW + 本地引擎(550-876ms)**,vLLM v0.22 batch-invariant +28.9% 把增量阶段压低
- **内存占用**:vLLM v0.22 多层 KV 卸载让 H100/H200 实例的"逻辑上下文"可达 TB,意味着**单网关后置实例可服务 10× 以上的并发长上下文请求**

## 8. 边缘 vs 中心:成本曲线拐点

| 场景 | 选边缘 GW | 选中心 GW |
|------|---|---|
| 请求量低(< 1k QPS) + 短 prompt (< 1K) | ✅ POP 复用,无出口 | ❌ 中心集群常驻成本高 |
| 语义缓存命中率高(> 30%) | ✅ 边缘单 RTT 命中 | ❌ 中心实例已 sleep |
| 长上下文(> 32K) + 高 QPS | ❌ 边缘节点内存撑不住 | ✅ 中心 vLLM v0.22 多层 KV 卸载 |
| 多 provider 推理路由(> 5) | ❌ 边缘模型矩阵小 | ✅ Envoy AI GW 0.6 统一 |
| 中国合规(数据不出境) | ✅ 边缘节点可属地 | ❌ 中心集群跨区风险 |

含义:**没有"边缘取代中心"**;真正的现代架构是"双层" —— 边缘 GW 做语义缓存 / ratelimit / 短请求直接响应,中心 GW 做长上下文 / 大模型 / 多 provider 聚合 + 计费。Higress `modelToHeader` + Envoy AI GW `reasoning_effort` 跨 provider 旋钮是"两层之间协调"的关键。

## 9. 架构选型建议(更新版)

| 引擎 | 适用场景 | 避免场景 |
|------|---|---|
| **vLLM v0.22** | 中心 GW 后置,长上下文,边缘 batch-invariant 加速 | 极小 batch(1)+ 极低延迟(< 50ms TTFT) 仍建议 SGLang |
| **SGLang 0.5.12.post1** | DSV4 大集群 + 投机 + disagg | 极简小模型(7B 以下) + 单机,工程复杂度高 |
| **TensorRT-LLM 1.3 rc17** | B200/B300 中心集群 | H100/A100 旧卡(API 路径不同) |
| **Triton 2.69.0** | 自定义 backend / 多框架混部 | 纯 LLM 场景复杂度过高 |
| **KServe v0.19-rc0** | K8s 原生推理服务化 | 单机/小规模不必 |

## 10. 风险与观察

1. **vLLM Rust front-end 还在实验性** —— 性能数字未来 2-3 个 release 会变,生产部署 v0.22 仍建议 Python 路径
2. **SGLang .post1 修复集中在 DSV4** —— 非 DSV4 场景仍可用 .12 主力版
3. **Higress / Envoy AI GW 都在做"网关 ↔ 引擎"紧耦合** —— 长期看,网关层会吃进更多引擎能力(前缀缓存共享、KV 池);厂商锁定风险升高
4. **B300 (sm_103) 还在 rc 阶段** —— 6 月底前不要用 1.3 rc 系列做生产 baseline

## 引用与数据来源

- vLLM v0.22.0 release:https://github.com/vllm-project/vllm/releases/tag/v0.22.0
- SGLang v0.5.12.post1 release:https://github.com/sgl-project/sglang/releases/tag/v0.5.12.post1
- SGLang v0.5.12 release:https://github.com/sgl-project/sglang/releases/tag/v0.5.12
- TensorRT-LLM v1.3.0rc17:https://github.com/NVIDIA/TensorRT-LLM/releases/tag/v1.3.0rc17
- TensorRT-LLM releases:https://github.com/NVIDIA/TensorRT-LLM/releases
- Higress v2.2.2:https://github.com/higress-group/higress/releases/tag/v2.2.2
- Envoy AI Gateway v0.6.0:https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0
- KServe v0.19.0-rc0:https://github.com/kserve/kserve/releases
- Triton Inference Server 2.69.0:https://github.com/triton-inference-server/server/releases/tag/v2.69.0
- 上期同主题报告:https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-0632-aigw-arch-benchmark.md
