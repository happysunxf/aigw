# AI 网关持续深挖 · 1/8 轮 · MCP Gateway 第 3 视角：部署架构演化

> **抓取时间**：2026-06-05 08:36 CST（UTC 2026-06-05 00:36）
> **新增数据点**：MCP Inspector 0.22.0（URL-mode elicitation）、ToolHive v0.29.0/v0.29.1、Cloudflare graphql-mcp-server 0.2.1、kgateway v2.3.2、Archestra v1.2.56/57、MCP Python SDK v1.27.2
> **不重复前两轮**：01:06 协议 + Auth IG；01:46 Envoy/IBM/Higress/Archestra/Docker 五大产品。本轮聚焦"产品怎么把协议落到部署拓扑"。

---

## 一、核心论点：MCP Gateway 已分裂出 4 种部署模式

| 模式 | 代表 | 拓扑 | 鉴权落点 | 状态 |
|---|---|---|---|---|
| **A. Centralized** | IBM `mcp-context-forge`、Envoy AI Gateway | 独立集群，client → gateway → N upstreams | Gateway 统一 OAuth/JWT | GA / v1beta1 |
| **B. Per-pod sidecar** | ToolHive `MCPServer` CRD | 每个 workload pod 内嵌 sidecar | Sidecar 自管 token | 快速演进 |
| **C. Client-side proxy** | Docker `mcp-gateway`、Archestra local | 开发者机器 / CI 容器 | 本地 keyring | 稳定 |
| **D. Gateway-as-a-Service** | Cloudflare `graphql-mcp-server`、Portkey MCP、Azure MCP | 厂商托管 | 厂商托管 OAuth | 闭源占主流 |

上 MCP 网关第一步是**选模式**——决定 RPS 路径、token 传递、审计落点、运维预算。

---

## 二、模式 A：Centralized 的"协议一致性"难题

