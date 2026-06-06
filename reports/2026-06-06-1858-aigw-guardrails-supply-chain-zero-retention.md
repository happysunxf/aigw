# AI 网关持续深挖 · Guardrails 专题（round 6 — 供应链安全 / 零留存 / 多模态红队）

> **主题**：Guardrails & 安全 — 提示词注入 / PII / 内容审计 / 零留存
> **轮次**：本轮第 6 次 guardrails 专题（按 hour % 7 = 4 命中）
> **时间锚点**：2026-06-06 18:58 UTC+8（Saturday）
> **数据窗**：过去 14d 重点抓过去 72h
> **核心信号**：`guardrails-ai` PyPI 0.10.1 投毒事件（CVE-2026-45758）后续处理、presidio v0.0.x unified analyzer config、garak v0.15.1 ProPILE PII 探针与 cas digest 矩阵、promptfoo 0.121.15 多模态 grading + A2A provider + 凭据泄露护栏

---

## 1. 总览：guardrails 三栈在 6/2–6/6 同时硬化

| 项目 | 版本 / 时间 | 主线 | 与 gateway 关系 |
| --- | --- | --- | --- |
| **guardrails-ai** | v0.10.2 (2026-06-04 19:37 UTC) | 投毒事件后续 + LiteLLM pin | 修 GitHub Actions secret 泄露 + `>=1.83.0` litellm 兼容 |
| **microsoft/presidio** | PR #1970 (5/17) + #2000 (5/16) | Unified Analyzer Config + countries 过滤 | PII 识别器统一治理 + locale-aware 部署 |
| **NVIDIA/garak** | v0.15.1 (2026-06-05 17:24 UTC) | ProPILE PII 探针 + cas digest 矩阵 | LLM red-team 探针成为 CI gate 的事实标准 |
| **promptfoo** | 0.121.15 (2026-06-05 14:21 UTC) | 多模态 grading + A2A provider + cloud auth 隔离 | red-team 评估框架 self-host/云混合模式护栏 |

四件同时落地说明一件事：**OSS guardrails 在 2026 H1 从"开发玩具"转到"生产 CI gate"**。其中 5/11 那一波 TanStack + guardrails-ai +（还有 agentthreatrules 等）的**同窗口 OSS 供应链攻击**仍然在持续清尾。

---

## 2. 核心信号 1：`guardrails-ai` 0.10.1 投毒事件（critical / 24 天后仍未完全收尾）

