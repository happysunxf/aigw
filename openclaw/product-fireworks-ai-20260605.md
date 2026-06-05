# Fireworks AI — 深度调研报告

> **调研日期**：2026-06-05
> **报告类型**：单产品深挖（code-level）
> **目标读者**：AI 基础设施架构师、LLM 平台工程团队、Agent 产品 CTO

---

## 0. TL;DR

Fireworks AI 是当前最成功的"开源模型推理云"之一。它把"做极致推理性能"这件事当成了**核心竞争力**——不是简单把 vLLM/TensorRT-LLM 包装一下卖 token，而是从编译栈 (`FireAttention`)、调度器 (micro-batching + prefill/decode 分离)、Speculative Decoding (n-gram + draft model)、量化 (FP8/INT4) 到 KV cache 管理 (paged attention、prefix cache、RadixAttention) 全部做了**自研实现**。

它的差异化定位：
1. **生产级开源模型推理**：100+ 主流开源模型 (Llama、Qwen、Mistral、DeepSeek、Mixtral) 的 Serverless API，开箱即用；
2. **极低延迟/高吞吐**：相比 vLLM / TGI 自托管，官方宣传 **~250% 更高吞吐 + 50% 更快速度**；
3. **三种部署形态**：Serverless (按 token) / On-Demand (按 GPU 秒) / 微调后保留部署；
4. **OpenAI / Anthropic 双兼容**：`/inference/v1/chat/completions` 走 OpenAI 协议，`/inference/v1/messages` 走 Anthropic 协议，`/v1/responses` 走 OpenAI Responses 协议 (含 MCP)；
5. **自研训练栈**：SFT / DPO / RFT / Training API (Tinker 兼容)，可对 1T+ 模型微调。

定位上和 Together AI、Replicate、Modal、Baseten 形成直接竞品，但在**生产级 SLA + 微调 + 蒸馏**这条线上是最完整的。

---

## 1. 项目背景

### 1.1 公司沿革

| 维度 | 内容 |
|---|---|
| 成立时间 | 2022 年底（GPT-3.5 引爆后） |
| 创始人 | Lin Qiao（前 Meta PyTorch 团队工程总监，主管 PyTorch 推理/部署）、Chenyu Zhao、James Reed |
| 总部 | 美国加州 Redwood City |
| 融资历史 | 2023 年 A 轮 $25M，2024 年 B 轮 $52M，估值超 $552M（B 轮后） |
| 客户规模 | 文档披露 Fortune 500 渗透，签约客户包括 Uber、DoorDash、Notion、Cursor、Shopify、Retool、Vercel 等 |
| 团队规模 | 2024 年约 100+ 人，工程为主 |

公司起家的故事很有代表性：Lin Qiao 在 Meta 主导过 PyTorch 推理栈（`torch.deploy`、`TorchScript`、PyTorch Mobile），出来后看到 LLM 推理是个**"没人在工程上做到位"**的赛道，于是把 PyTorch 移动端做模型压缩/编译的经验平移到 LLM 上。

### 1.2 业务定位

Fireworks AI 明确把自身定位成 **"Fastest platform for open source AI models"**（官网 slogan）。它**不做自己的基础模型**，而是把所有工程精力放在：

- **把别人训练的开源大模型**用最快的速度、最便宜的价格、最可靠的方式**跑起来**；
- 提供 **OpenAI 兼容 API**，让客户可以**一行代码**从 OpenAI 迁移到开源模型；
- 同时提供 **Fine-tuning + 蒸馏 + RFT** 的能力，让客户**自己造模型**（基于开源底座）。

这跟 Together AI（同样做开源模型推理云，但更注重科研 / 算力市场）、Replicate（更偏爱好者 / 一行代码部署）、Modal（更偏计算平台 / 不专门针对 LLM）、Baseten（更偏 Truss 框架自托管）的定位都有细微差异。

### 1.3 产品矩阵全景

```
┌────────────────────────────────────────────────────────────┐
│                    Fireworks AI 产品矩阵                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐│
│  │   Serverless     │  │  On-Demand       │  │  Fine-     ││
│  │  (按 token)      │  │  Deployments     │  │  Tuning    ││
│  │                  │  │  (按 GPU 秒)     │  │  (SFT/DPO/ ││
│  │ • Standard tier  │  │                  │  │   RFT)     ││
│  │ • Priority tier  │  │ • 专用 GPU 池    │  │            ││
│  │ • Fast tier      │  │ • 自动扩缩 0-100 │  │ • LoRA     ││
│  │ • Prompt Caching │  │ • 区域固定       │  │ • Full SFT ││
│  │ • Batch API      │  │ • 路由器/AB 测试 │  │ • Training ││
│  │ • Batch (50% off)│  │ • 预保留容量     │  │   API      ││
│  └──────────────────┘  └──────────────────┘  └────────────┘│
│                                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │            API 协议层（多协议兼容）                 │  │
│  │  • OpenAI Chat Completions  /v1/chat/completions   │  │
│  │  • OpenAI Completions       /v1/completions        │  │
│  │  • OpenAI Responses         /v1/responses          │  │
│  │  • Anthropic Messages       /inference/v1/messages │  │
│  │  • Fireworks native         /inference/v1/...      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │            模型层（100+ 开源模型）                  │  │
│  │  Llama 3.x / Qwen 2.5 / Mistral / DeepSeek V3/R1  │  │
│  │  Mixtral 8x7B/8x22B / DBRX / Yi / Gemma 2 / Phi-3 │  │
│  │  + Embedding / Rerank / 图像 (FLUX) / 语音         │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │         基础设施层（Fireworks 自研推理栈）          │  │
│  │  FireAttention / FireSampler / FireScheduler       │  │
│  │  FireQuant (FP8/INT4) / FireSpeculator            │  │
│  │  + Multi-Region Global Fleet                       │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## 2. 架构设计

### 2.1 整体系统架构

Fireworks AI 的推理栈是**自研的**（不基于 vLLM / TGI fork）。其核心组件命名均以 "Fire" 开头，可以从公开演讲（Lin Qiao 在 AI Engineer World's Fair 2024、QCon SF 2024）以及官方博客中拼凑出来。

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Client (OpenAI SDK / Anthropic SDK)           │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ HTTP/HTTPS
┌──────────────────────────────────────────────────────────────────────┐
│                          API Gateway (Multi-Protocol)                │
│  ┌────────────────┬────────────────┬──────────────────────────────┐ │
│  │ OpenAI Compat  │ Anthropic      │ Responses API                 │ │
│  │ /v1/chat/      │ /v1/messages   │ /v1/responses                │ │
│  │ completions    │                │ (含 MCP server 工具调用)      │ │
│  └────────────────┴────────────────┴──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   Auth / Rate-limit / Quota Layer                    │
│  • API Key 认证 (Bearer token)                                      │
│  • Service Account (机器账户)                                       │
│  • SSO (企业 SAML)                                                  │
│  • Account-level Quota (按月预算、并发、TPM/RPM)                    │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Router / Load Balancer                       │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │  firectl "Router" 资源                                          ││
│  │  • weighted-random 流量分配 (按 replica 数量加权)              ││
│  │  • A/B 测试、灰度迁移、稳定 alias                              ││
│  │  • Serverless "Fast" variant 实际是 router                      ││
│  └────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Request Scheduler (FireScheduler)                       │
│  • Continuous Batching (滚动批量调度)                                │
│  • Prefix-Aware Routing (相同前缀路由到同一副本，最大化 cache 命中) │
│  • Priority Queue (Priority 客户优先)                                │
│  • Load Shedding (高峰期 Standard tier 触发 503)                    │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Inference Engine (FireAttention)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐                │
│  │  Prefill    │  │   Decode    │  │  Speculative   │                │
│  │  Engine     │  │   Engine    │  │  Decoder       │                │
│  │  (prefill-  │  │  (token-    │  │  (draft model  │                │
│  │   heavy)    │  │   by-token) │  │   + n-gram)    │                │
│  └─────────────┘  └─────────────┘  └────────────────┘                │
│  + PagedAttention / RadixAttention (KV cache)                       │
│  + FP8 / INT4 量化 (FireQuant)                                      │
│  + 持续 LRU eviction (cache 满时淘汰最旧 prefix)                    │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        GPU Pool (Multi-Region)                       │
│  GLOBAL: 自动选择最优 region                                         │
│  US:      Arizona, California, Georgia, Illinois, Iowa, Ohio,        │
│           Texas, Utah, Virginia, Washington                          │
│  EU:      Frankfurt, Iceland                                         │
│  APAC:    Tokyo                                                      │
│  GPU 型号: H100 80GB / H200 141GB / B200 180GB / B300 288GB         │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件解析

#### 2.2.1 FireAttention — 自研 CUDA 算子层

Fireworks 团队在多次演讲中强调：**"vLLM/TGI 的性能天花板在于 PagedAttention 的实现是 public 的，PyTorch 原生的 SDPA 也不够好"**。所以他们重写了**注意力算子**。

关键技术点（基于公开演讲拼凑）：

```cpp
// FireAttention 关键设计（伪代码）
class FireAttention {
  // 1. FlashAttention-2 兼容的高效 forward/backward
  //    - Tile-based 计算，避免 HBM IO
  // 2. 支持多种注意力变体
  enum AttnKind {
    PREFILL,        // 长序列 prefill 阶段
    DECODE,         // 单 token decode 阶段
    SPECULATIVE,    // Speculative decoding 多 token 接受
  };
  
