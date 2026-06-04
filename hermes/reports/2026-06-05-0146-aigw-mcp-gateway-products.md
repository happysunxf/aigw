# AI 网关持续深挖 · MCP Gateway 专题（产品篇）

> **抓取时间**：2026-06-05 01:46 CST（UTC 2026-06-04 17:46）· **主题**：cron 1/8 轮 MCP Gateway，**第 2 视角：4 个产品如何落地 2026-07-28 RC 协议**。上轮（01:06）讲协议+Auth IG+Registry，本轮讲 35 天里产品工程动作。

---

## 一、本轮观察的产品矩阵

| 产品 | 仓库 | 上一 GA / RC | 本次观察点 | 关键趋势词 |
|---|---|---|---|---|
| Envoy AI Gateway | `envoyproxy/ai-gateway` | v0.6.0（2026-05-05）| `MCPRoute` → `v1beta1` 升级 + `MCPBackend` CRD 提案 + 5 项 MCP 网关新功能 | **MCP 一等公民** |
| IBM mcp-context-forge | `IBM/mcp-context-forge` | v1.0.0（2026-04-30 GA） | v1.0.1（5/13） + v1.0.2（5/25），59 PR | **合规化、SSRF 防护、Alembic** |
| Higress | `higress-group/higress` | v2.2.2（2026-05-26）| 37 个更新：model header 同步、Bedrock Mantle、cached tokens | **协议路由一致性** |
| Archestra | `archestra-ai/archestra` | platform v1.2.57（2026-06-04 一天 2 个版本）| MCP catalog team-scoping + GitHub App auth + DB pool 限流 | **企业治理、并发安全** |
| Docker mcp-gateway | `docker/mcp-gateway` | v0.42.2（2026-05-28）| CLI 插件路径稳定化 | 缓步 |

> **MCP Gateway 已从"附加模块"变成"产品独立赛道"**。Envoy AI GW 把 `MCPRoute` CRD 升 `v1beta1` 的时间（4/30）几乎和 IBM mcp-context-forge 1.0.0 GA（4/30）**同一天**——这是市场在 5 月集中"上位"的信号。

---

## 二、Envoy AI Gateway v0.6.0：MCP 第一次成为"一等公民"

### 2.1 MCPRoute → v1beta1（PR #2090, 2026-04-30 合并）

`MCPRoute` CRD 从 `v1alpha1` 升 `v1beta1`——这意味着**MCP 路由是网关的核心资源**，不再是实验性。这意味着：

- **API 字段冻结承诺**——下游 controller / 工具链可以开始依赖稳定 API
- **自动生成 CRD 文档** 进入 envoy-ai-gateway.io/docs
- **migration path** 写进 Upgrade Guidance

### 2.2 5 项 MCP 网关专属新能力（v0.6.0 release body）

| # | 能力 | 工程含义 |
|---|---|---|
| 1 | `MCPRouteBackendRef.forwardHeaders`：**按 backend 的 header 透传** | 多 backend 场景下，**每个 upstream MCP server 收到不同的 trace context / tenant id** |
| 2 | `MCPRouteOAuth.claimToHeaders`：**JWT claim → outbound header** | 网关验完 JWT 后注入到 upstream，**upstream 不用再解析 JWT** |
| 3 | `MCPToolFilter` 支持 `exclude` / `excludeRegex` | **deny 模式** 补齐；后端暴露 100 个 tool 时可以 deny 掉 95 个 |
| 4 | access log + response metadata 加 `mcp_tool_name` | **per-tool 调试和计费** 直接可观测 |
| 5 | **per-backend 能力跟踪**（tools/prompts/resources/logging/completions） | 网关能告诉客户端"route 实际可达能力"——**避免假阳性** |

### 2.3 MCPBackend CRD 提案（PR #2144, 2026-06-03 closed，**设计稿落地中**）

核心问题：**MCPRoute 内的 inline backendRefs 撞 K8s object size limit**——尤其当 RFC 8693 token exchange（每个 backend ~25 行 nested config）加进去后。

**4 个备选设计**：
1. inline security policy（简单但耦合生命周期）
2. **独立 security policy + Policy Attachment**（推荐，与 LLM 侧 `AIServiceBackend + BackendSecurityPolicy` 对齐）
3. backend-refs-policy
4. route-refs-policy

**推荐方案**：`MCPBackend` CRD + 扩展 `BackendSecurityPolicy` 用 `targetRefs`，同时保留 `MCPRouteBackendRef` 的 `Name/Group/Kind` 字段做向后兼容。

> **对架构师的信号**：Envoy AI GW 在做的是**MCP ↔ LLM 资源模型对齐**——LLM 侧早就有 `AIServiceBackend` + `BackendSecurityPolicy` 拆分的成熟模式（v0.5/v0.6 都用了），MCP 侧要走同一套。**这会成为 MCP 网关的事实标准**。

---

## 三、IBM mcp-context-forge：第一个 GA 级 MCP Gateway

### 3.1 v1.0.0 GA（2026-04-30）= **93 PR 一次性收口**

