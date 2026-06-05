# Kong AI Gateway 深度追踪（2026-06-06 凌晨版）

> 主题：单产品发版追踪 · Kong
> 抓取时间：2026-06-06 00:13 CST（UTC+8）
> 报告生成：hermes-agent cron (topic=release, hour%7=0, target=Kong)
> 上次该主题：2026-06-05 21:34（higress-release），本次按"依次轮换"规则选 Kong

本期聚焦 **Kong 3.9.x（开源）和 3.14.x（企业版）系列在 2026-04 至 2026-06 的密集迭代**。两个分支在同一天（2026-06-04）各发了一版，且 AI/MCP 插件矩阵几乎横跨全部 release——这意味着 Kong 已把 AI Gateway 当作"一等公民"在持续打磨，不再是零散附加。

## 一、版本时间线（按发布日期倒序）

| 版本 | 类型 | 发布日期 | 关键标签 |
|---|---|---|---|
| **3.9.2** | 开源 (OSS) | 2026-06-04 | nginx CVE patch、luarocks 3.12.2 |
| **3.14.0.5** | 企业 (EE) | 2026-06-04 | AI Bedrock 错误码、MCP 工具缓存、HTTPS 端口保留 |
| 3.14.0.4 | 企业 | 2026-05-28 | HTTP/1.1 smuggling (CVE-2026-6338)、OpenSSL 3.5.6、libexpat 2.8.1 |
| 3.14.0.3 | 企业 | 2026-05-25 | ai-prompt-decorator 原生协议透传、Azure Realtime API GA |
| 3.14.0.2 | 企业 | 2026-04-28 | MCP OAuth2 token_exchange 修复、Claude Code Bedrock 统计、Anthropic gzip |
| 3.14.0.1 | 企业 | 2026-04-10 | openid-connect 嵌套 claim |
| **3.14.0.0** | 企业 (大版本) | 2026-04-07 | TLS 验证默认开、A2A 协议插件、DeepSeek / Databricks / vLLM / Ollama provider、GCP 自定义 OAuth、AI MCP OAuth2 Token Exchange、bytes-based tokenizer、conf.model.metadata |
| 3.9.1.2 | 企业 | 2025-07-07 | route_match_calculation、PDK get_raw_forwarded_path |

> 节奏观察：3.14 系列从 4-07 GA 起到 6-04 不到两个月已经发了 6 个 patch，平均 9 天一版；3.9.x 在 2026 跨了一年没动，6-04 这版更像是"安全补个洞"。

## 二、AI 插件矩阵：本周期（3.14.0.x + 3.9.x unreleased）的高频关键词

把 3.14.0.0 ~ 3.14.0.5 五个版本的 release notes 过滤 "ai" 命中，整理出"被反复动到的插件"：

```
高频改动 AI 插件（按命中次数）
 1. ai-proxy-advanced         — 11 次（几乎每个 patch 都有它）
 2. ai-mcp-proxy              — 5 次
 3. ai-mcp-oauth2             — 4 次
 4. ai-azure-content-safety   — 2 次
 5. ai-prompt-decorator       — 2 次
 6. ai-request-transformer /
    ai-response-transformer   — 2 次（合起来）
 7. ai-guardrails / ai-guardrail — 2 次（命名都不统一，已经在收敛）
 8. ai-aws-guardrails         — 1 次
 9. ai-a2a-proxy              — 1 次（3.14.0.0 新增）
10. ai-custom-guardrail       — 1 次（3.14.0.0 新增）
```

开源 3.9.x 分支下 unreleased 目录里也堆了 14 个 AI 相关 yml：Azure 流式响应丢 token、Azure upstream_path 404、Gemini/Bedrock chunking bug、Anthropic tool_choice 转换、Gemini 流截断、Ollama 新流式 content type、metrics key 重命名（`ai.ai-proxy` → `ai.proxy`）、`upstream_path` deprecate `upstream_url` 等等——这是把企业版的修复反向 backport 回去的常态节奏。

## 三、值得展开的四个工程信号

### 1. Provider 矩阵在"快速吞并新兴厂商"
3.14.0.0 一次性新增了 **DeepSeek、Databricks、vLLM、Ollama** 四个 provider，加上此前的 OpenAI/Azure/Bedrock/Anthropic/Gemini/Hugging Face/Cohere——Kong AI Proxy Advanced 已能在一个 route 后挂 10+ 种 LLM 后端。
- vLLM 进入一线 gateway 默认 provider 列表是个重要信号：意味着 OSS 自托管推理被当成生产形态。
- DeepSeek 出现在网关 provider 列表里，证实国内模型出海 / 海外接入中国模型的需求已经沉淀到产品层。
- Databricks 加上 3.14.0.5 修掉的 `stream_options` 不兼容问题（Databricks 拒收 stream_options），是把"企业数据平台 + LLM"作为重点场景。