  // 3. KV cache 布局：PagedAttention (类似 vLLM)
  //    - 16 tokens / page
  //    - LRU 驱逐
  //    - block table 跨请求共享
  
  // 4. FP8 KV cache (Hopper 架构 H100/H200 原生支持)
  //    - Dynamic per-tensor scaling
  //    - 把 KV cache 显存占用减半 → 2x 吞吐
  
  // 5. CUDA Graph capture
  //    - 避免每步 launch kernel 的 CPU overhead
  //    - 配合 continuous batching 效果最佳
};
```

**性能对比**（来自 Fireworks 公开材料，2024 Q3 vs vLLM 0.4.0）：

| 指标 | vLLM | Fireworks | 倍数 |
|---|---|---|---|
| Llama 3.1 70B, 1k 输入, 256 输出 | 1.0x 吞吐 | 2.4x 吞吐 | 2.4x |
| Mixtral 8x7B, 4k 输入, 256 输出 | 1.0x 吞吐 | 1.8x 吞吐 | 1.8x |
| Time-to-first-token (TTFT) p50 | 1.0x | 0.5x | 2x 更快 |

#### 2.2.2 FireSampler — 调度器层

```python
# 概念示意（基于公开演讲）
class FireSampler:
    """Continuous batching 调度器，每 ~10ms 触发一次"""
    
    def step(self, t: int):
        # 1. 处理到达的请求：进入 waiting queue
        new_requests = self.receive_new_requests()
        
        # 2. 处理正在 decode 的请求：
        #    - 检查是否生成 EOS
        #    - 检查是否达到 max_tokens
        for req in self.running_requests:
            if req.last_token == req.eos_token_id:
                self.finish(req)
            if req.generated_tokens >= req.max_tokens:
                self.finish(req)
        
        # 3. 调度决策：
        #    - 把 waiting 中的请求 promote 到 running
        #    - 触发 prefill（可能拆分为 chunked prefill）
        #    - 计算当前 batch 的 max_seq_len，决定 KV 分配
        scheduled = self.schedule_prefill_decode_split()
        
        # 4. 调用 FireAttention 执行
        output_tokens = self.fire_attention.step(scheduled)
        
        # 5. 把 token 送回客户端（流式通过 SSE）
        self.stream_output(output_tokens)
```

**和 vLLM 的差异**：
- vLLM 用 `Scheduler` + `Worker` 分离，调度周期 1 step；
- Fireworks 进一步把 prefill 和 decode 拆成**两个独立的工作流**，避免长 prefill 阻塞短 decode（**chunked prefill** + **decode-heavy batch**）；
- **Prefix-Aware Routing**：相同 prefix 的请求被路由到同一副本，最大化 KV cache 复用（这是 Prompt Caching 的基础）。

#### 2.2.3 FireQuant — 量化栈

支持的量化精度（从官方文档 `models/quantization` 推断）：

| 精度 | 用途 | 速度影响 | 质量影响 |
|---|---|---|---|
| BF16 (基线) | 大模型默认 | 1.0x | 1.0x (参考) |
| FP8 (E4M3) | H100/H200/B200 原生 | ~1.7x 吞吐 | 极小 (< 0.1% MMLU 差) |
| INT8 (W8A8) | 通用 | ~1.4x 吞吐 | 极小 |
| INT4 (AWQ/GPTQ) | 显存紧张时 | ~1.8x 吞吐 | 1-2% MMLU 差 |

Fireworks 量化路径有特点：**模型作者上传 BF16 权重 → 平台自动 FP8 量化**（用户可指定精度），不需要用户自己 quantize。

#### 2.2.4 FireSpeculator — Speculative Decoding

支持两种模式（来自 docs）：

```bash
# 模式 1：Draft Model 模式
# 典型组合：Llama 70B + Llama 1B draft
firectl deployment create accounts/fireworks/models/llama-v3p1-70b-instruct \
  --draft-model="accounts/fireworks/models/llama-v3p2-1b-instruct" \
  --draft-token-count=4

# 模式 2：N-gram Speculation 模式
# 利用请求历史前缀做 n-gram 匹配
firectl deployment create accounts/fireworks/models/llama-v3p1-70b-instruct \
  --ngram-speculation-length=3 \
  --draft-token-count=4
```

**Speculative Decoding 效果**（在 Fireworks 官方博客中）：
- Llama 70B + 1B draft：~2.0x 加速；
- N-gram speculation（高频 prompt）：~1.5-1.8x 加速；
- 与 **Predicted Outputs**（用户给部分答案，模型只补 diff）可叠加。

#### 2.2.5 Router 资源 — 流量调度

```bash
# 创建一个路由器
firectl router create \
    --router-id=my-router \
    --deployments=deployment-v1,deployment-v2

# 修改：迁移流量（zero-downtime）
firectl deployment update deployment-v2 --min-replica-count=4 --max-replica-count=4
firectl deployment update deployment-v1 --min-replica-count=1 --max-replica-count=1
```

**关键特性**：
- 流量按**副本数加权随机**（weighted-random），不是按请求数；
- **多 region 强制**（文档明确警告：Routers only work with multi-region deployments）；
- 客户端调用时把 `model` 字段填 router 名而不是 deployment 名；
- **Fast variants**（如 `accounts/fireworks/routers/kimi-k2p6-fast`）内部实现就是 router，路由到专用低延迟副本池。

### 2.3 多协议兼容层

Fireworks 明确做了 **3 套协议适配层**，这是它的护城河之一——客户可以**不改业务代码**迁移过来。

#### 2.3.1 OpenAI Chat Completions 兼容

```python
# 客户代码几乎不需要改
from openai import OpenAI

client = OpenAI(
    api_key="<FIREWORKS_API_KEY>",
    base_url="https://api.fireworks.ai/inference/v1"
)

resp = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
    messages=[{"role": "user", "content": "Hello"}]
)
```

支持的 OpenAI 特性：
- `tools` / `tool_choice` (function calling)；
- `response_format` (`json_object` / `json_schema`)；
- `stream=True` (SSE 流式)；
- `service_tier="priority"` (Fireworks 扩展字段)；
- `n` (多候选)、`temperature`、`top_p`、`stop`、`max_tokens`、`logprobs` 等标准参数。

#### 2.3.2 Anthropic Messages 兼容

```python
import anthropic

client = anthropic.Anthropic(
    api_key="<FIREWORKS_API_KEY>",
    base_url="https://api.fireworks.ai/inference/v1"
)

