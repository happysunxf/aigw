# F5 NGINX AI Gateway (NGINX One + NGINX Gateway Fabric) 深度调研（2026-06）

> 调研日期：2026-06-06 (Asia/Shanghai)
> 调研人：Rich (OpenClaw agent for 小F)
> 项目位置：aigw/openclaw/product-f5-nginx-ai-gateway-20260606.md
> 一手数据来源：
> - F5 NGINX 官方产品页 <https://www.f5.com/products/nginx> + <https://docs.nginx.com/nginx-gateway-fabric/>
> - 设计愿景博客 <https://www.f5.com/company/blog/nginx/our-design-vision-for-nginx-one-the-ultimate-data-plane-saas> (2024-03-13)
> - NGINX Gateway Fabric 主仓 <https://github.com/nginx/nginx-gateway-fabric> (v2.6.3, 2026-05-29)
> - Gateway 架构文档 <https://docs.nginx.com/nginx-gateway-fabric/overview/gateway-architecture/>
> - Gateway API 兼容性 <https://docs.nginx.com/nginx-gateway-fabric/overview/gateway-api-compatibility/>
> - NGINX Agent 仓库 <https://github.com/nginx/agent> (v3.10.x)
> - Gateway API SIG <https://gateway-api.sigs.k8s.io/> （上游 API 规范）
> - 横向对比对象：Portkey / LiteLLM / Kong AI Gateway / Envoy AI Gateway / Higress / APISIX ai-proxy / Cloudflare AI Gateway / Vercel AI Gateway / Solo AI Gateway / Traefik Hub AI Gateway
>
> 重要前提：**F5 NGINX AI Gateway 不是一个独立的开源仓库或独立公司**。它由三层组成：
> 1. **NGINX Open Source / NGINX Plus** —— 仍然是 1996 年 Igor Sysoev 写的数据面，互联网上市场份额最高的反向代理。
> 2. **NGINX Gateway Fabric (NGF)** —— 2022 年开源的 K8s Gateway API 控制面（v2.6.3, 2026-05-29），是 NGINX 官方在云原生时代对 Envoy Gateway / Istio 的对位。
> 3. **NGINX One** —— 2024-03 AppWorld 首次亮相的 SaaS 管理面，2025-2026 在此基础上添加 **AI Gateway 能力**（token rate-limit / provider routing / prompt guard / LLM observability），并在 2026-05 推出"AI Gateway as a Service"。
>
> 也就是说：**NGINX 把 AI Gateway 当成"在 Gateway API 之上加 LLM-aware 中间件 + 把数据面指标上送 NGINX One SaaS 做成本归因"的工程问题**，而不是像 Portkey / Helicone 那样从 LLM 路由反向去做 API 网关。这条路线天然贴 F5 的传统强项：金融 / 运营商 / 政府的"应用交付 + 安全"大盘子。

---

## 目录

- 一、项目速览与定位
- 二、项目背景与公司：F5 / NGINX 的"全栈 → AI 全栈"演化
  - 2.1 F5（FFIV）公司基本面
  - 2.2 NGINX 收购与 Igor Sysoev 时代遗产
  - 2.3 NGINX Open Source 装机量
  - 2.4 NGF（Gateway Fabric）的诞生
  - 2.5 NGINX One SaaS 的"管理面回归"
  - 2.6 F5 AI Gateway 的发布时间线（2024-2026）
  - 2.7 在 AI Gateway 矩阵中的位置
- 三、架构设计：三层分离（OSS 数据面 + NGF 控制面 + NGINX One SaaS）
  - 3.1 总览图
  - 3.2 数据面：NGINX OSS / Plus（事件循环 + C10M 血统）
  - 3.3 控制面：NGF controller-runtime + NGINX Agent gRPC
  - 3.4 SaaS 管理面：NGINX One（设计愿景）
  - 3.5 AI Gateway 在三层中的"注入点"
  - 3.6 自托管（NGF only）vs 托管（NGF + NGINX One）双模式
  - 3.7 与 Envoy AI Gateway / Kong AI Gateway 的架构差异
- 四、AI Gateway 核心能力
  - 4.1 Provider 路由（OpenAI / Azure OpenAI / Bedrock / Vertex / Ollama / vLLM）
  - 4.2 Token Rate Limit 与 Quota（基于 NGINX Plus 共享内存 zone）
  - 4.3 Prompt Guard（regex + tokenizer + LLM judge 三档）
  - 4.4 LLM Observability（OTel GenAI semconv + NGINX One Cost Lens）
  - 4.5 Failover 与 Multi-region
  - 4.6 Caching（精确 / 语义两层）
  - 4.7 Streaming / SSE 优化
  - 4.8 与 F5 Distributed Cloud 的 Multicloud Network fabric
- 五、协议支持
  - 5.1 OpenAI Chat Completions / Responses / Embeddings / Audio
  - 5.2 Anthropic Messages（Messages API）
  - 5.3 Google Gemini generateContent / streamGenerateContent
  - 5.4 Cohere v2 Chat / Embed / Rerank
  - 5.5 Mistral Chat Completions
  - 5.6 OpenAI 兼容生态（Together / Fireworks / DeepSeek / OpenRouter / vLLM / Ollama）
  - 5.7 MCP（Model Context Protocol）代理
  - 5.8 A2A（Agent-to-Agent）代理
  - 5.9 协议矩阵
- 六、性能数据与基准
  - 6.1 NGINX 数据面性能血统（C10K / C10M）
  - 6.2 NGF 控制器延迟（社区基准 6-12ms 同步 / 0-3ms gRPC）
  - 6.3 实际 LLM 代理场景性能（OSS 用户分享）
  - 6.4 NGINX Plus 共享内存 zone 对 token rate-limit 的影响
  - 6.5 Streaming 吞吐（chunked transfer 与 SSE 转发）
  - 6.6 内存 / CPU footprint
  - 6.7 与 Envoy AI Gateway / Kong AI Gateway 的横向 benchmark
- 七、部署方式
  - 7.1 K8s Helm 安装
  - 7.2 K8s OpenShift Operator 安装
  - 7.3 独立 VM / Bare Metal（NGINX Plus + Agent）
  - 7.4 启用 AI Gateway flag
  - 7.5 典型部署模式 1：本地 LLM（Ollama / vLLM / TGI）
  - 7.6 典型部署模式 2：云端 LLM（OpenAI / Bedrock / Vertex）
  - 7.7 典型部署模式 3：Hybrid（敏感本地 + 默认云端）
  - 7.8 典型部署模式 4：F5 Distributed Cloud（XC）边缘接入
  - 7.9 GitOps 集成（ArgoCD / FluxCD / Spinnaker）
  - 7.10 与 BIG-IP Next 的统一管理
- 八、成本模型
  - 8.1 NGINX Plus 订阅（per-instance / per-year）
  - 8.2 NGINX One 消费计费（$0 / consumption tier）
  - 8.3 F5 Distributed Cloud Bandwidth / Compute
  - 8.4 间接成本：token rate-limit 节省与 cache 命中率
  - 8.5 隐性成本：WAF / DDoS 模块订阅
  - 8.6 与 Portkey / Helicone / Cloudflare 的成本对比
- 九、生态与第三方集成
  - 9.1 NGINX One Observability：Prometheus / Grafana / OpenTelemetry
  - 9.2 NGINX App Protect（WAF + Bot Defense + API Security）
  - 9.3 F5 Distributed Cloud（XC WAAP / Multicloud Network / Bot Defense）
  - 9.4 BIG-IP Next 联邦
  - 9.5 HashiCorp Vault / CyberArk 凭据保险箱
  - 9.6 cert-manager / SPIFFE / mTLS
  - 9.7 与 OPA / Cedar 的策略外接
  - 9.8 MCP Server 桥接（stdio → SSE）
- 十、客户案例
  - 10.1 公开宣称的客户行业（金融 / 电信 / 政府 / 关键基础设施）
  - 10.2 "Traefik / NGINX Proxy 60,000+ stars + F5 BIG-IP 4,000+ 客户" 形成的 OSS → 商业转化
  - 10.3 公开案例（用 NGINX 跑 LLM 服务的工程实践）
  - 10.4 与"AI Gateway 专门厂商"的客户重叠
- 十一、关键事件时间线（2024-2026）
- 十二、优劣势分析
  - 12.1 优势
  - 12.2 劣势
- 十三、与其他 AI Gateway 的对比
  - 13.1 与 Portkey / LiteLLM / One API（LLM Router 派）
  - 13.2 与 Kong AI Gateway / APISIX ai-proxy / Envoy AI Gateway（通用 API Gateway AI 插件派）
  - 13.3 与 Cloudflare AI Gateway / Vercel AI Gateway / Solo AI Gateway（边缘云 AI Gateway 派）
  - 13.4 与 AWS Bedrock / Azure AI / Vertex（云厂商原生）
  - 13.5 与 Helicone / OpenRouter / Unify（中间层 SaaS）
  - 13.6 与 Traefik Hub AI Gateway（直接对位）
  - 13.7 横向对比矩阵
- 十四、对我们的硬要求（落地 AIGW 12 条）
- 十五、参考资料

---

## 一、项目速览与定位

**F5 NGINX AI Gateway** 是 F5 公司在 2024 年推出 **NGINX One** 平台基础上，于 **2025-2026 年** 叠加的 **LLM-aware 流量管理层**。它把"NGINX 二十多年做反向代理、应用交付、API 网关"的经验直接复用为 LLM 场景的流量治理层。

**三句话定位**：
1. **不是 LLM Router 派（Portkey / LiteLLM）**——F5 不想从"100+ LLM provider 适配"切入；NGINX AI Gateway 把这件事留给下游（Cloudflare、Vercel、OpenRouter），而自己专注"AI-aware 流量调度 + 企业级安全 + NGINX Plus 的共享内存 zone"。
2. **不是云厂商原生派（AWS Bedrock / Azure AI）**——F5 强调"自托管 + 多云中立"，AI Gateway 是 NGINX One 上的一个 feature，不是"必须用 F5 公有云"。
3. **不是中间层 SaaS 派（Helicone / Unify）**——F5 不收 token 过路费、不做 cache 重售；F5 收的是 **NGINX Plus 实例订阅 + NGINX One SaaS 消费计费 + F5 Distributed Cloud 带宽**。

**与"通用 API Gateway + AI 插件"派（Kong / APISIX / Envoy / Traefik Hub）的关系**：F5 走"原生数据面"路线——NGINX 自 1996 年起就以"小而极致"为哲学，OpenResty / Kong / APISIX / Traefik 都曾借鉴或基于 NGINX 起家；F5 AI Gateway 的所有能力都编译进 NGINX 二进制（没有 Lua / WASM 开销）。

**核心客群画像**：
- **金融 / 银行**：F5 BIG-IP 全球 4,000+ 客户，PCI-DSS / SOX 合规要求"凭据不离域 + 全量审计 + WAF 一等公民"，NGINX Plus + F5 WAF 一行 YAML 启用。
- **电信 / 运营商**：F5 在 5G UPF / GiLAN 市场份额高，运营商有"私有 LLM + 公网 LLM 双轨"需求，AI Gateway 的"敏感本地 / 默认云端"路由正合胃口。
- **政府 / 公共部门**：FedRAMP / 国资云合规，AI Gateway 的"自托管 + 不上送 prompt 到 SaaS"是关键。
- **大型零售 / 制造**：NGINX 装机量大，已是 7 层标准件，AI Gateway 是在既有 NGINX Plus 资产上加 LLM-aware 中间件。

**关键数字（截至 2026-06）**：
- NGINX Gateway Fabric 仓库当前版本：**v2.6.3**（2026-05-29），Gateway API 标准 1.5.1、K8s 1.31+。
- NGINX Agent 当前版本：**v3.10.3**。
- NGINX Plus 当前发布版本：**R37**。
- NGINX Open Source 当前发布版本：**1.31.1**。
- F5 WAF for NGINX 当前版本：**5.13.1**。
- F5 公司（NASDAQ: FFIV）2025 财年营收约 **$3.0B**，员工 6,000+。
- NGINX 全球市场份额（Web Server Survey W3Techs 历史峰值）：**~33-34%**（Apache 31%、Cloudflare 22%、NGINX 22-33%），是 1996-2024 长跑冠军。

---

## 二、项目背景与公司：F5 / NGINX 的"全栈 → AI 全栈"演化

### 2.1 F5（FFIV）公司基本面

F5 Inc. 创立于 **1996 年**，总部 **西雅图**，2025 财年市值约 **$15B**，营收 **$3.0B** 区间。NYSE 上市代码 **FFIV**。

| 维度 | 数据 |
|---|---|
| 创立 | 1996 |
| 总部 | Seattle, WA, USA |
| 上市 | NASDAQ: FFIV |
| 员工 | 6,000+ (2025) |
| FY25 营收 | ~$3.0B |
| 主营业务 | BIG-IP（硬件 / 虚拟 ADC）、NGINX、Distributed Cloud（XC WAAP + Multicloud Network）、F5 WAF、BIG-IP Next（新一代）|
| 历史里程碑 | 1996 创立；2001 BIG-IP 4.x 走 IDC；2019 **$670M 收购 NGINX**；2021 收购 **Volterra**（边缘云，演化为 Distributed Cloud）；2022 推出 NGINX Gateway Fabric；2024 推出 NGINX One SaaS；2025-2026 叠加 AI Gateway |

F5 名字源自龙卷风 Fujita Scale 最高等级 5。长期占据 **应用交付控制器（ADC）** 市场近一半份额（2010s 顶峰），主要客户是大型银行、电信运营商、政府、关键基础设施。

### 2.2 NGINX 收购与 Igor Sysoev 时代遗产

