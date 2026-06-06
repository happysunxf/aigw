# AI 网关深挖 · MCP Gateway 专题（2026-06-06 08:08 CST）

> 主题 1/8：MCP 协议演进 / **生产治理 · 认证规范重构**。  
> 上一轮（01:25）覆盖「审计 + 缓存隔离」，本轮聚焦过去 48h MCP 主仓最重磅的协议层落地——**Authorization 规范拆分（PR #2858）+ DCR 正式 deprecate + CIMD 升为推荐客户端注册机制**。这是 MCP 自 2025-11-25 修订以来认证面最系统的范式重组。

## 一、本轮一句话论点

**MCP 把「Dynamic Client Registration（RFC 7591）」从"可选"明确降级为"Deprecated"，把「Client ID Metadata Documents (CIMD)」升为推荐客户端注册机制，配套把单文件 894 行的 `authorization.mdx` 拆成 4 个子页面（943 行净新增）。** 对 AI Gateway 而言：过去按"接受 DCR 注册请求 → 持久化 client_secret → 颁发 access_token"这条主线设计的 Auth Server 适配层需要重写——CIMD 模式下 client 不再向你注册，而是把 metadata 文档**托管在自己控制的 HTTPS URL** 上，你**只是 fetch + 校验**。本轮还把 SEP-2742（server.json 声明 auth 块）、Inspector v0.22.0、SDK 侧 5 个仓库同步跟随——**"auth spec 拆分"是这一周 MCP 的主旋律**。

## 二、协议主仓时间线（5/30 → 6/5）

| 时间 (UTC) | PR | 标题 | 净增/删 | 含义 |
|---|---|---|---|---|
| 6/4 13:05 | **#2843** | Add Authorization IG charter | +87/-0 | Auth IG 三 facilitator（Okta / Amazon / Anthropic）成宪 |
| 6/4 19:16 | **#2858** | Authorization spec split | +951/-895, 6 files | **主菜**：authorization.mdx 拆 4 文件 |
| 6/5 10:52 | **#2862** | Update auth spec structure/callouts | +91/-55, 6 files | 紧跟 #2858，链接归位 |
| 6/5 16:11 | **#2863** | sep-to-spec consistency pass | +101/-28, 18 files | SDK tier 降级规则、deprecation SEP 化 |
| 6/5 16:14 | #2865 | fix dead Python auth sample link | +1/-1 | 修死链 |

7 天 6 个 PR 命中 auth spec 主线，#2858 体量最大——**894 行单文件 → 4 个语义清晰子页面**。

## 三、Authorization 规范拆分（#2858）拆解

### 3.1 新文件结构

```
docs/specification/draft/basic/authorization/
├── index.mdx                       (421 行)  Overview + Roles + Standards
├── authorization-server-discovery.mdx  (165 行)  AS 发现 + PRM (RFC 9728)
├── client-registration.mdx         (201 行)  CIMD 优先 + DCR deprecate
└── security-considerations.mdx     (155 行)  Token 绑定 + PKCE + CIMD 安全
```

原 `authorization.mdx`（894 行）删除。sidebar 重排，#2865 必须修旧链接。

### 3.2 CIMD vs DCR：协议层的范式转移

新 `client-registration.mdx` 把**注册方式**分两档定优先级：

| 优先级 | 方式 | 状态 | I-D 来源 |
|---|---|---|---|
| 1 | **预共享 static credentials** | 始终首选 | 企业 IdP 流程 |
| 2 | **Client ID Metadata Documents (CIMD)** | SHOULD 优先 | `draft-ietf-oauth-client-id-metadata-document-00` |
| 3 | **Dynamic Client Registration (RFC 7591)** | **Deprecated** | RFC 7591 |

CIMD wire 行为：`client_id` 本身就是 client 控制的 HTTPS URL（`https://app.example.com/oauth/metadata.json`），AS 认证前**主动 fetch** 该 URL，**MUST** 校验 `client_id` 字段值与 URL 字符串完全一致。AS 通过 OAuth AS Metadata 的 `client_id_metadata_document_supported: true` 声明支持 CIMD。

**对比 DCR 的根本差异**：
- **DCR**：client → AS `POST /register` → AS 颁发 `client_id` + `client_secret` → AS 持久化
- **CIMD**：client 自报 `client_id`（= URL） → AS fetch URL → 校验内容 → 不持久化

→ AS 侧**从"持久化 + 颁发"角色退化为"fetch + 校验"角色**。含义：

