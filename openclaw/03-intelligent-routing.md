# 智能路由：决策算法演进与研究前沿

> 系列：AI Gateway 持续深挖 · 第 3 篇
> 性质：纯技术研究
> 范围：从静态路由到 LLM-as-a-Router 的完整算法谱系

---

## 目录

- [一、什么是 LLM 场景的"智能路由"](#一什么是-llm-场景的智能路由)
- [二、路由策略谱系](#二路由策略谱系)
- [三、传统路由策略详解](#三传统路由策略详解)
- [四、基于规则的路由](#四基于规则的路由)
- [五、基于代价函数的路由](#五基于代价函数的路由)
- [六、基于分类的路由](#六基于分类的路由)
- [七、基于强化学习的路由](#七基于强化学习的路由)
- [八、LLM-as-a-Router](#八llm-as-a-router)
- [九、关键算法详解](#九关键算法详解)
- [十、Cascade 路由](#十cascade-路由)
- [十一、Mixture-of-Experts 视角](#十一mixture-of-experts-视角)
- [十二、评估方法论](#十二评估方法论)
- [十三、未解难题与研究前沿](#十三未解难题与研究前沿)
- [十四、参考资料](#十四参考资料)

---

## 一、什么是 LLM 场景的"智能路由"

### 1.1 定义

**LLM 智能路由** = 在多个可用 LLM 之间，为当前请求选择**最优模型**的过程。"最优"是多目标的：
- 质量（任务完成度）
- 成本（token 费用）
- 延迟（首 token 时间、P99）
- 可靠性（fallback 成功率）
- 能力匹配（是否擅长此类任务）

### 1.2 为什么这个问题重要

- **经济性**：便宜模型（DeepSeek/GPT-4o-mini）vs 贵模型（GPT-4o/Claude Opus）成本差 10-100x
- **能力差异**：不同模型在不同任务上表现差异巨大
- **SLA 保障**：高可用需要 fallback
- **合规**：不同地区/合规要求用不同模型

### 1.3 与传统负载均衡的差异

| 维度 | 传统 LB | LLM 智能路由 |
|---|---|---|
| 决策粒度 | 请求级 | 请求级 / token 级 |
| 输入特征 | URL / header | prompt 内容 |
| 目标 | 资源利用率 | 质量 + 成本 + 延迟 |
| 反馈信号 | RT / 错误率 | 用户反馈 / 任务成功率 |
| 决策延迟 | < 1ms | 1-100ms |

---

## 二、路由策略谱系

```
L1 ── 静态路由（按 model 字段）
        │
L2 ── A/B 测试（按比例分流）
        │
L3 ── Fallback 链（失败切下一个）
        │
L4 ── 负载均衡（多 key 轮询）
        │
L5 ── 成本优先（选最便宜的）
        │
L6 ── 延迟优先（选 P99 最优）
        │
L7 ── 能力路由（按任务类型）
        │
L8 ── 智能路由（query 分类 + 模型选择）
        │
L9 ── Cascade（先小模型，不行再大模型）
        │
L10 ─ LLM-as-a-Router（用 LLM 决策）
        │
L11 ─ RL 路由（强化学习优化）
        │
L12 ─ 个性化路由（按用户偏好学习）
```

---

## 三、传统路由策略详解

### 3.1 静态路由

```python
def route_static(request):
    return request.model  # 用户指定啥就用啥
```

**适用**：用户已经知道要什么模型
**局限**：需要用户理解模型差异

### 3.2 A/B 测试

```python
def route_ab(request, ratio=0.5):
    if hash(request.user_id) % 100 < ratio * 100:
        return "gpt-4o"
    else:
        return "claude-sonnet"
```

**适用**：评估新模型 / 新 prompt
**局限**：50% 流量要承担次优结果的成本

### 3.3 Fallback 链

```python
def route_fallback(request, primary="gpt-4o", fallbacks=["claude-sonnet", "gpt-4o-mini"]):
    try:
        return call(request, primary)
    except (Timeout, RateLimit, Error):
        for fb in fallbacks:
            try:
                return call(request, fb)
            except (Timeout, RateLimit, Error):
                continue
    raise AllFailedError()
```

**适用**：保障可用性
**局限**：不优化成本、可能掩盖问题

### 3.4 负载均衡

```python
def route_load_balance(request, keys):
    # 多种策略：round-robin, weighted, least-busy
    key = select_key(keys, strategy="least-busy")
    return call(request, key)
```

**适用**：多账号轮询、规避 rate limit
**局限**：仍然是按"账号"分，不按"任务"分

---

## 四、基于规则的路由

### 4.1 简单规则

```python
def route_by_rules(request):
    if "code" in request.messages[-1].content.lower():
        return "deepseek-coder"  # 代码用 DeepSeek
    if is_english(request):
        return "gpt-4o-mini"
    if is_chinese(request):
        return "qwen-max"
    return "gpt-4o"  # 默认
```

**适用**：业务规则清晰、prompt 模式可识别
**局限**：规则爆炸、边界 case 难处理

### 4.2 元数据驱动

```python
def route_by_metadata(request):
    if request.metadata.get("priority") == "high":
        return "gpt-4o"
    if request.metadata.get("cost_center") == "marketing":
        return "gpt-4o-mini"  # 营销部门限制成本
    return "gpt-4o"
```

**适用**：组织内有明确的成本/优先级规则
**局限**：依赖上游打 metadata

---

## 五、基于代价函数的路由

### 5.1 思想

定义一个**代价函数** = α × 质量 - β × 成本 - γ × 延迟

每次请求选代价函数值最低的模型。

### 5.2 简单实现

```python
def route_by_cost(request, models):
    candidates = []
    for m in models:
        # 估算该请求在模型 m 上的代价
        cost = estimate_cost(request, m)  # token 数 × 单价
        quality = model_quality_db[m]     # 历史质量分
        latency = model_latency_db[m]     # P50
        score = -1 * cost + 2 * quality - 0.5 * latency
        candidates.append((m, score))
    return max(candidates, key=lambda x: x[1])[0]
```

### 5.3 关键挑战

- **α/β/γ 权重怎么设？**——业务相关
- **质量怎么量化？**——需要离线评测集
- **延迟怎么估？**——动态变化
- **token 数怎么估？**——prompt 长度 + 预估输出

### 5.4 工程实现

```python
class CostFunctionRouter:
    def __init__(self, weights, quality_db, latency_db, pricing_db):
        self.weights = weights
        self.quality_db = quality_db
        self.latency_db = latency_db
        self.pricing_db = pricing_db
    
    def route(self, request):
        scores = {}
        for model in self.available_models:
            quality = self.quality_db[model]["task_avg"]
            cost = self._estimate_cost(request, model)
            latency = self.latency_db[model]["p50"]
            
            score = (
                self.weights["alpha"] * quality
                - self.weights["beta"] * cost
                - self.weights["gamma"] * latency
            )
            scores[model] = score
        
        return max(scores, key=scores.get)
```

---

## 六、基于分类的路由

### 6.1 思想

把"路由选择"分解为两步：
1. **分类**：这条 query 属于哪类任务？（代码、翻译、摘要、对话……）
2. **选择**：该类任务的"最优模型"是哪个？

### 6.2 任务分类器实现

```python
# 方案 A：规则分类
def classify_task(query):
    if has_code_blocks(query):
        return "code"
    if is_translation_request(query):
        return "translation"
    if is_summarization(query):
        return "summarization"
    return "general"

# 方案 B：小模型分类
from transformers import pipeline
classifier = pipeline("zero-shot-classification", 
                       model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0")

def classify_task_ml(query):
    labels = ["code", "translation", "summarization", "qa", "creative"]
    result = classifier(query, candidate_labels=labels)
    return result["labels"][0]

# 方案 C：LLM 分类
def classify_task_llm(query):
    prompt = f"""Classify this query into one of: code, translation, summarization, qa, creative.
    Query: {query}
    Category:"""
    return call_llm(prompt, model="gpt-4o-mini", max_tokens=10)
```

### 6.3 模型选择表

```python
MODEL_SELECTION_TABLE = {
    "code": {
        "primary": "deepseek-coder",
        "fallback": "gpt-4o",
        "min_model": "gpt-4o-mini"
    },
    "translation": {
        "primary": "gpt-4o-mini",  # 翻译任务模型差异不大
        "fallback": "claude-haiku"
    },
    "summarization": {
        "primary": "gpt-4o-mini",
        "fallback": "claude-haiku"
    },
    "qa": {
        "primary": "gpt-4o",
        "fallback": "claude-sonnet"
    },
    "creative": {
        "primary": "claude-sonnet",  # 通常认为 Claude 更擅长创作
        "fallback": "gpt-4o"
    },
    "general": {
        "primary": "gpt-4o-mini",
        "fallback": "gpt-4o"
    }
}

def route_by_classification(request):
    task = classify_task_ml(request.messages[-1].content)
    config = MODEL_SELECTION_TABLE[task]
    return config["primary"]
```

### 6.4 挑战

- **分类器本身的成本**——小模型很快但要本地资源
- **类别边界模糊**——很多 query 多任务
- **新任务出现**——零样本分类能力要求高
- **类别与模型选择的耦合**——需要长期评测数据

---

## 七、基于强化学习的路由

### 7.1 思想

把路由问题建模为 **Contextual Bandit**：
- 每次请求 = 一个 step
- 模型选择 = action
- 反馈信号（用户接受/拒绝） = reward
- 学习最优 policy：π(model | query_features)

### 7.2 状态表示

```python
def extract_features(request):
    return {
        "query_length": len(request.messages[-1].content),
        "has_code": has_code(request.messages[-1].content),
        "language": detect_language(request.messages[-1].content),
        "time_of_day": datetime.now().hour,
        "user_tier": request.user_tier,  # 免费/付费
        "estimated_output_tokens": estimate_output_tokens(request),
    }
```

### 7.3 奖励设计

```python
def compute_reward(response, request, model):
    # 多目标加权
    quality = response.user_feedback or response.llm_judge_score or 0.5
    cost = -response.cost
    latency = -response.latency_ms / 1000
    
    reward = (
        0.6 * quality +
        0.3 * cost +     # 负成本（成本越低奖励越高）
        0.1 * latency
    )
    return reward
```

### 7.4 探索-利用

```python
def route_rl(request, policy, epsilon=0.1):
    if random.random() < epsilon:
        return random.choice(MODELS)  # 探索
    features = extract_features(request)
    return policy.predict(features)  # 利用
```

### 7.5 训练流水线

```
请求进来
    ↓
Policy 选择模型
    ↓
调用模型，返回响应
    ↓
收集反馈（用户/自动评估）
    ↓
更新 Policy
    ↓
Loop
```

### 7.6 挑战

- **冷启动**——新模型没有历史数据
- **反馈稀疏**——用户反馈很难收集
- **环境变化**——模型价格/能力都在变
- **探索成本**——探索阶段用错模型代价大

---

## 八、LLM-as-a-Router

### 8.1 思想

直接用一个 LLM 来做路由决策：

```python
def route_with_llm(request, available_models):
    router_prompt = f"""You are a model router. Based on the user query, choose the best model.

Available models:
- gpt-4o: Best for complex reasoning, code, math. $5/$15 per 1M tokens.
- gpt-4o-mini: Best for simple tasks, fast. $0.15/$0.60 per 1M tokens.
- claude-sonnet-4-5: Best for long context, analysis. $3/$15 per 1M tokens.
- deepseek-coder: Best for code. $0.14/$0.28 per 1M tokens.

User query: {request.messages[-1].content}

Respond with ONLY the model name."""

    return call_llm(router_prompt, model="gpt-4o-mini", max_tokens=20)
```

### 8.2 Few-shot 增强

```python
ROUTER_FEWSHOT = """
Examples:
Q: "Write a Python function to merge sorted lists"
A: deepseek-coder

Q: "Translate this Chinese email to English"
A: gpt-4o-mini

Q: "Analyze this 50-page legal contract"
A: claude-sonnet-4-5

Q: "What's the capital of France?"
A: gpt-4o-mini
"""
```

### 8.3 路由决策的"元 prompt"设计

```python
META_ROUTER_PROMPT = """You are an expert at routing user queries to language models.

You will be given:
- User query
- List of available models with capabilities and costs

Choose the model that best balances:
- Task completion quality
- Cost
- Latency

For simple queries (greetings, simple Q&A), use cheap fast models.
For complex tasks (code, analysis, long-form generation), use capable models.

Output JSON: {"model": "...", "reason": "..."}
"""
```

### 8.4 优势 vs 风险

| 优势 | 风险 |
|---|---|
| 不需要标注数据 | 路由决策本身要花钱 |
| 灵活、可解释 | 决策延迟（一次 LLM 调用） |
| 可以利用 LLM 的世界知识 | 路由 LLM 选错 → 雪上加霜 |
| 容易更新（改 prompt） | 难以离线评估 |

### 8.5 工程优化

#### 优化 1：小模型做决策

```python
# 用 7B/13B 本地模型做路由决策
# 成本接近 0，延迟 50-200ms
```

#### 优化 2：决策缓存

```python
# 相似 query 复用路由决策
if has_similar_cached_decision(query):
    return cached_decision
```

#### 优化 3：规则 fallback

```python
# 简单 query 走规则，复杂 query 才用 LLM
if is_simple(query):
    return "gpt-4o-mini"
return llm_route(query)
```

---

## 九、关键算法详解

### 9.1 FrugalGPT 算法

FrugalGPT（Stanford 2023）提出**级联调用**：

```python
def frugal_route(query, model_ladder):
    for model in model_ladder:
        response = call(model, query)
        if confidence_is_high(response):
            return response
    return model_ladder[-1]  # 最后兜底用最强模型
```

**关键**：怎么判断"置信度"？
- 多模型一致 → 高置信
- 单 token 概率熵低 → 高置信
- 自我评估（让模型说"我对这个答案有 80% 信心"）

### 9.2 RouterBench

**RouterBench**（2024）系统评测了 12+ 路由策略在多个 LLM 上的表现：

| 策略 | 平均成本节省 | 质量保持 |
|---|---|---|
| Always GPT-4 | 0% | 100% |
| Always GPT-3.5 | 85% | -15% |
| Random | 40% | -5% |
| KNN Router | 50% | -3% |
| Linear Router | 55% | -3% |
| MLP Router | 60% | -2% |
| Oracle | 70% | 0% |

**Oracle**（知道正确答案）才 70% 节省——给所有路由策略留了很大空间。

### 9.3 AutoMix

**AutoMix**（2023）：
1. 小模型先答
2. 用 LLM 验证（小模型答案对不对）
3. 不对就升级到大模型
4. 适合"难易差异大"的场景

### 9.4 HybridLLM

**HybridLLM**（2023）：
- 在路由前用**一个 verifier 模型**判断"小模型能不能答"
- 验证通过 → 走小模型
- 不通过 → 走大模型
- 关键创新：verifier 是单独训练的

### 9.5 RouteLLM

**RouteLLM**（2024，MIT）：
- 用公开的 Chatbot Arena 数据训练路由模型
- 4B 参数的 router 模型
- 能复现 GPT-4 95% 的质量，成本降 85%

### 9.6 ZOOT

**ZOOT**（2024）：
- 用 reward model 做路由
- 每个 query 跑一遍所有候选模型（小规模）
- 用 reward 排序
- 成本反而更高（因为要先全部跑）

---

## 十、Cascade 路由

### 10.1 思想

从便宜到贵依次尝试，**够用就停**：

```
GPT-4o-mini  →  不自信？  →  GPT-4o
                              →  不自信？  →  Claude Opus
```

### 10.2 实现

```python
def cascade_route(request, models, confidence_threshold=0.8):
    for model in models:
        response = call(model, request)
        confidence = estimate_confidence(response, model)
        if confidence > confidence_threshold:
            response.model_used = model
            return response
    # 全部不满意，返回最后一个
    return response
```

### 10.3 置信度估计

#### 方法 1：Token 概率熵

```python
def confidence_from_entropy(token_probs):
    # token 概率越集中，置信度越高
    entropy = -sum(p * log(p) for p in token_probs)
    return 1 / (1 + entropy)
```

#### 方法 2：自评估

```python
def confidence_self_eval(response, original_query):
    eval_prompt = f"""Rate your confidence in this answer (0-1):
    Query: {original_query}
    Answer: {response}
    Confidence:"""
    score = float(call_llm(eval_prompt, max_tokens=5).strip())
    return score
```

#### 方法 3：多模型一致性

```python
def confidence_consensus(responses):
    # 多个模型答案一致 → 高置信
    from collections import Counter
    most_common = Counter(responses).most_common(1)[0]
    return most_common[1] / len(responses)
```

### 10.4 挑战

- **置信度估计本身不可靠**——LLM 经常过度自信
- **小模型误自信**——错得很自信
- **大模型不自信**——能答对的反而说"我不行"

---

## 十一、Mixture-of-Experts 视角

### 11.1 MoE 与路由的关系

| 维度 | MoE（模型内） | 智能路由（模型间） |
|---|---|---|
| 粒度 | token 级 | 请求级 |
| Experts | 模型内的 FFN | 多个 LLM |
| 路由器 | 学习的 gating network | 策略函数 |
| 训练 | 端到端 | 离线 + 在线 |

### 11.2 思想实验

如果把所有 LLM 看作"experts"：
- 路由器 = 模型选择策略
- 专家 = 不同 LLM
- 训练 = 用反馈信号优化路由

这就是 **"LLM MoE"** 的概念——但用 LLM 代替 FFN。

### 11.3 研究方向

- **跨模型 MoE**：不同 LLM 作为 expert，路由器动态选择
- **跨厂商 MoE**：商业模型 + 开源模型混合
- **跨模态 MoE**：文本 / 图像 / 语音 expert 混合

---

## 十二、评估方法论

### 12.1 评估指标

#### 离线指标

| 指标 | 含义 |
|---|---|
| **质量分** | 与 GPT-4 参考答案的相似度 / 人类评分 |
| **成本** | 总 token 费用 / 节省率 |
| **延迟** | P50 / P99 |
| **任务成功率** | 业务指标（如代码编译通过率） |

#### 在线指标

| 指标 | 含义 |
|---|---|
| **用户接受率** | 用户没有重新生成的比例 |
| **任务完成率** | 用户最终完成任务的比率 |
| **投诉率** | 用户投诉 / 总请求 |
| **A/B 测试指标** | 业务核心指标（转化、留存） |

### 12.2 评测集设计

```
评测集 =
    真实流量采样（1000+ 条）
    + 任务类型分布对齐
    + 多模型参考答案
    + 人工评分
```

### 12.3 RouterBench 评测框架

RouterBench 提供：
- 8 个数据集（crossfit、RAFT 等）
- 12 个模型（包括 GPT-4、Claude、Llama、Mistral）
- 标准评测脚本
- 路由策略 baseline

### 12.4 评估陷阱

- **评测集不代表真实流量**——分布偏移
- **LLM-as-Judge 偏差**——偏好自己
- **A/B 测试流量小**——统计显著性不足
- **线上效果与离线差异大**——用户行为改变

---

## 十三、未解难题与研究前沿

### 13.1 决策质量

1. **是否存在"最优路由策略"？**——还是必然业务相关
2. **LLM-as-a-Router 能否超越学习式路由？**
3. **Cascade 路由的置信度估计**如何做得更准？
4. **多轮对话的路由**——历史轮次要不要参与决策？

### 13.2 决策成本

5. **路由决策本身的花销**——何时应该关闭智能路由？
6. **小模型路由 vs LLM 路由**的边界？
7. **决策缓存的命中率提升空间**？

### 13.3 反馈信号

8. **稀疏反馈下的路由学习**——怎么减少对显式反馈的依赖？
9. **隐式反馈信号**（用户停留时间、重新生成率）的有效性？
10. **LLM-as-Judge** 是否会被路由 LLM "串通"？

### 13.4 个性化

11. **按用户偏好学习路由**——技术可行但隐私问题
12. **跨用户的路由策略迁移**——什么样的策略可迁移？
13. **组织级 vs 用户级**的路由优化冲突？

### 13.5 鲁棒性

14. **路由决策被攻击**——恶意 query 强制选最贵模型
15. **路由策略对抗样本**——prompt 注入让路由选错
16. **模型故障检测**——上游模型"沉默失败"怎么办？
17. **路由决策的回放能力**——可解释路由的标准化

### 13.6 标准化

18. **路由策略的 benchmark 标准化**？
19. **路由决策日志的标准格式**（OpenLLMetry 是否覆盖）？
20. **路由元数据**（为什么选这个模型）的可观测标准？

### 13.7 新范式

21. **多模态路由**——图像 query 走哪条路径？
22. **Agent 多步调用的路由**——每步独立还是全局？
23. **联邦路由**——跨组织共享路由经验？
24. **基于世界模型的路由**——预测 query 走向再选模型
25. **博弈论视角的路由**——多智能体协作

---

## 十四、参考资料

### 14.1 必读论文

- **FrugalGPT** (Chen et al., 2023) - 级联调用
- **RouterBench** (Hu et al., 2024) - 路由评测基准
- **AutoMix** (Madaan et al., 2023) - 自我验证 cascade
- **HybridLLM** (Ding et al., 2023) - 验证器路由
- **RouteLLM** (Ong et al., 2024) - 训练式路由
- **ZOOT** (Lu et al., 2024) - Reward model 路由
- **Tryage** (Hari & Thomson, 2023) - 个性化路由
- **LLM-Blender** (Jiang et al., 2023) - 多模型集成

### 14.2 工业实践

- Not Diamond 博客
- Unify.ai 技术博客
- Martian 模型转换
- OpenRouter 路由策略
- Together AI 路由

### 14.3 项目

- github.com/lm-sys/RouteLLM
- github.com/withmartian/router
- github.com/notdiamond/notdiamond

### 14.4 评测基准

- RouterBench (github.com/withmartian/routerbench)
- Chatbot Arena (lmarena.ai)
- OpenLLM Leaderboard
- AlpacaEval

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 3 篇
- 主题：智能路由
- 上一份：02-semantic-cache.md
- 下一份预告：可观测 / OpenLLMetry 标准深入
