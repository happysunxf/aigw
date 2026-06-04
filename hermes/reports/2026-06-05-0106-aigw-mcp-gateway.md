# AI 网关持续深挖 · 第 1/8 轮 · MCP Gateway 专题

> **抓取时间**：2026-06-05 01:06 CST（UTC 2026-06-04 17:06）
> **主题**：MCP Gateway 专题 — MCP 协议演进、生产治理、安全（静态 API key / OAuth / 审计）
> **数据源**：`api.github.com/repos/modelcontextprotocol/*` + 官方 spec 文档 + 注册中心
> **方法**：直接读 RC release notes + draft changelog + Auth IG charter + 近 30 天 PR 列表，去噪整理

---

## 一、为什么这一轮聚焦 MCP Gateway

上一轮（2026-06-04）市场总览里已埋下伏笔：**"MCP Gateway" 已成为独立产品品类**（Portkey / TrueFoundry / Envoy AI Gateway / Higress 都有专门模块），但**协议本身正在大改**——2026-07-28 RC 是一次"协议级重构"（去掉 session、去掉 initialize 握手、tasks 改扩展），同时**授权治理从散件变成正式 IG**。如果网关产品不追这一波 spec 变更，企业部署会撞上一连串向后兼容问题。

---

## 二、2026-07-28 RC 是一次"协议级重构"

`tag 2026-07-28-RC`（cut 2026-05-29，目前仍是 RC）相对上一版 `2025-11-25` 的 **7 大主变更**（来自 draft changelog）：

| # | 变更 | 协议层影响 |
|---|---|---|
| 1 | **移除 `Mcp-Session-Id` 头**：Streamable HTTP 去掉协议级 session，list 端点不再随连接变化（SEP-2567） | 网关无法再用 session header 做"客户端粘性"路由 |
| 2 | **MCP 强制 stateless**：移除 `initialize`/`notifications/initialized` 握手（SEP-2575） | 每次请求必须自带 `protocolVersion` / `clientInfo` / `clientCapabilities` 三个 `_meta` 字段；版本不一致返回 `UnsupportedProtocolVersionError` |
| 3 | **新增 `server/discover` RPC**：服务器必须实现，声明支持的协议版本、capabilities、身份 | 客户端先探测再请求；stdio 上也用这个做向后兼容探测 |
| 4 | **替换订阅模型**：`resources/subscribe` 没了，改成 `subscriptions/listen` 单个长连接 POST-response 流（SEP-2575） | 网关必须支持"按订阅类型 opt-in"的多路复用流 |
| 5 | **移除 `ping` / `logging/setLevel` / `notifications/roots/list_changed`**；log level 改用 `_meta` 按请求设置 | 网关无需再维护连接级 log 状态机 |
| 6 | **Tasks 移出核心**：`io.modelcontextprotocol/tasks` 变成官方扩展；用 `tasks/get` 轮询 + `tasks/update` 输入；移除 `tasks/list`（SEP-2663） | 长时间任务不再是"特殊协议"而是"普通扩展" |
| 7 | **Multi Round-Trip Requests (MRTR) 模式** 取代 server-initiated 请求（`roots/list`、`sampling/createMessage`、`elicitation/create`）（SEP-2322） | 客户端不再被服务器"反向调用"；服务器用 `inputRequests` 声明所需信息，下一请求带 `inputResponses` |

**对网关架构师最重要的 3 个信号**：

1. **从"有状态连接"切到"无状态 + 元数据调用"**——`Mcp-Session-Id` 消失意味着网关做速率限制、配额、审计的**唯一抓手就是 `_meta` 里的 clientInfo + protocolVersion**。这与 LiteLLM 上轮引入的"OTEL span 带 team_metadata"思路一致。
2. **`server/discover` 让客户端能"先握手再工作"**——给网关多了一个**早期拦截点**：在客户端 discover 阶段就拒绝不符合策略的协议版本/能力组合，不必等到 `tools/call` 才发现远端不通。
3. **MRTR 模式把"server-initiated 调用"做成"客户端后续请求的元数据"**——这对网关追踪的损害是**因果链断裂**：`sampling/createMessage` 不再是独立 span，而是嵌在被调用方请求的下一跳里。OTEL 链路必须支持"嵌套因果"。

### 次要变更（产品决策也值得关注）

