"""
Data cleaning pipeline for JobPulse AI.
"""
from __future__ import annotations

import re
import logging
from typing import Optional
from pathlib import Path

import pandas as pd
import numpy as np

from .config import CLEANED_DATA_DIR, logger
from .utils import normalize_text, ensure_dir

JOB_TITLE_MAPPING = [
    (r"data\s*analyst", "Data Analyst"),
    (r"business\s*analyst", "Business Analyst"),
    (r"data\s*scientist", "Data Scientist"),
    (r"data\s*engineer", "Data Engineer"),
    (r"machine\s*learning\s*engineer", "Machine Learning Engineer"),
    (r"ml\s*engineer", "Machine Learning Engineer"),
    (r"ai\s*engineer", "Machine Learning Engineer"),
    (r"deep\s*learning", "Machine Learning Engineer"),
    (r"bi\s*analyst|business\s*intelligence", "BI Analyst"),
    (r"analytics\s*engineer", "Analytics Engineer"),
]

LOCATION_MAPPING = {
    "bengaluru": "Bangalore",
    "banglore": "Bangalore",
    "gurugram": "Gurgaon",
    "new delhi": "Delhi",
    "mumbai metropolitan region": "Mumbai",
}

EXP_PATTERNS = [
    (r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:year|yr|years|yrs)", "range"),
    (r"(\d+(?:\.\d+)?)\+\s*(?:year|yr|years|yrs)", "min_only"),
    (r"(\d+(?:\.\d+)?)\s*(?:year|yr|years|yrs)", "exact"),
]


def _find_column(df, name):
    for col in df.columns:
        if str(col).lower() == name.lower():
            return col
    return None


def standardize_job_title(title):
    if pd.isna(title) or str(title).strip() == "":
        return "Other"
    title_lower = normalize_text(title).lower()
    for pattern, standard in JOB_TITLE_MAPPING:
        if re.search(pattern, title_lower):
            return standard
    return "Other"


def standardize_location(location):
    if pd.isna(location) or str(location).strip() == "":
        return "Unknown"
    loc_lower = normalize_text(location).lower()
    if loc_lower in LOCATION_MAPPING:
        return LOCATION_MAPPING[loc_lower]
    for key, value in LOCATION_MAPPING.items():
        if key.lower() in loc_lower:
            return value
    return str(location).strip()


def clean_salary_value(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    text = str(value).replace(",", "").replace("₹", "").replace("$", "").replace("€", "").strip().lower()
    if not text or text in ("unknown", "n/a", "na", "-", "--"):
        return None
    lpa_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lakhs)", text)
    if lpa_match:
        return float(lpa_match.group(1)) * 100000
    l_match = re.search(r"(\d+(?:\.\d+)?)\s*l", text)
    if l_match:
        return float(l_match.group(1)) * 100000
    k_match = re.search(r"(\d+(?:\.\d+)?)\s*k", text)
    if k_match:
        return float(k_match.group(1)) * 1000
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if numbers:
        return float(numbers[0])
    return None


def process_salary(df):
    df = df.copy()
    salary_col = _find_column(df, "salary")
    salary_min_col = _find_column(df, "salary_min")
    salary_max_col = _find_column(df, "salary_max")
    currency_col = _find_column(df, "currency")

    if salary_min_col and salary_max_col:
        df["salary_min"] = pd.to_numeric(df[salary_min_col], errors="coerce")
        df["salary_max"] = pd.to_numeric(df[salary_max_col], errors="coerce")
    elif salary_col:
        min_vals, max_vals = [], []
        for val in df[salary_col]:
            parsed = clean_salary_value(val)
            if parsed is not None:
                min_vals.append(parsed)
                max_vals.append(parsed)
            else:
                min_vals.append(np.nan)
                max_vals.append(np.nan)
        df["salary_min"] = min_vals
        df["salary_max"] = max_vals

    if "salary_min" in df.columns and "salary_max" not in df.columns:
        df["salary_max"] = df["salary_min"]
    elif "salary_max" in df.columns and "salary_min" not in df.columns:
        df["salary_min"] = df["salary_max"]

    if "salary_min" in df.columns and "salary_max" in df.columns:
        df["salary_max"] = df["salary_max"].fillna(df["salary_min"])
        df["salary_min"] = df["salary_min"].fillna(df["salary_max"])
        df["salary_average"] = df[["salary_min", "salary_max"]].mean(axis=1, skipna=True)

    if currency_col:
        df["currency"] = df[currency_col].fillna("INR").replace({"": "INR", "Rs": "INR", "₹": "INR"})
    else:
        df["currency"] = "INR"

    for col in ["salary_min", "salary_max", "salary_average"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def parse_experience(exp_text):
    """Parse experience text into (min_years, max_years)."""
    if pd.isna(exp_text) or str(exp_text).strip() == "":
        return None, None
    text = normalize_text(exp_text).lower()
    if "fresher" in text or "0-1" in text:
        return 0.0, 0.0
    range_match = re.match(
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:year|yr|years|yrs)", text
    )
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))
    min_match = re.match(r"(\d+(?:\.\d+)?)\+\s*(?:year|yr|years|yrs)", text)
    if min_match:
        return float(min_match.group(1)), None
    exact_match = re.match(r"(\d+(?:\.\d+)?)\s*(?:year|yr|years|yrs)", text)
    if exact_match:
        val = float(exact_match.group(1))
        return val, val
    return None, None


