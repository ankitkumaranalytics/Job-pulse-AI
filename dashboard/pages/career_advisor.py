"""
Career Advisor page - skill gap analysis and career readiness score.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.skill_gap import SkillGapAnalyzer
from src.skill_extractor import get_all_skills


def render(df: pd.DataFrame) -> None:
    """Render the Career Advisor page."""
    st.markdown('<div class="page-title">🎯 Career Advisor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Discover your skill gap, your career readiness '
        'score, and personalised learning recommendations based on market demand.</div>',
        unsafe_allow_html=True,
    )

    if "extracted_skills" not in df.columns:
        st.error("Skill data is missing from this dataset. Run the data pipeline first.")
        return

    analyzer = SkillGapAnalyzer(df)
    roles = analyzer.get_available_roles()
    if not roles:
        st.warning("No job roles found in the dataset.")
        return

    # ---------------- User inputs ----------------
    st.markdown("### 👤 Your Profile")

    col1, col2 = st.columns(2)
    with col1:
        target_role = st.selectbox("🎯 Target Job Role", roles)
        st.selectbox(
            "📅 Experience Level",
            ["Fresher", "Entry Level", "Mid Level", "Senior Level"],
        )
    with col2:
        all_skills = get_all_skills()
        current_skills = st.multiselect(
            "🧠 Current Skills",
            options=all_skills,
            help="Select all skills you currently have.",
        )
        st.caption(f"Skills selected: {len(current_skills)}")

    st.text_input(
        "📍 Preferred Location (optional)",
        placeholder="e.g. Bangalore",
    )

    if not current_skills:
        st.info("Select at least one skill above to see your career readiness score.")
        return

    # ---------------- Career readiness score ----------------
    st.divider()
    st.markdown("### 📊 Career Readiness Analysis")

    result = analyzer.calculate_readiness_score(current_skills, target_role)

    if "error" in result and result.get("error"):
        st.warning(result["error"])
        return

    score = result["score"]
    color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"
    st.markdown(
        f"""
        <div style="text-align:center; padding:1.5rem;">
            <div style="font-size:4rem; font-weight:800; color:{color};">
                {score:.0f}%
            </div>
            <div style="font-size:1.1rem; color:#64748b;">
                Career Readiness Score for <strong>{target_role}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.progress(min(int(score), 100))

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Skill Match Percentage", f"{result['skill_match_pct']:.1f}%")
    with col2:
        st.metric(
            "Matched / Required",
            f"{result['total_matched']} / {result['total_required']}",
            help="Critical skills are weighted more heavily in the score.",
        )

    st.divider()

    # ---------------- Skills you have ----------------
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("### ✅ Skills You Already Have")
        if result["matched_skills"]:
            for skill in result["matched_skills"]:
                st.markdown(f'- <span class="skill-have">✓ {skill}</span>', unsafe_allow_html=True)
        else:
            st.caption("No matching skills yet.")

    # ---------------- Skills you should learn ----------------
    with col_r:
        st.markdown("### 📚 Skills You Should Learn")
        missing = result["missing_skills"]
        if missing["critical"] or missing["important"] or missing["optional"]:
            for skill in missing["critical"]:
                st.markdown(f'- <span class="skill-missing">✗ {skill} <em>(Critical)</em></span>', unsafe_allow_html=True)
            for skill in missing["important"]:
                st.markdown(f'- <span class="skill-missing">✗ {skill} <em>(Important)</em></span>', unsafe_allow_html=True)
            for skill in missing["optional"]:
                st.markdown(f'- <span style="color:#94a3b8;">◦ {skill} <em>(Optional)</em></span>', unsafe_allow_html=True)
        else:
            st.caption("You have all the required skills! 🎉")

    st.divider()

    # ---------------- Learning priority ----------------
    st.markdown("### 🎓 Recommended Learning Priority")
    recommendations = result["recommendations"]
    if recommendations:
        for i, skill in enumerate(recommendations[:8], 1):
            st.markdown(f"**{i}.** {skill}")

        st.divider()

        skill_freq = df["extracted_skills"].apply(
            lambda x: x if isinstance(x, (list, set)) else []
        ).explode()
        st.caption("**Why these skills?** Demand in the dataset:")
        for skill in recommendations[:5]:
            count = int((skill_freq == skill).sum())
            st.markdown(
                f"- **{skill}** — requested in {count:,} job postings"
                if count > 0 else f"- **{skill}** — trending"
            )
    else:
        st.success("You have mastered all the required skills for this role!")

    st.divider()

    # ---------------- Next steps ----------------
    st.markdown("### 🚀 Recommended Next Steps")
    if score >= 70:
        st.markdown(
            "✅ **You are well-prepared!** Focus on: applying to "
            f"**{target_role}** roles. Highlight your strongest skills in your "
            "resume and consider preparing for role-specific interview questions."
        )
    elif score >= 40:
        st.markdown(
            "🟡 **Good foundation, room to grow.** Prioritise learning the "
            "Critical skills above. Consider a structured course or hands-on "
            "projects to fill the gap. Target: **3-6 months** of focused learning."
        )
    else:
        st.markdown(
            "🔴 **Career switch requires effort.** Start with the fundamentals "
            f"of **{target_role}**. Build projects, complete a certification, "
            "and apply for entry-level roles to gain experience."
        )