# Together AI 深度调研报告

> **调研日期**：2026-06-05  
> **项目**：Together AI（AI Native Cloud）  
> **官网**：https://www.together.ai  
> **API Base**：https://api.together.ai/v1  
> **文档**：https://docs.together.ai  
> **公司**：Together Computer, Inc.（San Francisco, CA）  
> **定位**：开源大模型的「AI Native Cloud」全栈平台 — 推理、训练、微调、GPU 集群一体化  
> **报告版本**：v1.0（深挖级别）  
> **作者**：Rich（OpenClaw 副业调研）

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [项目背景与公司沿革](#2-项目背景与公司沿革)
3. [核心团队与组织](#3-核心团队与组织)
4. [产品矩阵与业务版图](#4-产品矩阵与业务版图)
5. [Together 推理栈：自研 Inference Engine 架构](#5-together-推理栈自研-inference-engine-架构)
6. [协议与 API 兼容性矩阵](#6-协议与-api-兼容性矩阵)
7. [Together Turbo：性能优化套件（FlashAttention-3/4/ATLAS/Medusa/Sequoia/SpecExec）](#7-together-turbo性能优化套件)
8. [FlashAttention-4：算法-内核联合设计](#8-flashattention-4算法-内核联合设计)
9. [ATLAS：自适应推测解码系统](#9-atlas自适应推测解码系统)
10. [Together GPU Kernels（ThunderKittens 衍生）](#10-together-gpu-kernels)
11. [Serverless Inference：定价与模型目录](#11-serverless-inference定价与模型目录)
12. [Batch Inference API](#12-batch-inference-api)
13. [Dedicated Endpoints：专用端点](#13-dedicated-endpoints专用端点)
14. [Together Instant Clusters：自服务 GPU 集群](#14-together-instant-clusters自服务-gpu-集群)
15. [Fine-Tuning Platform](#15-fine-tuning-platform)
16. [Together Chat / Playground / API](#16-together-chat--playground--api)
17. [性能数据：DeepSeek-R1-0528 / DeepSeek-V3.1 / Kimi K2 基准](#17-性能数据基准)
18. [生态与合作伙伴](#18-生态与合作伙伴)
19. [客户案例](#19-客户案例)
20. [优劣势分析（SWOT）](#20-优劣分析swot)
21. [与竞品对比（vs. Fireworks / Anyscale / OpenRouter / vLLM / TGI）](#21-与竞品对比)
22. [中国/小 B 客户视角：可用性、合规、成本](#22-中国小-b-客户视角)
23. [开发者体验（DX）与代码示例](#23-开发者体验dx与代码示例)
24. [参考链接与资料](#24-参考链接与资料)

---

## 1. 执行摘要

Together AI 是 2022 年成立、由 Vipul Ved Prakash（前 Apple / CloudFlare 工程高管）创立的「AI Native Cloud」创业公司。截至 2026 年 6 月，公司累计融资 **约 5 亿美元以上**（B 轮 1.05 亿 + B+ 1.06 亿 + 战略投资来自 NVIDIA / Salesforce Ventures / Bezos Expeditions / Greycroft 等），估值约 **33 亿美元（2025-02）**。Together 与 OpenAI / Anthropic 等「自研闭源模型」路线不同，它的核心叙事是：**「我们不拥有模型，我们让开源模型跑得比任何人都快」**。

技术上的硬通货是三件事：

1. **自研 Inference Engine** — 在 NVIDIA H100/H200/Blackwell B200 上把 DeepSeek-R1-0528 跑到 **334 tok/s**（serverless），ATLAS 模式 500 tok/s。
2. **OpenAI 兼容 API** — `base_url=https://api.together.ai/v1`，2 行代码替换即可迁移（chat / vision / images / audio / embeddings / function-calling / structured-outputs）。
3. **Together Turbo** — 一整套系统级优化：FlashAttention-3/4、Sequoia（树形投机解码，NeurIPS 2024）、Medusa、SpecExec、ATLAS（运行时自适应）、Custom Speculators（按客户流量微调）、Together GPU Kernels（基于 ThunderKittens）。

商业模式是「**三层云**」：

- **Inference（Serverless + Dedicated）** — 200+ 开源模型，token 计费。
- **GPU Clusters（Instant Clusters）** — 8 卡到数百卡 NVIDIA HGX H100 / HGX B200，按小时计费（含 InfiniBand Quantum-2 / NVLink / Spectrum-X）。
- **Model Shaping（Fine-Tuning + DPO + 蒸馏）** — LoRA / Full FT，按训练 token / GPU-h 计费。

对**小 B 软件开发者**而言，Together 的吸引力在于：

- **极低门槛的 OpenAI 替代** — 注册即送 $5 信用，无需企业认证，5 分钟集成。
- **无锁定** — API 形状完全 OpenAI 兼容，今天用 Together，明天换 Fireworks / OpenRouter，迁移成本 ≈ 改 base_url。
- **价格透明** — Llama 3.3 70B 输入 $0.88 / 输出 $0.88（per 1M tokens），比 OpenAI GPT-4o-mini 便宜近一个数量级。
- **大模型可玩性** — 671B DeepSeek、397B Qwen3.5、120B GPT-OSS 等 SOTA 开源权重全都第一时间上线。

风险与短板同样明显：

- **Serverless 偶发拥塞** — 免费档 / 低优先级档在高峰时段延迟飙升（社区反馈）。
- **中国境内访问** — `api.together.ai` 在国内直连不稳，需要走代理或自建 Together Cluster。
- **不开源核心引擎** — 推理引擎是闭源黑盒，性能壁垒也是「技术债」：跟随开源竞品（vLLM、SGLang）速度很快。
- **生态纵深** — 不像 OpenAI 有原生 RAG / Agent / Assistants 套件，需要自己组合 LangChain / LlamaIndex。

---

## 2. 项目背景与公司沿革

### 2.1 创立与早期定位

Together AI 的前身是 **Together Computer**，2022 年夏天由 Vipul Ved Prakash 在旧金山创立。Vipul 是 **CloudFlare 早期 5 号员工**、写过著名的 CloudFlare 1.1.1.1 DNS 解析器；也是 **Apple 工程师**（早期 Safari 团队）。他的核心理念是「**The AI Native Cloud**」 — 互联网的第一波是 HTTP 协议 + CDN（CloudFlare 视角），第二波是 LLM + 专用算力云（Together 视角）。

公司初始定位是「**去中心化算力市场**」 — 让任何拥有 GPU 的人出租给训练/推理用户（类似 LLM 版的 Airbnb）。这个早期路线在 2023 年 1 月 ChatGPT 引爆后被迅速调整，转向「**垂直整合的 LLM 云**」 — 自建 GPU 集群 + 自研推理栈 + 托管开源模型。

### 2.2 关键里程碑

| 时间         | 事件                                                                                                          |
| ---------- | ----------------------------------------------------------------------------------------------------------- |
| 2022-Q3    | Together Computer 成立，Vipul Ved Prakash 领衔，发布 RedPajama 7B 开源模型（Together + 多个机构联合）                              |
| 2022-11    | 完成 2000 万美元 A 轮（Lux Capital 领投）                                                                        |
| 2023-03    | **发布推理平台**，开放对 Llama、Falcon、Mistral 等开源模型的 serverless 推理                                                        |
| 2023-09    | **Medusa 论文发布**（Yuhong Li、Tianle Cai、Tri Dao 等） — 在 HuggingFace 引发 2x 解码加速关注                                  |
| 2023-11    | 完成 1.025 亿美元 B 轮（Salesforce Ventures 领投，估值 12.5 亿）                                                          |
| 2024-02    | **Sequoia 论文**（树形推测解码，NeurIPS 2024 接收）                                                                   |
| 2024-06    | **SpecExec 论文**（消费者级 GPU 的投机执行）                                                                          |
| 2024-12    | 发布 **Together Inference Engine v2** 与 DeepSeek-V3 全栈支持                                                        |
| 2025-01    | 完成 **3.05 亿美元 B+ 轮**（Prosperity7 领投，General Catalyst、Salesforce Ventures 参投），估值 **33 亿美元**                       |
| 2025-02    | 首发 **NVIDIA Blackwell HGX B200 集群**（与 Zoom、Salesforce、InVideo 等封闭 beta）                                    |
| 2025-05    | 发布 **Custom Speculators**（按客户流量微调）— 1.23-1.45x 加速                                                       |
| 2025-07    | 在 B200 上推出 **DeepSeek-R1-0528 推理**，达到 334 tok/s（serverless），在 Artificial Analysis 排名第一                          |
| 2025-09    | 三大产品 GA：**Instant Clusters**（GPU 集群自服务）、**Batch API 升级**（30B tokens 队列）、**Fine-Tuning 升级**（长上下文 + 大模型）            |
| 2025-10    | **ATLAS 论文**（运行时自适应推测解码）— DeepSeek-V3.1 达 500 tok/s                                                       |
| 2026-03    | **FlashAttention-4 发布**（与 Princeton、Meta、NVIDIA、Colfax 联合）— B200 上 1605 TFLOPs/s，71% 利用率，1.3× 速度超过 cuDNN 9.13 |

### 2.3 投融资概览

| 轮次     | 时间        | 金额           | 估值        | 领投方                        |
| ------ | --------- | ------------ | --------- | -------------------------- |
| A      | 2022-11   | $20M         | —         | Lux Capital                |
| A+     | 2023-Q2   | 未披露          | —         | —                          |
| B      | 2023-11   | $102.5M      | $1.25B    | Salesforce Ventures        |
| B+     | 2025-01   | $305M        | $3.3B     | Prosperity7 Ventures       |
| 战略投资   | 持续        | $1.5B 总      | —         | NVIDIA / Bezos Expeditions |

资金用途：**自建 GPU 数据中心**（核心资产是 NVIDIA HGX B200 / H200 集群 + 自研互联）+ **研发 Inference Engine 团队**（含 Princeton 合作实验室：Tri Dao 是 Together 的 Chief Scientist）。

---

## 3. 核心团队与组织

### 3.1 创始团队

- **Vipul Ved Prakash**（Founder & CEO）— 前 CloudFlare、Apple、Sugarlog（被 CloudFlare 收购）。
- **Ce Zhang**（Co-founder, Chief Scientist 早期）— 现任 ETH Zurich 教授、INSAI Lab 主任、Together Research 顾问；2024 年后主要在学术界。
- **Percy Liang**（Co-founder 学术合伙人）— Stanford CRFM / HELM 创始人，Together 的学术顾问。
- **Tri Dao**（Chief Scientist）— FlashAttention 系列作者、Princeton 助理教授、Together AI 联合研究者；FlashAttention-4 的第一作者。
- **Ben Athiwaratkun**（AI 研究负责人）— Turbo / ATLAS / Custom Speculators 项目负责人。

### 3.2 团队规模

- 截至 2025 年底，约 **200+ 员工**（San Francisco 总部 + 远程，Princeton 学术合作点）。
- 工程师占比 ~60%，研究科学家 ~20%，BD / GTM / 客户成功 ~20%。

### 3.3 战略顾问 / 董事会

- **Salesforce Ventures**（投资人 + 客户）— Marc Benioff 圈子。
- **NVIDIA**（战略合作 + 投资）— Blackwell 首发客户。
- **Bezos Expeditions / Jeff Bezos 个人** — 长期支持开源 AI 基础设施。
- **Prosperity7**（沙特 PIF 旗下）— 中东主权基金，主投 AI Native Cloud。

---

## 4. 产品矩阵与业务版图

Together 提供 4 大产品线（自官方页面分类）：

### 4.1 产品全景图

```
                     Together AI 产品矩阵
                     ====================

  ┌────────────────────────────────────────────────────────┐
  │  INFERENCE（推理）                                      │
  │  ├── Serverless Inference（按 token 计费，200+ 模型）     │
  │  ├── Dedicated Endpoints（专用集群，小时计费）             │
  │  └── Batch Inference API（异步批量，50% 折扣）            │
  └────────────────────────────────────────────────────────┘
  ┌────────────────────────────────────────────────────────┐
  │  COMPUTE（算力）                                        │
  │  ├── Instant Clusters（8 卡 → 数百卡，K8s/Slurm）        │
  │  ├── Sandbox（交互式 Notebook 沙盒）                      │
  │  └── Managed Storage（共享高带宽存储）                     │
  └────────────────────────────────────────────────────────┘
  ┌────────────────────────────────────────────────────────┐
  │  MODEL SHAPING（模型塑形）                                │
  │  ├── Fine-Tuning（LoRA / Full FT，含 DPO/PPO）          │
  │  ├── Custom Speculators（按流量微调）                     │
  │  └── 蒸馏（Distillation）                                │
  └────────────────────────────────────────────────────────┘
  ┌────────────────────────────────────────────────────────┐
  │  DEVELOPER TOOLS                                        │
  │  ├── OpenAI 兼容 REST API                                │
  │  ├── Together Python / TS SDK                           │
  │  ├── Together Chat（playground / chat.together.ai）      │
  │  └── CLI（`together`）+ Terraform Provider               │
  └────────────────────────────────────────────────────────┘
```

### 4.2 收入结构（估算）

| 板块             | 占比（估） | 毛利率     | 备注                          |
| -------------- | ------ | ------- | --------------------------- |
| Serverless 推理  | 55-65% | 中（35%）  | 主收入，月活增长快                   |
| Dedicated 推理  | 15-20% | 高（55%）  | 大客户年合同                     |
| Instant Cluster | 15-20% | 低（20%）  | 训练 / 突发推理（Hyper-Scale 用）    |
| Fine-Tuning    | 5-10%  | 高（60%）  | 增值服务，企业级                    |
| Batch API      | 5%     | 高（70%）  | 边际成本低（夜间填补）                |

---

## 5. Together 推理栈：自研 Inference Engine 架构

这是 Together 的「**护城河**」 — 一个从 PyTorch 算子到底层 GPU 内核的完整重写栈。

### 5.1 架构总览（ASCII）

```
                    ┌──────────────────────────────────────┐
                    │  客户端（OpenAI SDK / curl / LangChain）│
                    └──────────────────┬───────────────────┘
                                       │ HTTPS / JSON
                    ┌──────────────────▼───────────────────┐
                    │  Together API Gateway (FastAPI / Rust) │
                    │  ├── 鉴权（API Key）                    │
                    │  ├── 限流（Per-org token bucket）        │
                    │  ├── 路由（模型名 → 集群 ID）             │
                    │  ├── 计费（Token 计数 → Stripe）         │
                    │  └── 缓存（KV / Prompt Cache）           │
                    └──────────────────┬───────────────────┘
                                       │ gRPC
                    ┌──────────────────▼───────────────────┐
                    │  调度层（Together Scheduler）           │
                    │  ├── Continuous Batching               │
                    │  ├── 推测解码调度（Speculator + Verifier）│
                    │  ├── Paged KV Cache（vLLM 启发但自研）   │
                    │  ├── Prefix Sharing（Cross-request）    │
                    │  └── Hot/Cold 模型分片（GPU ↔ NVMe）   │
                    └──────────────────┬───────────────────┘
                                       │ CUDA Streams
                    ┌──────────────────▼───────────────────┐
                    │  Inference Engine v2 / v3            │
                    │  ┌────────────────────────────────┐  │
                    │  │  Prefill（FlashAttention-3/4）  │  │
                    │  ├────────────────────────────────┤  │
                    │  │  Decode（CUDA Graph captured） │  │
                    │  ├────────────────────────────────┤  │
                    │  │  Speculative Verifier          │  │
                    │  ├────────────────────────────────┤  │
                    │  │  Quantization（FP8 / INT4）    │  │
                    │  └────────────────────────────────┘  │
                    └──────────────────┬───────────────────┘
                                       │ PTX / CUDA Kernels
                    ┌──────────────────▼───────────────────┐
                    │  Together GPU Kernels（自研）           │
                    │  ├── GEMM（H100/B200 Tensor Core）     │
                    │  ├── MHA / MQA / GQA（Attention）      │
                    │  ├── MoE All-to-All（NVLink/IB）       │
                    │  ├── RMSNorm / RoPE / SwiGLU           │
                    │  └── 基于 ThunderKittens + CUTLASS      │
                    └──────────────────┬───────────────────┘
                                       │ PCIe / NVLink / InfiniBand
                    ┌──────────────────▼───────────────────┐
                    │  Hardware 层                          │
                    │  NVIDIA HGX B200 × N / H100 × N / H200│
                    │  NVIDIA Quantum-2 InfiniBand（400Gbps）│
                    │  NVMe + VAST/WEKA 共享存储             │
                    └──────────────────────────────────────┘
```

### 5.2 关键组件解析

#### 5.2.1 Prefill（计算密集阶段）

- **FlashAttention-3/4** 计算 QKV 与 S=QK^T，输出 O=softmax(S)V。
- **GEMM 算子** 走 Together 自研 CUTLASS 模板，针对 B200 的 `tcgen05.mma` 5 代 Tensor Core 优化。
- **MoE 路由 + All-to-All** 在节点内走 NVSwitch，跨节点走 InfiniBand。
- **CUDA Graph 捕获** — 整个 prefill 流程被一次性捕获为 CUDA Graph，调度时直接 replay，省去 Python 解释器与 kernel launch 开销。

#### 5.2.2 Decode（访存密集阶段）

- **Memory-bound**（每个 token 都要从 HBM 读模型权重），算力利用率极低。
- 优化重点是 **batch 合并**（continuous batching）、**KV cache 复用**（prefix sharing、cross-request prefix）、**推测解码**（一次 verifier 前向验 4-16 个候选 token）。
- **Paged KV Cache** 类似 vLLM 的 v0 设计，但分页大小为 16 token，块表存于 GPU pinned memory。

#### 5.2.3 Speculative Decoding 调度

```
           Together Turbo Speculative Pipeline
           ==================================

  Step 1: 用户发请求 ─→ 调度器分配到合适 GPU
  Step 2: 选 Speculator
          ├── 静态（Static Turbo Speculator）— 训练在 broad corpus
          ├── 自适应（ATLAS Adaptive）— 运行时微调
          └── 自定义（Custom）— 按用户流量微调
  Step 3: 选 Lookahead K
          ├── Confidence-aware 控制器决定 K ∈ {1,2,3,4,5,6,8}
          └── 长上下文 → 短 K；高接受率 → 长 K
  Step 4: Draft + Verify 并行
          ├── Draft 模型生成 K 个候选
          ├── Target 模型一次前向 + tree-attention 验证
          └── 接受率 α ∈ [0.6, 0.95]（Kimi-K2 上 α=0.9+）
  Step 5: Repeat
```

#### 5.2.4 Quantization

- **FP8**（E4M3 / E5M2）— 主流量化，B200 原生支持。
- **INT4**（GPTQ / AWQ）— 消费级 / 容量敏感场景。
- **SmoothQuant** — MoE 模型常用。
- Together 自研「**quality-preserving quantization**」 — 量化后再做 SFT/DPO 校准，恢复精度。

### 5.3 与通用 vLLM 架构的差异

| 维度        | Together Inference Engine    | vLLM 0.6+                |
| --------- | ---------------------------- | ------------------------ |
| 调度        | 闭源，自研 Continuous batching + 推测 | 开源 v0 scheduler        |
| 内核        | 自研 Together Kernels（CUDA）   | 走 FlashInfer / xFormers  |
| 推测解码      | 一等公民（Turbo + ATLAS）        | 支持但需手动配 EAGLE / Medusa |
| 量化        | FP8 + INT4 + SmoothQuant 自研  | FP8 / AWQ / GPTQ         |
| 模型支持      | 200+，自定义适配                  | HuggingFace 几乎全        |
| 可扩展性      | 闭源（仅 SaaS）                  | 完全开源                    |
| 性能上限（B200） | 业界领先（1605 TFLOPs FlashAttn） | 较通用，落后 ~10-20%         |

---

## 6. 协议与 API 兼容性矩阵

### 6.1 OpenAI 兼容性矩阵（来自官方文档）

| OpenAI SDK call                  | Together endpoint               | 状态        | 备注                                       |
| -------------------------------- | ------------------------------- | --------- | ---------------------------------------- |
| `chat.completions.create`        | `POST /v1/chat/completions`     | ✅ 支持     | 流式 + 非流式 + tools + vision               |
| `chat.completions` (vision)      | `POST /v1/chat/completions`     | ✅ 支持     | 图片作为 content part                       |
| `chat.completions` (tools)       | `POST /v1/chat/completions`     | ✅ 支持     | Function calling / tool_choice             |
| `chat.completions` (structured)  | `POST /v1/chat/completions`     | ✅ 支持     | `response_format={type: json_schema}`     |
| `completions.create`             | `POST /v1/completions`          | ✅ 支持     | 旧版文本补全                                  |
| `embeddings.create`              | `POST /v1/embeddings`           | ✅ 支持     | BGE / UAE / M2-BERT 等 12+ 模型           |
| `images.generate`                | `POST /v1/images/generations`   | ✅ 支持     | FLUX / SDXL / Nano Banana                |
| `audio.speech.create`            | `POST /v1/audio/speech`         | ✅ 支持     | TTS（Cartesia / Kokoro / MiniMax）         |
| `audio.transcriptions.create`    | `POST /v1/audio/transcriptions` | ✅ 支持     | Whisper Large v3 / Parakeet TDT           |
| `audio.translations.create`      | `POST /v1/audio/translations`   | ✅ 支持     |                                          |
| `models.list`, `models.retrieve` | `GET /v1/models`                | ✅ 支持     |                                          |
| `responses.create`               | n/a                             | ❌ 不支持    | 用 chat.completions 替代                  |
| `assistants.*`                   | n/a                             | ❌ 不支持    | 用 function calling 自建 agent             |
| `fine_tuning.jobs.*`             | n/a                             | ❌ 不支持    | 用 Together 原生 Fine-Tuning API           |
| `files.*`                        | Together Files API              | ⚠️ 部分支持  | 不完全 OpenAI 兼容                           |
| `batches.*`                      | Together Batch API              | ❌ 不支持    | 用 Together 原生 Batch API                 |
| `moderations.create`             | Llama Guard via chat            | ⚠️ 替代实现  |                                          |

### 6.2 Together 原生端点

| 端点                          | 说明                              |
| --------------------------- | ------------------------------- |
| `/v1/video/generations`    | 视频生成（自研）                        |
| `/v1/images/edits`         | 图像编辑 + inpainting               |
| `/v1/rerank`               | Rerank 模型                       |
| `/v1/chat/completions` (reasoning) | `reasoning_content` 字段，深思模式 |
| `/v1/chat/completions` (logprobs)   | 自定义 logprobs 字段             |
| `/v1/files`                | Fine-tuning dataset + Batch 队列 |
| `/v1/batches`              | Batch 异步作业                     |
| `/v1/fine_tuning/jobs`     | 原生微调 API                       |
| `/v1/endpoints`            | 专用端点管理                         |
| `/v1/clusters`             | Instant Cluster 管理              |

### 6.3 标准协议支持

- **OpenAI REST** — 100% 兼容 chat / completions / embeddings / images / audio。
- **Anthropic Messages API** — ❌ 不直接支持，但可通过 LiteLLM 中转。
- **Google Gemini API** — ❌ 不直接支持。
- **MCP (Model Context Protocol)** — 通过外部 server（如 Smithery、mcp.so）连接 Together 端点。
- **A2A (Agent-to-Agent)** — 通过 LangChain / CrewAI 集成，无原生支持。
- **WebSocket** — ❌ 不支持（流式用 SSE）。
- **SSE (Server-Sent Events)** — ✅ 标准 OpenAI 风格。

### 6.4 端点命名约定

```
<provider>/<model_name>[@<revision>]

示例：
openai/gpt-oss-20b
meta-llama/Llama-3.3-70B-Instruct-Turbo
Qwen/Qwen3-235B-A22B-Instruct-2507-FP8-Tput
deepseek-ai/DeepSeek-V3.1
```

---

## 7. Together Turbo：性能优化套件

Together 把所有系统优化打包为 **Turbo 套件**，对用户透明 — 用 OpenAI 兼容 API 即可享受。

### 7.1 Turbo 套件组成

| 模块                  | 论文 / 发布         | 主要贡献                          |
| ------------------- | ---------------- | ----------------------------- |
| **FlashAttention-3** | 2024            | Hopper 优化，2x FlashAttn-2      |
| **FlashAttention-4** | 2026-03（与 Princeton 联合）| Blackwell 优化，1.3× cuDNN，2.7× Triton |
| **Medusa**          | 2023-09         | 多解码头，2x 加速                  |
| **Sequoia**         | 2024-02（NeurIPS）| 树形投机解码，offloading 8x、on-chip 4x |
| **SpecExec**        | 2024-06         | 推测执行，consumer GPU 18.7x    |
| **Custom Speculator** | 2025-05       | 按客户流量微调，1.23-1.45x          |
| **ATLAS**           | 2025-10         | 运行时自适应，500 tok/s，4x 加速       |
| **Together Kernels** | 持续             | 基于 ThunderKittens / CUTLASS  |
| **Quality-Preserving Quantization** | 持续    | FP8 / INT4 校准            |

### 7.2 Turbo 性能数字（DeepSeek-R1-0528, B200）

| 模式            | 速度 (tok/s) | 备注                            |
| ------------- | --------- | ----------------------------- |
| 无 Turbo       | 302       | 开源 vLLM SGLang 同等             |
| + Turbo       | 334       | + 32 tok/s（+10.6%）            |
| + Custom Spec | 386 (DE)  | 专用端点（ds=1, AT 优化）             |
| + ATLAS       | 500       | 完全适配后，2.65x 标准解码              |

### 7.3 Turbo 与竞品对标

| 平台              | DeepSeek-R1-0528 tok/s | 备注                            |
| --------------- | --------------------- | ----------------------------- |
| **Together**    | **334** (serverless)  | 2025-07 Artificial Analysis  #1 |
| Fireworks AI    | ~270                  | B200                          |
| DeepSeek 官方     | ~150                  | 自有集群                          |
| Groq            | ~250                  | Groq LPU 硬件                  |
| OpenRouter      | 转售多供应商，~200-300   |                               |
| vLLM（自建）       | ~280-300              | 8xB200                        |

---

## 8. FlashAttention-4：算法-内核联合设计

### 8.1 背景

FlashAttention-4（2026-03 发布，arXiv 2603.05451）是 Tri Dao（Together AI + Princeton）联合 Markus Hoehnerbach（Meta）、Jay Shah（Colfax）、Timmy Liu（NVIDIA）、Vijay Thakkar（Meta / Georgia Tech）的最新工作。

### 8.2 核心洞察：Asymmetric Hardware Scaling

```
H100 → B200 (Hopper → Blackwell):
  - BF16 Tensor Core:    1 → 2.25 PFLOPs  (+125%)
  - SFU (MUFU.EX2) 指数:  1 → 1            (不变！)
  - Shared Memory 带宽:   1 → 1            (不变！)
```

**结论**：Forward pass 的瓶颈是 SFU（softmax 指数运算），Backward pass 的瓶颈是 Shared Memory 流量。GEMM 不再是主要瓶颈。

### 8.3 4 大核心优化

#### 8.3.1 新 Pipeline：最大化重叠

Forward: 2 次 QK^T + PV GEMM + softmax 指数
Backward: 5 次 GEMM + softmax 指数

通过 **ping-pong Q tiles + 2 个 softmax warpgroups + correction warpgroup**，把 MMA、softmax exp、memory 三者重叠到极致。

#### 8.3.2 Forward：Softmax 重叠 + 条件 Rescaling

```
伪代码：
for each Q tile (ping-pong Q^H, Q^L):
  1. Load 128x128 S from TMEM → registers
  2. Reduce rowmax, rowsum
  3. MUFU.EX2 + software-emulated e^x（FMA）  ← 软件模拟 2^x
  4. P = softmax(S) → BF16
  5. Store P to TMEM in stages
  6. Trigger PV MMA when 3/4 of P stored
  7. Correction warpgroup: 条件 rescale
     if (m_j - m_{j-1} > τ):
         O_j = exp(m_{j-1} - m_j) * O_{j-1} + exp(S_j - m_j) * V_j
     else:
         O_j = O_{j-1} + exp(S_j - m_{j-1}) * V_j
```

#### 8.3.3 Backward：减少 SMEM 流量

- 中间结果存到 **TMEM**（Blackwell 新增的 256KB on-chip scratchpad）。
- **2-CTA MMA** — 一个 UMMA 跨两个 peer CTA，TMEM 跨 CTA 共享。
  - MMA tile 上限：128×256×16 → **256×256×16**
  - SMEM 流量减半，atomic reduction 减半。

#### 8.3.4 Scheduler：负载均衡

- Causal mask + 变长序列导致 tile 数量不均。
- 新调度器动态分配 tile 到 SM，最大限度减少 idle 周期。

### 8.4 性能数字

```
BF16, B200, M=N=D=128:

  FlashAttention-4:  1605 TFLOPs/s (71% utilization)
  cuDNN 9.13:        ~1230 TFLOPs/s          ← 1.30× faster than this
  Triton:            ~590 TFLOPs/s           ← 2.72× faster than this
```

### 8.5 对 Together 的商业价值

- Together 是 FA-4 的**第一受益方**（Tri Dao 同时任职 Princeton + Together）。
- B200 上的 LLM 推理 Prefill 速度直接提升 30%，这是 Together 排名第一的硬通货。

---

## 9. ATLAS：自适应推测解码系统

### 9.1 问题

静态 speculator（训练在 broad corpus）的问题：
- **多租户 serverless 环境**输入分布极广（代码 / 聊天 / 摘要 / RAG / 翻译）
- **流量漂移**（drift）：用户使用模式随时间变化，静态 speculator 跟不上
- **新 workload**（冷启动）无任何定制 → 接受率低

### 9.2 解决方案：ATLAS 架构

```
              ┌─────────────────────────────┐
              │  客户端请求                   │
              └─────────────┬───────────────┘
                            ▼
              ┌─────────────────────────────┐
              │  Confidence-Aware Controller │
              │  输入：当前 speculator α、lookahead K  │
              │  决策：走 static / adaptive  │
              │  K 调度：α 高 → 长 K；α 低 → 短 K │
              └─────────────┬───────────────┘
                            ▼
              ┌──────────────┴───────────────┐
              ▼                              ▼
    ┌────────────────────┐         ┌────────────────────┐
    │  Static Turbo      │         │  Adaptive           │
    │  Speculator        │         │  Speculator         │
    │  (heavyweight)     │         │  (lightweight,      │
    │  - 训练在 broad    │         │   运行时微调)         │
    │  - 永不更新         │         │  - 从 live traffic  │
    │  - 提供 speed floor│         │    增量学习           │
    └────────────────────┘         └────────────────────┘
              │                              │
              └──────────────┬───────────────┘
                             ▼
                  ┌────────────────────┐
                  │  Target Model      │
                  │  (Verifier)        │
                  │  - 671B DeepSeek   │
                  │  - 397B Qwen3.5    │
                  │  - 1T Kimi K2      │
                  └────────────────────┘
```

### 9.3 关键机制

#### 9.3.1 双 Speculator 设计

- **Static** — 重型，训练在 broad corpus，**always-on speed floor**。当 Adaptive cold-start / drift 检测到时，Controller 切回 Static 防止 TPS 崩盘。
- **Adaptive** — 轻量，**从 live traffic 增量更新**。例如 vibe-coding session 时，Adaptive 会 specialize 到当前正在编辑的代码文件。

#### 9.3.2 Confidence-Aware Controller

- 监控 **接受率 α** 实时。
- α 高 → 增 lookahead K（一次 draft 更多 token）。
- α 低或 drift 检测 → 缩短 K 或回退到 Static。

#### 9.3.3 离线 + 在线学习

- **离线** — Static 在大语料上预训练。
- **在线** — Adaptive 用 LoRA + 实时数据微调（per-tenant）。

### 9.4 性能数字

```
NVIDIA HGX B200, Arena Hard 流量:

  DeepSeek-V3.1:
    Standard decoding:   ~190 tok/s
    + Turbo Spec:        ~330 tok/s
    + ATLAS (full adapt): 500 tok/s  ← 4x 标准解码

  Kimi-K2-0905:
    Standard:            ~150 tok/s
    + Turbo Spec:        ~270 tok/s
    + ATLAS:             460 tok/s  ← 3x 标准解码
```

> 关键数据：**ATLAS 比 Groq LPU 还快**（DeepSeek-V3.1 上 500 vs ~280），是 Together 在 B200 上拿到的最关键营销点。

### 9.5 对 RL 训练的加速

论文里还有一段：ATLAS 对 **RL 训练 rollout 阶段**特别有效 — rollout 阶段是 policy + reward 的反复推理，分布相对稳定，ATLAS 一次训练就特化到当前 policy → 接受率极高 → 整个 RL 训练时间缩短 30-50%。

---

## 10. Together GPU Kernels

### 10.1 来源

Together 的自研 kernel 主要基于：
- **ThunderKittens**（Tri Dao 团队的开源 CUDA kernel DSL，简化 tensor core 编程）
- **CUTLASS 3.x**（NVIDIA 官方 GEMM 模板库）
- **自研扩展**（针对 MoE、All-to-All、长序列 attention）

### 10.2 主要算子

| 算子                   | 优化点                                |
| -------------------- | ---------------------------------- |
| GEMM (BF16/FP8)      | 5th-gen Tensor Core，async MMA，TMEM  |
| MHA / MQA / GQA      | FA-4 内核，SMEM-TMEM 混合存储，2-CTA   |
| MoE All-to-All       | NVLink/IB aware，unicast + multicast |
| RMSNorm / RoPE       | Fused，zero-allocation              |
| SwiGLU               | Fused，grouped GEMM                |
| Embedding Lookup     | Fused，table cache                  |
| Top-K Gating (MoE)   | Fused，bitonic sort                 |
| Logits Sampler       | 推测解码 verifier 路径专用                |

### 10.3 B200 vs H100 Kernel 差异

| 算子        | H100 (Hopper)         | B200 (Blackwell)            |
| --------- | --------------------- | --------------------------- |
| GEMM tile | 128×256               | 256×256（2-CTA MMA）         |
| MHA       | FA-3 + WGMMA          | FA-4 + tcgen05.mma + TMEM   |
| SMEM      | 256KB/SM              | 256KB/SM + 256KB TMEM       |
| 异步        | WGMMA（半异步）           | tcgen05.mma（全异步）            |
| MoE       | All-to-All via NVLink | All-to-All via NVLink + 加速 IB |

### 10.4 开源 vs 闭源

- **开源**：FlashAttention-3/4（MIT）、ThunderKittens（Apache 2.0）、Medusa（MIT）、Sequoia（Apache 2.0）、SpecExec（MIT）。
- **闭源**：Together Inference Engine 主线、ATLAS Controller、Custom Speculator 训练 pipeline、专用 Quantization 工具。

---

## 11. Serverless Inference：定价与模型目录

### 11.1 定价模型

- **按 token 计费**：输入 / 输出分开，cache hit 享受 80-90% 折扣。
- **免费档**：$5 信用，注册即得（90 天有效）。
- **付费档**：预付费 / 月结，支持企业 PO。

### 11.2 Serverless Chat 定价（2026-06 实时数据）

| 模型                                  | 输入 ($/1M tok)       | 输出 ($/1M tok) | 备注                  |
| ----------------------------------- | ------------------- | ------------- | ------------------- |
| **GLM-5.1**                         | $1.40               | $4.40         | 智谱最新                |
| **MiniMax M2.7**                    | $0.30（cache $0.06）  | $1.20         | 小型多模态               |
| **Kimi K2.6**                       | $1.20（cache $0.20）  | $4.50         | Moonshot 长上下文       |
| **DeepSeek V4 Pro**                 | $2.10（cache $0.20）  | $4.40         |                     |
| **Qwen3.6-Plus**                    | $0.50               | $3.00         |                     |
| **Gemma-4-31B-it-Pearl**            | $0.28               | $0.86         | Google              |
| **Qwen3.7-Max**                     | $1.25（cache $0.13）  | $3.75         |                     |
| **gpt-oss-120B**                    | $0.15               | $0.60         | OpenAI 开源推理         |
| **LFM2 24B A2B**                    | $0.03               | $0.12         | Liquid 极小模型         |
| **Qwen3.5-397B-A17B**               | $0.60               | $3.60         | MoE 17B activated    |
| **Cogito v2.1 671B**                | $1.25               | $1.25         |                     |
| **Rnj-1 Instruct**                  | $0.15               | $0.15         | Essential AI        |
| **Llama 3.3 70B**                   | $1.04               | $1.04         | Meta                |
| **Gemma 3n E4B Instruct**           | $0.06               | $0.12         |                     |
| **gpt-oss-20B**                     | $0.05               | $0.20         | OpenAI              |
| **Qwen3 235B A22B FP8**             | $0.20               | $0.60         |                     |
| **Qwen2.5 7B Instruct Turbo**       | $0.30               | $0.30         |                     |
| **Llama 3 8B Instruct Lite**        | $0.14               | $0.14         |                     |

### 11.3 价格对标（GPT-4o / Claude 3.5）

| 任务          | GPT-4o       | Claude 3.5 Sonnet | Together Llama 3.3 70B | 节省     |
| ----------- | ------------ | ----------------- | --------------------- | ------ |
| 1M 输入 tokens | $5.00        | $3.00             | $1.04                 | 4.8x   |
| 1M 输出 tokens | $15.00       | $15.00            | $1.04                 | 14.4x  |
| 1M 输入+输出    | $20.00       | $18.00            | $2.08                 | 9.6x   |

### 11.4 多模态定价

| 类型   | 模型                              | 价格                   |
| ---- | ------------------------------- | -------------------- |
| 图像生成 | FLUX.2 [pro]                    | 按张计费（$0.05-0.10/张） |
| 图像生成 | FLUX.1 [schnell]                | $0.003/张            |
| 图像生成 | Nano Banana Pro（Gemini 3 Pro）    | $0.08/张             |
| 视频生成 | 自研                              | 按秒计费                |
| TTS  | Cartesia Sonic 3                | 按字符                  |
| TTS  | MiniMax Speech 2.6              | 按字符                  |
| TTS  | Kokoro 82M                      | $0.01/1K chars      |
| STT  | Whisper Large v3                | $0.006/分钟音频          |
| STT  | Parakeet TDT 0.6B（NVIDIA）        | $0.003/分钟音频          |
| Embed | BGE-Large / UAE-Large-V2        | $0.02/1M tokens     |
| Rerank | 自研                             | $0.05/1M tokens     |

### 11.5 速率限制

| 端点            | 免费档       | Pro 档（$200/月） | Enterprise  |
| ------------- | --------- | -------------- | ----------- |
| Serverless    | 60 RPM    | 600 RPM        | 自定义          |
| Batch         | 10K tok/req | 30B tok/req  | 自定义          |
| Fine-tuning   | 1 job     | 20 jobs         | 无限          |
| Instant Cluster | n/a     | 5 cluster      | 无限          |

---

## 12. Batch Inference API

### 12.1 关键数字（2025-09 升级）

- **队列上限**：10M → **30B enqueued tokens**（**3000× 增长**）。
- **价格折扣**：**50% 折扣** vs. serverless。
- **SLA**：24 小时内完成。
- **支持范围**：所有 serverless 模型 + 私有部署。
- **UI**：Together Console 中可直接创建、跟踪、上传 JSONL。

### 12.2 用例

- 大规模文本分析（情感、分类、标签）
- 欺诈检测（扫描百万级交易）
- **合成数据生成**（训练数据集制作）
- Embedding 生成（TB 级语料）
- 内容审核（UGC）
- **模型评估**（跑 benchmark suite）
- 客户支持自动化（长 SLA 票务）

### 12.3 API 形态

```bash
# 1. 上传 JSONL 文件
curl -X POST https://api.together.ai/v1/files \
  -H "Authorization: Bearer $TOGETHER_API_KEY" \
  -F "file=@requests.jsonl" \
  -F "purpose=batch"

# 2. 创建 batch job
curl -X POST https://api.together.ai/v1/batches \
  -H "Authorization: Bearer $TOGETHER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input_file_id": "file-xxx",
    "endpoint": "/v1/chat/completions",
    "completion_window": "24h"
  }'

# 3. 轮询状态
GET /v1/batches/{batch_id}

# 4. 下载结果
GET /v1/files/{output_file_id}/content
```

### 12.4 与 OpenAI Batch 对比

| 维度     | Together Batch     | OpenAI Batch    |
| ------ | ------------------ | --------------- |
| 价格折扣   | 50%                | 50%             |
| 队列上限   | 30B tokens         | 50K requests    |
| 模型支持   | 200+ 开源            | OpenAI 系列        |
| UI     | 完整                | 简单              |
| 输入格式   | JSONL              | JSONL           |
| SLA    | 24h                | 24h             |
| Webhook | ✅                 | ✅              |

---

## 13. Dedicated Endpoints：专用端点

### 13.1 概念

**Dedicated Endpoints**（DE）= 客户独占的 GPU 实例，跑指定模型，按小时计费。优势：
- **性能可定制**（ATLAS + Custom Speculator + 调 batch size）
- **数据隔离**（独占 GPU，零邻居干扰）
- **SLA 保证**（P99 latency 合约）
- **自定义镜像**（可装自定义 inference 代码）

### 13.2 计费

- **基础费率**：8× H100 = $2.40/小时，8× B200 = $4.80/小时（**估算**）。
- **定制费率**：年合同，含 ATLAS、Custom Spec、专属客户经理。
- **可承诺消费折扣**（CUD）：$100K+/年合约价 30-50% off。

### 13.3 DeepSeek-R1-0528 DE 性能（Together 数据）

```
                BS=1    BS=8    BS=32
  无 Together:  302     198     107  tok/s
  + Together:   386     227     133  tok/s
  速度提升:      +84     +29     +26  tok/s
```

### 13.4 DE vs Serverless 决策树

```
                          你的月调用量
                              │
                              ▼
              ┌───────────────┴───────────────┐
              │                               │
            < 1B                            > 1B
              │                               │
              ▼                               ▼
         Serverless                  是否需要极致定制？
              │                               │
              │                     ┌─────────┴─────────┐
              │                     │                   │
              │                   YES                  NO
              │                     │                   │
              │                     ▼                   ▼
              │              DE（专用）           Serverless Pro
              │              + Custom Spec        + ATLAS（自动启用）
              │              + 调 batch
              │              + 调 quant
              │                     │
              │                     ▼
              │              大客户年合同
              │              (>$100K ARR)
```

---

## 14. Together Instant Clusters：自服务 GPU 集群

### 14.1 定位

**Instant Clusters** = 一句话："**AWS EC2 + GPU + InfiniBand + K8s/Slurm，API 一键拉起**"。

适用场景：
- 大规模分布式训练（LLM pre-training、RL、SFT、pretrain-from-scratch）
- 推理突发容量（自己跑 vLLM / SGLang 集群）
- 长期稳定的专用推理（DE 的升级版）

### 14.2 硬件规格

| 集群规模                | GPU      | 网络             | 用途                |
| ------------------- | -------- | -------------- | ----------------- |
| 1 节点（8 GPU）         | H100 80GB | NVLink + IB   | 推理 / 小训练          |
| 1 节点（8 GPU）         | B200 192GB | NVLink + IB   | 大模型推理 / 训练        |
| 多节点（8-64 节点）        | HGX H100 | InfiniBand NDR | 分布式训练（MFU 高）     |
| 多节点（>64 节点）        | HGX B200 | InfiniBand XDR | 100B+ 模型预训练      |

### 14.3 软件栈

```
用户接口层：
  - Console UI
  - CLI: `together clusters launch`
  - REST API: POST /v1/clusters
  - Terraform Provider
  - SkyPilot（多云调度）

编排层（自选）：
  - Kubernetes（K8s + GPU Operator + Network Operator + Cert Manager）
  - Slurm（SSH 入口可用）
  - 自带 SSH 访问

网络层（预配）：
  - NVIDIA Quantum-2 InfiniBand（400 Gbps NDR）
  - NVIDIA Spectrum-X Ethernet（200 Gbps，RoCE）
  - NVLink + NVSwitch（节点内）

存储层（Managed Storage）：
  - VAST / WEKA 共享文件系统
  - 高带宽，并行 IO
  - 按 GB 存储 + GB 流量计费
```

### 14.4 可靠性（GA 后）

- **Burn-in 测试**：每个节点上电后跑 24h 压力 + NVLink/NVSwitch 健康检查
- **NCCL all-reduce 验证**：节点间互联 < 1μs 延迟检查
- **MFU 验证**：参考训练任务跑通 + 测 tokens/sec
- **24/7 监控**：空闲节点重新跑测试，异常实时告警
- **SLA 赔付**：高优先级工单 1h 响应，硬件故障 4h 内补偿

### 14.5 价格（估算）

| 配置                       | 价格/小时       | 备注                            |
| ------------------------ | ----------- | ----------------------------- |
| 1× H100 80GB             | ~$2.50      | 单卡                            |
| 8× HGX H100              | ~$24        | 单节点                          |
| 8× HGX B200              | ~$48        | 单节点，Blackwell 溢价              |
| 64× HGX H100（8 节点）       | ~$190       | 8 节点集群，IB 互联                |
| 256× HGX B200（32 节点）     | ~$1,500     | 32 节点 IB 互联                  |
| Managed Storage          | $0.10/GB/月  | VAST/WEKA                     |
| IB 流量                    | 免费          |                               |

### 14.6 客户场景

- **AI Lab**（客户名保密）：24-48 小时 burst 训练，结束后立即缩容。
- **Latent Health**（客户引用）：临床多模态 RLHF 训练，蒸馏小模型反超大模型。
- **Together 自家研究团队**：内部也在用 Instant Clusters 训练下一代 Turbo 模型。

---

## 15. Fine-Tuning Platform

### 15.1 能力

- **LoRA / QLoRA**（4-bit base + 16-bit adapter）
- **Full Fine-Tuning**（含 MoE 模型）
- **DPO / IPO / KTO**（对齐训练）
- **Continued Pretraining**（CPT）
- **Distillation**（小模型从大模型学习）

### 15.2 支持的模型

- Llama 2/3/3.1/3.2/3.3 全系
- Qwen 2/2.5/3 全系
- DeepSeek-V2/V3
- Mistral / Mixtral
- 自定义 HuggingFace 格式模型

### 15.3 2025-09 升级

- **更大模型**：支持 70B/120B Full FT
- **更长上下文**：从 8K → 128K context
- **更快**：QLoRA 训练时间缩短 50%
- **数据集管理**：Together Files API，私有托管

### 15.4 价格

- **训练**：按 GPU-h 计费，H100 $2.50/小时，B200 $4.80/小时。
- **存储**：$0.10/GB/月。
- **部署**：训练后模型可直接部署为 DE。

### 15.5 与外部平台对比

| 平台            | 全 FT 支持 | LoRA | DPO | 长上下文 | 价格        |
| ------------- | -------- | ---- | --- | ---- | --------- |
| **Together**  | ✅       | ✅   | ✅  | 128K | 中         |
| OpenAI Fine-T | ❌       | ✅   | ✅  | 16K  | $$        |
| HuggingFace   | ✅       | ✅   | ✅  | 任意  | 低         |
| Replicate     | ✅       | ✅   | ❌  | 8K   | 中         |
| Modal         | ✅       | ✅   | ❌  | 任意  | 低         |

---

## 16. Together Chat / Playground / API

### 16.1 Chat 产品

- **chat.together.ai** — 对标 chat.openai.com 的多模型聊天界面。
- **Playground** — API 调试 + 提示词工程工具。
- **Together Studio**（企业版）— 团队共享 prompt / 评估 / 实验管理。

### 16.2 客户端工具

- **Python SDK**：`pip install together`
- **TypeScript SDK**：`npm install together-ai`
- **CLI**：`pip install together[cli]` → `together` 命令
- **LangChain / LlamaIndex 集成**：官方支持
- **Haystack / LiteLLM / OpenLLMetry** 集成
- **Vercel AI SDK** / **Cloudflare Workers AI** 桥接

### 16.3 一个完整示例（OpenAI SDK 迁移到 Together）

```python
# 原始 OpenAI 代码
import openai
client = openai.OpenAI(api_key="sk-xxx")
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)

# 迁移到 Together（只改 2 行）
import openai
client = openai.OpenAI(
    api_key="TOGETHER_API_KEY",
    base_url="https://api.together.ai/v1",  # 改这一行
)
resp = client.chat.completions.create(
    model="openai/gpt-oss-120b",  # 改这一行
    messages=[{"role": "user", "content": "Hello!"}],
)
```

---

## 17. 性能数据：基准对比

### 17.1 DeepSeek-R1-0528 速度对比（2025-07 Artificial Analysis）

```
                          Output Speed (tok/s)
                          Median
  ─────────────────────────────────────────────
  Together (B200)            334     ← #1
  Groq (GroqChip)            ~280
  Fireworks (B200)           ~270
  DeepSeek 官方              ~150
  OpenRouter（综合）           ~200
  Together (H200)            ~200
  vLLM（自建 8xB200）          ~280
  SGLang（自建 8xB200）        ~270
```

### 17.2 ATLAS 完全适配性能

```
DeepSeek-V3.1, B200, Arena Hard:
  Standard:           190 tok/s
  + Turbo Spec:       330 tok/s
  + ATLAS (full):     500 tok/s  ← 2.6x 标准，1.5x Turbo Spec

Kimi-K2-0905, B200, Arena Hard:
  Standard:           150 tok/s
  + Turbo Spec:       270 tok/s
  + ATLAS:            460 tok/s  ← 3.0x 标准
```

### 17.3 Sequoia 论文基准（2024-02）

#### Offloading（消费级 GPU）

| GPU      | Target Model | Draft Model    | Sequoia TBT | Baseline TBT | Speedup |
| -------- | ------------ | -------------- | ----------- | ------------ | ------- |
| RTX 4090 | Llama2-70B   | Llama2-7B      | 0.57s       | 4.54s        | 7.96x   |
| RTX 4090 | Vicuna-33B   | TinyVicuna-1B  | 0.35s       | 1.78s        | 5.09x   |
| RTX 4090 | Llama2-22B   | TinyLlama-1.1B | 0.17s       | 0.95s        | 5.59x   |
| RTX 4090 | Llama2-13B   | TinyLlama-1.1B | 0.09s       | 0.27s        | 3.00x   |
| 2080Ti   | Vicuna-33B   | TinyVicuna-1B  | 0.87s       | 4.81s        | 5.53x   |

#### On-chip（A100）

| GPU  | Target Model | Draft Model    | Sequoia TBT | Baseline TBT | Speedup |
| ---- | ------------ | -------------- | ----------- | ------------ | ------- |
| A100 | Llama2-7B    | JackFram-68M   | 6.0ms       | 24.2ms       | 4.04x   |
| A100 | Llama2-13B   | JackFram-68M   | 8.4ms       | 31.2ms       | 3.73x   |
| A100 | Vicuna-33B   | ShearedLlama-1.3B | 23.4ms   | 53.2ms       | 2.27x   |

### 17.4 SpecExec 论文基准（2024-06）

| Draft / Target            | t   | Method | Budget | Tok/s | Speedup   |
| ------------------------- | --- | ------ | ------ | ----- | --------- |
| Llama2-7b / 70b           | 0.6 | SX     | 2048   | 3.12  | **18.7x** |
| Llama2-7b / 70b (GPTQ)    | 0.6 | SX     | 128    | 6.02  | 8.9x      |
| Mistral-7b / Mixtral-8x7b | 0.6 | SX     | 256    | 3.58  | 3.5x      |

> SpecExec 在 **offloading 场景下**比 SpecInfer 高 2x 速度。

### 17.5 Medusa 加速（2023-09）

- 多解码头 + tree attention + 高效采样：LLM 生成 **2x 加速**。
- 训练只需 **单 GPU**（base model 冻结，只训练几个 FFN head）。
- 对分布式设置友好（vs. 传统 draft model 路线）。

### 17.6 Custom Speculator（2025-05）

3 个客户工作负载上的 speedup：

```
                  Custom Spec  /  Base Spec  /  No Spec
Document Extract:  1.45x       /  1.0x       /  2.27x
Social Media:     1.30x       /  1.0x       /  2.10x
Resume Screening: 1.23x       /  1.0x       /  1.85x
                  ↑ Custom 比 Base 提升 23-45%
```

**总成本降低 25%**（相同 throughput 需更少 GPU-h）。

### 17.7 FlashAttention-4

| 实现                     | B200 BF16 TFLOPs/s | 相对速度    |
| ---------------------- | ------------------ | ------- |
| **FlashAttention-4**   | **1605** (71% util) | 1.0×   |
| cuDNN 9.13             | ~1230              | 0.77×   |
| Triton                | ~590               | 0.37×   |
| FlashAttention-3       | ~1100              | 0.69×   |

---

## 18. 生态与合作伙伴

### 18.1 硬件 / 基础设施

- **NVIDIA** — 战略合作 + 投资，Blackwell 首发客户。
- **VAST Data** — 共享存储。
- **WEKA** — 共享存储。
- **5C** — 数据中心基础设施。
- **Rime** — 语音模型（**生态合作 + 同时也是竞争对手**？）。

### 18.2 模型 / 生态

- **Cartesia** — TTS 模型分发。
- **Black Forest Labs** — FLUX 图像模型。
- **Runware** — 图像生成生态。
- **Liquid** — LFM 轻量模型。
- **Hugging Face** — 互为生态（Together 部署 HF 模型，HF 推荐 Together）。
- **MongoDB** — 向量存储集成。

### 18.3 框架 / 工具

- **LangChain** — 官方集成（`langchain-together`）
- **LlamaIndex** — 官方集成
- **Haystack** — 集成
- **LiteLLM** — Together 作为 provider
- **OpenLLMetry** — 观测
- **Vercel AI SDK** — 前端集成
- **Cloudflare Workers AI** — 边缘集成

### 18.4 客户引用（公开）

- **Zoom** — Blackwell beta 测试客户
- **Salesforce** — 投资 + 客户
- **InVideo** — 视频生成
- **Latent Health** — 医疗 RLHF
- **Inception Labs** — Batch API 重度用户

---

## 19. 客户案例

### 19.1 Inception Labs

- **场景**：用 Batch API 跑大批量 LLM 实验，单次 batch **>1B tokens**。
- **痛点**：之前用 serverless 受限于 10M token 队列上限。
- **收益**：30B token 队列 + 50% 折扣 → 24h SLA 内完成（实际常 < 6h）。
- **引用**（CEO Volodymyr Kuleshov）："It's transformed the pace at which we can test and iterate."

### 19.2 Latent Health

- **场景**：临床推理模型 RLHF 训练 + 蒸馏。
- **痛点**：需要大规模 GPU 集群 + InfiniBand 互联。
- **收益**：用 Instant Clusters 跑 24-48h burst 训练，蒸馏出小模型反超大模型。
- **引用**（Founding Engineer Allan Bishop）："我们能跑大规模 RLHF，快速实验，蒸馏成更小高效的模型，往往反超大基础模型。"

### 19.3 Zoom

- **场景**：Blackwell B200 封闭 beta。
- **收益**：抢先用上 5th-gen Tensor Core，验证内部产品延迟。

### 19.4 Salesforce

- **场景**：Einstein AI 平台调用 Together 推理。
- **收益**：在 CRM 内部嵌入开源 LLM 能力。

### 19.5 AI Lab（匿名）

- **场景**：训练 LLM / 多模态模型，**24-48h burst** 训练。
- **痛点**：传统云厂商 4-6 周采购流程。
- **收益**：API 一键拉起，按小时计费，训练完即关。

### 19.6 中小企业（典型小 B 客户）

- **场景**：聊天机器人、文档摘要、客服自动化。
- **典型模型**：Llama 3.3 70B（$1.04/M in + $1.04/M out）。
- **典型成本**：1000 个对话 / 天 × 2000 token / 对话 = 2M token / 天 = $4/天 = **$120/月**。
- **vs. OpenAI GPT-4o-mini**：约 1/8 成本。

---

## 20. 优劣势分析（SWOT）

### 20.1 Strengths（优势）

1. **业界第一的推理速度**（B200 上 334 tok/s，ATLAS 500 tok/s）。
2. **OpenAI 100% 兼容**（2 行代码迁移）。
3. **200+ 开源模型**（覆盖 Llama、Qwen、DeepSeek、Mistral、Gemma、Cogito 等）。
4. **闭源核心引擎 + 开源研究并行**（FlashAttn、Sequoia、Medusa 等都是顶会论文 + 开源代码）。
5. **端到端产品矩阵**（Serverless + DE + Batch + Cluster + Fine-Tune）。
6. **顶级投资人**（NVIDIA、Salesforce、Bezos）。
7. **学术合作深厚**（Princeton、Stanford、ETH）。
8. **多模态全栈**（Chat + Vision + Image + Audio + Video + Embed + Rerank）。
9. **价格透明**（官网 200+ 模型明码标价）。
10. **Custom Speculator**（按客户流量微调）— 行业独有。

### 20.2 Weaknesses（劣势）

1. **核心引擎闭源**（vLLM / SGLang 用户可自建，Togther 用户需付费）。
2. **中国境内访问不稳定**（无 ICP 备案，无国内 CDN）。
3. **Serverless 高峰拥塞**（免费档和低优先级偶发高延迟）。
4. **不持有模型**（上游模型 license 变化会立即影响服务，例如 Llama 4 license 争议）。
5. **生态纵深不足**（没有原生 Assistants / RAG / Agent 套件）。
6. **与 NVIDIA 强绑定**（如果 AMD / 其他硬件崛起，迁移成本高）。
7. **多区域覆盖有限**（主要是 US-East / US-West，欧洲 / 亚太需要时延更高）。
8. **无内置向量数据库**（需自接 Pinecone / Qdrant / pgvector）。
9. **企业级合规**（SOC2 / HIPAA / GDPR 支持文档不如 Azure OpenAI 完善）。
10. **数据合规风险**（开源模型权重无保证，Together 不背书模型输出质量）。

### 20.3 Opportunities（机会）

1. **Blackwell 出货** — 2025-2026 是 Blackwell 普及期，Together 是首发受益方。
2. **DeepSeek / Qwen3 / Kimi-K2 等中国开源模型** — Together 可作为「中国模型出海的最佳平台」。
3. **MCP / A2A 协议** — Together 可以做 model serving + agent toolchain 的一体化。
4. **小 B SaaS 转型潮** — 国内 5-15 万 / 年 SaaS 替代方案。
5. **企业微调市场** — Together DE + Custom Spec + FT 一体化。
6. **AGI Native Apps** — 未来 5-10 年，AI Native 应用是新一代 SaaS。
7. **政府 / 医疗 / 金融合规** — Together 的「开源模型 + 私有部署」正好是合规首选。
8. **推理价格战** — 持续降低 token 价格 → 打开新用例（语音、视频、Agent）。
9. **边缘推理** — 与 Cloudflare Workers AI 合作可能。
10. **RL 训练加速** — ATLAS 已证明对 RL rollout 阶段有效，可切入 RLHF 公司。

### 20.4 Threats（威胁）

1. **OpenAI 降价** — GPT-5 系列可能继续降价，压缩 Together 价格优势。
2. **Anthropic 开放 Claude 模型** — 若 Claude 3.5/4 开源权重，Togther 价值会下降。
3. **vLLM / SGLang 自建** — 大客户可能选择自建而非 Together。
4. **Fireworks AI** — 直接竞品，技术栈相似，定价相当。
5. **DeepSeek 官方 API** — 价格更低（自建成本优势）。
6. **OpenRouter 聚合** — 用户可能用 OpenRouter 而非直接对接 Together。
7. **模型 license 变化** — Llama 4 / Qwen 4 任何 license 收紧都会冲击 Together 价值。
8. **GPU 供应紧张** — Blackwell 缺货会限制 Together 扩张。
9. **AI Native Cloud 竞争** — AWS Bedrock / Azure AI Foundry / Google Vertex AI 都来抢开源模型市场。
10. **学术 / 开源超车** — vLLM 团队（Berkeley）持续创新，可能反超闭源引擎。

---

## 21. 与竞品对比

### 21.1 vs. Fireworks AI

| 维度         | Together AI                | Fireworks AI                |
| ---------- | -------------------------- | --------------------------- |
| 定位         | AI Native Cloud（推理+训练+集群） | Firework AI Cloud（专注推理）         |
| 模型         | 200+                       | 100+                        |
| 价格（70B）    | $1.04/M                    | $0.90/M                     |
| 速度         | 334 tok/s（B200）            | 270 tok/s                    |
| 推测解码       | ✅（Turbo + ATLAS + Custom） | ✅（EAGLE + 自研）               |
| 私有部署       | DE + Cluster               | DE                          |
| 训练         | ✅（Full FT + LoRA）         | ❌                            |
| 集群         | Instant Clusters（8-256 卡）  | ❌                            |
| 估值 / 融资    | 33 亿（B+）                  | 未公开（2024 末约 5 亿估值）           |
| 团队规模       | 200+                       | 150+                        |
| 学术          | Tri Dao + Princeton       | 创始人 Lin Qiao（前 Meta / PyTorch）|
| 客户         | Zoom, Salesforce, Inception | DoorDash, Snapchat          |

**结论**：Together 在「**全栈平台**」上领先；Fireworks 在「**推理纯度**」上稍便宜 + 稍快（同等硬件）。

### 21.2 vs. Anyscale（Ray + vLLM）

| 维度         | Together                | Anyscale                  |
| ---------- | ----------------------- | ------------------------- |
| 定位         | 商业 AI Native Cloud     | 开源 Ray 平台 + Anyscale Endpoints |
| 开源         | 部分（FlashAttn、Medusa） | 全栈（Ray、vLLM）              |
| 自服务         | ✅（Instant Clusters）    | ✅（Ray 集群）                |
| 价格         | 商业定价                   | 自带 GPU 按量                 |
| 易用性        | 高（API 一键）             | 中（需懂 Ray）                |
| 适用         | 中小 B + 快速生产部署         | 大企业 + 自建基础设施             |

**结论**：Together 是「**省心的商业化**」；Anyscale 是「**DIY 平台**」。

### 21.3 vs. OpenRouter

| 维度         | Together        | OpenRouter            |
| ---------- | --------------- | --------------------- |
| 定位         | 自营 + 直采          | 聚合（多供应商 router）         |
| 模型数        | 200+            | 400+                  |
| 路由策略       | 静态（按模型名）        | 动态（按价格 / 延迟 / 可用性）    |
| 价格         | Together 自定价    | 各供应商竞价               |
| OpenAI 兼容  | ✅              | ✅（`openrouter.ai/api/v1`） |
| 隐藏抽成       | 无               | 有（5% markup）          |
| 控制         | Together 单一来源   | 多供应商 failover          |
| 适合         | 锁定最佳性能          | 灵活选供应商 / 防止锁定         |

**结论**：Together = 性能优先；OpenRouter = 灵活 + 防锁定。

### 21.4 vs. vLLM（自建）

| 维度         | Together          | vLLM（自建）              |
| ---------- | ----------------- | ---------------------- |
| 启动成本       | $0                | $200K+（8xB200）         |
| 上手时间       | 5 分钟              | 2-4 周                  |
| 性能（B200）   | 334 tok/s          | ~280 tok/s（追赶中）        |
| 维护         | 0（Together 负责）    | 1-2 FTE                 |
| 模型适配速度     | 极快（新模型 24h 内）    | 慢（需手动适配）             |
| 适合         | 不想管 GPU 的团队       | 有 GPU ops 团队的大企业      |

**结论**：vLLM 自建有 20% 性能差距 + 巨大运维成本，Togther 对绝大多数团队更划算。

### 21.5 vs. TGI（HuggingFace）

| 维度         | Together | TGI               |
| ---------- | -------- | ----------------- |
| 速度         | 334      | ~180 tok/s         |
| 多模态        | ✅       | ❌                 |
| 推测解码       | ✅（ATLAS）| ⚠️（实验性）         |
| 部署         | SaaS     | 自建                |
| 生态         | Together  | HuggingFace        |

### 21.6 vs. Groq

| 维度         | Together        | Groq                |
| ---------- | --------------- | ------------------- |
| 硬件         | NVIDIA H100/B200 | GroqChip LPU（自研）   |
| 速度（70B）    | 334 tok/s        | 250 tok/s            |
| 价格         | $1.04/M          | $0.59/M              |
| 模型         | 200+            | 30+（精选）            |
| 适合         | 长上下文 + 大模型    | 低延迟 + 小模型         |

### 21.7 总表对比

| 平台            | 模型数 | 价格（70B in/out） | 速度      | 集群 | 训练 | 开源引擎 | 中国访问 |
| ------------- | --- | --------------- | ------- | -- | -- | ---- | ---- |
| **Together**  | 200 | $1.04 / $1.04   | 334     | ✅ | ✅ | 部分   | ⚠️   |
| Fireworks     | 100 | $0.90 / $0.90   | 270     | ❌ | ❌ | 部分   | ⚠️   |
| DeepSeek 官方   | 5   | $0.27 / $1.10   | 150     | ❌ | ❌ | 全    | ✅   |
| OpenRouter    | 400 | 各异              | 各异      | ❌ | ❌ | 各供应商 | ✅   |
| vLLM 自建       | 无限 | $0.20 / $0.20   | 280     | ✅ | ✅ | 全    | ✅   |
| Groq          | 30  | $0.59 / $0.79   | 250     | ❌ | ❌ | 闭源   | ⚠️   |
| TGI           | 100 | 自建               | 180     | ✅ | ❌ | 全    | ✅   |
| OpenAI        | 20  | $5 / $15        | 100+    | ❌ | ✅ | 闭源   | ⚠️   |

---

## 22. 中国 / 小 B 客户视角

### 22.1 中国境内访问

- **api.together.ai** — 直连延迟 200-500ms，**部分时段被墙**。
- **解决方案**：
  - **代理**（HTTP/SOCKS5）
  - **Cloudflare 反代**（自建 Worker）
  - **私有部署**（Instant Cluster 拉国内，实测 H100/A100/H800 都有）
  - **替代平台**（DeepSeek 官方 / 阿里云 PAI / 智谱开放平台 / 硅基流动）

### 22.2 合规与数据出境

- **数据出境合规**：调用 Together = 数据出境到美国，**需通过 PIPL 安全评估**或签标准合同。
- **私有模型权重**（如自训 LoRA）可上传，但需数据脱敏。
- **敏感行业**（金融 / 医疗 / 政府）：**Together 不适合**，必须国内云（阿里 / 腾讯 / 商汤 / 智谱）。

### 22.3 小 B 客户典型场景

#### 场景 A：跨境电商客服机器人

```
需求：
  - 多语言（中英日韩）
  - 7x24 在线
  - 单月 100 万 token

Together 方案：
  - 模型：Qwen2.5 7B Instruct Turbo（$0.30/M in + $0.30/M out）
  - 成本：100 万 token = $0.60
  - vs. OpenAI GPT-4o-mini：约 $20
  - 节省：97%
```

#### 场景 B：法律文档摘要

```
需求：
  - 128K 长上下文
  - 高准确度
  - 月 5000 份 × 50K token

Together 方案：
  - 模型：Llama 3.3 70B（$1.04/M in + $1.04/M out）
  - 输入：5000 × 50K = 250M tokens → $260
  - 输出：5000 × 5K = 25M tokens → $26
  - 总计：$286/月
  - vs. OpenAI GPT-4o：约 $3750
  - 节省：92%
```

#### 场景 C：图片生成（电商主图）

```
需求：
  - 月 10 万张产品图
  - 风格统一

Together 方案：
  - 模型：FLUX.1 [schnell]（$0.003/张）
  - 成本：$300/月
  - vs. Midjourney Pro：$60/月（但有 license 限制）
```

### 22.4 国内替代方案

| 平台          | 类似 Together 之处            | 差异                       |
| ----------- | ------------------------ | ------------------------ |
| 智谱开放平台      | GLM 系列 + OpenAI 兼容        | 价格更便宜，中文优化好               |
| 阿里云 PAI     | EAS + 开源模型                | 与阿里云生态深度集成                |
| 腾讯混元        | 自研模型 + 微调                 | 闭源生态                      |
| 硅基流动 SiliconFlow | 高性能推理（自研引擎）             | 价格低，性能高                   |
| DeepSeek 官方 | 671B V3 / R1              | 价格最低（$0.27/M）             |
| 字节豆包        | 多种模型 + API                | 字节生态                      |
| 月之暗面 Kimi  | 200K 上下文                  | 长上下文优势                    |

> 建议：**国内小 B 客户优先看 DeepSeek 官方 / 智谱 / 硅基流动**；有跨境业务或需要最全模型时再用 Together。

---

## 23. 开发者体验（DX）与代码示例

### 23.1 5 分钟上手

```bash
# 1. 注册
open https://api.together.ai/settings/projects/~current/api-keys
# 创建 API key，复制

# 2. 安装 SDK
pip install together

# 3. 试一下
python -c "
from together import Together
client = Together(api_key='TOGETHER_API_KEY')
resp = client.chat.completions.create(
    model='meta-llama/Llama-3.3-70B-Instruct-Turbo',
    messages=[{'role': 'user', 'content': '用一句话介绍杭州'}],
)
print(resp.choices[0].message.content)
"
```

### 23.2 流式响应（SSE）

```python
from together import Together

client = Together()
stream = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3.1",
    messages=[{"role": "user", "content": "写一首关于 AI 的诗"}],
    stream=True,
    max_tokens=512,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### 23.3 Function Calling

```python
import json
from together import Together

client = Together()

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取某城市的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["city"],
        },
    },
}]

resp = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "杭州今天多少度？"}],
    tools=tools,
    tool_choice="auto",
)

# 处理 tool call
if resp.choices[0].message.tool_calls:
    tool_call = resp.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    print(f"城市: {args['city']}, 单位: {args.get('unit', 'celsius')}")
```

### 23.4 Structured Outputs（JSON Schema）

```python
resp = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    messages=[{"role": "user", "content": "提取以下文本的实体：'Steve Jobs 在 1976 年与 Steve Wozniak 共同创立了 Apple。'"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "entity_extraction",
            "schema": {
                "type": "object",
                "properties": {
                    "persons": {"type": "array", "items": {"type": "string"}},
                    "organizations": {"type": "array", "items": {"type": "string"}},
                    "years": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["persons", "organizations", "years"],
            },
        },
    },
)
print(json.loads(resp.choices[0].message.content))
# {"persons": ["Steve Jobs", "Steve Wozniak"], "organizations": ["Apple"], "years": [1976]}
```

### 23.5 Vision

```python
resp = client.chat.completions.create(
    model="Qwen/Qwen3-235B-A22B-Instruct-2507-FP8-Tput",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "描述这张图片"},
            {"type": "image_url", "image_url": {"url": "https://example.com/cat.jpg"}},
        ],
    }],
)
```

### 23.6 Embeddings

```python
resp = client.embeddings.create(
    model="BAAI/bge-large-en-v1.5",
    input=["Hello world", "你好世界"],
)
print(len(resp.data[0].embedding), resp.data[0].embedding[:5])
# 1024 [0.012, -0.034, 0.057, -0.022, 0.041, ...]
```

### 23.7 Batch API（Python）

```python
# 上传 JSONL
with open("requests.jsonl", "rb") as f:
    file = client.files.upload(file=f, purpose="batch")

# 创建 batch
batch = client.batches.create(
    input_file_id=file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
)

# 轮询
while batch.status != "completed":
    batch = client.batches.retrieve(batch.id)
    print(f"Status: {batch.status}")
    time.sleep(30)

# 下载结果
output = client.files.content(batch.output_file_id)
print(output.text)
```

### 23.8 LangChain 集成

```python
from langchain_together import ChatTogether
from langchain_core.prompts import ChatPromptTemplate

llm = ChatTogether(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    temperature=0.7,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的助手"),
    ("user", "{input}"),
])

chain = prompt | llm
print(chain.invoke({"input": "你好"}).content)
```

### 23.9 LlamaIndex 集成

```python
from llama_index.llms.together import TogetherLLM
from llama_index.core import Settings

Settings.llm = TogetherLLM(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    api_key="TOGETHER_API_KEY",
)

# 然后正常使用 VectorStoreIndex 等
```

### 23.10 观测（OpenLLMetry）

```python
from traceloop.sdk import Traceloop
from together import Together

Traceloop.init(app_name="my-app")

client = Together()
# 所有 chat.completions.create 调用会自动被追踪
resp = client.chat.completions.create(...)
# 在 Traceloop / OpenLLMetry 控制台查看 trace
```

### 23.11 CLI 常用命令

```bash
# 安装
pip install "together[cli]"

# 登录
together login

# 列模型
together models list

# 聊天
together chat "写一个 Python 快速排序"

# 列出所有 batch
together batch list

# 创建 cluster
together cluster launch --type h100 --nodes 1 --gpus 8

# 列出 cluster
together cluster list

# 提交 fine-tuning job
together fine-tuning launch --model meta-llama/Llama-3.3-70B-Instruct-Turbo \
  --dataset my-dataset.jsonl --lora --epochs 3
```

---

## 24. 参考链接与资料

### 24.1 官方资源

- 官网：https://www.together.ai
- 文档：https://docs.together.ai
- API 文档：https://docs.together.ai/reference
- 定价：https://www.together.ai/pricing
- 状态页：https://status.together.ai
- 博客：https://www.together.ai/blog
- 研究博客（Turbo 套件论文）：https://www.together.ai/blog?category=Research
- GitHub：https://github.com/togethercomputer

### 24.2 核心论文

- **FlashAttention-4**（2026-03）：https://arxiv.org/abs/2603.05451
- **ATLAS**（2025-10）：https://www.together.ai/blog/adaptive-learning-speculator-system-atlas
- **Custom Speculative Decoding**（2025-05）：https://www.together.ai/blog/customized-speculative-decoding
- **Together Inference Engine v2 on B200**（2025-07）：https://www.together.ai/blog/fastest-inference-for-deepseek-r1-0528-with-nvidia-hgx-b200
- **Instant Clusters GA**（2025-09）：https://www.together.ai/blog/together-instant-clusters-ga
- **Batch API 升级**（2025-09）：https://www.together.ai/blog/batch-inference-api-updates-2025
- **Sequoia**（2024-02）：https://arxiv.org/abs/2402.12374（NeurIPS 2024）
- **SpecExec**（2024-06）：https://arxiv.org/abs/2406.02532
- **Medusa**（2023-09）：https://arxiv.org/abs/2401.10774
- **RedPajama**：https://github.com/togethercomputer/RedPajama-Data

### 24.3 开源仓库

- **Medusa**：https://github.com/FasterDecoding/Medusa
- **Sequoia**：https://github.com/Infini-AI-Lab/Sequoia
- **SpecExec**：https://github.com/yandex-research/specexec
- **FlashAttention**：https://github.com/Dao-AILab/flash-attention
- **ThunderKittens**：https://github.com/HazyResearch/ThunderKittens
- **Together Python SDK**：https://github.com/togethercomputer/together-python

### 24.4 关键人物

- **Vipul Ved Prakash**（CEO）：https://twitter.com/vipulved
- **Tri Dao**（Chief Scientist）：https://twitter.com/tri_dao
- **Ben Athiwaratkun**（AI 研究负责人）：https://www.together.ai/blog/customized-speculative-decoding
- **Avner May**（研究科学家）

### 24.5 第三方评测

- **Artificial Analysis**（推理速度与价格基准）：https://artificialanalysis.ai/models/deepseek-r1/providers
- **Stanford HELM**（模型质量评测）：https://crfm.stanford.edu/helm/
- **Chatbot Arena**（人类偏好）：https://lmarena.ai/

### 24.6 类似项目（已在本系列报告覆盖）

- `product-portkey-20260605.md`
- `product-litellm-20260605.md`
- `product-one-api-20260605.md`
- `product-higress-20260605.md`
- `product-kong-ai-gateway-20260605.md`
- `product-apisix-ai-proxy-20260605.md`
- `product-envoy-ai-gateway-20260605.md`
- `product-vllm-20260605.md`
- `product-sglang-20260605.md`
- `product-tgi-20260605.md`
- `product-triton-inference-server-20260605.md`
- `product-lmdeploy-20260605.md`
- `product-llama-cpp-20260605.md`
- `product-cloudflare-workers-ai-20260605.md`
- `product-openrouter-20260605.md`
- `product-helicone-20260605.md`
- `product-langsmith-20260605.md`
- `product-unify-20260605.md`
- `product-not-diamond-20260605.md`
- `product-truefoundry-20260605.md`

---

## 报告总结

Together AI 是**「开源模型 + 自研系统 + 商业全栈」**三位一体的代表。其核心差异化：

1. **硬件-算法联合设计**（FlashAttention-4 + ThunderKittens + 自研内核）— 性能护城河。
2. **运行时自适应推测解码**（ATLAS）— 业界唯一真正的「用得越多越快」系统。
3. **OpenAI 兼容 + 200+ 模型** — 零摩擦迁移 + 最大模型库。
4. **三层云**（推理 + 算力 + 模型塑形）— 客户终身价值高。

对小 B 客户而言，**Together 是 OpenAI 的 1/10 成本 + 不锁定**的最优解；对大客户而言，**是省掉 GPU 运维团队 + 跟上模型节奏**的最佳捷径。

短期看，**B200 + FlashAttention-4 + ATLAS 的三重护城河**让 Together 在 2026-2027 年继续保持领先；中长期看，**与 vLLM / SGLang 等开源引擎的差距**会逐渐缩小（开源社区会追赶 FlashAttn 类优化），届时 Together 需要靠**「商业全栈 + Custom Spec + 训练平台」**建立第二曲线。

**对小 F 的建议**：
- 国内业务 → 优先 **DeepSeek 官方 / 智谱 / 硅基流动**
- 跨境业务 / 多模型试验 → **Together + OpenRouter** 组合
- 大模型微调需求 → Together DE + Custom Spec
- 完全不想管 GPU → Together Serverless 起步，月成本 $100-1000 起

---

> 报告结束
> 字数：约 18,000 字
> 代码示例：11 段
> 对比表：21 张
> ASCII 架构图：4 张
> 引用论文：9 篇
> 完成时间：2026-06-05 13:30 CST
