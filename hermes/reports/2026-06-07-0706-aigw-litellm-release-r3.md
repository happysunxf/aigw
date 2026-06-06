# LiteLLM v1.89.0-rc.1 发版追踪报告

> 报告时间：2026-06-07 07:06 CST（cron 30 分钟轮值 · 本次主题 0/7 → 单产品发版追踪 · LiteLLM 轮位）
> 仓库源：`https://github.com/BerriAI/litellm`
> 数据获取时间：2026-06-07 07:06 CST

## 本期要点（TL;DR）

- 2026-06-06 23:06 UTC，BerrAI 发布 LiteLLM **v1.89.0-rc.1**，进入 1.89 系列的第一个 RC；上一稳定线 1.87.x 仍在 1.87.1 维护。
- 1.89.0-rc.1 的最重磅改动集中在**三处**：
  1. **MCP OAuth 透传 + 发行方范围 JWT 鉴权**（PR #28356 / 原始 #28008，2026-06-02 已合入），在 MCP 网关层面引入 `oauth_passthrough` 标志 + DB 迁移；
  2. **A2A agent 协议新增 watsonx Orchestrate provider**（PR #29410，2026-06-02 合并）以及 LangFlow A2A session bridging（PR #28963）；
  3. **MCP 维度的 per-server RPM 限流**（PR #29482，按 key/team 维度）。
- 1.89.0-rc.1 同时合入大量 OTel 增强：MCP semantic conventions（#29468）、guardrail span on passthrough block（#29470）、401 状态在 JWT 过期时保留（#29510）、Datadog 413 拆分批（#29444）。
- 治理动作：CI 引入 `stable/X.Y.x` 分支自动创建（#29457），CircleCI 失败用例重跑收集逻辑修复（#29475），proxy 优雅下线 `/health/drain` preStop hook（#29439）。

## v1.89.0-rc.1 关键 PR 拆解

### 1. MCP OAuth 透传 & 发行方范围 JWT（PR #28356，原始 #28008）

这是一条被 Cursor 标为 **High Risk** 的安全相关变更，落地三件事：

- 新增 MCP server 级 `oauth_passthrough` 标志（配套 DB migration + schema）。当 `auth_type=none` 的 server 透传 `Authorization` 头时，网关会**代理上游 RFC 9728 `oauth-protected-resource` 元数据**（带缓存），允许 OAuth 发现阶段的匿名冷启动，发出合规的 `WWW-Authenticate` 挑战，并通过 `MCPUpstreamAuthError` 把上游 401/403 透出而不是返回空工具列表。
- 鉴权转发收口到 `_should_strip_caller_authorization`：LiteLLM API key 不会泄漏到上游，同时**上游 bearer token 在 passthrough 路径上保留**。
- 引入 issuer-scoped JWT 校验，把 MCP 网关的鉴权边界从「鉴 token 是否合法」前移到「鉴 token 是否来自正确发行方」。

> 与之前 mcp-r26/mcp-r27 轮次中我反复强调的「MCP 网关的最大风险是 anonymous cold-start 期间鉴权短路」吻合；这条 PR 算是 LiteLLM 第一次在代码层面做出系统性回应。

### 2. A2A agent 协议家族扩张

- **watsonx Orchestrate provider**（#29410）：新增 IBM CP4D 上的 watsox Orchestrate 适配，实现 submit run / poll / SSE + fallback streaming，注册到 `A2AProviderConfigManager`，UI dashboard `agent_create_fields.json` 增加对应类型。
- **LangFlow A2A session bridging**（#28963）：LiteLLM 端把 LangFlow agent 通过 A2A 协议桥接出来，意味着 LangFlow 的图可以挂在 `/a2a/{agent}/message/send` 下面消费。
- **UI 调整**（#29512）：A2A skill 标签输入和校验。
- 加上之前 #29232 引入的"未来 Claude 模型通过 pattern matching 路由到 Anthropic provider"，A2A 这条线 LiteLLM 明显在**做"agent 协议端点"**而非仅做"模型网关"。

### 3. MCP 网关运营能力（per-MCP-server RPM 限流）

PR #29482 给 MCP server 增加**按 key 和 team 的 RPM 限流**。意义是：之前 MCP 流量只能按全局或按 LiteLLM key 限，单个 MCP server 被打爆时整条 key 都受影响；现在可以把 hot server 隔离在局部限额里。这是生产化治理的一个明确信号。

### 4. OTel / 可观测性矩阵

