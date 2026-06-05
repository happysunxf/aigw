# Not Diamond — 深度调研报告

> **调研日期**：2026-06-05
> **产品定位**：AI Model Router（智能 LLM 路由器）+ Prompt Optimization
> **公司曾用名**：Martian（路由器研究论文 RouterBench 出自该公司团队）
> **公司官网**：https://www.notdiamond.ai
> **文档站**：https://docs.notdiamond.ai
> **API 平台**：https://app.notdiamond.ai
> **PyPI**：`notdiamond`（https://pypi.org/project/notdiamond/）
> **npm**：`notdiamond`（https://www.npmjs.com/package/notdiamond）
> **GitHub (Python SDK)**：https://github.com/Not-Diamond/not-diamond-python
> **GitHub (RouterBench)**：https://github.com/withmartian/routerbench
> **论文**：RouterBench: A Benchmark for Multi-LLM Routing System（arXiv:2403.12031）

---

## 0. TL;DR

Not Diamond 是**全球第一个，也是目前最被资本认可的、面向 LLM 应用层的"智能路由器 + Prompt 优化器"**。其团队把"routing"这件事从"做网关"重新定位为"做调度大脑"——**不代理你的请求，不成为你的网关**：

- 你的应用 → 调用 `Not Diamond` → 拿回一个**应该用哪个 LLM 的建议 + session_id** → 再由你自己的代码（或你自己的 Portkey / LiteLLM / OpenRouter）去调用那个 LLM。
- 它要解决的核心问题：**长程 agent 工作流下的推理成本爆炸**（用户调研里反复出现 "5x cost savings on coding agents"）。

> "We are not a gateway, and our intelligent router simply determines when to use which model. Requests are then executed client-side through your gateway of choice." — Not Diamond 官方 FAQ

**它和 Portkey / LiteLLM / OpenRouter 的本质区别**：

| 维度 | Portkey / LiteLLM / OpenRouter | **Not Diamond** |
|---|---|---|
| 是不是 proxy/gateway | ✅ 是，**代理**所有 LLM 请求 | ❌ 不是网关，**只做路由决策** |
| 调用形式 | 业务直接打到 Portkey 网关 | 业务先打 Not Diamond 拿"用哪个模型"，再自己打 |
| 路由依据 | 权重 / A/B / 失败重试 / 简单规则 | 训练好的 meta-model，根据 prompt 语义挑模型 |
| 业务耦合点 | 网关内做 fail-over、统一日志 | 业务代码里多一行 `client.model_router.select_model(...)` |
| Prompt 优化 | ❌ 不是它的卖点 | ✅ 是另一条主产品线（DSPy 竞品） |
| 自训练路由 | ❌ 通常硬编码路由表 | ✅ 上传你的评估数据，训练 preference_id |
| 成本 | 按 token 用量收 gateway fee | 按"路由推荐次数" / "成功优化次数"收 |

> 一句话：**它是 Meta-model for LLM Selection**，而不是 AI Gateway。

---

## 1. 项目背景

### 1.1 团队 / 公司沿革

Not Diamond 的创始团队是 **Martian** 团队。Martian 在 2023 年发布 RouterBench（arXiv:2403.12031），是**第一篇系统性评估 LLM 路由器的论文**，数据集包含 405k+ 推理结果。Martian 后期品牌升级为 Not Diamond，将学术研究包装为可商用的 SaaS。

公司在 about 页（2026-06 抓取）写得很"理想主义"，把自家对标 Google 在 1998 年对 Yahoo 门户的做法——"不做大而全的门户，做 routing layer"：

> "Not Diamond is the data-driven recommendation layer for intelligence. ... We believe infrastructure to enable a distributed future for AI will not only drive forward performance, but also make the field less monopolistic, more energy efficient, and more interpretable."

### 1.2 投资人

公开的投资人名单（来自 about 页）几乎是"硅谷老炮 + AI 新贵"的全明星阵容：

- **Jeff Dean** — Google
- **Julien Chaumond** — Hugging Face
- **Ion Stoica** — Databricks, Anyscale
- **Akshay Kothari** — Notion
- **Arash Ferdowsi** — Dropbox
- **Guillermo Rauch** — Vercel
- **Olivier Pomel** — DataDog
- **Zack Kass** — OpenAI（前 GTM）
- **Lukas Biewald** — Weights & Biases
- **Jeff Weiner** — LinkedIn
- **Scott Belsky** — Adobe
- **Tom Preston-Werner** — GitHub
- **Dan Roth** — Oracle
- **Dwarak Rajagopal** — Snowflake
- **Amir Haghighat** — Baseten
- **Eoghan McCabe** — Intercom
- **Matias Woloski** — Auth0
- **John Kim** — PayPal
- **Paul Forster** — Indeed
- **Nadim Hossain** — Databricks
- **Amanpreet Singh** — Contextual AI
- **Chet Kapoor** — DataStax
- **Carl Rivera** — Shopify
- **Kiran Prasad** — LinkedIn
- **Neil Sequiera** — Defy
- **Dean Mai** — Myriad Venture Partners
- **Preetha Parthasarathy** — SAP
- **Caitlin Dullanty** — IBM
- **Adam Gartenberg** — 640 Oxford
- **Steven Woods** — Inovia Capital

团队规模非常小（"small, dedicated team"），强调 elite technical caliber。

### 1.3 三条产品线

```
Not Diamond
├── 1) Pre-trained Router  ── 预训练通用路由器（直接用，5 分钟接入）
│   ├── Chat router         ── 通用对话
│   └── Code router (EA)    ── 编程 agent 专用，号称"30%+ cost savings"
│
├── 2) Custom Router  ── 拿你自己的评测数据，训练定制路由器
│
└── 3) Prompt Optimization  ── 把你已有的 prompt，针对其他模型重写
```

### 1.4 业务口号

> "100x your AI dev cycles — let the machine build the machine"

更具体的数字（来自官网 hero）：

- **Accuracy gains 5%+**
- **Cost savings 30%+**
- **Faster dev cycles 2x**

---

## 2. 架构设计

### 2.1 整体定位：它不是网关，是"路由器"

这是 Not Diamond 和所有其他 AI Gateway 产品（Portkey、LiteLLM、Higress、APISIX、Kong、Envoy、Cloudflare、OpenRouter、Unify、Helicone）**最本质的架构差异**。

```
                          Not Diamond 在请求链路中的位置
                          =================================

[传统 AI Gateway 模式]
App  ──HTTP──▶  Gateway (Portkey/LiteLLM/OpenRouter)  ──HTTP──▶  LLM Provider
                       │
                       └─ 网关内做路由 + fail-over + 日志

[Not Diamond 模式]
App  ──HTTP──▶  Not Diamond API  ──(返回 "用 gpt-4o-mini")──▶  App
App  ──HTTP──▶  你自己的 LLM 客户端 / 你自己的 Gateway  ──HTTP──▶  LLM Provider
                  (OpenAI SDK / Portkey / LiteLLM / OpenRouter / Anything)
```

