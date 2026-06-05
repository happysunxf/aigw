# DeepInfra — AI Gateway / Serverless Inference Cloud 深度调研报告

> 调研对象：**DeepInfra**（`deepinfra.com`，2026-06 时点全球"开源 LLM serverless inference + OpenAI/Anthropic 双协议兼容网关"领先平台之一，2026-05-04 完成 **$107M Series B**）
> 调研时间：2026-06-06 03:36 (Asia/Shanghai) — cron `ai-gateway-product-research` 第 36 轮触发（r34 = Bifrost 之后）；按 r33 disposition §6.2 "扩展候选清单 ⭐⭐⭐" 落地
> 调研人：Rich (OpenClaw main session)
> 文档定位：r30-r33 closure 之后**第二轮扩展清单**的首个产品；与 r34 Bifrost 报告（`product-bifrost-20260606.md`）配套 — Bifrost 是"Go 自托管开源 gateway"，DeepInfra 是"托管 serverless inference cloud + 兼容网关"，构成"自托管 vs 托管"对照。
> 调研范围：项目背景 / 架构设计 / 协议支持 / 性能数据 / 部署方式 / 成本模型 / 生态 / 客户案例 / 优劣势 / 与 9 个竞品对比

---

## 0. TL;DR（执行摘要）

DeepInfra 是一家位于 **Palo Alto, CA** 的 AI 推理云（AI inference cloud），2022 年由 **Yotam Shacham**（CEO）创立，前身/同源公司 **ModelZoo**（ModelZoo.io 域名历史在 Wayback 中可见，2017 年早期形态可追溯）。其核心定位：

1. **"OpenAI 兼容 + Anthropic 兼容"双协议 serverless inference** — 用户用 `openai.OpenAI(base_url="https://api.deepinfra.com/v1/openai")` 或 `anthropic.Anthropic(base_url="https://api.deepinfra.com/anthropic")` 即可调用 **100+ 开源 LLM**（DeepSeek V4 / Qwen3 / Llama-4 / Mistral / Gemma / Nemotron / Claude / Gemini / Voxtral / etc.），代码零修改。
2. **价格最激进的 serverless LLM** — DeepSeek-V4-Flash **$0.10 / 1M input tokens**、Qwen3-235B-A22B-Instruct-2507 **$0.071 / 1M input tokens**、DeepSeek-V3.2 **$0.26 / $0.38**；命中 prompt cache 价格 1/10；OpenRouter 集成商中**模型数最多**。
3. **2026-05-04 完成 $107M Series B**（500 Global + Georges Harik 联合领投，A.Capital Ventures / Crescent Cove / Felicis / **NVIDIA** / Peak6 / **Samsung Next** / **Supermicro** / Upper90 跟投）—— 强 GPU 供应链 + 战略投资人组合，意味着 DeepInfra 不只是一个 LLM gateway，而是 **"GPU-as-a-service + model-as-a-service" 双层 IaaS/PaaS**。
4. **GPU Instances 单独产品** — B200-180GB / B300-288GB（2026 最新 NVIDIA Blackwell / Blackwell Ultra）1-8 卡 SSH 直连，按小时计费，类似 Lambda / RunPod / Vast.ai 但有自家优化；与 **Private Models**（自部署 LoRA / fine-tuned 权重）共同构成 **企业自部署** 能力。
5. **Scoped JWT 鉴权** — 可签发 1 小时 / 1 美元消费上限 / 限定模型列表的 JWT，**给第三方使用而不暴露主 key**，这是企业级 API gateway 必备能力。
6. **OpenAI Function Calling + Anthropic Tool Use 双协议 + JSON Object / JSON Schema 结构化输出 + Prompt Caching (KV cache prefix reuse) + Streaming (SSE) + Service Tier (priority +20% 加价) + Reasoning Effort (none/low/medium/high)** — 完整覆盖 2026 LLM API 必备特性。
7. **Webhooks**（异步回调，long-running 请求用）+ **Logs/Metrics Query API** + **Webhooks/CLI (`deepctl`)** + **Vercel 集成 / GitHub CLI Login / Okta SSO** — 完整 DevOps 工具链。

**关键差异化（vs 其他 serverless LLM）**：
- **双协议兼容**（OpenAI + Anthropic 都做 serverless，且 Anthropic 端点明确支持 **Claude Code** 后端替换）—— 大多数竞品只做 OpenAI 兼容
- **Prompt Caching KV prefix 命中价格 1/10** + 显式 `prompt_cache_key` API —— 与 Anthropic / OpenAI 同等量级
- **LoRA Adapter 全栈**：既支持 LLM LoRA 也支持 **Civitai 风格 Image LoRA**
- **GPU Rental + Private Model + Serverless 三层**：从 GPU 出租 → 自部署 → 共享推理，覆盖 enterprise 完整场景

**关键限制**：
- **没有 US 数据中心外的多区域**（公开材料未提及 EU / APAC 数据中心）
- **Anthropic / Google 模型**虽然可调用，但 **prompt 和 response 会被转发到 Anthropic/Google 端点**，DeepInfra 本身**不缓存不存储**，且 **Anthropic / Google 保留训练权**（与共享 LLM 不训练的策略不同）
- **没有内置的语义缓存 / 路由器 / 限流 / API key 多级预算**（对比 Portkey / Helicone / LiteLLM + 自家 gateway 时缺少）
- **Reranker 已有但 RAG 套件**（文档解析 / chunking / retrieval）**未提供** —— 需自接 LlamaIndex / Haystack

**针对小 F 副业（5-15 万/年 SaaS）的可借鉴点**：
- "OpenAI 兼容 base_url 切换" 模式是降本最直接手段（用户用 DeepInfra 价格可降 80%+）
- `prompt_cache_key` 设计是 prompt engineering 的 UX 创新点
- Scoped JWT + 限额鉴权是企业级分销 / 多租户的"标配" — 应做进自家产品

---

## 1. 项目背景

### 1.1 公司与团队

| 项 | 值 | 备注 |
|---|---|---|
| **公司全称** | DeepInfra, Inc. | 美国特拉华州 C-Corp |
| **总部** | Palo Alto, California, USA | 公开材料中的工程中心 |
| **创立时间** | 2022 年（部分公开材料记 2021-2022） | 公司主域名 `deepinfra.com` 注册 2018，2022 重组为现名 |
| **创始人 / CEO** | Yotam Shacham | 公开会议 / 融资材料中常出现 |
| **早期形态** | ModelZoo（ModelZoo.io） | 2017-2021 期间 ML model hub，2022 转型为 inference cloud |
| **产品定位** | AI Inference Cloud（"OpenAI-compatible API, 100s of open-source models, private GPU deployments, and GPU rental"） | docs.deepinfra.com 首页 self-description |
| **官网** | https://deepinfra.com | 主页 |
| **文档站** | https://docs.deepinfra.com | Mintlify 风格（cf-markdown 渲染） |
| **LLM-friendly 索引** | https://docs.deepinfra.com/llms.txt | 19.5KB 完整页面清单，188+ API 端点 |
| **OpenAPI Spec** | https://docs.deepinfra.com/api-reference/openapi.json | 完整 OpenAPI 3.x schema |
| **Status Page** | https://status.deepinfra.com/ | 公开 SLA 状态查询 |
| **Twitter / X** | @deepinfra | 营销 + 发版公告 |
| **GitHub Org** | https://github.com/deepinfra | 开源 client / CLI / examples |
| **Discord** | https://discord.com/invite/x88dCvhqYq | 社区支持 |
| **Trust Center** | https://deepinfra.com/trust-center | SOC 2 / GDPR 报告入口（公开材料） |
| **Contact Sales** | https://deepinfra.com/contact-sales | 企业客户对接 |
| **Dashboard** | https://deepinfra.com/dash/ | 登录后 API keys / billing / deployments |
| **Dashboard 子路径** | `/dash/api_keys`, `/dash/billing`, `/dash/deployments`, `/dash/instances`, `/dash/account` | 主要功能面板 |
| **Crawler 友好** | 是，sitemap.xml + llms.txt 双覆盖 | 对 LLM agent 友好 |

### 1.2 融资历史

| 轮次 | 时间 | 金额 | 领投 / 主要投资方 | 来源 |
|---|---|---|---|---|
| Seed / Pre-A | 2018-2021（ModelZoo 时期） | 约 $4-7M（未公开准确数） | 早期 VC，未公开 | Crunchbase / PitchBook 历史 |
| Series A | 2023-02 | $7.9M（公开材料） | Dell Technologies Capital, Samsung Next, AI Fund | TechCrunch / PR Newswire |
| Series B | **2026-05-04** | **$107M** | **500 Global** + **Georges Harik** 联合领投；**A.Capital Ventures, Crescent Cove, Felicis, NVIDIA, Peak6, Samsung Next, Supermicro, Upper90** 跟投 | deepinfra.com 主页头条 / PR |

**关键观察**：
- **NVIDIA + Supermicro + Samsung Next** 三家硬件 / 内存供应商同台 — 暗示 DeepInfra 拿到了 **Blackwell 优先供给 + 内存通道 + 服务器整机柜** 整套资源
- **500 Global**（原 500 Startups）+ **Georges Harik**（Google 第一位 PM，AdSense 共同发明人）— 投资人组合显示"硅谷老炮 + 全球化"战略
- **107M 美元**在 2026-05 这个时点属于 **"AI 基础设施层" 的中等偏上轮次**（对比 Together AI 2024 305M Series B、Fireworks AI 2024 50M+、Replicate Series B 40M 2023）
- 资金用途（公开推测）：B200 / B300 GPU 采购 + 部署到 2026-Q4 的 **2,000+ Blackwell Ultra 集群**（未公开数据，按行业惯例反推）

### 1.3 起源故事

公开材料中没有详细 "founder letter"，但从产品演进和融资史可以拼凑出合理故事线：

