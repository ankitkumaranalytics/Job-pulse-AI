"""
Feature engineering module for JobPulse AI.

Generates derived features from the cleaned dataset:
- standardized_job_title
- salary_average
- experience_category
- posting_month
- posting_year
- posting_weekday
- job_age_days
- normalized_location
- skills_count
"""
from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

from .config import logger
from .utils import normalize_text, ensure_dir
from .data_cleaning import (
    standardize_job_title,
    standardize_location,
    process_salary,
    process_experience,
    _find_column,
)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate all engineered features from a cleaned DataFrame.

    This function is idempotent — running it multiple times produces
    the same result. It safely handles missing data.
    """
    logger.info("Starting feature engineering (%d rows)", len(df))
    df = df.copy()

    # Ensure job cleaning has been applied (idempotent)
    df = process_salary(df)
    df = process_experience(df)

    # 1. standardized_job_title
    title_col = _find_column(df, "job_title")
    if title_col:
        df["standardized_job_title"] = df[title_col].apply(standardize_job_title)
    else:
        df["standardized_job_title"] = "Other"

    # 2. normalized_location (already added by cleaning, but ensure it exists)
    loc_col = _find_column(df, "location")
    if loc_col and "normalized_location" not in df.columns:
        df["normalized_location"] = df[loc_col].apply(standardize_location)
    elif "normalized_location" not in df.columns:
        df["normalized_location"] = "Unknown"

    # 3. posting_date components
    date_col = _find_column(df, "posting_date")
    if date_col:
        df["posting_date"] = pd.to_datetime(df[date_col], errors="coerce")
    elif "posting_date" in df.columns:
        df["posting_date"] = pd.to_datetime(df["posting_date"], errors="coerce")
    else:
        df["posting_date"] = pd.NaT

    df["posting_month"] = df["posting_date"].dt.month
    df["posting_year"] = df["posting_date"].dt.year
    df["posting_weekday"] = df["posting_date"].dt.day_name()

    # 4. job_age_days (days since posting)
    today = pd.Timestamp(datetime.now().date())
    df["job_age_days"] = (today - df["posting_date"]).dt.days
    # Negative or very large ages are invalid — set to NaN
    df.loc[df["job_age_days"] < 0, "job_age_days"] = np.nan
    df.loc[df["job_age_days"] > 3650, "job_age_days"] = np.nan  # > 10 years

    # 5. skills_count
    skills_col = _find_column(df, "skills")
    if skills_col:
        df["skills_count"] = df[skills_col].apply(lambda x: len(str(x).split(",")) if pd.notna(x) and str(x).strip() else 0)
    elif "extracted_skills" in df.columns:
        df["skills_count"] = df["extracted_skills"].apply(
            lambda x: len(x) if isinstance(x, (list, set)) else 0
        )
    else:
        df["skills_count"] = 0

    # 6. experience_category (already created by process_experience if called)
    if "experience_category" not in df.columns:
        df = process_experience(df)

    # 7. Ensure salary_average exists
    if "salary_average" not in df.columns:
        if "salary_min" in df.columns and "salary_max" in df.columns:
            df["salary_average"] = df[["salary_min", "salary_max"]].mean(axis=1, skipna=True)
        elif "salary_min" in df.columns:
            df["salary_average"] = df["salary_min"]
        else:
            df["salary_average"] = np.nan

    logger.info("Feature engineering complete")
    return df


def save_processed_data(df: pd.DataFrame, filepath=None) -> str:
    """Save the feature-engineered DataFrame to CSV."""
    from .config import DATA_OUTPUT_DIR
    if filepath is None:
        ensure_dir(DATA_OUTPUT_DIR)
        filepath = Path(DATA_OUTPUT_DIR) / "jobs_processed.csv"
    path = Path(filepath)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("Processed data saved: %s (%d rows)", path, len(df))
    return str(path)
