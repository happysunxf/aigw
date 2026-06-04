# AI Gateway 调研报告

> 调研日期：2026-06-05
> 目的：为 aigw 项目选型 / 定位 / 差异化提供决策依据
> 范围：面向 LLM/AI 应用的统一代理层（模型路由、限流、鉴权、可观测、计费、Guardrails）

---

## 目录

1. [产品定位与价值](#一产品定位与价值)
2. [市场分类总览](#二市场分类总览)
3. [开源/独立项目](#三一开源独立项目主流竞品)
4. [云厂商方案](#三二云厂商方案)
5. [独立 SaaS](#三三独立-saas)
6. [大模型厂商生态](#三四大模型厂商自家生态)
7. [核心能力矩阵](#四核心能力矩阵)
8. [代表性产品深入画像](#五代表性产品深入画像)
9. [竞品差异化与机会分析](#六竞品差异化与机会分析)
10. [给小F 副业的战略建议](#七给小f-副业的战略建议)
11. [技术选型参考](#八技术选型参考)
12. [风险与挑战](#九风险与挑战)
13. [参考资料](#十参考资料)

---

## 一、产品定位与价值

### 1.1 是什么

**AI Gateway** 是位于"AI 应用 ↔ LLM 模型 API"之间的统一代理层。它是传统 **API 网关**（鉴权、限流、路由、监控）在 LLM 场景下的特化版本。

### 1.2 为什么需要

直连 LLM API 的痛点：

| 痛点 | 说明 |
|---|---|
| **多模型管理** | 企业同时用 OpenAI / Claude / 通义 / DeepSeek，每家一套 key、一套协议、一套账单 |
| **成本失控** | 一个 prompt 写错循环调用就能烧几千美元，没有细粒度限流 |
| **可观测缺失** | 不知道谁、什么时候、调了什么、用了多少 token、为什么失败 |
| **Fallback 缺失** | 单家 API 抖动就业务不可用 |
| **Key 泄露** | 前端 / 多服务直连模型 key，散落各处无法收回 |
| **合规审计** | 出问题无法回放用户对话、无法拦截违规输出 |

### 1.3 AI Gateway 提供的核心能力

```
                        ┌──────────────────────┐
   AI 应用 / Agent ──▶  │     AI Gateway       │ ──▶ OpenAI / Claude / 通义 / DeepSeek ...
                        │                      │
                        │  • 统一鉴权          │
                        │  • 模型路由          │
                        │  • Token 限流/计费   │
                        │  • 缓存（精确/语义） │
                        │  • Fallback 负载     │
                        │  • 可观测 Tracing    │
                        │  • Guardrails        │
                        │  • Prompt 模板管理   │
                        │  • 成本归因          │
                        └──────────────────────┘
```

---

## 二、市场分类总览

按"出身"和"商业模式"分四类：

| 类别 | 代表 | 商业模式 | 目标客户 |
|---|---|---|---|
| **开源/独立项目** | Portkey、LiteLLM、One API、Higress | 自托管 + 商业版 | 开发者、中小企业 |
| **云厂商** | 阿里云 AI 网关、AWS Bedrock、Apigee AI | 绑定云服务 | 上云企业 |
| **独立 SaaS** | Helicone、Portkey Cloud、OpenRouter、Unify | 订阅 + 用量 | 中小企业、ToC 产品 |
| **大模型厂商生态** | OpenAI / Anthropic / 通义 | 自家模型+生态 | 直接用户 |

> **关键观察**：开源版和 SaaS 版的边界很模糊。Portkey、Higress、LiteLLM 都同时提供自托管和商业版。

---

## 三、分类详述

### 三·一、开源/独立项目（主流竞品）

| 产品 | 厂商/社区 | 语言 | Star 量级 | 核心特点 | 适用场景 |
|---|---|---|---|---|---|
| **Portkey Gateway** | Portkey AI | Go | 6k+ | 250+ 模型路由；Langfuse/Opik 原生集成；fallback、cache、guardrails、负载均衡 | 中大型企业、Agent 平台 |
| **LiteLLM** | BerriAI | Python | 20k+ | 万能协议翻译；自托管最简单；OpenAI SDK 兼容 | 开发者、自托管首选 |
| **One API** | songquanpeng | Go | 18k+ | 国产老牌；极轻量；30+ 国内外渠道；按渠道分发 Key | 国内小B、二级分销 |
| **New API** | QuantumNous | Go | 5k+ | One API 分支；渠道更全；多用户计费完善 | 国内代理、渠道商 |
| **OpenRouter（开源版）** | OpenRouter | - | - | 主 SaaS；按 token 路由最优模型；公开榜单 | 跨模型调度 |
| **Kong AI Gateway** | Kong | Lua/Go | - | 老牌 API 网关扩展；企业级稳定 | 大型金融、政企 |
| **Envoy AI Gateway** | CNCF | Go | 新 | Envoy 之上加 AI 路由；CNCF 推；K8s/Istio 友好 | 云原生大厂 |
| **Higress** | 阿里云开源 | Go/C++ | 5k+ | Envoy + Istio；国内模型覆盖全；插件化；阿里云商业版 | 国内中大型、阿里云用户 |
| **APISIX ai-proxy** | API7 | Lua | 13k+ | Apache 顶级项目插件；AI 路由、Token 限流、计费 | 已有 APISIX 栈 |
| **Solo AI Gateway** | Solo.io | Go | - | 服务网格路线；面向大企业 K8s 体系 | Solo Gloo 客户 |

### 三·二、云厂商方案

| 厂商 | 产品 | 特点 | 锁定程度 |
|---|---|---|---|
| **Google Cloud** | Apigee + Vertex AI Gateway | 企业级；Vertex 模型限流、缓存、Guardrails | 高（绑 GCP） |
| **AWS** | Bedrock + API Gateway | Bedrock 自带模型路由；API GW 做鉴权限流 | 高（绑 AWS） |
| **Azure** | Azure API Management + AI Gateway | APIM 加 AI 策略；面向 Azure OpenAI | 高（绑 Azure） |
| **阿里云** | 阿里云 AI 网关 / Higress 商业版 | 通义/百炼一体化；token 计费；函数计算/SAE 集成 | 中（开源版可独立） |
| **腾讯云** | API Gateway AI 插件 | 面向混元 + 第三方模型 | 中 |
| **华为云** | APIG AI 插件 | 面向盘古 | 中 |

### 三·三、独立 SaaS

| 厂商 | 特点 | 商业模式 | 备注 |
|---|---|---|---|
| **Portkey（云）** | 自托管 + SaaS；团队协作；评测、Prompt playground | 订阅 + 用量 | 与开源版功能有差 |
| **OpenRouter** | 模型聚合市场；按 token 路由；省去签多家 | 按 token 抽佣 | 用户量大、模型全 |
| **Helicone** | 偏可观测 + 代理；replay、用户维度统计 | 订阅 | 开发者友好 |
| **Lunary** | 类似 Helicone，更轻量 | 免费 + 订阅 | 适合早期 |
| **Unify** | 模型评测 + 路由；按 cost/latency 自动选 | 订阅 | 强调智能路由 |
| **Martian** | 强调"模型转换"——任意模型 API 转任意协议 | 用量 | 协议适配能力强 |
| **Not Diamond** | AI 路由决策；按 query 类型选最优模型 | 订阅 | 决策算法为核心 |
| **Traceloop** | OpenLLMetry 标准 + 网关 | 订阅 | 标准化路线 |
| **LangSmith Hub** | LangChain 自家；可观测 + 部分网关能力 | 订阅 | LangChain 用户 |
| **TrueFoundry** | MLOps 平台 + LLM Gateway | 企业版 | 偏平台化 |
| **Cloudflare AI Gateway** | 边缘节点 + 缓存命中统计 + 可观测 | 免费层 + 用量 | 边缘优势明显 |

### 三·四、大模型厂商自家生态

| 厂商 | 备注 |
|---|---|
| **OpenAI / Anthropic** | 本身没网关，但 OpenAI 协议是事实标准，所有网关都兼容 |
| **Azure OpenAI** | 通过 APIM 走 |
| **通义 / 豆包 / DeepSeek / Kimi** | OpenAI 兼容 API，企业仍常前置一层网关做统一管理 |

---

## 四、核心能力矩阵

| 能力 | 谁做得好 | 备注 |
|---|---|---|
| **协议兼容**（OpenAI / Anthropic 互转） | LiteLLM、Portkey、Martian、APISIX | 事实标准是 OpenAI 协议 |
| **多模型路由**（cost / latency / 任务） | Portkey、Not Diamond、Unify | 智能路由正在变成差异化 |
| **Fallback / 多 key 负载** | Portkey、LiteLLM、One API | 几乎人人都有 |
| **Token 级缓存**（精确 / 语义） | Cloudflare、Portkey、Helicone | 语义缓存是趋势 |
| **可观测 / Tracing**（OpenLLMetry） | Helicone、Langfuse+Portkey、Traceloop | 标准化进行中 |
| **Guardrails**（PII、毒性、过滤） | Portkey、Cloudflare、NVIDIA NeMo Guardrails | 多为插件化 |
| **按用户/租户限流 + 计费** | One API、New API、APISIX、Kong | 小B 最关心 |
| **Prompt 模板 / 版本管理** | Portkey、LangSmith | 偏协作 |
| **自托管友好** | LiteLLM、Portkey、One API、Higress、APISIX | 国内首选自托管 |
| **企业级合规 / 审计** | Kong、Apigee、Solo AI Gateway | 大客户刚需 |
| **K8s/服务网格原生** | Higress、Envoy AI Gateway、Solo | 云原生路线 |
| **国内模型覆盖** | One API、New API、Higress、APISIX | 国外产品对国内模型支持弱 |

---

## 五、代表性产品深入画像

### 5.1 Portkey Gateway
- **强项**：模型路由 + 可观测 + 团队协作，三者结合最好
- **架构**：Go 写，性能好；中间件思路
- **商业版**比开源版多了：审计日志、SSO、组织管理、Prompt playground
- **适合**：中大型 Agent 平台、ToB SaaS 集成商
- **短板**：国内模型覆盖弱、需要二次开发

### 5.2 LiteLLM
- **强项**：协议翻译之王，"什么模型都能塞进来"
- **架构**：Python，100+ 提供商，几乎所有 SDK 都能改 base_url 切过来
- **适合**：开发者快速实验、自托管 PoC
- **短板**：企业特性弱（多租户、计费需要自研）

### 5.3 One API / New API
- **强项**：国内"渠道聚合"事实标准，OpenAI 协议 + 多渠道 + 多用户
- **架构**：Go + SQLite/MySQL，一键部署
- **商业**：常用于"中转站"、"二级分销"
- **短板**：偏"转售"思路，企业侧（团队、计费、审计）做得不够

### 5.4 Higress
- **强项**：阿里云背书 + Envoy 内核 + 国内模型覆盖全
- **架构**：Go/C++，K8s 原生，Wasm 插件
- **适合**：阿里云用户、大流量场景
- **商业版**含：通义/百炼专属优化、阿里云监控集成

### 5.5 Cloudflare AI Gateway
- **强项**：边缘缓存 + 全球节点 + 零运维
- **适合**：出海产品、对延迟敏感的应用
- **短板**：深度可控性差、私有化部署能力弱

### 5.6 Helicone
- **强项**：可观测 + 成本归因 + 请求 replay
- **适合**：早期产品快速接入看数据
- **短板**：路由、计费等网关核心能力偏弱

---

## 六、竞品差异化与机会分析

### 6.1 现有格局"空白地带"

| 空白 | 说明 | 机会 |
|---|---|---|
| **垂直行业模板** | 现有都是通用网关，没有"电商客服 / 律所 / 教育"等场景化配置 | 高 |
| **国内 SaaS 化 + 企业微信/钉钉/飞书深度集成** | One API 是"渠道"思路，没有"业务"思路 | 高 |
| **按席位/工号计费 + 内部用量看板** | 小B 老板最关心"谁用了多少、谁在浪费" | 高 |
| **多租户 + 子账号 + 配额包** | 现有都是开发者工具，没有"老板"视角 | 高 |
| **审计 / 合规 / 留痕（等保视角）** | One API 等几乎没有 | 中 |
| **私有化 + 国密 + 信创** | Higress 商业版有，但偏云 | 中 |
| **AI 路由决策（按 query 类型选模型）** | Not Diamond / Unify 在做，但都是英文场景 | 中 |

### 6.2 国内小B 的真实需求

- 不需要 200 个模型，能稳定用上 GPT-4o-mini / DeepSeek / 豆包 / 通义 5-10 个就够
- 最在意"员工别乱花"、"老板能看见花在哪"、"出了问题能回放"
- 部署要简单（最好 SaaS，不想运维）
- 鉴权要能接企业微信 / 钉钉（员工离职自动回收）
- 计费要能"按部门、按项目"分摊

### 6.3 出海/ToC 机会

- 智能化路由（按 query 自动选模型 + 成本）还是蓝海
- 语义缓存（Cloudflare 是精确缓存，语义缓存有壁垒）
- 多模态网关（图像/视频/语音统一代理）刚起步

---

## 七、给小F 副业的战略建议

### 7.1 建议方向（按可行性排序）

#### 🥇 方向 A：国内小B 一体化 AI 网关 SaaS（**最推荐**）
- **目标客户**：100-500 人规模的企业（电商代运营、MCN、律所、培训机构、跨境电商）
- **核心卖点**：
  1. 一键开通 GPT-4o / DeepSeek / 豆包 / 通义，按用量计费
  2. 企业微信/钉钉集成，员工扫码登录、离职自动回收
  3. 老板看板：按部门/项目/个人看消耗
  4. 审计 + 对话回放（应对合规）
- **差异化 vs One API**：
  - One API 是"开发者工具" → 你做"老板视角"
  - One API 渠道聚合 → 你做"5-10 个精选模型 + 稳定 SLA"
  - One API 没有企业微信 → 你做"开箱即用"
- **定价**：5-15 万/年（正好命中你的目标价位）

#### 🥈 方向 B：垂直行业 AI 网关 + Prompt 模板市场
- 选 1-2 个垂直行业（先做电商客服或律所）
- 网关 + 行业 Prompt 模板 + 评测集
- 卖给同行业小B
- 优势：客单价高（20-30 万/年）、壁垒深

#### 🥉 方向 C：智能路由引擎（技术派）
- 做"按 query 自动选模型"的决策引擎
- 提供 API + 开源 SDK
- 卖给其他 AI 网关 / Agent 平台
- 风险：技术门槛高、销售周期长

### 7.2 不建议做的方向

| 方向 | 不建议原因 |
|---|---|
| 通用开源 AI Gateway | 已有 Portkey/LiteLLM/Higress 三座大山，小团队没胜算 |
| 国际化通用 SaaS | Helicone/Portkey Cloud 已经很深 |
| 纯模型聚合市场（OpenRouter 模式） | 模型厂商自己都在做，护城河浅 |
| K8s/服务网格路线 | 客户群小、决策周期长 |

### 7.3 启动建议（90 天计划）

**第 1-30 天：验证**
- 找 5-10 个潜在客户（电商代运营、MCN 老板）聊
- 验证"老板看板 + 企业微信集成"是不是真痛点
- MVP：LiteLLM 内核 + 简单企业微信集成 + 看板

**第 31-60 天：MVP 上线**
- 部署在阿里云（国内模型通道顺）
- 接 3-5 个 SaaS 客户试用
- 重点打磨：审计日志、配额管理、用量归因

**第 61-90 天：商业化**
- 收第一个付费客户（5-10 万/年）
- 打磨销售话术、ROI 案例
- 决定是往"行业纵深"还是"通用小B"走

---

## 八、技术选型参考

如果走方向 A，**MVP 技术栈建议**：

| 层 | 选型 | 理由 |
|---|---|---|
| **网关内核** | LiteLLM（Python）或自研 Go | LiteLLM 快、自研可控 |
| **数据库** | PostgreSQL | 稳定、审计/分析能力强 |
| **鉴权** | 企业微信 OAuth + 自建账号体系 | 客户刚需 |
| **计费** | 自建用量计量 + Stripe/微信支付 | 灵活 |
| **看板** | Metabase / 自建 React | MVP 用 Metabase 快 |
| **部署** | 阿里云 ACK（K8s） | 国内通道稳定 |
| **可观测** | Langfuse 自托管 | 开源、可控 |

---

## 九、风险与挑战

| 风险 | 影响 | 应对 |
|---|---|---|
| **模型 API 价格战** | 客户自购直接降价 | 做"管理价值"而非"价格优势" |
| **模型厂商自己做网关** | 头部客户被锁定 | 坚持中立、不绑任何厂商 |
| **合规政策变化** | 国内大模型需备案 | 提前研究、等保/备案准备 |
| **Key 泄露** | 一旦发生损失大 | 做"前端不可见 key"架构 |
| **小B 付费意愿弱** | 价格敏感 | 用"按用量"切入，避免年付门槛 |

---

## 十、参考资料

### 10.1 开源仓库（直接看 README 即权威）

- github.com/Portkey-AI/gateway
- github.com/BerriAI/litellm
- github.com/songquanpeng/one-api
- github.com/QuantumNous/new-api
- github.com/alibaba/higress
- github.com/api7/apisix（ai-proxy 插件）
- github.com/envoyproxy/ai-gateway
- github.com/kong/kong（ai 插件）
- github.com/Helicone/helicone

### 10.2 官方文档

- developers.cloudflare.com/ai-gateway
- docs.portkey.ai
- docs.litellm.ai
- higress.cn / aliyun.com/product/ai-gateway
- apigee.google.com（Apigee AI）
- aws.amazon.com/bedrock
- learn.microsoft.com/azure/api-management（AI 策略）

### 10.3 行业研究

- a16z: "The AI Gateway Stack"
- LangChain State of AI Agents 报告
- OpenLLMetry 标准（traceloop 主导）
- 沙丘智库 / 甲子光年 国内 LLM Infra 报告

---

## 报告结论

> **一句话定位建议**：
> 做"**面向国内小B 的 AI 网关 SaaS**"——**老板视角**、**企业微信/钉钉原生**、**用量看板 + 审计**、**精选 5-10 个模型**、**5-15 万/年**。
>
> 核心差异点：和 One API 的"渠道聚合"做切割，定位"老板/管理者"而非"开发者"。

---

**报告维护**：
- 报告版本：v1.0
- 维护人：小F / Rich
- 下次更新：竞品有新功能 / 模型价格有变化 / 新增 3 个客户案例时