**kgateway v2.3.2** (2026-06-04 17:16 UTC) 升级 Envoy 1.37.3 修 [CVE-2026-47774](https://github.com/envoyproxy/envoy/security/advisories/GHSA-22m2-hvr2-xqc8)，**但 release notes 完全没提 MCP**——和 Envoy AI Gateway 的"MCP 一等公民"分化。

**含义**：选 Envoy 派先确认是 `envoyproxy/ai-gateway` 还是 `kgateway-dev/kgateway`——前者有 MCP 一等公民，后者只有 LLM 路由 + HTTP 转码，不解析 MCP 协议。

**Schema migration 是企业生产化的最大拦路虎**：mcp-context-forge 1.0.1→1.0.2 引 Alembic；ToolHive v0.29.0 加 `StorageVersionMigrator` controller（opt-in 默认关）+ 12 个 v1beta1 CRD 接入 storage-version migration。**几乎所有 MCP Gateway 产品跳过这个话题**——但拦路虎是它：

- Schema 变更时正在服务的请求怎么办？停机 / 双写 / lazy migrate？
- OpenAPI ↔ CRD 双向同步？roll-back 路径？多租户存储版本协调？

**判断标准**：release notes 里从来不提 schema migration = 大概率没在生产规模上跑过。

---

## 三、模式 B：Sidecar 的"身份边界"难题

### 3.1 ToolHive v0.29.0 的两个关键 PR

- **PR #5364 (`@ChrisJBurns`, Freeze MCPServer generation per pod via downward API)**：每个 pod 用 downward API 注入**唯一 generation ID**，K8s 滚动升级时老的 generation 还能继续服务 in-flight 请求。
- **PR #5448 (`@jhrozek`, Thread VirtualMCPServer name into Cedar authz middleware)**：Cedar 策略引擎按 `VirtualMCPServer` 名字做授权决策。

**这是 2026 年 6 月最重要的 MCP Gateway 工程动作之一**——解决 sidecar 模式最大的设计难题：

> 一个 pod 里有 5 个 MCP server sidecar，**Cedar 策略要能区分"哪个 tool 来自哪个 sidecar"**。用 sidecar 名字做主键，**pod 一重启身份就丢**。ToolHive 用 downward API 冻结 generation + Cedar 看到 `VirtualMCPServer` 名字 = **sidecar 身份和 policy 绑定稳定**。

### 3.2 其他 4 个工程信号

| PR | 含义 |
|---|---|
| #5361 | `MCPExternalAuthConfig` CRD enum 接受 `obo`（on-behalf-of）——多用户 MCP server 场景标配 |
| #5372 | 统一 authserver DCR types 到 `pkg/oauthproto`——DCR 不再是 sidecar 私货 |
| #5343/5348 | CIMD（Client ID Metadata Document）storage decorator + 嵌入式 AS——MCP 官方推荐的 OAuth 注册方式落地 |
| #5147 | 不透明 upstream token 回退到 request-token claims——多 IdP 场景兼容性补丁 |

**对企业的建议**：sidecar 模式选 ToolHive 是当前最完整，但**要准备接受"K8s CRD 数量爆炸"**（12 个 v1beta1 CRD + 1 个 migration controller）。

---

## 四、模式 C：Client-side Proxy 的"开发者体验"难题

Archestra v1.2.56 (13:08 UTC) → v1.2.57 (17:34 UTC) 一天双发：

1. **PR #5298**：`mcp-catalog` team-admins scope catalog item 到自己的 team——**多团队共用 MCP server 治理**，以前 global only。
2. **PR #5293**：`github` GitHub App auth for skill imports and KB connectors——PAT → GitHub App，**审计粒度更细 + token 不再长期存活**。
3. **PR #5290（破坏性）**：移除 catalog preset feature——强制每个 MCP server 显式注册。

**信号**：Archestra 在**强推"零魔法 + 显式管理"**——和企业治理方向一致，但开发者"快速试"会不友好。

Docker mcp-gateway v0.42.2 (2026-05-28) release body 空——Docker 策略"稳定优先于速度"：v0.42.0 (4/30) → v0.42.1 (5/05) → v0.42.2 (5/28)，**一个月一个版本**。

---

## 五、模式 D：Gateway-as-a-Service 的"信任边界"难题

### 5.1 Cloudflare graphql-mcp-server 0.2.1 (2026-06-02，**3 天前**)

patch changelog 揭示**Cloudflare 整套 MCP server 矩阵的真实工程现状**：

1. Cloudflare 有 4+ 个 MCP server（graphql / workers-observability / workers-builds / R2 / D1 / Vectorize...）
2. 它们共享一个 Durable Object class（`UserDetails`）
3. 删除这个 class 是一次**跨产品的级联破坏**——`code: 10064` 阻止了 graphql 部署
4. Cloudflare 必须用 `deleted_classes` migration 才能继续 deploy

**对企业的含义**：**"用 SaaS 厂商的 MCP 编排" = 你的所有 MCP 请求都流过厂商的 Durable Object + Workers**。金融/医疗等强监管行业，**这是合规审计的天坑**——要么接受厂商审计报告，要么只能选 A/B 自建。

### 5.2 Microsoft MCP

`microsoft/mcp` 仓 6 月头两天：`Azure.Mcp.Server-3.0.0-beta.16` (2026-06-02 05:22 UTC) + `Template.Mcp.Server-0.0.12-alpha.6380381` (2026-06-01 23:29 UTC)。**模式 D 在 Microsoft 是"Azure 服务入口"——每个 Azure 服务一个 MCP server**（Storage / Key Vault / Monitor / App Insights...），**等于把"模式 A 集中网关"做成了 SaaS 形式**。

---

## 六、本轮最被低估的信号：Inspector 0.22.0 + URL-mode Elicitation

Inspector 0.22.0 (2026-06-04 12:36 UTC，**昨天**) PR #1423 `feat: add URL-mode elicitation support`——**协议还在 RC**（2026-07-28 才正式发布），**官方调试工具已经支持**。

前轮（01:06）讲过 2026-07-28 RC 里 **MRTR 模式取代 server-initiated 请求**——`elicitation/create` 改成"客户端用 `inputRequests`/`inputResponses` 走 HTTP 302 跳转"。

**Inspector 0.22.0 已实现 URL-mode elicitation** 意味着：
1. 协议还在 RC，**官方调试工具已支持**——生态会"先按 URL-mode 写客户端实现，再等协议最终版"
2. **网关拦截至关重要**——elicitation URL 跳转到 `evil.com` → 网关要做 allowlist

**对企业架构师的含义**：**网关必须 enforce "elicitation URL 必须在白名单域名内"**——否则会变成任意 URL 重定向漏洞。**本轮扫到的 8 个 MCP Gateway 产品 release notes 里没有任何一个提过 elicitation 防护**——这是 **2026 年 6 月 MCP 网关产品的安全盲点**。

---

## 七、SDK 侧观察

- **Python SDK v1.27.2** (2026-05-29)：bugfix 优先于 feature
- **TypeScript SDK v1.29.0** (2026-03-30)：**3 月后没新版本**——TypeScript 侧可能在大改（协议 2026-07-28 RC 落地前的冻结期）

---

## 八、6 条企业建议（本轮新增）

1. **先决定部署模式再选产品**——4 种模式没有银弹。从"鉴权落点 + 审计合规 + 运维预算"三轴选型。
2. **MCP Gateway 必须能拦截 elicitation URL**——8 个产品**没有任何一个**在 release notes 提过。
3. **选型表里要加"schema migration 策略"列**——ToolHive / IBM 在做，其余产品没说。
4. **sidecar 模式必须冻结 generation**——ToolHive PR #5364 的 downward API 模式值得复用。
5. **SaaS 模式（Cloudflare / Microsoft / Portkey）要先看厂商审计报告**——买的不只是网关，是"数据出境 + 厂商内部 Durable Object 共享"的合规框架。
6. **部署 MCP Inspector URL-mode elicitation 之前**——把"测试环境允许任意 URL，生产环境 enforce allowlist"作为网关默认配置。

---

## 九、本期数字摘要

- **覆盖产品数**：8 个（ToolHive / Archestra / Cloudflare / Docker / kgateway / Microsoft MCP / MCP Inspector / MCP SDK）
- **24h 内新 release**：3 个（kgateway v2.3.2、Archestra v1.2.56/57、Inspector 0.22.0、ToolHive v0.29.1）
- **MRTR / elicitation 支持**：Inspector 已实现 URL-mode；TypeScript SDK 3 月起冻结
- **Cedar / OAuth DCR / CIMD 完整实现**：ToolHive v0.29.0/v0.29.1
- **schema migration 策略明确化**：2 个产品（ToolHive + IBM）

---

## 引用与数据来源

### ToolHive（Stacklok）`stacklok/toolhive`
- v0.29.1 release (2026-06-04 12:48 UTC) — https://github.com/stacklok/toolhive/releases/tag/v0.29.1
- v0.29.0 release body — https://api.github.com/repos/stacklok/toolhive/releases/tags/v0.29.0
- PR #5364 (Freeze MCPServer generation per pod) — https://github.com/stacklok/toolhive/pull/5364
- PR #5448 (Cedar authz + VirtualMCPServer) — https://github.com/stacklok/toolhive/pull/5448
- PR #5361 (obo in MCPExternalAuthConfig) — https://github.com/stacklok/toolhive/pull/5361
- PR #5362 (StorageVersionMigrator controller) — https://github.com/stacklok/toolhive/pull/5362
- PR #5391 (Opt 12 v1beta1 CRDs into storage-version migration) — https://github.com/stacklok/toolhive/pull/5391
- PR #5343 + #5348 (CIMD storage decorator) — https://github.com/stacklok/toolhive/pull/5343 / /5348
- PR #5147 (Opaque upstream token fallback) — https://github.com/stacklok/toolhive/pull/5147
- PR #5372 (authserver DCR → pkg/oauthproto) — https://github.com/stacklok/toolhive/pull/5372

### Archestra `archestra-ai/archestra`
- v1.2.57 (2026-06-04 17:34 UTC) — https://github.com/archestra-ai/archestra/releases/tag/platform-v1.2.57
- v1.2.56 (2026-06-04 13:08 UTC) — https://github.com/archestra-ai/archestra/releases/tag/platform-v1.2.56
- PR #5298 / #5293 / #5290 — https://github.com/archestra-ai/archestra/issues/5298 / 5293 / 5290

### kgateway `kgateway-dev/kgateway`
- v2.3.2 (2026-06-04 17:16 UTC) — https://github.com/kgateway-dev/kgateway/releases/tag/v2.3.2
- Envoy 1.37.3 + CVE-2026-47774 — https://github.com/envoyproxy/envoy/security/advisories/GHSA-22m2-hvr2-xqc8

### Cloudflare / Docker / Microsoft
- Cloudflare graphql-mcp-server@0.2.1 (2026-06-02) — https://github.com/cloudflare/mcp-server-cloudflare/releases/tag/graphql-mcp-server%400.2.1
- Docker v0.42.2 (2026-05-28) — https://github.com/docker/mcp-gateway/releases/tag/v0.42.2
- Microsoft `Azure.Mcp.Server-3.0.0-beta.16` (2026-06-02) — https://github.com/microsoft/mcp/releases

### MCP Inspector / SDK
- Inspector 0.22.0 (2026-06-04 12:36 UTC) — https://github.com/modelcontextprotocol/inspector/releases/tag/0.22.0
- Inspector PR #1423 (URL-mode elicitation) — https://github.com/modelcontextprotocol/inspector/pull/1423
- Python SDK v1.27.2 (2026-05-29) — https://github.com/modelcontextprotocol/python-sdk/releases
- TypeScript SDK v1.29.0 (2026-03-30) — https://github.com/modelcontextprotocol/typescript-sdk/releases

### 上一轮对照（不重复）
- 01:06 轮：MCP 协议 + Auth IG + Registry — `hermes/reports/2026-06-05-0106-aigw-mcp-gateway.md`
- 01:46 轮：5 个产品 — `hermes/reports/2026-06-05-0146-aigw-mcp-gateway-products.md`
