# Higress AI Gateway 深度调研（2026-06）

> 系列：AI Gateway 单产品深挖 · 第 4 篇
> 目标项目：[Higress](https://github.com/higress-group/higress)（阿里云 / higress-group）
> 调研日期：2026-06-05
> 性质：单产品深挖（覆盖项目背景、架构、协议、性能、部署、成本、生态、案例、对比）
> 信息来源：Higress GitHub README（截至 2026-06-04 抓取）、官方文档站 higress.cn / higress.ai（英文站）、sealos.io 公开技术博客《Scaling to 2,000 Tenants》、官方 v2.2.2 release notes、ai-proxy / ai-cache / ai-statistics / mcp-server 插件源代码、API GitHub 元数据、既往 00-20 系列报告中的相关章节
> 当前快照：GitHub Stars **8,559** / Forks **1,143** / Watchers **8,559** / Open Issues **785** / License **Apache-2.0** / 归属组织 `higress-group`（CNCF Sandbox Project）

---

## 目录

- [一、项目速览与定位](#一项目速览与定位)
- [二、项目背景与公司](#二项目背景与公司)
- [三、架构设计：Istio/Envoy + Wasm + 双形态部署](#三架构设计istioenvoy--wasm--双形态部署)
- [四、控制面与数据面 xDS 协议：Higress Controller 的本质](#四控制面与数据面-xds-协议higress-controller-的本质)
- [五、AI 协议支持：Universal OpenAI / Claude 兼容层](#五ai-协议支持universal-openai--claude-兼容层)
- [六、AI 代理插件（ai-proxy）深度剖析：30+ Provider 矩阵](#六ai-代理插件ai-proxy深度剖析30-provider-矩阵)
- [七、Token 限流、Failover、重试：多 API Key 池化与冷却恢复](#七token-限流failover重试多-api-key-池化与冷却恢复)
- [八、AI 缓存（ai-cache）：向量语义 + Redis 精确双层缓存](#八ai-缓存ai-cache向量语义--redis-精确双层缓存)
- [九、AI 可观测（ai-statistics）：指标 / 日志 / 链路追踪三件套](#九ai-可观测ai-statistics指标--日志--链路追踪三件套)
- [十、MCP Server 托管与 OpenAPI→MCP 转换](#十mcp-server-托管与-openapimcp-转换)
- [十一、性能数据与基准：sealos 2000 租户实测](#十一性能数据与基准sealos-2000-租户实测)
- [十二、部署方式：Docker / K8s / Standalone / Helm / Helm Subchart](#十二部署方式docker--k8s--standalone--helm--helm-subchart)
- [十三、成本模型：开源 + 阿里云企业版 + 飞天专享版](#十三成本模型开源--阿里云企业版--飞天专享版)
- [十四、生态集成：Plugin Hub 与 Wasm 多语言 SDK](#十四生态集成plugin-hub-与-wasm-多语言-sdk)
- [十五、客户案例与典型用户：阿里云内 + 外部企业](#十五客户案例与典型用户阿里云内--外部企业)
- [十六、2026 年关键事件：Ingress Nginx 退役 + v2.2.2 重磅更新](#十六2026-年关键事件ingress-nginx-退役--v222-重磅更新)
- [十七、优劣势分析](#十七优劣势分析)
- [十八、与其他 AI Gateway 对比](#十八与其他-ai-gateway-对比)
- [十九、最佳实践与反模式](#十九最佳实践与反模式)
- [二十、参考资料与索引](#二十参考资料与索引)

---

## 一、项目速览与定位

Higress（读作 /ˈhaɪ.ɡres/，取自"High Gateway + Ingress"）是一个**云原生 API 网关**，**基于 Istio 与 Envoy** 构建，通过 **Wasm 插件**机制实现 Go/Rust/JS 多语言扩展。其官网 README 明确将自身定位为 **"AI Native API Gateway"**，即"AI 原生 API 网关"。

**核心一句话**：

> Higress = Envoy 数据面 + Istio 控制面 + Wasm 扩展运行时 + AI Gateway / MCP Server Hosting / Ingress Controller / 微服务网关 / 安全网关 **五合一**。

GitHub 仓库 8559 stars、1143 forks（截至 2026-06-04），语言 Go，License Apache-2.0，归属组织 `higress-group`（2022-10-27 创建），CNCF Sandbox 项目，OpenSSF Best Practices 徽章。Open Issues 785 表示社区非常活跃。

**与 Portkey / LiteLLM / One API 这类纯 LLM 网关的本质区别**：

| 维度 | Higress | Portkey / LiteLLM / One API |
| --- | --- | --- |
| 出身 | 通用 API 网关 + AI 能力叠加 | 纯 LLM 网关 |
| 流量代理 | 任意 HTTP/RPC 流量 + LLM | 仅 LLM/Embedding 流量 |
| 协议层 | OpenAI / Claude / MCP / A2A / SSE / gRPC / WebSocket / Dubbo | OpenAI 兼容 + 私有方言 |
| 部署 | K8s Ingress / Standalone Docker / Helm | Docker / Cloud |
| 扩展机制 | Wasm 多语言热更新 | 内置 Go/Python 配置 |
| 性能基线 | 十万级 QPS（阿里内） | 万级 QPS |
| 适用场景 | 混合流量 + AI 流量统一治理 | 纯 AI 业务 |

**典型用例**（README 列出 5 大场景）：

1. **MCP Server 托管**：通过插件机制托管 MCP Server，让 AI Agent 容易调用各种工具与服务。
2. **AI Gateway**：统一协议接入 LLM，含可观测、多模型负载均衡、Token 限流、缓存。
3. **K8s Ingress Controller**：兼容大量 nginx-ingress 注解，资源开销显著降低，配置变更速度提升 10 倍。
4. **微服务网关**：从 Nacos/ZooKeeper/Consul/Eureka 等服务注册中心发现服务，深度整合 Dubbo/Nacos/Sentinel。
5. **安全网关**：内置 WAF、Key-Auth / HMAC-Auth / JWT-Auth / Basic-Auth / OIDC 等多种认证。

---

## 二、项目背景与公司

### 2.1 诞生背景

Higress 起源于阿里巴巴内部，原名"内部 Tengine 网关"。Tengine 改造影响长连接服务（gRPC / WebSocket / SSE）的痛点 + 缺乏 gRPC/Dubbo 的高级负载均衡能力，迫使阿里工程师重新设计一套**基于 Envoy + Istio 的网关**。项目从 2022 年起在阿里内部大规模生产，2022-10 正式开源。

### 2.2 阿里云内应用

在阿里云内部，Higress 的 AI Gateway 能力支撑了以下核心 AI 应用：

- **通义千问 / 通义百炼 Model Studio**：阿里云的旗舰 LLM 平台。
- **PAI 机器学习平台**：阿里云的 ML 训练/推理平台。
- 其他关键 AI 服务。

阿里云基于 Higress 构建了云原生 API Gateway 产品，对外提供 **99.99%** 的网关高可用保证服务能力。中文官网（higress.cn）由阿里云维护，英文站（higress.ai）面向全球社区。

### 2.3 商业化产品（基于开源 Higress）

阿里云对外销售三档商业产品：

| 档位 | SLA | 部署方式 | 适用 |
| --- | --- | --- | --- |
| 社区版 | 社区支持 | 自托管 | 验证、个人/小团队 |
| 企业版 | 99.95% | 阿里云全托管 | 通用生产 |
| 飞天专享版 | 可谈判 | 阿里云独立部署 | 大型/合规要求高 |

### 2.4 关键人物与组织

- 主仓库维护者 `@johnlanni`（GitHub id 6763318），v2.2.2 release 也由其发布。
- 阿里云高级工程师团队持续贡献（含"如漫"、"望宸"、"梧同"、"子葵"、"张添翼"等名字出现在官方博客署名）。
- 项目已经从单纯的 alibaba/higress 仓库迁移到独立组织 **higress-group**（org id 116630909），higress-group 旗下还有：
  - higress-console（Higress 控制台）
  - higress-standalone（独立模式部署工具）
  - plugin-server（插件托管服务）
  - wasm-go（Go Wasm 插件 SDK）
  - openapi-to-mcpserver（OpenAPI → MCP Server 自动转换工具）

### 2.5 CNCF 治理

- **CNCF Sandbox Project**：2024 年进入 CNCF Sandbox，是 CNCF 第一个明确主打"AI Gateway"定位的项目。
- **OpenSSF Best Practices**：通过 OpenSSF 安全最佳实践徽章（bestpractices.dev/projects/12667）。
- **Apache-2.0 License**：可商用、可修改、可分发，但需保留版权与免责声明。

---

## 三、架构设计：Istio/Envoy + Wasm + 双形态部署

Higress 的整体架构由 **三大核心** 组成：

```
┌──────────────────────────────────────────────────────────────────┐
│                       Higress 全景架构                            │
│                                                                  │
│  ┌─────────────────┐    xDS/CRD   ┌──────────────────────┐      │
│  │  Higress        │ ───────────► │  Istio Pilot         │      │
│  │  Controller     │             │  (xDS Server)        │      │
│  │  (控制面)       │             └──────────┬───────────┘      │
│  │                 │                        │                   │
│  │  - Ingress/     │                        │ xDS               │
│  │    Gateway API  │                        ▼                   │
│  │    CRD 解析     │             ┌──────────────────────┐       │
│  │  - 配置存储     │             │  Envoy Data Plane    │       │
│  │    (K8s/        │             │  (Higress Gateway)   │       │
│  │     Nacos/      │             │                      │       │
│  │     Local File) │             │  - HTTP L7 代理      │       │
│  │  - 路由生成     │             │  - gRPC/Dubbo L4     │       │
│  │  - 插件编排     │             │  - Wasm 插件运行时   │       │
│  └─────────────────┘             │  - LLM/MCP 协议处理  │       │
│                                  │  - 指标/日志/Trace   │       │
│                                  └──────────┬───────────┘      │
│                                             │                   │
│                                             ▼                   │
│                              ┌──────────────────────────┐      │
│                              │  Upstream 服务           │      │
│                              │  - LLM Providers         │      │
│                              │  - MCP Servers           │      │
│                              │  - 微服务（HTTP/gRPC/...）│      │
│                              │  - 数据库/缓存           │      │
│                              └──────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

### 3.1 双形态部署

Higress 提供两种部署形态：

**(A) K8s 模式（标准模式）**
- 部署在 K8s 集群中，作为 K8s Ingress Controller 或 Gateway API 实现者。
- 配置存放在 K8s CRD（Ingress / Gateway / HTTPRoute / Higress 自定义 CRD）。
- 适合生产云原生环境。

**(B) Standalone 模式（独立模式）**
- 通过 `get-higress.sh` 或 `docker run` 启动。
- 配置存储可选择：**本地文件** 或 **Nacos**。
- 适合个人开发者、本地测试、混合云、边缘场景。
- 这是 Higress 区别于 Envoy Gateway / Istio Gateway 最显著的设计——后者必须依赖 K8s。

```
# 启动 Standalone 本地文件模式
mkdir higress && cd higress
docker run -d --rm --name higress-ai -v ${PWD}:/data \
        -p 8001:8001 -p 8080:8080 -p 8443:8443  \
        higress-registry.cn-hangzhou.cr.aliyuncs.com/higress/all-in-one:latest

# 启动 Standalone Nacos 模式
curl -fsSL https://higress.io/standalone/get-higress.sh | bash -s -- -a -c nacos://192.168.0.1:8848
```

### 3.2 Higress Controller：与原生 Istio 的关键差异

Higress Controller 是控制面，**直接与 Istio Pilot 对接**，通过 xDS 协议把配置下发到 Envoy 数据面。它与原生 Istio 最大的不同在于：

1. **配置 CRD 化**：将 Ingress / Gateway API / 插件配置统一为 K8s CRD（higress-config、ai-route、ai-service-provider 等），比原生 Istio 简单。
2. **配置存储可插拔**：支持 K8s Etcd / Nacos / 本地文件，K8s 不是唯一选择。
3. **插件机制自研**：Higress 在 Envoy Wasm 之上封装了更易用的插件协议（`plugin-server` + `wasm-go` SDK）。

### 3.3 Wasm 插件机制

Wasm（WebAssembly）是 Higress 的灵魂：

```
┌────────────────────────────────────────────────────────┐
│              Higress Wasm 插件执行模型                  │
│                                                        │
│  收到请求                                               │
│     │                                                  │
│     ▼                                                  │
│  ┌─────────────────┐                                   │
│  │ Authn 阶段       │  ← key-auth, jwt-auth, oidc 等    │
│  │ (priority 10)   │                                   │
│  └────────┬────────┘                                   │
│           ▼                                            │
│  ┌─────────────────┐                                   │
│  │ Default 阶段     │  ← ai-proxy (100) /              │
│  │ (priority 100)  │    ai-cache (10) /                │
│  │                 │    ai-statistics (200) /          │
│  │                 │    ai-ratelimit / prompt-decorator│
│  └────────┬────────┘                                   │
│           ▼                                            │
│  ┌─────────────────┐                                   │
│  │ Upstream 转发    │  ← 实际发起上游请求               │
│  └────────┬────────┘                                   │
│           ▼                                            │
│  ┌─────────────────┐                                   │
│  │ Default 阶段(响应)│  ← 流式/非流式响应处理            │
│  └────────┬────────┘                                   │
│           ▼                                            │
│  返回响应                                               │
└────────────────────────────────────────────────────────┘
```

**核心优势**：
- **多语言**：Go（最成熟）、Rust、JS（tinygo/QuickJS）。
- **沙箱隔离**：Wasm 沙箱天然安全，插件崩溃不会让整个网关挂掉。
- **热更新**：插件版本独立升级，**流量无损热更新**（对比 Nginx reload 时长连接抖动）。
- **可观测**：每个插件的 CPU/内存可观测。

### 3.4 关键仓库拓扑

```
higress-group/
├── higress                 ← 主仓库（控制面 + 数据面构建脚本）
├── higress-console         ← 前端控制台
├── higress-standalone      ← 独立模式部署工具
├── plugin-server           ← 插件托管服务（CRD 配置 → xDS）
├── wasm-go                 ← Go Wasm 插件 SDK
├── openapi-to-mcpserver    ← OpenAPI → MCP Server 转换器
└── ...                     ← 其他工具
```

---

## 四、控制面与数据面 xDS 协议：Higress Controller 的本质

### 4.1 xDS 协议族

Higress 数据面（Envoy）通过 Envoy 标准 xDS 协议与控制面通信：

| xDS 协议 | 用途 | Higress 是否使用 |
| --- | --- | --- |
| LDS（Listener Discovery Service） | 监听器配置 | ✅ |
| RDS（Route Discovery Service） | 路由配置 | ✅ |
| CDS（Cluster Discovery Service） | 集群（上游）配置 | ✅ |
| EDS（Endpoint Discovery Service） | 端点（实例）配置 | ✅ |
| SDS（Secret Discovery Service） | 密钥/TLS 证书 | ✅ |

Higress 通过 Istio Pilot 提供 xDS 服务，自己只负责生成 Istio 风格的配置 CRD。

### 4.2 配置存储：可插拔

Higress Controller 支持多种配置后端：

1. **K8s Etcd**（K8s 模式默认）
2. **Nacos**（Standalone 模式可选，阿里生态）
3. **Local File**（Standalone 模式默认，本地 JSON/YAML）

这意味着 Higress **不强制 K8s 依赖**，这是 Higress 相比 Envoy Gateway / Kong K8s 的关键优势。

### 4.3 增量配置加载（性能核心）

参考 sealos 公开博客，Higress 在大规模路由表下表现优异的关键是**增量 xDS 下发**：

- **Nginx Ingress**：每次配置变更触发 `nginx -s reload`，所有 worker 进程需重新加载配置，**长连接会断**。
- **Higress/Envoy**：xDS 增量推送，只更新变更的 Listener/Route/Cluster，**长连接保持**。

sealos 实测：2000 个 Ingress 条目时，Higress 新路由生效约 **3 秒**，Envoy Gateway / APISIX 普遍 30-120 秒。

---

## 五、AI 协议支持：Universal OpenAI / Claude 兼容层

Higress AI Gateway 最强的地方在于**多协议自动识别 + 转换**。它在 `ai-proxy` 插件中实现了**Universal Protocol** 模式：

### 5.1 请求路径后缀 → 协议

| 请求路径后缀 | 协议场景 | 默认解析 |
| --- | --- | --- |
| `/v1/chat/completions` | 文生文 | OpenAI Chat Completions |
| `/v1/messages` | Claude 文生文 | 自动检测（OpenAI→Claude 转换或原生 Claude） |
| `/v1/embeddings` | 文本向量化 | OpenAI Embeddings |
| `/v1/images/generations` | 文生图 | OpenAI Image Generation |
| `/v1/audio/speech` | 语音合成 | OpenAI Audio |
| `/v1/rerank` | 重排序 | Cohere Rerank |
| `mcp.sse` / Streamable HTTP | MCP 协议 | MCP 2025-03-26 |

### 5.2 自动协议兼容（Auto Protocol Compatibility）

`ai-proxy` 插件支持**零配置**的协议自动检测：

- 客户端发送 **OpenAI 格式**（`/v1/chat/completions`）→ 插件自动检测目标 provider 是否原生支持；若不支持（如阿里通义），自动转换为通义 DashScope 协议。
- 客户端发送 **Claude 格式**（`/v1/messages`）→ 插件自动检测目标 provider 是否原生支持 Claude；若不支持（如 OpenAI 兼容的 vllm），先转 OpenAI 协议再转发。

这与 Portkey / LiteLLM 的 `protocol: "openai"` 字段相比，**更自动化**。

### 5.3 自定义 OpenAI 兼容端点

通过 `openaiCustomUrl` 字段支持任意 OpenAI 协议兼容的后端：

```yaml
provider:
  type: openai
  openaiCustomUrl: https://my-mock-openai.example.com/v1/chat/completions
```

这意味着任何"伪装成 OpenAI"的服务（如 vLLM、Ollama 兼容模式、自建代理）都能接入。

### 5.4 MCP 协议支持

Higress 2.1.0+ 引入 MCP Server 托管能力，支持：

- **MCP SSE 协议**（旧版 2024-11-05）
- **MCP Streamable HTTP**（新版 2025-03-26）

Higress 在 MCP 场景的核心创新是 **OpenAPI→MCP 自动转换**：通过 `openapi-to-mcpserver` 工具，可以把任意 OpenAPI 规范自动转换为 MCP Server 插件配置，**零代码**把 REST API 变成 MCP 工具。

---

## 六、AI 代理插件（ai-proxy）深度剖析：30+ Provider 矩阵

`ai-proxy` 插件是 Higress AI Gateway 的核心，负责**协议适配 + Provider 转发 + 模型映射 + 限流 + 重试 + 缓存协同**。

### 6.1 Provider 完整列表（30+）

从 GitHub 仓库 `plugins/wasm-go/extensions/ai-proxy/provider/` 目录可确认 Higress 已实现的 30+ Provider（按字母序）：

| Provider | 协议 | 备注 |
| --- | --- | --- |
| **ai360** | 360 智脑 | 中文 |
| **azure** | Azure OpenAI | 完整 v1/legacy 支持 |
| **baichuan** | 百川智能 | 中文 |
| **baidu** | 文心一言 | 中文 |
| **bedrock** | AWS Bedrock | 支持 Anthropic Messages 直连 |
| **claude** | Anthropic Claude | Claude Code 模式 |
| **cloudflare** | Cloudflare Workers AI | 边缘推理 |
| **cohere** | Cohere | rerank/embed |
| **coze** | 扣子 | 字节系 Agent 平台 |
| **custom_setting** | 自定义参数注入 | 通用 |
| **deepl** | DeepL 翻译 | 文生文 |
| **deepseek** | DeepSeek | 推理模型 |
| **dify** | Dify | LLM 应用平台 |
| **doubao** | 豆包 | 字节系 |
| **failover** | 多 API Token 故障转移 | 通用 |
| **fireworks** | Fireworks AI | 推理优化 |
| **gemini** | Google Gemini | |
| **generic** | 通用兜底 | 自定义 URL |
| **github** | GitHub Models | |
| **grok** | xAI Grok | |
| **groq** | Groq | 超低延迟 |
| **hunyuan** | 腾讯混元 | |
| **kling** | 可灵 | 文生视频/图生视频 |
| **longcat** | 龙猫 | |
| **minimax** | MiniMax | v2 / pro 双 API |
| **mistral** | Mistral AI | |
| **model** | 通用模型定义 | |
| **moonshot** | 月之暗面 Kimi | 1M 上下文 |
| **multipart_helper** | 多模态支持 | 通用 |
| **ollama** | Ollama | 本地推理 |
| **openai** | OpenAI | 默认基线 |
| **openrouter** | OpenRouter | 路由聚合 |
| **provider** | Provider 抽象基类 | |
| **qwen** | 通义千问 | 兼容模式可选 |
| **request_helper** | 请求辅助 | 通用 |
| **retry** | 重试逻辑 | 通用 |
| **spark** | 讯飞星火 | |
| **stepfun** | 阶跃星辰 | |
| **together_ai** | Together AI | 推理优化 |
| **triton** | NVIDIA Triton | 自建推理 |
| **vertex** | Google Vertex AI | |
| **vllm** | vLLM | 自建推理 |
| **yi** | 零一万物 | |
| **zhipuai** | 智谱 AI | |

这是当前**最完整的 AI Provider 矩阵之一**——同时覆盖 OpenAI/Anthropic/Google/中国六大系（百度/阿里/腾讯/字节/智谱/月之暗面/百川/零一万物/阶跃/讯飞）以及自建推理（vLLM/Triton/Ollama）。

### 6.2 核心配置字段（`provider` 对象）

```yaml
provider:
  type: openai                    # Provider 类型
  apiTokens:                      # 多个 Token 池化
    - sk-key-1
    - sk-key-2
  timeout: 120000                 # 2 分钟
  modelMapping:                   # 模型名映射
    "gpt-3-*": "gpt-3.5-turbo"   # 前缀匹配
    "*": "qwen-max"               # 兜底
    "~gpt(.*)": "openai/gpt$1"   # 正则匹配
  protocol: openai                # openai / original
  context:                        # 上下文注入
    fileUrl: "https://example.com/context.txt"
    serviceName: "context-service"
    servicePort: 8080
  customSettings:                 # 参数注入
    - name: max_tokens
      value: 0
      mode: auto                  # auto / raw
      overwrite: true
  failover:                       # API Token 故障转移
    enabled: true
    failureThreshold: 3
    successThreshold: 1
    healthCheckInterval: 5000
    healthCheckTimeout: 5000
    healthCheckModel: "gpt-3.5-turbo"
    cooldownDuration: 30000
    failoverOnStatus: ["4.*", "5.*"]
  retryOnFailure:                 # 失败重试
    enabled: true
    maxRetries: 1
    retryTimeout: 30000
    retryOnStatus: ["4.*", "5.*"]
  reasoningContentMode: passthrough  # reasoning_content 处理
  capabilities:                   # 能力透传（避免重写）
    openai/v1/chatcompletions: /v1/chat/completions
  basePath: /v1                   # 路径前缀处理
  basePathHandling: removePrefix  # removePrefix / prepend
  contextCleanupCommands:         # 上下文清理
    - "/clear"
    - "/reset"
```

### 6.3 自定义参数（custom-setting）的协议映射

`custom-setting` 是 Higress 的杀手锏之一。`mode: auto` 时自动按协议重写参数名：

| settingName | openai | baidu | spark | qwen | gemini | hunyuan | claude | minimax |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| max_tokens | max_tokens | max_output_tokens | max_tokens | max_tokens | maxOutputTokens | none | max_tokens | tokens_to_generate |
| temperature | temperature | temperature | temperature | temperature | temperature | Temperature | temperature | temperature |
| top_p | top_p | top_p | none | top_p | topP | TopP | top_p | top_p |
| top_k | none | none | top_k | none | topK | none | top_k | none |
| seed | seed | none | none | seed | none | none | none | none |

`mode: raw` 时不做任何改写，直接传 raw JSON。

### 6.4 模型映射的高级玩法

```yaml
modelMapping:
  # 1. 简单别名
  "my-llm": "qwen-max"
  
  # 2. 前缀匹配
  "gpt-3-*": "qwen-turbo"
  
  # 3. 通配符兜底
  "*": "qwen-max"
  
  # 4. 正则匹配 + 捕获组引用
  "~gpt(.*)": "openai/gpt$1"
  
  # 5. 显式保留原名
  "gpt-4-turbo": ""  # 透传
```

### 6.5 Claude Code 模式（v2.1+ 新增）

v2.2.x 引入 `claudeCodeMode`，让 Higress 能直接使用 Claude Code 的 OAuth Token 访问 Anthropic API：

```yaml
provider:
  type: claude
  claudeCodeMode: true
  apiTokens:
    - "sk-ant-oat01-..."  # Claude Code OAuth Token
```

启用后：
- Bearer Token 替代 x-api-key
- 设置 Claude Code 特定 user-agent / x-app / anthropic-beta 头
- URL 添加 `?beta=true` 查询参数
- 自动注入 Claude Code 的系统提示词

---

## 七、Token 限流、Failover、重试：多 API Key 池化与冷却恢复

Higress 在 AI 场景的可靠性设计比 Portkey / LiteLLM 更细。`ai-proxy` 插件的 `failover` + `retryOnFailure` 配合使用，构成**多 API Key 池 + 失败重试 + 冷却恢复**体系。

### 7.1 API Token Failover 机制

```yaml
failover:
  enabled: true
  failureThreshold: 3              # 连续 3 次失败触发
  successThreshold: 1              # 健康检测通过需 1 次成功
  healthCheckInterval: 5000        # 健康检测间隔 5s
  healthCheckTimeout: 5000         # 健康检测超时 5s
  healthCheckModel: "gpt-3.5-turbo"  # 用轻量模型做健康检查
  cooldownDuration: 30000          # 冷却 30s 后自动恢复
  failoverOnStatus: ["4.*", "5.*"] # 4xx/5xx 触发
```

**工作流程**：

```
Request 1 → Token A (200)            ✓
Request 2 → Token A (200)            ✓
Request 3 → Token A (429)            ✗  计数+1
Request 4 → Token A (429)            ✗  计数+2
Request 5 → Token A (429)            ✗  计数+3 → 触发 failover
           → 切换到 Token B          ✓  B 健康
           
# 同时：Token A 进入冷却状态
# 5s 后开始健康检查
# 健康检查用 healthCheckModel 调用 Token A
# successThreshold 1 次成功 → Token A 回到 Token 池
```

### 7.2 重试（retryOnFailure）

```yaml
retryOnFailure:
  enabled: true
  maxRetries: 1
  retryTimeout: 30000
  retryOnStatus: ["4.*", "5.*"]
```

注意：**只对非流式请求重试**。流式请求一旦开始就不可重试。

### 7.3 与 Portkey / LiteLLM 的对比

| 维度 | Higress | Portkey | LiteLLM |
| --- | --- | --- | --- |
| API Key Failover | ✅ 健康检查 + 冷却 | ✅ 简单轮换 | ✅ 复杂 Cooldown |
| 自动重试 | ✅ 配置粒度 | ✅ | ✅ |
| 模型映射 | ✅ 5 种模式 | ✅ | ✅ |
| 上下文清理 | ✅ contextCleanupCommands | ❌ | ❌ |
| Reasoning 处理 | ✅ passthrough/ignore/concat | ⚠️ 基础 | ✅ |
| 健康检查 | ✅ 可配置 | ❌ | ⚠️ 简单 |
| 多 Token 池 | ✅ 同一 Provider 多 Token | ✅ | ✅ |

---

## 八、AI 缓存（ai-cache）：向量语义 + Redis 精确双层缓存

`ai-cache` 插件是 Higress AI Gateway 的**差异化杀手锏**之一。它同时支持：

1. **字符串精确匹配缓存**（Redis）
2. **向量语义缓存**（7+ 向量数据库后端）

### 8.1 配置架构

```yaml
# 字符串精确缓存（Redis）
cache:
  type: redis
  serviceName: redis.static
  servicePort: 6379
  cacheTTL: 3600
  cacheKeyPrefix: "higress-ai-cache:"

# 向量语义缓存
vector:
  type: dashvector                # 7+ 后端可选
  serviceName: dashvector.static
  servicePort: 443
  apiKey: "sk-xxx"
  topK: 1
  threshold: 0.95
  thresholdRelation: "gt"        # Cosine 用 gt
  collectionID: "my-collection"

# 文本向量化服务
embedding:
  type: dashscope                # 7+ 后端可选
  serviceName: dashscope.static
  servicePort: 443
  apiKey: "sk-xxx"
  model: "text-embedding-v3"

# 缓存策略
cacheKeyStrategy: "lastQuestion"  # lastQuestion/allQuestions/disabled
enableSemanticCache: true
```

### 8.2 向量数据库后端（7+）

| vector.type | 描述 |
| --- | --- |
| **dashvector** | 阿里云 DashVector |
| **chroma** | 开源 Chroma |
| **elasticsearch** | ElasticSearch（需 KNN 支持，8.16+ 测试通过） |
| **weaviate** | Weaviate |
| **pinecone** | Pinecone |
| **qdrant** | Qdrant |
| **milvus** | Milvus |

### 8.3 Embedding Provider（7+）

| embedding.type | 描述 |
| --- | --- |
| **dashscope** | 阿里云 DashScope（默认 text-embedding-v3） |
| **openai** | OpenAI text-embedding-3 |
| **azure** | Azure OpenAI |
| **cohere** | Cohere |
| **ollama** | Ollama（本地） |
| **huggingface** | Hugging Face（默认 sentence-transformers/all-MiniLM-L6-v2） |
| **textin** | 合合信息 |
| **xfyun** | 讯飞星火 |

### 8.4 GJSON 路径灵活提取

```yaml
cacheKeyFrom: "messages.@reverse.0.content"          # 最后一条用户消息
cacheValueFrom: "choices.0.message.content"          # 非流式响应
cacheStreamValueFrom: "choices.0.delta.content"      # 流式响应
cacheToolCallsFrom: "choices.0.delta.content.tool_calls"  # 工具调用
```

通过 [GJSON](https://github.com/tidwall/gjson) 路径语法，从复杂的请求/响应 JSON 中提取任意字段作为缓存键值。

### 8.5 双层缓存协同

```
Request → cacheKeyFrom 提取 key
          ↓
       cache (Redis) 字符串精确匹配
          ↓ miss
       vector (DashVector/Milvus) 语义相似度匹配
          ↓ miss
       上游 LLM Provider 调用
          ↓
       写入 cache (Redis)
       写入 vector (DashVector)
```

这种**双层架构**在 Higress 中实现得非常彻底，比 LiteLLM 的"单层缓存"或 Portkey 的"简单缓存"更强大。

### 8.6 响应模板

```yaml
responseTemplate: |
  {"id":"from-cache","choices":[{"index":0,"message":{"role":"assistant","content":"%s"},"finish_reason":"stop"}],"model":"from-cache","object":"chat.completion","usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}}

streamResponseTemplate: |
  data:{"id":"from-cache","choices":[{"index":0,"delta":{"role":"assistant","content":"%s"},"finish_reason":"stop"}],"model":"from-cache","object":"chat.completion","usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}}
  \n\ndata:[DONE]\n\n
```

通过 `%s` 占位符，可以自定义缓存返回的响应格式（保持 OpenAI 协议兼容）。

### 8.7 跳过缓存

携带 `x-higress-skip-ai-cache: on` 头时，该请求**不读缓存也不写缓存**——适合调试和敏感场景。

---

## 九、AI 可观测（ai-statistics）：指标 / 日志 / 链路追踪三件套

`ai-statistics` 插件提供**指标 / 日志 / 链路追踪**三件套，与 `ai-proxy` 配合使用。

### 9.1 内置指标（Prometheus 格式）

| 指标 | 类型 | 描述 |
| --- | --- | --- |
| `route_upstream_model_consumer_metric_input_token` | counter | 输入 token 累加 |
| `route_upstream_model_consumer_metric_output_token` | counter | 输出 token 累加 |
| `route_upstream_model_consumer_metric_llm_service_duration` | counter | 总 RT 累加 |
| `route_upstream_model_consumer_metric_llm_duration_count` | counter | 请求次数 |
| `route_upstream_model_consumer_metric_llm_first_token_duration` | counter | 首 token RT 累加（流式） |
| `route_upstream_model_consumer_metric_llm_stream_duration_count` | counter | 流式请求次数 |

**标签维度**：
- `ai_route`：网关路由
- `ai_cluster`：上游集群
- `ai_model`：模型名
- `ai_consumer`：消费者（配合认证）

### 9.2 常用 PromQL 查询

```promql
# 流式请求首 token 平均延时
irate(route_upstream_model_consumer_metric_llm_first_token_duration[2m])
/ 
irate(route_upstream_model_consumer_metric_llm_stream_duration_count[2m])

# 总请求平均耗时
irate(route_upstream_model_consumer_metric_llm_service_duration[2m])
/ 
irate(route_upstream_model_consumer_metric_llm_duration_count[2m])

# 每分钟总 token 消耗
sum by (ai_model) (
  rate(route_upstream_model_consumer_metric_input_token[5m]) +
  rate(route_upstream_model_consumer_metric_output_token[5m])
)
```

### 9.3 内置属性（Built-in Attributes）

`ai-statistics` 2.x 引入内置属性，**无需配置 value_source** 即可自动提取：

| 内置 Key | 描述 | 适用 |
| --- | --- | --- |
| `question` | 用户提问内容 | OpenAI/Claude |
| `system` | 系统提示词 | Claude `/v1/messages` |
| `answer` | AI 回答 | 流式 + 非流式 |
| `tool_calls` | 工具调用 | OpenAI/Claude |
| `reasoning` | 思考过程 | o1/DeepSeek-R1 |
| `reasoning_tokens` | 推理 token 数 | o1 |
| `cached_tokens` | 缓存命中 token | OpenAI |
| `input_token_details` | 输入 token 详情 | OpenAI/Gemini/Claude |
| `output_token_details` | 输出 token 详情 | OpenAI/Gemini/Claude |

### 9.4 流式响应提取规则

```yaml
attributes:
  - key: answer
    value_source: response_streaming_body
    value: choices.0.delta.content
    rule: append                  # first / replace / append
    apply_to_log: true
```

- `first`：取第一个有效 chunk
- `replace`：取最后一个有效 chunk
- `append`：拼接所有 chunk（用于流式回答）

### 9.5 Session ID 自动追踪

```yaml
session_id_header: "x-session-id"  # 自定义 header
# 也可省略，会自动按以下优先级查找：
# x-openclaw-session-key
# x-clawdbot-session-key
# x-moltbot-session-key
# x-agent-session
```

通过 session ID，可以追踪多轮 Agent 对话的完整成本。

### 9.6 与 OpenLLMetry 的差异

`ai-statistics` 内置的 token 统计来自**网关侧的协议解析**（读取 usage 字段），**不依赖应用端埋点**。这与 OpenLLMetry（应用层 OTel）形成互补：

- **ai-statistics**：网关层统计，全量、零侵入
- **OpenLLMetry**：应用层统计，更细粒度（包含应用上下文）

Higress 的做法比 OpenLLMetry 部署更简单，但精度略低（如果应用层做了 prompt 二次组装，网关可能看不到完整内容）。

---

## 十、MCP Server 托管与 OpenAPI→MCP 转换

Higress 在 MCP 场景的创新是**把 MCP Server 变成"网关原生能力"**——通过插件机制托管，让任意 REST API / 数据库 / Nacos 服务**零代码**变成 MCP 工具。

### 10.1 三种 MCP Server 来源

**(A) 数据库类型 MCP Server**

```yaml
# ConfigMap
servers:
  - name: postgres
    path: /postgres
    type: database
    config:
      dsn: "postgresql://user:pass@host:5432/db"
      dbType: "postgres"  # postgres/mysql/clickhouse/sqlite
```

支持的数据库：`postgres` / `mysql` / `clickhouse` / `sqlite`。

**(B) REST API 类型 MCP Server**

通过 Higress Console 添加 Service Source + Route + MCP Server 插件，零代码转换：

```yaml
server:
  name: "random-user-server"
  tools:
    - description: "Get random user information"
      name: "get-user"
      requestTemplate:
        method: "GET"
        url: "https://randomuser.me/api/"
      responseTemplate:
        body: |-
          # User Information
          {{- with (index .results 0) }}
          - **Name**: {{.name.first}} {{.name.last}}
          {{- end }}
```

使用 Go template 语法构造响应。

**(C) Nacos 类型 MCP Server**

```yaml
# Nacos 3.x 注册的 MCP 服务
# 访问 URL: http://mcp-registry.com/mcp/{name}/sse
# 支持两种模式：
# 1. REST API → MCP 转换
# 2. 直接代理原生 MCP 服务
```

### 10.2 MCP 会话粘性（SSE 长连接）

MCP 使用 SSE 长连接，Higress 通过 Redis 实现**会话粘性**：

```yaml
mcpServer:
  sse_path_suffix: /sse
  enable: true
  redis:
    address: redis-stack-server.higress-system.svc.cluster.local:6379
  match_list:
    - match_rule_domain: "*"
      match_rule_path: /postgres
      match_rule_type: "prefix"
```

会话粘性确保同一 MCP 客户端的请求**路由到同一个 Envoy 实例**，避免 SSE 长连接中断。

### 10.3 MCP 协议版本

- **SSE 协议**（2024-11-05）：ConfigMap 模式
- **Streamable HTTP**（2025-03-26）：ConfigMap 不需配置，自动识别

### 10.4 OpenAPI→MCP 自动转换

```bash
# 安装工具
npm install -g @higress-group/openapi-to-mcpserver

# 把 OpenAPI 文件转 MCP Server 插件配置
openapi-to-mcp --input openapi.yaml --output mcp-server-config.yaml
```

这是 Higress 独创的功能：把任意 OpenAPI 规范的 REST API，**零代码**转成 MCP 工具。与 FastMCP（Python）等工具相比，Higress 把转换结果**直接作为插件部署在网关**——不需要单独的 MCP Server 进程。

### 10.5 在线体验

官方提供 [https://mcp.higress.ai/](https://mcp.higress.ai/) 在线演示托管的 Remote MCP Servers。

---

## 十一、性能数据与基准：sealos 2000 租户实测

### 11.1 sealos 公开基准

sealos.io 公开博客《Scaling to 2,000 Tenants: Why Sealos Moved from Nginx to Envoy》提供了 Higress 在大规模生产环境的真实性能数据。

**测试场景**：2000 个租户，每个租户需要独立 Ingress 条目，总计 2000+ Ingress 资源。

#### 11.1.1 路由生效时间

| 方案 | 新路由生效时间 |
| --- | --- |
| **Nginx Ingress** | 30-60 秒（reload） |
| **APISIX** | 5-30 秒（增量推送不稳定） |
| **Cilium Gateway** | 分钟级（实测数分钟，不满足 SLA） |
| **Envoy Gateway**（早期版本） | 10-30 秒（OOM/PathPolicy bug） |
| **Higress** | **~3 秒**（增量 xDS + 社区优化） |

#### 11.1.2 资源消耗对比

| 方案 | CPU（2000 Ingress） | 内存 | 备注 |
| --- | --- | --- | --- |
| Nginx Ingress | 4-8 核 | 4-8 GB | OOM 频发 |
| Higress Controller | 0.5-1 核 | 1-2 GB | 稳定 |
| Higress Gateway | 2-4 核 | 2-4 GB | 高并发下仍低 |

#### 11.1.3 长连接稳定性

- **Nginx Ingress**：reload 时长连接会断，AI 业务不可接受
- **Higress**：xDS 增量推送，**长连接保持**

### 11.2 阿里内生产数据（README 暗示）

- "**2+ 年生产验证**"
- "**十万级 QPS**"（hundreds of thousands of requests per second）

> 注：阿里未公开具体 benchmark 数据，以上为定性描述。

### 11.3 性能优化关键技术

1. **增量 xDS 下发**：避免全量推送
2. **Wasm 沙箱**：避免插件影响主进程
3. **流式处理**：支持 SSE / chunked 完整流式，**避免大 body 缓存**（对 AI 业务至关重要）
4. **零拷贝**：Envoy 内部 L7 转发使用 zero-copy

### 11.4 与 LiteLLM Proxy 的对比基准（参考 14 报告）

参考既往 `14-performance-benchmark.md` 报告结论，**纯 LLM 场景下**：

| 维度 | Higress | LiteLLM Proxy | Portkey |
| --- | --- | --- | --- |
| 单 LLM 请求 P50 | ~5ms 转发开销 | ~10ms 转发开销 | ~8ms 转发开销 |
| 流式首 token 延迟 | **几乎无开销**（流式原生） | ~10-20ms 缓冲 | ~15ms 缓冲 |
| 缓存命中响应 | **< 1ms** | ~2-5ms | ~3-8ms |
| 10K 并发 | **稳定** | 中等 | 中等 |
| 100K 并发 | **可扩展** | 需要水平扩展 | 需要水平扩展 |

> 注：以上为定性比较，精确数字需以具体 benchmark 为准。

---

## 十二、部署方式：Docker / K8s / Standalone / Helm / Helm Subchart

Higress 提供 **5 种部署方式**，覆盖个人开发者到企业生产。

### 12.1 Docker 一键启动（个人/学习）

```bash
mkdir higress; cd higress
docker run -d --rm --name higress-ai -v ${PWD}:/data \
        -p 8001:8001 -p 8080:8080 -p 8443:8443  \
        higress-registry.cn-hangzhou.cr.aliyuncs.com/higress/all-in-one:latest
```

- 端口 8001：Higress Console UI
- 端口 8080：HTTP 网关入口
- 端口 8443：HTTPS 网关入口
- 配置存到本地 `${PWD}` 目录

### 12.2 AI Gateway 一键部署

```bash
curl -sS https://higress.cn/ai-gateway/install.sh | bash
```

- 启动时输入 Provider API Key（或后续在 Console 配置）
- 自动配置 OpenAI / DeepSeek / 阿里云百炼 / 豆包 / Azure OpenAI

### 12.3 K8s Helm 部署（生产标准）

```bash
helm repo add higress.io https://higress.io/helm-charts
helm install higress -n higress-system higress.io/higress --create-namespace --render-subchart-notes
```

获取 Gateway IP：

```bash
kubectl get svc -n higress-system higress-gateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### 12.4 本地 K8s（kind）部署

```bash
# 安装 kind + kubectl
# 创建集群
kind create cluster --name higress --config=cluster.conf

# 本地安装
helm install higress -n higress-system higress.io/higress \
  --create-namespace --render-subchart-notes \
  --set global.local=true \
  --set global.o11y.enabled=false
```

### 12.5 Standalone + Nacos

```bash
curl -fsSL https://higress.io/standalone/get-higress.sh | bash -s -- -a -c nacos://192.168.0.1:8848 \
  --nacos-username=nacos --nacos-password=nacos
```

适合**非 K8s 环境**的混合云/边缘部署。

### 12.6 镜像加速

Higress 镜像托管在阿里云 ACR，提供 3 个区域镜像：

| 区域 | Registry |
| --- | --- |
| 中国（杭州） | `higress-registry.cn-hangzhou.cr.aliyuncs.com` |
| 北美 | `higress-registry.us-west-1.cr.aliyuncs.com` |
| 东南亚 | `higress-registry.ap-southeast-7.cr.aliyuncs.com` |

K8s 部署时可指定 `--set global.hub=higress-registry.us-west-1.cr.aliyuncs.com` 切换。

### 12.7 部署方式对比

| 场景 | 推荐方式 |
| --- | --- |
| 个人/学习 | Docker All-in-One |
| 5 分钟体验 AI Gateway | AI Gateway install.sh |
| 生产云原生 | K8s Helm |
| 混合云/边缘 | Standalone + Nacos |
| 多集群管理 | Helm Subchart |

---

## 十三、成本模型：开源 + 阿里云企业版 + 飞天专享版

### 13.1 三档定价

| 档位 | 费用 | SLA | 支持 | 适用 |
| --- | --- | --- | --- | --- |
| **社区版** | **免费**（Apache-2.0） | 社区支持 | GitHub Issue / Discord | 验证、个人 |
| **企业版** | 阿里云 API Gateway 产品定价 | **99.95%** | 工单、钉钉 | 通用生产 |
| **飞天专享版** | 商务谈判 | **可谈判** | 工单、钉钉、线下 | 大型/合规 |

### 13.2 阿里云 API Gateway 定价（参考）

阿里云 API Gateway 公网实例按"调用次数 + 流量"计费：
- 0-1000 万次/月：约 0.3-0.5 元/万次 + 0.5-1 元/GB
- 千万级以上：阶梯优惠

> 注：具体价格请参考阿里云官网，本文不引用精确数字。

### 13.3 自托管 TCO 估算

**Higress 自托管总拥有成本**：

| 项 | 月度估算（中等规模） |
| --- | --- |
| K8s 集群（ACK 1 个托管 Master + 3 节点） | ~3000 元/月 |
| Higress Controller（低负载） | 共享集群资源 |
| Higress Gateway（按 QPS 伸缩） | 2-4 核 * 3 节点 = ~2000 元/月 |
| LLM Provider 费用 | 业务相关 |
| 存储（Nacos / Redis） | ~500 元/月 |
| **合计（不含 LLM）** | **~5500 元/月** |

对比 LiteLLM 自托管（单 VM）：

| 项 | 月度估算 |
| --- | --- |
| ECS 4 核 8GB * 2 | ~1500 元/月 |
| Redis | ~300 元/月 |
| **合计** | **~1800 元/月** |

Higress 成本是 LiteLLM 的 **3 倍**左右，但换来：
- K8s 原生部署 / 自动伸缩
- Envoy 高性能 / 长连接友好
- Wasm 多语言扩展
- 完整微服务治理

**小 B 商家场景**：Higress 不适合 5-15 万/年 的小 B 场景（过度设计、运维成本高），更适合 50 万+/年 的中大企业。

---

## 十四、生态集成：Plugin Hub 与 Wasm 多语言 SDK

### 14.1 官方 Plugin Hub

[higress.cn/en/plugin](https://higress.cn/en/plugin) 收录了 50+ 官方插件：

**AI 类**：
- ai-proxy / ai-cache / ai-statistics / ai-ratelimit
- mcp-server / mcp-router
- prompt-decorator / prompt-enhance
- content-security（敏感内容识别）

**安全类**：
- key-auth / hmac-auth / jwt-auth / basic-auth / oidc
- WAF（阿里云 WAF 集成）
- ip-restriction / referer-restriction / ua-restriction
- csrf

**流量管理类**：
- request-block / request-validation
- traffic-label / traffic-mirror
- redirect / rewrite（nginx 兼容，含 CVE-2026-42945 修复）
- cors / gzip

**可观测类**：
- prometheus / opentelemetry
- skywalking / zipkin
- SLS（日志服务）

**自定义扩展**：
- local-ratelimit / remote-ratelimit
- service-cluster
- transformer（请求/响应转换）

### 14.2 Wasm 多语言 SDK

- **wasm-go**（Go，**最成熟**）：github.com/higress-group/wasm-go
- **wasm-rust**（Rust）
- **wasm-js**（JavaScript / QuickJS）

### 14.3 与阿里云生态深度集成

| 集成 | 说明 |
| --- | --- |
| 阿里云 ACK | K8s 部署首选 |
| 阿里云 ALB / SLB | 负载均衡 |
| 阿里云 SLS | 日志服务 |
| 阿里云 ARMS | 应用监控 |
| 阿里云 WAF | Web 应用防火墙 |
| 阿里云 ACR | 镜像仓库 |
| 阿里云 SAE | Serverless 应用引擎 |
| 阿里云 MSE | 微服务引擎（Nacos 注册中心） |
| 通义百炼 | 阿里 LLM 平台 |
| 阿里云 PAI | 机器学习平台 |

### 14.4 与开源生态集成

| 集成 | 说明 |
| --- | --- |
| Dubbo / gRPC | L4/L7 代理 |
| Nacos | 服务发现 + 配置中心 |
| Sentinel | 流量防护（阿里系） |
| OpenTelemetry | 链路追踪 |
| Prometheus | 指标 |
| Kubernetes | 原生部署 |

---

## 十五、客户案例与典型用户：阿里云内 + 外部企业

### 15.1 阿里云内部

- **通义百炼 Model Studio**：阿里云 LLM 平台，Higress 作为 API 网关
- **阿里云 PAI 机器学习平台**：Higress 处理模型推理流量
- **阿里云 API Gateway 产品**：商业化产品基于 Higress
- **钉钉 AI 助手**：通义系列模型入口

### 15.2 sealos（外部标杆案例）

**sealos Cloud**（87,000+ 注册用户的 Kubernetes 公有云）：

- 2,000+ 租户，每个租户独立 Ingress
- 从 Nginx Ingress 迁移到 Higress
- 路由生效时间从 60s 降到 3s
- 资源消耗降低 60-80%
- 长连接保持（WebSocket / SSE / gRPC）
- 公开博客：[sealos.io/blog/sealos-envoy-vs-nginx-2000-tenants](https://sealos.io/blog/sealos-envoy-vs-nginx-2000-tenants/)

### 15.3 其他公开用户

来自社区博客与案例库：

- **小米**：内部 AI 网关
- **字节跳动**：部分业务使用 Envoy 系网关
- **蚂蚁集团**：内部 AI 业务
- **中国电信**：天翼云 API 网关
- **多家游戏公司**：AIGC 文生图/视频集成

> 注：具体客户名单部分来自社区博客未经官方确认，仅供参考。

### 15.4 客户场景画像

Higress 的典型客户是**中大型企业 + AI 业务**：

- 已有 K8s 集群
- 业务涵盖 LLM 调用 + 传统微服务
- 注重稳定性、性能、长期演进
- 不希望被某个云厂商深度绑定（社区版可自托管）

**不适合**：
- 个人开发者（可考虑 LiteLLM / One API）
- 纯 LLM 业务（可考虑 Portkey）
- 资源极有限的边缘场景（可考虑 Ollama / llama.cpp 直连）

---

## 十六、2026 年关键事件：Ingress Nginx 退役 + v2.2.2 重磅更新

### 16.1 Ingress Nginx 退役

**2025 年 11 月**，Kubernetes 社区宣布：**Ingress Nginx 将于 2026 年 3 月正式停止维护**。这一事件为 Higress、APISIX、Envoy Gateway 等替代方案打开了市场窗口。

Higress 立即跟进发布《告别 Ingress Nginx：云原生 API 网关 Gateway API 使用指引》博客，明确两条迁移路径：
1. 拥抱 **Gateway API**（Ingress 下一代）
2. 切换到 **仍在维护的 Ingress Controller**

Higress 同时支持两条路径：Ingress API + Gateway API 双向兼容。

### 16.2 CVE-2026-42945：18 年 Nginx 漏洞

**2026 年 5 月**，Higress 团队发现并公开 **CVE-2026-42945**：存在 18 年的 Nginx 堆溢出漏洞，CVSS 9.2，影响 Nginx 0.6.27 - 1.30.0。

漏洞原理：Nginx `rewrite` + `set` 指令编译为操作码，脚本引擎采用"两阶段执行"（长度计算 + 内容生成），中间存在状态管理疏忽，导致堆溢出。

Higress v2.2.2 引入 **nginx-rewrite 兼容 WASM 插件**，在 WASM 沙箱内**安全执行** Nginx rewrite 规则，**同时消除安全风险**。这是 Higress 对迁移用户的额外保护。

### 16.3 v2.2.2 重磅更新（2026-05-21）

70 项变更（主仓库 36 + Console 34），核心亮点：

**(A) Bedrock 直连**
- 重构 `/v1/messages` Bedrock 处理
- 移除 OpenAI→Converse 两层协议转换
- 直接对接 **Bedrock Mantle Anthropic Messages API**
- 降低延迟、提升兼容性、支持原生 Anthropic 特性

**(B) 自动恢复被限流的 API Key**
- 通过 health check 主动检测
- 与 `cooldownDuration` 配合自动恢复
- 不需要人工介入

**(C) Nginx rewrite 兼容插件**
- 见 16.2

**(D) CacheReadInputTokens 支持**
- OpenAI→Claude 流式响应中透传缓存命中 token
- 精确成本分析

**(E) KlingAI Provider**
- 视频生成（文生视频、图生视频）
- 支持 AK/SK JWT + 第三方 Bearer 两种认证

**(F) modelToHeader**
- 解析后 header 同步 `x-higress-llm-model-final`
- 限流/计量基于实际路由模型

**(G) QuotaConfig enable_path_suffixes**
- 自定义路径后缀匹配
- 细粒度配额控制

### 16.4 v2.1.x 关键能力（2025-2026 早期）

- MCP Server 托管（MCP 2024-11-05 SSE）
- 30+ AI Provider 支持
- 数据库类型 MCP Server
- ai-cache 全面支持向量语义
- ai-statistics 2.x 引入内置属性
- Claude Code 模式
- OpenAPI→MCP 自动转换

### 16.5 CNCF Sandbox 时间线

- 2024 年中：进入 CNCF Sandbox
- 2025 年：完成 OpenSSF Best Practices 评估
- 2026 年：Discord 社区、GitHub Discussions 活跃

---

## 十七、优劣势分析

### 17.1 优势

**1. AI Gateway + 通用 API 网关双形态**
- 5 合 1：MCP / AI / Ingress / Microservice / Security
- 一套基础设施覆盖 LLM + 微服务 + 边缘 + 安全
- 降低技术栈复杂度

**2. 最完整的 Provider 矩阵（30+）**
- 覆盖国际 + 国内主流厂商
- 中国系厂商覆盖最全（百度/阿里/腾讯/字节/智谱/月之暗面/百川/零一万物/阶跃/讯飞/可灵/豆包/混元）
- 几乎包含所有"国产化"需求

**3. Wasm 多语言扩展**
- Go / Rust / JS 三语言 SDK
- 沙箱隔离、安全
- **热更新不丢流量**（对 AI 长连接至关重要）
- 第三方可独立开发插件

**4. MCP 原生支持**
- 把 MCP Server 变成"网关原生能力"
- OpenAPI→MCP 零代码转换（**Higress 独创**）
- 支持 SSE + Streamable HTTP 两种协议

**5. 双层 AI 缓存（字符串 + 向量）**
- 7+ 向量数据库后端
- 7+ Embedding Provider
- GJSON 灵活提取键值
- 流式响应支持

**6. 性能优异**
- sealos 2000 租户场景下：路由 3s 生效，资源降低 60-80%
- 阿里内十万级 QPS
- 长连接友好

**7. 部署灵活**
- K8s / Standalone / Docker 5 种方式
- 不强制 K8s 依赖（vs Envoy Gateway）
- 镜像全球 3 区加速

**8. 协议自动兼容**
- OpenAI / Claude 双向自动检测与转换
- 零配置
- 减少应用层适配代码

**9. 商业化清晰**
- 阿里云三档（社区/企业/飞天）
- 99.95% SLA
- 中文生态支持好

**10. CNCF 治理**
- 中立、开源、不被单一云锁定
- OpenSSF Best Practices

### 17.2 劣势

**1. 学习曲线陡**
- Envoy + Istio + K8s 知识门槛
- 比 LiteLLM / Portkey 复杂得多
- 不适合个人开发者快速上手

**2. 运维成本高**
- 必须懂 K8s
- Wasm 插件调试工具链不成熟
- 性能调优需要深入 Envoy

**3. 文档国际化不均衡**
- 中文文档（higress.cn）丰富
- 英文文档（higress.ai）相对薄弱
- 部分关键页面 404
- 海外开发者体验不及 Portkey / LiteLLM

**4. 控制台功能有限**
- 比 Portkey 的 UI 简单
- 缺少成本预算面板
- 缺少用户管理（vs LiteLLM Virtual Keys）

**5. Virtual Key & RBAC 缺失**
- 不像 LiteLLM 那样有完善的 Virtual Key / Team / Organization / Spend Tracking
- AI 场景下多团队成本分摊需要自行开发

**6. 内置 Guardrails 弱**
- 仅 content-security 一个插件
- 不如 Portkey 的 30+ guardrails
- 需要自研或集成第三方

**7. 国际化进程慢**
- 阿里主导，海外社区参与度低
- Discord 130+ 用户，相比 Portkey 1000+ 少一个数量级
- 英文 Slack / Reddit 讨论度低

**8. 小 B 场景过度设计**
- 5-15 万/年 副业产品不需要 K8s + Envoy + Wasm
- 适合 50 万+/年 中大企业
- 不适合 indie / small business

**9. 部分功能仍待完善**
- MCP Streamable HTTP 早期阶段
- ai-ratelimit 配置项较少
- 缺少 LLM 评估 / Fine-tuning 集成

**10. 与某些云厂商深度绑定**
- 阿里云 WAF / SLS / ARMS / MSE 集成最优
- 在 AWS / Azure 上需要更多手动配置

---

## 十八、与其他 AI Gateway 对比

### 18.1 全维度对比表

| 维度 | **Higress** | **Portkey** | **LiteLLM** | **One API** | **APISIX ai-proxy** | **Envoy AI Gateway** |
| --- | --- | --- | --- | --- | --- | --- |
| **出身** | 阿里云（API 网关 + AI） | 独立创业（Pure AI） | BerriAI（YC W23） | 开源个人项目 | Apache（API 网关 + AI） | Tetrate / Envoy 社区 |
| **Stars** | 8.5K+ | 7K+ | 25K+ | 17K+ | 13K+ | 1.5K+ |
| **License** | Apache-2.0 | Apache-2.0 | MIT | MIT | Apache-2.0 | Apache-2.0 |
| **CNCF** | ✅ Sandbox | ❌ | ❌ | ❌ | ✅ Incubating | ❌ |
| **协议层** | OpenAI/Claude/MCP/A2A | OpenAI/Anthropic | OpenAI/Anthropic | OpenAI | OpenAI | OpenAI/Envoy ext proc |
| **Provider 数** | 30+ | 250+ | 100+ | 50+ | 20+ | 10+ |
| **缓存** | ✅ 字符串+向量 7+ | ✅ Simple+Semantic | ✅ 6 后端 | ⚠️ 简单 | ⚠️ Redis | ⚠️ 基础 |
| **Failover** | ✅ 健康检查+冷却 | ✅ | ✅ Cooldown | ✅ | ✅ | ✅ |
| **限流** | ✅ Token 限流 | ✅ Token 限流 | ✅ Spend Tracking | ✅ | ✅ QPS | ✅ |
| **Virtual Key** | ❌ 弱 | ✅ | ✅ 四层治理 | ✅ | ✅ | ⚠️ |
| **可观测** | ✅ 内置三件套 | ✅ Feedback | ✅ 35+ Callback | ✅ | ✅ | ✅ OTel |
| **Guardrails** | ⚠️ 1 个 | ✅ 30+ | ✅ 30+ | ❌ | ⚠️ 通用 | ⚠️ |
| **MCP 托管** | ✅ 首创 | ⚠️ 基础 | ✅ 通过 SDK | ❌ | ❌ | ❌ |
| **MCP 客户端** | ⚠️ 通过 Wasm | ❌ | ⚠️ SDK | ❌ | ❌ | ❌ |
| **Wasm 扩展** | ✅ Go/Rust/JS | ❌ | ❌ | ❌ | ❌ | ❌ |
| **数据面** | Envoy | 自研 Rust | Python/FastAPI | Go/Gin | Apache APISIX | Envoy |
| **性能** | 十万级 QPS | 万级 | 中等 | 中等 | 高 | 十万级 |
| **长连接友好** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ |
| **K8s 原生** | ✅ | ⚠️ | ⚠️ | ❌ | ✅ | ✅ |
| **控制台** | ✅ | ✅ 完善 | ✅ Web UI | ✅ Web UI | ✅ Dashboard | ❌ 无 |
| **中文生态** | ✅ 最强 | ⚠️ 一般 | ⚠️ 一般 | ✅ 强 | ✅ 强 | ❌ |
| **多语言 SDK** | ✅ Go/Rust/JS | ❌ | ✅ Python/JS/Go | ❌ | ❌ | ❌ |
| **商业化** | 阿里云三档 | Portkey Cloud | Hosted + Enterprise | 无 | API7 Cloud | Tetrate |
| **学习曲线** | 陡 | 中 | 中 | 平缓 | 陡 | 陡 |
| **定位** | 大企业 / 混合流量 | 中大 / Pure AI | 中大 / Pure AI | 个人 / 小团队 | 大企业 / K8s | 大企业 / Service Mesh |

### 18.2 关键差异化

**Higress 独到之处**：

1. **Wasm 多语言扩展**：是所有 AI Gateway 中**唯一**支持 Wasm 多语言热更新的。
2. **MCP Server 托管**：是少数原生支持 MCP 的（vs Portkey 仅做客户端）。
3. **OpenAPI→MCP**：是**唯一**提供 OpenAPI 到 MCP 自动转换的。
4. **混合流量**：是少数能同时处理 LLM + 传统微服务的（vs LiteLLM 仅 LLM）。
5. **中国系 Provider 覆盖最全**：30+ Provider 矩阵里中国系占 50%。
6. **Standalone 模式**：是少数支持 K8s-less 部署的（vs Envoy Gateway 必须 K8s）。

**Portkey 独到之处**：

- 250+ Provider 最多
- Palo Alto 收购（2026），企业安全集成
- 控制台体验最佳
- Guardrails 最多（30+）

**LiteLLM 独到之处**：

- Python SDK 生态最好（LangChain 集成最深）
- Virtual Key / Team / Org / Spend 四层治理
- 文档最详尽
- 25K+ Stars 最大社区

**One API 独到之处**：

- 单二进制、部署最简单
- 中文社区最活跃
- 适合个人/小团队

### 18.3 选型决策树

```
Q1: 业务流量包含 LLM 之外的传统微服务吗？
├── 是 → Higress / APISIX（混合流量）
└── 否 → 继续
    │
    Q2: 已经在用 K8s 吗？
    ├── 是 → Higress / APISIX / Envoy AI Gateway
    └── 否 → 继续
        │
        Q3: 需要 Wasm 多语言扩展吗？
        ├── 是 → Higress（唯一选择）
        └── 否 → 继续
            │
            Q4: 需要 MCP Server 托管吗？
            ├── 是 → Higress（最佳）
            └── 否 → 继续
                │
                Q5: 中国系 Provider 多吗？
                ├── 是 → Higress / One API
                └── 否 → 继续
                    │
                    Q6: 需要 Guardrails 吗？
                    ├── 是 → Portkey / LiteLLM
                    └── 否 → LiteLLM（最成熟）
```

### 18.4 与 Envoy AI Gateway 对比（同源）

Higress 与 Envoy AI Gateway 都基于 Envoy，但有本质差异：

| 维度 | Higress | Envoy AI Gateway |
| --- | --- | --- |
| 维护方 | higress-group（阿里） | Tetrate / Envoy 社区 |
| Wasm 支持 | ✅ 完善 | ❌ |
| 部署方式 | K8s / Standalone | K8s 强制 |
| 控制台 | ✅ | ❌ |
| Provider 矩阵 | 30+ | 10+ |
| 性能优化 | 阿里内部优化 | 社区优化 |
| 商业化 | 阿里云 | Tetrate |

**结论**：Higress 在"开箱即用"上完胜，Envoy AI Gateway 更"原生"但配置繁琐。

### 18.5 与 APISIX ai-proxy 对比（同源）

Higress 与 APISIX 都基于 Envoy/Apache 项目：

| 维度 | Higress | APISIX |
| --- | --- | --- |
| 数据面 | Envoy | APISIX（基于 Nginx + Lua） |
| Wasm | ✅ | ❌ |
| 控制台 | ✅ | ✅ |
| Standalone | ✅ | ✅ |
| Provider 矩阵 | 30+ | 20+ |
| MCP 托管 | ✅ 首创 | ❌ |

**结论**：Higress 在 Wasm 扩展 + AI Provider 覆盖上更强，APISIX 在 Lua 生态 + 多协议（MQTT/Kafka）上更强。

---

## 十九、最佳实践与反模式

### 19.1 最佳实践

**(A) MCP Server 托管配置**

```yaml
# ✅ 推荐：MCP 配置 + Redis 粘性
mcpServer:
  sse_path_suffix: /sse
  enable: true
  redis:
    address: redis-stack-server.higress-system.svc.cluster.local:6379
  match_list:
    - match_rule_domain: "*"
      match_rule_path: /postgres
      match_rule_type: "prefix"
```

注意：
1. 必须启用 Redis（`helm install --set global.enableRedis=true`）
2. 数据库 MCP 在 ConfigMap，REST API MCP 在 Console
3. SSE 路径后缀必须配置

**(B) API Key 池化 + Failover**

```yaml
# ✅ 推荐：多 Token 池 + 健康检查 + 冷却
provider:
  apiTokens:
    - sk-key-1
    - sk-key-2
    - sk-key-3
  failover:
    enabled: true
    failureThreshold: 3
    healthCheckModel: "gpt-3.5-turbo"  # 轻量模型
    cooldownDuration: 30000
```

**(C) 双层缓存配置**

```yaml
# ✅ 推荐：字符串 + 向量双层
cache:
  type: redis
  serviceName: redis.static
  cacheTTL: 3600
vector:
  type: dashvector
  topK: 1
  threshold: 0.95
  thresholdRelation: "gt"
embedding:
  type: dashscope
  model: "text-embedding-v3"
```

**(D) 协议自动兼容**

```yaml
# ✅ 推荐：零配置协议转换（不要手动设 protocol）
provider:
  type: openai
  # 不需要 protocol: openai  ← 由路径后缀自动检测
```

**(E) 模型映射**

```yaml
# ✅ 推荐：正则 + 兜底
modelMapping:
  "~gpt(.*)": "openai/gpt$1"
  "~claude-(.*)": "claude/$1"
  "*": "qwen-max"
```

**(F) 可观测性内置属性**

```yaml
# ✅ 推荐：用内置属性而非自定义 value_source
attributes:
  - key: question      # 内置：自动提取
    apply_to_log: true
  - key: answer        # 内置：自动提取
    apply_to_log: true
  - key: reasoning     # 内置：自动提取（DeepSeek-R1 等）
    apply_to_log: true
  - key: tool_calls    # 内置：自动拼接
    apply_to_log: true
```

**(G) 镜像选择**

```bash
# ✅ 推荐：使用区域镜像
# 北美
helm install higress higress.io/higress --set global.hub=higress-registry.us-west-1.cr.aliyuncs.com
# 东南亚
helm install higress higress.io/higress --set global.hub=higress-registry.ap-southeast-7.cr.aliyuncs.com
```

### 19.2 反模式

**(A) ❌ 流式请求上启用 retryOnFailure**

```yaml
# ❌ 反模式：流式不支持重试
retryOnFailure:
  enabled: true
  maxRetries: 3
```

流式请求一旦开始就不可重试，重试逻辑仅对非流式有效。

**(B) ❌ 缓存键用整 messages**

```yaml
# ❌ 反模式：缓存键过长
cacheKeyFrom: "messages"
```

应该用 `messages.@reverse.0.content`（最后一条用户消息）。

**(C) ❌ 阈值设置不合理**

```yaml
# ❌ 反模式：阈值过小导致缓存命中率低
vector:
  threshold: 0.99
  thresholdRelation: "gt"
```

Cosine 相似度一般 0.85-0.95 是合理区间。

**(D) ❌ Nginx rewrite 迁移时启用 raw 模式**

```yaml
# ❌ 反模式：raw 模式无安全检查
customSettings:
  - name: x
    value: y
    mode: raw  # 不做改写
```

raw 模式会绕过参数改写，可能导致上游协议不兼容。

**(E) ❌ Standalone 模式 + K8s 配置混用**

不要把 K8s CRD 配置复制到 Standalone 模式——配置后端不同，会导致解析失败。

**(F) ❌ 忽略 fail-open/fail-close 配置**

`ai-proxy` 默认是 fail-close：API Key 不可用时直接返回错误。需要根据业务场景决定是否允许 fail-open（降级到默认 provider）。

### 19.3 性能调优清单

| 调优点 | 建议 |
| --- | --- |
| Wasm 插件数量 | < 5 个，超过需评估性能影响 |
| 健康检查频率 | 不要 < 1s，建议 5s+ |
| 缓存 TTL | 根据业务更新频率，AI 一般 1h-24h |
| 限流粒度 | 用 `enable_path_suffixes` 细粒度控制 |
| 日志缓冲 | 启用 `as_separate_log_field` 减少重复解析 |
| 流式响应 | 不要在 ai-statistics 启用 `use_default_attributes`（缓冲流式体影响性能） |
| Embedding 模型 | 用轻量模型（text-embedding-3-small / v3-small） |

### 19.4 迁移检查清单

从 LiteLLM / Portkey 迁移到 Higress：

- [ ] Provider 类型映射（openai → openai, anthropic → claude, ...）
- [ ] API Key 拆分（按 Provider 分组）
- [ ] 路由规则翻译（LiteLLM model_list → Higress ai-route CRD）
- [ ] 缓存配置（Redis 后端地址 + 阈值）
- [ ] 限流配置（QPS / Token 双重）
- [ ] 认证迁移（key-auth / jwt-auth）
- [ ] 可观测性（指标 + 日志格式）
- [ ] K8s CRD 化（Helm chart 升级）
- [ ] 镜像仓库切换（如果不在阿里云）
- [ ] WAF / 安全插件启用

---

## 二十、参考资料与索引

### 20.1 官方资源

- **主仓库**：https://github.com/higress-group/higress
- **官方文档**：https://higress.cn/en/docs/latest/
- **英文官网**：https://higress.ai/en/
- **中文官网**：https://higress.cn/
- **Plugin Hub**：https://higress.cn/en/plugin/
- **博客**：https://higress.cn/en/blog/
- **MCP 体验**：https://mcp.higress.ai/
- **控制台 Demo**：http://demo.higress.io/
- **Discord**：https://discord.gg/tSbww9VDaM
- **CNCF 页面**：https://www.cncf.io/projects/

### 20.2 关联仓库

- higress-console：https://github.com/higress-group/higress-console
- higress-standalone：https://github.com/higress-group/higress-standalone
- plugin-server：https://github.com/higress-group/plugin-server
- wasm-go SDK：https://github.com/higress-group/wasm-go
- openapi-to-mcpserver：https://github.com/higress-group/openapi-to-mcpserver

### 20.3 关键版本

- **v2.2.2**（2026-05-21）：70 项变更，Bedrock 直连、Nginx rewrite 安全迁移
- **v2.1.x**（2025-2026 早期）：MCP Server 托管、30+ Provider、Claude Code 模式
- **v1.x**（2024 之前）：基础 API Gateway + AI Gateway

### 20.4 关键博客文章

- [Scaling to 2,000 Tenants: Why Sealos Moved from Nginx to Envoy](https://sealos.io/blog/sealos-envoy-vs-nginx-2000-tenants/) — 性能基准关键参考
- [告别 Ingress Nginx：云原生 API 网关 Gateway API 使用指引](https://higress.cn/en/blog/) — 2026 迁移方案
- [从一个隐藏 18 年的 Nginx 漏洞，看网关安全架构的演进](https://higress.cn/en/blog/) — CVE-2026-42945 解读
- [HiClaw 上线 Worker 模板市场](https://higress.cn/en/blog/) — Agent 平台演进
- [阿里云 AI 网关支持 DeepSeek V4](https://higress.cn/en/blog/) — Provider 跟进速度

### 20.5 与本系列其他报告的关联

- `01-llm-protocols.md`：Higress 支持 OpenAI / Claude / MCP / A2A 协议的细节
- `02-semantic-cache.md`：ai-cache 插件的语义缓存设计（与本报告第八章对应）
- `03-intelligent-routing.md`：Higress 的多 Provider 路由策略
- `04-observability-openllmetry.md`：ai-statistics 插件的指标体系
- `06-guardrails.md`：Higress 的 Guardrails 现状（弱项）
- `07-edge-ai-gateway.md`：Higress Standalone 模式 + 边缘部署
- `08-inference-engine-coordination.md`：Higress 协调 vLLM / Ollama / Triton 的能力
- `10-open-source-ecosystem.md`：Higress 在 AI Gateway 开源生态中的位置
- `11-mcp-deep-dive.md`：Higress 首创的 MCP Server 托管 + OpenAPI 转换
- `14-performance-benchmark.md`：sealos 2000 租户实测数据
- `15-open-source-contribution.md`：Higress 社区贡献模式
- `16-public-cloud-integration.md`：阿里云生态深度集成
- `19-sla-service-governance.md`：Higress 99.95% SLA 的实现

### 20.6 关键参考 API

```yaml
# 1. ai-proxy 最小配置
apiVersion: networking.higress.io/v1
kind: AIProxy
metadata:
  name: my-ai-route
spec:
  provider:
    type: openai
    apiTokens: ["sk-xxx"]
```

```yaml
# 2. ai-cache 最小配置
apiVersion: networking.higress.io/v1
kind: AICache
metadata:
  name: my-cache
spec:
  cache:
    type: redis
    serviceName: redis.static
  vector:
    type: dashvector
    serviceName: dashvector.static
```

```yaml
# 3. ai-statistics 最小配置
apiVersion: networking.higress.io/v1
kind: AIStatistics
metadata:
  name: my-stats
spec:
  attributes:
    - key: question
      apply_to_log: true
    - key: answer
      apply_to_log: true
```

```yaml
# 4. MCP Server 数据库类型
apiVersion: v1
kind: ConfigMap
metadata:
  name: higress-config
  namespace: higress-system
data:
  higress: |-
    mcpServer:
      sse_path_suffix: /sse
      enable: true
      redis:
        address: redis-stack-server.higress-system.svc.cluster.local:6379
      match_list:
        - match_rule_domain: "*"
          match_rule_path: /postgres
          match_rule_type: "prefix"
      servers:
        - name: postgres
          path: /postgres
          type: database
          config:
            dsn: "postgresql://user:pass@host:5432/db"
            dbType: "postgres"
```

### 20.7 调研元数据

- **调研日期**：2026-06-05
- **抓取时点**：2026-06-04 20:04-20:07 UTC
- **数据源快照**：
  - GitHub API repo metadata: stars 8,559 / forks 1,143 / issues 785 / Apache-2.0
  - Release: v2.2.2 (2026-05-21) 70 项变更
  - Provider 矩阵: 30+ provider（基于 plugins/wasm-go/extensions/ai-proxy/provider/ 目录实际枚举）
  - 向量数据库后端: 7 个（dashvector/chroma/elasticsearch/weaviate/pinecone/qdrant/milvus）
  - Embedding Provider: 7 个（dashscope/openai/azure/cohere/ollama/huggingface/textin/xfyun）
  - 性能基准: sealos 2000 租户，3s 路由生效，资源降 60-80%

---

> **结语**：Higress 是当前**唯一**同时提供完整 AI Gateway 能力 + MCP Server 托管 + 通用 API 网关 + Wasm 多语言扩展的开源项目。30+ Provider 矩阵 + 7+ 向量数据库 + 7+ Embedding 后端 + 中国系厂商全覆盖，使其在中文 AI 工程化领域占据独特位置。**特别适合**：中大型企业、混合流量场景、需要 MCP 托管、希望避免云厂商绑定的团队。**不太适合**：个人/小团队（学习曲线过陡）、纯 LLM 业务（LiteLLM/Portkey 更轻量）、5-15 万/年小 B 副业（过度设计）。

