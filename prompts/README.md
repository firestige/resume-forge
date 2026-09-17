# Copilot 预置 Prompt

本目录存放 Copilot 对话的预置 prompt，实现场景自动识别和角色切换。

## 结构

- `system.md` — 全局 System Prompt（项目上下文、文件约定、工作方式）
- `scenes/` — 场景 Prompt（每个工作流场景一个文件）
  - `init_base.md` — 初始化素材库
  - `analyze_jd.md` — JD 分析
  - `craft_resume.md` — 简历定制
  - `prep_interview.md` — 面试准备
  - `review_interview.md` — 面试复盘
  - `trend_insights.md` — 趋势洞察

## 加载机制

1. `.github/copilot-instructions.md` 自动注入全局指令到 Copilot 上下文
2. Copilot 根据用户意图自动识别场景，读取对应的 `scenes/*.md`
3. 动态注入当前工作所需的项目文件（base 素材、JD、分析结果等）

## 当前约束

- 所有岗位流程默认包含风险识别与跟踪，不再只做技能匹配
- 风险优先写入 `analysis.yaml`，并在简历定制、面试准备、复盘中持续更新

## 迭代

Prompt 是活的，根据使用效果持续优化。详见 [docs/04-prompt-engineering.md](../docs/04-prompt-engineering.md)。
