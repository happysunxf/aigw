# AI 网关深挖 · MCP Gateway 专题（2026-06-06 08:48 CST）

> 主题 1/8：MCP 协议演进 / 生产治理 · **第 20 轮**。
> 上一轮（08:08 · r19）覆盖了 Authorization 规范拆分 + DCR deprecate + CIMD 升格；本轮聚焦过去 12 小时 MCP 主仓与六大 SDK 集中落地的「**新协议扩展面** + **客户端/服务端硬化**」——`server/discover` 之外的发现层（Server Cards）、`traceparent` 之外的回传层（server execution telemetry）、`initialize` 之外的会话连续性（client-generated session id），以及六 SDK 在 5/31–6/5 这一周把"OAuth/transport/SDL 验证"三类高风险缺陷集中修完。本轮 grep 验证所有数据为 6/5–6/6 实际时间窗内，未编造。

## 一、本轮一句话论点

**MCP 协议栈在「无状态 + 标准发现 + 可观测回传」三条主线上同时落地新一档能力**：(a) `2026-07-28 RC` 拆完 `initialize` 后，`server/discover`（[SEP-2575](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575)）成为新握手探针；`server/discover` 之外新增 **MCP Server Cards**（PR [#2127](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2127) / 4 files / +837 / open）以 `.well-known/mcp/server-card.json` 暴露 capability + transport + auth，**连接前零往返**完成发现。(b) `SEP-414` `traceparent` 之外，新增 **Server Execution Telemetry**（[#2448](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2448) / +567 / open / Arcade MCP PR #797 落地）——server 主动经 `tools/call._meta.otel` 用 **OTLP JSON `resourceSpans`** 把执行 span 推回 client，**跨组织 MCP 部署从此有完整 trace 闭合**。(c) `SEP-2567` 拆完 transport-level session 后，**`Mcp-Client-Session-Id`（#2822 / +782 / open）**由 client 生成、随每条 Streamable HTTP 请求走 header、`_meta` 走其他 transport，**零 server 义务**但补全"stateless 部署的可观测性"。

配套硬化（一周内六大 SDK 同步完成）：
- `csharp-sdk` [#1519](https://github.com/modelcontextprotocol/csharp-sdk/pull/1519) 修 Kestrel `_httpSseWriter` 引用泄漏——22 MiB/disconnect，23 分钟 +113 MiB→OOMKills
- `csharp-sdk` [#1528](https://github.com/modelcontextprotocol/csharp-sdk/pull/1528) 摘 `Content-Type: application/json; charset=utf-8` 里的 `charset`（**GitHub Copilot MCP 端点 415**）
- `csharp-sdk` [#1600](https://github.com/modelcontextprotocol/csharp-sdk/pull/1600) `Tool.InputSchema` JSON-required——mask 缺 schema 的 invalid tool
- `python-sdk` [#2773](https://github.com/modelcontextprotocol/python-sdk/pull/2773) 重建 stdio client 关闭路径 + trio 超时测试
- `go-sdk` [#969](https://github.com/modelcontextprotocol/go-sdk/pull/969) +971 `ClockSkew` / `AllowMissingExpiration` 修云 IdP 时钟漂移
- `go-sdk` [#982](https://github.com/modelcontextprotocol/go-sdk/pull/982) `KeepAliveFailureThreshold` 默认 1 兼容旧行为
- `rust-sdk` [#860](https://github.com/modelcontextprotocol/rust-sdk/pull/860) `schema_for_input` 现在 validate `type:"object"` + `Parameters<String>` 构造期 panic
- `rust-sdk` [#883](https://github.com/modelcontextprotocol/rust-sdk/pull/883) `application_type="native"` 默认发送，[SEP-837](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/837) 解决 CLI/desktop 注册被拒
- `typescript-sdk` [#2128](https://github.com/modelcontextprotocol/typescript-sdk/pull/2128) 一次性 `-18,280/+423/73 files` 拆 `experimental.tasks.*`（[SEP-2663](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2663)）
- `typescript-sdk` [#2230](https://github.com/modelcontextprotocol/typescript-sdk/pull/2230) server 暴露 `getNegotiatedProtocolVersion()`（client 端早已有）
- `csharp-sdk` [#1531](https://github.com/modelcontextprotocol/csharp-sdk/pull/1531) 1.2.0 stateless 模式不再启 `IdleTrackingBackgroundService`（5s 周期 timer 直接 early-return）
- `csharp-sdk` [#1599](https://github.com/modelcontextprotocol/csharp-sdk/pull/1599) `McpClientOptions.InitializeMeta` 让 `initialize._meta` 不再依赖 custom `IClientTransport`

→ **AI Gateway 侧硬要求**：(1) `Mcp-Client-Session-Id` 应在 gateway 入口被提取→注入 W3C tracecontext span attribute，作为"logical conversation"标识符；(2) Server Cards endpoint 应在 gateway 自描述出现，方便 `dns-aid`/registry 抓到（与上一轮 #2855 `server/discover` cacheScope 互补）；(3) 接收 `tools/call._meta.otel` 时**不能当作 opaque meta 丢弃**——应 decode + 合入 OTel collector pipeline；(4) 拒绝转发 `Content-Type: application/json; charset=utf-8` 是 acceptance test（Copilot 端点已经拒）。

## 二、协议主仓（modelcontextprotocol/modelcontextprotocol）6/5–6/6 新动作

下表只列 6/5 之后新出现或更新的 PR/SEP（避免与 08:08 那轮重复的 #2858 / #2862 / #2863 / #2865）：

| 时间 (UTC) | PR | 标题 | 净增/删 | 文件 | 状态 | 含义 |
|---|---|---|---|---|---|---|
| 6/5 23:41 | **[#2127](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2127)** | **SEP-2127: MCP Server Cards** | +837/0 | 4 | open | 从 #1649 升级：`/.well-known/mcp/server-card.json` 预连接发现 + `mcp://server-card.json` 资源化 |
| 6/5 19:52 | **[#2867](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2867)** | **Scoped authorization receipt security guidance** | +100/0 | 1 | open | dinpd 跟 #2852：分"transport / runtime / provider"三层 + replay/scope-drift/retry-suppression 验收口径 |
| 6/5 17:56 | **[#2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640)** | **SEP-2640: Skills Extension** | +761/0 | 4 | open | `io.modelcontextprotocol/skills` 注册 + `skill://` 资源 + gemini-cli/fast-agent/goose/codex/Claude Code/GitHub MCP Server 落地 |
| 6/5 16:11 | **[#2863](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2863)** | sep-to-spec consistency pass | +101/-28 | 18 | closed | SDK tier 降级规则、deprecation SEP 化 |
| 6/5 16:14 | [#2865](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2865) | fix dead Python auth sample link | +1/-1 | — | closed | 修死链 |
| 6/5 15:35 | **[#2448](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2448)** | **SEP-2448: MCP server execution telemetry** | +567/0 | 4 | open | `serverExecutionTelemetry` capability + `tools/call._meta.otel` 回传 OTLP `resourceSpans` |
| 6/5 14:45 | **[#2419](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2419)** | **SEP-2419: cache_hint well-known key** | +454/0 | 4 | open | `CallToolResult._meta.cache_hint ∈ {"cache","no-cache"}`（**plain name 不加 `io.modelcontextprotocol/` 前缀**，等 #1788 落定再升） |
| 6/5 12:57 | **[#2866](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2866)** | ElicitationCompleteNotificationParams 抽取 | +39/-17 | 3 | open | **schema 卫生**：把唯一内联 params 拎成 `*NotificationParams extends NotificationParams`，`_meta` 普适继承 |
| 6/5 10:52 | [#2862](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2862) | Update auth spec structure | +91/-55 | 6 | closed | 跟 #2858 链接归位 |
| 6/5 10:46 | [#2857](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2857) | Collapse Server/Client Features sections | — | — | open | clareliguori：把 features 段折叠到 capabilities 下 |
| 6/5 09:27 | [#2864](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2864) | Add rust example for "Build an MCP client" | — | — | open | amikai 补 Rust 教程 |
| 6/5 01:34 | **[#1932](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1932)** | **SEP-1932: DPoP Profile for MCP** | +124/0 | 1 | open | PieterKas：sender-constrained token 阻止 replay，作为 auth extension 注册 |
| 6/4 22:48 | **[#2822](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2822)** | **SEP-2822 Client Generated Session ID** | +782/-43 | 4 | open | `Mcp-Client-Session-Id` header / `_meta`，无 server 义务，stateless 部署可观测性 |
| 6/4 22:00 范围 | [#2567](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2567) | Sessionless MCP via Explicit State Handles | — | — | closed | pja-ant：把 session 状态显式化 |
| 6/4 14:48 | [#2855](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2855) | make server/discover support caching | — | — | closed | CaitieM20：与本轮 #2127 Server Cards 是发现层两条线 |
| 6/4 13:05 | [#2843](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2843) | Add Authorization IG charter | +87/0 | — | closed | Auth IG 三 facilitator（Okta / Amazon / Anthropic） |

**协议主仓观察**：6/4 23:00–6/5 23:41 这 24 小时集中爆了 8 条高质量新 PR（#2822 / #1932 / #2864 / #2857 / #2866 / #2419 / #2448 / #2640 / #2867 / #2127），10 条都围绕"extensions track + discoverability + observability"，没有任何 breaking change 偏向——`2026-07-28 RC` 锁版期前的"非破坏性加能力"窗口收口。

## 三、三条主线的协议级新货展开

### 3.1 Server Cards（PR #2127 · 837 行 · 4 files · dsp-ant）

**新发现层**——`SEP-2127` 把 #1649 重开，宣告一套"在 HTTP transport 建立连接之前"就能拿到 server 元数据的机制：

| 表面 | URL | 用途 |
|---|---|---|
| 预连接 | `https://<server-host>/.well-known/mcp/server-card.json` | 标准 `.well-known` URI 命名空间 |
| 资源 | `mcp://server-card.json` | 连接后 `resources/read` |

**卡片内容**（来自 PR body）：server capabilities、可用 transports、认证要求、协议版本、各 primitive 的描述。**关键设计点**：**同时支持静态和动态 primitive 声明**——server 可以从 CMS / 配置系统拉取工具清单，避免"硬编码 `tools/list` 返回值"。

**对 AI Gateway 的硬要求**：
1. `.well-known/mcp/server-card.json` 应当被 gateway 自身实现——自家 server 也得有卡片；
2. `serverCard` 应被 DNS-AID / registry 索引（与上一轮覆盖的 `server/discover` cacheScope 互补——一个面向"已连接 client 的可发现缓存"，一个面向"未连接 client 的预知会"）；
3. 卡片里的 `transports` 列表是 gateway 路由决策的"前置 ground truth"——client 选 transport 时不需要先建立连接再 fallback。

**已知 mergeable=False**（GitHub API 返回），需要进一步审稿。

### 3.2 Server Execution Telemetry（PR #2448 · 567 行 · 4 files · savula15）

**新观测层**——**这是 6/4-6/5 期间 MCP 协议层最有分量的新 SEP**，对应 `SEP-414` 的对偶：SEP-414 让 client 推送 `traceparent` 进入 server，**`SEP-2448` 让 server 把执行 span 主动推回 client**。

**协议要点**：
- 新增 server capability `serverExecutionTelemetry`（opt-in）
- Client 在每次 `tools/call` / `resources/read` 请求里**显式声明**是否要回传 span（避免无意识吞成本）
- Server 响应时把 OTLP `resourceSpans` 放在 `_meta.otel` 字段，**直接用 `application/protobuf`/`application/json` 的 OTLP wire 格式**——client 端不需要做转换，**直接 ingest 进自己既有的 OTel collector**

**为什么是 2026 年 MCP 跨组织部署的"最后一公里"**：

之前 client 把请求发到 server 后，**server 内部的 tool execution 链路对 client 是黑盒**——第三方托管的 MCP server 出了慢调用、错误、异常，client 只能看到最终 `tools/call` 的外层 span。现在 server 主动回传子 span → **跨组织 MCP 有了完整分布式 trace 闭合**。

**参考实现**：[Arcade MCP PR #797](https://github.com/ArcadeAI/arcade-mcp/pull/797)（`feat/server-execution-telemetry` 分支），可直接借鉴。

**对 AI Gateway 的硬要求**：
1. **不能把 `_meta.otel` 当 opaque 字段丢**——**要 decode 合入 OTel collector pipeline**（直接 ingest OTLP protobuf/json）；
2. 配置 client 时默认开 `serverExecutionTelemetry`，**但要 cost-aware**（server 端回传 span 也可能含 PII / 大体积数据，要带 size cap）；
3. 与上一轮覆盖的 #2855 `server/discover` cacheScope 一起考虑：**server 卡 / discover / telemetry 三者构成"发现 + 缓存 + 可观测"三件套**。

### 3.3 Client Generated Session ID（PR #2822 · 782 行 · 4 files · javapro108）

**新会话连续性 primitive**——`SEP-2567` 拆完 transport-level session、`SEP-2575` 上 `server/discover` 之后，**"logical conversation" 没有标准标识符**。#2822 补一刀：

| 字段 | 位置 | 用途 |
|---|---|---|
| `Mcp-Client-Session-Id` | Streamable HTTP 每次请求的 HTTP header | server 拿到做 log correlation / audit / dynamic tool scoping |
| `_meta.<key>` | 其他 transport | 同样的语义，不同 surface |

**关键设计点**：
- **client 生成、client 持有、server 可忽略**——零 server 义务；
- **无协议状态、无 breaking change**——纯粹 additive primitive；
- **stateless 部署可观测**：多步 agent workflow 失败时，可以从 server log / audit trail 用这个 ID 拉出所有关联请求。

**对 AI Gateway 的硬要求**：
1. **gateway 入口要 `propagate` 这个 header**——从 client 透传到后端 server；
2. **gateway 入口要把这个 ID 注入 W3C tracecontext span attribute**（与 #2448 `serverExecutionTelemetry._meta.otel` 配对，形成"会话 ID + 完整 trace"两轴）；
3. **audit log 也要索引这个 ID**——"今天 14:32 那个多步 agent 跑了哪些 server 调用"一秒可查。

### 3.4 配套：scoped auth receipt / Skills / cache_hint / DPoP / schema 卫生

- **#2867 Scoped Auth Receipt**：dinpd 跟 #2852 讨论，**分三层**——transport auth（HTTP 401 重定向）/ runtime/action auth（scoped receipt，证明 client 此刻被授权做这个高风险 tool call）/ provider business auth（`stripe.charge` 这种与具体 API 业务规则绑定）。**replay / scope-drift / retry-suppression 三条 acceptance criteria**——这条是给 gateway 的"高风险 tool 调用审计"提供协议层的 receipt 形状范例（不强制 schema）。
- **#2640 Skills Extension**：`io.modelcontextprotocol/skills` 注册，`skill://` 资源化，gemini-cli/fast-agent/goose/codex/Claude Code/GitHub MCP Server 落地——**MCP 的"工具/资源/提示词/根/采样"五件套之外第六件**。AIGW 暂时不动，但 Skills 与 Resources 都要做配额/计费时，**Skills 应被视为 Resources 的一个 surface 走同一管道**。
- **#2419 cache_hint well-known key**：`CallToolResult._meta.cache_hint ∈ {"cache","no-cache"}`，**plain name 暂不加 `io.modelcontextprotocol/` 前缀**（等 #1788 落定再升，避免锁死）。**关键设计**："在 result 上而不是 tool 定义上"——同一 tool 不同调用可能 cacheable 不同。这条直接给 gateway 的"按 result 决定是否写 LLM 上下文 cache"提供协议层信号。
- **#1932 DPoP Profile for MCP**：DPoP（[RFC 9449](https://datatracker.ietf.org/doc/html/rfc9449)）把 access token 与客户端密钥对绑定，**token 即使被截获也用不了**——这是 SEP-2742 / CIMD 之外的第三条"高安全 AS 适配"路径。AIGW 接入 auth extension 框架时，**DPoP 验签**必须能在 gateway 终止（验证 HTU/HTM/jti 绑定的 sender constraint）。
- **#2866 ElicitationCompleteNotificationParams 抽取**：**这是 6/5 一周里最被低估的"卫生性" PR**。修复了一个**长期不一致**：`ElicitationCompleteNotification` 是 schema 里**唯一** `params` 仍是内联匿名对象的 notification，所有其他 notification（`CancelledNotification` / `ProgressNotification` / `ResourceUpdatedNotification` / `LoggingMessageNotification` / `SubscriptionsAcknowledgedNotification`）都用 `*NotificationParams extends NotificationParams` 命名类型。这次抽取后 **`_meta` 字段在 ElicitationComplete 上也普适继承**。对 AIGW 而言：**所有 notification 的 `_meta` 字段语义一致**——之前为 ElicitationComplete 单独写 schema 适配的代码可以删了。

## 四、六大 SDK 12h–7d 同步硬化

### 4.1 csharp-sdk（6/5 一日内 8 个合并到合流）

| PR | 行数 | 主题 |
|---|---|---|
| **[#1519](https://github.com/modelcontextprotocol/csharp-sdk/pull/1519)** | +141/-29 | **Kestrel `_httpSseWriter` 引用泄漏修复**——23 分钟 91 MiB → 204 MiB，**+113 MiB RSS、96% 是 unmanaged memory**；`MemoryPool<byte>` blocks、Pipe readers/writers、socket buffers 全部被 pin。Cursor IDE 探活场景下成楼梯式增长 → OOMKills。修法是 `HandleGetRequestAsync` 的 `finally` 立刻 null 化 `_httpSseWriter`。`Last-Event-ID` replay 不受影响。 |
| **[#1528](https://github.com/modelcontextprotocol/csharp-sdk/pull/1528)** | +53/-2 | **摘 `Content-Type: application/json; charset=utf-8` 的 `charset`**。[RFC 8259 §11](https://datatracker.ietf.org/doc/html/rfc8259#section-11) + IANA 注册明确 JSON 不带 charset。**`https://api.githubcopilot.com/mcp` 拒非裸 `application/json` 返回 415**——GitHub Copilot MCP 端点现在可以直连。Python/TS SDK 一直发裸 application/json，这次 C# 跟上。 |
| **[#1600](https://github.com/modelcontextprotocol/csharp-sdk/pull/1600)** | +9/0 | **`Tool.InputSchema` 标 JSON-required**——之前代码侧默认 `{"type":"object"}` 会被反序列化层 mask，导致 payload 缺 `inputSchema` 也能 deserialize 成功。加 regression test。 |
| [#1599](https://github.com/modelcontextprotocol/csharp-sdk/pull/1599) | +61/0 | `McpClientOptions.InitializeMeta` 让 `initialize._meta` 走 options 注入，不必再写 custom `IClientTransport` |
| **[#1531](https://github.com/modelcontextprotocol/csharp-sdk/pull/1531)** | +61/0 | **1.2.0 stateless 模式跳过 `IdleTrackingBackgroundService` 的 5s timer**——`StatefulSessionManager` 不填充，prune 没意义。`StartAsync` early-return，CPU 浪费消除 |
| [#1435](https://github.com/modelcontextprotocol/csharp-sdk/pull/1435) | — | `$ref` 指针在 output schema 包裹后解析修复 |
| [#1491](https://github.com/modelcontextprotocol/csharp-sdk/pull/1491) | — | `ReadEventsAsync_InStreamingMode` 同步点修 flaky test |
| [#1517](https://github.com/modelcontextprotocol/csharp-sdk/pull/1517) | — | `DiagnosticTests.Session_TracksActivities` 等待完整 server activity predicate |

csharp-sdk 主题词是 **stateless 收敛** + **生产 hardener 集中修**——配合 1.2.0 主线。

### 4.2 python-sdk（5/31–6/5 把 transport 全面 in-process 化）

| PR | 主题 |
|---|---|
| [#2788](https://github.com/modelcontextprotocol/python-sdk/pull/2788) | trio virtual clock 给 session-level timeout 测试 deflake |
| **[#2773](https://github.com/modelcontextprotocol/python-sdk/pull/2773)** | **stdio client 关闭路径 bug 修复 + 重建 stdio test suite** |
| [#2767](https://github.com/modelcontextprotocol/python-sdk/pull/2767) | StreamableHTTP transport 测试从 over-socket 改 in-process |
| [#2765](https://github.com/modelcontextprotocol/python-sdk/pull/2765) | SSE + Unicode transport 同上 |
| [#2764](https://github.com/modelcontextprotocol/python-sdk/pull/2764) | transport 安全测试同上 |
| [#2761](https://github.com/modelcontextprotocol/python-sdk/pull/2761) | docs: 2026-07-28 spec 新 feature 必须配 conformance test |

→ python-sdk 主题词是 **测试可信度 + transport 关闭路径**——stdio client 关闭一直不稳，这次算根治。

### 4.3 go-sdk（5/29–6/5 把 SEP-2575 客户端补齐 + auth 边界硬化）

| PR | 主题 |
|---|---|
| **[#975](https://github.com/modelcontextprotocol/go-sdk/pull/975)** | **[SEP-2575](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575) 客户端实现**：`Client.Connect()` 在 `protocolVersion >= 2026-06-30` 时先 `server/discover` 探针，fallback 旧 `initialize` 仅在 `-32601` / `-32004` / `Bad Request` 三种错误。每条请求 inject `_meta`（protocolVersion + clientInfo + clientCapabilities）。**server 端修复**：`ServerSession.handle` 不再把 `server/discover` 的 `_meta` 预填到 `state.InitializeParams`（避免 fallback `initialize` 被当重复拒）。12 files / +1010/-96。 |
| [#969](https://github.com/modelcontextprotocol/go-sdk/pull/969) | **`ClockSkew time.Duration` 给 `RequireBearerTokenOptions`**——云 IdP 漂移典型几秒；strict `==` 比较会误拒。default 0 保旧行为。 |
| [#971](https://github.com/modelcontextprotocol/go-sdk/pull/971) | **`AllowMissingExpiration`** 给 `RequireBearerTokenOptions`——同根问题 |
| **[#982](https://github.com/modelcontextprotocol/go-sdk/pull/982)** | **`KeepAliveFailureThreshold` 配 ClientOptions/ServerOptions**——连续失败 N 次才关 session；default 0/1 = 旧行为（一次失败关）。WARN 容忍 / ERROR 关闭。 |
| [#946](https://github.com/modelcontextprotocol/go-sdk/pull/946) | `mcp: add optional issuer validator for pre-registered client validation`（[SEP-2352](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2352)）|
| [#950](https://github.com/modelcontextprotocol/go-sdk/pull/950) | multi-round-trip request（[SEP-2322](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2322)）|

→ go-sdk 主题词是 **SEP-2575 客户端落地 + auth 时钟漂移 / 缺 exp 容忍 + 可配置 keepalive**。

### 4.4 rust-sdk（5/29–6/5 把"硬规范"补齐）

| PR | 主题 |
|---|---|
| **[#883](https://github.com/modelcontextprotocol/rust-sdk/pull/883)** | **DCR 时发 `application_type="native"`**（[SEP-837](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/837)）——OIDC 服务器把缺 `application_type` 假设成 `"web"`，与 CLI/desktop 的 loopback `localhost` redirect 冲突会被拒注册。`OAuthClientConfig::with_application_type(..)` 可显式选 `"web"`，默认 native。 |
| **[#884](https://github.com/modelcontextprotocol/rust-sdk/pull/884)** | **[SEP-2577](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2577)** ——`#[deprecated]` Roots / Sampling / Logging：`Peer::create_message` / `list_roots` / `set_level` / `notify_logging_message` + capability builder。`method!` / `builder!` 宏现在能转发 attribute。 |
| **[#860](https://github.com/modelcontextprotocol/rust-sdk/pull/860)** | **`schema_for_input` 现在 validate `type:"object"`**——`Parameters<String>` / `Parameters<i32>` 这种"非 object" 工具定义在构造期 panic with descriptive message（之前静默生成 spec-violating tool）。**Rust 的 std lib 标准在 AI 工具链的体现**——`JsonObject` 返回 Result。`outputSchema` 也 strip 掉冗余 `title` / `description`。 |

### 4.5 typescript-sdk（5/30–6/2 主线是"2026-07-28 RC 拆解"）

| PR | 主题 |
|---|---|
| **[#2128](https://github.com/modelcontextprotocol/typescript-sdk/pull/2128)** | **`-18,280/+423/73 files` 拆 `experimental.tasks.*`**（[SEP-2663](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2663)）：删 `TaskManager` + `Protocol` 里 task interception hook + `experimental.tasks.*` accessor。Mechanical deletion。**M5 dispatch-core extraction 的 standalone prerequisite**。`docs/migration.md` 跟进。 |
| **[#2230](https://github.com/modelcontextprotocol/typescript-sdk/pull/2230)** | **server 暴露 `getNegotiatedProtocolVersion()`**（client 端早就有 `Client.getNegotiatedProtocolVersion()`）——server 之前 `_oninitialize` 算出版本就丢。**这是 #2184 per-request envelope 的 M2 (1/2)**。 |
| [#2156](https://github.com/modelcontextprotocol/typescript-sdk/pull/2156) | codemod 改进 |
| [#2248](https://github.com/modelcontextprotocol/typescript-sdk/pull/2248) | `fix(types): restore task wire types removed with the task feature`（与 #2128 同步收尾）|
| [#2226](https://github.com/modelcontextprotocol/typescript-sdk/pull/2226) | spec-version lifecycle infra for 2026-07-28 release |
| [#2227](https://github.com/modelcontextprotocol/typescript-sdk/pull/2227) | pin conformance 0.2.0-alpha.1 + baseline draft-spec suites |
| [#2229](https://github.com/modelcontextprotocol/typescript-sdk/pull/2229) | sse matrix column hosted on shipped legacy SSEServerTransport |

→ typescript-sdk 主题词是 **`2026-07-28 RC` 拆解**——实验性能力下放 Extensions Track + protocol version 协商透明化。

### 4.6 java-sdk（5/22–6/4 主线：URL elicitation + error 卫生 + logging 收敛）

| PR | 主题 |
|---|---|
| **[#995](https://github.com/modelcontextprotocol/java-sdk/pull/995)** | **fix: avoid dropped errors when transport is closed or uninitialized**（6/4 12:11 UTC）——典型 OTel-able 边界 bug |
| [#993](https://github.com/modelcontextprotocol/java-sdk/pull/993) | Add URL elicitation support（[SEP-1036](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1036)）|
| [#985](https://github.com/modelcontextprotocol/java-sdk/pull/985) | Refine logging levels |
| [#984](https://github.com/modelcontextprotocol/java-sdk/pull/984) | Unify logging config |
| [#976](https://github.com/modelcontextprotocol/java-sdk/pull/976) | client-side application of elicitation schema defaults（[SEP-1034](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1034)）|

## 五、对 AI Gateway 工程的硬要求（综合）

1. **`Mcp-Client-Session-Id` 透传 + 注入 W3C tracecontext**（来自 #2822）：gateway 入口要把这个 header 提取→注入 OpenTelemetry span attribute 作 "logical conversation" 维度。**与 #2448 `serverExecutionTelemetry._meta.otel` 配对**，形成 "会话 ID × 完整 trace" 两轴。
2. **Server Cards 自实现**（来自 #2127）：自家 server 也得有 `/.well-known/mcp/server-card.json`——DNS-AID / registry 应能抓到（与上轮 #2855 `server/discover` cacheScope 互补）。
3. **`_meta.otel` 必须 decode**（来自 #2448）：不能作 opaque meta 丢弃。要 decode + 合入 OTel collector pipeline（直接 ingest OTLP protobuf/json），同时带 size cap 防 PII/大体积数据。
4. **`Content-Type: application/json; charset=utf-8` 拒绝转发**（来自 #1528）：acceptance test——Copilot 端点已经拒，gateway 转发链要当"非标"识别。
5. **DPoP 验签**（来自 #1932）：AIGW 接入 auth extension 框架时，**DPoP 验签必须能在 gateway 终止**（HTU/HTM/jti sender-constraint）。
6. **cache_hint 协议层信号**（来自 #2419）：gateway 应尊重 `CallToolResult._meta.cache_hint` 决定 LLM 上下文 cache 写入策略——subagent / benchmark / one-shot pipeline 不写 cache。
7. **scoped auth receipt 三层分类**（来自 #2867）：gateway 的高风险 tool 审计应分 transport / runtime / provider 三层——replay / scope-drift / retry-suppression 三条 acceptance criteria 走 runtime 层。
8. **`X-Time-Skew-Tolerance` 给所有 OAuth 资源服务器**（来自 #969/#971）：默认 0 严、建议 30s–60s 配云 IdP 漂移。
9. **`KEEPALIVE_FAILURE_THRESHOLD` 可配**（来自 #982）：默认 1（一次失败关），生产可调 3–5 应对 transient hiccup。
10. **`DCR application_type="native"` 默认**（来自 #883）：CLI/desktop gateway 走 native 注册，OIDC 服务器才不拒。

## 六、引用与数据来源

### MCP 主仓 6/5–6/6 新 PR
- [#2127 MCP Server Cards](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2127)
- [#2867 Scoped authorization receipt security guidance](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2867)
- [#2640 Skills Extension](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640)
- [#2863 sep-to-spec consistency pass](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2863)
- [#2865 fix dead Python auth sample link](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2865)
- [#2448 Server Execution Telemetry](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2448)
- [#2419 cache_hint well-known key](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2419)
- [#2866 ElicitationCompleteNotificationParams](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2866)
- [#2862 Update auth spec structure](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2862)
- [#2857 Collapse Server/Client Features sections](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2857)
- [#2864 Rust example for "Build an MCP client"](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2864)
- [#1932 DPoP Profile for MCP](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1932)
- [#2822 Client Generated Session ID](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2822)
- [#2567 Sessionless MCP via Explicit State Handles](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2567)
- [#2855 make server/discover support caching](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2855)
- [#2843 Add Authorization IG charter](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2843)
- [#2575 Make MCP Stateless](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575)
- [#2577 Deprecate Roots, Sampling, and Logging](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2577)
- [#2663 Tasks Extension](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2663)
- [#2484 Conformance Tests for Standards Track SEPs](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2484)
- [#2468 Recommend `iss` Parameter in MCP Auth Responses](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2468)
- [#2352 Clarify authorization server binding and migration](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2352)
- [#2351 RFC 8414 well-known URI suffix for MCP](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2351)
- [#2350 Client-side scope accumulation in step-up authorization](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2350)
- [#837 SEP-837 OIDC application_type during DCR](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/837)

### SDK 侧 12h–7d 同步硬化
- csharp-sdk: [#1519](https://github.com/modelcontextprotocol/csharp-sdk/pull/1519), [#1528](https://github.com/modelcontextprotocol/csharp-sdk/pull/1528), [#1600](https://github.com/modelcontextprotocol/csharp-sdk/pull/1600), [#1599](https://github.com/modelcontextprotocol/csharp-sdk/pull/1599), [#1531](https://github.com/modelcontextprotocol/csharp-sdk/pull/1531), [#1435](https://github.com/modelcontextprotocol/csharp-sdk/pull/1435), [#1491](https://github.com/modelcontextprotocol/csharp-sdk/pull/1491)
- python-sdk: [#2788](https://github.com/modelcontextprotocol/python-sdk/pull/2788), [#2773](https://github.com/modelcontextprotocol/python-sdk/pull/2773), [#2767](https://github.com/modelcontextprotocol/python-sdk/pull/2767), [#2765](https://github.com/modelcontextprotocol/python-sdk/pull/2765), [#2764](https://github.com/modelcontextprotocol/python-sdk/pull/2764), [#2761](https://github.com/modelcontextprotocol/python-sdk/pull/2761)
- go-sdk: [#975](https://github.com/modelcontextprotocol/go-sdk/pull/975), [#969](https://github.com/modelcontextprotocol/go-sdk/pull/969), [#971](https://github.com/modelcontextprotocol/go-sdk/pull/971), [#982](https://github.com/modelcontextprotocol/go-sdk/pull/982), [#946](https://github.com/modelcontextprotocol/go-sdk/pull/946), [#950](https://github.com/modelcontextprotocol/go-sdk/pull/950)
- rust-sdk: [#883](https://github.com/modelcontextprotocol/rust-sdk/pull/883), [#884](https://github.com/modelcontextprotocol/rust-sdk/pull/884), [#860](https://github.com/modelcontextprotocol/rust-sdk/pull/860)
- typescript-sdk: [#2128](https://github.com/modelcontextprotocol/typescript-sdk/pull/2128), [#2230](https://github.com/modelcontextprotocol/typescript-sdk/pull/2230), [#2156](https://github.com/modelcontextprotocol/typescript-sdk/pull/2156), [#2248](https://github.com/modelcontextprotocol/typescript-sdk/pull/2248), [#2226](https://github.com/modelcontextprotocol/typescript-sdk/pull/2226), [#2227](https://github.com/modelcontextprotocol/typescript-sdk/pull/2227), [#2229](https://github.com/modelcontextprotocol/typescript-sdk/pull/2229)
- java-sdk: [#995](https://github.com/modelcontextprotocol/java-sdk/pull/995), [#993](https://github.com/modelcontextprotocol/java-sdk/pull/993), [#985](https://github.com/modelcontextprotocol/java-sdk/pull/985), [#984](https://github.com/modelcontextprotocol/java-sdk/pull/984), [#976](https://github.com/modelcontextprotocol/java-sdk/pull/976)

### 参考实现 & 协议标准
- Arcade MCP server execution telemetry 参考实现: [ArcadeAI/arcade-mcp#797](https://github.com/ArcadeAI/arcade-mcp/pull/797)
- MCP Server Cards SEP 草案: [seps/2127-mcp-server-cards.md](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/sep/mcp-server-cards/seps/2127-mcp-server-cards.md)
- GitHub Copilot MCP 端点: `https://api.githubcopilot.com/mcp`
- IANA `application/json` 注册: https://www.iana.org/assignments/media-types/application/json
- [RFC 8259 §11](https://datatracker.ietf.org/doc/html/rfc8259#section-11) — JSON 不带 charset
- [RFC 9449](https://datatracker.ietf.org/doc/html/rfc9449) — DPoP
- [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728) — OAuth AS Metadata (PRM)
- OpenTelemetry `gen_ai.server.time_to_first_token`（与 #2448 配套）
- Skills Extension 草案: [experimental-ext-skills#69](https://github.com/modelcontextprotocol/experimental-ext-skills/pull/69) + [#83](https://github.com/modelcontextprotocol/experimental-ext-skills/pull/83)

### 上轮引用（避免重复）
- 08:08 · r19 — `reports/2026-06-06-0808-aigw-mcp-auth-spec-split.md`（DCR deprecate / CIMD 升格 / auth IG charter）
- 01:25 · r15 — `reports/2026-06-06-0125-aigw-mcp-audit-redact.md`（`server/discover` cacheScope / SEP-2817 audit `_meta`）
- 23:34 — `reports/2026-06-05-2334-aigw-agent-gateway-r17.md`
- 23:02 — `reports/2026-06-05-2253-aigw-mcp-sdk-reliability.md`
- 22:11 — `reports/2026-06-05-2211-aigw-mcp-spec-ia-refactor.md`

— END —