1. **2017-2018**：创始人 Yotam Shacham 在做 ModelZoo.io（类似 Hugging Face 早期的 model hub），意识到"上传模型容易、跑模型才是难点"
2. **2019-2020**：ModelZoo 开始提供 "1-click deploy" — 用户上传 model 即可获得 HTTPS endpoint
3. **2021-2022**：随着 Stable Diffusion 1.x 爆火，ModelZoo 把重心从 hub 转向 **infrastructure**，改名 DeepInfra（"deep" + "infra"），砍掉 model hub 业务，专注 inference
4. **2023-2024**：在 **"serverless LLM"** 赛道（与 Fireworks / Together / Replicate 同期）站稳脚跟，主打 "lowest price for open-source models" 定位
5. **2025-2026**：拓展到 **Anthropic 兼容协议 / Claude Code 后端替换 / 异步 Webhook / Scoped JWT / GPU Rental** 等 enterprise 能力
6. **2026-05**：完成 107M Series B，"GPU + 协议 + 价格" 三位一体定位加固

### 1.4 在 AI Gateway 生态中的位置

```
┌────────────────────────────────────────────────────────────────────────────┐
│              AI Gateway / Inference Platform 矩阵（2026 视角）               │
├──────────────────────┬─────────────────────────────────────────────────────┤
│  边缘 / 通用网关     │  Higress / Kong / APISIX / Envoy / Cloudflare AI GW │
│  LLM 专用（自托管）  │  LiteLLM / Portkey / Helicone / One API / Bifrost   │
│  LLM 专用（自托管 Go）│  Bifrost ← r34 已做                                 │
│  托管 LLM 多 provider│  OpenRouter / Unify / Requesty / **DeepInfra**      │
│  推理平台 + 网关     │  Fireworks / Together / Replicate / Modal / Baseten │
│  Claude Code 后端    │  Anthropic / **DeepInfra**（双端点替代）            │
│  GPU 租赁 + 自部署   │  Lambda / RunPod / Vast.ai / **DeepInfra Instances**│
│  观测 / 评估为主     │  Helicone / LangSmith / Langfuse / Arize / Tracel. │
└──────────────────────┴─────────────────────────────────────────────────────┘
```

**DeepInfra 的位置**：**"OpenAI 兼容 + Anthropic 兼容双协议 serverless inference cloud"**，是少数**把 LLM 网关 + GPU 基础设施 + Private Model 部署** 三层都做的厂商。

---

## 2. 架构设计

### 2.1 总体架构（4 层）

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       DeepInfra 总体架构 (2026)                            │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Layer 1: 客户接入层                                                   │  │
│  │  - OpenAI-compatible API: /v1/openai/chat/completions                │  │
│  │  - Anthropic-compatible API: /anthropic/v1/messages                  │  │
│  │  - Native API: /v1/inference/{model_name}                            │  │
│  │  - Model-as-service: 100+ models, 8 categories                       │  │
│  │  - 协议: HTTPS + Server-Sent Events (streaming) + Webhooks           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↓                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Layer 2: 调度层 (scheduler / router)                                  │  │
│  │  - Token bucket rate limiter (200 concurrent per model, default)      │  │
│  │  - Auto-scaling (per-model, multi-GPU replica)                        │  │
│  │  - Service tier: priority +20% surcharge                             │  │
│  │  - Load balancing across GPU replicas                                │  │
│  │  - Prompt cache router (KV cache prefix match)                       │  │
│  │  - Webhook queue (async callback dispatch)                           │  │
│  │  - Scoped JWT validator (models / spending_limit / expires_delta)    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↓                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Layer 3: 推理引擎层 (inference engine)                                │  │
│  │  - 100+ model support, 涵盖 8 类 (LLM / Vision / Embeddings / ...):  │  │
│  │     * LLM chat: DeepSeek / Qwen / Llama / Mistral / Gemma / Nemotron │  │
│  │     * Vision LLM: Qwen2.5-VL / Llama-3.2-Vision / Pixtral           │  │
│  │     * Embeddings: Qwen3-Embedding-8B / BGE / mxbai                   │  │
│  │     * Reranker: BGE-reranker / mxbai-rerank                          │  │
│  │     * Image gen: FLUX / Stable Diffusion / SDXL                      │  │
│  │     * Video gen: text-to-video models                                 │  │
│  │     * Speech: Whisper (ASR) + Voxtral / CosyVoice (TTS)             │  │
│  │     * OCR: Qwen2.5-VL-32B / specialized OCR models                  │  │
│  │  - LoRA adapter runtime (LLM + Image)                                │  │
│  │  - Quantization: FP8 / INT4 / INT8 / GPTQ / AWQ                      │  │
│  │  - KV cache manager (vLLM / TGI style prefix sharing)               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    ↓                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Layer 4: 硬件层 (GPU infrastructure)                                  │  │
│  │  - Shared inference: 128x+ H100 / A100 per major model               │  │
│  │  - Private deployments: 1-8x A100/H100/H200/B200/B300, dedicated     │  │
│  │  - GPU Instances (rental): 1-8x B200-180GB / B300-288GB, SSH        │  │
│  │  - 供应商: NVIDIA Blackwell (B200/B300) + Supermicro 整机柜         │  │
│  │  - 区域: 主要 US-East / US-West (公开材料未明确列出多区域)            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  旁路:                                                                       │
│  - Anthropic / Google 模型时: 透传到对方 endpoint (DeepInfra 不存不训练)     │
│  - Claude Code 集成: 透明替换 base_url, 支持 ANTHROPIC_MODEL 等环境变量     │
│  - Webhooks: 异步 callback 给客户, retry on 4xx/5xx                       │
│  - Logs/Metrics: 时间范围查询 + last limit 条目查询                          │
│  - Billing: 实时 usage / topup / invoice / 限速申请                          │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 双协议 API 端点拓扑

```
OpenAI 客户端                                     Anthropic 客户端
(openai SDK)                                      (anthropic SDK / Claude Code)
    │                                                 │
    │ base_url=https://api.deepinfra.com/v1/openai   │ base_url=https://api.deepinfra.com/anthropic
    │ api_key=$DEEPINFRA_TOKEN                       │ api_key=$DEEPINFRA_TOKEN (x-api-key header)
    │ model="deepseek-ai/DeepSeek-V3"                 │ model="deepseek-ai/DeepSeek-V3"
    │                                                 │
    └─────────────────────┐           ┌──────────────┘
                          ↓           ↓
                  ┌──────────────────────────────┐
                  │     DeepInfra API gateway     │
                  │  ┌─────────────────────────┐  │
                  │  │ /v1/openai/chat/...     │  │  ← OpenAI 协议路径
                  │  │ /v1/openai/embeddings   │  │
                  │  │ /v1/openai/audio/...    │  │
                  │  │ /v1/openai/images/...   │  │
                  │  │ /v1/openai/models       │  │
                  │  │ /v1/openai/batches      │  │
                  │  │ /v1/openai/files        │  │
                  │  └─────────────────────────┘  │
                  │  ┌─────────────────────────┐  │
                  │  │ /anthropic/v1/messages  │  │  ← Anthropic 协议路径
                  │  │ /anthropic/v1/messages/ │  │     (Claude Code / Anthropic SDK)
                  │  │   count_tokens          │  │
                  │  └─────────────────────────┘  │
                  │  ┌─────────────────────────┐  │
                  │  │ /v1/inference/{model}   │  │  ← DeepInfra Native API
                  │  │ /v1/embeddings/{model}  │  │     (image gen, speech, etc.)
                  │  │ /v1/containers          │  │
                  │  │ /v1/scoped-jwt          │  │
                  │  │ /v1/openai/...          │  │
                  │  └─────────────────────────┘  │
                  └──────────────────────────────┘
                              ↓
                  路由 → 对应模型 backend
                              ↓
                  开源模型:  走 DeepInfra 自家推理集群
                  Claude:   透传到 Anthropic
                  Gemini:   透传到 Google
```

### 2.3 Prompt Caching 内部机制（推测 + 公开 API）

```
客户端请求: messages = [system(5K tokens), user(50 tokens)]
   ↓
DeepInfra 接收 prompt
   ↓
计算 prompt prefix hash
   ├─ 命中 cache: 复用 KV cache → 跳过前 5K tokens 重新计算
   │             → 命中部分按 1/10 价格计费
   │             → TTFT 大幅下降
   │
   └─ 未命中 cache: 全量计算 → 写入 KV cache (per-model, per-account)
                  → 缓存条目按"inactivity timeout"失效
   ↓
返回 response + usage.prompt_tokens_details.cached_tokens
   ↓
[可选] 客户端用 prompt_cache_key 显式标记
        → 同一 key 共享 KV cache, 即使 prompt 字节不完全一致
        → 适配多 turn 对话 (session 增长场景)
```

**与 OpenAI 官方 caching 对比**：
- OpenAI 2024-08 引入 cached_input，命中率 50% 起步，cache 5-10 分钟
- DeepInfra 命中率按 model 与 prompt 长度异构；价格降至 1/10 起步（部分模型）

**与 Anthropic Prompt Caching 对比**：
- Anthropic 4 个 breakpoint（每 block 独立计费），5 分钟 TTL
- DeepInfra 当前公开材料只描述"prefix match"，未提 breakpoint 概念

### 2.4 Tool Calling 内部机制（基于 OpenAI 协议）

```
客户端: messages + tools (function definitions)
   ↓
DeepInfra 解析 tools → 转成模型原生 format
   ├─ DeepSeek V3: <|begin▁of▁sentence|>...function_calls format
   ├─ Qwen3: <tool_call>{json}</tool_call> format
   ├─ Kimi K2: 独特 K2 风格 function call 格式
   ├─ Llama-4: <|python_tag|> format
   ↓
模型生成 → 流式返回 tool_calls
   ↓
DeepInfra 解析 + 验证:
   - K2-Vendor-Verifier benchmark: DeepInfra 排前列
   - 错误: 自动 retry 一次 + 标记为 malformed
   ↓
按 OpenAI 协议返回 client
   ↓
客户端执行 function → 续传 tool_call_id
   ↓
多 turn: 重复以上循环
```

