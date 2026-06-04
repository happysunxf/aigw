# AI 网关可观测专题（续 · 2026-06-05 05:45）— Token 治理、eBPF 零插桩、Server 策略兜底、OTel GenAI 跨协议对齐

> 本期主题：**可观测 & 监控**（cron h%7==5）· 抓取时间：2026-06-05 05:45 (UTC+8)
> 上一篇：`2026-06-05-0506-aigw-observability.md`（Helicone/Mintlify、Langfuse v3.176-3.178、OpenLLMetry 0.61、OpenLIT 1.21、OTel semconv 拆分、Portkey 安全）
> 本期切片：① Phoenix v17.0-17.2 token 治理 + server 策略 ② eBPF 零插桩 LLM tracing 爆发 ③ OTel semconv-genai 独立仓跨协议对齐 ④ Langfuse 6-04 增量

---

## TL;DR

- **Token 治理成新一轮主战场**：Phoenix v16.2 (5-26) 修关键 bug "confine token counts to LLM spans at ingestion"（修复前 chain/tool/retrieval 父 span 累加的 token 会被重复归到 LLM span，成本归因偏高）；v17.0 (6-02) 引入 `system_settings` 表 + `agentTraceRecording` 策略 —— **server policy 是 ceiling，user preference 只能再窄**。把"谁能在哪里打 trace"从客户端 flag 升级为 server-enforced policy。
- **零插桩 eBPF 抓 LLM 从概念变可装可跑代码**：1 周内 `eunomia-bpf/agentsight` (381★) 发 v0.2.7/0.2.8/0.2.9 三 tag，主线推进 SSL filter 重构 + StdioRunner/SystemRunner + tool&file breakdown；`AkshantVats/ebpf-llm-tracer`（Go+BPF）从 BPF connect probe 推到 user-space HTTP parser + Kafka InferenceEvent schema。**不改一行应用代码，拿到 LLM 出入站 trace + token 计费**。
- **OTel GenAI semconv 跨协议对齐**：新独立仓 `open-telemetry/semantic-conventions-genai` 6-04 同日合并 4 个 spec-level PR：MCP context propagation 显式指向 **MCP SEP-414**（`traceparent`/`tracestate`/`baggage` 在 `params._meta` 中走无前缀 key），GenAI span duration 明确"含 retries、按 caller 视角计"，`gen_ai.conversation.id` 给 fallback 顺序，`gen_ai.request.top_k` 改 int 并把 retrieval top_k 拆出。
- **Langfuse 6-04 三件**：blob-storage 导出源可见性从 V4 beta toggle 解耦（V4 即将 GA 信号）、remote experiment config 读权限 gate、seeder 默认开启 AI 特性。
- **跨产品一致性**：上一轮讲"Helicone 维护 + Langfuse 接管"；本轮信号变成 **"把可观测做成云上控制面"** —— Phoenix admin trace ceiling、Langfuse in-app agent API key + audit、Portkey admin token default removal，三家同时收紧"可观测"动词后面的治理维度。

---

## 1. Arize Phoenix v17：Server 端 trace recording policy + PXI 助手

源：<https://github.com/Arize-ai/phoenix/releases>（v16.2 → v17.2.0）· 迁移：<https://github.com/Arize-ai/phoenix/blob/main/MIGRATION.md>

### 1.1 v17.0.0（6-02）— BREAKING：admin 控 trace 录制 · PR #13254

- 新增 `system_settings` 表（多进程共享、轮询、写穿缓存的 `SystemSettings` daemon 持有）。
- 第一条 setting：`agentTraceRecording` —— GraphQL 既能 query 也能 `setAgentTraceRecording` mutation；agent REST 路由在每条请求里把 per-request flag 与 server policy 求交集。**server policy 是 ceiling，不是 override**。
- 前端用 `getEffectiveTraceRecordingSettings` 在一处求值 `server ceiling ∧ user preference`。
- PXI 助手从客户端 feature flag 升级为 admin-managed `agent.assistant.enabled`（默认 on）。前端三道闸：`PHOENIX_DISABLE_AGENT_ASSISTANT` 部署环境 → admin system setting → per-user `useAssistantAgentEnabled`。
- **consent 模型改造**：`acknowledgedTraceConsent` 替换一次性 `hasAcknowledgedConsent`，把当时 server ceiling 整个快照下来；只有当 server **放宽**（开放新 channel）时再请求 consent，**收窄不动老 consent**。
- 附带：`generative_models.updated_at` 加索引（之前 cursor scan 是 sequential scan every poll）。

