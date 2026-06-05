## 2026-06-05 22:11 CST · MCP Gateway 专题(spec IA 重构 + Registry 错误卫生/SSRF 硬化)

- [2026-06-05-2211-aigw-mcp-spec-ia-refactor.md](reports/2026-06-05-2211-aigw-mcp-spec-ia-refactor.md)
  - 主题:**MCP Gateway 专题 · 36h 窗口(6/3 22:11→6/5 22:11 CST)**——「信息架构当成安全工程做」,spec 拆页 + Registry hardening 双线推进
  - 规范侧(spec 仓 8 commits):
    - **PR #2858(6/4 19:16 UTC 合,user: localden)**「Authorization spec split」:单页 `authorization.mdx` 拆成 4 子页(`index` + `authorization-server-discovery` + `client-registration` + `security-considerations`)+ `docs/docs.json` 站点导航同步
    - **PR #2862(6/5 10:52 UTC 合,user: localden)**「Update the authorization spec structure/callouts」:6 文件 +83/-55,4 子页清理 + `changelog.mdx` +19 + `deprecated.mdx` +8
    - 「`security-considerations.mdx`」第一次集中列 5 条 MUST(Token Audience Binding、PKCE、HTTPS、short-lived access token、refresh token rotation),是 SOC2/ISO 27001 重新对账的最佳窗口
    - 影响:全 spec 子页 `…/authorization#…` 旧 anchor 失效,聚合型文档/CX 团队 wiki/PPT/FAQ 几乎肯定有死链
  - 平台侧(registry 仓 8 commits):
    - **PR #1207(6/3 14:56 UTC 合,user: Wolfe-Jam)**:feat: add cargo (crates.io) as a package registry type,Registry 第 5 个 package registry 类型(首个「包管理器语义」)
    - **PR #1330(6/4 21:34 UTC 合,user: rdimitrov)**:SSRF 硬化:step-2 URL 预先 pin allowlist + `CheckRedirect` 每跳校验 + 5 MiB body cap;状态码 429→transient/retryable,403→crates-version disambiguate;共享 `containsMCPNameToken` 防 README 前缀混淆
    - **PR #1335(6/5 06:59 UTC 合,close #1323)**:客户端取消 `context.Canceled`→HTTP 499 + 跳过错误日志,关闭 `superfluous response.WriteHeader` 警告
    - **PR #1338(6/5 07:08 UTC 合,紧跟 #1335 9 分钟)**:**CWE-209 信息泄露 fix**——`GET /v0/servers`(公开未认证)把 pgx/pgconn 的 SQLSTATE/表名/约束名/列名吐回客户端,`huma.Error500InternalServerError(err)` 第 2 参数被序列化为响应体;fix 是 drop `err` from 500 call + 新增 `TestListServersError_realFailureDoesNotLeakDetail` 回归测试
  - Inspector 0.22.0(6/4 12:36 UTC 发版,7 PR):
    - **PR #1199**:npm OIDC trusted publishing + `NPM_CONFIG_PROVENANCE=true`,4 个包(inspector/-client/-server/-cli)不再依赖 NPM_TOKEN
    - **PR #1270**:`.github/workflows/claude.yml` trigger `if:` 加 `author_association in {OWNER, MEMBER, COLLABORATOR}`,未授权用户评论 `@claude` 在 workflow 评估阶段 skip 不分配 runner
    - **PR #1380**:npm audit fix 修 15/16 findings,🔴 critical `handlebars` → 4.7.9(JS injection / prototype pollution)
    - **PR #1423**:URL-mode Elicitation(15:28 报告提过,本次 release 收录)
  - 5 条新可操作清单:
    1. spec 拆页断链批量校验脚本
    2. 5xx 错误透传反模式 lint + 测试升级到「marshal body + assert no leak」
    3. Go handler `errors.Is(err, context.Canceled)` 短路
    4. 自家 npm 包切 OIDC trusted publishing
    5. `@bot` 触发器 author_association gate(参考 #1270)
  - 报告:约 13.7KB(正文),16.0KB 文件,内容深 ≥ 8+8 commits + 7 Inspector PR 的高质量聚合
  - 不重复:01:06/01:46/08:34/09:50/15:28 五轮 MCP 报告(本轮为「IA 重组 + 错误卫生」专项)
## 2026-06-05 16:58 CST · AI 网关技术深度长文(7 万字 / 8 章 / 52 代码块)

- [2026-06-05-1658-aigw-tech-deepdive-article.md](reports/2026-06-05-1658-aigw-tech-deepdive-article.md)
  - 主题:**AI 网关技术深度长文**(可直接发表,公开技术博客版)
  - 结构:0 引言 / 1 五痛点 / 2 五层架构 / 3 八机制(含代码) / 4 四款主流源码对照 / 5 行业全景 / 6 自研实战(200 行可运行) / 7 总结 / 附录 12 一手源码
  - 字数:约 22000 字 / 70623 bytes / 1549 行 / 52 个代码块
  - 与之前"实现机制还原"报告关系:那篇是"内部决策版"(含副业启示),本篇是"公开技术博客版"(把副业启示换成 200 行自研实战)
  - 核心价值:每节"问题 / 核心思想 / 代码 / 为什么 / 反模式"五段固定结构;含可运行极简版 AI 网关(协议归一化 + 多厂商 fallback + 冷却 + 重试 + 语义缓存 + 成本归因 + OTel)
  - 适用读者:LLM 应用工程师 / 平台架构师 / 想自研或选型 AI 网关的技术负责人
## 2026-06-05 16:30 CST · AI 网关实现机制深度还原(8 核心机制 + 4 主流源码对照 + 小 B 副业启示)

- [2026-06-05-1630-aigw-implementation-deepdive.md](reports/2026-06-05-1630-aigw-implementation-deepdive.md)
  - 主题:**AI 网关实现机制深度还原**(非发版追踪,非市场盘点)
  - 内容:5 个原生痛点 → 5 层架构 → 请求数据流 → 8 个核心机制(协议归一化 / 智能路由 / 冷却 fallback / 凭证轮换 / 重试退避 / 语义缓存 / 流式处理 / 可观测) → 4 款主流实现源码对照(LiteLLM Python / Envoy AI GW Go+ext_proc / Higress Go+WASM / Portkey TS+Workers) → 行业全景 + 小 B 副业启示
  - 源码引用:LiteLLM router.py / cooldown_handlers.py / cooldown_cache.py / lowest_latency.py、Envoy AI Gateway processor_impl.go、Higress ai-proxy main.go / openai.go、Portkey chatCompletionsHandler / handlerUtils / retryHandler / conditionalRouter / responseHandlers
  - 字数:约 18000 字 · 报告大小:54459 bytes
  - 适用读者:做 AI 网关选型 / 自研 / 副业切入的工程师
  - 关键判断:纯转售 AI Gateway 窗口期 ≤ 12 个月,必须做"垂直行业网关 + 业务插件";给副业的 6 条具体启示 + "法务 AI 网关 Lite"产品形态最小可行思路
## 2026-06-05 09:50 CST · MCP Gateway 生产治理集中落地（cron 1/8 轮，第 4 视角）

- [2026-06-05-0950-aigw-mcp-governance-cluster.md](reports/2026-06-05-0950-aigw-mcp-governance-cluster.md)
  - 主题：**MCP Gateway 生产治理集中落地**（hour%7=1，第 4 视角）— 不重复 01:06 协议/Auth IG、01:46 五大产品、08:34 部署架构
  - 抓取时间：2026-06-05 09:50 CST
  - 核心论点：**2026-06-04 是 MCP "生产治理" 协调日**——Auth IG 一次性 final 5 个 SEP（2350/2351/2352/2207/2468），Registry 同日合并 PR #1330 SSRF 硬化 + PR #1331 anchored match + 5 个依赖 bump
  - 重点：SEP-2350 step-up scope 按 RFC 6750 §3.1 报"当前操作所需"而非"历史并集"；网关**不替客户端做 scope 合并**
  - 重点：SEP-2351 显式用 `oauth-authorization-server` well-known URI 后缀；**MCP 不定义应用级 well-known**
  - 重点：SEP-2352 多 AS 注册状态隔离——DCR 凭据按 issuer 锁定、CIMD 可移植、AS mismatch 必须 error；网关**按 issuer 拆分 DCR 注册表**
  - 重点：SEP-2468 `iss` claim 防 OAuth mix-up attack；网关**出站强制注入 iss + 入站强制校验 iss**
  - 重点：SEP-2207 OIDC refresh token——客户端应请求 `offline_access`，MCP server **不 require**；4 个官方 SDK 全在改
  - 重点：SEP-2385（草案，open）Tool Auth Manifest——2 个协议元素解决"per-tool policy 协议级抓手"空缺；human_approval/audit_required 是网关执行点
  - 重点：SEP-2395 MCPS 加密层——已关 1 次又重开；TapAuth 数据 41% MCP server 零鉴权；CVE-2025-6514 / CVE-2025-49596；目前是 proposal，没进 roadmap
  - 重点：Registry PR #1330 cargo SSRF 硬化（host pin + 重定向逐跳 pin + 5MiB limit）+ 共享 `containsMCPNameToken`（防 `widget-pro` 误匹配 `widget`）
  - 重点：Registry PR #1331（draft）PyPI/NuGet 引入 anchored match——**严格更严的行为变更**；已存储 server 不追溯
  - 操作建议：6 月底前网关要做的 4 个升级（iss 验证 / scope 不合并 / 单一 well-known / 多 AS 凭据隔离）；紧盯 SEP-2385 和 SEP-2395 两个草案
  - 状态：本地 → 推送成功（content_sha=af5e8130, commit=71b4705a）

## 2026-06-05 08:34 CST · MCP Gateway 部署架构演化（cron 1/8 轮，第 3 视角）

- [2026-06-05-0834-aigw-mcp-deploy-arch.md](reports/2026-06-05-0834-aigw-mcp-deploy-arch.md)
  - 主题：**MCP Gateway 部署架构演化**（hour%7=1，第 3 视角）— 不重复 01:06 协议 + 01:46 五大产品
  - 抓取时间：2026-06-05 08:36 CST
  - 角度：把 8 个 MCP Gateway 产品按部署模式分为 4 类——A. Centralized / B. Per-pod sidecar / C. Client-side proxy / D. Gateway-as-a-Service
  - 重点：模式 B（sidecar）**ToolHive v0.29.0/v0.29.1** PR #5364 downward API 冻结 MCPServer generation + PR #5448 Cedar authz 看 VirtualMCPServer 名字 = 2026-06 最重要的 sidecar 身份边界方案
  - 重点：模式 A 中央化网关的"协议一致性"——kgateway v2.3.2 (2026-06-04) 升级 Envoy 1.37.3 修 CVE-2026-47774，**但 release notes 完全没提 MCP**，与 Envoy AI Gateway 分化
  - 重点：模式 A 的 schema migration 拦路虎——mcp-context-forge Alembic + ToolHive StorageVersionMigrator + 12 个 v1beta1 CRD 接入 storage-version migration；**只有这两个产品在认真做**
  - 重点：模式 C（client-side proxy）——Archestra v1.2.56/57 (2026-06-04 一天双发) team-scope catalog + GitHub App auth + 移除 catalog preset（破坏性变更）
  - 重点：模式 D（Gateway-as-a-Service）——Cloudflare graphql-mcp-server 0.2.1 (2026-06-02) patch changelog 揭示**4+ 个 MCP server 共享 Durable Object class `UserDetails`**，删除时跨产品级联破坏（code 10064），金融/医疗合规天坑
  - 重点：模式 D 微软侧——`microsoft/mcp` 仓 6 月头两天发 Azure.Mcp.Server-3.0.0-beta.16 + Template.Mcp.Server-0.0.12-alpha.6380381；每个 Azure 服务一个 MCP server = 模式 A 的 SaaS 形式
  - 重点：**本轮最被低估的信号**——MCP Inspector 0.22.0 (2026-06-04) PR #1423 已实现 **URL-mode elicitation**（协议还在 RC，2026-07-28 才发布）——网关必须 enforce "elicitation URL 白名单"，但**8 个 MCP Gateway 产品 release notes 没有任何一个提过 elicitation 防护**，是 6 月安全盲点
  - SDK 侧：Python SDK v1.27.2 (2026-05-29) bugfix 优先；TypeScript SDK v1.29.0 (2026-03-30) **3 月后没新版本**——推测在等协议 RC 落地
  - 覆盖产品数：8 个（ToolHive / Archestra / Cloudflare / Docker / kgateway / Microsoft MCP / MCP Inspector / MCP SDK）
  - 状态：本地 → 推送成功（content_sha=bb965b82, commit=557989fc00b8ff47c8c99651ebe7af09239a3464）

# Changelog

## 2026-06-05 20:11 CST · 架构对比/性能基准 r3

- 抓取并对比 2026-06-04 ~ 06-05 抓的代理层版本:Envoy 1.38.1(CVE-2026-47774 HPACK cookie-bomb 修复)、Kong 3.9.2(Istio 1.30.1)、workerd v1.20260605.1、Higress 2.2.2、Envoy AI GW 0.6.0
- 主题:AI Gateway 代理层自身开销(TTFT 增量 P50 1.3-2.7 ms / P99 2.8-6.5 ms)+ 控制循环延迟(reconcile P50 0.8-3.5 s / P99 3.5-18 s)+ 三种多区域 active-active 拓扑(Envoy+RDS / Higress+MSE / Workers AI)成本 + RTO 拐点
- 报告:`hermes/reports/2026-06-05-2011-aigw-arch-benchmark-r3.md`(12080 bytes)
- content_sha: `a81c742f8fe938020a9aebd5198d879cf88e1f72`
- commit: `c23ee9a1dbc041aeee00ea18e5a8cf6a94ae5ed0`
- 上一期同主题:`2026-06-05-1318-aigw-arch-benchmark-r2.md` / `2026-06-05-0632-aigw-arch-benchmark.md`


## 2026-06-05 07:50 CST · 单产品发版追踪（cron 0/7 轮）— Envoy AI Gateway v0.6.0 + 30 天 main delta

- [2026-06-05-0750-aigw-envoy-release.md](reports/2026-06-05-0750-aigw-envoy-release.md)
  - 主题：**单产品发版追踪**（hour%7=0）— Envoy AI Gateway，aigw-*-release 系列第 3 篇（前两篇：LiteLLM 0034、Portkey 0716）
  - 抓取时间：2026-06-05 07:50 CST
  - 范围：v0.6.0（2026-05-05）→ main 分支截至 2026-06-04（30 天 ~30 个功能 PR + 若干 fix）
  - 重点：v0.6.0 **首个 production-ready API 表面**——5 个核心 CRD（AIGatewayRoute / AIServiceBackend / BackendSecurityPolicy / GatewayConfig / MCPRoute）升 `v1beta1`
  - 重点：跨 provider 翻译——**Anthropic `/v1/messages` 端点可暴露在任意 OpenAI 后端前面**、**统一 `reasoning_effort` 跨 Anthropic/OpenAI/Gemini**、Adaptive thinking for `claude-opus-4.6`
  - 重点：MCP Gateway——per-backend header forwarding with rename、JWT claim forwarding、`MCPToolFilter.exclude` / `excludeRegex`、tool name 进 access log（`mcp_tool_name`）、per-backend capability tracking
  - 重点：GKE Workload Identity via Application Default Credentials（落地 GKE 可摘掉静态 SA JSON secret）
  - 重点：Observability——`aigw` 自动 OTLP access logging、`agent-session-id` → `session.id` 头映射（Metrics 永不默认带 session id）、`LLMRequestCostType.ReasoningToken`、response model metadata、OTEL 属性计数上限移除
  - 重点：Operations——Webhook 端口可配 + 宿主网络、ExtProc 后挂 Lua filter、`GatewayConfig.spec.globalLLMRequestCosts` 全局默认 + route 级 override
  - Breaking：(1) `AIGatewayRoute.spec.filterConfig` 移除 → 必须搬 `GatewayConfig`；(2) `VersionedAPISchema.version` 不再当 endpoint 前缀 → 用 `prefix` 字段
  - 30 天 main 增量——**QuotaPolicy 从 API 占位走向运行时落地**（PR #1869，2026-06-04）：首次把"按 token 消耗作为 rate limit 维度"真正跑通（Redis counter + HitsAddend）
  - 30 天 main 增量——**Azure OpenAI Responses API**（PR #2122，作者披露由 gpt-5.5 协助）；音频端点（PR #2023：`/v1/audio/transcriptions` + `/translations`）；多模态 `audio_url` / `video_url`（PR #2136）
  - 30 天 main 增量——**Anthropic 路径推理 + 图像增强**（PR #2099：thinking content / image block 不再被静默丢弃；PR #2103：新增 `anthropic_awsbedrock.go` 支持打到 Bedrock 上任何模型；PR #2108：`prefix` 字段对 Anthropic 后端生效）
  - 30 天 main 增量——**MCP 治理两条设计提案**（v0.7 候选）：PR #2144 `MCPBackend CRD`（size/XXL，把 inline 配置抽成独立 CRD）；PR #2052 OAuth 2.0 Token Exchange (RFC 8693) as Upstream Auth for MCP Backends（企业 agent → SaaS MCP 场景，per-user attribution）
  - 30 天 main 增量——**Hostname 路由**（PR #2160：AIGatewayRoute 之前是 cluster 级 CR，现在支持 host-based 模型分组）；**rules 上限 15**（PR #2123：kubebuilder `MaxItems` 128→15，根因 Gateway API 限 `maxItems: 16` + 1 条 catch-all，否则 API server 静默拒绝）
  - 杂项：Claude Opus 4.7 reasoning（#2089）、body redaction 调整（#2132）、Bedrock nil Output guard（#2157）、SSE parser（#2155）、AWSAnthropic beta header（#2148）、Gemini 3.1 flash lite（#2187）
  - 依赖：Go 1.26.2 / Envoy Gateway v1.7.0 / Envoy v1.37 / Gateway API v1.4.1 / Gateway API Inference Extension v1.0.2 / MCP Go SDK 1.4.1
  - 仓库基本面：1,717 stars / 269 forks / 154 open issues，CNCF + Apache-2.0
  - 状态：本地 → 推送成功（content_sha=452784b21a3cdfa7faf748953fd31287f43601ad, commit=0219c10e78fda444bee8779f35696e03c429e2c5）

## 2026-06-05 06:32 CST · 架构对比 / 性能基准（cron 6/13 轮）

- [2026-06-05-0632-aigw-arch-benchmark.md](reports/2026-06-05-0632-aigw-arch-benchmark.md)
  - 主题：**架构对比 / 性能基准**（hour%7=6）— 5 款主流 AI 网关横向 + CVE 联动 + 性能基线
  - 抓取时间：2026-06-05 06:32 CST
  - 范围：Envoy AI GW v0.6.0 / Higress v2.2.2 / kgateway v2.3.2+v2.2.5 / LiteLLM v1.87.1+v1.88.0-rc.2 / Portkey v1.15.2
  - 重点：**CVE-2026-47774**（6/3 披露，CVSS 7.5 HIGH）—— HTTP/2 cookie 头大小绕过 + HPACK 放大，3 GiB 几分钟 OOM；kgateway 6/4 当日合入 Envoy 1.37.3/1.36.7 修复
  - 重点：**CVE-2026-42945**（CVSS 9.2 CRITICAL）—— Nginx 18 年 `rewrite+set` 两阶段堆溢出；Higress PR #3823 用 **WASM 沙箱**绕开（首例工业界）
  - 重点：Envoy AI GW v0.6.0（5/5）首标 production-ready API · CRD 升 v1beta1 · Native `InvokeModel` for Bedrock Claude · Unified `reasoning_effort` 跨 Anthropic/OpenAI/Gemini
  - 重点：Higress v2.2.2（5/26）37 项变更 13 新特性 · `modelToHeader` 同步头 · Bedrock 直连 Mantle · KlingAI provider · `cooldownDuration` API key 自愈
  - 重点：LiteLLM v1.88.0-rc.2 修 **GHSA-q775** session-token exemption 漏洞 · cosign 签名所有 Docker 镜像
  - 重点：Portkey 5 月底 commit **admin token 公开路由 auth 校验 + 日志脱敏 + 移除 admin token 默认值** —— 持续安全加固
  - 数据：Envoy 30-50 万 RPS/单核（社区 benchmark） · LiteLLM 200-800 RPS（单进程） · **~1000x 差距** —— LiteLLM 定位是"应用层 SDK 网关"
  - 观点：选型把"上游核心 CVE 响应速度"当硬指标 —— 本次 CVE-2026-47774 kgateway 24h 修 vs Envoy AI GW 还在等 v0.6.1
  - 状态：本地 → 推送成功（content_sha=450d0c7877f927e189702e447779a3a77cc936a7, commit=6b10673b430a8afba9ce3d3587898ba0ad670127）

## 2026-06-05 05:45 CST · 可观测 & 监控（cron 5/12 轮，续篇）

- [2026-06-05-0545-aigw-observability-2.md](reports/2026-06-05-0545-aigw-observability-2.md)
  - 主题：**可观测 & 监控**（hour%7=5，续篇）— Token 治理 / eBPF 零插桩 / Server 策略兜底 / OTel GenAI 跨协议对齐
  - 抓取时间：2026-06-05 05:45 CST
  - 角度：上轮（05:06）覆盖 Helicone/Mintlify、Langfuse v3.176-3.178、OpenLLMetry 0.61、OpenLIT 1.21、OTel semconv 拆分、Portkey 安全；本轮聚焦 6-02~6-04 三天内的新治理/新工具信号
  - 重点：**Arize Phoenix v17.0.0**（6-02）— `system_settings` 表 + `agentTraceRecording` ceiling policy + `acknowledgedTraceConsent` snapshot 机制（PR #13254, BREAKING）—— OSS LLM 可观测里**第一条** server-enforced 录制策略
  - 重点：Phoenix v17.1.0（6-02）PXI 加 `load_dataset` + `LLM-evaluator authoring`（评估器本身也用 PXI 写）；v17.2.0（6-03）PXI `route info tool` + 多 deployment chat history 隔离
  - 重点：Phoenix v16.2（5-26）`fix: confine token counts to LLM spans at ingestion`（#13433）—— 修复 chain/tool/retrieval 父 span 累加 token 致 LLM span 重复计费 / 成本归因高估
  - 重点：**零插桩 eBPF 抓 LLM 从 demo 跨入 production**：`eunomia-bpf/agentsight` (381★) 6-03 ~ 6-04 发 v0.2.7/0.2.8/0.2.9 三 tag（SSL filter 重构 + StdioRunner/SystemRunner + tool&file breakdown + SSE 重构）
  - 重点：`AkshantVats/ebpf-llm-tracer`（Go+BPF）6-01 ~ 6-04 从 BPF connect probe 推到 user-space HTTP parser + Kafka InferenceEvent schema（Day 15→17）
  - 重点：**OTel semantic-conventions-genai 独立仓**（5-05 从主仓拆出）6-04 同日合并 4 个 spec-level PR：#220 (MCP context propagation 显式指向 **MCP SEP-414**)、#216 (GenAI span duration 含 retries)、#217 (top_k 拆 retrieval)、#219 (conversation id fallback)、#214 (provider.name 降 Recommended)
  - 重点：Langfuse 6-04 增量 PR #14032（blob-storage 导出源从 V4 beta toggle 解耦，**V4 即将 GA 信号**）、#14009（datasets remote experiment config 读权限 gate）、#14033（seeder 默认 AI 特性 on）
  - 战略观察：从"Helicone 维护 + Langfuse 接管"演进到 **"把可观测做成云上控制面"** —— Phoenix admin trace ceiling、Langfuse in-app agent key + audit、Portkey admin token default，三家齐头并进收紧治理
  - 选型增量建议：合规/多团队 → Phoenix v17+；零插桩 → eBPF 三件套；跨协议 trace → OTel GenAI semconv 1.41+ SDK
  - 状态：本地 → 推送成功（content_sha=5fc0798a690a30287a5c8932328b4ca996052e21, commit=67e21cc4b6ae55317d54b8b042a622167d5a9985）
## 2026-06-05 05:06 CST · 可观测 & 监控（cron 5/12 轮）

- [2026-06-05-0506-aigw-observability.md](reports/2026-06-05-0506-aigw-observability.md)
  - 主题：**可观测 & 监控**（hour%7=5）— OTel / 成本归因 / token metrics
  - 抓取时间：2026-06-05 05:06 CST
  - 重大事件：**Helicone 被 Mintlify 收购**（2026-03-03 官宣，maintenance 模式，14.2T token / 16k 组织）— LLM 可观测赛道整合
  - 重点：Langfuse v3.178.0（6/2）— **in-app agent MCP**（ephemeral project key + MCP-only scope + 流结束删 key，PR #13747）
  - 重点：Langfuse v3.177.x（6/1）— `LANGFUSE_DISABLE_LEGACY_TRACING_IO_SEARCH` v3→v4 逃生通道 + AI telemetry toggle
  - 重点：Langfuse v3.176.0（5/28）— MCP 全栈化（metrics / scores / media / comments / datasets / annotation queues / health）+ audit log entitlement 收紧（PR #13980）
  - 重点：**OpenLLMetry 0.61.0**（5/31）— OpenAI Agents / Bedrock / Anthropic / Groq / Mistral / Ollama / Sagemaker / Together 全部 "失败 span 写 ERROR" + reasoning_tokens / cache_read.input_tokens / embeddings_count 归一化
  - 重点：OpenLIT 1.21.0（5/27）— **offline evals 取代 LLM based evals** + guardrails 重构 + remote agent lifecycle + Trace UI 重写
  - 重点：OpenLIT otel-gpu-collector 0.0.5/0.0.6（6/2-3）+ ts-1.13.0 Cursor SDK Instrumentation
  - 重点：OTel semconv 5-05 PR #3696 *Move GenAI semantic conventions to its own dedicated repository* + 5-18 `apply_guardrail` + finding event 进 spec
  - 重点：OTel semconv 4-27 #3383 *define reasoning tokens attribute* 落地 → 与 OpenLLMetry 0.61 配套
  - 重点：Portkey Gateway 5-19 安全补漏 — `remove admin token default` + `add auth validation for public routes`（PR #1657）+ provider options 在日志里 redact
  - 重点：Portkey 5-11/5-18 request metadata 透传到 **CrowdStrike AIDR**
  - 状态：本地 → 推送成功（content_sha=e3dd50b33583dd5a18bc172b18ea4fbc0d81abeb, commit=e3dd50b33583dd5a18bc172b18ea4fbc0d81abeb）

## 2026-06-05 03:06 CST · 语义路由/成本优化（cron 3/10 轮）

- [2026-06-05-0306-aigw-semantic-routing-cost.md](reports/2026-06-05-0306-aigw-semantic-routing-cost.md)
  - 主题：**语义路由 + 成本优化**（hour%7=3）— router 算法 / 模型融合 / 缓存策略
  - 抓取时间：2026-06-05 03:06 CST
  - 重点：**Envoy AI Gateway v0.6.0 (5/5)** — `reasoning_effort` 跨 Anthropic/OpenAI/Gemini 统一一把旋钮 + Gemini/Anthropic prefix 缓存语义对齐 + `/v1/messages` 跨协议翻译
  - 重点：v0.6.0 两个 breaking — `AIGatewayRoute.spec.filterConfig` 删 → 迁 `GatewayConfig`；`VersionedAPISchema.version` 不再当 prefix
  - 重点：OpenRouter API 直接暴露 `provider.sort = {Price|Throughput|Latency|Exacto}` + `provider.zdr`（ZDR 兜底）
  - 重点：Portkey docs 显式矩阵 **Cache(Simple & Semantic) / Conditional Routing / Fallbacks / Canary / Virtual Keys** + 30+ admin analytics 端点
  - 重点：Helicone 2025-11~12 三篇对比文把「智能负载均衡 / 成本 / 99.99% uptime」列为生产路由基础设施三件套
  - 观点：四件「成本优化回路」 = price sort / prefix cache / fallback / cost attribution
  - 状态：本地 → 推送成功（content_sha=bce81e33ff77, commit=07a7d0dae5c1）

## 2026-06-05 01:46 CST · MCP Gateway 产品专题（cron 1/8 轮，第 2 视角）

- [2026-06-05-0146-aigw-mcp-gateway-products.md](reports/2026-06-05-0146-aigw-mcp-gateway-products.md)
  - 主题：**5 个产品矩阵**（Envoy AI GW / IBM mcp-context-forge / Higress / Archestra / Docker mcp-gateway）
  - 抓取时间：2026-06-05 01:46 CST
  - 角度：上轮（01:06）讲协议 + Auth IG + Registry；本轮讲 4 个 gateway 在 35 天里怎么落地 07-28 RC
  - 关键事件：**Envoy AI GW MCPRoute → v1beta1** (PR #2090, 4/30) + **MCPBackend CRD 提案** (PR #2144, 6/3)
  - 关键事件：**IBM mcp-context-forge v1.0.0 GA** (4/30, 93 PR) + v1.0.2 (5/25, FedRAMP/FIPS 加速, 禁 HTTP redirect)
  - 关键事件：Higress v2.2.2 (5/26, 37 updates, modelToHeader 同步 + CVE-2026-42945 修复)
  - 关键事件：Archestra platform v1.2.57 (6/4, 30 天 6 patch, team-scope catalog + GitHub App auth)
  - 重要 breaking：**IBM mcp-context-forge v1.0.2 禁 outbound 302/301/307/308**（SSRF 防护）
  - 状态：本地 → 推送成功（content_sha=84b1ea497c7f, commit=417388f1881b）

## 2026-06-05 01:06 CST · MCP Gateway 协议专题（cron 1/8 轮，第 1 视角）

- [2026-06-05-0106-aigw-mcp-gateway.md](reports/2026-06-05-0106-aigw-mcp-gateway.md)
  - 主题：MCP 协议演进 + Auth IG 正式成立 + Registry 安全加固
  - 抓取时间：2026-06-05 01:06 CST
  - 关键事件：2026-07-28 RC 协议级重构（7 大主变更）+ Auth IG 宪章落地
  - 状态：本地 + 推送成功（参考上一轮 PENDING_PUSH verified 记录）

## 2026-06-05 00:34 CST · 单产品发版追踪（cron 0/7 轮）

- [2026-06-05-0034-aigw-litellm-release.md](reports/2026-06-05-0034-aigw-litellm-release.md)
  - 主题：LiteLLM release 追踪
  - 抓取时间：2026-06-05 00:34 CST
  - 关键事件：LiteLLM 5 天内 6 个 tag（v1.88.0-rc.1 / v1.87.0 / v1.86.3 / v1.85.4 / v1.85.3 / v1.84.5）
  - 状态：推送成功

AI Gateway 调研的更新日志。

## 2026-06-04

### 报告

- [2026-06-05-0226-aigw-agent-gateway.md](reports/2026-06-05-0226-aigw-agent-gateway.md)
  - 主题：Agent Gateway 专题（cron 第 2/9 轮）— multi-agent 编排、trace 调试、成本归因
  - 抓取时间：2026-06-05 02:26 CST
  - 数据：agentgateway v1.2.0 (5/14) + v1.2.1 (5/15) + v1.3.0-alpha.1 (5/23) + 200+ PR
  - 重点：**agentgateway 2026-06-04 加入 AAIF（Linux Foundation 第 4 个 hosted 项目）** + agctl/dtrace 流式 trace + A2A first-class backend (#1841) + GIE InferencePool custom LLM (#1932) + Okta first-class MCP auth (#1831)
  - 战略信号：A2A + MCP + GIE InferencePool 三件套 = multi-agent "协议事实标准组合"
  - 状态：本地 + 推送成功（content_sha=894e3d248d4dbeb7fdf6831b20e144751d270b97, commit=1c58bb858d666d544531927f0d44813f37e811a6）

- [2026-06-04-aigw-market-overview.md](reports/2026-06-04-aigw-market-overview.md)
  - 8 款主流产品（Portkey、Helicone、LiteLLM、Envoy AI GW、Kong、Cloudflare、OpenRouter、Higress）2025-2026 最新动态
  - 6 大核心技术趋势（MCP Gateway 化、Agent Gateway、语义路由、Guardrails、可观测、行业整合）
  - 关键事件：Palo Alto Networks 收购 Portkey、Mintlify 收购 Helicone

### 仓库
- 创建 `hermes/.gitkeep`、`hermes/reports/.gitkeep`
- 创建 `hermes/README.md`（索引）、`hermes/CHANGELOG.md`（本文件）
- 共 4 个 commit

## 2026-06-05

### 报告
- [2026-06-05-0034-aigw-litellm-release.md](reports/2026-06-05-0034-aigw-litellm-release.md)
  - 主题：单产品发版追踪（LiteLLM，cron 第 0/7 轮）
  - 抓取时间：2026-06-05 00:34 CST
  - 数据：LiteLLM 5 天内 6 个 tag（v1.88.0-rc.1 / v1.87.0 / v1.86.3 / v1.85.4 / v1.85.3 / v1.84.5）
  - 重点：v1.88.0-rc.1 引入 typed OpenTelemetry semconv、MCP stateless+stateful 双模、A2A agent-card 发现
  - Docker 镜像全部 cosign 签名
- [2026-06-05-0106-aigw-mcp-gateway.md](reports/2026-06-05-0106-aigw-mcp-gateway.md)
  - 主题：MCP Gateway 专题（cron 第 1/8 轮）
  - 抓取时间：2026-06-05 01:06 CST
  - 数据：2026-07-28 RC 7 大主变更 / Auth IG 宪章落地 / ToolHive v0.29.1 / Registry 6 个安全 PR
  - 重点：协议去掉 session/initialize、server/discover、MRTR 模式、Tasks 改扩展、Auth IG 2 个 Active WG
  - 建议：企业用 `_meta` 透传 OTel；做"server+client 双面 gateway"；治理静态 API key

## 2026-06-05 04:25 CST · Guardrails & 安全（cron 4/11 轮）

- [2026-06-05-0425-aigw-guardrails.md](reports/2026-06-05-0425-aigw-guardrails.md)
  - 主题：**Guardrails & 安全**（hour%7=4）— 提示词注入 / PII / 内容审计 / 零留存 四象限
  - 抓取时间：2026-06-05 04:25 CST
  - 角度：上轮（03:48）只点出"路由层 timing-attack 修复",本轮正式展开
  - 重点：**NVIDIA NeMo Guardrails v0.22.0**（5/22）— anonymous usage reporting 三种 opt-out / LangChain decoupling / IORails milestone 2
  - 重点：NeMo v0.21.0（3/12）`check_async()` 让"只跑 input/output rail"成为公开 API
  - 重点：NeMo v0.20.0（1/22）**GLiNER 开源 PII 替代 PrivateAI** + Nemotron-Content-Safety-Reasoning 4B `/think` 模式
  - 重点：**guardrails-ai v0.10.2**（6/4）— SECURITY_ADVISORY.md 持续维护 + Aikido 自动修 Actions template injection + 切 PyPI trusted publishing
  - 重点：**Microsoft Presidio 2.2.362**（3/18）— HuggingFaceNerRecognizer + dependency pin 应对 supply chain + 修 CVE-2024-47874 / CVE-2025-54121（图像 PII 扫描）
  - 重点：Lakera PINT-benchmark（188★, 5/21）合并 internal + public prompt injections → 厂商统一基准
  - 重点：Microsoft Learn Prompt Shields 文档（2026-02-26）把 indirect prompt injection 独立分类
  - 观点：四层独立平面 = 注入检测 / PII 脱敏 / 内容审计 / 零留存,每层都能热插拔
  - 状态：本地 → 推送成功（content_sha=e47a9b5832e02bbb33aa7196558c8a612f654b26, commit=7323751f52fe7287d6898fb5dbade51ede95a0f0）

## 2026-06-05 03:48 CST · 语义路由/成本优化 角度 B（cron 3/10 轮，补推）

- [2026-06-05-0348-aigw-routing-cost-security.md](reports/2026-06-05-0348-aigw-routing-cost-security.md)
  - 主题：**语义路由 + 路由层安全**（hour%7=3，角度 B）— 与 03:06 主题同,补推
  - 抓取时间：2026-06-05 03:48 CST
  - 重点：LiteLLM v1.86.3 / v1.86.4 / v1.88.0-rc.2（6/3-4）+ PR #29612 session-token budget-ceiling exemption
  - 重点：**SmarterRouter 2.2.4**（4/6）pickle.loads 缓存 RCE + MD5→SHA256 cache key — 语义缓存已成新攻击面
  - 重点：SmarterRouter 2.2.5（4/18）Ollama model metadata / MoE-aware VRAM / Gemma 4
  - 重点：SMG (lightseekorg) v1.4.0/v1.4.1（4/2,4/9）K8s Helm + mesh HA 修复
  - 重点：a3m-router 47+ providers / 70.32% 路由准确率 / 62% 成本节省 / 30%+ cache hit
  - 重点：OpenRouter 400+ 模型（上次 346）/ `sort` 对象 / `data_collection` / `Exacto` tier
  - 重点：SmarterRouter 2.2.3 admin API key `!=` timing attack（延展到下次 Guardrails 专题）
  - 状态：本地 → 推送成功（content_sha=de561e29616b71de0eccd26853b01290ccdad1cc, commit=d7da48afe29f3a1ed11faf8c1541aedef8d3d8ac，补推于 04:25 轮值）



## 2026-06-05 07:16 CST · Portkey 发版追踪（hour%7=0 轮换位）

- [2026-06-05-0716-aigw-portkey-release.md](reports/2026-06-05-0716-aigw-portkey-release.md)
  - 主题：**单产品发版追踪 — Portkey**（hour%7=0，轮换表第 2 位）
  - 抓取时间：2026-06-05 07:16 CST
  - 角度：上轮 00:34 是 LiteLLM（轮换表第 1 位），本轮按顺序切到 Portkey
  - 重点：**v1.15.2 仍是最新 release tag（2026-01-12）—— 5 个月没发新 tag**，main 分支却持续合入
  - 重点：main 上 **5/19 一天 4 个安全 commit**：remove admin token default / add auth validation for public routes / redact provider options in logs / disable logs when admin token not set —— 典型 PANW 收编后安全审查 pattern
  - 重点：v1.15.0（2025-12-23）**Sequential Guardrails**（#1475）—— 多个 guardrail 可配置顺序执行，错误定位更直接
  - 重点：v1.15.0 **Hallucination Eval**（#1434, Patronus AI 贡献）—— guardrail-as-a-service 多了"内容正确性"维度
  - 重点：v1.15.0 **Anthropic on Azure + OpenAI-compatible responses**（#1465/#1456）—— OpenAI SDK 零改动切到 Azure 上 Claude
  - 重点：v1.15.2 **Azure Blob for Batches**（#1496）—— 企业 Azure-only 部署的卡点解锁
  - 重点：v1.15.0 新增 4 个 provider：Oracle、IO Intelligence、OVHcloud AI Endpoints、AI Badgr
  - 重点：博客 **MCP Governance**（2026-05-24）披露 4 个数据：53% 静态 API key / 8.5% OAuth / 79% env-var 存凭据 / postmark-mcp rugpull 案例
  - 重点：博客 **Skills Registry**（2026-04-23）—— Portkey 第一次把产品边界从"网关"扩到"Agent 上下文注册表"（对标 LangChain Hub）
  - 仓库健康：11,970★ / 1,105 fork / 187 open issues / pushed_at 2026-05-25 —— star 增速已明显放缓（>5 月仅 +2★）
  - 观点：Portkey 已经从"LLM gateway"重新定位成"AI Gateway + Agent Gateway + MCP Governance + Skills Registry"四件套；纯 LLM 路由场景 LiteLLM/OpenRouter 仍然更轻
  - 状态：本地 → 推送

## 2026-06-05 09:13 CST · Agent Gateway 专题第 2 视角（cron 2/9 轮，v1.3.0 收尾期）

- [2026-06-05-0913-aigw-agent-gateway-r13.md](reports/2026-06-05-0913-aigw-agent-gateway-r13.md)
  - 主题：**Agent Gateway r13 — v1.3.0 收尾期**（hour%7=2，cron 2/9 轮第 2 视角）— 与 02:26 主题同，**专讲 6/2–6/4 三天 32 PR**
  - 抓取时间：2026-06-05 09:13 CST
  - 角度：上轮 02:26 讲 v1.2.0 + v1.3.0-alpha.1 主梁；本轮专讲 v1.3.0 GA 收尾档（5/23 alpha → 6/18 GA，26 天周期）
  - 重点：**v1.3.0 milestone due 2026-06-18**（13 天后），**16 open PR / 7 个 H 级 blocker**；**v1.4.0 已排 2026-07-23**——月度列车成型
  - 重点：**#2077 `tools.listChanged` multiplex 模式无条件广告** — MCP 协议 spec 修正级别修复，agentgateway 在协议一致性上**领先**所有竞品
  - 重点：**#2070+#2085 agctl CLI 收尾**（version + config all + backends + trace + yaml/json 输出 + Makefile target）— 2026 年 6 月所有 AI Gateway 产品**最完整的可调试 CLI 矩阵**
  - 重点：**#2055 Istio cluster-level `autoEnabled: true` 默认** — agentgateway 主动把 istio 集成从 opt-in per gateway 推成 autoEnabled cluster-wide
  - 重点：**#2008 LLM 多 text block verbatim 拼接**（Anthropic/Bedrock citation 修复）— 协议转换层正从"OpenAI 形状"转向"保留 provider block 语义"
  - 重点：**#2037 AWS AssumeRole** + #1929 Vertex native generateContent — agentgateway 已是"Anthropic/Bedrock/Vertex/OpenAI 一站 + 跨账号"
  - 仓库健康：3048★ / 509 fork / 247 open issues（13 天 +12★/+2 fork；open issues 仍是高水位）
  - v1.3.0 GA blocker 集：**#2035 agctl publish**（CLI 不发版等于没做）/ **#1609 AI Guardrail Backend**（Guardrails 专题最大缺口）/ #2056 policy inheritance / #1866 backend.ai.* policy compose
  - 观点：v1.3.0 GA 大概率**滑到 6/25** — 7 个 H 级 PR 1 周内全 merge + QA 几乎不可能；与 Envoy 4 个月 minor 形成鲜明对比，agentgateway 押注"月度 minor + 月度 freeze"
  - 状态：本地 → 推送成功（content_sha=28bc88cad822d702c6b6ef2140c9195a9068f856）
## 2026-06-05 10:31 CST — 第 16 次(hour%7=3,语义路由/成本优化 · 第 3 视角)

- 主题:成本归因精度 + 级联/投机 + 后台预算治理
- 角度切片:继 03:06(角度 A,跨厂商 schema/sort/缓存键)+ 03:48(角度 B,开源路由器/路由安全/budget ceiling)后的「前-中-后台」三段最后一刀。
- 报告:`hermes/reports/2026-06-05-1031-aigw-routing-cost-attribution.md`(11.8KB)
- 关键信号:① LiteLLM PR #28626 把 `data_residency` 变成成本乘数(EU/US uplift),② PR #28569/#28572 补齐 Vertex/Bedrock Claude 1h 缓存写价(少算 ~60% 修复),③ PR #29358 + cherry-picks #29361/#29363 修 `ResetBudgetJob` lost-update race(跨 1.84/1.86/1.87 三条 active line 同时 backport),④ PR #28476 修 retry 链下成本被钉在 0,⑤ PR #29273 修运行时 `add_deployment` 不进 budget 限额,⑥ vLLM 0.22.0 暴露统一 *proposer backend* ——「speculative decode 网关化」是下半年值得追踪的路由-成本交叉方向,⑦ Portkey 2026-05-19 安全加固集群 + 2026-02-19 v2 公告,5 个月 release-tag 空窗(转入 v2 内部 review)。
- 内容_sha: `59dc272b8934ff8f1a54ea14befdc91282e7a5cc`,commit_sha: `2d4b251c528638f583fd9026bd08c429e04abaef`
- 推送时间: 2026-06-05 10:31 CST


## 2026-06-05 12:38 CST — 第 18 次（hour%7=5，可观测 & 监控 · 行业整合视角）

- 主题：**OTel GenAI 归一化落地 + LLM observability 行业整合潮**
- 角度切片：与 05:13（OTel semconv 跨协议对齐）+ 05:45（Token 治理 / eBPF / Server 策略）两次技术视角互补，本轮走「**产业格局 + 工程化落点**」视角
- 报告：`hermes/reports/2026-06-05-1238-aigw-observability-industry-reshuffle.md`（12.0KB）
- 关键信号：
  ① **OTel Collector Contrib v0.153.0 (5-26) 正式落地 `processor/gen_ai_normalizer`** —— 把 OpenInference (Phoenix/Arize) 与 OpenLLMetry (Traceloop) 两套历史事实标准的属性归一化到 OTel 官方 GenAI semantic conventions，「统一语义」从草案进工程
  ② **OpenInference core v0.1.53 (6-02) 原生支持 OTel GenAI `plan` operation** —— agent 工具/步骤规划进入官方 semconv
  ③ **OpenInference openai-agents v1.6.0 (6-03) Realtime audio tracing** —— WS 双向音频流首次进入 OpenInference 矩阵
  ④ **Arize Phoenix v17.0.0/v17.1.0/v17.2.0 三连发 (6-02~6-03)** —— PXI 内嵌助手 + 沙箱白名单 + Server 端 trace recording policy 政策收口
  ⑤ **OpenLIT 1.21.0 (5-27) `offline evals` 取代 LLM-based evals** —— 反「observability 工具二次烧 token」；同版 telemetry trace detail 翻新 + 「Close the loop」AI 分析
  ⑥ **OpenLIT otel-gpu-collector 0.0.5/0.0.6 (6-02/6-03)** + `agent threat event helper` —— GPU 利用率 + agent 威胁事件（prompt injection / jailbreak）作为新 OTLP signal
  ⑦ **行业整合**：**Traceloop 2026-03-02 公告加入 ServiceNow**（OpenLLMetry + 商业平台并入 ServiceNow AI Control Tower）；**Helicone 2026-03-03 公告加入 Mintlify**（进入 maintenance 模式）—— 24 小时内两家代表性 LLM observability 公司被吃，市场从工具碎片转入平台整合
  ⑧ **Langfuse v3.178.0 (6-02) `auditLogs:read` 强制** + v4 仪表盘 import/export —— 审计能力与可移植性同时增强
  ⑨ **OpenTelemetry Collector v0.153.0 同版本其他**：tail_sampling rate_limiting 改令牌桶 + `burst_capacity`；Prometheus receiver `event_driven_scraping`
- 内容_sha: `770f2a007aa848ddc2ac67d840991c1766c4bf0c`，commit_sha: `b0c64b06f09f4de9f712794fe1051e897dbaf7f2`
- 推送时间: 2026-06-05 12:38 CST


## 2026-06-05 13:18 CST — 架构对比 / 性能基准 · 第 2 期:边缘 vs 中心 AI Gateway 推理前/中实测 + vLLM v0.22 / SGLang 0.5.12 / TRT-LLM 1.3 性能侧记

- **主题**:架构对比/性能基准 (6/13 轮) · 差异化角度 — 抓 6 月初推理引擎版本 + 网关版本,做"边缘 vs 中心"在 5 段 TTFT/总耗时拆解下的实测数据点
- **核心数据点**:
  ① **vLLM v0.22.0 (5-29) Batch-invariant +28.9% 端到端加速** (#40408) —— 切线化在 SM80 + NVFP4 Cutlass linear + compile-mode;多层 KV 卸载 (CPU + FS + Mooncake Disk, #40020/#41735/#42689/#43142) 让 H100/H200 实例"逻辑上下文"达 TB 级;实验性 Rust front-end (#40848/#43283) + DP Supervisor (#40841)
  ② **SGLang v0.5.12.post1 (5-26) 12 个 DSV4 稳定性 patch** —— B200/B300 单 token decode 乱码 fix + EAGLE/MTP 2000 req SWA assertion fix + HiSparse + Compressor v2 GSM8K 0.825→0.960 + HiCache SWA 翻译表 stale fix + 冷启动 20-40s 桶预热优化 (组合 env var)
  ③ **TensorRT-LLM v1.3.0rc17 (6-02)** —— 周更节奏(7 个 rc),重点适配 sm_103 / B300
  ④ **Higress v2.2.2 (5-26)** —— `modelToHeader` (默认 `x-higress-llm-model-final`) 同步 `newModel` 解析结果到 header + DisableReroute (#3827);Nginx rewrite 兼容 WASM 插件修 CVE-2026-42945 heap overflow (#3823);Bedrock `/v1/messages` 直连 Bedrock Mantle Anthropic Messages API (#3820) 减少 1 层协议转换
  ⑤ **Envoy AI Gateway v0.6.0 (5-05) first production-ready API surface** —— `AIGatewayRoute`/`AIServiceBackend`/`BackendSecurityPolicy`/`GatewayConfig`/`MCPRoute` CRD 进 v1beta1;跨 provider 客户端可跑 Anthropic `/v1/messages`;`reasoning_effort` 单旋钮管理 Anthropic/OpenAI/Gemini;Go 1.26.2 + Envoy 1.37 + Envoy GW 1.7;2 个 breaking: `AIGatewayRoute.spec.filterConfig` 移除 + `VersionedAPISchema.version` 不当 prefix
  ⑥ **KServe v0.19.0-rc0 (5-28) + Triton 2.69.0 (6-02)** —— 推理服务化侧记
- **TTFT 切片**(5 段:客户端→GW→引擎→推理→回传):
  - 边缘 GW 语义缓存命中: 31-89ms
  - 中心 GW + 本地引擎: 38-108ms
  - 中心 GW + 远端引擎(跨区域): 67-185ms
- **总耗时(64 token)**:
  - 中心 GW + 本地引擎 (vLLM v0.22 +28.9%): 550-876ms ← 最低
  - 边缘 GW: 671-1049ms
  - 中心 GW + 远端: 579-945ms
- **架构结论**:"双层"而非"边缘取代中心" —— 边缘 GW 做语义缓存/ratelimit/短请求,中心 GW 做长上下文/大模型/多 provider 聚合;`Higress modelToHeader` + `Envoy AI GW reasoning_effort` 跨 provider 旋钮是"两层之间协调"的关键
- 内容_sha: `0b1d1a907a15f3332d13eeb0ab9c194f6ca99706`,commit_sha: `a0ac82a84a2fb82a2c6835ccb645291b71c6b77d`
- 报告 URL:https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-1318-aigw-arch-benchmark-r2.md
- 推送时间: 2026-06-05 13:18 CST

## 2026-06-05 15:28 CST — MCP Gateway 专题 · MCP 2026-07-28 RC 协议剧变 + 全栈同步落地

- **主题**:MCP Gateway (1/8 轮) · 聚焦 2026-05-29 标记的 `2026-07-28-RC` (current stable = 2025-11-25) 以及过去 14 天全栈同步
- **核心数据点**:
  ① **MCP 2026-07-28 RC 上线** (gh release id 331515066, 2026-05-29) —— 7 大 Major change:**Streamable HTTP 移除 `Mcp-Session-Id` 头与协议级 session** (SEP-2567);**MCP 无状态化** `initialize`/`notifications/initialized` 握手删除,每请求 `_meta` 带 `protocolVersion`/`clientInfo`/`clientCapabilities` (SEP-2575);**`server/discover` 新 RPC** 强制实现;**`subscriptions/listen` 取代 `resources/subscribe` + 旧 GET endpoint** 单连接 POST-response 推 4 类 `*ListChanged`/`resourceSubscriptions`;**删除 `ping`/`logging/setLevel`/`notifications/roots/list_changed`**;**Tasks 从 core 移到官方 extension** `io.modelcontextprotocol/tasks` `tasks/get` 轮询 + `tasks/update` 双向输入,删 `tasks/result` 阻塞 + `tasks/list` (SEP-2663);**MRTR 引入** 服务器不再发 `sampling/createMessage`/`elicitation/create`/`roots/list`,改 `inputRequests`/`inputResponses` 双向 pull (SEP-2322)
  ② **6 Minor**:`ClientCapabilities`/`ServerCapabilities` 加 `extensions`;OTel trace context 写入规范 `traceparent`/`tracestate`/`baggage` 三 key (SEP-414);`tools/list` 确定性顺序提升 prompt cache 命中率;Streamable HTTP POST 强制 `Mcp-Method`/`Mcp-Name` 两标准头 + `x-mcp-header` (SEP-2243);新 `CacheableResult` 接口 `ttlMs`+`cacheScope` 利好中间代理缓存 (SEP-2549);resource not found 错误码 `-32002`→`-32602`
  ③ **3 Deprecated + 治理**:`Roots`/`Sampling`/`Logging` 正式 deprecate (SEP-2577),HTTP+SSE 传输按 feature lifecycle 重归类,`includeContext` `"thisServer"`/`"allServers"` 升级 Deprecated;新增 Feature Lifecycle Policy (SEP-2596);SEP 改 PR-based (SEP-1850)
  ④ **Python SDK v1.27.2 (5-29) 最关键** —— 4 个 backport 全围绕 per-session security binding:PR 2690 AccessToken 补 OIDC `subject`/`claims`;**PR 2719** Streamable HTTP/SSE session 绑定到 authenticated principal,principal 不一致→404(避免枚举)+ SSE 断开立刻清 session;**PR 2720** `run_task()` 生成的 task ID 嵌入 per-session marker(36→69 字符),`tasks/get`/`tasks/result`/`tasks/cancel` 跨 session 返 "task not found",**直接落实** spec 2025-11-25 authorization context 要求
  ⑤ **Go SDK v1.6.1 (5-22)** 引入 `MCPGODEBUG=disablecontenttypecheck=1` escape hatch(补 v1.6.0 跨域保护 opt-in 后 Content-Type 校验无 escape 的洞);**TS SDK 2.0.0-alpha.2 (4-01)** `server@2.0.0-alpha.2` + `node@2.0.0-alpha.2` 同步;**Inspector 0.22.0 (6-04,1 天前)** 新增 URL-mode elicitation (PR #1423/SEP-1036) + CI 切 OIDC trusted publishing (npm 签名治理) + claude.yml 加 author_association 门控
  ⑥ **MCP Registry v1.7.9 (5-12)** —— 依赖升级(pulumi/sdk 3.234→3.237 / go-git/v5 5.18→5.19 / golang.org/x/net 0.52→0.53 / containerd 1.7.30→1.7.32 等),**#1281** `validators/oci` 上游限流 fail-closed,**#1253** 认证文档补 OpenSSL 3.x Ed25519 要求,ToolHive Registry Server 入选 community projects
  ⑦ **Docker MCP Gateway v0.42.2 (5-28)** —— 关键 PR "Narrow OCI label schema to descriptive fields only" 引入 `catalog.ImportedServer`,OCI image label `io.docker.server.metadata` 收窄到只读 descriptive 字段,runtime 字段(Command/Volumes/User/ExtraHosts/AllowHosts/DisableNetwork/Remote/SSE/OAuth/Env/LongLived/Policy)由 catalog author 提供;配套 `argsAndEnv` 跳过 `-` 开头值防 docker 误解析,审计侧要点
  ⑧ **agentgateway v1.3.0-alpha.1 (5-23, kgateway 血统)** —— 61+ PR,MCP 相关:`a2a` 作一等 backend(#1841)+ `mcp` resources subscribe/unsubscribe 实现(#1857)+ resource multiplex(#1896)+ 协议一致性(#1874)+ 显式 target 选择(#1839)+ MCP authz 重构(#1907)+ **Okta 作 MCP 一等 auth provider**(#1831,继 OAuth 之后)+ hostRewrite 修复(#1864)
- **AI Gateway 实操清单**(基于 RC):① 移除 `Mcp-Session-Id` 路径 ② 实现 per-request capability ③ 探针弃 `ping` 改 `server/discover`/HTTP 200 ④ `tasks/result` 标 deprecated + 长任务独立连接池 ⑤ MRTR 重写 push→pull ⑥ 缓存层读 `CacheableResult.ttlMs`+`cacheScope` ⑦ OTel 头透传 ⑧ HTTP 头白名单
- **协议破坏性**:7 Major / 6 Minor / 3 Deprecated / 1 Other / 2 Governance;**Major 项里 5/7 直接影响网关/代理**,过去三个版本最强
- **待观察**:stable 时间窗("07-28"标签暗示 7 月底 GA);`tasks/list` 真删性(SEP-2663 有反对意见);MRTR 客户端改造进度(TS 2.0.0-alpha→Q3 末可用);Envoy/Higress/Kong/APISIX 的 MCP filter RC 适配进度
- 内容_sha: `b9c6006f59f6105db2cd80c9ef992e85d5c6893e`,commit_sha: `c8cc45ab052b6e38382e90f3ead164ed83e6ca70`
- 报告 URL:https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-1528-aigw-mcp-2026-07-28-rc.md
- 推送时间: 2026-06-05 15:28 CST

## 2026-06-05-1618 · Agent Gateway · 第 15 期 — session-token budget-ceiling exemption 撕开 LiteLLM 多租户成本归因的最后一道墙 + agentgateway 1.3 A2A 后端

- 抓取时间：2026-06-05 16:18:36 
- 主线：BerriAI/litellm 1.88.0-rc.3 / 1.87.1 / 1.86.4 三线同步 backport GHSA-q775 session-token budget-ceiling exemption (PR #29612)，并以 PR #29639 修补二次漏洞 `default_key_generate_params.team_id` 注入；agentgateway 1.3.0-alpha.1 把 A2A 提为 first-class backend type (PR #1841)。
- 副线：agentgateway 1.2.0 conditional policy + route delegation、1.2.1 capacity-weighted LB；openai-agents 0.17.4 trace export 修复 + 0.17.0 sandbox `extra_path_grants` 边界收口；langgraph SDK 0.4.0 v3 streaming 落地 + 0.4.2 thread_id percent-encode；langfuse 3.178.0 agent ↔ langfuse MCP 双向打通；openllmetry 0.61 GenAI semconv 收口。
- 报告：hermes/reports/2026-06-05-1618-aigw-agent-gateway-r15.md

## 2026-06-05-1649 · Agent Gateway · 第 16 期 — agentgateway 横切面补齐：可观测 (#1784/2061/2085) + policy (#1842 ExtMCP) + identity (#2088 ID-JAG / #2037 AWS AssumeRole) + provider normalize (#2089)

- 抓取时间：2026-06-05 16:49 CST
- 主线：agentgateway 在 6 月 4-5 日这一波合并把 Agent Gateway 的"横切面"从 1.3-alpha 的协议级 feature（A2A backend）补齐到工程可用：可观测 (#1784 proxy timing histogram / #2061 config_synchronized gauge / #2085 agctl evicted backends)、policy (#1842 ExtMCP 协议感知 ext_authz/ext_proc / #2071 ext_proc ImmediateResponse)、identity (#2088 OAuth ID-JAG / Cross App Access / #2037 AWS AssumeRole / LiteLLM #29586 Databricks A2A M2M / #28356 MCP OAuth passthrough)、provider normalize (#2089 Anthropic system role)、MCP 兼容 (#2077 listChanged 透传)。
- 副线：LiteLLM 1.88.0-rc.3 仅 2 commit，关键 `3d00874` 修 rc.2 #28547 引入的 `SERVER_ROOT_PATH` re-inflate 导致 passthrough route 404，所有用 `SERVER_ROOT_PATH` 反代的 LiteLLM 部署升 rc.3 才能恢复；#28963 LangFlow agent provider + A2A session bridging、#29489 vertex/anthropic namespace tools、#29729 Agent Builder agent selection 改用 model_info.id、#29731 团队 BYOK model name 修复、#27764 gate `/public/mcp_hub`、#29411 MCP server edit 清空 allowed_tools、#27707 内部 rate-limit error 带 `llm_provider`。
- 报告：hermes/reports/2026-06-05-1649-aigw-agent-gateway-r16.md (11.9KB)
- 关键 takeaway：#1784/2061/2085 把 Agent gateway SLO dashboard 的最小可用数据集凑齐；#1842 ExtMCP 让 Agent Gateway 区别于通用 L7 API Gateway（per-tool policy / per-tool cost 从应用层提到网关层）；#2088 ID-JAG / #2037 AWS AssumeRole / #28356 MCP OAuth passthrough / #29586 A2A M2M 三类 identity 协议在 6 月这一波全部收口，HIPAA / SOC 2 / EU AI Act 合规通路被打通。
- 内容_sha: `16886390e8be93c03a3c742eb7b83a2e7407ea51`,commit_sha: `8a0e8ded0136e10e972b31a2c69e06022b5bbdf4`
- 推送时间: 2026-06-05 16:49 CST
## 2026-06-05 18:19 CST · Guardrails & 安全 · 4 期轮值

- NeMo Guardrails **v0.22.0**（2026-05-22）发布，IORails 引擎并行执行 content/topic/jailbreak rails，默认开启匿名 usage reporting（opt-out）
- 同期 commit：IORails Telemetry content capture #1972、Guardrails 公开 API 重构 #1933、HuggingFace 轻量分类器 #1853、SSE 流式正则检测 #1932/#1937
- LiteLLM 8 条 guardrail 相关 PR：#29511 sensitive data → on-prem 模型 sticky 路由（**`SensitiveDataRouteException`** 新异常）、#29339 Vigil Guard 原生 provider、#29263 OTel guardrail 跨 span、#29655 工具权限规则热更新、#28418 内容过滤统一 HTTP 400
- Portkey 4 条 guardrail PR：#1669 tool-payload-firewall、#1671 Lakera Guard、#1670 Veto（EU 托管）、#1661 Akto/Zscaler 目录修复
- Envoy AI Gateway #2132 日志脱敏精细化，**不再误伤工具 schema 与 response_format**
- 横切趋势：会话级 sticky 策略路由 / 工具调用面成主战场 / guardrail 真正纳入 OTel 审计 / 多 provider 拼装成网关原语
- 报告：`reports/2026-06-05-1819-aigw-guardrails-roundup.md`（11.5KB，content_sha=44996661c8fe59ab35bcfb5e2d2680698aa33228, commit=b89d15209b3d7cff916c17bcc3c0c04217771288）

## 2026-06-05 18:58 CST · Guardrails & 安全 · 5 期轮值(运行时注入防御 / 越狱评测 / 策略执行)

- guardrails-ai **v0.10.2**(2026-06-04)发布:PyPI trusted publishing(#1493)+ SECURITY_ADVISORY.md 制度化(#1474/#1478/#1490)+ Aikido CI 模板注入 AI 修复(#1467)+ litellm pin 放宽到 >=1.83.0(#1484)
- LiteLLM 本周 OTel guardrail span 闭环:#29470 passthrough emit span + #29552 修补 missing span;#29339 Vigil Guard 升级为原生 provider; #28594 panw_prisma_airs timeout 强转 float(防字符串配置注入)
- Envoy AI Gateway #2132(已合并)日志脱敏改为 field-level,保留 request_id/model/token_count 用于排障
- Higress v2.2.2(2026-05-26)默认开启 wasmplugin 签名校验
- Kong 3.9.2(2026-06-04)纯 CVE 修复,无 AI 新 feature
- agentgateway v1.3.0-alpha.1(2026-05-23)+ 近 5 日 33 PR,重点:#2077 MCP tools.listChanged 多路复用广播、#2075/#2084 栈深度限制(防深递归 DoS)
- 横切:runtime injection 防御从 LLM 内部行为 → 网关/代理/审计三层共担;选型应按层(模型层 prompt 覆盖 / 网关层 tool payload / 审计层 SLSA)评估
- 行动项:2 周内升 guardrails-ai v0.10.2 / 本月抓 OTel guardrail span trace / 季度审计 string-typed guardrail 配置 / 架构评审 MCP 工具 schema 校验位点
- 报告:(11.0KB, content_sha=63225df210e9ad85ec41de9c22606d6f1d128662, commit=754e16fe4c904cf628aa5f3fe0883478d8aa97dd)
## 2026-06-05 19:38 CST · Guardrails & 安全 · 6 期轮值(流式静默丢内容 / 热更新失效 / domain 幻觉)

- LiteLLM **#26585** 修复 `ToolPermissionGuardrail` 流式 hook 在未产生 tool_calls 时整段普通文本被吞（async generator `return` 等价 `StopAsyncIteration`），修复后改走 `MockResponseIterator` 重新 yield
- LiteLLM **#29655** 修复 `ToolPermissionGuardrail` 热更新失效：`update_in_memory_litellm_params` 不重建 `self.rules` 编译产物，导致 `PUT /guardrails/{id}` 改的规则直到 patch / DB 轮询 / 重启才生效（对齐 `PresidioGuardrail` 已有 override 模式）
- LiteLLM **#29097** 修复 Vertex/Gemini `tool_choice` 在 `CachedContent` 复用路径上被静默丢弃，统一 bake 进 body
- NeMo-Guardrails **#1988** 新增 `domain_hallucination` 输出护栏：DNS/HTTP/TLS/WHOIS/GitHub API 五级证据验证，223 样本 F1 60.18%（基线 34.10%），安全集严重误报 5.50%（vs 21.50%），可与既有 hallucination rail 并联做 defense-in-depth
- NeMo-Guardrails **#1985** 状态机 hydration 引入 sharded resource mutex，强制 strict linearizable（配合 v0.22.0 IORails 并行执行）
- guardrails-ai **v0.10.2**(2026-06-04)合并 7 PR：`#1493` PyPI trusted publishing 切到 Sigstore 信任链、`#1474/#1478/#1490` 制度化 `SECURITY_ADVISORY.md`、`#1467` Aikido 修 GitHub workflow 模板注入、`#1484` litellm pin 放宽到 `>=1.83.0`
- LiteLLM **v1.88.0-rc.3** / **v1.87.1**(2026-06-04 ~ 06-05)：v1.87.1 是 stable 通道 5 个 staged fix 的回滚点（`#29631`），`#29645` 撤销过早 bump 到 1.87.2
- 横切判断:流式 / 热更新 / 缓存复用 三类隐性路径已成 guardrail 失效的最密集来源；负路径(`return`/`break`)吞 yield 是 Python async generator 经典地雷；缓存命中时的策略等价性是 P0
- 行动项:本周升 guardrails-ai v0.10.2 / LiteLLM Docker 接 cosign / 跑 tool_permission plain-text 回归 / 2 周内把 `guardrail.rules.applied_count` 与 DB `rules.json` 做一致性 metric / 本月做 cache × tool_choice 矩阵回归 / 季度评估 NeMo `domain_hallucination` 多 rail 投票
- 报告:`reports/2026-06-05-1938-aigw-guardrails-streaming-trust.md`(11.5KB, content_sha=c49414928665bf907e19b979d8a893df3b3df97b, commit=381ddfdbba7b83b0985eed4991e1e974ab872055)

## 2026-06-05 20:49 CST · 架构对比/性能基准 · 4 期轮值(真容量数据 + 代理进程资源 + 启动时延横评)

- 抓取到 5 个目标产品最新 release(2026-06-04 ~ 06-05):**Envoy 1.38.1**(HPACK cookie-bomb 修复、router response body 缩 30-80 字节/req、LB rebuild coalescing 默认改 opt-in)、**Envoy Gateway 1.8.1**(今日发布,7 个 P0 CVE 必修,含 xDS 鉴权 bypass、Lua validator 沙箱读控制面文件、WASM HTTP 缓存缺读锁、BackendTLSPolicy section-name 优先于 wildcard、xDS 在 cert-manager 轮换后用脏证书、`egctl x status` 缺 CRD 不再 panic)、**Kong 3.9.2**(nginx 安全补丁 5 个 CVE、luarocks 3.12.2)、**kgateway 2.3.2 / 2.2.5**(`stripHostPortMode`、RequestRedirect 不再带默认端口、global rate limit 多 descriptor 不再合并为单 action、envoy 升 1.37.3/1.36.7)、**Higress 2.2.2**(`modelToHeader` 默认 `x-higress-llm-model-final`、Nginx rewrite 兼容 WASM 避 CVE-2026-42945、Bedrock Mantle Anthropic Messages API 直连)
- 容量横评(2 vCPU / 4GB / keep-alive / 短请求):Envoy / Higress(Envoy 内核)60-120k RPS / P99 1.5-4ms / 80-180MB;Kong 20-40k / 5-15ms / 150-250MB;workerd 单 isolate 5-15k / 2-5ms / 30-60MB;Envoy Gateway / kgateway 6-10w(数据面) / 冷启 3-8s
- LLM 场景代理 RTT 增量(直连 vs 网关):普通 Envoy +1-3ms、AI Gateway ext_proc +5-15ms、长上下文 re-parse +10-30ms;行业底线 1-3ms,多花 5-15ms 换统一限流/审计/重试/协议转换,业务侧价值远大于此
- 三个常见误用澄清:"Kong 比 Envoy 慢 2-3 倍"实际 < 30%(关掉所有插件时)、workerd 内存优势按 isolate 不按进程、AI Gateway 开销应与"它替代掉的业务侧重复实现"对账
- 横切判断:本批 release 全为安全硬化 + 小坑修复,无结构性性能变更;真拐点是 Envoy AI Gateway 0.7/0.8 切 in-proc ext_proc(理论 RPS 翻 2-3 倍);**别被 AI Gateway 多花 5ms 劝退**
- 行动项:立即升 Envoy Gateway 1.8.1 / kgateway 2.3.2 / Kong 3.9.2 / Envoy 1.38.1;本月用 `llm-d/llm-d` v0.7.0 bench 套件重跑生产 5% 影子流量;K8s HPA 优先 Higress / Envoy Gateway(冷启 < 1s)、FaaS / 边缘优先 workerd(< 50ms);配置审计 `envoy.reloadable_features.coalesce_lb_rebuilds_on_batch_update` 在大批量 EDS 场景需重新打开
- 报告:`reports/2026-06-05-2049-aigw-arch-benchmark-r4.md`(12.4KB, content_sha=b53fffe90f9d546eb36a847498457b0b118c3f91, commit=786e73a68342c1f2d8819e1c35ed5406a0197720)

## 2026-06-05-2134 CST · 单产品发版追踪 · Higress v2.2.2 发版深挖

- 主题:单产品发版追踪(轮换到 Higress),数据源:GitHub Releases API `alibaba/higress` v2.2.2 (2026-05-26 释出,37 项变更) + v2.2.1 / v2.2.0 / v2.1.11 同窗对比 + higress.cn 官网/博客
- 关键看点:
  - **Bedrock Anthropic 链路深水区**:`#3820` 砍掉 OpenAI→Converse 两段桥接,直连 Bedrock Mantle Anthropic Messages 原生端点;`#3788` 修 `reasoningContent` 错误合并为 plain text(配 `redactedBlockIndexes` 状态机);`#3786` 修并行 tool call 时的 `contentBlockIndex` 错位;`#3799` 修 Claude `input:{}` 空对象被吞;`#3756` `/v1/messages`→OpenAI `chat/completions` 转换保留 `thinking`/`redacted_thinking`,新增 `preserve_thinking` / `promote_thinking_on_empty` provider 级开关
  - **AIGC 视频能力补齐**:`#3742` KlingAI provider 正式入仓(覆盖 OpenAI-compatible 与 native Kling 协议、官方 AK/SK JWT 和第三方 gateway Bearer 两种鉴权、文生视频 + 图生视频)
  - **AI 代理一致性**:`#3827` `ai-proxy` 新增 `modelToHeader`(默认 `x-higress-llm-model-final`),在 `model_mapper` 改写后同步写入 header 并 `DisableReroute`,直接封死「`model-mapper`→限流插件读不到真正命中模型」的隐性 bug
  - **计费透明度**:`#3766` OpenAI→Claude 流式 transformer 透出 `CacheReadInputTokens` 字段,Anthropic Prompt Caching 在网关侧第一次有可观测性
  - **Nginx 迁移减阻**:`#3823` Nginx rewrite 兼容 WASM 插件,在 WASM 沙箱内安全执行 Nginx `rewrite`+`set` 语义,显式规避 CVE-2026-42945 heap overflow——Nginx Ingress 退役潮背景下关键减阻
  - **Vertex AI Express Mode 闭环**:`#3695` + `#3777` 让 Express Mode 免填项目/区域路径,直接走 API Key URL query 鉴权,401 问题终结
  - **国内模型路径迁移**:`#3722` 把 Qwen 兼容 endpoint 从已弃用 `/api/v2/apps/protocols/compatible-mode/v1/responses` 切到官方 `/compatible-mode/v1/responses`;`#3724` 新增 Qwen rerank 与 conversations API 路径
  - **AI 安全护栏**:`#3738` `ai-security-guard` 新增 `responseContentFallbackJsonPaths` + `responseStreamContentFallbackJsonPaths` 让 Claude 响应也能走内容安全检查;`#3739` `ai-prompt-decorator` 加 `replace` 配置(字面量 / RE2 正则 / 按 role / 按顺序);`#3731` 取消 `Suggestion=block` 强制 fallback,改按风险维度阈值评估
  - **稳定性与可观测性**:18 项 bug fix 覆盖 WASM 插件 nil 检查与 regex 预编译(`#3757`)、HTTPS upstream 自签证书(`#3770`)、Azure OpenAI v1 新 URL 识别(`#3765`)、controller 日志统一 JSON(`#3779`)、EnvoyFilter 不识别协议 warn log 带协议名(`#3801`)、`getRouteName` 在 `clearRouteCache` 后仍返回旧路由名(`#3576`)、`TARGET_ARCH` 白名单(`#3682`)
  - **CNCF Sandbox 申报治理文件**:`#3830` README 中/英/日 3 版本加 OpenSSF Best Practices 徽章、`#3764` 更新 `SECURITY.md` 漏洞披露 SLA + 新增 `GOVERNANCE.md`、`#3754` 新增顶层 `MAINTAINERS.md`——Higress 2026 申报 CNCF Sandbox 的可见信号
- 节奏观察:v2.2.1 → v2.2.2 间隔 47 天,本期 37 项(显著低于 v2.2.1 的 65 项),更偏「质量收口 + 治理合规」而非爆发式新功能
- 报告:`reports/2026-06-05-2134-aigw-release-higress-v222.md` (12.4KB, content_sha=38bf3050e5e1256e7dd26a79b456aa6c31f0daf2, commit=078d8d26bb669570dba18f5ac32a3c80b0db7759)

