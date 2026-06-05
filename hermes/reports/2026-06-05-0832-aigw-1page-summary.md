# AI Gateway 调研 · 1 页纸全景图（小B产品视角）

> **整理时间**：2026-06-05 08:32 CST
> **范围**：本仓库 13 份 hermes 自动化报告 + 30 份 openclaw 主题/产品深挖（共 40+ 份原始报告）
> **目的**：给「小B商户数字化」这条产品线挑可借鉴的 AI 网关技术 + 找商业机会

---

## 一、行业一句话

**AI 网关从"LLM 路由器"长成了"Agent + MCP + LLM 三件套"**——2025-2026 是分水岭。整合潮开始：Palo Alto 收 Portkey、Mintlify 收 Helicone、agentgateway 进 AAIF（Linux Foundation 旗下）。

对小B的信号：**企业市场是 SaaS + 自托管双轨**，**国内 Higress 凭完整 AI 插件矩阵 + 中文 + 商业支持是事实标准**。

---

## 二、10 大产品定位速查

| 产品 | 形态 | 杀手锏 | 对小B的可用度 |
|---|---|---|---|
| **Higress** (阿里) | 开源 + 商业 | 国内最全 AI 插件矩阵（含 RAG/Agent/Token 限流/MCP 桥接/本体论） | ⭐⭐⭐⭐⭐ 直接对标 |
| **LiteLLM** | 开源 Python | 100+ 厂商 + MCP + Agent 三合一网关，2 天一 release | ⭐⭐⭐⭐ 工具/脚本型集成 |
| **Envoy AI GW** | K8s CRD | CNCF 嫡系 + v0.6.0 首标 production-ready + `MCPRoute` v1beta1 | ⭐⭐⭐ 自建 K8s 才用 |
| **OpenRouter** | SaaS | 100T token/月 + 8M 用户 + `provider.sort` (Price/Throughput/Latency) + ZDR | ⭐⭐⭐⭐⭐ 多模型路由现成用 |
| **Portkey** (被 PANW 收) | 商业 + 开源 | 50+ Guardrails + Skills Registry + MCP Governance | ⭐⭐⭐ 治理场景用 |
| **Helicone AI GW** (被 Mintlify 收) | 开源 Rust | "最快最轻最易集成" 594★ | ⭐⭐⭐⭐ 边缘/小流量 |
| **Kong AI GW** | 商业 + 开源 | 把传统 API 网关经验搬进 AI，对 Kong 老客户友好 | ⭐⭐⭐ |
| **Cloudflare AI GW** | SaaS | 全计划免费 + 边缘 + GraphQL Analytics | ⭐⭐⭐⭐⭐ 个人/小团队零运维 |
| **One API / New API** | 开源 (国内) | 聚合 LLM API，国内小工作室标配 | ⭐⭐⭐⭐ 国内基础款 |
| **kgateway** | 开源 | Envoy GW 包装，CVE 响应最快（24h） | ⭐⭐ K8s 专业用户 |

**推理引擎侧**（vLLM / SGLang / TGI）也都产了深挖——结论：vLLM 是社区事实标准（生产 P50 最低延迟），SGLang 在结构化输出/多模态更优，TGI 是 HuggingFace 生态默认。

---

## 三、6 大技术趋势（按对小B的相关性排）

| # | 趋势 | 对小B产品的意义 |
|---|---|---|
| **1** | **MCP Gateway 化** | 小B商户的"工具"（POS、库存、ERP、IM）天然就是 MCP server；接 AI 网关 = 一行配置就接入 Agent；**这就是 2-3 年内 SaaS 标配** |
| **2** | **Agent Gateway 独立品类** | 多步 agent 跑完"15 个 200" ≠ 业务成功；Portkey 案例：单看 LLM 调用不顶用，要 trace + 成本归因到 agent run |
| **3** | **语义路由 / 价格仲裁** | OpenRouter `sort=Price` + `zdr=true` 把"挑模型"做成 API 参数；小B最直接收益：**用 DeepSeek 干 80% 活，关键步骤上 Claude** |
| **4** | **Guardrails 内置** | 不再外挂审核服务；**Prompt 注入 / PII / 内容审计 / 零留存**四层独立热插拔——小B客服场景刚需 |
| **5** | **可观测标准化 (OTel GenAI semconv)** | OTel 把 GenAI 属性拆出独立仓，5-05 起 4 个 spec-level PR 并入；统一 trace 跨厂商 LLM |
| **6** | **WASM 沙箱取代原生指令配置** | Higress v2.2.2 用 WASM 沙箱绕开 Nginx 18 年老洞 (CVE-2026-42945 CVSS 9.2)；未来扩展点 |

