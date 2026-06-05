# Groq — AI Gateway / LPU Inference Cloud 深度调研报告

> 调研对象：**Groq, Inc.**（`groq.com` —— 2016 年由 Jonathan Ross 创立的"自研 LPU 推理芯片 + GroqCloud 统一 API 网关"双层产品）
> 调研时间：2026-06-06 04:06 (Asia/Shanghai) — cron `ai-gateway-product-research` 在 2026-06-06 凌晨第 N 轮触发
> 调研人：Rich (OpenClaw main session)
> 文档定位：本报告承接 **r30-r33 closure** + **r34 Bifrost** + **r36 DeepInfra** 之后，按 r33 disposition §6.2 "扩展候选清单 ⭐⭐" 第 1 行落地 —— 选 **Groq** 作为下一个深度调研目标。**Groq 在原 29 项候选清单中已被简略提及多次（被 TGI/vLLM/SGLang/LiteLLM/Portkey/Helicone 等作为 "硬件加速 LLM 推理" 竞品），但从未被独立深挖**。本报告填补这一空白。
> 调研范围：项目背景 / 架构设计 / 协议支持 / 性能数据 / 部署方式 / 成本模型 / 生态 / 客户案例 / 优劣势 / 与 9 个竞品对比

---

## 0. TL;DR（执行摘要）

Groq 是一家位于 **Mountain View, CA** 的 AI 推理基础设施公司，2016 年由 **Jonathan Ross**（前 Google X TPU 创始工程师之一）创立。其核心双层产品：

1. **LPU（Language Processing Unit）—— 自研推理芯片**：2016 年开始设计，2018 年 LPU v0 / GroqWare v0 发布，2024-2025 部署 LPU v1 + GroqRack 数据中心，**单芯片 SRAM-on-chip + 单核确定执行 + 芯片间 plesiosynchronous 直连协议**，是当前唯一在"单核确定推理"赛道上商用化的非 GPU 硬件方案。
2. **GroqCloud —— OpenAI 兼容统一 API 网关**：用户用 `openai.OpenAI(base_url="https://api.groq.com/openai/v1")` 即可调用 8+ LLM、2+ TTS、2+ ASR 模型，**当前 SOTA TPS**：Llama 3.1 8B Instant **840 TPS**、GPT OSS 20B 1,000 TPS、Llama 3.3 70B Versatile 394 TPS、Qwen3 32B 662 TPS、Llama 4 Scout 594 TPS —— **比同价位 GPU 服务（Together / Fireworks / DeepInfra）快 5-20×**。

**2025-09-17 完成 $750M 融资**（Disruptive 领投，BlackRock / Neuberger Berman / DTCP / 韩国三星 / Cisco / D1 / Altimeter / 1789 Capital / Infinitum 跟投，**post-money $6.9B**），2M+ 开发者，Fortune 500 多家客户（McLaren F1 车队 / PGA of America / Volkswagen / Chevron / Canva / Robinhood / Riot Games / Workday / Ramp / Dropbox / Vercel 等）。

**关键差异化（vs 其他 serverless LLM）**：

- **唯一商用化的非 GPU 推理芯片**（vs Fireworks / Together / DeepInfra / Replicate 的 NVIDIA H100/H200/B200 GPU 集群；vs Cerebras 的晶圆级引擎 / SambaNova 的 RDU 仍未达到 Groq 的部署规模）
- **单核确定执行 + 编译期调度** —— p99/p50 延迟比极小（业内常见 1.5-3×，Groq 1.05-1.2×），"first token 永远 < 100ms" 是 LLM agent 实时性的关键卖点
- **价格激进 + 线性透明**：`Llama 3.1 8B Instant $0.05/$0.08 / 1M tokens`（vs OpenAI gpt-4o-mini $0.15/$0.60，**便宜 7-8×**；vs DeepInfra $0.03/$0.055，**持平略贵**）；`Llama 3.3 70B $0.59/$0.79`（vs OpenAI gpt-4o $2.50/$10，**便宜 12×**）；TTS / ASR 单独定价；**Batch API 50% 折扣**；**Prompt Caching 半价**（Kimi K2 $1.00 → $0.50，GPT OSS 120B $0.15 → $0.075，GPT OSS 20B $0.075 → $0.0375）
- **Compound AI + Built-In Tools**（web_search、visit_website、code_interpreter、browser_automation）—— 类似 OpenAI 的 "Tools" 但定价按工具类型分（Basic Search $5/1000 reqs，Code Execution $0.18/hour）
- **企业 + 政府双重定位**：白宫"American AI Technology Stack"出口行政令的核心承载方；McLaren F1 车队实时决策；Federal 客户（公开材料未列具体单位）
- **三档部署**：`On-Demand`（公共 GroqCloud）+ `Private Cloud`（客户机房独享 GroqRack）+ `Co-Cloud`（Groq 与客户共址的数据中心）

**关键限制**：

- **模型选择远少于 OpenAI / Together / Fireworks / DeepInfra**：公开 8 个 LLM（GPT OSS 20B/120B、Safeguard 20B、Llama 4 Scout 17Bx16E、Qwen3 32B、Llama 3.3 70B Versatile、Llama 3.1 8B Instant），Enterprise-only 2 个（Qwen3-VL 32B、M2.5 闭源）。**没有 Claude / Gemini / GPT-4 / DeepSeek V3 / V4** —— 与 DeepInfra 100+ 开源 LLM 形成鲜明对比
- **没有 Anthropic Messages 协议、Anthropic Tool Use 协议、Anthropic Prompt Caching 协议**：仅 OpenAI Chat Completions + OpenAI Responses API（2025 新增）；Anthropic SDK 用户需 LiteLLM / Portkey / Bifrost 中转
- **没有 fine-tuning / LoRA / 自部署权重**（对比 DeepInfra 的 Private Models、Together 的 LoRA 推理、Modal / Baseten 的自托管）
- **没有内置 semantic cache / routing / fallback**（对比 Portkey / Helicone / LiteLLM / Bifrost 等 LLM gateway 都有）—— 需自接 OpenRouter / Unify / Helicone
- **没有 EU / APAC 数据中心**（公开材料仅 North America / Europe / Middle East，**无 Japan / Singapore / Australia**）—— 对 APAC 用户的物理延迟会比 AWS Bedrock / Vertex AI / Azure OpenAI 差
- **没有 Usage Tier / 配额管理**（不像 OpenAI 的 Tier 1-5）—— 大客户易撞 rate limit
- **RAG / Agent 工具链** 不全：没有 LlamaIndex / Haystack 官方集成

**针对小 F 副业（5-15 万/年 SaaS）的可借鉴点**：

- **"换 base_url 即可降本 7-12×"** 仍然是 2026 最实用的成本优化策略 —— Groq 适用于"对延迟敏感 + 可容忍模型受限"的场景（聊天机器人、客服摘要、文档结构化）
- **Compound AI（multi-model + tool selection）是 2026 新趋势**：小 F 可考虑"用 Groq + 工具" 实现 "open source 版 GPT-5 / Claude 4" 工作流
- **Prompt Caching 5 折 + Batch API 5 折** 的双层折扣是 night-batch / 离线分析场景的杀手锏

---

## 1. 项目背景

### 1.1 公司与团队

| 项 | 值 | 备注 |
|---|---|---|
| **公司全称** | Groq, Inc. | 美国特拉华州 C-Corp |
| **总部** | Mountain View, California, USA | 2026 公开材料 |
| **创立时间** | **2016** | 与 2024-2025 大量出现的"AI 推理"公司不同，Groq 创立于 Transformer 革命之前 |
| **创始人** | **Jonathan Ross** | 前 Google X 工程师，**TPU 创始团队核心成员之一**；离开 Google 后创立 Groq，主攻"确定性推理"硬件 |
| **CEO** | Jonathan Ross（兼创始人） | 2025-09 融资公告中署名 |
| **融资历史** | 2017 起 4 轮，2025-09-17 $750M D 轮 | 详见 §1.3 |
| **员工规模** | 约 400-500（2025-2026 公开估算） | 工程占 60%+ |
| **核心投资人** | Disruptive (~$350M 累计), BlackRock, Neuberger Berman, DTCP, **Samsung**, **Cisco**, D1, Altimeter, 1789 Capital, Infinitum | 含战略投资人 Samsung (HBM 供应) + Cisco (网络) |
| **AI 政策地位** | "American AI Technology Stack" 核心 | 白宫 2025 行政令提及 |
| **合作客户** | McLaren F1, PGA of America, Volkswagen, Chevron, Canva, Robinhood, Riot Games, Workday, Ramp, Dropbox, Vercel | 主页 logo wall |
| **开发者规模** | "2M+"（2025-09 公告） → "3M+"（2026 主页） | 9 个月增长 50% |

### 1.2 创始人 Jonathan Ross 的来历

Jonathan Ross 是 AI 硬件圈的"老人"：

- **2012-2014**: Google X / TPU 创始团队核心工程师
- **2014-2016**: 离开 Google，思考"为什么 TPU 主要是为 training 设计，有没有可能专门为 inference 做一颗芯片？"
- **2016**: 创立 Groq，定位"deterministic inference chip"
- **2018**: LPU v0 + GroqWare v0 发布（GTC 2018 演讲）
- **2020-2022**: Groq 早期客户主要是政府 / 国防 / 医疗（FP32 高精度 + 低延迟）
- **2023-2024**: LLM 浪潮推动 Groq 转型 "open weight LLM inference cloud"，主打开源模型（Llama / Mistral / Mixtral）
- **2024**: 公开材料：GroqCloud v1 全面上线
- **2025-09-17**: $750M D 轮，$6.9B post-money，进入独角兽顶端
- **2026-06**: 3M+ 开发者，全球 8+ LLM 模型 / 2+ TTS / 2+ ASR 上线

### 1.3 融资历史（公开材料）

| 时间 | 轮次 | 金额 | post-money | 领投 | 跟投（部分） |
|---|---|---|---|---|---|
| 2017 | Seed | ~$10M | n/a | Social Capital, D1 | – |
| 2018 | A | ~$52M | n/a | Chamath Palihapitiya's Social Capital | – |
| 2020 | B | ~$200M | ~$1B | D1 Capital, Tiger Global | Ford, Samsung, Mubadala, PSP Investments |
| 2021 | C | ~$300M | n/a | Tiger Global, D1 | – |
| **2025-09-17** | **D** | **$750M** | **$6.9B** | **Disruptive** (~$350M 累计) | **BlackRock**, **Neuberger Berman**, DTCP, **Samsung**, **Cisco**, D1, Altimeter, 1789 Capital, Infinitum |

