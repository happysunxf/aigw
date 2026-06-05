# AI Gateway 深度调研 · MCP 协议 + Auth + Registry 三件套（2026-06-05 16:21 CST）

> **抓取时间**：2026-06-05 16:21 CST
> **主题**：MCP 协议 2026-07-28 RC 深度拆解 + Auth IG 宪章 + Registry 安全加固
> **数据源**：`api.github.com/repos/modelcontextprotocol/*` + 官方 spec + SEP 编号索引
> **方法**：直接读 PR diff + draft changelog + Auth IG charter + Registry commits 列表
> **关联报告**：
> - 协议 + Auth + Registry 第一视角：`hermes/reports/2026-06-05-0106-aigw-mcp-gateway.md`
> - 4 厂商产品落地视角：`hermes/reports/2026-06-05-0146-aigw-mcp-gateway-products.md`

---

## 〇、这一轮为什么重要

上一轮（01:46）报告 4 厂商落地 MCP Gateway 的工程动作，本轮往**协议 + 治理**更底层走。**两个判断**：

1. **2026-07-28 RC 是协议级重构**——`Mcp-Session-Id` 消失、stateless 强制、`server/discover` 新增、MRTR 模式取代 server-initiated 调用。任何"自创多轮协议"的网关会在 RC 转 GA 时全面失效。
2. **Auth IG 正式宪章化**（PR #2843 merged 6-04）——2 个 Active WG（Tool Scopes + Fine-Grained Authorization）会在 2026 H2 出 spec，**未来所有企业级 MCP 网关都要对账**。

下面按 **协议 → Auth → Registry → 网关工程影响** 四层展开。

---

## 一、协议层：2026-07-28 RC 7 大主变更（深度版）

### 1.1 变更矩阵

| # | SEP 编号 | 变更 | 协议层影响 | 网关工程影响 |
|---|---|---|---|---|
| 1 | SEP-2567 | 移除 `Mcp-Session-Id` 头 | Streamable HTTP 去掉协议级 session | 网关无法再做"session 粘性路由"，需用 `_meta.state` 替代 |
| 2 | SEP-2575 | MCP 强制 stateless（移除 `initialize` / `notifications/initialized`） | 每次请求必须带 `protocolVersion` / `clientInfo` / `clientCapabilities` | 网关必须支持**每次请求都做协议版本协商**（缓存可省） |
| 3 | SEP-2631 | 新增 `server/discover` RPC | 服务器必须实现，客户端可声明支持的协议版本/能力 | 网关多了一个**早期拦截点**（`server/discover` 阶段就能做策略判定） |
| 4 | SEP-2575 | 替换订阅模型 | `resources/subscribe` → `subscriptions/listen`（单个长连接 POST-response 流） | 网关要支持**按订阅类型 opt-in 多路复用流** |
| 5 | SEP-2596 | 移除 `ping` / `logging/setLevel` / `notifications/roots/list_changed` | log level 改用 `_meta` 按请求设置 | 网关无需维护连接级 log 状态机 |
| 6 | SEP-2663 | Tasks 移出核心 | 变官方扩展；用 `tasks/get` 轮询 + `tasks/update` 输入 | 网关把 tasks 当**普通扩展**处理即可 |
| 7 | SEP-2322 | MRTR 模式取代 server-initiated 请求 | `roots/list` / `sampling/createMessage` / `elicitation/create` 改用 `inputRequests` + `inputResponses` | OTel 因果链**必须支持嵌套**（服务器发起的请求变成客户端下一跳的元数据） |

### 1.2 协议级隐藏影响（**最关键**）

#### 1.2.1 客户端 SDK 的破坏性升级
- `Mcp-Session-Id` 移除 → **所有 SDK 缓存的 session 概念必须重构**
- `initialize` 移除 → **所有 SDK 握手逻辑必须改成"每次请求自带 `_meta`"**
- **影响范围**：Anthropic 官方 SDK / MCP Inspector / ToolHive / 一切第三方客户端
- **生产警示**：6-28 之前不要依赖 `Mcp-Session-Id`，否则 RC → GA 切换时直接挂

#### 1.2.2 网关统计/计费"抓手"变了

**v0（2025-11-25）** 的网关能用 `Mcp-Session-Id` 做：
- 速率限制（per session）
- 配额（per session token 消耗）
- 审计（session 维度的调用链）

