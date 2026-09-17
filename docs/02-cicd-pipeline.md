# CI/CD 流水线设计

> 关联：[00-overview.md](00-overview.md) §3 三层架构

## 1. 设计原则

- **变更驱动**：根据变更路径精准触发对应流水线，避免无意义构建
- **增量优先**：只构建受影响的岗位 PDF，全量构建仅在基准/模板变更时触发
- **产出可达**：所有 PDF 和报告通过 GitHub Pages 直接可访问
- **失败安全**：单个岗位构建失败不影响其他岗位

## 2. 流水线总览

| 工作流 | 触发条件 | 产出 |
|--------|----------|------|
| `build-resume.yml` | base/、variant、templates/、styles/ 变更 | 岗位 PDF |
| `generate-insights.yml` | jobs/ 下任意变更 | `_insights/` YAML 文件 |
| `deploy-pages.yml` | 上游工作流完成 | GitHub Pages 站点更新 |
| `weekly-report.yml` | 每周一 09:00 UTC+8 / 手动 | 周报 HTML |

## 3. 触发规则矩阵

| 变更路径 | build-resume | generate-insights | deploy-pages |
|----------|:---:|:---:|:---:|
| `base/**` | ✅ 全量构建 | ✅ | ✅ |
| `jobs/xxx/jd.md` | - | ✅ | ✅ |
| `jobs/xxx/variant.yaml` | ✅ 仅该岗位 | - | ✅ |
| `jobs/xxx/analysis.yaml` | - | ✅ | ✅ |
| `jobs/xxx/interviews/**` | - | ✅ | ✅ |
| `jobs/xxx/status.yaml` | - | ✅ | ✅ |
| `templates/**` | ✅ 全量构建 | - | ✅ |
| `styles/**` | ✅ 全量构建 | - | ✅ |
| `reports/**` | - | - | ✅ |
| `web/**` | - | - | - |

## 4. 工作流详细设计

### 4.1 build-resume.yml — 简历构建

```yaml
name: Build Resumes

on:
  push:
    branches: [main]
    paths:
      - 'base/**'
      - 'jobs/*/variant.yaml'
      - 'templates/**'
      - 'styles/**'
      - 'fonts/**'
  workflow_dispatch:
    inputs:
      job_target:
        description: '指定构建的岗位目录名（留空=自动检测）'
        required: false
        type: string

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      build_all: ${{ steps.check.outputs.build_all }}
      changed_jobs: ${{ steps.check.outputs.changed_jobs }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - id: check
        name: Detect what changed
        run: |
          if [[ -n "${{ inputs.job_target }}" ]]; then
            echo "changed_jobs=[\"${{ inputs.job_target }}\"]" >> $GITHUB_OUTPUT
            echo "build_all=false" >> $GITHUB_OUTPUT
            exit 0
          fi

          CHANGED=$(git diff --name-only HEAD~1 HEAD)

          # base/ templates/ styles/ fonts/ 变更 → 全量构建
          if echo "$CHANGED" | grep -qE '^(base|templates|styles|fonts)/'; then
            echo "build_all=true" >> $GITHUB_OUTPUT
          else
            echo "build_all=false" >> $GITHUB_OUTPUT
            # 提取变更的 job 目录
            JOBS=$(echo "$CHANGED" | grep '^jobs/' | grep 'variant.yaml' \
              | sed 's|jobs/\([^/]*\)/.*|\1|' | sort -u | jq -R -s -c 'split("\n") | map(select(. != ""))')
            echo "changed_jobs=$JOBS" >> $GITHUB_OUTPUT
          fi

  build:
    needs: detect-changes
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        job_dir: ${{ needs.detect-changes.outputs.build_all == 'true'
          && fromJson(steps.list-all.outputs.all_jobs)
          || fromJson(needs.detect-changes.outputs.changed_jobs) }}
    steps:
      - uses: actions/checkout@v4

      - name: List all jobs (if build_all)
        id: list-all
        if: needs.detect-changes.outputs.build_all == 'true'
        run: |
          JOBS=$(find jobs -maxdepth 1 -mindepth 1 -type d \
            ! -name '_*' -exec basename {} \; | jq -R -s -c 'split("\n") | map(select(. != ""))')
          echo "all_jobs=$JOBS" >> $GITHUB_OUTPUT

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install Python deps
        run: pip install -r requirements.txt

      - name: Install TeX Live
        uses: xu-cheng/latex-action@v3
        with:
          run: echo "TeX Live installed"

      - name: Build PDF
        run: python scripts/build.py --job ${{ matrix.job_dir }}

      - name: Upload PDF artifact
        uses: actions/upload-artifact@v4
        with:
          name: resume-${{ matrix.job_dir }}
          path: output/resumes/${{ matrix.job_dir }}.pdf

  collect-pdfs:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: output/resumes/
          pattern: resume-*
          merge-multiple: true

      - uses: actions/upload-artifact@v4
        with:
          name: all-resumes
          path: output/resumes/
```

