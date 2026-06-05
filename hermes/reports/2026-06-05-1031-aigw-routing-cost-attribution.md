# AI 网关持续深挖 · 第 16 次 — 语义路由/成本优化(第 3 视角:成本归因 + 级联/投机 + 后台预算治理)

- 轮值时间(本地): 2026-06-05 10:31 CST
- 主题: 语义路由/成本优化(hour % 7 = 3)
- 角度: 第 6 次(03:06,`...-0306-aigw-semantic-routing-cost.md`)覆盖「跨厂商 schema 收敛 + sort 维度 + 缓存键」;第 7 次(03:48,`...-0348-aigw-routing-cost-security.md`)覆盖「开源路由器 + 路由层 RCE + budget ceiling」;**本次 3rd 视角按 pitfall #13a/#27 切到新坐标轴**:① 成本归因精度,② 模型融合(speculative / cascade)网关化,③ 后台预算治理并发正确性。
- 抓取窗口: 2026-05-15 ~ 2026-06-05 GitHub release / PR / 官方 docs

---

## 1. 一句话结论

「**LLM 网关的成本层正在从『请求级计价』拆成『请求级 + 数据驻留级 + 缓存写价级 + 路由重试级』四层,后台预算治理正在并发修正的边角。**」

三条最硬的近 30 天信号:
1. LiteLLM **#28626**(2026-05-26 合并)给 OpenAI EU/US 端点引入 `regional_processing_uplift_multiplier`,把 `data_residency` 推断成成本乘数 — **data residency 不再只是合规标签,开始直接抬高计费**。
2. LiteLLM **#28569 / #28572**(2026-06-03)给 Vertex AI / Bedrock 的 Claude 模型补齐 **1 小时缓存写价**(1.6× 5 分钟价位) — 之前所有 `cache_control.ttl=1h` 的 Vertex Claude 请求在 LiteLLM 端被少算约 60%,**行业级定价模型修复**。
3. LiteLLM **#29358** + cherry-pick #29361/#29363:`ResetBudgetJob` 静默失败根因是 *「先 pre-zero 再写 spend」* 两段式逻辑在 scheduler tick 上 *lost-update race*;修复后写时只输出 `{spend, budget_reset_at}` 原子字段 — **「成本治理」与「多实例部署」第一次正式碰撞**。

---

## 2. 硬数据(均带日期与来源 URL)

### 2.1 LiteLLM:Data-Residency 成为成本乘数(PR #28626,2026-05-26)