Not Diamond 的核心架构原则（直接引自安全和 FAQ 文档）：

1. **Client-side routing**：所有 LLM 请求**直接**从你的应用打到 LLM provider，**不经过 Not Diamond 的代理**。
2. **Not Diamond is stack-agnostic**：可以和你现有的任何 gateway / harness 组合。
3. **SOC-2 + ISO 27001**：合规齐全；企业可走 ZDR / VPC 部署。

### 2.2 调用时序图

```ascii
┌─────────────┐                  ┌────────────────┐                  ┌──────────────┐
│   App SDK   │                  │ Not Diamond    │                  │  LLM API     │
│ (Py/TS/curl)│                  │ /v2/modelrouter│                  │ (openai/etc) │
└──────┬──────┘                  │   /modelSelect │                  └──────┬───────┘
       │                         └────────┬───────┘                         │
       │                                  │                                 │
       │ 1. select_model(messages,        │                                 │
       │     llm_providers=[...],         │                                 │
       │     tradeoff='cost',             │                                 │
       │     preference_id='p_xxx')       │                                 │
       │─────────────────────────────────▶│                                 │
       │                                  │ 2. 内部推理：                   │
       │                                  │   - 编码 prompt                 │
       │                                  │   - meta-model 预测最佳模型     │
       │                                  │   - 返回 {provider, session_id} │
       │                                  │                                 │
       │ 3. { session_id, provider,       │                                 │
       │      model_name }                │                                 │
       │◀─────────────────────────────────│                                 │
       │                                  │                                 │
       │ 4. client.chat.completions.create(messages, model='gpt-4o-mini')    │
       │────────────────────────────────────────────────────────────────────▶
       │                                                                     │
       │ 5. (可选) 反馈：client.session.create_feedback(                     │
       │       session_id, score, actual_model)                              │
       │─────────────────────────────────▶                                  │
       │                                  │ 6. 用于路由器的在线/离线学习    │
       │                                  │                                 │
```

### 2.3 路由器原理

#### 2.3.1 Pre-trained Router（开箱即用）

Not Diamond 内部有一个**预训练好的 meta-model**：

- 输入：`messages`（OpenAI 格式）+ `llm_providers`（候选模型列表）+ `tradeoff`（质量/成本/延迟偏好）
- 输出：建议调用的 `provider` + `model`，附带 `session_id`

论文里解释的原理大致对应：
- 把 prompt 编码为 embedding
- 喂给一个轻量级分类/回归模型（meta-model）
- 模型预测每个候选 LLM 的"预期得分"
- 用 Pareto 前沿做 cost/quality trade-off

#### 2.3.2 Custom Router（自训练）

你上传一份 **CSV 文件**给 Not Diamond 后端：

```
prompt, openai/gpt-5-2025-08-07/score, openai/gpt-5-2025-08-07/response,
         anthropic/claude-sonnet-4-5-20250929/score, anthropic/claude-sonnet-4-5-20250929/response,
         google/gemini-2.5-pro/score, google/gemini-2.5-pro/response,
         ...
```

- 最小样本数：**15**（prompt optimization 最小 25；custom router 15；prototype mode 3）
- 最大文件：5MB 或 10,000 samples
- 训练时间：几分钟到 1 小时（异步）
- 训练完会得到一个 `preference_id`，后续 select_model 调用时带上

**支持混合自定义模型**——可以把你自己 fine-tune 的模型或私有 inference endpoint 也加进候选列表：

```python
custom_model = {
    "provider": "custom",
    "model": "my-finetuned-model",
    "is_custom": True,
    "context_length": 200000,
    "input_price": 0.1,    # USD / 1M tokens
    "output_price": 0.2,   # USD / 1M tokens
    "latency": 0.01        # seconds to first token
}
```

约束：自定义 model 名不能和已有模型冲突，且只能含一个 `/`。

#### 2.3.3 Prompt Optimization（独立产品线）

这是一条和 routing **完全独立**的产品线，做的事情更接近 DSPy：

- 输入：你的现状（system prompt + user message template + 评估数据集 golden records）
- 输出：针对每个 target model **重新优化过的** system prompt + template
- 算法：在 agent loop 里跑 LLM 自己迭代 prompt，受你提供的 eval metric 约束（RL-guided + self-reflection）
- 评估指标：LLMaaJ:Sem_Sim_1（默认）、JSON_Match、EXACT_MATCH、BLEU、ROUGE、METEOR、RAGAS_FAITHFULNESS、RAGAS_RELEVANCE，或自定义 LLM-as-a-judge

**典型工作流**（来自文档）：

```
1. POST /v2/prompt/optimize        → optimization_run_id
2. GET  /v2/prompt/optimizeStatus  → 轮询 status
3. GET  /v2/prompt/optimizeResults → 拿到每个 target model 的优化 prompt + pre/post score
4. 生产中用优化后的 prompt + 各自的 target model
```

**响应结构**（关键字段）：

```json
{
  "origin_model": {
    "model_name": "openai/gpt-4o-2024-08-06",
    "score": 0.8,
    "evals": {"LLMaaJ:Sem_Sim_1": 0.8},
    "system_prompt": "...",
    "user_message_template": "..."
  },
  "target_models": [
    {
      "model_name": "anthropic/claude-sonnet-4-20250514",
      "pre_optimization_score": 0.64,
      "post_optimization_score": 0.8,
      "system_prompt": "...",
      "user_message_template": "...",
      "user_message_template_fields": ["..."]
    }
  ]
}
```

### 2.4 路由决策的高级控制

```python
# 1) 三种 tradeoff 模式
tradeoff="cost"     # 优先便宜
tradeoff="latency"  # 优先快
tradeoff=None       # 优先质量（默认）

# 2) cost/quality 连续混合（0-10）
# - 0: pure quality
# - 10: cheapest
# - 5: balanced
# 注意：tradeoff 和 cost_quality_tradeoff 互斥（同时设置会 422）
# 注意：cost_quality_tradeoff 只支持 pre-trained router，不支持 custom router
result = client.model_router.select_model(
    llm_providers=[...],
    messages=[...],
    cost_quality_tradeoff=5
)

# 3) 自定义 model attributes（per-model override）
# 走 "Defining additional configurations" 文档：可以为某个模型指定自定义 cost/latency

# 4) 反馈回路
result = client.model_router.select_model(...)
# ... 调 LLM 拿到真实 response ...
client.session.create_feedback(
    session_id=result.session_id,
    score=0.9,
    actual_model="openai/gpt-4o-mini"
)
```

---

## 3. 协议 / 接口支持

### 3.1 输入协议

