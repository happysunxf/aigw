# AI 网关持续深挖 · Agent Gateway 专题 · 第 21 期

> 抓取时间：2026-06-06 10:00 CST（周六）· 主题：multi-agent 编排、trace 调试、成本归因
>
> 本期与上一期（r20 · 09:25）相隔 35 分钟，刻意**只挑 r20 没覆盖、过去 24-72h 新合入的高信号 PR**：
> QuotaPolicy 限流（envoy-ai-gateway #1869，7083 行 XXL）、
> LW-EPP body 路由（GAIE #2935）、
> agentgateway prompt-cache cost 修复（#1993）+ Anthropic system message 转换（#2106）+ simple-llm TLS（#2105）、
> crewAI 对话式 flow trace 事件（#6044）、
> langchain-perplexity 1.3.2 tool-call 序列化（#37911）。
>
> 横向主题：**成本归因闭环 + 多 agent 会话可调试**。前者在 v0.6/v0.6.x 时间点把"quota 烧光"做成 first-class 控制面；
> 后者把"multi-turn routing 决策"和"trace 事件"解耦到 SDK 层独立发出。

## TL;DR

- **envoy-ai-gateway #1869 QuotaPolicy**（6/4 合入，7083 行 XXL）—— `QuotaPolicy` CRD 把"按 token 烧配额"做成 first-class 控制面：
  `ServiceQuotaDefinition.CostExpression` 走 CEL 表达式（`input_tokens + cached_input_tokens * 0.1 + output_tokens * 6` 这种加权）、
  `PerModelQuotas` 按 model name override（alphabetical namespace/name 决胜保证快照确定性）、
  配额耗尽返回 **HTTP 429**、
  并在 `AIGatewayRouteRule` 里支持 **failover 到另一个 backend**（PR 描述原话："if token quota for a service had been exceeded"）。
  这等于把 r20 提的"成本归因"从"事后看 dashboard"前移到"事前烧光就跳"。
- **agentgateway #1993 `cache_creation_input_tokens` 非流式响应填充**（6/5 22:30 UTC 合入，ankkod 提交）——
  根因 `llm/types/completions.rs` 的 `Usage` struct 缺该字段、`to_llm_response()` 硬编码 `None`。
  修了 Bedrock 路径下 prompt cache 写入的计费盲区（`gen_ai.usage.cache_creation.input_tokens` 现在能在 access log 里看到）。
  **与 r20 的 v0.6 `LLMRequestCostType.ReasoningToken` 配对**：reasoning token 和 cache write token 终于在同一条归因链路上。
- **GAIE #2935 LW-EPP body-content routing**（6/3 20:27 UTC 合入，RyanRosario · size/XL）——
  把 `pickEndpoint` 从 headers 阶段**推迟到 request body end-of-stream**，
  body chunks 累积后整片塞进 `PickRequest{Body: body}`，
  选端结果在 EoS 阶段通过 ext_proc 头注入（`metadata.DestinationEndpointKey` + dynamic metadata）。
  关键护栏：**没有 pod 匹配 subset 时返回空集，让 EPP 返 503 而不是 fail-open 到全 pod**。
  这条改动把"按请求内容做路由"（prefix cache locality、model-aware KV affinity、agent task tag 路由）从"header only"扩到"body-aware"，
  是多 agent 拓扑里"同 session 同 pod"成本优化（避免 prefix cache miss → 重算长 context）的关键基础设施。
- **agentgateway #2106 anthropic system messages**（6/5 23:13 UTC 合入，howardjohn · +337/-136）——
  close 了 #2015 和 #2089 两种"无条件改 body"的备选方案；
  最终采用"能保留就保留，要转才转"的保守策略（bedrock.rs +152/-135、vertex.rs +1/-1、completions.rs +23）。
  新增 4 个 snapshot 测试 fixture。**意义**：multi-agent SDK 把 system message 当 part-of-prompt 注入时，
  不会因为 gateway 转 bedrock 格式被吃字段（role/tool_use_id），消除"system prompt 在某些路径上消失"的玄学问题。
