# Portkey Gateway · 单产品发版追踪（Round 2 · 2.0.0 蓄势期）

- **轮次**：hour-0 单产品发版追踪 · 本地时间 2026-06-06 21:33 CST（小时 21 % 7 = 0）
- **目标产品**：Portkey AI Gateway
- **本轮节奏判定**：hour-0 主题按 LiteLLM → Portkey → Envoy → Higress → Kong → Helicone → OpenRouter 轮换；本轮为 Portkey 第二次深度覆盖（首次 2026-06-05-0716）
- **核心结论**：**自 v1.15.2（2026-01-12）发布以来 5 个月内未推出新版本标签**；`2.0.0` 分支持续更新（30 commits ahead / 11 behind），`/public/` 控制台在 2.0.0 静默丢失（#1662 正在修复），多个 guardrail 与新 provider 在排队等发版。

---

## 1. 版本节奏：v1.15.2 之后 5 个月空窗

`git tag` 查询 `Portkey-AI/gateway` 最新 8 个 tag，v1.15.2 之后无任何新 release 标签（含 pre-release / RC）：

| Tag | Published (UTC) | 距今 | 关键变化 |
|---|---|---|---|
| v1.15.2 | 2026-01-12 | **146 天** | Azure Blob batches、Anthropic beta header 一致化、Qualifire guardrail、sequential guardrails 修复 |
| v1.15.1 | 2025-12-24 | 165 天 | gemini minimal reasoning effort 修复、Azure protected material / sheild prompt 检查 |
| v1.15.0 | 2025-12-23 | 166 天 | Gemini 3 Pro thinking level、Anthropic on Azure、IO Intelligence / OVHcloud / AI Badgr / Oracle provider、Anthropic advanced tool use beta、google maps grounding、Not Null plugin、Z_AI / Modal Labs provider |
| v1.14.3 | 2025-11-26 | 193 天 | google signature 修复 |
| v1.14.0 | 2025-11-07 | 212 天 | Rate limits & budgets、Prometheus + Winston 监控、Qualifire、Walled、AI Guard、MatterAI、Claude Code OAuth/Max plans、SSRF 防护 |

⚠️ **节奏异常**：与 Portkey 一贯 2–4 周一版的节奏相比（v1.14.0 → v1.14.1 → v1.14.2 间隔 ≤ 1 天），5 个月空窗明确指向团队在憋 2.0.0。`main` 分支最近一次 commit 2026-05-25（#1657 merged），最近 8 周 stats/commit_activity 仅 1 周（5 commits）有活跃——典型的「freeze for 2.0.0」模式。

---

## 2. 2.0.0 分支：30 commits ahead，5 月重启迹象明显

`compare main...2.0.0` → status: **diverged**, ahead_by: **30**, behind_by: 11。

2.0.0 头部主线在 2026-03-11~03-14 集中 merge（Lasso v3、Zscaler AI Guard、Akto、Latitude AI），4 月有零星 PR，5 月几乎停摆。**5 月 2.0.0 复活信号**（base=2.0.0，open）：

| PR | 日期 | 主题 |
|---|---|---|
| #1679 | 2026-06-03 | feat(plugins/lasso): send `source.type=portkey` for Used By attribution |
| #1678 | 2026-06-02 | Nathan/cie prototype（2.0.0 概念原型） |
| #1662 | 2026-05-20 | **fix: restore /public/ console in 2.0.0 (regression from 1.15.2)** — v1.15.2 携带 ~75 KB 自包含 HTML 控制台，2.0.0 静默丢失 |
| #1661 | 2026-05-20 | fix: relocate akto/zscaler plugins into `src/plugins/` (Linux build fix) |
| #1660 | 2026-05-20 | fix: rename `realtimeLlmEventParser.ts` to match import case (Linux build fix) |

⚠️ #1662 / #1660 / #1661 三连 Linux build 修复说明 2.0.0 的 CI 在 Linux 下有 case-sensitivity 兼容性问题，是 2.0.0 GA 的卡点。`/public/` 回归是 2.0.0 准备 GA 的关键收尾事项。

**2.0.0 已合入的关键能力**（base=2.0.0 已 merge）：External plugins + middleware support（#1563，架构层最大变化）、Zscaler AI Guard plugin（#1514）、Akto plugin（#1548）、Lasso Security v3 / Deputies API（#1549）、Latitude AI provider（#1510）、strict 参数向 Anthropic tool definitions 透传（#1542）。

---

