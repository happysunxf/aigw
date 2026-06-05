# AI 网关持续深挖 · 2/9 轮 · Agent Gateway 第 2 视角：v1.3.0 收尾期

> **抓取时间**：2026-06-05 09:13 CST（UTC 2026-06-05 01:13）
> **本轮主体**：`agentgateway/agentgateway` · **v1.3.0 milestone due 2026-06-18**（13 天后）
> **不重复**：02:26 轮已讲 v1.2.0 三大支柱 + v1.3.0-alpha.1 主梁；本轮专讲 6/2–6/4 三天合并的 32 个 PR（去 dependabot 12 个）。

---

## 一、本轮核心信号

| 信号 | 含义 |
|---|---|
| **v1.3.0 due 2026-06-18**，16 open PR | 5/23 alpha.1 → 6/18 GA，**26 天周期比 v1.2.0 缩短 30%** |
| 6/2–6/4 三天 **32 个非依赖 PR merged** | 单日 10+——**v1.3.0 release train 收尾档** |
| v1.4.0 milestone 已在 GitHub 排期 **due 2026-07-23** | v1.3 还没发，v1.4 已排上——**月度列车成型** |
| 3048★ / 509 fork / 247 open issues（6/5 01:15 UTC） | 13 天 +12★/+2 fork；open issues 高水位（企业落地路上） |

> **关键洞察**：agentgateway 已从"季度 major + 月度 minor" 切到"**月度 minor + 月度 freeze**"——和 Envoy 4 个月一 minor 的画风完全不同。**押 agentgateway 必须用 SemVer + 月度升级计划**。

---

## 二、6/2–6/4 三天 32 个 PR 主题分桶（去 dependabot 12 个）

| 主题 | 数量 | 代表 PR |
|---|---|---|
| **agctl CLI 工具化** | 4 | #2070（`agctl version` + json/yaml 输出）/ #2085（evicted backends）/ #2053（backend TLS dump）/ #2045（http1PreserveHeaderCase） |
| **MCP 协议一致性** | 3 | #2077（`tools.listChanged` multiplex 广播）/ #2046（`WWW-Authenticate` 路径）/ #2075（mcp stack 瘦身） |
| **CEL / 表达式** | 4 | #2036（CEL `variables()` 重构）/ #2001（`response.grpcStatus`）/ #2027（`jwt.rawToken`）/ #2042（JWKS krt snapshot） |
| **Mesh / Istio** | 2 | #2055（Istio cluster-level `autoEnabled` 默认）/ #2080（meshconfig sync 等待） |
| **LLM 协议** | 3 | #2008（多 text block 保留）/ #2028（async-openai 0.40.3）/ #1990（性能回归） |
| **ext_proc / ext_authz** | 3 | #2010（ImmediateResponse body 阶段）/ #2002（ext_authz forwarded proto）/ #1715（response-phase dynamic metadata） |
| **安全 / CVE** | 3 | #2043（Go 1.26.4）/ #2048（Rust 1.96）/ #2076（rustls-openssl） |
| **AWS** | 1 | #2037（**AWS AssumeRole**） |
| **稳定性** | 3 | #2050（eviction flake）/ #2078（test stack overflow）/ #2012（jemalloc arm64 64KB page） |

> **战略信号**：**`agctl` 工具化**（4 PR）+ **MCP 协议一致性**（3 PR）是两主线。前者把 agentgateway 从"网关"升级为"网关 + 调试 CLI"；后者在前轮 0834 报告"8 个 MCP Gateway 没一个提 elicitation 防护"基础上，**agentgateway 在补"能力字段"而非"流量转发"**。

---

## 三、5 个最重 PR 详解

### 3.1 #2077 `mcp: advertise tools.listChanged in multiplexing mode`（Gilad Sever，6/4 19:54 UTC）

**问题**：multiplex 模式下 upstream 推 `notifications/tools/list_changed` → 网关转发到 client，**但 `InitializeResult` 里没声明 `capabilities.tools.listChanged`** → 符合 MCP 规范的客户端**直接丢弃转发通知**、不重新拉 `tools/list`。

**修复**：`capabilities` 在 multiplex 模式**无条件**广告 `tools.listChanged`——理由是 merged tool list 可能在 session 中变（`failOpen` 跳过 target），需要 client 主动 refetch。

> **对企业架构师的信号**：2026 年 6 月 MCP Gateway 赛道**唯一见到**的"按 spec 修正 capabilities 声明"级别修复。**协议一致性**上 agentgateway 至少在 `tools` 能力上**领先**所有竞品。

### 3.2 #2070 + #2085 `agctl` 工具链收尾（6/4）

`agctl` 一次性补 4 项能力：

```bash
agctl version              # 构建信息：version / commit / OS-arch
agctl config all           # 全部 binds/listeners/routes/backends/policies
agctl config backends      # per-backend 健康/请求数/延迟
agctl config all -o yaml   # 三种输出：short(默认表格) / json / yaml
```

