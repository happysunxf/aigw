# 推理引擎与网关协同：vLLM / TGI / Triton 深度解析

> 系列：AI Gateway 持续深挖 · 第 8 篇
> 性质：纯技术研究
> 范围：自托管 LLM 推理引擎的内部原理、与 AI Gateway 的协同、性能优化

---

## 目录

- [一、为什么理解推理引擎对网关设计重要](#一为什么理解推理引擎对网关设计重要)
- [二、LLM 推理的底层挑战](#二llm-推理的底层挑战)
- [三、主流推理引擎全景](#三主流推理引擎全景)
- [四、vLLM 深入](#四vllm-深入)
- [五、TGI（Text Generation Inference）深入](#五tgi-text-generation-inference-深入)
- [六、Triton Inference Server 深入](#六triton-inference-server-深入)
- [七、其他推理引擎](#七其他推理引擎)
- [八、性能对比与选型](#八性能对比与选型)
- [九、推理引擎核心优化技术](#九推理引擎核心优化技术)
- [十、网关与推理引擎的协同模式](#十网关与推理引擎的协同模式)
- [十一、KV Cache 管理深入](#十一kv-cache-管理深入)
- [十二、量化技术深入](#十二量化技术深入)
- [十三、分布式推理](#十三分布式推理)
- [十四、未解难题与研究前沿](#十四未解难题与研究前沿)
- [十五、参考资料](#十五参考资料)

---

## 一、为什么理解推理引擎对网关设计重要

### 1.1 网关与推理引擎的关系

```
AI Gateway
    ↓ HTTP
[推理引擎 vLLM/TGI/Triton]
    ↓ 内部
[GPU]
```

**传统视角**：网关代理请求到推理引擎，理解就此为止。

**深度视角**：网关要"懂"推理引擎才能做对的事：

| 网关需要懂的事 | 例子 |
|---|---|
| **协议细节** | OpenAI 协议 vs 推理引擎原生 API |
| **批处理策略** | 推理引擎是连续批还是静态批？ |
| **KV Cache 行为** | prefix caching 怎么配合？ |
| **流式语义** | SSE chunk 频率、终止信号 |
| **容量规划** | 单实例能服务多少并发？ |
| **Fallback 策略** | 推理引擎挂掉怎么 fallback？ |
| **路由优化** | 同 prefix 的请求路由到同一实例 |
| **资源感知** | 显存、KV cache 利用率 |

### 1.2 推理引擎对网关的"反向要求"

推理引擎也有"希望网关懂"的事：
- **Prompt 标准化**：避免无意义的 prompt 变化导致 KV cache 失效
- **Prefix 友好**：网关能否主动重排请求共享 prefix
- **流式节制**：不要让客户端在流式时压力过大
- **错误透传**：推理引擎的错误码要网关透传

---

## 二、LLM 推理的底层挑战

### 2.1 推理的两个阶段

```
Prefill（预填充）:
  输入：完整 prompt
  操作：一次性处理所有 token
  特点：计算密集（GPU-bound），高吞吐
  时间：100-500ms

Decoding（解码）:
  输入：上一步生成的 token
  操作：逐个生成下一个 token
  特点：内存密集（Memory-bound），低吞吐
  时间：每 token 10-50ms
```

### 2.2 Memory-bound 问题

**关键观察**：Decoding 阶段，GPU 算力很富余，但**内存带宽**成了瓶颈。

```
A100: 80 GB HBM, 2 TB/s 带宽
Llama-70B: 140 GB 权重（FP16），加载要 70ms+
70B 模型的 KV cache（32K context）: ~20GB

内存带宽决定 token 生成速度：
  ~2 TB/s ÷ 模型大小 = 每秒 token 数
```

### 2.3 KV Cache 爆炸

每生成一个 token，需要存所有历史 token 的 K 和 V 矩阵：

```
context_length × num_layers × num_heads × head_dim × 2 (K/V) × 2 (FP16)
= 32K × 80 × 64 × 128 × 2 × 2 = 160 GB (Llama-70B)

远超单卡显存
```

**后果**：
- 长 context 必须分页 / 量化
- 批处理时 KV cache 抢占显存
- 需要精细调度

### 2.4 推理性能的核心指标

| 指标 | 含义 | 行业水平 |
|---|---|---|
| **TTFT** | Time To First Token | 100-500ms |
| **TPOT** | Time Per Output Token | 10-50ms |
| **Throughput** | tokens/s（单卡） | 1k-10k |
| **并发** | 同时处理的请求数 | 10-100+ |
| **Goodput** | 在 SLA 内的吞吐 | 60-90% of peak |

---

## 三、主流推理引擎全景

### 3.1 横向对比

| 引擎 | 维护方 | 语言 | 性能 | 特性 | 适用 |
|---|---|---|---|---|---|
| **vLLM** | UC Berkeley + 社区 | Python + CUDA | ⭐⭐⭐⭐⭐ | PagedAttention、continuous batching | 通用 SOTA |
| **TGI** | HuggingFace | Rust + Python | ⭐⭐⭐⭐ | 生产级、HF 生态 | 企业部署 |
| **Triton** | NVIDIA | C++ / Python | ⭐⭐⭐⭐ | 通用推理服务器、模型编排 | 多模型混合 |
| **SGLang** | UC Berkeley | Python | ⭐⭐⭐⭐⭐ | RadixAttention、Agent 优化 | LLM 程序 |
| **TensorRT-LLM** | NVIDIA | C++ | ⭐⭐⭐⭐⭐ | NVIDIA 极致优化 | NVIDIA 栈 |
| **LMDeploy** | 书生·浦语 | Python + C++ | ⭐⭐⭐⭐ | 国产、量化好 | 国内 |
| **llama.cpp** | 社区 | C++ | ⭐⭐⭐ | CPU / 量化 | 边缘 / 个人 |
| **MLC-LLM** | 社区 | Python + TVM | ⭐⭐⭐ | 端侧编译 | 移动端 |
| **CTranslate2** | 社区 | C++ | ⭐⭐⭐ | 翻译 / 紧凑 | 翻译类 |
| **DeepSpeed-MII** | Microsoft | Python | ⭐⭐⭐⭐ | ZeRO 推理 | 微软栈 |
| **OpenLLM** | BentoML | Python | ⭐⭐⭐ | 简单易用 | 入门 |

### 3.2 历史脉络

```
2022: HuggingFace Transformers (baseline)
2023 Q1: vLLM 发布（PagedAttention）
2023 Q2: TGI（生产化）
2023 Q3: TensorRT-LLM（NVIDIA 极致）
2024 Q1: SGLang（程序化推理）
2024 Q2: LMDeploy、DeepSpeed-MII
2025:    性能趋同，开始拼生态
```

---

## 四、vLLM 深入

### 4.1 核心创新：PagedAttention

**问题**：传统 KV cache 是连续的显存块。

```python
# 传统
request_1 = KVCache(0-4096)        # 预占 4096 显存
request_2 = KVCache(4096-8192)
...
# 浪费严重
```

**PagedAttention 解决**：把 KV cache 分成"页"（类似操作系统虚拟内存）。

```python
# 分页
request_1 = [Page1, Page5, Page9, ...]   # 物理页不连续
request_2 = [Page2, Page3, ...]
# 显存按需分配，无浪费
```

**效果**：
- 显存利用率从 20-40% 提升到 90%+
- 批处理大小提升 4-24x
- 吞吐量提升 14-24x

### 4.2 Continuous Batching

**传统静态批**：

```
请求 1: |--生成 100 tokens--|
请求 2:        |--生成 100 tokens--|
请求 3:                  |--生成 100 tokens--|
                       ↑ 请求 1 完成才能开始
```

**Continuous Batching**（vLLM 创新）：

```
请求 1: |--生成 100 tokens--|✓
请求 2:        |--生成 100 tokens--|✓
请求 3:                  |--生成 100 tokens--|✓
       ↑ 请求 1 完成后立即接受新请求
```

**效果**：GPU 几乎不空闲，吞吐提升 2-3x。

### 4.3 架构

```
vLLM Engine
├── Model Executor（模型执行器）
│     ├── GPU Worker
│     │     ├── 模型权重
│     │     ├── KV Cache Manager（PagedAttention）
│     │     └── Sampling（采样）
│     └── CPU Scheduler
├── Block Manager（KV cache 分页管理）
├── Tokenizer
├── API Server
│     ├── /v1/chat/completions（OpenAI 协议）
│     ├── /v1/completions
│     └── /v1/embeddings
└── Distributed（多 GPU 通信）
```

### 4.4 部署方式

```python
# 命令行
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 32768 \
    --enable-prefix-caching

# OpenAI 协议默认监听 8000 端口
```

### 4.5 Prefix Caching

```python
# vLLM 自动检测共享 prefix
# 相同 prefix 复用 KV cache

# 启用
vllm serve ... --enable-prefix-caching
```

**原理**：
```
请求 1: [system: 长 system prompt] [user: Q1]
        ↓ KV cache [system] 存住
请求 2: [system: 长 system prompt] [user: Q2]
        ↓ 复用 system KV cache，只算 Q2
```

**网关层配合**：
```python
# 网关可以把 system prompt 放最前
# 让所有请求共享 system KV cache
def build_request(messages):
    # 把 system 提到最前
    system = next((m for m in messages if m.role == "system"), None)
    rest = [m for m in messages if m.role != "system"]
    return [system] + rest
```

---

## 五、TGI（Text Generation Inference）深入

### 5.1 架构特点

```
TGI (Rust + Python)
├── HTTP/gRPC Server (Rust)
│     • 高并发、低延迟
├── Python Worker
│     • 模型推理
├── Scheduler
│     • 连续批处理
├── Quantization
│     • bitsandbytes / GPTQ / AWQ
└── Prometheus metrics
```

**优势**：Rust 写的 HTTP 服务器，并发能力强，**生产级稳定性**。

### 5.2 部署

```bash
# Docker
docker run --gpus all -p 8080:80 \
    ghcr.io/huggingface/text-generation-inference:latest \
    --model-id meta-llama/Llama-3.1-70B-Instruct \
    --num-shard 4 \
    --max-input-length 32768 \
    --max-total-tokens 40960
```

### 5.3 协议

TGI 早期有自己协议，**新版已支持 OpenAI 协议**：

```bash
# OpenAI 兼容 API
curl http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "meta-llama/Llama-3.1-70B-Instruct",
        "messages": [...],
        "stream": true
    }'
```

### 5.4 与 vLLM 的差异

| 维度 | vLLM | TGI |
|---|---|---|
| 性能 | 略胜 | 略低 |
| 稳定性 | 社区版 | 企业级 |
| 易用性 | Python 友好 | 配置丰富 |
| 多 GPU 扩展 | tensor parallel | tensor/pipeline |
| 生态 | 学术 / 创业 | HuggingFace / 企业 |
| Rust | 仅 C++/CUDA | Rust 异步 I/O |

---

## 六、Triton Inference Server 深入

### 6.1 定位不同

**vLLM / TGI**：专门做 LLM  
**Triton**：通用推理服务器，LLM 只是其一种 backend

```
Triton
├── Backend
│     ├── TensorRT（NVIDIA 极致）
│     ├── TensorRT-LLM（LLM 专用）
│     ├── vLLM（通过 backend）
│     ├── ONNX Runtime
│     ├── PyTorch (TritonTorch)
│     ├── Python（自定义）
│     └── FIL (TensorFlow)
├── Model Store
└── HTTP/gRPC Server
```

### 6.2 核心特性

#### 特性 1：模型编排

```python
# 一个 Triton 实例跑多个模型
config.pbtxt:
  - "llama-3-70b"
  - "embedding-bge-large"
  - "classifier-bert"
  - "guardrail-llamaguard"
```

#### 特性 2：BLS（Business Logic Scripting）

```python
# 在 Triton 内部编排多个模型
# 实现"先做 Guardrails，再 LLM"的流程

def execute(requests):
    # 第一步：Guardrail
    guard_input = prepare_input(requests)
    guard_output = triton.invoke("guardrail-llamaguard", guard_input)
    if not guard_output.is_safe:
        return rejection_response()
    
    # 第二步：LLM
    llm_output = triton.invoke("llama-3-70b", guard_input)
    return llm_output
```

#### 特性 3：动态批处理

```
Triton 自动选择最佳 batch size
不同模型用不同调度策略
```

#### 特性 4：模型版本管理

```bash
# 同时跑多个版本
models/
├── llama-3/
│   ├── 1/
│   ├── 2/
│   └── 3/
```

### 6.3 LLM 用 Triton 的"性价比"

| 优势 | 劣势 |
|---|---|
| 多模型混合部署 | LLM 性能不如 vLLM 极致 |
| 统一管理 | 配置复杂 |
| 企业级特性 | 学习曲线陡 |
| NVIDIA 优化 | 强依赖 NVIDIA |

**结论**：需要多模型（LLM + embedding + 传统 ML）一起用时，Triton 强；纯 LLM 场景，vLLM 更优。

---

## 七、其他推理引擎

### 7.1 SGLang

**特色**：面向 LLM 程序的 runtime。

```python
# SGLang 的 RadixAttention
# 自动检测 LLM 程序中的共享 prefix
# 优化 multi-turn、agent、tree-of-thought
```

**优势**：
- **RadixAttention**：基于前缀树的 KV cache 复用
- **结构化生成**：JSON / regex 约束
- **Agent 友好**：原生的 chain、branch 支持

**适用**：复杂 LLM 程序（Agent、Tree of Thought）。

### 7.2 TensorRT-LLM

**特色**：NVIDIA 自家极致优化。

```
TensorRT-LLM 优化
├── Layer Fusion（算子融合）
├── Kernel Auto-tuning
├── In-flight Batching
├── Quantization (INT4/INT8)
├── Paged KV Cache
├── Speculative Decoding
└── Multi-GPU / Multi-Node
```

**优势**：性能最强（A100 / H100 上）
**劣势**：编译时间长、配置复杂、仅 NVIDIA

### 7.3 LMDeploy

**特色**：上海 AI Lab 书生·浦语团队开发。

```
LMDeploy 优化
├── Persistent Batch
├── Quantization (4-bit)
├── Dynamic Patching
├── Multi-model
└── TurboMind 引擎
```

**优势**：国产、量化激进、社区响应快
**劣势**：生态相对小

### 7.4 llama.cpp

**特色**：C++ 写，CPU / 边缘 / 个人使用。

```bash
# Mac M2 上跑 Llama-3-8B
./main -m llama-3-8b.Q4_K_M.gguf \
    -p "Hello" \
    -n 200
```

**优势**：
- CPU / Mac / 手机 / Raspberry Pi 都能跑
- GGUF 格式跨平台
- 量化成熟

**劣势**：不适合大模型、不适合高并发

---

## 八、性能对比与选型

### 8.1 性能基准

来自 vLLM 团队 2024 年论文：

| 引擎 | 相对吞吐 | TTFT | 备注 |
|---|---|---|---|
| **vLLM** | 100% (基线) | 100% | |
| **TGI** | 80-90% | 95-110% | |
| **SGLang** | 90-110% | 90-100% | LLM 程序场景超过 vLLM |
| **TensorRT-LLM** | 100-130% | 90-100% | NVIDIA 上 |
| **LMDeploy** | 80-100% | 100% | |
| **Transformers (HF)** | 10-20% | 150% | baseline |

### 8.2 选型决策树

```
需求？
├── 大模型 + 高并发 + SOTA 性能
│     → vLLM
├── 企业级稳定 + HF 生态
│     → TGI
├── NVIDIA 极致性能 + 长 context
│     → TensorRT-LLM
├── 复杂 LLM 程序 (Agent, ToT)
│     → SGLang
├── 多模型混合 (LLM + 传统 ML)
│     → Triton
├── 国产化 / 信创
│     → LMDeploy
├── 边缘 / CPU / 个人
│     → llama.cpp
└── 移动端
      → MLC-LLM
```

---

## 九、推理引擎核心优化技术

### 9.1 KV Cache 优化技术

#### 技术 1：PagedAttention（vLLM）

```
分页管理 KV cache
类似 OS 虚拟内存
显存利用率 90%+
```

#### 技术 2：RadixAttention（SGLang）

```
前缀树管理
自动检测 LLM 程序中的共享 prefix
```

#### 技术 3：Prefix Caching（vLLM / TGI / TRT-LLM）

```
相同 prefix 的请求共享 KV cache
减少重复计算
```

#### 技术 4：Quantized KV Cache

```
KV cache 也量化
INT8 / INT4 KV cache
显存再省 2-4x
```

#### 技术 5：KV Cache 卸载

```
CPU 内存 / NVMe 存溢出 KV cache
适合超长 context
```

### 9.2 批处理优化

| 优化 | 描述 | 引擎 |
|---|---|---|
| **Continuous Batching** | 请求粒度的批处理 | vLLM, TGI, SGLang |
| **In-flight Batching** | 边生成边接受新请求 | TRT-LLM |
| **Dynamic Batching** | 动态调整 batch size | Triton |
| **Persistent Batch** | 批处理常驻 | LMDeploy |

### 9.3 注意力优化

#### 优化 1：FlashAttention

```
IO-aware attention
O(N) 内存
速度 2-4x
```

#### 优化 2：Multi-Query Attention (MQA)

```
多个 Q head 共享 1 个 K/V head
KV cache 减少 8-32x
```

#### 优化 3：Grouped-Query Attention (GQA)

```
Q head 分组共享 K/V
KV cache 减少 4-8x
Llama-2-70B / Llama-3 用
```

#### 优化 4：Paged Flash Attention

```
FlashAttention + PagedAttention
vLLM 实现
```

### 9.4 Speculative Decoding

```
小模型快速生成 N 个候选 token
大模型一次性验证 N 个 token
加速 2-3x
```

```python
# 例子
draft_model.generate("The quick brown", max_tokens=5)
# → ["The", "quick", "brown", "fox", "jumps"]
main_model.verify(["The", "quick", "brown", "fox", "jumps"])
# → 接受前 4 个，第 5 个拒绝，重新生成
```

### 9.5 模型并行

```
Tensor Parallel（层内切分）:
  - 适合：单模型超大
  - 通信：NVLink 必备

Pipeline Parallel（按层切分）:
  - 适合：多机部署
  - 通信：网络即可

Sequence Parallel（按 seq 切分）:
  - 适合：长 context
  - 通信：低

Expert Parallel（MoE 切分）:
  - 适合：MoE 模型
  - 每个 GPU 存部分 expert
```

---

## 十、网关与推理引擎的协同模式

### 10.1 模式 A：透明代理

```
AI Gateway → (HTTP) → 推理引擎
```

**网关做的事**：
- 协议转换（如果有）
- 鉴权
- 限流
- 缓存
- 日志

**推理引擎做的**：
- 所有推理相关

**优点**：简单
**缺点**：网关无法利用推理引擎的"内部状态"

### 10.2 模式 B：协议透传 + 头部注入

```
AI Gateway → (HTTP + X-Header) → 推理引擎
```

**示例**：
```python
# 网关在 header 里告诉推理引擎用户信息
request.headers["X-User-Id"] = "user-123"
request.headers["X-Routing-Hint"] = "high_priority"
```

**用途**：让推理引擎做 user-aware 的优化。

### 10.3 模式 C：Prefix 感知路由

```python
# 网关根据 system prompt 路由
def route(request, vllm_instances):
    system_hash = hash(request.messages[0].content)
    
    # 同一 system 路由到同一实例
    instance = vllm_instances.get_instance_by_prefix(system_hash)
    if instance:
        return instance
    
    # 没有就负载均衡
    return vllm_instances.least_busy()
```

**效果**：显著提升 prefix caching 命中率。

### 10.4 模式 D：推理引擎 API 直接调用

```python
# 网关不只是代理，而是直接调用推理引擎的 Python API
from vllm import LLM, SamplingParams

# 共享同一个 vllm 实例
class Gateway:
    def __init__(self):
        self.llm = LLM("meta-llama/Llama-3.1-70B")
    
    async def process(self, request):
        # 直接用 vllm API
        sampling = SamplingParams(
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        result = self.llm.generate([request.prompt], sampling)
        return result
```

**优点**：避免 HTTP 序列化、延迟最低
**缺点**：紧耦合、不适合多推理引擎

### 10.5 模式 E：Triton BLS 编排

```
AI Gateway → Triton
              ↓
            [Guardrail Model] → [LLM Model] → [Post-process Model]
            (在 Triton 内部完成)
```

**优点**：复杂编排
**缺点**：编排逻辑锁在 Triton

### 10.6 模式 F：分层部署

```
AI Gateway
├── 边缘推理引擎（小模型）
├── 区域推理引擎（中模型）
└── 中心推理引擎（大模型）
    ↓
网关决定路由到哪层
```

---

## 十一、KV Cache 管理深入

### 11.1 KV Cache 生命周期

```
请求开始 → KV cache 分配 → 推理进行中 → 请求结束 → KV cache 释放
                                       ↘ 长 prefix → 缓存保留（prefix cache）
```

### 11.2 显存分配策略

#### 策略 1：预分配

```python
# 启动时分配
max_concurrent = 100
per_request = 2048  # tokens
total_kv = max_concurrent * per_request * layers * 2 * 2  # 4 KB / token
```

**优点**：管理简单
**缺点**：浪费

#### 策略 2：按需分配（vLLM）

```python
# 推理时按需分配 KV cache 页
# 用完即释放
```

**优点**：利用率高
**缺点**：管理复杂

### 11.3 KV Cache 共享

#### 共享 1：Prefix Sharing

```python
# 同一 prefix 的请求共享 KV cache
# vLLM: --enable-prefix-caching
```

#### 共享 2：Beam Search Sharing

```python
# beam search 中不同 beam 共享 prefix
# vLLM: 自动
```

#### 共享 3：Multi-LoRA Sharing

```python
# 多个 LoRA 适配器共享 base model 的 KV cache
```

### 11.4 KV Cache 监控

```python
# 关键指标
{
    "kv_cache_usage": 0.85,            # 使用率
    "kv_cache_free_blocks": 100,        # 空闲块
    "kv_cache_evicted_blocks_per_sec": 5,  # 淘汰速率
    "prefix_cache_hit_rate": 0.42,     # prefix 命中率
}
```

**告警**：
- 使用率 > 95% → 即将 OOM
- 命中率 < 10% → prefix 缓存配置有问题
- 淘汰速率 > 100/s → 缓存太小

---

## 十二、量化技术深入

### 12.1 量化方法对比

| 方法 | 精度 | 适用 | 性能损失 |
|---|---|---|---|
| **FP16** | 16-bit | 基线 | 0% |
| **BF16** | 16-bit | 训练 | 0% |
| **INT8 (PTQ)** | 8-bit | 通用 | < 1% |
| **INT8 (QAT)** | 8-bit | 量化感知 | 0% |
| **GPTQ (INT4)** | 4-bit | 通用 | 1-3% |
| **AWQ (INT4)** | 4-bit | 通用 | 0.5-1.5% |
| **SmoothQuant** | INT8 | 激活敏感模型 | < 1% |
| **GGUF (k-quants)** | 2-8 bit | CPU / 边缘 | 视级别 |
| **BitNet (1-bit)** | 1.58-bit | 极小模型 | 待观察 |

### 12.2 GPTQ vs AWQ

**GPTQ**：
- 按层量化、最小化重构误差
- 需要校准数据
- 量化时间较长（小时级）

**AWQ**：
- 保护"重要权重"不量化
- 不需要校准
- 量化时间短（分钟级）
- 性能略好于 GPTQ

### 12.3 部署

```python
# vLLM 加载 AWQ 量化模型
vllm serve "TheBloke/Llama-3.1-70B-AWQ"

# vLLM 加载 GPTQ
vllm serve "TheBloke/Llama-3.1-70B-GPTQ"

# 自动选择
vllm serve "meta-llama/Llama-3.1-70B" --quantization awq
```

### 12.4 量化对 KV Cache 的影响

```
原始 KV cache: FP16, 2 字节/token
INT8 KV cache: 1 字节/token
INT4 KV cache: 0.5 字节/token

节省 50-75% 显存
```

---

## 十三、分布式推理

### 13.1 张量并行（Tensor Parallel）

```
单个矩阵切到多卡
例：Q 矩阵 (4096 x 4096) 切 4 路
每卡 (4096 x 1024)

需要 NVLink（高速 GPU 间通信）
```

### 13.2 流水线并行（Pipeline Parallel）

```
GPU 0: layer 0-19
GPU 1: layer 20-39
GPU 2: layer 40-59
GPU 3: layer 60-79

气泡：1 / (num_stages) 时间浪费
```

### 13.3 专家并行（Expert Parallel，MoE）

```
Mixtral 8x7B: 8 个 expert，每个 7B
GPU 0: expert 0, 1
GPU 1: expert 2, 3
GPU 2: expert 4, 5
GPU 3: expert 6, 7
```

### 13.4 序列并行（Sequence Parallel）

```
长 context 切分
GPU 0: tokens 0-8192
GPU 1: tokens 8192-16384
```

### 13.5 网关的分布式感知

```python
# 网关理解分布式推理
class InferenceBackend:
    def __init__(self):
        self.instances = [
            {"id": "vllm-0", "tp": 4, "model": "llama-70b"},
            {"id": "vllm-1", "tp": 8, "model": "llama-70b"},
            {"id": "vllm-2", "tp": 1, "model": "llama-8b"},
        ]
    
    def route(self, request):
        # 大请求 → TP 8 实例
        if request.estimated_tokens > 10000:
            return "vllm-1"
        # 小请求 → TP 1 实例
        return "vllm-2"
```

---

## 十四、未解难题与研究前沿

### 14.1 KV Cache

1. **超长 context (1M+ tokens) 的 KV cache 调度**
2. **KV cache 压缩算法**（如 Key-Value eviction）
3. **跨实例 KV cache 共享**——分布式 prefix cache
4. **KV cache 持久化**——会话间复用
5. **KV cache 调度算法**——最优分配策略

### 14.2 性能

6. **Prefill 阶段的延迟优化**
7. **首个 token 延迟**进一步压低
8. **Speculative Decoding 的最优 draft 模型选择**
9. **动态批处理的最优 batch size**
10. **跨引擎的负载调度**

### 14.3 量化

11. **1-bit 模型的可行性**（BitNet）
12. **KV cache 量化**对长 context 的影响
13. **量化模型的微调**（QLoRA 之外的方案）
14. **混合精度**（部分层量化、部分层不量化）
15. **量化对 Agent 任务的影响**——能否仍能调用工具

### 14.4 分布式

16. **跨节点推理**的延迟瓶颈
17. **动态并行策略**——请求级别调整 TP/PP
18. **异构 GPU 集群**调度
19. **专家路由**在分布式下的延迟
20. **跨数据中心推理**

### 14.5 网关协同

21. **Prefix-aware 路由**的最优算法
22. **网关的"模型自发现"**——自动识别可用模型
23. **网关的容量规划**——推理引擎利用率预测
24. **多推理引擎的统一抽象**
25. **推理引擎的热升级**——不停机更新

### 14.6 标准化

26. **推理引擎 API 的标准化**——除了 OpenAI 协议还有吗？
27. **KV cache 状态的标准化**——能否被外部调度
28. **Prefix hash 的标准化**
29. **多推理引擎互操作**

### 14.7 未来形态

30. **推理引擎 + 网关融合**——变成一个产品
31. **自演化推理**——运行时根据流量调整配置
32. **推理引擎的"操作系统"化**——管理 GPU / 内存 / 调度
33. **"推理即服务"**的更细致切分

---

## 十五、参考资料

### 15.1 论文

- "PagedAttention: Virtual Memory for LLM Serving" (vLLM, SOSP 2023)
- "vLLM: Efficient Memory Management for Large Language Model Serving" (Kwon et al., 2023)
- "SGLang: Efficient Execution of Structured Language Model Programs" (Zheng et al., 2024)
- "FlashAttention: Fast and Memory-Efficient Exact Attention" (Dao et al., 2022)
- "Speculative Decoding" (Leviathan et al., 2023)
- "SmoothQuant" (Xiao et al., 2023)
- "AWQ: Activation-aware Weight Quantization" (Lin et al., 2023)
- "BitNet: Scaling 1-bit Transformers for Large Language Models" (Ma et al., 2024)
- "LLM Inference Unveiled: Survey and Roofline Model Insights" (Yuan et al., 2024)

### 15.2 仓库

- github.com/vllm-project/vllm
- github.com/huggingface/text-generation-inference
- github.com/triton-inference-server/server
- github.com/sgl-project/sglang
- github.com/NVIDIA/TensorRT-LLM
- github.com/InternLM/lmdeploy
- github.com/ggerganov/llama.cpp
- github.com/mlc-ai/mlc-llm

### 15.3 博客

- vLLM 团队博客
- HuggingFace "TGI in production"
- NVIDIA "TensorRT-LLM Optimization"
- SGLang 团队博客
- Anyscale "How vLLM works"
- Modal "LLM inference optimization"

### 15.4 基准测试

- github.com/vllm-project/vllm/tree/main/benchmarks
- github.com/InternLM/lmdeploy#benchmark
- llm-perf.github.io

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 8 篇
- 主题：推理引擎与网关协同
- 上一份：07-edge-ai-gateway.md
- 下一份预告：多模态（图像 / 语音 / 视频）网关的现状与挑战
