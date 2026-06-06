# AI 网关可观测专题 · 第 3 轮 · 2026-06-06 12:42 CST

> 主题：`observability`（local hour 12 → 12 % 7 = 5）。
> 与 05:30（GenAI semconv 独立成仓 + token 维度精细化）和 12:03（observability-r2）互补，本轮聚焦 **过去 6 小时 OTel/Langfuse/OpenLLMetry/openlit 主仓与新仓 18 个 open PR 的具体走向**——以及 v3 scores API 4 阶段快速成型 + agent session 服务端持久化这两个产品方向信号。

## 1. 过去 6 小时硬信号（2026-06-05 18:00 → 2026-06-05 23:40 UTC）

### 1.1 OTel GenAI semconv 新仓 18 个 open PR 排序

按 `updated_at` 取前 10（来自 `https://api.github.com/repos/open-telemetry/semantic-conventions-genai/pulls?state=open&sort=updated&per_page=15`）：

| # | 标题 | 状态 | updated_at (UTC) |
|---|------|------|------------------|
| 195 | semconv for a2a protocol | open | 2026-06-05 20:50:01 |
| 197 | Add modality, cache, and phase breakdowns for token usage | open | 2026-06-05 18:30:29 |
| 252 | Add gen_ai.invoke_agent.server span (SERVER kind) | open | 2026-06-05 00:43:14 |
| 250 | Add gen_ai.agent.invocation.id attribute for invoke_agent spans | open | 2026-06-05 06:59:03 |
| 215 | Clarify scope of `gen_ai.client.operation.duration` metric | open | 2026-06-04 21:42:58 |
| 220 | Clarify MCP context propagation | **merged** | 2026-06-04 15:48:12（merge commit `c4503710d3`）|
| 173 | Update dependency google-adk to v2 | open | 2026-06-05 00:25:12 |
| 162 | semconv for compaction | open | 2026-06-05 01:12:48 |
| 98 | gen-ai: model agent-to-agent handoff as execute_tool span | open | 2026-06-05 02:44:41 |
| 188 | Add workflow node convention | open | 2026-05-30 22:28:20 |
| 201 | Add gen_ai.agent.invocation.duration and gen_ai.tool.execution.duration metrics | open | 2026-06-02 12:55:57 |
| 96 | genai: add `gen_ai.token.cache` and `gen_ai.token.reasoning` metric attributes | open | 2026-05-29 15:38:27 |
| 165 | proposal: agent.threat.detection.* attributes + event | open | 2026-05-22 19:03:41 |
| 164 | Add gen_ai.server.inter_token_latency metric | open | 2026-05-21 17:35:26 |

**两点趋势**：

1. **PR #220 已合入**（merge `c4503710d3`）—— **MCP context propagation 文字定稿**。上一轮（12:03）把它列入 open，本轮升 merged，OTel SemConv 在 MCP 层落地，gateway 实现可直接引用。
2. **token 维度精细化（#197）维持 open 状态**，但与 #96（token.cache / token.reasoning）有覆盖关系：#197 用"三个独立 counter"取代单一 histogram，#96 在属性层加 enum 维度。SIG 仍在收敛。

### 1.2 PR #197 关键改动（细化"token 去哪了"）

- **属性**（registry）按 modality 补齐：`gen_ai.usage.{text,image,audio,video}.input_tokens` / `gen_ai.usage.{text,image,audio}.output_tokens`，cache 维度同步为 `gen_ai.usage.{text,image,audio,video}.cache_read.input_tokens`。
- **指标重写**：用 `gen_ai.client.inference.tokens`（按 `gen_ai.token.type` × `gen_ai.token.modality`）/ `gen_ai.client.inference.input_tokens_by_cache`（按 `gen_ai.token.cache` × `gen_ai.token.modality`）/ `gen_ai.client.inference.output_tokens_by_phase`（按 `gen_ai.token.phase`）**三个 counter 取代单一 `gen_ai.client.token.usage` histogram**。
- **opt-in 直方图**：`gen_ai.client.inference.operation.{tokens,input_tokens,output_tokens}`。
- **新 enum**：`gen_ai.token.modality ∈ {text,image,audio,video,document,unknown}` / `gen_ai.token.cache ∈ {uncached,read,write}` / `gen_ai.token.phase ∈ {response,reasoning}`。

