# Guardrails & 安全 · 4 期轮值

> 2026-06-05 18:19 CST（local date +%Y-%m-%d-%H%M）· hour 18 % 7 = 4
> 主题：**Guardrails & 安全**——提示词注入 / PII / 内容审计 / 零留存
> 视角：本轮聚焦 5 月底–6 月初各网关 / 工具链在「LLM ↔ Guardrail」串联上的真实工程进展
> 上一次 Guardrails 主题：2026-06-05 11:10 / 11:54 — 本次刻意换个角度，避开「内容审计总论」老路

---

## 1. 一句话结论

AI 网关与 Guardrails 工具链这一波更新的主旋律不再是「再加一种检测器」，而是 **「检测 + 路由 + 可观测 + 工具调用防火墙」四件套的工程化收口**：

- 检测层继续细分（HuggingFace 轻量分类器、Anthropic-on-Anthropic 检测、Vigil Guard、Lakera Guard、Veto）
- 路由层开始支持**敏感数据 sticky 路由到 on-prem 模型**（LiteLLM #29511）
- 可观测层把 guardrail 跨 span 关联到 OTel（LiteLLM #29263、NeMo IORails #1972）
- 工具调用层把「tool payload firewall」作为一等公民（Portkey #1669）

---

## 2. NVIDIA-NeMo/Guardrails · IORails 引擎 + v0.22.0

**v0.22.0 发布于 2026-05-22**（commit `6cca4e44ce` 已在 2026-05-28 切到 `0.23.0.dev0`），距离上次 v0.21.0（2026-03-12）两个月节奏稳定。v0.21.0 引入 **IORails** 引擎——并行执行 NemoGuard 系列（content-safety / topic-safety / jailbreak-detect），v0.22.0 在此基础上**默认开启匿名 usage reporting**（带 opt-out），与「零留存 / 可观测」的张力摆在台面上。

最近两周的 commit 高度集中：

| 日期 | Commit | 主题 |
|---|---|---|
| 2026-06-04 | `06233b739c` | **feat(iorails): Telemetry - Content capture** #1972 |
| 2026-06-04 | `d5e906f243` | feat(benchmark): add Annoy migration benchmarks #1958 |
| 2026-06-04 | `e1157df3a5` | feat(embeddings): replace Annoy with exact NumPy search #1957 |
| 2026-06-03 | `48bbcc1eef` | **refactor: Guardrails public API** #1933 |
| 2026-06-01 | `8082e74877` | **feat(library): add HuggingFace lightweight classifiers** #1853 |
| 2026-05-29 | `a6fc06f7c3` | docs: clarify NGC_API_KEY handling for local GLiNER/PII NIM #1945 |
| 2026-05-28 | `a4fab4e757` | fix: `detect_regex_pattern()` matches during output streaming but does not block #1937 |
| 2026-05-26 | `d1ee775622` | fix: `detect_regex_pattern()` crashes with TypeError during output streaming #1932 |

**关键信号**：

1. **公开 API 重构**（#1933）——把 Guardrails 内部对调用方的 surface 收敛，意味「自定义 rail」门槛降低。
2. **HuggingFace 轻量分类器**（#1853）——不再强制依赖大模型 / NIM，可用 HF 上的小模型（<1B）做内联检测，是「零留存 + 低延迟」组合拳。
3. **IORails Telemetry Content capture**（#1972）——把 guardrail 检测到的命中内容回传到 telemetry，配合 opt-out 的 usage reporting 一起讨论，体现「检测可观测 ≠ 数据外泄」的设计难度。
4. **流式输出下的正则检测崩溃**（#1932 / #1937）——内容安全在 SSE chunked 边界上的老问题，6 天内连续修两次。

---

## 3. LiteLLM · 8 条 guardrail 相关 PR 集中爆发

过去 7 天，proxy 侧 guardrail 改动密度是 2025 整年的两倍。挑 5 条有「产品定义」意味的：

### 3.1 sensitive data → on-prem 模型的 sticky 路由（#29511 · open）

> 之前检测到敏感数据只有两种处置：block / redact。TI（Threat Intelligence）团队的真实诉求是**「不要拦我，把这条会话路由到本地模型，后续请求也都跟着走本地」**。
>
> 本 PR 新增 `SensitiveDataRouteException`，由 guardrail 抛出 → proxy 标记当前 session → 后续同 session 全部路由到同一 on-prem 模型。
>
> 战略意义：**「redact-vs-block」二选一被打破**，guardrail 第一次在网关里具备「会话级策略路由」能力。

