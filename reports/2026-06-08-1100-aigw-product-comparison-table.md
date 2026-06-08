# AI Gateway 全景对照表（2026-06-08）

> 范围：`aigw/openclaw/product-*.md` 共 **78 个独立产品**（79 份深挖，其中 Solo.io agentgateway 有 6-06 / 6-07 两份不同时点的报告）。
> 字段：产品名 / 厂商 / 协议或许可 / 一句话定位。
> 分类按"出身 + 主业"分 5 大类；同类内按影响力/规模排序。

---

## ① AI Gateway 核心（路由 / 限流 / 缓存 / Guardrails 一体化）— 20 个

| # | 产品 | 厂商 | 协议/许可 | 一句话定位 |
|---|---|---|---|---|
| 1 | Portkey | Portkey AI | MIT + Cloud | 面向生产 AI 的控制面板；1600+ 模型、Guardrails、Configs、缓存、追踪；2026 被 Palo Alto Networks 收购 |
| 2 | LiteLLM | BerriAI | MIT + Cloud | 100+ LLM 统一接入网关，Python 起家；扩展出 A2A / MCP Gateway、可观测 / 成本 / 治理 |
| 3 | Higress | 阿里云 | Apache-2.0 | Envoy + Istio 内核；国内模型覆盖全；Wasm 插件；阿里云商业版叫"AI 网关" |
| 4 | APISIX ai-proxy | API7 / Apache | Apache-2.0 | Apache 顶级 API GW 的 AI 插件矩阵：多 Provider、Token 限流、Prompt 模板、RAG |
| 5 | Kong AI Gateway | Kong Inc. | OSS + Konnect | 老牌 API GW 的 AI 扩展：Universal LLM API、Token 限流、Semantic Cache、Guardrails |
| 6 | Envoy AI Gateway | CNCF | Apache-2.0 | CNCF 官方 AI 扩展；Envoy 数据面 + xDS 控制面；K8s / Istio 友好 |
| 7 | Solo.io agentgateway | Solo.io / LF | Apache-2.0 | Rust 写的 AI-native 网关；K8s / Agent 原生；同时管 LLM / MCP / A2A 流量 |
| 8 | HAProxy AI Gateway | HAProxy Tech | GPLv2 + 企业 | HAProxy 系列的 AI 扩展；高性能 L4/L7 网关 + AI 路由 |
| 9 | F5 NGINX AI Gateway | F5 | OSS + NGINX One | NGF 控制面 + NGINX 数据面 + NGINX One SaaS；3 层分离 |
| 10 | Akamai AI Gateway | Akamai | Cloud | 全球 4200+ 边缘节点；LLM 路由 + 边缘缓存 + 滥用防护 |
| 11 | Cloudflare AI Gateway | Cloudflare | 免费 + 用量 | 全球边缘节点；缓存 / 可观测 / 路由；零运维 |
| 12 | Traefik AI Gateway | Traefik | OSS + Hub | Traefik Proxy 之上的 AI 网关 Add-on |
| 13 | Vercel AI Gateway | Vercel | 用量 | v0 平台后端演化的 unified-model LLM gateway；前端 / Next.js 友好 |
| 14 | Netlify AI Gateway | Netlify | 用量 | Jamstack 平台底座上的统一 LLM 入口 |
| 15 | Bifrost | Maxim AI | MIT + Cloud | Go 写的企业级 LLM / MCP / Agent 统一网关 |
| 16 | Bedrock AgentCore Gateway | AWS | 云 | Bedrock 内的 Agent 运行时网关；绑定 AWS 生态 |
| 17 | Azure APIM (AI Gateway) | Microsoft | 云 | APIM 顶层加 AI 策略；面向 Azure OpenAI；企业级合规 |
| 18 | Istio AI Extension | CNCF / Istio | Apache-2.0 | Istio 1.30+ 的 AI 扩展；服务网格内 AI 流量治理 |
| 19 | Pydantic AI Gateway | Pydantic | 云 | Pydantic 团队 2025-11 推出的 LLM 统一代理；Python 生态深 |
| 20 | Helicone | Helicone | MIT + Cloud | LLM Gateway + 可观测一体；100+ 模型；边缘缓存；Session 追踪 |

---

## ② 模型聚合 / 路由市场（multi-model marketplace）— 19 个

