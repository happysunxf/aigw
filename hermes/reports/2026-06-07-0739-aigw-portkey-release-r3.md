# Portkey Gateway 单产品发版追踪 · round 3

- **时间**：2026-06-07 07:39 CST（local date，星期日）
- **主题**：单产品发版追踪（hour_mod_7 = 0）— Portkey
- **前次专题**：2026-06-06 21:33 `portkey-release-r2`（间隔 ~10h）

---

## TL;DR

Portkey Gateway 自 2026-01-12 v1.15.2 以来仍**无新 release tag**（**146 天空窗期**）。本次 round 3 关键发现：

1. **2.0.0 分支正式「冷冻结」**：自 2026-03-14 PR #1548（akto plugin merge）以来 **84 天无 commit、0 PR merged into 2.0.0**（仅 1 PR closed，大概率 stale bot）。与 r2（6 天前）`ahead:30 / behind:11` **完全反转** 为 `ahead:11 / behind:30` —— main 快速独立演化，2.0.0 不再吸 main。
2. **main 是事实上的主干**：89/100 open PRs base=`main`，11 base=`2.0.0`；5 月 #1657（public routes 鉴权 + provider options 脱敏 + admin token 移除默认 + 日志 fail-closed）是 main 上安全硬化主轴。
3. **2.0.0 仍有低频动作**：6/2 #1678「Nathan/cie prototype」（+227 LOC, 6 files, body 写「data plane half of CIE login」——CIE 极可能 = Conductor Identity Engine，4/17 Conductor×Portkey 合作同期）；6/3 #1679 lasso `source.type=portkey` attribution。
4. **6 月初 main 新动作**：#1682 AGIone provider、#1684「New files from Fly.io Launch」（Fly.io 一键部署模板入仓）。
5. **博客 5/25 后沉默 ~13 天**，与代码空窗叠加 = 团队处于整合期。

---

## 1. 2.0.0 冷冻结的硬证据

| 指标 | 数值 |
| --- | --- |
| 2.0.0 head SHA | `8febc1dc1d85` |
| 2.0.0 最后 commit | 2026-03-14 12:35:49 UTC |
| 距今天数 | **84 天** |
| 2026-03-15~06-07 merged into 2.0.0 | **0** |
| 同期 closed 2.0.0 PR | 1（stale bot 概率大） |
| open PR base 分布 | main=89, 2.0.0=11 |
| r2 时 `compare 2.0.0...main` | ahead=30, behind=11 |
| **本次 `compare 2.0.0...main`** | **ahead=11, behind=30**（方向反转） |

**解读**：main 6 天净增 19 个独有 commit，2.0.0 不再追赶。2.0.0 实际**降级为 Conductor SSO 集成的保留分支**，绝大多数 1.16.x 候选工作在 main。

---

## 2. main 5-6 月关键信号

### 2.1 #1657「public routes 鉴权」4 件套（5 月 main 最重要的安全硬化）

按时间顺序：

1. **4e43b19** 5/19 `add auth validation for public routes`（核心 patch）
2. **e457022** 5/19 `remove admin token default`（**删除默认 admin token**）
3. **9bcaee4** 5/19 `disable logs when admin token not set`（**admin token 缺失 → 日志 fail-closed 关闭**）
4. **c9ee943** 5/19 `redact provider options in logs`（provider options 含 API key，默认 redact）
5. **669825c** 5/25 Merge PR #1657

**核心思想**：fail-closed 默认值。`disable logs when admin token not set` 与 OpenRouter 5/29 Guardrails 选 402/404 而非 403（防 enumeration）是 2026 H1 网关产品共识——**fail-closed 默认**。

### 2.2 #1578（3/25）header forwarding 修复

`do not let people forward x-portkey-forward-headers to prevent infinite looping`——反向代理场景下构造 `x-portkey-forward-headers` 触发 request self-loop。#1578 与 #1657 间隔 55 天，**Portkey 5/19 才意识到 #1578 关联面是 public routes 默认无鉴权**。

### 2.3 6 月初 main 新增（最近 4 个 PR）

| PR # | 日期 | 标题 |
| --- | --- | --- |
| #1684 | 06-06 | New files from Fly.io Launch（部署模板） |
| #1682 | 06-05 | provider: add AGIone |
| #1681 | 06-03 | fix Anthropic service_tier forwarding |
| #1677 | 06-01 | triton embed + chatComplete |

---

## 3. open PR 30 个分类（base=main 优先）