---

## 四、最近一周必须知道的 5 个硬事件

1. **CVE-2026-47774** (CVSS 7.5) — Envoy HTTP/2 HPACK 放大 DoS，3GB 内存几分钟 OOM。**kgateway 24h 修，Envoy AI GW 等 v0.6.1**。**自建 K8s + Envoy 1.37.0-1.37.2 的本周内必升**。

2. **CVE-2026-42945** (CVSS 9.2 CRITICAL) — Nginx 18 年 `rewrite+set` 堆溢出。Higress 用 **WASM 沙箱** 绕开（首例工业界落地）。

3. **agentgateway 加入 AAIF** (2026-06-04) — Linux Foundation 第 4 个 hosted 项目，**A2A + MCP + GIE InferencePool 三件套 = multi-agent 协议事实标准**。

4. **Helicone 被 Mintlify 收购** (2026-03-03, 14.2T token / 16k 组织) — LLM 可观测赛道整合；Helicone 保留开源转 AI GW（Rust, 594★）。

5. **OTel GenAI semantic conventions 独立成仓** (2026-05-05) — 4 个 spec-level PR 同日合并：MCP context propagation (SEP-414) / span duration 含 retries / `top_k` 拆 retrieval / `provider.name` 降 Recommended。

---

## 五、架构 & 性能一张表

| 产品 | 数据面 | RPS/单核 | MCP | Wasm | CVE 响应 | 冷启动 |
|---|---|---|---|---|---|---|
| Envoy AI GW | Envoy + ext-proc | 30-50 万 | ✅ v1beta1 | ✅ | 周级（依赖上游） | 中 |
| Higress | Envoy fork + Wasm | 30-50 万 | ✅ Mcp Bridge | ✅ 一等公民 | 自维护 | 中 |
| kgateway | Envoy (via Envoy GW) | 30-50 万 | ❌ | ⚠️ 手写 | **24h** | 中 |
| LiteLLM | Python asyncio | 200-800 | ⚠️ v1.88 计划 | ❌ | Python 生态 | 极快 |
| Portkey | Node.js | 1k-3k | ✅ | ❌ | Node 生态 | 极快 |

**1000x 差距 = 选型分水岭**：要百万 RPS 走 Envoy 系；要"应用层 SDK 网关"（快速集成、25+ 模型、Guardrails 编排）走 LiteLLM/Portkey。

---

## 六、对「小B行业软件」副线的 5 个直接启发

> 小F 的目标市场：5-15 万/年 SaaS，**数字化转型痛点 + 轻硬件**。AI 网关行业这几条趋势直接对应可落地的产品方向：

### 启发 1：**MCP 工具网关 = 中小商户的"AI 工具总线"** ⭐⭐⭐⭐⭐
- 小B 商户有 POS/库存/CRM/小程序一堆工具
- 现在每个 AI Agent 都要自己接一遍
- **做个"垂直版 MCP Gateway"**：把通用 SaaS 工具（企业微信/钉钉/飞书/有赞/微店/抖店/美团商家）包装成 MCP server，按商户数量收费
- 对标：Portkey Skills Registry / TrueFoundry Prompt Management
- 切入点：**先用 Higress / mcp-context-forge 的开源底座改造**，节省 6 个月从零

