"""
Market Insights page — "Where are the opportunities?" (Phase 5).

Demand over time, location intelligence, industry intelligence and a
company preview — all filter-driven, with dynamic insight cards.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import bar_chart, horizontal_bar, line_chart
from dashboard.components.filters import filter_dataframe, select_filter, show_no_data
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

MIN_FOR_INSIGHT = 5


def render(df: pd.DataFrame) -> None:
    """Render the Market Insights page."""
    page_header(
        "Market Insights",
        "Where are the opportunities? Demand by time, location, industry and employer.",
        eyebrow="Step 1 · Understand the Market",
    )

    if df is None or len(df) == 0:
        empty_state("No Data Available", "No job market data is loaded. Run the data pipeline first.")
        return

    # ---------------- Filters (Phase 8) ----------------
    st.markdown("##### Filters")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        role = select_filter(df, "standardized_job_title", "Job Role", key="mi_role")
    with fcol2:
        location = select_filter(df, "city", "Location", key="mi_loc")
    with fcol3:
        industry = select_filter(df, "industry", "Industry", key="mi_ind")
    with fcol4:
        experience = select_filter(df, "experience_category", "Experience", key="mi_exp")

    date_range = None
    if "posting_date" in df.columns:
        dates = pd.to_datetime(df["posting_date"], errors="coerce").dropna()
        if len(dates) > 1 and dates.min() < dates.max():
            picked = st.date_input(
                "Posting Date Range",
                value=(dates.min().date(), dates.max().date()),
                min_value=dates.min().date(),
                max_value=dates.max().date(),
                key="mi_dates",
            )
            if isinstance(picked, tuple) and len(picked) == 2:
                date_range = picked

    filtered = filter_dataframe(
        df, role=role, location=location, industry=industry,
        experience=experience, date_range=date_range,
    )
    if len(filtered) == 0:
        show_no_data()
        return

    # ---------------- KPIs ----------------
    cities = filtered["city"].value_counts() if "city" in filtered.columns else pd.Series(dtype=int)
    industries = filtered["industry"].value_counts() if "industry" in filtered.columns else pd.Series(dtype=int)
    companies = filtered["company"].value_counts() if "company" in filtered.columns else pd.Series(dtype=int)
    sal = filtered["salary_average"].dropna() if "salary_average" in filtered.columns else pd.Series(dtype=float)

    kpi_row([
        {"title": "Job Postings", "value": fmt_number(len(filtered)),
         "sub": "match your filters", "accent": True},
        {"title": "Companies Hiring", "value": fmt_number(filtered["company"].nunique() if "company" in filtered.columns else 0),
         "sub": "in this segment"},
        {"title": "Average Salary", "value": fmt_lpa(sal.mean()) if len(sal) else "N/A",
         "sub": f"{fmt_number(len(sal))} listed salaries"},
        {"title": "Hottest City", "value": str(cities.index[0]) if len(cities) else "N/A",
         "sub": f"{fmt_number(cities.iloc[0])} postings" if len(cities) else ""},
    ])

    # ---------------- Demand trend ----------------
    st.divider()
    section_header("Job Demand Trend", kicker="How demand moves over time")
    trend = analytics.get_job_trend_analysis(filtered)
    if len(trend) > 0:
        st.plotly_chart(line_chart(trend, "year_month", "count", height=320), use_container_width=True)
        if len(trend) > 1:
            peak = trend.loc[trend["count"].idxmax()]
            insight_card(
                f"Posting activity peaked in **{peak['year_month']}** with "
                f"{int(peak['count']):,} jobs in this segment."
            )
    else:
        empty_state(message="No posting dates available for the trend chart.")

    # ---------------- Location + industry intelligence ----------------
    st.divider()
    section_header("Location & Industry Intelligence", kicker="Where the jobs are")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Top Hiring Cities**")
        if len(cities):
            loc_df = cities.head(10).reset_index()
            loc_df.columns = ["location", "count"]
            st.plotly_chart(horizontal_bar(loc_df, "count", "location", height=400), use_container_width=True)
        else:
            empty_state(message="No location data for this selection.")
    with col_r:
        st.markdown("**Demand by Industry**")
        if len(industries):
            ind_df = industries.head(8).reset_index()
            ind_df.columns = ["industry", "count"]
            st.plotly_chart(bar_chart(ind_df, "industry", "count", height=400), use_container_width=True)
        else:
            empty_state(message="No industry data for this selection.")

    # ---------------- Company preview ----------------
    st.divider()
    section_header("Top Hiring Companies", kicker="Who employs this segment")
    if len(companies):
        comp_df = companies.head(10).reset_index()
        comp_df.columns = ["company", "count"]
        st.plotly_chart(horizontal_bar(comp_df, "count", "company", height=400), use_container_width=True)
    else:
        empty_state(message="No company data for this selection.")

    # ---------------- Dynamic insights (Phase 16) ----------------
    if len(filtered) >= MIN_FOR_INSIGHT:
        bits = []
        if len(cities):
            bits.append(f"**{cities.index[0]}** leads demand with {int(cities.iloc[0]):,} postings")
        if len(industries):
            bits.append(f"**{industries.index[0]}** is the most active industry")
        if len(companies):
            bits.append(f"**{companies.index[0]}** is the top hiring company")
        if bits:
            insight_card("; ".join(bits) + ".", label="What This Means")

    # ---------------- Actionable insights (FEATURE 7 upgrade) ----------------
    if len(filtered) >= MIN_FOR_INSIGHT:
        st.divider()
        section_header(
            "Actionable Insights",
            kicker="What these numbers mean for your job hunt",
        )
        try:
            from dashboard.services.market_service import actionable_insights

            focus_role = None if role == "All" else role
            for insight in actionable_insights(filtered, focus_role):
                insight_card(insight)
        except Exception:  # noqa: BLE001 - insights are best-effort
            pass

    cta_block(
        "Now — which skills do these opportunities require?",
        "See the exact skills the market demands, ranked by real posting data.",
        "Explore Skills Intelligence",
        "Skills Intelligence",
        key="mi_cta_skills",
    )