| 分类 | 数量 | 代表 PR |
| --- | --- | --- |
| 新 guardrail plugin | 5 | #1652 ATR / #1644 Cato / #1647-#1637-#1671 Lakera / #1670 Veto / #1669 OPA payload firewall |
| 新 provider | 5 | #1682 AGIone / #1677 Triton / #1664 Astraflow / #1650 MiniMax / #1649 SaladCloud |
| 流健壮性 | 3 | #1658 V8 GC mid-stream / #1675 Fireworks 空 choices / #1638 Fireworks 空 chunks |
| 部署/console | 2 | #1684 Fly.io / #1662 restore /public/ console（2.0.0 regression） |
| 2.0.0 修补 | 2 | #1660-61 Linux case-sensitivity |

**5 月节奏观察**：5 guardrail + 5 provider + 3 流修补 + 部署 = v1.16.0 候选规模**等同 v1.15.0 整版**。Lakera Guard 3 次 PR（#1647→#1637→#1671）= 标准三段迭代，**Lakera 是 5 月 Portkey 团队重点支持的 guardrail vendor**。

---

## 4. 2.0.0 上 6 月低频动作

| PR # | 日期 | 作者 | 标题 | 体量 |
| --- | --- | --- | --- | --- |
| #1679 | 06-03 | orgersh92 (Lasso Security) | lasso `source.type=portkey` Used By attribution | +13 -1 |
| #1678 | 06-02 | smcwhtdtmc (Portkey 员工) | Nathan/cie prototype | +227, 6 files |

#1678 body 原文：「**Quick draft PR for the data plane half of CIE login. Note the base branch!**」—— smcwhtdtmc 主动强调 base=2.0.0 暗示「应走 2.0.0」的特殊 PR（与 89% PR 走 main 相反）。`CIE login` + 4/17 Conductor×Portkey 集成 + smcwhtdtmc 是 Portkey 员工 → **CIE = Conductor Identity Engine 内部代号**，**2.0.0 是 Conductor/Enterprise SSO 集成的承载体**。

#1679 在 /gateway/v3/classify payload stamp `source.type=portkey`，驱动 Application API Keys 列表的 "Used By" badge。无 backward compat 风险。

---

## 5. 博客层信号

RSS 最近 5 条：5/25「MCP Governance」/ 5/4「What's an agent gateway」/ 4/29「AgentOps」/ 4/27「GitHub Copilot best practices」/ 4/24「Who owns Claude Code」。

**5/25 之后 ~13 天无新博客**。5/25「What MCP Governance Actually Means in Production」核心论点：
- 53% MCP server 用静态 API key（Astrix Security state-of-mcp 2025）
- 8.5% 用 OAuth（2025-03 MCP spec 增补，仍 optional）
- 79% 凭证存环境变量
- 引用 postmark-mcp rugpull 事件

**4 governance primitives** = Trusted registry / Centralized authentication / Runtime policy enforcement / Audit logging

**与 Conductor×Portkey 4/17 + #1678 CIE SSO + #1669 OPA payload firewall + #1652 ATR plugin 形成「2.0.0 = Conductor/MCP governance 平台」产品闭环**。

---

## 6. 安全/合规态势

**GitHub Security Advisories**：1 条 = 2025-12-01 medium SSRF in Custom Host。**过去 6 个月 0 critical、0 high 公开 CVE**——与 LiteLLM 6 月连发 2 critical + 3 high 形成鲜明对比。

**「清净」的代价**：
- #1657 4 件套是 Portkey 团队**自行发现并修复的未公开漏洞**
- 5/19 #1657 修复**未发 CVE 公告**
- **生产自部署 v1.15.2 用户的实际暴露期**：v1.15.2 发布 2026-01-12 → #1657 merge 2026-05-25 = **133 天**
- 暴露窗口：admin token 未修改 + 日志开启 + provider options 写入日志 = **provider API key 长期泄漏到日志文件**

---

## 7. 横向对比（5-6 月）

| 维度 | Portkey 1.15.2 | LiteLLM 1.87.1 | Envoy AI GW b1869 | OpenRouter |
| --- | --- | --- | --- | --- |
| 距上次 release | **146 天** | 3 天 | 3 天 | 7 天 |
| 5-6 月 critical CVE | 0 公开 | 2 critical + 3 high | 0 | 0 |
| MCP governance | 5/25 博客 | 6/4 oauth2 playground | 6/4 OAuth Token Exchange | 5/29 Guardrails 4 件 |
| 自部署 readiness | v1.15.2 中等风险 | 1.87.1 minimum | 持续更新 | 不可自部署 |