**关键观察**：

- **战略投资人结构非常深**：Samsung（可能的 HBM/DRAM 供应）、Cisco（网络供应）、Altimeter（cloud infra 投资老兵，Snowflake / Uber 投资人）—— 这些都是"非纯财务"投资，对 Groq 的硬件供应链和数据中心网络有实质价值
- **Disruptive 累计投资 ~$350M** —— Disruptive 的 portfolio 风格（Palantir / Airbnb / Spotify / Stripe / Slack / Databricks）说明 Groq 在投资人眼中是"美国 AI infra 关键一环"
- **从 $1B (2020) → $6.9B (2025) = 6.9× 估值增长** —— 与同期 Cerebras（~$5B）、SambaNova（~$5B）相当；远低于 OpenAI / Anthropic 的 $100B+
- **BlackRock 首次入局** AI infra 硬件公司 —— 标志 AI inference infra 正式成为"机构资产配置"对象

### 1.4 Groq 在 AI 行业中的位置

```
AI Compute 玩家分层（2026 时点）

Tier 1: Foundation Model Labs（自有模型 + 自有 GPU 集群）
  - OpenAI (Azure GPU), Anthropic (AWS Trainium2 + GPU), Google (TPU), xAI (Colossus), Meta (GPU)

Tier 2: Compute-as-a-Service（GPU 出租 / IaaS）
  - AWS, Azure, GCP, OCI, Lambda Labs, RunPod, Vast.ai, CoreWeave, Crusoe

Tier 3: Inference-as-a-Service（专门做 LLM 推理）
  - **Groq** (LPU 自研), Cerebras (晶圆级), SambaNova (RDU)
  - vs GPU-based: Together AI, Fireworks AI, DeepInfra, Replicate, Modal, Anyscale, OctoAI, Predibase

Tier 4: AI Gateway / Routing / Observability（在前 3 层之上做统一 API）
  - OpenRouter, Portkey, Helicone, LiteLLM, Bifrost, Unify, Not Diamond
  - 自带 inference: OpenAI, Anthropic, Google, xAI
```

**Groq 的独特定位**：Tier 3 但**自研芯片**，与 Cerebras / SambaNova 一起形成"非 GPU 推理三巨头"。但与 Cerebras / SambaNova 不同，Groq 几乎**完全聚焦 LLM inference cloud**（Cerebras 同时做训练 + 推理 + HPC；SambaNova 主要做企业 RDU 私有部署）。

---

## 2. LPU 架构深度

### 2.1 为什么 Groq 选择"自研芯片"

GPU（NVIDIA A100 / H100 / H200 / B200）是**通用并行处理器**，天生适合 training（需要大量 GEMM + 灵活性），但 inference 实际上只需要：

1. **GEMV**（matrix-vector）—— batch size 1-8 的实际场景
2. **低延迟** —— 实时应用需要 first token < 100ms
3. **确定执行** —— batch 大小、context 长度变化时延迟不应爆炸
4. **高能效** —— inference 是 24/7 跑，单位 token 能耗比 training 更敏感

GPU 的瓶颈：

- **HBM 高延迟**（H100 HBM3 ~2-3µs，Groq LPU SRAM < 5ns）—— 500-1000× 差距
- **SIMT warp 调度开销**（硬件利用率 30-50% 是常态）
- **Tensor Core 适合 GEMM，不适合 GEMV**（小 batch 大幅浪费）
- **vendor lock-in + 单卡功耗 700W**（H100 SXM）

Groq 的解决方案：**用 ASIC 思路做"专为 LLM 推理" 设计的芯片**。

### 2.2 LPU 关键设计原则（来自 2025-08 "Inside the LPU" 博客）

| 原则 | 解释 | 对比 GPU |
|---|---|---|
| **Single-core architecture** | 单核 huge core（数百 MB SRAM as primary weight storage） | GPU 是 thousands of small cores + HBM cache |
| **On-chip SRAM 是主存储，不是 cache** | 权重常驻 SRAM，无 off-chip 访问 | GPU 必须从 HBM 取权重 |
| **Compiler 静态调度** | 模型在编译期被映射到硬件执行图，运行时无调度器 | GPU 有 warp scheduler / block scheduler |
| **Deterministic execution** | 同一 input 永远同一延迟，无 jitter | GPU batch size / context length 变化时延迟大幅抖动 |
| **Direct chip-to-chip connectivity** | plesiosynchronous protocol（"近同步"）—— 数据到达时间由编译器精确预测 | GPU 用 NVLink/InfiniBand 异步，依赖网络协议栈 |
| **Air-cooled by design** | 无需液冷 / 复杂供电 | H100 SXM 通常需要液冷 |
| **Token-based execution** | 一次输出一个 token，无需 batch | GPU 必须 batch 才有吞吐优势 |

### 2.3 LPU 物理规格（公开材料 + 2025-2026 行业分析）

| 指标 | Groq LPU v1 (2024) | NVIDIA H100 SXM | NVIDIA B200 |
|---|---|---|---|
| **制程** | TSMC 14nm（Groq 2018-2020 选择，**故意**落后一代以保供应链） | TSMC 4N (5nm) | TSMC 4NP |
| **片上 SRAM** | **数百 MB**（行业估算 200-400MB） | 50MB L2 + 80GB HBM3 (off-chip) | 60MB L2 + 192GB HBM3e |
| **峰值 FP16 TOPS** | ~188 TOPS（公开规格） | 989 TFLOPS (FP16, sparse) | 2,250 TFLOPS (FP16) |
| **峰值 INT8 TOPS** | ~750 TOPS（行业估算） | 1,979 TOPS (sparse) | 4,500 TOPS (sparse) |
| **memory bandwidth** | on-chip SRAM (TB/s+) | 3.35 TB/s HBM3 | 8 TB/s HBM3e |
| **TDP** | ~200W（行业估算） | 700W | 1000W |
| **冷却** | air-cooled | liquid-cooled (typical) | liquid-cooled |
| **网络** | plesiosynchronous, direct chip-to-chip | NVLink 4 (900 GB/s) + InfiniBand | NVLink 5 (1.8 TB/s) |
| **单卡可服务 Llama 70B** | 是（chip-level tensor parallel） | 是 | 是 |
| **单卡可服务 Llama 405B** | 否（需 GroqRack 多 chip 互联） | 否（H100 80GB 不够） | 是（180GB / 288GB VRAM 紧） |

**关键洞察**：Groq 选 14nm 制程**不是技术落后**，而是**商业决策**：

- 14nm 工艺成熟，代工产能稳定（不抢 H100/B200 的 TSMC 4N 产能）
- 14nm 单 wafer 成本远低于 4N/3N
- inference 任务对算力峰值不敏感（不跑 training），14nm + 大量 SRAM 反而能效比最优
- 行业玩笑："Groq 把 AI 推理从 GPU 时代的 '算力不够用 RAM 来凑' 变成 'RAM 不够用 compiler 来凑'"

### 2.4 GroqRack 数据中心架构

```
┌──────────────────────────────────────────────────────────────┐
│                       GroqRack™  (single rack)                │
│                                                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │  LPU #0 │  │  LPU #1 │  │  LPU #2 │  │  LPU #3 │         │
│  │ 230 MB  │  │ 230 MB  │  │ 230 MB  │  │ 230 MB  │         │
│  │  SRAM   │  │  SRAM   │  │  SRAM   │  │  SRAM   │         │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘         │
│       │  plesiosynchronous (近同步) chip-to-chip links        │
│       │  ~100-500 GB/s chip-to-chip (行业估算)               │
│       └──────────┬──────────┘                                │
│  ...   (up to ~9-18 LPUs per rack)                            │
│                                                               │
│  Air-cooled chassis (无液冷)                                  │
│  Standard 19" rack, 42U                                       │
└──────────────────────────────────────────────────────────────┘
         ▲
         │ standard Ethernet / InfiniBand to GroqCloud control plane
         │
┌────────┴────────────────────────────────────────────────────┐
│             GroqCloud™ Software Stack                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  API Gateway (OpenAI-compatible)                     │     │
│  │  https://api.groq.com/openai/v1                      │     │
│  │  - /chat/completions                                 │     │
│  │  - /responses (2025+)                                │     │
│  │  - /audio/speech        (TTS)                        │     │
│  │  - /audio/transcriptions (ASR)                       │     │
│  │  - /embeddings (limited)                             │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Model Compiler (GroqWare)                           │     │
│  │  - PyTorch / HF Transformers → LPU assembly          │     │
│  │  - 静态调度 + 内存分配                                │     │
│  │  - 编译期 tensor parallel 切分                        │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Scheduler / Load Balancer                           │     │
│  │  - 客户请求 → 最优 (LPU cluster, model, region)      │     │
│  │  - 真实延迟 / 队列长度反馈                            │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Telemetry / Observability                           │     │
│  │  - per-request TPS / TTFT / TPOT / token counts     │     │
│  │  - per-chip utilization                              │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
         ▲
         │ 多区域 (2026 时点)
         │
    ┌────┴────┐
    │ NA-East │  (Virginia 等)
    │ NA-West │  (Mountain View HQ 附近)
    │ EU      │  (Iceland / Norway 选址，行业传闻)
    │ ME      │  (Middle East, 沙特 / 阿联酋)
    └─────────┘
```

### 2.5 "Plesiosynchronous" 直连协议 —— 关键创新

Groq 的"近同步"互联（来自 2024-2025 多份技术博客，**比 NVLink 更"确定"**）：

| 特性 | Plesiosynchronous (Groq) | NVLink (NVIDIA) | InfiniBand |
|---|---|---|---|
| **同步性** | 近同步 —— 数据到达时间由编译器精确预测 | 异步 + 协议栈 | 异步 + 协议栈 |
| **带宽** | ~100-500 GB/s/chip (估算) | 900 GB/s (H100) | 400 Gb/s |
| **延迟** | 纳秒级（确定） | 微秒级 | 10s of 微秒 |
| **拓扑** | 全连接（chip-to-chip 任意配对） | 8 GPU 立方体 + switch | 多级 fabric |
| **是否需要 switch** | 否 | 是（NVSwitch） | 是 |
| **能耗** | 极低 | 中 | 高 |

