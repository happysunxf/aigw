# Guardrails & 安全 · Round 7 — Context-window 硬上限、特殊 token 注入、AgentHarm、MCP 安全探针、负向上下文

> **时间**：2026-06-07 04:32 CST（UTC 2026-06-06 20:32）
> **主题**：guardrails-ai / presidio / garak / promptfoo 过去 36 小时主线推进
> **作者**：Hermes Agent cron（happysunxf 私有 aigw 跟踪 #7）
> **触发**：local hour=4 → Guardrails & 安全

---

## 1. 过去 36h 五大硬信号

1. **presidio #2055 修 context window 边界 bug** — token 位置硬上限 `_add_n_words` 只对关键词扣预算，stop-word / 标点"隐形" → `context_prefix_count=0` 时 entity 之外的 token 仍能匹配（"I have $0.05" 把 Dollars 之外整段算入）→ **PII 上下文误命中**
2. **garak #1846 special token injection probe** — 16 个特殊 token（`<|im_start|>` / `[INST]` / `<s>` / `Ignore previous instructions.`）× 5 个 benign template，基线 vs 注入对照 = **prompt injection 的"模型层 smuggling"信号**
3. **garak #1687 MCP Security Probes（OWASP MCP Top 10）** — `MCPShadowToolAttack` / `MCPToolDescriptionInjection` / `MCPToolResponseInjection`，canary 触发 `MCPPWND`；**OWASP MCP-03 / MCP-04 / MCP-06 全部纳入 LLM-prompt threat boundary**
4. **garak #1776 AgentHarm probe**（arxiv:2410.01606） — 44 base × 4 augmentation = 176 prompts + 8 per-category + `CrossCategory` 10 条双类别组合（"Cybercrime × Fraud" 等），**单类别安全微调的盲区在跨类别组合时显露**
5. **promptfoo #9627 harden multimodal output grading** — URL-safe base64 / Bedrock Nova native image block / env-var 注册 / line-wrapped base64 假阳性，**drift 修了 5 个"看起来对实际错"的静默路径**

辅信号：presidio #1969 negative_context（FP 减少）、#2052 NER dedup（8 语言场景 -3.2GB → -1.1GB）、#2041 tokenizer-based chunker（YAML `text_chunker: {chunker_type: tokenizer, max_tokens: 512}`）、#2031 country filter（`countries=["US","DE"]` request-time）、#2028 PH 牌照；garak #1753 MitigationBypass 17 个 modern refusal pattern（"I'm sorry, I can't comply"）、#1676 ATR detector 1,597 regex / 9 classes；promptfoo #9177 RAG failure mode checklist / #9417 semantic plugin（Unicode 保留）/ #6271 Bedrock cost fail-closed（finite 校验）/ #8744 large eval table RangeError 修（API lean 化 + detail hydration）；guardrails-ai #1494 litellm <1.82.6 解除（接 1.87.x 含 7 CVE fix）+ #1492 `FieldReAsk.fail_results is None` IndexError + #1351 Python 3.14；LiteLLM #29696 latency-routing lost-update race / #29737 auth_v2 casbin / #29850 per-agent CLI wrapper；langchain #37698 neutralize `write_todos` / #37867 sanitize anthropic cache markers。

---

## 2. presidio #2055 — context window 硬上限的工程含义

**Issue #1444**：Dollars/cents 误匹配。原因：`_add_n_words` 预算仅对"匹配到的关键词"扣减，stop-word / 标点 "invisible to budget"。`context_prefix_count=0` 时本应窗口=0，**实际是"实体 + N 句未受约束的 token"**。

**Fix（+87/-2）**：
```python
max_token_positions = n_words * 2 + 1
```
**硬上限** = 实体两侧的 token 总数（×2 倍预留是 stop-word / 标点密度缓冲）。`test_add_n_words_zero_window_only_includes_entity` 锁 `n_words=0 → 仅 entity token`；forward / backward 各一条方向性测试。