GA 8 大块：🔐 Auth & OAuth（JWKS、audience、Entra ID、账户锁定）/ 🦀 Rust 运行时（A2A 1.0、MCP proxy SSRF）/ 🧩 插件框架（全局开关、PII filter）/ 🖥️ shadcn/ui Admin UI / 🔌 **2025-11-25 protocol compliance harness** / 🌐 API & Transport 完善。

> **战略信号**：`IBM/mcp-context-forge` **跳过 v0.9 beta 直接 RC-3 跳 v1.0.0 GA**——企业市场对"生产可用 MCP 网关"需求见顶。

### 3.2 v1.0.1（5/13）+ v1.0.2（5/25）：**合规化加速**

v1.0.2 集中修 **FedRAMP / FIPS / STIG**：#5033（FIPS STIG controls 补齐）/ #5053（OpenSCAP 扫描剩 4 个 STIG failure）/ #5025（alpine.js SRI hashes）/ **#5013（PII 日志脱敏）** / #5032（merge queue in docker-multiplatform）。

> **判断**：在做 **GovTech / FedRAMP 客户入场准备**——和 Envoy / Higress 路线完全不同（后者偏云原生 + 商业产品）。

### 3.3 一个**破坏性变更**值得注意：禁用 HTTP 302/301/307/308 重定向

理由：SSRF 防护（避免攻击者把"白名单 URL"重定向到内网）。**影响面**：所有用 redirect 做 API key 轮换 / OAuth callback 的 MCP server / gateway 集成**直接挂掉**。**mitigation**：注册 final destination URL。这是 v1.0.0 → v1.0.1 → v1.0.2 三次小版本里**最重的一个 breaking change**。

---

## 四、Higress v2.2.2：协议路由"细节"做到极致

### 4.1 13 个新功能里 4 个是 LLM 路由相关的

| PR | 功能 | 价值 |
|---|---|---|
| #3827 | `modelToHeader`（默认 `x-higress-llm-model-final`）同步更新 | 模型映射后**下游限流/计费能拿到真实匹配到的模型**——避免 header 错位导致策略跑偏 |
| #3823 | nginx-rewrite 兼容的 WASM 插件 | 修 **CVE-2026-42945**（heap overflow）——主动用 WASM sandbox **替换** 直接执行 nginx rewrite |
| #3820 | Bedrock Provider 直连 **Mantle Anthropic Messages API**（去掉 OpenAI→Converse 双跳翻译） | 降低延迟 + 原生 Anthropic feature 支持 |
| #3766 | OpenAI→Claude 流式响应里加 **CacheReadInputTokens** | 网关侧必须把缓存命中数往响应里传，**否则客户端账单不对** |

Higress v2.2 节奏稳（v2.2.0 2/11，v2.2.1 4/9，v2.2.2 5/26）——大版本稳定后密集修边角，**产品级**信号。

---

## 五、Archestra：把 MCP gateway 做成"企业平台"

### 5.1 节奏异常快

```
platform-v1.2.52  2026-05-27 13:12   platform-v1.2.53  2026-05-28 17:22
platform-v1.2.54  2026-05-31 23:03   platform-v1.2.55  2026-06-03 18:12
platform-v1.2.56  2026-06-04 12:32   platform-v1.2.57  2026-06-04 17:21
```

**30 天 6 个 patch 版本** + 经常一天 2 个——通常是"hotfix + feature flag 灰度"并行。

### 5.2 5 个值得拆的工程动作

| # | PR | 含义 |
|---|---|---|
| 1 | **#5293** GitHub App auth for skill imports and KB connectors | **企业身份集成**——用客户 GitHub org 身份同步 skill/知识库 |
| 2 | **#5298** team-admins scope catalog items to their teams | **MCP 工具按 team 隔离**——回应"53% 静态 API key"治理 |
| 3 | **#5305** cap database pool size | **主动限流**——staging 故障不进 prod |
| 4 | **#5276** MCP image refresh action | **registry-driven 自动 deploy** |
| 5 | **#5294** Go toolchain 1.25.11 (CVE-2026-42504) | **当天追 CVE**——Go 1.25.11 在 6/4 修的 CVE，Archestra 当天就跟 |

### 5.3 一次有意思的 revert

**#5302 Revert "refactor(mcp-registry): remove catalog preset feature"**——昨天（#5290）刚合的 catalog preset 移除今天就 revert。说明 **catalog preset 是 enterprise 客户在用**，不该轻易删。

> **信号**：Archestra 的产品哲学是"**企业优先 + 快速实验**"——每个 PR 都带 hotfix revert 通道，跟 IBM mcp-context-forge "慢稳"风格完全相反。

---

## 六、Docker mcp-gateway v0.42.2：CLI 插件路径稳定

v0.42.0 (4/30) → v0.42.1 (5/5) → v0.42.2 (5/28) — **两个月 3 个 patch**。Docker 的策略是把 MCP gateway 做成 **Docker Desktop 插件**——和"独立服务"产品路线不同，关注点是"CLI UX 和 Docker 生态集成"。

