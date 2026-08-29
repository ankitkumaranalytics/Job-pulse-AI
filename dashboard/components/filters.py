"""
Safe filter helpers for dashboard pages.

Guarantees that selectboxes never receive NaN/empty options and that
empty filtered results produce a friendly message instead of crashes.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

ALL = "All"


def safe_unique_values(df: pd.DataFrame, column: str) -> list[str]:
    """
    Return sorted unique non-null values of a column as strings.

    Missing column or empty data yields an empty list (never raises).
    """
    if column not in df.columns or len(df) == 0:
        return []
    vals = df[column].dropna().astype(str).str.strip()
    vals = vals[vals != ""]
    return sorted(vals.unique().tolist())


def select_filter(
    df: pd.DataFrame,
    column: str,
    label: str,
    key: str | None = None,
) -> str:
    """
    Render a safe 'All + unique values' selectbox for a column.

    Returns the selected value ('All' when no data / no selection).
    """
    options = [ALL] + safe_unique_values(df, column)
    return st.selectbox(label, options, key=key)


def show_no_data(context: str = "the selected filters") -> None:
    """Standard empty-state message for filtered views."""
    st.warning(
        f"📉 No data is available for {context}. "
        "Please adjust your filters and try again."
    )


def filter_dataframe(
    df: pd.DataFrame,
    role: str | None = None,
    location: str | None = None,
    industry: str | None = None,
    experience: str | None = None,
    date_range: tuple | None = None,
    date_column: str = "posting_date",
) -> pd.DataFrame:
    """
    Apply standard dashboard filters, tolerating missing columns.

    All comparisons are NaN-safe; date filtering is skipped unless the
    range is a proper (start, end) pair.
    """
    filtered = df

    if role and role != ALL and "standardized_job_title" in filtered.columns:
        filtered = filtered[filtered["standardized_job_title"] == role]

    if location and location != ALL and "city" in filtered.columns:
        filtered = filtered[filtered["city"] == location]

    if industry and industry != ALL and "industry" in filtered.columns:
        filtered = filtered[filtered["industry"] == industry]

    if experience and experience != ALL and "experience_category" in filtered.columns:
        filtered = filtered[filtered["experience_category"] == experience]

    if (
        date_range
        and isinstance(date_range, (tuple, list))
        and len(date_range) == 2
        and date_column in filtered.columns
    ):
        start, end = date_range
        dates = pd.to_datetime(filtered[date_column], errors="coerce")
        filtered = filtered[dates.between(pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1))]

    return filtered