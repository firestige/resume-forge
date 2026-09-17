# Web 展示层与 Copilot 工作流设计

> 关联：[00-overview.md](00-overview.md) §3 两层架构

## 1. 设计原则

- **Web 只做展示**：GitHub Pages 纯静态站点，不承担任何计算、编辑或 API 调用
- **操作全走 Copilot**：所有需要智能的操作（JD 分析、简历定制、面试复盘）在 IDE 中通过 Copilot 对话完成
- **push 驱动一切**：Copilot 修改文件 → git push → Actions 自动构建 → Pages 自动更新
- **零服务端成本**：不需要 App Server、Serverless Function 或任何付费服务

### 架构决策记录

**为什么不做 Web 端编辑器和 Copilot？**

| 需求 | Web 端实现代价 | IDE Copilot 已有能力 |
|------|---------------|---------------------|
| LaTeX → PDF | 需要 App Server 或 Serverless + texlive | Actions 自动构建，push 即触发 |
| LLM 对话 | 需要后端代理 API Key | IDE 内 Copilot 原生支持 |
| 读写 YAML | 需要 GitHub API + OAuth 认证 | 直接读写本地文件 |
| 实时预览 | 需要前端模拟 LaTeX 排版 | `make job=xxx` 本地构建 |

**结论**：IDE Copilot 已经是最好的交互界面，Web 端重复造轮子代价高、体验差。

## 2. Web 站点结构

GitHub Pages 部署的纯静态站点，由 CI/CD 中 `scripts/report.py` 生成。

```
output/site/
├── index.html                     # Dashboard 入口
├── insights.html                  # 洞察报告（关键词趋势、技能差距）
├── weekly/                        # 周报
│   ├── index.html                 # 周报列表
│   └── 2026-W10.html             # 具体某周
├── jobs/                          # 单岗位详情
│   ├── index.html                 # 岗位列表
│   └── 2026-01-example-tech-backend.html  # 单岗位报告
├── resumes/                       # PDF 文件托管
│   ├── 2026-01-example-tech-backend.pdf
│   └── full.pdf
└── assets/
    └── style.css                  # 简单样式
```

### 页面路由

| 路径 | 内容 | 数据来源 |
|------|------|----------|
| `/` | Dashboard 总览 | 聚合所有 status.yaml + _insights/ |
| `/insights.html` | 行业洞察 | `_insights/keyword_trends.yaml` + `skill_gaps.yaml` |
| `/weekly/` | 周报列表 | scripts/report.py --weekly 生成 |
| `/jobs/` | 岗位列表+状态 | 所有 `jobs/*/status.yaml` |
| `/jobs/xxx.html` | 单岗位详情 | analysis.yaml + status.yaml + interviews/ |
| `/resumes/xxx.pdf` | PDF 下载 | Actions 构建产出 |

## 3. Dashboard 设计

```
┌──────────────────────────────────────────────────────────┐
│  求职仪表盘                          最后更新: 2026-03-06 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  投递概览                                                │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │  8   │ │  3   │ │  2   │ │  1   │ │  2   │          │
│  │ 总投递│ │ 面试中│ │ 待回复│ │ Offer│ │ 已拒 │          │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘          │
│                                                          │
│  行业关键词 TOP10                                        │
│  ████████████ 分布式系统 87%                             │
│  ██████████   性能优化   75%                             │
│  ████████     Go         62%                             │
│  ███████      云原生      50%                            │
│                                                          │
│  薄弱环节追踪                                            │
│  ⚠️  Go 语言深度       出现 3 次    ← 高优先补强        │
│  ⚠️  K8s 实操          出现 2 次                        │
│                                                          │
│  最近动态                                                │
│  03-15 示例科技 一面 ✅                                  │
│  03-12 星辰云   二面 ✅                                  │
│  03-06 示例科技 投递简历                                 │
│                                                          │
│  简历下载                                                │
│  [示例科技版]  [星辰云版]  [完整版]                      │
└──────────────────────────────────────────────────────────┘
```

**技术实现**：纯 HTML + CSS，Jinja2 模板在 CI 构建时渲染为静态 HTML。无 JavaScript 依赖。

## 4. Copilot 工作流设计

所有智能操作在 IDE（VS Code / VS Code Web）中通过 Copilot 对话完成。

### Prompt 预置

Copilot 对话自动加载项目级预置 Prompt，无需用户手动设定角色。根据工作流场景自动切换 HR / 团队 Leader / 求职教练等视角。

详见 [04-prompt-engineering.md](04-prompt-engineering.md)。

### 4.1 支持的工作流

