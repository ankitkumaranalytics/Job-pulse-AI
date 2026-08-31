"""ATS scoring service (FEATURE 1, part 2).

Produces a transparent 0-100 ATS score with per-category factors.
Every component is deterministic rule-based logic and the report
explains exactly which factors moved each score — no opaque AI number.

Component weights live in ``dashboard.utils.constants.ATS_WEIGHTS``.
"""
from __future__ import annotations

import re

from dashboard.models.resume import ResumeProfile
from dashboard.utils.constants import ATS_WEIGHTS
from dashboard.utils.scoring import clamp100, weighted_score
from dashboard.utils.text_processing import (
    action_verb_count,
    has_quantified_achievements,
)

_BENCHMARK_SKILL_COUNT = 8  # breadth expected on data/analytics resumes


def _component(score: float, factors: list[str]) -> dict:
    return {"score": clamp100(score), "max": 100, "factors": factors}


def score_resume(
    profile: ResumeProfile,
    role_requirements: list[tuple[str, int, str]] | None = None,
) -> dict:
    """
    Score a parsed resume against an optional target role.

    ``role_requirements``: list of (skill, postings_count, importance),
    e.g. from ``SkillGapAnalyzer.get_required_skills(role, top_n=20)``.
    When omitted, neutral benchmarks keep the report honest.
    """
    text_lower = profile.text.lower()
    skills_set = {s.lower() for s in profile.skills}

    # ---------------- Skills Coverage (30%) ----------------
    if role_requirements:
        required = [s for s, _, _ in role_requirements]
        matched = [s for s in required if s.lower() in skills_set]
        coverage = 100.0 * len(matched) / len(required) if required else 0.0
        skills_comp = _component(
            coverage,
            [f"{len(matched)} of {len(required)} target-role skills present"],
        )
        missing_keywords = [s for s in required if s not in matched]
    else:
        coverage = min(100.0, 100.0 * len(profile.skills) / _BENCHMARK_SKILL_COUNT)
        skills_comp = _component(
            coverage,
            [f"{len(profile.skills)} skills detected "
             f"(benchmark for data/analytics resumes: ~{_BENCHMARK_SKILL_COUNT})"],
        )
        missing_keywords = []

    # ---------------- Keyword Optimization (25%) ----------------
    if role_requirements:
        keywords = [s for s, cnt, _ in sorted(role_requirements, key=lambda x: -x[1])][:15]
        present = [k for k in keywords if k.lower() in text_lower or k.lower() in skills_set]
        kw_score = 100.0 * len(present) / len(keywords) if keywords else 0.0
        kw_comp = _component(
            kw_score,
            [f"{len(present)}/{len(keywords)} high-frequency role keywords found "
             "in the resume text"],
        )
        missing_keywords = missing_keywords or [k for k in keywords if k not in present]
    else:
        kw_comp = _component(
            55.0 if profile.skills else 25.0,
            ["Neutral baseline — select a target role for keyword-optimised scoring"],
        )

    # ---------------- Experience Relevance (20%) ----------------
    exp_factors: list[str] = []
    exp_score = 0.0
    has_exp_section = any(
        k in ("experience", "work experience", "employment")
        for k in profile.sections_found
    )
    if has_exp_section:
        exp_score += 35
        exp_factors.append("Experience section found")
    else:
        exp_factors.append("No dedicated experience section detected")
    if profile.experience_years is not None:
        exp_score += 30
        exp_factors.append(f"Duration stated: {profile.experience_years:g} year(s)")
    else:
        exp_factors.append("No explicit 'N years' duration stated")
    if has_quantified_achievements(text_lower):
        exp_score += 35
        exp_factors.append("Contains quantified achievements (numbers/%)")
    else:
        exp_factors.append("No measurable achievements (add %, volumes, ₹ impact)")
    experience_comp = _component(exp_score, exp_factors)

    # ---------------- Resume Structure (15%) ----------------
    checks = [
        ("Email address", bool(profile.email), 15),
        ("Phone number", bool(profile.phone), 10),
        ("Professional summary/profile", any(
            k in profile.sections_found for k in ("summary", "profile", "objective")
        ), 15),
        ("Skills section", "skills" in " ".join(profile.sections_found), 20),
        ("Experience section", has_exp_section, 15),
        ("Education section", "education" in profile.sections_found, 15),
        ("Projects section", "projects" in profile.sections_found, 10),
    ]
    structure_score = sum(points for _, ok, points in checks if ok)
    structure_factors = [f"{'✓' if ok else '✗'} {name}" for name, ok, _ in checks]
    verbs = action_verb_count(text_lower)
    if verbs >= 5:
        structure_score = min(100, structure_score + 5)
        structure_factors.append(f"Strong action verbs ({verbs} achievement verbs)")
    structure_comp = _component(structure_score, structure_factors)

    # ---------------- Project Strength (10%) ----------------
    proj_factors: list[str] = []
    proj_score = 0.0
    if "projects" in profile.sections_found:
        proj_score += 35
        proj_factors.append("Projects section found")
    else:
        proj_factors.append("No projects section (add 2-3 data projects)")
    if profile.projects:
        proj_score += 30
        proj_factors.append(f"{len(profile.projects)} project entries detected")
    proj_blob = " ".join(profile.projects).lower()
    proj_skills = [s for s in profile.skills if s.lower() in proj_blob]
    if proj_skills:
        proj_score += 35
        proj_factors.append(f"Projects use relevant tech: {', '.join(proj_skills[:4])}")
    else:
        proj_factors.append("Projects do not reference the listed technical skills")
    project_comp = _component(proj_score, proj_factors)

    components = {
        "skills_coverage": skills_comp,
        "keyword_optimization": kw_comp,
        "experience_relevance": experience_comp,
        "structure": structure_comp,
        "project_strength": project_comp,
    }
    overall = weighted_score(
        {k: v["score"] for k, v in components.items()}, ATS_WEIGHTS
    )

    # ---------------- Recommendations ----------------
    recommendations: list[str] = []
    if not profile.contact_complete:
        recommendations.append("Add a professional email address and phone number at the top.")
    if missing_keywords:
        recommendations.append(
            "Include missing high-frequency keywords for the target role: "
            + ", ".join(missing_keywords[:6]) + "."
        )
    if not has_quantified_achievements(text_lower):
        recommendations.append(
            "Quantify achievements (e.g. 'reduced report time by 40%', "
            "'analysed 10k+ rows')."
        )
    if "projects" not in profile.sections_found:
        recommendations.append("Add a Projects section with 2-3 measurable data projects.")
    if verbs < 5:
        recommendations.append(
            "Start bullet points with achievement verbs (built, automated, improved)."
        )
    for warning in profile.warnings:
        recommendations.append(warning)

    strengths = [f for f in structure_factors if f.startswith("✓")]
    return {
        "overall": overall,
        "components": components,
        "missing_keywords": missing_keywords,
        "strengths": strengths,
        "recommendations": recommendations,
        "weights": ATS_WEIGHTS,
        "scoring_basis": (
            "Deterministic rule-based ATS simulation: section checklist, "
            "skill/keyword coverage and quantified-achievement detection. "
            "Not an official ATS vendor score."
        ),
    }