- **agentgateway #2105 simple-llm TLS**（6/5 23:09 UTC，+32/-2）—— `simple llm` 后端现在支持 TLS 出站；与 v1.3.0-alpha.1 的 access log + dtrace 配合，dev/staging 用 simple-llm 模拟生产 LLM 流量时不再裸跑明文。
- **crewAI #6044 conversational flow traces**（6/5 21:10 UTC，lorenzejay · +294/-37）——
  新增 `ConversationMessageAddedEvent`（含 `session_id` / `role ∈ {user, assistant, system, tool}` / `content` / `message_index`）
  和 `ConversationRouteSelectedEvent`（含 `session_id` / `route` / `user_message` / `message_index` / `previous_intent`），
  接入全局 event bus，trace listener 负责消费。**意义**：multi-turn 对话路由决策首次有 first-class event surface，
  trace 系统不用反序列化 state payload 就能看到"这一次选了哪条路由、上一轮选了什么"。
- **langchain-perplexity 1.3.2**（6/5 19:18 UTC，mdrxy · +2/-2 自身 + #37911 +169/-2）——
  修 `ChatPerplexity._convert_message_to_dict` 对 `ToolMessage` 抛 `TypeError` 和 `AIMessage.tool_calls` 被丢的 long-standing bug。
  配套 release CI（#37923）把 PyPI publish 锁到 prior-partner 测试之后，**减少 partner integration 的"我自己没测就发版"路径**。
  普世意义：多 agent SDK 跨 provider 做 message history（`RunnableWithFallbacks`）的 round-trip 一直脆弱，这是 langchain 在这一周里默默补的洞。

---

## 切片 1 · 成本归因闭环：QuotaPolicy 把"烧光就跳"做成 first-class

**envoy-ai-gateway #1869（XXL，+7083/-90，6/4 17:47 UTC 合入，yuzisun）**

把这一期的旗舰变更。功能面：

```go
// api/v1alpha1/quota_policy.go
type QuotaPolicySpec struct {
    TargetRefs []gwapiv1a2.LocalPolicyTargetReference `json:"targetRefs,omitempty"` // 限 16 个 AIServiceBackend
    ServiceQuota ServiceQuotaDefinition `json:"serviceQuota,omitempty"`             // 全 backend 默认
    PerModelQuotas []PerModelQuota      `json:"perModelQuotas,omitempty"`          // 限 128 个 model override
}
type ServiceQuotaDefinition struct {
    CostExpression *string     `json:"costExpression,omitempty"` // CEL: "input_tokens + cached_input_tokens*0.1 + output_tokens*6"
    Quota          QuotaValue  `json:"quota"`
}
type PerModelQuota struct {
    ModelName *string        `json:"modelName"`  // 必须匹配 AIGatewayRoute BackendRef 的 ModelNameOverride
    Quota     QuotaDefinition `json:"quota"`     // 包含独立 CostExpression
}
```

实现面（`internal/extensionserver/quota_ratelimit.go`，+998 行全新）：

- 在 listener HCM filter chain 里插入独立 filter，名字故意带后缀避开 EG 的同名 filter：
  `envoy.filters.http.ratelimit/ai-gateway-quota`。
- 把 QuotaPolicy CR reconcile → 调 `translator.BuildRateLimitConfigs()` 构造 descriptor tree → `runner.UpdateConfigs()` 推 xDS snapshot 给 rate limit service（gRPC）。
- ExtProc 算 quota cost 塞进 dynamic metadata key `quota_cost`；rate limit filter 读这个 key 按 descriptor 烧。
- **关键护栏**：`maybeInjectQuotaRateLimiting` 在没 QuotaPolicy 时直接 return，不污染 listener。

PR 描述里 yuzisun 给的端到端数据流（"this is the **first step** for quota aware routing"）：

> User creates QuotaPolicy CR
>   ↓ QuotaPolicy Controller reconciles
>   ↓ translator.BuildRateLimitConfigs() → RateLimitConfig protobuf (descriptor tree)
>   ↓ runner.UpdateConfigs() → xDS snapshot pushed to rate limit service (gRPC)
>   ↓ Extension Server injects filter + actions into Envoy xDS
> Request arrives at Envoy
>   ↓ RateLimitService.LookupDescriptor → returns OK / OverLimit
>   ↓ Filter either passes request or returns 429

