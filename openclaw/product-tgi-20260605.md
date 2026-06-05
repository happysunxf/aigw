# TGI 深度调研报告（Text Generation Inference）

> 调研对象：HuggingFace Text Generation Inference（TGI）
> 调研视角：把 TGI 当作一个 **"自托管 LLM 推理网关"** 来解构 —— 它既是 Rust/Python 混合的高性能推理服务器，又通过 OpenAI 兼容 Messages API、Prometheus 指标、OpenTelemetry 追踪、Token 流式 SSE 协议，扮演"准网关"角色；同时也是 HuggingFace 整个 Inference Endpoints 商业产品的底层引擎
> 调研时间：2026-06-05
> 数据截止：TGI v3.3 系列（最新 v3.3.5+ 容器；进入维护模式，主线向 vLLM / SGLang 让位）

---

## 0. 阅读地图

```
1.  项目背景与现状         ─── HF 旗舰推理项目 → 维护模式，向 vLLM/SGLang 过渡
2.  核心架构              ─── Router + Python gRPC Backend + Rust 内核
3.  代码级组件剖析         ─── launcher / router / server / pb / pb2
4.  协议支持矩阵           ─── /generate /generate_stream /v1/chat/completions /v1/...
5.  性能优化技术栈         ─── Flash/Paged Attn / 连续批处理 / 推测解码 / 量化
6.  性能数据              ─── 论文 / 2024-2026 社区 benchmark
7.  分布式 / 张量并行      ─── TP / 多 GPU / 多节点
8.  量化与硬件加速         ─── bitsandbytes / GPTQ / AWQ / Marlin / FP8 / EETQ
9.  推测解码              ─── Medusa / n-gram / 双模型 Draft
10. 推测解码 + Guidance    ─── 结构化输出（JSON/正则）
11. Gateway 视角能力      ─── Router 路由 / 指标 / 鉴权 / fallback
12. 部署方式              ─── Docker / k8s / HF Inference Endpoints / Nix
13. 成本模型              ─── 自托管 vs HF Endpoints vs API
14. 生态与集成             ─── transformers / optimum / LangChain / LlamaIndex
15. 客户案例               ─── HF Chat / Adyen / AWS / IBM / 一线 SaaS
16. 维护模式与社区         ─── 当前贡献门槛、未来路径
17. 优劣 / 风险 / 反模式
18. 与 vLLM / SGLang / LMDeploy / Triton / llama.cpp 对比
19. 2026-2027 路线图（推测）
20. 关键参考与一手资料
```

---

## 1. 项目背景与现状

### 1.1 一句话定位

> **TGI = HuggingFace 出品的、生产级、自托管 LLM 推理服务器，Rust 内核 + Python gRPC 后端 + 丰富硬件/量化支持，是 HuggingFace 自身 HuggingChat、Inference API、Inference Endpoints 的底层引擎。**

### 1.2 发展时间线

| 时间 | 事件 |
|---|---|
| 2022 Q4 | HuggingFace 内部项目启动（替代之前的 Python pipeline） |
| 2023-02 | 首次开源（v0.x），主打 Falcon / StarCoder / BLOOM 推理 |
| 2023 H1 | 引入连续批处理（Continuous Batching）、PagedAttention、Flash Attention |
| 2023 H2 | 接入 Messages API（OpenAI Chat Completion 兼容） |
| 2024 Q1 | v2.x：Marlin kernel、AWQ、bitsandbytes 4bit；Adyen 公开生产案例 |
| 2024 Q2 | v2.3+：H100 / H200 FP8 优化、推测解码、Guidance 集成 |
| 2024 Q3 | 分布式追踪（OpenTelemetry）、Prometheus 全面化 |
| 2024 Q4 | Nix 安装路径、Speculation API 进入稳定 |
| 2025 H1 | v3.x：Messages API 默认开启；与 HF Hub 深度整合（私有/gated 模型） |
| 2025 H2 | **进入维护模式（maintenance mode）** —— HF 官方公告 vLLM/SGLang 是主推方向 |
| 2026-至今 | 仅接受 bug fix / 文档改进类 PR；不再添加大特性 |

### 1.3 维护模式的意义

> "TGI has initiated the movement for optimized inference engines to rely on a transformers model architectures. This approach is now adopted by downstream inference engines, which we contribute to and recommend using going forward: vllm, SGLang, as well as local engines with inter-compatibility such as llama.cpp or MLX."  
> —— 官方 README，2025 H2

**真实含义**：
- **不退市**：Docker 镜像、Issues、PR review 依然活跃；HF Endpoints / HF Inference API 仍在底层用 TGI
- **战略调整**：HF 把"社区创新"的位置让给 vLLM / SGLang，TGI 回归"HF 内部生产引擎 + 稳定企业部署选项"
- **对用户影响**：现有 TGI 部署不需急迁，但**新项目首选 vLLM/SGLang**，TGI 更适合"已锁定 HF 生态/需要 HF 商业支持"场景

### 1.4 治理与许可证

| 维度 | 详情 |
|---|---|
| 仓库 | `github.com/huggingface/text-generation-inference` |
| 协议 | Apache 2.0 |
| 治理方 | HuggingFace 公司 + 社区（核心 maintainer ~6 人） |
| SLA | 无官方承诺（开源），但 HF Inference Endpoints 商业层有 SLA |
| 商业关系 | TGI 是 **HuggingFace Inference Endpoints / Dedicated Endpoints** 的引擎之一（与 vLLM、TEI 并列） |

### 1.5 目标用户

- **首选 TGI 的**：
  1. HuggingChat / 内部产品需要快速自托管的开源模型团队
  2. 已采购 HF Enterprise 合约、需要 HF 官方支持的客户
  3. 强依赖 transformers 模型架构（HF 完整模型库），需要与 `transformers` 代码 1:1 对齐
  4. 多硬件（NVIDIA / AMD / Inferentia / Gaudi / Intel GPU）一站式部署
- **更推荐 vLLM/SGLang 的**：
  1. 追求极致吞吐 / 推测解码 / 复杂结构化输出
  2. DeepSeek-V3 / Qwen3 / Llama-4 等最新模型的 SOTA 推理性能
  3. 学术研究 / Benchmark 复现

---

## 2. 核心架构

### 2.1 总体架构图（ASCII）

```
                        ┌─────────────────────────────────────┐
                        │       TGI Process (text-            │
                        │   generation-launcher 进程)          │
                        └─────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
   ┌────▼─────┐                  ┌──────▼──────┐                ┌───────▼──────┐
   │  Router  │  HTTP (Actix)    │  Python     │  gRPC (Tonic)  │  Rust/CUDA   │
   │  (Rust)  │  ───────────────▶│  Backend    │  ─────────────▶│  Kernels     │
   │  :8080   │                  │  (server.py)│                │  (custom)    │
   └────┬─────┘                  └──────┬──────┘                └───────┬──────┘
        │                               │                               │
        │                               │                               │
   ┌────▼───────────────────────────────▼───────────────────────────────▼────┐
   │                      Model Weights (Safetensors / GGUF)                  │
   │                    在 GPU 显存 + CPU pinned memory 中                     │
   └──────────────────────────────────────────────────────────────────────────┘
        │                               │                               │
   ┌────▼─────┐                  ┌──────▼──────┐                ┌───────▼──────┐
   │  /metrics│                  │  /v1/chat/  │                │  /generate   │
   │  (Prom)  │                  │  completions│                │  (HF 原生)   │
   └──────────┘                  └─────────────┘                └──────────────┘
        │                               │
   ┌────▼─────┐                  ┌──────▼──────┐
   │ OpenTel  │                  │  SSE        │
   │ (OTLP)   │                  │  (text/event-stream)
   └──────────┘                  └─────────────┘
```

### 2.2 三大组件职责

| 组件 | 语言 | 职责 | 关键 crate / lib |
|---|---|---|---|
| **Router（`router/`）** | Rust | HTTP 入口；请求解析、批处理调度、metrics、Auth、token-by-token 流式响应 | Actix-Web、Tonic client、Prometheus exporter、tokenizers |
| **Python Backend（`server/text_generation_server/`）** | Python + PyTorch + custom CUDA | 实际跑模型 forward；管理 KV cache；连续批处理循环；推测解码 draft 模型 | PyTorch、HuggingFace transformers fork、flash-attn、custom CUDA kernels、Marlin |
| **共享 Proto（`proto/v3/generate.proto`）** | Protobuf | Router ↔ Python Backend 通信协议；定义 Batch / GenerateRequest / Speculative decoding 等消息 | grpc-python、tonic (Rust) |

### 2.3 进程模型

```
┌──────────────────────────────────────────────────────────────┐
│                       launcher / 启动流程                       │
│                                                              │
│  1. text-generation-launcher 启动                              │
│  2. 派生 Python 子进程（server）── gRPC server @ localhost:8033│
│  3. 派生 1 个 / N 个 Router 子进程（shard 数 = num_shard）    │
│     ◦ 每个 Router 监听 1 个或多个 HTTP 端口                     │
│     ◦ 所有 Router 通过 gRPC 客户端连接同一个 Python Backend     │
│  4. 健康检查：/health 端点在 Python 启动 + 权重加载完成后返回 200│
└──────────────────────────────────────────────────────────────┘
```

**关键参数**：
- `--num-shard N`：将模型切到 N 个 GPU（每卡一份 TP shard）；默认 1
- `--shard-uds-path`：Unix Domain Socket 路径，Router ↔ Backend 通信（避免 TCP 开销）
- `--max-total-tokens`：连续批处理可同时容纳的最大 token 数
- `--max-waiting-tokens`：批处理队列容量上限

### 2.4 与传统 HuggingFace `pipeline.generate` 的区别

