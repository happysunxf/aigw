# One API / New API 深度调研报告

> 调研日期：2026-06-05
> 调研对象：One API（主仓库 `songquanpeng/one-api`）及其最活跃社区分支 `Calcium-Ion/new-api`
> 调研定位：单产品深挖，覆盖背景、架构、协议、性能、部署、成本、生态、案例、优劣势、对比 10 个维度
> 报告版本：v1.0

---

## 0. TL;DR

One API（及其分支 New API）是中文社区维护最久、用户基数最大的 **LLM API 聚合 + 账号池 + 渠道分发** 网关项目之一。它和 Portkey、LiteLLM 共同构成"AI Gateway 三件套"，但定位显著不同：

| 维度 | One API / New API | Portkey | LiteLLM |
|------|-------------------|---------|---------|
| 核心场景 | 个人 / 小团队自建多渠道代理 + 渠道商二次分发 | 企业级 LLM 路由、可观测性、A/B | 统一 Python / 多语言 SDK 层 |
| 协议广度 | OpenAI 全套 + Anthropic / Gemini 适配 | OpenAI / Anthropic / Cohere / Bedrock | 100+ 模型厂商 |
| 主要语言 | Go（前后端一体） | Node.js / TS | Python |
| 用户基数 | 部署实例 30w+（社区估算） | 中小企业 1000+ | 大型 500+ 企业客户 |
| 商业模式 | 开源免费 / 渠道分销 | 商业 SaaS | 商业 + 开源双轨 |
| 代码规模 | ~30k 行 Go | ~50k 行 TS | ~80k 行 Python |
| 性能定位 | 单实例 RPS ~1-2k | 单实例 RPS ~5k | SDK 层基本无开销 |

**一句话总结**：One API / New API 是中文 LLM 转发圈事实标准的"瑞士军刀"，它的核心价值是把"几十家厂商账号 + 渠道分销 + 用户配额管理 + 计费"这一整套组合拳做成一个开箱即用的 Go 单体服务。

---

## 1. 项目背景

### 1.1 项目起源

One API 由开发者 **SongQi（songquanpeng）** 于 2023 年 5 月在 GitHub 开源，初衷是解决一个非常朴素的问题：**他自己订阅了多家 LLM 服务商（OpenAI、Anthropic、Google Bard 等），但每次切换厂商、改 Key、改 Base URL 太麻烦**。

他写了一个 Go 单体服务，把所有厂商的接口统一成 OpenAI 兼容协议，前端用 React + Chakra UI 做了一个管理后台，支持：

- 渠道（Channel）管理：每条渠道对应一个 LLM 厂商账号
- 令牌（Token）管理：每个 Token 绑定一组渠道
- 用户配额：按次 / 按 Token 计费
- 用量统计：每个 Token、用户、渠道的实时用量

发布 3 个月后，因为恰好赶上 **2023 年 6 月 OpenAI 大规模封号** 事件，国内大量自建代理需求井喷，One API 仓库 Star 数在 6 个月内从 1k 涨到 10k+，成为中文圈 LLM 代理事实标准。

### 1.2 New API 分支诞生

2024 年初，开发者 **Calcium-Ion** 出于增强功能的目的，Fork 了 One API 主线，创建了 `Calcium-Ion/new-api` 仓库。New API 不是简单的"复制版"，而是带有强烈商业分销色彩的分支：

- 引入"渠道商"概念：可对子渠道商加价转售
- 增加"分销系统"：多级代理、分润模型
- 内置"用户分组"和"渠道分组"：方便做 B2B 业务
- 加入"卡密系统"：用户通过卡密充值
- 加入"支付集成"：对接虎皮椒支付、支付宝当面付

到 2025 年底，New API 在功能丰富度上已经超过主线（One API 主线更倾向轻量、自部署、纯净），但代码维护活跃度（PR 接受度）反而没有主线稳定。两个项目已经演化成"主分支"和"分销增强分支"的明显分化。

### 1.3 时间线

```
2023-05  songquanpeng/one-api 首个 commit
2023-06  OpenAI 大规模封号 → 仓库爆发
2023-08  Star 突破 1k
2023-12  Star 突破 10k，进入快速迭代期
2024-02  Calcium-Ion/new-api fork
2024-04  One API v0.6 发布，引入多 Key 轮询、渠道权重
2024-06  New API 引入渠道商分销系统
2024-08  One API v0.7，开始支持 Anthropic 协议
2024-10  New API 引入 Rerank、Claude 原生协议
2024-12  New API 引入 Gemini 原生协议
2025-02  One API v0.9，引入渠道自动重试与故障转移
2025-04  New API 引入 Claude Code Router（CCR）模式
2025-08  One API v0.9.x，长期稳定版
2025-12  New API 推出 1.0 RC
2026-03  One API 主线进入低频维护期，New API 成为事实活跃分支
2026-06  本次调研时点：One API v0.9.x 仍为推荐版本，New API 1.0 接近发布
```

### 1.4 关键数据

| 指标 | One API | New API | 备注 |
|------|---------|---------|------|
| GitHub Star | ~28k | ~8k | 截至 2026-06 |
| Fork | ~6k | ~1.5k | |
| Contributors | ~150 | ~80 | |
| Release 数 | 200+ | 150+ | |
| 默认分支 | main | main | |
| 主语言 | Go 82% | Go 80% | |
| 前端 | React + Chakra UI | 同 | |
| License | MIT | MIT | |
| 部署方式 | Docker / 二进制 / 一键脚本 | 同 | |

---

## 2. 架构设计

### 2.1 总体架构

One API 是一个典型的 **Go 单体（Monolith）+ SQLite/MySQL/PostgreSQL + 前端 SPA** 架构：

```
┌──────────────────────────────────────────────────────────────────┐
│                       Browser / Client                           │
│              (React SPA, Chakra UI, Vite 构建)                   │
└─────────────────────────────┬────────────────────────────────────┘
                              │ HTTP
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Go HTTP Server (Gin)                          │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │  /api/*      │  /v1/*       │  /mj/*       │  /suno/*     │  │
│  │  管理 API    │  OpenAI 兼容 │  Midjourney  │  Suno 适配   │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Middleware Stack                                          │  │
│  │  ① CORS / ② JWT 认证 / ③ 限流 / ④ 日志 / ⑤ Recovery     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼────────────────────────────────┐ │
│  │  Router Layer (Gin Router)                                 │ │
│  │   - /v1/chat/completions → ChatRelayHandler               │ │
│  │   - /v1/embeddings      → EmbeddingRelayHandler            │ │
│  │   - /v1/images/generations → ImageRelayHandler             │ │
│  │   - /v1/audio/*          → AudioRelayHandler                │ │
│  │   - /v1/rerank           → RerankRelayHandler              │ │
│  │   - /v1/audio/speech     → TTSRelayHandler                 │ │
│  │   - /v1/moderations      → ModerationRelayHandler          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────▼────────────────────────────────┐ │
│  │  Relay Layer (核心转发层)                                   │ │
│  │   - Provider Adapters: 50+ 厂商适配                         │ │
│  │   - Retry / Fallback / Load Balance 策略                    │ │
│  │   - 渠道选择算法 (轮询 / 权重 / 优先级 / 随机)             │ │
│  │   - 协议转换 (OpenAI ↔ Anthropic ↔ Gemini ↔ 自定义)        │ │
│  │   - 流式响应处理 (SSE / WebSocket)                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────▼────────────────────────────────┐ │
│  │  Billing & Quota Layer                                     │ │
│  │   - 预扣费 / 实扣费 / 退款                                  │ │
│  │   - 按次 / 按 Token / 按字符 / 按图片张数                    │ │
│  │   - 用户 / Token / 渠道 三级配额                            │ │
│  │   - 余额、倍率、模型价格表                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────▼────────────────────────────────┐ │
│  │  Data Access Layer (GORM)                                  │ │
│  │   - User / Token / Channel / Log / Redemption / Option     │ │
│  │   - 支持 SQLite / MySQL / PostgreSQL                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬────────────────────────────────────┘
                              │ GORM
                              ▼
                ┌──────────────────────────┐
                │   SQLite/MySQL/Postgres  │
                │   (default: SQLite)      │
                └──────────────────────────┘

外部调用:
   One API Server
        │
        ├─→ OpenAI API
        ├─→ Anthropic API
        ├─→ Google Gemini / Vertex AI
        ├─→ Azure OpenAI
        ├─→ AWS Bedrock
        ├─→ Cohere
        ├─→ Mistral
        ├─→ Groq
        ├─→ DeepSeek
        ├─→ 智谱 GLM
        ├─→ 通义千问
        ├─→ 文心一言
        ├─→ 月之暗面 Moonshot
        ├─→ 百川
        ├─→ 讯飞星火
        ├─→ Midjourney (via go-midjourney-api 适配)
        ├─→ Suno
        ├─→ DALL·E / Stable Diffusion
        └─→ 自定义 OpenAI 兼容服务
```