### 启发 2：**"用 AI 网关做模型路由" = 中小商户"用得起 AI"** ⭐⭐⭐⭐⭐
- OpenRouter `sort=Price` + Envoy v0.6.0 `reasoning_effort` 统一旋钮
- 中小商户不需要"最聪明"，需要"够用 + 便宜 + 不上传数据"
- **小B 套餐设计**：基础套餐用 DeepSeek/Qwen（国产 + 便宜），高级套餐才上 Claude/GPT
- 套 OpenRouter 或自建 Envoy AI GW 都能实现

### 启发 3：**Guardrails-as-a-Service 卖给合规敏感行业** ⭐⭐⭐⭐
- 教育/医疗/法律/金融小B最怕的是 prompt 注入和 PII 泄露
- Portkey 50+ Guardrails 是现成产品形态
- **国内做：GLiNER（开源 PII 替换）+ NeMo Guardrails（NVIDIA 开源）= 4 象限方案**
- 切行业：教育行业"必须本地化"、医疗"必须 PII 脱敏"

### 启发 4：**Agent 可观测 = 小B版的"业务大盘"** ⭐⭐⭐
- 传统 LLM 监控看"调用 200"对商户无意义
- 小B要看的是："AI 客服今天自动处理了多少单、退款率、人工接管率"
- 套 Langfuse / Phoenix v17 admin ceiling policy（OSS LLM 可观测里第一条 server-enforced 录制策略）
- 卖点：**不是给开发者看，是给老板看**

### 启发 5：**走国内 Higress 路线 = 借阿里云商业化渠道** ⭐⭐⭐⭐
- Higress 是国内唯一"完整 API 网关 + 完整 AI 网关 + 完整中文 + 商业支持"
- 在它上面做插件 / SaaS = 直接吃阿里云生态
- **潜在路径：给 Higress 贡献"小B 行业插件包"（餐饮/零售/教培）→ 阿里云市场分销**

---

## 七、3 个明确"不要做"

1. **不要做通用 AI 网关** — Portkey/Helicone/LiteLLM/OpenRouter 已经红海，且 2025 行业整合潮开始
2. **不要做新推理引擎** — vLLM/SGLang/TGI 三足鼎立，NVIDIA Dynamo + SGLang 合并趋势明显
3. **不要做"小B 自建 K8s 部署版 AI 网关"** — kgateway/Envoy AI GW 路线需要 K8s 团队，小B 养不起

---

## 八、推荐下一步（动作清单）

| 优先级 | 动作 | 产出 |
|---|---|---|
| P0 | 读 `2026-06-05-0306-aigw-semantic-routing-cost.md` 全文 + `2026-06-05-0146-aigw-mcp-gateway-products.md` 全文 | 确认 MCP 工具网关方向 |
| P0 | 起一个 PoC：Higress 装本地 → 把企业微信/有赞 API 包成 MCP server → 用 Claude Desktop / Cursor 调通 | 1 周出 demo |
| P1 | 调研小B 3 个垂直（教培/口腔诊所/连锁餐饮）的 MCP 工具清单 | 1 份 GTM 文档 |
| P1 | 竞品分析：国内"小B 工具 AI 化"赛道（用友/金蝶/微盟/有赞）最新动作 | 1 份竞品矩阵 |
| P2 | 评估 TrueFoundry 模式（拆成 4 个独立产品：AI GW / MCP GW / Agent GW / Skills Registry）作为小B 套餐结构 | 1 份产品分级方案 |

---

## 附录：仓库报告索引

- **13 份 hermes 自动化报告**：`hermes/reports/2026-06-04-aigw-market-overview.md` 起的所有 .md
- **20 系列主题深挖**：`openclaw/01-llm-protocols.md` ~ `20-future-2027-2030.md`
- **10 份产品深挖**：`openclaw/product-{litellm,portkey,envoy-ai-gateway,higress,vllm,sglang,tgi,apisix-ai-proxy,kong-ai-gateway,one-api}-20260605.md`
- **变更日志**：`hermes/CHANGELOG.md`

**报告全部本地 + 推送 GitHub 成功**（`origin/main` clean）。
