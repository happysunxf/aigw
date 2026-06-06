# AI Gateway 架构对比 / 性能基准 · round 6

> 时间锚定：**2026-06-06 13:21 CST**（local date +%Y-%m-%d-%H%M）。
> 主题：hour % 7 == 6 → 架构对比 / 性能基准（**真实 throughput / latency / memory 数字优先**）。
> 范围：过去 6h（UTC 2026-06-06T00:00 → 13:00）+ 近 7 天内未在 r1–r5 / `inference-gw` 报告覆盖的具体数字。
> 数据全部来自上游 PR 描述自报 / 火焰图实测，median of 5 passes 或 200k calls 标定。

## TL;DR · 一页数字

| 维度 | 数字 | 仓库 / PR |
| --- | --- | --- |
| LiteLLM `/v1/messages` throughput | 68.5 → 84.6 RPS（**+23%**），p50 127 → 102 ms | [litellm#29782](https://github.com/BerriAI/litellm/pull/29782) |
| LiteLLM `/chat/completions` overhead | 5.25 → 4.28 ms（**−18.5%**），RPS 190.5 → 233.2（**+22.4%**） | [#29537](https://github.com/BerriAI/litellm/pull/29537) |
| LiteLLM streaming Delta 构造 | `Delta(content,role)` 12.50 → 2.67 µs/call（**−79%**） | [#29761](https://github.com/BerriAI/litellm/pull/29761) |
| vLLM Qwen3-30B-A3B FP8 TP=4 + EP | **+4.5% E2E throughput**，baseline 13849 tok/s | [vllm#43137](https://github.com/vllm-project/vllm/pull/43137) |
| vLLM Qwen3-32B TP=4 prefill | wall 1110 → 1047 ms（**−5.7%**），AR hidden **95.7%** | [#44677](https://github.com/vllm-project/vllm/pull/44677) |
| vLLM DeepSeek-V3.2 TP=8 ROCm bench | input tokens 46359（**预期 10000**）—— 6× 通胀 | [#44708](https://github.com/vllm-project/vllm/pull/44708) |
| llm-d predicted-latency vs k8s Svc | input **+38.3%**, output **+40.2%**（Qwen3-32B, 10 × H100, 131K ctx） | [llm-d#1705](https://github.com/llm-d/llm-d/pull/1705) |
| llm-d TPU V6 P/D + WVA 4 类流量 | prefill/decode/symmetrical/bursty 全部入 ci | [#1661](https://github.com/llm-d/llm-d/pull/1661)+[#1700](https://github.com/llm-d/llm-d/pull/1700)+[#1586](https://github.com/llm-d/llm-d/pull/1586) |
| Higress MCP filter 内存退避 | 200 MiB 阈值强制 rebuild MCP filter VM | [higress#3922](https://github.com/alibaba/higress/pull/3922) |
| Higress WASM 重建触发器瘦身 | 删 request-count 触发器，**只留 memory-threshold** | [#3923](https://github.com/alibaba/higress/pull/3923) |
| agentgateway config 同步可观测 | `agentgateway_config_synchronized` gauge 0/1 | [agentgateway#2061](https://github.com/agentgateway/agentgateway/pull/2061) |
| Envoy AI GW token 配额全链路 | QuotaPolicy → xDS → ext_proc → RLS（**`HitsAddend = token count`**） | [ai-gateway#1869](https://github.com/envoyproxy/ai-gateway/pull/1869) |

## 1 · LiteLLM · 3 件 PR 把"单 worker RPS 上限"提升 25–50%

5 月底以来 LiteLLM 走"py-spy 找热帧 → 砍 import / 砍 `__setattr__` / 换序列化器"的同一模式。

### #29782 · orjson for `/v1/messages`（**+23% throughput, −20% p50**）
500K token / 500 turn Claude Code shaped 负载（mock Anthropic, single uvicorn worker）：throughput 68.5 → 84.6 RPS、p50 127 → 102 ms、event-loop freezes >50ms 不变（cold-start/inherent，非序列化）。orjson 在 1.9 MB body 0.11 ms vs stdlib 2.84 ms（约 25×）；orjson 是 proxy extra，`try/except` fallback。

### #29537 · per-request optional import cache（**+22% RPS**）
`/chat/completions` conc 1 RPS 190.5 → 233.2（**+22.4%**），overhead 5.25 → 4.28 ms（**−18.5%**）；conc 64 同样 +17–20%。py-spy `phase_span` 8.1% → 0.0%。Python 失败 import 不入 `sys.modules`，每次重跑 finder/loader。修法：第一次 import 解析 callables，失败用 disabled sentinel 永久缓存（**顺带修真 bug**：prisma 缺失时 `_is_exception_related_to_db` 在 exception handler 里 raise `ImportError` 把真实错误吞掉）。

### #29761 · pydantic Delta streaming path（**−79% µs/call**）
`Delta(content, role)` 12.50 → 2.67 µs/call；`Delta(content, role, tool_calls)` 14.08 → 4.39 µs/call。10 次 `__setattr__` + 5 次 `__delattr__`（pydantic `extra='allow'`）→ 一次 `parent init` 后直接写 `__pydantic_extra__` + `__pydantic_fields_set__`。**56-case golden snapshot + serialization contract test** 锁 byte-identical。**观察**：每 PR 3–5 文件、单一目标、内置 regression test、火焰图可重跑 —— **当一个 proxy 项目把"perf 门槛"做进 PR review checklist，RPS 上限就跟着改**。

## 2 · vLLM · 精度 / 量化 / 通信 / 基准方法学四条主线

### #44677 · DBO++: TP all-reduce overlap with compute（**PCIe > NVLink 收益**）
Qwen3-32B + TP=4 prefill：TP all-reduce 约占 **19%** latency，**−10.55% wall / +11.8% throughput**，AR **95.7%** hidden behind compute。nsys trace：
```
Without DBO: wall=1110ms  compute:[GEMM_0 AR_0 GEMM_1 AR_1 ...]  comm:unused
With DBO:    wall=1047ms  compute:[GEMM_0a GEMM_1a ... GEMM_0b ...]
                          comm:[AR_0a AR_1a ... AR_0b ... AR_Nb]
                          ↑ overlapped 95.7% with compute_stream
```
DBO = 2-thread-per-rank micro-batching：forward 沿 token 轴分 2 个 `UBatchSlice`，**同一 GPU、不同 CUDA stream**。**当 PCIe > NVLink 时 AR 通信成本更高，DBO 收益更大**（PR 明确写）。

### #43137 · `per_token_group_quant` 走 register（**+4.5% E2E**）
FP8 MoE (Qwen3-30B-A3B-Thinking-2507-FP8, TP=4 + EP)：baseline output 13849.18 tok/s、peak 14720、TTFT 116.68 ms、TPOT 8.98 ms、p99 ITL 12.85 ms。group=128 走 register bypass SMEM。

### #44708 · benchmark 方法学：**auto-detect tokenizer mismatch**
`vllm bench serve` client tokenizer ≠ server tokenizer 时，**输入 token 通胀 6×**（client transformers 5.9.0 DSv3.2 vs server ROCm aiter 内置）。baseline：benchmark 7.22s, output 138.59 tok/s, total 6563.52 tok/s, TTFT 918.93 ms —— **全部基于 inflated 46359 input tokens**。修法：probe `/tokenize` 第一个 prompt，不一致时 `WARNING: tokenizer mismatch (server=X, expected=Y), re-aligning prompts`。

## 3 · llm-d · 首份 PR-level bench report + 多 backend 对齐

### #1705 · predicted-latency-routing benchmarking templates
**第一份"PR 级别、含完整数字表、可复现"的 llm-d bench 报告**。`Qwen/Qwen3-32B`, 10 × vLLM decode pods (TP=2, 20 × H100), 131072 context：input throughput **+38.3%**, output throughput **+40.2%** vs 裸 k8s Service。代码变更：
- `benchmark-templates/run_benchmark.sh`：reusable orchestration（重启 EPP + per-run PVC + per-concurrency `inference-perf` Job + 早失败检测）
- `benchmark-templates/bench-job.yaml`：pinned `inference-perf:v0.5.0`
- 修复 `pluginsConfigFile` 路径 + `prefix-cache-scorer` 缩进 + 声明 `slo-headroom-tier-filter` plugin

**门禁陷阱**：`slo-headroom-tier-filter` 之前没声明 → plugin 静默不加载 → EPP router 配置"看起来对"实际不生效。**配置不报错是 router 项目的最大坑**。

### #1586 + #1700 + #1661 · WVA 4 类流量 + TPU V6 P/D
- WVA 4 类：prefill / decode / symmetrical / **bursty**（与生产 P99 关系最密切）
- TPU V6 P/D recipe + nightly benchmark 与 NVIDIA 主线 parity
- llm-d 正在把"benchmark = 一篇 PDF" 转为"benchmark = 每晚 regression test"

## 4 · Higress · MCP filter 内存退避 + WASM 重建触发器瘦身

### #3922 · MCP filter 200 MiB 重建阈值
`plugins/wasm-go/extensions/mcp-server` 加 max memory rebuild threshold，与 `ai-proxy` 对齐：**MCP filter VM memory > 200 MiB 触发 rebuild**。修 plugin OOM + `wasm.envoy.wasm.runtime.v8.active` 漂移。

### #3923 · 删 request-count 重建触发器
**删** request-count based 主动重建触发器，**保留** memory-threshold 重建触发器。在 #3920 调查 Envoy RSS 持续增长期间，稳态流量下避免 churn。**性能退避标准解法** = **先关多余开关 → 再加唯一触发器 → 监控中观察**。

## 5 · agentgateway · 配置同步可观测 + 出站调用时序直方图

### #2061 · `agentgateway_config_synchronized` gauge
0/1 gauge：`StateManager` 每次 config update 写入。PromQL `agentgateway_config_synchronized == 0` for 1m → page。合入前 reload 失败只能从 controller log 推断；合入后从 metric 直接查。配合 #2098 `agctl log` 子命令，运维形成 **gauge + agctl log + pprof** 三件套。

### #1784 · proxy timing measurements
`agentgateway_request_processing_seconds` histogram：label 维度 `backend` / `bind` / `gateway` / `listener` / `route` / `route_rule`，bucket 50µs / 100µs / 250µs / 500µs / 1ms / 2.5ms / 5ms / ...。**`MinimalHTTPLabels` 必须裁剪**避免 cardinality 爆炸。

## 6 · Envoy AI Gateway · QuotaPolicy + token 配额同链路

### #1869 · QuotaPolicy 注入后端配额限流 filter
end-to-end data flow：
```
User creates QuotaPolicy CR → Controller / translator.BuildRateLimitConfigs()
  → RateLimitConfig protobuf → runner.UpdateConfigs() → xDS snapshot
  → rate limit service (gRPC) → Extension Server injects filter + actions
Request → Envoy → request-time RLS check (无配额 429)
  → ext_proc extracts token usage
  → stream-done action: RLS HitsAddend = token count
  → rate limit service increments Redis counter by token count
```
**核心创新**：**「token 用量」直接喂回 RLS 当 counter**。`QuotaPolicy { rpm: 100, tpm: 1M, monthly_tokens: 10M }` 同一 RLS 同时 enforce —— **不需要单独 budget service**。传统 API gateway `rate_limit { rpm: 100 }` 只能 RPM 限流，月度 token budget 需要 clickhouse 聚合（6h+ 延迟）。

## 7 · 5 个反常识

| 反常识 | 来源 |
| --- | --- |
| 通信-计算 overlap 收益在 **PCIe > NVLink** | vLLM #44677 |
| token quota 可以走同一条限流链路 | Envoy AI GW #1869 |
| tokenizer 不一致让 benchmark 通胀 **6×** | vLLM #44708 |
| 删 request-count 重建触发器是性能优化 | Higress #3923 |
| GPU TPU parity 是路由算法在两栈都能落地的必要前提 | llm-d #1700 |

## 8 · AIGW 落点（累加 91 条，新增 5 条）

**#87** · proxy 内部序列化统一走 orjson（或 simdjson），不强制 base dep，`try/except` fallback；
**#88** · optional import 一次解析 + 永久 cache（sentinel 模式），prisma / OTel 等可选依赖全部走此模式；
**#89** · pydantic 大量 `setattr/delattr` 路径改"一次 init + 直写 `__pydantic_extra__`"，**必须有 golden snapshot 锁 byte-equality**；
**#90** · benchmark 工具必须 probe server `/tokenize` 自动对齐 client/server tokenizer，**否则数字不可信**；
**#91** · request-count based 主动重建触发器是反模式（Higress 实证），**只保留 memory-threshold**。

## 引用与数据来源

- LiteLLM PR 29782（orjson for /v1/messages）：https://github.com/BerriAI/litellm/pull/29782
- LiteLLM PR 29537（per-request optional import cache）：https://github.com/BerriAI/litellm/pull/29537
- LiteLLM PR 29761（streaming Delta 直接构造）：https://github.com/BerriAI/litellm/pull/29761
- vLLM PR 43137（per_token_group_quant 走 register, +4.5% E2E）：https://github.com/vllm-project/vllm/pull/43137
- vLLM PR 44677（DBO++ TP AR overlap compute, −10.55% wall）：https://github.com/vllm-project/vllm/pull/44677
- vLLM PR 44708（auto-detect tokenizer mismatch）：https://github.com/vllm-project/vllm/pull/44708
- llm-d PR 1705（predicted-latency-routing benchmarking + +40.2% output）：https://github.com/llm-d/llm-d/pull/1705
- llm-d PR 1586（WVA benchmark data）：https://github.com/llm-d/llm-d/pull/1586
- llm-d PR 1661（TPU V6 Recipe for P/D）：https://github.com/llm-d/llm-d/pull/1661
- llm-d PR 1700（TPU nightly benchmark）：https://github.com/llm-d/llm-d/pull/1700
- Higress PR 3922（MCP filter 200 MiB rebuild 阈值）：https://github.com/alibaba/higress/pull/3922
- Higress PR 3923（删 request-count 重建触发器）：https://github.com/alibaba/higress/pull/3923
- agentgateway PR 2061（config_synchronized gauge）：https://github.com/agentgateway/agentgateway/pull/2061
- agentgateway PR 1784（proxy timing measurements histogram）：https://github.com/agentgateway/agentgateway/pull/1784
- Envoy AI Gateway PR 1869（QuotaPolicy token RLS 全链路）：https://github.com/envoyproxy/ai-gateway/pull/1869
- Envoy AI Gateway PR 1709（QuotaPolicy 关联）：https://github.com/envoyproxy/ai-gateway/pull/1709
