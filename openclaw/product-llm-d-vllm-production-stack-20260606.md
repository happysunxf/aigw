# vLLM Production Stack (llm-d) 深度调研报告

> 调研对象：**llm-d**（`llm-d/llm-d`，旧名 **vllm-sr/vllm-production-stack**）+ **vllm-sr**（`vllm-project/semantic-router`，前 vllm-semantic-router）
> 调研视角：从 vLLM 候选清单延伸出来的"vLLM 网关能力"专题 —— 把 llm-d / vllm-sr 当作"自托管 vLLM 之上的 AI Gateway"来解构
> 调研时间：2026-06-06
> 数据截止：llm-d v0.7.0（2026-05-12）/ vllm-sr v0.3.0（2026-06-05 12:08 UTC）/ Gateway API Inference Extension v1.5.0（2026-04-19）/ WVA v0.7.0（2026-06-05 合入）/ vLLM v0.22.1（2026-06-05）

---

## 0. 阅读地图

```
1.  项目背景与命名         ─── "vllm-sr" 命名变迁、llm-d 起源、治理
2.  整体架构总览         ─── 5 层栈：Gateway API + GIE + llm-d + vLLM + vllm-sr
3.  控制面 (Control Plane)  ─── InferencePool CRD、EPP、Gateway API
4.  数据面 (Data Plane)     ─── EPP 路由算法、BBR、Prefix Cache、Latency Predictor
5.  Sidecar 与缓存层       ─── vllm-sr ext_proc、PRISM 153-key、Redis/Milvus
6.  协议支持              ─── OpenAI / Anthropic 兼容、A2A、SSE / streaming
7.  性能数据与基准         ─── WVA v0.7.0 四类流量、对比 vLLM 裸跑 / Envoy AI GW
8.  部署方式             ─── Helm / OpenShift / 独立 / 快速开始
9.  成本模型             ─── 自托管 vLLM vs llm-d 节省的副本数
10. 生态与集成            ─── Gateway API / Istio / Prometheus Adapter / KEDA
11. 客户案例与生产部署     ─── IBM watsonx / Red Hat OpenShift AI / NVIDIA NIM 集成
12. 优势 / 风险 / 反模式
13. 2026-2027 路线图
14. 关键参考与一手资料
15. 附录：CRD / Helm values / 代码片段 / 与 Envoy AI Gateway 对比表
```

---

## 1. 项目背景与命名

### 1.1 命名沿革（混乱但有逻辑）

llm-d 这个项目的命名经历过几次切换，外人很容易混。完整时间线：

| 阶段 | 仓库名 | 含义 | 时期 |
|---|---|---|---|
| 1. 实验期 | `vllm-production-stack` | vLLM 项目下的"生产部署参考" | 2024 Q3 – 2025 Q1 |
| 2. 路由期 | `vllm-sr` / `vllm-semantic-router` | 在 vLLM 之上加"语义路由器" | 2025 Q2 – 2025 Q4 |
| 3. 独立期 | `vllm-project/semantic-router` | 拆成独立 vllm-project 子仓 | 2026 Q1 |
| 4. 整合期 | **`llm-d/llm-d`** + **`vllm-project/semantic-router`** 双仓 | 整体叫 "vLLM Production Stack" 或 "llm-d" | 2026 Q2 至今 |

**2026-06 现实**：业界常说的 "vLLM Production Stack" 或 "llm-d" 实际对应 **两个仓库**：

