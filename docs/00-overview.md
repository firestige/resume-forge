# Resume Forge — 求职管理与简历生成系统

> 状态：可用

## 1. 项目定位

将传统的"简历仓库"升级为**求职作战指挥部**——覆盖素材管理、JD 分析、简历定制、面试复盘、趋势洞察全闭环，且每一步都适合 AI 对话驱动。

## 2. 核心设计理念

### 2.1 数据与模板分离

简历内容以 YAML 结构化管理，LaTeX 模板独立维护。数据变更不影响排版，排版优化不需要碰内容。

### 2.2 Base + Variant Overlay

```
base/（大而全的基准素材库）
  └── 每段经历的完整描述，作为"素材池"

variants/（每个目标岗位一个变体定义）
  └── 选择哪些素材 + 覆写/微调具体描述
      ↓ merge
  templates/ → LaTeX → PDF
```

同一段经历可以用不同视角表述。variant 支持字段级覆写，不只是"选择包含哪些"，更可以"重写怎么说"。

### 2.3 对话驱动版本生成

每个 variant 是 AI 对话的产物。就像为需求（某个特定岗位）重新拼装和微调一个版本构建——上传 JD、分析匹配、选材覆写、生成 PDF，全程对话完成。

### 2.4 岗位全生命周期管理

不止简历。从 JD 分析 → 简历定制 → 投递跟踪 → 面试记录 → 复盘洞察，形成完整闭环。

## 3. 两层架构

系统由 **Copilot 对话** 和 **GitHub Actions 自动化** 两层驱动，Web 仅作为只读展示层（GitHub Pages 纯静态站点），不承担任何计算或交互逻辑。

```
┌─────────────────────────────────────────────────────┐
│  🧠 Copilot 对话（IDE / VS Code Web）               │
│  ├─ JD 分析 → 生成 analysis.yaml                   │
│  ├─ 简历定制 → 生成/修改 variant.yaml               │
│  ├─ 面试复盘 → 生成 interviews/*.yaml               │
│  ├─ 状态更新 → 修改 status.yaml                     │
│  └─ 所有文件变更通过 git push 提交                   │
│      ↓ push                                        │
├─────────────────────────────────────────────────────┤
│  🤖 GitHub Actions（全自动）                         │
│  ├─ 构建 PDF（variant → LaTeX → PDF）               │
│  ├─ 聚合洞察（汇总 JD + 面试数据）                   │
│  ├─ 生成静态报告（Dashboard / 周报 HTML）            │
│  └─ 部署到 GitHub Pages                             │
│      ↓ deploy                                      │
├─────────────────────────────────────────────────────┤
│  🌐 GitHub Pages（纯静态，只读）                     │
│  ├─ Dashboard（投递概览、洞察报告）                   │
│  ├─ PDF 下载（各岗位简历）                           │
│  └─ 周报浏览                                        │
└─────────────────────────────────────────────────────┘
```

### 设计决策：为什么不做 Web 端交互？

- **PDF 编译需要 texlive**：GitHub Pages 是纯静态托管，无法运行服务端程序
- **LLM 调用需要 API Key**：不能暴露在前端代码中
- **Copilot 在 IDE 中已经足够好**：天然能读写文件、执行命令、对话驱动，无需重复造轮子
- **零成本**：不需要维护任何服务器、Serverless 函数或 Docker 实例

### 能力矩阵

| 操作 | 层级 | 触发方式 | 说明 |
|------|------|----------|------|
| JD 深度分析 | 🧠 Copilot | IDE 对话 | LLM 理解语义，匹配 base 素材，生成 analysis.yaml |
| 简历定制/覆写 | 🧠 Copilot | IDE 对话 | 选材、措辞优化、视角调整，生成 variant.yaml |
| 面试复盘 | 🧠 Copilot | IDE 对话 | 引导式记录，分析薄弱点，生成改进建议 |
| 投递状态更新 | 🧠 Copilot | IDE 对话 | 更新 status.yaml |
| 构建 PDF | 🤖 Actions | push 自动触发 | variant.yaml → LaTeX → PDF |
| 聚合洞察报告 | 🤖 Actions | push 自动触发 | 汇总所有 JD 和面试数据 → _insights/ |
| 生成 Dashboard | 🤖 Actions | push 自动触发 | 静态 HTML 报告 |
| 周报生成 | 🤖 Actions | cron 定时 | 每周一自动汇总 |
| 部署站点 | 🤖 Actions | 上游完成触发 | 发布到 GitHub Pages |
| 查看报告/下载 PDF | 🌐 Pages | 浏览器访问 | 纯静态，只读 |

## 4. 项目目录结构