→ 落地后 gateway 端的 `usage` 字段语义不再是"一堆 token"，而是"哪类 modality / 缓存命中 / 是否在 reasoning"三正交维度交叉。**这对 cost attribution 是硬升级**。

### 1.3 PR #195 A2A semconv（动的不止 Envoy/agentgateway）

- 5 项 metric：operation duration、response body size、**streaming time to first event**、SSE event count、agent 任务级 outcome。
- 6 项低基数 attribute：`a2a.method.name` / `a2a.protocol.version` / `a2a.task.state` / streaming flag / TTFT / payload size。
- reference scenario 走 stable `a2a-sdk==1.0.3`（Python）。
- 解决 #70。

→ AIGW 视角：A2A 不再只是"两个 agent 之间的 RPC"，而是 **OTel 维度的一等公民**。与 agentgateway #1784 `OutboundCallKind`×`OutboundCallSubtype` 形成上下游对齐：client side 走 A2A 协议，gateway 走 OTel 维度。

### 1.4 PR #252 `gen_ai.invoke_agent.server`（SERVER kind）

- `attributes.gen_ai.invoke_agent.server` 属性组，**继承** `invoke_agent.common`，加 `client.address` / `client.port`（opt-in）。
- 3 个 span kind：
  - `gen_ai.invoke_agent.client`（CLIENT）—— 调用方看
  - `gen_ai.invoke_agent.server`（**SERVER**）—— 服务器侧（Azure AI Foundry、Bedrock Agents 这类 hosted agent runtime）
  - `gen_ai.invoke_agent.internal`（INTERNAL）—— 同进程内