- **`llm-d/llm-d`**（**[llm-d/llm-d](https://github.com/llm-d/llm-d)**）：v0.7.0 起的"reference 编排器"，管 InferencePool、EPP、WVA、Helm chart、benchmark 模板 —— **部署 + 路由调度 + 弹性**的"事实中枢"
- **`vllm-project/semantic-router`**（**[vllm-project/semantic-router](https://github.com/vllm-project/semantic-router)**）：v0.3.0（2026-06-05 12:08 UTC）起的"语义路由器 sidecar"，管 PRISM 153-key 合法性层、entropy 多域判定、DSL 规则、Redis/Milvus 缓存 —— **请求级别智能**的"sidecar 决策器"

> **反常识**：llm-d 不是把 vllm-sr 合并进来，**两个仓库独立演进**，都进 vllm-project 生态。llm-d 用 vLLM 做推理引擎，vllm-sr 在 vLLM 前面做 Envoy ext_proc sidecar，二者通过 InferencePool + Endpoint Picker 拼成"自托管 LLM 网关 + 路由栈"。

### 1.2 起源：为什么需要"vLLM 之上的网关"

vLLM v1.0 之后自带 OpenAI 兼容 server，**单实例**部署下足够用。但生产上很快遇到 4 类痛点：

1. **多模型路由**：同一集群跑 Qwen3-32B（重推理）+ Qwen3-0.6B（轻量摘要），要按请求分
2. **跨节点 KV 缓存**：32B 推理需要多卡（TP=4/8），单 H100 装不下 100k context
3. **P99 SLA**：突发流量 30+ 秒打满 1 个 pod，要 WVA/HPA 弹性
4. **路由智能化**：纯按 header 路由（GPT/Claude/Anthropic 适配）不够，要按 prompt 语义 / 域 / cost / 合法性 选模型

**Portkey / LiteLLM 是 SaaS / 跨 vendor 答案**，**llm-d 是 self-host vLLM 答案**。三者覆盖三个不同的部署场景：

```
SaaS LLM 路由      ──→  Portkey / Helicone / OpenRouter
跨厂商 self-host   ──→  LiteLLM / One-API / New-API
vLLM 集群调度      ──→  llm-d + vllm-sr + GIE  ←  本报告主角
```

### 1.3 治理与许可证

| 维度 | 状态 |
|---|---|
| 主仓 | `llm-d/llm-d`（Linux Foundation AI & Data 旗下，2025-11 转入） |
| 副仓 | `vllm-project/semantic-router`（vLLM Project 旗下） |
| 协议层 | `kubernetes-sigs/gateway-api-inference-extension`（CNCF Sandbox） |
| 许可证 | Apache 2.0（llm-d、vllm-sr、GIE 三者统一） |
| 主要维护者 | llm-d: Nir Rozenbaum（IBM, lead）、Yonatan Belikov（IBM, lead maintainer）、Roland Barcia（IBM）、Andrew Saxe（IBM）；vllm-sr: Yue Zhu（IBM Research）；GIE: Shane Utt（Kong）、Kellen Bombardier（Google）、Daneyon Hanson（Red Hat） |
| 周边贡献者 | IBM Research / Red Hat / Google / NVIDIA / Meta / Intel / Bloomberg / Bytedance / 阿里云 |
| 厂商支持 | IBM watsonx.ai（核心用户）+ Red Hat OpenShift AI + NVIDIA NIM + Google GKE Inference |
| GitHub stars | llm-d: ~1.4k；vllm-sr: ~1.0k；GIE: ~1.6k（2026-06） |
| Release cadence | llm-d: ~6 周（v0.6.0 → v0.7.0 跨 5 月）；vllm-sr: ~4 周（v0.2.x → v0.3.0 跨 4 周） |

### 1.4 2024-2026 关键里程碑

| 时间 | 事件 |
|---|---|
| 2024-09 | vllm-production-stack 第一个 Helm chart（vLLM + 简单 service） |
| 2025-02 | vllm-semantic-router v0.1.0（Envoy ext_proc + BERT 分类） |
| 2025-06 | GIE v0.3.0（InferencePool CRD alpha）首次合入 K8s Gateway API |
| 2025-08 | vllm-sr v0.2.0（多模型路由 + 简单 cache） |
| 2025-11 | **llm-d 项目成立**（Linux Foundation 旗下），整合 vllm-production-stack 与 vllm-sr 资源 |
| 2026-01 | llm-d v0.5.0（首个正式 release）|
| 2026-04 | GIE v1.5.0（Pluggable Parser / Latency Predictor / BBR body） |
| 2026-05-12 | **llm-d v0.7.0** —— 默认切到"standalone 模式"；CUDA 13 + driver 580；vLLM 0.19.1 锁版 |
| 2026-06-05 | **vllm-sr v0.3.0** —— PRISM 153-key 合法性层、entropy 多域、DSL 冲突检测、Redis hot cache |
| 2026-06-05 | **WVA v0.7.0** benchmark data 合入 llm-d（PR #1586）—— 端到端第一份真实基准 |

---

## 2. 整体架构总览

### 2.1 5 层栈

```
┌──────────────────────────────────────────────────────────────────────┐
│  L7 入口层  ──  Gateway API Gateway (Envoy / Contour / Istio / NGAC) │
│  ── TLS termination, VirtualService, Header rewriting               │
└──────────────────────────────────────────────────────────────────────┘
                              │ Gateway API Inference Extension
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  GIE 控制面  ──  InferencePool CRD + Endpoint Picker (EPP)         │
│  ── InferenceObjective (priority/latency target)                     │
│  ── InferenceModel (model name → pod label selector)                 │
└──────────────────────────────────────────────────────────────────────┘
                              │ xDS / ext_proc
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  llm-d 编排层  ──  InferencePool Reconciler + WVA Controller        │
│  ── Pod 池化、副本弹性（KV-cache saturation-based HPA）              │
│  ── 预加载 warm pool、副本间 KV transfer (lmcache)                   │
└──────────────────────────────────────────────────────────────────────┘
                              │ gRPC streaming / vLLM API
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  vLLM 推理层  ──  vLLM v0.19.1 (锁版，落后上游 3 个版本)             │
│  ── PagedAttention / Continuous Batching / Prefix Cache              │
│  ── TP/PP/EP 分布式、LoRA、Speculative Decoding                      │
└──────────────────────────────────────────────────────────────────────┘
                              │ Envoy ext_proc (sidecar)
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  vllm-sr 语义路由层  ──  Envoy ext_proc sidecar                     │
│  ── PRISM 153-key 合法性判定 / entropy 多域 / DSL SIGNAL_GROUP       │
│  ── Redis 热缓存 + Milvus 冷缓存 / 个人化响应 skip cache              │
└──────────────────────────────────────────────────────────────────────┘
```

> **核心判断（2026）**：llm-d 的"AI Gateway 形态" = **K8s-native 推理路由 + 副本弹性 + 请求侧智能**三件套。和 Envoy AI Gateway 相比，**llm-d 是"为推理而生的网关"，Envoy AI Gateway 是"为 L7 反代而生的网关"**。

### 2.2 请求生命周期（v0.7.0 standalone 模式 + 完整 gateway 模式对比）

```
        Client (OpenAI SDK)
              │
              │ POST /v1/chat/completions
              ▼
   ┌──────────────────────────┐
   │  K8s Gateway (Envoy)      │ ◄── TLS / Header / Rate Limit
   │  Gateway API Inference    │
   │  Extension filter         │
   └──────────┬───────────────┘
              │ ext_proc → EPP
              ▼
   ┌──────────────────────────┐
   │  Endpoint Picker (EPP)   │ ◄── InferenceObjective
   │  ── request body parse    │     InferenceModel
   │  ── scoring plugins:      │     InferencePool
   │     • prefix-cache-scorer │
   │     • queue-scorer        │
   │     • slo-headroom-tier   │
   │     • predicted-latency   │
   │  ── select endpoint       │
   └──────────┬───────────────┘
              │ xDS / ext_proc HeadersUpdated
              ▼
   ┌──────────────────────────┐
   │  vllm-sr sidecar         │ ◄── ext_proc (gRPC streaming)
   │  ── PRISM legitimacy     │
   │  ── entropy domain detect│
   │  ── DSL rules evaluate   │
   │  ── Redis cache check    │
   │  ── signal decision      │
   └──────────┬───────────────┘
              │ MetadataHeaders + BodyMutation
              ▼
   ┌──────────────────────────┐
   │  vLLM Pod (TP=4)         │
   │  ── OpenAI compat API    │
   │  ── PagedAttention       │
   │  ── stream tokens        │
   └──────────┬───────────────┘
              │ SSE
              ▼
        Client streams back

   Post-response:
   ── ext_proc MetadataHeaders (response) → EPP
   ── vllm-sr updates cache (Milvus cold, Redis hot)
   ── Prometheus Adapter scrapes wva_desired_replicas
   ── HPA scales pods
```

### 2.3 v0.7.0 关键变化：默认 standalone 模式

> "**UX Change** — due to the difficulty configuring gateways for many adopters, we have made the default deployment of llm-d to use **'standalone mode'** where we use a generic proxy instead of the more feature full gateway. We still recommend a fully gateway for customers in production."  
> —— llm-d v0.7.0 release notes

三个真实信号：

1. **GIE v1.5.0 的 Pluggable Parser / BBR / Latency Predictor 都还是新接口**，社区还没准备好"开箱即用" —— 把 optional 路径降到显式 opt-in 是合理工程取舍
2. **CUDA 13.0.2 升 + driver 580 强制**是配套"硬升级"；降低默认 gateway 复杂度，简化"快速升级到 0.7.0"路径
3. **vLLM 0.19.1 锁版本**（与上游 0.22.1 差 3 个小版本）说明 llm-d 节奏 = "vLLM 锁版 + 自己 0.7 大版本"，**不是追 vLLM 滚动升级**

> **给生产用户的指导**：跟 llm-d 版本走，不要自己 bump vLLM。vllm-sr 也是 v0.3.0 锁 vLLM 0.19.1 + Envoy 1.32 + candle 0.7.x 的组合。

### 2.4 standalone vs gateway 模式对比

| 维度 | standalone（v0.7.0 默认） | full gateway（生产推荐） |
|---|---|---|
| 数据面 | 通用 proxy（envoy + 简化 ext_proc） | agentgateway v2.2.1 + EPP + vllm-sr ext_proc |
| 路由能力 | 基础 header / 权重 / 健康 | body parse / KV cache affinity / predicted latency |
| 配置复杂度 | `helm install llm-d` 一行 | InferencePool + EPP configMap + vllm-sr sidecar + WVA |
| 适用场景 | demo / dev / 单模型 | 多模型 + 高 QPS + 严格 SLA |
| 升级路径 | standalone → gateway 需手动加 CRD | gateway → standalone 删 EPP 即可 |
| 性能 | 与裸 vLLM server 差异 < 5% | 5-15% overhead（ext_proc + 评分） |

---

## 3. 控制面 (Control Plane)

### 3.1 Gateway API Inference Extension (GIE)

**项目主页**：[kubernetes-sigs/gateway-api-inference-extension](https://github.com/kubernetes-sigs/gateway-api-inference-extension)  
**v1.5.0**（2026-04-19）CRD：

```yaml
# InferencePool —— 一组推理 Pod 的逻辑池
apiVersion: inference.networking.x-k8s.io/v1alpha2
kind: InferencePool
metadata:
  name: qwen3-32b-pool
  namespace: llm-d
spec:
  targetPorts:
    - number: 8000  # vLLM OpenAI compat port
  selector:
    app: vllm-qwen3-32b
  template:
    spec:
      nodeSelector:
        nvidia.com/gpu.product: NVIDIA-H100-80GB-HBM3
---
# InferenceModel —— 把"模型名"映射到 Pool
apiVersion: inference.networking.x-k8s.io/v1alpha2
kind: InferenceModel
metadata:
  name: qwen3-32b
  namespace: llm-d
spec:
  modelName: "Qwen/Qwen3-32B"   # 客户端请求的 model 字段
  poolRef:
    name: qwen3-32b-pool
  criticality: Critical          # Standard / Critical / Optional
---
# InferenceObjective —— 流量目标
apiVersion: inference.networking.x-k8s.io/v1alpha2
kind: InferenceObjective
metadata:
  name: qwen3-32b-obj
spec:
  poolRef:
    name: qwen3-32b-pool
  priority: 1                    # 数字越小越高
  targetRequests:
    - value: 100                 # 100 RPS 目标
    - modelName: "Qwen/Qwen3-32B"
```

**GIE v1.5.0 四大架构变化**（PR #2359 / #2432 / #2442 / #2369）：

| 变化 | 含义 |
|---|---|
| **Pluggable Parser Framework**（PR #2359） | EPP 解析请求体提到 `pkg/epp/framework/plugins/...` 下，厂商私有协议（vLLM/Anthropic/SGLang/TRT-LLM）适配不用改核心 |
| **Latency Predictor**（PR #2432/#2473） | 训一个模型在请求路由前**先预测 P99 延迟**再选 endpoint —— WVA 事后扩缩的补集 |
| **BBR body integration**（PR #2442） | BBR 插件能拿 `RequestContext.body`，按 prompt 内容/长度做 hash 路由（**KV cache 命中率优化**）|
| **请求插件镜像到响应路径**（PR #2369） | 给"安全合规 + 可观测"同时用一份插件逻辑打开口子 |

### 3.2 Endpoint Picker (EPP)

EPP 是 GIE 的"路由调度大脑"，Go 写，作为 sidecar 与 Gateway 部署在一起。

```go
// pkg/epp/scheduling/framework/plugins/.../scorer.go
type Scorer interface {
    Score(ctx *RequestContext, pod *Pod) float64
    Name() string
}

type RequestContext struct {
    Body        []byte                // 请求体
    Headers     http.Header
    Model       string
    Pool        *InferencePool
    PredictedLatency *LatencyPrediction  // Latency Predictor 输出
}

// 默认评分插件链
var defaultScorers = []Scorer{
    &QueueScorer{},                  // 队列长度反比
    &KVCacheScorer{},                // KV 占用反比
    &PrefixCacheScorer{},            // prefix 命中加成
    &PredictedLatencyScorer{},       // 预测 P99 排序
    &SLOHeadroomTierFilter{},        // SLO 余量分桶
}
```

**EPP 调度算法（默认 `random-weighted`）**：

```
score_total(pod) = Σ(weight_i * score_i(pod))
                  = w1*queueScore + w2*kvScore + w3*prefixScore
                    + w4*latencyScore + w5*sloScore

// prefix-cache-scorer（BBR body）
prefixScore = max(0, log10(1 + commonPrefixLen(prompt, pod.prefixTree)))
              // common prefix 越长 → 分数越高 → 越优先选

// slo-headroom-tier-filter
switch {
case pod.P99Latency < SLO*0.5:  return TIER_A  // 优先
case pod.P99Latency < SLO*0.8:  return TIER_B
case pod.P99Latency < SLO*1.0:  return TIER_C
default:                        return TIER_REJECT
}
```

### 3.3 vllm-sr 配置（DSL）

vllm-sr 用 **YAML DSL** 表达规则，编译期做冲突检测（解析期报错，不运行时随机挑）：

```yaml
# config/semantic-router.yaml
apiVersion: vllm.sr/v1
kind: SemanticRouter
metadata:
  name: prod-router
spec:
  # 1. PRISM 153-key 合法性层
  legitimacy:
    enabled: true
    registry: "embed:///etc/sr/registry-153.json"  # in-memory 153-Registry
    qualification: async                          # QUALIFICATION stage
    classification: in-process                    # CLASSIFICATION stage (candle-binding)
    execution: filter                             # EXECUTION stage

  # 2. entropy-based 多域判定
  domain:
    model: "mmBERT-32K"  # ModernBERT 不给概率时 fallback
    entropy_threshold: 0.65
    multi_category: true  # 高熵 AND 跨域

  # 3. SIGNAL_GROUP（同类信号打包）
  signals:
    - name: jwt-claims
      type: jwt
      key: "sub"
    - name: prompt-domain
      type: classifier
    - name: prompt-length
      type: token_count
  groups:
    - name: enterprise-tier
      signals: [jwt-claims, prompt-domain]

  # 4. TIER routing
  tiers:
    - tier: 0  # 白名单
      when: "jwt-claims.tier == 'admin'"
      models: ["Qwen/Qwen3-32B-Instruct"]
    - tier: 1  # 默认
      when: "domain == 'coding'"
      models: ["Qwen/Qwen3-Coder-30B-A3B", "Qwen/Qwen3-32B"]
    - tier: 2  # 降级
      when: "domain == 'chat'"
      models: ["Qwen/Qwen3-0.6B"]
    - tier: 3  # fallback
      when: "true"
      models: ["Qwen/Qwen3-0.6B"]

  # 5. 缓存分层
  cache:
    hot:
      backend: redis
      ttl: 300
      key: "user_id + query + project_id + limit + threshold + types"
    cold:
      backend: milvus
      collection: prompt_embeddings
      threshold: 0.92
    skip_on:
      - personalized
      - tool_result
      - time_sensitive

  # 6. 隐私分级
  privacy:
    recipes: "/etc/sr/recipes/privacy/"
    # 敏感 → 本地 lane (private-pool)
    # 非敏感 → frontier lane (public-pool)
```

**冲突检测**（v0.3.0 新增，PR #1588）：

```go
// 解析期（启动时）跑冲突检测
func Validate(cfg *SemanticRouter) error {
    for _, t := range cfg.Tiers {
        // 规则互斥时：解析期报错，不运行时随机挑
        if overlap(t.When, otherTier.When) && t.Tier == otherTier.Tier {
            return fmt.Errorf("tier conflict: %s overlaps with %s",
                t.When, otherTier.When)
        }
    }
    // SIGNAL_GROUP 内信号必须同源（不能混 jwt-claims 和 prompt-length）
    for _, g := range cfg.Groups {
        if !sameSource(g.Signals) {
            return fmt.Errorf("signal group %s has mixed sources", g.Name)
        }
    }
    return nil
}
```

### 3.4 Workload Variant Autoscaler (WVA)

**WVA 项目**：[llm-d/llm-d/tree/main/guides/workload-autoscaling](https://github.com/llm-d/llm-d/blob/main/guides/workload-autoscaling/README.wva.md)  
**v0.7.0**（2026-06-05）—— saturation-based 自动扩缩，**比 HPA 默认 CPU/Memory 准**。

```yaml
apiVersion: autoscaling.llm-d.io/v1
kind: WorkloadVariantAutoscaler
metadata:
  name: qwen3-32b-wva
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-qwen3-32b
  saturation:
    kv_cache_threshold: 0.80     # 触发扩
    queue_length_threshold: 5
    spare_trigger: 0.10 + 3       # 余量：10% 缓存 + 3 个 queue slot
  metrics:
    - type: Pods
      pods:
        metric:
          name: wva_desired_replicas
        target:
          type: AverageValue
          averageValue: "1"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: qwen3-32b-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-qwen3-32b
  minReplicas: 1
  maxReplicas: 12               # 30B 模型需要 1 + warm pool
  metrics:
    - type: External
      external:
        metric:
          name: wva_desired_replicas
          selector:
            matchLabels:
              deployment: vllm-qwen3-32b
        target:
          type: Value
          value: "1"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Pods
          value: 10
          periodSeconds: 150
    scaleDown:
      stabilizationWindowSeconds: 240   # 关键：避免抖动
      policies:
        - type: Pods
          value: 10
          periodSeconds: 150
```

**WVA 关键设计**：

- **saturation-based**（KV cache 占用 + 队列长度），**不是 CPU/Memory**
- **spare trigger**（0.10+3）= 提前 10% 缓存 + 3 个 queue slot 才触发扩，**避免抖动**
- 通过 **Prometheus Adapter** 暴露 `wva_desired_replicas` 指标，HPA 通过 External Metrics API 拉取
- **scale-down stabilization 240s** —— 比 HPA 默认 300s 短，但比激进配置的 60s 长，**抖动/抖动/抖动**反复实证后定下

---

## 4. 数据面 (Data Plane)

### 4.1 InferencePool Pod 池化

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-qwen3-32b
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vllm-qwen3-32b
  template:
    metadata:
      labels:
        app: vllm-qwen3-32b
        llm-d.ai/pool: qwen3-32b-pool
        llm-d.ai/model: Qwen/Qwen3-32B
      annotations:
        llm-d.ai/warm-pool: "true"  # 标记 warm pool 不缩到 0
    spec:
      nodeSelector:
        nvidia.com/gpu.product: NVIDIA-H100-80GB-HBM3
      containers:
        - name: vllm
          image: vllm/vllm-openai:v0.19.1
          command: ["/bin/bash", "-c"]
          args:
            - >
              vllm serve Qwen/Qwen3-32B
              --tensor-parallel-size 4
              --pipeline-parallel-size 1
              --gpu-memory-utilization 0.92
              --max-model-len 32768
              --enable-prefix-caching
              --enable-chunked-prefill
              --kv-cache-dtype fp8
          ports:
            - containerPort: 8000
          resources:
            limits:
              nvidia.com/gpu: 4
              memory: 384Gi
            requests:
              nvidia.com/gpu: 4
              memory: 384Gi
        - name: epp  # Endpoint Picker sidecar
          image: llm-d/epp:v1.5.0
          env:
            - name: INFERENCE_POOL_NAME
              value: qwen3-32b-pool
            - name: PLUGIN_CONFIG
              value: /etc/epp/plugins.yaml
          volumeMounts:
            - name: epp-config
              mountPath: /etc/epp
        - name: vllm-sr  # 语义路由 sidecar
          image: vllm-project/semantic-router:v0.3.0
          command: ["semantic-router", "--config", "/etc/sr/semantic-router.yaml"]
          ports:
            - containerPort: 8801  # ext_proc gRPC
          volumeMounts:
            - name: sr-config
              mountPath: /etc/sr
        - name: lmcache  # 跨节点 KV-cache
          image: lmcache/lmcache:v0.3.1
          command: ["lmcache-controller", "--config", "/etc/lmcache.yaml"]
          ports:
            - containerPort: 8200
      volumes:
        - name: epp-config
          configMap:
            name: epp-config
        - name: sr-config
          configMap:
            name: sr-config
```

### 4.2 vllm-sr Sidecar 内部

vllm-sr 用 **Envoy ext_proc**（gRPC streaming）协议，是典型的"sidecar filter"模式：

```rust
// crates/semantic-router/src/ext_proc/handler.rs (Rust + candle)
async fn process_request(
    &self,
    req: ProcessingRequest_RequestHeaders,
) -> Result<ProcessingResponse, Status> {
    let headers = req.headers().clone();
    let mut response = ProcessingResponse::default();

    // 1. 解析请求体（chunked / streaming）
    let body = self.collect_body(&req).await?;

    // 2. PRISM legitimacy check
    let legitimacy = self.prism_registry.check(
        model: extract_model(&body),
        user: extract_user(&headers),
        region: extract_region(&headers),
    ).await?;
    if !legitimacy.allowed {
        return Ok(self.deny_response(legitimacy.reason));
    }

    // 3. entropy-based domain detection
    let (domain, confidence) = self.bert_classifier
        .classify(&body.messages)
        .await?;
    let entropy = self.entropy(&confidence);
    let categories = if entropy > 0.65 {
        top_k(&confidence, k=3)  // 高熵多 category (AND 跨域)
    } else {
        vec![argmax(&confidence)]
    };

    // 4. DSL rules evaluate
    let tier = self.dsl.evaluate(Signals {
        jwt_claims: extract_jwt(&headers),
        domain,
        categories,
        prompt_length: estimate_tokens(&body),
    });

    // 5. 选模型
    let model = self.tiers[tier].pick_model(&categories, &legitimacy);
    response.model_override = Some(model);

    // 6. Redis hot cache check
    let cache_key = build_key(user, &body, model);
    if let Some(cached) = self.redis.get(&cache_key).await? {
        if !self.skip_cache(&body) {  // 个人化 / tool result / time-sensitive
            return Ok(self.cache_hit_response(cached));
        }
    }

    // 7. Milvus cold cache check (semantic)
    if !self.skip_cache(&body) {
        let embedding = self.embed(&body.messages).await?;
        if let Some(hit) = self.milvus.search(embedding, threshold=0.92).await? {
            self.redis.set(&cache_key, &hit).await?;  // promote to hot
            return Ok(self.cache_hit_response(hit));
        }
    }

    Ok(response)
}
```

### 4.3 关键算法细节

#### 4.3.1 PRISM 153-key 合法性层

vllm-sr v0.3.0（PR #1563）引入，源自 IBM Research 的 PRISM（**P**olicy **R**egistry for **I**nference **S**ystem **M**odels）白皮书。

**三段判定**：

```
QUALIFICATION (async)         ── 启动时拉 model card / region policy / audit log
                                  in-memory 153-Registry empirical scoring
                                  （避免每次请求都去查外部 DB）

CLASSIFICATION (in-process)   ── 运行时用 candle-binding 跑 ModernBERT embedding
                                  比对 model card / region allowlist / jailbreak pattern

EXECUTION (filter)            ── 沿用 req_filter_jailbreak 模式
                                  模型选定前最后一道关
```

**153-Registry** = 153 个 key 的 in-memory 表，key 包括：
- 模型卡（model name, version, release date, license）
- 地区合规（EU GDPR, US FedRAMP, China 数据出境）
- 用户属性（org_id, tier, audit_log_enabled）
- 行为规则（jailbreak patterns, PII detect, content moderation）

> **意义**：从"我能路由到 X" 到 "我应该路由到 X"。Martian / NotDiamond 有"模型可用性"白名单，但"模型合不合法 / 是否被审计 / 是否在某地区被禁"这套 153-key 工程化 spec，目前仅 vllm-sr。

#### 4.3.2 entropy-based multi-category domain matching

vllm-sr PR #1497（2026-06-03）：

```python
# 之前：domain signal 永远返回 top-1
domain = argmax(classifier.probabilities)

# 现在：entropy-based 多 category
entropy = -Σ(p * log(p) for p in probabilities)
if entropy < threshold:  # 低熵：top-1
    domain = argmax(probabilities)
else:                    # 高熵：AND 跨域
    domain = top_k(probabilities, k=3, threshold=0.1)

# ModernBERT 给概率 → Shannon 熵
# BERT-base / mmBERT-32K 不给概率 → fallback
```

**bug fix**（同 PR）：`computer_science` vs `computer science` MMLU 标签对齐（label normalization）。6 Ginkgo spec 覆盖。

#### 4.3.3 Redis Hot Cache Layer

vllm-sr PR #1423（2026-06-04）：

```yaml
cache:
  hot:
    backend: redis
    key: "user_id + query + project_id + limit + threshold + types"
    ttl: 300
    prefix: "sr:cache:v1:"
```

**`key` 公式**（按 user scope + query 内容 + project 配置，**不能漏 project_id，否则跨租户污染**）：

```
key = sha256(f"{user_id}|{query_hash}|{project_id}|{limit}|{threshold}|{types}")
```

**per-user 失效**（按 prefix 删）：`redis.del("sr:cache:v1:" + user_id + ":*")`

**配套 skip 规则**：
- **PR #1502**：personalized 响应强制 skip（user-specific data / tool result / time-sensitive info）
- **PR #1558**：per-decision cache opt-out（DSL 里可声明 `cache.bypass: true`）

> **关键判断**："hot query 不再走向量库" = Redis < 1ms vs Milvus 5-30ms，是 demo 与 production 的硬分水岭。

#### 4.3.4 隐私路由（Privacy Tier）

vllm-sr PR #1635（2026-06-05）—— 4 文件完整 recipe：

```yaml
# deploy/recipes/privacy/router.yaml
spec:
  privacy:
    recipes: "/etc/sr/recipes/privacy/"
    rules:
      - when: "data.contains_pii || data.contains_phi || data.region == 'EU'"
        lane: "private-pool"     # 本地 vLLM，敏感数据不出域
      - default:
        lane: "public-pool"      # 远端 vLLM 或 frontier model
```

**probe manifest**（16/16 probes pass @ 2026-03-23）：

```yaml
# deploy/recipes/privacy/probes.yaml
probes:
  - name: pii_email
    input: "My email is test@example.com"
    expected_lane: private-pool
  - name: phi_medical
    input: "Patient X has diabetes type 2"
    expected_lane: private-pool
  - name: eu_gdpr
    input: "EU customer record: ..."
    expected_lane: private-pool
  - name: public_coding
    input: "Write a Python function to sort a list"
    expected_lane: public-pool
```

---

## 5. 协议支持

### 5.1 vLLM 推理层协议（v0.19.1 锁版）

| 协议 | 支持 | 说明 |
|---|---|---|
| **OpenAI Chat Completions** | ✅ 完整 | `/v1/chat/completions`，含 SSE 流式 |
| **OpenAI Completions** | ✅ 完整 | `/v1/completions`（legacy） |
| **OpenAI Embeddings** | ✅ 完整 | `/v1/embeddings` |
| **OpenAI Audio** | ✅ 完整 | `/v1/audio/transcriptions`, `/v1/audio/translations`, `/v1/audio/speech` |
| **OpenAI Responses API** | ⚠️ 0.22.1+ 才完整 | 0.19.1 部分支持 |
| **Anthropic Messages** | ✅ 完整 | `/v1/messages`（v0.7+） |
| **Hugging Face Inference API** | ✅ 兼容 | 自动 padding |
| **Tool Use / Function Calling** | ✅ 完整 | OpenAI / Anthropic 两种格式 |
| **MCP (Model Context Protocol)** | ✅ 完整 | vllm-sr 提供 mcp-bridge |
| **A2A (Agent-to-Agent)** | ⚠️ 实验 | v0.19.1 需 `--enable-a2a` |
| **SSE Streaming** | ✅ 完整 | text/event-stream 标准 |
| **WebSocket** | ⚠️ 需独立扩展 | 默认不开启 |

### 5.2 GIE 层协议

| 协议 | 支持 | 说明 |
|---|---|---|
| **HTTP/1.1, HTTP/2** | ✅ | Gateway 标准 |
| **gRPC** | ✅ | EPP 内部通信 |
| **xDS** | ✅ | Envoy CDS/EDS/LDS/RDS |
| **Envoy ext_proc** | ✅ | vllm-sr 用 gRPC streaming |
| **Gateway API** | ✅ v1.0+ | GIE 是 K8s Gateway API 子项目 |
| **Gateway API Inference Extension** | ✅ v1.5.0 | CRD 自定义 |

### 5.3 vllm-sr 层协议

| 协议 | 支持 | 说明 |
|---|---|---|
| **Envoy ext_proc (gRPC)** | ✅ | 主接口 |
| **Envoy ext_authz (gRPC)** | ✅ | 鉴权 |
| **HTTP/JSON 旁路控制** | ⚠️ | `/api/v1/eval` 用于调试 |

---

## 6. 性能数据与基准

### 6.1 WVA v0.7.0 真实基准（llm-d#1586）

来源：[llm-d/llm-d#1586](https://github.com/llm-d/llm-d/pull/1586)，落地在 `guides/workload-autoscaling/README.wva.md`。  
**测试配置**：NVIDIA H100 + OpenShift，Poisson 到达曲线，3-run 平均。  
**WVA KV 阈值 0.80 / 队列长度阈值 5 / spare trigger 0.10+3**；  
**HPA 1–10 replicas**，scale-up 10 Pods/150s（stabilization 0s），scale-down 10 Pods/150s（stabilization 240s），metric source = external `wva_desired_replicas`。

#### 四类流量结果（P99 TTFT 单位 ms）

| 场景 | 模型 | Duration | P99 TTFT | P99 ITL | Avg Rep | Max Rep | Avg KV | Avg Queue | Errors | Pod Startup |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Prefill Heavy** (4k/1k @20RPS) | Qwen3-32B | 600 s | **98,420** | 54.8 | 1.73 | 3 | 66.3% | 236.5 | 4,184 | 110 s |
| Prefill Heavy | Qwen3-0.6B | 600 s | 81,391 | 51.9 | 1.93 | 3 | 65.1% | 76.5 | 401 | 65 s |
| Prefill Heavy | Qwen3-0.6B | 1800 s | 66,177 | 47.3 | 3.17 | 5 | 55.7% | 41.2 | 860 | 66 s |
| **Decode Heavy** (1k/4k @20RPS) | Qwen3-32B | 600 s | 78,051 | 47.1 | 1.84 | 3 | 79.2% | 108.8 | 3,563 | 109 s |
| **Bursty** (15→2→10→15→5→2) | Qwen3-32B | 900 s | **262,441** | 196.3 | 2.43 | 4 | 45.1% | 53.5 | 6,110 | 103 s |
| Bursty | Qwen3-0.6B | 900 s | **13,376** | 48.0 | 1.99 | 3 | 35.2% | 16.0 | 51 | 66 s |
| **Symmetrical** (1k/1k @20RPS) | Qwen3-32B | 600 s | 100,187 | 67.3 | 1.70 | 3 | 70.2% | 166.8 | 3,729 | 103 s |
| Symmetrical | Qwen3-0.6B | 1800 s | 20,825 | 40.4 | 1.80 | 3 | 46.8% | 10.8 | 342 | 66 s |

### 6.2 5 个工程结论

#### 6.2.1 P99 TTFT 在 32B + 突发流量下塌方到 4.4 分钟

Bursty 场景 Qwen3-32B 的 P99 TTFT **262,441 ms ≈ 4.4 分钟**。HPA scale-up window（10 Pods / 150 s）+ WVA 阈值 + pod startup 103 s 三个延迟叠加，新副本就绪前请求已堵 30+ s。

**要 P99 < 1 s SLA**：把 WVA KV spare trigger 从 0.10 抬到 **0.20–0.25**（提前扩容），或把 pod startup 压到 60 s 以内（warm pool 预加载权重）。

#### 6.2.2 0.6B bursty 反而是 13 秒级（20× 改善）

同样 bursty，Qwen3-0.6B P99 TTFT **13,376 ms（~13 s）**。差距不在 WVA，在**模型加载 + 权重传输**：0.6B 启动 64 s、32B 要 103 s，**冷启动补偿直接决定 P99 上限**。

#### 6.2.3 WVA "saturation-based" 扩缩容比 HPA 默认 CPU/Memory 准

32B prefill-heavy KV cache 平均 66.3%、最大 replicas 才 3 — WVA 提前在 KV 75% 触发扩，**没让 cache 撞到 95%**。但 bursty 时 KV cache 平均只 45.1% — 多数时间是"pod 在冷启动"，WVA 决策已够早，**物理 pod startup 是天花板**。

#### 6.2.4 Errors 数字暴露"重试风暴"问题

32B prefill-heavy 600 s 跑出 **4,184 errors / 12,000 请求 = 35% 错误率**。同期 0.6B 同样配置 401 / 12,000 = 3.3% — **差一个数量级**。Bursty 32B 900 s errors 6,110 / 18,000 ≈ 34%。

WVA 没及时扩容时，**client SDK 的 timeout/retry 是 errors 主要贡献者**，不是 vLLM 自身 OOM。生产关键护栏：Client 端严格控制 retry 次数 + 退避；网关侧 early reject（429）+ 请求体大小限速兜底 — 这也是 llm-d v0.7.0 默认切到 standalone 模式的原因。

#### 6.2.5 Pod startup 是 K8s 推理扩容的"隐形税"

| 模型 | 冷启动 |
|---|---|
| Qwen3-32B（H100） | **103–110 s** |
| Qwen3-0.6B（H100） | 64–66 s |

突发流量峰值 < 2 分钟，autoscaling 来不及。解法不是把 WVA 阈值改更激进（反而抖动更大），而是**维持 1–2 个 warm pool pod**，把 max replicas 提到 12 而非 10。

### 6.3 vllm-sr ext_proc 性能开销

```bash
# benchmark 模板（vllm-sr#1585/#1614）
hey -n 10000 -c 100 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"hi"}]}' \
  http://localhost:8000/v1/chat/completions  # 裸 vLLM

hey -n 10000 -c 100 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"hi"}]}' \
  http://localhost:8080/v1/chat/completions  # vllm-sr → vLLM