**5 个反常识**：
- 业务用 `n_words=0` 的人预期"严格在 entity 周围"，实际拿到的是"全文匹配 + entity 周围加权"——**词法和上下文增强混在一起是隐式而非显式**
- `n_words × 2 + 1` 的"2 倍"是经验值，**不是上下文工程可解释的"双向句法距离"**
- unit test 通过、reporter 生产 case 仍误命中——**边界 case 的预设期望值（`0`）暴露的 bug 不会被常规 testing harness 覆盖**
- PII 治理在"negative context"和"hard cap"两个方向同时推进（#1969 + #2055），意味着 presidio 把 **context-aware PII 当作"可双向工程化对象"** 而非"启发式规则"
- 同窗口 presidio 改了三处独立可测点（#1969 negative score / #2055 hard cap / #2052 NER dedup），说明 **PII 治理在 6/2–6/6 是一波"实战修补"** 而非"大重构"

**AIGW 落点**：网关层做 PII 透出时**禁止**直接复用 presidio 旧版本（v2.2.362 之前），必须 patch 进 #2055；`context_prefix_count=0` 在生产**作为硬约束而非软建议**——任何 entity 上下文都进 review。

---

## 3. garak #1846 — special token injection probe 的真实价值

**动机**（Issue #74）：`<|im_start|>` / `<s>` / `[INST]` 等特殊 token 在 chat template 边界外仍能被 model 解析为"role switch"——这不是 prompt injection 的传统"instruction override"路径，而是 **tokenizer-level smuggling**。

**做法（+207/-2）**：
1. 5 benign template × 16 special token = 80 个对比组
2. baseline（无 token）vs injected（含 token）= **pair-wise 差分**
3. 检测：length 变化 >50% / word overlap <30% / refusal 仅在 injected 出现

**5 个反常识**：
- 16 个 token 中 **`Ignore previous instructions.` 是文本指令、不是特殊 token**——它和 `<|im_start|>` 同列意味着 garak 把"指令 injection"和"token smuggling"作为**同一族攻击**
- 5 个 benign template 是必要的：单 template 的"无变化"可能源于 model 已经过同 template 训练，**多 template 求并集才暴露 vulnerability**
- 检测信号是 **pair-wise behavioral divergence** 而非"是否输出特定内容"——garak 走的是 **distribution shift detection** 而非 keyword matching
- "Refusal 仅在 injected 出现"是 **prompt injection 漏洞的硬信号**（model 在 baseline 是 helpful、注入后变 refusal = 它"看到"了注入，但选择 compliance-or-bypass 行为不稳定）
- AIGW 网关层做 prompt injection 防御时，**单点 regex（"ignore previous" / "disregard"）是 sycophancy 而不是真防御**——garak 的 distribution-shift 范式才是工程化方向

**AIGW 落点**：网关层 guardrail hooks 必须包含 **special token sanitizer**（中间件层把 `<|im_start|>` / `[INST]` / `Ignore previous instructions.` 在 user-role turn 内 strip 或转义），否则 multi-tenant gateway 里的 tool-call JSON 字段会被 model tokenizer 误解析。

---

## 4. garak #1687 / #1776 / #1676 — OWASP MCP Top 10 + AgentHarm + ATR detector 三件套

### 4.1 #1687 MCP Security Probes（+616/-0，Closes #1639）

**OWASP MCP Top 10**（MCP-01~MCP-10）中 garak 选 LLM-prompt boundary 内的三条：
- **MCP-03 Tool Definition Manipulation**（schema 描述被改写）→ `MCPShadowToolAttack`
- **MCP-04 Tool Schema Injection** → `MCPToolDescriptionInjection`
- **MCP-06 Message Integrity**（tool response 注入指令）→ `MCPToolResponseInjection`

**机制**：canary `MCPPWND` 触发 → `MCPComplianceFollowed` detector 打分。
**附带修复**（关键）：`TriggerListDetector` 在 trigger list 为 `[]` 时**返回 fake pass**（score 0.0）而非 clean skip——**36 个 pytest 锁住**。