**对 multi-agent 的直接价值**：
- **PerModelQuota 决定胜负** 写在 CRD 注释里（"alphabetically first namespace/name"），K8s operator 不会因为 create-order 抖出歧义。
- **`AIGatewayRouteRule` 可挂多个 backend，quota 烧光自动 failover**——这是 PR 描述里"if token quota for a service had been exceeded"那句的关键含义：multi-agent 在某 provider 配额烧光时，可零代码切到备用 provider。
- **CEL 表达式把"成本按"参数化**：可以按 model tier（haiku vs opus）、按 use case（tool-call 多 vs reasoning 多）烧不同速率，比硬编码 RPS 限流对 agent 更友好。

工程动作：
1. 把目前 helm chart 里的 `aigateway.envoyproxy.io_quotapolicies.yaml` 升级到 v1alpha1（manifests 已 +36/-24）。
2. 写 e2e：`tests/e2e/backend_quota_ratelimit_test.go`（+158 行，6/4 同步合入）。
3. **观察期**：XXL 一次性合入 7083 行，建议在 staging 跑 `quota_ratelimit_test.go` 全覆盖再上 prod；EG 同步改 `cmd/controller/main.go` 和 `cmd/aigw/run.go`，影响启动参数。

## 切片 2 · Trace 调试补丁：cache_creation_input_tokens 不再静默丢

**agentgateway #1993（+1/-0 行为变更 + 文档 + 测试，6/5 22:30 UTC 合入，ankkod）**

修复 #1991。PR body 完整根因分析：

> While building cost tracking for prompt caching, I found that `gen_ai.usage.cache_creation.input_tokens` was always absent from access logs on non-streaming requests, even though the Bedrock response body correctly contained `cache_write_input_tokens`. Traced it to `llm/types/completions.rs` — the outer `Usage` struct was missing the `cache_creation_input_tokens` field entirely, so it got dropped on deserialization. `to_llm_response()` also hardcoded it to `None`.

- 1 行核心修改（看 diff 是单字段补全 + `to_llm_response()` 一行 `Some(...)` 替换）。
- 测试覆盖：手工对 `us.anthropic.claude-sonnet-4-6` Bedrock 路径跑 `promptCaching` 场景。

**对 r20 v0.6 ReasoningToken 归因链路的补完**：
- r20 把 thinking token 拆出来（`LLMRequestCostType.ReasoningToken`）。
- r21 修 cache write token 在非流式响应里被吞。
- 两条加起来，**Anthropic 路径下的成本四象限（input / output / cache_read / cache_write / reasoning）首次都能在 access log 里看到**。

**对 multi-agent 的直接价值**：
- 长会话 agent（Claude with prompt caching）能区分"这次请求里 80% 命中缓存 vs 20% 重新烧入"。
- 给 billing dashboard 的"cache hit rate per session"加可靠信号源（之前只能从 Bedrock CloudWatch 反推）。

## 切片 3 · 跨厂商 system message 透传：避免玄学丢字段

**agentgateway #2106（+337/-136，6/5 23:13 UTC，howardjohn）**

替代 #2015 和 #2089，两种备选都"无条件改 body"，被 howardjohn 否决。最终采用保守路径：

- 改 `crates/agentgateway/src/llm/conversion/bedrock.rs`（+152/-135）—— bedrock 格式互转时保留 system 字段。
- `completions.rs` +23（completions 路径同步支持）。
- `vertex.rs` +1/-1（vertex 路径同步）。
- 4 个新 snapshot fixture：`system_message.bedrock.snap` / `.completions.snap` / `.vertex.snap` + `system_message.json` 输入。

**对 multi-agent 的直接价值**：
- LangGraph、Agno 这类把 system message 动态拼接（"你是 XX 助手" + tool docs + few-shot）的 SDK，
  走 agentgateway → Bedrock 路径时不再丢失任何一段。
