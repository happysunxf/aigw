# 边缘 AI Gateway：边缘推理、CDN 集成与延迟优化

> 系列：AI Gateway 持续深挖 · 第 7 篇
> 性质：纯技术研究
> 范围：边缘 AI 推理架构、CDN 集成、低延迟优化、Cloudflare Workers AI 范式、Serverless 推理

---

## 目录

- [一、为什么需要"边缘 AI"](#一为什么需要边缘-ai)
- [二、边缘 AI 架构分类](#二边缘-ai-架构分类)
- [三、Cloudflare Workers AI 范式](#三cloudflare-workers-ai-范式)
- [四、边缘 LLM 推理的技术挑战](#四边缘-llm-推理的技术挑战)
- [五、边缘缓存 vs 边缘推理](#五边缘缓存-vs-边缘推理)
- [六、模型分发与冷启动](#六模型分发与冷启动)
- [七、CDN 厂商的 AI 布局](#七cdn-厂商的-ai-布局)
- [八、边缘 ↔ 中心协同架构](#八边缘--中心协同架构)
- [九、Serverless 推理平台](#九serverless-推理平台)
- [十、低延迟优化技术](#十低延迟优化技术)
- [十一、隐私与数据本地化](#十一隐私与数据本地化)
- [十二、未解难题与研究前沿](#十二未解难题与研究前沿)
- [十三、参考资料](#十三参考资料)

---

## 一、为什么需要"边缘 AI"

### 1.1 延迟的物理极限

光速限制：地球周长 40,000 km，**光纤中光速约 200,000 km/s**，单程最远 100ms（半个地球）。

| 用户位置 | 数据中心距离 | 物理延迟 |
|---|---|---|
| 同城 | < 50 km | < 0.5 ms |
| 同国 | 1000-3000 km | 5-15 ms |
| 跨洲 | 5000-10000 km | 25-50 ms |
| 半个地球 | 20000 km | 100 ms+ |

**LLM 调用** = 网络延迟 + 推理延迟（首 token 200-2000ms）

### 1.2 边缘 AI 的目标

```
把 LLM 推理推到离用户最近的地方：
- 首 token 延迟从 1s 降到 100-300ms
- 跨洲请求不绕路
- 数据不出本地（隐私）
- 主中心故障时不挂
```

### 1.3 边缘 vs 中心的差异

| 维度 | 中心 | 边缘 |
|---|---|---|
| **位置** | 1-10 个大区域 | 100-1000+ PoP |
| **硬件** | 8x H100 / A100 | 1-2 GPU / CPU |
| **模型** | 全尺寸大模型 | 量化/小模型 |
| **存储** | TB 级 | GB 级 |
| **网络** | 高带宽 | 受限 |
| **运维** | 集中 | 分布式、难管 |
| **成本** | 高固定成本 | 按用量计费 |

### 1.4 谁在推边缘 AI

- **CDN 厂商**：Cloudflare、Fastly、Akamai、Bunny
- **云厂商**：AWS Lambda@Edge、Azure Edge Zones
- **AI 厂商**：Hugging Face Endpoints、Replicate、Modal
- **创业公司**：Together AI、Anyscale、Fireworks

---

## 二、边缘 AI 架构分类

### 2.1 四种边缘 AI 范式

```
┌─────────────────────────────────────────────────┐
│ 范式 1：纯缓存（请求根本不回源）                  │
│   Edge PoP 缓存完整响应                          │
├─────────────────────────────────────────────────┤
│ 范式 2：轻量推理（边缘跑小模型）                  │
│   Edge PoP 跑 1-7B 量化模型                      │
├─────────────────────────────────────────────────┤
│ 范式 3：路由 + 智能调度                           │
│   Edge 决定路由到哪个中心 / 边缘实例              │
├─────────────────────────────────────────────────┤
│ 范式 4：预处理/后处理（边缘做 Guardrails 等）      │
│   Edge 做 PII 检测、流量清洗，主中心做推理         │
└─────────────────────────────────────────────────┘
```

### 2.2 范式 1：纯缓存

```
User → Edge PoP（缓存命中）→ 返回
                ↓ (miss)
              Origin
```

**优势**：极致延迟（< 10ms）
**局限**：必须有重复请求
**代表**：Cloudflare AI Gateway 缓存

### 2.3 范式 2：轻量推理

```
User → Edge PoP（运行 1-7B 量化模型）→ 返回
```

**优势**：低延迟、隐私
**局限**：模型能力有限
**代表**：Cloudflare Workers AI、AWS Lambda@Edge

### 2.4 范式 3：路由调度

```
User → Edge PoP（智能选 origin）→ 中心 LLM
```

**优势**：透明、成本可控
**局限**：不解决延迟

### 2.5 范式 4：边缘预处理

```
User → Edge（Guardrails、限流）→ 中心 LLM
                                ↓
User ← Edge（日志、缓存）     ← 中心 LLM
```

**优势**：减轻中心负担、合规前置
**局限**：边缘要能跑 ML 模型

### 2.6 混合范式（最常见）

```
User
  ↓
Edge PoP 1 (缓存 + Guardrails + 轻量意图分类)
  ↓ (复杂请求)
中心 LLM
  ↓
Edge PoP 1 (流式响应 + 局部缓存)
  ↓
User
```

---

## 三、Cloudflare Workers AI 范式

### 3.1 架构

```
┌─────────────────────────────────────────────┐
│ Cloudflare Network                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │ PoP1 │ │ PoP2 │ │ PoP3 │ │ PoP4 │      │
│  │GPU  │ │GPU  │ │CPU  │ │GPU  │ ...  │
│  │model│ │model│ │small │ │model│      │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘      │
│     └────────┴────────┴────────┘            │
│              shared config                  │
└─────────────────────────────────────────────┘
```

### 3.2 Workers AI API

```javascript
// 在 Cloudflare Worker 里调用
import { Ai } from '@cloudflare/ai';

export default {
    async fetch(request, env) {
        const ai = new Ai(env.AI);
        const response = await ai.run('@cf/meta/llama-3.1-8b-instruct', {
            messages: [
                { role: "system", content: "You are a helpful assistant" },
                { role: "user", content: "Hello!" }
            ]
        });
        return new Response(JSON.stringify(response));
    }
};
```

### 3.3 关键设计

| 设计 | 描述 |
|---|---|
| **Worker** | 边缘运行的 V8 isolate |
| **AI binding** | 同一 isolate 内调用 AI 模型 |
| **GPU 池** | 每个 PoP 有 GPU 池 |
| **模型分发** | 模型按需下载到 PoP |
| **冷启动** | 首次推理需 5-30s（模型加载） |

### 3.4 支持的模型

- Llama 3.1 8B / 70B（量化）
- Mistral 7B
- Qwen 1.5 7B / 14B
- Phi-2
- 各种 embedding 模型

### 3.5 AI Gateway（Cloudflare 配套）

```javascript
// 不一定要用 Workers AI 模型
// 也可以代理到 OpenAI
const response = await fetch(
    "https://gateway.ai.cloudflare.com/v1/.../openai/chat/completions",
    {
        method: "POST",
        headers: { "Authorization": `Bearer ${env.OPENAI_KEY}` },
        body: JSON.stringify({
            model: "gpt-4o",
            messages: [...]
        })
    }
);
```

**AI Gateway 提供**：
- 缓存（精确 + 语义）
- 可观测
- 速率限制
- 成本分析
- Fallback

---

## 四、边缘 LLM 推理的技术挑战

### 4.1 硬件约束

边缘 GPU 资源有限：
- Cloudflare PoP：L4 / A30（24GB 显存）
- Lambda@Edge：无 GPU，靠 CPU
- 移动端 / IoT：NPU / 手机芯片

**后果**：
- 只能跑 7B / 13B 量化模型
- 不能跑 70B+ 全精度模型
- 上下文窗口受限

### 4.2 量化技术

| 量化 | 精度 | 大小 | 性能损失 |
|---|---|---|---|
| **FP16** | 16-bit | 100% | 0% |
| **INT8** | 8-bit | 50% | < 1% |
| **INT4** | 4-bit (GPTQ) | 25% | 1-3% |
| **INT4** | 4-bit (AWQ) | 25% | 0.5-1.5% |
| **INT2** | 2-bit | 12.5% | 5-10% |
| **1-bit** | BitNet | 6.25% | 待观察 |

**边缘常用**：INT4 / INT8

```python
# 量化示例
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    quantization_config=quantization_config
)
```

### 4.3 模型并行 vs 流水线并行

边缘单卡放不下大模型时：

#### 方案 A：张量并行

```
将单个矩阵切到多卡
需要 NVLink（边缘不一定有）
```

#### 方案 B：流水线并行

```
Layer 0-10 → GPU 1
Layer 11-20 → GPU 2
Layer 21-30 → GPU 3
Layer 31-40 → GPU 4

气泡大、延迟高
```

#### 方案 C：拆分到多个 PoP

```
Layer 0-20 → PoP 1
Layer 21-40 → PoP 2

跨 PoP 网络成瓶颈
```

**现实**：边缘跑大模型不现实，**用小模型 + 中心 fallback**。

### 4.4 模型分发挑战

```
模型 70GB
PoP 1 万个
总数据 = 700 PB
```

**问题**：
- 存储成本
- 分发速度
- 同步一致性

**解决**：
- 模型分片、按需下载
- 中心化训练 → 边缘推理时下载
- 量化后大小降到 20GB

### 4.5 冷启动

| 操作 | 时间 |
|---|---|
| Worker 启动 | 5ms |
| 模型加载到 GPU | 10-60s |
| KV cache 预热 | 1-5s |
| 首次推理 | 200-2000ms |
| **总冷启动** | **12-65s** |

**缓解**：
- 模型预加载
- Warm pool（保活）
- Lazy loading（部分加载）

---

## 五、边缘缓存 vs 边缘推理

### 5.1 何时用缓存

**缓存适合**：
- 高重复率场景（客服 FAQ、文档问答）
- 接受过期（业务允许 1 小时前数据）
- 内容可哈希

**缓存不适合**：
- 高度个性化（每个用户不同）
- 实时性强（新闻、股票）
- 用户内容（隐私）

### 5.2 何时用推理

**推理适合**：
- 复杂生成（创作、代码）
- 个性化（基于用户上下文）
- 低重复（长尾问题）

**推理不适合**：
- 模型太大
- 延迟要求 < 100ms
- 成本敏感

### 5.3 决策树

```
Request
  ↓
[ 是否可缓存？]  ← 哈希 / 相似度判断
  ├─ Yes → 边缘缓存返回
  └─ No
       ↓
     [ 是否需大模型？]
       ├─ Yes → 路由到中心
       └─ No
            ↓
         [ 边缘有相应模型？]
            ├─ Yes → 边缘推理
            └─ No → 路由到中心
```

---

## 六、模型分发与冷启动

### 6.1 模型分发架构

```
Model Registry (S3 / HF Hub)
       ↓
CDN（模型版本）
       ↓
Edge PoPs（按需拉取）
       ↓
本地 SSD（缓存）
```

### 6.2 优化技术

#### 优化 1：模型分片

```python
# 模型分片，按 layer 切分
# 推理时按需加载
def load_model_shard(model_id, layer_start, layer_end):
    url = f"https://cdn.example.com/{model_id}/shard_{layer_start}-{layer_end}.safetensors"
    return load_from_url(url)
```

#### 优化 2：预热

```python
# Worker 空闲时预热
async def preheat_model(model_id):
    # 加载到 GPU
    model = load_model(model_id)
    # 一次 dummy 推理
    model(dummy_input)
    # 模型现在已"热"
    return model
```

#### 优化 3：模型预取

```python
# 根据流量预测，提前下载
def predict_traffic(time_of_day):
    # 早上 9 点 → 预加载客服模型
    # 晚上 8 点 → 预加载创意写作模型
    pass
```

### 6.3 Cloudflare 的"模型分片"做法

Cloudflare 把模型分到多个 PoP，推理时跨 PoP 协作（虽然不公开细节）。理论上有几种做法：

- **垂直分片**：按 layer 切
- **水平分片**：按 batch 切
- **专家并行**：MoE 模型的不同 expert 在不同 PoP

---

## 七、CDN 厂商的 AI 布局

### 7.1 Cloudflare

| 产品 | 特点 |
|---|---|
| **Workers AI** | 边缘 GPU 推理 |
| **AI Gateway** | 代理 + 缓存 + 可观测 |
| **Vectorize** | 边缘向量数据库 |
| **D1** | 边缘 SQL 数据库 |
| **R2** | 边缘对象存储 |
| **Durable Objects** | 边缘有状态计算 |

### 7.2 Fastly

| 产品 | 特点 |
|---|---|
| **Compute@Edge** | WebAssembly 边缘计算 |
| **Fastly AI** | 边缘 LLM（有限模型） |
| **Bot Management** | AI 流量识别 |

### 7.3 Akamai

| 产品 | 特点 |
|---|---|
| **Cloud Inference** | 边缘推理 |
| **Content Protector** | LLM 滥用防护 |
| **App & API Protector** | API 安全 |

### 7.4 AWS

| 产品 | 特点 |
|---|---|
| **Lambda@Edge** | 边缘函数（无 GPU） |
| **CloudFront** | CDN |
| **Bedrock** | 中心 LLM 推理 |
| **SageMaker** | 自托管模型 |
| **Inferentia** | AWS 自研推理芯片 |

### 7.5 Azure

| 产品 | 特点 |
|---|---|
| **Azure Front Door** | CDN |
| **Azure Functions** | 边缘函数 |
| **Azure OpenAI** | 中心 LLM |
| **Azure AI Foundry** | 模型管理 |

### 7.6 Google Cloud

| 产品 | 特点 |
|---|---|
| **Cloud CDN** | CDN |
| **Cloud Run** | 区域 Serverless |
| **Vertex AI** | 中心 LLM |
| **Media CDN** | 视频优化 |

### 7.7 阿里云

| 产品 | 特点 |
|---|---|
| **ESA** | 边缘安全加速 |
| **函数计算** | 边缘函数 |
| **PAI / 通义** | 中心 LLM |
| **边缘容器** | 边缘 K8s |

---

## 八、边缘 ↔ 中心协同架构

### 8.1 分层架构

```
┌──────────────────────────────────────┐
│ Tier 0: 用户端（浏览器 / App）         │
│   • 本地缓存                          │
│   • 客户端 LLM（WebLLM, MLC-LLM）     │
├──────────────────────────────────────┤
│ Tier 1: 边缘 PoP                       │
│   • 缓存                              │
│   • 轻量推理                          │
│   • Guardrails                        │
│   • 路由                              │
├──────────────────────────────────────┤
│ Tier 2: 区域中心                       │
│   • 中等模型                          │
│   • 复杂推理                          │
├──────────────────────────────────────┤
│ Tier 3: 主中心                         │
│   • 最大模型                          │
│   • 训练 / 微调                        │
│   • 全局可观测                         │
└──────────────────────────────────────┘
```

### 8.2 请求路由策略

```python
def route_request(request, user_location):
    # 检查边缘缓存
    if cached := edge_cache.get(request):
        return cached, "edge_cache"
    
    # 简单查询用边缘小模型
    if is_simple_query(request):
        if edge_model := edge_models.find_capable(request.task):
            return edge_model.infer(request), "edge_inference"
    
    # 复杂查询路由到中心
    nearest_center = pick_nearest_center(user_location, centers)
    return nearest_center.infer(request), "central_inference"
```

### 8.3 模型协调

```python
# 边缘 + 中心协同
async def hybrid_inference(query):
    # 1. 边缘小模型快速响应
    quick_response = await edge_model.infer(query, max_tokens=200)
    
    # 2. 检查是否够好
    if is_good_enough(quick_response):
        return quick_response
    
    # 3. 不够好？升级到中心大模型
    final_response = await central_model.infer(query)
    return final_response
```

### 8.4 跨层缓存一致性

```python
# L1 (Edge) → L2 (Region) → L3 (Center)
# 写入时多级失效
def write_data(key, value):
    central_cache.set(key, value)
    for region in regions:
        region.cache.set(key, value)
        for pop in region.pops:
            pop.cache.set(key, value)

# 读时多级查找
def read_data(key):
    for layer in [edge_cache, region_cache, central_cache]:
        if value := layer.get(key):
            return value
    return None
```

---

## 九、Serverless 推理平台

### 9.1 Serverless LLM 的范式

```python
# 部署成 Serverless 函数
@app.function(
    gpu="A10G",
    memory=16,
    timeout=300,
)
def llm_inference(prompt: str) -> str:
    model = load_model()  # 冷启动时加载
    return model.generate(prompt)
```

**平台**：
- Modal
- Replicate
- RunPod Serverless
- AWS SageMaker Serverless
- Together AI
- Fireworks AI

### 9.2 冷启动 vs 成本

| 模式 | 冷启动 | 成本 |
|---|---|---|
| **常驻 GPU** | 0s | 高（按小时） |
| **Serverless** | 5-60s | 低（按请求） |
| **Warm Pool** | < 1s | 中 |
| **预热** | < 1s | 中高 |

### 9.3 Modal 详解

```python
import modal

stub = modal.Stub()
image = modal.Image.debian_slim().pip_install("vllm")

@stub.function(gpu="A100", image=image, timeout=600)
async def generate(prompt: str) -> str:
    from vllm import LLM
    llm = LLM("meta-llama/Llama-3.1-70B")
    return llm.generate(prompt)

# 调用
with stub.run():
    result = generate.remote("Hello!")
```

**特点**：
- 自动冷启动管理
- 模型自动缓存
- 流式响应支持
- Webhook 触发

### 9.4 Replicate 详解

```python
import replicate

output = replicate.run(
    "meta/llama-2-70b-chat:latest",
    input={"prompt": "Hello!"}
)
```

**特点**：
- 大量社区模型
- 一行代码调用
- 按 token 计费
- 支持自定义模型（Cog）

---

## 十、低延迟优化技术

### 10.1 网络层

#### 优化 1：HTTP/2 / HTTP/3

```
HTTP/1.1: 队头阻塞
HTTP/2: 多路复用、二进制
HTTP/3 (QUIC): UDP、0-RTT、多路复用
```

#### 优化 2：连接复用

```python
# 复用上游连接池
import httpx
client = httpx.AsyncClient(
    http2=True,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)
```

#### 优化 3：地理路由

```python
# 用户 IP → 最近 PoP
geo = geoip_lookup(user_ip)
selected_pop = pick_nearest_pop(geo, pops)
```

### 10.2 推理层

#### 优化 1：Speculative Decoding

```
用小模型快速生成候选
用大模型验证
比大模型直接生成快 2-3x
```

#### 优化 2：Continuous Batching

```python
# 传统：一个请求完成才开始下一个
# 连续批：多个请求的 token 交错生成
# 提升吞吐量 10-24x（vLLM 数据）
```

#### 优化 3：KV Cache 优化

- **PagedAttention**（vLLM）：KV cache 分页管理
- **Prefix Caching**：共享 prefix 的 KV cache
- **Quantized KV Cache**：KV cache 量化

#### 优化 4：FlashAttention

```
标准 Attention: O(N²) 内存
FlashAttention: O(N) 内存，速度 2-4x
```

### 10.3 协议层

#### 优化 1：流式响应（必须）

```python
# 第一个 token 延迟 vs 总延迟
# 流式：用户看到第一个 token 100-300ms
# 非流式：用户看到完整响应 2-10s
```

#### 优化 2：SSE vs WebSocket

| 维度 | SSE | WebSocket |
|---|---|---|
| 协议 | HTTP | 升级 |
| 方向 | 单向（服务器→客户端） | 双向 |
| 适合 | LLM 流式输出 | 双向交互 |

#### 优化 3：gRPC Streaming

```protobuf
service LLMService {
    rpc Generate(GenerateRequest) returns (stream GenerateResponse);
}
```

### 10.4 应用层

#### 优化 1：预取 + 预生成

```python
# 用户在输入框打字时
# 后台就开始预生成
# 用户提交时，部分响应已就绪
```

#### 优化 2：本地缓存

```python
# 浏览器 IndexedDB
# App 本地 SQLite
# 节省网络往返
```

#### 优化 3：客户端 LLM（WebLLM）

```javascript
// 浏览器里跑 LLM（隐私 + 离线）
import { WebLLM } from "@mlc-ai/web-llm";
const engine = await WebLLM.create({
    model: "Llama-3.1-8B-q4f16_1"
});
const response = await engine.chat.completions.create({
    messages: [{ role: "user", content: "Hello" }]
});
```

---

## 十一、隐私与数据本地化

### 11.1 数据主权要求

| 法规 | 要求 |
|---|---|
| **GDPR** | 欧盟用户数据不出欧盟 |
| **Schrems II** | 美国云厂商合规 |
| **中国数据安全法** | 数据出境需评估 |
| **俄罗斯数据本地化** | 公民数据必须境内 |
| **印度 DPDP** | 严格本地化 |

### 11.2 边缘 AI 的隐私优势

```
用户数据 →
  Edge PoP（同地区）
  ↓
  推理 → 返回
  
数据从未离开该地区/国家
```

**场景**：
- 欧盟用户 → 欧盟 PoP
- 中国用户 → 中国 PoP
- 医疗数据 → 医院本地 PoP
- 金融数据 → 私有 PoP

### 11.3 同态加密推理

```python
# 数据加密后送推理
encrypted_prompt = he.encrypt(prompt)
result = model.infer(encrypted_prompt)  # 模型不解密
decrypted_result = he.decrypt(result)
```

**现状**：
- 计算开销 1000-10000x
- 还在研究阶段
- 部分公司（Zama, Inpher）有产品

### 11.4 TEE（可信执行环境）

```python
# 在 TEE（Intel SGX / AMD SEV）里跑模型
# 外部看不到模型权重和输入
# 适合：自托管模型的隐私保护
```

---

## 十二、未解难题与研究前沿

### 12.1 模型分发

1. **大模型跨 PoP 分布**——如何最小化数据量
2. **模型分片的最优策略**——按层？按专家？
3. **模型版本一致性**——边缘多 PoP 如何同步升级
4. **模型回滚**——发现问题时怎么回滚
5. **A/B 测试**——边缘 PoP 的多版本流量切分

### 12.2 冷启动

6. **冷启动延迟降至 < 1s** 是否可能？
7. **模型预热的预测算法**——基于历史流量
8. **冷启动与成本的平衡**——多少 warm pool
9. **跨 PoP 冷启动协同**
10. **冷启动对突发流量的应对**

### 12.3 边缘推理能力

11. **边缘能跑多大模型？**——GPU 演进
12. **CPU 推理的极限**——Llama.cpp / GGUF
13. **NPU / 移动端推理**——苹果 ANE、高通 Hexagon
14. **端-边-云协同推理**——分层模型
15. **边缘的并发吞吐**——一个 PoP 同时服务多少用户

### 12.4 边缘-中心协同

16. **何时升级到中心**的决策算法
17. **边缘 + 中心级联**的最佳实践
18. **跨层缓存一致性**——CAP 权衡
19. **多区域部署**——active-active / active-passive
20. **灾备**——边缘 PoP 故障的恢复

### 12.5 安全 / 隐私

21. **边缘节点的物理安全**
22. **多租户模型隔离**——一个 PoP 跑多客户模型
23. **数据出境的自动检测**
24. **边缘的密钥管理**
25. **边缘审计**——日志怎么集中

### 12.6 协议 / 标准化

26. **边缘 LLM 协议**——OpenAI 协议能跑在边缘吗？
27. **WebLLM / MLC-LLM / Llama.cpp 的标准化**
28. **MCP 服务的边缘部署**
29. **A2A 的边缘通信**

### 12.7 经济性

30. **边缘 AI 的单位经济**——什么场景下边缘 AI 划算
31. **Serverless 推理的定价模型**——按 token 还是按秒
32. **冷启动转嫁**——谁付冷启动的钱

### 12.8 未来形态

33. **端云一体**——WebLLM + 边缘 + 中心
34. **"个人 AI 网关"**——每个用户的本地代理
35. **联邦边缘 AI**——边缘节点贡献算力

---

## 十三、参考资料

### 13.1 平台文档

- developers.cloudflare.com/workers-ai
- developers.cloudflare.com/ai-gateway
- docs.fastly.com/products/compute
- aws.amazon.com/lambda/edge
- modal.com/docs
- replicate.com/docs
- runpod.io/docs

### 13.2 论文

- "ServerlessLLM: Low-Latency Serverless Inference for Large Language Models" (2024)
- "LLM Inference Unveiled: Survey and Roofline Model Insights" (2024)
- "EdgeLLM: Efficient Distributed LLM Inference on Edge Devices" (2024)
- "SpecInfer: Accelerating Generative LLM Serving with Speculative Inference" (2024)
- "PagedAttention" (vLLM 论文)
- "FlashAttention" 论文

### 13.3 项目

- github.com/vllm-project/vllm
- github.com/ggerganov/llama.cpp
- github.com/mlc-ai/mlc-llm
- github.com/web-llm/web-llm
- github.com/tatsu-lab/alpaca_eval
- github.com/exllama/exllamav2

### 13.4 博客

- Cloudflare "How Workers AI works"
- Modal "Serverless GPU for ML"
- Replicate "Cog: containers for ML"
- Hugging Face "Inference Endpoints"
- vLLM 团队博客

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 7 篇
- 主题：边缘 AI Gateway
- 上一份：06-guardrails.md
- 下一份预告：vLLM / TGI / Triton 与网关的协同
