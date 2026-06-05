# AI 网关持续深挖 · Agent Gateway 专题 · 第 18 期

> **抓取时间**：2026-06-06 02:06 CST（UTC 18:06）
> **抓取来源**：agentgateway/agentgateway 6/4–6/5 合并窗（#1784 / #2061 / #2039 / #2098 / #2096 / #2094 / #1850 / #1170）
> **主题索引**：cron 2/9 → Agent Gateway（**trace 调试 / 成本归因**）
> **上一期**：r17（#1398 budget × #1405 DNS-AID × #1334 Ed25519）

## 本期一句话总结

agentgateway 在 6/4–6/5 这一波把"**trace 调试 / 成本归因**"从"有 OTel 出口"（#493 v1.37.0）推到"**OTel 出口 + Prometheus 直方图按 call kind 切分 + CLI 把 pprof/heap/log 一把抓 + config_synchronized gauge**"——multi-agent 场景里"**哪条 sub-agent 调用慢、谁花了钱、为什么那段时间配置漂移了**"这条诊断链第一次有完整工具箱。

---

## 一、主轴 · 1784 + 2094 + 1170：TTFT → trace，call kind → metric

### 1.1 #1784 `proxy timing measurements`（**未合并**，5 commits / +604 / -106）

新增 `OutboundCallKind`（Primary / Policy / Mirror）× `OutboundCallSubtype`（Http / Llm / Mcp / ExtAuthz / ExtProc / Guardrail / RateLimit / Oidc）双维度 label + 两条直方图：

```
agentgateway_request_processing_seconds  {backend, bind, gateway, listener, route, route_rule}  # 入口 → primary outbound
agentgateway_response_processing_seconds {backend, bind, gateway, listener, route, route_rule}  # upstream first byte → 客户端首字节
```

CEL 暴露 `request.backend_call.kind` / `response.backend_call.kind` / `request.elapsed` / `response.elapsed`。**cardinality 工程克制**：新增 `MinimalHTTPLabels`（剥 status / method 等高基数维度）专门给处理时长直方图用。

**对 multi-agent 调试的实际收益**：

1. **sub-agent 拓扑可视化**。`{backend, route, route_rule}` 笛卡尔积天然描绘"哪个 session 走到哪条路由、命中哪个 backend"
2. **A2A peer 延迟横向比较**。call kind 拆分把 agent↔agent、agent↔model 拆成不同 series——**A2A 协议 call graph metric 的基础**
3. **退避 / 熔断的 metric 化触发**。`request.elapsed > X` 配 `route_rule` 是 sub-agent，policy 可 CEL 直接熔断该子 agent 改路由到 cold-standby
4. **cost × latency 矩阵**。response_processing × LLM cost（#285 token usage metric）= "哪个 agent 花最多钱且最慢"，是选型 / 砍模型的依据

### 1.2 #2094 `Set Time to First Token (TTFT) to traces`（open，6/5 16:57 howardjohn 评）

MarkYQJ 提的请求：

> "agentgateway could get the Time to First Token (TTFT), but not set to trace attribute `gen_ai.server.time_to_first_token`."

howardjohn 6/5 16:57 立即回复：

> "Once https://github.com/agentgateway/agentgateway/pull/1784 lands I can incorporate it there."

**意味着**：TTFT 不再独立实现，会在 #1784 的 response_processing 路径上加 `gen_ai.server.time_to_first_token` 语义属性——和 OTel GenAI v1.37.0 semconv 直接对齐。**Token-level streaming latency 进入 trace** 是 multi-agent 调试关键缺口：sub-agent 的"思考停顿时间"（first chunk → 第二个 chunk 间隔）在 prompt 拼接 + 工具调用场景下，比 total latency 更能定位瓶颈。

### 1.3 #1170 `GSoC 2026 · benchmarking framework`（open，3/9 robin-vidal 草案）

GSoC 2026 申请，**对 agentgateway inference routing 做可复现 benchmark**（mirror GIE 思路），用 `llm-d-inference-sim` 做对照。已跑数据：

| Metric | agentgateway | baseline |
|---|---|---|
| Requests succeeded | 455 / 510 | 455 / 510 |
| Mean latency | 6.30 ms | 3.20 ms |
| TTFT (mean) | 3.00 ms | 0.95 ms |
| ITL (mean) | 5.67 µs | 3.38 µs |

**隐含信号**：agentgateway 在 6.3 ms mean / 3.0 ms TTFT 量级上，**比裸 baseline 高 2–3 倍**。GSoC 是 mac 维度、#1784 是 unix 维度，两个合起来回答"agent gateway 的开销分布"。pending 5 个 maintainer 问题：CI 间隔、Looker vs Pages、S3 兼容、GPU 周期、是否回馈 GIE。

