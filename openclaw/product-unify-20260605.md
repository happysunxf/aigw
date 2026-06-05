# Unify AI — Deep Dive

> 调研日期：2026-06-05
> 调研对象：Unify AI Ltd.（unify.ai）+ 开源仓库 `unifyai/*`
> 关键发现：**Unify 已经从「LLM 智能路由 SaaS」演化为「AI 同事（agent teammate）平台」**，unillm 是其 LLM 路由层核心，但 LLM 路由只是 agent runtime 的一个组件。本报告同时覆盖 LLM 路由层（unillm）和 Agent 编排层（unity+unify+orchestra）。

---

## 0. 调研快照

| 维度 | 摘要 |
|---|---|
| 公司 | Unify AI Ltd., Covent Garden, London |
| 域名 | unify.ai / docs.unify.ai / api.unify.ai |
| GitHub | github.com/unifyai（11+ 仓库，unify/unillm/unity/orchestra 为主） |
| 主导产品 | **AI teammates**（"AI hires, not AI tools"） |
| LLM 路由核心 | `unifyai/unillm`（基于 LiteLLM 之上的 thin wrapper） |
| Agent runtime | `unifyai/unity`（dual-brain, CodeAct, steerable handles） |
| 后端 API | `unifyai/orchestra`（FastAPI + Postgres + pgvector） |
| 客户端 SDK | `unifyai/unify`（Python，状态/日志/项目/计费） |
| 定价 | $75/月 workspace，0% 平台费，credits 1:1 映射模型真实花费 |
| 协议 | OpenAI-compatible（chat completions）、流式、WebSocket voice |
| 早期定位 | LLM 智能路由 SaaS（benchmark/router），已被新方向替代 |

---

## 1. 项目背景与战略转向

### 1.1 早期 vs 现在

Unify AI 最早期在 2023-2024 年被业内熟知为 **LLM 智能路由平台**：
- 单一 endpoint 访问 50+ LLM
- 按 cost / latency / 质量自动选模型
- 自建 `v0/benchmarks` benchmark 数据库
- 写过一个 `unify-python-client`（已 deprecated，旧文档在 PyPI 还搜得到）

但到 2026 年，unify.ai 的 home page 已经完全转向 **"AI hires, not AI tools"** 的 Agent teammate 定位：
- "Hire them the way you'd hire a person"
- "Hop on a call, share your screen, walk them through the work"
- "Persistent identity across chat, voice, phone, video, screen-share, sms, email"

这是一个**很值得关注的产品演进路径** — 一个本来是「开发者工具」（LLM 路由 SDK）的公司，把自己重塑成了「AI 同事」产品。LLM 路由变成了 agent 的 internal subsystem。

### 1.2 核心叙事

| 旧叙事（2024） | 新叙事（2026） |
|---|---|
| "Use the best LLM for each task" | "Hire an AI teammate that handles the work" |
| **模型为中心** | **结果为中心** |
| 开发者集成 SDK | 业务人员 onboarding via Zoom |
| 智能路由（router） | 智能执行（agent runtime） |
| Credits 消耗控制 | Pass-through 定价，无平台费 |

### 1.3 公司信息

- **法人主体**：Unify AI Ltd., 71-75 Shelton Street, Covent Garden, London, WC2H 9JQ
- **定价货币**：USD，但基础体系是 credits（1 credit ≈ $0.001 模型花费）
- **合规**：GDPR aligned · SOC 2 aligned（自述，详情未公开）
- **开源协议**：所有 GitHub 仓库 MIT / Apache 2.0

---

## 2. 产品架构：四层解耦

Unify 现在的产品形态由四个 MIT 开源仓库组成，加上托管 SaaS 控制台：

```
┌──────────────────────────────────────────────────────────────┐
│  Hosted SaaS (console.unify.ai)                              │
│  • Workspace / 多 named teammates / Voice / Telephony        │
│  • Per-organization billing · Console UI                     │
│  • Proprietary, on top of orchestra-platform (private)      │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│  orchestra-platform (PRIVATE repo, FastAPI)                  │
│  • /v0/ 多租户 REST · /metrics Prometheus · /webhooks       │
│  • Stripe/Twilio/ElevenLabs/Cartesia/Deepgram 集成          │
│  • Depends on orchestra-core (public kernel)                │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│  orchestra-core (PUBLIC repo, kernel)                        │
│  • Postgres + pgvector 表: project, context, log_event,     │
│    field_type, embedding, embedding_queue                    │
│  • Single-tenant kernel APIs (kernel-level CRUD + embedding)│
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│  unify (SDK) + unillm (LLM client) + unity (runtime)        │
│  • unify: Python SDK 包装 Orchestra REST                      │
│  • unillm: LLM 路由/归一化/缓存/可观测（基于 LiteLLM）       │
│  • unity: agent runtime（dual-brain + CodeAct + handles）    │
└──────────────────────────────────────────────────────────────┘
```

四层职责分明（从仓库 README 拼出）：

| 层 | 仓库 | 角色 | 是否开源 |
|---|---|---|---|
| Runtime / orchestration | `unifyai/unity` | 本地 agent brain | ✅ MIT |
| Model access | `unifyai/unillm` | LLM 路由 + 归一化 | ✅ MIT |
| Persistence / state | `unifyai/unify` | 包装后端 REST | ✅ MIT |
| Backend API | `unifyai/orchestra-platform` | 多租户 SaaS 后端 | ❌ Private |
| Backend kernel | `unifyai/orchestra-core` | 单租户 DB kernel | ✅ MIT |
| Docs | `unifyai/docs` | Mintlify 站点源码 | ✅ MIT |
| Console UI | `unifyai/console` | Web UI | ❌ (not listed) |
| TypeScript SDK | `unifyai/unillm` 内 @unify/sdk | TS 客户端 | ✅ |

注意：unify.org GitHub 主页上 12 个仓库全在 `unifyai/` 组织下，最近活跃的（按 star 数）：`ivy` (14k) 是 ML framework transpiler、`unity` (44 star, 新)、`unillm` (2 star, 新)。新仓库 star 都不多 — 说明这个转向是 **重起炉灶**，不是延续社区。

---

## 3. LLM 路由核心：`unifyai/unillm`

虽然 LLM 路由不再是公司主叙事，但它依然是 Agent runtime 依赖的核心基础设施。要理解 Unify，必须先理解 unillm。

### 3.1 设计目标

> "Lightweight LLM access layer with provider normalization, caching, and observability. It uses a unified `endpoint` format (`model@provider`) so application code can switch providers without rewriting call sites, while still allowing developers to choose the model provider or compatible endpoint they want to use."

### 3.2 端点格式：`model@provider`

```python
import unillm

client = unillm.Unify("gpt-4o@openai")
client = unillm.Unify("claude-sonnet-4-20250514@anthropic")
client = unillm.Unify("gemini-2.0-flash@vertexai")
client = unillm.Unify("llama-3.1-70b@together")
```

这是 unillm 最显眼的设计选择 — 模仿 Docker image 的语义：把"用什么模型"和"从哪个 provider 拿"绑在同一个字符串里。切换 provider 不需要改业务代码，只改 endpoint 字符串。

### 3.3 支持的 providers

从 unillm README：

- OpenAI
- Anthropic
- Vertex AI (Google) — gcloud ADC or service account
- Bedrock (AWS)
- DeepSeek
- Groq
- Mistral
- Replicate
- Together AI
- xAI