**Portkey 在 release cadence 上落后 OpenRouter 25x、LiteLLM/Envoy 50x**。但**安全 CVE 数 = 0** 是反向优势——前提是自部署用户及时 cherry-pick #1657。

---

## 8. 与 r1/r2 报告的差异（delta）

r1：2026-06-05 07:16 `portkey-release`
r2：2026-06-06 21:33 `portkey-release-r2`

**r3 相对 r2 的关键修正**：

| r2 结论 | r3 修正 |
| --- | --- |
| 5 月 2.0.0 复活迹象（#1660-62 / #1678-79） | 2.0.0 **84 天冷冻结、0 PR merged** |
| P-1「#1563 三件套 = GA 临近」 | #1563 仍 open，**GA 信号未现** |
| P-2「#1654→#1669 OPA 路径监控」 | #1669 仍 open（一致），但 Lakera 落地 (#1671) 才是新主轴 |
| P-3「v1.15.2 不动等 2.0.0」 | **#1657 4 件套暴露 133 天，应升级 v1.16.0** |
| P-4「agent gateway 主张 vs plugins 落地」 | 2.0.0 转 Conductor SSO 分支后「agent gateway」叙事在 2.0.0 GA 上脱节风险更高 |

**r3 新信号**：#1657 4 件套（r2 未识别为安全主轴）/ #1678 CIE SSO（r2 仅识别为 prototype）/ #1684 Fly.io 模板 / 2.0.0 84 天无 commit。

---

## 9. AIGW 落点新增 6 条（累加 96 条）

- **(P-1)** Portkey v1.15.2 自部署应等 v1.16.0 GA（cherry-pick #1657 4 件套），发布即升。**不要等 2.0.0**。
- **(P-2)** 日志配置模板强制 `redact_provider_options=true` + 显式设置 admin token，不依赖默认值。
- **(P-3)** v1.16.0 启动强制 admin token 检查，IaC/Helm values 需提前注入 secret。
- **(P-4)** Conductor SSO 集成（#1678 CIE）可能仅在 SaaS 模式可用，自部署用户不期待。
- **(P-5)** v1.16.0 候选规模 = 5 provider + 5 guardrail + 3 流修补 = 等同 v1.15.0 整版，Portkey 跳过 2.0.0 GA 走 1.16.0 是合理路径。
- **(P-6)** r2 报告「2.0.0 GA 临近」判断需修正：2.0.0 实际转为 Conductor SSO 保留分支，GA 主体工作落在 main 上的 1.16.0。

---

## 引用与数据来源

1. GitHub Releases: `https://api.github.com/repos/Portkey-AI/gateway/releases?per_page=8`
2. compare 2.0.0...main: `https://api.github.com/repos/Portkey-AI/gateway/compare/2.0.0...main`
3. 2.0.0 branch head: `https://api.github.com/repos/Portkey-AI/gateway/branches/2.0.0`
4. main commits: `https://api.github.com/repos/Portkey-AI/gateway/commits?sha=main&per_page=20`
5. open PRs: `https://api.github.com/repos/Portkey-AI/gateway/pulls?state=open&per_page=100`
6. Security Advisories: `https://api.github.com/repos/Portkey-AI/gateway/security-advisories`
7. search 2.0.0 PR merged 03-15..06-07: `https://api.github.com/search/issues?q=repo:Portkey-AI/gateway+is:pr+base:2.0.0+merged:2026-03-15..2026-06-07`
8. PR #1678 body: `https://api.github.com/repos/Portkey-AI/gateway/pulls/1678`
9. PR #1679 body: `https://api.github.com/repos/Portkey-AI/gateway/pulls/1679`
10. PR #1657 merge: `https://api.github.com/repos/Portkey-AI/gateway/commits/669825c`
11. Portkey 2.0.0 README: `https://raw.githubusercontent.com/Portkey-AI/gateway/2.0.0/README.md`
12. Portkey blog RSS: `https://portkey.ai/blog/rss/`
13. 5/25 博客: `https://portkey.ai/blog/mcp-governance/`
14. 5/4 博客: `https://portkey.ai/blog/what-is-an-agent-gateway/`
15. r2 报告: `hermes/reports/2026-06-06-2133-aigw-portkey-release-r2.md`
16. r1 报告: `hermes/reports/2026-06-05-0716-aigw-portkey-release.md`
17. local time: `date`（2026-06-07 07:39 CST）
