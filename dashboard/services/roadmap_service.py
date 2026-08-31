"""Personalized Career Roadmap service (FEATURE 6).

Groups prioritised missing skills into phased, time-boxed learning
blocks (Foundation → SQL → Programming → Visualization → Advanced →
Cloud/Engineering → Portfolio) and computes progress tracking.

Skills are assigned to the FIRST phase whose focus list contains them;
anything unmatched lands in 'Portfolio & Practice' so no skill is lost.
Durations scale with skill count: max(2 weeks, 1.5 weeks per skill).
"""
from __future__ import annotations

from dashboard.utils.scoring import clamp100

# Ordered phase blueprint: (phase name, focus, skills belonging to it)
PHASE_BLUEPRINT: list[tuple[str, str, set[str]]] = [
    (
        "Foundation",
        "Spreadsheets, statistics fundamentals and data cleaning habits",
        {"Excel", "Statistics"},
    ),
    (
        "SQL & Databases",
        "Joins, aggregations, window functions and query optimisation",
        {"SQL", "MySQL", "PostgreSQL", "SQL Server", "SQLite", "BigQuery", "Snowflake", "Oracle"},
    ),
    (
        "Programming & Analysis",
        "Python for data: pandas, NumPy and reproducible notebooks",
        {"Python", "R", "Pandas", "NumPy", "Scikit-learn"},
    ),
    (
        "Visualization & BI",
        "Dashboards, DAX measures and executive storytelling",
        {"Power BI", "Tableau", "Looker", "Qlik", "Matplotlib", "Seaborn", "Plotly", "D3.js"},
    ),
    (
        "Advanced Analytics & ML",
        "Predictive modelling and experimentation",
        {"Machine Learning", "NLP", "Computer Vision", "TensorFlow", "PyTorch",
         "XGBoost", "LightGBM", "Hugging Face", "ONNX"},
    ),
    (
        "Cloud & Data Engineering",
        "Pipelines, orchestration and warehouses at scale",
        {"AWS", "Azure", "GCP", "Spark", "Hadoop", "Airflow", "Kafka", "DBT",
         "Fivetran", "NiFi", "Elasticsearch", "Redis", "Cassandra", "MongoDB",
         "Scala", "Java", "JavaScript", "Go", "Rust", "C++", "C#", "Shell"},
    ),
]

_PORTFOLIO_PHASE = (
    "Portfolio & Practice",
    "Capstone projects that prove the skills above to recruiters",
)


def build_roadmap(
    priority_skills: list[str],
    target_role: str = "",
    completed_skills: set[str] | None = None,
) -> dict:
    """
    Build a phased roadmap from an ordered (highest-priority-first) skill list.

    Returns {phases: [...], total_skills, completed_skills,
             completion_pct, target_role}.
    """
    completed = {s.lower() for s in (completed_skills or [])}
    assigned: dict[str, list[str]] = {}
    seen: set[str] = set()

    for skill in priority_skills:
        key = str(skill).strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        for name, _focus, members in PHASE_BLUEPRINT:
            if key in members:
                assigned.setdefault(name, []).append(key)
                break
        else:
            assigned.setdefault(_PORTFOLIO_PHASE[0], []).append(key)

    # Always close with a portfolio phase when any technical skill exists
    if seen and _PORTFOLIO_PHASE[0] not in assigned:
        assigned[_PORTFOLIO_PHASE[0]] = [
            f"Role-aligned capstone: {target_role or 'Data Analytics'} project"
        ]

    phases: list[dict] = []
    ordered_names = [n for n, _f, _m in PHASE_BLUEPRINT if n in assigned]
    if _PORTFOLIO_PHASE[0] in assigned:
        ordered_names.append(_PORTFOLIO_PHASE[0])

    for name in ordered_names:
        skills = assigned[name]
        focus = _PORTFOLIO_PHASE[1] if name == _PORTFOLIO_PHASE[0] else next(
            f for n, f, _m in PHASE_BLUEPRINT if n == name
        )
        remaining = [s for s in skills if s.lower() not in completed]
        phases.append({
            "phase": f"PHASE {len(phases) + 1} — {name.upper()}",
            "name": name,
            "focus": focus,
            "skills": skills,
            "remaining": remaining,
            "duration_weeks": max(2, round(1.5 * len(skills))),
            "completed_in_phase": len(skills) - len(remaining),
        })

    total = len(seen)
    done = len(seen & completed) if completed else 0
    return {
        "phases": phases,
        "total_skills": total,
        "completed_skills": done,
        "completion_pct": clamp100(100.0 * done / total) if total else 0.0,
        "target_role": target_role,
    }