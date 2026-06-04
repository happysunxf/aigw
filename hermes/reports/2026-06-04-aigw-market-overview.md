# AI Gateway 2025–2026 最新技术进展调研报告

> **数据采集时间**：2026 年 6 月初  
> **方法**：直接抓取各产品官网、文档站、GitHub releases/Bing 搜索结果，交叉验证  
> **覆盖范围**：开源 + 商业，海外 + 国内，共 8 款主流产品

---

## 一、市场一句话总结

**AI 网关从"LLM 路由器"演化成了"AI 智能体基础设施"——同时承担模型路由、Agent 编排、MCP 治理、Guardrails、可观测四件事。** 2025 年最显眼的趋势是 **"Agent Gateway" 和 "MCP Gateway" 成为独立品类**（不再只是 LLM proxy）。同时行业开始整合：Palo Alto Networks 收购 Portkey、Mintlify 收购 Helicone——头部 AI 网关正被传统安全/文档巨头收编。

---

## 二、主流产品 2025-2026 最新动态

### 1. Portkey（被 Palo Alto Networks 收购）

- **收购**：2026 年 Palo Alto Networks 完成了对 Portkey 的收购（首页公告："Palo Alto Networks has completed the acquisition of Portkey"），定位是 AI 治理 + 安全层
- **仓库热度**：GitHub `Portkey-AI/gateway`：**11,968 stars / 1,104 forks**，TypeScript 实现，MIT 协议，最新 commit 2026-06-04
- **官方定位**："blazing fast AI Gateway with integrated guardrails"，**1,600+ LLMs、50+ AI Guardrails**
- **2026 年 4-5 月新动作**：
  - **Agent Gateway** 独立产品线：治理、可观测、控制 AI agent
  - **Skills Registry**（4-23 推出）：管理 agent 可调用的工具/技能清单
  - **MCP Governance 博客**（5-24）："53% of MCP servers use static API keys"——MCP 安全是个被低估的问题
- **典型痛点描述**（来自其博客 5-3 "What's an agent gateway"）："A 12-step agent run produces the wrong answer. You open the logs and find fifteen 200s. Every individual call succeeded."——单个调用成功 ≠ agent 业务成功

### 2. Helicone（被 Mintlify 收购 → 转型开源 AI Gateway）

- **收购**：2026-03-03 "After three years and 14.2 trillion tokens, Helicone has been acquired by Mintlify"（Helicone blog 公告）
- **新定位**：之前是 LLM 可观测平台，现在演化为 **AI Gateway**——独立开源仓库 `Helicone/ai-gateway` 出现
- **仓库热度**：GitHub `Helicone/ai-gateway`：**594 stars**，**Rust 实现**，GPL-3.0 协议，slogan 是"**the fastest, lightest, and easiest-to-integrate AI gateway on the market. Fully open-sourced**"
- **能力**：100+ AI 模型、OpenAI 兼容、智能路由、自动 fallback、Claude Sonnet 4/4.5 默认 1M 上下文
- **意义**：收购后保留开源路线，专做"轻量"和"快"——和 Portkey 的"治理重"形成对比

### 3. LiteLLM（最活跃的开源 LLM 路由）

- **版本节奏**：2026 年 5-31 发布 `v1.88.0-rc.1`，6-04 还在出 `v1.86.3 / v1.85.4 / v1.84.5` patch——**基本每两天一个 release**
- **官方定位**（来自 docs llms.txt）："deploy and validate the **LLM, MCP, and Agent gateway**"——明确三合一
- **支持**：100+ LLM 供应商、OpenAI 输入/输出格式转换、retry/fallback、batches、embeddings、images、audio
- **新发布 v1.87.0**：OCI Generative AI 接入
- **企业版**：自托管 + 商业支持双轨

### 4. Envoy AI Gateway（Solo.io + CNCF 生态）

- **版本**：v0.6.0（2026-05-05 GA）、v0.5.0（2026-01-23）、v0.4.0（2025-11-08）——**半年内跨两个大版本**
- **技术栈**：基于 Envoy Proxy + Envoy Gateway，主打 **eBPF/Envoy 生态、k8s-native**
- **2025 关键里程碑**（来自官方 blog 标题）：
  1. **MCP Support**（"Announcing Model Context Protocol Support in Envoy AI Gateway"）
  2. **OpenTelemetry Tracing**（"Enhancing AI Gateway Observability - OpenTelemetry Tracing Arrives"）
  3. **Endpoint Picker Support**（多 endpoint 智能选择）
  4. **Control Plane Benchmarking**（"Benchmarking Envoy AI Gateway Control Plane Scaling"）
  5. **Reference Architecture** for adopters
