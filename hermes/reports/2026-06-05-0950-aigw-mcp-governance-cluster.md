# AI 网关持续深挖 · 1/8 轮 · MCP Gateway 专题（第 4 视角）

> **抓取时间**：2026-06-05 09:50 CST（UTC 2026-06-05 01:50）
> **主题**：cron 1/8 轮 MCP Gateway——**"生产治理" 集中落地期**：Auth IG 在 5 月底 / 6 月初把 5 个 SEP 同步 final，Registry 同步补 SSRF + 名字前缀混淆
> **不重复前 3 轮**：01:06 协议 + Auth IG 章程；01:46 Envoy/IBM/Higress/Archestra/Docker 五大产品；08:34 部署架构（4 模式 / schema migration / sidecar 身份）
> **数据源**：`api.github.com/repos/modelcontextprotocol/*` 30 天内 security/SEP/registry commits

---

## 一、本轮核心论点：2026-06-04 是 MCP "生产治理" 的协调日

30 天窗口里，**5 月是「零散 SEP」、6 月初是「集中落地」**。最关键的协调：

- **2026-06-04**：SEP-2350/2351/2352 + SEP-2207 + SEP-2468 文档化同步更新（5 个 PR 全 `closed`，全带 `final` + `auth` + `security` 标签）——Auth IG "周四 finalization"
- **2026-06-04**：Registry PR #1330 cargo 验证器 SSRF 硬化 + 共享 `containsMCPNameToken`；PR #1331 draft（PyPI/NuGet anchored match）；5 个 OTEL/Pulumi/pgx 依赖 bump
- 2026-05-17 SEP-2468（`iss` claim）closed；SEP-2395 (MCPS) 关闭又重开；SEP-2343 elicitation+auth 推 draft

> **关键信号**：**Auth IG 6/4 一次性把「AS 绑定 + well-known URI + step-up scope 累积 + OIDC refresh token + iss 验证」5 个 spec 切片同时 final**——MCP 的 OAuth 2.1 落地在 spec 层面**从「补丁式」变成「系统化」**。任何在 2026-03 之前赶工实现的 MCP 网关，6 月底前要全部对齐这 5 条。

---

## 二、5 个 SEP 一次性 final：MCP OAuth 2.1 落到"系统化阶段"

### 2.1 SEP-2350 · step-up scope 累积语义对齐 RFC 6750

`Runtime Insufficient Scope Errors` 实现之前模糊——服务端到底报"当前操作所需 scope"还是"历史授权 scope 并集"？

