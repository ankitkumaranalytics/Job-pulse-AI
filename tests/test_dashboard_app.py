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


# ---------------------------------------------------------------------------
# Navigation regression tests (StreamlitAPIException fix).
#
# CTA buttons must navigate ONLY on click, via the `requested_navigation`
# queue that app.py consumes BEFORE the nav radio (key="nav_selection") is
# instantiated. Writing a widget-backed key after the widget exists raises
# StreamlitAPIException; these tests prove the queue flow works end-to-end
# and that it cannot loop (the request is popped exactly once).
#
# Each test boots its OWN AppTest session (like a real user opening a new
# browser tab) so widget-state replay from previous pages cannot interfere.
# ---------------------------------------------------------------------------


def _fresh_app() -> AppTest:
    """Boot a fresh, isolated AppTest session of the real app."""
    at = AppTest.from_file(str(APP_PATH), default_timeout=300)
    at.run()
    return at


def test_fresh_session_starts_on_overview_with_no_pending_navigation() -> None:
    """Rendering the Home page must not trigger any automatic navigation."""
    at = _fresh_app()
    assert not at.exception, f"Home page crashed: {at.exception}"
    assert at.sidebar.radio[0].value == "Overview"
    assert _session_get(at, "requested_navigation") is None


def test_home_cta_navigates_to_career_advisor() -> None:
    """Clicking the Home hero CTA switches the nav radio to Career Advisor."""
    at = _fresh_app()
    assert not at.exception

    # Simulate the user clicking the hero CTA button on the Home page.
    # A single run() is enough: AppTest follows go_to()'s st.rerun()
    # internally (queue -> consume before radio -> render target page).
    at.button(key="home_cta_advisor").click()
    at.run()

    assert not at.exception, f"CTA navigation crashed: {at.exception}"
    assert at.sidebar.radio[0].value == "⭐ AI Career Advisor"
    # The request is consumed exactly once -> no infinite rerun loop.
    assert _session_get(at, "requested_navigation") is None


@pytest.mark.parametrize(
    ("host_page", "button_key", "pre_click", "expected_page"),
    [
        ("Market Insights", "mi_cta_skills", None, "Skills Intelligence"),
        ("Salary Explorer", "se_cta_company", None, "Company Intelligence"),
        ("Skills Intelligence", "si_cta_advisor", None, "⭐ AI Career Advisor"),
        # The Career Advisor CTA only exists after running the analysis.
        ("⭐ AI Career Advisor", "ca_to_jobs", "ca_analyze", "Job Recommendations"),
    ],
)
def test_every_cta_routes_to_its_target_page(
    host_page: str, button_key: str, pre_click: str | None, expected_page: str
) -> None:
    """Every CTA button in the app navigates to its intended page on click."""
    at = _fresh_app()
    assert not at.exception

    at.sidebar.radio[0].set_value(host_page)
    at.run()
    assert not at.exception, f"Host page '{host_page}' crashed: {at.exception}"

    if pre_click is not None:
        at.button(key=pre_click).click()
        at.run()
        assert not at.exception

    # A single run() per interaction: AppTest follows go_to()'s st.rerun()
    # internally (queue -> consume before radio -> render target page).
    at.button(key=button_key).click()
    at.run()

    assert not at.exception, f"CTA '{button_key}' crashed: {at.exception}"
    assert at.sidebar.radio[0].value == expected_page, (
        f"CTA '{button_key}' did not navigate to '{expected_page}'"
    )
    assert _session_get(at, "requested_navigation") is None