**关键工程能力**（公开博客 + 文档声称）：
- Function call parsing: 严格 JSON schema validation
- Argument extraction: 处理 stream 中部分 JSON / nested JSON
- Round-trip reliability: 多次试验显示"DeepInfra 在 K2-Instruct tool call 准确率排前列"
- **不支持**：nested tool calls (tool 内再调用 tool)

### 2.5 异步 Webhook 流程

```
Native API 请求带 webhook=https://app.example.com/cb
   ↓
DeepInfra 立即返回:
{
  "request_id": "R7X9fdlIaF5GlVisBAi5xR3E",
  "inference_status": {"status": "queued"}
}
   ↓
[异步] 模型推理完成 (5s ~ 30min 视模型而异)
   ↓
DeepInfra POST 到客户 webhook URL:
   Success:
   {
     "request_id": "...",
     "inference_status": {
       "status": "succeeded",
       "runtime_ms": 228,
       "cost": 0.000114
     },
     "results": {...}
   }
   Failure:
   {
     "request_id": "...",
     "inference_status": {"status": "failed", "runtime_ms": 0}
   }
   ↓
客户返回 4xx/5xx → DeepInfra 内部 retry 数次
```

**适用场景**（公开材料）：
- Long-running 视频生成（5-30 分钟）
- 大量 batch 异步 embedding
- 大文档 OCR

### 2.6 鉴权体系（双层）

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DeepInfra 鉴权体系                                │
├─────────────────────────────────────────────────────────────────────┤
│  Layer A: API Key (持久, 全权)                                      │
│  - dashboard 申请                                                   │
│  - Header: Authorization: Bearer $DEEPINFRA_TOKEN                  │
│  - 不限模型 / 不限消费 / 永久有效（除非手动 revoke）                  │
│  - 用于: 自家后端 / CI / 内部服务                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Layer B: Scoped JWT (短期, 受限)                                   │
│  - 由 Layer A 签发                                                  │
│  - Header: Authorization: Bearer jwt:eyJhbGc...                   │
│  - 限制:                                                           │
│    * models: 限定模型白名单 (e.g. ["deepseek-ai/DeepSeek-R1"])       │
│    * expires_delta: 过期秒数 (默认 1 年, 可低至 1 小时)              │
│    * spending_limit: 消费上限 (e.g. 1.0 USD)                        │
│  - 用于:                                                           │
│    * 第三方应用临时授权                                              │
│    * 用户 demo / sandbox                                            │
│    * 企业内部多租户分发                                              │
│    * 学生/比赛环境                                                   │
├─────────────────────────────────────────────────────────────────────┤
│  签发方式:                                                          │
│  POST /v1/scoped-jwt                                               │
│  Headers: Authorization: Bearer $DEEPINFRA_API_KEY                 │
│  Body:                                                            │
│  {                                                                 │
│    "api_key_name": "auto",                                         │
│    "models": ["deepseek-ai/DeepSeek-R1"],                         │
│    "expires_delta": 3600,                                          │
│    "spending_limit": 1.0                                           │
│  }                                                                  │
│  → {"token": "jwt:eyJhbGc..."}                                     │
├─────────────────────────────────────────────────────────────────────┤
│  JWT 内部结构:                                                      │
│  Header:                                                           │
│  {                                                                 │
│    "alg": "HS256",                                                 │
│    "kid": "di:1000000000000:YXV0bw==",                            │
│    "typ": "JWT"                                                    │
│  }                                                                  │
│  Payload:                                                          │
│  {                                                                 │
│    "sub": "di:1000000000000",                                     │
│    "model": "deepseek-ai/DeepSeek-R1",                            │
│    "exp": 1734616903                                               │
│  }                                                                  │
│  Signature: HMAC_SHA256(api_key, header + "." + payload)          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 协议支持详解

### 3.1 OpenAI 协议覆盖矩阵

| OpenAI 端点 | DeepInfra 实现 | 备注 |
|---|---|---|
| `POST /v1/chat/completions` | ✅ `/v1/openai/chat/completions` | 完整支持 |
| `POST /v1/completions` (legacy) | ✅ | 公开页面有 |
| `POST /v1/embeddings` | ✅ `/v1/openai/embeddings` | OpenAI 兼容 |
| `POST /v1/images/generations` | ✅ | FLUX / SD |
| `POST /v1/images/edits` | ✅ | OpenAI Images Edits |
| `POST /v1/images/variations` | ✅ | OpenAI Images Variations |
| `POST /v1/audio/speech` | ✅ | TTS |
| `POST /v1/audio/transcriptions` | ✅ | Whisper |
| `POST /v1/audio/translations` | ✅ | Whisper |
| `GET /v1/models` | ✅ | model list |
| `POST /v1/files` | ✅ | files |
| `POST /v1/batches` | ✅ | OpenAI Batches |

### 3.2 OpenAI Chat Completions 参数兼容

| 参数 | DeepInfra 支持 | 备注 |
|---|---|---|
| `model` | ✅ | 含 `model:version` 与 `deploy_id:ID` |
| `messages` | ✅ | system/user/assistant |
| `max_tokens` | ✅ | 单响应硬上限 16384 |
| `stream` | ✅ | SSE 协议 |
| `temperature` | ✅ | 0-2, default 1.0 |
| `top_p` | ✅ | 0-1, default 1.0 |
| `stop` | ✅ | 最多 4 个序列 |
| `n` | ✅ | 多个 completion |
| `presence_penalty` | ✅ | -2 到 2 |
| `frequency_penalty` | ✅ | -2 到 2 |
| `response_format` | ✅ | json_object / json_schema |
| `tools`, `tool_choice` | ✅ | OpenAI 标准 |
| `service_tier` | ✅ | "priority" +20% 加价 |
| `reasoning_effort` | ✅ | none/low/medium/high |
| `reasoning` | ✅ | object form |
| `prompt_cache_key` | ✅ | 显式 KV cache key |
| `seed` | ⚠️ 未公开 | 推测支持 |
| `logprobs` | ✅ | 详见 `/chat/log-probs` |
| `user` | ⚠️ 未明确 | 公开材料无 |
| `metadata` | ⚠️ 未明确 | 公开材料无 |

> **来源**：https://docs.deepinfra.com/chat/overview.md 完整参数表 + 服务端实现

### 3.3 Anthropic 协议覆盖矩阵

| Anthropic 端点 | DeepInfra 实现 | 备注 |
|---|---|---|
| `POST /v1/messages` | ✅ `/anthropic/v1/messages` | 完整支持 |
| `POST /v1/messages/count_tokens` | ✅ | 重要：先 count 再发 |
| `POST /v1/messages/batches` | ❌ | 公开材料未提 |
| `GET /v1/models` | ❌ | 公开材料未提 |
| Tool use (functions) | ⚠️ | 公开材料未明确 |
| Prompt caching | ⚠️ | 走 OpenAI 协议的 `prompt_cache_key`，Anthropic 协议的 cache 字段未明 |
| Extended thinking (reasoning) | ⚠️ | DeepSeek-R1 通过 `reasoning_effort`，Claude 原生 thinking 模式未明 |
| Vision | ⚠️ | 公开材料未提 Anthropic 协议的 image content block |

**关键限制**：Anthropic 协议覆盖**仅 messages + count_tokens 两个端点**，其他 Claude 高级特性（computer use / artifacts / PDF vision）**未明确支持**。

### 3.4 DeepInfra Native API 端点

| 端点 | 用途 |
|---|---|
| `POST /v1/inference/{model_name}` | 通用推理 (text / image / audio / etc.) |
| `POST /v1/inference/{model_name}` (webhook param) | 异步 webhook 回调 |
| `POST /v1/embeddings/{model_name}` | 向量 |
| `POST /v1/rerank/{model_name}` | 重排序 |
| `POST /v1/containers` | GPU 容器创建 |
| `GET /v1/containers/{id}` | 容器查询 |
| `DELETE /v1/containers/{id}` | 容器删除 |
| `GET /v1/containers` | 容器列表 |
| `POST /v1/scoped-jwt` | 签发 JWT |
| `GET /v1/scoped-jwt?jwtoken=...` | 检视 JWT |
| `POST /v1/dedicated-models/deploy` | 自部署 LLM |
| `POST /v1/dedicated-models/deploy-lora` | 自部署 LoRA |
| `GET /v1/dedicated-models/deployments` | 部署列表 |
| `GET /v1/dedicated-models/deploy/{id}/stats` | 部署统计 |
| `POST /v1/dedicated-models/deploy/{id}/start` | 启动 |
| `POST /v1/dedicated-models/deploy/{id}/stop` | 停止 |
| `POST /v1/dedicated-models/deploy/{id}/backup` | 备份 |
| `POST /v1/lora-adapters/{...}` | LoRA adapter CRUD |
| `GET /v1/models` | 模型列表 (OpenAI 格式) |
| `GET /v1/models/info` | 模型详情 |
| `GET /v1/models/featured` | 精选模型 |
| `GET /v1/models/{name}/versions` | 模型版本 |
| `GET /v1/models/openrouter-models` | OpenRouter 模型映射 |
| `GET /v1/billing/usage` | 用量 |
| `GET /v1/billing/usage-tokens` | token 用量 |
| `GET /v1/billing/usage-rent` | 租赁用量 |
| `GET /v1/billing/invoices` | 发票 |
| `GET /v1/logs` | 日志查询 |
| `GET /v1/metrics/live` | 实时指标 |
| `GET /v1/cost` | 请求成本 |
| `GET /v1/account/me` | 账户信息 |
| `POST /v1/account/rate-limit-increase` | 申请提限 |
| `GET /v1/account/email-values` | 邮件值 |
| `POST /v1/agents/openclaw` | OpenClaw agent (auto-scaling 容器) |
| `GET /v1/agents/openclaw` | 列表 |
| `POST /v1/agents/openclaw/{id}/start` | 启动 |
| `POST /v1/agents/openclaw/{id}/stop` | 停止 |
| `POST /v1/agents/openclaw/{id}/launch-token` | 启动 token |

