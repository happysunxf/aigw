# Changelog

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
