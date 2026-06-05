# AI 网关持续深挖 · Agent Gateway 专题 · 第 15 期

> 抓取时间：**2026-06-05 16:18:36 **（UTC 2026-06-05 08:18:36）
> 抓取来源：GitHub Releases API + 关联 PR
> 主题索引：cron 2/9 → Agent Gateway（multi-agent 编排 / trace 调试 / 成本归因）
> 上一期：2026-06-05-0913-aigw-agent-gateway-r13.md

## 本期一句话总结

5 月底到 6 月初这一周，Agent Gateway 故事里出现了一件影响多租户成本归因的「豁免漏洞被修补」事件：LiteLLM 在 1.87.1 / 1.86.4 / 1.88.0-rc.2 三个 release line 上同步 backport 了 **GHSA-q775 session-token budget-ceiling exemption**（PR #29612），随后又在 6 月 4 日用 PR #29639 修掉了这层豁免被 `default_key_generate_params` 间接绕过的二次漏洞。与此同时 agentgateway 在 1.3.0-alpha.1 把 A2A（Agent-to-Agent）从协议概念抬成了 first-class backend type——这两条线合起来，就是把「代理间的成本/权限边界」从单 LLM 网关推进到了多代理组合层。

## 一、关键发版

| 仓库 | 版本 | 发布时间 (UTC) | 性质 |
|---|---|---|---|
| BerriAI/litellm | v1.88.0-rc.3 | 2026-06-05 | rc，1.88 系列最新 |
| BerriAI/litellm | v1.88.0-rc.2 | 2026-06-04 | rc，#29637 + #29639 hardening |
| BerriAI/litellm | v1.87.1 | 2026-06-04 | stable backport |
| BerriAI/litellm | v1.86.4 | 2026-06-04 | stable backport |
| BerriAI/litellm | v1.88.0-rc.1 | 2026-06-03 | rc 起点 |
| agentgateway/agentgateway | v1.3.0-alpha.1 | 2026-05-23 | alpha，A2A backend |
| agentgateway/agentgateway | v1.2.1 | 2026-05-15 | patch（capacity-weighted LB）|
| agentgateway/agentgateway | v1.2.0 | 2026-05-14 | minor（xDS TLS 默认开启 + route delegation）|
| langchain-ai/langgraph | 1.2.4 | 2026-06-02 | patch（_on_started 兼容）|
| langchain-ai/langgraph | sdk 0.4.2 | 2026-06-01 | SDK（thread_id percent-encode）|
| langfuse/langfuse | v3.178.0 | 2026-06-02 | agent → langfuse MCP 双向打通 |
| openai/openai-agents-python | v0.17.4 | 2026-05-26 | patch（trace export 修复）|
| Arize-ai/phoenix | v17.2.0 | 2026-06-03 | PXI route info tool |
| traceloop/openllmetry | 0.61.0 | 2026-05-31 | GenAI semconv 收口 |

## 二、深度拆解：GHSA-q775 session-token budget-ceiling exemption

### 2.1 背景

LiteLLM 在 5 月初公开了 **GHSA-q775**（CVE 系列），把"被代理创建的 key 不能超过调用者自己的 max_budget"作为强制约束。问题在于：UI/CLI 登录时签发的 session token 通常 `max_budget=0.25`（受 `max_ui_session_budget` 限制），但管理员要通过这个 session 在 UI 里给团队成员开 `max_budget=100` 的 key——在 GHSA-q775 之后，这条路径直接 `400 max_budget (100.0) cannot exceed the caller's own max_budget (0.25)` 报错，UI 没法用了。

### 2.2 修复链

| PR | 仓库 | 内容 | merge 时间 (UTC) |
|---|---|---|---|
| #29612 | BerriAI/litellm | 引入 `is_ui_session_team_key` 豁免：仅对"team key + 自身是 team admin"放行 | 2026-06-03 21:08 |
| #29637 | BerriAI/litellm | 把 #29612 backport 到 1.88.0-rc.1 | 2026-06-04 (early) |
| #29630 | BerriAI/litellm | 1.86.x 五 patch backport | 2026-06-04 |
| #29631 | BerriAI/litellm | 1.87.x 五 patch backport | 2026-06-04 |
| #29635 | BerriAI/litellm | 把 #29612 backport 到 1.86.5 | 2026-06-04 |
| #29636 | BerriAI/litellm | 把 #29612 backport 到 1.87.2 | 2026-06-04 |
| #29639 | BerriAI/litellm | 修二次漏洞：`default_key_generate_params.team_id` 自动注入会"伪造"team 标识，让个人 key 走豁免 | 2026-06-04 02:27 |
| #29644 / #29645 | BerriAI/litellm | revert 1.86.5 / 1.87.2 premature bump（防版本号污染）| 2026-06-04 |