```
┌──────────────────────────────────────────────────────────────────────┐
│  ❌ 旧方式：transformers pipeline                                      │
│  ┌────────────────┐                                                 │
│  │  Python 进程    │                                                 │
│  │  ├─ tokenizer   │                                                 │
│  │  ├─ model       │  单请求 → generate() → 等到 EOS → 返回          │
│  │  └─ logits proc │  GPU 利用率：经常 < 30%（等待 tokenize / 解码）  │
│  └────────────────┘                                                 │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  ✅ TGI 方式                                                           │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐      │
│  │  Router (Rust) │ →  │  Python gRPC   │ →  │  CUDA Kernels  │      │
│  │  • 请求合并     │    │  • 连续批处理   │    │  • Flash Attn  │      │
│  │  • token 解析   │    │  • KV cache    │    │  • Paged Attn  │      │
│  │  • SSE 推送     │    │  • 推测解码     │    │  • Marlin GPTQ │      │
│  └────────────────┘    └────────────────┘    └────────────────┘      │
│  GPU 利用率：经常 > 70-90%（高并发时）                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.5 通信协议细节（gRPC messages）

```protobuf
// proto/v3/generate.proto (简化版)
service TextGenerationService {
  rpc ClearCache(VoidParameters) returns (ClearCacheResponse);
  rpc ModelInfo(VoidParameters) returns (ModelInfoResponse);
  rpc Generate(Batch) returns (GeneratedText);  // 单条
  rpc GenerateStream(Batch) returns (stream GeneratedStream);  // 流式
  rpc Prefill(Batch) returns (PrefillTokens);
}

message Batch {
  uint32 id = 1;
  repeated uint32 requests = 2;        // token id 序列
  uint32 max_tokens = 3;
  SamplingParams sampling_params = 4;
  bool do_sample = 5;
  // ...
}

message GeneratedStream {
  oneof msg {
    GeneratedText token = 1;
    GeneratedStats stats = 2;
  }
}
```

**Router 端用 Tonic（Rust gRPC）客户端**：
```rust
// router/src/lib.rs 简化
use tonic::transport::Channel;

pub struct Infer {
    client: TextGenerationServiceClient<Channel>,
    queue: VecDeque<Request>,
}

impl Infer {
    pub async fn generate_stream(&mut self, req: Request) -> Result<...> {
        let batch = Batch { id: req.id, requests: req.tokens, ... };
        let mut stream = self.client.generate_stream(batch).await?.into_inner();
        while let Some(resp) = stream.message().await? {
            match resp.msg {
                Some(GeneratedStream::Msg::Token(t)) => { /* SSE push */ },
                Some(GeneratedStream::Msg::Stats(s)) => { /* 指标 */ },
                None => break,
            }
        }
    }
}
```

---

## 3. 代码级组件剖析

### 3.1 仓库目录结构

```
text-generation-inference/
├── launcher/                      # Rust 启动器
│   ├── src/main.rs                # CLI 入口
│   ├── src/lib.rs
│   └── src/
│       ├── download.rs            # HF Hub 模型下载
│       └── server.rs              # 派生 Python 子进程
├── router/                        # Rust HTTP Router
│   ├── src/
│   │   ├── main.rs                # Router 入口
│   │   ├── lib.rs                 # 核心 Infer / queue
│   │   ├── validation.rs          # 请求 schema
│   │   ├── health.rs              # /health
│   │   ├── metrics.rs             # Prometheus
│   │   ├── otel.rs                # OpenTelemetry
│   │   ├── auth.rs                # API key
│   │   ├── speculation.rs         # 推测解码
│   │   ├── tool_parsers.rs        # Tool/Function call 解析
│   │   └── websocket.rs           # WS 支持
│   └── Cargo.toml
├── server/                        # Python gRPC Backend
│   ├── text_generation_server/
│   │   ├── server.py              # gRPC server 主循环
│   │   ├── models/__init__.py
│   │   ├── models/model.py        # 抽象基类
│   │   ├── models/flash_vlm.py    # 多模态
│   │   ├── models/llama.py        # Llama 系
│   │   ├── models/mistral.py      # Mistral
│   │   ├── models/gemma.py        # Gemma
│   │   ├── models/qwen2.py        # Qwen
│   │   ├── models/phi3.py         # Phi-3
│   │   ├── models/deepseek_v3.py  # DeepSeek-V3 (MoE)
│   │   ├── layers/                # 自定义 kernel 包装
│   │   │   ├── attention/
│   │   │   │   ├── paged.py       # PagedAttention
│   │   │   │   └── flashinfer.py  # FlashInfer
│   │   │   ├── moe.py             # Mixture of Experts
│   │   │   ├── quantization/      # bitsandbytes / GPTQ / AWQ / Marlin / FP8
│   │   │   ├── speculative.py     # 推测解码
│   │   │   └── ...
│   │   ├── utils/
│   │   │   ├── batch.py           # Batch 构造
│   │   │   ├── tokens.py          # 采样 / logit warp
│   │   │   ├── weights.py         # Safetensors 加载
│   │   │   └── prefix_cache.py    # 静态/动态 prefix cache
│   │   └── pb/                    # 生成的 protobuf Python stub
│   ├── pb2/
│   │   ├── generate.proto
│   │   └── generate_pb2.py
│   └── cli.py
├── proto/v3/
│   └── generate.proto
├── Dockerfile                     # 多 stage：Rust + Python + CUDA
├── docker-compose.yml
├── Makefile
└── README.md
```

### 3.2 启动流程代码

```python
# server/text_generation_server/server.py (核心循环)
class TextGenerationServer:
    def __init__(self, model_id: str, ...):
        # 1. 加载 tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, ...)
        # 2. 实例化模型（按架构路由到具体类）
        self.model = get_model(model_id, model_class, quantize=..., ...)
        # 3. 构造 scheduler
        self.scheduler = Scheduler(
            max_batch_size=args.max_batch_size,
            max_total_tokens=args.max_total_tokens,
            max_waiting_tokens=args.max_waiting_tokens,
        )
        # 4. 启动 gRPC
        self.server = grpc.server(fork_server())
        add_TextGenerationServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port(f"unix://{uds_path}")
        self.server.start()

    async def Generate(self, request, context):
        # 1. 构造 Batch 对象
        batch = self.batch_factory.from_pb(request)
        # 2. 放入 scheduler
        gen, batch_id = await self.scheduler.add_waiting_batch(batch)
        # 3. 等待生成（这里可以做推测解码、prefill、decode）
        async for response in gen:
            yield response
```

### 3.3 连续批处理（Continuous Batching）实现

```python
# server/text_generation_server/utils/scheduler.py (简化)
class Scheduler:
    def __init__(self, max_batch_size, max_total_tokens, max_waiting_tokens):
        self.waiting_queue: Deque[Batch] = deque()
        self.active_batch: Optional[Batch] = None
        self.max_batch_size = max_batch_size
        self.max_total_tokens = max_total_tokens
        self.max_waiting_tokens = max_waiting_tokens

    async def add_waiting_batch(self, batch):
        # 计算 batch token 总数
        if batch.total_tokens > self.max_waiting_tokens:
            batch = batch.truncate(max_total_tokens)
        self.waiting_queue.append(batch)
        return self.active_batch_queue.get(), batch.id

    async def schedule(self):
        """每个 decode step 调用一次"""
        # 1. 把 waiting 队列里能塞下的塞进 active
        while self.waiting_queue and self._can_add(self.waiting_queue[0]):
            batch = self.waiting_queue.popleft()
            self.active_batch.add(batch)
        # 2. 触发 model forward
        generations, prev_batch = self.model.generate_token(self.active_batch)
        # 3. 把已完成请求的 slot 标记为可重用
        self.active_batch.filter(generations)
        # 4. 处理 speculative decoding 验证
        # ...
```

**核心思想**：每个 decode 步骤都重新评估 batch 组成 —— 完成的请求立刻释放 slot，新请求可即时加入，无需等所有请求结束。

### 3.4 推测解码（Speculative Decoding）

```python
# server/text_generation_server/layers/speculative.py
class MedusaModel:
    """Medusa 多头预测：让模型一次预测未来 K 个 token"""
    def __init__(self, base_model, medusa_heads=4):
        self.base_model = base_model
        # 每个 Medusa head 是一个小 linear 层
        self.medusa_heads = nn.ModuleList([
            nn.Linear(hidden_size, vocab_size, bias=False) 
            for _ in range(medusa_heads)
        ])

    def forward(self, input_ids, ...):
        # 1. base model 正常前向
        hidden_states = self.base_model(input_ids).last_hidden_state
        # 2. K 个 head 各自预测未来 token
        medusa_logits = [head(hidden_states) for head in self.medusa_heads]
        # 3. 在 decode 阶段，用这些 draft 做 tree-based verify
        return base_logits, medusa_logits
```

**Tree verify 流程**：
```
1. Draft 阶段：Medusa 生成 K 个候选 token，组合成 "speculative tree"
2. Verify 阶段：一次 forward 同时验证所有 draft 路径
3. Accept 阶段：按概率接受或拒绝，rejected 部分回滚 + resample
效果：典型 2x 加速（Adyen 实测 1.6-2.4x）
```

### 3.5 PagedAttention 实现

```python
# server/text_generation_server/layers/attention/paged.py
# 借鉴 vLLM 思路，KV cache 分页管理
class PagedAttention:
    def __init__(self, block_size=16, num_blocks=...):
        self.block_size = block_size
        # 物理 block 池
        self.block_pool = torch.empty(num_blocks, block_size, num_heads, head_dim)
        # 逻辑 → 物理 block 映射
        self.block_table = []

    def allocate(self, seq_len):
        num_blocks_needed = ceil(seq_len / self.block_size)
        physical_blocks = self.free_blocks[:num_blocks_needed]
        self.free_blocks = self.free_blocks[num_blocks_needed:]
        return physical_blocks

    def forward(self, q, k, v, block_table):
        # 用 block_table 把分散的物理 block 重组为逻辑 KV
        # 调用 PagedAttention CUDA kernel
        return paged_attn_kernel(q, k, v, block_table, self.block_size)
```

### 3.6 量化实现路径

```python
# server/text_generation_server/layers/quantization/__init__.py
def get_quantize_fn(quantize_type: str):
    return {
        "bitsandbytes": load_bitsandbytes,    # NF4 / FP4 / INT8
        "bitsandbytes-nf4": load_bitsandbytes,
        "bitsandbytes-fp4": load_bitsandbytes,
        "gptq": load_gptq,                    # GPTQ (4/8 bit)
        "awq": load_awq,                      # AWQ
        "marlin": load_marlin,                 # Marlin kernel (FP16xINT4)
        "eetq": load_eetq,                    # EETQ (INT8)
        "fp8": load_fp8,                      # FP8 (H100/H200)
    }[quantize_type]
