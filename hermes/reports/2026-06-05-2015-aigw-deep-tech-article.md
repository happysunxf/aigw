# AI 网关（AI Gateway）2025-2026 深度技术剖析

> **作者**：aigw 调研团队
> **抓取时间**：2026-06-05 20:15 CST
> **数据基线**：仓库 50+ 份调研报告（13 份 cron 自动化 + 30 份主题深挖 + 10 份产品深挖）
> **GitHub 主仓**：https://github.com/happysunxf/aigw
> **范围**：协议层 / 产品矩阵 / 架构 / 安全 / 可观测 / 选型 / 未来 6-12 个月展望

---

## 第 1 章 · 行业定调：为什么 AI 网关从"路由器"长成"三件套"

### 1.1 一句话行业定调

**AI 网关从"LLM 路由器"演化成了"AI 智能体基础设施"——同时承担模型路由、Agent 编排、MCP 治理、Guardrails、可观测四件事。** 2025-2026 是分水岭年，**"Agent Gateway" 和 "MCP Gateway" 成为独立产品品类**，**整合潮**开始：Palo Alto Networks 收购 Portkey、Mintlify 收购 Helicone、agentgateway 加入 AAIF（Linux Foundation 旗下第 4 个 hosted 项目）。

### 1.2 时间线

```
2024 Q4  Anthropic 提出 MCP（Model Context Protocol）——"AI 万能转接头"协议
2025 Q1  Portkey 推出 Agent Gateway 独立产品线
2025 Q3  Helicone 完成 14.2T token 处理（"被收购前夜"）
2025 Q4  Envoy AI Gateway v0.4.0 GA、Portkey 被 PANW 收购
2026 Q1  Helicone 被 Mintlify 收购（2026-03-03）、OpenRouter 100T token/月
2026 Q2  Envoy AI Gateway v0.6.0（5-05）首标 production-ready
2026 Q2  agentgateway 加入 AAIF（6-04）、MCP 2026-07-28 RC 协议级重构
2026 Q3  [预测] MCP 7-28 RC 转 GA、Auth IG Tool Scopes WG 出 spec
```

### 1.3 三大产品类别边界

| 类别 | 解决什么问题 | 代表产品 |
|---|---|---|
| **LLM Gateway** | 多模型路由、协议翻译、成本优化、可观测 | LiteLLM、Portkey、OpenRouter、Helicone AI GW |
| **MCP Gateway** | 统一管理 MCP server/tool、鉴权、审计、限流 | Envoy AI Gateway（MCPRoute）、IBM mcp-context-forge、Archestra、ToolHive |
| **Agent Gateway** | 多步 agent 编排、step-level trace、成本归因到 agent run | Portkey Agent Gateway、TrueFoundry、agentgateway |

**2026 关键趋势**：三个类别**正在合并到同一个产品**——比如 Envoy AI GW v0.6.0 同时提供 `AIGatewayRoute`（LLM 路由）+ `MCPRoute`（MCP 路由）；Portkey 同时提供 LLM GW + Agent GW + MCP Governance + Skills Registry 四件套。

---

## 第 2 章 · 主流产品矩阵（10 款）

### 2.1 全景速查表

| 产品 | 形态 | 仓库 | 协议支持 | MCP | Wasm | RPS/单核 | CVE 响应 |
|---|---|---|---|---|---|---|---|
| **Higress** | 开源 + 商业 | alibaba/higress (8.5k★) | 50+ provider | ✅ Mcp Bridge | ✅ 一等公民 | 30-50 万 | 自维护 |
| **Envoy AI GW** | K8s CRD | envoyproxy/ai-gateway (1.7k★) | 4 厂商互译 | ✅ v1beta1 | ✅ | 30-50 万 | 周级（依赖上游）|
| **kgateway** | K8s | kgateway-dev/kgateway | OpenAI 兼容 | ❌ | ⚠️ 手写 | 30-50 万 | **24h** |
| **LiteLLM** | Python | BerriAI/litellm | 250+ provider | ⚠️ v1.88 计划 | ❌ | 200-800 | Python 生态 |
| **Portkey** | Node | Portkey-AI/gateway (12k★) | 250+ provider | ✅ mcp-tool-filter | ❌ | 1k-3k | Node 生态 |
| **Helicone AI GW** | Rust | Helicone/ai-gateway (594★) | 100+ provider | — | — | — | — |
| **Kong AI GW** | 商业 + 开源 | Kong/kong | 主流 provider | — | ✅ | — | 商业支持 |
| **Cloudflare AI GW** | SaaS | — | 主流 provider | — | ❌ | — | Cloudflare |
| **OpenRouter** | SaaS | — | 60+ provider / 400+ 模型 | — | ❌ | — | — |
| **One API** | 开源 | songquanpeng/one-api | 聚合 LLM API | — | — | — | — |

### 2.2 三个梯队的边界

#### **百万 RPS 真网关**
- **代表**：Envoy AI Gateway、Higress、kgateway
- **架构形态**：Envoy 系（数据面） + K8s CRD（配置面）
- **典型场景**：大厂生产环境、K8s 原生部署、多协议翻译
- **代价**：K8s 团队、controller 运维成本

#### **应用层 SDK 网关**
- **代表**：LiteLLM、Portkey、Helicone AI GW
- **架构形态**：进程内代理（Python / Node / Rust）+ SDK 翻译
- **典型场景**：快速集成、25+ 模型切换、Guardrails 编排
- **代价**：单进程 200-3000 RPS（~1000x 差距）

#### **聚合市场 / 边缘**
- **代表**：OpenRouter、Cloudflare AI GW、One API
- **架构形态**：SaaS 优先 / Workers 边缘
- **典型场景**：个人开发者、小团队、多模型路由现成用
- **代价**：定制能力弱、数据出境

### 2.3 关键产品深度卡片

#### **Envoy AI Gateway v0.6.0（2026-05-05）**

**核心 CRD 全升 v1beta1**：`AIGatewayRoute / AIServiceBackend / BackendSecurityPolicy / GatewayConfig / MCPRoute`。**首个 production-ready API 表面**。

**杀手锏**：
- **跨 provider 翻译**：Anthropic `/v1/messages` 端点可暴露在任意 OpenAI 后端前面
- **统一 `reasoning_effort` 跨 Anthropic/OpenAI/Gemini** 一把旋钮
- **Adaptive thinking for `claude-opus-4.6`** 网关端到端翻译
- **GKE Workload Identity via ADC** —— 落地 GKE 可摘掉静态 SA JSON secret

**仓库健康**：1,717 stars / 269 forks / 154 open issues，CNCF + Apache-2.0。

**两条 breaking change**：
1. `AIGatewayRoute.spec.filterConfig` 整字段删除 → 必须搬 `GatewayConfig`
2. `VersionedAPISchema.version` 不再当 endpoint 前缀 → 用 `prefix` 字段

#### **Higress v2.2.2（2026-05-26）**

**37 项变更 + 13 新特性**。国内唯一同时具备"完整 API 网关 + 完整 AI 网关 + 完整中文 + 商业支持"。

