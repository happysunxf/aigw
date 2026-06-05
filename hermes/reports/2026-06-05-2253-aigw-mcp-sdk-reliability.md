# AI 网关深挖 · MCP Gateway 专题（2026-06-05 22:53 CST）

> **窗口**：过去 36h（2026-06-04 22:53 → 2026-06-05 22:53 CST）。**焦点**：**MCP
> 客户端 SDK 可靠性工程** —— 三个不同语种 SDK 在同一窗口期独立提交了"非协议级"
> 变更：rust-sdk 首次把 Roots/Sampling/Logging 标 deprecated（SEP-2577）、
> 同一个仓合入 OIDC `application_type=native`（SEP-837）、go-sdk 加上
> `ClockSkew` 容忍 IdP 时钟漂移。
> **不重复**：01:06/01:46/08:34/09:50/15:28/22:11 六轮 MCP 报告。
> **本地 hour % 7 = 1** → MCP Gateway 专题。

**时间锚点**：报告生成 **2026-06-05 22:53 CST**（周五，Asia/Shanghai）。
**GitHub 状态**：spec `2026-07-28-RC`（5/29）仍为最新 release tag；rust-sdk
`rmcp-v1.7.0`（5/13）未发新版；go-sdk `v1.6.1`（5/22）未发新版；conformance
`0.2.0-alpha.2`（6/3 22:27 CST）；Inspector **0.22.0**（6/4 20:34 CST，
URL-mode elicitation）。

---

## 一、本轮核心论点：MCP 1.0 之前的"静默层"在补

MCP 协议层在 5/29 已经 freeze 到 `2026-07-28-RC`，但过去 36h 客户端 SDK
集体进入"协议不动、工程化补强"的窗口期。三件事看似无关，**实际是同一
个治理哲学**：

- **rust-sdk #884 (SEP-2577)** 首次把 **Roots / Sampling / Logging** 三件套
  client capability 在编译器层标 deprecated。
- **rust-sdk #883 (SEP-837)** 在 OIDC Dynamic Client Registration 里强制带
  `application_type`，缺省 `"native"` 以匹配 CLI/desktop 的 loopback 重定向。
- **go-sdk #969** 在 `RequireBearerTokenOptions` 加 `ClockSkew` 容忍 IdP 端
  `exp` 微秒级漂移。

**对比 22:11 报告**：上一轮集中在**协议 IA 重构 + Registry 服务端 CWE-209
错误卫生**（服务侧安全工程）。本轮切到 **客户端 SDK 治理**（客户端可靠性
工程），互不重复但叙事连贯。

---

## 二、rust-sdk：首次正式 deprecate 三件套 client capability（SEP-2577, PR #884）

