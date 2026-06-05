# Envoy AI Gateway v0.6.0 深度追踪 & 后续 main 进展

> 主题：单产品发版追踪 — Envoy AI Gateway（aigw-*-release 系列第 3 篇）
> 报告生成时间：2026-06-05 07:50 CST（Friday）
> 抓取窗口：v0.6.0（2026-05-05）→ main 分支截至 2026-06-04
> 数据源：GitHub Releases / Commits / PRs、aigateway.envoyproxy.io 官方站点

## 1. 仓库基本面

| 指标 | 值 |
|---|---|
| 仓库 | `envoyproxy/ai-gateway`（CNCF，Apache-2.0） |
| Stars / Forks | 1,717 / 269（截至 2026-06-04） |
| Open Issues | 154 |
| 最近 commit | 2026-06-04T20:52Z（PR #2187） |

Bloomberg + Tetrate 联合发起的 AI/LLM 网关，把 Envoy Gateway / Envoy Proxy 能力（HTTP/2、mTLS、可观测、动态配置）延伸到 LLM 流量；自 v0.4 起把 MCP 网关纳入产品范围。

## 2. v0.6.0（2026-05-05）：首个生产可用 API 表面

官方首句："v0.6 marks the first production-ready API surface"。5 个核心 CRD 升 `v1beta1`：`AIGatewayRoute` / `AIServiceBackend` / `BackendSecurityPolicy` / `GatewayConfig` / `MCPRoute`。v1alpha1 仍注册（带 deprecation 警告），存量 manifest 兼容。

### 2.1 重大新能力

**AWS Bedrock**：原生 `InvokeModel` API 支持 Claude（Anthropic 客户端薄路径）；OpenAI → Bedrock Titan embeddings 翻译（Cohere 暂未覆盖）。

**Anthropic 跨 provider 翻译**：
- Anthropic `/v1/messages` 端点可暴露在任意 OpenAI 后端前面——Claude 客户端无缝打 OpenAI / Azure OpenAI / 任何 OpenAI 兼容 provider。
- 结构化输出（JSON schema）下放到 Anthropic 与 Bedrock Claude（GCP Vertex AI Claude 暂缺）。
- `max_tokens` 缺省不再让 translator 崩；Adaptive thinking for `claude-opus-4.6`。
- 统一 `reasoning_effort` 跨 Anthropic / OpenAI / Gemini——单旋钮（`low/medium/high/xhigh`）映射到 Anthropic thinking budget + Gemini 3 thinking controls。

**Gemini**：embeddings 走 OpenAI `/v1/embeddings` 合约；context caching 用 Anthropic 风格 `cache_control` prefix；reasoning 输出为 thinking blocks（非流式同时给 string content + 结构化 `thinking_blocks`）。

**OpenAI 兼容**：Responses API 第二波（context management + 改善 streaming）；兼容开源 Responses API 实现；新增 `/v1/audio/speech` TTS 端点。

**MCP Gateway**：per-backend header forwarding with rename（`MCPRouteBackendRef.forwardHeaders`）；JWT claim forwarding to MCP backends（`MCPRouteOAuth.claimToHeaders`）；tool selector 排除规则（`MCPToolFilter.exclude` / `excludeRegex`）；tool name 进 access log & dynamic metadata（key `mcp_tool_name`）；per-backend capability tracking——客户端拿到的是"实际可达后端的能力交集"。

**Auth & Identity**：GKE Workload Identity via Application Default Credentials——`BackendSecurityPolicy` 不写 `credentialsFile` / `workloadIdentityFederationConfig` 时自动用 workload identity，落地 GKE 可摘掉静态 SA JSON secret。

**Security & Privacy**：请求/响应 body redaction——写日志/trace/指标前遮罩敏感字段。

**Observability**：`aigw` 启动时自动配置 OTLP access logging；默认 `agent-session-id` → `session.id` 头映射——Goose 等 agent 框架零配置关联 session，Metrics 永不默认带 session id（高基数考量，做得很克制）；`LLMRequestCostType.ReasoningToken`——thinking token 单独成成本类型；response model metadata——响应带回"实际命中的上游模型"，便于 model aliasing / fallback 校验；OTEL 属性计数上限移除——长上下文 trace 字段不再被静默丢弃。