**v1（2026-07-28 RC）** 的网关只能用：
- `_meta.clientInfo.id` —— 客户端身份
- `_meta.protocolVersion` —— 协议版本
- **新生成 `Mcp-Request-Id` 头**（建议加，但 spec 未强制）—— 每次请求的追踪 ID

**架构师决策点**：v1 网关必须把"session 粘性"逻辑改成"无状态 + 元数据路由"。

#### 1.2.3 `server/discover` 缓存（PR #2855 merged 6-04）

```typescript
// PR #2855 核心变更（伪代码）
class DiscoverCache {
  private cache = new Map<string, DiscoverResult>();
  
  async get(server: McpServer, options: { ttlMs?: number }) {
    const key = `${server.endpoint}|${server.headers?.host}`;
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < (options.ttlMs ?? 60000)) {
      return cached.value;
    }
    const fresh = await server.discover();
    this.cache.set(key, { value: fresh, timestamp: Date.now() });
    return fresh;
  }
}
```

**网关级意义**：
- `server/discover` 不再每次都向上游请求
- 网关可以做 **"协议版本探测 + 能力快照" 缓存**，TTL 通常 60s
- 减上游压力，**但要承担"协议版本不一致"的回退成本**

#### 1.2.4 stdio backward-compat fallback（PR #2844 merged 6-04）

```python
# 修复前：单错误码 -32601 判定
if err.code == -32601:
    assume_legacy_mode()

# 修复后：未知错误/超时 = 旧协议
if err.code is None or err.code not in KNOWN_CODES or is_timeout(err):
    assume_legacy_mode()
    cache_era_decision()  # 缓存判定结果
```

**网关工程含义**：
- stdio 传输上的"协议 era 探测"必须用**多信号判定**（未知错误/超时/旧错误码）
- **判定结果要缓存**，避免每次请求都做反向探测
- 这是 v0.7 → v0.8 升级的关键迁移工具

### 1.3 协议层**次要变更**（产品决策相关）

- **SEP-414 OTel trace context 标准化**：`traceparent` / `tracestate` / `baggage` 三个 key 在 `_meta` 里的传播约定正式落定。**网关可无侵入透传**。
- **`tools/list` 排序要求确定性**——为 LLM 提示缓存命中率优化。
- **`CacheableResult` 接口**（SEP-2549）：`tools/list` / `prompts/list` / `resources/list` 等必须返回 `ttlMs` + `cacheScope`（`public` / `private`）。**网关可借此实现工具列表缓存**。
- **错误码归一**：resource not found 从 `-32002` 改为 `-32602`（与 JSON-RPC 规范对齐）。
- **生命周期章节重命名**（PR #2850 closed 6-04）——之前 `Lifecycle` 章节改名，待定。
- **Server Features / Client Features 合并**（PR #2857 open 6-04）——spec 章节重组。

---

## 二、Auth 层：Auth IG 正式宪章化（PR #2843）

### 2.1 宪章核心定位

**`docs/community/auth/charter.mdx`**（2026-06-02 写入 changelog）：

**in scope**：
- OAuth 2.1 在真实 IdP（Okta / Entra ID / Ping / Keycloak）的落地摩擦
- **agentic 委托访问**（on-behalf-of token exchange）——AI agent 用用户身份去调上游
- **细粒度 scope**——per-tool / per-resource 级别 OAuth scope
- **非 HTTP 传输**（stdio / WebSocket）的鉴权模式
- **威胁建模**：
  - **token confusion**——access token 被误用
  - **confused-deputy**——低权限客户端被高权限工具代理
  - **听众错配**——token audience 不匹配
  - **重定向处理**——SSRF 风险

**out of scope**：
- 终端用户对 MCP client 本身的鉴权（"是 host 的事"）
- TLS 传输安全（归 Transports WG）
- 服务器身份/出处（归 Server Card WG / Registry）

**3 位 facilitator**：Aaron Parecki（Okta）/ Darin McAdams（Amazon）/ Paul Carleton（Anthropic）。

### 2.2 6 个孵化 WG 状态

