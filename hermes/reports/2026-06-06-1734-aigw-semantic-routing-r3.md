# 语义路由 / 成本优化 第 3 轮（2026-06-06 17:34 CST）

> 主题：LLM Router 算法演进、模型融合、缓存策略、动态预算、路由安全
> 时段：local hour=17 → 17%7=3 → 语义路由/成本优化（第 3 次）
> 相对前两轮（0328、1038）的增量：OpenRouter 5 月 Release Spotlight 集中放量（Model Fusion、Pareto Code Router、Session-id Stickiness、Auto router cost_quality_tradeoff 0-10），LiteLLM 1.88 RC 围绕 deployment budget 收口，semantic-router 发布 CVE-2026-42208 安全修复。

## TL;DR

1. **OpenRouter 5 月 Release Spotlight（2026-06-01）** 把"路由"做成产品矩阵：Model Fusion、Pareto Code Router、Auto Router `cost_quality_tradeoff` 改 0-10 整数、Session-id 路由让 agent 多轮命中同 provider 提缓存命中。
2. **OpenRouter Response Caching（2026-04-30 GA）** 提供 `X-OpenRouter-Cache: true` 头，命中 4ms 返回、零 token 费用；TTL 1s-24h、可 `X-OpenRouter-Cache-Clear` 主动 bust。
3. **LiteLLM 1.88.0-rc.1（2026-05-31）** 收口 budget/router bug：PR #29273 补 `add_deployment`/`upsert_deployment` 路径 budget 注册；session-token budget-ceiling exemption 在 rc.2/rc.3 持续加固。
4. **aurelio-labs/semantic-router v0.1.15（2026-05-23）** 修 CVE-2026-42208；v0.1.13（2026-05-14）给 QdrantIndex 加 namespace 多租户隔离。
5. **Not Diamond 4-5 月连发**：4/23《A Comprehensive Guide to Model Routing》、5/6《How to reduce Claude Code costs without sacrificing output quality》。

## 1. OpenRouter：5 月集中放量，"路由"产品化

来源：<https://openrouter.ai/announcements/may-release-spotlight>（2026-06-01，作者 Nick Livermore）。月路由 100 万亿 token 级别（"we're now routing 100 trillion tokens a month"）。

### 1.1 Model Fusion
并行把 prompt 路由到多个模型，再合成一个回答。提供三种形态：**API plugin**（标准 chat completions 启用）、**server tool**（agent 调用）、**chatroom composer**（UI 试用）。直接对应 MoA 思路；作为商用网关一等公民能力出现，意味着「路由 + 融合」正式进入 L7 网关主流程。

### 1.2 Pareto Code Router
- `min_coding_score`（最低 coding 质量门槛）→ 选**最便宜**且过门槛的 coding 模型。
- 默认值可在 workspace plugin 设置里调。
- 把"cost-quality 二元选择"做成可配置的连续变量。

### 1.3 Auto Router `cost_quality_tradeoff` 改 0-10
旧的 binary 开关（"省钱" vs "高质量"）被替换成 0-10 整数；越大越偏质量，越小越偏成本。从"启发式 fallback 链"推到"连续参数空间"。

### 1.4 Session-id Provider Stickiness
同 `session_id` 的请求，路由到**同一 provider + 同一具体模型**。官方动机：提升多轮 agent 工作流的 provider 端 prompt cache 命中率。和 §2 Response Caching 互相成就。

## 2. OpenRouter Response Caching（GA，2026-04-30）

来源：<https://openrouter.ai/announcements/response-caching>（Brian Thomas）。

- **触发**：`X-OpenRouter-Cache: true`。
- **缓存键**：`hash(request_body, model, api_key, streaming_mode)`。
- **TTL**：`X-OpenRouter-Cache-TTL`，1s-24h，默认 5min。
- **主动 bust**：`X-OpenRouter-Cache-Clear: true`。
- **响应头**：`X-OpenRouter-Cache-Status: HIT|MISS`、`-Age`、`-TTL`。
- **性能（官方）**：命中 80-300ms（其中 4ms 是 cache lookup）；对照：Gemini 2.5 Flash 1.3s、Kimi K2.6 4.6s、GPT-5.5 9.1s。
- **计费**：命中**零费用**，不计 prompt/completion token。
- **多模态**：text/image/audio/document/tool 都能缓存；多模态 base64 参与 hash；超大到内部 offload 的不参与。
- **作用域**：API key 维度（不同 key 不共享）。
- **与 prompt caching 区分**：prompt caching 省 provider 内 prompt 部分费用；response caching 是 OpenRouter 边缘层直接跳过 provider 调用、返回完整 response。

⚠️ **使用约束**：temperature=0、tools 固定、system prompt 固定才能拿到命中。**安全侧**：cache key 含 API key，跨 key 不共享是有意设计，避免跨 key 数据泄漏。

