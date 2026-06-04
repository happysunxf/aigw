# AI 网关持续深挖 · 第 0/7 轮 · LiteLLM 发版追踪

> **抓取时间**：2026-06-05 00:34 CST（UTC 2026-06-04 16:34）
> **主题**：单产品发版追踪 → **LiteLLM**
> **数据源**：`https://api.github.com/repos/BerriAI/litellm/releases`（未鉴权公开 API）
> **方法**：直接读取 GitHub Releases 元数据 + PR 标题摘要，去噪后整理

---

## 一、本次主题选择

按 cron 规则 `local hour % 7` = 0 → 主题「单产品发版追踪」，本轮聚焦 **LiteLLM**（7 款轮换产品序列的第一个）。后续每 7 个轮次（≈3.5 小时）会切到下一款：LiteLLM → Portkey → Envoy AI GW → Higress → Kong → Helicone → OpenRouter，再循环。

---

## 二、LiteLLM 近期发布节奏（2026-05-31 ~ 2026-06-04）

5 天内连续发了 **6 个 tag**，平均不到一天一个。LiteLLM 团队当前是「多分支并行维护 + 高频 patch backport」的模式：

| Tag | 发布时间 (UTC) | 类型 | 备注 |
|---|---|---|---|
| `v1.88.0-rc.1` | 2026-05-31 04:31 | **预发布 (prerelease)** | 下一个大版本候选，含 40+ PR 合并 |
| `v1.87.0` | 2026-06-02 04:12 | GA | **首个支持 Gemini 3.5 Flash / 3.1 Flash-Lite** 的版本 |
| `v1.85.3` | 2026-06-02 02:30 | stable patch | 5 个 PR cherry-pick |
| `v1.86.3` | 2026-06-03 01:40 | stable patch | 1.86.x 分支 backport |
| `v1.85.4` | 2026-06-04 05:16 | stable patch | 1.85.x 分支 backport |
| `v1.84.5` | 2026-06-04 04:11 | stable patch | 1.84.x 分支 backport |

**观察**：LiteLLM 当前同时维护 **1.84 / 1.85 / 1.86 三个 stable 分支** + 1.88 mainline 候选，patch backport 频率 ≈ 24 小时——这是企业级 LLM 网关该有的"三轨制"节奏。

---

## 三、v1.88.0-rc.1 —— 下一个大版本值得关注的 10 个 PR

从 40+ merged PR 中筛出对网关架构有实质影响的：

1. **`feat(mcp): support stateless and stateful clients via session-id routing`** (`#26857`)
   - MCP server 同时支持 stateless 和 stateful 客户端，通过 session-id 路由
   - 这是 LiteLLM 把自己定位成"MCP Gateway"的关键工程动作——目前其他家要么纯 stateless 要么纯 stateful，二者并存是更大的设计挑战

2. **`feat(mcp): allow native MCP OAuth support for cursor`** （v1.87.0 已合入）
   - 支持 Cursor IDE 的原生 MCP OAuth 流程
   - 配套 v1.88 还有 `feat(mcp/auth): additive key access-group grants + opt-in member assignment` (`#29313`)——把 MCP 访问纳入现有的"key → access_group"权限模型

3. **`feat(otel): typed semconv-aligned OpenTelemetry instrumentation`** (`#28909`)
   - **按 OpenTelemetry semantic conventions 重写 instrumentation**，输出 typed span
   - 这是 LiteLLM 在可观测领域"对齐生态标准"的标志性 PR——之前 span 是自定义 attribute，外部 trace 工具（Honeycomb / Datadog / Grafana）要写特殊解析

4. **`feat(otel): add team_metadata, http.route, and model names to inference spans`** (`#29319`)
   - span 上多带 `team_metadata` / `http.route` / model name，**OTEL 终于能按团队、按模型切分成本/延迟**

5. **`feat(a2a): well-known agent-card discovery + LangGraph Platform mode`** (`#28860`)
   - A2A (Agent-to-Agent) 协议支持：通过 `.well-known/agent-card.json` 发现 agent
   - 同时支持 LangGraph Platform 模式——开始跨入 Agent Gateway 领域

6. **`fix(proxy): link passthrough success spans to the SERVER root OTEL span`** (`#29315`)
   - passthrough 模式下，外部请求的 span 正确链接到 proxy server 根 span
   - 配合上面 #28909 的 typed semconv，整体 OTEL trace 拓扑会大幅改善

7. **`fix(guardrails): return HTTP 400 for litellm content filter blocks`** (`#28418`)
   - guardrail 拦截后返回 **HTTP 400**（之前可能 200/422 不一致），客户端 SDK 终于能用统一 status code 判断"内容被拒"

8. **`fix(otel): emit guardrail span on violation, surface status + categories`** (v1.87.0)
   - guardrail 命中时单独 emit 一个 span，附带 status 和 category（"PII" / "toxic" / "jailbreak"），审计可观测性补齐

9. **`feat(guardrails): add Microsoft Purview DLP guardrail`** (v1.87.0)
   - 集成 Microsoft Purview DLP——企业合规场景补一块

10. **`feat(pass_through): extend passthrough_managed_object_ids to Azure`** (`#29160`)
    - pass-through 路由管理的 object id 扩展到 Azure
    - 多云一致管理前进一小步

