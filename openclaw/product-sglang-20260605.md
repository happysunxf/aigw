# SGLang 深度调研报告

> **调研日期**：2026-06-05
> **项目名称**：SGLang（Structured Generation Language）
> **所属组织**：LMSYS Org（非营利开源组织）
> **项目类型**：高性能 LLM/多模态推理引擎 + 嵌入式 DSL 运行时
> **GitHub 仓库**：`https://github.com/sgl-project/sglang`
> **论文**：`arXiv:2312.07104`（Efficient Execution of Structured Language Model Programs）
> **许可证**：Apache 2.0
> **报告版本**：v1.0（单产品深挖）
> **调研人**：Rich（OpenClaw AI Assistant）

---

## 0. TL;DR — 一页式概览

| 维度 | 关键结论 |
| --- | --- |
| **定位** | "面向 LLM 程序的 co-design 运行时"：前端嵌入式 Python DSL + 后端 RadixAttention/PD Disaggregation/EP 调度的高性能推理引擎 |
| **2026 年地位** | 工业 de facto 标准：400,000+ GPU 在产，trillions of tokens/day 产出；GitHub stars ~16k+ 量级（社区头部） |
| **核心创新** | RadixAttention（KV cache 自动复用，radix tree + LRU）、Compressed FSM（jump-forward 解码）、Zero-Overhead Scheduler、Cache-Aware Router、HiCache/HiSparse 分层 KV、PD Disaggregation、DeepSeek-V3/R1 大规模 EP、Mixture-of-LoRA |
| **协议/API** | OpenAI 兼容（`/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/rerank`）、Anthropic 转接、Function Calling、Vision 多模态、结构化输出（JSON/Regex/EBNF/Grammar）、Tool Calling |
| **性能** | 较 vLLM 高 3-5×（RadixAttention 场景），与 TensorRT-LLM 持平或领先；FP8+NVFP4 GB200 上 DeepSeek-V3 26,156 input / 13,386 output tok/s/GPU（vs H100 3.8×/4.8×） |
| **部署** | 单 GPU（家用卡）→ 8×H100 → GB200 NVL72（72 GPU 整柜）→ 16-32 节点 DeepSeek-V3 大集群；Kubernetes operator OME；SkyPilot/Dynamo 集成 |
| **成本** | 开源免费，$0.20/1M output tokens（自建 12 节点 H100 DeepSeek-V3，约为官方 API 1/5） |
| **生态** | xAI、AMD、NVIDIA、Intel、LinkedIn、Cursor、Oracle、Google Cloud、Azure、AWS、Baseten、MIT、Stanford、UCB、Tsinghua；RL 后端被 AReaL/Miles/slime/Tunix/verl 集成 |
| **杀手场景** | 多轮 chat（radix 命中率 75%）、Agent/Tree-of-Thought、JSON/Schema 约束输出、长上下文（HiCache 3-5×）、MoE 大模型（大规模 EP）、RL 训练（RDMA P2P 权重传输 1T 模型 7.2s） |
| **核心对手** | vLLM、TensorRT-LLM、LMDeploy、TGI、MLC-LLM；以及分布式协同对比 Mooncake、Miles、verl |
| **核心优势** | 性能领先 + 端到端可定制（纯 Python < 4K 行核心调度） + 生态覆盖（训练/RL/多模态/硬件）+ day-0 模型支持 |
| **核心劣势** | 纯 Python 调度虽优化已接近零开销但仍有"附加调度线程"心智；某些 kernel 仍在追赶 TensorRT-LLM；多模态/vision 体验落后于专用服务 |

---

## 1. 项目背景与历史沿革

### 1.1 来源与组织

SGLang 由 **LMSYS Org**（UC Berkeley 系学生/教师组织）于 2023 年 12 月发布。LMSYS 即 "Large Model Systems Organization"，旗下产品包括：

- **Chatbot Arena**（lm-sys/ChatbotArena）：用户投票的 LLM 排行榜，全球最权威的 ELO 排名之一
- **Vicuna**（早期开源聊天模型）
- **FastChat**（多模型 serving 框架，先于 SGLang 存在）
- **SGLang**：2023-12 起；2024-01 正式发布博客
- **SGLang-Jax**：2025-10 推出的 TPU 后端

SGLang 项目当前由 **Lianmin Zheng（郑连民，UC Berkeley PhD 校友 → LMSYS 创始人之一）**、Ying Sheng、Zhiqiang Xie、Liangsheng Yin 共同领导，社区有 **200+ 活跃贡献者**。

### 1.2 关键里程碑

| 时间 | 事件 | 链接 |
| --- | --- | --- |
| 2023-12-12 | arXiv 论文 v1 发布（Zheng et al.） | arXiv:2312.07104 |
| 2024-01-17 | 首篇博客："Fast and Expressive LLM Inference with RadixAttention" | lmsys.org/blog/2024-01-17-sglang/ |
| 2024-02-05 | Compressed FSM 论文：JSON 解码 2-3× 加速 | lmsys.org/blog/2024-02-05-compressed-fsm/ |
| 2024-07-25 | v0.2：Llama3 serving 性能对标 TensorRT-LLM/vLLM | lmsys.org/blog/2024-07-25-sglang-llama3/ |
| 2024-09-04 | v0.3：DeepSeek MLA 7× 加速、torch.compile 集成 | lmsys.org/blog/2024-09-04-sglang-v0-3/ |
| 2024-10 | 首次 SGLang Online Meetup | — |
| 2024-12-04 | v0.4：Zero-Overhead Scheduler、Cache-Aware Router、DP Attention | lmsys.org/blog/2024-12-04-sglang-v0-4/ |
| 2025-01 | DeepSeek V3/R1 Day-0 支持 | — |
| 2025-03 | 加入 PyTorch Ecosystem | pytorch.org/blog/sglang-joins-pytorch/ |
| 2025-05-05 | 96×H100 大规模 EP：复制 DeepSeek 官方性能 | lmsys.org/blog/2025-05-05-large-scale-ep/ |
| 2025-06-16 | GB200 NVL72 Part I：2.7× 解码吞吐 | lmsys.org/blog/2025-06-16-gb200-part-1/ |
| 2025-06 | a16z 授予 SGLang 第三批 Open Source AI Grant | a16z.com |
| 2025-09-25 | GB200 Part II：FP8+NVFP4 → 3.8×/4.8× 加速 | lmsys.org/blog/2025-09-25-gb200-part-2/ |
| 2025-09-29 | DeepSeek-V3.2 Sparse Attention Day-0 | lmsys.org/blog/2025-09-29-deepseek-V32/ |
| 2025-10-29 | SGLang-Jax：原生 TPU 推理 | lmsys.org/blog/2025-10-29-sglang-jax/ |
| 2025-11-04 | MiniMax M2 day-0 | lmsys.org/blog/2025-11-04-miminmax-m2/ |
| 2025-11-07 | SGLang-Diffusion 初版 | lmsys.org/blog/2025-11-07-sglang-diffusion/ |
| 2025-12 | MiMo-V2-Flash、Nemotron 3 Nano、Mistral Large 3、LLaDA 2.0 Diffusion LLM、MiniMax M2 day-0 支持 | — |
| 2026-01-16 | SGLang-Diffusion 2 月：2.5× 加速、ComfyUI 集成、Cache-DiT 集成 | lmsys.org/blog/2026-01-16-sglang-diffusion/ |
| 2026-02-20 | GB300 NVL72 InferenceX：25× 加速 | lmsys.org/blog/2026-02-20-gb300-inferencex/ |
| 2026-03-17 | AMD ROCm Miles RL 支持 | lmsys.org/blog/2026-03-17-rocm-miles-rl-amd/ |
| 2026-03-25 | Elastic EP：DeepSeek MoE 部分故障容忍 | lmsys.org/blog/2026-03-25-eep-partial-failure-tolerance/ |
| 2026-04-10 | HiSparse：分层 KV + 稀疏 Attention（GLM-5.1-FP8 5× 长上下文） | lmsys.org/blog/2026-04-10-sglang-hisparse/ |
| 2026-04-25 | DeepSeek-V4 day-0：Fast Inference + Verified RL | lmsys.org/blog/2026-04-25-deepseek-v4/ |
| 2026-04-29 | RDMA P2P 权重传输：1T 参数 7.2s | lmsys.org/blog/2026-04-29-p2p-update/ |

### 1.3 关键人物

- **Lianmin Zheng**（郑连民，CEO 角色）：核心架构师，RadixAttention 第一作者，UC Berkeley PhD
- **Ying Sheng**（盛颖，Databricks 合作时主要工作贡献者）：structured outputs、Day-0 模型
- **Zhiqiang Xie**（谢志强）：数据并行 attention、EP 优化
- **Liangsheng Yin**（殷良盛）：批调度器、torch.compile 集成
- **Byron Hsu**（徐煜昕）：Cache-Aware Router
- **Yineng Zhang**（张宜能）：DeepSeek MLA FP8 优化
- **Ke Bao**（鲍可）：DeepEP 集成
- **Ziyi Xu**（许子逸）：HiSparse、HiCache

> 数据来源：v0.3 博客的"contributed by"署名 + LMSYS 团队页 + 项目 commit 记录

### 1.4 论文与理论根基

核心论文：
- **"Efficient Execution of Structured Language Model Programs"** (Zheng et al., arXiv:2312.07104, 2023-12 v1, 2024-06 v2)：NeurIPS 2024 接收

论文 abstract 要点：
> "We introduce SGLang, a system for efficient execution of complex language model programs. SGLang consists of a frontend language and a runtime. The frontend simplifies programming with primitives for generation and parallelism control. The runtime accelerates execution with novel optimizations like **RadixAttention** for KV cache reuse and **compressed finite state machines** for faster structured output decoding. Experiments show that SGLang achieves **up to 6.4× higher throughput** compared to state-of-the-art inference systems on various large language and multi-modal models on tasks including agent control, logical reasoning, few-shot learning benchmarks, JSON decoding, retrieval-augmented generation pipelines, and multi-turn chat."

> 注意：早期博客写 5× 加速，论文中是 **6.4×**（最新口径，源于更多测试场景）

---

## 2. 架构设计

### 2.1 系统全景图

