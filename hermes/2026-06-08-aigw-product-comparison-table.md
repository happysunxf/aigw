# AI 网关产品对照表 · 16 款主流实现横评(2026-06)

> **生成时间**:2026-06-08(本地)
> **数据窗口**:2026-05-05 ~ 2026-06-07,基于本地 60+ 份 `aigw-*` 报告
> **覆盖产品**:16 款(横跨通用 LLM Gateway / MCP Gateway / Agent Gateway / 边缘聚合 / 传统 API 网关+AI / 网关注入层 6 个赛道)
> **性质**:纯研究向横评,不做商业推荐,数据全部溯源到本地材料

---

## 引言:为什么需要"产品对照表"

过去 60 天,AI 网关赛道出现**三个独立拐点**:

1. **MCP 升格为网关一等公民**——Envoy AI Gateway 把 `MCPRoute` 从 `v1alpha1` 升 `v1beta1`(2026-04-30),IBM mcp-context-forge 同日 v1.0.0 GA,Archestra 30 天 6 个 patch
2. **Agent Gateway 独立成赛道**——`agentgateway/agentgateway` 2026-06-04 加入 AAIF(Agentic AI Foundation)成为第 4 个 hosted 项目,Solo.io → Linux Foundation 路线闭环
3. **纯转售型窗口期关闭**——v2 长文 5.2 章节判断**纯转售型 AI Gateway 窗口期 ≤ 12 个月**(2026 中结束),必须"做垂直行业 + 业务插件"

这张表的目的:把分散在 60+ 份报告里的产品数据,压成**16 款 × 多维度**的横向坐标,供研究、选型、对标使用。**所有数据均标注来源报告 + 时间锚定**。

---

## 表 1 · 基础定位(16 款 × 9 维度)

| # | 产品 | 厂商/仓库 | 主语言 | 部署形态 | 核心定位 | License | 最新版 | 首版 | 维护节奏 |
|---|------|----------|--------|---------|---------|---------|--------|------|---------|
| 1 | **LiteLLM** | BerriAI / `BerriAI/litellm` | Python | SDK + 服务 | "LLM 瑞士军刀",100+ 厂商适配 | AGPL-3.0 | v1.87.x (持续) | 2023 | 高:日级 commit |
| 2 | **Envoy AI Gateway** | Solo.io / `envoyproxy/ai-gateway` | Go + Envoy ext_proc | Envoy sidecar / gateway | 云原生 / Service Mesh 优先 | Apache 2.0 | v0.7.0 (06-04) | 2025-Q1 | 高:周级 release |
| 3 | **Higress** | 阿里 / `higress-group/higress` | Go + WASM | API GW 插件 | 国内云原生 + API GW 一体 | Apache 2.0 | v2.2.2 (05-26) | 2022 | 中:月级 minor |
| 4 | **Portkey** | Portkey / `Portkey-AI/portkey` | TypeScript | Edge function / 云 | Edge 全球低延迟 + 顶级 dashboard | AGPL-3.0 | v1.15.2 (2026-01 停) | 2023 | 中:main 持续,v1 后 5 月无新 tag |
| 5 | **Apache APISIX** | api7.ai / `apache/apisix` | Lua (OpenResty) | etcd + OpenResty / standalone | 传统 API GW + AI Native | Apache 2.0 | 3.16 (04-08) | 2019 | 高:月级 minor |
| 6 | **IBM mcp-context-forge** | IBM / `IBM/mcp-context-forge` | Python | 独立服务 | 第一个 GA 级 MCP Gateway,FedRAMP/FIPS 路线 | Apache 2.0 | v1.0.2 (05-25) | 2025 | 高:30 天 3 个 patch |
| 7 | **Archestra** | Archestra / `archestra-ai/archestra` | TypeScript / Node | 平台 | "企业优先 + 快速实验"的 MCP/Agent 平台 | Apache 2.0 (推测) | v1.2.57 (06-04) | 2025 | 极高:30 天 6 patch |
| 8 | **Docker mcp-gateway** | Docker / `docker/mcp-gateway` | Go | Docker Desktop 插件 | Docker 生态集成的 MCP Gateway | Apache 2.0 | v0.42.2 (05-28) | 2025-Q3 | 低:2 月 3 patch |
| 9 | **Arcade.dev MCP Gateway** | Arcade / `arcadeai/arcade-mcp` | Python (FastAPI) | 云服务 | "MCP-as-a-Service" + 企业 IAM 集成 | 商业 + OSS | v1.x (持续) | 2024 | 中:周级 commit |
| 10 | **agentgateway** | Solo.io→Linux Foundation / `agentgateway/agentgateway` | Rust 数据面 + Go controller | K8s Gateway API | "Agent Gateway"赛道事实代表,AAIF 第 4 项目 | Apache 2.0 | v1.2.0 (05-14) | 2024-Q4 | 极高:65 分钟 7 PR |
| 11 | **OpenRouter** | OpenRouter / `OpenRouterTeam/openrouter-runner`(deprecated) | 多语言 SDK | 云服务 | "模型聚合 + 生产 AI 基础设施" | 商业 + 部分 OSS | Series B 113M (05-28) | 2023 | 高:5 月 5 篇主博客 |
| 12 | **Cloudflare Workers AI Gateway** | Cloudflare / `cloudflare/ai-gateway` | Workers (V8) | Edge function | Edge AI Gateway,2025-06 进入付费层 | 商业 + 部分 OSS | 持续更新 | 2024 | 高:Workers 迭代 |
| 13 | **Helicone** | Helicone / `Helicone/helicone` | TypeScript / Bun | 云服务 + OSS | "AI Observability 先行者"+ AI Gateway | MIT (OSS) + 商业 | v2025.08.21-1(285 天未发版) | 2023 | 异常:main 在动,无 tag |
| 14 | **Kong AI Gateway** | Kong / `Kong/kong` | Lua (OpenResty) | API GW 插件 | "传统 API GW 头部 + AI 一等公民" | Apache 2.0 (OSS) + 商业 (EE) | OSS 3.9.2 / EE 3.14.0.5 (06-04) | 2015 | 高:3.14 系列 2 月 6 patch |
| 15 | **Bifrost (Maxim)** | Maxim AI / `maxim-ai/bifrost` | Go + Python SDK | 云服务 | "AI Gateway + 评测 + 注入"三合一 | 商业 + OSS | 持续 | 2024-Q3 | 中:周级 commit |
| 16 | **kgateway** | kgateway-dev / `kgateway-dev/kgateway` | Go (Envoy) | K8s Gateway | "Envoy 通用数据面 + LLM provider" | Apache 2.0 | v2.3.2 (05-26) | 2024 | 中:月级 minor |

