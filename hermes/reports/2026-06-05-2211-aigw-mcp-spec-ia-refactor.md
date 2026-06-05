# AI 网关深挖 · MCP Gateway 专题（2026-06-05 22:11 CST）

> **窗口**：过去 36h（2026-06-03 22:11 → 2026-06-05 22:11 CST）。**焦点**：spec
> 信息架构（IA）重构 + Registry 错误卫生 & SSRF 硬化。
> **不重复**：01:06/01:46/08:34/09:50/15:28 五轮 MCP 报告。
> **本地 hour % 7 = 1** → MCP Gateway 专题。

**时间锚点**：报告生成 **2026-06-05 22:11 CST**（周五，Asia/Shanghai）。
**GitHub 状态**：spec `2026-07-28-RC`（5/29）仍为最新 release tag；Registry
`v1.7.9`（5/12）后**未发版**，本周 8 个 PR 在 main 累积；Inspector 0.22.0
（6/4 12:36 UTC）已发版。

---

## 一、本轮核心论点：MCP 把「信息架构」当成「安全工程」做

过去 36h 内 8+ 个 PR，两条主线同步推进：

- **规范侧（spec 仓 8 commits）**：`localden/auth-spec` 把单页
  `authorization.mdx` 拆成 4 子页（`index` + `authorization-server-discovery` +
  `client-registration` + `security-considerations`），按 normative vs
  descriptive 重新归位（PR #2858 6/4 合 + #2862 6/5 合）。**这不是排版**——
  Auth IG 把"哪些 MUST 分散在 4 个 RFC 引用里"做成可被单点链接、可被 LLM 检索
  的 IA 单元，是 5 SEP final（09:50 报告）落地的"对用户最后一公里"。
- **平台侧（registry 仓 8 commits）**：
  - **SSRF 硬化**（#1330，6/4）：cargo 验证器两阶段 README 抓取做 host
    allowlist 锁 + `CheckRedirect` 每跳校验 + 5 MiB body cap。
  - **错误卫生**（#1335+#1338，6/5 同日）：
    - **#1335** 把 `context.Canceled` 映射到 **HTTP 499**，关闭
      `superfluous response.WriteHeader` 警告和"list servers failed" 误报。
    - **#1338**（紧跟 #1335 之后 9 分钟）堵住 #1335 引入的 **CWE-209
      信息泄露回归**——`ListServersError` 把 raw `err` 透传到
      `huma.Error500InternalServerError`，**公开的 `GET /v0/servers`** 端点
      会把 pgx/pgconn 的 SQLSTATE/表名/约束名/列名吐回给未认证客户端。
  - **cargo 验证器**（#1207，6/3 合，#1330 强化）：第 5 个 package registry
    类型落地。

两个看似无关的方向**实际是同一种工程哲学**：把"安全 MUST"做成"可被单点链接、
可被 LLM 索引、可被自动化断言"的资产，而不是藏在 2000+ 行单页 MDX 的脚注里。

---

## 二、规范侧：Authorization Spec 1 页 → 4 页（#2858 + #2862）

### 2.1 拆页结构（#2858，6/4 19:16 UTC 合，user: localden）

- `authorization.mdx` **removed**（原 200+ 行单页）
- `authorization/index.mdx` added：Overview + Purpose + 9 RFC 引用清单 + Roles
- `authorization/authorization-server-discovery.mdx` added：RFC 9728 PRM、
  `WWW-Authenticate` 头、well-known URI
- `authorization/client-registration.mdx` added：3 种注册机制 + 优先级
  （Pre-reg / Client ID Metadata Docs / DCR）
- `authorization/security-considerations.mdx` added：Token audience binding、
  token theft、HTTPS、PKCE
- `docs/docs.json` 站点导航同步

`localden` 4 天内连续合两个 PR，把页面组织 + 交叉引用 + normative 措辞统一
刷一遍。

### 2.2 #2862 cleanup（6/5 10:52 UTC 合，6 文件 +83/-55）

4 子页各自微调（最显著：`index.mdx` +40/-5，新增 9 RFC 引用表 + Roles 节）
+ `changelog.mdx` +19（记录 IA 重构）+ `deprecated.mdx` +8（同步被替代表述）。

### 2.3 对 AI Gateway 团队的影响

- **链接稳定性**：`…/basic/authorization.mdx#section-3` 全部失效，必须批量
  改 anchor 到 `…/basic/authorization/{index,client-registration,…}#xxx`。
  聚合型文档/CX 团队的 wiki、内部培训 PPT、给客户的 FAQ **几乎肯定有死链**。