def categorize_experience(exp_min):
    """Categorise: Fresher, Entry Level, Mid Level, Senior Level."""
    if exp_min is None or pd.isna(exp_min):
        return "Not Specified"
    if exp_min == 0:
        return "Fresher"
    elif exp_min <= 2:
        return "Entry Level"
    elif exp_min <= 5:
        return "Mid Level"
    else:
        return "Senior Level"


def process_experience(df):
    """Process experience into experience_min, experience_max, experience_category."""
    df = df.copy()
    exp_col = _find_column(df, "experience")
    exp_min_col = _find_column(df, "experience_min")
    exp_max_col = _find_column(df, "experience_max")

    min_vals, max_vals = [], []
    if exp_col:
        for val in df[exp_col]:
            emin, emax = parse_experience(val)
            min_vals.append(emin)
            max_vals.append(emax)
        df["experience_min"] = min_vals
        df["experience_max"] = max_vals
    elif exp_min_col and exp_max_col:
        df["experience_min"] = pd.to_numeric(df[exp_min_col], errors="coerce")
        df["experience_max"] = pd.to_numeric(df[exp_max_col], errors="coerce")

    if "experience_min" in df.columns:
        df["experience_category"] = df["experience_min"].apply(categorize_experience)
    else:
        df["experience_category"] = "Not Specified"
    return df


def handle_missing_values(df):
    """Handle missing values with intelligent defaults."""
    df = df.copy()
    fills = {
        "location": "Unknown", "city": "Unknown", "state": "Unknown",
        "country": "India", "industry": "Other",
        "employment_type": "Not Specified", "currency": "INR",
        "company": "Unknown", "job_description": "", "skills": "",
    }
    for col, default in fills.items():
        actual = _find_column(df, col)
        if actual:
            df[actual] = df[actual].fillna(default)
    if "experience_category" in df.columns:
        df["experience_category"] = df["experience_category"].fillna("Not Specified")
    return df


def remove_duplicates(df):
    """Remove exact and near-duplicate rows."""
    df = df.copy()
    exact = int(df.duplicated(keep="first").sum())
    df = df.drop_duplicates(keep="first")
    logger.info("Removed %d exact duplicates", exact)

    near_cols = []
    for c in ["job_title", "company", "location", "posting_date"]:
        for dc in df.columns:
            if str(dc).lower() == c:
                near_cols.append(dc)
    if len(near_cols) == 4:
        before = len(df)
        df = df.drop_duplicates(subset=near_cols, keep="first")
        removed = before - len(df)
        if removed > 0:
            logger.info("Removed %d near-duplicates", removed)
    return df


def clean_data(df):
    """Run the full data cleaning pipeline."""
    logger.info("Starting data cleaning (%d rows)", len(df))
    df = df.copy()

    df = remove_duplicates(df)

    title_col = _find_column(df, "job_title")
    if title_col:
        df["standardized_job_title"] = df[title_col].apply(standardize_job_title)
    else:
        df["standardized_job_title"] = "Other"

    loc_col = _find_column(df, "location")
    if loc_col:
        df["normalized_location"] = df[loc_col].apply(standardize_location)
    else:
        df["normalized_location"] = "Unknown"

    city_col = _find_column(df, "city")
    if city_col:
        df["city"] = df[city_col].apply(standardize_location)

    df = process_salary(df)
    df = process_experience(df)
    df = handle_missing_values(df)

    date_col = _find_column(df, "posting_date")
    if date_col:
        df["posting_date"] = pd.to_datetime(df[date_col], errors="coerce")

    if not any(str(c).lower() == "job_id" for c in df.columns):
        df["job_id"] = range(1, len(df) + 1)
    else:
        id_col = _find_column(df, "job_id")
        df = df.rename(columns={id_col: "job_id"})
        if df["job_id"].isna().any():
            # Backfill only the missing IDs positionally (fillna() cannot
            # accept a range object in newer pandas versions).
            missing_mask = df["job_id"].isna()
            df.loc[missing_mask, "job_id"] = range(1, int(missing_mask.sum()) + 1)
        try:
            df["job_id"] = df["job_id"].astype(int)
        except (ValueError, TypeError):
            pass  # Non-numeric IDs (e.g. "J1") keep their original dtype

    if "company" in df.columns:
        df["company"] = df["company"].astype(str).str.strip()

    if title_col and title_col != "job_title":
        df = df.rename(columns={title_col: "job_title"})

    logger.info("Data cleaning complete: %d rows", len(df))
    return df


def save_cleaned_data(df, filepath=None):
    """Save the cleaned DataFrame to CSV."""
    if filepath is None:
        ensure_dir(CLEANED_DATA_DIR)
        filepath = Path(CLEANED_DATA_DIR) / "jobs_cleaned.csv"
    path = Path(filepath)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("Cleaned data saved: %s (%d rows)", path, len(df))
    return str(path)
