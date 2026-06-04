# AI 网关的 SLA 与服务治理

> 系列：AI Gateway 持续深挖 · 第 2 批 · 第 9 篇
> 性质：纯技术研究
> 范围：AI Gateway 的 SLA 体系、服务治理、容灾、变更管理、可靠性工程

---

## 目录

- [一、AI Gateway SLA 的独特挑战](#一ai-gateway-sla-的独特挑战)
- [二、SLA 的核心指标](#二sla-的核心指标)
- [三、SLA 的等级设计](#三sla-的等级设计)
- [四、可用性工程](#四可用性工程)
- [五、容灾与多活](#五容灾与多活)
- [六、限流与降级](#六限流与降级)
- [七、变更管理](#七变更管理)
- [八、事件响应](#八事件响应)
- [九、SLA 监控与报告](#九sla-监控与报告)
- [十、合规与审计](#十合规与审计)
- [十一、容量与成本治理](#十一容量与成本治理)
- [十二、未解难题与研究前沿](#十二未解难题与研究前沿)
- [十三、参考资料](#十三参考资料)

---

## 一、AI Gateway SLA 的独特挑战

### 1.1 LLM 调用固有的"非确定性"

| 挑战 | 描述 |
|---|---|
| **延迟波动** | 同模型同请求 P50 / P99 差 5-10x |
| **流式响应** | TTFT 单独算、E2E 单独算 |
| **模型可用性** | 上游 API 故障率 0.1-1% |
| **冷启动** | 自托管模型冷启动 5-30s |
| **限流** | 上游 rate limit 不可控 |
| **幻觉** | 质量波动 |
| **Token 限制** | 超长 prompt 失败 |
| **价格波动** | 模型价格可能变化 |

### 1.2 AI Gateway 自身的挑战

| 挑战 | 描述 |
|---|---|
| **多上游依赖** | 任何一个挂掉可能影响 |
| **多租户公平性** | 一个租户不能拖累其他 |
| **缓存一致性** | 多节点缓存如何同步 |
| **流式状态** | 长连接管理 |
| **冷启动** | 网关实例的冷启动 |

### 1.3 SLA 与传统服务的差异

| 维度 | 传统服务 | AI Gateway |
|---|---|---|
| **可用性目标** | 99.99% | 99.5-99.9% |
| **延迟稳定性** | P99 < 1.5x P50 | P99 < 5x P50 |
| **错误率** | < 0.01% | < 1% |
| **降级** | 几乎不发生 | 经常发生（fallback） |
| **回滚** | 简单 | 复杂（模型状态） |

---

## 二、SLA 的核心指标

### 2.1 SLI（Service Level Indicator）

| 类别 | 指标 | 测量方式 |
|---|---|---|
| **可用性** | 请求成功率 | 2xx / 总请求 |
| **延迟** | P50/P95/P99 | 响应时间 |
| **吞吐** | QPS / TPS | 成功请求数 / 时间 |
| **错误率** | 4xx/5xx 比例 | 错误 / 总 |
| **饱和度** | 资源使用率 | CPU/内存/GPU |

### 2.2 LLM 特有 SLI

| 指标 | 含义 |
|---|---|
| **TTFT P99** | 99% 请求首 token 延迟 < X |
| **TPOT P99** | 99% token 间延迟 < Y |
| **E2E P99** | 99% 端到端延迟 < Z |
| **缓存命中率** | 缓存 / 总请求 |
| **Fallback 触发率** | Fallback / 总请求 |
| **幻觉率** | 包含幻觉 / 总请求 |
| **Token 错误率** | Token 计算错误 / 总请求 |

### 2.3 SLO（Service Level Objective）

```yaml
# 典型 AI Gateway SLO
apiVersion: slo/v1
kind: ServiceLevelObjective
metadata:
  name: ai-gateway-slo
spec:
  service: ai-gateway
  
  objectives:
    # 可用性
    - name: availability
      sli: availability
      target: 99.9  # 99.9% 成功
      window: 30d
    
    # 延迟
    - name: ttft_p99
      sli: ttft
      target: 1000  # 1s
      percentile: 99
      window: 30d
    
    - name: e2e_p99
      sli: e2e_latency
      target: 5000  # 5s
      percentile: 99
      window: 30d
    
    # 业务
    - name: user_satisfaction
      sli: thumbs_up_rate
      target: 0.85
      window: 30d
```

### 2.4 Error Budget（错误预算）

```
错误预算 = (1 - SLO) × 时间窗口
       = (1 - 0.999) × 30 天 × 24 × 60
       = 0.001 × 43200 分钟
       = 43.2 分钟

意味着：30 天内可"消耗" 43 分钟的不可用时间
超出后：禁止发布新功能，专注稳定性
```

### 2.5 SLA 协议（Service Level Agreement）

```yaml
# 给客户的承诺
sla:
  uptime_guarantee: 99.9%
  
  compensation:
    - condition: "uptime < 99.9%"
      compensation: "10% 信用返还"
    - condition: "uptime < 99.0%"
      compensation: "25% 信用返还"
    - condition: "uptime < 95.0%"
      compensation: "50% 信用返还"
  
  exclusions:
    - 上游 LLM 提供商故障（按比例）
    - 客户原因
    - 不可抗力
```

---

## 三、SLA 的等级设计

### 3.1 分级 SLA

| 等级 | 可用性 | 延迟（P99） | 错误预算/月 | 价格 |
|---|---|---|---|---|
| **免费** | 99.0% | 5s | 7.2 小时 | 免费 |
| **基础** | 99.5% | 3s | 3.6 小时 | $X/月 |
| **企业** | 99.9% | 1.5s | 43 分钟 | $Y/月 |
| **关键** | 99.95% | 1s | 21 分钟 | $Z/月 |
| **专属** | 99.99% | < 500ms | 4 分钟 | 定制 |

### 3.2 按租户分级

```python
TENANT_SLA = {
    "free": {
        "availability": 0.99,
        "ttft_p99": 2000,
        "e2e_p99": 8000,
        "rate_limit_rpm": 60,
        "support": "community"
    },
    "pro": {
        "availability": 0.995,
        "ttft_p99": 1000,
        "e2e_p99": 5000,
        "rate_limit_rpm": 600,
        "support": "email"
    },
    "enterprise": {
        "availability": 0.999,
        "ttft_p99": 500,
        "e2e_p99": 2000,
        "rate_limit_rpm": 6000,
        "support": "24/7 phone"
    }
}
```

### 3.3 按功能分级

```python
# 不同功能不同 SLA
FEATURE_SLA = {
    "chat": {"availability": 0.99, "e2e_p99": 3000},
    "embeddings": {"availability": 0.995, "e2e_p99": 1000},
    "agent": {"availability": 0.98, "e2e_p99": 30000},  # 复杂任务
    "fine_tuned_inference": {"availability": 0.99, "e2e_p99": 5000}
}
```

---

## 四、可用性工程

### 4.1 可用性的数学

```
可用性 = MTBF / (MTBF + MTTR)
       = 平均无故障时间 / (平均无故障时间 + 平均修复时间)

99.9% 可用性：
  MTBF = 30 天
  MTTR < 43 分钟

99.99% 可用性：
  MTBF = 30 天
  MTTR < 4.3 分钟
```

### 4.2 提高可用性的方法

#### 方法 1：冗余

```
N+1：一台备用
N+2：两台备用
2N：完全双倍
2N+1：双倍 + 备用
```

**AI Gateway 推荐**：
- 关键组件 N+1 或 N+2
- 数据库 2N+1
- 缓存 N+1

#### 方法 2：健康检查

```python
class HealthChecker:
    def __init__(self, dependencies):
        self.dependencies = dependencies
    
    async def check_health(self):
        results = {}
        for dep in self.dependencies:
            try:
                start = time.time()
                ok = await dep.ping()
                latency = (time.time() - start) * 1000
                results[dep.name] = {
                    "healthy": ok,
                    "latency_ms": latency
                }
            except Exception as e:
                results[dep.name] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return results
```

#### 方法 3：自动恢复

```python
class AutoRecovery:
    def __init__(self):
        self.circuit_breakers = {}
    
    async def call_with_breaker(self, name, func):
        cb = self.circuit_breakers.get(name, CircuitBreaker())
        if cb.state == "open":
            raise CircuitOpenError()
        try:
            result = await func()
            cb.record_success()
            return result
        except Exception as e:
            cb.record_failure()
            if cb.failure_rate > 0.5:
                cb.open()
            raise
```

#### 方法 4：优雅降级

```python
class GracefulDegradation:
    async def process(self, request):
        try:
            # 1. 首选：完整 RAG + LLM
            return await self.full_pipeline(request)
        except UpstreamError:
            try:
                # 2. 降级：简化 RAG + 较小模型
                return await self.simplified_pipeline(request)
            except:
                try:
                    # 3. 兜底：纯 LLM
                    return await self.llm_only(request)
                except:
                    # 4. 静态响应
                    return self.cached_fallback(request)
```

#### 方法 5：消除单点

```
检查清单
├── 网关实例 ≥ 3（避免单点）
├── 数据库主从（避免主库单点）
├── Redis Cluster（避免 Redis 单点）
├── 多个上游 LLM provider（避免单家故障）
├── 多区域部署（避免区域故障）
└── 多 CDN（避免 CDN 故障）
```

---

## 五、容灾与多活

### 5.1 容灾等级

| 等级 | RPO（数据丢失） | RTO（恢复时间） | 成本 |
|---|---|---|---|
| **本地冗余** | 0 | 秒级 | 低 |
| **同城容灾** | 秒级 | 分钟级 | 中 |
| **异地容灾** | 分钟级 | 小时级 | 高 |
| **异地多活** | 秒级 | 0（自动切换） | 极高 |

### 5.2 AI Gateway 的容灾架构

```
                ┌──────────────────────┐
                │  Global Load Balancer │
                │  (Route53 / Cloudflare)│
                └──────────┬───────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │ US-East │       │ US-West │       │ EU-West │
   │ 主区域  │       │ 主区域  │       │ 主区域  │
   └────┬────┘       └────┬────┘       └────┬────┘
        ↓                  ↓                  ↓
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │ US-East │       │ US-West │       │ EU-West │
   │ 备区域  │       │ 备区域  │       │ 备区域  │
   └─────────┘       └─────────┘       └─────────┘
```

### 5.3 Active-Active vs Active-Passive

#### Active-Active

```
两个区域都接收流量
├── 优点：利用率高、故障切换快
├── 缺点：数据同步复杂、成本高
└── 适用：全球用户、关键业务
```

#### Active-Passive

```
主区域接收流量，备区域待命
├── 优点：简单
├── 缺点：浪费资源、切换慢
└── 适用：中小企业
```

### 5.4 数据库复制

```python
# 主从复制
class DatabaseConfig:
    # 写主库
    primary = "postgres-primary.example.com"
    # 读从库
    replicas = [
        "postgres-replica-1.example.com",
        "postgres-replica-2.example.com"
    ]
    
    @classmethod
    def get_read_url(cls):
        return random.choice(cls.replicas)
    
    @classmethod
    def get_write_url(cls):
        return cls.primary
```

### 5.5 流量切换

```python
class TrafficFailover:
    def __init__(self, primary, secondary):
        self.primary = primary
        self.secondary = secondary
        self.current = primary
        self.health_checker = HealthChecker([primary, secondary])
    
    async def should_failover(self):
        health = await self.health_checker.check_health()
        if not health[self.current]["healthy"]:
            # 主区不健康
            if health[self.secondary]["healthy"]:
                return True
        return False
    
    async def failover(self):
        self.current = self.secondary if self.current == self.primary else self.primary
        # 通知 DNS / LB
        await self.dns.update(self.current)
```

---

## 六、限流与降级

### 6.1 多级限流

```
限流层级
├── 1. 用户级（每个用户每分钟 N 次）
├── 2. 租户级（每个租户总配额）
├── 3. API Key 级（每个 key）
├── 4. 模型级（每个上游 provider）
├── 5. 全局（总流量）
└── 6. 突发保护（防止瞬间洪峰）
```

### 6.2 限流算法

#### Token Bucket

```python
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def allow(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

#### Sliding Window

```python
class SlidingWindow:
    def __init__(self, window_size, max_requests):
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = []
    
    def allow(self):
        now = time.time()
        # 移除窗口外的请求
        self.requests = [r for r in self.requests if now - r < self.window_size]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
```

### 6.3 限流维度

```python
class RateLimiter:
    def __init__(self, redis):
        self.redis = redis
    
    async def check(self, key, limit, window):
        """分布式限流"""
        now = time.time()
        window_start = now - window
        
        # 使用 Redis sorted set
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, int(window) + 1)
        
        results = await pipe.execute()
        count = results[2]
        
        if count > limit:
            return False
        return True
```

### 6.4 降级策略

```python
class DegradationPolicy:
    async def execute(self, request):
        if self.is_normal_load():
            return await self.full_service(request)
        elif self.is_heavy_load():
            # 降级 1：禁用大模型，只用小模型
            return await self.small_model_only(request)
        elif self.is_overload():
            # 降级 2：返回缓存
            cached = await self.cache.get(request)
            if cached:
                return cached
            # 降级 3：返回兜底
            return self.fallback_response()
        elif self.is_emergency():
            # 紧急：只服务 VIP 用户
            if request.user_tier in ["vip", "enterprise"]:
                return await self.full_service(request)
            return self.queue_response()
```

### 6.5 排队与公平

```python
class FairQueue:
    """多租户公平排队"""
    
    def __init__(self, quotas):
        self.quotas = quotas  # {"tenant-A": 100, "tenant-B": 50}
        self.queues = defaultdict(deque)
    
    def enqueue(self, tenant_id, request):
        if len(self.queues[tenant_id]) >= self.quotas[tenant_id]:
            return False  # 队列满
        self.queues[tenant_id].append(request)
        return True
    
    def dequeue(self):
        """按权重选下一个"""
        # 简单：轮询
        for tenant_id in self.quotas:
            if self.queues[tenant_id]:
                return self.queues[tenant_id].popleft()
        return None
```

---

## 七、变更管理

### 7.1 变更类型

| 变更 | 风险 | 流程 |
|---|---|---|
| **配置变更** | 低 | PR + Review |
| **网关代码变更** | 中 | PR + 测试 + 灰度 |
| **新增 provider** | 中 | 测试 + 灰度 |
| **路由策略变更** | 高 | 灰度 + 监控 |
| **模型升级** | 高 | 灰度 + A/B + 回滚预案 |
| **基础设施变更** | 高 | 演练 + 维护窗口 |

### 7.2 灰度发布

```python
class CanaryDeploy:
    def __init__(self, old_version, new_version, stages):
        # stages: [{"traffic": 0.05, "duration": "1h"}, ...]
        self.old = old_version
        self.new = new_version
        self.stages = stages
        self.current_stage = 0
    
    def traffic_split(self):
        if self.current_stage < len(self.stages):
            return self.stages[self.current_stage]["traffic"]
        return 1.0  # 全量
    
    async def should_advance(self, metrics):
        # 1. 错误率 < 阈值
        if metrics["new_error_rate"] > metrics["old_error_rate"] * 1.5:
            return False
        # 2. 延迟 < 阈值
        if metrics["new_p99"] > metrics["old_p99"] * 1.2:
            return False
        return True
```

### 7.3 Feature Flag

```python
class FeatureFlags:
    def __init__(self, redis):
        self.redis = redis
    
    async def is_enabled(self, flag, user_context):
        # 1. 全局开关
        if not await self.redis.get(f"flag:{flag}:global"):
            return False
        
        # 2. 租户开关
        if not await self.redis.get(f"flag:{flag}:tenant:{user_context.tenant_id}"):
            return False
        
        # 3. 百分比发布
        percentage = int(await self.redis.get(f"flag:{flag}:percentage") or 0)
        if hash(user_context.user_id) % 100 >= percentage:
            return False
        
        return True
```

### 7.4 回滚

```python
class RollbackManager:
    async def rollback(self, deployment_id):
        # 1. 切流量回旧版本
        await self.lb.update_traffic(deployment_id, percentage=0)
        
        # 2. 等待新版本流量归零
        await asyncio.sleep(30)
        
        # 3. 关闭新版本
        await self.k8s.scale(deployment_id, replicas=0)
        
        # 4. 记录事件
        await self.audit_log("rollback", deployment_id)
```

### 7.5 变更前检查清单

```yaml
pre_deploy_checklist:
  - name: tests_pass
    description: 所有测试通过
    required: true
  
  - name: performance_test
    description: 性能测试无回归
    required: true
  
  - name: security_scan
    description: 安全扫描无新增漏洞
    required: true
  
  - name: rollback_plan
    description: 回滚方案明确
    required: true
  
  - name: monitoring_ready
    description: 监控已配置
    required: true
  
  - name: on_call_aware
    description: 值班人员已通知
    required: true
```

---

## 八、事件响应

### 8.1 事件分级

| 等级 | 描述 | 响应时间 | 处理时长 |
|---|---|---|---|
| **P0** | 全部故障 | < 5 分钟 | < 1 小时 |
| **P1** | 主要功能故障 | < 15 分钟 | < 4 小时 |
| **P2** | 部分功能受影响 | < 1 小时 | < 24 小时 |
| **P3** | 轻微问题 | < 24 小时 | 下个迭代 |
| **P4** | 优化建议 | < 1 周 | 待规划 |

### 8.2 事件响应流程

```
[1. 检测] (alert / 用户反馈)
    ↓
[2. 确认] (值班人员验证)
    ↓
[3. 分级] (P0/P1/P2/P3)
    ↓
[4. 通知] (Slack / 邮件 / 短信)
    ↓
[5. 启动响应] (Incident Commander)
    ↓
[6. 诊断] (查监控 / 日志)
    ↓
[7. 缓解] (回滚 / 限流 / 切流量)
    ↓
[8. 根因分析] (RCA)
    ↓
[9. 修复] (代码 / 配置)
    ↓
[10. 复盘] (Postmortem)
    ↓
[11. 预防] (改进 / 告警)
```

### 8.3 关键 Runbook

```yaml
# runbook-upstream-failure.yaml
name: 上游 LLM 提供商故障
symptoms:
  - 上游错误率突增
  - 多个模型同时失败
  - 用户反馈大量失败

diagnosis:
  - 检查上游 status page
  - 检查我们的错误日志
  - 检查上游 API 响应

mitigation:
  - 1. 启用 fallback provider
  - 2. 启用缓存响应
  - 3. 启用降级模式

recovery:
  - 1. 监控上游恢复
  - 2. 逐步切回
  - 3. 验证正常

postmortem:
  - 影响范围
  - 时间线
  - 根本原因
  - 改进措施
```

### 8.4 值班制度

```yaml
on_call_schedule:
  rotation: weekly
  primary: ["alice", "bob", "charlie", "diana"]
  secondary: ["eve", "frank"]
  
  # 主备值班
  primary_responder: "primary"
  secondary_responder: "secondary"
  
  # 升级链
  escalation:
    - level: 1
      role: "primary"
      timeout: "5m"
    - level: 2
      role: "secondary"
      timeout: "10m"
    - level: 3
      role: "manager"
      timeout: "15m"
```

---

## 九、SLA 监控与报告

### 9.1 实时监控

```yaml
# Prometheus 告警规则
groups:
- name: ai-gateway-sla
  rules:
  - alert: SLOAvailabilityAtRisk
    expr: |
      (sum(rate(gateway_requests_total{status=~"2.."}[5m])) / 
       sum(rate(gateway_requests_total[5m]))) < 0.999
    for: 5m
    annotations:
      summary: "可用性可能违反 SLO"
  
  - alert: SLOBudgetBurnRate
    expr: |
      (1 - (sum(rate(gateway_requests_total{status=~"2.."}[1h])) / 
             sum(rate(gateway_requests_total[1h])))) * 24 > 14.4
    for: 5m
    annotations:
      summary: "错误预算消耗过快"
```

### 9.2 SLO 报告

```python
class SLOReport:
    def __init__(self, period):
        self.period = period  # "30d"
    
    def generate(self):
        report = {
            "period": self.period,
            "slis": self.collect_slis(),
            "slo_compliance": {},
            "error_budget": {},
            "incidents": self.get_incidents(),
            "trends": self.get_trends()
        }
        
        for slo in self.slos:
            actual = self.compute_slo(slo)
            compliance = actual >= slo.target
            report["slo_compliance"][slo.name] = {
                "target": slo.target,
                "actual": actual,
                "compliant": compliance
            }
            
            budget_used = (slo.target - actual) / slo.target
            report["error_budget"][slo.name] = {
                "remaining": 1 - budget_used,
                "burn_rate": self.compute_burn_rate(slo)
            }
        
        return report
```

### 9.3 SLO 仪表盘

```
┌────────────────────────────────────────┐
│  SLO 30 天状态                          │
│  ════════════════════════════════════  │
│                                        │
│  可用性 SLO 99.9%                      │
│  ████████████████████████████░░ 99.85% │
│  错误预算剩余: 14% (低)                 │
│  烧损率: 2.1x (高)                     │
│                                        │
│  TTFT P99 SLO 1000ms                   │
│  ██████████████████████████████ 850ms  │
│  错误预算剩余: 85% (高)                 │
│  烧损率: 0.3x (低)                     │
│                                        │
│  E2E P99 SLO 5000ms                    │
│  ████████████████████████░░░░░ 4200ms  │
│  错误预算剩余: 35% (中)                 │
│  烧损率: 1.5x (中)                     │
└────────────────────────────────────────┘
```

### 9.4 SLA 客户报告

```python
class CustomerSLAReport:
    def generate(self, tenant_id, period):
        return {
            "tenant": tenant_id,
            "period": period,
            "guarantees": {
                "availability": {
                    "guaranteed": 0.999,
                    "actual": 0.9994,
                    "credit": 0
                },
                "ttft_p99": {
                    "guaranteed": 1000,
                    "actual": 850,
                    "credit": 0
                }
            },
            "usage": {
                "total_requests": 1_234_567,
                "total_tokens": 89_000_000,
                "total_cost_usd": 1234.56
            },
            "incidents_impacting_you": [
                {
                    "id": "INC-2025-12-01",
                    "date": "2025-12-01",
                    "duration_min": 12,
                    "impact": "部分请求超时"
                }
            ]
        }
```

---

## 十、合规与审计

### 10.1 合规框架

| 框架 | 适用 |
|---|---|
| **GDPR** | 欧盟用户数据 |
| **CCPA** | 加州用户 |
| **HIPAA** | 医疗数据 |
| **SOC 2** | SaaS 审计 |
| **ISO 27001** | 信息安全 |
| **等保 2.0** | 中国大陆 |
| **PCI-DSS** | 支付数据 |

### 10.2 审计日志

```python
class AuditLogger:
    def log_request(self, request, response, user_context):
        self.db.insert({
            "timestamp": time.time(),
            "user_id": user_context.user_id,
            "tenant_id": user_context.tenant_id,
            "action": "llm_request",
            "request_hash": hash_request(request),
            "response_hash": hash_response(response),
            "model": request.model,
            "tokens": response.usage.total_tokens,
            "cost": response.cost,
            "ip_address": user_context.ip,
            "user_agent": user_context.user_agent,
            "request_id": request.id,
        })
    
    def log_admin_action(self, admin, action, target):
        self.db.insert({
            "timestamp": time.time(),
            "user_id": admin.id,
            "action": action,
            "target": target,
            "ip": admin.ip
        })
```

### 10.3 数据保留

```python
RETENTION_POLICY = {
    "request_logs": 90,        # 90 天
    "response_logs": 30,       # 30 天
    "audit_logs": 7 * 365,     # 7 年
    "pii_logs": 0,             # 立即删除
    "billing": 7 * 365,        # 7 年（财务要求）
}
```

### 10.4 数据删除（GDPR Right to be Forgotten）

```python
class DataDeletion:
    async def delete_user_data(self, user_id):
        # 1. 主数据库
        await self.db.delete_user(user_id)
        
        # 2. 日志
        await self.logs.delete_user_logs(user_id)
        
        # 3. 缓存
        await self.cache.delete_user_cache(user_id)
        
        # 4. 备份
        await self.backups.schedule_user_deletion(user_id, grace_period=30)
        
        # 5. 记录
        await self.audit_log("gdpr_deletion", user_id)
```

---

## 十一、容量与成本治理

### 11.1 容量治理

```python
class CapacityGovernance:
    """容量规划与治理"""
    
    def __init__(self):
        self.thresholds = {
            "warn": 0.7,
            "critical": 0.85,
            "block": 0.95
        }
    
    async def check(self, metric, current):
        threshold = self.thresholds.get(self.thresholds)
        if current > 0.95:
            return "block"
        elif current > 0.85:
            return "scale_up_immediate"
        elif current > 0.7:
            return "scale_up_planned"
        return "ok"
```

### 11.2 成本治理

```python
class CostGovernance:
    async def check_budget(self, tenant_id, estimated_cost):
        # 1. 月度预算检查
        if await self.is_over_budget(tenant_id, estimated_cost):
            return "block"
        
        # 2. 速率检查（防止突增）
        if await self.is_rate_too_high(tenant_id):
            return "rate_limit"
        
        # 3. 异常检查
        if await self.is_anomalous(tenant_id):
            return "require_approval"
        
        return "allow"
```

### 11.3 容量与成本的平衡

```
高可用 ↔ 低成本
├── 高可用需要冗余
├── 冗余 = 额外成本
└── 平衡：用 "刚好够" 的冗余 + 弹性
```

---

## 十二、未解难题与研究前沿

### 12.1 SLA 设计

1. **AI Gateway 的合理 SLO** 是什么？
2. **流式响应的 SLA** 怎么定
3. **Agent 多步调用** 的 SLA
4. **客户 SLA** vs 内部 SLA 的差异
5. **SLA 违反** 的自动补救

### 12.2 容灾

6. **跨云容灾** 的实现
7. **数据库多活** 的数据一致性
8. **流式响应状态** 的灾备
9. **AI Gateway 自身的灾备演练**
10. **大模型故障** 的快速切换

### 12.3 变更

11. **零停机** 的网关升级
12. **微调模型** 的无缝切换
13. **路由策略** 的热更新
14. **配置变更** 的原子性
15. **回滚的边界** 控制

### 12.4 监控

16. **流式响应的实时监控** 难题
17. **多租户公平** 的监控
18. **GPU 利用率** 的细粒度监控
19. **异常检测** 的算法
20. **根因分析** 的自动化

### 12.5 合规

21. **AI 法规**（EU AI Act）的技术落地
22. **跨境数据传输** 的合规审计
23. **数据最小化** 的实现
24. **AI 决策可解释性** 的要求
25. **AI 输出责任** 的归属

### 12.6 未来

26. **AI 网关自治**（自愈、自优化）
27. **预测性维护**
28. **AI 辅助的事件响应**
29. **"零信任" 在 AI 网关中的实现**
30. **AI SLA 经济学** 的理论化

---

## 十三、参考资料

### 13.1 SLA / SLO 实践

- Google SRE Book
- "Site Reliability Engineering" (O'Reilly)
- "Implementing Service Level Objectives" (O'Reilly)
- sloth.dev (SLO 工具)

### 13.2 工具

- Prometheus + Alertmanager
- Grafana
- PagerDuty / Opsgenie
- StatusPage
- incident.io
- FireHydrant

### 13.3 标准

- ISO 27001
- SOC 2
- GDPR
- EU AI Act
- 中国《生成式人工智能服务管理暂行办法》

### 13.4 关键博客

- Google Cloud "SLO 实践"
- AWS "Well-Architected Framework"
- Microsoft "Azure SRE"
- "The Art of SLOs"

### 13.5 案例

- OpenAI 99.9% SLA
- Anthropic 99.9% SLA
- Cloudflare 100% SLA（限部分产品）

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 批 · 第 9 篇
- 主题：AI 网关的 SLA 与服务治理
- 上一份：18-fine-tuning-personalization.md
- 下一份预告：AI 网关的未来形态（2027-2030）