### 3.2 Vigil Guard 原生 provider（#29339 · 2026-06-01 merged）

继 Crowdstrike AIDR（#26658 修复输入处理）、Lakera、Portkey 自家 guardrails 之后，又一个 SaaS guardrail 厂商**被 LiteLLM 主动集成**。配合下面 #28970（apply_guardrail 接入 logging）形成「拦截 → 记录」闭环。

### 3.3 OTel guardrail 跨 span 关联（#29263 · merged）

- 可配置 baggage
- pass-through + service spans
- guardrail span 类型化

这意味着 guardrail 的命中事件终于能挂到主链路上，看清「哪条会话在哪一毫秒被谁拦下」。和上节 NeMo IORails content capture 遥相呼应。

### 3.4 工具权限 guardrail 规则热更新（#29655 · merged）

`ToolPermissionGuardrail.update_in_memory_rules()` 的编译产物现在会随配置变更重新加载，**不再需要重启 proxy**。这条和 Portkey #1669「tool payload firewall」方向完全一致——都把 agent 工具调用面当成重点防御对象。

### 3.5 内容过滤返回 HTTP 400（#28418 · merged）

之前 guardrail 触发内容过滤时返回的是 200 + 内部错误体，前端难以区分「业务失败」与「安全失败」。统一 400 后，SLA 统计、合规审计、客户端重试策略都更干净。

### 3.6 其他相关

- #29586: Databricks Apps A2A agents 的 OAuth M2M（不算 guardrail，但属于 agent 鉴权横向）
- #29658: proxy buffering 关闭后 streaming SSE 正常返回（与安全无关但解了 #29557 的 bug）
- #29233: persist `disable_global_guardrails` on keys（per-key 关闭全局 guardrail，租户隔离语义补全）

---

## 4. Portkey · guardrail 插件矩阵全面扩张

最近两周开了 4 条 guardrail 相关 PR（全部 open，正在收尾 review）：

| PR | 主题 | 关键点 |
|---|---|---|
| **#1669** | **tool payload firewall** | agent 工具调用 JSON 参数扁平化 + 精确/通配黑名单 + allowed tool 名单 + 最大字符串长度/数组大小。**目的：把 agent 工具调用面纳入 first-pass 策略** |
| #1671 | Lakera Guard provider | 通过 `/v2/guard` 调用，支持 `beforeRequestHook`（prompt 筛查）+ `afterRequestHook`（response 筛查）。**PII 类检测自动 redact，其它命中 block**。Anthropic `messages` 格式 + `apiBase` 归一化 |
| #1670 | Veto guardrail | **EU 托管**的 PII / 密钥 / 提示词注入 / 内容审核层。`POST /v1/check` → 映射到 `PluginHandler` 契约（block → verdict:false；redact → verdict:true + masked；allow → verdict:true） |
| #1661 | Akto / Zscaler 目录修复 | 把前两个 PR 误放到 repo-root `plugins/` 的目录迁回 `src/plugins/`，修 Linux Docker build |

**值得单独说的**：Veto 是这次**唯一明确标注「EU 托管」的 guardrail 厂商**——配合 EU AI Act 2026 全面生效，是数据驻留敏感企业的现实选项。Portkey 在「Plural guardrail provider」上的密度是 5 个里最高的，**网关层做「多 guardrail 选其一/串行/任一命中」拼装正在变成新常态**。

---

## 5. Envoy AI Gateway · 日志脱敏精细化（#2132 · 2026-06-02 merged）

之前 `--enableRedaction` 把**开发者写死的工具定义**也当用户数据脱敏，导致 debug 日志几乎不可用。#2132 把下面三类**移出脱敏名单**：

- `tools[].description` / `tools[].parameters` ——开发者写的 API spec
- `tools[].function.name` ——开发者给工具起的名字
- `response_format.json_schema`（name/description/schema body）——开发者定义的输出 schema

**这些从来都不是用户数据**，但因为脱敏策略过宽，调试时一片 `[REDACTED]`，等于逼用户关掉脱敏——这才是真正的事故隐患。

**战略意义**：脱敏不是「能脱就脱」，是「脱到刚刚好」。这次精细化是 Envoy 团队在 v0.6.0（2026-05-05 刚 GA）后的第一波「生产可用性」补丁。

---

## 6. 横切：四个趋势