---

## 二、运维 DX 升级 · #2061 + #2098 + #2096 三个 agctl 收口

### 2.1 #2061 `Configuration synchronisation metric`（**6/5 15:34 合并**）

```
agentgateway_config_synchronized 0|1
```

`StateManager` 每次 reload 立即更新。**SRE 痛点闭环**："我现在跑的 config 和磁盘上的 config 是不是同一份"以前靠 `agctl config_dump | diff <(kubectl get cm -o yaml)`；现在 prom 端 1 个 query 就有答案。**对 multi-agent 场景特别关键**：sub-agent CRD（`AgentgatewayPolicy` / `AgentgatewayParameters` / `AgentgatewayBackend`）任何一个 reload 失败，prompt guard / 路由表 / 模型 list 全部可能静默回退到旧版本。

### 2.2 #2098 `agctl: restructure CLI and add proxy/controller log commands`（open，6/5 16:28 jbohanon）

agctl 重组为 `agctl proxy` / `agctl controller` 两大子命令组，旧 `config` / `trace` 降级为 alias + deprecation 提示：

- `agctl proxy log --set agentgateway::proxy=debug` —— 远程调 `/logging` 端点，按 Rust tracing-subscriber module 路径调级别
- `agctl controller log --set reconciler=debug` —— 调 Go slog 的 `?component=level` 端点
- HA / 副本扩缩时 `kubeutil.ForEachPod` 自动 fan-out
- **追加式 directive**：`--set` 不替换当前 filter 而合并，`--level` 才会重置

### 2.3 #2096 `agctl profile subcommand for pprof CPU and heap dumps`（open，6/5 14:29）

admin 端点 `/debug/pprof/profile?seconds=N` 和 `/debug/pprof/heap` 在 `crates/agentgateway/src/management/admin.rs` 已暴露，**但 agctl 没封装**。提案加 `agctl profile cpu --seconds=30 -o profile.pb.gz` / `agctl profile heap -o heap.pb.gz`。

**实际场景**：在 multi-agent gateway 上看到 CPU 飙升或 RSS 增长，**过去要 SSH 进 pod + 手敲 curl**；现在一条命令抓 pprof 直接 `go tool pprof`。**对 Rust 服务特别重要**——Go 的 pprof 工具链成熟，agentgateway 的 admin 端点留了 `.pb.gz`，从 Go 工具看 Rust 服务零摩擦。

### 2.4 三件套 · 调试 DX 矩阵

| 命令族 | 数据面 | 内存 | 配置 | 控制面 |
|---|---|---|---|---|
| `agctl proxy trace` | ✅ 链路抓 | — | — | — |
| `agctl proxy config` | — | — | ✅ 静态 dump | — |
| `agctl proxy log` | — | — | ✅ 调 log 级别 | — |
| `agctl proxy profile` | — | ✅ pprof | — | — |
| `agctl controller log` | — | — | — | ✅ 调 Go slog |
| `agentgateway_config_synchronized` (gauge) | — | — | ✅ | ✅ reload 状态 |

**这是 agentgateway 给 SRE 的"一站式工具箱"**：trace 看路径，log 调级别，profile 看资源，config_synchronized 看板盯漂移。**multi-agent 部署的"事故响应剧本"第一次有 CLI 直通车**。

---

## 三、周边 · #2039 + #1850 + #2095 三个值得记账

### 3.1 #2039 `Compose multiple AI backend policies`（**6/5 17:28 合并**，+98）

复用 AI policy 字段级 merge 逻辑处理多个 applicable backend AI policy；保留 route map 配置即便只有 promptguard-only policy；加 `/v1/messages` + wildcard route 的回归覆盖。**对 multi-agent 意义**：当一个 backend 同时受 prompt guard + 流量镜像 + 成本统计三类 policy 控制时，policy merge 顺序确定性是 audit 链可信的基础。

### 3.2 #1850 `Support MCP prompts in multiplexing mode`（open，5/18 ivanhavasi）

multiplex 模式下 `prompts` capability 在 initialize 响应中被省略，客户端不发 `prompts/list` / `prompts/get`；手动调用 `prompts/get` 返回 500 `invalid resource name`。**单 backend 模式无问题**。复刻 #692（resources 多路复用修复）的路子。**对动态 agent 拓扑**（DNS-AID 那种，r17 跟踪的 #1405）影响更大——上游 prompt 列表无法在 initialize 阶段宣告，下游 agent 不可知地少了能力。

### 3.3 #2095 `WebSocket upgrade case-sensitivity`（open，6/5）