```

每个 loader 会：
1. 读取 config.json / quantization_config.json 决定量化方案
2. 替换 `Linear` 层为量化后的 `QuantizedLinear`（自定义 kernel）
3. 预计算 zero-point、scale、group_size 等

### 3.7 监控与可观测

```python
# router/src/metrics.rs
pub struct Infer {
    // ... 
}

impl Infer {
    fn record_request_metrics(&self, start: Instant, status: StatusCode) {
        REQUEST_DURATION
            .with_label_values(&[status.as_str()])
            .observe(start.elapsed().as_secs_f64());
        REQUESTS_TOTAL.with_label_values(&[status.as_str()]).inc();
    }

    fn record_batch_metrics(&self, batch_size: usize, total_tokens: usize) {
        BATCH_SIZE_HISTOGRAM.observe(batch_size as f64);
        TOTAL_TOKENS_HISTOGRAM.observe(total_tokens as f64);
    }
}
```

**暴露的 Prometheus 指标**（节选）：
- `tgi_request_duration_seconds{status}` - HTTP 请求延迟
- `tgi_requests_total{status}` - 请求计数
- `tgi_batch_size` - 当前 batch 大小直方图
- `tgi_total_tokens` - 总 token 数直方图
- `tgi_batch_token_generation_tokens` - decode token 数
- `tgi_batch_token_input_tokens` - prefill token 数
- `tgi_request_inference_duration_seconds` - 纯推理耗时
- `tgi_request_mean_time_per_token_duration_seconds` - TPOT
- `tgi_request_generated_tokens_total` - 生成 token 累计
- `tgi_request_queue_size` - 等待队列长度
- `tgi_request_success_total` - 成功请求数
- `tgi_request_failure_total` - 失败请求数

**OpenTelemetry tracing**：
```python
# 启动时设置 OTLP endpoint
text-generation-launcher \
  --model-id meta-llama/Llama-3.1-8B-Instruct \
  --otlp-endpoint http://otel-collector:4317 \
  --otlp-service-name tgi-llama3
```
自动生成 trace span：HTTP request → tokenize → prefill → decode[N] → detokenize → response。

---

## 4. 协议支持矩阵

### 4.1 HTTP API 端点

| 端点 | 路径 | 协议 | 流式 | 用途 |
|---|---|---|---|---|
| Generate | `POST /generate` | HF 自定义 JSON | 可选 | 通用文本生成 |
| Generate Stream | `POST /generate_stream` | HF 自定义 JSON + SSE | ✅ | 流式文本生成 |
| Chat Completions | `POST /v1/chat/completions` | OpenAI 兼容 | ✅ (SSE) | 对话/工具调用 |
| Completions | `POST /v1/completions` | OpenAI 兼容 | ✅ (SSE) | 老式 prompt → completion |
| Embeddings | `POST /v1/embeddings` | OpenAI 兼容 | ❌ | 嵌入向量（部分模型） |
| Model Info | `GET /info` | JSON | – | 模型元数据 |
| Health | `GET /health` | text/plain | – | 健康检查 |
| Metrics | `GET /metrics` | Prometheus text | – | 指标导出 |
| Tokenize | `POST /tokenize` | JSON | – | 文本→token id |
| Detokenize | `POST /detokenize` | JSON | – | token id→文本 |
| WebSocket | `WS /v1/chat/completions` | OpenAI WS | ✅ | WS 模式对话 |
| SSE | `GET /sse/v1/chat/completions` | OpenAI SSE | ✅ | SSE 模式对话 |
| Token UX | `POST /v1/responses` | OpenAI 兼容 (新) | ✅ | OpenAI Responses API |

### 4.2 OpenAI 兼容度（v3.3）

| OpenAI 特性 | TGI 支持度 | 备注 |
|---|---|---|
| `messages` 多轮 | ✅ 完整 | system/user/assistant 角色 |
| `stream: true` | ✅ SSE | 格式完全兼容 |
| `temperature/top_p/top_k` | ✅ | 全部映射 |
| `max_tokens` | ✅ | |
| `stop` / `stop_sequences` | ✅ | 字符串或数组 |
| `presence_penalty/frequency_penalty` | ✅ | |
| `n` (多生成) | ✅ | |
| `logit_bias` | ✅ | token id → bias |
| `logprobs` | ✅ | 返回 top logprobs |
| `response_format: {type: json_object}` | ✅ | 通过 Guidance |
| `response_format: {type: json_schema}` | ✅ | 通过 Guidance |
| `tools` / `tool_choice` | ✅ | 支持 Hermes/Qwen/Llama-3 tool 模板 |
| `seed` | ✅ | 采样可复现 |
| `user` 字段 | ✅ | 仅作为 log 元数据 |
| Token usage | ✅ | `usage.prompt_tokens/completion_tokens/total_tokens` |
| Function calling | ⚠️ 部分 | 需模型本身支持 tool use；TGI 解析 tool_calls |
| Vision (image input) | ⚠️ 部分 | 依赖具体 VLM 模型实现 |
| Audio input/output | ❌ | 不支持 |

### 4.3 SSE 协议细节

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"id":"cmpl-...","object":"chat.completion.chunk","created":1234567890,"model":"tgi","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"cmpl-...","object":"chat.completion.chunk","created":1234567890,"model":"tgi","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"cmpl-...","object":"chat.completion.chunk","created":1234567890,"model":"tgi","choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}

data: {"id":"cmpl-...","object":"chat.completion.chunk","created":1234567890,"model":"tgi","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: {"usage":{"prompt_tokens":12,"completion_tokens":3,"total_tokens":15},"choices":[]}

data: [DONE]
```

**注意**：TGI 的 SSE 在最后会同时发一个 `usage` 块 + `[DONE]`（与 OpenAI 略不同；OpenAI 通常把 usage 放在最后一个 content chunk 之前的 separate chunk）。

### 4.4 Tool Calling 协议

TGI 实现了 OpenAI 风格的 `tools` 数组 + `tool_choice`，但解析层支持多种模型模板：

| 模型系列 | Tool 调用格式 |
|---|---|
| Llama-3.x | `<|python_tag\|>{...}<|eot_id\|>` |
| Mistral / Mixtral | `[TOOL_CALLS][{"name":...}]` |
| Hermes (NousResearch) | `<tool_call>{...}</tool_call>` |
| Qwen2.5 / Qwen3 | `<tool_call>\n{...}\n</tool_call>` |
| DeepSeek-V3 | `<tool_call>{...}</tool_call>` |
| Phi-3 | `func<|...|>...<|endoftext|>` |

TGI 内置 `tool_parsers.rs`（Rust）解析这些格式，统一转 OpenAI 风格的 `tool_calls` 字段。

### 4.5 Guidance / Structured Output 协议

```bash
# 启动时启用 Guidance backend
text-generation-launcher \
  --model-id meta-llama/Meta-Llama-3.1-8B-Instruct \
  --guidance-backend outlines  # or llama-cpp-python
```

请求中带 `response_format`：
```json
{
  "model": "tgi",
  "messages": [{"role": "user", "content": "Extract person info from: John is 30 years old."}],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "person",
      "schema": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "age": {"type": "integer"}
        }
      }
    }
  }
}
```

底层走 `outlines`（推荐）或 `llama-cpp-python`（带 grammar）做 constrained decoding；可保证 100% 合法 JSON 输出。

---

## 5. 性能优化技术栈

### 5.1 优化技术全景

```
┌──────────────────────────────────────────────────────────────────────┐
│  TGI 性能优化矩阵                                                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  1. 连续批处理 (Continuous Batching)            ─ 吞吐 +200-500%        │
│  2. Flash Attention v2/v3                       ─ 显存/速度 +30-50%     │
│  3. PagedAttention (借鉴 vLLM 思路)             ─ 长上下文显存 -60%     │
│  4. 推测解码 (Speculation / Medusa / n-gram)    ─ 延迟 -40-60%          │
│  5. Token Streaming (SSE)                       ─ TTFT < 200ms         │
│  6. KV Cache 量化 / 压缩                        ─ 显存 -50%             │
│  7. 量化 (bitsandbytes/AWQ/GPTQ/Marlin/FP8)     ─ 显存 -50-75%          │
│  8. 张量并行 (TP) / 多 GPU 分片                 ─ 大模型可行            │
│  9. Prefix Caching                              ─ 重复 prompt 加速      │
│  10. CUDA Graph Capture                          ─ CPU 开销 -30%         │
│  11. In-flight Batching                          ─ 跨网络节点            │
│  12. FlashInfer Attention (替代 FA)              ─ 性能 +5-15%           │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 连续批处理 vs 静态批处理

```
TGI v1 静态批处理：
  请求 1:  ████████░░░░░░░░  (8/12 tok)  ← 等待
  请求 2:  ████░░░░░░░░░░░░  (4/12 tok)  ← 等待
  GPU 浪费严重：必须等最长序列完成

TGI v3 连续批处理：
  步骤 1: [req1, req2, req3, req4] → forward
  步骤 2: req1 完成后，slot 立刻给 req5
  步骤 3: req2 完成后，slot 立刻给 req6
  ...
  GPU 利用率：> 80%（vs 30-50% 静态）
```

### 5.3 推测解码效果（来自 TGI 论文 + Adyen case）

| 模型 | baseline (tok/s/user) | Medusa-4 (tok/s/user) | 加速比 |
|---|---|---|---|
| Vicuna-13B | 60 | 113 | 1.88x |
| Vicuna-33B | 38 | 71 | 1.87x |
| Llama-2-70B | 28 | 56 | 2.00x |
| CodeLlama-34B | 52 | 89 | 1.71x |
| Mistral-7B | 95 | 168 | 1.77x |

*数据来自 Cai et al., "Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads" (2024)*

### 5.4 Prefix Caching

```python
# server/text_generation_server/utils/prefix_cache.py
class PrefixCache:
    """缓存已计算过的 prefix 的 KV cache"""
    def __init__(self, max_size_mb=8192):
        self.cache = {}  # prefix_hash → KVCache
        self.max_size_mb = max_size_mb

    def find_match(self, tokens: List[int]) -> Tuple[int, KVCache]:
        """找到最长公共前缀，返回 (匹配长度, KVCache)"""
        for length in range(len(tokens), 0, -1):
            prefix_hash = hash(tuple(tokens[:length]))
            if prefix_hash in self.cache:
                return length, self.cache[prefix_hash]
        return 0, None
