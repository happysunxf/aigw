# RAG 场景的 AI 网关优化

> 系列：AI Gateway 持续深挖 · 第 2 批 · 第 7 篇
> 性质：纯技术研究
> 范围：RAG（Retrieval-Augmented Generation）场景下，AI Gateway 的特殊优化、路由、缓存、监控

---

## 目录

- [一、RAG 为什么需要"网关"](#一rag-为什么需要网关)
- [二、RAG 完整流程拆解](#二rag-完整流程拆解)
- [三、网关在 RAG 流程中的位置](#三网关在-rag-流程中的位置)
- [四、RAG 特有的缓存策略](#四rag-特有的缓存策略)
- [五、RAG 路由策略](#五rag-路由策略)
- [六、检索增强的可观测](#六检索增强的可观测)
- [七、RAG 成本优化](#七rag-成本优化)
- [八、多模态 RAG](#八多模态-rag)
- [九、Agent + RAG](#九agent--rag)
- [十、RAG 评测](#十rag-评测)
- [十一、企业 RAG 实践](#十一企业-rag-实践)
- [十二、未解难题与研究前沿](#十二未解难题与研究前沿)
- [十三、参考资料](#十三参考资料)

---

## 一、RAG 为什么需要"网关"

### 1.1 RAG 是什么

**RAG（Retrieval-Augmented Generation）** = 检索 + 生成。让 LLM 在回答前先检索相关文档，使回答基于事实。

### 1.2 RAG 的快速崛起

```
2020: RAG 概念提出
2023: ChatGPT 知识截止引发关注，RAG 爆发
2024: RAG 成为企业 AI 落地的标准范式
2025: Advanced RAG / Agentic RAG / GraphRAG
2026: 多模态 RAG、实时 RAG
```

### 1.3 RAG 场景下网关的独特价值

| 价值 | 描述 |
|---|---|
| **统一入口** | 所有 RAG 调用都过网关 |
| **检索增强** | 网关可做二次检索 / 重排 |
| **缓存** | 文档级 / 答案级缓存 |
| **路由** | 不同问题路由到不同知识库 |
| **可观测** | 看到检索质量、生成质量 |
| **成本控制** | 检索 + 生成的 token 都计量 |
| **安全** | 文档级权限控制 |

### 1.4 没有网关的 RAG 困境

```
问题 1：每个应用都自己拼装 → 代码重复
问题 2：缓存不共享 → 浪费资源
问题 3：权限管理混乱 → 安全风险
问题 4：监控各自为政 → 难以优化
问题 5：成本归因难 → 老板看不见
```

---

## 二、RAG 完整流程拆解

### 2.1 标准 RAG 流程

```
User Query
    ↓
[1. Query 处理]
    - Query 改写
    - Query 扩展
    - HyDE（生成假设性答案再检索）
    ↓
[2. 检索（Retrieval）]
    - 向量检索
    - 关键词检索
    - 混合检索
    - 多跳检索
    ↓
[3. 后处理（Post-Retrieval）]
    - 重排（Rerank）
    - 过滤（Filter）
    - 压缩（Compress）
    ↓
[4. Prompt 组装]
    - 插入上下文
    - 引用标注
    ↓
[5. LLM 生成]
    - 流式输出
    - 引用插入
    ↓
[6. 后处理（Post-Generation）]
    - 引用清理
    - 幻觉检查
    ↓
Response
```

### 2.2 高级 RAG 模式

#### Advanced RAG

```
Query → 改写 → 检索 → 重排 → 压缩 → LLM
                              ↑
                       多轮反馈
```

#### Agentic RAG

```
Query → Agent → 多步检索 → 综合 → 回答
                ├→ 检索 1
                ├→ 检索 2（基于检索 1 结果）
                └→ 检索 3（基于检索 1+2）
```

#### Self-RAG

```
Query → 检索 → 生成 → 自我评估 → 是否需要再检索？
                              ↓
                          是 → 重新检索
                          否 → 输出
```

#### Corrective RAG (CRAG)

```
Query → 检索 → 评估文档质量
              ├→ 高质量：直接用
              ├→ 中等：补充检索
              └→ 低：重新生成检索 query
```

#### GraphRAG

```
Query → 知识图谱检索 → 实体关系 → 文档 → LLM
```

### 2.3 关键技术细节

#### Query 改写

```python
def rewrite_query(query, history=None):
    # 1. 处理指代
    if history:
        query = resolve_coreferences(query, history)
    
    # 2. 扩展同义词
    query = expand_synonyms(query)
    
    # 3. 提取关键实体
    entities = extract_entities(query)
    
    return query, entities
```

#### HyDE（Hypothetical Document Embeddings）

```python
def hyde_retrieval(query, llm):
    # 1. 让 LLM 生成假设性答案
    hypothetical = llm.generate(f"Answer this question briefly: {query}")
    
    # 2. 用假设性答案的 embedding 检索
    hyp_embedding = embed(hypothetical)
    results = vector_db.search(hyp_embedding, top_k=10)
    
    return results
```

#### 重排（Rerank）

```python
def rerank(query, retrieved_docs, reranker_model):
    # Cross-Encoder 重排
    pairs = [[query, doc.content] for doc in retrieved_docs]
    scores = reranker_model.predict(pairs)
    
    # 按分数排序
    sorted_docs = [doc for _, doc in sorted(zip(scores, retrieved_docs), reverse=True)]
    return sorted_docs[:5]  # top 5
```

---

## 三、网关在 RAG 流程中的位置

### 3.1 三种部署模式

#### 模式 A：网关作为代理（最常见）

```
Application
    ↓
[AI Gateway]  ← 网关只做协议、缓存、监控
    ↓
[RAG Pipeline]  ← 应用内做完整 RAG
    ↓
[Vector DB] + [LLM]
```

**特点**：
- 网关不感知 RAG 内部
- 简单
- 缓存粒度粗

#### 模式 B：网关编排 RAG

```
Application
    ↓
[AI Gateway]  ← 网关协调检索 + LLM
    ├→ [Vector DB]
    └→ [LLM]
```

**特点**：
- 网关是 RAG 编排器
- 灵活
- 网关复杂

#### 模式 C：网关感知 RAG

```
Application
    ↓
[AI Gateway with RAG]  ← 网关理解 RAG 协议
    ├→ [Query Rewrite Service]
    ├→ [Retrieval Service]
    ├→ [Rerank Service]
    └→ [LLM]
```

**特点**：
- 网关有 RAG 专用能力
- 可观测深度最高
- 还在早期

### 3.2 网关的 RAG 价值

```
价值
├── 检索增强
│     ├── 跨应用共享检索结果
│     ├── 网关层 Query 改写
│     └── 二次重排
├── 缓存
│     ├── 文档级缓存
│     ├── 答案级缓存
│     └── Embedding 缓存
├── 路由
│     ├── 按租户路由知识库
│     ├── 按问题路由模型
│     └── 按语言路由
├── 可观测
│     ├── 检索质量
│     ├── 命中率
│     └── 答案忠实度
├── 成本
│     ├── Embedding 成本
│     ├── 检索成本
│     └── 生成成本
└── 安全
      ├── 文档权限
      ├── 答案审计
      └── 来源追溯
```

### 3.3 网关感知 RAG 的协议设想

```python
# 网关接收的请求
{
    "model": "gpt-4o",
    "messages": [...],
    
    # RAG 扩展字段
    "rag": {
        "knowledge_bases": ["kb-product-docs", "kb-internal-wiki"],
        "retrieval_strategy": "hybrid",
        "top_k": 10,
        "rerank": true,
        "include_citations": true,
        "max_context_tokens": 4000
    }
}

# 网关返回的响应
{
    "choices": [...],
    
    # RAG 元数据
    "rag_metadata": {
        "retrieved_docs": [
            {"id": "doc-1", "score": 0.92, "source": "kb-product-docs"},
            {"id": "doc-2", "score": 0.85, "source": "kb-internal-wiki"}
        ],
        "retrieval_time_ms": 120,
        "rerank_time_ms": 80,
        "context_tokens": 3200,
        "citation_count": 3
    }
}
```

---

## 四、RAG 特有的缓存策略

### 4.1 缓存层级

```
┌────────────────────────────────────┐
│ L1: 完整答案缓存（Query + Answer）  │  ← 最高命中率，最低复杂度
├────────────────────────────────────┤
│ L2: 检索结果缓存（Query + Docs）    │  ← 中等命中率
├────────────────────────────────────┤
│ L3: Embedding 缓存（Query + Vec）   │  ← 减少 Embedding 计算
├────────────────────────────────────┤
│ L4: 文档级缓存（DocID + 摘要）      │  ← 适合大文档
└────────────────────────────────────┘
```

### 4.2 L1：完整答案缓存

```python
class AnswerCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, query, knowledge_base_version, model):
        cache_key = f"{hash(query)}:{knowledge_base_version}:{model}"
        return self.cache.get(cache_key)
    
    def set(self, query, knowledge_base_version, model, answer):
        cache_key = f"{hash(query)}:{knowledge_base_version}:{model}"
        self.cache[cache_key] = answer
```

**失效**：
- 知识库更新 → 失效
- 模型升级 → 失效
- TTL 到期 → 失效

### 4.3 L2：检索结果缓存

```python
class RetrievalCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, query, knowledge_base_id, top_k):
        cache_key = f"{hash(query)}:{knowledge_base_id}:{top_k}"
        return self.cache.get(cache_key)
    
    def set(self, query, knowledge_base_id, top_k, docs):
        cache_key = f"{hash(query)}:{knowledge_base_id}:{top_k}"
        self.cache[cache_key] = docs
```

**价值**：
- 检索是 RAG 瓶颈
- 缓存后省掉向量检索
- **不需重排时**可直接用

### 4.4 L3：Embedding 缓存

```python
class EmbeddingCache:
    """避免重复计算 embedding"""
    
    def get_or_compute(self, text, model):
        cache_key = f"emb:{model}:{hash(text)}"
        if cached := self.cache.get(cache_key):
            return cached
        embedding = self.embedding_model.embed(text)
        self.cache[cache_key] = embedding
        return embedding
```

**重要**：很多 RAG 系统**每次都重新 embed query**，浪费巨大。

### 4.5 缓存的语义化

```python
class SemanticAnswerCache:
    """语义相似度匹配"""
    
    def get(self, query, threshold=0.92):
        query_emb = embed(query)
        for cached_emb, cached_data in self.cache.items():
            sim = cosine_similarity(query_emb, cached_emb)
            if sim > threshold:
                return cached_data
        return None
```

**适用**：
- 知识库变化慢
- 答案相对稳定
- 问法多样

### 4.6 网关的 RAG 缓存架构

```python
class RAGCacheLayer:
    def __init__(self):
        self.answer_cache = AnswerCache()      # L1
        self.retrieval_cache = RetrievalCache()  # L2
        self.embedding_cache = EmbeddingCache()  # L3
        self.semantic_cache = SemanticAnswerCache()  # 语义
    
    async def process(self, request):
        # 1. 检查答案缓存
        if answer := self.answer_cache.get(request):
            return answer
        
        # 2. 检查检索缓存
        retrieved_docs = None
        if cached_docs := self.retrieval_cache.get(request):
            retrieved_docs = cached_docs
        else:
            # 3. 计算 embedding（用缓存）
            query_emb = self.embedding_cache.get_or_compute(request.query)
            retrieved_docs = await vector_db.search(query_emb)
            self.retrieval_cache.set(request, retrieved_docs)
        
        # 4. 重新生成
        response = await llm.generate(retrieved_docs, request)
        
        # 5. 缓存答案
        self.answer_cache.set(request, response)
        
        return response
```

### 4.7 缓存命中率优化

| 优化 | 命中率提升 |
|---|---|
| **Query 归一化**（小写、去标点） | +5% |
| **多粒度缓存**（单 query + 子 query） | +10% |
| **语义缓存** | +20-30% |
| **共享知识库** | +30-50% |
| **预热** | 立即可用 |

---

## 五、RAG 路由策略

### 5.1 路由维度

```
RAG 请求
├── 知识库路由
│     ├── 按租户
│     ├── 按部门
│     ├── 按业务
│     └── 按权限
├── 模型路由
│     ├── 简单问答 → 小模型
│     ├── 复杂推理 → 大模型
│     ├── 代码任务 → 代码模型
│     └── 多语言 → 多语言模型
├── 检索策略路由
│     ├── 高频 Q → 精确缓存
│     ├── 长尾 Q → 完整检索
│     └── 实时数据 → 实时索引
└── 知识库优先级
      ├── 主知识库
      ├── 备用知识库
      └── 联网搜索
```

### 5.2 知识库路由

```python
class KBRouter:
    def __init__(self, knowledge_bases, permissions):
        self.kbs = knowledge_bases
        self.perms = permissions
    
    def route(self, request, user_context):
        # 1. 找用户可访问的 KB
        accessible_kbs = self._get_accessible_kbs(user_context)
        
        # 2. 按内容分类路由
        relevant_kbs = self._classify_kbs(request.query, accessible_kbs)
        
        # 3. 合并检索
        all_docs = []
        for kb in relevant_kbs:
            docs = self._retrieve(kb, request)
            all_docs.extend(docs)
        
        # 4. 重排
        reranked = self._rerank(all_docs, request)
        return reranked
    
    def _get_accessible_kbs(self, user_context):
        user_perms = self.perms[user_context.user_id]
        return [kb for kb in self.kbs if kb.id in user_perms.allowed_kbs]
```

### 5.3 模型路由

```python
def route_model(query, retrieved_docs):
    complexity = estimate_complexity(query, retrieved_docs)
    
    if complexity < 0.3:
        return "gpt-4o-mini"  # 简单问答
    elif complexity < 0.7:
        return "gpt-4o"  # 标准 RAG
    else:
        return "claude-opus"  # 复杂分析
```

### 5.4 检索策略路由

```python
def route_retrieval_strategy(query, history):
    # 多轮对话：可能上下文更相关
    if history and len(history) > 2:
        return "context_aware_retrieval"
    
    # 实时查询：必须最新数据
    if "latest" in query.lower() or "now" in query.lower():
        return "web_search_retrieval"
    
    # 精确查询：可能关键词匹配更好
    if is_specific_entity_query(query):
        return "keyword_retrieval"
    
    # 默认：混合检索
    return "hybrid_retrieval"
```

### 5.5 知识库优先级

```python
PRIORITY_CHAIN = [
    "user_personal_kb",     # 用户个人知识库
    "team_kb",              # 团队知识库
    "department_kb",        # 部门知识库
    "company_kb",           # 公司知识库
    "public_kb",            # 公开知识库
    "web_search"            # 联网搜索
]

def retrieve_with_priority(query, user):
    docs = []
    for kb_name in PRIORITY_CHAIN:
        kb = get_kb(kb_name, user)
        kb_docs = kb.retrieve(query, top_k=5)
        docs.extend(kb_docs)
        if is_sufficient(docs):
            break
    return docs
```

---

## 六、检索增强的可观测

### 6.1 关键指标

| 指标 | 含义 | 目标 |
|---|---|---|
| **检索召回率** | 命中的相关文档 / 总相关文档 | > 80% |
| **检索精确率** | 命中的相关文档 / 命中总文档 | > 60% |
| **MRR** | Mean Reciprocal Rank | > 0.7 |
| **NDCG** | Normalized Discounted Cumulative Gain | > 0.8 |
| **答案忠实度** | 答案基于检索的比例 | > 90% |
| **答案相关性** | 答案与 query 的相关 | > 80% |
| **答案完整性** | 答案是否完整 | > 75% |
| **命中率** | 检索有结果的比例 | > 95% |
| **检索延迟** | P50/P99 | < 500ms |
| **生成延迟** | P50/P99 | < 2s |

### 6.2 网关层的可观测

```python
class RAGObservability:
    def __init__(self):
        self.tracer = tracer
    
    async def trace_rag(self, request, user_context):
        with self.tracer.start_span("rag_request") as span:
            # 1. 检索阶段
            with self.tracer.start_span("retrieval") as sub_span:
                retrieved = await self.retrieve(request)
                sub_span.set_attribute("rag.retrieved_count", len(retrieved))
                sub_span.set_attribute("rag.avg_score", avg([d.score for d in retrieved]))
                sub_span.set_attribute("rag.top_score", retrieved[0].score if retrieved else 0)
            
            # 2. 重排阶段
            with self.tracer.start_span("rerank"):
                reranked = await self.rerank(request, retrieved)
            
            # 3. 生成阶段
            with self.tracer.start_span("llm_generation"):
                response = await self.llm.generate(request, reranked)
            
            # 4. 评估
            with self.tracer.start_span("evaluation"):
                metrics = self.evaluate(request, retrieved, response)
                span.set_attribute("rag.faithfulness", metrics.faithfulness)
                span.set_attribute("rag.relevance", metrics.relevance)
            
            return response
```

### 6.3 检索质量监测

```python
class RetrievalQualityMonitor:
    """实时监测检索质量"""
    
    def monitor(self, query, retrieved_docs, response, user_feedback=None):
        metrics = {
            # 检索阶段
            "retrieved_count": len(retrieved_docs),
            "top_score": retrieved_docs[0].score if retrieved_docs else 0,
            "avg_score": avg([d.score for d in retrieved_docs]),
            "score_variance": variance([d.score for d in retrieved_docs]),
            
            # 答案阶段
            "answer_relevance": self.estimate_relevance(query, response),
            "faithfulness": self.estimate_faithfulness(retrieved_docs, response),
            "citation_accuracy": self.check_citations(retrieved_docs, response),
            
            # 用户反馈
            "user_accepted": user_feedback.accepted if user_feedback else None,
            "user_regenerated": user_feedback.regenerated if user_feedback else None,
        }
        
        return metrics
```

### 6.4 答案忠实度评估

```python
def estimate_faithfulness(context, response):
    """LLM 评估答案是否基于上下文"""
    prompt = f"""Rate how faithful the answer is to the context (0-1).
    
    Context: {context}
    
    Answer: {response}
    
    Score (0=not faithful, 1=fully faithful):"""
    
    score = call_llm_mini(prompt, max_tokens=5)
    return float(score)
```

### 6.5 异常告警

```yaml
alerts:
  - name: RAG_Retrieval_LowScore
    condition: rag_top_score < 0.5
    duration: 5m
    severity: warning
    description: "检索 top 分数持续偏低，知识库可能有问题"
  
  - name: RAG_HighHallucination
    condition: rag_faithfulness < 0.7
    duration: 5m
    severity: critical
    description: "答案忠实度低，可能在幻觉"
  
  - name: RAG_NoRetrieval
    condition: rag_retrieved_count == 0
    duration: 1m
    severity: critical
    description: "检索无结果，索引可能损坏"
```

---

## 七、RAG 成本优化

### 7.1 成本拆解

```
RAG 总成本
├── Embedding 成本
│     ├── 文档 embedding（一次性）
│     └── Query embedding（每次）
├── 检索成本
│     ├── 向量库查询
│     └── 重排模型
└── 生成成本
      ├── 上下文 token
      └── 输出 token
```

### 7.2 典型成本分布

| 阶段 | 占总成本比例 |
|---|---|
| **Embedding** | 5-15% |
| **检索** | 5-10% |
| **生成（上下文）** | 60-80% |
| **生成（输出）** | 10-20% |

**洞察**：上下文 token 是最大头。

### 7.3 优化策略

#### 优化 1：上下文压缩

```python
def compress_context(docs, max_tokens=2000):
    """用 LLM 压缩检索到的文档"""
    combined = "\n\n".join([d.content for d in docs])
    
    if count_tokens(combined) <= max_tokens:
        return combined
    
    compressed = llm.generate(
        f"Compress the following to under {max_tokens} tokens, preserving key info:\n{combined}",
        max_tokens=max_tokens
    )
    return compressed
```

**效果**：上下文 token 减少 50-80%。

#### 优化 2：智能 top_k

```python
def adaptive_top_k(query):
    """根据问题复杂度调整 top_k"""
    complexity = estimate_query_complexity(query)
    if complexity < 0.3:
        return 3
    elif complexity < 0.7:
        return 5
    else:
        return 10
```

#### 优化 3：Embedding 模型选择

| 模型 | 维度 | 成本 | 质量 |
|---|---|---|---|
| OpenAI text-embedding-3-small | 1536 | $0.02/1M | 高 |
| BGE-large | 1024 | 自托管 | 高 |
| all-MiniLM-L6-v2 | 384 | 自托管 | 中 |

**成本差异**：100-1000x。

#### 优化 4：嵌入缓存

```python
# Query embedding 缓存
# 同一 query 不重复 embed
# 命中率：5-20%
```

#### 优化 5：检索跳过

```python
def should_skip_retrieval(query):
    """简单问题跳过检索"""
    if is_greeting(query):
        return True
    if is_general_knowledge(query):
        return True
    return False
```

### 7.4 上下文 token 优化技术

| 技术 | 节省 | 副作用 |
|---|---|---|
| **Top-k 减少** | 30-50% | 可能漏信息 |
| **上下文压缩** | 50-80% | 失真风险 |
| **关键句提取** | 60-80% | 实现复杂 |
| **摘要替换** | 70-90% | 信息损失 |
| **结构化检索** | 50-70% | 需要预处理 |

---

## 八、多模态 RAG

### 8.1 多模态 RAG 类型

| 类型 | 描述 | 例子 |
|---|---|---|
| **图像检索** | 用图像查相似图像/文档 | Google Lens |
| **视频 RAG** | 视频内容检索+问答 | 视频内容分析 |
| **音频 RAG** | 音频转文本后 RAG | 播客问答 |
| **多模态输入 RAG** | 图像 + 文本查询 | "图里的产品说明" |
| **多模态输出 RAG** | 检索后生成图文 | 报告 + 图表 |

### 8.2 多模态 RAG 挑战

| 挑战 | 描述 |
|---|---|
| **多模态 embedding** | 不同模态对齐 |
| **大文件** | 视频、音频大 |
| **预处理** | 抽帧、ASR |
| **跨模态检索** | 用文搜图 / 用图搜文 |
| **多模态生成** | 输出图文 |

### 8.3 网关层的多模态 RAG

```python
class MultimodalRAGGateway:
    async def process(self, request):
        # 1. 多模态预处理
        if request.has_image:
            # 图像描述
            caption = await vision_llm.generate(
                prompt="Describe this image in detail",
                image=request.image
            )
            # 把图像描述加入检索 query
            request.query += f"\n[Image content: {caption}]"
        
        if request.has_audio:
            # ASR
            text = await asr.transcribe(request.audio)
            request.query += f"\n[Audio transcript: {text}]"
        
        # 2. 检索
        retrieved = await vector_db.search(embed(request.query))
        
        # 3. 多模态生成
        response = await multimodal_llm.generate(
            prompt=request.query,
            context=retrieved,
            image=request.image  # 保留原图
        )
        
        return response
```

---

## 九、Agent + RAG

### 9.1 Agentic RAG

```python
class AgenticRAG:
    def __init__(self, agent, retriever):
        self.agent = agent
        self.retriever = retriever
    
    async def run(self, query):
        # 1. Agent 规划
        plan = self.agent.plan(query)
        # ["search_kb1", "search_kb2", "compare", "synthesize"]
        
        # 2. 多步检索
        all_docs = []
        for step in plan:
            if step.startswith("search"):
                kb = step.split("_")[1]
                docs = await self.retriever.retrieve(kb, query)
                all_docs.extend(docs)
            elif step == "compare":
                # Agent 做比较
                comparison = self.agent.compare(all_docs)
                all_docs.append(comparison)
            elif step == "synthesize":
                # Agent 总结
                return self.agent.synthesize(all_docs, query)
```

### 9.2 多 Agent RAG

```
User Query
    ↓
Orchestrator Agent
    ├→ Knowledge Agent
    │     ├→ 检索 1
    │     ├→ 检索 2
    │     └→ 重排
    ├→ Analysis Agent
    │     └→ 分析检索结果
    └→ Writing Agent
          └→ 综合 + 引用
    ↓
Final Answer
```

### 9.3 网关在 Agentic RAG 中的角色

```python
class GatewayForAgenticRAG:
    async def process(self, request):
        # 1. 网关可观察所有 Agent 调用
        # 2. 网关可缓存子任务结果
        # 3. 网关可限流（避免 Agent 死循环）
        # 4. 网关可计费（按子任务）
        # 5. 网关可审计（哪步用了哪些知识库）
```

---

## 十、RAG 评测

### 10.1 评测维度

| 维度 | 指标 |
|---|---|
| **检索质量** | Recall, Precision, MRR, NDCG |
| **生成质量** | Faithfulness, Relevance, Coherence |
| **端到端** | 任务完成率, 用户满意度 |
| **成本** | 单查询成本 |
| **延迟** | P50/P99 |
| **安全** | 引用准确, 无幻觉 |

### 10.2 评测数据集

| 数据集 | 描述 |
|---|---|
| **BEIR** | 检索基准 |
| **MS MARCO** | 检索基准 |
| **Natural Questions** | 开放域 QA |
| **HotpotQA** | 多跳 QA |
| **RAGAS** | RAG 专用评测 |
| **ARES** | 自动 RAG 评估 |
| **RGB** | RAG 基准 |

### 10.3 自动化评测

```python
class RAGEvaluator:
    def __init__(self):
        self.judge_llm = GPT_4O_MINI
    
    async def evaluate(self, query, context, response, ground_truth=None):
        metrics = {}
        
        # 1. 忠实度（基于上下文）
        metrics['faithfulness'] = await self.judge(
            f"Is the answer faithful to the context?\nContext: {context}\nAnswer: {response}"
        )
        
        # 2. 相关性（基于 query）
        metrics['answer_relevance'] = await self.judge(
            f"Is the answer relevant to the query?\nQuery: {query}\nAnswer: {response}"
        )
        
        # 3. 与 ground truth 比
        if ground_truth:
            metrics['ground_truth_similarity'] = cosine_similarity(
                embed(response), embed(ground_truth)
            )
        
        return metrics
```

### 10.4 在线评测

```python
# 用户反馈作为评测信号
class OnlineEvaluator:
    def record(self, query, response, user_action):
        if user_action == "regenerate":
            # 用户不满意
            self.metrics['regenerate_rate'].increment()
        elif user_action == "thumbs_up":
            self.metrics['positive_rate'].increment()
        elif user_action == "click_citation":
            # 用户查看了引用
            self.metrics['citation_click_rate'].increment()
```

---

## 十一、企业 RAG 实践

### 11.1 典型企业 RAG 架构

```
┌────────────────────────────────────────┐
│ 企业应用                                 │
└─────────────────┬──────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ AI Gateway (Higress / Portkey)         │
│ - 鉴权                                 │
│ - 限流                                 │
│ - 计费                                 │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ RAG Orchestrator                        │
│ - Query 改写                           │
│ - 多 KB 路由                           │
│ - 重排                                 │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────┼─────────────────────┐
│                 │                     │
↓                 ↓                     ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ KB: HR      │ │ KB: 财务    │ │ KB: 产品    │
│ Qdrant     │ │ pgvector   │ │ Milvus     │
└─────────────┘ └─────────────┘ └─────────────┘
```

### 11.2 文档处理流水线

```
原始文档
    ↓
[1. 解析]
    - PDF / Word / HTML / Markdown
    - 保留结构
    ↓
[2. 分块]
    - 按段落 / 章节
    - 500-1000 tokens 块
    - 块重叠 100 tokens
    ↓
[3. Embedding]
    - 批量 embed
    - 异步
    ↓
[4. 索引]
    - 写入向量库
    - 元数据
    ↓
可检索
```

### 11.3 文档更新策略

| 策略 | 描述 | 适用 |
|---|---|---|
| **全量重建** | 删旧建新 | 文档变化大 |
| **增量更新** | 只更新变化 | 文档变化小 |
| **双写** | 同时新旧索引 | 零停机 |
| **版本化** | 多版本共存 | 需要回滚 |

### 11.4 权限管理

```python
# 文档级权限
class DocumentPermissions:
    def can_access(self, user, document):
        # 1. 文档级 ACL
        if document.acl and user.id not in document.acl:
            return False
        
        # 2. 部门级
        if document.department_id and user.department_id != document.department_id:
            return False
        
        # 3. 分类级（机密/内部/公开）
        if document.classification == "confidential" and user.clearance < 3:
            return False
        
        return True
```

### 11.5 网关层的权限过滤

```python
class RAGGatewayWithPermissions:
    async def retrieve(self, request, user_context):
        # 1. 检索所有相关文档
        all_docs = await self.retriever.retrieve(request)
        
        # 2. 过滤用户无权访问的
        accessible_docs = [
            d for d in all_docs 
            if self.permissions.can_access(user_context.user, d)
        ]
        
        if not accessible_docs:
            return None  # 用户没权限
        
        return accessible_docs
```

### 11.6 引用与可追溯

```python
def generate_with_citations(query, context_docs, llm):
    prompt = f"""Answer the question based on the context.
    
    For each claim, cite the source as [1], [2], etc.
    
    Context:
    [1] {context_docs[0].content}
    [2] {context_docs[1].content}
    [3] {context_docs[2].content}
    
    Question: {query}
    """
    response = llm.generate(prompt)
    
    # 验证引用
    citations = extract_citations(response)
    for cite_num in citations:
        if int(cite_num) > len(context_docs):
            # 引用不存在
            log_warning(f"Invalid citation [{cite_num}]")
    
    return response, citations
```

---

## 十二、未解难题与研究前沿

### 12.1 检索质量

1. **检索召回率的天花板**——还能怎么提升
2. **长尾查询**的检索难题
3. **多模态检索**的统一表征
4. **跨语言检索**的语义对齐
5. **实时索引**与查询的一致性

### 12.2 生成质量

6. **幻觉的根本解决**——还是只能检测
7. **引用准确性**的系统性提升
8. **多文档综合**的可靠性
9. **矛盾文档**的智能处理
10. **答案多样性与准确性**的平衡

### 12.3 架构

11. **RAG 协议标准化**——网关该如何知道 RAG 流程
12. **RAG + Fine-tuning** 的最优组合
13. **RAG + Agent** 的边界
14. **RAG 状态管理**——多轮对话
15. **RAG 的可解释性**

### 12.4 性能

16. **检索延迟的极限**——< 100ms 可能吗
17. **大知识库的检索扩展**
18. **检索 + 生成的联合优化**
19. **流式 RAG**
20. **预检索**的极致优化

### 12.5 成本

21. **RAG 单位经济**——单 query 成本优化极限
22. **Embedding 成本**进一步降低
23. **上下文压缩** 的质量损失
24. **缓存命中**的天花板
25. **多租户 RAG** 的成本分摊

### 12.6 评测

26. **RAG 评测的"真值"问题**——没有标准答案
27. **长尾场景评测**
28. **多模态 RAG 评测**
29. **Agentic RAG 评测**
30. **用户主观质量**与机器评分的对齐

---

## 十三、参考资料

### 13.1 论文

- "Retrieval-Augmented Generation for Large Language Models: A Survey" (Gao et al., 2023)
- "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection" (Asai et al., 2023)
- "Corrective Retrieval Augmented Generation" (Yan et al., 2024)
- "Advanced RAG Techniques" 系列
- "GraphRAG" (Microsoft Research, 2024)
- "RAGAS: Automated Evaluation of Retrieval Augmented Generation" (Es et al., 2023)

### 13.2 框架

- LangChain / LlamaIndex
- Haystack (deepset)
- txtai
- RAGFlow
- DSPy
- Verba (Weaviate)
- PrivateGPT

### 13.3 向量库

- Qdrant
- Milvus
- Weaviate
- pgvector
- Pinecone
- Chroma
- LanceDB

### 13.4 评测

- RAGAS
- ARES
- TruLens
- LangSmith
- Phoenix (Arize)

### 13.5 关键博客

- "Advanced RAG" 系列
- LangChain RAG 教程
- LlamaIndex RAG 文档
- Anthropic "Contextual Retrieval"
- OpenAI "RAG 最佳实践"

### 13.6 网关相关

- Portkey RAG 支持
- LiteLLM RAG 集成
- Higress RAG 插件

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 批 · 第 7 篇
- 主题：RAG 场景的网关优化
- 上一份：16-public-cloud-integration.md
- 下一份预告：Fine-tuning 与个性化网关
