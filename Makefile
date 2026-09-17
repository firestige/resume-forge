.PHONY: full job all new analyze insights report weekly preview clean

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
SCRIPTS := scripts
OUTPUT := output

# 构建完整版简历（仅 base，无 variant）
full:
	$(PYTHON) $(SCRIPTS)/build.py --full

# 构建指定岗位简历
job:
ifndef JOB
	$(error JOB is required. Usage: make job JOB=2026-03-bytedance-storage)
endif
	$(PYTHON) $(SCRIPTS)/build.py --job $(JOB)

# 构建所有岗位简历
all:
	$(PYTHON) $(SCRIPTS)/build.py --all

# 创建新岗位脚手架目录
new:
ifndef JOB
	$(error JOB is required. Usage: make new JOB=2026-03-bytedance-storage)
endif
	@mkdir -p jobs/$(JOB)/jd_source
	@mkdir -p jobs/$(JOB)/variant/projects
	@mkdir -p jobs/$(JOB)/interviews
	@touch jobs/$(JOB)/jd.md
	@touch jobs/$(JOB)/status.yaml
	@echo "Created jobs/$(JOB)/"

# 分析指定岗位 JD
analyze:
ifndef JOB
	$(error JOB is required. Usage: make analyze JOB=2026-03-bytedance-storage)
endif
	$(PYTHON) $(SCRIPTS)/analyze.py --job $(JOB)

# 聚合全局洞察
insights:
	$(PYTHON) $(SCRIPTS)/insights.py

# 生成全部报告
report:
	$(PYTHON) $(SCRIPTS)/report.py --output $(OUTPUT)/site/

# 生成本周周报
weekly:
	$(PYTHON) $(SCRIPTS)/report.py --weekly

# 一键本地预览（含自动重建）
preview:
	$(PYTHON) $(SCRIPTS)/preview.py --host $${HOST:-127.0.0.1} --port $${PORT:-8000}

# 清理构建产出
clean:
	rm -rf $(OUTPUT)
