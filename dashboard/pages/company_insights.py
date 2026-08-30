"""
Company Intelligence page — who is hiring and what do they require?

All figures come exclusively from the loaded dataset; no company facts
are invented. Missing columns degrade to clean empty states.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import bar_chart, donut_chart, horizontal_bar
from dashboard.components.metrics import fmt_lpa, fmt_number
from dashboard.components.premium import (
    cta_block,
    empty_state,
    insight_card,
    kpi_row,
    page_header,
    section_header,
    skill_badges,
)
from src import analytics


def _series_to_df(series: pd.Series, name: str) -> pd.DataFrame:
    """Convert a value_counts Series into a chart-friendly DataFrame."""
    if series is None or len(series) == 0:
        return pd.DataFrame()
    out = series.rename_axis("name").reset_index(name="count")
    out.columns = [name, "count"]
    return out


def render(df: pd.DataFrame) -> None:
    """Render the Company Intelligence page."""
    page_header(
        "Company Intelligence",
        "Who is hiring, where, and which skills do they ask for — "
        "based only on postings available in the dataset.",
        eyebrow="05 · Company Intelligence",
    )

    if "company" not in df.columns or df["company"].dropna().empty:
        empty_state(
            "No Company Data",
            "The loaded dataset does not contain any company information. "
            "Load a dataset with a 'company' column to explore hiring activity.",
        )
        return

    companies = df["company"].value_counts()
    total_companies = int(len(companies))
    top_company = companies.index[0]
    top_company_jobs = int(companies.iloc[0])

    # ---------------- KPIs ----------------
    kpi_row(
        [
            {"title": "Companies Hiring", "value": fmt_number(total_companies)},
            {
                "title": "Top Hiring Company",
                "value": str(top_company),
                "sub": f"{top_company_jobs:,} postings",
                "accent": True,
            },
            {
                "title": "Avg Postings / Company",
                "value": fmt_number(len(df) / max(total_companies, 1)),
            },
            {"title": "Job Postings", "value": fmt_number(len(df))},
        ]
    )

    # ---------------- Top hiring companies ----------------
    section_header("Top Hiring Companies", "Ranked by number of job postings")
    top_companies = analytics.get_top_companies(df, n=15)
    if len(top_companies) > 0:
        st.plotly_chart(
            horizontal_bar(top_companies, "count", "company", height=460),
            use_container_width=True,
        )
        top_share = top_company_jobs / max(len(df), 1) * 100
        insight_card(
            f"**{top_company}** currently has the highest number of postings in this "
            f"dataset with **{top_company_jobs:,} jobs** "
            f"({top_share:.1f}% of all postings)."
        )
    else:
        empty_state(message="No hiring-company data could be aggregated.")

    st.divider()

    # ---------------- Company detail selector ----------------
    section_header("Company Profile", "Select a company to explore its hiring footprint")

    company_list = companies.index.tolist()
    if not company_list:
        empty_state(message="No companies available to display.")
        return

    selected_company = st.selectbox(
        "Choose a company",
        company_list,
        index=0,
        key="ci_company",
    )

    if not selected_company:
        return

    profile = analytics.get_company_profile(df, selected_company)
    if not profile:
        empty_state("No Data", f"No data found for '{selected_company}'.")
        return

    # Company KPIs
    kpi_row(
        [
            {"title": "Job Postings", "value": fmt_number(profile["total_postings"]), "accent": True},
            {
                "title": "Avg Salary",
                "value": fmt_lpa(profile["avg_salary"]) if profile.get("avg_salary") else "N/A",
                "sub": f"{profile.get('salary_count', 0)} records",
            },
            {
                "title": "Locations",
                "value": fmt_number(len(profile.get("locations", []))),
            },
            {"title": "Top Skills", "value": fmt_number(len(profile.get("top_skills", [])))},
        ]
    )

    st.divider()

    # Two-column layout: roles + locations
    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        section_header("Top Roles", "Job roles this company is hiring for")
        roles = profile.get("top_roles", pd.Series(dtype=int))
        if len(roles) > 0:
            roles_df = _series_to_df(roles, "job_role")
            st.plotly_chart(
                bar_chart(roles_df, "job_role", "count", height=360),
                use_container_width=True,
            )
        else:
            empty_state(message="No role data available.")

    with col_b:
        section_header("Hiring Locations", "Where this company is hiring")
        locs = profile.get("locations", pd.Series(dtype=int))
        if len(locs) > 0:
            locs_df = _series_to_df(locs, "location")
            st.plotly_chart(
                donut_chart(labels=locs_df["location"].tolist(), values=locs_df["count"].tolist(), height=360),
                use_container_width=True,
            )
        else:
            empty_state(message="No location data available.")

    st.divider()

    # Skills + experience
    col_c, col_d = st.columns(2, gap="large")

    with col_c:
        section_header("Top Skills Requested", "Most demanded skills at this company")
        skills = profile.get("top_skills", pd.Series(dtype=int))
        if len(skills) > 0:
            skill_list = [str(s) for s in skills.index.tolist()]
            skill_badges(skill_list, kind="have")
        else:
            empty_state(message="No skill data available.")

    with col_d:
        section_header("Experience Requirements", "Experience levels sought")
        exp = profile.get("experience", pd.Series(dtype=int))
        if len(exp) > 0:
            exp_df = _series_to_df(exp, "experience_category")
            st.plotly_chart(
                bar_chart(exp_df, "experience_category", "count", height=360),
                use_container_width=True,
            )
        else:
            empty_state(message="No experience data available.")

    # Dynamic insight
    if len(roles) > 0 and len(skills) > 0:
        top_role = str(roles.index[0])
        top_skill = str(skills.index[0])
        insight_card(
            f"**{selected_company}** hires most frequently for **{top_role}**, "
            f"and **{top_skill}** is its most requested skill."
        )