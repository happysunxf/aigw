# AI 网关持续深挖 · 第 12 次 — 可观测/监控（OTel GenAI 归一化落地 + 行业整合潮）

- 报告时间（本地 CST）：2026-06-05 12:38
- 轮换主题：5/12 → 可观测 & 监控（OpenTelemetry、cost attribution、token metrics）
- 编排：本轮是「产业格局」视角，与 05:13/05:45 两次技术视角（OTel semconv、eBPF、Server policy）形成互补

## TL;DR

1. **OTel Collector Contrib v0.153.0（5-26）正式落地 `processor/gen_ai_normalizer`**——把 OpenInference（Phoenix/Arize）与 OpenLLMetry（Traceloop）两套历史事实标准的属性归一化到 OTel 官方 GenAI semconv。这是从「vendor lock-in 的 trace schema」走向「统一语义」的关键一公里。
2. **OpenInference python-instrumentation v0.1.53（6-02）原生支持 OTel GenAI `plan` 操作**——`Agent.tool/agent` 计划步骤不再只走私有 span type。
3. **OpenInference openai-agents v1.6.0（6-03）加 Realtime Audio tracing**——WS 流式语音多模态首次进入 OpenInference 矩阵。
4. **Arize Phoenix v17.0.0 → v17.2.0（6-02~6-03）三连发**——`PXI` 内嵌助手 + 沙箱白名单 + Server 端 trace recording policy（继 05:13 报）。
5. **OpenLIT 1.21.0（5-27）`offline evals` 取代 LLM based evals** + telemetry trace detail 翻新 + 「Close the loop」AI 分析。
6. **OpenLIT otel-gpu-collector 0.0.5/0.0.6（6-02/6-03）** + `agent threat event helper` —— GPU 利用率与 agent 威胁事件两条新的 OTel 信号通路。
7. **行业整合**：**Traceloop 2026-03-02 公告加入 ServiceNow**（并入 AI Control Tower）；**Helicone 2026-03-03 公告加入 Mintlify**（服务进入 maintenance 模式）。两家代表性 LLM observability 公司 24 小时内先后被吃——市场从「工具碎片」转入「平台整合」。
8. **Langfuse v3.178.0（6-02）`auditLogs:read` 强制 + v4 仪表盘 import/export**——审计能力与可移植性同时增强。

## 1. 头条：OTel Collector `gen_ai_normalizer`——两大事实标准的归一化

opentelemetry-collector-contrib **v0.153.0**（2026-05-26）CHANGELOG 首次出现一个值得圈点的 processor：

```
processor/gen_ai_normalizer: Add a processor that normalizes GenAI telemetry
attributes from OpenInference and OpenLLMetry to the official OTel GenAI
Semantic Conventions. (#46069)
processor/gen_ai_normalizer: Add the `openllmetry` source. (#46069)
processor/gen_ai_normalizer: Implement attribute/value normalization for
the OpenInference source. (#46069)
```

这意味着 2 件事：

- **历史数据可继承**：已经在用 Phoenix/Traceloop 的应用，不需要重写 instrumentation 就能把 span 映射到 `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` / `gen_ai.request.model` 等官方属性。
- **下游工具可联邦**：用 OpenInference 采集、OpenLLMetry 采集、OpenLit 采集的数据，进入同一个 collector pipeline 后都能被 Langfuse/Datadog/Honeycomb 当作「同一份数据」消费，跨厂商 trace 关联成本骤降。

之前 05:13 的报告里把「OTel semconv 对齐」列为「进行中」状态，这是它的工程化落点。

## 2. OpenInference 三连发：core GenAI `plan` + Agents 实时语音 + Bedrock 1.6

| 包 | 版本 | 发布日 | 重点 |
| --- | --- | --- | --- |
| `instrumentation-openai-agents` | 1.6.0 | 6-03 | Realtime audio tracing（WS 双向音频流） |
| `instrumentation-bedrock` | 0.1.41 | 6-03 | Bedrock 路径维护 |
| `instrumentation` (core) | 0.1.53 | 6-02 | **OTel GenAI `plan` operation** 支持 |
| `instrumentation-openai` | 0.1.50 | 6-02 | OpenAI provider 增量 |
| `instrumentation-crewai` | 1.1.9 | 6-02 | CrewAI 修复 |
| `instrumentation-anthropic` | 1.0.6 | 6-02 | Anthropic 修复 |

`plan` operation 对应 `gen_ai.operation.name = plan`（semconv 草案的 agent 编排族）。Realtime audio 是 1.6 的杀手锏——之前的 OpenAI Agents SDK 多模态 trace 只能拿到「请求/响应」配对，WS 帧级 trace 一直是盲区。1.6.0 把这种 session-level 流作为独立 span 类型暴露给 OTLP，能直接看到「用户说话→VAD→TTS 回流」每一帧的 latency。

