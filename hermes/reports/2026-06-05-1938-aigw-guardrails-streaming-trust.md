# AI 网关持续深挖 · Guardrails & 安全 · 6 期

> **轮次**：2026-06-05 19:38 CST（第 N 次，hour=19，19 % 7 = 5 → Guardrails & 安全）
> **本期主轴**：流式会话里**静默丢内容 / 静默丢工具调用**类隐性注入类缺陷集中爆发；guardrails-ai 接入 PyPI trusted publishing；NeMo-Guardrails 推出 domain-hallucination 输出护栏
> **上期**：`hermes/reports/2026-06-05-1858-aigw-guardrails-runtime-defense.md`（runtime injection 防御 · 5 期）
> **报告人**：hermes-agent cron · 30 分钟轮值

## 一、摘要

本轮值抓取窗口（2026-06-03 ~ 2026-06-05）里 guardrails 生态出现三个值得立即关切的信号：

1. **LiteLLM 修复了 2 个会让 guardrail"看似正常工作但实际丢数据"的高危 bug**——`#26585` 修复 `ToolPermissionGuardrail` 流式 hook 在未产生 tool_calls 时整段普通文本回复被吞掉；`#29097` 修复 Vertex/Gemini `tool_choice` 在 CachedContent 路径上被静默丢弃。
2. **LiteLLM 同步修复 `ToolPermissionGuardrail` 热更新失效**（`#29655`）——`update_in_memory_litellm_params` 不重建 `self.rules` 编译产物，导致 `PUT /guardrails/{id}` 改的规则不生效，直到下次 patch / 轮询 / 重启才被发现。
3. **NeMo-Guardrails 新增 `domain_hallucination` 输出护栏**（`#1988`），在静态 223 样本上 F1 60.18%（基线 34.10%），覆盖 URL / domain / GitHub repo 真伪验证；`#1985` 引入 sharded resource mutex 强制 strict linearizability。
4. **guardrails-ai v0.10.2（2026-06-04）切到 PyPI trusted publishing**（`#1493`），结合同版本落地的 `SECURITY_ADVISORY.md`，治理链路正式与 Sigstore 同源化。

横切判断：**"流式 / 热更新 / 缓存复用" 三类隐性路径已成 guardrail 失效的最密集来源**——下游表现为"启用 guardrail 后响应变空"或"刚改完规则像没改一样"，攻击面则是"借 tool_choice / cached_content / 编译缓存的旧值绕过策略"。

## 二、本期关键数据点

### 2.1 LiteLLM `ToolPermissionGuardrail` 流式 hook 静默丢文本（#26585，已合并）

- **症状**：proxy 启用 `tool_permission` guardrail（mode=post_call）后，LLM 决定不调用工具、走纯文本回复时，async generator 的 `return` 等价 `raise StopAsyncIteration`，整段响应被吞，客户端只收到 `data: [DONE]`。
- **触发条件**：所有 chat 客户端 + 流式 + `ToolPermissionGuardrail` 启用 + LLM 选择纯文本（占比很高的对话类 query）。
- **修复**：在 `if not tool_calls` 分支走 `MockResponseIterator` 把已组装响应重新 yield，与同函数下方允许工具路径保持一致。
- **评分**：Greptile Confidence 5/5，PR scope 1 problem / 2 files。
- **借鉴价值**：提示我们做网关侧 guardrail 时，必须对"未匹配任何规则路径"做显式 `pass-through` 回归测试；负路径（`return`/`break`）吞 yield 是 Python async generator 的经典地雷。

### 2.2 LiteLLM `ToolPermissionGuardrail` 热更新失效（#29655，已合并）

- **症状**：`__init__` 中编译 `self.rules` / `_compiled_rule_targets` / `_compiled_rule_patterns` 三张表；`update_in_memory_litellm_params` 只 `setattr` 原值，三个编译产物从未重建。`PUT /guardrails/{id}` 改完规则后，写入 DB 成功、`self.rules` 已更新，但实际匹配走的还是构造期的旧编译表。
- **生效时间窗**：直到 `PATCH /guardrails/{id}` 路径触发、DB 轮询命中、或进程重启，才会被强制刷新。
- **修复**：抽 `_load_rules(rules)` 私有 helper，让 `__init__` 与 in-memory update 共用同一编译逻辑，对齐 `PresidioGuardrail` 已有的 override 模式。
- **借鉴价值**：策略在内存 / DB / 编译缓存三态不一致是最容易写出的"治理错觉"——审计看到 DB 改对了，线上却没拦到。

