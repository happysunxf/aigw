# AI 网关深挖 · Agent Gateway 专题（round 24）

> **轮值时间**：2026-06-07 02:30 CST · **窗口期**：过去 2.5h（06-06 23:55 ~ 06-07 02:30 CST，对应 UTC 06-06 15:55 ~ 06-07 18:30）
> **主角**：agentgateway（#2112 OTEL attribute limit + #1850 MCP prompts/mux 二次接力）
> **AIGW 落点**：本期新增 2 条硬要求 → 累加 **AG-42 ~ AG-43**

## TL;DR

r23（23:01 CST）之后 2.5h，agentgateway 仓库**仅 1 条新 PR 合入或开放**（#2112 17:32 UTC 开放，未合入），其余 5 条均已**在 r23 之前落地**——这是 agentgateway 进入"密集合入后短暂静默期"的典型节奏。但**窗口期内仍有 2 个关键信号**：(1) **PR #2112（fix telemetry · OTEL attribute limit）**——首条**正式承认"agent 多轮 trace 后段被截断"是 OTEL 128 attribute 上限**的 PR，并加 `dropped_attributes_count` 透明披露；(2) **Issue #1850 第 5 楼（rohitg00 06-06 18:22 认领）**——MCP prompts/resources 的 `*_listChanged` 能力补全正式启动，**multiplexing 模式下"mux 后能力完整性"问题**进入收尾。**跨厂商**：LiteLLM 06-06 18:06 开放 **#29846 `litellm-proxy claude-code` CLI wrapper**——首次把"Claude Code 透明走 LiteLLM proxy"做成一条命令（清 `ANTHROPIC_API_KEY`、注入 `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`），与 agentgateway #2111 server-side tool interception 形成"两条独立路径做同一件事"的对照。

## 1. 窗口期（15:55 ~ 18:30 UTC 06-06）新动态

### 1.1 [PR #2112] fix(telemetry): support OTEL attribute count limit

**作者** abhinavgautam01（06-06 17:32 开，17:40 二次 commit `cache OTEL attribute limit`），**仍未合入**（21:00 UTC 后无 review 活动），**+110/-9，单文件** `crates/agentgateway/src/telemetry/trc.rs`。**Fixes #2060**（MarkYQJ 06-04 04:26 开）。

**痛点（#2060 原话）**："For an AI Agent traces with many turns, the later turns are dropped after some threshold. It looks like `gen_ai.prompt.42.content`...`gen_ai.prompt.48.content`. Then it is always stopped at `gen_ai.prompt.48.content`. Is this limited by `OTEL_ATTRIBUTE_COUNT_LIMIT`（which is default 128）?"

**根因**：agentgateway **手动构造** `SpanData`（access-log trace 路径），SDK 内部 span limit **不会**应用于这些手工 span，导致"SDK 走 128 默认，但 access-log span 不受 128 限制 / 也不受用户 env 覆盖"。**行为不一致**是问题核心。

**修复细节**（patch 直引）：
- 新增 `OTEL_ATTRIBUTE_COUNT_LIMIT` + `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT` 两个常量，`OnceCell` 缓存解析结果
- `apply_span_attribute_limit` 把超限属性截断，**同时**回填 `SpanData.dropped_attributes_count`（u32）
- **优先级**：`OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`（span 特定）> `OTEL_ATTRIBUTE_COUNT_LIMIT`（SDK 通用）> 默认无限
- `build_tracer_provider` 一并把 limit 透传给 SDK（`with_max_attributes_per_span`），**手工 span 与 SDK span 行为对齐**
- 三组 unit test：`attribute_limit`、`span_attribute_count_limit`、`truncation behavior`

**AIGW 落点 AG-42**：**多 agent 长链路 trace 必须配置 `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`**（建议 ≥512），且所有手工构造 span 的组件必须**显式回填 `dropped_attributes_count`**——这是 trace 完整性与成本归因的**审计硬要求**。

### 1.2 [Issue #1850 第 5 楼] MCP prompts/resources `*_listChanged` 接力认领

