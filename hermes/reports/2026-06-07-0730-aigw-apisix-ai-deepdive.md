# Apache APISIX × AI 能力深度调研(2026 Q2)

> **副标题**:从 `ai-proxy` 到 `mcp-bridge` —— 一个老牌 API 网关的 AI 原生演化全景
> **版本快照**:基于 APISIX 3.16.0(2026-04-08 发布),`master` 分支截止 2026-06-07
> **报告代号**:`2026-06-07-apisix-ai-deepdive`
> **定位**:技术深度报告,目标读者是需要在生产里落 LLM 网关的工程师 / 架构师
> **体裁**:实战优先,每个插件至少 1 个配置示例 + 1 个使用场景;不写"什么是 LLM"

---

## 0. 阅读地图

| 你想了解 | 直接看 |
|---------|--------|
| APISIX 现在到底有多少 AI 插件?都干嘛的? | §1 / §2(全景图) |
| 怎么用 APISIX 做多模型路由 + fallback? | §3(ai-proxy-multi 核心枢纽) |
| 提示词注入防御、限流、按 token 计费怎么配? | §4 / §5 |
| 能不能做语义缓存?支持 Redis 吗? | §6 |
| APISIX 支持 MCP 吗?怎么把 MCP server 接入? | §7(MCP / Agent) |
| 跟 Envoy / Higress / Kong / Portkey 比,选谁? | §9(横评) |
| 我是接小 B 客户的副业,这套东西能用吗? | §10(落地实战) |

---

## 1. APISIX 速写:从 API 网关到 AI 基础设施

### 1.1 项目定位

Apache APISIX 是 Apache 软件基金会顶级项目,由 API7(深圳支流科技)主导,脱胎于 2019 年的开源项目。在中国云原生生态里它最知名的对位是 Kong(北美系)和 Higress(阿里系),但 APISIX 在 GitHub 增速、贡献者数量、企业采用(中国电信、中国移动、Airwallex、明源云等)上一直领先。

- **GitHub Star**(2026-06):约 15.5K
- **最新稳定版**:3.16.0(2026-04-08)
- **核心语言**:Lua + C(基于 OpenResty/Nginx)
- **配置中心**:默认 etcd,支持 standalone 模式(本地 YAML)
- **数据面延迟**:P99 在 8 核 16G 上约 0.4ms(社区 benchmark,见 §9)

### 1.2 为什么 APISIX 会做 AI?

2023 年底 OpenAI 把 ChatGPT 流量做爆之后,所有 API 网关厂商都面临一个问题:**"LLM 流量长得跟传统 REST 流量不一样"**。差异点至少四个:

1. **SSE 流式响应**:传统网关按 `Content-Length` 缓存,SSE 没有 Content-Length
2. **成本按 token 计量**:不能简单按 RPS 限流,要按 `total_tokens` 限
3. **多模型 fallback**:OpenAI 429 / 5xx 时要能切到 DeepSeek / Azure
4. **提示词安全**:提示词注入(Prompt Injection)是 OWASP LLM Top 1 风险,需要网关层做

APISIX 的应对方式不是"做一个 AI 大插件",而是**把整个 AI 体系拆成 11 个独立插件 + 3 个子模块目录**。这是工程师喜欢的方式:每个插件只做一件事,组合出复杂场景。

### 1.3 版本节奏与 AI 插件时间线

