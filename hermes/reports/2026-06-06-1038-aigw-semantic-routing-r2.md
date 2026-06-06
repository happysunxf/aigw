# AI 网关持续深挖 · 第 N 次 — 语义路由/成本优化(第 6 视角:工业路由器 0.3 时代「合法性 + 冲突解决 + 缓存分层」)

- 轮值时间(本地): 2026-06-06 10:38 CST(Saturday)
- 主题: 语义路由/成本优化(hour % 7 = 3)
- 角度: 前 5 次覆盖 — 跨厂商 schema / 路由 RCE / 成本归因+投机 / vLLM SR Themis / router 算法内核+语义缓存工业切片。本次 **第 6 视角「工业路由器 0.3 时代」**:从「算法内核」移到「路由器达到体量后绕不开的三件事」—— **(1) 模型选型『合法性 / 合规性』层、(2) DSL 表达力与『冲突解决』、(3) 缓存分层(冷热+隐私分级)**。三件事都来自 vllm-sr v0.3.0(06-05 12:08 UTC)同日密集 PR 群。
- 抓取窗口: 2026-05-30 ~ 2026-06-06 10:38 CST

---

## 1. 一句话结论

「**vLLM Semantic Router v0.3.0(2026-06-05)把『路由器』从『选得快』推进到『选得合法 / 选得不冲突 / 选得不泄密』:PRISM 153-key 合法性层 + DSL 冲突检测 + Redis 热缓存 + 隐私路由配方 + entropy 多域判定;同期 Envoy AI GW 推出 QuotaPolicy-aware 路由,LiteLLM 1.87.1 backport session-token budget-ceiling exemption,Portkey 1.15.2 之后主线动作稀少。**」

近 3 天最硬 5 信号:
1. **vllm-sr v0.3.0(06-05 12:08 UTC)** —— PRISM 白皮书 + entropy 多域 + DSL SIGNAL_GROUP/TIER/冲突检测 + Redis hot cache + 隐私 routing 配方 + extproc sjson/gjson 性能优化。单 release 70+ PR,6 个 GHCR 镜像 + Helm 0.3.0 同步 tag。
2. **Envoy AI GW #1869(06-04)** —— QuotaPolicy-aware routing:`QuotaPolicy` → RLS descriptor tree,ext_proc 在 stream-done 把 `HitsAddend = token count` 推回 RLS,「先看配额再看模型」落地。
3. **LiteLLM v1.87.1(06-04) + 1.88.0-rc.3(06-05)** —— 1.87.1 = 5 项 backport;**#29612 session-token budget-ceiling exemption** 稳定版出现在 1.87.x(1.87.2 短暂后 revert),「单 session 豁免月度 budget ceiling」治理路径。
4. **LMCache 8 commit / 3 天(06-05~06-06)** —— `#3521` 混合分配器支持「不同 group 不同 block size」(异构 GPU 池)+ `#3528` server_bench `--mode cpu` + `#3531` create_cache_context factory —— LMCache 把自己做成「跨 vLLM 版本 / 跨硬件的 KV-cache 路由器」。
5. **ModelEngine-Group/unified-cache-management(华为)** —— `#994` 恢复 Ascend PC e2e gate(昇腾 NPU KV-cache 端到端门禁),`#960` layerwise & pipeline store metrics —— 昇腾端 KV-cache 治理进入 GA 前修尾。

---

## 2. 硬数据

### 2.1 vLLM Semantic Router v0.3.0(06-05 12:08 UTC)—— Themis 之后工业三件套

**A. PRISM — 153-key 合法性层(`#1563`,Mossaab-s)**—— documentation only。
- **三层合法性**:Key 1 QUALIFICATION(async auto-discovery at startup)/ Key 2 CLASSIFICATION(in-process `candle-binding` embedding,不发外部调用)/ Key 3 EXECUTION(legitimacy validation 沿用 `req_filter_jailbreak` 模式)。
- **153-Registry** —— in-memory store + empirical scoring(过去 N 次实际表现)。
- **Re-route loop** —— **不动** `selectModelFromCandidates`(向后兼容)。
- 意义:**从「我能路由到 X」到「我应该路由到 X」**。Martian / NotDiamond 有「模型可用性」白名单,但「模型合不合法 / 是否被审计 / 是否在某地区被禁」这套 153-key 工程化 spec,目前仅 vllm-sr。

