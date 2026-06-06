# AI Gateway · 架构对比 / 性能基准 round 8

> **时间锚定**：2026-06-07 06:19 CST（local `date +%Y-%m-%d-%H%M`）/ UTC 2026-06-06 22:19。
> **主题**：hour 6 mod 7 = 6 → 架构对比 / 性能基准（**真实 throughput / latency / memory / 调度异常数字优先**）。
> **范围**：过去 36h（UTC 2026-06-05T22:19 → 2026-06-06T22:19）。**不重复** r1–r7 / `inference-gw` 已覆盖的 PR。
> **核心三轴**：（1）Envoy AI Gateway **v0.7.0** release 落地（71 files / +17586/-355）；（2）vLLM **397B-A17B-NVFP4 +24.4%** / **RDNA3 W4A16 MoE 2.17×** 双重量级回归；（3）agentgateway `agctl` CLI 重构 + 9-PR cluster。

## TL;DR · 一页数字

| 维度 | 数字 / 结论 | 仓库 / PR |
| --- | --- | --- |
| **vLLM Qwen3.5-397B-A17B-NVFP4 end-to-end** | unified 131,976 → split **164,156 tok/s**，**+24.4%** | [vllm#44700](https://github.com/vllm-project/vllm/pull/44700) |
| **vLLM 397B kernel micro-bench (953+7239)** | chunk 4361 µs → split **2256 µs**，**1.93×** | [vllm#44700](https://github.com/vllm-project/vllm/pull/44700) |
| **vLLM ROCm W4A16 MoE on RDNA3 (1× RX 7900 XTX)** | batch=32 throughput **348 → 756 tok/s**，**2.17×**；TPOT 65.4 → 31.9 ms（**2.05×**）；TTFT 14.9s → 8.6s（**1.72×**） | [vllm#44075](https://github.com/vllm-project/vllm/pull/44075) |
| **vLLM mHC fused-RMSNorm miscompile** | hidden=2048/3072 **直接 NaN**；DSv4(H=7168) H≥512 触发 | [vllm#44692](https://github.com/vllm-project/vllm/pull/44692) |
| **Envoy AI GW v0.7.0 release** | hostname multi-tenant + Anthropic→Bedrock Converse + Audio + Azure Responses + QuotaPolicy runtime + **rules cap 128→15** + `xhigh` 推理档 | [aigw#2177](https://github.com/envoyproxy/ai-gateway/pull/2177) |
| **Envoy AI GW QuotaPolicy runtime** | xDS snapshot → backend RL filter → Redis counter by token count | [aigw#1869](https://github.com/envoyproxy/ai-gateway/pull/1869) |
| **Envoy AI GW responses API token capture** | `completed/incomplete/failed` 全捕获；`max_output_tokens` 中断流不再报 0 token | [aigw#2184](https://github.com/envoyproxy/ai-gateway/pull/2184) |
| **Envoy AI GW log redaction 收紧** | 解除 `tool.description` / `response_format.json_schema` redact | [aigw#2132](https://github.com/envoyproxy/ai-gateway/pull/2132) |
| **agentgateway `agctl proxy/controller log`** | port-forward + admin API；multi-pod fan-out；process-local state 多副本可能不一致 | [agentgateway#2098](https://github.com/agentgateway/agentgateway/pull/2098) |
| **agentgateway `config_synchronized` gauge** | 暴露"上次 config 加载成功" 0/1 信号 | [agentgateway#2061](https://github.com/agentgateway/agentgateway/pull/2061) |
| **agentgateway AWS AssumeRole** | 29 files / +2196/-971 跨账号 / 跨组织 inference 入口 | [agentgateway#2037](https://github.com/agentgateway/agentgateway/pull/2037) |
| **LiteLLM record/replay proxy 普惠** | 从 gpt-image-1 扩到 chat/embeddings/moderations/rerank/Anthropic；`api_base` 路径前缀而非 header | [litellm#29847](https://github.com/BerriAI/litellm/pull/29847) |
| **LiteLLM Anthropic ctx overflow 500→400** | `ExceptionCheckers.is_error_str_context_window_exceeded` 双 phrasing 识别 | [litellm#29848](https://github.com/BerriAI/litellm/pull/29848) |
| **LiteLLM MCP per-server env vars** | global + per-user scope；`${NAME}` 运行时插值；list/edit 往返不再丢 `env_vars` | [litellm#28917](https://github.com/BerriAI/litellm/pull/28917) |
| **Kong 3.9.3** | version bump 6/4；含 nginx CVE cherry-pick + pluginserver revert | [kong#14890](https://github.com/Kong/kong/pull/14890) |

## 1. vLLM 性能回归两条主线

### 1.1 Split prefill+decode batch（[vllm#44700](https://github.com/vllm-project/vllm/pull/44700)）

**问题**：GDN attention 把**所有 non-spec token**走 `chunk_gated_delta_rule`，每条 decode 单独 padded 到 `FLA_CHUNK_SIZE=64`。`D` 条 decode = `D` 个近乎空的 64-token chunk。Qwen3.5-35B-A3B/35B-A3B-FP8/397B-A17B-NVFP4 三档 GSM8K 无精度损失，但 kernel 时间被 decode 空 padding 吃掉。

| 案例 | Kernel | Median (µs) |
| --- | --- | --- |
| prefill 8192 | CuteDSL chunk | 464.1 |
| decode 953 | fused_sigmoid | 1843.7 |
| Sum | | 2370.8 |
| **旧 unified (953+7239 → chunk)** | CuteDSL chunk | **4361.6** |
| **新 split (pre+dec)** | CuteDSL + fused_sigmoid | **2256.5** |

**修法**：non-spec batch 混合 prefill/decode 时，把 decode front-slice 剥到 recurrent update kernel `fused_sigmoid_gating_delta_rule_update`，只剩 prefill tail 走 chunk。metadata builder rebase chunk metadata 到 prefill-only tail；outputs 以 decode-first 顺序 stitch。

**端到端**（8×B200, DP=8+EP, ISL=8192 / OSL=256, conc=2048, steady-state）：

| Metric | Baseline | With split | Δ |
| --- | --- | --- | --- |
| **Total tok/s** | 131,976 | **164,156** | **+24.4%** |

附加：MTP eval config for Qwen3.5-397B NVFP4；`fast_kernel` → `aiter_kernel` 重命名（"fast_kernel 太通用"）= 命名权收敛到 ROCm 生态约定。

### 1.2 ROCm W4A16 MoE on RDNA3（[vllm#44075](https://github.com/vllm-project/vllm/pull/44075), JartX, +1906/-5, 11 files）

**硬件目标**：AMD RDNA3 gfx1100（消费卡 RX 7900 XTX / RX 7800 XT），替换 Triton `fused_moe_kernel_gptq_awq`。HIP 原生 kernel `csrc/rocm/moe_q_gemm_rdna3.cu` 把 expert routing + W4A16 GEMM 一次 launch 完：`v_dot2_f32_f16` / `v_dot2_f32_bf16` + exllama bit-trick dequant + 64-bit CAS atomic output。

**关键 trick**：`output_topk` 把 `moe_sum` fuse 进 w2 kernel → atomics 写 `out[token_id / top_k]`，**消掉一次独立 kernel launch + 中间 buffer**；bf16 `M=1` fast path 跳过 LDS staging（direct global read，`v_dot2_f32_bf16` opacity trick 反 InstCombine）；decode `BLOCK_SIZE_M=1`（消掉 ~75% padding waste）；pre-allocated w1/act buffer。**Build guard**：`.cu` 仅当 `VLLM_GPU_ARCHES` 含 `gfx1100` 时编译；torch op 注册在 `#ifdef VLLM_ROCM_GFX1100` 下；Python 侧用 `hasattr(torch.ops._rocm_C, "moe_gptq_gemm_rdna3")` 探测。`_try_get_rocm_moe_method()` dispatch 检查 arch + op 可用性，**RDNA4/CDNA 可加 branch**；不可用时 fall through Triton WNA16。

**Benchmark**（EvalScope `perf` / `openqa` / 50 req / 1× RX 7900 XTX，模型 `cyankiwi/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit`，MoE 128/8 active，W4A16 AWQ）：

**Throughput (completion tok/s)**

| max_num_seqs | Triton (upstream) | HIP (this PR) | Speedup |
| ---: | ---: | ---: | ---: |
| 1 | 82.84 | 102.01 | **1.23×** |
| 8 | 186.99 | 401.94 | **2.15×** |
| 32 | 348.49 | 755.62 | **2.17×** |

**Per-request latency (max_num_seqs = 32)**

| Metric | Triton | HIP | Improvement |
| --- | ---: | ---: | ---: |
| TPOT (ms) | 65.4 | 31.9 | 2.05× |
| Latency avg (s) | 65.3 | 33.4 | 1.95× |
| TTFT avg (ms) | 14,888 | 8,634 | 1.72× |

**关键观察**：speedup 随 concurrency 升（~1.2× 单流 → ~2.2× 批 8-32）= **改善的是 batched decode 效率**，不是单请求延迟。**精度（gsm8k, 5-shot）**：HIP `0.868/0.840` vs Triton `0.848/0.836` —— **略升不降**。

### 1.3 Bugfix 三连

- **vllm#44692**（zyongye, +1/-1）：mHC pre-big-fuse-with-RMSNorm 在 `num_stages=3` + persistent `output_shared` + loop-carried `sumsq` 组合下 TileLang software pipeliner **miscompile loop**。hidden=2048/3072 → **NaN**；DSv4(H=7168) H≥512 触发。
- **vllm#44694**（vadiklyutiy）：Qwen3.5-FP8 nightly fail —— `fused_add_rms_norm` input/weight dty 守卫。
- **vllm#44613**（aoshen02）：MoE `max_cudagraph_capture_size` snapshot 进 `FusedMoEConfig`。

## 2. Envoy AI Gateway v0.7.0（[aigw#2177](https://github.com/envoyproxy/ai-gateway/pull/2177), 71 files / +17586/-355）

### 2.1 Multi-tenant hostname routing（核心新范式）

`AIGatewayRoute.spec.hostnames` 可指定 hostname 列表（含 `*.ai.example.com` wildcard）。`/v1/models` 自动**只返回当前 Host header 匹配 route 的 models**。一个 Gateway = 多个 tenant 各看自己 catalog。**配套 breaking**：`AIGatewayRoute.spec.rules` **cap 从 128 降到 15**，对齐 Gateway API HTTPRoute 限制（一个 slot 留给 controller-injected catch-all rule）。多 rules 必须**拆 AIGatewayRoute 资源**。

### 2.2 Provider 翻译 + 推理档

- **Anthropic `/v1/messages` → AWS Bedrock Converse API**（text + image + tool use + thinking + streaming）—— Anthropic-native client 不改协议即可上 Bedrock；
- **Anthropic→OpenAI reasoning + image**：`/v1/messages` → `/v1/chat/completions` 保留 thinking / redacted_thinking blocks + image block → OpenAI `image_url`；**之前 silently dropped**；
- **Claude Opus 4.7 完整 reasoning**：`display` 参数（`summarized`/`omitted`，**默认 `omitted`**）+ `xhigh` effort tier（6 档）+ `claude-mythos-preview` 也认 effort；
- **`anthropic-beta` header → `anthropic_beta` body field** for AWSAnthropic backends；**Anthropic `prefix` 路径** 自定义 path —— **AWSAnthropic / GCPAnthropic 内部 override path 仍忽略 prefix**。

### 2.3 OpenAI 兼容 + QuotaPolicy runtime

- **Audio endpoints**：`/v1/audio/transcriptions` (Whisper) + `/v1/audio/translations` —— `multipart/form-data` 路径（[aigw#2023](https://github.com/envoyproxy/ai-gateway/pull/2023)，+3607/-6，39 files），同一套 auth / rate limit / observability；
- **Azure OpenAI Responses API**：`/v1/responses?api-version=...` —— Azure 用户不换 client code；
- **audio_url / video_url content types** —— vLLM phi-4-mm / Qwen 3.5 multimodal 入口打通；
- **QuotaPolicy runtime**（[aigw#1869](https://github.com/envoyproxy/ai-gateway/pull/1869)，+7083/-90，31 files）：`QuotaPolicy` 挂 `AIServiceBackend` 时 controller 注入 backend rate limit filter，`BuildRateLimitConfigs()` → `xDS snapshot` → gRPC → Envoy xDS → request-time 限速 → `HitsAddend` 累计 token count → Redis 计数。**离"full quota-aware routing across multiple backends"还有距离**。

### 2.4 MCP + Observability + Bugfix 7 连

- **MCP `tools/list` 走 authorization 过滤** —— 不被授权的 tool 名字不暴露；
- **log redaction 收紧**（[aigw#2132](https://github.com/envoyproxy/ai-gateway/pull/2132)）：解除 `tool.description` / `tool.parameters` / `tool.function.name` / `response_format.json_schema` / `guided_json` 的 redact（**developer-authored schema metadata**），仍 redact **user-provided content** + **AI-generated content**。distinction：redact "数据" 不 redact "schema"。
- **Bugfix 7 连**：SSE parser `data:{json}`（no space after colon）；Responses API SSE buffering；token usage 从 `incomplete` / `failed` 捕获（**`max_output_tokens` 触发的流不再报 0 token** —— [aigw#2184](https://github.com/envoyproxy/ai-gateway/pull/2184)）；Bedrock 200 + 无 `output` nil guard；Gemini finish-reason 全映射（`SAFETY` / `BLOCKLIST` / `RECITATION` / `MALFORMED_FUNCTION_CALL` ...）—— 未知 → `error`；GCP Vertex AI streaming 无 candidate content → **空 `delta` 对象**；Responses API assistant message 无 `type:"message"`（OpenCode 这种）→ 正确识别。

## 3. agentgateway 9-PR cluster（2026-06-05 22 UTC 一小时内）

howardjohn（Solo.io）+ jbohanon + ankkod 同时合入。**核心 ops 升级 + Anthropic-native 支持 + MCP 完善**。

- **#2098 agctl**（jbohanon, +451/-17, 10 files）—— **核心 ops 工具升级**：`agctl proxy` / `agctl controller` 子命令分组；`config` / `trace` 沉到 `agctl proxy` 下；`agctl proxy log` —— `kubectl port-forward` + admin `/logging`；`--set <module>=<level>` 增量追加 Rust tracing-subscriber filter directive（如 `agentgateway::proxy`）；`agctl controller log` —— Go slog `?component=level`；**multi-pod fan-out**：`kubeutil.ForEachPod` 全打一遍再返回首个错 —— 读时 fan-out 读到 process-local state，**HA controller 副本间 level 可能不一致**。
- **#2106 anthropic system messages**（howardjohn, +337/-136, 9 files）：替代 #2015/#2089 —— 旧 PR 无条件改 body 风险大；**新实现 preserve request，只在需要时转换**。
- **#2104 detect-passthrough for bedrock**（howardjohn）：`passthrough: detect` 模式 —— "全捕获 claude code + bedrock 流量"，observability 关键开关。
- **#2101 websocket case-insensitive upgrade token**（howardjohn）：RFC 6455 严格 lowercase，**部分客户端（特别是某些 IDE bridge）大写** —— WebSocket 升级失败排查巨坑修。
- **#2100 mcp resource subscribe**（howardjohn, +230/-20, 4 files）：`resources/subscribe` method + watch GET stream + 名称 multiplexing。
- **#2105 simple llm TLS** / **#2099 local llm CORS** / **#2086 no evict when health without eviction**（howardjohn）：本地 LLM serving 加 TLS / browser 调用入口 / **关键修复** —— 配置 health 但未配置 eviction 时**不要**做 evict 操作。
- **#2061 config_synchronized metric**（jbohanon, +37/-8, 4 files）：`agentgateway_config_synchronized` gauge，0/1 信号 —— **CI/CD 流水线可编程判断 "config 加载成功"**，对应 issue #2057。
- **#2039 Compose multiple AI backend policies**（howardjohn, +98/-19, 1 file）：AI policy **field-wise merge**，promptguard + `/v1/messages` + wildcard 路由回归覆盖。
- **#2037 AWS AssumeRole**（howardjohn, +2196/-971, 29 files）：跨账号 / 跨组织 inference 入口一次性补齐。
- **#1993 cache_creation_input_tokens non-streaming**（ankkod）：Anthropic cache 计量在 non-streaming response 中补全。

## 4. LiteLLM 2026-06-06 staging promote + 功能 PR

- **#29861**（+151158/-25435, **1444 files**）：chore(ci): promote internal staging to main —— **超大 PR 几乎全是 CircleCI / GH Actions / `.gitattributes` 调整** + test infra 翻新。**结论：LiteLLM 测试 infra 进入 "UI API types 从 OpenAPI 自动生成" 阶段**。
- **#29862**（5 files）：staging 功能 promote —— **功能侧 = [litellm#29848](https://github.com/BerriAI/litellm/pull/29848)**（Anthropic context overflow 500→400 + failed auth trace seed）。
- **#29847 record/replay proxy 普惠**：从 gpt-image-1 扩到 chat/embeddings/moderations/rerank/Anthropic。**路径前缀而非 header**：`api_base=/__recorder_upstream/<host>/`。**为什么不用 header** —— cohere rerank 丢未知 header，header 路由**跨 provider replay 不一致**。upstream fold 进 cache key。
- **#28917 MCP per-server env vars**（+5951/-110, 37 files）：`${NAME}` 在 `static_headers` 运行时插值，**global scope**（admin 配一次全员用）+ **per-user scope**（用户在 MCP Gateway dashboard 自填）。**list/edit 往返 bug**：`GET /v1/mcp/server` 从 in-memory registry 重建 `LiteLLM_MCPServerTable` 时 `_build_mcp_server_table` / `health_check_server` **复制 `static_headers` 但丢了 `env_vars`** → list 永远返回 `env_vars: null` → admin edit form 加载空 env var list → 保存任何 edit 都 persist `env_vars: []` 静默清掉存的变量 → `${VAR}` literal 上游透传。**双 conversion 现在都带 `env_vars`**。
- **#29848 fix: 400 on Anthropic context overflow; seed identity on failed auth**：Anthropic 上下文溢出有时 500 而不是 400 —— "input length and max_tokens exceed context limit: A + B > C" 在 upstream exception 没 `status_code` 时 fall through 到 `APIConnectionError`(500)。**修法**：`ExceptionCheckers.is_error_str_context_window_exceeded` 在 status-code gate 之前 detect 双 phrasing。同时 OTEL V2 `seed_request_identity` 加 `auth` phase span fallback —— failed trace 也带 `litellm.team.id` / `gen_ai.request.model`。

## 5. 5 个反常识 / 横向洞察

1. **vLLM GDN attention 把 decode 浪费在 64-token padding chunk** —— 不是 decode 不能并行，是 chunked kernel 把 `D` 个 decode 各 pad 到 64-token 满，**总有效 compute 占不到 1/64**。**split 路径本质是"kernel-level routing"** —— 跟 AI GW 层的 model routing 是同构问题，只是粒度到 kernel。
2. **RDNA3 W4A16 MoE 2.17× speedup 是 kernel-level 优化** —— 不是 dequant 算法升级，是 **`v_dot2_f32_bf16` + 64-bit CAS atomic + `output_topk` 融合 `moe_sum`** 三件套让 expert routing + GEMM 一次 launch 完。**消费级显卡追平数据中心卡的"低成本路径"** = 部署形态新选项。
3. **Envoy AI GW `rules` cap 从 128 降到 15** 是**对 Gateway API 限制定位** —— AI GW 在 `HTTPRoute` 层挂载能力，**HTTPRoute limit 决定 AIGatewayRoute limit**。**AIGW = HTTPRoute + AI policy，不是平行的另一种资源**。这对"单 AIGW 巨型 yaml"模式是 breaking。
4. **agentgateway `agctl proxy log` multi-pod fan-out 暴露"process-local state"** —— HA controller 副本的 log level 可能各不同步。**这是 K8s 上 multi-replica 控制面 + log-level 动态调谐的根本问题**。`agentgateway_config_synchronized` gauge 解决"config 加载"侧，**"运行时 process state" 侧**仍是 Open Question。
5. **LiteLLM record/replay proxy 走 `api_base` 路径前缀而非 header** —— 因为 **cohere rerank 丢未知 header**。**provider 行为异质性决定了"测试基础设施"必须用最保守的"语义层不变量"做 routing 维度**。HTTP header 在 OpenAPI 客户端里不是"uniformly preserved" 的一等公民。

## 6. AIGW 5 条新硬要求（增量 → 累加 118 条）

- **(A-114)** AI GW / AIGatewayRoute 资源 `rules` 上限按 v0.7 降到 15；多 rules 必拆 AIGatewayRoute；**老配置**（>15 rules）升级 v0.7 前**先拆 yaml**。
- **(A-115)** 部署 `claude-opus-4-7` / `claude-mythos-preview` 必须显式 `display:"summarized"`（默认 `omitted`），否则 thinking 摘要不会回传；`xhigh` effort 仅 long-horizon agentic / coding 任务开。
- **(A-116)** 自研 AI GW 路径要走 vLLM `aiter_kernel` 命名（`fast_kernel` 已 deprecated）+ 对 Qwen3.5-397B-A17B-NVFP4 这类 MoE+GDN attention 走 split path 部署。
- **(A-117)** 部署 ROCm RDNA3 W4A16 MoE 必须确认 `VLLM_GPU_ARCHES` 含 `gfx1100`（否则 kernel 不编译）+ 检查 `hasattr(torch.ops._rocm_C, "moe_gptq_gemm_rdna3")` runtime probe + 配套 lm_eval GSM8K threshold（HIP `0.868/0.840` vs Triton `0.848/0.836` 略升不降）。
- **(A-118)** agentgateway 部署时监控 `agentgateway_config_synchronized` gauge，**多 pod 副本的 log level process-local state** 不一致要靠 `agctl proxy log` multi-pod fan-out 周期性 reconcile；MCP server `GET /v1/mcp/server` + `health` 路径必须**走 in-memory registry `_build_mcp_server_table` 修复后版本**（litellm #28917 修复前 list/edit 往返会静默 wipe env_vars）。

## 7. 旁路

- **Kong 3.9.3**（[kong#14890](https://github.com/Kong/kong/pull/14890), 2026-06-04）：version bump；3.9.2 + cherry-pick nginx CVE patch（[kong#14880](https://github.com/Kong/kong/pull/14880)）+ pluginserver runtime data revert（[kong#14886](https://github.com/Kong/kong/pull/14886)）。
- **Higress**：36h 内 0 个 merged PR —— v2.2.2 (2026-05-26) 之后无主线合入，处于"已发版稳定期"。
- **anthropic-sdk-python v0.107.0**（2026-06-06）：Managed Agents type 微调；v0.106.0（6/5）标 Claude Opus 4.1 deprecated。

## 引用与数据来源

vLLM：[#44700](https://github.com/vllm-project/vllm/pull/44700) · [#44075](https://github.com/vllm-project/vllm/pull/44075) · [#44692](https://github.com/vllm-project/vllm/pull/44692) · [#44694](https://github.com/vllm-project/vllm/pull/44694) · [#44613](https://github.com/vllm-project/vllm/pull/44613)

Envoy AI GW：[#2177 v0.7.0](https://github.com/envoyproxy/ai-gateway/pull/2177) · [#1869 QuotaPolicy](https://github.com/envoyproxy/ai-gateway/pull/1869) · [#2132 log redaction](https://github.com/envoyproxy/ai-gateway/pull/2132) · [#2184 token capture](https://github.com/envoyproxy/ai-gateway/pull/2184) · [#2023 audio](https://github.com/envoyproxy/ai-gateway/pull/2023) · [#2089 Opus 4.7](https://github.com/envoyproxy/ai-gateway/pull/2089) · [#2099 reasoning+image](https://github.com/envoyproxy/ai-gateway/pull/2099) · [#2122 Azure Responses](https://github.com/envoyproxy/ai-gateway/pull/2122)

agentgateway：[#2098 agctl](https://github.com/agentgateway/agentgateway/pull/2098) · [#2106 anthropic sys](https://github.com/agentgateway/agentgateway/pull/2106) · [#2105 TLS](https://github.com/agentgateway/agentgateway/pull/2105) · [#2104 passthrough](https://github.com/agentgateway/agentgateway/pull/2104) · [#2101 WS](https://github.com/agentgateway/agentgateway/pull/2101) · [#2100 MCP subscribe](https://github.com/agentgateway/agentgateway/pull/2100) · [#2099 CORS](https://github.com/agentgateway/agentgateway/pull/2099) · [#2086 no-evict](https://github.com/agentgateway/agentgateway/pull/2086) · [#2061 config sync metric](https://github.com/agentgateway/agentgateway/pull/2061) · [#2039 compose policy](https://github.com/agentgateway/agentgateway/pull/2039) · [#2037 AssumeRole](https://github.com/agentgateway/agentgateway/pull/2037) · [#1993 cache_creation](https://github.com/agentgateway/agentgateway/pull/1993)

LiteLLM：[#29847 record/replay](https://github.com/BerriAI/litellm/pull/29847) · [#29848 ctx overflow](https://github.com/BerriAI/litellm/pull/29848) · [#29861 staging](https://github.com/BerriAI/litellm/pull/29861) · [#29862 staging](https://github.com/BerriAI/litellm/pull/29862) · [#28917 MCP env vars](https://github.com/BerriAI/litellm/pull/28917)

其它：[kong#14890 3.9.3](https://github.com/Kong/kong/pull/14890) · [kong#14880 CVE](https://github.com/Kong/kong/pull/14880) · [kong#14886 revert](https://github.com/Kong/kong/pull/14886) · [anthropic-sdk-python releases](https://github.com/anthropics/anthropic-sdk-python/releases)