**注意：unillm 没有自己的"智能路由"**。它不是"按 query 选最佳模型"的 router。它只是：
- 协议归一化（OpenAI/Anthropic/Vertex 各家消息格式差异）
- provider-specific preprocessing/postprocessing
- 缓存
- 成本核算
- OpenTelemetry 追踪
- 限流 hook

`unillm` **底层调用 `litellm` 完成真正的 provider 调用**（代码里直接 `import litellm`）：

```python
# unillm/clients/uni_llm.py
import litellm
import unify
# ...
```

所以 unillm 是 **LiteLLM 之上的 thin wrapper**：
- LiteLLM 负责把 `model@provider` 拆解 + 真正的 HTTP 调用
- unillm 负责成本核算（`_safe_deduct_credits`）+ 计费 + caching + OTel + limit hooks

### 3.4 成本核算（Cost Accounting）

```python
# unillm/costs.py
_DEFAULT_COST_MARGIN = 1.2

def get_cost_margin() -> float:
    return float(os.environ.get("UNILLM_COST_MARGIN", "1.2"))
```

> 重要发现：unillm 默认在 provider 实际成本之上**加 20% margin** 用于计费。环境变量 `UNILLM_COST_MARGIN` 可调。  
> 这与 unify.ai 主页"0% 平台费"的宣传**矛盾**。  
> **解读**：unillm 是底层 client SDK，默认 1.2x margin 是给"自己用 unillm 做计费中介"的人用的；托管 SaaS 走 Orchestra 端做计费，传给用户的 credits 1:1 映射。这两件事不冲突。

### 3.5 缓存层

```python
client = unillm.Unify("gpt-4o@openai", cache=True)

# 缓存模式
client.generate(..., cache="read")       # 仅读
client.generate(..., cache="write")      # 仅写
client.generate(..., cache="both")       # 读写
client.generate(..., cache="read-only")  # 必须在 cache，否则 error
```

缓存事件捕获：

```python
from unillm import capture_cache_events

with capture_cache_events() as events:
    client.generate(messages=[...])

print(events[0]["cache_status"])  # "hit" or "miss"
```

支持的 backend：
- `LocalCache` — file-based NDJSON（默认）
- `LocalSeparateCache` — 读/写分离的本地缓存（CI 场景）

### 3.6 OpenTelemetry 追踪

```bash
export UNILLM_OTEL=true
export UNILLM_OTEL_ENDPOINT=http://localhost:4317
export UNILLM_OTEL_LOG_DIR=/path/to/traces
```

LLM 调用会发出 OTel spans，可与 parent 应用 span 关联，propagated 到 child services。  
**这是 Unify 与其他 LLM Gateway（如 Helicone、Portkey）竞争最关键的差异化点** — 它不是孤立 LLM 监控，而是**和 OpenTelemetry 标准对齐**，可以纳入企业既有 observability 栈（Datadog/Honeycomb/Tempo）。

### 3.7 状态对话、Tool Calling、Structured Output

```python
# Stateful
client = unillm.Unify("gpt-4o@openai", stateful=True)
client.generate(user_message="What is 2+2?")
client.generate(user_message="And what is that times 3?")  # 自动维持历史

# Streaming
client = unillm.Unify("gpt-4o@openai", stream=True)
for chunk in client.generate(messages=[...]):
    print(chunk, end="")

# Tool calling (OpenAI-compatible)
tools = [{"type": "function", "function": {...}}]
response = client.generate(messages=[...], tools=tools)

# Structured output (Pydantic)
from pydantic import BaseModel
class Answer(BaseModel):
    value: int
    explanation: str
response = client.generate(messages=[...], response_format=Answer)
```

这些都不稀奇，但统一在 `unillm.Unify(...)` 一个 client 下，跨 provider 一致。

### 3.8 限流 hook

```python
from unillm import check_limits, SpendingLimitExceededError

try:
    check_limits(model=..., prompt_tokens=..., estimated_cost=...)
except SpendingLimitExceededError:
    # 用户超支
    ...
```

unillm 通过 `limit_hooks.py` 在每次 LLM 调用前/后回调，让应用方可以做 budget guard。  
**注意**：unillm 自身**没有内置 provider failover**。如果 OpenAI 报错，没有自动切换到 Anthropic。这是与 Portkey/LiteLLM 的差距。

### 3.9 `unify` SDK（持久化层）

```python
import unify

# Project 管理
unify.activate("my-project")
unify.create_project("my-project")
unify.list_projects()

# Structured logging
unify.log(question="What is 2+2?", response="4", score=1.0)
logs = unify.get_logs()

# Async admin（计费查询）
# Credits 扣减
unify.deduct_credits(amount, category="llm", ...)
```

`unify` SDK 是对 Orchestra 后端 REST 的 Python 封装。它和 unillm 通过 `billing_context.py` 关联 — unillm 算完 cost 后调用 `unify.deduct_credits` 把花费写到 Orchestra 账本里。

---

## 4. Agent 运行时：`unifyai/unity`

如果说 unillm 是 LLM 路由层，unity 就是 Unify 真正想卖的"产品"。它解决了 agent 框架的一个核心问题：**mid-flight 操控**。

### 4.1 设计目标

> "Open-source virtual teammates that take voice and video calls — and let you interrupt, redirect, or pause them mid-task without restarting."

它想做的，是把"对话"从"submit prompt → wait → get result"的同步模型变成"持续存在、可中途介入"的异步会话。

### 4.2 三层架构（这是 Unify 的核心 IP）

```
┌──────────────────────────────────────────────────────────────┐
│  USER SURFACES (white)                                       │
│  • Chat REPL · Voice (LiveKit) · Phone (Twilio)              │
│  • Video (Meet/Zoom/Teams) · Email · SMS · Webhooks          │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│  DUAL-BRAIN CONVERSATION TIER                                │
│  • Fast Brain (LiveKit subprocess, sub-second turn-taking)   │
│  • Slow Brain = ConversationManager (always present, pink)   │
│    ↕ IPC: SPEAK / NOTIFY / BLOCK / events / context        │
│  • Steerable handle registry                                │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│  CodeActActor (green tool-calling loop)                      │
│  • Writes one Python program per turn                        │
│  • Calls typed primitives.* APIs                             │
│  • Returns SteerableToolHandle for in-flight steering       │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│  STATE MANAGERS (each runs own LLM tool loop)                │
│  • ContactManager · KnowledgeManager · TaskScheduler         │
│  • TranscriptManager · GuidanceManager · FileManager         │
│  • WebSearcher · SecretManager · FunctionManager            │
│  • ImageManager · BlacklistManager · DataManager            │
└──────────────────────────────────────────────────────────────┘
                              ▲
┌──────────────────────────────────────────────────────────────┐
│  ORCHESTRA (Postgres + pgvector)                             │
│  • EventBus (typed pub/sub, Pydantic)                        │
│  • MemoryManager (offline consolidation every 50 messages)   │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 关键模式 1：Steerable Handles

每个 manager 方法都返回统一的 `SteerableToolHandle`：

```python
handle = await actor.act("Research flights to Tokyo and draft an itinerary")

# 20 秒后，工作还在进行：
await handle.interject("Also check train options from Tokyo to Osaka")

# 不打断地查询进度
status_handle = await handle.ask("What have you found so far?")

# 暂停，处理紧急事
await handle.pause()
# ... 处理完 ...
await handle.resume()