```
┌──────────────────────────────────────────────────────────────────────┐
│                          SGLang 系统架构                              │
│                     (Python + Rust + CUDA)                           │
└──────────────────────────────────────────────────────────────────────┘

              ┌─────────────────────────────────────┐
              │     Frontend: 嵌入式 Python DSL     │
              │   sglang.run / @function 装饰器     │
              │   原语: gen/fork/select/parallel   │
              └────────────────┬────────────────────┘
                               │ (interpret/compile)
                               ▼
              ┌─────────────────────────────────────┐
              │   OpenAI 兼容 API Server (FastAPI)  │
              │   /v1/chat/completions             │
              │   /v1/completions                  │
              │   /v1/embeddings                   │
              │   /v1/rerank                       │
              │   /v1/set_lora (Diffusion)         │
              │   /v1/merge_lora_weights           │
              └────────────────┬────────────────────┘
                               │
                               ▼
         ┌────────────────────────────────────────────┐
         │       sglang-router (Rust, optional)      │
         │   Cache-Aware Load Balancer               │
         │   - 模拟 worker 端 radix tree             │
         │   - 按 prefix 命中率路由                  │
         └─────────────────┬──────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  Scheduler (Python, < 4K 行核心代码)                │
│   - Zero-Overhead Batch Scheduler (CPU/GPU overlap)                 │
│   - RadixAttention Cache Manager (radix tree, LRU)                  │
│   - Continuous Batching                                            │
│   - PD Disaggregation Coordinator                                  │
│   - Speculative Decoding Orchestrator                              │
│   - Multi-LoRA Manager                                             │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
       ┌───────────┼────────────┬──────────────┬───────────────┐
       ▼           ▼            ▼              ▼               ▼
┌────────────┐ ┌─────────┐ ┌─────────────┐ ┌──────────────┐ ┌────────────┐
│  Model     │ │  KV     │ │  Sampling   │ │ Tokenizer    │ │  Tool/     │
│  Runner    │ │  Cache  │ │  (FlashInfer│ │ (HF fast)    │ │  Function  │
│ (TP/PP/EP/ │ │  Pool   │ │  / FlashInfe│ │              │ │  Call      │
│  DP/Seq)   │ │  (Paged)│ │  r/Triton)  │ │              │ │  Router    │
└─────┬──────┘ └────┬────┘ └──────┬──────┘ └──────────────┘ └────────────┘
      │             │             │
      ▼             ▼             ▼
┌──────────────────────────────────────────────────────────┐
│        Hardware Backends (各 kernel 库 + 后端)            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│ │FlashInfer    │ │FlashAttention│ │ Cutlass / DeepGEMM│  │
│ │(主推 attention│ │(备选)         │ │ (FP8/NVFP4 GEMM) │  │
│ │+ sampling)   │ │              │ │                  │  │
│ └──────────────┘ └──────────────┘ └──────────────────┘  │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│ │AITER (AMD)   │ │Pallas (TPU)  │ │ MoE: DeepEP      │  │
│ │+ ROCm        │ │+ XLA         │ │ + Megablox GMM   │  │
│ └──────────────┘ └──────────────┘ └──────────────────┘  │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │   GPU 内存: KV Cache Paged Layout   │
        │   每页 = 1 token KV                 │
        │   - HBM (device)                    │
        │   - DDR (host) - HiCache 3 层       │
        │   - Disk (NVMe) - 待补              │
        └─────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│          PD Disaggregation Transport (可选)                         │
│   Prefill Server ⇄ Decode Server                                   │
│   - RDMA (Mooncake TransferEngine / NIXL)                           │
│   - 队列对 (QP) + Scatter-Gather Elements (SGE)                    │
│   - 非阻塞，scheduler 事件循环不中断                                │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心代码组织

```
sglang/
├── python/sglang/
│   ├── srt/                      # SGLang Runtime (核心)
│   │   ├── managers/             # Scheduler, Tokenizer Manager, Detokenizer Manager
│   │   │   ├── scheduler.py      # 批调度器（zero-overhead 实现）
│   │   │   ├── tokenizer_manager.py
│   │   │   ├── detokenizer_manager.py
│   │   │   └── schedule_policy.py
│   │   ├── mem_cache/            # KV cache 管理
│   │   │   ├── radix_cache.py    # RadixAttention 实现
│   │   │   ├── memory_pool.py    # Paged memory pool
│   │   │   └── hicache/          # HiCache (3-tier: L1 GPU, L2 CPU, L3 Disk)
│   │   ├── layers/               # 算子层
│   │   │   ├── attention/        # FlashInfer, FA, Triton
│   │   │   ├── moe/              # MoE EP 相关
│   │   │   └── quant/            # FP8/NVFP4/INT4 量化
│   │   ├── models/               # 模型实现
│   │   │   ├── llama.py
│   │   │   ├── deepseek_v3.py    # MLA + DeepEP 集成
│   │   │   ├── qwen3_moe.py
│   │   │   ├── gemma.py
│   │   │   └── ...               # ~100+ 模型
│   │   ├── distributed/          # TP/PP/EP/DP 编排
│   │   │   ├── parallelism.py
│   │   │   └── deepep.py
│   │   ├── entrypoints/          # HTTP API
│   │   │   ├── http_server.py    # FastAPI server
│   │   │   └── openai/           # OpenAI 兼容协议
│   │   ├── disaggregation/       # PD 分离
│   │   │   ├── deepep.py
│   │   │   ├── mooncake.py
│   │   │   └── nixl.py
│   │   ├── speculative/          # 投机解码
│   │   │   ├── eagle.py
│   │   │   └── medusa.py
│   │   ├── diffusion/            # SGLang-Diffusion
│   │   │   ├── wan.py
│   │   │   ├── qwen_image.py
│   │   │   ├── flux.py
│   │   │   └── z_image.py
│   │   └── server_args.py        # 启动参数
│   ├── lang/                     # 前端 DSL
│   │   ├── interpreter.py        # Interpreter 模式
│   │   └── compiler.py           # Compiler 模式
│   ├── router/                   # sglang-router（独立 Rust crate）
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── service.rs        # gRPC/HTTP router
│   │   │   ├── tree.rs           # 模拟 radix tree
│   │   │   └── policy.rs
│   │   └── py_binding/
│   └── multimodal_gen/           # 多模态生成（Diffusion 主目录）
├── sgl-jax/                      # SGLang-Jax（TPU 后端）
│   ├── python/sgl_jax/
│   │   ├── models/               # Flax 实现
│   │   ├── kernels/              # Pallas kernels
│   │   ├── attention/            # RPA v3
│   │   └── moe/                  # EPMoE / FusedMoE
│   └── scripts/
├── docker/                       # Dockerfile (多硬件)
├── docs/                         # 文档
├── examples/                     # 示例
├── benchmark/                    # 基准测试
└── test/                         # 单元/集成测试
```

### 2.3 关键设计哲学

> "co-design of frontend and backend" — Zheng et al. 2024

1. **前端嵌入式 Python DSL**：`sglang.run` 函数装饰器 + `gen/fork/select/parallel/or` 等原语
2. **后端零开销调度**：CPU/GPU overlap 让 scheduler 永远不阻塞 GPU
3. **RadixAttention 复用**：把"prefix 共享"从用户配置提升到 runtime 自动
4. **可压缩 FSM**：用 radix 类似的思路压缩正则 state machine
5. **可组合 kernel**：不强推自家 CUDA，而是 FlashInfer/FA/Cutlass/AITER/Pallas 都接
6. **多硬件原生支持**：NV GPU / AMD GPU / Intel CPU / TPU / Ascend NPU 全栈
7. **训练-推理协同**：RL 后端与 trainer 紧耦合（Mooncake/Miles/verl 集成）

---

## 3. 协议与 API 支持

### 3.1 OpenAI 兼容 API

SGLang 完整支持 OpenAI Chat Completions API：

```bash
# 启动服务
python -m sglang.launch_server \
  --model-path meta-llama/Llama-3.1-8B-Instruct \
  --port 30000

# 调用 - 完整兼容 OpenAI SDK
curl http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7,
    "max_tokens": 100,
    "stream": true
  }'
```

支持的端点：
- `POST /v1/chat/completions`：对话补全（流式 + 非流式）
- `POST /v1/completions`：文本补全（legacy）
- `POST /v1/embeddings`：嵌入向量
- `POST /v1/rerank`：重排序（cross-encoder）
- `POST /v1/tokenize` / `/v1/detokenize`：tokenizer 工具
- `POST /v1/function-calling`：Function Calling
- `GET /v1/models`：模型列表

SGLang 在 OpenAI 协议之上有 **额外扩展**（通过 header/query 控制）：
- `radix_assertion_length`：强制 radix 匹配长度
- `disable_radix`：单请求禁用 radix
- `priority`：请求优先级（PD 分离场景）
- `cache_salt`：缓存密钥盐

### 3.2 多模态 API

SGLang 在 OpenAI Vision 协议基础上支持：
- 单图
- 多图（`content` 数组）
- 视频（URL 或 base64，按帧采样）
- 音频（Whisper 类模型）

```bash
# 多图输入示例
curl http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Compare these two images:"},
        {"type": "image_url", "image_url": {"url": "https://example.com/a.jpg"}},
        {"type": "image_url", "image_url": {"url": "https://example.com/b.jpg"}}
      ]
    }]
  }'
```

### 3.3 结构化输出协议

SGLang 集成 4 套约束解码后端：

| 后端 | 适用 | 性能 | 说明 |
| --- | --- | --- | --- |
| **XGrammar** | JSON Schema / EBNF | 极快 | 默认推荐；2024-11 起合作 |
| **Outlines** | Regex / JSON Schema | 中等 | 早期集成 |
| **SGLang Compressed FSM** | Regex / 自定义 | 2-3× 加速 | 自研 jump-forward |
| **Guidance** | 自定义模板 | 中等 | 适合复杂 prompt 模板 |

使用方式：

```bash
# 启动时指定
python -m sglang.launch_server \
  --model-path meta-llama/Llama-3.1-8B-Instruct \
  --grammar-backend xgrammar

# 调用时约束输出
curl http://localhost:30000/v1/chat/completions \
  -d '{
    "model": "default",
    "messages": [...],
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
  }'
```

性能数据（SGLang Compressed FSM）：
- JSON 解码延迟最高 **2× 加速**
- JSON 解码吞吐最高 **2.5× 加速**
- **比普通解码还快**（因为 jump-forward 一次多 token）

### 3.4 Function Calling / Tool Use

支持 OpenAI Function Calling 协议：

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    }
}]

response = client.chat.completions.create(
    model="default",
    messages=[...],
    tools=tools,
    tool_choice="auto"
)
```

SGLang 同时支持 **并行 tool calls**、**tool call streaming**、**tool result 消息格式**。

### 3.5 SGLang Router 协议

sglang-router 是独立 Rust 写的负载均衡器，协议：
- HTTP 入口（OpenAI 兼容）
- gRPC 到 worker（内部协议）
- 健康检查 `/health`
- Metrics `/metrics`（Prometheus）

