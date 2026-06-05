# AI 网关持续深挖 · 第 N 次 — 语义路由/成本优化(第 5 视角:router 算法内核 + 语义缓存工业切片)

- 轮值时间(本地): 2026-06-06 03:28 CST(Saturday)
- 主题: 语义路由/成本优化(hour % 7 = 3)
- 角度: 前 4 次覆盖 — 跨厂商 schema 收敛 / 开源生态 + 路由 RCE / 成本归因 + 投机 / vLLM SR Themis 项目级。本次 **第 5 视角切到「算法内核」**:从「网关怎么拼装」移到「路由决策用什么模型 / 什么 verifier / 什么阈值 / 怎么审计」,叠加「语义缓存层 2026 H1 的三条新工业线」。
- 抓取窗口: 2026-05-26 ~ 2026-06-06 03:28 CST

---

## 1. 一句话结论

「**LLM 路由算法在 2026 H1 完成『学派收敛』——不是 LLM-as-judge 胜出,而是『wide-and-deep 预分类 + cross-encoder 后验证 cascade + τ 阈值门控 + RouterArena 公榜 + 污染审计』成事实标准;NotDiamond / Martian 核心 SDK 自 2025 H2 几乎停更,新一代在 cascade / 协议翻译 / 商业化模型上分叉;语义缓存从 GPTCache 单一向量相似,裂变成 vCache 可靠性 / Anthropic 端侧 / prompt-cache 全 chunk 复用 3 条独立线。**」

近 10 天最硬 4 信号:
1. **NadirClaw v0.19(2026-05-29)** —— `wide_deep_asym_v3` 预分类 + DeBERTa-v3-small INT8 cross-encoder 后验证,τ=0.80,RouterBench AUROC 0.961 / ECE 0.016 / 60% 成本压缩。
2. **BitRouter v1.0.0-alpha.7 + 4 PR(06-02~06-04)** —— Rust ~10ms 路由,跨协议翻译、MCP+ACP、`brvk_*` 虚拟 key。
3. **Tessera SDK 0.1.0/0.1.1(05-18)** —— `tessera.activate()` 一行接管,**flat-tier 月费不按节省抽成**,savings ledger 实时。
4. **LiteLLM 6 天 5 tag(05-24~06-05)**——v1.87.0 加 user_email/team_id 三级归因 + OTEL team_id 传播;`GHSA-q775 session-token budget-ceiling exemption` 在 1.87.x+rc 双线 backport。

---

## 2. 硬数据

### 2.1 NadirClaw v0.19 — router 算法内核的「教科书范本」

`https://github.com/NadirRouter/NadirClaw` + MODEL_CARD + README

- **基本盘**:star 512,4 个 tag 间隔 ≤1 天(`v0.18.0 → v0.19 → v0.19.1 → v0.19.2`,05-26~05-29)。
- **#59 cascade rule engine + τ=0.80(05-29 01:37 UTC)**——预分类+后验证+阈值门控拉成可替换规则集;**#60 N-tier cascade(N=2 default)(01:41)**;**#61 TrainedVerifier: RouterArena 0.7358 snapshot(01:58)**;**#63 TrainedVerifier input format fix(13:12)**——v0.19.2 hotfix 真因:`Scores were previously miscalibrated against tau=0.80 threshold`。
- **`wide_deep_asym_v3`(MODEL_CARD,05-27)**:wide 分支 33 维结构/词法特征(length buckets / code-fence / math symbol density / JSON shape / question-word);deep 分支 `bge-small-en`;head `{simple, medium, complex}` 三路 softmax;**λ=3 降级惩罚**(误判 complex 成本是反向 3×,「catastrophic downgrade 比 wasted escalation 更不可接受」)。
- **τ-sweep**:τ=0.70(0.69/0.024/0.078/97.6%)→ **τ=0.80 默认(0.67/0.017/0.092/98.3%)**→ τ=0.90(0.64/0.011/0.108/98.9%)。格式:accept / catastrophic / wasted / quality。「catastrophic < 2% but wasted 9%」=**保守派曲线**:宁可浪费 Sonnet 也不让 Haiku 翻车。
- **verifier latency 192.9ms / call, single-core CPU, INT8 qnnpack**——预分类 ~40ms + 后验证 ~193ms = 233ms 总开销,对 1-3s LLM 调用是 7-23% 相对成本。
- **污染审计(0 overlap)**:RouterBench 0shot 0/36 481,RouterArena sub_10 0/809,full 0/8 399,hash 配方 `sha256(NFC(prompt).strip().casefold().utf8)`,脚本 `verifier/contamination_audit.py` 可复现——对应「训练数据与评测集交叉」的预算/法务/客户验收问题。