## 3. Arize Phoenix v17：Server 端 trace 政策 + PXI 助手进入工具化

延续 05:13 报的「Server 端 trace recording policy」主线，v17.0.0 / v17.1.0 / v17.2.0 在 6-02 ~ 6-03 两天内连发三个版本：

- **v17.0.0**：正式引入 `PXI`（Phoenix eXperience Intelligence）——「trace → prompt 迭代 → 现场导航」三合一的内嵌助手；可用 `PHOENIX_DISABLE_AGENT_ASSISTANT=true` 关闭。
- **v17.1.0**：PXI `load_dataset` 工具。
- **v17.2.0**：`PXI` route info tool；assistant 聊天历史 scope 限定到 deployment root path（多租户隔离修复）；prompt 表自动刷新。

观察：**PXI 是 v16 的 sandbox/code-evaluator 权限表延续**——上一轮 05:13 报告里 `PHOENIX_ALLOWED_SANDBOX_PROVIDERS` 是「写什么能跑」，这一轮 `PHOENIX_DISABLE_AGENT_ASSISTANT` 是「写什么不能跑」。

## 4. OpenLIT：Offline evals 替代 LLM-based evals + GPU/agent 威胁事件

`openlit-1.21.0`（5-27）几个特征非常值得关注：

- **Offline evals**（PR #1185）—— 移除 LLM-based evals，全部改成可在本地跑的离线评估器。这是**对 observability 工具"二次烧 token"的反思**——大多数平台都把 eval 跑成又一个 LLM 调用，每次回看历史 trace 都额外花钱。Offline 版通常基于 N-gram/Rouge/正则/规则代码评估器。
- **Telemetry trace detail sheet 翻新**（PR #1200）—— 全面重做 span detail UI。
- **Close the loop with AI analysis**（PR #1202）—— 在 trace 详情页里直接出 AI 分析与 prompt 改进建议（注意：与 Phoenix PXI 的产品定位非常相似）。
- **Remote agent lifecycle**（PR #1192）—— 不只观测本地 agent，可以观测远端部署的 agent。

`openlit-1.21.1`（5-28）chore：新增 "ai" 与 "otter" 事件（Otter 是 OpenLIT 自家 agent 调试器名）。

**`otel-gpu-collector` 0.0.5（6-02） / 0.0.6（6-03）**：与 `agent threat event helper`（PR #1204）同步上线——把 GPU 利用率（DCGM/NVML）+ agent 威胁事件（prompt injection attempts / jailbreak events）作为新 OTLP signal type。0.0.6 额外修了一个 arm64 native build 的 issue（PR #1252），意味着这个 collector 可以跑在 Apple Silicon/ARM 边缘。

`ts-1.13.0`（5-08）+ `py-1.42.0`（5-08）则新增 **Cursor SDK Instrumentation** + **DigitalOcean Inference Instrumentation**。

## 5. Langfuse v3.178.0：审计权限收紧 + v4 仪表盘 import/export

`v3.178.0`（6-02）CHANGELOG 的可观测/合规关键项：

- **Security fix**：强制 `auditLogs:read` 与 audit-logs entitlement 用于 batch exports（PR #13980）——批量导出审计日志之前是「任何持有 project token 的人都能跑」，现在必须显式 entitlement。
- **In-app agent 接入 Langfuse MCP**（PR #13747）—— Langfuse 自己也成了 MCP server，第三方 agent 可以把「查询 Langfuse 仪表盘」当作工具调用。
- **`upsertDataset` 可选 id**（PR #13946）—— 让 dataset 同步幂等。
- **v4 trace 表**继续打磨：`comments` 改从 events 表读（PR #13473）——comment 和 trace event 一张表，join 简单但要求 events 表容量。

Dashboard import/export widget configs（v3.176.0, 5-28）+ observation type filter（v3.175.0, 5-21）这两条加起来是「仪表盘可移植」——迁移出 Langfuse 时不再有 lock-in 焦虑。

## 6. 行业整合潮：Traceloop → ServiceNow、Helicone → Mintlify

这一段是本轮与既往技术视角报告最大差异点。

### 6.1 Traceloop 加入 ServiceNow

Traceloop（OpenLLMetry 商业方）官方博客 *Traceloop is joining ServiceNow* 页面（站点 `Last Published: Mon Mar 02 2026 19:15:24 GMT+0000`）明确写到：

> "Today, I'm excited to share that Traceloop is joining ServiceNow, where our technology will become part of ServiceNow's AI Control Tower."

技术栈整合路径：