1. **持久化攻击面消失**——DCR 模式下 AS 的 `client_registry` 表 / 凭据库 / 删除流程是 P0 攻击面（参考 2025 年 Okta DCR 越权事件）。CIMD 模式下 AS 不持久化 client，攻击面归零。
2. **client_secret 消失**——CIMD 推荐 `token_endpoint_auth_method=none`（public client），依赖 redirect_uri 严格匹配 + PKCE。AS 不再管理 client 凭据生命周期（rotation、revoke）。
3. **新引入 SSRF 风险**——AS fetch `client_id` URL，必须做：私网地址黑名单 + DNS rebinding 防御 + 超时 + 大小限制 + HTTP cache 缓存。
4. **多 AS 多 client 隔离**——同 client 跨 AS 不可移植，符合 #2863 的 SEP-2352。

### 3.3 `iss` 验证升 SHOULD + MUST（SEP-2468）

`changelog.mdx` Minor #7：AS SHOULD include `iss` in authorization response per RFC 9207, and MCP clients MUST validate a present `iss` against the recorded issuer before redeeming the authorization code。

→ **授权码注入（mix-up）攻击的协议层硬防**。AS 不返回 `iss` 时 client 仍可继续（向后兼容），但 AS 主动返回了却对不上就拒绝。

### 3.4 Token Audience Binding（RFC 8707）强约束

`security-considerations.mdx`：MCP clients MUST include the `resource` parameter in authorization and token requests. MCP servers MUST validate that tokens presented to them were specifically issued for their use.

→ **`resource` 从可选项升 MUST 项**。多 AS 共享 IdP 时阻止"用 server A 的 token 调 server B"的 confused-deputy。

## 四、SEP-2742：server.json 声明 auth 块（直接互补）

**状态**：open · 5/19 开 · 6/3 更新 · 2 评论。

**核心提案**：给 `server.json` 和 Server Cards (SEP-2127) 加 `auth` 块，让**远程 MCP server 在客户端第一次请求前**声明认证方式——这正好是 RFC 8414 / RFC 9728 discovery **说不清**的领域。

5 个声明维度：
1. **认证姿态** `none` / `optional` / `required` —— 客户端要不要在 `initialize` 前先认证，还是 lazy 401 后再认证。
2. **方法菜单** —— OAuth 或 static-header（或两者）。
3. **OAuth 注册模式** `dynamic` (DCR) / `client-metadata` (CIMD) / `static`——**正好对应本轮新规范的优先级**。
4. **Client 凭据类型** `none` / `client_secret` / `private_key_jwt` / `tls_client_auth`。
5. **带外 AS 端点** —— 对那些**不发布 `.well-known/oauth-authorization-server`** 的现实 AS（如多租户 IdP），声明 fallback 端点 + same-origin + validation 防 IdP Mix-Up。

**与本轮 #2858 咬合**：
- #2858 定义**协议层**认证流程（怎么注册、怎么发现、怎么校验 token）。
- SEP-2742 定义**发布层**认证声明（server 在 metadata 里**预先告诉**客户端它支持哪种）。
- 两者**同期落地**——MCP 把"auth 治理"系统化的一次协同。

## 五、Inspector v0.22.0（6/4 12:36 UTC）