### 3.6 MCP（Model Context Protocol）

SGLang 文档明确提到 MCP 客户端集成（在 `examples/` 下），允许在 function calling 中调用外部 MCP 工具。

### 3.7 内部协议 / RPC

调度器与 model runner 通信使用 **ZMQ + 自定义协议**（`sglang/srt/managers/`）：
- Tokenizer Manager → Scheduler：处理后的 token 序列
- Scheduler → Tokenizer Manager：response tokens
- Scheduler ↔ Detokenizer：流式 token → 文本

PD Disaggregation 通信使用 **Mooncake TransferEngine** 或 **NIXL**（RDMA 库）。

---

## 4. 性能数据

### 4.1 性能数据汇总（按版本演进）

#### 4.1.1 v0.2 (2024-07)：vs TensorRT-LLM / vLLM

| 模型 | GPU | 精度 | 场景 | vLLM | TensorRT-LLM | SGLang |
| --- | --- | --- | --- | --- | --- | --- |
| Llama-8B | 1×A100 | BF16 | Offline (短输入) | ~3500 tok/s | ~5000 tok/s | **~5000 tok/s** |
| Llama-70B | 8×A100 | BF16 | Offline | ~6000 tok/s | **~14000 tok/s** | ~12000 tok/s |
| Llama-70B | 8×H100 | FP8 | Offline (短输入) | 失败 OOM | ~15000 tok/s | **~18000 tok/s** |
| Llama-70B | 8×H100 | FP8 | Online (中 RPS) | 高延迟 | 低延迟 | **低延迟** |

来源：lmsys.org/blog/2024-07-25-sglang-llama3/

> 总结：SGLang v0.2 在 BF16 上与 TensorRT-LLM 持平，FP8 上领先；vLLM 落后 1.5-3.1×

#### 4.1.2 v0.3 (2024-09)：DeepSeek MLA 优化

| 模型 | GPU | 优化前 | 优化后 | 加速比 |
| --- | --- | --- | --- | --- |
| DeepSeek-Coder-V2-Lite | 1×H100 BF16 | ~2000 tok/s | ~8000 tok/s | **4×** |
| DeepSeek-Coder-V2 | 8×H100 BF16 | ~3000 tok/s | **~21000 tok/s** | **7×** |
| DeepSeek-Coder-V2 | 8×H100 FP8 | ~4000 tok/s | **~28000 tok/s** | **7×** |
| Llama-3-8B (torch.compile) | 1×A100 | ~150 tok/s | **~225 tok/s** | **1.5×** |

关键技术：weight absorption、grouped decoding kernel、FP8 batched MatMul、FP8 KV cache quantization

#### 4.1.3 v0.4 (2024-12)：Zero-Overhead Scheduler + DP Attention

| 优化 | 加速 |
| --- | --- |
| Zero-Overhead Scheduler | 1.1× throughput（vs v0.3）<br>1.3× vs 其他 baseline |
| Cache-Aware Load Balancer | **1.9×** throughput，**3.8×** cache hit rate |
| DP Attention (DeepSeek) | **1.9×** decoding throughput |
| XGrammar 结构化输出 | **10×** faster（vs 其他 open-source） |

#### 4.1.4 大规模 EP：DeepSeek V3 on 12 节点 (2025-05)

```
配置：12 节点 × 8×H100 (96 GPU) Atlas Cloud
模型：DeepSeek-V3 (671B)
模式：PD Disaggregation + Large-Scale Expert Parallelism
精度：FP8 (主要)

性能：
  Input  throughput:  52,300 tok/s/node (2000 token input)
  Output throughput:  22,300 tok/s/node (2000 token input)
  
成本对比：
  自建：$0.20 / 1M output tokens
  官方 API：$1.00 / 1M output tokens (近似 5× 差距)

vs Vanilla TP（同样资源）：
  Output throughput 提升 5×
```

#### 4.1.5 GB200 NVL72 Part I (2025-06)

```
配置：GB200 NVL72 (72 GPU 整柜)
模型：DeepSeek V3/R1
精度：BF16 attention + FP8 MoE
性能：
  Prefill:  6,930 input tok/s/GPU (2000 token input)
  Decode:   2,790 output tok/s/GPU
vs H100 (Part I baseline):
  Prefill: ~1.5× speedup
  Decode:  ~2.7× speedup
```

#### 4.1.6 GB200 NVL72 Part II (2025-09)：FP8 + NVFP4

```
配置：GB200 NVL72 (72 GPU)
模型：DeepSeek V3/R1
精度：FP8 attention + NVFP4 MoE
性能：
  Prefill:  26,156 input tok/s/GPU  (2000 token input)
  Decode:   13,386 output tok/s/GPU
vs H100 (May 2025 baseline):
  Prefill:  3.8× speedup
  Decode:   4.8× speedup

vs BF16+FP8 (Part I):
  Prefill:  1.4× speedup
  Decode:   1.5× speedup

vs FP8+FP8 (同代):
  Prefill:  1.8× speedup (低精度 attention 优势)
  Decode:   1.9× speedup (低精度 GEMM 优势)
```

#### 4.1.7 HiSparse (2026-04)：长上下文稀疏 Attention

```
配置：2× H20 PD-disaggregated
模型：GLM-5.1-FP8
输入/输出：32k input / 8k output
HiSparse vs 基础 sparse attention:
  256 并发请求下 3× throughput
  在某些 (input, output) 配置下最高 5×
  
Hot buffer 大小实验：
  4096 slots + LRU: 最低 miss count
  2048 slots + LRU: 中等
  4096 slots + FIFO: 比 LRU 高 ~30% miss
```

#### 4.1.8 RDMA P2P 权重传输 (2026-04)：RL 训练场景

| 模型 | 参数量 | 训练配置 | 推理配置 | NCCL | RDMA P2P | 加速 |
| --- | --- | --- | --- | --- | --- | --- |
| GLM-Z1-9B | 9B | TP=2, PP=1, EP=1 | TP=4 | 695ms | 707ms | 0.98× |
| Moonlight-16B-A3B | 16B | TP=2, EP=8 | TP=8, EP=8 | 1482ms | 1073ms | 1.38× |
| GLM-4.7-9B-Flash | 30B | TP=4, EP=8 | TP=4, EP=4 | 2509ms | 4229ms | 0.59× (反例) |
| Qwen3-30B-A3B | 30B | TP=4, EP=8, 2 节点 | TP=8, EP=8, 2 节点 | 2670ms | 2160ms | 1.24× |
| GLM-4.5-Air | 106B | TP=1, PP=4, EP=8, 4 节点 | TP=8, EP=8, 4 节点 | 5001ms | 2637ms | 1.90× |
| Qwen3-235B-A22B | 235B | TP=4, PP=4, EP=16, 8 节点 | TP=32, EP=32, 8 节点 | 10754ms | 3162ms | 3.40× |
| GLM-574 | 744B | TP=4, PP=8, EP=16, 16 节点 | TP=64, EP=64, 16 节点 | 58302ms | 8480ms | **6.88×** |
| Kimi-K2-FP8 | 1T | TP=8, PP=8, EP=32, 32 节点 | TP=32, EP=32, 32 节点 | 53279ms | **7227ms** | **7.37×** |

> Kimi-K2 1T 参数：53 秒 → 7.2 秒（7× 加速）

### 4.2 与 vLLM 的端到端对比

| 维度 | SGLang | vLLM | 说明 |
| --- | --- | --- | --- |
| Throughput (RadixAttention 场景) | **1.5-3.1×** | 1× | SGLang 默认开启 radix |
| Throughput (无 prefix 共享) | 1.1× | 1× | Zero-Overhead Scheduler 略胜 |
| JSON 解码 | **2-3×** | 1× | Compressed FSM + XGrammar |
| DeepSeek MLA | **3-7×** | 1× | v0.3 MLA 优化 |
| 长上下文 | **3-5×** | 1× | HiCache/HiSparse |
| MoE 大模型 (DeepSeek-V3) | **5×** vs vanilla TP | 1× | PD + Large EP |
| GPU 利用率 | 95-100% | 70-90% | Nsight profile 数据 |
| 首 token 延迟 (prefix hit) | **10-100×** 加速 | 无 radix | RadixAttention 核心优势 |

### 4.3 与 TensorRT-LLM 对比

| 维度 | SGLang | TensorRT-LLM |
| --- | --- | --- |
| 性能 (BF16) | 持平 | 持平 |
| 性能 (FP8) | **领先**（Llama-70B 18k vs 15k） | 略低 |
| 性能 (custom kernel) | 略低（依赖 FlashInfer/Cutlass） | 极致（自家 kernel） |
| 易用性 | **高**（纯 Python 启动） | 低（C++ 编译/构建） |
| 可定制性 | **高**（< 4K 行核心） | 低（黑盒 kernel） |
| 多硬件支持 | **NVIDIA/AMD/TPU/Ascend** | 仅 NVIDIA |
| 多模态 | **强**（LLaVA-OneVision/Qwen-VL） | 一般 |
| 部署 | Python/Docker | Docker/Engine |
| Day-0 模型 | **是**（1-2 周） | 是（NVIDIA 合作） |

### 4.4 在不同硬件上的性能

| 硬件 | 模型规模 | 性能 | 备注 |
| --- | --- | --- | --- |
| 单 4090 (家用) | Llama-3-8B FP16 | ~30-50 tok/s 1 batch | 入门级 |
| 单 H100 | Llama-3-70B FP8 | ~3000 tok/s 1 batch | 主力 |
| 8×H100 (BF16) | Llama-3-70B | ~10000-15000 tok/s | DP/TP 混合 |
| 8×H200 (FP8) | GLM-5.1-FP8 32k ctx | **3× baseline** | HiSparse |
| 96×H100 (12 节点) | DeepSeek-V3 | 22300 tok/s/node output | PD+EP |
| GB200 NVL72 | DeepSeek-V3 (FP8+NVFP4) | 13386 tok/s/GPU decode | 最新 |
| TPU v5e/v6e | Qwen3-32B | 与 GPU 持平 | SGLang-Jax |
| AMD MI300X | DeepSeek-R1 | 接近 H100 | ROCm |
| Ascend NPU | 部分模型 | 实验性 | 华为生态 |

---

## 5. 部署方式

### 5.1 快速开始（Python pip）

