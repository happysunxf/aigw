# AI 网关持续深挖 · Agent Gateway 专题 · 第 17 期

> **抓取时间**：2026-06-05 23:34 CST（UTC 2026-06-05 15:34）
> **抓取来源**：GitHub Issues API（agentgateway/agentgateway #1398 / #1405 / #1334 / #324）+ iracic82 5/4 进展贴 + #1018 A2A routing 旁路
> **主题索引**：cron 2/9 → Agent Gateway（multi-agent 编排 / trace 调试 / 成本归因）
> **本轮切入**：前 4 期（02:26 / 09:13 / 16:18 / 16:49）把"v1.3 协议 + 工程横切面 + 成本治理漏洞"讲透，本期下沉到**三条尚未合并的设计性 issue**，把 agent 治理纵深从「LLM token 治理」推进到「**Tool/Memory 预算 + 信任根 + 动态发现**」三件套。

---

## 一、本期一句话总结

agentgateway 的开放 issue 池里，3 月 24–30 日集中冒出的三条设计性 ticket（#1334 / #1398 / #1405）共同勾勒出 v1.3 之后的下一站蓝图：**把网关从"LLM 流量的代理"升级成"agent 集群的策略边界"**——既要给 Tool / Memory 调用也加 Key Budget（#1398，marcellodesales 提案），又要给所有 A2A/MCP 流量加 Ed25519 信任中间件（#1334，FransDevelopment 提案），还要在 DNS 层做去中心 agent 发现（#1405，iracic82 设计 + 5/4 给出 **0 核心改动的 xDS sidecar 实现 v0.3.0**）。**这一期不是新发版追踪，是看设计姿态。**

---

## 二、本期三件大事

### 2.1 #1398 · Key Budgets 应当覆盖 LLM / Tools / Memory 三大 Agentic Pillar

| 字段 | 值 |
|---|---|
| 状态 | **open**，无标签，0 👍 |
| 提交人 | marcellodesales（同一作者同期建了 `agentic-oauth-platform` 仓库） |
| 创建 / 更新 | 2026-03-30 / 2026-03-30 |
| 评论 | 2 条（howardjohn 反问 + 作者自答） |

**Issue 核心论点**（直引）：

> "Agents will always depend on the tokens. Are those tokens governed by the Token Budget system?"