**杀手锏**：
- **`modelToHeader` 默认 `x-higress-llm-model-final`** —— 模型映射后下游限流/计费能拿到真实匹配
- **nginx-rewrite 兼容 WASM 插件**（PR #3823）—— 主动用 WASM sandbox 替换直接执行 nginx rewrite，**修 CVE-2026-42945**（Nginx 18 年老洞 CVSS 9.2）
- **Bedrock Provider 直连 Mantle Anthropic Messages API**（去掉 OpenAI→Converse 双跳翻译）
- **KlingAI 视频生成 provider**（OpenAI 兼容 + 原生双协议）
- **`cooldownDuration`** —— API key 失败后自动 cooldown（不靠真实请求做健康检查，省 token）

**企业版**："90%+ 性能优化、节省 50% 资源成本、7×24 工单 + 钉群"。

#### **LiteLLM v1.87.1 / v1.88.0-rc.2（2026-06-04）**

**2 天一 release 节奏**——5 月内 6 个 tag（v1.88.0-rc.1 / v1.87.0 / v1.86.3 / v1.85.4 / v1.85.3 / v1.84.5）。

**v1.88.0-rc.2 关键**：
- **`fix(key_generate): harden GHSA-q775 session-token exemption against default_key_generate_params`**
- typed OpenTelemetry semconv
- MCP stateless+stateful 双模
- A2A agent-card 发现
- 所有 Docker 镜像 **cosign 签名**

**支持**：100+ LLM 供应商、OpenAI 输入/输出格式转换、retry/fallback、batches、embeddings、images、audio。

#### **OpenRouter（截至 2026-06）**

**规模**：月 **100T tokens**、**8M+ 用户**、**60+ 提供商**、**400+ 模型**。

**自我定位**："Started in early 2023 as the **first LLM marketplace**, OpenRouter has grown to become the **largest and most popular AI gateway**"。

**2026 年新发布**：
- **Speech/transcription APIs**
- **Model Fusion**（多模型融合推理）
- Private models
- Enterprise workspace controls
- 20 new models（Gemini 3.5 Flash、Claude Opus 4.8）
- **Guardrails**：budget enforcement、zero data retention、model/provider restrictions

**API 直暴露**：
- `provider.sort = {Price|Throughput|Latency|Exacto}` —— 把"挑模型"做成 API 参数
- `provider.zdr`（Zero Data Retention 兜底）
- `provider.only` / `provider.ignore` / `provider.require_parameters`

---

## 第 3 章 · Envoy AI Gateway 深度拆解

### 3.1 v0.6.0 的关键意义

v0.6.0 是 **Envoy AI Gateway 第一个 production-ready 版本**。判断依据：

1. **5 个核心 CRD 全部 v1beta1** —— 字段冻结承诺，下游工具链可依赖
2. **MCP v1beta1** —— 4-30 升 v1beta1，几乎和 IBM mcp-context-forge v1.0.0 GA **同一天**
3. **GKE Workload Identity via ADC** —— 落地 GKE 不再需 SA JSON
4. **`aigw` CLI 自动 OTLP access logging** —— 开箱即用
5. **response model metadata** —— 真实模型名回写（多后端 fallback 场景下能区分）

### 3.2 5 个核心 CRD 全字段拆解

#### 3.2.1 `AIGatewayRoute` —— 核心路由 CR

- **资源位置**：cluster-scoped（v0.6.0 起支持 host-based，PR #2160）
- **核心字段**：
  - `spec.rules[]` —— **上限 15**（kubebuilder `MaxItems: 15`，根因 Gateway API 限 `maxItems: 16` + 1 catch-all）
  - `spec.targetRefs[]` —— 指向 Gateway
  - `spec.backendRefs[]` —— 指向 AIServiceBackend
  - `spec.modelAliases` —— 路径模型名映射
  - `spec.timeout` / `spec.retry` —— 标准 Gateway API 字段
- **breaking**：`spec.filterConfig` 整字段删除 → 迁 `GatewayConfig`

#### 3.2.2 `AIServiceBackend` —— 模型后端

表示一个具体的 LLM provider endpoint。

- 字段：
  - `spec.backendRef` —— K8s Service ref
  - `spec.modelName` —— 实际模型名（vs 暴露给客户端的 alias）
  - `spec.versionedAPISchema` —— **`version` 字段不再当 prefix**（breaking），用 `prefix` 显式声明
- 例子：Gemini 实际 endpoint 是 `/v1beta/openai/chat/completions` → `prefix: /v1beta/openai`

#### 3.2.3 `BackendSecurityPolicy` —— 后端鉴权

- 字段：
  - `spec.type: APIKey` / `AWS` / `Azure` / `Anthropic` / `GCPCredentials`
  - `spec.credentialsRef` —— 指向 K8s Secret
  - **GKE Workload Identity via ADC**（v0.6.0 新）—— 不再需 SA JSON secret
- 落地 GKE 可摘掉静态 SA JSON secret

#### 3.2.4 `GatewayConfig` —— 过滤器配置（新家）

替代被删的 `AIGatewayRoute.spec.filterConfig`。

- 通过注解 `aigateway.envoyproxy.io/gateway-config` 关联
- 字段：
  - `spec.globalLLMRequestCosts` —— **全局默认 cost**（v0.6.0 新）
  - `spec.routeLevelLLMRequestCosts` —— route 级 override
  - `spec.tokenCosts` —— 多种 cost type：`InputToken` / `OutputToken` / `CachedInputToken` / `ReasoningToken`（v0.6.0 新独立 cost type）

#### 3.2.5 `MCPRoute` —— MCP 路由（v1beta1）

4-30 升 v1beta1（PR #2090）。

- 字段：
  - `spec.rules[].matches[]` —— MCP method matching（`tools/list` / `tools/call` 等）
  - `spec.rules[].backendRefs[]` —— 指向 MCP server
  - **`MCPRouteBackendRef`**：
    - `forwardHeaders` —— **按 backend 的 header 透传**（每个 upstream 收到不同 trace context / tenant id）
    - `oidc` —— OAuth config
  - **`MCPRouteOAuth`**：
    - `claimToHeaders` —— **JWT claim → outbound header**（网关验完 JWT 注入 upstream）
  - **`MCPToolFilter`**：
    - `include` / `exclude` / `excludeRegex` —— deny 模式
- access log + response metadata 加 `mcp_tool_name` —— **per-tool 调试和计费**

### 3.3 协议翻译机制

Envoy 主线不支持 LLM 协议，所以走 **External Processor 模式**：

```
Client → Envoy → ext-proc (Go) → Provider API
       ← Envoy ← ext-proc    ←
```

- ext-proc 进程（Go 实现）跑在 K8s controller pod 里
- 协议转换在 ext-proc 里完成：**OpenAI ↔ Anthropic ↔ Gemini ↔ Bedrock** 之间任意翻译
- 关键能力：
  - `/v1/messages` (Anthropic) ↔ `/v1/chat/completions` (OpenAI) ↔ Vertex AI ↔ Bedrock Converse
  - 统一 `reasoning_effort` 跨三厂商：
    - Anthropic → thinking budget tokens
    - OpenAI → reasoning_tokens 字段
    - Gemini 3 → thinking_config.thinking_budget
  - prefix 缓存对齐：Anthropic `cache_control` / Gemini `cached_content` / OpenAI prompt caching