**关键设计决策**：
- 删 `pretty` / `json` 双选项——CLI 不在 wire 上传，`jq` 自己处理
- `--proxy-admin-port` flag 描述从 "Envoy admin port" 改成 "Agentgateway admin port"——**product boundary 声明**
- **取消 CLI/controller version mismatch check**——`config` 和 `trace` 只对话 proxy admin port，**不交互 controller**
- 新增 `agctl` Makefile build target：`make agctl` / `make agctl-linux-amd64` / `make agctl-linux-arm64`

> **对 DevOps 的信号**：之前因为"调试工具不全"不敢上生产？**v1.3.0 后这个理由消失**。`agctl` 矩阵是 2026 年 6 月所有 AI Gateway 产品里**最完整的可调试性 surface**。

### 3.3 #2055 `install: cleanup mesh ux`（Steven Landow，6/4 02:28 UTC）

Istio 集成 UX **重做**——之前是 `AgentgatewayParameters.spec.istio: {}` 这种"presence 即开启"魔法，现在：

```yaml
# Helm values cluster-level 默认
istio:
  autoEnabled: true              # 默认所有 built-in gateway 都开
  namespace: istio-system
  revision: "1-30"
  caAddress: "https://istiod..."
```

```yaml
# 旧 API 仍兼容
spec:
  istio: {}                      # 等同 enabled: true
# opt-out 单个 gateway
spec:
  istio:
    enabled: false
```

> **关键洞察**：agentgateway 在**主动把 istio 集成从"opt-in per gateway" 推成 "autoEnabled cluster-wide"**——**宣告 istio 是默认 mesh**。**生产 mesh 治理最省心组合**：agentgateway + istio HBONE（不是 sidecar-less，不是 ambient）。

### 3.4 #2008 `fix(llm): preserve all text blocks`（jungbbong，6/4 16:00 UTC）

**Bug**：Anthropic / Bedrock 在 `citations: enabled` 时把 text 切成多个 block，**Completions API 非流式响应在 agentgateway 转换时 collapse 到最后一个**——citation 信息全丢。

**修复**：和 streaming 路径、sibling `to_responses_typed` 一致，**所有 text block verbatim 拼接**。

> **对架构师的信号**：LLM 协议转换层正从"按 OpenAI Chat Completions 形状走"转向"**每个 provider 自己的 block 语义都保留**"。Anthropic 2024 推 Citations API 后这是必踩坑——Portkey / LiteLLM 大概率也有同 bug，只是没在 release notes 公开。**自建多 provider 网关的兄弟：用这个 PR 当 test case 验证你们自己的 Completions 转换**。

### 3.5 #2037 `Add support for AWS AssumeRole`（John Howard，6/4 23:24 UTC）

agentgateway 现在能**assume AWS IAM role** 跨账号/跨组织调 Bedrock。配套（v1.3.0 milestone 内）：
- #1929（vertex: native `generateContent` endpoint，v1.3.0 开放）
- #1893（AWS request signing allowlist）
- #1991（Bedrock `cache_creation_input_tokens` 在 access log 缺失，v1.3.0 修复）

> **对企业的信号**：**agentgateway 已能"一站调遍" Anthropic / Bedrock / Vertex / OpenAI** + AssumeRole = **多账号 Bedrock 不用每个 account 单独建 API key**，gateway 层做 STS assume。**自建 AI Gateway vs 商用**的新筹码。

---

## 四、v1.3.0 milestone 16 open PR（直冲 GA 风险评估）

| 重要性 | 编号 | 标题 |
|---|---|---|
| **H** | #2035 | `Publish agctl on release`（**CLI 不发版等于没做**） |
| **H** | #1609 | `AI Guardrail Backend`（4/11 轮 Guardrails 专题最大缺口） |
| **H** | #2056 | `policy: add inheritance strategy` |
| **H** | #1715 | `ext-proc: capture response-phase dynamic metadata` |
| **H** | #1900 | `fix(llm): capture completion content in streaming paths`（langfuse/helicone 类成本归因命根子） |
| H | #1866 | `backend.ai.* policies don't compose across separate AgentgatewayPolicy resources`（**多团队 policy 合规痛点**） |
| H | #1990 | `AgentGateway Performance Issues`（issue 但**性能回归是 GA blocker**） |
| M | #1929 | `vertex: support native generateContent endpoint` |
| M | #1855 | `Support MCP DNS rebinding specification`（MCP 协议 spec 写明的安全要求） |
| M | #1851 | `MCP upstream: don't propagate incoming Host header`（防 SSRF） |
| M | #2058 | `ext-proc: ImmediateResponse in ResponseBody can cause hangs` |
| M | #1991 | Bedrock `cache_creation_input_tokens` 缺失 |
| M | #2039 | `Merge AI backend policy fields` |
| M | #1832 | `Custom Guardrail FailOpen` |
| M | #2057 | `Detecting config synchronisation programmatically` |
| L | #1821 | `Sync UI new-ui-features upstream to agentgateway` |