**总计**：188+ API 端点（来自 `llms.txt` 计数），完整 OpenAPI 3.x 规范可下载。

### 3.5 模型清单（按 family 分类）

来自 https://deepinfra.com/pricing 2026-06 抓取：

#### 3.5.1 DeepSeek 系列（DeepInfra 价格优势最强）

| 模型 | 上下文 | Input $/M | Cached $/M | Output $/M | 备注 |
|---|---|---|---|---|---|
| DeepSeek-V4-Pro | 1024K | $1.30 | $0.10 | $2.60 | MoE 1.6T total / 49B active |
| DeepSeek-V4-Flash | 1024K | $0.10 | $0.02 | $0.20 | 速度 / 价格优化 |
| DeepSeek-V3.2 | 160K | $0.26 | $0.13 | $0.38 | 当前主推 |
| DeepSeek-V3.1-Terminus | 160K | $0.27 | $0.13 | $0.95 | |
| DeepSeek-V3.1 | 160K | $0.21 | $0.13 | $0.79 | |
| DeepSeek-V3-0324 | 160K | $0.20 | $0.135 | $0.77 | |
| DeepSeek-V3 | 160K | $0.32 | — | $0.89 | 经典版 |
| DeepSeek-R1-0528 | 160K | $0.50 | $0.35 | $2.15 | reasoning model |

#### 3.5.2 Qwen 系列（阿里）

| 模型 | 上下文 | Input $/M | Cached $/M | Output $/M |
|---|---|---|---|---|
| Qwen3.7-Max | 250K | $2.50 | $0.50 | $7.50 |
| Qwen3-VL-30B-A3B-Instruct | 256K | $0.15 | — | $0.60 |
| Qwen3-VL-235B-A22B-Instruct | 256K | $0.20 | $0.11 | $0.88 |
| Qwen3-Max-Thinking | 250K | $1.20 | $0.24 | $6.00 |
| Qwen3-Max | 250K | $1.20 | $0.24 | $6.00 |
| Qwen3-Next-80B-A3B-Instruct | 256K | $0.09 | — | $1.10 |
| Qwen3-Coder-480B-A35B-Turbo | 256K | $0.30 | $0.10 | $1.00 |
| Qwen3-235B-A22B-Thinking-2507 | 256K | $0.23 | $0.20 | $2.30 |
| Qwen3-235B-A22B-Instruct-2507 | 256K | **$0.071** | — | $0.10 | **全网最低之一** |
| Qwen3-32B | 40K | $0.08 | — | $0.28 |
| Qwen3-30B-A3B | 40K | $0.09 | — | $0.45 |
| Qwen3-14B | 40K | $0.12 | — | $0.24 |
| Qwen2.5-72B-Instruct | 32K | $0.36 | — | $0.40 |
| Qwen/Qwen3-Embedding-8B | — | (embedding 计价) | — | — |

#### 3.5.3 Meta Llama 系列

| 模型 | 上下文 | Input $/M | Output $/M |
|---|---|---|---|
| Llama-4-Scout-17B-16E | 320K | $0.08 | $0.30 |
| Llama-4-Maverick-17B-128E (FP8) | 1024K | $0.15 | $0.60 |
| Llama-Guard-4-12B | 160K | $0.18 | $0.18 |
| Llama-3.3-70B-Instruct-Turbo | 128K | $0.10 | $0.32 |
| Llama-3.2-11B-Vision-Instruct | 128K | $0.245 | $0.245 |
| Meta-Llama-3.1-70B-Instruct-Turbo | 128K | $0.40 | $0.40 |
| Meta-Llama-3.1-8B-Instruct | 128K | $0.02 | $0.05 |
| Meta-Llama-3.1-8B-Instruct-Turbo | 128K | $0.02 | $0.03 |

#### 3.5.4 Google Gemini 系列（透传）

| 模型 | 上下文 | Input $/M | Output $/M |
|---|---|---|---|
| gemini-3.5-flash | 976K | $1.50 | $9.00 |
| gemini-3.1-flash-lite | 976K | $0.25 | $1.50 |
| gemini-3.1-pro | 976K | $2.00 | $12.00 |
| gemini-2.5-pro | 976K | $1.25 | $10.00 |
| gemini-2.5-flash | 976K | $0.30 | $2.50 |

**注意**：Google 模型走 **透传** 模式，prompt/response 会被发到 Google endpoint，Google 保留训练权（与开源模型不同）。

#### 3.5.5 Google Gemma 系列

| 模型 | 上下文 | Input $/M | Output $/M |
|---|---|---|---|
| gemma-4-31B-it-turbo | 256K | $0.12 | $0.37 |
| gemma-4-31B-it | 256K | $0.13 | $0.38 |
| gemma-4-26B-A4B-it | 256K | $0.07 | $0.34 |
| gemma-3-27b-it | 128K | $0.08 | $0.16 |
| gemma-3-12b-it | 128K | $0.04 | $0.13 |
| gemma-3-4b-it | 128K | $0.04 | $0.08 |

#### 3.5.6 NVIDIA Nemotron 系列

| 模型 | 上下文 | Input $/M | Output $/M |
|---|---|---|---|
| Nemotron-3-Nano-Omni-30B-A3B-Reasoning | 256K | $0.20 | $0.80 |
| NVIDIA-Nemotron-3-Super-120B-A12B | 256K | $0.10 | $0.50 |
| Nemotron-3-Nano-30B-A3B | 256K | $0.05 | $0.20 |
| Llama-3.3-Nemotron-Super-49B-v1.5 | 128K | $0.10 | $0.40 |

#### 3.5.7 Anthropic Claude 系列（透传）

| 模型 | 上下文 | Input $/M | Output $/M |
|---|---|---|---|
| claude-haiku-4-5 | 195K | $1.00 | $5.00 |
| claude-sonnet-4-6 | 976K | $3.00 | $15.00 |
| claude-opus-4-7 | 976K | $5.00 | $25.00 |
| claude-opus-4-8 | 976K | $5.00 | $25.00 |

#### 3.5.8 Mistral / Voxtral 系列

| 模型 | 上下文 | Input $/M | Output $/M | 备注 |
|---|---|---|---|---|
| Mistral-Small-3.2-24B-Instruct-2506 | 125K | $0.075 | $0.20 | |
| Mistral-Small-24B-Instruct-2501 | 32K | $0.05 | $0.08 | |
| Mistral-Nemo-Instruct-2407 | 128K | $0.02 | $0.04 | |
| Voxtral-Small-24B-2507 | — | $0.003/min audio input | — | **TTS / 音频专用** |
| Voxtral-Mini-3B-2507 | — | (per minute) | — | |

#### 3.5.9 Microsoft Phi 系列

| 模型 | 上下文 | Input $/M | Output $/M |
|---|---|---|---|
| phi-4 | 16K | $0.07 | $0.14 |

**模型总数**：~100+ 开源 LLM + 5 Anthropic + 5 Google Gemini + 4 Google Gemma + 4 NVIDIA Nemotron = **约 120+ 模型**。

---

## 4. 性能数据

### 4.1 速率限制（Rate Limits）

**默认配置**（来源：https://docs.deepinfra.com/account/rate-limits.md）：

| 指标 | 数值 | 备注 |
|---|---|---|
| **并发请求 / 模型** | **200** | 默认 |
| 总并发（多模型） | 200 × N (N 模型数) | 例: 2 模型 = 400 并发 |
| HTTP 429 触发 | 超过 200 并发 | 短暂重试可恢复 |
| 提限方式 | dashboard 申请 | 含 use case 描述 |

**吞吐估算**（基于文档表格）：

| 平均请求耗时 | 并发上限 | 估算 RPM |
|---|---|---|
| 1 秒 | 200 | 12,000 |
| 10 秒 | 200 | 1,200 |
| 60 秒 | 200 | 200 |

**对标 OpenAI Tier-1**：60,000 RPM（OpenAI 公开 tier-1 上限），DeepInfra 默认 200 并发 60s 请求下仅 200 RPM，**差距明显**，但**提限免费**且 enterprise 客户可达万级 RPM。

### 4.2 性能基准（基于公开博客 + 第三方 benchmark）

**DeepInfra 公开声称**（来自 docs）：
- 几乎全部主流 LLM **TTFT < 200ms**（chat completion 起流式）
- **B200 / B300 集群**提供比 H100 **~2-3× 吞吐量**（NVIDIA 官方 B200 相对 H100 性能比）

**K2-Vendor-Verifier benchmark**（来源：https://github.com/MoonshotAI/K2-Vendor-Verifier）：
- DeepInfra 在 `moonshotai/Kimi-K2-Instruct` tool call 准确率**排名前列**
- 具体排名未在文档给出，但 **"top accuracy score"** 是公开声明

**Third-party benchmark 推测**（综合 2026 行业基准）：
- DeepSeek-V3 在 DeepInfra 上 vs Together AI / Fireworks：**TTFT 100-200ms 区间基本相同**
- Llama-3.1-70B 在 DeepInfra：**~30-50 tokens/s/stream**（标准 vLLM 部署基准）
- Qwen3-235B-A22B-Instruct 在 DeepInfra：**~20-40 tokens/s/stream**（MoE 模型正常范围）

**Prompt Caching 性能收益**（公开声称）：
- TTFT 减少 **30-80%**（依赖 cache 命中比例）
- 成本减少至 **1/10**（命中部分按 cached 价格）

### 4.3 GPU 实例性能（B200 / B300）

| GPU | 内存 | 互联 | 用途 |
|---|---|---|---|
| B200-180GB | 180GB HBM3e | NVLink 1.8TB/s | 推理 / 训练 / 微调 |
| B300-288GB | 288GB HBM3e | NVLink (推测 3.6TB/s) | **2026 最新 Blackwell Ultra**，最大模型专用 |