**PR**：[#884](https://github.com/modelcontextprotocol/rust-sdk/pull/884)
**合入时间**：2026-06-04 20:43 CST（commit `82b04a3`，**未触发 release**，
rmcp 仍停 v1.7.0 / 5/13）

### 2.1 改动核心（advisory-only，**无协议层 wire 变更**）

```
- Forward attributes through the service `method!` macros and deprecate
  `Peer::create_message`, `Peer::list_roots`, `Peer::set_level`, and
  `Peer::notify_logging_message`.
- Forward per-field attributes through the capability `builder!` macro and
  deprecate the generated `enable_roots`, `enable_sampling`, and
  `enable_logging` builders.
- Document the deprecation on the capability types and fields.
- Allow `deprecated` at the crate's own call sites so the build stays
  warning-clean, and refresh the message schema snapshots.
```

### 2.2 为什么对 AI 网关重要

**Roots / Sampling / Logging** 是 MCP "client ↔ LLM 双向桥"的**三件套**：
Roots 是 client 暴露给 server 的文件系统边界；Sampling 是 client 调 server
的 LLM 完成生成；Logging 是 client 接收 server 的结构化日志。这是 MCP "把
LLM 当成 server-side resource"的核心桥接。

标 deprecated 意味着工作组认为：**未来 LLM 与 tool 之间的桥不应再走 client
中转**，而应走更显式的 task/external 协议（参见 experimental-ext-tasks 仓
6/3 22:49 CST 还在 `qs` 升级）。

**对网关侧的影响**：
- **短期（v1.x）**：wire 不变，三件套继续工作，rust 用户会看到编译警告。
- **中期（v2.0）**：三件套可能从协议层移出或被 task 协议吸收，**网关侧的
  sampling 中转、root 文件系统白名单同步、logging 聚合 sink** 都要重设计。

这是**第一次**在 rust SDK 层看到 deprecation attribute 显式落在 capability
类型/builder 上。给 Go/Python/TypeScript SDK 打了个样本：advisory
deprecation 是一种"零 wire 风险"的协议演化方式。

---

## 三、rust-sdk：OIDC `application_type=native`（SEP-837, PR #883）

**PR**：[#883](https://github.com/modelcontextprotocol/rust-sdk/pull/883)
**作者**：Stefano Amorelli `<stefano@amorelli.tech>`
**合入时间**：2026-06-04 22:53 CST（commit `f1ef2ec`）

### 3.1 问题陈述

OIDC Dynamic Client Registration（RFC 7591）允许 IdP 决定 `application_type`。
MCP 客户端在 CLI/desktop 场景下用 **loopback 重定向**
（`http://127.0.0.1:PORT/callback`），符合 OIDC `native` 类型。但 SEP-837
之前的实现**没在请求体里带 `application_type`**，IdP 默认成 `"web"`，而
web 类型期望 `https://` 重定向 + 域名校验，**直接拒绝 loopback 客户端的
注册请求**。

### 3.2 改动

- `register_client` 始终发 `application_type`，**默认 `"native"`**（覆盖
  rust-sdk 默认行为）。
- 新增 `OAuthClientConfig::with_application_type` 让 web 客户端显式选
  `"web"`。
- 同步在 hosted client metadata document（URL-based client_id 流程）里设
  `application_type=native`，**让两种客户端身份注册路径（dynamic register
  vs metadata document）一致**。
- 配套测试覆盖序列化请求体 + config 默认值。

### 3.3 对 AI 网关的影响

这是**生产级 OAuth 网关必踩的坑**：企业 IdP（Okta/Azure AD/PingFederate）
对 `application_type` 校验比自托管 IdP 严格得多。**MCP 客户端默认不带
`application_type`，过 50% 的企业 IdP 都注册不上**。rust-sdk 把 "loopback
就是 native" 作为默认假设写死，对 go/python/ts SDK 是一个 "protocol MUST"
信号。

---

## 四、go-sdk：`ClockSkew` 容忍 IdP 时钟漂移（PR #969）

**PR**：[#969](https://github.com/modelcontextprotocol/go-sdk/pull/969)
**合入时间**：2026-06-05 18:16 CST（commit `5045d86`，**未发版**，go-sdk
仍停 v1.6.1 / 5/22）

### 4.1 改动

```go
// RequireBearerTokenOptions 新增字段
ClockSkew time.Duration
```

- 默认零值 → **保留旧严格比较**（token `exp` 一过即拒，零兼容负担）。
- 正值 → 允许 verifier 端的"远端 token 看起来 microseconds-in-the-past"也
  能接受，覆盖 CDN 边缘节点 / 多区域部署 / 云托管 IdP 时钟漂移。
- 配套测试 `TestRequireBearerToken_ClockSkew` 四种情况：fresh-accept /
  strict-expired-reject / within-skew-accept / beyond-skew-reject。

### 4.2 为什么对 AI 网关有"路标"价值

go-sdk 的策略非常工程化：**默认严格 = 不动现有行为**。给其他语言 SDK 一
个"保守默认值 + 可选放宽"的样本。**时钟漂移是分布式 OAuth 网关的真实痛
点**：云托管 IdP（Auth0/Cognito/Azure AD B2C）NTP 漂移可达 1-3 秒；CDN
边缘节点 token 校验时钟相对 issuer 常见 200-500ms 漂移；多 master IdP 集
群若 NTP 不严格同步，token `exp` 在不同 DC 看到不同值。

go-sdk 选"严格默认" + 显式 opt-in 是合理的——打开就增加 token reuse 窗口。
**对 AI 网关的建议**：
- 网关 `Authorization` 校验阶段的 **token 校验 cache** TTL 必须 ≤
  `ClockSkew` 配置的合理上限。
- 网关支持 multi-IdP（Okta + Auth0 + 自托管 Keycloak）时，ClockSkew 应
  按 IdP 单独配置。

---

## 五、python-sdk：transport 测试**进程内**重构（三连发）

- **#2764** (6/2 19:30 UTC) — transport security tests in process
- **#2765** (6/2 20:46 UTC) — SSE and Unicode transport tests in process
- **#2767** (6/3 11:45 UTC) — StreamableHTTP transport tests in process

把 stdio / SSE / StreamableHTTP 三种 transport 的集成测试**从 fork+exec 改成
asyncio 进程内调用**。这不是协议变更，是测试基础设施：减少 CI 资源消耗、
加速测试反馈、让 StreamableHTTP 测试不再依赖真实 TCP socket。

**信号**：MCP 工作组把 **StreamableHTTP 作为下一代 transport 主推**
（inspector 0.22.0 URL-mode elicitation 也走 StreamableHTTP），围绕它的测试
基础设施在被优先加固。**任何在生产环境跑 MCP StreamableHTTP 网关的团队，
都应该把这些 in-process 测试模式作为 CI 模板**——特别是在测试自己的
reverse proxy / auth middleware 时，不要 fork 真实 HTTP server，直接用
`httpx.AsyncClient` 进程内测。

---

## 六、Inspector 0.22.0：URL-mode elicitation

**Release**：Inspector **0.22.0**（2026-06-04 12:36 UTC, PR #1428）
**主功能**：URL-mode elicitation（PR #1423, 6/4 01:09 UTC 合）

Elicitation 是 MCP 让 server 主动向 user 要确认/输入的能力（"我可以调用
这个外部 API 吗？"），原模式是 in-band JSON 弹窗。**URL-mode 改成 server
返回一个 URL，client（Inspector）打开浏览器跳转**——本质是 **out-of-band
authorization UI delegation**，让 server 不必实现完整 modal UI。

这是 MCP 0.22 内**第一个真正意义的多 channel elicitation**——把"向人类
请求确认"这个动作从"in-channel 强耦合"变成"out-channel 浏览器流"，更接近
OAuth consent screen 的 UX。**对 AI 网关**：
- 网关如果代理 MCP server 的 elicitation，需要决定 URL 是要 enforce 走特定
  domain（防钓鱼）还是 allow-list 任意 URL。
- 网关如果做 elicitation 审计，要看清 URL 字段因为它代表"被请求的外部
  action"。

---

## 七、conformance 0.2.0-alpha.2：version-aware MockServer

**Release**：conformance **0.2.0-alpha.2**（6/3 22:27 CST, PR #328）
**主功能**：
- **PR #318** (6/1) — version-aware Connection abstraction for **server** scenarios
- **PR #321** (6/3) — version-aware MockServer abstraction for **client** scenarios

把 spec schema 类型按 spec version vendor 进仓，让一个 MockServer 能在
v0 / v1 / draft 之间切换。**信号**：conformance 套件进入"**多 spec 版本
基线测试**"阶段。AI 网关的**自身 conformance test** 应该接这个套件，而
不是自己造轮子。

---

## 八、Spec 端"小动作"：editorial only

spec main 在 22:11 之后只多了一个**纯文档编辑** commit（6/5 20:31 CST,
`6d44151`）：把 `## Message Patterns` 改回 `### Message Patterns`（作为
"Messages" 的子标题）。这是合入 #2862 (auth spec 拆页) 之后的目录层级
调整，**非协议变更**。

spec 已经实质 freeze 到 `2026-07-28-RC`——6/2 之后合入 main 的都是文档/链
接修复、editorial。**未来 4 周（截至 7/28 RC → stable）的窗口期是 SDK
治理期**。

---

## 九、对 AI 网关的本周三件事

1. **如果对接 rust-sdk**：开 compiler warning 监控，**`#884` deprecation
   warning 是"v2 路径会断"的早期信号**。
2. **如果做 OIDC client registration 代理**：默认透传 `application_type`，
   把 loopback client 强制标 `native`（rust-sdk PR #883 是个参考实现）。
3. **如果跑 StreamableHTTP 流量**：借鉴 python-sdk #2764/65/67 的
   in-process 测试模式做 reverse proxy regression 套件。

---

## 引用与数据来源

- rust-sdk #884 (SEP-2577)：https://github.com/modelcontextprotocol/rust-sdk/pull/884
- rust-sdk #883 (SEP-837)：https://github.com/modelcontextprotocol/rust-sdk/pull/883
- rust-sdk `82b04a3`：https://github.com/modelcontextprotocol/rust-sdk/commit/82b04a3
- rust-sdk `f1ef2ec`：https://github.com/modelcontextprotocol/rust-sdk/commit/f1ef2ec
- go-sdk #969 (ClockSkew)：https://github.com/modelcontextprotocol/go-sdk/pull/969
- go-sdk `5045d86`：https://github.com/modelcontextprotocol/go-sdk/commit/5045d86
- python-sdk #2764/2765/2767 (in-process tests)：https://github.com/modelcontextprotocol/python-sdk/pull/2767
- Inspector 0.22.0 / PR #1428：https://github.com/modelcontextprotocol/inspector/pull/1428
- Inspector URL-mode elicitation / #1423：https://github.com/modelcontextprotocol/inspector/pull/1423
- conformance 0.2.0-alpha.2 / #328：https://github.com/modelcontextprotocol/conformance/pull/328
- conformance #321 (MockServer)：https://github.com/modelcontextprotocol/conformance/pull/321
- spec `6d44151` (editorial)：https://github.com/modelcontextprotocol/modelcontextprotocol/commit/6d44151
- spec `2026-07-28-RC` tag、registry #1338：参考 22:11 报告

报告生成于 2026-06-05 22:53 CST，下一轮预计 23:23 CST。
