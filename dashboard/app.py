"""
JobPulse AI - Streamlit Application Entry Point.

Run with: streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Must be the first Streamlit command
st.set_page_config(
    page_title="JobPulse AI - Job Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.components.styling import apply_custom_styles
from dashboard.components.sidebar import render_sidebar, load_processed_data


def main() -> None:
    """Main application entry point."""
    apply_custom_styles()
    render_sidebar()

    # Load data (cached)
    try:
        df = load_processed_data()
        st.session_state["df"] = df
    except Exception as e:
        st.error(f"Could not load data: {e}")
        st.info("Run the pipeline first: `python scripts/run_pipeline.py --skip-db`")
        st.stop()

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