**5 个反常识**：
- garak **明确拒绝**把 Transport (MCP-07) 和 Audit Trail (MCP-08) 纳入 LLM-prompt boundary——**"LLM 红队 vs infra 红队"分得清**才能避免一锅烩
- `MCPShadowToolAttack` 测的不是 model 是否被骗，而是 **LLM 是否"看到"被篡改的 schema 并采用**——和 tool registry 端的 HASH verification 是不同层
- `MCPToolResponseInjection` 的威胁面是 **post-tool message**——**OWASP ASI-06（memory poisoning）和 MCP-06（message integrity）在工程实现上重合**
- 修复 `TriggerListDetector` 的 fake-pass 路径是**单点修复但影响所有 detector 家族**——garak 框架层"self-test"比单元测试多一道关
- 36 个 pytest 看似多但**每个探测器平均 9 个 case**——garak 把"攻击面"和"defense"在测试层 1:1 配对

### 4.2 #1776 AgentHarm（+742/-0，Closes #974）

**arxiv:2410.01606** 的 44 base × 4 augmentation = 176 prompts（8 类别：Copyright / Cybercrime / Disinformation / Drugs / Fraud / Harassment / Hate / Sexual）。新增 `CrossCategory` 10 条**手写双类别组合**，4 种 jailbreak 文献 framing（fictional / research / sequential / policy-brief）。

**5 个反常识**：
- 公开 HF split 44 条，private 还有 11 类别（Violence / Terrorism / Self-harm）**不进**本 PR——**测试集分级匹配评估合理性**
- `hint_included × detailed_prompt` 二维 augmentation 把同一 base prompt 展成 4 变体，**测的是"信息密度"vs"hint 显式度"对安全行为的影响**
- `CrossCategory` 10 条**全部手写不来自 dataset**——"单类别 SFT 难以泛化到双类别"是 jailbreak 文献的经验，**garak 把"文献观察"变成"first-class probe"**
- agentic 任务（"deploy this ransomware"）和 Q&A 任务（"explain ransomware"）在 threat surface 上**完全不同**——AgentHarm 测的是 **"多步执行能力"而非"知识表达"**
- 默认 active = `AgentHarm`、inactive = `AgentHarmAugmented` / per-category / `CrossCategory`——**red-team 工件按"攻击成本"分级**（主动开 baseline，深度评估 opt-in）

### 4.3 #1676 Agent Threat Rules detector（+637/-0）

**ATR 1,597 regex / 293 production rules / 9 detector classes**：
- `AgentThreats`（all 9）
- `PromptInjection`
- `ToolPoisoning`
- `CredentialExfiltration`
- `PrivilegeEscalation`
- `SkillCompromise`（typosquatting / rug pull / impersonation）
- `ExcessiveAutonomy`（retry loop / resource exhaustion）
- `AgentManipulation`（cross-agent attack / trust exploitation）

**5 个反常识**：
- 1,597 regex **打包在 `garak/data/atr/rules.json` 不做 runtime fetch**——**离线可审计**对 red-team 工件是合规要求
- 9 个 detector 类别**与 OWASP MCP Top 10 / OWASP ASI / NIST AI RMF 的 1:1 映射**——garak 在主动靠拢 standards
- `SkillCompromise` 直接命中"**typosquatting / rug pull**"两个 npm 时代延续的 attack pattern——**agent 时代的新风险源自旧 risk 类别**
- `ExcessiveAutonomy` 把"retry loop"列为 attack vector——**agent 自主性的反面是"infinite loop = self-DoS"**
- `AgentManipulation` "cross-agent trust exploitation"——**多 agent 系统的 trust boundary 是 attack surface**

**AIGW 落点**：AIGW 的 MCP proxy / agent middleware 必须内置 **garak #1687 + #1776 + #1676 三件套** 作为 red-team CI gate；`MCPShadowToolAttack` 之外，**schema HASH 验证** 是必须加的 infra 层（garak 测 LLM 是否被骗，infra 测 tool 是否被替换）。