> **注**:
> - 表中"最新版本"为 2026-05 ~ 2026-06 抓取时观察到的最新 tag/release;OpenRouter 为商业产品,以 Series B 融资事件锚定。
> - **维护节奏**:"高"= 周级 release;"中"= 月级 minor;"极高"= 65 分钟内 7 PR(agentgateway 6-06 案例);"异常"= main 在动但无 tag(Helicone 285 天)。

---

## 表 2 · 核心能力矩阵(16 款 × 12 维度)

| 产品 | 协议归一化 | 多模型 fallback | 语义路由 | 语义缓存 | token 限流 | MCP 支持 | A2A 支持 | 凭证轮换 | 重试退避 | 可观测 | 成本归因 | 审计 |
|------|----------|--------------|---------|---------|----------|---------|---------|---------|---------|--------|---------|------|
| LiteLLM | ✅ 100+ 厂商 ★★★★★ | ✅ 6 策略 | ✅ | ✅ **一等公民** | ✅ | ❌ | ❌ | ✅ | ✅ | 中(自建) | ✅ | ✅ |
| Envoy AI GW | ✅ 30+ translator | ✅ CEL | ✅ | ❌ | ✅ QuotaPolicy runtime | ✅ v1beta1 (4-30) | ❌ | ✅ | ✅ | ★★★★★ (CEL+OTel) | ✅ CEL 动态 | ✅ |
| Higress | ✅ 30+ provider | ✅ | ✅ | ⚠️ 社区方案 | ✅ | ✅ 工具市场 (2025-09) | ❌ | ✅ | ✅ | 中(普米) | ✅ YAML 静态 | ✅ |
| Portkey | ✅ 15+ | ✅ | ✅ | ✅ 付费层 | ✅ | ❌ | ❌ | ✅ | ✅ | ★★★★★ (dashboard) | ✅ JS 静态 | ✅ |
| Apache APISIX 3.16 | ✅ 6 (OpenAI/Anthropic/Bedrock/Vertex/Passthrough) | ✅ priority + fallback_strategy | ✅ | ❌ **无官方插件** | ✅ **`cost_expr` 表达式 (独家)** | ✅ **mcp-bridge (2025-04 最早)** | ❌ | ✅ 加密 etcd | ✅ | ★★★★ (Prom+OTel+ClickHouse) | ✅ Lua 算术表达式 | ✅ |
| IBM mcp-context-forge | ✅ MCP-only | n/a | n/a | n/a | n/a | ✅ **v1.0.0 GA(4-30)** | n/a | ✅ | ✅ | ✅ | n/a | ✅ + PII 脱敏 |
| Archestra | ✅ MCP catalog | n/a | n/a | n/a | ✅ DB pool cap | ✅ team-scoping catalog | n/a | ✅ GitHub App auth | ✅ | ✅ | ✅ | ✅ |
| Docker mcp-gateway | ✅ MCP-only | n/a | n/a | n/a | n/a | ✅ CLI 插件路径稳定 | n/a | n/a | n/a | n/a | n/a | n/a |
| Arcade.dev | ✅ MCP + IAM | n/a | n/a | n/a | n/a | ✅ MCP-as-a-Service | n/a | ✅ OAuth | n/a | n/a | n/a | ✅ |
| agentgateway | ✅ LLM + MCP + A2A | ✅ | ✅ CEL | ❌ | ✅ | ✅ ExtMCP + per-JSON-RPC opt-in | ✅ **AWS Strands reference stack** | ✅ AWS AssumeRole | ✅ pprof+OTel | ✅ **TTFT 走 `gen_ai.server.time_to_first_token`** | ✅ | ✅ |
| OpenRouter | ✅ 400+ 模型 | ✅ MoA (Mixture of Agents) | ✅ `cost_quality_tradeoff` 0-10 | ✅ Response Caching | ✅ per-key 预算 402 | ⚠️ 通过工具调用 | n/a | ✅ | ✅ | ★★★★★ (Guardrails + 5 月新) | ✅ | ✅ **5 月新 Guardrails** |
| Cloudflare AI GW | ✅ OpenAI 兼容 | ✅ | ✅ | ✅ Workers KV | ✅ | ✅ 通过插件 | n/a | ✅ | ✅ | ✅ Workers Analytics | ✅ | ✅ |
| Helicone | ✅ 透传 | ✅ | ✅ | n/a | ✅ | n/a | n/a | ✅ | ✅ | **★★★★★ (Observability 强项)** | ✅ | ✅ |
| Kong AI Gateway | ✅ 10+ provider + DeepSeek/vLLM/Ollama/Databricks | ✅ | ✅ | ⚠️ proxy-cache | ✅ | ✅ **ai-mcp-proxy + ai-mcp-oauth2(2026 GA)** | ✅ **ai-a2a-proxy (3.14.0.0 唯一原生)** | ✅ | ✅ | ✅ Prom + OTel | ✅ bytes-based tokenizer | ✅ |
| Bifrost | ✅ 100+ | ✅ | ✅ | n/a | ✅ | ✅ | n/a | ✅ | ✅ | ✅ | ✅ | ✅ |
| kgateway | ✅ LLM provider | ✅ | ✅ | n/a | ✅ | ⚠️ 2026 路线图 | n/a | ✅ | ✅ | ✅ | ✅ | ✅ |