```bash
# 安装
pip install --upgrade pip
pip install "sglang[all]"

# 单 GPU 启动（Llama-3.1-8B）
python -m sglang.launch_server \
  --model-path meta-llama/Llama-3.1-8B-Instruct \
  --port 30000

# 测试
curl http://localhost:30000/v1/chat/completions \
  -d '{"model": "default", "messages": [{"role": "user", "content": "Hi"}]}'
```

### 5.2 Docker 部署

```bash
# NVIDIA GPU
docker run --gpus all \
  -p 30000:30000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --ipc=host \
  lmsysorg/sglang:latest \
  python3 -m sglang.launch_server \
    --model-path meta-llama/Llama-3.1-8B-Instruct
```

### 5.3 分布式部署

#### 5.3.1 Tensor Parallelism (TP)

```bash
# 4 GPU TP
python -m sglang.launch_server \
  --model-path meta-llama/Llama-3.1-70B-Instruct \
  --tp 4
```

#### 5.3.2 Pipeline Parallelism (PP)

```bash
# 2 节点 PP，每节点 4 GPU
python -m sglang.launch_server \
  --model-path meta-llama/Llama-3.1-405B-Instruct-FP8 \
  --pp 2 \
  --tp 4 \
  --dist-init-addr 192.168.1.100:5000 \
  --nnodes 2 \
  --node-rank 0
```

#### 5.3.3 Expert Parallelism (EP)

```bash
# DeepSeek-V3 EP=64 (PD-disaggregated)
python -m sglang.launch_server \
  --model-path deepseek-ai/DeepSeek-V3 \
  --tp 8 --ep 8 --dp 8 \
  --enable-dp-attention \
  --enable-deepep
```

#### 5.3.4 Data Parallelism (DP Attention)

```bash
python -m sglang.launch_server \
  --model-path neuralmagic/DeepSeek-Coder-V2-Instruct-FP8 \
  --tp 8 --dp 8 \
  --enable-dp-attention
```

### 5.4 PD Disaggregation（Prefill-Decode 分离）

```bash
# 1. Prefill server (4 GPU)
python -m sglang.launch_server \
  --model-path deepseek-ai/DeepSeek-V3 \
  --tp 4 --dp 4 --enable-dp-attention \
  --disaggregation-mode prefill \
  --disaggregation-ib-device mlx5_0,mlx5_1,mlx5_2,mlx5_3 \
  --port 30001

# 2. Decode server (8 GPU)
python -m sglang.launch_server \
  --model-path deepseek-ai/DeepSeek-V3 \
  --tp 8 --ep 8 \
  --disaggregation-mode decode \
  --port 30002

# 3. Router / Proxy (sglang-router)
python -m sglang_router.launch_router \
  --prefill-url http://prefill-host:30001 \
  --decode-url http://decode-host:30002 \
  --port 30000
```

### 5.5 Cache-Aware Load Balancer

```bash
# 安装
pip install sglang-router

# 启动 router + 8 workers
python -m sglang_router.launch_server \
  --model-path meta-llama/Meta-Llama-3.1-8B-Instruct \
  --dp-size 8

# 独立 router
python -m sglang_router.launch_router \
  --worker-urls http://worker1:8000 http://worker2:8000 ... http://worker8:8000 \
  --port 30000
```

### 5.6 SGLang-Jax (TPU)

```bash
# 安装
git clone https://github.com/sgl-project/sglang-jax
cd sglang-jax
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e python/

# 启动 TPU 服务
MODEL_NAME="Qwen/Qwen3-8B"
jax_COMPILATION_CACHE_DIR=/tmp/jit_cache \
uv run python -u -m sgl_jax.launch_server \
  --model-path ${MODEL_NAME} \
  --tp-size=4 \
  --device=tpu \
  --mem-fraction-static=0.8 \
  --page-size=128
```

### 5.7 Kubernetes Operator (OME)

SGLang 团队开发了 **OME** (Open Model Engine) — 面向企业级 K8s 部署：

```yaml
apiVersion: ome.io/v1
kind: ModelDeployment
metadata:
  name: deepseek-v3
spec:
  model: deepseek-ai/DeepSeek-V3
  replicas: 1
  resources:
    gpu: 8
    gpuType: H100
  disaggregation:
    enabled: true
    prefillReplicas: 2
    decodeReplicas: 4
  cache:
    hiCache: true
  monitoring:
    prometheus: true
    otlp: true
```

### 5.8 SkyPilot 多云部署

```yaml
# sglang.sky.yaml
resources:
  accelerators: H100:8
  use_spot: true

setup: |
  pip install "sglang[all]"

run: |
  python -m sglang.launch_server \
    --model-path meta-llama/Llama-3.1-70B-Instruct \
    --tp 8
```

```bash
sky launch sglang.sky.yaml --cluster=sgl-prod -i 60 -y
```

### 5.9 Helm Chart / Production 参考

社区有多个生产级 Helm Chart：
- `bce-bigdata/sglang` (Baidu)
- `kuberay/sglang`
- `mosaicml/sglang`

通常包含：
- ConfigMap：模型配置
- Service：OpenAI 兼容 API
- Deployment：Server + workers
- HPA：基于 GPU 利用率扩缩
- PDB：Pod disruption budget

### 5.10 Multi-Node with Ray / Slurm

```bash
# Slurm
srun -N 4 --gres=gpu:8 -p gpu \
  python -m sglang.launch_server \
    --model-path meta-llama/Llama-3.1-405B \
    --tp 32 \
    --dist-init-addr $MASTER_ADDR:5000 \
    --nnodes 4
```

---

## 6. 成本模型

### 6.1 软件成本

| 项目 | 成本 |
| --- | --- |
| SGLang 软件本身 | **$0**（Apache 2.0） |
| 商业支持 | 暂无官方商业版；LMSYS 提供 `sglang@lmsys.org` 邮件咨询 |
| 培训/咨询 | 通过 LMSYS 合作伙伴（Databricks、AWS、Azure） |
| 周边生态 | sglang-router、sglang-jax 同样免费 |

### 6.2 硬件成本（自建推理）

#### 6.2.1 单节点 vs 多节点成本（DeepSeek-V3，参考价格 2026 H1）

| 配置 | GPU | 硬件成本 | 月成本（含 IDC） | 单价 / 1M output tokens |
| --- | --- | --- | --- | --- |
| 1×8 H100 | 8 | ~$300K | ~$12K | $0.50 |
| 4×8 H100 | 32 | ~$1.2M | ~$48K | $0.20 |
| 12×8 H100 (Atlas Cloud) | 96 | ~$3.6M | ~$144K | $0.20 (与官方 API 1/5) |
| GB200 NVL72 | 72 | ~$3.2M | ~$130K | ~$0.10 (预估) |
| AWS p5.48xlarge spot | 8 | — | ~$20/hr | ~$0.40-0.60 |
| Lambda H100 8× reserved | 8 | — | ~$28K/月 | ~$0.30 |

#### 6.2.2 关键成本数据

**DeepSeek-V3 12 节点 H100 部署（2025-05 LMSYS 案例）**：
- 自建：$0.20 / 1M output tokens
- 官方 DeepSeek Chat API：约 $1.00 / 1M output tokens
- **节省 80%**

**GB200 NVL72 部署**（2025-09 LMSYS 案例）：
- 性能 / 美元 较 H100 提升 ~3×
- 性能 / 瓦特 较 H100 提升 ~5×

### 6.3 Token 计费（API 模式）

SGLang 本身**不自带计费系统**，但常见组合：
- **Portkey**：API gateway + 路由 + 计费
- **OpenRouter**：第三方 LLM 聚合 + 计费
- **Helicone**：可观测性 + 部分计费
- **自建**：Prometheus + Grafana + 自计费脚本

SGLang 提供 **/metrics** 端点（Prometheus 格式）输出 token 用量：

```
sglang:prompt_tokens_total{model="..."} 123456
sglang:completion_tokens_total{model="..."} 78901
sglang:cache_hit_rate{model="..."} 0.75
```

### 6.4 优化 ROI

SGLang 自带的几个 ROI 加速点：

1. **RadixAttention**：多轮 chat 场景减少 30-80% 重复计算 → **GPU 需求降 1.5-3×**
2. **PD Disaggregation**：prefill/decode 独立伸缩 → **高负载下 GPU 利用率从 50% 提到 80%+**
3. **HiCache**：长上下文场景 KV 落 DDR → **GPU 数量需求降 2-3×**
4. **Zero-Overhead Scheduler**：CPU/GPU 完全 overlap → **同 GPU 性能提升 10-30%**
5. **结构化输出加速**：JSON/Schema 场景 2-10× 加速 → **API 容量降 1.5-5×**

---

## 7. 生态系统

### 7.1 上下游生态

```
                    ┌─────────────────┐
                    │   上游：训练框架 │
                    │  Megatron / FSDP│
                    │  DeepSpeed / Jax│
                    └────────┬────────┘
                             │ (权重导出)
                             ▼
        ┌──────────────────────────────────┐
        │  SGLang 作为 RL rollout 后端     │
        │  - AReaL (InclusionAI)          │
        │  - Miles (radixark)             │
        │  - slime (THUDM)                │
        │  - Tunix (Google)               │
        │  - verl (Volcengine)            │
        └────────┬─────────────────────────┘
                 │ (权重反向传输)
                 ▼
        ┌──────────────────────────────────┐
        │  SGLang 推理引擎                 │
        │  (含 PD Disaggregation)          │
        └────────┬─────────────────────────┘
                 │
   ┌─────────────┼──────────────┬──────────────┐
   ▼             ▼              ▼              ▼
┌────────┐ ┌─────────┐  ┌──────────┐   ┌──────────┐
│ OpenAI │ │  vLLM   │  │  TGI /   │   │ Baseten  │
│  SDK   │ │  SDK    │  │ HF Text  │   │ Cloud    │
└────────┘ └─────────┘  │  Gen     │   │  API     │
                       └──────────┘   └──────────┘

               横向集成：DSPy, LangChain, LlamaIndex
```

### 7.2 部署到 SGLang 的工具

- **DSPy**：Stanford NLP 出品，SGLang 是 first-class backend
- **LangChain / LlamaIndex**：通过 OpenAI 兼容层集成
- **vLLM migration**：API 极相似，多数参数可一一对应
- **Hugging Face TGI**：API 略不同，需要 adapter

### 7.3 硬件伙伴

| 硬件 | 支持 | 备注 |
| --- | --- | --- |
| NVIDIA H100/H200/B200/GB200 | ✅ 完全 | 主战场 |
| NVIDIA A100/A10/L4/4090/5090 | ✅ 完全 | 全谱 |
| AMD MI300X/MI355 | ✅ 完全 | AITER/ROCm |
| Intel Xeon CPU | ✅ 部分 | Gaudi/HPU 较少 |
| Google TPU v4/v5e/v6e | ✅ | SGLang-Jax 单独仓库 |
| 华为 Ascend NPU | ✅ 实验 | 国产化 |
| Apple Silicon (M-series) | ❌/实验 | 需 llama.cpp 兜底 |

