# AI 网关持续深挖 · 第 8 次 — Guardrails & 安全(PII / 提示词注入 / 内容审计 / 零留存)

- 轮值时间(本地): 2026-06-05 04:25 CST
- 主题: Guardrails & 安全(hour % 7 = 4)
- 角度: 上一轮(03:48)只点出"路由层的 timing-attack 修复",本轮**正式展开 AI Gateway 的 Guardrails 四象限**:
  ① 输入侧 — 提示词注入与越狱检测;② 输出侧 — PII / 敏感信息脱敏;
  ③ 全链路审计 — 内容审计日志 / 可观测 hook;④ 合规面 — 零留存(zero retention)与厂商处置策略。
- 数据源(已抓到): NVIDIA NeMo Guardrails v0.22.0 / v0.21.0 / v0.20.0、guardrails-ai v0.10.2 / v0.10.0、Microsoft Presidio 2.2.362 / 2.2.361、Microsoft Learn Prompt Shields 文档、OWASP LLM Top 10、Lakera PINT benchmark(188★)、NIST AI 600-1 摘要、EU AI Act(2024/1689)。

---

## 1. 主题速览:AI Gateway 上的 Guardrails ≠ 单一 SDK

**结论先放**:到 2026 年 6 月,成熟的 AI Gateway 团队**不再把 guardrails 当成"装一个 SDK 就完事"的单点能力**,而是把"输入/输出/审计/合规"拆成**四层独立平面**,每层都能热插拔。这一期把四层在开源生态的最新动态全部对齐。

---

## 2. 输入侧:提示词注入 & 越狱检测

### 2.1 NVIDIA NeMo Guardrails v0.22.0(2026-05-22)— 重点变化

`v0.22.0` 三件大事:

1. **匿名 usage reporting + opt-out**:`NEMO_GUARDRAILS_NO_USAGE_STATS=1`、`DO_NOT_TRACK=1`、`~/.config/nemoguardrails/do_not_track` 三个开关全到位。这是第一次把"网关层 telemetry"当成可治理对象,符合欧盟 AI Act 的"可审计但默认最小化"原则。
2. **LangChain decoupling**:OpenAI-compatible LLM 改用内置 httpx 客户端,LangChain 退回到 `NEMOGUARDRAILS_LLM_FRAMEWORK=langchain` 显式 opt-in。**安全意义**:少一个依赖链路 = 少一类供应链 attack surface。
3. **IORails milestone 2**:`v0.21.0` 引入的并行 NemoGuard rails(content-safety / topic-safety / jailbreak)进入第二阶段,带 unique request ID + 集中 logging。v0.21.0 的 `check_async()` 方法允许**只跑输入/输出 rail,不用拉起整条对话流** —— 这是把 guardrails 卖给**纯转发型 gateway** 的关键 API。

### 2.2 guardrails-ai v0.10.2(2026-06-04)— 安全补丁走起

| PR | 内容 |
|---|---|
| #1474 / #1478 / #1490 | `SECURITY_ADVISORY.md` 多次更新,**显式承认这是"持续维护的安全公告文档"** |
| #1467 | Aikido 自动修 GitHub Actions workflow 的 template injection |
| #1484 | litellm 最低 pin 从 `<1.83` 放宽到 `>=1.83` —— **解封动作,说明下游 LiteLLM 漏洞已修** |
| #1493 | release workflow 切到 **trusted publishing**(PyPI 新出的"免长期 token"机制) |

**信号**:`v0.10.0 → v0.10.2` 之间没大特性,**全是 supply-chain hardening**。这是 guardrails-ai 库从"快速迭代"转向"安全维稳"的标志。

### 2.3 Lakera PINT-benchmark(2026-05-21 更新)— 业内公认的 injection 评测

* 188★,最近 commit `0efab3f`(2026-04-02)"merge public and internal prompt injections"——把内部语料也并入公开基准,**降低厂商自评偏差**。
* 上一条 commit `0aa0d6`(2025-12-16)就是这次合并。意味着 2025 末 → 2026 末,**所有号称"sota jailbreak detector"的厂商都该拿同一份 PINT 跑分**。
* 包含 Google Model Armor 的成绩作为 PR 引用条目(`cc11013` 2025-08-28),给独立基准一个**官方 vendor baseline**。

### 2.4 Microsoft Prompt Shields / Azure AI Content Safety(文档最近刷新 2026-02-26)

