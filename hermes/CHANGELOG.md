# Changelog

AI Gateway 调研的更新日志。

## 2026-06-04

### 报告
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

### 报告
- [2026-06-05-0106-aigw-mcp-gateway.md](reports/2026-06-05-0106-aigw-mcp-gateway.md)
  - 主题：MCP Gateway 专题（cron 第 1/8 轮）
  - 抓取时间：2026-06-05 01:06 CST
  - 数据：2026-07-28 RC 7 大主变更 / Auth IG 宪章落地 / ToolHive v0.29.1 / Registry 6 个安全 PR
  - 重点：协议去掉 session/initialize、server/discover、MRTR 模式、Tasks 改扩展、Auth IG 2 个 Active WG
  - 建议：企业用 `_meta` 透传 OTel；做"server+client 双面 gateway"；治理静态 API key