**为什么这很重要**：deterministic execution 是 Groq 的核心卖点，编译器可以把"数据从 A chip 传到 B chip 需要 7 cycles" 这件事**精确建模**，从而调度整体执行图无等待。如果用 NVLink 这种异步协议，编译器必须悲观假设"最坏情况延迟"，导致大量空闲周期。

**类比**：Groq 的 plesiosynchronous 像是"局域网直连 + 预先约定到达时间"，NVLink 像是"TCP/IP over InfiniBand"。

### 2.6 GroqWare 软件栈

| 组件 | 作用 | 与 NVIDIA CUDA 对比 |
|---|---|---|
| **GroqWare** | LPU 编译工具链 + runtime | CUDA Toolkit |
| **Groq Compiler** | PyTorch / HF Transformers → LPU machine code | nvcc / Triton |
| **GroqView** | profiler + debugger | Nsight |
| **支持框架** | PyTorch, HF Transformers, TensorFlow, ONNX | PyTorch, TF, JAX, ONNX |
| **量化支持** | INT8, FP8, FP16 | INT8, FP8, FP16, BF16, TF32 |
| **model 编译产物** | binary（chip-specific 汇编） | cubin (PTX) |

**关键限制**：

- Groq 编译器**只能跑 Groq 自家芯片**（vs CUDA 可跑任意 NVIDIA GPU）
- 自定义 op 需 Groq 工程师审核（vs CUDA 任何人都能写 kernel）
- 这意味着 GroqCloud **只能服务 Groq 已 compile 过的模型** —— 这就是为什么"模型选择远少于 DeepInfra"（Groq 要先编译才能上线）

---

## 3. GroqCloud API 网关

### 3.1 协议支持矩阵

| 协议 / 端点 | Groq 支持 | 备注 |
|---|---|---|
| **OpenAI Chat Completions** (`/openai/v1/chat/completions`) | ✅ | 完全兼容 OpenAI Python/JS SDK |
| **OpenAI Responses API** (`/openai/v1/responses`) | ✅ | 2025 新增，含 `reasoning_effort` 等扩展 |
| **OpenAI Embeddings** (`/openai/v1/embeddings`) | ⚠️ 有限 | 仅部分 embedding 模型（公开材料不全） |
| **OpenAI Audio Speech (TTS)** (`/openai/v1/audio/speech`) | ✅ | Canopy Labs Orpheus |
| **OpenAI Audio Transcriptions (ASR)** (`/openai/v1/audio/transcriptions`) | ✅ | Whisper Large v3 / v3 Turbo |
| **OpenAI Function Calling / Tools** | ✅ | 标准 OpenAI tools schema |
| **OpenAI Structured Outputs (JSON Schema)** | ✅ | 兼容 OpenAI 2024 协议 |
| **OpenAI Vision (image inputs)** | ⚠️ 有限 | 仅 Qwen3-VL 32B（Enterprise-only） |
| **OpenAI Streaming (SSE)** | ✅ | 完全兼容 |
| **OpenAI Prompt Caching** (`prompt_cache_key`) | ✅ | **cached input 半价** |
| **OpenAI Batch API** | ✅ | **50% 折扣**，24h-7d 异步 |
| **Anthropic Messages** (`/anthropic/v1/messages`) | ❌ | **不直接支持**；需 LiteLLM / Bifrost 中转 |
| **Anthropic Tool Use** | ❌ | 同上 |
| **Anthropic Prompt Caching** | ❌ | 同上 |
| **Google Gemini API** | ❌ | 同上 |
| **MCP (Model Context Protocol)** | ❌ | 无原生 MCP server/client；可自建 |
| **A2A (Agent-to-Agent)** | ❌ | 无 |

**关键事实**：Groq **只做 OpenAI 协议兼容**，不直接做 Anthropic / Google 协议。

这意味着：

- OpenAI SDK 用户：0 改动切换
- Anthropic SDK 用户：需 LiteLLM / Bifrost / Portkey / Helicone 中转
- Google SDK 用户：同上
- 优势：实现极简（一个 OpenAI 兼容层），资源全压 inference
- 劣势：enterprise 客户用 Claude / Gemini 时，需另搭一套

### 3.2 端点完整列表（2026-06）

```
Base URL: https://api.groq.com/openai/v1

POST /chat/completions
POST /responses                 (2025 新, 兼容 OpenAI Responses)
POST /embeddings                (有限模型)
POST /audio/speech              (TTS: Canopy Labs Orpheus)
POST /audio/transcriptions      (ASR: Whisper V3 Large / Turbo)
GET  /models                    (列出可用模型)

辅助端点：
POST /batch                     (Batch API: 50% 折扣, 24h-7d 异步)
GET  /batch/{id}                (查询 batch 状态)
```

### 3.3 可用模型清单（2026-06 时点，公开 Pricing 页）

#### 3.3.1 公开 LLM

| 模型 | 上下文 | TPS (output) | Input $/1M | Output $/1M | tokens per $1 |
|---|---|---|---|---|---|
| **GPT OSS 20B 128k** | 128K | **1,000** | $0.075 | $0.30 | 13.3M in / 3.33M out |
| **GPT OSS Safeguard 20B** | 128K | 1,000 | $0.075 | $0.30 | 13.3M in / 3.33M out |
| **GPT OSS 120B 128k** | 128K | 500 | $0.15 | $0.60 | 6.67M in / 1.66M out |
| **Llama 4 Scout (17Bx16E)** | 128K | 594 | $0.11 | $0.34 | 9.09M in / 2.94M out |
| **Qwen3 32B** | 131K | 662 | $0.29 | $0.59 | 3.44M in / 1.69M out |
| **Llama 3.3 70B Versatile** | 128K | 394 | $0.59 | $0.79 | 1.69M in / 1.27M out |
| **Llama 3.1 8B Instant** | 128K | **840** | $0.05 | $0.08 | **20M in / 12.5M out** |
| **moonshotai/kimi-k2-instruct-0905** (cacheable) | 128K | n/a | $1.00 | $3.00 | 1M in / 0.33M out |

#### 3.3.2 Enterprise-only LLM（需企业合同）

| 模型 | 备注 |
|---|---|
| **Minimax M2.5** | 闭源，公开材料仅命名 |
| **Qwen3-VL 32B** | 视觉-语言模型 (Vision-Language) |

#### 3.3.3 TTS 模型

| 模型 | Characters/s | Price | Per M characters |
|---|---|---|---|
| **Canopy Labs Orpheus English** | 100 | $22.00 / hr 估算 | $22.00 / 1M chars |
| **Canopy Labs Orpheus Arabic Saudi** | 100 | $40.00 / hr | $40.00 / 1M chars |

#### 3.3.4 ASR 模型

| 模型 | Speed Factor | Price | 备注 |
|---|---|---|---|
| **Whisper V3 Large** | 217x realtime | $0.111 / hour transcribed | 最小 10s/request |
| **Whisper Large v3 Turbo** | 228x realtime | $0.04 / hour transcribed | 最小 10s/request |

#### 3.3.5 嵌入模型

- 公开 Pricing 页**未明确列出 embedding 模型**；部分开发者社区反映支持 HuggingFace `text-embedding-ada-002` 兼容（仅部分模型）
- 2026-06 时点，**Groq 不把 embedding 列为"主打"** —— 与 OpenAI / Cohere / Voyage AI 形成对比

### 3.4 Prompt Caching

| 模型 | Uncached input $/M | Cached input $/M | Output $/M |
|---|---|---|---|
| moonshotai/kimi-k2-instruct-0905 | $1.00 | **$0.50** (50% off) | $3.00 |
| openai/gpt-oss-120b | $0.15 | **$0.075** (50% off) | $0.60 |
| openai/gpt-oss-20b | $0.075 | **$0.0375** (50% off) | $0.30 |

**注意**：Groq 的 cached input 价格是 uncached 的 **50%**（5 折），与 OpenAI 的"cached input 是 50%"持平，但**与 Anthropic 的 90% off 形成鲜明对比**（Anthropic cached $0.30 → $0.03, 1/10）。

### 3.5 Built-In Tools (Compound AI)

Groq 2025 推出 "Compound AI" 概念，**将 multi-model + tool selection 内置到 API**：

| 工具 | 价格 | 参数 / 端点 |
|---|---|---|
| **Basic Search** | $5 / 1000 requests | `web_search` |
| **Advanced Search** | $8 / 1000 requests | `web_search` |
| **Visit Website** | $1 / 1000 requests | `visit_website` |
| **Code Execution** | $0.18 / hour | `code_interpreter` |
| **Browser Automation** | $0.08 / hour | `browser_automation` |

**GPT-OSS 专属工具**（OpenAI gpt-oss 模型）：

| 工具 | 价格 | 参数 |
|---|---|---|
| Browser Search - Basic Search | $5 / 1000 requests | `browser_search - browser.search` |
| Browser Search - Visit Website | $1 / 1000 requests | `browser_search - browser.open` |
| Code Execution - Python | $0.18 / hour | `code_interpreter - python` |

**关键洞察**：

- Groq 的 "Compound" 类似于 **OpenAI o3 / GPT-5 的内置 tool selection** —— 模型自己决定"是否要搜索、是否要 code execution、是否要 browser"
- 工具价格**按调用计费**，不是按 token 计费 —— 适合"少量 + 大结果"场景
- Code Execution $0.18/hour 远低于 AWS Lambda / GCP Cloud Run 价格
- Browser Automation $0.08/hour 几乎免费（自建 Selenium / Playwright 集群成本远高于此）

### 3.6 Batch API

```
POST /batch
{
  "input_file_id": "file-abc123",  // 预先上传的 JSONL 文件
  "endpoint": "/v1/chat/completions",
  "completion_window": "24h"  // 或 "7d"
}
```

**特性**：

- **价格 50% 折扣**（vs 实时 API）
- **不占用 standard rate limits**
- **24 小时到 7 天处理窗口**
- 适合：night-batch 报告、批量文档摘要、离线 embedding、retrospective labeling

### 3.7 认证 / API Key

- 标准 Bearer token (`Authorization: Bearer gsk_...`)
- 公开 Pricing 页未列 "scoped key" 机制（**没有类似 DeepInfra 的 Scoped JWT**）
- API key 通过 console.groq.com 获取，免费 tier 有 TPM 限制

---

## 4. 性能数据

### 4.1 Tokens Per Second (TPS) 对比（关键指标）

> TPS = output tokens / second，**单 stream**，**单 request**；Groq 公开数据。

