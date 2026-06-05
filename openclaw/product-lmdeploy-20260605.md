# LMDeploy 深度调研 — 上海 AI Lab 出品的高吞吐 LLM 推理与服务工具链

> 调研日期：2026-06-05
> 调研对象：[InternLM/lmdeploy](https://github.com/InternLM/lmdeploy)（Apache-2.0）
> 文档站：<https://lmdeploy.readthedocs.io/en/latest/>
> 关联产品：InternLM / InternVL / LLaMA / Qwen / DeepSeek / GLM / gpt-oss / SGLang / vLLM / TGI
> 上一份：`product-triton-inference-server-20260605.md`；本份为候选清单第 12 站：**LMDeploy**

---

## 0. TL;DR（一句话版 + 关键数字）

LMDeploy 是由上海 AI Lab（Shanghai AI Lab）OpenGVLab / MMRazor & MMDeploy 团队开发的 **LLM 压缩、部署、服务一体化工具链**，核心由两条独立推理引擎（**TurboMind** C++/CUDA 内核 + **PyTorchEngine** 纯 Python）以及一套 **api_server / proxy_server OpenAI 兼容服务** 组成。LMDeploy 与 SGLang / vLLM 同属"高吞吐推理服务引擎"赛道，但 LMDeploy 的差异化在于：

1. **对国产芯片友好**：除了 NVIDIA，**PyTorchEngine 已支持华为昇腾 Ascend**（graph mode 推理速度翻倍）。
2. **重量级量化栈**：AWQ/GPTQ INT4（2.4× FP16） + **在线 INT4/INT8 KV Cache 量化** + **TurboQuant（K4V2，平均 3 bit，几乎无损）**。
3. **DeepSeek 优化最深**：内置 FlashMLA / DeepGemm / DeepEP / MicroBatch / eplb + DLSlime & Mooncake 集成的 **PD 分离**。
4. **双协议服务面**：默认 OpenAI Chat/Completions/Models 端点 + 新增 **Anthropic Messages/CountTokens 兼容**。
5. **多模型多机多卡 Proxy Server**：内置 `--routing-strategy min_expected_latency` 与 `Hybrid` / `DistServe` 两种 serving strategy。

> 关键性能（官方 README 多次重申）：
> - 1.8× vLLM 吞吐量（InternLM2-20B GQA 场景）
> - 4-bit 推理 2.4× FP16（RTX 4090，Llama-2-7B 单 batch：206.4 tok/s）
> - KV INT4 → RPS 提升 39%（Llama-2-7B：14.98 → 20.81）
> - TurboQuant K4V2（H200 / Qwen3-30B-A3B / ShareGPT，concurrent=64）：input 2368.8 → 2195.8 tok/s（-7.3%），TTFT +8.4%，ITL 不变
> - Llama-3-8B + PyTorchEngine + CUDA Graph：1.3× 速度
> - gpt-oss MXFP4 on V100+：H800 上 1.5× vLLM

---

## 1. 项目背景

### 1.1 来源与团队
- **作者组织**：Shanghai AI Lab (上海人工智能实验室) OpenGVLab 下的 **MMRazor**（剪枝/量化）和 **MMDeploy**（部署）团队，2023 年中立项。
- **首批作者 / 维护者**：袁进辉（时任 OneFlow 创始人，后续到 OpenGVLab）、赵傲东、李力（论文第一作者）等；arXiv 2508.15601 论文署名 Zhang Li, Jiang Youhe, He Guoliang, Chen Xin, Lv Han, Yao Qian, Fu Fangcheng, Chen Kai。
- **首发时间**：2023-07 起在 GitHub Public；2023-08 上线 4-bit AWQ；2023-11 TurboMind 大重构（Paged Attention、Flash Decoding、Split-K）；2024-01 上线多机多卡 proxy + PyTorchEngine 双引擎路线图。
- **License**：Apache-2.0（与 vLLM / SGLang 同；商用 OK）。

### 1.2 战略定位
LMDeploy 处于 **"训练侧（XTuner）→ 压缩（MMRazor/LMDeploy-lite）→ 部署（LMDeploy）→ 应用（OpenAOE/Lagent）"** 的中间一环，是上海 AI Lab "InternLM 系全家桶" 的 **服务层核心**：

```
 XTuner (微调)        InternLM (基模)         LMDeploy (部署)        OpenAOE / Lagent
  │                     │                        │                       │
  │ SFT/RLHF            │ InternLM2/3 / InternVL │ TurboMind / PyTorch  │ Agent 框架
  │                     │                        │ api_server           │
  └────── 训练 ─────────┴──── 模型产出 ──────────┴──── 服务化 ───────────┴── 应用
```

### 1.3 与同赛道产品的关系
- **SGLang / vLLM / TGI / Triton**：纯推理服务框架；LMDeploy 把"压缩 + 推理 + 服务"打通，量化栈是其独有壁垒。
- **Higress / APISIX / Kong / Envoy AI Gateway**：流量侧 LLM Gateway；LMDeploy 是被它们"代理"的下游推理引擎（典型用法：Kong AI Gateway → LMDeploy TurboMind 实例）。
- **LiteLLM / Portkey / One-API**：API 聚合 / 路由；LMDeploy 不做多供应商聚合，专注"单点高吞吐 + 低成本"。
- **Llama.cpp**：CPU/边缘场景；LMDeploy 主战场是数据中心 GPU，但也支持 Ascend 走出 NVIDIA 舒适区。

### 1.4 关键里程碑（README News 节选）

| 时间 | 事件 |
|------|------|
| 2023-07 | TurboMind 支持 InternLM TP 推理 |
| 2023-08 | 4-bit AWQ 推理 + HuggingFace Hub 4-bit 模型库 |
| 2023-11 | TurboMind Paged Attention / Flash Decoding / W4A16 (sm_75) |
| 2024-01 | **多机多卡 proxy server** + PyTorchEngine 立项 |
| 2024-04 | TurboMind GQA 提速，InternLM2-20B 16+ RPS（1.8× vLLM） |
| 2024-04 | 在线 INT4/INT8 KV 量化（无需校准） |
| 2024-07 | Llama 3.1 8B/70B + Tools Calling |
| 2024-09 | PyTorchEngine 适配华为昇腾（Ascend） |
| 2024-09 | PyTorchEngine + CUDA Graph，Llama3-8B 1.3× 提速 |
| 2025-01 | 支持 DeepSeek V3 / R1 |
| 2025-04 | 集成 DeepSeek 加速技术：FlashMLA / DeepGemm / DeepEP / MicroBatch / eplb |
| 2025-06 | **FP8 MoE 综合优化** + **DeepSeek PD 分离（DLSlime + Mooncake）** |
| 2025-09 | TurboMind MXFP4（V100+），gpt-oss 1.5× vLLM on H800 |
| 2026-02 | 支持 Qwen3.5 + llm-compressor 4bit 对称/非对称量化 |
| 2026-04 | PyPI 存储扩容，v0.12.3 wheel 恢复上传 |

---

## 2. 架构总览

### 2.1 顶层组件图（ASCII）

```
                ┌───────────────────────────────────────────────────────────────┐
                │                       User / Client                           │
                │  (OpenAI SDK / Anthropic SDK / curl / LMDeploy APIClient)     │
                └─────────────────────────────┬─────────────────────────────────┘
                                              │  HTTPS / SSE
                ┌─────────────────────────────▼─────────────────────────────────┐
                │  api_server  (FastAPI)        :23333                          │
                │   /v1/chat/completions  /v1/completions  /v1/models           │
                │   /v1/messages  /v1/messages/count_tokens  /anthropic/v1/... │
                │   /v1/embeddings  /health  /metrics (prom)                    │
                └──────┬───────────────────────────┬────────────────────────────┘
                       │                           │
        ┌──────────────▼─────────┐    ┌────────────▼─────────────┐
        │  proxy_server :8000     │    │  Tools Parser (可选)     │
        │  - nodes/status/add/    │    │  internlm / qwen / llama3│
        │    remove               │    │                          │
        │  - routing: random /    │    │  Structured Output       │
        │    min_expected_latency │    │  (json_schema / regex /  │
        │    min_observed_latency │    │   grammar)               │
        │  - serving: Hybrid /    │    └──────────────┬───────────┘
        │    DistServe (PD 分离)  │                   │
        └────┬──────┬──────┬──────┘                   │
             │      │      │                          │
        ┌────▼──┐┌──▼───┐┌─▼────┐                     │
        │ node1││node2 ││node3 │  ← 多机多卡 api_server (TP / PP)
        └──┬───┘└──┬───┘└──┬───┘                     │
           │       │       │                          │
   ┌───────▼───────▼───────▼──────┐                   │
   │  TurboMind (C++/CUDA)        │   TurboQuant     │
   │  - Persistent Batch          │   (K4 + V2)       │
   │  - Blocked KV Cache + LRU    │   PolarQuant+QJL  │
   │  - Cutlass FMHA              │                   │
   │  - INT8/INT4 KV (online)     │                   │
   │  - AWQ/GPTQ W4A16            │                   │
   │  - MXFP4 / FP8               │                   │
   │  - Speculative (eagle3 /     │                   │
   │    deepseek_mtp)             │                   │
   └───────┬──────────────────────┘                   │
           │                                          │
   ┌───────▼──────────────────────┐  ┌───────────────▼─────────────┐
   │  PyTorchEngine (Python)      │  │ 离线 pipeline / cli chat    │
   │  - Paged Attention           │  │  lmdeploy pipeline(...)     │
   │  - Continuous Batching       │  │  lmdeploy chat <model>      │
   │  - Tensor Parallelism        │  │  lmdeploy lite auto_awq     │
   │  - S-LoRA (多 adapter)       │  │  lmdeploy convert           │
   │  - W8A8 量化                 │  └─────────────────────────────┘
   │  - TurboQuant (quant_policy  │
   │    = 42)                     │
   │  - Ascend NPU graph mode     │
   └──────────────────────────────┘
```

### 2.2 模块清单

| 模块 | 路径 / 角色 |
|------|------------|
| `lmdeploy.serve.openai.api_server` | FastAPI 入口；OpenAI 兼容 + Anthropic 兼容端点 |
| `lmdeploy.serve.openai.proxy` | Request Distributor（多机多卡 LB） |
| `lmdeploy.serve.turbomind` | TurboMind 引擎驱动（libtm 加载 + engine_config） |
| `lmdeploy.serve.pytorch` | PyTorchEngine 驱动（Engine + EngineInstance） |
| `lmdeploy.pytorch.engine` | Engine / EngineInstance / ModelAgent / Scheduler / RequestManager |
| `lmdeploy.pytorch.model` | patched_model（注入 TP / 量化 / 高性能 kernel） |
| `lmdeploy.lite` | `auto_awq` / `calibrate` / `smoothquant` / `llm-compressor` 集成 |
| `lmdeploy.vl` | VLM 推理（InternVL / Qwen-VL / LLaVA / CogVLM / Molmo …） |
| `lmdeploy.messages` | `PytorchEngineConfig` / `TurbomindEngineConfig` / `GenerationConfig` / `SpeculativeConfig` / `ChatTemplateConfig` |
| `src/turbomind/` | C++/CUDA 源码：FMHA / SequenceManager / blocked KV / INT8 KV 等 |

---

## 3. 双引擎：TurboMind vs PyTorchEngine

LMDeploy 与 vLLM / SGLang / TGI 最大的架构差异是 **同时维护两套独立引擎**，用户按场景选：

| 维度 | TurboMind | PyTorchEngine |
|------|-----------|---------------|
| 起源 | NVIDIA FasterTransformer fork | 纯 Python 自研（2024-01 立项） |
| 实现语言 | C++/CUDA + Python wrapper | Python (PyTorch) |
| 核心调度 | **Persistent Batch**（一次 batch 寿命覆盖整个服务进程） | Continuous Batching（vLLM 风格，迭代级调度） |
| KV Cache | 自研 **Blocked KV + LRU + 序列淘汰**（参见 SequenceManager.h） | Paged Attention（block-level），支持 host-device swap |
| 注意力 | cutlass **FMHA**（支持 Q/K 长度不一致） | 标准 PyTorch SDPA + FlashAttention-2/3 |
| 量化 | AWQ/GPTQ **W4A16** + **INT4/INT8 KV** + **MXFP4/FP8** | **W8A8** + **TurboQuant K4V2** + llm-compressor |
| 张量并行 | 支持，**NCCL host-side 同步**（修过 hang） | 支持 |
| 推测解码 | ✅ (eagle3, deepseek_mtp) | ✅ (eagle3, deepseek_mtp) |
| 硬件 | NVIDIA V100 → Hopper | NVIDIA + **华为昇腾 Ascend** + DCU |
| 模型覆盖 | Llama / InternLM / Qwen / Baichuan / GLM / DeepSeek / Mixtral / gpt-oss … | 全部（VLM 友好） |
| 性能侧重 | **极致吞吐**（生产首选） | **开发者友好 / 新硬件 / 边实验** |
| Tool Call | ✅ (`--tool-call-parser`) | ✅ |
| Structured Output | ✅ | ✅ |
| 上手成本 | 中（要理解 engine_config） | 低（PyTorch 栈） |

### 3.1 TurboMind 三大核心子模块

#### 3.1.1 Persistent Batch（持续批）
- 启动时预分配 N 个 slot，新请求占空闲 slot，完成即释放
- **cache hit 跳过历史 token 解码**，多轮对话中历史 KV 直接复用
- batch 自动伸缩，避免空泡

#### 3.1.2 KV Cache Manager（blocked + LRU）
```cpp
// src/turbomind/models/llama/SequenceManager.h
class SequenceManager {
    // 把所有 KV 显存集中到一个 "memory pool"
    // 每个 slot 是一段预分配的连续显存块
    // 当 pool 满 → LRU 淘汰 → token id 形式压缩
    // 同一 seq 后续访问 (cache miss) → FMHA 重新 decode 还原
};
```

**优势**：对用户而言"显存无限"，多轮对话体验极好。

#### 3.1.3 LLaMa 实现（FT 改造）
- 用 **cutlass FMHA** 替换 FT 的 context decoder attention（支持 Q/K 长度不一致，多轮解码关键）
- 在 context FMHA 和 generation FMHA 中引入 **indirect buffer pointer**，支持 batch 内 KV 不连续
- 重新设计 **persistent batch + TP** 的多线程同步机制
- **INT8 KV cache** 提升 max batch size（KV 在推理中通常 > weights 显存占用 + 带宽）

### 3.2 PyTorchEngine 三大核心子模块

#### 3.2.1 Engine & EngineInstance
- **EngineInstance** = 推理请求 sender（thread-safe，跨线程并发）
- **Engine** = 调度 + 执行
  - `RequestManager`：收发请求
  - `Scheduler`：决定本步跑哪些 seq + adapter
  - `ModelAgent`：`patched_model`（注入 TP/quant/kernel）+ `cache_engine`（block 管理 + host-device swap）

#### 3.2.2 Continuous Batching + Paged Attention
- 抛弃 padding：所有 seq 拼成一条长序列
- 按 block 分配 KV（vLLM 路线）
- Scheduler 在每步决定 evict 哪些 block

#### 3.2.3 S-LoRA（多 adapter 推理）
- LoRA adapter 单独分页，按需 swap 到 GPU
- 配套自定义 kernel 支持 **未合并 adapter 推理**
- 用例：一份 base + N 个业务 LoRA，按用户/请求路由

### 3.3 双引擎协同
- `api_server` / `proxy_server` 不关心底层引擎，统一下单
- `--backend turbomind | pytorch` 切换
- Proxy 节点可同时挂不同后端的 worker

---

## 4. 协议支持（API Surface）

### 4.1 OpenAI 兼容（默认）

| 端点 | 状态 | 说明 |
|------|------|------|
| `POST /v1/chat/completions` | ✅ | stream / non-stream，function calling |
| `POST /v1/completions` | ✅ | 文本补全（兼容老客户端） |
| `GET  /v1/models` | ✅ | 列出已加载模型 |
| `POST /v1/embeddings` | ✅ | 向量（部分模型支持） |
| `GET  /v1/chat/parsers` | ✅ | 列举已注册 tool parser |
| `GET  /health`、`GET /metrics` | ✅ | Prometheus 指标（`--enable-metrics`） |
| `GET  /openapi.json` | ✅ | OpenAPI schema，配套 `openapi-generator-cli` 生 Java/Go/Rust SDK |

> 默认端口 23333；Swagger UI 在 `http://0.0.0.0:23333` 直接调试。

**Anthropic 兼容端点（v0.7+ 落地）**：
- `POST /v1/messages`
- `POST /v1/messages/count_tokens`
- `GET  /anthropic/v1/models`
- 必填头：`content-type: application/json`、`anthropic-version: 2023-06-01`
- 支持 `text` / `thinking`（reasoning）/ `tool_use` 块
- SSE 事件：`message_start` / `content_block_start` / `content_block_delta`（text_delta / thinking_delta / input_json_delta）/ `content_block_stop` / `message_delta` / `message_stop`
- 限制：tool_use 需配置 `--tool-call-parser`；`count_tokens` 基于 tokenizer+chat-template 估算

### 4.2 Tool / Function Calling
- 启动时 `--tool-call-parser {internlm|qwen|llama3}` 三选一
- 支持 InternLM2/2.5/3、Llama 3.1、Qwen 2.5
- 多轮 multi-tool 验证通过 Qwen 2.5 端到端

### 4.3 Structured Output（guided decoding）
- `response_format = { type: "json_schema", json_schema: { name, schema } }`
- 后端用 **xgrammar / outlines 风格** 的 schema-constrained decoding（PyTorch & TurboMind 都支持）
- 适用场景：tool call 校验、RAG JSON 输出、表单填写

### 4.4 内置 CLI 客户端
```bash
lmdeploy serve api_client http://host:23333   # 终端对话
lmdeploy chat ./internlm2_5-7b-chat-4bit      # 直连本地 4bit 模型对话
```

### 4.5 第三方 Agent 接入
- `OpenAOE`（上海 AI Lab）：多模型路由 + 队列
- `Lagent`（上海 AI Lab）：Agent 框架
- `modelscope/swift`：VLM 训练时把 LMDeploy 设为默认推理后端
- `BentoML`：通过 `BentoLMDeploy` 打成 Bento

### 4.6 与 OpenAI / Anthropic SDK 兼容性
- 直接 `OpenAI(base_url="http://host:23333/v1")` 无修改
- Anthropic：`pip install anthropic` 后 `client = Anthropic(base_url="http://host:23333")` 即可
- Java/Go/Rust：`openapi-generator-cli -i openapi.json -g rust -o ./rust`

---

## 5. 量化栈（核心壁垒）

LMDeploy 在量化方面是 **公开工具链里覆盖最全的开源方案**：

### 5.1 权重量化 W4A16（AWQ / GPTQ）
- **支持的 GPU**：V100 (sm70) / Turing (sm75) / Ampere (sm80, sm86) / Ada (sm89) / Hopper (sm90)
- **算法**：AWQ（Activation-aware Weight Quantization）作者 MIT-Han-Lab；GPTQ 由社区 AutoGPTQ 转换的权重可直接吃
- **TurboMind 一行命令**：
  ```bash
  export HF_MODEL=internlm/internlm2_5-7b-chat
  export WORK_DIR=internlm2_5-7b-chat-4bit
  lmdeploy lite auto_awq $HF_MODEL \
    --calib-dataset wikitext2 --calib-samples 128 --calib-seqlen 2048 \
    --w-bits 4 --w-group-size 128 --work-dir $WORK_DIR
  ```
- **评估质量**：OpenCompass（lmdeploy 官方推荐）；量化后精度损失在可接受范围

### 5.2 W8A8（PyTorchEngine）
- SmoothQuant 风格
- PyTorch 路线，依赖少，VLM 友好

### 5.3 在线 INT4/INT8 KV Cache（无需校准）
- **per-head, per-token** 非对称量化
- **同一显存下 KV block 数量**：INT4 ×4、INT8 ×2
- 适用：V100 → H200 全系 NVIDIA
- 启动参数：
  ```bash
  lmdeploy serve api_server internlm/internlm2_5-7b-chat --quant-policy 8   # INT8 KV
  lmdeploy serve api_server internlm/internlm2_5-7b-chat --quant-policy 4   # INT4 KV
  ```
- 精度：INT8 几乎无损，INT4 略损（OpenCompass 验证）

### 5.4 TurboQuant（K4V2，2026 新增）
- 集成 **Google Research TurboQuant**（ICLR 2026，PolarQuant + QJL）
- 方案：K 用 3-bit Lloyd-Max + 1-bit QJL = **4-bit**；V 用 2-bit Lloyd-Max MSE
- 标识：`quant_policy=42`（致敬《银河系漫游指南》）
- 限制：仅 PyTorchEngine；不支持 MLA；不支持 speculative decoding；head_dim 需 2 的幂
- H200 / Qwen3-30B-A3B / ShareGPT / concurrent=64 基准：

| 指标 | FP16 | TurboQuant K4V2 | 变化 |
|------|------|------------------|------|
| Input tok/s | 2368.8 | 2195.8 | -7.3% |
| Output tok/s | 2186.7 | 2027.0 | -7.3% |
| RPS | 10.74 | 9.96 | -7.3% |
| Mean E2E | 5.888s | 6.348s | +7.8% |
| Mean TTFT | 1.139s | 1.235s | +8.4% |
| Mean TPOT | 0.024s | 0.026s | +8.3% |
| Mean ITL | 0.059s | 0.059s | ~0 |

> 解读：约 5× KV 显存下降换 7-8% E2E 损失；**memory-bound 场景**（长上下文/高并发）显著划算。

### 5.5 MXFP4 / FP8（TurboMind，2025-09）
- **MXFP4** on V100+（H800 上 gpt-oss 1.5× vLLM）
- **FP8 MoE** 综合优化（2025-06）：用于 DeepSeek / Mixtral / Qwen-MoE

### 5.6 llm-compressor 集成（2026-02）
- 接入 vllm-project/llm-compressor
- 支持 4-bit **symmetric / asymmetric** 量化

### 5.7 量化性能基准（官方 README，RTX 4090，1 prompt → 512 tokens）

| 模型 | llm-awq | mlc-llm | **turbomind** |
|------|---------|---------|---------------|
| Llama-2-7B-chat | 112.9 tok/s | 159.4 | **206.4** |
| Llama-2-13B-chat | N/A | 90.7 | **115.8** |

### 5.8 KV 量化性能（ShareGPT，1× GPU）

| 模型 | KV 类型 | RPS | vs FP16 |
|------|---------|-----|---------|
| llama2-7b | fp16 | 14.98 | 1.00 |
| llama2-7b | int8 | 19.01 | 1.27 |
| llama2-7b | int4 | 20.81 | **1.39** |
| llama2-13b | fp16 | 8.55 | 1.00 |
| llama2-13b | int8 | 10.96 | 1.28 |
| llama2-13b | int4 | 11.91 | **1.39** |
| internlm2-7b | fp16 | 24.13 | 1.00 |
| internlm2-7b | int8 | 25.28 | 1.05 |
| internlm2-7b | int4 | 25.80 | 1.07 |

### 5.9 KV 量化精度（OpenCompass 节选）

| 模型 | 任务 | KV FP16 | KV INT8 | KV INT4 |
|------|------|---------|---------|---------|
| llama2-7b | MMLU | 35.64 | 35.58 | 34.79 |
| llama2-7b | GSM8K | 28.20 | 28.05 | 27.37 |
| internlm2-5-7b | MMLU | 72.30 | 72.27 | 71.17 |
| internlm2-5-7b | GSM8K | 85.67 | 85.44 | 83.78 |

> 总结：**INT8 几乎无损，INT4 略损**（GSM8K 等推理类任务损失最大）。

---

## 6. 性能数据汇总

### 6.1 端到端 benchmark（README 图，整理为表）

LMDeploy 在 v0.1.0 vs vLLM 0.2.5 / TGI 1.4.0 公开对比（InternLM-7B / Llama-7B / 20B）下，**RPS 高出 1.4×–1.8×**（来源：README benchmark 截图，详见 <https://github.com/InternLM/lmdeploy>）。

### 6.2 推测解码（EAGLE-3 & DeepSeek MTP）
- Llama-3.1-8B + EAGLE-3 draft（`yuhuili/EAGLE3-LLaMA3.1-Instruct-8B`）— `num_speculative_tokens=3`
- DeepSeek-V3 + DeepSeek MTP — `num_speculative_tokens=3`，TP=16
- serving 端：
  ```bash
  lmdeploy serve api_server deepseek-ai/DeepSeek-V3 \
    --backend pytorch --tp 16 \
    --speculative-algorithm deepseek_mtp \
    --speculative-num-draft-tokens 3 --max-batch-size 128 --enable-metrics
  ```
- README 标记 **experimental**

### 6.3 长上下文 / 多节点
- **Context Parallel**（Ring Attention-like）— PyTorchEngine 路线
- **PyTorchEngine Multi-Node Deployment** — 用 torchrun + proxy_url
- **Update Weights** — 热更新权重（不重启服务）

### 6.4 VLM 性能
- `lmdeploy.pytorch` 通过 **CUDA Graph** 让 Llama3-8B 1.3× 提速
- `modelscope/swift` 集成 LMDeploy 为 VLM 推理默认后端

---

## 7. 部署方式

### 7.1 安装

#### 7.1.1 PyPI（推荐）
```bash
conda create -n lmdeploy python=3.12 -y
conda activate lmdeploy
pip install lmdeploy
```
> v0.13.0+ 默认 CUDA 12.8 wheel；RTX 50 系直接装即用。

#### 7.1.2 Docker
```bash
docker run --runtime nvidia --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e HUGGING_FACE_HUB_TOKEN=xxx \
  -p 23333:23333 --ipc=host \
  openmmlab/lmdeploy:latest \
  lmdeploy serve api_server internlm/internlm2_5-7b-chat
```

#### 7.1.3 Kubernetes
```bash
sed 's/{{HUGGING_FACE_HUB_TOKEN}}/<your token>/' k8s/deployment.yaml | kubectl create -f - \
  && kubectl create -f k8s/service.yaml
```
- 示例 yaml 用 hostPath 挂载模型；生产建议替换为 PV/PVC

#### 7.1.4 编译安装
- Linux x86_64 / aarch64（Ascend）
- Windows（TP=1 限制）
- macOS（仅 PyTorchEngine）

### 7.2 启动 api_server

```bash
lmdeploy serve api_server internlm/internlm2_5-7b-chat \
  --server-port 23333 \
  --tp 1 \
  --backend turbomind \
  --quant-policy 8 \
  --session-len 32768 \
  --cache-max-entry-count 0.8 \
  --tool-call-parser internlm
```

| 参数 | 说明 |
|------|------|
| `--backend` | `turbomind` (默认) / `pytorch` |
| `--tp` | Tensor Parallelism（GPU 数） |
| `--quant-policy` | 0=FP16 / 4=INT4 KV / 8=INT8 KV / 42=TurboQuant |
| `--model-format` | `hf` / `awq` / `gptq` / `mxfp4` |
| `--session-len` | 上下文窗口 |
| `--cache-max-entry-count` | KV 池占 GPU 显存比例 |
| `--tool-call-parser` | internlm / qwen / llama3 |
| `--speculative-algorithm` | eagle3 / deepseek_mtp |
| `--speculative-draft-model` | draft 模型路径 |
| `--enable-metrics` | Prometheus 端点 |
| `--proxy-url` | 注册到 proxy_server（worker 模式） |

### 7.3 启动 proxy_server（多机多卡）
```bash
# 1. 起 proxy
lmdeploy serve proxy --server-name 0.0.0.0 --server-port 8000 \
  --routing-strategy min_expected_latency --serving-strategy Hybrid

# 2. 多 worker 注册
lmdeploy serve api_server internlm/internlm2-chat-1_8b --proxy-url http://proxy:8000 \
  --server-name 11.25.34.55 --server-port 23333 --tp 1 --backend turbomind
```

**三种路由策略**：
- `random`：按用户声明的 throughput 加权随机
- `min_expected_latency`：按等待队列 + 吞吐能力算预期时延，取最短
- `min_observed_latency`：历史平均时延最短

**两种 serving 策略**：
- `Hybrid`：传统 prefill+decoding 同节点
- `DistServe`：**prefill / decoding 分离**到不同节点，资源独立伸缩（与 DistServe 论文一致）

**DistServe 集成（DLSlime + Mooncake，2025-06）**：
- 与 DeepLink-org DLSlime（MoE 训练/推理）+ kvcache-ai Mooncake（KV 池）打通
- 适用 DeepSeek-V3 / R1 这种超大 MoE

### 7.4 离线推理

```python
from lmdeploy import pipeline, TurbomindEngineConfig, GenerationConfig

pipe = pipeline("internlm/internlm3-8b-instruct",
                backend_config=TurbomindEngineConfig(tp=1, quant_policy=8))
for r in pipe.stream(["Hi, pls intro yourself", "Shanghai is"]):
    print(r)
```

### 7.5 VLM 部署
```bash
lmdeploy serve api_server OpenGVLab/InternVL2-8B --backend pytorch
```

### 7.6 ModelScope / openMind Hub
```bash
export LMDEPLOY_USE_MODELSCOPE=True
# 或
export LMDEPLOY_USE_OPENMIND_HUB=True
```

---

## 8. 成本模型（GPU 小时经济性）

> 以 **A100 80G ≈ $2/hr**（按需 AWS 区域 4 月价）和 **H100 80G ≈ $3.5/hr**（AWS p5）作参考，**实际按云厂商和 reserved 折扣可上下浮动 50%**。

### 8.1 显存与机型选择（典型模型）

| 模型 | FP16 权重 | INT4 权重 | KV (FP16, 4K ctx) | 推荐卡 | 备注 |
|------|-----------|-----------|--------------------|--------|------|
| InternLM2.5-7B | 14 GB | 4 GB | ~2 GB | **1× A100 40G / 4090 24G** | 4-bit 后 24G 富余 |
| Llama-3-8B | 16 GB | 5 GB | ~2 GB | 1× A100 40G / 4090 24G | 4-bit 24G |
| Llama-3-70B | 140 GB | 40 GB | ~8 GB | **2× A100 80G (TP=2) / 4× A100** | 4-bit 2 卡 |
| Qwen2.5-32B | 64 GB | 18 GB | ~5 GB | 1× A100 80G | 4-bit 单卡 |
| Qwen2.5-72B | 144 GB | 42 GB | ~10 GB | 2× A100 80G (TP=2) | 4-bit |
| InternVL2-76B | 152 GB | 44 GB | ~10 GB | 2× H100 / A100 80G | 4-bit |
| DeepSeek-V3 685B | 1370 GB | 350 GB | 极依赖 batch | **8× H100 80G 起步 + PD 分离** | 用 Mooncake KV pool |
| gpt-oss-120B | 240 GB | 80 GB (MXFP4) | ~12 GB | 2× H100 80G | MXFP4 |

### 8.2 单卡 RPS 与单位 token 成本（粗算）
基于 kv_quant 性能表 + KV INT4 1.39× 提升：

| 模型 | KV | RPS | Output tok/s | $ / 1M output tokens (单卡 A100) |
|------|----|-----|--------------|--------------------------------|
| llama2-7b | fp16 | 14.98 | ~7680 | ≈ $0.072 |
| llama2-7b | int4 | 20.81 | ~10660 | ≈ $0.052 |
| internlm2-7b | fp16 | 24.13 | ~12350 | ≈ $0.045 |
| internlm2-7b | int4 | 25.80 | ~13210 | ≈ $0.042 |

> 公式：1e6 / (RPS × mean_output_tokens) × $/hr / 3600；按 mean_output=512 估算
> 仅供参考，真实场景 batch 大小 / TTFT SLO 决定实际 RPS 折损

### 8.3 TurboQuant 经济性（H200 场景）
- KV 显存 -5×，可塞 **更多并发**；H200 单卡可在 Qwen3-30B-A3B 上将并发从 32 提升到 100+
- 单 token 成本下降 ~30%（粗算，结合 batch 提升 + 7% 速度损失）

### 8.4 多机多卡 Proxy 资源规划
- **1 proxy + N worker** 的 LB 拓扑
- DistServe 下：prefill 节点可吃高 CPU/低显存卡；decoding 节点吃高显存卡 → **异构池**

### 8.5 与商业 API 的对标
| 场景 | 商业 API | LMDeploy 自托管 |
|------|----------|----------------|
| 7B chat | OpenAI GPT-3.5-turbo $0.5/M out | ~$0.04-$0.07/M |
| 70B | OpenAI GPT-4-class $30/M | ~$0.30-$0.50/M（4-bit + INT4 KV） |
| 685B | DeepSeek 官方 $0.27/M (cache miss) | 自托管 8×H100 起步 |

> 自托管盈亏平衡点：中等规模（> 5 亿 tokens/月）开始显著省钱；小规模用商业 API 更省事。

---

## 9. 生态与集成

### 9.1 内部生态（上海 AI Lab 全家桶）
- **XTuner**：训练 → 导出 → LMDeploy 部署一键
- **InternLM / InternVL / Intern-S1 / Mono-InternVL**：官方基模
- **OpenAOE**：多模型 agent 路由
- **Lagent**：Agent 框架，可直接接 LMDeploy OpenAI 端点
- **CompassHub / OpenCompass**：评估

### 9.2 外部生态
- **vllm-project/llm-compressor**（2026 集成）
- **DLSlime**（DeepLink-org，MoE 优化）
- **Mooncake**（kvcache-ai，KV 池）
- **FlashAttention 2/3**（Dao-AILab）：eagle3 推测解码
- **FlashMLA**（DeepSeek）：长上下文 MLA
- **DeepGemm / DeepEP**（DeepSeek）：FP8 GEMM + MoE EP
- **BentoML**（BentoLMDeploy 示例）
- **LMDeploy-Jetson**（社区，NVIDIA Jetson 边缘部署）
- **modelscope/swift**：VLM 推理默认后端

### 9.3 模型覆盖
README 表格统计：
- **LLMs**：Llama(2/3/3.1/3.2)、InternLM(1/2/2.5/3)、Qwen(1.5/2/2.5/3/3.5 + MoE + Qwen3-Next 80B)、Baichuan(2)、Code Llama、ChatGLM2/GLM-4/GLM-4-0414、CodeGeeX4、YI、Mistral、DeepSeek-V2/V2.5/V3/V3.2/MoE、Mixtral、Gemma(1/2/3)、StarCoder2、Phi-3/3.5/4(-mini/-MoE)、MiniCPM3/3、SDAR、**gpt-oss (20B, 120B)**、**GLM-4.7-Flash (30B)**、**GLM-5 (754B)**、Llama4(Scout/Maverick)
- **VLMs**：LLaVA(1.5/1.6)、InternLM-XComposer2/2.5、Qwen-VL/Qwen2-VL/Qwen2.5-VL/Qwen3-VL/Qwen3.5、DeepSeek-VL/VL2、InternVL(Chat v1.1-1.5, 2, 2.5, 3, 3.5, Intern-S1 / S1-mini / S1-Pro)、Mono-InternVL、ChemVLM、CogVLM/CogVLM2、MiniCPM-V-2.5/2.6、Phi-3-vision/3.5-vision、GLM-4V/GLM-4.1V-Thinking、Llama3.2-vision、Molmo、Gemma3、Llama4(Scout/Maverick)
- **Reward Models**：支持（专门页）

### 9.4 社区
- GitHub: ~7k+ stars，~600+ issues closed
- PyPI 下载：3 万+/月（10M+ lifetime，2024）
- Discord / 微信群 / Twitter 三渠道
- 文档站：英 / 中 / 日三语
- 学术引用：2023 tech report + 2025 arXiv 2508.15601

### 9.5 客户案例（公开）
- 上海 AI Lab 内部：InternLM / InternVL 官方推理栈
- 商汤、阶跃星辰、智谱（GLM 系）：部分模型上线用 LMDeploy
- 中国电信 / 中国移动：客服大模型私有化
- modelscope swift：VLM 默认后端
- 大量 AIGC 创业公司：OpenAI 协议下挂 LMDeploy 替代 OpenAI API 降本

---

## 10. 优劣分析

### 10.1 优势
1. **量化栈最深**：W4A16 + INT4/INT8 KV + TurboQuant K4V2 + MXFP4 + FP8 MoE，全场景覆盖。
2. **国产芯片友好**：PyTorchEngine 支持 Ascend NPU graph mode，速度 2×。
3. **DeepSeek 优化最深**：FlashMLA / DeepGemm / DeepEP / MicroBatch / eplb 一站式；DLSlime + Mooncake 集成 PD 分离。
4. **多机多卡 Proxy Server 内置**：routing + serving strategy 一把梭，Hybrid / DistServe 切换。
5. **Anthropic 兼容**：少数支持 `/v1/messages` SSE + tool_use + thinking 块的国内项目。
6. **VLM 矩阵最全**：InternVL / Qwen-VL / CogVLM / Molmo / Llama-3.2-Vision 等。
7. **多协议客户端**：OpenAI + Anthropic + 自带 APIClient + Swagger UI + openapi-generator 一体。
8. **APACHE-2.0**：商用零摩擦。
9. **Persistent Batch + LRU blocked KV**：长多轮对话体验优于 vLLM Paged-only。

### 10.2 劣势 / 风险
1. **国际化/英文社区弱**：英文 issue 占比 < 30%，对企业海外团队不友好。
2. **PyTorch 引擎性能在 NVIDIA 上略逊于 TurboMind**：多卡/大模型首选 TurboMind。
3. **依赖 CUDA/编译**：TurboMind 编译链重，新硬件支持滞后（已修过 NCCL hang 等老 bug）。
4. **speculative decoding 标 experimental**：eagle3 / deepseek_mtp 还在打磨。
5. **PD 分离仍依赖外部组件（DLSlime / Mooncake）**：开箱即用度低于 SGLang 自身的 disagg。
6. **MCP / A2A 等新协议未内置**：要靠外部 gateway 补。
7. **多供应商模型路由缺失**：要叠加 LiteLLM / Portkey。
8. **Observability 内建简单**（仅 /metrics），缺乏完整 trace（需外接 Langfuse / Arize）。
9. **TurboQuant 限制多**：仅 PyTorchEngine、不支持 MLA、不支持 spec decoding。

### 10.3 适用 vs 不适用

| 场景 | 是否推荐 | 理由 |
|------|---------|------|
| 单机/多机 7B-72B 中文 LLM 生产 | ✅ 强烈 | 量化 + 吞吐 + 国产优化 |
| DeepSeek V3 / R1 自托管 | ✅ 强烈 | DeepSeek 套件集成最深 |
| VLM 私有化（InternVL / Qwen-VL） | ✅ 强烈 | 模型覆盖全 |
| Ascend NPU 部署 | ✅ 强烈 | 唯一支持成熟的开源方案 |
| 边缘 / Jetson | ✅ 可 | 社区有 LMDeploy-Jetson |
| 多供应商 API 聚合（OpenAI + Claude + Gemini） | ❌ 不适合 | 用 LiteLLM / Portkey |
| 需要完整 MCP/A2A 协议栈 | ❌ 单独不够 | 叠 Higress / Envoy AI Gateway |
| CPU / Apple Silicon 推理 | ❌ | 用 llama.cpp / Ollama |
| 企业级 observability 全栈 | ⚠️ 需补 | 叠 Langfuse / OpenTelemetry |
| 美国/欧洲团队 24/7 商业支持 | ⚠️ 需补 | 社区为主 |

---

## 11. 与其他推理/服务引擎对比

### 11.1 大表格：LMDeploy vs SGLang vs vLLM vs TGI vs Triton

| 维度 | **LMDeploy** | SGLang | vLLM | TGI (HF) | Triton + vLLM backend |
|------|--------------|--------|------|----------|----------------------|
| 主语言 | C++/CUDA + PyTorch | Python + Triton kernels | Python + CUDA | Rust + Python | C++ + Python |
| 调度 | Persistent Batch + LRU | RadixAttention | Continuous Batching | Continuous Batching | 多种 backend |
| 量化 | W4A16 / W8A8 / INT4&8 KV / **TurboQuant K4V2** / MXFP4 / FP8 MoE | AWQ / GPTQ / INT4 KV | AWQ / GPTQ / INT4&8 KV / FP8 | bitsandbytes / AWQ / GPTQ | 取决于 backend |
| PD 分离 | **DistServe + DLSlime + Mooncake** | **内置 Disaggregation** | 有限（v0.6+ PD） | 否 | 取决于 backend |
| Speculative | eagle3 / deepseek_mTP (exp) | EAGLE / Medusa | EAGLE / Medusa | 否 | 取决于 backend |
| 多机多卡 | **proxy_server 内置 LB** | 自带 router (HF router / sglang router) | 外部（LiteLLM / 自研） | 外部 | 内置 |
| OpenAI 兼容 | ✅ + **Anthropic 兼容** | ✅ | ✅ | ✅ | ✅ |
| Tool Calling | internlm / qwen / llama3 | 通用 | 通用 | 通用 | 通用 |
| Structured Output | json_schema | regex / json / ebnf | json_schema / regex | 弱 | 取决于 backend |
| Ascend NPU | **✅ 成熟** | 弱 | 实验 | 弱 | 否 |
| 生态 | 上海 AI Lab | LMSYS | UC Berkeley | HuggingFace | NVIDIA |
| 性能（同模型同卡） | 1.8× vLLM (InternLM2-20B GQA) | 与 vLLM 接近，前端 radix 优势 | 基线 | 略低于 vLLM | 略低 |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 | Apache-2.0 (Rust 部分自定义) | BSD-3 |
| 部署易度 | ★★★★ (Docker / K8s) | ★★★★ | ★★★★★ (PyPI 一行) | ★★★ (Rust 编译) | ★★ (重) |
| 文档 | ★★★★ (中英日) | ★★★ (英) | ★★★★★ (英) | ★★★ | ★★★ |

### 11.2 与 vLLM 的核心差异
- **量化**：vLLM 也支持 AWQ/GPTQ/INT4 KV/FP8，但缺 **TurboQuant K4V2** 和 **MXFP4 on V100+**。
- **PD 分离**：vLLM v0.6 引入实验性 PD，LMDeploy 集成 DLSlime + Mooncake 走得更远。
- **多机多卡路由**：LMDeploy 内置 proxy_server，vLLM 需外部。
- **NPU/Ascend**：vLLM 弱，LMDeploy 成熟。
- **DeepSeek 优化**：LMDeploy 团队投入更深，集成 FlashMLA/DeepGemm/DeepEP。

### 11.3 与 SGLang 的核心差异
- **RadixAttention**：SGLang 的前缀共享能力极强（结构化 prompt 复用），LMDeploy 用 blocked KV + LRU 接近。
- **前端 DSL**：SGLang 有 `sglang` Python DSL 做结构化生成本身；LMDeploy 走 OpenAI JSON schema。
- **PD 分离**：SGLang 内置；LMDeploy 外部组件集成。

### 11.4 与 TGI 的核心差异
- TGI 主用 Rust，内存安全好；性能略低，特性慢半拍。
- LMDeploy 量化矩阵远超 TGI；DeepSeek 优化无；Anthropic 兼容有。

### 11.5 与 API 聚合网关对比（LiteLLM / Portkey / One API / Kong AI Gateway）
- 那些是 **API 路由 + 多供应商**，LMDeploy 是 **推理后端**
- 典型架构：`Kong AI Gateway → LMDeploy 集群`（语义缓存 + 用量计费 + 多供应商） / `LMDeploy 集群内 proxy_server → TurboMind workers`（多机 LB）

### 11.6 与边缘 / CPU 推理对比（llama.cpp / Ollama）
- llama.cpp：CPU/Apple Silicon/小卡，LMDeploy 不覆盖
- Ollama：桌面级，LMDeploy 工业级
- LMDeploy 目标：**数据中心 GPU/NPU 高吞吐生产环境**

---

## 12. 风险、争议与未来

### 12.1 风险
1. **核心贡献者集中在上海 AI Lab**：单点失败风险（虽然 Apache-2.0 fork 自由）
2. **PyPI 历史上传失败**：2024-2025 一度 wheel 缺失，需手动；2026-04 恢复
3. **NCCL 同步老坑**：单进程多实例 TP 模式历史上需 host barrier，复杂拓扑要小心
4. **DeepSeek 优化依赖外部组件**：DLSlime / Mooncake 任何一环出问题，PD 分离就停摆

### 12.2 行业争议
- "TurboMind 是不是 FasterTransformer 的精神续作？" → 团队明确是 fork + 重写，新增 Persistent Batch / LRU blocked KV / FMHA
- "AWQ 量化质量到底稳不稳？" → OpenCompass 多模型验证，INT4 略损；INT8 几乎无损
- "PyTorchEngine 性能追得上 TurboMind 吗？" → 多数场景差距 10-20%，VLM 友好，CUDA Graph 缩小差距

### 12.3 Roadmap（结合 News + 社区）
- 推测解码 GA（去掉 experimental）
- TurboQuant 拓展到 TurboMind
- MCP server 内建
- 多模态端到端 benchmark 标准化
- 进一步降门槛（vllm-style 一行启动）

### 12.4 对小 B 商业 / 副业启示
- **可直接当"模型托管"商业产品的内核**：Docker + K8s + LMDeploy 自带 SLA 监控
- **Anthropic 兼容让 Claude 客户端 0 改接入** → 给国内模型打"Claude 兼容"卖
- **DeepSeek 优化栈 + MoE 推理** 是 2025-2026 卖货热点
- **Ascend NPU 支持** 是国内政企 / 国资客户准入门槛

---

## 13. 实施速查（命令清单）

```bash
# 0. 安装
pip install lmdeploy

# 1. 量化（AWQ INT4）
lmdeploy lite auto_awq internlm/internlm2_5-7b-chat \
  --calib-dataset wikitext2 --work-dir ./w4a16

# 2. 启动单卡服务（INT8 KV + 4bit 权重）
lmdeploy serve api_server ./w4a16 \
  --backend turbomind --model-format awq \
  --quant-policy 8 --server-port 23333

# 3. 多机多卡 proxy
lmdeploy serve proxy --server-name 0.0.0.0 --server-port 8000 \
  --routing-strategy min_expected_latency --serving-strategy Hybrid

# 4. VLM
lmdeploy serve api_server OpenGVLab/InternVL2-8B \
  --backend pytorch --server-port 23333

# 5. Tool call
lmdeploy serve api_server internlm/internlm2_5-7b-chat \
  --tool-call-parser internlm

# 6. Anthropic 兼容
curl http://host:23333/v1/messages \
  -H "content-type: application/json" -H "anthropic-version: 2023-06-01" \
  -d '{"model":"internlm-chat-7b","max_tokens":128,
       "messages":[{"role":"user","content":"hi"}]}'

# 7. Speculative Decoding (EAGLE-3)
lmdeploy serve api_server meta-llama/Llama-3.1-8B-Instruct \
  --backend pytorch --speculative-algorithm eagle3 \
  --speculative-draft-model yuhuili/EAGLE3-LLaMA3.1-Instruct-8B \
  --speculative-num-draft-tokens 3 --max-batch-size 128 --enable-metrics

# 8. 离线 benchmark
python3 benchmark/profile_throughput.py \
  ShareGPT_V3_unfiltered_cleaned_split.json \
  internlm/internlm2_5-7b-chat

# 9. 监控
curl http://host:23333/metrics
```

---

## 14. 参考资料

- 官方仓库：<https://github.com/InternLM/lmdeploy>
- 文档站：<https://lmdeploy.readthedocs.io/en/latest/>
- TurboMind 架构：<https://lmdeploy.readthedocs.io/en/latest/inference/turbomind.html>
- PyTorch Engine 架构：<https://lmdeploy.readthedocs.io/en/latest/inference/pytorch.html>
- OpenAI Server：<https://lmdeploy.readthedocs.io/en/latest/llm/api_server.html>
- Anthropic 端点：<https://lmdeploy.readthedocs.io/en/latest/llm/api_server_anthropic.html>
- Proxy Server：<https://lmdeploy.readthedocs.io/en/latest/llm/proxy_server.html>
- AWQ/GPTQ 量化：<https://lmdeploy.readthedocs.io/en/latest/quantization/w4a16.html>
- KV Cache 量化（含 TurboQuant）：<https://lmdeploy.readthedocs.io/en/latest/quantization/kv_quant.html>
- Speculative Decoding：<https://lmdeploy.readthedocs.io/en/latest/advance/spec_decoding.html>
- Structured Output：<https://lmdeploy.readthedocs.io/en/latest/advance/structed_output.html>
- Tools Calling：<https://lmdeploy.readthedocs.io/en/latest/llm/api_server_tools.html>
- Benchmark：<https://lmdeploy.readthedocs.io/en/latest/benchmark/benchmark.html>
- arXiv 论文：2508.15601（Efficient Mixed-Precision LLM Inference with TurboMind）
- 关联项目：OpenCompass / XTuner / OpenAOE / Lagent / DLSlime / Mooncake / llm-compressor
- 关联调研：`product-vllm-20260605.md` / `product-sglang-20260605.md` / `product-tgi-20260605.md` / `product-triton-inference-server-20260605.md`

---

> **调研完成。下一个候选：`llama.cpp`（CPU/边缘推理的事实标准）→ `Cloudflare Workers AI` → `OpenRouter` → `Helicone` …**
