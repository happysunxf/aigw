# AI Gateway 厂商全景

> 调研时间：2026-06 · 小F 副业方向参考
> 范围：面向 LLM/AI 应用的统一代理层（路由、限流、鉴权、可观测、计费）

---

## 一、定位

统一代理所有 LLM 调用，对外提供：模型路由、Key 管理、限流/配额、缓存、可观测、Prompt 模板、Guardrails、计费计量。  
本质是 **API 网关 + LLM 特色能力**。

---

## 二、分类（四类）

### 1. 开源 / 独立项目

| 产品 | 厂商 / 社区 | 核心特点 |
|---|---|---|
| **Portkey Gateway** | Portkey AI | 多模型路由；支持 250+ 模型；原生 Langfuse/Opik 集成；fallback、cache、guardrails、负载均衡；Go |
| **LiteLLM** | BerriAI | Python；几乎兼容所有 LLM SDK；OpenAI 协议万能翻译；自托管简单 |
| **One API** | songquanpeng | 国产老牌；极轻量；30+ 国内外渠道；按渠道分发 Key |
| **New API** | QuantumNous | One API 分支；渠道更全；多用户计费完善 |
| **OpenRouter（开源版）** | OpenRouter | 主 SaaS；开源版 API 形态；按 token 路由最优模型 |
| **Kong AI Gateway** | Kong | 老牌 API 网关扩展 AI 插件；企业级稳定 |
| **Envoy AI Gateway** | Envoy 社区 + CNCF | Envoy 之上加 AI 路由；CNCF 在推；K8s/Istio 友好 |
| **Higress** | 阿里云开源 | 基于 Envoy + Istio；支持通义/DeepSeek/豆包；插件化 |
| **APISIX ai-proxy** | API7 | Apache APISIX 插件，AI 路由、Token 限流、计费 |
| **Solo AI Gateway** | Solo.io | 服务网格路线；面向大企业 K8s 体系 |

### 2. 云厂商（绑定自家生态）

| 厂商 | 产品 | 特点 |
|---|---|---|
| **Google Cloud** | Apigee + Vertex AI Gateway | 企业级；Vertex 模型限流、缓存、Guardrails |
| **AWS** | Amazon Bedrock + API Gateway | Bedrock 自带模型路由；API GW 做鉴权限流 |
| **Azure** | Azure API Management + AI Gateway | APIM 加 AI 策略；面向 Azure OpenAI |
| **阿里云** | 阿里云 AI 网关 / Higress 商业版 | 通义/百炼一体化；token 计费；函数计算/SAE 集成 |
| **腾讯云** | API Gateway AI 插件 | 面向混元 + 第三方模型 |
| **华为云** | APIG AI 插件 | 面向盘古 |

### 3. 独立 SaaS

| 厂商 | 特点 |
|---|---|
| **Portkey（云）** | 自托管 + SaaS；团队协作；评测、Prompt playground |
| **OpenRouter** | 模型聚合市场；按 token 路由；省去签多家 |
| **Helicone** | 偏可观测 + 代理；replay、用户维度统计 |
| **Lunary** | 类似 Helicone，更轻量 |
| **Unify** | 模型评测 + 路由；按 cost/latency 自动选 |
| **Martian** | 强调"模型转换"——任意模型 API 转任意协议 |
| **Not Diamond** | AI 路由决策；按 query 类型选最优模型 |
| **Traceloop** | OpenLLMetry 标准 + 网关 |
| **LangSmith Hub** | LangChain 自家；可观测 + 部分网关能力 |
| **TrueFoundry** | MLOps 平台 + LLM Gateway |
| **Cloudflare AI Gateway** | 边缘节点 + 缓存命中统计 + 可观测 |

### 4. 大模型厂商自家

| 厂商 | 备注 |
|---|---|
| **OpenAI / Anthropic** | 本身没网关，但 OpenAI 协议是事实标准 |
| **Azure OpenAI** | 通过 APIM 走 |
| **通义 / 豆包 / DeepSeek** | OpenAI 兼容 API，企业仍常前置一层网关 |

---

## 三、能力矩阵

| 能力 | 代表实现 |
|---|---|
| 协议兼容（OpenAI / Anthropic 互转） | LiteLLM、Portkey、Martian、APISIX |
| 多模型路由（cost / latency / 任务） | Portkey、Not Diamond、Unify |
| Fallback / 多 key 负载 | Portkey、LiteLLM、One API |
| Token 级缓存（精确 / 语义） | Cloudflare、Portkey、Helicone |
| 可观测 / Tracing（OpenLLMetry） | Helicone、Langfuse+Portkey、Traceloop |
| Guardrails（PII、毒性、过滤） | Portkey、Cloudflare、NVIDIA NeMo Guardrails（搭配） |
| 按用户/租户限流 + 计费 | One API、New API、APISIX、Kong |
| Prompt 模板 / 版本管理 | Portkey、LangSmith |
| 自托管友好 | LiteLLM、Portkey、One API、Higress、APISIX |
| 企业级合规 / 审计 | Kong、Apigee、Solo AI Gateway |
| K8s / 服务网格原生 | Higress、Envoy AI Gateway、Solo |
| 国内模型覆盖 | One API、New API、Higress、APISIX |

---

## 四、给小F 的副业启发

- **国内小B**：One API / New API 几乎垄断"渠道聚合"，但都偏渠道层。差异化方向：
  1. 垂直行业模板（电商客服话术、律所文档生成）
  2. 企业微信 / 钉钉 / 飞书深度接入
  3. 按席位 / 工号计费 + 内部用量看板
- **出海 / To C**：Portkey、Helicone 已做深，机会在"更易用"或"垂直场景"
- **云原生**：Higress、Envoy AI Gateway 抢 K8s 用户，门槛高，小团队慎入

---

## 五、参考资料

- github.com/Portkey-AI/gateway
- github.com/BerriAI/litellm
- github.com/songquanpeng/one-api
- github.com/api7/apisix（ai-proxy 插件）
- github.com/alibaba/higress
- github.com/envoyproxy/ai-gateway
- developers.cloudflare.com/ai-gateway

---

**信息时效说明**：基于训练数据（截止 2025 上半年）。如需 2026 Q2 最新版（含融资、最新 feature），需配置网络搜索工具后实时拉取。