> **关键观察**:
> - **APISIX 3.16** 在 `cost_expr` 表达式限流上**独家**,5 款通用网关里唯一无官方语义缓存(反常识)。
> - **Envoy AI GW v0.7.0** 用 CEL 动态成本表达式,与 APISIX 算术表达式分庭抗礼。
> - **OpenRouter** 5 月发 Guardrails + MoA + Response Caching + Session-id Stickiness + Auto router = "生产 AI 基础设施 6 件套"。
> - **agentgateway** 是**唯一**把 LLM + MCP + A2A 三个一等公民都做了的网关;Bifrost 路线是"评测+注入"差异化。

---

## 表 3 · MCP 协议支持深度(5 款 MCP Gateway 专项)

| 维度 | Envoy AI Gateway | IBM mcp-context-forge | Archestra | Docker mcp-gateway | Arcade.dev |
|------|-----------------|----------------------|-----------|-------------------|-----------|
| **MCP 资源模型** | `MCPRoute` CRD **v1beta1** (4-30 升格) | FastAPI + A2A 1.0 + MCP proxy | MCP catalog (team-scoping) | CLI 插件路径 | MCP-as-a-Service |
| **多 backend 跟踪** | ✅ per-backend 能力跟踪 (tools/prompts/resources/logging/completions) | ✅ SSRF 防护(禁 302/301/307/308) | ✅ catalog preset 启用回退 | ⚠️ 简单 | ✅ |
| **OAuth2 / 鉴权** | ✅ `MCPRouteOAuth.claimToHeaders` (JWT claim→outbound) | ✅ JWKS、audience、Entra ID、账户锁定 | ✅ GitHub App auth | ❌ | ✅ 企业 IAM |
| **Per-tool 过滤** | ✅ `MCPToolFilter` 支持 `exclude`/`excludeRegex` | ✅ 插件框架 PII filter | ✅ team-scope | n/a | n/a |
| **协议版本跟随** | 2026-07-28 RC | 2025-11-25 compliance harness (GA 锁) | 持续 main 合入 | 缓步 | 持续 |
| **SSRF / 安全** | access log `mcp_tool_name` 可观测 | ⚠️ **breaking**:禁 HTTP 302/301/307/308 | ✅ DB pool cap 限流 | n/a | n/a |
| **治理成熟度** | v1beta1 字段冻结;`MCPBackend` CRD 提案 6-03 closed | FedRAMP/FIPS/STIG 准备 (v1.0.2) | 30 天 6 patch + revert 通道 | Docker 生态绑定 | 企业 IAM 优先 |
| **重要 PR** | #2090 MCPRoute v1beta1 / #2144 MCPBackend / #2047 forwardHeaders | #5033 FIPS / #5013 PII 日志脱敏 / merge queue | #5293 GitHub App / #5298 team-scope / #5302 revert | v0.42.0→.1→.2 路径稳定 | 持续 |

