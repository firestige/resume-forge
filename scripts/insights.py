#!/usr/bin/env python3
"""
insights.py — 跨岗位数据聚合，生成 jobs/_insights/*.yaml

用法:
  python scripts/insights.py           # 全量聚合
  python scripts/insights.py --weekly  # 仅输出本周周报所需摘要
"""

import argparse
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
JOBS = ROOT / "jobs"
INSIGHTS = JOBS / "_insights"


# ── 工具函数 ──────────────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def dump_yaml(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def iter_job_dirs():
    for d in sorted(JOBS.iterdir()):
        if d.is_dir() and not d.name.startswith("_"):
            yield d


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def is_application_event(event_text: str, result: str) -> bool:
    text = (event_text or "").strip()
    res = (result or "").strip()
    if re.search(r"投递简历|简历投递|已通过.+投递|通过.+投递", text):
        return True
    return res == "applied"


def is_prep_timeline_event(event_text: str, result: str) -> bool:
    text = (event_text or "").strip()
    res = (result or "").strip()
    if any(keyword in text for keyword in ["面试准备", "补课计划", "知识树", "追问清单", "口述稿", "冲刺", "表达优化", "归档为 interviews/prep_", "简历已提交并冻结"]):
        return True
    return res in {"prep_ready", "ready_for_interview_prep", "in_preparation", "interview_prep_refreshed", "expression_prep_refined", "resume_frozen_for_interview"}


def is_live_interview_event(event_text: str, result: str) -> bool:
    text = (event_text or "").strip()
    if is_prep_timeline_event(text, result):
        return False
    if any(keyword in text for keyword in ["预约", "安排面试", "面试时间"]):
        return False
    return bool(re.search(r"完成.*面试|已完成.*面试|一面|二面|三面|技术面|HR面|终面", text))


KEYWORD_CANONICAL_RULES = [
    (r"spring\s*boot|spring\s*cloud|spring\s*mvc|mybatis|eureka|apollo", "Spring 生态"),
    (r"java|go|python|c\+\+|javascript|typescript|vue", "语言与应用开发"),
    (r"redis|kafka|rabbitmq|rocketmq|mysql|oracle", "中间件与数据库"),
    (r"高并发|分布式|微服务|一致性|raft|paxos", "分布式与并发架构"),
    (r"性能|调优|jvm|gc|慢\s*sql|压测", "性能优化"),
    (r"sre|稳定性|可观测性|告警|降级|熔断", "稳定性工程"),
]

GAP_NON_ACTIONABLE_RULES = [
    r"\d+\s*年(以上|经验)",
    r"工作年限",
    r"学历",
    r"年龄",
    r"专业要求",
    r"行业经验",
    r"业务域经验",
    r"电商.*经验",
    r"物流.*经验",
    r"快递.*经验",
    r"快时尚.*经验",
    r"半导体.*经验",
]

ACTIONABLE_HORIZON_RULES = [
    (r"英语|english|口语|听力", "1-3个月"),
    (r"表达|沟通|自我介绍|口径", "2-4周"),
    (r"k8s|docker|oracle|mysql|mq|rabbitmq|kafka|rocketmq", "1-2个月"),
    (r"go|c\+\+|rtos|linux|云原生", "2-3个月"),
    (r"性能|调优|jvm|gc|慢\s*sql", "1-2个月"),
]


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


def canonicalize_keyword(keyword: str) -> str:
    text = (keyword or "").strip()
    low = text.lower()
    for pattern, canonical in KEYWORD_CANONICAL_RULES:
        if re.search(pattern, low):
            return canonical
    return text


def classify_keyword_category(keyword: str) -> str:
    low = (keyword or "").strip().lower()
    for pattern, canonical in KEYWORD_CANONICAL_RULES:
        if re.search(pattern, low):
            return canonical
    return "其他"


def is_non_actionable_gap(gap_text: str) -> bool:
    txt = (gap_text or "").strip().lower()
    return any(re.search(rule, txt) for rule in GAP_NON_ACTIONABLE_RULES)


def classify_gap_category(gap_text: str) -> str:
    txt = (gap_text or "").strip().lower()
    if is_non_actionable_gap(gap_text):
        return "硬性条件"
    if re.search(r"电商|物流|业务域|行业", txt):
        return "业务域迁移"
    if re.search(r"k8s|docker|oracle|go|c\+\+|rtos|云原生", txt):
        return "技能缺口"
    if re.search(r"表达|沟通|面试", txt):
        return "面试表达"
    if re.search(r"英语|english", txt):
        return "语言能力"
    return "可改进项"