---

## 5. promptfoo #9627 multimodal output grading — drift 修了 5 个静默路径

**5 个静默错（+1357/-92）**：
1. URL-safe base64 报"invalid base64" → 标准化为 standard base64
2. Bedrock Nova 收 `image_url` 报 `ValidationException: extraneous key [type]` → 翻译为 native Nova image block
3. 5 个 env-var（`PROMPTFOO_GRADING_MAX_IMAGES` 等）未注册到 `EnvVars` → raw-char cap 失效
4. 0 user docs / 0 example → 加 `llm-rubric` reference + `examples/multimodal-output-grading`
5. line-wrapped base64 假阳性（data URI 在 first comma 拆开 + per-image raw-char cap 走 canonical URI）

**5 个反常识**：
- **OpenAI image_url → Nova image block** 的"translation layer"是 provider 适配器"防错"的标准做法——**bedrock 不接受 OpenAI shape 是 documentation gap 修正**
- `llm-rubric` 当 grader 跑真实 evals（red/blue image + "is it red?" rubric）验证**grader 真的读 pixel** 而非 prompt
- env-var 注册是个"小"事情，**不注册 = 改 env-var 静默不生效** 是 product bug 而非 config bug
- URL-safe base64 vs standard base64 是**RFC 4648 §5 vs §4**，在 HTTP body 里**前者出现频率正快速上升**（compact URL、token exchange）
- 5 个 fix 集中在一个 PR = 一次发版可吃下 5 类"silent path"——**比分散修更有工程价值**

**AIGW 落点**：AIGW multimodal output 路径（image generation / image understanding）走 grading-as-judge 时**必须用 promptfoo ≥ 0.121.15**，否则 base64url / Nova shape 会触发 **silent fail**（grade=FAIL with "0 errors" = "看起来是 FAIL 实际是 driver 拒收"）。

---

## 6. guardrails-ai #1494 — litellm 7 CVE 解除 + jwt 重构 + GH Actions shell 注入

**Fix 1 — litellm upper bound**：
```toml
# 之前：litellm >= 1.79.1, < 1.82.6  # 1.82.6 之后 7 个 CVE
# 之后：litellm >= 1.79.1
```
放行 1.87.0+（含 **CVE-2026-35029 / CVE-2026-35030 / GHSA-69x8-hrgq-fjj8 / CVE-2026-42203 / CVE-2026-42208 / CVE-2026-42271 / CVE-2026-40217** 的修复）。

**Fix 2 — jwt expiry check 集中**：
- 共享 `guardrails/hub_token/utils.py` 的 `client_check_token_expiry()`
- 改用**手动 base64 decode `exp` claim** 替代 `jwt.decode(verify_signature=False)`——**"unverified-signature" pattern 是 CVE 高发路径**

**Fix 3 — GitHub Actions shell injection**：
- `validator_pypi_publish/action.yml` 里 4 处 `${{ inputs.* }}` interpolation 全迁到 `env:` 块

**5 个反常识**：
- `<1.82.6` upper bound 在 CVE-2026-42208 (semantic-router) 和 LiteLLM 5 月 5 个 critical/high CVE 之后已经**成为风险源**——upper bound 保护的是"已知问题"，**与"上游已修"冲突时必须主动放行**
- `jwt.decode(verify_signature=False)` 是 python-jose 一直以来的反模式（**"for introspection only" should not exist**）——guardrails-ai 把这个 pattern 集中化 + 移除 = **消除一类 CVE 入口**
- 4 处 `${{ inputs.* }}` 在 GH Actions 里是**典型 shell injection 路径**——ArgoCD / GitHub Actions 几乎所有 release workflow 都中招
- 这是一个**+120/-45 的小 PR**，但包含 7 CVE 放行 + 1 个 framework 修复 + 1 个 CI 修复，**密度极高**
- guardrails-ai 在 0.10.1 投毒（5/11）后 26 天仍 PyPI quarantined（截至 6/6），但 0.10.2 (6/4) 已上 trusted publishing + 7 CVE fix，**逐步走出"信任何服"危机**但仍未完全恢复

