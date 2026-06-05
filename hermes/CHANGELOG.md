# AI 网关持续深挖 · CHANGELOG

> 自动化 cron 任务产出记录。每 30 分钟一次，主题按 `local hour % 7` 轮换。
> 报告文件存放在 `reports/`，命名格式 `YYYY-MM-DD-HHMM-aigw-<topic>.md`。

## 2026-06-06

- 03:28 · `semantic-routing-algorithms-cache` · round 5 — **router 算法内核 + 语义缓存** 专题。第 5 视角从「网关拼装」切到「路由决策用什么模型」。NadirClaw v0.19 (05-29) 把算法收敛到「`wide_deep_asym_v3` 预分类 (33 维结构特征 + BGE-small + λ=3 降级惩罚) + DeBERTa-v3-small INT8 cross-encoder 后验证 + τ=0.80 cascade」,RouterBench AUROC 0.961 / ECE 0.016 / 60% 成本压缩 / 0 overlap 污染审计;BitRouter v1.0.0-alpha.7 (06-03) Rust ~10ms / 跨协议翻译 / MCP+ACP / `brvk_*` 虚拟 key;Tessera SDK 0.1.0/0.1.1 (05-18) flat-tier 月费不按节省抽成 + savings ledger;LiteLLM 6 天 5 tag (1.87.0/1.87.1/1.88.0-rc.1~3),`#29612/#29636/#29645` 双线 backport `GHSA-q775 session-token budget-ceiling exemption`,5 条 security advisories 全爆在「路由层权限边界」;SmarterRouter 2.2.5~2.2.7 主推 Ollama `/api/show` 自动 capability detect + 熔断器多 quota 消歧;语义缓存层 vCache 提「可靠性 benchmark 套件」、prompt-cache 0.4 全 chunk 复用、Anthropic 端侧 5min/1h 命中、C2C (ICLR'26) 学术 KV cache 跨 prompt 复用 4 条线分流。NotDiamond/Martian 核心 SDK 自 2025 H2 几乎 0 动,「single-binary-rust / drop-in-sdk / cascade-rule-engine / local-first-ollama」4 个新故事在抢同一批客户。详见 [report](reports/2026-06-06-0328-aigw-semantic-routing-algorithms-cache.md)。
- 01:25 · `mcp-gateway` · **审计 + 零留存** — 5/29–6/5 协议层与生产侧同步推进。**协议侧**：(1) PR #2855 给 `server/discover` 加 `cacheScope: public|private` + `ttlMs`，多租户 cache 串号提升为 wire-level MUST NOT；(2) PR #2843 Authorization IG 正式 charter（Okta/Amazon/Anthropic 三厂 facilitator），6 WG 中 4 已 Completed / 2 Active；(3) PR #2863 SEP-to-Spec 一致性 pass 新增 "Tier 1 持续不暴露 deprecation warning 即降级" + "Deprecated 可长期保留"。**SEP 侧**：SEP-2817 `_meta.io.modelcontextprotocol/aiInvocation` 审计上下文（invocationReason / model / userIntent / turnId），MCP 史上首份自带 "AI 辅助声明" 的 SEP；拼图含 SEP-2448 server telemetry 返 spans、SEP-2787/2809/2828/2672 全链路证据化、SEP-1913 trust tier、SEP-2385 tool auth manifest。**生产侧**：Docker mcp-gateway PR #497（5/27）用 strings.Repeat 拼装 test token 字面量绕过secret-scanning 误报；Cloudflare PR #358（6/1）Semgrep Pro 回退 CE、findings 留仓；Cloudflare PR #386 17 个 OAuth server 锁 0.4→0.7；Microsoft PR #2690 EnterpriseMCP 进官方 catalog、PR #2781 CI 不发 telemetry。详见 [report](reports/2026-06-06-0125-aigw-mcp-audit-redact.md)。
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