def infer_improvement_horizon(gap_text: str, actionable: bool) -> str:
    if not actionable:
        return "不可直接改进"
    txt = (gap_text or "").strip().lower()
    for pattern, horizon in ACTIONABLE_HORIZON_RULES:
        if re.search(pattern, txt):
            return horizon
    return "1-2个月"


def gap_severity_weight(severity: str) -> int:
    sev = (severity or "").lower()
    return {"high": 3, "medium": 2, "low": 1}.get(sev, 1)


def is_prep_session(file_name: str, interview_record: dict) -> bool:
    round_name = str(interview_record.get("round", ""))
    result = str(interview_record.get("result", interview_record.get("overall_result", "")))
    if file_name.startswith("prep_"):
        return True
    if "准备" in round_name or "模拟" in round_name:
        return True
    if result in {"in_preparation", "ready_for_interview_prep"}:
        return True
    return False


def classify_interview_item(item: str) -> str:
    txt = (item or "").lower()
    if re.search(r"沟通|表达|20\s*秒|口径", txt):
        return "面试表达"
    if re.search(r"mysql|oracle|mq|rabbitmq|kafka|rocketmq|redis", txt):
        return "中间件与数据库"
    if re.search(r"性能|调优|jvm|gc|延迟|吞吐", txt):
        return "性能优化"
    if re.search(r"架构|trade-off|方案", txt):
        return "架构设计"
    if re.search(r"c\+\+|go|rtos|linux", txt):
        return "语言与系统能力"
    return "综合"


# ── 聚合逻辑 ──────────────────────────────────────────────────────────────

def aggregate_keyword_trends() -> dict:
    """统计所有 analysis.yaml 中 keywords 出现频次。"""
    must_counter: Counter = Counter()
    nice_counter: Counter = Counter()
    canonical_counter: Counter = Counter()
    category_counter: Counter = Counter()
    category_keywords: dict[str, set] = defaultdict(set)
    total_jobs = 0

    for job_dir in iter_job_dirs():
        ana = load_yaml(job_dir / "analysis.yaml")
        if not ana:
            continue
        total_jobs += 1
        kw = ana.get("keywords", {})
        job_seen_canonical = set()
        job_seen_category = set()
        for k in kw.get("must_have", []):
            must_counter[k] += 1
            canonical = canonicalize_keyword(k)
            cat = classify_keyword_category(k)
            category_keywords[cat].add(k)
            job_seen_canonical.add(canonical)
            job_seen_category.add(cat)
        for k in kw.get("nice_to_have", []):
            nice_counter[k] += 1
            canonical = canonicalize_keyword(k)
            cat = classify_keyword_category(k)
            category_keywords[cat].add(k)
            job_seen_canonical.add(canonical)
            job_seen_category.add(cat)

        for c in job_seen_canonical:
            canonical_counter[c] += 1
        for cat in job_seen_category:
            category_counter[cat] += 1

    def ranked(counter: Counter):
        return [
            {"keyword": k, "count": v, "pct": round(v / total_jobs * 100) if total_jobs else 0}
            for k, v in counter.most_common(20)
        ]

    return {
        "generated_at": date.today().isoformat(),
        "total_jobs": total_jobs,
        "must_have": ranked(must_counter),
        "nice_to_have": ranked(nice_counter),
        "canonical_keywords": ranked(canonical_counter),
        "category_heatmap": [
            {
                "category": c,
                "count": v,
                "pct": round(v / total_jobs * 100) if total_jobs else 0,
                "keywords": sorted(category_keywords[c])[:12],
            }
            for c, v in category_counter.most_common()
        ],
    }