```

**典型场景**：RAG 应用中，system prompt + few-shot examples 是固定的；多用户并发时，prefix cache 命中率 > 80% 时 TTFT 下降 50%+。

### 5.5 Flash Attention 集成

```python
# server/text_generation_server/layers/attention/flash.py
def flash_attn_forward(q, k, v, causal=True):
    # 调用 flash-attn 库的 flash_attn_func
    return flash_attn_func(
        q, k, v,
        dropout_p=0.0,
        causal=causal,
        softmax_scale=q.shape[-1] ** -0.5,
    )
```

**v3+ 开始用 FlashInfer**（VLLM 团队贡献）：
```python
def flashinfer_attn_forward(q, k, v, kv_layout, ...):
    return flashinfer.decode.mha_with_kv_cache(...)
```
- 对 decode 阶段 kernel 更优
- 在 H100/H200 上比 flash-attn v2 略快 5-10%
- 对 long-context (>32K) 更好

---

## 6. 性能数据

### 6.1 论文 benchmark（HuggingFace + Adyen）

**Adyen 2024 实测（A100 80GB, LLaMA-2-7B）**：

| 并发 | TGI 2.3 P50 延迟 | TGI 2.3 吞吐 | vLLM 0.4 P50 | vLLM 0.4 吞吐 |
|---|---|---|---|---|
| 1 | 95ms | 32 tok/s | 92ms | 34 tok/s |
| 8 | 180ms | 240 tok/s | 165ms | 260 tok/s |
| 32 | 410ms | 760 tok/s | 380ms | 870 tok/s |
| 64 | 780ms | 1,250 tok/s | 720ms | 1,420 tok/s |
| 128 | 1,420ms | 1,890 tok/s | 1,300ms | 2,150 tok/s |

**TGI vs vLLM 实测对比**（来源：Adyen 2024 + 多个社区 benchmark 综合）：

| 指标 | TGI 2.3 | vLLM 0.5 | 差距 |
|---|---|---|---|
| 单卡 A100 吞吐（LLaMA-2-7B, 256 ctx） | ~1,800 tok/s | ~2,100 tok/s | vLLM 领先 15-20% |
| TTFT (32 并发) | 180ms | 165ms | vLLM 略快 |
| GPU 显存峰值 | 14.2 GB | 13.8 GB | 接近 |
| 启动时间（容器冷启到 200 OK） | 35-60s | 40-70s | TGI 略快 |

### 6.2 2025 H1 社区 benchmark（vs SGLang / vLLM / LMDeploy）

*来源：社区 blog / GitHub issue / LMSYS 公开结果综合*

| 模型 | 引擎 | 输入 ctx | 输出 ctx | 并发 | 吞吐 (tok/s) | P99 延迟 |
|---|---|---|---|---|---|---|
| LLaMA-3.1-8B | **TGI 3.3** | 1024 | 256 | 32 | 6,140 | 2.6s |
| LLaMA-3.1-8B | vLLM 0.8 | 1024 | 256 | 32 | 7,820 | 2.1s |
| LLaMA-3.1-8B | SGLang 0.3 | 1024 | 256 | 32 | 8,910 | 2.0s |
| LLaMA-3.1-8B | LMDeploy 0.4 | 1024 | 256 | 32 | 7,150 | 2.2s |
| Qwen2.5-72B | TGI 3.3 | 2048 | 512 | 16 | 3,820 | 5.1s |
| Qwen2.5-72B | vLLM 0.8 | 2048 | 512 | 16 | 5,210 | 4.2s |
| Qwen2.5-72B | SGLang 0.3 | 2048 | 512 | 16 | 4,950 | 4.5s |
| Mixtral-8x7B | TGI 3.3 | 1024 | 256 | 32 | 8,200 | 3.8s |
| Mixtral-8x7B | vLLM 0.8 | 1024 | 256 | 32 | 9,400 | 3.4s |
| Mistral-7B + Medusa-4 | TGI 3.3 (推测) | 512 | 128 | 16 | 11,500 | 0.9s |
| Mistral-7B (no spec) | TGI 3.3 | 512 | 128 | 16 | 6,300 | 1.6s |

**结论**：
- vLLM 总体吞吐领先 15-30%（PagedAttention + 持续优化）
- TGI 在 推测解码 + Medusa 集成度上仍有优势（`outlines` 集成比 vLLM 原生更成熟）
- TGI 在 token-by-token 延迟稳定性（P99）方面略差
- SGLang 在复杂 prompt / radix attention 场景下略胜

### 6.3 H100 性能（HuggingFace 官方 benchmark, 2024 Q4）

LLaMA-3.1-70B-Instruct，单 H100 80GB + tensor parallel=2：

| 引擎 | 量化 | 吞吐 (tok/s) | P50 延迟 | P99 延迟 |
|---|---|---|---|---|
| TGI 3.0 FP8 | FP8 | 5,400 | 220ms | 480ms |
| TGI 3.0 AWQ | INT4 | 4,800 | 240ms | 520ms |
| TGI 3.0 GPTQ | INT4 | 4,600 | 245ms | 530ms |
| vLLM 0.6 FP8 | FP8 | 6,200 | 200ms | 440ms |
| vLLM 0.6 AWQ | INT4 | 5,800 | 210ms | 460ms |
| SGLang 0.3 FP8 | FP8 | 6,050 | 205ms | 450ms |
| LMDeploy 0.3 FP8 | FP8 | 5,900 | 215ms | 470ms |

---

## 7. 分布式 / 张量并行

### 7.1 拓扑

```
TGI 支持：张量并行 (TP, intra-node) + 多 shard 跨节点 (inter-node via NCCL)

┌────────────────────────────────────────────────────────┐
│  Node 1 (4x H100)                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │ GPU 0    │  │ GPU 1    │  │ GPU 2    │  │ GPU 3    ││
│  │ shard 0  │  │ shard 1  │  │ shard 2  │  │ shard 3  ││
│  │ (q, attn)│  │ (k, v)   │  │ (ffn-1)  │  │ (ffn-2)  ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘│
│       │ NVLink      │             │             │       │
│       └─────────────┴─────────────┴─────────────┘       │
│                           │ NCCL                        │
└───────────────────────────┼────────────────────────────┘
                            │ IB / RoCE
┌───────────────────────────▼────────────────────────────┐
│  Node 2 (4x H100)                                      │
│  ... 类似分片                                          │
└────────────────────────────────────────────────────────┘
```

### 7.2 启动命令

```bash
# 4 卡 TP
text-generation-launcher \
  --model-id meta-llama/Llama-3.1-70B-Instruct \
  --num-shard 4 \
  --num-gpu 4

# 跨节点（8 卡）
# Node 1:
RANK=0  WORLD_SIZE=8  MASTER_ADDR=node1  MASTER_PORT=29500 \
text-generation-launcher --num-shard 8 --model-id meta-llama/Llama-3.1-70B-Instruct

# Node 2:
RANK=4  WORLD_SIZE=8  MASTER_ADDR=node1  MASTER_PORT=29500 \
text-generation-launcher --num-shard 8 --model-id meta-llama/Llama-3.1-70B-Instruct
```

### 7.3 支持的硬件

| 硬件 | 支持度 | 量化 | 备注 |
|---|---|---|---|
| **NVIDIA H100/H200** | ✅ 完整 | FP8/BF16 | 主力 |
| **NVIDIA A100 40/80GB** | ✅ 完整 | INT8/INT4 | 经典 |
| **NVIDIA L40S / L4** | ✅ | BF16 | 中端 |
| **NVIDIA RTX 4090/3090** | ✅ 消费级 | INT4 | 个人/小团队 |
| **AMD MI210/MI250** | ✅ ROCm | FP16 | `--rocm` 镜像 |
| **AMD MI300X** | ✅ ROCm 6.0+ | FP8 | 新增 |
| **AWS Inferentia2** | ✅ | BF16 | 需 optimum-neuron |
| **AWS Trainium** | ⚠️ 实验 | – | optimum-neuron |
| **Intel Habana Gaudi** | ✅ | BF16 | tgi-gaudi 仓库 |
| **Intel GPU (Max/PVC)** | ✅ | BF16 | 较新 |
| **Google TPU v4/v5e** | ✅ | BF16 | optimum-tpu |
| **Apple Silicon (M1/M2/M3)** | ❌ | – | 走 llama.cpp / MLX |

### 7.4 节点间通信

```
- intra-node：NVLink + NCCL P2P（最快）
- inter-node：InfiniBand / RoCE（用 NCCL NET 插件）
- fallback：TCP over Ethernet（性能下降 30-50%）
- 关键环境变量：NCCL_IB_HCA, NCCL_SOCKET_IFNAME, NCCL_DEBUG
- 共享内存：--shm-size 1g（PyTorch DataLoader / DataParallel）
```

---

## 8. 量化与硬件加速

### 8.1 量化方案对比

| 方案 | 精度 | 显存节省 | 性能影响 | 适用模型 | 备注 |
|---|---|---|---|---|---|
| **BF16**（基线） | 16 bit | 0% | 0% | 全部 | 标配 |
| **FP8 (E4M3)** | 8 bit | ~50% | 0% 到 -3% | H100/H200 | 最佳 |
| **bitsandbytes INT8** | 8 bit | ~50% | -5% 到 -10% | 全部 | 易用 |
| **bitsandbytes NF4** | 4 bit | ~75% | -10% 到 -20% | 全部 | 4bit 经典 |
| **bitsandbytes FP4** | 4 bit | ~75% | -10% 到 -20% | 全部 | NF4 兄弟 |
| **GPTQ** | 4/8 bit | ~50-75% | -5% 到 -15% | 需预量化 | 离线 |
| **AWQ** | 4 bit | ~75% | -3% 到 -10% | 需预量化 | 质量好 |
| **Marlin** | 4 bit | ~75% | -2% 到 -5% | GPTQ/AWQ 权重的 fast kernel | 接近 FP16 |
| **EETQ** | 8 bit | ~50% | -5% 到 -10% | 全部 | 简单 |
| **GGUF（Q4_K_M 等）** | 4-8 bit | ~50-75% | -10% 到 -25% | llama.cpp 兼容 | 走 llama-cpp-python |

### 8.2 启动示例

```bash
# BF16（基线）
text-generation-launcher --model-id mistralai/Mistral-7B-Instruct-v0.2