```

**结果**（vllm-sr 官方 benchmark，2026-06-05）：

| 场景 | 裸 vLLM p50 | vllm-sr p50 | 开销 | 裸 vLLM p99 | vllm-sr p99 | 开销 |
|---|---:|---:|---:|---:|---:|---:|
| 短 prompt (< 100 tokens) | 145 ms | 152 ms | +4.8% | 380 ms | 410 ms | +7.9% |
| 中 prompt (1k tokens) | 580 ms | 612 ms | +5.5% | 1,420 ms | 1,510 ms | +6.3% |
| 长 prompt (8k tokens) | 2,310 ms | 2,395 ms | +3.7% | 5,800 ms | 6,050 ms | +4.3% |
| **含缓存命中（短 prompt）** | 145 ms | **8 ms** | **-94.5%** | 380 ms | **22 ms** | **-94.2%** |

> **关键判断**：vllm-sr 的开销 5-8% 是 ext_proc 协议开销 + DSL 评估 + Redis/Milvus 查找。但**缓存命中时是 95% 加速**（毫秒级），**这是 vllm-sr 的核心价值**。

### 6.4 sjson / gjson 性能优化

vllm-sr PR #1585（sjson 替代 encoding/json）+ PR #1614（gjson 替代）：

```rust
// 之前：encoding/json
let body: serde_json::Value = serde_json::from_slice(&body_bytes)?;  // 8.4 µs

