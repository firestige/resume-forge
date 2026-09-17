# 数据模型与存储设计

> 关联：[00-overview.md](00-overview.md) §2 核心设计理念

## 1. 设计原则

### 1.1 结构化与非结构化分离

简历是**结构化数据与非结构化叙事混合**的典型场景：

| 数据类型 | 举例 | 特点 | 存储格式 |
|----------|------|------|----------|
| 结构化 | 姓名、联系方式、公司名、职级、时间段 | 固定字段、可枚举 | **YAML** |
| 非结构化 | 项目描述、工作亮点、技能阐述 | 自由叙事、视角多变、对话产物 | **Markdown** |

**YAML 只管元数据，Markdown 承载叙事。**

### 1.2 对话优先，文件是产物

用户不应该手写 YAML 或 Markdown。所有内容都是与 Copilot 对话的产物：

```
用户口述/粗略描述 → Copilot 提炼结构 → 生成文件 → 用户审核确认
```

文件格式的设计目标不是"让人容易填写"，而是"让 Copilot 容易读写、让构建脚本容易消费"。

### 1.3 JD 输入多模态

真实的 JD 来源是招聘 App 截图（Boss直聘、拉勾、猎聘等），而非结构化文本。系统应支持：

```
截图/图片 → Copilot（多模态 LLM）OCR + 提取 → 存储原图 + 结构化结果
```

---

## 2. 目录结构

```
base/
├── profile.yaml                   # 结构化：个人信息
├── education.yaml                 # 结构化：教育背景
├── experience.yaml                # 结构化：工作经历时间线（仅元数据）
├── skills.md                      # 非结构化：全量技能叙事
├── projects_order.yaml            # 完整版简历中的项目展示顺序
└── projects/                      # 每个项目一个目录
    ├── course_platform/
    │   ├── meta.yaml              # 结构化：项目名、公司、时间、技术栈、标签
    │   ├── content.md             # 非结构化：完整叙事（描述 + 亮点），写入简历
    │   └── notes.md               # 可选：面试技术深度备注（不参与构建）
    ├── search_platform/
    │   ├── meta.yaml
    │   └── content.md
    ├── content_review/
    └── data_pipeline/

jobs/
├── 2026-01-example-tech-backend/
│   ├── jd_source/                 # JD 原始输入（截图）
│   │   ├── screenshot1.png
│   │   └── screenshot2.png
│   ├── jd.md                      # Copilot 从截图提取的 JD 文本
│   ├── analysis.yaml              # JD 分析结果（结构化）
│   ├── variant/                   # 简历变体
│   │   ├── config.yaml            # 结构化：选材配置（选哪些项目、顺序、模板）
│   │   ├── profile.yaml           # 可选覆写：个人信息（如 title）
│   │   ├── projects/              # 非结构化：项目叙事覆写
│   │   │   ├── course_platform.md # 为该岗位重写的课程平台叙事
│   │   │   └── data_pipeline.md   # 为该岗位重写的数据管道叙事
│   │   └── skills.md              # 为该岗位重写的技能叙事
│   ├── interviews/
│   │   ├── prep_2026-03-07.yaml   # 面试准备 / 模拟记录
│   │   └── round1.yaml            # 真实面试记录
│   └── status.yaml
└── _insights/
    ├── keyword_trends.yaml
    ├── skill_gaps.yaml
  ├── interview_patterns.yaml
  └── self_model.yaml            # 长期自我认知模型
```

---

## 3. Base 素材库

### 3.1 profile.yaml — 个人信息（结构化）

```yaml
name: "李明"
email: "liming@example.com"
phone: "(+86) 138-0000-0000"
github:
  username: "example-user"
  url: "https://github.com/example-user"
homepage: "https://example.com"
location: "北京"
title: "高级后端工程师"
```

### 3.2 education.yaml — 教育背景（结构化）

```yaml
education:
  - id: donghu
    school: "东湖大学"
    location: "武汉"
    period: "2012 -- 2016"
    degree: "学士"
    major: "计算机科学与技术"
```

### 3.3 experience.yaml — 工作经历时间线（仅元数据）

只存公司、职位、时间等事实性信息，不含叙事描述。