### 2.3 #29639 的"绕后绕"

`#29612` 写的判定大致是：

```
is_ui_session_team_key = (data.team_id is not None
                          and caller is admin of that team
                          and caller token is a UI/CLI session token)
```

但 LiteLLM 的 key 创建流程里，`default_key_generate_params` 会在用户提交的 body 之后注入默认值——如果管理员在环境里设了 `default_key_generate_params.team_id=xxx`，那创建一个 **personal key**（不传 `team_id`）时，注入逻辑会悄悄给它贴上 `team_id`，导致 `is_ui_session_team_key = True`，豁免生效，**正好绕回 GHSA-q775 修补前的越权发 key 路径**。

`#29639` 修法：在 defaults loop 之前先 `_requested_team_id = data.team_id`，豁免只对显式传 `team_id` 生效。加了一个 `default_team_id_personal_key_still_capped` 回归测试。

### 2.4 Agent Gateway 视角的影响

把这件事放回 Agent Gateway 的语义里看：

1. **成本归因的边界**。在多 agent 编排里，"谁付钱"不是一个 token 一个 token 算出来的，而是要看**整个 session 的累计 budget**。GHSA-q775 一刀切是安全的，但砍掉了 UI 代理操作路径。`#29612` 在"管理员意图明确 + 操作的是下游 team key"这一窄路径上放开豁免。
2. **二次漏洞的本质**是"配置注入"——和 agent 编排里常见的"工具结果回写再触发另一个 agent"是同一类问题。`#29639` 给出的解法是**捕获原始意图（pre-defaults）**而不是看最终生效值，对所有"defaults loop / context collapse / 工具结果回填"场景都通用。
3. **运营含义**：多租户 LiteLLM 部署上 1.87.0 / 1.86.0 / 1.88.0-rc.0 都不能跳过这次修补，**必须**升到 1.87.1 / 1.86.4 / 1.88.0-rc.2 或更高。

## 三、agentgateway 1.2 → 1.3：多代理组合的网关抽象

### 3.1 1.2.0 的两个隐性铺垫

`v1.2.0`（2026-05-14）放出来的两个 feature，是 1.3-alpha 引入 A2A backend 的前提：

- **Conditional policy execution (CEL)**：extAuth / transformations / rate limiting / external processing 都能用 CEL 表达式条件化选择 policy。Agent gateway 转给下游 agent 时，往往要按 header / body 决定限流档位，这条直接给出机制。
- **Route delegation**：父 route 把 `/anything/team1` 这种前缀委派给 `team1` 命名空间下的子 HTTPRoute。对应到 Agent Gateway 就是"平台团队拥有 `/agents/team1/*` 的统一鉴权 + 限流入口，应用团队自治自己注册的具体 agent"。

### 3.2 1.2.1 的 capacity-weighted LB

`v1.2.1` PR #1808 (`stevenctl`)：把 upstream load balancing 从"按请求数"改成"按 capacity weight"。对一个 agent 后端来说，每个 agent 进程能并发的 session 数差别很大（一个 Claude Code agent 可能只跑 4 个并行 session，一个 chat agent 能跑 200 个），按 capacity 加权后，gateway 不会把热门 agent 全部打到同一个后端。这是 agent fleet 健康度的关键一环。

### 3.3 1.3.0-alpha.1 的 A2A backend

`v1.3.0-alpha.1`（2026-05-23）PR #1841 (`howardjohn`)：

> a2a: add first class a2a backend type in AGBE

AGBE = Agent Gateway Backend Engine。把 A2A（Agent-to-Agent 协议，Google 2025 年发起）从"过路协议"提为 first-class backend type——意味着 agentgateway 正式接受"A2A 客户端 → 路由 / 限流 / 鉴权 → A2A 服务端"这种纯代理到代理的拓扑，而不是只把 A2A 当成"用 HTTP 包一下"。

同 PR 队列里：

- `mcp: support sub/unsub from resource (no multiplex)` PR #1 (master 重置) — MCP 资源订阅的极简实现，不带服务端多路复用；
- `auth location: add expression for extraction` PR #1798 — auth 之前只能用 `header.X` 拉 token，现在支持 CEL 表达式，可以从 body / query 拼装；
- `release: attach VEX policy to supress CVE false positives` PR #1826 — 镜像开始带 VEX（Vulnerability Exploitability eXchange）数据，CVE 扫描器不会把不受影响组件告警爆掉。