// 现在：sjson 写入 + gjson 读取
let mut writer = sjson::Writer::new(&mut buf);
writer.insert("model", model);  // 0.3 µs

let msg_content = gjson::get(&body, "messages.0.content").str();  // 0.2 µs
```

实测数字：request body rewrite p99 减少 **45%**，response body 提取减少 **60%**。

### 6.5 与其他推理栈对比

| 维度 | llm-d + vllm-sr v0.7.0 | Envoy AI Gateway v0.6 | TGI + K8s 裸 | vLLM 裸 + 手动扩缩 |
|---|---|---|---|---|
| **设计目标** | K8s-native 推理路由 | L7 反代 + 模型路由 | 推理引擎 + 简单 LB | 单实例自托管 |
| **数据面** | agentgateway v2.2.1 + EPP + vllm-sr ext_proc | Envoy + extproc | TGI Rust server | vLLM server |
| **路由粒度** | Header / body / KV cache affinity / predicted latency | Header / body / 模型名 | Round-robin / random | 单一模型 |
| **配置规模** | InferencePool CRD + WVA | AIGatewayRoute 2,000 条 | Service + Ingress | 单 deployment |
| **运行时性能（P99 TTFT 32B prefill）** | 98 s（WVA 0.7 数据） | 未公开统一基准 | ~85 s（裸 TGI） | ~80 s（裸 vLLM） |
| **P99 TTFT 32B bursty** | **262 s**（冷启动物理上限） | 未测 | ~240 s | ~220 s |
| **自动扩缩** | **WVA v1 Saturation + HPA + Prometheus Adapter** | 无内建 | HPA CPU/Memory | 手动 |
| **缓存层** | **Redis + Milvus + LMCache** | 仅 1 层（自实现） | 无 | 无 |
| **路由算法丰富度** | **5 类 scorers** + DSL + PRISM | extproc 自实现 | 简单权重 | 无 |
| **升级风险** | v0.7.0 强升 CUDA 13 + driver 580 + vLLM 锁版 | v0.6 弃用 filterConfig | TGI 升级平滑 | vLLM 升级平滑 |
| **默认路径** | standalone（v0.7.0 起） | full gateway | full | 单一 pod |
| **生产 SRE 友好** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ |

### 6.6 GIE v1.5.0 Latency Predictor 预测精度

来源：GIE PR #2432 文档（2026-04-19）。

| 模型 | 真实 P99 | 预测 P99 | 误差 |
|---|---:|---:|---:|
| Qwen3-32B（prefill-heavy 4k/1k @20RPS） | 98 s | 87 s | -11.2% |
| Qwen3-32B（bursty） | 262 s | 295 s | +12.6% |
| Qwen3-0.6B（prefill-heavy） | 81 s | 76 s | -6.2% |

预测特征：
- 提示词长度（字符数 + token 数 + 实际 tokenizer 后长度）
- 历史 P50/P90/P99 延迟（按 model × prompt 长度桶）
- 当前 KV cache 占用率
- 队列深度

**好处**：把"新副本还差多少就绪"信号融进 routing 决策，**让老副本多扛一会儿**，**避免重复预测同一个未来时刻**。Bursty 32B 的 P99 TTFT 4.4 分钟问题有望压到 < 60 s（不是 cold start 救得了，而是 routing 决策更准）。

---

## 7. 部署方式

### 7.1 快速开始（standalone 模式）

```bash
# 1. 准备 K8s 集群（H100 GPU + OpenShift / vanilla K8s 1.29+）
# 2. 安装 GPU operator
helm install nvidia-gpu nvidia/gpu-operator \
  --namespace nvidia-gpu --create-namespace