**作者** ivanhavasi 05-18 12:54 开，**rohitg00 06-06 18:22 认领**（"I'll take this one. I'll wire up `enable_prompts_list_changed` and `enable_resources_list_changed` so they work, then enable them. Planning to skip a new issue since this thread already covers it, and keep the PR small. Will open it once it's ready."）。

**完整讨论链**：
- 05-18 12:54 ivanhavasi：mux 模式下 `initialize` 响应**漏 `prompts` capability**，手调 `prompts/list` 返空数组，`prompts/get` 返 500（`JSON-RPC error -32603: failed to send message: invalid resource name`）
- 06-04 17:27 rohitg00 主动请缨
- 06-04 17:40 howardjohn 回复："this one actually may be completed and just forgot to close out this issue"，**指向 `crates/agentgateway/src/mcp/handler.rs:609`**（commit `5823d7b1`）——所以 prompts mux 主体已修，但 `*_listChanged` **能力通告**（订阅机制）未开
- 06-05 16:45 howardjohn 给新方向："make sure `enable_prompts_list_changed` and `enable_resources_list_changed` can work, and then enable them"
- 06-06 18:22 rohitg00 确认认领

**MCP 协议关键点**：`listChanged: true` 通告告诉客户端"该能力（prompts/resources）的列表会动态变化，订阅 `notifications/*/list_changed` 即可获得更新"——mux 模式下，**任一后端** server 推送 `list_changed` 通知，gateway 必须**统一聚合 + 透明转发**到所有订阅客户端，**且 fan-out 时机不能 race**。