- **社区**：周会、Slack、GitHub Discussions 齐全，CNCF 风格

### 5. Kong AI Gateway（API 网关巨头的 AI 化）

- **官方定位**："Connectivity and **governance layer** for modern AI-native applications built on top of Kong Gateway"——强调 governance
- **场景描述**："applications are evolving beyond basic LLM calls into **complex, multi-actor systems—including user apps, agents, orchestration layers, and context servers**"——直白说出"AI 网关 = 多角色编排"
- **支持**：on-prem + Konnect SaaS 部署双轨
- **差异化**：把传统 API 网关的"限流/认证/审计"经验直接搬到 AI 场景，**对已有 Kong 客户友好**

### 6. Cloudflare AI Gateway（边缘 AI 网关的标杆）

- **定价**："Available on **all plans**"——免费层就可用，靠 Cloudflare Workers/网络效应
- **核心能力**（来自官方文档）：可观测（requests / tokens / errors / cost 仪表盘）、缓存、**Rate limiting**（fixed / sliding）、**Analytics GraphQL API**、Model fallback
- **provider native 支持**：Amazon Bedrock、Anthropic、Azure OpenAI 等
- **差异化**：零运维、全球边缘，**对个人开发者和小团队最友好**——是 LiteLLM/Helicone 的最强对手

### 7. OpenRouter（最大的 LLM 聚合市场）

- **规模**（2026-06 数据）：月 **100T tokens**、**8M+ 用户**、**60+ 提供商**、**400+ 模型**——已经是行业事实标准
- **自我定位**："Started in early 2023 as the **first LLM marketplace**, OpenRouter has grown to become the **largest and most popular AI gateway**"
- **2026 年新发布**（6-1 月报）：Speech/transcription APIs、**Model Fusion**（多模型融合推理）、Private models、Enterprise workspace controls、20 new models（Gemini 3.5 Flash、Claude Opus 4.8）
- **新品 Guardrails**：budget enforcement、zero data retention、model/provider restrictions——商业版开始向治理延伸
- **意义**：OpenRouter 的存在证明——**LLM 路由本身是高频需求**；它的 Fusion 功能代表"推理层组合化"的未来

### 8. Higress（阿里云原生，国内最强）

- **仓库热度**：GitHub `higress-group/higress`：**8,559 stars / 1,143 forks**，Go 实现，Apache-2.0，最新 commit 2026-06-04
- **版本**：v2.2.2（2026-05-26）、v2.2.0（2026-02-11）
- **技术栈**：基于 Istio + Envoy，云原生，**Wasm 插件扩展**
- **AI 插件矩阵**（从官方文档菜单直接抄的，已是业内最齐全）：
  - 大模型 API 供应 / 消费
  - AI 缓存、AI 提示词、AI 代理（Function Calling）
  - **AI 内容安全**、**AI 数据脱敏**、**AI 配额管理**、**AI Token 限流**
  - AI Agent、**RAG**、JSON 格式化、提示词模版、**搜索增强**（RAG 增强）
  - AI 可观测、IP 地理位置、历史对话、意图识别、请求响应转换
  - **Mcp Bridge** 配置说明（自研 MCP 桥接）
- **企业版**："90%+ 性能优化、节省 50% 资源成本、7×24 工单 + 钉群"
- **差异化**：唯一同时具备"完整 API 网关 + 完整 AI 网关 + 完整中文文档 + 商业支持"的开源产品
- **2026 年新方向**（来自博客 5-29）：**本体论（Ontology）优化 Agent 效果**——把语义本体作为 agent 的认知地图

### 9. 其他值得关注的

- **TrueFoundry**：把网关细分成 4 个独立产品——**AI Gateway / MCP Gateway / Agent Gateway / Prompt Management / Agent Skills Registry**。"Agent Gateway" 这个产品名最早可能就是他们喊出来的
- **Cloudflare Workers AI**：边缘推理 + 网关一体
- **Martian**：模型路由研究型公司，专注"任务→最佳模型"动态路由
- **APIPark**（国内）：API 资产 + AI 网关的整合

---

## 三、2025–2026 核心技术趋势

### 趋势 1：MCP Gateway 化

- Envoy AI Gateway、Portkey、TrueFoundry、Higress 都把 **MCP（Model Context Protocol）** 当成"AI 网关的下一站"
- 背景：MCP 是 Anthropic 2024 提出的"AI 万能转接头"协议（LLM ↔ 数据/工具），2025 年爆发式增长
- 痛点：Portkey 数据——**53% 的 MCP server 仍用静态 API key**，生产环境是"裸奔"
- 网关的新角色：MCP 凭据轮换、审计、限流、白名单