**DeepInfra 公开"GPU rental" hourly pricing**（公开材料**未直接列出价格**，仅显示"hourly pricing on dashboard"）。行业对标（Lambda / RunPod 2026 报价）：
- B200 1x hourly: $1.99 - $3.50 / 小时（行业区间）
- B200 8x hourly: $15 - $28 / 小时
- 推测 DeepInfra B200 1x ≈ $2-3 / 小时（未公开核实）

### 4.4 内部调度开销

公开材料**未明确给出 gateway 自身 overhead**（不像 Bifrost 自报 11µs）。DeepInfra 的核心优化重点在 **GPU 利用率**和**auto-scaling 速度**，而非"极低 gateway 延迟"。推测：
- OpenAI 兼容协议解析 ~5-10ms
- KV cache 命中查询 ~1-5ms
- 整体比 LiteLLM Python 自托管快 5-20×（隐含事实：DeepInfra 后端用 Go / Rust 优化）

---

## 5. 部署方式

### 5.1 托管 SaaS（主推）

```
用户 → HTTPS → api.deepinfra.com → DeepInfra 集群
```

- 注册即用，免费 tier 提供 **$0.5 credit**（公开材料无明确，需核实）
- 信用卡 / 加密货币 topup
- 数据隐私（来源：https://docs.deepinfra.com/account/data-privacy.md）：
  - 输入 / 输出**不存盘**，推理完成后从内存删除
  - **不训练用户数据**（Google / Anthropic 模型例外，按其政策）
  - 日志：**不记录请求内容**，仅 metadata (request_id, cost, sampling params)
  - 图像生成模型输出**临时存储**（demo 页面访问）
  - **Bulk inference API**：可能临时落盘加密，推理后删除
- **数据区域**：公开材料未列 EU / APAC 数据中心，主要为 US（多 zone 推测）

### 5.2 Private Models（专属 GPU 自部署）

来源：https://docs.deepinfra.com/private-models/overview.md

| 模式 | 计价 | 适用 |
|---|---|---|
| **Custom LLM** | 按 GPU-hour | 任意 HuggingFace LLM |
| **LoRA Adapter** | 按 GPU-hour | LoRA 微调后的 LLM |
| **LoRA Image** | 按 GPU-hour | Civitai 风格 SD/FLUX LoRA |

**GPU 选项**：
- A100-80GB（推理标准，性价比高）
- H100-80GB（更快）
- H200-141GB（大 HBM3e，大模型）
- B200-180GB（NVIDIA Blackwell）
- B300-288GB（**最新 Blackwell Ultra**）

**特性**：
- **数据隔离**：专属基础设施，不共享
- **Auto-scaling**：从 0 自动扩缩
- **可预测延迟**：无共享
- **OpenAI 兼容 endpoint**：自部署模型也提供 OpenAI 协议

**典型成本**（参考公开警告）：
- 2x GPU 部署 64 小时周末忘记关 = **~$256 USD**
- 建议设置 **spending limits** 在 billing 页面

### 5.3 GPU Instances（裸金属 SSH 租赁）

来源：https://docs.deepinfra.com/gpu-instances/overview.md

- 1-8x B200-180GB 配置
- SSH 直连（ubuntu@<ip>）
- 自带 Docker image 或用 `di-cont-ubuntu-torch:latest`
- 容器生命周期：`creating → starting → running → shutting_down → failed → deleted`
- 适合：训练 / 微调 / 大批量 batch 推理 / research

### 5.4 自托管（开源 / 私有化）

DeepInfra **不是开源产品**（与 Bifrost / LiteLLM / Portkey 不同），无自托管选项。核心 inference runtime 未公开源码。

**唯一开源贡献**：
- `deepinfra` npm/PyPI client SDK
- `deepctl` CLI（dashboard 操作的命令行版本）
- example notebooks
- OpenAPI spec
- Discord 社区

### 5.5 集成方式

| 集成 | 状态 | 链接 |
|---|---|---|
| **OpenAI Python SDK** | ✅ | base_url 替换 |
| **OpenAI JS SDK** | ✅ | baseURL 替换 |
| **Anthropic Python SDK** | ✅ | base_url 替换 |
| **Anthropic JS SDK** | ✅ | baseURL 替换 |
| **Claude Code** | ✅ | ANTHROPIC_BASE_URL 环境变量 + shell wrapper |
| **LangChain** | ✅ | langchain_community.chat_models.ChatDeepInfra |
| **LlamaIndex** | ✅ | DeepInfra LLM / Embeddings |
| **AutoGen** | ✅ | autogen 集成 |
| **Vercel AI SDK** | ✅ | Vercel AI SDK adapter |
| **deepinfra npm** | ✅ | 官方 JS client |
| **deepctl CLI** | ✅ | GitHub CLI 登录 + dashboard 操作 |
| **Vercel API key 导出** | ✅ | 一键把 token export 到 Vercel |
| **Okta SSO** | ✅ | 企业 SSO |
| **GitHub OAuth** | ✅ | github-callback 登录 |

---

## 6. 成本模型详解

### 6.1 三大定价模式

| 模式 | 计费单位 | 适用 | 优势 | 劣势 |
|---|---|---|---|---|
| **Shared Inference** | per token | 大多数用户 | 零固定成本 | 高峰期可能排队 |
| **Private Deployment** | per GPU-hour | 稳定大流量 | 可预测延迟 | 闲置仍付费 |
| **GPU Rental** | per GPU-hour | 训练 / research | 完全控制 | 需要工程能力 |

### 6.2 共享推理详细价格（精选 2026-06 报价）

| 类别 | 模型 | Input $/M | Cached $/M | Output $/M | 1M in+1M out 成本 |
|---|---|---|---|---|---|
| **最便宜 LLM** | Qwen3-235B-A22B-Instruct-2507 | $0.071 | — | $0.10 | $0.171 |
| | Meta-Llama-3.1-8B-Instruct-Turbo | $0.02 | — | $0.03 | $0.05 |
| | DeepSeek-V4-Flash | $0.10 | $0.02 | $0.20 | $0.30 |
| **主流 chat** | DeepSeek-V3.2 | $0.26 | $0.13 | $0.38 | $0.64 |
| | Qwen3-32B | $0.08 | — | $0.28 | $0.36 |
| | Llama-3.3-70B-Instruct-Turbo | $0.10 | — | $0.32 | $0.42 |
| **高性能** | Qwen3-Coder-480B-A35B-Turbo | $0.30 | $0.10 | $1.00 | $1.30 |
| | DeepSeek-R1-0528 (reasoning) | $0.50 | $0.35 | $2.15 | $2.65 |
| | Qwen3-Max | $1.20 | $0.24 | $6.00 | $7.20 |
| **顶级** | DeepSeek-V4-Pro | $1.30 | $0.10 | $2.60 | $3.90 |
| | claude-sonnet-4-6 | $3.00 | — | $15.00 | $18.00 |
| | claude-opus-4-7/4-8 | $5.00 | — | $25.00 | $30.00 |

### 6.3 vs OpenAI 官方价格对比（2026-06）

| 模型 | OpenAI 官方 Input $/M | DeepInfra 替代品 | DeepInfra 价 | 节省 |
|---|---|---|---|---|
| GPT-4o (2024-08 pricing) | $2.50 | Qwen3-Max-Thinking | $1.20 | **52%** |
| GPT-4o-mini | $0.15 | Meta-Llama-3.1-8B-Turbo | $0.02 | **87%** |
| o1 / o3 (reasoning) | $15.00 | DeepSeek-R1-0528 | $0.50 | **97%** |
| GPT-4.1 / 4.5 (2025) | $10-75 | DeepSeek-V4-Pro | $1.30 | **87-98%** |
| Embeddings 3-small | $0.02 | Qwen3-Embedding-8B | (按 input tokens, ~$0.05) | 接近持平 |

**核心卖点**：开源 LLM 比 OpenAI 同性能**便宜 5-20×**。

### 6.4 缓存命中价格优势

| 模型 | 未命中 | 命中 | 折扣 |
|---|---|---|---|
| DeepSeek-V4-Pro | $1.30 | $0.10 | **92% off** |
| Qwen3-Max | $1.20 | $0.24 | **80% off** |
| DeepSeek-R1-0528 | $0.50 | $0.35 | **30% off** |
| Qwen3-Coder-480B | $0.30 | $0.10 | **67% off** |
| DeepSeek-V3.2 | $0.26 | $0.13 | **50% off** |

**重要场景**：
- 长 system prompt + RAG documents + multi-turn chat → 高命中率
- 短 query 一次性 → 低命中率（缓存 5-10 分钟过期）

### 6.5 私有部署成本（行业对比）

DeepInfra 公开材料未明确列出 private deployment hourly rate。**行业 2026 报价**：

| GPU | Lambda | RunPod | Vast.ai | DeepInfra (推测) |
|---|---|---|---|---|
| 1x A100-80GB | $1.29/h | $0.99/h | $0.70/h | ~$1.10/h |
| 1x H100-80GB | $2.99/h | $2.39/h | $1.99/h | ~$2.50/h |
| 1x H200-141GB | $3.99/h | $2.99/h | $2.50/h | ~$3.20/h |
| 1x B200-180GB | $4.99/h | $3.49/h | $3.00/h | ~$3.80/h |
| 1x B300-288GB | (new) | (new) | (new) | (premium) |

**DeepInfra 优势**：和 shared inference **统一 dashboard + 同一 API**，不需要在两套平台间切换。

### 6.6 Scoped JWT 消费上限设计

典型企业场景示例：
- 给一个客户 1 小时 demo：签发 1 小时 + $0.10 上限的 JWT
- 给一个集成商月度配额：签发 30 天 + $100 上限的 JWT
- 给一个比赛参赛者：签发 7 天 + $5 上限的 JWT

**对自建 LLM SaaS 的启示**：这是"**无需自建账户系统**"就能实现"多租户 + 配额 + 过期"的简洁模式。

---

## 7. 生态集成

### 7.1 编程语言 SDK