**新规则**：
- **服务端**：scope error 按 [RFC 6750 §3.1](https://datatracker.ietf.org/doc/html/rfc6750#section-3.1) 报**当前操作所需**的 scope
- **客户端**：`Step-Up Authorization Flow` 时把"之前请求过的 scope"和"本次被 challenge 的 scope"取**并集**重新发起授权
- `Protected Resource Metadata` 里把"authoritative"明确成"当前操作必须"

**对网关**：收到 403 `insufficient_scope` 时**不要替客户端做 scope 合并**——这是客户端逻辑；**scope 去重是必须的**。

### 2.2 SEP-2351 · 显式指定 RFC 8414 well-known URI 后缀

[RFC 8414 §3.1](https://datatracker.ietf.org/doc/html/rfc8414) 要求应用显式声明 well-known URI 后缀，MCP 之前没声明。

**新规则**：**MCP 使用 `oauth-authorization-server` 后缀**（RFC 8414 默认）；**MCP 不定义自己的应用级 well-known URI**。

**对网关**：在 spec 之上做"路径猜测"的网关都得收敛到**单一路径**——减少 AS 探针攻击面。

### 2.3 SEP-2352 · 授权服务器绑定 + 多 AS 注册状态隔离

MCP 客户端同时对接 Okta + Entra ID 时，凭据/注册状态跨 AS 串了会怎样？

**新规则**（3 条）：
1. **每个 AS 独立维护注册状态**（`SHOULD`）
2. **MUST NOT 假设跨 AS 凭据有效**（硬性）
3. 区分 DCR 预注册 client 和 CIMD：**DCR 凭据按 issuer 锁定**；**CIMD client_id 可移植**；AS 不匹配**必须 error**

**对网关**：做 AS 反向代理时**不能用单一 client 凭据**——按 issuer 隔离；AS mismatch **要让客户端**报错，不要网关内部吞掉。

### 2.4 SEP-2468 · `iss` claim 强制验证（防 mix-up 攻击）

多 IdP 环境下，攻击者把对 AS-A 的授权响应重定向到 AS-B 的客户端，客户端拿 AS-A 的 code 去 AS-B 换 token（**OAuth mix-up attack**）。

**新规则**：**要求授权响应带 `iss` claim**；**客户端必须验证 issuer**——把响应绑到正确 AS（引用 [RFC 9207](https://datatracker.ietf.org/doc/html/rfc9207)）。

**对网关**：做 AS 聚合/反向代理时**必须在出站时强制注入 `iss`**（从 AS 元数据里读）；入站校验**必须校验 `iss` 等于"我期望的 AS"**。

### 2.5 SEP-2207 · OIDC 风格 refresh token 引导

OAuth 2.1 不强制 AS 给 refresh token，**但绝大多数 OIDC AS 要求 `offline_access` scope 才会给**。

**新规则**：
- **客户端**应该按 OIDC AS 的要求请求 `offline_access`
- **MCP server 不应该在响应里 `require` `offline_access`**——这是 AS 的能力，不该由 RS 强制

**SDK 跟进**（4 个官方 SDK 全在改）：`conformance#166` / `python-sdk#2039` / `typescript-sdk#1523` / `rust-sdk#676`。

**对网关**：看到 `offline_access` 进 scope，**别慌**——是规范要求；计数/计费时**不要把 `offline_access` 当作特殊 scope**。

---

## 三、SEP-2385（草案，open） · Tool Auth Manifest——"per-tool policy" 的协议级抓手

**仍未合并**（2026-04-13 仍 open）但**意义深远**：**TAM 解决 SEP-990/1046（连接鉴权）之上的空缺**——连接鉴权解决"谁能连"，但**没有协议级机制声明"连进来后能干什么"**。

**最小化设计**（只加 2 个协议元素）：
1. `authorizationManifest` 能力位（`initialize` 时声明）
2. `tools/authorizationManifest` 方法（返回每个 tool 函数的：required roles / resource classification / human approval flag / audit requirement）

**对网关**（如果 SEP 通过）：
- 网关**必须在 tool 路由前读 TAM**
- `human_approval: true` 的 tool 调用**必须拦截**等用户审批
- `audit: required` 的 tool 调用**必须落 audit log**才能执行

> **2026 年 MCP 协议最值得跟踪的草案之一**——如果通过，**MCP 网关终于有"per-tool policy" 的协议级抓手**，不再依赖各 server 自定义 `tools/list` 注解。

---

## 四、SEP-2395（MCPS）：协议级加密层——已被关闭 1 次又重开

**状态**：2026-03-15 关闭 → 2026-04-26 又重开。引用 [TapAuth 研究](https://tapauth.ai/blog/518-mcp-servers-scanned-41-percent-no-auth)：**41% MCP server 零鉴权**；CVE-2025-6514 (CVSS 9.6) **tool poisoning → RCE**；CVE-2025-49596 (CVSS 9.4) **MCP Inspector RCE**。

**设计要素**（消息层，与 OAuth 会话层互补）：Agent Passports（ECDSA P-256）/ 每条 JSON-RPC 消息签名 / tool 定义完整性（防 rug pull）/ replay 防护（nonce + 300s 时间窗）/ Trust Levels L0–L4 / CRL+OCSP 风格撤销。

**判断**：**MCPS 与 MCP 主 spec 的张力**——加信封模型可能让 LiteLLM/Portkey/Envoy 这种"透传型"网关还要做 message-level 验证，**对网关架构冲击比 OAuth spec 切片大得多**。**目前是 proposal 阶段，没进 roadmap**，但 SEP 重新打开说明社区还在讨论。

---

## 五、Registry 在 6 月 4 日同步硬化：SSRF + 名字前缀混淆

`modelcontextprotocol/registry` 在同一天（2026-06-04）密集提交了 4 个安全相关 PR。

### 5.1 PR #1330（merged） · cargo 验证器 SSRF 硬化

**上下文**：5/03 合并的 PR #1207 给 Registry 加了 cargo (crates.io) 作为新 package 类型，**PR #1330 是 review 后的 follow-up 硬化**。

**3 大改动**：
1. **SSRF 硬化**——两步 README 抓取：第 2 步抓 README URL **先 pin 允许的 host**（prod 是 `static.crates.io`）；**每一跳 3xx 重定向都要 pin 回 allowlist**；README body 用 `io.LimitReader` **5 MiB 上限**
2. **状态码语义细化**：`429` → 报 transient/retryable；`403` → 反查 crate-version 端点区分"真不存在" vs "存在但没 README"
3. **共享 `containsMCPNameToken` helper**：边界锚定的所有权 token 匹配，**防止 `io.github.acme/widget-pro` 误匹配 `io.github.acme/widget`**（前缀混淆）

> **作者明确说"目前不可被 publisher 利用"**（URL 来自 crates.io）——但让"host 是 pin 的"这个保证**在代码里**而不是**靠 crates.io 行为**。

### 5.2 PR #1331（draft，行为变更） · PyPI/NuGet 引入 anchored match

**注意是 draft**——**严格更严**的行为变更：替换 `strings.Contains` 为 `containsMCPNameToken`（PR #1330 引入）；关闭前缀混淆攻击；**影响面**：publish 时（`CreateServer`）跑所有权校验，**已存储 server 不追溯**——只有重新发版的 publisher 可能被卡。

### 5.3 其他 6/4 同步动作

PR #1335（open）"client-cancelled GET /v0/servers returns 499 without error log"；多个 PGx/Pulumi/OTel 依赖 bump。

**含义**：**Registry 6/4 是一次"安全 + 依赖清理"集中窗口**——和 Auth IG 的 5-SEP finalization 是**两个独立项目、同一周**的同步行为，说明 6 月初 MCP 全栈进入了"运营级硬化"阶段。

---

## 六、对架构师 / 网关选型的 3 条操作建议

### 6.1 6 月底前要做的 4 个升级

如果你的 MCP 网关是 2026-03 之前实现的：
1. **iss 验证**——入站响应都要检查 iss 等于我方 AS
2. **scope 不替客户端做合并**——SEP-2350 写得很清楚
3. **单一 well-known URI 路径**——只发 `/.well-known/oauth-authorization-server`
4. **多 AS 凭据隔离**——按 issuer 拆分 DCR 注册表

### 6.2 紧盯 2 个未通过的草案

- **SEP-2385 Tool Auth Manifest**——如果通过，per-tool policy 终于有协议抓手
- **SEP-2395 MCPS**——加密层提案；如果进入 main spec 路线，**透传型网关架构要重做**

### 6.3 Registry 选型要看"安全卫生"

- **SSRF 防御**——README/icon fetch 的 host 是不是 pin 死的
- **名字前缀混淆**——有没有边界锚定的 ownership match
- **依赖 bump 频率**——6/4 一天 bump 多个是**健康信号**
- **429/499 处理**——5xx/4xx 区分是不是 actionable

---

## 七、和前 3 轮的关系

| 轮次 | 视角 | 本轮补的视角 |
|---|---|---|
| 01:06 | 协议 + Auth IG 章程 | **5 个 SEP final 实现细节** |
| 01:46 | 5 大产品工程动作 | **SEP-2385 TAM 是"per-tool policy"的协议级基础** |
| 08:34 | 4 种部署模式 | **Registry 硬化是部署前的"信任根"问题** |
| **09:50（本轮）** | **生产治理集中落地** | — |

---

## 引用与数据来源

### MCP 主 spec / SEP

- SEP-2468 `iss` claim：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2468
- SEP-2350 step-up scope：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2350
- SEP-2351 RFC 8414 well-known：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2351
- SEP-2352 AS binding：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2352
- SEP-2207 OIDC refresh token：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2207
- SEP-2385 Tool Auth Manifest（草案）：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2385
- SEP-2343 elicitation+auth（草案）：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2343
- SEP-2395 MCPS 加密层：https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2395
- RFC 6750 §3.1：https://datatracker.ietf.org/doc/html/rfc6750#section-3.1
- RFC 8414：https://datatracker.ietf.org/doc/html/rfc8414
- RFC 9207：https://datatracker.ietf.org/doc/html/rfc9207

### MCP Registry

- 仓库：https://github.com/modelcontextprotocol/registry
- PR #1330 cargo 硬化：https://github.com/modelcontextprotocol/registry/pull/1330
- PR #1331 PyPI/NuGet anchored match：https://github.com/modelcontextprotocol/registry/pull/1331
- PR #1207 cargo 包类型：https://github.com/modelcontextprotocol/registry/pull/1207
- PR #1335 499 处理：https://github.com/modelcontextprotocol/registry/pull/1335

### 协议实现

- Arcade.dev MCP Gateway 实现 SEP-2207：https://docs.arcade.dev/en/guides/mcp-gateways
- TapAuth 41% 无鉴权研究：https://tapauth.ai/blog/518-mcp-servers-scanned-41-percent-no-auth
- CVE-2025-6514（tool poisoning RCE，CVSS 9.6）/ CVE-2025-49596（MCP Inspector RCE，CVSS 9.4）