**B. entropy-based multi-category domain matching(`#1497`,06-03)**—— 之前 `domain signal` 永远返回 top-1。现在:ModernBERT 给概率 → Shannon 熵 → 低熵 top-1 / 高熵多 category(AND 跨域);BERT-base / mmBERT-32K 不给概率 → fallback。新增 `/api/v1/eval` 字段 `signal_confidences`。6 Ginkgo spec。附 bugfix:`computer_science` vs `computer science` MMLU 标签对齐。配套 revert:`#1572 UseModernBERT` 在 `#1532` 后被 `#1561` revert(`#1574` 修 candle FFI softmax,下一轮再合)。

**C. DSL 表达力(`#1588`,rootfs)** —— `SIGNAL_GROUP`(同类信号打包)+ `TEST 块`(DSL 内部单测)+ `TIER routing`(0/1/2/3 tier:白名单/默认/降级/fallback)+ **冲突检测**(规则互斥时解析期报错,不运行时随机挑)。

**D. conflict-free routing workstream(`#1620`,Xunzhuo,06-05)**—— 重命名 post-signal 路由契约为 `routing.projections`;新增 `projections.scores` + `projections.mappings`,decisions 可用 `type: projection` 消费;maintained `balance` recipe 重构为 learned + heuristic + partitioned 三策略。5 道门禁:`dashboard-check` / `agent-lint` / `agent-ci-gate` / `agent-feature-gate` / `agent-validate`。

**E. Redis hot cache layer(`#1423`,liavweiss,06-04)**—— Milvus 之前叠 Redis。read-through + per-user 失效,key = `user_id + query + project_id + limit + threshold + types`,TTL + key prefix 可配;hit/miss/latency 指标。**「hot query 不再走向量库」** 是 demo 与 production 的硬分水岭(Redis < 1ms vs Milvus 5-30ms)。

**F. 隐私路由配方(`#1635`,Xunzhuo,06-05)**—— `deploy/recipes/privacy/` 4 文件(YAML + DSL + probe manifest + README)。**隐私敏感 / 可疑 query → 低成本本地 lane;非敏感 / 深度推理 → 高成本 frontier lane**。16/16 probes pass(2026-03-23)。**AIGW 角度**:对应「敏感数据不出域」硬要求,部署可照搬 4 文件。

**G. ext_proc 性能**:`#1585` `sjson` 替代 encoding/json(request body rewrite)、`#1614` `gjson` 替代 encoding/json(response body 提取)—— p99 latency 直接受益。

**H. 其他 06-04~06-05 配套**:`#1502` skip cache for personalized / `#1558` per-decision cache opt-out / `#1627` OpenClaw VSR install bridge / `#1583` 拆 `vllm-sr-sim v0.1.0` 独立发版。

### 2.2 Envoy AI Gateway #1869 —— QuotaPolicy-aware routing(06-04)

端到端:User creates QuotaPolicy CR → Controller → `translator.BuildRateLimitConfigs()` → RateLimitConfig protobuf → `runner.UpdateConfigs()` → xDS snapshot 推 RLS(Redis)→ Extension Server 注入 filter + actions → Envoy request-time 限流(无配额 429)→ ext_proc 抽 token usage → stream-done `HitsAddend = token count` 推回 RLS → Redis counter 累加。**「token 用量」直接喂回 RLS 当 counter** —— 月度「1000 万 token」按量 quota 与 RPM 限流同一个 RLS,不需要单独 budget service。同期:#2023 /v1/audio/* 端点、#2122 Azure OpenAI Responses API、#2052/#2144 OAuth 2.0 Token Exchange + MCPBackend CRD proposal。

### 2.3 LiteLLM v1.87.x(06-04)—— session-token budget-ceiling exemption 落地

