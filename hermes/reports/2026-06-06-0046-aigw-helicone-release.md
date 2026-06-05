# Helicone AI Gateway 深度追踪 (2026-05 ~ 2026-06-06)

> 轮次：hour=0 主题「单产品发版追踪」 · 本期聚焦：**Helicone**
> 报告时间：2026-06-06 00:46 CST（本地）
> 数据窗口：2026-03 ~ 2026-06-06，覆盖 GitHub main、blog、status page、官方文档

---

## 0. 一句话总结

Helicone 在过去 90 天没有再发 release tag（最近一次 `v2025.08.21-1` 停在 2025-08-21），但仓库主干在 5 月 14–18 日经历了一场**长达 4 天的观测层降级**（AWS 误锁 Bedrock API key 致整个账号被冻结），并被同期三个修复 PR 牵出两条**潜在的结构性脆弱**：(1) bifrost 前端站点**已 2 个月无法成功生产部署**，(2) 一行 debug log **让 CloudWatch 单月烧掉 \$22,475**。期间官方还把整站文档迁到 Mintlify、AI Gateway 入口 `ai-gateway.helicone.ai` 持续在线（HTTP 405，方法层正常）。

---

## 1. 发版节奏：仓库「无 tag，但 main 在动」

| 项 | 数值 | 来源 |
|---|---|---|
| 最近 release | `v2025.08.21-1`（2025-08-21 18:47 UTC） | GitHub Releases API |
| 与本报告间隔 | 285 天未发版 | 时间差 |
| main 最近 commit | `094b210b` 2026-05-18 23:17 UTC | `commits?per_page=1` |
| 5/18 当天 merge 数 | 5 个（incident 处理集中批） | PR 列表 |

社区把 release 节奏从「日级 tag」切到「main 直发 + Vercel 自动部署」是 GitHub Actions 时代的常见优化，但**事故期没有任何 tag 也没有任何 hotfix 分支**——一旦 main 退化，没有可快速回滚的「已知好版本」可钉，这点在下面 #3 会再戳到。

---

## 2. 5/14–5/18 AWS 账号被误锁：4 天观测降级，proxy 没事

来源：创始人 Cole Gottdank 5/18 发的公开 incident post（**`/blog/aws-account-incident`，不显示在 blog 列表**，仅从站内 banner 跳转）。

### 2.1 时间线

- **5/14 (周四)** — AWS 把 Helicone 的一个 **Bedrock API key** 标记为「possibly compromised」，连带**整个 AWS 账号被锁定**。
- **5/14–5/18** — ECS task 起不来，**日志摄入和 dashboard 后端全挂**；Helicone 反复 escalate，**4 天里大部分时间在等 AWS 回复**。
- **5/18 (周一中午)** — 账号解封；5/18 当天连发 5 个修复 PR 收尾（详见 §4）。

### 2.2 影响半径

- ✅ **Gateway proxy 全程正常**——用户经 `ai-gateway.helicone.ai` 发到 OpenAI/Anthropic/Google 等上游的请求没受影响。
- ❌ 日志/dashboard/auth 挂掉 4 天；用户看到的现象是「dashboard 登不进去、log 一直不出现、auth 报错」。
- ✅ **无数据丢失**——请求被排队、没丢弃，账号恢复后逐步回放。
- 🔁 全部 credentials **预防性轮换**（即使调查确认 key 未真泄露，按 founder 原话「assume the worst and rotate」）。

### 2.3 暴露的脆弱

1. **AWS 单账号硬耦合**——一个 Bedrock key 被误判 → 整个账号（ECS/CloudWatch/S3/...）雪崩；多账号/多 region 隔离缺位。
2. **支持工单响应慢**——Helicone「escalated repeatedly」仍然等到周一；4 天观测停摆对 SaaS 而言是品牌级事件。
3. **事故透明度靠 banner 跳转隐藏博文**——incident post 故意 *未* 进 blog list，只挂在 banner 链接上，SEO 上几乎搜不到。

---

## 3. CloudWatch 单月烧 \$22,475：一行 debug log 的代价

PR **#5665** `fix: remove RAW request/response body debug logs`（merged 2026-05-02）—— 这次事故的「事后归因」比 5/18 事故本身更值得产品方警惕。

### 3.1 起因

2026-04-03 PR **#5652**（修 Anthropic response token mapping）在 `ResponseBodyHandler.processBody` 留了两行 `console.log`，**每次请求都把完整 LLM 请求/响应体打进 stdout**。还把 tag 拼成错别字 `[RAW_RESONSE_BODY]`，搜起来更顺。

### 3.2 放大器

`awslogs` 把多行 payload pretty-print 后，**单次请求拆出数千个 CloudWatch event**。多模态（Gemini inline image、audio）一单几百 KB base64，碎片化更夸张。

### 3.3 账单

| 指标 | 修复前（4 月） | 修复后基线 |
|---|---|---|
| `/ecs/valhalla_jawn` 日摄入 | **1.5–3.9 TB/天** | ~1 GB/天 |
| 月 CloudWatch 总账单 | **\$23,053** | — |
| `USW2-DataProcessing-Bytes` | **\$22,475（97.5%）** | — |

修复后预期回落到 ~\$1k/月量级。**36 小时内把日志量从 GB 拉到 TB 级的代码改动能合进 main，说明 CI 里缺一道 log-volume 闸门**——任何新增 `console.log` 触发 ingest 涨幅超过某个阈值就应自动 block。

---

## 4. bifrost 站点「2 个月没成功生产部署」

PR **#5683**（merged 2026-05-18）`fix: unbreak bifrost build (stub dead stats pages blocked since #5638)` 披露了一个**更尴尬**的真相：bifrost（Helicone 的 marketing/blog 前端）**自 2026-03-15 以来就一直没成功部署过**。