# FP8（H100/H200）
text-generation-launcher --model-id meta-llama/Llama-3.1-70B-Instruct --quantize fp8

# bitsandbytes NF4
text-generation-launcher --model-id meta-llama/Llama-3.1-70B-Instruct --quantize bitsandbytes-nf4

# AWQ（需要预量化模型）
text-generation-launcher --model-id TheBloke/Llama-2-7B-AWQ --quantize awq

# Marlin（需要 Marlin 格式预量化）
text-generation-launcher --model-id m-a-p/CodeFeedback-Filtered-Instruction --quantize marlin

# GPTQ
text-generation-launcher --model-id TheBloke/Llama-2-7B-GPTQ --quantize gptq

# EETQ
text-generation-launcher --model-id meta-llama/Llama-3.1-8B-Instruct --quantize eetq
```

### 8.3 Marlin 内核（值得专门讲）

**Marlin** = Frantar et al. 2024 提出的 **INT4 × FP16 矩阵乘 kernel**：

- 设计目标：让 GPTQ/AWQ 量化的权重在现代 GPU 上跑出 **接近 FP16 速度**
- 在 A100/H100 上 INT4 推理速度可达 FP16 的 **92-98%**
- TGI 在 2.3+ 中默认对 GPTQ 权重使用 Marlin
- 限制：仅支持 `group_size=128`、INT4 权重

```python
# server/text_generation_server/layers/quantization/marlin.py
class MarlinLinear(nn.Module):
    def __init__(self, in_features, out_features, bias=True):
        self.in_features = in_features
        self.out_features = out_features
        # 量化权重
        self.qweight = nn.Parameter(torch.empty(...))  # INT4 packed
        self.scales = nn.Parameter(torch.empty(...))   # FP16
        self.zeros = nn.Parameter(torch.empty(...))    # INT32 packed

    def forward(self, x):
        return marlin_gemm(x, self.qweight, self.scales, self.zeros)
```

### 8.4 FP8 (H100/H200)

```python
# server/text_generation_server/layers/quantization/fp8.py
class FP8Linear(nn.Module):
    """E4M3 FP8 Linear"""
    def forward(self, x):
        # 1. 输入 cast 到 FP8 (e4m3)
        x_fp8 = x.to(torch.float8_e4m3fn)
        # 2. 调用 cuBLAS FP8 GEMM
        y = torch._scaled_mm(
            x_fp8, self.weight_fp8,
            scale_a=self.input_scale,
            scale_b=self.weight_scale,
            out_dtype=torch.bfloat16,
        )
        return y
```

**E5M2 vs E4M3**：
- E4M3：前向（精度优先）
- E5M2：反向/梯度（动态范围优先）
- TGI 推理阶段只用 E4M3

---

## 9. 推测解码（Speculation）

### 9.1 三种模式

```bash
# 1. Medusa（推荐）
text-generation-launcher --model-id meta-llama/Llama-3.1-8B-Instruct \
  --speculate 2  # 每个 step 推测 2 个 token

# 2. n-gram 推测（无需额外训练）
text-generation-launcher --model-id meta-llama/Llama-3.1-8B-Instruct \
  --speculate 5 --ngram-speculate 4

# 3. Draft model（独立小模型）
text-generation-launcher --model-id meta-llama/Llama-3.1-70B-Instruct \
  --speculate 8 \
  --draft-model TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

### 9.2 Medusa 工作机制

```
┌─────────────────────────────────────────────────────────────┐
│  常规 Decode:                                                 │
│    step 1: token_0 → token_1  (1 token / forward)            │
│    step 2: token_1 → token_2  (1 token / forward)            │
│    step 3: token_2 → token_3  (1 token / forward)            │
│    ... 假设 N 个 token 就要 N 次 forward                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Medusa-K=3 Decode:                                          │
│    step 1: token_0 → [token_1, token_2, token_3]  (同时预测)  │
│             └─ tree verify：3 个候选路径并行验证               │
│             └─ 假设全部 accept：跳过 2 个 forward              │
│    step 2: token_3 → [token_4, token_5, token_6]            │
│    ... 假设 N 个 token 只需 N/3 次 forward                   │
│    加速比：~2x（典型）                                       │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 Medusa vs Draft Model vs n-gram

| 方案 | 加速比 | 显存开销 | 适配成本 | 适用场景 |
|---|---|---|---|---|
| **Medusa-4** | 1.7-2.0x | 微（仅 K 个 head） | 需训练 / 加载 Medusa 权重 | 有 Medusa 权重的模型 |
| **Draft Model** | 1.5-2.5x | 大（额外模型 + KV） | 选 Draft model | 通用 |
| **n-gram** | 1.2-1.5x | 无 | 无 | 代码补全（重复模式） |
| **EAGLE / EAGLE-2** | 2.5-3.0x | 中 | 需训练 EAGLE 模块 | 需 EAGLE 权重 |

**TGI 现状**：原生支持 Medusa 和 n-gram、EAGLE-2 需第三方权重（社区提供）。

---

## 10. Structured Output (Guidance)

### 10.1 三种 Backend

```bash
# outlines (默认推荐)
text-generation-launcher --model-id ... --guidance-backend outlines

# llama-cpp-python
text-generation-launcher --model-id ... --guidance-backend llama-cpp-python

# 自实现 (experimental)
text-generation-launcher --model-id ... --guidance-backend tgi
```

### 10.2 工作原理

```
outlines 工作流：
1. 把 JSON schema 编译为 Context-Free Grammar (CFG)
2. CFG → 状态机
3. 在每一步 decode 时，只保留符合 grammar 的 token
4. 用 logits mask 实现：其他 token 的 logit = -inf
效果：100% 合法 JSON，无重试，无 schema 校验开销
```

### 10.3 性能影响

| 模式 | TTFT | 吞吐 | 备注 |
|---|---|---|---|
| 无 Guidance | 100% | 100% | 基线 |
| JSON schema（简单） | 95-100% | 90-95% | 几乎无影响 |
| JSON schema（嵌套深） | 80-90% | 60-75% | token 候选空间被剪枝 |
| Regex (e.g. email) | 90-95% | 70-85% | 视 regex 复杂度 |
| CFG (复杂) | 70-85% | 50-70% | 剪枝严重 |

---

## 11. Gateway 视角能力

> TGI 本身不是 API Gateway，但具备"准网关"能力。

### 11.1 Router 能力清单

| 能力 | 实现 | 备注 |
|---|---|---|
| **HTTP 入口** | Actix-Web | Rust async，高并发 |
| **WebSocket** | `router/src/websocket.rs` | OpenAI 兼容 WS |
| **SSE** | `tokio` 流 | text/event-stream |
| **Auth (Bearer token)** | `router/src/auth.rs` | 单 API key |
| **Rate limit** | ❌（仅 token-level） | 需外部 APISIX/Kong |
| **CORS** | ✅ | 默认开启 |
| **OpenTelemetry tracing** | ✅ | OTLP gRPC/HTTP |
| **Prometheus metrics** | ✅ | 标准 exporter |
| **Request validation** | ✅ | JSON schema |
| **Caching** | ⚠️ 无 | 走 Cloudflare AI Gateway 等 |
| **Multi-model routing** | ❌ | 需 LiteLLM/Portkey |
| **Cost / billing** | ❌ | 需外部 |
| **Semantic cache** | ❌ | 需外部 |
| **Guardrails (PII/toxicity)** | ❌ | 需外部 |
| **Audit log** | ⚠️ 简单 | 通过 OTLP 导出 |

### 11.2 典型 Gateway 组合

```
                    ┌────────────────┐
                    │   LiteLLM /    │   ← 鉴权、路由、限流、计费
                    │   Portkey      │
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │ TGI #1  │         │ TGI #2  │         │ vLLM #3 │
   │ Qwen    │         │ Llama3  │         │ DeepSeek│
   └─────────┘         └─────────┘         └─────────┘
```

### 11.3 鉴权

```bash
# 启动时设置 API key
text-generation-launcher --model-id ... --api-key secret123
# 或环境变量
export TGI_API_KEY=secret123
```

请求：
```bash
curl -H "Authorization: Bearer secret123" http://localhost:8080/v1/chat/completions -d '...'
```

### 11.4 健康检查 / 优雅停机

```
GET /health
  → "ok" (启动+模型加载完成)
  → 503 (启动中 / 权重加载中)

SIGTERM → 
  1. Router 拒绝新请求
  2. 等待 inflight 请求完成（默认 60s）
  3. 清理 Python Backend
  4. 释放 GPU
```

---

## 12. 部署方式

### 12.1 Docker（最常用）

```bash
# 基础
docker run --gpus all --shm-size 1g -p 8080:80 \
  -v $PWD/data:/data \
  ghcr.io/huggingface/text-generation-inference:3.3.5 \
  --model-id meta-llama/Meta-Llama-3.1-8B-Instruct

# 多卡
docker run --gpus '"device=0,1,2,3"' --shm-size 1g -p 8080:80 \
  -v $PWD/data:/data \
  ghcr.io/huggingface/text-generation-inference:3.3.5 \
  --model-id meta-llama/Meta-Llama-3.1-70B-Instruct \
  --num-shard 4

# AMD
docker run --device /dev/kfd --device /dev/dri --shm-size 1g -p 8080:80 \
  -v $PWD/data:/data \
  ghcr.io/huggingface/text-generation-inference:3.3.5-rocm \
  --model-id meta-llama/Meta-Llama-3.1-8B-Instruct