来源: `https://github.com/BerriAI/litellm/pull/28626`(internal copy,original PR #28622,Cursor Bugbot 中等风险)

- 行为:按 `api_base` 主机(`eu.api.openai.com` / `us.api.openai.com`)推断 `data_residency`,透传到 logging params + cost calculator。
- 引入 per-model regional uplift 系数 `regional_processing_uplift_multiplier_eu / _us`,对 *token-based 成本*(含 batch / realtime stream 路径)做乘法。
- 触发原因:OpenAI 在 2026 Q2 对 EU/US 端点引入 *data-residency processing fee*,LiteLLM 早期只把 `data_residency` 当 *合规/路由标签*。
- 测试:20 个 parametrized 用例验证 uplift 行为与 region 推断。

> **网关语义升级样本**。`data_residency` 之前是 *transport 层 policy*,现在影响 *pricing 路径*。**任何「仅按 token 算成本」的网关在合规跨区时都会少报成本**;同时为「按区域加价路由」打开了 *cost-arbitrage routing* 的新自由度。

### 2.2 LiteLLM:Vertex / Bedrock Claude 的 1 小时缓存写价(PR #28569 / #28572,2026-06-03)

来源: `https://github.com/BerriAI/litellm/pull/28569` + `https://github.com/BerriAI/litellm/pull/28572`

- GCP Vertex AI 文档化 1h 缓存写价 = 5min × 1.6(与 Bedrock ratio 一致);LiteLLM 之前 Vertex AI Anthropic 条目 *只承载 5min 价位*。
- 修复:为 Vertex AI Anthropic 条目补 `cache_creation_input_token_cost_above_1hr` 字段,加 20 条回归测试。
- 影响:任何 Vertex AI Claude 上 `cache_control.ttl=1h` 的请求被 *少算 ~60%* 缓存写成本 — 2026-05 后才上量的成本盲区。

> 同根的「定价盲区」还在(a) Azure OpenAI region-aware pricing,(b) OpenAI priority tier processing fee,(c) Anthropic prompt-cache 5m/1h 双 tier — **「少算成本」合规风险正在被多个 PR 连续修复**。

### 2.3 LiteLLM:`ResetBudgetJob` lost-update 竞态(PR #29358 + cherry-pick #29361/#29363,2026-05-31)

来源: `https://github.com/BerriAI/litellm/pull/29358`;fixes #27730

- 现象:v1.84.0+ 的 `ResetBudgetJob` 对 *UI-created key* 静默失败:(1) spend 在 budget 周期边界*永不重置*,(2) 每次 scheduler tick 出现*周期性的 budget-enforcement 绕过窗口*。
- 根因:*「先 pre-zero 再写 spend」* 在 scheduler tick 上是 *read-modify-write*,中间窗口让下一次 enforce 看到 `spend=0` 而放行。
- 修复:DB 层一次写只输出 `{spend, budget_reset_at}`,不再 pre-zero;47 unit test 通过。修复被同时 cherry-pick 到 `patch/v1.87.0rc1` + `patch/v1.84.3` — **跨三条 active release line 同时 backport**。

> **「后台调度正确性」被提到跟 budget ceiling 同级**。OpenAI / Anthropic / Vertex 自己的 dashboard 都没暴露这条 race;LiteLLM 在自托管场景下必须自承担。

### 2.4 LiteLLM:Router Retry 后成本被钉在 0(PR #28476,2026-05-21)

来源: `https://github.com/BerriAI/litellm/pull/28476`

- 现象:Router 多次重试时,`failure_handler` 在每次失败把 `response_cost = 0`(#4604);PR #21844 的 *preserve 分支* 看到 `0` 不为空就 *不重算*,最终成功响应*永远记 0 成本*。
- 修复:重试成功时强制用成功响应的 usage *重新计算 cost*,不再信任 `0` 这种 *stale preserved value*。
- 影响:**Router-retry 路径下 spend 报表低估 100%**。

> **「重试路径是计费死角」** — Anthropic 官方 *automatic fallback* 与 OpenAI 官方 *priority tier* 文档都未点名,只在 LiteLLM 这种*有显式 router 的网关*才能被命中。

### 2.5 LiteLLM:动态加入的 deployment 也要注册 budget(PR #29273,2026-05-30)

来源: `https://github.com/BerriAI/litellm/pull/29273`(fixes #25799, Linear LIT-3043)

- 现象:`RouterBudgetLimiting` 之前只在启动时从 `model_list` 读取 `max_budget`;运行时 `/model/new` `add_deployment / upsert_deployment` 加进来的 deployment *不进入 budget 限额* — *drip-add 模型*的团队会持续超支。
- 修复:在 `add_deployment / upsert_deployment` 路径上注册 budget,lazy 启用 `router_budget_limiting`,用 *exact-type* lookup 避免 `_PROXY_VirtualKeyModelMaxBudgetLimiter` 误识别。

> 与 #29358 是「成本治理运行时正确性」的对偶 — 一个修后台调度,一个修运行时注册。**LiteLLM 在 5 月底一周内连续合入 4 条成本治理类修复,显示「成本会计」已从 SDK 边缘话题升到 proxy 核心稳定性问题。**

### 2.6 vLLM v0.22.0(2026-05-29):Speculative Decode 在网关侧的「可路由化」信号

来源: `https://github.com/vllm-project/vllm/releases/tag/v0.22.0`

- 新增 *Custom callable proposer backend*(#39487)、*post-norm EAGLE-3 speculators*(#42764)、*peagle speculators*(#41826)、*non-MTP speculation for NemotronH*(#43130)、*shared MTP weights in MRv2*(#42538)。
- DeepSeek V4 在 v0.22.0 拿到 **MTP speculative decoding**(#43385)+ MegaMoE + sparse MLA 完整重构。
- 配合 *Batch-invariant inference* 28.9% 端到端延迟下降(#40408)+ *Multi-tier KV cache offloading*(#40020)。

> **「speculative decode」从 vLLM 内核特性向「网关可调用」外延**。自建 LLM gateway 已在 `litellm_completion(..., speculative=True)` 实验 — vLLM 端给所有 speculator 暴露统一 proposer backend 之后,**网关侧 router 有望直接按 prompt 难度挑选 `target + proposer` 二元组**,把 *cascade routing* 从「两 model 串行」扩展到「两 model 投机」。**2026 下半年最值得跟进的网关化方向。**

### 2.7 Portkey:2026-05-19 安全加固集群 + 2026-02-19 v2 公告

来源: `https://github.com/Portkey-AI/gateway/commits?per_page=20`

- 2026-02-19 main 合入 `feat: announce v2 of gateway` — 解释 2026-01-12 之后 *5 个月无新 release tag* 的空窗(转入 v2 内部 review)。
- 2026-05-19 同一日四个 commit 集群:`remove admin token default` / `disable logs when admin token not set` / `redact provider options in logs` / `add auth validation for public routes`(PR #1657,2026-05-25 合并)。
- 典型 *post-acquisition / pre-v2 security hardening burst*(PANW pattern 镜像)。
- star 数 11,972(对比 4 周前推测 ~11,500-11,700),30 天 ~200-300 star — **v2 公告期间 star 仍微增**。

> Portkey 是 *单产品发版追踪* 下一个 hour%7=0 潜在目标;**今天值得记下来的是:Portkey 的「v2 重置 release-train」是 2026 下半年最重要的 release-cadence 信号之一**,若 v2 第一个 release tag 在 6 月底前出,会立刻成为「网关 v2 化」对标对象。

---

## 3. 三视角差异(前-中-后台切片)

- 角度 A(03:06,`...-0306-aigw-semantic-routing-cost.md`):**前** — 跨厂商 schema 收敛 + sort 维度 + 缓存键。代表:Envoy v0.6.0、OpenRouter sort。
- 角度 B(03:48,`...-0348-aigw-routing-cost-security.md`):**中** — 开源路由器生态 + 路由层 RCE。代表:SmarterRouter 2.2.4、LiteLLM budget ceiling。
- **第 3 视角(本次)**:**后** — 成本归因精度 + 级联/投机 + 后台预算治理。代表:#28626 / #28569 / #29358 / #28476 / #29273、vLLM 0.22.0 speculator、Portkey 5/19 cluster。

> 同一 topic 的「**前-中-后台**」三段切片,3 视角共覆盖 7 条 LiteLLM PR + 1 vLLM 主版本 + 1 收购模式信号 + 1 RCE 修复。

---

## 4. 结论与下一轮钩子

1. **「成本归因」已分裂为四个独立维度**:请求级 × 数据驻留级 × 缓存写价级 × 路由重试级。**4 个维度全在 2026-05 末到 2026-06 初的 2 周内被 LiteLLM 主线一一补齐**,「成本会计」从「运营商报表」变成「网关 SLA」。
2. **「后台预算治理」并发正确性是 2026 下半年新稳定性战场**:`ResetBudgetJob` lost-update、运行时 budget 注册、`end-user budget` 误判三条 PR 表明 LiteLLM 已经把 *scheduler* + *router hot path* + *proxy auth* 三条线都碰到了边界。
3. **「speculative decode 网关化」是下一波值得追踪的路由-成本交叉信号**:vLLM 0.22.0 给出统一 *proposer backend* 后,网关侧能直接挑 `target + proposer` 二元组;6 月底前若 LiteLLM / Portkey / OpenRouter 任一家出 *speculative-aware router* 文档会立刻成为下一轮 #3 主题的入口。
4. **Portkey v2 release-train 即将出关**:2026-05-19 集群是「v2 release cut」前的最后清理,后续 hour%7=0 轮值若命中 Portkey,**应当用 v2 第一个 tag 作为切入点**,并把「v2 的网关注册接口」作为补充维度。

---

## 5. 引用与数据来源

- LiteLLM Releases: `https://github.com/BerriAI/litellm/releases` (v1.86.3 / v1.86.4 / v1.87.1 / v1.88.0-rc.2/-rc.3, 2026-06-03~06-05)
- PR #28626: `https://github.com/BerriAI/litellm/pull/28626` (regional cost uplift, 2026-05-26)
- PR #28569 / #28572: `https://github.com/BerriAI/litellm/pull/28569` (Vertex/Bedrock Claude 1h cache write pricing, 2026-06-03)
- PR #28476: `https://github.com/BerriAI/litellm/pull/28476` (recalc cost after router retry, 2026-05-21)
- PR #29273: `https://github.com/BerriAI/litellm/pull/29273` (deployment budgets for runtime-added models, 2026-05-30)
- PR #29358 + cherry-picks #29361/#29363: `https://github.com/BerriAI/litellm/pull/29358` (reset_budget race, 2026-05-31)
- PR #29420 / #26612: `https://github.com/BerriAI/litellm/pull/29420` (end-user budget check fix + Snowflake Cortex pricing, 2026-06-03/04)
- vLLM v0.22.0: `https://github.com/vllm-project/vllm/releases/tag/v0.22.0` (speculative decoder + DeepSeek V4 MTP, 2026-05-29)
- Portkey main commits 2026-05-19 / 2026-05-25 cluster: `https://github.com/Portkey-AI/gateway/commits?per_page=20`
- Portkey PR #1657: `https://github.com/Portkey-AI/gateway/pull/1657` (auth validation for public routes, 2026-05-25)
- Portkey Releases: `https://github.com/Portkey-AI/gateway/releases` (v1.15.2 2026-01-12,latest — 5-month gap, v2 in flight)
- 前序报告: `~/hermes/reports/2026-06-05-0306-aigw-semantic-routing-cost.md`(A)、`~/hermes/reports/2026-06-05-0348-aigw-routing-cost-security.md`(B)