### 3.4 v0.6.0 两条 breaking change 详解

#### Breaking 1：`AIGatewayRoute.spec.filterConfig` 删除

- 原因：filter 配置和 route 配置耦合导致 complexity 上升
- 迁移：把 filter 配置搬到 `GatewayConfig` 资源
- 注解关联：`aigateway.envoyproxy.io/gateway-config`
- 时间窗口：v0.6.0 release notes 给出 1-2 个 minor 的兼容期

#### Breaking 2：`VersionedAPISchema.version` 不再当 prefix

- 原因：旧实现把 version 当 endpoint 前缀拼出 URL，但不同 provider 的 prefix 规则不一样
- 迁移：用 `prefix` 字段显式声明
- 例子：
  ```yaml
  # 旧
  spec:
    versionedAPISchema:
      name: OpenAI
      version: v1beta/openai  # 旧实现把它当 prefix 拼
  
  # 新
  spec:
    versionedAPISchema:
      name: OpenAI
      prefix: /v1beta/openai  # 显式 prefix
  ```
- 实际应用：
  - Gemini → `prefix: /v1beta/openai`
  - Cohere → `prefix: /compatibility/v1`

---

## 第 4 章 · MCP 协议 2026-07-28 RC 深度拆解 ⭐ 核心章

### 4.1 7 大主变更

| # | SEP 编号 | 变更 | 协议层影响 | 网关工程影响 |
|---|---|---|---|---|
| 1 | SEP-2567 | 移除 `Mcp-Session-Id` 头 | Streamable HTTP 去掉协议级 session | 网关无法再做"session 粘性路由"，需用 `_meta.state` 替代 |
| 2 | SEP-2575 | MCP 强制 stateless（移除 `initialize` / `notifications/initialized`） | 每次请求必须带 `protocolVersion` / `clientInfo` / `clientCapabilities` | 网关必须支持**每次请求都做协议版本协商**（缓存可省） |
| 3 | SEP-2631 | 新增 `server/discover` RPC | 服务器必须实现，客户端可声明支持的协议版本/能力 | 网关多了一个**早期拦截点**（`server/discover` 阶段就能做策略判定） |
| 4 | SEP-2575 | 替换订阅模型 | `resources/subscribe` → `subscriptions/listen`（单个长连接 POST-response 流） | 网关要支持**按订阅类型 opt-in 多路复用流** |
| 5 | SEP-2596 | 移除 `ping` / `logging/setLevel` / `notifications/roots/list_changed` | log level 改用 `_meta` 按请求设置 | 网关无需维护连接级 log 状态机 |
| 6 | SEP-2663 | Tasks 移出核心 | 变官方扩展；用 `tasks/get` 轮询 + `tasks/update` 输入 | 网关把 tasks 当**普通扩展**处理即可 |
| 7 | SEP-2322 | MRTR 模式取代 server-initiated 请求 | `roots/list` / `sampling/createMessage` / `elicitation/create` 改用 `inputRequests` + `inputResponses` | OTel 因果链**必须支持嵌套**（服务器发起的请求变成客户端下一跳的元数据） |

### 4.2 协议级隐藏影响

#### 4.2.1 客户端 SDK 的破坏性升级

- `Mcp-Session-Id` 移除 → **所有 SDK 缓存的 session 概念必须重构**
- `initialize` 移除 → **所有 SDK 握手逻辑必须改成"每次请求自带 `_meta`"**
- **影响范围**：Anthropic 官方 SDK / MCP Inspector / ToolHive / 一切第三方客户端
- **生产警示**：6-28 之前不要依赖 `Mcp-Session-Id`，否则 RC → GA 切换时直接挂

#### 4.2.2 网关统计/计费"抓手"变了

**v0（2025-11-25）** 的网关能用 `Mcp-Session-Id` 做：
- 速率限制（per session）
- 配额（per session token 消耗）
- 审计（session 维度的调用链）

**v1（2026-07-28 RC）** 的网关只能用：
- `_meta.clientInfo.id` —— 客户端身份
- `_meta.protocolVersion` —— 协议版本
- **新生成 `Mcp-Request-Id` 头**（建议加，但 spec 未强制）—— 每次请求的追踪 ID

**架构师决策点**：v1 网关必须把"session 粘性"逻辑改成"无状态 + 元数据路由"。

#### 4.2.3 `server/discover` 缓存（PR #2855 merged 6-04）

```typescript
// PR #2855 核心变更（伪代码）
class DiscoverCache {
  private cache = new Map<string, DiscoverResult>();
  
  async get(server: McpServer, options: { ttlMs?: number }) {
    const key = `${server.endpoint}|${server.headers?.host}`;
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < (options.ttlMs ?? 60000)) {
      return cached.value;
    }
    const fresh = await server.discover();
    this.cache.set(key, { value: fresh, timestamp: Date.now() });
    return fresh;
  }
}
```

**网关级意义**：
- `server/discover` 不再每次都向上游请求
- 网关可以做 **"协议版本探测 + 能力快照" 缓存**，TTL 通常 60s
- 减上游压力，**但要承担"协议版本不一致"的回退成本**

#### 4.2.4 stdio backward-compat fallback（PR #2844 merged 6-04）

```python
# 修复前：单错误码 -32601 判定
if err.code == -32601:
    assume_legacy_mode()

# 修复后：未知错误/超时 = 旧协议
if err.code is None or err.code not in KNOWN_CODES or is_timeout(err):
    assume_legacy_mode()
    cache_era_decision()  # 缓存判定结果
```

**网关工程含义**：
- stdio 传输上的"协议 era 探测"必须用**多信号判定**（未知错误/超时/旧错误码）
- **判定结果要缓存**，避免每次请求都做反向探测
- 这是 v0.7 → v0.8 升级的关键迁移工具

### 4.3 `Mcp-Session-Id` 移除后的网关工程预案

#### 预案 1：路由策略迁移

```python
# 旧实现：基于 session 粘性
def route_request(request):
    session_id = request.headers.get('Mcp-Session-Id')
    backend = session_affinity[session_id]  # 同一个 session 路由到同一 backend
    return forward(backend, request)

# 新实现：基于元数据 + 一致性 hash
def route_request_v1(request):
    meta = request.body.get('_meta', {})
    client_id = meta.get('clientInfo', {}).get('id', 'anonymous')
    request_id = request.headers.get('Mcp-Request-Id', generate_uuid())
    
    # 基于 client_id 做一致性 hash
    backend = consistent_hash(client_id, backends)
    return forward(backend, request, x_request_id=request_id)
```

#### 预案 2：配额/限流迁移