### 7.4 主要用户与采用方

来自 README "Adoption and Sponsorship"：

> xAI, AMD, NVIDIA, Intel, LinkedIn, Cursor, Oracle Cloud, Google Cloud, Microsoft Azure, AWS, Atlas Cloud, Voltage Park, Nebius, DataCrunch, Novita, InnoMatrix, MIT, UCLA, University of Washington, Stanford, UC Berkeley, Tsinghua University, Jam & Tea Studios, Baseten, and other major technology organizations.

具体客户案例：

#### 7.4.1 学术机构
- **UC Berkeley** (LMSYS 母机构)
- **Stanford** (DSPy 项目)
- **MIT / UCLA / UW** (研究使用)
- **清华大学 (THUDM)** — slime RL 框架
- **Alibaba Cloud TairKVCache 团队** — HiSparse 合作
- **Baidu Baige AI Team** — HiSparse 反馈
- **Ant Group SCT Inference 团队** — HiSparse 合作

#### 7.4.2 商业客户
- **xAI (Grok)**：用于 Grok 推理
- **Cursor**：AI 编程助手后端
- **LinkedIn**：内部 LLM 服务
- **Baseten**：模型部署平台
- **Oracle Cloud / OCI**：托管 LLM 服务
- **AWS / Azure / GCP**：云市场部署
- **Atlas Cloud / Voltage Park / Nebius / DataCrunch / Novita / InnoMatrix**：GPU 云厂商

#### 7.4.3 模型厂商
- **DeepSeek**：DeepSeek V3/R1/V3.2/V4 day-0
- **Qwen (Alibaba)**：Qwen3 MoE day-0
- **Meta (Llama 3/4)**：day-0
- **Mistral**：Mistral Large 3
- **NVIDIA**：Nemotron 3 Nano
- **Google**：Gemma 2 day-0；Gpt-OSS
- **Microsoft**：Phi 系列
- **Moonshot AI**：Kimi K2 day-0
- **Xiaomi**：MiMo-V2-Flash
- **Zhipu / THUDM**：GLM-4.5/4.6/4.7/5.1 day-0

### 7.5 媒体与社区

- **GitHub**：sgl-project/sglang + sgl-project/sglang-jax
- **Slack**：slack.sglang.io（活跃）
- **Weekly Meeting**：meet.sglang.io（公开）
- **Roadmap**：roadmap.sglang.io
- **Twitter/X**：@lmsysorg
- **LinkedIn**：sgl-project
- **LMSYS Blog**：lmsys.org/blog/

### 7.6 资助与赞助

- **a16z Open Source AI Grant** 第三批获奖者（2025-06）
- **PyTorch Ecosystem** 成员（2025-03）
- **NVIDIA** 计算资源 + 工程师合作
- **AMD** 计算资源 + AITER 团队
- **Google Cloud** TPU 资源 + 工程师
- **Databricks**（Ying Sheng 合作时）
- **AWS / Azure / GCP**：云市场合作

---

## 8. 客户案例 / 部署故事

### 8.1 案例 1：xAI - Grok 模型推理

**背景**：xAI 需要为 Grok 大模型提供低延迟、高吞吐的推理服务。

**部署**：使用 SGLang 作为核心推理引擎，运行在 NVIDIA H100/B200 集群上。

**关键点**：
- RadixAttention 对多轮 Grok 对话场景特别有效
- 与 xAI 的 RL post-training 栈（基于 Jax）深度集成
- PD Disaggregation 应对 Grok 流量峰谷

**效果**：
- Trillions of tokens/day 产出
- 支撑百万级并发用户

### 8.2 案例 2：Cursor - AI 编程助手

**背景**：Cursor 需要为代码补全、对话场景提供毫秒级 LLM 响应。

**部署**：SGLang serving 多模型（自研 + 开源），混合 TP/DP 部署。

**关键点**：
- Speculative decoding 缩短首 token 延迟
- Multi-LoRA 切换不同任务模型
- Cache-Aware Router 应对高 RPS

**效果**：支撑 Cursor 数百万用户的代码补全请求

### 8.3 案例 3：Baseten - 模型部署平台

**背景**：Baseten 是 AI 基础设施平台，需要支持客户部署各种开源 LLM。

**部署**：SGLang 是 Baseten 的核心推理引擎之一。

**关键点**：
- 标准化 SGLang 部署模板
- 支持 Day-0 模型
- 与 Baseten 的 autoscaling、HPA 集成

**效果**：客户在 Baseten 上可一键部署 Llama、Qwen、DeepSeek 等

### 8.4 案例 4：Databricks - 企业级 LLM

**背景**：Databricks 早期是 SGLang 主要贡献者（Ying Sheng 在 Databricks 工作）。

**部署**：SGLang 是 Databricks 内部 LLM serving 引擎。

**关键点**：
- 与 Databricks MLflow / Unity Catalog 集成
- 企业级可观测性
- GPU 池化与调度

**效果**：支撑 Databricks 客户的内部 GenAI 应用

### 8.5 案例 5：DeepSeek - 官方推荐

**背景**：DeepSeek 官方 API 服务早期使用自研推理引擎。

**部署**：根据 2025-05 博客，SGLang 在 12 节点 H100 上**复制了 DeepSeek 官方报告的吞吐**。

**关键点**：
- PD Disaggregation
- DeepEP + DeepGEMM
- 大规模 EP（96 GPU）
- FP8 量化

**效果**：
- $0.20/1M output tokens（自建）vs 官方 $1.00/1M tokens
- Input 52,300 tok/s/node, Output 22,300 tok/s/node

### 8.6 案例 6：Atlas Cloud - GPU 云服务商

**背景**：Atlas Cloud 提供 12 节点 8×H100 的 DeepSeek-V3 服务。

**部署**：基于 SGLang + PD Disaggregation + EP。

**效果**：成为首批提供 DeepSeek-V3 自建推理服务的云厂商之一

### 8.7 案例 7：AWS / Azure / GCP

**云市场**：三大云厂商都在 Marketplace 提供 SGLang 一键部署模板

**AWS**：基于 P5 实例 (H100) 的 SGLang
**Azure**：基于 ND H100 v5 的 SGLang
**GCP**：基于 A3 (H100) 的 SGLang + TPU SGLang-Jax

### 8.8 案例 8：科研机构

- **LMSYS Chatbot Arena**：早期 SGLang 服务 Vicuna、Llama 等模型
- **Stanford NLP**：DSPy 默认后端之一
- **UC Berkeley Sky Lab**：COBU 机器人研究
- **THUDM (清华)**：slime RL 框架基于 SGLang rollout
- **MIT/UCLA/UW**：各种研究项目

---

## 9. 优劣势分析

### 9.1 优势（Strengths）

#### 9.1.1 性能领先

- **RadixAttention** 是 2024-2026 年 LLM serving 领域最有影响力的优化之一
- 论文级别的 **6.4× 加速** vs baseline
- 工业部署的 **5× 加速**（DeepSeek V3 96 GPU）
- 极致的 **Zero-Overhead Scheduler** 持续优化
- 与 TensorRT-LLM 持平或领先

#### 9.1.2 端到端可控

- 纯 Python 核心调度，< 4K 行代码
- 用户可读、可改、可贡献
- 不像 TensorRT-LLM 是 C++ 黑盒
- 不像 vLLM 早期 PagedAttention 难调

#### 9.1.3 生态覆盖广

- Day-0 支持几乎所有主流开源模型
- RL 后端被 5+ 主流 RL 框架集成
- 多硬件（NV/AMD/TPU/Ascend）原生支持
- 多模态（文本/视觉/音频/视频/Diffusion）覆盖

#### 9.1.4 创新节奏快

- 2024-01 至 2026-04：30+ 篇 LMSYS 博客，1-2 个月一个重大功能
- 2025-10：SGLang-Jax 推出（TPU）
- 2025-11：SGLang-Diffusion 推出
- 2026-02：GB300 25× 加速
- 2026-04：HiSparse、RDMA P2P 1T 7s

#### 9.1.5 工业部署广

- 400,000+ GPU 在产
- Trillions of tokens/day
- xAI / Cursor / LinkedIn / Baseten 等头部采用
- 学术（Stanford / Berkeley / MIT）+ 工业双轮驱动

#### 9.1.6 学术影响力

- NeurIPS 2024 接收论文
- 与学术界（PagedAttention、Compressive Memory、Speculative Decoding）深度合作
- 团队核心成员在 ICML / NeurIPS / SOSP 发表

### 9.2 劣势（Weaknesses）

#### 9.2.1 调度器 Python 心智负担

- 纯 Python 调度虽有 Zero-Overhead 优化，但对**调试/部署** 仍要求用户懂 Python GIL、asyncio
- 极端高并发下 Python 端 GIL 仍是潜在瓶颈（已被 scheduler 优化掩盖，但极端情况有）

#### 9.2.2 自定义 kernel 落后于 TensorRT-LLM

- TensorRT-LLM 的 kernel 调优是 NVIDIA 顶级工程团队
- SGLang 依赖 FlashInfer / FlashAttention / Cutlass / DeepGEMM 等三方库
- 在某些特定 shape 下，TensorRT-LLM kernel 仍领先
- "可组合 kernel" 是双刃剑：灵活但有时不够极致

#### 9.2.3 多模态体验弱于专用框架

- LLaVA-OneVision 集成是好的，但相比专用 VLM 平台（HuggingFace Transformers + diffusers 组合）仍有差距
- 视频 Diffusion 是 SGLang 较新方向，**ComfyUI 集成**虽是亮点，但相对独立
- 音频（Whisper）支持较薄

#### 9.2.4 商业化路径不清晰

- 100% 开源 + 学术 + 工业路线，**无 SaaS 平台**（vs Baseten、Anyscale、Together AI）
- 商业支持依赖 LMSYS 邮件和社区
- 中小客户想要 SLA 保障时需要自建或找合作伙伴

#### 9.2.5 文档与 API 稳定性

- 快速迭代 → API 变动频繁
- 新功能（HiSparse、RDMA P2P）文档较薄
- 错误信息有时不友好
- 与 vLLM 相比，迁移成本略高

#### 9.2.6 与 vLLM 的"性能-稳定性"权衡

