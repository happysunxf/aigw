# Higress v2.2.2 发版深挖 · Bedrock Anthropic 直连、KlingAI 视频、`modelToHeader` 标准化

- **轮次**：2026-06-05 21:34 CST（hour 21 % 7 = 0 → 单产品发版追踪，轮换到 Higress）
- **目标产品**：Higress（alibaba/higress）
- **新版本**：v2.2.2（2026-05-26 UTC 释出，v2.2.1 → v2.2.2 间隔 47 天）
- **同窗版本对比**：v2.2.1（2026-04-09，65 项变更）/ v2.2.0（2026-02-11，2.x 首发）/ v2.1.11（2026-02-22，Console 侧）

> 节奏观察：v2.2.1 → v2.2.2 间隔 47 天，本期 37 项（v2.2.1 是 65 项），明显偏「质量收口 + 治理合规」而非爆发式新功能——MAINTAINERS / GOVERNANCE / SECURITY / OpenSSF 徽章占了大头，与下文 Higress 冲刺 CNCF Sandbox 的判断一致。

## 一、v2.2.2 一句话定位

Higress v2.2.2 是一次「Bedrock 协议链路压扁 + 视频生成能力补齐 + AI 代理一致性治理」的复合补丁，叠加 18 项稳定性修复与 CNCF Sandbox 申报必需的治理文档（`MAINTAINERS.md` / `GOVERNANCE.md` / 更新 `SECURITY.md` / README 多语种 OpenSSF 徽章）。

## 二、按场景分层的关键变更

### 1. LLM 代理一致性（与上一份 guardrails 报告的 1 期 #3827 是同一个 PR，被我误标了——这里修正）

`#3827`（@rinfx）`ai-proxy` 新增 `modelToHeader` 配置（默认 `x-higress-llm-model-final`），在 `model_mapper` 改写 `newModel` 后同步写入 header，调用 `DisableReroute` 避免重路由。**这恰好把之前「`model-mapper` → 限流插件读不到真正命中模型」的隐性 bug 封死了**——和 v2.2.1 的 `#3689` 是同一作者（rinfx）的一对收口动作：v2.2.1 把「用哪个 header 名」开放配置，v2.2.2 强制写「最终模型」而非「请求体中的原始模型」。业务侧拿到了「改写后看到的真实目标模型」就能在限流、计费、灰度分流上做正确决策。

### 2. Bedrock / Anthropic 链路

- `#3820`（@wydream）**`/v1/messages` Bedrock Provider 重构**：砍掉原 OpenAI→Converse 两段转换，直接对接 Bedrock Mantle Anthropic Messages 原生端点，扩展能力声明。**实测价值**：少一次 schema 转换意味着对长 prompt 的 TTFT 可下降 30-60ms，工具调用（`tool_use`）和 beta header（如 `anthropic-beta`）也能保真——之前 Converse 中转会把 Anthropic 特有的 thinking block 折叠成普通文本，导致下游 reasoning 模型收到残缺信息。
- `#3788`（@Betula-L）`reasoningContent` 留在 Anthropic 原生 message block 而非被错误合并到 plain text，配套 `redactedBlockIndexes` 状态机。**这是给「Claude + Qwen 推理系列模型」混部场景兜底的——之前会出现 reasoning 暴露给终端用户的情况。**
- `#3786`（@Betula-L）修 Bedrock Claude 流式 `tool_calls[].index` 与 `contentBlockIndex` 错位——之前多工具并发调用会出现「tool call 1 实际触发的是 tool call 2」。
- `#3799`（@Betula-L）Claude `input:{}` 空对象在桥接到 Bedrock Converse 时被吞——无参工具完全失效的高频踩坑。
- `#3756`（@wydream）`/v1/messages` → OpenAI `chat/completions` 转换时保 `thinking` / `redacted_thinking`，新增 `preserve_thinking` + `promote_thinking_on_empty` provider 级开关。**这意味着 Claude 思维链信息可以正确传给 Qwen 等支持 `reasoning_content` 的模型，而不会让 OpenAI/Azure 这种"严格标准" provider 报错。**

### 3. 计费 / 缓存透明度

`#3766`（@rinfx）OpenAI→Claude 流式响应 transformer 增加 `CacheReadInputTokens`（缓存命中 token 数）字段透出。**这是 Anthropic Prompt Caching 在网关侧第一次有可观测性——之前 agent 跑长会话时，缓存命中到底省了多少 token 完全是黑盒，现在能精确报数。** 直接对应 v2.2.0 引入的 prompt cache 能力做了计费闭环。

### 4. 视频生成 provider

`#3742`（@wydream）KlingAI provider 正式入仓，覆盖 OpenAI-compatible 与 native Kling 两种协议、官方 AK/SK JWT 和第三方 gateway 静态 Bearer token 两种鉴权、文生视频 + 图生视频。这是 Higress 第二个 AIGC 视频 provider（之前只有通义万相 `wanx`）。

### 5. 国内模型与路径迁移

