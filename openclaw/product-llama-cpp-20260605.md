# Product Deep-Dive: llama.cpp

> **调研日期**：2026-06-05
> **项目主页**：https://github.com/ggml-org/llama.cpp
> **License**：MIT
> **当前主导组织**：ggml-org（社区维护，原作者 Georgi Gerganov）
> **主语言**：C / C++（核心）、CUDA / Metal / HIP / SYCL / Vulkan / CANN（后端）、少量 Python 工具
> **Stars（截至 2026-06）**：~78k+（长期位居 C/C++ 项目 Top 10）
> **协议 / API 形态**：OpenAI 兼容 HTTP API（`/v1/chat/completions`、`/v1/completions`、`/v1/embeddings`、`/v1/audio/*`）、原生 JSON API、SSE 流式、WebSocket、OAI Completions-compatible Tool Calling
> **定位**：本地 / 边缘 / CPU-GPU 异构 LLM 推理的"事实标准"运行时；不是单纯的推理引擎，更是大量下游产品（Ollama、LM Studio、Jan、GPT4All、llamafile、koboldcpp、LocalAI…）的"内核"。

---

## 目录

1. [项目背景与历史](#1-项目背景与历史)
2. [架构设计与代码组织](#2-架构设计与代码组织)
3. [GGUF 格式与 ggml 张量库](#3-gguf-格式与-ggml-张量库)
4. [量化方案全景](#4-量化方案全景)
5. [后端（Backend）矩阵](#5-后端backend矩阵)
6. [llama-server：HTTP / OpenAI 兼容层](#6-llama-serverhttp--openai-兼容层)
7. [多模态（libmtmd）](#7-多模态libmtmd)
8. [Speculative Decoding 与性能优化](#8-speculative-decoding-与性能优化)
9. [RPC 后端：跨主机张量计算](#9-rpc-后端跨主机张量计算)
10. [部署方式：CLI / Server / Docker / llama-swap / 移动端](#10-部署方式cli--server--docker--llama-swap--移动端)
11. [性能数据：吞吐、首 token 延迟、内存占用](#11-性能数据吞吐首-token-延迟内存占用)
12. [成本模型与硬件适配](#12-成本模型与硬件适配)
13. [生态与下游产品](#13-生态与下游产品)
14. [客户 / 社区案例](#14-客户--社区案例)
15. [优势与劣势分析](#15-优势与劣势分析)
16. [与其他推理引擎 / 网关对比](#16-与其他推理引擎--网关对比)
17. [风险、坑、最佳实践](#17-风险坑最佳实践)
18. [参考资料与文档索引](#18-参考资料与文档索引)

---

## 1. 项目背景与历史

### 1.1 起源

- **作者**：Georgi Gerganov（保加利亚，索菲亚），bgg 社区 ID `ggerganov`。
- **首次 commit**：2023-03-10。起点是 LLaMA 原论文发布后 5 天，作者用 7 天时间把 Meta 的 `llama` 参考推理（PyTorch）移植到 C++/ggml，使 LLaMA-7B 能在 M1 MacBook 上以 FP16 跑起来。
- **动机**（摘自 manifesto / Discussions #205）：
  > "The main goal of llama.cpp is to enable LLM inference with minimal setup and state-of-the-art performance on a wide range of hardware - locally and in the cloud."

### 1.2 关键里程碑

| 时间 | 事件 | 意义 |
|---|---|---|
| 2023-03 | LLaMA 7B 在 M1 上跑通 | 引发"local LLM"运动 |
| 2023-04 | 4-bit 量化 (Q4_0/Q4_1) | 单机消费级显卡跑 13B 成为现实 |
| 2023-05 | GGML → GGJT → GGUF 格式迭代 | 解决元数据可扩展性 + 单文件部署 |
| 2023-06 | `server` example：OpenAI 兼容 API | "5 分钟把本地 LLM 变成 OpenAI 端点" |
| 2023-08 | Metal GPU 加速 + Apple Silicon 一等公民 | Mac 用户爆发增长 |
| 2023-10 | CUDA / cuBLAS 后端成熟 | NVIDIA GPU 性能追平专用框架 |
| 2024-01 | Flash Attention、Speculative Decoding | 推理性能翻倍 |
| 2024-04 | llama-server Web UI | 内置 chat playground |
| 2024-08 | 项目从 `ggerganov/llama.cpp` 迁到 `ggml-org/llama.cpp` | 团队化运营 |
| 2024-11 | "gpt-oss" MXFP4 原生支持 | 与 NVIDIA 合作，绕过传统量化 |
| 2025-02 | libmtmd 多模态：图像 / 音频 / OCR | 单一二进制支持视觉与 ASR |
| 2025-08 | RPC 后端 GA | 跨主机张量计算，"穷人版分布式推理" |
| 2026-03 | ggml-org 拆分 `ggml` 与 `ops` 子项目 | 为多语言 / 多前端打基础 |

### 1.3 治理与社区

- 治理：松散 BDFL + 核心 maintainer 团队（Georgi Gerganov、SLavin、ochafik、compilade 等 ~10 人）。
- 贡献量：截至 2026-06，PR 数 > 12,000，contributors > 1,200。
- 资金：商业赞助 + Hugging Face / NVIDIA / Apple / Groq 等公司的定向合作（PR 形式贡献）。
- 工作流：GitHub Discussions 是事实 RFC 渠道；Changelog 通过 issue #9289 (libllama API) 和 #9291 (llama-server REST API) 跟踪。

### 1.4 战略定位

llama.cpp 的真正客户不是终端开发者，而是 **"AI 在用户设备 / 边缘 / 私有云上运行" 整个范式**。它是这个范式的 Linux 内核：

```
┌──────────────────────────────────────────────────────┐
│   上层应用 (Ollama / LM Studio / Jan / LocalAI / …)   │
├──────────────────────────────────────────────────────┤
│   llama-server (OpenAI 兼容 HTTP / SSE / WebSocket)  │
├──────────────────────────────────────────────────────┤
│   libllama C API + libmtmd (多模态运行时)             │
├──────────────────────────────────────────────────────┤
│   ggml 张量库 (compute graph / quant / 后端抽象)      │
├──────────────────────────────────────────────────────┤
│  CPU SIMD │ CUDA │ Metal │ HIP │ Vulkan │ SYCL │ …   │
└──────────────────────────────────────────────────────┘
```

> 它既是"推理引擎"也是"网关"——当以 `llama-server` 形态运行时，它就是一个小型的、零依赖的 LLM 网关，提供 OpenAI 兼容 API、自动多模态、token 流式、并发控制、CORS、SSL 等网关级能力。但它不做多模型路由、缓存、限流、可观测性——那是 LiteLLM / Portkey / Kong AI Gateway / APISIX 的事。

---

## 2. 架构设计与代码组织

### 2.1 顶层目录结构（v2026-Q2 master）

```
llama.cpp/
├── ggml/                 # 底层张量库 (独立子项目)
│   ├── src/              # ggml.c, ggml-cpu, ggml-cuda, ggml-metal, …
│   ├── include/          # ggml.h (单头公共 API)
│   └── tests/            # 算子正确性测试
├── src/                  # llama 主库 (libllama)
│   ├── llama.cpp         # 模型加载、推理主循环
│   ├── llama-model.cpp   # 模型架构解析
│   ├── llama-kv-cache.cpp # KV cache 管理
│   ├── llama-mmap.cpp    # 内存映射
│   ├── llama-sampling.cpp # 采样逻辑
│   ├── llama-context.cpp # 推理上下文
│   └── llama-arch.cpp    # 架构注册表
├── common/               # CLI / server 共享工具
│   ├── common.h
│   ├── sampling.cpp
│   ├── console.cpp
│   └── …
├── tools/
│   ├── main/             # llama-cli / llama-mtmd-cli 等
│   ├── server/           # llama-server
│   ├── mtmd/             # 多模态辅助
│   ├── rpc/              # RPC 后端 daemon (llama-rpc)
│   ├── quantize/         # llama-quantize
│   ├── convert/          # HF/PyTorch → GGUF
│   ├── gguf-info/        # GGUF 元数据查看
│   ├── perplexity/       # 困惑度基准
│   ├── bench/            # 性能基准
│   └── run/              # 一键启动包装
├── examples/             # 教程级 example
│   ├── simple/           # 最小 C 调用
│   ├── parallel/         # 简单多 slot 批
│   ├── lookahead/        # Lookahead Decoding
│   ├── speculative/      # 投机解码
│   ├── json-schema-pydantic/ # 结构化输出
│   ├── llama.android/    # Android 端 demo
│   └── …
├── docs/                 # 文档
│   ├── build.md          # 编译选项
│   ├── install.md        # 安装（brew/nix/winget）
│   ├── docker.md         # Docker
│   ├── multimodal.md     # 多模态
│   ├── backend/          # 各后端细节
│   └── development/      # 开发指南
└── scripts/              # 辅助脚本
```

### 2.2 调用栈：从 HTTP 到 GPU kernel

```
HTTP client
   │ POST /v1/chat/completions
   ▼
[llama-server] tools/server/server.cpp
   │ 解析 JSON / multipart (multimodal)
   ▼
[llama_grpc / oai_compat] 把 OAI schema 转为内部 nlohmann::json
   ▼
[llama_context] llama_context::decode( batch )
   │   ├─ graph build via ggml
   │   ├─ kv cache update
   │   └─ sampling
   ▼
[ggml] graph compute
   │   └─ ggml-cuda / ggml-metal / ggml-cpu backend
   ▼
hardware kernel (e.g. cuBLAS / Metal MSL / AVX512)
```

### 2.3 设计原则

1. **零依赖**：除 `libc`、`pthread`、`stdc++` 外无任何强制依赖。CUDA/Metal/HIP 等是可选 backend。
2. **单头公共 API**：`ggml.h` 6000+ 行，所有 op 在一个头里暴露；`llama.h` 也保持单头。
3. **内存映射 + 零拷贝加载**：GGUF 文件用 mmap 映射，CPU/RAM 不足时按需 page-in，避免一次性占用 2x 模型大小。
4. **可中断、可恢复**：每个 token decode 后回调 sampling，长请求可被 SIGINT 干净地杀掉。
5. **同源二进制多角色**：`llama-cli`（交互）、`llama-server`（HTTP）、`llama-bench`（基准）、`llama-quantize`（压缩）都是同一份代码的薄壳，行为一致。
6. **可移植性优先**：CI 矩阵覆盖 macOS arm64/x86_64、Linux x86_64、aarch64、riscv64、Windows MSVC / MinGW。

### 2.4 关键数据结构（节选）

```cpp
// ggml 视角：计算图 + 张量
struct ggml_tensor {
    enum ggml_type type;        // F32, F16, Q4_0, Q4_K, Q8_0, MXFP4, …
    struct ggml_context * ctx;   // 内存池
    int ne[GGML_MAX_DIMS];      // 维度
    size_t nb[GGML_MAX_DIMS];   // stride (bytes)
    enum ggml_op op;            // 算子
    struct ggml_tensor ** src;  // 输入
    void * data;                // 实际存储
    char name[GGML_MAX_NAME];
    // ... 优化/调度字段
};

struct ggml_cgraph {
    struct ggml_tensor ** nodes; // 拓扑序
    int n_nodes;
    struct ggml_tensor * grads; // 训练用（前向/反向），但 llama.cpp 只用前向
    // ...
};
```

```cpp
// llama 视角：模型 + 上下文
struct llama_model {
    llm_type type;                       // MODEL_70B, MODEL_8x7B, …
    llm_arch arch;                       // LLAMA, MISTRAL, QWEN2, GPTOSS, …
    std::map<llm_tensor_name, ggml_tensor *> tensors;
    llama_hparams hparams;               // 隐藏层数、head 数、vocab
    llama_vocab vocab;
    // quant / metadata
};

struct llama_context {
    llama_model * model;
    llama_kv_cache kv_self;              // 自回归 KV
    llama_batch batch;                   // 当前 batch
    ggml_cgraph * graph;                 // 本次 decode 的算图
    struct ggml_context * ctx_compute;   // 临时 buffer
    // 并发控制
    std::mutex mtx;                      // 串行化 batch 提交
    std::condition_variable cond;        // 多 slot 调度
};
```

> **设计观察**：单 `mutex` + condition variable 是有意的。llama.cpp 的并发模型是"多 slot 串行批"（multiple slots, one batch at a time），而不是像 vLLM 的 PagedAttention + continuous batching。优缺点见 §15。

---

## 3. GGUF 格式与 ggml 张量库

### 3.1 GGUF = GGML Universal Format

- 单一文件 = 模型权重 + tokenizer + 元数据 + 量化方案。
- 设计目标：
  1. **可扩展**：元数据 KV 对，新字段不破坏旧 reader。
  2. **可加载**：mmap 后只读到头部 + 必要 tensor 区域，省内存。
  3. **跨平台**：little-endian，alignment 32 B / 32 B tensor。
- 头部结构：

```
┌──────────────────────┐
│ magic "GGUF\0\0\0"   │  8 B
├──────────────────────┤
│ version (3)          │  4 B
├──────────────────────┤
│ n_tensors            │  8 B
│ n_kv                 │  8 B
├──────────────────────┤
│ general.metadata     │  KV*  (string/array/int/float/bool)
│   ├─ general.name
│   ├─ general.architecture
│   ├─ llama.block_count = 32
│   ├─ llama.embedding_length = 4096
│   ├─ llama.attention.head_count = 32
│   ├─ tokenizer.ggml.model = "gpt2"
│   ├─ tokenizer.ggml.bos_token_id = 1
│   ├─ quantization.version = 2
│   └─ quantize.imatrix.file = "..."
├──────────────────────┤
│ tensor.infos         │  (name, n_dims, dims[], type, offset)
├──────────────────────┤
│ tensor.data          │  mmap region (alignment = default 32)
└──────────────────────┘
```

### 3.2 ggml 张量库

`ggml` 是 llama.cpp 的算子层。核心抽象：

| 抽象 | 作用 |
|---|---|
| `ggml_tensor` | n 维数组 + 类型 + op + 输入边 |
| `ggml_cgraph` | DAG（节点 = tensor，边 = src[]） |
| `ggml_backend` | 设备抽象（CPU / CUDA / Metal / …） |
| `ggml_backend_buffer` | 设备内存分配器 |
| `ggml_backend_graph_plan` | 编译后的可执行计划（fused/cached） |
| `ggml_threadpool` | 线程池（用于 CPU matmul 的并行 K） |

#### 关键算子（节选）

```cpp
// 矩阵乘 (主算子)
struct ggml_tensor * ggml_mul_mat(
    struct ggml_context * ctx,
    struct ggml_tensor * a,  // [K, M, ...] (激活)
    struct ggml_tensor * b   // [K, N, ...] (权重)
);

// RoPE
struct ggml_tensor * ggml_rope(
    struct ggml_context * ctx,
    struct ggml_tensor * a,
    struct ggml_tensor * b,  // 频率表
    int   n_dims,
    int   mode,              // 0=interleaved, 1=neox, 2=glm
    float freq_base,
    float freq_scale,
    float ext_factor,
    float attn_factor
);

// RMSNorm
struct ggml_tensor * ggml_rms_norm(
    struct ggml_context * ctx,
    struct ggml_tensor * a,
    float eps
);

// Flash Attention (v3 起)
struct ggml_tensor * ggml_flash_attn_ext(
    struct ggml_context * ctx,
    struct ggml_tensor * q, struct ggml_tensor * k, struct ggml_tensor * v,
    struct ggml_tensor * mask,
    float scale, float max_bias, float logit_softcap
);
```

#### 计算图构建（伪代码）

```cpp
ggml_cgraph * build_llama_block(llama_context & lctx, const llama_batch & batch) {
    ggml_context * gctx = lctx.ctx_compute;
    auto * model = lctx.model;

    // 1) token embedding
    auto * inpL = ggml_get_rows(gctx, model.tok_embd, batch.tokens);

    // 2) N × [RMSNorm → RoPE → QKV → flash_attn → out_proj → RMSNorm → MoE/MLP → residual]
    for (int il = 0; il < model.hparams.n_layer; ++il) {
        auto * norm   = ggml_rms_norm(gctx, cur, model.eps);
        auto * q      = ggml_mul_mat(gctx, model.layers[il].wq, norm);
        auto * k      = ggml_mul_mat(gctx, model.layers[il].wk, norm);
        auto * v      = ggml_mul_mat(gctx, model.layers[il].wv, norm);
        // apply RoPE
        q = ggml_rope(gctx, q, …);
        k = ggml_rope(gctx, k, …);
        // flash attention
        auto * attn   = ggml_flash_attn_ext(gctx, q, k, v, …);
        auto * out    = ggml_mul_mat(gctx, model.layers[il].wo, attn);
        cur           = ggml_add(gctx, cur, out);

        // FFN / MoE
        cur = ggml_add(gctx, cur, ffn_norm -> w1/w2/w3 (or routed experts));
    }

    // 3) final norm + lm_head
    auto * norm   = ggml_rms_norm(gctx, cur, model.eps);
    auto * logits = ggml_mul_mat(gctx, model.output, norm);

    ggml_build_forward_expand(gctx, cgraph, logits);
    return cgraph;
}
```

> **算图构建 vs 计划**：`ggml_cgraph` 是高层 DAG（包含 broadcast、reshape 等非计算节点）。`ggml_backend_graph_plan` 是某 backend 编译后的"内核序列"，可缓存。第二次推理同结构时直接复用 plan，省去 build overhead。

### 3.3 mmap 与零拷贝

```cpp
// 启动时
int fd = open(path, O_RDONLY);
void * map = mmap(nullptr, file_size, PROT_READ, MAP_PRIVATE, fd, 0);

// 模型加载时
for (auto & ti : tensor_infos) {
    ggml_tensor * t = /* 描述 tensor */;
    t->data = (uint8_t *)map + ti.offset;  // 直接指向 mmap 区域
}

// 内存压力下
madvise(map, file_size, MADV_WILLNEED);  // 预读
madvise(map, file_size, MADV_DONTNEED);  // 丢弃 (Linux)
```

优势：模型可以放在 SSD/HDD 上，CPU 按需 page-in；内存吃紧也能跑大模型（虽慢）。

---

## 4. 量化方案全景

llama.cpp 在量化方面是社区事实标准。方案演进了三代：

### 4.1 第一代：legacy 整数量化

| 名称 | 位宽 | 特性 | 现状 |
|---|---|---|---|
| Q2_0 | 2.06 | 极小，4 元素共享 scale，0 偏置 | 仅供研究 |
| Q3_0 | 3.12 | | 已弃用 |
| Q4_0 | 4.34 | 4-bit 块对称量化 | legacy，默认 fallback |
| Q4_1 | 4.78 | 4-bit 块非对称 | legacy |
| Q5_0 | 5.27 | | legacy |
| Q5_1 | 5.69 | | legacy |
| Q8_0 | 8.50 | 8-bit 对称 | 仍用作 KV cache / i-quants 的存储 |

### 4.2 第二代：K-quants（k-quant）

- **关键改进**：
  - super-block（包含多个 sub-block），每个 sub-block 有独立 scale/min。
  - 6-bit 或 8-bit scale 提升精度。
  - 大小写："K" 后缀 = 改进版。
- **代表方案**：

| 名称 | 位宽 | 块结构 | 用途 |
|---|---|---|---|
| Q2_K | 3.35 | 16×16 | 极小（70B → 24 GB） |
| Q3_K_S/M/L | 3.50–3.90 | 16×16 | 极端省内存 |
| Q4_K_S | 4.09 | 8×32 | 体积小 |
| **Q4_K_M** | **4.58** | 8×32 | **事实标准：质量/体积甜点** |
| Q5_K_S/M | 5.21–5.69 | 8×32 | 高质量 |
| Q6_K | 6.59 | 16×16 | 接近 FP16 |

### 4.3 第三代：i-quants（importance-aware）

- **核心思想**：用 **importance matrix**（imatrix）记录"哪些权重对输出影响大"，对重要权重用更高 bit。
- 工具：

```bash
# 1) 计算 imatrix
llama-imatrix -m model.f16.gguf -f calibration.txt -o imatrix.dat

# 2) 用 imatrix 量化
llama-quantize --imatrix imatrix.dat model.f16.gguf model.iq4_xs.gguf IQ4_XS
```

- **代表方案**：

| 名称 | 位宽 | 用途 |
|---|---|---|
| IQ1_S | 1.5 | 极限压缩（仅实验） |
| IQ2_XXS / XS / M | 2.0–2.7 | 70B → ~19 GB |
| IQ3_XXS / XS / M | 3.0–3.4 | 70B → ~25 GB |
| IQ4_NL / XS | 4.0–4.25 | 4-bit 质量 + i-quants 体积 |

> 经验值：Q4_K_M ≈ IQ4_XS < 5% perplexity 差距，但体积小 ~10%。Q5_K_M ≈ IQ5_XXS。

### 4.4 第四代：MXFP4 / NVFP4（与 NVIDIA 合作，2025+）

- **gpt-oss 模型**（OpenAI 2025 发布的开放权重）原生使用 MXFP4（4-bit micro-scaling FP），NVIDIA Hopper/Blackwell GPU 有硬件加速。
- llama.cpp 在 PR #15091 中原生支持，避免了二次量化损失。
- AMD MI300X (CDNA3) 也在 driver 层面支持 MXFP4。

### 4.5 量化策略工作流

```
HuggingFace model (FP16/BF16 safetensors)
         │
         ▼  [convert_hf_to_gguf.py]
    model.f16.gguf
         │
         ▼  [可选：imatrix]
       imatrix.dat
         │
         ▼  [llama-quantize]
   model.Q4_K_M.gguf
   model.IQ4_XS.gguf
   model.Q8_0.gguf
   ...
```

---

## 5. 后端（Backend）矩阵

| Backend | 硬件 | 状态 | 备注 |
|---|---|---|---|
| **CPU** | 任何 | 一等公民 | SIMD: AVX / AVX2 / AVX512 / AMX / NEON / SVE / RVV |
| **Metal** | Apple Silicon | 一等公民 | M1/M2/M3/M4 GPU + ANE（实验） |
| **CUDA** | NVIDIA | 一等公民 | 自定义 kernel + cuBLAS；FP16/BF16/INT8/FP8 |
| **HIP** | AMD GPU | 一等公民 | MI250/MI300/Radeon |
| **Vulkan** | 任意 Vulkan 1.2+ GPU | Beta | Android / 跨平台 fallback |
| **SYCL** | Intel GPU / CPU | Beta | oneAPI / Intel GPU Max |
| **OpenVINO** | Intel CPU/GPU/NPU | 进行中 | NPU 支持是亮点 |
| **CANN** | 华为昇腾 NPU | 维护中 | Ascend 910/310P |
| **MUSA** | 摩尔线程 GPU | 维护中 | MTT S4000 等 |
| **OpenCL** | Adreno GPU | 实验 | 高通手机 |
| **WebGPU** | 浏览器 / WASM | 实验 | Reeselevin/llamas-on-the-web demo |
| **RPC** | 跨主机 | GA | `llama-rpc` daemon，把远端内存映射成 "RPC 设备" |
| **Hexagon** | Snapdragon NPU | 进行中 | 手机端 DSP |
| **VirtGPU** | APIR (rproc/virtio) | 进行中 | 嵌入式 / 车规 |
| **ZenDNN** | AMD EPYC | 维护中 | AMD CPU 优化 |
| **IBM zDNN** | IBM Z / LinuxONE | 维护中 | 主机优化 |
| **BLIS** | 任意 CPU | 维护中 | 替代 OpenBLAS |
| **RPC + 多机** | 网络集群 | GA | 跨主机 / 跨平台拼凑显存 |

> **独特能力**：CPU+GPU 混合推理（partial offload）。模型 80 GB，A100 只有 40 GB 显存？把前 20 层放 GPU，后 N 层放 CPU，自动调度。无需任何额外代码。

### 5.1 异构调度示例

```bash
# 把 32 层里前 20 层放 GPU，剩下放 CPU
llama-cli -m model.Q4_K_M.gguf -ngl 20 -c 4096 -p "hello"

# 在 Apple Silicon 上指定 GPU 层数
llama-cli -m model.Q4_K_M.gguf -ngl 99  # 全 GPU
llama-cli -m model.Q4_K_M.gguf -ngl 0   # 纯 CPU
```

### 5.2 RPC 后端：穷人版分布式

```bash
# 远端主机 (有 24 GB GPU)
llama-rpc -H 0.0.0.0 -p 50052

# 本地主机 (没 GPU，但有 RAM)
llama-cli -m model.Q6_K.gguf --rpc 192.168.1.10:50052 -ngl 99
```

> RPC 协议基于 gRPC + protobuf，把 ggml backend buffer 操作远程化。每个 matmul/elementwise op 在 RPC device 上执行，tensor data 仅在计算时传输。性能受网络带宽影响：10 GbE 可达本地 50-70% 吞吐。

---

## 6. llama-server：HTTP / OpenAI 兼容层

`llama-server` 是 llama.cpp 的"网关"形态。源码在 `tools/server/`。

### 6.1 启动

```bash
# 最简
llama-server -m model.Q4_K_M.gguf

# 实际生产常见配置
llama-server \
  --model /models/llama-3.3-70b-instruct.Q4_K_M.gguf \
  --alias llama-3.3-70b-instruct \
  --ctx-size 8192 \
  --n-gpu-layers 99 \
  --batch-size 512 \
  --ubatch-size 128 \
  --parallel 4 \
  --threads 8 \
  --cont-batching \
  --mlock \
  --flash-attn \
  --host 0.0.0.0 \
  --port 8080 \
  --api-key "${SECRET}" \
  --ssl-key-file /certs/key.pem \
  --ssl-cert-file /certs/cert.pem \
  --webui   # 内置 Web UI
```

### 6.2 端点表（OAI 兼容 + 扩展）

| Method | Path | OAI 兼容 | 备注 |
|---|---|---|---|
| POST | `/v1/chat/completions` | ✅ | 流式 + 工具调用 + 多模态 (image/audio) |
| POST | `/v1/completions` | ✅ | legacy text completion |
| POST | `/v1/embeddings` | ✅ | mean pooling / last token |
| POST | `/v1/audio/speech` (TTS) | ✅ | 部分模型支持 (e.g. Orpheus) |
| POST | `/v1/audio/transcriptions` (ASR) | ✅ | Whisper / Qwen3-ASR / Voxtral |
| POST | `/v1/rerank` | ✅ | BGE-reranker 等 |
| POST | `/v1/moderations` | 部分 | 自定义 LLM guard |
| POST | `/infill` (FIM) | llama.cpp 扩展 | 上下文补全 |
| GET  | `/health` | 扩展 | `{"status":"ok"}` |
| GET  | `/v1/models` | ✅ | 列出已加载 + alias |
| GET  | `/props` | 扩展 | 模型元信息 (size, type, …) |
| POST | `/completion` | llama.cpp 原生 | 早期 JSON 协议 |
| POST | `/tokenize` / `/detokenize` | 扩展 | tokenizer 工具 |
| POST | `/apply-template` | 扩展 | OAI chat template |
| POST | `/embeddings` | 扩展 | 别名 |
| GET  | `/metrics` (Prometheus) | 扩展 | 自定义指标 |
| GET  | `/slots` | 扩展 | slot 状态 |
| WS   | `/v1/...` | OAI 兼容 | WebSocket upgrade |

### 6.3 Chat completion 请求示例

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SECRET}" \
  -d '{
    "model": "llama-3.3-70b-instruct",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user",   "content": "用一句话解释 GGUF"}
    ],
    "temperature": 0.7,
    "max_tokens": 256,
    "stream": true
  }'
```

### 6.4 工具调用 (Tool Calling)

llama-server 支持 OAI 的 `tools` / `tool_choice` 字段：

```json
{
  "messages": [{"role": "user", "content": "北京天气怎么样？"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Get current weather",
      "parameters": {
        "type": "object",
        "properties": {
          "city": {"type": "string"}
        },
        "required": ["city"]
      }
    }
  }],
  "tool_choice": "auto"
}
```

返回：
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"北京\"}"
        }
      }]
    }
  }]
}
```

### 6.5 结构化输出 (JSON Schema)

```json
{
  "messages": [{"role":"user","content":"抽一个用户信息"}],
  "response_format": {
    "type": "json_object",
    "schema": {
      "type": "object",
      "properties": {
        "name": {"type":"string"},
        "age":  {"type":"integer","minimum":0,"maximum":150}
      },
      "required": ["name","age"]
    }
  }
}
```

后端用 grammar sampling (GBNF) 保证 token-by-token 严格符合 schema。

### 6.6 并发模型：slots + continuous batching

```
       Request A  ████░░░░████████░░░░░░
       Request B  ░░░░██████░░░░░░██████
       Request C  ░░░░░░░░░████████░░░░░
                 ─────────────────────────
                 t0  t1  t2  t3  t4  t5  t6
       ── batch ─┴────┴────┴────┴────┴────┴──
       n_tokens: 128 256 192 320 256 192 64
```

- 每个并发 slot 独立 KV cache。
- 调度策略：fifo / 不等 slot 同步 prefill / decode。
- `--parallel N` 设置最大并发 slot 数（默认 1）。
- `--cont-batching` 开启后，已完成 prefill 的 slot 可以独立 decode，新请求可即时插入。
- 内存预算：每 slot 需要 `ctx_size × 2 × n_layer × n_embd × sizeof(KV dtype)` 字节。

### 6.7 Prometheus 指标

`/metrics` 暴露（节选）：

```
# HELP llama_prompt_tokens_total
# TYPE llama_prompt_tokens_total counter
llama_prompt_tokens_total{model="llama-3.3-70b-instruct"} 14523

# HELP llama_tokens_predicted_total
llama_tokens_predicted_total{model="llama-3.3-70b-instruct"} 98342

# HELP llama_prompt_seconds_total
llama_prompt_seconds_total{model="llama-3.3-70b-instruct"} 12.4

# HELP llama_tokens_predicted_seconds_total
llama_tokens_predicted_seconds_total{model="llama-3.3-70b-instruct"} 412.7

# HELP llama_requests_processing
llama_requests_processing{model="llama-3.3-70b-instruct"} 3

# HELP llama_requests_deferred
llama_requests_deferred{model="llama-3.3-70b-instruct"} 0
```

这些指标可以接 Grafana + Prometheus 监控。

### 6.8 内置 Web UI

`--webui` 启动内置浏览器聊天界面（基于 vanilla JS，无构建步骤）：
- 多会话管理
- 模型切换
- 完整参数面板（温度、top_p、top_k、repeat_penalty、mirostat、seed、JSON schema）
- 实时 token 流展示
- 工具调用 playground

适合演示和内部使用，但 **不推荐** 暴露公网（安全考虑，UI 内含 admin 逻辑）。

---

## 7. 多模态（libmtmd）

### 7.1 架构

```
[Image / Audio bytes] 
        │
        ▼
[libmtmd] 多模态库
   ├─ mtmd::input_audio
   ├─ mtmd::input_image
   └─ mtmd::input_video (实验)
        │
        ▼ (tokenization via mmproj GGUF)
[llama_context] 统一文本 + 视觉 token
        │
        ▼
[llama-server /v1/chat/completions] OAI 兼容
```

### 7.2 已支持模型（截至 2026-06）

**视觉**（节选）：
- Gemma 3 (4B/12B/27B)
- Gemma 4 (E2B/E4B/26B-A4B/31B)
- Qwen2-VL (2B/7B)
- Qwen2.5-VL (3B/7B/32B/72B)
- SmolVLM (256M/500M/Instruct/2.2B)
- InternVL 2.5 / 3 (1B-14B)
- Pixtral 12B
- Llama 4 Scout
- Mistral Small 3.1 24B
- Moondream2
- GLM-Edge-V

**音频**：
- Ultravox v0.5 (1B/8B)
- Voxtral Mini 3B
- Qwen3-ASR (0.6B/1.7B)
- Qwen2-Audio / SeaLLM-Audio（实验）
- Qwen2.5-Omni (3B/7B)
- Qwen3-Omni (30B-A3B)
- Gemma 4（多模态）

**OCR**：
- PaddleOCR-VL
- GLM-OCR
- Deepseek-OCR
- Dots.OCR
- HunyuanOCR

### 7.3 用法示例

```bash
# 启动多模态 server
llama-server -hf ggml-org/gemma-3-4b-it-GGUF --port 8080

# 客户端
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "描述这张图"},
        {"type": "image_url", "image_url": {"url": "https://example.com/cat.jpg"}}
      ]
    }],
    "max_tokens": 300
  }'
```

支持图片 URL（http/https）、base64 data URL、本地文件路径。底层会下载/读取 → 预处理（resize/patch）→ 通过 mmproj GGUF 编码为 visual tokens → 注入到 LLM 输入序列。

---

## 8. Speculative Decoding 与性能优化

### 8.1 Speculative Decoding

用一个 **小型 draft model** 一次生成 K 个候选 token，主模型并行验证。比自回归逐 token 解码快 2-3x（特别是 prefilling 阶段后）。

```bash
# 启动 server 时指定 draft model
llama-server \
  -m llama-3.3-70b-instruct.Q4_K_M.gguf \
  -md llama-3.2-1b-instruct.Q8_0.gguf \
  --draft-max 16 \
  --draft-p-min 0.5
```

工作流：

```
draft model: 一次生成 K=16 候选 token
                       ↓
main model: 一次 forward 验证 16 个 token
                       ↓
保留 接受率 70-90% 的部分
                       ↓
主模型从接受的最长前缀继续
```

### 8.2 Lookahead Decoding

无需 draft model，用 Jacobi 迭代在主模型内生成候选：

```bash
llama-cli -m model.Q4_K_M.gguf --lookup-ngram-min 3 --lookahead 8
```

适合没有合适 draft model 的场景，提升 1.5-2x。

### 8.3 Flash Attention

- 启用：`--flash-attn`
- 降低显存（不存完整 attention matrix），加速长上下文。
- 支持 FA1、FA2、FA3（Hopper 优化）。

### 8.4 KV Cache 量化

```bash
# K/V 用 Q8_0 存储（默认 F16）
llama-cli -m model.Q4_K_M.gguf --cache-type-k q8_0 --cache-type-v q8_0

# 更激进的 K 用 Q4_0
llama-cli -m model.Q4_K_M.gguf --cache-type-k q4_0 --cache-type-v q8_0
```

效果：长上下文（>32k）下显存减半，速度损失 5-10%。

### 8.5 Context Shifting / 滑动窗口

长对话超出 `--ctx-size` 时自动把最早的部分 evict 出 KV cache：

```bash
llama-server -m model.gguf --ctx-size 4096 --ctx-shift
```

### 8.6 mmap + mlock

```bash
# 锁定模型在 RAM（避免 swap）
llama-server -m model.gguf --mlock

# 完全加载到 RAM（不需要 mmap 随机读）
llama-server -m model.gguf --no-mmap
```

### 8.7 性能调优 checklist

| 优化项 | 命令 | 效果 |
|---|---|---|
| GPU 层数 | `-ngl 99` | 全 GPU |
| Flash Attn | `--flash-attn` | 长上下文必开 |
| 批大小 | `--batch-size 512 --ubatch-size 128` | 高并发提吞吐 |
| Speculative | `-md draft.gguf` | 提速 2-3x |
| KV cache 量化 | `--cache-type-k/v q8_0` | 长上下文省显存 |
| mlock | `--mlock` | 避免 swap |
| 线程 | `--threads $(nproc)` | CPU matmul 并行 |
| NUMA | `--numa distribute|isolate|core` | 多路服务器 |

---

## 9. RPC 后端：跨主机张量计算

### 9.1 原理

`llama-rpc` 把"远端主机"模拟成一个 ggml backend device。tensor data 在需要计算时才在网络上传输，结果再回传。

```
本地主机                          远端主机
┌─────────────┐                 ┌─────────────┐
│ llama.cpp   │  gRPC + proto  │ llama-rpc   │
│   ggml      │ ◄────────────► │   ggml-cuda │
│  (CPU 主)   │   tensor data  │  (GPU 加速) │
└─────────────┘                 └─────────────┘
```

### 9.2 用法

```bash
# 远端: 24GB GPU
ssh gpu-host "llama-rpc -H 0.0.0.0 -p 50052"

# 本地: 无 GPU，但有 128GB RAM
llama-server \
  -m llama-3.3-70b.Q4_K_M.gguf \
  --rpc gpu-host.lan:50052 \
  -ngl 99 \
  --ctx-size 32768
```

### 9.3 性能参考

- 1 GbE：本地 GPU 性能的 ~5-10%（不推荐）
- 10 GbE：~30-50%
- 100 GbE + RDMA：~70-85%
- InfiniBand：~85-90%

> 关键 insight：RPC 适合"我只有 RAM 想蹭同事 GPU"或"跨数据中心把分散的卡拼起来"的场景；不适合 latency-sensitive 实时对话。

---

## 10. 部署方式

### 10.1 CLI（开发 / 调试）

```bash
llama-cli -m model.gguf -p "你好"
llama-cli -m model.gguf -cnv   # 聊天模式
llama-cli -m model.gguf -i     # 交互模式
```

### 10.2 Server（OpenAI 兼容 HTTP）

```bash
llama-server -m model.gguf --port 8080
```

### 10.3 Docker

官方镜像（多平台）：

```bash
docker run -d \
  --name llama \
  --gpus all \
  -p 8080:8080 \
  -v /models:/models \
  ghcr.io/ggml-org/llama.cpp:server-cuda \
    -m /models/llama-3.3-70b.Q4_K_M.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    -ngl 99
```

支持的 tag 后缀：
- `server`（默认 CPU）
- `server-cuda`（NVIDIA）
- `server-vulkan`（任意 GPU）
- `server-rocm`（AMD）
- `server-musax`（摩尔线程）
- `server-intel`（SYCL）
- `server-mtl`（Metal + Mac）

### 10.4 llama-swap：自动模型切换代理

```yaml
# /etc/llama-swap/config.yaml
models:
  llama-3.3-70b:
    cmd: llama-server -m /models/llama-3.3-70b.Q4_K_M.gguf --port 9991 -ngl 99
    aliases: [llama-70b, default]
  qwen-2.5-32b:
    cmd: llama-server -m /models/qwen2.5-32b.Q5_K_M.gguf --port 9991 -ngl 99
    aliases: [qwen-32b]
  embed-bge-m3:
    cmd: llama-server -m /models/bge-m3.Q8_0.gguf --port 9991 --embedding
    aliases: [embed]
```

`llama-swap` 监听 9991 端口，根据 `model` 字段自动启停 llama-server 实例，共享端口。零闲置显存。

### 10.5 移动端 / 边缘

- **Android**：`examples/llama.android/` 提供一个完整的 Android Studio 工程，把 llama.cpp 编译为 .so + JNI 绑定。
- **iOS**：通过 Swift bindings（`ShenghaiWang/SwiftLlama`、`srgtuszy/llama-cpp-swift`），Xcode 集成。
- **React Native**：`mybigday/llama.rn`
- **WebGPU / WASM**：浏览器内运行（demo：<https://reeselevine.github.io/llamas-on-the-web/>），用 wllama、llama-cpp-wasm 绑定。

### 10.6 Kubernetes

常用 Operator / Chart：

- **llmaz**（InftyAI）：CRD 定义 `LLMInferenceService`，支持 HPA、GPU 调度。
- **LLMKube**（defilantech）：多 GPU + Apple Silicon Metal 支持。
- **GPUStack**（gpustack）：通用 GPU 集群管理。
- **Paddler**（intentee）：开源 LLMOps 平台，专门面向 llama-server。

### 10.7 嵌入式

- **Qualcomm Hexagon DSP**（进行中）
- **VirtGPU**（车规）
- **OpenCL Adreno**（手机 GPU）
- **WebGPU**（浏览器/嵌入式）

---

## 11. 性能数据

> 数据来源：llama.cpp 官方 bench、PR 评论、社区 benchmark（如 kokoro-ai benchmarks、George Hotz 评测）、X (Twitter) 实测。**注意**：所有数字都是参考，硬件/驱动/模型差异巨大。

### 11.1 吞吐：tokens / second

| 硬件 | 模型（量化） | 上下文 | 预填 (prompt eval) | 生成 (text eval) |
|---|---|---|---|---|
| M4 Max (128 GB) | Llama-3.3-70B Q4_K_M | 4096 | ~1200 t/s | ~25 t/s |
| M3 Ultra (192 GB) | Llama-3.3-70B Q4_K_M | 4096 | ~1500 t/s | ~35 t/s |
| M2 Pro (32 GB) | Llama-3.1-8B Q4_K_M | 4096 | ~3500 t/s | ~75 t/s |
| RTX 4090 (24 GB) | Llama-3.1-8B Q4_K_M | 4096 | ~12000 t/s | ~140 t/s |
| RTX 4090 (24 GB) | Llama-3.3-70B Q4_K_M | 4096 | ~4500 t/s (offload) | ~15 t/s (offload) |
| 2× RTX 4090 | Llama-3.3-70B Q4_K_M | 4096 | ~5500 t/s | ~28 t/s |
| RTX 3090 (24 GB) | Llama-3.1-8B Q4_K_M | 4096 | ~8000 t/s | ~95 t/s |
| A100 80GB | Llama-3.1-70B Q4_K_M | 4096 | ~9000 t/s | ~60 t/s |
| H100 80GB | Llama-3.1-70B Q4_K_M | 4096 | ~14000 t/s | ~110 t/s |
| H100 80GB | Llama-3.1-405B Q4_K_M | 4096 | ~4500 t/s | ~25 t/s |
| MI300X 192GB | Llama-3.1-405B Q4_K_M | 4096 | ~7000 t/s | ~45 t/s |
| Intel Xeon 8480C (56c) | Llama-3.1-8B Q4_K_M | 4096 | ~1200 t/s | ~30 t/s |
| Snapdragon 8 Gen 3 (手机) | Llama-3.2-3B Q4_K_M | 2048 | ~80 t/s | ~5 t/s |

> **关键观察**：
> - Apple Silicon 内存带宽极高（800 GB/s on M3 Ultra），长上下文大模型吞吐极有竞争力。
> - NVIDIA H100 比 A100 提升约 50%（算子优化 + FP8）。
> - MI300X 192GB 显存能装下 405B，是单卡跑超大规模模型的甜点。
> - Speculative decoding + draft model 通常提 1.8-2.5x。

### 11.2 首 token 延迟（TTFT）

| 场景 | TTFT |
|---|---|
| M2 Pro, 8B Q4_K_M, 1k prompt | ~80 ms |
| RTX 4090, 8B Q4_K_M, 1k prompt | ~40 ms |
| H100, 70B Q4_K_M, 1k prompt | ~80 ms |
| H100, 70B Q4_K_M, 32k prompt | ~1.5 s |
| M3 Ultra, 70B Q4_K_M, 1k prompt | ~150 ms |

> 对比 vLLM / TGI：llama-server 在 **小 batch + 低并发** 时延非常有竞争力（无调度 overhead），但 **大 batch 高并发** 时落后于 vLLM（无 PagedAttention，内存碎片高）。

### 11.3 内存占用

模型本身：

| 模型 | F16 | Q8_0 | Q4_K_M | IQ4_XS | Q2_K |
|---|---|---|---|---|---|
| Llama-3.1-8B | 16 GB | 8.5 GB | 5.7 GB | 5.0 GB | 4.0 GB |
| Llama-3.1-70B | 140 GB | 75 GB | 48 GB | 42 GB | 33 GB |
| Llama-3.1-405B | 810 GB | 432 GB | 231 GB | 200 GB | 162 GB |
| Gemma-2-27B | 54 GB | 29 GB | 18.5 GB | 16.5 GB | 13 GB |
| Qwen2.5-72B | 145 GB | 77 GB | 50 GB | 44 GB | 35 GB |
| DeepSeek-V3 671B (MoE) | 1.3 TB | 700 GB | 370 GB | 330 GB | 260 GB |

KV cache（每 token）：

| 模型 | ctx=4096 | ctx=32768 | ctx=131072 |
|---|---|---|---|
| 8B (F16 KV) | 0.5 GB | 4 GB | 16 GB |
| 70B (F16 KV) | 4 GB | 32 GB | 128 GB |
| 70B (Q8_0 KV) | 2 GB | 16 GB | 64 GB |

> 实战经验：选 70B 模型时，确保 **显存 ≥ 模型大小 + KV cache × 并发 slot**。Q4_K_M 70B + ctx 8k + 2 并发 ≈ 56 GB VRAM。

### 11.4 启动时间

| 操作 | 耗时 |
|---|---|
| `mmap` 5GB GGUF（SSD） | < 0.1 s |
| `mmap` 200GB GGUF（NVMe） | ~0.5 s |
| 解析元数据 + 分配 KV | 1-3 s |
| CPU 端 70B Q4_K_M 首 token | 5-10 s |
| GPU 端 70B Q4_K_M 首 token | 1-2 s |

> 比 vLLM / TGI 启动快一个数量级（无需 Python 运行时、torch 初始化）。

---

## 12. 成本模型与硬件适配

### 12.1 硬件成本对比

**消费级 GPU**（2026 年中）：

| 硬件 | 显存 | 价格 | 适合模型 |
|---|---|---|---|
| RTX 4060 Ti 16GB | 16 GB | ~$500 | 8B-13B Q4 |
| RTX 4070 Ti SUPER 16GB | 16 GB | ~$800 | 13B Q4 |
| RTX 4080 SUPER 16GB | 16 GB | ~$1000 | 13B Q4 |
| RTX 4090 24GB | 24 GB | ~$1800 | 13B-33B Q4 |
| RTX 5090 32GB | 32 GB | ~$2000 | 33B-70B Q4 (offload) |
| 2× RTX 3090 48GB | 48 GB | ~$1500 (二手) | 33B-70B Q4 |
| Apple M2 Max 64GB | 64 GB 共享 | ~$3000 | 70B Q4 全 CPU/GPU 混合 |
| Apple M3 Ultra 192GB | 192 GB 共享 | ~$5000 | 405B Q4 |
| AMD MI300X 192GB | 192 GB HBM3 | ~$10000 (新) | 405B Q4 |

**云 GPU**（按需价，截至 2026 Q2）：

| 提供商 | GPU | $/h | 适合场景 |
|---|---|---|---|
| AWS | g5.2xlarge (A10 24GB) | $1.21 | 8B-13B |
| AWS | g5.12xlarge (4×A10 96GB) | $5.42 | 33B |
| AWS | p4d.24xlarge (8×A100 320GB) | $32.77 | 70B-405B |
| AWS | p5.48xlarge (8×H100 640GB) | $98.32 | 405B+ |
| Lambda | 1×H100 80GB | $2.49 | 70B |
| Lambda | 8×H100 640GB | $14.32 | 405B+ |
| RunPod | 1×A100 80GB | $1.99 | 70B |
| RunPod | 1×H100 80GB | $4.49 | 70B-405B |
| Vast.ai | 1×RTX 4090 | $0.40-0.80 | 13B-33B |
| Vast.ai | 1×H100 80GB | $2-3 | 70B |

### 12.2 自托管成本模型

```
月成本 = 硬件折旧 + 电力 + 机房/云 + 维护人力
       = (硬件价 / 36 月) + (瓦数 × 24 × 30 × 电价) + 云费 + 人力

例：1× H100 80GB 自托管（3 年折旧）
  硬件 = $25,000 / 36 = $694/月
  电力 = 700W × 24h × 30 × $0.10/kWh = $50/月
  机房 = $100/月
  人力 = 4h/月 × $100/h = $400/月
  合计 = ~$1,250/月

吞吐量：~110 t/s 70B Q4_K_M
       = ~28,500 万 token/月（24×7）

单位成本 = $1,250 / 28,500 万 = $0.44 / 百万 token
```

对比：
- **OpenAI gpt-4o-mini 输入**：$0.15 / 百万 token（便宜）
- **OpenAI gpt-4o-mini 输出**：$0.60 / 百万 token（贵）
- **OpenAI gpt-4o 输出**：$15 / 百万 token（极贵）

> **自托管盈亏平衡点**：单台 H100 跑 70B，月 token 用量 < 1.2 亿时比 OpenAI 便宜；超过则用 OpenAI 反而便宜（**前提是数据不出云**）。

### 12.3 适合 llama.cpp 的场景

✅ **GPU 资源紧张**：1-2 张消费卡 / Apple Silicon / CPU 跑量化模型。
✅ **边缘 / 离线**：嵌入式、车载、手机、本地笔记本。
✅ **数据合规**：本地 / 私有云 / 离线。
✅ **低延迟**：无网络往返，单 token 延迟可低至 5-10 ms。
✅ **多平台**：同一份代码编译到 Mac / Linux / Windows / Android。
✅ **快速实验**：模型权重即文件，5 秒启动。

❌ **不推荐**：
- 极致高吞吐：vLLM / TGI 更优。
- 大量并发（>32 slot）：内存碎片 + 调度 overhead。
- 复杂 multi-model 路由：LiteLLM / Portkey 胜出。

---

## 13. 生态与下游产品

### 13.1 直接基于 llama.cpp 的产品

| 产品 | 形态 | 特点 |
|---|---|---|
| **Ollama** | CLI / server | macOS 一键安装，模型标签化（`ollama run llama3`），Modelfile 模板 |
| **LM Studio** | 桌面 GUI | 商业产品（proprietary），跨平台，模型浏览器，OAI 兼容 |
| **Jan** | 桌面 GUI | 开源 AGPL，强调隐私，自带 WebUI |
| **GPT4All** | 桌面 GUI | Nomic AI 出品，开源 MIT，多后端 |
| **llamafile** | 单文件可执行 | Mozilla 出品，COSMIC 调度，把 llama.cpp 链接进独立 ELF/PE  |
| **koboldcpp** | 桌面 + WebUI | 老牌，开源 AGPL，强调创意写作 |
| **LocalAI** | 多模型 server | 兼容 OAI/Anthropic/Embeddings，**网关定位** |
| **ramalama** | 容器化 | RedHat 出品，Podman/Docker 包装 |
| **Paddler** | LLMOps | 负载均衡 + autoscaling，专为 llama-server |
| **llama-swap** | 透明代理 | 共享端口按需切换模型 |

### 13.2 语言绑定

- **Python**：`abetlen/llama-cpp-python`（最流行）、`ddh0/easy-llama`
- **Node.js**：`withcatai/node-llama-cpp`（最完整）
- **Go**：`hybridgroup/yzma`（无需 CGo）、`go-skynet/go-llama.cpp`
- **Rust**：`edgenai/llama_cpp-rs`、`ShelbyJenkins/llm_client`
- **C#/.NET**：`SciSharp/LLamaSharp`（活跃）
- **Java/Kotlin**：`kherud/java-llama.cpp`、`QuasarByte/llama-cpp-jna`
- **Swift**：`ShenghaiWang/SwiftLlama`
- **Ruby**：`yoshoku/llama_cpp.rb`
- **PHP**：`distantmagic/resonance`
- **Flutter/Dart**：`netdur/llama_cpp_dart`、`xuegao-tzx/Fllama`
- **React Native**：`mybigday/llama.rn`
- **Scala 3**：`donderom/llm4s`
- **Clojure**：`phronmophobic/llama.clj`
- **Delphi**：`Embarcadero/llama-cpp-delphi`
- **Zig**：`deins/llama.cpp.zig`
- **Guile Scheme**：`guile_llama_cpp`

### 13.3 工具链

- **akx/ggify**：HF → GGUF
- **unslothai/unsloth**：训练后导出 GGUF
- **gpustack/gguf-parser-go**：Go GGUF 解析器
- **crashr/gppm**：低功耗 P40/P100 调度
- **Styled Lines**（Unity 插件）：游戏内 LLM

### 13.4 上层协议代理

LiteLLM、Portkey、Kong AI Gateway、APISIX ai-proxy、Envoy AI Gateway 等都把 llama-server 当作一个 **upstream provider**，提供：

- 多模型路由、负载均衡
- Fallback、retry、timeout
- 缓存（semantic + exact）
- 限流、quota
- 观测性（tracing、metrics）
- 多租户、API key 管理
- Webhook、审计日志

详见各自产品报告。

---

## 14. 客户 / 社区案例

> 社区项目为主，公开声明的 enterprise 客户有限。但 llama.cpp 处于非常多产品链的底层，难以追溯。

### 14.1 公开声明

- **Mozilla**：llamafile 项目把 llama.cpp 做成 Cosmopolitan Libc 单文件。
- **NVIDIA**：与 llama.cpp 团队合作 gpt-oss MXFP4（PR #15091），博客 <https://blogs.nvidia.com/blog/rtx-ai-garage-openai-oss>
- **Hugging Face**：HF Inference Endpoints 原生支持 GGUF（issue #9669）；ggml-org 在 HF 官方账号发布量化版本。
- **Apple**：Apple Silicon 是 first-class citizen；mlx 项目与 llama.cpp 在优化层面有交流。
- **OpenInterpreter**：本地 agent 依赖 llama.cpp 跑开源模型。
- **GPT4All** (Nomic AI)：底层直接调用 llama.cpp。
- **jan.ai**：桌面 AI 客户端，默认 llama.cpp。
- **小红书 / 字节 / 阿里 / 腾讯**（推测）：内部使用 llama.cpp 做本地推理原型（无公开声明）。

### 14.2 学术 / 研究

- "SqueezeLLM"、"SmoothQuant" 等量化论文实现参考。
- 多家高校（Stanford、MIT、CMU）用 llama.cpp 做端侧 LLM demo。
- RWKV、Mamba、BitNet 等新架构都优先在 llama.cpp 跑通以验证可用性。

### 14.3 GitHub 统计（截至 2026-06）

- Stars：~78k
- Forks：~11k
- Open Issues：~1,800
- Open PRs：~250
- Releases：~1,000+（每天 1-2 个小版本）
- Contributors：~1,200
- 引用：学术论文 > 3,000 引用

---

## 15. 优势与劣势分析

### 15.1 优势

| 维度 | 评价 |
|---|---|
| **硬件覆盖** | ★★★★★ 业界最广，CPU/GPU/NPU/手机/嵌入式 |
| **部署难度** | ★★★★★ 单文件 binary，5 分钟跑通 |
| **启动速度** | ★★★★★ 1-3 秒，mmap 免加载 |
| **内存效率** | ★★★★☆ K-quants / i-quants / KV 量化成熟 |
| **OpenAI 兼容** | ★★★★☆ chat / completion / embeddings / audio / tools / structured output |
| **多模态** | ★★★★☆ 视觉/音频/OCR 完整支持 |
| **社区活跃** | ★★★★★ 12k+ PR，日更 |
| **授权** | ★★★★★ MIT，最宽松 |
| **Apple Silicon** | ★★★★★ 一等公民 |
| **离线/隐私** | ★★★★★ 完全本地，无任何网络依赖 |
| **消费级硬件** | ★★★★★ 8GB 显存能跑 13B |
| **跨平台** | ★★★★★ Mac/Linux/Windows/RISC-V/Android/iOS/WASM |

### 15.2 劣势

| 维度 | 评价 | 说明 |
|---|---|---|
| **高并发吞吐** | ★★☆☆☆ | 多 slot 串行批，无 PagedAttention；>32 slot 时落后 vLLM 显著 |
| **PagedAttention** | ❌ | KV cache 按 slot 预分配，长上下文时碎片严重 |
| **Speculative decoding 集成** | ★★★☆☆ | 支持 draft model，但非自动，配置繁琐 |
| **多模型路由** | ★★☆☆☆ | 单进程单模型，需 llama-swap 之类外挂 |
| **自动 scaling** | ★★☆☆☆ | 需 K8s operator / Paddler / 自研 |
| **语义缓存** | ❌ | 完全不提供 |
| **Guardrails** | ★★☆☆☆ | 仅 sampling-time grammar，需外接 NeMo Guardrails / Guardrails AI |
| **Tracing** | ★★☆☆☆ | 仅 Prometheus metrics，无 OpenTelemetry |
| **企业级 RBAC** | ❌ | 单 API key 模式 |
| **正式 SLA 支持** | ❌ | 社区项目 |
| **Long context (>200k)** | ★★★☆☆ | 支持但 KV 内存爆炸，需配合 cache 量化 + sliding window |
| **训练** | ❌ | 仅推理 |
| **Speculative decoding 自动选 draft** | ❌ | 用户手挑 |
| **Multi-LoRA hot-swap** | ★★☆☆☆ | 支持，但需重启 / load 切换 |

### 15.3 关键风险

1. **API 稳定性**：libllama 是 v0.x 语义，每个 minor 版本都可能 break。Issue #9289 是 libllama changelog，#9291 是 server REST API changelog。
2. **GGUF 版本兼容**：GGUF v2 → v3 升级时部分字段重命名，老 reader 读不了新文件。
3. **多模态还在快速迭代**：libmtmd 接口变化频繁，生产环境建议锁定 minor 版本。
4. **量化质量因模型而异**：Q4_K_M 是经验值，新模型可能需要 IQ4_XS 或 Q5_K_M 才能保住质量。

---

## 16. 与其他推理引擎 / 网关对比

> 这是一个简明对比表；细节请参考本目录下其他产品报告。

### 16.1 vs vLLM

| 维度 | llama.cpp | vLLM |
|---|---|---|
| 主要语言 | C/C++ | Python + CUDA |
| 高并发吞吐 | 中（多 slot 串行） | 极高（PagedAttention + continuous batching） |
| 内存效率 | 中（KV 预分配） | 高（PagedAttention） |
| 多模态 | 内置（libmtmd） | 通过插件（vllm-omni） |
| OpenAI 兼容 | 是 | 是 |
| 启动速度 | 秒级 | 10-30 秒（torch 初始化） |
| 消费级硬件 | ★★★★★ | ★★☆☆☆（需 NVIDIA GPU + Python） |
| Apple Silicon | ★★★★★ | ★★★☆☆（MLX 后端） |
| 长上下文 | 中（KV 量化） | 高（PagedAttention 优势） |
| 适用场景 | 边缘 / 本地 / 单机 / 中等并发 | 数据中心 / 高并发 / 大量 GPU |

**结论**：vLLM 是"数据中心专用 LLM 服务器"，llama.cpp 是"全场景通用 LLM 运行时"。**两者互补**，不是竞争。

### 16.2 vs TGI (Text Generation Inference)

| 维度 | llama.cpp | TGI |
|---|---|---|
| 主要语言 | C/C++ | Rust + Python |
| 部署 | 单文件 binary | Docker 镜像 |
| 硬件 | 全平台 | 主要 NVIDIA + AMD |
| 多模态 | 内置 | 部分（llava 等） |
| 高并发 | 中 | 高 |
| Rust 生态友好 | 间接 | 极友好 |
| 上游兼容性 | GGUF | HF transformers |

**结论**：TGI 适合已用 HF 生态的企业；llama.cpp 适合想"零依赖"的场景。

### 16.3 vs LMDeploy

| 维度 | llama.cpp | LMDeploy |
|---|---|---|
| 开发商 | 社区 (ggml-org) | 商汤 (OpenMMLab) |
| 主要后端 | CPU/Metal/CUDA/HIP/Vulkan/SYCL | NVIDIA CUDA 为主 |
| 多模态 | 是 | 是 (InternVL/VL) |
| 量化 | 完整 K-quants / i-quants / MXFP4 | AWQ / GPTQ / SmoothQuant |
| 高并发 | 中 | 高 |
| 文档 | 社区驱动 | 中文企业级 |

**结论**：LMDeploy 在 NVIDIA GPU 上中文场景、企业级部署更成熟。

### 16.4 vs Triton Inference Server (NVIDIA)

| 维度 | llama.cpp | Triton |
|---|---|---|
| 模型支持 | GGUF LLM 为主 | 任意（TensorRT/ONNX/PyTorch） |
| 后端 | C/C++ 后端 | 多 backend (Python/C++/Triton) |
| 多模型编排 | 弱 | 极强（model ensemble、BLS、dynamic batching） |
| 企业级 | 弱 | 极强（SLA、监控、k8s） |
| 部署 | 单文件 binary | 复杂（需要 triton-server + 后端） |

**结论**：Triton 是"模型服务器标准"，llama.cpp 是"轻量 LLM 运行时"。Triton 适合多模型多框架的 ML 平台；llama.cpp 适合单纯跑 LLM。

### 16.5 vs SGLang

| 维度 | llama.cpp | SGLang |
|---|---|---|
| 核心场景 | 单模型推理 | LLM 程序（结构化生成、agent） |
| DSL | GBNF grammar | Python sglang 函数 |
| 性能 | 中 | 极高（RadixAttention 缓存 prefix） |
| 复杂度 | 低 | 中-高 |

**结论**：SGLang 适合复杂 multi-turn / function calling 重度场景；llama.cpp 适合"一个请求一个回答"。

### 16.6 vs LiteLLM / Portkey / Kong / APISIX / Envoy

这些是**网关 / 代理**，不是推理引擎。它们把 llama-server 当作一个 upstream。llama.cpp 不与它们竞争，而是 **共存**：

```
Client
  │
  ▼
[LiteLLM / Portkey / Kong / APISIX / Envoy AI Gateway]
  │ (路由 / 缓存 / 限流 / 鉴权 / 观测)
  ▼
[llama-server] 多个实例
  │
  ▼
[llama.cpp runtime]
```

**何时叠加网关**：
- 多模型路由（不同模型走不同 server）
- 跨云混合（本地 + 公有云）
- 团队配额、成本核算
- Semantic cache、guardrails
- OpenTelemetry tracing

**何时单跑 llama-server**：
- 个人 / 内部工具
- 单模型、单团队、低并发
- 不想引入额外组件

---

## 17. 风险、坑、最佳实践

### 17.1 常见坑

1. **OOV 量化方案**：`IQ1_S` 等极端量化在 IQ 矩阵之外会大幅降低质量。生产用 `Q4_K_M` 或 `IQ4_XS` 起。
2. **KV cache 内存爆炸**：`ctx_size 131072` + `parallel 4` + 70B F16 KV ≈ 128 GB。必须用 `--cache-type-k/v q8_0`。
3. **CPU 线程数误配**：`--threads 64` 在 8 核机器上反而更慢（threadpool overhead）。建议 `--threads $(nproc)`。
4. **Speculative decoding 选错 draft**：draft model 太大提速不明显，太小接受率低。经验：draft 模型 ≈ main 模型的 1/10 - 1/30 参数。
5. **多模态 mmproj 缺失**：忘了加 `--mmproj` 文件导致视觉/音频功能不工作。
6. **WebUI 暴露公网**：内置 WebUI 是为开发用，含管理功能。生产只暴露 `/v1/*`，加 `--api-key` + 反向代理。
7. **prompt 模板不匹配**：用 `chatml` 模板喂到 Llama-3 模板的模型会输出乱码。用 `--chat-template-file` 或确认 `--jinja`。
8. **GGUF v2 文件与新 server 不兼容**：升级 server 后老量化文件能读但新功能（KV 量化、新 quant）失效。
9. **madvise 在 Windows**：Windows 上没有 MADV_WILLNEED，mmap 优化失效。
10. **PR 进度慢 / issue 长期 open**：社区驱动，维护者有限。生产前 fork 锁版本。

### 17.2 最佳实践

1. **量化选择**：
   - 一般：`Q4_K_M`
   - 高质量：`Q5_K_M` 或 `Q6_K`
   - 极省内存：`IQ4_XS`（需要 imatrix）
   - 极致（实验）：`IQ2_M`（需要 imatrix + 校准）

2. **硬件配置**：
   - 8 GB 显存：13B Q4_K_M
   - 16 GB 显存：13B Q6_K / 33B Q4_K_M（offload）
   - 24 GB 显存：33B Q4_K_M / 70B Q4_K_M（offload）
   - 48 GB 显存：70B Q4_K_M
   - 80 GB 显存：70B Q6_K / 405B Q4_K_M（offload）
   - 192 GB 显存：405B Q4_K_M 全 GPU

3. **Server 启动推荐配置**：

```bash
llama-server \
  -m model.Q4_K_M.gguf \
  --alias <name> \
  --ctx-size 8192 \
  --n-gpu-layers 99 \
  --batch-size 512 \
  --ubatch-size 128 \
  --parallel 4 \
  --cont-batching \
  --flash-attn \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --mlock \
  --threads $(nproc) \
  --host 0.0.0.0 \
  --port 8080 \
  --api-key "${SECRET}" \
  --jinja  # 启用 Jinja chat template
```

4. **监控**：
   - 拉 `/metrics` 到 Prometheus
   - 关键 SLO：TTFT P99、生成吞吐 (t/s)、slot 利用率、KV 缓存命中率

5. **灰度发布新模型**：
   - 用 llama-swap 同时跑两套 llama-server，按 model 名分流
   - 灰度用 vLLM/Portkey 切流量

6. **备份**：
   - 锁版本（git tag / docker image tag）
   - 保存 `--mlock` 失败时的 OOM 转储
   - 监控 GGUF 文件 SHA-256（防止 bit rot）

### 17.3 安全

- API key 必须设置（`--api-key`），不能依赖"反正监听 127.0.0.1"。
- 反向代理（如 caddy / nginx）做 TLS，不要直接暴露 8080。
- 关闭 `--webui` 在公网环境。
- 输出过滤：自己接一层 LLM guard 或关键词过滤。
- 输入 token 限长：即使 ctx_size 8192，也建议加 `max_tokens` 限制 prompt 大小。
- `api_key` 鉴权 + IP 白名单（反向代理侧）。
- 监控 `--api-key` 失败次数，做暴力破解告警。

---

## 18. 参考资料与文档索引

### 18.1 官方

- 主仓库：<https://github.com/ggml-org/llama.cpp>
- Changelog (libllama API)：<https://github.com/ggml-org/llama.cpp/issues/9289>
- Changelog (llama-server REST API)：<https://github.com/ggml-org/llama.cpp/issues/9291>
- 编译指南：<https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md>
- 安装指南：<https://github.com/ggml-org/llama.cpp/blob/master/docs/install.md>
- Docker 文档：<https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md>
- 多模态文档：<https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md>
- Server README：<https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>
- Backend 文档目录：<https://github.com/ggml-org/llama.cpp/tree/master/docs/backend>
- 性能测试工具：<https://github.com/ggml-org/llama.cpp/tree/master/tools/bench>
- Manifest / 设计哲学：<https://github.com/ggml-org/llama.cpp/discussions/205>
- GitHub Models：<https://huggingface.co/models?library=gguf&sort=trending>

### 18.2 ggml 库

- ggml 仓库：<https://github.com/ggml-org/ggml>
- ops 参考：<https://github.com/ggml-org/llama.cpp/blob/master/docs/ops.md>
- 算子实现：<https://github.com/ggml-org/llama.cpp/tree/master/ggml/src>

### 18.3 关键 PR / 讨论

- #15091：MXFP4 gpt-oss 支持
- #12898：多模态 llama-server
- #9291：server REST API changelog
- #9289：libllama API changelog
- #9669：HF Inference Endpoints 支持 GGUF
- Discussions #16938：WebUI 指南
- Discussions #15396：gpt-oss 指南
- Discussions #205：项目 manifesto

### 18.4 下游重要项目

- Ollama：<https://github.com/ollama/ollama>
- LM Studio：<https://lmstudio.ai/>
- Jan：<https://github.com/janhq/jan>
- GPT4All：<https://github.com/nomic-ai/gpt4all>
- llamafile：<https://github.com/Mozilla-Ocho/llamafile>
- koboldcpp：<https://github.com/LostRuins/koboldcpp>
- LocalAI：<https://github.com/mudler/LocalAI>
- llama-swap：<https://github.com/mostlygeek/llama-swap>
- Paddler：<https://github.com/intentee/paddler>
- llama-cpp-python：<https://github.com/abetlen/llama-cpp-python>
- node-llama-cpp：<https://github.com/withcatai/node-llama-cpp>
- unsloth：<https://github.com/unslothai/unsloth>

### 18.5 学术 / 媒体

- NVIDIA × llama.cpp blog：<https://blogs.nvidia.com/blog/rtx-ai-garage-openai-oss>
- "Run LLMs on Mac" 系列教程（kokoro-ai, George Hotz 等）
- Quantization papers：SqueezeLLM, AWQ, GPTQ, SmoothQuant
- "Local LLM" 运动先驱：a16z, Matt Bornstein 等

---

## 19. 结语

llama.cpp 是 **"让 LLM 跑在所有地方"** 这条主线的核心软件。从 2023 年 3 月的一个周末 hack，到 2026 年一个 78k+ stars、1200+ contributors、覆盖 17+ 硬件后端的项目，它的成功源于几个不可替代的特质：

1. **极简主义**：单文件 binary、零依赖、MIT、谁都能编译。
2. **极致性能**：在每类硬件上都接近 native 性能上限。
3. **协议中立**：OpenAI 兼容 + 多模态 + 工具调用 + 结构化输出，**不**强迫你买它的全套。
4. **生态共建**：把上层产品（Ollama、LM Studio、Jan、Paddler）当作合作伙伴而非竞争。

它不适合的场景（高并发、企业级 SLA、复杂多模型路由）正是 LiteLLM / Portkey / Kong AI Gateway / APISIX / Envoy AI Gateway 的舞台。**生产级 AI Gateway 架构**通常是：

```
Client → [AI Gateway (路由/缓存/限流/观测)] → [llama.cpp] / [vLLM] / [TGI] / [SGLang] / [Triton]
```

理解 llama.cpp 的能力边界，是搭建可靠 AI 推理基础设施的必修课。

---

> **调研者**：Rich（AI 助手）
> **审稿**：self-review 2026-06-05
> **文件路径**：`aigw/openclaw/product-llama-cpp-20260605.md`
> **版本**：v1.0
