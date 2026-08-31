"""
⭐ AI Career Advisor — the hero feature of JobPulse AI (Phases 9-12).

Two-column career assessment: build a profile on the left, receive a
full career intelligence report on the right — readiness gauge, skill
gap analysis, data-driven learning roadmap, career insights and a
bridge to job recommendations.

Every number is computed from the loaded dataset via
``models.skill_gap.SkillGapAnalyzer``; nothing is hardcoded or fabricated.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.premium import (
    cta_block,
    empty_state,
    insight_card,
    job_card,
    kpi_row,
    page_header,
    readiness_classification,
    readiness_gauge,
    roadmap_card,
    section_header,
    skill_badges,
)
from models.job_recommender import JobRecommender
from models.skill_gap import SkillGapAnalyzer
from src.skill_extractor import SKILL_CATEGORIES, get_all_skills

EXP_YEARS = {"Fresher": 0.0, "Entry Level": 1.5, "Mid Level": 3.5, "Senior Level": 7.0}
ROADMAP_LEVELS = ["High Priority", "Core Skill", "Advanced Skill", "Bonus Skill"]
BAND_CLASS = {
    "Needs Development": "b-low",
    "Building Foundation": "b-mid",
    "Job Ready": "b-good",
    "Highly Competitive": "b-high",
}


@st.cache_resource(show_spinner="Preparing the recommendation engine…")
def _get_recommender(df: pd.DataFrame) -> JobRecommender:
    recommender = JobRecommender(df)
    recommender.fit()
    return recommender


def _popular_skills_first(df: pd.DataFrame) -> list[str]:
    """Order the skill dictionary so the most in-demand skills appear first."""
    demanded: list[str] = []
    if "extracted_skills" in df.columns:
        counts = (
            df["extracted_skills"]
            .apply(lambda x: x if isinstance(x, (list, set)) else [])
            .explode()
            .dropna()
            .value_counts()
        )
        demanded = [s for s in counts.index if isinstance(s, str)]
    rest = [s for s in get_all_skills() if s not in demanded]
    return demanded + rest


def render(df: pd.DataFrame) -> None:
    """Render the AI Career Advisor — the hero feature of JobPulse AI."""
    page_header(
        "⭐ AI Career Advisor",
        "Discover how ready you are for your target role, identify skill gaps, "
        "and get a personalized learning roadmap — all powered by real market data.",
        eyebrow="06 · AI Career Advisor",
    )

    if "extracted_skills" not in df.columns:
        empty_state(
            "Skill Data Missing",
            "This dataset has no skill information. Run the data pipeline to "
            "enable the AI Career Advisor.",
        )
        return

    analyzer = SkillGapAnalyzer(df)

    col_left, col_right = st.columns([5, 7], gap="large")

    with col_left:
        section_header("Build Your Career Profile", "Tell us about your career goals")

        available_roles = analyzer.get_available_roles()
        if not available_roles:
            empty_state(message="No job roles found in the dataset.")
            return

        target_role = st.selectbox(
            "🎯 Target Role",
            available_roles, index=0, key="ca_role",
        )
        user_skills = st.multiselect(
            "🧠 Current Skills",
            options=_popular_skills_first(df), default=[], key="ca_skills",
        )
        experience = st.selectbox(
            "📅 Experience Level",
            ["Fresher", "Entry Level", "Mid Level", "Senior Level"],
            index=1, key="ca_exp",
        )
        loc_options = ["Any Location"] + sorted(
            df["city"].dropna().unique().tolist() if "city" in df.columns else []
        )
        preferred_location = st.selectbox(
            "📍 Preferred Location", loc_options, index=0, key="ca_loc",
        )
        analyze_clicked = st.button(
            "✨ Analyze My Career", type="primary",
            use_container_width=True, key="ca_analyze",
        )
        # A Streamlit button is only True during the single run right after
        # its click. Persisting the flag keeps the report (and its
        # "View Recommended Jobs" CTA) alive across reruns — otherwise any
        # later interaction, including clicking that CTA, would re-run the
        # script with analyze_clicked=False and silently drop the click.
        if analyze_clicked:
            st.session_state["ca_report_visible"] = True

    with col_right:
        if not st.session_state.get("ca_report_visible"):
            st.markdown(
                '<div class="cta-block"><div class="cta-title">'
                "Your Career Intelligence Report</div>"
                '<div class="cta-text">Fill in your profile on the left and click '
                "<strong>Analyze My Career</strong> to generate your report."
                "</div></div>",
                unsafe_allow_html=True,
            )
            return

        with st.spinner("Calculating your skill match and career readiness..."):
            result = analyzer.calculate_readiness_score(user_skills, target_role)

        if "error" in result:
            empty_state("Insufficient Data", result["error"])
            return

        section_header("Your Career Readiness", f"Target role: {target_role}")
        score = result["score"]
        classification = readiness_classification(score)
        band = BAND_CLASS.get(classification, "b-mid")
        readiness_gauge(score)
        st.markdown(
            f'<div class="readiness-badge {band}">{classification} &middot; {score:.0f}%</div>',
            unsafe_allow_html=True,
        )
        kpi_row([
            {"title": "Skills Matched",
             "value": f"{result['total_matched']}/{result['total_required']}",
             "sub": f"{result['skill_match_pct']}% match", "accent": True},
            {"title": "Critical Skills",
             "value": str(result["skill_breakdown"]["critical"]["matched"]),
             "sub": f"of {result['skill_breakdown']['critical']['required']} required"},
            {"title": "Important Skills",
             "value": str(result["skill_breakdown"]["important"]["matched"]),
             "sub": f"of {result['skill_breakdown']['important']['required']} required"},
        ])

        st.divider()
        section_header("Your Strengths", "Skills you already have that the market demands")
        if result["matched_skills"]:
            skill_badges(result["matched_skills"], kind="have")
        else:
            st.markdown(
                '<div class="empty-state">No matching skills found. '
                "Try adding more skills to your profile.</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        section_header("Skills You Should Learn", "Prioritized by market demand for your target role")
        missing = result["missing_skills"]
        if missing["critical"]:
            st.markdown('<div class="label-critical">Critical Skills Missing</div>', unsafe_allow_html=True)
            skill_badges(missing["critical"], kind="missing")
        if missing["important"]:
            st.markdown('<div class="label-important">Important Skills Missing</div>', unsafe_allow_html=True)
            skill_badges(missing["important"], kind="missing")
        if not missing["critical"] and not missing["important"] and not missing["optional"]:
            st.success("You have all the important skills for this role!")

        # ---- Priority skill gap (FEATURE 5 upgrade) ----
        try:
            from dashboard.services.skill_gap_service import analyze_skill_gap

            gaps = analyze_skill_gap(df, user_skills, target_role)
            section_header(
                "Priority Skills to Learn",
                kicker="Weighted by posting frequency, importance and foundational value",
            )
            for bucket, icon in (("High", "🔴"), ("Medium", "🟠"), ("Low", "🟢")):
                items = gaps["bucketed"][bucket]
                if items:
                    st.markdown(f"**{icon} {bucket} priority**")
                    st.markdown(
                        "".join(
                            f'<span class="skill-badge badge-missing">✗ {p["skill"]} '
                            f'({p["frequency_pct"]:.0f}% of postings)</span>'
                            for p in items[:6]
                        ),
                        unsafe_allow_html=True,
                    )
            st.caption(gaps["scoring_basis"])
        except Exception:  # noqa: BLE001 - gap analysis is best-effort
            pass

        st.divider()
        section_header("Your Recommended Learning Roadmap", "Data-driven priority order")
        recommendations = result["recommendations"]
        if recommendations:
            for i, skill in enumerate(recommendations[:6]):
                level = ROADMAP_LEVELS[min(i, len(ROADMAP_LEVELS) - 1)]
                required = analyzer.get_required_skills(target_role, top_n=20)
                reason = next(
                    (f"Appears in {cnt} job postings for {target_role}"
                     for s, cnt, _ in required if s == skill),
                    f"Frequently required for {target_role} roles",
                )
                roadmap_card(i + 1, level, skill, reason)
        else:
            st.info("No additional skills recommended — you're well prepared!")

        # ---- Roadmap progress tracking (FEATURE 6 upgrade) ----
        if recommendations:
            done_key = "ca_completed_skills"
            done_set = set(st.session_state.get(done_key, []))
            st.markdown("#### 🗺 Your learning progress")
            progress_cols = st.columns(3)
            for i, skill in enumerate(recommendations[:9]):
                with progress_cols[i % 3]:
                    st.checkbox(
                        skill,
                        value=skill in done_set,
                        key=f"ca_done_{skill}",
                    )
            done_now = {
                s for s in recommendations[:9]
                if st.session_state.get(f"ca_done_{s}")
            }
            st.session_state[done_key] = sorted(done_now)
            pct = 100.0 * len(done_now) / max(1, len(recommendations[:9]))
            st.progress(min(1.0, max(0.0, pct / 100.0)))
            st.caption(
                f"**{pct:.0f}% of your priority skills learned** "
                f"({len(done_now)}/{len(recommendations[:9])}). "
                "Tick skills as you master them — progress is tracked for this session."
            )

        st.divider()
        section_header("Career Insights", "Personalized observations based on your profile")
        for insight in _generate_insights(result, target_role, user_skills, df):
            insight_card(insight)

    # ---- BRIDGE TO JOB RECOMMENDATIONS (Phase 12) ----
    st.divider()
    section_header("Your Best Job Matches", "Ready to see which jobs fit your profile?")
    st.session_state["career_profile"] = {
        "role": target_role,
        "skills": user_skills,
        "exp_level": experience,
        "location": preferred_location,
    }
    cta_block(
        title="See Your Personalized Job Matches",
        message=f"Based on your profile — {target_role} with {len(user_skills)} skills — "
        "we'll find the best-matching jobs using TF-IDF + weighted matching.",
        button_label="View Recommended Jobs →",
        nav_label="Job Recommendations",
        key="ca_to_jobs",
    )


def _generate_insights(
    result: dict, target_role: str, user_skills: list[str], df: pd.DataFrame
) -> list[str]:
    """Generate 3-5 dynamic, data-driven career insights (Phase 11)."""
    insights: list[str] = []
    total_required = result["total_required"]
    total_matched = result["total_matched"]
    score = result["score"]
    missing = result["missing_skills"]

    if total_required > 0:
        insights.append(
            f"You currently match **{total_matched} of the top {total_required} important skills** "
            f"for the **{target_role}** role."
        )

    if "extracted_skills" in df.columns and user_skills:
        from src.skill_extractor import SKILL_CATEGORIES

        cat_counts: dict[str, int] = {}
        for skill in user_skills:
            cat = SKILL_CATEGORIES.get(skill, "Other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if cat_counts:
            top_cat = max(cat_counts, key=cat_counts.get)
            insights.append(
                f"Your strongest skill category is **{top_cat}** "
                f"({cat_counts[top_cat]} skills)."
            )

    if missing["critical"]:
        insights.append(
            f"**{missing['critical'][0]}** is one of your highest-priority missing skills "
            f"based on market demand for {target_role}."
        )
    elif missing["important"]:
        insights.append(
            f"**{missing['important'][0]}** is a key skill to add — it appears frequently "
            f"in {target_role} job postings."
        )

    if missing["critical"] or missing["important"]:
        n_missing = len(missing["critical"]) + len(missing["important"])
        insights.append(
            f"Adding the top **{min(n_missing, 2)} missing skills** could significantly "
            f"improve your skill coverage and readiness score."
        )

    if score >= 80:
        insights.append("You are **highly competitive** for this role. Keep refining your edge!")
    elif score >= 60:
        insights.append("You are **job ready** — closing the remaining gaps will make you even stronger.")
    elif score >= 40:
        insights.append("You are **building a solid foundation** — focus on the critical skills first.")
    else:
        insights.append("You are in the **early stages** — the roadmap above is your step-by-step plan.")

    return insights[:5]