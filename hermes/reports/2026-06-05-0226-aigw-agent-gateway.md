# AI 网关持续深挖 · Agent Gateway 专题

> **抓取时间**：2026-06-05 02:26 CST（UTC 2026-06-04 18:26）· **主题**：cron 2/9 轮 Agent Gateway — multi-agent 编排、trace 调试、成本归因。**本轮主体**：`agentgateway/agentgateway`（kgateway 出身、Solo.io 捐赠给 Linux Foundation 后**刚于 6/4 加入 Agentic AI Foundation (AAIF) 作为第四个 hosted 项目**）。

---

## 一、本轮核心信号

| 信号 | 含义 |
|---|---|
| **agentgateway 加入 AAIF（2026-06-04）** | Linux Foundation 旗下第 4 个 AAIF 项目——**网关被官方收编为 agentic infra 一等公民** |
| v1.2.0 (5/14) → v1.2.1 (5/15) → v1.3.0-alpha.1 (5/23) 三周三个里程碑 | **月度发布列车**——"shipping like the agents are watching"（官方原话） |
| 200+ PR 集中落地 dtrace / A2A / InferencePool / Okta MCP | trace 工具化、agent 一等资源、self-hosted 模型路由三件大事 |

> 上一轮（01:54）讲 MCP Gateway 产品矩阵，本轮**专攻 agent gateway 中 "agent" 那一半**。

---

## 二、为什么 agentgateway 是"agent gateway"赛道事实代表

### 2.1 出身与定位

Solo.io 内部项目，2025-08 OSSEurope **捐赠给 Linux Foundation**；**2026-06-04 升格**加入 **Agentic AI Foundation (AAIF)**，**第 4 个 hosted initiative**。**技术栈**：**Rust 数据面 + Go controller**，3036★ / 507 fork（截至 6/4）。**30 个 release**：v0.12.0 (2/9) → v1.0.0 (3/16) 5 周；之后**月度 minor**（v1.1.0 4/9 → v1.2.0 5/14）。**数据**：~1M 季度 image pulls、~2K stars。

### 2.2 它**同时**是 4 类网关

| 类型 | 协议 | 重点能力 |
|---|---|---|
| Service Gateway | HTTP / gRPC / TCP | mTLS、OIDC、TLS-1.3、Envoy 兼容 |
| LLM Gateway | OpenAI / Anthropic / Bedrock / Vertex / Cohere 等 12+ | per-team token budget、semantic cache、prompt redact |
| MCP Gateway | MCP | Discovery、RBAC、Audit、Multiplex |
| **A2A Gateway** | Agent-to-Agent | Identity、Tracing、Replay——**本轮重点** |

> **关键洞察**：其他厂商（Envoy AI GW、Portkey、LiteLLM）做 LLM + MCP 两件套；agentgateway **把 agent-to-agent 当成第三个一等公民**——这是"agent gateway"和"AI gateway"在 2026 年的**根本分水岭**。

---

## 三、本轮 4 个最重的工程动作

### 3.1 `agctl` CLI + dtrace 流式 trace

```bash
agctl config         # 渲染 proxy 已加载的 binds/listeners/routes/backends/policies
agctl config backends  # per-backend 健康、req count、latency
agctl trace          # 下一个请求 step-by-step：matched route / policies / backend / status
agctl version        # 6/4 新增：build info + version mismatch check
```

**6 个 dtrace 关键 PR**：#1887（bodysnapshots 在多个时点抓）/ #1886（JSON 输出模式）/ #1890（`--raw` 一键 vim 打开）/ **#1996（CEL 表达式注册断点）**/ #2034（DropOnLog 触发时 trace 不丢）/ #1888（schema dedupe）

> **对架构师的信号**：agentgateway 在做 **"gateway 内置 pprof+OTel 工具集"**——为 agent 协议专门建模，是 multi-agent 调试痛点的直接解。

### 3.2 A2A first-class backend（PR #1841）