- **1.87.1**(06-04):5 项 backport,cut by `mateo-berri`(#29631)。
- **#29612 实质**:**会话级 token 预算可豁免 budget ceiling**。企业场景:team 月度 budget 100M 用完,但单 session 因流式 tool-call 长链路需继续执行不被打断 → 该 session 通过 exemption 通过 budget check。
- 06-05~06-06 commits:#29820 修 team BYOK model 悬挂、#29714 MCP playground auth 改 `oauth2` mode、#28370 `you_com` search provider、#29779 cohere v2 chat 支持 `max_completion_tokens`。
- **1.88.0-rc.3**(06-05):目前 3 个 rc,等 stable cut。

### 2.4 LMCache 06-04~06-06 —— 跨硬件 KV-cache 路由器

- `#3521` [Hybrid allocator] 不同 group 不同 block size(06-05)—— 异构 GPU 池 / 异构 KV layout 的核心 PR,**LMCache 同时管 H100 + L40S / 不同 head 配置的 KV 池**。
- `#3528` server_bench `--mode cpu` + `--transfer-mode`(06-05)—— CPU↔GPU transfer benchmark。
- `#3531` create_cache_context factory 重构 mp 路径(06-06)。
- `#3524` non-GPU path transfer timing logs(与 CUDA path 对齐)/ `#3507` c_ops vs python_ops_fallback parity test / `#3522` coordinator CLI + mp server registration(多 server 协调)。

**AIGW 角度**:**LMCache 正在从「vLLM 内部 KV-cache 复用」长成「跨 vLLM / SGLang / TensorRT-LLM 的 KV-cache 路由器」**。

### 2.5 ModelEngine-Group/unified-cache-management(华为)—— 昇腾端 KV-cache 治理

- `#994` 恢复 Ascend PC e2e gate(06-05)—— 昇腾 NPU KV-cache 端到端测试门禁恢复,**「华为 + 昇腾」进入商用窗口**。
- `#960` layerwise & pipeline store metrics(06-01)/ `#983/#986` 修 FAWA HMA dump handling(05-30)/ `#985` 优化 MLA TP dump balance(05-26)。

### 2.6 Portkey / Helicone / Kong —— 主线动作稀少

- **Portkey**(1.15.2 之后 5 月无主线动作,5 个最近 commit 全是 05-19~05-25 的 auth 修补)—— **主线可能从「gateway-first」转向「observability-first」或企业版 BaaS**。
- **Helicone**:05-18 修 bifrost build / Supabase Node 20 / AWS 事件 banner 撤掉。
- **Kong**:3.9.2(06-04)发版,主版本线无新东西。

---

## 3. 信号归纳

### 3.1 「路由器 0.3 时代」三件套

| 维度 | 过去(算法内核) | 现在(0.3 时代) | 谁在做 |
|---|---|---|---|
| 模型选型 | 「我能路由到 X」 | 「我应该路由到 X」legitimacy/compliance/audit | **vllm-sr PRISM 153-key** |
| 规则表达 | flat SIGNAL + 表达式 | SIGNAL_GROUP + TEST + TIER + 冲突检测 | **vllm-sr `#1588`/`#1620`** |
| 缓存分层 | 单一向量库 | Milvus(冷)+ Redis(热)+ per-decision opt-out + 个性化 skip | **vllm-sr `#1423`/`#1502`/`#1558`** |
| 配额感知 | 月度 budget / RPM | 配额耗尽仍允许单 session 豁免 + token 实时回写 RLS | **LiteLLM `#29612` + Envoy `#1869`** |
| 隐私分级 | 不分,统一出公网 | 敏感 → 本地 lane;非敏感 → frontier lane | **vllm-sr `#1635`** |
| 域判定 | 单 top-1 | entropy-based 多 category(AND 跨域) | **vllm-sr `#1497`** |

### 3.2 「路由器与 LLM 推理栈」边界模糊化

- **vllm-sr** = Envoy ext_proc + candle 路由推理 + Milvus/Redis 缓存 + DSL —— 路由器正在变成「带 LLM 推理能力的 sidecar」。
- **LMCache** = 跨 vLLM 版本的 KV-cache 路由 —— 缓存层正在变成「跨推理引擎的路由器」。
- **Envoy AI GW** = Gateway API + ext_proc + RLS 集成 —— Service Mesh 把 AI 用例作为「一等工作负载」。
- 三层都向「router + classifier + cache + policy」四件套收敛,**未来 12 个月最可能看到「vllm-sr + LMCache + Envoy」三选一打包**(类似「Istio + Envoy + Prometheus」当年的组合)。

### 3.3 Portkey / Helicone 静止的原因(推测)

- 商业化产品「开源仓库」节奏放缓 ≠ 产品停更。Portkey / Helicone 可能把新工作放在 closed-source enterprise SKU。Portkey 在 2026 H1 可能从「gateway-first」转向「observability-first」。

---

## 4. AIGW(内部 AI 网关)落点 —— 10 条硬要求增量

(沿用 05-31 起每轮累加的 10 条硬要求清单,本次增量 5 条 → 累加 80 条)

**76.** **PRISM 153-key 合法性层** —— 内部路由决策前增加 legitimacy check 层(模型是否被 deprecate / 是否在某地区被禁 / 是否被审计拒绝),实现 QUALIFICATION/CLASSIFICATION/EXECUTION 三段,153-Registry 用 in-memory store 暂存。

**77.** **entropy-based 多域判定** —— 内部 domain classifier 替换为 ModernBERT + Shannon 熵(高熵多 category 同时返回,AND 跨域);低概率后端(BERT-base)保留 fallback。

**78.** **DSL 冲突检测** —— 内部 routing DSL 增加 `SIGNAL_GROUP` / `TIER` / `TEST` 块 + 解析期冲突检测(规则互斥时编译期报错),不依赖运行时随机选一条。

**79.** **Redis hot cache 在 Milvus 之前** —— 内部 memory retrieval 加 Redis 缓存层(1ms 级),per-user 失效,key = `user_id + query + project_id + limit + threshold + types`,TTL 可配。

**80.** **个人化响应 skip cache** —— 内部 semantic cache 写入前判断「response 是否含 personalization 标记」(user-specific data / tool result / time-sensitive info),命中则强制 opt-out。

---

## 5. 待办 / 后续观察

- vllm-sr v0.3.1 / v0.4:`conflict-free routing` 完整落地 + `routing.projections` DSL 完整 + ModernBERT candle FFI 软最大值 PR `#1574` 何时合入(`#1572` 已 revert)。
- Envoy AI GW QuotaPolicy v1:等 #1869 后续 PR(回写路径 + HitsAddend 验证 + 与 token budget service 的统一 RLS schema)。
- LiteLLM 1.88.0 stable:关注 stable cut 时间,`session-token budget-ceiling exemption` 何时在 mainline 出现(目前仅 1.87.x backport)。
- LMCache 异构 block size(`#3521`)的 benchmark 实测数据(目前只有 `#3528` server_bench 工具,实测报告待出)。
- ModelEngine-Group 昇腾 NPU e2e gate 通过的 PR(目前 `#994` 是「恢复」,等待正式通过)。
- 隐私 routing recipe 的 `POST /config/deploy` → `PUT /config/classification` 二次刷新 —— 内部部署时记得同步。

---

## 引用与数据来源

- vllm-sr v0.3.0 release:`https://github.com/vllm-project/semantic-router/releases/tag/v0.3.0`
- PRISM 153-key whitepaper PDF:`https://github.com/user-attachments/files/25750911/PRISM-Vllm-SR-whitepaper-COMPLET-EN.pdf`
- vllm-sr PR #1497/#1588/#1620/#1423/#1635/#1585/#1614/#1558/#1502/#1627/#1583/#1574/#1563:`https://github.com/vllm-project/semantic-router/pull/<num>`
- Envoy AI GW PR #1869/#2144/#2023/#2122/#2052:`https://github.com/envoyproxy/ai-gateway/pull/<num>`
- LiteLLM v1.87.1 release:`https://github.com/BerriAI/litellm/releases/tag/v1.87.1`
- LiteLLM #29612:`https://github.com/BerriAI/litellm/pull/29612`
- LiteLLM v1.88.0-rc.3:`https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3`
- LMCache PR #3531/#3521/#3528/#3524/#3507/#3522:`https://github.com/LMCache/LMCache/pull/<num>`
- ModelEngine-Group PR #994/#960/#983/#985/#986:`https://github.com/ModelEngine-Group/unified-cache-management/pull/<num>`
- Portkey gateway:`https://github.com/Portkey-AI/gateway`
- Helicone repo:`https://github.com/Helicone/helicone`
- 上一轮(router 算法内核+语义缓存):`hermes/reports/2026-06-06-0328-aigw-semantic-routing-algorithms-cache.md`
- 上一轮(vllm-sr Themis):`hermes/reports/2026-05-31-1528-aigw-semantic-routing-vllm-themis.md`