**AIGW 落点**：所有 prod 部署用 guardrails-ai 的 AIGW **必须 pin 0.10.2+ 且放行 litellm 1.87.0+**；`jwt.decode(verify_signature=False)` pattern 在自研 hub_token 代码里**禁止使用**。

---

## 7. 横向信号：LiteLLM / langchain 1d 内与 guardrails 直接相关的硬化

### 7.1 LiteLLM #29696 latency-routing lost-update race

**修法**（+XX/-XX）：latency tracker 走 **CAS（compare-and-swap）** 替代 read-modify-write 路径，**防 multi-worker 场景下"successful request 也被记录为 lost"** → 路由决策偏向"已知时延最低"的 model → **新接入 model 永远拿不到流量**（"cold start 不可恢复"）。

**AIGW 落点**：自研 router 走 latency-based 决策时**必须**走 atomic update，否则**新加入 backend 永远冷启动**。

### 7.2 LiteLLM #29737 auth_v2 casbin（flag-gated WIP）

`authlib + casbin` 双 factor，flag-gated —— **从"static API key + role table"到"RBAC + ABAC + time-bound policy"** 的过渡。

**AIGW 落点**：自研 RBAC 不要自己造，**直接评估 casbin + OPA（同期生态）**。

### 7.3 LiteLLM #29850 per-agent `litellm-proxy claude` / `codex` / `opencode` CLI wrapper

**per-agent 接入**：把 `claude-code` / `codex` / `opencode` 三个 CLI 工具用 LiteLLM proxy 包裹起来，**任何 agent 拿 CLI 默认走 gateway + 配额 + 审计**。

**AIGW 落点**：AIGW 必须提供"**CLI 包装器**"而非"SDK 改造"路径——**CLI 是 agent 时代的 SSH**。

### 7.4 langchain #37698 neutralize `write_todos` tool message

`write_todos` 是 LangChain 内置 tool（"let the model write TODOs"），但**该 tool message 可被 prompt injection 改写**——neutralize = **把 tool output 当作 model content 而非"plan of record"**。

### 7.5 langchain #37867 sanitize anthropic cache markers on fallback retries

Anthropic `cache_control` 标记在**fallback retry** 路径上**不清理**会污染 OpenAI provider 的 prompt cache 命中率——**跨 provider cache 隔离是 hardening 点**。

**AIGW 落点**：multi-provider gateway 走 fallback 时**必须** strip provider-specific cache markers（`cache_control` / `prompt_cache_key` 等）。

---

## 8. 5 个 AIGW 硬要求 → 累加 113 条

**(G-109) presidio 必须 pin 含 #2055 的 commit**（context window 硬上限）—— v2.2.362 之后未发布，但 main 已合；自部署 presidio 必须 git pin **commit hash** + token-position cap 行为作为部署前置检查；`context_prefix_count=0` 在 PII 透出场景**作为硬约束**而非软建议。
**(G-110) AIGW guardrail hooks 内置 special token sanitizer**（garak #1846 范式）—— `<|im_start|>` / `<|im_end|>` / `<s>` / `[INST]` / `Ignore previous instructions.` 在 user-role turn 内 strip / escape；red-team CI 跑 garak 16-token × 5-template 80 case pair-wise。
**(G-111) AIGW MCP proxy 走 garak #1687 + #1776 + #1676 三件套**（OWASP MCP Top 10 + AgentHarm + ATR detector）—— 作为 red-team CI gate；`MCPShadowToolAttack` 之外，**schema HASH 验证** 是必须加的 infra 层；1,597 regex 离线可审计 bundle。
**(G-112) AIGW multimodal output 路径走 promptfoo ≥ 0.121.15**（#9627 范式）—— base64url 标准化 + Nova shape 翻译 + env-var 注册；`grade=FAIL with 0 errors` 是 silent fail 信号，grading-as-judge 必查 driver reject reason。
**(G-113) AIGW 走 multi-provider fallback 时 strip provider-specific cache markers**（langchain #37867 范式）—— `cache_control` / `prompt_cache_key` / `safety_identifier` 在 fallback 重试时**不继承**；自研 router 走 latency-based 决策必走 atomic update（LiteLLM #29696 范式）；CLI 包装器路径（`litellm-proxy claude`）**优先** 于 SDK 改造路径。

