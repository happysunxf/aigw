# LLM API 协议深入研究

> 系列：AI Gateway 持续深挖 · 第 1 篇
> 性质：纯技术研究
> 范围：当前主流 LLM API 协议的内部结构、互操作、标准之争

---

## 目录

- [一、为什么协议是 AI Gateway 的"第一性问题"](#一为什么协议是-ai-gateway-的第一性问题)
- [二、OpenAI Chat Completions 协议解剖](#二openai-chat-completions-协议解剖)
- [三、Anthropic Messages 协议解剖](#三anthropic-messages-协议解剖)
- [四、Google Gemini 协议解剖](#四google-gemini-协议解剖)
- [五、OpenAI Responses API：新事实标准的尝试](#五openai-responses-api新事实标准的尝试)
- [六、MCP（Model Context Protocol）深入](#六mcpmodel-context-protocol深入)
- [七、A2A（Agent-to-Agent）协议深入](#七a2aagent-to-agent协议深入)
- [八、协议翻译工程实践](#八协议翻译工程实践)
- [九、协议层演进趋势](#九协议层演进趋势)
- [十、未解难题与研究前沿](#十未解难题与研究前沿)
- [十一、参考资料](#十一参考资料)

---

## 一、为什么协议是 AI Gateway 的"第一性问题"

### 1.1 协议即"接口契约"

AI Gateway 的核心职责之一是**协议翻译**——把所有上游 API 统一成一种（或几种）下游协议。这意味着：

- Gateway **必须懂所有上游协议**的字段、语义、流式行为
- Gateway **必须选择一种下游协议**作为对外契约
- 一旦选错，迁移成本巨大

### 1.2 当前协议格局的三个观察

1. **OpenAI Chat Completions 是事实标准**——大多数客户端 SDK 围绕它设计
2. **Anthropic Messages 是第二大生态**——结构差异最大，翻译成本最高
3. **MCP（Anthropic 推）和 A2A（Google 推）正在成为新标准**——但都还在早期

### 1.3 协议层的"四个翻译维度"

| 维度 | 含义 | 难度 |
|---|---|---|
| **请求结构** | 字段映射、嵌套结构 | ★★ |
| **流式语义** | chunk 边界、增量字段、终止信号 | ★★★★ |
| **工具调用** | tool_calls / tool_use / function_call 命名与结构差异 | ★★★★ |
| **结构化输出** | JSON Schema / grammar / response_format 差异 | ★★★ |

---

## 二、OpenAI Chat Completions 协议解剖

### 2.1 核心字段

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
    {"role": "user", "content": "How are you?"}
  ],
  "temperature": 1.0,
  "top_p": 1.0,
  "max_tokens": 1000,
  "stream": false,
  "tools": [...],
  "tool_choice": "auto",
  "response_format": {...},
  "stop": null,
  "presence_penalty": 0,
  "frequency_penalty": 0,
  "user": "user-123",
  "seed": 42,
  "logit_bias": {...}
}
```

### 2.2 响应（非流式）

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "gpt-4o-2024-08-06",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'm doing well, thanks!",
        "tool_calls": [...]
      },
      "finish_reason": "stop",
      "logprobs": null
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  },
  "system_fingerprint": "fp_xxx"
}
```

### 2.3 流式响应（SSE）

```
data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1700000000,"model":"gpt-4o","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1700000000,"model":"gpt-4o","choices":[{"index":0,"delta":{"content":"I"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1700000000,"model":"gpt-4o","choices":[{"index":0,"delta":{"content":"'m"},"finish_reason":null}]}

...

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1700000000,"model":"gpt-4o","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### 2.4 关键设计点

| 设计 | 含义 | 工程影响 |
|---|---|---|
| **messages 数组** | 全量历史（无状态） | 网关必须管理上下文窗口 |
| **stream=true 时返回 SSE** | 增量 token 推送 | 网关需要 chunk-by-chunk 透传 |
| **finish_reason 字段** | 终止原因枚举 | 网关可据此判定是否计费完整 |
| **usage 只在非流式返回** | 流式结束时不返回 token 统计 | 网关必须自己计算（tokenizer 算） |
| **tool_calls 结构** | 结构化工具调用 | 比纯文本提示词可靠 |
| **response_format** | JSON Schema / json_object | 强制结构化输出 |

### 2.5 协议陷阱

- **`system_fingerprint` 是 OpenAI 专属**，其他厂商没有
- **`logit_bias` 是 OpenAI 专属**
- **`seed` 用于可复现**，但只有 OpenAI / 少数厂商支持
- **`user` 字段用于滥用检测**，不是稳定的用户 ID 字段
- **finish_reason 枚举值各厂商不一致**（"stop" / "end_turn" / "STOP"）

---

## 三、Anthropic Messages 协议解剖

### 3.1 核心差异：system 不是 message

Anthropic 的 messages 数组**不含 system 角色**——system 是独立顶级字段：

```json
{
  "model": "claude-sonnet-4-5",
  "system": "You are a helpful assistant.",
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"},
    {"role": "user", "content": "How are you?"}
  ],
  "max_tokens": 1024,
  "temperature": 1.0,
  "stream": false,
  "tools": [...],
  "tool_choice": {"type": "auto"}
}
```

### 3.2 content 是数组而不是字符串

Anthropic 用结构化 content block 数组：

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What's in this image?"},
    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
  ]
}
```

这是 Anthropic 协议的核心特征——**多模态原生**。

### 3.3 工具调用

Anthropic 的工具调用和结果在 messages 里有专门 role：

```json
// 助手调用工具
{"role": "assistant", "content": [
  {"type": "tool_use", "id": "toolu_xxx", "name": "get_weather", "input": {"city": "SF"}}
]}

// 工具返回结果
{"role": "user", "content": [
  {"type": "tool_result", "tool_use_id": "toolu_xxx", "content": "72°F sunny"}
]}
```

注意：Anthropic 用 `tool_use` / `tool_result` 而不是 `tool_calls`，而且**工具结果是 user 角色的 content block**，不是独立的 tool 消息。

### 3.4 流式事件类型（不止 SSE）

Anthropic 的流式响应有**多种事件类型**：

```
event: message_start
data: {"type":"message_start","message":{...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: ping
data: {"type":"ping"}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"output_tokens":15}}

event: message_stop
data: {"type":"message_stop"}
```

**关键差异**：
- 不用 `data: [DONE]` 终止
- 用 `event: <type>` + `data:` 复合结构
- 有专门的 `ping` 事件（保持连接）
- content_block 是原子单位，可包含 text / tool_use / image

### 3.5 Prompt Caching（Anthropic 独有）

```json
{
  "system": [
    {
      "type": "text",
      "text": "You are a helpful assistant.",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [...]
}
```

`cache_control` 字段让 Anthropic 服务端缓存指定 prefix——**比 gateway 层语义缓存更原生**。

### 3.6 协议翻译挑战

| OpenAI 字段 | → Anthropic 字段 | 难度 |
|---|---|---|
| `messages[].role=system` | 提升为顶级 `system` 字段 | ★★ |
| `messages[].content` (str) | 包装为 `[{"type":"text","text":...}]` | ★ |
| `tools[].function` 嵌套 | 扁平化 | ★★ |
| `tool_calls[].function.arguments` | `input` 字段 | ★ |
| 工具结果 role=tool | 包装为 user 的 `tool_result` block | ★★★ |
| `max_tokens` | 必需（Anthropic 必填，OpenAI 可选） | ★ |
| `finish_reason="tool_calls"` | `stop_reason="tool_use"` | ★ |
| 流式 `[DONE]` 终止 | `message_stop` 事件 | ★★ |

---

## 四、Google Gemini 协议解剖

### 4.1 完全不同的结构

```json
{
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "Hello"}]
    },
    {
      "role": "model",
      "parts": [{"text": "Hi there!"}]
    }
  ],
  "systemInstruction": {
    "role": "system",
    "parts": [{"text": "You are a helpful assistant."}]
  },
  "generationConfig": {
    "temperature": 1.0,
    "topP": 0.95,
    "maxOutputTokens": 1000,
    "responseMimeType": "application/json"
  },
  "tools": [...]
}
```

### 4.2 关键差异

| 维度 | OpenAI | Gemini |
|---|---|---|
| 消息容器 | `messages` | `contents` |
| 角色名 | `assistant` | `model` |
| System 字段 | message[0] | 顶级 `systemInstruction` |
| 内容结构 | string 或 array | 永远是 `parts[]` 数组 |
| 工具调用 | `tool_calls[].function` | `functionCall` |
| 配置 | 顶级字段 | `generationConfig` 嵌套 |
| 多模态 | content 数组 | parts 数组 |

### 4.3 安全设置（Gemini 独有）

```json
{
  "safetySettings": [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
  ]
}
```

Gemini 把安全设置做成顶级字段——**是协议级的 Guardrails**。

---

## 五、OpenAI Responses API：新事实标准的尝试

### 5.1 是什么

OpenAI 在 2025 年推出 Responses API，目标是**统一 Chat Completions 和 Assistants API**，为多步 Agent 调用提供更原生的支持。

### 5.2 核心新特性

```json
{
  "model": "gpt-4o",
  "input": "Hello",
  "instructions": "You are a helpful assistant.",
  "tools": [...],
  "previous_response_id": "resp_xxx",
  "truncation": "auto",
  "store": true
}
```

| 新特性 | 含义 |
|---|---|
| **`input` 简化** | 不再是 messages 数组，可以是字符串或 input_item 数组 |
| **`previous_response_id`** | 服务端管理上下文，前端不需要维护 messages |
| **`store` 字段** | 是否把这次响应存入 OpenAI 服务端（用于将来检索） |
| **`truncation: "auto"`** | 服务端自动截断超长上下文 |
| **内置工具** | `web_search` / `file_search` / `code_interpreter` / `image_generation` 作为一等公民 |

### 5.3 对 AI Gateway 的影响

- **如果 Responses API 成事实标准**——所有网关都要支持新协议
- **如果 Chat Completions 继续主流**——网关可以暂时不跟进
- **OpenAI 的双协议策略**——故意分裂生态，强制生态跟随

---

## 六、MCP（Model Context Protocol）深入

### 6.1 是什么

MCP 是 Anthropic 在 2024 年底推出的**工具调用标准化协议**，目标是**统一 LLM 与外部工具/数据源的连接方式**。

类比：MCP 之于 LLM 工具调用 ≈ LSP 之于编辑器插件。

### 6.2 架构

```
┌──────────────┐                  ┌──────────────┐
│ LLM Client   │ ◀── JSON-RPC ──▶ │  MCP Server  │
│ (Claude,etc) │                  │ (Tools, Data)│
└──────────────┘                  └──────────────┘
        │                                  │
        │             MCP 协议              │
        └──────────────────────────────────┘
```

### 6.3 三个核心原语

| 原语 | 含义 | 类比 |
|---|---|---|
| **Tools** | LLM 可调用的函数 | OpenAI 的 function calling |
| **Resources** | LLM 可读取的数据 | 类似于 RAG 文档 |
| **Prompts** | 预定义的 prompt 模板 | 模板库 |

### 6.4 通信机制

- **stdio**（本地进程间）
- **HTTP + SSE**（网络）
- **JSON-RPC 2.0** 消息格式

### 6.5 MCP 与传统 Function Calling 的差异

| 维度 | 传统 Function Calling | MCP |
|---|---|---|
| 工具定义 | 每次请求都发 | 启动时 discovery（`tools/list`） |
| 工具状态 | 无状态 | 持久连接，可订阅 |
| 协议 | HTTP 内的 JSON | 独立协议层 |
| 多客户端 | 各自实现 | 一份 MCP server 多客户端 |
| 工具市场 | 无 | 正在形成 |

### 6.6 对 AI Gateway 的影响

- **MCP 客户端/服务端代理**可能成为网关的新职责
- **MCP server 注册中心** = 网关的"插件市场"
- **MCP 工具调用审计** = 网关的可观测增强点

---

## 七、A2A（Agent-to-Agent）协议深入

### 7.1 是什么

Google 在 2025 年推的 Agent 通信协议。目标：让不同厂商的 Agent **跨平台通信**。

### 7.2 核心概念

| 概念 | 含义 |
|---|---|
| **Agent Card** | Agent 自我介绍（能力、URL、认证） |
| **Task** | Agent 间的工作单元（同步/异步/流式） |
| **Artifact** | Task 产生的输出 |
| **Message** | Task 内的通信单元（role + parts） |
| **Part** | Message 的内容块（text / file / data） |

### 7.3 协议流程

```
1. Agent A 发送 Agent Card 给 Agent B
2. Agent B 解析能力
3. Agent A 发起 Task："请翻译这个文档"
4. Agent B 返回 task id + status
5. Agent A 轮询 / 订阅 Task 状态
6. Agent B 完成，返回 Artifact
```

### 7.4 与 MCP 的关系

| 维度 | MCP | A2A |
|---|---|---|
| 层级 | LLM ↔ 工具/数据 | Agent ↔ Agent |
| 通信对象 | 工具（无智能） | Agent（有智能） |
| 协议 | JSON-RPC | HTTP + SSE / WebSocket |
| 推方 | Anthropic | Google |

两者**正交**：Agent 内部用 MCP 调工具，Agent 之间用 A2A 通信。

### 7.5 对 AI Gateway 的影响

- **Agent 流量代理**——A2A 流量将走 AI Gateway
- **Agent 发现 / 注册**——类似服务注册中心
- **跨 Agent 鉴权**——OAuth / JWT for Agents
- **Agent 间计费**——A2A 调用链的成本归因

---

## 八、协议翻译工程实践

### 8.1 翻译器架构

```
请求:  OpenAI 协议
       ↓
[ 协议解析器 ] ── 解析为内部 IR
       ↓
[ 内部中间表示 (IR) ]
   {
     model: str,
     messages: [{role, content_blocks: [...]}],
     tools: [{name, description, schema}],
     config: {temperature, max_tokens, stream, ...}
   }
       ↓
[ 协议生成器 ] ── 翻译为 Anthropic/Gemini/OpenAI
       ↓
请求:  Anthropic 协议
```

### 8.2 关键设计原则

1. **IR 必须语义完整**——能表达所有上游协议
2. **IR 内部统一**——不偏袒任何厂商
3. **翻译器只做"无损翻译"**——不做业务逻辑
4. **流式 chunk 也要走 IR**——不能只为非流式做翻译

### 8.3 翻译中的"信息丢失"问题

| 翻译方向 | 可能丢失 |
|---|---|
| OpenAI → Anthropic | `logit_bias`、`seed` |
| OpenAI → Gemini | `logit_bias`、`presence_penalty` |
| Anthropic → OpenAI | `cache_control`（需要网关模拟） |
| Gemini → OpenAI | `safetySettings`（需要网关做 Guardrails） |
| 任意 → Responses | `previous_response_id` 状态 |

**好的网关应该警告用户哪些字段无法翻译。**

### 8.4 流式翻译的难点

- **chunk 边界不对齐**——Anthropic 的 content_block_start 对应 OpenAI 的首个 content chunk
- **增量字段差异**——Anthropic 有 `input_json_delta` 增量 JSON，OpenAI 一次性给完整 arguments
- **终止信号**——OpenAI `data: [DONE]` vs Anthropic `message_stop` vs Gemini 的 `candidates[].finishReason`
- **错误处理**——Anthropic 错误事件用 `event: error` 而非 HTTP 4xx/5xx

---

## 九、协议层演进趋势

### 9.1 短期（1-2 年）

- **OpenAI Responses API 与 Chat Completions 并存**——OpenAI 不会快速淘汰后者
- **MCP 工具生态快速扩张**——会出现 MCP server 市场和注册中心
- **A2A 早期实验**——Google 主导，跨厂商支持待观察
- **国产模型协议收敛**——国内厂商基本都做 OpenAI 兼容

### 9.2 中期（3-5 年）

- **可能形成新事实标准**——目前 OpenAI 协议是"老标准"，可能由 MCP/A2A 派生新标准
- **多模态协议统一**——图像/音频/视频字段在不同协议中表达不一致
- **Agent 协议成熟**——A2A 或其继任者
- **结构化输出协议**——JSON Schema / Grammar / Tool Use 三种范式收敛

### 9.3 长期（5+ 年，未知）

- **协议本身被 LLM 生成**——未来模型自己适配协议，固定协议变得不重要
- **语义级协议**——不是字段级，而是意图级
- **联邦协议**——跨组织、跨云的协议层

---

## 十、未解难题与研究前沿

### 10.1 协议设计层

1. **是否存在"理想"的 LLM API 协议？**——还是必然要分场景
2. **状态管理应该放在哪？**——OpenAI 放服务端（Responses），Anthropic 放客户端（messages）
3. **工具调用应该独立协议（MCP）还是 HTTP 内嵌？**
4. **结构化输出是 JSON Schema / Grammar / CFG 哪个胜出？**

### 10.2 互操作层

5. **OpenAI 协议 → 其他协议的"信息丢失"如何量化？**
6. **跨协议流式 chunk 边界对齐的标准化方法？**
7. **多模态协议能否统一？**（文本/图像/音频/视频）
8. **错误码在跨协议翻译时如何映射？**

### 10.3 标准化层

9. **MCP 能否像 LSP 一样成为工具调用事实标准？**
10. **A2A 与 MCP 的边界**——会不会合流？
11. **是否需要"协议测试套件"**——类似 HTTP 的一致性测试？
12. **Responses API 能否替代 Chat Completions？**

### 10.4 安全 / 隐私层

13. **协议级 Guardrails（Gemini safetySettings）能否成为标准？**
14. **协议层加密**——PII 字段端到端加密？
15. **协议层的访问控制**——按字段级权限？

### 10.5 经济层

16. **协议层成本标记**——每个字段的"token 成本"应在协议中可见？
17. **协议层的成本优化原语**——"这段上下文可缓存"应在协议中表达？

---

## 十一、参考资料

### 11.1 协议官方文档

- platform.openai.com/docs/api-reference/chat
- platform.openai.com/docs/api-reference/responses
- docs.anthropic.com/en/api/messages
- ai.google.dev/api/generate-content
- modelcontextprotocol.io
- google.github.io/A2A

### 11.2 推荐阅读

- Anthropic "Introducing the Model Context Protocol"
- OpenAI "New Responses API" 公告
- Google "Agent2Agent Protocol" 白皮书
- LangChain "MCP vs Function Calling" 对比文
- a16z "The AI Gateway Stack" 中关于协议的章节

### 11.3 仓库

- github.com/modelcontextprotocol/python-sdk
- github.com/modelcontextprotocol/typescript-sdk
- github.com/google/A2A
- github.com/BerriAI/litellm（协议翻译典范）

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 1 篇
- 主题：LLM API 协议深入
- 下一份预告：语义缓存实现原理与调优实战