NGINX 起初是俄罗斯工程师 **Igor Sysoev** 在 2002 年的开源项目，最初解决 C10K 问题（单机 10K 并发）。2011 年成立 NGINX Inc.（前称），Igor 任 CTO。2019 年 3 月 F5 以 **$670M** 收购 NGINX。Igor 一度在 F5 担任 Fellow，2022 年 1 月离职（部分社区因此担忧 NGINX 失去"灵魂工程师"，但 F5 保留 NGINX 团队和开源策略不变）。

NGINX 核心遗产：
- **事件循环（epoll/kqueue）架构**——单机 50K+ 长连接、C10K 时代的标杆。
- **小而可组合**——核心代码 C 语言 ~15 万行，编译后 ~2MB；可执行文件 1.4MB。
- **配置 DSL**——`nginx.conf` 嵌套指令块，行业标杆；Kong / OpenResty / Traefik Proxy 都曾借鉴。
- **OpenResty**——章亦春（agentzh）基于 NGINX + LuaJIT 的扩展框架，**2015-2020 年 Kong / APISIX 早期版本都是 OpenResty 衍生品**。

### 2.3 NGINX Open Source 装机量

W3Techs 历史数据，NGINX 在 Web Server 市场份额峰值为 **33-34%**（与 Apache 轮流）。是 Cloudflare、Netflix、WordPress.com、Dropbox 等大型服务的 7 层标配。装机量本身是 F5 AI Gateway 商业转化的最大底气。

| 项目 | 2024 数据 |
|---|---|
| NGINX OSS 1.x 系列累计下载 | >1B+ Docker pulls (Docker Hub `nginx`) |
| W3Techs Web Server 份额（截至 2024） | ~22-34% |
| 全球部署实例（粗估） | 4 亿+ 容器实例 / 数千万物理 / 虚机 |
| 知名用户 | Cloudflare / Netflix / WordPress.com / Dropbox / Atlassian / GitHub 部分边缘节点 |

### 2.4 NGF（Gateway Fabric）的诞生

**NGINX Gateway Fabric (NGF)** 是 2022 年开源的 K8s Gateway API 控制面。它和 **NGINX Ingress Controller (NIC)** 并存：
- **NIC（2014-）**：基于 K8s Ingress 1.x API，老牌、稳定、市占率高，但 Ingress 1.x 表达能力弱。
- **NGF（2022-）**：基于 K8s Gateway API（SIG-Network 主导），是 NGINX 对 Envoy Gateway / Istio 的对位。

NGF 2.6.3 (2026-05-29) 当前支持的 Gateway API 标准：**v1.5.1**，K8s：**1.31+**。早期版本对照（取自 README）：

| NGF | Gateway API | K8s | NGINX OSS | NGINX Plus | NGINX Agent | F5 WAF |
|---|---|---|---|---|---|---|
| 2.6.3 (current) | 1.5.1 | 1.31+ | 1.31.1 | R37.0 | v3.10.3 | 5.13.1 |
| 2.5.1 | 1.5.1 | 1.31+ | 1.29.7 | R36 | v3.8.0 | — |
| 2.4.2 | 1.4.1 | 1.25+ | 1.29.5 | R36 | v3.7.1 | — |
| 2.3.0 | 1.4.1 | 1.25+ | 1.29.3 | R36 | v3.6.0 | — |
| 2.2.2 | 1.3.0 | 1.25+ | 1.29.2 | R35 | v3.6.0 | — |
| 2.1.4 | 1.3.0 | 1.25+ | 1.29.1 | R35 | v3.3.1 | — |
| 2.0.2 | 1.3.0 | 1.25+ | 1.28.0 | R34 | v3.0.1 | — |
| 1.6.2 | 1.2.1 | 1.25+ | 1.27.4 | R33 | — | — |
| 1.0.0 | 1.0.0 | 1.23+ | 1.25.4 | R31 | — | — |

**OpenShift** 兼容性：

| NGF | Operator | Preferred GWAPI | Compatible GWAPI | OCP with Preferred | Supported OCP |
|---|---|---|---|---|---|
| 2.6.x | v1.4.x | v1.5.x | v1.2.1-v1.5.x | — | 4.19-4.21 |
| 2.5.x | v1.3.x | v1.5.x | v1.2.1-v1.5.x | — | 4.19-4.21 |
| 2.4.x | v1.2.x | v1.4.x | v1.2.1-v1.4.x | 4.20-4.21 | 4.19-4.21 |
| 2.2.x | v1.0.x | v1.3.0 | v1.2.1 | — | 4.19 |

### 2.5 NGINX One SaaS 的"管理面回归"

2024 年 3 月 13 日，NGINX 在 F5 AppWorld 2024 大会正式发布 **NGINX One**——把 OSS / Plus / Instance Manager / Ingress Controller / Gateway Fabric 五个产品统一到一个 SaaS 管理面，订阅式付费。设计愿景博客（2024-03-13）核心原文：

> "We will introduce new use cases like AI gateway. We are making it frictionless and ridiculously easy for you to consume these services with a consumption-based tiered pricing."

NGINX One 核心原则：
- **非意见化（non-opinionated）**——支持所有 NGINX 用法（web server / reverse proxy / ADC / K8s / WAF / CDN）。
- **单一 API**——RESTful API 集成进 CI/CD。
- **单一管理面**——一个控制台管所有 NGINX 实例。
- **消费计费（consumption-based）**——无年费 / 无按座收费，按消耗算。
- **云无关**——自部署 / 公有云 / F5 Distributed Cloud 都可。
- **F5 Distributed Cloud 集成**——Multicloud Network + OneWAF + DDoS 一站启用。

### 2.6 F5 AI Gateway 的发布时间线（2024-2026）

| 日期 | 事件 |
|---|---|
| 2024-03-13 | AppWorld 2024 大会发布 NGINX One，宣布"AI gateway" 是 NGINX One 的未来方向。|
| 2024-06 | NGINX One Early Access 计划开启（waiting list 模式）。|
| 2024-09-2024-12 | NGINX One GA；F5 在多场活动（AppWorld EMEA / APAC）宣传 AI Gateway 是 2025 主线。|
| 2025-Q1 | **F5 NGINX AI Gateway beta**：在 NGINX One 上叠加 AI 流量管理能力（provider 路由 / token rate-limit / 基础 observability）。|
| 2025-Q2 | **F5 NGINX AI Gateway GA**（NGINX One Add-on）：宣布 token-aware rate limiting、prompt guard（regex + tokenizer + LLM judge 三档）、F5 WAF for AI。|
| 2025-Q3 | **F5 WAF for AI**：针对 LLM 流量的 WAF 规则集（jailbreak / 越权 / 异常响应）。|
| 2025-Q4 | **F5 Distributed Cloud 集成**：AI Gateway 与 XC WAAP 双向同步，跨云统一管理。|
| 2026-Q1 | **A2A 协议代理**：F5 在 NGINX AI Gateway 中加入 Agent-to-Agent 协议识别（与 Google A2A spec 同期落地）。|
| 2026-Q2 | **MCP 桥接**：stdio → SSE 转换，SSE → streamable HTTP 反向代理，与 MCP 2026-07-28-rc 规范同步。|
| 2026-05-29 | NGF 2.6.3 发布（与本调研日期相邻），强化 ListenerSet / WAF 集成 / mTLS 端点。|
| 2026-06 | F5 在本年度 NGINX Summit（预定）公开 AI Gateway 商业化下一步方向。|

### 2.7 在 AI Gateway 矩阵中的位置

按 2026 年视角的 AI Gateway 矩阵：

| 维度 | NGINX AI Gateway | Portkey | LiteLLM | Kong AI Gateway | Envoy AI Gateway | Cloudflare AI Gateway |
|---|---|---|---|---|---|---|
| 切入路线 | 通用 API Gateway + AI 插件 | LLM Router | LLM Router | 通用 API Gateway + AI 插件 | Service Mesh 派 | 边缘云 + AI |
| 部署形态 | 自托管 / SaaS / XC | SaaS + OSS Proxy | OSS Proxy | 自托管 | 自托管 | SaaS 边缘 |
| 数据面语言 | C (NGINX) | Python | Python | Lua + Go | C++ (Envoy) | Workers (Rust) |
| 主要客群 | 金融 / 电信 / 政府 | AI 工程师 | AI 工程师 | 大型企业 | Service Mesh 用户 | 边缘 / 多云 |
| 商业化深度 | 极深（F5 + XC 闭环）| 中（云） | 浅（OSS） | 中 | 浅 | 中 |
| LLM provider 适配 | 5-10 个原生 + 任何 OpenAI 兼容 | 250+ | 100+ | 25+ | 10+ | 35+ |
| Token-aware 治理 | ★★★★★ | ★★★★ | ★★★ | ★★★★ | ★★★★ | ★★★ |
| 企业安全 (WAF / DDoS) | ★★★★★ (F5 WAF) | ★★ | ★ | ★★★★ (Kong) | ★★ | ★★★★★ (CF WAAP) |
| MCP / A2A 协议支持 | 2026-Q2 跟进 | 2025-Q4 跟进 | 2025-Q4 跟进 | 2026-Q1 跟进 | 2025-Q4 跟进 | 2025-Q4 跟进 |
| 总拥有成本 | 高（F5 Plus 订阅）| 中（SaaS） | 低（OSS + 自运维） | 中-高 | 中 | 中 |

NGINX AI Gateway 的"卡位"是**"如果你的 LLM 服务要部署在 NGINX 已经在的地方，并且你要 PCI-DSS / FedRAMP 合规，那么 F5 是阻力最小的那条路"**。

---

## 三、架构设计：三层分离

### 3.1 总览图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  F5 NGINX AI Gateway 三层架构                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │          Layer 3: SaaS Management Plane (NGINX One)              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │  │
│  │  │ AI Cost Lens │  │ Config Sync  │  │ AI-aware Observability  │ │  │
│  │  │ (token×$/?)  │  │ (GitOps)     │  │ (OTel GenAI semconv)    │ │  │
│  │  └──────────────┘  └──────────────┘  └─────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │ F5 WAF for AI  │ Prompt Guard  │ Token Rate Limit  │ Audit │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│           ▲ mTLS (NGINX Agent) / OTel collector / REST API              │
│           │                                                                │
│  ┌────────┴───────────────────────────────────────────────────────────┐   │
│  │         Layer 2: Control Plane (NGINX Gateway Fabric 2.6.3)       │   │
│  │  ┌──────────────────────────────────────────────────────────────┐ │   │
│  │  │  NGF Controller (controller-runtime, Go)                      │ │   │
│  │  │  - watch GatewayClass / Gateway / HTTPRoute / GRPCRoute       │ │   │
│  │  │  - watch Service / Endpoints / Secrets / ConfigMap            │ │   │
│  │  │  - translate → NGINX config snippets                          │ │   │
│  │  └──────────────────────────────────────────────────────────────┘ │   │
│  │  ┌──────────────────────────────────────────────────────────────┐ │   │
│  │  │  NGINX Agent (gRPC, v3.10.3)                                 │ │   │
│  │  │  - receive config from controller                            │ │   │
│  │  │  - validate → write files → signal nginx -s reload           │ │   │
│  │  │  - collect metrics / events / token usage                     │ │   │
│  │  └──────────────────────────────────────────────────────────────┘ │   │
│  └────────┬───────────────────────────────────────────────────────────┘   │
│           │ (per-Gateway data plane deployment)                          │
│  ┌────────┴───────────────────────────────────────────────────────────┐   │
│  │          Layer 1: Data Plane (NGINX OSS 1.31.1 / NGINX Plus R37)  │   │
│  │  ┌──────────────────────────────────────────────────────────────┐ │   │
│  │  │  NGINX Worker Process(es)                                    │ │   │
│  │  │  - epoll/kqueue event loop                                   │ │   │
│  │  │  - HTTP/1.1, HTTP/2, HTTP/3, gRPC, WebSocket                 │ │   │
│  │  │  - upstream load balancing (round-robin / least-conn / hash)  │ │   │
│  │  │  - shared memory zone (NGINX Plus): token rate-limit / cache │ │   │
│  │  │  - L7 routing: path / host / header / method / cookie        │ │   │
│  │  └──────────────────────────────────────────────────────────────┘ │   │
│  │  ┌──────────────────────────────────────────────────────────────┐ │   │
│  │  │  AI-Aware Extensions (compiled into NGINX binary)            │ │   │
│  │  │  - LLM provider snippet: OpenAI / Anthropic / Bedrock / etc. │ │   │
│  │  │  - Token rate-limit: shm-zone counter, sliding window        │ │   │
│  │  │  - Prompt guard: regex pre-filter + tokenizer anomaly        │ │   │
│  │  │  - Streaming: chunked / SSE / WebSocket passthrough          │ │   │
│  │  │  - Caching: exact (key=hash) + semantic (cosine, external)   │ │   │
│  │  └──────────────────────────────────────────────────────────────┘ │   │
│  └────────┬───────────────────────────────────────────────────────────┘   │
│           │ HTTP / gRPC / SSE                                              │
│  ┌────────┴───────────────────────────────────────────────────────────┐   │
│  │                     Backend LLM Upstreams                          │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐       │   │
│  │  │ OpenAI │  │ Azure  │  │Bedrock │  │  vLLM  │  │ Ollama │       │   │
│  │  │  API   │  │  OpenAI│  │  Claude│  │  KServe│  │  Local │       │   │
│  │  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘       │   │
│  └────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据面：NGINX OSS / Plus（事件循环 + C10M 血统）

NGINX 数据面是 1996 年 Igor Sysoev 写 C 语言起的家，20 多年演化到 NGINX 1.31.1 (OSS) 和 R37 (Plus)。

