# Guardrails 专题·R21 — 生态快照：ATR v3.2.0、garak 新探针矩阵、Cisco AI Defense 接 LiteLLM、Presidio 6 月硬化

> 主题：guardrails（11 % 7 = 4） · **2026-06-06 11:23 CST** · 今天 guardrails 第 3 轮
> 角度：**6/4 → 6/6 48h 窗口**的"上游硬货集锦"——不重复 04:10（middleware）/ 04:50（SLO + garak v0.15.1 ProPILE + CVE-2026-45758）已写的
> 关键词：**ATR v3.2.0 自动发布**、**garak 新 6 个探针**（#1846 special-token / #1843 base65536+hexagram / #1779 context-compliance / #1676 ATR detector / #1845 skip-reason log / #1827 文件锁）、**LiteLLM #28249 Cisco AI Defense 双 surface (chat|mcp)**、**Presidio 6 月五件套**（#2055 hard token cap / #2041 tokenizer chunking / #2052 NER dedupe / #2039 FastAPI / #2056 docker build）、**LiteLLM 三连击**（#29810 cache_control_injection_points Anthropic Responses / #29737 auth_v2 casbin / #29590 datadog cost_tag_keys）、**cisco-ai-defense SDK 6/5 commit**、**Mastra 输入处理器 subpath**

---

## TL;DR

48h 窗口里 guardrails 生态的硬信号密度**比上轮高**。**Agent-Threat-Rule/agent-threat-rules v3.2.0 自动发布**首次把"通过 TC (Threat Crystallization) 结晶出的规则"以 release artifact 形式落到 PyPI（之前是 CLI 内置或仓库 tarball），把"治理信号"推向了版本号维度的可声明性。**NVIDIA/garak 同期 6 个 PR** 在 v0.15.1 之上把检测矩阵拓到三个新维度：编码绕过（base65536 / I-Ching hexagram）、控制字符（special-token injection）、上下文合规（context-compliance jailbreak = 制造一个假的三轮"无害对话"作为前置 context，再让 LLM 顺势配合有害请求）——这些是 4-5 月 OWASP/MITRE 攻击库在 garak harness 的"开箱即用"落地。**LiteLLM #28249 Cisco AI Defense 集成**是这一波第 7 个"partner guardrail"——和 Pillar / PANW Prisma AIRS / Lasso / GraySwan / Hiddenlayer 并列，**但 Cisco 是首个双 surface（`inspection_type=chat|mcp`）**——MCP 流量走 `/api/v1/inspect/mcp`，body 是 JSON-RPC 原始 envelope，"on-wire contract 跟 curl 一致"，意味着 vendor 端可以**不解析** LiteLLM 的内部结构。**Presidio 6 月**接住了"4 套 PII 召回不足 + 1 套内存浪费"的实战反馈，把 tokenizer-aware 切分、multilingual NER 内存去重（8 语言 3.2GB → 单模型）、`max_token_positions` 硬上限、FastAPI server 镜像等四件套一次性推到合并线附近。**LiteLLM #29810** 揭示一个**协议级 bug**——`cache_control_injection_points` 在 Responses API 路径上 hook 找 `messages[].role=="system"`，但 OpenAI Responses 把 system 放顶层 `instructions` 字符串，结果 hook 静默 no-op；**同时**该 bug 触发 Claude tool-call 的确定性循环直到 MaxTurns——和 04:50 报告里 anthropics/claude-code #65574 的"百万 token 计费"是同一类问题，但根因在 gateway 协议翻译。`auth_v2`（authlib + casbin）WIP 和 Datadog cost_tag_keys 传丢失是收尾型硬化。

---

## 一、Agent-Threat-Rules v3.2.0：TC 结晶规则首次以 release artifact 形式发布

