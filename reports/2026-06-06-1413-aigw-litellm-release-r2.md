# AI Gateway 单产品发版追踪 · LiteLLM (Round 2)

- 轮次时间：2026-06-06 14:13 CST
- 主题：LiteLLM（hour=14, 14%7=0 → release；上轮已轮过 Kong/Helicone/OpenRouter，回到 LiteLLM 起点）
- 上次 LiteLLM 报告：`reports/2026-06-05-0034-aigw-litellm-release.md`
- 数据窗口：2026-06-04 ~ 2026-06-06（36h）
- 数据源：GitHub Releases + Issues + Commits + 单 PR

---

## 一、版本总览（过去 36h）

| tag | 发布时间 (UTC) | 类型 | 备注 |
|---|---|---|---|
| `v1.88.0-rc.3` | 2026-06-05 02:10 | rc | 与 rc.2 内容相同（diff 空），纯 tag 步进 |
| `v1.87.1` | 2026-06-04 22:12 | stable patch | backport 5 项；#29612 → 1.87.2 被 #29645 revert |
| `v1.86.4` | 2026-06-04 16:35 | stable patch | backport 6 项；#29612 → 1.86.5 被 #29644 revert |
| `v1.84.5` | 2026-06-04 04:11 | stable patch | 长尾维护线 |

`v1.88.0-rc.3` vs `v1.88.0-rc.2` **没有新 commit** —— **LiteLLM stable cut 节奏陷入「卡 3 个 rc、迟迟不切 stable」**。`mateo-berri` 在 1.87.x / 1.86.x 反复做 #29612 → bump → revert，说明 stable cut 对「不预先做 regression gate 就 bump version」仍有踩坑。

---

## 二、过去 36h main 分支高信号 PR

### 1. **#29809 `fix(ui): persist Tools-tab MCP OAuth token to DB`** — 6/6 05:29 UTC

MCP OAuth "on behalf of" (OBO) **阻断性 bug**：`access_token` / `refresh_token` 没存 DB，过期/即将过期不刷新 → 工具列表空。修法：落 `litellm_MCPUserCredentials` 表 + 60s 提前刷新（LIT-3579）。观察：MCP 接入层 6/3–6/6 进入"集中修 OAuth"窗口（#29732 / #29714 / #28917 / #29809），**4 个 PR 修 4 个"用户登不上工具"症状**。**MCP OAuth 有 3 个变体（M2M / PKCE Passthrough / PKCE OBO），任一变体错位都让"工具不见"**。

### 2. **#28917 `feat(mcp): per-server env vars with global + per-user scopes`** — 6/6 03:15 UTC

新增 **per-user scope**：`${NAME}` 模板插值到 `static_headers` 请求时展开；listing 走 best-effort（未填的留空，工具仍可见），tool-call 抛 `MCPMissingUserEnvVarsError`；`POST /v1/mcp/server` DB 写作为 commit point，in-memory refresh 作为 best-effort —— **修了一个 500 让 caller 重试导致 duplicate row 的死锁**。同步修 `GET /v1/mcp/server` 丢失 `env_vars` 字段的 list/edit 反弹 bug。

### 3. **#29820 `fix(proxy): drop deleted team BYOK model name from team.models`** — 6/6 01:35 UTC

修"鬼模型"（#22594）：`delete_model` 只用 alias lookup 删 `team.models`，但 team-scoped 模型（`/model/new` + `model_info.team_id`）**从来不创建 alias 行**；raw `update` `litellm_teamtable` 之后**不调 `_refresh_cached_team`**。修法：按 `team_public_model_name` 作为 key 删 + 强制 refresh cache。观察：BYOK 模型在 `team.models` 里有**两个真理来源**（`litellm_modeltable` alias 行 vs `team.models` 直接存的 public name）—— 任何"删"操作必须双写清理。

### 4. **#29806 `refactor(ui): route behavior-preserving networking calls through apiClient`** — 6/6 03:40 UTC

dashboard `networking.tsx` 手工 `fetch()` + `proxyBaseUrl ? ... : ...` 三元 URL 大重构：约 61 个函数从手卷 `fetch()` 改为 `apiClient.get/post/put/delete/patch`，**byte-for-byte behavior-preserving** 原则。

### 5. **#29816 `feat(ui): generate dashboard API types from the proxy OpenAPI spec`** — 6/6 00:20 UTC

