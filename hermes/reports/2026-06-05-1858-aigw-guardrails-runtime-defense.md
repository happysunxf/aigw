# AI 网关持续深挖 · 第 N 次 — Guardrails & 安全(运行时注入防御 / 越狱评测 / 策略执行)

- 轮值时间(本地): 2026-06-05 18:58 CST
- 主题:Guardrails & 安全 · 5 期(运行时层)
- 上一期(Guardrails 4 期)聚焦「数据驻留 + 镜像签名 + 日志脱敏 + 工具 payload 防火墙」;本期转向 **运行时的 prompt-injection 防御、jailbreak 评测体系、以及 agent 行为策略的网关层强制点**。

## 1. 一句话结论

guardrails-ai v0.10.2(2026-06-04, 距今约 23h)把"PyPI trusted publishing + Aikido 模板注入 AI 修复 + SECURITY_ADVISORY.md 制度化"三件事一起落地,等于给 guardrails 工具链本身做了一次供应链硬化;同时 LiteLLM 在 6/01-6/05 之间把 **OTel guardrail span** 补齐成可观测闭环。三件事合起来,本期主线是:**「防御本身」也在变成一种被防御的对象**——guardrails 网关要把自身纳入 SLSA / 信任发布 / 注入检测的标准治理面。

## 2. guardrails-ai v0.10.2(2026-06-04)— 自身供应链硬化

发布主页:https://github.com/guardrails-ai/guardrails/releases/tag/v0.10.2
- 关键 PR(7 个):
  - `#1493` release workflow for trusted publishing(由 @zsimjee 提交)
  - `#1486` v0.10.2 切版(@CalebCourier)
  - `#1490 / #1478 / #1474` `SECURITY_ADVISORY.md` 三连(由 @ShreyaR 主笔)
  - `#1484` 放宽 litellm pin 到 `>=1.83.0`(@vaibhatredu)—— 历史教训:pin 太死会被旧 CVE 卡住
  - `#1467` Aikido AI Fix for Template Injection in GitHub Workflows Action(@aikido-autofix[bot])—— 这是首个在 guardrails-ai 仓里出现的"反 CI 注入"修复

### 2.1 解读:trusted publishing 为什么重要

PyPI trusted publishing(PEP 740 + OIDC)把"上传者"从长期 token 切到短命 OIDC 身份,意味着:
- **token 一旦泄露,攻击者拿不到 PyPI 上传权**——把"PyPI 投毒"从"凭据泄露 → 全网污染"压缩到"凭据泄露 → 单个构建污染"
- 之前 guardrails-ai 0.10.1(被影响版)已经发生过 PyPI 投毒事件(参考 Guardrails 3 期报告),v0.10.2 走 trusted publishing 是直接闭环
- **对 AI 网关侧的启示**:把"用 guardrails-ai 做审计"的链路,自己也要纳入 SLSA L3 校验——别让审计器变成攻击面

### 2.2 `SECURITY_ADVISORY.md` 三连——披露流程制度化