### 趋势 2：Agent Gateway 成为独立品类

- Portkey、TrueFoundry、LiteLLM 都把 "Agent Gateway" 单独成项
- 核心问题（Portkey 5-3 博客）：传统 LLM 监控看"调用是否 200"，但 **agent 是多步串联的，单独每个调用成功≠最终结果正确**
- 解决方向：把 LLM 监控升级为 **trace + step-level 调试 + 成本归因到 agent run**（Langfuse、LangSmith 的对手）

### 趋势 3：语义路由 / LLM Router

- 任务→最便宜/最快的模型（如代码→DeepSeek-Coder、闲聊→本地小模型、复杂推理→Claude Opus）
- OpenRouter 的 **Model Fusion** 把多模型融合进同一个响应
- Martian、Not Diamond（已被 Snowflake 收购）、RouteLLM 等专注"路由器"层
- 节省 30–70% LLM 成本是常见宣称

### 趋势 4：Guardrails 内置

- 不再是"LLM 旁边外挂一个内容审核服务"，**AI 网关原生支持 guardrails**
- Portkey：**50+ 内置 guardrails**（PII 检测、提示词注入防御、toxicity、品牌安全）
- OpenRouter 2026-06 上线 Guardrails（budget、零留存、模型限制）
- Cloudflare AI Gateway、Helicone、Higress 都有等价能力

### 趋势 5：可观测标准化

- **OpenTelemetry** 胜出：Envoy AI Gateway 已原生支持 OTel tracing
- 成本归因（cost attribution）：按用户/团队/项目分摊 LLM 成本是高频需求
- Token-level metrics：输入/输出/缓存命中率

### 趋势 6：行业整合

- **Palo Alto Networks 收购 Portkey**（安全巨头拿下 AI 治理）
- **Mintlify 收购 Helicone**（文档工具收编可观测）
- 推断：剩下的中间层（LiteLLM、Kong、OpenRouter、Higress）要么继续做大、要么被云厂商收编

---

## 四、架构观察

| 类别 | 代表 | 优势 | 劣势 |
|------|------|------|------|
| **轻量独立** | Helicone AI Gateway (Rust)、LiteLLM (Python) | 部署简单、社区活跃、模型覆盖广 | 治理能力弱 |
| **传统网关+AI** | Kong、Envoy、Higress、APIPark | 限流/认证/MCP/可观测全套 | 学习曲线陡、运维重 |
| **边缘托管** | Cloudflare AI Gateway、OpenRouter | 零运维、按量计费 | 数据出境/合规风险 |
| **垂直场景** | TrueFoundry、Portkey | Agent/MCP/Prompt 工具链深 | 商业版贵、开源版功能裁剪 |

---

## 五、对 AI 网关领域的小判断

> 个人观点，仅供参考

1. **"AI 网关"会进一步碎片化**：未来不是"一个网关统治一切"，而是 **LLM Gateway + MCP Gateway + Agent Gateway** 三个独立品类共存
2. **开源 + 商业混合模式最稳**：LiteLLM、Higress 的"开源打底 + 企业版收费"是被验证过的（Kong 早期也是这条路）
3. **AI 网关的护城河不在"路由"，在"治理"**：路由功能迟早被 OpenRouter、Cloudflare 摊薄到免费；能收费的是 **审计、合规、成本归因、agent 可观测** 这些"合规+财务"能力
4. **本体论 / RAG 增强** 是 Higress 在押的差异化方向——把"语义结构"作为网关的认知层

---

## 六、引用与数据来源

- 产品官网：portkey.ai / helicone.ai / aigateway.envoyproxy.io / higress.cn / konghq.com / developers.cloudflare.com / openrouter.ai / truefoundry.com
- GitHub：BerriAI/litellm、Portkey-AI/gateway（11,968★）、Helicone/ai-gateway（594★）、envoyproxy/ai-gateway、higress-group/higress（8,559★）
- 官方博客（标题级引用）：Portkey "What's an agent gateway" (2026-05-03)、"MCP Governance in Production" (2026-05-24)、"Skills Registry" (2026-04-23)
- 收购公告：Palo Alto Networks (Portkey 首页)、Helicone blog (2026-03-03)
- OpenRouter 数据：100T 月 token、8M+ 用户、60+ 提供商、400+ 模型（2026-06 月报）

---

*报告完。*  
*如需深入某一款产品的部署细节或对比测试，可继续追问。*
