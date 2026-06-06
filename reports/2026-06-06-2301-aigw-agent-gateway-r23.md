# AI 网关深挖 · Agent Gateway 专题（round 23）

> **轮值时间**：2026-06-06 23:01 CST · **窗口期**：过去 24h（06-05 ~ 06-06 23:00 CST）
> **主角**：agentgateway（v1.3.0-alpha.1 后 +30 PR 持续密集合入）
> **AIGW 落点**：本期新增 5 条硬要求 → 累加 **AG-37 ~ AG-41**

## TL;DR

agentgateway 在 06-05 ~ 06-06 **65 分钟内集中合入 7 条 PR**（#2098/2100/2101/2104/2105/2106/2087/2086），把 multi-agent 编排的"治理边界"从协议层推到 **OAuth/OIDC 授权层**（ID-JAG / Browser OIDC）+ **操作可观测层**（proxy timing / agctl pprof）+ **政策归并层**（policy inheritence + BackendReferenceGrantMode）。5 大新信号：(1) **#2088 ID-JAG** —— agent 替用户调下游 API 不二次登录；(2) **#1450 Browser OIDC**（8258/103 文件）—— Auth Code + PKCE，**与 `jwtAuthentication` 互斥**；(3) **#1842 ExtMCP**（6799/58）—— MCP-aware ext_authz，per-JSON-RPC-method opt-in，**mutate 后不重跑 mcpAuth**；(4) **#1784 proxy timing** —— `request_processing_seconds` + `backend_time{kind}` + TTFT 直方图；(5) **Issue #2111** —— server-side tool calling interception & MCP injection，**"网关成为 Claude Code 的 MCP 注册中心"**。

## 1. 24h 合入的 7 条 PR（65 分钟短跑）

