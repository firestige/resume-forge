#!/usr/bin/env python3
"""
build.py — 简历构建脚本
用法:
  python scripts/build.py --full              # 从 base/ 构建完整版
  python scripts/build.py --job <dir>         # 构建指定岗位变体
  python scripts/build.py --all              # 构建所有岗位
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent.parent
BASE = ROOT / "base"
JOBS = ROOT / "jobs"
TEMPLATES = ROOT / "templates"
STYLES = ROOT / "styles"
OUTPUT = ROOT / "output" / "resumes"


# ── Markdown → LaTeX 转换 ─────────────────────────────────────────────────

def md_inline_to_tex(text: str) -> str:
    """将 Markdown 行内格式转换为 LaTeX 命令。"""
    # [text](url) -> \href{url}{text}
    text = re.sub(r'\[([^\]]+?)\]\((https?://[^\s)]+)\)', r'\\href{\2}{\1}', text)
    # **bold** → \textbf{bold}
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    # *italic* → \textit{italic}  (不匹配已处理的 **)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\\textit{\1}', text)
    # `code` → \texttt{code}
    text = re.sub(r'`(.+?)`', r'\\texttt{\1}', text)
    # % 需要转义
    text = text.replace('%', r'\%')
    return text


def md_to_tex(md: str) -> str:
    """
    将简单 Markdown 转换为 LaTeX。
    支持: 段落、无序列表(-)、行内加粗/斜体/代码
    """
    lines = md.strip().splitlines()
    result = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # 忽略 HTML 注释，避免辅助标记进入最终 PDF
        if stripped.startswith('<!--') and stripped.endswith('-->'):
            continue

        # 忽略 Markdown 标题，项目标题由 LaTeX 模板统一渲染
        if stripped.startswith('#'):
            continue

        if stripped.startswith('- ') or stripped.startswith('* '):
            # 列表项
            if not in_list:
                result.append(r'\begin{itemize}')
                in_list = True
            item_text = md_inline_to_tex(stripped[2:])
            result.append(f'  \\item {item_text}')
        else:
            if in_list:
                result.append(r'\end{itemize}')
                in_list = False
            if stripped:
                result.append(md_inline_to_tex(stripped))
            else:
                result.append('')  # 空行保留段落间距

    if in_list:
        result.append(r'\end{itemize}')

    return '\n'.join(result)


def md_to_skill_list(md: str) -> list[str]:
    """将 skills.md 中的 bullet 列表解析为字符串列表。"""
    items = []
    for line in md.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith('<!--') and stripped.endswith('-->'):
            continue
        if stripped.startswith('- ') or stripped.startswith('* '):
            items.append(md_inline_to_tex(stripped[2:]))
    return items


# ── 数据加载 ──────────────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_text(path: Path) -> str:
    with open(path, encoding='utf-8') as f:
        return f.read()


def load_base() -> dict:
    """加载完整 base/ 素材库。"""
    data = {}
    data['profile'] = load_yaml(BASE / 'profile.yaml')
    edu_yaml = load_yaml(BASE / 'education.yaml')
    data['education'] = edu_yaml.get('education', [])
    data['certifications'] = edu_yaml.get('certifications', [])
    data['experience'] = load_yaml(BASE / 'experience.yaml').get('experience', [])

    skills_md = load_text(BASE / 'skills.md')
    data['skills'] = md_to_skill_list(skills_md)

    # 加载所有项目
    projects_dir = BASE / 'projects'
    projects = {}
    for proj_dir in sorted(projects_dir.iterdir()):
        if proj_dir.is_dir():
            pid = proj_dir.name
            meta = load_yaml(proj_dir / 'meta.yaml')
            content_md = load_text(proj_dir / 'content.md')
            projects[pid] = {
                'meta': meta,
                'content_tex': md_to_tex(content_md),
            }
    data['projects_map'] = projects

    return data


def apply_variant(base: dict, job_dir: Path) -> dict:
    """将 variant/ 覆写规则合并到 base 数据上，返回新的数据字典。"""
    variant_dir = job_dir / 'variant'
    config_path = variant_dir / 'config.yaml'

    if not config_path.exists():
        print(f"  [warn] No variant/config.yaml found in {job_dir}, building full resume.")
        return build_full_context(base)

    config = load_yaml(config_path)
    data = dict(base)

    # Profile 覆写（如 title）
    if 'profile' in config:
        data['profile'] = {**base['profile'], **config['profile']}

    # 按 config.projects 顺序选材，优先使用 variant 叙事覆写
    project_ids = config.get('projects', list(base['projects_map'].keys()))
    projects = []
    for pid in project_ids:
        if pid not in base['projects_map']:
            print(f"  [warn] Project '{pid}' not found in base/, skipping.")
            continue
        proj = dict(base['projects_map'][pid])
        meta_override_path = variant_dir / 'projects' / f'{pid}.yaml'
        if meta_override_path.exists():
            meta_override = load_yaml(meta_override_path)
            proj = dict(proj)
            proj['meta'] = {**proj['meta'], **meta_override}
        override_path = variant_dir / 'projects' / f'{pid}.md'
        if override_path.exists():
            override_md = load_text(override_path)
            proj = dict(proj)
            proj['content_tex'] = md_to_tex(override_md)
        projects.append(proj)
    data['projects'] = projects

    # 工作经历筛选
    exp_ids = config.get('experience')
    if exp_ids:
        exp_map = {e['id']: e for e in base['experience']}
        data['experience'] = [exp_map[eid] for eid in exp_ids if eid in exp_map]
    else:
        data['experience'] = base['experience']

    # 技能覆写
    skills_override = variant_dir / 'skills.md'
    if skills_override.exists():
        data['skills'] = md_to_skill_list(load_text(skills_override))

    data['variant_ref'] = job_dir.name
    return data


def build_full_context(base: dict) -> dict:
    """构建完整版简历上下文（所有项目，base 顺序）。"""
    data = dict(base)
    # 展示顺序由 base/projects_order.yaml 决定，未列出的项目按目录名追加在后面
    order_path = BASE / 'projects_order.yaml'
    order = load_yaml(order_path).get('order', []) if order_path.exists() else []
    all_keys = list(base['projects_map'].keys())
    ordered_keys = [k for k in order if k in all_keys] + \
                   [k for k in all_keys if k not in order]
    data['projects'] = [base['projects_map'][k] for k in ordered_keys]
    data['variant_ref'] = None
    return data


# ── 渲染 & 编译 ───────────────────────────────────────────────────────────

def render_tex(context: dict, template_name: str = 'resume_zh.tex.j2') -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters['md_inline'] = md_inline_to_tex
    template = env.get_template(template_name)
    return template.render(**context)


def compile_pdf(tex_source: str, output_name: str) -> Path:
    """将 LaTeX 源码编译为 PDF，返回 PDF 路径。"""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build_dir = OUTPUT / f'_build_{output_name}'
    build_dir.mkdir(exist_ok=True)

    # 将 styles/ 软链接或复制到 build 目录（xelatex 需要 resume.cls）
    cls_src = STYLES / 'resume.cls'
    cls_dst = build_dir / 'resume.cls'
    if not cls_dst.exists():
        shutil.copy2(cls_src, cls_dst)

    # linespacing_fix.sty
    lsf_src = STYLES / 'linespacing_fix.sty'
    if lsf_src.exists():
        shutil.copy2(lsf_src, build_dir / 'linespacing_fix.sty')

    tex_path = build_dir / f'{output_name}.tex'
    tex_path.write_text(tex_source, encoding='utf-8')

    cmd = [
        'xelatex',
        '-interaction=nonstopmode',
        '-output-directory', str(build_dir),
        str(tex_path),
    ]

    print(f"  Compiling {output_name}.tex with xelatex ...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    pdf_src = build_dir / f'{output_name}.pdf'

    if not pdf_src.exists():
        print("  [ERROR] xelatex failed — no PDF produced. Last lines of log:")
        log_lines = result.stdout.splitlines()
        print('\n'.join(log_lines[-30:]))
        sys.exit(1)

    if result.returncode != 0:
        # 警告但有产出 — 打印摘要继续
        warnings = [l for l in result.stdout.splitlines()
                    if l.startswith('!') or 'Error' in l]
        if warnings:
            print(f"  [warn] xelatex warnings: {len(warnings)} line(s)")
    pdf_dst = OUTPUT / f'{output_name}.pdf'
    shutil.copy2(pdf_src, pdf_dst)
    print(f"  ✓ Output: {pdf_dst.relative_to(ROOT)}")
    return pdf_dst


# ── 入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Build resume PDF')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--full', action='store_true', help='Build base full resume')
    group.add_argument('--job', metavar='JOB_DIR', help='Build specific job variant')
    group.add_argument('--all', action='store_true', help='Build all job variants')
    args = parser.parse_args()

    print("Loading base data ...")
    base = load_base()

    if args.full:
        print("Building full resume ...")
        ctx = build_full_context(base)
        tex = render_tex(ctx)
        compile_pdf(tex, 'resume_full')

    elif args.job:
        job_dir = JOBS / args.job
        if not job_dir.exists():
            print(f"[ERROR] Job directory not found: {job_dir}")
            sys.exit(1)
        print(f"Building job variant: {args.job} ...")
        ctx = apply_variant(base, job_dir)
        tex = render_tex(ctx)
        compile_pdf(tex, args.job)

    elif args.all:
        job_dirs = [d for d in JOBS.iterdir()
                    if d.is_dir() and not d.name.startswith('_')]
        if not job_dirs:
            print("[warn] No job directories found.")
            return
        for job_dir in sorted(job_dirs):
            print(f"Building {job_dir.name} ...")
            ctx = apply_variant(base, job_dir)
            tex = render_tex(ctx)
            compile_pdf(tex, job_dir.name)


if __name__ == '__main__':
    main()