- ✅ **OpenAI Chat Format**（`messages=[{"role": ..., "content": ...}]`）—— 主要接口
- ✅ **Tool / Function calling**（doc 明确提到：compatible models 支持 tool call；select_model 支持 function calling）
- ❌ **Anthropic 原生 messages 格式**（需要你在自己的 LLM 客户端做转换）
- ❌ **Google Gemini 原生格式**（同上）
- ✅ **MCP 客户端支持**：未官方声明（架构上不冲突，因为 routing 本身是 model selection）

### 3.2 输出 / 状态管理

- ✅ **`session_id`**：每个 routing 推荐返回唯一 ID，用于反馈和 debug
- ✅ **HTTP REST API**（`/v2/modelrouter/modelSelect`, `/v2/pzn/trainCustomRouter`, `/v2/prompt/optimize` 等）
- ✅ **Python SDK**（基于 httpx + Pydantic，Python ≥ 3.9）
- ✅ **TypeScript SDK**（基于 fetch）
- ❌ **没有 OpenAI 兼容的 `/v1/chat/completions` 端点**——Not Diamond **不代理** LLM 请求

### 3.3 API 端点清单（来自 /llms.txt 索引）

```
GET  /v2/models                       # 列出所有支持的 text 模型（含价格、context、延迟）
                                      # 缓存 1 小时
                                      # 支持 ?provider=openai&provider=anthropic
                                      # 支持 ?openrouter_only=true

POST /v2/modelrouter/modelSelect      # 路由推荐
                                      # 输入: messages, llm_providers, tradeoff,
                                      #       cost_quality_tradeoff, preference_id
                                      # 输出: provider, model, session_id

POST /v2/pzn/trainCustomRouter        # 训练 custom router
                                      # 输入: dataset_file (CSV), llm_providers,
                                      #       prompt_column, language, maximize
                                      # 输出: preference_id
                                      # 约束: 最小 15 样本, 最大 5MB / 10k 行

POST /v2/preferences/userPreferenceCreate  # 创建 preference（个性化路由）

GET  /v2/prompt/optimizeStatus/{id}   # 轮询 prompt optimization 状态
                                      # 状态: created, queued, processing, completed, failed
                                      # queued 时返回 queue_position

POST /v2/prompt/optimize              # 启动 prompt 优化
                                      # 输入: system_prompt, template, fields,
                                      #       goldens, origin_model, target_models,
                                      #       evaluation_metric 或 evaluation_config,
                                      #       prototype_mode
                                      # 输出: optimization_run_id
                                      # 约束: 最小 25 样本 (prototype 模式 3)

GET  /v2/prompt/optimizeResults/{id}  # 拉取优化结果
                                      # 输出: 每个 target model 的 system_prompt,
                                      #       user_message_template, pre/post score

GET  /v2/prompt/optimize/{id}/costs   # 优化过程的成本明细
```

### 3.4 错误码

来自 Python SDK 的 errors 文档：

| 状态码 | 异常类 |
|---|---|
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 403 | `PermissionDeniedError` |
| 404 | `NotFoundError` |
| 422 | `UnprocessableEntityError`（参数互斥、custom router + cost_quality_tradeoff 冲突等） |
| 429 | `RateLimitError`（当前默认 50 RPS） |
| ≥500 | `InternalServerError` |
| N/A | `APIConnectionError`（网络问题） |

---

## 4. 支持的模型（2026-06 抓取）

### 4.1 Routing 支持的模型

| Provider | 模型示例（节选） |
|---|---|
| **OpenAI** | gpt-4o, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-5, gpt-5-mini, gpt-5-nano, gpt-5.1, gpt-5.2, gpt-5.2-pro, gpt-5.4-pro, gpt-5.4-mini, gpt-5.4-nano, gpt-5.5, gpt-oss-120b, o3 等 |
| **Anthropic** | claude-opus-4.7, claude-opus-4.6, claude-opus-4.5, claude-opus-4.1, claude-opus-4.0, claude-sonnet-4.6, claude-sonnet-4.5, claude-sonnet-4.0, claude-haiku-4.5, claude-3.7-sonnet, claude-3.5-haiku, claude-3-haiku |
| **Google** | gemini-3.1-pro-preview, gemini-3.1-flash-lite-preview, gemini-3-pro-preview, gemini-3-flash-preview, gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-2.0-flash, gemma-4-31b-it |
| **X.AI** | grok-4.3, grok-4, grok-4-fast, grok-4.1-fast, grok-3, grok-3-mini |
| **Mistral** | mistral-large-latest, mistral-large-2407, mistral-medium-latest, mistral-small-latest, open-mistral-7b, open-mistral-nemo, open-mixtral-8x22b, open-mixtral-8x7b, codestral-latest |
| **Cohere** | command-r-plus, command-r |
| **DeepSeek** | deepseek-v4-flash, deepseek-v4-pro |
| **Qwen** | qwen3.6-plus |
| **Inception** | mercury-2 |
| **Perplexity** | sonar, sonar-pro |
| **Replicate** | meta-llama-3-70b-instruct, meta-llama-3-8b-instruct, mixtral-8x7b-instruct-v0.1, mistral-7b-instruct-v0.2, meta-llama-3.1-405b-instruct（仅部分支持 routing） |
| **Together AI** | Llama-3-70b-chat-hf, Meta-Llama-3.1-8B/70B/405B-Instruct-Turbo, Qwen2-72B-Instruct, Mixtral-8x22B/8x7B, Mistral-7B, DeepSeek-R1（仅部分支持 routing） |

> 注：Replicate 和 TogetherAI 的列表相对静态，新模型跟进速度明显比 OpenAI/Anthropic 慢。

### 4.2 Prompt Optimization 支持的模型（更窄）

文档明确列出的 prompt optimization models 较少（约 20 个）：

- **OpenAI**（gpt-4o 全系, gpt-4.1 全系, gpt-5 全系到 gpt-5.2）
- **Anthropic**（claude-sonnet-4, claude-sonnet-4.5, claude-opus-4, claude-3-7-sonnet）
- **Google**（gemini-2.5-flash/pro, gemini-3-pro/flash-preview）
- **Mistral**（mistral-large-2411）
- **Qwen**（qwen3-14b, qwen3-32b, qwen3-235b-a22b）
- **Meta**（llama-3.1-8b/70b/405b-instruct）
- **Moonshot**（kimi-k2-thinking）
- **OpenRouter**（gpt-oss-120b, llama-3.3-70b-instruct）

> 团队明确说："We are continuously expanding our list of supported models for prompt optimization. For custom deployments we can provide an interface that will allow you to optimize against any model of your choosing, including private and local models."

### 4.3 Custom Model 支持

不限定 Not Diamond 的官方列表——任何 LLM 都可以：

