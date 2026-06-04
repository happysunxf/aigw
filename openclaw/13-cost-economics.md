# AI 网关的成本经济学：单位经济、定价、ROI

> 系列：AI Gateway 持续深挖 · 第 2 批 · 第 3 篇
> 性质：纯技术研究
> 范围：AI Gateway 的成本结构、单位经济、定价模型、ROI 测算、成本优化

---

## 目录

- [一、AI 网关的"双层成本"结构](#一ai-网关的双层成本结构)
- [二、Token 价格基础](#二token-价格基础)
- [三、成本模型详解](#三成本模型详解)
- [四、单次请求成本计算](#四单次请求成本计算)
- [五、成本归因](#五成本归因)
- [六、成本预测与预算](#六成本预测与预算)
- [七、成本优化技术](#七成本优化技术)
- [八、定价模型与商业模式](#八定价模型与商业模式)
- [九、ROI 测算方法](#九roi-测算方法)
- [十、成本治理与告警](#十成本治理与告警)
- [十一、行业基准与对标](#十一行业基准与对标)
- [十二、未解难题与研究前沿](#十二未解难题与研究前沿)
- [十三、参考资料](#十三参考资料)

---

## 一、AI 网关的"双层成本"结构

### 1.1 AI Gateway 同时承担两种成本视角

| 视角 | 关心什么 | 角色 |
|---|---|---|
| **作为使用者** | 我用 LLM 花多少钱？ | 网关暴露给上层业务 |
| **作为运营者** | 我运营网关花多少钱？ | 网关自身成本 |

两个视角**完全独立**，但很多团队混淆。

### 1.2 两种成本的具体组成

#### 视角 A：使用者（业务方关心）

```
总成本 = Σ 请求成本
      = Σ (prompt_tokens × prompt_price + completion_tokens × completion_price)
      + 工具调用成本
      + Agent 多步调用累计
      + 缓存未命中成本
      + Fallback 额外成本
```

#### 视角 B：运营者（网关自身成本）

```
总成本 = 云资源 + 人力 + 第三方服务
云资源 = 计算 + 存储 + 网络
人力 = 研发 + 运维 + 客户支持
第三方 = 可观测 SaaS + 鉴权服务 + 邮件服务
```

### 1.3 本篇报告主要视角

**主要**：视角 A —— **AI Gateway 帮助业务方理解、预测、优化 LLM 使用成本**  
**次要**：视角 B —— **AI Gateway 公司自身的商业可持续性**

---

## 二、Token 价格基础

### 2.1 主要模型价格（2025 行业水平）

| 模型 | 输入 ($/1M) | 输出 ($/1M) | 比例 |
|---|---|---|---|
| **GPT-4o** | 5.00 | 15.00 | 1:3 |
| **GPT-4o-mini** | 0.15 | 0.60 | 1:4 |
| **Claude Sonnet 4.5** | 3.00 | 15.00 | 1:5 |
| **Claude Haiku** | 0.80 | 4.00 | 1:5 |
| **Gemini 1.5 Pro** | 1.25-2.50 | 5.00-10.00 | 1:4 |
| **Gemini Flash** | 0.075 | 0.30 | 1:4 |
| **DeepSeek V3** | 0.14 | 0.28 | 1:2 |
| **Qwen Max** | 0.40 | 1.20 | 1:3 |
| **Llama 3.1 70B (自托管)** | ~0.50 | ~0.50 | 1:1 |

**观察**：
- 输出 token 比输入贵 3-5x
- 旗舰模型 vs 廉价模型差 50-100x
- 自托管价格主要由 GPU 摊销决定

### 2.2 Token 计费单位

```
1 token ≈ 0.75 英文单词 ≈ 4 字符
1 token ≈ 1.5 中文字符

1 块代码（10 行） ≈ 200-500 tokens
1 张 A4 文档 ≈ 1000-2000 tokens
1 本书 ≈ 100k-200k tokens
```

### 2.3 多模态 token 计算

| 模态 | Token 计算 |
|---|---|
| **文本** | 字符 / 4 |
| **图像** | 按 tile：512x512 ≈ 170 tokens，1024x1024 ≈ 765 |
| **音频** | 1 秒 ≈ 50-100 tokens |
| **视频** | 抽帧数 × 单帧 token + 音频 token |

**多模态可能比文本贵 100-1000x**。

### 2.4 缓存折扣

| 提供方 | 缓存折扣 |
|---|---|
| **OpenAI** | 提示词缓存命中 50% off |
| **Anthropic** | 缓存写入 25% 溢价，命中 90% off |
| **Gemini** | 上下文缓存 50-90% off |

---

## 三、成本模型详解

### 3.1 单次请求成本公式

```python
def request_cost(request, response, model_pricing):
    cost = 0
    
    # 输入 token
    cost += request.input_tokens * model_pricing.input_price / 1_000_000
    
    # 输出 token
    cost += response.output_tokens * model_pricing.output_price / 1_000_000
    
    # 工具调用
    for tool_call in response.tool_calls:
        cost += tool_call.cost  # 工具自身可能收费
    
    # 缓存命中折扣
    if response.cache_hit:
        cost *= 0.5  # 50% off
    
    # 微调模型溢价
    if model_pricing.is_finetuned:
        cost *= 1.5
    
    return cost
```

### 3.2 多步 Agent 成本

```python
def agent_task_cost(steps, model_pricing):
    total = 0
    for step in steps:
        step_cost = (
            step.input_tokens * model_pricing.input_price +
            step.output_tokens * model_pricing.output_price
        ) / 1_000_000
        # 工具调用
        for tool in step.tool_calls:
            step_cost += tool.cost
        total += step_cost
    return total
```

**现实**：
- 简单 Chat：$0.001 - $0.01
- RAG：$0.01 - $0.10
- 单 Agent：$0.05 - $1.00
- 多 Agent 复杂任务：$1.00 - $10.00

### 3.3 月度成本估算

```
月度成本 = 日活用户 × 人均请求数 × 单请求成本

例子：
  DAU = 10,000
  人均请求 = 5
  单请求 = $0.02
  → 月度 = 10,000 × 5 × 30 × $0.02 = $30,000
```

**关键变量**：
- DAU（用户量）
- 人均请求数（黏性）
- 单请求成本（效率）

### 3.4 成本驱动因素

| 因素 | 影响 | 优化空间 |
|---|---|---|
| **模型选择** | 5-100x | 高 |
| **Prompt 长度** | 1-10x | 高 |
| **输出长度** | 3-5x | 中 |
| **缓存命中率** | 1-5x | 高 |
| **路由策略** | 1-3x | 高 |
| **工具调用** | 0.1-2x | 中 |
| **Agent 步数** | 1-50x | 高 |

---

## 四、单次请求成本计算

### 4.1 网关层成本计算器

```python
class CostCalculator:
    def __init__(self, model_pricing_db):
        self.pricing = model_pricing_db
    
    def calculate(self, request, response):
        model = request.model
        pricing = self.pricing[model]
        
        # Token 计数
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        # 基础成本
        input_cost = input_tokens * pricing.input_price / 1_000_000
        output_cost = output_tokens * pricing.output_price / 1_000_000
        base_cost = input_cost + output_cost
        
        # 缓存折扣
        cache_discount = 0
        if response.cache_hit:
            if response.cache_type == "exact":
                cache_discount = base_cost * 0.5
            elif response.cache_type == "semantic":
                cache_discount = base_cost * 0.3
            elif response.cache_type == "prompt_caching":
                cache_discount = base_cost * 0.9  # Anthropic 90% off
        
        # 工具调用
        tool_cost = sum(t.cost for t in response.tool_calls)
        
        # 实际成本
        actual_cost = base_cost - cache_discount + tool_cost
        
        return CostBreakdown(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            base_cost=base_cost,
            cache_discount=cache_discount,
            tool_cost=tool_cost,
            actual_cost=actual_cost
        )
```

### 4.2 成本元数据附加到响应

```python
# 网关在响应 header 里加成本信息
response.headers["X-Cost-USD"] = "0.0123"
response.headers["X-Cost-Breakdown"] = json.dumps({
    "input_tokens": 200,
    "output_tokens": 500,
    "input_cost": 0.001,
    "output_cost": 0.0075,
    "cache_discount": 0.0,
    "total_cost": 0.0085
})
```

### 4.3 流式响应的成本

```python
# 流式响应中，token 数不完整（结束才知道）
# 网关需要：
# 1. 预估（基于流速）
# 2. 流结束后精确计算
# 3. 增量更新

async def stream_with_cost(generator):
    accumulated_tokens = 0
    async for chunk in generator:
        accumulated_tokens += chunk.usage_tokens if chunk.usage else 0
        chunk.cost_so_far = accumulated_tokens * PRICE / 1_000_000
        yield chunk
```

---

## 五、成本归因

### 5.1 归因维度

```
总成本 $10,000/月
├── 按用户：user-1 ($500), user-2 ($200), ...
├── 按租户：tenant-A ($6,000), tenant-B ($3,000), ...
├── 按团队：team-1 ($4,000), team-2 ($2,000), ...
├── 按项目：project-X ($3,000), project-Y ($1,000), ...
├── 按应用：app-1 ($5,000), app-2 ($3,000), ...
├── 按模型：gpt-4o ($7,000), claude-sonnet ($2,000), ...
├── 按功能：chat ($4,000), RAG ($3,000), Agent ($3,000)
└── 按时间段：工作日 vs 周末
```

### 5.2 实现

```python
class CostAttributor:
    def __init__(self, storage):
        self.storage = storage  # ClickHouse / BigQuery
    
    def record(self, request, response, cost, context):
        # context 包含所有归因维度
        self.storage.insert({
            "timestamp": time.time(),
            "user_id": context.get("user_id"),
            "tenant_id": context.get("tenant_id"),
            "team_id": context.get("team_id"),
            "project_id": context.get("project_id"),
            "app_id": context.get("app_id"),
            "model": request.model,
            "feature": context.get("feature", "unknown"),
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "cost_usd": cost.actual_cost,
        })
    
    def query_cost_by(self, dimension, time_range):
        sql = f"""
        SELECT {dimension}, SUM(cost_usd) as total
        FROM costs
        WHERE timestamp BETWEEN ? AND ?
        GROUP BY {dimension}
        ORDER BY total DESC
        """
        return self.storage.query(sql, time_range)
```

### 5.3 成本看板

```
┌──────────────────────────────────────────────┐
│  本月总成本：$10,234                          │
│  较上月：+12% 📈                              │
│  预算：$15,000（使用 68%）                    │
├──────────────────────────────────────────────┤
│  按部门                                       │
│  ├── 工程部   $4,500 (44%)                   │
│  ├── 运营部   $2,800 (27%)                   │
│  ├── 市场部   $1,500 (15%)                   │
│  └── 其他     $1,434 (14%)                   │
├──────────────────────────────────────────────┤
│  按模型                                       │
│  ├── GPT-4o        $7,000 (68%)              │
│  ├── Claude Sonnet $2,000 (20%)              │
│  └── 其他          $1,234 (12%)              │
├──────────────────────────────────────────────┤
│  Top 10 高成本用户                            │
│  user-1   $500                               │
│  user-2   $300                               │
│  ...                                          │
└──────────────────────────────────────────────┘
```

### 5.4 跨租户成本隔离

```python
# 网关层强制：每租户独立成本统计
# 不允许一个租户的查询影响另一个租户的 quota

class TenantCostGuard:
    def __init__(self, redis):
        self.redis = redis
    
    def check_quota(self, tenant_id, monthly_quota_usd):
        # 查询本月累计
        current = self.redis.get(f"cost:{tenant_id}:{month}")
        if current and current + estimated_cost > monthly_quota_usd:
            raise QuotaExceededError()
    
    def deduct(self, tenant_id, cost):
        # 累加
        self.redis.incrbyfloat(f"cost:{tenant_id}:{month}", cost)
```

---

## 六、成本预测与预算

### 6.1 短期预测（天/周）

```python
class CostForecaster:
    def __init__(self, history_db):
        self.history = history_db
    
    def predict_next_day(self):
        # 取过去 7 天数据
        # 简单移动平均
        recent = self.history.query("timestamp > now() - 7d")
        avg = recent.cost_usd.mean()
        # 调整周末/工作日差异
        if datetime.now().weekday() < 5:  # 工作日
            return avg * 1.2
        return avg * 0.7
```

### 6.2 中期预测（月/季）

```python
def predict_monthly(growth_rate=0.2):
    # 假设线性增长
    current_daily = 1000
    return current_daily * 30 * (1 + growth_rate) ** 3
```

### 6.3 长期预测

考虑因素：
- 用户增长
- 模型价格变动
- 业务功能扩展
- 新模型替代

```python
def predict_yearly():
    # 多场景预测
    return {
        "conservative": base * 2,
        "expected": base * 4,
        "aggressive": base * 8
    }
```

### 6.4 预算管理

```python
class BudgetManager:
    def __init__(self, budgets):
        # 预算配置
        # {
        #   "monthly": {"global": 15000, "tenant:A": 5000},
        #   "daily": {"global": 500, "tenant:A": 200}
        # }
        self.budgets = budgets
    
    def check(self, dimension, key, period, current_usage, estimated_new):
        limit = self.budgets[period].get(f"{dimension}:{key}", float('inf'))
        if current_usage + estimated_new > limit:
            return "block", f"would exceed {period} budget"
        elif current_usage + estimated_new > limit * 0.8:
            return "warn", f"approaching {period} budget (80%)"
        return "allow", None
```

### 6.5 预算告警

```
[10% of budget]: 内部通知
[50% of budget]: 邮件给 Owner
[80% of budget]: Slack 告警 + 邮件
[100% of budget]: 拒绝 + 紧急通知
[120% of budget]: 暂停服务 + 升级
```

---

## 七、成本优化技术

### 7.1 优化维度 1：模型选择

```python
def optimize_model_selection(query):
    complexity = estimate_complexity(query)
    if complexity < 0.3:
        return "gpt-4o-mini"  # $0.15/$0.60
    elif complexity < 0.7:
        return "gpt-4o"  # $5/$15
    else:
        return "claude-opus"  # $15/$75
```

**效果**：平均节省 30-70%。

### 7.2 优化维度 2：Prompt 压缩

```python
def compress_prompt(prompt):
    # 1. 移除冗余空白
    prompt = re.sub(r'\s+', ' ', prompt).strip()
    # 2. 移除不必要的指令
    prompt = remove_redundant_instructions(prompt)
    # 3. 用更简洁的措辞
    prompt = simplify_language(prompt)
    return prompt
```

**效果**：节省 20-40%。

### 7.3 优化维度 3：缓存

| 缓存类型 | 节省率 | 命中率 |
|---|---|---|
| **精确缓存** | 100% | 5-15% |
| **语义缓存** | 100% | 20-50% |
| **Prompt 缓存** | 50-90% | 30-70% |
| **响应缓存** | 100% | 10-30% |

### 7.4 优化维度 4：智能路由

```python
# 不是所有请求都需要最强模型
# 用小模型 + 大模型配合

def smart_routing(query):
    easy_classifier_output = small_llm.classify_difficulty(query)
    if easy_classifier_output == "easy":
        return small_llm.generate(query)  # $0.001
    else:
        return big_llm.generate(query)  # $0.05
```

**效果**：平均节省 40-60%。

### 7.5 优化维度 5：输出限制

```python
# 限制 max_tokens 防止"啰嗦"响应
config = {
    "max_tokens": 1000,  # 不允许超过 1000
    "stop_sequences": ["\n\n---", "END"]
}
```

### 7.6 优化维度 6：批量请求

```python
# 合并多个小请求为一个大请求
def batch_requests(requests):
    combined_prompt = combine_prompts(requests)
    response = llm.generate(combined_prompt, max_tokens=2000)
    return split_responses(response, len(requests))
```

**效果**：节省 30-50%。

### 7.7 优化维度 7：微调 vs 通用

| 场景 | 通用大模型 | 微调小模型 | 节省 |
|---|---|---|---|
| 简单任务 | GPT-4o mini | 自训练 7B | 5-10x |
| 复杂任务 | GPT-4o | GPT-4o + 微调 | 1.5-3x |

### 7.8 优化维度 8：Token 预算

```python
# 给每类请求分配 token 预算
TOKEN_BUDGETS = {
    "intent_classification": 100,
    "simple_qa": 500,
    "complex_qa": 2000,
    "code_generation": 4000,
    "summarization": 2000,
    "agent_step": 4000,
}

def enforce_budget(feature, max_tokens):
    return min(TOKEN_BUDGETS.get(feature, 1000), max_tokens)
```

### 7.9 优化维度 9：闲置停止

```python
# 如果流式响应用户已经断连，停掉
async def stream_with_disconnect_check(generator, connection_alive):
    async for chunk in generator:
        if not connection_alive():
            return  # 停止生成，节省 token
        yield chunk
```

### 7.10 综合优化效果

```
基线：$30,000/月
├── 智能路由：-40%  → $18,000
├── 缓存：-30%      → $12,600
├── Prompt 压缩：-20% → $10,080
├── 输出限制：-10%   → $9,072
└── 综合：$9,072（节省 70%）
```

---

## 八、定价模型与商业模式

### 8.1 AI Gateway 公司的定价

| 模式 | 描述 | 例子 |
|---|---|---|
| **按 token 抽成** | 在上游 token 价格上加 10-30% | Portkey |
| **按请求数** | $X/1k requests | 部分 SaaS |
| **按月订阅** | $X/月，按 tier 划分 | 企业版 |
| **按用量阶梯** | 用越多单价越低 | Cloudflare |
| **按功能** | 基础免费 + 高级收费 | LiteLLM |
| **混合** | 基础订阅 + 用量超额 | 多数 |

### 8.2 定价示例

#### Portkey 风格

```
免费层：0-100 万 token/月，0%
Growth：100 万 - 1000 万 token，$0.001/1k token 加成
Pro：1000 万+，定制价格
```

#### Cloudflare 风格

```
免费：10 万次请求/月
Paid $5/月：1000 万次
Enterprise：定制
```

#### Helicone 风格

```
免费层：0-10k requests
Pro $20/月：100k requests
Team $200/月：1M requests
Enterprise：定制
```

### 8.3 AI Gateway 公司的成本结构

| 成本 | 占比 |
|---|---|
| **云基础设施** | 30-40% |
| **人力（工程）** | 30-40% |
| **销售** | 15-20% |
| **支持** | 5-10% |
| **其他** | 5% |

### 8.4 毛利率分析

| 业务 | 毛利率 |
|---|---|
| **按 token 抽成** | 50-70% |
| **SaaS 订阅** | 70-85% |
| **托管服务** | 30-50% |
| **咨询服务** | 60-80% |

### 8.5 定价心理

- **9 美元定价**：低于 10 元感
- **年付折扣**：20% off 月付
- **按用量**：让客户"花多少花多少"
- **免费层**：培养用户
- **透明定价**：建立信任

---

## 九、ROI 测算方法

### 9.1 ROI 公式

```
ROI = (收益 - 成本) / 成本 × 100%
```

### 9.2 AI 网关带来的收益

| 收益维度 | 量化方式 |
|---|---|
| **成本降低** | 直接节省的 token 费用 |
| **效率提升** | 工程师节省的时间 |
| **业务增长** | 因 AI 能力带来的新收入 |
| **风险降低** | 避免的安全/合规事故损失 |

### 9.3 详细测算

```
投入：
- 网关订阅：$5,000/月
- 实施工时：$20,000 一次性
- 运维工时：$3,000/月

收益：
- 缓存节省：$10,000/月
- 路由优化节省：$5,000/月
- 故障率降低（避免 downtime）：$2,000/月（等效）
- 工程师效率提升：$8,000/月（等效）

月度 ROI = (25,000 - 8,000) / 8,000 = 213%
年度 ROI = (300,000 - 116,000) / 116,000 = 159%
```

### 9.4 TCO（总拥有成本）

```
直接成本：
- 软件订阅
- 云资源
- 第三方服务

间接成本：
- 实施工时
- 培训
- 维护

隐藏成本：
- 机会成本
- 切换成本
- 学习曲线
```

### 9.5 Payback Period（投资回收期）

```
回收期 = 投入 / 月度净收益
     = ($20,000 + 3×$8,000) / $17,000/月
     = $44,000 / $17,000
     = 2.6 个月
```

**健康指标**：< 6 个月。

### 9.6 NPV（净现值）

```
NPV = Σ (CF_t / (1+r)^t) - 初始投入

考虑 3 年：
- 第 1 年：现金流 $200,000
- 第 2 年：现金流 $300,000
- 第 3 年：现金流 $500,000
- 初始投入：$100,000
- 折现率：10%
- NPV = ?
```

### 9.7 风险调整

```
期望 ROI = ROI × 成功概率 - 失败损失 × 失败概率
```

| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| 网关故障 | 1% | 业务中断 | 多活 + 监控 |
| 模型价格变化 | 30% | 成本上升 | 多模型支持 |
| 团队学习成本 | 50% | 效率下降 | 培训 + 文档 |
| 厂商锁定 | 20% | 切换成本 | 开源 + 中立 |

---

## 十、成本治理与告警

### 10.1 实时监控

```python
class CostMonitor:
    def __init__(self, alert_manager):
        self.alert_manager = alert_manager
    
    def on_cost_event(self, event):
        # 1. 累加
        current = self.get_current(event.tenant_id, period="month")
        budget = self.get_budget(event.tenant_id)
        
        # 2. 阈值告警
        ratio = current / budget
        if ratio > 1.0:
            self.alert("exceeded", event.tenant_id, ratio)
        elif ratio > 0.8:
            self.alert("warning", event.tenant_id, ratio)
    
    def get_current(self, tenant_id, period):
        # 从 ClickHouse 查询
        return self.storage.query(...)
```

### 10.2 异常检测

```python
class AnomalyDetector:
    def detect(self, recent_costs):
        # 简单：与历史均值比较
        mean = recent_costs[:-1].mean()
        std = recent_costs[:-1].std()
        latest = recent_costs[-1]
        z_score = (latest - mean) / std
        return z_score > 3  # 3σ 异常
```

### 10.3 成本控制

```python
class CostController:
    def check(self, request, tenant_id):
        # 1. 估算成本
        estimated = estimate_cost(request)
        
        # 2. 检查预算
        if exceeds_budget(tenant_id, estimated):
            return "block"
        
        # 3. 检查速率（避免突然爆炸）
        if rate_too_high(tenant_id):
            return "rate_limit"
        
        return "allow"
```

### 10.4 死循环防护

```python
# Agent 可能死循环
# 网关必须有终止能力

class LoopGuard:
    def check(self, agent_id, steps):
        if len(steps) > 50:
            raise TooManyStepsError()
        
        if detect_repeat(steps):
            raise LoopDetectedError()
```

---

## 十一、行业基准与对标

### 11.1 行业平均成本

| 业务类型 | 每用户每月成本 |
|---|---|
| **ChatGPT 类** | $0.50-2.00 |
| **客服 Chatbot** | $0.20-1.00 |
| **RAG 知识库** | $1.00-5.00 |
| **代码助手** | $2.00-10.00 |
| **Agent 平台** | $5.00-50.00 |
| **AI 搜索** | $0.10-0.50 |

### 11.2 单 token 成本基准

| 任务 | 平均 token | 平均成本 |
|---|---|---|
| **简单问答** | 500 in + 200 out | $0.003 |
| **RAG 问答** | 3000 in + 500 out | $0.015 |
| **代码生成** | 500 in + 1000 out | $0.020 |
| **Agent 任务** | 10000 in + 3000 out | $0.080 |

### 11.3 成本 vs 质量

```
成本 ↑
    │  ★ GPT-4o ($0.05/req, 95% quality)
    │
    │       ★ Claude Sonnet ($0.04, 94%)
    │
    │            ★ GPT-4o-mini ($0.001, 85%)
    │
    │               ★ DeepSeek V3 ($0.0008, 80%)
    │
    │                  ★ Llama 3.1 8B (self, $0.0005, 70%)
    │
    └────────────────────────────→ 质量
```

**甜蜜点**：$0.001-0.01/req 区域（GPT-4o-mini、DeepSeek）。

### 11.4 行业利润率

| 行业 | AI 产品利润率 |
|---|---|
| **AI 客服 SaaS** | 50-70% |
| **AI 写作工具** | 60-80% |
| **AI 代码助手** | 40-60% |
| **AI 搜索** | 30-50% |
| **AI Agent 平台** | 20-50%（成本高） |

---

## 十二、未解难题与研究前沿

### 12.1 定价

1. **AI 网关的"合理"抽成**应该多少？
2. **按 token vs 按请求 vs 按订阅**哪种最优？
3. **多模型价格变动**时的定价调整
4. **"免费层"的最优设计**——能培养又不亏
5. **企业大客户**的定价心理学

### 12.2 成本优化

6. **模型选择**的最优算法（结合质量）
7. **Prompt 压缩**的极限
8. **缓存命中率**的天花板
9. **批量请求**的组织方式
10. **跨请求上下文复用**的极致

### 12.3 成本预测

11. **突发流量**的预测
12. **新功能上线**的成本影响评估
13. **模型升级**的成本影响
14. **多模型混合**的预测
15. **季节性**模式识别

### 12.4 经济学

16. **AI 服务的边际成本**是否真为 0？
17. **"摊销"GPU 成本**的正确方式
18. **自建 vs 用 API**的经济学
19. **AI 服务的可负担性**长期
20. **AI 经济泡沫**风险

### 12.5 治理

21. **跨部门成本分摊**的公平性
22. **影子 AI**（未授权使用）的成本治理
23. **AI 滥用**（攻击者花光预算）的防护
24. **AI 投入** vs 实际收益的追踪
25. **AI 成本**的财务核算

### 12.6 未来形态

26. **Token 经济**是否成为新的"货币"
27. **AI 服务的免费性**可持续吗
28. **AI 服务的"开源"经济学**
29. **AI 服务的"网络效应"**
30. **AI 网关作为"卖水人"**的天花板

---

## 十三、参考资料

### 13.1 模型价格

- openai.com/pricing
- anthropic.com/pricing
- ai.google.dev/pricing
- deepseek.com/pricing
- alibaba cloud 通义 pricing

### 13.2 行业分析

- a16z "Cost of AI"
- Bessemer "AI cost analysis"
- IDC "AI infrastructure"
- Sequoia "AI compute costs"
- ICONIQ "AI unit economics"

### 13.3 工具

- github.com/Portkey-AI/gateway（成本归因）
- github.com/Helicone/helicone（成本分析）
- OpenAI Usage Dashboard
- Anthropic Console
- Google Cloud Billing

### 13.4 论文

- "The Economics of Large Language Models" (OpenAI)
- "LLM API Pricing Trends" (Stanford CRFM)
- "The Cost of AI" (Sequoia)

### 13.5 关键博客

- Simon Willison "LLM pricing"
- Latent Space "AI infra costs"
- The Pragmatic Engineer "AI pricing"

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 批 · 第 3 篇
- 主题：AI 网关的成本经济学
- 上一份：12-a2a-protocol.md
- 下一份预告：性能压测与容量规划