`src/lib/http/schema.d.ts` 从手工维护改为 **从 FastAPI `app.openapi()` 直接生成**：`openapi-typescript 7.13.0` → `openapi.json` → `schema.d.ts`（10 文件 / +52976 / -4），新增 `Check UI API Types Sync` CI：drift 即 PR 失败。观察：**#29793 base URL resolver + #29806 apiClient 收敛 + #29816 OpenAPI type generation 是 LiteLLM 6/4–6/6 的 UI 治理标准三件套：base URL 单点 / 客户端单点 / 类型单点**。

### 6. 其他 PR

- **#29713 `feat(litellm): finish models/repository migration`**（LIT-3570）：所有 DB table 移到 `litellm/models/`，inline Prisma table access 走 repository 层。
- **#17365 `feat: Cancel LLM stream response on client disconnect`**（#13774）：`is_disconnected()` + `CustomStreamWrapper` + break stream on disconnect。
- **#18353 `feat(batch): skip token counting for batch operations`**：Vertex AI batch 5GB+ GCS 文件不再下载数 token。
- **#29822 (OPEN) `fix(bedrock): preserve cache_control for ARN models`**：与 #17479「Bedrock cachePoint extraneous key」同症状。

---

## 三、rc 周期 1.88 切 4 个 fix + 1 个回归

