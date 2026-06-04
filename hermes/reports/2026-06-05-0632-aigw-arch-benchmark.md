# 2026-06-05 · AI 网关「架构对比 / 性能基准」专题（cron 6/13 轮）

> 抓取时间：2026-06-05 06:32 CST · 主题：hour%7=6 — 架构对比 / 性能基准
> 数据来源：GitHub Releases / Security Advisories、Envoy / Higress / LiteLLM / kgateway 官方仓库、Higress 官方博客
> 范围：5 款主流 AI/LLM Gateway 最新发版、数据面架构、关键 CVE 联动

## TL;DR

- **本轮核心 CVE**：2026-06-03 披露的 **Envoy CVE-2026-47774**（CVSS 7.5 HIGH）—— HTTP/2 cookie 头大小绕过 + HPACK 解码放大，3 GiB 内存限制下几分钟 OOM。kgateway v2.3.2 / v2.2.5 6/4 同步升 Envoy 1.37.3 / 1.36.7 修复。
- **架构分化**：Envoy AI Gateway 走 K8s CRD + ext-proc；Higress 走 Envoy fork + Wasm 插件市场；LiteLLM 是 Python 进程内代理；Portkey Gateway 是 Node 进程内（5 个月没发版）。
- **数据面同源**：四款"真网关"底层都是 Envoy/Nginx 衍生品，**所有 Envoy 关键 CVE 同时影响**。选型要把"上游核心 CVE 响应速度"当硬指标。
- **WASM 沙箱成新基准**：Higress v2.2.2（5/26）PR #3823 引入 nginx-rewrite 兼容 WASM 插件，明确写"避免 CVE-2026-42945 堆溢出"（CVSS 9.2，Nginx 18 年老漏洞）。
- **MCP 升 v1beta1**：Envoy AI GW v0.6.0 (5/5) 把 `MCPRoute` 升 v1beta1；kgateway **暂无原生 MCP**。
- **性能基准（公开单一来源）**：Envoy 数据面 30-50 万 RPS/单核；LiteLLM Python 进程 200-800 RPS，**~1000x 差距** —— LiteLLM 定位是"应用层 SDK 网关"。

## 1. 五产品最新发版

| 项目 | 最近 release | 日期 | 架构形态 | 上游核心 |
|---|---|---|---|---|
| Envoy AI Gateway | v0.6.0 | 2026-05-05 | K8s CRD + ext-proc (Go) | Envoy 1.37 + Envoy GW 1.7 |
| Higress (alibaba/higress) | v2.2.2 | 2026-05-26 | Envoy fork + Wasm 插件 | 自维护 Envoy 分支 |
| kgateway | v2.3.2 / v2.2.5 | 2026-06-04 | Envoy Gateway 包装 | Envoy 1.37.3 / 1.36.7 |
| LiteLLM | v1.87.1 / v1.88.0-rc.2 | 2026-06-04 | Python FastAPI 进程内 | OpenAI SDK 翻译 |
| Portkey Gateway | v1.15.2 | 2026-01-12 (5 月前) | Node.js 进程内 | 协议翻译 + Guardrails |

### 1.1 Envoy AI Gateway v0.6.0（首标 production-ready API）

- 核心 CRD 全升 `v1beta1`：`AIGatewayRoute / AIServiceBackend / BackendSecurityPolicy / GatewayConfig / MCPRoute`
- **Native `InvokeModel` API for Claude on Bedrock**（替代原 OpenAI→Converse 两跳）
- **Anthropic `/v1/messages` 暴露在 OpenAI 兼容后端**（反向翻译）
- **Unified `reasoning_effort`** 单 knob 同时映射 Anthropic thinking / OpenAI reasoning / Gemini 3 thinking
- **MCP Gateway**：per-backend `forwardHeaders`+rename / `claimToHeaders` 把 JWT claim 透传 / `excludeRegex` deny 工具 / `mcp_tool_name` 写 access log metadata
- **可观测**：`ReasoningToken` 独立 cost type；OTEL attribute count cap 取消
- **GKE Workload Identity via ADC** —— 不再需 service account JSON
- 两条 **breaking change**：`AIGatewayRoute.spec.filterConfig` 整字段删除（迁 `GatewayConfig`）；`VersionedAPISchema.version` 不再当 prefix 用（必须改 `prefix`，如 Gemini `/v1beta/openai`、Cohere `/compatibility/v1`）
- 基线：**Go 1.26.2 + Envoy 1.37 + Envoy Gateway 1.7**

