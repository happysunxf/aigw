# AI 网关与公有云深度集成

> 系列：AI Gateway 持续深挖 · 第 2 批 · 第 6 篇
> 性质：纯技术研究
> 范围：AWS、Azure、GCP、阿里云、腾讯云、华为云等公有云厂商的 AI 网关与 AI 基础设施集成

---

## 目录

- [一、公有云为何要做 AI Gateway](#一公有云为何要做-ai-gateway)
- [二、AWS AI 网关与 AI 基础设施](#二aws-ai-网关与-ai-基础设施)
- [三、Microsoft Azure AI 网关与生态](#三microsoft-azure-ai-网关与生态)
- [四、Google Cloud AI 网关与 Vertex AI](#四google-cloud-ai-网关与-vertex-ai)
- [五、阿里云 AI 网关与通义生态](#五阿里云-ai-网关与通义生态)
- [六、腾讯云、华为云、字节云等](#六腾讯云华为云字节云等)
- [七、跨云 AI 网关](#七跨云-ai-网关)
- [八、企业混合云 AI 网关架构](#八企业混合云-ai-网关架构)
- [九、云原生 AI 网关](#九云原生-ai-网关)
- [十、未解难题与研究前沿](#十未解难题与研究前沿)
- [十一、参考资料](#十一参考资料)

---

## 一、公有云为何要做 AI Gateway

### 1.1 云厂商的动机

| 动机 | 描述 |
|---|---|
| **绑定客户** | 客户用了 AI Gateway 难以迁移 |
| **生态系统** | 围绕云构建 AI 生态 |
| **收入来源** | 模型调用抽成、托管服务费 |
| **差异化** | 与其他云厂商竞争 |
| **数据控制** | 收集使用数据优化产品 |

### 1.2 云厂商 AI Gateway 的优势

| 优势 | 描述 |
|---|---|
| **深度集成** | 与其他云服务（IAM、VPC、监控）天然集成 |
| **一站式** | 不用自己拼装 |
| **SLA 保障** | 云厂商兜底 |
| **按用量付费** | 不用预测容量 |
| **安全合规** | 继承云厂商认证 |

### 1.3 云厂商 AI Gateway 的劣势

| 劣势 | 描述 |
|---|---|
| **厂商锁定** | 难迁移 |
| **价格不透明** | 隐性成本 |
| **功能受限** | 只能用云厂商提供的模型 |
| **创新滞后** | 比独立产品慢 |
| **数据出境** | 受云厂商所在地区限制 |

### 1.4 主流公有云 AI 布局

| 云厂商 | AI Gateway | 模型 | 推理 | 训练 |
|---|---|---|---|---|
| **AWS** | API Gateway + Bedrock | Claude / Llama / Mistral / Cohere | Bedrock / SageMaker | SageMaker |
| **Azure** | APIM + AI Gateway | GPT / Claude / Llama / Mistral | Azure OpenAI / AI Foundry | Azure ML |
| **Google Cloud** | Apigee + Vertex AI | Gemini / Claude / Llama | Vertex AI | Vertex AI |
| **阿里云** | Higress + AI 网关 | 通义 / Llama / Qwen | PAI / 函数计算 | PAI |
| **腾讯云** | API Gateway + 混元 | 混元 / Llama | TI 平台 | TI 平台 |
| **华为云** | APIG + 盘古 | 盘古 / Llama | ModelArts | ModelArts |
| **字节云** | 火山引擎 API | 豆包 / Skywork | 火山方舟 | 火山方舟 |

---

## 二、AWS AI 网关与 AI 基础设施

### 2.1 整体架构

```
                    ┌─────────────────────────────┐
                    │  AWS API Gateway            │
                    │  - 限流 / 鉴权 / 监控       │
                    └────────────┬────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ↓                    ↓                    ↓
    ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
    │  Bedrock      │    │  SageMaker    │    │  Marketplace  │
    │  (托管模型)   │    │  (自托管)     │    │  (第三方模型) │
    └───────┬───────┘    └───────┬───────┘    └───────┬───────┘
            ↓                    ↓                    ↓
    Claude / Llama       自训练模型            各种合作伙伴
    Mistral / Cohere
```

### 2.2 Amazon Bedrock

**核心能力**：

| 能力 | 描述 |
|---|---|
| **托管模型市场** | Claude、Llama、Mistral、Cohere、AI21、Stability 等 |
| **多模型 API** | 统一 API 调用所有模型 |
| **Knowledge Base** | RAG 服务（与 OpenSearch 集成） |
| **Agents** | Bedrock Agent 服务（多步调用） |
| **Guardrails** | 内置 Guardrails（内容安全） |
| **Fine-tuning** | 部分模型支持微调 |
| **Provisioned Throughput** | 预留吞吐 |
| **Batch Inference** | 批量推理 |

**API 示例**：

```python
import boto3

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

response = bedrock.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    })
)
```

**流式响应**：

```python
response = bedrock.invoke_model_with_response_stream(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({...})
)

for event in response['body']:
    chunk = json.loads(event['chunk']['bytes'])
    if chunk['type'] == 'content_block_delta':
        print(chunk['delta']['text'], end='')
```

### 2.3 Bedrock 与传统 API Gateway 的集成

```python
# API Gateway → Lambda → Bedrock
# 1. 创建 REST API
# 2. 配置 Lambda 集成
# 3. Lambda 调用 Bedrock

import boto3
import json

def lambda_handler(event, context):
    bedrock = boto3.client('bedrock-runtime')
    
    body = json.loads(event['body'])
    response = bedrock.invoke_model(
        modelId=body.get('model', 'anthropic.claude-3-5-sonnet'),
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": body.get('max_tokens', 1000),
            "messages": body['messages']
        })
    )
    
    return {
        'statusCode': 200,
        'body': response['body'].read()
    }
```

### 2.4 Bedrock Agents

```python
agent = bedrock_agent_runtime_client.create_agent(
    agentName="MyAgent",
    foundationModel="anthropic.claude-3-5-sonnet-20241022-v2:0",
    instruction="You are a helpful assistant",
    agentResourceRoleArn=role_arn,
    actionGroups=[
        {
            "actionGroupName": "DatabaseAccess",
            "description": "Access database",
            "actionGroupExecutor": {"lambda": lambda_arn},
            "apiSchema": {"payload": openapi_schema}
        }
    ]
)
```

**关键能力**：
- 自动规划
- 多步执行
- 工具调用
- Knowledge Base 集成

### 2.5 Bedrock Guardrails

```python
guardrail = bedrock.create_guardrail(
    name="MyGuardrail",
    description="Content safety guardrail",
    contentPolicyConfig={
        "filtersConfig": [
            {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "PROMPT_ATTACK", "inputStrength": "HIGH"}  # Bedrock 独有
        ]
    },
    topicPolicyConfig={
        "topicsConfig": [
            {"name": "Forbidden", "definition": "Discussion of illegal activities", "type": "DENY"}
        ]
    },
    wordPolicyConfig={
        "wordsConfig": [
            {"text": "badword"}
        ]
    },
    sensitiveInformationPolicyConfig={
        "piiEntitiesConfig": [
            {"type": "EMAIL", "action": "ANONYMIZE"},
            {"type": "PHONE", "action": "ANONYMIZE"},
            {"type": "CREDIT_CARD", "action": "BLOCK"}
        ]
    }
)
```

**重要**：`PROMPT_ATTACK` 是 Bedrock 独有的注入检测能力。

### 2.6 SageMaker 推理

```python
# 部署模型到 SageMaker Endpoint
predictor = huggingface_model.deploy(
    initial_instance_count=1,
    instance_type="ml.g5.2xlarge"
)

# 调用
response = predictor.predict({
    "inputs": "Hello, how are you?"
})
```

**SageMaker 特点**：
- 支持自训练 / 自定义模型
- 支持多框架（PyTorch、TensorFlow、HuggingFace）
- Auto Scaling
- Multi-Model Endpoints
- 多 GPU / 多机

### 2.7 AWS Lambda@Edge

```
Lambda@Edge + AI Gateway
├── 边缘节点预处理
├── 缓存
└── Guardrails 前置
```

**限制**：
- 无 GPU
- 不能跑 LLM
- 适合轻量任务

---

## 三、Microsoft Azure AI 网关与生态

### 3.1 整体架构

```
                ┌─────────────────────────────┐
                │  Azure API Management       │
                │  - 策略 / 限流 / 监控        │
                │  - AI 专用策略               │
                └────────────┬────────────────┘
                             │
            ┌────────────────┼────────────────┐
            ↓                ↓                ↓
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
    │  Azure OpenAI │  │  AI Foundry   │  │  Azure ML     │
    └───────────────┘  └───────────────┘  └───────────────┘
```

### 3.2 Azure OpenAI Service

**与 OpenAI 直接 API 的差异**：

| 维度 | OpenAI 直接 | Azure OpenAI |
|---|---|---|
| **认证** | API Key | Azure AD / API Key |
| **数据驻留** | 美国 | 可选区域 |
| **合规** | OpenAI | Azure 合规（FedRAMP、HIPAA 等） |
| **VPC** | 公开 | 私有 endpoint |
| **SLA** | 99.9% | 99.9% |
| **功能** | 最新最快 | 略晚于 OpenAI |

**API 调用**：

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key="...",
    api_version="2024-10-21",
    azure_endpoint="https://my-resource.openai.azure.com"
)

response = client.chat.completions.create(
    model="my-gpt-4-deployment",  # 部署名，不是模型名
    messages=[{"role": "user", "content": "Hello"}]
)
```

**注意**：`model` 参数是**部署名**（Azure 概念）而不是模型名。

### 3.3 Azure API Management + AI

**AI 专用策略**：

```xml
<!-- API Management 策略 -->
<policies>
    <inbound>
        <base />
        <!-- AI Token 限制 -->
        <azure-openai-token-limit 
            tokens-per-minute="10000" 
            counter-key="@(context.Request.IpAddress)" />
        <!-- 内容安全 -->
        <azure-openai-content-safety 
            content-safety-resource="my-content-safety" />
        <!-- 模拟响应（用于开发） -->
        <mock-response status-code="200" content-type="application/json" />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
</policies>
```

**能力**：
- Token 速率限制
- 内容安全检查
- 模拟响应（开发环境）
- 语义缓存（实验性）
- 用量监控

### 3.4 Azure AI Foundry

**前身**：Azure AI Studio

**特点**：
- 一站式 AI 应用开发
- 模型市场（包括 OpenAI、Anthropic、Mistral、Meta、HuggingFace）
- Prompt Flow（编排）
- 评估能力
- 部署能力

**Prompt Flow**：

```python
# 用 Python 定义 flow
from promptflow import tool, Input, Output
from promptflow.connections import AzureOpenAIConnection

@tool
def generate_text(prompt: str, conn: AzureOpenAIConnection) -> str:
    from openai import AzureOpenAI
    client = AzureOpenAI(
        api_key=conn.api_key,
        api_version="2024-10-21",
        azure_endpoint=conn.api_base
    )
    response = client.chat.completions.create(
        deployment_name="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

**优势**：
- 可视化编排
- 内置评估
- 部署到多个目标

### 3.5 Azure Content Safety

**独立服务**：

```python
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory

client = ContentSafetyClient(endpoint, credential)

request = AnalyzeTextOptions(
    text="...",
    categories=[TextCategory.HATE, TextCategory.SELF_HARM, TextCategory.SEXUAL, TextCategory.VIOLENCE]
)

response = client.analyze_text(request)

for item in response.categories_analysis:
    print(f"{item.category}: severity={item.severity}")
```

**特点**：
- 多类别检测
- 多模态支持（图像）
- 自定义类别
- 多语言

### 3.6 Azure AI Search

**RAG 专用**：

```python
from azure.search.documents import SearchClient

search_client = SearchClient(endpoint, index_name, credential)

results = search_client.search(
    search_text="...",
    vector_queries=[{
        "kind": "vector",
        "vector": embedding_vector,
        "k": 5
    }],
    top=5
)
```

**特点**：
- 混合搜索（关键词 + 向量）
- 内置 embedding 集成
- 索引管理
- 与 OpenAI 集成

### 3.7 Azure ML 推理

```
Azure ML Endpoints
├── Managed Endpoints（托管）
├── Kubernetes Online Endpoints（K8s）
└── Batch Endpoints（批量）
```

**优势**：
- 多模型支持
- Auto Scaling
- 蓝绿部署
- 与 Azure 监控集成

---

## 四、Google Cloud AI 网关与 Vertex AI

### 4.1 整体架构

```
                ┌─────────────────────────────┐
                │  Apigee / Cloud Gateway      │
                │  - API 管理                  │
                └────────────┬────────────────┘
                             │
            ┌────────────────┼────────────────┐
            ↓                ↓                ↓
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
    │  Vertex AI    │  │  Gemini API   │  │  GKE + vLLM   │
    │  (托管模型)   │  │  (直接调用)   │  │  (自托管)     │
    └───────────────┘  └───────────────┘  └───────────────┘
```

### 4.2 Vertex AI

**核心能力**：

| 能力 | 描述 |
|---|---|
| **Model Garden** | 模型市场（Gemini、Claude、Llama、Mistral 等） |
| **Model-as-a-Service** | 托管的第三方模型 |
| **Tuning** | 监督微调、RLHF、LoRA |
| **Vector Search** | 托管向量数据库 |
| **Agent Builder** | Agent 平台（基于 LangChain） |
| **RAG Engine** | 托管 RAG 流程 |
| **Pipelines** | ML 流水线 |

### 4.3 Gemini API

**多模态原生**：

```python
import google.generativeai as genai

model = genai.GenerativeModel('gemini-2.0-pro')

# 文本 + 图像
response = model.generate_content([
    "What's in this image?",
    PIL.Image.open('image.png')
])

print(response.text)
```

**流式**：

```python
response = model.generate_content(
    "Tell me a story",
    stream=True
)
for chunk in response:
    print(chunk.text, end='')
```

### 4.4 Vertex AI Agent Builder

**基于 LangChain**：

```python
from vertexai.preview import agent_builder

agent = agent_builder.Agent.create(
    display_name="My Agent",
    model="gemini-2.0-pro",
    instruction="You are a helpful assistant",
    tools=[
        # 内置工具
        # - Code Interpreter
        # - Vertex AI Search
        # - 第三方 API
    ]
)
```

**特点**：
- 可视化构建
- 内置工具
- 多模态
- 与 GCP 服务集成

### 4.5 Vertex AI Search

**企业级 RAG**：

```
- 文档上传（PDF、HTML、Word）
- 自动解析 + 分块
- 自动 embedding
- 混合检索
- 与 Gemini 集成
```

### 4.6 Apigee + AI Gateway

**Apigee 高级 API 管理**：

```
Apigee
├── 流量管理
├── 安全（OAuth、JWT）
├── 配额 / 速率限制
├── 分析
├── 货币化
└── AI Gateway 策略
```

**AI Gateway 策略**：

- Token 限流
- 模型路由
- Prompt 模板
- 响应转换
- 语义缓存（实验性）

### 4.7 GKE + 自托管模型

```
GKE
├── vLLM / TGI / SGLang Pod
├── K8s 自动伸缩
├── GPU 节点池
├── 网络策略
└── 监控
```

**与 Vertex AI 协同**：
- Vertex AI 用于生产
- GKE 自托管用于敏感场景
- AI Gateway 统一路由

### 4.8 Gemini 多模态

**原生多模态**（与 GPT-4o 一样）：

```python
# 视频理解
video_file = genai.upload_file("video.mp4")
response = model.generate_content([
    "What happens in this video?",
    video_file
])

# 实时音频（Gemini Live）
# 图像生成（Imagen）
# 视频生成（Veo）
```

---

## 五、阿里云 AI 网关与通义生态

### 5.1 整体架构

```
                ┌─────────────────────────────┐
                │  Higress / ESA              │
                │  - API 网关 + AI 插件        │
                └────────────┬────────────────┘
                             │
            ┌────────────────┼────────────────┐
            ↓                ↓                ↓
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
    │  百炼         │  │  PAI          │  │  函数计算 FC   │
    │  (通义全家桶) │  │  (自训练)     │  │  (轻量推理)   │
    └───────────────┘  └───────────────┘  └───────────────┘
```

### 5.2 阿里云百炼

**核心能力**：

| 能力 | 描述 |
|---|---|
| **模型市场** | 通义、Llama、ChatGLM、DeepSeek、Yi 等 |
| **应用模板** | 多种预置应用（客服、写作、代码） |
| **知识库** | RAG 一体化 |
| **智能体** | Agent 平台 |
| **API 调用** | OpenAI 兼容 API |
| **微调** | 部分模型支持 |
| **流量包** | 套餐 + 按量 |

### 5.3 通义模型家族

| 模型 | 类型 | 能力 |
|---|---|---|
| **Qwen-Max** | 旗舰 | 最强 |
| **Qwen-Plus** | 中等 | 性价比 |
| **Qwen-Turbo** | 快速 | 低延迟 |
| **Qwen-Long** | 长上下文 | 1M+ tokens |
| **Qwen-VL** | 多模态 | 图像/视频 |
| **Qwen-Code** | 代码 | 代码生成 |
| **Qwen-Math** | 数学 | 数学推理 |

**API 调用**：

```python
import dashscope

response = dashscope.Generation.call(
    model="qwen-max",
    messages=[{"role": "user", "content": "Hello"}],
    result_format="message"
)
print(response.output.choices[0].message.content)
```

**OpenAI 兼容**：

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-...",  # DashScope key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen-max",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### 5.4 Higress（云原生 AI 网关）

**详见报告 #7**。核心：
- 基于 Envoy + Istio
- Wasm 插件
- AI 专用插件（路由、限流、统计、模板）
- 阿里云商业版

**阿里云商业版增强**：
- 通义/百炼深度集成
- 阿里云监控集成
- 商业 SLA
- 安全合规

### 5.5 阿里云 PAI（机器学习平台）

```
PAI
├── PAI-DSW（交互式开发）
├── PAI-DLC（分布式训练）
├── PAI-EAS（在线推理服务）
├── PAI-Blade（推理优化）
└── PAI-Designer（可视化）
```

**PAI-EAS 推理**：

```python
# 部署 vLLM 到 EAS
eas_config = {
    "model_path": "/mnt/models/qwen-72b",
    "framework": "vllm",
    "instance_type": "ecs.gn7e-c16g1.4xlarge",  # 4x A100
    "instance_count": 2
}
```

**特点**：
- 一键部署开源模型
- Auto Scaling
- 蓝绿部署
- A/B 测试

### 5.6 阿里云 ESA（边缘安全加速）

**Cloudflare 类比**：
- 边缘节点
- Worker 函数
- AI 推理（实验性）

### 5.7 阿里云函数计算 FC

**Serverless LLM**：
- 按请求计费
- 自动伸缩
- 适合低频 AI 应用

---

## 六、腾讯云、华为云、字节云等

### 6.1 腾讯云

#### 模型

- **混元**（hunyuan）—— 自研
- 第三方模型

#### 平台

- **TI 平台**（机器学习）
- **大模型知识引擎**（RAG）
- **大模型应用引擎**（Agent）

#### API Gateway

- 传统 API Gateway
- AI 插件

#### 特色

- 微信生态（公众号、小程序）集成
- 音视频场景

### 6.2 华为云

#### 模型

- **盘古**（Pangu）—— 自研
- 第三方模型

#### 平台

- **ModelArts**（机器学习）
- **盘古大模型**（PanguLM）
- **昇思**（MindSpore）

#### API Gateway

- APIG
- AI 插件

#### 特色

- 昇腾芯片（自研 NPU）
- 信创生态
- 政企客户

### 6.3 字节火山引擎

#### 模型

- **豆包**（Doubao）—— 自研
- **Skywork**（天工）
- 第三方模型

#### 平台

- **火山方舟**（LLM 平台）
- **机器学习平台**

#### 特色

- 字节内部应用（抖音、TikTok）
- 价格激进
- 字节系生态（飞书、巨量引擎）

### 6.4 百度智能云

#### 模型

- **文心**（ERNIE）—— 自研
- 第三方模型

#### 平台

- **千帆**（大模型平台）
- 百度智能云

#### 特色

- 搜索 + AI
- Apollo 自动驾驶
- 文心系列

### 6.5 京东云

- **言犀**（Yanxi）
- 供应链 AI
- 客服场景

### 6.6 对比表

| 云 | 旗舰模型 | 网关 | 推理 | 特色 |
|---|---|---|---|---|
| **AWS** | Claude / Llama | API Gateway | Bedrock / SageMaker | 全球、生态 |
| **Azure** | GPT | APIM | Azure OpenAI | 企业、合规 |
| **Google** | Gemini | Apigee | Vertex AI | 多模态、技术 |
| **阿里云** | 通义 | Higress | PAI | 国内生态、电商 |
| **腾讯云** | 混元 | API Gateway | TI | 微信、音视频 |
| **华为云** | 盘古 | APIG | ModelArts | 信创、政企 |
| **字节** | 豆包 | 火山方舟 | 火山引擎 | 价格、内部应用 |
| **百度** | 文心 | 千帆 | 百度智能云 | 搜索、Apollo |

---

## 七、跨云 AI 网关

### 7.1 为何需要跨云

| 需求 | 描述 |
|---|---|
| **多云策略** | 避免厂商锁定 |
| **区域合规** | 不同地区用不同云 |
| **成本优化** | 不同云价格不同 |
| **高可用** | 多云容灾 |
| **最佳模型** | 不用绑定单一云 |

### 7.2 跨云 AI 网关实现

```python
class MultiCloudGateway:
    def __init__(self, providers):
        self.providers = providers  # {"aws": ..., "azure": ..., "gcp": ...}
    
    async def route(self, request):
        # 1. 选云
        cloud = self._select_cloud(request)
        
        # 2. 协议适配
        if cloud == "aws":
            return await self._call_bedrock(request)
        elif cloud == "azure":
            return await self._call_azure_openai(request)
        elif cloud == "gcp":
            return await self._call_vertex_ai(request)
        elif cloud == "alibaba":
            return await self._call_dashscope(request)
    
    def _select_cloud(self, request):
        # 策略：成本、延迟、合规、模型能力
        if request.requires("europe_data_residency"):
            return "azure"  # 假设 Azure 欧洲可用
        if request.model == "gemini-2.0-pro":
            return "gcp"  # Gemini 只能在 GCP
        if request.budget == "low":
            return "alibaba"  # 假设通义便宜
        return "aws"  # 默认
```

### 7.3 跨云的挑战

| 挑战 | 描述 |
|---|---|
| **协议差异** | AWS / Azure / GCP / 阿里云 API 不同 |
| **认证** | 各家不同（API Key、IAM、Service Account） |
| **数据格式** | 略有差异（但 OpenAI 协议逐渐统一） |
| **监控** | 各家独立 |
| **成本核算** | 各家账单不同 |
| **网络** | 跨云延迟 |
| **合规** | 不同地区不同法规 |

### 7.4 跨云 AI 网关模式

```
                    ┌─────────────────────┐
                    │  Multi-Cloud Gateway│
                    │  (自建或 Portkey)   │
                    └──────────┬──────────┘
                               │
        ┌──────────────┬───────┴──────┬──────────────┐
        ↓              ↓              ↓              ↓
    ┌───────┐    ┌───────┐    ┌───────┐    ┌───────┐
    │ AWS  │    │ Azure │    │ GCP   │    │ 阿里云 │
    └───────┘    └───────┘    └───────┘    └───────┘
```

### 7.5 工具

- **Portkey**：支持多云
- **LiteLLM**：支持多 provider
- **自建**：用 LiteLLM + Portkey 的能力

---

## 八、企业混合云 AI 网关架构

### 8.1 典型企业架构

```
┌────────────────────────────────────────────┐
│  企业总部 / 研发中心                         │
│                                            │
│  ┌──────────────────────────────────┐      │
│  │  AI Gateway (Higress / Kong)     │      │
│  │  - 统一认证                      │      │
│  │  - 统一限流                      │      │
│  │  - 统一计费                      │      │
│  │  - 统一审计                      │      │
│  └────────────┬─────────────────────┘      │
└───────────────┼────────────────────────────┘
                │
    ┌───────────┼──────────────┐
    ↓           ↓              ↓
┌─────────┐ ┌─────────┐  ┌─────────┐
│ 私有云  │ │ 公有云  │  │ SaaS    │
│ (自托管 │ │ (Bedrock│  │ (OpenAI)│
│  vLLM)  │ │  Azure) │  │         │
└─────────┘ └─────────┘  └─────────┘
```

### 8.2 路由策略

```python
ENTERPRISE_ROUTING = {
    # 敏感数据 → 私有云
    "sensitive_data": {
        "match": {"data_classification": "high"},
        "target": "private_cloud",
        "models": ["self-hosted-qwen-72b"]
    },
    # 通用任务 → 公有云
    "general": {
        "match": {},
        "target": "public_cloud",
        "models": ["gpt-4o", "claude-sonnet"]
    },
    # 探索性 → SaaS
    "experimental": {
        "match": {"tag": "experimental"},
        "target": "saas",
        "models": ["gpt-4o-mini", "claude-haiku"]
    }
}
```

### 8.3 数据驻留合规

| 地区 | 合规要求 | 云选择 |
|---|---|---|
| **欧盟** | GDPR | 欧盟 region（AWS Frankfurt、Azure West Europe） |
| **中国** | 数据出境法 | 阿里云/腾讯云 国内 region |
| **美国政府** | FedRAMP | AWS GovCloud / Azure Government |
| **医疗** | HIPAA | BAA 合规云 |
| **金融** | PCI-DSS | 专用云 |

**AI Gateway 必须支持**：
- 按租户路由到不同云
- 数据驻留标签传递
- 合规审计

### 8.4 灾备

```python
# 多云 active-active
PRIMARY = "aws-us-east-1"
SECONDARY = "azure-east-us"

def route_with_failover(request):
    try:
        return call_with_retry(primary, request, max_retries=2)
    except FailoverTrigger:
        return call_with_retry(secondary, request)
```

---

## 九、云原生 AI 网关

### 9.1 K8s 上的 AI Gateway

```yaml
# Higress on K8s
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-gateway
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: higress
        image: higress-registry.cn-hangzhou.aliyuncs.com/higress/higress:latest
        ports:
        - containerPort: 80
        - containerPort: 443
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
```

### 9.2 Gateway API（K8s 标准）

```yaml
# K8s Gateway API + AI 扩展
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: llm-routes
spec:
  parentRefs:
  - name: ai-gateway
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/chat
    backendRefs:
    - name: gpt4o-service
      kind: Service
      port: 8000
    - name: claude-service
      kind: Service
      port: 8000
    filters:
    - type: ExtensionRef
      extensionRef:
        group: ai.gateway.io
        kind: AIRoutePolicy
        name: smart-routing
```

### 9.3 Gateway API Inference Extension

**CNCF 新项目**（2024）：

```
Gateway API
    + Inference Extension
        ├── Model Routing
        ├── Token-aware Load Balancing
        ├── Prefix-aware Routing
        └── Model Pool Management
```

**特点**：
- 标准化 K8s 上的 AI Gateway
- 集成 Envoy Gateway
- 集成 vLLM 等推理引擎

### 9.4 Service Mesh 集成

```
Istio + AI Gateway
├── Envoy sidecar
├── mTLS
├── 流量管理
└── 可观测
```

**Istio AI 扩展**（实验性）

### 9.5 Operator 模式

```python
# K8s Operator 管理 AI Gateway 生命周期
class AIGatewayOperator:
    def reconcile(self, gateway):
        # 1. 创建/更新 Gateway
        # 2. 配置路由
        # 3. 配置 Provider
        # 4. 配置 Guardrails
        # 5. 配置监控
        pass
    
    def scale(self, metrics):
        # 根据 QPS 自动伸缩
        pass
```

---

## 十、未解难题与研究前沿

### 10.1 厂商锁定

1. **跨云迁移**的实际可行性
2. **数据导出**的格式标准化
3. **微调模型**的可移植性
4. **企业级"中立"网关**的真正落地
5. **锁定 vs 集成的取舍**

### 10.2 多云

6. **多云延迟优化**
7. **跨云成本对比**实时
8. **跨云合规审计**
9. **多云身份联邦**
10. **多云灾难恢复** RTO/RPO

### 10.3 云原生

11. **K8s Gateway API AI 扩展**标准化
12. **Serverless LLM** 与 K8s 集成
13. **GPU 共享** vs 独占的最优
14. **多租户在 K8s 上的隔离**
15. **冷启动优化**（K8s 视角）

### 10.4 合规

16. **跨境数据传输**的 AI Gateway 设计
17. **数据驻留**的强制保证
18. **主权 AI** 的实现
19. **AI 法规**（EU AI Act 等）的技术落地
20. **审计追踪** 的合规性

### 10.5 经济

21. **云厂商定价**的隐性成本
22. **跨云价格套利** 的可能性
23. **长期合约 vs 按量** 的最优
24. **云厂商锁定成本**的量化
25. **云迁移 ROI** 测算

### 10.6 未来

26. **AI 网关的云无关性** 标准化
27. **Serverless AI** 与传统云的边界
28. **边缘云** 的 AI 部署
29. **AI 服务的网络效应**
30. **"AI 云"** 概念的出现

---

## 十一、参考资料

### 11.1 官方文档

- AWS Bedrock（aws.amazon.com/bedrock）
- AWS API Gateway
- Azure OpenAI（learn.microsoft.com/azure/ai-services/openai）
- Azure API Management
- Google Vertex AI（cloud.google.com/vertex-ai）
- Google Apigee
- 阿里云百炼（bailian.console.aliyun.com）
- 阿里云 Higress（higress.cn）
- 腾讯云 TI 平台
- 华为云盘古
- 火山引擎方舟

### 11.2 K8s / 云原生

- Gateway API（gateway-api.sigs.k8s.io）
- Gateway API Inference Extension
- Istio 文档
- Envoy AI Gateway

### 11.3 工具

- Portkey（多云）
- LiteLLM（多 provider）
- Higress（K8s 网关）
- Kong（K8s 网关）

### 11.4 关键博客

- AWS "Bedrock GA"
- Azure "Azure OpenAI Service"
- Google "Vertex AI updates"
- 阿里云"通义大模型"
- 火山引擎"豆包大模型"

### 11.5 行业分析

- Gartner "Magic Quadrant for AI Gateways"
- Forrester "AI Infrastructure"
- IDC "AI in Cloud"

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 批 · 第 6 篇
- 主题：公有云深度集成
- 上一份：15-open-source-contribution.md
- 下一份预告：RAG 场景的网关优化