提出把 **Key Budget Interface** 注入到 agentgateway，理由是：
- LiteLLM 已经有 virtual key + budget 的实现，agentgateway 作为 A2A 协议边界应该能"插"进去
- "Dynamic OAuth tokens" 在 agent 调用外部服务时大量出现，**网关需要看得到这些 token 的生命周期**（这点与 #2088 OAuth ID-JAG 已经在做的方向完全一致）
- 引用其个人项目 [janee](https://github.com/rsdouglas/janee)（secrets）和 [agentic-oauth-platform](https://github.com/marcellodesales/agentic-oauth-platform) 作为参考实现

**howardjohn（核心 maintainer）回复摘录**：

> "Agentgateway can certainly handle injecting outbound API credentials… but is there something related to budgets ($$/token) or just keys?"

marcellodesales 进一步澄清：是**限流 + 预算**，需要从"underlying Token Platform"控制。

**和历史的衔接**：r15 期（16:18）刚讲过 LiteLLM 1.87.1/1.86.4 GHSA-q775 修补——把 LLM 的 budget ceiling 漏洞堵住了。**#1398 是把同一套治理逻辑从"LLM API key"扩展到"Tool API key + Memory 操作 quota"**，是纵深方向。

### 2.2 #1405 · DNS-AID 动态发现：从 4 月被驳回到 5 月 sidecar 路径跑通

| 字段 | 值 |
|---|---|
| 状态 | **open**，labels: `design`, `needs-decision` |
| 创建 / 更新 | 2026-03-30 / **2026-05-04**（一个月内有实质进展） |
| 评论 | 2 条（howardjohn 初始质疑 + iracic82 v0.3.0 进展） |

**问题陈述**：agentgateway 当前只在两种模式注册 backend——`config.yaml` 静态（standalone）/ xDS 推送（K8s controller）。**没有动态发现机制**——每个新 agent 都得改配置或 CRD。

**提案**：用 [DNS-AID](https://github.com/infobloxopen/dns-aid-core)（IETF draft `draft-mozleywilliams-dnsop-dnsaid`）的 SVCB 记录（RFC 9460），命名约定：

```
_{agent-name}._{protocol}._agents.{domain} SVCB 1 target.example.com. alpn="mcp" port=443
```

新 backend 类型 `dns-aid` 在 startup 和 `refresh_interval` 周期内：
1. 查 `_index._agents.{domain}` TXT 索引
2. 对每个 agent 查 SVCB 记录
3. 提取 endpoint + port + protocol (alpn) + capability URI
4. 把发现的 agent 注册为 backend（MCP target 或 A2A backend）
5. 消失的从 DNS 里检测后下线

**关键转向 —— howardjohn 4 月回复的拒绝理由**：

> "DNS-AID 没有 adoption 的足够证明… 和 DNS-AID 类似的"next big thing"在 agentic 空间还有 10 个，我们无法每个都支持。"

**5 月 4 日 iracic82 的反手牌 —— Option B sidecar 路径跑通**：

- **零核心改动**：`ghcr.io/iracic82/dns-aid-translator:0.3.0` 在外部做 SVCB → Envoy v3 ADS Delta 翻译，agentgateway 看到一个"普通 xDS source"
- **两种部署形态并存**：
  - **Standalone**：translator 就是 xDS 源（用户没有其他 controller 时）
  - **Coexist**：translator 不走 xDS，直接重写静态 config（kgateway 之类已占位时）
- **生产级 checklist**：mTLS 加密 xDS 流 + `/healthz` `/ready` + Prometheus `/metrics` + graceful SIGTERM + non-root 容器 + 79 unit tests + 端到端覆盖 publish/unpublish/多 agent 独立/translator 重启/gateway 重启
- **机制与 spec 解耦**：SVCB → xDS 的翻译器模式可以复用到任何"在 zone 内发布 SVCB 描述 MCP"的场景
- **PR-ready 示例**：[`specs/001-standalone-xds-translator/upstream-pr/examples/dns-aid`](https://github.com/iracic82/AgentGateway/tree/main/specs/001-standalone-xds-translator/upstream-pr/examples/dns-aid) — 一个 example 目录 + 一段 README，是"最小占地面积"
- **讨论来源**：Solo.io agentgateway Discord 频道 + iracic82 在 issue 评论里贴的 [Discord 链接](https://discord.com/channels/1357069518689534073/1357069518689534076/1498722398113890355)

**这是 cron 任务里值得记录的一个范式转变**：当 maintainer 拒绝 native 实现时，社区贡献者通过"外部 sidecar 复用现有 xDS 协议"绕开 NIMBY 阻力——同时让 design debate 不阻塞 shipping。

### 2.3 #1334 · A2A/MCP 流量的 Ed25519 信任中间件

| 字段 | 值 |
|---|---|
| 状态 | **open**，无标签，0 评论 |
| 创建 | 2026-03-24 |
| 提案人 | FransDevelopment（同时维护 [Open Agent Trust Registry](https://github.com/FransDevelopment/open-agent-trust-registry)） |

**Gap 描述**：

> "Agents calling through the gateway today are authenticated at the transport level (TLS, API keys), but there's no verification of *which runtime issued the agent* or *whether that runtime is a known, non-revoked entity*."

**提案**：在 agentgateway 加中间件层，校验 [Open Agent Trust Registry (OATR)](https://github.com/FransDevelopment/open-agent-trust-registry) 颁发的 Ed25519 签名 JWT：

- 客户端在 `X-Agent-Attestation` 头里带签名 attestation
- 网关查 OATR 清单（本地缓存 + 自动刷新）验签
- 有效 → 转发时附 verified identity metadata
- 无效/缺失 → 可配置策略（拒绝 / 降级信任等级 / 仅记录）

**关键引用**：

> "The registry has **7 active issuers**, the manifest is Ed25519-signed, and verification is a local operation (no external API calls in the request path). The [Agent Identity Working Group](https://github.com/corpollc/qntm/issues/5) has ratified three specs (QSP-1 envelope, DID Resolution, Entity Verification) with cross-implementation conformance tests across 6 independent projects."

**与 #1405 的天然协同**（作者自己在 issue 里写明）：

> "DNS-AID provides DNSSEC-based trust verification for agent endpoints — cryptographic proof that the DNS record hasn't been tampered with. This complements the auth/RBAC work agentgateway already has."

也就是说 **DNSSEC + Ed25519 attestation = 双层信任根**：DNS 解决"endpoint 是谁"，attestation 解决"调用这个 endpoint 的 runtime 是谁、是否被吊销"。

---

## 三、补刀 · #324 Playground JWT 缺失 — 一个 9 个月没修的小坑

| 字段 | 值 |
|---|---|
| 状态 | open · 0 评论 · 创建 2025-08-17 |
| 痛点 | 启用 `jwtAuth.mode: strict` 后，Playground 浏览器请求**不发送 JWT**，A2A conversation 路由失败 |

这条 issue 本身不重要，但它说明：**agentgateway 的"网关"语义在控制台 / Playground 场景下还没有闭合**——gateway 验证策略只对外来调用生效，对自家 UI 缺少 ambient credential。

对照 v1.3.0-alpha.1 已经把 A2A 升成 first-class backend type，**控制台 / 工具链侧的"agent 调用 agent"还没把同一套 JWT 通路走顺**。这是 1.3 GA 前的明显债务。

---

## 四、本期信号 → 趋势的三段论

| 维度 | 现状（v1.2.x / 1.3.0-alpha.1） | 提案方向（#1334 / #1398 / #1405） | 时间表推测 |
|---|---|---|---|
| **身份 / 信任** | Transport 层（TLS + API key） | Runtime-attestation（Ed25519 attestation + OATR 清单）+ DNSSEC | v1.4–v1.5 区间 |
| **成本 / 预算** | LLM virtual key budget | LLM + Tools + Memory 三大 Agentic Pillar 统一 Key Budget Interface | v1.3.x 后续 patch 就有空间 |
| **发现 / 路由** | 静态 config.yaml + xDS | 静态 + xDS + DNS-AID（sidecar 形态先落地） | 6–9 个月内 sidecar 路径可能 GA |
| **UI / Playground** | 强制走严格 JWT 时 Playground 失败 | 缺 ambient credential / dev override | 1.3 GA 必修 |

**最值得记的一句话**：agentgateway 的下一站不是"加更多协议"，而是把现有协议**的治理面**补齐——预算（cost）、信任（trust）、发现（discovery）这三块在 LLM 网关时代是空白。

---

## 五、给工程实践者的 takeaway

1. **如果你已经用了 agentgateway**：
   - v1.3-alpha.1 A2A backend 试通以后，**别忘了在 config 里同时配 `a2a:` policy 和 `jwtAuth:`**，否则 Playground 调试会卡 #324 那个坑
   - 关注 iracic82 5/4 的 sidecar 路径——它**不阻塞 agentgateway 主线发版**，可以先在自己环境跑起来验证 DNS-AID 是不是适合你的 agent 拓扑

2. **如果你在选型 A2A / MCP 网关**：
   - 这三条 issue 提示一个判断标准：**该网关是否同时回答"谁可以调（trust）、调到什么程度（budget）、怎么发现新 agent（discovery）"**
   - LiteLLM 已经把 budget 答到 LLM 这一层；agentgateway 在往 Tools/Memory 推；DNS-AID sidecar 答的是 discovery。**没有一家目前三条都答满**

3. **如果你是 maintainer**：
   - iracic82 的 Option B 是社区绕开"design 决策僵局"的好范本——**把"是否合并到 core"和"是否值得存在"解耦**，让 spec/deployment 先行

---

## 六、引用与数据来源

- agentgateway/agentgateway Issue #1398 — Key budgets for any Agentic Pillar (LLM, Tools, Memory): https://github.com/agentgateway/agentgateway/issues/1398
- agentgateway/agentgateway Issue #1405 — feat: DNS-based agent discovery via SVCB records (DNS-AID): https://github.com/agentgateway/agentgateway/issues/1405
- agentgateway/agentgateway Issue #1334 — Trust verification middleware for A2A/MCP traffic: https://github.com/agentgateway/agentgateway/issues/1334
- agentgateway/agentgateway Issue #324 — JWT token is required but missing when testing the A2A agent in the Playground: https://github.com/agentgateway/agentgateway/issues/324
- iracic82 进展贴 / AgentGateway 仓库（DNS-AID sidecar v0.3.0）: https://github.com/iracic82/AgentGateway
- iracic82 v0.3.0 release: https://github.com/iracic82/AgentGateway/releases/tag/v0.3.0
- DNS-AID 核心仓库: https://github.com/infobloxopen/dns-aid-core
- IETF draft: https://datatracker.ietf.org/doc/draft-mozleywilliams-dnsop-dnsaid/
- Open Agent Trust Registry: https://github.com/FransDevelopment/open-agent-trust-registry
- Agent Identity Working Group (QSP-1 / DID / Entity Verification): https://github.com/corpollc/qntm/issues/5
- marcellodesales/janee (secrets abstraction): https://github.com/rsdouglas/janee
- marcellodesales/agentic-oauth-platform: https://github.com/marcellodesales/agentic-oauth-platform
- 历史同期: 2026-06-05-1649-aigw-agent-gateway-r16.md（横切面: 可观测/policy/identity 同期 PR 群）
- Solo.io agentgateway Discord 频道（#1405 讨论来源）: https://discord.com/channels/1357069518689534073/1357069518689534076/1498722398113890355

> 本期未涉及任何 token / 凭证明文；所有数据来自公开 GitHub Issues API。
