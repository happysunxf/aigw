# AI 网关深挖 · MCP Gateway 专题（2026-06-06 01:25 CST）

> 主题 1/8：MCP 协议演进 / **生产治理**（**审计 + 零留存** 角度）。  
> 上一轮（22:53）已覆盖 SDK 可靠性，本轮聚焦过去 48h 落地的"审计与缓存隔离"——这正是 AI Gateway 部署里被反复踩的"多租户串号"与"审计上下文缺失"两个洞。

## 一、本轮一句话论点

**MCP 把"零留存"和"审计上下文"两个长期被 Gateway 自行打补丁的领域，推进到了协议层：** `server/discover` 在 #2855 获得 `cacheScope: public | private`（让共享多租户 cache 不再泄 user A 给 user B）；SEP-2817 把 AI 调用的"为什么 / 哪个模型 / 哪一轮"塞进 `_meta.io.modelcontextprotocol/aiInvocation`。前者是隔离面，后者是审计面。两者本周（5/29–6/5）几乎同步落地——没有 `private` 标识，audit `_meta` 一旦被多租户 cache 复用，就成了泄漏面。

## 二、协议侧：#2855 `server/discover` 缓存化

- **PR #2855**（CaitieM20，**2026-06-04 14:48 UTC** merge，10 文件 +47/-18）。Core-Maintainer 在 6/3 RC Spec 评审时发现漏配——`tools/list` / `prompts/list` / `resources/list` / `resources/read` 都已是 `CacheableResult`，唯独 `server/discover` 漏了。  
- 新字段（schema.json + schema.ts）：  
  - `ttlMs: integer` — 毫秒为单位的客户端新鲜期；显式收紧为"必须给"。  
  - `cacheScope: "public" | "private"` — 类比 HTTP `Cache-Control: public/private`：  
    - `public`：**任何**客户端 / 中间层（共享 gateway、proxy）都可缓存，**并**可向**任何**用户投递该副本；  
    - `private`：**只有**发起请求的用户客户端可缓存；多租户共享 cache **MUST NOT** 把该副本给其他用户。  
- 配套措辞（`utilities/caching.mdx`）：服务器**MUST**对同一 list 请求的所有 page 保持同一 `cacheScope`（第一页 `private` 则后续所有 page 也 `private`）。`public` 标注意味着"认证端点返回的结果也可跨用户共享"——给错标注开了口子，需要 server 严格自证"该结果与用户无关"。  
- **对 AI Gateway 的可操作含义**：  
  1. **多租户串号风险收敛**——以前共享 AI Gateway 上跑 `tools/list` 时，只要结果在 TTL 内，第二个用户就拿到第一个用户的列表（含 resource 模板参数、tool 描述里的内部 hint）。`private` 字段把"cache 不能跨用户"提升为 **wire-level MUST NOT**。  
  2. `server/discover` 之前每次都拉，对治理层极不友好：大量重复握手（既增延迟，又给 IdP 增加无意义 token 校验）；如果 server 在握手时回填"用户能访问哪些 sub-server"，本轮之前**没有任何机制**告诉 Gateway 可以 cache。  
  3. **网关实现建议**：把 `cacheScope` 翻译成 cache key 前缀——`public` → hash(server 身份 + 协议版本)；`private` → hash(server 身份 + sub + token-fingerprint)；TTL 直接采用 `ttlMs`。

## 三、协议治理侧：#2863 SEP-to-Spec 一致性 pass

- **Tier Relegation based on unaddressed issues**（`docs/community/sdk-tiers.mdx` +3 行）：旧规则只有"连续 4 周"不达标才降级；新增"issue **2 个月**未处理也可降级"。配合 `disputed` 标签：被标 `disputed` 的 conformance 测试在争议解决前**不计入**计分。  
- **Deprecation Process Update**（`docs/community/feature-lifecycle.mdx` +19 行）：Tier 1 SDK 持续不暴露 Deprecated feature → 触发 Tier 降级；明确"Deprecated 不必在最短窗口内删除，可以长期保留"——以前企业部署总要算"6 个月后会不会突然删"，现在可**显式选择"Deprecated 永久保留"**。新增 Roles 表把治理 SOP 文档化。  
- **对 AI Gateway 含义**：Tier 降级直接**约束了 SDK 在 Gateway 中的可信度**——"必须 deprecation warning 真的冒出来"会通过 SDK 反射到 Gateway 的告警管道；"Deprecated 长期保留"给了企业一个**可证伪的承诺**。