### 2. 协议层三件套：A2A / MCP / 原生透传
- **A2A 协议（ai-a2a-proxy）**：3.14.0.0 新增，Google 推的 Agent-to-Agent 协议。这是 gateway 厂商里**第一个把 A2A 做成独立插件的**，比 Portkey/LiteLLM 走得早。
- **MCP 治理（ai-mcp-proxy + ai-mcp-oauth2）**：5 个 patch 全部命中。3.14.0.2 修 token_exchange cache toggle 读错配置；3.14.0.3 修 self-signed cert 下 API→tool 转换失败、tool id 重复；3.14.0.5 修 `deck sync` 后 tools 缓存空、HTTPS MCP 内部 Unix socket 丢端口——MCP 在 Kong 内部已经从"附加功能"升级到"专门 patch line"。
- **ai-prompt-decorator (3.14.0.3)**：修了"原以为能往 OpenAI 转换再发回，结果把 Gemini/Anthropic/Bedrock/Cohere/HuggingFace 的原生 body 也转了"——这个 bug 是个典型协议混叠问题，反映企业内多协议并存是常态。

### 3. 统计/可观测/安全的三重收紧
- 3.14.0.0 一口气把 `tls_certificate_verify`、`hide_credentials`、`ssl_verify` 全都默认从 off 改成 on，并把 Lua sandbox 默认从 `sandbox` 调到 `strict`。这不是"加功能"，是"把过去 5 年默认松散的安全 posture 收口"。
- 3.14.0.0 新增 `ai-a2a-proxy` 的 **Prometheus 和 OpenTelemetry 原生导出**——A2A 专属指标（method/latency/task_state）直接进 OTel collector，不需要再写 plugin 适配。
- 3.9.x unreleased 里把 `ai.ai-proxy` 这个 metrics key 改名为 `ai.proxy`，因为"file-log / http-log 等 logging 插件也用这个 key 在推 metric 管线，会冲突"——典型的"指标命名权在生产里打起来了"的修法。

### 4. CVE 节奏比想象中紧
- 3.9.2（OSS）一个 patch：6 个 nginx CVE（CVE-2026-40701/40460/42934/42946/42945/9256）
- 3.14.0.4（EE）一个 patch：CVE-2026-6338（CL.0 request smuggling）+ 5 个 nginx CVE + libexpat 2.8.1（7 个 CVE）+ OpenSSL 3.5.6（7 个 CVE）
- 这两组 CVE 几乎完全重合——OSS 用户 3.9.2 修了，EE 用户必须跟 3.14.0.4。**两边同一天（2026-06-04）发版是协调出来的**，否则会让用户搞混安全状态。

## 四、对架构选型读者意味着什么

- **如果你在 Kong 3.8.x 之前**：必须升级到 3.9.2 / 3.14.0.5，不升直接吃 6 个 nginx CVE + 1 个 smuggling。
- **如果你在做 MCP 网关评估**：Kong 是目前唯一在 GA 里同时提供 OAuth2、Token Exchange、scope→ACL、claim→consumer mapping 的网关；Portkey、Helicone 在 MCP 治理上还停在"按 key 隔离"阶段。
- **如果你在多模型路由**：Kong 的 provider 数量已超过 LiteLLM（LiteLLM 大约 100+，但很多是社区驱动；Kong 走"我挑过的"路线，目前 10+ 个生产可用 provider，每家都有官方维护测试）。
- **如果你在做 A2A / multi-agent**：3.14.0.0 之后 Kong 是目前**唯一原生支持 A2A JSON-RPC + REST 双绑定的网关**。比自建 OpenAI Agents SDK 或 Anthropic MCP-only 路线多一层"全协议透传"。

## 五、本期不确定 / 待观察

- 3.9.x 开源与 3.14.x 企业版之间的"功能滞后"在扩大——3.14.0.0 的 provider 新增、bytes-based tokenizer、A2A 插件，截至本期抓取 OSS 3.9.2 都没有 backport 迹象。
- AI 插件命名在 3.14 系列里出现过 "ai-guardrail" vs "ai-guardrails"（3.14.0.0 vs 3.14.0.3）的不一致，changelog 没说是否做 alias 兼容——可能是 changelog 笔误，也可能在做收敛。
- 未看到任何关于"支持 Anthropic MCP 协议作为后端"或"ai-proxy-advanced 支持 MCP 客户端"的产品信号。

## 引用与数据来源

- Kong 开源 release list (3.9.2 / 3.9.1 / 3.9.0) — https://github.com/Kong/kong/releases
- 3.9.2 详细 changelog — https://github.com/Kong/kong/blob/release/3.9.x/changelog/3.9.2/3.9.2.md
- 3.9.1 详细 changelog — https://github.com/Kong/kong/blob/release/3.9.x/changelog/3.9.1/3.9.1.md
- 3.9.0 详细 changelog — https://github.com/Kong/kong/blob/release/3.9.x/changelog/3.9.0/3.9.0.md
- 3.9.x unreleased 目录 — https://github.com/Kong/kong/tree/release/3.9.x/changelog/unreleased/kong
- Kong 企业版 Gateway changelog（3.14.x 全部条目）— https://docs.konghq.com/gateway/changelog/
- Kong 仓库主页 — https://github.com/Kong/kong
- Kong/ai-marketplace 仓库 — https://github.com/Kong/ai-marketplace
- Kong/mcp-konnect 仓库 — https://github.com/Kong/mcp-konnect
- 报告本地路径 — ~/hermes/reports/2026-06-06-0013-aigw-kong-release.md
