# 开源贡献与社区治理：AI Gateway 项目的可持续生态

> 系列：AI Gateway 持续深挖 · 第 2 批 · 第 5 篇
> 性质：纯技术研究
> 范围：开源 AI Gateway 项目的贡献者生态、社区治理、可持续性、治理结构演化

---

## 目录

- [一、AI Gateway 开源生态现状](#一ai-gateway-开源生态现状)
- [二、贡献者画像](#二贡献者画像)
- [三、贡献者成长路径](#三贡献者成长路径)
- [四、治理模式详解](#四治理模式详解)
- [五、典型项目治理对比](#五典型项目治理对比)
- [六、开源许可协议选择](#六开源许可协议选择)
- [七、社区健康度评估](#七社区健康度评估)
- [八、维护者工作](#八维护者工作)
- [九、贡献者激励机制](#九贡献者激励机制)
- [十、企业与个人贡献的协同](#十企业与个人贡献的协同)
- [十一、开源可持续性挑战](#十一开源可持续性挑战)
- [十二、未解难题与研究前沿](#十二未解难题与研究前沿)
- [十三、参考资料](#十三参考资料)

---

## 一、AI Gateway 开源生态现状

### 1.1 主流项目概览

| 项目 | Stars | 贡献者 | License | 公司背书 |
|---|---|---|---|---|
| **LiteLLM** | 22k+ | 500+ | MIT | BerriAI |
| **Portkey** | 6k+ | 100+ | MIT | Portkey AI |
| **One API** | 18k+ | 200+ | MIT | 个人 |
| **Higress** | 5k+ | 100+ | Apache 2.0 | 阿里云 |
| **vLLM** | 30k+ | 800+ | Apache 2.0 | Anyscale / 学术 |
| **SGLang** | 11k+ | 200+ | Apache 2.0 | LMSYS / 学术 |
| **TGI** | 9k+ | 200+ | Apache 2.0 | HuggingFace |
| **Kong** | 39k+ | 400+ | Apache 2.0 | Kong Inc. |
| **APISIX** | 14k+ | 500+ | Apache 2.0 | API7 |
| **Triton** | 9k+ | 200+ | BSD-3 | NVIDIA |
| **OpenLLMetry** | 1k+ | 50+ | Apache 2.0 | Traceloop |
| **LangChain** | 90k+ | 3000+ | MIT | LangChain Inc. |

### 1.2 贡献者来源

```
贡献者构成
├── 公司雇员（50-70%）
│     ├── 全职做该项目
│     ├── 部分时间贡献
│     └── 通过雇主赞助
├── 个人贡献者（20-30%）
│     ├── 业余时间
│     ├── 求职需要
│     └── 个人兴趣
├── 学术界（5-15%）
│     ├── 论文相关
│     └── 学生项目
└── 承包商 / 顾问（5-10%）
```

### 1.3 贡献类型分布

```
PR 类型
├── Bug 修复（30-40%）
├── 新功能（20-30%）
├── 文档（10-15%）
├── 测试（5-10%）
├── 重构（5-10%）
└── 性能优化（5-10%）
```

---

## 二、贡献者画像

### 2.1 三类典型贡献者

#### 类型 A：核心维护者（Maintainer）

**特点**：
- 项目所有者或核心团队
- 投入大量时间
- 有最终决策权
- 通常有公司背景

**例子**：
- BerriAI 团队（LiteLLM）
- LangChain 团队（LangChain）
- 阿里云团队（Higress）
- HuggingFace 团队（TGI）

**动机**：
- 公司业务需要
- 行业影响力
- 招聘 / 品牌

#### 类型 B：常规贡献者（Contributor）

**特点**：
- 长期贡献
- 熟悉代码
- 但无最终决策权
- 可能是公司雇员

**例子**：
- vLLM 的众多贡献者
- LiteLLM 社区活跃成员

**动机**：
- 解决自己用项目时遇到的问题
- 行业声誉
- 学习

#### 类型 C：偶发贡献者（One-time）

**特点**：
- 提交 1-2 个 PR
- 通常是 bug 修复或小功能
- 不深入参与

**动机**：
- 用项目时遇到问题
- 公司要求
- 求职加分

### 2.2 贡献者地理分布

```
主要贡献地区（粗估）
├── 美国 30-40%
├── 中国 20-30%
├── 欧洲 15-20%
├── 印度 10-15%
└── 其他 5-10%
```

### 2.3 贡献者技能画像

| 技能 | 占比 |
|---|---|
| **Python** | 60-70% |
| **Go** | 20-30% |
| **TypeScript** | 20-30% |
| **Rust** | 5-10% |
| **C++** | 5-10% |
| **云 / DevOps** | 30-40% |
| **ML / AI 知识** | 70-80% |

---

## 三、贡献者成长路径

### 3.1 路径模型

```
Stage 0: 用户（User）
  │ 用项目，遇到问题
  ↓
Stage 1: 提问者（Asker）
  │ 提 Issue、问问题
  ↓
Stage 2: 文档贡献者（Doc Contributor）
  │ 修文档、改进例子
  ↓
Stage 3: Bug 修复者（Bug Fixer）
  │ 修小 bug、提小 PR
  ↓
Stage 4: 功能贡献者（Feature Contributor）
  │ 实现新功能
  ↓
Stage 5: 评审者（Reviewer）
  │ 评审他人 PR
  ↓
Stage 6: 维护者（Maintainer）
  │ 项目核心成员
  ↓
Stage 7: 项目领导者（Project Lead）
  │ 战略决策
```

### 3.2 关键转化点

#### 从用户 → 提问者

**触发**：
- 遇到问题
- 找不到答案
- 项目 issue 区不活跃

**加速器**：
- 友好欢迎新人的文化
- 完善的 issue 模板
- Slack / Discord 社区

#### 从提问者 → 文档贡献者

**触发**：
- 发现文档错误
- 想要更好的例子

**加速器**：
- "Good first issue" 标签
- 文档贡献指南
- 自动构建预览

#### 从文档 → Bug 修复

**触发**：
- 调试时发现简单 bug
- 修个小问题不复杂

**加速器**：
- 标注 "good first issue" 的 bug
- 详细的 bug 报告
- 开发环境文档

#### 从 Bug → 功能

**触发**：
- 想要项目没实现的功能
- 提 RFC（Request for Comments）

**加速器**：
- RFC 流程
- 设计文档评审
- 导师制度

#### 从功能 → 维护者

**触发**：
- 长期贡献
- 获得其他维护者信任

**加速器**：
- 透明的晋升流程
- 多种贡献认可方式
- 维护者津贴（如果有）

### 3.3 贡献者流失的常见原因

| 原因 | 占比（行业经验） |
|---|---|
| **工作变化** | 30% |
| **失去兴趣** | 20% |
| **沟通冲突** | 15% |
| **维护负担** | 15% |
| **公司方向改变** | 10% |
| **其他** | 10% |

---

## 四、治理模式详解

### 4.1 三种主要治理模式

#### 模式 A：独裁（Benevolent Dictator）

```
创始人 / 主导公司
    ↓ 决策
贡献者
```

**代表**：
- LiteLLM（创始团队）
- One API（个人项目）
- LangChain（Harrison Chase 主导）

**优点**：
- 决策快
- 方向一致

**缺点**：
- 单点失败
- 可能脱离社区

#### 模式 B：公司主导（BDFL + 公司）

```
公司核心团队
    ↓ 决策
外部贡献者
```

**代表**：
- Portkey
- Helicone
- TrueFoundry

**优点**：
- 资源充足
- 长期稳定

**缺点**：
- 可能不中立
- 商业压力

#### 模式 C：基金会（Foundation-led）

```
基金会（如 Linux Foundation、CNCF）
    ↓ 治理
TSC（技术指导委员会）
    ↓ 决策
贡献者
```

**代表**：
- vLLM（Anyscale 主导，但尝试中立化）
- SGLang（LMSYS 主导）
- TGI（HuggingFace 主导）
- Higress（阿里云主导，但已捐给 CNCF 候选）

**优点**：
- 中立
- 治理透明

**缺点**：
- 决策慢
- 需要协调

### 4.2 治理的具体内容

```
治理 = 决策机制
├── 战略方向
├── 重大功能决策
├── API 变更
├── 依赖升级
├── 社区准则
├── 维护者任免
├── 冲突解决
├── 商标 / 品牌
└── 资金使用（如果有）
```

### 4.3 治理文档

**必备文档**：
- `GOVERNANCE.md` —— 治理结构
- `CONTRIBUTING.md` —— 贡献指南
- `CODE_OF_CONDUCT.md` —— 行为准则
- `MAINTAINERS.md` —— 维护者列表
- `SECURITY.md` —— 安全政策
- `LICENSE` —— 许可证

### 4.4 决策流程

```
提案（RFC / Issue）
    ↓ 讨论
评审（Maintainer / TSC）
    ↓ 决策
实施（贡献者）
    ↓ 合并
发布
```

---

## 五、典型项目治理对比

### 5.1 LiteLLM

**模式**：BDFL + 创业公司
**治理文档**：基础
**决策机制**：核心团队
**特点**：
- 快速迭代
- 创始人主导
- 商业化清晰

### 5.2 Portkey

**模式**：创业公司
**治理文档**：完善
**决策机制**：核心团队 + 社区 RFC
**特点**：
- 企业特性优先
- 商业化路径明确
- 社区参与度高

### 5.3 Higress

**模式**：大厂（阿里云）+ CNCF 候选
**治理文档**：完善
**决策机制**：阿里云 + 工作组
**特点**：
- 中文社区
- 阿里云生态绑定
- 努力走向中立

### 5.4 vLLM

**模式**：学术 + 商业（Anyscale）
**治理文档**：完善
**决策机制**：核心团队 + 工作组
**特点**：
- 学术影响力
- 工业采用度高
- 治理逐步规范化

### 5.5 对比总结

| 项目 | 治理 | 决策速度 | 中立性 | 商业化 |
|---|---|---|---|---|
| **LiteLLM** | BDFL | 极快 | 低 | 清晰 |
| **Portkey** | 公司 | 快 | 中 | 清晰 |
| **Higress** | 大厂+社区 | 中 | 中 | 间接 |
| **vLLM** | 学术+商业 | 中 | 中 | 间接 |
| **Kong** | 公司+OSS | 中 | 中 | 直接 |
| **TGI** | 公司 | 快 | 低 | 间接 |

---

## 六、开源许可协议选择

### 6.1 主流协议对比

| 协议 | 商用 | 修改 | 分发 | 专利授权 | Copyleft |
|---|---|---|---|---|---|
| **MIT** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Apache 2.0** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **BSD-3** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **MPL 2.0** | ✅ | ✅ | ✅ | ✅ | 文件级 |
| **LGPL** | ✅ | ✅ | ✅ | ✅ | 链接级 |
| **GPL** | ✅ | ✅ | ✅ | ✅ | 强 copyleft |
| **AGPL** | ✅ | ✅ | ✅ | ✅ | 网络 copyleft |
| **BSL** | 限制 | ✅ | ❌ | ❌ | 商业限制 |
| **SSPL** | 限制 | ✅ | ❌ | ❌ | 服务限制 |
| **Elastic License** | 限制 | ✅ | ❌ | ❌ | 限制托管 |
| **CCL** | 看具体 | 看具体 | ❌ | ❌ | 看具体 |

### 6.2 AI Gateway 项目的选择

| 项目 | 协议 | 选择理由 |
|---|---|---|
| **LiteLLM** | MIT | 最宽松、吸引最多用户 |
| **Portkey** | MIT | 商业友好 |
| **Higress** | Apache 2.0 | 大厂标准、专利授权 |
| **vLLM** | Apache 2.0 | 学术友好 |
| **Kong** | Apache 2.0 | OSI 批准 |
| **TGI** | Apache 2.0 | HuggingFace 默认 |
| **APISIX** | Apache 2.0 | 基金会友好 |
| **One API** | MIT | 个人项目、最宽松 |
| **Triton** | BSD-3 | NVIDIA 偏好 |
| **OpenLLMetry** | Apache 2.0 | 标准协议 |

### 6.3 协议选择的考量

#### 决定因素

| 因素 | 倾向 |
|---|---|
| **想最大化采用** | MIT / Apache 2.0 |
| **想防止云厂商吸血** | AGPL / BSL |
| **想企业采用** | Apache 2.0（含专利条款） |
| **想和某基金会对齐** | Apache 2.0 |
| **想商业化** | BSL / Elastic License |

#### 协议变更的代价

**例子**：
- Elastic 从 Apache 2.0 → SSPL → AWS 分叉 OpenSearch
- HashiCorp 从 MPL → BSL → OpenTofu 分叉
- MongoDB 从 AGPL → SSPL → 社区分裂
- Redis 从 BSD → SSPL → Valkey 分叉

**给 AI Gateway 的教训**：
- 改 license 是大事件
- 改 license 前评估分叉风险
- 社区信任是核心资产

### 6.4 "Open Source" 定义之争

**OSI（Open Source Initiative）认可**：MIT、Apache 2.0 等
**不认可**：BSL、SSPL、Elastic License

**争论**：
- "Open source" 应该包括 SSPL 吗？
- 商业限制的 license 是"开源"吗？
- "Source available" vs "Open source"

**业界趋势**：
- OSI 严格定义
- 部分公司用 "source available" 区分
- 商业开源公司多数用 BSL 等

---

## 七、社区健康度评估

### 7.1 关键指标

| 指标 | 健康阈值 | 警告信号 |
|---|---|---|
| **月度 commit** | > 50 | < 10 |
| **独立贡献者** | > 30 | < 5 |
| **首次响应时间** | < 7 天 | > 30 天 |
| **PR 合并率** | > 50% | < 20% |
| **未关闭 issue** | < 100 | > 500 |
| **stale PR** | < 10% | > 30% |
| **公司采用度** | > 5 家 | < 2 家 |
| **多平台 mention** | > 10 平台 | 1-2 个 |

### 7.2 评估框架

#### CHAOSS 指标

CHAOSS（Linux 基金会）提供开源健康度评估：

- **贡献者多样性**
- **公司参与度**
- **项目活跃度**
- **许可合规**
- **治理成熟度**

#### 评估工具

| 工具 | 来源 | 特点 |
|---|---|---|
| **OSSF Scorecard** | Linux Foundation | GitHub 评分 |
| **CHAOSS Metrics** | Linux Foundation | 完整指标 |
| **LFX Insights** | Linux Foundation | 基金会社区 |
| **CII Best Practices** | Linux Foundation | 最佳实践 |
| **GitHub Octoverse** | GitHub | 趋势报告 |

### 7.3 常见健康度问题

#### 问题 1：Bus Factor = 1

```
核心维护者就 1 个人
他/她离开 = 项目死掉
```

**缓解**：
- 培养副手
- 分散决策
- 文档化一切

#### 问题 2：大量 stale PR

```
堆积的 PR 没有评审
贡献者失望、流失
```

**缓解**：
- 定期 review
- 自动化 CI
- 透明状态

#### 问题 3：Issue 大量未响应

```
社区问的问题没人理
```

**缓解**：
- 设立 "triage" 角色
- 机器人预响应
- FAQ 文档

#### 问题 4：公司主导的"伪开源"

```
看似开源，实际只是公司 PR
外部贡献被拒绝
```

**缓解**：
- 透明的 governance
- 公开 roadmap
- 真正接受外部 PR

---

## 八、维护者工作

### 8.1 维护者的日常

```
典型一天
├── Review PRs（30-60%）
├── 回答 issue（10-20%）
├── 写代码（10-30%）
├── 会议（5-10%）
├── 文档维护（5-10%）
└── 社区互动（5-10%）
```

### 8.2 维护者常见痛点

| 痛点 | 描述 |
|---|---|
| **PR 堆积** | 看不过来 |
| **Issue 堆积** | 答不完 |
| **贡献者争吵** | 调解冲突 |
| **公司压力** | 商业需求 vs 社区需求 |
| **Burnout** | 长期无偿工作 |
| **范围蔓延** | 什么都要加 |
| **向后兼容** | 老的不能动 |
| **安全压力** | 漏洞报告响应 |

### 8.3 维护者支持机制

#### 机制 1：津贴

| 项目 | 津贴 |
|---|---|
| **Linux Kernel** | 部分公司付费给维护者 |
| **Kubernetes** | CNCF 资助 |
| **Node.js** | OpenJS 基金会资助 |
| **Rust** | Mozilla 资助 |

**AI Gateway 项目的现状**：
- 多数无津贴
- 仅靠公司薪酬
- 兼职维护者

#### 机制 2：基础设施支持

- CI/CD 免费额度（GitHub Actions、Travis）
- 翻译支持
- 文档托管
- 包管理（npm、PyPI、crates.io）

#### 机制 3：心理支持

- 维护者 Slack/Discord
- 经验分享会议
- Burnout 预警

### 8.4 维护者轮换

```python
# 模型 A：固定维护者（多数项目）
maintainers = ["alice", "bob", "charlie"]

# 模型 B：轮流（少数项目）
on_call = ["alice", "bob", "charlie"]
current_on_call = on_call[week_num % 3]

# 模型 C：领域维护者（大型项目）
domain_maintainers = {
    "core": ["alice", "bob"],
    "integrations": ["charlie", "diana"],
    "docs": ["eve"],
}
```

---

## 九、贡献者激励机制

### 9.1 内在激励

| 激励 | 描述 |
|---|---|
| **成就感** | 解决问题、被感谢 |
| **学习** | 接触新代码、新人 |
| **社区** | 归属感、朋友 |
| **影响力** | 影响项目方向 |
| **作品** | GitHub profile 展示 |

### 9.2 外在激励

| 激励 | 描述 |
|---|---|
| **公司认可** | 雇主支持、奖励 |
| **工作机会** | 招聘、推荐 |
| **会议演讲** | Speaker 机会 |
| **实物奖励** | 周边、奖品 |
| **金钱** | Bug Bounty、捐赠 |
| **认证** | Maintainer 徽章 |

### 9.3 Bug Bounty

**例子**：
- Kubernetes：没有
- LiteLLM：没有
- vLLM：通过 Sentry
- 主要的 AI Gateway 项目：尚未建立 Bug Bounty

**挑战**：
- 商业模式
- 漏洞分类
- 财务可持续

### 9.4 捐赠

- GitHub Sponsors
- Open Collective
- Polar
- Tidelift

**行业经验**：
- 多数项目捐赠收入 < $10k/年
- 仅靠捐赠无法维持

### 9.5 雇主支持

```
公司支持开源的方式
├── 直接雇佣贡献者
├── 给贡献者时间（20% rule）
├── 提供基础设施
├── 参加赞助商
├── 法律支持
└── 会议赞助
```

---

## 十、企业与个人贡献的协同

### 10.1 常见模式

#### 模式 1：公司主导 + 社区参与

```
公司核心团队
    ↓ 主导开发
社区贡献者
    ↑ 提交 PR
    ↓ Review
公司核心团队
```

**代表**：vLLM、Portkey、LiteLLM

**优点**：
- 持续投入
- 方向一致

**缺点**：
- 社区贡献被边缘化

#### 模式 2：基金会 + 多家公司

```
CNCF/Linux Foundation
    ↓ 治理
多家公司贡献
    ↓ 协同
共同项目
```

**代表**：Kubernetes、Prometheus、Envoy

**优点**：
- 中立
- 多方投入

**缺点**：
- 决策慢
- 协调成本

#### 模式 3：个人项目 → 公司接管

```
个人 → 增长 → 公司接管 → 商业化
```

**例子**：
- LangChain：个人 → 公司
- LiteLLM：个人 → 公司
- LiteLLM 创始人加入大厂后继续维护

### 10.2 公司与社区的常见冲突

| 冲突 | 例子 | 解决 |
|---|---|---|
| **公司 PR 优先合并** | 外部 PR 等几周 | 公平 review SLA |
| **公司决定路线** | 社区不同意 | RFC 流程 |
| **公司独占赞助** | 不中立 | 多家公司赞助 |
| **公司员工转岗** | 维护者流失 | 知识传递 |
| **商标争议** | 公司抢注 | CLA 明确商标 |

### 10.3 CLA（DCO）

**CLA（Contributor License Agreement）**：
- 贡献者授权公司使用其代码
- 公司可以重新授权

**DCO（Developer Certificate of Origin）**：
- 轻量级，贡献者签字确认
- 不转让版权

**例子**：
- Linux Kernel：DCO
- Kubernetes：CNCF CLA
- LiteLLM：无
- vLLM：无

**AI Gateway 项目多数用 DCO 或无需 CLA**。

---

## 十一、开源可持续性挑战

### 11.1 收入模式

#### 模式 1：纯开源 + 服务

```
公司提供
├── 托管云
├── 企业支持
├── 培训
├── 咨询
└── 实施服务
```

**例子**：Kong、Elastic（早期）

#### 模式 2：开源 + 商业版

```
开源核心
    +
商业版（额外功能）
```

**例子**：GitLab、MongoDB（早期）

#### 模式 3：SaaS + 开源核心

```
SaaS 订阅
    +
开源可自托管
```

**例子**：Sentry、Cal.com

#### 模式 4：Open Core

```
开源核心 + 商业扩展
```

**例子**：GitLab、CockroachDB

### 11.2 AI Gateway 项目的可持续性

**挑战**：
- 多个竞争项目
- 模型 API 价格战
- 企业付费意愿弱
- 云厂商可能直接做

**机会**：
- AI 流量增长
- 工具市场未成熟
- 多模型需求
- 企业需要中立

### 11.3 "开源陷阱"

```
陷阱 1：项目被云厂商免费用 → 公司无法变现
陷阱 2：社区版本和企业版本差异太大 → 社区流失
陷阱 3：开发完全靠公司 → 公司一旦放弃，项目死
陷阱 4：靠捐赠 → 维护者难以全职
陷阱 5：scope 蔓延 → 维护者 burnout
```

### 11.4 可持续的开源治理

**建议**：
1. **明确的 mission** —— 项目解决什么问题
2. **透明的 governance** —— 谁决策、怎么决策
3. **健康的贡献者结构** —— 不依赖单一个体
4. **可持续的资金** —— 多源（公司、捐赠、服务）
5. **适度的 scope** —— 不做"全能"项目
6. **社区优先** —— 重视用户和贡献者
7. **文档完善** —— 降低参与门槛
8. **友好的文化** —— 欢迎新人

---

## 十二、未解难题与研究前沿

### 12.1 治理

1. **AI Gateway 项目的"最佳"治理模式**是什么？
2. **大厂 + 社区**如何真正平衡？
3. **从公司主导到中立基金会**的过渡路径
4. **AI 时代的新治理挑战**（如：AI 生成代码的版权）
5. **多项目联合治理**（MCP / A2A / OTel 协调）

### 12.2 贡献者

6. **贡献者的有效激励**是什么？
7. **全职开源维护者**的可持续性
8. **贡献者"代际传承"**如何做
9. **AI 辅助贡献**的影响（人 + AI 协作）
10. **贡献者 burnout** 的预防

### 12.3 商业化

11. **AI Gateway 项目的商业可持续**模式
12. **云厂商吸血**的应对
13. **Open Core 边界**的合理划定
14. **服务 vs SaaS vs 自托管**的选择
15. **企业级支持**的定价

### 12.4 社区

16. **多语言社区**（中、英、日、韩）
17. **企业用户参与**开源的方式
18. **学术界与工业界**的协同
19. **新贡献者入门**的优化
20. **社区文化**的塑造

### 12.5 标准化

21. **开源治理标准**（类似 ISO）
22. **CLA / DCO 标准化**
23. **代码质量标准**
24. **安全漏洞披露**标准
25. **SBOM（软件物料清单）**标准

### 12.6 未来

26. **AI 时代"项目领导人"角色**的变化
27. **AI 自动维护**的可能性
28. **开源 vs 闭源**的长期格局
29. **AI 训练数据**与开源代码的关系
30. **开源的最终形态**

---

## 十三、参考资料

### 13.1 治理 / 社区

- Linux Foundation
- CNCF（Cloud Native Computing Foundation）
- Apache Software Foundation
- OpenJS Foundation
- CHAOSS（Community Health Analytics Open Source Software）
- TODO Group
- OSI（Open Source Initiative）

### 13.2 协议

- SPDX License List
- choosealicense.com
- Open Source Definition

### 13.3 评估工具

- github.com/ossf/scorecard
- github.com/cncf/landscape
- chaoss.community
- lfx.insights

### 13.4 关键博客 / 报告

- "Open Source Guides" (GitHub)
- "The Open Source Way" (Red Hat)
- "Measuring Community Health" (CHAOSS)
- "The Rise of Open Core Companies"
- "Why Open Source Governance Matters"

### 13.5 案例

- Elastic vs OpenSearch
- HashiCorp vs OpenTofu
- MongoDB / Redis 改 license
- Sentry 的可持续模式
- Cal.com 的开源 SaaS 模式

### 13.6 AI Gateway 项目的治理文档

- LiteLLM CONTRIBUTING.md
- Portkey GOVERNANCE.md
- Higress CONTRIBUTING.md
- vLLM CONTRIBUTING.md
- LangChain GOVERNANCE.md

---

**报告维护**

- 系列：AI Gateway 持续深挖 · 第 2 批 · 第 5 篇
- 主题：开源贡献与社区治理
- 上一份：14-performance-benchmark.md
- 下一份预告：AI 网关与公有云深度集成