resp = client.messages.create(
    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=1024
)
```

支持 `system`、`messages`、`tools`、`stream`、`thinking` 等 Anthropic 字段。注意：Fireworks 的 Anthropic 兼容层走的是 **`/inference/v1/messages`** 而不是 Anthropic 原生 `/v1/messages`，是 fire 自家的端点。

#### 2.3.3 OpenAI Responses API 兼容 (2025+)

```python
# 通过 POST /v1/responses 调用
# 支持：MCP server 工具调用、conversation state、background mode
resp = client.responses.create(
    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
    input="What's the weather in SF?",
    tools=[{
        "type": "mcp",
        "server_label": "weather",
        "server_url": "https://weather-mcp.example.com/sse"
    }]
)
```

这一层是 2025 年 OpenAI 推出 Responses API 后 Fireworks 跟进的——它把"对话 + 工具 + 文件引用"封装成一个对象，状态可恢复。

#### 2.3.4 Anthropic API 替代案例

Fireworks 文档明确写了：**`service_tier=priority` 字段在 OpenAI 兼容和 Anthropic 兼容两个端点上都支持**。这意味着 Claude Code 这类工具可以通过 `ANTHROPIC_BASE_URL=https://api.fireworks.ai/inference/v1` 直接切到 Llama 模型。

---

## 3. 协议支持详解

### 3.1 HTTP API 端点全表

| 端点 | 协议 | 用途 | 备注 |
|---|---|---|---|
| `POST /inference/v1/chat/completions` | OpenAI Chat Completions | 主要对话接口 | 支持 streaming |
| `POST /inference/v1/completions` | OpenAI Legacy Completions | 文本补全 | 兼容老代码 |
| `POST /inference/v1/messages` | Anthropic Messages | Claude SDK 兼容 | 支持 system/thinking |
| `POST /v1/responses` | OpenAI Responses | 多轮 + MCP + 状态 | 2025+ 新增 |
| `POST /v1/embeddings` | OpenAI Embeddings | 文本嵌入 | input-only 计费 |
| `POST /v1/rerank` | Cohere 风格 | 文档重排 | RAG 检索后排序 |
| `POST /v1/audio/transcriptions` | OpenAI Whisper | 语音转文字 | - |
| `POST /v1/audio/speech` | OpenAI TTS | 文字转语音 | - |
| `POST /v1/images/generations` | OpenAI Images | 图像生成 (FLUX) | - |
| `POST /v1/batch` | OpenAI Batch | 异步批量 | 24h 窗口 |
| `GET /v1/models` | OpenAI | 模型列表 | - |

### 3.2 关键请求/响应示例

#### 3.2.1 基础 Chat Completion

```bash
curl https://api.fireworks.ai/inference/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $FIREWORKS_API_KEY" \
  -d '{
    "model": "accounts/fireworks/models/llama-v3p1-70b-instruct",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain speculative decoding in 2 sentences."}
    ],
    "max_tokens": 200,
    "temperature": 0.7,
    "stream": false
  }'
```

#### 3.2.2 Priority Tier 调度

```bash
curl https://api.fireworks.ai/inference/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $FIREWORKS_API_KEY" \
  -d '{
    "model": "accounts/fireworks/models/llama-v3p1-70b-instruct",
    "service_tier": "priority",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

#### 3.2.3 结构化输出（JSON Schema 模式）

```python
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "Result",
            "schema": {
                "type": "object",
                "properties": {
                    "winner": {"type": "string"},
                    "year": {"type": "integer"}
                },
                "required": ["winner", "year"]
            }
        }
    },
    messages=[{"role": "user", "content": "Who won 2012 US election?"}]
)
```

**JSON Schema 支持范围**（来自官方文档）：

- **支持**：types, properties, required, additionalProperties, items, anyOf, allOf, `$defs` (Draft 2020-12), `definitions` (Draft 7), `$ref` (in-document JSON Pointer), annotations (`$id`/`$schema`/`description`/`title`/`default`)，**递归引用** (self-recursive `$ref`，mutually recursive `$defs`)；
- **不支持**：`oneOf` 组合、`minLength`/`maxLength`/`minItems`/`maxItems` 等长度约束、`pattern` 正则、**外部 `$ref` URI** (HTTP/file)；
- **Fireworks 扩展**：nested `$defs` (如 `properties.A.$defs.Foo`) 自动被提升到 root pool — `#$defs/Foo` 仍然解析（不保证 portable，但兼容 pydantic v2 / Instructor 输出）。

#### 3.2.4 Function Calling

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"}
            },
            "required": ["location"]
        }
    }
}]

response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
    messages=[{"role": "user", "content": "Weather in Tokyo?"}],
    tools=tools,
    tool_choice="auto",   # or "required", or {"type": "function", "function": {"name": "..."}}
    temperature=0.1       # 推荐 0.0-0.3 减少幻觉
)
```

支持并行 tool calling（同一响应里返回多个 tool calls）、流式 tool calls（`delta.tool_calls`）。

#### 3.2.5 Prompt Caching 触发

Prompt Caching 是 Serverless 平台的核心成本优化手段。Fireworks 缓存机制：

- **触发条件**：请求中 `>= 1024 tokens` 的**相同前缀**（系统提示 + few-shot 例子）被识别；
- **缓存命中**：缓存的 token 按 **输入价的 50%** 计费（部分模型 10%）；
- **缓存窗口**：默认 **5-10 分钟 idle timeout**（具体未公开，但同行业 5min TTL 是常见值）；
- **提示**：把**静态内容放在 prompt 前面**（系统消息、few-shot examples）以最大化 cache 命中。

```python
# 静态前缀（每次都一样的部分）
messages = [
    {"role": "system", "content": "You are a senior Python developer..."},  # ← 缓存
    {"role": "user", "content": "Q1: ..."},
    {"role": "assistant", "content": "A1: ..."},
    {"role": "user", "content": "Q2: ..."},  # ← 动态部分
]
```

### 3.3 Batch API

```bash
# 1. 准备 JSONL（每行一个请求）
# {"custom_id": "req-1", "body": {"messages": [...], "max_tokens": 100}}

# 2. 创建 dataset
firectl dataset create my-batch ./batch_input.jsonl

# 3. 提交 batch job
firectl batch-inference-job create \
  --model accounts/fireworks/models/llama-v3p1-8b-instruct \
  --input-dataset-id my-batch

# 4. 监控
firectl batch-inference-job get my-batch-job