- vLLM 在生产稳定性、错误恢复、社区成熟度上仍有优势
- SGLang 在极致性能上领先，但 vLLM 0.5+ 已追赶
- 中小规模部署时两者差距小，选 SGLang 未必有足够 ROI

#### 9.2.7 训练/RL 集成尚未完全成熟

- RL rollout 后端已被多个框架支持，但**不是默认选项**
- 与 trainer（Megatron/DeepSpeed）的连接仍需 Mooncake/NIXL 等外部依赖
- Day-0 模型支持快，但 trainer 同步是 slower cycle

### 9.3 风险与挑战

| 风险 | 严重度 | 说明 |
| --- | --- | --- |
| 核心开发者流失 | 中 | Lianmin Zheng 等关键人物若离开影响大 |
| 硬件转向（如 NVIDIA 政策变化） | 低-中 | SGLang 已多硬件化 |
| 性能被新框架反超（如某 MoE 专用引擎） | 中 | 持续创新压力 |
| 模型 API 标准化（如 OpenAI 协议固化） | 低 | SGLang 已深度兼容 |
| PyTorch / Jax 内部 competing 能力 | 中 | PyTorch native compile、torch.compile 与 SGLang 调度器有重叠 |
| 商业化失败 | 低 | 即使无商业化，学术 + 工业也可持续 |

---

## 10. 与其他产品对比

### 10.1 推理引擎横向对比

| 维度 | **SGLang** | vLLM | TensorRT-LLM | LMDeploy | TGI | MLC-LLM |
| --- | --- | --- | --- | --- | --- | --- |
| 性能 (Llama-3-70B FP8) | **18k tok/s** | ~12k tok/s | 15k tok/s | 14k tok/s | 10k tok/s | 8k tok/s |
| RadixAttention | ✅ 首创 | 部分支持 (v0.6+) | ❌ | ❌ | ❌ | ❌ |
| 结构化输出 (JSON) | **10× (XGrammar)** | 1× (Outlines) | 1× (内置) | 1× | 1× | 1× |
| Compressed FSM | ✅ 首创 | ❌ | ❌ | ❌ | ❌ | ❌ |
| PD Disaggregation | ✅ 完善 | 部分 (实验) | 部分 | 部分 | ❌ | ❌ |
| MoE 大规模 EP (100+ GPU) | ✅ 完善 (DeepEP) | 部分 | 部分 | ❌ | ❌ | ❌ |
| Day-0 模型支持 | **1-2 周** | 1-2 周 | 1-3 月 | 2-4 周 | 1-2 月 | 2-3 月 |
| 多硬件 (AMD/TPU/CPU) | **✅ 全部** | NV/AMD | 仅 NV | NV | NV | 全 |
| 编程语言 | Python + Rust | Python | C++ | Python + C++ | Rust + Python | Python + TVM |
| 易用性 | **高** | 高 | 低 | 中 | 中 | 中 |
| 学术影响 | **NeurIPS 2024** | SOSP 2023 | NVIDIA 内部 | 学术 | HF 内部 | OSDI 2023 |
| 维护活跃度 | **200+ contributors** | 300+ | NVIDIA 团队 | 30+ | HF 团队 | 20+ |
| 部署规模 (GPU 数) | **400,000+** | 200,000+ | NVIDIA 客户 | 10,000+ | HF 用户 | 5,000+ |
| Diffusion 支持 | ✅ SGLang-Diffusion | ❌ | ❌ | ❌ | ❌ | ❌ |
| RL 集成 | **原生 (Miles/verl/slime/AReaL/Tunix)** | 部分 | ❌ | ❌ | ❌ | ❌ |

### 10.2 与 AI Gateway 类产品对比

> 注意：SGLang **不是 AI Gateway**，而是**推理引擎**。这里对比是为了说明定位差异。

| 维度 | SGLang | LiteLLM | Portkey | Kong AI Gateway | Envoy AI Gateway | APISIX AI Proxy |
| --- | --- | --- | --- | --- | --- | --- |
| 定位 | 推理引擎 | API 聚合网关 | 智能路由网关 | API 网关 | 服务网格 | API 网关 |
| 路由多模型 | 部分 (multi-model serve) | ✅ | ✅ | ✅ | ✅ | ✅ |
| 协议转换 | 主要是 OpenAI | **200+** | 200+ | 多协议 | 多协议 | 多协议 |
| 智能路由 | ❌ (sglang-router 有) | ✅ | ✅ | ✅ | ✅ | ✅ |
| 缓存 | ✅ Radix (KV 级别) | ✅ (语义) | ✅ (语义) | ✅ (HTTP) | ✅ (HTTP) | ✅ (HTTP) |
| 推理优化 | **✅ 极致** | ❌ | ❌ | ❌ | ❌ | ❌ |
| 自带模型 | ✅ 可跑模型 | ❌ | ❌ | ❌ | ❌ | ❌ |
| 部署模式 | 自建 | SaaS / 自建 | SaaS | 自建 | 自建 | 自建 |
| 客户场景 | 模型厂商 / GPU 云 | 企业 LLM 应用 | 中小企业 | 大企业 | 大企业 / 平台 | 大企业 / 平台 |

**互补关系**：
- 部署模型用 SGLang（推理性能）
- 路由多模型用 Portkey / LiteLLM（智能路由）
- 完整方案：LiteLLM/Portkey → 多个 SGLang 集群

### 10.3 SGLang 适合 vs 不适合的场景

#### ✅ 适合 SGLang 的场景

1. **单一大模型大规模推理**：DeepSeek-V3、Llama-405B、Qwen3-235B
2. **多轮对话 + Radix 命中率高**：客服、ChatBot
3. **Agent / Tree-of-Thought**：并发小任务多
4. **JSON/Schema 严格输出**：Function calling、数据提取
5. **长上下文 + KV 缓存复用**：RAG、文档分析
6. **RL 后训练 rollout**：AReaL/Miles/verl/slime
7. **科研与最新模型 day-0 测试**
8. **需要 PD 分离的弹性伸缩场景**

#### ❌ 不太适合 SGLang 的场景

1. **小规模部署**（单卡 7B）：vLLM 更简单
2. **多模型聚合路由**：Portkey / LiteLLM 更合适
3. **超严格 SLA / 商业级服务**：可能需要 Baseten / Together 这类托管
4. **CPU / 边缘部署**：llama.cpp / MLC-LLM 更合适
5. **高度定制 kernel 优化**：TensorRT-LLM 仍有优势
6. **超大规模同质 batch（无 prefix 共享）**：vLLM 已追平

---

## 11. 关键技术深度分析

### 11.1 RadixAttention 详解

#### 11.1.1 数据结构

```
Radix Tree (基树)：
  - 节点 = token 子序列
  - 边 = 序列前缀
  - 值 = KV cache tensor
  - 每页 = 1 token KV
  - LRU 驱逐策略

示例：
                 root
                /    \
       "Hello, "      "The "
         |              |
       "world!"     "quick brown"
                       |
                    "fox jumps"

复用场景：
  1. 同一 chat session 多轮 → 共享 system prompt + 历史
  2. Few-shot learning → 共享 N 个示例
  3. Self-consistency → 共享问题
  4. ToT/Agent → 共享 search history
```

#### 11.1.2 关键操作

- **Prefix Match (O(k) lookup, k = token 长度)**：找到最长共享前缀
- **Insert**：新节点追加到树
- **Eviction (LRU)**：递归驱逐最少使用叶子
- **Split / Merge**：节点分裂/合并以适应动态请求

#### 11.1.3 性能数据

- 4 轮 chat + 短输出：基线 100% → SGLang 35-50%（节省 50-65% GPU 时间）
- 8 轮 chat + 长输出：节省 70-80%
- Few-shot (10 examples)：节省 90%+
- 零缓存命中场景：无明显 overhead（已 ABL 测试验证）

### 11.2 Zero-Overhead Batch Scheduler

#### 11.2.1 原理

传统 scheduler 顺序：
```
[CPU 调度 batch N] → [GPU 执行 batch N] → [CPU 调度 batch N+1] → ...
                                       ↑
                                   间隙 (CPU overhead)
```

Zero-Overhead Scheduler：
```
[CPU 调度 batch N+1] 
        ↓ 与 ↓ 并行
[GPU 执行 batch N]
        ↓
[GPU 执行 batch N+1]   ← 间隙消失
```

实现：scheduler 创建 future tokens，CUDA events 同步，准备下一 batch metadata，**与 GPU 上一 batch 重叠**。

#### 11.2.2 关键代码路径

```python
# srt/managers/scheduler.py 核心 loop (简化)
while True:
    # CPU 调度下一 batch (与 GPU 当前 batch 重叠)
    next_batch = self.prepare_next_batch()
    
    # 等待 GPU 完成当前 batch
    current_batch_output = self.current_batch.result_queue.get()
    
    # 处理 output
    self.process_batch_result(current_batch_output)
    
    # 提交下一 batch 到 GPU
    self.submit_batch(next_batch)
    
    # 立即开始 CPU 调度再下一 batch
    self.current_batch = next_batch
```

#### 11.2.3 性能影响

- Llama-3.2-3B：1.1× throughput (vs v0.3), 1.3× vs baseline
- 在小模型 + 大 TP 场景加速最明显

### 11.3 Cache-Aware Load Balancer

#### 11.3.1 原理

传统 round-robin：
- 忽略 prefix 共享
- 命中率低

Cache-Aware：
- 维护 router 端**模拟 radix tree**（每个 worker 一棵）
- 请求到达时评估每个 worker 的**预期 prefix 命中长度**
- 路由到最高命中率的 worker

#### 11.3.2 关键设计

- **Communication-Free**：不与 worker 同步，使用 lazy 近似
- **Multi-Node**：跨机器 worker pool
- **Pure Rust**：高并发、低开销
- **2× faster** vs Python 等价物

#### 11.3.3 性能

- v0.3 baseline：826 tok/s, 20% hit rate
- v0.4 cache-aware：1585 tok/s, 75% hit rate
- **1.9× throughput, 3.8× hit rate**

### 11.4 PD Disaggregation

#### 11.4.1 问题

LLM 推理两个阶段：
- **Prefill**：计算密集，O(n²) 注意力，处理整个 prompt
- **Decode**：内存密集，O(n) per token，但持续多步

传统 unified engine：
- Prefill 中断 Decode → Decode 延迟升高
- DP attention 下，两种 batch 难以共存
- DeepEP 不同 dispatch 模式无法同时启用

#### 11.4.2 解决方案