### 4.1 根因链

1. **2026-03-15** PR **#5638** `fix: remove unauthenticated endpoints that run SQL` 出于安全考虑删除了三个未鉴权端点（`/v1/public/alert-banner`、`/v1/public/stats/*`、`/v1/public/waitlist/*`），其中 **`/v1/public/stats/*` 走 ClickHouse 且跨全 org**。
2. 三个前端页面（`app/stats/StatsPage.tsx`、`app/stats/authors/...`、`app/stats/providers/...`）**仍在调已删除端点**。
3. 仓库**没有 `typescript.ignoreBuildErrors`**，于是 `next build` 直接挂在 `PathsWithMethod` 类型错误。
4. Vercel 持续返回构建失败，但**部署流水线只是静默回退到上一个成功构建**——3/15 之前的旧构建就一直 serving。期间所有 blog 新增文章 `fs.readFile` 都会 ENOENT，于是 `/blog/[file-path]` 在未知 slug 时**返回 500 而不是 404**，连上面 #2 的 incident post 都被卡 500。

### 4.2 修复

把三个 stats 页面临时换成「Temporarily Unavailable」静态组件，类型干净、构建通过；明确**不**用 `as any` 或全局 ignoreBuildErrors 糊住。完全可逆——stats endpoint 安全重做后从 git history 还原即可。

### 4.3 PR 自己列的「follow-up」比修复本身更扎心

> bifrost should fail loudly on deploy failure — 2 months of silent failed deploys is the real process gap here.

2 个月**没有任何人发现** Vercel 在静默喂旧构建。如果不是 5/18 incident post 500 才暴露，这个状态可能还会再拖几个月。

---

## 5. 模型与生态杂项（2026 Q2）

- **2026-03-26** PR：新增 **Claude Opus 4.6** OpenRouter 路由别名
- **2026-03-07** PR：新增 **GPT-5.4** 与 **Gemini 3.1 Flash-Lite Preview** 模型支持
- **2026-03-19** PR：anthropic 价格表修正
- **2026-04-04** PR：anthropic response conversion **token 映射**修复（事后被指为 §3 那场 \$22k 事故的源头）
- **2025-11-26** changelog：Claude Sonnet 4/4.5 支持 1M context window
- **2025-08-13** changelog：Playground 加入 reasoning effort 控制 + thinking 模型反馈

AI Gateway 文档自我定位：「100+ LLM providers / 0% markup / 自带 observability + sessions + users + prompt management + caching + rate limits + security + automatic fallbacks + 开源 + BYOK」—— 卖点直接对标 **OpenRouter**（5.5% markup、无 sessions/prompts 等），营销节奏明显。

---

## 6. 现状一图流（报告生成时 2026-06-06 00:46 CST）

| 维度 | 状态 |
|---|---|
| `ai-gateway.helicone.ai` | HTTP 405（live，方法层正常） |
| `status.helicone.ai` | All services online，proxy 自称 99.9999% uptime 持续 18+ 月 |
| 最近 release | `v2025.08.21-1`（285 天前） |
| main 活跃度 | 高，5/18 单日 5 个 PR |
| 文档站 | 已迁至 Mintlify（footer: "Powered by Mintlify"） |
| 事故状态 | 5/18 已恢复，无数据丢失，全 credentials 已轮换 |

---

## 7. 对 AI 网关选型的三点启示

1. **观测层与数据面必须解耦**——Helicone 这次靠「proxy 和 ingestion 跑在不同栈」扛住了 4 天事故。Litellm/Portkey 自建者值得借鉴：**不要把日志/dashboard 跟转发代理放同一 AWS 账号、同一 IAM 信任域**。
2. **「日志泄漏 + 多模态」是 CloudWatch 默认账单模型的天然放大器**——任意 LLM 网关在多模态流量下若把 request/response 整段打 stdout，单月账单四位数美元起跳。生产环境必须配 log sampling + 体积阈值告警。
3. **「静默回退到上一个成功构建」是 Vercel 风格 PaaS 的暗债**——当事故 PR 想紧急上 banner 才发现构建已坏 2 个月，舆情窗口就丢了。自建者应在 CI 里把「连续 N 次部署失败」升级为 P0 告警。

---

## 引用与数据来源

- GitHub Releases：`https://api.github.com/repos/Helicone/helicone/releases?per_page=8`
- GitHub Commits：`https://github.com/Helicone/helicone/commits/main`
- PR #5683（bifrost build 修复）：`https://github.com/Helicone/helicone/pull/5683`
- PR #5681（incident post）：`https://github.com/Helicone/helicone/pull/5681`
- PR #5680（Supabase ws 修复）：`https://github.com/Helicone/helicone/pull/5680`
- PR #5678（hardcoded banner）：`https://github.com/Helicone/helicone/pull/5678`
- PR #5665（remove RAW body debug logs）：`https://github.com/Helicone/helicone/pull/5665`
- Issue/PR #5638（删除未鉴权端点）：`https://github.com/Helicone/helicone/pull/5638`
- PR #5652（Anthropic token mapping 修复 — 间接源头）：`https://github.com/Helicone/helicone/pull/5652`
- Incident 公开博文：`https://www.helicone.ai/blog/aws-account-incident`
- AI Gateway 文档总览：`https://docs.helicone.ai/gateway/overview`
- 状态页：`https://status.helicone.ai/`
- 端点连通性自检：`curl https://ai-gateway.helicone.ai/`（HTTP 405，0.66s）

> 本报告由 hermes-agent cron 自动生成；下次轮次 2026-06-06 01:16 CST（hour=1 → MCP Gateway 专题）。