**为什么重要**：多团队共享的 Phoenix 部署（平台 SRE 给全公司装一套，各业务线自己用）以前 trace 录制完全靠"业务线各自配 client flag"，**SRE 没法保证 PII 一定不出域**。v17.0 后 SRE 可以在 server 端把 `agentTraceRecording` 锁到 `disabled`，所有请求一律不打 trace。这是公开 LLM 可观测平台里**第一条** "server-enforced 录制策略" 的 production-grade 落地（Langfuse 还在 client 配 `enabled`；OpenLLMetry / OpenLIT / Helicone / Portkey logs 都还是 SDK 端默认 on，靠 redaction 兜底）。`system_settings` 表是**通用 registry**，后续可挂 trace sampling rate、retention window、redaction rule set —— Phoenix 在搭"可观测控制面"。

### 1.2 v16.2 / v17.1 / v17.2 增量

- **v16.2 (5-26) #13433**: `fix: confine token counts to LLM spans at ingestion` —— OTel/GenAI 模型里**只有 span kind=LLM 的 span 才应该拥有 token 用量与 cost**；修复前 chain/tool/retrieval 父 span 也保留 token 字段导致**多 span 重复计费**、成本归因高估。和 v17.0 server 策略配套 —— **数据层 + 治理层双向收紧**。
- **v17.1 (6-02)**: `playground: add PXI load_dataset tool`（#13558）、`pxi: LLM-evaluator authoring`（#13579，**评估器本身也用 PXI 写**）、`skill loading display`（#13576）；修 `docs MCP init failure` 不会拖崩 server 启动（#13595）。
- **v17.2 (6-03)**: `add PXI route info tool`（#13591）、`scope assistant chat history to deployment root path`（#13615，多 deployment 隔离）、`expand PXI guide with skills, controls, and extensibility`（#13611）。

---

## 2. 零插桩 eBPF LLM Tracing：AgentSight + ebpf-llm-tracer

### 2.1 eunomia-bpf/agentsight（381★, C / Go）

源：<https://github.com/eunomia-bpf/agentsight> · releases v0.2.7-0.2.9 · 描述：**"Zero instrument system-level AI agent tracing in eBPF"**

时间线：

- 6-03 08:01 — v0.2.7
- 6-03 16:18 — v0.2.8
- 6-03 17:32 — v0.2.9
- 6-04 06:45 → 19:50 — 10 commit：重构 SSL filter、引入 `StdioRunner`/`SystemRunner` 两个 event collector、增加 tool & file breakdown、SSE 处理 / session DB summary 重构

**架构观察**：

1. **三类事件源**：BPF `connect()` hook（fd → dst_ip，ring buffer 上送）+ `StdioRunner`（抓 Claude Code/Codex CLI 的 stdin/stdout）+ `SystemRunner`（抓 open/exec/file write 系统调用）—— 三层覆盖 LLM HTTP + agent 进程 + 系统调用。
2. **SSL filter 重构**：抓 LLM 调用必须能读 TLS 明文。常见做法是 uprobe 注入 `ssl_read`/`ssl_write`（OpenSSL 3.x 的 `_libssl.so`），但 ABI 变化、SSL 厂商异构（OpenSSL/BoringSSL/libnss）让 uprobe 极脆弱；这次重构多半在解耦 libssl 版本变化。
3. **tool & file breakdown**：按 tool 调用（Read/Edit/Bash/Grep）和 file 操作做归因 → **直接对应 "cost attribution to tool"** —— agent 用得贵在哪一步一目了然。

输出格式猜测是 OTel-compatible JSON spans（eunomia-bpf 一贯风格）—— 可直接喂给 OTel Collector / Langfuse / Phoenix 后端。380+ star + 持续 6-04 commit，是**目前 OSS 端最活跃的 eBPF LLM tracing 项目**。

### 2.2 AkshantVats/ebpf-llm-tracer（Go + BPF，独立项目）

源：<https://github.com/AkshantVats/ebpf-llm-tracer/commits>

- 6-01 07:52 — `feat: BPF connect probe — fd→dst_ip map, ring buffer events, Go loader (Day 15)`
- 6-01 08:15 — `feat(http-parser): userspace HTTP parsing for LLM API events`
- 6-04 09:40 — `feat(kafka): InferenceEvent schema + Kafka producer + E2E mock (Day 17)`
- 6-04 17:43 — `refactor: oss-polish day-17 — gofmt, errcheck, docs`

定位更 narrow：**专门抓 LLM HTTP 出入站**，从内核 `connect()` 探针开始（fd → dst_ip），ring buffer 上送 userspace，userspace 做 HTTP 解析（识别 `/v1/chat/completions` / `/v1/responses` / `/v1/messages` / Anthropic / OpenAI / Cohere 路径），把 `model`、`prompt_tokens`、`completion_tokens` 抽出来封装为 `InferenceEvent` schema，6-04 推到 Kafka。与 AgentSight 互补（一个抓 LLM、一个抓 agent，event schema 互不冲突）。

