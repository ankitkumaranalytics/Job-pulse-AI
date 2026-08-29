"""
Home page for JobPulse AI.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from dashboard.components.metrics import render_kpi_card, fmt_lpa, fmt_number
from dashboard.components.charts import horizontal_bar, line_chart, donut_chart
from dashboard.components.styling import synthetic_data_notice
from src import analytics


def render(df: pd.DataFrame) -> None:
    """Render the home page."""
    st.markdown('<div class="page-title">JobPulse AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">'
        '"Understand the Job Market. Discover Your Skill Gap. Build Your Career."'
        '</div>',
        unsafe_allow_html=True,
    )

    synthetic_data_notice()

    # ---------------- KPI Cards ----------------
    summary = analytics.get_job_market_summary(df)
    top_skills = analytics.get_top_skills(df, n=1)

    st.markdown("### 📊 Market Overview")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        render_kpi_card("Total Job Postings", fmt_number(summary["total_jobs"]))
    with col2:
        render_kpi_card("Total Companies", fmt_number(summary["total_companies"]))
    with col3:
        render_kpi_card("Total Locations", fmt_number(summary["total_locations"]))
    with col4:
        render_kpi_card("Average Salary", fmt_lpa(summary["avg_salary"]))
    with col5:
        top_skill_name = top_skills.iloc[0]["skill"] if len(top_skills) else "N/A"
        render_kpi_card("Most In-Demand Skill", top_skill_name)

    st.divider()

    # ---------------- Job market overview ----------------
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown("### 🎯 Top Job Roles")
        top_roles = analytics.get_top_roles(df, n=10)
        if len(top_roles) > 0:
            fig = horizontal_bar(top_roles, "count", "job_role", height=420)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No role data available")

    with col_r:
        st.markdown("### 📍 Top Locations")
        top_locations = analytics.get_top_locations(df, n=8)
        if len(top_locations) > 0:
            fig = donut_chart(
                top_locations["location"].tolist(),
                top_locations["count"].tolist(),
                height=420,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No location data available")

    st.divider()

    # ---------------- Recent job trends ----------------
    st.markdown("### 📈 Recent Job Posting Trends")
    trend = analytics.get_job_trend_analysis(df)
    if len(trend) > 0:
        fig = line_chart(trend, "year_month", "count", height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available")

    # ---------------- Footer ----------------
    st.divider()
    st.caption(
        "JobPulse AI — a data analytics portfolio project. "
        "Data shown is synthetic unless a real dataset has been loaded."
    )