```python
# 旧实现
def check_rate_limit(session_id):
    return rate_limiter.check(session_id)

# 新实现：双轨
def check_rate_limit_v1(meta, request):
    client_id = meta.get('clientInfo', {}).get('id')
    if not client_id:
        return False, "missing clientInfo.id"
    
    # 维度1: 客户端身份限流
    if rate_limiter.check(f"client:{client_id}"):
        return True
    
    # 维度2: 协议版本限流（新协议优先放行）
    protocol = meta.get('protocolVersion', 'unknown')
    if rate_limiter.check(f"proto:{protocol}"):
        return True
    
    return False
```

#### 预案 3：审计日志增强

```python
# 旧审计：session 维度
log.info("mcp_call", session_id=session_id, method=method, duration_ms=ms)

# 新审计：client 维度 + 协议维度 + request 维度
log.info("mcp_call_v1", 
    client_id=meta.get('clientInfo', {}).get('id'),
    client_version=meta.get('clientInfo', {}).get('version'),
    protocol_version=meta.get('protocolVersion'),
    request_id=request_id,
    capabilities=meta.get('clientCapabilities'),
    method=method,
    duration_ms=ms,
    tool_name=response_metadata.get('mcp_tool_name'))
```

### 4.4 协议层**次要变更**（产品决策相关）

- **SEP-414 OTel trace context 标准化**：`traceparent` / `tracestate` / `baggage` 三个 key 在 `_meta` 里的传播约定正式落定。**网关可无侵入透传**。
- **`tools/list` 排序要求确定性**——为 LLM 提示缓存命中率优化。
- **`CacheableResult` 接口**（SEP-2549）：`tools/list` / `prompts/list` / `resources/list` 等必须返回 `ttlMs` + `cacheScope`（`public` / `private`）。**网关可借此实现工具列表缓存**。
- **错误码归一**：resource not found 从 `-32002` 改为 `-32602`（与 JSON-RPC 规范对齐）。
- **生命周期章节重命名**（PR #2850 closed 6-04）——之前 `Lifecycle` 章节改名，待定。
- **Server Features / Client Features 合并**（PR #2857 open 6-04）——spec 章节重组。

---

## 第 5 章 · Auth 治理：从散件到 IG 宪章化

### 5.1 Auth IG 正式成立

PR #2843（2026-06-04 merged，user: pcarleton @ Anthropic）把 `#auth-ig` 从 2025 中开始的"事实存在"变成**正式宪章化**的兴趣小组（IG）。

**3 位 facilitator**：Aaron Parecki（Okta）/ Darin McAdams（Amazon）/ Paul Carleton（Anthropic）。

**章程关键定位**（`docs/community/auth/charter.mdx`，2026-06-02 写入 changelog）：

**in scope**：
- OAuth 2.1 在真实 IdP（Okta / Entra ID / Ping / Keycloak）的落地摩擦
- **agentic 委托访问**（on-behalf-of token exchange）——AI agent 用用户身份去调上游
- **细粒度 scope**——per-tool / per-resource 级别 OAuth scope
- **非 HTTP 传输**（stdio / WebSocket）的鉴权模式
- **威胁建模**：
  - **token confusion**——access token 被误用
  - **confused-deputy**——低权限客户端被高权限工具代理
  - **听众错配**——token audience 不匹配
  - **重定向处理**——SSRF 风险

**out of scope**：
- 终端用户对 MCP client 本身的鉴权（"是 host 的事"）
- TLS 传输安全（归 Transports WG）
- 服务器身份/出处（归 Server Card WG / Registry）

### 5.2 6 个孵化 WG 状态

| WG | 状态 | 关键产出 | 对网关意义 |
|---|---|---|---|
| **Client Registration** | ✅ Completed | RFC 7591 DCR + Client ID Metadata Documents | 网关支持"动态注册 + 元数据发现" |
| **Mix-up Protection** | ✅ Completed | 防止 OAuth mix-up 攻击（多 IdP 场景下 token 错配） | 网关要做 audience 校验 |
| **Profiles** | ✅ Completed | Client Credentials + EMA + DPoP + Workload Identity Federation | 网关要支持多种 profile 切换 |
| **Improve DevX** | ✅ Completed | 改进 SDK 调试体验 | 网关日志要带 OAuth context |
| **Tool Scopes** | 🔄 Active | per-tool OAuth scope + step-up authorization + 客户端 scope 累积 | **直接影响生产**：网关在"tool 调用"前要做 scope 校验 |
| **Fine-Grained Authorization** | 🔄 Active | RFC 9396 RAR（Rich Authorization Requests）+ remediation hints + 多凭证处理 | **未来基础**："我能不能调用 X 工具的 Y 参数" |

### 5.3 关键 SEP 进展

#### 5.3.1 **SEP-1932: DPoP Profile for MCP**（open 6-05）

OAuth 2.0 DPoP（Demonstrating Proof-of-Possession，RFC 9449）的 MCP 绑定提案。

**核心思想**：access token 不够，还要证明"调用方持有 token 对应的私钥"——防止 token 泄露后被滥用。

**网关工程含义**：
- 网关必须验证 DPoP proof（JWT 格式，含 `htm`/`htu`/`iat`/`jti`）
- 验证 DPoP proof 的 JWK thumbprint 与 access token 内 cnf claim 一致
- 防止 replay（jti 必须唯一 + 时间窗口）

**当前状态**：draft，6-05 在 PR review 阶段。

#### 5.3.2 **SEP-2822: Client Generated Session ID**（open 6-04）

Mcp-Session-Id 移除后，**客户端可以自生成 session ID 用于追踪**——但这跟"无状态"哲学有微妙张力。

**争议点**：
- 支持方：客户端 SDK 仍需要 session 概念做缓存/复用
- 反对方：会重新引入"session 粘性"问题
- **当前草案**：允许但**不强制**使用，客户端可在 `_meta.session_id` 自定义

**网关工程含义**：
- 网关应同时支持"客户端 session ID"和"无状态追踪"两种模式
- 在 `_meta.session_id` 存在时优先使用，不存在时自生成 `Mcp-Request-Id`

### 5.4 Auth Spec 切片（PR #2858 closed/merged 6-04）

`#2858` "Authorization spec split" 把单一的 auth 章节拆成多个子页面：
- `auth-foundation.mdx`（基础概念）
- `auth-oauth.mdx`（OAuth 2.1 流程）
- `auth-scopes.mdx`（per-tool scope）
- `auth-rar.mdx`（Rich Authorization Requests）
- `auth-step-up.mdx`（step-up authorization）

**网关对齐策略**：未来 1-2 个版本要按子页对账，每加一个新 sub-spec 就要补一段实现。

---

## 第 6 章 · Registry 信任体系深度

### 6.1 近 7 天安全硬化 commit 矩阵