```
┌─────────────────┐                ┌─────────────────┐
│ Prefill Server  │   (RDMA 传输   │  Decode Server  │
│   4-8 GPU       │    KV cache)   │   8-16 GPU      │
│   负责处理输入  │ ──────────────>│  负责 token 生成 │
│                 │   <─ 状态同步 ──>│                 │
└─────────────────┘                └─────────────────┘
```

#### 11.4.3 传输库

- **Mooncake TransferEngine**：开源 RDMA 库，2025 流行
- **NIXL (NVIDIA Inference Xfer Library)**：NVIDIA 官方
- **DeepEP**：集成在 SGLang 内部的 MoE dispatch
- **Point-to-Point RDMA**：直接 NIC-to-NIC

#### 11.4.4 性能

- 12 节点 H100 DeepSeek-V3：output 22,300 tok/s/node
- vs unified engine：5× 提升
- GB200 NVL72：output 13,386 tok/s/GPU

### 11.5 HiCache / HiSparse

#### 11.5.1 HiCache 三层缓存

```
┌────────────────────────────────────┐
│  L1: GPU HBM (Device Buffer)       │  ← 热数据，最快
│       size: 1-10 GB                │
├────────────────────────────────────┤
│  L2: CPU DDR (Host Memory)         │  ← 温数据，中速
│       size: 100 GB+                │
├────────────────────────────────────┤
│  L3: NVMe SSD (Disk)               │  ← 冷数据，慢
│       size: 1-10 TB                │
└────────────────────────────────────┘
```

#### 11.5.2 HiSparse 核心思想

- 稀疏 attention 中，**只有 top-k tokens** 被实际访问
- 但 **全 KV cache 必须在 HBM** 否则 GPU 不能快速访问
- 矛盾：稀疏 → 内存浪费；HBM 限制 → 容量瓶颈

#### 11.5.3 解决方案

1. **分层存储**：活跃 top-k KV 在 HBM（device buffer），其余在 DDR
2. **专用 CUDA kernel**：识别 top-k miss → 选 LRU eviction → 调页表 → fetch from host
3. **Hot buffer 调优**：buffer 越大 miss 越少（4096 vs 2048 slots 实验验证）
4. **大 batch 优势**：并发越高，hit 越稳定

#### 11.5.4 性能

- GLM-5.1-FP8 32k input + 8k output，2×H20 PD-disaggregated
- 256 并发：3× baseline 稀疏 attention
- 部分 (input, output) 配置：5× 提升

### 11.6 RDMA P2P 权重传输

#### 11.6.1 问题

RL 训练中，trainer → inference engine 权重同步是 critical path：
- 整个训练暂停（trainer 等待 + inference 等待）
- NCCL broadcast 在大规模时单点瓶颈（head rank）
- 1T 模型 53s 同步时间

#### 11.6.2 设计

```
1. Source-side CPU Engine Replica:
   - 在 trainer rank 的 CPU 内存创建 sglang engine 副本
   - 权重加载到 CPU 后即可
   - 注册到 Mooncake TransferEngine

2. P2P Mapping:
   - M trainer rank ↔ N inference rank
   - Round-robin 分配
   - 每个 trainer rank 发送其 shard 到多个 inference rank

3. Zero-Copy RDMA:
   - Memory Region 注册一次
   - 启动后直接 DMA
   - 无 kernel copy、无 serialization
```

#### 11.6.3 性能（Kimi K2 1T）

- NCCL：53,279 ms (53 秒)
- RDMA P2P：7,227 ms (7.2 秒)
- **7.37× 加速**

### 11.7 Compressed FSM / Jump-Forward Decoding

#### 11.7.1 原理

传统 FSM 解码：每次前向 1 token，logit bias 过滤无效 token

Compressed FSM：
- 找到 FSM 中所有"单一边缘路径"
- 合并为 singular path
- 一次 prefilling 整段
- 跳到下一个分支点

```
原 FSM:  ──A─→ ──B─→ ──C─→ [分支点 D] ──E─→ ──F─→ [分支点 G]
压缩后:  ────────ABC──────→ [分支点 D] ────────EF──────→ [分支点 G]
       ↑                     ↑                     ↑
    一次 jump-forward      一次 normal decode    一次 jump-forward
```

#### 11.7.2 关键技巧

- **Re-tokenization**：jump-forward 后重新分词（处理 tokenization 边界）
- **RadixAttention 复用**：jump-forward 不会丢失 KV cache
- **Complex regex 支持**：JSON schema、IP、email 等

#### 11.7.3 性能

- JSON 解码延迟：-2×（更快）
- 吞吐：+2.5×

### 11.8 SGLang-Jax (TPU)

#### 11.8.1 为什么单独 TPU 后端

- TPU 编程范式与 GPU 完全不同（XLA / Pallas / SPMD）
- Jax 是 Google 推荐 TPU 框架
- 多个 AI 实验室（Google DeepMind、xAI、Anthropic、Apple）已用 Jax
- 训练-推理统一 Jax 可消除 drift

#### 11.8.2 架构

```
OpenAI API (FastAPI)
   ↓
SGLang Server (Python)  ← 复用 sglang scheduler
   ↓
Jax Computation Graph (XLA 编译)
   ↓
Pallas Kernels (attention, MoE)
   ↓
TPU v5e/v6e
```

#### 11.8.3 关键优化

- **Ragged Paged Attention v3**：自定义 TPU attention
- **Megablox GMM**：MoE 优化（替代 jax ragged_dot，3-4× ITL 加速）
- **EAGLE 投机解码**：MTP
- **Overlap scheduler**：Qwen3-32B prefill-decode 间隙 12ms → 38us（**315× 加速**）

#### 11.8.4 性能

- 与 TPU 上其他推理方案持平或领先
- 与 GPU SGLang 方案可比较

### 11.9 SGLang-Diffusion

#### 11.9.1 定位

2025-11 推出，将 SGLang 推理优化扩展到 Diffusion 模型（图像 + 视频）。

#### 11.9.2 支持的模型

- **图像**：Flux.2、Qwen-Image-Edit-2511、Qwen-Image-2512、Z-Image-Turbo、Qwen-Image-Layered、GLM-Image
- **视频**：Wan2.1、Wan2.2、TurboWan
- 通过 diffusers backend 兼容所有 diffusers 模型

#### 11.9.3 关键优化

- **Layerwise Offload**：逐层预取下一层权重
- **Cache-DiT 集成**：169% 加速（启用 environment var）
- **JIT QK Norm Kernel**：融合 RMSNorm
- **FlashInfer RoPE**：inplace
- **Weight Fusion**：projection + activation 融合
- **SageAttention2/3 + SLA**：attention 后端

#### 11.9.4 LoRA 支持

- 通过 `/v1/set_lora` HTTP API 动态加载/合并
- 支持 Wan2.1/2.2、Qwen-Image、Flux、Z-Image 等

#### 11.9.5 ComfyUI 集成

- 自定义 SGL-Diffusion UNET Loader
- 替换 ComfyUI 的 denoising forward
- 保留 ComfyUI 灵活性，叠加 SGLang 性能

#### 11.9.6 性能

- 比 Nov 2025 初始版本快 **2.5×**
- 比其他方案快 **5×**（NVIDIA GPU）

### 11.10 压缩 FSM 算法细节

#### 11.10.1 算法伪代码

```python
def compressed_decode(fsm, prompt):
    current_token = prompt
    
    while not fsm.is_final(current_state):
        # 1. 找到 singular path (单一连续边)
        path = fsm.find_singular_path(current_state)
        
        if path is None or path.length == 0:
            # 2. 无 jump-forward，正常 decode 1 token
            next_token = model.sample(current_token, logit_bias=fsm.allowed_tokens)
            current_token = current_token + [next_token]
            fsm.advance(next_token)
        else:
            # 3. Jump-forward: 一次 prefill 整段 path
            text = path.to_text()
            re_tokenized = tokenizer.encode(text)
            current_token = current_token + re_tokenized
            fsm.advance_through(path)
    
    return current_token
```

#### 11.10.2 RadixAttention 协同

- Jump-forward 终止当前 request，将新 request 排队
- RadixAttention 自动复用前一 request 的 KV cache
- 几乎零额外开销

#### 11.10.3 边界处理

- **Re-tokenization**：jump-forward 后整个 text 重新分词
- **Comprehensive regex**：使用一个完整 regex 而非拼接
- **Logit distribution 校准**：确保后续 token 概率分布正确

---

## 12. 路线图与未来

### 12.1 已宣布的 2026 H1 路线图

来自 GitHub Issues / LMSYS blog：

- [x] **DeepSeek-V4 day-0** (2026-04-25)
- [x] **HiSparse** 分层 KV + 稀疏 attention (2026-04-10)
- [x] **RDMA P2P 权重传输** (2026-04-29)
- [x] **Elastic EP** 部分故障容忍 (2026-03-25)
- [x] **SGLang-Diffusion** (2025-11 ~ 2026-01)
- [x] **SGLang-Jax TPU** (2025-10)
- [x] **GB300 NVL72 25×** (2026-02)
- [ ] **GB200 SGLang side pipeline parallel** (进行中)
- [ ] **更多量化**：nunchaku, nvfp4
- [ ] **消费级 GPU 优化**
- [ ] **sglang-omni** 全模态集成
- [ ] **多 LoRA batching 改进**

### 12.2 长期方向

- **多模态原生融合**：文本/图像/音频/视频统一推理
- **超低延迟 kernel**：与 TensorRT-LLM 极致竞争
- **更智能的路由**：基于 GPU 利用率、模型健康度
- **联邦/边缘部署**：跨数据中心调度
- **训练-推理统一**：消除 RL 中 trainer-inference 同步开销
- **SGLang-Agent**：原生 agent 协议支持
- **SGLang-Safety**：内置 guardrails

### 12.3 学术界影响

SGLang 团队在持续发表论文：
- **arXiv:2312.07104** (NeurIPS 2024) — 原始论文
- 后续技术报告 / 简短 arXiv 论文不定期

---

## 13. 关键挑战与开放问题

### 13.1 待解决

1. **多模态原生调度**：当前 LLM + VLM 仍是分开调度
2. **超长上下文（>1M tokens）**：HiCache 3 层后是否需 RDMA 远端
3. **冷启动速度**：冷启动一个 405B 模型需 1-2 分钟
4. **跨数据中心**：调度器未设计为多 region
5. **量化覆盖度**：NVFP4 / FP4 还需更多模型验证
6. **稀疏 + 量化叠加**：HiSparse + FP8 组合场景未完全覆盖
7. **AIGC 商业化**：缺乏 SaaS 平台

### 13.2 与竞争对比的关键差距