仓库 [`Agent-Threat-Rule/agent-threat-rules`](https://github.com/Agent-Threat-Rule/agent-threat-rules)（注意：用户名 "Rule" 单数，不是 lasso-security/...），★ 245、**42 主题**、6 月 5 日 17:xx UTC 一日 8 个 PR / 13 commit，关键四条：

**(1) v3.2.0 release (commit `5e46739` 2026-06-05)** — 标题"auto-publish TC-crystallized rules"——把 Threat Crystallization 流程产出的规则从"仓内 tarball"提到 release tag，落地为**版本化供应链**。这是 6/3→6/5 ATR 一直宣传的"v3.x 治理收口"在工程上的最后一公里：之前 v3.1.0→v3.1.1 30 分钟双发已经验证了 462 条规则的快速迭代能力，v3.2.0 是把"通过 TC 自动结晶出的规则"独立成 release line，企业版引用方可以 pin 到具体 tag 而不是 main HEAD。

**(2) #104 100% rule coverage across 6 frameworks + CI honesty gates**（`fe40465` 06-05 闭）— 6 个合规框架（OWASP / NIST AI RMF / EU AI Act / ISO/IEC 42001 / SOC 2 / Five-Eyes——见 `587a66b` docs）的覆盖率从 70-80% 区间推到 100%，并把"声明的覆盖率 vs 实际生效的规则"做了一道 CI 闸门：**claim 必须等于 reality**。这是上一轮 04:50 提到的"ATR-2026-00001 FP"事件的延伸修复——6/4 误报后，ATR 把"框架声称的覆盖"和"git HEAD 实际生效的规则"做 SHA 比对，claim 漂移直接卡 CI。

**(3) #96 SymJack 00572 + CrewAI VU#221883 覆盖激活**（06-05 闭）— CrewAI 漏洞 VU#221883 现在有 ATR 规则覆盖；SymJack 00572 是新加的符号混淆绕过模式（猜测是 control-char + 视觉同形字符组合）。

**(4) #95 Mastra 输入处理器 subpath**（`20aec0f` 06-05 闭，**5 PR 矩阵新成员**）— `agent-threat-rules/mastra` 出口，**zero `@mastra/core` 依赖**——通过 TypeScript 结构性 generics 捕获 Mastra `Processor` 契约（不是 import，而是 duck-type），给 Mastra 的 input processor 链塞一个 `ATRProcessor`，**默认 critical/high 阻断**。这是 ATR 第 5 个 subpath 集成（前 4 个是 langchain / llamaindex / crewai / autogen + 04:50 提到的 mcp 桥）。

**(5) #94 文档修正 PINT framing**——"self-built corpus, not Lakera's official PINT"，PINT (Prompt Injection Test Suite) 之前在文档里被误描述为 Lakera 官方套件（实际是 ATR 自己构建的语料 + Lakera PINT 一部分抽样），这条改动防止"测试集来源 = 厂商基准"导致评估结果 inflation。

**v3.2.0 治理意义**：把 TC 规则从 "main HEAD 滚动" 升到 "release tag 锁定"——对企业引用方意味着 `pip install agent-threat-rules==3.2.0` 拿到的就是合规审计可声明的 462 条规则集，**不再随 main 漂移**。CI honesty gate 防止 "声称覆盖 6 框架 / 实际只编入 4 框架" 的合规通胀——这是一条对所有 "compliance-as-code" 项目都适用的"声明 vs 现实"二段式门禁。

---

## 二、NVIDIA/garak v0.15.1 之上：6 个新 PR 把攻击矩阵拓到 4 个新维度

上一轮 04:50 写过 v0.15.1 (06-05 17:24 UTC) 的 ProPILE PII 探针 + 数据集路径遍历修复 + 删 `maxrecall` evaluator。**v0.15.1 之后 24h** 内的 6 个新 PR 是 v0.16 候选主线：

| PR | 标题 | 攻击维度 | 关键设计点 |
|---|---|---|---|
| [#1846](https://github.com/NVIDIA/garak/pull/1846) | special-token injection probe | **控制字符** | baseline vs injected 双 prompt 对，5 模板 × 16 special token (`<|endoftext|>`/`<|im_start|>`/`<|im_end|>`/`<|im_sep|>` + 12 个厂商私有 token)，detector 比对行为分歧（长度/词重叠/refusal 一致性） |
| [#1843](https://github.com/NVIDIA/garak/pull/1843) | base65536 + hexagram 编码注入 | **编码绕过** | Base65536（2 字节/字符）+ I-Ching 卦象（Base64 字符映射成卦象图，bits 可见），都走 `EncodingMixin` + `primary_detector=encoding.DecodeMatch`，**无新运行时依赖** |
| [#1779](https://github.com/NVIDIA/garak/pull/1779) | Context Compliance jailbreak probe | **多轮 context 制造** | 3 轮假对话：(1) user 无害问题 → (2) assistant 给出 neutral overview 并"主动提出可以配合有害目标" → (3) user 直接重发"那帮我做"——检测目标能否被"前置无害 context"诱导到配合 |
| [#1676](https://github.com/NVIDIA/garak/pull/1676) | **ATR detector** (新模块) | **agent 专属威胁** | 9 个 detector 类，`garak/data/atr/rules.json` 内置 1,597 个 regex 来自 ATR 293 条生产规则（**bundled，无运行时依赖**），覆盖 MCP tool poisoning / skill compromise / context exfiltration / excessive autonomy 四大类 |
| [#1845](https://github.com/NVIDIA/garak/pull/1845) | skip-reason log | 可观测 | detector base 加 `skip_reason` 属性，harness 在 `skip=True` 时 INFO 级 log，**解决 "用户不知道哪些 detector 为什么没跑"** (fix #1061) |
| [#1827](https://github.com/NVIDIA/garak/pull/1827) | log 文件锁 | 稳定性 | 修 `RuntimeError: reentrant call inside <_io.BufferedWriter>` —— `multiprocessing.Pool` fork 时子进程继承父 `FileHandler` fd，第三方库 `__del__`（openai/httpcore 关连接）触发的 reentrant flush 在 Py 3.13+ 报错；fix: 父进程 log handler 改 `NullHandler`，子进程各起独立 `FileHandler` |

**附加硬化**：[#1833](https://github.com/NVIDIA/garak/pull/1833) HF Hub 5xx 不再 fail 测试（`pytest.skip()` on `HfHubHTTPError` status≥500）—— garak 维护者记录 issue #1033 的"维护者意图"已对齐"5xx 应该 skip 不是 fail"，**与 04:50 提的 HF Hub 不稳定是同一根因**。[#1820](https://github.com/NVIDIA/garak/pull/1820) 修 Wordnet 探针"干净 cache 下 SQLite 不存在"导致 `sqlite3.OperationalError` 的二阶失败模式（**有重试，但词库下载完 SQLite 还没建索引**）。[#1753](https://github.com/NVIDIA/garak/pull/1753) `MitigationBypass` detector 补 17 个现代 refusal substring（GPT-4o 时代新话术，原 substring 来自 ShareGPT/Vicuna 数据集，**outdated**），加 `test_mitigation_bypass_false_positives` 回归测试。

**三条 AIGW 硬要求**：
- **#81** garak ATR detector 在自家 gateway 接入（`pip install garak[atr]`）——1,597 regex + 293 production rule 是**生产级威胁本体**而非 demo 集，每季度 v3.x→v3.y 升一次；
- **#82** 编码类探针（base65536 / hexagram）必须能跑——**Unicode 安全过滤器在非 BMP 平面有盲区**，I-Ching 卦象这种"视觉可解但字符已替换"是真实的 PDF/邮件附件通道；
- **#83** Context Compliance 探针 = "前置无害 context 制造"——和 RAG 间接注入是同一类技术，gateaway 层做 context provenance 标签 + agent 层做"前置 context 是否可信源"硬校验。

---

## 三、LiteLLM #28249：第 7 个 partner guardrail + **首个 MCP surface 集成**

[PR #28249](https://github.com/BerriAI/litellm/pull/28249) 把 Cisco AI Defense 的 Inspection API 接进 `litellm/proxy/guardrails/guardrail_hooks/cisco_ai_defense/`，是这一波第 7 个 partner guardrail（前面 6 个是 Pillar / PANW Prisma AIRS / Lasso / GraySwan / Hiddenlayer / Cisco）。**三个工程上值得专门拆的设计决策**：

**(1) 双 surface，`inspection_type` dropdown 在 `chat | mcp` 之间二选一**——Chat 流量 POST 到 `/api/v1/inspect/chat`；MCP 流量 POST 到 `/api/v1/inspect/mcp`，**MCP request body 是顶层 JSON-RPC envelope 本身**（不包 wrapper），"on-wire contract matches a hand-rolled curl against /inspect/mcp"——意味着 Cisco 的 inspector **不需要理解 LiteLLM 内部结构**就能拦截 MCP 流量，**vendor 端可零成本接入**。这是 partner guardrail 矩阵里**第一个原生双 surface**（其它都是 chat-only，需要 LiteLLM 在 hook 里把 MCP envelope 翻译成 chat-like JSON 再发，**vendor 拿到的是 LiteLLM 私有结构**）。

**(2) Auto-discovered via 现有 `guardrail_hooks` loader**——和 6 个 partner guardrail 共用发现机制，运维侧**零额外配置**（挂 env 即可）。

**(3) MCP response inspection 单独成路径**（commit message 显示）——agent tool call 链路是双向的，request 投毒 + response 投毒都要 inspect，**而不是 request-only**。

**vendor 端 cisco-ai-defense SDK**：[`cisco-ai-defense/ai-defense-python-sdk`](https://github.com/cisco-ai-defense/ai-defense-python-sdk) ★31，6/5 单 commit `0ec35ee` (AIFW-24958) 修"connection status unspecified"在 event 处理路径上的未定义行为，5/12 `b10691d` 给 inspection response 加 `detected_pii` 字段——和 presidio #2000 (上一轮 04:10 提过) 的 `countries` 过滤是一对上下游，**Cisco inspector 在边界发现 PII 类型 → Presidio 后续决定 locale-aware 替换策略**。

**#28249 vs 之前 6 个 partner**：之前 Pillar / PANW / Lasso / GraySwan / Hiddenlayer 全部 chat-only（04:10 报告里 LLM-side coverage），Cisco 是首个**把 inspection API 设计为协议层多 surface**的 vendor——这意味着 LiteLLM 的 guardrail_hooks 抽象已经从"贴一个 LLM-side 检查"长成了"贴一个协议层 surface 切换"。

**#28249 的 sibling 修复**：[#29531](https://github.com/BerriAI/litellm/pull/29531) (closed 06-05) sensitive data sticky routing——session-level 黏性到 on-prem（04:10 报告写过）；[#29356](https://github.com/BerriAI/litellm/pull/29356) (open 06-05) InternalServerError in allowed fails policy——`InternalServerErrorAllowedFails` 在 `get_allowed_fails_from_policy` 静默丢失，fix 显式 check 异常类型；[#29737](https://github.com/BerriAI/litellm/pulls/29737) (WIP) `auth_v2` flag-gated auth on **authlib + casbin**——从 in-house token check 升到 OAuth/OIDC 工业标准（authlib）+ 策略引擎（casbin，**和 #28249 的 MCP scope 校验复用同一个 casbin model**）；[#29590](https://github.com/BerriAI/litellm/pulls/29590) Datadog `cost_tag_keys` 传丢失——`DatadogCostManagementLogger` 总是 `cost_tag_keys=[]`，**#28487 的 consumption 侧 wiring 没接通 production 侧**，意味着 FinOps 团队配了 `callback_settings.datadog_cost_management.cost_tag_keys` 但**永远拿不到标签化的 cost**。

---

## 四、LiteLLM #29810：cache_control_injection_points 协议级 bug = 静默 no-op + 确定性 tool-call 死循环

[Issue #29810](https://github.com/BerriAI/litellm/issues/29810) (open 06-05) 是一个**协议翻译 bug** 的典型样本：

**(1) 现象**：当 `cache_control_injection_points` 配置在 Anthropic Claude 模型 + LiteLLM 代理 OpenAI Agents JS SDK（`/v1/responses` 路径）时，两件事同时发生：
  - **Cache injection 静默 no-op**：hook 迭代 `messages[]` 找 `role: "system"`，但 Responses API 协议把 system 放顶层 `instructions` 字符串，**hook 找不到任何东西，返回 `cache_controls=[]`**；
  - **Claude tool-call 死循环直到 MaxTurns**：cache 漏打 + agents SDK 的 retry 行为组合，**循环调用同一组 tool 直到 agent runtime 触顶**。

**(2) 根因**：LiteLLM 把 OpenAI Chat Completions 协议内部语义（`messages[].role=system`）硬编码到 cache injection hook，**没有为 Responses API 协议翻译**。

**(3) 与 04:50 报告的关联**：04:50 写过 anthropics/claude-code #65574（cyber safeguard 误拦 → 整次 agentic run ~1,000,000 token 计费且无恢复路径），**两者表面是不同问题（一个 FP、一个协议错位），本质都是"协议层 bug 放大为 token 损失"**——区别在于 65574 根因在 classifier 模型层（4.7→4.8 升/降回归），#29810 根因在 gateway 协议翻译。

**(4) AIGW 硬要求**（合并上一轮）：#21（协议层 hook 走抽象，不要硬编码 `messages[]` schema） + #84（**协议层 no-op 必须有 warn-level log** + SLO 闸门——"hook 返回空 + 请求继续" 是静默失败的反面教材）。

---

## 五、microsoft/presidio 6 月五件套：PII 召回 + 内存 + 部署 + 协议切分

Presidio（microsoft/presidio，★3.7k+）6/3→6/6 5 个关键 PR（**5 个都是 6/3-6/5 出现，全部 open**）：

| PR | 类别 | 问题 | 修复 |
|---|---|---|---|
| [#2055](https://github.com/microsoft/presidio/pull/2055) | **PII 召回准确** | fix #1444：context 词在 `context_prefix_count` / `context_suffix_count` 窗口外被匹配到 entity（FN/FP 来源）——`_add_n_words` 只在 keyword 命中时扣 budget，stop-word 和 punctuation **invisible to budget**，小 prefix count 0 时 token 可以无限远地贡献。| 引入 `max_token_positions = n_words * 2 + 1` 硬上限，**把扫描窗 bbox 在 prefix/suffix 各方向**——"宁可漏掉窗外的真信号，也不让窗外的噪声进 entity" |
| [#2041](https://github.com/microsoft/presidio/pull/2041) | 多语言长文本 | 长文档 NER 召回不足 | 新增 `TokenizerBasedTextChunker` 用 HuggingFace tokenizers 做 token-aware 切分；`GLiNERRecognizer` + `HuggingFaceNerRecognizer` 两条路径**可从 yaml 配置** |
| [#2052](https://github.com/microsoft/presidio/pull/2052) | **多语言内存** | 8 语言配置下 `RecognizerListLoader` 为每语言各 `__init__` 一次 recognizer，**HF transformer 8 份拷贝 ≈ 3.2GB 内存浪费** | multilingual 配置**去重 NER 模型实例**（同一 model 全语言共享），8 语言 → 1 模型 |
| [#2039](https://github.com/microsoft/presidio/pull/2039) | 部署 | 长期 #1769 第一窄切片——给 `presidio-anonymizer` 加 **FastAPI server 镜像**（`fastapi_app.py`）| 5 个端点：health/anonymize/deanonymize/anonymizers/deanonymizers，**Flask 入口不变**，FastAPI + Uvicorn 通过新 optional 暴露 |
| [#2056](https://github.com/microsoft/presidio/pull/2056) | **部署文档** | 自建 Docker image 文档残缺 | 文档化：默认 yaml 在 published image 哪、`docker build` 怎么 override |

**两条 04:50 报告的延伸**：
- 04:50 写过 Presidio #2000 `countries` 过滤（country 从 module path 推断、case-insensitive、`countries=[]` 只留 locale-agnostic），#2031 的 plate recognizer / #2052 多语言 NER / #2055 hard token cap 是同一时间窗的"PII 治理在 locale + 文本边界 + 内存"三件套；
- #2039 FastAPI server = 04:50 报告里 ATR `scan-with-judge.mts` + Lakera Gandalf 的"`/health` + REST 端点"模式在 Presidio 端的对应——**presidio-anonymizer 终于有了和 presidio-analyzer 一致的 async/Python3.11+ 部署形态**。

**AIGW 硬要求**（合并）：#85（presidio-analyzer 部署必须走 FastAPI server 而不是 Flask，`/v1/anonymize` async 路径 + uvloop，**避免和 LiteLLM 同步 worker 抢 event loop**）；#86（multilingual NER 配置走 `RecognizerListLoader` 共享模型，**别在 gateway hot-reload 时 N+1 加载**）；#87（`max_token_positions` 硬上限，**在 yaml 里显式声明而不是用默认**——默认是 `n_words * 2 + 1`，但不同 recognizer 期望不同）。

---

## 六、紫队 benchmark 信号：meta-llama/PurpleLlama 6/3 修 AsyncTestInTestCase 批次 13/15

[`meta-llama/PurpleLlama`](https://github.com/meta-llama/PurpleLlama) 6/3 一次性合并 `d301f78`（batch 13/15）修 5 个测试文件的 `AsyncTestInTestCase`——5/18 → 6/2 期间在 `fbcode/security/genai/CybersecurityBenchmarks/datasets/canary_exploit/memory_cor` 反复 commit `canary exploit memory corruption` 样本（多个 commit 重复同标题），与 6/2 `1f18149`（`Cap semgrep --jobs to prevent io_uring resource exhaustion`）一起：**PurpleLlama 在收尾年度 async test 迁移**。5 月起就几乎没在新增 CVE 探针（v0.x 内容稳定），**当前是基础设施硬化而非新威胁本体**——给 AIGW 侧的信号：**短期不要把 PurpleLlama 升级到 main 拿新威胁，要稳定 tag**。

---

## 七、cisco-ai-defense SDK 6/5 commit `0ec35ee`：connection status unspecified = 边界态

AIFW-24958 修"connection status unspecified"在 event 处理路径上的未定义行为——**这是 partner guardrail SDK 在 production 部署时**几乎必然碰到的"边界态"：vendor 的 connection state machine 有 NORMAL / DEGRADED / DOWN / CONNECTING / UNSPECIFIED 五态，前四个有明确 handler，最后一个因为 vendor 内部某个 race 出现 **unspecified**，SDK 之前会丢进 default 分支**静默放过**。修复后强制把 unspecified 显式归类（"降级模式 + 标记 retry"），**避免"vendor 状态机抖动 → 流量瞬间无 inspect 通过 gateway"**。和 garak #1827 文件锁同一类——**vendor SDK 的"边界态可观察化"是生产 SLO 的隐藏前置条件**。

---

## 八、累计 AIGW 硬要求（本次新增 5 条 → 总 90 条）

- **#86** Cisco AI Defense / partner guardrail 的 MCP surface 集成方式 = "原始 JSON-RPC envelope 透传 + vendor 零解析"——AIGW 自家 MCP gateway 也要给 vendor 暴露**同样的"协议层原样"** API（**而不是"翻译成 chat-like JSON 再传"**——翻译即语义损耗）。
- **#87** 协议层 hook 必须走**抽象 schema**（OpenAI Chat / Responses / Anthropic Messages / MCP JSON-RPC 各自的 system/instructions/tool_use/tool_result 字段定位），**硬编码 `messages[].role=system` 是已知反模式**（#29810 已证）。Hook 返回空集合必须是 **warn-level log + SLO counter**，不是静默 no-op。
- **#88** v3.x release-line pinning：ATR v3.2.0 这种 "TC 结晶规则以 release artifact 发布" 的治理模型适合 AIGW 的"威胁本体版本"——`pip install agent-threat-rules==3.2.0` 拿到的就是合规审计可声明的规则集，**不要 `pip install agent-threat-rules@main`**。
- **#89** CI honesty gate：合规框架的"声称覆盖率"必须 CI 校验等于"实际编入规则"——claim drift 直接卡 CI。AIGW 在 PII / guardrail 维度可以抄这条。
- **#90** vendor SDK 边界态 = 生产 SLO 隐藏前置：Cisco "connection status unspecified" 静默放过、garak log file race 在 Py 3.13+ reentrant flush、LiteLLM cache_control hook 静默 no-op——**都是"边界态不显式归类"的同类 bug**。AIGW 自身 SDK 集成规范要硬性写一条："unspecified 状态不允许 default 分支静默放过，必须降级模式 + 标记 retry"。

---

## 引用与数据来源

- Agent-Threat-Rule/agent-threat-rules 仓库：https://github.com/Agent-Threat-Rule/agent-threat-rules
- ATR v3.2.0 release：https://github.com/Agent-Threat-Rule/agent-threat-rules/releases
- ATR PR #104 / #96 / #95 / #94 / #87 / #103：https://github.com/Agent-Threat-Rule/agent-threat-rules/pulls
- NVIDIA/garak v0.15.1 release：https://github.com/NVIDIA/garak/releases/tag/v0.15.1
- garak PR #1846 / #1843 / #1779 / #1676 / #1845 / #1827 / #1833 / #1820 / #1753：https://github.com/NVIDIA/garak/pulls
- BerriAI/litellm PR #28249 Cisco AI Defense：https://github.com/BerriAI/litellm/pull/28249
- BerriAI/litellm #29810 cache_control 协议 bug：https://github.com/BerriAI/litellm/issues/29810
- BerriAI/litellm PR #29531 sensitive data sticky routing / #29356 failsafe / #29737 auth_v2 / #29590 datadog：https://github.com/BerriAI/litellm/pulls
- cisco-ai-defense/ai-defense-python-sdk commit `0ec35ee`：https://github.com/cisco-ai-defense/ai-defense-python-sdk
- microsoft/presidio PR #2055 / #2041 / #2052 / #2039 / #2056：https://github.com/microsoft/presidio/pulls
- meta-llama/PurpleLlama 6/3 commits：https://github.com/meta-llama/PurpleLlama/commits
- guardrails-ai v0.10.2 release（04:50 已写）：https://github.com/guardrails-ai/guardrails/releases/tag/v0.10.2
- 上一轮互补：reports/2026-06-06-0410-aigw-guardrails-prompt-injection-middleware.md（middleware 实战）
- 上一轮互补：reports/2026-06-06-0450-aigw-guardrails-production-slo-failures.md（SLO + garak ProPILE + CVE-2026-45758）
