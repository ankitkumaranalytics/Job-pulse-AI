"""
JobPulse AI - Streamlit Application Entry Point.

Run with: streamlit run dashboard/app.py

Works with zero configuration: when PostgreSQL is unavailable the app
falls back to processed CSV data automatically.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("jobpulse.dashboard")

# Must be the first Streamlit command
st.set_page_config(
    page_title="JobPulse AI - Job Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.components.styling import apply_custom_styles
from dashboard.components.sidebar import render_sidebar, load_dashboard_data, parse_skills_for_session


def render_health_check(df, source: str, db_failed: bool) -> None:
    """
    Developer-friendly diagnostic panel (Phase 17).

    Displays component status in a collapsible sidebar section without
    ever exposing credentials, connection strings, or absolute paths.
    """
    def _ok(condition: bool) -> str:
        return "✅" if condition else "❌"

    with st.sidebar.expander("🩺 System Health"):
        st.markdown(
            f"{_ok(df is not None and len(df) > 0)} **Dataset loaded** — "
            f"{len(df):,} rows · source: `{source}`"
        )

        required = [
            "job_title", "company", "standardized_job_title",
            "extracted_skills", "posting_date",
        ]
        missing = [c for c in required if c not in df.columns]
        st.markdown(
            f"{_ok(not missing)} **Required columns**"
            + (f" — missing: {', '.join(missing)}" if missing else "")
        )

        skill_ok = any(
            isinstance(x, (list, set)) and len(x) > 0
            for x in df["extracted_skills"].head(200)
        ) if "extracted_skills" in df.columns else False
        st.markdown(f"{_ok(skill_ok)} **Skill extraction data**")

        try:
            from models.job_recommender import JobRecommender  # noqa: F401
            st.markdown("✅ **Recommendation engine available**")
        except Exception:
            st.markdown("❌ **Recommendation engine unavailable**")

        st.markdown(
            ("ℹ️ **Database (optional)** — unreachable, CSV fallback active"
             if db_failed else
             "✅ **Database (optional)** — not required in CSV mode")
        )
        st.markdown("✅ **Streamlit configuration working**")


def main() -> None:
    """Main application entry point."""
    apply_custom_styles()
    render_sidebar()

    # Load data (cached across reruns; DB -> processed -> cleaned -> raw fallback)
    try:
        df, source, db_failed = load_dashboard_data()
        df = parse_skills_for_session(df)
        st.session_state["df"] = df
        st.session_state["data_source"] = source
        st.session_state["data_tier"] = source  # backwards compatibility
        st.session_state["db_attempted_failed"] = db_failed
    except Exception as e:
        logger.error("Dataset loading failed: %s", e)
        st.error("⚠️ **No job market dataset is available.**")
        st.info(
            "The dashboard needs a dataset to display insights. "
            "Generate and process one with:\n"
            "```\n"
            "python scripts/generate_sample_data.py\n"
            "python scripts/run_pipeline.py --skip-db\n"
            "```"
        )
        st.caption("Details are written to the application logs.")
        st.stop()

    # Non-blocking notice: DB was configured but unreachable (CSV fallback used)
    if db_failed:
        st.info(
            "ℹ️ PostgreSQL credentials were configured but the database could "
            "not be reached — showing **processed CSV data** instead. "
            "All features remain available."
        )

    render_health_check(df, source, db_failed)

    # Simple built-in navigation using radio for reliability
    pages = {
        "🏠 Home": "home",
        "📈 Market Insights": "market_insights",
        "🧠 Skills Intelligence": "skills_intelligence",
        "💰 Salary Explorer": "salary_explorer",
        "🏢 Company Insights": "company_insights",
        "🎯 Career Advisor": "career_advisor",
        "📋 Job Recommendations": "job_recommendations",
    }

    with st.sidebar:
        st.divider()
        selection = st.radio("Navigate", list(pages.keys()), label_visibility="collapsed")

    page = pages[selection]

    # Import and render the selected page module
    if page == "home":
        from dashboard.pages.home import render as render_home
        render_home(df)
    elif page == "market_insights":
        from dashboard.pages.market_insights import render as render_market
        render_market(df)
    elif page == "skills_intelligence":
        from dashboard.pages.skills_intelligence import render as render_skills
        render_skills(df)
    elif page == "salary_explorer":
        from dashboard.pages.salary_explorer import render as render_salary
        render_salary(df)
    elif page == "company_insights":
        from dashboard.pages.company_insights import render as render_company
        render_company(df)
    elif page == "career_advisor":
        from dashboard.pages.career_advisor import render as render_career
        render_career(df)
    elif page == "job_recommendations":
        from dashboard.pages.job_recommendations import render as render_recos
        render_recos(df)


if __name__ == "__main__":
    main()