- 必须填 `context_length`, `input_price`, `output_price`, `latency` 四个字段
- 命名必须唯一（不能和已有模型同名）
- 名字里最多一个 `/`
- 可以是 fine-tuned model、私有 inference endpoint、agent

---

## 5. 性能数据

### 5.1 路由推荐延迟（官方）

> "The latency of each routing recommendation will range from 10–100ms depending on the amount of data used to train your router. Additional network latency may be incurred depending on your infrastructure setup."

- **Pre-trained router**：**10–100ms**（一次额外 RTT）
- **Custom router**：同上，但取决于训练数据量
- 加上业务自己的 LLM 调用延迟，**整体是 1 个额外网络跳 + 1 个额外 RTT**（不是 proxy 模式，没有 double-hop 风险）

### 5.2 官方宣称的成本节省

| 场景 | 节省比例 |
|---|---|
| Coding agent（pre-trained code router, EA） | **30%+ cost savings** |
| 通用 chat routing | "Significant"（FAQ 没具体数字） |
| Custom router | 取决于你的数据分布（团队 cite "5%+ accuracy gains"） |

### 5.3 官方宣称的准确度提升

- "Accuracy gains 5%+"
- "Faster dev cycles 2x"

### 5.4 速率限制

- **50 RPS**（默认；over-the-quota 返回 429 + Retry-After）
- 业务高负载需要联系销售

### 5.5 RouterBench 论文（arXiv:2403.12031）的实验数据

论文（v2，2024-03-28）的关键发现：

- 收集了 **405k+ 推理结果**，覆盖 8 个任务 × 11 个 LLM
- 11 个 LLM 包括 GPT-4、GPT-3.5、Mistral、Mixtral、Claude 等
- 8 个任务：MMLU、HellaSwag、ARC、GSM8K、HumanEval 等
- **核心结论 1**：相同性能水平下，**不同 LLM 的 cost 可以差 2-5×**——这正是 routing 的价值
- **核心结论 2**：简单的 routing（如"易问小模型，难问大模型"）就能拿到显著收益
- **核心结论 3**：一些早期 routing 机制泛化能力差，**Not Diamond 的 meta-model 架构**在复杂任务上明显更优

论文提出的 **AIQ (Area under the cost-quality curve)** 指标已成为 routing 领域的标准度量之一。

### 5.6 实测 benchmark（独立来源）

> 公开的独立 benchmark 仍然有限，论文后的下游工作（Predictive Pager、CARGO、HybridLLM、RouteLLM、FrugalGPT 等）在不同任务上各有胜负。Not Diamond 官方没公布过第三方独立复现报告。

---

## 6. 部署方式

### 6.1 SaaS（默认）

```
pip install notdiamond
export NOTDIAMOND_API_KEY=...
python your_routing_app.py
```

### 6.2 Zero Data Retention（ZDR）

文档明文：

> "Not Diamond is SOC-2 and ISO 27001 compliant. We provide custom ZDR policies, VPC deployments, and 24/7 on-call support to the most sophisticated AI teams in the world."

- ZDR：notdiamond 不留存 prompt / response 数据
- VPC：可部署在客户的 VPC / on-prem

### 6.3 Local Deployment（私有化）

定价页的 "Custom" plan 明文包含：

- Agent optimization
- Bulk pricing
- Bring your own models
- Custom evaluation metrics
- Priority API job queue
- **More target models per run**（SAAS 默认 4 个 target models）
- **More custom routers**（SAAS 默认 3 个 custom router）
- Custom ZDR policies
- 24/7 support

要拿到 local deploy / 私有化部署需要 contact sales（calendly）。

### 6.4 集成模式

文档明确"stack-agnostic"，常见组合：

| 业务架构 | Not Diamond 在哪 |
|---|---|
| 直接调 LLM 的脚本 | `select_model()` 返回结果后用 `openai`/`anthropic` SDK 直接调 |
| 用 Portkey/LiteLLM/OpenRouter 当 gateway | `select_model()` 返回结果后用 Portkey/LiteLLM/OpenRouter 调（gate 仍在自己手里） |
| 用 Claude Code / Codex 这种 coding agent | "We have an early access program for select developers and enterprises to try the next generation of our router which is purpose-built for long-horizon coding agent workloads" |
| 自建 inference 集群（vLLM、TGI） | 把自建 endpoint 注册为 custom model |

---

## 7. 成本模型

### 7.1 Pay-as-you-go（开发者 / 小团队）

#### Intelligent Routing

| 配额 | 价格 |
|---|---|
| 每月 10K routing 推荐 | **免费** |
| 之后每 10K 推荐 | **$10** |

> "Each API request returns a single routing recommendation, independent of input size."

—— **不按 token 计费，只按"推荐次数"计费**。这跟 OpenAI / Anthropic 的 token billing 模型完全不同。

#### Prompt Optimization

| 配额 | 价格 |
|---|---|
| 每月 10 次成功优化 | **免费** |
| 之后每次成功优化 | **$20** |
| 每次最多 target model 数 | 4 个（custom plan 不限） |
| 单次优化典型成本 | $0.10 - $2.00（取决于 target model 数量和评估样例数） |

#### Custom Router（SAAS plan 内）

- **3 个 free custom routers**（含在 pay-as-you-go 里）
- 训练数据集限制：5MB 或 10,000 samples
- 训练时间：几分钟到 1 小时

### 7.2 Custom / Enterprise

- 单独的 bulk pricing
- 折扣：startup / researcher 可申请（`contact@notdiamond.ai`）

### 7.3 整体成本举例

假设一个 coding agent 月跑 1M 次 LLM 调用：

| 计费维度 | 数字 |
|---|---|
| Routing 推荐 | 1M × $1/1k = $1000 |
| LLM 实际调用 | 取决于你用什么模型（Not Diamond 不抽成） |
| Custom router | $0（3 个 free） |
| Prompt optimization | $0-200（按优化频率） |
| **总 Not Diamond 成本** | **$1000-1200**（不含 LLM 本身） |

如果通过它把 GPT-5 调用换成 GPT-5-mini 30%，按 GPT-5 约 $5/M input + $15/M output 算，省下的钱远超过 routing 本身费用。

---

## 8. 安全 / 合规

### 8.1 合规

- ✅ **SOC-2**
- ✅ **ISO 27001**
- ✅ **ZDR（Zero Data Retention）**
- ✅ **VPC 部署**（Custom plan）

### 8.2 数据流加密

> "Our Python SDK uses `requests==2.31.0` and `urllib3==2.2.1` which encrypts data through HTTPS with TLS 1.3 (with fallback to TLS 1.2 if necessary). Our database is encrypted using AES-256, and all access to the database is also encrypted in transit using TLS certificates."

### 8.3 数据隐私架构

> "For our routing features, we operate client-side rather than as a proxy—all LLM requests go directly from your application to the model providers."

