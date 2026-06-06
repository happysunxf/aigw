# AI 网关持续深挖 · Agent Gateway 专题 · 第 20 期

> 抓取时间：2026-06-06 09:25 CST（周六）· 主题：multi-agent 编排、trace 调试、成本归因
> 本期口径：紧盯 `agentgateway/agentgateway`、`envoyproxy/ai-gateway`、`kubernetes-sigs/gateway-api-inference-extension`、`langchain-ai/langgraph`、`crewAIInc/crewAI` 五个仓库近 30 天的 commit/release，特别关注 (a) multi-agent session 关联、(b) trace/span 编排、(c) thinking token 成本归因。

## TL;DR

- **agentgateway/agentgateway v1.3.0-alpha.1**（2026-05-23）落地后 14 天内又合入 14+ 个 PR，重点是 A2A 后端类型、MCP subscribe/unsubscribe、CORS/TLS、`agctl` CLI 重构、`dtrace` 引入 body snapshot 与 JSON 格式输出 —— 多 agent 调试能力在快速补齐。
- **envoyproxy/ai-gateway v0.6.0**（2026-05-05）正式把核心 CRD 提到 `v1beta1`（"production-ready"），并把 `agent-session-id → session.id` 当成默认 OTel span/log 关联键、引入 `LLMRequestCostType.ReasoningToken`、暴露 resolved upstream model 元数据 —— 直接把"多 agent 会话成本归因"和"上游模型可观测"变成 first-class 能力。
- **langgraph 1.2.4**（2026-06-02）是个补丁版本：保证 `_on_started` 在带 `cause` 的新链路里与历史 override 兼容，配合 1.2.x 的 factory-graph server 路径，是多 agent 服务化部署的稳态补丁。
- **crewAI 1.14.6**（2026-05-28）+ 1.14.7a1/a2（06-03/06-05）把 **Agent Control Plane (ACP, Beta)** 文档化，结构化输出泄漏 / checkpoint 字段序列化 / `AgentExecutor` 从 checkpoint 恢复 等问题逐项打补丁 —— ACP 的"控制平面"概念在生态里开始与 gateway 角色竞争。
- **GAIE v1.5.0**（2026-04-19）让 EPP/BBR 插件接口完成"可插拔 + 框架化"，flow control 文档化，并官方推荐 quickstart 改用 agentgateway —— 说明社区共识正在向 "agent gateway = data plane + inference extension EPP" 收敛。

下面按"主题切片"展开，每个切片都对应一个 multi-agent 工程化痛点。

## 切片 1 · Session 关联：跨 LLM/MCP 调用的同一会话怎么串起来

- agentgateway 在 v1.3.0-alpha.1 已经把 `request_id` 和 `connection_id` 放进 access log 字段（PR #1849），方便用 OTel log 关联同一次 user turn。
- envoy-ai-gateway v0.6.0 直接做"协议层"映射：客户端发 `agent-session-id` 头 → 网关把它映射成 OTel 的 `session.id` span/log 属性（可通过 `OTEL_AIGW_REQUEST_HEADER_ATTRIBUTES` 覆盖/关闭）。这样 Goose 这类 agent 框架零配置就能拿到 session 关联，metrics 默认不挂 session.id（防高基数爆炸）。
- agentgateway 还在 PR #2097 修了 `mcp-session-id` 的 CORS 头转发，让多步 agent 里的 MCP 订阅会话能跨 origin 复现。
- **落地建议**：当你前面跑 Goose / LangGraph / CrewAI 这类多 agent 客户端，给所有出站请求注入 `agent-session-id: <uuid>`，让网关在 trace/log 里自动把同一 session 的所有 LLM、MCP、A2A 调用串起来；这是 v0.6 / v1.3 这条线最值得开启的开关。

## 切片 2 · Trace 调试：能看到 LLM 请求体里的 thinking/tool_call 吗

- agentgateway PR #1887 `dtrace: include bodysnapshots at various points in the request` —— 在请求生命周期的多个点（认证后、翻译前、出站前）抓 body snapshot，配合既有的 dtrace 框架可做"重放式"调试，是 multi-agent 调试痛点（"我明明发对了 tool schema，为什么远端说 invalid"）的强解药。
- agentgateway v1.3.0-alpha.1 还合入：
  - `anthropic: do not swallow non-json errors`（#1878）—— Claude 出错时保留原始 body，agent 调试能看见真实错误。
  - `dtrace: add json format mod` —— dtrace 导出支持 JSON，SIEM/ELK 直接 ingest。