- 三次 update(#1474 / #1478 / #1490)在 6/03-6/04 之间连续提交,说明 guardrails-ai 团队在把"如何披露 CVE / 投毒事件"沉淀成 repo 内文档,而不是临时 issue
- 给 AI 网关运营方的实践:把 guardrails-ai 升级流程接入 "GHSA → 内部 ticket → 灰度替换" 的 SLA,而不是"等下一个 release notes"

### 2.3 litellm pin `>=1.83.0`——历史 CVE 反向教训

放宽 pin 是因为 1.83.x 之前有 PII 路径处理 bug(参 LIT-3114),pin 过死会被旧 bug 锁死。这是典型的"安全左移"反例:安全策略本身不能成为升级摩擦。

## 3. LiteLLM 一周(6/01-6/05)— OTel guardrail span 闭环

近 5 日 guardrail 相关 PR(共 40 条命中,精选 6 条):

| PR | 合并时间 | 主题 |
|---|---|---|
| `#28250` | 2026-06-01 | content filter path traversal CWE-022 修复 |
| `#29339` | 2026-06-01 | Add native Vigil Guard guardrail provider |
| `#28594` | 2026-06-01 | fix(panw_prisma_airs):timeout 强转 float(防止字符串配置注入到 SDK 调用) |
| `#29470` | 2026-06-02 | fix(passthrough): emit OTel guardrail span when a guardrail blocks |
| `#29552` | 2026-06-03 | fix: missing span for guardrail passthrough |
| `#29531` | 2026-06-05 | [internal copy of #29511] sensitive data → on-prem 路由 |

### 3.1 OTel guardrail span 闭合(本期最关键的可观测进展)

- `#29470` + `#29552` 把 guardrail "block 事件"补成一个独立 OTel span,挂到 `litellm.request` parent 上
- **直接价值**:
  - 在 Tempo / Honeycomb / Datadog 里能查到 "这条 request 走了哪个 guardrail、为什么被 block、耗时多少"
  - 配合 Guardrails 4 期提到的 `tool-payload-firewall`,可以画完整的"用户输入 → LLM → 工具调用 → 输出 guardrail" trace
  - 出现"FP 突增"时,能定位是哪个 guardrail rule 触发的,而不是只看"request 失败"
- **给网关侧的对接建议**:把 `litellm.guardrail.{provider,action,duration_ms,rule_id}` 作为 fan-out 指标,告警阈值用"过去 1h block rate > N%"比"绝对数"更稳

### 3.2 Vigil Guard 正式成为原生 provider

`#29339` 把 Vigil Guard(开源 LLM 防火墙,基于规则 + ML 混合)从"需要自接 hook"升级成 litellm `config.yaml` 里一行:

```yaml
guardrails:
  - guardrail_name: "vigil-prod"
    litellm_params:
      guardrail: vigil
      mode: [pre_call, post_call]
      api_base: https://vigil.internal
      api_key: os.environ/VIGIL_KEY
```

意味着选 LiteLLM 做网关的团队,可以用 "Vigil + 业务规则" 双层防御,不再需要单独写中间件。

### 3.3 timeout 强转 float(看似微小,实是配置注入面)

`#28594` 修了 `panw_prisma_airs` provider 的 timeout 配置:如果运营把 `timeout: "5"` 写成字符串,SDK 会拿到字符串直接传出去,可能触发下游 SDK 的 crash。修复点很小,但说明 **"字符串配置"是 guardrail SDK 集成的典型注入面**——审计时要把所有 `*_timeout` / `*_url` / `*_token` 配置都做类型校验。

## 4. NVIDIA NeMo Guardrails v0.22.0(2026-05-22)复述 + 后续

- 上一期(Guardrails 4 期)已覆盖 v0.22.0 的 IORails 引擎
- 本期补充一个观察:5/22 之后到 6/05 已经 14 天,NeMo-Guardrails 仓**没有任何新 release**——社区节奏放缓,可能 0.23 还在内部测试
- 给网关侧的策略:不要把 NeMo 视为 "active fast-iterating" 组件,做好 LTS 心态,升级周期放到 2 个月一档

## 5. Envoy AI Gateway:PR #2132(已合并)日志脱敏精细化

- 来源:https://github.com/envoyproxy/ai-gateway/pull/2132
- 核心改动:把"全字段 redact" 改为 "按字段粒度 redact",**保留 request_id / model / token_count 用于排障**,只 redact 实际 payload 中的 user content
- 价值:把"安全 vs 排障"的天平往后者倾斜一点点——对生产 SRE 更友好
- 部署建议:在 `ai-gateway-config.yaml` 里:
```yaml
logRedaction:
  strategy: field-level
  keepFields: [request_id, model, token_count, latency_ms, guardrail_action]
  redactFields: [messages, tools, response]
```

## 6. Kong 3.9.2(2026-06-04)纯 CVE——AI 网关"前门"的反代

- 来源:https://github.com/Kong/kong/releases/tag/3.9.2
- 本期 Kong release 没有任何 AI 相关 feature,**全是核心网关 CVE 修复**
- 解读:Kong 在 AI 网关的定位还是"前面那层反代",AI 特性走 Kong AI 插件单独线;主仓保持稳定
- **网关组合的实践**:Kong 3.9.x(反代 / 鉴权)+ LiteLLM(LLM 路由 / guardrail)+ guardrails-ai v0.10.2(独立审计)三层共存,不要在 Kong 上做 LLM 业务逻辑

## 7. Higress v2.2.2(2026-05-26)— 阿里系网关稳定版

- 来源:https://github.com/alibaba/higress/releases/tag/v2.2.2
- 5/26 发布,距今 10 天。安全相关:默认开启 WASM 模块的 wasmplugin 签名校验(防止恶意 wasm 注入到数据面)
- 给国内部署的团队:Higress 在多集群 + AI 网关场景的合规优势(信创 / 国密)依然明显,本期的 wasmplugin 签名是补齐"AI 插件自身安全"的关键

## 8. agentgateway v1.3.0-alpha.1(2026-05-23)— 行为策略层

- 来源:https://github.com/agentgateway/agentgateway/releases/tag/v1.3.0-alpha.1
- 近 5 日(6/01-6/05)merge 33 个 PR,核心几条:
  - `#2077` mcp: advertise tools.listChanged in multiplexing mode——MCP 多路复用下的工具变更广播
  - `#2075` fix(mcp): shrink the stack a bit——DoS 防御(深递归)
  - `#2084` memory: drop stack size of backend call——同上,内存层栈深度限制
- **runtime injection 防御面**:
  - 1.3.0-alpha.1 把"工具 schema 变更"和"栈深度限制"两件事都做进 alpha,**说明 agent gateway 层正在承担运行时注入防御的一部分责任**——单 LLM 防御不够
  - 推荐架构:LiteLLM(API 层 guardrail)+ agentgateway(行为 / 工具层 guardrail)+ guardrails-ai(独立审计)三层,每层覆盖 OWASP LLM Top 10 中的不同条目

## 9. 横切:四件事本期叠加成一个新信号

1. **guardrails 工具自身被纳入 SLSA / trusted publishing**(guardrails-ai v0.10.2)
2. **gateway 把 guardrail 行为变成可观测对象**(LiteLLM OTel span)
3. **gateway 把"配置注入"列为 P1 修**(LiteLLM #28594 timeout 强转)
4. **agent gateway 承担"工具/MCP 层"注入防御**(agentgateway 1.3.0-alpha.1)

合成一个趋势:**「运行时注入防御」正在从"LLM 内部行为"变成"网关/代理/审计三层共担"**。 选型时不应只评估"模型层能不能挡住 jailbreak",而要分清每层在防什么:
- 模型层:prompt 形态学注入(直接对 system prompt 的覆盖)
- 网关层:tool payload 注入、schema 篡改、栈 / 内存 DoS
- 审计层:信任发布 / 镜像签名 / 升级 SLA

## 10. 给团队的行动项(本期)

1. **2 周内**把 guardrails-ai 升到 v0.10.2(避开 0.10.1 投毒窗口),并启用 PyPI pin `>=1.83.0` 的 litellm 兼容
2. **本月底**在 LiteLLM 网关上抓 24h trace,确认 OTel guardrail span 正确冒泡(指标名 `litellm.guardrail.action` 取值 `block` / `modify` / `passthrough`)
3. **季度审计**所有 guardrail provider 的 string-typed 配置项,统一做类型校验(参考 #28594)
4. **架构评审**确认 MCP / agent 网关层有"工具 schema 校验"位点(对照 agentgateway 1.3.0 的 `tools.listChanged` 思路)

## 引用与数据来源

- guardrails-ai v0.10.2 release:https://github.com/guardrails-ai/guardrails/releases/tag/v0.10.2
- guardrails-ai SECURITY_ADVISORY.md:https://github.com/guardrails-ai/guardrails/blob/main/SECURITY_ADVISORY.md
- guardrails-ai #1493 trusted publishing:https://github.com/guardrails-ai/guardrails/pull/1493
- guardrails-ai #1467 Aikido template injection fix:https://github.com/guardrails-ai/guardrails/pull/1467
- LiteLLM v1.88.0-rc.3:https://github.com/BerriAI/litellm/releases/tag/v1.88.0-rc.3
- LiteLLM v1.87.1:https://github.com/BerriAI/litellm/releases/tag/v1.87.1
- LiteLLM #29470 OTel guardrail span:https://github.com/BerriAI/litellm/pull/29470
- LiteLLM #29552 missing span fix:https://github.com/BerriAI/litellm/pull/29552
- LiteLLM #29339 Vigil Guard provider:https://github.com/BerriAI/litellm/pull/29339
- LiteLLM #28594 timeout type fix:https://github.com/BerriAI/litellm/pull/28594
- LiteLLM #28250 CWE-022 path traversal fix:https://github.com/BerriAI/litellm/pull/28250
- Envoy AI Gateway #2132:https://github.com/envoyproxy/ai-gateway/pull/2132
- Kong 3.9.2:https://github.com/Kong/kong/releases/tag/3.9.2
- Higress v2.2.2:https://github.com/alibaba/higress/releases/tag/v2.2.2
- agentgateway v1.3.0-alpha.1:https://github.com/agentgateway/agentgateway/releases/tag/v1.3.0-alpha.1
- NeMo-Guardrails v0.22.0:https://github.com/NVIDIA/NeMo-Guardrails/releases/tag/v0.22.0
- 上期报告(Guardrails 4 期):`hermes/reports/2026-06-05-1819-aigw-guardrails-roundup.md`