- **OpenTelemetry trace context 标准化**：`traceparent` / `tracestate` / `baggage` 三个 key 在 `_meta` 里的传播约定正式落定（SEP-414）——**网关可以无侵入透传**。
- **`tools/list` 排序要求确定性**——为 LLM 提示缓存命中率优化。
- **`CacheableResult` 接口**：`tools/list` / `prompts/list` / `resources/list` / `resources/read` / `resources/templates/list` 必须返回 `ttlMs`（毫秒）+ `cacheScope`（`public` / `private`）（SEP-2549）。
- **错误码归一**：resource not found 从 `-32002` 改为 `-32602`（与 JSON-RPC 规范对齐）。

---

## 三、Auth IG 正式成立 — MCP 授权治理进入"机构化"阶段

PR #2843（2026-06-04 merged，user: pcarleton @ Anthropic）把 `#auth-ig` 从 2025 中开始的"事实存在"变成**正式宪章化**的兴趣小组（IG）。

**3 位 facilitator**：Aaron Parecki（Okta）/ Darin McAdams（Amazon）/ Paul Carleton（Anthropic）。

**章程关键定位**（`docs/community/auth/charter.mdx`，2026-06-02 写入 changelog）：

- **in scope**：OAuth 2.1 在真实 IdP（Okta / Entra ID / Ping / Keycloak）的落地摩擦、agentic 委托访问（on-behalf-of token exchange）、细粒度 scope、非 HTTP 传输（stdio / WebSocket）的鉴权模式、威胁建模（token confusion / confused-deputy / 听众错配 / 重定向处理）。
- **out of scope**：终端用户对 MCP client 本身的鉴权（"是 host 的事"）、TLS 传输安全（归 Transports WG）、服务器身份/出处（归 Server Card WG / Registry）。
- **6 个孵化 WG**，4 个已 Completed：Client Registration（RFC 7591 DCR + Client ID Metadata Documents）/ Mix-up Protection / Profiles（Client Credentials + EMA + DPoP + Workload Identity Federation）/ Improve DevX。**2 个 Active**：Tool Scopes（per-tool OAuth scope + step-up）/ Fine-Grained Authorization（RFC 9396 RAR + remediation hints + 多凭证处理）。

**对网关的意义**：

- **Auth spec 已被切片**（PR #2858 open，"Authorization spec split"）——未来 auth 章节会拆成多个子页面，**MCP 官方推荐网关 + Auth server 双侧实现按子页对账**。
- **Tool Scopes WG 是最直接影响生产的 WG**：per-tool scope + step-up authorization + 客户端 scope 累积——直接把"53% 静态 API key"问题（上一轮提到的 Portkey 数据）推到 OAuth scope 模型。网关在"tool 调用"前要做 scope 校验。
- **Fine-Grained Authorization WG** 正在搞 RAR（Rich Authorization Requests, RFC 9396）——结构化声明"我要访问的对象/动作"。这是 MCP 未来"我能不能调用 X 工具的 Y 参数"细粒度决策的基础。

---

## 四、生产治理实战：ToolHive（Stacklok）的 Virtual MCP Server

`stacklok/toolhive` 仓库近 7 天 commit 列表（2026-05-28 ~ 06-04）展示**MCP Gateway 化最具体的工程动作**：

- **v0.29.1 release**（2026-06-04）
- **VirtualMCPServer（vMCP）核心接口和 Config 契约**（PR #5450，2026-06-03）——把多个 MCP server 抽象成一个虚拟 server
- **Cedar authz 中间件**接收 vMCP server name（PR #5448）——AWS Cedar 策略引擎接入 authz
- **BackendID 通过 advertising filter 传递**（PR #5452）——多 backend 时按 ID 路由
- **lazy mode + 延迟登录**（PR #5427 / #5429）——server 注册后才提示登录

**核心模式**：MCP Gateway 不再是"反向代理 + auth"，而是**"虚拟 server 注册中心 + 策略引擎 + 后端 backend 发现"**——这与"传统 API Gateway（Kong/Envoy）"的 service mesh 模式趋同，但承载的是 **AI 工具调用** 而非 HTTP API 调用。

---

## 五、Registry（mcp-publisher）的安全加固

`modelcontextprotocol/registry` 近 30 天 commit 显示**鉴权/凭据链路是生产化重点**：