```
2026-06-05
  #1338  [M]  fix: don't leak internal error detail in GET /v0/servers 500
  #1335  [M]  fix: client-cancelled GET /v0/servers returns 499 without error
  #1331  [M]  fix(validators): harden mcp-name matching (PyPI/NuGet anchor)
  #1310  [O]  fix: reject mangled publisher metadata
2026-06-04
  #1330  [M]  fix(cargo): harden README fetch, clarify status handling
  #1334  [M]  build(deps): bump github.com/jackc/pgx/v5 from 5.9.2 to 5.10
  #1333  [M]  build(deps): bump github.com/pulumi/pulumi/sdk/v3 from 3.243
  #1332  [M]  build(deps): bump go.opentelemetry.io/contrib/instrumentation
2026-05-07
  #1261  [M]  Add ToolHive Registry Server to community projects
  #1253  [M]  Document OpenSSL 3.x Ed25519 signing
2026-04-30
  #1230  [M]  docs: GitHub OIDC audience binding for CI
2026-04-29
  #1227  [M]  fix: open redirect and 加固
2026-04-25
  #1202  [M]  fix(dns): better error messages and wrong-selector hints
2026-04-15
  #1166  [M]  feat: move publisher credentials to ~/.config/mcp-publisher/
```

**6-04/6-05 两天 4 个安全 fix + 3 个依赖升级**——Registry 进入"安全硬化阶段"。

### 6.2 6 个关键 PR 拆解

#### 6.2.1 **#1338 不泄漏 internal error detail**（6-05）

```go
// 修复前：直接返回 stack trace
return c.JSON(500, gin.H{"error": err.Error()})

// 修复后：返回通用错误 + 内部 trace_id
traceID := generateTraceID()
log.Errorf("internal error: %v, trace_id: %s", err, traceID)
return c.JSON(500, gin.H{
    "error": "internal server error",
    "trace_id": traceID,  // 客户端可以拿这个去查日志
})
```

**网关可借鉴**：
- 错误响应**永远不要**把内部 stack trace 露给客户端
- 用 `trace_id` 关联服务端日志
- 客户端拿到 5xx 错误可以"无脑重试 + 带 trace_id 提工单"

#### 6.2.2 **#1331 harden mcp-name matching**（6-05）

```python
# 修复前：宽松的 name 校验
if re.match(r'^[a-z0-9-]+$', server_name):
    return True

# 修复后：加 PyPI/NuGet anchor（防止 lookalike 攻击）
def is_valid_mcp_name(name: str) -> bool:
    # 不能和已知的 PyPI/NuGet 包同名
    if name in pypi_reserved_names or name in nuget_reserved_names:
        return False
    # 不能是 homograph attack（视觉相似字符）
    if contains_homographs(name):
        return False
    # 长度 3-64
    if not (3 <= len(name) <= 64):
        return False
    return True
```

**意义**：防止攻击者注册 "openai-mcp" / "anthropic-mcp" 之类的**仿冒服务器**——这是 Registry 信任体系的基石。

#### 6.2.3 **#1310 拒绝 mangled publisher metadata**（open 6-05）

```typescript
// 验证 publisher metadata 结构
function validatePublisherMetadata(meta: PublisherMeta): ValidationResult {
  // 必填字段
  if (!meta.namespace || !meta.publisher_id) {
    return { valid: false, reason: 'missing required fields' }
  }
  // OIDC audience 必须匹配 namespace
  if (meta.oidc_audience !== `https://registry.modelcontextprotocol.io/${meta.namespace}`) {
    return { valid: false, reason: 'OIDC audience mismatch' }
  }
  // GitHub org 验证
  if (meta.publisher_type === 'github' && !await verifyGitHubOrg(meta.publisher_id)) {
    return { valid: false, reason: 'GitHub org not found' }
  }
  return { valid: true }
}
```

**网关可借鉴**：
- 验证 publisher 身份的"双因素"：namespace 必填 + OIDC audience 必匹配 + GitHub org 必存在
- **mangled metadata** 是供应链攻击的常见入口

#### 6.2.4 **#1227 open redirect 修复**（4-29）

注册中心 webflow 流程里的"open redirect"漏洞——攻击者构造一个 redirect URL，诱导用户在注册后跳转到恶意站点。

**修复**：注册中心现在对 redirect URL 做白名单校验，**只允许跳回 registry 自身或已验证的 namespace URL**。

#### 6.2.5 **#1253 Ed25519 签名 server.json**（5-07）

```bash
# 生成 Ed25519 签名
openssl genpkey -algorithm Ed25519 -out server_signing_key.pem
openssl pkey -in server_signing_key.pem -pubout -out server_signing_key.pub

# 签名 server.json
openssl pkeyutl -sign -inkey server_signing_key.pem -in server.json -out server.json.sig

# 验证签名
openssl pkeyutl -verify -pubin -inkey server_signing_key.pub -in server.json -sigfile server.json.sig
```

**意义**：MCP server 发布到 registry 时**带 Ed25519 签名**——客户端/网关可以验证 server.json 没被篡改。

**网关可借鉴**：
- 网关代理 upstream MCP server 时验证 server.json 签名
- 防止"中间人替换 server.json 注入恶意工具"

#### 6.2.6 **#1166 publisher 凭据存 `~/.config/`**（4-15）

```bash
# 旧位置：项目根
./.mcp-publisher/credentials

# 新位置：XDG 规范
~/.config/mcp-publisher/credentials
```

**意义**：符合 XDG Base Directory 规范，避免凭据散落项目目录被意外提交。

### 6.3 Registry 6 大安全模式总结

| 模式 | 用途 | 网关可借鉴 |
|---|---|---|
| **Ed25519 签名 server.json** | 验证 MCP server 出处 | 网关代理前必验签 |
| **namespace ownership 强制** | 防止仿冒 | 网关侧做"namespace → org" 映射校验 |
| **publisher 凭据存 `~/.config/`** | 本地凭据规范 | 网关发"publish 凭据"时也走 XDG |
| **OIDC audience 绑定** | CI 场景 | 网关"OIDC token 的 audience 必须正确" |
| **错误信息不泄漏** | 防信息泄露 | 5xx 错误带 trace_id 不带 stack |
| **mcp-name lookalike 防护** | 防 homograph attack | 网关对 upstream server name 做规范化 |

---

## 第 7 章 · 架构对比矩阵

### 7.1 8 维度对比

| 维度 | Envoy AI GW | Higress | kgateway | LiteLLM | Portkey |
|---|---|---|---|---|---|
| **数据面** | Envoy + ext-proc (Go) | Envoy fork + Wasm | Envoy (via Envoy GW) | Python asyncio | Node.js |
| **配置面** | K8s CRD | CRD + Nginx annotation + Console | Gateway API | YAML/UI | UI/API |
| **协议翻译** | ext-proc OpenAI/Anthropic/Gemini/Bedrock | Wasm/插件（多 provider） | 主要 OpenAI 兼容 | 250+ provider | 250+ provider |
| **MCP 集成** | ✅ `MCPRoute` v1beta1 | ✅ `Mcp Bridge` + AI 安全 | ❌ 暂无 | ⚠️ v1.88 计划 | ✅ `mcp-tool-filter` 仓库 |
| **Wasm 扩展** | ✅ Envoy 自身支持 | ✅ 一等公民（市场） | ⚠️ 需手写 | ❌ | ❌ |
| **RPS 基线（单核 L7）** | 30-50 万 | 30-50 万 | 30-50 万 | 200-800 | 1000-3000 |
| **冷启动** | 中（K8s controller） | 中 | 中 | 极快（pip） | 极快（npm） |
| **CVE 响应速度** | 依赖 Envoy GW（周级） | 自维护 Envoy（日级） | **24h**（本次 CVE） | Python 生态（CVE 少） | Node 生态（CVE 少） |

### 7.2 1000x RPS 差距的根因

**Envoy 30-50 万 RPS/单核**（社区 benchmark）：
- C++ 实现 + epoll + io_uring
- P99 < 1ms
- 数据面极简（filter chain）

**LiteLLM Python 进程 200-800 RPS**：
- Python asyncio + OpenAI SDK I/O 限制
- 8 进程 → 1500-5000 RPS
- 定位"应用层 SDK 网关"

**Portkey Node 1k-3k RPS**：
- Node 异步 I/O
- 横向扩 → 8000+ RPS

**MCP 路由开销**：
- Envoy AI GW v0.6.0 P99 +~2ms（release notes 自报）
- Higress Mcp Bridge P99 +1-3ms

**结论**：选型分水岭 —— 要百万 RPS 走 Envoy 系；要"应用层 SDK 网关"走 LiteLLM/Portkey。

### 7.3 选型决策树

```
是否要 MCP 路由？
├─ 是
│  ├─ K8s 原生 + 多协议翻译 → Envoy AI GW v0.6.0（首选）
│  ├─ 国内 + 中文商业支持 → Higress v2.2.2
│  └─ 自建 K8s + 24h CVE 响应 → kgateway v2.3.2
│
└─ 否
   ├─ 大流量（>10k RPS） + K8s → Envoy 系
   ├─ 应用层 SDK（25+ 模型 + Guardrails）→ LiteLLM v1.87.1
   ├─ 治理重（50+ Guardrails + 审计）→ Portkey v1.15.2
   ├─ 最快最轻 → Helicone AI GW（Rust）
   └─ 零运维边缘 → Cloudflare AI GW