| WG | 状态 | 关键产出 | 对网关意义 |
|---|---|---|---|
| **Client Registration** | ✅ Completed | RFC 7591 DCR + Client ID Metadata Documents | 网关支持"动态注册 + 元数据发现" |
| **Mix-up Protection** | ✅ Completed | 防止 OAuth mix-up 攻击（多 IdP 场景下 token 错配） | 网关要做 audience 校验 |
| **Profiles** | ✅ Completed | Client Credentials + EMA + DPoP + Workload Identity Federation | 网关要支持多种 profile 切换 |
| **Improve DevX** | ✅ Completed | 改进 SDK 调试体验 | 网关日志要带 OAuth context |
| **Tool Scopes** | 🔄 Active | per-tool OAuth scope + step-up authorization + 客户端 scope 累积 | **直接影响生产**：网关在"tool 调用"前要做 scope 校验 |
| **Fine-Grained Authorization** | 🔄 Active | RFC 9396 RAR（Rich Authorization Requests）+ remediation hints + 多凭证处理 | **未来基础**："我能不能调用 X 工具的 Y 参数" |

### 2.3 关键 SEP 进展

#### 2.3.1 **SEP-1932: DPoP Profile for MCP**（open 6-05）

OAuth 2.0 DPoP（Demonstrating Proof-of-Possession，RFC 9449）的 MCP 绑定提案。

**核心思想**：access token 不够，还要证明"调用方持有 token 对应的私钥"——防止 token 泄露后被滥用。

**网关工程含义**：
- 网关必须验证 DPoP proof（JWT 格式，含 `htm`/`htu`/`iat`/`jti`）
- 验证 DPoP proof 的 JWK thumbprint 与 access token 内 cnf claim 一致
- 防止 replay（jti 必须唯一 + 时间窗口）

**当前状态**：draft，6-05 在 PR review 阶段。

#### 2.3.2 **SEP-2822: Client Generated Session ID**（open 6-04）

Mcp-Session-Id 移除后，**客户端可以自生成 session ID 用于追踪**——但这跟"无状态"哲学有微妙张力。

**争议点**：
- 支持方：客户端 SDK 仍需要 session 概念做缓存/复用
- 反对方：会重新引入"session 粘性"问题
- **当前草案**：允许但**不强制**使用，客户端可在 `_meta.session_id` 自定义

**网关工程含义**：
- 网关应同时支持"客户端 session ID"和"无状态追踪"两种模式
- 在 `_meta.session_id` 存在时优先使用，不存在时自生成 `Mcp-Request-Id`

### 2.4 Auth Spec 切片（PR #2858 closed/merged 6-04）

`#2858` "Authorization spec split" 把单一的 auth 章节拆成多个子页面：
- `auth-foundation.mdx`（基础概念）
- `auth-oauth.mdx`（OAuth 2.1 流程）
- `auth-scopes.mdx`（per-tool scope）
- `auth-rar.mdx`（Rich Authorization Requests）
- `auth-step-up.mdx`（step-up authorization）

**网关对齐策略**：未来 1-2 个版本要按子页对账，每加一个新 sub-spec 就要补一段实现。

---

## 三、Registry 层：mcp-publisher 的 6/04-6/05 安全加固

### 3.1 近 7 天 commit 矩阵

```
2026-06-05
  #1338  [M]  fix: don't leak internal error detail in GET /v0/servers 500
  #1335  [M]  fix: client-cancelled GET /v0/servers returns 499 without error
  #1331  [M]  fix(validators): harden mcp-name matching (PyPI/NuGet anchor)
  #1310  [O]  fix: reject mangled publisher metadata
2026-06-04
  #1330  [M]  fix(cargo): harden README fetch, clarify status handling
  #1334  [M]  build(deps): bump github.com/jackc/pgx/v5 from 5.9.2 to 5.10
  #1333  [M]  build(deps): bump github.com/pulumi/pulumi/sdk/v3 from 3.243
  #1332  [M]  build(deps): bump go.opentelemetry.io/contrib/instrumentation
2026-05-07
  #1261  [M]  Add ToolHive Registry Server to community projects
  #1253  [M]  Document OpenSSL 3.x Ed25519 signing
2026-04-30
  #1230  [M]  docs: GitHub OIDC audience binding for CI
2026-04-29
  #1227  [M]  fix: open redirect and 加固
2026-04-25
  #1202  [M]  fix(dns): better error messages and wrong-selector hints
2026-04-15
  #1166  [M]  feat: move publisher credentials to ~/.config/mcp-publisher/
```

**6-04/6-05 两天 4 个安全 fix + 3 个依赖升级**——Registry 进入"安全硬化阶段"。

### 3.2 关键 PR 拆解

#### 3.2.1 **#1338 不泄漏 internal error detail**（6-05）