**Operations**：Webhook 端口可配 + 宿主网络（`controller.mutatingWebhook.port` / `controller.hostNetwork`，GKE private cluster 部署更顺）；AI ExtProc stage 之后可挂 Lua filter；Route-scoped LLM request costs + 全局默认（`GatewayConfig.spec.globalLLMRequestCosts` + `AIGatewayRoute.spec.llmRequestCosts`）。

### 2.2 两个 breaking change

1. **`AIGatewayRoute.spec.filterConfig` 移除**——v0.5 已把 `resources` 子字段标 deprecated，v0.6 整个 `filterConfig` 删除。extProc 配置必须搬到 `GatewayConfig`，Gateway 用 `aigateway.envoyproxy.io/gateway-config` annotation 引用。
2. **`VersionedAPISchema.version` 不再当 endpoint 前缀**——必须用 `prefix` 字段（Gemini：`prefix: /v1beta/openai`；Cohere：`prefix: /compatibility/v1`）。

### 2.3 新 API / 依赖 / Bug Fixes

新 API：`MCPRouteBackendRef.forwardHeaders` / `MCPRouteOAuth.claimToHeaders` / `MCPToolFilter.exclude` & `excludeRegex` / `LLMRequestCostType.ReasoningToken` / `GatewayConfig.spec.globalLLMRequestCosts` / Preview `QuotaPolicy`（v1alpha1，无 controller reconcile / 强制，纯 API 占位）。

依赖：Go 1.26.2 / Envoy Gateway v1.7.0 / Envoy v1.37 / Gateway API v1.4.1 / Gateway API Inference Extension v1.0.2 / MCP Go SDK 1.4.1。

Bug Fixes：Webhook cache race（刚 apply 的 `AIGatewayRoute` 偶尔 extProc 注入失败）；Secret rotation 不再需要重启 MCPRoute；AWS Bedrock Titan embeddings dataplane route 恢复；Bearer token 解析 panic 修复；`aigw` standalone 启动失败给清晰错误不再 hang；JSON 大小写敏感 marshal/unmarshal 修齐；`aigw` standalone 接受 IP 地址当 endpoint（127.0.0.1 loopback 测试通了）。

## 3. v0.6.0 之后 30 天 main 分支增量

### 3.1 QuotaPolicy 从 API 占位走向运行时落地

**PR #1869（2026-06-04 merged）**：`feat: inject backend quota rate limit filter for QuotaPolicy`——v0.6 preview API 真正落地的第一步。流程：用户创建 `QuotaPolicy` CR → controller 调 `translator.BuildRateLimitConfigs()` 构建 RateLimitConfig protobuf → xDS 推到 rate-limit service（Redis）→ Envoy 请求期执行 rate limit → extProc 拿 token 用量 → stream-done 时把 `HitsAddend` 加到 Redis counter。首次把"按 token 消耗作为 rate limit 维度"真正跑通。What's Next 明确：未来要做 quota-aware routing——按上游当前配额状态自动绕开 429。

### 3.2 Responses API / 音频 / 多模态

- **PR #2122**：Azure OpenAI Responses API 支持——新增 Azure 专用 translator，路由到 `/openai/responses?api-version=...`，避免污染 OpenAI 主 translator。作者披露"PR 由 gpt-5.5 协助"，已 review 持有 ownership——AI 辅助 PR 在主仓已常态化。
- **PR #2023**：补齐 `/v1/audio/transcriptions` + `/v1/audio/translations`。关键设计：`EndpointSpec` 接口加 `ParseMultipartBody` 方法，纯 JSON 端点返回 `errMultipartNotSupported`。
- **PR #2136**：`audio_url` / `video_url` content types in OpenAI schema——点名 phi-4-mm / qwen3.5 多模态推理服务器。
- **PR #2163**（Responses streaming SSE 缓冲）/ **PR #2172**（typeless assistant 消息）同期合并。

### 3.3 Anthropic 路径的推理 + 图像增强