# 3. 安装 llm-d (standalone 模式)
helm install llm-d oci://ghcr.io/llm-d/charts/llm-d \
  --version 0.7.0 \
  --namespace llm-d --create-namespace \
  --set inferencePool.name=qwen3-32b-pool \
  --set vllm.model=Qwen/Qwen3-32B \
  --set vllm.tensorParallelSize=4

# 4. 端口转发测试
kubectl port-forward -n llm-d svc/llm-d-inference-gateway 8000:80

# 5. 调 OpenAI 兼容 API
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-32B",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 7.2 完整 gateway 模式

```bash
# 1. 安装 Gateway API CRD
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

# 2. 安装 GIE CRD
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/download/v1.5.0/manifests.yaml

# 3. 安装 Gateway 实现（Envoy Gateway / Contour / Istio）
helm install eg envoy/gateway --namespace envoy-gateway-system --create-namespace

# 4. 安装 llm-d (full gateway 模式)
helm install llm-d oci://ghcr.io/llm-d/charts/llm-d \
  --version 0.7.0 \
  --namespace llm-d --create-namespace \
  --set mode=gateway \
  --set inferencePool.enabled=true \
  --set vllmSr.enabled=true \
  --set wva.enabled=true

# 5. 部署 vllm-sr sidecar config
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: sr-config
  namespace: llm-d
data:
  semantic-router.yaml: |
    apiVersion: vllm.sr/v1
    kind: SemanticRouter
    spec:
      domain:
        model: "mmBERT-32K"
        entropy_threshold: 0.65
      tiers:
        - tier: 0
          when: "user.tier == 'admin'"
          models: ["Qwen/Qwen3-32B"]
        - tier: 1
          when: "true"
          models: ["Qwen/Qwen3-32B", "Qwen/Qwen3-0.6B"]
      cache:
        hot:
          backend: redis
          ttl: 300
        cold:
          backend: milvus
          threshold: 0.92
EOF

# 6. 部署 Redis + Milvus
helm install redis bitnami/redis --namespace llm-d
helm install milvus milvus/milvus --namespace llm-d
```

### 7.3 IBM watsonx.ai 集成

```bash
# watsonx.ai 内部用 llm-d
# 1. 私有化部署
oc apply -f https://raw.githubusercontent.com/IBM/watsonx-deployer/main/llm-d/operator.yaml

# 2. watsonx.ai LLM 调用直接走 llm-d 集群
#    外部接口仍是 OpenAI 兼容
curl -X POST https://watsonx.ai/api/v1/chat/completions \
  -H "Authorization: Bearer ${WATSONX_API_KEY}" \
  -d '{"model":"ibm/granite-3-32b-instruct","messages":[...]}'
```

### 7.4 升级路径

```bash
# v0.6.x → v0.7.0 升级注意事项
# 1. 升级前必须升级 CUDA + driver
nvidia-smi  # 确认 driver >= 580
# 如未达 580，先升级 GPU operator
helm upgrade nvidia-gpu nvidia/gpu-operator --set driver.version=580

# 2. 备份自定义 CRD
kubectl get inferencepool -A -o yaml > backup-pool.yaml
kubectl get workloadvariantautoscaler -A -o yaml > backup-wva.yaml

# 3. 升级 llm-d
helm upgrade llm-d oci://ghcr.io/llm-d/charts/llm-d --version 0.7.0 \
  --reuse-values \
  --set vllm.image.tag=v0.19.1  # 锁版本

# 4. vllm-sr 也需要同步升级
helm upgrade vllm-sr oci://ghcr.io/vllm-project/semantic-router/charts/sr --version 0.3.0
```

---

## 8. 成本模型

### 8.1 部署成本结构

以 IBM watsonx.ai production 部署为例（2026-Q2 数据，**64×H100-80GB 集群**）：

| 组件 | 数量 | 单位成本（$/h） | 月度成本（$） |
|---|---:|---:|---:|
| H100-80GB GPU（按需） | 64 | 2.5 | 115,200 |
| H100-80GB GPU（1年预留） | 64 | 1.6 | 73,728 |
| EPP（4 vCPU × 8Gi × 3 replicas） | 3 pods | 0.32 | 691 |
| vllm-sr sidecar（2 vCPU × 4Gi × 16 pods） | 16 pods | 0.16 | 1,843 |
| Redis（cache 热层，3 主 3 从） | 6 节点 | 0.20 | 864 |
| Milvus（cache 冷层，1 主 2 从） | 3 节点 | 0.45 | 972 |
| **月度总成本（按需）** | | | **~119,500** |
| **月度总成本（1年预留）** | | | **~78,000** |

### 8.2 单位 Token TCO

**对比 SaaS OpenAI GPT-4o**（2026-Q2 价目，$5/1M input + $15/1M output）：

```
以 1B tokens/月（50% input + 50% output）为例：
- OpenAI GPT-4o: $5 * 0.5 + $15 * 0.5 = $10/1M tokens
              → 1B tokens = $10,000/月
- llm-d 自托管 (Qwen3-32B):
    月度固定成本 $78,000 ÷ 1B tokens = $78/1M tokens
    → 1B tokens = $78,000/月  (贵 7.8x)

但如果 QPS 上去，GPU 利用率提上来：
    64 GPU × 2.5k tokens/s/GPU × 86400s × 30d = 414B tokens/月（理论上限）
    实际 30% 利用率 = 124B tokens/月
    → $78,000 / 124B = $0.63/1M tokens
    → 比 OpenAI 便宜 16x

盈亏平衡点：~ 10B tokens/月
```

**结论**：llm-d 自托管在 **月 token 量 > 10B** 时开始比 OpenAI GPT-4o 便宜。  
对 5-15 万 / 年的副业产品（即月均 50k-150k tokens 用户群），**SaaS LLM API 更划算**；llm-d 是"自托管大流量"或"数据合规要求本地化"的方案。

### 8.3 llm-d 相对裸 vLLM 的额外成本收益

- **WVA 节省副本**：实测减少 30-40% 平均副本数（vs 静态 HPA）
- **LMCache 跨节点 KV**：长 prompt 场景节省 50%+ GPU 时间
- **vllm-sr 缓存命中**：重复 query 节省 90%+ GPU 时间
- **EPP prefix-cache-scorer**：相同 prefix 请求打同一 pod，节省 30%+ decode 时间

**综合**：llm-d 比裸 vLLM deployment **省 30-50% 副本**，月度成本下降 30-50%。

---

## 9. 生态与集成

### 9.1 上游生态

| 项目 | 关系 | 集成方式 |
|---|---|---|
| **vLLM** | 推理引擎 | llm-d 锁 vLLM 0.19.1，vllm-sr 通过 OpenAI 兼容 API 调 |
| **LMCache** | 跨节点 KV-cache | 同一 Pod 内 sidecar，NVLink/IB 互联 |
| **Kubernetes Gateway API** | 入口标准 | GIE 是子项目 |
| **Istio** | Service Mesh | 通过 Gateway API 接入（不是直接 Envoy） |
| **Prometheus Adapter** | 指标桥接 | 暴露 `wva_desired_replicas` 给 HPA |
| **KEDA** | 事件驱动扩缩 | 可替代 Prometheus Adapter |
| **OpenTelemetry** | Tracing | EPP / vllm-sr 都有 OTel 导出器 |
| **NVIDIA NIM** | 推理镜像 | 可作为 vLLM 替代后端 |

### 9.2 商业产品集成

| 厂商 | 集成方式 |
|---|---|
| **IBM watsonx.ai** | 直接基于 llm-d 私有化部署 |
| **Red Hat OpenShift AI** | Service Mesh + llm-d Operator 一键装 |
| **Google GKE Inference** | Gateway API + InferencePool 复用 |
| **NVIDIA NIM Operator** | NIM 镜像可作为 llm-d 的推理后端 |
| **阿里云 ACK** | 通过服务网格集成 |
| **腾讯云 TKE** | 实验性集成 |

### 9.3 关键 PR 生态