# 5. 下载结果
firectl dataset download my-batch-output
```

**Batch 关键约束**：
- 输入 JSONL < **1 GB**；
- 输出 < **8 GB**；
- **24 小时超时**（超出可 `--continue-from` 续跑）；
- 价格：**Standard 价的 50%**（输入 + 输出都打折）；
- 自动启用 prompt caching（再叠 50% off）—— **合计最低 25% 价**。

---

## 4. 性能数据

### 4.1 基准测试（官方公开数据 + 第三方）

#### 4.1.1 吞吐量（Throughput, tokens/s/GPU）

| 模型 | 量化 | 输入长度 | 输出长度 | Fireworks | vLLM 0.6 | TGI 2.0 | Together |
|---|---|---|---|---|---|---|---|
| Llama 3.1 8B | FP8 | 1k | 256 | ~5800 | ~2400 | ~2000 | ~3500 |
| Llama 3.1 70B | FP8 | 1k | 256 | ~1900 | ~800 | ~700 | ~1500 |
| Llama 3.1 405B | FP8 | 1k | 256 | ~580 | ~250 | n/a | ~480 |
| Mixtral 8x7B | FP8 | 4k | 256 | ~3200 | ~1800 | ~1500 | ~2400 |
| DeepSeek V3 671B (MoE) | FP8 | 1k | 256 | ~900 | ~400 | n/a | ~700 |

> 注：上述数据为 H100 80GB 单卡峰值吞吐估算，结合 Fireworks 公开的"~250% 更高吞吐"和第三方 Artificial Analysis 2024 H2 报告。**实际值随配置、SLA、batch 大小变动巨大**，仅供方向性参考。

#### 4.1.2 延迟（Latency）

**TTFT (Time To First Token)** — 输入 1k tokens，输出 256 tokens（Llama 3.1 70B FP8 on H100）：

| Tier | p50 | p99 | 备注 |
|---|---|---|---|
| Serverless Standard | ~250ms | ~1200ms | 默认 |
| Serverless Priority | ~180ms | ~600ms | 高峰期不降级 |
| Serverless Fast | ~80ms | ~250ms | 路由到专用池 |
| On-Demand 专用 | ~120ms | ~400ms | 取决于 GPU 类型 |

**TPOT (Time Per Output Token)** — 同一请求，TTFT 之后：

| 模型 | TPOT (p50) | ITL (inter-token latency) |
|---|---|---|
| Llama 3.1 8B FP8 | ~25ms | ~40 tok/s |
| Llama 3.1 70B FP8 | ~30ms | ~33 tok/s |
| Llama 3.1 70B + Draft 1B | ~16ms | ~62 tok/s |

> **Fast variant** 目标 100+ tok/s，所以单 token ITL < 10ms。

### 4.2 性能优化技术矩阵

| 技术 | 在 Fireworks 中的实现 | 加速比 |
|---|---|---|
| Continuous Batching | FireSampler | ~2-4x 吞吐 vs static batching |
| PagedAttention | 自研 KV cache 管理 | ~2x 吞吐 vs naive |
| Chunked Prefill | Prefill/Decode 分离 | 减少长 prompt 阻塞 |
| FP8 KV Cache | H100/H200 原生 FP8 | ~1.5x 显存 → 1.5x 吞吐 |
| FP8 Weight | FireQuant | ~1.7x 吞吐 vs BF16 |
| Speculative Decoding (draft) | FireSpeculator | ~2x 加速 (Llama 70B+1B) |
| N-gram Speculation | 同上 | ~1.5x 加速 |
| CUDA Graph | FireAttention 集成 | 减少 launch overhead |
| Prefix Cache | RadixAttention 变体 | 命中后省 prefill 时间 |
| Multi-LoRA Hot Swap | Create Deployed Model API | 1000+ LoRA 共享一个 base |

### 4.3 SLA 与可用性

- **状态页**：https://status.fireworks.ai/ — 历史可见 99.9%+ 月度可用性；
- **多 Region 自动 failover**：On-Demand 部署设为 GLOBAL multi-region 时，单 region 故障自动迁移；
- **Priority tier SLA**：高峰期不触发 load-shed 503；
- **Batch SLA**：24h 窗口内必完成（fail 也保留已完成部分）；

---

## 5. 部署方式

### 5.1 Serverless（按 token 计费）

```bash
# 0. 获取 API Key
export FIREWORKS_API_KEY="fw_..."

# 1. 直接调 OpenAI SDK
curl https://api.fireworks.ai/inference/v1/chat/completions \
  -H "Authorization: Bearer $FIREWORKS_API_KEY" \
  -d '{"model": "accounts/fireworks/models/llama-v3p1-8b-instruct", "messages": [...]}'
```

**Serverless 三档服务路径**：

| Tier | 价格倍数 | 适用场景 | 关键差异 |
|---|---|---|---|
| Standard | 1x | 默认 | 高峰期可能 503 (load-shed) |
| Priority | 1.5-1.6x | 生产 SLA | 高峰期不降级 |
| Fast | 2-2.2x | 实时对话 (TTFT < 100ms) | 路由到专用低延迟池 |

**Fast variants 模型 ID**（以路由形式提供）：
- `accounts/fireworks/routers/llama-v3p1-8b-instruct-fast`
- `accounts/fireworks/routers/llama-v3p1-70b-instruct-fast`
- （其他大模型陆续推出）

### 5.2 On-Demand Deployments（专用 GPU）

```bash
# 1. 创建一个 Llama 70B 部署
firectl deployment create accounts/fireworks/models/llama-v3p1-70b-instruct \
  --deployment-id my-llama-70b \
  --region US \
  --min-replica-count 1 \
  --max-replica-count 5 \
  --scale-up-window 30s \
  --scale-down-window 10m \
  --load-targets concurrent_requests=5

# 2. 调它
curl https://api.fireworks.ai/inference/v1/chat/completions \
  -H "Authorization: Bearer $FIREWORKS_API_KEY" \
  -d '{"model": "accounts/<ACCOUNT_ID>/deployments/my-llama-70b", ...}'
```

**部署选项矩阵**：

| 维度 | 选项 |
|---|---|
| **GPU 型号** | H100 80GB / H200 141GB / B200 180GB / B300 288GB / A100 80GB |
| **Region** | GLOBAL（默认）/ US / EUROPE / APAC / 19 个单 region |
| **Min/Max Replicas** | 0 到 N；min=0 支持 scale-to-zero |
| **Load Target** | default / tokens_generated_per_second / prompt_tokens_per_second / requests_per_second / concurrent_requests |
| **Scale Window** | scale-up (默认 30s) / scale-down (10m) / scale-to-zero (1h, min 5m) |
| **Draft Model** | Speculative Decoding 加速 |
| **Quantization** | 默认 FP8，可选 BF16/INT8/INT4 |

**自动扩缩细节**（来自 docs）：
- 当请求进入时若 deployment 在 0 replica，**返回 503 + `DEPLOYMENT_SCALING_UP` 错误码**；
- **不会排队**——客户必须自己重试（指数退避，文档给出 Python/JS/curl 示例）；
- **冷启动时间**：小模型 30-60s，大模型 405B / MoE 671B 3-10 分钟；
- **7 天无流量自动删除**（min=0 时）；
- **Reserved capacity** 购买可保证硬件不被回收（适合低延迟 SLA 场景）。

### 5.3 Fine-tuning 后保留部署

```bash
# 1. 创建 SFT job
firectl sft-job create \
  --model accounts/fireworks/models/llama-v3p1-8b-instruct \
  --dataset my-dataset \
  --output-model my-finetuned-llama \
  --lora \
  --epochs 3

# 2. 训练完自动部署为 deployment
# 或手动部署
firectl deployment create accounts/<ACCOUNT>/models/my-finetuned-llama \
  --deployment-id my-custom-llama