```

### 7.4 选型实操清单

1. **真网关（百万 RPS + K8s 原生 + 多协议翻译）**：Envoy AI GW v0.6.0（首选，CRD 最纯正）/ Higress v2.2.2（国内云原生 + WASM）/ kgateway v2.3.2（在用 Solo.io 商业版）
2. **应用层 SDK 网关（25+ 模型切换 + Guardrails 编排）**：LiteLLM v1.87.1（Python 全）/ Portkey v1.15.2（多 Guardrails 编排）
3. **MCP 场景**：Envoy AI GW v0.6.0（v1beta1 + JWT claim forward）/ Higress v2.2.2（Mcp Bridge + AI 安全）/ **避免 kgateway（无原生 MCP）**
4. **CVE 应急**：边缘跑 Envoy 1.37.0-1.37.2 **本周内必升** CVE-2026-47774
5. **架构演进信号**：
   - WASM 沙箱取代原生指令式配置（Higress PR #3823）—— 12 个月内扩散到所有 AI 网关
   - **MCP 升 v1beta1** —— "AI 网关 = LLM 路由 + MCP 路由 + Agent 路由"三件套成事实标准
   - 双轨 LTS 策略（kgateway v2.3.x / v2.2.x）—— 大型项目维护趋势

---

## 第 8 章 · 安全与 CVE 联动

### 8.1 CVE-2026-47774（CVSS 7.5 HIGH）

**披露日期**：2026-06-03
**影响**：HTTP/2 cookie 头大小绕过 + HPACK 解码放大
**后果**：3 GiB 内存限制下几分钟 OOM
**修复版本**：Envoy 1.35.11 / 1.36.7 / 1.37.3 / 1.38.1

**AI 网关合入情况**：
- **kgateway v2.3.2 + v2.2.5（6/4 当日修）** —— 24h 响应
- Envoy AI GW v0.6.0：基线 Envoy 1.37.0，**未修**（等 v0.6.1）
- Higress v2.2.2：自维护 Envoy 分支，要看后续是否 backport
- LiteLLM / Portkey：进程内，不直接吃 Envoy CVE

### 8.2 CVE-2026-42945（CVSS 9.2 CRITICAL）

**披露日期**：2026-05-XX（Nginx 18 年老漏洞）
**影响**：Nginx `rewrite`+`set` 两阶段状态泄漏 → 堆溢出
**修复版本**：Nginx 1.30.0+

**AI 网关合入情况**：
- **Higress PR #3823 用 WASM 沙箱绕开** —— 业界首例
- LiteLLM / Portkey：进程内，不直接吃 Nginx CVE

### 8.3 5 款 AI 网关 24h 修 vs 等版本对比

| CVE | kgateway | Envoy AI GW | Higress | LiteLLM | Portkey |
|---|---|---|---|---|---|
| CVE-2026-47774 | ✅ 24h | ❌ 等 v0.6.1 | ⚠️ backport | N/A | N/A |
| CVE-2026-26308 | 待查 | ❌ | ❌ | N/A | N/A |
| CVE-2026-26330 | 待查 | ❌ | ❌ | N/A | N/A |
| CVE-2026-42945 | N/A | N/A | ✅ WASM 沙箱 | N/A | N/A |
| **GHSA-q775 (session-token)** | N/A | N/A | N/A | ✅ v1.88.0-rc.2 | N/A |
| **CVE-2026-42504 (Go toolchain)** | N/A | N/A | N/A | N/A | N/A (Archestra 6-04 当日跟) |

**实操含义**：
- 选型把"上游核心 CVE 响应速度"当硬指标
- 本次 CVE-2026-47774：6/3 披露 → kgateway **24h 修**（v2.3.2 + v2.2.5）；Envoy AI GW 还没修
- **本周内必升**：边缘跑 Envoy 1.37.0-1.37.2 的环境

### 8.4 WASM 沙箱取代原生指令配置

**Higress PR #3823 的设计**：
- 旧实现：nginx rewrite 指令直接执行
- 新实现：rewrite 逻辑编译成 WASM 字节码，在 WASM 沙箱里跑
- **核心优势**：
  - 内存隔离：WASM 沙箱限制内存使用
  - 指令集安全：WASM 字节码是确定性的
  - **避免 18 年老漏洞**（CVE-2026-42945）
- **未来 12 个月预测**：所有 AI 网关都会跟进 WASM 沙箱

---

## 第 9 章 · 性能基准与可观测

### 9.1 公开 RPS 数据汇总

| 产品 | 单核 RPS | P99 延迟 | 备注 |
|---|---|---|---|
| Envoy 主线 | 30-50 万 | <1ms | 社区 benchmark |
| Envoy AI GW ext-proc 模式 | 15-30 万 | +30-50% | ext-proc 多一跳 |
| Higress WASM 插件 | 30-50 万 | +0.3-0.5ms | 内部 benchmark |
| LiteLLM proxy 单进程 | 200-800 | — | FastAPI worker + OpenAI SDK |
| LiteLLM 8 进程 | 1500-5000 | — | 横向扩展 |
| Portkey 单进程 | 1000-3000 | — | Node 异步 I/O |
| Portkey 横向扩展 | 8000+ | — | — |
| MCP 路由（Envoy AI GW）| 减 30-50% | +~2ms | release notes 自报 |
| MCP 路由（Higress）| 减 30-50% | +1-3ms | Mcp Bridge |

**结论**：
- 数据面 L7 路由 30-50 万 RPS/单核是行业基准
- LLM/MCP 网关的开销主要在 ext-proc 翻译、WASM 沙箱、协议序列化
- 1000x 差距（Envoy vs LiteLLM）= **"真网关 vs SDK 网关"的分水岭**

### 9.2 OTel GenAI semantic conventions 独立成仓

**5-05 关键事件**：OTel 主仓 PR #3696 "Move GenAI semantic conventions to its own dedicated repository"

**独立仓**：`open-telemetry/semantic-conventions-genai`

**6-04 同日合并 4 个 spec-level PR**：

| PR | 内容 | 含义 |
|---|---|---|
| **#220** | MCP context propagation 显式指向 **MCP SEP-414** | LLM trace 和 MCP tool call trace 终于能串成一条链 |
| **#216** | GenAI span duration 含 retries | 之前 retry 隐藏了真实耗时，现在能算 P99 |
| **#217** | `top_k` 拆 retrieval | 区分 LLM 参数和 RAG 参数 |
| **#219** | conversation id fallback | 多 session 同 user 时 trace 能拼起来 |
| **#214** | `provider.name` 降 Recommended → Optional | 厂商信息不强求，但有就给 |

**对网关的意义**：
- **统一的 LLM trace 协议**——半年内所有 LLM 可观测工具（Langfuse / Phoenix / OpenLLMetry / OpenLIT）都会跟进
- 网关可在 OTLP 上报时**带 OTel semconv 标准属性**——客户端/Grafana 能直接消费

### 9.3 eBPF 零插桩 LLM 可观测 production 化

| 项目 | 进度 | 亮点 |
|---|---|---|
| `eunomia-bpf/agentsight` (381★) | 6/3-6/4 三 tag（v0.2.7/0.2.8/0.2.9）| SSL filter 重构 + StdioRunner/SystemRunner + SSE 重构 |
| `AkshantVats/ebpf-llm-tracer` (Go+BPF) | 6/1-6/4 Day 15→17 | 从 connect probe 推到 user-space HTTP parser + Kafka InferenceEvent |

**两个独立信号**：
- eBPF 项目从 demo（"能抓 OpenAI 调用"）走到 production（"能抓 SSE 流式响应 + 写 Kafka"）
- 零插桩 = **无需改应用代码**，网关/EOS 都能跑

**对网关的意义**：
- 网关可集成 eBPF tracer 做**深度 packet inspection**——不依赖 SDK
- 适合"老应用无法插桩" + "全链路监控" 场景

### 9.4 跨协议 trace：MCP context propagation 对接 SEP-414

**核心问题**：LLM 调用和 MCP tool call 在不同 trace 里，无法串成一条链。

**解决方案**（SEP-414）：
- `traceparent` / `tracestate` / `baggage` 三个 key 在 MCP `_meta` 里传播
- 网关/客户端无侵入透传

**网关实现示例**：
```python
def forward_mcp_request(request, upstream):
    # 提取 OTel context
    meta = request.body.get('_meta', {})
    traceparent = meta.get('traceparent')
    tracestate = meta.get('tracestate', '')
    baggage = meta.get('baggage', '')
    
    # 透传到 upstream HTTP header
    headers = {
        'traceparent': traceparent,
        'tracestate': tracestate,
        'baggage': baggage,
    }
    
    return upstream.post(headers=headers, json=request.body)