—— 这是 Not Diamond **最重要的安全卖点**：

- 你的 prompt 和 LLM 响应**完全不经过** Not Diamond 的服务器
- Not Diamond 只看到"为了让 meta-model 决策而需要看的 prompt 摘要/embedding"
- 这对金融、医疗、政务客户至关重要

### 8.4 速率限制

- 50 RPS（SAAS 默认）
- 触发 429 后建议：exponential backoff + queue + cache

---

## 9. 生态

### 9.1 SDK

| 语言 | 仓库 | 备注 |
|---|---|---|
| Python | `pip install notdiamond`（https://github.com/Not-Diamond/not-diamond-python） | 官方，活跃维护；基于 httpx + Pydantic，Python ≥ 3.9 |
| TypeScript / JavaScript | `npm install notdiamond` | 官方，活跃维护；API 设计与 Python 一致 |
| REST | https://docs.notdiamond.ai/reference | 直接 curl / fetch / Postman 调 |

### 9.2 协作生态

Not Diamond 自己**不做 gateway**，天然适合和以下产品组合：

- **Portkey**（gateway 层：fail-over, logging, caching, guardrails）
- **LiteLLM**（开源 LLM proxy；同 gateway 层）
- **OpenRouter**（统一 LLM API + 多家 provider）
- **Unify**（同类型智能 routing SaaS；直接竞品）
- **Helicone**（observability + routing；功能有重叠）
- **Langfuse / LangSmith / Arize Phoenix**（observability；可观察 Not Diamond 的决策）
- **DSPy**（Prompt Optimization 算法层；Not Diamond 是它的产品化实现之一）
- **Cloudflare AI Gateway**（edge gateway + caching）
- **Higress / APISIX / Kong / Envoy**（通用 API Gateway + AI 插件）

### 9.3 论文 / 学术影响

- **RouterBench**（arXiv:2403.12031）—— 第一篇 LLM router benchmark 论文，被后续工作大量引用
- 论文合作者：Qitian Jason Hu、Jacob Bieker、Xiuyu Li、Nan Jiang、Benjamin Keigwin、Gaurav Ranganath、Kurt Keutzer、Shriyash Kaustubh Upadhyay（其中多位仍在 Not Diamond 团队）
- arXiv 引用（截至 2026 上半年）：被 FrugalGPT、RouteLLM、HybridLLM、CARGO、ZOOTER、Tryage 等多篇后续工作引用

### 9.4 OSS 资产

- **withmartian/routerbench**（GitHub）—— benchmark 数据集 + 评估框架 + 路由算法实现
- **Hugging Face dataset** `withmartian/routerbench` —— 405k+ 推理结果
- Python SDK 是 **source-available**（`not-diamond-python`）：用户可看源码、提 PR；不是 MIT/Apache

---

## 10. 客户案例

> 公开案例有限，**Not Diamond 没有公开 logo 墙**，但从 about 投资人名单 + 公开访谈可以反推目标客户画像：

### 10.1 直接目标客户

- **Coding agent 公司**（Cursor、Cognition、Anthropic、Codeium、Continue.dev、Replit Agent 一类）—— pre-trained code router 早期访问计划主攻
- **大型企业 AI 平台**（需要 SOC-2、ISO 27001、VPC 部署）—— Custom plan 主攻
- **AI 创业公司**（需要 cost optimization）—— Pay-as-you-go 主攻
- **Startups / Researchers** —— 有折扣

### 10.2 间接信号

- Notion 是投资人 → 大概率是客户（Notion AI）
- Vercel 是投资人 → 大概率是客户（v0 / AI SDK 路径）
- Baseten 是投资人 → 大概率是客户（Baseten 自家也有 routing 概念）
- GitHub 是投资人 → GitHub Copilot 路径有合作可能

### 10.3 公开背书

投资人名单本身就是背书（Jeff Dean 投了一家做 routing 的公司，说明 routing 在顶级 AI 研究者眼中是基础设施级问题）。

---

## 11. 优劣势分析

### 11.1 优势

1. **架构差异化最彻底**：唯一不代理 LLM 请求的"routing"产品。**零 prompt 数据暴露风险**。
2. **学术血统最硬**：RouterBench 论文是 routing 领域的奠基性工作，团队拥有学术话语权。
3. **投资人质量极高**：Jeff Dean、Ion Stoica、Julien Chaumond、Tom Preston-Werner 等；信号意义远大于资金意义。
4. **产品矩阵最干净**：路由 + 训练 + 优化三件套，每件都做深，不试图吞下整个 gateway 市场。
5. **计费模型友好**：按"推荐次数"计费，不按 token；和 OpenAI / Anthropic 这种按 token 的计费正交，**可预测性极高**。
6. **Prompt Optimization 是杀手锏**：和 DSPy 同台竞技但做成 SaaS；这是其他 AI Gateway（Portkey、LiteLLM 等）完全没有的功能。
7. **Custom router 极简门槛**：15 个样本就能训练；比 fine-tune 一个 router 简单 100 倍。
8. **Coding agent 垂直深耕**：pre-trained code router 是市面上第一个专门为 coding agent 优化的路由（考虑 cache pricing 之后）。
9. **安全合规齐全**：SOC-2 + ISO 27001 + ZDR + VPC；金融/医疗/政务可走。
10. **和所有 gateway 正交**：你可以在 Portkey / LiteLLM / OpenRouter 前面再套一层 Not Diamond 拿 routing 决策。

### 11.2 劣势 / 风险

1. **不是 gateway**：意味着用户要自己处理 fail-over、retries、logging、caching、rate limiting、load balancing。这些 Not Diamond **都不做**。
2. **增加一次网络跳**：每次调用都多一次 10-100ms 的额外 RTT（虽然不大，但对 latency-sensitive 应用不友好）。
3. **依赖元数据质量**：meta-model 决策的依据是 prompt embedding；如果你有大量 fine-tuned 私有模型 / 私有数据 routing 效果完全取决于你训练 custom router 的数据质量。
4. **生态单薄**：客户端 SDK 只有 Python + TypeScript；没有 Go、Rust、Java 官方 SDK；没有 VS Code / JetBrains 插件。
5. **没有自带的 observability**：路由决策日志、AB test、cost analytics 这些是 Portkey/Helicone 的强项，Not Diamond 这块基本留白（虽然可以通过 session_id 自己接 Langfuse / LangSmith）。
6. **价格不透明**：定制 router、target model 数量、API priority 这些都锁在"contact sales"里。
7. **公司规模小**：team 自称"small, dedicated"；长期支持 / 长期 roadmap / 抗风险能力不如 Portkey（背后有 Portkey AI 公司）/ LiteLLM（开源社区庞大）。
8. **Pre-trained router 黑盒**：你不知道 meta-model 的训练数据、训练方式，只能信官方说"我训得好"；这对强解释性需求场景不友好。
9. **没有 guardrails**：PII detection、prompt injection defense、content moderation 这些安全功能是 Not Diamond 不做的。
10. **没有 multi-modal routing**：路由的候选必须都是 text 模型；图片、语音、视频路由不涉及。
11. **Routing 模型支持延迟于市场**：Replicate / TogetherAI / Cohere 的新模型上线明显比 OpenAI / Anthropic 慢（文档可证）。

