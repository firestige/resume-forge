# Resume Forge — 求职管理与简历生成系统

把求职过程变成一条可版本化、可追溯、可复盘的流水线：素材管理、JD 分析、风险识别、简历定制、面试复盘、趋势洞察全闭环，由 AI 对话驱动，由 CI 自动产出 PDF 与静态站点。

核心理念不是"更快做一份简历"，而是"让每一次投递、沟通、面试都沉淀成下一次更高质量决策的输入"。

> ⚠️ **隐私提醒**：本仓库中的 `base/` 与 `jobs/` 只是**虚构示例数据**。当你填入自己的真实信息（姓名、手机号、邮箱、公司、面试记录）后，请务必把你的仓库设为 **private**，并谨慎对待 GitHub Pages 部署——它会把 Dashboard 和简历 PDF 公开到互联网上。

## 架构

- **AI 对话**（IDE 内的 Copilot / Claude Code 等）— JD 分析、简历定制、面试复盘等智能操作
- **GitHub Actions**（自动化）— PDF 构建、洞察聚合、报告生成、Pages 部署
- **GitHub Pages**（只读）— Dashboard、PDF 下载、周报浏览

三层之间唯一的触发机制是 `git push`：AI 只读写本地文件，不调用任何外部 API。

## 快速开始

### 依赖

- Python 3.12+
- TeX Live（需要 `xelatex`，以及中文字体支持）
  - macOS: `brew install --cask mactex-no-gui`
  - Ubuntu: `sudo apt-get install texlive-xetex texlive-fonts-extra texlive-latex-extra texlive-lang-chinese fonts-noto-cjk`

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 跑通示例

仓库自带一份虚构候选人（李明）和一个示例岗位，开箱即可构建：

```bash
make full                                      # 构建完整版简历
make job JOB=2026-01-example-tech-backend      # 构建指定岗位的定制版
make preview                                   # 本地预览站点（含自动重建）
```

`make preview` 会先执行 `insights + report`，然后启动 `http://127.0.0.1:8000`。
当 `base/`、`jobs/`、`reports/`、`templates/`、`styles/`、`scripts/` 下相关文件变更时会自动重建。

### 换成你自己的数据

1. 替换 `base/` 下的 `profile.yaml`、`education.yaml`、`experience.yaml`、`skills.md`
2. 删除 `base/projects/` 下的示例项目，按同样的 `meta.yaml` + `content.md` 结构写入你自己的项目
3. 更新 `base/projects_order.yaml` 中的展示顺序
4. 删除 `jobs/2026-01-example-tech-backend/`，用 `make new JOB=<岗位目录名>` 创建你自己的岗位

## 常用命令

| 命令 | 作用 |
|------|------|
| `make full` | 构建完整版简历 PDF |
| `make job JOB=xxx` | 构建指定岗位的定制简历 |
| `make all` | 构建全部岗位简历 |
| `make new JOB=xxx` | 创建新岗位脚手架目录 |
| `make insights` | 聚合跨岗位洞察 |
| `make report` | 生成静态站点 |
| `make weekly` | 生成本周周报 |
| `make preview` | 本地预览（自动重建 + 本地服务） |
| `make clean` | 清理构建产出 |

## 目录结构

```
base/           # 基准素材库（YAML 元数据 + Markdown 叙事）
jobs/           # 岗位管理（JD、分析、变体、面试、状态）
templates/      # LaTeX Jinja2 模板
styles/         # LaTeX 样式文件
scripts/        # Python 构建脚本
reports/        # HTML 报告模板
prompts/        # 预置 AI Prompt
docs/           # 设计文档
output/         # 构建产出（gitignored）
```

## 数据模型要点

- **YAML 只管元数据，Markdown 承载叙事**：姓名、公司、时间段是结构化的；项目描述、技能阐述是自由叙事的。
- **Base + Variant 覆写**：`base/` 是大而全的素材池，每个岗位的 `variant/` 只描述"选哪些、什么顺序、哪些需要重写"。
- **`notes.md` 不参与构建**：项目目录下的 `notes.md` 承载容量估算、设计决策、已知局限、追问备答，只用于面试准备。

完整规范见 [docs/01-data-model.md](docs/01-data-model.md)。

## 与 AI 对话

在 VS Code 中打开本项目后，`.github/copilot-instructions.md` 会自动注入项目级指令，无需手动设置角色。直接在 Chat 面板输入即可：

```
[粘贴或拖入 JD 截图]
帮我分析这个 JD，创建岗位目录 jobs/2026-02-xxx/

这个 JD 的必要技能和我的 base/ 素材怎么匹配？有哪些明显的 gap？
这个岗位除了技能 gap，还有哪些投递风险？

按你的建议帮我生成 variant/config.yaml，项目顺序：A → B → C

我明天面 xxx，读一下 jobs/2026-02-xxx/ 下的 analysis.yaml 和我的 base/ 素材，
帮我预测高概率面试题。

我刚面完一面，帮我创建 interviews/round1.yaml，我来说过程，你帮我整理成结构化记录。
```

场景 Prompt 见 [prompts/scenes/](prompts/scenes/)。

## 工作流速查

| 场景 | 操作 |
|------|------|
| 新岗位投递 | 粘贴 JD → AI 分析风险 + 生成 variant → `git push` |
| 更新基准素材 | 直接告诉 AI 改什么 → `git push` |
| 本地预览简历 | `make job JOB=xxx` → 打开 PDF |
| 面试前准备 | AI 读 analysis.yaml（含风险）→ 模拟问答 |
| 面试后复盘 | AI 引导记录 → 更新 interviews/ + status.yaml → `git push` |

## 设计原则

- **保持完整工作时间轴**：定制简历时不主动删除任何一段工作经历，弱相关经历只降权、不制造空窗期。
- **风险贯穿全流程**：级别/薪资错配、业务方向偏差、on-call、团队稳定性、信息缺失等风险结构化写入 `analysis.yaml`，在沟通与面试中逐步求证，而不是用单一信号一票否决。
- **对话优先，文件是产物**：不要求用户手写 YAML，文件格式的设计目标是"让 AI 容易读写、让脚本容易消费"。

## 设计文档

- [docs/00-overview.md](docs/00-overview.md) — 架构总览
- [docs/01-data-model.md](docs/01-data-model.md) — 数据模型
- [docs/02-cicd-pipeline.md](docs/02-cicd-pipeline.md) — CI/CD 流水线
- [docs/03-web-and-copilot.md](docs/03-web-and-copilot.md) — Web 展示层与对话工作流
- [docs/04-prompt-engineering.md](docs/04-prompt-engineering.md) — Prompt 工程

## 致谢

LaTeX 简历样式基于 [billryan/resume](https://github.com/billryan/resume) 的思路演化而来。

## License

[MIT](LICENSE)
