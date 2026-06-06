---
title: "AI 网关持续深挖 · 语义路由/成本优化 · round 4"
date: 2026-06-07 03:45 CST
topic: semantic-routing-cost
round: r4
previous: 2026-06-06-1734-aigw-semantic-routing-r3
sources_window: "2026-06-05 22:00 ~ 2026-06-07 03:00 UTC (~30h)"
---

# 语义路由/成本优化 · r4 — 「生命周期收口 + 错误结构化 + 跨引擎 KV-cache IPC」三件硬通货

> 范围：vllm-sr / LiteLLM / LMCache 6/5 22:00–6/7 03:00 UTC 关键 PR。(1) **vllm-sr 模型生命周期收口到 config-owned catalog**（#2066，+3302/-1353/49f）；(2) **LiteLLM 限流错误第一次走「structured 分类 + Prometheus label」**（#27687，OpenAI 真 USD 实测）；(3) **LMCache 跨引擎 KV-cache IPC 拓展到 block-only server + POSIX SHM + S3FIFO + DCP-aware gather**（DeepSeek-V4-Flash 验证）。加 LiteLLM 两条 CLI 范式 PR。

## 1. vllm-sr：模型生命周期收口（PR #2066，+3302/-1353/49f，open）

**[#2066 Router: Centralize router model lifecycle](https://github.com/vllm-project/semantic-router/pull/2066)**（aabdelraey，6/6 16:50 UTC，30 天内 vllm-sr 主仓最大单一重构 PR 候选）—— 把 router 内部**所有模型（embedder / intent / factcheck / feedback / image-gen / 多模态）的本地路径、伴生文件、运行时名、下载/初始化时机**统一收口到 `pkg/modellifecycle` 单一 catalog，配套 `pkg/modeldownload` 与 model-info API 共用一份 source of truth。

**关键改动**：**canonical serving 默认锁 mmBERT**（embedder + intent/factcheck/feedback 三件套 merged），legacy BERT/SentenceTransformer fallback 退出默认 plan；**配置-治理-下载三段解耦**：`pkg/config` canonical defaults + 解析期 ref 校验（`TestParseYAMLBytesRejectsUnknownLifecycleModelRef` 拒未声明 ref），`pkg/modellifecycle` 运行时，`pkg/modeldownload` 下载；**AMD/ROCm reduced-model backend 真机回归通过**（image tag `amd-regression-56e1dc47`）—— `deploy/recipes/balance.yaml` 全跑通，**L1 dropped ~17× 趋势在 ROCm 一致**；**TD044/PL0032 plan/tech-debt 双轨**同步更新，**AMD 验证状态写入**。

**配套 PR**：**#2067** `GLOBAL_MODEL_FACTORY` `OnceLock` 被 multimodal 抢先后 embedder factory 丢失的真 bug，修法 factory 注册时如已被占**fallback to explicit error**；**#2069** dashboard restart SQLite recovery test with PVC-backed workflow store（Issue #1509），e2e gate；**#2060** drop supervisord monolith paths, default split runtime containers（Issue #1508）—— **与 #2066 互锁**：lifecycle catalog 默认 plan 是给 split container 设计的。

## 2. LiteLLM 限流错误第一次走「structured 分类 + Prometheus label」（PR #27687，+3049/-198/24f，open，rebased 6/6）

**[#27687 feat: standardize rate limit errors with category, rate_limit_type, model, and listener](https://github.com/BerriAI/litellm/pull/27687)**（rebased onto `litellm_internal_staging` post-#28909 typed v2 OTel refactor）—— LiteLLM 限流错误体系**首次**结构化分类：**callback payload 增 `error_information.error_rate_limit_category` + `error_rate_limit_type ∈ {requests, budget, tpm, ...}` + 完整 `llm_provider`**，Prometheus row 同步增 `rate_limit_category` / `rate_limit_type` 两 label（保留旧 `exception_class` shim 向后兼容）。

**真 USD 实测**（`localhost:4000` 对真 `api.openai.com` / `gpt-4o-mini`）：**BEFORE** `StandardLoggingPayload.error_information` 只 5 字段，`llm_provider` 空串；**AFTER** `error_rate_limit_category="litellm_rate_limit"` + `error_rate_limit_type="requests"`（RPM 路径）/ `"budget"`（BudgetExceededError 路径），`llm_provider="openai"` 填好。**Wire-format headers**（`retry-after: 60` / `rate_limit_type: requests` / `reset_at: ...`）429 响应两状态都保留。

**关键技术取舍**：**v2 OTel span integration 撤回**——proxy-side rate limit 在「任何 upstream 调用前」就被 gate 拒，**LLM-call span 根本没开**，`LITELLM_LOGGING_NO_UPSTREAM_LLM_CALL` tag 一打 v2 logger 新 attribute 就是 dead field；**改走 `StandardLoggingPayload` custom-callback + Prometheus label 双通道**。**PROD-grade 4 件套**：真 USD 验证 + BEFORE/AFTER 截图 + shim 向后兼容 + wire-format 不变。**对 AIGW 来说这是「错误结构化」的金标准样板**——下游 SIEM 可按 `rate_limit_type` 维度做告警/限流/预算归因。

## 3. LMCache 跨引擎 KV-cache IPC 四件套（6/6 集中冲刺，DeepSeek-V4-Flash 验证）

### 3.1 **#3550 [MP][DSV4] LMCache server block-only（+824/-398/17f，open，Ready for review）** —— 架构分层清场

DeepSeek-V4 hybrid KV cache manager 暴露 5 个 `KVCacheGroupSpec`，**logical block size 各异**（MLA=256 / SWA=64 / state=4+8），`block_size` 塌缩到 GCD → server 用单 scalar 推 `compress_ratio` → **SWA/state group 静默只存一部分**（P0 正确性 bug）。**让 server 变 block-only**（不推理 SWA / block size / token offset）：

- **Connector 做剪枝**：`_slice_block_ids` 把 chunk 剪到 trailing SWA window；retrieve APC skip 改 `skip_blocks_per_group: list[int]`，**token→block 转换 + suffix-offset 调整全在 connector 折叠**；
- **新增 wire hint** `per_layer_storage_blocks_per_chunk`；**`per_layer_sliding_window` 从 wire 删**；
- **RETRIEVE 字段** `skip_first_n_tokens: int` → `skip_blocks_per_group: list[int]`；
- **server 删 SWA machinery**（`sliding_window` / `num_suffix_blocks_per_chunk` / `chunk_suffix_offset_blocks` / suffix gather / token→block skip conversion）。

**真机验证**（`DeepSeek-V4-Flash` tp=4, fp8, block_size=256, LMCache 256 GiB L1 SHM）：6/5 首次 `l1_memory_usage_bytes` **58 MB**（vs 667 MB full-chunk，**17× L1 drop**，cold≈warm semantically identical）；6/6 重跑 L1 0→19→77→97 MB 稳态。**supersedes** #3548 / #3261 / #3564。**教训**：**KV store 不应建模 engine paging 语义**。

### 3.2 **#3561 [Feature] DCP-aware CPU KV offload for vLLM v1 connector（+430/-0/3f，open）**

vLLM `decode_context_parallel_size > 1`（DCP）下每 rank 只持 `1/cp_world` context slice，v1 connector 假设 MLA latent KV replicated → **global save rank 永远拿不到完整 prefix，DCP 下 LMCache CPU hit = 0**。self-contained `lmcache/integration/vllm/dcp_gather.py` 加 DCP 耦合：SAVE all-gather → block-interleave → 存到 full-token key；LOAD broadcast → deinterleave。**non-DCP 分支 `return False`，零侵入**。

**B200（SM100）/ TP=4 / Kimi-K2.6-NVFP4 / fp8 KV cache / eagle3 spec / Mooncake agentic-trace replay**：IFEval gated（reasoning 关）DCP=2 prompt_strict **0.88** / DCP=4 prompt_strict **0.89**，**与 no-offload baseline 完全对齐**；30k+ hit-events / 单请求 CPU load 数十万 token 无 crash。**部署硬要求**：DCP 必须用 strided KV layout（`cp_kv_cache_interleave_size=1`）。

### 3.3 **#3563 + #3566 配套：POSIX SHM 基础设施 + S3FIFO 驱逐**

**[#3563](https://github.com/lmcache/lmcache/pull/3563)**（+867/-6/7f）跨进程 CPU KV-cache 共享内存基座（从 #3352 抽出）。单机多卡 RDMA/IB 没意义，但跨进程 CPU↔CPU KV-cache 共享走 SHM 比 unix socket 快 10×+。**[#3566](https://github.com/lmcache/lmcache/pull/3566)**（+1447/-428/41f）S3FIFO 三队列 small/main/ghost，给「scan-resistant workload」新选项；不破坏现有 `LRU`/`LFU` 工厂接口，**factory registration 增一项 + 41 files unit test**。

**AIGW 落地含义**：LMCache 5 天内连续推 4 类核心 PR——**block-only 架构清场**（#3550）/ **DCP-aware CPU offload**（#3561，DeepSeek-V4 类 MoE 在 DCP 下也能 hit）/ **POSIX SHM IPC**（#3563）/ **S3FIFO scan-resistant eviction**（#3566）——**「跨 vLLM/SGLang/TensorRT-LLM 的 KV-cache 路由器」产品形态正在落地**。

## 4. LiteLLM 两条 CLI 范式 PR（agent 端到代理 + 网关端到回放）

### 4.1 **#29850 per-agent `litellm-proxy claude` / `codex` / `opencode`（+613/-0/5f，open）supersedes #29846（closed）**

**per-agent CLI 路由器**：`litellm-proxy claude` / `codex` / `opencode` 直接转发 argv 后所有参数（`litellm-proxy claude --resume`），**所有 LLM 流量透明流过 proxy** 在 `localhost:4000/ui/?page=logs` 可见。

**DX 设计**（学自 **Infisical agent-vault**）：(a) **automatic SSO login** 交互模式；(b) **env-key "agent mode"** for containers/CI（`LITELLM_PROXY_API_KEY` 存在就不开 browser）；(c) **fail-fast preflight** 启动前打 proxy 验 key（坏 key 立即报错**不会**在 agent 深处失败）；(d) **per-agent env 映射**：Claude Code 收 `ANTHROPIC_BASE_URL`（bare root）+ `ANTHROPIC_AUTH_TOKEN`，**`ANTHROPIC_API_KEY` 显式 drop**；Codex 收 `OPENAI_BASE_URL=http://localhost:4000/v1` + `OPENAI_API_KEY`；**TTY + signals 透传**；(e) **registry-driven**。对应 r24 硬要求 AG-41。

### 4.2 **#29847 Extend the record/replay proxy to chat/embeddings/moderations/rerank/Anthropic（+347/-73/8f，open）**

把 [gpt-image-1 record/replay](https://github.com/BerriAI/litellm/pull/29802) 普适化：**一个 recorder 进程 front 所有 upstream**，cache key 用 `api_base`（**不是** header —— 避免 cohere rerank 丢 unknown header）。`RECORDER_*_BASE_URL` 只在 CI container 里 set，本地 dev + prod 透明。**三个 CI 工作流**：`build_and_test`（chat/embeddings/**`text-moderation-stable`**/image）/ `proxy_logging_guardrails_model_info_tests`（**Cohere rerank**）/ `proxy_e2e_anthropic_messages_tests`（**真 Anthropic `claude-sonnet-4-5-20250929`**）。**单次 commit 可重放 6+ 月，CI 全量 provider E2E 零 USD**。

## 5. 横向对比：路由器 0.3 时代（r2–r4）三件硬通货

| 维度 | r2（vllm-sr v0.3.0） | r3（OpenRouter + LiteLLM 1.88 RC） | r4（本期） |
|---|---|---|---|
| **范式** | PRISM 153-key / entropy / DSL `SIGNAL_GROUP`+`TIER` | Model Fusion / Pareto Code / `cost_quality_tradeoff` 0-10 / edge cache | **lifecycle catalog 单一 SoT** / **block-only KV store** |
| **治理** | 3 段合法性 + 153-Registry | budget fix（#29273） / `LITELLM_OTEL_V2`（#28909） | **TD044/PL0032 双轨** / AMD 真机回归 / **split containers 默认** |
| **错误** | —— | 5 条 critical/high security advisory | **rate limit error structured 分类** |
| **KV-cache** | hybrid allocator | coordinator CLI + mp server | **block-only server** / **DCP-aware offload** / **POSIX SHM** / **S3FIFO** |
| **agent 接入** | —— | —— | **per-agent CLI wrapper** + **record/replay E2E** |

**5 个反常识**：(1) **lifecycle catalog 是产品化分水岭**——vllm-sr #2066 收口 `pkg/modellifecycle` 单一 catalog，**AMD/ROCm 跑通 + split containers 默认**两件事一起才能让 sidecar 进 K8s operator 列表；(2) **block-only KV store 是分层清场**——LMCache #3550 删 server 端 SWA machinery，**正确性 + 性能同时 +17× L1 drop**；(3) **structured rate limit error 是错误治理金标准**——LiteLLM #27687 真 USD BEFORE/AFTER 对照，**callback + Prometheus 双通道 + shim 向后兼容 + wire-format 不变**是 4 件套；(4) **per-agent CLI wrapper 是 agent 端到代理的最低成本**——Infisical agent-vault DX 模式（SSO + env-key + fail-fast preflight + per-agent env mapping + registry-driven）；(5) **record/replay 普适化是 CI 烧钱陷阱的根治**——LiteLLM #29847 用 `api_base` cache key 绕开 cohere rerank 丢 header bug，**CI 单元测试从此零 USD**。

## 6. AIGW 5 条新硬要求 → 累加 90 条

**(R-81) vllm-sr 接入按 split container 模式部署**（#2060+#2066）—— mmBERT 为最小可观测集（embedder + intent + factcheck + feedback 四件套）。
**(R-82) mmBERT embedder factory graceful fallback**（#2067）—— `OnceLock` 被占时**显式 error 而非静默用错的工厂**（CI gate 必跑 `TestParseYAMLBytesRejectsUnknownLifecycleModelRef`）。
**(R-83) LiteLLM 限流错误结构化**（#27687）—— rate-limit 触发时**必 emit** `error_rate_limit_category` + `error_rate_limit_type` + 完整 `llm_provider`，callback + Prometheus 双通道；**保留** wire-format `retry-after` / `rate_limit_type` / `reset_at` 头。
**(R-84) LMCache server block-only**（#3550）—— engine paging 语义在 connector；per-group block count 用 `per_layer_storage_blocks_per_chunk`，**`per_layer_sliding_window` 不进 wire**；RETRIEVE `skip_blocks_per_group: list[int]`。
**(R-85) agent 接入走 per-agent CLI wrapper**（LiteLLM #29850）—— gateway 提供 `litellm-proxy claude` / `codex` / `opencode` 或等价 wrapper（agent-vault DX：SSO + env-key + fail-fast preflight + per-agent env mapping + registry-driven），**让代理成为 agent 必经之路**；record/replay E2E（`api_base` cache key，CI 烧 USD 归零）。

## 引用与数据来源

- vllm-sr PR #2066：<https://github.com/vllm-project/semantic-router/pull/2066>
- vllm-sr PR #2067：<https://github.com/vllm-project/semantic-router/pull/2067>
- vllm-sr PR #2060：<https://github.com/vllm-project/semantic-router/pull/2060>
- vllm-sr release v0.3.0：<https://github.com/vllm-project/semantic-router/releases/tag/v0.3.0>
- LiteLLM PR #27687：<https://github.com/BerriAI/litellm/pull/27687>
- LiteLLM PR #29850：<https://github.com/BerriAI/litellm/pull/29850>
- LiteLLM PR #29846（superseded）：<https://github.com/BerriAI/litellm/pull/29846>
- LiteLLM PR #29847：<https://github.com/BerriAI/litellm/pull/29847>
- LiteLLM release v1.88.0-rc.3：<https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3>
- LMCache PR #3550：<https://github.com/lmcache/lmcache/pull/3550>
- LMCache PR #3561：<https://github.com/lmcache/lmcache/pull/3561>
- LMCache PR #3563：<https://github.com/lmcache/lmcache/pull/3563>
- LMCache PR #3566：<https://github.com/lmcache/lmcache/pull/3566>
- r3 上轮：`reports/2026-06-06-1734-aigw-semantic-routing-r3.md`
- r2 上轮：`reports/2026-06-06-1038-aigw-semantic-routing-r2.md`