- MCP semantic conventions 落到 otelv2（#29468）——把 `mcp.method`、`mcp.resource`、`mcp.server` 之类的语义属性标准化。
- Passthrough 路径下 guardrail block 时**显式 emit OTel span**（#29470），之前是被静默吃掉的。
- 401 过期 JWT 的状态码在 OTel trace 里**保留为 401**（#29510），之前可能被映射成 200 / 500 影响告警。
- Datadog 日志批遇到 413 时**拆分**而不是无限重排队（#29444），避免 OOM。

### 5. 治理 / 稳定性

- `ci(release): create stable/X.Y.x line branch on X.Y.0 tags`（#29457）—— 1.88 之后 X.Y.0 标签会自动产生一条 stable/X.Y.x 分支用于 backport。配合 1.87.x 仍在 backport session-token budget-ceiling 例外（PR #29612 / 29636，但被 #29645 回滚了一次重新打 1.87.1），可看出 LiteLLM 已经采用类似 Linux kernel 的 stable line 模型。
- `feat(proxy): native /health/drain preStop hook for graceful shutdown`（#29439）—— K8s rolling update 友好，避免排空时仍发新请求。

## 与近期轮次的连续性

- **mcp-r27**（2026-06-07 01:53）记录了「MCP 网关在 OAuth 透传上仍是行业空白」；1.89.0-rc.1 用 #28356 把这一块从「缺口」变成「落地」，是过去 24h 内 LiteLLM 最实质的进展。
- **arch-benchmark-r8**（2026-06-07 06:19）讨论过「agent 协议端点化」是大势所趋；1.89.0-rc.1 一次加 watsonx Orchestrate + LangFlow 两个 A2A provider，与该判断方向一致。
- **observability-r6**（2026-06-07 05:48）提过 guardrail span 在 passthrough 下缺失；#29470 修复。
- **guardrails-r7**（2026-06-07 04:32）讨论过 JWT 过期 401 在 OTel 里的失真；#29510 修复。

## 风险 / 注意事项

1. **High Risk 标记的 OAuth 透传 PR** 仍需要仔细 rollout：现有 `oauth_passthrough` 配置的迁移路径在 PR 描述里被点名要求审慎。
2. **1.87.x 同时存在 1.87.1 / 1.87.2 反复**（#29631 切到 1.87.1，#29636 推 1.87.2，#29645 又回滚到 1.87.1），说明 stable line 的版本号治理仍有摩擦；用户在锁版本时建议直接 pin commit 而不是 tag。
3. **1.89.0-rc.1 仍是 RC**；不建议生产。等 1.89.0 stable 出来后建议优先升级，但先小流量灰度。
4. **CI 改动**（stable/X.Y.x 自动创建、#29475 CircleCI rerun）属于 release 流程结构性变化，会影响未来几周发版节奏。

## 升级建议（如果生产用 1.88.x 及以前）

- 紧盯 1.89.0 stable 标签；rc.1 → stable 之间的 PR diff 要复盘，特别关注 OAuth passthrough 行为切换和 A2A provider 协议版本。
- 升级前预先盘点：MCP server 是否已配 `auth_type=none` 且依赖隐式匿名访问——这些 server 是 OAuth passthrough 改造的主要影响面。
- Datadog 批处理 413 拆分（#29444）是无破坏性变更，可以直接 backport 思路参考。
- K8s 部署侧建议同时升级到使用 `/health/drain` preStop hook（#29439），配合 30s terminationGracePeriodSeconds。

## 引用与数据来源

- LiteLLM v1.89.0-rc.1 release：https://github.com/BerriAI/litellm/releases/tag/v1.89.0-rc.1
- v1.87.1 release：https://github.com/BerriAI/litellm/releases/tag/v1.87.1
- PR #28356 MCP OAuth passthrough：https://github.com/BerriAI/litellm/pull/28356
- PR #28008（原始）：https://github.com/BerriAI/litellm/pull/28008
- PR #29410 watsonx Orchestrate A2A：https://github.com/BerriAI/litellm/pull/29410
- PR #28963 LangFlow A2A：https://github.com/BerriAI/litellm/pull/28963
- PR #29482 per-MCP-server RPM：https://github.com/BerriAI/litellm/pull/29482
- PR #29468 MCP OTel semantic conventions：https://github.com/BerriAI/litellm/pull/29468
- PR #29470 guardrail span on passthrough block：https://github.com/BerriAI/litellm/pull/29470
- PR #29510 JWT 401 状态保留：https://github.com/BerriAI/litellm/pull/29510
- PR #29444 Datadog 413 拆分：https://github.com/BerriAI/litellm/pull/29444
- PR #29457 stable/X.Y.x 自动分支：https://github.com/BerriAI/litellm/pull/29457
- PR #29439 /health/drain preStop：https://github.com/BerriAI/litellm/pull/29439
- cosign 签名说明：https://docs.sigstore.dev/cosign/overview/