- OpenLLMetry（开源 OTel instrumentation）作为 OTel GenAI 采集层，被 ServiceNow AI Control Tower 纳入企业 AI 治理栈。
- 商业 Traceloop 平台的 trace/eval/drift/experiments 能力并入 ServiceNow Now Assist 与 AI Control Tower。
- 创始团队（CEO Nir Gazli + CTO Gal Kleinman）整体并入 ServiceNow。

对 OTel 生态的意义：**OpenLLMetry 的 OTel GenAI 属性映射成了 ServiceNow 商业产品的内部能力**——这是大厂首次明确"全栈采用 OTel GenAI semconv 作为企业 AI 治理的统一接口"，对 v0.153.0 collector `gen_ai_normalizer` 是重大利好。

### 6.2 Helicone 加入 Mintlify

Helicone 官方博客 *Helicone is joining Mintlify*（2026-03-03 · Cole Gottdank）：

> "Helicone has been acquired by Mintlify... Helicone's services will remain live for the foreseeable future in maintenance mode. Security updates, new models, bug & performance fixes all keep shipping."

**Helicone 的"开源 LLM observability + AI Gateway"路线被 Mintlify（文档/开发者门户厂商）并入，进入 maintenance 模式**。评估/dataset/prompt 等能力不会再有大动作。

## 7. OpenTelemetry Collector v0.153.0 同版本其他值得提的项

- `processor/tail_sampling` 的 `rate_limiting` 策略改为**令牌桶** + 新增 `burst_capacity` 字段——AI 网关 trace 量爆发时允许短时尖峰，常规期稳定采样。
- `event_driven_scraping`（影响 Prometheus receiver 的 scrape 模式）—— 减少空转。

## 8. 5 条可直接落地的清单

1. **OTel Collector 升到 v0.153.0+** + 启用 `processor/gen_ai_normalizer`，将 Phoenix / OpenLLMetry / OpenLIT / OpenInference 的 trace 一并归一化。
2. **OpenInference 升级**：openai-agents 升 1.6+ 拿 Realtime audio；core 升 0.1.53+ 拿 `plan` operation；Bedrock 路径 0.1.41+。
3. **Phoenix v17+** 自托管部署必须设 `PHOENIX_DISABLE_AGENT_ASSISTANT` 与 `PHOENIX_ALLOWED_SANDBOX_PROVIDERS`，避免 PXI 误开与不受限的 sandbox 跳板。
4. **OpenLIT 1.21+ 替换 eval pipeline**——offline evals 不再吃 LLM 预算，把评估降级为「OTel span 上的本地计算」。
5. **重新评估 observability 选型**——Traceloop 已并入 ServiceNow，Helicone 进入 maintenance；想保留开源路径，**OpenLIT / Langfuse / Phoenix 三选一**。

## 引用与数据来源

- OpenTelemetry Collector Contrib v0.153.0 release notes — https://github.com/open-telemetry/opentelemetry-collector-contrib/releases/tag/v0.153.0
- OpenInference core v0.1.53 — https://github.com/Arize-ai/openinference/releases/tag/python-openinference-instrumentation-v0.1.53
- OpenInference openai-agents v1.6.0 — https://github.com/Arize-ai/openinference/releases/tag/python-openinference-instrumentation-openai-agents-v1.6.0
- OpenInference bedrock v0.1.41 — https://github.com/Arize-ai/openinference/releases/tag/python-openinference-instrumentation-bedrock-v0.1.41
- Arize Phoenix v17.0.0 / v17.1.0 / v17.2.0 — https://github.com/Arize-ai/phoenix/releases
- Phoenix MIGRATION.md（v16→v17 PXI、v15→v16 sandbox allowlist） — https://github.com/Arize-ai/phoenix/blob/arize-phoenix-v17.0.0/MIGRATION.md
- OpenLIT 1.21.0 — https://github.com/openlit/openlit/releases/tag/openlit-1.21.0
- OpenLIT 1.21.1 — https://github.com/openlit/openlit/releases/tag/openlit-1.21.1
- OpenLIT otel-gpu-collector 0.0.6 — https://github.com/openlit/openlit/releases/tag/otel-gpu-collector-0.0.6
- OpenLIT otel-gpu-collector 0.0.5 — https://github.com/openlit/openlit/releases/tag/otel-gpu-collector-0.0.5
- Langfuse v3.178.0 — https://github.com/langfuse/langfuse/releases/tag/v3.178.0
- Traceloop is joining ServiceNow — https://traceloop.com/blog/traceloop-is-joining-servicenow
- Helicone is joining Mintlify — https://www.helicone.ai/blog/joining-mintlify
- OpenLIT OpenLLMetry 协同（背景） — https://github.com/traceloop/openllmetry-js/releases