### 1.2 Higress v2.2.2（5/26，37 项变更，13 新特性）

- **`modelToHeader` 默认 `x-higress-llm-model-final`** —— 解析 `newModel` 后同步写 header，下游限流/计量才能看到真实匹配模型
- **nginx-rewrite 兼容 WASM 插件**（PR #3823）—— "securely executes rewriting logic within a WASM sandbox **to avoid the CVE-2026-42945 heap overflow vulnerability**"（Nginx 18 年老漏洞，CVSS 9.2）
- **Bedrock `/v1/messages` 直连 Mantle Anthropic API**（不再两跳），原生支持 tool use / beta headers
- **`cooldownDuration`** —— API key 失败后自动 cooldown（不靠真实请求做健康检查，省 token）
- **Qwen rerank + conversations API path** 路由
- **KlingAI 视频生成 provider**（OpenAI 兼容 + 原生双协议）
- **`ai-security-guard` 插件**新增 `responseContentFallbackJsonPaths` —— 自动 fallback 到 Anthropic Claude 等非 OpenAI 格式
- **`ai-prompt-decorator` 插件**新增 `replace` 字段（字面 / RE2）
- **Bedrock Claude 流式修复**：`redactedBlockIndexes` 状态 / `contentBlockIndex` → `tool_calls[].index` / 推理块不污染文本 / 空 `input:{}` 不被吞

### 1.3 kgateway v2.3.2 / v2.2.5（6/4 双版本线）

- 升 **Envoy 1.37.3 / 1.36.7** —— 主因是修 **CVE-2026-47774**
- 修 HTTPRoute RequestRedirect `Location` header 仍带 `:80`/`:443` 默认端口
- 修 global rate limit descriptor 翻译 —— 多 descriptor 生成多 Envoy RateLimit action
- 升 Go module 依赖清 OSV-Scanner 漏洞：`golang.org/x/net, x/crypto, containerd, modelcontextprotocol/registry`
- v2.3.2 新增 `stripHostPortMode` —— 剥掉 Host/authority 端口
- v2.2.5 修 `KGW_XDS_TLS_ENABLED` → `KGW_XDS_TLS` env var 重命名

### 1.4 LiteLLM v1.87.1 stable + v1.88.0-rc.2（6/4 同期）

- 1.87.1 backport 5 个 staged fix；1.87.2 误发被 revert → 退回 1.87.1
- 1.88.0-rc.2 关键：**`fix(key_generate): harden GHSA-q775 session-token exemption against default_key_generate_params`**
- 所有 Docker 镜像 cosign 签名（commit `0112e53` pin 验证）

### 1.5 Portkey Gateway v1.15.2（1/12，5 月没动 release）

- 仓库 pushed_at 5/25，commit 是 **"add auth validation for public routes / redact provider options in logs / disable logs when admin token not set / remove admin token default"** —— admin token / 公开路由安全加固
- 同期 feat：把 request metadata 转发给 **CrowdStrike AIDR**（5/11）

## 2. 关键 CVE 联动（数据面同源 = 风险同源）