---

## 四、v1.87.0 重点（GA 版）

- **Day 0 支持 Gemini 3.5 Flash** + **Gemini 3.1 Flash-Lite**（含模型 cost map）
- **Gemini managed agents support**（Gemini 原生 Agent SDK 透传）
- **feat(interactions): migrate to Google Interactions API steps schema (May 2026)** —— 跟进 Google 新版 Interactions API
- **`fix(deepseek): use native /anthropic/v1/messages endpoint and sanitize tools`** —— DeepSeek 走 Anthropic 兼容端点 + 工具清洗
- **`feat(azure): add Speech STT config support`** —— Azure 语音转文字配置支持
- **`Add granian as an ASGI compliant web server`** —— 引入 granian（Rust 写的 ASGI server）作为备选，**per-request / per-chunk overhead 在 Anthropic 流式路径下降**（commit message 原文）
- **`feat(mcp): JWT on tools/list and REST tools/call server resolution`** —— MCP 调用的 JWT 鉴权
- **`feat(mcp): Add tool call and tool list support via UI for Oauth mcps`** —— UI 上配置 OAuth MCP server
- **`Encrypt callback_vars in key/team metadata in DB`** —— **数据库中 key/team 元数据的 callback_vars 加密存储**
- **`feat(prometheus): emit per-token-type detail metrics (LIT-3220)`** —— Prometheus 按 token 类型（input/output/cache_read/cache_write）拆开打点
- **`feat: propagate team_id and team_alias to all child OTEL spans`** —— 子 span 携带 team 标识

---

## 五、Docker 镜像签名（供应链安全）

所有 LiteLLM 官方 Docker 镜像 (`ghcr.io/berriai/litellm:*`) **统一用 cosign 签名**，签名 key 钉在 commit `0112e53046018d726492c814b3644b7d376029d0`。每个 release 页面都给出两套 verify 命令：

- **按 commit hash 验签**（推荐，最强）
- **按 tag 验签**（方便，依赖 tag 保护规则）

这意味着 LiteLLM 已经在走 SLSA / sigstore 供应链安全实践——其他几家（Portkey、Helicone、Envoy AI GW）目前公开文档里**没有看到对应的镜像签名机制**。

---

## 六、值得追踪的几个信号

1. **OTEL 重大重写（v1.88）**：typed semconv + 团队/模型 metadata 下沉到 span，意味着 LiteLLM 正在向"可观测一等公民"靠拢。对使用 OTel Collector 的企业是利好。
2. **MCP OAuth 全面化**：从 v1.87 开始的 `feat(mcp): allow native MCP OAuth support for cursor`、`feat(mcp): JWT on tools/list`、`feat(mcp): Add tool call and tool list support via UI for Oauth mcps`——MCP server 的鉴权/注册能力在快速补齐。
3. **Granian 引入**：选型从 uvicorn 切到 granian，号称"更好的吞吐稳定性"——LiteLLM 团队对"网关性能"这件事开始认真做 benchmark。
4. **A2A 协议入场**：`#28860` 支持 `.well-known/agent-card.json`——A2A 协议在 2026 年从"Google 内部规范"开始被开源网关采纳。
5. **稳定分支多轨制**：1.84 / 1.85 / 1.86 三个 stable 同时在 backport，意味用户能选"长尾维护版"或"快迭代版"。

---

## 七、本轮没改的，留给后续

- v1.88 GA（rc 之后的稳定版）何时出
- LiteLLM 与 LiteLLM Proxy（企业版）的边界是否会在 1.88 进一步清晰
- granian 替换 uvicorn 后的官方 benchmark 数据

---

## 八、推送状态

- 目标仓库：`happysunxf/aigw@main`
- 尝试 PUT 时间：2026-06-05 00:34 CST
- 结果：**HTTP 401 Bad credentials**（GitHub PAT 失效或被吊销）
- 处置：报告 + CHANGELOG delta 已落本地 `~/hermes/reports/` 与 `~/hermes/CHANGELOG_DELTA.md`，列入 `~/hermes/PENDING_PUSH.md` 待下次 cron 补推
- 备注：未鉴权 GET（公开仓库 + 公开 Releases API）正常工作，仅写入端需要有效 PAT

---

## 引用与数据来源

- LiteLLM GitHub Releases（未鉴权公开 API）：
  - `https://api.github.com/repos/BerriAI/litellm/releases?per_page=8`
  - `https://api.github.com/repos/BerriAI/litellm/releases/tags/v1.88.0-rc.1`
  - `https://api.github.com/repos/BerriAI/litellm/releases/tags/v1.87.0`
  - `https://api.github.com/repos/BerriAI/litellm/releases/tags/v1.86.3`
  - `https://api.github.com/repos/BerriAI/litellm/releases/tags/v1.85.4`
  - `https://api.github.com/repos/BerriAI/litellm/releases/tags/v1.85.3`
  - `https://api.github.com/repos/BerriAI/litellm/releases/tags/v1.84.5`
- LiteLLM 仓库：`https://github.com/BerriAI/litellm`
- Cosign 文档：`https://docs.sigstore.dev/cosign/overview/`
