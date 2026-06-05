# AI 网关持续深挖 · Agent Gateway 专题 · 第 16 期

> 抓取时间：**2026-06-05 16:49 CST**（UTC 2026-06-05 08:49）
> 抓取来源：GitHub Releases API + agentgateway 主仓近期 PR + LiteLLM 1.88.0-rc.3
> 主题索引：cron 2/9 → Agent Gateway（multi-agent 编排 / trace 调试 / 成本归因）
> 上一期：2026-06-05-1618-aigw-agent-gateway-r15.md（GHSA-q775 修补链 + 1.3 A2A backend）

## 本期一句话总结

agentgateway 在 6 月 4-5 日这一波合并，把 Agent Gateway 的"横切面"从 1.3-alpha 的协议级 feature（A2A backend）补齐到工程可用：**可观测**（#1784 proxy timing / #2061 config_synchronized / #2085 agctl evicted）、**policy**（#1842 ExtMCP 协议感知 ext_authz / #2071 ext_proc ImmediateResponse）、**identity**（#2088 OAuth ID-JAG / Cross App Access / #2037 AWS AssumeRole / LiteLLM #29586 A2A M2M / #28356 MCP OAuth passthrough）、**provider normalize**（#2089 Anthropic system role）、**MCP 兼容**（#2077 listChanged 透传）。多 agent 编排的"网关原语"从"协议 + 路由"扩展到"identity + 审计 + 计时"。

## 一、本期关键 PR（按维度）

- **可观测** — #1784 (proxy timing histogram, kind 切分, CEL 变量) / #2061 (`config_synchronized` gauge) / #2085 (agctl evicted backends)
- **policy** — #1842 ExtMCP（MCP-aware ext_authz/ext_proc, per-method callout, upstream tool name 而非 mux 后名）/ #2071 ext_proc ImmediateResponse for response body
- **identity** — #2088 OAuth ID-JAG / Cross App Access（RFC 8693 → RFC 7523 两步 token 交换，缓存键 (subject, audience, scope, resource)）/ #2037 AWS AssumeRole / LiteLLM #29586 Databricks A2A M2M / #28356 MCP OAuth passthrough + issuer-scoped JWT
- **provider normalize** — #2089 Anthropic Messages system role
- **MCP 兼容** — #2077 `tools/listChanged` 透传（multiplex 模式）
- **LiteLLM agent 相关** — #28963 LangFlow agent provider + A2A session bridging / #29489 vertex/anthropic namespace tools / #29729 Agent Builder agent selection / #29731 团队 BYOK model name 修复 / #27764 gate `/public/mcp_hub` / #29411 MCP server edit 清空 allowed_tools / #27707 内部 rate-limit error 带 `llm_provider`

**LiteLLM 1.88.0-rc.3（2026-06-05 02:10 UTC）**：仅 2 commit，关键 `3d00874 fix(proxy): match passthrough registry routes bare-to-bare with SERVER_ROOT_PATH`——rc.2 #28547 让 `get_request_route` strip deployment prefix，但 registry lookup 仍用 `SERVER_ROOT_PATH` re-inflate，**导致 `/llmproxy/ml` 这类子路径 404**。所有用 `SERVER_ROOT_PATH` 反代的 LiteLLM 部署升 rc.3 才能恢复 passthrough route 解析。

## 二、深度拆解 #1784：proxy timing histogram

### 2.1 加了什么

```
# HELP agentgateway_request_processing_seconds Duration from receiving an HTTP request to sending the primary outbound call (seconds).
# TYPE agentgateway_request_processing_seconds histogram
agentgateway_request_processing_seconds{backend, bind, gateway, listener, route, route_rule}
```

以 `kind` 切分（primary backend / sub-agent backend / MCP tool call / A2A peer）。CEL 变量也同步暴露：`request.backend_call.kind`、`response.backend_call.kind`、`request.elapsed`、`response.elapsed`，policy 里可直接做条件化路由（"primary backend 已在 P99 之上时，第二次 sub-agent 调用直接走 fallback 模型"）。

### 2.2 多 agent 调试的实际收益

1. **agent 拓扑可视化**。`{backend, route, route_rule}` 三标签笛卡尔积天然描绘"哪个 client 的哪个 agent session 走到了哪条路由、命中了哪个 backend"——**multi-agent 编排里"某条子路由为什么变慢"**终于有 metric 答案。
2. **退避 / 熔断的 metric 化触发**。之前退避是 timer-based 粗粒度；现在如果 `request.elapsed > X` 同时 `route_rule` 是 sub-agent，可 CEL 直接熔断该子 agent，把请求改路由到 cold-standby agent。
3. **A2A peer 延迟横向比较**。r15 讲了 A2A backend type 化；`backend` 标签把 agent↔agent、agent↔model 拆开——**A2A 协议的"call graph metric"基础**。