[**GHSA-xmpw-2vmm-p4p6 / CVE-2026-45758**](https://github.com/guardrails-ai/guardrails/security/advisories/GHSA-xmpw-2vmm-p4p6)（critical）— guardrails-ai 0.10.1 PyPI 投毒。**时间线**：

- **5/11 18:00 PT**：攻击者用一位 guardrails-ai 员工的 GitHub PAT 触发 org 内 30 个 repo 的 GitHub Action，产物泄露 repo secrets → 用 deploy token 推送恶意 0.10.1 到 PyPI。
- **5/11 20:00 PT**：安全研究员在 ~2h 内识别，PyPI 隔离。
- **5/12**：guardrails-ai 发布 SECURITY_ADVISORY.md，5/13 14:00 PT 全 org 轮换所有 Snowglobe/Hub API key。
- **5/19**：PR #1484 `fix: update litellm version pin to allow >=1.83.0` 合入（依赖治理）。
- **5/27**：社区在追踪 issue #1473 追问 PyPI 隔离解除 ETA，maintainer @ShreyaR 答"working with PyPI team, no estimate yet"。
- **6/4 19:37 UTC**：v0.10.2 release，仅含 7 项 `security advisory update` + litellm pin + trusted publishing workflow（PR #1493）。
- **6/6 18:58 本轮**：[issue #1473](https://github.com/guardrails-ai/guardrails/issues/1473) **仍未关闭**，PyPI quarantine 持续 → 所有 pip 用户**继续**必须走 `pip install guardrails-ai==0.10.0` 或 `pip install git+https://github.com/guardrails-ai/guardrails.git@v0.10.0`。

**24 天 OSS 供应链响应**对生产部署是 deal-breaker：

> 同样是 5/11 22:40 UTC 那一波：[**CVE-2026-45321 / GHSA-g7cv-rxg3-hmpx** TanStack](https://github.com/TanStack/router/security/advisories/GHSA-g7cv-rxg3-hmpx)（42 个 @tanstack/* 包 credential exfil）。两件事在 SECURITY_ADVISORY.md 显式 cross-reference。**同窗口同 attacker** 是高置信度结论。

**对 AI 网关的含义**：

1. **pip 依赖 attack surface**：guardrails-ai 是 guardrails Hub + Snowglobe 推理服务 + Cisco AI Defense / Prompt Security / Lakera 等多家 vendor SDK 的**传递依赖**。一家被投毒会沿 supply chain 推 5+ 层。liteLLM PR #28249 接 Cisco AI Defense、portkey、helicone 都把它作可选项引入。
2. **`trusted publishing` (PR #1493)** 是正确方向 — OIDC 取代 PAT 推 PyPI。但**v0.10.0 仍不 trusted publishing**（PyPI quarantine 也没 lift），OSS 治理需要耐心。
3. **组织级 PAT 策略硬要求**：guardrails-ai 写明"Restricting creation of classic GitHub PATs, fine-grained PATs require approval and expiration, **all commits must have verified signature**"。这是**任何** AI 网关在 fork guardrails-ai / presidio / garak / promptfoo 时**必对齐**的 org policy。

---

## 3. 核心信号 2：presidio v0.0.x 统一 analyzer config + 多国电话/护照识别器

**PR #1970 "Unified Analyzer Configuration"** (SharonHart, 5/17, 30 files / **+1179 / -146**) — 把 `default_analyzer.yaml` + `default.yaml` + `default_recognizers.yaml` 三个文件合并成**单一** `analyzer.yaml`，旧文件保留 deprecation banner。

**配套 PR**：

- **#2000 "feat(analyzer): add optional country filter to load_predefined_recognizers"** (ynachiket, 5/16) — `load_predefined_recognizers(..., countries=["US", "DE"])` 显式列 locale-agnostic 之外要加载的 locale，**`countries=[]` 只留 locale-agnostic**。**locale-aware 部署从"动态推断"变"参数显式"** —— 多 region 合规部署（EU 留电话 / US 加 SSN / CN 加身份证）一行 API。
- **#2025 "fix: Custom operator validate() must not invoke the lambda"** (HammadSiddiqui, 5/20, fixes #2024) — `Custom.validate()` 之前调 `new_val("PII")` 探针会**真实执行 lambda**，对**有状态 lambda（anonymizer 把 token→原值映射存到 map 里做 de-anonymize）**会插入 `{"TOKEN_1": "PII"}` 假条目，让所有 token 计数器 +1。修法 = `validate()` 只检 `callable(new_val)`，type contract 移到 `operate()` 真实数据路径。**3 个新 test**：`test_stateful_lambda_not_called_during_validate` + `test_stateful_token_map_not_corrupted_by_validate` + `test_given_non_str_lambda_then_ipe_raised_at_operate_time`。
- **#2038 "feat: add Philippine mobile number (PH_MOBILE_NUMBER) recognizer"** (5/26) / **#2006 "TR_PHONE_NUMBER"** (5/24) / **#2011 "ES passport recognizer"** (5/04) / **#2014 "Phonenumber configurable entity"** (5/14)。

**对 AI 网关的含义**：

1. **统一 config 是"production hardening"信号**：3 文件 → 1 文件看起来倒退，实际是消除"两处改一处忘"的 P0 治理洞。Anthropic / AWS Bedrock key 之类的 custom recognizer 在 3 文件分写时，container restart 顺序错就只部分生效，统一 config 让 `kubectl rollout` 可预测。
2. **`validate()` 不调 lambda** 是"框架层做 unit test 不能破坏用户状态"的范式 —— 不止 presidio，**所有用户写回调的 AI GW 组件都要对齐**：LiteLLM callback（`/proxy` callback hook）/ Higress wasm filter user script / LitServe 中间件。如果单元测试 mock 一次就改了真实 token map，CI 跑 OK、prod 全错。
3. **`countries=[]` 显式 PII locale 维度**是金融 / 医疗 / 跨境业务事实标准。gateway 暴露 `presidio.recognizers.filter.countries` 配置必须支持**空 = 全部 + 显式列表 = 子集**两种语义，不能 fallback 到默认 US。

---

## 4. 核心信号 3：garak v0.15.1 PII 探针 + 评估可观察性升级

**v0.15.1 (2026-06-05 17:24 UTC)** —— 14d 内最实质的 red-team LLM 框架升级：

1. **PR #1504 "ProPILE probes for PII leakage detection"** (stefanoamorelli, 1st contribution) —— arXiv:2307.01881 的 ProPILE methodology 落地，**默认 `active=False` + `tier=INFORMATIONAL`**（不污染主评估但可显式打开），4 个 probe 类 = `propi_leakage.twin` / `propi_leakage.triplet` / `propi_leakage.quadruplet` / `propi_leakage.unstructured`。数据集 Enron ~50 条，**Twin/Triplet/Quadruplet 测"已知 1/2/3 条 PII 推断第 N 条"**（与 `leakreplay` "训练集逐字回放"互补）。
2. **PR #1807 "cas: Add eval-level intents and digest technique/intent matrix"** (patriciapampanelli, 6/4) —— (a) `eval.intents` (per-eval) map `{passed, total_evaluated, nones}` 字段（**`nones` 不可评分的输出单独 bucket，与 `eval.nones` 顶层一致地从 `total_evaluated` 排除**）；(b) `digest.technique_intent_matrix` 顶层加性字段，按 probe 的 `demon:*` tag 投出 technique × intent 交叉表，**与 `reporting.taxonomy` 解耦**（前端可以 technique / intent 独立视图而互不影响）。Resolves #1704。
3. **PR #1839 bump javascript dependencies** / **#1781 data_path escape protection** (path traversal 修) / **#1732 remove deprecated maxrecall evaluator**（强制走 `z_rating` defcon，**新旧 defcon 公式必须 byte-equal 锁**） / **#1794 inline score_to_defcon in get_z_rating** / **#1791 regression guard for config_files dedup** —— 整体把 0.15.0 起的"重写报告层 + 改 defcon"动作收尾。
4. **PR #1738 "fix(detectors): keep packagehallucination entries with invalid dates"** / **#1796 "Fix malformed MISP tag on snowball detectors"** / **#1795 "guard max_tokens override when generator lacks it"** —— 7 个 edge case fix。

**对 AI 网关的含义**：

1. **ProPILE 探针是 PII 治理的"实际负载"**。在 gw 启 `pii_redact` 不能只在合成数据集（如 GLiNER demo）上 recall 95%，**生产环境 PII 是"已知部分推断"模式** —— 用户给三个邮箱就问"第一个人的家庭住址"。`propi_leakage.quadruplet` 正好测这条。
2. **`digest.technique_intent_matrix` 是 AIGW dashboard 模板**：纵轴 attack technique (prompt_inject / jailbreak / system_prompt_extract / homoglyph / multimodal_turn) × 横轴 attacker intent (data_exfil / pii_leak / secret_leak / code_exfil / compliance_violation) — 每个 cell 一个 probe×detector 组合，**新增 probe 立即落到正确 cell 不需重排**。前端可"按 technique 看" + "按 intent 看"互不破坏。
3. **garak 0.15.1 是 LTS-ready**：3 个测试（phrasing/sata/config dedup）+ 1 评估器回归 + 1 evaluator `z_rating` inlining + 1 path traversal 修 —— 0.15.0 → 0.15.1 这一步 99% 是稳定性 + 可观察性。**生产 CI gate 应该 pin 0.15.1+**。

---

## 5. 核心信号 4：promptfoo 0.121.15 多模态 / A2A / 凭据泄露护栏

**v0.121.15 (2026-06-05 14:21 UTC)** + v0.121.14 (6/2) + v0.121.13 (5/28) + v0.121.12 (5/21) —— **5 月 1 个月 4 个 minor release**，节奏是**安全 + 多模态 + A2A + agent-rubric**。亮点 PR：

1. **PR #9617 "feat(assertions): grade multimodal outputs"** (jameshiester-oai) — llm-rubric + redteam graders 接 image output：
   - `providerResponse.images` 传 grader，rendered prompt 包成 OpenAI 多模态 chat 消息
   - resolver 处理 data URL / base64 / URL / blob 四种 image
   - **公开 HTTP(S) image URL 自动 hydrate 到 data URL**，grader provider 不需要 web/file 访问
   - **私有 / local image URL 默认跳过**，`PROMPTFOO_ALLOW_GRADING_IMAGE_PRIVATE_URLS=true` 作显式 escape hatch（**fail-closed 默认 + 显式 opt-in**）
   - result metadata 只存 rendered text + image count，**不存 image bytes**（与 redact 思维一致）
   - 新 example `redteam-openai-image-age-bias` 演示 `bias:age` × `openai:image:gpt-image-2` × vision OpenAI grader。

2. **PR #9586 "feat: add A2A provider"** — A2A HTTP+JSON v1 first-class provider（与 MCP provider 同框架）：Agent Card discovery / `message:send` polling / `message:stream` SSE / task polling / tenant+protocol header 透传 / `transformResponse`。**Agent Card skills/capabilities 喂给 redteam 生成 context**（与 MCP tool discovery 上下文机制对齐）。**scope 显式声明 A2A HTTP+JSON v1 only**，JSON-RPC / gRPC / push webhooks 不在范围。
3. **PR #9453 "feat(assertions): add agent-rubric grader"** — coding-agent graders first-class `agent-rubric` assertion，**Codex SDK safe default** + 显式 agent-provider validation + schema/docs + regression。
4. **PR #9597 "fix(redteam): restrict remote auth to cloud host"** —— **必看**。把 saved Promptfoo Cloud bearer token 限制在 origin 与 `cloudConfig.getApiHost()`（含 on-prem）匹配的请求，单点注入在 `monkeyPatchFetch`（与 `cache.ts` `getHeadersForCacheKey` 配对），**token 永远不会泄漏到 custom `PROMPTFOO_REMOTE_GENERATION_URL` 或 `PROMPTFOO_UNALIGNED_INFERENCE_ENDPOINT`**。`isPromptfooCloudApiHost` 比 `URL.origin` 与配置 host（同 vs 异 port、http vs https、unparseable host fail-closed）。**Do not override caller-supplied `Authorization`** —— 修了一个回归：re-validating/rotating key 把旧 saved token 注入到已登录 on-prem host，**未验证 key 也会被保存**。**230 个 test 覆盖**含"custom/look-alike hosts receive no token" / "on-prem (incl. `:8443`) attaches it" / "same-host-different-port 不 attach" / "unparseable `getApiHost()` fails closed"。
5. **PR #9609 "fix(eval): escape CSV formula injection in result exports"** —— CSV export 防止 formula injection（Excel 把 `=cmd|'/c calc'!A1` 当公式执行，**CWE-1236**）。
6. **PR #9626 "fix(assertions): respect inverse when an object value can't parse output as JSON"** —— `not-equals` 路径之前 catch 块 hard-code `pass = false`，忽略 `inverse`。修法 `pass = inverse`（`false !== inverse`），`not-equals` 对 plain-text 输出正常 pass。
7. **PR #9612 "fix(auth): enable auto-share for on-prem Report Server after login"** + **#9610 "preserve cloud request headers"** —— on-prem 报告 server 在 user 登录后启用 auto-share，cloud 路径 headers 不丢。
8. **PR #9603 "fix(providers): require deployment name for no-default Azure provider types"** —— `AzureGenericProvider` 之前接受 `azure:image` / `azure:image:`（空 deployment），构建出 `undefined` deployment 的 provider，registry 接受 → 请求时 401/404。修法 = `requirePathSegment` helper，每个 type（chat/completion/assistant/foundry-agent/image）都强制。
9. **PR #9595 "feat(providers): add Azure MAI image provider"** —— `azure:image:MAI-Image-2.5` 等 4 个 model，走 `…/mai/v1/images/generations`（**不是 Azure OpenAI 的 `/openai/deployments/.../images/generations`**，**无 `api-version` param**），返回 base64 PNG + per-image cost。

**对 AI 网关的含义**：

1. **A2A provider 在 promptfoo 落地 + Anthropic 推 Claude Code / OpenAI 推 Responses API / Cisco AI Defense 接 MCP** = AIGW 6/2026 的**surface 在爆破性扩张**。**Anthropic cookbook 14 项 CMA-MCP 硬化**与 promptfoo A2A provider 在**同一周**出现不是巧合。
2. **PR #9597 凭据隔离是"自部署 AIGW"必抄**。所有用 saved cloud token + custom remote inference endpoint 的工具（不只是 promptfoo —— OpenAI Agents SDK / Anthropic SDK / Aider / Cursor 都有类似模式）都要么显式 origin allowlist 要么 fail-closed。**"saved token 跑到 attacker 的 endpoint"** 是 2026 H2 OSS 攻击 vector #1。
3. **多模态 grader 的"私有 URL 默认 fail-closed + 显式 opt-in"是"redact by default + explicit allow"范式** —— 应在所有 grader / guard / classifier 落地：`PROMPTFOO_ALLOW_GRADING_IMAGE_PRIVATE_URLS` 的语义直接搬到 LiteLLM `safe_merge_extra_body`（已落地）、Higress wasm `require_explicit_allow`、`presidio` `countries=[]` 显式。

---

## 6. 反常识 / 反模式 5 条

1. **OSS 供应链攻击的恢复期 > 24 天**：guardrails-ai 0.10.1 投毒（5/11）→ 社区问 ETA（5/18, 5/23）→ maintainer 答"working with PyPI, no estimate"（5/27）→ 6/6 仍未关闭 issue #1473。**6 周仍 quarantined 不罕见**。任何自部署 AI GW 走 PyPI install 都要有"pip 拉不到 → git tag fallback"机制，否则 dep 一断就是 prod 死。
2. **`validate()` 调 lambda 是"无伤大雅"假象**：presidio PR #2025 揭示"探针调用破坏 stateful lambda 的真实状态"是 P0 —— 单测 OK、prod 错。**任何 callback/hook/operator 设计都要在 `validate()` 阶段**显式不执行 user code**。
3. **0.10.0 vs 0.10.1 是 single-commit 投毒**：5/11 同窗口 TanStack 42 个包 + guardrails-ai 一个包，**单点入侵导致**多包同时投毒**。对策是 `pip install --require-hashes` + `pip-audit` 在 CI，**但**还要加 `pip install` 后 `python -c "import guardrails; print(guardrails.__file__)"` 对比 git tag SHA（不来自 source distribution 的 wheel 拒收）。
4. **garak 0.15.1 `digest.technique_intent_matrix` 把"technique × intent"投影作为 first-class** —— 现行 AIGW dashboard 几乎都是"按 probe type"维度切，**intent 维度**（attacker 想 exfil 什么）缺失。前端能力从"哪些探针没过"升级到"哪些攻击意图没过"是 red-team 评估的可观察性 +1。
5. **promptfoo A2A provider 与 MCP provider 在**同框架**是信号**：A2A `Agent Card.skills` 与 MCP `tools/list` 在 redteam generation context 是**完全对偶**的，"tool surface"作为攻击面已经成为 AIGW 通用抽象。

---

## 7. AIGW 5 条新硬要求 → 累加 108 条

(G-1) **OSS PyPI 供应链攻击缓解（必做）** — 任何自部署 AIGW 的 `pip install` 路径必须加：(a) `pip install --require-hashes` + lock file（uv/pip-tools/poetry），(b) `pip-audit` 在 CI，(c) `pip install` 后验 `module.__file__` 包含的 git tag SHA 必须与 lock 一致（投毒 wheel 来自非预期 source distribution），(d) dep 中含 guardrails-ai / presidio / garak / promptfoo / LiteLLM / OpenAI / Anthropic / langchain / Cisco AI Defense / Lakera 等**任何 OSS**的 prod 部署必须有 "PyPI quarantined → git tag fallback" runbook。

(G-2) **`validate()` 不调 lambda**（对所有 callback/hook/operator） — presidio PR #2025 给的范式：在 unit test 阶段的 `validate()` 只检 `callable(cb)`，type contract 移到 `operate()` 真实数据路径。**AIGW 三个落地**：(a) LiteLLM `proxy/callbacks/` user callback，(b) Higress wasm filter user script，(c) LangChain middleware。

(G-3) **Saved Cloud Token 严格 origin allowlist**（**PR #9597 范式**） — 自部署 AIGW 内置 cloud token + custom remote endpoint 的所有路径必须 `URL.origin` 与 `cloudConfig.getApiHost()` 比对，**显式不 attach to**: look-alike host / different port / http vs https / unparseable host，**显式 attach to**: exact match（incl. port-bearing on-prem）。**不要 override caller-supplied `Authorization`**（regression guard）。

(G-4) **多模态 grader / recognizer 默认 fail-closed + 显式 opt-in** — `PROMPTFOO_ALLOW_GRADING_IMAGE_PRIVATE_URLS=true` 范式 = 公开 URL 自动 hydrate 到 data URL（grader provider 不需 web 访问），私有 / local URL 默认跳过，**显式 env var opt-in**。AIGW 三件套：(a) `presidio.recognizers.filter.countries=[]` 显式 = locale-agnostic only，(b) Higress wasm `require_explicit_allow` 拉白名单，(c) LiteLLM `safe_merge_extra_body` 已落地（继续）。**grader metadata 不存 image bytes**（与 redact 思维一致）。

(G-5) **`digest.technique_intent_matrix` 投影作为 red-team 评估 first-class** — AIGW 报告层加 (a) per-eval intents map `{passed, total_evaluated, nones}` + (b) top-level technique×intent 交叉表 digest。**前端可"按 attack technique" + "按 attacker intent"独立视图**。新 probe 加 `demon:*` tag 自动落到正确 cell 不需重排。

---

## 8. 引用与数据来源

### GitHub 仓库
- guardrails-ai/guardrails — [v0.10.2 release](https://github.com/guardrails-ai/guardrails/releases/tag/v0.10.2), [SECURITY_ADVISORY.md](https://github.com/guardrails-ai/guardrails/blob/main/SECURITY_ADVISORY.md), [issue #1473](https://github.com/guardrails-ai/guardrails/issues/1473), [PR #1484](https://github.com/guardrails-ai/guardrails/pull/1484), [PR #1493](https://github.com/guardrails-ai/guardrails/pull/1493), [GHSA-xmpw-2vmm-p4p6](https://github.com/guardrails-ai/guardrails/security/advisories/GHSA-xmpw-2vmm-p4p6)
- microsoft/presidio — [PR #1970 Unified Analyzer Config](https://github.com/microsoft/presidio/pull/1970), [PR #2000 country filter](https://github.com/microsoft/presidio/pull/2000), [PR #2025 validate() fix](https://github.com/microsoft/presidio/pull/2025), [PR #2038 PH_MOBILE](https://github.com/microsoft/presidio/pull/2038), [PR #2006 TR_PHONE](https://github.com/microsoft/presidio/pull/2006), [PR #2011 ES passport](https://github.com/microsoft/presidio/pull/2011), [PR #2014 configurable Phonenumber](https://github.com/microsoft/presidio/pull/2014)
- NVIDIA/garak — [v0.15.1 release](https://github.com/NVIDIA/garak/releases/tag/v0.15.1), [PR #1504 ProPILE](https://github.com/NVIDIA/garak/pull/1504), [PR #1807 cas digest](https://github.com/NVIDIA/garak/pull/1807), [PR #1839 js deps](https://github.com/NVIDIA/garak/pull/1839), [PR #1781 path traversal](https://github.com/NVIDIA/garak/pull/1781), [PR #1732 remove maxrecall](https://github.com/NVIDIA/garak/pull/1732)
- promptfoo/promptfoo — [0.121.15 release](https://github.com/promptfoo/promptfoo/releases/tag/0.121.15), [PR #9617 multimodal](https://github.com/promptfoo/promptfoo/pull/9617), [PR #9586 A2A provider](https://github.com/promptfoo/promptfoo/pull/9586), [PR #9453 agent-rubric](https://github.com/promptfoo/promptfoo/pull/9453), [PR #9597 cloud auth restrict](https://github.com/promptfoo/promptfoo/pull/9597), [PR #9609 CSV formula injection](https://github.com/promptfoo/promptfoo/pull/9609), [PR #9626 inverse JSON](https://github.com/promptfoo/promptfoo/pull/9626), [PR #9612 auto-share](https://github.com/promptfoo/promptfoo/pull/9612), [PR #9610 preserve headers](https://github.com/promptfoo/promptfoo/pull/9610), [PR #9603 require deployment](https://github.com/promptfoo/promptfoo/pull/9603), [PR #9595 Azure MAI](https://github.com/promptfoo/promptfoo/pull/9595), [PR #9557 DAG cycle](https://github.com/promptfoo/promptfoo/pull/9557), [PR #9614 validation harden](https://github.com/promptfoo/promptfoo/pull/9614)
- TanStack/router — [GHSA-g7cv-rxg3-hmpx (CVE-2026-45321)](https://github.com/TanStack/router/security/advisories/GHSA-g7cv-rxg3-hmpx)
- proPILE 论文 — arXiv:2307.01881

### 上一轮 guardrails 报告（避免重复）
- [2026-06-06-0450 guardrails-production-slo-failures](./2026-06-06-0450-aigw-guardrails-production-slo-failures.md)
- [2026-06-06-0410 guardrails-prompt-injection-middleware](./2026-06-06-0410-aigw-guardrails-prompt-injection-middleware.md)
- [2026-06-05-1938 guardrails-streaming-trust](./2026-06-05-1938-aigw-guardrails-streaming-trust.md)
- [2026-06-05-1858 guardrails-runtime-defense](./2026-06-05-1858-aigw-guardrails-runtime-defense.md)
- [2026-06-05-1819 guardrails-roundup](./2026-06-05-1819-aigw-guardrails-roundup.md)