## 3. main / 2.0.0 上未发版积累的「新能力候选」

### Guardrail 生态爆发
- **#1671 · Lakera Guard plugin** — 通过 `/v2/guard` 接入；`beforeRequestHook` prompt 筛查、`afterRequestHook` response 筛查；仅当 `pii/*` 命中时自动 redact，其它 policy 命中 block
- **#1652 · ATR (Agent Threat Rules) detection plugin** — MIT 许可的开放 agent 安全威胁规则格式；参照 `plugins/lasso/` 模式实现 `manifest.json` + handler + tests + README
- **#1669 · tool-payload-firewall guardrail** — RFC #1654 的首个实现：把 tool-call JSON arguments 扁平化，对 blocked-path 规则做 exact/wildcard 匹配，本地控制；解决 OPA payload firewall 缺位问题
- **#1670 · Veto guardrail plugin**

### 新 Provider（OpenAI 兼容协议为主）
- **#1682 · AGIone**（2026-06-05 最最新）、**#1677 · Triton Inference Server**（chat + embed）、**#1664 · Astraflow**、**#1650 · MiniMax as LLM provider**、**#1649 · SaladCloud**、**#1586 · HPC-AI**
- **#1533 · ModelsLab image generation provider**（2.0.0 open）— 2.0.0 将边界首次扩到 multimodal output

### Streaming / 运行时健壮性
- **#1681** · fix Anthropic `service_tier` forwarding
- **#1675 / #1628** · handle empty Fireworks AI stream choices
- **#1658** · fix(streamHandler): prevent V8 GC of upstream Response mid-stream（2.0.0）
- **#1551** · avoid immutable header mutation for mapped streaming responses（2.0.0）
- **#1667** · jittered retry backoff controls

### 运行时 / 配置
- **#1657** · add auth validation for public routes（2026-05-25 main merge — 上一发版前最后的安全修复）
- **#1642** · forward request metadata to CrowdStrike AIDR
- **#1540** · feat(oracle): rerank + guardrails
- **#1646** · fix(gemini): `thinkingBudget` for 2.5, `thinkingLevel` for 3+

---

## 4. 官方博客 & 产品主张同步