| 工作流 | 输入 | Copilot 行为 | 输出文件 |
|--------|------|-------------|----------|
| 新建岗位 | 岗位名称 | 创建目录脚手架 | `jobs/xxx/` 目录 |
| JD 分析 | 截图/图片/文本 | 多模态 OCR 提取 + 语义分析 | `jd_source/*.png` + `jd.md` + `analysis.yaml` |
| 简历定制 | analysis + 对话 | 选材、重写叙事、微调 | `variant/config.yaml` + `variant/projects/*.md` + `variant/skills.md` |
| 面试记录 | 引导式对话 | 记录问题、自评、反思 | `interviews/roundN.yaml` |
| 状态更新 | 对话 | 更新投递进展 | `status.yaml` |
| 趋势分析 | 全量 JD + 面试数据 | 跨岗位归纳 | 对话中输出，辅助决策 |

### 4.2 典型对话示例

**场景 1：从截图开始一个新岗位**

```
你：[拖入招聘 App 截图] 帮我分析这个岗位

Copilot：
  识别到截图内容：示例科技 · 高级后端工程师
  已创建 jobs/2026-01-example-tech-backend/ 目录
  截图已保存到 jd_source/
  JD 文本已提取保存为 jd.md

  分析结果：
  - 必须项：高并发、Java/Go、性能优化
  - 加分项：开源贡献、云原生
  - 匹配度：85/100
  - 差距：Go 深度不够、云原生经验少

  已生成 analysis.yaml

  建议简历调整：
  1. 项目排序：课程平台 → 站内搜索平台 → 数据管道
  2. 课程平台突出选课高峰的限流与一致性方案
  3. 技能部分 Go 提前

  要我按这个方案生成简历变体吗？

你：好的，但课程平台的描述再强调一下架构设计能力

Copilot：
  已生成：
  - variant/config.yaml（选材配置）
  - variant/projects/course_platform.md（突出架构设计的重写版本）
  - variant/skills.md（Go 提前、高并发方向优化）

  现在 git push 即可触发 Actions 构建 PDF。

你：push 吧

Copilot：[执行 git add + commit + push]
  已推送。Actions 正在构建，约 1-3 分钟后可在
  https://<your-name>.github.io/<your-repo>/resumes/2026-01-example-tech-backend.pdf
  下载 PDF。
```

**场景 2：面试复盘**

```
你：刚面完示例科技一面，帮我记录一下

Copilot：好的，几个问题：
  1. 面了多久？
  2. 面试官大概什么角色？

你：60分钟，交易团队 TL

Copilot：开始记录。有哪些问题？一个一个说就行。

你：先问了课程平台的服务拆分，答得还行

Copilot：✅ 评为 good，还有呢？

你：问了 Go 调度模型，答得不好

Copilot：⚠️ 评为 weak。这已经是第3次在 Go 深度上被问住了。
  建议补强：Go runtime GPM 调度、三色标记 GC。
  还有其他问题吗？

你：没了

Copilot：已保存 → interviews/round1.yaml
  要更新投递状态吗？

你：一面过了

Copilot：已更新 status.yaml，当前阶段 → interviewing。
  push 后 Dashboard 会自动更新。
```

**场景 3：查看趋势**

```
你：最近投的这些岗位，有什么共同趋势吗？

Copilot：[读取所有 analysis.yaml 和面试记录]
  分析 8 个岗位的 JD：
  1. 87% 要求分布式系统经验 → 你的强项
  2. 62% 提到 Go → 你面试中 Go 相关表现偏弱，建议重点补强
  3. 50% 提到云原生 → 你缺乏实际 K8s 经验，考虑用侧项目补充
  4. AI Infra 相关后端需求在增长

  你最大的短板是 Go 语言深度，已在 3 次面试中暴露。
```

### 4.3 Copilot 与 Git 的集成

Copilot 在 IDE 中完成文件修改后，工作流：

```
Copilot 生成/修改文件
    ↓
git add → git commit → git push
（可以由 Copilot 代为执行，也可以用户手动）
    ↓
GitHub Actions 检测变更路径，触发对应流水线
    ↓
PDF 构建 / 洞察更新 / 报告生成 / Pages 部署
    ↓
GitHub Pages 站点更新，PDF 可下载
```

关键点：**push 是唯一的触发机制**，Copilot 不直接调用任何 API，只读写本地文件。

## 5. 本地开发体验

不需要 Web 服务器，所有操作通过命令行和 Copilot 完成：

```bash
# 本地构建某个岗位的 PDF（需要本地安装 texlive）
make job JOB=2026-01-example-tech-backend

# 本地构建所有 PDF
make all

# 本地生成报告（HTML，可用浏览器打开）
make report

# 创建新岗位目录
make new JOB=2026-02-another-company-backend

# 聚合洞察
make insights
```

本地构建可选，主要用于快速验证。正式产出全部走 CI/CD。
