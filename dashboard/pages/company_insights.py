"""
Company Insights page - company hiring profile based on dataset only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import horizontal_bar, bar_chart, donut_chart
from dashboard.components.metrics import fmt_lpa
from src import analytics


def render(df: pd.DataFrame) -> None:
    """Render the Company Insights page."""
    st.markdown('<div class="page-title">🏢 Company Insights</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Explore hiring patterns by company — '
        'based only on the dataset provided.</div>',
        unsafe_allow_html=True,
    )

    if "company" not in df.columns:
        st.warning("No company data available in the dataset.")
        return

    # ---------------- Company selector ----------------
    companies = df["company"].value_counts()
    top_companies = companies.head(15)

    col1, col2 = st.columns([1, 2])
    with col1:
        company = st.selectbox("Select a company", companies.index.tolist())
    with col2:
        st.caption("Choose a company to view its profile based on dataset postings.")

    if not company:
        return

    comp_df = df[df["company"] == company]
    n_postings = len(comp_df)

    st.markdown(
        f"""
        <div class="info-box">
        Showing profile for <strong>{company}</strong> based on
        <strong>{n_postings:,} job postings</strong> in this dataset.
        All information is derived from the dataset only — no external facts inferred.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------- Top hiring companies overview ----------------
    st.markdown("### 🏆 Top Hiring Companies")
    comp_ranking = analytics.get_top_companies(df, n=12)
    if len(comp_ranking) > 0:
        st.plotly_chart(
            horizontal_bar(comp_ranking, "count", "company", height=400),
            use_container_width=True,
        )

    st.divider()

    # ---------------- Company profile ----------------
    st.markdown(f"### 📋 Company Profile: {company}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Postings", f"{n_postings:,}")
    with col2:
        st.metric("Roles", f"{comp_df['standardized_job_title'].nunique() if 'standardized_job_title' in comp_df.columns else 0}")
    with col3:
        st.metric("Locations", f"{comp_df['city'].nunique() if 'city' in comp_df.columns else 0}")
    with col4:
        if "salary_average" in comp_df.columns and comp_df["salary_average"].notna().any():
            st.metric("Avg Salary", fmt_lpa(comp_df["salary_average"].mean()))
        else:
            st.metric("Avg Salary", "N/A")

    st.divider()

    # ---------------- Roles by company ----------------
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("### 🎯 Job Roles by Company")
        role_counts = comp_df["standardized_job_title"].value_counts().head(8).reset_index()
        role_counts.columns = ["job_role", "count"]
        if len(role_counts) > 0:
            st.plotly_chart(
                horizontal_bar(role_counts, "count", "job_role", height=340),
                use_container_width=True,
            )
        else:
            st.info("No role data")

    with col_r:
        st.markdown("### 📍 Locations by Company")
        loc_counts = comp_df["city"].value_counts().head(8).reset_index()
        loc_counts.columns = ["location", "count"]
        if len(loc_counts) > 0:
            st.plotly_chart(
                horizontal_bar(loc_counts, "count", "location", height=340),
                use_container_width=True,
            )
        else:
            st.info("No location data")

    st.divider()

    # ---------------- Skills by company ----------------
    st.markdown("### 🧠 Skills Requested by Company")
    comp_skills = analytics.get_top_skills(comp_df, n=15)
    if len(comp_skills) > 0:
        st.plotly_chart(
            horizontal_bar(comp_skills, "count", "skill", height=400),
            use_container_width=True,
        )
    else:
        st.info("No skill data for this company")

    st.divider()

    # ---------------- Experience by company ----------------
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("### 📅 Experience Requirements")
        exp_counts = comp_df["experience_category"].value_counts().reset_index()
        exp_counts.columns = ["experience", "count"]
        if len(exp_counts) > 0:
            st.plotly_chart(
                donut_chart(exp_counts["experience"].tolist(), exp_counts["count"].tolist(), height=320),
                use_container_width=True,
            )
        else:
            st.info("No experience data")

    with col_r2:
        st.markdown("### 🏭 Industries")
        ind_counts = comp_df["industry"].value_counts().head(6).reset_index()
        ind_counts.columns = ["industry", "count"]
        if len(ind_counts) > 0:
            st.plotly_chart(
                bar_chart(ind_counts, "industry", "count", height=320),
                use_container_width=True,
            )
        else:
            st.info("No industry data")

    st.divider()
    st.caption("All company information shown is derived only from the loaded dataset.")