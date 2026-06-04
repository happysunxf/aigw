# 语义缓存：实现原理、调优与研究前沿

> 系列：AI Gateway 持续深挖 · 第 2 篇
> 性质：纯技术研究
> 范围：从精确缓存到语义缓存的完整技术栈、调优方法、未解难题

---

## 目录

- [一、为什么 LLM 场景需要"新缓存"](#一为什么-llm-场景需要新缓存)
- [二、缓存类型全景](#二缓存类型全景)
- [三、精确缓存实现](#三精确缓存实现)
- [四、语义缓存实现](#四语义缓存实现)
- [五、前缀缓存与推理引擎协同](#五前缀缓存与推理引擎协同)
- [六、缓存键设计：看似简单实则复杂](#六缓存键设计看似简单实则复杂)
- [七、缓存命中率与边际收益](#七缓存命中率与边际收益)
- [八、调优实战](#八调优实战)
- [九、缓存失效策略](#九缓存失效策略)
- [十、多租户与隐私问题](#十多租户与隐私问题)
- [十一、未解难题与研究前沿](#十一未解难题与研究前沿)
- [十二、参考资料](#十二参考资料)

---

## 一、为什么 LLM 场景需要"新缓存"

### 1.1 传统 HTTP 缓存为什么不直接用

| 维度 | 传统 HTTP 缓存 | LLM 场景 |
|---|---|---|
| Key | URL + Vary header | prompt 内容 |
| 失效 | TTL / Cache-Control | 语义相似度 |
| 命中条件 | 字节级相同 | 语义级相似 |
| 价值 | 减少回源 | 节省 token 成本 + 降低延迟 |

**LLM 场景的核心矛盾**：用户不会发完全相同的 prompt，但**意图相同**的问题大量存在。

例子：
- "How to learn Python?"
- "Best way to study Python?"
- "Python 学习方法"

这三条 prompt 语义相近，但 hash 完全不同，精确缓存全部 miss。

### 1.2 缓存的三大价值

1. **降本**——直接节省 token 费用
2. **降延迟**——缓存命中可降低 P50 延迟 5-10x
3. **削峰**——突发流量下保护上游 API

---

## 二、缓存类型全景

### 2.1 五个层级

```
┌──────────────────────────────────────────────────┐
│ L1: 进程内 LRU（最快、最小）                       │
├──────────────────────────────────────────────────┤
│ L2: 分布式缓存 Redis（快、共享、有限）             │
├──────────────────────────────────────────────────┤
│ L3: 语义缓存（embedding 检索 + 相似度阈值）        │
├──────────────────────────────────────────────────┤
│ L4: 前缀缓存（与推理引擎 KV cache 协同）           │
├──────────────────────────────────────────────────┤
│ L5: CDN / 边缘缓存（精确 + 地理分发）              │
└──────────────────────────────────────────────────┘
```

### 2.2 各层定位

| 层级 | 一致性 | 命中率 | 适用 |
|---|---|---|---|
| L1 进程内 | 弱（节点独立） | 视场景 | 高频重复 |
| L2 Redis | 强 | 中 | 多实例共享 |
| L3 语义 | 弱（阈值相关） | 高 | 自然语言输入 |
| L4 前缀 | 强 | 视 prefix 共享度 | 长上下文 + 共享 prefix |
| L5 CDN | 强 | 视场景 | 出海 / 静态内容 |

---

## 三、精确缓存实现

### 3.1 Key 构造

最简实现：
```python
import hashlib
import json

def cache_key(request):
    canonical = json.dumps({
        "model": request.model,
        "messages": request.messages,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "tools": request.tools,  # 工具定义也参与 hash
    }, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()
```

### 3.2 关键决策点

#### 决策 1：哪些字段参与 key

- **必须参与**：model、messages、temperature、top_p、tools
- **可选参与**：max_tokens、stop、seed、response_format
- **不参与**：user 字段、stream 字段、metadata

#### 决策 2：消息归一化

```python
# 归一化前
{"role": "user", "content": "Hello   World"}  
# 归一化后（去多余空白）
{"role": "user", "content": "Hello World"}
```

#### 决策 3：时间戳 / 随机数剔除

```python
# 归一化前
{"role": "user", "content": "现在几点？2025-01-15 10:30:00"}
# 归一化后（剔除时间）
{"role": "user", "content": "现在几点？"}
```

这是精确缓存命中率的关键。

### 3.3 精确缓存的局限

- **N-gram 改写**：换了同义词就 miss
- **格式微调**：多了空格、换了标点就 miss
- **多轮上下文**：只要一轮不同就全 miss

这逼出语义缓存。

---

## 四、语义缓存实现

### 4.1 核心流程

```
1. 客户端发 prompt
       ↓
2. 网关把 prompt 编码为 embedding（vector）
       ↓
3. 在向量库（Redis / pgvector / Qdrant / Milvus）里 ANN 检索 Top-K
       ↓
4. 相似度 > 阈值（如 0.92）→ 命中缓存
       ↓
5. 返回缓存的 response
```

### 4.2 关键设计点

#### 设计点 1：Embedding 模型选择

| 模型 | 维度 | 速度 | 质量 |
|---|---|---|---|
| text-embedding-3-small (OpenAI) | 1536 | API 慢 | 高 |
| text-embedding-3-large | 3072 | API 慢 | 极高 |
| all-MiniLM-L6-v2 (HF) | 384 | 本地快 | 中 |
| BGE-large-zh-v1.5 | 1024 | 本地快 | 中文优 |
| M3E | 768 | 本地快 | 中文优 |

**取舍**：
- **API embedding**——质量好但每次都花钱
- **本地 embedding**——免费但占资源
- **混合**——用本地做粗筛，API 做精筛

#### 设计点 2：向量库选型

| 库 | 规模 | 性能 | 部署 |
|---|---|---|---|
| **pgvector** | < 100 万 | 中 | 与业务库同部署 |
| **Qdrant** | 100 万 - 1 亿 | 高 | 独立部署 |
| **Milvus** | > 1 亿 | 极高 | 集群部署 |
| **Redis Vector** | < 100 万 | 中 | 已有 Redis 时 |
| **Chroma** | < 10 万 | 低 | 玩具/PoC |

#### 设计点 3：相似度阈值

**阈值与命中率的负相关**：

```
阈值 0.99  →  命中率 ~5%   (只命中几乎相同的)
阈值 0.95  →  命中率 ~15%
阈值 0.90  →  命中率 ~30%
阈值 0.85  →  命中率 ~50%  (开始有误命中)
阈值 0.80  →  命中率 ~70%  (误命中增多)
```

**理想区间**：0.88 - 0.94。需要 A/B 调优。

### 4.3 命中判定的两种范式

#### 范式 A：纯 embedding 相似度

```python
def semantic_match(query_emb, cache_emb, threshold=0.92):
    sim = cosine_similarity(query_emb, cache_emb)
    return sim > threshold, sim
```

**问题**：embedding 相似不等于语义相似
- "Apple is a fruit" vs "Apple is a company"  →  embedding 相似但语义不同

#### 范式 B：embedding 相似 + LLM 二次判定

```python
def semantic_match_v2(query, cached_query, query_emb, cache_emb, threshold=0.90):
    sim = cosine_similarity(query_emb, cache_emb)
    if sim < threshold:
        return False, sim
    # 二次判定：让 LLM 决定是否同义
    is_match = llm_judge(query, cached_query)
    return is_match, sim
```

**优势**：显著降低误命中
**代价**：多一次 LLM 调用（要花钱、增延迟）

### 4.4 语义缓存的特殊问题

#### 问题 1：工具调用的不可缓存

工具调用的输入包含**实时数据**（天气、股票）——这些不该被缓存。

解决：在 metadata 里标注 `cacheable: false`。

#### 问题 2：参数注入风险

如果缓存键计算错误，可能让**用户 A 的 query 命中用户 B 的 response**——这是严重安全问题。

解决：按租户分桶（详见第十节）。

#### 问题 3：流式响应的缓存

流式响应的缓存策略：

```python
# 方案 1：缓存完整响应，流式时重新切片
# 方案 2：缓存 chunk 序列，按相同速率流式输出
# 方案 3：缓存首 token 延迟，流式内容不缓存
```

---

## 五、前缀缓存与推理引擎协同

### 5.1 什么是前缀缓存

**KV Cache**：LLM 推理时，每个 token 的 attention 计算需要历史所有 token 的 K、V 矩阵。  
**前缀缓存**：如果两个请求的 prompt 前缀相同，K、V 矩阵可以**复用**——大幅降低推理延迟和成本。

### 5.2 vLLM 的实现

vLLM 用 **PagedAttention** + **prefix caching**：
- 自动检测 prompt 前缀
- 相同前缀的请求共享 KV cache
- 在多轮对话、共享 system prompt 的场景下命中率极高

### 5.3 网关层如何配合

#### 策略 1：透传不破坏

让 vLLM 自己做 prefix matching —— 网关只做透传。

#### 策略 2：主动重排

```python
# 多个并发请求如果 system 相同，路由到同一个推理实例
def smart_routing(requests, instances):
    grouped = defaultdict(list)
    for r in requests:
        key = r.system_prompt  # 简化
        grouped[key].append(r)
    
    # 同 key 的请求路由到同一实例
    for key, group in grouped.items():
        instance = find_instance_with_prefix(key)
        for r in group:
            route(r, instance)
```

#### 策略 3：提示前缀位置

```python
# 把系统提示放最前
# 把用户问题放最后
# 把共享内容（few-shot examples）放中间
```

### 5.4 网关层的"前缀感知"能力

| 网关 | 是否前缀感知 |
|---|---|
| vLLM 直接调用 | ✅ 原生 |
| LiteLLM + vLLM | ❌ 透传 |
| Higress + vLLM | ✅ Wasm 插件可实现 |
| Portkey | ⚠️ 计划中 |

---

## 六、缓存键设计：看似简单实则复杂

### 6.1 必须考虑的字段差异

| 字段 | 归一化策略 |
|---|---|
| `messages[].content` | 去空白、Unicode 归一化（NFKC） |
| `messages[].role` | 大小写不敏感 |
| `temperature` | 浮点四舍五入（如 0.7 vs 0.700001 视为相同） |
| `max_tokens` | 必须参与 |
| `tools` | 序列化顺序无关 |
| `tool_choice` | 必须参与 |
| `response_format` | 必须参与 |
| `stream` | **不参与**（流式是传输方式） |
| `user` | **不参与**（避免跨用户泄露） |
| `seed` | 必须参与 |

### 6.2 "意外字段"陷阱

- `metadata` 字段——OpenAI 接受但不影响输出，**不参与** key
- `logit_bias`——OpenAI 专属，参与
- `safetySettings`（Gemini）——**必须参与**！不同安全级别会改变输出
- `cache_control`（Anthropic）——控制是否缓存，参与
- `previous_response_id`（Responses API）——**不参与**（已经是状态引用）

### 6.3 多轮对话的缓存

```python
# 错误做法：缓存整个 messages 数组 → 第一轮不同就全 miss
# 正确做法 1：只缓存最后一轮
def get_last_user_message(messages):
    return next(m for m in reversed(messages) if m.role == "user")

# 正确做法 2：滑动窗口（只取最近 N 轮）
def get_recent_messages(messages, n=3):
    return messages[-2*n:]
```

---

## 七、缓存命中率与边际收益

### 7.1 典型命中率

| 场景 | 精确缓存命中率 | 语义缓存命中率 | 提升 |
|---|---|---|---|
| 客服机器人 | 5-15% | 30-60% | 3-5x |
| 文档 RAG | 10-20% | 40-70% | 3-4x |
| 代码助手 | 20-40% | 40-50% | 1.5-2x |
| 通用 Chat | 1-5% | 10-20% | 3-5x |
| Agent 多步 | < 1% | 5-10% | 5-10x |

### 7.2 边际收益曲线

```
命中率提升
   ↑
   │                    ┌─── 收益递减
   │                 ╱
   │              ╱
   │           ╱
   │        ╱
   │     ╱
   │  ╱
   │╱
   └─────────────────────→ 投入（embedding 成本 / 调优时间）
```

**洞察**：
- 从 0% 到 20% 命中率——**极容易**（精确缓存 + 归一化）
- 从 20% 到 50%——需要语义缓存 + 调优
- 从 50% 到 80%——需要 LLM 二次判定 + 复杂路由
- 超过 80%——通常意味着数据问题（不是缓存做得好）

---

## 八、调优实战

### 8.1 调优步骤

```
Step 1: 收集 1 周真实流量，统计 prompt 分布
Step 2: 先上精确缓存，记录命中率
Step 3: 分析未命中的 prompt 模式
Step 4: 上语义缓存，从阈值 0.95 开始
Step 5: 人工抽检误命中，调整阈值
Step 6: 引入 LLM 二次判定（如果允许）
Step 7: A/B 测试不同 embedding 模型
Step 8: 长期监控命中率、误命中率、用户反馈
```

### 8.2 关键指标

| 指标 | 含义 | 目标 |
|---|---|---|
| **命中率** | 缓存命中 / 总请求 | 30-60% |
| **误命中率** | 不该命中但命中 / 总命中 | < 5% |
| **延迟节省** | 命中请求的 P50 延迟降低 | 5-10x |
| **成本节省** | 节省的 token 费用 | 看场景 |
| **Embedding 成本** | 每次请求的 embedding 费用 | < 节省的 30% |

### 8.3 调优陷阱

#### 陷阱 1：embedding 模型选错

- 用英文模型处理中文 → 命中率塌陷
- 用小模型处理复杂语义 → 误命中飙升

#### 陷阱 2：阈值一刀切

- 客服 query 简单 → 阈值 0.95
- 技术 query 复杂 → 阈值 0.88
- 应该**按场景分桶**

#### 陷阱 3：忽略缓存污染

- 一次错误的 response 写入缓存 → 后续所有相似 query 都拿到错误答案
- 必须有**反馈机制**（用户纠正/重新生成时清除缓存）

#### 陷阱 4：缓存预热过度

- 把历史数据全量预热 → 浪费存储、命中率也不高
- 应该**懒加载**——只缓存真正被命中的

---

## 九、缓存失效策略

### 9.1 失效维度

| 维度 | 策略 |
|---|---|
| **时间** | TTL（通常 1h - 24h） |
| **事件** | 模型升级 → 全清 |
| **用户** | 主动清除（纠错时） |
| **租户** | 租户级 TTL（不同租户不同策略） |
| **内容敏感度** | 敏感 query 不缓存 |

### 9.2 模型升级带来的问题

- v1 模型升级到 v1.1 → 输出可能微调
- 但 hash key 相同 → 命中 v1 的旧 response
- **解决**：model version 参与 cache key，或模型升级时清空

### 9.3 "软失效"

不要直接删除，而是：
- 标记为 "stale"
- 优先返回 stale 缓存
- 异步重新生成，下次覆盖
- 比"删除 + 回源"延迟更低

---

## 十、多租户与隐私问题

### 10.1 跨租户泄露风险

**错误实现**：
```python
# 所有租户共享一个向量库
def semantic_search(query_emb):
    return vector_db.search(query_emb)  # 可能命中其他租户的缓存
```

**正确实现**：
```python
def semantic_search(query_emb, tenant_id):
    return vector_db.search(
        query_emb,
        filter={"tenant_id": tenant_id}  # 强制隔离
    )
```

### 10.2 隐私保护增强

| 级别 | 策略 |
|---|---|
| **L0** | 租户隔离（基础） |
| **L1** | PII 检测后才入库 |
| **L2** | 敏感字段端到端加密 |
| **L3** | 差分隐私 embedding |
| **L4** | 同态加密（理论） |

### 10.3 "缓存 key 推断" 攻击

攻击场景：攻击者通过**反复查询相似 prompt** + 观察响应延迟，**推断出缓存里有什么**。

缓解：
- 缓存命中也走完整延迟（不早返回）
- 缓存大小对租户隐藏

---

## 十一、未解难题与研究前沿

### 11.1 命中率极限

1. **不同业务的命中率天花板分别是多少？**——还是经验值
2. **embedding 检索 + LLM 二次判定**的最优比例？
3. **什么样的 prompt 不该被缓存**？——理论上的可缓存判别器

### 11.2 成本博弈

4. **embedding 成本 vs 节省成本**——何时应该关闭语义缓存？
5. **缓存污染的经济影响**——一个错误响应被 N 次复用，损失多大？
6. **多级缓存的最优配比**——L1/L2/L3 投入多少资源？

### 11.3 一致性 / 隐私

7. **跨租户语义缓存的隐私 vs 命中率**怎么权衡？
8. **缓存推断攻击**的量化风险？
9. **差分隐私 embedding** 在生产环境可行吗？
10. **GDPR / 数据保护法**下，缓存的合法性边界？

### 11.4 新范式

11. **基于 LLM 自身的"可缓存判断"**——把"这个 query 能缓存吗"做成 LLM 任务
12. **跨用户 query 聚类**——把相似 query 自动聚类，共享缓存
13. **prompt 模板感知的缓存**——同一模板不同参数共享缓存
14. **基于强化学习的缓存策略**——阈值 + 失效策略自适应
15. **联邦语义缓存**——跨组织共享缓存但不泄露内容

### 11.5 与推理引擎的协同

16. **vLLM PagedAttention** 能否被网关直接调度？
17. **prefix caching 的"前缀最长匹配"**——网关能否主动重排请求？
18. **语义缓存命中时跳过 prefix 重建**——这是浪费还是必要？
19. **多模态 prefix caching**（图像 + 文本前缀）

### 11.6 可观测

20. **缓存命中/未命中的归因分析**——为什么这条 prompt 没命中？
21. **缓存污染的自动检测**——基于用户反馈 or LLM 评估
22. **缓存热度的长期演化**——老缓存自然淘汰机制

---

## 十二、参考资料

### 12.1 论文 / 文章

- "CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion" (2024)
- "Prompt Cache: Modular Attention Reuse for Low-Latency Inference" (2024)
- "Efficient Streaming Language Models with Attention Sinks" (2024, vLLM 团队)
- Anthropic "Prompt Caching" 文档
- OpenAI "Prompt Caching" 文档
- vLLM PagedAttention 论文

### 12.2 工具

- github.com/redis/redis (vector module)
- github.com/pgvector/pgvector
- github.com/qdrant/qdrant
- github.com/milvus-io/milvus
- github.com/chroma-core/chroma

### 12.3 项目实践

- GPTCache (zilliztech/GPTCache) —— 专门做 LLM 缓存的开源项目
- LiteLLM caching 模块
- Portkey cache plugin
- Cloudflare AI Gateway cache
- LangChain caching (InMemoryCache, RedisCache, RedisSemanticCache)

### 12.4 关键博客

- HuggingFace "How to cache LLM responses"
- Pinecone "Semantic caching for LLM applications"
- Anyscale "LLM inference optimization: prefix caching"
- Modal "LLM caching strategies"

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 篇
- 主题：语义缓存
- 上一份：01-llm-protocols.md
- 下一份预告：智能路由决策算法演进