- **fix: open redirect and 加固**（PR #1227，2026-04-29）——registry webflow 的 open-redirect 漏洞修复
- **DNS 验证错误信息和 wrong-selector 提示优化**（PR #1202，2026-04-25）
- **OpenSSL 3.x Ed25519 文档**（PR #1253，2026-05-07）——说明 registry 已经在用 Ed25519 签名 server.json
- **ToolHive Registry Server 加入 community projects**（PR #1261，2026-05-07）
- **GitHub OIDC audience binding 文档**（PR #1230，2026-04-30）——CI 场景下"OIDC token 的 audience 必须正确"
- **publisher 凭据改 `~/.config/mcp-publisher/`**（PR #1166，2026-04-15）——本地凭据不再散落项目根

**对 AI 网关的可借鉴模式**：
1. **签名 server.json**（Ed25519）——MCP registry 在用，未来"网关 ↔ MCP server" 之间的可信发布链条应基于此。
2. **namespace ownership 强制**——"想 publish 到某 namespace 必须证明拥有对应 GitHub org / OIDC audience"。网关代理 upstream MCP server 时也应做类似校验。
3. **publisher 凭据存 `~/.config/`**——AI 网关如果给用户发"publish 凭据"，也必须走 XDG 规范目录。

---

## 六、对企业的 5 个具体建议

1. **现在就用 `_meta` 透传 OTel context**——SEP-414 落定后，**未来所有 MCP 客户端/服务端都会传** `traceparent` / `tracestate` / `baggage`。网关提前支持 = 免费拿到分布式追踪。
2. **做"MCP server / 客户端 双面 gateway"**——server 侧代理加策略（tool call 白名单 + scope 校验 + step-up），client 侧做"凭据隔离"（每个 user / agent 一组 token）。ToolHive 的 vMCP 是参考实现。
3. **跟踪 2 个 Active WG**（Tool Scopes + Fine-Grained Authorization）——它们的标准一旦 finalize，2026 年部署的 MCP 网关都要补对。
4. **避免在 stdio 上做"严格 era 探测"**——PR #2844 修复了 stdio backward-compat fallback：单一错误码（`-32601`）判定 legacy 不可靠，应改为"未知错误 / 超时 = 旧协议" + **缓存 era 判定结果**。
5. **建立"53% 静态 API key"治理 backlog**——Portkey 数据不会自动消失，需要主动扫描自家 MCP server（grep / scanner），把每个静态 key 替换为 OAuth flow + scope + 审计日志。

---

## 七、本期数字摘要

- 抓取对象：**MCP 协议 spec + Auth IG + Registry + ToolHive** 4 个核心仓
- 关键事件：**2026-07-28 RC cut 5/29** + **Auth IG 宪章 6/2 落地** + **server/discover 缓存 PR 6/4 merged**
- 重点变更数：**7 大主变更 + 6 小变更 + 3 个 deprecation**
- Active 工作组：**2 个**（Tool Scopes / Fine-Grained Authorization）
- 网关生态可参考项目：**ToolHive v0.29.1**（Stacklok）

---

## 引用与数据来源

### MCP 协议主仓（modelcontextprotocol/modelcontextprotocol）
- Release `2026-07-28-RC`：https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28-RC
- Draft changelog（`docs/specification/draft/changelog.mdx`）：https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/draft/changelog.mdx
- Auth IG Charter（PR #2843 merged 2026-06-04）：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2843
- PR #2855（server/discover 缓存）/ #2844（stdio fallback）/ #2858（auth spec split, open）/ #2848（async approval SEP, open）/ #2841（error taxonomy SEP, open）/ #2850（rename Lifecycle, closed）：均见 `https://github.com/modelcontextprotocol/modelcontextprotocol/pull/<编号>`
- 协议 spec site：https://modelcontextprotocol.io/specification/draft

### Registry（modelcontextprotocol/registry）
- README：https://raw.githubusercontent.com/modelcontextprotocol/registry/main/README.md
- PR #1227 / #1202 / #1166 / #1253 / #1261 / #1230：均见 `https://github.com/modelcontextprotocol/registry/pull/<编号>`
- API live docs：https://registry.modelcontextprotocol.io/docs

### ToolHive（stacklok/toolhive）+ MCP Inspector
- ToolHive commits API：https://api.github.com/repos/stacklok/toolhive/commits
- ToolHive v0.29.1 release：https://github.com/stacklok/toolhive/releases/tag/v0.29.1
- MCP Inspector 0.22.0（2026-06-04）：https://github.com/modelcontextprotocol/inspector/releases

### 相关 SEP 编号（draft changelog 引用）
- SEP-2567 / SEP-2575 / SEP-2663 / SEP-2322 / SEP-2549 / SEP-2596 / SEP-2577 / SEP-414 / SEP-2243