```

**价值**：
- LLM 调用 → MCP tool call → upstream API → DB query，**完整 trace 链**
- Grafana Tempo / Jaeger / Honeycomb 能直接消费
- **零侵入**——客户端/服务端 SDK 都不用改

---

## 第 10 章 · 未来 6-12 个月展望

### 10.1 协议层：MCP 7-28 RC 转 GA 的迁移路径

**关键时间点**（预测）：
- **2026-07-28**：RC cut（已经发生，5-29 cut）
- **2026-09**：预计 RC.2 / RC.3
- **2026-10~11**：预计 GA

**网关迁移时间窗**（建议）：
- **2026-07-28 ~ 09-30**：**观望期**——RC 阶段不生产
- **2026-10 ~ 12**：**灰度期**——10% 流量走新协议
- **2027-01 ~ 03**：**全量期**——所有流量走新协议

**网关必备的 4 个迁移动作**：
1. `_meta` 透传 OTel context（SEP-414）
2. `Mcp-Session-Id` 移除预案
3. `server/discover` 缓存支持
4. CacheableResult TTL 字段支持

### 10.2 产品层：MCPBackend CRD 提案落地

**PR #2144（6-03 closed，设计稿落地中）**：

**核心问题**：`MCPRoute` 内的 inline backendRefs 撞 K8s object size limit——尤其当 RFC 8693 token exchange（每个 backend ~25 行 nested config）加进去后。

**4 个备选设计**：
1. inline security policy（简单但耦合生命周期）
2. **独立 security policy + Policy Attachment**（推荐，与 LLM 侧 `AIServiceBackend + BackendSecurityPolicy` 对齐）
3. backend-refs-policy
4. route-refs-policy

**推荐方案**：`MCPBackend` CRD + 扩展 `BackendSecurityPolicy` 用 `targetRefs`，同时保留 `MCPRouteBackendRef` 的 `Name/Group/Kind` 字段做向后兼容。

**预测落地时间**：v0.7.0（预计 2026 Q4）

### 10.3 协议层：Tool Scopes + RAR 标准化

**Tool Scopes WG**（Active）关键产出：
- per-tool OAuth scope 定义
- step-up authorization 流程
- 客户端 scope 累积策略

**Fine-Grained Authorization WG**（Active）关键产出：
- RFC 9396 RAR（Rich Authorization Requests）格式
- remediation hints（"用户需要 X 权限才能调用此工具"）
- 多凭证处理（一个用户身份 + 多个 tool 凭证）

**预测时间窗**：
- **2026 Q3**：spec 草案
- **2026 Q4**：RFC 化
- **2027 Q1**：网关产品落地

**对网关的硬性要求**：
- per-tool scope 校验（call tool 前做 scope check）
- step-up 触发（"高风险 tool 需要重新认证"）
- RAR 格式解析（结构化声明 "我要访问的对象/动作"）

### 10.4 生态层：AAIF 旗下 multi-agent 协议栈

**AAIF 现状**（截至 2026-06-04）：
1. A2A（Agent-to-Agent）—— 2025 加入
2. MCP（Model Context Protocol）—— 2025 加入
3. GIE（Gateway API Inference Extension）—— 2025 加入
4. **agentgateway**（新进，2026-06-04）

**A2A + MCP + GIE + agentgateway 协议组合**：
- A2A：agent ↔ agent 通信
- MCP：LLM ↔ tool 通信
- GIE：K8s 层面的 LLM 路由
- agentgateway：multi-agent 编排 + trace

**预测**：
- **2026 H2**：AAIF 完成 multi-agent 协议栈标准化
- **2027 H1**：所有"自创 multi-agent 协议"的项目失去标准地位
- **2027 H2**：Linux Foundation 可能再收编 1-2 个新项目（如 Guardrails spec、Eval spec）

**对网关的判断**：
- 任何 AI 网关未来 12 个月**必须支持** AAIF 四件套
- 不支持 → 在 2027 年变成"小众定制网关"

---

## 附录 A · 引用与数据源

### A.1 GitHub 主仓

- `https://github.com/happysunxf/aigw`（aigw 调研仓库，50+ 份报告）
- `https://github.com/envoyproxy/ai-gateway`（Envoy AI Gateway）
- `https://github.com/higress-group/higress`（Higress）
- `https://github.com/kgateway-dev/kgateway`（kgateway）
- `https://github.com/BerriAI/litellm`（LiteLLM）
- `https://github.com/Portkey-AI/gateway`（Portkey）
- `https://github.com/Helicone/ai-gateway`（Helicone AI Gateway）
- `https://github.com/Kong/kong`（Kong）
- `https://github.com/modelcontextprotocol/modelcontextprotocol`（MCP 主仓）
- `https://github.com/modelcontextprotocol/registry`（MCP Registry）
- `https://github.com/stacklok/toolhive`（ToolHive vMCP）
- `https://github.com/IBM/mcp-context-forge`（IBM mcp-context-forge）
- `https://github.com/archestra-ai/archestra`（Archestra）
- `https://github.com/docker/mcp-gateway`（Docker mcp-gateway）
- `https://github.com/open-telemetry/semantic-conventions-genai`（OTel GenAI semconv）