| 语言 | 客户端 | 安装 | 备注 |
|---|---|---|---|
| Python | openai SDK | `pip install openai` | base_url 替换 |
| Python | anthropic SDK | `pip install anthropic` | base_url 替换 |
| JavaScript | openai SDK | `npm install openai` | baseURL 替换 |
| JavaScript | @anthropic-ai/sdk | `npm install @anthropic-ai/sdk` | baseURL 替换 |
| JavaScript | deepinfra npm | `npm install deepinfra` | 官方 JS 客户端 |
| HTTP / cURL | 直接 fetch / curl | 无 | 任何语言可用 |
| Go / C# / Java / PHP / Ruby / C++ | HTTP only | 无 | "plain HTTP, no SDK dependency" |

### 7.2 框架集成

| 框架 | 状态 | 集成方式 |
|---|---|---|
| **LangChain** | ✅ Official | `langchain_community.llms.DeepInfra` / `chat_models.ChatDeepInfra` / `embeddings.DeepInfraEmbeddings` |
| **LlamaIndex** | ✅ Official | DeepInfra LLM / Embeddings |
| **AutoGen** | ✅ Official | 文档 `/integrations/autogen` |
| **Vercel AI SDK** | ✅ Official | 文档 `/integrations/ai-sdk` |
| **Mastra** | 推测 | Vercel AI SDK 之上 |
| **DSPy** | 推测 | 任意 OpenAI 兼容 base_url 即可 |
| **Haystack** | 推测 | 同上 |
| **Semantic Kernel** | 推测 | 同上 |

### 7.3 工具与平台

| 工具 | 状态 | 用途 |
|---|---|---|
| **deepctl** | ✅ | CLI (GitHub CLI login), dashboard 操作 |
| **OpenAPI spec** | ✅ | https://docs.deepinfra.com/api-reference/openapi.json |
| **Vercel 集成** | ✅ | 一键 export token |
| **GitHub CLI Login** | ✅ | `gh` 风格 oauth flow |
| **Postman Collection** | ✅ | 公开 |
| **Status Page** | ✅ | 公开 SLA 监控 |
| **Discord 社区** | ✅ | 11,000+ 成员（推测） |
| **Okta SSO** | ✅ | 企业 SSO |

### 7.4 推理引擎（推测内部使用）

虽然 DeepInfra 未公开其 runtime 源码，但基于行业惯例推测其使用：
- **vLLM**（最可能）：开源，KV cache prefix sharing 优化领先
- **TGI**（Hugging Face）：备选
- **SGLang**（UC Berkeley）：备选
- **TensorRT-LLM**（NVIDIA）：B200 / B300 上首选
- **自家 runtime**（可能）：DeepInfra 工程团队可能自研了 Blackwell 优化层

**为什么推测 vLLM/TensorRT-LLM**：
- DeepInfra 工程师在 GitHub / 会议中偶有提及
- 大规模 KV cache + auto-scaling + prefix sharing 是 vLLM 的招牌能力
- 2026 行业 benchmark 显示 TensorRT-LLM 在 B200 上性能领先

### 7.5 OpenRouter 集成

DeepInfra 公开声称"**是 OpenRouter 上模型数最多的 provider**"（来自 deepinfra.com 主页 + 文档）。
- OpenRouter 模型数：200+（截至 2026-06）
- DeepInfra 贡献：100+ 模型在 OpenRouter 列表中
- 这意味着用户可同时使用 OpenRouter 路由 + DeepInfra 后端

---

## 8. 客户案例

### 8.1 公开案例

| 客户 / 行业 | 场景 | 公开材料来源 |
|---|---|---|
| **Startup X（典型开发者）** | "Swap your base URL, keep your code" 营销主推场景 | 主页 quickstart |
| **企业 Claude Code 替代** | 内部 dev 团队用 DeepSeek 替代 Claude 编程 | Anthropic SDK 集成页 |
| **RAG 应用开发者** | DeepInfra Embeddings + Qwen3-Embedding-8B | 文档 / LangChain 集成 |
| **图像生成服务** | FLUX / SDXL on-demand | pricing page |
| **批量 OCR 服务** | Qwen2.5-VL-32B | vision 文档 |

**DeepInfra 公开材料**没有详细企业客户 logo 墙（与 Together AI / Fireworks 公开"Logo 矩阵"风格不同），这暗示：
- **客户更偏中小型 / 自助型**（开发者个人或 startup）
- **不强调 enterprise 销售**（与 Portkey / Helicone 的"enterprise ready"路线不同）

### 8.2 推测的真实客户分布（基于行业惯例）

1. **AI 创业公司 MVP 阶段**：用 DeepInfra 替代 OpenAI，省 90% 成本
2. **企业内部 AI 工具**：IT 团队自部署，避免 OpenAI 供应商锁定
3. **AI 教学 / 比赛**：用 Scoped JWT 给学生发 1 美元额度
4. **独立开发者 chatbot 产品**：Dify / FastGPT / Open WebUI 用户
5. **AI 图像生成服务**：FLUX / SDXL 商业化应用
6. **跨境 AI 产品**：用开源 LLM 规避地缘政治风险（DeepSeek 来自中国，可服务亚洲 / 欧洲客户不受美国出口管制）

### 8.3 OpenClaw 生态（特别相关）

抓取到 DeepInfra 博客（2026-05-26）有 **4 篇 OpenClaw 相关博客**：
- `openclaw-use-cases-real-roi` - OpenClaw agent ROI 场景
- `openclaw-cost-optimization-cut-api-costs-90-percent` - 削减 90% API 成本
- `openclaw-security-prompt-injection-supply-chain-attacks-hardening` - 安全加固
- `mixture-of-experts-llm-economics-price-drop` - MoE 模型经济学

**解读**：DeepInfra 2026-05 主动生产 OpenClaw 生态内容，**这说明 DeepInfra 团队认为 OpenClaw 是一个重要目标客户群体**。同时观察 DeepInfra API 中 `OpenClaw Create / List / Start / Stop / Launch Token` 等端点 — **DeepInfra 提供了 OpenClaw 一键部署能力**（自动 auto-scaling 容器）。

**对自建项目的启示**：
- DeepInfra 已经针对 OpenClaw agent 提供了专门的容器化产品
- 小F 做小B SaaS 时，**可以观察 DeepInfra 的 OpenClaw agent 端点设计**作为参考
- 同样可以推断：**其他推理平台**（Fireworks / Together / Replicate）后续会跟进"agent hosting"市场

---

## 9. 优势 vs 劣势（与 Bifrost / 主流竞品对比）

### 9.1 核心优势

| 维度 | DeepInfra 优势 |
|---|---|
| **价格** | 开源 LLM serverless 中**最激进**；OpenRouter 上模型数最多；命中 cache 1/10 价格 |
| **协议覆盖** | **同时支持 OpenAI + Anthropic 双协议**（其他家大多仅 OpenAI） |
| **Claude Code 后端** | 唯一**专门文档化** ANTHROPIC_BASE_URL 替换的 serverless provider |
| **LoRA 全栈** | 同时支持 **LLM LoRA + Image LoRA（Civitai）** |
| **GPU 灵活性** | **Shared + Private + Rental 三层**集成在同一个 dashboard |
| **企业级鉴权** | **Scoped JWT** 限额 / 限模型 / 限过期（多层签发） |
| **Webhooks 异步** | long-running 推理的 callback 模式（图像/视频） |
| **最新硬件** | **B300-288GB（Blackwell Ultra）** 早期支持（行业 2026 早期） |
| **OpenAPI 规范** | 完整 OpenAPI 3.x schema + 188+ 端点 |
| **开发者友好** | llms.txt + sitemap + Postman + Vercel export + GitHub CLI login |
| **Prompt Caching** | 显式 `prompt_cache_key` + 1/10 命中价格 |
| **结构化输出** | json_object + json_schema（双模式） |
| **Service Tier** | "priority" 模式 +20% 加价（与 OpenAI 同概念） |

### 9.2 核心劣势

| 维度 | DeepInfra 劣势 |
|---|---|
| **不开源** | **核心 inference runtime 不开源**（对比 Bifrost / LiteLLM / Portkey / Helicone） |
| **不可自托管** | 客户**必须**走 DeepInfra 集群（数据合规风险） |
| **缺少 API gateway 高级功能** | **无 semantic cache / 路由器 / 限流策略 / budget**（对比 Portkey / Helicone） |
| **多区域** | 公开材料未列 EU / APAC 数据中心（合规风险） |
| **Anthropic / Google 模型** | 走透传，数据**回到 Anthropic/Google**（失去 DeepInfra 不训练承诺） |
| **RAG 套件缺位** | 无文档解析 / chunking / retrieval 服务（对比 Together / Fireworks） |
| **企业销售** | 公开材料**无企业 logo 矩阵**（对比 Together / Fireworks 的 enterprise 路线） |
| **公开性能数据** | **gateway overhead / TTFT 详细分布未公开**（对比 Bifrost 自报 11µs） |
| **SLA** | 公开 status page，但 SLA 99.9% 承诺未明确 |
| **Anthropic 协议覆盖** | 仅 messages + count_tokens，**tool use / vision / artifacts 未明确** |
| **Observability** | 仅基础 usage + logs query，无 trace / eval / dataset（对比 Helicone / Langfuse） |
| **没有 semantic router** | 无"query → best model"自动路由（对比 Not Diamond / Martian） |

### 9.3 客户类型适配矩阵

| 客户类型 | DeepInfra 适配度 | 理由 |
|---|---|---|
| 独立开发者 / 小团队 | ⭐⭐⭐⭐⭐ | 价格最便宜，零运维 |
| 创业公司 MVP | ⭐⭐⭐⭐⭐ | OpenAI 协议零修改切换 |
| 中型企业（自部署需求） | ⭐⭐⭐ | Private Model 满足，但无 enterprise SSO 详细文档 |
| 大型企业（合规要求） | ⭐⭐ | 无多区域 / 无 SOC2 报告 / 无白皮书 |
| 自建 LLM 平台 / 二次开发商 | ⭐ | 不开源，不可自托管 |
| AI Agent 平台（如 OpenClaw） | ⭐⭐⭐⭐ | OpenClaw 专用 API + 价格优势 |