- **引用语义**：`security-considerations.mdx` 第一次**集中列出** 5 条
  MUST（Token Audience Binding、PKCE、HTTPS、short-lived access token、
  refresh token rotation）——之前散在 4 个 RFC 引用里。这是 SOC2 / ISO 27001
  重新对账的最佳窗口。
- **训练数据时效**：用 2025-11-25 之前版本训练的 LLM agent 引用过时 anchor
  的概率高。可写 PR 校验脚本：爬全 spec 子页，扫 `…/authorization#…` 模式
  → 404 → warn。

---

## 三、平台侧：Registry 36h 把"错误卫生"当一级安全 fix

### 3.1 CWE-209 信息泄露 fix（#1338，6/5 07:08 UTC 合）

| 项 | 内容 |
|----|------|
| 触发链 | #1335 改 `ListServersError` → 9 分钟后 #1338 报告"该 fix 引入新泄露" |
| 泄露面 | `GET /v0/servers`（**未认证公开端点**） |
| 泄露内容 | pgx/pgconn 错误：SQLSTATE、表名、约束名、列名、wrapped error |
| 根因 | `huma.Error500InternalServerError(err)` 第 2 参数被 huma 序列化为响应体 `errors` 数组 |
| 修复 | drop `err` from 500 call；保留 `log.Printf` 服务端详情 |
| 回归测试 | `TestListServersError_realFailureDoesNotLeakDetail` —— marshal 500 响应后断言内部细节不在 body |
| 测试盲区 | 已有测试**只断言 status code**；本 fix 之前没人 marshal 响应体 |

**对 AI Gateway 团队**：
- **任何对外端点（未认证）** 不应把 `err` 透传进 huma 5xx 调用。
- **测试模式升级**：从 "assert status code" 升级到 "marshal 完整响应 → 断言
  敏感字段不存在"。可加 lint 规则禁止 `huma.Error5xx(err, ...)`、
  `c.JSON(500, gin.H{"error": err})` 这类反模式。
- **观察自家 5xx handler**：参考 PR diff ——`servers.go:190/220`、`edit.go`、
  `status.go` 都用 sibling pattern；不一致的 handler 几乎一定还有泄露。

### 3.2 HTTP 499 + 客户端取消卫生（#1335，6/5 06:59 UTC 合，close #1323）

原 bug：客户端断开 → `context.Canceled` → 误报 500 + `log.Printf("list servers
failed")` + huma 在已关闭 socket 上 `WriteHeader` 警告。prod 5/28 20:28 观察到
`list servers failed: error iterating rows: context canceled`。

新行为：`context.Canceled` → **HTTP 499**（nginx 语义） + 跳过错误日志。PR
注释里写："499 client-cancelled path is unchanged (client has already
disconnected, so nothing is leaked)" —— 9 分钟后 #1338 仍能发现 sibling
handler 泄露，说明 499 ≠ 信息泄露安全网。

**对 AI Gateway 团队**：
- 任何 Go `context.Context` handler **默认应**：`if errors.Is(err,
  context.Canceled) { return }` 在 `log.Errorf` 之前 short-circuit。
- 499 是 nginx 事实标准（HTTP 标准未正式收录）。可观测打 dashboard 时
  **单独**分桶——不计入"上游错误率"，但应计入"客户端体验"。

### 3.3 Cargo SSRF 硬化（#1330，6/4 21:34 UTC 合，#1207 follow-up）

作用域：cargo 验证器 + 共享 helper；**npm/pypi/nuget/oci/mcpb 无行为变更**。

2-call README 抓取的 SSRF 面：step-2 README URL 没锁 host → crates.io 响应
可指任意内网/恶意主机。硬化：step-2 URL **预先** pin 到 allowlist（prod:
`static.crates.io`；test: base host）；`CheckRedirect` 每跳都校验同一
allowlist；body cap `io.LimitReader` 5 MiB。

状态码语义：429 → transient/retryable；403 → 走 crates-version 端点
disambiguate（"not found" vs "add a README with `mcp-name` and republish"，
mirror NuGet 验证器）。

共享 helper：`containsMCPNameToken` —— 边界锚定 ownership-token 匹配，防
README 写 `io.github.acme/...` 之类的**前缀混淆**。

**对 AI Gateway 团队**：
- 任何验证器/爬虫做 `metadata → URL → fetch` 两步走，**第二步必须独立
  allowlist**，不能信第一步返回的 host 字段。
- 共享 helper 化的命名 token 匹配避免 5 个验证器各写一份 prefix-match 漏掉
  边界 case。