# 完全停止
await handle.stop("No longer needed")
```

`SteerableToolHandle` 的方法（来自 `architecture/steerable-handles.md`）：

| 方法 | 用途 |
|---|---|
| `ask(question)` | 只读查询进度/结果，返回新 handle |
| `interject(message)` | 注入新上下文/纠正/要求 |
| `pause()` | 暂停，未完成的子操作完成，但不开始新动作 |
| `resume()` | 恢复，pause 期间完成的结果先处理 |
| `stop(reason)` | 取消任务和所有子操作 |
| `done()` | 检查是否完成 |
| `result()` | await 最终输出 |

**关键创新**：

> "When the Actor calls `primitives.contacts.ask(...)`, the ContactManager starts its own tool loop and returns its own handle — nested inside the Actor's handle, which is nested inside the ConversationManager's."

handle 是**任意深度可嵌套**的：

```
ConversationManager.handle
    └── Actor.act.handle
        ├── ContactManager.ask.handle
        ├── KnowledgeManager.update.handle
        └── TaskScheduler.execute.handle
```

用户对 ConversationManager 介入时，CM 决定是否转发给 Actor，Actor 再决定是否转发给 active manager — **每层都有自己的策略**。

**对其他 agent 框架的对比**（Unity README 自述）：

| 框架 | steering 行为 |
|---|---|
| HermesAgent | 文本注入到下一个 tool result；interrupt 是 thread-scoped flag |
| OpenClaw | 在 turn 边界处理；`interrupt` 终止，`steer`/`followup` 入队 |
| **Unity** | **嵌套的 typed signal**，每层 handle 都暴露统一 `ask/interject/pause/resume/stop` |

### 4.4 关键模式 2：CodeAct（程序即计划）

传统 agent 框架每次吐一个 JSON tool call：

```json
// 5 步任务要 5 个 round-trip，每个都把之前所有内容 append 一次
{"name": "contacts_lookup", "args": {"query": "Henderson"}}
// model 看结果
{"name": "knowledge_query", "args": {"contact": "...", "topic": "..."}}
// ... 共 5 次
```

Unity Actor 写一段 Python：

```python
contacts = await primitives.contacts.ask(
    "Who was involved in the Henderson project?"
)
for contact in contacts:
    history = await primitives.knowledge.ask(
        f"What was {contact} last working on?"
    )
    await primitives.contacts.update(
        f"Send {contact} a catch-up email referencing {history}"
    )
```

这段代码在 sandboxed execution session 跑，**有真正的变量、循环、控制流**。术语来自 ICML 2024 论文 ["Executable Code Actions Elicit Better LLM Agents"](https://arxiv.org/abs/2402.01030)。

**vs HermesAgent PTC（Programmatic Tool Calling）**：
- HermesAgent 的 `execute_code` 跑 Python 调通用 tools（file/shell），只是把 stdout 写进 context，**目的是优化 context 增长**
- Unity 的 CodeAct 调用 **typed domain primitives**（`primitives.contacts.ask`），每个 primitive 内部都有自己的 LLM tool loop，**目的是把 domain 智能组合起来**

**vs Claude/OpenAI 的 tool_use**：CodeAct 是把 "N 次 JSON tool call" 压成 "1 段 Python 程序"，**减少 LLM 决策轮次**，避免 combinatorial explosion。

### 4.5 关键模式 3：Dual-Brain Voice

语音对话最大的问题是"agent 思考时用户干等"。

Unity 把 voice 拆成两个 brain：

**Fast Brain**：
- LiveKit subprocess（real-time voice agent）
- sub-second turn-taking
- 直接处理对话

**Slow Brain**（ConversationManager）：
- 看到全貌：所有 channel、所有 in-flight actions、memory
- 深思熟虑
- 主进程跑

两者通过 IPC 通信，慢脑发给快脑三种消息：

| 模式 | 行为 |
|---|---|
| **SPEAK** | "一字不差地说这个" — 绕过 fast brain 的 LLM，直接合成语音 |
| **NOTIFY** | "这是上下文，你决定怎么用" — fast brain 决定怎么融入对话 |
| **BLOCK** | 什么都不发 — fast brain 自己继续 |

**例子**：

```
User: Can you research flights to Tokyo for next week?
Fast: "Sure, let me look into that for you."
Slow: starts actor.act("Research flights to Tokyo...") → returns handle
[Actor 跑 30 秒，查 web、比价]
Slow → Fast: NOTIFY { "Found 3 direct flights, cheapest is ¥85,000 on ANA" }
Fast: "I've found a few options — the best deal looks like an ANA direct flight for about 85,000 yen."
```

User 永远不需要干等。**这是 OpenAI Realtime API 那种"turn-taking 模式"和"agent task 模式"的桥接**。

**Speech Urgency Evaluator** 还会判断 — 如果用户刚问"你找到啥了？"而结果刚刚到，要 **preempt 当前 fast brain turn**，立即回应。

### 4.6 关键模式 4：State Managers

**English as API** 是 Unity 最具争议的设计选择：

```python
# ContactManager.ask — 参数是英语，不是 SQL
await primitives.contacts.ask("Who did we meet at the conference last month?")

# KnowledgeManager.update — 指令是英语，不是 CRUD
await primitives.knowledge.update(
    "Record that the Henderson project deadline moved to March 15"
)
```

每个 manager 都有自己的内部 LLM tool loop 来解释 English 请求，调用低层 tools（DB queries、API calls）。  
**为什么这么设计**：
- **Manager 是可替换的**：ContactManager 可以用 SQL / Vector store / 外接 CRM，调用方代码不变
- **可读性**：看 Actor 的 plan 就知道它在做什么，不用读实现
- **组合自然**：`for contact in contacts: await primitives.knowledge.ask(f"What was {contact} working on?")` — 英文自然流过

但代价：
- **每次 LLM 解释都加延迟**（一次 manager call 可能要 1-3 秒 + 1-2 次 LLM 跳转）
- **不可控的 cost**（每次 ask 都要 1 次 LLM）
- **调试复杂**（LLM 解释可能误解）

### 4.7 关键模式 5：MemoryManager

每 50 条消息，MemoryManager 后台跑 consolidation：

1. **Contact extraction** — 识别提到的人，更新联系人记录
2. **Knowledge extraction** — 提取事实/项目细节/偏好
3. **Task extraction** — 识别承诺/截止日期/follow-ups
4. **Summary updates** — 更新 per-contact rolling summaries

结果写入 typed、queryable 表，不是 freeform text。

**vs MEMORY.md 类方案**（来自 `architecture/memory.md`）：

| 能力 | Freeform memory | Unity 结构性 consolidation |
|---|---|---|
| "Who's Alice?" | 文本搜 "Alice" | `Contacts` 表：name/role/org/relationship |
| "What did Alice say about budget?" | fuzzy search | Join `Contacts` → `Transcripts` |
| "How does Alice prefer to communicate?" | 寄希望于某处提到过 | `response_policy` 字段 |
| "What's overdue?" | 不可靠的日期解析 | `Tasks` 表 `deadline < now` |
| 10,000 条消息后 | 慢、噪声大 | 一致速度 |

### 4.8 关键模式 6：Functions + Guidance 双库

**FunctionManager** — 可执行 Python（带 metadata + venv），Actor 可以组合进 plan

**GuidanceManager** — 程序化的 how-to 散文：SOPs、软件 walkthroughs、多步策略

成功的 trajectory 会被 `store_skills` 主动 review，提取：
- 值得保留的代码
- 使用它的程序化叙事

下次 session 会先查这两个库再伸手去 raw tools。

### 4.9 Schedules and Triggers

不用 cron 表达式或 webhook YAML。用**自然语言**描述给 agent，存为 `Task`：

```
"Every Monday at 9, summarize my unread emails"
"Ping me whenever Alice emails about invoices"
```

这些 Task 存为 `schedule`+`repeat`（cadences）或 `trigger`（event matches）。时间到 / trigger 触发时，contained `Actor` run 醒过来，读 task description，规划怎么做。

**关键创新** — **自动毕业**：

> "After enough successful description-driven runs, the storage-review loop can persist the trajectory as a stored function — at which point the recurring task runs in a hidden, headless lane against that function rather than re-planning from scratch each time."

"每周一总结邮件"开始是段文字让 agent 理解，几个月后变成 headless lane 直接调用 entrypoint。**这是"自演化 agent"的形态**。

### 4.10 安装和运行

```bash
# 一行安装
curl -fsSL https://raw.githubusercontent.com/unifyai/unity/main/scripts/install.sh | bash