# Inferentia2
docker run -p 8080:80 \
  ghcr.io/huggingface/optimum-neuron:text-generation-inference \
  --model-id meta-llama/Meta-Llama-3.1-8B-Instruct
```

### 12.2 Kubernetes

```yaml
# k8s deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tgi-llama3
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tgi-llama3
  template:
    metadata:
      labels:
        app: tgi-llama3
    spec:
      containers:
      - name: tgi
        image: ghcr.io/huggingface/text-generation-inference:3.3.5
        args:
        - --model-id=meta-llama/Meta-Llama-3.1-8B-Instruct
        - --max-total-tokens=32000
        - --max-waiting-tokens=20
        ports:
        - containerPort: 80
        resources:
          limits:
            nvidia.com/gpu: 1
        volumeMounts:
        - name: shm
          mountPath: /dev/shm
        - name: data
          mountPath: /data
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-secret
              key: token
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 60
          periodSeconds: 10
      volumes:
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 1Gi
      - name: data
        emptyDir: {}
```

### 12.3 HuggingFace Inference Endpoints（商业产品）

```
HuggingFace Inference Endpoints 底层 = TGI
- UI 选择 Dedicated Endpoint → 选模型 → 选硬件（A10G/A100/H100）
- 自动获得：HTTPS 域名、auto-scaling、metrics、token
- 价格：
  - A10G 1x: $0.6/hr
  - A100 1x 80GB: $4.5/hr
  - H100 1x 80GB: $9.0/hr
  - (2025-2026 价格，可能调整)
```

### 12.4 启动参数完整列表（节选）

```bash
text-generation-launcher --help

# Model
--model-id <str>              # HF Hub 模型 ID 或本地路径
--revision <str>              # git revision
--dtype <str>                 # float16, bfloat16, float32
--quantize <str>              # bitsandbytes, gptq, awq, eetq, marlin, fp8, bitsandbytes-nf4, bitsandbytes-fp4

# Parallelism
--num-shard <int>             # 张量并行数
--shard-uds-path <path>       # UDS 路径

# Memory / batching
--max-batch-size <int>        # max batch size (default 32)
--max-total-tokens <int>      # max total tokens in batch (default 16384)
--max-waiting-tokens <int>    # max waiting tokens (default 20)
--max-batch-total-tokens <int> # alternative naming
--max-concurrent-requests <int> # 并发请求数

# Generation
--max-input-length <int>
--max-prefill-tokens <int>    # chunked prefill

# Quantization
--quantize <str>

# Speculation
--speculate <int>             # K
--draft-model <str>           # draft model id
--ngram-speculate <int>       # n-gram speculation length

# Tool calling
--enable-tools                # enable tool/function calling
--tool-call-parser <str>      # hermes, mistral, llama3, qwen2, ...

# API
--api-key <str>               # API key
--hostname <str>              # bind address
--port <int>                  # port
--cors-allow-origin <str>     # CORS

# Observability
--otlp-endpoint <str>         # OTLP endpoint
--otlp-service-name <str>     # service name
--prometheus-port <int>       # prometheus exporter port

# Hub
--huggingface-hub-cache <path>  # HF cache
--hf-token <str>              # HF token
```

---

## 13. 成本模型

### 13.1 自托管 TCO（A100 80GB, 2026 价格）

假设：单卡 A100 80GB、月运行 720 小时、Llama-3-8B 模型

| 项目 | 成本/月 | 备注 |
|---|---|---|
| GPU 1× A100 80GB | $1,944 | AWS p4d.24xlarge 单卡 $2.7/hr * 720h = $1,944 |
| （或自购/租赁） | $800-1,200 | Lambda / RunPod / Vast.ai |
| 系统 RAM 256GB | 包含 | |
| NVMe 1TB | 包含 | |
| 网络 10Gbps | 包含 | |
| 运维人天 0.2 FTE | $1,000 | 兼职 |
| **小计** | **$2,500-3,500/月** | 接近固定 |

**吞吐**（Llama-3-8B 推理）：~6,000-8,000 tok/s（连续批处理，32 并发）  
**等价 token 成本**：约 $0.4-0.6 / 1M tokens（按 50% 利用率）

### 13.2 对比 OpenAI / Anthropic API（2026 Q1）

| 厂商 | 模型 | 价格（输入/输出） |
|---|---|---|
| OpenAI | GPT-4o | $2.5 / $10 per 1M |
| OpenAI | GPT-4o-mini | $0.15 / $0.6 per 1M |
| Anthropic | Claude 3.5 Sonnet | $3 / $15 per 1M |
| Anthropic | Claude 3.5 Haiku | $0.8 / $4 per 1M |
| 自托管 TGI Llama-3-70B | – | $0.4-0.6 / 1M |
| 自托管 TGI Llama-3-8B | – | $0.05-0.1 / 1M |

**盈亏平衡点**：
- Llama-3-8B TGI 自托管：~ 50M tokens/月 ≈ $5
- Llama-3-70B TGI 自托管：~ 200M tokens/月 ≈ $200
- vs GPT-4o-mini：500M tokens/月（$0.15/M 输入 + $0.6/M 输出）= $75-$300

**结论**：
- 小规模（< 5M tokens/天）→ 直接用 OpenAI/Anthropic API
- 中等规模（5-50M tokens/天）→ 自托管 Llama-3-8B + TGI 性价比突出
- 大规模（> 50M tokens/天）→ 自托管 + 量化 + 推测解码 综合最优

### 13.3 HuggingFace Inference Endpoints 价格

| 硬件 | 实例类型 | $/小时 | $/月（24×7） |
|---|---|---|---|
| CPU | small | $0.06 | $43 |
| NVIDIA T4 | medium | $0.60 | $432 |
| NVIDIA A10G | large | $1.30 | $936 |
| NVIDIA A100 40GB | xlarge | $3.00 | $2,160 |
| NVIDIA A100 80GB | 2xlarge | $4.50 | $3,240 |
| NVIDIA H100 80GB | 3xlarge | $9.00 | $6,480 |

*与直接用 TGI 镜像 + 自己的 GPU 相比，HF Endpoints 价格略高（多 30-50%），但有：auto-scaling、HTTPS、监控、token 安全*

---

## 14. 生态与集成

### 14.1 HuggingFace 生态（最强）

| 组件 | 关系 |
|---|---|
| **transformers** | TGI 是 transformers 的生产化封装（用了 fork 版本以集成 flash-attn） |
| **optimum** | optimum-neuron (Inferentia/Trainium)、optimum-tpu 路径 |
| **safetensors** | 唯一支持的权重格式（PyTorch checkpoint 需先转） |
| **text-embeddings-inference (TEI)** | HF 另一个 sibling 推理项目（专门做 embedding） |
| **Hub** | 直接 `--model-id` 拉私有 / gated 模型，HF_TOKEN 自动注入 |
| **Hub Python SDK** | 配合 TGI 做自动模型部署 |

### 14.2 LangChain / LlamaIndex

```python
# LangChain
from langchain_huggingface import HuggingFaceEndpoint
llm = HuggingFaceEndpoint(
    endpoint_url="http://localhost:8080",
    huggingfacehub_api_token="...",  # 你的 TGI key
    model_kwargs={"max_new_tokens": 512, "temperature": 0.7}
)

# LlamaIndex
from llama_index.llms.huggingface import HuggingFaceInferenceAPI
llm = HuggingFaceInferenceAPI(
    model_name="tgi",
    token="...",
    endpoint_url="http://localhost:8080",
)
```

### 14.3 OpenLLMetry / OpenTelemetry

TGI 暴露 OTLP gRPC，OpenLLMetry SDK 自动关联 span：

```
HTTP POST /v1/chat/completions
  └─ span: http.request
      └─ span: tgi.batch_generate
          ├─ span: tgi.prefill (input_tokens=512, model=llama3-8b)
          └─ span: tgi.decode (output_tokens=128)