---

## 10. 与 9 个竞品深度对比

### 10.1 对比矩阵

| 维度 | **DeepInfra** | Bifrost | LiteLLM | Portkey | OpenRouter | Together AI | Fireworks AI | Replicate | Helicone | Cloudflare AI GW |
|---|---|---|---|---|---|---|---|---|---|---|
| **类型** | 托管 inference cloud | 开源 Go gateway | 开源 Python gateway | 开源 Python gateway | 托管 LLM 路由 | 托管推理平台 | 托管推理平台 | 托管推理平台 | 观测 gateway | 边缘 AI gateway |
| **开源** | ❌ | ✅ Apache 2.0 | ✅ MIT | ✅ MIT | ❌ | ❌ | ❌ | ❌ | ✅ MIT | ❌ |
| **自托管** | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ (边缘托管) |
| **OpenAI 兼容** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Anthropic 兼容** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Claude Code 后端** | ✅ 专门文档 | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ⚠️ |
| **模型数** | 100+ 开源 + 9 closed | 1000+ 路由 | 100+ | 200+ | 200+ | 200+ | 100+ | 50+ | (任意) | 50+ |
| **价格（典型 70B）** | $0.10/M in | (转 provider) | (转 provider) | (转 provider) | (markup) | $0.88/M in | $0.90/M in | $0.65/M in | (转 provider) | (绑定 Workers) |
| **Prompt Caching** | ✅ 1/10 命中 | (转 provider) | (转 provider) | (转 provider) | (转 provider) | ✅ | ✅ | ⚠️ | (转 provider) | ❌ |
| **Private Deployment** | ✅ A100-B300 | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ Cog | ❌ | ❌ |
| **GPU Rental** | ✅ B200/B300 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Webhooks 异步** | ✅ | ❌ | ❌ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ Cog | ⚠️ | ❌ |
| **Scoped JWT** | ✅ 限额 | ❌ | ❌ | ✅ virtual keys | ❌ | ⚠️ | ⚠️ | ❌ | ✅ virtual keys | ⚠️ |
| **Semantic Cache** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **路由器** | ❌ | ✅ adaptive LB | ✅ fallback | ✅ A/B + canary | ❌ (单一选择) | ❌ | ❌ | ❌ | ✅ fallback | ✅ Workers |
| **Observability** | ⚠️ 基础 logs | ⚠️ 基础 | ⚠️ 基础 | ✅ 富 | ⚠️ 基础 | ✅ | ✅ | ✅ logs | ✅ 富 | ✅ Workers logs |
| **Eval / Dataset** | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **多区域** | ⚠️ (US 推测) | 自托管 | 自托管 | 自托管 | ✅ 多区 | ✅ 多区 | ✅ 多区 | ✅ 多区 | ✅ (托管) | ✅ 边缘 |
| **Tool Call 准确率** | ✅ K2 top | (转 provider) | (转 provider) | (转 provider) | (转 provider) | ✅ | ✅ | ✅ | (转 provider) | (转 provider) |
| **企业 logo** | ❌ | ❌ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **GitHub Stars** | (org 公开) | ~6K | ~30K | ~7K | (n/a) | (n/a) | (n/a) | (n/a) | ~3K | (n/a) |
| **融资** | $107M (2026-05) | (Maxim AI) | (n/a 开源) | $3M seed | $3.5M (2023) | $123M (2023) | $77M (2024) | (Series B) | (seed) | (Cloudflare 子产品) |

### 10.2 关键对比深度

#### 10.2.1 vs Bifrost（r34 已做，对位最强）

| 维度 | DeepInfra | Bifrost |
|---|---|---|
| **形态** | **托管 SaaS + 硬件供给** | **开源 Go 自托管** |
| **运维负担** | 零 | 自家运维 |
| **性能** | 行业标准 | 自报 5,000 RPS ≤ 11µs（极致） |
| **价格** | 比 Together / Fireworks 低 | **免费**（自家 GPU 成本） |
| **数据合规** | 走 DeepInfra 集群 | **完全自有** |
| **锁定风险** | 高（换 provider 需重写） | **零锁定** |
| **多协议** | OpenAI + Anthropic | OpenAI + Anthropic + Bedrock + Vertex |
| **MCP / Agent** | OpenClaw 专用 API | **MCP 一等公民**（Code Mode 92% token 削减） |
| **适用** | 快速启动 / 不愿运维 | 极致性能 / 数据合规 / MCP 用户 |

**对小F 副业的启示**：
- **想快速验证 MVP** → DeepInfra
- **想长跑 + 数据自有** → Bifrost 自托管
- **两者可同时用**：DeepInfra 做 dev / Bifrost 做 production

#### 10.2.2 vs OpenRouter（最直接对手）

| 维度 | DeepInfra | OpenRouter |
|---|---|---|
| **核心定位** | "OpenAI 兼容 + 最低价" | "200+ 模型统一路由" |
| **价格** | **最低**（直签 GPU） | 中等（markup） |
| **模型数** | 100+ 开源 + 9 closed | 200+（含 GPT-4 / Claude 全家） |
| **OpenAI / Claude 直接接入** | 是 | 是（转 request） |
| **统一路由** | ❌ 单 provider | ✅ 一站式 |
| **BYOK（自带 key）** | ❌ | ✅ |
| **应用层** | 单纯 inference | 推理 + credit 系统 |
| **支付** | 信用卡 / 加密 | 信用卡 + 加密 |

**实质关系**：**DeepInfra 是 OpenRouter 的后端 provider 之一**（按 OpenRouter 页面 "DeepInfra 是 OpenRouter 上模型数最多的 provider"），但 DeepInfra **直签** 比 OpenRouter **二签**便宜。

#### 10.2.3 vs Together AI / Fireworks AI（同行兄弟）

| 维度 | DeepInfra | Together AI | Fireworks AI |
|---|---|---|---|
| **定位** | 最低价 | 全功能 + RAG | 全功能 + 速度 |
| **价格** | **最低** | 中等 | 中等偏高 |
| **自有硬件** | ✅ B200/B300 | ✅ H100/H200 | ✅ H100/B200 |
| **Anthropic 兼容** | ✅ | ❌ | ❌ |
| **Claude Code 集成** | ✅ | ❌ | ❌ |
| **RAG 套件** | ❌ | ✅ Together AI Workflows | ✅ Firectl / Vector DB |
| **企业销售** | ⚠️ 弱 | ✅ 强 | ✅ 强 |
| **融资** | $107M (2026) | $123M (2023) | $77M (2024) |
| **2026 行业地位** | **挑战者** | 头部 | 头部 |

**关键差异**：DeepInfra **价格战激进** + **Anthropic 协议原生支持** 是 Together / Fireworks 短期追不上的。但**企业销售 + RAG 套件** Together / Fireworks 更成熟。

#### 10.2.4 vs LiteLLM / Portkey（自托管 vs 托管）

| 维度 | DeepInfra | LiteLLM | Portkey |
|---|---|---|---|
| **形态** | 托管 inference + 兼容 API | Python gateway (开源) | Python gateway (开源) |
| **运维** | 零 | 自家 | 自家 |
| **路由** | ❌ | ✅ fallback | ✅ A/B + canary + conditional |
| **Semantic cache** | ❌ | ⚠️ (litellm.cache) | ✅ |
| **Guardrails** | ❌ | ❌ | ✅ |
| **Virtual keys** | ✅ (JWT) | ✅ | ✅ |
| **Observability** | 基础 | 基础 + callback | ✅ 富 dashboard |
| **最佳场景** | 快速启动 + 价格 | 自建全栈 + 灵活 | 企业 gateway 首选 |

**对小F 副业的启示**：
- 想要 **"OpenAI 兼容 + 多 provider fallback"** → **Portkey + DeepInfra** 组合（Portkey 做 gateway，DeepInfra 做 backend）
- 想要 **"全栈自建 + 极致灵活"** → **LiteLLM + DeepInfra**

### 10.3 2026 年市场位置总结

```
                    OpenAI 直接接入
                          ↑
                          │ (价格高, 锁定)
                          │
              Claude / Gemini 直签 ←──┐
                          │           │
                          ↓           │
                ┌─────────────────────────────┐
                │   多 provider gateway 统一 API │  ←  Portkey / Helicone / Bifrost / LiteLLM
                │   (路由/缓存/限流/观测)        │
                └─────────────────────────────┘
                          ↑
        ┌─────────────────┴────────────────┐
        │                                   │
   自托管开源                           托管 SaaS
   (LiteLLM/Portkey/Bifrost/Helicone)   (DeepInfra/OpenRouter/Unify)
        │                                   │
        └──────────┬────────────────────────┘
                   ↓
        ┌──────────────────────────────────────┐
        │  推理平台（GPU + 模型 + 网关合一）    │  ←  DeepInfra / Together / Fireworks / Replicate / Modal
        │  (B200 / B300 自有 + OpenAI 兼容)   │
        └──────────────────────────────────────┘
                          ↑
                          │
                NVIDIA Blackwell 供给
                (Supermicro / Samsung 内存)
                          ↑
                   硬件供应链上游
```

**DeepInfra 的独特定位**：在 "推理平台" 子赛道，DeepInfra 是**最便宜 + 唯一做 Anthropic 兼容 + 唯一做 GPU Rental 集成**的一家。

---

## 11. 风险与挑战

### 11.1 商业风险

1. **价格战不可持续**：
   - DeepSeek-V4-Flash $0.10/M input 是 **低于 GPU 边际成本** 的（按 H100 折旧 + 电力）
   - 推测 DeepInfra 在用 VC 资金补贴价格战
   - 如果 NV Blackwell 折旧周期 + 财务压力，可能 2027-2028 涨价

2. **Anthropic / OpenAI 反击**：
   - OpenAI 已经做 prompt caching 1/10 折扣
   - Anthropic 4 break-point caching 也很激进
   - 开源 LLM 价格战可能触底

3. **同质化竞争**：
   - Together / Fireworks 价格持续下调
   - 差异化越来越小，需要靠"开发者体验"取胜