```

**微调栈**：

```
┌──────────────────────────────────────────────────────────┐
│  Fireworks Agent (2025+) — 自然语言描述，自动全流程     │
│  • Agent 选 base model / 准备数据 / sweep 超参 / 评估    │
│  • 用户在 Claude Code / Cursor / Codex 内调用           │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│  Managed Fine-Tuning — UI/CLI/REST 提交                  │
│  • SFT (Supervised)  — messages 数组格式                │
│  • DPO (Preference)  — chosen/rejected pairs            │
│  • RFT (Reinforcement) — 评分函数，verifiable tasks     │
│  • LoRA 或 Full-Parameter                              │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│  Training API (Tinker 兼容) — Python 脚本                 │
│  • 自定义 loss function (forward_backward_custom)        │
│  • inference-in-the-loop evaluation (hotload ckpt)       │
│  • Per-step diagnostics, MoE Routing Replay             │
└──────────────────────────────────────────────────────────┘
```

### 5.4 部署架构对比

| 形态 | 谁适合 | 计费 | 冷启动 | SLA | 隔离 |
|---|---|---|---|---|---|
| **Serverless Standard** | 原型/低频 | $/1M tok | 无 | 尽力 | 多租户 |
| **Serverless Priority** | 生产 SLA | $/1M tok × 1.5 | 无 | 99.9% | 多租户 + 优先队列 |
| **Serverless Fast** | 实时对话 | $/1M tok × 2 | 无 | 高 | 多租户 + 专用池 |
| **On-Demand Deployment** | 高频/可控 | $/GPU·s | 30s-10min | 99.9% | 专用 |
| **Reserved Capacity** | 强 SLA | 月费 + $/s | 极短 | 99.99% | 硬件保留 |
| **Fine-tuned + On-Demand** | 自定义模型 | $/GPU·s | 同上 | 同上 | 专用 |
| **Self-Hosted (历史)** | 退出 | - | - | - | - |

> 2024 年 Q3 后 Fireworks 关停了一度支持的 "Self-Hosted"（私有化）业务线，专注云端。

---

## 6. 成本模型

### 6.1 Serverless 计费（per 1M tokens，美元，2025-2026）

> 价格取自 docs.fireworks.ai/serverless/pricing 公开页面，**以 2026-06-05 调研日期为准**。

#### 6.1.1 主流模型 (Standard / Priority 价 = input / cached-input / output)

| 模型 | Standard | Priority |
|---|---|---|
| Llama 3.1 8B Instruct | $0.20 / $0.10 / $0.20 | $0.30 / $0.15 / $0.30 |
| Llama 3.1 70B Instruct | $0.90 / $0.45 / $0.90 | $1.35 / $0.68 / $1.35 |
| Llama 3.1 405B Instruct | $3.00 / $1.50 / $3.00 | $4.50 / $2.25 / $4.50 |
| Llama 3.2 1B/3B | $0.10 / $0.05 / $0.10 | - |
| Llama 3.3 70B | $0.90 / $0.45 / $0.90 | $1.35 / $0.68 / $1.35 |
| Qwen 2.5 7B Instruct | $0.20 / $0.10 / $0.20 | - |
| Qwen 2.5 72B Instruct | $0.90 / $0.45 / $0.90 | - |
| Mixtral 8x7B | $0.50 / $0.25 / $0.50 | - |
| Mixtral 8x22B | $1.20 / $0.60 / $1.20 | - |
| DeepSeek V2.5 / V3 | $0.90 / $0.14 / $0.90 | - |
| DeepSeek R1 (reasoning) | $3.00 / $0.55 / $8.00 (估) | - |
| DBRX | $1.20 / $0.60 / $1.20 | - |
| Yi-Large | $0.90 / $0.45 / $0.90 | - |

**Fast variants**：约 Standard 价的 2x。

#### 6.1.2 Embeddings

| 模型 | $/1M input tokens |
|---|---|
| 小型 (≤150M) | $0.008 |
| 中型 (150M-350M) | $0.016 |
| Qwen 3 8B Embedding | $0.10 |

#### 6.1.3 Batch Inference

- **50% off** 输入 + 输出 token 价；
- **自动 prompt caching**（再叠 50% off cached tokens）—— **理论上最低 25% 价**（$0.05/1M for 8B batch input）。

#### 6.1.4 图像 / 语音（FLUX / Whisper）

- 图像生成按张计费（具体未公开，~ $0.01-0.05/张 1024x1024 估算）；
- 语音转写按分钟（~$0.006/min，OpenAI Whisper 同价位）。

### 6.2 On-Demand GPU 计费

| GPU | VRAM | $/GPU·小时 | 备注 |
|---|---|---|---|
| H100 80GB SXM | 80GB | $7.00 | Hopper 主力 |
| H200 141GB SXM | 141GB | $7.00 | 显存大，KV cache 友好 |
| B200 180GB | 180GB | $10.00 | Blackwell，2025 上市 |
| B300 288GB | 288GB | $12.00 | Blackwell Ultra，2026 |
| A100 80GB (legacy) | 80GB | ~$4.00 (估) | 旧部署仍有 |

**按秒计费**，无启动费；多 region 加价（未公开，通常 5-15%）。

### 6.3 Fine-tuning 训练计费（per 1M training tokens）

| 模型规模 | LoRA SFT | LoRA DPO | Full SFT | Full DPO |
|---|---|---|---|---|
| ≤ 16B | $0.50 | $1.00 | $1.00 | $2.00 |
| 16.1B - 80B | $3.00 | $6.00 | $6.00 | $12.00 |
| 80B - 300B | $6.00 | $12.00 | $12.00 | $24.00 |
| > 300B (DeepSeek V3 / Kimi K2 量级) | $10.00 | $20.00 | $20.00 | $40.00 |

- **RFT** (Reinforcement FT) 按 GPU 小时计（同 On-Demand）；
- **微调后部署**：基础模型同价（无附加费）。

### 6.4 与竞品定价对比（1M input/output tokens，2026-06）

| 服务 | Llama 3.1 8B | Llama 3.1 70B | Mixtral 8x7B |
|---|---|---|---|
| **Fireworks** | $0.20 / $0.20 | $0.90 / $0.90 | $0.50 / $0.50 |
| **Together AI** | $0.18 / $0.18 | $0.88 / $0.88 | $0.60 / $0.60 |
| **OpenRouter (均价)** | $0.20 / $0.20 | $1.00 / $1.00 | $0.60 / $0.60 |
| **Replicate** | $0.20 / $0.50 | $0.95 / $2.85 | - |
| **Groq (自研硬件)** | $0.05 / $0.08 | $0.59 / $0.79 | $0.24 / $0.24 |
| **OpenAI GPT-4o-mini** | $0.15 / $0.60 | - | - |

**注意**：Fireworks 价**不含**批价（batch 50% off）、缓存 50% off；OpenAI 等没有同级别 batch 优惠（OpenAI Batch 是 24h 完成窗口，价相同但 SLA 较低）。

### 6.5 TCO 模型示例

**场景**：中型 AI Agent 产品，1B input tokens/月 + 500M output tokens/月，70% 命中 prompt cache，30% 走 batch。

```
主流量：Llama 3.1 70B
输入：$0.90/1M × 1000M = $900
输出：$0.90/1M × 500M = $450
缓存折扣：70% × $900 × 0.5 = $315
Batch 折扣：30% × ($900 + $450) × 0.5 = $202.5
──────────────────────────────────
小计：$900 + $450 - $315 - $202.5 = $832.5/月
```

对比 OpenAI GPT-4o mini：
```
输入：$0.15/1M × 1000M = $150
输出：$0.60/1M × 500M = $300
无 cache 折扣、无 batch 折扣
──────────────────────────────────
小计：$450/月
```

**结论**：如果质量可接受，OpenAI 闭源模型仍更便宜；但**当需要开源可控、微调、部署在自己的环境**时，Fireworks 是价格/性能甜点。

---

## 7. 生态

### 7.1 客户端 SDK

| SDK | 语言 | 状态 |
|---|---|---|
| `openai` (Python/Node) | 多语言 | ✅ 官方推荐（改 base_url 即可） |
| `anthropic` (Python/Node) | 多语言 | ✅ 改 base_url |
| `fireworks-ai` (Python) | Python | ✅ 官方，支持 `reasoning_content` 等扩展字段 |
| `llama-index` | Python | ✅ 通过 OpenAI 兼容层 |
| `langchain` / `langgraph` | Python/JS | ✅ 通过 OpenAI 兼容层 |
| `instructor` | Python | ✅ 通过 OpenAI 兼容层 |
| `vercel ai sdk` | JS/TS | ✅ 通过 OpenAI 兼容层 |
| `claude code` | CLI | ✅ 改 `ANTHROPIC_BASE_URL` |
| `cursor` | IDE | ✅ 改 provider |
| `github copilot` | IDE | ✅ 通过 custom endpoint |
| `microsoft foundry` (Azure) | 平台 | ✅ Azure 集成 |

### 7.2 集成亮点

#### 7.2.1 Microsoft Foundry / Azure 集成

- 在 Azure 订阅内部署 Fireworks 模型；
- 通过 Azure 账单计费（企业客户走 Azure MSA 流程）；
- 数据驻留 Azure（vs Fireworks 自有 region）。

#### 7.2.2 Claude Code 集成

```bash
# .envrc 或 shell config
export ANTHROPIC_BASE_URL=https://api.fireworks.ai/inference/v1
export ANTHROPIC_AUTH_TOKEN=$FIREWORKS_API_KEY

# Claude Code 直接把请求打到 Fireworks
claude "Refactor this function"
```

#### 7.2.3 Vercel AI SDK

```typescript
import { openai } from '@ai-sdk/openai';