# 提示输入 OpenAI 或 Anthropic key，写到 ~/.unity/unity/.env
# 自动启动 Docker 里的 local Orchestra
# PATH 写入 ~/.zshrc / ~/.bashrc

# 两个终端
unity               # Terminal 1: chat
unity logs          # Terminal 2: live logs
```

**Voice 二步**：

```bash
unity voice setup   # 装 LiveKit server（本地，无 LiveKit Cloud 账户需要）

# 需要 keys:
# DEEPGRAM_API_KEY  (STT)
# CARTESIA_API_KEY  或  ELEVEN_API_KEY  (TTS)
```

```
unity --live-voice  # 启动
# 在 chat 里: call    -> 打开浏览器 LiveKit Playground
#               end_call  -> 拆掉房间
```

**pre-requirements**：Python 3.12+ · Docker · OpenAI/Anthropic key · macOS/Linux/WSL2 · PortAudio

### 4.11 与 OpenClaw / Hermes 的官方对比

Unity README 给了一张**共享视觉语言**的三方对比图（同 panel、同 box/arrow grammar、同色标）：

| 颜色 | 含义 |
|---|---|
| 绿色 | agent 的 tool-calling loop（每个 assistant 都有一个） |
| 桃色 | 自主 wake 源（cron+webhooks vs. 自然语言 Tasks） |
| 粉色 | **持久推理 loop**（位于 agent 之上；这是三家中唯一变化的部分） |
| 白色 | 被动结构层（channels/surfaces, tools, state, dispatcher daemon） |

**Unity 的差异化**：
- 粉色持久推理 loop（ConversationManager 在 agent 之上）
- 双脑 conversation tier
- 独立的 Actor tier 在 slow brain 之下
- typed back office（ContactManager 等）替代 opaque file storage
- 自然语言 autonomous wake 源

**OpenClaw 的差异化**：
- 专门的 Gateway daemon dispatcher tier
- 显式"无 agent-hierarchy 框架（manager-of-managers）"作为 non-goal
- cron+webhook 是 in-process timer + HTTP server（在 Gateway daemon 内）

**Hermes 的差异化**：
- ~12k LOC 单一 sync agent loop
- SQLite+FTS5 transcripts
- 文本注入 steering 模式

---

## 5. 后端层：Orchestra

### 5.1 双层结构

```
orchestra-platform (private, 多租户)
    ↑ 依赖
orchestra-core (public, 单租户 kernel)
```

平台/内核分离是单边依赖 — `orchestra-platform` 可以 import `orchestra-core`，反过来不行。CI 用 `scripts/check_core_purity.sh` 强制。

### 5.2 哪些放平台、哪些放内核

| 修改位置 | 仓库 |
|---|---|
| `project`, `context`, `log_event`, `field_type`, `embedding`, `embedding_queue` | orchestra-core |
| Kernel-only DAO / service / endpoint，无 account/tenant 上下文 | orchestra-core |
| `user`, `organization`, `billing_*`, `assistants`, `api_key`, `voices`, `space`, `team` | orchestra-platform |
| 任何读 `user_id` / `organization_id` / `assistant_id` 做访问控制 | orchestra-platform |
| Stripe, Twilio, ElevenLabs, Cartesia, Deepgram, Vertex AI 集成 | orchestra-platform |
| Console UI state：`interface`, `tile`, `tab`, `dashboard_token` | orchestra-platform |
| Alembic migration | 取决于触及哪些表 |

判断口诀：**"Could this run in a fully local, single-user, no-billing context?"** → Yes 进 core。

### 5.3 本地开发

```bash
# 启动 Postgres + pgvector
docker run --name orchestra-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=orchestra -e POSTGRES_USER=orchestra -e POSTGRES_DB=orchestra \
  pgvector/pgvector:pg15

# 安装
poetry install --with dev
alembic upgrade head
poetry run python -m orchestra
# API 跑在 http://127.0.0.1:8000/v0
```

### 5.4 安全设计

- `Authorization: Bearer` token（除 `/v0/health` 和 Stripe webhook）
- Admin 端点要求 `ORCHESTRA_ADMIN_KEY`，用 `secrets.compare_digest()` 防 timing attack
- Prometheus `/metrics` 用 `PROMETHEUS_METRICS_TOKEN` 认证
- IP-based rate limit（admin/metrics/webhook 60 req/IP/60s）
- 邮件地址从 metric labels 中排除（防 PII 泄漏）
- Security headers 全套：`X-Content-Type-Options` / `X-Frame-Options` / `Strict-Transport-Security` / `Referrer-Policy` / `X-XSS-Protection` / `Permissions-Policy`

### 5.5 数据持久性

- 所有 state 在 Orchestra Postgres（Docker named volume `orchestra-local-db-data`）
- Docker 启动参数 `--restart unless-stopped`
- 重启后 Postgres 自动 attach volume，Unity 再次启动会 auto-start Orchestra FastAPI
- **状态跨重启不丢**（除了 Docker daemon 自动启动外的部分）

---

## 6. 协议与互操作性

### 6.1 协议清单

| 协议 | 支持情况 | 备注 |
|---|---|---|
| OpenAI Chat Completions | ✅ | unillm 主路径 |
| OpenAI Responses（`openai/responses/`） | ✅ | unillm 对 GPT-5.x+ tool 路由 |
| Anthropic Messages | ✅ | unillm 直接支持 |
| Google Vertex AI（Gemini + Claude） | ✅ | gcloud ADC |
| AWS Bedrock | ✅ | AWS 凭证 |
| WebSocket（LiveKit voice） | ✅ | Unity fast brain |
| Webhook | ✅ | Orchestra `/v0/webhooks/stripe` + 自定义 |
| REST | ✅ | Orchestra `/v0/...` |
| Streaming (SSE) | ✅ | unillm `stream=True` |
| MCP (Model Context Protocol) | ❌ | 暂未集成 |
| A2A (Agent-to-Agent) | ❌ | 暂未集成 |

### 6.2 OpenAI Responses Bridge

`unillm` 有个特别代码块处理 **OpenAI GPT-5.x+ Responses 模式**：

```python
_OPENAI_RESPONSES_BRIDGE_MODEL_PREFIX = "openai/responses/"
_OPENAI_GPT_MINOR_VERSION_RE = re.compile(r"^gpt-5\.(?P<minor>\d+)(?:[-.].*)?$")