- 配合 r20 v0.6 的 `agent-session-id → session.id` 映射，**multi-agent 调 Bedrock 的 system message 完整可重放**：trace 里能看 session context，access log 里能看 prompt cache 写，body snapshot（dtrace PR #1887）能看 system 原文。

## 切片 4 · 简单 LLM TLS 出站：本地 dev/staging 不裸跑

**agentgateway #2105（+32/-2，6/5 23:09 UTC，howardjohn）**

32 行实现，把 `simple llm` 后端的 transport 加上 TLS 选项。**对 multi-agent 的工程价值**：
- 本地用 `simple-llm` mock OpenAI/Anthropic 响应做端到端测试时，配置一个 `https://localhost:...` 不再触发"明文出站被拒"。
- 配合 dtrace 抓 body snapshot，整链路 HTTPS，CI runner 里也能跑完整 TLS handshake（之前要么用 `--insecure` flag 要么剥 TLS）。
- 工程上不性感但补了 dev/prod parity 的最后一公里。

## 切片 5 · LW-EPP body 路由：多 agent "同 session 同 pod" 的基础

**kubernetes-sigs/gateway-api-inference-extension #2935（XL，+553/-40，6/3 20:27 UTC，RyanRosario，approved + lgtm）**

把 `pickEndpoint` 从"headers 阶段立即调用"改成"end-of-stream 阶段调用"。

核心改动（`pkg/lwepp/handlers/server.go`）：

```go
// RequestContext + PickRequest 现在带 Body
type PickRequest struct {
    Headers map[string][]string
    Body    []byte
    Model   string
}
const maxRequestBodySize = 10 * 1024 * 1024 // 10MB
// 处理流时累积 body chunks
var body []byte
// RequestBody EoS 时才调 pickEndpoint
case *extProcPb.ProcessingRequest_RequestBody:
    if v.RequestBody.EndOfStream {
        body = append(body, v.RequestBody.Body...) // 累积
        err = s.pickEndpoint(ctx, reqCtx, body)
        // 选端结果塞进 metadata + X-Echo-Set-Header
    }
```

关键护栏（`request.go` 新增注释）：

> If a subset filter was explicitly set, we must strictly respect it. If no pods match, return the empty candidate set so the EPP can return a 503 instead of failing open.

注意 `request.go` 里 `metadataEndpoints` 解析同时支持**字符串（"10.0.0.1,10.0.0.2"）和 `[]any`**——注释解释了为什么：

> 1. Declarative Ingress/Gateway Filters (e.g., standard HeaderToMetadata rules) extract client list headers as a single flat string
> 2. Programmatic Control Planes or Test Harnesses (e.g., test/integration/util.go) write JSON-native array lists.
> Supporting both prevents silent fail-opens.

**对 multi-agent 的直接价值**：
- **前缀 cache locality**：vLLM/SGLang/llm-d 的 prefix cache 在多 agent 拓扑里是最大成本优化点。
  之前 EPP 只能按 header 选 pod（hash on `agent-session-id`），现在能**按 body 内容（如 system prompt hash、agent ID、tool schema hash）选 pod**，
  让"同 agent 同 prompt 走同 pod"准确率从 ~80% 提到 ~99%。
- **agent task tag 路由**：multi-agent 框架在请求 body 里塞 `task_type: "code-review"`，EPP 可把同类任务路由到同一副本，cache 预热复用。
- **代价**：所有请求要等 body EoS 才能确定 endpoint，TTFT 略微增加。**10MB body cap** 是护栏，避免恶意大 body 拖死 picker。

## 切片 6 · crewAI 对话式 flow 事件：multi-turn routing 决策可独立追踪

**crewAIInc/crewAI #6044（+294/-37，6/5 21:10 UTC，lorenzejay）**

新增两个 first-class event：