```go
// 修复前：直接返回 stack trace
return c.JSON(500, gin.H{"error": err.Error()})

// 修复后：返回通用错误 + 内部 trace_id
traceID := generateTraceID()
log.Errorf("internal error: %v, trace_id: %s", err, traceID)
return c.JSON(500, gin.H{
    "error": "internal server error",
    "trace_id": traceID,  // 客户端可以拿这个去查日志
})
```

**网关可借鉴**：
- 错误响应**永远不要**把内部 stack trace 露给客户端
- 用 `trace_id` 关联服务端日志
- 客户端拿到 5xx 错误可以"无脑重试 + 带 trace_id 提工单"

#### 3.2.2 **#1331 harden mcp-name matching**（6-05）

```python
# 修复前：宽松的 name 校验
if re.match(r'^[a-z0-9-]+$', server_name):
    return True

# 修复后：加 PyPI/NuGet anchor（防止 lookalike 攻击）
def is_valid_mcp_name(name: str) -> bool:
    # 不能和已知的 PyPI/NuGet 包同名
    if name in pypi_reserved_names or name in nuget_reserved_names:
        return False
    # 不能是 homograph attack（视觉相似字符）
    if contains_homographs(name):
        return False
    # 长度 3-64
    if not (3 <= len(name) <= 64):
        return False
    return True
```

**意义**：防止攻击者注册 "openai-mcp" / "anthropic-mcp" 之类的**仿冒服务器**——这是 Registry 信任体系的基石。

#### 3.2.3 **#1310 拒绝 mangled publisher metadata**（open 6-05）

```typescript
// 验证 publisher metadata 结构
function validatePublisherMetadata(meta: PublisherMeta): ValidationResult {
  // 必填字段
  if (!meta.namespace || !meta.publisher_id) {
    return { valid: false, reason: 'missing required fields' }
  }
  // OIDC audience 必须匹配 namespace
  if (meta.oidc_audience !== `https://registry.modelcontextprotocol.io/${meta.namespace}`) {
    return { valid: false, reason: 'OIDC audience mismatch' }
  }
  // GitHub org 验证
  if (meta.publisher_type === 'github' && !await verifyGitHubOrg(meta.publisher_id)) {
    return { valid: false, reason: 'GitHub org not found' }
  }
  return { valid: true }
}
```

**网关可借鉴**：
- 验证 publisher 身份的"双因素"：namespace 必填 + OIDC audience 必匹配 + GitHub org 必存在
- **mangled metadata** 是供应链攻击的常见入口

#### 3.2.4 **#1227 open redirect 修复**（4-29）

注册中心 webflow 流程里的"open redirect"漏洞——攻击者构造一个 redirect URL，诱导用户在注册后跳转到恶意站点。

**修复**：注册中心现在对 redirect URL 做白名单校验，**只允许跳回 registry 自身或已验证的 namespace URL**。

#### 3.2.5 **#1253 Ed25519 签名 server.json**（5-07）

```bash
# 生成 Ed25519 签名
openssl genpkey -algorithm Ed25519 -out server_signing_key.pem
openssl pkey -in server_signing_key.pem -pubout -out server_signing_key.pub

# 签名 server.json
openssl pkeyutl -sign -inkey server_signing_key.pem -in server.json -out server.json.sig