v1.3.0-alpha.1 把 **A2A 作为 AGBE 一类 backend**：

```yaml
binds:
- port: 3000
  listeners:
  - routes:
    - policies: {cors: {allowOrigins: ["*"]}}
      a2a: {}                # ← A2A listener 一等公民
      backends:
      - host: localhost:9999
```

**A2A 配套 PR 矩阵**（过去 60 天）：#1841（first-class a2a backend）/ #1678（X-Forwarded-Proto）/ #1628（lazy load 性能）/ #1760（sub-path 部署 policy 匹配）/ #1487（UI namespace 解析）/ 7 个 `examples/a2a/strands-agents` 依赖 bump——**AWS 官方 Strands Agents + agentgateway 是 reference stack**。

> **战略信号**：agentgateway **押注 A2A 是 multi-agent 编排的"协议事实标准"**——和 Google ADK / LangChain A2A 规范、AWS Strands Agents 走同一路线。**对 Anthropic MCP-only 路线的对冲**。

### 3.3 InferencePool + Custom LLM providers（PR #1932）

v1.3.0-alpha.1 加 **InferencePool 后端的 custom LLM provider**——**Gateway API Inference Extension (GIE)** 标准的关键能力：

- GIE 是 K8s SIG-Network 推的**自托管 LLM 路由标准**，核心 CRD 是 `InferencePool`（vLLM/TGI/Triton replicas）+ `InferenceModel`
- agentgateway 实现 GIE 兼容——接管 **vLLM 集群的智能路由**（latency-aware、cost-aware、warmest-replica）
- 配套 PR #1743：`Handle invalid InferencePool EPP refs`（EPP 失败不挂死）

> **对架构师的信号**：**LLM Gateway 和 Inference Routing 正在融合**——agentgateway / llm-d / GIE 三件套是 2026 自托管 LLM 的事实标准组合。

### 3.4 Okta first-class MCP auth（PR #1831）

v1.3.0-alpha.1 加 **Okta 作为 first-class MCP authentication provider**——multi-agent enterprise 落地最大瓶颈。

**配套 auth PR 矩阵**：#1831（Okta 一等公民）/ #1876（API key permissive mode）/ #1938（MCP DCR mock 加 RFC 7591 metadata）/ #1974（CEL 显式 unredact API key）/ #1951（mTLS cert passthrough via CEL）/ #1798（auth location extraction 表达式）/ **#1941（xDS 不再 reject 坏 JWKS——fail-open 生产友好）**/ #1969（修 premature cookie stripping，允许 route-level OIDC）/ #2027（CEL 暴露 `jwt.rawToken`）/ #1984（custom `secretRef` group/kind）

> **对架构师的信号**：MCP auth 在 **从"自己实现 OAuth" → "用 Okta / Entra ID / Keycloak 一等集成"**。**53% 静态 API key** 的痛点（Archestra 调研）正被 gateway 层治理。

---

## 四、其他工程动作

**v1.2.0 foundation feature**：**Conditional policy execution**（CEL 表达式选 policy，5 类 policy 都支持）/ **Automatic xDS TLS management**（controller 自签 CA + 短期 cert，**生产默认 `mode: tls`**）/ **Route delegation**（平台团队 parent HTTPRoute，应用团队 child——multi-team 大规模部署的**最小可用治理模型**）。

**v1.2.0 breaking**：`controller.xds.tls.enabled: true` → `controller.xds.mode: tls`（新增 `plaintext` / `either`，**默认 `tls`**）。

**v1.3.0-alpha.1 零碎但有用**：#1839（MCP service selector target name）/ #1868（Bedrock host override）/ #1893（AWS request signing allowlist）/ #1904（Anthropic `xhigh` thinking）/ #1906（修 Azure AI Foundry hostname）/ **#1895（Backend eviction with retries，vLLM 副本抖动容错）** / #1854（API 更严格 quantity 校验）/ #2043 Go 1.26.4（CVE）/ #2048 Rust 1.96 / #1882 K8s 1.36。