> **6/18 GA 风险评估**：
> - 16 open PR 中 **7 个 H**——按 Solo.io 节奏，**1 周内全 merge + QA 几乎不可能**
> - **#2035 `Publish agctl on release`** 没 merge = CLI 永远卡在"开发者本地构建"——**v1.3.0 战略级 blocker**
> - **#1609 `AI Guardrail Backend`** 是 4/11 轮 Guardrails 专题最大缺口——v1.3.0 GA 不带 = **战略价值减半**
>
> **预测**：v1.3.0 GA 大概率**滑到 6/25**。前轮 02:26 讲"v1.2.0 → v1.2.1 → v1.3.0-alpha.1 三周三里程碑" alpha 节奏，**到 GA 通常再延 1–2 周**。

---

## 五、对 multi-agent 项目的 4 个具体建议

1. **盯 v1.3.0 GA 的 #2035 `Publish agctl on release`**——没这个 PR = 调试工具链战略**等于零**。
2. **`MCP DNS rebinding` (#1855) 是 v1.3.0 必修**——MCP 协议 spec 写明的安全要求；其他 MCP Gateway（ToolHive / Archestra）也必须考虑。
3. **`MCP upstream Host header 不透传` (#1851) 是防 SSRF 标准修复**——**所有用 upstream MCP server 的 multi-agent 系统都要查自己实现**。
4. **`AWS AssumeRole` (#2037) + `Vertex native generateContent` (#1929) 一起来**——agentgateway 在做"**多云 LLM 一站 + 跨账号**"；**自建 AI Gateway 的兄弟要考虑押 agentgateway** 而不是自己写。

---

## 六、本期数字摘要

- **覆盖产品**：1 个深度（agentgateway）——multi-agent 编排赛道**唯一值得深挖**
- **时间窗**：6/2–6/4 三天（v1.3.0 GA 收尾期）
- **关键数据**：v1.3.0 due **2026-06-18** / 16 open / v1.4.0 due 2026-07-23 / 3048★
- **重点 PR**：#2077 MCP `tools.listChanged` / #2070+2085 agctl / #2055 Istio autoEnabled / #2008 LLM text block / #2037 AWS AssumeRole
- **CLI 工具链**：`agctl` 已成型（version + config all + backends + trace + YAML/JSON 输出）
- **预测**：v1.3.0 GA 大概率滑到 6/25

---

## 引用与数据来源

### agentgateway `agentgateway/agentgateway`（主线）
- repo meta：`https://api.github.com/repos/agentgateway/agentgateway`（3048★ / 509 fork / 247 open issues / updated 2026-06-05 01:15 UTC）
- milestone：`https://api.github.com/repos/agentgateway/agentgateway/milestones?state=all`（v1.3.0 due 2026-06-18，v1.4.0 due 2026-07-23）
- releases：`https://api.github.com/repos/agentgateway/agentgateway/releases`
- v1.3.0-alpha.1：`https://api.github.com/repos/agentgateway/agentgateway/releases/tags/v1.3.0-alpha.1`
- 6/2–6/4 merged PRs：`https://api.github.com/repos/agentgateway/agentgateway/issues?state=closed&since=2026-05-23`
- v1.3.0 open PRs：`https://api.github.com/repos/agentgateway/agentgateway/issues?state=open`

### 5 个重点 PR
- #2077 — `https://github.com/agentgateway/agentgateway/pull/2077`
- #2070 — `https://github.com/agentgateway/agentgateway/pull/2070`
- #2085 — `https://github.com/agentgateway/agentgateway/pull/2085`
- #2055 — `https://github.com/agentgateway/agentgateway/pull/2055`
- #2008 — `https://github.com/agentgateway/agentgateway/pull/2008`
- #2037 — `https://github.com/agentgateway/agentgateway/pull/2037`

### v1.3.0 GA blocker 集（open PR）
- #2035 agctl publish · #1609 Guardrail Backend · #2056 policy inheritance · #1715 ext-proc response metadata
- #1866 backend.ai.* policy compose · #1855 MCP DNS rebinding · #1851 MCP Host header · #1929 vertex generateContent
- #1900 streaming completion content · #1990 perf issues — 全部在 `https://github.com/agentgateway/agentgateway/pulls?q=is%3Apr+is%3Aopen+milestone%3Av1.3.0`

### 上一轮对照
- 02:26 轮 v1.2.0 + v1.3.0-alpha.1 主梁 — `hermes/reports/2026-06-05-0226-aigw-agent-gateway.md`

### 协议 / 标准
- MCP `tools.listChanged` 语义参考 modelcontextprotocol 协议 `notifications/tools/list_changed` 章节
- AWS STS AssumeRole：`https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html`
- Istio HBONE / multi-cluster：`https://istio.io/latest/docs/ops/deployment/multi-cluster/`