- **PR #2099**：Anthropic↔OpenAI 双向翻译里，之前 thinking content 和 image block 被静默丢弃，现修齐：透传 thinking config、保留多轮 thinking blocks、base64/URL image block 转 `image_url`；响应方向把 `thinking_blocks` 翻成 Anthropic 形状。
- **PR #2103**：新增 `anthropic_awsbedrock.go`——Anthropic 客户端格式可打到 Bedrock 上任何模型（不只是 Claude），覆盖 messages / system / tools / thinking config / images / streaming / error translation。
- **PR #2108**：Anthropic 后端之前 `prefix` 字段被静默丢弃（路径硬编码 `/v1/messages`），现按 schema 走 prefix，可挂自定义前缀的 Anthropic 兼容后端。默认 `prefix="v1"`，行为不变。

### 3.4 MCP 治理两条设计提案（v0.7 候选）

- **PR #2144（2026-06-03, size/XXL）**：`docs: proposal for MCPBackend CRD`——把 `MCPRoute.spec.backendRefs[]` 的 inline 配置抽成独立 `MCPBackend` CRD。动机：inline 在 backend 数量上去后撞 K8s object size limit；token exchange（RFC 8693）会再加 ~25 行嵌套配置。推荐方案：`MCPBackend CRD` + 扩展现有 `BackendSecurityPolicy`（加 `targetRefs`）+ `MCPRouteBackendRef` 显式 `Name/Group/Kind` 字段做向后兼容。
- **PR #2052**（对接 issue #2036）：OAuth 2.0 Token Exchange as Upstream Auth for MCP Backends——企业 agent（VS Code）通过网关调 GitHub Copilot MCP；入向企业 IdP（Okta/Entra）OAuth/OIDC，出向 GitHub 不认内部 token，网关做 RFC 8693 token exchange，实现 per-user attribution + 网关层 token 兑换。两条都是"提案文档"，无实现代码，勾勒 v0.7：MCP 后端解耦 + token exchange 网关化。

### 3.5 Hostname 路由 + 限速边界

- **PR #2160**：`feat: support hostname in aigateway route`——之前 `AIGatewayRoute` 是 cluster 级 CR，没法把一组模型绑到 `xx.api.aieg.com`；`/v1/models` 也会返回 cluster 内所有 route 的模型。修完可做 host-based 模型分组（多租户隔离）。
- **PR #2123**：`api: cap AIGatewayRoute rules at 15`——kubebuilder `MaxItems` 从 128 砍到 15。根因：Gateway API 给 `HTTPRoute.rules` 限定 `maxItems: 16`，AI Gateway controller 每条 AIGatewayRoute rule 产 1 条 HTTPRoute rule + 1 条 catch-all "route-not-found" rule，超过 15 条 AIGatewayRoute rule 会被 API server 静默拒绝，数据面停在旧 snapshot，`AIGatewayRoute` 资源上完全没有错误信号。改成 15 后 admission 直接报错；需要多 model rule 的 operator 拆 route。

### 3.6 杂项

PR #2089（Claude Opus 4.7 reasoning）/ #2132（body redaction 过度收，影响 debug）/ #2139（CI `contents:write`）/ #2157（Bedrock nil Output guard）/ #2155（SSE parser 不再丢字段）/ #2148（AWSAnthropic beta header）/ #2168（Go deps 13 项更新）/ #2187（Gemini 3.1 flash lite）。

> 节奏：v0.6 后 30 天 ~30 个功能 PR + 若干 fix，commit 频次约 1/天。四大主题：Quotas 落地、Responses API 全平台、音频/多模态、Anthropic 跨 provider 增强；v0.7 候选：MCPBackend + Token Exchange。

## 4. 对照前几篇专题

| 维度 | Envoy AI Gateway | 旁证 |
|---|---|---|
| CRD 模型 | K8s-native，5 CRD 已 `v1beta1` | LiteLLM 偏 SDK + proxy config；Portkey 偏 SaaS 控制面 |
| MCP 支持 | MCPRoute + OAuth + JWT claim 转发 + per-backend header + capability tracking | 上次 MCP 专题：Envoy 是少数同时支持 CRD + capability negotiation 的 |
| 可观测性 | OpenInference tracing + 多 cost type（含 `ReasoningToken`） | 上次 observability 报告：reasoning token 单独计费很少见 |
| 限速 | RateLimitConfig protobuf + Redis，token-level HitsAddend | 与上次语义路由/成本专题"按 token 算 rate limit"思路一致 |
| 跨 provider 翻译 | Anthropic↔OpenAI↔Gemini↔Bedrock | 与 Agent Gateway 报告"model-agnostic 抽象"对齐 |
| host / 多租户 | v0.6 + #2160 hostname 路由 + 拆 route | 多数网关 vhost 隐式，Envoy 走 K8s Gateway API 标准 host 表达 |
| License | Apache-2.0 + CNCF | 与 Higress（Apache-2.0）同档 |