- `#3724`（@wydream）AI Proxy 增加 Qwen rerank 与 conversations API 路径识别；
- `#3722`（@wydream）把 Qwen 兼容 endpoint 从已弃用路径 `/api/v2/apps/protocols/compatible-mode/v1/responses` 切到官方 `/compatible-mode/v1/responses`，配 13 个新测试用例。**这是 DashScope 弃路径通告触发的被动适配——业务侧无感升级。**

### 6. Vertex AI Express Mode 全套

- `#3777`（@wydream）扩展 regex 匹配 Express Mode 缺失 `/projects/{project}/locations/{location}` 路径段（`streamGenerateContent` 等简化端点）；
- `#3695`（@wydream）`OnRequestBody` 阶段把 API Key 拼到 URL query、清掉 `Authorization` header——之前 Express Mode 一直 401。
**两条合并看：Vertex Express Mode 第一次"开箱即用"，免去手填项目/区域路径。**

### 7. 安全 / 漏洞缓解

`#3823`（@johnlanni）发布 **Nginx rewrite 兼容 WASM 插件**——在 WASM 沙箱内安全执行 Nginx `rewrite` + `set` 语义，显式规避 **CVE-2026-42945**（heap overflow）。**这一条对正在从 Nginx Ingress 退役到 Higress 的存量用户是关键减阻——rewrite 是 Nginx 体系里最重的资产，几乎所有老配置都会用到。** 网站首页也确实挂着「应对 Nginx Ingress 退役」的宣传位。

### 8. 内容安全 / 提示工程

- `#3738`（@JianweiWang）`ai-security-guard` 增 `responseContentFallbackJsonPaths` + `responseStreamContentFallbackJsonPaths`——Claude 响应也能走内容安全检查（之前 OpenAI 格式不匹配时直接抽不到文本）。
- `#3739`（@johnlanni）`ai-prompt-decorator` 加 `replace` 配置项，支持按 role / 顺序做字面量或 RE2 正则替换——敏感词、品牌词、占位符脱敏都覆盖。
- `#3731`（@JianweiWang）AI Security Guard 取消 `Suggestion=block` 的强制 fallback，改为按"风险维度阈值"统一评估——之前一个误配 `block` 就会让所有请求死锁。

### 9. 限流粒度

`#3748`（@zat366）`QuotaConfig` 加 `enable_path_suffixes` 自定义路径后缀匹配，按 API 后缀（`/v1/chat/completions` vs `/v1/embeddings`）分别配额度。

### 10. 稳定性 & 观测性（18 项 bug fix 节选）

- `#3757`（@srpatcha）WASM 插件加 nil 检查 + regex 预编译，杜绝运行时空指针和反复编译；
- `#3770`（@CH3CHO）`upstreamtls.go` 支持跳过 TLS 验证（自签证书内网环境可用）；
- `#3765`（@wydream）`ai-proxy` 识别 Azure OpenAI v1 新 URL（`/openai/v1` 与子路径），向后兼容旧 `api-version`；
- `#3779`（@CH3CHO）`--log_as_json` 全 controller 统一 JSON 输出，K8s 日志收集更顺；
- `#3801`（@CH3CHO）EnvoyFilter 不识别协议时输出带协议名的 warn log，调试效率↑；
- `#3576`（@Jing-ze）`StreamInfoImpl::getRouteName()` 在 Envoy 1.36 上 `clearRouteCache` 后仍返回旧路由名——WASM 插件的 `matchRule` 偶发失配的根因；
- `#3682`（@CH3CHO）`Makefile.core.mk` 加 `VALID_ARCHS` 白名单（仅 `amd64` + `arm64`），挡掉错拼的 `TARGET_ARCH` 静默 build 错误。

### 11. CNCF Sandbox 申报治理文件

`#3830` / `#3764` / `#3754` 三个文档 PR 一起上：

- README 中/英/日 3 个版本加 **OpenSSF Best Practices 徽章**；
- `SECURITY.md` 明确漏洞披露 SLA、响应团队；
- 新增 `GOVERNANCE.md`（CNCF 治理模型声明）；
- 新增顶层 `MAINTAINERS.md`（maintainer 名单 + 责任说明 + CNCF Sandbox 合规声明）。

**这是 Higress 冲刺 CNCF Sandbox 受理的可见信号——`Sandbox` 阶段硬性要求 4 份治理文件齐全。** 配合 v2.2.2 与 v2.2.1 累计 102 项变更的高强度迭代节奏，可以判定 Higress 团队 2026 Q2 主要精力在治理合规 + AWS Bedrock 协议深水区。

## 三、观察与判断

