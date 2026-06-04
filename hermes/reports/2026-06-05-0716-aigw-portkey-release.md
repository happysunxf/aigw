# Portkey 发版追踪 · 2026-06-05 07:16 CST

> **本轮主题**：单产品发版追踪 — Portkey（hour%7=0 轮换位）  
> **抓取时间**：2026-06-05 07:16 CST（Friday）  
> **数据源**：GitHub `Portkey-AI/gateway` Releases/Tags/Commits API、portkey.ai/blog、portkey.ai 主站  
> **覆盖范围**：v1.12.2 → v1.15.2 共 8 个 release tag、main 分支最近 30 个 commit、4 篇 2026 年 4-5 月新博客

---

## 一、一句话结论

**Portkey 的"商业化曲线"已经盖过"开源发版曲线"——最近一个 release tag `v1.15.2` 是 2026-01-12 的，到今天已 5 个月没有新 tag，但 main 分支仍以"安全加固 + 鉴权收紧"为主线在持续合入（5/19 一天连合 4 个 auth/log 相关 commit）。** 与此同时，被 Palo Alto Networks 收编后，公司的产品叙事从"LLM gateway"明确转向"Agent Gateway + MCP Governance + Skills Registry"三件套。

## 二、关键发现

### 1. Release 节奏明显放缓（5 个月没发新 tag）

| Tag | 发布日 | 主要变化 |
| --- | --- | --- |
| v1.15.2 | 2026-01-12 | Qualifire guardrails 更新、Azure batch 修、anthropic beta header 行为统一 |
| v1.15.1 | 2025-12-24 | Gemini minimal reasoning、Azure 内容安全 checks、batch URL 修复 |
| v1.15.0 | 2025-12-23 | Gemini 3 Pro thinking、Anthropic on Azure、Oracle provider、Sequential guardrails、Hallucination eval |
| v1.14.3 | 2025-11-26 | Google signature 修复（hotfix） |
| v1.14.2 | 2025-10 末 | 略 |

**5 个月不发新 tag，对一个常驻 GitHub 趋势榜的 LLM 网关项目来说不寻常**——同期 LiteLLM 平均 1-2 周一个 minor。可能性有三种：① 团队把精力放在 PANW 收编后的产品整合上；② main 上大量 PR 还没稳定到能切 release 分支；③ 主推商业 SaaS，开源版更趋保守。

### 2. main 分支"安全加固"成为主线（5/19 一天 4 个 commit 全是 auth/log）

```
2026-05-25  Merge #1657 fix/add-auth-validation-for-public-rout[es]
2026-05-19  formatting
2026-05-19  redact provider options in logs
2026-05-19  disable logs when admin token not set
2026-05-19  remove admin token default
2026-05-19  add auth validation for public routes
2026-05-18  Merge #1642 (CrowdStrike AIDR metadata)
2026-05-11  feat: forward request metadata to CrowdStrike AIDR
```

值得注意的动作：
- **"remove admin token default"** —— 之前默认 `ADMIN_TOKEN` 可能是空字符串或固定值，现在显式要求设置（防呆，避免生产忘记设就被外网直接 admin）。
- **"add auth validation for public routes"** —— 公开路由（health/metrics 之类）以前可能 bypass 鉴权，现在补上统一校验。
- **"redact provider options in logs"** —— 日志里出现的 provider config 包含 `api_key`/`authorization`，日志落到 ELK/S3 之前先 redact。
- **"disable logs when admin token not set"** —— 配套：未鉴权部署时把日志全关掉，避免敏感数据被静默收集。

这一组动作连看是一个典型的"Post-Palo-Alto 收编安全审查"pattern——PANW 的安全团队会扫一遍核心 OSS 资产，强制要求 admin auth 默认开启。

### 3. 仓库健康度：11,970★ / 1,105 fork / 187 open issues

- `pushed_at=2026-05-25`（main 分支仍在活跃）
- `open_issues_count=187` —— 处于历史正常水位，issue 跟 PR 都有维护
- 上一份综合报告（2025-2026 大报告）记录的是 11,968★ / 1,104 fork，说明过去几个月 star 增速已经明显放缓（> 5 个月只 +2★），也吻合 release 节奏放缓的判断。

### 4. v1.15.0/1.15.1/1.15.2 的 3 个里程碑功能（开源自部署可用）

#### 4.1 顺序执行 Guardrails（#1475, v1.15.0）
- 旧行为：多个 guardrail 并行触发，输出只要有一个 fail 就 reject
- 新行为：可以配置"sequential"模式，前一个 fail 就不跑后续，省延迟 + 避免矛盾规则
- 实战价值：把"先 PII 检测 → 再 toxicity → 再 jailbreak"做成有序流水线，错误定位更直接

#### 4.2 Hallucination Eval（#1434, v1.15.0, Patronus AI 贡献）
- 新增 "hallucination eval" guardrail provider，背后应该是 Patronus 的 Lynx 之类的判别模型
- 这是 guardrail-as-a-service 的重要拼图——之前只有"内容是否安全"维度，现在加了"内容是否正确"

#### 4.3 Anthropic on Azure + OpenAI-compatible response（#1465 / #1456, v1.15.0）
- 之前要在 Azure OpenAI 上跑 Anthropic 模型需要自定义 provider
- 现在原生支持，并且把"responses"接口做成 OpenAI 兼容——意味着现有 OpenAI SDK 代码可以零改动切到 Azure 上的 Claude

#### 4.4 Azure Blob for Batches（#1496, v1.15.2）
- Batch API 输入/输出文件支持 Azure Blob，之前只支持 AWS S3
- 对企业 Azure-only 部署的客户是卡点解锁