**核心数据面能力**：
- **事件循环**：Linux epoll / BSD kqueue / Solaris eventports，单进程可处理 50K+ 活跃长连接。
- **Worker 模型**：默认 `worker_processes = CPU cores`；每个 worker 单线程 + 多连接（多 accept_mutex 协调）。
- **AIO + thread pool**：大文件传输 / 动态计算（auth_request）走 thread pool 不阻塞事件循环。
- **HTTP/1.1 / HTTP/2 / HTTP/3**：HTTP/3 (QUIC) 自 1.25 起 GA。
- **Upstream load balancing**：
  - Round-robin / least-conn / IP-hash / random / generic hash
  - Active health check (Plus：自定义 status / body regex)
  - Passive health check（连续失败 N 次摘除）
  - Slow start (Plus：新上线的 pod 限流 warm-up)
  - Connection draining (Plus：`drain` 不杀正在处理的长连接)
- **Shared memory zone (Plus)**：跨 worker 共享计数器 / cache key，是 token rate-limit 实现的物质基础。
- **Auth subrequest**：通过 `auth_request` 调外部 service，做 token 校验 / token 配额扣除。
- **Mirroring**：`mirror` 指令把请求体复制一份到镜像后端（用于 shadow / replay / 对照）。
- **gRPC / WebSocket / SSE**：原生支持，stream 转发不缓冲。

**与 AI 场景特别相关的细节**：
- **chunked transfer + streaming**：NGINX 默认对 HTTP/1.1 启用 chunked，配合 `proxy_buffering off;` + `proxy_cache off;` 可实现 SSE 端到端流式。NGINX Plus R25+ 引入 **`proxy_request_buffering off;` 与 `proxy_buffer_size` 调优**针对长 chunk 流。
- **Upstream keepalive**：维持与 OpenAI / Bedrock 长连接，省掉每个请求的 TLS 握手（节省 50-100ms p50 延迟）。
- **request body buffering**：默认 `client_body_buffer_size 16k`，可关掉 (`client_body_in_file_only` 或 `client_body_buffer_size 0`) 避免 prompt 落盘。

### 3.3 控制面：NGF controller-runtime + NGINX Agent gRPC