## 5. 升级 & 落地建议

1. v0.5 → v0.6：把 `AIGatewayRoute.spec.filterConfig` 全部搬到 `GatewayConfig`；把 `VersionedAPISchema.version` 当前缀用的改成 `prefix`。
2. 新装：直接 `apiVersion: aigateway.envoyproxy.io/v1beta1`。
3. 试 QuotaPolicy：用 main 分支 PR #1869，runtime 强制已接通，fallback / 多 provider 路由还没做，按 alpha 用。
4. GKE 用户：可去掉 `BackendSecurityPolicy` 里的 `credentialsFile` / `workloadIdentityFederationConfig`，让 ADC 链接管 GCP 鉴权。
5. MCP 审计：直接读 `mcp_tool_name` dynamic metadata 接 access log。
6. Anthropic 客户端跨 provider：`reasoning_effort` + `claude-opus-4.6` adaptive thinking + `/v1/messages` 端点对外暴露，已能打 OpenAI / Azure OpenAI / 任何 OpenAI 兼容后端；Azure OpenAI Responses API（#2122）也通。
7. 多模型路由：注意 `AIGatewayRoute.rules` 限 15，超出需拆。
8. 关注 v0.7 候选：MCPBackend CRD（#2144）+ OAuth 2.0 Token Exchange（#2036/#2052），企业 SaaS MCP 场景即将解锁。

## 6. 引用与数据来源

**GitHub（拉取时间 2026-06-05 07:50 CST）**
- Releases 列表 API：`https://api.github.com/repos/envoyproxy/ai-gateway/releases?per_page=8`
- v0.6.0：https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0
- v0.5.0：https://github.com/envoyproxy/ai-gateway/releases/tag/v0.5.0
- 仓库元数据：https://api.github.com/repos/envoyproxy/ai-gateway
- PR 列表（直链同 `https://github.com/envoyproxy/ai-gateway/pull/<id>`）：#1869 QuotaPolicy、#2023 音频端点、#2052 Token Exchange 提案、#2089 Claude Opus 4.7、#2099 Anthropic→OpenAI 推理+图像、#2103 Anthropic→Bedrock、#2108 Anthropic prefix、#2122 Azure Responses、#2123 rules 上限、#2132 日志 redaction 调整、#2136 多模态、#2139 CI 权限、#2144 MCPBackend CRD 提案、#2148 AWSAnthropic beta header、#2155 SSE parser、#2157 Bedrock nil Output、#2160 hostname 路由、#2163 SSE 缓冲、#2168 Go deps 更新、#2172 typeless assistant、#2187 Gemini 3.1
- Issue #2036 Token Exchange 主线：https://github.com/envoyproxy/ai-gateway/issues/2036

**官方站点**
- Release Notes：https://aigateway.envoyproxy.io/release-notes/
- v0.6.x：https://aigateway.envoyproxy.io/release-notes/v0.6
- 文档：https://aigateway.envoyproxy.io/docs/0.6/
- 博客：https://aigateway.envoyproxy.io/blog
- 仓库：https://github.com/envoyproxy/ai-gateway
- Helm：`oci://registry-1.docker.io/envoyproxy/ai-gateway-helm --version v0.6.0`

**前几篇对照（hermes/reports/）**：2026-06-05-0034-aigw-litellm-release.md / 0716-aigw-portkey-release.md / 0146-aigw-mcp-gateway-products.md / 0226-aigw-agent-gateway.md / 0306-aigw-semantic-routing-cost.md / 0348-aigw-routing-cost-security.md / 0425-aigw-guardrails.md / 0506-aigw-observability.md / 0545-aigw-observability-2.md / 0632-aigw-arch-benchmark.md