> **核心判断**:
> - **IBM mcp-context-forge** = **"企业合规路线"**;v1.0.0 跳 0.9 直 GA(企业生产可用 MCP 网关需求见顶)
> - **Archestra** = **"企业 + 快速实验"**;每个 PR 都带 hotfix revert 通道,与 IBM "慢稳"风格完全相反
> - **Envoy AI Gateway** = **"协议路线图"**;v1beta1 升格是事实标准信号,`MCPBackend` CRD 拆分与 LLM 侧 `AIServiceBackend + BackendSecurityPolicy` 对齐
> - **Docker mcp-gateway** = **"Docker 生态路线"**;不是独立服务,而是 Docker Desktop 插件
> - **Arcade.dev** = **"MCP-as-a-Service"**;SEP-2207 标准实现代表

---

## 表 4 · 性能与工程指标(16 款 × 7 维度)

| 产品 | 单实例 RPS | SSE P99(1000 并发) | TTFT | MCP 吞吐 | 部署复杂度 | 多租户 | 扩缩容模型 |
|------|----------|-------------------|------|---------|----------|--------|----------|
| LiteLLM | ~500 (3k with gunicorn) | 280ms | 视模型 | n/a | 低 (pip install) | 中(需自建) | 水平(Redis 后端) |
| Envoy AI GW | **10k+** | 30ms | 视 ext_proc | 视 backend | 高(Envoy + Go binary + CRD) | ★★★★★ (CRD) | HPA + xDS |
| Higress | ~3k | 60ms | 视模型 | 视工具市场 | 中(API GW 部署) | 中 | HPA |
| Portkey | 1k+ (Workers) | 50ms | 视模型 | n/a | 低(Edge deploy) | ★★★★★ (header config) | Workers 自动 |
| Apache APISIX 3.16 | **3-5k** | **50ms** (Lua 协程) | 视模型 | 视 mcp-bridge | 中(etcd + OpenResty / standalone) | ★★★★ (consumer + group) | 水平(etcd) |
| IBM mcp-context-forge | 中(Python) | 中 | n/a | 高(GA 级) | 中(FastAPI) | 中 | 水平 |
| Archestra | 中(TS) | 中 | n/a | 高(快速迭代) | 中(平台部署) | ★★★★★ (team-scope) | 水平 |
| Docker mcp-gateway | 视容器 | 视上游 | n/a | 低 | 极低(Docker 插件) | 低 | 容器 |
| Arcade.dev | 云服务 | 云服务 | n/a | 云服务 | 极低(API) | 企业 IAM | 托管 |
| agentgateway | 高(Rust 数据面) | 视 ext_proc | 走 OTel `gen_ai.server.time_to_first_token` | 高(ExtMCP) | 中(K8s Gateway API) | ★★★★★ (listener×route×backend 三维) | HPA + 多 controller |
| OpenRouter | 云服务 | 云服务 | 云服务 | n/a | 极低(API) | ★★★★★ (Workspace) | 托管(自研) |
| Cloudflare AI GW | Edge 全球 | 50ms 级 | Edge | 视插件 | 极低(Workers) | ★★★★★ (Cloudflare 账户) | Edge 自动 |
| Helicone | 中(TS) | 中 | n/a | n/a | 低(云 + OSS) | 中 | 水平 |
| Kong AI Gateway | 中-高(传统 API GW) | 中 | 视插件 | 视 ai-mcp-proxy | 中(传统部署) | ★★★★★ (consumer + ACL) | 水平 |
| Bifrost | 云服务 | 云服务 | 云服务 | 中 | 极低(API) | 中 | 托管 |
| kgateway | 高(Envoy) | 视 LLM | 视 LLM | 2026 路线图 | 中(K8s) | ★★★★ (K8s) | HPA |

> **关键观察**:
> - **Envoy AI GW** 单实例 10k+ RPS 是通用网关里**最强**;但部署门槛高(Envoy + Go binary + CRD)
> - **APISIX 3.16** SSE P99 50ms 来自 Lua/OpenResty 协程 + `ngx.pipe` 零拷贝,接近 Envoy 但部署更轻
> - **agentgateway** 是**唯一**在可观测标签里**显式区分** `kind × backend × listener` 三维多租户的网关(`CEL MinimalHTTPLabels` 防 cardinality 爆炸)
> - **OpenRouter** 6 个月周路由量 5T → 25T tokens(5×),年度 1 quadrillion tokens(自报)

---

## 表 5 · 生态与可观测(16 款 × 8 维度)

