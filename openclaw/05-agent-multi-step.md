# Agent 多步调用：状态、循环、可观测与网关新挑战

> 系列：AI Gateway 持续深挖 · 第 5 篇
> 性质：纯技术研究
> 范围：Agent 时代对 AI Gateway 提出的新挑战、多步调用的状态管理、循环控制、调试回放

---

## 目录

- [一、Agent 时代来了](#一agent-时代来了)
- [二、Agent 调用的形态分类](#二agent-调用的形态分类)
- [三、单 Agent 多步调用的内部结构](#三单-agent-多步调用的内部结构)
- [四、多 Agent 协作的通信结构](#四多-agent-协作的通信结构)
- [五、状态管理：从无状态到全状态](#五状态管理从无状态到全状态)
- [六、循环控制：何时停止、怎样重试](#六循环控制何时停止怎样重试)
- [七、成本与延迟的指数级挑战](#七成本与延迟的指数级挑战)
- [八、可观测：Agent 调用的"录像"机制](#八可观测agent-调用的录像机制)
- [九、网关层 Agent-aware 设计](#九网关层-agent-aware-设计)
- [十、Memory 与 Context Engineering](#十memory-与-context-engineering)
- [十一、未解难题与研究前沿](#十一未解难题与研究前沿)
- [十二、参考资料](#十二参考资料)

---

## 一、Agent 时代来了

### 1.1 什么是 Agent

**Agent** = 能自主规划、调用工具、与环境交互、完成多步任务的 LLM 系统。

**从 Chat 到 Agent 的跃迁**：

| 维度 | Chat (单次) | Agent (多步) |
|---|---|---|
| 调用次数 | 1 | N（5-50+） |
| 工具使用 | 0-1 | 多工具循环 |
| 决策者 | 用户 | Agent 自主 |
| 状态 | 无 | 长状态 |
| 失败模式 | 答错 | 卡死循环、错路径 |
| 成本 | 1x | 5-100x |
| 延迟 | 几秒 | 几十秒到几小时 |

### 1.2 为什么这对 AI Gateway 重要

- **流量模式变了**：从"短而多"变成"长而少"
- **状态管理变了**：从"无状态"变成"长连接"
- **可观测变了**：从"单次请求"变成"多步调用链"
- **成本归因变了**：从"按请求"变成"按任务 + 步骤"
- **失败模式变了**：从"出错"变成"卡死"

### 1.3 当前生态

- **框架**：LangGraph、AutoGen、CrewAI、Letta（MemGPT）、Agno
- **协议**：MCP（工具调用）、A2A（Agent 间）
- **平台**：OpenAI Assistants / Agents、Anthropic Computer Use、Google Agents

---

## 二、Agent 调用的形态分类

### 2.1 简单循环 Agent

```python
while not done:
    response = llm(messages)
    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            result = execute(tool_call)
            messages.append(result)
    else:
        done = True
return response
```

**典型场景**：单次任务、5-10 步。

### 2.2 Plan-and-Execute Agent

```python
# 第一阶段：规划
plan = llm("Given task X, generate a step-by-step plan")
# plan: ["step1: search", "step2: parse", "step3: write"]

# 第二阶段：执行
for step in plan:
    result = execute_step(step)
    if needs_replan(result):
        plan = replan(plan, result)
```

**典型场景**：复杂任务、20-50 步。

### 2.3 ReAct Agent

```
Thought: I need to find the weather in SF
Action: get_weather(SF)
Observation: 65°F sunny
Thought: Now I can answer
Action: Finish("It's 65°F and sunny in SF")
```

**典型场景**：需要推理的工具调用。

### 2.4 Multi-Agent 协作

```
Orchestrator Agent
├── Research Agent
│     ├── search_web
│     └── summarize
├── Coding Agent
│     ├── write_code
│     └── test_code
└── Reviewer Agent
      └── check_quality
```

**典型场景**：复杂工作流、需要专业化分工。

### 2.5 长期任务 Agent

```python
# 跨会话持续工作
while not goal_achieved:
    context = load_from_memory()
    response = llm(context)
    if response.needs_human_input:
        return ask_human(response.question)
    execute(response.actions)
    save_to_memory(response, result)
```

**典型场景**：Devin 类、AutoGPT 类。

---

## 三、单 Agent 多步调用的内部结构

### 3.1 典型调用链

```
Task: "帮我订明天从北京到上海的高铁票"
Step 1: 搜索车次
  LLM Call #1: 解析用户意图 → 调用 search_trains
  Tool Call: search_trains("北京", "上海", "明天")
  Tool Result: [G1, G3, G7, G11...]
Step 2: 选择车次
  LLM Call #2: 根据偏好筛选 → 选择 G7
Step 3: 检查用户身份
  LLM Call #3: 读取用户信息 → 调用 get_user_info
  Tool Call: get_user_info(user_id)
  Tool Result: {name: "...", id_card: "..."}
Step 4: 确认价格
  LLM Call #4: 计算价格 → 调用 get_price
  Tool Call: get_price(G7, user_id)
  Tool Result: ¥553
Step 5: 询问用户确认
  LLM Call #5: 决定是否需要用户确认
  Final Response: "已找到 G7 次列车，¥553。是否确认预订？"
```

### 3.2 Trace 结构

```
Trace: book_train_task
├── Span: agent.think          [step 1, 800ms]
│   ├── Span: llm_call #1      [1200ms]
│   │     tokens: 800 in, 50 out
│   ├── Span: tool.search_trains [200ms]
│   └── Event: agent.thought
├── Span: agent.think          [step 2, 600ms]
│   ├── Span: llm_call #2      [900ms]
│   └── Event: agent.thought
├── Span: agent.think          [step 3, 500ms]
│   ├── Span: llm_call #3      [700ms]
│   ├── Span: tool.get_user_info [100ms]
│   └── Event: agent.thought
├── Span: agent.think          [step 4, 500ms]
│   ├── Span: llm_call #4      [800ms]
│   ├── Span: tool.get_price   [100ms]
│   └── Event: agent.thought
└── Span: agent.think          [step 5, 400ms]
    ├── Span: llm_call #5      [600ms]
    └── Event: agent.final_answer
```

**关键观察**：
- 一个 Task 包含多个 Step
- 每个 Step 包含 1+ 个 LLM Call + 0+ Tool Call
- 总计 5 个 LLM Call + 3 个 Tool Call

### 3.3 消息状态演化

```python
# Step 1 后的 messages
messages = [
    system: "你是订票助手",
    user: "帮我订明天从北京到上海的高铁票",
    assistant: tool_call(search_trains),
    tool: "G1, G3, G7, G11..."
]

# Step 2 后的 messages
messages = [
    system: "...",
    user: "...",
    assistant: tool_call(search_trains),
    tool: "G1, G3, G7, G11...",
    assistant: "推荐 G7 次列车，14:00 发车..."  # ← Step 2 的输出
]

# Step 3 后的 messages
messages = [
    ...,
    assistant: tool_call(get_user_info),
    tool: "{name: ..., id_card: ...}"
]
```

**状态增长**：每步都往 messages 里追加，线性增长。

---

## 四、多 Agent 协作的通信结构

### 4.1 编排模式

#### 模式 A：中央编排

```
                Orchestrator
                /     |     \
            Agent1  Agent2  Agent3
              |       |       |
           tools    tools    tools
```

**特点**：单一调度者，决策集中
**代表**：CrewAI、LangGraph supervisor

#### 模式 B：对等通信

```
            Agent1 <---> Agent2
              ^           ^
              |           |
            Agent3 <---> Agent4
```

**特点**：去中心化、点对点
**代表**：AutoGen 群聊

#### 模式 C：流水线

```
Input → Agent1 → Agent2 → Agent3 → Output
```

**特点**：单向、固定流程
**代表**：SequentialChain

#### 模式 D：事件驱动

```
       Event Bus
      /     |     \
   Agent1  Agent2  Agent3
```

**特点**：解耦、可扩展
**代表**：Temporal + Agent

### 4.2 多 Agent 的 trace 挑战

```
Trace: complex_task
├── Span: orchestrator.decide
├── Trace: agent1.subtask
│     ├── Span: agent1.llm
│     └── Span: agent1.tool
├── Trace: agent2.subtask
│     ├── Span: agent2.llm
│     ├── Trace: agent2.delegate
│     │     └── Trace: agent2_1.subsubtask
│     └── Span: agent2.tool
└── Trace: agent3.subtask
```

**嵌套 Trace**——OpenTelemetry 支持，但工具支持不完善。

---

## 五、状态管理：从无状态到全状态

### 5.1 状态类型

| 类型 | 例子 | 存储位置 |
|---|---|---|
| **消息历史** | messages 列表 | 内存 / DB |
| **工具结果** | tool_call_id → result | 内存 / 缓存 |
| **中间变量** | agent scratchpad | 内存 |
| **任务状态** | step 进度、checkpoint | DB |
| **长期记忆** | 用户偏好、历史对话 | 向量库 / KV |
| **外部状态** | DB / API 调用结果 | 外部系统 |

### 5.2 状态存储方案

#### 方案 1：纯内存

```python
class Agent:
    def __init__(self):
        self.messages = []
    
    def step(self, user_input):
        self.messages.append(user_input)
        response = llm(self.messages)
        self.messages.append(response)
        return response
```

**优点**：快
**缺点**：进程崩了就丢、不能跨实例

#### 方案 2：Checkpoint 到 DB

```python
# LangGraph 的做法
class Agent:
    def step(self, state):
        new_state = llm(state)
        checkpoint_to_db(new_state)  # 每步存档
        return new_state

# 崩溃后可从 checkpoint 恢复
```

**优点**：可恢复、可调试
**缺点**：每步 IO 开销

#### 方案 3：Redis 缓存 + DB 持久化

```python
# 短期状态（当前 session）放 Redis
# 长期状态（用户历史）放 DB
```

### 5.3 状态序列化挑战

| 挑战 | 描述 |
|---|---|
| **messages 体积** | 50 步调用可能 100K+ tokens |
| **工具结果** | 可能含大型对象（图、文件、二进制） |
| **特殊类型** | datetime / Decimal / 自定义类 |
| **跨语言** | Python 状态 → JS 客户端 |
| **版本兼容** | 状态 schema 升级 |

### 5.4 Context Window 限制与压缩

每步都往 messages 里塞东西，**最终会超 context window**。必须压缩。

#### 策略 1：滑动窗口

```python
def trim_messages(messages, max_tokens=100000):
    # 只保留最近 N 条
    return messages[-20:]
```

#### 策略 2：摘要压缩

```python
def summarize_old_steps(messages, keep_recent=5):
    if len(messages) <= keep_recent * 2:
        return messages
    old = messages[:-keep_recent*2]
    recent = messages[-keep_recent*2:]
    summary = llm(f"总结以下对话:\n{old}", max_tokens=500)
    return [{"role": "system", "content": f"历史摘要: {summary}"}] + recent
```

#### 策略 3：分层 Memory

```
工作记忆 (working memory)  ← 当前任务上下文
├── 短期记忆 (short-term)  ← 当前 session 对话
└── 长期记忆 (long-term)   ← 用户偏好、事实知识
```

### 5.5 Checkpoint 与重放

```python
# LangGraph 的 checkpoint 机制
{
    "thread_id": "task-123",
    "checkpoint_id": "ckpt-5",
    "state": {
        "messages": [...],
        "current_step": 5,
        "scratchpad": {...}
    },
    "next_action": "agent.think",
    "parent_checkpoint_id": "ckpt-4"
}
```

**价值**：
- **崩溃恢复**：从最近 checkpoint 继续
- **时间旅行调试**：回到某步重新执行
- **A/B 测试**：同一状态走不同路径

---

## 六、循环控制：何时停止、怎样重试

### 6.1 三种停止条件

```python
class Agent:
    def __init__(self, max_steps=20, max_cost=1.0, max_time=300):
        self.max_steps = max_steps
        self.max_cost = max_cost
        self.max_time = max_time  # 秒
        self.steps = 0
        self.cost = 0
        self.start_time = time.time()
    
    def should_stop(self, response):
        self.steps += 1
        self.cost += response.cost
        elapsed = time.time() - self.start_time
        
        # 显式终止
        if response.done:
            return "completed"
        # 步数限制
        if self.steps >= self.max_steps:
            return "max_steps_reached"
        # 成本限制
        if self.cost >= self.max_cost:
            return "max_cost_reached"
        # 时间限制
        if elapsed >= self.max_time:
            return "timeout"
        return None
```

### 6.2 循环检测

Agent 卡在循环是常见 bug。

```python
def detect_loop(state_history, window=5):
    # 检测最近 N 步是否高度相似
    recent = state_history[-window:]
    # 简单的：检测 action 序列是否重复
    actions = [s.action for s in recent]
    if len(set(actions)) <= 2 and len(actions) >= window:
        return True
    return False
```

### 6.3 错误处理与重试

```python
class Agent:
    def execute_with_retry(self, action, max_retries=3):
        for attempt in range(max_retries):
            try:
                return execute(action)
            except TransientError as e:
                if attempt < max_retries - 1:
                    # 让 LLM 重新规划
                    new_plan = llm(f"上次失败: {e}, 重新规划")
                    action = new_plan.action
                else:
                    raise
            except PermanentError:
                raise
```

### 6.4 自我纠错（Self-Correction）

```python
def agent_step_with_correction(self, state):
    response = llm(state)
    
    if response.has_tool_calls:
        results = []
        for call in response.tool_calls:
            result = execute(call)
            # 验证结果
            if not is_valid(result):
                # 让 LLM 重新规划
                correction_response = llm(f"""
                原计划: {call}
                执行失败: {result}
                请重新规划或调整参数。
                """)
                results.append(correction_response)
            else:
                results.append(result)
        return results
    return response
```

---

## 七、成本与延迟的指数级挑战

### 7.1 成本爆炸

```
单步成本 = 0.01 USD
20 步 = 0.20 USD
100 步 = 1.00 USD
500 步 = 5.00 USD
1 Agent 跑 1000 个任务 = 1000 USD
```

**成本失控场景**：
- 死循环（卡 500 步）
- 复杂 RAG（每步都检索 + LLM）
- 多 Agent 嵌套（指数级放大）

### 7.2 延迟爆炸

```
单步 LLM 延迟 = 1s
工具调用 = 0.5s
状态序列化 = 0.1s
20 步 = 32s  (用户已经不耐烦)
50 步 = 82s
```

### 7.3 应对策略

#### 策略 1：硬性限制

```python
class AgentLimits:
    max_steps = 20
    max_cost_usd = 0.5
    max_wall_time_s = 60
    max_tool_calls = 50
```

#### 策略 2：成本预估前置

```python
def estimate_cost(plan):
    # 简单的线性估算
    steps = len(plan.steps)
    return steps * AVG_STEP_COST

def estimate_cost_detailed(plan, model_costs):
    cost = 0
    for step in plan:
        cost += model_costs[step.model] * estimate_tokens(step)
    return cost
```

#### 策略 3：早停机制

```python
def should_stop_early(state, threshold=0.95):
    # 如果最近几步答案高度一致
    # 任务已收敛
    if state.consecutive_similar_answers > 3:
        return True
    return False
```

#### 策略 4：分阶段预算

```python
class StagedBudget:
    def __init__(self):
        self.stage_budgets = {
            "planning": 0.05,
            "execution": 0.30,
            "verification": 0.10,
            "recovery": 0.05
        }
        self.current_stage = "planning"
    
    def can_continue(self):
        return self.spent[self.current_stage] < self.stage_budgets[self.current_stage]
```

### 7.4 实时成本展示

给用户一个"进度条"：

```
Agent 任务: 订高铁票
进度: ████████░░ 80%
已用成本: ¥0.45 / ¥0.50 预算
已用时间: 23s / 60s
当前步骤: 等待用户确认
```

---

## 八、可观测：Agent 调用的"录像"机制

### 8.1 三个层级

| 层级 | 内容 | 用途 |
|---|---|---|
| **Step 级** | 每步的 LLM 调用 + 工具调用 | 性能分析 |
| **Task 级** | 整个任务的多步链路 | 调试、回放 |
| **Session 级** | 跨任务的会话历史 | 用户行为分析 |

### 8.2 "录像"的关键字段

```json
{
  "task_id": "task-123",
  "thread_id": "thread-456",
  "user_id": "user-789",
  "start_time": "2026-06-05T10:00:00Z",
  "end_time": "2026-06-05T10:00:32Z",
  "total_steps": 5,
  "total_cost_usd": 0.18,
  "total_tokens": 12500,
  "status": "completed",
  "final_answer": "已找到 G7 次列车，¥553。是否确认预订？",
  "steps": [
    {
      "step_id": 1,
      "type": "think",
      "thought": "用户要订明天北京到上海的高铁，我需要先查车次",
      "action": "search_trains",
      "action_input": {"from": "北京", "to": "上海", "date": "明天"},
      "observation": "G1, G3, G7, G11...",
      "duration_ms": 1400,
      "cost_usd": 0.04,
      "tokens": 1500
    },
    ...
  ]
}
```

### 8.3 时间旅行调试

```python
# 从第 3 步重放
agent.replay_from_checkpoint(
    checkpoint_id="ckpt-3",
    override_plan=["新计划"],
)
```

### 8.4 Agent 评估

#### 离线评估

```python
# 跑 100 个测试 task，统计成功率、平均步数、平均成本
def evaluate_agent(agent, test_tasks):
    results = []
    for task in test_tasks:
        result = agent.run(task)
        results.append({
            "task": task,
            "success": evaluate(result),
            "steps": result.steps,
            "cost": result.cost
        })
    return aggregate_metrics(results)
```

#### 在线评估

- **任务成功率**：用户最终是否完成目标
- **人工评估**：抽样让人看
- **A/B 测试**：不同 prompt/策略对比
- **用户反馈**：点赞/点踩

---

## 九、网关层 Agent-aware 设计

### 9.1 网关能感知什么

```
HTTP Request Headers:
  X-Agent-Thread-ID: thread-456
  X-Agent-Task-ID: task-123
  X-Agent-Step: 3
  X-Agent-Total-Steps: 5
  
OR

Body Metadata:
{
  "messages": [...],
  "agent_context": {
    "thread_id": "thread-456",
    "step": 3,
    "plan": [...]
  }
}
```

### 9.2 网关应该做什么

#### 能力 1：整任务计费

```python
# 传统：按单次请求计费
# Agent 时代：按整任务计费
gateway.billing_strategy = "per_task"
gateway.task_cost = sum(step_costs) + overhead
```

#### 能力 2：Agent 级别限流

```python
# 传统：限制单用户 QPS
# Agent 时代：限制单用户并发 Agent 任务数
gateway.agent_concurrency_limit = {"free": 2, "paid": 10}
```

#### 能力 3：整任务超时

```python
# 网关为整任务设置 deadline
gateway.task_deadline = start_time + 120  # 秒
# 在每步检查：如果剩余时间 < 阈值，强制终止
```

#### 能力 4：Agent 路由

```python
# 不同 Agent 任务用不同模型
gateway.route_rules = [
    {
        "match": {"agent_type": "research"},
        "model": "gpt-4o"  # 研究类用强模型
    },
    {
        "match": {"agent_type": "chat"},
        "model": "gpt-4o-mini"
    }
]
```

#### 能力 5：循环检测

```python
# 网关层检测 Agent 是否卡死
class AgentLoopDetector:
    def __init__(self, gateway):
        self.gateway = gateway
    
    def check(self, step_history):
        # 检测：连续 N 步输出高度相似
        recent_actions = [s.action for s in step_history[-5:]]
        if len(set(recent_actions)) <= 1:
            self.gateway.kill_task(reason="detected_infinite_loop")
```

### 9.3 网关不应该做什么

- **不负责 Agent 编排**（那是 LangGraph 的活）
- **不负责 Memory 存储**（那是专门的 Memory 服务的活）
- **不负责工具执行**（那是 MCP server 的活）

**定位**：网关是 Agent 流量的"观测点 + 控制点 + 计费点"。

---

## 十、Memory 与 Context Engineering

### 10.1 Memory 的分类

```
Memory
├── 工作记忆 (Working Memory)
│     └── 当前 step 的临时变量
├── 短期记忆 (Short-term Memory)
│     └── 当前 session 对话历史
├── 长期记忆 (Long-term Memory)
│     ├── 情景记忆 (Episodic)：过去做过什么
│     ├── 语义记忆 (Semantic)：学到的知识
│     └── 程序记忆 (Procedural)：技能、习惯
└── 共享记忆 (Shared Memory)
      └── 多 Agent 共享的事实
```

### 10.2 Memory 存储选型

| 类型 | 工具 | 用途 |
|---|---|---|
| **向量库** | Qdrant / Milvus / pgvector | 语义记忆、检索 |
| **KV 存储** | Redis | 工作记忆、短期 |
| **文档库** | PostgreSQL / MongoDB | 长期情景、语义 |
| **图存储** | Neo4j | 关系型记忆（知识图谱） |
| **文件系统** | S3 | 大型对象（图、文件） |

### 10.3 Context Engineering

**Context Engineering** = 在 context window 有限的情况下，把**最相关的信息**塞进去的艺术。

#### 技术 1：RAG

把外部知识检索后塞入 prompt。

#### 技术 2：Compress（压缩）

```python
def compress_conversation(messages):
    summary = llm(f"摘要以下对话：\n{messages}", max_tokens=500)
    return [
        {"role": "system", "content": f"对话摘要：{summary}"}
    ] + messages[-3:]  # 保留最近 3 轮
```

#### 技术 3：Prune（剪枝）

```python
def prune_tool_results(messages):
    # 工具结果太长就截断
    for m in messages:
        if m.role == "tool" and len(m.content) > 1000:
            m.content = m.content[:500] + "...[truncated]"
    return messages
```

#### 技术 4：Reorder（重排）

把最重要的信息（最近的用户消息、当前任务）放到 context 的中后部（attention 衰减前）。

#### 技术 5：External Memory

```python
# 把详细信息存到外部，按需取用
def agent_with_external_memory(query):
    # 1. 检索相关 memory
    relevant = memory.search(query, top_k=3)
    # 2. 构造 prompt（只放相关 memory）
    prompt = build_prompt(query, relevant)
    # 3. LLM 调用
    return llm(prompt)
```

---

## 十一、未解难题与研究前沿

### 11.1 状态管理

1. **Agent 状态标准格式**——类似 OpenLLMetry 的统一标准？
2. **跨语言 Agent 状态**——Python 状态序列化给 JS 客户端
3. **状态压缩的最优策略**——保留多少历史？
4. **状态共享的安全边界**——多租户 Agent 怎么共享 memory？
5. **状态版本控制**——Agent "rebase" 的可行性

### 11.2 循环与终止

6. **循环检测**的标准算法？
7. **自我纠错**什么时候该停？什么时候该重试？
8. **任务提前收敛**的判断标准？
9. **人类介入**的最优时机（Human-in-the-loop）？
10. **任务取消**的状态一致性？

### 11.3 成本控制

11. **预算感知 Agent**——Agent 知道自己有预算并合理分配
12. **早停的经济学**——什么时候停止是"省了"而不是"亏了"
13. **成本预估的准确度**——和实际偏差多少？
14. **多 Agent 的成本博弈**——子 Agent 互相"花钱"

### 11.4 可观测

15. **Agent trace 的标准格式**——OTel 是否够用？
16. **多 Agent 嵌套 trace**的工具支持
17. **Agent 回放的"完美"程度**——状态重放 vs 外部副作用
18. **Agent 失败归因**——是 prompt 错？工具错？模型错？
19. **跨任务的 Memory 追溯**——Agent 怎么从历史学？

### 11.5 评估

20. **Agent 评估的 ground truth**——很多任务没有标准答案
21. **长尾任务评估**——99% 任务没见过怎么评估？
22. **多 Agent 系统评估**——整体质量 vs 单 Agent 质量
23. **效率 vs 质量的帕累托前沿**——怎么找？
24. **A/B 测试在 Agent 时代的统计方法**

### 11.6 网关层

25. **Agent 流量**的特征提取（用什么 header / metadata）
26. **网关该不该有 Agent 编排能力**？——还是应该中立
27. **Agent 流量 vs 普通流量的资源调度**（K8s 视角）
28. **Agent 流量的 SLA 保障**——长任务 vs 短任务
29. **Agent 任务的优先级调度**——付费用户 vs 免费用户

### 11.7 标准化

30. **Agent 协议之争**——MCP / A2A / LangGraph / AutoGen 谁会胜出？
31. **OpenAI Agents / Anthropic Computer Use** 的标准化可能性
32. **Agent marketplace** 的标准化（共享 Agent / 共享工具）

### 11.8 未来形态

33. **Agent 自身的 AI 化**——Agent 优化 Agent
34. **多 Agent 涌现行为**——会出现什么意料之外的能力
35. **Agent 经济**——Agent 雇佣 Agent 完成任务的"市场"

---

## 十二、参考资料

### 12.1 框架与平台

- github.com/langchain-ai/langgraph
- github.com/microsoft/autogen
- github.com/joaomdmoura/crewAI
- github.com/letta-ai/letta（MemGPT）
- OpenAI Agents SDK
- Anthropic Computer Use
- Google Agent Development Kit (ADK)

### 12.2 协议

- modelcontextprotocol.io
- google.github.io/A2A
- OpenAI Function Calling / Tools

### 12.3 论文

- "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022)
- "Reflexion: Language Agents with Verbal Reinforcement Learning" (Shinn et al., 2023)
- "AutoGPT: An Autonomous GPT-4 Experiment"
- "MemGPT: Towards LLMs as Operating Systems" (Packer et al., 2023)
- "Voyager: An Open-Ended Embodied Agent with Large Language Models"
- "Toolformer: Language Models Can Teach Themselves to Use Tools"

### 12.4 评估基准

- SWE-bench (代码 Agent)
- WebArena (网页 Agent)
- AgentBench (综合)
- GAIA (通用助手)
- ToolBench
- BFCL (Berkeley Function Calling)

### 12.5 关键博客

- LangChain "State of Agents 2024"
- LangGraph 架构博客
- Anthropic "Building effective agents"
- OpenAI "A Practical Guide to Building Agents"
- "Why Agents Crash" 系列

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 5 篇
- 主题：Agent 多步调用与状态管理
- 上一份：04-observability-openllmetry.md
- 下一份预告：Guardrails 技术栈与 PII / 注入防护