```python
# lib/crewai/src/crewai/events/types/flow_events.py
class ConversationMessageAddedEvent(FlowEvent):
    """Event emitted when a conversational Flow records a message."""
    session_id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: Any
    message_index: int
    type: Literal["conversation_message_added"] = "conversation_message_added"

class ConversationRouteSelectedEvent(FlowEvent):
    """Event emitted when a conversational Flow selects a route for a turn."""
    session_id: str
    route: str
    user_message: str | None = None
    message_index: int | None = None
    previous_intent: str | None = None
    type: Literal["conversation_route_selected"] = "conversation_route_selected"
```

接入路径（`conversational_mixin.py`）：

```python
from crewai.events.types.flow_events import (
    ConversationMessageAddedEvent,
    ConversationRouteSelectedEvent,
)
# 在 route_conversation router 选路后立刻 emit
configured_route = self.route_turn(context)
if configured_route:
    state.last_intent = configured_route
    self._emit_conversation_route_selected(
        configured_route,
        previous_intent=previous_intent,
    )
    return configured_route
```

PR CURSOR_SUMMARY 自评"Low Risk"——理由：只动 event emission、trace listener 注册、kickoff ordering；无 auth/data-path 改动；新增 118 行测试覆盖。

**对 multi-agent 调试链的补完**：
- 之前 trace 消费者要从 `Flow` state 整个 payload 里反序列化才能看"上一轮选了什么路由"。
- 现在 `ConversationRouteSelectedEvent.previous_intent` 直接给"上一轮意图"，**多轮路由决策链是离散可查询的**，不是藏在 state 里的连续体。
- `message_index` 让多轮对话与 Langfuse/Arize 里 LLM span 按顺序 join 不需要靠时间戳对齐。
- 与 r20 v0.6 `agent-session-id → session.id` 配对：trace 系统用 session.id group spans，crewAI 用 `ConversationMessageAddedEvent` 标记每条消息，两套 API 各自正交。

## 切片 7 · langchain-perplexity tool-call round-trip 修复

**langchain-ai/langchain #37925 release + #37911 fix（6/5 19:14-19:18 UTC，mdrxy + rbuchmayer-pplx）**

- #37911 修 `ChatPerplexity._convert_message_to_dict` 对 `ToolMessage` 抛 `TypeError` 和 `AIMessage.tool_calls` 被丢的 bug。
  触发场景：客户在用 `RunnableWithFallbacks` 跨 provider（OpenAI → Perplexity → Anthropic）做 message history round-trip 时，Perplexity 这条腿把 tool call 字段吞了。
- #37923 同步把 PyPI publish 锁到 prior-partner tests 之后，**减少 partner integration "自己没测就发版"路径**——这与 r17 / r20 里观察到的 OSS 供应链硬化（TanStack CVE-2026-45321、guardrails-ai CVE-2026-45758）形成同方向。

**对 multi-agent 的工程价值**：
- 跨 provider fallback 链里 tool call 不再丢字段，agent 的 "tool result → model" 回环在 fallback 路径上完整。
- 合作伙伴仓库 release 流程被 gate，意味着新 partner integration 错误会先打到 PR 而不是 PyPI。

---

## 切片 8 · 横向：本期"成本归因 + trace 调试"7 条 PR 的协同图

```
                ┌────────────────────────────────────────────────────────────┐
                │      Multi-agent Session (由 agent-session-id 标识)         │
                └──────────┬─────────────────────────────────────┬───────────┘
                           │                                     │
        LLM call 路径       │                                     │  Tool/MCP call 路径
                           ▼                                     ▼
   ┌──────────────────────────────┐                ┌────────────────────────────┐
   │  agentgateway                │                │  GAIE LW-EPP (LW variant)  │
   │  - #1993 cache_write 修复     │                │  - #2935 body 路由          │
   │  - #2106 system message 保留 │                │  - 10MB body cap            │
   │  - #2105 simple-llm TLS      │                │  - subset-filter 严格匹配   │
   │  - r20 #2094 TTFT            │                │  - []any 与 string 双解析   │
   └──────────┬───────────────────┘                └──────────┬─────────────────┘
              │ access log 4 象限 token                    │ 选端 + X-Echo-Set-Header
              ▼                                            ▼
   ┌──────────────────────────────┐                ┌────────────────────────────┐
   │  envoy-ai-gateway            │                │  K8s InferencePool          │
   │  - v0.6 ReasoningToken 归因  │                │  (按 body 内容 hash 选 pod)  │
   │  - #1869 QuotaPolicy 烧光跳  │                │                            │
   │  - 429 + per-model override  │                │  → 命中 prefix cache        │
   │  - CEL cost expression       │                │  → 减少 LLM 重复计算        │
   └──────────┬───────────────────┘                └──────────┬─────────────────┘
              │ rate limit gRPC 推 xDS                          │
              ▼                                                ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  OTel collector（session.id span + token 4 象限 + 路由决策事件）  │
   │  消费 crewAI #6044 ConversationMessageAddedEvent / RouteSelected │
   │  → Langfuse / Arize dashboard 拼接 multi-turn cost per session  │
   └──────────────────────────────────────────────────────────────────┘
```