| 产品 | OTel `gen_ai.*` 集成 | 成本归因模型 | Redis 后端 | K8s CRD | Dashboard | Python 生态 | JS/TS 生态 | 部署文档完整度 |
|------|---------------------|------------|-----------|---------|-----------|-----------|-----------|--------------|
| LiteLLM | ✅ 自建 | Python 静态表 | 可选 | ❌ | ✅ proxy UI | ★★★★★ | 中 | ★★★★★ |
| Envoy AI GW | ✅ 原生 | **CEL 动态表达式** | 可选 | ✅ AIGatewayRoute | ✅ Envoy Admin | 中(Go 客户端) | 中 | ★★★★ |
| Higress | ✅ | YAML 静态表 | ✅ | ✅ | ✅ | 中 | 中 | ★★★★ |
| Portkey | ✅ | JS 静态表 | 可选 | ❌ | ✅ **顶级** | 中 | ★★★★★ (Vercel) | ★★★★★ |
| Apache APISIX | ✅ + Prom + ClickHouse | **Lua 算术表达式** | 可选 | ✅ | ★★★★ | 中(SDK) | 中(SDK) | ★★★★★ |
| IBM mcp-context-forge | ✅ | n/a(MCP 网关) | ✅ | ❌ | ✅ shadcn/ui | ★★★★★ | 中 | ★★★★ |
| Archestra | ✅ | ✅ | ✅(限流) | ❌ | ✅ | 中 | ★★★★★ | ★★★★ |
| Docker mcp-gateway | ⚠️ 简单 | n/a | ❌ | ❌ | CLI | n/a | n/a | ★★★ |
| Arcade.dev | ✅ | n/a | 托管 | ❌ | ✅ | ★★★★ | ★★★★ | ★★★★ |
| agentgateway | ✅ **TTFT 走 `gen_ai.server.time_to_first_token`** | ✅ | ✅ | ✅ **K8s Gateway API** | ✅ agctl CLI | 中(Rust 客户端) | 中 | ★★★★ |
| OpenRouter | ✅ | ✅ | 托管 | ❌ | ★★★★★ | ★★★★ | ★★★★ | ★★★★★ |
| Cloudflare AI GW | ✅ | ✅ | 托管 | ❌ | ✅ Workers Analytics | 中 | ★★★★★ | ★★★★ |
| Helicone | ✅ **强项** | ✅ | 托管 + OSS | ❌ | ✅ | 中 | ★★★★★ | ★★★★ |
| Kong AI Gateway | ✅ | ✅ bytes-based tokenizer | ✅ | ✅ | ✅ Kong Manager | 中(SDK) | 中(SDK) | ★★★★★ |
| Bifrost | ✅ | ✅ | 托管 | ❌ | ✅ | ★★★★ | ★★★★ | ★★★★ |
| kgateway | ✅ | ✅ | ✅ | ✅ K8s Gateway API | ✅ | 中 | 中 | ★★★★ |

> **关键观察**:
> - **成本归因模型**三类路线:**Python/JS/YAML 静态表**(LiteLLM/Higress/Portkey)、**CEL 动态表达式**(Envoy AI GW)、**Lua 算术表达式 / bytes-based tokenizer**(APISIX/Kong)
> - **OTel `gen_ai.*` 集成**:agentgateway 显式走 `gen_ai.server.time_to_first_token` 字段;Helicone / OpenRouter 都在 GenAI Semantic Conventions GA(2024-11)后跟进
> - **Dashboard 顶级**:Portkey / OpenRouter / Helicone(3 款都是商业为先)
> - **部署文档顶级**:LiteLLM / Portkey / APISIX / Kong / OpenRouter(开源普及型)

---

## 表 6 · 2026 H1 重大里程碑(16 款 × 5 维度)