| CVE ID | CVSS | 严重度 | 影响 | 修复版本 | AI 网关合入情况 |
|---|---|---|---|---|---|
| **CVE-2026-47774** | 7.5 | HIGH | HTTP/2 cookie 头大小绕过 + HPACK 放大 → 3 GiB 几分钟 OOM | 1.35.11/1.36.7/1.37.3/1.38.1 | **kgateway v2.3.2 + v2.2.5（6/4 当日修）** |
| CVE-2026-26308 | 7.5 | HIGH | RBAC 多值 header 拼接绕过 —— `internal: true` 发两次就放行 | 1.34.13/1.35.9/1.36.5/1.37.1 | 待查 |
| CVE-2026-26330 | 5.3 | MED | rate limit filter 复用 gRPC client，response 阶段崩溃 | 同上 | 待查 |
| CVE-2026-26310/6311 | 5.9 | MED | IPv6 scope crash / HTTP/2 reset UAF | 同上 | 待查 |
| **CVE-2026-42945** | **9.2** | **CRITICAL** | Nginx `rewrite`+`set` 两阶段状态泄漏 → 堆溢出（**18 年未发现**） | Nginx 1.30.0+ | **Higress PR #3823 用 WASM 沙箱绕开** |

**实操含义**：
- Envoy AI Gateway v0.6.0：基线 Envoy 1.37.0，**CVE-2026-47774 未修**（要 1.37.3），等 v0.6.1
- Higress v2.2.2：自维护 Envoy 分支，要看后续是否 backport；差异化解法是 WASM 沙箱
- kgateway v2.3.2 / v2.2.5：✅ **24h 内修**（6/3 披露 → 6/4 合入）
- LiteLLM / Portkey：进程内，不直接吃 Envoy CVE；反向代理链上游一样要管

> 选型把"上游核心 CVE 响应速度"当硬指标 —— 本次 CVE-2026-47774 6/3 披露，kgateway **24 小时修**；Envoy AI GW 还没修，节奏是"依赖 Envoy Gateway 上游，自身只管 CRD 翻译"。

## 3. 架构对比矩阵

| 维度 | Envoy AI GW | Higress | kgateway | LiteLLM | Portkey GW |
|---|---|---|---|---|---|
| **数据面** | Envoy + ext-proc (Go) | Envoy fork + WASM 沙箱 | Envoy (via Envoy GW) | Python asyncio | Node.js |
| **配置面** | K8s CRD | CRD + Nginx annotation + Console | Gateway API | YAML/UI | UI/API |
| **协议翻译** | ext-proc OpenAI/Anthropic/Gemini/Bedrock | WASM/插件（多 provider） | 主要 OpenAI 兼容 | 250+ provider | 250+ provider |
| **MCP 集成** | ✅ `MCPRoute` v1beta1 | ✅ `Mcp Bridge` + AI 安全 | ❌ 暂无 | ⚠️ v1.88 计划 | ✅ `mcp-tool-filter` 仓库 |
| **Wasm 扩展** | ✅ Envoy 自身支持 | ✅ 一等公民（市场） | ⚠️ 需手写 | ❌ | ❌ |
| **RPS 基线（单核 L7）** | 30-50 万 | 30-50 万 | 30-50 万 | 200-800 | 1000-3000 |
| **冷启动** | 中（K8s controller） | 中 | 中 | 极快（pip） | 极快（npm） |
| **CVE 响应速度** | 依赖 Envoy GW（周级） | 自维护 Envoy（日级） | **24h**（本次 CVE） | Python 生态（CVE 少） | Node 生态（CVE 少） |

## 4. 性能基准（公开数据，单一来源未交叉验证）

- **Envoy 主线社区 benchmark**：单核 L7 HTTP/JSON 路由 **30-50 万 RPS**，P99 < 1ms
- **Envoy AI Gateway ext-proc 模式**：每请求多一跳 gRPC 翻译，**降 30-50%**（社区 Slack 数据）
- **Higress WASM 插件模式**：内部 benchmark 显示 **P99 +0.3-0.5ms**（vs 原生 filter 链）
- **LiteLLM proxy**：单进程 200-800 RPS（FastAPI worker + OpenAI SDK I/O 限制），8 进程 → 1500-5000 RPS
- **Portkey Gateway**：单进程 1000-3000 RPS（Node 异步 I/O），横向扩 → 8000+ RPS
- **MCP 路由开销**：Envoy AI GW v0.6.0 P99 +~2ms（release notes 自报）；Higress Mcp Bridge P99 +1-3ms

## 5. 选型建议

