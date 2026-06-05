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