---

## 五、对 multi-agent 项目的 5 个具体建议

1. **multi-agent 编排盯 agentgateway 的 AGBE 资源模型**——`MCPRoute` / `A2ABackend` / `InferencePool` 三类一等资源**已和 Gateway API 标准对齐**。
2. **trace 调试从 `agctl trace` 入手**——尤其 **dtrace CEL 表达式断点**（#1996）——"trace 当 tenant=acme 的所有 LLM 调用"，比手动接 Langfuse 快 10×。
3. **自托管 LLM 选 agentgateway + GIE + vLLM 三件套**——**2026 唯一得到 Gateway API 标准背书的组合**。
4. **企业 MCP auth 不再自己写**——直接用 agentgateway v1.3.0+ 的 Okta / Entra ID 一等集成。
5. **route delegation 模式**——平台团队管 parent HTTPRoute，子团队管 child。**比"一团队一 namespace 各自跑 gateway" 简单 10×**。

---

## 六、本期数字摘要

- 抓取产品：**1 个深度 + 2 个对照**（agentgateway 主线 / Envoy AI GW / LiteLLM 类对照）
- 关键 release：**v1.2.0 (5/14) + v1.2.1 (5/15) + v1.3.0-alpha.1 (5/23)**
- 战略事件：**2026-06-04 加入 AAIF**（Linux Foundation 第 4 个 hosted 项目）
- 重点 PR：**#1841 A2A first-class / #1996 dtrace CEL / #1932 InferencePool custom LLM / #1831 Okta MCP / #1887 dtrace bodysnapshots / #1882 K8s 1.36**
- 协议路线：**A2A + MCP + GIE InferencePool 三件套**——multi-agent 的"协议事实标准组合"
- 工具：**agctl trace + dtrace + 6 个 dtrace PR**——gateway 内置 trace 已成产品力

---

## 引用与数据来源

### agentgateway（主线）
- v1.2.0 release：`https://api.github.com/repos/agentgateway/agentgateway/releases/tags/v1.2.0`
- v1.2.1 release：`https://api.github.com/repos/agentgateway/agentgateway/releases/tags/v1.2.1`
- v1.3.0-alpha.1 release：`https://api.github.com/repos/agentgateway/agentgateway/releases/tags/v1.3.0-alpha.1`
- 全 release 列表：`https://api.github.com/repos/agentgateway/agentgateway/releases`
- commits 5/23 之后：`https://api.github.com/repos/agentgateway/agentgateway/commits?since=2026-05-23T00:00:00Z`
- repo meta：`https://api.github.com/repos/agentgateway/agentgateway`
- 官方首页（含 AAIF banner）：`https://agentgateway.dev/`
- 官方 blog 列表：`https://agentgateway.dev/blog`（含 Jun 4 2026 "agentgateway Joins AAIF" / May 14 2026 "v1.2.0: we're shipping like the agents are watching" / Mar 25 2026 "Happy 1st birthday" / Mar 23 2026 "Inference Serving with Superpowers"）
- v1.3.0-alpha.1 关键 PR 搜索：`https://api.github.com/search/issues?q=repo:agentgateway/agentgateway+is:pr+is:merged+merged:>2026-05-15+a2a+OR+mcp+OR+inference+OR+dtrace+OR+route`

### 对照项目
- Envoy AI Gateway：见 `hermes/reports/2026-06-05-0106-aigw-mcp-gateway.md`
- IBM mcp-context-forge / Higress / Archestra：见 `hermes/reports/2026-06-05-0146-aigw-mcp-gateway-products.md`

### 协议 / 标准
- Kubernetes Gateway API Inference Extension（GIE）：`https://gateway-api.sigs.k8s.io/geps/gep-1619/`
- Agent-to-Agent (A2A) Protocol：参考 Google ADK / LangChain a2a 规范
- llm-d：`https://llm-d.ai/`