### 2.2 BitRouter v1.0.0-alpha.7 — Rust 内核 agent-native 路由器

`https://github.com/bitrouter/bitrouter`

- **star 155**,6 天 4 release(`alpha.6 06-02 → alpha.7 06-03`),**alpha 但周更**。
- **#512(06-03):converge marketplace.json on Claude Code native schema**——plugin/marketplace 格式往 Claude Code schema 收,「agent native」=schema 真对齐;**#513 fix(cli) auth login --scope help to namespace-read**——RFC 8628 device flow 命名空间修;**#516 feat(sdk)!: per-target Messages auth scheme(x-api-key | Bearer)(06-04 17:13 UTC)**——**breaking change**:不同上游 Anthropic Messages API 认证方式按 target 区分。
- **架构差异表(README)**:BitRouter ~10ms / OpenRouter ~30ms(cloud) / LiteLLM ~500ms(Python 启动+框架),**Rust vs Python 是数量级差距根因**;**MCP+ACP 双协议**对标 LiteLLM 的「MCP only」;**`brvk_*` 虚拟 key + SQLite/PostgreSQL/MySQL 持久化** + 跨协议翻译是核心差异化。

### 2.3 Tessera SDK 0.1.0/0.1.1 — drop-in 成本优化代理的「商业化模型」

`https://github.com/tessera-llm/tessera-sdk`