- envoy-ai-gateway v0.6.0 的 `Response.model` 元数据：路由使用 alias 或 fallback 时，回包里能直接读到"这次请求实际打到哪个 model"，配合 OTel 的 `gen_ai.response.model` 属性能在 Langfuse / Arize 里按真实模型切片。
- 同步把"上下文被截断"的隐性问题解决：v0.6 移除了 OTEL span 属性数量上限，长上下文请求不再被静默丢弃 trace 字段。

## 切片 3 · 成本归因：thinking token / cache token / reasoning_effort

这是本期最值得展开的"运营视角"更新：

- `LLMRequestCostType.ReasoningToken`（envoy-ai-gateway v0.6 新增）：把 thinking token 从 input/output/cache 之外单独立一档，cost dashboard 可以按"思考开销"做独立预算与告警。对跑 Claude 4.6 adaptive thinking、o-series high reasoning 的 agent 来说终于能讲清楚"思考到底花了多少钱"。
- `GatewayConfig.spec.globalLLMRequestCosts` + `AIGatewayRoute.spec.llmRequestCosts`：fleet-wide 默认 + per-route 覆盖，per-tenant 成本追踪不再需要"每条路由手抄一份"。
- `Response.model` + 自带 `cache_creation_input_tokens`（agentgateway PR #1993）—— 修复了"非流式响应里 cache_creation_input_tokens 没填"这个 long-standing bug，从此在 Anthropic 路径下做 cache 写入计费有可靠信号。
- `reasoning_effort` 跨厂商统一：v0.6 把 OpenAI 风格的 `low/medium/high/xhigh` 同时映射到 Anthropic thinking budget 和 Gemini 3 thinking 控制，客户端一个 knob 切三厂，对做"按任务难度动态调整思考强度"的 multi-agent 路由很关键。
- GAIE v1.5.0 同步在 latency predictor 训练目标里加入 mean objective + sliding window，TPOT 训练精度提升 —— 成本模型依赖的"per-token 延迟基线"会更准。

## 切片 4 · A2A 与 MCP 协议合规：多 agent 互操作的协议层

- agentgateway PR #1841 `a2a: add first class a2a backend type in AGBE` —— AGBE（Agent Gateway Backend Extension）正式把 A2A 作为一等 backend 类型，而不是只把它当普通 HTTP route。配合 PR #2100 `mcp: support resource subscribe`，MCP 资源订阅/退订也被原生支持。
- 进一步协议合规补丁：PR #1874 `mcp: misc protocol compliance enhancements`、PR #1857 `mcp: support sub/unsub from resource (no multiplex)`，解决了资源订阅在多 backend 多路复用时的歧义。
- envoy-ai-gateway v0.6.0 的 `MCPRoute` 同样增强：`forwardHeaders`（per-backend header forward + rename）、`MCPRouteOAuth.claimToHeaders`（JWT claim 透出到 MCP 后端）、`MCPToolFilter.exclude/excludeRegex`、动态 metadata 里带 `mcp_tool_name`、per-backend capability tracking —— 多 agent 通过不同 MCP backend 拼装工具时，可以精细控制每个 backend 看到什么头、能调什么工具。
- **横向对比**：agentgateway 把 A2A 当 backend、envoy-ai-gateway 把 MCP 当 first-class route、kubernetes-sigs/GAIE 收敛 EPP/BBR 插件框架 —— 三个项目的"网关协议边界"在 v1.3/v0.6/v1.5 时间点形成清晰分工：data plane（agentgateway/envoy-ai-gateway）+ 智能选端插件层（GAIE）。

## 切片 5 · Agent Control Plane 来了：谁能当 multi-agent 的"控制面"

crewAI 在 1.14.6 文档里新增 **Agent Control Plane (ACP, Beta)** 导航与 `Agent Control Plane docs`，并把 `Skills Repository` 移到 `experimental` 后面、要求 `CREWAI_EXPERIMENTAL` 环境变量门控。这条路径与"AI 网关"在产品定位上开始竞争/互补：

- 网关偏向**流量 + 安全 + 协议 + 可观测**；
- ACP 偏向**多 agent 任务编排 + checkpoint + 工具仓库**。
- 工程上正确的做法是让 agent runtime（LangGraph / CrewAI / AutoGen）暴露 ACP 接口，让 gateway 透传并加计费/审计/限流；agentgateway 这次把 A2A 当 backend，已经有"让 control plane 接到 gateway 后端"的设计意图。
- checkpoint 这块 crewAI 1.14.6 修了"结构化输出泄漏到 tool-calling 循环"和"`type[BaseModel]` 字段不能 round-trip"两个长期痛点，LangGraph 1.2.4 修了 `_on_started` 在带 `cause` 的新链路里与历史 override 的兼容性 —— 两边都在做"长会话可恢复 + 可重放"。

## 切片 6 · 可观测 & 部署稳态

