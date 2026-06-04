# AI 网关性能压测与容量规划

> 系列：AI Gateway 持续深挖 · 第 2 批 · 第 4 篇
> 性质：纯技术研究
> 范围：LLM 网关性能指标、压测方法、容量规划、性能调优、瓶颈分析

---

## 目录

- [一、为什么 AI 网关性能独特](#一为什么-ai-网关性能独特)
- [二、关键性能指标（KPI）](#二关键性能指标kpi)
- [三、性能基线：业界水平](#三性能基线业界水平)
- [四、压测方法论](#四压测方法论)
- [五、压测工具](#五压测工具)
- [六、压测场景设计](#六压测场景设计)
- [七、性能瓶颈分析](#七性能瓶颈分析)
- [八、容量规划](#八容量规划)
- [九、性能调优技术](#九性能调优技术)
- [十、性能监控与告警](#十性能监控与告警)
- [十一、性能回归测试](#十一性能回归测试)
- [十二、未解难题与研究前沿](#十二未解难题与研究前沿)
- [十三、参考资料](#十三参考资料)

---

## 一、为什么 AI 网关性能独特

### 1.1 与传统 API 网关的差异

| 维度 | 传统 API 网关 | AI Gateway |
|---|---|---|
| **请求体大小** | 几 KB | 几 MB（多模态） |
| **响应模式** | 同步、确定大小 | 流式、不可预测 |
| **后端延迟** | 10-100ms | 500-5000ms |
| **单请求资源** | 低 | 高（GPU） |
| **缓存效果** | 大（请求-响应匹配） | 中（语义匹配） |
| **吞吐瓶颈** | CPU | GPU + 网络 |

### 1.2 性能优化的"两难"

**延迟 vs 吞吐**：
- 优化延迟 → 小 batch，资源利用率低
- 优化吞吐 → 大 batch，延迟高

**质量 vs 成本**：
- 优化质量 → 大模型、慢
- 优化成本 → 小模型、快

**缓存命中 vs 缓存存储**：
- 命中率越高越好 → 存更多
- 存更多 → 检索慢、内存大

### 1.3 网关特有的性能挑战

- **流式响应**：TCP 长连接、内存累积
- **多模态**：图像 base64 编码、内存膨胀
- **Agent 多步**：状态累积、连接管理
- **缓存层**：语义检索、embedding 计算
- **可观测**：日志写入、metrics 上报
- **多租户**：公平调度、资源隔离

---

## 二、关键性能指标（KPI）

### 2.1 延迟指标

| 指标 | 含义 | 单位 | 行业目标 |
|---|---|---|---|
| **TTFT** | Time To First Token | ms | 100-500 |
| **ITL** | Inter-Token Latency | ms/token | 10-50 |
| **TPOT** | Time Per Output Token | ms/token | 10-50 |
| **E2E 延迟** | 端到端（用户视角） | ms | 1000-5000 |
| **P50** | 中位数延迟 | ms | < 1000 |
| **P95** | 95 分位 | ms | < 3000 |
| **P99** | 99 分位 | ms | < 5000 |
| **Max** | 最坏延迟 | ms | < 30000 |

### 2.2 吞吐指标

| 指标 | 含义 | 单位 | 行业目标 |
|---|---|---|---|
| **QPS** | Queries Per Second | req/s | 100-10000+ |
| **TPS** | Tokens Per Second | tokens/s | 1k-100k+ |
| **RPM** | Requests Per Minute | req/min | 1k-100w+ |
| **并发数** | 同时处理请求数 | count | 10-1000+ |
| **Goodput** | SLA 内的吞吐 | req/s | 70-90% of peak |

### 2.3 资源指标

| 指标 | 含义 | 行业水平 |
|---|---|---|
| **CPU 使用率** | 进程 CPU | 50-80% |
| **内存使用** | 进程内存 | 视实现 |
| **网络带宽** | 入/出 | 视规模 |
| **GPU 利用率** | GPU 占用 | 70-90% |
| **KV cache 使用** | 显存占用 | 70-90% |
| **连接数** | TCP 连接 | 视实现 |

### 2.4 业务指标

| 指标 | 含义 |
|---|---|
| **缓存命中率** | 缓存命中 / 总请求 |
| **错误率** | 5xx / 总请求 |
| **重试率** | 重试 / 总请求 |
| **降级率** | Fallback / 总请求 |
| **用户接受率** | 用户未重新生成 / 总请求 |

---

## 三、性能基线：业界水平

### 3.1 网关层（自建）

| 网关 | 语言 | P99 增量 | 吞吐 (单核) |
|---|---|---|---|
| **Portkey** | Go | 5-20ms | 5k-20k RPS |
| **LiteLLM** | Python | 20-100ms | 500-2k RPS |
| **Higress** | Go/C++ | 1-5ms | 50k+ RPS |
| **Envoy** | C++ | 1-3ms | 100k+ RPS |
| **Nginx** | C | < 1ms | 100k+ RPS |

### 3.2 上游 LLM API

| 提供方 | TTFT | TPOT | 备注 |
|---|---|---|---|
| **OpenAI GPT-4o** | 200-500ms | 20-40ms | 流式 |
| **Anthropic Claude** | 300-700ms | 25-50ms | 流式 |
| **Google Gemini** | 200-600ms | 15-30ms | 流式 |
| **DeepSeek** | 300-800ms | 30-50ms | 国内较慢 |
| **Qwen** | 200-500ms | 20-40ms | 国内 |

### 3.3 自托管推理引擎

| 引擎 | 显卡 | TTFT | TPOT | 吞吐 |
|---|---|---|---|---|
| **vLLM (Llama-70B)** | 2×H100 | 100-200ms | 30-50ms | ~3000 tokens/s |
| **TGI (Llama-70B)** | 2×H100 | 100-300ms | 30-50ms | ~2500 tokens/s |
| **SGLang (Llama-70B)** | 2×H100 | 80-200ms | 25-45ms | ~3500 tokens/s |
| **TensorRT-LLM** | 2×H100 | 80-150ms | 20-40ms | ~4000 tokens/s |

### 3.4 网关对 LLM 的延迟贡献

```
总延迟 = 网关延迟 + 网络延迟 + 上游 LLM 延迟
      = 5-50ms  + 10-50ms + 200-2000ms
      ≈ 网关占比 < 5%
```

**结论**：网关本身不是瓶颈，但**放大了其他瓶颈**。

---

## 四、压测方法论

### 4.1 压测四阶段

```
Stage 1: 摸底（Smoke Test）
  - 1 个用户，1 个请求
  - 验证基本功能

Stage 2: 负载（Load Test）
  - 模拟生产流量
  - 验证 SLA

Stage 3: 压力（Stress Test）
  - 超出预期流量
  - 找极限点

Stage 4: 极限（Soak / Spike Test）
  - 持续运行 / 突发流量
  - 找稳定性问题
```

### 4.2 压测四要素

| 要素 | 描述 |
|---|---|
| **负载模式** | 渐增、恒定、脉冲、阶梯 |
| **用户模拟** | 真实用户、脚本、录制回放 |
| **数据准备** | 真实 prompt、生产日志 |
| **指标采集** | QPS、延迟、错误、资源 |

### 4.3 真实 vs 合成流量

| 维度 | 真实 | 合成 |
|---|---|---|
| **准确性** | 高 | 中 |
| **可重复** | 低 | 高 |
| **隐私** | 风险 | 安全 |
| **覆盖度** | 高 | 可控 |
| **生产风险** | 风险 | 隔离 |

**最佳实践**：合成为主 + 真实抽样回放。

### 4.4 压测工作流

```
1. 准备测试数据（prompt 集）
2. 配置压测工具
3. 启动目标系统
4. 暖机（warm-up）
5. 渐进增加负载
6. 采集指标
7. 达到目标后停止
8. 分析结果
9. 调优
10. 复测
```

### 4.5 LLM 特有的压测挑战

#### 挑战 1：响应长度不可预测

```python
# 不同 prompt 输出长度差 100x
# 压测时需要多样化
prompts = [
    "Hi",  # 输出 ~5 tokens
    "Explain quantum computing in detail",  # 输出 ~500 tokens
    "Write a 10-page essay on...",  # 输出 ~5000 tokens
]
```

#### 挑战 2：流式响应难测

```python
# 必须测：首 token 延迟 + 中间 token 延迟 + 末 token 延迟
metrics = {
    "ttft": ...,      # 首 token
    "itl_avg": ...,   # 平均
    "itl_p99": ...,   # 99 分位
    "total": ...,     # 总时间
}
```

#### 挑战 3：上游限流

```python
# 上游 API 有 rate limit
# 压测可能触发限流
# 必须设计退避策略或用 mock
```

#### 挑战 4：成本

```python
# 真实压测可能烧钱
# 解决：
# - 用本地 mock（fast mock LLM）
# - 用小模型
# - 用真实 API + 限额
```

### 4.6 Mock LLM 工具

```python
# 快速 mock，模拟各种响应时间
class MockLLM:
    def __init__(self, ttft_mean=300, tpot_mean=30):
        self.ttft_mean = ttft_mean
        self.tpot_mean = tpot_mean
    
    async def stream(self, prompt):
        # 模拟首 token 延迟
        await asyncio.sleep(random.gauss(self.ttft_mean, 50) / 1000)
        yield "Mock"
        
        # 模拟后续 token
        for i in range(random.randint(5, 50)):
            await asyncio.sleep(random.gauss(self.tpot_mean, 5) / 1000)
            yield f" token{i}"
```

---

## 五、压测工具

### 5.1 通用压测工具

| 工具 | 语言 | 特点 |
|---|---|---|
| **wrk** | C | 高性能 HTTP 压测 |
| **k6** | Go | 现代化压测平台 |
| **Locust** | Python | 分布式压测 |
| **Vegeta** | Go | 简单稳定 |
| **hey** | Go | 极简 |
| **JMeter** | Java | 老牌 GUI |
| **Gatling** | Scala | 高级场景 |

### 5.2 LLM 专用压测

| 工具 | 特点 |
|---|---|
| **openai-evals** | OpenAI 官方 eval 框架 |
| **vllm bench** | vLLM 性能测试 |
| **llm-perf** | LLM 性能基准 |
| **genai-bench** | 多模型对比 |
| **Guidance bench** | 带约束的生成测试 |
| **llmperf** | Stanford CRFM 的 LLM 性能测试 |

### 5.3 自建 LLM 压测

```python
import asyncio
import time
from dataclasses import dataclass

@dataclass
class LoadResult:
    total_requests: int
    successful: int
    failed: int
    ttft_p50: float
    ttft_p99: float
    tpot_p50: float
    tpot_p99: float
    total_p99: float
    qps: float

class LLMLoadTester:
    def __init__(self, target_url, model, prompt_set):
        self.target = target_url
        self.model = model
        self.prompts = prompt_set
    
    async def run(self, concurrent_users, total_requests):
        semaphore = asyncio.Semaphore(concurrent_users)
        results = []
        
        async def one_request():
            async with semaphore:
                prompt = random.choice(self.prompts)
                result = await self._send_request(prompt)
                results.append(result)
        
        start = time.time()
        await asyncio.gather(*[one_request() for _ in range(total_requests)])
        elapsed = time.time() - start
        
        return self._analyze(results, elapsed, concurrent_users)
    
    async def _send_request(self, prompt):
        # 调用 LLM，记录 TTFT、TPOT 等
        ...
    
    def _analyze(self, results, elapsed, concurrent):
        # 统计 P50/P99 等
        ...
```

### 5.4 用 k6 做压测

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
    stages: [
        { duration: '1m', target: 100 },   // 渐增到 100 并发
        { duration: '5m', target: 100 },   // 保持
        { duration: '1m', target: 1000 },  // 渐增到 1000
        { duration: '5m', target: 1000 },  // 保持
        { duration: '1m', target: 0 },     // 渐降
    ],
    thresholds: {
        http_req_duration: ['p(99)<3000'],  // P99 < 3s
        http_req_failed: ['rate<0.01'],     // 错误率 < 1%
    }
};

export default function () {
    let prompt = randomItem(['Hi', 'Explain X', 'Write Y']);
    let res = http.post(`${__ENV.TARGET}/v1/chat/completions`, JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [{ role: 'user', content: prompt }],
        stream: true
    }), {
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${__ENV.KEY}` }
    });
    
    check(res, {
        'status is 200': (r) => r.status === 200,
        'has content': (r) => r.body.length > 0,
    });
}
```

### 5.5 流式响应压测

```python
class StreamingLoadTester:
    async def measure_stream(self, prompt):
        ttft = None
        tpot_list = []
        last_token_time = None
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.target}/v1/chat/completions",
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        now = time.time()
                        if ttft is None:
                            ttft = (now - start) * 1000
                        elif last_token_time:
                            tpot_list.append((now - last_token_time) * 1000)
                        last_token_time = now
        
        return {
            "ttft_ms": ttft,
            "tpot_avg_ms": sum(tpot_list) / len(tpot_list) if tpot_list else 0,
            "tpot_p99_ms": sorted(tpot_list)[int(len(tpot_list) * 0.99)] if tpot_list else 0,
            "total_ms": (time.time() - start) * 1000,
            "token_count": len(tpot_list) + 1
        }
```

---

## 六、压测场景设计

### 6.1 场景分类

| 场景 | 描述 | 关键指标 |
|---|---|---|
| **Chat 场景** | 短 prompt + 短响应 | TTFT, E2E |
| **RAG 场景** | 长 prompt + 中响应 | TTFT, TPOT |
| **Agent 场景** | 多步调用 | E2E, 步数 |
| **流式实时** | 持续长流 | TTFT, 流稳定 |
| **突发流量** | 10x 突增 | 错误率, 恢复时间 |
| **长会话** | 持续几小时 | 内存, 稳定 |

### 6.2 真实 prompt 抽样

```python
# 从生产日志抽样
def sample_production_prompts(log_file, n=10000):
    prompts = []
    with open(log_file) as f:
        for line in f:
            entry = json.loads(line)
            if random.random() < 0.01:  # 1% 采样
                prompts.append(entry['request']['messages'])
                if len(prompts) >= n:
                    break
    return prompts

# 或者用公开数据集
def use_public_dataset():
    from datasets import load_dataset
    ds = load_dataset("OpenAssistant/oasst1", split="train")
    return [item['text'] for item in ds.shuffle().select(range(1000))]
```

### 6.3 场景模板

```yaml
# scenario.yaml
scenarios:
  - name: "chat_baseline"
    concurrent_users: 100
    duration: 300s
    prompts:
      - "Hi"
      - "How are you?"
      - "Explain quantum computing briefly"
    metrics:
      - ttft_p99 < 500
      - e2e_p99 < 3000
      - error_rate < 0.1%
  
  - name: "rag_heavy"
    concurrent_users: 50
    duration: 600s
    prompts:
      - "Given the following context: [2000 tokens context]... Answer the question"
    metrics:
      - ttft_p99 < 1000
      - tpot_p99 < 50
      - error_rate < 0.5%
  
  - name: "agent_loop"
    concurrent_users: 20
    duration: 1800s
    scenarios:
      - complex multi-step task
    metrics:
      - e2e_p99 < 60000
      - steps < 20
      - cost < $1.0
  
  - name: "spike"
    concurrent_users: 1000
    duration: 60s
    ramp_up: 5s
    metrics:
      - error_rate < 5%
      - recovery_time < 30s
```

### 6.4 多场景并行

```python
# 模拟真实流量混合
SCENARIO_MIX = {
    "chat": 0.5,      # 50% 短对话
    "rag": 0.3,       # 30% RAG
    "agent": 0.1,     # 10% Agent
    "code": 0.1,      # 10% 代码
}

def pick_scenario():
    r = random.random()
    cumulative = 0
    for name, ratio in SCENARIO_MIX.items():
        cumulative += ratio
        if r < cumulative:
            return name
```

---

## 七、性能瓶颈分析

### 7.1 瓶颈识别方法

#### 方法 1：分层打点

```python
import time

class PerformanceProfiler:
    def __init__(self):
        self.timings = {}
    
    def record(self, layer, duration_ms):
        self.timings[layer] = self.timings.get(layer, 0) + duration_ms
    
    def profile_request(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_total = time.time()
            
            start = time.time()
            # 网关层处理
            self.record("gateway_in", (time.time() - start) * 1000)
            
            start = time.time()
            response = await func(*args, **kwargs)
            self.record("llm_call", (time.time() - start) * 1000)
            
            start = time.time()
            # 后处理
            self.record("gateway_out", (time.time() - start) * 1000)
            
            self.record("total", (time.time() - start_total) * 1000)
            return response
        return wrapper
```

#### 方法 2：火焰图

```python
# 用 py-spy 生成 Python 火焰图
py-spy record -o flamegraph.svg --pid 12345

# 用 async-profiler 生成 Java 火焰图（如果用 JVM）

# 用 perf 生成 C/Rust 火焰图
perf record -F 99 -p 12345 -g -- sleep 30
perf script | stackcollapse-perf | flamegraph > flamegraph.svg
```

#### 方法 3：分布式追踪

```
[OpenTelemetry Trace]
├── Span: gateway.receive     [5ms]
├── Span: pii_detect          [3ms]
├── Span: cache_check         [2ms]
├── Span: route_decision      [1ms]
├── Span: llm_call            [1500ms]   ← 瓶颈
│     ├── Span: prefetch
│     ├── Span: prefill
│     └── Span: decode
├── Span: stream_chunks       [800ms]
├── Span: redact_output       [3ms]
└── Span: send_to_client      [5ms]
```

### 7.2 常见瓶颈

#### 瓶颈 1：GPU 显存不足

**症状**：
- OOM 错误
- 吞吐突然下降
- 请求被排队

**诊断**：
```bash
nvidia-smi
# 看 GPU 显存使用、KV cache 占用
```

**解决**：
- 增大 batch size
- 量化
- 模型并行
- 增加 GPU

#### 瓶颈 2：网络带宽

**症状**：
- TTFT 正常但总延迟高
- 跨 region 请求慢

**诊断**：
```bash
iperf3 -c server
```

**解决**：
- 压缩
- 边缘缓存
- 同 region 部署

#### 瓶颈 3：日志写入

**症状**：
- 写日志慢
- 异步队列堆积

**诊断**：
```python
import logging
# 看日志写入延迟
```

**解决**：
- 异步批量写
- 采样
- 用 ClickHouse 代替 ES

#### 瓶颈 4：缓存检索

**症状**：
- 缓存命中率高但延迟没降
- embedding 计算慢

**诊断**：
- 测 embedding 推理时间
- 测向量检索时间

**解决**：
- 本地 embedding 模型
- 优化向量库（HNSW 参数）
- 预计算

#### 瓶颈 5：连接池

**症状**：
- 连接建立慢
- "too many open files"

**诊断**：
```bash
ulimit -n
ss -s
```

**解决**：
- HTTP keep-alive
- 连接池复用
- 调大 ulimit

#### 瓶颈 6：Python GIL

**症状**：
- 多核没用
- CPU 单核打满

**解决**：
- 多进程（gunicorn）
- 改 Go/Rust
- C 扩展

---

## 八、容量规划

### 8.1 容量规划公式

```
所需 QPS = 峰值 DAU × 人均请求 / 86400 × 峰值系数

例子：
  DAU = 100,000
  人均 = 10 请求/天
  峰值系数 = 5（一天中最高小时是平均的 5 倍）
  
  峰值 QPS = 100,000 × 10 / 86400 × 5
          = 11.5
          ≈ 12 QPS

  峰值 TPM（Tokens Per Minute）= 12 × 60s × 500 tokens/req
                              = 360,000 tokens/min
```

### 8.2 容量规划步骤

```
Step 1: 业务预测
  - DAU 增长
  - 人均请求增长
  - 季节性
  
Step 2: 流量建模
  - 峰值 QPS
  - 平均 / P99 延迟
  - 流量曲线

Step 3: 资源测算
  - 多少网关实例
  - 多少 GPU
  - 多少存储

Step 4: 余量设计
  - 2x 容量冗余
  - N+1 高可用
  - 弹性伸缩

Step 5: 验证
  - 压测
  - 灰度
  - 监控
```

### 8.3 网关实例数计算

```
网关单实例吞吐 = 5,000 RPS
峰值 QPS = 12
实例数 = ceil(12 / 5000) = 1
加冗余 = 3 实例（高可用）

结论：1 个网关实例足够，3 个保高可用
```

### 8.4 GPU 数量计算

```
单卡吞吐 = 3000 tokens/s
峰值 TPM = 360,000 tokens/min = 6000 tokens/s
单卡足够 = 6000/3000 = 2 张卡

加冗余 = 3 张卡
加 buffer（5x 增长）= 15 张卡
```

### 8.5 容量规划表

| 业务规模 | DAU | QPS 峰值 | 网关实例 | GPU |
|---|---|---|---|---|
| **早期** | 1k | 1 | 2 | 1-2 |
| **成长** | 10k | 10 | 3 | 4-8 |
| **规模** | 100k | 100 | 5-10 | 20-50 |
| **大型** | 1M | 1000 | 20-50 | 100-300 |
| **超大型** | 10M+ | 10k+ | 100+ | 1000+ |

### 8.6 弹性伸缩

```python
class AutoScaler:
    def __init__(self, k8s_client):
        self.k8s = k8s_client
        self.thresholds = {
            "scale_up": {"qps_per_pod": 3000, "p99_ms": 2000, "gpu_util": 0.85},
            "scale_down": {"qps_per_pod": 1000, "p99_ms": 500, "gpu_util": 0.3}
        }
    
    def check_and_scale(self):
        metrics = self.get_current_metrics()
        
        if self.should_scale_up(metrics):
            self.scale_up()
        elif self.should_scale_down(metrics):
            self.scale_down()
    
    def scale_up(self):
        new_count = self.current_count + 2
        self.k8s.scale_deployment("ai-gateway", new_count)
    
    def scale_down(self):
        new_count = max(1, self.current_count - 1)
        self.k8s.scale_deployment("ai-gateway", new_count)
```

### 8.7 容量规划的常见错误

| 错误 | 后果 |
|---|---|
| **低估峰值** | 突发流量打挂 |
| **高估峰值** | 资源浪费 |
| **忽略冷启动** | 用户感知慢 |
| **没考虑增长** | 几个月后扩容 |
| **没考虑 fail-over** | 单点故障 |
| **没考虑依赖** | 网关没挂但 DB 挂了 |

---

## 九、性能调优技术

### 9.1 网关层

#### 优化 1：连接复用

```python
# 客户端
async with httpx.AsyncClient(
    http2=True,
    limits=httpx.Limits(
        max_connections=200,
        max_keepalive_connections=50
    )
) as client:
    response = await client.post(...)
```

#### 优化 2：HTTP/2 + Server Push

```python
# 上游 HTTP/2 多路复用
# 单个连接处理多个请求
```

#### 优化 3：零拷贝

```python
# 大响应直接转发，不 buffer
async def stream_response(response):
    async for chunk in response.aiter_raw():
        yield chunk
```

#### 优化 4：序列化优化

```python
# 用 msgpack / protobuf 代替 JSON
# 内部通信

import msgpack
packed = msgpack.packb(data)
unpacked = msgpack.unpackb(packed)
# 比 JSON 快 3-5x
```

#### 优化 5：批量处理

```python
# 多个小请求合并
async def batch_requests(requests):
    if len(requests) == 1:
        return await process(requests[0])
    
    # 批量处理
    tasks = [process(r) for r in requests]
    return await asyncio.gather(*tasks)
```

#### 优化 6：避免 GC

```python
# Python: 调 GC 阈值
import gc
gc.set_threshold(700, 10, 5)

# 或者用 PyPy / 或换 Go
```

### 9.2 缓存层

#### 优化 1：分层缓存

```
L1: 进程内 LRU（< 1ms）
L2: Redis Cluster（5-10ms）
L3: 向量库（10-50ms）
L4: 上游 LLM（500-5000ms）
```

#### 优化 2：缓存预热

```python
# 启动时预加载热门缓存
async def warmup_cache():
    for prompt in popular_prompts:
        await get_or_compute(prompt)
```

#### 优化 3：缓存结果压缩

```python
# 缓存值用 gzip 压缩
import gzip
compressed = gzip.compress(response_body.encode())
```

### 9.3 协议层

#### 优化 1：流式优先

```python
# 所有响应尽量流式
# 减少感知延迟
```

#### 优化 2：SSE vs WebSocket

```
SSE: 简单、HTTP 友好、单向
WebSocket: 双向、复杂
选择：LLM 场景 SSE 够用
```

#### 优化 3：gRPC（内部通信）

```protobuf
service LLMService {
    rpc Generate(GenerateRequest) returns (stream GenerateResponse);
}
```

### 9.4 推理引擎层

#### 优化 1：vLLM 调参

```python
# 启动参数
vllm serve ... \
    --max-num-seqs 256 \         # 最大并发
    --max-model-len 32768 \      # 最大长度
    --gpu-memory-utilization 0.95 \
    --enable-prefix-caching \
    --enable-chunked-prefill
```

#### 优化 2：Speculative Decoding

```python
# 用小模型做猜测
# 大模型验证
# 加速 2-3x
```

#### 优化 3：量化

```python
# 4-bit 量化
# 显存减半，吞吐提升 1.5-2x
```

### 9.5 系统层

```bash
# Linux 调优
sysctl -w net.core.somaxconn=65535
sysctl -w net.ipv4.tcp_max_syn_backlog=65535
ulimit -n 1000000

# TCP 调优
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.tcp_fin_timeout=15
```

---

## 十、性能监控与告警

### 10.1 关键指标

```yaml
# Prometheus 指标
gateway_requests_total{method, model, status}
gateway_request_duration_seconds{method, model, quantile}
gateway_tokens_total{type, model}
gateway_cost_usd_total{model}
gateway_cache_hits_total{type}
gateway_active_connections
gateway_queue_length
gateway_error_rate
```

### 10.2 关键告警

```yaml
alerts:
  - name: HighP99Latency
    condition: gateway_request_duration_seconds:p99 > 3000
    duration: 5m
    severity: warning
  
  - name: HighErrorRate
    condition: rate(gateway_requests_total{status=~"5.."}[5m]) > 0.01
    duration: 2m
    severity: critical
  
  - name: GPUMemoryHigh
    condition: gpu_memory_used_bytes / gpu_memory_total_bytes > 0.95
    duration: 1m
    severity: critical
  
  - name: QueueGrowing
    condition: gateway_queue_length > 1000
    duration: 2m
    severity: warning
```

### 10.3 性能仪表盘

```
┌────────────────────────────────────────────┐
│  QPS: 1,234 (peak 2,567)                    │
│  P99: 1.8s (SLA 3s)                         │
│  Error rate: 0.3%                            │
│  GPU: 78% (12/16 cards)                     │
├────────────────────────────────────────────┤
│  TTFT P50: 280ms                            │
│  TTFT P99: 850ms                            │
│  TPOT P50: 25ms                             │
│  TPOT P99: 65ms                             │
├────────────────────────────────────────────┤
│  Cache hit rate: 35%                        │
│  Cost: $1,234 / day (budget $2,000)         │
└────────────────────────────────────────────┘
```

---

## 十一、性能回归测试

### 11.1 为什么需要

- 上游模型更新可能影响性能
- 网关代码改动可能引入 regression
- 缓存策略变化可能影响延迟
- 路由逻辑变化可能改变延迟分布

### 11.2 性能回归测试流程

```
1. 锁定基线
   - 选定 commit / 版本
   - 压测，记录指标
   
2. 改动代码

3. 同样条件压测
   - 同样 prompt 集
   - 同样并发
   - 同样时间

4. 对比指标
   - QPS 差异
   - P99 差异
   - 错误率差异
   - 资源使用差异

5. 决定
   - 性能回归 > 5%：回滚 / 优化
   - 性能持平：接受
   - 性能提升：保留
```

### 11.3 自动化性能 CI

```yaml
# .github/workflows/perf-test.yml
name: Performance Test
on: [pull_request]

jobs:
  perf:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build
        run: docker build -t gateway:test .
      - name: Start
        run: docker run -d -p 8080:8080 gateway:test
      - name: Warmup
        run: ./perf/warmup.sh
      - name: Benchmark
        run: ./perf/run.sh
      - name: Compare
        run: |
          CURRENT=$(cat results.json | jq '.p99_latency_ms')
          BASELINE=$(cat baseline.json | jq '.p99_latency_ms')
          REGRESSION=$(echo "scale=2; ($CURRENT - $BASELINE) / $BASELINE * 100" | bc)
          if (( $(echo "$REGRESSION > 5" | bc -l) )); then
            echo "Performance regression: $REGRESSION%"
            exit 1
          fi
```

### 11.4 性能基线管理

```python
# 维护历史基线
baselines = {
    "v1.0": {"p99": 1500, "qps": 5000},
    "v1.1": {"p99": 1400, "qps": 5500},
    "v1.2": {"p99": 1380, "qps": 5600},
    # ...
}

# 性能趋势可视化
import matplotlib.pyplot as plt
versions = list(baselines.keys())
p99s = [b['p99'] for b in baselines.values()]
plt.plot(versions, p99s)
plt.title("P99 Latency Over Versions")
plt.show()
```

---

## 十二、未解难题与研究前沿

### 12.1 性能

1. **流式响应的 P99** 怎么精准测量
2. **多模态响应**的延迟分解
3. **Agent 多步**的端到端延迟预测
4. **跨区域**延迟的稳定性
5. **首 token 延迟**的极限压低

### 12.2 压测

6. **真实流量回放**的标准化
7. **多场景混合**压测的统计方法
8. **压测成本**（真 LLM 调用）的降低
9. **压测覆盖率**（prompt 分布）的度量
10. **生产环境压测**的安全边界

### 12.3 容量规划

11. **突发流量**的预测算法
12. **资源弹性**的最优策略
13. **多区域容量**的协调
14. **GPU 共享** vs 独占的最优
15. **冷启动对容量的影响**

### 12.4 调优

16. **自动调优**（用 LLM 调 LLM 网关）
17. **跨语言优化**（Python → Go 迁移路径）
18. **GPU 利用率**的最优化
19. **网络协议**对延迟的影响
20. **内核参数**的最优配置

### 12.5 监控

21. **流式响应**的实时监控
22. **多租户公平**的指标
23. **GPU 细粒度**监控
24. **跨云/跨区**统一监控
25. **异常检测**算法

### 12.6 标准化

26. **LLM 网关压测标准**
27. **延迟测量标准**（TTFT/TPOT 怎么算）
28. **SLA 模板**
29. **性能基准**（业内公认）
30. **OpenTelemetry 性能属性**扩展

---

## 十三、参考资料

### 13.1 压测工具

- k6 (k6.io)
- Locust (locust.io)
- wrk (github.com/wg/wrk)
- Vegeta (github.com/tsenart/vegeta)
- llmperf (github.com/ray-project/llmperf)
- genai-bench (github.com/mlfoundations/genai-bench)
- openai-evals

### 13.2 推理引擎基准

- vllm benchmark
- TGI benchmark
- sglang benchmark
- llm-perf.github.io

### 13.3 性能分析

- py-spy (Python profiler)
- async-profiler (JVM)
- perf + FlameGraph (Linux)
- bcc / bpftrace

### 13.4 关键博客

- "Performance of LLM inference" 系列
- vLLM "Throughput optimizations"
- SGLang "Performance tricks"
- Anthropic "Production LLM inference"
- "Building a high-performance AI gateway"

### 13.5 论文

- "LLM Inference Unveiled: Survey and Roofline Model Insights" (2024)
- "FlashAttention" 系列
- "PagedAttention" 论文
- "Speculative Decoding" 论文

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 批 · 第 4 篇
- 主题：性能压测与容量规划
- 上一份：13-cost-economics.md
- 下一份预告：开源贡献与社区治理
