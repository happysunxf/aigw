# AI 网关持续深挖 · CHANGELOG

> 自动化 cron 任务产出记录。每 30 分钟一次，主题按 `local hour % 7` 轮换。
> 报告文件存放在 `reports/`，命名格式 `YYYY-MM-DD-HHMM-aigw-<topic>.md`。

## 2026-06-06

- 04:10 · `guardrails` · **prompt injection 防御在 gateway + agent middleware 层的实战**。聚焦 5/4–6/5 三家上游同时落地的"tool-call 前 / 工具结果后"中间件：(1) LangChain 把 security middleware 矩阵铺齐——#37303 ATR Threat Detection（7 条 high-precision 规则源自 Agent-Threat-Rules 425 条 catalog，97.1% recall on NVIDIA garak）+ #37192 SecretMiddleware（tool-arg 凭据 IDS，9 种 BUILTIN_SECRET_TYPES 含 GH fine-grained PAT / LangSmith / OpenAI project / AWS / JWT，draft 状态）+ #34715 RAG 间接注入硬化（XML `<context>` 包裹 + explicit IGNORE 指令，作者 skyvanguard 5/20 closed）+ #37906 memory write validation hook（OWASP ASI-06 长期中毒）+ #36317 monorepo 顶层 THREAT_MODEL.md。(2) LiteLLM 三件前所未见：#29647 修 provider-handler `extra_body` 注入链（`safe_merge_extra_body` 让 validated key 胜出 + Interactions handler 干掉 `model`/`agent` 互斥注入，guardrail `validation_target` 不再被 client 改写——等于把"scan-vs-send mismatch"护栏补上）；#28249 把 Cisco AI Defense 接进 guardrail_hooks，**`inspection_type=chat|mcp` 双 surface** + MCP native JSON-RPC envelope；#29511 sensitive data sticky routing——**整 session 黏性 on-prem**，guardrail 触发的合规路由 ≠ block。(3) Anthropic cookbook #626 一次性 14 项 CMA-MCP 硬化：MCP `getAgent` 字段过滤、`listEvents` 500 cap、IP 限流 60 req/min、1MB body、容器非 root。(4) 反证：`@tzb1-ai` 在 5/30 把"Safety Report: AI Guardrails Do Not Work — 56-Day Proof (06K Loss)" cross-post 到 6+ 个上游 tracker（openai-python/anthropic-sdk/aider/aws-toolkit-vscode/TabNine/generative-ai-docs），reaction 0、形式 spam、内容**不是噪音**——5 项硬需求（hard gate / persistent violation / auth taxonomy / blast radius / mandatory dry-run）正好对应 OSS 5 月以来在 handler-layer 的 enforcement 落地。详见 [report](reports/2026-06-06-0410-aigw-guardrails-prompt-injection-middleware.md)。
- 02:06 · `agent-gateway` · round 18 — **trace 调试 / 成本归因** 专题。agentgateway 在 6/4–6/5 把 multi-agent 诊断链补齐到"OTel 出口 + Prometheus 按 call kind 切分 + CLI 把 pprof/heap/log 一把抓 + config_synchronized gauge"。三主线：#1784 新增 `OutboundCallKind`（Primary/Policy/Mirror）× `OutboundCallSubtype`（Http/Llm/Mcp/ExtAuthz/ExtProc/Guardrail/RateLimit/Oidc）双维度直方图，配 `MinimalHTTPLabels` 防 cardinality 爆炸；#2094 TTFT howardjohn 明确"在 #1784 路径上加 `gen_ai.server.time_to_first_token`"，#1170 GSoC 草案同期给 llm-d-inference-sim 基准（agentgateway 6.3ms / TTFT 3.0ms vs baseline 3.2ms / 0.95ms）。运维侧：#2061 `config_synchronized` gauge 已合；#2098 agctl 重组加 `proxy log` / `controller log`（追加式 directive）；#2096 agctl pprof 封装待合。周边：#2039 多 AI policy 字段级 merge 已合；#1850 MCP prompts 在 multiplex 模式被忽略（影响 DNS-AID 拓扑）；#2095 WebSocket 大小写 bug 让"成功但立刻死"请求污染成本归因。详见 [report](reports/2026-06-06-0206-aigw-agent-gateway-r18.md)。
- 00:46 · `release` · **Helicone** — 单产品发版追踪。285 天未发新 tag（最近 `v2025.08.21-1`），main 仍在高活跃（5/18 单日 5 PR）。聚焦三件事：(1) 5/14–5/18 AWS Bedrock key 误报致 4 天观测层降级，proxy 没事、无数据丢失、全 credentials 轮换；(2) PR #5665 揭示一行 `console.log` 把 CloudWatch 从 1GB/天拉到 1.5–3.9TB/天，4 月单月 \$22,475；(3) PR #5683 揭示 bifrost 站点 2 个月没成功生产部署（Vercel 静默回退旧构建）。AI Gateway 端点 `ai-gateway.helicone.ai` 当前 405 正常，状态页 99.9999% uptime 18+ 月。详见 [report](reports/2026-06-06-0046-aigw-helicone-release.md)。
- 00:13 · `release` · **Kong** — Kong 3.9.2 (OSS) / 3.14.0.5 (EE) 同步发布同日 (2026-06-04)。重点：3.14.0.0 一次性新增 A2A 协议插件、DeepSeek/Databricks/vLLM/Ollama provider；5 个 3.14.0.x patch 全部命中 ai-proxy-advanced 与 ai-mcp-proxy。MCP 治理（OAuth2 + Token Exchange + scope→ACL）已成企业版主线。详见 [report](reports/2026-06-06-0013-aigw-kong-release.md)。

## 2026-06-05

- 23:34 · `agent-gateway` · round 17 — agent gateway 持续追踪。
- 23:02 · `mcp-sdk-reliability` · MCP SDK 可靠性专题。
- 22:11 · `mcp-spec-ia-refactor` · MCP 规范 IA 重构。
- 21:34 · `release` · **Higress** v2.2.2 — Higress 发版追踪。
- 21:02 / 20:11 · `arch-benchmark` · round 4/3 — 架构对比/性能基准。
- 19:38 / 18:58 / 18:19 · `guardrails` · streaming/trust/runtime defense。
- 17:36 · `tech-deepdive-article` · 70KB 技术深度长文。
- 17:04 / 16:49 / 16:18 / 15:28 · `agent-gateway` / `mcp-2026-07-28-rc`。
- 13:18 · `arch-benchmark` · round 2。
- 12:38 · `observability-industry-reshuffle` · 行业洗牌专题。
- 12:08 / 11:54 / 11:10 · `guardrails` PII / 数据驻留 / 供应链。
- 10:31 · `routing-cost-attribution` · 成本归因。
- 09:50 / 09:13 · `mcp-governance-cluster` / `agent-gateway`。
- 08:34 · `mcp-deploy-arch` · MCP 部署架构。
- 08:01 · `release` · **Envoy AI GW** — Envoy 发版追踪。
- 07:16 · `release` · **Portkey** — Portkey 发版追踪。
- 06:32 · `arch-benchmark` · 架构对比/性能基准 round 1。
- 05:45 / 05:06 · `observability` · 可观测/监控专题。
- 04:25 · `guardrails` · guardrails 专题。
- 03:48 / 03:06 · `routing-cost-security` / `semantic-routing-cost`。
- 02:26 · `agent-gateway` · agent gateway 专题。
- 01:46 / 01:06 · `mcp-gateway-products` / `mcp-gateway`。
- 00:34 · `release` · **LiteLLM** — LiteLLM 发版追踪。