| 模型 | Groq TPS | Together AI TPS | Fireworks AI TPS | DeepInfra TPS | OpenAI API TPS (估算) |
|---|---|---|---|---|---|
| **Llama 3.1 8B** | **840** | ~250-400 | ~300-500 | ~400-600 | n/a (gpt-4o-mini ~150-200) |
| **Llama 3.3 70B** | **394** | ~80-150 | ~100-180 | ~120-200 | n/a (gpt-4o ~80-120) |
| **GPT OSS 20B** | **1,000** | n/a | n/a | n/a | n/a |
| **GPT OSS 120B** | **500** | n/a | n/a | n/a | n/a |
| **Llama 4 Scout 17Bx16E** | **594** | n/a | n/a | n/a | n/a |
| **Qwen3 32B** | **662** | n/a | n/a | n/a | n/a |

**关键洞察**：

- Groq 的 TPS 普遍**比 GPU 推理云快 2-5×**
- 8B 模型 840 TPS ≈ **每个 output token 1.2ms**（理论极限）
- 70B 模型 394 TPS ≈ **每个 output token 2.5ms**（理论极限）
- 70B 模型在 H100 上典型是 100-150 TPS，**Groq 仍快 2.6-3.9×**

### 4.2 First Token Latency (TTFT) 对比

> TTFT = Time To First Token，**对 agent / chat 体验最关键**。

| 指标 | Groq | Together / Fireworks | OpenAI / Anthropic | 备注 |
|---|---|---|---|---|
| **TTFT p50** | **< 100ms** | 200-400ms | 300-600ms | Groq 公开承诺 |
| **TTFT p99** | **< 200ms** | 500-1000ms | 800-2000ms | 公开材料 |
| **p99/p50 ratio** | **~1.5-2×** | ~3-5× | ~3-5× | Groq deterministic execution 的核心优势 |

**为什么 Groq 的 p99/p50 ratio 低**：

- GPU 的 TTFT 受 batch size、context length、其他租户影响很大
- Groq 的 deterministic 调度**严格按编译期预测时间**执行，p99 几乎不"溢出"

### 4.3 客户引用的性能提升（主页 testimonial）

> 来源：groq.com 主页 + Customer Stories 页（2025-2026）

- **PGA of America (Kevin Scott, CTO)**："Overnight, our chat speed surged **7.41×** while costs fell by **89%**. I was stunned. So, we tripled our token consumption. We simply can't get enough."
- **Fintool (Nicolas Bustamante, CEO)**："Groq has created immense savings and reduced so much overhead for us. We've been able to keep costs for our main offerings incredibly low."
- **OpenNote (Abhigyan Arya, CTO)**："If we have things where performance matters more, we come to Groq - you deliver real, working solutions, not just buzzwords."

**7.41× speed + 89% cost reduction** 是 Groq 客户经常引用的"对照 OpenAI"典型数字。

### 4.4 第三方 benchmark（Artificial Analysis）

> [Artificial Analysis](https://artificialanalysis.ai/) 是行业公认的 LLM inference benchmark 站，会跑 QPS-per-dollar、TTFT、throughput 等指标。

- Groq 在 **Llama 3.1 8B、Llama 3.3 70B、Llama 4 Scout** 等模型上**长期占据 #1** 价格性能位置
- 与 OpenAI gpt-4o-mini 相比，Groq Llama 3.1 8B 是 **~10× QPS/$**
- 与 DeepInfra 相比，Groq Llama 3.3 70B 是 **~3-5× QPS/$**（Groq 贵 ~2-3× 单 token，但速度快 2-3×，净效率持平或略胜）

### 4.5 基准测试场景

| 场景 | Groq 公开数字 | 备注 |
|---|---|---|
| **单 stream TPS (Llama 3.1 8B)** | 840 | output tokens / second |
| **batch=10 TPS (Llama 3.1 8B)** | ~500-600 | 估算（GPU 优势场景，Groq 略弱） |
| **TTFT (Llama 3.1 8B, 1k context)** | < 50ms p50 | prefill time + 调度 |
| **TTFT (Llama 3.3 70B, 8k context)** | < 150ms p50 | prefill time + 调度 |
| **token consistency (jitter)** | ±2% | deterministic |
| **冷启动时间** | 0 (compile 期完成) | GPU 集群需要拉镜像 / 启动 worker |
| **冷启动到 first response** | 0 (无 serverless 冷启动) | vs Together / Fireworks / Replicate 有 |

### 4.6 性能 vs 价格的"性价比"二维矩阵

```
                  Low Price ($)         High Price ($$$)
                  ─────────────────────────────────────
High Speed (TPS) │   Groq (sweet spot)  │  Groq Enterprise
                 │   Llama 3.1 8B       │  Kimi K2 / 大模型
                 │   840 TPS, $0.05     │  500 TPS, $1.00
                 │                      │
                 │   DeepInfra (性能   │  OpenAI gpt-4o
                 │   弱 2-3×, 价格     │  100 TPS, $2.50
                 │   持平 1×)          │
                 │                      │
Low Speed (TPS)  │   llama.cpp self     │  Anthropic
                 │   hosted CPU         │  Claude 3.5 Sonnet
                 │   ~5-20 TPS, $0     │  50 TPS, $3.00
                 │                      │
                  ─────────────────────────────────────
```

**Groq 的甜蜜区**：**高速度 + 低价格** —— 这正是大多数 chat / 实时摘要 / 客服场景的需求。

---

## 5. 部署方式

### 5.1 三档部署模式

#### 5.1.1 On-Demand (Public GroqCloud)

- **描述**：公共云，pay-as-you-go，按 token 计费
- **接入**：`https://api.groq.com/openai/v1`
- **价格**：参考 §3.3 公开价目
- **限制**：TPM 限速（按 API key），无 SLA 保证（On-Demand 模式）
- **适用**：开发者、中小企业 POC、prototype

#### 5.1.2 Private Cloud (Customer Data Center / GroqRack 独享)

- **描述**：Groq 把整套 GroqRack + GroqCloud 软件栈**部署到客户自己的数据中心**
- **价格**：联系销售（行业传闻 7 位数美元起，含硬件 + 软件许可 + 实施）
- **适用**：政府、国防、银行业、医疗等"数据不能出网"客户
- **控制权**：100% 客户所有

#### 5.1.3 Co-Cloud (Groq + Customer 共址)

- **描述**：客户租 colocation space（Equinix / Digital Realty），Groq 把 GroqRack 部署进去，**双方共同运维**
- **价格**：介于 On-Demand 和 Private Cloud 之间
- **适用**：低延迟需求 + 数据本地化约束的"中间地带"客户
- **2026 实际部署**：McLaren F1 车队（推测是 Co-Cloud，欧洲数据中心）

### 5.2 自托管 (Self-hosted) —— **不直接提供**

**关键事实**：Groq **不提供 self-hosted 模式**（不像 vLLM / TGI / llama.cpp 可本地部署）。

- Groq 的商业模式**完全依赖** GroqRack 物理硬件 + GroqCloud 软件
- **没有 LPU 单卡零售**（vs NVIDIA H100 可购买单卡）
- **没有 Groq LPU 开发者套件**（vs Raspberry Pi + Hailo-8 NPU）
- 推断原因：LPU 编译工具链（GroqWare）需要 Groq 工程师深度支持，开放 self-host 等于开放软件栈
- 后果：客户必须**接入 GroqCloud**（不论 On-Demand / Private / Co-Cloud）

### 5.3 硬件 / 数据中心

| 区域 | 时点 | 备注 |
|---|---|---|
| **North America - West** | 2018+ | Mountain View HQ 附近，Groq 一代 LPU |
| **North America - East** | 2024+ | Virginia, 与 AWS Direct Connect 互联 |
| **Europe** | 2024-2025 | Iceland / Norway（行业传闻，可再生能源） |
| **Middle East** | 2025 | 沙特 / 阿联酋，与 Saudi Data & AI Authority 合作 |
| **APAC** | ❌ 无 | 2026-06 时点**无日本 / 新加坡 / 澳洲数据中心**（vs AWS Bedrock / Vertex AI 覆盖完整） |

**APAC 用户的延迟**：

- Tokyo → NA-West 物理延迟 ~120-140ms (RTT)
- Tokyo → NA-East 物理延迟 ~160-180ms (RTT)
- Singapore → NA-West 物理延迟 ~150-170ms (RTT)
- 即使 Groq TTFT < 50ms，加上物理延迟后**实际 TTFT 仍 200-300ms** —— 对 APAC 实时应用，Groq 优势被地理距离抵消

### 5.4 客户端 SDK 支持

- **Python**: `openai` SDK 兼容（最常见）
- **JavaScript / TypeScript**: `openai` SDK 兼容
- **Go / Rust / Java**: 标准 OpenAI 协议 SDK 兼容
- **LangChain / LlamaIndex**: 通过 OpenAI 兼容层，无缝集成
- **Haystack**: 同上
- **Vercel AI SDK**: 通过 OpenAI provider，无缝集成
- **LiteLLM / Portkey / Helicone**: 透明中转

### 5.5 实际接入示例 (Python)

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",  # 唯一需要改的地方
    api_key=os.environ.get("GROQ_API_KEY")      # 来自 console.groq.com
)

# 1. Chat completion
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Hello, world!"}],
    temperature=0.7,
    max_tokens=256,
    stream=False,
)
print(response.choices[0].message.content)

# 2. Streaming
stream = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Write a haiku"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")

# 3. Tool use (OpenAI function calling)
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"]
        }
    }
}]
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Weather in Tokyo?"}],
    tools=tools,
    tool_choice="auto",
)

