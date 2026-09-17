#!/usr/bin/env python3
"""
report.py — 生成静态 HTML 报告站点

用法:
  python scripts/report.py --output output/site/          # 生成完整站点
  python scripts/report.py --weekly --output output/site/ # 仅生成本周周报
"""

import argparse
import html
import os
import re
import shutil
from datetime import date, datetime
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).parent.parent
JOBS = ROOT / "jobs"
INSIGHTS = JOBS / "_insights"
REPORTS = ROOT / "reports"
ASSET_VERSION = (os.environ.get("GITHUB_SHA", "")[:8] or datetime.utcnow().strftime("%Y%m%d%H%M%S"))
MERMAID_BLOCK_RE = re.compile(r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.DOTALL)
MARKDOWN_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


# ── 工具函数 ──────────────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def iter_job_dirs():
    for d in sorted(JOBS.iterdir()):
        if d.is_dir() and not d.name.startswith("_"):
            yield d


def make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(REPORTS)),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )


def render(env: Environment, template_name: str, context: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmpl = env.get_template(template_name)
    ctx = dict(context)
    ctx.setdefault("asset_version", ASSET_VERSION)
    output_path.write_text(tmpl.render(**ctx), encoding="utf-8")
    print(f"  ✓ {output_path.relative_to(ROOT)}")


def render_markdown(raw: str) -> tuple[Markup, bool]:
    html_output = markdown.markdown(
        raw,
        extensions=["fenced_code", "tables", "nl2br"],
    )
    has_mermaid = False

    def replace_mermaid(match: re.Match[str]) -> str:
        nonlocal has_mermaid
        has_mermaid = True
        return f'<pre class="mermaid">{html.unescape(match.group(1))}</pre>'

    html_output = MERMAID_BLOCK_RE.sub(replace_mermaid, html_output)
    return Markup(html_output), has_mermaid


def extract_markdown_title(raw: str, fallback: str) -> str:
    match = MARKDOWN_TITLE_RE.search(raw)
    if match:
        return match.group(1).strip()
    return fallback


STAGE_ALIASES = {
    "draft": "draft",
    "草稿": "draft",
    "review_draft": "draft",
    "复核草稿": "draft",
    "applied": "applied",
    "已投递": "applied",
    "screening": "screening",
    "简历筛选": "screening",
    "筛选中": "screening",
    "resume_screening": "screening",
    "interviewing": "interviewing",
    "面试中": "interviewing",
    "已进入一面": "interviewing",
    "awaiting_interview_feedback": "interviewing",
    "待面试反馈": "interviewing",
    "等待面试反馈": "interviewing",
    "offer": "offer",
    "录用": "offer",
    "suspended": "suspended",
    "挂起": "suspended",
    "closed": "closed",
    "关闭": "closed",
    "已关闭": "closed",
    "rejected": "rejected",
    "已拒绝": "rejected",
    "withdrawn": "withdrawn",
    "已撤回": "withdrawn",
}


def normalize_stage(stage: str) -> str:
    raw = str(stage or "unknown").strip()
    return STAGE_ALIASES.get(raw, raw or "unknown")


ACTIVE_STAGES = ["draft", "applied", "screening", "interviewing", "offer"]
INACTIVE_STAGES = ["suspended", "closed", "rejected", "withdrawn"]


def get_job_score(job: dict) -> int:
    score = ((job.get("analysis") or {}).get("match_score") or {}).get("overall", 0)
    try:
        return int(score)
    except (TypeError, ValueError):
        return 0


def sort_jobs_for_listing(jobs: list[dict]) -> list[dict]:
    return sorted(
        jobs,
        key=lambda job: (-get_job_score(job), job.get("analysis", {}).get("company", ""), job.get("id", "")),
    )


def build_job_groups(jobs: list[dict]) -> list[dict]:
    grouped = []
    for title, description, stages in [
        ("活跃岗位", "优先关注未投递、已投递、筛选中和面试中的岗位。", ACTIVE_STAGES),
        ("非活跃岗位", "挂起、关闭、已拒绝或已撤回的岗位，保留复盘价值，不作为当前主跟踪对象。", INACTIVE_STAGES),
    ]:
        status_groups = []
        for stage in stages:
            stage_jobs = [job for job in jobs if job.get("status", {}).get("normalized_stage") == stage]
            if not stage_jobs:
                continue
            status_groups.append({
                "stage": stage,
                "label": STAGE_LABEL.get(stage, stage),
                "jobs": sort_jobs_for_listing(stage_jobs),
            })
        grouped.append({
            "title": title,
            "description": description,
            "count": sum(len(group["jobs"]) for group in status_groups),
            "status_groups": status_groups,
        })
    return grouped


# ── 数据收集 ──────────────────────────────────────────────────────────────

def load_all_jobs() -> list[dict]:
    jobs = []
    for job_dir in iter_job_dirs():
        status = load_yaml(job_dir / "status.yaml")
        status["normalized_stage"] = normalize_stage(status.get("current_stage", "unknown"))
        status["is_active"] = status["normalized_stage"] in ACTIVE_STAGES
        ana = load_yaml(job_dir / "analysis.yaml")
        interviews = []
        prep_sessions = []
        study_materials = []
        has_mermaid_study_materials = False
        iv_dir = job_dir / "interviews"
        if iv_dir.exists():
            for iv_file in sorted(iv_dir.glob("*.yaml")):
                iv = load_yaml(iv_file)
                round_name = str(iv.get("round", ""))
                result = str(iv.get("result", iv.get("overall_result", "")))
                is_prep = iv_file.stem.startswith("prep_") or "准备" in round_name or "模拟" in round_name or result in {
                    "in_preparation",
                    "ready_for_interview_prep",
                }
                if is_prep:
                    prep_sessions.append(iv)
                else:
                    interviews.append(iv)

            for md_file in sorted(iv_dir.glob("*.md")):
                raw = md_file.read_text(encoding="utf-8")
                rendered_html, has_mermaid = render_markdown(raw)
                has_mermaid_study_materials = has_mermaid_study_materials or has_mermaid
                fallback_title = md_file.stem.replace("_", " ")
                study_materials.append(
                    {
                        "name": md_file.stem,
                        "title": extract_markdown_title(raw, fallback_title),
                        "html": rendered_html,
                        "has_mermaid": has_mermaid,
                    }
                )
        variant_cfg = load_yaml(job_dir / "variant" / "config.yaml")
        jobs.append({
            "id": job_dir.name,
            "status": status,
            "analysis": ana,
            "interviews": interviews,
            "prep_sessions": prep_sessions,
            "study_materials": study_materials,
            "has_mermaid_study_materials": has_mermaid_study_materials,
            "variant_config": variant_cfg,
        })
    return jobs


def load_insights() -> dict:
    return {
        "keyword_trends": load_yaml(INSIGHTS / "keyword_trends.yaml"),
        "skill_gaps": load_yaml(INSIGHTS / "skill_gaps.yaml"),
        "interview_patterns": load_yaml(INSIGHTS / "interview_patterns.yaml"),
        "weekly_summary": load_yaml(INSIGHTS / "weekly_summary.yaml"),
        "self_model": load_yaml(INSIGHTS / "self_model.yaml"),
    }


def collect_resume_entries(jobs: list[dict]) -> list[dict]:
    resumes_src = ROOT / "output" / "resumes"
    entries: list[dict] = []

    full_pdf = resumes_src / "resume_full.pdf"
    if full_pdf.exists():
        entries.append({
            "name": "resume_full.pdf",
            "label": "完整版简历",
            "job_id": None,
            "available": True,
        })

    for job in jobs:
        job_pdf = resumes_src / f"{job['id']}.pdf"
        entries.append({
            "name": f"{job['id']}.pdf",
            "label": f"{job['analysis'].get('company', job['id'])} · {job['analysis'].get('role', job['id'])}",
            "job_id": job["id"],
            "available": job_pdf.exists(),
        })

    return entries


def copy_valid_resumes(output_dir: Path, entries: list[dict]) -> None:
    resumes_src = ROOT / "output" / "resumes"
    resumes_dst = output_dir / "resumes"
    if resumes_dst.exists():
        shutil.rmtree(resumes_dst)
    resumes_dst.mkdir(parents=True, exist_ok=True)

    if not resumes_src.exists():
        return

    for entry in entries:
        if not entry.get("available"):
            continue
        src = resumes_src / entry["name"]
        if src.exists():
            shutil.copy2(src, resumes_dst / src.name)


# ── 站点构建 ──────────────────────────────────────────────────────────────

STAGE_ORDER = ["draft", "applied", "screening", "interviewing", "offer", "suspended", "closed", "rejected", "withdrawn"]
STAGE_LABEL = {
    "draft": "草稿",
    "applied": "已投递",
    "screening": "简历筛选",
    "interviewing": "面试中",
    "offer": "Offer",
    "suspended": "挂起",
    "closed": "关闭",
    "rejected": "已拒绝",
    "withdrawn": "已撤回",
    "review_draft": "复核草稿",
    "awaiting_interview_feedback": "待面试反馈",
    "待面试反馈": "待面试反馈",
    "等待面试反馈": "待面试反馈",
    "挂起": "挂起",
    "关闭": "关闭",
    "unknown": "未知",
}

INSIGHT_DETAIL_PAGES = [
    {"key": "category-heatmap", "slug": "category-heatmap", "title": "高频需求分类热力"},
    {"key": "canonical-keywords", "slug": "canonical-keywords", "title": "关键词云"},
    {"key": "focus-gaps", "slug": "focus-gaps", "title": "优先改进薄弱项"},
    {"key": "non-actionable-gaps", "slug": "non-actionable-gaps", "title": "低权重硬约束"},
    {"key": "interview-gaps", "slug": "interview-gaps", "title": "面试复盘薄弱项"},
    {"key": "prep-gaps", "slug": "prep-gaps", "title": "备战清单"},
]


def build_site(output_dir: Path, weekly_only: bool = False) -> None:
    env = make_env()

    # 全量生成时先清理旧站点文件，避免历史页面残留导致样式版本不一致。
    if not weekly_only and output_dir.exists():
        shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    jobs = load_all_jobs()
    resume_entries = collect_resume_entries(jobs)
    insights = load_insights()
    generated_at = date.today().isoformat()

    # 复制静态资源
    assets_src = REPORTS / "assets"
    assets_dst = output_dir / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    # 仅复制当前岗位可用的简历 PDF，避免已删除岗位的旧产物混入站点。
    copy_valid_resumes(output_dir, resume_entries)

    if weekly_only:
        # 仅生成本周周报
        weekly = insights["weekly_summary"]
        week_id = weekly.get("week", date.today().strftime("%Y-W%V"))
        render(env, "weekly.html.j2", {
            "weekly": weekly,
            "generated_at": generated_at,
        }, output_dir / "weekly" / f"{week_id}.html")
        # 更新周报列表（追加入 index）
        _build_weekly_index(env, output_dir, generated_at)
        return

    # Dashboard
    stage_counts = {s: 0 for s in STAGE_ORDER}
    for j in jobs:
        s = normalize_stage(j["status"].get("current_stage", "unknown"))
        stage_counts[s] = stage_counts.get(s, 0) + 1

    patterns = insights.get("interview_patterns", {})
    recent_timeline = patterns.get("recent_timeline", [])

    render(env, "dashboard.html.j2", {
        "jobs": jobs,
        "resume_entries": resume_entries,
        "stage_counts": stage_counts,
        "stage_label": STAGE_LABEL,
        "insights": insights,
        "recent_timeline": recent_timeline[:5],
        "generated_at": generated_at,
    }, output_dir / "index.html")

    # Insights 页
    render(env, "insights.html.j2", {
        "insights": insights,
        "stage_label": STAGE_LABEL,
        "generated_at": generated_at,
    }, output_dir / "insights.html")

    # Insights 详情页（每张卡片单独页面）
    insight_detail_dir = output_dir / "insights"
    if insight_detail_dir.exists():
        shutil.rmtree(insight_detail_dir)
    for detail in INSIGHT_DETAIL_PAGES:
        render(env, "insight_detail.html.j2", {
            "insights": insights,
            "detail": detail,
            "stage_label": STAGE_LABEL,
            "generated_at": generated_at,
        }, insight_detail_dir / f"{detail['slug']}.html")

    # 简历下载页（GitHub Pages 不支持目录 listing，必须有 index.html）。
    render(env, "resumes.html.j2", {
        "jobs": jobs,
        "resume_entries": resume_entries,
        "generated_at": generated_at,
    }, output_dir / "resumes" / "index.html")

    # 单岗位详情页
    for j in jobs:
        render(env, "per_job.html.j2", {
            "job": j,
            "stage_label": STAGE_LABEL,
            "generated_at": generated_at,
        }, output_dir / "jobs" / f"{j['id']}.html")

    # 岗位列表
    render(env, "per_job.html.j2", {
        "job": None,
        "jobs": jobs,
        "job_groups": build_job_groups(jobs),
        "stage_label": STAGE_LABEL,
        "generated_at": generated_at,
        "is_list": True,
    }, output_dir / "jobs" / "index.html")

    # 周报
    weekly = insights["weekly_summary"]
    week_id = weekly.get("week", date.today().strftime("%Y-W%V"))
    render(env, "weekly.html.j2", {
        "weekly": weekly,
        "generated_at": generated_at,
    }, output_dir / "weekly" / f"{week_id}.html")
    _build_weekly_index(env, output_dir, generated_at)


def _build_weekly_index(env: Environment, output_dir: Path, generated_at: str) -> None:
    weekly_dir = output_dir / "weekly"
    weeks = sorted(
        [p.stem for p in weekly_dir.glob("*.html") if p.stem != "index"],
        reverse=True,
    )
    render(env, "weekly.html.j2", {
        "weekly": None,
        "weeks": weeks,
        "generated_at": generated_at,
        "is_index": True,
    }, weekly_dir / "index.html")


# ── 入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="output/site/", help="输出目录")
    parser.add_argument("--weekly", action="store_true", help="仅生成本周周报")
    args = parser.parse_args()

    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {'weekly report' if args.weekly else 'full site'} → {output_dir.relative_to(ROOT)}")
    build_site(output_dir, weekly_only=args.weekly)


if __name__ == "__main__":
    main()