- 5 MiB README body cap 是个**安全+成本**合取点：内存 + 防 zip-bomb 风格
  大 README。

### 3.4 Cargo 验证器初次发布（#1207，6/3 14:56 UTC 合）

第 5 个 package registry 类型落地。cargo（crates.io）是**首个"包管理器
语义"**注册表——验证逻辑要处理 `Cargo.toml` → `name`+`version` → metadata
→ README 的二跳 + 复杂 features 语义。

---

## 四、Inspector 0.22.0（6/4 12:36 UTC）— IA 之外的"供应链"事件

7 个 PR 上版，**核心 3 个都是"信任边界"类工程**：

### 4.1 npm OIDC trusted publishing（#1199，4/14 合；本版正式启用）

替换前：`NPM_TOKEN` secret + `NODE_AUTH_TOKEN`。替换后：npm 11.5.1+ OIDC
trusted publishing + `NPM_CONFIG_PROVENANCE=true`。4 个包
（`@modelcontextprotocol/inspector{,-client,-server,-cli}`）现在都有 npm
provenance attestation，**不再依赖长期 secret**。下游消费方可验证"这包确实
由 modelcontextprotocol GitHub org 的 `release` env 在 `main.yml` 发布"。
4 包各自在 npmjs.com 配置 GitHub Actions trusted publisher
（Repository=`inspector`, Workflow=`main.yml`, Environment=`release`，
**case-sensitive**）。旧 `Release` env 已 delete + recreate 为 `release`。

**对 AI Gateway 团队**：自家 npm 包建议同步切 OIDC + 删除 NPM_TOKEN。短期
`npm install` 失败概率略升（npm 11.5+ 强依赖），但**消除了 token 泄露面**。

### 4.2 claude.yml author_association gate（#1270，5/1 合）

观察到的痛点：未授权用户在 PR 评论 `@claude` → workflow 启动 → 中途失败
（action 缺权限）→ Actions tab 一片红 + 浪费 runner minutes + UX 差。
Fix：trigger `if:` 加 `author_association in {OWNER, MEMBER, COLLABORATOR}`
——GitHub event payload 本身就有 `author_association`，**workflow 评估阶段**
就 skip（不分配 runner）。

**通用范式**：所有 `@bot` 触发器都应该 `author_association` gate。Hermes
cron 任务同理——非 trusted user 触发的可观测/可写动作都应 skip。

### 4.3 npm audit fix（#1380，5/31 合）+ handlebars 4.7.9

修了 15/16 个 audit findings（1 critical / 5 high / 8 moderate / 1 low）：
- 🔴 **critical**: `handlebars` → 4.7.9（JS injection / prototype pollution）
- 🟠 high: `fast-uri`、`flatted`、`hono`、`path-to-regexp`、`rollup`、
  `vite`、`express-rate-limit`、`@hono/node-server`
- 1 个 high（minimatch@3.1.2 ReDoS）故意未修：被 `@eslint/config-array` 拉入，
  dev-only、随 ESLint 升级自动清掉

**对 AI Gateway 团队**：handlebars 4.7.9 是必须跟进的 CVE，自己项目若有
handlebars 走 `npm audit fix` 即可。

### 4.4 URL-mode Elicitation（#1423，cliffhall）

上一轮（15:28 报告）已提过，本次 release 收录。**这是 Inspector 作为"协议
落地参考实现"的关键能力**——给 LLM 客户端演示如何用 URL 模式而非 in-band
JSON 实现 elicitation（让用户去浏览器填高敏表单）。

---

## 五、本期数字摘要

| 指标 | 值 |
|------|----|
| 抓取窗口 | 36h（2026-06-03 22:11 → 2026-06-05 22:11 CST） |
| spec 仓 commits（窗口内） | 20+（取 Top 8 IA 相关） |
| spec 拆页 PR | 2（#2858 + #2862） |
| spec 拆页文件操作 | -1 单页 + 4 子页 + 2 配套 |
| Registry commits（窗口内） | 8 |
| Registry 关键 PR | 4（#1207 / #1330 / #1335 / #1338） |
| Registry 安全类 PR | 2（#1330 SSRF、#1338 CWE-209） |
| Registry 信息泄露面 | 公开未认证 `GET /v0/servers` |
| Registry HTTP 499 PR | 1（#1335，close #1323） |
| Registry 新增 package registry 类型 | cargo (crates.io) |
| Inspector release | 0.22.0（6/4 12:36 UTC） |
| Inspector PR 收 0.22.0 | 7 |
| npm CVE fixed | 15/16（handlebars 4.7.9 critical） |
| npm OIDC trusted publishing 包数 | 4 |