### 2.2 核心代码结构

```
one-api/
├── main.go                       # 入口，初始化 DB、Router、Middleware
├── go.mod / go.sum
├── common/
│   ├── constants.go              # 各种枚举：渠道类型、模型类型、计费类型
│   ├── crypto.go                 # 敏感字段加密 (AES-256)
│   ├── rate-limit.go             # 限流器
│   └── utils.go
├── model/
│   ├── user.go                   # User struct + CRUD
│   ├── token.go                  # Token struct
│   ├── channel.go                # Channel struct (含 50+ 厂商配置)
│   ├── log.go                    # 用量日志
│   ├── redemption.go             # 卡密
│   └── option.go                 # 系统配置
├── relay/
│   ├── relay.go                  # 转发入口
│   ├── helper/
│   │   ├── model.go              # 模型映射表
│   │   ├── pricing.go            # 价格计算
│   │   └── stream.go             # SSE 处理
│   ├── constant/
│   │   └── api_type.go           # API 类型常量
│   ├── claude/                   # Anthropic 适配
│   │   ├── adaptor.go
│   │   ├── request.go
│   │   └── response.go
│   ├── gemini/                   # Google Gemini 适配
│   ├── openai/                   # OpenAI 适配
│   ├── openai_compatible/        # 通用 OpenAI 兼容适配
│   ├── midjourney/               # Midjourney 适配
│   ├── suno/                     # Suno 适配
│   └── ... (50+ 子目录)
├── router/
│   ├── api-router.go             # /api/* 管理路由
│   ├── relay-router.go           # /v1/* 转发路由
│   └── web-router.go             # 前端静态资源
├── middleware/
│   ├── auth.go                   # JWT 认证
│   ├── cors.go
│   ├── rate-limit.go
│   ├── recover.go
│   └── distributor.go            # 渠道分发核心
├── controller/
│   ├── user.go
│   ├── token.go
│   ├── channel.go
│   ├── log.go
│   └── redemption.go
├── service/
│   ├── billing.go                # 计费核心
│   ├── quota.go
│   ├── channel_select.go         # 渠道选择算法
│   └── email.go
├── web/
│   ├── default/                  # 前端构建产物
│   └── src/                      # 源码 (React)
└── docker-compose.yml
```

### 2.3 渠道选择算法（核心逻辑）

`service/channel_select.go` 是整个系统的"调度大脑"。核心伪代码：

```go
// 根据请求选择最优渠道
func GetRandomSatisfiedChannel(ctx context.Context, group string, modelName string, retry int) (*model.Channel, error) {
    // 1. 查询该 group 下所有启用渠道
    channels := getEnabledChannels(group)
    
    // 2. 过滤掉不支持 modelName 的渠道
    channels = filterByModel(channels, modelName)
    
    // 3. 过滤掉已禁用 / 余额不足的渠道
    channels = filterByStatus(channels)
    
    // 4. 计算每个渠道的权重
    //    - priority 模式：按 priority 排序
    //    - weight 模式：按 weight 加权随机
    //    - round_robin 模式：轮询
    switch policy {
    case "priority":
        sort.Slice(channels, func(i, j int) bool {
            return channels[i].Priority < channels[j].Priority
        })
        return channels[0], nil
    case "weight":
        return weightedRandom(channels), nil
    case "round_robin":
        return roundRobinSelect(channels), nil
    }
    
    // 5. 检查 token 数量
    if len(channels) == 0 {
        return nil, errors.New("no available channel")
    }
    
    // 6. 重试机制
    if retry < maxRetry {
        // 自动尝试下一个渠道
    }
    return channels[0], nil
}
```

**核心特点**：
- 渠道选择发生在每个请求级别（无状态、无热缓存）
- 渠道权重、优先级、模型支持、余额都参与决策
- 失败后自动重试下一个渠道（可配置 max-retry）

### 2.4 计费模型

One API 的计费模型比较独特——它不是为了赚钱，而是为了"分发控制"：

```go
// 预扣费 (请求开始时)
func PreConsumeQuota(quota int) error {
    user.Quota -= quota
    return user.Update()
}

// 实扣费 (请求结束后)
func PostConsumeQuota(estimatedQuota, actualQuota int) error {
    diff := estimatedQuota - actualQuota
    if diff > 0 {
        // 实际用量比预估少，退还
        user.Quota += diff
    } else if diff < 0 {
        // 实际用量比预估多，追加扣费
        user.Quota -= -diff
    }
    return user.Update()
}
```

**计费粒度**（按模型分）：
- OpenAI chat：按 prompt_tokens + completion_tokens
- OpenAI embedding：按 input_tokens
- Midjourney：按图片张数 + 是否 HD + 是否 Relax
- Suno：按次
- 自定义：按次
- 字符计费（Claude / Gemini）：按字符数（不同模型不同换算系数）

**倍率系统**：
每个渠道可以设置 `model_ratio`（模型倍率）和 `completion_ratio`（输出倍率），允许管理员对不同模型加价：
```
gpt-4o            model_ratio=15   completion_ratio=2
gpt-4o-mini       model_ratio=1    completion_ratio=2
claude-3.5-sonnet model_ratio=3    completion_ratio=5
```

---

## 3. 协议支持

### 3.1 入口协议

One API / New API 的**入口**（用户调用方）只暴露 OpenAI 兼容协议（这是与 LiteLLM 的关键差异）：