## 3. LiteLLM 1.88 RC：Budget / Router 收口

来源：<https://github.com/BerriAI/litellm/releases>（v1.87.1 2026-06-04 GA、v1.88.0-rc.3 2026-06-05）。

### 3.1 router budget 修复（PR #29273）
- 现象：deployment budget 只在 router 启动时从 `model_list` 注册，运行时通过 `add_deployment`/`upsert_deployment`（`/model/new` API）加进来的模型**没注册到 `RouterBudgetLimiting`**。
- 修复：补全 `add_deployment` / `upsert_deployment` 路径的 budget 注册；第一次运行时新增 budgeted deployment 时懒启动 `router_budget_limiting`。
- 关联：fixes LIT-3043、fixes #25799。

### 3.2 OTEL v2 可选门控（PR #28909，已 merge 2026-05-30）
- 默认完全关，**`LITELLM_OTEL_V2` 环境变量启用**。
- 设计：FastAPI instrumentation 拥有 HTTP server span；本包负责"gen-ai"类 span（LLM / guardrail / 内部服务/DB）；span 父子关系**显式锚定到 request root span**（`set_request_root_span`）而不是 ambient —— 解决 pass-through 请求从 `asyncio.create_task` 关闭 server span 导致 orphan 的历史 bug。
- span 树（PR body 节选）：
  ```
  SERVER span  "POST /v1/chat/completions"  ← FastAPI
  ├── INTERNAL span  "auth /v1/chat/completions"
  │   ├── CLIENT span  "postgres get_key_object"
  │   └── CLIENT span  "postgres get_team_membership"
  ├── INTERNAL span  "execute_guardrail …"
  ├── CLIENT span    "chat gpt-4o"
  └── CLIENT span    "batch_write_to_db …"
  ```

### 3.3 1.87.1 稳定线、1.87.2 被回滚
1.87.2（backport session-token budget-ceiling exemption）被 1.87.1 再次覆盖回滚（PR #29645）。session-token budget exemption 进了 1.88 RC，**稳定线用户在 1.88 GA 前不会拿到**。建议等 1.88.0 GA 上 prod。

### 3.4 安全公告（与路由/认证强相关）
来源：<https://github.com/BerriAI/litellm/security/advisories>，近 60 天：
- **GHSA-4xpc-pv4p-pm3w**（2026-05-28, **critical**）—— Host Header 注入导致 authentication bypass。
- **GHSA-r75f-5x8p-qvmc**（2026-04-20, **critical**）—— Proxy API key 校验处 SQL 注入。
- **GHSA-v4p8-mg3p-g94g**（2026-04-21, high）—— MCP stdio test endpoint 认证后命令执行。
- **GHSA-wxxx-gvqv-xp7p**（2026-05-07, high）—— 自定义 guardrail 沙箱逃逸。
- **GHSA-xqmj-j6mv-4862**（2026-04-20, high）—— `/prompts/test` SSTI。

两条 critical 都直接威胁到 **API key 校验路径**和**网关鉴权边界**，公网暴露的 LiteLLM proxy 必须升级。

## 4. aurelio-labs/semantic-router：v0.1.15 CVE + 多租户

来源：<https://github.com/aurelio-labs/semantic-router/releases>。

- **v0.1.15（2026-05-23）**：修复 **CVE-2026-42208**。建议升 ≥0.1.15。
- **v0.1.14（2026-05-18）**：补 QdrantIndex async 错误 & 缺失方法（PR #663）。
- **v0.1.13（2026-05-14）**：
  - 给 QdrantIndex 加 **namespace-based 租户隔离**（PR #661）—— 多租户企业可用同一 backend。
  - Ollama encoder 参数 `model_name` 重命名为 `name`（PR #654）。
  - notebooks 05/07 兼容 v0.1（PR #656）。

NS 隔离 + CVE 修复，把 semantic router 从"开发玩具"推向"多租户可用"。

## 5. Not Diamond 4-5 月：路由 + Prompt Adaptation

来源：<https://notdiamond.ai/blog>。
- **2026-04-23**《A Comprehensive Guide to Model Routing》：把 model routing 整理为方法论。
- **2026-05-06**《How to reduce Claude Code costs without sacrificing output quality》：把"路由降低 coding agent 成本"做成具体案例。
- **2026-01-20** Prompt Optimization GA。
- **2024-09-25**《RoRF: Routing on random forests》—— 路由器后端是随机森林（feature：prompt embedding、长度、模型历史表现等）。

差异化是「路由器使用轻量 ML 模型（random forest / learned router）」，不是规则 / 启发式。配合 prompt adaptation（2025-12 GA），路由 + 提示优化形成双层 cost reduction。

## 6. 横向对比：当前主流 LLM Router 形态