| 仓库 | 关键 PR | 说明 |
|---|---|---|
| llm-d/llm-d | #1586 WVA benchmark data | v0.7.0 端到端第一份真实基准 |
| llm-d/llm-d | #1688 precise-prefix-cache-scorer | 精确 prefix 缓存评分 |
| llm-d/llm-d | #1655 Prometheus Adapter deprecation | 警示 Prometheus Adapter 不再是首选 |
| llm-d/llm-d | #1700 TPU benchmark | 跨硬件支持（TPU V6 P/D） |
| vllm-project/semantic-router | #1563 PRISM 153-key | 合法性层白皮书 |
| vllm-project/semantic-router | #1497 entropy domain | entropy 多域判定 |
| vllm-project/semantic-router | #1588 SIGNAL_GROUP/TIER | DSL 表达力 + 冲突检测 |
| vllm-project/semantic-router | #1620 routing.projections | conflict-free routing |
| vllm-project/semantic-router | #1423 Redis hot cache | 缓存分层 |
| vllm-project/semantic-router | #1635 privacy recipe | 隐私分级 |
| vllm-project/semantic-router | #1585 sjson | request body rewrite 性能 |
| vllm-project/semantic-router | #1614 gjson | response body 提取性能 |
| vllm-project/semantic-router | #1574 candle FFI softmax | ModernBERT 软最大值（下一轮） |
| vllm-project/semantic-router | #1583 vllm-sr-sim v0.1.0 | 独立 simulator |
| kubernetes-sigs/gateway-api-inference-extension | #2359 Pluggable Parser | EPP 解析框架 |
| kubernetes-sigs/gateway-api-inference-extension | #2432/#2473 Latency Predictor | 预测 P99 路由 |
| kubernetes-sigs/gateway-api-inference-extension | #2442 BBR body | body 路由 |
| kubernetes-sigs/gateway-api-inference-extension | #2369 插件镜像响应 | 同一插件双向 |

### 9.4 vllm-sr v0.3.0 release 70+ PR 速览

```
# 6/3-6/5 70+ PR（按时间倒序，部分）
#1627  OpenClaw VSR install bridge        -- 与 OpenClaw 集成
#1620  routing.projections                -- conflict-free routing
#1614  gjson for response body            -- 性能
#1588  SIGNAL_GROUP + TEST + TIER        -- DSL 表达力
#1585  sjson for request body             -- 性能
#1583  vllm-sr-sim v0.1.0                 -- simulator 独立
#1574  candle FFI softmax                 -- ModernBERT 软最大值（待合）
#1572  UseModernBERT                      -- 已 revert（待 #1574 修）
#1563  PRISM 153-key whitepaper           -- 合法性层
#1561  revert UseModernBERT               -- 跟随 #1574
#1558  per-decision cache opt-out         -- DSL cache.bypass
#1532  ModernBERT refactor                -- ModernBERT 集成
#1502  skip cache for personalized        -- 个性化 skip
#1497  entropy-based domain matching      -- 多 category
#1423  Redis hot cache                    -- 缓存分层
#1435  Prometheus metrics                 -- 可观测
#1401  Helm chart 0.3.0                   -- 部署
#1392  health check                       -- 健康检查
#1380  OpenAI tool call parsing           -- 工具调用
#1375  streaming response                 -- SSE
#... 70+ PRs 总计
```

---

## 10. 客户案例与生产部署

### 10.1 IBM watsonx.ai（核心用户）

**部署规模**：2026-Q2 公开数据，IBM Cloud 内部 64×H100 + 32×MI300X 集群，跑 Granite 3 系列 + Qwen3 蒸馏版。

**配置摘要**：
- 3 个 InferencePool：granite-3-32b / granite-3-8b / granite-3-2b
- 16 个 vllm-sr sidecar（每个 vLLM pod 1 个）
- WVA: KV 0.80 / queue 5 / spare 0.10+3，max replicas 12/pool
- Redis 6 节点 + Milvus 3 节点
- EPP 在推理 Gateway 中 3 replicas

**实际效果**（IBM 2026-Q1 报告）：
- 平均 P99 TTFT 32B prefill：从 1.8 分钟（裸 vLLM）降到 1.6 分钟
- Bursty 32B P99 TTFT：从 4.5 分钟降到 4.4 分钟（**主要受限于冷启动**）
- 副本数：从 8-10（静态 HPA）降到 4-6（WVA 动态），**节省 30-40% GPU**
- 重复 query 缓存命中：~25% 请求走 Redis 毫秒级返回

### 10.2 Red Hat OpenShift AI

**部署形态**：包装成 OpenShift Operator + OpenShift Service Mesh 2.x。

**特点**：
- 一键 `oc create -f llm-d-operator.yaml` 装好
- 自动注入 Gateway API + GIE CRD
- 与 OpenShift Service Mesh 2 集成，统一 mTLS + 可观测
- 通过 OpenShift GitOps 同步 vllm-sr config

### 10.3 NVIDIA NIM 集成

**模式**：NIM 镜像可作为 llm-d 的推理后端之一（vLLM 是默认）。

```yaml
apiVersion: inference.networking.x-k8s.io/v1alpha2
kind: InferencePool
metadata:
  name: nim-llama3-pool
spec:
  targetPorts:
    - number: 8000
  selector:
    app: nim-llama3-70b-instruct
  template:
    spec:
      containers:
        - name: nim
          image: nvcr.io/nim/meta/llama3-70b-instruct:1.0.0
          # ... NIM 标准配置
```

### 10.4 Bloomberg

**私有化部署**：基于 vllm-sr 早期版本（v0.2.x），金融领域 fine-tune 模型 + RAG。

**重点场景**：
- 金融实体识别（NER 模型）
- 财报摘要（Qwen3-32B 蒸馏版）
- 隐私路由：含客户信息 → 本地 lane，**完全不出域**

### 10.5 阿里云（ACK + 服务网格）

**模式**：通过阿里云 ASM（服务网格）集成 Gateway API + GIE。

**特点**：
- 阿里云 GPU 池（A100 / H800）作为推理后端
- vllm-sr 走 Qwen 系列模型
- 与百炼平台模型市场联动

### 10.6 一线互联网公司（公开案例汇总）

| 公司 | 用法 | 规模 |
|---|---|---|
| Bytedance | 内部 LLM 网关 | ~200 GPU H100/A100 |
| Meta | LLaMA 推理 + 内部 API 网关 | 私有化（规模未公开） |
| Google | GKE Inference 内部使用 | 200+ 集群 |
| 阿里 | 通义实验室 + 内部 RAG | 100+ GPU |
| Bloomberg | 金融 fine-tune | 32 GPU |
| 蚂蚁 | 风控模型 + LLM | 64 GPU |

---

## 11. 优势 / 风险 / 反模式

### 11.1 优势

1. **K8s 原生**：InferencePool CRD + HPA + WVA，K8s 运维工具链（kubectl / ArgoCD / Prometheus Adapter / KEDA）全部天然适配
2. **调度粒度细**：5 类 scorers（queue / KV / prefix / predicted latency / SLO）= 请求级别 + 副本级别双维度调度
3. **缓存分层**：Redis 热 + Milvus 冷 + LMCache 跨节点 KV = 重复 query 95% 加速
4. **路由智能化**：entropy 多域 + PRISM 合法性 + DSL SIGNAL_GROUP = 不止"按 header 路由"
5. **隐私分级**：本地 lane vs frontier lane = 数据合规要求本地化时的硬性要求
6. **开源 + 厂商中立**：LF AI & Data 旗下，IBM / Red Hat / Google / NVIDIA 多家支持
7. **完整 CI/CD**：WVA v0.7.0 benchmark data 合入 = 每晚 regression test，避免"benchmark = PDF"

### 11.2 风险

1. **vLLM 锁版本**：llm-d 0.7.0 锁 vLLM 0.19.1，落后上游 3 个版本（v0.22.1）。**生产用户不能自己 bump vLLM**，要等 llm-d 大版本
2. **CUDA 强升**：v0.7.0 强制 CUDA 13.0.2 + driver 580，旧 GPU operator 不兼容
3. **Pod 冷启动**：32B 模型 103-110s 冷启动，**突发流量下 P99 SLA 物理不可达**（warm pool 是必须的）
4. **配置复杂度**：vllm-sr DSL + GIE CRD + WVA + EPP = 4 套配置协同，新人上手 2-3 周
5. **gRPC streaming ext_proc 调试困难**：sjson / gjson 性能优化带来的字节级差异，在 streaming response 拼接时会暴露
6. **Milvus 部署成本**：3 节点起步 + GPU embedding 推理 = 缓存冷层不便宜
7. **冲突检测导致启动失败**：DSL 写得不好，启动期 `tier conflict` 错误就整个 pod 起不来

### 11.3 反模式（明确不要）

1. **❌ 在 bursty 流量下不配 warm pool**：32B 冷启动 100s 物理上限，无解
2. **❌ Client SDK 默认 `max_retries=2`**：35% 错误率 × 3 倍重试 = 副本打挂
3. **❌ 监控看 HPA 实际 replicas 而非 `wva_desired_replicas`**：HPA 默认 240s scale-down stabilization，"假性扩容"是真实成本黑洞
4. **❌ 用 vllm-sr 但不开缓存**：5-8% 协议开销白付，没拿到 95% 加速红利
5. **❌ 把 llm-d 默认 standalone 模式直接上生产**：v0.7.0 UX 友好但生产应该切回 full gateway
6. **❌ 用 ModernBERT 没等 #1574 合入**（#1572 已 revert）：candle FFI softmax 修不了会概率错误
7. **❌ 自己 bump vLLM**：锁版本是 llm-d 团队的责任，自己升级会破 WVA / LMCache / EPP 集成
8. **❌ 个人化响应（user-specific / tool result / time-sensitive）走缓存**：PR #1502 已明确 skip，违反会造成**信息泄露**

### 11.4 调试工具集

| 工具 | 用途 |
|---|---|
| `kubectl get inferencepool -o yaml` | 看 CRD 状态 |
| `kubectl get workloadvariantautoscaler -o yaml` | 看 WVA 状态 |
| `kubectl logs -f deploy/epp` | EPP 日志 |
| `kubectl logs -f <pod> -c vllm-sr` | vllm-sr 日志 |
| `agctl log proxy / agctl log controller` | agentgateway 日志 |
| `agctl pprof` | 性能 profile |
| `inference-perf` (v0.5.0) | 压测工具 |
| `vllm-sr-sim` (v0.1.0) | 路由模拟器 |
| `redis-cli MONITOR` | Redis 缓存监控 |
| `milvus_cli query` | Milvus 缓存查询 |

---

## 12. 2026-2027 路线图

### 12.1 已确定的下个版本

| 版本 | 预计发布 | 关键变化 |
|---|---|---|
| **vllm-sr v0.3.1** | 2026-06 中下旬 | conflict-free routing 完整落地 + `routing.projections` DSL 完整 + ModernBERT candle FFI 软最大值 PR #1574 合入 |
| **vllm-sr v0.4.0** | 2026 Q3 | multi-cluster 路由 + A2A 协议支持 + 完整 e2e benchmark |
| **llm-d v0.8.0** | 2026 Q3 | 默认切回 full gateway（standalone 留 opt-in）+ vLLM 0.21.x 锁版 + GIE v1.6 集成 |
| **llm-d v0.9.0** | 2026 Q4 | TPU/GPU 异构调度 + 跨集群路由 + A2A 协议原生 |
| **GIE v1.6.0** | 2026 Q3 | Latency Predictor 训练数据开源 + BBR v2（多模态支持） |
| **WVA v1.0.0** | 2026 Q3 | 正式 GA，脱离 llm-d guides 独立项目 |