```yaml
experience:
  - id: yunfan
    company: "云帆科技"
    location: "北京"
    period: "2021年6月 -- 至今"
    role: "高级后端工程师"
    level: "职级：P6"

  - id: xinghe
    company: "星河网络"
    location: "北京"
    period: "2018年3月 -- 2021年5月"
    role: "后端开发工程师"

  - id: lanjing
    company: "蓝鲸信息"
    location: "成都"
    period: "2016年7月 -- 2018年2月"
    role: "软件开发工程师"
```

### 3.4 skills.md — 技能全量叙事（非结构化）

Markdown 格式，对话产物。Copilot 可以整段重写。

```markdown
- 语言运用：Java > Go > Python > TypeScript > Shell
- 熟悉常见设计模式与领域建模方法，对 Spring、Netty 源码有深入分析，有多个重构案例。
- 对 JVM 内存模型与 GC 行为有较深入了解，熟练使用 JFR、async-profiler 定位疑难问题。
- 熟悉分布式事务、幂等、限流降级等高并发场景的常见方案，并在生产环境落地。
- 熟悉 TCP/IP、HTTP/2、gRPC 等协议，有较为丰富的网络编程经验。
```

### 3.5 projects/\<id\>/ — 项目（元数据 + 叙事分离）

**meta.yaml** — 项目的事实性信息：

其中 `tech` 字段在默认模板里会直接展示在项目标题下方，因此它的语义不应是“碰到过哪些组件”或“依赖清单”，而应是**这段经历最值得被看见的头部关键词**。优先写工作主轴、能力标签和必要的关键依赖；像某个具体 SDK 或中间件客户端这类只是实现载体、但不是项目重点的组件，默认不应占据头部关键词位置。

```yaml
id: course_platform
name: "课程平台服务化改造"
company: "云帆科技"
period: "2024.2至今"
tech: ["领域建模", "服务拆分", "契约测试", "灰度发布"]
role: "技术负责人，架构设计与核心开发"
tags: ["服务化", "领域建模", "重构", "平台建设"]
```

**content.md** — 自由叙事，对话产物：

```markdown
作为课程平台技术负责人，负责领域建模、服务拆分方案设计与核心链路开发。主要成果有：

- 主导单体课程系统的服务化拆分，按领域边界拆出 6 个服务，发布回滚范围从全站收敛到单服务，发布耗时从 40 分钟降到 8 分钟。
- 重构选课状态机，统一 9 类状态流转语义，配合幂等与本地消息表方案，将选课相关工单从月均 25 件降到 3 件以内。
- 针对开课高峰设计分层限流与热点课程缓存方案，峰值写入从 800 QPS 提升到 3.5k QPS，P99 保持在 240ms 以内。
```

**notes.md** — 可选，**不参与简历构建**，承载面试技术深度：

```markdown
## 容量估算
推导路径、关键参数、边界条件

## 关键设计决策
每个决策的选项与选择理由

## 已知局限
坦诚承认方案的边界和不足

## 可能被追问的点
高频问题与参考回答
```

`notes.md` 的写作原则：
- 写"为什么这样设计"而不是"做了什么"（后者已在 `content.md`）
- 包含数字和推导过程，不写模糊表述
- 坦诚记录局限，不回避缺陷（坦诚本身是加分项）
- Copilot 可基于代码分析和用户补充自动生成和维护

**为什么这样设计？**

- `meta.yaml` 给构建脚本用：排序、筛选、生成 LaTeX 的 `\datedsubsection`、`\role` 等命令
- `content.md` 给模板用：直接渲染为 LaTeX 正文，Copilot 可以整段替换或微调
- 不再强行把叙事拆成 `description` + `highlights[]` 的 YAML 数组——叙事就是叙事，让它保持自然

---

## 4. Variant 变体

### 4.1 设计思路

variant 不是"从 base 选字段覆写"，而是**为某个岗位重新编排的一份简历蓝图**：

- `config.yaml` — 结构化配置：选哪些项目、什么顺序、用什么模板
- `projects/<id>.md` — 针对该岗位重写的项目叙事（只有需要重写的才放这里）
- `skills.md` — 针对该岗位重写的技能叙事
- `profile.yaml` — 覆写个人信息（如 title）

### 4.2 config.yaml — 选材与编排（结构化）

