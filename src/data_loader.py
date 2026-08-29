"""
Data loading module for JobPulse AI.

Provides a flexible ``load_raw_data`` function that:
- Accepts CSV, Excel, or JSON inputs
- Detects required vs. optional columns
- Handles encoding issues gracefully
- Returns a standardised pandas DataFrame
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import DATA_PATH, RAW_DATA_DIR
from .utils import detect_columns

logger = logging.getLogger("jobpulse")

# Columns that are truly required for the pipeline to function
REQUIRED_COLUMNS = {"job_title", "company", "job_description"}

# Optional but useful columns
OPTIONAL_COLUMNS = [
    "job_id", "location", "city", "state", "country", "industry",
    "salary", "salary_min", "salary_max", "currency",
    "experience", "experience_min", "experience_max", "employment_type",
    "posting_date", "skills",
]


def load_raw_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load raw job-posting data from a file.

    Parameters
    ----------
    filepath : str | None
        Path to the data file. If *None*, uses ``DATA_PATH`` from config.

    Returns
    -------
    pd.DataFrame
        Raw job data.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file is empty or required columns are missing.
    """
    if filepath is None:
        filepath = DATA_PATH

    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            f"Tip: Run 'python scripts/generate_sample_data.py' to create sample data."
        )

    if path.stat().st_size == 0:
        raise ValueError(f"Data file is empty: {path}")

    # Determine file type and load
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="warn")
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path, engine="openpyxl")
    elif suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.json_normalize(data)
    else:
        # Default to CSV
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="warn")

    logger.info("Loaded raw data: %s — %d rows, %d columns", path, df.shape[0], df.shape[1])

    # Check required columns
    existing_columns = set(df.columns.str.strip())
    missing_required = REQUIRED_COLUMNS - existing_columns
    if missing_required:
        # Try case-insensitive matching
        df_cols_lower = {c.lower(): c for c in df.columns}
        resolved = set()
        for col in missing_required:
            if col.lower() in df_cols_lower:
                resolved.add(col)
        missing_required = missing_required - resolved

    if missing_required:
        raise ValueError(
            f"Missing required columns: {missing_required}\n"
            f"Required columns are: {REQUIRED_COLUMNS}\n"
            f"Found columns: {list(df.columns)}"
        )

    return df


def detect_and_rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect columns that may have slightly different names and rename them
    to the standard column names expected by the pipeline.
    """
    rename_map = {}
    all_cols_lower = {c.lower(): c for c in df.columns}

    column_aliases = {
        "job_title": ["job_title", "title", "position", "role", "jobname"],
        "company": ["company", "employer", "organisation", "organization", "company_name"],
        "location": ["location", "location_name", "city_region"],
        "city": ["city", "city_name"],
        "state": ["state", "state_name", "province"],
        "country": ["country", "country_name"],
        "industry": ["industry", "sector"],
        "salary": ["salary", "salary_package", "ctc", "compensation"],
        "salary_min": ["salary_min", "min_salary", "salary_minimum"],
        "salary_max": ["salary_max", "max_salary", "salary_maximum"],
        "currency": ["currency", "curr"],
        "experience": ["experience", "exp", "experience_required", "yrs"],
        "experience_min": ["experience_min", "min_experience", "exp_min"],
        "experience_max": ["experience_max", "max_experience", "exp_max"],
        "employment_type": ["employment_type", "employmenttype", "job_type"],
        "posting_date": ["posting_date", "date", "posted_date", "date_posted", "created_date"],
        "job_description": ["job_description", "description", "desc", "job_desc", "details"],
        "skills": ["skills", "skill_set", "required_skills", "technical_skills"],
        "job_id": ["job_id", "id", "job_id", "ref_id"],
    }

    for standard_name, aliases in column_aliases.items():
        if standard_name in [c.lower() for c in df.columns]:
            continue  # already standard
        for alias in aliases:
            if alias.lower() in all_cols_lower and standard_name not in rename_map.values():
                rename_map[all_cols_lower[alias.lower()]] = standard_name
                break

    if rename_map:
        df = df.rename(columns=rename_map)
        logger.info("Renamed columns: %s", rename_map)

    return df


# ---------------------------------------------------------------------------
# Dashboard-facing tiered dataset loading (PostgreSQL-free fallback chain)
# ---------------------------------------------------------------------------
# Priority: processed CSV -> cleaned CSV -> raw CSV -> clear error.
# These functions are intentionally Streamlit-free so tests can use them;
# the dashboard wraps them in @st.cache_data (see dashboard/components).

class DatasetNotFoundError(RuntimeError):
    """Raised when no usable dataset tier is available."""


def parse_extracted_skills_column(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise the ``extracted_skills`` column to Python lists (in place)."""
    if "extracted_skills" in df.columns and df["extracted_skills"].dtype == object:
        df["extracted_skills"] = df["extracted_skills"].apply(
            lambda x: x if isinstance(x, list) else (
                [] if pd.isna(x) else [s.strip() for s in str(x).split(";") if s.strip()]
            )
        )
    return df


def load_tiered_dataset() -> tuple[pd.DataFrame, str]:
    """
    Load the best available dataset tier for the dashboard.

    Returns
    -------
    (pd.DataFrame, str)
        The dataframe and the tier name: 'processed', 'cleaned' or 'raw'.

    Raises
    ------
    DatasetNotFoundError
        If no dataset file exists at all (message explains what to run).
    """
    from .config import DATA_OUTPUT_DIR, CLEANED_DATA_DIR

    processed_path = Path(DATA_OUTPUT_DIR) / "jobs_processed.csv"
    cleaned_path = Path(CLEANED_DATA_DIR) / "jobs_cleaned.csv"

    # Tier 1: processed (preferred - has all engineered features + skills)
    if processed_path.exists():
        try:
            df = pd.read_csv(processed_path)
            df = parse_extracted_skills_column(df)
            logger.info("Dashboard data source: processed (%d rows)", len(df))
            return df, "processed"
        except Exception as exc:  # corrupted CSV - fall through to next tier
            logger.warning("Processed CSV unreadable, falling back: %s", exc)

    # Tier 2: cleaned (needs skill extraction + feature engineering)
    if cleaned_path.exists():
        try:
            from .skill_extractor import extract_skills
            from .feature_engineering import engineer_features

            df = pd.read_csv(cleaned_path)
            df = extract_skills(df)
            df = engineer_features(df)
            df = parse_extracted_skills_column(df)
            logger.info("Dashboard data source: cleaned (%d rows)", len(df))
            return df, "cleaned"
        except Exception as exc:
            logger.warning("Cleaned CSV pipeline failed, falling back: %s", exc)

    # Tier 3: raw (run the minimal in-memory pipeline)
    raw_path = Path(DATA_PATH)
    if raw_path.exists():
        from .skill_extractor import extract_skills
        from .feature_engineering import engineer_features
        from .data_cleaning import clean_data

        raw = load_raw_data(str(raw_path))
        raw = detect_and_rename_columns(raw)
        df = clean_data(raw)
        df = extract_skills(df)
        df = engineer_features(df)
        df = parse_extracted_skills_column(df)
        logger.info("Dashboard data source: raw (%d rows)", len(df))
        return df, "raw"

    # Nothing available - raise with actionable guidance
    raise DatasetNotFoundError(
        "No job market dataset found. Looked for:\n"
        f"  - {processed_path}\n"
        f"  - {cleaned_path}\n"
        f"  - {raw_path}\n"
        "Fix: run 'python scripts/generate_sample_data.py' followed by "
        "'python scripts/run_pipeline.py --skip-db'."
    )