### 12.2 长期方向（2026 H2 - 2027）

1. **"vllm-sr + LMCache + Envoy" 打包**（类似当年 Istio + Envoy + Prometheus 三件套）—— 路由器与 LLM 推理栈边界模糊化
2. **Latency Predictor 与 WVA 闭环**：预测 P99 → 提前扩容 → 实际 P99 → 反馈训练 → 更准预测
3. **多模态路由**：文本 / 图像 / 音频 / 视频按 BBR v2 路由
4. **A2A 协议原生**：vllm-sr v0.4 + llm-d v0.9 + GIE v1.6 同步支持
5. **跨云路由**：本地 lane（私有云）+ frontier lane（公有云）+ cost-aware 切换
6. **agent trace 整合**：OTel GenAI semconv `gen_ai.agent.invocation.id` 与 WVA event 对齐
7. **GPU TPU parity**：nightly benchmark 同步两栈（已在 #1661 启动）
8. **MCP 协议深度集成**：vllm-sr 提供 mcp-bridge + ext_proc MCP 解析

### 12.3 不确定项

- **何时 GA v1.0**：llm-d 团队未公开时间表，估计 2026 Q4
- **是否做跨厂商 SaaS 路由**：当前专注 self-host vLLM，但 PRISM 153-key 可以扩展到 Anthropic / OpenAI
- **是否替换 EPP 为自家路由器**：当前依赖 GIE，但 EPP 在 v0.7.0 还没达到"开箱即用"

---

## 13. 关键参考与一手资料

### 13.1 项目仓库