const model = openai('accounts/fireworks/models/llama-v3p1-70b-instruct', {
  baseURL: 'https://api.fireworks.ai/inference/v1',
  apiKey: process.env.FIREWORKS_API_KEY,
});
```

### 7.3 监控 / 可观测性集成

| 平台 | 集成方式 |
|---|---|
| Datadog | Metrics export via `/deployments/exporting-metrics` |
| Prometheus | OpenMetrics endpoint |
| OpenTelemetry | OTLP gRPC/HTTP |
| Helicone | 通过 OpenAI 兼容层代理 |
| Langfuse | 通过 OpenAI 兼容层代理 |
| LangSmith | 通过 OpenAI 兼容层代理 |
| Arize Phoenix | OpenTelemetry exporter |

### 7.4 模型生态

- **100+ 模型**（2025 年统计，2026 年应 150+）：
  - **文本**：Llama 2/3/3.1/3.2/3.3 全系、Qwen 2/2.5/QwQ、DeepSeek V2/V3/R1、Mistral 7B/Mixtral 8x7B/8x22B、Yi、DBRX、Gemma 1/2、Phi-3/4、Command R+；
  - **多模态**：Llama 3.2 Vision、Qwen2-VL、Idefics、Pixtral；
  - **代码**：CodeLlama、DeepSeek Coder、Qwen 2.5 Coder、Code Llama 70B；
  - **嵌入**：nomic-embed、bge-large、Qwen 3 8B Embedding、Fireworks 自研 e5/fireembed；
  - **重排**：Fireworks 自研 rerank、bge-reranker、jina-reranker；
  - **图像生成**：FLUX.1 [schnell] FP8、FLUX.1 Kontext；
  - **音频**：Whisper V3（转录）、Bark（合成）。

---

## 8. 客户案例

> 公开案例来自 Fireworks 官方博客、播客采访、Crunchbase 数据。

### 8.1 Cursor (AI IDE)

- **场景**：Cursor 早期 (2023) 用 Fireworks 跑自己微调的 deepseek-coder，作为 VS Code extension 的代码补全后端；
- **量级**：亿级 tokens/天，70B 模型并发数百 QPS；
- **原因**：微调友好（Cursor 在 Fireworks 上微调自己的 code 模型）+ 低延迟（Fast tier）。

### 8.2 Uber

- **场景**：Uber Eats 客服 AI、driver 端 RAG 助手；
- **量级**：百万 QPS 月度（披露有限）；
- **原因**：数据合规（SOC2 + HIPAA 合规 Trust Center 公开），私有部署选项（已停）。

### 8.3 DoorDash

- **场景**：商户 AI 助手、消费者客服 routing；
- **细节**：使用 Llama 70B + 自己的 domain 微调，处理食品配送领域 query；
- **SLA 要求**：高峰期 TTFT < 500ms（Priority tier 满足）。

### 8.4 Notion

- **场景**：Notion AI 功能（问答、写作辅助）的部分推理；
- **模型**：Mixtral 8x22B（Notion 在 Fireworks 上微调）；
- **为什么**：相比直接调 OpenAI，**可定制** + **可微调** + **数据可出境**。

### 8.5 Shopify

- **场景**：Shopify Magic 商家侧 AI 助手（产品描述、营销文案）；
- **集成**：通过 OpenAI 兼容层 + Function calling 调用 Shopify 后台 API。

### 8.6 Retool

- **场景**：Retool AI Workflows 后端；
- **细节**：用 Fireworks 跑开源 LLM，让企业客户能选**自托管推理**还是 **Fireworks 托管**。

### 8.7 Vercel

- **场景**：v0 部分推理后端；
- **细节**：Fireworks 是 Vercel Marketplace 早期合作方之一。

### 8.8 Character.ai（部分场景）

- **场景**：虽然主要自建推理，但非高峰流量用 Fireworks 弹性。

---

## 9. 优劣势分析

### 9.1 优势

| 维度 | 具体 |
|---|---|
| **性能** | 自研推理栈，FP8 + Speculative + Prefix Cache 组合下，~250% 吞吐优势（vs vLLM 自托管）|
| **延迟** | Fast tier TTFT < 100ms，Priority SLA 99.9%，多 region failover |
| **协议兼容** | OpenAI + Anthropic + Responses 三套协议，改 base_url 即可迁移 |
| **微调能力** | SFT / DPO / RFT 全栈，1T+ 模型可训，Tinker 兼容 Training API |
| **模型广度** | 100+ 开源模型，2025 年新增 Qwen 3 / DeepSeek V3 等 |
| **价格** | 批价 50% off、缓存 50% off，B200/B300 新硬件率先可用 |
| **生产稳定** | SOC2 + HIPAA + audit report（Trust Center 公开）|
| **DevX** | firectl CLI 完善、Cookbook (Notion / Cursor / RAG 都有) |
| **企业功能** | SSO、Service Account、Quota、按 team 分账 |

### 9.2 劣势

| 维度 | 具体 |
|---|---|
| **闭源** | 推理栈（FireAttention / FireSampler）不开放，**客户无法自托管**（2024 Q3 后退出 self-hosted 业务）|
| **锁定** | 训练数据 / LoRA / Router 都绑定 Fireworks，迁移成本高 |
| **价格不最优** | 同类竞品（Groq、Together）部分模型更便宜；OpenAI 闭源模型对中小客户更便宜 |
| **冷启动** | 大模型 (405B / 671B) 冷启动 3-10 分钟，On-Demand scale-from-zero 503 不排队 |
| **不透明** | 内部架构（FireAttention 具体实现）公开材料少，黑盒程度高 |
| **不跑自己模型** | 不做基础模型研究，与 OpenAI/Anthropic/DeepSeek 自家模型相比有内容/能力上限 |
| **企业功能** | 相比 AWS Bedrock / Azure AI Foundry，区域/合规选项仍少 |
| **部分限制** | JSON Schema 不支持 `oneOf`、外部 `$ref`、长度约束，复杂场景需 workaround |
| **中文生态** | 国内访问偶尔不稳（虽然 2025+ 加入 AP_TOKYO 区域）|

### 9.3 不适合谁

- **需要私有化部署的金融 / 政企客户**——走 OpenAI / Azure 私有 endpoint；
- **需要极致便宜的小客户**——用 Groq / OpenRouter 比价 + 缓存策略可能更省钱；
- **需要自定义推理栈的客户**——vLLM / TensorRT-LLM 自托管；
- **不需要微调、只用现成闭源模型**——直接调 OpenAI / Anthropic 即可。

### 9.4 适合谁

- **生产级 AI 产品** 需要开源模型 + 微调 + 高 SLA；
- **RAG / Agent 应用**需要 function calling + JSON schema + 流式；
- **成本敏感但不愿自建**的中型企业；
- **多模型集成**需要 100+ 模型统一 API；
- **从 OpenAI 迁移**需要"一行代码"的兼容层。

---

## 10. 与其他产品对比

### 10.1 横向对比矩阵

| 维度 | **Fireworks AI** | **Together AI** | **Replicate** | **Modal** | **Baseten** | **Groq** |
|---|---|---|---|---|---|---|
| **定位** | 推理 + 微调一体化 | 推理 + 算力市场 | 模型市场 / 一键部署 | 计算平台 (不专 LLM) | 推理框架 + 部署 | 极低延迟推理 |
| **核心场景** | 生产级开源模型推理 | 研究 / 算力调度 | Demo / PoC / 爱好者 | 任意 Python 工作负载 | 自托管 Truss 框架 | 实时对话 |
| **模型数量** | 100+ | 200+ | 数万 (社区贡献) | 自定义 | 自定义 + 库 | 20+ (精选) |
| **核心 API** | OpenAI / Anthropic 兼容 | OpenAI 兼容 | 自有 Cog API | 任意 | OpenAI 兼容 | OpenAI 兼容 |
| **微调** | ✅ SFT/DPO/RFT | ✅ SFT/DPO | ❌ (需自带) | ✅ 自定义 | ✅ Truss 训练 | ❌ |
| **部署形态** | Serverless + On-Demand | Serverless + GPU 租赁 | Serverless | 容器 | Dedicated | Serverless |
| **推理引擎** | 自研 (FireAttention) | vLLM + FlashAttention | Cog (定制) | 用户自选 | Truss (定制) | 自研 LPU 硬件 |
| **硬件** | H100/H200/B200/B300 | H100/A100 | T4/L4/A100 | 用户自选 | H100/A100 | 自研 LPU |
| **价格 (70B)** | $0.90/$0.90 | $0.88/$0.88 | $0.95/$2.85 | 算力 + 自己跑 | $0.80/$0.80 (估) | $0.59/$0.79 |
| **延迟 (TTFT)** | 250ms (Std) / 80ms (Fast) | ~300ms | ~400ms | 自定 | ~300ms | ~150ms (LPU 优势) |
| **SLA** | 99.9% (Priority) | 99.9% | 尽力 | 99.95% | 99.9% | 99.9% |
| **冷启动** | < 5s (Serverless) | < 5s | < 5s | < 10s (容器) | < 30s | < 5s |
| **数据驻留** | 多 region | 多 region | 多 region | 任意 | 多 region | 美国 |
| **私有化** | ❌ (2024+ 停) | ❌ | ❌ | ✅ (本地 Modal) | ✅ (Truss OSS) | ❌ |
| **计费模型** | Token / GPU·s | Token / GPU·s | 启动 + token | 计算·s | GPU·小时 | Token |

### 10.2 与 Together AI 详细对比

| 维度 | Fireworks | Together |
|---|---|---|
| **价格** | 略低 (5-10%) | 略高 |
| **性能 (单 query)** | FireAttention 略胜 | vLLM 0.6+ 接近 |
| **模型数** | 100+ (精选) | 200+ (包括小众) |
| **微调** | 强（SFT/DPO/RFT/Training API）| 强（SFT/DPO/Continued Pretrain）|
| **学术友好** | 弱（商业平台）| 强（学术算力折扣）|
| **企业 SLA** | Priority tier 强 | Reserved 强 |
| **数据合规** | SOC2 + HIPAA + Trust Center | SOC2 + HIPAA |
| **生态** | Cookbook + Vercel + Cursor | 学术论文 + 算力市场 |

**总结**：
- 选 Fireworks：**生产级 SLA + 微调 + 多协议兼容** 想要一体化；
- 选 Together：**学术 / 研究 / 算力调度 / 自由度高**。

### 10.3 与 Replicate 详细对比

| 维度 | Fireworks | Replicate |
|---|---|---|
| **目标用户** | 企业生产 | 个人 / 爱好者 / 快速 PoC |
| **定价模型** | 透明 Token | 启动费 + token（难预估成本）|
| **模型来源** | Fireworks 官方 | 社区上传 (cog 容器) |
| **稳定性** | 高 | 中（小模型冷启动 5-10s）|
| **微调** | ✅ | ❌ |
| **企业功能** | 强 (SSO/Quota) | 弱 |
| **价格 (稳定负载)** | 低 30-50% | 高（启动费） |

**总结**：
- 选 Fireworks：**生产负载 + 成本可控**；
- 选 Replicate：**试玩 / 一次跑 100 个不同模型 / 短任务**。

### 10.4 与 Modal 详细对比

| 维度 | Fireworks | Modal |
|---|---|---|
| **定位** | LLM 推理专精 | 通用 Python 容器 |
| **使用门槛** | API 调用 | 写 Python 装饰器 |
| **灵活性** | 低（只能跑支持的模型）| 极高（任意 Python 代码）|
| **推理性能** | 优化过 | 取决于用户自选 |
| **冷启动** | < 5s | < 10s (容器) |
| **计费** | Token | CPU/GPU·s + 内存 + 网络 |
| **适合谁** | 调 LLM API 即可 | 需要把 LLM 嵌进复杂流程 |

**总结**：
- 选 Fireworks：**只需要 LLM 推理**；
- 选 Modal：**LLM 只是流水线一环**（如：先 OCR，再调 LLM，再 render 视频）。

### 10.5 与 Baseten 详细对比

| 维度 | Fireworks | Baseten |
|---|---|---|
| **核心产品** | 托管平台 | Truss 框架 + 托管 |
| **开源程度** | 闭源 | Truss 框架开源 |
| **推理引擎** | 自研 | 自研 (TTS/MII) + 用户自选 |
| **微调** | 平台托管 | 自带训练 (MosaicML 出身) |
| **价格** | 略低 | 略高 |
| **适合** | 不愿管推理栈 | 想用 Truss 自托管 + 商业部署双轨 |

**总结**：
- 选 Fireworks：**全托管，no code 起步**；
- 选 Baseten：**Truss 框架 + 想要"自托管 + 商业"灵活性**。

### 10.6 与 Groq 详细对比

| 维度 | Fireworks | Groq |
|---|---|---|
| **硬件** | NVIDIA GPU | 自研 LPU (LPU Inference Engine) |
| **延迟** | 80-250ms (TTFT) | 50-150ms (TTFT) |
| **吞吐** | 极高 | 中（受 LPU 集群规模限制）|
| **价格 (8B)** | $0.20/$0.20 | $0.05/$0.08 |
| **模型数** | 100+ | 20+ (Llama / Mixtral / Whisper) |
| **生产 SLA** | Priority tier 强 | 偶发容量限制 |
| **生态** | 全（多协议 + 微调）| 仅 OpenAI 兼容 API |

**总结**：
- 选 Fireworks：**模型多 + 微调 + 生态**；
- 选 Groq：**极致延迟 / 价格（牺牲灵活性）**。

---

## 11. 架构图汇总

### 11.1 推理调用链路时序

```
┌────────┐          ┌─────────┐        ┌──────────┐       ┌─────────┐
│ Client │          │ Gateway │        │ Scheduler│       │  GPU    │
│(OpenAI │          │(protocol│        │(Fire-    │       │  Pool   │
│  SDK)  │          │ router) │        │ Sampler) │       │         │
└───┬────┘          └────┬────┘        └────┬─────┘       └────┬────┘
    │ POST /v1/chat     │                   │                  │
    ├──────────────────>│                   │                  │
    │                   │ parse + auth      │                  │
    │                   │ + rate limit      │                  │
    │                   ├──────────────────>│                  │
    │                   │                   │ enqueue request  │
    │                   │                   │ + match prefix   │
    │                   │                   │ + assign replica │
    │                   │                   ├─────────────────>│
    │                   │                   │                  │ prefill
    │                   │                   │                  │ (compute
    │                   │                   │                  │  attention)
    │                   │                   │                  │
    │                   │                   │                  │ KV cache
    │                   │                   │                  │ allocated
    │                   │                   │                  │
    │ SSE stream ◄──────┼───────────────────┼──────────────────┤
    │ (data: {...})     │                   │                  │ decode
    │                   │                   │                  │ (token 1)
    │                   │                   │                  │ decode
    │                   │                   │                  │ (token 2)
    │                   │                   │                  │ ...
    │ SSE stream ◄──────┼───────────────────┼──────────────────┤
    │ (data: [DONE])    │                   │                  │ EOS
    │                   │                   │ bill tokens      │
    │                   │                   │ + log usage      │
    │                   │                   │                  │ free KV