### 2.3 同期活跃项目 & 观察

`eunomia-bpf/agentsight` (381★) C/Go · `AkshantVats/ebpf-llm-tracer` Go+BPF · `eunomia-bpf/MCPtrace` (70★) Rust · `deepflowio/deepflow` (4114★) 通用 eBPF APM · `CloudDetail/apo` (380★) OTel+eBPF。除 deepflow 这种"通用 eBPF APM"，**专门做 LLM/agent 的 eBPF 工具** 在 2025-07 之前几乎为零；agentsight 出现后 2026 上半年集中爆发。**eBPF 是 2026 年 LLM 可观测最被低估的一条赛道**。

---

## 3. OTel semantic-conventions-genai 跨协议对齐

源：<https://github.com/open-telemetry/semantic-conventions-genai>（5-05 从 `open-telemetry/semantic-conventions` 拆出）

> 5-05 commit `c9e48b1d1a` "Move GenAI semantic conventions to its own dedicated repository (#3696)" —— 第一阶段（仓库拆分）。
> 6-04 一次合并 4 个 spec-level PR —— 第二阶段（开始大规模规范细化）。

### 3.1 6-04 一次性落地的关键 spec PR

| PR | 标题 | 影响 |
|---|---|---|
| **#220** | Clarify MCP context propagation | 显式指向 **MCP SEP-414**（`traceparent`/`tracestate`/`baggage` 走 `params._meta`、**无前缀**） |
| **#216** | Clarify GenAI span duration | GenAI span SHOULD 含 retries、按 caller 视角计；与 RPC/DB semconv 措辞对齐 |
| **#217** | `gen_ai.request.top_k` 改 int，retrieval top_k 拆出 | `gen_ai.retrieval.top_k` 独立 |
| **#219** | Clarify GenAI conversation id fallbacks | 给出 `gen_ai.conversation.id` 在缺省场景下的回退顺序 |
| **#214** | `gen_ai.provider.name` 在 `gen_ai.client.operation.duration` 上从 Conditionally Required 降为 Recommended | 减少 SDK 必填字段 |

### 3.2 PR #220 的战略意义

**MCP SEP-414**（<https://modelcontextprotocol.io/community/seps/414-request-meta>）是 MCP 协议层扩展，把 OTel 标准 `traceparent`、`tracestate`、`baggage` HTTP header **去掉前缀**塞进 MCP JSON-RPC `params._meta`。

- 直接好处：**MCP client/server 之间的 distributed trace 不需要任何 SDK 改造**，因为 `_meta` 已经是协议级概念。
- 配合上周已覆盖的 `agctl/dtrace` 流式 trace + A2A first-class backend —— **MCP / A2A / GenAI semconv 三件套第一次在 OTel 规范层面正式交叉**。
- 对 vendor 硬要求：所有"声称支持 OTel GenAI semconv"的 agent 框架（LangGraph、AutoGen、CrewAI、agentgateway）都应在 MCP 通道透传 `params._meta` 而不是丢弃。

`open-telemetry/semantic-conventions` 主仓自 v1.41.1（5-11）以来**没有新 release**，GenAI 子仓独立运作 —— 5-05 拆分计划**按预期执行**。

### 3.3 影响 OSS SDK

- OpenLLMetry 0.61.0（5-31）已"全面对齐 OTel GenAI semconv"（上轮报告过）；本轮新规范字段需要在下一次 minor（0.62 或 0.63）跟进。
- OpenLIT 1.21.x 的 guardrails / offline evals 改造也按 GenAI semconv 推进。
- Phoenix v16.2 的 `confine token counts to LLM spans` 实际是 GenAI semconv 1.41 "Span kind = LLM is the only one that carries token usage" 的 enforcement。

---

## 4. Langfuse 6-03 ~ 6-04 增量 & 5. 选型增量建议

源：<https://github.com/langfuse/langfuse/commits>（since 2026-06-02）

**v3.179 / 3.180 候选**：

- `1d863d41d9` 6-04 17:09 — `feat(blob-storage): decouple export source visibility from V4 beta toggle (#14032)`：**暗示 V4 即将 GA**。
- `4c89785249` 6-04 15:21 — `fix(datasets): gate remote experiment config reads (#14009)`：远程 experiment config 读取要权限门
- `2253190c06` 6-04 09:01 — `chore(seeder): default ai features on in seeder (#14033)`：seeder 默认开 AI 特性
- `9c866258c5` 6-04 15:34 — `chore: Setup storybook branch deployments (#14030)`