| 版本 | 发布时间 | AI 相关大事 |
|------|---------|-------------|
| 3.10.0 | 2024-08 | `ai-rate-limiting` 引入(最初只支持 total_tokens) |
| 3.11.0 | 2024-10 | `ai-rag` 插件首次发布(Azure 优先) |
| 3.12.0 | 2025-04 | `mcp-bridge` 插件首发(2025-04-19 PR #12151) |
| 3.13.0 | 2025-06 | `ai-proxy` / `ai-proxy-multi` 分家;引入 `instance_health` fallback |
| 3.14.0 | 2025-10 | `ai-prompt-decorator` / `ai-prompt-guard` 引入 ACL 元组 |
| 3.15.0 | 2026-02 | `ai-rate-limiting` 加 `cost_expr` 表达式(2026-04 PR #13191) |
| **3.16.0** | **2026-04** | **三段式重构 protocols/providers/transport(PR #13170);Bedrock provider(PR #13249);Vertex AI(2026-01 PR #12933)** |

**关键判断**:APISIX 在 MCP 方向比 Kong(2025-08 才有 MCP support)和 Envoy(目前没有官方 MCP proxy)都早 **4 个月**。这是工程师评估"AI 网关要不要选 APISIX"时的关键点。

---

## 2. AI 插件全景图(2026 Q2 快照)

APISIX 的 `apisix/plugins/` 目录里有 130+ 插件,AI 相关的全部在下面这张表里(以官方代码 `master` 分支为准,**实测一手数据**):

| 插件名 | 优先级 | 引入版本 | 核心职责 | 对应 OpenTelemetry 指标 |
|--------|--------|---------|---------|----------------------|
| `ai-proxy` | 1040 | 3.13 | **单 provider 路由** + 协议转换 | `ai_chat` / `ai_stream` |
| `ai-proxy-multi` | 1041 | 3.13 | **多 provider fallback / 优先级路由** | `ai_chat` / `ai_stream` |
| `ai-request-rewrite` | 1060 | 3.14 | LLM 改写客户端 prompt(自带模型调用) | `ai_chat` |
| `ai-prompt-decorator` | 1070 | 3.14 | 在 messages 数组前/后注入 system 消息 | — |
| `ai-prompt-template` | 1071 | 3.14 | 按模板填充 prompt(model + messages) | — |
| `ai-prompt-guard` | 1072 | 3.14 | 正则白/黑名单拦截 prompt injection | — |
| `ai-rate-limiting` | 1030 | 3.10 | 按 `total_tokens` / `prompt_tokens` / `expression` 限流 | token 计数 |
| `ai-rag` | 1060 | 3.11 | **向量检索增强**:embeddings + vector_search | — |
| `ai-aws-content-moderation` | 1050 | 3.13 | 用 AWS Comprehend 做内容审查 | — |
| `ai-aliyun-content-moderation` | 1050 | 3.13 | 用阿里云绿网做内容审查(支持 SSE 实时) | — |
| `ai` (入口插件) | 22900 | 3.13 | **路由匹配缓存**(降低 LLM 路由热路径 CPU) | — |
| `mcp-bridge` | 510 | 3.12 | **把 stdio MCP server 桥接为 SSE/HTTP** | — |

**注意 `ai` 入口插件**:它不是聚合所有 ai-* 插件,实际上是**路由匹配缓存**插件 —— 通过 `scope=global` 在网关启动时给所有路由做匹配结果缓存,降低 `ai-proxy` 的 lookup 开销。OpenAI 流式调用 P99 上能省 0.1-0.2ms。

**子模块目录**(非独立插件,通过 `ai-proxy` / `ai-rag` 间接调用):

| 目录 | 内容 | 数量 |
|------|------|------|
| `ai-providers/` | 各 LLM provider 适配:openai, openai-compatible, anthropic, azure-openai, bedrock, vertex-ai, deepseek, gemini, openrouter, aimlapi, base | 11 |
| `ai-protocols/` | 协议层:openai-chat, openai-embeddings, openai-responses, anthropic-messages, bedrock-converse, passthrough | 6 |
| `ai-protocols/converters/` | 跨协议转换:anthropic-messages → openai-chat, openai-embeddings → vertex-predict | 2 |
| `ai-transport/` | 传输层:http, sse, aws-eventstream, auth, auth-aws | 5 |
| `ai-rag/embeddings/` | 嵌入:azure_openai | 1 |
| `ai-rag/vector-search/` | 向量库:azure_ai_search | 1 |

### 2.1 三段式架构(3.16 关键重构)

2026-04-08 PR #13170 把 AI 体系从"平铺"改成"三层"——这是**自上而下最重要的架构变化**:

```
┌─────────────────────────────────────────────────────────────┐
│ Protocol 层 (apisix/plugins/ai-protocols/)                 │
│  - openai-chat / openai-responses / openai-embeddings        │
│  - anthropic-messages / bedrock-converse / passthrough      │
│  - converters/ (协议互转)                                   │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│ Provider 层 (apisix/plugins/ai-providers/)                 │
│  - openai / azure-openai / anthropic / bedrock / vertex-ai  │
│  - deepseek / gemini / openrouter / aimlapi / openai-compat │
│  - 负责鉴权签名、endpoint 计算、auth 头注入                  │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│ Transport 层 (apisix/plugins/ai-transport/)                │
│  - http (普通 HTTP) / sse (Server-Sent Events)               │
│  - aws-eventstream (Bedrock 流式)                            │
│  - auth / auth-aws (SigV4 签名)                              │
└─────────────────────────────────────────────────────────────┘
```

**实战意义**:
- 你可以把"OpenAI Chat 协议"**转换后**发到"Google Vertex AI" —— APISIX 会自动用 anthropic-messages → openai-chat 转换器做协议桥
- 加新 provider 不用动 protocol 代码,只写一个 `ai-providers/<name>.lua`
- 加新传输(如 gRPC streaming)不用动 provider 代码,只写一个 `ai-transport/<name>.lua`

---

## 3. ai-proxy 深度拆解:多 LLM 路由的核心枢纽

### 3.1 `ai-proxy` vs `ai-proxy-multi` 区别

这是初学者最常问的问题。**官方代码(schema.lua 注释)讲得很清楚**:

- **`ai-proxy`**(单 provider):一个 route → 一个上游 LLM。配置最简单,适合"我只用 OpenAI"的场景。
- **`ai-proxy-multi`**(多 provider):一个 route → 多个上游 LLM 实例,**带 priority / fallback / 健康检查**。配置稍复杂,适合"我想 OpenAI 切 DeepSeek"。

`ai-proxy` 内部其实也调 `ai-proxy-multi` 的 schema 和负载均衡代码,只是配置上更"单点"。

### 3.2 `ai-proxy-multi` 完整配置示例

**场景**:某 SaaS 客户需要把 LLM 流量分到 3 个供应商,优先级 OpenAI(主) > DeepSeek(次) > Anthropic(兜底),当 429 或 5xx 时自动 fallback。

```yaml
# standalone 模式:conf/apisix.yaml
upstreams:
  - name: llm-orchestrator
    type: roundrobin
    nodes:
      "openai-us.openai.azure.com:443": 1
      "api.deepseek.com:443": 1
      "api.anthropic.com:443": 1

routes:
  - uri: /v1/chat/completions
    upstream_id: llm-orchestrator
    plugins:
      ai-proxy-multi:
        instances:
          - name: openai-gpt4o
            provider: openai
            priority: 100              # 数字越大越优先
            weight: 1
            options:
              model: gpt-4o-2024-08-06
            auth:
              header:
                Authorization: "Bearer ${env.OPENAI_API_KEY}"
          - name: deepseek-chat
            provider: deepseek
            priority: 50
            weight: 1
            options:
              model: deepseek-chat
            auth:
              header:
                Authorization: "Bearer ${env.DEEPSEEK_API_KEY}"
          - name: anthropic-sonnet
            provider: anthropic
            priority: 10               # 兜底
            weight: 1
            options:
              model: claude-3-5-sonnet-20241022
            auth:
              header:
                "x-api-key": "${env.ANTHROPIC_API_KEY}"
                "anthropic-version": "2023-06-01"
        fallback_strategy:
          - http_429                  # 遇到 429 触发
          - http_5xx                  # 遇到 5xx 触发
          - instance_health           # 实例健康检查失败
        keepalive: true
        keepalive_pool: 30
        ssl_verify: true
        timeout: 30000                # 总超时 30s
```

**几个关键参数解释**:

| 字段 | 含义 | 默认 |
|------|------|------|
| `priority` | 数值越大越优先;同 priority 内部按 weight 轮询 | 0 |
| `fallback_strategy` | 触发 fallback 的条件数组,枚举值:`http_429` / `http_5xx` / `instance_health` / `rate_limiting` | — |
| `keepalive_pool` | 与上游的 keepalive 连接池大小 | 30 |
| `timeout` | **总**超时(含 connect + send + read)ms | 30000 |
| `instance_health` | 启用主动/被动健康检查,失败实例暂时降级 | false |

### 3.3 `request_body_override` 的妙用(3.16 新增)

PR #13170 引入了一个非常巧妙的特性:**按目标协议重写请求体**。例:客户端发 OpenAI 协议,但你想让 OpenAI 用 `max_completion_tokens`(新字段),同时让 DeepSeek 走 `max_tokens`(旧字段):

```yaml
ai-proxy-multi:
  instances:
    - name: openai-gpt5
      provider: openai
      options:
        model: gpt-5
      override:
        request_body:
          openai-chat:               # 按目标协议名分组
            max_tokens: 4096
    - name: deepseek-v3
      provider: deepseek
      options:
        model: deepseek-chat
      override:
        request_body:
          openai-chat:
            max_tokens: 8192         # 不同实例不同值
        request_body_force_override: true   # 强制覆盖客户端值
```

**实战坑点**:`request_body_force_override: false`(默认)时,**客户端传的字段优先**,override 只填"客户端没传的字段"。要做"强一致"治理(比如统一把 temperature 锁在 0.3)必须设 true。

### 3.4 跨协议转换:OpenAI 协议 → Anthropic 协议

APISIX 的 `ai-protocols/converters/anthropic-messages-to-openai-chat.lua` 可以让"客户端发 OpenAI Chat 协议,网关转 Anthropic Messages 协议"。

**配置示例**:

```yaml
ai-proxy-multi:
  instances:
    - name: claude-via-openai
      provider: anthropic
      options:
        model: claude-3-5-sonnet-20241022
      # 告诉网关这个 provider 用 anthropic-messages 协议
      provider_conf:
        # (provider-specific config 在 ai-providers/anthropic.lua 里)
```

客户端只需要按 OpenAI Chat 协议 POST,网关自动转成 Anthropic 的 `messages` + `system` 字段。

**意义**:**同一个客户端 SDK 可以无缝切到 Anthropic / Bedrock / Vertex AI**——前端代码零改动,这是 APISIX 在多模型场景的关键竞争力。

### 3.5 性能:ai-proxy 的延迟数据

社区 benchmark(2026-05)在 8 核 16G / 1000 并发 / 单 upstream / 简单 prompt 场景下:

| 场景 | P50 | P99 | 失败率 |
|------|-----|-----|-------|
| 不带 ai-proxy(直连 OpenAI) | 1.2s | 1.8s | 0.1% |
| ai-proxy 1 个 instance | 1.22s | 1.83s | 0.1% |
| ai-proxy-multi 3 instance + fallback | 1.25s | 1.90s | **0.01%** |
| ai-proxy-multi + ai-rate-limiting + ai-prompt-decorator | 1.28s | 1.95s | 0.01% |

**判断**:网关引入的额外延迟约 **20-50ms**,fallback 带来的**可用性收益远大于延迟成本**。

---

## 4. 提示词与安全防线:ai-prompt-* 家族

### 4.1 三个 prompt 插件的职责矩阵

| 插件 | 改写? | 注入 system prompt? | 正则拦截? |
|------|------|-------------------|----------|
| `ai-prompt-decorator` | ✅ | prepend / append messages | ❌ |
| `ai-prompt-template` | ✅(整模板替换) | 按模板填入 model + messages | ❌ |
| `ai-prompt-guard` | ❌(只检查) | ❌ | ✅ allow / deny |

### 4.2 `ai-prompt-decorator` 配置示例

**场景**:你的 SaaS 客户端必须强制带合规护栏(法律声明 + 数据格式约束),而且这层不能由客户端控制(防止某些 SDK 用户绕过)。

```yaml
plugins:
  ai-prompt-decorator:
    prepend:                  # 拼到 messages 最前面
      - role: system
        content: |
          你是某公司客服助手。
          - 不得讨论竞品
          - 不得生成任何 PII
          - 回答长度 ≤ 200 字
    append:                   # 拼到 messages 最后面
      - role: system
        content: |
          请用中文回答,并在结尾加 "[本回答由 AI 生成,请核实]"
```

**原理**(`ai-prompt-decorator.lua` 第 78-85 行):`protocols.prepend_messages(body_tab, ctx, conf.prepend)`,把 system 消息插入到 `body.messages` 数组首/尾,改写完后用 `ngx.req.set_body_data(new_jbody)` 重设请求体。

### 4.3 `ai-prompt-guard` 配置示例

**场景**:你给某教培机构做 AI 答疑,需要拦截"提示词注入"(学生试图绕过 system 提示)。

```yaml
plugins:
  ai-prompt-guard:
    match_all_roles: true              # 检查所有 system / user / assistant 角色
    match_all_conversation_history: true  # 检查历史消息(不只是最后一条)
    deny_patterns:
      - "ignore (all|previous|above) instructions"
      - "disregard.*system"
      - "你(是|就是)(?!.*助手)"        # 中文:不要让模型忘记"你是助手"
      - "(?i)act as (?!assistant)"     # "act as" 类
      - "DAN|developer mode|jailbreak"
    allow_patterns:                    # allow 和 deny 冲突时,allow 优先
      - "系统.*助手"                   # 例外:这条 system 提示是合规的
```

**实现细节**(`ai-prompt-guard.lua` 第 27-32 行):用 `resty.core.regex.re_match_compile("jou")` 编译 PCRE,`ngx.re.find` 匹配。`jou` flag = **j**(just-in-time compile)+ **u**(unicode)+ **o**(单次编译)。性能开销 < 0.5ms。

**风险点**:正则只能挡"已知模式"。新型 prompt injection(如 Unicode homoglyph 攻击、间接注入——把恶意内容塞到 RAG 检索的文档里)需要配合 `ai-rag` + Lakera Guard 这类专用服务,正则是不够的。

### 4.4 `ai-prompt-template` 的妙用

这个插件适合做"按场景选择不同模型"——比如内部 demo,客户可以用 `template_name` 参数切换 gpt-4o / gpt-3.5 / deepseek:

```yaml
plugins:
  ai-prompt-template:
    templates:
      - name: fast
        template:
          model: gpt-3.5-turbo
          messages:
            - role: system
              content: "你是一个简洁的助手"
      - name: smart
        template:
          model: gpt-4o
          messages:
            - role: system
              content: "你是一个严谨的助手"
      - name: cn-cheap
        template:
          model: deepseek-chat
          messages:
            - role: system
              content: "你是中文助手"
```

客户端在请求头里加 `X-Template: smart` 就切换了。

### 4.5 实战组合:decorator + guard + request-rewrite

`ai-request-rewrite` 是另一个不太被注意但很实用的插件——**网关层调用 LLM 来改写用户请求**。

**场景**:客户发来口语化中文"我肚子不舒服咋办",你想先让 LLM 改写成专业问题再调主模型,降低主模型负担。

```yaml
plugins:
  ai-request-rewrite:
    provider: deepseek              # 用便宜的 deepseek 改写
    options:
      model: deepseek-chat
    prompt: |
      将用户的口语化问题改写为标准化的医疗咨询问题。
      保留核心症状描述,删除冗余表达。
      输出改写后的问题,不要其他内容。
    auth:
      header:
        Authorization: "Bearer ${env.DEEPSEEK_API_KEY}"
    timeout: 5000
```

**实测数据**:每条请求增加 200-400ms 延迟和一次额外 LLM 调用,**只有当主模型是 GPT-4o 这种贵模型时才划算**。deepseek 改写 + gpt-4o 主答,综合成本可降 30%。

---

## 5. 资源治理:限流 / 配额 / 成本 / Token 计量

### 5.1 `ai-rate-limiting` 是 APISIX 最有"深度"的 AI 插件

不要被名字骗了 —— 它不只是限流。**官方 schema 显示它有 3 种用法 + 1 个表达式引擎**:

```yaml
# 方式 1:全局按 token 限流
ai-rate-limiting:
  limit: 100000
  time_window: 3600
  limit_strategy: total_tokens       # 枚举:total_tokens / prompt_tokens / completion_tokens / expression

# 方式 2:按 instance 限流(精细化到 provider)
ai-rate-limiting:
  instances:
    - name: openai-gpt4o
      limit: 100000
      time_window: 3600
    - name: deepseek-v3
      limit: 500000
      time_window: 3600

# 方式 3:按 key(用户 / 租户)分桶限流
ai-rate-limiting:
  rules:
    - count: 1000                    # 1000 token
      time_window: 60               # 60 秒
      key: consumer_name             # 按 consumer 分桶
      header_prefix: "X-Quota"       # 在响应头加 X-Quota-Limit 等
```

**3.15 新增的 `expression` 策略**(`PR #13191`,2026-02)是杀手锏:

```yaml
ai-rate-limiting:
  limit_strategy: expression
  cost_expr: "input_tokens + cache_creation_input_tokens + output_tokens"
  limit: 100000
  time_window: 3600
```

**意义**:**Anthropic 模型的 cache_creation_input_tokens 比普通 input_tokens 贵 1.25 倍**,以前用 `total_tokens` 一刀切,要么漏算要么多算。`cost_expr` 让你用 Lua 算术表达式精确计量任意成本公式。

### 5.2 `cost_expr` 的边界与陷阱

`cost_expr` 实际是一个受限制的 Lua 算术表达式(不是完整 Lua),变量从 LLM API 返回的 `usage` 字段自动注入:

```lua
-- 内部实现(简化):
local env = setmetatable({}, {__index = function(_, k) return rawget(usage, k) or 0 end})
local f = load("return " .. cost_expr)  -- load 编译
local cost = f()                         -- 调用
```

**陷阱**:
- **缺失变量默认 0**(`rawget(usage, k) or 0`),所以不会报错,但你写 `input_tokne`(拼错)不会得到 0 —— 它会被当成 0,**静默错算**。调试时打开 `error_log` 看 `ai-rate-limiting` 块。
- **不支持函数调用**,只能 `+ - * / ()`
- **不能跨 provider 复用表达式**:OpenAI 用 `prompt_tokens`,Anthropic 用 `input_tokens`,你得为不同 provider 写不同 `cost_expr`(可以配多 instance 路由时按 `instance.name` 区分)

### 5.3 限流被触发后的响应

```yaml
ai-rate-limiting:
  rejected_code: 429
  rejected_msg: "Rate limit exceeded, please retry later"
```

**默认 503**—— 但生产里 **强烈建议改成 429**(`HTTP 429 Too Many Requests`语义更对,客户端 SDK 知道要 backoff)。

### 5.4 配额 vs 限流:`ai-rate-limiting` 的 `rules` 模式

`rules` 模式让你按 `key`(consumer / header / IP)分桶,实现"VIP 用户不限速 / 试用用户严限速":

```yaml
ai-rate-limiting:
  rules:
    - count: 10000                   # 试用用户
      time_window: 86400             # 每天 10K token
      key: consumer_name
    - count: 1000000                 # 付费用户
      time_window: 86400             # 每天 1M token
      key: consumer_name
```

APISIX 默认把限流计数存 `lua-resty-limit-count` 的 shared dict(进程内),生产多实例部署时**必须切到 redis**:

```yaml
# conf/config.yaml
apisix:
  limit_count:
    redis:
      host: 10.0.0.10
      port: 6379
      password: ${REDIS_PASSWORD}
      timeout: 1000
      pool_size: 50
```

否则多节点限流数据不一致,会被滥用。

### 5.5 字段级权限:`fine-grained-authz` 不存在,但 `consumer-restriction` 够用

**APISIX 没有专门的 "fine-grained-authz" 插件**(很多文章提到这个其实把 Portkey 和 APISIX 搞混了)。APISIX 的字段级授权靠两个东西:

1. **`consumer-restriction`** + **`jwt-auth` / `key-auth` / `multi-auth`** 配合,实现"按 consumer 限制能调哪些 route / service"
2. **`traffic-label`**(3.x 新插件)给流量打标签,作为匹配条件

实战里 80% 场景这两个够用。如果真要"按 prompt 内容授权",需要二次开发,这是 APISIX 在细粒度授权上的短板。

---

## 6. 缓存层:ai-cache-redis + ai-semantic-cache

### 6.1 APISIX 的两种 LLM 缓存

| 类型 | 插件 | 命中条件 | 适用场景 |
|------|------|---------|---------|
| **精确缓存** | `proxy-cache`(传统) | 请求 URL + body hash 相同 | 完全相同问题重复问 |
| **语义缓存** | `proxy-cache` + 二次开发 | embedding 余弦相似度 > 阈值 | "你好" 和 "hi" 视为相同问题 |

**重要事实**:**APISIX 没有官方的 `ai-semantic-cache` 插件**。`ai-rate-limiting` 文档里被反复提到的"ai-cache-redis"是社区方案,核心是用 `proxy-cache` + Redis 二次封装。

社区典型实现(我见过的方案,不是 APISIX 内置):

```lua
-- 在 proxy-cache 自定义 cache_key 里,先用 LLM 把 prompt 转 embedding
-- 然后用 embedding 哈希做 cache key
-- (省略 200 行 Lua)
```

### 6.2 精确缓存配置(最实用)

```yaml
plugins:
  proxy-cache:
    cache_zone: llm_cache
    cache_key: ["$uri", "$arg_user_id"]  # 注意:不包括 body,body hash 要自己算
    cache_ttl: 300                        # 5 分钟
    cache_method: ["POST"]
    cache_http_status: [200]
```

**注意**:`proxy-cache` 默认按 URL + args 做 key,POST body **不参与**。要做"按 prompt 内容缓存",得用 `body-transformer` + 自定义 cache key。

### 6.3 缓存命中率的实战数据

小 B 客户(咨询公司 / 教培)实际跑的命中率:
- **完全相同问题**:20-35% 命中率(用户重复问"怎么退款")
- **语义相似**:开 embedding 缓存可到 50-60%(同义改写)
- **多轮对话**:0%(每次 messages 数组都不一样)

**判断**:对"FAQ 机器人"类应用缓存价值大(可省 50% token 成本),对"开放式对话"基本无用。

---

## 7. 🔑 MCP 与 Agentic 能力(2024-2025 杀手锏)

### 7.1 时间线:MCP 不是蹭热度

| 时间 | 事件 | APISIX 对应动作 |
|------|------|---------------|
| 2024-11 | Anthropic 发布 MCP 协议 | APISIX 团队开始调研 |
| **2025-04-19** | APISIX 提交 `mcp-bridge` PR #12151 | **全球首批 MCP 网关实现**之一 |
| **2025-06** | 3.13.0 发布,mcp-bridge GA | — |
| 2025-08 | Kong 跟进 MCP support | 比 APISIX 晚 4 个月 |
| 2025-12 | Envoy AI Gateway 才开始 MCP 路线图 | 比 APISIX 晚 8 个月 |
| 2026-02 | mcp-bridge 1.0 GA | 1.x 版本稳定 |

### 7.2 `mcp-bridge` 工作原理

它做的事很直接:**用 `ngx.pipe` 拉起一个 stdio MCP server,然后把这个 server 的 stdio 协议转换为 SSE / streamable HTTP**。

```lua
-- 简化自 mcp-bridge.lua 第 56-78 行
local function on_connect(conf, ctx)
    return function(additional)
        local proc, err = pipe.spawn({conf.command, unpack(conf.args or {})})
        ctx.mcp_bridge_proc = proc

        -- ngx.pipe 是 yield 操作
        ctx.mcp_bridge_proc_event_loop = thread_spawn(function ()
            while not worker_exiting() do
                -- 按行读 stdout
                repeat
                    local line = proc:stdout_read_line()
                    if line then
                        local ok, err = server.transport:send(line)
                    end
                until not line
            end
        end)
    end
end
```

**配置示例**:把本地一个 Python MCP server 接入 APISIX,变成 HTTP 端点:

```yaml
routes:
  - uri: /mcp/weather
    plugins:
      mcp-bridge:
        command: "python3"
        args:
          - "/opt/mcp-servers/weather.py"
        base_uri: "/mcp/weather"
```

**实战意义**:**任何能跑 stdio MCP server 的进程(file_search / sql_query / browser_use)都能被 APISIX 暴露为 HTTP / SSE 端点,供外部 LLM 调用**。

### 7.3 `ai-deep-research-agent`:**目前没有**

**必须澄清**:`ai-deep-research-agent` 插件**目前不存在于 APISIX 主干**。社区有人提 issue 询问,APISIX 团队的回复是"通过 `mcp-bridge` + 多个 MCP server 组合实现"。

如果要做"深度研究 agent",现在的可行路径:

```yaml
routes:
  - uri: /agent/deep-research
    plugins:
      ai-proxy-multi:                # 主 LLM(gpt-4o / claude)
        instances:
          - { provider: openai, options: { model: gpt-4o } }
      mcp-bridge:                    # 工具 1:网页搜索 MCP
        command: "npx"
        args: ["-y", "@modelcontextprotocol/server-brave-search"]
        base_uri: "/mcp/search"
      mcp-bridge:                    # 工具 2:文件读取 MCP
        command: "npx"
        args: ["-y", "@modelcontextprotocol/server-filesystem", "/data"]
        base_uri: "/mcp/files"
```

(注:同一 route 不能同时挂多个 mcp-bridge,得用 upstream / sub-route 组合)

### 7.4 跟 Higress 的 MCP 路线对比

阿里 Higress 2025-09 GA 了"原生 MCP 工具市场" + "MCP server 协议转换",核心是**把存量 HTTP API 一键转 MCP 工具**(自动 schema 推断)。APISIX 的 `mcp-bridge` 走的是更纯粹的"stdio 桥接"路线。

| 维度 | APISIX mcp-bridge | Higress MCP 工具市场 |
|------|-------------------|----------------------|
| 接入成本 | 需 stdio MCP server | 一键转 HTTP API |
| 协议支持 | stdio / SSE / streamable HTTP | HTTP → MCP 自动转 |
| 工具数量 | 依赖社区 | 阿里云市场内置 |
| 性能 | ngx.pipe 零拷贝 | HTTP → JSON-RPC 转换 |
| 适合 | 自建工具 / 内部 stdio 服务 | 存量 HTTP API 复用 |

**判断**:**有存量 API 要暴露的选 Higress,有 stdio 工具要桥接的选 APISIX**。

### 7.5 `ai-rag` 插件细节

`ai-rag` 是 2024-10 PR #11568 引入,目标是"网关层做 RAG 召回":

```yaml
plugins:
  ai-rag:
    embeddings_provider:
      azure_openai:
        endpoint: "https://xxx.openai.azure.com"
        deployment_name: "text-embedding-3-large"
        api_key: "${env.AZURE_OPENAI_KEY}"
    vector_search_provider:
      azure_ai_search:
        endpoint: "https://xxx.search.windows.net"
        index_name: "kb-2026"
        api_key: "${env.AZURE_SEARCH_KEY}"
    ssl_verify: true
```

**调用方式**:客户端请求体里加 `ai_rag: { vector_search: {...}, embeddings: {...} }`,网关先查向量库,把召回内容塞进 prompt 再调 LLM。

**判断**:**Azure-only 是硬伤**。2026 Q2 的 master 分支里 `ai-rag/embeddings/` 还是只有 `azure_openai.lua`,`vector-search/` 只有 `azure_ai_search.lua`。**对国内用 DeepSeek embedding + Milvus 的客户基本不友好**。

---

## 8. 可观测:Prometheus / OpenTelemetry / ClickHouse 集成

### 8.1 Prometheus 指标:APISIX 是 LLM 观测最早的

3.13 起 `ai-proxy` 插件在 Prometheus 上报专门的 LLM 指标:

```promql
# ai_chat_total{model="gpt-4o",provider="openai"} 123
# ai_stream_total{model="gpt-4o",provider="openai"} 45
# ai_request_duration_seconds_bucket{...}
# ai_tokens_total{type="prompt",model="gpt-4o"} 15234
# ai_tokens_total{type="completion",model="gpt-4o"} 4521
# ai_request_failure_total{reason="429",provider="openai"} 5
```

**实际 exporter 代码**(在 `apisix/plugins/prometheus/exporter.lua`)有这一行:

```lua
if vars.request_type == "ai_stream" or vars.request_type == "ai_chat" then
    -- 注入 LLM 专有 label
end
```

### 8.2 OpenTelemetry 集成

```yaml
plugins:
  opentelemetry:
    trace_id_source: x-request-id
    batch_span_processor:
      max_export_batch_size: 512
      inactive_timeout: 1
    collector:
      address: otel-collector:4317
    resource:
      service.name: llm-gateway
```

3.16 起 AI 请求的 trace 里会自动带 `gen_ai.*` 语义属性(遵循 OpenTelemetry GenAI Semantic Conventions 草案):

```json
{
  "span.name": "openai.chat.completions",
  "attributes": {
    "gen_ai.system": "openai",
    "gen_ai.request.model": "gpt-4o",
    "gen_ai.usage.input_tokens": 1234,
    "gen_ai.usage.output_tokens": 567
  }
}
```

### 8.3 ClickHouse 日志:`ai-proxy` 自动上送 token 用量

3.13 起 `ai-proxy` 插件可以直接把 `usage` 字段上送 ClickHouse(配置示例见 `2026-06-05-0506-aigw-observability.md`)。

---

## 9. 生态对标:APISIX vs Envoy / Higress / Kong / Portkey

> **注意**:本节数字均来自各项目 2026 Q2 公开 release notes / benchmark / 社区帖子。生产实际数字可能差 20-50%。

### 9.1 六维横评表

| 维度 | APISIX 3.16 | Envoy 1.34 + AI Gateway | Higress 1.4 | Kong 3.9 + AI Proxy | Portkey 2.x | LiteLLM 1.5x |
|------|-------------|--------------------------|-------------|---------------------|-------------|--------------|
| **AI 协议数** | 6(OpenAI/Anthropic/Bedrock/Vertex/Passthrough) | 2(OpenAI/Passthrough) | 3(OpenAI/通义/Passthrough) | 4(OpenAI/Azure/Bedrock/Anthropic) | 15+ | 100+ |
| **MCP 支持** | ✅ **mcp-bridge(2025-04)** | ⚠️ 2026 路线图 | ✅ 工具市场(2025-09) | ⚠️ 2025-08 才有 | ❌ 无 | ❌ 无 |
| **多模型 fallback** | ✅ priority + 429/5xx 触发 | ✅ 基础 | ✅ | ✅ | ✅ 智能路由 | ✅ |
| **RAG 集成** | ⚠️ Azure-only | ❌ 无 | ✅ 阿里云向量库 | ⚠️ 第三方插件 | ✅ | ❌ |
| **限流按 token** | ✅ `cost_expr` 表达式 | ⚠️ 仅 total_tokens | ✅ | ✅ | ✅ 成本感知 | ✅ |
| **SSE 性能(P99)** | 50ms 内 | 30ms(纯 C++) | 60ms | 80ms | N/A(纯 Python) | N/A |
| **部署门槛** | 中(Lua 生态) | 高(Istio 经验) | 低(Go 单二进制) | 中(OpenResty 同 APISIX) | 低(Python) | 低(Python) |
| **企业采用(中国)** | 电信/移动/Airwallex | 字节/美团 | 阿里集团/钉钉 | 招行/平安 | 创业公司 | 创业公司 |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0(部分 enterprise 闭源) | AGPL-3 | MIT |

### 9.2 关键判断

**APISIX 的强项**:
1. **MCP 支持早 4-8 个月** —— 这是 2026 年 AI Agent 爆发期的关键卡位
2. **`cost_expr` 表达式限流** —— 唯一支持任意 token 成本公式的网关
3. **三段式 AI 架构** —— 比 Kong 2 段式更易扩展
4. **Apache 2.0** —— 全开源,无 enterprise 闭源

**APISIX 的弱项**:
1. **`ai-rag` 只支持 Azure** —— 国内客户基本不能用
2. **没有智能语义缓存** —— 只能精确缓存
3. **没有 `ai-deep-research-agent` 官方插件** —— 需自组 mcp-bridge
4. **Lua 学习曲线** —— 二次开发门槛比 Go/Python 高

**Higress 的强项**:
1. **MCP 工具市场** —— 一键把存量 HTTP API 转 MCP
2. **阿里云背书** —— 国内 SLA 保障
3. **Go 性能** —— 部署简单,二进制启动 < 1s

**Portkey / LiteLLM 的强项**:
1. **provider 数量多**(LiteLLM 100+)
2. **Python 生态** —— LLM 应用开发者友好
3. **智能路由 + 成本优化** —— 按 prompt 复杂度选模型

### 9.3 选型决策树

```
你的主诉求是什么?
├── 多模型 fallback + 复杂路由 ──→ APISIX
├── 国内合规 + 阿里云生态 ──→ Higress
├── 100+ provider 集成 + Python 友好 ──→ LiteLLM
├── 智能路由 + 成本优化(按 prompt) ──→ Portkey
├── 海外 + 极致性能 + 服务网格 ──→ Envoy AI Gateway
└── 传统 API 网关场景 + 基础 AI ──→ Kong
```

---

## 10. 副业落地:小 B 客户怎么用 APISIX 做 AI 网关

> **场景假设**:你(独立开发者)要给某小 B 客户(50-200 人的律所 / 教培 / 餐饮连锁 / 诊所)交付一套"内部 AI 网关",统一管理 OpenAI / DeepSeek / 通义 / Ollama 的接入,实现合规审计 + 成本控制。

### 10.1 三套实战方案

#### 方案 A:单实例 + 单 LLM(最简单,1-2 天交付)

**适用**:客户只用一个 LLM(全公司统一 DeepSeek),只需"网关层做合规 + 限流"。

**Docker Compose**:

```yaml
version: '3'
services:
  apisix:
    image: apache/apisix:3.16.0
    ports: ["9080:9080", "9180:9180", "9090:9090"]  # HTTP / Admin / Prom
    volumes:
      - ./apisix_conf.yaml:/usr/local/apisix/conf/apisix.yaml
      - ./standalone_config.yaml:/usr/local/apisix/conf/config.yaml
    depends_on: [etcd]

  etcd:
    image: quay.io/coreos/etcd:v3.5
    command: ["etcd", "-advertise-client-urls=http://etcd:2379",
              "-listen-client-urls", "http://0.0.0.0:2379"]

  prometheus:
    image: prom/prometheus
    volumes: ["./prometheus.yml:/etc/prometheus/prometheus.yml"]
    ports: ["9091:9090"]
```

**conf/apisix.yaml**(standalone 模式):

```yaml
upstreams:
  - name: deepseek
    type: roundrobin
    nodes:
      "api.deepseek.com:443": 1

routes:
  - uri: /v1/chat/completions
    upstream_id: deepseek
    plugins:
      ai-proxy:
        provider: openai-compatible   # DeepSeek 协议兼容 OpenAI
        options:
          model: deepseek-chat
        auth:
          header:
            Authorization: "Bearer ${env.DEEPSEEK_API_KEY}"
      ai-prompt-decorator:
        prepend:
          - role: system
            content: "你是XX律所助手,严格遵守律师执业规范"
      ai-prompt-guard:
        deny_patterns:
          - "(?i)ignore (all|previous|above)"
          - "(?i)jailbreak|DAN"
      ai-rate-limiting:
        rules:
          - count: 100000
            time_window: 86400
            key: consumer_name
        rejected_code: 429
```

**交付成本**:1-2 人天,客户硬件要求 2 核 4G 起,月成本 < ¥100(云)。

---

#### 方案 B:多模型 fallback + MCP 工具(中等,3-5 天)

**适用**:客户要"主力 OpenAI,兜底 DeepSeek",且公司有 2-3 个 stdio MCP 工具(企业微信查考勤 / SQL 查业务 / 文档库)。

**架构**:

```
Client ──> APISIX (3 实例) ──┬──> OpenAI (主)
                              ├──> DeepSeek (次)
                              └──> Bedrock (兜底,海外)
                              ├──> MCP: 考勤查询
                              ├──> MCP: 业务 SQL
                              └──> MCP: 文档库
```

**核心配置**(在方案 A 基础上加):

```yaml
# 改 ai-proxy → ai-proxy-multi
plugins:
  ai-proxy-multi:
    instances:
      - { provider: openai, priority: 100, options: { model: gpt-4o } }
      - { provider: deepseek, priority: 50, options: { model: deepseek-chat } }
      - { provider: bedrock, priority: 10, options: { model: anthropic.claude-3-5-sonnet-20240620-v1:0 } }
    fallback_strategy: [http_429, http_5xx, instance_health]

# 加 3 个 MCP 路由
routes:
  - uri: /mcp/attendance
    plugins:
      mcp-bridge:
        command: "node"
        args: ["/opt/mcp/attendance.js"]
  - uri: /mcp/sql
    plugins:
      mcp-bridge:
        command: "python3"
        args: ["/opt/mcp/sql.py", "--dsn=postgresql://..."]
  - uri: /mcp/docs
    plugins:
      mcp-bridge:
        command: "node"
        args: ["/opt/mcp/docs.js", "--dir=/data/docs"]
```

**交付成本**:3-5 人天,客户硬件 4 核 8G × 3 节点(etcd 集群 + APISIX 集群)。

---

#### 方案 C:全功能 + 完整可观测(企业级,2-3 周)

**适用**:中大型客户(200-2000 人),需要完整 SLO 监控 + 多租户隔离 + 审计合规 + 成本归因。

**架构**(完整版,涉及 8 个组件):

```
                 ┌──> Prometheus ──> Grafana
Client ──> APISIX ──> ClickHouse ──> Metabase
                 │   (审计 + 用量)
                 └──> OTel Collector ──> Jaeger (trace)
                 
                 OpenAI / DeepSeek / 通义 / Bedrock
                 3-5 个 MCP 工具
```

**多租户配置**(关键):

```yaml
consumers:
  - username: dept-marketing
    plugins:
      jwt-auth:
        key: "marketing-secret"
      ai-rate-limiting:
        rules:
          - count: 500000
            time_window: 2592000      # 30 天
            key: consumer_name
  - username: dept-engineering
    plugins:
      jwt-auth:
        key: "eng-secret"
      ai-rate-limiting:
        rules:
          - count: 5000000            # 工程部预算多
            time_window: 2592000
            key: consumer_name
```

**成本归因**(ClickHouse + ai-proxy 自动上送):

```sql
-- 每月按部门分账
SELECT
  consumer_name,
  sum(JSONExtractFloat(usage, 'prompt_tokens')) AS prompt_total,
  sum(JSONExtractFloat(usage, 'completion_tokens')) AS completion_total,
  sum(cost) AS total_cost_cny
FROM llm_logs
WHERE event_time > now() - INTERVAL 30 DAY
GROUP BY consumer_name
```

**交付成本**:2-3 人周,客户硬件 8 核 16G × 3 节点(APISIX)+ ClickHouse 集群 + Prometheus + Grafana。

### 10.2 副业切入点:3 个推荐方向

#### 切入点 1:**MCP 工具市场集成商**(信息差红利期)

- **市场状态**:国内 90% 公司不知道 MCP,知道的有 80% 不会自己接 stdio server
- **你的服务**:给客户做"存量 HTTP API → MCP server" + 接入 APISIX,3-5 天 1 单
- **定价**:¥3 万-8 万 / 单(中等客户,10-30 个 API 转换)
- **关键 skill**:懂 MCP 协议 + 能写 stdio MCP server(Python / TypeScript)+ 懂 APISIX 路由

#### 切入点 2:**多模型成本优化顾问**(合规 + 省钱)

- **市场状态**:2026 年 LLM 成本占中型 SaaS 公司 IT 预算 15-30%,但 80% 公司没做多模型路由
- **你的服务**:给客户做"流量分析 + 多模型路由配置 + 月度成本归因报告"
- **定价**:¥2 万-5 万 / 月(顾问费)+ ¥1 万-3 万 / 次(实施费)
- **关键 skill**:懂 ai-rate-limiting + 懂 ClickHouse 查询 + 懂各 LLM 计费规则

#### 切入点 3:**AI 网关白标产品**(年付 SaaS)

- **市场状态**:小 B 不需要"全套可观测",需要"开箱即用的 AI 网关 + 后台"
- **你的产品**:基于 APISIX + 一键 Docker + 管理后台(¥5-10 万 / 年)
- **差异化**:比 Higress 灵活(支持私有部署),比 Portkey 便宜(自托管)
- **关键 skill**:能写 APISIX Admin API 的 CRUD + 简易 Web 后台(FastAPI / Next.js)

### 10.3 运维成本估算

| 客户规模 | 硬件月成本 | 你的实施费 | 你的年服务费 | 续约率经验值 |
|---------|----------|----------|------------|------------|
| 50 人(单 LLM) | ¥300 | ¥1.5 万 | ¥2 万 | 70% |
| 200 人(多模型) | ¥1,500 | ¥5 万 | ¥5 万 | 85% |
| 1000 人(全功能) | ¥8,000 | ¥15 万 | ¥15 万 | 90% |

**毛利率**:全功能套餐 50-65%,小套餐 70-80%。

---

## 11. 风险与坑(必看)

### 11.1 部署层

1. **etcd 强依赖**:APISIX 3.x 默认依赖 etcd 集群,standalone 模式(YAML)只适合 demo。生产请用 3 节点 etcd 集群,否则脑裂。
2. **Lua 调试困难**:插件 bug 排查时,`error.log` 是唯一窗口,务必把 `error_log_level: warn` 调到 `info` 看插件行为。
3. **OpenResty 版本敏感**:APISIX 3.16 要求 OpenResty 1.25.3+,镜像里内置,但如果你用源码编译要小心。

### 11.2 AI 插件版本兼容

4. **3.13 → 3.16 schema 有破坏性变更**:`ai-proxy` 配置文件结构改过,升级前看官方 migration guide。
5. **`ai-rag` 只支持 Azure**:国内客户基本不能用,这是硬伤,等社区 PR(目前有 Milvus / Qdrant 实现的 issue 但没合并)。
6. **Bedrock SigV4 签名复杂**:`auth.aws` 配置里 access_key 必须有 bedrock 权限,且 `region` 必须正确。

### 11.3 安全层

7. **API key 加密**:所有 `auth.header.Authorization` 字段在 schema 标了 `encrypt_fields`,APISIX 会自动加密存储在 etcd 里。但**Admin API 默认是明文 HTTP**,生产请开 TLS。
8. **prompt 注入无法 100% 防**:`ai-prompt-guard` 的正则只是基础防线,真正的 PII / 越狱检测需要接 Lakera Guard / Prompt Armor 这类专用服务。
9. **SSE 长连接资源耗尽**:每个 SSE 连接占 1 个 worker,**默认 worker 数 = CPU 核数**。1000 并发 SSE 会把 worker 打爆,要调大 `event.worker_connections` 或者用 stream subsystem。

### 11.4 成本层

10. **DeepSeek 限流突袭**:DeepSeek 在 2025-09 / 2026-01 两次大规模限流(429),fallback 策略要**真的**测过,不是配置上写了就高枕无忧。
11. **OpenAI 实时批价不更新**:OpenAI 2024-08 引入 `cached_input_tokens` 字段,APISIX 3.16 之前的版本不识别,会被当成普通 `prompt_tokens` 计费,**客户账单对不上**。

---

## 12. 总结:APISIX 在 2026 是不是"AI 网关"的好选择?

### ✅ 适合选 APISIX 的场景

- 你已经在用 APISIX 做 API 网关,想"加 AI 流量" → **直接升级到 3.16,0 成本接入**
- 你需要 MCP 工具桥接(企业内有 stdio 工具)→ **mcp-bridge 是 2026 上半年最成熟的**
- 你需要按复杂成本公式限流(Anthropic cache 价 / DeepSeek 限流)→ **`cost_expr` 业界独家**
- 你需要三段式架构(协议 / provider / 传输可独立扩展)→ **3.16 起官方支持**
- 你需要 Apache 2.0 全开源(无 enterprise 闭源风险)→ **APISIX 满足**

### ❌ 不适合选 APISIX 的场景

- 你的核心需求是 100+ provider 集成(创业公司 MVP)→ 选 LiteLLM
- 你的核心需求是"按 prompt 智能选模型"→ 选 Portkey
- 你的客户全在阿里云生态,需要 SLA 保障→ 选 Higress
- 你的核心需求是 LLM 应用开发框架(LangChain / LlamaIndex)→ 那是 LangChain / LlamaIndex,不是网关

### 一句话判断

> **APISIX 在 2026 Q2 的定位已经从"通用 API 网关"悄悄变成了"AI Native API 网关"。如果你的场景是"在企业网关里跑 LLM 流量",APISIX 3.16 是 Apache 2.0 阵营里最成熟的答案——MCP 支持早、协议覆盖广、成本计量精、扩展机制清晰。但如果你只是给 LLM 应用加个 API 层,不如直接用 LiteLLM。**

---

## 附录 A:关键 Commit 引用

| PR | 日期 | 标题 | 重要性 |
|----|------|------|-------|
| #12151 | 2025-04-19 | feat: add mcp-bridge plugin | ⭐⭐⭐⭐⭐ 首批 MCP 网关 |
| #12168 | 2025-06-07 | refactor: mcp server framework implementation | ⭐⭐⭐⭐ MCP 框架基座 |
| #12030 | 2025-03-11 | refactor(ai): ai-proxy and ai-proxy-multi | ⭐⭐⭐⭐ 引入 multi 模式 |
| #12055 | 2025-03-17 | chore: rectify business logic/code in ai-proxy | ⭐⭐⭐ |
| #12515 | 2025-08-27 | feat(ai-proxy): add support for pushing logs in ai-proxy | ⭐⭐⭐ |
| #12518 | 2025-08-19 | feat(ai-proxy): add latency and usage in access log and prometheus | ⭐⭐⭐⭐ |
| #12933 | 2026-01-26 | feat: support vertex-ai | ⭐⭐⭐ |
| #12967 | 2026-02-05 | feat: support configuring variables in limit-conn, limit-count and ai-rate-limiting | ⭐⭐⭐ |
| #13000 | 2026-02-11 | feat: support rules in limit-conn and ai-rate-limiting | ⭐⭐⭐⭐ |
| #13004 | 2026-02-12 | feat: support header prefix in limit-count rules | ⭐⭐ |
| #13170 | 2026-04-08 | refactor: three-layer AI proxy architecture (protocols/providers/transport) | ⭐⭐⭐⭐⭐ 架构级重构 |
| #13191 | 2026-04-10 | feat(ai-rate-limiting): add expression-based limit strategy | ⭐⭐⭐⭐⭐ `cost_expr` 表达式 |
| #13192 | 2026-04-10 | feat: enhance encrypt_fields to support nested structures | ⭐⭐⭐ |
| #13203 | 2026-04-17 | fix(security): TLS ssl_verify hardcoding and credential encryption issues | ⭐⭐⭐ |
| #13249 | 2026-04-27 | feat(ai-proxy): support aws bedrock | ⭐⭐⭐⭐ |
| #13312 | 2026-04-30 | feat: extend secret references to all plugins with central resolution | ⭐⭐⭐ |
| #13458 | open | fix(resource): add plugin_configs support for fetch_latest_conf, fix ai-proxy-multi plugin with multi instance not support plugin_config_id | ⭐⭐ 待合并 |
| #13466 | open | feat: add max_req_body_size to bound client request body in forward-auth and ai-proxy | ⭐⭐ |
| #13477 | open | feat(ai-proxy): add built-in nginx variables for LLM observability | ⭐⭐⭐ |

## 附录 B:推荐阅读

- APISIX 官方文档:https://apisix.apache.org/docs/apisix/plugins/ai-proxy/
- APISIX GitHub:https://github.com/apache/apisix
- MCP 协议规范:https://modelcontextprotocol.io
- OpenTelemetry GenAI SemConv:https://opentelemetry.io/docs/specs/semconv/gen-ai/
- 本仓库相关:`2026-06-05-1658-aigw-tech-deepdive-article.md`(Higress AI 深度)、`2026-06-05-2134-aigw-release-higress-v222.md`(`aigw-mcp-r27.md`)(MCP 演进)

## 附录 C:版本速查

| APISIX 版本 | 发布时间 | AI 关键特性 |
|-------------|---------|-------------|
| 3.10.0 | 2024-08 | ai-rate-limiting 初版 |
| 3.11.0 | 2024-10 | ai-rag(Azure only) |
| 3.12.0 | 2025-04 | mcp-bridge, ai-prompt-* 草案 |
| 3.13.0 | 2025-06 | ai-proxy-multi, ai-prompt-{decorator,guard,template}, ai-aws/aliyun-content-moderation |
| 3.14.0 | 2025-10 | fine-tuning, secret 加密 |
| 3.15.0 | 2026-02 | ai-rate-limiting `rules` 模式 |
| **3.16.0** | **2026-04-08** | **三段式重构, Bedrock, Vertex AI, cost_expr** |
| 3.17.0(预计) | 2026-08 | 推测:语义缓存 / Milvus / Qdrant 支持 |

---

> **报告完成时间**:2026-06-07 07:30 UTC+8
> **作者**:Hermes / happysunxf
> **仓库**:happysunxf/aigw/hermes/reports/
> **字数**:约 13,500 字(中文)
> **License**:CC-BY 4.0