def _is_openai_gpt_responses_tool_model(model: str) -> bool:
    match = _OPENAI_GPT_MINOR_VERSION_RE.match(model)
    return bool(match and int(match("minor")) >= 4)
```

**解读**：GPT-5.4+ 在有 tools + `reasoning_effort` 时需要走 Responses API（不是 Chat Completions）。unillm 自动检测并把 `parallel_tool_calls` 和 `tool_choice` 移交给 bridge。  
**意义**：unillm 在和 OpenAI 最新模型同步（这是 LiteLLM 还不一定第一时间支持的能力）。

### 6.3 客户端兼容性

- `pip install unifyai` → 持久化 SDK
- `pip install unifyai-unillm` → LLM 客户端
- `pip install unifyai-unity` → Agent runtime（最新）
- TypeScript：`@unify/sdk`（文档里列了但代码仓未直接看到）

---

## 7. 性能与可扩展性

### 7.1 性能特性

| 指标 | 描述 |
|---|---|
| **LLM 调用延迟** | unillm 是 thin wrapper，开销 <5ms；真实延迟取决于 provider |
| **流式首字节** | 取决于 provider；unillm 透传 |
| **并发** | Python aiohttp session 复用（`shared_session.py`） |
| **缓存命中** | 文件 NDJSON cache，命中时跳过 LLM |
| **Memory consolidation** | 后台跑，不阻塞对话 |
| **Voice turn-taking** | sub-second（LiveKit fast brain） |
| **Slow brain latency** | 数秒级（actor.act + CodeAct 写程序） |

### 7.2 缓存命中率（来自 unillm 文档）

> "With a populated `.cache.ndjson`, cached LLM responses are replayed — so tests run fast and deterministically without making real LLM calls."

unillm 自带**测试 cache 复用机制**。这意味着在 CI 中，一旦首次跑过，后续测试 0 LLM cost。但生产环境的 cache hit rate **未公开数据**。

### 7.3 Cost Margin

unillm 默认 1.2x provider cost（环境变量可调）。但 SaaS 控制台是 pass-through。

### 7.4 双脑延迟分离

```
User: "Can you research flights to Tokyo for next week?"
  ↓ 50ms (LiveKit audio)
Fast: "Sure, let me look into that for you."
  ↓ 100ms
Slow: actor.act("Research flights...")  → handle returned
[30s 内 Fast 继续正常对话，不死等]
Slow → Fast: NOTIFY { "Found 3 direct flights..." }
  ↓ 200ms
Fast: "I've found a few options..."
```

**LiveKit 单独进程**，所以 fast brain 不会被 slow brain 的 CodeAct 阻塞。这是 OpenAI Realtime 风格 turn-taking + Anthropic 风格 agent task 的桥接。

---

## 8. 部署方式

### 8.1 三种部署

| 模式 | 描述 | 适合 |
|---|---|---|
| **托管 SaaS** | console.unify.ai · Stripe 计费 · UK/EU data residency on request | 个人 / 团队 / 企业 |
| **本地单机** | `curl … \| bash` 一行安装；Docker 跑 local Orchestra | 开发者 / 个人 |
| **自定义 Orchestra** | `--skip-setup` 装代码，point at `ORCHESTRA_URL` + `UNIFY_KEY` | 私有部署 |

### 8.2 本地安装组件

```
~/.unity/
├── unity/          # Agent runtime
├── unify/          # SDK
├── unillm/         # LLM client
└── orchestra-core/ # 单租户 backend

~/.unity/unity/.env  # UNIFY_KEY, ORCHESTRA_URL, OPENAI_API_KEY, LIVEKIT_*

