"""
Salary Explorer page — "What is the salary potential?" (Phase 7).

KPI cards, distribution and salary-by-dimension views using only valid
salary records; degrades gracefully when salary data is insufficient.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import bar_chart, horizontal_bar, scatter_salary
from dashboard.components.filters import select_filter, show_no_data
from dashboard.components.metrics import fmt_lpa, fmt_number
from dashboard.components.premium import (
    cta_block,
    empty_state,
    insight_card,
    kpi_row,
    page_header,
    section_header,
)
from src import analytics

MIN_SALARY_RECORDS = 10
MIN_GROUP_RECORDS = 3


def render(df: pd.DataFrame) -> None:
    """Render the Salary Explorer page."""
    page_header(
        "Salary Explorer",
        "What is the salary potential? Distribution and averages by role, city and experience.",
        eyebrow="Step 3 · Understand the Pay",
    )

    if df is None or len(df) == 0:
        empty_state("No Data Available", "No job market data is loaded. Run the data pipeline first.")
        return

    if "salary_average" not in df.columns or df["salary_average"].notna().sum() < MIN_SALARY_RECORDS:
        found = int(df["salary_average"].notna().sum()) if "salary_average" in df.columns else 0
        st.warning(
            "⚠️ **Insufficient valid salary data is available for reliable salary "
            f"analysis.** Found only {found} records with a valid salary "
            f"(minimum {MIN_SALARY_RECORDS} required). No averages are shown to "
            "avoid misleading conclusions."
        )
        return

    salary_df = df.dropna(subset=["salary_average"]).copy()
    salary_df["salary_lpa"] = salary_df["salary_average"] / 100000

    # ---------------- Filters (Phase 8) ----------------
    st.markdown("##### Filters")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        sel_role = select_filter(salary_df, "standardized_job_title", "Job Role", key="se_role")
    with fcol2:
        sel_loc = select_filter(salary_df, "city", "Location", key="se_loc")
    with fcol3:
        sel_exp = select_filter(salary_df, "experience_category", "Experience", key="se_exp")
    with fcol4:
        sel_ind = select_filter(salary_df, "industry", "Industry", key="se_ind")

    filtered = salary_df.copy()
    if sel_role != "All":
        filtered = filtered[filtered["standardized_job_title"] == sel_role]
    if sel_loc != "All":
        filtered = filtered[filtered["city"] == sel_loc]
    if sel_exp != "All":
        filtered = filtered[filtered["experience_category"] == sel_exp]
    if sel_ind != "All":
        filtered = filtered[filtered["industry"] == sel_ind]

    if len(filtered) == 0:
        show_no_data()
        return

    # ---------------- KPI cards ----------------
    sal = filtered["salary_average"]
    coverage = len(filtered) / len(df) * 100 if len(df) else 0
    kpi_row([
        {"title": "Average Salary", "value": fmt_lpa(sal.mean()), "sub": "valid records only", "accent": True},
        {"title": "Median Salary", "value": fmt_lpa(sal.median()), "sub": "50th percentile"},
        {"title": "Highest Salary", "value": fmt_lpa(sal.max()), "sub": "in this segment"},
        {"title": "Salary Data Coverage", "value": f"{coverage:.0f}%",
         "sub": f"{fmt_number(len(filtered))} of {fmt_number(len(df))} postings"},
    ])

    # ---------------- Distribution ----------------
    st.divider()
    section_header("Salary Distribution", kicker="How pay is spread")
    fig = px.histogram(
        filtered, x="salary_lpa", nbins=30,
        labels={"salary_lpa": "Salary (LPA)"}, template="plotly_white",
    )
    fig.update_layout(margin=dict(l=40, r=20, t=40, b=40), height=380, title_font_size=16)
    st.plotly_chart(fig, use_container_width=True)

    # ---------------- Salary by dimension ----------------
    st.divider()
    section_header("Salary by Dimension", kicker="Role, location and experience")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Salary by Job Role**")
        sal_role = analytics.get_salary_by_role(filtered)
        if len(sal_role):
            sal_role = sal_role[sal_role["count"] >= MIN_GROUP_RECORDS]
        if len(sal_role):
            fig = horizontal_bar(sal_role, "avg_salary", "job_role", height=400)
            fig.update_layout(xaxis=dict(tickformat=".0s"))
            st.plotly_chart(fig, use_container_width=True)
            top_role = sal_role.sort_values("avg_salary", ascending=False).iloc[0]
            insight_card(
                f"**{top_role['job_role']}** shows the highest average salary "
                f"({fmt_lpa(top_role['avg_salary'])}) among roles with at least "
                f"{MIN_GROUP_RECORDS} salary records."
            )
        else:
            empty_state(message=f"Fewer than {MIN_GROUP_RECORDS} salary records per role in this selection.")
    with col_r:
        st.markdown("**Salary by Location**")
        sal_loc = analytics.get_salary_by_location(filtered)
        if len(sal_loc):
            fig = bar_chart(sal_loc, "location", "avg_salary", height=400)
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Locations shown require at least {MIN_GROUP_RECORDS} salary records.")
        else:
            empty_state(message="Not enough salary records by location in this selection.")

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        st.markdown("**Salary by Experience**")
        sal_exp = analytics.get_salary_by_experience(filtered)
        if len(sal_exp):
            st.plotly_chart(bar_chart(sal_exp, "experience", "avg_salary", height=360), use_container_width=True)
        else:
            empty_state(message="Not enough salary records by experience level.")
    with col_r2:
        st.markdown("**Experience vs Salary**")
        scatter_df = filtered.dropna(subset=["experience_min"])
        if len(scatter_df) >= MIN_SALARY_RECORDS:
            fig = scatter_salary(
                scatter_df, "experience_min", "salary_lpa",
                "standardized_job_title", height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            empty_state(message="Not enough data points for the scatter plot.")

    cta_block(
        "Who pays for these skills?",
        "See which companies are hiring for this segment and what they require.",
        "Explore Company Intelligence",
        "Company Intelligence",
        key="se_cta_company",
    )
    st.caption("Salary figures are computed from valid records in the loaded dataset only.")