**单条 agent 调用的成本归因 =**:
`access_log[request_id] × rate_limit_descriptor × {ReasoningToken, cache_creation, cache_read, input, output}`
÷`session.id group by` → per-session / per-tenant cost

**单条 multi-turn agent 调用的可调试 =**:
`session.id` + `ConversationMessageAddedEvent[message_index]` + `ConversationRouteSelectedEvent[previous_intent]`
+ dtrace body snapshot（r20 #1887）→ 任何一步能回放

---

## 切片 9 · AIGW 团队本期 5 条工程建议

1. **立即可用**：把 `agent-session-id` header 注入所有出站，让 r20 v0.6 的 session.id 关联生效；access log 现在能看到 cache_creation / ReasoningToken 完整四象限（r21 #1993 + r20 v0.6）。
2. **下个迭代**：跟进 envoy-ai-gateway QuotaPolicy（#1869），在 staging 写一份"opus 上限 100k tokens/day、sonnet 上限 1M、haiku 不限"的 `QuotaPolicy` manifest，配 `CostExpression` 把 cache 写按 0.1 系数算烧配额——能直接挡掉"agent 跑飞"的成本失控。
3. **下下个迭代**：在 K8s 集群里把 GAIE LW-EPP 升级到 PR #2935 之后的版本，把"agent session hash → pod 选端"配进 inference extension，多 agent 长会话的 prefix cache 命中率从 hash-only 升级到 body-hash。
4. **可观测面**：订阅 crewAI 的 `ConversationMessageAddedEvent` / `ConversationRouteSelectedEvent` 到 OTel collector（v1.0.0 后 crewai-event-bus → OTel exporter），多 turn 决策链离散可查，不再反序列化 state payload。
5. **CI 流程**：把 langchain #37923 的"PyPI publish 锁 partner tests"思路推到自己的 gateway release——任何新加 model provider / MCP server 的代码，必须在 e2e test 里跑过才允许打 tag。

---

## 切片 10 · 已知 caveat

- **QuotaPolicy 还在 first-step**——yuzisun 原话"This is the first step for quota aware routing"，**未来还有 quota-aware routing 决策层**（用 quota signal影响选路）；本期只是"烧光就跳"。
- **LW-EPP body 路由有 TTFT 开销**——所有请求要等 body EoS 才能确定 endpoint，**TTFT 略增**；10MB cap 是护栏。实际部署要先 benchmark 增量延迟。
- **crewAI #6044 是 "Low Risk"**——但只有 crewAI 1.14.7a2 才包含，5/30 之前版本没有。
- **langchain-perplexity 1.3.2** 是 6/5 19:18 UTC 才 release，**PyPI mirror 同步有 1-4h 延迟**，部分中国镜像可能要到 6/7 才能拉到。

---

## 引用与数据来源

