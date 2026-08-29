"""
Utility functions shared across the JobPulse AI project.

Includes helper functions for:
- Safe numeric conversion
- Safe date parsing
- DataFrame info summaries
- Logging helpers
- Path management
"""
from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger("jobpulse")


# ---------------------------------------------------------------------------
# Safe numeric conversion
# ---------------------------------------------------------------------------
def safe_float(value: Any, default: float = float("nan")) -> float:
    """Convert a value to float safely, returning *default* on failure."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int safely, returning *default* on failure."""
    f = safe_float(value, default=float(default))
    if pd.isna(f):
        return default
    return int(f)


# ---------------------------------------------------------------------------
# Safe date parsing
# ---------------------------------------------------------------------------
def safe_datetime(value: Any) -> pd.Timestamp:
    """Parse a date/datetime value safely, returning NaT on failure."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    try:
        return pd.to_datetime(value, errors="coerce")
    except Exception:
        return pd.NaT


# ---------------------------------------------------------------------------
# Column detection helpers
# ---------------------------------------------------------------------------
def detect_columns(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """
    Given a list of candidate column names, return the first one that
    exists (case-insensitive) in *df*.
    """
    df_cols_lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in df_cols_lower:
            return df_cols_lower[candidate.lower()]
    return None


# ---------------------------------------------------------------------------
# DataFrame summary
# ---------------------------------------------------------------------------
def dataframe_summary(df: pd.DataFrame) -> str:
    """Return a human-readable summary string of a DataFrame."""
    lines = [
        f"Shape: {df.shape[0]} rows × {df.shape[1]} columns",
        f"Columns: {list(df.columns)}",
    ]
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing) > 0:
        lines.append("Missing values:")
        for col, count in missing.items():
            pct = count / len(df) * 100
            lines.append(f"  {col}: {count} ({pct:.1f}%)")
    else:
        lines.append("No missing values")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def file_exists(path: str | Path) -> bool:
    """Check if a file exists and is non-empty."""
    p = Path(path)
    return p.exists() and p.stat().st_size > 0
def unique_options(df: pd.DataFrame, column: str) -> list[str]:
    """
    Return sorted, unique, non-null string values of *column*.

    Safe for Streamlit selectboxes/multiselects: drops NaN/None/blank values
    and always returns plain strings. Returns an empty list when the column
    is missing or contains no valid values.
    """
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str).str.strip()
    values = values[values != ""]
    return sorted(values.unique().tolist())


# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------
def normalize_text(text: Any) -> str:
    """Normalize text: lowercase, strip whitespace, collapse spaces."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def contains_keywords(text: Any, keywords: list[str]) -> bool:
    """Check if *text* contains any of the *keywords* (case-insensitive)."""
    if not text:
        return False
    text_lower = normalize_text(text).lower()
    return any(kw.lower() in text_lower for kw in keywords)
