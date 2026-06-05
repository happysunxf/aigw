# AI 网关持续深挖 · CHANGELOG

> 自动化 cron 任务产出记录。每 30 分钟一次，主题按 `local hour % 7` 轮换。
> 报告文件存放在 `reports/`，命名格式 `YYYY-MM-DD-HHMM-aigw-<topic>.md`。

## 2026-06-06

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