def aggregate_skill_gaps() -> dict:
    """聚合 analysis.yaml 中的 gaps 和面试弱项。"""
    gap_records: dict[str, dict] = {}
    interview_weak: Counter = Counter()
    interview_weak_category: Counter = Counter()
    prep_focus: Counter = Counter()

    for job_dir in iter_job_dirs():
        # 来自 JD 分析
        ana = load_yaml(job_dir / "analysis.yaml")
        for gap in ana.get("gaps", []):
            # gaps 可能是字符串列表，也可能是含 gap/severity/strategy 的字典列表。
            if isinstance(gap, dict):
                gap_key = gap.get("gap", str(gap))
                severity = gap.get("severity", "")
            else:
                gap_key = str(gap)
                severity = ""

            rec = gap_records.setdefault(
                gap_key,
                {
                    "gap": gap_key,
                    "count": 0,
                    "severity_weight": 0,
                    "category": classify_gap_category(gap_key),
                    "actionable": not is_non_actionable_gap(gap_key),
                    "improve_horizon": infer_improvement_horizon(
                        gap_key,
                        not is_non_actionable_gap(gap_key),
                    ),
                },
            )
            rec["count"] += 1
            rec["severity_weight"] += gap_severity_weight(severity)

        # 来自面试记录
        interviews_dir = job_dir / "interviews"
        if interviews_dir.exists():
            for iv_file in sorted(interviews_dir.glob("*.yaml")):
                iv = load_yaml(iv_file)
                prep = is_prep_session(iv_file.stem, iv)
                for q in iv.get("questions", []):
                    if q.get("answer_quality") in ("weak", "poor"):
                        topic = q.get("notes", q.get("question", ""))[:80]
                        if prep:
                            prep_focus[topic] += 1
                        else:
                            interview_weak[topic] += 1
                            interview_weak_category[classify_interview_item(topic)] += 1
                for item in iv.get("action_items", []):
                    if prep:
                        prep_focus[item] += 1
                    else:
                        interview_weak[item] += 1
                        interview_weak_category[classify_interview_item(item)] += 1

    jd_gaps = []
    for rec in gap_records.values():
        rec["priority_score"] = round(
            rec["count"] * 2.0
            + rec["severity_weight"] * 1.5
            + (3.0 if rec["actionable"] else 0.0),
            2,
        )
        jd_gaps.append(rec)

    actionable = [x for x in jd_gaps if x["actionable"]]
    non_actionable = [x for x in jd_gaps if not x["actionable"]]
    actionable.sort(key=lambda x: (x["priority_score"], x["count"]), reverse=True)
    non_actionable.sort(key=lambda x: (x["priority_score"], x["count"]), reverse=True)

    return {
        "generated_at": date.today().isoformat(),
        "actionable_count": len(actionable),
        "non_actionable_count": len(non_actionable),
        "focus_gaps": actionable[:15],
        "non_actionable_gaps": non_actionable[:15],
        # 兼容旧模板字段：默认展示可改进项。
        "from_jd_gaps": actionable[:15],
        "from_interviews": [
            {
                "item": k,
                "count": v,
                "category": classify_interview_item(k),
            }
            for k, v in interview_weak.most_common(15)
        ],
        "from_interviews_by_category": [
            {"category": k, "count": v} for k, v in interview_weak_category.most_common()
        ],
        # 单独放置面试准备/模拟会话，不混入真实面试薄弱项。
        "from_prep": [
            {"item": k, "count": v} for k, v in prep_focus.most_common(15)
        ],
    }


def aggregate_interview_patterns() -> dict:
    """统计面试轮次、通过率、高频问题主题。"""
    stages = Counter()
    rounds_by_job = {}
    prep_by_job = {}
    total_rounds = 0
    passed = 0
    total_prep_rounds = 0

    for job_dir in iter_job_dirs():
        status = load_yaml(job_dir / "status.yaml")
        stage = normalize_stage(status.get("current_stage", "unknown"))
        stages[stage] += 1

        interviews_dir = job_dir / "interviews"
        rounds = []
        if interviews_dir.exists():
            for iv_file in sorted(interviews_dir.glob("*.yaml")):
                iv = load_yaml(iv_file)
                result = iv.get("result", iv.get("overall_result", ""))
                rec = {
                    "round": iv.get("round", iv_file.stem),
                    "date": iv.get("date", ""),
                    "result": result,
                }
                if is_prep_session(iv_file.stem, iv):
                    total_prep_rounds += 1
                    prep_by_job.setdefault(job_dir.name, []).append(rec)
                    continue

                total_rounds += 1
                if result == "passed":
                    passed += 1
                rounds.append(rec)
        if rounds:
            rounds_by_job[job_dir.name] = rounds

    timeline = []
    for job_dir in iter_job_dirs():
        status = load_yaml(job_dir / "status.yaml")
        for event in status.get("timeline", []):
            timeline.append({
                "job": job_dir.name,
                "date": str(event.get("date", "")),
                "event": event.get("event", ""),
                "result": event.get("result", ""),
            })
    timeline.sort(key=lambda x: x["date"], reverse=True)

    return {
        "generated_at": date.today().isoformat(),
        "stage_summary": dict(stages.most_common()),
        "total_interview_rounds": total_rounds,
        "total_prep_rounds": total_prep_rounds,
        "pass_rate": round(passed / total_rounds * 100) if total_rounds else 0,
        "rounds_by_job": rounds_by_job,
        "prep_by_job": prep_by_job,
        "recent_timeline": timeline[:20],
    }