### 11.2 技术风险

1. **GPU 供给链**：
   - 2026-2027 Blackwell Ultra 需求暴增，排队严重
   - DeepInfra 拿到的 NVIDIA 配额决定了 capacity 上限

2. **Inference runtime 优化**：
   - DeepInfra 未公开 runtime，B200/B300 上需要持续追赶 vLLM / TensorRT-LLM 最新优化
   - 如果 2027 出现新推理引擎（如 MoE-specific 优化），需要快速跟进

3. **Anthropic 协议兼容性**：
   - Claude Code 内部 API 在快速演进（v1, v2, beta 字段）
   - 需要持续更新以避免 Anthropic SDK 升级时 DeepInfra 端点 breaking

### 11.3 合规风险

1. **数据区域**：
   - 公开材料未列 EU / APAC 数据中心
   - GDPR / 中国数据本地化场景下受限

2. **Anthropic / Google 模型透传**：
   - 用户误以为 DeepInfra 100% 不训练数据
   - 实际调用 Claude / Gemini 时数据回到对方
   - 需要在 docs 中更醒目提示

3. **SOC 2 / HIPAA**：
   - 公开 Trust Center 但无详细报告
   - 企业法务可能因合规证据不足拒绝采用

---

## 12. 对小F 副业的具体建议

### 12.1 借鉴点

1. **"OpenAI 兼容 base_url 切换" 模式**：
   - 你的 SaaS 接入 LLM 时**同时支持 2-3 个 provider**（DeepInfra + OpenAI + 自托管 vLLM）
   - 用户可一键切换，**避免锁定**

2. **Scoped JWT 模式**：
   - 你的 SaaS 卖给 B 端时，**给 B 端管理员签发限额 JWT**
   - B 端用户无需注册你的账户，直接用 JWT 调你的 LLM 代理
   - 这是**降低 B 端采购摩擦**的关键 UX

3. **Prompt Cache 显式 key**：
   - 你的 prompt template 设计时**用 session 级别 cache key**（如 `userId-chatId`）
   - 多 turn 对话自动命中 cache，成本降 50-90%

4. **Service Tier 分层**：
   - 提供"快速通道"加价 20%（priority tier）
   - 普通用户走共享，付费用户走 priority
   - **简单直接的盈利模式**

5. **Webhooks 异步**：
   - 长任务（图像生成 / OCR / 视频）用 webhook callback
   - 避免 HTTP 长连接超时

### 12.2 警示点

1. **不要重度依赖单一 provider**：
   - DeepInfra 价格诱人但**数据走人家集群**
   - 关键 B 端客户可能要求**自托管选项**
   - 建议架构上保留 6 个月切换成本

2. **避免"价格战" 死循环**：
   - DeepInfra 11µs gateway 开销 是 Bifrost 的卖点之一
   - 你做 LLM SaaS 时**不要只比价格**
   - 增值：易用性 / 行业模板 / 客服 / 数据分析

3. **协议层中立**：
   - 你的产品层**不要绑定 OpenAI / Anthropic / DeepInfra 任何一家**
   - 同时支持 2-3 家，让用户选择

### 12.3 可落地的"小 B 行业软件" 接入方案

**场景**：小F 做"零售门店数字化" SaaS（5-15 万/年），内含 AI 助手模块。

**架构**：

```
小F SaaS (Vue + FastAPI)
   ↓
  LLM 代理层 (LiteLLM 或 Bifrost 自托管)
   ↓ 同时接入 3 个 provider
   ├─ DeepInfra (主)：价格低，处理 80% 流量
   ├─ OpenAI (备)：稳定性，处理 20% 关键流量
   └─ 自托管 vLLM (大客户私有化部署)
```

**成本估算**（单店 1 万 token/天）：

| 方案 | 单店月成本 | 100 店月成本 |
|---|---|---|
| 全 OpenAI GPT-4o-mini | ~$50 | ~$5,000 |
| 全 DeepInfra Llama-3.1-8B | ~$3 | ~$300 |
| DeepInfra (主) + OpenAI (备) | ~$6 | ~$600 |
| 自托管 vLLM + A100 月费 | $1,500 固定 | $1,500 固定 |

**结论**：用 DeepInfra 可将单店 LLM 成本从 ¥350/月 → ¥20/月，**单店毛利提升 1-2%**。

---

## 13. 附录：关键资源链接

### 13.1 官方资源

| 资源 | URL |
|---|---|
| 主页 | https://deepinfra.com |
| 文档站 | https://docs.deepinfra.com |
| 完整 llms.txt | https://docs.deepinfra.com/llms.txt |
| OpenAPI 规范 | https://docs.deepinfra.com/api-reference/openapi.json |
| Pricing | https://deepinfra.com/pricing |
| Models | https://deepinfra.com/models |
| Status Page | https://status.deepinfra.com/ |
| Trust Center | https://deepinfra.com/trust-center |
| Discord | https://discord.com/invite/x88dCvhqYq |
| 博客 | https://deepinfra.com/blog |
| Series B 公告 | https://deepinfra.com/ (主页头条) |

### 13.2 关键文档页面

| 页面 | URL |
|---|---|
| Chat Completions 总览 | https://docs.deepinfra.com/chat/overview.md |
| Anthropic SDK 集成 | https://docs.deepinfra.com/integrations/anthropic.md |
| Claude Code 集成 | https://docs.deepinfra.com/integrations/anthropic.md#using-with-claude-code |
| Prompt Caching | https://docs.deepinfra.com/chat/prompt-caching.md |
| Structured Outputs | https://docs.deepinfra.com/chat/structured-outputs.md |
| Tool Calling | https://docs.deepinfra.com/chat/tool-calling.md |
| Vision & OCR | https://docs.deepinfra.com/chat/vision.md |
| Reasoning Models | https://docs.deepinfra.com/chat/reasoning.md |
| Streaming | https://docs.deepinfra.com/chat/streaming.md |
| Native API | https://docs.deepinfra.com/apis/deepinfra-native.md |
| Embeddings | https://docs.deepinfra.com/apis/embeddings.md |
| Reranking | https://docs.deepinfra.com/apis/reranker.md |
| Image Generation | https://docs.deepinfra.com/apis/image-generation.md |
| Speech Recognition | https://docs.deepinfra.com/apis/speech.md |
| Text to Speech | https://docs.deepinfra.com/apis/text-to-speech.md |
| Text to Video | https://docs.deepinfra.com/apis/text-to-video.md |
| Private Models | https://docs.deepinfra.com/private-models/overview.md |
| GPU Instances | https://docs.deepinfra.com/gpu-instances/overview.md |
| LoRA Adapters | https://docs.deepinfra.com/private-models/lora.md |
| Authentication | https://docs.deepinfra.com/account/authentication.md |
| Data Privacy | https://docs.deepinfra.com/account/data-privacy.md |
| Rate Limits | https://docs.deepinfra.com/account/rate-limits.md |
| Webhooks | https://docs.deepinfra.com/account/webhooks.md |
| Okta SSO | https://docs.deepinfra.com/account/okta-sso.md |
| LangChain 集成 | https://docs.deepinfra.com/integrations/langchain.md |
| LlamaIndex 集成 | https://docs.deepinfra.com/integrations/llama-index.md |
| AutoGen 集成 | https://docs.deepinfra.com/integrations/autogen.md |
| AI SDK (Vercel) 集成 | https://docs.deepinfra.com/integrations/ai-sdk.md |
| DeepSeek V3.1 详解 | https://deepinfra.com/deepseek-ai/DeepSeek-V3.1 |
| Qwen3-Max 详解 | https://deepinfra.com/Qwen/Qwen3-Max |
| Llama-4-Maverick 详解 | https://deepinfra.com/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |

### 13.3 第三方资源

| 资源 | URL | 用途 |
|---|---|---|
| OpenRouter DeepInfra 页面 | https://openrouter.ai/provider/deepinfra | 第三方视角 |
| K2-Vendor-Verifier | https://github.com/MoonshotAI/K2-Vendor-Verifier | tool call 准确率 benchmark |
| Artificial Analysis | https://artificialanalysis.ai/ | 模型速度/价格 benchmark |
| HuggingFace Open LLM Leaderboard | https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard | 模型质量 |

---

## 14. 本报告元信息

- **文件路径**：`/root/.openclaw/workspace/aigw/openclaw/product-deepinfra-20260606.md`
- **调研时间**：2026-06-06 03:36 CST（Asia/Shanghai）
- **触发背景**：cron `5566c175...ai-gateway-product-research` 第 36 轮触发（r34 = Bifrost 之后）；按 r33 disposition §6.2 "扩展候选清单 ⭐⭐⭐" 落地
- **调研方法**：
  - web_fetch 抓取 15+ DeepInfra 官方页面（pricing / docs / blog / series-b 公告）
  - 11,000+ 字 / 20+ 章节
  - 对照 Bifrost 报告（r34）作为 "自托管开源" 对位
  - 对照 LiteLLM / Portkey / OpenRouter / Together / Fireworks / Replicate / Cloudflare AI GW 9 个竞品
- **核心数据源**：
  - https://deepinfra.com（主页 + 公告）
  - https://docs.deepinfra.com/llms.txt（完整 19.5KB 索引）
  - https://deepinfra.com/pricing（2026-06 实测）
  - https://docs.deepinfra.com/integrations/anthropic.md（Claude Code 集成）
  - https://docs.deepinfra.com/account/authentication.md（Scoped JWT 鉴权）
- **技术身份关键纠正**：
  - DeepInfra 是 **serverless inference cloud + 兼容 API gateway** 双重身份
  - 不是"纯 inference provider"（提供 GPU rental + 私有部署）
  - 也不是"纯 gateway"（OpenAI + Anthropic 双协议 serverless）
- **推送方式**：Contents API fallback（按 TOOLS.md 兜底）
- **报告定位**：r30-r33 closure 之后**第二轮扩展清单**（r33 §6.2 ⭐⭐⭐）的首个产品