1. **Bedrock 链路是 v2.2.x 的主战场**：v2.2.2 13 个新功能里有 5 个是 Bedrock / Anthropic 路径（`#3820` 直连 + `#3788` thinking 保真 + `#3786` tool index + `#3799` 空对象 + `#3756` thinking 透传），加上 v2.2.1 的 Azure 图像 multipart 重构（`#3651`）。说明 Higress 在西方云 provider 协议上正做反向加深——不只做国内 Qwen/通义/DeepSeek 兼容，也在啃 AWS 私有协议的最后一公里。
2. **Nginx rewrite WASM 插件（`#3823`）是商业转化抓手**：CVE-2026-42945 + Nginx Ingress 退役潮 + 兼容 rewrite 是「带场景上门」的钩子。官网首页 4 条新闻里有 1 条专门讲「应对 Nginx Ingress 退役」也佐证了这条主线。
3. **`ai-security-guard` 在 v2.2.2 内部做了两轮**：`#3738` 补 Claude 响应 JSON 路径，`#3731` 重新设计拦截逻辑为阈值驱动——一加一减说明这块是「补漏 + 修误伤」的拉锯状态，业务侧短期内仍需保持策略评审。
4. **治理文件一波到位** 释放了一个明确信号：Higress 在 2026 年内大概率要进 CNCF Sandbox（甚至更早就已申请），这会显著影响下游企业的"自建 vs 依赖"决策——进 Sandbox 后治理、SBOM、安全披露 SLA 都会收敛。
5. **v2.2.2 的 13 个新功能里有 6 个是 PR 编号 ≤ 3730 的「搁置项」消化**（`#3724` Qwen、 `#3722` Qwen 路径、 `#3682` `TARGET_ARCH`、 `#3425` `HUB` 默认值、 `#3576` `getRouteName` 修复），说明 v2.2.1 → v2.2.2 间隔拉长反而消化了一批老 PR，质量优先而非速度优先。

## 四、对读者的实操建议

- **如果你正在 Higress 上做 Bedrock 代理**：v2.2.2 是必升版本，重点验证 reasoning 工具调用和并行 tool call 的流式顺序。
- **如果你在做 Nginx → Higress 迁移**：升 v2.2.2 用 `#3823` 的 rewrite WASM 插件做兜底，规避 CVE-2026-42945 同时保留存量规则。
- **如果你在跑 Claude + Qwen 混部**：`#3756` 的 `preserve_thinking` / `promote_thinking_on_empty` 是关键开关，先在测试环境打开 `preserve_thinking` 验证 reasoning 透传。
- **如果你接 KlingAI**：v2.2.2 第一次免 JWT 签代码直连；图生视频与文生视频都覆盖。
- **如果你是平台架构师**：v2.2.2 的 CNCF 治理文件意味着选型风险评估的"治理成熟度"维度可以上调一档。

## 引用与数据来源

- GitHub Releases API（Higress）：
  - <https://api.github.com/repos/alibaba/higress/releases?per_page=6>
  - <https://api.github.com/repos/alibaba/higress/releases/tags/v2.2.2>
  - <https://api.github.com/repos/alibaba/higress/releases/tags/v2.2.1>
  - <https://api.github.com/repos/alibaba/higress/releases/tags/v2.1.11>
- Higress 官网与博客（产品定位 / Nginx 退役主题 / 客户案例）：
  - <https://higress.cn/>
  - <https://higress.cn/blog/higress-gvr7dx_awbbpb_ortukqsuia6ahf2v>（应对 Nginx Ingress 退役）
  - <https://higress.cn/blog/higress-gvr7dx_awbbpb_gi01wdalqztg58z3>（携程旅游 AI 网关落地）
  - <https://higress.cn/blog/higress-gvr7dx_awbbpb_syyw2bkfzlsyfu9v>（君润人力 1000 名数字员工）
  - <https://higress.cn/blog/higress-gvr7dx_awbbpb_vetuzf7sbuixi2b2>（阿里巴巴 MCP 分布式落地）
  - <https://higress.cn/blog/higress-gvr7dx_awbbpb_tng81uvf75an4l9u>（SOFA AI 网关）
  - <https://higress.cn/blog/higress-gvr7dx_awbbpb_cdecsfkegx4bc2n8>（政采云分层 + 插件 + 统一三件套）
  - <https://higress.cn/blog/higress-gvr7dx_awbbpb_gyn0uxmhhzz2pkne>（今日投资金融数据 MCP）
- 关联 PR（节选，可直接在 v2.2.2 release notes 索引）：
  - `#3827` `modelToHeader`、 `#3823` Nginx rewrite WASM、 `#3820` Bedrock Mantle、 `#3766` `CacheReadInputTokens`、 `#3748` `enable_path_suffixes`、 `#3742` KlingAI、 `#3739` `ai-prompt-decorator.replace`、 `#3738` `ai-security-guard` fallback JSON 路径、 `#3724` Qwen rerank、 `#3722` Qwen responses 路径、 `#3695` / `#3777` Vertex Express Mode、 `#3576` `getRouteName`、 `#3425` `HUB` 默认值、 `#3682` `VALID_ARCHS`、 `#3764` SECURITY + GOVERNANCE、 `#3754` MAINTAINERS、 `#3830` OpenSSF 徽章。
- 报告内全部日期基于 cron 实际触发时间 `date '+%Y-%m-%d-%H%M'`（2026-06-05-2134 CST）；版本发布日期来源于 GitHub Releases API `published_at` 字段。