**AIGW 落点 AG-43**：mux 模式下 **`*_listChanged` 必须三个全开**（prompts/resources/tools），且**任一后端 list_changed → 全部订阅客户端**；`tools.listChanged` 已在 r22 (#2077) 合入，本次补 prompts/resources。

### 1.3 跨厂商对照 · LiteLLM #29846 `litellm-proxy claude-code`

**作者** mateo-berri（BerriAI），06-06 17:56 开 DRAFT，18:06 最后 update，**+382/-0，5 文件**。**与 agentgateway #2111 是同期双胞胎**——两条不同路径达成"让 Claude Code 走代理网关"。

**实现**（body 直引 + 截图）：
```bash
# 1. 启动 proxy
python litellm/proxy/proxy_cli.py --config litellm/proxy/dev_config.yaml ...

# 2. CLI 登录（浏览器 SSO）
litellm-proxy login

# 3. 启动 Claude Code（透明走 proxy）
litellm-proxy claude-code
```

**env 注入细节**（验证用 fake `claude` 实测）：
| 环境变量 | 注入值 | 作用 |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `http://localhost:4000` | 强制走 proxy |
| `ANTHROPIC_AUTH_TOKEN` | `sk-litellm-demo-123` | proxy key |
| `ANTHROPIC_MODEL` | `--model` 传入值 | 模型映射 |
| `ANTHROPIC_API_KEY` | **强制清空** | 防止用户环境里漏 key 绕开 proxy |
| `--` 后续参数 | 原样透传 `claude` | 透传 Claude Code 子命令 |

**与 agentgateway #2111 对照**：
- **#2111（agentgateway）**：**运行时拦截** + **MCP 工具注入**——agent gateway 改 server-side tool call payload，对 model 透明
- **#29846（LiteLLM）**：**启动时改 env** + **CLI wrapper**——在 Claude Code 启动前 env 替换，对 Claude Code 进程透明
- **两条路径目标一致**：让 Claude Code **可走任何 backend**（vLLM / SGLang / OpenRouter / 任意 proxy）
- **互补性**：LiteLLM wrapper 走 `ANTHROPIC_*` env 改向（Claude Code → Anthropic-compatible API）；agentgateway 走 MCP injection（Claude Code → 自定义 tool calling）。**两种 user model 都要支持**。

**AIGW 落点补充**：**AG-41 现需明确两条子路径**——AG-41.a LiteLLM-style（env wrapper，agent 不感知）；AG-41.b agentgateway-style（payload 注入 + MCP 转 tool call，model 透明）。

## 2. 24h 累计推进表（r23 → r24）

| 类别 | 数量 | 代表 PR/Issue | 状态变化 |
|---|---|---|---|
| OAuth/身份 | 1 | #2088 ID-JAG | r23 报告，本期无更新 |
| OIDC 浏览器 | 1 | #1450（8258 行） | r23 报告，本期无更新 |
| MCP ext_authz | 1 | #1842 ExtMCP | r23 报告，本期无更新 |
| Proxy timing | 1 | #1784 | r23 报告，本期无更新 |
| Bedrock cost | 1 | #2000 streaming token | r23 报告，本期无更新 |
| **OTEL trace 完整性** | **1** | **#2112**（+110/-9） | **本期新增开放** |
| **MCP listChanged** | **1** | **#1850 第 5 楼** | **本期新增认领** |
| **跨厂商 CLI wrapper** | **1** | **LiteLLM #29846** | **本期新增 DRAFT** |

**静态期说明**：2.5h 内 agentgateway **零合入**（last merge 仍为 06-05 23:13 UTC 的 #2106 anthropic system messages）。这是 r23 之后 7 个 PR/65 分钟密集合入后的自然回落——**howardjohn 与 apexlnc 处于 review/coding 静默期**。

## 3. AIGW 落点（新增 2 条硬要求）

| 编号 | 硬要求 | 来源 |
|---|---|---|
| **AG-42** | 多 agent 长链路 trace **必须配置 `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`**（建议 ≥512）；**所有手工构造 span 的组件必须显式回填 `dropped_attributes_count`**——这是 trace 完整性与成本归因的审计硬要求 | PR #2112 + issue #2060 |
| **AG-43** | mux 模式下 **`prompts/resources/tools` 的 `*_listChanged` 必须全开**；任一后端 list_changed → 全部订阅客户端 fan-out；fan-out 时机不能 race | Issue #1850 第 5 楼（#2077 tools 已合入） |

**AG-41 细化**：分两条子路径
- **AG-41.a**（LiteLLM-style）：CLI 启动时 env 改向（`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`，清 `ANTHROPIC_API_KEY`），对 Claude Code 进程透明 —— **来源** LiteLLM #29846
- **AG-41.b**（agentgateway-style）：运行时拦截 server-side tool call，**注入 MCP tool 到 tool-calling 数组**（filesystem / web search / DB），对 model 透明 —— **来源** Issue #2111

**AIGW 硬要求全集 43 条**：AG-1 ~ AG-43。

## 4. 风险与待办

- **OTEL default 128** 在多 agent 长链路是 **silent 数据丢失**，且当前 trace 路径**未记录 dropped**。#2112 修，但**需 +1 配套 alert**：`dropped_attributes_count > 0` 即应触发。
- **mux `*_listChanged` fan-out race** 未在 issue 1850 讨论中明确（howardjohn 仅说"make it work then enable"）。rohitg00 的 PR 应当会给出 race-free 方案，下轮追踪。
- **LiteLLM #29846 DRAFT**——Greptile review 还没求（"I have requested a Greptile review"未勾选），预计 1-3 天进 review。

## 引用与数据来源

- agentgateway [PR #2112](https://github.com/agentgateway/agentgateway/pull/2112) · [Issue #2060](https://github.com/agentgateway/agentgateway/issues/2060) · [Issue #1850](https://github.com/agentgateway/agentgateway/issues/1850) · [commits since r23](https://github.com/agentgateway/agentgateway/commits/main)
- 上轮 [r23（23:01）](reports/2026-06-06-2301-aigw-agent-gateway-r23.md) 中的 #2088/#1450/#1842/#1784/#2000
- 跨厂商：LiteLLM [PR #29846](https://github.com/BerriAI/litellm/pull/29846) · [LiteLLM Web Search Interception](https://docs.litellm.ai/docs/integrations/websearch_interception)
- 协议：[OpenTelemetry Span Limits](https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/#general-sdk-configuration) · [MCP list_changed](https://modelcontextprotocol.io/specification/2025-06-18/server/resources#list-changed-notification)
- 上轮报告：[r23（23:01）](reports/2026-06-06-2301-aigw-agent-gateway-r23.md) · [r22（16:50）](reports/2026-06-06-1650-aigw-agent-gateway-r22.md) · [r21（10:03）](reports/2026-06-06-1003-aigw-agent-gateway-r21.md)