### 5. Skills Registry（4-23 博客，重要新品类）

Portkey 在 4-23 的博客 *Introducing Skills Registry* 里推了一个全新产品线：

- **定位**：Claude Code / Cursor / Codex 这类 IDE-side coding agent 都会读 `SKILL.md` 之类的"团队 context"文件
- **痛点**：技能散落在工程师各自笔记本上，没版本管理、没 review 流程、无法整队同步
- **解法**：在 Portkey Prompt Engineering Studio 里用 Prompt Partial 写 SKILL.md，绑定稳定 ID + 版本号 + draft/publish 工作流，然后 `portkey skills sync` 一键下发到本地 agent
- **本质**：把"prompt 内容管理"从"人脑/Confluence"挪到一个"SDK-first registry"

这是 Portkey 第一次把产品边界从"网关"扩到"Agent 上下文管理"。可以理解为对标 LangChain Hub / PromptLayer 的 prompt 管理能力 + Anthropic Skills 协议 的存储层。

### 6. MCP Governance 博客（5-24，披露新数据）

博客 *What MCP Governance Actually Means in Production* 给出 4 组关键统计（2026 年最新调研）：

| 指标 | 数值 | 含义 |
| --- | --- | --- |
| 使用静态 API key 的 MCP 服务器 | **53%** | 大半数仍用长期 secret，没 OAuth |
| 使用 OAuth 的 MCP 服务器 | **8.5%** | OAuth 是 MCP 2025-03 才加的可选项，渗透极低 |
| 把凭据存到环境变量 | **79%** | env var 本身没加密，只是"约定俗成"的隐藏 |
| 引用案例 | postmark-mcp rugpull | 仿冒 postmark 名字的 npm 包被广泛安装 |

由此提出 **4 个 governance primitive**：
1. **Trusted Registry** — 允许名单制，决定哪些 MCP server 能用（防 shadow MCP）
2. **Centralized Authentication** — per-user OAuth，取代共享 static token
3. **Runtime Policy Enforcement** — 在 tool 执行前 evaluate & block
4. **Audit Logging** — 全量记录 invoker、参数、结果

这是对 01:46 那份"MCP Gateway 产品专题"（Azure APIM / Kong / Zuplo / Cloudflare AI GW 的 MCP 角度）的呼应——安全治理开始从"协议级"下沉到"运行时+凭据级"。

### 7. 商业 / 公司层

- 2026 年 Palo Alto Networks 完成对 Portkey 的收购，logo 区域已出现 "portkey-PANW-company-logo" 字样（blog 顶部 `portkey-PANW-company-logo-positive-1.png`）
- 收编后维护节奏从"互联网创业公司"变成"企业安全公司"——这是 5 个月没新 tag 的最合理解释
- 主站 hero 仍标 "1,600+ LLMs, 50+ AI Guardrails"，商业定位主打 guardrail + 可观测 + agent 治理三件套

## 三、给生产用户的建议

1. **升级到 v1.15.2**：Azure blob batch、Sequential guardrails、Hallucination eval 三件套都是实战痛点解锁
2. **手动设置 ADMIN_TOKEN**：main 分支的 "remove admin token default" 还没 release，但生产部署现在就该做
3. **不要把 Portkey 当"普通过网关"用**：Skills Registry + MCP Governance + Agent Gateway 这三件套绑在一起才是它差异化；如果你只要多模型路由 + 限流，LiteLLM / OpenRouter 自部署更轻
4. **关注 v1.16.0**：5 个月积累的安全加固合并 release 后，重大变更是认证模型，需要看 release notes 决定是否能直接升
5. **MCP 接入必须走 OAuth**：53% 静态 key 的现实说明 npm 生态的"默认安全"假设是错的，部署 MCP server 时强制 OAuth + audit log

## 四、本轮次要数据

- v1.15.2 release size：8 个 PR（qualifire update + azure batch + anthropic beta + 1 个新贡献者）
- v1.15.0 新增 providers 4 个：Oracle、IO Intelligence、OVHcloud AI Endpoints、AI Badgr
- 博客 2026 年 1-5 月新发文 ≥ 5 篇（MCP Governance / Agent Gateway / AgentOps / Skills Registry / Coding Agents）
- main 上 5/19 一天的 4 个安全 commit 实际上未在 v1.15.2 内——它们是要进 v1.16 的候选内容

## 引用与数据来源

- GitHub Releases: <https://github.com/Portkey-AI/gateway/releases>
- GitHub Tags: <https://github.com/Portkey-AI/gateway/tags>
- GitHub Commits (main): <https://github.com/Portkey-AI/gateway/commits/main>
- Repo metadata API: <https://api.github.com/repos/Portkey-AI/gateway>
- Portkey 博客首页: <https://portkey.ai/blog>
- *What MCP Governance Actually Means in Production* (2026-05-24): <https://portkey.ai/blog/mcp-governance/>
- *Introducing Skills Registry* (2026-04-23): <https://portkey.ai/blog/skills-registry/>
- *What is an Agent Gateway* (2026-05-03): <https://portkey.ai/blog/what-is-an-agent-gateway/>
- *What is AgentOps* (2026-04-29): <https://portkey.ai/blog/what-is-agentops/>
- Portkey Docs: <https://portkey.ai/docs>
- 历史综合报告（2025-2026 全产品调研）: `aigw-report-2025.md`
- 上次 LiteLLM 发版追踪: `reports/2026-06-05-0034-aigw-litellm-release.md`
