# AI Gateway · 架构对比 / 性能基准 round 7

> **时间锚定**：2026-06-06 20:32 CST（local `date +%Y-%m-%d-%H%M`） / UTC 2026-06-06 12:32。
> **主题**：hour 20 mod 7 = 6 → 架构对比 / 性能基准（**真实 throughput / latency / memory / 调度异常数字优先**）。
> **范围**：过去 24h 内 GitHub 流量（UTC 2026-06-05T12:32 → 2026-06-06T12:32）。**不重复** r1–r6 / `inference-gw` 已覆盖的 PR；只补 r6 之后入 master / 仍未入 master 但形态成熟的新信号。
> **数据基线**：vLLM v0.22.1（2026-06-05）、Higress v2.2.2（2026-05-26）、Kong 3.9.2（2026-06-04）、Envoy AI Gateway v0.6.0（2026-05-05）、agentgateway v2.2.2（2026-05-26）、llm-d v0.7.0（2026-05-12）+ Dynamo v1.3.0 三发 dev tag（DeepSeek-V4、Nemotron-Ultra、Nemotron-Super）。

## TL;DR · 一页数字

| 维度 | 数字 / 结论 | 仓库 / PR |
| --- | --- | --- |
| vLLM 90s ↔ 5s 握手错配 | uvicorn keep-alive=5s vs decode sidecar IdleConnTimeout=90s → socket RST | [llm-d#1564](https://github.com/llm-d/llm-d/pull/1564) |
| vLLM `VLLM_API_KEY` 安全洞 | 写进 `cache_key_factors.json` + DEBUG `pprint` 明文 | [vllm#44696](https://github.com/vllm-project/vllm/pull/44696) |
| vLLM mHC fused-RMSNorm 静默 NaN | hidden=2048/3072 直接 NaN；DSv4(H=7168) H≥512 触发 | [vllm#44692](https://github.com/vllm-project/vllm/pull/44692) |
| vLLM ROCm sparse indexer 热路径 | `torch.empty/full` → `WorkspaceManager` 复用 | [vllm#41002](https://github.com/vllm-project/vllm/pull/41002) |
| vLLM GPT-OSS ROCm 融合 | `RoPE → static Q FP8 quant → KV-cache update` 一次性 compile pass | [vllm#42832](https://github.com/vllm-project/vllm/pull/42832) |
| vLLM `--use-fp64-gumbel` 覆盖 | 从 1 path → 5 path（V1 / spec / TopKTopP / rejection / draft） | [vllm#43150](https://github.com/vllm-project/vllm/pull/43150) |
| vLLM `kv_both` deprecate Phase1 | 软弃用；Phase2 用 `kv_producer/consumer` 启动期优化 | [vllm#43874](https://github.com/vllm-project/vllm/pull/43874) |
| vLLM DP placement 节点隔离 | `VLLM_RAY_DP_PLACEMENT_NODE_IPS` allowlist 解决多引擎抢 device | [vllm#44669](https://github.com/vllm-project/vllm/pull/44669) |
| vLLM batch-invariance 覆盖 | Llama-3.2-3B 在 FLASH_ATTN/TRITON/FLEX 全部 bitwise bs1≡bs16 | [vllm#44435](https://github.com/vllm-project/vllm/pull/44435) |
| vLLM KV cache NaN 检测 Phase 2 | 从 MLA-only 推广到 `reshape_and_cache_flash` | [vllm#44719](https://github.com/vllm-project/vllm/pull/44719) |
| Higress `cluster_hash` 一致性 LB | FNV-1a, 100 槽位 weight 展开, 缺 header → 403 | [higress#3898](https://github.com/alibaba/higress/pull/3898) |
| Higress `ai-provider-affinity` 独立插件 | 同样 FNV-1a + consumer header, WASM 实现 | [higress#3867](https://github.com/alibaba/higress/pull/3867) |
| Higress `ai-security-guard` embedding | 新 API type `embedding`, `responseErrorContentJsonPath` 提取 error | [higress#3895](https://github.com/alibaba/higress/pull/3895) |
| Higress `x_higress_guardrail` 结构化拒绝 | `legacy` / `structured` 模式; `finish_reason` 改 `stop` | [higress#3894](https://github.com/alibaba/higress/pull/3894) |
| Higress `Set-Cookie` shard 串接修复 | RFC 6265 唯一不可 comma-fold header | [higress#3928](https://github.com/alibaba/higress/pull/3928) |
| Higress Bedrock Runtime Invoke 路径 | Mantle + `/model/{id}/invoke` + 流式 `invoke-with-response-stream` | [higress#3907](https://github.com/alibaba/higress/pull/3907) |
| Envoy AI GW Responses API token 全捕获 | `response.completed/incomplete/failed` 全捕获 | [aigw#2184](https://github.com/envoyproxy/ai-gateway/pull/2184) |
| Envoy AI GW Azure Responses | 独立 translator, `?api-version=...` | [aigw#2122](https://github.com/envoyproxy/ai-gateway/pull/2122) |
| Envoy AI GW Opus 4.7 `xhigh` 努力档 | `none/low/medium/high/xhigh/max` 6 档 | [aigw#2089](https://github.com/envoyproxy/ai-gateway/pull/2089) |
| Envoy AI GW `MCPBackend` CRD 提案 | 4 方案对比; 选 MCPBackend + PolicyAttachment | [aigw#2144](https://github.com/envoyproxy/ai-gateway/pull/2144) |
| Envoy AI GW audio endpoint 完整支持 | `/v1/audio/transcriptions` + `/v1/audio/translations` 双向 | [aigw#2023](https://github.com/envoyproxy/ai-gateway/pull/2023) |
| Envoy AI GW Anthropic→OpenAI 推理 + image | thinking blocks 双向 + base64/URL image | [aigw#2099](https://github.com/envoyproxy/ai-gateway/pull/2099) |
| Envoy AI GW audio_url + video_url content | OpenAI schema only, no API 变化 | [aigw#2136](https://github.com/envoyproxy/ai-gateway/pull/2136) |
| Envoy AI GW 日志脱敏瘦身 | 工具 description / function.name / role 不再 redact | [aigw#2132](https://github.com/envoyproxy/ai-gateway/pull/2132) |
| Envoy AI GW 测试模型升级 | gemini-2.0-flash-lite 弃用 → gemini-3.1-flash-lite | [aigw#2187](https://github.com/envoyproxy/ai-gateway/pull/2187) |
| agentgateway 多 AI backend policy 合并 | field-wise merge + route map 保留 + promptguard 兼容 | [agentgw#2039](https://github.com/agentgateway/agentgateway/pull/2039) |
| agentgateway Anthropic system messages | 比 #2015/#2089 更精准, 仅必要时转换 | [agentgw#2106](https://github.com/agentgateway/agentgateway/pull/2106) |
| agentgateway `simple llm` TLS | 内置模型可走 HTTPS | [agentgw#2105](https://github.com/agentgateway/agentgateway/pull/2105) |
| agentgateway eviction 与 health 解耦 | 仅设 `unhealthyCondition` 不再触发 eviction | [agentgw#2086](https://github.com/agentgateway/agentgateway/pull/2086) |
| agentgateway MCP resource subscribe | multiplex GET stream + name 变换 | [agentgw#2100](https://github.com/agentgateway/agentgateway/pull/2100) |
| agentgateway Bedrock `detect-passthrough` | claude code + bedrock 全可见 | [agentgw#2104](https://github.com/agentgateway/agentgateway/pull/2104) |
| agentgateway `agctl` 重组 | `proxy/controller` 拆 + log 读写 | [agentgw#2098](https://github.com/agentgateway/agentgateway/pull/2098) |
| Kong 3.9.2 (2026-06-04) | 6 个 nginx CVE 一次性 backport | [Kong 3.9.2](https://github.com/Kong/kong/releases/tag/3.9.2) |
| Dynamo v1.3.0-deepseek-v4-dev.1 | DeepSeek-V4-Pro (1.6T/49B-active, 1M ctx) 走 TRT-LLM `1.3.0rc15.post1` | [dynamo#10343](https://github.com/ai-dynamo/dynamo/releases/tag/v1.3.0-deepseek-v4-dev.1) |
| Dynamo v1.3.0-nemotron-ultra-dev.1 | Nemotron-3-Ultra 550B/A55B NVFP4, 走 vLLM v0.22.0 + patch stack | [dynamo#10234](https://github.com/ai-dynamo/dynamo/releases/tag/v1.3.0-nemotron-ultra-dev.1) |
| LiteLLM v1.88.0-rc.3 (2026-06-05) | cosign 签名 + 4 staged fixes + session-token budget 豁免硬化 | [litellm#29632](https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3) |

## 1 · vLLM · 「不变量检测 + 配置安全 + ROCm 全栈」三线齐进

r6 集中在 KV cache / 量化 / DBO++ / tokenizer 通胀，这 24h 的主线则是 **「正确性在不常见配置上不能假设」** —— 三件 PR 都和"我以为这条 path 没人用，结果真有人在生产上炸"有关。

### #44692 · mHC fused-RMSNorm hidden_size ≠ 4096 静默 NaN（**已合并 2026-06-06**）

`mhc_pre_big_fuse_with_norm_tilelang`（DSv4 启用 mHC 时用的 RMSNorm-fused 预 big-fuse）用 `num_stages=3` 软件流水线，配合 loop-carried `sumsq` 归约和 per-iteration 偏移写入的 `output_shared` staging buffer，**TileLang software pipeliner 直接 miscompile 循环**。差异用 fp32 reference 量化：

| hidden_size | trip count (`H//1024`) | result vs fp32 reference |
| --- | ---: | --- |
| 2048 | 2 | **NaN** |
| 3072 | 3 | **NaN** |
| 4096 | 4 | correct (1.66e-3) |
| 5120 | 5 | 0.55 |
| 6144 | 6 | 0.23 |
| 7168 (DSv4) | 7 | 0.17 |
| 8192 | 8 | 0.36 |

并且 **occupancy-dependent**：H=7168 时 ≤256 tokens 正确，≥512 才坏；slightly non-deterministic run-to-run。PR 修复一行：`num_stages=3` → `num_stages=2`，对齐 sibling `mhc_pre_big_fuse_tilelang`（已对）。**观察**：kernel 仅在 H=4096 验过就上 mainline，**hidden_size 是 TileLang 软件流水线最敏感的 codegen 维度**。这跟 r6 #44708 "tokenizer 不一致让 benchmark 通胀 6×" 是同一类教训 —— **「只能信被穷举过的输入维度」**。

### #44696 · `VLLM_API_KEY` 写进 `cache_key_factors.json`（**安全，open 待审**）

`compile_factors()` 的 `ignored_factors` 集合漏了 `VLLM_API_KEY`，但 `S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY / S3_ENDPOINT_URL` 都已正确排除。两处泄漏：

1. **明文落盘** — `cache_key_factors.json` 在 torch.compile cache 目录里
2. **DEBUG 日志** — `pprint.pformat` raw factors，DEBUG 模式可见

`S3_*` 已 sibling 处理。**这是 PR #44708 "benchmark 通胀" 的安全侧孪生兄弟**：**「secret 当作 cache factor」是 vLLM 长期潜伏的脏角落，**所有 env var 走过同一道 list 就同时过了这个洞。

### #44719 · KV cache NaN 检测 Phase 2（**open, 功能补完**）

r6 提到的 NaN 检测只盖了 MLA (`concat_and_cache_mla`)。Phase 2 推广到所有 KV cache write path，最关键的是 `reshape_and_cache_flash_kernel`。机制：

- 新 env `VLLM_DEBUG_KV_CACHE_NANS`（默认 `false`）
- CUDA kernel `detect_nans` 参数 + atomic device counter `g_nan_cache_write_count`
- Python 层 `_check_nan_in_cache_source()` 采样 KV tensor 前 1024 elements

**为什么重要**：NaN 一旦进入 KV cache，下一生成步就直接污染 logits；**到 NaN 出现在 logits 时，originating layer/phase/step 全部丢失**。在 cache write boundary 检测才能保留因果。配合 #44692（已知 fused-RMSNorm 在 H=7168 会出 NaN），**这是 vLLM 的 NaN 端到端可追溯体系**。

### #43150 · `--use-fp64-gumbel` 从 1 path 推广到 5 path（**已合并 2026-06-05**）

之前 `--use-fp64-gumbel` 只盖显式 Triton Gumbel sampler。V1 sampling / spec decode / TopKTopPSampler / rejection sampler recovery / LLM draft proposer 全部用 `q.exponential_(); probs/q; argmax` 等价指数-race 形式，**但用 fp32 噪声**。H100 + PyTorch 2.9.1+cu126 实测：

- 200M fp32 指数样本：min 恰好 `2^-24`，**0 个样本**低于该值
- float64 同样 200M：有样本低于该 cutoff

**many-tail race (trials=100k, tail_tokens=262144, gap=20.5)** 下两个精度的 race 分数不同，**spec decode 选中 token 不同**。**观察**：fp64 不是性能问题，是 spec decode 选中正确 token 的精度问题。**精确数字：`2^-24` 这个边界是 fp32 尾数宽度，fp64 才会给小数一席之地**。

### #42832 · ROCm GPT-OSS 三合一 compile-time fusion（**已合并 2026-06-05**）

`RoPE → static Q FP8 quant → KV-cache update` 在 GPT-OSS style decode graph 上是热路径相邻三步。新增 `RopeStaticQQuantKVCachePattern` 在 `rope_kvcache_fusion.py`，复用既有 `fused_rope_and_unified_kv_cache_update`，加 capability guard（static FP8 quant op + FP8 dtype）。**关键约束**：`offsets=None` 仅传给 AITER triton rotary，**不传给普通 CUDA rotary pattern matching**（signature 不一致）。`#41002` 同期合入，把 ROCm sparse indexer 的 `k_fp8` / `k_scale` / `rocm_fp8_paged_mqa_logits` 临时 buffer 从 `torch.empty/full` 改成 `WorkspaceManager`，对齐 CUDA sparse indexer 模式。

### #43874 · `kv_both` 软弃用 Phase 1（**已合并 2026-06-05**）

llm-d / vLLM 协作 NIXL connector 的角色枚举即将从 `kv_both` → `kv_producer/consumer`。Phase 1 软弃用：examples 改写 + 启动期 warning。Phase 2 会**让 vllm 启动期就根据 config 优化实例角色**。**对 agentgateway 这类写 "detect-passthrough" 的反查路径有连锁影响** —— 启动期要知道自己是 producer 还是 consumer 决定要不要 register KV listener。

### #44669 · DP placement 节点 allowlist（**已合并 2026-06-05**）

`create_dp_placement_groups` 默认 greedy 抢占 Ray cluster 任意 free device。**多 DP 引擎共享 Ray 集群（P/D 分离 / 多模型 / 外部 orchestrator）** 时一个引擎的 remote rank 落到另一个引擎的 master node 上，触发 `Not enough resources to allocate ... DP ranks on DP master node`。修复：

- 新 env `VLLM_RAY_DP_PLACEMENT_NODE_IPS`（逗号分隔 IP）
- DP placement 限制到这些节点（DP master 永远 included）

**架构含义**：vLLM Ray DP 后端从"implicit global cluster"过渡到"explicit per-engine node set"，**外部 orchestrator 终于可以静态分区**。配合 llm-d 的 well-lit P/D 拓扑（r6 提过），**P/D 分离从"动态抢占"迁移到"节点级 partition"**。

### #44435 · batch-invariance 覆盖 Llama-3.2-3B（**已合并 2026-06-05**）

RTX 4080 (SM 8.9) + `VLLM_BATCH_INVARIANT=1` + vLLM v0.22.0 + V1 model runner：

| Test | Backend | Result |
| --- | --- | --- |
| `test_logprobs_bitwise_batch_invariance_bs1_vs_bsN[16-16]` | FLASH_ATTN | ✅ |
| `test_logprobs_bitwise_batch_invariance_bs1_vs_bsN[16-16]` | TRITON_ATTN | ✅ |
| `test_logprobs_bitwise_batch_invariance_bs1_vs_bsN[16-16]` | FLEX_ATTENTION | ✅ |
| `test_logprobs_bitwise_batch_invariance_bs1_vs_bsN[8-16]` | FLASH_ATTN | ✅ |
| `test_v1_generation_is_deterministic_across_batch_sizes_with_needle` | FLASH_ATTN | ✅ |
| `test_simple_generation` | FLASH_ATTN | ✅ |

**bs1 和 bsN 产生 bitwise-identical logprobs**。Llama 3.2 序列 (`3.1-8B` / `3.2-1B` / `3.2-3B`) 全部补齐。**架构含义**：logprob-bitwise batch-invariant 是 2026 下半年 LLM 推理框架的"出厂质量门槛"，**vLLM v0.22 已覆盖 Llama 2/3/3.1/3.2 全部 4 个尺度的代表性 model**。

### vLLM v0.22.1（2026-06-05）· 8 commits, 6 contributors, 1 new

r6 时 v0.22.1 已在 24h 内发版，**这里补 r6 没细看的关键点**：

- **DeepSeek-V4** init CUTLASS `fmin` 兼容性（0decac0d）
- **HyperCLOVAX** 切 native 路径（transformers ≥ 5.9.0，#43860）
- **AMD Zen CPU** zentorch W8A8/W4A16 linear（#41813，#aadwived 首贡献）
- **Ray DP** 多节点 `num_api_servers > 1` 死锁（#43864）—— 排除了 Ray DP 后端从 #42585 deferred port 分配
- **Docker** `flashinfer-jit-cache` 摘掉 `--extra-index-url`（#44366）
- **NIXL** wheel 过滤，CUDA 13 image 上 `libcudart.so.12` `ImportError` 修（#44266）

## 2 · llm-d · 握手错配（**90s vs 5s**）是 P/D 分离最大隐形 boss

### #1564 · P/D prefill keep-alive 90s ↔ 5s 错配（**已合并 2026-06-03**）

`wide-ep-lws` / `experimental-dp-aware` / `pd-disaggregation HPU` 三条 well-lit path 的 prefill server config 统一设 `VLLM_HTTP_TIMEOUT_KEEP_ALIVE=120`。

**问题**：
- decode sidecar Go HTTP transport `IdleConnTimeout: 90 * time.Second`（proxy.go）
- uvicorn 默认 `VLLM_HTTP_TIMEOUT_KEEP_ALIVE=5`

**链路**：prefill 5s 闲置 → uvicorn 关 socket → sidecar 90s 内复用 → **kernel 看到 unread data → RST**。

**观察到的场景**：GB200 NVL72 + DeepSeek-R1 + P2D8 配置，**单个 connection 上 consecutive prefill 请求间隔**时有超过 5s。**架构含义**：**P/D 分离的 socket 池两端 keep-alive 错配是最难调的一类参数** —— uvicorn 想"省 fd"，Go transport 想"省握手"，**两端不主动同步就会随机 RST**。5×→120× 提升是一次性补丁，但**默认值的合理基准应是 prefill 单条请求 P99 E2E × 2**。

### #1654 · CPU offloading 基准（**已合并 2026-06-02**）

`#1654` 给出 cpu offloading 最小基准验证。**明示「正在 prism 做 tiered prefix caching 真实负载基准，等出来再更新 benchmark」**。架构含义：**LLM 推理侧的"最小可行 benchmark"和"生产 representative benchmark"是两件事**，llm-d 现在给的是前者，**等 prism 工作量出来才升到后者**。这是 r6 #1586（WVA v0.7.0 真实基准）路径的延续 —— **基准是工程资产，不是发布 checklist**。

### #1627 · WVA nightly script 拆出（**已合并 2026-06-02**）

`nightly-e2e-wva-ocp.yaml` / `nightly-e2e-wva-cks.yaml` 35 行 inline bash 拆到 `guides/workload-autoscaling/scripts/nightly-deploy-ocp.sh` + `nightly-deploy-cks.sh`。**`${{ needs.build-wva-image.outputs.image_tag }}` 提到顶部作 `export WVA_TAG=`，脚本里用 plain `${WVA_TAG:-}`**。零逻辑变更。**GHA 表达式和 shell 表达式混写在 GHA YAML 里是 CI 长期反模式**，本次切干净。

### #1637 · nightly e2e → nightly benchmark 迁移（**已合并 2026-06-04**）

从 `optimized-baseline` 工作流开始。`nightly e2e` 关注"服务能跑通"，`nightly benchmark` 关注"服务能跑 P99"。**当一个 inference framework 还没把 benchmark 当 nightly 一等公民时，所有手测 benchmark 都只是"工程证据"，不是"回归门"**。

## 3 · Higress · `cluster_hash` + embedding guardrail 是 r6 之后最大架构拐点

### #3898 + #3867 · 一致性 LB 双实现（**已合并 2026-06-01 / open**）

`ai-load-balancer` 新增 `lb_policy: cluster_hash`，**`ai-provider-affinity` 新独立 WASM 插件**（已含 `main_test.go`），两者行为一致：

- 从 hash_header（默认 `x-mse-consumer`）读 consumer 标识
- providers 按 weight 展开为 **100 槽位**（**权重和必须 100**）
- **FNV-1a hash + mod 100** → 目标 cluster
- 写 `x-higress-target-cluster` 头
- 配合路由上的 EnvoyFilter `cluster_header` 机制完成 upstream 选择
- 缺 consumer header → **403**

**架构含义**：Higress 把"按 consumer 一致性 hash 到 provider"做成**两套实现**（lb_policy 内置 + 独立 WASM 插件），意味着：

1. 旧 api-version 兼容路径用 `lb_policy`（不需要额外装插件）
2. 新部署想隔离 affinity 逻辑用 `ai-provider-affinity`（可独立升级 / 灰度）

**这跟 Envoy `MCPBackend` CRD 提案（#2144）走"独立 CRD + PolicyAttachment"是同一思路**：**把"横向能力"从主对象抽出来**。

### #3895 + #3894 · `ai-security-guard` 从 chat-only 走向 multi-modal 全覆盖

- **#3895** 新增 `embedding` API type —— OpenAI 兼容 embedding endpoint 的请求 `input`（string + string-array）和响应 `data` 都过 `lvwang/multi_modal_guard/embedding/openai.go`。`responseErrorContentJsonPath` 提取非 200 响应的 `error.message`。**明确 skip streaming 审核**（embedding 无流式响应），仅 warning log。
- **#3894** 把 `x_higress_guardrail` 升级为 `structured` 模式：guardrail metadata 嵌进 `choices[0].x_higress_guardrail` JSON 对象，正文 text 单独；`finish_reason` 从 `content_filter` 改 `stop`（LangChain/LiteLLM/SDK 兼容）；`safecheck_status` 在 error early-return 时正确置 `request error` / `response error`。

**架构含义**：Higress 把 guardrail 做成 **"plugin name + action + api type 三元组"** —— 同样的 `MultiModalGuard` action 覆盖 text_generation / image_generation / mcp / embedding **四种 api type**。OpenAI 兼容面继续扩张（Higress 跟 Envoy AI GW 的差距持续收窄）。

### #3928 · OIDC `Set-Cookie` shard 串接修复（**已合并 2026-06-05**）

session cookie > 4KB 拆成 `_oauth2_proxy_0`、`_oauth2_proxy_1` ... 各一个 `Set-Cookie` 头。**session refresh 期间 `Proxy()` 函数 `strings.Join(cookies, ",")` 串成一个 `Set-Cookie`**。问题是 `Set-Cookie` 是 HTTP 头里**唯一**不能 comma-fold 的（RFC 6265 §3）—— 因为 `Expires` 含逗号（如 `Thu, 05 Jun 2026 09:10:07 GMT`）。浏览器静默丢弃，下一次请求带 stale cookie（refresh token 已被 IDP 消费）→ `No valid authentication`。**架构含义**：**`Set-Cookie` 在 WASM 插件里要逐个 emit，不能 comma-fold**。同类教训是"协议层 + 传输层 + 反向代理层对 header fold 规则不统一"，**唯一不可 fold 的就是 `Set-Cookie`**。

### #3907 · Bedrock Runtime Invoke 路径（**open**）

`/v1/messages` 之前默认走 `bedrock-mantle.{awsRegion}.api.aws/anthropic/v1/messages`（AWS 自维护的 Anthropic 兼容端点）。**当后端域名是 `bedrock-runtime.{region}.amazonaws.com` 或 capability 显式配 Invoke path 时**，走 Bedrock Runtime `InvokeModel` / `InvokeModelWithResponseStream`：

- 非流式 → `/model/%s/invoke`
- 流式 → `/model/%s/invoke-with-response-stream`
- Runtime Invoke 签名 service = `bedrock`
- Mantle 签名 service 保持 `bedrock-runtime`

**Anthropic Messages → Bedrock Invoke 转换** + **Bedrock EventStream → Anthropic SSE 转换**。架构含义：Higress Bedrock provider 现在有 **2 个 endpoint、3 个 streaming 协议**（Mantle / Runtime / Converse, r5 时有）—— **能用 Mantle 就 Mantle，**否则 Runtime Invoke，**再否则走 Converse**。

## 4 · Envoy AI Gateway · Responses API 完整 token 捕获 + MCPBackend CRD 立项

### #2184 · `response.incomplete` / `response.failed` SSE token 捕获（**已合并 2026-06-03**）

OpenAI Responses API 协议在 **任何携带 terminal `Response` 对象的 event** 上都发 usage：`response.completed` / `response.incomplete` / `response.failed`。原 translator 只从 `response.completed` 提取。**后果**：

- `response.incomplete`（hit `max_output_tokens` / content filter 触发）→ 报 0 token
- `response.failed`（生成后失败）→ 报 0 token

修复：提取 `setTokenUsageFromResponse` helper + nil-guard `Response.Usage`（顺手修了一个**非合规后端 nil-deref**的潜在 segfault）。**架构含义**：**Responses API streaming 的 token accounting 必须处理 3 种 terminal state**，**只看 `response.completed` 会让 metering 漏报 1/3 的真实消耗**。

### #2144 · `MCPBackend` CRD 提案（**已合并 2026-06-03**）

`MCPRoute.spec.backendRefs[]` 的 inline 模式撞 K8s 对象大小限制，**加 OAuth 2.0 RFC 8693 Token Exchange 后每后端多 ~25 行嵌套配置 + 关注点混在一起**。提案评估 4 方案：

| 方案 | 优势 | 劣势 |
| --- | --- | --- |
| Inline security policy | 简单 | K8s 限 + 关注点混杂 |
| Separate security policy + Policy Attachment | 解耦 | 多个对象需要 reconciliation |
| Backend-refs-policy | per-backend 集中 | 只能管 backend security，不能管 MCP-specific |
| **Route-refs-policy** | route 维度灵活 | 跟 AIServiceBackend 不一致 |

**推荐**：`MCPBackend` CRD + 扩展现有 `BackendSecurityPolicy`（加 `targetRefs` Policy Attachment） + 显式 `Name/Group/Kind`。**这跟 Higress `ai-provider-affinity` 抽独立插件是同一思路**：MCP 专属能力从 MCPRoute 抽出来，**复用 AIServiceBackend + BackendSecurityPolicy 已成熟的 security 模型**。

### #2122 · Azure OpenAI Responses API（**已合并 2026-06-03**）

独立 translator，因为 Azure OpenAI Responses 兼容端点需要 `?api-version=...`。不污染 OpenAI translator。**架构含义**：AIGW 现在 Responses API 有 **2 个独立 translator**（OpenAI / Azure），**Responses 走 Azure 必须用 Azure translator**。

### #2089 · Claude Opus 4.7 `xhigh` 努力档（**已合并 2026-06-03**）

Opus 4.7 + Mythos Preview 的 `display` 默认 `omitted`（之前版本默认 `summarized`），**用户必须显式 `display: "summarized"` 才会收 thinking 摘要**。`xhigh` 是 Opus 4.7 新增 effort tier（介于 `high` 和 `max` 之间）。**自维护 6 档 `ReasoningEffort` 常量**（`none/low/medium/high/xhigh/max`），升级 `anthropic-sdk-go` 1.27.1 → 1.38.0。

### #2099 · Anthropic→OpenAI translator reasoning + image（**已合并 2026-06-02**）

`/v1/messages → /chat/completions` 双向：

- Request：pass through thinking config + 保留 multi-turn thinking/redacted_thinking blocks + image blocks (base64+URL) → `image_url`
- Response：`ThinkingBlocks` / `ReasoningContent` → Anthropic thinking/redacted_thinking blocks（非流式）+ thinking SSE events（流式）

**Tests port 自 vLLM `test_anthropic_messages_conversion.py`**。

### #2132 · 日志脱敏瘦身（**已合并 2026-06-02**）

`--enableRedaction` flag 之前把 **开发者写的 schema 元数据**（tool definition `description`/`parameters`、tool call `function.name`、`role`）也当 user content redact 了。修后这些字段不再 redact。**架构含义**：**「脱敏什么」必须有明文清单** —— 默认"宁误杀不放过"会让 debug log 失去价值。

### #2023 · `/v1/audio/transcriptions` + `/v1/audio/translations`（**已合并 2026-06-03**）

OpenAI Whisper 两 endpoint 全数据面支持。`internal/apischema/openai` 加 `TranscriptionRequest/Response/TranslationRequest/Response/Segment/Word` 类型。`EndpointSpec` 接口加 `ParseMultipartBody` 方法（multipart/form-data 解析）。**架构含义**：AIGW 的 `EndpointSpec` 接口**第一次含 multipart 解析方法**，**所有 JSON-only endpoint 都得 stub 这个新方法**。

### #2136 · OpenAI schema `audio_url` + `video_url`（**已合并 2026-05-28**）

纯 schema 变更，**无 API 变化**。phi-4-mm / qwen3.5 多模态输入广泛使用。

## 5 · agentgateway · Anthropic 协议精度 + 多 backend policy 合并

### #2039 · 多 AI backend policy 合并（**已合并 2026-06-05**）

- 复用现有 AI policy **field-wise merge** 逻辑
- 保留 configured route maps（**promptguard-only AI policy 同时适用时**不丢路由）
- 加 regression：prompt guard + `/v1/messages` + wildcard route 三类叠加

**架构含义**：agentgateway 不再"一个 backend 一个 policy"，**多 policy 适用同一 backend 时做"字段级 merge + 关键配置保留"**。这跟 Envoy `MCPBackend` + `BackendSecurityPolicy` Policy Attachment 思路异曲同工 —— **policy 是一等对象，可独立 attach**。

### #2106 · Anthropic system messages 支持（**已合并 2026-06-05**）

替代 #2015 / #2089。**两个旧方案都无条件改写 request body**，**新方案保留原 request，能不转换就不转换**。**架构含义**：**协议转换应该 lazy（按需）+ 保留（无必要不动）**，**eager rewrite = 兼容性风险**。

### #2105 · `simple llm` 支持 TLS（**已合并 2026-06-05**）

内置模型可走 HTTPS。配合 #2104（Bedrock `detect-passthrough`）和 #2099（local LLM CORS），**agentgateway 的本地/内置模型后端开始补齐"安全 + 协议"两侧的细节**。

### #2086 · eviction 与 health 解耦（**已合并 2026-06-05**）

`unhealthyCondition` 在不带 eviction policy 之前会被隐式开启 eviction。**这违反了"只设 unhealthyCondition 不应触发 eviction"的注释承诺**。**修复 + 改 test 锁住正确行为**。

### #2100 · MCP resource subscribe（**已合并 2026-06-05**）

实现 MCP `resources/subscribe` 方法。**关键 trick**：监听 GET stream，**name 上做 multiplexing 变换**。

### #2098 · `agctl` CLI 重组（**已合并 2026-06-05**）

`agctl` 重构成 `agctl proxy` + `agctl controller` 子命令组。旧 `config` / `trace` 进 `proxy` 保留 deprecated top-level 别名。**`agctl proxy log [resource] --level debug --set agentgateway::proxy=debug,agentgateway::http=info`** 是新 log 控制接口。

## 6 · Dynamo v1.3.0 dev tag 三连发

24h 内 NVIDIA Dynamo 一次发 3 个 dev tag，**全部围绕新一代硬件 + 模型**：

### v1.3.0-deepseek-v4-dev.1（**2026-06-06 00:16 UTC**）

- **DSv4-Pro**（`deepseek-ai/DeepSeek-V4-Pro`）走 Dynamo **TensorRT-LLM** 后端
- TRT-LLM pin `1.3.0rc15.post1`（`#10343`）
- 关键：**.post1 加 ~140 commits over `rc15`**，几乎全是 DSv4
- **核心 model support** — DSv4/V4-Pro 启用 + fused **mHC** (Manifold-Constrained Hyper-Connections) RMS-norm + V4-Pro hidden-size handling (#13587, #13771)
- **Attention/MLA** — MLA dependency-aware overlap, BF16 compressor-input optimization, indexer top-k + compressed-length handling (#13629, #13761, #13802, #13811)
- **Quantization** — DSv4 FP8 (`o_a_proj` FP8 + fused inv-rope FP8 quant) + **NVFP4** support (#13938, #14026)
- **MoE/routing** — bf16 custom router GEMM kernel + EPLB for DSv4 (#13646, #13595)
- **Tool calling** — DSv4 tool template + parser (#13608)
- **KV cache V2 + disaggregated serving** — V2 KV-cache manager/events + 多 disagg stability fixes

**架构含义**：DSv4 + 1M ctx + 3 reasoning modes + MoE 1.6T/49B-active 走完整 TRT-LLM 路径。**和 vLLM #44692（mHC fused-RMSNorm 静默 NaN）形成镜像**：vLLM 侧在 H=7168 修 TileLang pipeline bug，TRT-LLM 侧在 V4 hidden-size 加专门 handling。

### v1.3.0-nemotron-ultra-dev.1（**2026-06-05 17:51 UTC**）

- **Nemotron-3-Ultra**（`nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4`）走 Dynamo **vLLM** 后端
- **CUDA 13 vLLM runtime base → v0.22.0**（r6 时 v0.22.1 已发）
- patch stack 在 `container/deps/vllm/patches/v0.22.0/ultra/` 路径下（**vLLM 自身用 vendored patch 而非 upstream**）
- **关键能力**：Mamba prefix-cache P/D runtime support + hybrid hash-block KV events + MTP conv-state layout handling + SSM/NIXL tail fix（`#10234`）
- aggregated + disaggregated recipes，B200 / H200 两档硬件，chat + agentic profile（`#10303`）
- H200 上 262K max context + MTP speculative decoding (1 token)

**架构含义**：**Nemotron-3-Ultra 是 hybrid Mamba/Attention/MoE**，**Mamba prefix-cache P/D 是 hybrid 架构第一次在 P/D 分离上有 runtime 支持**。

### v1.3.0-nemotron-super-dev.1（**2026-06-04**）

- Nemotron-Super 系列，vLLM 后端
- 配合 ultra tag 的 patch stack 思路

## 7 · LiteLLM v1.88.0-rc.3 + Langfuse v3.178.0 + Kong 3.9.2

### LiteLLM v1.88.0-rc.3（**2026-06-05 02:10 UTC**）

相比 rc.2 唯一变更：`chore(release): patch v1.88.0-rc.1 with four staged fixes`（#29632）。rc.2 自身又是 v1.88.0-rc.1 + session-token budget-ceiling exemption（#29637）+ harden `GHSA-q775` session-token exemption against `default_key_generate_params`（#29639）。**架构含义**：**v1.88 主线在做"安全硬化 + session-token 边界"**，跟 r6 #29782（orjson for /v1/messages +23% RPS）不冲突 —— 性能与安全两条独立轨道。

### Langfuse v3.178.0（**2026-06-02 13:29 UTC**）

24h 内 4 个新版本（v3.175 → v3.178）。v3.178 主要项：

- `feat(agent): Connect in-app agent to langfuse MCP`（#13747）
- `feat(mcp): Add optional id to upsertDataset`（#13946）
- `fix(security): enforce auditLogs:read and audit-logs entitlement for audit_logs batch exports`（#13980）
- `refactor(comments): Make comment TRPC routes read from events table`（#13473）
- `fix(agent): Remove explicit LANGFUSE_AWS_BEDROCK_REGION precondition`（#13991）

**架构含义**：**Langfuse agent + MCP 集成 + audit log entitlement 是 6 月初的 3 条主线**。audit log 加 entitlement 是 enterprise readiness 信号。

### Kong 3.9.2（**2026-06-04 07:12 UTC**）

- Bump luarocks 3.11.1 → 3.12.2
- **6 个 nginx CVE 一次性 backport**：
  - **CVE-2026-40701**, **CVE-2026-40460**, **CVE-2026-42934**, **CVE-2026-42946**, **CVE-2026-42945**, **CVE-2026-9256**

**架构含义**：**Kong 3.9.2 是 6 月 nginx 系列 CVE 集中 backport**。CVE-2026-42945 在 Higress v2.2.2 release notes 也被引用（"避免了 CVE-2026-42945 heap overflow"）—— **整个 AI gateway 生态 6 月都在做 nginx-core CVE 同步**。

## 8 · 关键 take-aways（24h 落点）

1. **「不变量检测」从研究 → 工程化**：vLLM #44719（KV cache NaN 推广）、#43150（fp64 gumbel 多 path 覆盖）、#44435（batch-invariance 全 Llama 3.2 覆盖）—— **3 件 PR 同时推"可追溯 + 可重现"两面**。
2. **「安全漏点」= env var cache factor + DEBUG pprint**：vLLM #44696 暴露 `VLLM_API_KEY`，**所有 secret 类 env var 走同一道 ignore list 才能根治**。
3. **「kernel 只验过默认 hidden_size」= 静默 NaN**：vLLM #44692 mHC 在 H≠4096 全部数值错误，**TileLang 软件流水线对 hidden_size 最敏感**。
4. **「P/D 分离 socket 池握手错配」= 隐形 boss**：llm-d #1564 uvicorn 5s vs Go transport 90s 不匹配 → RST。**默认值应是 prefill P99 × 2**。
5. **「横向能力抽 CRD/插件」= 共识**：Higress `ai-provider-affinity` 独立 WASM + Envoy `MCPBackend` CRD 提案 + agentgateway 多 backend policy merge —— **三个项目同 24h 走"policy/capability 抽出来"**。
6. **「DP 部署从 greedy → 节点 allowlist」**：vLLM #44669 显式分区 Ray 节点，**多 DP 引擎共享 Ray 不再有 race**。
7. **「Dynamo 三 dev tag 锁新一代硬件+模型」**：DSv4（1.6T/49B-active 1M ctx）+ Nemotron-3-Ultra（550B/A55B hybrid Mamba）+ Nemotron-Super，**TRT-LLM `1.3.0rc15.post1` +140 commits 主打 DSv4**。
8. **「nginx CVE 6 件套 6 月集中 backport」**：Kong 3.9.2 + Higress v2.2.2 +（隐含）所有 nginx-core 衍生品。

## 9 · AIGW 落点（累加 91 条，新增 7 条）

**#92** · kernel 类 PR 必须在**多组 hidden_size**（H∈{2048,3072,4096,5120,6144,7168,8192}）上跑 golden，**不能只验默认值**；
**#93** · `compile_factors()` 的 `ignored_factors` 集合必须把**所有 secret 类 env var**全部列入，**S3_* / VLLM_API_KEY / BEDROCK_* / HF_TOKEN 一视同仁**；
**#94** · P/D 分离 uvicorn `VLLM_HTTP_TIMEOUT_KEEP_ALIVE` 配 sidecar `IdleConnTimeout` 时**下限设 prefill P99 × 2**（≥120s 是经验值）；
**#95** · 新版 reasoning effort 必须**自维护常量 + 兼容上游 SDK**（`anthropic-sdk-go` 升级 = 不可避免），**不要直接用上游常量**；
**#96** · `Set-Cookie` 在反向代理 / WASM 插件里**逐个 emit，不能 comma-fold**（RFC 6265 唯一例外）；
**#97** · DP placement 引擎间共享 Ray 集群时**必须给每个引擎显式节点 allowlist**（env `VLLM_RAY_DP_PLACEMENT_NODE_IPS`）；
**#98** · Anthropic `display` 字段在 Opus 4.7+ **默认从 `summarized` 变 `omitted`**，**显式 `display: "summarized"` 才会收 thinking 摘要**。

## 引用与数据来源

### vLLM PRs
- #44692（mHC fused-RMSNorm hidden_size ≠ 4096 静默 NaN，已合并）：https://github.com/vllm-project/vllm/pull/44692
- #44696（`VLLM_API_KEY` 泄漏到 cache_key_factors.json，open 安全）：https://github.com/vllm-project/vllm/pull/44696
- #44719（KV cache NaN 检测 Phase 2，open）：https://github.com/vllm-project/vllm/pull/44719
- #43150（`--use-fp64-gumbel` 5 path 覆盖）：https://github.com/vllm-project/vllm/pull/43150
- #42832（ROCm GPT-OSS RoPE+static Q FP8+KV fusion）：https://github.com/vllm-project/vllm/pull/42832
- #41002（ROCm sparse indexer WorkspaceManager）：https://github.com/vllm-project/vllm/pull/41002
- #43874（NixlConnector `kv_both` 软弃用 Phase 1）：https://github.com/vllm-project/vllm/pull/43874
- #44669（DP placement 节点 allowlist）：https://github.com/vllm-project/vllm/pull/44669
- #44435（batch-invariance Llama-3.2-3B 覆盖）：https://github.com/vllm-project/vllm/pull/44435
- #43684（ROCm ApplyRotaryEmb flash_attn 65535 限制回退）：https://github.com/vllm-project/vllm/pull/43684
- #44613（MoE FusedMoEConfig max_cudagraph_capture_size snapshot）：https://github.com/vllm-project/vllm/pull/44613
- #44709（RMSNorm quant fusion dtype guard）：https://github.com/vllm-project/vllm/pull/44709
- #44391（Rust Frontend `include_reasoning=false`）：https://github.com/vllm-project/vllm/pull/44391
- #44559（Voxtral MistralCommonFeatureExtractor transformers ≥5.10 兼容）：https://github.com/vllm-project/vllm/pull/44559
- vLLM v0.22.1（2026-06-05）：https://github.com/vllm-project/vllm/releases/tag/v0.22.1
- vLLM v0.22.0（2026-05-29）：https://github.com/vllm-project/vllm/releases/tag/v0.22.0

### llm-d PRs
- #1564（P/D prefill keep-alive 90s ↔ 5s 错配修复）：https://github.com/llm-d/llm-d/pull/1564
- #1654（cpu offloading 基准最小验证）：https://github.com/llm-d/llm-d/pull/1654
- #1627（nightly WVA script 拆出）：https://github.com/llm-d/llm-d/pull/1627
- #1637（nightly e2e → nightly benchmark 迁移 starting with optimized-baseline）：https://github.com/llm-d/llm-d/pull/1637
- #1663（guides OWNERS 文件）：https://github.com/llm-d/llm-d/pull/1663
- #1689（e2e 切 new tokenizer than UDS）：https://github.com/llm-d/llm-d/pull/1689
- #1620（optimized baseline multimodal guide）：https://github.com/llm-d/llm-d/pull/1620

### Higress PRs
- #3898（`ai-load-balancer` cluster_hash FNV-1a 一致性 LB）：https://github.com/alibaba/higress/pull/3898
- #3867（`ai-provider-affinity` 独立 WASM 插件）：https://github.com/alibaba/higress/pull/3867
- #3895（`ai-security-guard` Embedding API content detection）：https://github.com/alibaba/higress/pull/3895
- #3894（`x_higress_guardrail` 结构化拒绝 + AI logging + error metrics）：https://github.com/alibaba/higress/pull/3894
- #3928（OIDC `Set-Cookie` shard 串接修复）：https://github.com/alibaba/higress/pull/3928
- #3907（Bedrock Runtime Invoke 路径）：https://github.com/alibaba/higress/pull/3907
- #3904（Vertex passthrough strip `anthropic-beta` / `anthropic-version`）：https://github.com/alibaba/higress/pull/3904
- #3922（rebuild MCP filter 200 MiB 内存阈值）：https://github.com/alibaba/higress/pull/3922
- #3923（删 request-count 重建触发器）：https://github.com/alibaba/higress/pull/3923
- Higress v2.2.2（2026-05-26，含 nginx CVE-2026-42945 修复）：https://github.com/alibaba/higress/releases/tag/v2.2.2

### Envoy AI Gateway PRs
- #2184（Responses API token 捕获 `incomplete/failed`）：https://github.com/envoyproxy/ai-gateway/pull/2184
- #2144（`MCPBackend` CRD 提案）：https://github.com/envoyproxy/ai-gateway/pull/2144
- #2122（Azure OpenAI Responses API）：https://github.com/envoyproxy/ai-gateway/pull/2122
- #2089（Claude Opus 4.7 `xhigh` 努力档）：https://github.com/envoyproxy/ai-gateway/pull/2089
- #2099（Anthropic→OpenAI translator reasoning + image）：https://github.com/envoyproxy/ai-gateway/pull/2099
- #2132（日志脱敏瘦身）：https://github.com/envoyproxy/ai-gateway/pull/2132
- #2023（`/v1/audio/transcriptions` + `//v1/audio/translations`）：https://github.com/envoyproxy/ai-gateway/pull/2023
- #2136（OpenAI schema `audio_url` + `video_url`）：https://github.com/envoyproxy/ai-gateway/pull/2136
- #2187（CI 测试模型升级 gemini-3.1-flash-lite）：https://github.com/envoyproxy/ai-gateway/pull/2187
- #2052（OAuth 2.0 Token Exchange as Upstream Auth for MCP Backends 提案）：https://github.com/envoyproxy/ai-gateway/pull/2052
- #2148（fix: map anthropic beta header for AWSAnthropic）：https://github.com/envoyproxy/ai-gateway/pull/2148
- Envoy AI GW v0.6.0（2026-05-05）：https://github.com/envoyproxy/ai-gateway/releases/tag/v0.6.0

### agentgateway PRs
- #2039（多 AI backend policy 合并）：https://github.com/agentgateway/agentgateway/pull/2039
- #2106（Anthropic system messages）：https://github.com/agentgateway/agentgateway/pull/2106
- #2105（`simple llm` TLS）：https://github.com/agentgateway/agentgateway/pull/2105
- #2086（eviction 与 health 解耦）：https://github.com/agentgateway/agentgateway/pull/2086
- #2100（MCP resource subscribe）：https://github.com/agentgateway/agentgateway/pull/2100
- #2104（Bedrock `detect-passthrough`）：https://github.com/agentgateway/agentgateway/pull/2104
- #2098（`agctl` CLI 重组）：https://github.com/agentgateway/agentgateway/pull/2098
- #2101（websocket case insensitive upgrade token）：https://github.com/agentgateway/agentgateway/pull/2101
- #2099（local LLM CORS）：https://github.com/agentgateway/agentgateway/pull/2099
- agentgateway v2.2.2（2026-05-26）：https://github.com/agentgateway/agentgateway/releases/tag/v2.2.2

### Dynamo / NVIDIA
- Dynamo v1.3.0-deepseek-v4-dev.1（2026-06-06 00:16 UTC，DSv4-Pro + TRT-LLM `1.3.0rc15.post1`）：https://github.com/ai-dynamo/dynamo/releases/tag/v1.3.0-deepseek-v4-dev.1
- Dynamo v1.3.0-nemotron-ultra-dev.1（2026-06-05 17:51 UTC，Nemotron-3-Ultra 550B/A55B NVFP4 + vLLM v0.22.0 patch stack）：https://github.com/ai-dynamo/dynamo/releases/tag/v1.3.0-nemotron-ultra-dev.1
- Dynamo v1.3.0-nemotron-super-dev.1（2026-06-04）：https://github.com/ai-dynamo/dynamo/releases/tag/v1.3.0-nemotron-super-dev.1
- TRT-LLM `1.3.0rc15...1.3.0rc15.post1` diff（~140 commits，几乎全 DSv4）：https://github.com/NVIDIA/TensorRT-LLM/compare/v1.3.0rc15...v1.3.0rc15.post1

### LiteLLM / Langfuse / Kong
- LiteLLM v1.88.0-rc.3（2026-06-05 02:10 UTC）：https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3
- LiteLLM v1.88.0-rc.2（2026-06-04 16:43 UTC）：https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.2
- LiteLLM #29632（patch v1.88.0-rc.1 with four staged fixes）：https://github.com/BerriAI/litellm/pull/29632
- LiteLLM #29637（session-token budget-ceiling exemption）：https://github.com/BerriAI/litellm/pull/29637
- LiteLLM #29639（harden GHSA-q775 session-token exemption against default_key_generate_params）：https://github.com/BerriAI/litellm/pull/29639
- Langfuse v3.178.0（2026-06-02 13:29 UTC）：https://github.com/langfuse/langfuse/releases/tag/v3.178.0
- Langfuse #13980（enforce auditLogs:read and audit-logs entitlement）：https://github.com/langfuse/langfuse/pull/13980
- Langfuse #13747（Connect in-app agent to langfuse MCP）：https://github.com/langfuse/langfuse/pull/13747
- Kong 3.9.2（2026-06-04 07:12 UTC，6 个 nginx CVE 一次性 backport）：https://github.com/Kong/kong/releases/tag/3.9.2
- Kong CHANGELOG.md 3.9.2 节：https://github.com/Kong/kong/blob/release/3.9.x/CHANGELOG.md#392