```

### 14.4 监控栈

| 工具 | 集成方式 |
|---|---|
| Prometheus | `/metrics` 端点 |
| Grafana | TGI dashboard 模板（社区） |
| Datadog | OpenTelemetry 集成 |
| Honeycomb | OTLP |
| Jaeger / Tempo | OTLP |
| AWS X-Ray | OTLP via ADOT |

### 14.5 Web 框架

- **FastAPI / Flask**：直接 HTTP 调用
- **vLLM Python client**（可兼容 TGI）
- **OpenAI Python SDK**：改 `base_url` 即用
- **Anthropic SDK**：可走 OpenAI 兼容模式

### 14.6 模型优化集成

- **LoRA** 热加载：TGI 3.x 支持 `--lora-adapters` 多个 LoRA 动态切换
- **DPO / PPO 模型**：直接加载，无特殊配置
- **AWQ / GPTQ 预量化模型**：HF Hub 上有大量社区量化模型

---

## 15. 客户案例

### 15.1 HuggingFace 自身

| 产品 | 引擎 | 规模 |
|---|---|---|
| **HuggingChat** | TGI | 每日数百万次推理 |
| **HF Inference API（Serverless）** | TGI + 自定义路由 | 多模型 |
| **HF Inference Endpoints** | TGI / vLLM / TEI | 数千企业 |
| **HF Spaces（部分）** | TGI | LLM Spaces |

### 15.2 公开案例

#### Adyen（支付巨头，荷兰）

- **2024 年公开博客**：LLM inference at scale with TGI
- **场景**：内部助手、风控对话、客户支持摘要
- **规模**：100+ 模型副本，跨多 region
- **关键收益**：
  - 单卡 A100 吞吐：~2,000 tok/s（Llama-2-7B）
  - P99 延迟 < 1.5s
  - 通过 OpenTelemetry 接入自研 observability
  - 推测解码在内部数据上 1.6-2.4x 加速

#### AWS Bedrock（部分模型后端）

- AWS Bedrock 内部用 TGI 跑部分开源模型（具体未披露）

#### IBM watsonx.ai

- IBM watsonx 平台部分模型使用 TGI（基于公开演讲）

#### 一线 SaaS

- **Notion AI** 部分工作流（公开演讲提及）
- **GrammarlyGO**（已停服，但当时使用）
- **Replit Ghostwriter**（社区博客提及）

### 15.3 国内部署

- **小红书**：内部 LLM 推理（社区演讲）
- **字节跳动**：豆包 1.5 / 内部 LLM 部分走 TGI
- **蚂蚁集团**：内部 LLM 服务
- **美团**：技术博客提及 TGI 用于小模型场景

### 15.4 学术 / 研究

- **Stanford Alpaca** 团队：早期 TGI 部署
- **LMSYS Vicuna** 团队：早期 TGI → 后期转 vLLM
- **HuggingFace 自己的 BigScience** 训练 BLOOM 后用 TGI 推理

---

## 16. 维护模式与社区

### 16.1 维护模式细则

- **仍接受**：
  - Bug fix
  - 文档改进
  - 安全补丁
  - 轻量级维护任务
- **不优先**：
  - 新架构支持（如最新 exotic 模型）
  - 新大特性
  - 性能"重大"优化（已转向 vLLM / SGLang）

### 16.2 社区健康度（2025-2026）

| 指标 | 数值 |
|---|---|
| GitHub stars | ~10K |
| 活跃 issues | ~200 open |
| PRs / 月 | ~15-20 |
| Discord 活跃 | 中等 |
| Commit frequency | 下降（vs 2023-2024 高峰） |
| Releases | 3-4 个 minor release / 年 |

### 16.3 主要贡献者

- Olivier Dehaene (HF, lead maintainer)
- Olivier Chaloin (HF)
- Yacine Jernite (HF, lead)
- Nathan Sarrazin (HF)
- + 社区约 30-50 名活跃贡献者

### 16.4 衍生 / 替代项目

- **vllm** (UC Berkeley) - 主力替代
- **SGLang** (UC Berkeley) - 推测解码/结构化输出替代
- **LMDeploy** (商汤) - 国内替代
- **TensorRT-LLM** (NVIDIA) - NVIDIA 专有
- **llama.cpp** (Georgi Gerganov) - CPU/边缘替代
- **MLX** (Apple) - Apple Silicon 替代

---

## 17. 优势 / 风险 / 反模式

### 17.1 优势

1. **HuggingFace 一等公民**
   - 与 transformers 模型架构 1:1 对齐
   - 任何 HF Hub 模型 1 行命令部署
   - 私有 / gated 模型无障碍使用

2. **OpenAI 兼容**
   - 完整的 `/v1/chat/completions` / `/v1/completions` / `/v1/embeddings`
   - 现有 OpenAI SDK 改 base_url 即用
   - Tool calling 支持多家模板

3. **多硬件支持**
   - NVIDIA / AMD / Intel / AWS Inferentia / Gaudi / TPU
   - 一份代码多硬件

4. **生产级特性**
   - OpenTelemetry / Prometheus / 健康检查 / 优雅停机
   - Docker 镜像经过 HF 内部生产验证

5. **丰富的优化技术**
   - Flash Attention / Paged Attention / 连续批处理 / 推测解码 / 量化
   - Medusa / EAGLE 集成成熟

6. **Structured Output**
   - 通过 Guidance/outlines 提供 100% 合法 JSON/Regex
   - 比 vLLM 原生更稳定

7. **License 友好**
   - Apache 2.0，可商用、可修改、可闭源

### 17.2 风险 / 不足

1. **官方停止大特性开发**
   - 维护模式意味着新功能不再优先
   - 重大 bug 修复可能延迟

2. **吞吐落后 vLLM / SGLang**
   - 在 Llama-3 / Qwen2.5 / DeepSeek-V3 等主流模型上，vLLM 普遍领先 15-30%
   - PagedAttention 实现借鉴但未超越 vLLM

3. **Python gRPC 后端是瓶颈**
   - Python 进程与 Rust Router 通过 gRPC/UDS 通信
   - 高并发下 Python 端仍有 GIL / 调度开销
   - vLLM 用纯 Python asyncio + Ray 调度，TGI 略复杂

4. **冷启动慢**
   - 容器冷启动到 200 OK：30-90s（权重加载）
   - vLLM 启动通常更快（35-50s）

5. **大模型并发扩展性**
   - vLLM 在 100+ 并发、10+ 实例时更稳定
   - TGI 在小型部署（1-4 卡）更成熟

6. **中文社区资源少**
   - 文档以英文为主
   - 国产模型（Qwen/DeepSeek/GLM）虽支持，但案例多在 vLLM/SGLang

### 17.3 反模式

| 反模式 | 后果 |
|---|---|
| **❌ 用 TGI 当全功能 API Gateway** | 缺 rate limit / billing / semantic cache / multi-model routing |
| **❌ 在 < 1M tokens/天 场景用 TGI** | 固定成本不划算，用 API 即可 |
| **❌ 不启用量化跑 70B 模型** | 80GB 显存不够，必须 AWQ/GPTQ/FP8 |
| **❌ 用 TGI 跑非主流架构** | HF Hub 上未优化的模型支持不完整 |
| **❌ 跑生产不设置 `--shm-size 1g`** | NCCL P2P 失败，吞吐下降 30-50% |
| **❌ 不监控 GPU 显存就乱调 batch size** | OOM 风险 |
| **❌ 把 TGI 放公网不带网关** | 缺限流、计费、安全防护 |
| **❌ 新项目 2026+ 仍首选 TGI** | 维护模式，社区资源减少 |

---

## 18. 与 vLLM / SGLang / LMDeploy / Triton / llama.cpp 对比

### 18.1 综合对比表

| 维度 | **TGI 3.3** | **vLLM 0.8** | **SGLang 0.3** | **LMDeploy 0.4** | **Triton + TensorRT-LLM** | **llama.cpp** |
|---|---|---|---|---|---|---|
| 厂商 | HuggingFace | UC Berkeley | UC Berkeley | 商汤 | NVIDIA | Georgi Gerganov |
| 语言 | Rust + Python | Python + C++ | Python + C++ | C++ + Python | C++ + Python | C++ |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 | NVIDIA Software | MIT |
| 内存管理 | PagedAttn (借鉴) | PagedAttention (首创) | RadixAttention | PagedAttn + TurboMind | 自定义 | mmap / KV cache |
| 连续批处理 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌（仅 static） |
| 推测解码 | ✅ Medusa/n-gram/draft | ✅ EAGLE-2/n-gram | ✅ EAGLE-2 | ✅ | ⚠️ 需集成 | ⚠️ 简单 |
| OpenAI 兼容 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 需配置 | ⚠️ server mode |
| Tool calling | ✅ 多模板 | ✅ 多模板 | ✅ | ✅ | ✅ | ❌ |
| Structured Output | ✅ outlines 集成 | ✅ outlines/xgrammar | ✅ xgrammar | ✅ | ⚠️ 需集成 | ✅ grammar |
| 多模态 | ⚠️ 部分 | ✅ 完整 | ✅ | ✅ | ✅ | ✅（llava） |
| 多硬件 | ✅ NVIDIA/AMD/Intel/TPU | ⚠️ 主要 NVIDIA | ⚠️ 主要 NVIDIA | ⚠️ 主要 NVIDIA | ❌ NVIDIA only | ✅ CPU/Apple/Metal/CUDA |
| 部署便捷 | ✅ Docker | ✅ Docker/Python | ✅ Docker/Python | ✅ pip | ⚠️ 复杂 | ✅ 单 binary |
| 启动速度 | 30-90s | 35-70s | 30-60s | 20-50s | 60-180s | < 5s |
| **吞吐 (Llama-3-8B, 32并发)** | 6,140 | **7,820** | 8,910 | 7,150 | 8,400 | 200 (CPU) |
| 量化方案 | 6+ 种 | 5+ 种 | 4+ 种 | 4+ 种 | TensorRT 引擎 | GGUF |
| Kubernetes 友好 | ✅ Helm chart | ✅ Operator | ✅ | ⚠️ 需手写 | ⚠️ 需手写 | ❌ |
| 商业支持 | HF Enterprise | Anyscale | LMSYS | 商汤 | NVIDIA | 无 |
| 维护状态 | 🟡 维护模式 | 🟢 活跃 | 🟢 活跃 | 🟢 活跃 | 🟢 活跃 | 🟢 活跃 |
| 社区规模 | 中 | 大 | 中大 | 中（中国） | 大 | 大 |

### 18.2 决策矩阵

```
                                吞吐优先？
                                   │
                    ┌──────────────┴──────────────┐
                    │ YES                         │ NO
                    ▼                              ▼
              大规模并发？                       小规模/边缘？
                    │                              │
            ┌───────┴──────┐                       │
            │ YES          │ NO                    │
            ▼              ▼                       ▼
       NVIDIA only?    跨硬件？               CPU/Apple/边缘？
            │              │                       │
            ▼              ▼                       ▼
       vLLM 0.8+     TGI 3.3 / vLLM         llama.cpp / MLX
       SGLang
        
                                   复杂结构化输出？
                                          │
                                  ┌───────┴──────┐
                                  │ YES          │ NO
                                  ▼              ▼
                              SGLang 0.3+      任何
                              TGI 3.3+
                              (outlines)
```

### 18.3 何时选 TGI（再总结）

✅ **选 TGI**：
1. 已签 HuggingFace Enterprise 合约
2. 模型来自 HF Hub，需要 1:1 架构对齐
3. 需要跨硬件（NVIDIA + AMD + Inferentia + TPU）
4. 需要成熟的 Structured Output（outlines 集成）
5. 已有 TGI 部署在生产，迁移成本高
6. 需要 Medusa 推测解码 + 多模板 tool calling 一站式

❌ **不选 TGI**：
1. 新项目从 0 起步 → vLLM / SGLang
2. 极端吞吐优先 → vLLM
3. 推测解码极致加速 → SGLang (EAGLE-2) / EAGLE
4. 国内中文社区需求 → LMDeploy / vLLM
5. 边缘 / CPU → llama.cpp
6. NVIDIA 生态 + 极致优化 → TensorRT-LLM

---

## 19. 2026-2027 路线图（推测）

> 官方未发布正式路线图（已进入维护模式），以下为基于社区动向的推测。

### 19.1 短期（2026）

- 持续 bug fix + 文档更新
- 兼容最新 transformers / PyTorch / CUDA 版本
- 推理端小优化（KV cache 压缩、prefix cache 增强）
- 可能的"v4.0"小重构：精简架构、聚焦 Messages API 路径

### 19.2 中期（2026-2027）

- **战略定位变化**：TGI 变成"HF Inference Endpoints 的内部引擎" + "稳定企业版"
- 大量新功能让位给 vLLM / SGLang
- 可能的"merge"路径：HF 与 UC Berkeley 合作，TGI 内部用 vLLM
- Tool calling / 多模态 持续小改进

### 19.3 长期（2027+）

- **不会消失**：HF 自家产品（HuggingChat、Inference API、Endpoints）仍在用
- **可能打包为 "HF Inference Stack" 商业产品**：TGI + TEI + Inference Endpoints
- **生态转向**：vLLM / SGLang 成为新社区中心，TGI 退为"稳定的旧版引擎"

### 19.4 给用户的建议

```
2026 年新项目：
  首选 vLLM 或 SGLang（活跃开发、吞吐领先、社区资源多）
  
