"""
Skills Intelligence page - skill demand, role comparison, combos.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import horizontal_bar, donut_chart
from src import analytics
from src.skill_extractor import SKILL_CATEGORIES


def render(df: pd.DataFrame) -> None:
    """Render the Skills Intelligence page."""
    st.markdown('<div class="page-title">🧠 Skills Intelligence</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Understand which skills matter most — '
        'by demand, by role, and by location.</div>',
        unsafe_allow_html=True,
    )

    # ---------------- Top 20 skills ----------------
    st.markdown("### 🔝 Top 20 Most Demanded Skills")
    top_skills = analytics.get_top_skills(df, n=20)
    if len(top_skills) > 0:
        st.plotly_chart(
            horizontal_bar(top_skills, "count", "skill", height=500),
            use_container_width=True,
        )
    else:
        st.info("No skill data available")

    st.divider()

    # ---------------- Skill category distribution ----------------
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("### 📂 Skill Category Distribution")
        all_skills = df["extracted_skills"].tolist()
        category_counts = {}
        for skills in all_skills:
            if isinstance(skills, (list, set)):
                for s in skills:
                    cat = SKILL_CATEGORIES.get(s, "Other")
                    category_counts[cat] = category_counts.get(cat, 0) + 1
        if category_counts:
            items = sorted(category_counts.items(), key=lambda x: -x[1])
            st.plotly_chart(
                donut_chart([i[0] for i in items], [i[1] for i in items], height=380),
                use_container_width=True,
            )
        else:
            st.info("No skill category data")

    with col_r:
        st.markdown("### 🎯 Skills by Job Role")
        role = st.selectbox("Select Job Role", sorted(df["standardized_job_title"].unique()))
        if role:
            role_df = df[df["standardized_job_title"] == role]
            role_skills = analytics.get_top_skills(role_df, n=12)
            if len(role_skills) > 0:
                st.plotly_chart(
                    horizontal_bar(role_skills, "count", "skill", height=380),
                    use_container_width=True,
                )
            else:
                st.info(f"No skill data for {role}")

    st.divider()

    # ---------------- Skills by location ----------------
    st.markdown("### 📍 Skills by Location")
    col1, col2 = st.columns([1, 3])
    with col1:
        loc = st.selectbox("Select Location", ["All"] + sorted(df["city"].unique().tolist()))
    with col2:
        st.caption("Most in-demand skills in the selected location")

    if loc and loc != "All":
        loc_df = df[df["city"] == loc]
    else:
        loc_df = df

    loc_skills = analytics.get_top_skills(loc_df, n=15)
    if len(loc_skills) > 0:
        st.plotly_chart(
            horizontal_bar(loc_skills, "count", "skill", height=420),
            use_container_width=True,
        )
    else:
        st.info("No skill data for selected location")

    st.divider()

    # ---------------- Skill combinations ----------------
    st.markdown("### 🔗 Most Requested Skill Combinations")
    combos = analytics.get_skill_combinations(df, n=10)
    if len(combos) > 0:
        combos["combination"] = combos["skill_1"] + " + " + combos["skill_2"]
        st.dataframe(
            combos[["combination", "count"]].rename(
                columns={"combination": "Skill Combination", "count": "# Jobs"}
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No skill combination data available")

    st.divider()

    # ---------------- Role comparison ----------------
    st.markdown("### ⚖️ Compare Two Job Roles")

    roles = sorted(df["standardized_job_title"].unique().tolist())
    col1, col2 = st.columns(2)
    with col1:
        role1 = st.selectbox("Role A", roles, index=0)
    with col2:
        role2 = st.selectbox("Role B", roles, index=min(1, len(roles) - 1))

    if role1 and role2 and role1 != role2:
        comparison = analytics.get_role_comparison(df, role1, role2)
        if "error" not in comparison:
            col3, col4, col5 = st.columns(3)
            with col3:
                st.markdown("#### ✅ Common Skills")
                if comparison["common_skills"]:
                    st.markdown(
                        "".join(
                            f'<span class="tag">{s}</span>' for s in comparison["common_skills"][:15]
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("None")
            with col4:
                st.markdown(f"#### 🔵 Unique to {role1}")
                if comparison["unique_to_role1"]:
                    st.markdown(
                        "".join(
                            f'<span class="tag">{s}</span>' for s in comparison["unique_to_role1"][:10]
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("None")
            with col5:
                st.markdown(f"#### 🟠 Unique to {role2}")
                if comparison["unique_to_role2"]:
                    st.markdown(
                        "".join(
                            f'<span class="tag">{s}</span>' for s in comparison["unique_to_role2"][:10]
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("None")

            st.divider()

            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown(f"#### 💪 Most Important Skills — {role1}")
                for skill, count in comparison["top_skills_role1"][:10]:
                    st.markdown(f"- **{skill}** ({count:,} mentions)")
            with col_right:
                st.markdown(f"#### 💪 Most Important Skills — {role2}")
                for skill, count in comparison["top_skills_role2"][:10]:
                    st.markdown(f"- **{skill}** ({count:,} mentions)")
        else:
            st.warning(comparison.get("error", "Cannot compare roles"))
    else:
        st.info("Select two different roles to compare.")