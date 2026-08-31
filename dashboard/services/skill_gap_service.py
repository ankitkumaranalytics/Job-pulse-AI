"""Skill Gap Analysis service (FEATURE 5).

Compares the user's skills against target-role requirements mined from
real postings (via the existing ``models.skill_gap.SkillGapAnalyzer``)
and produces a prioritised learning queue:

priority = 45% posting frequency + 35% importance weight + 20% how
foundational the skill is for further learning.
"""
from __future__ import annotations

from dashboard.utils.scoring import clamp100
from dashboard.utils.validation import ServiceError

_FOUNDATIONAL_SKILLS = {"SQL", "Python", "Excel", "Statistics"}
_IMPORTANCE_WEIGHT = {"Critical": 3.0, "Important": 2.0, "Optional": 1.0}
_BUCKET_THRESHOLDS = {"High": 65.0, "Medium": 45.0}  # below Medium -> Low


def _bucket(priority: float) -> str:
    if priority >= _BUCKET_THRESHOLDS["High"]:
        return "High"
    if priority >= _BUCKET_THRESHOLDS["Medium"]:
        return "Medium"
    return "Low"


def analyze_skill_gap(
    df,
    user_skills: list[str],
    target_role: str,
    top_n: int = 25,
) -> dict:
    """
    Returns {
      gap_score, total_required, matched_skills, missing_count,
      priorities: [ {skill, priority, importance, frequency_pct,
                     category, bucket} ], bucketed: {High: [], Medium: [], Low: []},
      scoring_basis
    }.
    """
    from models.skill_gap import SkillGapAnalyzer  # existing engine (reused)

    if df is None or len(df) == 0:
        raise ServiceError("Skill gap analysis needs job data to work.")
    if not target_role:
        raise ServiceError("Choose a target role to analyse your skill gap.")

    analyzer = SkillGapAnalyzer(df)
    role_postings = 0
    if "standardized_job_title" in df.columns:
        role_postings = int((df["standardized_job_title"] == target_role).sum())
    if role_postings == 0:
        raise ServiceError(
            f"No postings found for role '{target_role}' in the loaded dataset."
        )

    required = analyzer.get_required_skills(target_role, top_n=top_n) or []
    if not required:
        raise ServiceError(
            f"No skill requirements could be mined for '{target_role}'."
        )

    user_set = {s.lower() for s in (user_skills or [])}
    max_count = max((cnt for _, cnt, _ in required), default=1) or 1

    matched: list[str] = []
    priorities: list[dict] = []
    total_weight = 0.0
    missing_weight = 0.0

    from src.skill_extractor import get_skill_category

    for skill, count, importance in required:
        weight = _IMPORTANCE_WEIGHT.get(importance, 1.0)
        total_weight += weight
        if skill.lower() in user_set:
            matched.append(skill)
            continue
        missing_weight += weight
        freq_pct = 100.0 * count / role_postings
        priority = clamp100(
            0.45 * (100.0 * count / max_count)
            + 0.35 * (100.0 * weight / 3.0)
            + 0.20 * (100.0 if skill in _FOUNDATIONAL_SKILLS else 40.0)
        )
        priorities.append({
            "skill": skill,
            "priority": priority,
            "importance": importance,
            "frequency_pct": round(freq_pct, 1),
            "category": get_skill_category(skill),
            "bucket": _bucket(priority),
        })

    priorities.sort(key=lambda p: -p["priority"])
    bucketed: dict[str, list[dict]] = {"High": [], "Medium": [], "Low": []}
    for item in priorities:
        bucketed[item["bucket"]].append(item)

    gap_score = clamp100(100.0 * missing_weight / total_weight) if total_weight else 0.0
    return {
        "gap_score": gap_score,
        "total_required": len(required),
        "matched_skills": matched,
        "missing_count": len(priorities),
        "priorities": priorities,
        "bucketed": bucketed,
        "scoring_basis": (
            "priority = 45% posting frequency + 35% importance weight "
            "(Critical > Important > Optional) + 20% foundational-boost; "
            "gap_score = missing importance share of the role's requirements."
        ),
    }