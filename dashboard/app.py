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
from dashboard.components.premium import NAV_LABELS, PAGE_KEYS


def render_health_check(df, source: str, db_failed: bool) -> None:
    """
    Deprecated: kept for backwards compatibility only.

    The health panel now renders once, inside ``render_sidebar()``
    (components/sidebar.py). Rendering it here as well duplicated the
    section on every page.
    """
    return None


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

    # Health panel renders ONCE, inside render_sidebar() (sidebar.py).
    # -----------------------------------------------------------------
    # Navigation: canonical journey order defined in components.premium
    # (Phase 3/14). The Career Advisor is the hero feature and is
    # visually starred. CTA buttons on other pages navigate via
    # premium.go_to(), which queues st.session_state["requested_navigation"].
    #
    # The queued request MUST be consumed HERE, before the radio widget
    # (key="nav_selection") is instantiated: Streamlit forbids writing a
    # widget-backed session key after that widget has been created in the
    # current run (StreamlitAPIException). Popping the key also guarantees
    # the request is applied exactly once, so no rerun loop can occur.
    if "requested_navigation" in st.session_state:
        requested_nav = st.session_state.pop("requested_navigation")
        if requested_nav in NAV_LABELS:
            st.session_state["nav_selection"] = requested_nav

    # Initialize navigation safely (default = first page, "Overview",
    # which maps to the Home page via PAGE_KEYS).
    if "nav_selection" not in st.session_state:
        st.session_state["nav_selection"] = NAV_LABELS[0]

    with st.sidebar:
        st.divider()
        selection = st.radio(
            "Navigate",
            NAV_LABELS,
            key="nav_selection",
            label_visibility="collapsed",
        )

    page = PAGE_KEYS[selection]

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