### 4.2 generate-insights.yml — 洞察聚合

```yaml
name: Generate Insights

on:
  push:
    branches: [main]
    paths:
      - 'jobs/**'
  workflow_dispatch:

jobs:
  insights:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Aggregate insights
        run: python scripts/insights.py

      - name: Generate reports
        run: python scripts/report.py

      - name: Commit insights back to repo
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add jobs/_insights/
          git diff --cached --quiet || git commit -m "chore: update insights [skip ci]"
          git push
```

### 4.3 deploy-pages.yml — GitHub Pages 部署

```yaml
name: Deploy to GitHub Pages

on:
  workflow_run:
    workflows: ["Build Resumes", "Generate Insights"]
    types: [completed]
    branches: [main]
  push:
    branches: [main]
    paths:
      - 'reports/**'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name != 'workflow_run' }}
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install Python deps
        run: pip install -r requirements.txt

      - name: Download latest resume PDFs
        uses: actions/download-artifact@v4
        with:
          name: all-resumes
          path: output/resumes/
        continue-on-error: true  # 可能没有新构建

      - name: Generate static reports
        run: python scripts/report.py --output output/site/

      - name: Copy PDFs to site
        run: |
          mkdir -p output/site/resumes
          cp output/resumes/*.pdf output/site/resumes/ 2>/dev/null || true

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: output/site/

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### 4.4 weekly-report.yml — 定时周报

```yaml
name: Weekly Report

on:
  schedule:
    - cron: '0 1 * * 1'   # 每周一 09:00 UTC+8
  workflow_dispatch:

jobs:
  weekly:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Generate weekly insights
        run: python scripts/insights.py --weekly

      - name: Generate weekly report
        run: python scripts/report.py --weekly

      - name: Commit weekly report
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          WEEK=$(date +%Y-W%V)
          git add output/site/weekly/
          git diff --cached --quiet || git commit -m "chore: weekly report $WEEK [skip ci]"
          git push
```

## 5. 构建产出目录

```
output/
├── resumes/                        # 各岗位 PDF
│   ├── 2026-03-bytedance-storage.pdf
│   ├── 2026-03-aliyun-iot.pdf
│   └── full.pdf
└── site/                           # GitHub Pages 站点根目录
    ├── index.html                  # Dashboard 入口
    ├── insights.html               # 洞察报告
    ├── resumes/                    # PDF 下载
    │   └── *.pdf
    ├── weekly/                     # 周报
    │   └── 2026-W10.html
    ├── per_job/                    # 单岗位详情
    │   └── 2026-03-bytedance-storage.html
    └── assets/                     # 静态资源
        ├── css/
        └── js/
```

## 6. 本地开发命令 (Makefile)

```makefile
# 构建指定岗位 PDF
job:
	python scripts/build.py --job $(JOB)

# 构建全部 PDF
all:
	python scripts/build.py --all

# 创建新岗位脚手架
new:
	python scripts/new_job.py $(JOB)

# 分析 JD（需要 LLM，仅本地/Web 使用）
analyze:
	python scripts/analyze.py --job $(JOB)

# 聚合洞察
insights:
	python scripts/insights.py

# 生成报告
report:
	python scripts/report.py

# 生成周报
weekly:
	python scripts/insights.py --weekly
	python scripts/report.py --weekly

# 本地预览 Dashboard
dashboard:
	python scripts/report.py --serve

# 清理
clean:
	rm -rf output/
```

## 7. 注意事项

1. **[skip ci] 标记**：insights 自动提交使用 `[skip ci]` 避免死循环触发
2. **fail-fast: false**：矩阵构建中单个岗位失败不影响其他
3. **并发控制**：Pages 部署使用 concurrency group 避免竞争
4. **敏感信息**：LLM API key 通过 GitHub Secrets 管理，JD 分析仅在 Web/本地执行，CI 不触发 LLM 调用
5. **artifact 保留**：PDF artifact 默认保留 90 天
