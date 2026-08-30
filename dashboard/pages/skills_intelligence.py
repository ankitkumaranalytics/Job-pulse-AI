"""
Skills Intelligence page — "What skills does the market want?" (Phase 6).

Top skills with demand share, category distribution, skills by role and
a side-by-side role comparison — all computed from the dataset.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import donut_chart, horizontal_bar
from dashboard.components.premium import (
    cta_block,
    empty_state,
    insight_card,
    page_header,
    section_header,
    skill_badges,
)
from src import analytics
from src.utils import unique_options


def render(df: pd.DataFrame) -> None:
    """Render the Skills Intelligence page."""
    page_header(
        "Skills Intelligence",
        "What skills does the market want? Ranked demand, categories, roles and comparisons.",
        eyebrow="Step 2 · Understand the Skills",
    )

    if df is None or len(df) == 0:
        empty_state("No Data Available", "No job market data is loaded. Run the data pipeline first.")
        return

    # ---------------- Section 1 — Top skills ----------------
    section_header("Most Demanded Skills", kicker="Section 1 · Ranked market demand")
    top_skills = analytics.get_top_skills(df, n=20)
    if len(top_skills) == 0:
        empty_state(message="No skill data available. Run the skill extraction pipeline.")
        return

    ranked = top_skills.copy()
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    ranked["Coverage %"] = (ranked["count"] / len(df) * 100).round(1)
    ranked.columns = ["Rank", "Skill", "Demand (# postings)", "Coverage %"]
    st.dataframe(ranked, use_container_width=True, hide_index=True)
    st.plotly_chart(
        horizontal_bar(top_skills, "count", "skill", height=560),
        use_container_width=True,
    )
    s0 = top_skills.iloc[0]
    insight_card(
        f"**{s0['skill']}** appears in {s0['count'] / len(df) * 100:.0f}% of all "
        f"postings — the most universal skill in this dataset."
    )

    # ---------------- Section 2 — Skill categories ----------------
    st.divider()
    section_header("Skill Category Demand", kicker="Section 2 · Where demand concentrates")
    categories = analytics.get_skill_category_counts(df)
    col_l, col_r = st.columns([2, 3])
    with col_l:
        if len(categories):
            st.plotly_chart(
                donut_chart(categories["category"].tolist(),
                            categories["count"].tolist(), height=340),
                use_container_width=True,
            )
        else:
            empty_state(message="No skill category data available.")
    with col_r:
        if len(categories):
            cat_df = categories.head(8)
            st.plotly_chart(
                horizontal_bar(cat_df, "count", "category", height=340),
                use_container_width=True,
            )
        else:
            empty_state(message="No skill category data available.")
    if len(categories):
        c0 = categories.iloc[0]
        insight_card(
            f"**{c0['category']}** skills dominate demand with {int(c0['count']):,} "
            f"mentions across the dataset."
        )

    # ---------------- Section 3 — Skills by role ----------------
    st.divider()
    section_header("Skills by Job Role", kicker="Section 3 · Role-specific demand")
    roles = unique_options(df, "standardized_job_title")
    if not roles:
        empty_state(message="No job role data available.")
        return
    default_role = "Data Analyst" if "Data Analyst" in roles else roles[0]
    role = st.selectbox("Select a job role", roles, index=roles.index(default_role), key="si_role")
    role_df = df[df["standardized_job_title"] == role]
    role_skills = analytics.get_top_skills(role_df, n=12)
    if len(role_skills):
        st.plotly_chart(
            horizontal_bar(role_skills, "count", "skill", height=400),
            use_container_width=True,
        )
        rs = role_skills.iloc[0]
        insight_card(
            f"For **{role}** roles, **{rs['skill']}** leads demand — requested in "
            f"{int(rs['count']):,} of {len(role_df):,} postings "
            f"({rs['count'] / len(role_df) * 100:.0f}%)."
        )
    else:
        empty_state(message=f"No skill data for {role}.")

    # ---------------- Section 4 — Role comparison ----------------
    st.divider()
    section_header("Compare Two Roles", kicker="Section 4 · Side-by-side skills")
    col_a, col_b = st.columns(2)
    with col_a:
        role_a = st.selectbox("Role A", roles, index=0, key="si_role_a")
    with col_b:
        role_b = st.selectbox(
            "Role B", roles, index=min(1, len(roles) - 1), key="si_role_b"
        )

    if role_a == role_b:
        st.info("Select two different roles to compare.")
        return

    comparison = analytics.get_role_comparison(df, role_a, role_b)
    if "error" in comparison:
        st.warning(comparison["error"])
        return

    st.markdown(f"##### {role_a} vs {role_b}")
    st.caption(
        f"{comparison['role1_count']:,} postings for {role_a} · "
        f"{comparison['role2_count']:,} postings for {role_b}"
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**✅ Common Skills**")
        skill_badges(comparison["common_skills"][:12], kind="have")
        if not comparison["common_skills"]:
            st.caption("None")
    with c2:
        st.markdown(f"**🔵 Unique to {role_a}**")
        skill_badges(comparison["unique_to_role1"][:10])
        if not comparison["unique_to_role1"]:
            st.caption("None")
    with c3:
        st.markdown(f"**🟠 Unique to {role_b}**")
        skill_badges(comparison["unique_to_role2"][:10])
        if not comparison["unique_to_role2"]:
            st.caption("None")

    st.markdown("##### Skill Demand Comparison")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown(f"**Top skills — {role_a}**")
        df_a = pd.DataFrame(comparison["top_skills_role1"], columns=["skill", "count"])
        if len(df_a):
            st.plotly_chart(horizontal_bar(df_a, "count", "skill", height=360), use_container_width=True)
    with col_d2:
        st.markdown(f"**Top skills — {role_b}**")
        df_b = pd.DataFrame(comparison["top_skills_role2"], columns=["skill", "count"])
        if len(df_b):
            st.plotly_chart(horizontal_bar(df_b, "count", "skill", height=360), use_container_width=True)

    cta_block(
        "So — how do YOUR skills compare?",
        "Match your profile against this demand and get your Career Readiness Score.",
        "Analyze My Career",
        "⭐ AI Career Advisor",
        key="si_cta_advisor",
    )