def aggregate_weekly_summary() -> dict:
    """本周新增投递、面试、状态变化摘要。"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    patterns = aggregate_interview_patterns()
    gaps = aggregate_skill_gaps()
    self_model = load_yaml(INSIGHTS / "self_model.yaml")

    new_applications = []
    new_interviews = []
    new_prep_sessions = []

    for job_dir in iter_job_dirs():
        status = load_yaml(job_dir / "status.yaml")
        for event in status.get("timeline", []):
            ev_date_raw = event.get("date")
            if not ev_date_raw:
                continue
            try:
                ev_date = date.fromisoformat(str(ev_date_raw))
            except ValueError:
                continue
            if ev_date >= week_start:
                record = {
                    "job": job_dir.name,
                    "date": str(ev_date),
                    "event": event.get("event", ""),
                }
                event_text = event.get("event", "")
                result = event.get("result", "")
                if is_application_event(event_text, result):
                    new_applications.append(record)
                elif is_prep_timeline_event(event_text, result):
                    new_prep_sessions.append(record)
                elif is_live_interview_event(event_text, result):
                    new_interviews.append(record)

    recurring_weaknesses = self_model.get("recurring_weaknesses", [])
    suspected_strengths = self_model.get("suspected_strengths", [])
    positioning_hypotheses = self_model.get("positioning_hypotheses", [])
    recent_updates = self_model.get("recent_updates", [])

    stable_findings = [
        {
            "statement": item.get("statement", ""),
            "category": item.get("category", ""),
            "severity": item.get("severity", ""),
        }
        for item in recurring_weaknesses[:3]
        if item.get("statement")
    ]

    provisional_findings = []
    for item in suspected_strengths[:2]:
        provisional_findings.append({
            "kind": "待验证优势",
            "statement": item.get("statement", ""),
            "confidence": item.get("confidence", ""),
            "next_validation": item.get("next_validation", ""),
        })
    for item in positioning_hypotheses[:2]:
        provisional_findings.append({
            "kind": "定位假设",
            "statement": item.get("statement", ""),
            "confidence": item.get("confidence", ""),
            "next_validation": item.get("next_validation", ""),
        })

    action_candidates = []
    for item in recurring_weaknesses:
        action_candidates.extend(item.get("action_plan", []))
    for item in recent_updates:
        action_candidates.extend(item.get("action_required", []))
    for item in gaps.get("from_prep", [])[:6]:
        action_candidates.append(item.get("item", ""))

    priority_actions = dedupe_keep_order(action_candidates)[:8]
    evidence_jobs = sorted(patterns.get("prep_by_job", {}).keys())
    total_jobs = sum(patterns.get("stage_summary", {}).values())

    headline = "本周最稳定的模拟结论是：当前主要瓶颈不是单一技术点，而是经验尚未被稳定抽象成结构化表达。"
    if not stable_findings:
        headline = "本周尚未形成足够稳定的模拟结论，需继续补充 prep 样本。"

    return {
        "week": week_start.strftime("%Y-W%V"),
        "generated_at": today.isoformat(),
        "new_applications": new_applications,
        "new_interviews": new_interviews,
        "new_prep_sessions": new_prep_sessions,
        "overview": {
            "total_jobs": total_jobs,
            "total_prep_rounds": patterns.get("total_prep_rounds", 0),
            "total_interview_rounds": patterns.get("total_interview_rounds", 0),
            "validation_stage": self_model.get("validation_stage", "unknown"),
        },
        "readable_summary": {
            "headline": headline,
            "scope": f"基于 {patterns.get('total_prep_rounds', 0)} 份 prep 记录，覆盖 {len(evidence_jobs)} 个岗位方向。",
            "confidence_note": "当前结论证据级别为演绎模拟，面试链路仍待真实 round 求证。",
            "evidence_jobs": evidence_jobs,
        },
        "stable_findings": stable_findings,
        "provisional_findings": provisional_findings,
        "priority_actions": priority_actions,
    }


# ── 入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly", action="store_true", help="仅生成周报摘要")
    args = parser.parse_args()

    INSIGHTS.mkdir(parents=True, exist_ok=True)

    if args.weekly:
        summary = aggregate_weekly_summary()
        dump_yaml(summary, INSIGHTS / "weekly_summary.yaml")
        print(f"✓ weekly_summary.yaml ({summary['week']})")
    else:
        kw = aggregate_keyword_trends()
        dump_yaml(kw, INSIGHTS / "keyword_trends.yaml")
        print(f"✓ keyword_trends.yaml ({kw['total_jobs']} jobs)")

        gaps = aggregate_skill_gaps()
        dump_yaml(gaps, INSIGHTS / "skill_gaps.yaml")
        print(f"✓ skill_gaps.yaml")

        patterns = aggregate_interview_patterns()
        dump_yaml(patterns, INSIGHTS / "interview_patterns.yaml")
        print(f"✓ interview_patterns.yaml")

        summary = aggregate_weekly_summary()
        dump_yaml(summary, INSIGHTS / "weekly_summary.yaml")
        print(f"✓ weekly_summary.yaml")


if __name__ == "__main__":
    main()