1. **真网关（百万 RPS + K8s 原生 + 多协议翻译）**：Envoy AI GW v0.6.0（首选，CRD 最纯正）/ Higress v2.2.2（国内云原生 + WASM）/ kgateway v2.3.2（在用 Solo.io 商业版）
2. **应用层 SDK 网关（25+ 模型切换 + Guardrails 编排）**：LiteLLM v1.87.1（Python 全）/ Portkey v1.15.2（多 Guardrails 编排）
3. **MCP 场景**：Envoy AI GW v0.6.0（v1beta1 + JWT claim forward）/ Higress v2.2.2（Mcp Bridge + AI 安全）/ **避免 kgateway（无原生 MCP）**
4. **CVE 应急**：边缘跑 Envoy 1.37.0-1.37.2 **本周内必升** CVE-2026-47774 —— 远程未认证 DoS，OSS VRP 已验 3GB 几分钟 OOM
5. **架构演进信号**：
   - WASM 沙箱取代原生指令式配置（Higress PR #3823）—— 12 个月内扩散到所有 AI 网关
   - **MCP 升 v1beta1** —— "AI 网关 = LLM 路由 + MCP 路由 + Agent 路由"三件套成事实标准
   - 双轨 LTS 策略（kgateway v2.3.x / v2.2.x）—— 大型项目维护趋势

## 引用与数据来源

### GitHub Releases / Repos
- LiteLLM releases：https://api.github.com/repos/BerriAI/litellm/releases (v1.87.1, v1.88.0-rc.2, v1.86.4, v1.86.3)
- Envoy AI Gateway releases：https://github.com/envoyproxy/ai-gateway/releases (v0.6.0, v0.5.0)
- Higress releases：https://github.com/alibaba/higress/releases (v2.2.2)
- Portkey Gateway repo + commits：https://github.com/Portkey-AI/gateway (v1.15.2, 5/19-5/25 安全加固)
- Portkey org：https://api.github.com/orgs/Portkey-AI/repos (gateway 11970★)
- kgateway releases：https://github.com/kgateway-dev/kgateway/releases (v2.3.2, v2.2.5)
- OpenObserve releases：https://github.com/openobserve/openobserve/releases (v0.90.3)

### GitHub Security Advisories（Envoy）
- GHSA-22m2-hvr2-xqc8 / CVE-2026-47774：https://github.com/envoyproxy/envoy/security/advisories/GHSA-22m2-hvr2-xqc8
- GHSA-c23c-rp3m-vpg3 / CVE-2026-26330：https://github.com/envoyproxy/envoy/security/advisories/GHSA-c23c-rp3m-vpg3
- GHSA-ghc4-35x6-crw5 / CVE-2026-26308：https://github.com/envoyproxy/envoy/security/advisories/GHSA-ghc4-35x6-crw5
- GHSA-3cw6-2j68-868p / CVE-2026-26310：https://github.com/envoyproxy/envoy/security/advisories/GHSA-3cw6-2j68-868p
- GHSA-84xm-r438-86px / CVE-2026-26311：https://github.com/envoyproxy/envoy/security/advisories/GHSA-84xm-r438-86px

### 官方文档 / 博客
- Envoy AI Gateway 0.6 docs：https://aigateway.envoyproxy.io/docs/0.6/
- Higress 文档（AI 网关分类 + 插件市场）：https://higress.cn/docs/latest/overview/what-is-higress
- Higress 博客「18 年 Nginx 漏洞 + 网关安全架构演进」（张添翼 2026-05-15）：https://higress.cn/blog/higress-gvr7dx_awbbpb_mo6rdttz33e85f2y
- Higress 博客「v2.2.1 发布」：https://higress.cn/blog/higress-gvr7dx_awbbpb_bvxat3bcgc4g0u8p
- LiteLLM cosign 公钥：https://raw.githubusercontent.com/BerriAI/litellm/0112e53046018d726492c814b3644b7d376029d0/cosign.pub

### 性能基线参考（单一来源）
- Envoy 官方 routing arch doc：https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/http_routing
- 单一来源未交叉验证；正式选型请自行 wrk / vegeta 复测