### A.2 关键 PR / Issue

#### MCP 主仓
- Auth IG Charter（PR #2843 merged 6-04）
- SEP-1932 DPoP Profile（open 6-05）
- SEP-2822 Client Session ID（open 6-04）
- Auth spec split（PR #2858 merged 6-04）
- server/discover caching（PR #2855 merged 6-04）
- stdio fallback（PR #2844 merged 6-04）

#### MCP Registry
- #1338 / #1335 / #1331 / #1310（6-05 4 个安全 fix）
- #1330 / #1334 / #1333 / #1332（6-04 安全 + 依赖）
- #1261 / #1253 / #1230 / #1227 / #1202 / #1166（4-5 月硬化）

#### Envoy AI Gateway
- v0.6.0 release（5-05）
- MCPRoute v1beta1（PR #2090 4-30）
- MCPBackend CRD 提案（PR #2144 6-03）
- v0.6.0 两个 breaking change

#### Higress
- v2.2.2 release（5-26）
- PR #3827 modelToHeader
- PR #3823 nginx-rewrite WASM（CVE-2026-42945）
- PR #3820 Bedrock Mantle
- PR #3766 cached tokens

#### Archestra
- 30 天 6 个 patch（5-27 ~ 6-04）
- #5293 GitHub App auth
- #5298 team-scope catalog
- #5305 DB pool cap
- #5294 Go 1.25.11 CVE-2026-42504
- #5302 revert catalog preset

### A.3 协议规范

- MCP 2026-07-28 RC：https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28-RC
- MCP spec site：https://modelcontextprotocol.io/specification/draft
- Registry API live docs：https://registry.modelcontextprotocol.io/docs
- Envoy AI Gateway docs：https://aigateway.envoyproxy.io/docs/0.6/

---

## 附录 B · 缩略语表

| 缩略语 | 全称 | 含义 |
|---|---|---|
| **CRD** | Custom Resource Definition | K8s 自定义资源 |
| **SEP** | Specification Enhancement Proposal | MCP 的 spec 提案编号 |
| **IG** | Interest Group | MCP 的兴趣小组 |
| **WG** | Working Group | 工作组 |
| **MRTR** | Multi Round-Trip Requests | 多轮请求模式 |
| **DPoP** | Demonstrating Proof-of-Possession | OAuth 2.0 防 token 滥用 |
| **RAR** | Rich Authorization Requests | RFC 9396 结构化授权请求 |
| **MCP** | Model Context Protocol | 模型上下文协议 |
| **AAIF** | Agentic AI Foundation | Linux Foundation 旗下 agent 基金会 |
| **A2A** | Agent-to-Agent | agent 通信协议 |
| **GIE** | Gateway API Inference Extension | K8s 网关推理扩展 |
| **Wasm** | WebAssembly | 字节码沙箱 |
| **ext-proc** | External Processor | Envoy 外部处理器 |
| **CVE** | Common Vulnerabilities and Exposures | 公共漏洞编号 |
| **CVSS** | Common Vulnerability Scoring System | 漏洞评分系统 |
| **OTel** | OpenTelemetry | 可观测标准 |
| **OTLP** | OpenTelemetry Protocol | OTel 数据协议 |
| **DCR** | Dynamic Client Registration | RFC 7591 OAuth 动态注册 |
| **STIG** | Security Technical Implementation Guides | 美国国防部安全配置基线 |
| **FedRAMP** | Federal Risk and Authorization Management Program | 美国联邦云安全认证 |
| **PANW** | Palo Alto Networks | 网络安全公司，收购 Portkey |
| **ZDR** | Zero Data Retention | 零数据留存 |
| **SSRF** | Server-Side Request Forgery | 服务端请求伪造 |
| **RC** | Release Candidate | 候选发布版 |
| **GA** | General Availability | 正式发布版 |
| **ADR** | AI Detection and Response | CrowdStrike 的 AI 安全产品 |

---

## 附录 C · 时间线

```
2024 Q4  Anthropic 提出 MCP
2025 Q1  Portkey 推出 Agent Gateway
2025 Q3  Helicone 14.2T token
2025 Q4  Envoy AI Gateway v0.4.0 GA、Portkey 被 PANW 收购
2026-01  Portkey v1.15.2 GA、最后一个大版本
2026-02  Higress v2.2.0、Cloudflare AI Gateway 全部计划免费
2026-03  Helicone 被 Mintlify 收购（3-03）、OpenRouter 月 100T token
2026-04  IBM mcp-context-forge v1.0.0 GA（4-30）、Envoy AI GW MCPRoute v1beta1（4-30）
2026-05  Envoy AI GW v0.6.0（5-05）、Higress v2.2.2（5-26）、Portkey 5-19 安全审查 4 commit、MCP 7-28 RC cut（5-29）
2026-06  agentgateway 加入 AAIF（6-04）、Auth IG 宪章化（6-04）、Registry 4 个安全 fix（6-05）、aigw 调研 50+ 报告沉淀
2026-07  [预测] MCP 7-28 RC.2
2026 Q4  [预测] MCPBackend CRD 落地、Tool Scopes + RAR spec 草案
2027 H1  [预测] MCP 7-28 GA、AAIF multi-agent 协议栈标准化
2027 H2  [预测] Linux Foundation 再收编 1-2 个新项目
```

---

**【完】**

**作者**：aigw 调研团队
**发布**：aigw 仓库 `hermes/reports/2026-06-05-2015-aigw-deep-tech-article.md`
**许可**：Apache-2.0
**反馈**：issue @ happysunxf/aigw