| # | 产品 | 厂商 | 协议/许可 | 一句话定位 |
|---|---|---|---|---|
| 1 | OpenRouter | OpenRouter | SaaS | 模型聚合市场；按 token 路由；模型数最多，被视作 multi-model 入口 |
| 2 | One API | songquanpeng | MIT / AGPL | 国产老牌渠道聚合；OpenAI 协议 + 30+ 国内外渠道 + 多用户计费 |
| 3 | New API | QuantumNous | AGPL | One API 活跃分支；渠道更全；多用户计费完善；二级分销场景 |
| 4 | Unify | Unify AI | SaaS | 模型评测 + 路由；按 cost / latency 自动选模型 |
| 5 | Not Diamond | Not Diamond | SaaS | 按 query 类型选最优模型；决策算法为核心；适合 Agent |
| 6 | Martian | Martian Inc. | SaaS | 强调"模型转换"——任意模型 API 转任意协议；协议适配能力强 |
| 7 | TrueFoundry | TrueFoundry | 企业版 | MLOps 平台 + LLM Gateway；面向企业的部署 + 治理 |
| 8 | Together AI | Together Inc. | 云 | 开源 LLM 全栈平台：推理 / 训练 / 微调 / GPU 集群一体化 |
| 9 | Fireworks AI | Fireworks AI | 云 | OSS LLM 推理优化（Speculative Decoding）；多 LoRA 推理 |
| 10 | DeepInfra | DeepInfra | 云 | imo messenger 团队做的 OpenAI 兼容推理云；100+ OSS 模型 serverless |
| 11 | Replicate | Replicate | 云 | 云端跑任意开源模型；按秒计费；Cog 容器化推理 |
| 12 | Modal | Modal Labs | 云 | Serverless GPU cloud + Code-first deployment + Autoscaling |
| 13 | Lepton AI | Lepton / NVIDIA | 云 | 贾扬清创立，2025-Q1 被 NVIDIA 收购；企业级 LLM 推理云 |
| 14 | RunPod | RunPod | 云 | GPU 租赁 + Serverless 推理；按秒 / 小时计费 |
| 15 | Ollama | Ollama Inc. | MIT | 本地 / 单机 LLM 推理；llama.cpp 包装；OpenAI 兼容 server 模式 |
| 16 | OpenPipe | OpenPipe | 云 | LLM 微调 + 推理；面向生产工作负载的 fine-tuning pipeline |
| 17 | Requesty | Requesty | 云 | LLM 路由 + 优化；智能路由；中长尾模型聚合 |
| 18 | TensorZero | TensorZero (Martian 开源) | MIT | LLM 工业级数据 + 训练 + 推理统一栈；observability 深度集成 |
| 19 | Groq | Groq Inc. | 云 | 自研 LPU + 极速推理（Llama / Mixtral 专长）；按 token 计费 |

---

## ③ 推理引擎 / Self-host 平台（vLLM / SGLang / TGI 等）— 19 个

| # | 产品 | 厂商 | 协议/许可 | 一句话定位 |
|---|---|---|---|---|
| 1 | vLLM | UC Berkeley | Apache-2.0 | PagedAttention 出品；高吞吐 LLM 推理；2026 v1.0；事实标准 |
| 2 | vLLM Production Stack (llm-d) | llm-d 社区 | Apache-2.0 | vLLM 之上的 K8s 生产级包装；路由 / 扩缩 / 可观测 |
| 3 | SGLang | SGLang 团队 | Apache-2.0 | RadixAttention；结构化生成 / Agent 工作负载高效；vLLM 主要竞品 |
| 4 | TGI | HuggingFace | Apache-2.0 | HF 出品的 Rust 推理 server；支持 transformer 一键部署 |
| 5 | Triton Inference Server | NVIDIA | BSD-3 | NVIDIA 多框架推理 server；TensorRT / PyTorch / ONNX |
| 6 | LMDeploy | InternLM / 上海AI Lab | Apache-2.0 | 国产推理引擎；TurboMind 后端；高吞吐低延迟 |
| 7 | llama.cpp | Georgi Gerganov | MIT | CPU / GPU 异构 LLM 推理事实标准；Ollama / LM Studio 等下游 |
| 8 | LocalAI | Mudler | MIT | 开源 OpenAI 替代；Go 写；多 backend 推理；含 LLM Gateway |
| 9 | Mosec | mosecorg | Apache-2.0 | Rust + Python ML 模型服务；动态批处理；多阶段 pipeline |
| 10 | BentoML / BentoCloud | BentoML Inc. | Apache-2.0 | ML 模型打包 / 部署 / 服务；BentoCloud 是托管推理平台 |
| 11 | Anyscale / Ray Serve | Anyscale Inc. | Apache-2.0 | Ray 生态；@serve.llm 装饰器；自营 LLM API + 自建 serving |
| 12 | Baseten | Baseten Inc. | 云 | Truss 模型框架 + Baseten Inference 托管；多 LoRA 优化 |
| 13 | Cerebrium | Cerebrium | 云 | Serverless GPU 推理；冷启动 < 1s；按请求计费 |
| 14 | Beam | Beam Cloud | 云 | Python-first serverless GPU；按秒计费；适合长跑任务 |
| 15 | Hugging Face Inference Endpoints | Hugging Face | 云 | 在 HF Hub 一键部署任意模型；按小时计费 |
| 16 | KServe | CNCF | Apache-2.0 | KFServing 演化；K8s 原生 ML serving；含 Transformer / Predictor |
| 17 | Seldon Core 2 | Seldon | 云 / 自托管 | K8s 原生 ML serving 平台；与 Istio / Envoy 集成 |
| 18 | NVIDIA NIM Operator | NVIDIA | 自托管 | NIM 微服务在 K8s 上的 Operator；GPU 优化部署 |
| 19 | Predibase | Predibase Inc. | Apache-2.0 (LoRAX) | Ludwig 低代码训练 + LoRAX 多 LoRA 推理 + 商业平台 |

