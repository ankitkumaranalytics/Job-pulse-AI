"""
Sidebar navigation, cached data loading and health checks for the dashboard.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import BASE_DIR, is_db_configured, logger  # noqa: E402
from src.data_access import DB_SOURCE, load_dashboard_dataframe  # noqa: E402
from src.data_loader import DatasetNotFoundError  # noqa: E402

# Core columns the dashboard expects; pages degrade gracefully if some are
# absent, but these drive the primary views.
CORE_COLUMNS = [
    "standardized_job_title",
    "company",
    "city",
    "industry",
    "experience_category",
    "salary_average",
    "posting_date",
    "extracted_skills",
]

DATA_TIER_LABEL = {"database": "PostgreSQL", "processed": "Processed", "cleaned": "Cleaned", "raw": "Raw"}


@st.cache_data(show_spinner="Loading job market data…")
def load_dashboard_data() -> tuple[pd.DataFrame, str, bool]:
    """
    Load the best available dataset (cached across reruns).

    Priority: PostgreSQL -> processed CSV -> cleaned CSV -> raw CSV.

    Returns
    -------
    (pd.DataFrame, str, bool)
        Dataframe, source name ('database' | 'processed' | 'cleaned' |
        'raw'), and True only when the database was configured but the
        connection attempt failed (CSV fallback was used).
    """
    try:
        return load_dashboard_dataframe()
    except DatasetNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc


@st.cache_data(show_spinner=False)
def parse_skills_for_session(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure ``extracted_skills`` is a list column after CSV round-trip."""
    df = df.copy()
    if "extracted_skills" in df.columns:
        df["extracted_skills"] = df["extracted_skills"].apply(
            lambda x: x if isinstance(x, list) else (
                [] if pd.isna(x) else [s.strip() for s in str(x).split(";") if s.strip()]
            )
        )
    return df


def run_health_checks(df: pd.DataFrame | None) -> list[tuple[str, bool, str]]:
    """
    Internal health check (Phase 17). Returns rows of (check, ok, detail).

    Never exposes secrets or connection strings.
    """
    checks: list[tuple[str, bool, str]] = []

    # 1. Dataset available
    if df is not None and len(df) > 0:
        checks.append(("Dataset available", True, f"{len(df):,} rows loaded"))
    else:
        checks.append(("Dataset available", False, "No rows loaded"))

    # 2. Required columns
    if df is not None and len(df) > 0:
        missing = [c for c in CORE_COLUMNS if c not in df.columns]
        if missing:
            checks.append(("Required columns", False, f"Missing: {', '.join(missing)}"))
        else:
            checks.append(("Required columns", True, f"All {len(CORE_COLUMNS)} present"))
    else:
        checks.append(("Required columns", False, "Skipped (no data)"))

    # 3. Skill extraction engine importable + dictionary populated
    try:
        from src.skill_extractor import get_all_skills

        n_skills = len(get_all_skills())
        checks.append(("Skill extraction engine", True, f"{n_skills} skills in dictionary"))
    except Exception as exc:  # pragma: no cover - defensive
        checks.append(("Skill extraction engine", False, f"Import failed: {type(exc).__name__}"))

    # 4. Recommendation engine available
    try:
        from models.job_recommender import JobRecommender  # noqa: F401

        checks.append(("Recommendation engine", True, "TF-IDF model available"))
    except Exception as exc:  # pragma: no cover - defensive
        checks.append(("Recommendation engine", False, f"Import failed: {type(exc).__name__}"))

    # 5. Database connection (optional - CSV fallback is always active)
    if is_db_configured():
        try:
            from src.database_loader import test_connection

            if test_connection():
                checks.append(("Database (optional)", True, "Connected successfully"))
            else:
                checks.append(("Database (optional)", True, "Unreachable - CSV fallback active"))
        except Exception:  # pragma: no cover - defensive
            checks.append(("Database (optional)", True, "Unreachable - CSV fallback active"))
    else:
        checks.append(("Database (optional)", True, "Not configured - using CSV fallback"))

    # 6. Streamlit configuration (theme file committed to the repo)
    if (BASE_DIR / ".streamlit" / "config.toml").exists():
        checks.append(("Streamlit configuration", True, "Theme config found"))
    else:
        checks.append(("Streamlit configuration", True, "Default theme in use"))

    return checks


def render_health_section() -> None:
    """Developer-friendly diagnostics expander in the sidebar."""
    with st.sidebar.expander("🩺 System Health", expanded=False):
        df = st.session_state.get("df")
        for name, ok, detail in run_health_checks(df):
            icon = "✅" if ok else "❌"
            st.markdown(f"{icon} **{name}**  \n<span style='font-size:0.78rem;opacity:0.7'>{detail}</span>",
                        unsafe_allow_html=True)


def render_sidebar() -> None:
    """Render the sidebar branding, navigation info and health section."""
    with st.sidebar:
        st.markdown("## 📊 JobPulse AI")
        st.markdown("*Job Market & Skills Intelligence*")
        st.divider()
        st.caption("**Pages**")
        st.markdown("""
        - 🏠 Home
        - 📈 Market Insights
        - 🧠 Skills Intelligence
        - 💰 Salary Explorer
        - 🏢 Company Insights
        - 🎯 Career Advisor
        - 📋 Job Recommendations
        """)
        st.divider()
        # Non-blocking data-source badge
        source = st.session_state.get("data_source")
        if source:
            label = DATA_TIER_LABEL.get(source, source.title())
            if source == DB_SOURCE:
                st.caption(f"🟢 Data source: **{label}**")
            else:
                st.caption(f"🟢 Data source: **{label} CSV** (PostgreSQL not in use)")
        if st.session_state.get("db_attempted_failed"):
            st.caption("🟡 Database unreachable — CSV fallback active")
        st.caption("Built with Streamlit, Python, Plotly & PostgreSQL")
        render_health_section()


def show_datasets_tab() -> None:
    """Optional sidebar expander listing available datasets."""
    with st.sidebar.expander("📁 Available Datasets"):
        st.caption("Data sources available for this dashboard:")
        st.markdown("- `data/raw/jobs.csv` (raw)")
        st.markdown("- `data/cleaned/jobs_cleaned.csv`")
        st.markdown("- `data/processed/jobs_processed.csv`")