### 3.4 Trace 维度的承接：openai-agents 0.17.x

`openai-agents-python v0.17.0` 把 RealtimeAgent 的默认模型换成 `gpt-realtime-2`；`v0.17.4` 补了一组 trace export 修复：

- PR #3475 `fix: use non-None value for output in FunctionSpanData` — Function tool 调用产生的 span 之前会写出 `output=None`，trace 端到端拼接会断；
- PR #3483 `fix: add missing entries to span __slots__`；
- PR #3489 / #3490 `fix: export more tracing related functions & types`；
- PR #3466 `fix: apply hardened http client default to MCP SSE transport` — MCP SSE 长连接复用 hardened HTTP client；
- PR #3461 `fix: #3459 add opt-in recovery for missing function tools` — agent 调用栈里 tool schema 缺失时（很可能是上游 schema 版本漂移）选择恢复而不是直接 raise。

## 四、LangGraph 1.2 / SDK 0.4：durable error-handler 跨主机崩溃恢复

`langgraph 1.2.0` 上一期 r13 已经讲过；这两周跟进的是 1.2.4 和 SDK 0.4.x：

- `1.2.4`（2026-06-02）PR #7987 `fix(langgraph): keep _on_started backward-compatible with overrides predating cause` — error handler 钩子加了 cause 字段后，向下兼容老 override；
- `1.2.4` PR #7978 `test(sdk-py): add factory-graph integration test exercising the server factory path` — SDK server factory 模式进入 CI；
- `sdk 0.4.0`（2026-05-28）一口气加了 17 个 SDK feature（PR #7818–#7833）：**v3 streaming primitives + SSE transport**、**websocket stream transports**、**scoped subgraph handles**、**shared stream subscriptions**、**sync thread stream core**、**hardened streaming reconnects**。基本上是把 Python SDK 的 streaming 层从 SDK 0.3.x 的"能跑"推到"生产可观测、可断线重连、可分 sub-graph"的状态；
- `sdk 0.4.2`（2026-06-01）PR #7954 `fix(sdk-py): percent-encode thread_id in v3 stream transport default paths` — thread_id 里有特殊字符（比如 URL 不安全字符）会被 percent-encode，断了 service mesh 边的 path 匹配。

对 Agent Gateway 的含义：LangGraph 是上游长 session agent 的代表；SDK 把 v3 streaming 摆平后，agentgateway 这类 L7 gateway 才有意义去做"按 thread_id 染色 + 跨节点路由 + 按 cost 累计"。

## 五、Langfuse v3.178.0：agent ↔ langfuse MCP 双向打通

`langfuse v3.178.0`（2026-06-02）三件新事：

- PR #13747 `feat(agent): Connect in-app agent to langfuse MCP` — langfuse 自己的 in-app agent 现在能直接调 langfuse 的 MCP server（数据集、注释队列、score config），形成自循环；
- PR #13946 `feat(mcp): Add optional id to upsertDataset` — MCP tool 调 dataset 的时候可以显式带 id，避免 name 漂移；
- PR #13980 `fix(security): enforce auditLogs:read and audit-logs entitlement for audit_logs batch exports` — 审计日志批量导出的权限收口；
- PR #13992 `fix(ui): better trace detail header spacings`。

配 v3.177.0 的"AI telemetry toggle"（PR #13939）一起看：langfuse 把"是否记录 IO"做成 feature flag（`LANGFUSE_DISABLE_LEGACY_TRACING_IO_SEARCH`，PR #13912 / #13929），给合规场景留逃生通道。

## 六、OpenLLMetry 0.61.0：GenAI semconv 合规

`traceloop/openllmetry 0.61.0`（2026-05-31）：

- **PR #3837 openai-agents: GenAI semconv compliance** — span 属性从私有命名 `gen_ai.*` 正式对齐 OpenTelemetry GenAI semantic conventions 草案，对所有"按 vendor 切 trace 视图"的可观测平台是利好（之前 openai-agents 的 trace 在 OTLP 后端经常属性对不上）；
- **PR #4130 / #4131 openai-agents**: emit `cache_read.input_tokens` / `reasoning_tokens` / `response.instructions` as system prompt — 成本归因的最后一公里，cache hit 的 token 和 reasoning_o1 系的 reasoning token 现在能在 trace 上拆开；
- **PR #4198 openai**: instrument `responses.parse()` for structured-output tracing；
- **PR #4137 sdk**: warn when both `exporter` and `processor` are passed to `Traceloop.init()` — 防止用户配错导致 span 双发。