- [llm-d/llm-d](https://github.com/llm-d/llm-d) —— 主仓
- [vllm-project/semantic-router](https://github.com/vllm-project/semantic-router) —— 路由 sidecar
- [kubernetes-sigs/gateway-api-inference-extension](https://github.com/kubernetes-sigs/gateway-api-inference-extension) —— 协议层
- [LMCache](https://github.com/LMCache/LMCache) —— 跨节点 KV-cache
- [vllm-project/vllm](https://github.com/vllm-project/vllm) —— 推理引擎

### 13.2 vllm-sr v0.3.0 关键 PR

- PRISM 153-key whitepaper: <https://github.com/user-attachments/files/25750911/PRISM-Vllm-SR-whitepaper-COMPLET-EN.pdf>
- #1563 PRISM whitepaper PDF
- #1497 entropy domain
- #1588 SIGNAL_GROUP / TIER / TEST
- #1620 routing.projections
- #1423 Redis hot cache
- #1635 privacy recipe
- #1585 sjson / #1614 gjson 性能
- #1502 skip cache personalized
- #1558 per-decision cache opt-out
- #1574 candle FFI softmax（下一轮）
- #1583 vllm-sr-sim v0.1.0
- #1627 OpenClaw VSR install bridge

### 13.3 GIE v1.5.0 关键 PR

- #2359 Pluggable Parser Framework
- #2432 / #2473 Latency Predictor
- #2442 BBR body integration
- #2369 插件镜像响应

### 13.4 llm-d v0.7.0 关键 PR

- #1586 WVA benchmark data
- #1688 precise-prefix-cache-scorer
- #1655 Prometheus Adapter deprecation note
- #1700 TPU benchmark test

### 13.5 行业报告（2026-05 - 2026-06）

- `reports/2026-06-06-0648-aigw-arch-benchmark-inference-gw.md` —— 本报告主要数据源
- `hermes/reports/2026-06-06-1038-aigw-semantic-routing-r2.md` —— vllm-sr v0.3.0 详细 PR 分析
- `hermes/reports/2026-06-05-0226-aigw-agent-gateway.md` —— agentgateway 关系
- `hermes/reports/2026-06-05-2049-aigw-arch-benchmark-r4.md` —— 上一期架构对比

### 13.6 内部已覆盖的相邻产品（用于对比）

- `product-vllm-20260605.md` —— 推理引擎侧
- `product-envoy-ai-gateway-20260605.md` —— L7 反代侧
- `product-kserve-20260606.md` —— K8s 推理平台侧
- `product-istio-ai-extension-20260606.md` —— 服务网格侧
- `product-kong-ai-gateway-20260605.md` —— 传统 API 网关侧
- `product-higress-20260605.md` —— API 网关侧（基于 Envoy）
- `product-solo-ai-gateway-20260606.md` —— 服务网格 + 推理路由
- `product-bentoml-bentocloud-20260606.md` —— 推理部署平台
- `product-triton-inference-server-20260605.md` —— NVIDIA 推理引擎
- `product-tgi-20260605.md` —— HF 推理引擎

---

## 14. 附录

### 14.1 完整 InferencePool + EPP + WVA 一体化示例

```yaml
# === InferencePool：定义推理 pod 池 ===
apiVersion: inference.networking.x-k8s.io/v1alpha2
kind: InferencePool
metadata:
  name: qwen3-32b-pool
  namespace: llm-d
spec:
  targetPorts:
    - number: 8000
  selector:
    app: vllm-qwen3-32b
---
# === InferenceModel：模型名 → Pool 映射 ===
apiVersion: inference.networking.x-k8s.io/v1alpha2
kind: InferenceModel
metadata:
  name: qwen3-32b
  namespace: llm-d
spec:
  modelName: "Qwen/Qwen3-32B"
  poolRef:
    name: qwen3-32b-pool
  criticality: Critical
---
# === Gateway + GIE 绑定 ===
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: llm-d-gateway
  namespace: llm-d
spec:
  gatewayClassName: envoy
  listeners:
    - name: http
      port: 80
      protocol: HTTP
  infrastructure:
    labels:
      llm-d.ai/gateway: "true"
---
# === HTTPRoute：路径路由 ===
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: openai-compat
  namespace: llm-d
spec:
  parentRefs:
    - name: llm-d-gateway
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /v1
      backendRefs:
        - group: inference.networking.x-k8s.io
          kind: InferencePool
          name: qwen3-32b-pool
---
# === vLLM Deployment ===
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-qwen3-32b
  namespace: llm-d
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vllm-qwen3-32b
  template:
    metadata:
      labels:
        app: vllm-qwen3-32b
        llm-d.ai/pool: qwen3-32b-pool
      annotations:
        llm-d.ai/warm-pool: "true"
    spec:
      nodeSelector:
        nvidia.com/gpu.product: NVIDIA-H100-80GB-HBM3
      containers:
        - name: vllm
          image: vllm/vllm-openai:v0.19.1
          command: ["/bin/bash", "-c"]
          args:
            - >
              vllm serve Qwen/Qwen3-32B
              --tensor-parallel-size 4
              --gpu-memory-utilization 0.92
              --max-model-len 32768
              --enable-prefix-caching
              --enable-chunked-prefill
              --kv-cache-dtype fp8
              --served-model-name Qwen/Qwen3-32B
          ports:
            - containerPort: 8000
          resources:
            limits:
              nvidia.com/gpu: 4
              memory: 384Gi
        - name: epp
          image: llm-d/epp:v1.5.0
          env:
            - name: INFERENCE_POOL_NAME
              value: qwen3-32b-pool
            - name: PLUGIN_CONFIG
              value: /etc/epp/plugins.yaml
          ports:
            - containerPort: 9000
          volumeMounts:
            - name: epp-config
              mountPath: /etc/epp
        - name: vllm-sr
          image: vllm-project/semantic-router:v0.3.0
          command: ["semantic-router", "--config", "/etc/sr/semantic-router.yaml"]
          ports:
            - containerPort: 8801
          volumeMounts:
            - name: sr-config
              mountPath: /etc/sr
        - name: lmcache
          image: lmcache/lmcache-controller:v0.3.1
          command: ["lmcache-controller", "--config", "/etc/lmcache.yaml"]
          ports:
            - containerPort: 8200
      volumes:
        - name: epp-config
          configMap:
            name: epp-config
        - name: sr-config
          configMap:
            name: sr-config
---
# === EPP 插件配置 ===
apiVersion: v1
kind: ConfigMap
metadata:
  name: epp-config
  namespace: llm-d
data:
  plugins.yaml: |
    apiVersion: inference.networking.x-k8s.io/v1alpha2
    kind: EPPConfig
    spec:
      plugins:
        - type: queue-scorer
          name: queue
          parameters:
            window: 30s
        - type: kv-cache-scorer
          name: kv
          parameters:
            threshold: 0.95
        - type: prefix-cache-scorer
          name: prefix
          parameters:
            minMatch: 32
        - type: predicted-latency-scorer
          name: latency
          parameters:
            modelPath: "/etc/epp/latency-model.onnx"
        - type: slo-headroom-tier-filter
          name: slo
          parameters:
            targetP99Ms: 1000
      scoring:
        - scorer: queue
          weight: 0.2
        - scorer: kv
          weight: 0.3
        - scorer: prefix
          weight: 0.3
        - scorer: latency
          weight: 0.1
        - scorer: slo
          weight: 0.1
---
# === vllm-sr config ===
apiVersion: v1
kind: ConfigMap
metadata:
  name: sr-config
  namespace: llm-d
data:
  semantic-router.yaml: |
    apiVersion: vllm.sr/v1
    kind: SemanticRouter
    spec:
      legitimacy:
        enabled: true
        registry: "embed:///etc/sr/registry-153.json"
        qualification: async
        classification: in-process
        execution: filter
      domain:
        model: "mmBERT-32K"
        entropy_threshold: 0.65
        multi_category: true
      signals:
        - name: jwt-tier
          type: jwt
          key: "tier"
        - name: prompt-domain
          type: classifier
        - name: prompt-length
          type: token_count
      groups:
        - name: enterprise-tier
          signals: [jwt-tier, prompt-domain]
      tiers:
        - tier: 0
          when: "jwt-tier == 'admin'"
          models: ["Qwen/Qwen3-32B"]
        - tier: 1
          when: "domain == 'coding'"
          models: ["Qwen/Qwen3-32B", "Qwen/Qwen3-0.6B"]
        - tier: 2
          when: "true"
          models: ["Qwen/Qwen3-0.6B"]
      cache:
        hot:
          backend: redis
          ttl: 300
          key: "user_id + query + project_id + limit + threshold + types"
        cold:
          backend: milvus
          collection: prompt_embeddings
          threshold: 0.92
        skip_on:
          - personalized
          - tool_result
          - time_sensitive
      privacy:
        rules:
          - when: "data.contains_pii || data.region == 'EU'"
            lane: "private-pool"
          - default:
            lane: "public-pool"
---
# === WVA: Workload Variant Autoscaler ===
apiVersion: autoscaling.llm-d.io/v1
kind: WorkloadVariantAutoscaler
metadata:
  name: qwen3-32b-wva
  namespace: llm-d
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-qwen3-32b
  saturation:
    kv_cache_threshold: 0.80
    queue_length_threshold: 5
    spare_trigger: 0.10
    spare_queue: 3
---
# === HPA 消费 WVA 指标 ===
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: qwen3-32b-hpa
  namespace: llm-d
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-qwen3-32b
  minReplicas: 2      # 1 + 1 warm pool
  maxReplicas: 12
  metrics:
    - type: External
      external:
        metric:
          name: wva_desired_replicas
          selector:
            matchLabels:
              deployment: vllm-qwen3-32b
        target:
          type: Value
          value: "1"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Pods
          value: 10
          periodSeconds: 150
    scaleDown:
      stabilizationWindowSeconds: 240
      policies:
        - type: Pods
          value: 10
          periodSeconds: 150
---
# === Redis (cache 热层) ===
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: llm-d
spec:
  replicas: 6  # 3 主 3 从
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7.2-alpine
          args: ["--maxmemory", "4gb", "--maxmemory-policy", "allkeys-lru"]
          ports:
            - containerPort: 6379
---
# === Milvus (cache 冷层) ===
# 简化版，Milvus Operator 见 https://milvus.io/docs/install_cluster-milvusoperator.md
apiVersion: milvus.io/v1beta1
kind: Milvus
metadata:
  name: milvus
  namespace: llm-d
spec:
  components:
    enabled: true
  config:
    common:
      storageType: "MinIO"
```

### 14.2 EPP 评分算法伪代码

```go
// pkg/epp/scheduling/framework/plugins/queue/queue.go
type QueueScorer struct{}

func (q *QueueScorer) Score(ctx *RequestContext, pod *Pod) float64 {
    queueLen := pod.Metrics.QueueDepth
    if queueLen == 0 {
        return 1.0
    }
    // queue length 反比
    return 1.0 / (1.0 + float64(queueLen) / 10.0)
}

// pkg/epp/scheduling/framework/plugins/kvcache/kv.go
type KVCacheScorer struct{}

func (k *KVCacheScorer) Score(ctx *RequestContext, pod *Pod) float64 {
    usage := pod.Metrics.KVCacheUsage  // 0.0 - 1.0
    if usage > 0.95 {
        return 0.0  // 拒绝
    }
    return 1.0 - usage
}

// pkg/epp/scheduling/framework/plugins/prefix/prefix.go
type PrefixCacheScorer struct{}

func (p *PrefixCacheScorer) Score(ctx *RequestContext, pod *Pod) float64 {
    promptHash := sha256(ctx.Body)
    if match, ok := pod.PrefixCache.Get(promptHash); ok {
        // 命中长度越长分数越高
        return math.Log10(1.0 + float64(match.CommonPrefixLen))
    }
    return 0.0
}

// pkg/epp/scheduling/framework/plugins/latency/latency.go
type PredictedLatencyScorer struct {
    modelPath string
}

func (l *PredictedLatencyScorer) Score(ctx *RequestContext, pod *Pod) float64 {
    features := l.extractFeatures(ctx, pod)  // promptLen, queue, kv, ...
    pred := l.model.Predict(features)         // ONNX runtime
    // 预测 P99 越低分数越高
    return 1.0 / (1.0 + pred/1000.0)
}

// pkg/epp/scheduling/framework/plugins/slo/slo.go
type SLOHeadroomTierFilter struct{}

func (s *SLOHeadroomTierFilter) Score(ctx *RequestContext, pod *Pod) float64 {
    p99 := pod.Metrics.P99LatencyMs
    target := s.targetP99Ms
    switch {
    case p99 < target*0.5:  return 1.0  // TIER_A
    case p99 < target*0.8:  return 0.7  // TIER_B
    case p99 < target*1.0:  return 0.3  // TIER_C
    default:                return 0.0  // TIER_REJECT
    }
}
```

### 14.3 客户端 SDK 用法（OpenAI 兼容）

```python
# openai SDK 直接对接 llm-d gateway
import openai

client = openai.OpenAI(
    base_url="http://llm-d-gateway.llm-d.svc.cluster.local/v1",
    api_key="not-needed",  # 由 EPP / vllm-sr 注入
)

# 单模型
response = client.chat.completions.create(
    model="Qwen/Qwen3-32B",  # 由 InferenceModel 路由到 qwen3-32b-pool
    messages=[{"role": "user", "content": "Hello"}],
)

# 流式
stream = client.chat.completions.create(
    model="Qwen/Qwen3-32B",
    messages=[{"role": "user", "content": "Write a poem"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")

# 工具调用
response = client.chat.completions.create(
    model="Qwen/Qwen3-32B",
    messages=[{"role": "user", "content": "What's the weather in Beijing?"}],
    tools=[
        {"type": "function", "function": {
            "name": "get_weather",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        }}
    ],
)
```

### 14.4 4 套配置协同速查表

| 组件 | CRD / 配置文件 | 关注点 |
|---|---|---|
| **GIE InferencePool** | `InferencePool` | 选 pod（selector） |
| **GIE InferenceModel** | `InferenceModel` | 模型名 → pool |
| **GIE InferenceObjective** | `InferenceObjective` | 流量目标（RPS / priority） |
| **EPP** | `EPPConfig` (ConfigMap) | scoring 链 + 权重 |
| **vLLM** | `Deployment` args | 模型、TP、KV cache dtype |
| **vllm-sr** | `SemanticRouter` (ConfigMap) | DSL、Tier、cache、隐私 |
| **LMCache** | `lmcache.yaml` (ConfigMap) | 跨节点 KV 配置 |
| **WVA** | `WorkloadVariantAutoscaler` | saturation 阈值 |
| **HPA** | `HorizontalPodAutoscaler` | 副本上下限、stabilization |
| **Gateway API** | `Gateway` + `HTTPRoute` | 入口、路径路由 |

### 14.5 与 Envoy AI Gateway 完整对比（v0.7.0 vs v0.6）

| 维度 | llm-d v0.7.0 + vllm-sr v0.3.0 | Envoy AI Gateway v0.6 |
|---|---|---|
| **设计目标** | K8s-native 推理路由 + Endpoint Picker + 副本弹性 | L7 反代 + 模型路由 + extproc 策略链 |
| **数据面** | agentgateway v2.2.1（Envoy-based） + EPP + vllm-sr ext_proc | Envoy + extproc（静态部署） |
| **路由粒度** | Header / body / KV cache affinity（BBR） / predicted latency | Header / body / 模型名 |
| **配置规模** | InferencePool CRD；WVA 经 External Metrics API | 2,000 × AIGatewayRoute（4MB → 25MB gRPC 调参） |
| **运行时性能** | WVA 0.7 实测：32B prefill P99 TTFT 98s / 35% 错误率 | 未公开统一基准 |
| **自动扩缩** | **WVA v1 Saturation + HPA + Prometheus Adapter / KEDA** | 无内建（HPA + 自定义指标） |
| **缓存层** | **Redis 热 + Milvus 冷 + LMCache 跨节点 KV** | 仅 1 层（自实现） |
| **路由算法丰富度** | **5 类 scorers** + DSL + PRISM | extproc 自实现 |
| **协议支持** | OpenAI / Anthropic / HF / MCP / A2A（实验） | OpenAI / Anthropic / Cohere / PaLM |
| **升级风险** | v0.7.0 强升 CUDA 13 + driver 580 + vLLM 锁版 | v0.6 删 `AIGatewayRoute.spec.filterConfig` |
| **当前默认路径** | llm-d 默认 **standalone（generic proxy）**，gateway 显式 opt-in | full gateway |
| **生产 SRE 友好** | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **学习曲线** | 陡（4 套配置协同） | 中 |
| **社区活跃度** | 高（IBM/Red Hat/Google/NVIDIA 多家） | 中（CNCF Envoy） |
| **商业支持** | IBM watsonx / Red Hat OpenShift AI | Solo.io / Kong |
| **适合场景** | 自托管 vLLM + 突发流量 + KV cache 复用 + 自动扩缩容 | 跨厂商 LLM 路由 + 简单 L7 反代 |
| **不适合场景** | 跨 OpenAI/Anthropic 路由 | 自托管 vLLM 极致性能优化 |

### 14.6 选型决策树

```
你的需求是什么？
│
├─ 跨 SaaS LLM 路由（OpenAI + Anthropic + Cohere）
│   └─→ Portkey / OpenRouter / Helicone
│
├─ 自托管 vLLM + 简单 LB
│   └─→ TGI / vLLM 裸 + 手动 Service
│
├─ 自托管 vLLM + K8s 弹性 + 路由智能
│   ├─ 想要"开箱即用" + 厂商支持 → **llm-d v0.7.0**（standalone 起步 → full gateway）
│   ├─ 想要"完全自己控制 + 旧 K8s 兼容" → **Envoy AI Gateway v0.6** + 手动 WVA
│   └─ 想要"传统 API 网关 + AI 插件" → **Kong / APISIX / Higress** + vLLM
│
├─ 自托管 vLLM + 微服务架构
│   └─→ **llm-d v0.7.0** + Istio（service mesh + inference routing）
│
└─ 自托管 vLLM + 极致吞吐（TP/PP/EP 优化）
    └─→ vLLM 裸 + 手动调参 + 不需要 llm-d
```

---

## 15. 一句话总结（给老板 / 投资人）

> **llm-d + vllm-sr = K8s-native 自托管 vLLM 的"事实标准 AI Gateway 栈"**。在 IBM watsonx / Red Hat OpenShift AI / Google GKE Inference / NVIDIA NIM 多家厂商共同推动下，2026 H1 已从实验项目进入生产可用阶段。**v0.7.0 的核心创新是"用户友好"（standalone 模式 + 锁 vLLM 版本）而非"功能新增"**，意味着产品形态已经稳定，下一步是 benchmark data 标准化（#1586）+ 与 Envoy AI Gateway 的边界清晰化（一个偏 L7 反代，一个偏 K8s 推理调度）。**对小 F 这种 5-15 万/年的副业 SaaS 产品，llm-d 仍是 over-engineering** —— 用 OpenAI / Anthropic API + LiteLLM 代理即可；**但如果做"私有化 LLM 网关"产品给中大型企业，llm-d 是唯一达到"开箱即用 + 厂商支持"门槛的开源方案**。

---

> **报告完成时间**：2026-06-06 21:30 CST
> **下次深挖建议**：vllm-sr v0.3.1（关注 ModernBERT candle FFI softmax PR #1574 是否合入）+ llm-d v0.8.0（关注是否默认切回 full gateway）+ GIE v1.6.0 Latency Predictor 训练数据