---

## ④ 可观测 / 评估 / 护栏（observability / eval / guardrails）— 13 个

| # | 产品 | 厂商 | 协议/许可 | 一句话定位 |
|---|---|---|---|---|
| 1 | LangSmith | LangChain | 云 + 企业 | AI Agent 全生命周期平台：Trace / Evals / Prompt Hub / Fleet / Engine / Sandboxes |
| 2 | Langfuse | Langfuse | MIT + 企业 | 开源 LLM Engineering Platform；Observability / Prompt Mgmt / Evals / Datasets |
| 3 | Arize Phoenix | Arize AI | ELv2 + 企业 | OpenTelemetry 原生 + OpenInference 语义约定；Eval / Experiment |
| 4 | Traceloop | Traceloop | Apache-2.0 | OpenLLMetry 标准制定者；SDK 自动 trace LLM 调用 |
| 5 | W&B Weave | Weights & Biases | 云 + 企业 | LLM 观测 + 评估 + 护栏 + AI Gateway 一体；与 CoreWeave GPU 集成 |
| 6 | Datadog AI Gateway | Datadog | 云 | 原 LLM Observability 子产品；与 Datadog APM / Logs 深度整合 |
| 7 | Braintrust | Braintrust | 云 | LLM Evals / Tracing / Prompt 工程；面向产品团队的评测平台 |
| 8 | DeepEval | Confident AI | Apache-2.0 | LLM 评测框架；类 pytest；20+ 评测指标；CI/CD 集成 |
| 9 | Galileo | Galileo AI | 云 | LLM 评估 / 可观测 / Hallucination 检测；Agent Reliability 平台 |
| 10 | Lunary | Lunary | MIT + Cloud | 轻量 LLM 可观测 + 评测；模块化；早期产品友好 |
| 11 | Promptfoo | Promptfoo | MIT + Cloud | LLM 评测 / 红队 / Prompt 端到端测试；CI/CD 友好 |
| 12 | WhyLabs | WhyLabs / Apple | 云（停止） | AI Observability + Guardrails；2025-01 被 Apple 收购停止商业运营 |
| 13 | MCP Gateway | 社区 | 开源 | MCP 协议专用网关；OpenAPI→MCP 转换；2026 新品类 |

---

## ⑤ 云厂商 / 大厂方案（Cloud Provider AI Gateway）— 7 个

| # | 产品 | 厂商 | 协议/许可 | 一句话定位 |
|---|---|---|---|---|
| 1 | Amazon Bedrock (+ IPR) | AWS | 云 | 100+ foundation model 统一接入；Intelligent Prompt Routing；AgentCore |
| 2 | Google Vertex AI Model Gateway | Google Cloud | 云 | Vertex 控制面 managed gateway；100+ 模型 + Model Armor + MCP tool routing |
| 3 | Azure APIM (AI) | Microsoft | 云 | APIM AI 策略 + Azure OpenAI；企业级合规 / 审计（与①类 Azure AI Gateway 同体系） |
| 4 | 阿里云百炼 + PAI + Higress 商业版 | 阿里云 | 云 | MaaS（百炼）+ PaaS（PAI-EAS）+ API GW（Higress 商业版）三层 |
| 5 | 火山引擎方舟 Ark + APIG | 字节跳动 | 云 | 豆包大模型 + 火山 APIG；MaaS + API GW 套件 |
| 6 | Snowflake Cortex AI | Snowflake | 云 | 数据云上的 AI 套件；模型市场 + Functions + Copilot |
| 7 | Databricks Unity AI Gateway | Databricks | 云 | Unity Catalog 之上的 AI 网关；模型评估 / 路由 / 治理 |

---

## 横向观察（一句话总结）

- **① 核心类** 已高度拥挤：开源三座大山 **Portkey / LiteLLM / Higress**，老牌 API GW 全部加 AI 插件（Kong / APISIX / Envoy / HAProxy / F5 / Traefik / Istio），CNCF 路线有 Solo.io agentgateway 这种 Rust 重写的新叙事。
- **② 聚合类** 是"渠道商"思路的代表：海外 OpenRouter / Unify / Not Diamond 偏智能路由，国内 One API / New API 偏二级分销 + 多用户计费。
- **③ 推理类** vLLM 已经是事实标准，llama.cpp 统治本地；国产 LMDeploy 进入主流行列。
- **④ 观测类** Langfuse（开源）+ LangSmith（商业）是双寡头；Arize Phoenix / Traceloop 在 OpenTelemetry 标准上抢位。
- **⑤ 厂商类** 全在"绑定自家云"——通用网关很难打入大客户，开放中立的中间层仍有空间。

---

**数据基准**：2026-06-08；所有产品均有 `aigw/openclaw/product-*.md` 单产品深挖（60-120 KB / 千行级），可在仓库查阅。