观察：v3.179 节奏延后（v3.178 = 6-02），到 5-45 还没新 tag；`decouple blob-storage from V4 beta` 是前 GA 信号；`seeder default ai features on` 与 Phoenix v17.0 PXI 默认 enabled、Langfuse v3.176 MCP metrics 默认 enable 同样策略；治理层延续 v3.178 audit log 授权、v3.176 in-app agent API key —— 一条线："可观测 = 治理面" 的产品定位。

**选型增量建议**（在 5-06 基础上新增）：

- **强合规 / 多团队共享平台** → 评估 **Arize Phoenix v17+**。`agentTraceRecording` server-enforced ceiling + `acknowledgedTraceConsent` snapshot 是目前 OSS LLM 可观测里**唯一**能回答"我能不能保证 PII 不出域"的方案。配合 v16.2 的 token 归一化（cost 不会被父 span 重复计费）。
- **追求零插桩 / 不想改应用代码** → **eBPF 方案在 2026 上半年从 demo 跨入 production**。AgentSight (381★) + ebpf-llm-tracer (Go) + deepflow (4114★ 通用 APM) 三个项目可同时用 —— AgentSight 抓 agent 视角，ebpf-llm-tracer 抓 LLM HTTP，deepflow 兜底系统调用 / 网络。**注意**：eBPF 路径在 macOS / Windows 不可用（仅 Linux 4.18+），且需要 root / CAP_BPF。
- **跨协议追踪要求高**（MCP server / A2A / OpenAI / Anthropic / Bedrock / Ollama 全都要 trace）→ OTel GenAI semconv 独立仓已经在**协议级**对齐 MCP SEP-414 context propagation；**选型时优先用声称支持 OTel GenAI semconv 1.41+ 的 SDK**（OpenLLMetry 0.61 / OpenLIT 1.21 / Langfuse v3.176+），并确认 SDK 升级计划跟得上新独立仓的 spec-level PR。
- **可观测做治理面**：本轮 Phoenix / Langfuse / Portkey 三家齐头并进在收紧"可观测的治理维度" —— Phoenix server policy、Langfuse in-app agent key + audit、Portkey admin token default。**以后选型要把"治理能力"列为第一评估维度**。

---

## 引用与数据来源

- Arize Phoenix: <https://github.com/Arize-ai/phoenix/releases> · PR #13254（system_settings）: <https://github.com/Arize-ai/phoenix/issues/13254> · MIGRATION.md: <https://github.com/Arize-ai/phoenix/blob/main/MIGRATION.md> · v16.2 fix token counts (#13433): <https://github.com/Arize-ai/phoenix/issues/13433> · v17.1.0 release: <https://github.com/Arize-ai/phoenix/releases/tag/arize-phoenix-v17.1.0>
- eunomia-bpf/agentsight: <https://github.com/eunomia-bpf/agentsight> · commits: <https://github.com/eunomia-bpf/agentsight/commits>
- AkshantVats/ebpf-llm-tracer: <https://github.com/AkshantVats/ebpf-llm-tracer/commits>
- eunomia-bpf/MCPtrace: <https://github.com/eunomia-bpf/MCPtrace> · deepflowio/deepflow: <https://github.com/deepflowio/deepflow>
- OTel semantic-conventions-genai repo: <https://github.com/open-telemetry/semantic-conventions-genai> · PR #220 (MCP context): <https://github.com/open-telemetry/semantic-conventions-genai/pull/220> · PR #216 (span duration): <https://github.com/open-telemetry/semantic-conventions-genai/pull/216> · PR #217 (top_k split): <https://github.com/open-telemetry/semantic-conventions-genai/pull/217> · PR #219 (conversation id fallbacks): <https://github.com/open-telemetry/semantic-conventions-genai/pull/219> · PR #214 (provider.name 降级): <https://github.com/open-telemetry/semantic-conventions-genai/pull/214>
- OTel semantic-conventions PR #3696 (GenAI 拆仓): <https://github.com/open-telemetry/semantic-conventions/pull/3696>
- MCP SEP-414 (request _meta): <https://modelcontextprotocol.io/community/seps/414-request-meta>
- Langfuse commits: <https://github.com/langfuse/langfuse/commits> · PR #14032 (blob-storage): <https://github.com/langfuse/langfuse/pull/14032> · PR #14009 (datasets remote gate): <https://github.com/langfuse/langfuse/pull/14009>
- 上一篇同主题: <https://github.com/happysunxf/aigw/blob/main/hermes/reports/2026-06-05-0506-aigw-observability.md>