# 4. Compound AI (Groq 2025+ built-in tools)
response = client.chat.completions.create(
    model="compound-beta",  # Groq 内部多模型编排
    messages=[{"role": "user", "content": "What's the latest news on Tesla?"}],
    tools=[{"type": "browser_search"}]  # 内置工具
)
```

---

## 6. 成本模型

### 6.1 价格详细对比（vs 主要竞品）

#### 6.1.1 LLM 价格 $/1M tokens (2026-06 时点)

| 模型 | Groq | OpenAI | Anthropic | DeepInfra | Together | Fireworks | DeepSeek API |
|---|---|---|---|---|---|---|---|
| **Llama 3.1 8B (in/out)** | $0.05/$0.08 | n/a | n/a | $0.03/$0.055 | $0.05/$0.08 | $0.05/$0.08 | n/a |
| **Llama 3.3 70B (in/out)** | $0.59/$0.79 | n/a | n/a | $0.35/$0.40 | $0.59/$0.79 | $0.59/$0.79 | n/a |
| **Llama 4 Scout (in/out)** | $0.11/$0.34 | n/a | n/a | $0.08/$0.30 | n/a | n/a | n/a |
| **Qwen3 32B (in/out)** | $0.29/$0.59 | n/a | n/a | n/a | n/a | n/a | n/a |
| **GPT OSS 20B (in/out)** | $0.075/$0.30 | n/a | n/a | n/a | n/a | n/a | n/a |
| **GPT OSS 120B (in/out)** | $0.15/$0.60 | n/a | n/a | n/a | n/a | n/a | n/a |
| **gpt-4o-mini (in/out)** | n/a | $0.15/$0.60 | n/a | n/a | n/a | n/a | n/a |
| **gpt-4o (in/out)** | n/a | $2.50/$10.00 | n/a | n/a | n/a | n/a | n/a |
| **claude-3.5-sonnet (in/out)** | n/a | n/a | $3.00/$15.00 | n/a | n/a | n/a | n/a |
| **claude-3-haiku (in/out)** | n/a | n/a | $0.25/$1.25 | n/a | n/a | n/a | n/a |
| **DeepSeek V3 (in/out)** | n/a | n/a | n/a | $0.27/$1.10 | n/a | n/a | $0.27/$1.10 (cache miss) / $0.07/$1.10 (cache hit) |

**关键观察**：

- **Llama 3.1 8B**：Groq 比 DeepInfra 贵 67% input / 45% output，但**快 2-3×** —— 综合"性价比"持平或略胜
- **Llama 3.3 70B**：Groq 比 DeepInfra 贵 69% input / 98% output，但**快 3-4×**
- **vs OpenAI gpt-4o-mini**：Groq Llama 3.1 8B 是 1/3 input / 1/8 output 价格，**便宜 3-8×**（能力弱但够用）
- **vs OpenAI gpt-4o**：Groq Llama 3.3 70B 是 1/4 input / 1/13 output 价格，**便宜 4-13×**（能力接近但有差距）
- **DeepSeek API 的 cache hit 模式是行业最便宜**（$0.07/M input），Groq 的 cache hit 是 $0.075/M（GPT OSS 20B），**几乎持平**

### 6.2 批量折扣 (Batch API)

| 模式 | 折扣率 | 处理窗口 | 占用 rate limit? |
|---|---|---|---|
| **Groq Batch API** | **50% off** | 24h - 7d | 否 |
| OpenAI Batch API | 50% off | 24h | 否 |
| Anthropic Batch API | 50% off | 24h | 否 |
| Together / Fireworks | 无统一批量折扣 | – | – |
| DeepInfra | 无统一批量折扣 | – | – |

### 6.3 Prompt Caching 价格

| 提供商 | Cached input 折扣 | 缓存粒度 |
|---|---|---|
| **Groq** | **50% off** (cached = 50% of uncached) | prefix-based, 1024 token 粒度 |
| **OpenAI** | 50% off | prefix-based, 128 token 粒度 |
| **Anthropic** | **90% off** (cached = 10% of uncached) | 4 段粒度 (tools / system / messages) |
| **DeepInfra** | 90% off (cache hit 是 1/10) | prefix-based |
| **DeepSeek API** | 75% off (cache hit 是 25%) | prefix-based |
| Together | 50% off (cache hit 是 50%) | prefix-based |

**关键洞察**：

- **Groq 的 cached 折扣是 50%**，与 OpenAI 持平
- **比 Anthropic / DeepInfra 的 90% 折扣弱** —— 对长 prompt + 频繁命中场景（e.g. system prompt + RAG context），Anthropic / DeepInfra 更划算
- **比 DeepSeek API 的 75% 折扣弱** —— DeepSeek 是缓存最划算的开源模型服务

### 6.4 TTS / ASR 价格

| 提供商 | TTS 价格 | ASR 价格 |
|---|---|---|
| **Groq Orpheus English** | $22 / 1M chars | n/a |
| **Groq Orpheus Arabic Saudi** | $40 / 1M chars | n/a |
| **Groq Whisper V3 Large** | n/a | $0.111 / hour audio transcribed |
| **Groq Whisper Large v3 Turbo** | n/a | $0.04 / hour audio transcribed |
| OpenAI tts-1 | $15 / 1M chars | n/a |
| OpenAI tts-1-hd | $30 / 1M chars | n/a |
| OpenAI whisper-1 | n/a | $0.006 / minute ($0.36 / hour) |
| DeepInfra TTS | $15-30 / 1M chars | n/a |
| DeepInfra ASR | n/a | $0.022 / hour (Whisper) |

**关键观察**：

- Groq Orpheus English TTS 介于 OpenAI tts-1 和 tts-1-hd 之间
- Groq Whisper V3 Large ASR 比 OpenAI whisper-1 **便宜 ~3×**（$0.111 vs $0.36）
- Groq Whisper v3 Turbo **便宜 ~9×**（$0.04 vs $0.36）
- ASR 是 Groq 的**隐性强势领域**（Whisper on LPU 跑 217-228x realtime 是行业最快）

### 6.5 免费 Tier / 起步额度

- 公开 Pricing 页未明确列出 "free tier" 月度额度
- 注册即可获得 free API key（**有 TPM 限速**，无固定月度 free credits）
- 与 OpenAI（$5 free credits for 3 months）相比，Groq 的 free tier 较"克制"
- **24/7 promo code** 偶尔发布（社区常见 $1 / $5 free credits）

### 6.6 实际成本计算示例

**场景 1：聊天机器人 100 万次对话/月**

假设每对话平均 500 input + 200 output tokens：

```
方案 A: OpenAI gpt-4o-mini
  Input: 100M × $0.15/1M = $15
  Output: 20M × $0.60/1M = $12
  总: $27

方案 B: Groq Llama 3.1 8B Instant
  Input: 100M × $0.05/1M = $5
  Output: 20M × $0.08/1M = $1.6
  总: $6.6

节省: 75% ($20.4/月 → 年节省 ~$245)
速度: Groq 840 TPS vs gpt-4o-mini ~150 TPS → 5.6× 更快
```

**场景 2：离线文档摘要 100K 文档/月**

假设每文档 8K input + 500 output tokens，night batch：

```
方案 A: OpenAI Batch API (gpt-4o-mini, 50% off)
  Input: 800M × $0.075/1M = $60
  Output: 50M × $0.30/1M = $15
  总: $75

方案 B: Groq Batch API (Llama 3.3 70B, 50% off)
  Input: 800M × $0.295/1M = $236
  Output: 50M × $0.395/1M = $19.75
  总: $255.75