```yaml
meta:
  job_ref: "2026-01-example-tech-backend"
  language: zh
  template: resume_zh

# 覆写 title（可选）
profile:
  title: "高并发服务端工程师"

# 项目选取与排序（有序数组，决定简历中的展示顺序）
projects:
  - course_platform      # 使用 base 叙事
  - search_platform      # 使用 base 叙事
  - data_pipeline        # variant/projects/data_pipeline.md 存在 → 用覆写版

# 工作经历选取（有序数组）
experience:
  - yunfan
  - xinghe
  - lanjing

# 中国职场默认要求时间轴完整，不应主动删除工作经历；与岗位弱相关的经历可弱化描述，但不建议从 experience 中移除。
# 技能：如果 variant/skills.md 存在则用覆写版，否则用 base
# 教育：始终用 base
```

### 4.3 叙事覆写（Markdown 文件）

只有需要为该岗位调整叙述的项目，才在 `variant/projects/` 下放对应的覆写文件。

- `variant/projects/<id>.md`：覆写项目正文叙事
- `variant/projects/<id>.yaml`：覆写项目 `meta.yaml` 中的展示字段，如 `tech`、`role`

**variant/projects/data_pipeline.md**（为高并发岗位重新视角的数据管道叙事）：

```markdown
作为核心开发者负责数据链路的吞吐与稳定性设计。

- 基于 Kafka + Flink 搭建流式处理流水线，日处理事件 3000 万条，端到端延迟从小时级降到分钟级。
- 设计基于水位线的去重与回放机制，保证上游重发场景下的结果幂等。
- 基于 Redis 构建维度字典缓存，将关联查询带来的处理延时降低约 35%。
```

对比 base 版本（强调数据建模与报表产出），这个版本重新组织了叙事，**突出吞吐能力与一致性保障**。

**variant/skills.md**（为高并发岗位重排技能）：

```markdown
- 语言：Java > Go > Python > Shell
- 熟悉高并发场景下的缓存、消息队列与限流降级方案的适用边界，有峰值 3.5k QPS 的生产落地经验。
- 对 Spring、MyBatis 源码有较为深入的分析，有多个服务化拆分与重构案例。
- 熟悉 JVM 内存结构与 GC 行为，能通过 JFR、async-profiler 定位内存与耗时问题。
- 熟悉 TCP/IP、HTTP/2、gRPC 等协议，有较为丰富的接口设计与联调治理经验。
```

### 4.4 Merge 规则

构建脚本的合并逻辑非常简单：

```
对于每个 section：
  1. 从 config.yaml 读取选材列表
  2. 对于每个选中的项目/条目：
    a. 如果 variant/projects/<id>.yaml 存在 → merge 到 base/projects/<id>/meta.yaml
    b. 如果 variant/projects/<id>.md 存在 → 用它覆写正文
    c. 否则 → 用 base/projects/<id>/content.md
  3. skills：variant/skills.md 存在 → 用它，否则 → 用 base/skills.md
  4. profile：config.yaml 中有覆写字段 → merge，否则 → 用 base/profile.yaml
  5. education / experience：始终从 base 读取元数据
```

**不再有深度字段合并**——叙事整文件替换，配置简单 merge。

---

## 5. JD 输入：多模态支持

### 5.1 输入形式

| 来源 | 输入形式 | 处理方式 |
|------|----------|----------|
| 招聘 App 截图 | PNG / JPG 图片 | Copilot 多模态 LLM → OCR + 提取文本 |
| 网页复制 | 粘贴文本 | Copilot 整理格式 |
| PDF 文件 | PDF | Copilot 提取文本 |

### 5.2 存储结构

```
jobs/2026-01-example-tech-backend/
├── jd_source/                  # 原始输入（保留溯源）
│   ├── screenshot1.png         # 招聘 App 截图
│   └── screenshot2.png         # 第二张截图
└── jd.md                       # Copilot 提取后的结构化文本
```

### 5.3 Copilot 处理流程

```
用户：[拖入截图] 帮我分析这个岗位

Copilot：
  1. 识别图片内容（多模态 LLM）
  2. 将截图保存到 jd_source/
  3. 提取 JD 文本 → 保存为 jd.md
  4. 解析 JD → 生成 analysis.yaml
  5. 与 base/ 素材匹配 → 输出建议
```

### 5.4 jd.md 格式

Copilot 从截图/文本提取后整理的标准格式：

```markdown
# 高级后端工程师 — 示例科技

**来源**: 招聘平台
**提取日期**: 2026-01-08

## 岗位职责
- 负责交易核心链路的架构设计和核心开发
- 负责系统的性能优化和稳定性保障
- ...

## 任职要求
- 5 年以上 Java/Go 后端开发经验
- 熟悉分布式系统原理，有高并发系统经验
- ...

## 加分项
- 有开源项目贡献经验
- ...
```