## 四、协议侧：Authorization IG 正式宪章（#2843）

- **PR #2843** `Add Authorization Interest Group charter`（pcarleton，**2026-06-04 13:05 UTC** merge，2 文件 +87/-0）。原本在 Discord `#auth-ig` 自 2025 年中起"野生"运行的 IG 终于有正式 charter。  
- **三 Facilitator**：Aaron Parecki（Okta）、Darin McAdams（Amazon）、Paul Carleton（Anthropic）——"三厂联合背书"是 OAuth 治理少见的"非单厂商可劫持"形态。  
- **6 个孵化的 Working Group**（4 已 Completed / 2 Active）：

| WG | 焦点 | 状态 |
|---|---|---|
| Client Registration | DCR / Client ID Metadata Documents | Completed |
| Mix-up Protection | OAuth AS 混搭与 audience confusion | Completed |
| Profiles | grant 扩展 / DPoP / WIF / 企业托管 | Completed |
| Tool Scopes | 工具级 scope / step-up auth | **Active**（charter pending）|
| Fine-Grained Authorization | RAR（RFC 9396）/ remediation hints | **Active**（charter pending）|
| Improve DevX | 安全客户端/服务端开发最佳实践 | Completed |

- **首次显式 In/Out-of-Scope**：TLS / mTLS 划 Transports WG；server identity / provenance 划 Server Card / Registry。"重定向安全归 Auth IG 还是 Transports WG"现在有据可查。
## 五、SEP 侧：#2817 AI 审计上下文（本轮灵魂）

- **Discussion #2704**（5/9 开，34 评论）：AI 调 tool 时最常缺失**为什么调 / 哪个模型 / 哪个 turn**。实现各自发明字段（`user_query` / `reason` / `invocation_reason` / `model` / `ai_model` / `request_id` / `mcp_request_id` / `correlation_id`）——**审计日志无法跨厂商对账**。  
- **SEP-2817** 最小设计：新增**可选** reserved `_meta` key `io.modelcontextprotocol/aiInvocation`，全字段**可选** + **client-asserted** + **显式声明不作为授权证据**。四字段：`invocationReason` / `model` / `userIntent`（**safe to provide** 时才给）/ `turnId`（同 turn group key；服务器**MAY**在响应 `_meta` 里只回 `turnId`）。Draft，sponsor 寻找中，21 评论。  
- **AI 准备声明**："This SEP was prepared with AI assistance for structure, wording, and review"——**MCP 历史上第一份元数据里自带"AI 辅助声明"的 SEP**。  
- **关联 SEP 拼图**：**SEP-2448** server execution telemetry（savula15，3/24）——服务器**主动**通过 `_meta.otel` 把 OTLP `resourceSpans` 塞回响应，**audit 拼图的"反向腿"**（客户端发 `traceparent` SEP-414 已稳）；**SEP-2787** tool call attestation / **SEP-2809** ATSA / **SEP-2828** Server-Side Signed Execution Record / **SEP-2672** Per-Call Passkey Verified Approval——"调用全链路证据化"四件套；**SEP-1913** Trust and Sensitivity Annotations——tool 自带"信任级别 + 敏感度"标签，配合 SEP-2817 后审计日志**自动**含 trust tier；**SEP-2385** Tool Auth Manifest——tool 维度声明"需要哪些凭据才能调用"，与 SEP-2817 联动可生成"用凭据 X 调了 trust-tier Y 的 tool，原因是 Z，模型是 W"完整审计事实。

## 六、生产侧：基础设施级"零留存"工程实践

