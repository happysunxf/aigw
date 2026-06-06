# AI 网关深挖 · Agent Gateway 专题（round 22）

> **轮值时间**：2026-06-06 16:50 CST（UTC 08:50）
> **专题**：Agent Gateway（multi-agent 编排 / trace 调试 / 成本归因）
> **窗口期**：过去 72 小时（2026-06-03 ~ 2026-06-06）
> **主角**：agentgateway（v1.3.0-alpha.1 后 30+ PR 密集合入）+ AG2 v0.13.3 跨进程 Network + Google ADK v2.2.0

## 1. agentgateway 加入 AAIF（Linux Foundation）

2026-06-04，agentgateway 以"AI agentic 基础设施开放网关"身份加入 **Agentic AI Foundation（AAIF）**，成为该基金会的**第 4 个 hosted 项目**。核心论点（[Lin Sun 的 AAIF 官博原文](https://aaif.io/blog/agentgateway-joins-aaif-as-an-open-gateway-for-agentic-ai-infrastructure/)）：

- "AI 系统越来越像分布式系统"（agents → tools → models → providers → MCP servers），传统 API 网关缺少 agentic 系统所要求的治理、可观测、路由、安全控制
- 定位 = "the first open-source AI-native gateway for the new wave of agentic systems"
- 与 A2A / MCP 规范对齐

**8 大旗舰用户引用**（agentgateway.dev 首页）：Dell CTO "bridges A2A + MCP"；CoreWeave SVP "open and interoperable"；Akamai SVP "purpose-built, not retrofitted legacy"；Microsoft CNCF "complements A2A + MCP specifications"；T-Mobile Director "AI-native connectivity that understands MCP and A2A"；UBS Exec Director "OTel integration = evaluable unit"；NYU/TUF 创始人 "MCP security 是当下最大的开放安全问题之一，first step"；Kyverno/Nirmata "vendor-neutral infrastructure"。

## 2. agentgateway v1.3.0-alpha.1 之后 PR 密度

2026-05-23 cut v1.3.0-alpha.1（52 PR 一次性合入）。截至 2026-06-06 08:44 UTC，**main 分支 14 天内 30+ 新 PR**，节奏 = 每日 2-3 PR。按 monthly cadence（5-11 v1.2.0 → 5-15 v1.2.1 → 5-23 v1.3.0-alpha.1），**v1.3.0 stable 切预计 2026-06 中下旬**。

### 重点 PR（按业务分类）

**A. 跨进程 / multi-agent 编排**

- **#1842（open）feat(mcp): ExtMCP for MCP-aware ext_authz/ext_proc** — 专为 MCP 设计的远端 gRPC hook 端点，针对 `tools/call`/`tools/list`/`prompts/get` 等具体 JSON-RPC 方法做 gate/mutate，避免 ext_authz server 重新解析 MCP 帧。要点：(1) gateway-to-client 工具名做 mux（"tool_name_backend_name"），但 hook 用 upstream tool name，backend name 作为 metadata 传；(2) callout per-method opt-in；(3) `list` fanout 时每个 backend 一次 ExtMCP hook；(4) 跑在 post-auth 之后，**mutate 之后不再 re-run mcpAuthentication**（避免 mutate 引入 policy gap）。
- **#2088（open）Add support for OAuth Identity Assertion (ID-JAG / Cross App Access)** — 实现 `draft-ietf-oauth-identity-assertion-authz-grant` client 侧，新 policy `backendAuth.identityAssertion`。agent 替用户调用下游 API 时**不需要二次交互登录**：先 RFC 8693 token exchange 拿 ID-JAG assertion，再 RFC 7523 JWT-bearer grant 拿资源服务端 Bearer token。缓存键 = `(subject, audience, scope, resource)`。**scope 在两段都透传**（资源服务端只授权 jwt-bearer 显式请求的 scope，不继承 ID-JAG 的 scope）。Client auth：`clientSecretBasic` / `clientSecretPost` / `privateKeyJwt`。E2E 验证用 Okta XAA sandbox。Out of scope：DPoP、`.well-known` discovery、XDS/controller transport、SAML/refresh-token。Closes #2029。

**B. 浏览器 OIDC / 流量 policy**

- **#1450（open）feat(oidc): controller-backed OIDC discovery with xDS-delivered policy** — Closes #925。Browser-based OIDC login（Auth Code + PKCE，gateway 是 Relying Party，cookie session 加密），作为 `AgentgatewayPolicy` 的 TrafficPolicy。和 `jwtAuthentication`（机器对机器 bearer 校验）**互斥**。架构亮点：抽 `controller/pkg/agentgateway/remotecache/` 通用 generics（`FetchedResults[R]` / `Fetcher[S, R]` / `Store[S, R]` / `Codec[T]` / `Entries[T]` / `ConfigMapController[T]`），JWKS (#1175) 和 OIDC 是同一套 generic 的两个消费者，**没有并行实现**。**CRD-level CEL 在 apply 时强制 method ↔ secret 配对**。`tokenEndpointAuthMethod` 显式 override → 强制按配置；不 override → 用 IdP advertise 的；空 advertise 列表 → OIDC Discovery §4.2 / RFC 8414 §2 默认 `client_secret_basic`；confidential client IdP 啥都不 advertise → **dataplane load 时 fail closed**。Refresh interval 固定 1h。

**C. 可观测 / 成本归因（trace 调试 / 成本归因专题核心）**

- **#2061 feat(metrics): Configuration synchronisation metric** — 新增 `agentgateway_config_synchronized` gauge，**0 = reload 失败，1 = 同步成功**（AIGW 落"健康检查 + SLO"必须）。
- **#1993 fix: populate cache_creation_input_tokens in non-streaming responses** — 修 `llm/types/completions.rs`：之前 outer `Usage` struct 缺 `cache_creation_input_tokens` → Bedrock response body 的 `cache_write_input_tokens` 直接被 deserializer 丢掉，**access log 永远没有 cache_creation 指标**。修后实测 `us.anthropic.claude-sonnet-4-6` with `promptCaching` enabled：cache write 时 `gen_ai.usage.cache_creation.input_tokens=3153`、cache read 时 `cache_creation=0/cache_read=3153`。**这是 prompt caching 成本归因的最后一块拼图**。
- **#2086** 健康检查和驱逐解耦 / **#1982** unevict timer 不再匹配当前 endpoint 状态时被忽略 / **#1784**（open）proxy timing / **#2017**（open）buffer config / **#1849**（v1.3.0-alpha.1 已合）request/connection id logging。

**D. MCP 协议深化（与本期 MCP r24 联动）**

- **#2100 mcp: support resource subscribe**（多路复用模式下 watch GET stream + name transform）/ **#2103 Add per mcp backend oauth passthrough**（per-MCP-server OAuth 自主 vs gateway）/ **#2077 mcp: advertise tools.listChanged in multiplexing mode**（upstream `listChanged` 转发到 client）/ **#2106 anthropic: support system messages**（替代 #2015/#2089）/ **#2097 include mcp-session-id in cors request header**。

**E. Bedrock / 协议兼容**

- **#2037 AWS AssumeRole** / **#2018 forward reasoning_signature on Bedrock Converse**（Anthropic Claude 4.x thinking 链必备）/ **#2093 Fix Bedrock Opus 4.8 thinking conversion** / **#2104 detect-passthrough for bedrock**（让 Claude Code + Bedrock 全链路 access log 可见）/ **#2105 simple llm: TLS** / **#2107 bedrock: allowlist anthropic beta headers**。

**F. 平台 / K8s / Policy 治理**

- **#2056**（open）policy inheritence strategy（`Default` Route > Gateway vs `Override`，借自 GEP-713）/ **#2081** BackendReferenceGrantMode / **#1846** CONNECT terminate / **#2001** CEL grpc status / **#2098** agctl proxy/controller log（远程读/设置 log level）。

## 3. AG2 v0.13.3 跨进程 Network

2026-06-05，AG2 发布 v0.13.3。v0.13.x → v1.0 路线图里第一个重要的 **Beta 框架**里程碑。

**5 大新特性：**

1. **跨进程 Network**（#2914 + #2915）— v0.13.0 Network 是 in-process；v0.13.3 跨进程 + 跨机器
   - 跨进程 Data Plane：`WsLink` WebSocket 传 hub ↔ client envelope，含 auth + delivery 语义
   - 跨进程 Control Plane：frame-based RPC（registration / channel lifecycle / governance）
   - 配合 #2941 hub envelope id 严格单调
2. **`background_agent_tool`**（#2900）— 父 agent 不阻塞 → 后台跑子 agent
3. **Sandbox 协议 + LocalSandbox**（#2879）— 干净抽象 sandboxed 执行
4. **Eval 增强** — Agent-as-a-judge + Pairwise 可不传 reference answer（#2936）；**Export `run_agent` spans 到外部 backend**（#2919）—— 对 AIGW 极其关键：AG2 agent 的运行 span 可外推 OTel-compatible backend
5. **A2A 协议升级** — 流式文本 chunk 改为先创建 artifact 再追加（a2a-sdk 1.1.0 兼容，#2924）；连接时校验 A2A protocol version（#2935）

**3 个生产 bug 修复：** #2928 reasoning tokens 误映射 `cache_creation` → 改 `thinking_tokens`；#2929 `Stream.get` 防"第二个匹配 event abort turn"；#2918 tool result 缺失不 crash。

**节奏：** AG2 从 0.13.0（5-13）到 0.13.3（6-05）= **23 天 3 minor**，月级 cadence。v1.0 之前还要做 Agent Memory、Reflection、Tool Use v2，**预计 2026 Q3-Q4 切 stable**。

## 4. Google ADK Python v2.2.0 + 横向参照

**Google ADK Python v2.2.0**（2026-06-04）— 同期 commits：`928017d` add automatic adk web updates / `10e5f07` refactor PR analysis from triage / `c1e852f` fix LiteLlm graph model serialization（**v2.2.0 重点修复**）。

**横向项目状态：**

| 项目 | 最新动态 | 节奏判断 |
|------|----------|----------|
| LangGraph | 06-05 #8002 migrate type checking to `ty` | 周级 deps 升级，**主线在 `libs/cli` 和 `libs/checkpoint`** |
| AutoGen | 04-06 "Update maintenance mode banner in readme" (#7521) | ⚠️ **进入维护期** |
| AgentStack | 04-03 #2507 Python 3.14 Quickstart；04-02 #2506 替换 access_token | 月级慢节奏 |
| AG2 | 06-05 v0.13.3 跨进程 Network + Sandbox | 月级 minor，**主线 v1.0 准备期** |
| Google ADK Python | 06-04 v2.2.0 + web 自动发版 | 月级 + patch |

## 5. 三大趋势判断

**趋势 1：MCP-aware gateway 取代"通用 API 网关 + MCP 代理"二元结构。** #1842 ExtMCP（专为 MCP 设计的 ext_authz）= MCP 帧在网关层做 gate；#2103 per-MCP-backend OAuth passthrough；#2100 resources/subscribe + #2077 listChanged = **MCP 协议完整对接**。推断：未来 6 个月「MCP-aware gateway」成新标准；通用 API 网关（Kong、Envoy）会追赶式补 MCP plugin。

**趋势 2：跨进程 Network 取代 in-process multi-agent。** AG2 v0.13.3 跨进程 Network = **agent 不再和 hub 同进程 → hub 可独立 scale + 多 agent 跨机器协作**；agentgateway #1842 ExtMCP 也是"远端 gRPC server 网关化" — **「control plane 在云端、data plane 在本地」成 agent 平台标准**。推断：未来 12 个月「agent runtime + agent gateway」会拆成两个独立产品。

**趋势 3：可观测 + 成本归因进入 "agent-level"。** #2061 `agentgateway_config_synchronized` gauge（配置层健康指标）/ #1993 cache_creation/cache_read access log（cache 成本归因）/ #1784 proxy timing（请求级时延）/ AG2 #2919 export `run_agent` spans（agent 运行 trace 外推）。推断：未来 6 个月「agent observability」会拆出独立产品线（类似 Langfuse、Helicone），agentgateway 会提供 trace SDK 对接。

## 6. AIGW 落点：本期 6 条硬要求

> 在前 21 轮累积的硬要求基础上，本期新增 6 条：

- **#81 ExtMCP for ext_authz**（#1842）— AIGW 的 MCP 路由层必须支持"per-method opt-in 的远端 gRPC hook"
- **#82 OAuth Identity Assertion (ID-JAG / XAA)**（#2088）— AIGW 替 agent 调用下游 API 时按 ID-JAG spec 拿资源服务端 Bearer；scope 在 RFC 8693 + RFC 7523 两段都透传；缓存键 `(subject, audience, scope, resource)`
- **#83 controller-backed OIDC discovery with xDS-delivered policy**（#1450）— AIGW browser-based OIDC login 走 controller，dataplane 不打 `.well-known` / `jwks_uri`；OIDC 和 JWT policy 互斥；CEL 在 CRD apply 时强制配对
- **#84 `agentgateway_config_synchronized` metric**（#2061）— AIGW 暴露 config load/reload 是否成功的 gauge（0/1）
- **#85 cache_creation_input_tokens in OTel access log**（#1993）— AIGW 用 Bedrock 时必须把 `cache_write_input_tokens` / `cache_read_input_tokens` 都打 access log（不是只打 read）
- **#86 per-MCP-backend OAuth passthrough flag**（#2103）— AIGW 支持 per-MCP-server 单独决定 OAuth 自己管还是 gateway 管

## 引用与数据来源

- agentgateway repo / v1.3.0-alpha.1 / v1.2.1 / commits since 06-04：<https://github.com/agentgateway/agentgateway> ｜ <https://github.com/agentgateway/agentgateway/releases/tag/v1.3.0-alpha.1> ｜ <https://github.com/agentgateway/agentgateway/commits/main?since=2026-06-04T00:00:00Z>
- agentgateway 30+ PR 详情：#1842 / #2088 / #1450 / #2061 / #1993 / #2056 / #2081 / #1846 / #2100 / #2103 / #2077 / #2106 / #2098 / #1784 / #1982 / #2086 / #2037 / #2018 / #2093 / #2104 / #2105 / #2107 / #2017 / #2001 / #1849 / Issue #925 / Issue #175 — 全部链接为 <https://github.com/agentgateway/agentgateway/pull/NNNN>（替换 NNNN 即可）
- GEP-713：<https://gateway-api.sigs.k8s.io/geps/gep-713/>
- AG2 v0.13.3 release / Release Roadmap / Distributed Deployment：<https://github.com/ag2ai/ag2/releases/tag/v0.13.3> ｜ <https://docs.ag2.ai/latest/docs/user-guide/release-roadmap/> ｜ <https://docs.ag2.ai/latest/docs/beta/network/distributed/>
- AG2 PRs：#2914 / #2915 / #2900 / #2879 / #2936 / #2919 / #2924 / #2935 / #2928 / #2929 / #2918 / #2941 — 全部链接为 <https://github.com/ag2ai/ag2/pull/NNNN>
- Google ADK Python：<https://github.com/google/adk-python/releases/tag/v2.2.0>
- 横向：LangGraph <https://github.com/langchain-ai/langgraph> / AutoGen <https://github.com/microsoft/autogen> / AgentStack <https://github.com/i-am-bee/agentstack>
- 官方博客：agentgateway blog <https://agentgateway.dev/blog/> / AAIF 官博 <https://aaif.io/blog/agentgateway-joins-aaif-as-an-open-gateway-for-agentic-ai-infrastructure/> / Designing agentgateway <https://agentgateway.dev/blog/2026-06-04-designing-agentgateway-unified-gateway/> / v1.2.0 release <https://agentgateway.dev/blog/2026-05-11-agentgateway-v1.2.0/> / AAIF <https://aaif.io/> / docs <https://agentgateway.dev/docs/>
- 规范 / RFC：ID-JAG draft <https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/> / RFC 8693 <https://datatracker.ietf.org/doc/html/rfc8693> / RFC 7523 <https://datatracker.ietf.org/doc/html/rfc7523> / RFC 8414 <https://datatracker.ietf.org/doc/html/rfc8414> / OIDC Discovery §4.2 <https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderMetadata> / Okta XAA sandbox <https://xaa.dev>