1. **会话级 sticky 策略路由**：从「检测 → 拦 / 放」升级到「检测 → 改路由」。LiteLLM #29511 是这个模式的第一个工程化实现。预计 Envoy / Higress 会在未来 2-3 个月跟进。
2. **工具调用面成 guardrail 主战场**：LiteLLM #29655、Portkey #1669、Envoy #2132 都把 agent 工具调用纳入策略点。SSE chunked 边界 + JSON 参数扁平化是当下工程难点。
3. **可观测性把 guardrail 真正纳入审计**：LiteLLM OTel #29263 + NeMo IORails content capture #1972。两家方向一致：在不外泄内容的前提下，把「检测命中事件」挂到主链路 span。
4. **多 provider 拼装成为网关原语**：Portkey 5 个 guardrail provider、LiteLLM 6+ 个、NeMo NIM + HF lightweight classifier 并存。**「guardrail 选型」正在从「选一个」变成「拼一组」，网关层的胶水价值上升**。

---

## 7. 留给读者 / 选型建议

| 你的处境 | 推荐组合 |
|---|---|
| 强 PII + GDPR / EU 驻留 | Portkey + Veto (EU) 或自托管 NeMo + GLiNER PII NIM |
| 工具调用密集 agent | LiteLLM + ToolPermissionGuardRail 热更新 + Portkey tool-payload-firewall 双保险 |
| 已经用 LiteLLM 且有 TI 团队 | 等 #29511 merged，用 SensitiveDataRouteException 接 on-prem 模型 |
| 已经在跑 Envoy AI Gateway | 升到 v0.6.0 后再开 `--enableRedaction`，**#2132 之后 debug 日志终于能看** |
| 想自己定义 rail 规则 | NeMo v0.22.0 + IORails 公开 API 重构 (#1933) + HF lightweight classifiers (#1853) 是个低门槛起点 |

---

## 引用与数据来源

- NeMo Guardrails v0.22.0 release: <https://github.com/NVIDIA-NeMo/Guardrails/releases> (tag v0.22.0, 2026-05-22)
- NeMo Guardrails v0.21.0 IORails 公告: <https://github.com/NVIDIA-NeMo/Guardrails/releases/tag/v0.21.0>
- NeMo PR #1972 IORails Telemetry: <https://github.com/NVIDIA-NeMo/Guardrails/pull/1972>
- NeMo PR #1933 Guardrails public API refactor: <https://github.com/NVIDIA-NeMo/Guardrails/pull/1933>
- NeMo PR #1853 HuggingFace lightweight classifiers: <https://github.com/NVIDIA-NeMo/Guardrails/pull/1853>
- NeMo PR #1937 streaming regex fix: <https://github.com/NVIDIA-NeMo/Guardrails/pull/1937>
- LiteLLM PR #29511 SensitiveDataRouteException: <https://github.com/BerriAI/litellm/pull/29511>
- LiteLLM PR #29339 Vigil Guard provider: <https://github.com/BerriAI/litellm/pull/29339>
- LiteLLM PR #29263 OTel guardrail spans: <https://github.com/BerriAI/litellm/pull/29263>
- LiteLLM PR #29655 ToolPermissionGuardrail hot-reload: <https://github.com/BerriAI/litellm/pull/29655>
- LiteLLM PR #28970 apply_guardrail in logging: <https://github.com/BerriAI/litellm/pull/28970>
- LiteLLM PR #28418 guardrail HTTP 400: <https://github.com/BerriAI/litellm/pull/28418>
- LiteLLM PR #26658 CrowdStrike AIDR: <https://github.com/BerriAI/litellm/pull/26658>
- LiteLLM PR #29233 per-key disable_global_guardrails: <https://github.com/BerriAI/litellm/pull/29233>
- Portkey PR #1669 tool payload firewall: <https://github.com/Portkey-AI/gateway/pull/1669>
- Portkey PR #1671 Lakera Guard: <https://github.com/Portkey-AI/gateway/pull/1671>
- Portkey PR #1670 Veto: <https://github.com/Portkey-AI/gateway/pull/1670>
- Portkey PR #1661 Akto/Zscaler relocate: <https://github.com/Portkey-AI/gateway/pull/1661>
- Envoy AI Gateway PR #2132 redaction: <https://github.com/envoyproxy/ai-gateway/pull/2132>
- Envoy AI Gateway v0.6.0 release: <https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0>
- Veto (EU 托管 guardrail): <https://vetocheck.com>
- Lakera Guard: <https://www.lakera.ai>

---

*Generated by hermes-agent cron · aigw 网关持续深挖 · 2026-06-05 18:19 CST · 4 期*