~/.local/bin/unity   # CLI shim
~/.livekit-playground/  # 浏览器 voice UI（首次 call 时克隆）
```

### 8.3 Enterprise

- SSO
- 审计日志导出
- DPA
- BAA
- UK / EU 数据驻留
- 专属 tenancy
- SLA
- 命名支持
- 定制计费条款 + 安全审查

---

## 9. 成本模型

### 9.1 公开定价（unify.ai/pricing）

| Plan | 价格 | 适合 |
|---|---|---|
| Team | $75/月 workspace credits | 团队（most teams） |
| Enterprise | Custom · Volume pricing on request | 受监管行业 |

**关键承诺**：

> "0% platform fee · Pass-through pricing · Credits map to actual model spend at Anthropic, OpenAI, and Google."

> "10× cheaper by month three · Caching pulls the bill down."

> "$0 per-seat charge · No per-seat charges."

### 9.2 Credits 用量分布（自述）

| 任务类型 | Credits |
|---|---|
| Quick task（Slack 摘要 + CRM follow-up） | 100-300 |
| Real workflow（landing page fix shipped） | 500-1,500 |
| Full project（竞品分析 + board PDF） | 2,000-5,000 |

20,000 credits ≈ 40-200 tasks，取决于复杂度。

### 9.3 0% 平台费 vs 1.2x Margin

`unillm` 仓库源码默认 `UNILLM_COST_MARGIN=1.2`。  
`unify.ai` 主页承诺 "0% platform fee"。  

**这是两件不同的事**：
- `unillm` 是 OSS client SDK，默认 1.2x margin 给**自己用 unillm 当中介**的人用的（计费工具自己拿 20%）
- SaaS 控制台是 Orchesta 后端跑，credits 1:1 映射 provider cost 给最终用户

**对终端用户**：如果用 SaaS，确实 0% 加价。  
**对 SDK 集成者**：如果自己跑 unillm 计费，默认收 1.2x cost。

---

## 10. 生态系统与集成

### 10.1 Standard Integrations

unify.ai 自述："**~3,000 apps** at last count" — 包括：
- HubSpot, Salesforce, Stripe, Linear, Jira, GitHub, Notion, Figma
- Google Workspace, Microsoft 365
- Slack, Teams, Mixpanel, PostHog, Snowflake
- 长尾 ...

### 10.2 通信渠道

- Chat REPL
- Voice (LiveKit)
- Phone (Twilio) — SIP
- Video (Zoom, Meet, Teams)
- Screen-share (LiveKit 浏览器)
- SMS
- Email
- Webhook (Stripe, GitHub, Jira, custom)

### 10.3 LLM Providers

10 家（见 §3.3） — OpenAI, Anthropic, Vertex AI, Bedrock, DeepSeek, Groq, Mistral, Replicate, Together AI, xAI

### 10.4 语音栈

- **STT**：Deepgram（要求自带 API key，free tier）
- **TTS**：Cartesia 或 ElevenLabs（选一，free credits）
- **Voice infra**：LiveKit（本地跑 livekit-server 二进制，无需 LiveKit Cloud 账户）

### 10.5 财务/支付

Stripe（hosted billing），Twilio（电话），Cartesia/Deepgram/ElevenLabs 各自原生计费。

---

## 11. 客户案例

### 11.1 主页挂出的 use cases

| 角色 | 任务 |
|---|---|
| Founders & CEOs | 投资人更新、pipeline 复盘、board pack |
| Marketing & Growth | 跨渠道 ad 审计、SEO content、ICP lead lists |
| Engineering | bug triage、real PRs、admin tools（无需占用 sprint） |
| Operations & Finance | 供应商追讨、发票匹配、recurring reports |

### 11.2 主页示例对话

```
David: 9:14
@unity can you pull this week's MRR from Stripe + new opps from HubSpot, 
draft a Notion summary?
unity: 9:14
stripe  MRR $84,210 +4.2%
hubspot 18 new opps · 3 stalled
notion  weekly-review · draft ready
```

```
Mike: 11:32
@unity the pricing page still shows "$99/mo" on the starter tier. 
Should be "$79/mo" — can you update it?
unity: 11:38
✅ Done. PR opened with the change, preview ready for review.
pricing.tsx · pull request #214
```

```
Lisa: 9:14
@unity competitive analysis — us vs Notion AI, Glean, Moveworks. 
Pricing, features, positioning. PDF I can share with the board.
unity: 9:42
✅ Done. Twelve-page brief — feature matrix, pricing comparison, 
positioning map. Exec summary 📎
competitive-analysis-q1.pdf
```

### 11.3 命名客户

unify.ai 主页**没有挂出 logo wall 或 customer testimonials**。只有"Reusable workflows · Real work by end of day" 的模糊措辞。  
**这说明 Unify 处于**：
- 产品已 GA（`console.unify.ai` 注册即可用）
- 但品牌 / 客户关系还没建立起来
- 还在 PMF 验证阶段

---

## 12. 优势与劣势

### 12.1 优势

| 维度 | 评价 |
|---|---|
| **架构创新** | ⭐⭐⭐⭐⭐ Steerable handle 嵌套 steering 在同类 agent 框架里**找不到对手**（HermesAgent 是文本注入，OpenClaw 是 turn 边界处理） |
| **CodeAct** | ⭐⭐⭐⭐ ICML 论文基础上有真创新 — 不是 batch 工具调用，而是 typed domain primitives 组合 |
| **Dual-brain voice** | ⭐⭐⭐⭐⭐ Sub-second turn-taking + 长 thinking 期间不死等。这个桥接在 OpenAI Realtime / LiveKit / 任何商用 voice agent 里都少见 |
| **结构化 memory** | ⭐⭐⭐⭐ Contacts/Knowledge/Tasks typed tables 远比 MEMORY.md 类方案可查询 |
| **Open source** | ⭐⭐⭐⭐⭐ 11+ 仓库 MIT/Apache 2.0，unillm/unity/orchestra-core 全部公开 |
| **English-as-API managers** | ⭐⭐⭐⭐ 可读性 + 可替换性是真优势（caller 不耦合 SQL/CRUD） |
| **OpenTelemetry** | ⭐⭐⭐⭐ unillm 走标准 OTel，可纳入企业既有 observability 栈 |
| **定价透明度** | ⭐⭐⭐⭐⭐ 0% 平台费、pass-through、无 per-seat（罕见） |
| **Caching** | ⭐⭐⭐ 4 种 cache 模式 + event capture；unillm CI test cache 复用是亮点 |
| **自然语言 schedule** | ⭐⭐⭐⭐ "每周一总结邮件"自动毕业成 stored function 是真创新 |

### 12.2 劣势

| 维度 | 评价 |
|---|---|
| **不是 LLM Gateway** | ❌ unillm **没有内置智能路由**（没有按 query 自动选 best model）。它只是带计费/缓存的 LLM 客户端封装。**和 Portkey/LiteLLM 的 router 模式不同** |
| **没有 provider failover** | ❌ OpenAI 报错，unillm **不会自动切到 Anthropic**（这是 Portkey/LiteLLM 的核心功能） |
| **English-as-API 性能** | ⚠️ 每次 manager call 1-3 秒 + 1-2 次 LLM 跳转。复杂任务延迟累积 |
| **English-as-API 成本** | ⚠️ 每次 ask 1 次 LLM；高任务数下成本线性增长 |
| **新平台，缺生态** | ❌ GitHub 仓库 star 数极少（unify 4、unillm 2、unity 44），社区不活跃 |
| **没客户 logo** | ❌ unify.ai 主页没挂出 customer testimonials，PMF 未验证 |
| **没 benchmark 数据** | ❌ 主页说"10× cheaper by month three"但没公开数据 |
| **unillm 自身 1.2x margin** | ⚠️ 与"0% 平台费"宣传矛盾（虽是 SDK 与 SaaS 两件事） |
| **没 MCP 集成** | ❌ MCP 是 2024 末-2025 主流，Unify 还没支持 |
| **没 A2A 集成** | ❌ 同样缺 |
| **Voice 依赖第三方** | ⚠️ Deepgram/Cartesia/ElevenLabs 各自要 key + 各自计费 |
| **重 LLM 依赖** | ⚠️ 每个 manager 内部都跑 LLM tool loop，op cost 不可忽视 |
| **本机 OS 限制** | Windows native 不可用（macOS/Linux/WSL2） |
| **文档 SPA** | ⚠️ docs.unify.ai 是 Mintlify SPA，搜索引擎很难抓 |

### 12.3 不适合的场景

- **需要 LLM 智能路由**（按 query 自动选 best model）→ 用 Portkey / LiteLLM / Not Diamond
- **需要 provider failover** → 用 Portkey / LiteLLM
- **需要 0 外部 LLM cost 透明度**（Unify 1.2x margin）→ 用 LiteLLM 自部署
- **Windows native** → 用 OpenClaw / Hermes
- **需要大型社区和文档** → OpenClaw（GitHub 28k+）
- **只想做简单 LLM 调用，不想搭 agent** → 用 LiteLLM 直连

### 12.4 适合的场景

- **需要"AI 同事"产品**（多 channel、persistence、voice）→ Unify 几乎独占
- **需要 mid-flight steering**（不能让 agent 跑完才能改）→ Unify 显著优势
- **需要结构化 long-term memory**（不是 MEMORY.md）→ Unify 优势
- **需要 English-as-API 的可组合性**（让不同 manager 互不耦合）→ Unify 优势
- **预算透明（0% 平台费）** → Unify 优势
- **需要 LLM 缓存 + OTel 标准化** → unillm 优势

---

## 13. 与其他 LLM Gateway / Agent 平台对比

### 13.1 LLM Gateway 维度

| 维度 | Unify (unillm) | Portkey | LiteLLM | Helicone | OpenRouter |
|---|---|---|---|---|---|
| **核心定位** | LLM 客户端（带计费/cache/OTel） | LLM Gateway + observability | 通用 LLM 客户端 | LLM observability | 多模型 SaaS 路由 |
| **智能路由** | ❌ | ✅（按 cost/latency/quality 选） | ❌（手动） | ❌ | ✅（按价格/能力自动） |
| **Provider failover** | ❌ | ✅ | ✅（retries+fallback） | ❌ | ❌ |
| **Cache** | ✅ 4 模式 | ✅ | ✅ | ✅ | ❌ |
| **OTel** | ✅ 原生 | ⚠️ 通过 export | ❌ | ⚠️ 自有格式 | ❌ |
| **开源** | ✅ MIT | ✅ Apache 2.0 | ✅ MIT | ✅ MIT | ❌ |
| **托管控制台** | ✅ console.unify.ai | ✅ Portkey Cloud | ⚠️ 仅企业 | ✅ Helicone Cloud | ✅ |
| **Hosted pricing 透明度** | ⭐⭐⭐⭐⭐ 0% fee | ⭐⭐⭐ 含 5% markup | — | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Provider 数量** | 10 | 250+ | 100+ | 20+ | 50+ |
| **Cost 1.2x margin (SDK)** | ✅（SDK 默认） | ❌ | ❌ | ❌ | — |
| **结构化 memory** | ⭐⭐⭐⭐⭐（Agent 层） | ❌ | ❌ | ❌ | ❌ |
| **Voice** | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ |
| **Steerable mid-flight** | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ |
| **代码复杂度** | 中（基于 LiteLLM） | 中 | 大 | 小 | 小 |

### 13.2 Agent 平台维度

| 维度 | Unify (unity) | OpenClaw | Hermes | LangGraph | AutoGen |
|---|---|---|---|---|---|
| **持久推理 loop** | ⭐⭐⭐⭐⭐（pink 慢脑） | ❌ | ❌ | ❌ | ❌ |
| **Steerable mid-flight** | ⭐⭐⭐⭐⭐ 嵌套 | ⚠️ turn 边界 | ⚠️ 文本注入 | ⚠️ interrupt | ⚠️ |
| **CodeAct 写程序** | ⭐⭐⭐⭐ typed primitives | ❌ | ⚠️ PTC | ❌ | ❌ |
| **结构化 memory** | ⭐⭐⭐⭐⭐ | ⚠️ MEMORY.md | ⚠️ SQLite FTS5 | ❌ | ❌ |
| **Voice** | ⭐⭐⭐⭐⭐ dual-brain | ⚠️ plugin | ❌ | ❌ | ❌ |
| **Channel 广度** | ⭐⭐⭐⭐（chat/voice/phone/video/screen-share/email/sms） | ⭐⭐⭐⭐⭐（14+ channels） | ⭐⭐⭐⭐（4 surfaces） | ❌ | ❌ |
| **Community** | ⭐ 44 stars | ⭐⭐⭐⭐⭐ 28k+ stars | ⭐⭐⭐ 4k+ stars | ⭐⭐⭐⭐ 14k+ stars | ⭐⭐⭐⭐ 35k+ stars |
| **Production-grade** | ⚠️ PMF 验证中 | ✅ 成熟 | ✅ 成熟 | ✅ 成熟 | ✅ 成熟 |
| **本地优先** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **门槛** | 一行安装 | 较复杂 | 中 | 中 | 中 |
| **License** | MIT | MIT | MIT | MIT | MIT/Commercial |

### 13.3 关键判断

1. **Unify 的真实竞争对手不是 LLM Gateway 玩家**（Portkey/LiteLLM），而是 **AI 同事 / 数字员工平台**（Sierra、Decagon、Salesforce Agentforce、Claude for Work）。  
   - 区别在于：Sierra/Decagon 做客服，Salesforce Agentforce 做 CRM 内，Unify 想做**通用 virtual teammate**。

2. **unillm 本身不具备和 Portkey 直接竞争的能力**。它没有智能路由、没有 failover、没有 provider 数量优势。它的优势是 OTel 标准化 + cache 友好 + 嵌套 unillm.Unify 客户端简单。

3. **unity 是 Unify 真正的护城河**。Steerable handles + Dual-brain + CodeAct typed primitives 这套设计在 agent 框架里几乎是独占的（HermesAgent 是文本注入，OpenClaw 显式拒绝 manager-of-managers）。

---

## 14. 代码示例汇总

### 14.1 unillm 基础调用

```python
import unillm