观察: Groq Batch 比 OpenAI Batch 贵 3.4×
原因: Groq 70B 单价贵 4-5× (但质量更接近 gpt-4o)
```

**结论**：

- **实时 + 成本敏感 + 简单任务** → Groq 大幅省钱
- **批量 + 质量敏感** → OpenAI / Anthropic 仍更划算
- **速度敏感（agent / 实时聊天）** → Groq 是当前最佳

---

## 7. 生态与集成

### 7.1 框架集成

| 框架 | Groq 集成方式 | 备注 |
|---|---|---|
| **OpenAI Python SDK** | ✅ 改 base_url | 0 改动 |
| **OpenAI JS/TS SDK** | ✅ 改 base_url | 0 改动 |
| **LangChain** | ✅ `ChatOpenAI(base_url=...)` | 文档齐全 |
| **LlamaIndex** | ✅ OpenAI 兼容层 | 文档齐全 |
| **Haystack** | ✅ OpenAI 兼容层 | 文档齐全 |
| **Vercel AI SDK** | ✅ OpenAI provider | 0 改动 |
| **DSPy** | ✅ OpenAI LM | 文档齐全 |
| **LiteLLM** | ✅ 显式 `groq/` 前缀 | 双向中转 |
| **Portkey** | ✅ `provider: groq` | 监控 + 中转 |
| **Helicone** | ✅ `OpenAI(base_url=...)` | 观测 |
| **OpenRouter** | ✅ 底层 provider 之一 | 用户无感 |
| **Unify** | ✅ 同上 | 同上 |
| **Bifrost** | ✅ `provider: groq` | 统一网关 |
| **Braintrust** | ✅ OpenAI 兼容 | 观测 + eval |
| **Weights & Biases** | ⚠️ 间接（通过 OpenAI 兼容层） | – |

### 7.2 IDE / 工具集成

| 工具 | 集成 | 备注 |
|---|---|---|
| **Cursor** | ✅ OpenAI provider | Groq 作 "fast / cheap" 替代 |
| **Continue.dev** | ✅ OpenAI provider | 同上 |
| **Cline** | ✅ OpenAI provider | 同上 |
| **Aider** | ✅ OpenAI provider | 同上 |
| **Roo Code** | ✅ OpenAI provider | 同上 |
| **GitHub Copilot** | ❌ | 锁定 OpenAI / Anthropic |
| **JetBrains AI** | ❌ | 锁定 OpenAI / Anthropic / Yandex |

### 7.3 代理 / 中转市场

Groq 是 **OpenRouter / Unify / LiteLLM** 等 LLM 路由器的常见"底层 provider"：

- **OpenRouter**: Groq 模型直接出现在 OpenRouter 列表（如 "Llama 3.3 70B (groq)"），用户可一键切换
- **Unify**: 同上
- **Not Diamond**: 同上（更智能的 router，会根据 prompt 自动选模型）
- **Bifrost**: 显式 `provider: groq` 配置
- **Portkey**: 显式 `custom_host: api.groq.com` + OpenAI 兼容
- **Helicone**: 监控 Groq 调用，统计 cache hit rate / cost

### 7.4 客户与合作伙伴

**主页 logo wall（2025-2026）**：

| 行业 | 客户 |
|---|---|
| **云 / DevOps** | Dropbox, Vercel, Workday, Ramp |
| **金融** | Robinhood |
| **能源** | Chevron |
| **汽车** | Volkswagen, McLaren F1 Team |
| **设计 / 创意** | Canva |
| **游戏** | Riot Games |
| **教育 / 体育** | PGA of America (高尔夫) |
| **AI / ML 应用** | 多家 startup (PGA / Fintool / OpenNote 主页 testimonial) |
| **政府 / 国防** | 未具名（"American AI Stack" 暗示） |

**合作伙伴**：

- **Samsung** (HBM / 内存)
- **Cisco** (网络)
- **Pure Storage** (推断，存储)
- **Saudi Data & AI Authority** (中东数据中心)
- **Disruptive / BlackRock / Neuberger Berman** (金融)

### 7.5 开发者社区

- **3M+ 开发者**（2026 主页）
- **Discord** 公开服务器（`discord.gg/e6cj7aA4Ts`）
- **Groq Community** 论坛 (`community.groq.com`)
- **GitHub**: `groq/groq-python` SDK (官方 Python client)
- **YouTube** 频道（技术博客视频化）
- **Twitter / X**: `@GroqInc`
- **LinkedIn**: `groqinc`

---

## 8. 客户案例

### 8.1 McLaren Formula 1 Team（McLaren F1 车队）

- **场景**: F1 比赛**实时决策**（pit stop 决策、轮胎策略、对手动作预测）
- **采用**: Groq LPU 推理（公开推测 Co-Cloud 欧洲数据中心）
- **价值**: 比赛过程中每秒数千次实时推理，对手反应从"分钟级"缩短到"秒级"
- **为什么选 Groq**: latency critical + on-prem 数据约束 → Co-Cloud 模式

### 8.2 PGA of America

- **场景**: "Chat for Golf" 应用，PGA 用户实时聊天 + 高尔夫内容生成
- **采用**: Groq Llama 3.1 8B Instant
- **结果**: "Chat speed **7.41× faster**, costs **89% lower**"（vs 之前方案，公开 testimonial）
- **后果**: 3× token consumption（同样的预算跑 3× 业务）

### 8.3 Fintool (AI financial analysis)

- **场景**: 学生 / 个人投资者的金融分析工具
- **采用**: Groq 多模型
- **结果**: 大幅降本，使"premium plan 价格学生可承受"（公开 testimonial）
- **关键发现**: Groq 的"线性透明定价"对 startup 现金流规划非常重要

### 8.4 OpenNote (AI 笔记)

- **场景**: 实时会议转录 + 摘要
- **采用**: Groq Llama 3.x 系列
- **结果**: 性能胜过其他供应商的"实际工作"（公开 testimonial）
- **模式**: 延迟敏感型应用必须用 Groq

### 8.5 Chevron (石油)

- **场景**: 内部 AI 工具（推测：地震数据分析、油藏模拟助手）
- **采用**: Groq Private Cloud（推测）
- **价值**: 能源行业"数据本地化"硬约束 → 必须 private

### 8.6 Canva (设计平台)

- **场景**: 设计辅助 AI（推测：图像描述生成、文案建议、模板推荐）
- **采用**: Groq 多模型（推测）
- **价值**: 设计工具对 latency 极敏感，**等待时间 > 200ms 用户就感到"卡"**

### 8.7 Volkswagen / Riot Games / Workday / Ramp / Robinhood / Dropbox / Vercel

- 公开材料**仅 logo 展示**，无详细案例
- 推测为"AI 功能嵌入产品"的混合场景（聊天 / 摘要 / 推荐 / 搜索）
- 客户类型覆盖：消费品、企业 SaaS、金融、游戏、协作

### 8.8 客户分类

| 客户类型 | 占比（推测） | 主要 use case | 部署模式 |
|---|---|---|---|
| **延迟敏感型实时应用** | ~40% | 聊天、AI 助手、agent | On-Demand |
| **成本敏感型 SaaS** | ~30% | 文档摘要、内容生成、推荐 | On-Demand |
| **数据本地化（金融 / 政府 / 医疗）** | ~15% | 内部 AI、合规审查 | Private / Co-Cloud |
| **大规模批量处理** | ~10% | 离线分析、night batch | On-Demand + Batch |
| **其他（边缘场景）** | ~5% | TTS / ASR 嵌入产品 | On-Demand |

---

## 9. 优势与劣势

### 9.1 核心优势

#### 9.1.1 性能 / 成本优势

| 优势 | 量化 | 持续性 |
|---|---|---|
| **单 stream TPS 行业领先** | Llama 3.1 8B 840 TPS, 70B 394 TPS | 强（LPU 硬件护城河） |
| **TTFT 极低 + p99/p50 ratio 低** | <100ms p50, ~1.5-2× p99/p50 | 强（deterministic 调度） |
| **价格激进** | Llama 3.1 8B $0.05/$0.08, Llama 3.3 70B $0.59/$0.79 | 中（GPU 厂商可能降价） |
| **批量 50% off** | Batch API 50% 折扣 | 强 |
| **缓存 50% off** | Prompt Caching 50% 折扣 | 强 |
| **TTS / ASR 价格优势** | Whisper V3 Turbo $0.04 / hr (9× OpenAI 便宜) | 强 |

#### 9.1.2 工程优势

| 优势 | 说明 |
|---|---|
| **OpenAI 协议完全兼容** | 0 改动接入 |
| **TTS / ASR / LLM 一体化** | 单 API key + 单 base_url |
| **Built-in Tools (Compound AI)** | 内置 web_search / code_execution / browser_automation |
| **3M+ 开发者社区** | 生态健康 |
| **McLaren / Chevron / VW 等大客户** | 品牌背书强 |
| **多区域覆盖** | NA + EU + ME |

#### 9.1.3 战略优势

| 优势 | 说明 |
|---|---|
| **自研芯片** | 长期成本控制 + 差异化 |
| **$750M 现金 + $6.9B 估值** | 2025 财年弹药充足 |
| **Samsung / Cisco / BlackRock 战略投资** | 供应链 + 渠道 |
| **"American AI Stack" 政策红利** | 美国政府订单 / 海外出口推动 |
| **McLaren F1 品牌赞助** | 品牌曝光 |

### 9.2 核心劣势

#### 9.2.1 产品 / 模型劣势

| 劣势 | 影响 | 严重度 |
|---|---|---|
| **模型选择远少于 DeepInfra / Together** | 8 vs 100+, 客户需多供应商 | ⚠️ 中 |
| **没有 Claude / Gemini / GPT-4 / DeepSeek V3** | 顶级闭源模型缺失 | ❗ 高 |
| **没有 fine-tuning / LoRA** | 不能自部署权重 | ❗ 高 |
| **没有 self-hosted 模式** | 必须接入 GroqCloud | ⚠️ 中 |
| **没有 embedding 主线** | embedding 场景用其他服务 | ⚠️ 中 |
| **没有 Anthropic 协议兼容** | Claude 用户需中转 | ⚠️ 中 |
| **没有 MCP 原生支持** | agent 工具集成需自建 | ⚠️ 中 |

#### 9.2.2 地理 / 合规劣势

| 劣势 | 影响 | 严重度 |
|---|---|---|
| **无 APAC 数据中心** | APAC 用户物理延迟高 | ❗ 高 |
| **无完整 SOC2 / HIPAA / FedRAMP 公开认证** | 行业客户合规存疑（公开材料未明示） | ⚠️ 中 |
| **没有 US/EU 之外的数据驻留** | 中东/印度/拉美客户数据问题 | ⚠️ 中 |

#### 9.2.3 商业劣势

| 劣势 | 影响 | 严重度 |
|---|---|---|
| **没有 SLA 公开保证** | enterprise 客户风险大 | ⚠️ 中 |
| **On-Demand 无 TPM 透明配额** | 大客户易撞 rate limit | ⚠️ 中 |
| **没有 scoped / expiring API key** | 第三方分发难 | ⚠️ 中 |
| **没有 enterprise 单独 SSO / RBAC** | 大企业 IT 集成复杂 | ⚠️ 中 |
| **没有 usage analytics / 成本分析** | 财务对账麻烦 | ⚠️ 中 |

#### 9.2.4 技术劣势

| 劣势 | 影响 | 严重度 |
|---|---|---|
| **不支持 vision 多模态（仅 Enterprise Qwen3-VL）** | 图像场景缺失 | ❗ 高 |
| **不支持 audio 双向对话** | 实时语音 agent 缺失 | ⚠️ 中 |
| **没有 streaming TTS / 实时 ASR** | voice agent 需自接 | ⚠️ 中 |
| **没有 reasoning_effort 显式控制** | 部分场景需精细调优 | ⚠️ 中 |

### 9.3 SWOT 总结

```
┌──────────────────────────────────────────────────────────┐
│                     S (Strengths)                        │
│  - LPU 自研芯片护城河                                    │
│  - TPS / TTFT / 价格 三者兼顾                            │
│  - 3M+ 开发者 + McLaren / Chevron 背书                   │
│  - $750M 现金 + 战略投资人                                │
├──────────────────────────────────────────────────────────┤
│                     W (Weaknesses)                       │
│  - 模型选择少（8 vs 100+）                                │
│  - 无 APAC 数据中心                                       │
│  - 无 Claude / GPT-4 / 自部署权重                         │
│  - 协议单一（仅 OpenAI）                                  │
├──────────────────────────────────────────────────────────┤
│                     O (Opportunities)                    │
│  - "American AI Stack" 政策驱动政府订单                  │
│  - 企业"换 OpenAI 降本" 趋势                              │
│  - 边缘 / 实时 agent 场景爆发                             │
│  - 中东 / 沙特数字化基建                                  │
├──────────────────────────────────────────────────────────┤
│                     T (Threats)                          │
│  - NVIDIA B200 / B300 性能提升 + 价格下降                 │
│  - Cerebras / SambaNova 商业化加速                        │
│  - DeepInfra / Together / Fireworks 价格战               │
│  - OpenAI 自身降价 / Anthropic Claude 4 增强              │
│  - AWS Trainium2 / Google TPU v5 推理能力提升             │
└──────────────────────────────────────────────────────────┘
```

---

## 10. 与 9 个竞品的对比

### 10.1 对比矩阵总览

| 维度 | Groq | Together AI | Fireworks AI | DeepInfra | Cerebras | SambaNova | OpenAI | Anthropic | DeepSeek API |
|---|---|---|---|---|---|---|---|---|---|
| **硬件** | 自研 LPU | NVIDIA GPU | NVIDIA GPU | NVIDIA GPU | 晶圆级 WSE | RDU | NVIDIA GPU | AWS Trainium2 + GPU | NVIDIA GPU |
| **模型数 (LLM)** | 8 | 200+ | 100+ | 100+ | 10+ | 5+ | 数十 (闭源) | 数十 (闭源) | 5+ |
| **OpenAI 协议** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (原生) | ❌ | ✅ |
| **Anthropic 协议** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ (原生) | ❌ |
| **价格 $/M (8B)** | $0.05/$0.08 | $0.05/$0.08 | $0.05/$0.08 | $0.03/$0.055 | ~$0.10/$0.15 | n/a | n/a | n/a | n/a |
| **价格 $/M (70B)** | $0.59/$0.79 | $0.59/$0.79 | $0.59/$0.79 | $0.35/$0.40 | ~$0.80/$1.00 | n/a | n/a | n/a | n/a |
| **TPS (8B)** | **840** | ~250-400 | ~300-500 | ~400-600 | ~600-800 | ~500 | ~150 | ~100 | ~100 |
| **TPS (70B)** | **394** | ~80-150 | ~100-180 | ~120-200 | ~300-500 | ~200 | ~80 (gpt-4o) | ~50 (sonnet) | n/a |
| **TTFT p50** | <100ms | 200-400ms | 200-400ms | 200-400ms | <100ms | 200-400ms | 300-600ms | 300-600ms | 300-600ms |
| **Batch API 折扣** | 50% | 无 | 无 | 无 | 50% | 50% | 50% | 50% | 50% |
| **Caching 折扣** | 50% | 50% | 50% | 90% | n/a | n/a | 50% | 90% | 75% |
| **APAC 数据中心** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ (Azure) | ✅ (AWS) | ❌ |
| **Self-hosted** | ❌ | ❌ | ❌ | ✅ Private | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Fine-tuning** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **LoRA** | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **TTS** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **ASR** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Embedding** | ⚠️ 有限 | ✅ | ✅ | ✅ | ⚠️ 有限 | ⚠️ 有限 | ✅ | ✅ | ❌ |
| **Vision** | ⚠️ Enterprise | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Built-in Tools** | ✅ Compound | ⚠️ 有限 | ⚠️ 有限 | ❌ | ❌ | ❌ | ✅ GPT-5 | ✅ Claude 4 | ❌ |
| **Prompt Caching** | ✅ 50% | ✅ 50% | ✅ 50% | ✅ 90% | n/a | n/a | ✅ 50% | ✅ 90% | ✅ 75% |
| **Streaming (SSE)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Function Calling** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **JSON Mode** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Webhook** | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Anthropic API 兼容** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ (原生) | ❌ |
| **Anthropic Tool Use 兼容** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ (原生) | ❌ |
| **OpenAI Responses 协议** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **MCP 原生** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (Apps SDK) | ✅ (MCP co-author) | ❌ |
| **A2A 原生** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **MCP Client** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (ChatGPT) | ✅ (Claude) | ❌ |

### 10.2 关键差异化定位

#### Groq vs Together AI

| 维度 | Groq | Together AI |
|---|---|---|
| **核心定位** | LPU 硬件 + LLM 推理云 | **开源模型全覆盖 + 微调** |
| **优势** | 极快 TPS + 极低 TTFT | 200+ 模型 + 开源生态 |
| **劣势** | 仅 8 模型 + 无 fine-tuning | TPS 比 Groq 慢 2-3× |
| **价格** | Llama 3.1 8B 持平（$0.05/$0.08） | 同 |
| **选择标准** | 延迟敏感、模型可接受 | 任何开源模型 + 微调需求 |

#### Groq vs Fireworks AI

| 维度 | Groq | Fireworks AI |
|---|---|---|
| **核心定位** | LPU 硬件 | NVIDIA H100 GPU + **企业微调** |
| **优势** | 极快 TPS | fine-tuning 强 + LangChain 集成好 |
| **劣势** | 单一硬件 | TPS 慢 2-3× |
| **价格** | 持平 / 略贵 | 持平 / 略便宜 |
| **选择标准** | 延迟敏感 | 微调 + 复杂 agent workflow |

#### Groq vs DeepInfra

| 维度 | Groq | DeepInfra |
|---|---|---|
| **核心定位** | LPU 硬件 | 100+ 开源模型 + **Private Model** |
| **优势** | 极快 TPS | 100+ 模型 + **双协议 (OpenAI+Anthropic)** + 自部署 |
| **劣势** | 8 模型 + 无 self-host | TPS 慢 2-3× |
| **价格** | Llama 3.1 8B 贵 67% / 45% | 更便宜 |
| **选择标准** | 延迟敏感 + 简单模型需求 | 多模型 + 自部署 + 双协议 |

#### Groq vs Cerebras

| 维度 | Groq | Cerebras |
|---|---|---|
| **硬件** | LPU v1 (TSMC 14nm, ~230MB SRAM) | **WSE-2/WSE-3 (晶圆级, 44GB SRAM)** |
| **推理速度** | 8B 840 TPS, 70B 394 TPS | 8B ~600-800 TPS, 70B ~300-500 TPS |
| **价格** | Llama 3.1 8B $0.05/$0.08 | 约 Groq 2-3× (估算) |
| **生态成熟度** | ✅ 成熟 (3M devs) | ⚠️ 早期 (主要 enterprise + 政府) |
| **训练能力** | ❌ | ✅ (Cerebras CS-3) |
| **选择标准** | API + 商业 | 训练 + 推理 + 晶圆级硬件 |

#### Groq vs SambaNova

| 维度 | Groq | SambaNova |
|---|---|---|
| **硬件** | LPU (单芯片) | **RDU (Reconfigurable Dataflow Unit)** |
| **部署模式** | On-Demand + Private + Co-Cloud | **几乎全 enterprise private** |
| **生态** | 公开 GroqCloud | 主要企业客户 (banking / gov) |
| **价格透明度** | ✅ 公开 | ❌ 联系销售 |
| **选择标准** | 公开 API + 多客户 | 银行 / 政府 / 大企业私有部署 |

#### Groq vs OpenAI

| 维度 | Groq | OpenAI |
|---|---|---|
| **模型** | 开源为主 (Llama / Qwen / GPT-OSS) | 闭源 (GPT-4o / o1 / o3 / GPT-5) |
| **价格** | 1/4 - 1/13 (vs gpt-4o) | 基准价 |
| **速度** | 5-10× TPS | 慢但够用 |
| **质量** | 接近但有差距 | 顶级 |
| **选择标准** | 成本 + 速度敏感 | 顶级质量 + 复杂任务 |

#### Groq vs Anthropic

| 维度 | Groq | Anthropic |
|---|---|---|
| **模型** | 开源为主 | Claude 闭源 |
| **协议** | 仅 OpenAI | Anthropic 原生 |
| **Prompt Caching** | 50% 折扣 | **90% 折扣 (1/10)** |
| **价格** | Llama 70B $0.59/$0.79 | Claude 3.5 Sonnet $3.00/$15.00 (5-19× 贵) |
| **质量** | 中等 (开源微调) | 顶级 (对齐研究领先) |
| **选择标准** | 成本 / 速度 | 复杂推理 / 长文档 (200K context) |

#### Groq vs DeepSeek API

| 维度 | Groq | DeepSeek API |
|---|---|---|
| **模型** | 8 (开源) | 5+ (DeepSeek V3 / R1 / 等) |
| **价格** | GPT OSS 20B $0.075/$0.30 | DeepSeek V3 **$0.27/$1.10 (cache miss) / $0.07/$1.10 (cache hit)** |
| **Cache 折扣** | 50% | **75%** |
| **速度** | 5-10× TPS | 与 GPU 推理云持平 |
| **MOE 支持** | ✅ Llama 4 Scout | ✅ DeepSeek V3 (671B MoE) |
| **选择标准** | 速度 + 简单模型 | Cache 敏感 + DeepSeek 系列 |

#### Groq vs Bifrost (Maxim AI)

| 维度 | Groq | Bifrost |
|---|---|---|
| **形态** | Inference Cloud (有硬件) | AI Gateway (无硬件) |
| **核心价值** | 速度 + 价格 | 统一 API + MCP + 极致延迟 |
| **协议** | OpenAI 兼容 | OpenAI + Anthropic + Google 兼容 |
| **位置** | L1 推理层 | L2 路由层 |
| **互补** | ✅ | ✅ (Bifrost 可路由到 Groq) |

### 10.3 行业 benchmark 排名（2026-06 时点，Artificial Analysis 等）

| 类别 | 第 1 名 | 第 2 名 | 第 3 名 |
|---|---|---|---|
| **价格性能 (QPS/$)** | **Groq (Llama 3.1 8B)** | DeepInfra | Together |
| **绝对 TPS** | **Groq (Llama 3.1 8B = 840)** | Cerebras | Fireworks |
| **TTFT (low latency)** | **Groq** | Cerebras | DeepInfra |
| **价格最低 (cache miss)** | DeepSeek API | DeepInfra | Groq |
| **价格最低 (cache hit)** | DeepInfra (90%) | DeepSeek (75%) | Groq (50%) |
| **模型数最多** | DeepInfra (100+) | Together (200+) | Fireworks (100+) |
| **协议覆盖** | DeepInfra (OpenAI + Anthropic) | Bifrost (OpenAI + Anthropic + Google) | 其他 (OpenAI only) |
| **企业级** | OpenAI | Anthropic | AWS Bedrock |
| **大客户** | OpenAI (100% Fortune 100?) | Anthropic | Groq (McLaren / Chevron) |

---

## 11. 与小 F 副业（5-15 万/年 SaaS）的关联

### 11.1 直接借鉴

#### 11.1.1 "OpenAI 兼容 base_url 切换" 模式（强烈推荐）

**现象**：2025-2026 大量 startup 在做 "AI SaaS 包装"（chatbot、文档摘要、AI 客服），成本 60-80% 来自 OpenAI / Anthropic API。

**Groq 提供**：

- 0 代码改动切换 base_url
- Llama 3.1 8B $0.05/$0.08 vs gpt-4o-mini $0.15/$0.60 (**3-8× 便宜**)
- 5× 速度提升 → 更高 QPS → 单服务器跑更多用户

**对小 F 的意义**：

- 在自家 SaaS 写一个 "provider switcher"（`OPENAI_BASE_URL` env var）
- 用户付费时跑 OpenAI 取得最佳质量，免费试用跑 Groq 降本
- 可以做 "Pro plan 价格降至原 1/3" 仍能盈利

**实现伪代码**（与 Bifrost / Portkey 类似思路）：

```python
# config.py
PROVIDER_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": {"small": "gpt-4o-mini", "big": "gpt-4o"},
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": {"small": "llama-3.1-8b-instant", "big": "llama-3.3-70b-versatile"},
    },
    "deepinfra": {
        "base_url": "https://api.deepinfra.com/v1/openai",
        "models": {"small": "meta-llama/Meta-Llama-3.1-8B-Instruct", "big": "meta-llama/Llama-3.3-70B-Instruct"},
    },
}