### 2.3 LiteLLM `vertex_ai` Gemini CachedContent 静默丢 `tool_choice`（#29097，已合并）

- **症状**：`tool_choice` 在请求被复用到 Gemini `CachedContent` 时未被 bake 进 body，模型在缓存命中分支上忽略工具选择；外部看是"agent 偶尔不调工具"，但根因是请求路径切换。
- **修复**：把 `tool_choice` 显式 bake 进 `CachedContent` body，保证缓存命中与非命中路径行为一致。
- **借鉴价值**：缓存层是策略执行的盲区——既要考虑"缓存命中时的策略等价性"，也要考虑"缓存复用是否会让旧策略对象继续生效"。

### 2.4 NeMo-Guardrails `domain_hallucination` 输出护栏（#1988，feature）

- **形态**：`nemoguardrails/library/domain_hallucination/` 输出 rail，使用 DNS / HTTP / TLS / WHOIS / GitHub API 五级证据验证 LLM 回复中出现的 URL / domain / GitHub repo 真伪。
- **基线对比（223 样本静态评测）**：
  - Macro F1：60.18%（vs 原 hallucination rail 34.10%）
  - 安全集严重误报率：5.50%（vs 21.50%）
- **可组合**：与既有的 `hallucination` rail 并联使用，做 defense-in-depth。
- **风险分级动作**：`block` / `refine` / `warn` / `pass` 四级；支持 knowledge base 集成 + expert review。
- **横向意义**：把"agent 编造引用 / 假仓库 / 假文档链接"从单点检测升级为可编排的输出策略——直接对应 AI 网关需要对外承诺的"输出可追溯"承诺。

### 2.5 NeMo-Guardrails 状态机 strict linearizability（#1985，bug fix）

- **症状**：state hydration pipeline 跨 shard 时存在并发 race，可能让两条 rail 看到不同的中间状态。
- **修复**：sharded resource mutex，强制 hydration 路径 strict linearizable。
- **关联**：与 IORails（v0.22.0 起并行执行 content/topic/jailbreak rails）配套——并行执行的前提是状态可序列化，否则会出现"两条 rail 各自跑在不一致的世界里"。

### 2.6 guardrails-ai v0.10.2（2026-06-04）+ trusted publishing（#1493）

- 7 条合并 PR：`#1474/#1478/#1490` 制度化 `SECURITY_ADVISORY.md`、`#1467` Aikido 修复 GitHub workflow 模板注入（首个 `@aikido-autofix[bot]` 贡献）、`#1484` 把 `litellm` pin 从上限放开到 `>=1.83.0`、`#1493` 切到 PyPI trusted publishing。
- **治理意义**：从 npm/PyPI 包分发的角度进入 Sigstore 信任链，与 LiteLLM 的 cosign 镜像签名同源；下游选型时可以将"是否走 trusted publishing / cosign"作为治理基线之一。
- 后续 dev 分支 2ef10125 / 99dd2d02 还在做 alpha bump 与 build 调整，v0.10.3/0.11.0 节奏可关注。

### 2.7 LiteLLM v1.88.0-rc.3 / v1.87.1（2026-06-04 / 06-05）

- v1.88.0-rc.3 仍是 cosign-only 签名文档，未在 release body 展开变更。
- v1.87.1 是 stable 通道的回滚点（`#29631` 把 5 个 staged fix 移植到 stable/1.87.x 后切到 1.87.1；`#29636` 切到 1.87.2 后被 `#29645` revert 回 1.87.1，避免过早 1.87.2 bump）。
- 同期 `#29612` `key_generate` 给 UI/CLI session token 加了"team budget ceiling 豁免"，是治理策略而非 guardrail 范畴；本轮值不展开。

## 三、对 AI 网关的横切判断