### 2.3 跟 #2061 + #2085：可观测三角

- **#2061** `config_synchronized` gauge：每次 `StateManager` reload 立即更新。SRE 一直想要"我现在跑的 config 和磁盘上的 config 是不是同一份"——这是答案。**对 agent gateway 这种 xDS 热更新场景极其关键**。
- **#2085 agctl**：`get backends` 不再藏 LB 已驱逐的后端，对"为什么我的 agent 池子越跑越少"的诊断从 log-grep 变成 list-即知。

**三件套合起来**：#1784 = request-side timing，#2061 = control-plane health，#2085 = data-plane membership。**Agent gateway SLO dashboard 的最小可用数据集**。

## 三、深度拆解 #1842：ExtMCP — 把 MCP 协议感知塞进 ext_proc/ext_authz

### 3.1 解法与价值

新增 `ExtMcp` backend policy：

- **per-method callout**：`tools/call`、`tools/list`、`prompts/get` 等 method 按 method 名 opt-in 触发。
- **upstream 视角的 tool name**：hook 收到的是"上游 agent 真实看到的 tool 名"，不是 mux 之后的 `tool_name_backend_name`；backend 名字以 metadata 形式单独传。
- **list fanout 一 backend 一 hook**：multiplex 模式下 `tools/list` 实际 fan-out 到 N 个 backend 各自 list，每个 backend 独立触发一次 ExtMCP hook。
- **post-auth、不重跑 mcpAuthentication**：避免循环。

### 3.3 对 multi-agent 编排的价值

- **per-tool policy**。"`web_search` 命中 `domain=internal` 之外关键词截断并告警"——之前需应用层 try/catch；ExtMCP 在 hook 侧直接 deny/transform。
- **per-agent-cost 归因**。hook 在 `tools/call` 上能拿到 `params`，把 `agent_id` / `session_id` 转写到 metrics label——**Agent Gateway 的 cost attribution 第一次有了"tool-level 切片"**，而不是只有"request-level"和"backend-level"两个粒度。
- **audit 合规**。HIPAA / SOC 2 / EU AI Act 约束的客户，hook 持久化"哪个 agent 在哪个 session 调了哪个 tool、入参是什么"——直接接 SIEM。

### 3.4 跟 #2071 一起看

#2071 修 ext_proc response body phase 之前可能 hang 死的问题。配上 #1842，MCP hook 现在能稳定在 response 阶段直接给 ImmediateResponse（deny / rewrite and continue），**不会卡住整个 agent session**。两条合起来把 ExtMCP 推到 production safe。

## 四、深度拆解 #2088：OAuth Identity Assertion（ID-JAG / Cross App Access）

### 4.1 问题场景

用户登录 agent → agent 用 user context 调下游 API（Calendar、CRM、Email）。目前实现多是 agent 后端持一对"service account credentials"，所有 user 共用，**丢掉了 user 身份**。

正解是 OAuth Identity Assertion（草案 `draft-ietf-oauth-identity-assertion-authz-grant`，Okta 推的 **Cross App Access**）：

```
agent (with user's session token)
  → 1) RFC 8693 token exchange at user IdP → ID-JAG
  → 2) RFC 7523 JWT-bearer grant at resource AS → resource-scoped Bearer
  → 3) 用 resource Bearer 调下游 API
```

两步走必要性：(1) 把"用户身份"从 agent 所在域转写到资源域；(2) 在资源域 AS 上申请"针对该资源的访问令牌"。下游 API 看到的是 user 本人 token，agent 退化成 token 交换代理。

### 4.2 agentgateway 的实现（#2088）

在 `BackendAuth` enum 加 `backendAuth.identityAssertion`：

- 每次 backend call 由 gateway 帮 agent 走完两步 exchange；
- ID-JAG 和 jwt-bearer 的 scope **都显式前向传递**（资源 AS 不继承 ID-JAG scope，必须显式请求）；
- 缓存键 `(subject, audience, scope, resource)`，TTL = exp - 30s；
- client auth 支持 `clientSecretBasic` / `clientSecretPost` / `privateKeyJwt`；
- 在 Okta Cross App Access sandbox（https://xaa.dev）端到端验过。

### 4.3 对 multi-agent 编排的价值