| PR | 主题 | 作者 | 关键变化 |
|---|---|---|---|
| [#2106](https://github.com/agentgateway/agentgateway/pull/2106) | anthropic: support system messages | howardjohn | 替代 #2015/#2089，**preserves request 当 possible** |
| [#2105](https://github.com/agentgateway/agentgateway/pull/2105) | simple llm: TLS | howardjohn | `simpleLLM.tls: {}` |
| [#2104](https://github.com/agentgateway/agentgateway/pull/2104) | llm: detect-passthrough for bedrock | howardjohn | `passthrough: detect` → "Claude Code + Bedrock 全链路 access log 可见" |
| [#2101](https://github.com/agentgateway/agentgateway/pull/2101) | websocket: case-insensitive Upgrade | – | 修 #2095：上游 `Upgrade: WebSocket` 大小写致"成功但立刻死" |
| [#2100](https://github.com/agentgateway/agentgateway/pull/2100) | mcp: resource subscribe | howardjohn | `resources/subscribe` + watch GET stream + name transform（mux） |
| [#2099](https://github.com/agentgateway/agentgateway/pull/2099) | local llm: CORS | – | local LLM 默认允许跨源 |
| [#2098](https://github.com/agentgateway/agentgateway/pull/2098) | agctl: restructure CLI + log | jbohanon | `agctl proxy log` / `agctl controller log` 远程读/设置 log level |

**配套**：[#2087](https://github.com/agentgateway/agentgateway/issues/2087) 保留 agentcore default servicename；[#2086](https://github.com/agentgateway/agentgateway/pull/2086) eviction 与 health 监测解耦；[#2091](https://github.com/agentgateway/agentgateway/issues/2091) macOS Intel darwin-amd64 asset 缺失；[#2090](https://github.com/agentgateway/agentgateway/issues/2090) Bedrock Opus 4.8 拒 `thinking.type=enabled`（#2093 已修）。

## 2. 五大 Multi-Agent 编排硬信号

### 2.1 [PR #2088] OAuth Identity Assertion（ID-JAG / Cross App Access）

**作者** iamspathan（+6920/2/8，06-05 10:54 开）。实现 `draft-ietf-oauth-identity-assertion-authz-grant` 客户端，新 policy `backendAuth.identityAssertion`，**Closes #2029**。

**两段 token exchange**：
1. **RFC 8693** token exchange at user's IdP → **ID-JAG assertion**（subject + audience + scope）
2. **RFC 7523** JWT-bearer grant at 资源 AS → **Bearer access token** → 附在 upstream request

**关键设计**：**缓存键** = `(subject, audience, scope, resource)`，四元组一致才命中；**scope 在两段都透传**（资源 AS 不继承 ID-JAG 的 scope —— RFC 7523 §2.2 硬性）；**Client auth 矩阵**：`clientSecretBasic` / `clientSecretPost` / `privateKeyJwt`（不支持 `none`）；接入 `BackendAuth` enum（gcp/aws/azure 同级），**复用 config/policy/apply 路径**；E2E 验证 Okta **XAA sandbox**（https://xaa.dev）。**Out of scope**：DPoP、`.well-known` discovery、XDS transport、SAML/refresh-token。

**AIGW 落点 AG-37**：agent → downstream API 代用户身份切换时，**必走 ID-JAG 两段**；agent **不直接持有**长期 refresh-token。

### 2.2 [PR #1450] Controller-backed OIDC（8258/103 文件）

**作者** apexlnc（开 04-03，06-06 04:23 仍 open）。Closes #925。**5-6 月最大单一 PR**。**Browser-based OIDC**（Auth Code + PKCE，gateway 是 Relying Party，**encrypted-cookie session**），作为 `AgentgatewayPolicy` 的 TrafficPolicy。**与 `jwtAuthentication` 互斥** —— OIDC 走人，JWT 走机器。

**通用化远程工件生命周期**（架构最关键）：抽 `controller/pkg/agentgateway/remotecache/` generics（`FetchedResults[R]` / `Fetcher[S, R]` / `Store[S, R]` / `Codec[T]` / `Entries[T]` / `ConfigMapController[T]`），**JWKS (#1175) 和 OIDC 是同一套 generic 的两个消费者**，**没有并行实现**。

**Token-endpoint auth method 决策树**：(1) 显式 override → **CRD-CEL apply 时强制 method ↔ secret 配对**；(2) 不 override → ship IdP advertise 的；(3) 空 advertise → OIDC Discovery §4.2 / RFC 8414 §2 默认 `client_secret_basic`；(4) Confidential client IdP 啥都不 advertise → **dataplane load 时 fail closed**；(5) Public client（PKCE only）→ 省略 `client_secret`。

**Dataplane 行为**：永不调 `.well-known` / `jwks_uri`（controller over xDS ship resolved provider）；空 `client_secret` 仅对 `None` 合法；field shape proto-decode 时强制。Refresh interval **固定 1h**。

**AIGW 落点 AG-38**：浏览器流走 OIDC + 加密 cookie；机器流走 JWT bearer；**两条路径不可混用**。

### 2.3 [PR #1842] ExtMCP（MCP-aware ext_authz）

**作者** stevenctl（+6799/689/58，05-15 开，06-06 仍 open）。fixes #175。仿 Envoy `ext_authz`，专为 MCP 语义 —— 远端 gRPC server 对 `tools/call` / `tools/list` / `prompts/get` 等 JSON-RPC 方法做 gate/mutate，**不重新实现 MCP 帧**。

**4 条关键设计**：(1) **Mux 模式 hook name**：tool name mux 为 `"tool_name_backend_name"`，但 hook 用 **upstream tool name**（去 mux 前缀），**backend name 走 metadata** —— 避免 hook 重复 mux 解析；(2) **Per-method opt-in**：callout 按 method 列表 opt-in；(3) **`list` fanout per-backend hook**：fanout 时**每个 backend 一次** ExtMCP hook；(4) **Post-auth + 不重跑**：extmcp 跑在 mcpAuth 之后；**mutate 后不重跑 mcpAuth** —— 避免 mutate 引入 policy gap（ext_authz 经典 pitfall）。

**AIGW 落点 AG-39**：MCP tool call 转 SIEM/SOAR/审计/合规时走 **ExtMCP**（gRPC over mTLS），**比 HTTP webhook 性能好、比 mirror policy 灵活**。

### 2.4 [PR #1784] Proxy Timing Measurements（+33 文件）

**作者** howardjohn（05-08 开，06-05 22:28 仍 open）。**6/5~6/6 trace 调试 / 成本归因专题的旗舰 PR**。

**新增 metric 矩阵**：
```
agentgateway_request_processing_seconds       # HTTP 接收 → 主 outbound
agentgateway_request_time_seconds             # 接收 → 响应
agentgateway_response_time_seconds            # upstream 响应 → client
agentgateway_backend_time_seconds{kind=...}   # 主 outbound 时长
agentgateway_backend_time_to_first_token      # kind=llm 时附加
```

**关键工程决策**：**label 集严格控制** —— `{backend, bind, gateway, listener, route, route_rule}` + `kind`（Http/Llm/Mcp/ExtAuthz/ExtProc/Guardrail/RateLimit/Oidc 共 8 类），避免 cardinality 爆炸（CEL `MinimalHTTPLabels`）；**CEL 变量同步** —— `request.duration` / `response.duration` / `backend.duration` / `backend.kind` 在 route policy CEL 直接消费；**TTFT 直方图** —— 对接 [#2094](https://github.com/agentgateway/agentgateway/issues/2094) issue，与 OTel `gen_ai.server.time_to_first_token` 字段对齐。

**AIGW 落点 AG-40**：多 agent 共用 gateway 时按 `kind × backend × listener` **三维切分**；**TTFT 走 `gen_ai.server.time_to_first_token`**。

### 2.5 [Issue #2111] Server-side Tool Calling Interception & MCP Injection

**作者** 06-06 12:28 UTC 开 issue，**未指定 assignee**。**全行业首批**"agent 网关拦截 server-side tool call 透明替换为 MCP 调用"的设计。

**用例**（issue body 直引）："enable server-side web search tool calling in Claude Code with custom LLM engines (vLLM/SGLang/OpenRouter) and custom search providers (SearXNG)"

**6 步流程**：(1) Claude Code 发 coding 请求；(2) Gateway 拦截并注入 MCP tools 到 tool-calling 数组；(3) Model 标准 tool calling 调 MCP tool；(4) Gateway 执行 MCP tool 返回结果；(5) Model 把 result 写进 response；(6) **对 Claude Code 完全透明** —— 只见 Anthropic message format。

**3 个外部参照**：[LiteLLM Web Search Interception](https://docs.litellm.ai/docs/integrations/websearch_interception) · [LiteLLM Claude Code Websearch](https://docs.litellm.ai/docs/tutorials/claude_code_websearch) · [Bifrost × Claude Code](https://www.getmaxim.ai/bifrost/blog/integrating-claude-code-with-bifrost-gateway)

**AIGW 落点 AG-41**：Claude Code + 自部署推理引擎时**由 gateway 拦截 + 注入**；MCP 工具"在 gateway 上注册一次，对所有后端透明"（vLLM/SGLang/OpenRouter 不需分别配）。

## 3. 政策归并 / Reference Grant / Buffer（11 条附属 PR）

| PR | 主题 | 关键变化 | 类别 |
|---|---|---|---|
| [#2056](https://github.com/agentgateway/agentgateway/pull/2056) | policy: inheritence strategy | `Default`/`Override`（借自 GEP-713）+1353/704/20 | policy 归并 |
| [#2081](https://github.com/agentgateway/agentgateway/pull/2081) | BackendReferenceGrantMode | backend reference grant 严格度 +609/35/18 | 引用治理 |
| [#2017](https://github.com/agentgateway/agentgateway/pull/2017) | feat(buffer): request body buffering | 显式 buffering config +1992/793/17 | 流量控制 |
| [#2108](https://github.com/agentgateway/agentgateway/pull/2108) | service routes port filter | – | 流量控制 |
| [#2109](https://github.com/agentgateway/agentgateway/pull/2109) | fix(ui): XDS route path prefixes | 修 #1370：admin UI 修 `pathPrefix`/`prefix` 双字段 | 可观测 |
| [#2102](https://github.com/agentgateway/agentgateway/pull/2102) | cel/route meta | DRAFT，**route metadata 注入 CEL context** | 编程接口 |
| [#2107](https://github.com/agentgateway/agentgateway/pull/2107) | bedrock: allowlist anthropic beta | – | 模型兼容 |
| [#2103](https://github.com/agentgateway/agentgateway/pull/2103) | per mcp backend oauth passthrough | DRAFT，per-MCP-server OAuth 自主 vs gateway | MCP 治理 |
| [#2093](https://github.com/agentgateway/agentgateway/pull/2093) | Fix Bedrock Opus 4.8 thinking | OpenAI `reasoning_effort` → `thinking.type=adaptive` + `output_config.effort` | 模型兼容 |
| [#2000](https://github.com/agentgateway/agentgateway/pull/2000) | capture streaming completion in bedrock | **streaming completion token 抓得到** —— cost attribution 修复 +93/1/3 | 成本归因 |
| [#2110](https://github.com/agentgateway/agentgateway/pull/2110) | agctl pprof profile | `agctl proxy profile cpu [resource]`，fixes #2096 +466/0/5 | 可观测 |

## 4. AIGW 落点（新增 5 条硬要求）

| 编号 | 硬要求 | 来源 |
|---|---|---|
| **AG-37** | agent → downstream API 代用户身份切换必走 **ID-JAG 两段 token exchange**；agent 不持长期 refresh-token；缓存键 = `(subject, audience, scope, resource)` | PR #2088 |
| **AG-38** | Browser 走 **OIDC + 加密 cookie**（PKCE S256）；机器走 **JWT bearer**；**不可混用**；controller CEL 强制 method↔secret 配对；dataplane 不调 `.well-known` | PR #1450 |
| **AG-39** | MCP tool call 转 SIEM/SOAR/审计/合规走 **ExtMCP**（gRPC over mTLS），per-JSON-RPC-method opt-in，**mutate 后不重跑 mcpAuth** | PR #1842 |
| **AG-40** | 多 agent 共用 gateway 按 `kind × backend × listener` 三维切分延迟；**TTFT 走 `gen_ai.server.time_to_first_token`** | PR #1784 + issue #2094 |
| **AG-41** | Claude Code + 自部署推理引擎时，**gateway 拦截 server-side tool call 注入 MCP tool**；MCP 工具"在 gateway 上注册一次，对所有后端透明" | Issue #2111 |

**AIGW 硬要求全集 41 条**：AG-1 ~ AG-41。

## 引用与数据来源

- agentgateway [releases](https://github.com/agentgateway/agentgateway/releases) · [commits since 6/5](https://github.com/agentgateway/agentgateway/commits/main) · [PRs](https://github.com/agentgateway/agentgateway/pulls) · [issues](https://github.com/agentgateway/agentgateway/issues)
- 关键 PR：[#1450](https://github.com/agentgateway/agentgateway/pull/1450) · [#1784](https://github.com/agentgateway/agentgateway/pull/1784) · [#1842](https://github.com/agentgateway/agentgateway/pull/1842) · [#2000](https://github.com/agentgateway/agentgateway/pull/2000) · [#2017](https://github.com/agentgateway/agentgateway/pull/2017) · [#2056](https://github.com/agentgateway/agentgateway/pull/2056) · [#2081](https://github.com/agentgateway/agentgateway/pull/2081) · [#2088](https://github.com/agentgateway/agentgateway/pull/2088) · [#2093](https://github.com/agentgateway/agentgateway/pull/2093) · [#2098](https://github.com/agentgateway/agentgateway/pull/2098) · [#2100](https://github.com/agentgateway/agentgateway/pull/2100) · [#2104](https://github.com/agentgateway/agentgateway/pull/2104) · [#2106](https://github.com/agentgateway/agentgateway/pull/2106) · [#2110](https://github.com/agentgateway/agentgateway/pull/2110)
- 关键 issue：[#2065](https://github.com/agentgateway/agentgateway/issues/2065) · [#2090](https://github.com/agentgateway/agentgateway/issues/2090) · [#2094](https://github.com/agentgateway/agentgateway/issues/2094) · [#2111](https://github.com/agentgateway/agentgateway/issues/2111)
- AAIF 加入：[Lin Sun 官博原文](https://aaif.io/blog/agentgateway-joins-aaif-as-an-open-gateway-for-agentic-ai-infrastructure/)
- 协议：[draft-ietf-oauth-identity-assertion-authz-grant](https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/) · [RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693) · [RFC 7523](https://datatracker.ietf.org/doc/html/rfc7523) · [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414) · [GEP-713](https://gateway-api.sigs.k8s.io/geps/gep-713/)
- 同业：[LiteLLM Web Search Interception](https://docs.litellm.ai/docs/integrations/websearch_interception) · [LiteLLM Claude Code Websearch](https://docs.litellm.ai/docs/tutorials/claude_code_websearch) · [Bifrost × Claude Code](https://www.getmaxim.ai/bifrost/blog/integrating-claude-code-with-bifrost-gateway) · [Okta XAA sandbox](https://xaa.dev)
- 周边：[kgateway v2.3.2](https://github.com/kgateway-dev/kgateway/releases/tag/v2.3.2) · [kagent](https://github.com/kagentdev/kagent)
- 上轮报告：[r22（16:50）](reports/2026-06-06-1650-aigw-agent-gateway-r22.md) · [r21（10:03）](reports/2026-06-06-1003-aigw-agent-gateway-r21.md) · [r20（09:25）](reports/2026-06-06-0925-aigw-agent-gateway-r20.md)
