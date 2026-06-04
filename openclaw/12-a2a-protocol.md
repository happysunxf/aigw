# A2A 协议与多 Agent 互联：跨厂商 Agent 通信的未来

> 系列：AI Gateway 持续深挖 · 第 2 批 · 第 2 篇
> 性质：纯技术研究
> 范围：A2A（Agent-to-Agent）协议、Google 主推、多 Agent 通信、网关集成

---

## 目录

- [一、A2A 是什么、不是什么](#一a2a-是什么不是什么)
- [二、A2A 与 MCP 的关系](#二a2a-与-mcp-的关系)
- [三、A2A 架构深度剖析](#三a2a-架构深度剖析)
- [四、Agent Card 详解](#四agent-card-详解)
- [五、Task 生命周期](#五task-生命周期)
- [六、Message 与 Artifact](#六message-与-artifact)
- [七、通信模式](#七通信模式)
- [八、安全与鉴权](#八安全与鉴权)
- [九、实现参考](#九实现参考)
- [十、A2A 与多 Agent 框架对比](#十a2a-与多-agent-框架对比)
- [十一、AI 网关与 A2A 集成](#十一ai-网关与-a2a-集成)
- [十二、A2A 生态与未来](#十二a2a-生态与未来)
- [十三、未解难题与研究前沿](#十三未解难题与研究前沿)
- [十四、参考资料](#十四参考资料)

---

## 一、A2A 是什么、不是什么

### 1.1 一句话定义

**A2A（Agent-to-Agent Protocol）** = Google 2025 年推出的、**让不同厂商/框架的 AI Agent 跨平台通信**的标准化协议。

### 1.2 类比

| 类比 | 描述 |
|---|---|
| **SMTP 之于邮件** | A2A 之于 Agent |
| **HTTP 之于 Web 服务** | A2A 之于 Agent 服务 |
| **gRPC 之于微服务** | A2A 之于 Agent 微服务 |

### 1.3 A2A 解决的核心问题

#### 问题 1：Agent 孤岛

```
当前现状：
- OpenAI Agent、Anthropic Computer Use、LangGraph Agent、CrewAI Agent...
- 各自封闭，无法跨平台协作
- 企业想"混合"使用多个 Agent 平台，难
```

#### 问题 2：Agent 发现困难

```
"我想找一个能分析合同的 Agent"
"哪里有？什么能力？"
```

#### 问题 3：Agent 互操作

```
- A Agent 想调用 B Agent 的能力
- A 和 B 协议不同、鉴权不同、数据格式不同
```

### 1.4 A2A 不是什么

| 误解 | 真相 |
|---|---|
| "A2A 替代 MCP" | 互补：MCP 是 Agent ↔ 工具，A2A 是 Agent ↔ Agent |
| "A2A 只支持 Google Agent" | 开放标准，多家实现 |
| "A2A = LangGraph" | A2A 是协议，LangGraph 是框架 |
| "A2A 适合所有场景" | 主要适合跨组织、跨平台 Agent 协作 |
| "A2A 成熟了" | 早期，2025 刚发布 |

---

## 二、A2A 与 MCP 的关系

### 2.1 协议栈定位

```
┌─────────────────────────────────────┐
│ 应用层：多 Agent 协作任务              │
├─────────────────────────────────────┤
│ A2A：Agent ↔ Agent 通信              │  ← 横向（Agent 间）
├─────────────────────────────────────┤
│ MCP：Agent ↔ 工具/数据               │  ← 纵向（Agent 内）
├─────────────────────────────────────┤
│ 模型层：LLM / 推理引擎                │
├─────────────────────────────────────┤
│ 基础设施：K8s / 边缘 / Serverless     │
└─────────────────────────────────────┘
```

### 2.2 详细对比

| 维度 | MCP | A2A |
|---|---|---|
| **通信对象** | Agent ↔ 工具 | Agent ↔ Agent |
| **通信方向** | 上下（Agent 调工具） | 横向（Agent 间） |
| **对象特征** | 工具无智能 | Agent 有智能 |
| **协议** | JSON-RPC | HTTP + JSON-RPC + SSE |
| **状态** | 通常无状态 | 有（Task、Artifact） |
| **发现** | 工具列表 | Agent Card |
| **主导** | Anthropic | Google |
| **场景** | 单 Agent 工具扩展 | 多 Agent 协作 |

### 2.3 协同工作流

```
User Task
    ↓
Orchestrator Agent (A2A Client)
    ↓ A2A 调用
Specialist Agent A (A2A Server)
    ↓ MCP 调用
Tool Server (MCP Server)
    ↓
返回结果
    ↓ A2A 消息
Orchestrator
    ↓
Specialist Agent B (A2A Server)
    ↓
Artifact 返回
    ↓
最终结果
```

**例子**：
- Orchestrator 通过 A2A 找到 "Research Agent"
- Research Agent 通过 MCP 调用 web 搜索 MCP Server
- 通过 A2A 返回结果给 Orchestrator
- Orchestrator 通过 A2A 调用 "Writing Agent" 整合

### 2.4 协议栈上的关系

```
Application:  A2A + MCP 共同支撑 Agent 应用
         ↓
Protocol:    A2A 跨 Agent，MCP 跨工具
         ↓
Data:        JSON、protobuf、multipart
         ↓
Transport:   HTTP/SSE/WebSocket
```

---

## 三、A2A 架构深度剖析

### 3.1 整体架构

```
┌──────────────────────────────────────────┐
│ Agent A (Client)                         │
│                                          │
│  - 发现其他 Agent（Agent Card）          │
│  - 创建 Task                             │
│  - 订阅 Task 状态                        │
│  - 接收 Artifact                         │
└────────────────┬─────────────────────────┘
                 │ A2A (HTTP + JSON-RPC + SSE)
                 ↓
┌──────────────────────────────────────────┐
│ Agent B (Server)                         │
│                                          │
│  - 暴露 Agent Card (/agent-card)         │
│  - 接收 Task                             │
│  - 处理（可能用 LLM + 工具）             │
│  - 返回 Artifact                         │
└──────────────────────────────────────────┘
```

### 3.2 三个核心概念

| 概念 | 含义 | 类比 |
|---|---|---|
| **Agent Card** | Agent 的自我介绍（能力、URL、认证） | 简历 / 名片 |
| **Task** | Agent 间的工作单元 | 工单 |
| **Message** | Task 内的通信单元 | 工单回复 |
| **Artifact** | Task 产生的输出 | 交付物 |
| **Part** | Message/Artifact 的内容块 | 段落 / 附件 |

### 3.3 Agent Card 详解（重点）

```json
{
  "name": "Weather Research Agent",
  "description": "Analyzes weather data and provides research insights",
  "url": "https://weather-agent.example.com",
  "provider": {
    "organization": "Example Corp",
    "url": "https://example.com"
  },
  "version": "1.0.0",
  "documentationUrl": "https://weather-agent.example.com/docs",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "stateTransitionHistory": true,
    "extensions": [...]
  },
  "authentication": {
    "schemes": ["oauth2", "apiKey"],
    "credentials": "..." 
  },
  "defaultInputModes": ["text", "image"],
  "defaultOutputModes": ["text", "structured"],
  "skills": [
    {
      "id": "weather-research",
      "name": "Weather Research",
      "description": "Deep research on weather patterns",
      "tags": ["weather", "research", "climate"],
      "examples": [
        "Analyze rainfall patterns in Pacific Northwest",
        "Predict hurricane trajectories"
      ],
      "inputModes": ["text"],
      "outputModes": ["text", "structured"]
    },
    {
      "id": "weather-forecast",
      "name": "Weather Forecast",
      "description": "Generate weather forecasts",
      "tags": ["weather", "forecast"],
      "examples": [
        "What's the weather in Seattle next week?"
      ]
    }
  ]
}
```

**字段解析**：

| 字段 | 含义 |
|---|---|
| `name` | Agent 名称 |
| `description` | 简短描述 |
| `url` | Agent 的 A2A endpoint |
| `version` | 版本（用于兼容性） |
| `capabilities.streaming` | 是否支持流式 |
| `capabilities.pushNotifications` | 是否支持服务端推送 |
| `capabilities.stateTransitionHistory` | 是否保留状态历史 |
| `authentication.schemes` | 支持的认证方式 |
| `defaultInputModes` | 输入模态（text/image/audio） |
| `defaultOutputModes` | 输出模态 |
| `skills[]` | Agent 的能力列表 |
| `skills[].examples` | 调用示例（给 LLM 看） |

### 3.4 Agent Card 的发现

```
方式 1：Well-known URI
GET https://example.com/.well-known/agent.json
→ 返回 Agent Card

方式 2：注册中心
GET https://registry.a2a-protocol.org/agents?skill=weather
→ 返回匹配的 Agent Cards

方式 3：手动指定
由开发者硬编码 Agent URL
```

### 3.5 与 OpenAI Assistants / MCP 的对比

| 维度 | OpenAI Assistants | MCP Server | A2A Agent |
|---|---|---|---|
| **卡片** | ❌ 无 | tools/list | Agent Card |
| **能力描述** | model spec | tool schema | skills + examples |
| **模态** | input/output types | inputSchema | inputModes/outputModes |
| **认证** | API key | 进程隔离 | schemes |
| **发现** | API | 启动列表 | well-known / registry |

---

## 四、Agent Card 详解

### 4.1 必填字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | ✅ | Agent 名称 |
| `description` | ✅ | 简短描述 |
| `url` | ✅ | A2A endpoint |
| `version` | ✅ | 语义化版本 |
| `capabilities` | ✅ | 能力声明 |
| `defaultInputModes` | ✅ | 输入模态列表 |
| `defaultOutputModes` | ✅ | 输出模态列表 |
| `skills` | ✅ | 技能列表 |

### 4.2 选填字段

| 字段 | 说明 |
|---|---|
| `provider` | 厂商信息 |
| `documentationUrl` | 文档 |
| `authentication` | 认证方式 |
| `capabilities.extensions` | 扩展能力 |
| `skills[].examples` | 技能示例 |

### 4.3 Skills 设计最佳实践

```yaml
skills:
  - id: "code-review"
    name: "Code Review"
    description: "Reviews code for bugs, style, performance"
    tags: ["code", "review", "quality"]
    examples:
      - "Review this Python function for edge cases"
      - "Check this Go code for concurrency issues"
    inputModes: ["text"]
    outputModes: ["text", "structured"]
    
  - id: "code-translate"
    name: "Code Translation"
    description: "Translates code between programming languages"
    tags: ["code", "translation"]
    examples:
      - "Translate this Python to TypeScript"
    inputModes: ["text"]
    outputModes: ["text"]
```

**设计原则**：
- `id` 唯一
- `description` 清晰、具体
- `examples` 给出实际调用例子
- `tags` 便于发现

### 4.4 能力声明的含义

```json
{
  "capabilities": {
    "streaming": true,                    // 支持流式响应
    "pushNotifications": true,            // 支持服务端主动推送
    "stateTransitionHistory": true,       // 状态变更历史可查
    "extensions": [
      {
        "uri": "https://example.com/extensions/oauth2",
        "description": "OAuth 2.0 扩展"
      }
    ]
  }
}
```

**`streaming=true` 含义**：
- Client 可以 SSE 订阅 Task 状态
- 增量接收 Artifact

**`pushNotifications=true` 含义**：
- Server 可以主动调用 Client 的 webhook
- 不需要 Client 轮询

---

## 五、Task 生命周期

### 5.1 Task 状态

```
created → submitted → working → input-required ↔ working
                       ↓
                   completed
                       ↓
                   failed / canceled
```

| 状态 | 含义 |
|---|---|
| `created` | Task 刚创建，未提交 |
| `submitted` | 已提交，等待处理 |
| `working` | 处理中 |
| `input-required` | 需要 Client 补充输入 |
| `completed` | 完成（成功） |
| `failed` | 失败 |
| `canceled` | 取消 |

### 5.2 Task 创建

```http
POST /tasks
Content-Type: application/json
Authorization: Bearer ...

{
  "id": "task-123",
  "sessionId": "session-456",  // 可选：会话 ID
  "message": {
    "role": "user",
    "parts": [
      {
        "type": "text",
        "text": "Analyze the weather in Seattle last month"
      }
    ]
  },
  "metadata": {
    "user_id": "user-789",
    "priority": "high"
  }
}
```

### 5.3 Task 响应

```json
{
  "id": "task-123",
  "status": {
    "state": "working",
    "message": "Researching weather data..."
  },
  "artifacts": []
}
```

### 5.4 Task 轮询

```http
GET /tasks/task-123
→ 返回当前状态
```

### 5.5 Task 完成

```json
{
  "id": "task-123",
  "status": {
    "state": "completed"
  },
  "artifacts": [
    {
      "name": "weather-report",
      "parts": [
        {
          "type": "text",
          "text": "## Weather Analysis for Seattle\n\nLast month..."
        },
        {
          "type": "file",
          "file": {
            "name": "data.csv",
            "mimeType": "text/csv",
            "data": "..."  // base64
          }
        }
      ]
    }
  ]
}
```

### 5.6 流式 Task

```http
POST /tasks/stream
Accept: text/event-stream

→ SSE 流式返回

event: status
data: {"state": "working"}

event: status
data: {"state": "working", "message": "Analyzing..."}

event: artifact
data: {"artifact": {...partial...}}

event: status
data: {"state": "completed"}
```

### 5.7 多轮 Task（input-required）

```
Task 创建 → working → input-required
                            ↓
Client 发送补充输入 → working → completed
```

例子：
```
Task 1: "Book me a flight to Tokyo"
Agent: input-required（"Which date?"）
Task 1 续: "Next Friday"
Agent: working → completed
```

---

## 六、Message 与 Artifact

### 6.1 Message 结构

```json
{
  "role": "user" | "agent",
  "parts": [
    {
      "type": "text",
      "text": "..."
    },
    {
      "type": "file",
      "file": {
        "name": "...",
        "mimeType": "...",
        "data": "..."  // or "uri": "..."
      }
    },
    {
      "type": "data",
      "data": {...}  // 结构化数据
    }
  ]
}
```

### 6.2 Part 类型

| 类型 | 用途 |
|---|---|
| `text` | 文本 |
| `file` | 文件（base64 或 URI） |
| `data` | 结构化数据（JSON 对象） |

### 6.3 Artifact 结构

```json
{
  "name": "report",
  "description": "Final report",
  "parts": [
    {
      "type": "text",
      "text": "..."
    },
    {
      "type": "file",
      "file": {...}
    }
  ],
  "metadata": {
    "generated_at": "2026-06-05T10:00:00Z",
    "model": "gemini-2.0-pro"
  }
}
```

### 6.4 与 OpenAI / Anthropic 消息的对应

| A2A | OpenAI | Anthropic |
|---|---|---|
| `Message.role=user` | `messages[].role=user` | `messages[].role=user` |
| `Message.role=agent` | `messages[].role=assistant` | `messages[].role=assistant` |
| `parts[].type=text` | `content` (str) | `content` (text block) |
| `parts[].type=file` | `content[].image_url/file` | `content[].image/document` |
| `parts[].type=data` | `tool_calls[]` | `tool_use[]` |

---

## 七、通信模式

### 7.1 请求-响应（同步）

```python
# Client 发起 Task
task = await client.send_task(
    agent_url="https://weather-agent.example.com",
    message={...}
)

# Server 同步处理
result = await server.handle_task(task)

# 立即返回 Task（含 Artifact）
return result
```

**适用**：
- 短任务（< 30s）
- 简单查询

### 7.2 轮询（异步）

```python
# Client 发起 Task
task = await client.create_task(agent_url, message)

# 轮询状态
while True:
    status = await client.get_task(agent_url, task.id)
    if status.state in ["completed", "failed", "canceled"]:
        break
    await asyncio.sleep(2)

# 拿到 Artifact
return status.artifacts
```

**适用**：
- 长任务
- 简单实现

### 7.3 流式（SSE）

```python
# Client 订阅流
async for event in client.stream_task(agent_url, message):
    if event.type == "status":
        print(f"Status: {event.data.state}")
    elif event.type == "artifact":
        print(f"Got: {event.data.artifact}")
```

**适用**：
- 长任务 + 实时反馈
- 用户体验好

### 7.4 服务端推送（Webhook）

```python
# Client 注册 webhook
await client.register_webhook(
    agent_url=agent_url,
    task_id=task.id,
    webhook_url="https://my-agent.com/callback"
)

# Server 在 Task 状态变更时主动推
await server.notify_webhook(webhook_url, event)

# Client 的 webhook 接收
@app.post("/callback")
async def callback(event):
    if event.state == "completed":
        result = event.artifacts
        # 处理
```

**适用**：
- 超长任务（小时级）
- 不想保持长连接

### 7.5 各模式对比

| 模式 | 延迟 | 实现复杂度 | 适用 |
|---|---|---|---|
| **请求-响应** | 即时 | 低 | 短任务 |
| **轮询** | 高 | 低 | 长任务 |
| **SSE 流式** | 即时 | 中 | 长任务 + 实时 |
| **Webhook** | 即时 | 高 | 超长任务 |

---

## 八、安全与鉴权

### 8.1 认证方式

```json
{
  "authentication": {
    "schemes": [
      {
        "type": "oauth2",
        "flows": {
          "clientCredentials": {
            "tokenUrl": "https://auth.example.com/token",
            "scopes": {
              "agent:invoke": "Invoke the agent"
            }
          }
        }
      },
      {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key"
      }
    ]
  }
}
```

**支持的方式**：
- `oauth2`（Client Credentials、Authorization Code）
- `apiKey`（Header / Query / Cookie）
- `bearer`（JWT）
- `mtls`（mTLS，未来）

### 8.2 授权

**粒度**：
- Agent 级别（能否调用该 Agent）
- Skill 级别（能否用该技能）
- 资源级别（每次调用的 quota）

**示例**：
```python
# Token 包含权限
{
  "sub": "service-account-1",
  "aud": "weather-agent",
  "scope": "agent:invoke weather:read",
  "exp": 1700000000
}
```

### 8.3 传输安全

```
强制要求：
- HTTPS（生产环境）
- TLS 1.2+ 最低
- 现代密码学套件
```

### 8.4 数据安全

| 风险 | 应对 |
|---|---|
| **数据外泄** | E2E 加密、字段级脱敏 |
| **PII 泄露** | 传输前脱敏 |
| **响应投毒** | 签名验证 |
| **中间人** | mTLS |

### 8.5 审计与可观测

```python
# 每次 A2A 调用记录
audit_log.info("a2a_call", extra={
    "caller_agent": "orchestrator",
    "callee_agent": "weather-agent",
    "task_id": task.id,
    "skill": "weather-research",
    "input_tokens": 200,
    "output_tokens": 1500,
    "cost_usd": 0.05,
    "duration_ms": 5000,
    "status": "completed"
})
```

---

## 九、实现参考

### 9.1 Python Server

```python
from a2a import A2AServer, AgentCard, Skill, Task

agent_card = AgentCard(
    name="Weather Research Agent",
    description="Analyzes weather data",
    url="https://weather-agent.example.com",
    version="1.0.0",
    skills=[
        Skill(
            id="weather-research",
            name="Weather Research",
            description="Deep research on weather",
            tags=["weather", "research"],
            examples=["Analyze rainfall patterns"]
        )
    ]
)

server = A2AServer(agent_card=agent_card)

@server.handler("weather-research")
async def handle_weather_research(task: Task) -> Task:
    # 解析输入
    user_query = task.message.parts[0].text
    
    # 内部处理
    result = await do_research(user_query)
    
    # 构造 Artifact
    task.artifacts.append({
        "name": "weather-report",
        "parts": [{"type": "text", "text": result}]
    })
    task.status.state = "completed"
    return task

# 启动
import uvicorn
uvicorn.run(server.app, host="0.0.0.0", port=8000)
```

### 9.2 Python Client

```python
from a2a import A2AClient

client = A2AClient()

# 1. 发现 Agent
agent_card = await client.discover("https://weather-agent.example.com")
print(f"Found: {agent_card.name}")
print(f"Skills: {[s.id for s in agent_card.skills]}")

# 2. 发起 Task
task = await client.create_task(
    agent_url=agent_card.url,
    message={
        "role": "user",
        "parts": [{"type": "text", "text": "Analyze Seattle weather"}]
    }
)

# 3. 等待完成
final_task = await client.wait_for_completion(
    agent_url=agent_card.url,
    task_id=task.id,
    timeout=300
)

# 4. 获取结果
for artifact in final_task.artifacts:
    for part in artifact.parts:
        print(part.text)
```

### 9.3 流式订阅

```python
async with client.stream_task(agent_url, message) as stream:
    async for event in stream:
        if event.type == "status":
            print(f"Status: {event.state}")
        elif event.type == "artifact":
            print(f"Partial: {event.artifact}")
        elif event.type == "error":
            print(f"Error: {event.error}")
```

---

## 十、A2A 与多 Agent 框架对比

### 10.1 对比维度

| 维度 | A2A | LangGraph | AutoGen | CrewAI |
|---|---|---|---|---|
| **定位** | 协议 | 框架 | 框架 | 框架 |
| **跨平台** | ✅ | ❌ | ❌ | ❌ |
| **Agent 发现** | Agent Card | 代码 | 代码 | 代码 |
| **状态** | Task 状态机 | Graph | Chat history | Task 状态 |
| **厂商** | Google | LangChain | Microsoft | CrewAI |
| **成熟度** | 早期 | 成熟 | 成熟 | 早期 |

### 10.2 何时用 A2A

- 跨组织、跨厂商 Agent 协作
- Agent 市场 / 目录
- 多云混合
- 长期投资的协议标准

### 10.3 何时用框架

- 内部应用、单组织
- 快速迭代
- 框架功能够用

### 10.4 混合

```
外部 Agent 协作 → A2A
内部 Agent 编排 → LangGraph / AutoGen
```

---

## 十一、AI 网关与 A2A 集成

### 11.1 网关的核心角色

```
[LLM App]
    ↓
[A2A Gateway]   ← 统一管理 A2A 流量
    ↓
[Agent A] [Agent B] [Agent C]
```

**网关职责**：
- Agent 注册 / 发现（代理 Agent Card）
- 任务路由
- 鉴权（OAuth token 代理）
- 限流
- 计费
- 审计
- 缓存
- 协议转换

### 11.2 实现示例

```python
class A2AGateway:
    def __init__(self, config):
        self.agents = {}  # agent_id → agent_card
        self.task_history = []
        self.rate_limiter = RateLimiter()
        self.cache = {}
    
    async def register_agent(self, agent_url):
        """通过代理访问 Agent Card"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{agent_url}/.well-known/agent.json")
            agent_card = resp.json()
        agent_id = self._generate_id(agent_card)
        self.agents[agent_id] = agent_card
        return agent_id
    
    async def list_agents(self, skill=None, tags=None):
        """按 skill / tag 过滤"""
        results = []
        for agent_id, card in self.agents.items():
            if self._matches(card, skill, tags):
                results.append(card)
        return results
    
    async def create_task(self, agent_id, message, user_context):
        # 1. 鉴权
        if not self._authorize(user_context, agent_id):
            raise PermissionError()
        
        # 2. 限流
        if not self.rate_limiter.allow(user_context["user_id"], agent_id):
            raise RateLimitError()
        
        # 3. 路由
        agent_card = self.agents[agent_id]
        agent_url = agent_card["url"]
        
        # 4. 注入网关身份
        headers = self._build_headers(user_context, agent_id)
        
        # 5. 转发
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{agent_url}/tasks",
                json=message,
                headers=headers
            )
        
        # 6. 审计
        self.task_history.append({
            "user_id": user_context["user_id"],
            "agent_id": agent_id,
            "task": message,
            "timestamp": time.time()
        })
        
        return resp.json()
```

### 11.3 Agent 路由

```python
class SmartAgentRouter:
    """根据用户 query 选最合适的 Agent"""
    
    def __init__(self, gateway):
        self.gateway = gateway
        self.llm = OpenAI()
    
    async def route(self, user_query, user_context):
        # 1. 获取候选 Agent
        candidates = await self.gateway.list_agents()
        
        # 2. 用 LLM 选最佳 Agent
        agent_summaries = [
            {
                "id": a["url"],
                "name": a["name"],
                "description": a["description"],
                "skills": [s["name"] for s in a["skills"]]
            }
            for a in candidates
        ]
        
        prompt = f"""Given the user query and available agents, choose the best agent.

User query: {user_query}

Available agents:
{json.dumps(agent_summaries, indent=2)}

Respond with the agent id."""

        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        chosen_id = json.loads(response.choices[0].message.content)["agent_id"]
        
        # 3. 路由
        return await self.gateway.create_task(
            agent_id=chosen_id,
            message={"role": "user", "parts": [{"type": "text", "text": user_query}]},
            user_context=user_context
        )
```

### 11.4 网关 vs Agent Registry

| 维度 | 网关 | Registry |
|---|---|---|
| **职责** | 流量管理 | 目录服务 |
| **转发** | ✅ | ❌ |
| **鉴权** | ✅ | 可选 |
| **限流** | ✅ | ❌ |
| **发现** | 可对接 | ✅ |
| **缓存** | ✅ | 可选 |
| **审计** | ✅ | ❌ |

**最佳实践**：网关 + Registry 配合。

---

## 十二、A2A 生态与未来

### 12.1 当前生态

| 角色 | 状态 |
|---|---|
| **协议规范** | v0.x，2025 发布 |
| **参考实现** | Google 提供 Python/TS SDK |
| **Agent 平台** | 早期支持（Google ADK、LangGraph） |
| **第三方** | 探索中 |

### 12.2 生态发展时间线

```
2025 Q1: A2A 协议发布
2025 Q2: Google ADK 支持
2025 Q3: 早期实验
2025 Q4: 更多平台支持
2026:    标准化、治理
2027:    主流 Agent 平台默认支持
```

### 12.3 竞争协议

| 协议 | 推方 | 定位 |
|---|---|---|
| **A2A** | Google | Agent ↔ Agent |
| **MCP** | Anthropic | Agent ↔ 工具 |
| **ANP** | 社区 | Agent Network Protocol |
| **Agent Protocol** | LangChain | Agent 通信 |
| **OpenAI Swarm** | OpenAI | 多 Agent 编排 |
| **AG2 / AGUI** | 社区 | Agent UI |

**胜出关键**：
- 标准成熟度
- 大厂背书
- 生态广度
- 治理结构

### 12.4 治理的可能演化

| 阶段 | 治理 |
|---|---|
| **当前** | Google 主推 |
| **中期** | 厂商 + 社区工作组 |
| **长期** | Linux Foundation / CNCF |

### 12.5 未来形态

- **Agent 互联网**：A2A 让 Agent 形成网络
- **Agent 市场**：像 App Store 一样卖 Agent
- **跨组织工作流**：A2A + MCP 形成标准栈
- **AI 经济**：Agent 雇佣 Agent，A2A 是支付和通信协议

---

## 十三、未解难题与研究前沿

### 13.1 协议

1. **A2A 与 MCP 的边界**是否会融合？
2. **A2A 的 v1.0**什么时候稳定？
3. **二进制 A2A 协议**的可行性
4. **A2A over gRPC**的探索
5. **A2A 与 HTTP/3**的结合

### 13.2 性能

6. **大规模 A2A 部署**的性能
7. **SSE vs WebSocket**的最优选择
8. **Agent 调用的延迟优化**
9. **A2A + MCP 联合延迟**的控制
10. **流式 A2A**的协议细节

### 13.3 安全

11. **跨组织 A2A** 的鉴权标准
12. **Agent 间的信任链**
13. **A2A 流量的加密**（端到端）
14. **恶意 Agent** 的检测
15. **A2A 审计** 的合规框架

### 13.4 生态

16. **A2A 注册中心** 的标准
17. **Agent 评分**机制
18. **Agent SLA** 标准化
19. **A2A + MCP** 的统一治理
20. **跨云 A2A** 的实现

### 13.5 网关

21. **A2A 网关** 的标准化
22. **A2A 路由算法**
23. **A2A 流量与 LLM 流量**的整合
24. **A2A 计费**模型
25. **A2A 可观测** 标准

### 13.6 未来形态

26. **Agent 互联网** 的实现路径
27. **Agent 经济** 的基础设施
28. **A2A + 区块链** 的去中心化信任
29. **A2A 与 AI 安全法规** 的结合
30. **A2A 的最终形态**是什么

---

## 十四、参考资料

### 14.1 官方

- google.github.io/A2A
- github.com/google/A2A
- github.com/google-a2a/a2a-python
- github.com/google-a2a/a2a-js

### 14.2 规范

- A2A Protocol Specification
- JSON-RPC 2.0（基础）

### 14.3 关键博客

- Google "Announcing A2A"
- Google "A2A: A new standard"
- LangChain "A2A 集成"
- Anthropic "A2A vs MCP"

### 14.4 相关协议

- modelcontextprotocol.io（MCP）
- agentprotocol.ai（LangChain）
- ag2-protocol.org（社区）

### 14.5 实现参考

- Google Agent Development Kit (ADK)
- LangGraph
- AutoGen
- CrewAI

### 14.6 评测 / 案例

- 早期案例仍在积累
- Google 内部案例
- 部分企业 PoC

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 批 · 第 2 篇
- 主题：A2A 协议与多 Agent 互联
- 上一份：11-mcp-deep-dive.md
- 下一份预告：AI 网关的成本经济学