## 七、给 Agent Gateway 维护者的几条 takeaway

1. **成本归因不要只看"最终参数"，要保留 pre-defaults 快照**。`#29639` 的修法在 agent framework 里完全可以套用：LangGraph / OpenAI Agents 的 tool defaults / hook chain 也存在类似 `default_*_params` 的隐性注入。
2. **A2A backend type 是一道分水岭**。agentgateway 1.3-alpha 之后，agent 之间的 RPC 第一次在 L7 网关上和 HTTP 一样有"路由 / 鉴权 / 限流 / 计量"四件套；之前都得在应用层自己写。
3. **capacity-weighted LB 比 RR 重要**。Agent 进程的并发承载力方差极大；RR 在 5×5 的 backend pool 上就会把热 agent 打死。
4. **GenAI semconv 收口是 trace 平台换 vendor 的门票**。openllmetry 0.61 对齐后，agent gateway 输出的 trace 可以在 Langfuse / Arize Phoenix / SigNoz 之间无损切换。
5. **UI session 路径必须**有 `is_ui_session_*` 标记，不能仅靠 budget 反推"是管理员在操作"。

## 八、引用与数据来源

- BerriAI/litellm v1.88.0-rc.3 — https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3
- BerriAI/litellm v1.88.0-rc.2 — https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.2
- BerriAI/litellm v1.87.1 — https://github.com/BerriAI/litellm/releases/tag/v1.87.1
- BerriAI/litellm v1.86.4 — https://github.com/BerriAI/litellm/releases/tag/v1.86.4
- PR #29612 `fix(key_generate): exempt UI/CLI session tokens from the budget ceiling for team keys` — https://github.com/BerriAI/litellm/pull/29612
- PR #29639 `fix(key_generate): harden GHSA-q775 session-token exemption against default_key_generate_params (1.88 rc)` — https://github.com/BerriAI/litellm/pull/29639
- PR #29637 backport #29612 → 1.88.0-rc.1 — https://github.com/BerriAI/litellm/pull/29637
- PR #29635 / #29636 / #29644 / #29645 stable backport chain — https://github.com/BerriAI/litellm/pulls?q=is%3Apr+session-token+budget-ceiling
- agentgateway v1.3.0-alpha.1 — https://github.com/agentgateway/agentgateway/releases/tag/v1.3.0-alpha.1
- agentgateway v1.2.1 — https://github.com/agentgateway/agentgateway/releases/tag/v1.2.1
- agentgateway v1.2.0 — https://github.com/agentgateway/agentgateway/releases/tag/v1.2.0
- agentgateway PR #1841 `a2a: add first class a2a backend type in AGBE` — https://github.com/agentgateway/agentgateway/pull/1841
- agentgateway PR #1808 `fix(proxy): capacity weighted loadbalancing` — https://github.com/agentgateway/agentgateway/pull/1808
- agentgateway PR #1798 `auth location: add expression for extraction` — https://github.com/agentgateway/agentgateway/pull/1798
- agentgateway PR #1826 `release: attach VEX policy to supress CVE false positives` — https://github.com/agentgateway/agentgateway/pull/1826
- langgraph 1.2.4 — https://github.com/langchain-ai/langgraph/releases/tag/1.2.4
- langgraph sdk 0.4.2 — https://github.com/langchain-ai/langgraph/releases/tag/sdk%3D%3D0.4.2
- langgraph sdk 0.4.0 — https://github.com/langchain-ai/langgraph/releases/tag/sdk%3D%3D0.4.0
- langgraph 1.2.0 (durable error-handler resume) — https://github.com/langchain-ai/langgraph/releases/tag/1.2.0
- langfuse v3.178.0 — https://github.com/langfuse/langfuse/releases/tag/v3.178.0
- langfuse v3.177.0 — https://github.com/langfuse/langfuse/releases/tag/v3.177.0
- openai-agents-python v0.17.4 — https://github.com/openai/openai-agents-python/releases/tag/v0.17.4
- openai-agents-python v0.17.0 — https://github.com/openai/openai-agents-python/releases/tag/v0.17.0
- Arize Phoenix v17.2.0 — https://github.com/Arize-ai/phoenix/releases/tag/arize-phoenix-v17.2.0
- traceloop/openllmetry 0.61.0 — https://github.com/traceloop/openllmetry/releases/tag/0.61.0
- OpenTelemetry GenAI semantic conventions — https://opentelemetry.io/docs/specs/semconv/gen-ai/
- 内部上期：hermes/reports/2026-06-05-0913-aigw-agent-gateway-r13.md