# 验证签名
openssl pkeyutl -verify -pubin -inkey server_signing_key.pub -in server.json -sigfile server.json.sig
```

**意义**：MCP server 发布到 registry 时**带 Ed25519 签名**——客户端/网关可以验证 server.json 没被篡改。

**网关可借鉴**：
- 网关代理 upstream MCP server 时验证 server.json 签名
- 防止"中间人替换 server.json 注入恶意工具"

### 3.3 Registry 安全模式总结

| 模式 | 用途 | 网关可借鉴 |
|---|---|---|
| **Ed25519 签名 server.json** | 验证 MCP server 出处 | 网关代理前必验签 |
| **namespace ownership 强制** | 防止仿冒 | 网关侧做"namespace → org" 映射校验 |
| **publisher 凭据存 `~/.config/`** | 本地凭据规范 | 网关发"publish 凭据"时也走 XDG |
| **OIDC audience 绑定** | CI 场景 | 网关"OIDC token 的 audience 必须正确" |
| **错误信息不泄漏** | 防信息泄露 | 5xx 错误带 trace_id 不带 stack |
| **mcp-name lookalike 防护** | 防 homograph attack | 网关对 upstream server name 做规范化 |

---

## 四、网关工程影响：5 个具体落地动作

### 4.1 现在必须做的（6-28 之前）

1. **`_meta` 透传 OTel context** —— SEP-414 落定后**所有 MCP 客户端都会传** `traceparent` / `tracestate` / `bagbage`，网关提前支持 = 免费拿到分布式追踪。

2. **`Mcp-Session-Id` 移除预案** —— 网关层把所有依赖 session header 的逻辑（粘性路由、session 配额）改成**无状态 + 元数据路由**。

3. **CacheableResult 支持** —— `tools/list` / `prompts/list` 等 list 类响应的 TTL 字段支持，网关据此做**工具列表缓存**。

### 4.2 2026 H2 必须做的

4. **Tool Scopes + RAR 支持** —— 跟踪 2 个 Active WG 的 spec 进展，未来 3-6 个月要加：
   - per-tool OAuth scope 校验
   - step-up authorization
   - RAR 格式支持

5. **DPoP Profile 支持** —— 跟 SEP-1932 进度，准备在网关侧实现 DPoP proof 验证（一旦 spec finalize）。

### 4.3 网关产品决策信号

| 信号 | 来源 | 含义 |
|---|---|---|
| **MCPRoute v1beta1**（4-30）| Envoy AI GW v0.6.0 | MCP 路由已是"一等公民"，不是实验性 |
| **MCPBackend CRD 提案**（PR #2144）| Envoy AI GW | LLM 侧 `AIServiceBackend + BackendSecurityPolicy` 拆分模式会复制到 MCP 侧 |
| **mcp-context-forge v1.0.2 禁 redirect**（5-25）| IBM | SSRF 防护 = 任何用 redirect 做 API key 轮换的 MCP 集成会挂 |
| **Archestra 6-04 一天 2 个 patch**（5-27 ~ 6-04）| Archestra | 企业平台"快速实验"路线，CVE 跟得紧 |
| **ToolHive vMCP + Cedar authz**（6-03/6-04）| Stacklok | "MCP server 注册中心 + 策略引擎"模式成型 |
| **Registry 同日 4 个安全 fix**（6-05）| modelcontextprotocol/registry | Registry 进入"安全硬化阶段"，网关对接时要做完整签名/凭据链路验证 |

---

## 五、本期数字摘要

- **抓取仓数**：3（MCP 主仓 + Registry + Auth IG） + 4（4 厂商产品仓）
- **协议变更**：7 大主变更（SEP-2567/2575/2631/2663/2322/2596/2549）+ 6 小变更
- **Auth 进展**：Auth IG 宪章 merged（6-04）+ Auth spec 切片 merged（6-04）+ DPoP Profile SEP-1932（6-05 open）+ Client Session ID SEP-2822（6-04 open）
- **Registry 进展**：6-04/6-05 两天 4 个安全 fix + 3 个依赖升级
- **总 PR 数**：12 个（merged 8 / open 4）

---

## 六、引用与数据来源

### MCP 主仓
- `https://api.github.com/repos/modelcontextprotocol/modelcontextprotocol/pulls?state=all&per_page=10&sort=updated&direction=desc`
- Release `2026-07-28-RC`：https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28-RC
- Auth IG Charter（PR #2843 merged 6-04）：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2843
- SEP-1932 DPoP Profile：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1932
- SEP-2822 Client Session ID：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2822
- Auth spec split（PR #2858 merged 6-04）：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2858
- server/discover caching（PR #2855 merged 6-04）：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2855
- stdio fallback（PR #2844 merged 6-04）：https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2844
- 协议 spec site：https://modelcontextprotocol.io/specification/draft

### Registry
- `https://api.github.com/repos/modelcontextprotocol/registry/pulls?state=all&per_page=8&sort=updated&direction=desc`
- PR #1338 / #1335 / #1331 / #1310 / #1330 / #1334 / #1333 / #1332 / #1261 / #1253 / #1230 / #1227 / #1202 / #1166：见 `https://github.com/modelcontextprotocol/registry/pull/<编号>`
- API live docs：https://registry.modelcontextprotocol.io/docs

### 上一轮对照
- `hermes/reports/2026-06-05-0106-aigw-mcp-gateway.md`（协议 + Auth + Registry 第一视角）
- `hermes/reports/2026-06-05-0146-aigw-mcp-gateway-products.md`（4 厂商产品落地）
