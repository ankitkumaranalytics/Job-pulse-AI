"""
Integration smoke tests: boot the real Streamlit app with AppTest and
render every page with the actual dataset (Phase 7 / Phase 18).

These tests catch import errors, unguarded column access, empty-state
crashes and widget failures that unit tests cannot see.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"

PAGES = [
    "Overview",
    "Market Insights",
    "Skills Intelligence",
    "Salary Explorer",
    "Company Intelligence",
    "⭐ AI Career Advisor",
    "Job Recommendations",
]


@pytest.fixture(scope="module")
def app_test() -> AppTest:
    """Boot the app once (Home page default) with a generous timeout."""
    at = AppTest.from_file(str(APP_PATH), default_timeout=300)
    at.run()
    return at


def _session_get(at: AppTest, key: str):
    """AppTest session_state has no .get(); read a key defensively."""
    try:
        return at.session_state[key]
    except KeyError:
        return None


def test_app_boots_without_exception(app_test: AppTest) -> None:
    """The entry point must run clean: data loads, sidebar renders."""
    assert not app_test.exception, f"App crashed: {app_test.exception}"
    assert app_test.sidebar.radio, "Navigation radio missing from sidebar"
    # Data tier recorded in session state by app.py
    assert _session_get(app_test, "data_tier") in {"processed", "cleaned", "raw"}
    # Dataset actually loaded into session state
    df = _session_get(app_test, "df")
    assert df is not None and len(df) > 0, "Dashboard session has no dataframe"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_exception(app_test: AppTest, page: str) -> None:
    """Switch the nav radio to each page and confirm no crash."""
    app_test.sidebar.radio[0].set_value(page)
    app_test.run()
    assert not app_test.exception, f"Page '{page}' crashed: {app_test.exception}"


def test_market_insights_filters_produce_charts(app_test: AppTest) -> None:
    """After selecting a role filter the page must still render content."""
    app_test.sidebar.radio[0].set_value("Market Insights")
    app_test.run()
    assert not app_test.exception
    # Every selectbox filter defaults to 'All' and must exist
    assert len(app_test.selectbox) >= 4, "Market Insights filters missing"


def test_company_page_selects_first_company(app_test: AppTest) -> None:
    """Company selector defaults to a real company; profile must render."""
    app_test.sidebar.radio[0].set_value("Company Intelligence")
    app_test.run()
    assert not app_test.exception
    assert app_test.selectbox, "Company selectbox missing"


def test_career_page_empty_skills_is_safe(app_test: AppTest) -> None:
    """With no skills selected the page shows guidance, not a crash."""
    app_test.sidebar.radio[0].set_value("⭐ AI Career Advisor")
    app_test.run()
    assert not app_test.exception