- vs **vLLM**：稳定性、企业级 K8s 集成
- vs **TensorRT-LLM**：极致 kernel 性能、closed-source 引擎
- vs **Baseten / Together**：托管 SaaS、计费
- vs **Portkey / LiteLLM**：多模型路由、协议转换

### 13.3 未来 12-24 月可能的变化

- NVIDIA Dynamo（与 SGLang 紧密合作）可能改变 GPU 调度市场
- TPU 市场份额变化（Google Cloud vs AWS Trainium vs Microsoft Maia）
- 端侧 LLM 发展（Apple Silicon、Qualcomm）影响 SGLang 适用场景
- 中国国产 GPU（华为昇腾、寒武纪、摩尔线程）可能让 SGLang 受益

---

## 14. 总结与建议

### 14.1 一句话总结

SGLang 2026 年是**性能领先、端到端可控、生态最广的 LLM 推理引擎**，在工业 de facto 标准的地位上日益巩固。

### 14.2 选型建议

#### 选 SGLang 当

- 你需要运行大模型（>70B）大规模推理
- 你的场景有高 prefix 共享（多轮 chat、agent、RAG）
- 你需要 day-0 支持最新开源模型
- 你想做 RL post-training
- 你需要混合硬件（NV/AMD/TPU/Ascend）
- 你需要极致性能（钱不是问题）

#### 不选 SGLang 当

- 你的场景是简单单卡 7B（小规模）
- 你需要严格 SLA 商业服务（用 Baseten / Together / Replicate）
- 你需要 200+ 模型聚合路由（用 Portkey / LiteLLM）
- 你想零代码搭 LLM 应用（用 OpenAI / Anthropic API）

### 14.3 部署 checklist

- [ ] 选硬件（H100 / H200 / GB200 / MI300X / TPU）
- [ ] 选模型（看 README "Supported Models"）
- [ ] 选精度（BF16 / FP8 / NVFP4 / INT4 AWQ / INT4 GPTQ）
- [ ] 选调度模式（unified / PD-disaggregated / DP / EP / TP）
- [ ] 选 cache 模式（radix / HiCache / HiSparse / off）
- [ ] 选 API 模式（OpenAI 兼容 / Function Calling / Structured Output）
- [ ] 部署（pip / docker / k8s OME / SkyPilot）
- [ ] 监控（Prometheus / OTLP / Grafana）
- [ ] 测试（bench_serving / 压测）
- [ ] 弹性（HPA / PodDisruptionBudget）

### 14.4 关键数据点（再次强调）

| 关键数据 | 数值 |
| --- | --- |
| 在产 GPU 数 | **400,000+** |
| 每天产出 tokens | **Trillions** |
| GitHub stars | 约 16k-18k（2026 H1） |
| 贡献者 | 200+ |
| 主要客户 | xAI, AMD, NVIDIA, LinkedIn, Cursor, Baseten, DeepSeek |
| 性能加速（vLLM baseline） | **1.5-7×**（视场景） |
| 性能加速（TP baseline） | **5×**（DeepSeek-V3 大规模 EP） |
| 1T 参数权重传输 | 7.2 秒（RDMA P2P） |
| Day-0 模型周期 | 1-2 周 |

---

## 附录 A：参考资料

### 论文与博客

1. **arXiv 论文**：
   - Zheng et al. 2023-12 (v1), 2024-06 (v2). "Efficient Execution of Structured Language Model Programs." arXiv:2312.07104
   - 接收：NeurIPS 2024

2. **LMSYS 官方博客**（按时间顺序）：
   - 2024-01-17: SGLang 首发：RadixAttention
   - 2024-02-05: Compressed FSM 3× 加速
   - 2024-07-25: v0.2 vs TensorRT-LLM, vLLM
   - 2024-09-04: v0.3 DeepSeek MLA 7×
   - 2024-12-04: v0.4 Zero-Overhead, Cache-Aware Router
   - 2025-05-05: 大规模 EP on 96 H100
   - 2025-06-16: GB200 Part I 2.7×
   - 2025-09-25: GB200 Part II 4.8×
   - 2025-10-29: SGLang-Jax TPU
   - 2025-11-07 / 2026-01-16: SGLang-Diffusion
   - 2026-02-20: GB300 25×
   - 2026-03-25: Elastic EP
   - 2026-04-10: HiSparse
   - 2026-04-25: DeepSeek-V4 Day-0
   - 2026-04-29: RDMA P2P 1T 7.2s

3. **GitHub 仓库**：
   - 主仓库：https://github.com/sgl-project/sglang
   - TPU 后端：https://github.com/sgl-project/sglang-jax
   - 学习材料：https://github.com/sgl-project/sgl-learning-materials

4. **官方网站**：
   - 文档：https://docs.sglang.io/
   - Roadmap：https://roadmap.sglang.io
   - Slack：https://slack.sglang.io/
   - 周会：https://meet.sglang.io/
   - Diffusion Cookbook：https://cookbook.sglang.io/docs/diffusion/

5. **依赖项目**（致谢）：
   - vLLM, LightLLM, FlashInfer, Outlines, LMQL, Guidance
   - NVIDIA TensorRT-LLM, DeepEP, DeepGEMM
   - AMD AITER, MoRI
   - Mooncake TransferEngine, NIXL
   - xgrammar, DSPy

### 附录 B：性能测试脚本

```bash
# SGLang 自身 benchmark
python -m sglang.bench_serving \
  --backend sglang \
  --num-prompts 1000 \
  --random-input-len 1024 \
  --random-output-len 1024

# vs vLLM 对比
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3-8B-Instruct

# vs TensorRT-LLM (需先构建 engine)
trtllm-build --model_dir ./llama-3-8b --output_dir ./engine

# 详细复现：见 benchmark/ 目录
```

### 附录 C：术语表

| 术语 | 解释 |
| --- | --- |
| **RadixAttention** | SGLang 首创的 KV cache 自动复用技术，用 radix tree 管理 |
| **PD Disaggregation** | Prefill-Decode 分离部署，独立伸缩 |
| **EP** | Expert Parallelism，专家并行（MoE 模型） |
| **TP** | Tensor Parallelism，张量并行 |
| **PP** | Pipeline Parallelism，流水线并行 |
| **DP** | Data Parallelism，数据并行 |
| **DP Attention** | 数据并行 attention（消除 KV cache 重复） |
| **DeepEP** | DeepSeek 开源的 MoE 通信库 |
| **DeepGEMM** | DeepSeek 开源的 FP8 GEMM 库 |
| **Mooncake** | 内存 + 存储 + RDMA 一体化架构项目 |
| **HiCache** | SGLang 的 3 层 KV 缓存（HBM + DDR + NVMe） |
| **HiSparse** | SGLang 的稀疏 attention + 分层 KV 组合 |
| **MoE** | Mixture of Experts，混合专家 |
| **MLA** | Multi-head Latent Attention，DeepSeek 提出的 attention 变体 |
| **PagedAttention** | vLLM 提出的分页 KV cache 管理 |
| **NCCL** | NVIDIA Collective Communications Library |
| **RDMA** | Remote Direct Memory Access，远程直接内存访问 |
| **NVFP4** | NVIDIA 4-bit Floating Point 格式 |
| **Compressed FSM** | 压缩有限状态机，结构化解码优化 |
| **AReaL** | InclusionAI 的 RL 框架 |
| **Miles** | radixark 的 RL 框架（基于 SGLang） |
| **slime** | THUDM 的 RL 框架 |
| **verl** | Volcengine 的 RL 框架 |
| **Tunix** | Google 的 RL 框架 |
| **Rfork** | SGLang 的远程实例权重加载机制 |
| **TransferEngine** | Mooncake 的 RDMA 库 |
| **RPA v3** | Ragged Paged Attention v3（TPU attention） |
| **EAGLE** | SGLang 集成的投机解码算法 |
| **Pallas** | Google TPU 的自定义 kernel 框架 |
| **AITER** | AMD 的 AI Tensor Engine for ROCm |
| **OME** | Open Model Engine，SGLang 的 K8s operator |
| **Dynamo** | NVIDIA 的 GPU 调度系统（与 SGLang 合作） |
| **SkyPilot** | 多云 ML 编排系统 |
| **LMSYS** | UC Berkeley 主导的非营利组织 |
| **MCP** | Model Context Protocol，Anthropic 推出的工具协议 |
| **EPLB** | Expert Parallel Load Balancer |

### 附录 D：与其他 8 份 product 报告的交叉引用

- 与 **product-vllm-20260605.md** 对比：vLLM 是 SGLang 最大的直接对手，二者在 PagedAttention、RadixAttention、PD Disaggregation 思路类似但 SGLang 集成更紧。
- 与 **product-kong-ai-gateway-20260605.md** 对比：Kong AI Gateway 是**上层 API 网关**，SGLang 是**底层推理引擎**，二者互补不冲突。
- 与 **product-portkey-20260605.md** 对比：Portkey 是智能路由网关，SGLang 是被 Portkey 调度的后端之一。
- 与 **product-litellm-20260605.md** 对比：LiteLLM 是 API 聚合网关（200+ 模型），SGLang 是单一推理引擎。
- 与 **product-apisix-ai-proxy-20260605.md** 对比：APISIX AI Proxy 关注流量网关能力，SGLang 关注推理能力。
- 与 **product-envoy-ai-gateway-20260605.md** 对比：Envoy AI Gateway 是 CNCF 系服务网格 AI 扩展，SGLang 是 CNCF 系之外但被 Envoy 集成。
- 与 **product-higress-20260605.md** 对比：Higress 是阿里云系 API 网关，集成多家推理引擎后端包括 SGLang。
- 与 **product-one-api-20260605.md** 对比：One API 是轻量级 LLM 聚合网关，SGLang 是高性能推理引擎。

---

## 结语

SGLang 从 2023-12 一篇 arXiv 论文起步，到 2026-04 已经在 400,000+ GPU 上每天产出 trillions of tokens，**成为工业 de facto 的高性能推理标准**。它代表了 LLM 推理领域的几个重要趋势：

1. **RadixAttention 成为标准**：vLLM 0.6+ 跟进了类似功能
2. **PD Disaggregation 成为大模型标配**：所有头部引擎都集成
3. **Day-0 模型支持成为竞争力**：1-2 周上线新模型
4. **多硬件统一**：NV / AMD / TPU / Ascend 全栈
5. **RL 后端集成**：与训练-推理协同紧密
6. **多模态融合**：文本 + 视觉 + 音频 + 视频 + Diffusion

下一个产品调研：**TGI（Text Generation Inference）**。

---

**报告结束** · 调研人：Rich（OpenClaw AI Assistant） · 2026-06-05