| 形态 | 代表 | 算法核心 | 缓存策略 | 公开 Benchmark |
|---|---|---|---|---|
| 规则 + 启发式 fallback | LiteLLM Router | 优先级/retry/cooldown/fallback | `caching` 参数（redis/qdrant） | 无 |
| 学习式路由 | Not Diamond (RoRF) | Random forest on prompt features | 与 prompt cache 解耦 | RoRF 论文 |
| 边际质量增益 | Martian | Pareto 前沿专家编排 | 内部 | RouterBench |
| 隐式 router = LLM | Semantic Router (aurelio) | 嵌入相似度 → 路由 | 与 external index 集成 | 无 |
| 网关 + Auto router | OpenRouter | 启发式 + session-id stickiness + Pareto Code | Response Cache (edge) + provider prompt cache | rankings 公开 |
| Ensemble | OpenRouter Model Fusion | 并行 + 合成 | 透传 | 无 |
| MoE 替代（模型级） | Martian Airlock | 内部多专家 | 内部 | 无 |

## 7. 实战建议

1. **想直接降本**（最快路径）：开 OpenRouter Response Caching（4ms 命中 / 零费用）→ 设 session-id 让 agent 多轮命中同 provider 提 provider 端 prompt cache。
2. **想拿到 Pareto 收益**：用 OpenRouter Pareto Code Router 设 `min_coding_score`；或自部署 Not Diamond RoRF（开源 SDK）。
3. **自部署 LiteLLM**：必须升级到 ≥ 1.87.1；critical 漏洞（GHSA-4xpc-pv4p-pm3w、GHSA-r75f-5x8p-qvmc）决定要升 1.88 GA（建议等 GA 上 prod）；想用 budget fix（PR #29273）需要 1.88.0-rc.1+。
4. **多租户 semantic router**：aurelio-labs/semantic-router v0.1.15+，开 QdrantIndex namespace 隔离；务必升 0.1.15 修 CVE-2026-42208。
5. **可观测必须配 OTEL v2**：LiteLLM 设 `LITELLM_OTEL_V2=1` 显式打开，否则路由链路上的 LLM span 父链会是错的。

## 8. 待跟踪项

- LiteLLM 1.88.0 GA 何时发布（rc.3 2026-06-05 之后通常 1-2 周内）。
- OpenRouter 是否会开放 Pareto Code Router 的 `min_coding_score` 全模型调参与 Provider 维度差异化。
- Not Diamond 2026 下半年是否把 RoRF 开源 weights 到 GitHub。

## 引用与数据来源

- OpenRouter May Release Spotlight（2026-06-01）: <https://openrouter.ai/announcements/may-release-spotlight>
- OpenRouter Response Caching（2026-04-30 GA）: <https://openrouter.ai/announcements/response-caching>
- OpenRouter Guardrails（2026-05-29）: <https://openrouter.ai/announcements/guardrails>
- OpenRouter Series B（2026-05-28）: <https://openrouter.ai/announcements/series-b>
- OpenRouter GPT-5.5 Cost Analysis（2026-05-04）: <https://openrouter.ai/announcements/gpt55-cost-analysis>
- OpenRouter Blog index: <https://openrouter.ai/blog>
- LiteLLM v1.87.1: <https://github.com/BerriAI/litellm/releases/tag/v1.87.1>
- LiteLLM v1.88.0-rc.1: <https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.1>
- LiteLLM v1.88.0-rc.2: <https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.2>
- LiteLLM v1.88.0-rc.3: <https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3>
- LiteLLM PR #29273 (router budget): <https://github.com/BerriAI/litellm/pull/29273>
- LiteLLM PR #28909 (OTEL v2): <https://github.com/BerriAI/litellm/pull/28909>
- LiteLLM Security Advisories: <https://github.com/BerriAI/litellm/security/advisories>
- aurelio-labs/semantic-router v0.1.15 (CVE-2026-42208): <https://github.com/aurelio-labs/semantic-router/releases/tag/v0.1.15>
- aurelio-labs/semantic-router v0.1.14: <https://github.com/aurelio-labs/semantic-router/releases/tag/v0.1.14>
- aurelio-labs/semantic-router v0.1.13 (QdrantIndex namespace): <https://github.com/aurelio-labs/semantic-router/releases/tag/v0.1.13>
- Not Diamond blog index: <https://notdiamond.ai/blog>
- Not Diamond《A Comprehensive Guide to Model Routing》(2026-04-23): <https://notdiamond.ai/blog/a-comprehensive-guide-to-model-routing>
- Not Diamond《How to reduce Claude Code costs》(2026-05-06): <https://notdiamond.ai/blog/how-to-reduce-claude-code-costs-without-sacrificing-output-quality>
- Not Diamond RoRF (2024-09-25): <https://notdiamond.ai/blog/rorf-routing-on-random-forests>
- Martian blog: <https://withmartian.com/blog>
- zilliztech/GPTCache: <https://github.com/zilliztech/GPTCache/releases>

— 完 —