# 同步
client = unillm.Unify("gpt-4o@openai")
response = client.generate(
    messages=[{"role": "user", "content": "Hello!"}]
)

# 异步
async_client = unillm.AsyncUnify("claude-sonnet-4-20250514@anthropic")
response = await async_client.generate(
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### 14.2 unillm 流式 + 缓存

```python
client = unillm.Unify("gpt-4o@openai", stream=True, cache=True)

# 流式
for chunk in client.generate(messages=[...]):
    print(chunk, end="")

# 缓存事件
from unillm import capture_cache_events
with capture_cache_events() as events:
    client.generate(messages=[...])
print(events[0]["cache_status"])  # "hit" or "miss"
```

### 14.3 unillm 状态 + Tool

```python
client = unillm.Unify("gpt-4o@openai", stateful=True)
client.generate(user_message="What is 2+2?")
client.generate(user_message="And what is that times 3?")  # 维持历史

tools = [{"type": "function", "function": {"name": "get_weather", ...}}]
response = client.generate(messages=[...], tools=tools)
```

### 14.4 unillm Pydantic 结构化输出

```python
from pydantic import BaseModel

class Answer(BaseModel):
    value: int
    explanation: str

response = client.generate(
    messages=[{"role": "user", "content": "What is 2+2?"}],
    response_format=Answer
)
```

### 14.5 unify SDK 项目 + 日志

```python
import unify

# 项目
unify.activate("my-project")
unify.create_project("new-proj")
unify.list_projects()

# 日志
unify.log(question="What is 2+2?", response="4", score=1.0)
logs = unify.get_logs()

# Credits
unify.deduct_credits(
    amount=0.0123,
    category="llm",
    assistant_id="unity-main",
    description="gpt-4o call",
    detail={"model": "gpt-4o", "prompt_tokens": 100, "completion_tokens": 50, "provider_cost": 0.010}
)
```

### 14.6 unity CodeAct（typed primitives）

```python
# Actor 内部 Python 程序
contacts = await primitives.contacts.ask(
    "Who was involved in the Henderson project?"
)
for contact in contacts:
    history = await primitives.knowledge.ask(
        f"What was {contact} last working on?"
    )
    await primitives.contacts.update(
        f"Send {contact} a catch-up email referencing {history}"
    )

# 长期任务：返回 handle 让用户能 steering
return await primitives.tasks.execute("Generate the quarterly report")
```

### 14.7 unity Steerable Handle

```python
handle = await actor.act("Research flights to Tokyo and draft an itinerary")

# 20s 后，工作还在进行：
await handle.interject("Also check train options from Tokyo to Osaka")

# 不打断查询
status = await handle.ask("What have you found so far?")

# 暂停 / 恢复
await handle.pause()
# ... 处理紧急事 ...
await handle.resume()

# 停止
await handle.stop("No longer needed")
```

### 14.8 unity 双脑语音

```bash
# 安装 voice 组件
unity voice setup
# 装 livekit-server + 写 LIVEKIT_URL/LIVEKIT_API_KEY/SECRET

# 准备 keys（写在 .env）
DEEPGRAM_API_KEY=...    # STT
CARTESIA_API_KEY=...    # TTS（可选 ElevenLabs）
```

```bash
# 两个终端
unity --live-voice      # Terminal 1
unity logs              # Terminal 2

# 在 chat 里：
> call         # 打开 LiveKit Agents Playground 浏览器
> end_call     # 拆房间
```

### 14.9 Orchestra 本地开发

```bash
# Postgres + pgvector
docker run --name orchestra-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=orchestra -e POSTGRES_USER=orchestra \
  -e POSTGRES_DB=orchestra \
  pgvector/pgvector:pg15

# 安装 + migrate
poetry install --with dev
alembic upgrade head
poetry run python -m orchestra

# API 跑在 http://127.0.0.1:8000/v0
```

### 14.10 Unity 自然语言 schedule

```python
# 不用 cron，直接告诉 agent
"Every Monday at 9, summarize my unread emails"
"Ping me whenever Alice emails about invoices"

# → 存为 Task，schedule + repeat 或 trigger 字段
# → 触发时 contained Actor run 醒过来，读 description
# → 多次成功后自动毕业为 stored function
```

---

## 15. 关键设计权衡（Trade-offs）

### 15.1 English-as-API 设计的代价

| 收益 | 代价 |
|---|---|
| Caller 不耦合 SQL/CRUD | 每个 manager call 加 1-3 秒 |
| 可读性高 | 每次 ask 都要 1 次 LLM 跳转 |
| Manager 可替换 | 不可控的 cost |
| 组合自然 | 调试难（LLM 可能误解） |

### 15.2 CodeAct vs JSON Tool Call

| 收益 | 代价 |
|---|---|
| 减少 round-trip | 1 段 Python 错误整个 plan 失败 |
| 真正的控制流 | LLM 写代码能力比 tool 选择更挑剔 |
| 避免 context 爆炸 | 错误处理更复杂 |
| | 调试更难（不像 tool call 有结构化 trace） |

### 15.3 Dual-Brain 的复杂度

| 收益 | 代价 |
|---|---|
| Voice 不死等 | 两个进程要 IPC 协调 |
| Sub-second turn-taking | 状态同步问题（slow brain 改主意 vs fast brain 已说出） |
| Sub-agent 灵活 | 部署复杂度（LiveKit 二进制要本地跑） |
| | Speech urgency evaluator 引入新失败模式 |

### 15.4 Steerable Handle 嵌套

| 收益 | 代价 |
|---|---|
| Mid-flight 控制是独门武器 | 协议实现复杂 |
| 每层有自主策略 | 用户需要学习 ask/interject/pause/resume 区别 |
| | Cancellation 语义在嵌套时容易乱 |

---

## 16. 对小B 行业软件副业的启发

小F 正在做 5-15 万/年的小B 商户数字化转型软件，Unify 的设计对这种场景有几条直接启发：

### 16.1 "English-as-API manager" 适合复杂业务对象

小B 软件（餐饮、汽修、零售）有大量异构数据：菜品、工单、库存、会员...。  
如果照搬 Unify 的 "manager 把 SQL 屏蔽掉，对外暴露 `text: str` 询问接口"，可以让**非技术客户配置**："查过去 7 天退菜最多的 3 道菜"，而不用写 SQL。

### 16.2 "CodeAct over typed primitives" 适合复杂业务流

小B 客户的"老板"是中间人 — 既不是开发者也不是终端用户。CodeAct 让 LLM 直接生成可审计的 Python 计划（"先查库存，再生成补货单"），比"5 步 JSON tool call"对老板更友好。

### 16.3 "Steerable handles" 解决对话中途改需求

小B 老板最常做的是 "等等，加个条件" — 中途插入"这个客户是 VIP，要打 8 折"。Unify 的嵌套 handle 模式天然支持这个 — 不需要重跑整个 plan。

### 16.4 "0% 平台费" 适合小B 成本敏感

小B 软件客户 5-15 万/年的预算，平台费要控制。Unify 的 pass-through 定价和 code 全开源，是可借鉴的差异化定位。

### 16.5 ⚠️ 不要照搬"全平台 agent"

Unify 走的是**重 agent runtime 路线**（CodeAct + dual-brain + 结构化 memory）。这条路对个人 assistant 合理，但小B 行业软件**不需要 voice + 跨 channel**。  
**结论**：学 Unify 的"English-as-API manager"和"嵌套 handle"模式，但**砍掉 voice/double-brain**，保留 typed primitive + structured memory 即可。

### 16.6 仓库拆分的可借鉴点

Unify 把 `kernel`（orchestra-core，单租户）从 `platform`（orchestra-platform，多租户）拆开：
- kernel 完全开源，platform 私有
- 客户要私有部署 → 拿 kernel 跑
- 客户要 SaaS → 走 platform

小B 软件也建议这种"双层"：
- 核心引擎（业务逻辑）开源 / 可私有部署
- 客户管理 + 计费 + 控制台走 SaaS

---

## 17. 时间线与未来动向推测

| 时间 | 事件 |
|---|---|
| 2023 | Unify.ai 创立（伦敦） |
| 2024 H1 | LLM 智能路由 SaaS 上线（unify-python-client） |
| 2024 H2 | 转向 agent 方向；拆分 orchestra-core/orchestra-platform |
| 2025 H1 | unity + unillm + unify 三件套开源 |
| 2025 H2 | dual-brain voice 上线；steerable handle 协议发布 |
| 2026 Q1 | CodeAct + structural memory 公开；`unifai-network` 独立项目（DeFi） |
| 2026 Q2 | console.unify.ai 公开发布 · $75/月定价 |

**未来可能**：
- 智能路由（SaaS 层）回归 — 把旧 unify 智能路由产品作为 "Unity smart router" 加进 SaaS
- MCP / A2A 集成
- 公开 customer case studies + 行业垂直版本
- Voice 多语言（目前只测过英文文档）

---

## 18. 信息源

| 来源 | 关键信息 |
|---|---|
| unify.ai/ | home, pricing |
| docs.unify.ai/*.md（通过 llms.txt 索引） | 全套 architecture 文档 |
| github.com/unifyai/orgs | 仓库列表 |
| raw.githubusercontent.com/unifyai/unillm/main/README.md | unillm 全功能 |
| raw.githubusercontent.com/unifyai/unillm/main/unillm/costs.py | 1.2x margin |
| raw.githubusercontent.com/unifyai/unillm/main/unillm/clients/uni_llm.py | 基于 LiteLLM |
| raw.githubusercontent.com/unifyai/unity/main/README.md | unity 架构 |
| raw.githubusercontent.com/unifyai/orchestra/main/README.md | orchestra 平台/内核分离 |
| raw.githubusercontent.com/unifyai/unify/main/README.md | SDK 角色 |

---

## 19. 结论

**Unify 的产品本质不是 LLM Gateway，而是一个 "AI 同事"平台** — 其中 LLM 路由（unillm）是它的内部 subsystem。

**它对 LLM Gateway 领域的真实贡献**：
- OpenTelemetry 标准化的可观测性（unillm）
- Pass-through 0% 平台费定价
- 4 模式缓存 + CI cache 复用
- Cost accounting 抽象

**它对 Agent 领域的真实贡献**：
- Steerable handles 嵌套 steering 协议（无对手）
- CodeAct + typed domain primitives 组合
- Dual-brain voice 桥接 turn-taking 与 long thinking
- 结构化 long-term memory 替代 MEMORY.md

**对小B 行业软件副业的启发**：
- 学 "English-as-API manager" 和 "嵌套 handle"
- 砍 voice 和 double-brain
- 走 pass-through 定价
- 区分 kernel（开源）vs platform（私有 SaaS）

**总评**：Unify 是 LLM Gateway 赛道里**最有产品深度**的玩家，但**定位已经偏离**。如果你想找智能路由 + failover 的 LLM Gateway，**Unify 不是首选**（Portkey / LiteLLM / Not Diamond 才是）。如果你想找"AI 同事"产品形态的灵感和参考实现，**Unify 是必看**。

---

> 字数统计：本文档约 700+ 行，覆盖项目背景、架构（4 层）、LLM 路由（unillm）、Agent runtime（unity）、后端（orchestra）、协议、性能、部署、成本、生态、客户、优劣势、对比、设计权衡、副业启发、时间线、信息源、结论。
