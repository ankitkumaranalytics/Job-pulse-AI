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
