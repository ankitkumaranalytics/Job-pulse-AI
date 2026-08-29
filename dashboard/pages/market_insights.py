"""
Market Insights page - interactive market overview with filters.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import horizontal_bar, line_chart, donut_chart
from src import analytics


def _apply_filters(df, role, location, industry, exp_cat, date_range):
    """Apply dashboard filters to the DataFrame."""
    filtered = df.copy()

    if role and role != "All":
        filtered = filtered[filtered["standardized_job_title"] == role]

    if location and location != "All":
        if "city" in filtered.columns:
            filtered = filtered[filtered["city"] == location]

    if industry and industry != "All":
        if "industry" in filtered.columns:
            filtered = filtered[filtered["industry"] == industry]

    if exp_cat and exp_cat != "All":
        if "experience_category" in filtered.columns:
            filtered = filtered[filtered["experience_category"] == exp_cat]

    if date_range and "posting_date" in filtered.columns:
        start, end = date_range
        filtered["posting_date"] = pd.to_datetime(filtered["posting_date"], errors="coerce")
        filtered = filtered[filtered["posting_date"].between(start, end)]

    return filtered


def render(df: pd.DataFrame) -> None:
    """Render the Market Insights page."""
    st.markdown('<div class="page-title">📈 Market Insights</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Explore job demand, top companies, industries '
        'and posting trends with dynamic filters.</div>',
        unsafe_allow_html=True,
    )

    # ---------------- Filters ----------------
    st.markdown("### Filters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        roles = ["All"] + sorted(df["standardized_job_title"].unique().tolist())
        role = st.selectbox("Job Role", roles)

    with col2:
        locs = ["All"] + sorted(df["city"].unique().tolist()) if "city" in df.columns else ["All"]
        location = st.selectbox("Location", locs)

    with col3:
        industries = ["All"] + sorted(df["industry"].unique().tolist()) if "industry" in df.columns else ["All"]
        industry = st.selectbox("Industry", industries)

    with col4:
        exps = ["All"] + sorted(df["experience_category"].unique().tolist()) if "experience_category" in df.columns else ["All"]
        exp_cat = st.selectbox("Experience", exps)

    date_col = None
    for c in df.columns:
        if str(c).lower() in ("posting_date", "date", "posted_date"):
            date_col = c
            break

    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if len(dates) > 0:
            min_d = dates.min().date()
            max_d = dates.max().date()
            date_range = st.date_input(
                "Date Range", value=(min_d, max_d), min_value=min_d, max_value=max_d,
            )
        else:
            date_range = None
    else:
        date_range = None

    filtered = _apply_filters(df, role, location, industry, exp_cat, date_range)

    st.divider()

    # ---------------- Summary metrics ----------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Filtered Jobs", f"{len(filtered):,}")
    with col2:
        st.metric("Companies", f"{filtered['company'].nunique() if 'company' in filtered.columns else 0:,}")
    with col3:
        st.metric("Locations", f"{filtered['city'].nunique() if 'city' in filtered.columns else 0:,}")
    with col4:
        if "salary_average" in filtered.columns and filtered["salary_average"].notna().any():
            avg = filtered["salary_average"].mean() / 100000
            st.metric("Avg Salary", f"₹{avg:.1f} LPA")
        else:
            st.metric("Avg Salary", "N/A")

    st.divider()

    # ---------------- Charts ----------------
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("### 🎯 Jobs by Role")
        top_roles = analytics.get_top_roles(filtered, n=10)
        if len(top_roles) > 0:
            st.plotly_chart(horizontal_bar(top_roles, "count", "job_role", height=380), use_container_width=True)
        else:
            st.info("No data for current filters")

    with col_r:
        st.markdown("### 📍 Jobs by Location")
        top_locs = analytics.get_top_locations(filtered, n=10)
        if len(top_locs) > 0:
            st.plotly_chart(horizontal_bar(top_locs, "count", "location", height=380), use_container_width=True)
        else:
            st.info("No data for current filters")

    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("### 🏢 Top Companies")
        comps = analytics.get_top_companies(filtered, n=10)
        if len(comps) > 0:
            st.plotly_chart(horizontal_bar(comps, "count", "company", height=380), use_container_width=True)
        else:
            st.info("No data for current filters")

    with col_r2:
        st.markdown("### 🏭 Industry Distribution")
        inds = analytics.get_industry_analysis(filtered)
        if len(inds) > 0:
            top_inds = inds.head(7)
            other = int(inds.iloc[7:]["count"].sum()) if len(inds) > 7 else 0
            if other > 0:
                top_inds = pd.concat([
                    top_inds,
                    pd.DataFrame([{"industry": "Other", "count": other}]),
                ])
            st.plotly_chart(
                donut_chart(top_inds["industry"].tolist(), top_inds["count"].tolist(), height=380),
                use_container_width=True,
            )
        else:
            st.info("No data for current filters")

    st.divider()

    # ---------------- Job trend ----------------
    st.markdown("### 📈 Job Posting Trend Over Time")
    trend = analytics.get_job_trend_analysis(filtered)
    if len(trend) > 0:
        st.plotly_chart(line_chart(trend, "year_month", "count", height=380), use_container_width=True)
    else:
        st.info("No trend data for current filters")