### 5.5 analysis.yaml（结构化分析结果）

```yaml
parsed_at: 2026-01-08
source: recruiting_app
company: "示例科技"
role: "高级后端工程师"
level: "高级/专家"
location: "北京"

keywords:
  must_have:
    - "高并发"
    - "Java/Go"
    - "性能优化"
    - "分布式系统"
  nice_to_have:
    - "开源社区贡献"
    - "云原生"

match_score:
  overall: 85
  details:
    - skill: "高并发系统设计"
      match: strong
      evidence: "课程平台选课链路经历"
    - skill: "Go 开发"
      match: partial
      evidence: "有 Go 经验但非主力语言"

gaps:
  - "JD 强调云原生，简历中云原生经验偏少"
  - "Go 语言深度不够，建议突出数据管道项目"

risks:
  - id: "level_mismatch"
    category: "级别/薪资"
    severity: "medium"
    signal: "JD 写 1-3 年，但招聘方表示团队也有专家岗位，当前 HC 尚未确认"
    impact: "可能导致薪资带、面评标准和岗位预期不一致"
    mitigation: "先确认当前沟通 HC 的真实级别，再决定是否深度定制简历"
    validation_question: "当前在沟通的 HC 是否按专家岗推进？"
    status: "open"

risk_summary:
  overall: "medium"
  decision: "continue_with_validation"
  note: "技术匹配较强，但需要尽快验证岗位级别与工作节奏"

resume_advice:
  - "项目顺序：课程平台 → 站内搜索平台 → 数据管道"
  - "强调性能优化成果"
  - "技能部分 Go 提到第二位"
```

### 5.6 风险字段约定

`analysis.yaml` 中的 `risks` 是岗位级风险登记表，用于记录“需要持续收集、验证，并在后续决策中使用”的信息，不局限于技能 gap。

推荐字段如下：

```yaml
risks:
  - id: "oncall_pressure"
    category: "作息/值班"
    severity: "high"
    signal: "招聘者深夜回复，岗位为面向全球用户的核心链路"
    impact: "可能存在晚间协作或线上值班压力"
    mitigation: "在继续推进前确认是否有固定 on-call 制度与频率"
    validation_question: "该岗位是否参与线上值班？频率如何？"
    status: "open"   # open / validated / invalidated / mitigated

  - id: "response_quality"
    category: "信息缺失/线索质量"
    severity: "medium"
    signal: "招聘者仅回复‘发简历’，未回应岗位画像、HC 优先级或筛选口径"
    impact: "若立即交出强定向首版简历，第一印象成本高，但获取的信息增量很低"
    mitigation: "先降级观察，优先继续索取低摩擦有效信息；在拿到更强信号前，不交高成本第一版简历"
    validation_question: "当前优先推进的 HC 是哪个？初筛更看重哪类背景或关键词？"
    status: "open"
```

设计原则：

- `signal` 记录事实信号，不直接下结论
- `impact` 说明为什么这个风险会影响投递决策或简历策略
- `mitigation` 说明应对动作：继续提问、调整简历、降低投入、放弃推进等
- `validation_question` 用于指导下一轮与招聘者/面试官沟通
- `status` 记录风险生命周期，便于在面试准备和复盘阶段持续更新

使用原则：

- 前期以“侧面收集、低摩擦求证”为主，不把单一风险信号当作早期一票否决
- 中期用于指导简历定制、问题追问和面试准备的投入重点
- 后期在是否继续推进、是否接受 offer 时集中发挥决策作用

招聘响应判断补充 SOP：

- 只索要简历、不回应任何岗位问题：记为 `低质量线索`，降级优先级，但不直接判定“非真实需求”
- 索要简历同时愿意补 1 条有效信息：记为 `中等质量线索`，可继续推进，但首版简历不要过窄
- 连续回答岗位优先级、筛选重点、团队画像、推进节奏：记为 `高质量线索`，可进入高投入定制
- 是否值得交第一版简历，不取决于“对方有没有要简历”，而取决于“对方有没有提供足够支撑第一印象成本的有效信息”

---

## 6. 面试与状态文件

这两类数据是结构化的，YAML 合适，保持不变。

### 6.1 interviews/round1.yaml