---

## 七、对企业的 4 个具体建议（本轮新增）

1. **部署 Envoy AI Gateway v0.6.0 试用 MCPRoute v1beta1**——这是**最接近 MCP 协议规范的 gateway 资源模型**，未来 1-2 个版本会加 `MCPBackend` CRD 拆解，提前用 v1beta1 可无缝升级。
2. **如果走"企业合规"路线，盯 mcp-context-forge**——FedRAMP/FIPS 准备 + v1.0.2 SSRF 修复方案（直接禁 redirect）是**值得抄的清单**：URL 校验 + 禁 redirect + PII 日志脱敏 + Redis TLS。
3. **如果走"快速实验 + 团队治理"路线，盯 Archestra**——team-scoping、GitHub App auth、DB pool cap 三个 feature 全是企业刚需，**30 天 6 个 patch 节奏**意味着反馈回路短。
4. **自建 MCP gateway 时，对照 v0.6 release body 的 5 个 MCP 能力**——尤其 `MCPRouteBackendRef.forwardHeaders` 和 per-backend capability tracking。这两个**是 "多 MCP backend" 场景的最小可用能力集**。

**协议跟进总览**（07-28 RC 关键项 × 4 产品）：
- **IBM mcp-context-forge 跟进最紧**（v1.0.0 GA 就锁了 2025-11-25 compliance）→ Envoy AI GW 跟进第二（v1beta1 + per-backend capability tracking）→ Higress 走"LLM 路由"路线而非 MCP 直通 → Archestra 走"企业平台"路线。

---

## 八、本期数字摘要

- 抓取产品：**5 个**（Envoy AI GW / IBM mcp-context-forge / Higress / Archestra / Docker mcp-gateway）
- 关键 GA / RC：**Envoy AI GW v0.6.0 (5/5) + IBM mcp-context-forge v1.0.0 GA (4/30) + v1.0.1 (5/13) + v1.0.2 (5/25) + Higress v2.2.2 (5/26) + Archestra v1.2.57 (6/4)**
- 重点 PR：**MCPRoute v1beta1 (#2090 4/30) + MCPBackend CRD 提案 (#2144 6/3) + MCPRouteBackendRef.forwardHeaders (#2047 4/22)**
- **MCP 一等公民信号**：**MCPRoute → v1beta1 升级**（不再是 alpha）
- **重大 breaking**：**IBM mcp-context-forge v1.0.2 禁 outbound HTTP 302/301/307/308**（SSRF 防护）

---

## 引用与数据来源

### Envoy AI Gateway
- v0.6.0 release body / tag：见 `https://api.github.com/repos/envoyproxy/ai-gateway/releases/tags/v0.6.0` + `https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0`
- PR 列表：`https://api.github.com/search/issues?q=repo:envoyproxy/ai-gateway+MCPRoute+is:pr+is:merged+merged:>2026-04-01`
- 关键 PR：#2090（MCPRoute v1beta1）/ #2144（MCPBackend CRD 提案 closed）/ #2047（forwardHeaders）
- 官方文档：`https://aigateway.envoyproxy.io/docs/0.6/`

### IBM mcp-context-forge
- v1.0.0 GA / v1.0.2 release bodies：见 `https://api.github.com/repos/IBM/mcp-context-forge/releases/tags/v1.0.0` + `v1.0.2`
- v1.0.2 tag：`https://github.com/IBM/mcp-context-forge/releases/tag/v1.0.2`
- 2026-05-20 之后 commits：`https://api.github.com/repos/IBM/mcp-context-forge/commits?since=2026-05-20T00:00:00Z`
- 关键 PR：#5033（FIPS STIG）/ #5053（OpenSCAP 4 failures）/ #5025（alpine SRI）/ #5013（PII log redact）/ #5032（merge queue）

### Higress
- v2.2.2 release body / tag：`https://api.github.com/repos/higress-group/higress/releases/tags/v2.2.2` + `https://github.com/higress-group/higress/releases/tag/v2.2.2`
- 关键 PR：#3827（modelToHeader）/ #3823（nginx-rewrite WASM, CVE-2026-42945）/ #3820（Bedrock Mantle）/ #3766（cached tokens）

### Archestra
- releases / commits：`https://api.github.com/repos/archestra-ai/archestra/releases?per_page=6` + `https://api.github.com/repos/archestra-ai/archestra/commits?since=2026-05-25T00:00:00Z`
- 关键 PR：#5293（GitHub App auth）/ #5298（team-scope catalog）/ #5305（DB pool cap）/ #5294（Go 1.25.11 CVE-2026-42504）/ #5276（MCP image refresh）/ #5302（revert catalog preset removal）

### Docker mcp-gateway
- releases API + v0.42.2 tag：`https://api.github.com/repos/docker/mcp-gateway/releases?per_page=6` + `https://github.com/docker/mcp-gateway/releases/tag/v0.42.2`

### 上一轮对照（协议 + Auth IG + Registry）
- `hermes/reports/2026-06-05-0106-aigw-mcp-gateway.md`（同仓库）