---

## 12. 与其他产品的对比

### 12.1 一图对比（核心维度）

| 维度 | **Not Diamond** | **Portkey** | **LiteLLM** | **OpenRouter** | **Unify** | **Helicone** | **Martian** (前 Not Diamond) |
|---|---|---|---|---|---|---|---|
| 定位 | Meta-model router + Prompt optimization | AI gateway (proxy) | LLM proxy (proxy) | Unified LLM API (proxy) | Model router (proxy) | Observability + routing | 同 Not Diamond |
| 代理 LLM 请求？ | ❌ 不代理 | ✅ 代理 | ✅ 代理 | ✅ 代理 | ✅ 代理 | ✅ 代理 | ❌ 不代理 |
| 路由依据 | Trained meta-model | 权重 / A/B / 规则 / 失败重试 | 规则 / cost / 失败重试 | 规则 / 偏好 | Trained router | 简单规则 | 同 ND |
| 训练自定义路由 | ✅ CSV 上传，15 样本起 | ❌ | ❌ | ❌ | 部分支持 | ❌ | 同 ND |
| Prompt optimization | ✅ 独立产品线 | ❌ | ❌ | ❌ | ❌ | ❌ | 同 ND |
| Fail-over | ❌（你自己做） | ✅ 核心功能 | ✅ 核心功能 | ❌（按 provider 选） | ✅ | ❌ | 同 ND |
| Observability | ❌ | ✅ 详细 logs | ✅ logs + callbacks | ❌ | ✅ 基础 | ✅ 极强 | 同 ND |
| Caching | ❌ | ✅ semantic cache | ✅ | ❌ | ❌ | ✅ | 同 ND |
| Guardrails | ❌ | ✅ | ⚠️ 基础 | ❌ | ❌ | ❌ | 同 ND |
| 部署模式 | SaaS + ZDR + VPC | SaaS + 自部署 | 自部署（OSS） | 仅 SaaS | SaaS | SaaS + 自部署 | 同 ND |
| License | Closed source | Closed source + 自部署 | MIT（OSS） | Closed source | Closed source | Closed source | 同 ND |
| 计费 | 按 routing 推荐次数 + 优化次数 | 按 token 用量 | OSS 免费 / 企业付费 | 按 token 抽佣 | 按 token | 按事件 | 同 ND |
| 投资人质量 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | N/A（OSS） | ⭐⭐ | ⭐⭐ | ⭐⭐ | 同 ND |
| 论文 / 学术影响 | ⭐⭐⭐⭐⭐（RouterBench） | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ | 同 ND |

### 12.2 选型决策树

```
你的需求是什么？
│
├─ 我想要 fail-over / rate-limit / cache / observability
│   └─→ 选 Portkey / LiteLLM / Helicone
│
├─ 我想要"一个 API 调用所有 LLM provider"
│   └─→ 选 OpenRouter / LiteLLM / Portkey
│
├─ 我想要"为每个 prompt 智能选最便宜的模型、保持质量"
│   └─→ 选 Not Diamond / Unify
│       │
│       ├─ 我有私有模型 / 自训练数据
│       │   └─→ 选 Not Diamond（custom router 训练最成熟）
│       │
│       └─ 我是创业公司，标准化 prompt 路由
│           └─→ 选 Unify / Not Diamond 都行
│
├─ 我想要"为我的 coding agent 砍 30% 成本"
│   └─→ 选 Not Diamond（code router 是市面上唯一的）
│
├─ 我想要"自动优化我的 prompt 让它跨模型都好使"
│   └─→ 选 Not Diamond / DSPy
│       │
│       ├─ 我想自己控代码
│       │   └─→ DSPy（开源）
│       └─ 我想要 SaaS / 不写代码
│           └─→ Not Diamond
│
└─ 我想要"学术严肃度的 routing research"
    └─→ 选 Not Diamond（RouterBench 出品）
```

### 12.3 关键差异点深度对比

#### Not Diamond vs Unify（同为智能 routing SaaS）

| 维度 | Not Diamond | Unify |
|---|---|---|
| 架构 | 不代理，client-side | 代理（proxy） |
| 训练数据 | ✅ Custom router + Prompt optimization | ⚠️ Custom router 能力较弱 |
| Coding agent 优化 | ✅ Pre-trained code router | ❌ |
| 自训练门槛 | 15 样本 | 类似 |
| 投资人 | Jeff Dean 等 | Lightspeed 等 |
| Prompt 优化 | ✅ 独立产品线 | ❌ |

#### Not Diamond vs Portkey（架构对立面）

| 维度 | Not Diamond | Portkey |
|---|---|---|
| 在请求链路位置 | 决策点（不代理） | 网关（代理） |
| 失败重试 | ❌ | ✅ 核心卖点 |
| 缓存 | ❌ | ✅ semantic cache |
| Observability | ❌ | ✅ 详细 logs/dashboard |
| Guardrails | ❌ | ✅ |
| 智能选模型 | ✅ trained meta-model | ⚠️ A/B / 权重 / 简单规则 |
| Prompt 优化 | ✅ | ❌ |
| 合规 | SOC-2 + ISO 27001 + ZDR + VPC | SOC-2 |

> 实际上**两者是互补的**——很多生产架构是 `Not Diamond (routing decision) → Portkey (execute + observability)`。

#### Not Diamond vs Martian（公司沿革）

Not Diamond 是 Martian 的**品牌升级**。RouterBench 论文 2024 年发表时公司叫 Martian；2024 下半年到 2025 上半年更名为 Not Diamond 并把 routing 商业化。

#### Not Diamond vs OpenRouter

OpenRouter 是"统一 LLM API + billing layer"，定位是给"一个 key 调所有模型"。Not Diamond 是"在 N 个模型里选最合适的那个"。两者是**完全不同的需求**。

#### Not Diamond vs Helicone

Helicone 主打 observability（请求日志、cost analytics、user tracking），附带 simple routing。Not Diamond 主打智能 routing，**没有 observability dashboard**。可以混用：`Not Diamond` 决策 → `Helicone` 记录。

#### Not Diamond vs LangSmith

LangSmith 是 LangChain 出的 LLM dev 平台，定位是"调试、评估、监控 LLM 应用"。Not Diamond 是"路由 + 优化 LLM 应用"。两者几乎正交。

---

## 13. 风险与未解问题

### 13.1 Not Diamond 自家未明确的