[Ghost CMS Blog](https://portkey.ai/blog/) 2026-04~05 共发 8+ 关键文章，与代码 PR 高度协同：

| 发布日 | 文章 | 与代码层对应 |
|---|---|---|
| 2026-05-24 | **What MCP Governance Actually Means in Production** | 引用数据 "53% MCP servers 用静态 API key / 8.5% OAuth / 79% 凭证在 env var"；Postmark-mcp rugpull 警示；4 个治理 primitive → 对应 #1671 Lakera、#1669 tool-payload-firewall、#1652 ATR、#1667 retry backoff |
| 2026-05-03 | **What's an agent gateway?** | 把 "fifteen 200s, 4 hops back" 失败归因作为论据；multi-provider / multi-step / 工具调用递归的 token bill 放大 → 对应 #1681 service_tier、#1658 GC、#1667 retry 修复 |
| 2026-04-24 | Launching Prompt Engineering Studio | 配套 #1481 Not Null plugin、Skills Registry |
| 2026-04-23 | **Introducing Skills Registry** | 重新定义 SKILL.md 在 Claude Code / Cursor / Codex 之间的同步：author → draft → review → publish → version history；与 Agent Skills 规范直接对接 |
| 2026-04-29 | What is AgentOps? | — |
| 2026-04-27 | GitHub Copilot best practices for teams | — |

> 🔍 产品主张已明确从 "LLM gateway" 转向 "**agent gateway**"：5/3 与 4/29 两文直接命名；`what-is-an-agent-gateway` 反复强调 "A standard LLM call is a transaction, agents don't behave that way"。这与 2.0.0 的 external plugins + middleware 架构升级是同一故事的两面。

---

## 5. 战术解读

### 5.1 为什么 5 个月不发版？
- **不是"放弃维护"**：`main` 持续合 PR（最近 2026-05-25），只是把发版开关掐在 2.0.0
- **典型 2.0 架构变动**：`/public/` 控制台丢失、Linux 构建 case-sensitivity、外部 plugins / middleware 引入（#1563）—— 都是 breaking change
- **集成面收口**：v1.15.x 在 1 月密集发版（v1.15.0 → 1 → 2 间隔 3 周）已把 guardrails / providers 推到 80+；2.0.0 是把这些打包成「商业 / 平台化」版本

### 5.2 对用户的建议
- **生产环境**：v1.15.2 当前最稳；如需 Lakera Guard / Veto / tool-payload-firewall，**自编译 main 风险高**（#1658 GC 修复未 GA）—— 等 2.0.0 RC
- **架构选型观察点**：2.0.0 `external plugins + middleware` 是分水岭事件，把 Portkey 从「网关 + 集成清单」推向「网关 + 插件平台」；与 Kong / Higress 插件生态打法收敛
- **关注 RFC #1654 → #1669 演化**：OPA-style payload firewall 首次落地，标志着 Portkey 从「perimeter security」往「deep agent security」走

### 5.3 与同期其它单产品对比
- **LiteLLM**：1–2 周节奏稳定，v1.81+ 在 2026 Q2 持续推 PR
- **Envoy AI Gateway**：ext_proc + external processor 模式稳定
- **Kong AI / Higress**：插件生态路线一致；Kong AI 已 GA 多个 provider
- **Portkey 2.0.0 的"external plugin"如果 GA，将成为该路线**最"开发者友好"的一个**（TypeScript 生态 + manifest.json 简单模式）

---

## 6. 数据点速查表

| 维度 | 数据 |
|---|---|
| 最新稳定版 | v1.15.2 (2026-01-12) |
| 距上一发版 | 146 天 |
| `main` 最近 commit | 2026-05-25 (PR #1657) |
| `2.0.0` 分支 ahead/behind | 30 / 11 commits |
| 5 月以来 open PR (main) | 17 个 |
| 5 月以来 open PR (2.0.0) | 6 个 |
| v1.15.x 累计 provider | 80+（Z_AI、Modal、Oracle、IO Intelligence、AI Badgr、OVHcloud、MatterAI、CometAPI 等） |
| v1.15.x 累计 guardrail 集成 | 14+（Qualifire、Akto、Zscaler、Lasso v3、Walled、f5、Javelin、Veto、Lakera、ATR、tool-payload-firewall、Asqav、Not Null、Add Prefix） |
| Skills Registry 概念首发 | 2026-04-23 博客 |
| MCP governance 关键数据 | 53% 静态 API key / 8.5% OAuth / 79% env var |

---

## 7. 风险与监控点

- **2.0.0 RC 时间窗未公开**；#1662、#1660、#1661 "修尾"PR 合并速度是 2.0.0 临近 GA 的最直接信号
- **Lakera / Veto / tool-payload-firewall 三 guardrail 同期进入**，2.0.0 将一次性引入 ~5 个新 guardrail（关注命名冲突 / 顺序问题）
- **Image generation provider（ModelsLab）首次进入**，2.0.0 边界从 LLM chat/embed 扩到 multimodal output
- **agent gateway 主张 vs 落地**：博客层已切换叙事，但代码层 external plugins（#1563）仍在 open；如 2.0.0 不带该 PR GA，叙事会与现实脱节

---

## 引用与数据来源

- Portkey Gateway Releases: <https://github.com/Portkey-AI/gateway/releases>
- Portkey Gateway Tags: <https://github.com/Portkey-AI/gateway/tags>
- Portkey Gateway Commits (main): <https://github.com/Portkey-AI/gateway/commits/main>
- Portkey Gateway compare main...2.0.0: <https://github.com/Portkey-AI/gateway/compare/main...2.0.0>
- Portkey Blog: <https://portkey.ai/blog/>
- What MCP Governance Actually Means in Production: <https://portkey.ai/blog/mcp-governance/>
- What's an agent gateway?: <https://portkey.ai/blog/what-is-an-agent-gateway/>
- Introducing Skills Registry: <https://portkey.ai/blog/skills-registry/>
- Launching Prompt Engineering Studio: <https://portkey.ai/blog/prompt-engineering-studio/>
- What is AgentOps?: <https://portkey.ai/blog/what-is-agentops/>
- Portkey Product Updates: <https://portkey.ai/product-updates>
- 关键 PR：#1682 AGIone · #1679 Lasso source.type · #1677 Triton · #1671 Lakera · #1669 tool-payload-firewall · #1662 restore /public/ · #1657 auth validation · #1654 RFC OPA · #1652 ATR · #1563 external plugins
- Release notes: [v1.15.2](https://github.com/Portkey-AI/gateway/releases/tag/v1.15.2) · [v1.15.0](https://github.com/Portkey-AI/gateway/releases/tag/v1.15.0)

> 本地生成时间：2026-06-06 21:33 CST · 文件大小 ~11.4 KB