[#29632](https://github.com/BerriAI/litellm/pull/29632) 是 1.88.0-rc.2 的核心 cherry-pick bundle：

| PR | 主题 | 影响 |
|---|---|---|
| [#29545](https://github.com/BerriAI/litellm/pull/29545) | resolve managed video model ids through router | 视频 polling/download 401 → 修 |
| [#29310](https://github.com/BerriAI/litellm/pull/29310) | team members create keys on org-scoped teams | 1.84.0-rc.1 回归（VERIA-55）|
| [#29585](https://github.com/BerriAI/litellm/pull/29585) | strip `output_config.effort` for Vertex Claude (Haiku 4.5) | Claude Code 默认 payload 含 `output_config.effort`，Haiku 4.5 Vertex 拒 |
| [#29598](https://github.com/BerriAI/litellm/pull/29598) | stop duplicate cost callbacks | 一次请求两笔 spend |

[#29637](https://github.com/BerriAI/litellm/pull/29637) cherry-pick #29612：UI 内部 session token 创建 team key 时免 budget ceiling 校验（GHSA-q775 加固）；进 stable 反复：1.87.2 + 1.86.5 → gate 失败 → #29645/#29644 revert。观察：**release 自动化需要 patch 阶段 full CI 而非 target branch CI**。

---

## 四、MCP 集中修 OAuth（6/3-6/6 四联击）

| PR | 症状 | 修法 | 类型 |
|---|---|---|---|
| #29732 (OPEN) | PKCE passthrough auth 后 tools list 空 | diagnose cancel 吞错 | diagnose |
| [#29714](https://github.com/BerriAI/litellm/pulls/29714) | UI 把 PKCE Passthrough 误标 M2M → 不带 access-token | labelling 分清 M2M/PKCE Passthrough/PKCE OBO | UI labelling |
| #28917 (6/6) | per-server env vars listing 误抛错 | listing best-effort + tool-call raise | template + lifecycle |
| [#29809](https://github.com/BerriAI/litellm/pulls/29809) | OBO mode token 不存 DB → 工具空 | 落 `litellm_MCPUserCredentials` 表 + 60s 提前刷新 | persistence |

**模式**：3 OAuth 变体 × 2 lifecycle（listing vs call）× 2 数据源（sessionStorage vs DB）= 12 出错点，**已识别并修 4 个**。**MCP "tools 不见" bug 三角**：UI labelling 错 / token 不持久 / template 解析抛错。AIGW 硬要求：**MCP OAuth 三变体必须每变体独立走 e2e smoke test，listing path 与 tool-call path 走不同 test suite**。

---

## 五、Issue Tracker 当前高关注 Bug

| Issue | 主题 | 重要度 |
|---|---|---|
| [#29818](https://github.com/BerriAI/litellm/issues/29818) | OpenAI Codex CLI 不工作（`/v1/responses` 路径）| 高 |
| [#29808](https://github.com/BerriAI/litellm/issues/29808) | `MidStreamFallbackError` Vertex AI 不重试 | 中 |
| [#17479](https://github.com/BerriAI/litellm/issues/17479) | Bedrock prompt caching extraneous `cachePoint` key | 中（#29822 修法）|
| [#27300](https://github.com/BerriAI/litellm/issues/27300) | `max_budget` reset 后不生效 | 中 |
| [#23016](https://github.com/BerriAI/litellm/issues/23016) | `/v1/messages` image url source 不支持 | 中 |
| [#23034](https://github.com/BerriAI/litellm/issues/23034) | Langfuse logging 在 1.81.16 突然挂 | 中 |

[#29818 OpenAI Codex CLI](https://github.com/BerriAI/litellm/issues/29818) 单独看：用户配 `openai/gpt-5.5` 通过 LiteLLM 跑 Codex CLI，proxy 报 `Invalid HTTP request received.`，codex 端 `Stream disconnected before completion`。**Codex CLI 走 `/v1/responses` 路径（OpenAI 6/2026 推的下一代 endpoint），LiteLLM 的 HTTP parser 似乎没正确处理这种 streaming request**。借鉴：**OpenAI 把 `/v1/responses` 推为下一代主路径，gateway 必须确保 path-aware parser 正确分流**。

---

## 六、上轮报告没看到的几个重要走向

1. **UI 治理三件套（6/5-6/6）**：#29793 → #29806 → #29816 —— **大代理项目 dashboard 治理标准组合**。
2. **MCP 协议层 OAuth 三角**（M2M / PKCE Passthrough / PKCE OBO）成 LiteLLM 6/3-6/6 的**新战场**。
3. **stable cut 流程反复**（#29612 1.87.2/1.86.5 被 revert）说明 release 自动化需要 patch 阶段 full CI 而非 target branch CI。
4. **Cosign 验证流程**已稳定（每个 release 页面都给 commit-pinned + tag-pinned 两种 verify 路径），**docker 镜像的供应链安全是 LiteLLM 在 AI GW 项目里目前唯一公开 SLSA 实践**。
5. **Anthropic Claude Code / OpenAI Codex CLI 兼容性**成新隐患 —— CLI 默认 payload 含非标准字段（`output_config.effort`、`/v1/responses`）让 proxy 必须能"剥 + 转"，这是 2026 H2 通用问题。
6. **LiteLLM 主推 1.87.x + 1.88.x 双轨**：1.86.4 / 1.85.x / 1.84.5 是 LTS 维护线，1.88 是快迭代；1.87.1 实际是「1.88 没 stable 之前的事实 stable」。

---

## 七、值得追踪的几个信号

1. **1.88 stable 何时切**（rc.1→rc.2→rc.3 内容基本相同，**rc.3 看着是 placeholder**）
2. **OpenAI Codex CLI 兼容性**（#29818）会否带出 `/v1/responses` 路径系统性改造
3. **MCP OAuth 三变体 UI 治理**（#29714 labelling + #29809 persistence + #28917 env vars）是否会在 1.89 收敛为单一 MCP OAuth provider abstraction
4. **UI 治理三件套**（#29793 / #29806 / #29816）完成后，dashboard 与 proxy 之间的 schema drift 是否还会发生（drift gate 已建）
5. **Cosign 实践** vs 其他 AIGW（Portkey/Helicone/Envoy AI GW/Kong）的供应链安全对比 —— LiteLLM 是目前唯一公开 SLSA 级实践
6. **本轮没改的**（留给后续）：v1.88 GA 时间窗 / 1.87.x 是否重新带回 #29612 / 1.86.x LTS 维护周期 / Codex CLI `/v1/responses` 完整支持 / 视频生成 router resolve（#29545）在 1.88.0 GA 前的回归测试覆盖。

---

## 引用与数据来源

### GitHub Releases
`https://api.github.com/repos/BerriAI/litellm/releases?per_page=5` · `releases/tags/v1.88.0-rc.3` / `v1.88.0-rc.2` / `v1.87.1` / `v1.86.4` / `v1.84.5`

### Pull Requests（22 条，base URL = `https://github.com/BerriAI/litellm/pull/`）
#29809 / #29806 / #29816 / #28917 / #29820 / #29822 / #29632 / #29637 / #29793 / #29714 / #29781 / #29217 / #29545 / #29310 / #29585 / #29598 / #29537 / #29782 / #29761 / #17365 / #18353 / #29713

### Issues（9 条，base URL = `https://github.com/BerriAI/litellm/issues/`）
#29818 / #29808 / #17479 / #22594 / #27300 / #23016 / #23034 / #29612 / #13774

### 元信息
LiteLLM 仓库：`https://github.com/BerriAI/litellm` · Cosign 文档：`https://docs.sigstore.dev/cosign/overview/` · Linear：LIT-3579 / LIT-3570 / LIT-3540 / LIT-3128 / LIT-3411 / LIT-3214