- ❓ **Pre-trained router 的训练集**是什么规模、什么来源、什么分布？
- ❓ **Meta-model 的架构**是什么？Transformer? MLP? Ensemble? 论文没细说。
- ❓ **Cost / Latency 数据来源**是官方 pricing page 还是 historical inference？精度如何？
- ❓ **Prompt optimization 的具体算法**——只是 RL + self-reflection，还是用了 DSPy / OPRO / PromptAgent？ 文档说"RL-guided + self-reflective"，没给具体引用。
- ❓ **Custom router 的更新频率**——`override=True` 后是 incremental training 还是从头训？

### 13.2 长期风险

- **如果 OpenAI / Anthropic 自家做"smart routing"**（OpenAI 已经在做"模型按 query 自动选"的尝试），Not Diamond 的价值会被压缩。
- **如果 fine-tune 一个超大模型比 routing 更便宜**，routing 的 ROI 会被质疑。
- **如果 OpenRouter / Together AI / Fireworks 之类"廉价模型池"**把 frontier model 价格打到 $1/M 以下，routing 节省的成本空间会缩小。
- **Coding agent 垂直化**（Cursor 自己训 routing 模型）会让 Not Diamond 的 code router 价值减弱。

### 13.3 我的判断（2026-06）

- **短期（6-12 个月）**：Not Diamond 在"routing"细分赛道**几乎无敌**。投资人质量 + 学术血统 + 唯一的产品定位 = 难以替代。
- **中期（1-2 年）**：和 Portkey / LiteLLM / Helicone 形成"routing + observability + caching"组合栈。
- **长期（2+ 年）**：面临 OpenAI / Anthropic 自家 routing + 模型价格崩塌的双重风险；公司必须向"agent optimization"或"agent harness optimization"延展才有活路（看 Custom plan 已经在做）。

---

## 14. 附录：完整代码示例（Python）

```python
"""
Not Diamond 完整使用示例
覆盖：routing、custom router、prompt optimization、feedback loop
"""

import os
import time
import json
import pandas as pd
from pathlib import Path
from notdiamond import NotDiamond
from openai import OpenAI

# ============================================================
# 1) 基础：5 分钟跑通 routing
# ============================================================
os.environ["NOTDIAMOND_API_KEY"] = "sk-..."

client = NotDiamond(api_key=os.environ.get("NOTDIAMOND_API_KEY"))

result = client.model_router.select_model(
    messages=[
        {"role": "system", "content": "You are a world-class programmer."},
        {"role": "user", "content": "Write a Python quicksort in 4 lines."},
    ],
    llm_providers=[
        {"provider": "openai", "model": "gpt-5-2025-08-07"},
        {"provider": "openai", "model": "gpt-5-mini-2025-08-07"},
        {"provider": "openai", "model": "gpt-5-nano-2025-08-07"},
        {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
        {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
        {"provider": "google", "model": "gemini-2.5-pro"},
        {"provider": "google", "model": "gemini-2.5-flash"},
    ],
    tradeoff="cost",  # 优先便宜
)

print("Session ID:", result.session_id)
print("Selected model:", result.provider.model)

# ============================================================
# 2) 实际调 LLM（你自己用 OpenAI / Anthropic SDK）
# ============================================================
oai = OpenAI()
completion = oai.chat.completions.create(
    model=result.provider.model,
    messages=[
        {"role": "system", "content": "You are a world-class programmer."},
        {"role": "user", "content": "Write a Python quicksort in 4 lines."},
    ],
)
print(completion.choices[0].message.content)

# ============================================================
# 3) 反馈回路：告诉 Not Diamond 实际表现
# ============================================================
client.session.create_feedback(
    session_id=result.session_id,
    score=0.9,                       # 0-1 之间，你自己的评估
    actual_model=result.provider.model,
)

# ============================================================
# 4) 连续 cost/quality 权衡（0-10）
# ============================================================
result_balanced = client.model_router.select_model(
    messages=[{"role": "user", "content": "Summarize this article: ..."}],
    llm_providers=[
        {"provider": "openai", "model": "gpt-5-2025-08-07"},
        {"provider": "openai", "model": "gpt-5-mini-2025-08-07"},
    ],
    cost_quality_tradeoff=5,  # 0=quality-first, 10=cheapest
)

# ============================================================
# 5) 自定义 model 加入候选
# ============================================================
custom_model = {
    "provider": "custom",
    "model": "my-finetuned-llama",
    "is_custom": True,
    "context_length": 128_000,
    "input_price": 0.1,
    "output_price": 0.2,
    "latency": 0.05,
}

result_custom = client.model_router.select_model(
    messages=[{"role": "user", "content": "Hello"}],
    llm_providers=[
        {"provider": "openai", "model": "gpt-4o"},
        custom_model,
    ],
    tradeoff="cost",
)

# ============================================================
# 6) 训练 custom router
# ============================================================
df = pd.read_csv("humaneval.csv")
# CSV 列: prompt, openai/gpt-5-2025-08-07/score, openai/gpt-5-2025-08-07/response,
#        anthropic/claude-sonnet-4-5-20250929/score, anthropic/claude-sonnet-4-5-20250929/response,
#        ...

llm_providers = [
    {"provider": "openai", "model": "gpt-5-2025-08-07"},
    {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    {"provider": "google", "model": "gemini-2.5-pro"},
    {"provider": "openai", "model": "gpt-5-mini-2025-08-07"},
    {"provider": "anthropic", "model": "claude-opus-4-20250514"},
]

with open("humaneval.csv", "rb") as f:
    response = client.custom_router.train_custom_router(
        dataset_file=f,
        language="english",
        llm_providers=json.dumps(llm_providers),
        maximize=True,
        prompt_column="Input",
    )

preference_id = response.preference_id
print("Trained custom router with preference_id:", preference_id)

# 用 custom router 路由
result_with_custom = client.model_router.select_model(
    messages=[{"role": "user", "content": "Write merge sort in 3 lines."}],
    llm_providers=llm_providers,
    preference_id=preference_id,
)
print("Custom router chose:", result_with_custom.provider.model)

# ============================================================
# 7) 更新 custom router
# ============================================================
with open("humaneval.csv", "rb") as f:
    response = client.custom_router.train_custom_router(
        dataset_file=f,
        language="english",
        llm_providers=json.dumps(llm_providers),
        maximize=True,
        prompt_column="Input",
        preference_id=preference_id,
        override=True,  # 覆盖之前的
    )

# ============================================================
# 8) Prompt Optimization
# ============================================================
result = client.prompt_optimization.optimize(
    system_prompt="You are a mathematical assistant that counts digits accurately.",
    template="Question: {question}\nAnswer:",
    fields=["question"],
    target_models=[
        {"model": "claude-sonnet-4-5-20250929", "provider": "anthropic"},
        {"model": "gemini-2.5-flash", "provider": "google"},
    ],
    train_goldens=[
        {"fields": {"question": "How many digits are in (23874045494*2789392485)?"}, "answer": "20"},
        {"fields": {"question": "How many odd digits are in (999*777*555*333*111)?"}, "answer": "10"},
        # 至少 25 个，prototype 模式可只 3 个
    ],
    test_goldens=[
        {"fields": {"question": "How many digits are in (9876543210*123456)?"}, "answer": "15"},
    ],
    evaluation_metric="LLMaaJ:Sem_Sim_1",
    prototype_mode=True,  # 快速原型
)

optimization_run_id = result.optimization_run_id
print("Optimization started:", optimization_run_id)

# 轮询状态
while True:
    status = client.prompt_optimization.get_optimization_status(optimization_run_id)
    print(f"Status: {status.status}")
    if status.status == "queued":
        print(f"Queue position: {status.queue_position}")
    if status.status in ["completed", "failed"]:
        break
    time.sleep(30)

# 拉取结果
if status.status == "completed":
    results = client.prompt_optimization.get_optimization_results(optimization_run_id)
    for target in results.target_models:
        print(f"\n{'='*50}")
        print(f"Model: {target.api_model_name}")
        print(f"Pre-opt score:  {target.pre_optimization_score:.3f}")
        print(f"Post-opt score: {target.post_optimization_score:.3f}")
        print(f"Optimized system prompt:\n{target.system_prompt}")
        print(f"Optimized template:\n{target.user_message_template}")
        print(f"Cost: ${target.cost:.4f}")

# ============================================================
# 9) 错误处理
# ============================================================
import notdiamond

try:
    client.prompt_optimization.optimize(
        system_prompt="...",
        template="...",
        fields=["q"],
        target_models=[{"model": "gpt-5-2025-08-07", "provider": "openai"}],
        train_goldens=[{"fields": {"q": "2+2?"}, "answer": "4"}],
        test_goldens=[{"fields": {"q": "3*3?"}, "answer": "9"}],
    )
except notdiamond.APIConnectionError as e:
    print("Network issue:", e.__cause__)
except notdiamond.RateLimitError as e:
    print("429 hit, backoff")
except notdiamond.APIStatusError as e:
    print("HTTP", e.status_code, e.response)

# ============================================================
# 10) 超时配置（Prompt Optimization 10-30 分钟，要调大）
# ============================================================
client = NotDiamond(
    api_key=os.environ.get("NOTDIAMOND_API_KEY"),
    timeout=httpx.Timeout(60.0, read=5.0, write=10.0, connect=2.0),
)

# 单次覆盖
client.with_options(timeout=120.0).prompt_optimization.get_optimization_status(
    optimization_run_id="your-run-id"
)
```