- **Docker `mcp-gateway` PR #497**（**5/27**，tuna-docker）：`pkg/secretsscan/secrets_test.go` 字面量同时命中 **GitHub PAT** 与 **Docker PAT** 正则，GitHub secret-scanning **把仓当泄露源**且 push-protection 永久阻止类似 push。解法：`strings.Repeat` 把 `ghp_` / `dckr_pat_` 前缀+padding 在**运行时**组装，源码不再有完整 token 形状字面量。**字面测试数据**本身是 secret-scanning 盲区，会污染所有下游审计（cache / 日志 / replica）——与上一轮 Helicone 故事同源，工程成本极低但挡住了一个潜在多年才会被发现的"全平台 secret scanner 误报"。  
- **Cloudflare `mcp-server-cloudflare` PR #358**（**6/1**）：从 Semgrep Pro **回退到 Semgrep CE**，CI 加 `semgrep==1.160.0 --config=auto` workflow，**不阻塞**（findings 仅 informational），`actions/cache@v5` 缓存 pip，`ubuntu-slim` + `contents: read` 最小权限。**每 PR 跑 SAST，findings 写仓内 GHAS，不外发任何第三方平台**——本身就是"审计全留仓"的范例。配合 **PR #386** `upgrade @cloudflare/workers-oauth-provider 0.4.0 → 0.7.0`——同步锁紧 17 个 OAuth-enabled MCP server 的 provider 依赖，证明 OAuth 是 Cloudflare **Tier 1 必修项**。  
- **Microsoft `mcp` PR #2690**（**6/4**）：`EnterpriseMCP` 进官方 catalog（Learn 与 Sentinel 之间）；PR #2801 / #2802 / #2811 统一 Storage、Compute、Skill 引用治理；**PR #2781**（**6/2**）"Prevent CI CLI usage from capturing telemetry"——**CI 跑的 CLI 不允许上传 telemetry**。含义：微软正式把"企业级 MCP 部署"提到 1L 位置，未来 Azure API Management / Entra ID / App Configuration 都会把 MCP 纳入一等公民。

## 七、对 AI Gateway 团队本周三件可落地的事

1. **实现 `cacheScope` 翻译层**：在 `tools/list` / `resources/list` / `prompts/list` / `resources/read` cache key 里按 `private` 划租户墙；`server/discover` 用 `ttlMs` 启用 TTL，不再全量重握。  
2. **审计日志 schema 对齐 SEP-2817**：把 `_meta.io.modelcontextprotocol/aiInvocation` 透传到 access log；`turnId` 注入 trace span tag——零侵入兼容现有 SDK。  
3. **参考 Cloudflare Semgrep CE 模板改造 CI**：SAST 强制 PR（informational-only），findings 全留仓；SDK 依赖钉 commit SHA（参考 docker mcp-gateway 那批 bake-action SHA pin PR）。

## 八、本期数字摘要

spec 仓 48h 合并 30 commits，4/5 实质性 PR 与治理 / 缓存 / 审计相关；Registry 仓 5 天 8 commits（错误卫生 #1338 / #1335、Cargo SSRF #1330、Cargo validator #1207）；SEP 池 open：2817 / 2787 / 2809 / 2828 / 2672 / 2448 / 2385 / 1913；厂商：Docker #497、Cloudflare #358/#386、Microsoft #2690/#2781。

## 引用与数据来源

- spec 仓 48h commits：https://api.github.com/repos/modelcontextprotocol/modelcontextprotocol/commits?since=2026-06-04T00:00:00Z
- PR #2855 server/discover cacheable：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2855
- PR #2843 Authorization IG charter：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2843
- PR #2863 SEP-to-spec consistency：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2863
- SEP-2817 AI Invocation Audit Context：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2817
- Discussion #2704：https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/2704
- SEP-2448 server execution telemetry：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2448
- SEP-2787 tool call attestation：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2787
- SEP-2809 ATSA：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2809
- SEP-2828 server-side signed execution record：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2828
- SEP-2672 per-call passkey verified approval：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2672
- SEP-1913 trust and sensitivity annotations：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1913
- SEP-2385 tool auth manifest：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2385
- Registry 5 天 commits：https://api.github.com/repos/modelcontextprotocol/registry/commits?since=2026-06-01T00:00:00Z
- Registry PR #1338 CWE-209：https://github.com/modelcontextprotocol/registry/pull/1338
- Registry PR #1335 499 取消卫生：https://github.com/modelcontextprotocol/registry/pull/1335
- Registry PR #1330 Cargo SSRF：https://github.com/modelcontextprotocol/registry/pull/1330
- Docker mcp-gateway PR #497 secretscan fixture：https://github.com/docker/mcp-gateway/pull/497
- Cloudflare PR #358 Semgrep CE：https://github.com/cloudflare/mcp-server-cloudflare/pull/358
- Cloudflare PR #386 OAuth provider 0.4→0.7：https://github.com/cloudflare/mcp-server-cloudflare/pull/386
- Microsoft PR #2690 EnterpriseMCP：https://github.com/microsoft/mcp/pull/2690
- Microsoft PR #2781 CI 不发 telemetry：https://github.com/microsoft/mcp/pull/2781
- 上一轮 MCP（不重复）— SDK 可靠性 `reports/2026-06-05-2253-aigw-mcp-sdk-reliability.md`、spec IA 重构 `reports/2026-06-05-2211-aigw-mcp-spec-ia-refactor.md`
