"""
Salary Explorer page - interactive salary analysis.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import horizontal_bar, bar_chart, scatter_salary
from dashboard.components.metrics import fmt_lpa
from src import analytics

MIN_SALARY_RECORDS = 10


def render(df: pd.DataFrame) -> None:
    """Render the Salary Explorer page."""
    st.markdown('<div class="page-title">💰 Salary Explorer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Explore salary distributions by role, '
        'location, experience, and industry.</div>',
        unsafe_allow_html=True,
    )

    # Filter to rows with salary data before showing anything
    if "salary_average" not in df.columns or df["salary_average"].notna().sum() < MIN_SALARY_RECORDS:
        st.warning(
            "⚠️ Insufficient salary data to display reliable charts. "
            f"Found only {df['salary_average'].notna().sum() if 'salary_average' in df.columns else 0} "
            f"records with a valid salary value (minimum {MIN_SALARY_RECORDS} required)."
        )
        return

    salary_df = df.dropna(subset=["salary_average"]).copy()
    salary_df["salary_lpa"] = salary_df["salary_average"] / 100000

    # ---------------- Filters ----------------
    st.markdown("### Filters")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        role = st.selectbox(
            "Job Role", ["All"] + sorted(salary_df["standardized_job_title"].unique().tolist())
        )
    with col2:
        loc = st.selectbox(
            "Location", ["All"] + sorted(salary_df["city"].unique().tolist())
        )
    with col3:
        exp = st.selectbox(
            "Experience", ["All"] + sorted(salary_df["experience_category"].unique().tolist())
        )
    with col4:
        ind = st.selectbox("Industry", ["All"] + sorted(salary_df["industry"].unique().tolist()))

    filtered = salary_df.copy()
    if role != "All":
        filtered = filtered[filtered["standardized_job_title"] == role]
    if loc != "All":
        filtered = filtered[filtered["city"] == loc]
    if exp != "All":
        filtered = filtered[filtered["experience_category"] == exp]
    if ind != "All":
        filtered = filtered[filtered["industry"] == ind]

    st.divider()

    # ---------------- Key stats ----------------
    if len(filtered) == 0:
        st.info("No salary records match the current filters. Try relaxing them.")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Average Salary", fmt_lpa(filtered["salary_average"].mean()))
    with col2:
        st.metric("Minimum", fmt_lpa(filtered["salary_average"].min()))
    with col3:
        st.metric("Maximum", fmt_lpa(filtered["salary_average"].max()))
    with col4:
        st.metric("Records Analysed", f"{len(filtered):,}")

    st.divider()

    # ---------------- Salary distribution ----------------
    st.markdown("### 📊 Salary Distribution")
    fig = px.histogram(
        filtered, x="salary_lpa", nbins=30,
        labels={"salary_lpa": "Salary (LPA)"}, template="plotly_white",
    )
    fig.update_layout(margin=dict(l=40, r=20, t=40, b=40), height=380, title_font_size=16)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ---------------- Salary by role / location ----------------
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("### 🎯 Salary by Job Role")
        sal_role = analytics.get_salary_by_role(filtered)
        if len(sal_role) > 0:
            sal_role = sal_role[sal_role["count"] >= 3]
            fig = horizontal_bar(sal_role, "avg_salary", "job_role", height=420)
            fig.update_layout(
                xaxis=dict(tickformat=".0s"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data by role")

    with col_r:
        st.markdown("### 📍 Salary by Location")
        sal_loc = analytics.get_salary_by_location(filtered)
        cnt_col = "count"
        if len(sal_loc) > 0:
            fig = bar_chart(sal_loc.sort_values("avg_salary", ascending=False), "location", "avg_salary", height=420)
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Locations shown require at least 3 salary records")
        else:
            st.info("Not enough data by location")

    st.divider()

    # ---------------- Salary by experience & scatter ----------------
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("### 📅 Salary by Experience")
        sal_exp = analytics.get_salary_by_experience(filtered)
        if len(sal_exp) > 0:
            fig = bar_chart(sal_exp, "experience", "avg_salary", height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data by experience")

    with col_r2:
        st.markdown("### 📈 Experience vs Salary")
        scatter_df = filtered.dropna(subset=["experience_min"]).copy()
        if len(scatter_df) >= MIN_SALARY_RECORDS:
            fig = scatter_salary(
                scatter_df, "experience_min", "salary_lpa", "standardized_job_title",
                height=380,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for scatter plot")

    st.divider()
    st.caption("Salary figures shown are based on the loaded dataset only.")