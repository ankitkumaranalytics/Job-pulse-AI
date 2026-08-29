"""
Centralized data access layer for JobPulse AI.

Implements the required data-source priority:

1. PostgreSQL (cloud credentials via Streamlit secrets, or local via env/.env)
2. Processed CSV  (data/processed/jobs_processed.csv)
3. Cleaned CSV    (data/cleaned/jobs_cleaned.csv)
4. Raw CSV        (data/raw/jobs.csv)

If the database is unconfigured or unreachable the loader logs the failure
(never exposing credentials) and falls back to CSV so the dashboard keeps
working. This module is intentionally Streamlit-free; the dashboard wraps
``load_dashboard_dataframe`` in ``@st.cache_data`` (see dashboard/components).
"""
from __future__ import annotations

import pandas as pd

from .config import is_db_configured, logger
from .data_loader import DatasetNotFoundError, load_tiered_dataset

DB_SOURCE = "database"
CSV_FALLBACK_SOURCES = {"processed", "cleaned", "raw"}


def load_from_database() -> pd.DataFrame | None:
    """
    Load the jobs dataset from PostgreSQL, or ``None`` when unavailable.

    Returns None (instead of raising) when:
    - credentials are not configured, or
    - the connection/query fails, or
    - the jobs table is empty (pipeline has not been run yet).

    Skill mappings are reconstructed from the ``job_skills``/``skills``
    tables into an ``extracted_skills`` list column so downstream pages
    receive the same schema as the CSV pipeline output.
    """
    if not is_db_configured():
        logger.info("Database not configured - using CSV fallback")
        return None

    try:
        from sqlalchemy import text

        from .database_loader import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            jobs = pd.read_sql(text("SELECT * FROM jobs"), conn)
            if jobs.empty:
                logger.warning("Database connected but jobs table is empty")
                return None
            mappings = pd.read_sql(
                text(
                    "SELECT js.job_id, s.skill_name FROM job_skills js "
                    "JOIN skills s ON js.skill_id = s.skill_id"
                ),
                conn,
            )
        if len(mappings):
            grouped = mappings.groupby("job_id")["skill_name"].apply(
                lambda s: sorted(set(s.dropna()))
            )
            jobs["extracted_skills"] = jobs["job_id"].map(grouped)
        else:
            jobs["extracted_skills"] = [[] for _ in range(len(jobs))]
        jobs["extracted_skills"] = jobs["extracted_skills"].apply(
            lambda v: list(v) if isinstance(v, (list, tuple, pd.Series)) else []
        )
        logger.info("Loaded %d jobs from PostgreSQL", len(jobs))
        return jobs
    except Exception as exc:  # noqa: BLE001 - any DB failure must fall back
        # Log the exception TYPE only - never the message, which could embed
        # host/credential details from driver errors.
        logger.warning("Database load failed (%s) - falling back to CSV", type(exc).__name__)
        return None


def load_dashboard_dataframe() -> tuple[pd.DataFrame, str, bool]:
    """
    Load the best available dataset following the data-source priority.

    Returns
    -------
    (pd.DataFrame, str, bool)
        Dataframe, source name ('database' | 'processed' | 'cleaned' |
        'raw'), and a flag that is True only when the database WAS
        configured but the attempt failed (used to show a non-blocking
        message in the UI).
    """
    db_failed = False

    jobs = load_from_database()
    if jobs is not None:
        return jobs, DB_SOURCE, False
    if is_db_configured():
        db_failed = True  # credentials existed but the attempt failed

    df, tier = load_tiered_dataset()  # processed -> cleaned -> raw
    return df, tier, db_failed


__all__ = [
    "DB_SOURCE",
    "CSV_FALLBACK_SOURCES",
    "DatasetNotFoundError",
    "load_dashboard_dataframe",
    "load_from_database",
]
