"""
Home page — the entry point of the JobPulse AI story (Phase 4).

Guided flow: understand the market -> understand the required skills ->
discover your own career position (call-to-action into the AI Career
Advisor, the hero feature of the platform).
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import donut_chart, horizontal_bar, line_chart
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


def render(df: pd.DataFrame) -> None:
    """Render the home page with the guided product story."""
    st.markdown(
        """
        <div class="hero">
            <div class="hero-eyebrow">Job Market &amp; Skills Intelligence Platform</div>
            <div class="hero-title">JobPulse AI</div>
            <div class="hero-tagline">"Understand the Job Market. Discover Your Skill Gap. Build Your Career."</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df is None or len(df) == 0:
        empty_state(
            "No Data Available",
            "No job market data is loaded. Run the data pipeline to generate insights.",
        )
        return

    if st.session_state.get("data_source") != "database":
        st.caption(
            "🧪 Showing a clearly-labelled **synthetic sample dataset** so every "
            "feature is explorable. All figures on this page are computed from "
            "the loaded data — nothing is hard-coded."
        )

    # ---------------- Premium KPI cards ----------------
    summary = analytics.get_job_market_summary(df)
    top_skills = analytics.get_top_skills(df, n=1)
    top_skill_name = str(top_skills.iloc[0]["skill"]) if len(top_skills) else "N/A"
    top_skill_share = (
        f"{top_skills.iloc[0]['count'] / len(df) * 100:.0f}% of postings"
        if len(top_skills)
        else ""
    )
    avg_salary = summary["avg_salary"]

    kpi_row(
        [
            {"title": "Total Job Postings", "value": fmt_number(summary["total_jobs"]),
             "sub": "in the loaded dataset", "accent": True},
            {"title": "Total Companies", "value": fmt_number(summary["total_companies"]),
             "sub": "actively hiring"},
            {"title": "Total Locations", "value": fmt_number(summary["total_locations"]),
             "sub": "cities covered"},
            {"title": "Average Salary", "value": fmt_lpa(avg_salary) if avg_salary > 0 else "N/A",
             "sub": "across listed salaries"},
            {"title": "Most In-Demand Skill", "value": top_skill_name, "sub": top_skill_share},
        ]
    )

    # ---------------- Step 1 — Understand the market ----------------
    st.divider()
    section_header("Understand the Market", kicker="Step 1 · Where are the opportunities?")

    trend = analytics.get_job_trend_analysis(df)
    if len(trend) > 0:
        st.plotly_chart(
            line_chart(trend, "year_month", "count", height=300), use_container_width=True
        )

    top_locations = analytics.get_top_locations(df, n=8)
    top_companies = analytics.get_top_companies(df, n=10)
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Top Hiring Cities**")
        if len(top_locations) > 0:
            st.plotly_chart(
                donut_chart(top_locations["location"].tolist(),
                            top_locations["count"].tolist(), height=320),
                use_container_width=True,
            )
        else:
            empty_state(message="No location data available.")
    with col_r:
        st.markdown("**Top Hiring Companies**")
        if len(top_companies) > 0:
            st.plotly_chart(
                horizontal_bar(top_companies, "count", "company", height=320),
                use_container_width=True,
            )
        else:
            empty_state(message="No company data available.")

    if len(top_locations) > 0:
        loc = top_locations.iloc[0]
        insight_card(
            f"**{loc['location']}** currently has the highest concentration of job "
            f"postings — {int(loc['count']):,} openings "
            f"({loc['count'] / len(df) * 100:.0f}% of the dataset)."
        )

    # ---------------- Step 2 — Understand the skills ----------------
    st.divider()
    section_header("Understand the Required Skills",
                   kicker="Step 2 · What skills does the market want?")

    top12 = analytics.get_top_skills(df, n=12)
    categories = analytics.get_skill_category_counts(df)
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown("**Top 12 In-Demand Skills**")
        if len(top12) > 0:
            st.plotly_chart(
                horizontal_bar(top12, "count", "skill", height=360),
                use_container_width=True,
            )
        else:
            empty_state(message="No skill data available.")
    with col_r:
        st.markdown("**Demand by Skill Category**")
        if len(categories) > 0:
            st.plotly_chart(
                donut_chart(categories["category"].tolist(),
                            categories["count"].tolist(), height=360),
                use_container_width=True,
            )
        else:
            empty_state(message="No skill category data available.")

    if len(top12) > 0:
        s = top12.iloc[0]
        insight_card(
            f"**{s['skill']}** is the single most demanded skill — requested in "
            f"{int(s['count']):,} postings ({s['count'] / len(df) * 100:.0f}% of the market)."
        )

    # ---------------- Step 3 — Your career position (hero CTA) ----------------
    st.divider()
    cta_block(
        "How Ready Are You for Your Target Role?",
        "Compare your skills against real market demand, get your Career Readiness "
        "Score, and receive a personalised learning roadmap built from the data.",
        "Analyze My Career Profile",
        "⭐ AI Career Advisor",
        key="home_cta_advisor",
    )

    # ---------------- Step 4 — Resume & search CTAs (2026 upgrade) ----------------
    cta_block(
        "See How Your Resume Scores Against the Market",
        "Upload your resume for a transparent ATS-style audit, missing-keyword "
        "analysis, and a match score against any job description.",
        "Open Resume Intelligence",
        "Resume Intelligence",
        key="home_cta_resume",
    )

    cta_block(
        "Search Jobs in Plain English",
        "Type what you want — 'fresher data analyst internship in Chennai with "
        "Python and SQL' — and the semantic search engine finds matching postings.",
        "Open Job Search",
        "Job Search",
        key="home_cta_search",
    )

    with st.expander("🧭 The JobPulse journey — how this platform tells the story"):
        st.markdown(
            "1. **Market Insights** — where the opportunities are\n"
            "2. **Skills Intelligence** — which skills the market demands\n"
            "3. **Salary Explorer** — what the pay potential looks like\n"
            "4. **Company Intelligence** — who is hiring and what they require\n"
            "5. **⭐ AI Career Advisor** — how ready *you* are, and what to learn next\n"
            "6. **Job Recommendations** — which roles fit your profile today"
        )
    st.caption(
        "JobPulse AI — data analytics portfolio project. "
        "Every value is computed from the loaded dataset."
    )