```
resume-forge/
├── base/                          # 基准素材库
│   ├── profile.yaml               # 结构化：个人信息
│   ├── education.yaml             # 结构化：教育背景
│   ├── experience.yaml            # 结构化：工作经历时间线（仅元数据）
│   ├── skills.md                  # 非结构化：全量技能叙事
│   ├── projects_order.yaml        # 完整版简历中的项目展示顺序
│   └── projects/                  # 每个项目一个子目录
│       ├── course_platform/
│       │   ├── meta.yaml          #   结构化：项目名、公司、时间、标签
│       │   ├── content.md         #   非结构化：完整叙事
│       │   └── notes.md           #   可选：面试技术深度备注（不参与构建）
│       ├── search_platform/
│       ├── content_review/
│       └── data_pipeline/
│
├── jobs/                          # 岗位管理
│   ├── <date>-<company>-<role>/   # 每个岗位一个目录
│   │   ├── jd_source/             # JD 原始输入（截图/图片）
│   │   │   └── *.png
│   │   ├── jd.md                  # Copilot 从截图提取的 JD 文本
│   │   ├── analysis.yaml          # JD 分析结果
│   │   ├── variant/               # 简历变体
│   │   │   ├── config.yaml        #   选材配置（项目、顺序、模板）
│   │   │   ├── projects/          #   叙事覆写（仅需调整的项目）
│   │   │   │   └── <id>.md
│   │   │   └── skills.md          #   技能叙事覆写
│   │   ├── interviews/            # 面试记录
│   │   │   └── round1.yaml
│   │   └── status.yaml            # 投递状态追踪
│   └── _insights/                 # 跨岗位洞察（CI 自动生成）
│       ├── keyword_trends.yaml
│       ├── skill_gaps.yaml
│       └── interview_patterns.yaml
│
├── templates/                     # LaTeX Jinja2 模板
│   ├── resume_zh.tex.j2           # 中文主模板
│   ├── resume_en.tex.j2           # 英文主模板
│   └── partials/                  # 可复用区块模板
│       ├── header.tex.j2
│       ├── projects.tex.j2
│       ├── experience.tex.j2
│       ├── skills.tex.j2
│       └── education.tex.j2
│
├── reports/                       # 报告 HTML 模板（Jinja2）
│   ├── dashboard.html.j2          # 总览仪表盘
│   ├── insights.html.j2           # 洞察报告
│   ├── weekly.html.j2             # 周报
│   └── per_job.html.j2            # 单岗位详情
│
├── styles/                        # LaTeX 样式文件
│   ├── resume.cls
│   └── *.sty
├── fonts/                         # 字体文件
│
├── scripts/                       # Python 构建脚本
│   ├── build.py                   # 简历构建（YAML → LaTeX → PDF）
│   ├── analyze.py                 # JD 预处理
│   ├── insights.py                # 聚合洞察
│   └── report.py                  # 生成 HTML 报告 & Dashboard
│
├── .github/workflows/             # CI/CD 流水线
│   ├── build-resume.yml           # 简历构建
│   ├── generate-insights.yml      # 洞察报告
│   ├── deploy-pages.yml           # GitHub Pages 部署
│   └── weekly-report.yml          # 定时周报
│
├── prompts/                       # 预置 Prompt（Copilot 角色与场景）
│   ├── system.md                  #   全局 System Prompt
│   └── scenes/                    #   场景 Prompt（JD 分析、简历定制等）
│
├── output/                        # 生成产出 (gitignored)
├── docs/                          # 设计文档
├── .github/copilot-instructions.md # 项目级 Copilot 指令（自动加载）
├── Makefile                       # 快捷命令
├── requirements.txt               # Python 依赖
└── README.md
```

## 5. 核心工作流

```
                    ┌─────────────────────────────────┐
                    │  上传 JD                         │
                    └───────────┬─────────────────────┘
                                ▼
                    ┌─────────────────────────────────┐
                    │  🧠 AI 分析 JD → analysis.yaml   │
                    │  ├─ 提取关键词                    │
                    │  ├─ 与 base/ 匹配打分             │
                    │  └─ 输出定制建议                   │
                    └───────────┬─────────────────────┘
                                ▼
                    ┌─────────────────────────────────┐
                    │  🧠 对话定制 → variant.yaml       │
                    │  选材 + 覆写 + 微调措辞            │
                    └───────────┬─────────────────────┘
                                ▼
                    ┌─────────────────────────────────┐
                    │  git push → 🤖 Actions 构建 PDF   │
                    │  → 部署到 GitHub Pages            │
                    └───────────┬─────────────────────┘
                                ▼
                    ┌─────────────────────────────────┐
                    │  面试后记录 → interviews/          │
                    │  ├─ 问题 & 自评                   │
                    │  ├─ 更新 status.yaml             │
                    │  └─ 🤖 触发 _insights 更新        │
                    └─────────────────────────────────┘
```

## 6. Makefile 命令

| 命令 | 作用 |
|------|------|
| `make job=xxx` | 构建指定岗位简历 PDF |
| `make all` | 构建全部 PDF |
| `make new JOB=xxx` | 创建新岗位脚手架目录 |
| `make analyze JOB=xxx` | 分析指定岗位 JD |
| `make insights` | 聚合全局洞察 |
| `make report` | 本地生成全部报告 |
| `make weekly` | 生成本周周报 |

## 7. 实施阶段

### Phase 1 — 项目骨架 + Copilot 指令 + base 数据

项目基础设施、预置 Prompt、base 素材初始化。完成后 Copilot 打开项目即自动进入求职助手角色。

### Phase 2 — 构建管线 + 模板协同迭代

模板与管线不是线性先后关系，而是**协同迭代**：

```
2.1 管线骨架      最小 build.py + 极简模板 → "丑但正确"的 PDF
2.2 模板基线      基于 billryan/resume.cls 建立初版，定义模板与数据接口
2.3 迭代打磨      渲染 → 审视 → 调字体/间距/布局 → 再渲染（循环多轮）
2.4 Partials 拆分  模板稳定后拆出 partials/*.tex.j2，方便变体复用
```

### Phase 3 — 岗位工作流（variant → 定制 PDF）

岗位脚手架、variant 合并逻辑、辅助脚本、端到端示例。

### Phase 4 — CI/CD + 静态报告

GitHub Actions 4 个工作流、HTML 报告模板、Pages 部署。

## 8. 相关设计文档

- [01-data-model.md](01-data-model.md) — 数据模型与 YAML 格式规范
- [02-cicd-pipeline.md](02-cicd-pipeline.md) — CI/CD 流水线设计
- [03-web-and-copilot.md](03-web-and-copilot.md) — Web 展示层与 Copilot 工作流设计
- [04-prompt-engineering.md](04-prompt-engineering.md) — Prompt 工程设计（预置角色与场景 Prompt）