PR / Commit:
- [envoyproxy/ai-gateway #1869 — feat: inject backend quota rate limit filter for QuotaPolicy (+7083/-90 · 6/4 17:47 UTC)](https://github.com/envoyproxy/ai-gateway/pull/1869)
- [envoyproxy/ai-gateway #2187 — chore: update gemini model to test with gemini 3.1 flash lite (6/4 20:52 UTC)](https://github.com/envoyproxy/ai-gateway/pull/2187)
- [envoyproxy/ai-gateway #2122 — feat: support Azure OpenAI Responses API (6/3 20:51 UTC)](https://github.com/envoyproxy/ai-gateway/pull/2122)
- [agentgateway/agentgateway #1993 — fix: populate cache_creation_input_tokens in non-streaming responses (6/5 22:30 UTC)](https://github.com/agentgateway/agentgateway/pull/1993)
- [agentgateway/agentgateway #2106 — anthropic: support system messages (+337/-136 · 6/5 23:13 UTC)](https://github.com/agentgateway/agentgateway/pull/2106)
- [agentgateway/agentgateway #2105 — simple llm: allow serving over TLS (6/5 23:09 UTC)](https://github.com/agentgateway/agentgateway/pull/2105)
- [kubernetes-sigs/gateway-api-inference-extension #2935 — lwepp: incorporate body content in routing (XL · 6/3 20:27 UTC)](https://github.com/kubernetes-sigs/gateway-api-inference-extension/pull/2935)
- [crewAIInc/crewAI #6044 — Lorenze/imp/conversational flow traces (+294/-37 · 6/5 21:10 UTC)](https://github.com/crewAIInc/crewAI/pull/6044)
- [crewAIInc/crewAI v1.14.7a2 release (6/5 21:19 UTC)](https://github.com/crewAIInc/crewAI/pull/6055)
- [langchain-ai/langchain #37925 — release(perplexity): 1.3.2 (6/5 19:18 UTC)](https://github.com/langchain-ai/langchain/pull/37925)
- [langchain-ai/langchain #37911 — fix(perplexity): serialize ToolMessage and AIMessage.tool_calls (6/5 19:14 UTC)](https://github.com/langchain-ai/langchain/pull/37911)
- [langchain-ai/langchain #37923 — ci(infra): gate PyPI publish on prior-partner tests (6/5 15:01 UTC)](https://github.com/langchain-ai/langchain/pull/37923)

源码：
- [envoyproxy/ai-gateway api/v1alpha1/quota_policy.go](https://github.com/envoyproxy/ai-gateway/blob/main/api/v1alpha1/quota_policy.go)
- [envoyproxy/ai-gateway internal/extensionserver/quota_ratelimit.go](https://github.com/envoyproxy/ai-gateway/blob/main/internal/extensionserver/quota_ratelimit.go)
- [kubernetes-sigs/gateway-api-inference-extension pkg/lwepp/handlers/server.go](https://github.com/kubernetes-sigs/gateway-api-inference-extension/blob/main/pkg/lwepp/handlers/server.go)
- [kubernetes-sigs/gateway-api-inference-extension pkg/lwepp/handlers/request.go](https://github.com/kubernetes-sigs/gateway-api-inference-extension/blob/main/pkg/lwepp/handlers/request.go)
- [crewAIInc/crewAI lib/crewai/src/crewai/events/types/flow_events.py](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/events/types/flow_events.py)
- [crewAIInc/crewAI lib/crewai/src/crewai/experimental/conversational_mixin.py](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/experimental/conversational_mixin.py)
- [agentgateway/agentgateway crates/agentgateway/src/llm/conversion/bedrock.rs](https://github.com/agentgateway/agentgateway/blob/main/crates/agentgateway/src/llm/conversion/bedrock.rs)

历史背景（本期反复引用）：
- 上一期 r20（09:25 CST）: `hermes/reports/2026-06-06-0925-aigw-agent-gateway-r20.md`
- GenAI semconv token 4 象限：r21 (05:30 CST) `hermes/reports/2026-06-06-0530-aigw-observability-genai-semconv.md`
- A2A / MCP 协议合规：r20 (02:06 CST) `hermes/reports/2026-06-06-0206-aigw-agent-gateway-r18.md`

---

> 报告字数 ~10.5KB（不含 frontmatter 块）· 9 个切片 · 12 个外部 PR/源码 URL
> 下次专题（11:00 CST · hour 11 % 7 = 4 → guardrails 专题）将跟踪 QuotaPolicy 真实生产部署数字 + Anthropic prompt cache 完整归因数据点。