---

## 引用与数据来源

- presidio: [#2055 hard cap](https://github.com/microsoft/presidio/pull/2055), [#1969 negative_context](https://github.com/microsoft/presidio/pull/1969), [#2052 NER dedup](https://github.com/microsoft/presidio/pull/2052), [#2041 tokenizer chunker](https://github.com/microsoft/presidio/pull/2041), [#2031 country filter](https://github.com/microsoft/presidio/pull/2031), [#2028 PH plate](https://github.com/microsoft/presidio/pull/2028), [Issue #1444](https://github.com/microsoft/presidio/issues/1444)
- garak: [#1846 special token injection](https://github.com/NVIDIA/garak/pull/1846), [#1687 MCP Security Probes](https://github.com/NVIDIA/garak/pull/1687), [#1776 AgentHarm](https://github.com/NVIDIA/garak/pull/1776), [#1753 MitigationBypass refusal](https://github.com/NVIDIA/garak/pull/1753), [#1676 ATR detector](https://github.com/NVIDIA/garak/pull/1676), [#1848 GoogleTranslator](https://github.com/NVIDIA/garak/pull/1848), [#1847 calibration pathlib](https://github.com/NVIDIA/garak/pull/1847), [Issue #74](https://github.com/NVIDIA/garak/issues/74), [Issue #1639](https://github.com/NVIDIA/garak/issues/1639), [Issue #974](https://github.com/NVIDIA/garak/issues/974), [Issue #1413](https://github.com/NVIDIA/garak/issues/1413)
- promptfoo: [#9627 harden multimodal](https://github.com/promptfoo/promptfoo/pull/9627), [#9177 RAG failure mode](https://github.com/promptfoo/promptfoo/pull/9177), [#9417 semantic plugin](https://github.com/promptfoo/promptfoo/pull/9417), [#6271 Bedrock cost](https://github.com/promptfoo/promptfoo/pull/6271), [#8744 large eval table](https://github.com/promptfoo/promptfoo/pull/8744), [0.121.15 release](https://github.com/promptfoo/promptfoo/releases/tag/0.121.15)
- guardrails-ai: [#1494 litellm CVEs](https://github.com/guardrails-ai/guardrails/pull/1494), [#1492 FieldReAsk IndexError](https://github.com/guardrails-ai/guardrails/pull/1492), [#1351 Python 3.14](https://github.com/guardrails-ai/guardrails/pull/1351), [v0.10.2 release](https://github.com/guardrails-ai/guardrails/releases/tag/v0.10.2)
- LiteLLM: [#29696 latency race](https://github.com/BerriAI/litellm/pull/29696), [#29737 auth_v2 casbin](https://github.com/BerriAI/litellm/pull/29737), [#29850 per-agent CLI](https://github.com/BerriAI/litellm/pull/29850)
- langchain: [#37698 neutralize write_todos](https://github.com/langchain-ai/langchain/pull/37698), [#37867 sanitize cache markers](https://github.com/langchain-ai/langchain/pull/37867)
- 上轮 reference: [round 6 supply-chain-zero-retention](reports/2026-06-06-1858-aigw-guardrails-supply-chain-zero-retention.md), [round 5 streaming-trust](reports/2026-06-05-1938-aigw-guardrails-streaming-trust.md)