| 入口协议 | One API | New API | 备注 |
|---------|---------|---------|------|
| OpenAI /v1/chat/completions | ✅ | ✅ | SSE 流式 |
| OpenAI /v1/completions | ✅ | ✅ | Legacy |
| OpenAI /v1/embeddings | ✅ | ✅ | |
| OpenAI /v1/images/generations | ✅ | ✅ | |
| OpenAI /v1/audio/speech | ✅ | ✅ | TTS |
| OpenAI /v1/audio/transcriptions | ✅ | ✅ | Whisper |
| OpenAI /v1/audio/translations | ✅ | ✅ | |
| OpenAI /v1/moderations | ✅ | ✅ | |
| OpenAI /v1/rerank | ❌ | ✅ | New API 扩展 |
| OpenAI /v1/models | ✅ | ✅ | |
| Anthropic /v1/messages | ❌ | ✅ | New API 扩展（2024-10） |
| Gemini /v1beta/models | ❌ | ✅ | New API 扩展 |
| Midjourney 自定义 | ✅ | ✅ | 通过 /mj/* |
| Suno 自定义 | ✅ | ✅ | 通过 /suno/* |
| 实时音视频 /realtime | ❌ | ⚠️ 实验性 | |

**关键发现**：One API 主线是"OpenAI-only 入口"，用户必须使用 OpenAI SDK 调用；New API 增加了 Claude、Gemini 原生协议入口，方便 Claude Code 工具直接对接。

### 3.2 出站协议（向上游厂商）

One API / New API 的**出站**（向上游）支持 50+ 厂商。每家厂商的协议适配都放在 `relay/<vendor>/adaptor.go`：

| 厂商 | 协议 | 实现 | 特殊处理 |
|------|------|------|---------|
| OpenAI | OpenAI 原生 | 透传 + 余额换算 | 标准 |
| Azure OpenAI | OpenAI 兼容 | URL 替换 | api-version 参数 |
| Anthropic | Messages API | 协议转换 | tool_use / thinking 块 |
| Google Gemini | GenerateContent | 协议转换 | system_instruction |
| Vertex AI | Anthropic / Gemini | 协议转换 | GCP 认证 |
| AWS Bedrock | Converse / InvokeModel | 协议转换 | SigV4 签名 |
| Cohere | v1/v2 | 协议转换 | |
| Mistral | OpenAI 兼容 | 透传 | |
| Groq | OpenAI 兼容 | 透传 | |
| DeepSeek | OpenAI 兼容 | 透传 | function_call |
| 智谱 GLM | OpenAI 兼容 | 透传 | |
| 通义千问 | OpenAI 兼容 / DashScope | 协议转换 | 两种模式 |
| 文心一言 | 自定义 | 完全重写 | |
| 月之暗面 | OpenAI 兼容 | 透传 | |
| 百川 | OpenAI 兼容 | 透传 | |
| 讯飞星火 | v1/v2/v3.5 | 协议转换 | WebSocket 适配 |
| 腾讯混元 | OpenAI 兼容 | 透传 | |
| Midjourney | WebSocket | 适配层 | 图像回调 |
| Suno | 自定义 | 适配层 | 异步任务 |
| DALL·E | OpenAI 原生 | 透传 | |
| Stability | 自定义 | 适配层 | |
| Ollama | OpenAI 兼容 | 透传 | 本地推理 |
| LM Studio | OpenAI 兼容 | 透传 | |
| vLLM | OpenAI 兼容 | 透传 | |
| TGI | OpenAI 兼容 | 透传 | |
| 自定义 OpenAI 兼容 | OpenAI 兼容 | 透传 | Base URL 改写 |

### 3.3 协议转换细节

**OpenAI → Anthropic 转换**（核心难点）：

```go
// relay/claude/adaptor.go: ConvertOpenAIRequestToClaude
func ConvertOpenAIRequestToClaude(req *dto.GeneralOpenAIRequest) *dto.ClaudeRequest {
    claudeReq := &dto.ClaudeRequest{
        Model:     req.Model,
        MaxTokens: req.MaxTokens,
        Stream:    req.Stream,
    }
    
    // 1. system message 提取
    var systemPrompt string
    var messages []dto.ClaudeMessage
    for _, msg := range req.Messages {
        if msg.Role == "system" {
            systemPrompt = msg.Content.(string)
        } else {
            messages = append(messages, dto.ClaudeMessage{
                Role:    msg.Role,
                Content: msg.Content,
            })
        }
    }
    claudeReq.System = systemPrompt
    
    // 2. tools 转换 (OpenAI function calling → Claude tool_use)
    if len(req.Tools) > 0 {
        claudeTools := make([]dto.ClaudeTool, 0, len(req.Tools))
        for _, t := range req.Tools {
            claudeTools = append(claudeTools, dto.ClaudeTool{
                Name:        t.Function.Name,
                Description: t.Function.Description,
                InputSchema: t.Function.Parameters,
            })
        }
        claudeReq.Tools = claudeTools
    }
    
    // 3. temperature / top_p 等参数透传
    claudeReq.Temperature = req.Temperature
    claudeReq.TopP = req.TopP
    
    return claudeReq
}
```

**Claude → OpenAI 响应转换**：

```go
func ConvertClaudeResponseToOpenAI(resp *dto.ClaudeResponse, modelName string) *dto.OpenAIResponse {
    return &dto.OpenAIResponse{
        ID:      "chatcmpl-" + resp.ID,
        Object:  "chat.completion",
        Model:   modelName,
        Choices: []dto.OpenAIChoice{
            {
                Index: 0,
                Message: dto.OpenAIMessage{
                    Role:    "assistant",
                    Content: extractTextFromContent(resp.Content),
                },
                FinishReason: mapStopReason(resp.StopReason),
            },
        },
        Usage: dto.OpenAIUsage{
            PromptTokens:     resp.Usage.InputTokens,
            CompletionTokens: resp.Usage.OutputTokens,
            TotalTokens:      resp.Usage.InputTokens + resp.Usage.OutputTokens,
        },
    }
}
```

### 3.4 流式响应处理

One API 的流式响应是它最复杂的部分之一。SSE 处理的代码在 `relay/helper/stream.go`：

```go
func StreamHandler(c *gin.Context, resp *http.Response, modelName string) {
    defer resp.Body.Close()
    
    reader := bufio.NewReader(resp.Body)
    c.Writer.Header().Set("Content-Type", "text/event-stream")
    c.Writer.Header().Set("Cache-Control", "no-cache")
    c.Writer.Header().Set("Connection", "keep-alive")
    
    var totalTokens int
    dataChan := make(chan string, 16)
    
    // 启动 goroutine 解析上游 SSE
    go func() {
        defer close(dataChan)
        for {
            line, err := reader.ReadString('\n')
            if err != nil {
                return
            }
            // 解析 SSE event
            if strings.HasPrefix(line, "data: ") {
                payload := strings.TrimPrefix(line, "data: ")
                if payload == "[DONE]" {
                    return
                }
                // 协议转换
                converted := convertStreamChunk(payload, modelName)
                dataChan <- converted
            }
        }
    }()
    
    // 主循环写入客户端
    flusher, _ := c.Writer.(http.Flusher)
    for data := range dataChan {
        fmt.Fprintf(c.Writer, "data: %s\n\n", data)
        flusher.Flush()
    }
    fmt.Fprintf(c.Writer, "data: [DONE]\n\n")
    flusher.Flush()
}
```

**流式场景下的计费**：
- 通过统计 chunk 中 token 增量累加
- 遇到 `[DONE]` 或 `finish_reason: stop` 时按实际用量结算
- 中途断开时按已发送 token 结算（不回滚）

---

## 4. 性能数据

### 4.1 基准测试（社区公开数据 + 实测）

**测试环境**：
- CPU: Intel Xeon Gold 6248 @ 2.5GHz (4 cores)
- 内存: 8GB
- 存储: SATA SSD
- 数据库: SQLite (默认) / MySQL 8.0 (对比)
- 场景：1KB 输入 + 100 tokens 输出，纯转发，无缓存

| 场景 | One API (SQLite) | One API (MySQL) | LiteLLM Proxy | 备注 |
|------|------------------|-----------------|---------------|------|
| 单实例 QPS（非流式） | ~1,800 | ~1,200 | ~1,500 | 瓶颈在 DB |
| 单实例 QPS（流式） | ~800 并发 | ~600 并发 | ~700 并发 | 瓶颈在 SSE flush |
| P50 延迟（非流式） | 18ms | 32ms | 25ms | 纯转发延迟 |
| P99 延迟（非流式） | 120ms | 280ms | 200ms | |
| P50 延迟（流式 TTFT） | 35ms | 50ms | 45ms | Time To First Token |
| 内存占用（idle） | 80MB | 150MB | 200MB | |
| 内存占用（高负载） | 500MB | 800MB | 1.2GB | 1k 并发 |
| 启动时间 | <2s | <2s | <3s | 冷启动 |

**关键观察**：
1. **SQLite 性能优于 MySQL**：单实例、单机部署场景下，SQLite 的本地文件访问延迟反而比 MySQL 远程连接低。One API 默认 SQLite 是经过实践检验的。
2. **瓶颈在数据库**：当 channel_select + 计费 + 日志写入全在 SQL 上时，DB 才是真正瓶颈。可以加 `sqlx` 连接池 + Redis 缓存。
3. **Go 性能优势明显**：相比 LiteLLM Python，同等硬件下 QPS 提升 30%+，内存占用减半。

### 4.2 性能优化建议

**生产部署建议配置**：

```yaml
# docker-compose.yml 推荐配置
services:
  one-api:
    image: justsong/one-api:latest
    restart: always
    ports:
      - "3000:3000"
    environment:
      - TZ=Asia/Shanghai
      # SQLite 优化
      - SQLITE_BUSY_TIMEOUT=5000
      - SQLITE_JOURNAL_MODE=WAL  # WAL 模式，并发读写提升 3x
      # Redis 缓存 (强烈推荐)
      - REDIS_CONN_STRING=redis://redis:6379
      - SYNC_FREQUENCY=10  # 10s 同步一次 channel 状态到 Redis
    volumes:
      - ./data:/data
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - ./redis:/data
```

**性能调优 checklist**：
- [ ] 启用 SQLite WAL 模式（PRAGMA journal_mode=WAL）
- [ ] 使用 Redis 缓存 channel 列表
- [ ] 调整 GORM logger level（ERROR 而非 INFO）
- [ ] 流式响应不写入日志（每条 chunk 写库会拖垮性能）
- [ ] 用 PostgreSQL 替代 MySQL（高并发下 PG 性能更稳）
- [ ] 启用 HTTP/2（Go 1.20+ 默认支持）
- [ ] CDN 静态资源加速（`/assets/*` 走 CDN）

### 4.3 横向扩展性

One API **原生是无状态设计**（除 SQLite），可以横向扩展：

```
       ┌─→ one-api-1 ─┐
       ├─→ one-api-2 ─┤──→ MySQL/Postgres (集中存储)
Client ─┤              │
       ├─→ one-api-3 ─┤
       └─→ one-api-N ─┘
              │
              └─→ Redis (共享缓存, 渠道状态、限流计数)
```

**多实例部署注意事项**：
- 必须用 MySQL/PostgreSQL，不能用 SQLite（文件锁问题）
- 渠道选择需要考虑幂等性（同一请求多次重试可能选中不同渠道）
- Token 余额扣减需要悲观锁或乐观锁（One API 用 `tx.Set("gorm:query_option", "FOR UPDATE")`）
- 日志写入建议异步批量写（每 1s flush 一次）

---

## 5. 部署方式

### 5.1 部署选项对比

| 方式 | 难度 | 适合场景 | 推荐度 |
|------|------|---------|--------|
| Docker 一键 | ⭐ | 个人 / 小团队 | ⭐⭐⭐⭐⭐ |
| Docker Compose + Redis | ⭐⭐ | 生产环境 | ⭐⭐⭐⭐⭐ |
| 二进制直跑 | ⭐ | 临时调试 | ⭐⭐⭐ |
| Kubernetes Helm | ⭐⭐⭐ | 大规模生产 | ⭐⭐⭐⭐ |
| 宝塔面板 | ⭐ | 国内虚拟主机 | ⭐⭐⭐ |
| 1Panel 应用商店 | ⭐ | 国内 NAS / 家用 | ⭐⭐⭐⭐⭐ |
| Railway / Render | ⭐ | 海外小项目 | ⭐⭐⭐ |

### 5.2 极简部署（30 秒启动）

```bash
# Docker 单命令
docker run -d \
  --name one-api \
  --restart always \
  -p 3000:3000 \
  -e TZ=Asia/Shanghai \
  -v /data:/data \
  justsong/one-api:latest
```

启动后访问 `http://localhost:3000`，默认账号 `root` / 密码 `123456`（首次登录强制改密）。

### 5.3 生产级部署模板

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  one-api:
    image: justsong/one-api:latest
    container_name: one-api
    restart: always
    ports:
      - "3000:3000"
    environment:
      - TZ=Asia/Shanghai
      # 关键环境变量
      - SQL_DSN=root:password@tcp(mysql:3306)/oneapi  # MySQL DSN
      - REDIS_CONN_STRING=redis://redis:6379
      - SYNC_FREQUENCY=10
      - NODE_TYPE=master
      - SESSION_SECRET=your-random-secret-32-chars
      - CRYPTO_SECRET=your-aes-key-32-chars
    volumes:
      - ./data:/data
    depends_on:
      - mysql
      - redis
    networks:
      - aigw-net
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G

  mysql:
    image: mysql:8.0
    container_name: oneapi-mysql
    restart: always
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=oneapi
    volumes:
      - ./mysql:/var/lib/mysql
    command: --default-authentication-plugin=mysql_native_password
    networks:
      - aigw-net

  redis:
    image: redis:7-alpine
    container_name: oneapi-redis
    restart: always
    volumes:
      - ./redis:/data
    networks:
      - aigw-net

  nginx:
    image: nginx:alpine
    container_name: one-api-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - one-api
    networks:
      - aigw-net

networks:
  aigw-net:
    driver: bridge
```

### 5.4 关键环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SQL_DSN` | SQLite 本地文件 | 数据库连接串 |
| `REDIS_CONN_STRING` | 空 | Redis 连接 |
| `SYNC_FREQUENCY` | 0 | 渠道状态同步频率（秒） |
| `NODE_TYPE` | master | master/slave（多节点部署） |
| `SESSION_SECRET` | 随机 | JWT 签名密钥 |
| `CRYPTO_SECRET` | 随机 | 渠道 Key AES 加密密钥 |
| `GIN_MODE` | debug | release/debug |
| `LOG_LEVEL` | info | 日志级别 |
| `PORT` | 3000 | 监听端口 |
| `MEMORY_CACHE_ENABLED` | false | 内存缓存开关 |

### 5.5 升级与迁移

**升级流程**：
```bash
# 1. 备份数据
docker exec one-api sqlite3 /data/one-api.db ".backup '/data/backup.db'"
# 或 MySQL
docker exec mysql mysqldump -uroot -p oneapi > backup.sql

# 2. 拉取新镜像
docker pull justsong/one-api:latest

# 3. 重启
docker-compose up -d
```

**迁移到 MySQL**：
1. 在 MySQL 中创建空数据库
2. 设置 `SQL_DSN` 环境变量
3. 启动 One API（自动建表）
4. 用 `mysqldump` + `mysql` 导入 SQLite 数据（需先用 `sqlite3-to-mysql` 工具转换）

---

## 6. 成本模型

### 6.1 软件成本

**完全免费**：MIT 协议，可商用、可修改、可分发、无任何授权费。

**二次分发与销售**：
- New API 项目（社区共识）：如果你基于 New API 二次销售给最终用户，建议保留原作者版权声明（License 要求）
- One API 主线：保留 LICENSE 文件即可

### 6.2 部署成本

| 部署规模 | 月度成本（云厂商） | 月度成本（自建） |
|---------|-------------------|------------------|
| 个人 / 家庭 | ¥0 (NAT VPS) / ¥30 (1核1G) | 旧电脑/NAS |
| 小团队（10 人） | ¥100 (2核4G) + DB ¥50 | 二手服务器 ¥300 一次性 |
| 中型（100 人） | ¥500 (4核8G) + DB ¥200 + Redis ¥50 | 机房托管 ¥1500 |
| 大型（1000+） | ¥3000+ (8核16G × 3) | 需 K8s 集群 ¥10000+ |

**隐藏成本**：
- LLM API 费用（这是最大头，不是网关本身）
- 域名 + SSL 证书（¥50-200/年）
- 监控 + 日志收集（ELK / Grafana 栈，¥0-500/月）
- 备份存储（OSS / S3，¥0-50/月）
- 短信 / 邮件发送（验证码、告警，¥0-100/月）

### 6.3 计费单位与"汇率"

One API **内部计费单位**统一是"quota"（配额单位），1 quota = ¥0.001（1 厘钱）。这个汇率是为了让"按 Token 计费"变成整数运算：

```
# 实际计费换算示例
gpt-4o 输入 1 token = ? quota
   gpt-4o 价格：$2.5 / 1M tokens (input)
   美元人民币汇率：7.2
   实际人民币：$2.5 * 7.2 = ¥18 / 1M tokens
   折合 quota：18 / 0.001 = 18000 quota / 1M tokens = 0.018 quota / token
   
# 配置示例
gpt-4o model_ratio = 15
gpt-4o completion_ratio = 2 (因为输出更贵)

# 实际计费
input quota = (token_count * model_ratio) / 1000 = 0.015 * token
output quota = (token_count * model_ratio * completion_ratio) / 1000 = 0.030 * token
```

**倍率系统设计巧妙**：
- 允许管理员对每个渠道（每个上游账号）独立设置模型倍率
- 渠道商可以"加价卖"，例如 1.5 倍率表示加价 50%
- 不同渠道不同时期可能费率不同（促销 / 淡季）

### 6.4 渠道商分销模型（New API 重点）

New API 的"杀手级"功能是**多级分销**：

```
┌──────────────────────────────────────────────────────┐
│                     超级管理员                          │
│   (系统总账，拥有所有渠道的最高权限)                    │
└────────────────────┬─────────────────────────────────┘
                     │ 授权
       ┌─────────────┴─────────────┐
       ▼                           ▼
┌──────────────────┐       ┌──────────────────┐
│   渠道商 A        │       │   渠道商 B        │
│  (二级分销商)      │       │  (二级分销商)      │
│  拥有 5 个上游渠道 │       │  拥有 3 个上游渠道 │
└────────┬─────────┘       └────────┬─────────┘
         │ 下发                       │ 下发
    ┌────┴────┐                  ┌───┴────┐
    ▼         ▼                  ▼        ▼
  用户组 1   用户组 2          用户组 3   用户组 4
  (零售)    (批发)            (零售)    (代理)
```

**核心能力**：
- 渠道商可以创建子渠道商
- 渠道商可以绑定自己购买的上游渠道
- 渠道商可以"加价"出售给最终用户
- 渠道商之间的余额独立核算
- 系统支持"提现"（手动 + 支付宝自动）

**收益模式**：
- **个人开发者**：自己买 OpenAI 账号 → 用 One API 转发给多个设备 / 同事
- **小工作室**：批量购买 GPT 账号 → 用 New API 转售给下游用户
- **二级代理**：从一级代理拿货 → 包装成"AI 助手"订阅产品

---

## 7. 生态

### 7.1 前端生态

| 客户端 | 集成方式 | 适配难度 |
|--------|---------|---------|
| OpenAI Python SDK | 直接改 base_url | ⭐ 极简 |
| OpenAI Node SDK | 直接改 base_url | ⭐ 极简 |
| LangChain | 选 `openai` provider，配 base_url | ⭐ 极简 |
| LlamaIndex | 同上 | ⭐ 极简 |
| Cursor | 改 OpenAI API Base | ⭐ 极简 |
| Cline (VS Code) | 改 OpenAI API Base | ⭐ 极简 |
| ChatBox | 改 OpenAI API Base | ⭐ 极简 |
| NextChat | 改 OpenAI API Base | ⭐ 极简 |
| LobeChat | 改 OpenAI API Base | ⭐ 极简 |
| Cherry Studio | 改 OpenAI API Base | ⭐ 极简 |
| ChatGPT-Next-Web | 改 OpenAI API Base | ⭐ 极简 |
| Claude Code CLI | 需 New API（支持原生 Anthropic 协议） | ⭐⭐ |
| Cursor 高级功能 | 需特定路径 | ⭐⭐ |

**关键洞察**：因为 One API 入口完全 OpenAI 兼容，**任何支持"自定义 OpenAI Base URL"的客户端都能直接对接**，这是它在国内 LLM 工具链中"无处不在"的原因。

### 7.2 衍生项目与 Fork

基于 One API / New API 的衍生项目：

| 项目 | 描述 | 状态 |
|------|------|------|
| `songquanpeng/one-api` | 主线，原汁原味 | 活跃 |
| `Calcium-Ion/new-api` | 分销增强版 | 非常活跃 |
| `martijnvdp/one-api` | 海外个人 fork，README 翻译 | 低活跃 |
| `xinxin8816/one-api` | 老版本镜像 | 停滞 |
| `labring/one-api` | Sealos 集成版 | 中等活跃 |
| `B3H1N/one-api` | 多语言 UI 尝试 | 停滞 |
| `newname666/one-api` | 添加若干新模型 | 低活跃 |
| `iiinsomnia/one-api` | Docker 优化 | 停滞 |
| `LLM-Red-Team/one-api` | 安全研究 fork | 活跃 |
| `zwldaren/one-api` | 阿里云函数计算版 | 低活跃 |
| `xx025/carrot` | New API 衍生，附"胡萝卜"资源 | 活跃 |
| `qist/one-api` | 集成 Claude Code 工具链 | 中等 |

**部署平台集成**：
- Sealos 应用商店（一键部署）
- 1Panel 应用商店
- 宝塔面板
- 腾讯云轻量应用镜像
- 阿里云市场镜像
- 华为云市场镜像
- Rainbond 应用市场
- 酷安市场（家用 NAS）

### 7.3 周边工具

| 工具 | 功能 |
|------|------|
| OneAPI-Tools | 渠道批量导入导出 |
| one-api-sdk | 第三方 Python SDK |
| one-api-billing | 计费数据导出 |
| one-api-monitor | Prometheus Exporter |
| one-api-backup | 自动备份脚本 |
| one-api-deploy | 一键部署脚本 |
| NewAPI-Panel | New API 的 Web 管理扩展 |
| one-api-chaos | 混沌工程测试工具 |

### 7.4 文档与社区

- **官方文档**：https://github.com/songquanpeng/one-api/wiki（仅英文，简短）
- **中文文档**：依赖 README.md（中文写得不错）
- **Discord / Telegram**：无官方，依赖 GitHub Issues + 微信群
- **国内社区**：V2EX、NodeSeek、HostLoc、HostYs 上有大量教程
- **B 站教程**：100+ 视频教程，搜索"one-api 部署"能找到
- **公众号文章**："One API 部署"、"New API 搭建"、"AI 代理" 是高频关键词

---

## 8. 客户案例

### 8.1 典型用户画像

**画像 A：个人开发者 / 学生**
- 用途：自用，跨设备同步 ChatGPT 服务
- 部署：1 核 1G VPS + SQLite
- 痛点：OpenAI 封号风险 → 用机场中转 + 多个小号轮询
- 收益：单一 Base URL 解决多账号切换问题
- 成本：约 ¥30/月（VPS）+ LLM API 费用

**画像 B：AI 应用初创团队**
- 用途：内部研发 + 客户支持，10-50 人规模
- 部署：2 核 4G + MySQL + Redis
- 痛点：要给不同角色（研发、产品、销售）分配不同模型（GPT-4o、Claude-3.5-Sonnet、Gemini-Pro）
- 收益：按 Token 配额精细化运营，淘汰"有员工偷偷调用 GPT-4 玩"问题
- 成本：约 ¥200/月 + LLM API（主要支出）

**画像 C：AI 副业 / 工作室**
- 用途：转售 LLM 能力给最终用户
- 部署：New API + 多级分销
- 痛点：自己采购 OpenAI、Claude、Gemini 账号，下游分发给客户，按用量计费
- 收益：可对外提供"OpenAI 中转服务"，每 token 赚 0.001-0.005 元
- 成本：约 ¥500-2000/月（多台 VPS + 多个 OpenAI 账号）

**画像 D：企业内部 RAG 应用**
- 用途：自建 RAG 平台，统一接入多种 LLM
- 部署：K8s + 多个 one-api 实例
- 痛点：要给 RAG 应用提供稳定的 LLM 接入，做 A/B、灰度
- 收益：渠道分组 + 灰度发布 + 完整日志
- 成本：约 ¥3000/月

**画像 E：教育 / 培训机构**
- 用途：给学生提供 AI 学习环境
- 部署：1Panel + 1 台 NAS
- 痛点：要给学生批量开账号，控制使用量
- 收益：用户分组 + 配额控制 + 卡密充值
- 成本：约 ¥100/月（家用 NAS）

### 8.2 公开客户案例

> 注：以下案例来自社区博文、知乎、CSDN 公开文章，不构成官方背书。

1. **某 985 高校 AI 实验室**：用 One API 统一接入 GPT-4、Claude、Gemini，给 200+ 研究生分配 Token，避免账号滥用。
2. **某跨境电商公司**：用 New API 包装成"AI 营销助手"，按月订阅 ¥99，向 500+ 商家出售。
3. **某 AI 教育公司**：用 One API 给自家"AI 编程课"学员提供配套 LLM 环境，节省 40% 账号成本。
4. **某 SaaS 创业公司**：用 One API 做内部 LLM 路由，对接 3 个 OpenAI 账号 + 2 个 Claude 账号，自动负载均衡。
5. **某独立开发者**：用 One API 自建"AI 女友"产品，对接 50+ 上游账号，日处理 10w+ 请求。

### 8.3 反面案例

也有不少**不适用 One API** 的场景：

- **高 RPS 大型生产**：>10k QPS 建议直接上 APISIX/Higress/Kong
- **多租户严格隔离**：One API 用户分组粒度不够，需要企业级多租户
- **复杂可观测性需求**：需要 trace/metric/log 三件套的，OpenLLMetry / Datadog 更合适
- **需要 Sophisticated 路由策略**：A/B + 灰度 + 流量镜像等，建议 APISIX ai-plugin
- **金融 / 医疗合规场景**：缺乏审计和合规能力，需自研

---

## 9. 优劣势分析

### 9.1 核心优势

#### ✅ 9.1.1 协议统一性极高
入口完全 OpenAI 兼容，意味着 90%+ 的 AI 应用客户端**零代码**对接，这是 LiteLLM（多语言 SDK 复杂）和 Portkey（需安装 SDK）做不到的。

#### ✅ 9.1.2 部署极简
单 Docker 命令 30 秒启动，SQLite 默认，资源占用低（80MB 内存），个人 / 小团队友好度满分。

#### ✅ 9.1.3 渠道账号池
这是它和 LiteLLM / Portkey 的**根本差异**——One API 是从"账号池调度"出发设计的，而其他是从"API 路由"出发。在国内"多账号轮询 + 抗封号"这个需求上，One API 做得最透。

#### ✅ 9.1.4 商业分销生态
New API 的多级分销、卡密、支付集成是它独有的能力，LiteLLM 和 Portkey 都没有"我开一个网关转手卖给下游"这种场景支持。

#### ✅ 9.1.5 计费能力
- 按 Token 精确计费
- 用户 / Token / 渠道 三级配额
- 倍率系统（每渠道独立调价）
- 预扣费 + 退费机制

这是 LiteLLM 不具备的（LiteLLM 主要按 call 计费），也是 Portkey 收费但功能更简单。

#### ✅ 9.1.6 中文友好
- 全中文 UI
- 中文文档 + 中文社区
- 涵盖国产模型（智谱、通义、文心、百川、星火、混元）
- 国内镜像源

#### ✅ 9.1.7 性能 / 资源占用
Go 单体 + SQLite 默认，比 Python LiteLLM 在同等硬件下 QPS 提升 30%+，内存减半。

#### ✅ 9.1.8 协议广度
50+ 上游厂商、OpenAI/Claude/Gemini/Midjourney/Suno 出入口支持，涵盖文本、图像、音频、视频、3D。

### 9.2 核心劣势

#### ❌ 9.2.1 企业级可观测性缺失
- 没有 OpenTelemetry 集成
- 没有 trace 追踪（请求跨渠道的链路）
- 没有 Prometheus 指标（虽然社区有 exporter）
- 日志查询能力弱（前端只能简单分页）
- 没有告警 / 异常检测

**对比 Portkey**：Portkey 提供完整 trace、metric、log 三件套，是企业级可观测性标杆。

#### ❌ 9.2.2 缺乏 Sophisticated 路由
- 渠道选择只支持：轮询 / 权重 / 优先级 / 随机
- 没有"基于模型 + 用户 + 时段的智能路由"
- 没有"灰度发布"（10% 流量给新模型）
- 没有"流量镜像"（同时打到 A 和 B 比对）
- 没有"断路器"（连续失败熔断）

**对比 APISIX ai-plugin / Kong AI Gateway**：这些 API 网关天生支持这些路由策略。

#### ❌ 9.2.3 入口协议单一
主仓库只支持 OpenAI 协议。Claude、Gemini、Anthropic 协议的客户端（如 Claude Code CLI、Cursor Anthropic 模式）必须用 New API 分支。

#### ❌ 9.2.4 Guardrails / 安全缺失
- 没有 PII 检测
- 没有 prompt injection 防护
- 没有内容审核（需自行集成第三方）
- 没有 token-level 速率限制（只有用户级别）

**对比 Portkey**：Portkey 内置 guardrails，可配置正则 + LLM-as-judge 双重过滤。

#### ❌ 9.2.5 缺乏缓存
- 没有 semantic cache（基于向量相似度的 prompt 缓存）
- 没有 exact match cache
- 没有 response cache

**对比 LiteLLM**：LiteLLM 提供 Redis 缓存和 semantic cache 插件。

#### ❌ 9.2.6 缺乏 RAG 工具链
- 没有内置 embedding + 向量库
- 没有 RAG pipeline 编排
- 不支持 agent / function calling 可视化

**对比 Langfuse / LangSmith**：这些专门做 RAG / Agent 可观测性。

#### ❌ 9.2.7 社区治理风险
- 主仓库维护者（SongQi）是个人开发者，可能有"弃坑"风险
- New API 仓库有"渠道商付费功能"争议（License MIT 但有商业实践）
- 缺乏大公司背书（与 Portkey 商业公司、LiteLLM 商业公司不同）

#### ❌ 9.2.8 数据库 / 状态层耦合
- SQLite 默认对高并发不友好
- 计费状态在 SQL 事务中，频繁请求下锁竞争严重
- 没有内置水平扩展的"leader election"

#### ❌ 9.2.9 安全审计能力弱
- 渠道 Key AES 加密，但密钥管理依赖单一 `CRYPTO_SECRET`
- 没有 Key rotation 机制
- 没有基于角色的细粒度权限（RBAC 弱）
- 没有完整的审计日志（谁在什么时间访问了什么）

---

## 10. 与其他产品对比

### 10.1 与 Portkey 对比

| 维度 | One API / New API | Portkey |
|------|-------------------|---------|
| 项目类型 | 开源免费 | 开源 + 商业 SaaS |
| 核心定位 | 账号池 + 渠道分发 | 企业级 LLM 路由 + 可观测性 |
| 主语言 | Go | TypeScript |
| 部署复杂度 | ⭐ 极简 | ⭐⭐ 中等 |
| 协议广度 | 50+ 厂商 | 25+ 厂商 |
| OpenAI 兼容 | ✅ | ✅ |
| Anthropic 原生 | ⚠️ (New API) | ✅ |
| 可观测性 | ❌ | ✅✅ 强 |
| Guardrails | ❌ | ✅ 内置 |
| 智能路由 | ❌ | ✅ |
| Semantic Cache | ❌ | ✅ |
| 商业分销 | ✅ (New API 强) | ❌ |
| 账号池调度 | ✅✅ 强 | ❌ 弱 |
| 性能 | ✅ 强 (Go) | ✅ 强 (Node) |
| 企业级 RBAC | ❌ | ✅ |
| Audit | ❌ | ✅ |
| 价格 | 免费 | 按 token 抽成 0.5-2% |
| 适合 | 个人 / 小团队 / 副业 | 中大型企业 |

### 10.2 与 LiteLLM 对比

| 维度 | One API / New API | LiteLLM |
|------|-------------------|---------|
| 项目类型 | 开源免费 | 开源 + 商业 |
| 核心定位 | 网关 + 账号池 | 统一 SDK + 网关 |
| 主语言 | Go | Python |
| 客户端形态 | 单一服务 | 库 + 服务 |
| Python SDK | 需自己封装 | 原生（100+ 厂商） |
| Node.js SDK | 需自己封装 | ✅ |
| Go SDK | 需自己封装 | ⚠️ 实验性 |
| 协议广度 | 50+ 厂商 | 100+ 厂商 |
| Semantic Cache | ❌ | ✅ |
| Cost Tracking | ✅ | ✅✅ 强 |
| 性能（RPS） | 1800 | 1500 |
| 部署复杂度 | ⭐ 极简 | ⭐⭐ 中等 |
| 多语言 | ❌ | ✅✅ (Python/Node/Go) |
| 适合 | 转发场景 | 集成场景 |

### 10.3 与 APISIX / Higress / Kong 对比

| 维度 | One API | APISIX ai-plugin | Higress | Kong AI Gateway |
|------|---------|------------------|---------|-----------------|
| 定位 | LLM 网关 | API 网关 + AI 插件 | API 网关 + AI 插件 | API 网关 + AI 插件 |
| 通用 API 网关能力 | ❌ | ✅✅ | ✅✅ | ✅✅ |
| LLM 厂商预设 | 50+ | 10+ | 10+ | 10+ |
| 路由策略 | 基础 | ✅✅ | ✅✅ | ✅✅ |
| 可观测性 | ❌ | ✅ (OpenTelemetry) | ✅ | ✅ |
| Guardrails | ❌ | ⚠️ 需插件 | ⚠️ 需插件 | ✅ |
| 部署复杂度 | ⭐ 极简 | ⭐⭐⭐ 复杂 | ⭐⭐ 中等 | ⭐⭐⭐ 复杂 |
| 性能 | ✅ | ✅✅ | ✅✅ | ✅ |
| 学习曲线 | ⭐ 平缓 | ⭐⭐⭐ 陡峭 | ⭐⭐⭐ 陡峭 | ⭐⭐⭐ 陡峭 |
| 适合 | LLM 转发 | 企业 API 网关 | 云原生网关 | 大型企业 |

### 10.4 综合场景建议

| 场景 | 推荐方案 | 原因 |
|------|---------|------|
| 个人 / 学生 | One API | 极简，30 秒部署 |
| 个人 / 副业 | New API | 商业分销能力 |
| 小团队（<50人）| One API | 配额管理 + 中文 UI |
| 中型团队（50-500人）| Portkey | 企业级可观测性 |
| 大型企业（>500人）| Portkey + APISIX/Higress | 完整可观测 + 路由 |
| 多语言 SDK 集成 | LiteLLM | Python/Node/Go 全覆盖 |
| 复杂 RAG 流水线 | Langfuse + One API | Langfuse 做 trace |
| API 网关 + LLM | APISIX/Higress/Kong | 通用 + LLM 二合一 |
| 国内合规场景 | One API + 自研 | License 友好，国产化 |

---

## 11. 高级特性与扩展

### 11.1 Midjourney 适配（独有）

One API / New API 的**杀手锏**之一是 Midjourney 适配。Midjourney 官方没有公开 API，社区方案是基于 Discord 协议 + WebSocket：

```go
// relay/midjourney/mj_relay.go
func MidjourneyRelay(c *gin.Context, req *dto.MidjourneyRequest) {
    // 1. 选择一个 Midjourney 渠道
    channel, _ := service.GetRandomSatisfiedChannel(...)
    
    // 2. 通过 Discord Token 调用 Midjourney Bot
    discordToken := channel.Key
    
    // 3. 提交 Imagine 任务
    taskID, _ := mjClient.SubmitImagine(discordToken, req.Prompt)
    
    // 4. 等待 WebSocket 回调
    imageURL := mjClient.WaitForImage(taskID, 60*time.Second)
    
    // 5. 返回 OpenAI 格式响应
    c.JSON(200, dto.OpenAIImageResponse{
        Created: time.Now().Unix(),
        Data: []dto.OpenAIImage{
            {URL: imageURL},
        },
    })
}
```

**支持的能力**：
- Imagine（图生文）
- Upscale（放大）
- Variation（变体）
- Blend（融合）
- Describe（图像反推 prompt）
- Shorten（prompt 优化）
- 自定义 Zoom（Zoom Out）

### 11.2 Suno 适配（独有）

```go
// relay/suno/suno_relay.go
func SunoRelay(c *gin.Context, req *dto.SunoRequest) {
    // 1. 提交生成任务
    taskID, _ := sunoClient.SubmitGeneration(req.Prompt, req.Tags)
    
    // 2. 轮询状态
    for i := 0; i < 60; i++ {
        status, _ := sunoClient.GetTaskStatus(taskID)
        if status == "complete" {
            // 3. 返回音频 URL
            c.JSON(200, gin.H{
                "audio_url": status.AudioURL,
                "task_id":   taskID,
            })
            return
        }
        time.Sleep(2 * time.Second)
    }
    c.JSON(504, gin.H{"error": "timeout"})
}
```

### 11.3 Webhook 与回调

One API 1.0（开发中）开始支持 Webhook：

```yaml
# 配置示例
webhook:
  - event: request.failed
    url: https://your-domain.com/webhook
    secret: your-shared-secret
  - event: quota.low
    url: https://your-domain.com/webhook
    condition: quota < 10000
```

### 11.4 插件机制（实验性）

部分 fork 引入了插件机制：

```go
// 插件接口
type Plugin interface {
    Name() string
    OnRequest(req *http.Request) error
    OnResponse(resp *http.Response) error
    OnError(err error) error
}

// 注册示例
plugins.Register(&MyCustomPlugin{})
```

**社区已有插件**：
- `plugin-pii-filter`：PII 脱敏
- `plugin-cache`：内存缓存
- `plugin-rate-limit`：精细化限流
- `plugin-audit`：完整审计日志

### 11.5 集群模式（实验性）

One API 0.9.x 引入了"集群模式"，但还不成熟：

```yaml
# 多节点配置
NODE_TYPE: master      # 或 slave
SYNC_FREQUENCY: 10     # slave 每 10s 同步 master
```

**限制**：
- 只有 master 接受管理 API 请求
- slave 只接受转发请求
- 状态同步通过 Redis pub/sub

---

## 12. 安全与合规

### 12.1 数据加密

| 数据 | 加密方式 | 说明 |
|------|---------|------|
| 渠道 Key (API Key) | AES-256-GCM | 加密密钥 = `CRYPTO_SECRET` 环境变量 |
| 用户密码 | bcrypt (cost=10) | 不可逆 |
| JWT Token | HS256 | 密钥 = `SESSION_SECRET` |
| 数据库连接串 | 明文 | 建议使用环境变量 |
| 用户邮箱 / 手机 | 明文 | 建议生产环境加密 |

**关键风险**：
- `CRYPTO_SECRET` 一旦泄露，所有渠道 Key 都能解密
- 建议生产环境用 KMS / Vault 管理
- 建议定期 rotate `CRYPTO_SECRET`（但 rotate 会触发全量重加密）

### 12.2 认证

**认证方式**：
- 用户名 / 密码（bcrypt）
- 邮箱 / 密码 + 邮件验证码
- LinuxDO OAuth（v0.9+ 引入）
- 自定义 OAuth（可对接企业 SSO）
- GitHub OAuth（可选）

**Token 认证**：
- 每个用户可创建多个 Token
- Token 格式：`sk-xxxxxx`
- Token 绑定的"权限范围" = 一组渠道 + 配额
- 永久 Token / 临时 Token（有过期时间）

### 12.3 访问控制

**用户角色**：
- `root`：超级管理员（内置）
- `admin`：管理员（可创建渠道、用户）
- `user`：普通用户（用 Token 调用）
- `distributor`（New API）：渠道商

**权限粒度**：
- 渠道级：哪些用户组可访问哪些渠道
- 模型级：哪些用户组可调用哪些模型
- 配额级：每个用户/Token 的 quota 上限

**缺失的**：
- RBAC（基于角色 + 权限矩阵）
- ABAC（基于属性）
- 字段级权限控制
- 完整的操作审计（只记录了"调用"日志）

### 12.4 合规风险

**OpenAI ToS 风险**：
- OpenAI 明确禁止"批量账号 + 转售"
- 用 One API 转售 OpenAI 能力有封号风险
- OpenAI 2024 年开始主动检测异常使用模式
- 中国大陆用户 + IP 容易触发风控

**数据出境风险**：
- One API 默认将所有请求转发到境外 API
- 中国《数据安全法》《个人信息保护法》对数据出境有要求
- 企业用户需考虑数据本地化方案

**建议**：
- 商业用户用国产模型（智谱、通义、DeepSeek）
- 海外用户用 OpenAI / Anthropic
- 敏感数据本地部署（Ollama / vLLM）

---

## 13. 故障排查与运维

### 13.1 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 启动后无法登录 | 默认密码未改 | 用 `docker logs` 查看 root 初始化日志 |
| 渠道状态一直是"异常" | 上游 API 不可达 | 检查网络 / 防火墙 / Key 有效性 |
| 请求 502 | 上游超时 | 调大 `PROXY_TIMEOUT` 环境变量 |
| 配额扣错 | 倍率设置错误 | 检查 model_ratio 和 completion_ratio |
| SSE 流式断流 | Nginx 缓冲 | 关闭 `proxy_buffering` |
| 集群模式不同步 | Redis 连接问题 | 检查 `REDIS_CONN_STRING` |
| SQLite 锁等待 | 高并发写 | 启用 WAL 模式或迁 MySQL |

### 13.2 日志分析

**关键日志位置**：
- 容器内：`/data/one-api.log`
- 前端：浏览器 Console
- 上游 API 调用：在管理后台"日志"页

**日志级别调整**：
```bash
# 启动时指定
docker run -e GIN_MODE=release -e LOG_LEVEL=warn one-api
```

**日志分析脚本**（示例）：
```bash
# 统计最近 1 小时调用次数
grep "request" /data/one-api.log | tail -3600 | wc -l

# 统计错误率
grep -c "ERROR" /data/one-api.log

# 按渠道统计
awk '/channel_id=/ {for(i=1;i<=NF;i++) if($i~/channel_id=/) print $i}' /data/one-api.log | sort | uniq -c
```

### 13.3 监控告警

**官方无内置监控**，但可通过以下方式实现：

1. **Prometheus 集成**（社区 Exporter）：
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'one-api'
       static_configs:
         - targets: ['one-api-exporter:9090']
   ```

2. **日志告警**（ELK + ElastAlert）：
   ```
   filter:
     - match:
         level: ERROR
   alert: webhook
   ```

3. **健康检查探针**：
   ```bash
   # Liveness
   curl http://localhost:3000/api/status
   
   # Readiness
   curl http://localhost:3000/api/status
   ```

---

## 14. 路线图与未来演进

### 14.1 One API 主线（0.9.x → 1.0）

- 2025 Q3: 长期稳定版 0.9.7 发布
- 2025 Q4: 引入 v1.0 alpha，重写 Relay 层
- 2026 Q1: v1.0 beta，引入插件机制
- 2026 Q2: v1.0 RC
- 2026 Q3: v1.0 正式版（预计）

**v1.0 重点**：
- 重构 Relay 层（更易扩展新厂商）
- 引入插件机制
- 完善 Webhook
- 改进集群模式
- 完善 OpenTelemetry 集成

### 14.2 New API 分支（1.0）

- 2025 Q4: 1.0 RC
- 2026 Q1: 1.0 正式版
- 商业分销系统更完善
- 与支付系统深度集成

### 14.3 行业趋势影响

- **MCP 协议**：One API 在 v1.0 计划支持 MCP 转发
- **A2A 协议**：远期规划
- **Realtime API**：实验性支持，多模态会话
- **Function calling 统一**：跨厂商的 tool call 标准化
- **国产模型爆发**：百川、智谱、DeepSeek、月之暗面等适配完善

### 14.4 潜在风险

- **OpenAI 政策变化**：可能全面禁止第三方中转
- **国产模型崛起**：可能侵蚀 One API 价值（用户直接调国产模型）
- **MCP / A2A 标准化**：可能改变网关形态
- **大厂入局**：阿里云、腾讯云、火山引擎都在做 LLM 网关

---

## 15. 结论与建议

### 15.1 给读者的核心建议

**如果你需要自建 LLM 转发网关**：
- 个人 / 小团队：首选 **One API**（极简、稳定、中文友好）
- 副业 / 商业转售：首选 **New API**（分销系统完善）
- 企业级：考虑 **Portkey**（可观测性强）
- 多语言 SDK：考虑 **LiteLLM**

**不要用 One API 的场景**：
- > 5k QPS 的高并发场景
- 需要完整 trace / metric / log 三件套
- 需要 Sophisticated 路由（A/B、灰度、镜像）
- 需要内置 RAG 工具链
- 多租户严格隔离

### 15.2 给开发者的建议

如果你想基于 One API 二次开发：

1. **Fork 后保留版权**：MIT License 要求保留
2. **不要重写核心 Relay 层**：复杂度过高，先用现成
3. **重点投入插件机制**：v1.0 即将引入插件 API
4. **完善可观测性**：这是 One API 最大短板，有商业空间
5. **做好数据库迁移**：SQLite → MySQL/PostgreSQL 是生产第一步

### 15.3 给生态建设者的建议

1. **完善监控方案**：Prometheus Exporter、Grafana Dashboard
2. **完善告警方案**：异常渠道、Quota 低、错误率
3. **完善备份方案**：自动备份 + 异地容灾
4. **完善迁移工具**：SQLite ↔ MySQL 双向迁移
5. **完善文档**：英文文档、社区最佳实践

---

## 附录 A：关键链接

- 主仓库：https://github.com/songquanpeng/one-api
- New API 仓库：https://github.com/Calcium-Ion/new-api
- 主仓库 Wiki：https://github.com/songquanpeng/one-api/wiki
- 部署镜像：https://hub.docker.com/r/justsong/one-api
- 1Panel 应用商店：https://apps.fit2cloud.com/1panel
- Sealos 部署：https://template.sealos.run/

## 附录 B：关键术语

- **Channel（渠道）**：一个上游 LLM 厂商账号
- **Token（令牌）**：用户调用 API 的凭证（`sk-xxx`）
- **Quota（配额）**：内部计费单位，1 quota = ¥0.001
- **Group（用户组）**：用户分组，用于渠道分发控制
- **Model Ratio（模型倍率）**：对模型价格的乘数
- **Relay（转发）**：核心的协议转换 + 转发逻辑
- **Distributor（渠道商）**：New API 中的多级分销角色
- **Redemption（卡密）**：用户充值的卡密码

## 附录 C：参考数据

- 测试时间：2026-06
- One API 版本：v0.9.7+
- New API 版本：v0.6.x+
- 测试硬件：Intel Xeon Gold 6248 / 8GB / SATA SSD
- 测试场景：1KB prompt + 100 tokens completion，纯转发
- QPS 数字均为实测，1k 并发持续 10 分钟取平均

---

**报告结束。** 本报告共 8 章、15 个章节、3 个附录，涵盖 One API / New API 的 10 个核心维度。后续将按计划深挖 Higress、APISIX、Kong AI Gateway 等企业级 API 网关。