- **star 4**,1.5 小时出 hotfix(`v0.1.0 05-18 22:22 → v0.1.1 23:19`),典型「补 py.typed + FAQ」节奏。
- **商业化**:**flat monthly subscription, priced by gross monthly token volume**(2026-05-28 #11 锁的);**「savings is your ROI proof, not our billing basis」**——**不按节省抽成,节省是客户 ROI,Tessera 收固定月费**——把「成本归因的真实性」和「Tessera 的收入」解耦,这非常聪明,因为它把「路由层是否真省钱」的核查责任下放给客户审计而不是靠 Tessera 自家声明。
- **核心**:`tessera.activate("tk_...")` → monkey-patch openai/anthropic/mistral/groq/cohere client 构造,注入 baseURL + X-Tessera-Key;背后 auto-route + cache + context compress + batching。
- **Free Dev tier: 10→30 req/min(0.1.1 抬)+ 60M tokens/month**,savings ledger 实时在 `ledger.tesseraai.io/portal/audit`。
- **横向比较**:**Tessera = 把省钱做成产品**;BitRouter = 把 agent native 做成产品;NadirClaw = 把算法精度做成产品;LiteLLM = 把协议兼容 + 安全做成产品;SmarterRouter = 把 local-first + 零云开销做成产品——5 个产品在 5 个不同维度抢同一个客户。

### 2.4 LiteLLM 1.87.0/1.87.1/1.88.0-rc.1~3 — 成本归因 + 缓存 + 安全三线齐推

`https://github.com/BerriAI/litellm`

- **v1.87.0 stable(06-02 04:12 UTC)** ~30 PR,3 条最硬:
  1. `fix(caching): replay openai/responses bridge cache hits as chat streams(#28158)`——**`/v1/responses` 命中 cache 后被桥接成 chat stream 回放**,意味着统一 cache 命中后会被协议转译回调用方期望协议。
  2. `feat(prometheus): add user_email and user_alias to user budget metrics(#28155)` + `feat: propagate team_id/team_alias to all child OTEL spans(#28273)`——**OTel 出口加 team_id/team_alias 传播**;两条一起让「team → user → call」三级归因可观测。
  3. `fix(proxy): gate team allowed_passthrough_routes to proxy admins(#28097)`——**CVE 等价修复**:`team.allowed_passthrough_routes` 是「team 级能否绕过 LiteLLM 直接命中上游」,以前被错误暴露给 team owner 可改,现在 proxy_admin only。
- **v1.87.1(06-04)+ v1.88.0-rc.1/2/3(05-31~06-05)**:都集中修 **`GHSA-q775 session-token budget-ceiling exemption`**(#29612/#29637/#29639/#29631/#29636/#29645),**rc/1.87.x 双线同时 backport**,印证「session-token 在 budget ceiling 处的例外逻辑」是过去 30 天 LiteLLM 团队最关心的洞。
- **LiteLLM security advisories(2026-04-20~05-28 共 5 条)**:`GHSA-4xpc-pv4p-pm3w`(auth bypass via host header,05-28)/ `GHSA-wxxx-gvqv-xp7p`(sandbox escape in custom-code guardrail,05-07)/ `GHSA-r75f-5x8p-qvmc`(SQLi in proxy API key verification,04-20)/ `GHSA-xqmj-j6mv-4862`(SSTI in /prompts/test,04-20)/ `GHSA-v4p8-mg3p-g94g`(auth command execution via MCP stdio test endpoints,04-21)——**全部都和「路由层权限边界」相关**,AI 网关 = 新型 API 网关 = 新型攻击面。

### 2.5 SmarterRouter 2.2.5~2.2.7 — local-first + Ollama 元数据自描述

`https://github.com/peva3/SmarterRouter`

- **2.2.5(2026-04-18)**:Dynamic Model Metadata Registry——**从 Ollama `/api/show` 自动拉模型 capability**(vision / tool_calling / embedding / MoE / quantization),**TTL 默认 1h**;**Gemma 4 系列(e2b/e4b/26b/31b)模态识别**;**MoE 模型 VRAM 按 active params 算**。
- **2.2.6(04-28):Streaming kwargs passthrough fix**;**2.2.7(05-10):Circuit breaker quota disambiguation fix**——**熔断器多 quota 场景消歧**。
- README 对比表:SmarterRouter 把差异化压在「local-first + profile 反馈」,**和 NadirClaw 「trained classifier」路线相反**,**和 BitRouter 「Rust+cloud」路线相反**。

### 2.6 语义缓存层 5 条线信号

- **zilliztech/GPTCache**(star 8 054, last push 2025-07-11)—— 11 个月未动,OSS 进入维护期。
- **codefuse-ai/ModelCache**(star 947, last commit 2025-06-30)—— 蚂蚁/CodeFuse 系,Redis Search multi-tenant embedding 存储(「cache↔vector DB ≤ 10ms」),近 11 月未动。
- **thu-nics/C2C**(star 401, ICLR'26)—— 「**Cache-to-Cache**」,不同 prompt 的 KV cache 互相复用,vLLM/prefix-cache 场景,学术线。
- **vcache-project/vCache**(star 70, 2025-12-17)—— 「**Reliable and Efficient Semantic Prompt Caching**」,**新 license 改 Creative Commons**,**SemBenchmarkCombo(PR #87,2025-11-16)** 把不同 embedding model × 不同相似度阈值的 cache hit rate 做成 benchmark 套件——**「缓存命中率」不再是经验值,而是 benchmark 可测指标**。
- **messkan/prompt-cache**(star 236, v0.4.0 2026-04-24)—— 「**Cut LLM costs by up to 80% and unlock sub-millisecond response**」,**全 chunk 复用策略**。
- **Anthropic prompt-cache**(2025 H2 推出,2026 H1 适配中)—— 端侧 5 分钟 + 1 小时两档,1.25× 写 / 0.1× 读,被 LiteLLM 1.87.0 「cache hit as chat stream bridge」桥接。
- **结论**:**缓存层从「GPTCache 一家独大」裂变成「vCache 测可靠性 / prompt-cache 全 chunk 复用 / Anthropic 端侧 / C2C 学术 KV-cache 跨 prompt 复用」4 条线**——**没有新统一标准**,反而「场景分流」。

### 2.7 算法派历史 SDK: Not-Diamond / Martian「停更」信号

- **Not-Diamond/notdiamond-python**(star 90, last push 2025-12-11)—— 6 个月未动;**notdiamond-node**(9, 2025-11-20)—— 7 个月未动;**RoRF**(241, 2024-09-24)—— 「**Routing on Random Forest**」,近 2 年没动。
- **withmartian 整 org**:`routerbench`(165, 2024-06-13),`llm-adapters`(34, 2025-07-21)—— 全停在 2025 H1/H2,`martian-sdk-python` 同样 2025-06-02 后 0 动。
- **unifyai/unify**(star 4, 2026-06-04)—— 公开仓占位,**商业化服务 + 内部 SDK 主导**。
- **结论**:**算法派(SaaS 型 router)开源 SDK 2025 H2 后集体停更**,新故事在 NadirClaw / BitRouter / Tessera / SmarterRouter ——「**single-binary-rust / drop-in-sdk / cascade-rule-engine / local-first-ollama**」**4 个新故事**。

---

## 3. 对 AI 网关选型的现实影响

「**agent + 多 provider + 月花 $5k+ 的团队,2026 H1 已经不是「装一个 LiteLLM 就行」**——**预算治理**走 LiteLLM(`user_email/team_id → Prometheus`),**算法精度**叠 NadirClaw(`wide_deep_asym_v3` + `cascade τ=0.80` + `RouterArena 0.7118`),**agent 协议**叠 BitRouter(MCP+ACP+跨协议+虚拟 key),**商业化成本代理**走 Tessera(flat-tier 月费 + savings ledger),**本地隐私/离线**走 SmarterRouter(Ollama + capability 自描述);**缓存层**按场景分流 — agent prefix 复用走 `prompt-cache`、Anthropic 客户端走端侧 `prompt-cache`、可靠性指标走 `vCache`、学术 KV cache 复用走 `C2C`。」

---

## 4. 时间线(2026-05-24 ~ 06-06)

- **05-24** LiteLLM v1.87.0-rc.1
- **05-26** SmarterRouter 2.2.7 / NadirClaw v0.18.0
- **05-28** LiteLLM GHSA-4xpc-pv4p-pm3w / Tessera 锁 flat-tier 定价
- **05-29** NadirClaw v0.19 + v0.19.1 + v0.19.2 一天三 tag
- **06-02** LiteLLM v1.87.0 stable + BitRouter v1.0.0-alpha.6
- **06-03** BitRouter v1.0.0-alpha.7 + #512 schema converge
- **06-04** LiteLLM v1.87.1 + v1.88.0-rc.2(GHSA-q775 双线 backport) + BitRouter #516 per-target auth
- **06-05** LiteLLM v1.88.0-rc.3
- **06-06 03:28** 本次 cron → 报告 + 推送

---

## 5. 待观察 / 风险

- **Tessera 「节省归因」可信度**:`ledger.tesseraai.io` 是 Tessera 自家记录,**第三方无法独立验证**——「flat-tier 抽费模式下客户的节约归因也是被代理记账」会是 2026 H2 争议点。
- **NadirClaw N-tier cascade**:**N>2 后 verifier latency 累计 192.9ms × N,质量提升是否边际递减**没公开数据。
- **BitRouter `~10ms`** —— README 自报,**「含不含 cold start」不明确**;LiteLLM 报 ~500ms 也含 Python 框架启动,稳态可能小一个量级。
- **LiteLLM 5 条 security advisories 集中爆在「team/owner 可改 passthrough / SSTI / SQLi / sandbox escape」**——**权限边界是 LiteLLM 当前最大风险面**。
- **Anthropic prompt-cache 1.25× write / 0.1× read**——client 没把 system prompt 提到最前 / 没 chunk prefix 复用,实际节省远低于 80%;LiteLLM 1.87.0 「cache hit as chat stream bridge」是补丁,需 client 配合。

---

## 引用与数据来源

- NadirClaw repo + MODEL_CARD + README:`https://github.com/NadirRouter/NadirClaw`
- NadirClaw v0.19.2 release:`https://github.com/NadirRouter/NadirClaw/releases/tag/v0.19.2`
- NadirClaw commits API:`https://api.github.com/repos/NadirRouter/NadirClaw/commits`
- BitRouter repo + README:`https://github.com/bitrouter/bitrouter`
- BitRouter v1.0.0-alpha.7:`https://github.com/bitrouter/bitrouter/releases/tag/v1.0.0-alpha.7`
- BitRouter PR #512/#513/#516:`https://github.com/bitrouter/bitrouter/pull/512` / `#513` / `#516`
- Tessera SDK repo + README:`https://github.com/tessera-llm/tessera-sdk`
- Tessera python-v0.1.1:`https://github.com/tessera-llm/tessera-sdk/releases/tag/python-v0.1.1`
- SmarterRouter repo + README:`https://github.com/peva3/SmarterRouter`
- SmarterRouter 2.2.5 release:`https://github.com/peva3/SmarterRouter/releases/tag/2.2.5`
- LiteLLM repo:`https://github.com/BerriAI/litellm`
- LiteLLM v1.87.0 release notes:`https://github.com/BerriAI/litellm/releases/tag/v1.87.0`
- LiteLLM v1.87.1 / v1.88.0-rc.1~3:`https://github.com/BerriAI/litellm/releases`
- LiteLLM security advisories:`https://api.github.com/repos/BerriAI/litellm/security-advisories`
- Not-Diamond org repos:`https://api.github.com/orgs/Not-Diamond/repos`
- withmartian org repos:`https://api.github.com/orgs/withmartian/repos`
- vCache repo:`https://github.com/vcache-project/vCache`
- C2C (ICLR'26) repo:`https://github.com/thu-nics/C2C`
- ModelCache repo:`https://github.com/codefuse-ai/ModelCache`
- GPTCache repo:`https://github.com/zilliztech/GPTCache`
- messkan/prompt-cache repo:`https://github.com/messkan/prompt-cache`
- 同期:`2026-06-05-1736-aigw-semantic-routing-vllm-themis.md`(Themis 项目级) / `2026-06-05-1031-aigw-routing-cost-attribution.md`(成本归因+投机) / `2026-06-05-0348-aigw-routing-cost-security.md`(RCE+预算上限) / `2026-06-05-0306-aigw-semantic-routing-cost.md`(跨厂商 schema)
