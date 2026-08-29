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
from dashboard.components.filters import (
    ALL,
    filter_dataframe,
    select_filter,
    show_no_data,
)
from src import analytics


def render(df: pd.DataFrame) -> None:
    """Render the Market Insights page."""
    st.markdown('<div class="page-title">📈 Market Insights</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Explore job demand, top companies, industries '
        'and posting trends with dynamic filters.</div>',
        unsafe_allow_html=True,
    )

    if df is None or len(df) == 0:
        show_no_data("the loaded dataset")
        return

    # ---------------- Filters ----------------
    st.markdown("### Filters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        role = select_filter(df, "standardized_job_title", "Job Role", key="mi_role")

    with col2:
        location = select_filter(df, "city", "Location", key="mi_location")

    with col3:
        industry = select_filter(df, "industry", "Industry", key="mi_industry")

    with col4:
        experience = select_filter(df, "experience_category", "Experience", key="mi_exp")

    date_range = None
    if "posting_date" in df.columns:
        dates = pd.to_datetime(df["posting_date"], errors="coerce").dropna()
        if len(dates) > 0:
            min_d = dates.min().date()
            max_d = dates.max().date()
            # date_input returns a tuple only when a 2-value range is given;
            # a single date (e.g. min == max) is returned unboxed - handle both.
            picked = st.date_input(
                "Date Range",
                value=(min_d, max_d) if min_d < max_d else min_d,
                min_value=min_d,
                max_value=max_d,
            )
            if isinstance(picked, (tuple, list)) and len(picked) == 2:
                date_range = (picked[0], picked[1])
            else:
                date_range = (min_d, max_d) if not hasattr(picked, "year") else (picked, picked)

    filtered = filter_dataframe(
        df,
        role=role,
        location=location,
        industry=industry,
        experience=experience,
        date_range=date_range,
    )

    st.divider()

    # ---------------- Empty-state guard (Phase 8) ----------------
    if len(filtered) == 0:
        show_no_data()
        return

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