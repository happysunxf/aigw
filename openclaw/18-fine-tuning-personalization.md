# Fine-tuning 与个性化 AI 网关

> 系列：AI Gateway 持续深挖 · 第 2 批 · 第 8 篇
> 性质：纯技术研究
> 范围：Fine-tuning 技术详解、个性化 LLM 路径、网关层对 Fine-tuned 模型的支持、个性化路由

---

## 目录

- [一、为什么需要 Fine-tuning](#一为什么需要-fine-tuning)
- [二、Fine-tuning 技术全景](#二fine-tuning-技术全景)
- [三、主流 Fine-tuning 框架与平台](#三主流-fine-tuning-框架与平台)
- [四、Fine-tuning 的数据策略](#四fine-tuning-的数据策略)
- [五、Fine-tuning 的训练基础设施](#五fine-tuning-的训练基础设施)
- [六、Fine-tuning 模型的部署](#六fine-tuning-模型的部署)
- [七、网关与 Fine-tuned 模型](#七网关与-fine-tuned-模型)
- [八、个性化路由](#八个性化路由)
- [九、个性化 RAG 与 Memory](#九个性化-rag-与-memory)
- [十、评估与监控 Fine-tuned 模型](#十评估与监控-fine-tuned-模型)
- [十一、未解难题与研究前沿](#十一未解难题与研究前沿)
- [十二、参考资料](#十二参考资料)

---

## 一、为什么需要 Fine-tuning

### 1.1 Fine-tuning 解决什么问题

| 问题 | Fine-tuning 的解决 |
|---|---|
| **特定领域术语** | 在专业领域（医学、法律）效果差 |
| **特定输出格式** | JSON、代码、特殊格式 |
| **特定风格** | 品牌口吻、企业话术 |
| **降低成本** | 小模型微调替代大模型 |
| **减少延迟** | 7B 替代 70B 提速 10x |
| **数据隐私** | 自托管、不发外部 API |

### 1.2 Fine-tuning vs 其他方案

| 方案 | 数据需求 | 成本 | 效果 | 灵活性 |
|---|---|---|---|---|
| **Prompt Engineering** | 0 | 0 | 中 | 极高 |
| **RAG** | 文档库 | 中 | 高 | 高 |
| **Fine-tuning** | 标注数据 | 高 | 高 | 低 |
| **Fine-tuning + RAG** | 两者 | 高 | 极高 | 中 |

**最佳实践**：**Fine-tuning + RAG 组合**，效果最好。

### 1.3 Fine-tuning 的成本权衡

```
微调 7B 模型
├── 数据准备：~1000-10000 条样本
├── 训练：1-4 GPU · 1-3 天
├── 训练成本：~$100-500
└── 推理：比通用模型便宜 5-10x

vs 用 GPT-4o
└── 每月 1000 万 token：~$150-300
```

**结论**：流量大时，微调便宜；流量小时，API 灵活。

---

## 二、Fine-tuning 技术全景

### 2.1 Fine-tuning 方法分类

#### 全参数微调（Full Fine-tuning）

```
预训练模型权重全部更新
├── 优点：效果最好
├── 缺点：成本高、需要大显存
└── 适用：大厂、有充足算力
```

#### LoRA（Low-Rank Adaptation）

```
冻结预训练权重
加低秩矩阵（A·B）作为 adapter
只训练 adapter
├── 优点：参数少（< 1%）、显存省
├── 缺点：略低于全参数
└── 适用：最常用
```

#### QLoRA

```
4-bit 量化 + LoRA
├── 优点：更省显存
└── 适用：单卡微调大模型
```

#### Adapter Tuning

```
插入 adapter 层
├── Houlsby Adapter
├── Pfeiffer Adapter
└── 适用：多任务学习
```

#### Prefix Tuning

```
训练前缀 token
├── 优点：参数极少
└── 适用：生成任务
```

#### Prompt Tuning

```
只训练 soft prompt embedding
├── 优点：参数最少
└── 适用：少样本学习
```

#### RLHF / DPO

```
基于人类反馈的强化学习
├── RLHF：PPO + Reward Model
├── DPO：直接偏好优化
└── 适用：对齐人类偏好
```

### 2.2 各方法对比

| 方法 | 可训练参数 | 显存需求 | 训练速度 | 效果 |
|---|---|---|---|---|
| **Full FT** | 100% | 极高 | 慢 | 100% |
| **LoRA (r=16)** | 0.1-1% | 中 | 中 | 95-99% |
| **QLoRA** | 0.1-1% | 低 | 中 | 92-97% |
| **Adapter** | 1-5% | 中 | 中 | 95-98% |
| **Prefix Tuning** | 0.01% | 低 | 快 | 85-92% |
| **Prompt Tuning** | 0.001% | 极低 | 快 | 80-90% |

### 2.3 SFT（监督微调）vs RLHF

#### SFT（Supervised Fine-tuning）

```python
# 最简单
training_data = [
    {"input": "...", "output": "..."},
    ...
]
model.train(training_data)
```

**适用**：
- 学习特定任务
- 学习特定格式
- 学习特定风格

#### RLHF

```python
# 三步
# 1. SFT
model = sft(base_model, data)
# 2. 训练 Reward Model
reward_model = train_reward(prompts, ranked_responses)
# 3. PPO 优化
model = ppo_optimize(model, reward_model)
```

**适用**：
- 对齐人类偏好
- 安全
- 复杂指令

#### DPO（Direct Preference Optimization）

```python
# 比 RLHF 简单
training_data = [
    {"prompt": "...", "chosen": "...", "rejected": "..."},
    ...
]
model = dpo_train(base_model, training_data)
```

**优势**：
- 不需要 Reward Model
- 不需要 PPO
- 训练稳定

### 2.4 持续预训练（Continual Pre-training）

```
在大规模无标注数据上继续训练
让模型掌握新领域的语言、术语
```

**适用**：
- 法律、医学等专业领域
- 多语言扩展
- 新兴概念（AI 网关、MCP）

---

## 三、主流 Fine-tuning 框架与平台

### 3.1 开源框架

| 框架 | 维护方 | 特点 |
|---|---|---|
| **Transformers** | HuggingFace | 通用、易用 |
| **PEFT** | HuggingFace | LoRA / QLoRA 标准 |
| **TRL** | HuggingFace | RLHF / DPO |
| **Axolotl** |社区 | 一站式微调 |
| **LLaMA-Factory** | 社区 | 中文友好 |
| **Unsloth** | Unsloth.ai | 速度 2-5x |
| **LoRA** | 社区 | 经典 |
| **Swift** | 魔搭 | 阿里 |

### 3.2 商业平台

| 平台 | 特点 |
|---|---|
| **OpenAI Fine-tuning** | GPT-3.5 / GPT-4o 官方 |
| **Anthropic Fine-tuning** | Claude（部分模型） |
| **Google Vertex AI Tuning** | Gemini + 开源模型 |
| **AWS SageMaker** | 自定义训练 |
| **Azure OpenAI Fine-tuning** | GPT 模型 |
| **Together AI** | 开源模型微调 |
| **Anyscale** | Ray 平台 |
| **Fireworks AI** | 多种模型 |
| **Replicate** | Cog 训练 |
| **Modal** | Serverless 训练 |

### 3.3 OpenAI Fine-tuning 详解

```python
# 1. 准备数据
training_data = [
    {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    },
    ...
]

# 2. 上传
with open("train.jsonl", "w") as f:
    for item in training_data:
        f.write(json.dumps(item) + "\n")

# 3. 创建微调任务
from openai import OpenAI
client = OpenAI()

file = client.files.create(file=open("train.jsonl", "rb"), purpose="fine-tune")

job = client.fine_tuning.jobs.create(
    training_file=file.id,
    model="gpt-4o-mini-2024-07-18",
    hyperparameters={
        "n_epochs": 3,
        "batch_size": 4,
        "learning_rate_multiplier": 0.1
    }
)

# 4. 等待完成
while job.status not in ["succeeded", "failed"]:
    job = client.fine_tuning.jobs.retrieve(job.id)
    time.sleep(30)

# 5. 使用微调模型
response = client.chat.completions.create(
    model=job.fine_tuned_model,  # "ft:gpt-4o-mini:..."
    messages=[{"role": "user", "content": "..."}]
)
```

### 3.4 HuggingFace PEFT 详解

```python
from peft import LoraConfig, get_peft_model, TaskType
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 加载模型
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

# LoRA 配置
lora_config = LoraConfig(
    r=16,  # rank
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM
)

# 应用 LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()  # "trainable params: 13.6M || all params: 8.1B || trainable: 0.17%"

# 训练
from transformers import Trainer, TrainingArguments

training_args = TrainingArguments(
    output_dir="./lora-llama",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=2e-4,
    fp16=True
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    tokenizer=tokenizer
)

trainer.train()

# 保存 LoRA
model.save_pretrained("./lora-llama-final")
```

### 3.5 LLaMA-Factory 详解

```bash
# 一行命令微调
llamafactory-cli train \
    --model_name_or_path meta-llama/Llama-3.1-8B \
    --template llama3 \
    --dataset alpaca_zh,identity \
    --output_dir ./lora-llama \
    --finetuning_type lora \
    --lora_rank 8 \
    --per_device_train_batch_size 2 \
    --num_train_epochs 3
```

**优势**：
- 中文友好
- 一键脚本
- Web UI（可选）
- 多种数据集格式

### 3.6 Unsloth 详解

```python
# 比 HF PEFT 快 2-5x，显存省 40%
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="meta-llama/Llama-3.1-8B",
    max_seq_length=2048,
    dtype=None,  # auto
    load_in_4bit=True,
)

# 加 LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=16,
    use_gradient_checkpointing="unsloth"
)

# 训练
from trl import SFTTrainer
trainer = SFTTrainer(...)
trainer.train()
```

**特别适合**：单卡 / 笔记本 / 边缘训练。

---

## 四、Fine-tuning 的数据策略

### 4.1 数据准备

#### 数据来源

| 来源 | 适用 |
|---|---|
| **历史对话** | 客服、销售场景 |
| **专家标注** | 专业领域 |
| **公开数据集** | Alpaca / ShareGPT |
| **合成数据** | 用 LLM 生成 |
| **用户反馈** | 持续改进 |

#### 数据格式

```jsonl
{"messages": [
  {"role": "system", "content": "..."},
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "..."}
]}
```

#### 数据量

| 任务 | 最少 | 推荐 |
|---|---|---|
| **格式学习** | 100 | 1000 |
| **风格学习** | 500 | 5000 |
| **领域适应** | 1000 | 10000 |
| **能力提升** | 10000+ | 100000+ |

### 4.2 数据质量

**原则**：质量 > 数量。

```python
# 数据清洗
def clean_data(dataset):
    # 1. 去重
    dataset = deduplicate(dataset)
    # 2. 过滤过短
    dataset = filter_length(dataset, min_tokens=20)
    # 3. 过滤低质量
    dataset = filter_quality(dataset, llm_judge)
    # 4. 去敏感
    dataset = filter_sensitive(dataset)
    return dataset
```

### 4.3 合成数据

```python
# 用 GPT-4o 生成训练数据
def generate_synthetic_data(topic, n=1000):
    prompt = f"""Generate {n} high-quality Q&A pairs about {topic}.
    Format as JSON with 'question' and 'answer' fields.
    Focus on practical, real-world scenarios.
    """
    response = gpt4o.generate(prompt, max_tokens=8000)
    data = json.loads(response)
    return data
```

**风险**：
- 幻觉引入
- 模式单一
- 需人工审核

### 4.4 数据增强

```python
# 同义改写
def augment_text(text, llm):
    return llm.generate(
        f"Rewrite the following in 5 different ways:\n{text}",
        max_tokens=2000
    )
```

**方法**：
- 同义改写
- 多语言翻译
- 风格转换
- 反向生成

---

## 五、Fine-tuning 的训练基础设施

### 5.1 硬件需求

| 模型规模 | 显存（全参数） | 显存（LoRA） | 推荐 GPU |
|---|---|---|---|
| 7B | 28GB | 8GB | RTX 4090 / A10 |
| 13B | 52GB | 16GB | A100 40G |
| 70B | 280GB | 40GB | 4x A100 80G |
| 405B | 1.6TB | 160GB | 16x H100 |

### 5.2 训练平台

#### 云端

- **AWS SageMaker** —— 完整 MLOps
- **Azure ML** —— 集成好
- **Google Vertex AI** —— Gemini 训练
- **Lambda Labs** —— 便宜
- **RunPod** —— 灵活
- **Vast.ai** —— 便宜但不稳定

#### 自托管

- **GPU 服务器** —— NVIDIA H100/A100
- **Apple Silicon** —— M2/M3 Max（实验性）
- **国产芯片** —— 昇腾、海光

### 5.3 训练优化

```python
# 关键技术
optimizations = {
    # 显存优化
    "gradient_checkpointing": True,
    "mixed_precision": "bf16",
    "8bit_optimizer": True,
    "zero_redundancy_optimizer": "ZeRO-3",
    
    # 速度优化
    "flash_attention": True,
    "compile": True,  # torch.compile
    
    # 数据
    "packing": True,  # 序列打包
    "data_parallel": True,
}
```

### 5.4 训练监控

```python
# 用 wandb / tensorboard
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="./lora-llama",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=2e-4,
    logging_steps=10,
    report_to="wandb",  # 或 tensorboard
    eval_steps=100,
    save_steps=500
)
```

---

## 六、Fine-tuning 模型的部署

### 6.1 部署方式

#### 方式 1：合并后部署

```python
# 把 LoRA 合并回基础模型
model = model.merge_and_unload()
model.save_pretrained("./merged-model")
```

**优点**：
- 简单
- 推理无额外开销

**缺点**：
- 每个变体需要一份完整模型

#### 方式 2：Adapter 部署

```python
# 基础模型 + 多个 LoRA adapter
# vLLM 支持 multi-LoRA

# 推理时
# base_model + lora_adapter_1 → 输出
# base_model + lora_adapter_2 → 输出
```

**优点**：
- 节省存储（一份 base + 多个小 adapter）
- 灵活切换

**缺点**：
- 实现复杂

#### 方式 3：商业 API 部署

```
OpenAI / Anthropic / Google 等提供的微调模型
直接用 API
```

### 6.2 vLLM 部署多 LoRA

```bash
# 启动
vllm serve meta-llama/Llama-3.1-8B \
    --enable-lora \
    --lora-modules my-lora-1=/path/to/lora-1 my-lora-2=/path/to/lora-2

# 调用
curl http://localhost:8000/v1/chat/completions \
    -d '{
        "model": "my-lora-1",
        "messages": [...]
    }'
```

### 6.3 模型版本管理

```python
# 模型注册表
MODEL_REGISTRY = {
    "base-llama-3.1-8b": {
        "type": "base",
        "path": "meta-llama/Llama-3.1-8B",
        "checksum": "..."
    },
    "customer-support-v1": {
        "type": "fine-tuned",
        "base": "base-llama-3.1-8b",
        "lora_path": "lora/customer-support-v1",
        "version": "1.0",
        "training_data": "data/customer-support-v1.jsonl",
        "metrics": {"accuracy": 0.92, "f1": 0.88}
    },
    "customer-support-v2": {...}
}
```

---

## 七、网关与 Fine-tuned 模型

### 7.1 网关对 Fine-tuned 模型的支持

```
┌────────────────────────────────────────┐
│ AI Gateway                             │
│                                        │
│  Models Registry                       │
│  ├── gpt-4o (OpenAI)                  │
│  ├── claude-sonnet (Anthropic)         │
│  ├── customer-support-v1 (fine-tuned) │  ← 自托管
│  ├── code-assistant-v3 (fine-tuned)    │  ← 自托管
│  └── ...                               │
│                                        │
│  Routing                               │
│  └── customer_support queries →       │
│      customer-support-v1              │
└────────────────────────────────────────┘
```

### 7.2 网关的 Fine-tuned 模型路由

```python
class FineTunedRouter:
    def __init__(self, model_registry, traffic_splitter):
        self.registry = model_registry
        self.splitter = traffic_splitter
    
    async def route(self, request):
        # 1. 识别任务类型
        task_type = await self.classify_task(request)
        
        # 2. 选模型
        if task_type == "customer_support":
            # 灰度发布：新模型 10% 流量
            if random.random() < 0.1:
                return await self.call(
                    self.registry["customer-support-v2"],  # 新模型
                    request
                )
            else:
                return await self.call(
                    self.registry["customer-support-v1"],  # 旧模型
                    request
                )
        
        elif task_type == "code":
            return await self.call(self.registry["code-assistant-v3"], request)
        
        else:
            return await self.call(self.registry["gpt-4o"], request)
```

### 7.3 灰度发布

```python
class CanaryDeployment:
    def __init__(self, traffic_percentages):
        # {"v1": 80, "v2": 20}
        self.percentages = traffic_percentages
    
    def select_model(self):
        r = random.random() * 100
        cumulative = 0
        for model, pct in self.percentages.items():
            cumulative += pct
            if r < cumulative:
                return model
        return list(self.percentages.keys())[0]
```

### 7.4 A/B 测试

```python
class ABTest:
    def __init__(self, variants, metrics_collector):
        self.variants = variants  # {"A": "model-v1", "B": "model-v2"}
        self.metrics = metrics_collector
    
    def select(self, user_id):
        # 按 user_id 哈希，确保一致性
        bucket = hash(user_id) % 2
        if bucket == 0:
            return self.variants["A"]
        else:
            return self.variants["B"]
    
    def record(self, user_id, request, response, feedback=None):
        variant = self.select(user_id)
        self.metrics.record(variant, request, response, feedback)
```

### 7.5 监控 Fine-tuned 模型

```python
class FineTunedMonitor:
    """监控微调模型的关键指标"""
    
    def monitor(self, model_name, request, response, ground_truth=None):
        metrics = {
            # 性能
            "latency_ms": response.latency_ms,
            "tokens_per_sec": response.tokens / response.duration,
            
            # 业务
            "user_accepted": response.user_accepted,
            "user_regenerated": response.user_regenerated,
            
            # 与 base 模型对比
            "improvement_vs_base": self.compare_with_base(request, response),
            
            # 漂移检测
            "output_distribution_shift": self.detect_drift(model_name, response),
        }
        
        # 自动告警
        if metrics["output_distribution_shift"] > 0.1:
            self.alert(f"Model {model_name} output distribution shifted")
        
        return metrics
```

---

## 八、个性化路由

### 8.1 个性化的层次

| 层次 | 描述 | 技术 |
|---|---|---|
| **用户级** | 同一个问题，不同用户看到不同答案 | 用户画像 / 历史 |
| **租户级** | B 租户的模型 vs C 租户 | 租户配置 |
| **场景级** | 客服场景用模型 A，代码场景用模型 B | 任务分类 |
| **时段级** | 白天用快模型，深夜用强模型 | 时段配置 |

### 8.2 用户级个性化

```python
class PersonalizedRouter:
    def __init__(self, user_profiles):
        self.profiles = user_profiles
    
    def select_model(self, user_id, request):
        profile = self.profiles[user_id]
        
        # 1. 用户的偏好（喜欢哪种回答风格）
        if profile.prefers == "concise":
            return "gpt-4o-mini"  # 已经够好
        
        # 2. 用户的专业度
        if profile.expertise == "expert":
            return "claude-opus"  # 强模型
        
        # 3. 用户的语言
        if profile.language == "zh":
            return "qwen-max"  # 中文好
        
        # 4. 用户的历史任务
        if profile.frequent_task == "code":
            return "code-assistant-v3"  # 微调
        
        return "gpt-4o"  # 默认
```

### 8.3 租户级个性化

```python
TENANT_MODEL_MAPPING = {
    "tenant-A": {
        "primary": "gpt-4o",
        "fallback": "claude-sonnet",
        "fine_tuned": "tenant-A-finetuned-v1",
        "rate_limit": 1000,  # rpm
    },
    "tenant-B": {
        "primary": "qwen-max",  # 国内便宜
        "fallback": "deepseek-v3",
        "fine_tuned": None,
        "rate_limit": 100,
    }
}

def route_by_tenant(request, tenant_id):
    config = TENANT_MODEL_MAPPING[tenant_id]
    return config["primary"]
```

### 8.4 场景级个性化

```python
# 业务场景 → 模型
SCENARIO_MODEL_MAPPING = {
    "code_generation": "code-assistant-v3",
    "code_review": "code-review-v1",
    "customer_support": "customer-support-v1",
    "creative_writing": "claude-opus",
    "data_analysis": "gpt-4o",
    "translation": "gpt-4o-mini",
    "summarization": "gpt-4o-mini",
}

def route_by_scenario(request, scenario):
    return SCENARIO_MODEL_MAPPING.get(scenario, "gpt-4o")
```

### 8.5 自适应个性化

```python
class AdaptivePersonalizer:
    """基于用户反馈自适应调整路由"""
    
    def __init__(self):
        self.user_model_perf = defaultdict(lambda: defaultdict(list))
    
    def route(self, user_id, request, scenario):
        # 1. 历史性能最好的模型
        if self.user_model_perf[user_id]:
            best = max(
                self.user_model_perf[user_id].items(),
                key=lambda x: sum(x[1]) / len(x[1])
            )
            return best[0]
        
        # 2. 默认
        return SCENARIO_MODEL_MAPPING[scenario]
    
    def record_feedback(self, user_id, model, feedback_score):
        self.user_model_perf[user_id][model].append(feedback_score)
```

---

## 九、个性化 RAG 与 Memory

### 9.1 个性化 RAG

```
用户问题
    ↓
[个性化 Query 改写]
    - 加入用户历史
    - 加入用户偏好
    ↓
[个性化检索]
    - 用户专属知识库
    - 用户权限过滤
    ↓
[个性化 Prompt]
    - 系统提示加入用户信息
    ↓
[LLM]
    ↓
[个性化答案]
    - 风格符合用户偏好
    - 引用用户相关数据
```

### 9.2 Memory 系统

```python
class UserMemory:
    def __init__(self, user_id, memory_store):
        self.user_id = user_id
        self.store = memory_store
    
    async def get_relevant_memories(self, query, top_k=5):
        """检索与当前 query 相关的用户记忆"""
        query_emb = embed(query)
        memories = await self.store.search(
            user_id=self.user_id,
            query_emb=query_emb,
            top_k=top_k
        )
        return memories
    
    async def add_memory(self, memory):
        """添加新记忆"""
        await self.store.add(user_id=self.user_id, memory=memory)
```

### 9.3 网关的 Memory 集成

```python
class GatewayWithMemory:
    async def process(self, request, user_context):
        # 1. 检索用户相关记忆
        memories = await self.memory.get_relevant_memories(
            user_id=user_context.user_id,
            query=request.messages[-1].content
        )
        
        # 2. 构造个性化 prompt
        system_message = self._build_system_message(
            user_context=user_context,
            memories=memories
        )
        
        # 3. 调用 LLM
        response = await self.llm.generate(
            messages=[system_message] + request.messages
        )
        
        # 4. 更新记忆
        await self.memory.add_memory(
            user_id=user_context.user_id,
            memory=extract_memory(request, response)
        )
        
        return response
```

### 9.4 长上下文 vs Memory

| 方案 | 适用 |
|---|---|
| **长上下文（128K-1M）** | 短期任务、文档分析 |
| **Memory 系统** | 长期、跨会话 |

**最佳实践**：短期用上下文，长期用 Memory。

---

## 十、评估与监控 Fine-tuned 模型

### 10.1 评估指标

| 类别 | 指标 |
|---|---|
| **基础能力** | MMLU, ARC, HellaSwag |
| **任务能力** | HumanEval, GSM8K, BBH |
| **业务能力** | 自定义评测集 |
| **人类偏好** | 用户反馈、ELO |
| **安全** | 注入抵抗、有害内容率 |

### 10.2 自动化评估

```python
class FineTunedEvaluator:
    def __init__(self, eval_dataset):
        self.dataset = eval_dataset
        self.judge = "gpt-4o"
    
    async def evaluate(self, model):
        results = []
        for item in self.dataset:
            response = await model.generate(item["input"])
            
            metrics = {
                "task_accuracy": await self.check_accuracy(
                    item["expected_output"], 
                    response
                ),
                "style_match": await self.check_style(
                    item.get("expected_style", "default"),
                    response
                ),
                "format_correct": self.check_format(response),
                "factual": await self.check_factual(item["context"], response),
            }
            
            results.append(metrics)
        
        return self.aggregate(results)
```

### 10.3 A/B 测试方法

```python
class FineTuneABTest:
    def __init__(self, model_a, model_b, traffic_split=0.5):
        self.model_a = model_a
        self.model_b = model_b
        self.split = traffic_split
        self.metrics_a = []
        self.metrics_b = []
    
    async def route(self, user_id, request):
        if hash(user_id) % 100 < self.split * 100:
            response = await self.model_a.generate(request)
            self.metrics_a.append(self.score(response, request))
            return response, "A"
        else:
            response = await self.model_b.generate(request)
            self.metrics_b.append(self.score(response, request))
            return response, "B"
    
    def analyze(self):
        return {
            "A": self.summarize(self.metrics_a),
            "B": self.summarize(self.metrics_b),
            "winner": "A" if self.avg(self.metrics_a) > self.avg(self.metrics_b) else "B"
        }
```

### 10.4 漂移检测

```python
class ModelDriftDetector:
    """检测微调模型的输出分布变化"""
    
    def __init__(self, baseline_distribution):
        self.baseline = baseline_distribution
    
    def detect(self, recent_outputs):
        # 计算 KL 散度
        current_dist = self.compute_distribution(recent_outputs)
        kl_div = kl_divergence(self.baseline, current_dist)
        
        if kl_div > 0.1:
            return "DRIFT_DETECTED"
        return "OK"
    
    def compute_distribution(self, outputs):
        # 用 embedding 聚类 / 输出长度 / 词汇分布
        ...
```

---

## 十一、未解难题与研究前沿

### 11.1 微调技术

1. **微调 vs RAG** 的最优决策
2. **Few-shot 微调**（< 100 样本）的极限
3. **持续学习**——避免灾难性遗忘
4. **多任务微调**——如何不互相干扰
5. **人类反馈的高效收集**

### 11.2 数据

6. **数据质量评估**——如何自动评估
7. **合成数据的边界**——能替代真实数据吗
8. **数据隐私**——微调时如何保护
9. **数据版本管理**
10. **数据不平衡**的解决

### 11.3 部署

11. **多 LoRA 高效切换**——千个 adapter 怎么管
12. **微调模型的热更新**
13. **基础模型升级时微调模型的迁移**
14. **分布式微调模型**的统一调度
15. **A/B 测试**的统计显著性

### 11.4 个性化

16. **用户级个性化**的隐私问题
17. **个性化 vs 公平性** 的权衡
18. **冷启动用户**的个性化
19. **个性化效果** 的归因
20. **跨设备、跨场景**的个性化连续性

### 11.5 评估

21. **微调后能力保留**——MMLU 等下降问题
22. **领域过拟合**的检测
23. **与基础模型**的合理对比
24. **在线评估的统计方法**
25. **离线-在线评估的差距**

### 11.6 未来

26. **自我微调**（Self-Tuning）
27. **联邦微调**（保护隐私）
28. **在线学习**的微调
29. **AI 网关作为微调编排器**
30. **微调的最终形态**

---

## 十二、参考资料

### 12.1 论文

- "LoRA: Low-Rank Adaptation of Large Language Models" (Microsoft, 2021)
- "QLoRA: Efficient Finetuning of Quantized LLMs" (Dettmers et al., 2023)
- "DPO: Direct Preference Optimization" (Rafailov et al., 2023)
- "PEFT: State-of-the-art Parameter-Efficient Fine-tuning" (HuggingFace)
- "Instruction Tuning" 系列
- "RLHF" 系列

### 12.2 框架

- github.com/huggingface/peft
- github.com/huggingface/trl
- github.com/hiyouga/LLaMA-Factory
- github.com/unslothai/unsloth
- github.com/axolotl-ai-cloud/axolotl
- github.com/modelscope/swift

### 12.3 平台

- OpenAI Fine-tuning
- Anthropic Console
- Google Vertex AI Tuning
- AWS SageMaker
- Azure OpenAI Fine-tuning
- Together AI
- Anyscale

### 12.4 评测

- OpenAI Evals
- HuggingFace Evaluate
- RAGAS
- TruLens
- LangSmith

### 12.5 关键博客

- HuggingFace "PEFT 文档"
- OpenAI "Fine-tuning 指南"
- Anthropic "Claude fine-tuning"
- Sebastian Raschka "LLM training"
- "LoRA 实战"系列

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 批 · 第 8 篇
- 主题：Fine-tuning 与个性化网关
- 上一份：17-rag-gateway-optimization.md
- 下一份预告：AI 网关的 SLA 与服务治理