1. **"负路径默认行为" 必须可观测**。`#26585` 这种"guardrail 启用后纯文本消失"的 bug，只有在 chat 客户端真正流式渲染时才暴露。建议在网关层对 guardrail 三态（`pass`/`block`/`error`）打 OTel span，并保留 `noop_yield_count`、`null_chunk_count` 两个 counter，异常时 alert。
2. **策略热更新要走"编译产物重建"路径**。`#29655` 是教科书级反例——DB 写对 ≠ 线上生效。审计应要求每条 guardrail 提供"改完即生效"的证明（最近一次 `update_in_memory_litellm_params` 调用时戳 vs 策略生效时戳）。
3. **缓存与流式的策略等价性是 P0**。`#29097`（CachedContent 丢 tool_choice）说明 Gemini / Anthropic prompt cache / OpenAI prompt cache 各自都可能让 guardrail 失效。短期：把"带 cache-control 的请求"走与冷启动相同路径；中期：在网关层统一禁用或重新注入 tool_choice / system prompt 的 cache key。
4. **domain / URL / repo 真伪是新型输出治理**。`#1988` 的 F1 60.18% 仍不足以单独上线，但作为输出 rail 与既有的 jailbreak / topic rail 并联已足够；网关侧应预留"output rail 评分 + 多 rail 投票"的钩子。
5. **trusted publishing / cosign 应列入选型硬指标**。guardrails-ai v0.10.2 接入 PyPI trusted publishing、LiteLLM Docker 走 cosign——这两个项目的供应链治理已对齐 Sigstore 信任链；其他仍走"维护者手动上传 + 个人 PyPI token"的项目应标记为治理白点。

## 四、可立即采取的行动项

- [ ] **本周**：升级 guardrails-ai 到 v0.10.2，验证 PyPI 元数据是否显示 "Verified"；同步把 LiteLLM Docker 镜像 cosign 校验接进 CI。
- [ ] **本周**：在 LiteLLM proxy 端对所有启用 `ToolPermissionGuardrail` 的环境跑 `tests/test_litellm/proxy/guardrails/guardrail_hooks/test_tool_permission.py` 与 `test_async_post_call_streaming_iterator_hook_plain_text_yields_chunks`；确认 plain-text 路径在流式下仍能 yield。
- [ ] **2 周内**：把 `PUT /guardrails/{id}` 之后的"实际生效"用 OTel `guardrail.rules.applied_count` 与 DB `rules.json` 做一致性 metric。
- [ ] **本月**：把 Vertex / Gemini / OpenAI / Anthropic 各自的"prompt cache + tool_choice / system 注入" 路径做一次矩阵化回归——是否会出现"cache 命中后策略失效"。
- [ ] **季度**：以 NeMo-Guardrails `domain_hallucination` v0.22.x 之后的 release 为锚点，评审"输出层 multi-rail 投票"是否值得引入到自家网关。

## 五、引用与数据来源

> 所有日期以 `date` 命令取自本机（2026-06-05 19:38 CST）。

- LiteLLM #26585 ToolPermissionGuardrail streaming 静默丢文本：https://github.com/BerriAI/litellm/pull/26585
- LiteLLM #29655 ToolPermissionGuardrail 热更新失效：https://github.com/BerriAI/litellm/pull/29655
- LiteLLM #29097 Vertex/Gemini CachedContent 静默丢 tool_choice：https://github.com/BerriAI/litellm/pull/29097
- LiteLLM #29552 guardrail passthrough 缺 span 修复：https://github.com/BerriAI/litellm/pull/29552
- LiteLLM #29531 sensitive data → on-prem 模型 sticky 路由（internal copy）：https://github.com/BerriAI/litellm/pull/29531
- LiteLLM v1.88.0-rc.3 release：https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3
- LiteLLM v1.87.1 release：https://github.com/BerriAI/litellm/releases/tag/v1.87.1
- NeMo-Guardrails #1988 domain_hallucination 输出护栏：https://github.com/NVIDIA/NeMo-Guardrails/pull/1988
- NeMo-Guardrails #1985 state hydration strict linearizability：https://github.com/NVIDIA/NeMo-Guardrails/pull/1985
- NeMo-Guardrails #1972 IORails Telemetry content capture：https://github.com/NVIDIA/NeMo-Guardrails/pull/1972
- NeMo-Guardrails v0.22.0 release：https://github.com/NVIDIA/NeMo-Guardrails/releases/tag/v0.22.0
- guardrails-ai v0.10.2 release：https://github.com/guardrails-ai/guardrails/releases/tag/v0.10.2
- guardrails-ai #1493 PyPI trusted publishing：https://github.com/guardrails-ai/guardrails/pull/1493
- guardrails-ai #1467 Aikido AI Fix template injection：https://github.com/guardrails-ai/guardrails/pull/1467
- guardrails-ai #1474/#1478/#1490 SECURITY_ADVISORY.md 制度化：https://github.com/guardrails-ai/guardrails/pull/1474
- 上期报告（Guardrails 5 期）：`hermes/reports/2026-06-05-1858-aigw-guardrails-runtime-defense.md`
- 上上期报告（Guardrails 4 期）：`hermes/reports/2026-06-05-1819-aigw-guardrails-roundup.md`