```yaml
date: 2026-03-15
record_type: live_interview
round: "技术一面"
duration: "60min"
interviewer_role: "业务后端团队 Tech Lead"

questions:
  - question: "介绍课程平台的服务拆分方案"
    category: "architecture"
    answer_quality: good
    gap_type: expression
    notes: "回答流畅，追问了一致性取舍"

  - question: "Go channel 和 goroutine 调度原理"
    category: "language_runtime"
    answer_quality: weak
    gap_type: capability
    notes: "只答了表层，GPM 模型细节没答好"

risk_updates:
  - risk_id: "work_style_oncall_uncertainty"
    new_status: validated
    evidence: "面试官明确说明存在轮值"

self_model_updates:
  - theme: "Go 运行时深度"
    old_belief: "Go 能支撑基础沟通"
    new_belief: "Go 运行时相关问题会暴露真实深度不足"
    gap_type: capability

self_reflection: |
  整体还行，Go 语言深度不够暴露了。

action_items:
  - "深入学习 Go GPM 调度模型"
  - "准备 Go 并发模式的实际案例"
```

### 6.2 interviews/prep_2026-03-07.yaml

```yaml
date: 2026-03-07
record_type: prep
round: "面试准备"
duration: "90min"
interviewer_role: "self-prep"

focus_topics:
  - "MQ 选型边界"
  - "Oracle 快速补齐路径"

questions:
  - question: "RabbitMQ 与 RocketMQ 在你项目中的选型边界是什么？"
    category: "middleware"
    answer_quality: weak
    gap_type: expression
    notes: "需按吞吐、顺序、可靠性、运维复杂度给出决策口径"

self_model_updates:
  - theme: "选型表达"
    old_belief: "做过 MQ 生产实践就足够回答选型题"
    new_belief: "如果没有统一比较框架，实践经验很难稳定转化为好答案"
    gap_type: expression

action_items:
  - "准备 RabbitMQ vs RocketMQ 对比表"

result: "in_preparation"
```

### 6.3 status.yaml

```yaml
applied_at: 2026-03-06
channel: "内推"
referrer: "xxx"
current_stage: interviewing

timeline:
  - date: 2026-03-06
    event: "投递简历"
  - date: 2026-03-15
    event: "技术一面"
    result: passed
  - date: 2026-03-16
    event: "确认该岗位存在夜间值班要求"
    result: "risk_validated"
```

`status.yaml` 不承载完整风险结构，但应该记录关键风险节点，尤其是：

- 招聘者确认真实 HC / 岗位级别
- 确认存在或不存在 on-call、跨时区协作、强制现场办公等
- 面试中验证出 JD 与真实业务方向存在偏差

---

## 7. 洞察文件

`jobs/_insights/` 下的文件由 CI 自动聚合生成。除关键词趋势、技能缺口、面试模式外，建议新增：

- `self_model.yaml`：长期自我认知模型，承载跨岗位稳定成立的强项、短板、定位假设与近期修正记录

---

## 8. 设计总结

| 内容类型 | 格式 | 谁来生成 | 谁来消费 |
|----------|------|----------|----------|
| 个人信息、教育、工作经历元数据 | YAML | Copilot 对话生成，用户确认 | 构建脚本 |
| 项目元数据（名称、公司、时间、标签） | YAML | Copilot 对话生成 | 构建脚本（排序、筛选） |
| 项目叙事（描述、亮点） | Markdown | Copilot 对话提炼 | 模板渲染为 LaTeX 正文 |
| 技能叙事 | Markdown | Copilot 对话提炼 | 模板渲染为 LaTeX 正文 |
| JD 原始输入 | 图片/文本 | 用户提供（截图、粘贴） | Copilot 多模态处理 |
| JD 提取文本 | Markdown | Copilot OCR 提取 | Copilot 分析 |
| JD 分析结果（含风险） | YAML | Copilot 分析生成 | 构建脚本、报告生成、后续决策 |
| 简历变体配置 | YAML | Copilot 对话生成 | 构建脚本（选材合并） |
| 简历变体叙事覆写 | Markdown | Copilot 对话重写 | 模板渲染 |
| 面试记录 | YAML | Copilot 引导式对话 | 洞察聚合 |
| 投递状态 | YAML | Copilot 对话更新 | Dashboard、洞察 |
| 洞察报告 | YAML | CI 自动聚合 | Dashboard、Copilot 趋势分析 |