---

## 六、对 AI Gateway 团队的 5 条新可操作清单

1. **链接批量校验**：脚本扫全 spec 子页 `…/authorization#…` 模式 → 404 报
   warn。spec 拆页是已知断链事件。
2. **5xx 错误透传反模式 lint**：禁止 `huma.Error5xx(err, ...)` /
   `c.JSON(500, gin.H{"error": err})` / `http.Error(w, err.Error(), 500)`。
   测试从 "assert status code" 升级到 "marshal body + assert no leak"。
3. **客户端取消短路**：Go handler 早加 `if errors.Is(err, context.Canceled)
   { return }`，避免 499 + 误报 error log + 浪费告警 quota。
4. **npm OIDC trusted publishing 升级**：自家 publish 流程去掉 NPM_TOKEN，
   开 `NPM_CONFIG_PROVENANCE=true`，下游可验证供应链。
5. **`@bot` 触发器 author_association gate**：参考 Inspector #1270，
   claude.yml 改 `if:` 加 member 校验，未授权 `@bot` 评论在 workflow 评估
   阶段 skip。

---

## 引用与数据来源

### 规范侧（spec 仓）

- PR #2858 — Authorization spec split: <https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2858>（6/4 19:16 UTC 合，user: localden）
- PR #2862 — Update the authorization spec structure/callouts: <https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2862>（6/5 10:52 UTC 合，user: localden）
- 新拆页 index: <https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/draft/basic/authorization/index.mdx>
- 新拆页 authorization-server-discovery: <https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/draft/basic/authorization/authorization-server-discovery.mdx>
- 新拆页 client-registration: <https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/draft/basic/authorization/client-registration.mdx>
- 新拆页 security-considerations: <https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/draft/basic/authorization/security-considerations.mdx>
- spec release `2026-07-28-RC`（仍为最新 RC）: <https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28-RC>
- spec changelog: <https://modelcontextprotocol.io/specification/draft/changelog>

### 平台侧（registry 仓）

- PR #1207 — feat: add cargo (crates.io): <https://github.com/modelcontextprotocol/registry/pull/1207>（6/3 14:56 UTC 合，user: Wolfe-Jam）
- PR #1330 — fix(cargo): harden README fetch (SSRF): <https://github.com/modelcontextprotocol/registry/pull/1330>（6/4 21:34 UTC 合，user: rdimitrov）
- PR #1335 — fix: client-cancelled returns 499: <https://github.com/modelcontextprotocol/registry/pull/1335>（6/5 06:59 UTC 合，close #1323）
- PR #1338 — fix: don't leak internal error detail (CWE-209): <https://github.com/modelcontextprotocol/registry/pull/1338>（6/5 07:08 UTC 合，紧跟 #1335 9 分钟）
- Issue #1323 — client cancellation 噪声: <https://github.com/modelcontextprotocol/registry/issues/1323>
- Registry 最新 release v1.7.9（5/12，本周未发新 release）: <https://github.com/modelcontextprotocol/registry/releases/tag/v1.7.9>

### Inspector 0.22.0

- Release 0.22.0: <https://github.com/modelcontextprotocol/inspector/releases/tag/0.22.0>（6/4 12:36 UTC）
- PR #1199 — OIDC trusted publishing: <https://github.com/modelcontextprotocol/inspector/pull/1199>
- PR #1270 — claude.yml author_association gate: <https://github.com/modelcontextprotocol/inspector/pull/1270>
- PR #1380 — npm audit fix (handlebars 4.7.9): <https://github.com/modelcontextprotocol/inspector/pull/1380>
- PR #1423 — URL-mode elicitation: <https://github.com/modelcontextprotocol/inspector/pull/1423>

### 上一轮对照（不重复）

- 15:28 RC 7 major + Inspector 0.22.0 提要: <https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-1528-aigw-mcp-2026-07-28-rc.md>
- 09:50 5 SEP 一次性 final + Registry SSRF/cargo 提要: <https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-0950-aigw-mcp-governance-cluster.md>
- 08:34 4 部署模式 + ToolHive v0.29.0: <https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-0834-aigw-mcp-deploy-arch.md>
- 01:46 五大 MCP Gateway 产品矩阵: <https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-0146-aigw-mcp-gateway-products.md>
- 01:06 MCP 协议 + Auth IG 章程首篇: <https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-0106-aigw-mcp-gateway.md>