| # | 产品 | 最新 GA / RC | 收购/融资/合作 | 关键新功能(2026-04 ~ 06) | 数据(模型数/调用量/份额) |
|---|------|-------------|--------------|----------------------|----------------------|
| 1 | LiteLLM | 持续(2026-06 持续 commit) | 2025-08 a16z B 轮 2500 万美元 | record/replay proxy 普惠 / MCP per-server env vars / Anthropic ctx overflow 500→400 | GitHub ~30k★;OpenAI Cookbook 2025-Q3 推荐 |
| 2 | Envoy AI GW | **v0.7.0 (06-04)** | Solo.io 2025-11 收购 api7.ai 部分资产 | Multi-tenant hostname routing / Anthropic→Bedrock Converse / QuotaPolicy runtime / 推理档 `xhigh` | 71 files / +17586 LOC;rules cap 128→15 |
| 3 | Higress | v2.2.2 (05-26) | 阿里 2025-Q3 团队扩编 | modelToHeader 同步 / Bedrock Mantle / cached tokens 透传 | 中国云原生 API GW 22% 份额(API7 数据) |
| 4 | Portkey | v1.15.2 (2026-01 冷冻结) | 2025-09 收购 APIClarity | public routes 鉴权 4 件套 / header forwarding 修复 / 30 个 open PR | 5 月 30 天主战场 |
| 5 | Apache APISIX | **3.16 (04-08)** | n/a(Apache 基金会) | 三段式 AI 架构 / Bedrock / Vertex AI / **`cost_expr` 表达式限流 (独家)** | GitHub ~15.5k★;**中国云原生 API GW 35% 份额**;**2025 mcp-bridge 1.0 GA 比 Kong 早 4 月、比 Envoy 早 8 月** |
| 6 | IBM mcp-context-forge | v1.0.0 GA (4-30) → v1.0.2 (5-25) | n/a | 93 PR 一次性收口 / **breaking: 禁 HTTP 302/301/307/308 (SSRF 防护)** / FIPS / PII 脱敏 | 第一个 GA 级 MCP 网关 |
| 7 | Archestra | v1.2.57 (06-04) | n/a | GitHub App auth / team-scope catalog / DB pool cap / MCP image refresh | **30 天 6 patch + 经常一天 2 个** |
| 8 | Docker mcp-gateway | v0.42.2 (05-28) | n/a | CLI 插件路径稳定 | 2 月 3 patch,缓步 |
| 9 | Arcade.dev | v1.x(持续) | n/a | MCP-as-a-Service + 企业 IAM | SEP-2207 标准实现 |
| 10 | agentgateway | v1.2.0 (05-14) | **2026-06-04 加入 AAIF (第 4 项目)** | ID-JAG 两段 token exchange / Browser OIDC / ExtMCP per-JSON-RPC opt-in / Claude Code 网关层注入(issue #2111) | ~1M 季度 image pulls / ~2K stars / 30 release |
| 11 | OpenRouter | n/a(云服务) | **2026-05-28 Series B $113M (CapitalG 领投,NVentures + ServiceNow/MongoDB/Snowflake/Databricks)** | Guardrails / MoA / Audio API / Response Caching / Session-id Stickiness / **Auto router `cost_quality_tradeoff` 0-10** | **8M+ 开发者 / 400+ 模型 / 周路由量 5T→25T tokens (6 月 5×) / 年度 1 quadrillion tokens** |
| 12 | Cloudflare AI GW | 持续 | 2025-06 商业化 | Workers AI Gateway 付费层 | Cloudflare 生态 |
| 13 | Helicone | **v2025.08.21-1(285 天未发版)** | n/a | **5/14-5/18 AWS 账号被误锁 4 天观测降级**;**CloudWatch 单月烧 $22,475**(debug log 事故);bifrost 前端 2 月未成功生产部署 | 创业公司单点故障典型 |
| 14 | Kong AI Gateway | OSS 3.9.2 / EE 3.14.0.5(06-04 同日) | n/a | 10+ provider (DeepSeek/vLLM/Ollama/Databricks 新增) / **ai-a2a-proxy (3.14.0.0 唯一原生)** / MCP OAuth2 Token Exchange | **3.14 系列 2 月 6 patch(平均 9 天一版)** |
| 15 | Bifrost | 持续 | Maxim AI 商业 | Claude Code 注入 / 评测 + 网关注入 | "网关 + 评测"差异化 |
| 16 | kgateway | v2.3.2 (05-26) | n/a | LLM provider / K8s Gateway API | Envoy 通用数据面延伸 |

> **关键观察**:
> - **2026 H1 最大融资**:OpenRouter $113M Series B (5-28, CapitalG)
> - **2026 H1 最重要组织事件**:agentgateway 加入 AAIF(6-04)+ Solo.io 收 api7.ai 部分资产(2025-11)
> - **2026 H1 关键 protocol 事件**:Envoy AI GW `MCPRoute` v1beta1(4-30)+ IBM mcp-context-forge v1.0.0 GA(同日)
> - **2026 H1 反常识事件**:Helicone 285 天无新 tag(main 持续动但无 release);APISIX mcp-bridge 2025-04 早于 Kong 4 月 + Envoy 8 月

---

## 表 7 · 选型决策树(4 层引导)

### 第一层:主语言 / 部署形态

```
你的主语言 / 部署形态是什么?
├── Python / SDK 集成 → LiteLLM (首选) 或 APISIX (基础设施)
├── Go / K8s 重度 / 高 QPS / 大企业 → Envoy AI Gateway
├── 国内云原生 / API GW + AI GW 一体 / 阿里云 → Higress 或 APISIX
├── TypeScript / Edge 全球部署 → Portkey
├── Rust 数据面 + 多 agent / Agent Gateway 赛道 → agentgateway
├── 传统 API GW 演进(已有 Kong 客户) → Kong AI Gateway
├── 已有 Cloudflare / Workers 生态 → Cloudflare AI Gateway
├── Docker 桌面工具链 → Docker mcp-gateway
├── 企业合规(FedRAMP/FIPS) → IBM mcp-context-forge
├── 企业 MCP 治理 + 快速迭代 → Archestra
└── 纯模型聚合 + 400+ 模型一行接入 → OpenRouter
```

### 第二层:核心痛点

```
你的核心痛点是什么?
├── 100+ 厂商覆盖 / 早期产品 / Python 生态 → LiteLLM
├── 多模型 fallback + 复杂路由策略 + 高 QPS → Envoy AI Gateway
├── 阿里云生态 / 国内合规 + 数据驻留 → Higress
├── Edge 全球低延迟 + 顶级 dashboard → Portkey
├── MCP 桥接 + 表达式成本限流 + 已有 API 网关 → APISIX
├── Agent 治理 + A2A + ID-JAG → agentgateway
├── MCP-as-a-Service + 企业 IAM → Arcade.dev
├── 顶级 AI 观测 / 自部署 → Helicone
└── 纯 LLM 多模型聚合 + 顶级 UX → OpenRouter
```

### 第三层:12 个月路线图

```
未来 12 个月你的关键里程碑?
├── 0-3 月:起 demo,接 2-3 家厂商 → LiteLLM (最快) 或 OpenRouter
├── 0-3 月:已有 API 网关要加 AI 流量 → APISIX / Kong(基础设施复用)
├── 3-9 月:加 1-2 个垂直业务插件 → 任何一家都行
├── 6-12 月:准备 MCP 工具桥接 → APISIX(mcp-bridge 最早)/ Higress / Envoy AI GW
├── 9-12 月:评估自研替换 SaaS → 参考 Envoy AI Gateway ext_proc 模式
├── 12 月+:MCP-aware 升级,准备 agent 网关 → agentgateway / Archestra
└── 终态:大企业自研 → 参考 JPMorgan / Netflix 内部网关模式
```

### 第四层:标准化 / 长期生态

```
你押注哪个标准化方向?
├── OTel GenAI Semantic Conventions(2024-11 GA)→ 所有主流网关已支持,选已有集成
├── MCP(2026-07-28 RC)→ 重点看 Envoy AI GW / IBM mcp-context-forge / Archestra
├── A2A(Google 推)→ Kong 3.14 唯一原生;agentgateway 是 AWS Strands reference
├── CNCF AI Gateway WG(2025-Q4 成立)→ 关注 Envoy AI GW + Higress 贡献
├── Apache 2.0 强诉求 → 排除 LiteLLM / Portkey(AGPL-3) / Helicone(MIT 限制)
└── 国资 / 信创 / 等保 → APISIX / Higress
```

---

## 表 8 · 整合事件时间线(2025-08 ~ 2026-06)

| 时间 | 事件 | 类型 | 含义 |
|------|------|------|------|
| 2025-08 | **LiteLLM a16z B 轮 2500 万美元** | 融资 | B 轮落地,产品商业化加速 |
| 2025-09 | **Portkey 收购 APIClarity** | 收购 | 抢 API 可观测市场 |
| 2025-10 | **Helicone 推出 "AI Agent Observability"** | 产品 | 与 Portkey 正面竞争 |
| 2025-Q3 | **阿里 Higress 团队扩编** | 组织 | 国内 AI GW 重点投入 |
| 2025-11 | **Solo.io 收购 api7.ai 部分资产** | 收购 | API Gateway + AI Gateway 一体化(Envoy AI GW ↔ APISIX 出现合作) |
| 2025-12 | **OpenRouter 收购 Martian** | 收购 | 模型路由 + 路由器合并 |
| 2025-06 | **Cloudflare Workers AI Gateway 商业化** | 商业 | Edge AI Gateway 进入付费层 |
| 2026-02 | **APISIX mcp-bridge 1.0 GA** | 产品 | 比 Kong 早 4 月 / Envoy 早 8 月,占 MCP 网关先发位 |
| 2026-04-08 | **Apache APISIX 3.16 发布** | 产品 | 三段式 AI 架构重构 + Bedrock + Vertex + `cost_expr` 表达式限流 |
| 2026-04-30 | **IBM mcp-context-forge v1.0.0 GA** | 产品 | 跳 v0.9 直接 GA,企业生产可用 MCP 网关需求见顶 |
| 2026-04-30 | **Envoy AI GW `MCPRoute` v1beta1** | 协议 | MCP 升格网关一等公民 |
| 2026-05-28 | **OpenRouter Series B $113M** | 融资 | CapitalG 领投,NVentures + ServiceNow/MongoDB/Snowflake/Databricks 战投 |
| 2026-06-04 | **agentgateway 加入 AAIF** | 组织 | Linux Foundation 第 4 个 hosted 项目 |

---

## 表 9 · 标准化与生态位(2025-2026)

| 标准 / 生态位 | 状态 | 主要推动者 | 影响 |
|--------------|------|----------|------|
| **OpenTelemetry GenAI Semantic Conventions** | GA(2024-11),2025 大面积落地 | OTel WG + 各厂商 | 所有主流 AI 网关已支持 `gen_ai.*` 字段 |
| **MCP(Model Context Protocol)** | 2026-07-28 RC(Anthropic 主导) | Anthropic + 社区 | Envoy AI GW / IBM mcp-context-forge / Archestra / Archestra / Docker 跟进 |
| **CNCF AI Gateway Working Group** | 2025-Q4 成立 | CNCF + Solo.io + api7.ai 等 | 目标统一 AI 网关 API |
| **OpenAI 兼容"事实标准"** | 80% 厂商自报兼容 | OpenAI | 实现差异巨大,需要协议转换层(APISIX `ai-protocols/converters/`) |
| **A2A(Agent-to-Agent)** | Google 推 | Kong 3.14(唯一原生 ai-a2a-proxy)+ agentgateway(AWS Strands reference) | multi-agent 网关层协议 |
| **Apache 2.0 vs AGPL-3.0** | 协议分裂 | AGPL: LiteLLM / Portkey;Apache: Envoy AI GW / Higress / APISIX / Kong | 商业化合规风险 |
| **国家合规 / 等保 / 信创** | 国内市场关键 | APISIX / Higress | 国内中型企业首选 |

---

## 反常识洞察(5 条)

1. **"无官方语义缓存"是 APISIX 3.16 的反常识**——5 款通用网关里**只有 APISIX 没有官方 ai-semantic-cache 插件**;LiteLLM 把它做成"一等公民",Portkey 在付费层。要补必须用 `proxy-cache + body-transformer + 自定义 cache key` 社区方案。

2. **agentgateway 是"唯一"把 LLM + MCP + A2A 三件套都做成"一等公民"的网关**——其他厂商(LiteLLM/Portkey/Envoy AI GW)做 LLM + MCP 两件套;**agent → agent 是第三个一等公民**,这是"Agent Gateway"和"AI Gateway"在 2026 年的**根本分水岭**。

3. **Helicone 285 天无新 release tag 但 main 持续动**——仓库从"日级 tag"切到"main 直发 + Vercel 自动部署"是 GitHub Actions 时代常见优化,**但事故期没有任何 tag 也没有 hotfix 分支**,一旦 main 退化,没有可快速回滚的"已知好版本"可钉;**5/14-5/18 AWS 账号被误锁 4 天**和**CloudWatch 单月烧 $22,475**(一行 debug log)两次事故叠加,暴露了"无 tag"路线的脆弱。

4. **APISIX mcp-bridge 比 Kong 早 4 个月、比 Envoy AI GW 早 8 个月(2025-04 GA)**——APISIX 不只是"传统 API 网关头部",在 MCP 网关赛道是**最早**;但**ai-rag 只支持 Azure**(国内痛点)+ 无 ai-semantic-cache + Lua 生态门槛 = 三个不解决的痛点。

5. **"纯转售型 AI Gateway 窗口期 ≤ 12 个月"**——v2 长文 5.2 章节判断 2026 中结束;要活下去必须"垂直行业网关 + 业务插件"。APISIX 走另一条路:"AI Native API 网关"——让传统 API 网关客户**零成本**升级。

---

## 一句话总结(16 款)

> **通用 LLM Gateway**:LiteLLM(100+ 厂商 + Python 瑞士军刀)/ Envoy AI GW(Go + Envoy ext_proc 云原生最强 10k+ RPS)/ Higress(阿里云 + WASM)/ Portkey(Edge + 顶级 dashboard,2026 节奏放缓)/ **Apache APISIX(Lua/OpenResty + `cost_expr` + 35% 中国份额 + mcp-bridge 最早)**。
> **MCP Gateway**:Envoy AI GW(v1beta1 + `MCPBackend` 提案)/ **IBM mcp-context-forge(第一个 GA + FedRAMP 路线)/ Archestra(企业 + 30 天 6 patch)/ Docker mcp-gateway(Docker 生态)/ Arcade.dev(MCP-as-a-Service)**。
> **Agent Gateway**:**agentgateway(AAIF 第 4 项目 + LLM/MCP/A2A 三一等公民)**。
> **边缘 / 聚合**:**OpenRouter(Series B $113M + 8M 开发者 + 400+ 模型 + 周路由量 25T tokens)/ Cloudflare Workers AI Gateway(Edge)/ Helicone(观测强项但 285 天无 tag)**。
> **传统 API 网关 + AI**:**Kong AI Gateway(3.14 EE + 唯一原生 A2A + MCP OAuth2 Token Exchange)/ kgateway(Envoy 通用数据面)**。
> **网关注入层**:**Bifrost(评测 + 注入,Claude Code 网关层代表)**。

---

## 引用与数据来源(本地报告锚定)

- **v2 长文(主)**:`hermes/reports/2026-06-07-0825-aigw-tech-deepdive-article-v2.md`
- **APISIX 专报**:`hermes/reports/2026-06-07-0730-aigw-apisix-ai-deepdive.md`
- **MCP Gateway 专报**:`hermes/reports/2026-06-05-0146-aigw-mcp-gateway-products.md`
- **MCP Gateway 协议视角**:`hermes/reports/2026-06-05-0106-aigw-mcp-gateway.md`
- **Agent Gateway 系列**(r17~r24,共 8 份)
- **单产品发版追踪**:
  - `hermes/reports/2026-06-06-0013-aigw-kong-release.md`
  - `hermes/reports/2026-06-06-0046-aigw-helicone-release.md`
  - `hermes/reports/2026-06-07-0026-aigw-openrouter-release.md`
  - `hermes/reports/2026-06-07-0739-aigw-portkey-release-r3.md`
- **架构 / 性能基准 r8**:`hermes/reports/2026-06-07-0619-aigw-arch-benchmark-r8.md`
- **LiteLLM release r3**:`hermes/reports/2026-06-07-0706-aigw-litellm-release-r3.md`
- **Higress release v2.2.2**:`hermes/reports/2026-06-05-2134-aigw-release-higress-v222.md`
- **Envoy release**:`hermes/reports/2026-06-05-0750-aigw-envoy-release.md`

> **本地归档**:`/home/ubuntu/hermes/reports/2026-06-08-aigw-product-comparison-table.md`
> **远端目标**:`happysunxf/aigw/hermes/2026-06-08-aigw-product-comparison-table.md`