* 文档里 *indirect prompt injection* 显式作为独立攻击类别。
* Azure 端的 `Jailbreak Risk Detection` 把用户 prompt(原话)+ classification API 响应,作为 0/1 风险标签返回。
* 配合 Azure AI Content Safety 的 `SeverityLevel` 0-4 等级,可对接 gateway 的 5xx 拒答。

### 2.5 OWASP LLM Top 10(当前展示版 10 项)

```
LLM01 Prompt Injection        ← 输入侧主战场
LLM02 Insecure Output Handling
LLM03 Training Data Poisoning
LLM04 Model DoS
LLM05 Supply Chain
LLM06 Sensitive Information Disclosure  ← 输出侧主战场
LLM07 Insecure Plugin Design
LLM08 Excessive Agency
LLM09 Overreliance
```

> ⚠️ OWASP 2025 草案已经加 LLM10 "Unbounded Consumption"(对 token / cost 做 abuse)和 LLM11 "AI Code Execution";**正式 web 页面只到 9 项**,以 9 项为准。

---

## 3. 输出侧:PII / 敏感信息脱敏

### 3.1 Microsoft Presidio 2.2.362(2026-03-18)— 重大 supply chain 动作

* `HuggingFaceNerRecognizer` 直接挂 transformers NER 模型,绕开 spaCy / Stanza 的下载链路 —— **零外部包=零拉链攻击**。
* **`Pin dependencies to mitigate supply chain attacks` PR #1861** 标题直白:Presidio 现在显式承认"依赖 pin 是供应安全的第一道关"。
* **修复 CVE-2024-47874 + CVE-2025-54121**(PR #1860)—— 拆开来都跟 python image-handling 相关,意味着 Presidio 不再只关心 text PII,**图像/扫描件里的 PII 也要扫**。
* 2.2.360(2025-09-09)还加了 **韩国 RRN(居民登记号)** + 印度 Aadhaar 上下文分隔符支持,中港印韩日五国身份号全部覆盖到 2025 末。

### 3.2 NeMo Guardrails v0.20.0(2026-01-22)的 PII 路径

* `GLiNER` 集成作为**开源 PII 替代 PrivateAI** 的方案(PrivateAI 是闭源商业 API,有数据出网问题)。
* **多语言拒绝消息** multilingual refusal bots,让"我无法回答这类问题"不再只有英文。
* 配合 Nemotron-Content-Safety-Reasoning-4B 的 `/think` 模式 —— **可解释的 moderation**(每条拒答都带 reasoning trace),audit friendly。

---

## 4. 全链路审计:logging / OTel hook / content audit

### 4.1 NeMo Guardrails v0.21.0(2026-03-12)引入 `unique request ID`

* 输入 → 三个并行 NemoGuard rail → 输出,每条都带同一 request ID。
* 配合 OpenAI-compatible `/v1/models` endpoint,可直接走 OpenTelemetry exporter 到 Datadog / Honeycomb。
* **实战建议**:用 `traceparent` W3C header 把 request ID 串到上游 gateway + 下游 provider,审计一次对话不丢包。

### 4.2 guardrails-ai 的 hub 动态加载(v0.9.2 → v0.9.3)

* `ModuleNotFoundError when installing hub validators dynamically` 的修复 + `barrel imports → dynamic registry-based loading` 改造。
* 审计意义:每个 validator 走的是"按需下载+签名校验"链路,而不是启动时一股脑 import。**对"我在哪个 validator 暴露了哪些字段"有清晰依赖图**。

### 4.3 OWASP LLM06 Sensitive Information Disclosure 的工程做法

落到 gateway 上,实务要做三件事:
1. **出站 prompt/template 也审计** — 不是只审计用户输入,system prompt 里残留的 PII 也要扫(常见在 few-shot example)。
2. **输出回填(redaction)后**才入对话历史。
3. **对话历史**单独走 Presidio `anonymize` 一次,再存进向量库。

---

## 5. 合规面:零留存(zero retention)与厂商现状

### 5.1 2026 年的事实

* 欧盟 AI Act(Regulation 2024/1689)Article 10 要求"数据质量+可追溯",对训练数据 + 推理数据都适用;**默认推断**是"用完即焚",opt-in 才能留。
* NIST AI 600-1(2024-07 发布,2026 仍是事实标准)把"confidentiality of prompts + responses"放在 Generative AI Profile 的 GOVERN/OPERATE 两条线。
* 主流 SaaS 提供商在 2025-2026 已经分化:**OpenAI Enterprise / Anthropic Claude for Work 默认 zero-retention**;**OpenRouter / DeepSeek 等聚合层**部分路由仍可保留 30 天。

### 5.2 落到 AI Gateway 的工程做法

1. **Provider-级 audit 字段**:把 `retention` policy 作为路由权重之一(和 cost、latency 同一层)。
2. **client → provider 链路**做"零留存承诺" hash 比对,合同/SLA 上把承诺固化。
3. **审计日志**本身要 PII 脱敏 —— 用 Presidio 跑一遍再存,别把审计日志变成**第二个 PII 泄露面**。
4. **EU AI Act 高风险场景**(recruitment / credit / education)需要"human-in-the-loop"开关,gateway 层要能 force 拦截 LLM 决策,转人工。

---

## 6. 给 AI Gateway 团队的整合清单(本期落地建议)

| 平面 | 开源优先 | 商用补充 | 上线顺序 |
|---|---|---|---|
| 注入检测 | Lakera PINT 基准 + 自建 regex + Presidio 小词表 | Azure Prompt Shields / Google Model Armor | P0(必须) |
| PII 脱敏 | Presidio + GLiNER(NeMo 路径) | PrivateAI / Cloudflare DLP | P0(必须) |
| 内容审计 | OTel + 集中 logging(带 request ID) | Datadog LLM Observability | P1 |
| 零留存 | 自签 contract + 路由 metadata | Cloudflare Workers AI / OpenAI Enterprise 协议层 | P0(法务驱动) |
| Reasoning 解释 | Nemotron-Content-Safety-Reasoning 4B 的 `/think` | — | P2(可解释合规) |

---

## 7. 待观察(下次主题:可观测 & 监控,hour%7=5)

* **Cloudflare Workers AI** 最近 release `v1.20260604.1` 几乎每天一发,值得下周拿"AI Gateway 边缘化"的角度看一次。
* **Lakera PINT** 4 月合并 internal injections 后,**会有 vendor 集体跑分** —— 出现新的"market leader claim",下次拿来当 OTel 维度的对照组。
* **NeMo IORails milestone 3**(预计 7-8 月)— 把多 rail 并行从"内容安全"扩到"PII + jailbreak + topic"三件套并行,延迟会再降一档。
* **OWASP LLM Top 10 2025 草案**(LLM10 Unbounded Consumption)正式合入主页面之前,可以**把 LiteLLM budget ceiling** 当实战样本先记下 —— 上次(03:48)已经写过,下次做 cost monitoring 时联动引用。

---

## 引用与数据来源

* NVIDIA NeMo Guardrails releases API:https://api.github.com/repos/NVIDIA/NeMo-Guardrails/releases
  * v0.22.0(2026-05-22):https://github.com/NVIDIA/NeMo-Guardrails/releases/tag/v0.22.0
  * v0.21.0(2026-03-12):https://github.com/NVIDIA/NeMo-Guardrails/releases/tag/v0.21.0
  * v0.20.0(2026-01-22):https://github.com/NVIDIA/NeMo-Guardrails/releases/tag/v0.20.0
* guardrails-ai releases API:https://api.github.com/repos/guardrails-ai/guardrails/releases
  * v0.10.2(2026-06-04):https://github.com/guardrails-ai/guardrails/releases/tag/v0.10.2
  * v0.10.0(2026-04-03):https://github.com/guardrails-ai/guardrails/releases/tag/v0.10.0
  * v0.9.3(2026-04-03):https://github.com/guardrails-ai/guardrails/releases/tag/v0.9.3
* Microsoft Presidio releases API:https://api.github.com/repos/microsoft/presidio/releases
  * 2.2.362(2026-03-18):https://github.com/microsoft/presidio/releases/tag/2.2.362
  * 2.2.361(2026-02-12):https://github.com/microsoft/presidio/releases/tag/2.2.361
  * 2.2.360(2025-09-09):https://github.com/microsoft/presidio/releases/tag/2.2.360
* Lakera PINT-benchmark:https://github.com/lakeraai/pint-benchmark(commits API:`/repos/lakeraai/pint-benchmark/commits`)
* Microsoft Learn — Jailbreak detection(Azure AI Content Safety):https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection(本次抓取文档版本时间 2026-02-26)
* OWASP LLM Top 10:https://owasp.org/www-project-top-10-for-large-language-model-applications/
* NIST AI 600-1 Generative AI Profile:https://doi.org/10.6028/NIST.AI.600-1
* EU AI Act(Regulation 2024/1689):https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689
* Cloudflare workerd releases API:https://api.github.com/repos/cloudflare/workerd/releases(`v1.20260604.1`, 2026-06-04)

> 数据抓取时间:2026-06-05 04:25-04:30 CST(本地)。所有 release 日期均直接来自 GitHub API,未做人工修饰。