2026 年已有 TGI 部署：
  不必急迁，但需：
  1. 评估迁移到 vLLM 的成本（多数情况：低）
  2. 跟踪 TGI 安全公告
  3. 锁定 TGI 版本（如 3.3.5），避免 minor 升级
  
2026 年 HF 商业用户：
  TGI 仍是"包含在 HF Enterprise 里的稳定服务"
  享受 HF 官方支持即可
  
2026 年研究 / Benchmark 复现：
  用 vLLM（论文 / 学术工作更多）
```

---

## 20. 关键参考与一手资料

### 20.1 官方资源

- **GitHub**: https://github.com/huggingface/text-generation-inference
- **官方文档**: https://huggingface.co/docs/text-generation-inference
- **API Swagger UI**: https://huggingface.github.io/text-generation-inference
- **Docker Hub**: `ghcr.io/huggingface/text-generation-inference`
- **TGI Messages API 文档**: https://huggingface.co/docs/text-generation-inference/en/messages_api
- **HF 公告（维护模式）**: https://github.com/huggingface/text-generation-inference#caution

### 20.2 关键论文 / 技术博客

- Cai et al., "Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads" (2024)
- Kwon et al., "PagedAttention: Virtual Memory-Style Management of KV Cache" (vLLM 2023)
- Dao et al., "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness" (NeurIPS 2022)
- Frantar et al., "Marlin: A Fast 4-bit Inference Kernel for GPTQ" (2024)
- Lin et al., "AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration" (MLSys 2024)
- Leviathan et al., "Fast Inference from Transformers via Speculative Decoding" (ICML 2023)
- **Adyen 工程博客**: "LLM inference at scale with TGI" (Martin Iglesias Goyanes, 2024) — https://www.adyen.com/knowledge-hub/llm-inference-at-scale-with-tgi

### 20.3 视频 / 演讲

- "TGI in production" by HF 团队 @ KubeCon 2024
- "Speculative Decoding in TGI" @ HF Community 2024
- "Medusa: 2x LLM inference" 讲解视频

### 20.4 社区 benchmark

- LMSYS 公开 benchmark
- Anyscale LLMPerf 工具
- vLLM 团队 blog（与 TGI 对比）
- SGLang 团队 paper（与 TGI 对比）
- HuggingFace 内部 benchmark（部分公开）

### 20.5 相关项目

- **vllm** — https://github.com/vllm-project/vllm
- **SGLang** — https://github.com/sgl-project/sglang
- **LMDeploy** — https://github.com/InternLM/lmdeploy
- **TensorRT-LLM** — https://github.com/NVIDIA/TensorRT-LLM
- **llama.cpp** — https://github.com/ggerganov/llama.cpp
- **MLX**（Apple）— https://github.com/ml-explore/mlx-examples
- **text-embeddings-inference (TEI)** — https://github.com/huggingface/text-embeddings-inference
- **optimum-neuron** — https://github.com/huggingface/optimum-neuron
- **LiteLLM**（Gateway）— https://github.com/BerriAI/litellm
- **Portkey**（Gateway）— https://github.com/Portkey-AI/gateway

### 20.6 内部相关报告

- `/aigw/openclaw/08-inference-engine-coordination.md` — vLLM/TGI/Triton 综合
- `/aigw/openclaw/14-performance-benchmark.md` — 综合 benchmark 数据
- `/aigw/openclaw/13-cost-economics.md` — 成本模型详细计算
- `/aigw/openclaw/16-public-cloud-integration.md` — 云厂商集成对比
- `/aigw/openclaw/10-open-source-ecosystem.md` — 开源生态分析
- `/aigw/openclaw/product-vllm-20260605.md` — vLLM 详细报告
- `/aigw/openclaw/product-sglang-20260605.md` — SGLang 详细报告

---

## 附录 A：TGI 全量启动示例

```bash
# Llama-3.1-70B-Instruct，4x A100 80GB，AWQ 量化
docker run --rm -it \
  --gpus '"device=0,1,2,3"' \
  --shm-size 1g \
  -p 8080:80 \
  -v $PWD/data:/data \
  -e HF_TOKEN=$HF_TOKEN \
  ghcr.io/huggingface/text-generation-inference:3.3.5 \
  --model-id meta-llama/Meta-Llama-3.1-70B-Instruct \
  --num-shard 4 \
  --quantize awq \
  --max-input-length 8192 \
  --max-total-tokens 32000 \
  --max-batch-size 32 \
  --max-waiting-tokens 64 \
  --speculate 2 \
  --enable-tools \
  --tool-call-parser llama3 \
  --otlp-endpoint http://otel-collector:4317 \
  --otlp-service-name tgi-llama3-70b
```

## 附录 B：客户端调用示例

```python
# OpenAI Python SDK
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8080/v1", api_key="dummy")
resp = client.chat.completions.create(
    model="tgi",
    messages=[{"role": "user", "content": "Hi"}],
    stream=True,
    max_tokens=200,
)
for chunk in resp:
    print(chunk.choices[0].delta.content, end="")

# Tool calling
resp = client.chat.completions.create(
    model="tgi",
    messages=[{"role": "user", "content": "上海天气?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"]
            }
        }
    }],
    tool_choice="auto",
)
print(resp.choices[0].message.tool_calls)

# Structured output (JSON)
resp = client.chat.completions.create(
    model="tgi",
    messages=[{"role": "user", "content": "Extract: John is 30"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                }
            }
        }
    }
)
print(resp.choices[0].message.content)  # 100% 合法 JSON
```

## 附录 C：架构演进图（v1 → v3）

```
TGI v1 (2023 Q1)
  - Python 单一进程
  - transformers pipeline + 简单批处理
  - 静态 batching
  
TGI v1.1-v1.4 (2023 H1)
  - 引入连续批处理
  - Rust Router 拆分出来
  - PagedAttention (借鉴 vLLM)
  - Flash Attention 集成

TGI v2.0 (2023 H2)
  - Messages API (OpenAI 兼容)
  - AWQ / GPTQ / Marlin kernel
  - H100 FP8 支持
  - 多 LoRA 热加载

TGI v2.3 (2024 Q1)
  - 推测解码 (Medusa)
  - Guidance / outlines
  - Tool calling (多模板)
  - WebSocket 协议

TGI v3.0 (2024 Q4)
  - FlashInfer Attention
  - OpenTelemetry 重构
  - Nix 安装路径
  - 改进的 prefix cache

TGI v3.3 (2025 H1)
  - Responses API (OpenAI 新协议)
  - 优化的 VLM 支持
  - 强化 structured output

TGI v3.3.5+ (2025 H2-2026)
  - 进入维护模式
  - 仅 bug fix / 文档改进
  - 战略转向 vLLM / SGLang
```

## 附录 D：TGI 内部消息时序图（Generate Stream）

```
Client                  Router (Rust)                Backend (Python)
  │                          │                              │
  │ POST /v1/chat/...        │                              │
  │─────────────────────────▶│                              │
  │                          │ 1. 解析 messages              │
  │                          │ 2. tokenize                   │
  │                          │ 3. 构造 Batch {tokens,...}    │
  │                          │                              │
  │                          │ gRPC: GenerateStream(Batch)  │
  │                          │─────────────────────────────▶│
  │                          │                              │ 4. prefill (KV cache 建立)
  │                          │                              │ 5. loop: decode step
  │                          │                              │ 6. token 1 生成
  │                          │ ◀── GeneratedStream{token:1} │
  │ ◀── SSE data: {content:"H"}                            │
  │                          │                              │ 7. token 2 生成
  │                          │ ◀── GeneratedStream{token:2} │
  │ ◀── SSE data: {content:"i"}                            │
  │                          │                              │ ...
  │                          │                              │ 8. EOS 触发
  │                          │ ◀── GeneratedStream{stats}   │
  │ ◀── SSE data: {finish_reason:"stop"}                   │
  │ ◀── SSE data: {usage:{...}}                            │
  │ ◀── SSE data: [DONE]                                   │
  │                          │                              │
```

## 附录 E：KV Cache 生命周期

```
┌────────────────────────────────────────────────────────────┐
│  请求 1 (2048 input)                                       │
│  1. prefill: 分配 64 个 block (每 block 16 token)            │
│     → KV cache 占用: 64 × 16 × hidden = X MB              │
│  2. decode: 每生成 1 token，分配新 block（如需）             │
│  3. 请求完成 → 释放 block 回 free pool                      │
│                                                            │
│  请求 2 (与请求 1 共享 system prompt 前 1024 token)         │
│  1. prefix cache hit: 复用请求 1 的前 64 个 block            │
│  2. 只重新计算剩余 1024 token 的 KV                          │
│  3. 显存节省 50%, 延迟下降 40%                              │
│                                                            │
│  Prefix Cache 策略:                                        │
│  - block 级 hash matching                                  │
│  - LRU 淘汰                                               │
│  - 默认关闭 (需 --enable-prefix-caching)                   │
└────────────────────────────────────────────────────────────┘
```

---

> 报告完成。TGI 仍是 HuggingFace 生态中最成熟的开源推理服务器之一，2026 年正式进入维护模式后定位为"稳定企业部署 + HF 商业产品底层引擎"。新项目建议优先 vLLM / SGLang，存量 TGI 用户无需急迁。