```

### 11.2 Fine-tuning 工作流

```
┌──────────────────────────────────────────────────────────────┐
│                      数据准备阶段                             │
│  • 上传 JSONL 到 dataset (OpenAI messages 格式)              │
│  • 校验格式 (validate-dataset-upload)                         │
│  • 解析 token count、估算训练时长                            │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                      训练任务创建                             │
│  • 选 base model + tuning mode (SFT/DPO/RFT)                 │
│  • 选 LoRA 或 Full-Param                                     │
│  • 选 GPU 形状 (H100/H200/B200)                              │
│  • 提交 sft-job / dpo-job / rft-job                          │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                      训练执行 (GPU 集群)                      │
│  • Distributed Data Parallel (DDP)                          │
│  • ZeRO-3 / FSDP (大模型)                                    │
│  • MoE Routing Replay (Kimi K2 等)                          │
│  • Checkpoint 每 N step 写盘                                 │
│  • 监控 loss / reward (RFT) / eval metrics                   │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                      模型注册 + 可选部署                      │
│  • ckpt 转为 Fireworks model 格式                            │
│  • 量化 (FP8/INT4)                                          │
│  • 可选: 自动转 deployment (On-Demand)                       │
│  • 路由到 router (A/B 测试)                                  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                      推理服务                                │
│  • 标准 OpenAI / Anthropic 兼容 API                          │
│  • 计费 = 基础模型同价                                       │
│  • 支持 scale-to-zero + autoscaling                          │
└──────────────────────────────────────────────────────────────┘
```

### 11.3 多 Region 部署

```
                        Global Edge (anycast)
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
   │   US    │             │   EU    │             │  APAC   │
   │ Multi-  │             │ Multi-  │             │ Multi-  │
   │ Region  │             │ Region  │             │ Region  │
   └────┬────┘             └────┬────┘             └────┬────┘
        │                       │                       │
   ┌────┼────────────────┐ ┌───┼────────────┐ ┌───────┼────────┐
   │                    │ │                │ │                │
┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌▼─────┐ ┌────────┐ ┌▼────┐ ┌────────┐
│Ari- │ │Cal- │ │Iowa │ │Frank-│ │Iceland │ │Tokyo│ │Tokyo  │
│zona │ │ifor-│ │H100 │ │furt  │ │H200/   │ │H100 │ │H200   │
│H100 │ │nia  │ │A100 │ │H100  │ │B200    │ │     │ │       │
└─────┘ │H200 │ └─────┘ └──────┘ └────────┘ └─────┘ └───────┘
        └─────┘
```

---

## 12. 关键技术细节补充

### 12.1 Fireworks Python SDK

```python
from fireworks import Fireworks

client = Fireworks(api_key="fw_...")

# 基础 chat
resp = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
    messages=[{"role": "user", "content": "Hello"}],
)

# 扩展字段：reasoning_content（reasoning 模型）
resp = client.chat.completions.create(
    model="accounts/fireworks/models/deepseek-r1",
    messages=[{"role": "user", "content": "9.11 vs 9.8"}],
)
print(resp.choices[0].message.reasoning_content)  # 推理过程
print(resp.choices[0].message.content)            # 最终答案
```

### 12.2 firectl CLI 命令速查

```bash
# 模型
firectl list models
firectl get model <MODEL_ID>
firectl create model <HF_REPO>  # 上传自定义模型

# 部署
firectl deployment create <MODEL> --deployment-id=<ID> --region=US \
    --min-replica-count=1 --max-replica-count=5
firectl deployment get <ID>
firectl deployment update <ID> --min-replica-count=0
firectl deployment scale <ID> --replicas=10
firectl delete deployment <ID>

# Router
firectl router create --router-id=<ID> --deployments=<D1>,<D2>
firectl router update <ID> --deployments=<D1>,<D2>,<D3>
firectl router get <ID>
firectl router delete <ID>

# 微调
firectl sft-job create --model=<M> --dataset=<D> --output-model=<OM> --lora --epochs=3
firectl sft-job get <JOB_ID>
firectl sft-job list

# Batch
firectl batch-inference-job create --model=<M> --input-dataset-id=<D>
firectl batch-inference-job get <JOB_ID>

# Quota
firectl quota list
firectl quota get <RESOURCE>

# Account
firectl account get
```

### 12.3 错误码速查

| Code | HTTP | 含义 | 处理 |
|---|---|---|---|
| `DEPLOYMENT_SCALING_UP` | 503 | Deployment 0 replica 启动中 | 指数退避重试 |
| `RATE_LIMIT_EXCEEDED` | 429 | TPM/RPM 超出 | 退避重试 + 提配额 |
| `INSUFFICIENT_QUOTA` | 402 | 账户余额/信用不足 | 充值 |
| `MODEL_NOT_FOUND` | 404 | 模型 ID 错 | 检查 ID |
| `CONTEXT_LENGTH_EXCEEDED` | 400 | 输入超 max context | 截断或换大窗口模型 |
| `INVALID_JSON_SCHEMA` | 400 | `response_format` schema 不合法 | 检查不支持的字段 |
| `STREAM_ABORTED` | - | SSE 流中断 | 客户端重试 |

### 12.4 与 OpenAI 协议的微妙差异

| 字段 | OpenAI 行为 | Fireworks 行为 | 兼容？ |
|---|---|---|---|
| `service_tier` | 仅 "auto"/"default" | + "priority"/"fast" | OpenAI 端会忽略 |
| `response_format` | 支持 | 支持 + json_schema 扩展 | ✅ |
| `tools` | 支持 | 支持 + `$defs` shorthand 扩展 | ✅ |
| `metadata` | 支持 | 支持 | ✅ |
| `store` (Responses API) | 支持 | 支持 | ✅ |
| `truncation` (auto) | 支持 | 支持 | ✅ |
| `parallel_tool_calls` | 3 个新模型 | 多数开源模型 | ⚠️ 视模型 |

---

## 13. 战略趋势与展望（2026-2027）

### 13.1 Fireworks 自身方向

1. **企业市场深化**：Trust Center 持续扩展（SOC2 → HIPAA → FedRAMP 路径）；
2. **微调生态**：Training API (Tinker 兼容) 降低 RL 研究门槛，吸引 research 客户；
3. **Fireworks Agent**（2025+）：自然语言描述 → 自动全流程微调，是 **"AI 训练 AI"** 的产品化；
4. **Blackwell 全面铺开**：B200/B300 抢先部署，**KV cache 容量提升 ~2-3x** → 间接降价；
5. **多模态推理**：FLUX Kontext、Qwen3-VL、audio 模型扩展。

### 13.2 行业坐标

Fireworks 在 AI Gateway / 推理云赛道里处于 **"开源模型生产级推理"** 第一梯队（与 Together AI、Anyscale、Baseten 并列），与 **"闭源模型聚合"**（OpenRouter、Unify）、**"通用计算平台"**（Modal、Replicate）、**"自研硬件"**（Groq、Cerebras）形成清晰差异化。

未来 18-24 个月最大变量：
- **DeepSeek / Qwen / GLM 等中国开源模型**持续追平 GPT-4 → Fireworks 这类推理云的需求增长；
- **企业自托管** 趋势反弹（合规/数据出境），Fireworks 退出 self-hosted 是赌注；
- **RFT / RL 训练** 工具化，Fireworks Agent 抢先卡位；
- **Blackwell 涨价** vs **开源模型同质化** → 推理云价格战压力。

---

## 14. 决策建议（面向 CTO / 架构师）

| 场景 | 推荐 |
|---|---|
| **快速 PoC / 调 OpenAI 替代** | ✅ Fireworks（OpenAI 兼容 + 100+ 模型） |
| **生产级 Agent / RAG** | ✅ Fireworks Priority tier（多协议 + function calling + JSON schema） |
| **实时对话 (< 100ms TTFT)** | ✅ Fireworks Fast / 或 Groq（极端延迟） |
| **微调自研模型 (SFT/DPO/RFT)** | ✅ Fireworks（一体）或 Together（研究） |
| **多模型 A/B 路由** | ✅ Fireworks Router（内置）或自建 LiteLLM |
| **私有化部署** | ❌ 改 Modal (本地) / Baseten (Truss) / 自托管 vLLM |
| **成本极致 (Groq 价格胜出)** | ⚠️ 选 Groq（牺牲模型多样性） |
| **中国国内客户 (合规)** | ⚠️ 走 Together / 自托管 / 国内云（Fireworks 国内访问偶发不稳） |
| **GLM 4 / Qwen 优先** | ⚠️ 选阿里云 / 智谱 / Together（Fireworks 也支持但非首选） |

---

## 15. 关键参考

- 官方文档：https://docs.fireworks.ai/
- 价格：https://docs.fireworks.ai/serverless/pricing
- 状态页：https://status.fireworks.ai/
- Trust Center：https://trust.fireworks.ai/
- Cookbook：https://github.com/fw-ai/cookbook
- firectl CLI 文档：https://docs.fireworks.ai/tools-sdks/firectl
- Lin Qiao 演讲：AI Engineer World's Fair 2024、QCon SF 2024
- 第三方评测：Artificial Analysis (artificialanalysis.ai) — 2024-2026 多家推理云横评

---

> **报告字数**：~14,500 字（含代码块、表格、ASCII 图）
> **覆盖维度**：项目背景、架构设计、协议支持、性能数据、部署方式、成本模型、生态、客户案例、优劣势分析、对比
> **下次更新建议**：季度同步（关注 Fireworks Agent 进展、Blackwell 定价、新模型上线）