libwebsockets / ttyd 上游返回 `Upgrade: WebSocket` 大写时，agentgateway 字节级比对，101 Switching Protocols 后 1ms 内隧道拆解。RFC 6455 §4.2 明确 token ASCII case-insensitive。**trace 调试视角**：access log `duration` ~1 ms + status 101 看似"成功"，但客户端反复 reconnect——**成本归因侧把这些"成功但立刻死"的请求计 1 次，实际上 sub-agent 重试 3-5 次才放弃**。配对 #2101 PR 同主题修复。

---

## 四、给 multi-agent 项目的 takeaway

1. **如果已接 agentgateway**：升 1.3.0-alpha.1 后**优先确认**多 backend 路径都跑过 #2039 描述的"多 policy 叠加"场景；提前把 `agentgateway_config_synchronized`（#2061 已合）和 `agentgateway_request_processing_seconds`（#1784 待合）的 Prometheus 看板 placeholder 加好；把 `agctl proxy log --set agentgateway::mcp=debug`（#2098 待合）写进事故 runbook。

2. **如果在选型 multi-agent trace 工具链**：agentgateway 现在能 export OTel GenAI v1.37.0（#493）+ 即将加 TTFT（#2094 经 #1784 路径）+ Prometheus 多 call kind 切分。这套组合**和 Langfuse 3.178.x 的 agent ↔ MCP 双向打通**是两条独立但可叠加的 trace 路径——agentgateway 走 network-level（gateway 视角），Langfuse 走 application-level（agent 视角）。**没有一家目前同时答完 "sub-agent timing 切分 + token cost 归因 + trace TTFT 标注"**——agentgateway 在做前者，LiteLLM 答后者，Langfuse 答中间。

3. **如果你是 agent gateway 维护者**：#1784 直方图暴露后，**对多 backend 拓扑一定要设 route label cardinality 上限**（agentgateway 选 `MinimalHTTPLabels` 剥 status code，值得借鉴）；#2094 + #1784 的合并顺序值得学：**先 Prometheus 直方图（reliable），再 trace 属性（依赖 OTel collector 配套）**——避免 trace 升级挡住 metric 升级；#2098 那种 CLI 重构**别一口气做**——保留 deprecation alias 至少两个 minor 版本，CLI 是最破坏性的接口。

---

## 五、本期数字摘要

- 抓取 6/4–6/5 24 小时窗：14 个 PR 状态更新，6 个新 issue，3 merge，2 close-not-merge
- 主线 PR：#1784（未合）/ #2061（已合）/ #2039（已合）/ #2098（待合）/ #2096（待合）
- 关联 issue：#2094 TTFT / #1170 GSoC / #1850 MCP prompts / #2095 WebSocket case
- r17 关注的设计性 issue 三角（#1398 / #1405 / #1334）本期无新进展

---

## 引用与数据来源

- agentgateway/agentgateway PR #1784 — proxy timing measurements: https://github.com/agentgateway/agentgateway/pull/1784
- agentgateway/agentgateway PR #2061 — config synchronisation metric: https://github.com/agentgateway/agentgateway/pull/2061
- agentgateway/agentgateway PR #2098 — agctl CLI restructure + log: https://github.com/agentgateway/agentgateway/pull/2098
- agentgateway/agentgateway PR #2096 — agctl profile (pprof): https://github.com/agentgateway/agentgateway/pull/2096
- agentgateway/agentgateway PR #2039 — compose multiple AI backend policies: https://github.com/agentgateway/agentgateway/pull/2039
- agentgateway/agentgateway PR #2101 — websocket case insensitive upgrade: https://github.com/agentgateway/agentgateway/pull/2101
- agentgateway/agentgateway Issue #2094 — TTFT to traces: https://github.com/agentgateway/agentgateway/issues/2094
- agentgateway/agentgateway Issue #2095 — WebSocket upgrade case: https://github.com/agentgateway/agentgateway/issues/2095
- agentgateway/agentgateway Issue #1850 — MCP prompts multiplex: https://github.com/agentgateway/agentgateway/issues/1850
- agentgateway/agentgateway Issue #1170 — GSoC benchmarking framework: https://github.com/agentgateway/agentgateway/issues/1170
- agentgateway/agentgateway Issue #692 — MCP resources multiplex（#1850 引用）: https://github.com/agentgateway/agentgateway/issues/692
- agentgateway/agentgateway PR #493 — OTel GenAI v1.37.0 semconv: https://github.com/agentgateway/agentgateway/pull/493
- agentgateway/agentgateway PR #1842 — ExtMCP for MCP aware ext_authz/ext_proc: https://github.com/agentgateway/agentgateway/pull/1842
- OpenTelemetry GenAI semantic conventions 1.37.0: https://opentelemetry.io/docs/specs/semconv/gen-ai/
- 上一期 r17 / 同期 2026-06-06-0046-aigw-helicone-release.md / 2026-06-06-0013-aigw-kong-release.md