- envoy-ai-gateway v0.6.0：standalone `aigw` 启动失败终于会干净报错（不再"挂着等"或 trace 乱飞），OTLP access logging 在 `OTEL_EXPORTER_OTLP_ENDPOINT` 设置后自动开启。Lua filter slot 放在 AI ExtProc 之后 → 不写 `EnvoyExtensionPolicy` 也能做"最后一公里"header/body 微调。
- agentgateway：v1.3.0-alpha.1 的 `agctl` CLI 在 PR #2098 里重组，新增 `agctl p` 命名空间 + proxy/controller log 子命令，本地多进程调试更顺手；PR #2061 `feat(metrics): Configuration synchronisation metric` 把"我当前生效的配置 vs 期望配置"差异做成可观察指标，operator dashboard 能直接看到"配置漂移"。
- 安全：v0.6 引入请求/响应 body 脱敏（合规），hardened bearer token 解析不再 panic MCP subject extractor；agentgateway PR #2105 `simple llm: allow serving over TLS`，本地 LLM 直连也可以走 TLS。
- 跨云身份：v0.6 的 GKE Workload Identity via ADC —— 不再需要把 GCP service account JSON 当 Secret 灌进集群。

## 给工程团队的行动项

1. **启用 session 关联**：在所有 agent 客户端注入 `agent-session-id` 头（envoy-ai-gateway 0.6+ / agentgateway 1.3+ 均支持），把多步 multi-agent 调用在 trace 里串成一根线。
2. **拆分 thinking token 成本**：把 `LLMRequestCostType.ReasoningToken` 加进你们的 cost 看板（envoy-ai-gateway 0.6+），给"思考开销"单独设告警阈值；同步把 cache 写入 (`cache_creation_input_tokens`) 信号接入计费系统（agentgateway 已修 #1993）。
3. **跨厂商 reasoning_effort 标准化**：用 OpenAI 风格的 `reasoning_effort` 做"任务难度 → 思考强度"统一旋钮，跨 Anthropic/OpenAI/Gateway 三个目标都能映射（envoy-ai-gateway 0.6）。
4. **协议层分工落地**：A2A / MCP 资源订阅 / 工具白名单 走 gateway 协议原语，不要在 agent runtime 里硬塞；agentgateway 的 AGBE A2A backend、envoy-ai-gateway 的 MCPRoute forwardHeaders/excludeRegex 是当前最干净的承载点。
5. **关注 ACP vs 网关边界**：crewAI Agent Control Plane 走 beta 阶段，先观察再接入；不要把 control plane 职责（checkpoint、技能仓库）塞进网关，反过来也不要把网关职责（限流、鉴权、可观测）塞进 agent runtime。
6. **开启 body snapshot 调试**：在 staging 环境把 agentgateway 的 dtrace body snapshot 打开，保留最近若干请求的 body snapshot；multi-agent 调试时能直接复现"我发出去的是什么"，省下 80% 的复现时间。

## 引用与数据来源

- agentgateway/agentgateway v1.3.0-alpha.1 release notes — https://github.com/agentgateway/agentgateway/releases/tag/v1.3.0-alpha.1
- agentgateway/agentgateway commits since 2026-06-04 — https://github.com/agentgateway/agentgateway/commits
- agentgateway PR #1887 dtrace body snapshot — https://github.com/agentgateway/agentgateway/pull/1887
- agentgateway PR #1993 cache_creation_input_tokens fix — https://github.com/agentgateway/agentgateway/pull/1993
- agentgateway PR #2098 agctl 重构 — https://github.com/agentgateway/agentgateway/pull/2098
- agentgateway PR #1841 a2a first-class backend — https://github.com/agentgateway/agentgateway/pull/1841
- agentgateway PR #2100 mcp resource subscribe — https://github.com/agentgateway/agentgateway/pull/2100
- envoyproxy/ai-gateway v0.6.0 release notes — https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0
- envoy-ai-gateway v0.6 docs — https://aigateway.envoyproxy.io/docs/0.6/
- kubernetes-sigs/gateway-api-inference-extension v1.5.0 — https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/tag/v1.5.0
- langgraph 1.2.4 release — https://github.com/langchain-ai/langgraph/releases/tag/1.2.4
- langgraph sdk 0.4.2 — https://github.com/langchain-ai/langgraph/releases/tag/sdk%3D%3D0.4.2
- crewAI 1.14.6 release — https://github.com/crewAIInc/crewAI/releases/tag/1.14.6
- crewAI 1.14.7a2 — https://github.com/crewAIInc/crewAI/releases/tag/1.14.7a2
- 上一期相关报告：2026-06-06-0848-aigw-mcp-server-cards-telemetry-r20.md（同期姊妹篇）
- 上一期相关报告：2026-06-06-0246-aigw-agent-gateway-r19.md