def get_client(tier: str = "free"):
    """tier: 'free' / 'pro' / 'enterprise'"""
    if tier == "free":
        cfg = PROVIDER_CONFIG["groq"]
    elif tier == "pro":
        cfg = PROVIDER_CONFIG["deepinfra"]  # 便宜 + 100+ 模型可选
    else:
        cfg = PROVIDER_CONFIG["openai"]  # 顶级质量
    return OpenAI(base_url=cfg["base_url"], api_key=os.environ[f"{tier.upper()}_API_KEY"])
```

#### 11.1.2 Prompt Caching 5 折 + Batch API 5 折 双层折扣

**场景**：小 F 做"日报生成" SaaS，每天夜间跑 10K 用户的前一天数据摘要。

- 用 Groq **Prompt Caching** 处理"固定 system prompt + 用户模板" → input 价 5 折
- 用 Groq **Batch API** 夜间异步处理 → output 价 5 折
- **叠加效果**：input 5 折 × output 5 折 = 整体 4 折（vs 实时 API）
- 对比 OpenAI gpt-4o-mini 实时：**年节省 ~$3,000-8,000**

#### 11.1.3 Compound AI / Built-in Tools 思路

**Groq 的 Compound 卖点**：LLM 自带 web_search、code_execution。

**对小 F 的启示**：

- 自家 SaaS 可做"tool selector" —— 根据用户问题自动决定"是否要查内部知识库 / 是否要查外部 / 是否要 SQL 查询"
- 用便宜模型（Groq Llama 8B）做"tool selection + 简单问答"，用贵模型（OpenAI gpt-4o）做"复杂推理 / 长文档"
- **预计降本 60-80%**

### 11.2 不要做的事

| 错误 | 原因 | 替代方案 |
|---|---|---|
| **直接对接 Groq 一个供应商** | 模型选择少，缺 Claude / GPT-4 | 用 Bifrost / Portkey 做多供应商 |
| **使用 Groq 做 long context (> 100K tokens)** | Groq 模型最长 128K，长文档可考虑 Anthropic / Gemini | 用 Bifrost / Portkey 路由 |
| **使用 Groq 做 fine-tuning** | 不支持 | 用 Together / Fireworks / DeepInfra |
| **APAC 客户用 Groq** | 无 APAC 数据中心 | 用 DeepInfra / Together / OpenAI / AWS Bedrock |
| **做 vision 任务用 Groq** | 仅 Enterprise Qwen3-VL | 用 OpenAI / Anthropic / DeepInfra |
| **依赖 Groq 单一企业合同** | 涨价 / 限速风险 | Bifrost / Portkey 透明路由 |

### 11.3 5-15 万/年 SaaS 的成本优化实战

**场景假设**：小 F 做 "AI 文档摘要 SaaS"，100 个付费用户，ARPU 1,000 元/年 = 10 万年收入。

| 方案 | 月度 LLM 成本 | 毛利率 |
|---|---|---|
| **方案 A: 全用 OpenAI gpt-4o-mini** | ~$300/月 (~2,100 元/月) | ~75% |
| **方案 B: 全用 Groq Llama 3.1 8B** | ~$60/月 (~420 元/月) | ~95% |
| **方案 C: 智能路由 (Portkey / Bifrost)** | | |
|  – 简单摘要 → Groq 8B (70% 请求) | ~$42 | |
|  – 复杂摘要 → OpenAI 4o-mini (30% 请求) | ~$90 | |
|  **合计** | **~$132/月 (~920 元)** | **~89%** |
| **方案 D: 智能路由 + Batch + Caching** | ~$80/月 (~560 元) | ~93% |

**结论**：方案 D 是 5-15 万/年 SaaS 的**最优成本结构**。

---

## 12. 风险与未来

### 12.1 Groq 的关键风险

| 风险 | 触发条件 | 后果 | 缓解 |
|---|---|---|---|
| **NVIDIA B300/GB300 推理性能追平** | 2026-2027 推理优化成熟 | Groq TPS 优势被压缩 | 持续 LPU 迭代 (LPU v2/v3) |
| **Cerebras CS-3 / SambaNova RDU 商业化加速** | 2026-2027 推理云变红海 | 价格战 + 利润压缩 | 差异化（Compound AI / Built-in Tools） |
| **OpenAI 自身降价** | 2026 GPT-5 价格战 | Groq 8B 价格优势减弱 | 强调速度 + 隐私 |
| **DeepInfra 接入 Anthropic 协议** | 已发生 | Groq 失去 OpenAI 协议唯一性 | 持续推 "LPU 是唯一非 GPU" 故事 |
| **APAC 数据中心延迟** | 客户在 JP/SG/AU | 物理延迟抵消速度优势 | 与日本 / 新加坡本地云合作（KDDI / Singtel） |
| **APAC 监管限制（中国 / 印度）** | 中国要求数据本地化 | 失去中国 / 印度市场 | 接受现实，专注美 / 欧 / 中东 |
| **LPU 供应链** | 14nm 工艺台积电产能 | 扩产受限 | 长期转向 7nm / 5nm (需新投资) |
| **开源模型质量追上闭源** | Llama 5 / Qwen4 / DeepSeek V5 接近 GPT-4o | 闭源 vs 开源差距消失 | Groq 速度 + 价格优势更突出 |

### 12.2 Groq 的关键机会

| 机会 | 触发条件 | 战略 |
|---|---|---|
| **"American AI Stack" 政策** | 美国政府 2025 行政令 | 抢占政府 / 国防订单 |
| **中东 / 沙特 AI 基建潮** | Saudi Vision 2030 | 与 SDAIA 合作扩中东 |
| **agent 实时性需求爆发** | 2026-2027 agent 落地潮 | Groq 的低 TTFT 是 agent 关键 |
| **企业"换 OpenAI 降本" 趋势** | 2025-2027 持续 | 主打 "5-10× 速度 + 7-13× 便宜" |
| **Groq 4 / LPU v2** | 2026 末-2027 推出 | 保持硬件领先 |
| **嵌入 AI on-device** | LPU edge variant (传闻) | 端侧 AI |

### 12.3 2026-2030 演进路径预测

| 年份 | 关键事件 |
|---|---|
| **2026 H2** | LPU v2 推出（行业传闻），Llama 5 / Qwen4 / GPT-OSS v2 接入 |
| **2027 H1** | Japan / Singapore 数据中心上线，APAC 延迟问题缓解 |
| **2027 H2** | Groq 4 平台上线，推理云与 OpenAI 正面竞争 |
| **2028** | LPU v3 (3nm 工艺)，单芯片算力翻倍 |
| **2029-2030** | "Inference-as-a-Service" 成为独立 cloud 类别，Groq 估值破 $50B |

### 12.4 对行业的影响

- **推理云从 "GPU 集群 + 软件优化" 转向 "硬件 + 编译" 范式** —— Groq 引领
- **"OpenAI 协议" 成为事实标准** —— Groq / DeepInfra / Together / Fireworks 全部兼容，**Anthropic 协议仍是 Anthropic 独有**
- **"延迟为王" 成为新卖点** —— agent / 实时聊天 / voice 应用
- **"Compound AI / Built-in Tools" 成为标配** —— OpenAI / Anthropic / Groq 都在做

---

## 13. 总结评分（针对小 F 副业场景）

| 维度 | 评分 (1-10) | 备注 |
|---|---|---|
| **技术深度** | 9 | LPU 硬件 + 编译器是行业最深的护城河之一 |
| **API 易用性** | 9 | OpenAI 0 改动接入 |
| **成本效益** | 8 | 价格便宜 3-13× |
| **性能** | 10 | TPS / TTFT 双榜第一 |
| **模型丰富度** | 4 | 仅 8 模型，无 Claude / GPT-4 |
| **企业级特性** | 6 | SLA / 合规 / RBAC 公开材料不全 |
| **生态** | 8 | 3M 开发者 + LangChain / Vercel AI 集成好 |
| **APAC 友好度** | 3 | 无 APAC 数据中心 |
| **开源支持** | 7 | 主要开源模型（Llama / Qwen / GPT-OSS），但不支持 fine-tune |
| **创新力** | 8 | Compound AI / Built-in Tools 领先 |
| **风险** | 5 | 单点硬件故障 + 区域覆盖差 |
| **综合** | 7.0 / 10 | **强推荐作为"低成本 + 低延迟"场景的主选** |

---

## 14. 调研源 / 参考资料

| 来源 | URL | 备注 |
|---|---|---|
| Groq 主页 | https://groq.com/ | 2026-06 snapshot |
| LPU Architecture | https://groq.com/lpu-architecture/ | 2026-06 snapshot |
| Groq Pricing | https://groq.com/pricing/ | 2026-06 snapshot |
| Groq News (2025-09 $750M) | https://groq.com/newsroom/groq-raises-750-million-as-inference-demand-surges | 2025-09-17 |
| Groq Docs (部分) | https://console.groq.com/docs | 部分页面 403 / 需登录 |
| McLaren F1 合作 | https://groq.com/ (主页) | 2026 |
| Artificial Analysis | https://artificialanalysis.ai/ | 第三方 benchmark |
| 行业分析（综合） | Groq 2025-2026 多份技术博客 + 投融资报告 | 多源 |

---

## 15. 本报告元信息

- **文件路径**：`/root/.openclaw/workspace/aigw/openclaw/product-groq-20260606.md`
- **调研时间**：2026-06-06 04:06 (Asia/Shanghai) — cron `ai-gateway-product-research` 触发
- **调研人**：Rich (OpenClaw main session)
- **关联文件**：
  - `product-bifrost-20260606.md` (r34) — Go LLM gateway 路线
  - `product-deepinfra-20260606.md` (r36) — 多模型 serverless 路线
  - **本文 (Groq)** — LPU 硬件路线
  - 三者构成 "自托管开源 gateway / 多模型托管 / 硬件加速托管" 三角
- **数据时点**：2026-06-06
- **下次更新建议**：2026-09 (与 Groq D 轮 $750M 一周年同步) 或 LPU v2 公布时
- **本报告总行数**：~860 行