[Release 0.22.0](https://github.com/modelcontextprotocol/inspector/releases/tag/0.22.0) —— 4 项 CI/安全 + 1 项新功能 + 1 项发版：

- **PR #1199** `ci: switch npm publish to OIDC trusted publishing` —— npm 发布改 OIDC trusted publishing，**撤销长期 npm token**。与上轮 04:50 提到的 guardrails-ai CVE-2026-45758（5/11 token 投毒）形成"上游预防 / 下游加固"双轨。
- **PR #1270** `ci: gate claude.yml on author_association` —— **限制 Claude Code 自动化 PR 只能由 maintainer 触发**，防 GitHub Action 投毒（tj-actions/changed-files 同型）。
- **PR #1380** `npm audit fix for transitive security advisories` —— 修 transitive 漏洞。
- **PR #1423** `feat: add URL-mode elicitation support` —— 与 SEP-2322（MRTR）`inputRequests/inputResponses` 对应的**用户侧能力**。

## 六、SDK 侧同步（5/30–6/5）

| 仓库 | PR | 关键变更 |
|---|---|---|
| **rust-sdk** | [#883](https://github.com/modelcontextprotocol/rust-sdk/pull/883) | feat: specify OIDC application_type during dynamic client registration (SEP-837) |
| **rust-sdk** | [#884](https://github.com/modelcontextprotocol/rust-sdk/pull/884) | feat: deprecate roots, sampling, and logging (SEP-2577) |
| **go-sdk** | [#969](https://github.com/modelcontextprotocol/go-sdk/pull/969) | auth: add ClockSkew option to RequireBearerTokenOptions（防时钟漂移导致 token 误拒） |
| **python-sdk** | [#2773](https://github.com/modelcontextprotocol/python-sdk/pull/2773) | Fix stdio client shutdown bugs and rebuild the stdio test suite |
| **csharp-sdk** | [#1600](https://github.com/modelcontextprotocol/csharp-sdk/pull/1600) | Require Tool inputSchema during deserialization（SEP-2106） |
| **csharp-sdk** | [#1599](https://github.com/modelcontextprotocol/csharp-sdk/pull/1599) | Add McpClientOptions.InitializeMeta（SEP-2575 stateless 适配） |
| **java-sdk** | [#995](https://github.com/modelcontextprotocol/java-sdk/pull/995) | fix: avoid dropped errors when transport is closed |

**rust-sdk 表现最积极**——SEP-837 + SEP-2577 **同周落地**，比 spec 主仓更激进。csharp-sdk 在追 SEP-2575 stateless。go-sdk 给 Bearer 校验加 `ClockSkew`——**实现层补完"协议 MUST 校验 token"**的细节。

## 七、对 AI Gateway 团队本轮四件可落地的事

1. **Auth Server 适配 CIMD 优先**：AS metadata 加 `client_id_metadata_document_supported: true`；实现 fetch + 校验 + HTTP cache；对 `client_id` URL 做 SSRF 黑名单（私网/loopback/link-local/169.254/100.64/6to4）+ DNS 解析时锁 IP + HTTPS 证书强校验。
2. **DCR 路径标 deprecated 但保留**：新 client 引导走 CIMD；历史 DCR client 12 个月宽限期（SEP-2596 政策），宽限期内 MUST 仍工作。
3. **`iss` + `resource` 双校验**：(a) AS 颁发时 authorization response 加 `iss`；(b) client MUST 校验 `iss` 与"最初记录的 issuer"一致；(c) token request MUST 带 `resource`；(d) AS MUST 校验 resource 与本 server 的 audience 一致。
4. **Server Card / server.json 提前声明 auth**（SEP-2742）：本仓库若发布 public MCP server，加 `auth` 块声明 `registrationMode=client-metadata` + `authMethod=none` + `audience=<canonical URL>`，让客户端第一次 `initialize` 前就预知认证要求，避免 lazy 401 触发的 2 次 RTT。

## 八、本轮未覆盖的相邻话题（提示下一轮）

- **MCP-2026-07-28 RC 倒计时 52 天**：上轮 15:28 覆盖"7 大 major changes"。本轮 #2863 是 RC 前最后一致性清扫。
- **MCP-Inspector v0.23+** 可能接入 `subscriptions/listen`（SEP-2575）。
- **MCP Registry / Server Card 治理**（SEP-2127）—— 与 SEP-2742 联动，给 Registry 提供"已声明 CIMD 支持的 server 优先被收录"能力。

## 引用与数据来源

**MCP 主仓 spec**
- PR #2858 — https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2858
- PR #2862 / #2863 / #2865 / #2843 — `…/pull/{2862,2863,2865,2843}`
- 新 auth spec：`docs/specification/draft/basic/authorization/{index,client-registration,authorization-server-discovery,security-considerations}.mdx`
- changelog — `…/docs/specification/draft/changelog.mdx`
- SEP-2742 — `…/issues/2742`
- SEP-2468 / 837 / 2352 / 2577 / 2106 / 2596 / 2127 — `…/pull/{2468,837,2352,2577,2106,2596,2127}`

**MCP Inspector**
- v0.22.0 — https://github.com/modelcontextprotocol/inspector/releases/tag/0.22.0

**SDK 同步**
- rust-sdk #883 (SEP-837) — https://github.com/modelcontextprotocol/rust-sdk/pull/883
- rust-sdk #884 (SEP-2577) — `…/rust-sdk/pull/884`
- go-sdk #969 (ClockSkew) — `…/go-sdk/pull/969`
- python-sdk #2773 (stdio) — `…/python-sdk/pull/2773`
- csharp-sdk #1600 / #1599 — `…/csharp-sdk/pull/{1600,1599}`
- java-sdk #995 — `…/java-sdk/pull/995`

**RFC / I-D**
- RFC 8707 Resource Indicators — https://www.rfc-editor.org/rfc/rfc8707.html
- RFC 9207 Issuer Identification — https://datatracker.ietf.org/doc/html/rfc9207
- RFC 9728 Protected Resource Metadata — https://datatracker.ietf.org/doc/html/rfc9728
- CIMD I-D — https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00
- MCP blog RSS — https://blog.modelcontextprotocol.io/index.xml