- **多 agent 共享 user context 不需要把 token 在 agent 之间传来传去**。每个 agent 只持"自己需要的那一段 audience Bearer"，gateway 帮忙换。
- **审计链更清晰**。下游 API 收到的 Bearer 里写的是 user 真实 subject，审计/合规时不需要回头拼 "agent X 调 Y 时是哪个 user 触发的"。
- **和 #1842 ExtMCP 配合**。ExtMCP hook 拿到的 `auth.context` 现在包含 user 真实 subject，可以做 "per-user 限流"（同一 user 的 tool call 1 分钟内不超过 30 次）——**多租户 agent 平台必须的**。

## 五、次要 PR

- **#2089 Anthropic system role normalize**：`/v1/messages` 解析时把"消息数组里塞了 `role: system`"提升到顶层 `system` + 保留 `cache_control` metadata + 保持非 system 消息顺序。Claude Code Cowork gateway 模式之前会让 Bedrock Anthropic strict reject。**Anthropic-compatible provider 跨 client 升级不再因 system role 位置差异而坏**。
- **#2077 MCP `tools/listChanged` 透传**：multiplex 模式原来没在 InitializeResult 声明该能力，spec-compliant 客户端收到 `notifications/tools/list_changed` 后**直接丢弃**。修法：multiplex 模式无条件声明。**过去 6 个月各家 agent 平台"为什么我的 MCP 工具集合好像不更新"的最大隐性 root cause**。
- **#2037 AWS AssumeRole backend auth**、**#1846 下游 HTTP CONNECT termination**：分别用 STS 链拿短时 credential、opt-in 终止 CONNECT 不再 405。

## 六、给 Agent Gateway 维护者的几条 takeaway

1. **可观测三件套到位 (#1784 / #2061 / #2085)**。SRE dashboard 从"通用 L7 metrics + grep 日志"升级到"backend 切片 + config sync 状态 + membership diff"，可直接用 Grafana 出 SLO。
2. **policy 层进入协议感知时代 (#1842 ExtMCP)**。MCP-aware ext_proc 把"per-tool policy / per-tool cost"从应用层提到网关层，是 Agent Gateway 区别于通用 L7 API Gateway 的关键 feature。
3. **identity 三件套对齐 (#2088 ID-JAG / #2037 AWS AssumeRole / #28356 MCP OAuth passthrough / #29586 A2A M2M)**。"agent ↔ agent"、"agent ↔ 下游 API"、"agent ↔ MCP"三类的 identity 协议都从"长期 secret + 共享 service account"切到"短时 token + user context / issuer-scoped JWT"，**HIPAA / SOC 2 / EU AI Act 合规通路被打通**。
4. **provider normalize (#2089 Anthropic system role)** 是被低估的工作量：每次新 agent framework 升级都可能让 spec 边界 case 暴露，gateway normalize 是最稳的位置。
5. **MCP spec 兼容性是暗坑 (#2077 listChanged)**。multiplex 模式独有的 spec 边界 case 正在被一连串 PR 修补，部署前必须盯紧 agentgateway 1.3.0 stable 之前的 1.2.x patch。

## 七、引用与数据来源

- BerriAI/litellm v1.88.0-rc.3 — https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3
- BerriAI/litellm v1.88.0-rc.2 — https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.2
- BerriAI/litellm commit 3d00874 — https://github.com/BerriAI/litellm/commit/3d00874
- LiteLLM agent-related PRs (#29586 / #28963 / #29489 / #29729 / #28356 / #27764 / #29411 / #29731 / #27707) — https://github.com/BerriAI/litellm/pulls?q=is%3Apr+merged%3A2026-06-02..2026-06-05
- agentgateway v1.3.0-alpha.1 — https://github.com/agentgateway/agentgateway/releases/tag/v1.3.0-alpha.1
- agentgateway PRs (#1784 / #2061 / #2085 / #1842 / #2071 / #2088 / #2037 / #2089 / #1846 / #2077) — https://github.com/agentgateway/agentgateway/pulls?q=is%3Apr+merged%3A2026-06-04..2026-06-05
- Okta Cross App Access sandbox — https://xaa.dev
- OAuth Identity Assertion Authz Grant — https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/
- RFC 8693 — https://datatracker.ietf.org/doc/html/rfc8693
- RFC 7523 — https://datatracker.ietf.org/doc/html/rfc7523
- MCP spec `tools.listChanged` — https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- 内部上期：hermes/reports/2026-06-05-1618-aigw-agent-gateway-r15.md