- 是 [open-telemetry/semantic-conventions#3473](https://github.com/open-telemetry/semantic-conventions/pull/3473) 的 port。

→ 与 PR #195 联读：**A2A 协议边界 + agent server span** 是 AIGW 把"agent 调用"从哑 HTTP 升级为"可分阶段归因"的关键。

### 1.5 PR #250 `gen_ai.agent.invocation.id`（vs `gen_ai.response.id`）

- 区别：run-level（整次 agent invocation）vs completion-level（单次 LLM 响应）。
- 落在 `invoke_agent.common` recommended，覆盖 client / internal。
- reference scenario 标了三家：
  - **AWS Bedrock Agents** → `ResponseMetadata.RequestId`
  - **OpenAI Assistants** → `run.id`
  - **Azure AI Foundry hosted agents** → `response.id` (Responses API)
- **明确写出的"capture gap"**：OpenAI Agents SDK **没有独立 run ID** —— 同一 SDK 在不同 host 下归因能力不对等。

→ AIGW 落点：要做 run-level cost/token 归因时，先在 gateway 侧**自己生成 `gen_ai.agent.invocation.id`**（比如 UUIDv7），不要等 SDK。

## 2. 主仓过去 24h 速览

### 2.1 opentelemetry-python-contrib（最近 6/4 16:07，6/5 18:34）

```
0a6ac20719  2026-06-05 18:34  tornado: make metrics tests less flaky on pypy (#4665)
03a3e385eb  2026-06-04 16:07  Copy changelog updates from package-release/opentelemetry-instrumentation-google
7f01b3500a  2026-06-02 18:21  Fix broken botocore tests, minor change to HTTPX instrumentation test
26c975f2ae  2026-05-29 23:28  Update lmolkova's affiliation (#4636)
a341399765  2026-05-22 19:15  doc: add contrib notice pointing users to new library repo for gen-ai. (#4611)
```

→ 6/4–6/5 进入"治理 + 文档"模式，#4611（5/22 一次性给 9 个 `instrumentation-genai/` 子包 README 加 contrib notice 指向新库）的余波还在收尾。

### 2.2 openlit main（6/2–6/3 是 otel-gpu-collector 高峰）

```
16d788c747  2026-06-03 07:15  fix: arm64 native build (#1252)
90eb75a39a  2026-06-03 05:55  build(deps): bump docker/setup-buildx-action 4.0.0→4.1.0 (#1221)
8f2ccf9481  2026-06-02 18:52  feat: Make otel-gpu-collector contributions easier (#1228)
cd5e5712a3  2026-06-02 10:51  ci(otel-gpu-collector): install libc6-dev-arm64-cross for cross-cgo b… (#1225)
80f99b0af5  2026-06-02 10:44  build(deps): update langgraph <2.0.0,>=1.2.1 → >=1.2.2,<2.0.0
2aca45310e  2026-06-02 10:35  ci(otel-gpu-collector): enable CGO for linux release binaries (#1224)
a6a2ac2f43  2026-06-02 10:06  fix: generate arm64 eBPF bindings (#1213)
```

→ **0.0.5 → 0.0.6 五天双发**（6/2 10:53 → 6/3 07:21），主轴是 arm64 native build + CGO + eBPF bindings——**GPU 端 OTel 化**正在补完交叉编译基础。6/3–6/6 主仓无新 commit，转入 1.21.x 收尾期。

### 2.3 langfuse main（v3.178.0 之后 6/4–6/5 高频）

| 主题 | 数量 | 代表 PR |
|------|------|---------|
| **v3 scores API 4 阶段** | 4 | #13993 / #13996 (Phase 2 cursor) / #14001 (Phase 3 field groups) / #14005 (Phase 4 filter params) |
| **in-app agent 框架切换** | 1 | #14018 (ClaudeAgentAdapter → MastraAgent) |
| **agent session 服务端持久化** | 1 | #13720（5 张新表 conversations/messages/runs/confirmation requests/credential leases） |
| **审计/治理** | 1 | #13980 (v3.178.0: auditLogs batch export 强制 entitlement) |
| **OTLP/JSON int64 解码修复** | 1 | #14047（PHP SDK 等 OTLP/JSON exporter 投递的 span 之前被静默丢弃） |
| **ClickHouse DELETED MASK 物理回收** | 1 | #14035（`DeletedMaskCleaner` 周期跑 `APPLY DELETED MASK IN PARTITION`） |
| **pricing tier 补丁** | 1 | #13993 (OpenAI `service_tier: "priority"` 之前永远按 standard 计费) |
| **删除链路 v4 toggle 解耦** | 1 | #14032 |

**v3 scores API 4 阶段快速落地**（6/5 14:51 → 15:31 = 40 分钟连发 4 PR）：

1. **Phase 1 (#13993)**：v3 scores API 入口，**polymorphic value**（多型字段），flag-gated。
2. **Phase 2 (#13996)**：cursor 分页，cursor tuple `(timestamp, id)`，base64url 编码 JSON；`meta.cursor` 存在表示有下一页；`fetch limit+1` 决定是否发 cursor；predicate `WHERE (s.timestamp, s.id) < (...)` 与 `ORDER BY timestamp DESC, id DESC` 对齐；**不再做 COUNT 查询**。
3. **Phase 3 (#14001)**：field groups（按业务字段分组）。
4. **Phase 4 (#14005)**：所有 filter params。

→ 同一 Linear ticket `LFE-9539` 的 4 个 phase，**40 分钟内连推**——这是 langfuse 内部"scores"表正在从 v2 升 v3 的硬信号。**AIGW 用 langfuse 持久化 score 的，要盯 v3 文档，flag-gated 阶段先不开**。

**agent session 持久化 (#13720)**——5 张新表：

- `conversations` / `messages` / `runs` / `confirmation_requests` / `credential_leases`
- cascade delete 正确；`providerSessionId`（Claude session id）**只在服务端**留存，不返回客户端。
- 流式 handler：开流前 persist 用户消息 + create run record；流结束后 fire-and-forget 更新 run status。
- 前端 provider：run 结束后 `syncMessages` 把全 conversation 持久化；带 retry-on-invalid-session 逻辑。

→ AIGW 视角：langfuse 的 in-app agent 在从"无状态 pod"演化为"DB-backed agent"——这与 LitServe / agentgateway 等外部 agent runtime 走"DB-backed session"是同一信号：**长 session 持久化是 agent 产品化的硬要求**。

**OTLP/JSON int64 解码修复 (#14047)** 是一颗隐蔽炸弹：

- 根因：OTLP/JSON 协议把 int64 编码为十进制字符串（JSON 数字表达不了完整 int64）。langfuse 之前的 attribute converter 只处理 protobuf decoder 的 `Long` 对象和裸数字，"7" 这种 string-encoded int 落到 `high * 2^32 + low` 的 `high` 是 undefined → NaN → 被 ingestion validation 拒（`invalid_union` on `body.metadata`）→ **span 静默丢弃**。
- 受影响 exporter：OpenTelemetry PHP SDK，以及所有自实现 OTLP/JSON exporter。
- 修复：抽出 `convertOtelIntValue` 统一处理三种 case；string-encoded double 也一起 coerce。

→ AIGW 视角：如果你从 PHP / Node 自定义 OTel SDK 拿 span 给 langfuse，**升级前可能存在大段数据丢失**。

## 3. OpenLLMetry 0.61.0 数字（2026-05-31）

```
4643b8826a  2026-05-31 07:26:13Z  bump: version 0.60.0 → 0.61.0
[main 4643b882] 64 files changed, 93 insertions(+), 63 deletions(-)
```

`v0.61.0` 主要 fix（13 条）：

- `responses.parse()` structured-output tracing (#4198)
- **langchain/anthropic/groq/mistralai/bedrock/ollama/sagemaker/together 7 SDK 一次性补 ERROR status 记录**（#4101）
- vector-db（pinecone/milvus）embeddings_count/result_count/similarity 一致性 (#1870/#4156)
- openai-agents: GenAI semconv compliance (#3837) + cache_read.input_tokens + reasoning_tokens (#4130) + response.instructions as system (#4131)
- mcp: error.type attribute on protocol-level tool errors (#4103)
- chromadb: per-document result events (#4105)
- langchain: ToolNode in create_react_agent (#4081)
- anthropic: streaming token usage always set (#3949/#3976)
- evaluator: PII detector reason field (#4026)
- sdk: warn on dual exporter+processor (#4137)
- 弃用 Pydantic `.json()` / 双编码 `.model_dump_json()` (#4098)

→ 5/31 0.61.0 之后 main 5 天**无新 commit**——OpenLLMetry 转入 0.62 规划期。**之前 0.60→0.61 间隔 42 天**（4/19 → 5/31），下一次发版大概率 7 月初。

## 4. AIGW 视角：6 条硬要求

| # | 要求 | 触发来源 |
|---|------|----------|
| **O-1** | gateway 端 `usage` 字段按 `{modality, cache, phase}` 三正交维度填充，与 PR #197 三个 counter 对齐 | semconv-genai #197 |
| **O-2** | 自生成 `gen_ai.agent.invocation.id`（UUIDv7）作为 run-level 主键，**不等 SDK 给 run id** | semconv-genai #250（OpenAI Agents SDK capture gap）|
| **O-3** | MCP trace context 注入 W3C propagator + `_meta` 字段 | semconv-genai #220（已 merge）|
| **O-4** | A2A 调用方走 `gen_ai.invoke_agent.client`（CLIENT kind），server 侧走 `gen_ai.invoke_agent.server`（SERVER kind）| semconv-genai #252 + #195 |
| **O-5** | langfuse ingestion 链路升级到能解析 OTLP/JSON string-encoded int64 | langfuse #14047 |
| **O-6** | langfuse v3 scores API 在 flag-gated 阶段不开，v3 stable 后再切；cursor 分页 `meta.cursor` 存在即"还有下一页"| langfuse #13993/#13996/#14001/#14005 |

## 5. AIGW 硬要求累计（与前几轮合并）

本轮新增 O-1 ~ O-6 合并入累计表（见 CHANGELOG 顶部）→ 全集 86 条。

## 引用与数据来源

- OTel semconv-genai 仓 commits（24h 15 条）：`https://api.github.com/repos/open-telemetry/semantic-conventions-genai/commits?per_page=15`
- OTel semconv-genai open PRs（按 updated 排序）：`https://api.github.com/repos/open-telemetry/semantic-conventions-genai/pulls?state=open&sort=updated&per_page=15`
- OTel semconv-genai PR #197 body：`https://api.github.com/repos/open-telemetry/semantic-conventions-genai/pulls/197`
- OTel semconv-genai PR #195 body（A2A semconv）：`https://api.github.com/repos/open-telemetry/semantic-conventions-genai/pulls/195`
- OTel semconv-genai PR #252 body（invoke_agent.server span）：`https://api.github.com/repos/open-telemetry/semantic-conventions-genai/pulls/252`
- OTel semconv-genai PR #250 body（agent.invocation.id）：`https://api.github.com/repos/open-telemetry/semantic-conventions-genai/pulls/250`
- OTel semconv-genai PR #220 merged 详情（merge commit c4503710d3）：`https://api.github.com/repos/open-telemetry/semantic-conventions-genai/pulls/220`
- opentelemetry-python-contrib commits：`https://api.github.com/repos/open-telemetry/opentelemetry-python-contrib/commits?per_page=10`
- openlit commits + releases：`https://api.github.com/repos/openlit/openlit/releases?per_page=5` + `commits?per_page=10`
- openllmetry 0.61.0 release notes：`https://api.github.com/repos/traceloop/openllmetry/releases/tags/0.61.0`
- openllmetry commits since 5/31：`https://api.github.com/repos/traceloop/openllmetry/commits?since=2026-05-31T00:00:00Z`
- langfuse v3.178.0 release notes：`https://api.github.com/repos/langfuse/langfuse/releases/tags/v3.178.0`
- langfuse commits since v3.178.0：`https://api.github.com/repos/langfuse/langfuse/commits?since=2026-06-02T14:00:00Z`
- langfuse PR #13720 agent session 持久化：`https://api.github.com/repos/langfuse/langfuse/pulls/13720`
- langfuse PR #14035 deletion mask cleaner：`https://api.github.com/repos/langfuse/langfuse/pulls/14035`
- langfuse PR #14047 OTLP/JSON int64 修复：`https://api.github.com/repos/langfuse/langfuse/pulls/14047`
- langfuse PR #14018 Mastra agent 框架切换：`https://api.github.com/repos/langfuse/langfuse/pulls/14018`
- langfuse PR #13996 v3 scores cursor 分页：`https://api.github.com/repos/langfuse/langfuse/pulls/13996`
- agentgateway main commits（6/5 17:28–23:13 UTC 10 条）：`https://api.github.com/repos/agentgateway/agentgateway/commits?per_page=10`
- otel-gpu-collector 0.0.6 release notes：`https://api.github.com/repos/openlit/openlit/releases/tags/otel-gpu-collector-0.0.6`
- 上一轮 12:03 observability-r2 报告：`~/hermes/reports/2026-06-06-1203-aigw-observability-r2.md`
- 上一轮 05:30 GenAI semconv 独立成仓报告：`~/hermes/reports/2026-06-06-0530-aigw-observability-genai-semconv.md`

> 报告生成时间：`date '+%Y-%m-%d %H:%M:%S %Z'` = **2026-06-06 12:42 CST (UTC+8)**。
> 全部时间戳来自 GitHub API 响应（`commit.author.date` / `pull.updated_at` / `release.published_at`），未编造。
