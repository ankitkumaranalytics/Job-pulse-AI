"""
Sidebar navigation and data loading for the dashboard.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_OUTPUT_DIR, DATA_PATH, logger


@st.cache_data(show_spinner=False)
def load_processed_data() -> pd.DataFrame:
    """
    Load the processed dataset for the dashboard.

    Tries data/processed/jobs_processed.csv first, then falls back
    to running the pipeline from data/raw/jobs.csv if needed.
    """
    processed_path = Path(DATA_OUTPUT_DIR) / "jobs_processed.csv"

    if processed_path.exists():
        df = pd.read_csv(processed_path)
    else:
        # Attempt to load from raw data through a minimal pipeline
        from src.data_loader import load_raw_data, detect_and_rename_columns
        from src.data_cleaning import clean_data
        from src.skill_extractor import extract_skills
        from src.feature_engineering import engineer_features

        if not Path(DATA_PATH).exists():
            st.error(
                "No data found. Please run 'python scripts/generate_sample_data.py' "
                "followed by 'python scripts/run_pipeline.py --skip-db'."
            )
            st.stop()

        raw = load_raw_data()
        raw = detect_and_rename_columns(raw)
        cleaned = clean_data(raw)
        cleaned = extract_skills(cleaned)
        df = engineer_features(cleaned)

    # Safely convert extracted_skills strings back to lists
    if "extracted_skills" in df.columns and df["extracted_skills"].dtype == object:
        df["extracted_skills"] = df["extracted_skills"].apply(
            lambda x: x if isinstance(x, list) else (
                [] if pd.isna(x) else [s.strip() for s in str(x).split(";") if s.strip()]
            )
        )

    return df


def render_sidebar() -> None:
    """Render the sidebar branding and navigation info."""
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
        st.caption("Built with Streamlit, Python, Plotly & PostgreSQL")


def show_datasets_tab() -> None:
    """Optional sidebar expander listing available datasets."""
    with st.sidebar.expander("📁 Available Datasets"):
        st.caption("Data sources available for this dashboard:")
        st.markdown("- `data/raw/jobs.csv` (raw)")
        st.markdown("- `data/cleaned/jobs_cleaned.csv`")
        st.markdown("- `data/processed/jobs_processed.csv`")


def notify_if_raw_data() -> None:
    """Display a notice in the sidebar if data is likely synthetic."""
    # We can't easily determine synthetic-ness here; the notice is
    # shown on the Home page. Kept as a hook for future real data.
    pass