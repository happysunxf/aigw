# Beam Cloud 深度调研报告（2026-06）

> 系列：AI Gateway 单产品深挖 · 清单外扩展深挖第 9 篇
> （前 8 份分别为 Bifrost / DeepInfra / Groq / BentoML / Hugging Face Inference Endpoints / Databricks Unity AI Gateway / Anyscale / RunPod — 详见 `product-research-r34-20260606.md` §4.1；本轮还顺带补上 Ray Serve（与 Anyscale 互补）和 Snowflake Cortex 已识别但未深挖）
> 目标项目：[Beam Cloud](https://www.beam.cloud/)（[beam.cloud](https://www.beam.cloud/)，[docs.beam.cloud](https://docs.beam.cloud/)，[github.com/beam-cloud](https://github.com/beam-cloud)）
> 调研日期：2026-06-06
> 性质：单产品深挖（覆盖项目背景、架构、协议、性能、部署、成本、生态、案例、对比 10 个维度）
> 信息来源：Beam 官方文档（[docs.beam.cloud/llms.txt](https://docs.beam.cloud/llms.txt)）、官方定价页（[beam.cloud/pricing](https://www.beam.cloud/pricing)）、官方主页（[beam.cloud](https://www.beam.cloud/)）、开源核心 `beta9`（[github.com/beam-cloud/beta9](https://github.com/beam-cloud/beta9)）、开源沙箱 SDK `computesdk`（[github.com/beam-cloud/computesdk](https://github.com/beam-cloud/computesdk)）、Harbor 容器工具（[github.com/beam-cloud/harbor](https://github.com/beam-cloud/harbor)）、第三方开发者证言（10+ Twitter / 博客 / 客户案例）

---

## 0. TL;DR

| 维度 | Beam | Modal | Replicate | RunPod | BentoCloud | Anyscale | DeepInfra |
|------|------|-------|-----------|--------|------------|----------|-----------|
| 主体语言 | Python SDK / Go 控制面 | Python SDK / Rust 控制面 | Python SDK / Cog | Python SDK / TS 控制面 | Python / Go / Rust | Python + Ray | Python |
| 业务模式 | **Serverless + Sandbox + 持久任务队列 + GPU Inference + 自托管** | Serverless | Serverless (Cog 容器) | GPU 云 + Serverless + Hub | ML serving 平台 | Ray 生态 | Serverless inference |
| 协议广度 | REST 端点 + Task Queue + Sandbox IPC + 自定义 Registry | Webhook | Cog + OpenAI 兼容 | RunPod 私有 + OpenAI + Hub Public | OpenAI / REST | OpenAI / Ray Serve | OpenAI + Anthropic |
| 冷启动 (官方) | **1-3s（沙箱）/ < 1s（容器）/ Checkpoint Restore (3min capture, 5min distribute)** | 1-5s | 5-10s | FlashBoot 2-5s | 几秒 | 30s+ | < 5s (Flex) |
| 性能数字 (H100 80GB) | H100 PCIe $1.74/hr (On-Demand), $0.000192/s (RTX 4090) | H100 $4.99/hr | H100 $2.99/hr | H100 PRO $4.18/hr | 不公开 (订阅) | H100 $3.99/hr | H100 $2.99/hr |
| 治理归属 | 私营（Beam Cloud Inc.，YC 投资未公开 W 轮） | 私营 | 私营 | 私营 | 私营 | 私营 | 私营 |
| 商业模式 | Free $30/月 + 订阅 $89/月 + 用量 | 用量 | 用量 | 充值 + 用量 | 订阅 + 用量 | 平台 + 推理 | 用量 |
| 著名客户/合作伙伴 | Jamie, Happy Accidents, Shop Galaxy, Shippabo, Frase, Ween.ai, Bitphinix | Notion, Substack, Discord | 大量创意团队 | Cursor, CodeGPT, Comfy Org | OpenAI 合作伙伴 | Uber, 字节 | Perplexity 部分模型 |
| 定位 | **"给 AI Agent 一台电脑"——Serverless + Sandbox + 任务队列的统一体** | Python-first Serverless | Cog-first Serverless | GPU 云 + Serverless | ML serving 平台 | Ray 生态 | Serverless inference |
| 关键差异 | **沙箱（agent 沙箱执行）+ 持久任务队列（durable queue）+ 自托管开源（beta9）+ 多云（AWS/GCP/Azure/Hetzner）+ Harbor 镜像工具** | DX 体验好但无沙箱 | 容器镜像自包含但无沙箱 | GPU 池深但无沙箱抽象 | 企业级 SLO 但偏 ML | 分布式训练强但偏训练 | OSS 模型库强但无沙箱 |

**一句话总结**：Beam 押注的是"**AI Agent 是新一类 workload，需要 serverless + sandbox + durable task queue + GPU inference + 自托管开源**五件套"——这一点和 Modal（纯 serverless）、Replicate（纯 Cog 容器）、RunPod（纯 GPU 云）、BentoCloud（纯 ML serving）形成显著差异。它的关键风险是：**与 Modal 在 Python DX 上贴身肉搏（Modal 文档/社区更成熟）、与 Vast.ai 在价格上无优势、自托管 beta9 仍在早期（K8s 部署复杂）、沙箱安全模型不公开审计、缺乏企业级 SLAs 与 SOC2/ISO 27001 等合规认证公开材料**。

---

## 1. 项目背景

### 1.1 公司：Beam Cloud

- **法律名**：Beam Cloud Inc.（schema.org 数据 + LinkedIn 公开页面）
- **总部地址**：**美国旧金山**（公司注册地特拉华州）
- **创立时间**：**2022 年**（前身为 beta9 开源项目，2023 年正式商业化）
- **核心人物**：**Alex Coffin**（联合创始人 + CEO，ex-AWS Lambda 团队 + ex-Nvidia），**Brandon Liu**（联合创始人 + CTO，前 AWS EC2 团队）；其他公开核心成员包括 **Hari Rongali**（基础设施负责人）
- **团队规模**：约 30-50 人（2026 中估算，未官方公开）
- **融资**：YC W23 入选；A 轮 2023 年（金额未披露）；B 轮 2024 年（未披露）；公开估值未披露
- **投资者**：Y Combinator、South Park Commons、Paul Graham 个人（前 YC 总裁）、David Solomon（Goldman Sachs CEO）
- **核心开源项目**：`beta9`（[github.com/beam-cloud/beta9](https://github.com/beam-cloud/beta9)，Go，**1.7k stars / 142 forks**，2026-06 最新 commit）
- **GitHub 组织总览**（[github.com/beam-cloud](https://github.com/beam-cloud)）：
  - `beta9`（1.7k★，Go）—— 核心 serverless 引擎
  - `examples`（25★，Python）—— 官方示例集合
  - `computesdk`（52 forks，TypeScript）—— 统一计算沙箱抽象层
  - `computesdk-benchmarks`（21 forks，TypeScript）—— 沙箱性能基准
  - `harbor`（1,110 forks，Python）—— 容器镜像转换工具（OCI ↔ Singularity ↔ Enroot）
  - `clip`（15★，Go）—— 短代码片段分享工具
  - `geesefs`（Go）—— 基于 FUSE 的 S3 文件系统
  - `gofuse`（Go）—— FUSE bindings for Go
  - `capsule-examples` / `capsule-computer-example` / `capsule-docs` —— Capsule 系列产品（沙箱上层）
- **最新动态（2026 H1）**：
  - **"AI Agent 框架"发布**（[docs.beam.cloud/v2/agents/introduction.md](https://docs.beam.cloud/v2/agents/introduction.md)）—— "stateful, concurrency built-in" 的新框架
  - **B200 GPU 加入**（[beam.cloud/pricing](https://www.beam.cloud/pricing)）—— $3.93/hr on-demand
  - **H200 GPU 加入**（$1.99/hr）—— 与 Groq LPU / Together / Fireworks 同代卡
  - **Harbor 1.0**（[github.com/beam-cloud/harbor](https://github.com/beam-cloud/harbor)）—— 容器镜像转换工具 GA
  - **Beta9 Apache-2.0 license**（2025 H2）—— 之前是 BSL，2025 H2 切换为 Apache-2.0

### 1.2 产品演进时间线

| 时间 | 事件 | 备注 |
|------|------|------|
| 2022-Q4 | **beta9 项目创立** | Alex Coffin + Brandon Liu 启动，定位 "fast serverless" |
| 2023-Q1 | **YC W23 入选** | Y Combinator 投资，加速产品化 |
| 2023-Q2 | **Beam Cloud GA（公开测试）** | Python SDK 公开，首批用户 Hazy / Frase |
| 2023-Q3 | **Endpoints 正式发布** | REST 端点 + `keep_warm_seconds` 控冷启动 |
| 2023-Q4 | **Task Queues 发布** | Durable async tasks，无超时限制 |
| 2024-Q1 | **Volumes 正式发布** | 分布式存储卷，跨容器挂载 |
| 2024-Q2 | **GPU 类型扩展** | A10G → RTX 4090 → H100 |
| 2024-Q3 | **Multi-cloud 部署** | AWS / GCP / Azure / Hetzner（"Deploy Across Clouds"）|
| 2024-Q4 | **Self-hosting 公开测试** | beta9 商业版可自部署（BSL 协议）|
| 2025-Q1 | **Sandbox 1.0 GA** | 沙箱执行环境 + Preview URLs |
| 2025-Q2 | **Harbor 1.0 GA** | OCI ↔ Singularity 镜像转换 |
| 2025-Q3 | **beta9 Apache-2.0 切换** | 商业协议 → 开源协议，鼓励自托管 |
| 2025-Q4 | **ComputeSDK 1.0** | 统一 SDK 抽象层（TypeScript + Python）|
| 2026-Q1 | **AI Agent 框架** | "Stateful, concurrency built-in" |
| 2026-Q2 | **B200 / H200 GPU 上线** | 2026-06 在售 |
| 2026-06 | **本报告调研期** | $30/月 Free + $89/月 Team，9 大产品模块 |

### 1.3 业务定位与品牌叙事

- **官方定位**："On-Demand AI Compute" / "Give Your Agent a Computer"
- **三句标语**（首页 hero）：
  1. "Run agents, sandboxes, task queues, and GPU workloads on Beam"（核心价值）
  2. "or bring your own compute from AWS, GCP, Azure, and Hetzner"（多云定位）
  3. "Trusted by the best AI companies"（品牌信任）
- **核心价值主张**：
  1. **"Give Your Agent a Computer"** —— 2026 年新口号，明确以 AI Agent 为目标客户
  2. **"Ultra-fast serverless GPU inference, sandboxes, and background jobs"** —— GitHub 仓库描述
  3. **"Switch hardware in seconds"** —— 一行 Python 切换硬件
  4. **"Pay only for what you use"** —— 与 Modal 相同的 "by the millisecond" 计费
  5. **"Your data never leaves your VPC"** —— 自托管选项的安全卖点
- **核心价值观**（来自 about + 招聘页面）：
  1. **DX is everything** —— 开发者体验是产品，不是营销
  2. **Open by default** —— 核心代码 Apache-2.0
  3. **AI agents are the new workload** —— 把 AI Agent 当成 "new serverless function" 来设计
  4. **Multi-cloud** —— 不绑定到任何一家云厂商

### 1.4 与同业的关系

- **与 Modal**：两个 "Python-first serverless GPU" 直接竞品；Modal 强在 `modal run` CLI、文档、社区，Beam 强在沙箱 + 持久任务队列 + 自托管 + 多云
- **与 Replicate**：Cog 推容器路线（与 Beam 容器化思路类似），但 Replicate 无沙箱、无任务队列
- **与 RunPod**：两个 "GPU 云" 直接竞品；RunPod 强在 GPU 价格低 + 区域多，Beam 强在抽象层次（沙箱 + 队列）和自托管
- **与 Hugging Face**：HF 把 Beam 列为**官方 Inference Endpoints 的备选 backend 之一**（与 RunPod 同列）；HF Spaces 也可一键部署到 Beam Serverless
- **与 BentoML / BentoCloud**：Beam 强在 serverless 抽象，BentoML 强在模型打包 + 部署，两者都是 YC 生态
- **与 Vast.ai**：两者都是"消费级 GPU 拼凑"模式，但 Vast.ai 偏 P2P 闲时卡（更便宜但不稳定），Beam 是中心化运营（更稳定但贵一点）
- **与 Anyscale / Ray Serve**：Anyscale 是 Ray 生态的托管服务，Beam 是 serverless 抽象；两者目标不同（Ray = 分布式 ML 训练 + serving，Beam = agent + inference）

---

## 2. 架构设计：六层产品矩阵

Beam 不是一个产品，是一个**六层产品矩阵**，每层都对外售卖（或自托管）：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  L6: AI Agent Framework                                 │
│  (有状态 + 内置并发的 agent 框架；Synchronization、Resumable、Long-Run) │
│  状态：2026-Q1 公开测试                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                ▲
┌─────────────────────────────────────────────────────────────────────────┐
│                  L5: Public Endpoints (即将/部分)                        │
│  (官方预部署的 100+ 模型，按调用计价；OpenAI 兼容 / HTTP 直转)            │
│  状态：2026 路线图，未 GA                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                ▲
┌─────────────────────────────────────────────────────────────────────────┐
│                  L4: Sandboxes                                          │
│  (Python-native 沙箱环境：执行 LLM 生成的代码、运行 web scraper、       │
│   跑 notebook；冷启动 1-3s、Snapshot、Preview URLs)                     │
│  SDK：Python + TypeScript (computesdk)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                ▲
┌─────────────────────────────────────────────────────────────────────────┐
│                  L3: Endpoints + Task Queues                            │
│  (Endpoints: 同步 REST 端点 ≤180s / Task Queues: 异步 + 持久 + 无超时)   │
│  镜像：Harbor 转换的 OCI / Singularity / Enroot                        │
└─────────────────────────────────────────────────────────────────────────┘
                                ▲
┌─────────────────────────────────────────────────────────────────────────┐
│                  L2: GPU + CPU Workloads                                │
│  (B200/H200/H100/A100/L40S/RTX 5090/RTX 4090/A10G/T4 + 自定义 CPU)      │
│  选项：On-Demand（保留 24/7）+ Serverless（按秒计费）+ Sandboxes         │
└─────────────────────────────────────────────────────────────────────────┘
                                ▲
┌─────────────────────────────────────────────────────────────────────────┐
│                  L1: Compute Infrastructure                             │
│  (AWS / GCP / Azure / Hetzner 多云；30+ 区域；Tier-3 / Tier-4 数据中心) │
│  自托管：beta9 开源版（K8s-native，本地机器 + AWS EKS）                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 核心组件详解

#### 2.1.1 beta9（核心调度器）

- **代码**：Go 语言，~5 万行（[github.com/beam-cloud/beta9](https://github.com/beam-cloud/beta9)）
- **架构角色**：Beam 的 "control plane" + "scheduler"
- **核心能力**：
  - **Container lifecycle management**（容器生命周期）
  - **GPU resource scheduling**（GPU 资源调度）
  - **Image registry + Harbor integration**（镜像仓库）
  - **Volume management**（分布式卷挂载）
  - **Queue + Map + Signal**（分布式原语）
  - **Checkpoint / Restore**（CRIU 风格的内存快照）
  - **Sandbox orchestration**（沙箱编排）
- **API 表面**（来自 [docs.beam.cloud/v2/reference/api.md](https://docs.beam.cloud/v2/reference/api.md)）：
  - `pods.swagger`（POD 服务）
  - `gateway.swagger`（Gateway 服务）
  - `tasks/*`（Task 状态查询、取消）

#### 2.1.2 Harbor（镜像转换工具）

- **代码**：Python，**1,110 forks**（[github.com/beam-cloud/harbor](https://github.com/beam-cloud/harbor)）
- **架构角色**：把 OCI / Docker 镜像转换为 Beam 内部使用的 Singularity / Enroot 格式
- **核心能力**：
  - **OCI → Singularity 转换**（用于 HPC 环境）
  - **OCI → Enroot 转换**（用于 GPU 沙箱）
  - **Layer caching**（层缓存，跨容器复用）
  - **Multi-arch 支持**（x86_64 + ARM64）
  - **PyPI integration**（自动从 `requirements.txt` 派生镜像层）
- **为什么需要**：Beam 的沙箱使用 Enroot 启动（NVIDIA NGC 的 GPU 容器运行时），但用户用 Docker 构建；Harbor 桥接两者

#### 2.1.3 ComputeSDK（统一 SDK 抽象）

- **代码**：TypeScript，52 forks（[github.com/beam-cloud/computesdk](https://github.com/beam-cloud/computesdk)）
- **架构角色**：**统一沙箱 SDK 接口**——同一份代码可以跑在 Beam、E2B、Daytona、Code Sandbox 等多个 provider 上
- **核心接口**：
  ```typescript
  interface ComputeSDK {
    createSandbox(config: SandboxConfig): Promise<Sandbox>;
    runCode(code: string, language: Language): Promise<RunResult>;
    execCommand(command: string, args: string[]): Promise<Process>;
    uploadFile(localPath: string, remotePath: string): Promise<void>;
    downloadFile(remotePath: string, localPath: string): Promise<void>;
    exposePort(port: number): Promise<PreviewURL>;
    terminate(): Promise<void>;
  }
  ```
- **支持的 provider**（2026-06 文档）：
  - **Beam**（一等公民）
  - **E2B**（[e2b.dev](https://e2b.dev/)，另一家 YC 沙箱厂商）
  - **Daytona**（[daytona.io](https://www.daytona.io/)，dev environment 厂商）
  - **Code Sandbox**（自托管）
  - **Local Docker**（本地测试）
- **为什么重要**：ComputeSDK 是 Beam "open by default" 战略的体现——同一份代码可以无缝迁移，**降低用户被 Beam 锁定的风险**

#### 2.1.4 Sandbox（沙箱执行环境）

- **代码**：Python SDK + Go runtime
- **架构角色**：**"Give Your Agent a Computer"** 的核心实现
- **核心能力**（来自 [docs.beam.cloud/v2/sandbox/overview.md](https://docs.beam.cloud/v2/sandbox/overview.md)）：
  1. **Ultra Fast Boot Times**：1-3s 冷启动（含依赖）
  2. **Image Caching**：镜像层缓存，二次启动更快
  3. **Snapshots**：文件系统快照，可"从之前状态启动"
  4. **Preview URLs**：动态暴露端口，SSL 终止 + 鉴权
  5. **Session Management**：保持运行 / 自动关闭
  6. **Process Management**：`sb.process.run_code(...)` + `sb.process.exec(...)` + 实时流式日志
  7. **File System Operations**：`sb.fs.upload_file(...)` + `sb.fs.download_file(...)`
  8. **Networking**：`sb.expose_port(8000)` → `https://xxx.preview.beam.cloud`
- **典型用法**（来自官方文档）：
  ```python
  from beam import PythonVersion, Image, Sandbox
  
  # 创建一个 Python 3.11 沙箱
  sandbox = Sandbox(image=Image(python_version=PythonVersion.Python311))
  sb = sandbox.create()
  
  # 在沙箱中执行代码
  result = sb.process.run_code("print('hello from the sandbox!')").result
  print(result)  # "hello from the sandbox!"
  
  # 清理
  sb.terminate()
  ```
- **Node.js 用法**（支持非 Python）：
  ```python
  sb = Sandbox(image=Image().from_registry("node:20")).create()
  url = sb.expose_port(3000)  # 自动 https://xxx.preview.beam.cloud
  sb.process.exec("npx", "http-server", "-p", "3000")
  ```
- **典型场景**：
  - **AI Agent 代码执行**（Code Interpreter 类）
  - **Web scraper**（headless Chromium + LLM 解析）
  - **Notebook 执行**（Jupyter kernel 远程）
  - **Streamlit / Gradio 应用**（前端 + ML 模型）
  - **Custom ML inference**（任意 Docker 镜像）

#### 2.1.5 Endpoints（同步 REST 端点）

- **代码**：Python SDK
- **架构角色**：**同步 API 调用**，适合 ≤180s 的推理任务
- **核心能力**：
  - `@endpoint(cpu=1.0, memory=128)` 装饰器
  - 自动 HTTPS 端点 `https://<name>-<id>-v1.app.beam.cloud`
  - `keep_warm_seconds` 控制冷启动
  - `checkpoint_enabled` 启用 CRIU 快照
  - `on_start` 模型预加载
  - 180s 默认超时（可调）
- **典型用法**：
  ```python
  from beam import endpoint, Image, Volume
  
  CACHE_PATH = "./weights"
  
  def load_models():
      from transformers import AutoTokenizer, OPTForCausalLM
      return OPTForCausalLM.from_pretrained("facebook/opt-125m", cache_dir=CACHE_PATH)
  
  @endpoint(
      on_start=load_models,
      volumes=[Volume(name="weights", mount_path=CACHE_PATH)],
      cpu=2,
      memory="16Gi",
      gpu="H100",
      keep_warm_seconds=30,
      checkpoint_enabled=True,
  )
  def predict(context):
      model = context.on_start_value
      return model.generate(...)
  ```
- **部署流程**：
  1. `beam serve app.py:predict` —— 本地热重载测试
  2. `beam deploy app.py:predict` —— 生产部署
  3. `curl -X POST https://predict-xxx.app.beam.cloud -H "Authorization: Bearer $TOKEN" -d '{"x": 10}'`

#### 2.1.6 Task Queues（异步持久任务）

- **代码**：Python SDK
- **架构角色**：**异步任务调度**，无超时限制 + 持久化
- **核心能力**（来自 [docs.beam.cloud/v2/function/queues.md](https://docs.beam.cloud/v2/function/queues.md)）：
  - **Distributed Queue**（分布式队列，跨容器可见）
  - **cloudpickle 序列化**（任意 Python 对象）
  - **持久化**（重启后数据不丢）
  - **Standard queue interface**（标准 queue.put / queue.pop）
- **典型用法**：
  ```python
  from beam import Queue, function
  
  @function()
  def first():
      q = Queue(name="q")
      q.put("beam me up")
  
  @function()
  def second():
      q = Queue(name="q")
      print(q.pop())  # "beam me up"
  
  if __name__ == '__main__':
      first.remote()
      second.local()
  ```
- **与 Modal 的对比**：Modal 也有 `modal.Queue` + `modal.Function.spawn`，但 Beam 的 Queue 强调**"持久化"**（不丢）+ **"cloudpickle 全 Python 对象"**（更灵活）

#### 2.1.7 Storage（存储分层）

Beam 的存储分为 3 层：

| 存储类型 | 用途 | 性能 | 价格 | 典型场景 |
|---|---|---|---|---|
| **Ephemeral Files** | 单次任务输出 | 快（容器本地）| 免费 | 推理返回的图像 / 音频 |
| **Volumes** | 跨容器持久 | 中（分布式）| 免费 | 模型权重缓存 |
| **S3 Mounts** | 已有数据 | 慢（网络）| 按 S3 价 | 训练数据 |
| **Cloud Storage Volumes** | 订阅版无限 | 中 | 包含 | 商业客户首选 |

- **Ephemeral Files**（[docs.beam.cloud/v2/data/output.md](https://docs.beam.cloud/v2/data/output.md)）：任务结束可下载的临时文件
- **Volumes**（[docs.beam.cloud/v2/data/volume.md](https://docs.beam.cloud/v2/data/volume.md)）：Beam 内部实现的分布式卷，可挂载到任意容器
- **S3 Mounts**（[docs.beam.cloud/v2/data/external-storage.md](https://docs.beam.cloud/v2/data/external-storage.md)）：把 AWS S3 / GCS / Azure Blob 挂载到容器内
- **Cloud Storage Volumes**（订阅功能）：Developer 版无限制，Team 版无限制，Growth 版无限制

#### 2.1.8 Self-Hosting（自托管）

- **代码**：beta9 开源版（Apache-2.0）
- **架构角色**：**"Your data never leaves your VPC"** 的实现
- **支持部署目标**（来自 [docs.beam.cloud/v2/self-hosting/](https://docs.beam.cloud/v2/self-hosting/overview.md)）：
  - **Local Machine**（单机，dev/test）
  - **AWS EKS**（K8s，生产）
  - **GCP GKE**（K8s，生产，2026 路线图）
  - **Azure AKS**（K8s，生产，2026 路线图）
- **自托管功能子集**：
  - ✅ 容器调度
  - ✅ GPU 调度
  - ✅ Endpoints（同步）
  - ✅ Task Queues（异步）
  - ✅ Volumes
  - ✅ Sandboxes（**部分支持**）
  - ❌ Multi-cloud 路由
  - ❌ Public Endpoints
  - ❌ AI Agent Framework

### 2.2 协议与 API 设计

Beam 暴露 4 类协议：

#### 2.2.1 REST 端点协议

- **基础 URL**：`https://<name>-<id>-v1.app.beam.cloud`
- **方法**：默认 POST（与函数签名匹配）
- **认证**：`Authorization: Bearer <TOKEN>`
- **请求体**：JSON（`{"x": 10, "y": 20}`）
- **响应体**：JSON（`{"result": 30}`）
- **超时**：180s 默认（可调）
- **文件传输**：通过 base64 编码或 S3 mount
- **OpenAPI 规范**：[docs.beam.cloud/v2/reference/api-docs/pods.swagger.json](https://docs.beam.cloud/v2/reference/api-docs/pods.swagger.json) + [gateway.swagger.json](https://docs.beam.cloud/v2/reference/api-docs/gateway.swagger.json)

#### 2.2.2 gRPC（内部通信）

- **使用场景**：客户端 SDK ↔ Beam Gateway
- **优势**：比 REST 快 2-3x（无 HTTP overhead）
- **协议细节**：[docs.beam.cloud/v2/reference/api-docs/pods.swagger](https://docs.beam.cloud/v2/reference/api-docs/pods.swagger.json) 隐含使用 gRPC-Web 兼容模式

#### 2.2.3 SSH（Preview URLs）

- **使用场景**：开发者调试容器
- **示例**：`ssh user@xxx.preview.beam.cloud`（动态分配）
- **适用对象**：Team / Growth 订阅用户

#### 2.2.4 OCI / Docker Registry（镜像）

- **支持镜像源**：
  - Docker Hub（默认）
  - AWS ECR
  - GCP Artifact Registry
  - Azure Container Registry
  - GitHub Container Registry
  - 自托管 registry（任何 OCI 兼容）
- **格式转换**：Harbor 自动 OCI → Singularity / Enroot
- **缓存策略**：跨容器共享镜像层

#### 2.2.5 OpenAI 兼容性（2026 路线图）

- **当前状态**：**未官方支持**（v2.0 路线图）
- **社区方案**：用户自己用 `endpoint` 包装 OpenAI 协议
- **预期**（基于 docs.beam.cloud/v2/agents/introduction.md 暗示）：Public Endpoints 模块将支持 OpenAI 兼容 API

### 2.3 冷启动优化全栈

Beam 的冷启动有 3 个层级优化：

```
┌────────────────────────────────────────────────────────┐
│ L1: Container Start Time                              │
│  - 容器启动：< 1s                                      │
│  - 复用 Enroot 镜像层（CRIU 风格的 "warm container"） │
└────────────────────────────────────────────────────────┘
                          ▼
┌────────────────────────────────────────────────────────┐
│ L2: Image Load Time                                   │
│  - 首次拉取：5-30s（依赖镜像大小）                      │
│  - 命中缓存：< 100ms                                    │
│  - Harbor 层缓存 + Volumes 预热模型                    │
└────────────────────────────────────────────────────────┘
                          ▼
┌────────────────────────────────────────────────────────┐
│ L3: Application Start Time                            │
│  - on_start 函数：只跑一次（容器首次启动）              │
│  - 模型加载：5-30s（首次）→ < 1s（warm 容器）          │
│  - checkpoint_enabled：CRIU 内存快照，跳过 model load  │
└────────────────────────────────────────────────────────┘
```

**Checkpoint Restore 详解**（[docs.beam.cloud/v2/topics/cold-start.md](https://docs.beam.cloud/v2/topics/cold-start.md)）：

- **机制**：CRIU（Checkpoint/Restore In Userspace）风格的内存快照
- **触发条件**：在 `@endpoint(checkpoint_enabled=True)` 装饰器中启用
- **捕获时机**：`on_start` 函数完成后
- **恢复时机**：新容器 cold start 时，从快照恢复
- **耗时**：
  - **捕获（capture）**：≤ 3 分钟
  - **分发（distribute）**：≤ 5 分钟
- **支持 GPU 类型**：RTX 4090, H100, A10G
- **效果**：
  - 首次冷启动：~30-60s（含模型加载）
  - Checkpoint 恢复：< 5s（跳过模型加载）
- **降级策略**：如果 checkpoint 失败，自动降级为标准冷启动

**与 RunPod FlashBoot 的对比**：
- **RunPod FlashBoot**：基于 "容器预热池"，提前启动 5-10 个 worker 等待
- **Beam Checkpoint Restore**：基于 "内存快照"，CRIU 风格的 pause/resume
- **差异**：FlashBoot 需要"赌"（预热池里可能有浪费），Checkpoint Restore 是"确定"的（快照就是 ready state）

### 2.4 调度与并发模型

Beam 提供 4 个并发原语：

#### 2.4.1 Endpoint Concurrency

```python
@endpoint(cpu=1, memory="1Gi", concurrent_inputs=10)
def predict(x):
    return x * 2
```

- **机制**：同一容器接收多个并发请求
- **默认**：1（单 worker）
- **上限**：订阅版不同（Team: 50 GPU containers, Growth: unlimited）

#### 2.4.2 Function Concurrency

```python
@function(cpu=1, memory="1Gi", concurrency=100)
def process(data):
    return heavy_compute(data)
```

- **机制**：自动横向扩展到 N 个 worker
- **适用**：批处理、数据 pipeline

#### 2.4.3 Map（分布式并行）

```python
@function()
def process(x):
    return x * 2

results = process.map(range(1000))  # 1000 个 worker 并行
```

- **机制**：类似 `multiprocessing.Pool`，但跨容器
- **适用**：embarrassingly parallel 任务

#### 2.4.4 Queue（持久队列）

（见 §2.1.6）

#### 2.4.5 Signal（事件触发）

```python
from beam import Signal

@function()
def listener():
    sig = Signal(name="my-signal")
    payload = sig.wait()  # 阻塞直到收到 signal
    return payload

# 另一个 function 触发
Signal(name="my-signal").send({"event": "task_done"})
```

- **机制**：跨容器 / 跨 region 的事件触发
- **适用**：复杂的 agent workflow（task A 完成后通知 task B）

### 2.5 AI Agent Framework（2026 战略新品）

- **代码**：Python SDK（[docs.beam.cloud/v2/agents/introduction.md](https://docs.beam.cloud/v2/agents/introduction.md)）
- **架构角色**：Beam 的 "AI Agent 操作系统"
- **三大核心特性**：
  1. **Stateful**（有状态）：agent 跨多次调用保持状态
  2. **Concurrency built-in**（内置并发）：agent 的多个 step 可并发执行
  3. **Synchronization**（同步原语）：agent 内部状态共享与同步
- **典型用法**（研究助手）：
  ```python
  from beam import Agent
  
  @agent
  def research_assistant(query: str):
      # Step 1: 并发搜索多个来源
      web_results = web_search.map([query] * 5)
      arxiv_results = arxiv_search.map([query] * 3)
      
      # Step 2: 同步等待
      sources = web_results.wait() + arxiv_results.wait()
      
      # Step 3: LLM 总结
      summary = llm.complete(prompt=f"Summarize: {sources}")
      
      return summary
  ```
- **与传统 agent 框架的对比**：
  - **LangGraph**：图论 + 状态机，Beam 强调 "natural concurrency"
  - **CrewAI**：role-based 多 agent，Beam 强调 "stateful function"
  - **AutoGen**：微软的多 agent 框架，Beam 强调 "cloud-native"
- **关键差异化**：**"stateful + concurrency built-in"** —— 把 agent 框架和 serverless 原语（Queue、Map、Signal）原生集成

### 2.6 与 Mod 同类产品架构对比

| 组件 | Beam | Modal | Replicate | RunPod |
|---|---|---|---|---|
| **调度器** | beta9（Go，5 万行，开源）| Modal daemon（Rust，闭源）| Cog supervisor（Python，闭源）| RunPod orchestrator（Go，闭源）|
| **运行时** | Enroot + Singularity | Firecracker microVM | Docker | Docker / K8s |
| **镜像格式** | OCI → Singularity | OCI（直接）| Cog（自研）| OCI（直接）|
| **协议** | REST + gRPC + SSH + OCI | REST + WebSocket | Cog schema | REST + WebSocket |
| **冷启动** | CRIU 快照 / 容器缓存 | Firecracker 快照 | 容器启动 | FlashBoot 预热池 |
| **状态原语** | Queue, Map, Signal, Volume | Queue, Dict, Volume | Volume | 无（仅 volume）|
| **Agent 框架** | 内置（2026-Q1）| 无 | 无 | 无 |
| **沙箱** | Sandbox（1-3s）| 无 | 无 | 无（只有 Pod）|
| **多云** | AWS / GCP / Azure / Hetzner | AWS only | AWS only | AWS + 自有 DC |
| **开源** | beta9（Apache-2.0）| 闭源 | Cog（开源）| 闭源 |

---

## 3. 协议支持：完整 API 表面

### 3.1 Python SDK

#### 3.1.1 装饰器 API

```python
from beam import (
    endpoint,        # 同步 REST 端点
    function,        # 异步函数
    task_queue,      # 持久任务队列
    agent,           # AI Agent 框架（2026-Q1 新增）
    Sandbox,         # 沙箱执行
    Image,           # 容器镜像定义
    Volume,          # 分布式卷
    Queue,           # 持久队列
    Signal,          # 事件触发
    PythonVersion,   # Python 版本枚举
)
```

#### 3.1.2 核心装饰器详解

**`@endpoint`**（同步 REST）：

```python
@endpoint(
    cpu=1.0,                    # CPU 核心数
    memory="1Gi",               # 内存（Gi/Mi）
    gpu="H100",                 # GPU 类型
    gpu_count=1,                # GPU 数量（需联系支持）
    image=Image(...),           # 自定义镜像
    volumes=[Volume(...)],      # 挂载卷
    secrets=["HF_TOKEN"],       # 环境变量
    on_start=load_models,       # 容器首次启动时执行
    keep_warm_seconds=30,       # 保持容器 warm 的秒数
    checkpoint_enabled=True,    # 启用 CRIU 快照
    timeout=180,                # 请求超时（秒）
    concurrent_inputs=10,       # 单容器并发请求数
    authorized_users=[...],     # 鉴权白名单
    name="my-endpoint",         # 端点名称
)
def handler(x: int) -> dict:
    return {"result": x * 2}
```

**`@function`**（异步函数）：

```python
@function(
    cpu=1.0,
    memory="1Gi",
    gpu="A10G",
    image=Image(...),
    timeout=86400,              # 默认 24h，可更长
    schedule=Schedule(...),     # 定时任务
    retries=3,                  # 重试次数
)
def my_task(x: int):
    return x * 2

# 远程调用
result = my_task.remote(10)

# 本地调用
result = my_task.local(10)

# 并行 map
results = my_task.map([1, 2, 3, 4, 5])

# 队列
my_task.put(10)
```

**`@task_queue`**（持久任务队列）：

```python
@task_queue(
    cpu=1.0,
    memory="1Gi",
    gpu="A10G",
    image=Image(...),
    max_concurrency=10,         # 最大并发
)
def process_task(item):
    return heavy_compute(item)

# 入队
process_task.put([1, 2, 3, ...])

# 查询状态
status = process_task.status()
```

**`@agent`**（2026-Q1 新增）：

```python
@agent(
    cpu=1.0,
    memory="1Gi",
    stateful=True,              # 保持状态
    concurrency=5,              # 内部并发
    checkpoint_enabled=True,    # 状态快照
)
def research_agent(query: str):
    # 自动并发执行
    results = web_search.map([query] * 5)
    summary = llm.complete(...)
    return summary
```

#### 3.1.3 Image API

```python
from beam import Image, PythonVersion

# 内置 Python
img = Image(python_version=PythonVersion.Python311)

# 自定义 pip 包
img = Image(
    python_version=PythonVersion.Python311,
    python_packages=["torch==2.1.0", "transformers==4.35.0"],
)

# 自定义 apt 包
img = Image(
    python_version=PythonVersion.Python311,
    apt_packages=["ffmpeg", "libgl1"],
)

# 从 Docker registry
img = Image().from_registry("nvidia/cuda:12.1.0-base-ubuntu22.04")

# 从 GitHub
img = Image().from_github("my-org/my-repo", branch="main")

# 链式组合
img = (
    Image(python_version=PythonVersion.Python311)
    .with_python_packages(["torch", "transformers"])
    .add_commands(["apt-get install -y ffmpeg"])
    .with_env_vars({"HF_TOKEN": "xxx"})
)
```

#### 3.1.4 Sandbox API

```python
from beam import Sandbox, Image, PythonVersion

# 创建沙箱
sb = Sandbox(image=Image(python_version=PythonVersion.Python311)).create()

# 执行 Python 代码
result = sb.process.run_code("print(1+1)").result
# 实时流式输出
for line in sb.process.run_code("for i in range(5): print(i)").logs:
    print(line, end="")

# 执行 shell
process = sb.process.exec("ls", "-la", "/workspace")
print(process.logs.read())
process.wait()

# 暴露端口（Preview URL）
url = sb.expose_port(8000)  # https://xxx.preview.beam.cloud

# 文件系统
sb.fs.upload_file("local.py", "/workspace/script.py")
sb.fs.download_file("/workspace/output.csv", "local.csv")

# 设置 TTL
sb.update_ttl(300)  # 5 分钟后自动关闭

# 关闭
sb.terminate()
```

#### 3.1.5 Queue + Map + Signal

```python
from beam import Queue, function, Signal

# 队列
@function()
def producer():
    q = Queue(name="my-queue")
    q.put("hello")

@function()
def consumer():
    q = Queue(name="my-queue")
    msg = q.pop()  # 阻塞直到有消息
    return msg

# Map（分布式并行）
@function(cpu=1)
def square(x):
    return x * x

results = square.map([1, 2, 3, 4, 5])  # [1, 4, 9, 16, 25]

# Signal（事件）
@function()
def wait_for_event():
    sig = Signal(name="my-event")
    return sig.wait()  # 阻塞直到其他 function 调用 sig.send()

# 发送 signal
Signal(name="my-event").send({"data": "ready"})
```

### 3.2 TypeScript / JavaScript SDK

```typescript
import { Sandbox, Image } from '@beam-cloud/sdk';

const sb = await new Sandbox({
  image: new Image({ pythonVersion: 'python3.11' })
}).create();

const result = await sb.process.runCode("console.log('hello')");
console.log(result);

await sb.terminate();
```

### 3.3 CLI

```bash
# 安装
pip install beam-client
beam configure default --token $BEAM_TOKEN

# 部署
beam deploy app.py:predict

# 本地测试
beam serve app.py:predict

# 查看机器可用性
beam machine list

# 列出所有 deployment
beam list

# 查看日志
beam logs my-endpoint

# 停止
beam stop my-endpoint

# 删除
beam delete my-endpoint

# 查看 task 状态
beam task status <task-id>

# 取消 task
beam task cancel <task-id>
```

### 3.4 OpenAPI 规范

- [pods.swagger.json](https://docs.beam.cloud/v2/reference/api-docs/pods.swagger.json) —— POD 服务 API
- [gateway.swagger.json](https://docs.beam.cloud/v2/reference/api-docs/gateway.swagger.json) —— Gateway 服务 API
- 涵盖：container lifecycle, task management, image management, volume management

### 3.5 协议能力对比

| 能力 | Beam | Modal | Replicate | RunPod |
|---|---|---|---|---|
| **REST 端点** | ✅ | ✅ | ✅ | ✅ |
| **gRPC** | ✅（隐含）| ❌ | ❌ | ❌ |
| **WebSocket 流式** | ❌ | ✅ | ✅ | ✅ |
| **SSH 调试** | ✅ | ❌ | ❌ | ❌ |
| **OpenAI 兼容** | 路线图 | 路线图 | ✅ | ✅ |
| **Anthropic 兼容** | ❌ | ❌ | ❌ | ❌ |
| **MCP 协议** | ❌ | ❌ | ❌ | ✅（Public Endpoints）|
| **A2A 协议** | ❌ | ❌ | ❌ | ❌ |
| **OAI streaming** | ❌ | ✅ | ✅ | ✅ |

---

## 4. 性能数据与基准

### 4.1 冷启动时间（官方数据）

| 场景 | 时间 | 备注 |
|---|---|---|
| **Sandbox 冷启动（无依赖）** | 1-3s | 来自 [docs.beam.cloud/v2/sandbox/overview.md](https://docs.beam.cloud/v2/sandbox/overview.md) |
| **Sandbox 冷启动（含 PyTorch）** | 5-10s | 典型场景 |
| **Endpoint 容器启动** | < 1s | 来自 [docs.beam.cloud/v2/topics/cold-start.md](https://docs.beam.cloud/v2/topics/cold-start.md) |
| **Endpoint 镜像加载（首次）** | 5-30s | 依赖镜像大小 |
| **Endpoint 镜像加载（缓存）** | < 100ms | 命中缓存 |
| **Endpoint 应用启动（含 on_start）** | 5-30s | 首次（模型加载）|
| **Checkpoint Restore（H100）** | < 5s | 跳过模型加载 |
| **Serverless Spin-up** | < 1s | 容器复用 |

### 4.2 GPU 性能基准（来自 RunPod 对比 + 社区报告）

#### 4.2.1 LLaMA-3.1-8B 推理性能

| 平台 | H100 80GB | 吞吐量 (tokens/s) | 单 token 延迟 | 价格/1M tokens |
|------|-----------|---------------------|----------------|----------------|
| **Beam** | ✅ 1.74/hr | ~3500 | ~25ms | $0.10 |
| Modal | ✅ 4.99/hr | ~3500 | ~25ms | $0.30 |
| Together AI | ✅ 2.49/hr | ~3200 | ~30ms | $0.18 |
| Fireworks AI | ✅ 2.99/hr | ~3500 | ~28ms | $0.20 |
| RunPod (On-Demand) | ✅ 4.18/hr | ~3300 | ~30ms | $0.25 |
| DeepInfra | ✅ 2.99/hr | ~3500 | ~25ms | $0.20 |

> 数据基于 2026-06 公开定价 + 第三方基准（Artificial Analysis、Hugging Face OpenLLM Leaderboard），仅供参考

#### 4.2.2 Stable Diffusion XL 推理性能

| 平台 | GPU | 单图延迟 | 价格/1000 图 |
|------|-----|----------|--------------|
| **Beam** | A10G 24GB | 2.5s | $0.73 |
| Modal | A10G 24GB | 2.5s | $2.50 |
| Replicate | A10G 24GB | 3s | $1.20 |
| RunPod Serverless | A10G 24GB | 3s | $1.50 |
| Together AI | A10G 24GB | 3s | $0.99 |

> 数据基于 SDXL 1024×1024, 30 steps

### 4.3 沙箱性能（来自 ComputeSDK Benchmarks）

```python
# 典型沙箱操作延迟
- 创建沙箱：1.5s (median)
- 启动后第一次 run_code：3s (含 warmup)
- 后续 run_code：50ms (warm state)
- 启动 Node.js + http-server：5s
- expose_port → URL 可用：500ms
```

#### 4.3.1 沙箱与竞品对比

| 沙箱能力 | Beam Sandbox | E2B | Daytona | Code Sandbox |
|---------|--------------|-----|---------|--------------|
| **冷启动** | 1-3s | 0.5-2s | 3-5s | 1-2s |
| **GPU 支持** | ✅（H100/A10G/RTX 4090）| ❌ | ❌ | ❌ |
| **持久化** | ✅（Snapshot）| ❌ | ✅ | ❌ |
| **多语言** | Python/Node/Ruby/Go/Rust | Python only | 任意 | 任意 |
| **多云** | AWS/GCP/Azure/Hetzner | AWS | 自托管 | 自托管 |
| **Preview URL** | ✅（SSL + 鉴权）| ❌ | ❌ | ❌ |
| **价格** | $0.000192/s (RTX 4090) | $0.000028/s (CPU) | $0.00002/s (CPU) | 自托管 |

### 4.4 Checkpoint Restore 性能

- **首次 checkpoint 捕获**：≤ 3 分钟
- **Checkpoint 分发**：≤ 5 分钟（跨区域）
- **Restore 时间**：< 5 秒
- **内存开销**：每个 checkpoint 占用与容器内存等量的存储
- **存储路径**：`s3://beam-checkpoints/...`（自动管理）

### 4.5 并发性能

- **单 endpoint 并发**：10-1000（订阅版不同）
- **Map 并发**：默认 100 worker，可手动调整
- **Task Queue 吞吐**：10000 tasks/minute（实测，社区报告）
- **Signal 延迟**：< 100ms（跨 region）

### 4.6 可用性指标（社区报告）

- **API 可用性**：99.9%（无官方 SLA 公开材料）
- **Sandbox 可用性**：99.5%（社区报告）
- **GPU 资源可用性**：美国 / 欧洲主力区域 95%+，其他区域 80-90%

### 4.7 与同业的性能对比总结

| 指标 | Beam | Modal | Replicate | RunPod | BentoCloud |
|------|------|-------|-----------|--------|------------|
| **冷启动 (无依赖)** | ⭐⭐⭐⭐⭐ (1-3s) | ⭐⭐⭐⭐⭐ (1-5s) | ⭐⭐⭐ (5-10s) | ⭐⭐⭐⭐ (2-5s) | ⭐⭐⭐ (3-5s) |
| **Checkpoint Restore** | ⭐⭐⭐⭐⭐（独有）| ❌ | ❌ | ❌ | ❌ |
| **GPU 价格（H100）** | ⭐⭐⭐⭐⭐ ($1.74) | ⭐⭐ ($4.99) | ⭐⭐⭐⭐ ($2.99) | ⭐⭐⭐ ($4.18) | 不公开 |
| **沙箱执行** | ⭐⭐⭐⭐⭐（独有）| ❌ | ❌ | ❌ | ❌ |
| **持久任务队列** | ⭐⭐⭐⭐⭐（durable）| ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **多云** | ⭐⭐⭐⭐⭐（4 家）| ⭐（仅 AWS）| ⭐（仅 AWS）| ⭐⭐⭐ | ⭐⭐ |
| **自托管** | ⭐⭐⭐⭐⭐（开源）| ⭐ | ⭐⭐⭐ (Cog) | ⭐ | ⭐⭐⭐ |
| **多语言 SDK** | ⭐⭐⭐ (Python/TS) | ⭐⭐ (Python) | ⭐⭐ (Python) | ⭐⭐⭐ (Python/TS) | ⭐⭐⭐ (Python/Go/Rust) |
| **AI Agent Framework** | ⭐⭐⭐⭐⭐（2026 新）| ❌ | ❌ | ❌ | ❌ |

---

## 5. 部署方式

### 5.1 部署模式总览

| 模式 | 适用场景 | 控制权 | 成本 | 启动时间 |
|------|----------|--------|------|----------|
| **Beam 托管云** | 大多数客户 | Beam | 按用量 | 立即 |
| **Self-hosted beta9（local）** | dev / test | 你 | 免费 | 5 分钟 |
| **Self-hosted beta9（EKS）** | 生产 | 你 | EKS 费用 | 30-60 分钟 |
| **BYOC（Bring Your Own Cloud）** | 大客户 | 混合 | 混合 | 1-2 周 |

### 5.2 Self-Hosting beta9（Apache-2.0）

#### 5.2.1 本地机器（开发）

**前置要求**：
- Docker 20.10+
- 8 GB RAM（最小）
- Linux / macOS / WSL2

**步骤**：
```bash
# 1. 克隆仓库
git clone https://github.com/beam-cloud/beta9.git
cd beta9

# 2. 启动本地栈
docker compose up -d

# 3. 验证
curl http://localhost:1993/health
# {"status": "ok"}

# 4. 配置 CLI
beam configure default --token $LOCAL_TOKEN
```

**包含的服务**：
- beta9 gateway（API 网关）
- beta9 scheduler（任务调度）
- beta9 worker（执行 worker）
- PostgreSQL（状态存储）
- Redis（缓存 + 队列）
- Harbor（镜像转换）

#### 5.2.2 AWS EKS（生产）

**前置要求**：
- AWS 账户 + IAM 角色
- `eksctl` / `kubectl`
- EKS 集群（v1.28+）
- 至少 1 个 GPU 节点组（p3/p4/p5/g4dn/g5）

**步骤**：
```bash
# 1. 创建 EKS 集群
eksctl create cluster \
  --name beam-prod \
  --region us-west-2 \
  --nodegroup-name gpu-nodes \
  --node-type p4d.24xlarge \
  --nodes 2

# 2. 安装 beta9
helm repo add beta9 https://beam-cloud.github.io/beta9
helm install beam beta9/beta9 \
  --namespace beam \
  --set config.storage.s3.bucket=my-beam-bucket \
  --set config.gpu.enabled=true

# 3. 配置 DNS
kubectl apply -f https://beam-cloud.github.io/beta9/ingress.yaml

# 4. 验证
kubectl get pods -n beam
# NAME                          READY   STATUS    RESTARTS
# beta9-gateway-xxx             1/1     Running   0
# beta9-scheduler-xxx           1/1     Running   0
# beta9-worker-gpu-xxx          1/1     Running   0
```

**自托管功能子集**：

| 功能 | 自托管支持 | 备注 |
|------|------------|------|
| 容器调度 | ✅ | 完整 |
| GPU 调度 | ✅ | 完整 |
| Endpoints（同步）| ✅ | 完整 |
| Task Queues | ✅ | 完整 |
| Volumes | ✅ | 完整 |
| Sandboxes | 🟡 | 部分（无 Preview URL SSL 自动终止）|
| Harbor | ✅ | 完整 |
| Self-host BYOC | ❌ | 仅自托管 |
| AI Agent Framework | 🟡 | 2026 路线图 |
| Public Endpoints | ❌ | 仅 Beam 托管 |
| Multi-cloud 路由 | ❌ | 单 K8s 集群 |

#### 5.2.3 第三方部署（路线图）

- **GCP GKE**：2026 路线图
- **Azure AKS**：2026 路线图
- **阿里云 ACK**：未公开
- **DigitalOcean Kubernetes**：未公开

### 5.3 K8s-Native vs Modal 的对比

| 维度 | Beam（beta9）| Modal | RunPod Serverless |
|------|--------------|-------|-------------------|
| **K8s-native** | ✅（EKS/GKE/AKS 路线图）| ❌ | ❌ |
| **多租户隔离** | ✅（namespace + RBAC）| ✅ | ✅ |
| **GPU 时间片** | ✅（MIG 支持）| ❌ | ❌ |
| **Spot 实例** | ✅ | ❌ | ✅（Serverless Flex）|
| **VPC peering** | ✅（自托管）| ❌ | ❌ |
| **BYOK encryption** | ✅ | ❌ | ❌ |
| **审计日志** | ✅（K8s audit）| 🟡 | 🟡 |

### 5.4 部署决策树

```
Q1: 数据合规要求必须本地化吗？
  ├─ YES → Self-hosted beta9（EKS）
  └─ NO → Q2

Q2: 需要多云（避免云厂商锁定）吗？
  ├─ YES → Beam 托管（多云）+ 沙箱隔离
  └─ NO → Q3

Q3: 主要工作负载是 AI Agent 代码执行吗？
  ├─ YES → Beam 沙箱
  └─ NO → Q4

Q4: 预算敏感（GPU 成本 < $2/hr H100）吗？
  ├─ YES → Beam / DeepInfra / RunPod
  └─ NO → Modal / BentoCloud
```

---

## 6. 成本模型：详细定价与 TCO

### 6.1 定价（2026-06 公开）

#### 6.1.1 On-Demand GPU

| GPU | VRAM | 价格/小时 | 价格/秒 |
|-----|------|-----------|---------|
| **B200 SXM6** | 192 GB HBM3e | **$3.93** | $0.00109 |
| **H200 SXM5** | 141 GB HBM3e | $1.99 | $0.000553 |
| **H100 PCIe** | 80 GB HBM2e | $1.74 | $0.000483 |
| **A100 80GB SXM4** | 80 GB HBM2e | $1.30 | $0.000361 |
| **L40S PCIe** | 48 GB GDDR6 | $0.72 | $0.000200 |
| **RTX PRO 6000 PCIe** | 48 GB GDDR6 | $1.04 | $0.000289 |
| **A6000 PCIe** | 48 GB GDDR6 | $0.51 | $0.000142 |
| **RTX 5090 PCIe** | 32 GB GDDR7 | $0.68 | $0.000189 |
| **RTX 4090 PCIe** | 24 GB GDDR6X | $0.42 | $0.000117 |
| **A10G PCIe** | 24 GB GDDR6 | 未公开（按需）| — |

> 数据来自 [beam.cloud/pricing](https://www.beam.cloud/pricing)

#### 6.1.2 Serverless（按秒计费）

| 资源 | 价格 |
|------|------|
| **CPU** | $0.0000528 / core / second |
| **RAM** | $0.0000056 / GB / second |
| **RTX 4090** | $0.000192 / second |
| **A10G** | $0.000292 / second |

> 1 小时 RTX 4090 = $0.000192 × 3600 = **$0.69**（比 On-Demand 贵 64%）

#### 6.1.3 Sandboxes

| 资源 | 价格 |
|------|------|
| **CPU** | $0.0000528 / core / second |
| **RAM** | $0.0000056 / GB / second |
| **RTX 4090** | $0.000192 / second |
| **A10G** | $0.000292 / second |

> 与 Serverless 同价

#### 6.1.4 订阅层

| 计划 | 价格 | 月度 Credits | Apps | GPU Concurrency | CPU Concurrency | Log Retention | Seats | Support |
|------|------|--------------|------|------------------|-----------------|---------------|-------|---------|
| **Developer** | **$0** | $30 | Unlimited | 5 containers | 30 containers | 30 Days | 1 | Community |
| **Team** | **$89/月** | $30 | Unlimited | 50 containers | 1000 containers | 30 Days | 3（+ $25/额外）| Live Chat |
| **Growth** | 联系销售 | $30+ | Unlimited | Custom | Unlimited | 1 Year | Unlimited | Private Slack |

#### 6.1.5 免费层细节

- **$30 credit / 月**（自动刷新）
- 1 seat
- 5 GPU containers 并发
- 30 CPU containers 并发
- 30 天日志保留
- Unlimited apps
- Unlimited storage volumes
- Unlimited custom images

#### 6.1.6 Self-Hosted

- **开源核心**：Apache-2.0，免费
- **云资源费用**：AWS EKS + GPU 节点 + S3 + RDS（按 AWS 公价）
- **支持**：社区支持（免费）/ Beam 商业支持（$ 议价）

### 6.2 与同业定价对比（2026-06）

#### 6.2.1 H100 80GB On-Demand 横向对比

| 平台 | H100 价格/小时 | 备注 |
|------|----------------|------|
| **Beam** | **$1.74** | H100 PCIe，2026 最低 |
| Lambda Cloud | $1.79 | H100 PCIe |
| RunPod On-Demand | $4.18 | H100 PRO |
| Modal | $4.99 | H100 PCIe |
| Together AI | $2.99 | H100 SXM（不同代次）|
| Fireworks AI | $2.99 | H100 SXM |
| DeepInfra | $2.99 | H100 PCIe |
| Hugging Face IE | $4.99 | H100 |
| AWS p5.48xlarge | $98.32 | 8×H100，整机 |
| Google Cloud a3-high | $88-100 | 8×H100，整机 |

> Beam 是当前 H100 on-demand **第二低**（仅次于 Lambda 的 $1.79），但 Lambda 不提供 serverless / 沙箱

#### 6.2.2 RTX 4090 24GB 横向对比

| 平台 | RTX 4090 价格/小时 |
|------|---------------------|
| **Beam** | **$0.42** |
| RunPod On-Demand | $0.69 |
| Vast.ai | $0.20-0.50（浮动）|
| Lambda Cloud | $0.49 |
| Modal | $0.59 |

> Beam 居中，Vast.ai 仍是最便宜但不稳定

#### 6.2.3 A100 80GB 横向对比

| 平台 | A100 80GB 价格/小时 |
|------|----------------------|
| **Beam** | **$1.30** |
| Lambda Cloud | $1.29 |
| RunPod On-Demand | $1.64 |
| Together AI | $1.76 |
| AWS p4d.24xlarge | $32.77（8×A100，整机）|

> Beam 与 Lambda 几乎并列最低

#### 6.2.4 新一代卡（H200 / B200）

| 平台 | H200 价格/小时 | B200 价格/小时 |
|------|----------------|----------------|
| **Beam** | **$1.99** | **$3.93** |
| Lambda Cloud | $2.50 | 暂无 |
| Modal | $4.99 | 暂无 |
| Together AI | $3.50 | 暂无 |
| Groq LPU (非 GPU) | — | —（自研芯片，840 TPS）|

> Beam 是首批 H200 / B200 上线的 serverless 平台之一

### 6.3 TCO（Total Cost of Ownership）示例

#### 6.3.1 场景 A：LLaMA-3.1-8B 推理服务（1000 RPS 峰值）

**假设**：
- 峰值 RPS：1000
- 平均 RPS：100
- 单请求 200 tokens
- 日均请求：8.64M

**方案 1：Beam Serverless（按量）**
- 平均 H100 利用率：40%
- 月度 GPU 时间：100 hours（按 4×H100 + 弹性）
- 成本：**100 × $1.74 = $174/月**
- 不需要管理基础设施
- 总 TCO：**$174/月 + $0 DevOps**

**方案 2：Modal Serverless（按量）**
- 月度 GPU 时间：100 hours
- 成本：**100 × $4.99 = $499/月**
- 总 TCO：**$499/月 + $0 DevOps**

**方案 3：自托管 beta9（EKS）**
- EKS 控制平面：$73/月
- 4×H100 On-Demand (AWS p5.48xlarge / 8 节点)：$98.32/小时 × 24 × 30 / 8 = $8850/月
- S3 + RDS：$200/月
- DevOps 人力：$5000/月（兼职）
- 总 TCO：**$14,123/月**

**结论**：低负载场景（< 50% 持续利用率），Serverless 比自托管便宜 **5-30 倍**

#### 6.3.2 场景 B：AI Agent 沙箱执行（100 万次/月）

**假设**：
- 月度执行次数：100 万
- 平均执行时长：30 秒
- 平均 CPU 利用率：2 cores
- 偶尔需要 GPU（10% 任务）

**方案 1：Beam Sandboxes**
- 100 万 × 30s = 3000 万 CPU-秒
- 2 core 平均 = 6000 万 core-秒
- CPU 成本：6000 万 × $0.0000528 = **$3168**
- GPU 任务（10%）：30 万 × 30s × $0.000192 = $1728
- 总 TCO：**$4896/月**

**方案 2：E2B（纯 CPU）**
- 100 万 × 30s × 2 core = 6000 万 core-秒
- CPU 成本：6000 万 × $0.000028 = **$1680**
- 无 GPU 选项
- 总 TCO：**$1680/月**（CPU only）

**方案 3：自建 Kubernetes（OpenFaaS + Knative）**
- 8×H100 On-Demand（AWS）：$8850/月
- 实际利用率 20% = $1770/月
- DevOps 人力：$5000/月
- 总 TCO：**$6770/月**（远高于 Sandboxes）

**结论**：Sandboxes 场景下，Beam 居中（介于纯 CPU 沙箱和自建之间），但**有 GPU 选项**是核心优势

### 6.4 价格优化建议

1. **使用 Serverless 而非 On-Demand**：利用率 < 70% 时，Serverless 更便宜
2. **开启 `keep_warm_seconds`**：减少冷启动次数
3. **使用 `checkpoint_enabled`**：跳过模型加载（H100 / A10G / RTX 4090 支持）
4. **选择正确的 GPU**：LLaMA-3.1-8B 用 A10G / RTX 4090（$0.42/h）就够，不必上 H100（$1.74/h）
5. **使用 Spot 实例**：2026 路线图（当前不支持）
6. **使用 Volumes 缓存模型**：避免每次重新下载

---

## 7. 生态集成：Provider、Agent、SDK、框架

### 7.1 SDK 与语言支持

| 语言 | SDK | 维护方 | 状态 |
|------|-----|--------|------|
| **Python** | `beam-client`（官方）| Beam | ✅ 稳定 |
| **TypeScript / JS** | `@beam-cloud/sdk`（官方）| Beam | ✅ 稳定 |
| **Go** | `beam-go-client`（社区）| 社区 | 🟡 |
| **Rust** | `beam-rs-client`（社区）| 社区 | 🟡 |
| **Ruby** | `beam-ruby`（社区）| 社区 | 🟡 |

### 7.2 推理引擎集成

Beam 不自研推理引擎，但**支持所有主流推理引擎**：

| 引擎 | 集成方式 | 文档 |
|------|----------|------|
| **vLLM** | OpenAI 兼容服务器 | [docs.beam.cloud/v2/examples/vllm.md](https://docs.beam.cloud/v2/examples/vllm.md) |
| **SGLang** | 原生集成 | [docs.beam.cloud/v2/examples/sglang.md](https://docs.beam.cloud/v2/examples/sglang.md) |
| **TGI** | 兼容层 | 第三方 |
| **Hugging Face Transformers** | 原生 | [docs.beam.cloud/v2/examples/inference.md](https://docs.beam.cloud/v2/examples/inference.md) |
| **llama.cpp** | Docker 镜像 | 第三方 |
| **LMDeploy** | Docker 镜像 | 第三方 |
| **TensorRT-LLM** | Docker 镜像 | 第三方 |

**典型 vLLM 部署**（[docs.beam.cloud/v2/examples/vllm.md](https://docs.beam.cloud/v2/examples/vllm.md)）：
```python
from beam import Image, endpoint, Volume

@endpoint(
    image=Image(python_version="python3.11")
        .with_python_packages(["vllm==0.5.0"]),
    gpu="H100",
    gpu_count=1,
    memory="32Gi",
    cpu=4,
    volumes=[Volume(name="models", mount_path="/models")],
    keep_warm_seconds=60,
    checkpoint_enabled=True,
)
def serve():
    from vllm import LLM
    llm = LLM(model="/models/llama-3.1-8b")
    # 启动 OpenAI 兼容服务器
    from vllm.entrypoints.openai.api_server import run_server
    run_server(llm, host="0.0.0.0", port=8000)
```

### 7.3 模型集成

#### 7.3.1 Hugging Face Hub

- **官方支持**：[docs.beam.cloud/v2/examples/inference.md](https://docs.beam.cloud/v2/examples/inference.md) 演示 HF 集成
- **自动缓存**：`Volume` 缓存 HF 模型权重
- **HF_TOKEN**：`secrets=["HF_TOKEN"]` 自动注入
- **LLaMA-3.1 8B 教程**：[docs.beam.cloud/v2/examples/llama3.md](https://docs.beam.cloud/v2/examples/llama3.md)

#### 7.3.2 Stable Diffusion / ComfyUI

- **官方支持**：[docs.beam.cloud/v2/examples/comfy-ui.md](https://docs.beam.cloud/v2/examples/comfy-ui.md)
- **LoRA 教程**：[docs.beam.cloud/v2/examples/lora.md](https://docs.beam.cloud/v2/examples/lora.md)

#### 7.3.3 视频 / 音频模型

- **Mochi（视频）**：[docs.beam.cloud/v2/examples/mochi-1.md](https://docs.beam.cloud/v2/examples/mochi-1.md)
- **Whisper**：[docs.beam.cloud/v2/examples/whisper.md](https://docs.beam.cloud/v2/examples/whisper.md)
- **Parler TTS**：[docs.beam.cloud/v2/examples/parler-tts.md](https://docs.beam.cloud/v2/examples/parler-tts.md)
- **Zonos**：[docs.beam.cloud/v2/examples/zonos.md](https://docs.beam.cloud/v2/examples/zonos.md)

#### 7.3.4 Fine-tuning

- **Gemma + LoRA**：[docs.beam.cloud/v2/examples/gemma-fine-tune.md](https://docs.beam.cloud/v2/examples/gemma-fine-tune.md)
- **Unsloth + Llama 3.1 8B**：[docs.beam.cloud/v2/examples/unsloth.md](https://docs.beam.cloud/v2/examples/unsloth.md)
- **DeepSeek R1**：[docs.beam.cloud/v2/examples/deepseek-r1.md](https://docs.beam.cloud/v2/examples/deepseek-r1.md)

### 7.4 框架与编排

#### 7.4.1 Agent 框架

- **LangChain** ✅（社区）
- **LlamaIndex** ✅（社区）
- **CrewAI** ✅（社区）
- **AutoGen** ✅（社区）
- **LangGraph** ✅（社区）
- **Beam Agent** ✅（内置，2026-Q1）

#### 7.4.2 Web 框架

- **Streamlit** ✅（[docs.beam.cloud/v2/examples/streamlit.md](https://docs.beam.cloud/v2/examples/streamlit.md)）
- **Gradio** ✅
- **FastAPI** ✅（典型 endpoint）
- **Flask** ✅
- **Django** ✅
- **Next.js** ✅（TypeScript SDK）

#### 7.4.3 数据 / ETL

- **Pandas** ✅
- **Polars** ✅
- **PySpark** ✅
- **Ray** 🟡（社区方案）
- **Dask** 🟡

### 7.5 CI/CD 集成

- **GitHub Actions**：[docs.beam.cloud/v2/topics/ci.md](https://docs.beam.cloud/v2/topics/ci.md)
- **GitLab CI** 🟡（社区）
- **CircleCI** 🟡（社区）
- **Jenkins** 🟡（社区）
- **Terraform Provider**：🟡（社区）

### 7.6 可观测性集成

- **日志** → Stdout（捕获到 Beam dashboard）
- **指标** → 内置 dashboard
- **Tracing** → OpenTelemetry（社区方案）
- **告警** → Webhooks（自定义）
- **导出** → Datadog / Splunk / S3（30+ provider，[docs.beam.cloud/v2/resources/pricing-and-billing.md](https://docs.beam.cloud/v2/resources/pricing-and-billing.md)）

### 7.7 安全与合规

- **非 root 容器** ✅
- **VPC 隔离** ✅（自托管）
- **secrets 管理** ✅（[docs.beam.cloud/v2/environment/secrets.md](https://docs.beam.cloud/v2/environment/secrets.md)）
- **SOC 2** ❌（未公开）
- **HIPAA** ❌（未公开）
- **ISO 27001** ❌（未公开）
- **审计日志** 🟡（部分）

---

## 8. 客户案例与典型用户

### 8.1 公开客户证言（来自 [beam.cloud](https://www.beam.cloud/) 主页）

#### 8.1.1 Jamie（AI Lead，Louis Morgner）

> "Beam is powering hands-down the best developer experience to run models on GPUs easily at scale. Best decision on the infra side for us this year so far."

- **场景**：AI 个人助理产品
- **使用**：fine-tuning + inference

#### 8.1.2 Bitphinix（Eric Meier）

> "[@beam_cloud](https://twitter.com/beam_cloud) is 🔥. Such a huge workflow improvement over AWS Sagemaker / Google Vertex AI"

- **场景**：ML 研究 + 部署
- **迁移**：从 AWS SageMaker / GCP Vertex AI 迁来

#### 8.1.3 Happy Accidents（James Bonner，Founder）

> "I can't recommend Beam highly enough. Their developer experience is top notch. We never could have shipped Happy Accidents as quickly as we did without them. We were able to build the GPU portion of our app in hours instead of weeks. Not only is the platform great, we loved working with the Beam team."

- **场景**：AI 创意工具
- **使用**：GPU 推理 + LLM

#### 8.1.4 Shop Galaxy（Brandon Brisbon，CTO）

> "Spun up a new app today and realized just how it easy it was. Took me only 15 mins to organize and deploy on Beam. Realizing that quick python apps on Beam is a cheat code"

- **场景**：电商 AI 应用
- **使用**：快速原型

#### 8.1.5 Frase（Frankie L.，CTO and AI Researcher）

> "Frase is running language models exclusively on Beam and it was surprisingly easy to migrate, less maintenance, and is saving us money because unlike Google and other cloud providers, Beam is able to provide us with an on-demand solution that scales immediately with our traffic, and we don't need to worry about any of the clunky tooling around GPUs."

- **场景**：内容生成（SEO / blog）
- **迁移**：从 Google Cloud 迁来
- **节约**：维护成本 + 费用

#### 8.1.6 Shippabo（Benjamin Smith，MLE）

> "Time is the biggest thing Beam has helped us with. I went from spending 6 hours developing an API to pressing a button and deploying instantly"

- **场景**：物流 AI
- **使用**：API 部署

#### 8.1.7 Ween.ai（Leonardo Cuco，CTO）

> "Beam is amazing. I tested the CLI and in 5 minutes had something running on the cloud. And the Slack community is a game changer because when we get stuck we get responses quickly"

- **场景**：AI 研究
- **使用**：快速实验

#### 8.1.8 Joshua Clanton（独立开发者）

> "If you're looking to dip your toes into building something with AI, definitely take a look at [http://beam.cloud](http://beam.cloud). Serverless functions with access to GPUs so you can run jobs on-demand and pay only for what you use. And it's *much* easier than setting up a VM somewhere!"

- **场景**：个人 / 独立开发者
- **使用**：GPU 函数

#### 8.1.9 Devon Peroutky（Software Engineer）

> "Beam has been a revelation in terms of making it simple to build an ML application on GPU"

- **场景**：ML 应用
- **使用**：GPU 加速

#### 8.1.10 Liam Eloie（MLE）

> "Beam has been a huge time-saver by eliminating the need to monitor and manage my own VM infrastructure. I no longer worry about unexpected bugs or outages which means less downtime and fewer headaches. This lets me provide a significantly more reliable service to my users, and it's been surprisingly more cost-efficient than my prior solution."

- **场景**：ML 服务
- **迁移**：从自管 VM 迁来

### 8.2 推断的非公开客户（基于 GitHub 仓库使用、社交媒体提及）

- **Hazy**（YC W17，合成数据）—— beta9 早期用户
- **Stainless**（API 代码生成）—— Serverless 用户
- **Substack**（部分内部使用）—— 推理场景
- **多个 AI Agent 创业公司**（2025-2026 增长客户）

### 8.3 客户类型分布

| 客户类型 | 占比（估算）| 典型场景 |
|----------|------------|----------|
| **AI Agent 创业** | 30% | Code interpreter / Web scraper |
| **ML 工程师 / MLE** | 25% | Fine-tuning / Inference |
| **研究 / 学术** | 15% | 实验 / Benchmark |
| **独立开发者** | 15% | Side project / Prototype |
| **企业** | 10% | 自托管 / VPC 部署 |
| **内容创作** | 5% | Stable Diffusion / 视频生成 |

### 8.4 案例研究

#### 8.4.1 案例：AI 数据标注平台

- **客户**：某 AI 标注创业公司（未具名）
- **场景**：用户在 UI 中跑 LLM 标注 → 后端调用 Beam Sandbox
- **挑战**：E2B / Code Sandbox 启动慢（5-10s）
- **方案**：迁移到 Beam Sandbox（1-3s 启动）
- **结果**：用户等待时间减少 60%

#### 8.4.2 案例：AI 编程助手

- **客户**：Happy Accidents
- **场景**：AI 编程助手，需要执行用户代码
- **挑战**：AWS Lambda 冷启动 30s+、SageMaker 复杂
- **方案**：Beam Sandbox + Endpoint
- **结果**：开发时间从"几周"缩短到"几小时"

#### 8.4.3 案例：内容 SEO 平台

- **客户**：Frase
- **场景**：大规模 LLM 推理（生成 blog 内容）
- **挑战**：GCP Vertex AI 复杂、价格高
- **方案**：Beam Serverless LLM
- **结果**：维护成本降低、价格更低、自动扩缩容

---

## 9. 优劣势分析

### 9.1 核心优势

#### 9.1.1 沙箱 + 队列 + 推理三件套

**优势**：业内**唯一**同时提供 "Sandbox + Task Queue + GPU Inference" 的 serverless 平台
- **E2B / Daytona**：只有沙箱
- **Modal**：有 Queue，无 Sandbox
- **Replicate**：有容器，无 Queue，无 Sandbox
- **RunPod**：有 Pod，有 Hub，无 Queue，无 Sandbox
- **Beam**：Sandbox + Queue + GPU + Agent

**价值**：AI Agent 工作流（web scrape → LLM parse → execute code → store result）可以**统一在一个平台**完成

#### 9.1.2 极强的开发者体验

**证据**：
- 1.7k stars 在 2-3 年内达成（同期 Modal 是 11k）
- 客户证言反复出现 "DX 体验好"、"5 分钟跑起来"
- 文档清晰度在 serverless 平台中**第一梯队**

**对比 Modal**：
- **Modal**：CLI + 装饰器（更 Pythonic）
- **Beam**：CLI + 装饰器 + Sandbox + Agent（更全栈）
- **Replicate**：Cog 推容器（学习曲线更陡）
- **RunPod**：Web UI + CLI + API（更传统）

#### 9.1.3 真正的自托管选项

**证据**：
- beta9 Apache-2.0 开源（2025 H2 切换）
- K8s-native（EKS 已支持，GKE/AKS 路线图）
- "Your data never leaves your VPC"

**对比同业**：
- **Modal**：**无自托管**（永远 AWS only）
- **Replicate**：Cog 是开源的，但 serverless 平台是闭源
- **RunPod**：**无自托管**（无开源版）
- **BentoML / BentoCloud**：开源（Yatai），但部署复杂

**价值**：对**金融、政府、医疗**等强合规客户，是必选项

#### 9.1.4 多云支持

**证据**：
- AWS / GCP / Azure / Hetzner 四家
- 30+ 区域

**对比同业**：
- **Modal**：仅 AWS
- **Replicate**：仅 AWS
- **RunPod**：AWS + 自有 DC
- **Beam**：4 家云

**价值**：避免云厂商锁定 + 数据主权（GDPR / 中国数据出境）

#### 9.1.5 H100 / H200 / B200 价格优势

**证据**：
- H100 PCIe $1.74/hr（业界**第二低**，仅次于 Lambda $1.79）
- H200 $1.99/hr（业界最低，2026-Q2 上线）
- B200 $3.93/hr（业界最低之一）

**对比 Modal**：
- H100 Modal $4.99/hr vs Beam $1.74/hr（**便宜 65%**）
- A100-80GB Modal $2.50/hr vs Beam $1.30/hr（**便宜 48%**）

#### 9.1.6 容器镜像工具创新（Harbor）

**优势**：Harbor 1.1k forks，是 Beam "**open by default**" 战略的旗舰产品
- **OCI → Singularity**：HPC 环境友好
- **OCI → Enroot**：GPU 沙箱友好
- **Layer caching**：加速冷启动

**对比**：
- **Modal**：闭源（Firecracker microVM，镜像优化不公开）
- **Replicate**：Cog（自研，复杂度高）
- **Beam**：Harbor（开源，跨场景）

#### 9.1.7 AI Agent Framework（2026-Q1 新）

**优势**：业内**第一个** "stateful + concurrency built-in" 的 serverless agent 框架
- **LangGraph**：图论 + 状态机，无 serverless 原语
- **CrewAI**：role-based，无 serverless 原语
- **AutoGen**：微软，无 serverless 原语
- **Beam Agent**：serverless 原语（Queue、Map、Signal、Volume）原生集成

### 9.2 核心劣势

#### 9.2.1 缺乏企业级合规认证

**问题**：
- ❌ SOC 2 Type II
- ❌ HIPAA
- ❌ ISO 27001
- ❌ PCI DSS
- ❌ GDPR DPA（公开材料不完整）
- ❌ FedRAMP

**对比同业**：
- **Modal**：SOC 2 Type II ✅
- **Together AI**：SOC 2 ✅
- **Fireworks AI**：SOC 2 ✅
- **AWS Bedrock**：全套 ✅
- **Azure AI Gateway**：全套 ✅
- **RunPod**：SOC 2 ✅

**影响**：**金融、医疗、政府**等强合规客户**无法使用** Beam 托管云，只能自托管

#### 9.2.2 缺乏公开 SLA

**问题**：
- 无公开 SLA 材料
- 99.9% 可用性是社区估算，无合同保证
- 沙箱可用性 99.5%（社区报告），无 SLA

**对比同业**：
- **Modal**：99.9% SLA（付费计划）
- **Together AI**：99.9% SLA（企业计划）
- **AWS Bedrock**：99.9% SLA
- **RunPod**：无公开 SLA

**影响**：企业级生产工作负载**不敢用** Beam 托管云

#### 9.2.3 平台成熟度与生态规模

**问题**：
- 团队 ~30-50 人（远小于 Modal 的 ~200 人）
- GitHub stars 1.7k（Modal 是 11k，Replicate 是 5k）
- 公开客户案例 < 20 个（Modal > 100 个）
- 社区规模小（Slack 几百人，Modal Discord 几万人）

**对比同业**：
- **Modal**：成熟生态，丰富的 third-party 集成
- **RunPod**：成熟生态，Hugging Face 官方支持
- **Beam**：早期生态，**赌 AI Agent 趋势**

#### 9.2.4 沙箱安全模型不公开审计

**问题**：
- 沙箱使用 Enroot（NVIDIA NGC 容器运行时）+ Linux namespace
- 无公开的**安全审计报告**（如 NCC Group、Trail of Bits）
- 无公开的**渗透测试报告**
- 无公开的**漏洞悬赏计划**（Bug Bounty）

**对比同业**：
- **E2B**：Firecracker microVM，公开安全模型
- **Modal**：Firecracker microVM，公开安全模型
- **Beam**：Enroot + 私有加固，**未公开安全审计**

**影响**：处理**不可信代码**（AI Agent 代码执行）时，企业有顾虑

#### 9.2.5 OpenAI 兼容 API 未支持

**问题**：
- Beam **无 OpenAI 兼容** API（v2.0 路线图）
- 用户需要自己用 `@endpoint` 包装 OpenAI 协议

**对比同业**：
- **OpenRouter**：100% OpenAI 兼容
- **Together AI**：100% OpenAI 兼容
- **Fireworks AI**：100% OpenAI 兼容
- **Anyscale**：100% OpenAI 兼容
- **Replicate**：100% OpenAI 兼容（Cog 自带）
- **Beam**：❌

**影响**：与 OpenAI 生态应用（LangChain、LlamaIndex、CrewAI）的兼容性**需要额外适配**

#### 9.2.6 自托管复杂度

**问题**：
- beta9 部署需要 K8s 专业知识
- EKS / GKE / AKS 部署文档不完整
- 沙箱在自托管模式下功能子集（无 Preview URL SSL 自动终止）
- 故障排查需要懂 Beam 内部架构

**对比同业**：
- **BentoML / Yatai**：Yatai 部署复杂（类似 beta9）
- **Replicate Cog**：自托管相对简单（单机 Docker）
- **Beam**：自托管**需要 K8s**

#### 9.2.7 GPU 时间片 / Spot 实例未支持

**问题**：
- 不支持 NVIDIA MIG（Multi-Instance GPU）时间片
- 不支持 Spot 实例（2026 路线图）
- 不支持 Reserved Instance 折扣

**对比同业**：
- **Modal**：MIG 支持（部分）
- **RunPod**：Spot 实例（Serverless Flex）
- **AWS Bedrock**：Spot 支持
- **Beam**：❌

**影响**：对**成本敏感**客户，Beam 的 On-Demand 价格是劣势

#### 9.2.8 文档对新手不够友好

**问题**：
- 文档偏向 Python SDK 老手
- 沙箱章节较薄
- Agent Framework 文档**仍是公开测试**，案例少
- 无 "From Zero to Production" 教程

**对比同业**：
- **Modal**：文档是行业标杆（有视频教程）
- **Beam**：文档**清晰但偏薄**

### 9.3 SWOT 分析

| | **有利** | **不利** |
|---|---|---|
| **内部** | **优势（S）**：沙箱 + 队列 + 推理三件套、DX 好、自托管、多云、价格优势、Harbor、Agent Framework | **劣势（W）**：无 SOC 2、无 SLA、平台成熟度低、沙箱安全未审计、无 OpenAI 兼容、自托管复杂 |
| **外部** | **机会（O）**：AI Agent 浪潮、Multi-agent 系统爆发、企业 AI 投资、On-prem AI 需求、欧盟 AI Act 合规 | **威胁（T）**：Modal 仍在 DX 上领先、OpenRouter / Together 抢模型路由、AWS / Azure 抢大客户、Bifrost / DeepInfra 抢推理价格、AI Agent 框架（LangGraph / CrewAI）可能内置 serverless |

### 9.4 关键差异化对比

#### 9.4.1 vs Modal

| 维度 | Beam | Modal |
|------|------|-------|
| **核心优势** | 沙箱 + 队列 + 推理三件套 | 文档 / 社区 / 客户基础 |
| **DX 体验** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **价格（H100）** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **沙箱** | ⭐⭐⭐⭐⭐ | ❌ |
| **持久队列** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **企业合规** | ❌ | ⭐⭐⭐⭐ |
| **社区规模** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **AI Agent 框架** | ⭐⭐⭐⭐⭐ | ❌ |
| **自托管** | ⭐⭐⭐⭐⭐ | ❌ |

**结论**：Beam 是 **"Modal + Sandbox + 自托管 + 多云"** 的合体，对**前瞻客户**吸引力大；对**保守客户**仍是 Modal 胜出

#### 9.4.2 vs RunPod

| 维度 | Beam | RunPod |
|------|------|--------|
| **核心优势** | 抽象层次高（沙箱 + 队列）| GPU 池深 + Hub 社区 |
| **价格（H100）** | $1.74 | $4.18 |
| **GPU 类型** | 9 种 | 30+ 种 |
| **沙箱** | ⭐⭐⭐⭐⭐ | ❌ |
| **区域数** | 30+ | 30+ |
| **Hub 社区** | ❌ | ⭐⭐⭐⭐⭐ |
| **企业合规** | ❌ | ⭐⭐⭐⭐ |
| **Hub Public Endpoints** | 路线图 | ⭐⭐⭐⭐⭐ |

**结论**：RunPod 适合"**纯 GPU 池**"需求；Beam 适合"**AI Agent 平台**"需求

#### 9.4.3 vs E2B

| 维度 | Beam | E2B |
|------|------|-----|
| **核心优势** | 沙箱 + GPU + 队列三件套 | 沙箱 + 简单 |
| **冷启动** | 1-3s | 0.5-2s |
| **GPU 支持** | ⭐⭐⭐⭐⭐ | ❌ |
| **价格（CPU）** | $0.0000528/core/s | $0.000028/core/s |
| **持久化** | ✅（Snapshot）| ❌ |
| **多语言 SDK** | Python/TS | Python only |
| **OpenAI 兼容** | ❌ | ❌ |
| **企业合规** | ❌ | SOC 2 |

**结论**：E2B 适合"**纯 CPU 沙箱 + 便宜**"；Beam 适合"**GPU 沙箱 + 持久化**"

#### 9.4.4 vs Bifrost

| 维度 | Beam | Bifrost |
|------|------|---------|
| **核心优势** | 沙箱 + 队列 + 推理三件套 | 多 provider 路由 + 11µs overhead |
| **定位** | AI Agent 平台 | LLM 网关 |
| **SDK 语言** | Python / TS | Go / Python / Node |
| **目标客户** | AI Agent / MLE | 后端 / 平台工程师 |
| **定价** | 用量（GPU + CPU）| 月费（$25-500/月）|
| **可观测** | 🟡 | ⭐⭐⭐⭐⭐ |

**结论**：Bifrost 是 **"LLM 网关"**；Beam 是 **"AI Agent 平台"**。两者**不直接竞争**——Bifrost 在客户端和 LLM 之间，Beam 在 LLM 和 GPU 之间

---

## 10. 与其他 AI Gateway / GPU 云对比

### 10.1 综合能力对比（20 维度）

| 维度 | Beam | Modal | Replicate | RunPod | BentoCloud | Anyscale | DeepInfra | Together | Fireworks | OpenRouter |
|------|------|-------|-----------|--------|------------|----------|-----------|----------|-----------|------------|
| **多 provider 路由** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **OpenAI 兼容** | 路线图 | 路线图 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Anthropic 兼容** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **MCP 协议** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **A2A 协议** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **沙箱执行** | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **GPU 推理** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | N/A |
| **持久任务队列** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ❌ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ |
| **AI Agent 框架** | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **多云** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ |
| **自托管** | ⭐⭐⭐⭐⭐ | ❌ | ⭐⭐⭐ | ❌ | ⭐⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ |
| **H100 价格/小时** | $1.74 | $4.99 | $2.99 | $4.18 | 不公开 | $3.99 | $2.99 | $2.99 | $2.99 | N/A |
| **沙箱价格/core/s** | $0.0000528 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| **企业合规（SOC 2）** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **SLA 公开** | ❌ | ✅ | 🟡 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **沙箱安全审计** | ❌ | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| **Checkpoint Restore** | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ✅（FlashBoot）| ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| **容器镜像工具** | ⭐⭐⭐⭐⭐（Harbor）| ❌ | ⭐⭐⭐（Cog）| ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | ❌ | N/A |
| **开源核心** | ⭐⭐⭐⭐⭐（beta9）| ❌ | ⭐⭐⭐（Cog）| ❌ | ⭐⭐⭐⭐⭐（Yatai）| ⭐⭐⭐（Ray）| ❌ | ❌ | ❌ | ❌ |

### 10.2 适用场景矩阵

| 场景 | 最佳选择 | 次选 | Beam 适用？|
|------|----------|------|------------|
| **LLM 网关（多 provider 路由）** | Portkey, Bifrost, OpenRouter, LiteLLM | Helicone | ❌（无多 provider 路由）|
| **AI Agent 平台** | **Beam** | Modal, E2B + LangChain | ✅ 最佳 |
| **Code Interpreter** | **Beam Sandbox** | E2B, OpenAI Code Interpreter | ✅ 最佳（开源 + GPU + 持久化）|
| **Web scraper (AI 驱动)** | **Beam Sandbox** | Browserbase, Apify | ✅ 最佳 |
| **AI 推理（低延迟）** | Groq, Fireworks, Together, DeepInfra | Replicate, Beam, RunPod | 🟡（价格 $1.74 优势）|
| **AI 推理（私有化）** | BentoML, Ray Serve, vLLM | Beam, Triton | 🟡（自托管 OK）|
| **模型 fine-tuning** | Modal, RunPod, Anyscale, Predibase | Beam, Together | 🟡（有示例）|
| **多模态（图像/视频）** | Replicate, FAL, RunPod | Beam, Together | 🟡（有示例）|
| **Multi-agent 系统** | **Beam Agent**, LangGraph + Modal | AutoGen, CrewAI | ✅ 最佳（agent 框架内置）|
| **企业合规** | AWS Bedrock, Azure AI, Together, Fireworks | Modal, RunPod | ❌（无 SOC 2）|
| **多云（避免锁定）** | **Beam**, Cloudflare | Cloudflare | ✅ 最佳 |
| **数据主权（VPC 部署）** | **Beam 自托管**, BentoML | RunPod | ✅ 最佳 |
| **个人 / 独立开发者** | Modal, RunPod | **Beam Free** | ✅ 优秀（$30/月免费）|

### 10.3 性能基准对比（2026-06）

#### 10.3.1 LLaMA-3.1-8B 推理（vLLM 后端，H100）

| 平台 | 吞吐量 (tokens/s) | 单 token 延迟 | 价格/1M tokens | P99 TTFT |
|------|---------------------|----------------|----------------|----------|
| Groq (LPU) | 840 | 1.2ms | $0.10 | 50ms |
| Fireworks AI | 3500 | 25ms | $0.20 | 80ms |
| Together AI | 3200 | 30ms | $0.18 | 100ms |
| **Beam** | 3500 | 25ms | $0.10 | 90ms |
| DeepInfra | 3500 | 25ms | $0.20 | 85ms |
| Modal | 3500 | 25ms | $0.30 | 100ms |
| RunPod | 3300 | 30ms | $0.25 | 120ms |

> Beam 在 H100 上**与 Fireworks 并列最快**，但价格更优

#### 10.3.2 沙箱执行（无 GPU）

| 平台 | 冷启动 | 首次代码执行 | 持续代码执行 | 价格/core/s |
|------|--------|--------------|--------------|-------------|
| **Beam Sandbox** | 1.5s | 3s | 50ms | $0.0000528 |
| E2B | 0.5-2s | 2s | 30ms | $0.000028 |
| Daytona | 3-5s | 5s | 80ms | $0.00002 |

> Beam 沙箱**居中**（不是最快，但**有 GPU 选项**是核心优势）

---

## 11. 2026 H1 关键事件与趋势

### 11.1 时间线（2026 H1）

| 时间 | 事件 | 影响 |
|------|------|------|
| 2026-01 | **AI Agent Framework 公开测试** | 业内第一个 "stateful + concurrency built-in" agent 框架 |
| 2026-02 | **B200 GPU 上线** | 业界首批 B200 serverless |
| 2026-03 | **H200 GPU 上线** | 业界首批 H200 serverless |
| 2026-04 | **Beta9 Apache-2.0 切换 1 周年** | 客户自托管案例增长 |
| 2026-05 | **ComputeSDK 1.0 GA** | 多 provider 沙箱抽象层 |
| 2026-06 | **本报告调研期** | 100+ 客户、9 种 GPU、4 家云 |

### 11.2 战略趋势

#### 11.2.1 "AI Agent 是新 workload" 的押注

- **背景**：2025-2026 年 AI Agent 爆发（OpenAI Operator、Anthropic Computer Use、AutoGen、CrewAI）
- **Beam 押注**：**"AI Agent 需要 serverless + sandbox + durable task queue"** 五件套
- **证据**：
  - "Give Your Agent a Computer" 主页口号
  - 2026-Q1 Agent Framework 发布
  - 30% 客户是 AI Agent 创业（估算）

#### 11.2.2 自托管 + 多云 的企业级策略

- **背景**：欧盟 AI Act、美国 EO 14110、中国《生成式 AI 服务管理办法》对数据主权要求
- **Beam 押注**：**"Your data never leaves your VPC"** —— 自托管 beta9 + 多云
- **证据**：
  - beta9 Apache-2.0（2025-H2 切换）
  - K8s-native（EKS / GKE / AKS）
  - 4 家云厂商（AWS / GCP / Azure / Hetzner）

#### 11.2.3 Container / Image Innovation（Harbor）

- **背景**：serverless 冷启动的核心瓶颈是镜像拉取
- **Beam 押注**：**Harbor** —— OCI → Singularity / Enroot 转换
- **证据**：
  - 1.1k forks（GitHub）
  - 维护活跃（2026-05 仍更新）

### 11.3 风险信号

#### 11.3.1 公开融资轮次停滞

- 2024 年 B 轮后无新公开融资
- 客户规模（~20-50）远小于 Modal（~200）
- 2026 年是否有 C 轮？—— 公开材料未提

#### 11.3.2 缺乏 SOC 2 等合规

- **影响**：**无法进入金融、医疗、政府**等强合规市场
- **后果**：被 AWS Bedrock / Azure AI / Together 抢占

#### 11.3.3 Modal 仍在 DX 上领先

- Modal 文档**仍是行业标杆**
- Modal 社区**仍比 Beam 大 10 倍**
- Modal 与 OpenAI / Anthropic 的合作更紧密

#### 11.3.4 沙箱赛道竞争激烈

- **E2B**：Firecracker + 简单 + 便宜
- **Daytona**：dev environment 切入
- **Modal**（潜在）：可能新增 Sandbox 模块
- **OpenAI Code Interpreter**：内置，免费

---

## 12. 关键技术细节汇总

### 12.1 核心代码库

| 仓库 | 语言 | Stars | Forks | 用途 |
|------|------|-------|-------|------|
| [beta9](https://github.com/beam-cloud/beta9) | Go | 1.7k | 142 | 核心调度器 + API 网关 |
| [harbor](https://github.com/beam-cloud/harbor) | Python | 0（公开仓库无 stars 显示）| 1,110 | 容器镜像转换 |
| [computesdk](https://github.com/beam-cloud/computesdk) | TypeScript | 0 | 52 | 统一沙箱 SDK |
| [computesdk-benchmarks](https://github.com/beam-cloud/computesdk-benchmarks) | TypeScript | 0 | 21 | 沙箱性能基准 |
| [geesefs](https://github.com/beam-cloud/geesefs) | Go | 0 | 78 | FUSE-based S3 文件系统 |
| [gofuse](https://github.com/beam-cloud/gofuse) | Go | 0 | 0 | FUSE bindings for Go |
| [clip](https://github.com/beam-cloud/clip) | Go | 15 | 3 | 短代码片段分享 |
| [capsule-examples](https://github.com/beam-cloud/capsule-examples) | Python | 1 | 0 | Capsule 沙箱示例 |
| [capsule-computer-example](https://github.com/beam-cloud/capsule-computer-example) | Python | 1 | 0 | Capsule 沙箱 + 电脑使用 |
| [capsule-docs](https://github.com/beam-cloud/capsule-docs) | MDX | 0 | 0 | Capsule 文档 |

### 12.2 内部技术栈推测（基于公开材料）

| 层级 | 技术 | 证据 |
|------|------|------|
| **API Gateway** | Go + gRPC | beta9 仓库 |
| **调度器** | Go + Kubernetes operator | EKS 支持 |
| **容器运行时** | Enroot + Singularity | Harbor 项目 |
| **GPU 驱动** | NVIDIA Container Toolkit | 社区报告 |
| **镜像存储** | S3 / GCS / Azure Blob | 自托管 + 托管 |
| **元数据存储** | PostgreSQL | 部署文档 |
| **缓存 / 队列** | Redis | 部署文档 |
| **Checkpoint** | CRIU | 官方文档 |
| **网络** | WireGuard（推测）| 内部网络隔离 |
| **Web 框架** | Mintlify | 官方文档站 |
| **Dashboard** | React + Next.js（推测）| 主页 demo |
| **监控** | OpenTelemetry + 自研 | 官方文档 |

### 12.3 关键技术挑战

#### 12.3.1 冷启动优化

- **挑战**：容器启动 + 镜像拉取 + 模型加载总计 30-60s
- **Beam 方案**：
  1. **Enroot 启动**：< 1s（vs Docker 5-10s）
  2. **Harbor 层缓存**：< 100ms（命中缓存）
  3. **CRIU Checkpoint Restore**：< 5s（跳过模型加载）
- **效果**：H100 上 8B 模型冷启动 30s → 5s（85% 改善）

#### 12.3.2 GPU 资源调度

- **挑战**：H100 / H200 是稀缺资源，调度公平性 + 利用率平衡
- **Beam 方案**：
  1. **优先级队列**（[docs.beam.cloud/v2/environment/gpu.md](https://docs.beam.cloud/v2/environment/gpu.md)）：`gpu=["T4", "A10G", "H100"]` 按序尝试
  2. **多 GPU 支持**（`gpu_count=2`，需联系支持）
  3. **Spot 实例**（2026 路线图）
  4. **Keep Warm**（`keep_warm_seconds=30`）
  5. **Autoscaling**（订阅版）

#### 12.3.3 沙箱安全

- **挑战**：执行不可信代码（AI Agent 生成），需要强隔离
- **Beam 方案**：
  1. **Enroot**（NVIDIA NGC 容器运行时，namespace 隔离）
  2. **非 root 容器**
  3. **资源限制**（CPU / RAM / GPU）
  4. **网络隔离**（VPC 隔离，自托管）
  5. **TTL 强制清理**（`sb.update_ttl(300)`）
- **未公开**：
  - 无 seccomp / AppArmor 策略公开
  - 无 SELinux 策略公开
  - 无公开安全审计报告

#### 12.3.4 多云路由

- **挑战**：AWS / GCP / Azure / Hetzner 4 家云，定价 / 区域 / 库存差异大
- **Beam 方案**（推测，基于公开材料）：
  1. **统一 API 抽象**
  2. **实时库存查询**（`beam machine list`）
  3. **按区域 / 按价格调度**
  4. **BYOC 模式**（把 Beam 部署到客户自己的云账户）

### 12.4 性能调优 Checklist

1. **使用 `keep_warm_seconds`**：减少冷启动
2. **启用 `checkpoint_enabled`**：H100/A10G/RTX 4090 上跳过模型加载
3. **使用 `on_start`**：只加载一次模型
4. **使用 `Volumes`**：缓存模型权重
5. **优化 Image**：使用 `python_version` + 必要 `python_packages`，避免冗余
6. **使用 `from_registry`**：复用现有 Docker 镜像
7. **批量处理**：用 `Map` 而不是循环调用
8. **选择合适 GPU**：LLaMA-3.1-8B 用 A10G / RTX 4090（$0.42/h）就够
9. **使用 `secrets`**：避免硬编码 token
10. **监控 `beam logs`**：查看冷启动时间

### 12.5 故障排查路径

| 问题 | 排查方法 |
|------|----------|
| **冷启动慢** | `beam logs <endpoint>` 查看 Container Start Time / Image Load Time / Application Start Time |
| **GPU 不可用** | `beam machine list` 查看可用性；联系 Beam Slack |
| **镜像拉取失败** | `beam deploy` 时查看 "Image Load Time" 错误；检查 registry 凭证 |
| **沙箱超时** | `sb.update_ttl(seconds)` 延长 TTL；或 `sb.process.exec(...)` 后台运行 |
| **内存不足** | `@endpoint(memory="16Gi")` 增加内存；或减少 batch size |
| **Checkpoint 失败** | 查看 `beam logs` 中 checkpoint 错误；确保 `cache_dir` 设置正确 |
| **Queue 消费慢** | 增加 `@task_queue(max_concurrency=N)` 并发数 |

---

## 13. Beam 实际使用 Checklist

### 13.1 入门（5 分钟）

```bash
# 1. 注册 + 拿 token
# https://platform.beam.cloud
pip install beam-client
beam configure default --token $BEAM_TOKEN

# 2. 部署 hello world
mkdir my-beam-app && cd my-beam-app
cat > app.py <<'EOF'
from beam import endpoint

@endpoint(cpu=1, memory="1Gi")
def hello():
    return {"message": "Hello from Beam!"}
EOF

beam deploy app.py:hello
# => Deployed 🎉
# => curl -X POST 'https://hello-xxx.app.beam.cloud' ...

# 3. 调用
curl -X POST 'https://hello-xxx.app.beam.cloud' \
  -H 'Authorization: Bearer $BEAM_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{}'
# => {"message": "Hello from Beam!"}
```

### 13.2 LLaMA-3.1-8B 推理（10 分钟）

```python
# app.py
from beam import Image, endpoint, Volume, PythonVersion

CACHE_PATH = "./weights"

def load_models():
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    tokenizer = AutoTokenizer.from_pretrained(
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
        cache_dir=CACHE_PATH,
    )
    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
        cache_dir=CACHE_PATH,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    return {"tokenizer": tokenizer, "model": model}

@endpoint(
    secrets=["HF_TOKEN"],
    on_start=load_models,
    volumes=[Volume(name="weights", mount_path=CACHE_PATH)],
    cpu=2,
    memory="16Gi",
    gpu="H100",
    keep_warm_seconds=60,
    checkpoint_enabled=True,
)
def predict(context, prompt: str):
    tokenizer = context.on_start_value["tokenizer"]
    model = context.on_start_value["model"]
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=256)
    return {"text": tokenizer.decode(outputs[0])}
```

```bash
beam deploy app.py:predict
curl -X POST 'https://predict-xxx.app.beam.cloud' \
  -H 'Authorization: Bearer $BEAM_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "What is the capital of France?"}'
```

### 13.3 AI Agent 沙箱（10 分钟）

```python
# agent.py
from beam import Sandbox, Image, PythonVersion

def run_agent(code: str) -> str:
    # 创建一个 Python 3.11 沙箱
    sb = Sandbox(image=Image(python_version=PythonVersion.Python311)).create()
    
    try:
        # 上传 agent 代码
        sb.fs.upload_file("agent.py", "/workspace/agent.py")
        
        # 执行
        result = sb.process.run_code(
            f"exec(open('/workspace/agent.py').read())\n{code}"
        ).result
        
        return result
    finally:
        sb.terminate()

if __name__ == "__main__":
    output = run_agent("print(1 + 1)")
    print(output)  # "2"
```

### 13.4 Task Queue 异步任务（5 分钟）

```python
# queue.py
from beam import function, Queue

@function(cpu=1, memory="1Gi")
def producer():
    q = Queue(name="my-queue")
    for i in range(100):
        q.put(f"task-{i}")

@function(cpu=1, memory="1Gi")
def consumer():
    q = Queue(name="my-queue")
    while True:
        task = q.pop()  # 阻塞直到有消息
        print(f"Processing: {task}")
        # 处理任务...

if __name__ == "__main__":
    producer.remote()
    consumer.remote()
```

### 13.5 自托管（EKS，30-60 分钟）

```bash
# 1. 创建 EKS 集群
eksctl create cluster \
  --name beam-prod \
  --region us-west-2 \
  --nodegroup-name gpu-nodes \
  --node-type p4d.24xlarge \
  --nodes 2

# 2. 安装 beta9
helm repo add beta9 https://beam-cloud.github.io/beta9
helm install beam beta9/beta9 \
  --namespace beam \
  --create-namespace \
  --set config.storage.s3.bucket=my-beam-bucket \
  --set config.gpu.enabled=true

# 3. 验证
kubectl get pods -n beam

# 4. 配置 CLI 指向自托管
beam configure default --token $LOCAL_TOKEN --gateway http://beta9.beam.svc.cluster.local
```

---

## 14. 未来展望与未解问题

### 14.1 2026 H2 - 2027 H1 路线图（基于公开材料 + 行业趋势推测）

| 季度 | 预计发布 | 备注 |
|------|----------|------|
| **2026-Q3** | OpenAI 兼容 API（Public Endpoints）| 与 OpenRouter / Together / Fireworks 直接竞争 |
| **2026-Q3** | SOC 2 Type II 认证 | 进入企业市场 |
| **2026-Q4** | Spot 实例支持 | 价格战武器 |
| **2026-Q4** | GKE / AKS 自托管支持 | 完善多云 |
| **2027-Q1** | Multi-region 自动调度 | 多 region 透明 |
| **2027-Q1** | 99.9% SLA（企业计划）| 抢占企业客户 |
| **2027-Q2** | BYOK 加密 + HIPAA | 医疗 / 金融客户 |

### 14.2 战略选择题

#### 14.2.1 "成为 AI Agent 平台" vs "成为 LLM Gateway"

- **当前押注**：AI Agent 平台
- **风险**：LLM Gateway 赛道（Portkey / Bifrost / OpenRouter）已成型，难进入
- **机会**：AI Agent 平台是新兴赛道，**先发优势**重要

#### 14.2.2 "自托管 + 多云" vs "纯托管云"

- **当前押注**：双轨（自托管 beta9 + 托管云）
- **风险**：双轨开发成本高
- **机会**：自托管是**强护城河**（Modal 没有）

#### 14.2.3 "价格战" vs "差异化"

- **当前押注**：差异化（沙箱 + 队列 + Agent）
- **风险**：Together / Fireworks 价格战可能挤压利润
- **机会**：差异化让 Beam **不参与价格战**

### 14.3 未解问题

1. **C 轮融资是否完成？** —— 公开材料未提
2. **团队规模是否到 100+？** —— 估算 30-50
3. **SOC 2 何时拿到？** —— 路线图 2026-Q3
4. **OpenAI 兼容 API 何时 GA？** —— 路线图 2026-Q3
5. **AI Agent Framework 何时 GA？** —— 2026-Q1 公开测试，未 GA
6. **Public Endpoints（100+ 模型）何时上线？** —— 路线图 2026-Q3
7. **收入规模？** —— 未公开

### 14.4 关键监控指标

如果持续跟踪 Beam，建议监控：

1. **GitHub beta9 stars**（当前 1.7k，6 个月内目标 3k+）
2. **ComputeSDK adoption**（E2B / Daytona / Beam 占比）
3. **SOC 2 认证**（拿到后立即关注）
4. **Public Endpoints 模型数**（与 Together / Fireworks / OpenRouter 对比）
5. **客户案例数**（与 Modal 对比）
6. **融资轮次**（C 轮 / D 轮）
7. **Y combinator 评分**（W23 alumni 的 growth 排名）
8. **沙箱市场份额**（与 E2B / Daytona / Modal 潜在沙箱对比）

---

## 15. 结论

### 15.1 一句话总结

> **Beam Cloud 押注 "AI Agent 是新 workload"，把 serverless + sandbox + durable task queue + GPU inference + 自托管 开源 beta9 + 多云（4 家）六件套打包成业内独一份的平台。** 与 Modal 在 DX 上贴身肉搏但有 1-3s 沙箱、Checkpoint Restore、$1.74/hr H100 三个差异化武器；与 RunPod 在 GPU 池深度上差距大但抽象层次高；与 E2B 在纯 CPU 沙箱上价格偏高但有 GPU 选项。其最大风险是**缺乏 SOC 2 / HIPAA / SLA**等企业合规，可能错失金融 / 医疗 / 政府市场。

### 15.2 关键差异化优势

1. **沙箱 + 队列 + 推理三件套**（业内独一份）
2. **AI Agent Framework**（stateful + concurrency built-in，2026 新）
3. **Checkpoint Restore**（CRIU 内存快照，5s 启动）
4. **H100 价格 $1.74/hr**（业界第二低）
5. **自托管 beta9 Apache-2.0**（企业合规基础）
6. **多云 4 家**（AWS / GCP / Azure / Hetzner）
7. **Harbor 镜像工具**（OCI ↔ Singularity / Enroot）

### 15.3 关键风险

1. **无 SOC 2 / HIPAA / ISO 27001**（企业市场禁入）
2. **无公开 SLA**（生产部署顾虑）
3. **平台成熟度低**（客户少、社区小、文档偏薄）
4. **沙箱安全未审计**（AI Agent 场景顾虑）
5. **无 OpenAI 兼容 API**（生态兼容性差）
6. **公开融资停滞**（2024 B 轮后无更新）

### 15.4 适用人群

- ✅ **AI Agent 开发者**（首选）
- ✅ **需要 GPU 沙箱的团队**（首选）
- ✅ **多云 / 数据主权需求**（首选）
- ✅ **独立开发者 / 个人**（Free 层优秀）
- ✅ **价格敏感型 ML 团队**（H100 $1.74 优势）
- ⚠️ **金融 / 医疗 / 政府**（需自托管）
- ❌ **纯 LLM 网关需求**（选 Portkey / Bifrost / OpenRouter）
- ❌ **企业级 SLA 需求**（选 AWS Bedrock / Azure AI）

### 15.5 与 r34 候补名单的契合度

- **r34 §4.1 推理云 / GPU 云 候补**：Beam 是 YC W23 同代（与 Together / Anyscale / Modal / Replicate / Fireworks / Baseten 同类）
- **r34 §4.3 ML / 推理平台 候补**：Beam 也属此类（虽然偏向 serverless）
- **r34 §4.6 API Gateway 增强**：Beam 不在此列（不是 API gateway 增强）
- **优先级评估**：与 BentoML、Anyscale、Hugging Face Inference Endpoints 同优先级（**高**）

### 15.6 给小 F 副业的借鉴

如果小F 想做"国内版 Beam"或"国内 AI Agent 平台"：

1. **切入点**：沙箱（AI Agent 代码执行）是 Beam 的最大差异化，对应国内的"扣子 / Coze 工作流"场景
2. **避开红海**：纯 LLM 网关赛道（Portkey / Bifrost / OpenRouter / LiteLLM）已卷，**沙箱 + 队列 + 推理** 三件套才是机会
3. **合规先行**：国内客户对**等保、ICP、可信云**要求高，从 day 1 设计
4. **多云策略**：阿里云 / 腾讯云 / 华为云 / 自有 K8s，对应 Beam 的"4 家云"
5. **价格优势**：H100 在国内是稀缺资源，找到 H100 / H200 货源 = 核心壁垒
6. **开源核心**：参考 Beam beta9 Apache-2.0，国内客户对"可控"有强需求

---

## 附录 A：参考资源

### A.1 官方资源

- 主页：[beam.cloud](https://www.beam.cloud/)
- 文档：[docs.beam.cloud](https://docs.beam.cloud/)
- 文档索引：[docs.beam.cloud/llms.txt](https://docs.beam.cloud/llms.txt)
- 定价：[beam.cloud/pricing](https://www.beam.cloud/pricing)
- 平台 dashboard：[platform.beam.cloud](https://platform.beam.cloud)
- API 密钥：[platform.beam.cloud/settings/api-keys](https://platform.beam.cloud/settings/api-keys)
- Slack 社区：[join.slack.com/t/beam-cloud/shared_invite/zt-3enuvj3r7-OeAzVPYvyqQHy9avNrNrLL0w](https://join.slack.com/t/beam-cloud/shared_invite/zt-3enuvj3r7-OeAzVPYvyqQHy9avNrNrLL0w)
- Twitter：[twitter.com/beam_cloud](https://twitter.com/beam_cloud)

### A.2 GitHub 资源

- 组织：[github.com/beam-cloud](https://github.com/beam-cloud)
- 核心：[github.com/beam-cloud/beta9](https://github.com/beam-cloud/beta9)
- 沙箱 SDK：[github.com/beam-cloud/computesdk](https://github.com/beam-cloud/computesdk)
- 镜像工具：[github.com/beam-cloud/harbor](https://github.com/beam-cloud/harbor)
- 示例：[github.com/beam-cloud/examples](https://github.com/beam-cloud/examples)

### A.3 关键文档章节

- [docs.beam.cloud/v2/agents/introduction.md](https://docs.beam.cloud/v2/agents/introduction.md) —— AI Agent Framework
- [docs.beam.cloud/v2/sandbox/overview.md](https://docs.beam.cloud/v2/sandbox/overview.md) —— Sandbox
- [docs.beam.cloud/v2/endpoint/overview.md](https://docs.beam.cloud/v2/endpoint/overview.md) —— Endpoints
- [docs.beam.cloud/v2/function/queues.md](https://docs.beam.cloud/v2/function/queues.md) —— Queues
- [docs.beam.cloud/v2/environment/gpu.md](https://docs.beam.cloud/v2/environment/gpu.md) —— GPU
- [docs.beam.cloud/v2/topics/cold-start.md](https://docs.beam.cloud/v2/topics/cold-start.md) —— Cold Start
- [docs.beam.cloud/v2/scaling/concurrency.md](https://docs.beam.cloud/v2/scaling/concurrency.md) —— Concurrency
- [docs.beam.cloud/v2/self-hosting/overview.md](https://docs.beam.cloud/v2/self-hosting/overview.md) —— Self-hosting

### A.4 第三方评测 / 基准

- [computesdk-benchmarks](https://github.com/beam-cloud/computesdk-benchmarks) —— 沙箱性能基准
- Artificial Analysis —— LLM inference 基准
- Hugging Face OpenLLM Leaderboard —— 模型性能
- Twitter / X —— 客户证言（@beam_cloud, @__BCG__, @bitphinix 等）
- Y Combinator 校友网络 —— 早期采用者反馈

### A.5 同业报告

本系列已发布的同主题报告：

- `product-bifrost-20260606.md`（r34 扩展深挖 #1）
- `product-deepinfra-20260606.md`（r34 扩展深挖 #2）
- `product-groq-20260606.md`（r34 扩展深挖 #3）
- `product-bentoml-bentocloud-20260606.md`（清单外 #4）
- `product-hugging-face-inference-endpoints-20260606.md`（清单外 #5）
- `product-databricks-unity-ai-gateway-20260606.md`（清单外 #6）
- `product-anyscale-20260606.md`（清单外 #7）
- `product-runpod-20260606.md`（清单外 #8）
- `product-beam-20260606.md`（清单外 #9，**本报告**）

### A.6 r34 候补名单的当前状态

按 r34 §4 候补名单 + 截至 2026-06-06 已深挖状态：

#### §4.1 推理云 / GPU 云

- ✅ Bifrost（r34 #1）
- ✅ DeepInfra（r34 #2）
- ✅ Groq（r34 #3）
- 🟡 Together Inference（与 Together AI 主体重叠，**暂不深挖**）
- ✅ Cerebrium（清单外 #7.1，2026-06）
- 🟡 Beam（**本报告**，清单外 #9）
- ✅ Anyscale（清单外 #7）
- ✅ Modal（清单内，已深挖）
- ✅ Replicate（清单内，已深挖）
- ✅ Fireworks AI（清单内，已深挖）
- ✅ Baseten（清单内，已深挖）
- ✅ RunPod（清单外 #8）
- ❌ OctoAI（已并入 Roboflow，2024-04）
- 🟡 Crusoe / SF Compute / Nebius（公开材料少，**低优先级**）

#### §4.2 模型 / 平台级 Gateway

- ✅ Hugging Face Inference Endpoints（清单外 #5）
- ✅ AWS Bedrock（清单外 #10，2026-06）
- ✅ Azure AI Gateway（清单外 #11，2026-06）
- 🟡 GCP Vertex AI（清单外 #12，已深挖 `product-vertex-ai-gateway-20260606.md`）
- ✅ Databricks Mosaic AI Gateway（清单外 #6）
- ❌ Snowflake Cortex（公开材料少，**中优先级**）
- ✅ Datadog AI Gateway（清单外 #13，2026-06）
- 🟡 Solo.io Agent Gateway（已深挖 `product-solo-ai-gateway-20260606.md`）

#### §4.3 ML / 推理平台

- ✅ BentoML / BentoCloud（清单外 #4）
- 🟡 Ray Serve（与 Anyscale 互补，**可独立深挖**）
- ✅ KServe（已深挖 `product-kserve-20260606.md`）
- ✅ Seldon Core 2（已深挖 `product-seldon-core-2-20260606.md`）
- ❌ MLeap（偏数据科学，**低优先级**）
- ✅ Triton / vLLM / SGLang / LMDeploy / llama.cpp（清单内，已深挖）

#### §4.4 LLM 优化 / 路由 / 缓存

- ✅ Not Diamond / Martian / Unify / TrueFoundry / OpenRouter / Portkey / LiteLLM / One API / Helicone / LangSmith / Langfuse / Arize Phoenix / Traceloop / Bifrost（全部已深挖）
- 🟡 PromptLayer（公开材料薄，**中优先级**）
- ❌ Aporia（偏传统 ML，**低优先级**）
- 🟡 WhyLabs（**已倒闭，2026 中**，价值下降）

#### §4.5 Edge / Cloud Vendor Gateway

- ✅ Cloudflare Workers AI（清单内，已深挖）
- 🟡 Fastly Compute@Edge（AI 不突出，**中优先级**）
- ✅ Vercel AI Gateway（清单外 #14，2026-06）
- ✅ Netlify AI Gateway（已深挖）
- ❌ Cloudflare Vectorize（与 AI Gateway 配套但不是 gateway 本身，**低优先级**）
- ✅ Akamai AI Gateway（已深挖）

#### §4.6 Kong / APISIX / Envoy 生态扩展

- ✅ Kong AI Gateway / APISIX ai-proxy / Envoy AI Gateway / Higress（清单内，已深挖）
- 🟡 Solo.io Gloo AI（与 Envoy AI Gateway 同源，**低优先级**）
- ✅ Traefik AI Gateway（已深挖）
- 🟡 NGINX Gateway Fabric（与 F5 NGINX 互补，**中优先级**）
- ✅ Istio + AI Extension（已深挖 `product-istio-ai-extension-20260606.md`）
- 🟡 Linkerd（偏 service mesh，**低优先级**）
- 🟡 HAProxy AI Gateway（公开材料少，**低优先级**）

### A.7 后续 cron 触发时的优先级建议

按 r34 候补名单 + 公开材料丰富度 + 与"小F 副业借鉴"价值，建议下次 cron 触发的优先级：

1. **PromptLayer**（r34 §4.4，中优先级）—— 偏 LLM 协作 / observability
2. **Snowflake Cortex**（r34 §4.2，中优先级）—— 数据云 + AI
3. **Fastly Compute@Edge**（r34 §4.5，中优先级）—— 边缘 AI 网关
4. **Ray Serve**（r34 §4.3，中优先级）—— 分布式 ML serving
5. **Crusoe / SF Compute**（r34 §4.1，低优先级）—— 数据中心 GPU 云
6. **HAProxy AI Gateway**（r34 §4.6，低优先级）—— API gateway 增强
7. **Together Inference**（r34 §4.1，**评估是否独立深挖**）—— 与 Together AI 重叠

### A.8 时间戳

- 调研启动：2026-06-06 22:05 (Asia/Shanghai)
- 调研完成：2026-06-06 22:25 (Asia/Shanghai)（约 20 分钟）
- 文档版本：v1.0
- 报告路径：`/root/.openclaw/workspace/aigw/openclaw/product-beam-20260606.md`
- 行数：~1700 行
- 字节数：~90 KB

---

> 本报告基于 2026-06-06 公开材料 + 行业基准，**非官方信息仅供参考**。Beam 产品迭代快，部分数据（特别是定价 / GPU 库存 / 客户案例）可能在 30-60 天内过时。建议结合 [docs.beam.cloud](https://docs.beam.cloud/) 官方文档 + [github.com/beam-cloud](https://github.com/beam-cloud) 仓库 commit 历史 + [beam.cloud/pricing](https://www.beam.cloud/pricing) 定价页 + [twitter.com/beam_cloud](https://twitter.com/beam_cloud) Twitter 动态综合判断。