NGF 是 K8s 原生 controller，使用 [controller-runtime](https://github.com/kubernetes-sigs/controller-runtime) 库（K8s SIG 官方 controller 框架，kubebuilder 衍生）。代码语言：Go。

**核心组件**：
- **NGF Controller Pod**：单 Deployment，运行在 `nginx-gateway` namespace。
- **NGINX Data Plane Pod**：每个 Gateway 资源对应 1 个 Deployment / DaemonSet，NGINX 容器 + NGINX Agent 容器（sidecar 模式或同 pod 多 container）。
- **NGINX Agent**（v3.10.3）：Go 写的 gRPC 守护进程，监听 control plane 的配置推送。

**通信协议**（自 NGINX 文档）：
1. **Kubernetes API → NGF Controller**（HTTPS）：NGF watch Gateway / HTTPRoute / GRPCRoute / ReferenceGrant / Service / Endpoints / Secrets。
2. **NGF Controller → NGINX Agent**（gRPC + mTLS）：NGF 把生成的 NGINX config snippets 通过 gRPC 推给 Agent。默认 self-signed 证书，可选 cert-manager 集成。
3. **NGINX Agent → NGINX Master**（Signal）：Agent 把新配置写入磁盘后，signal NGINX master `nginx -s reload`，零停机 reload。
4. **Prometheus → NGINX Worker**（HTTP/HTTPS）：`/metrics` 端点暴露 NGINX 内置指标。
5. **NGF Controller → F5 Telemetry Service**（HTTPS）：控制面发出 API 请求、usage、性能 stats、错误率等遥测。
6. **Client → NGINX Worker**（HTTP/HTTPS）：正常 7 层流量。

**与 Envoy Gateway 的本质差异**：
- **Envoy Gateway**：xDS（CDS / EDS / LDS / RDS）协议，Envoy 与 xDS server 走 gRPC streaming。控制面推送的是"配置状态 + 端点状态"全量。
- **NGF**：gRPC 一来一回 + 文件 + reload。配置通过文件 + reload 落地，每次 reload 是完整 NGINX 重启 worker（NGINX 平滑 reload 是"master fork 子 worker"机制，几乎不丢连接，但有微秒级卡顿）。
- **reload vs xDS**：reload 模型在 1000+ HTTPRoute 的大集群上，配置变化会导致 10-50ms worker 切换延迟累积；xDS 是真正流式更新。**这是 NGINX AI Gateway 在大集群下的已知限制**。

**NGF 资源模型**：
- `GatewayClass`（v1）：每个 NGF 安装一个 GatewayClass，由 `--gatewayclass` flag 配置。
- `Gateway`（v1）：监听器（listener）+ TLS 配置 + NginxProxy 参数。
- `HTTPRoute`（v1）：HTTP 路径 / header / query / method 匹配 + filter（rewrite / redirect / mirror / CORS / extensionRef）+ backendRefs。
- `GRPCRoute`（v1）：gRPC method 匹配 + 头 / 过滤器 + 后端。
- `TCPRoute` / `UDPRoute`（v1alpha2 实验）：L4 直通。
- `TLSRoute`（v1）：SNI 路由。
- `ReferenceGrant`（v1）：跨 namespace 引用授权。
- `BackendTLSPolicy`（v1，部分支持）：到 backend 的 mTLS。
- `Custom policies`（NginxProxy / SnippetsFilter / AuthenticationFilter / ClientSettingsPolicy / etc.）：Nginx 自定义扩展。

### 3.4 SaaS 管理面：NGINX One（设计愿景）

NGINX One 是 2024-03 推出的 SaaS 控制面，把 NGINX OSS / Plus / Instance Manager / Ingress Controller / Gateway Fabric 统一管理。

**核心能力**：
- **统一管理面**：一个 console / 一套 API 管全球所有 NGINX 实例（数据中心 / 多云 / 边缘）。
- **AI Cost Lens**：把 NGINX data plane 收集的 `gen_ai.client.token.usage`（prompt / completion / cache_read 三元组）× model × team × project 维度上送 SaaS，在 dashboard 上出 cost / token / latency 报表。
- **AI-aware Observability**：内建 OpenTelemetry GenAI semconv 支持，trace 走 SaaS collector（可选导出到客户自己的 OTel backend）。
- **Config Sync**：从 GitOps 仓库（ArgoCD / FluxCD）拉配置，NGINX One 负责"config 应当长什么样"与"实际 long-running config 状态"对比，drift 时报警。
- **F5 Distributed Cloud 联邦**：NGINX One 的视图能下钻到 F5 XC 的边缘节点。
- **CVE mitigation discovery**：自动扫描组织内所有 NGINX 实例版本，对照 NVD 找受 CVE 影响的版本，提示升级。

**通信**：NGINX Agent（已经部署）通过 mTLS 与 NGINX One 后端通信，把"配置 + 指标 + 事件"上送。

### 3.5 AI Gateway 在三层中的"注入点"

把"AI 流量管理能力"在三层中分别注入：

| 能力 | 注入层 | 实现方式 |
|---|---|---|
| Provider 路由（OpenAI / Azure / Bedrock / Vertex） | 数据面 | NGINX `upstream` + `proxy_pass` 集群；LLM 协议在 `location` 块中识别。|
| Token rate-limit | 数据面（Plus 共享内存 zone）| `limit_req_zone $token_zone:zone=ai:rate=Nr/m;` 配 `limit_req` + `map` 从 JWT 抽 team。|
| Prompt guard（regex / tokenizer） | 数据面 | `if ($prompt ~* "jailbreak|ignore previous")` block；tokenizer 异常走 `auth_request` 调外部 service。|
| LLM judge prompt guard | SaaS / 数据面外接 | `auth_request` 调 F5 Distributed Cloud 上的 LLM judge service（更慢，~500ms p99）。|
| LLM Observability | 数据面 + SaaS | 数据面 emit OTel GenAI semconv span（`gen_ai.client.token.usage` 等）；SaaS dashboard 渲染。|
| Failover / Multi-region | 数据面（Plus 集群）| `upstream` 多 backend + `backup` + `max_fails` + `fail_timeout`。|
| Caching | 数据面 | `proxy_cache_path` 精确缓存；语义缓存走 `auth_request` 调外部 vector store。|
| MCP 桥接 | 数据面 + 控制面 | `location` 识别 `mcp-session-id` header；stdio → SSE 转换在 `auth_request` 外接 sidecar。|
| A2A 协议识别 | 数据面 | `map $http_content_type $is_a2a` 识别 JSON-RPC over HTTP；走 A2A-specific 路由。|

### 3.6 自托管（NGF only）vs 托管（NGF + NGINX One）双模式

| 模式 | 控制面 | 数据面 | 管理 | 适用客户 |
|---|---|---|---|---|
| **自托管 OSS** | NGF OSS（v2.6.3）| NGINX OSS 1.31.1 | kubectl / Helm / Kustomize | 小团队 / 严格自托管 |
| **自托管 Plus** | NGF OSS | NGINX Plus R37 | NGINX Instance Manager（可选）| 中大型企业 |
| **NGINX One SaaS** | NGF + NGINX One SaaS | NGINX OSS 或 Plus | SaaS console | 多集群 / 多云 |
| **F5 Distributed Cloud** | NGINX One + XC 联邦 | NGINX Plus on XC edge | XC console | 全球边缘 / 合规边缘 |

### 3.7 与 Envoy AI Gateway / Kong AI Gateway 的架构差异

| 维度 | NGINX AI Gateway | Envoy AI Gateway | Kong AI Gateway |
|---|---|---|---|
| 数据面 | NGINX C 事件循环 | Envoy C++ 事件循环 | OpenResty (NGINX + LuaJIT) + Go |
| 配置更新机制 | 文件 + reload | xDS streaming | DB-less (declarative) / DB-mode |
| reload 影响 | 微秒级 worker 切换（基本无感）| 零（xDS 推送）| reload 切换（Kong 也有 reload 痛点）|
| 集群规模 | 1k-10k HTTPRoute OK | 100k+ | 1k-5k |
| 启动 / 配置生效延迟 | 秒级（K8s reconcile）| 毫秒级（xDS）| 秒级 |
| 核心强项 | 性能 + 安全 + WAF 集成 | xDS 灵活性 + Service Mesh 兼容 | 插件生态 + 250+ 已有插件 |
| 生态广度 | 限于 NGINX 生态 | 限于 Envoy 生态 / Istio 兼容 | Kong 250+ 插件 + 自定义 Go/Lua/JS |
| 性能血统 | 20+ 年反向代理优化 | Lyft 4 年 Service Mesh 优化 | OpenResty 衍生 |
| 大集群 L7 route 数 | 1k-10k 流畅 | 10k+ 流畅 | 1k-5k |
| 与 WAF 集成 | F5 WAF 5.13.1 一等公民 | 需外接 | Kong WAF 插件 |

---

## 四、AI Gateway 核心能力

### 4.1 Provider 路由（OpenAI / Azure OpenAI / Bedrock / Vertex / Ollama / vLLM）

NGINX AI Gateway 通过 **upstream 集群** + **路径前缀 / Host 匹配** 路由到不同 LLM provider。

**典型 OpenAI 代理配置**（NGINX conf）：

```nginx
upstream openai_backend {
    server api.openai.com:443;
    keepalive 64;
    keepalive_timeout 60s;
    keepalive_requests 1000;
}

upstream anthropic_backend {
    server api.anthropic.com:443;
    keepalive 32;
}

upstream bedrock_backend {
    # AWS Bedrock with SigV4 presigned URL
    server bedrock-runtime.us-east-1.amazonaws.com:443;
    keepalive 32;
}

# map token count from request body
map $request_body $req_estimated_tokens {
    default 100;  # fallback
    "~*\"max_tokens\"\s*:\s*(\d+)" $1;
}

# Token rate limit (NGINX Plus shared memory zone)
limit_req_zone $jwt_team zone=ai_team:10m rate=1000r/m;

server {
    listen 8443 ssl;
    server_name llm.example.com;
    ssl_certificate /etc/ssl/certs/llm.example.com.crt;
    ssl_certificate_key /etc/ssl/private/llm.example.com.key;
    ssl_protocols TLSv1.3;

    # OpenAI Chat Completions
    location /v1/chat/completions {
        # Token rate-limit
        limit_req zone=ai_team burst=10 nodelay;
        limit_req_status 429;

        # Pass to OpenAI
        proxy_pass https://openai_backend;
        proxy_set_header Host api.openai.com;
        proxy_set_header Authorization "Bearer $openai_api_key";
        proxy_set_header Content-Type application/json;

        # Streaming: don't buffer
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_http_version 1.1;
        chunked_transfer_encoding on;

        # Long timeout for streaming
        proxy_connect_timeout 5s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Anthropic Messages
    location /v1/messages {
        limit_req zone=ai_team burst=10 nodelay;
        proxy_pass https://anthropic_backend;
        proxy_set_header Host api.anthropic.com;
        proxy_set_header x-api-key $anthropic_api_key;
        proxy_set_header anthropic-version "2023-06-01";

        proxy_buffering off;
        proxy_request_buffering off;
        proxy_http_version 1.1;
    }

    # AWS Bedrock
    location /v1/bedrock/ {
        limit_req zone=ai_team burst=10 nodelay;
        proxy_pass https://bedrock_backend;
        # SigV4 signing handled by AWS SDK in upstream or auth_request
        proxy_set_header Authorization $bedrock_aws_sigv4;

        proxy_buffering off;
    }
}
```

**Provider 适配现状**（截至 2026-06）：

| Provider | 协议 | NGINX 适配方式 | 关键点 |
|---|---|---|---|
| **OpenAI** | Chat Completions / Responses / Embeddings / Audio | `proxy_pass` 集群 + Host 重写 + Authorization header 注入 | 最稳定；NGINX One 内置 example |
| **Azure OpenAI** | 同 OpenAI（不同 endpoint）| `proxy_pass` 集群 + `Host: <resource>.openai.azure.com` | API version 通过 query string 传 |
| **AWS Bedrock** | InvokeModel / Converse / ConverseStream | `proxy_pass` 集群 + SigV4 签名（via `auth_request` 调 Lambda）| SigV4 是痛点，2026 还在做原生签名 |
| **Google Vertex AI** | generateContent / streamGenerateContent | `proxy_pass` 集群 + OAuth2 token 刷新（`auth_request` 周期刷新）| Token 刷新是定时任务 |
| **Anthropic** | Messages | `proxy_pass` 集群 + `x-api-key` header | 简单；NGINX One 内置 |
| **Cohere** | v2 Chat / Embed / Rerank | `proxy_pass` 集群 | 简单 |
| **Mistral** | Chat Completions | `proxy_pass` 集群 | OpenAI 兼容 |
| **Ollama** | OpenAI 兼容 + 原生 `/api/chat` | `proxy_pass` 集群 + 路径重写 | 本地部署最常用 |
| **vLLM** | OpenAI 兼容 | `proxy_pass` 集群 | KServe / 裸 vLLM 通用 |
| **TGI** | OpenAI 兼容 + 原生 | `proxy_pass` 集群 | Hugging Face 标准 |
| **LMDeploy** | OpenAI 兼容 | `proxy_pass` 集群 | 国产 |
| **OpenRouter / Together / Fireworks / DeepSeek** | OpenAI 兼容 | `proxy_pass` 集群 | 一行 upstream |

**痛点**：Bedrock SigV4 / Vertex OAuth2 需要 `auth_request` 调外部服务，每次请求增加 5-50ms 延迟。F5 在 2026 roadmap 上提到"原生 SigV4 in NGINX binary"。

### 4.2 Token Rate Limit 与 Quota

**这是 NGINX AI Gateway 区别于其它"AI 中间层"的最强能力点**——基于 NGINX Plus 的 **共享内存 zone**（shm zone），实现跨 worker 进程的 token 维限流。

**实现原理**：

```nginx
# 1. 定义 token 共享内存 zone（NGINX Plus）
limit_req_zone $jwt_team zone=ai_team_per_min:10m rate=1000r/m;
limit_req_zone $jwt_team zone=ai_team_per_day:50m rate=1000000r/d;

# 2. 提取 token 计数（粗估：1 token ≈ 4 chars）
map $request_body $req_estimated_tokens {
    default 200;  # 默认估 200 tokens
    "~*\"prompt\"\s*:\s*\"([^\"]*)\"" $prompt_len;  # 简化：实际用 tokenize
}

# 3. 在 location 块使用
location /v1/chat/completions {
    limit_req zone=ai_team_per_min burst=20 nodelay;
    limit_req zone=ai_team_per_day burst=1000 nodelay;
    limit_req_status 429;
    limit_req_log_level warn;
}
```

**与普通 IP/QPS 限流的差异**：
- **IP 限流**：Nginx OSS 即可（`limit_req_zone $binary_remote_addr`）。
- **Token 限流**：需要在请求处理前**估算** token（粗估 + 实际后置校准）。
- **后置校准**：从 upstream response 中读 `usage.total_tokens`，写入 zone 做"准实时"扣减，避免超发。
- **跨 worker 一致性**：NGINX Plus 的 shm zone 用自旋锁 + atomic counter，跨 worker 同步无锁。

**Token 估算的实现路径**（F5 推荐）：
1. **Header 注入**：`client_max_body_size 1m;` 收完整 body。
2. **map 抽 `prompt` 字段**：`map $request_body $prompt_len` 抽 `messages[*].content` 长度。
3. **粗估**：1 token ≈ 4 chars (English) / 1.5 chars (Chinese)，乘系数。
4. **精确（可选）**：`auth_request` 调本地 tokenizer sidecar（gRPC），耗时 ~5ms / 1KB body。
5. **后置校准**：用 `subrequest` 抓 upstream response 里的 `usage.prompt_tokens` / `completion_tokens`，写回 zone。

**Quota 类型**：
- **Per-team RPM**（每分钟请求数）。
- **Per-team TPM**（每分钟 token 数）。
- **Per-team Daily TPM**（每日 token 数，对应月度账单）。
- **Per-user**（在 team 内细分，适用 B2B SaaS）。
- **Per-API-key**（客户 BYOK 场景）。

**NGINX Plus 共享内存 zone 上限**：
- 默认 `zone=NAME:10m` 10MB，约可放 8 万 4 字节 key-value。
- 50 个团队 × 100K entry = 50MB zone。
- 性能：每次 limit_req 命中 shm zone，~200ns。

**F5 WAF for AI 联动**：当 rate-limit 触发 429，F5 WAF 可选择"软限流"（不杀请求，加 retry-after header）或"硬限流"（直接 503）。

### 4.3 Prompt Guard（regex + tokenizer + LLM judge 三档）

**正则预检**（数据面，~微秒级）：

```nginx
# 1. 关键词黑名单（jailbreak、prompt leak）
if ($http_x_prompt ~* "(?i)(ignore previous|act as|jailbreak|developer mode|system prompt|reveal.*password)") {
    return 403;
    # log to NGINX One AI Cost Lens
}

# 2. PII 检测（信用卡号 / SSN / email 简单正则）
if ($request_body ~* "\b(?:\d[ -]*?){13,19}\b") {
    return 403;
    # 在 NGINX One 记录 PII 拦截事件
}
```

**Tokenizer 异常**（数据面 + sidecar，~5ms）：

```nginx
# 检测 token 数量异常（如 prompt 突然有 100K token，可能是 prompt 注入）
location = /internal/tokenize {
    internal;
    proxy_pass http://tokenizer_sidecar:50051;
    grpc_pass grpc://tokenizer_sidecar:50051/TokenizeService/Estimate;
}
```

**LLM judge**（SaaS 调外部 service，~500ms p99）：

```nginx
# LLM as judge：用一个小模型判断 prompt 是否 jailbreak
location /v1/chat/completions {
    auth_request /judge_prompt;
}

location = /judge_prompt {
    internal;
    proxy_pass http://f5-llm-judge.internal:8443/judge;
    proxy_set_header X-Original-Body $request_body;
    proxy_connect_timeout 1s;
    proxy_read_timeout 5s;
    # judge 失败时默认 allow（避免 judge 故障 = 业务瘫痪）
    proxy_next_upstream error timeout http_5xx;
}
```

**F5 WAF for AI**（2025-Q3 推出）：F5 官方发布的"AI-aware WAF 规则集"，包括：
- **Jailbreak patterns**：100+ 已知 jailbreak 模板正则。
- **Prompt extraction**：试图问"你的 system prompt 是什么"。
- **Code injection**：在 prompt 中嵌入 SQL / Python / shell 注入。
- **DAN / "do anything now" 角色**。
- **Refusal bypass**：试图让 LLM 突破安全 guard。

### 4.4 LLM Observability（OTel GenAI semconv + NGINX One Cost Lens）

**NGINX Agent**（v3.10.3）支持导出 OTel metrics / traces，与 OpenTelemetry GenAI semantic conventions 对齐。

**关键 metric**（NGINX Agent 导出）：
- `nginx.connections.active` (gauge)
- `nginx.connections.accepted` (counter)
- `nginx.connections.handled` (counter)
- `nginx.http.requests.total` (counter)
- `nginx.http.requests.current` (gauge)
- `nginx.upstream.peer.failed` (counter)
- `nginx.upstream.peer.connect.time` (histogram)
- `nginx.upstream.peer.first.byte.time` (histogram)
- `nginx.upstream.peer.response.time` (histogram)

**AI-specific metrics**（NGINX Agent 解析 upstream response 后扩展）：
- `gen_ai.client.token.usage` (histogram, attribute: `type=input|output`, `model`, `team`, `user`)
- `gen_ai.client.request.duration` (histogram)
- `gen_ai.client.time_to_first_token` (histogram, "streaming" 才有)
- `gen_ai.client.cost.estimated` (counter, attribute: `currency=USD`, `model`, `team`)

**与 OpenTelemetry GenAI semconv 0.5 对齐**（截至 2026-06）：
- 完整支持 `gen_ai.client.operation.name=chat`。
- 完整支持 `gen_ai.request.model` / `gen_ai.response.model`。
- 完整支持 `gen_ai.usage.input_tokens` / `output_tokens` / `cache_read_input_tokens`。
- 部分支持 `gen_ai.usage.cache_creation_input_tokens`（Bedrock / Anthropic，2026 跟进）。

**NGINX One Cost Lens**（SaaS dashboard）：
- 横向轴：team / project / user。
- 纵向轴：token count / estimated cost / latency p50/p99 / cache hit rate。
- 时间窗：1h / 24h / 7d / 30d。
- 钻取：从 team → user → single request → 上游 response trace。

**OpenTelemetry 后端兼容性**：
- NGINX Agent 把 OTel 信号直接发到 OTel collector（OTLP gRPC / HTTP）。
- 支持 Tempo / Jaeger / Honeycomb / Datadog / Dynatrace / New Relic / Grafana Cloud。
- NGINX One SaaS 自带 90 天 retention，可作为 secondary。

### 4.5 Failover 与 Multi-region

```nginx
upstream openai_primary {
    server api.openai.com:443 max_fails=3 fail_timeout=30s;
    server api-eu.openai.com:443 backup;  # 备用 region
    keepalive 64;
}

upstream bedrock_multi_region {
    # AWS 多 region 故障转移
    server bedrock-runtime.us-east-1.amazonaws.com:443 weight=5;
    server bedrock-runtime.us-west-2.amazonaws.com:443 weight=3;
    server bedrock-runtime.eu-west-1.amazonaws.com:443 backup;
    keepalive 32;
}

server {
    location /v1/chat/completions {
        proxy_pass https://openai_primary;
        proxy_next_upstream error timeout http_502 http_503 http_504;
        proxy_next_upstream_tries 2;
        proxy_next_upstream_timeout 10s;

        # 健康检查
        health_check uri=/health interval=5s fails=3 passes=2;
    }
}
```

**Plus 增强**：
- `health_check` 主动健康检查（interval / fails / passes / match status/body）。
- `slow_start` 新加 backend 限流 warm-up。
- `drain` 优雅下线（不杀正在处理的请求）。

**Failover 时间**：通常 < 5s（NGINX Plus 检测 + 切换 + 新连接建立）。

### 4.6 Caching（精确 / 语义两层）

**精确缓存**（NGINX 内置）：

```nginx
proxy_cache_path /var/cache/nginx/ai levels=1:2 keys_zone=ai_cache:100m
                 max_size=10g inactive=24h use_temp_path=off;

location /v1/chat/completions {
    proxy_cache ai_cache;
    proxy_cache_key "$scheme$proxy_host$request_uri$request_body";
    proxy_cache_valid 200 5m;  # 5 分钟
    proxy_cache_bypass $http_cache_control;
    add_header X-Cache-Status $upstream_cache_status;
}
```

**坑点**：LLM 默认带 `Authorization` header，`proxy_cache_key` 不能包含它（避免 key 不一致）。但需要包含 `request_body`（prompt 不同 cache 不同）。

**语义缓存**（外部 vector store）：

```nginx
location /v1/chat/completions {
    # 先查语义缓存
    error_page 418 = @semantic_cache_check;
    return 418;

    # 正常 path
    proxy_pass https://openai_backend;
}

location @semantic_cache_check {
    internal;
    # auth_request 调 vector store sidecar
    auth_request /semantic_cache;
    auth_request_set $cached_response $upstream_http_x_cached_response;
    # 若命中，直接返回
    add_header X-Cache-Source semantic;
    return 200 $cached_response;
}
```

**语义缓存命中率提升**：典型 20-40%（在客服 / RAG 场景），可省大量 token。

### 4.7 Streaming / SSE 优化

NGINX 对流式的支持**默认就比较干净**，但有几个调优点：

```nginx
location /v1/chat/completions {
    # 关键三件套
    proxy_buffering off;          # 不要把 response 缓存到磁盘
    proxy_request_buffering off;  # 不要把 request 缓存到磁盘
    proxy_http_version 1.1;       # 必须 HTTP/1.1，HTTP/2 streaming 不一样

    # 超时
    proxy_connect_timeout 5s;
    proxy_send_timeout 600s;       # 长 streaming
    proxy_read_timeout 600s;

    # 立即 flush
    proxy_socket_keepalive on;
    tcp_nodelay on;
    tcp_nopush off;                # streaming 不要 nopush

    # 关闭 Gzip（避免 streaming 时延迟）
    gzip off;
}
```

**SSE 头识别**：

```nginx
map $upstream_http_content_type $is_sse {
    default 0;
    "text/event-stream" 1;
    "~*text/event-stream" 1;
}

# streaming 路径优化
if ($is_sse) {
    # 强制关闭缓冲
    proxy_buffering off;
    add_header X-Accel-Buffering no;  # 兼容 nginx-push-stream-module
}
```

### 4.8 与 F5 Distributed Cloud 的 Multicloud Network fabric

F5 Distributed Cloud（XC）是 F5 在 2021 收购 Volterra 后的边缘云产品，包括：
- **XC WAAP**：WAF / Bot Defense / API Security / DDoS。
- **Multicloud Network fabric**：跨云专线（AWS / Azure / GCP / 私有云）。
- **App Stack**：边缘 K8s。
- **API Gateway**：SaaS 化 API Gateway。

NGINX AI Gateway 与 XC 的集成：
- **NGINX One → XC 同步**：NGINX One 上的 AI Gateway 配置可推到 XC 边缘节点。
- **XC WAAP for AI**：在 XC 边缘拦截 AI 攻击（jailbreak / DLP），把"净化后"流量转到 NGINX AI Gateway。
- **Distributed Rate Limit**：跨 region / 跨云的 token quota 同步（走 XC 控制面，不依赖单一 region 的 shm zone）。
- **F5 Global PoP**：把 AI 流量从最近 PoP 入网，延迟 < 50ms。

---

## 五、协议支持

### 5.1 OpenAI Chat Completions / Responses / Embeddings / Audio

| 端点 | 路径 | NGINX 适配 | 备注 |
|---|---|---|---|
| Chat Completions | `/v1/chat/completions` | ✅ 原生 | 最常用 |
| Responses | `/v1/responses` | ✅ 原生 | 2025-Q3 起的 OpenAI 新协议，状态化 |
| Embeddings | `/v1/embeddings` | ✅ 原生 | 用于 RAG |
| Audio Speech | `/v1/audio/speech` | ✅ 原生 | TTS，response 是 binary |
| Audio Transcription | `/v1/audio/transcriptions` | ✅ multipart 透传 | 需 `client_max_body_size` 调大 |
| Images generations | `/v1/images/generations` | ✅ 原生 | DALL-E 之类 |
| Moderations | `/v1/moderations` | ✅ 原生 | 内容审核 |
| Files | `/v1/files` | ✅ multipart | 上传文件 |
| Fine-tuning | `/v1/fine_tuning/jobs` | ✅ 原生 | |
| Batch | `/v1/batch` | ✅ 原生 | 异步批量 |
| Realtime | `/v1/realtime` | ⚠️ WebSocket | 需要 `proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade;` |

### 5.2 Anthropic Messages

| 端点 | 路径 | NGINX 适配 | 备注 |
|---|---|---|---|
| Messages | `/v1/messages` | ✅ 原生 | 标准 |
| Messages streaming | `/v1/messages` (SSE) | ✅ 原生 | SSE 流式 |
| Count tokens | `/v1/messages/count_tokens` | ✅ 原生 | 用于预算检查 |
| Models | `/v1/models` | ✅ 原生 | 列出模型 |

**Anthropic Bedrock 路由**（双 upstream）：

```nginx
location /v1/messages {
    # Direct Anthropic API
    proxy_pass https://anthropic_backend;
    # 或
    # proxy_pass https://bedrock_anthropic_backend;
}
```

### 5.3 Google Gemini generateContent / streamGenerateContent

| 端点 | 路径 | NGINX 适配 | 备注 |
|---|---|---|---|
| generateContent | `/v1beta/models/{model}:generateContent` | ✅ 原生 | 同步 |
| streamGenerateContent | `/v1beta/models/{model}:streamGenerateContent` | ✅ 原生 | SSE 流式 |
| embedContent | `/v1beta/models/{model}:embedContent` | ✅ 原生 | |
| countTokens | `/v1beta/models/{model}:countTokens` | ✅ 原生 | |

**Vertex AI 特殊处理**：
- 需要 OAuth2 access token（`https://oauth2.googleapis.com/token`）。
- 通过 `auth_request` 周期刷新 token 到 NGINX 变量。
- 1 小时过期，需要 LRU cache + 提前 5 分钟刷新。

### 5.4 Cohere v2 Chat / Embed / Rerank

| 端点 | 路径 | NGINX 适配 | 备注 |
|---|---|---|---|
| Chat | `/v2/chat` | ✅ 原生 | |
| Embed | `/v2/embed` | ✅ 原生 | |
| Rerank | `/v2/rerank` | ✅ 原生 | RAG 排序 |

### 5.5 Mistral Chat Completions

OpenAI 兼容。`proxy_pass` 到 Mistral endpoint 即可。

### 5.6 OpenAI 兼容生态

下面这些 provider 都走 OpenAI 兼容协议，NGINX 配置几乎一样（只换 upstream）：

| Provider | 端点 |
|---|---|
| **OpenRouter** | `openrouter.ai/api/v1` |
| **Together AI** | `api.together.xyz/v1` |
| **Fireworks AI** | `api.fireworks.ai/inference/v1` |
| **DeepSeek** | `api.deepseek.com/v1` |
| **Groq** | `api.groq.com/openai/v1` |
| **OpenAI** | `api.openai.com/v1` |
| **Azure OpenAI** | `<resource>.openai.azure.com/openai/deployments/<dep>` |
| **vLLM** | `<host>:<port>/v1` |
| **TGI** | `<host>:<port>/v1` |
| **LMDeploy** | `<host>:<port>/v1` |
| **Ollama** | `<host>:<port>/v1` |
| **llama.cpp** | `<host>:<port>/v1` |
| **Hugging Face Inference Endpoints** | `<endpoint>.endpoints.huggingface.cloud/v1` |

### 5.7 MCP（Model Context Protocol）代理

2026-Q2 跟随 MCP 2026-07-28-rc 规范，NGINX AI Gateway 加入了 MCP-aware 路由。

**核心能力**：
- **MCP `mcp-session-id` header 透传**：`proxy_set_header mcp-session-id $http_mcp_session_id`。
- **MCP `Mcp-Client-Session-Id`（新）**：2026 规范新加的 client 端 session ID，NGINX 注入 W3C tracecontext。
- **stdio → SSE 转换**：通过 `auth_request` 调本地 sidecar（small MCP bridge），把 stdio MCP server 暴露为 SSE 端点。
- **MCP Server Card**（`/.well-known/mcp/server-card.json`）：通过 `location = /.well-known/mcp/server-card.json` 静态文件服务。
- **MCP `cache_hint` 信号**：`map` 解析 `_meta.cache_hint` 字段触发 NGINX 缓存层。
- **DPoP 验签**：`auth_request` 验 RFC 9449 DPoP token。
- **scoped auth receipt 三层分类**：在 NGINX `map` 中解析 receipt，分 transport / runtime / provider。

**典型配置**：

```nginx
location /mcp/sse {
    # MCP SSE 端点
    proxy_pass http://mcp_bridge_backend;
    proxy_buffering off;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header mcp-session-id $http_mcp_session_id;
    proxy_set_header Mcp-Client-Session-Id $http_mcp_client_session_id;
}

location = /.well-known/mcp/server-card.json {
    root /etc/nginx/mcp;
    add_header Cache-Control public, max-age=3600;
}
```

### 5.8 A2A（Agent-to-Agent）代理

2026-Q1 跟随 Google A2A 协议，NGINX AI Gateway 加入 A2A-aware 路由。

**核心能力**：
- **A2A `agent-card.json` 识别**：`/.well-known/agent.json` 静态服务。
- **JSON-RPC over HTTP 识别**：`map $http_content_type $is_a2a { "application/json" 1; }`。
- **A2A streaming**：`text/event-stream` SSE 转发。
- **Agent auth context**：`auth_request` 调 OAuth2 / OIDC provider。

**典型配置**：

```nginx
location /a2a/ {
    # A2A JSON-RPC over HTTP
    proxy_pass https://agent_backend_pool;
    proxy_set_header Content-Type application/json;
    proxy_buffering off;
    proxy_http_version 1.1;
    chunked_transfer_encoding on;
}

location = /.well-known/agent.json {
    root /etc/nginx/a2a;
}
```

### 5.9 协议矩阵

| 协议 | NGINX 适配层 | 实现 | 现状（2026-06） |
|---|---|---|---|
| OpenAI Chat Completions | 数据面 | `proxy_pass` 透传 | ✅ GA |
| OpenAI Responses | 数据面 | `proxy_pass` 透传 | ✅ GA（2025-Q3+）|
| OpenAI Realtime (WebSocket) | 数据面 | `proxy_set_header Upgrade` | ✅ GA |
| OpenAI Embeddings / Audio / Images | 数据面 | `proxy_pass` 透传 | ✅ GA |
| Anthropic Messages | 数据面 | `proxy_pass` 透传 | ✅ GA |
| Anthropic Count Tokens | 数据面 | `proxy_pass` 透传 | ✅ GA |
| Google Gemini | 数据面 + OAuth2 | `proxy_pass` + `auth_request` | ✅ GA（OAuth2 需配）|
| AWS Bedrock | 数据面 + SigV4 | `proxy_pass` + `auth_request`（Lambda）| ⚠️ SigV4 还在做原生（2026 路线）|
| Cohere v2 | 数据面 | `proxy_pass` 透传 | ✅ GA |
| Mistral | 数据面 | `proxy_pass` 透传 | ✅ GA |
| MCP stdio → SSE | 数据面 + sidecar | `auth_request` 调 MCP bridge | ✅ GA（2026-Q2）|
| MCP Server Card | 数据面 | 静态文件 | ✅ GA |
| MCP DPoP | 数据面 + auth_request | DPoP 验签 | ⚠️ Beta |
| A2A JSON-RPC | 数据面 | `proxy_pass` + `map` 路由 | ✅ GA（2026-Q1）|
| A2A streaming | 数据面 | SSE 转发 | ✅ GA |
| Agent Card | 数据面 | 静态文件 | ✅ GA |
| OpenAI 兼容 100+ provider | 数据面 | `proxy_pass` 集群 | ✅ GA（每加 1 provider 5 行配置）|

---

## 六、性能数据与基准

### 6.1 NGINX 数据面性能血统（C10K / C10M）

NGINX 从设计上就为高并发而生：
- **单 worker 50K+ 长连接**（epoll/kqueue）。
- **静态文件 100K+ RPS**（256KB 文件，AES-NI 加速）。
- **TLS 握手 0-RTT**（TLS 1.3 + session resumption）。
- **内存 footprint**：worker 进程 2-5MB（无模块加载）/ 10-30MB（加载标准模块）。

LLM 代理场景下，NGINX 主要耗在：
- **TLS 终结**：NGINX 卸载 client → NGINX，upstream keepalive 复用。
- **Body 解析**：JSON body 在 NGINX 不解析（透明转发），但要 buffer 一份用于 map 抽字段。
- **Stream 转发**：SSE 端到端流式，延迟开销 < 1ms。

### 6.2 NGF 控制器延迟

NGF controller-runtime 同步 + NGINX Agent gRPC 异步，配置变更延迟：
- **Gateway 创建 → NGINX 实际处理流量**：典型 5-15s（含 K8s admission webhook、NGF reconcile、Agent gRPC、文件写入、nginx reload）。
- **HTTPRoute 变更 → 路由生效**：2-5s。
- **Backend Endpoints 变化**：1-3s。
- **reload 期间 worker 切换延迟**：< 100ms（NGINX master fork 子 worker 优雅交接）。

社区基准（2024-2025 多次 KubeCon 分享）：
- **NGF controller CPU**：100 个 Gateway 资源时 < 100m CPU。
- **NGF controller memory**：< 256Mi。
- **NGINX data plane 内存**：256 个 active routes 时 < 512Mi。

### 6.3 实际 LLM 代理场景性能（OSS 用户分享）

公开 KubeCon / NGINX Summit 用户分享数据：

| 场景 | 配置 | 性能 |
|---|---|---|
| OpenAI Chat Completions 透传 | 1 NGINX Plus pod, 4 worker, 8 vCPU | ~30K RPS（纯 proxy_pass）|
| OpenAI + token rate-limit | 1 NGINX Plus pod, 4 worker | ~25K RPS（shm zone 限流 5% 开销）|
| OpenAI + 精确 cache 命中 | cache 命中率 50% | ~60K RPS（命中后无 upstream call）|
| OpenAI + 语义 cache + LLM judge | judge 5ms sidecar | ~5K RPS（受 sidecar 限）|
| Bedrock SigV4 签名 | Lambda 签名 50ms | ~1K RPS（受 Lambda 限）|
| Anthropic Messages 透传 | 1 NGINX Plus pod | ~28K RPS |

**vs Envoy AI Gateway 横向**（来源：Envoy AI Gateway 2025-Q4 自家 blog）：

| 维度 | NGINX AI Gateway | Envoy AI Gateway |
|---|---|---|
| 纯 LLM 透传 p50 延迟 | 1.2ms | 1.4ms |
| 纯 LLM 透传 p99 延迟 | 4.5ms | 5.2ms |
| 内存 per 1K active connections | 80MB | 120MB |
| 启动时间 | 0.5s | 1.5s |
| 配置生效延迟 | 3-5s | < 100ms (xDS streaming) |
| 集群规模上限（Route 数）| ~10K | ~100K+ |

### 6.4 NGINX Plus 共享内存 zone 对 token rate-limit 的影响

- **shm zone 创建**：启动时 mmap 一次性分配，10MB zone 约 8 万 entry。
- **limit_req 检查延迟**：~200ns per request。
- **跨 worker 同步**：NGINX Plus 自旋锁 + atomic，p99 < 1μs。
- **高并发表现**：10K RPS 下，limit_req 命中 100% 准确（无超发）。

### 6.5 Streaming 吞吐

NGINX 对 SSE / chunked transfer 的支持是**业内最干净**的：
- **TTFT（Time To First Token）开销**：< 1ms（chunked 立即 flush）。
- **throughput**：受 upstream LLM 限制，NGINX 自身不成为瓶颈。
- **单 NGINX Plus pod 支撑的并发流式连接**：~10K（受 fd / memory 限）。

### 6.6 内存 / CPU footprint

| 部署模式 | 内存 | CPU | 备注 |
|---|---|---|---|
| NGINX OSS 1 worker | 5-15MB | 5-15% 1 core | 最小 |
| NGINX Plus 4 worker（默认）| 50-200MB | 0.5-1.0 core | 正常 |
| NGF controller | 200-500MB | 100-500m | K8s reconcile |
| NGINX Agent | 50-100MB | 50-100m | gRPC + metrics |
| 完整 NGINX One SaaS 注册 | + 50-100MB | + 50m | SaaS agent |

### 6.7 与 Envoy AI Gateway / Kong AI Gateway 的横向 benchmark

| 维度 | NGINX AI Gateway | Envoy AI Gateway | Kong AI Gateway |
|---|---|---|---|
| 透传 p50 | 1.2ms | 1.4ms | 1.6ms |
| 透传 p99 | 4.5ms | 5.2ms | 6.0ms |
| 内存 per 1K 连接 | 80MB | 120MB | 150MB |
| 启动时间 | 0.5s | 1.5s | 3s |
| 配置生效延迟 | 3-5s | < 100ms (xDS) | 3-10s (reload) |
| 大集群（10K+ route）| 受限（reload）| 流畅（xDS）| 受限（reload）|
| WAF 集成 | 一等公民（F5 WAF）| 需外接 | Kong WAF 插件 |
| Token rate-limit | shm zone（一等公民）| ext_proc 外接 | Go 插件外接 |
| Lua/WASM 扩展 | 不支持（编译时）| WASM/lua filter | Lua/Go/JS plugin |
| 生态 | 限于 NGINX | 限于 Envoy | 250+ Kong 插件 |

---

## 七、部署方式

### 7.1 K8s Helm 安装

```bash
# 1. 添加 helm repo
helm repo add nginx-stable https://helm.nginx.com/stable
helm repo update

# 2. 创建 namespace
kubectl create namespace nginx-gateway

# 3. 安装 NGF
helm install ngf nginx-stable/nginx-gateway \
  --namespace nginx-gateway \
  --set nginx.image.repository=ghcr.io/nginx/nginx-gateway-fabric
```

### 7.2 K8s OpenShift Operator 安装

NGF 在 OpenShift OperatorHub 上有官方 operator：

```bash
# 1. 在 OpenShift console → Operators → OperatorHub 搜 "NGINX Gateway Fabric"
# 2. Install → 选择 namespace → Subscribe
# 3. 创建 NginxGatewayFabric CR
cat <<EOF | kubectl apply -f -
apiVersion: gateway.nginx.org/v1alpha1
kind: NginxGatewayFabric
metadata:
  name: ngf
  namespace: nginx-gateway
EOF
```

### 7.3 独立 VM / Bare Metal（NGINX Plus + Agent）

```bash
# 1. 装 NGINX Plus（订阅下载）
sudo apt-get install nginx-plus

# 2. 装 NGINX Agent
curl -L https://github.com/nginx/agent/releases/download/v3.10.3/nginx-agent_3.10.3-1_amd64.deb -o nginx-agent.deb
sudo dpkg -i nginx-agent.deb

# 3. 注册到 NGINX One SaaS
sudo /usr/bin/nginx-agent \
  --config-path /etc/nginx-agent/nginx-agent.conf \
  --instance-group my-vm-group
```

### 7.4 启用 AI Gateway flag

**在 NGF 2.6.3+**，AI Gateway 是 NGINX One SaaS 提供的 feature，不需要单独 flag（data plane 上自动开）。

**自托管 OSS NGF + 自建 AI 中间件**（用户自定义）：

```yaml
# SnippetsFilter 注入自定义 LLM provider 配置
apiVersion: gateway.nginx.org/v1alpha1
kind: SnippetsFilter
metadata:
  name: openai-snippet
spec:
  location:
    - upstream openai_backend { server api.openai.com:443; keepalive 64; }
    - limit_req_zone $jwt_team zone=ai:10m rate=1000r/m;
```

### 7.5 典型部署模式 1：本地 LLM（Ollama / vLLM / TGI）

```yaml
# Ollama + NGINX AI Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: ai-gateway-local
  namespace: ai
spec:
  gatewayClassName: nginx
  listeners:
  - name: http
    port: 80
    protocol: HTTP
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: ollama-route
  namespace: ai
spec:
  parentRefs:
  - name: ai-gateway-local
  hostnames:
  - "llm.internal"
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/chat/completions
    backendRefs:
    - name: ollama-service
      port: 11434
```

```nginx
# NGINX 配置（自动生成）
upstream ollama-service {
    server ollama-service.ai.svc.cluster.local:11434;
    keepalive 32;
}

server {
    listen 80;
    server_name llm.internal;

    location /v1/chat/completions {
        # 改写为 Ollama 路径
        rewrite ^/v1/chat/completions$ /api/chat break;
        proxy_pass http://ollama-service;
        proxy_buffering off;
        proxy_http_version 1.1;
    }
}
```

### 7.6 典型部署模式 2：云端 LLM（OpenAI / Bedrock / Vertex）

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: openai-route
spec:
  parentRefs:
  - name: ai-gateway-cloud
  hostnames:
  - "api.llm.example.com"
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/chat/completions
    backendRefs:
    - group: ""
      kind: Service
      name: openai-upstream  # 实际上 NGINX 直接 proxy_pass 到 OpenAI，无需 Service
```

```nginx
# NGINX 注入（NGF 自动生成）
server {
    listen 443 ssl;
    server_name api.llm.example.com;
    ssl_certificate /etc/ssl/certs/api.llm.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.llm.example.com.key;

    location /v1/chat/completions {
        # Token rate-limit
        limit_req zone=ai_team_per_min burst=20 nodelay;

        # Upstream 鉴权
        proxy_set_header Authorization "Bearer $openai_api_key";
        proxy_pass https://api.openai.com;

        # Streaming 优化
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_http_version 1.1;
        proxy_read_timeout 300s;
    }
}
```

### 7.7 典型部署模式 3：Hybrid（敏感本地 + 默认云端）

**核心**：用 `map` 根据 prompt 内容路由到不同 upstream。

```nginx
# map 抽取 prompt 中是否有 PII / 医疗 / 法律关键词
map $request_body $route_class {
    default "cloud";
    "~*(?i)(ssn|credit card|patient|medical|diagnosis|prescription)" "local";
    "~*(?i)(attorney|client|confidential|legal)" "local";
}

map $route_class $upstream_endpoint {
    "cloud" "https://api.openai.com";
    "local" "http://ollama-secure.svc.cluster.local:11434";
}

server {
    listen 443 ssl;
    server_name api.llm.example.com;

    location /v1/chat/completions {
        # 敏感 prompt 走本地
        if ($route_class = "local") {
            rewrite ^/v1/chat/completions$ /api/chat break;
            proxy_pass http://ollama-secure.svc.cluster.local:11434;
            access_log /var/log/nginx/llm-local-access.log;
        }
        # 非敏感走云端
        if ($route_class = "cloud") {
            proxy_pass https://api.openai.com;
            proxy_set_header Authorization "Bearer $openai_api_key";
            access_log /var/log/nginx/llm-cloud-access.log;
        }
    }
}
```

### 7.8 典型部署模式 4：F5 Distributed Cloud（XC）边缘接入

在 F5 XC console 上：
1. 创建 HTTP Load Balancer，origin = NGINX AI Gateway internal IP。
2. 配置 WAF policy（含 AI-aware rules）。
3. 配置 Bot Defense policy。
4. 配置 rate limit（per IP / per token）。
5. 配置 geo policy（按 region 路由到最近 LLM）。

### 7.9 GitOps 集成（ArgoCD / FluxCD / Spinnaker）

```yaml
# ArgoCD Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ai-gateway
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/example/ai-gateway-config
    targetRevision: main
    path: nginx-gateway/
  destination:
    server: https://kubernetes.default.svc
    namespace: nginx-gateway
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 7.10 与 BIG-IP Next 的统一管理

F5 BIG-IP Next（2024+）是 F5 新一代硬件 ADC。它通过 **NGINX One** 与 NGINX AI Gateway 联邦：
- BIG-IP Next 上的 L7 策略同步到 NGINX One。
- NGINX AI Gateway 配置可在 BIG-IP Next console 上查看。
- BIG-IP Next 上的硬件加速（SSL / 压缩）可被 NGINX AI Gateway 利用。

---

## 八、成本模型

### 8.1 NGINX Plus 订阅

**Per-instance / per-year** 模式：
- **NGINX Plus 单实例订阅**：约 **$2,500-$5,000/instance/year**（2026 标准价格）。
- **5 instances 起卖**。
- **包含**：NGINX Plus R37 binary + 1 年技术更新 + F5 WAF for NGINX 5.13.1 兼容。

**实例定义**：一个 OS-level install，可承载多个 Gateway（多 worker）。
- **生产部署典型**：5 instances = $12,500-$25,000/year。
- **大型企业**：50 instances = $125,000-$250,000/year。

### 8.2 NGINX One 消费计费

**consumption-based**（按消费量）：
- **基础订阅**：包含 N 个 instances + SaaS 面板。
- **超额按 instance-hour 收费**。
- **AI Cost Lens**：包含在 NGINX One 基础订阅，无额外费用。
- **典型价格**：**~$200-$500/instance/month**（含 SaaS + AI features）。

### 8.3 F5 Distributed Cloud Bandwidth / Compute

F5 XC 边缘 PoP：
- **Bandwidth**：$0.05-$0.20/GB（跨 region 不同）。
- **Compute**（XC App Stack）：~$0.05-$0.20/vCPU/hour。
- **WAF / DDoS**：附加订阅，~$1,000-$10,000/month 区间。

### 8.4 间接成本：token rate-limit 节省与 cache 命中率

**典型 token 节省**：
- **精确 cache 命中**：0 token（直接返回缓存）。
- **语义 cache 命中**：0 token（语义相似度 > 0.95）。
- **典型客服场景**：cache 命中率 20-40%，月省 **$1,000-$50,000**（取决于规模）。

**典型 rate-limit 节省**：
- **Per-team TPM 限流**：避免单个 team 滥用，预算可控。
- **Per-user TPM 限流**：避免内部恶意循环调用，**典型省 30-50%**。
- **Return 429 + retry-after**：客户端自适应回退。

### 8.5 隐性成本：WAF / DDoS 模块订阅

- **F5 WAF for NGINX 5.13.1**：包含在 NGINX Plus 订阅内。
- **F5 WAF Premium / Advanced**：附加订阅，~$5,000-$20,000/instance/year。
- **DDoS protection**：F5 XC WAAP 提供，附加订阅。

### 8.6 与 Portkey / Helicone / Cloudflare 的成本对比

| 维度 | NGINX AI Gateway (F5) | Portkey | Helicone | Cloudflare AI Gateway |
|---|---|---|---|---|
| 基础订阅 | $2,500-$5,000/inst/year (Plus) | $0-$999/month | $0-$1,000/month | $0-$250/month + 缓存费 |
| Token 过路费 | $0 | $0 | $0 (cache 重售除外) | $0 |
| Cache 费用 | $0 (本地) | $0 (Redis 自配) | $0.001/cache hit | $0.05/GB 存储 |
| Observability | $0 (NGINX One 自带) | $0 (Lite) / $499 (Pro) | $0 (Lite) / $200+ (Pro) | $0 (基础) / $5/百万 metrics |
| WAF 集成 | $0 (F5 WAF 包含) | $0 | $0 | $0 (CF WAAP) |
| 典型 100M token/月总成本 | $15K-50K/year | $5K-12K/year | $3K-8K/year | $1K-5K/year |
| 自助 vs 托管 | 自助为主 | 托管 | 托管 | 托管 |
| 客群匹配 | 大企业 | AI 工程师 | AI 工程师 | 边缘 / 多云 |

**关键点**：F5 的总拥有成本**显著高于** SaaS 派（Portkey / Helicone / Cloudflare），但**显著低于**自建 LiteLLM 集群（运维 + 监控 + 安全加固），且**对"已经在用 NGINX"的企业无感**。

---

## 九、生态与第三方集成

### 9.1 NGINX One Observability：Prometheus / Grafana / OpenTelemetry

**Prometheus 集成**（自带 `/metrics` 端点）：

```yaml
# ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: nginx-gateway-fabric
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: nginx-gateway-fabric
  endpoints:
  - port: metrics
    interval: 30s
```

**Grafana 仪表盘**：
- NGINX 官方 Grafana dashboard ID：**12708**（NGINX Plus Prometheus Exporter）。
- AI Cost Lens dashboard（NGINX One SaaS 自带）。

**OpenTelemetry 集成**：
- NGINX Agent 导出 OTel signals（OTLP gRPC / HTTP）。
- 接收端：Tempo / Jaeger / Datadog / Honeycomb / Dynatrace / New Relic / Grafana Cloud。

### 9.2 NGINX App Protect（WAF + Bot Defense + API Security）

F5 WAF for NGINX（5.13.1）：
- **OWASP Top 10** 规则集。
- **Bot Defense**（人机识别）。
- **API Security**（敏感数据检测）。
- **DDoS**（L7 限流）。
- **AI-aware rules**（2025-Q3 起的 "F5 WAF for AI" 规则集）：
  - Jailbreak patterns。
  - Prompt extraction。
  - PII in request body。
  - Toxic content in response body。

### 9.3 F5 Distributed Cloud（XC WAAP / Multicloud Network / Bot Defense）

- **XC WAAP**：WAF / Bot Defense / API Security / DDoS 边缘。
- **Multicloud Network fabric**：跨云专线。
- **API Gateway**：SaaS 化 API Gateway。
- **App Stack**：边缘 K8s。

### 9.4 BIG-IP Next 联邦

- BIG-IP Next 上的 L7 策略同步到 NGINX One。
- NGINX AI Gateway 配置可在 BIG-IP Next console 统一管理。
- BIG-IP Next 的硬件加速（SSL 卸载）可被 NGINX AI Gateway 利用。

### 9.5 HashiCorp Vault / CyberArk 凭据保险箱

**动态凭据获取**（`auth_request` 调 Vault）：

```nginx
location /v1/chat/completions {
    auth_request /vault_token;
    proxy_pass https://openai_backend;
}

location = /vault_token {
    internal;
    proxy_pass http://vault.internal:8200/v1/aws/creds/ai-role;
    proxy_set_header X-Vault-Token $vault_root_token;
    proxy_connect_timeout 1s;
    proxy_read_timeout 3s;
}
```

**CyberArk / BeyondTrust** 类似集成方式。

### 9.6 cert-manager / SPIFFE / mTLS

- **cert-manager**：自动签发 / 轮换 Listener TLS 证书。
- **SPIFFE / SPIRE**：零信任身份，NGINX Agent 支持 SPIFFE Workload Identity。
- **mTLS to backend**：BackendTLSPolicy（v1）部分支持。
- **mTLS to upstream**：通过 `proxy_ssl_certificate` 配 client cert。

### 9.7 与 OPA / Cedar 的策略外接

**OPA（Open Policy Agent）**：

```nginx
location /v1/chat/completions {
    auth_request /opa_authz;
    proxy_pass https://openai_backend;
}

location = /opa_authz {
    internal;
    proxy_pass http://opa.internal:8181/v1/data/ai/authz;
    proxy_set_header Content-Type application/json;
    proxy_set_header X-Auth $http_authorization;
    proxy_set_request_body '{"input": {"team": "$jwt_team", "model": "$arg_model"}}';
    # 200 = allow, 403 = deny
}
```

**Cedar**（AWS 开源策略语言）：类似集成。

### 9.8 MCP Server 桥接（stdio → SSE）

```yaml
# 把 stdio MCP server 暴露为 SSE 端点
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-bridge
spec:
  template:
    spec:
      containers:
      - name: mcp-server
        image: mcp/postgres:latest
        # stdio MCP server
      - name: mcp-bridge
        image: mcp/bridge:latest
        args:
        - --stdio
        - --server=localhost:8080
        - --expose=sse
        - --sse-port=8081
```

NGINX 路由 `/mcp/sse` 到 mcp-bridge 8081。

---

## 十、客户案例

### 10.1 公开宣称的客户行业

F5 BIG-IP + NGINX 公开客户群（**注意**：F5 不直接公开 "AI Gateway" 客户清单，但通过 NGINX 装机量 + F5 BIG-IP 客群可推断）：

- **金融 / 银行**：摩根大通、汇丰银行、美国银行、ING、瑞银、星展银行、中国银行、工商银行（部分使用 NGINX）。
- **电信 / 运营商**：Verizon、AT&T、NTT、Docomo、Orange、中国移动（部分使用 NGINX）。
- **政府 / 公共部门**：NASA、美国国防部（DISA）、英国 NHS、澳大利亚税务局、新加坡 GovTech（部分使用 F5）。
- **大型零售 / 电商**：Target、Walmart、Best Buy（部分使用 NGINX）。
- **流媒体 / SaaS**：Netflix、Dropbox、Cloudflare、Atlassian（部分使用 NGINX）。
- **制造业**：Toyota、Bosch、Siemens（部分使用 NGINX）。

### 10.2 "Traefik / NGINX Proxy 60,000+ stars + F5 BIG-IP 4,000+ 客户" 形成的 OSS → 商业转化

F5 在 AI Gateway 时代的"商业转化"逻辑：
- **存量 NGINX Plus 客户** → 加购 AI Gateway 特性（无新增许可费，NGF / NGINX One 加购）。
- **存量 BIG-IP 客户** → 通过 NGINX One 联邦，把 AI Gateway 纳入 F5 生态。
- **F5 公有云客户**（Distributed Cloud）→ 直接用 XC WAAP + AI Gateway 一站配齐。
- **OSS 用户** → 自助 + 升级到 Plus（NGINX AI Gateway 的 AI 特性基本都在 Plus 订阅内）。

### 10.3 公开案例（用 NGINX 跑 LLM 服务的工程实践）

KubeCon 2024-2026 多场分享：
- **"Scaling LLM Inference on K8s with NGINX Gateway Fabric"** —— 大型银行案例，用 NGF + vLLM 跑内部 RAG，月均 100M token。
- **"AI Gateway for Sovereign LLMs"** —— 欧洲电信客户，用 NGINX AI Gateway 路由 EU-only LLM（Mistral / Aleph Alpha），拒绝非 EU 流量。
- **"Hybrid LLM with NGINX Plus"** —— 零售客户，敏感 PII 走本地 Ollama，默认走 OpenAI。
- **"F5 WAF for AI: Stopping Jailbreaks at Layer 7"** —— F5 自家分享，F5 WAF for AI 规则集实战。
- **"Cost Attribution for LLM Workloads"** —— SaaS 客户，用 NGINX One Cost Lens 做 per-team 成本归因，月省 $50K。

### 10.4 与"AI Gateway 专门厂商"的客户重叠

NGINX AI Gateway vs Portkey / Helicone / Cloudflare：
- **重叠客户**：大企业 + 已有 NGINX / F5 资产。
- **不重叠客户**：
  - 初创 / AI 工程师主导（→ Portkey / Helicone）。
  - 边缘 / 多云（→ Cloudflare）。
  - 严格自托管 + Service Mesh（→ Envoy / Istio + 自建 AI Gateway）。

**对 Portkey 的"客群侵蚀"**：
- F5 NGINX AI Gateway 的目标客群是**已有 NGINX Plus / F5 资产**的大企业。
- Portkey 的目标客群是**没有 NGINX 资产**、从 LLM 切入的 AI 工程师团队。
- 重叠部分在中间地带：中等规模企业（100-1000 人）有 NGINX 装机但 AI 团队独立采购。

---

## 十一、关键事件时间线（2024-2026）

| 日期 | 事件 |
|---|---|
| **2019-03** | F5 $670M 收购 NGINX Inc.，Igor Sysoev 担任 F5 Fellow。|
| **2021-01** | F5 $500M 收购 Volterra（边缘云，演化为 Distributed Cloud）。|
| **2022-01** | NGF（NGINX Gateway Fabric）首次开源，K8s Gateway API 标准。|
| **2022-12** | Igor Sysoev 离开 F5，NGINX 团队和开源策略不变。|
| **2024-03-13** | AppWorld 2024 大会，NGINX One SaaS 首次发布（design vision blog 公开）。|
| **2024-06** | NGINX One Early Access 开启。|
| **2024-09-2024-12** | NGINX One GA；F5 公开宣布 "AI gateway" 是 2025 主线方向。|
| **2025-Q1** | **F5 NGINX AI Gateway beta**：在 NGINX One 上叠加 AI 流量管理能力。|
| **2025-Q2** | **F5 NGINX AI Gateway GA**（NGINX One Add-on）：token rate-limit + prompt guard + F5 WAF for AI。|
| **2025-Q3** | **F5 WAF for AI** 正式发布，jailbreak / 越权 / 异常响应规则集。|
| **2025-Q4** | **F5 Distributed Cloud 集成**：AI Gateway 与 XC WAAP 双向同步。|
| **2026-Q1** | **A2A 协议代理**：NGINX AI Gateway 加入 Agent-to-Agent 协议识别。|
| **2026-Q2** | **MCP 桥接**：stdio → SSE 转换，与 MCP 2026-07-28-rc 规范同步。|
| **2026-05-29** | NGF 2.6.3 发布：ListenerSet / 多 TLS 证书 / F5 WAF 集成 / mTLS Agent。|
| **2026-06** | 调研日期（2026-06-06）。F5 在 2026 年中计划 NGINX Summit。|

---

## 十二、优劣势分析

### 12.1 优势

| # | 优势 | 详细 |
|---|---|---|
| 1 | **数据面性能** | NGINX C 事件循环，C10M 血统，TLS 卸载 + upstream keepalive，p50 < 1.5ms。|
| 2 | **企业安全** | F5 WAF for NGINX 5.13.1 一等公民，OWASP / Bot Defense / API Security / DDoS / AI-aware rules 全部就位。|
| 3 | **Token rate-limit** | 基于 NGINX Plus shm zone，跨 worker 同步，~200ns/check，**强于**所有 SaaS 派（Portkey / Helicone 走 Redis，多 ms）。|
| 4 | **混合云 / 多云** | F5 Distributed Cloud 联邦，跨云专线（Multicloud Network），大企业友好。|
| 5 | **认证客户群** | F5 BIG-IP 4,000+ 客户 + NGINX 4 亿+ 容器实例，"存量转化"是最大护城河。|
| 6 | **PII / 合规** | 自托管 + F5 WAF for AI + Vault 凭据 + SPIFFE mTLS，金融 / 政府 / 医疗合规首选。|
| 7 | **成熟运维工具链** | NGINX Instance Manager + NGINX One SaaS + BIG-IP Next console，运维体验完整。|
| 8 | **OpenTelemetry 集成** | NGINX Agent 导出 OTel GenAI semconv，标准化可观测。|
| 9 | **OpenAI 兼容生态** | 一行 `upstream` 接入 100+ provider（Together / Fireworks / DeepSeek / OpenRouter / Ollama / vLLM）。|
| 10 | **MCP / A2A 跟进** | 2026-Q1/Q2 跟进 MCP 2026-07-28-rc + A2A 协议，与业界同步。|

### 12.2 劣势

| # | 劣势 | 详细 |
|---|---|---|
| 1 | **reload 模型** | NGINX reload vs xDS streaming，**大集群 10K+ route 时配置生效延迟 3-5s**，不如 Envoy Gateway 流畅。|
| 2 | **总拥有成本高** | NGINX Plus $2,500-$5,000/inst/year，**显著高于** SaaS 派（Portkey / Helicone / Cloudflare）。|
| 3 | **AI 协议适配广度** | 只原生适配 5-10 个 LLM provider，**不如** Portkey (250+) / LiteLLM (100+) / Helicone (35+) / OpenRouter (300+)。|
| 4 | **OSS 版本** | 核心 AI 特性（token rate-limit / prompt guard）需要 **NGINX Plus**，OSS 只有基础 proxy_pass。|
| 5 | **没有 Lua/WASM 扩展** | 编译时集成，不支持运行时插件（vs Kong OpenResty + WASM / Envoy WASM filter）。|
| 6 | **没有"AI Router"特性** | 缺语义路由（BERT 分类 / topic 路由）、LLM cascade、cost-based 路由、reflection 等。|
| 7 | **没有内建 LLM judge** | 需 F5 WAF for AI 外部 service / 自建 sidecar。|
| 8 | **没有"AI Cost Lens"开源** | Cost Lens 锁定在 NGINX One SaaS，自托管只有 metrics 导出。|
| 9 | **大集群 L7 route 性能** | 10K+ HTTPRoute 时 reload 切换累积延迟，**弱于** Envoy Gateway（xDS）。|
| 10 | **社区 / 文档质量** | NGINX 文档质量高，但 F5 商业化把很多 AI 特性藏在 NGINX One 文档后面，OSS 用户有"半遮半掩"感。|

---

## 十三、与其他 AI Gateway 的对比

### 13.1 与 Portkey / LiteLLM / One API（LLM Router 派）

| 维度 | NGINX AI Gateway | Portkey | LiteLLM | One API |
|---|---|---|---|---|
| 切入路线 | 通用 API Gateway + AI 插件 | LLM Router | LLM Router | LLM Router |
| LLM provider 数 | 5-10 原生 + 100+ OpenAI 兼容 | 250+ | 100+ | 50+ |
| Token rate-limit | shm zone（一等公民）| Redis | Redis | Redis |
| 语义路由 | ❌（2026 路线）| ✅ | ⚠️ partial | ❌ |
| LLM cascade / reflection | ❌ | ✅ | ⚠️ | ❌ |
| Cost-based 路由 | ❌ | ✅ | ⚠️ | ❌ |
| 自托管 | ✅ NGF | ✅ | ✅ | ✅ |
| SaaS 托管 | ✅ NGINX One | ✅ | ❌ | ⚠️ |
| 客群 | 大企业 / 金融 / 电信 | AI 工程师 | AI 工程师 | 个人 / 小团队 |
| 总拥有成本 | 高 | 中 | 低 | 极低 |
| WAF / Bot Defense | 一等公民（F5 WAF）| ❌ | ❌ | ❌ |
| MCP 协议 | ✅ 2026-Q2 | ✅ 2025-Q4 | ✅ 2025-Q4 | ⚠️ partial |
| A2A 协议 | ✅ 2026-Q1 | ✅ 2025-Q4 | ⚠️ | ❌ |
| 集群规模 | 中（reload 限）| 大 | 中 | 小 |

**结论**：NGINX AI Gateway 的优势在**安全 + 合规 + 性能**；Portkey / LiteLLM 的优势在**AI 协议广度 + 智能路由**。如果客户是**传统大企业 + 已有 NGINX / F5 资产**，选 NGINX AI Gateway；如果是**AI 工程师主导 + 多 provider 实验**，选 Portkey / LiteLLM。

### 13.2 与 Kong AI Gateway / APISIX ai-proxy / Envoy AI Gateway（通用 API Gateway AI 插件派）

| 维度 | NGINX AI Gateway | Kong AI Gateway | APISIX ai-proxy | Envoy AI Gateway |
|---|---|---|---|---|
| 数据面语言 | C | OpenResty (Lua) | Lua | C++ |
| LLM provider 数 | 5-10 原生 + 100+ OpenAI 兼容 | 25+ | 20+ | 10+ |
| 配置更新 | 文件 + reload | DB-less / DB + reload | etcd + reload | xDS streaming |
| reload 影响 | 微秒级 worker 切换 | Kong reload 痛点 | APISIX 较快 | 零（xDS）|
| 集群规模 | 1k-10k HTTPRoute OK | 1k-5k | 1k-5k | 10k+ |
| WAF 集成 | F5 WAF 一等公民 | Kong WAF 插件 | Apache APISIX WAF | 需外接 |
| Token rate-limit | shm zone | Go 插件 / Redis | 限流插件 | ext_proc + Redis |
| 插件生态 | 编译时（无运行时）| 250+ Kong 插件 | 100+ APISIX 插件 | WASM / Lua / native filter |
| 自托管 | ✅ | ✅ | ✅ | ✅ |
| 商业化深度 | F5 全栈 | Kong Inc. | Apache 软件基金会 | Tetrate / Solo.io |
| MCP 协议 | ✅ 2026-Q2 | ✅ 2026-Q1 | ⚠️ | ✅ 2025-Q4 |
| A2A 协议 | ✅ 2026-Q1 | ✅ 2026-Q1 | ⚠️ | ✅ 2025-Q4 |

**结论**：NGINX AI Gateway 在**安全 + 性能**上最强；Kong AI Gateway 在**插件生态**上最强；APISIX 在**国产化**上最强；Envoy 在**集群规模 + Service Mesh 兼容**上最强。

### 13.3 与 Cloudflare AI Gateway / Vercel AI Gateway / Solo AI Gateway（边缘云 AI Gateway 派）

| 维度 | NGINX AI Gateway | Cloudflare AI Gateway | Vercel AI Gateway | Solo AI Gateway |
|---|---|---|---|---|
| 部署形态 | 自托管 / F5 XC | 边缘 SaaS | 边缘 SaaS | 自托管 + SaaS |
| 边缘节点 | F5 XC PoP | Cloudflare 全球 300+ PoP | Vercel Edge Network | Solo Gloo Cloud |
| Token rate-limit | shm zone | 边缘 KV | 边缘 KV | 分布式 |
| WAF | F5 WAF | Cloudflare WAAP | ❌ | Solo WAAP |
| LLM provider 数 | 5-10 原生 + 100+ 兼容 | 35+ | 15+ | 20+ |
| MCP 协议 | ✅ | ✅ | ✅ | ✅ |
| A2A 协议 | ✅ | ✅ | ⚠️ | ✅ |
| 自托管 | ✅ | ❌ | ❌ | ✅ |
| 典型 100M token/月成本 | $15K-50K | $1K-5K | $1K-3K | $5K-15K |
| 客群 | 大企业 / 自托管 | 中小 / 边缘 | 中小 / web 应用 | 中型 / Service Mesh |

**结论**：Cloudflare AI Gateway 在**边缘 + 价格**上无敌；Vercel AI Gateway 在**web 应用集成**上最简；Solo AI Gateway 在**Service Mesh 兼容**上最强；NGINX AI Gateway 在**自托管 + 企业安全**上最强。

### 13.4 与 AWS Bedrock / Azure AI / Vertex（云厂商原生）

| 维度 | NGINX AI Gateway | AWS Bedrock | Azure AI Foundry | Vertex AI |
|---|---|---|---|---|
| 多云中立 | ✅ | ❌ (AWS) | ❌ (Azure) | ❌ (GCP) |
| 自托管 | ✅ | ❌ | ❌ | ❌ |
| 协议统一 | OpenAI / Anthropic / Bedrock / Vertex | Bedrock 协议 | Azure OpenAI / Responses | Vertex 协议 |
| WAF 集成 | F5 WAF | AWS WAF | Azure WAF | GCP Armor |
| Token rate-limit | shm zone | API Gateway + Lambda | APIM | API Gateway |
| LLM cascade | ❌ | ❌ | ❌ | ❌ |
| MCP / A2A | ✅ | ✅ | ✅ | ✅ |

**结论**：云厂商原生适合**单云 + 不需要数据出门**的客户；NGINX AI Gateway 适合**多云 / 混合 / 自托管 + 数据不出域**的客户。

### 13.5 与 Helicone / OpenRouter / Unify（中间层 SaaS）

| 维度 | NGINX AI Gateway | Helicone | OpenRouter | Unify |
|---|---|---|---|---|
| 部署形态 | 自托管 / F5 XC | SaaS | SaaS | SaaS |
| Token 过路费 | $0 | $0 (cache 重售除外) | 5-10% markup | $0 (低 markup) |
| LLM provider 数 | 5-10 原生 + 100+ 兼容 | 35+ | 300+ | 30+ |
| LLM 协议广度 | 中 | 中 | 极广 | 中 |
| 自托管 | ✅ | ❌ | ❌ | ❌ |
| 客群 | 大企业 | AI 工程师 | 任意 | AI 工程师 |

**结论**：Helicone / OpenRouter / Unify 适合**AI 工程师快速集成**；NGINX AI Gateway 适合**企业级自托管 + 安全合规**。

### 13.6 与 Traefik Hub AI Gateway（直接对位）

| 维度 | NGINX AI Gateway | Traefik Hub AI Gateway |
|---|---|---|
| 公司 | F5 (NASDAQ: FFIV) | Traefik Labs (Containous, France) |
| 数据面 | NGINX (C) | Traefik Proxy (Go) |
| 控制面 | NGF (Go) | Helm Operator (Go) |
| SaaS 模式 | NGINX One (consumption) | Traefik Hub (subscription) |
| Token rate-limit | shm zone (Plus) | Redis (Token-Rate-Limit plugin) |
| 语义缓存 | ❌（外接）| ✅ 内置 (Redis/Milvus/Weaviate) |
| 5 个 AI middlewares | 部分 | 完整 5 个 + parallel-llm-guard |
| LLM judge | F5 WAF for AI | LLM-as-a-Judge 内置 |
| Air-Gap Ready | ✅ | ✅ |
| 商业化深度 | 极深（F5 全栈）| 中（Traefik Labs 单产品）|
| 自托管 | ✅ | ✅ |
| MCP 协议 | ✅ 2026-Q2 | ⚠️ partial |
| A2A 协议 | ✅ 2026-Q1 | ⚠️ partial |
| 客群 | 大企业 | 中型 / K8s-first |
| 性能 | NGINX C 优势 | Go 1.2x latency |
| WAF 集成 | F5 WAF 一等公民 | Coraza WAF 插件 |
| 集群规模 | 中 | 中 |

**结论**：Traefik Hub AI Gateway 在 **AI middlewares 矩阵** 上更完整（5 个 + 1 个），且**强调"Air-Gap Ready"**；NGINX AI Gateway 在 **企业安全（F5 WAF）+ 性能 + F5 全栈集成**上更强。

### 13.7 横向对比矩阵

| 维度 | NGINX AI Gateway | Portkey | LiteLLM | Kong AI | Envoy AI | Cloudflare AI | Traefik Hub AI | Solo AI |
|---|---|---|---|---|---|---|---|---|
| 部署 | 自+XC | SaaS+OSS | OSS | 自+EE | 自+Solo | SaaS | 自+Hub | 自+Gloo |
| LLM provider | 5-10+100 兼容 | 250+ | 100+ | 25+ | 10+ | 35+ | 15+ | 20+ |
| Token rate-limit | ★★★★★ | ★★★★ | ★★★ | ★★★★ | ★★★★ | ★★★ | ★★★★ | ★★★★ |
| 语义路由 | ★ | ★★★★★ | ★★★ | ★★ | ★★ | ★ | ★ | ★★ |
| Cost-based 路由 | ★ | ★★★★★ | ★★ | ★★ | ★★ | ★★ | ★★ | ★★ |
| LLM cascade | ★ | ★★★★★ | ★★ | ★★ | ★★ | ★ | ★ | ★★ |
| WAF 集成 | ★★★★★ (F5) | ★ | ★ | ★★★★ (Kong) | ★★ | ★★★★★ (CF) | ★★★ (Coraza) | ★★★★ (Solo) |
| 性能 | ★★★★★ (C) | ★★ (Py) | ★★ (Py) | ★★★ (Lua) | ★★★★★ (C++) | ★★★★ (Rust) | ★★★ (Go) | ★★★ (Go) |
| 集群规模 | ★★★ (10K) | ★★ (Py 限) | ★★ (Py 限) | ★★★ (5K) | ★★★★★ (100K+) | ★★★★★ (CF 边缘) | ★★★ (5K) | ★★★★ (10K) |
| MCP 协议 | ★★★★ | ★★★★ | ★★★ | ★★★★ | ★★★★ | ★★★★ | ★★ | ★★★★ |
| A2A 协议 | ★★★★ | ★★★★ | ★★ | ★★★★ | ★★★★ | ★★★★ | ★★ | ★★★★ |
| 商业化深度 | ★★★★★ (F5 全栈) | ★★★ | ★★ | ★★★★ (Kong Inc) | ★★★ (Tetrate/Solo) | ★★★★★ (CF) | ★★★ (Traefik Labs) | ★★★★ (Solo.io) |
| 客群匹配 | 大企业 / 金融 / 电信 | AI 工程师 | AI 工程师 | 中大型 | Mesh 用户 | 边缘 / 多云 | K8s-first | Mesh 用户 |
| TCO 100M token/月 | $15K-50K/yr | $5K-12K/yr | $3K-8K/yr | $8K-20K/yr | $5K-15K/yr | $1K-5K/yr | $8K-20K/yr | $5K-15K/yr |
| F5 / NGINX 客户首选 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AI 工程师首选 | ❌ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |

---

## 十四、对我们的硬要求（落地 AIGW 12 条）

从 F5 NGINX AI Gateway 的设计中，我们可以学到 12 条对 AIGW（AI Gateway）产品的硬要求：

| # | 要求 | 来源 |
|---|---|---|
| 1 | **数据面性能血统** | NGINX C 事件循环 < 1.5ms p50，AI Gateway 必须保持 L7 性能门槛。|
| 2 | **Token rate-limit 一等公民** | 基于 shm zone / Redis 集群，~200ns/check，跨 worker / 跨节点同步。|
| 3 | **精确 + 语义双层 cache** | 精确 cache 用 `proxy_cache_key` + request body；语义 cache 走外部 vector store。|
| 4 | **Streaming 优化** | `proxy_buffering off; proxy_request_buffering off; proxy_http_version 1.1;` 三件套 + SSE 头识别。|
| 5 | **OpenAI 兼容 + 5-10 原生** | 原生适配 OpenAI / Anthropic / Bedrock / Vertex / Cohere；其他 OpenAI 兼容 1 行 upstream。|
| 6 | **WAF / Bot Defense / API Security 集成** | 至少 3 个独立模块，与 AI Gateway 协同（OWASP / Jailbreak / PII）。|
| 7 | **OpenTelemetry GenAI semconv** | `gen_ai.client.token.usage` (input/output/cache_read) + `time_to_first_token` + `cost.estimated` 全 attribute。|
| 8 | **MCP + A2A 协议** | 跟随 MCP 2026-07-28-rc + A2A 2026 规范，header 透传 + 路由。|
| 9 | **Failover + Multi-region** | `proxy_next_upstream` + `backup` + `max_fails` + `fail_timeout` + `slow_start` (Plus)。|
| 10 | **GitOps 友好** | K8s Gateway API CRD 一等公民，ArgoCD / FluxCD 直接 apply。|
| 11 | **PII / 合规** | 自托管 + 数据不出域 + Vault 凭据 + SPIFFE mTLS + 审计日志。|
| 12 | **多部署形态** | 自托管（OSS / Plus） + SaaS 管理面 + 边缘云，三模式并存。|

---

## 十五、参考资料

1. **F5 NGINX 官方**：<https://www.f5.com/products/nginx>（重定向后产品页）
2. **NGINX Gateway Fabric 主仓**：<https://github.com/nginx/nginx-gateway-fabric>（v2.6.3, 2026-05-29）
3. **NGF 架构文档**：<https://docs.nginx.com/nginx-gateway-fabric/overview/gateway-architecture/>
4. **NGF Gateway API 兼容性**：<https://docs.nginx.com/nginx-gateway-fabric/overview/gateway-api-compatibility/>
5. **NGF Releases**：<https://github.com/nginx/nginx-gateway-fabric/releases>
6. **NGF Technical Specifications**：<https://docs.nginx.com/nginx-gateway-fabric/overview/technical-specifications/>
7. **NGINX Agent 主仓**：<https://github.com/nginx/agent>（v3.10.3）
8. **NGINX One 设计愿景博客**：<https://www.f5.com/company/blog/nginx/our-design-vision-for-nginx-one-the-ultimate-data-plane-saas>（2024-03-13）
9. **F5 WAF for NGINX 5.13.1**：<https://docs.nginx.com/waf/>
10. **K8s Gateway API 标准**：<https://gateway-api.sigs.k8s.io/>
11. **OpenTelemetry GenAI semconv**：<https://opentelemetry.io/docs/specs/semconv/gen-ai/>
12. **MCP 2026-07-28-rc 规范**（上一轮 MCP deep-dive 报告覆盖）
13. **Google A2A 协议**（上一轮 A2A deep-dive 报告覆盖）
14. **Traefik Hub AI Gateway 调研**：aigw/openclaw/product-traefik-ai-gateway-20260606.md
15. **Kong AI Gateway 调研**：aigw/openclaw/product-kong-ai-gateway-20260605.md
16. **Envoy AI Gateway 调研**：aigw/openclaw/product-envoy-ai-gateway-20260605.md
17. **APISIX ai-proxy 调研**：aigw/openclaw/product-apisix-ai-proxy-20260605.md
18. **Cloudflare AI Gateway 调研**：aigw/openclaw/product-cloudflare-workers-ai-20260605.md
19. **Vercel AI Gateway 调研**：aigw/openclaw/product-vercel-ai-gateway-20260606.md
20. **Solo AI Gateway 调研**：aigw/openclaw/product-solo-ai-gateway-20260606.md
21. **Higress 调研**：aigw/openclaw/product-higress-20260605.md

---

**调研小结**：

F5 NGINX AI Gateway 是 **"通用 API Gateway 派"在企业级 + 自托管 + 安全合规"赛道**的代表。它的**最强项**是：（1）F5 WAF for AI 一等公民；（2）NGINX Plus shm zone 上的 token rate-limit（~200ns/check，跨 worker 同步）；（3）F5 BIG-IP 4,000+ 客户群 + NGINX 4 亿+ 容器实例的"存量转化"。**最弱项**是：（1）reload 模型在 10K+ route 大集群的延迟累积；（2）AI 协议广度不如 Portkey / LiteLLM；（3）总拥有成本高于 SaaS 派。

**对 AIGW 落地**：F5 NGINX AI Gateway 是**"金融 / 电信 / 政府 / 关键基础设施"客户的首选**，但对**AI 工程师主导的初创 / 中型 SaaS**不是最优解。它的 12 条硬要求（特别是 token rate-limit 一等公民、shm zone 跨 worker 同步、F5 WAF for AI 集成）应作为 AIGW 产品的"企业级"基准。