---

## 15. 参考资料

1. Not Diamond 官网：https://www.notdiamond.ai
2. Not Diamond 文档：https://docs.notdiamond.ai
3. Not Diamond 文档 LLM 索引：https://docs.notdiamond.ai/llms.txt
4. About 页：https://www.notdiamond.ai/about
5. 定价页：https://www.notdiamond.ai/pricing
6. Pre-trained router quickstart：https://docs.notdiamond.ai/docs/quickstart-routing
7. Pre-trained code router（EA）：https://docs.notdiamond.ai/docs/pre-trained-router-code
8. Custom router training：https://docs.notdiamond.ai/docs/router-training-quickstart
9. Custom model routing：https://docs.notdiamond.ai/docs/routing-between-custom-models
10. Key concepts：https://docs.notdiamond.ai/docs/key-concepts
11. Supported routing models：https://docs.notdiamond.ai/docs/llm-models
12. Supported prompt optimization models：https://docs.notdiamond.ai/docs/prompt-optimization-models
13. Prompt optimization quickstart：https://docs.notdiamond.ai/docs/quickstart-prompt-optimization
14. Classification example：https://docs.notdiamond.ai/docs/classification
15. Evaluation metrics：https://docs.notdiamond.ai/docs/evaluation-metrics
16. Security / privacy / local deployments：https://docs.notdiamond.ai/docs/privacy-security-and-local-deployments
17. Rate limits：https://docs.notdiamond.ai/docs/rate-limits
18. API keys：https://docs.notdiamond.ai/docs/api-keys
19. Support：https://docs.notdiamond.ai/docs/support
20. Python SDK：https://pypi.org/project/notdiamond/
21. Python SDK GitHub：https://github.com/Not-Diamond/not-diamond-python
22. Not Diamond npm：https://www.npmjs.com/package/notdiamond
23. Not Diamond API reference：https://docs.notdiamond.ai/reference
24. `POST /v2/modelrouter/modelSelect`：https://docs.notdiamond.ai/reference/token_model_select_v2_modelrouter_modelselect_post.md
25. `POST /v2/pzn/trainCustomRouter`：https://docs.notdiamond.ai/reference/train_custom_router_v2_pzn_traincustomrouter_post.md
26. `POST /v2/prompt/optimize`：https://docs.notdiamond.ai/reference/optimize_prompt_v2_prompt_optimize_post.md
27. `GET /v2/prompt/optimizeStatus/{id}`：https://docs.notdiamond.ai/reference/get_optimize_status_v2_prompt_optimizestatus__optimization_run_id__get.md
28. `GET /v2/prompt/optimizeResults/{id}`：https://docs.notdiamond.ai/reference/get_optimize_results_v2_prompt_optimizeresults__optimization_run_id__get.md
29. `GET /v2/prompt/optimize/{id}/costs`：https://docs.notdiamond.ai/reference/get_optimization_run_costs_v2_prompt_optimize__optimization_run_id__costs_get.md
30. `GET /v2/models`：https://docs.notdiamond.ai/reference/list_models_v2_models_get.md
31. RouterBench 论文：https://arxiv.org/abs/2403.12031
32. RouterBench 论文 HTML：https://arxiv.org/html/2403.12031v2
33. RouterBench GitHub：https://github.com/withmartian/routerbench
34. RouterBench 数据集：https://huggingface.co/datasets/withmartian/routerbench
35. Ragas 文档（FAITHFULNESS）：https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/
36. Ragas 文档（RELEVANCE）：https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/answer_relevance/
37. HuggingFace METEOR 文档：https://huggingface.co/spaces/evaluate-metric/meteor

---

## 16. 一句话总结

> **Not Diamond 是 LLM 应用层的"智能路由器 + Prompt 优化器"，是 RouterBench 论文团队商业化的成果。它不代理 LLM 请求，只用 10-100ms 给业务一个"用哪个模型最划算"的决策；可与 Portkey / LiteLLM / OpenRouter 等任意 gateway 正交组合。投资人阵容（Jeff Dean、Ion Stoica、Tom Preston-Werner 等）几乎独步 AI 圈。**

— 完 —
