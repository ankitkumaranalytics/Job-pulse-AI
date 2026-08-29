"""
Data validation pipeline for JobPulse AI.

Performs comprehensive validation checks on raw job-posting data and
produces a structured validation report (JSON + CSV).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import CLEANED_DATA_DIR, logger
from .data_loader import REQUIRED_COLUMNS
from .utils import ensure_dir

NUMERIC_COLUMNS = ["salary_min", "salary_max", "experience_min", "experience_max"]
DATE_COLUMNS = ["posting_date"]


class ValidationReport:
    """Container for validation results."""

    def __init__(self):
        self.total_rows: int = 0
        self.valid_rows: int = 0
        self.invalid_rows: int = 0
        self.duplicate_rows: int = 0
        self.missing_values: dict = {}
        self.warnings: list = []
        self.errors: list = []
        self.column_report: dict = {}
        self.timestamp: str = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "duplicate_rows": self.duplicate_rows,
            "missing_values": self.missing_values,
            "warnings": self.warnings,
            "errors": self.errors,
            "column_report": self.column_report,
        }

    def save_json(self, filepath) -> None:
        ensure_dir(Path(filepath).parent)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info("Validation report saved to %s", filepath)

    def save_csv(self, filepath) -> None:
        ensure_dir(Path(filepath).parent)
        rows = []
        for col, stats in self.column_report.items():
            rows.append({
                "column": col,
                "dtype": stats.get("dtype", "unknown"),
                "non_null": stats.get("non_null", 0),
                "null_count": stats.get("null_count", 0),
                "null_pct": stats.get("null_pct", 0),
                "invalid_count": stats.get("invalid_count", 0),
                "unique_count": stats.get("unique_count", 0),
            })
        summary = pd.DataFrame(rows)
        summary.to_csv(filepath, index=False)
        logger.info("Validation CSV report saved to %s", filepath)



def validate_data(df: pd.DataFrame, report_dir=None) -> ValidationReport:
    """
    Run the full validation pipeline on a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw job data.
    report_dir : str | Path | None
        Directory to save the report. Defaults to data/cleaned/.

    Returns
    -------
    ValidationReport
        Structured validation results.
    """
    report = ValidationReport()
    report.total_rows = len(df)

    if report_dir is None:
        report_dir = CLEANED_DATA_DIR
    report_dir = Path(report_dir)

    # 1. Required columns
    existing_cols_lower = {c.lower(): c for c in df.columns}
    missing_required = set()
    for col in REQUIRED_COLUMNS:
        if col.lower() not in existing_cols_lower:
            missing_required.add(col)
    if missing_required:
        report.errors.append(f"Missing required columns: {sorted(missing_required)}")
        logger.error("Missing required columns: %s", missing_required)

    # 2-3. Per-column analysis
    for col in df.columns:
        col_str = str(col)
        series = df[col]
        null_count = int(series.isnull().sum())
        non_null = int(series.notna().sum())
        unique_count = int(series.nunique(dropna=True))
        col_stats = {
            "dtype": str(series.dtype),
            "non_null": non_null,
            "null_count": null_count,
            "null_pct": round(null_count / max(len(df), 1) * 100, 2),
            "invalid_count": 0,
            "unique_count": unique_count,
        }
        # Numeric columns
        if col_str in NUMERIC_COLUMNS:
            parsed = pd.to_numeric(series, errors="coerce")
            invalid = parsed.isna() & series.notna()
            col_stats["invalid_count"] = int(invalid.sum())
            if invalid.sum() > 0:
                report.warnings.append(
                    f"Column '{col_str}' has {invalid.sum()} non-numeric values"
                )
        # Date columns
        if col_str in DATE_COLUMNS:
            parsed_dates = pd.to_datetime(series, errors="coerce")
            invalid_dates = parsed_dates.isna() & series.notna()
            col_stats["invalid_count"] = int(invalid_dates.sum())
            if invalid_dates.sum() > 0:
                report.warnings.append(
                    f"Column '{col_str}' has {invalid_dates.sum()} invalid dates"
                )
        # Empty strings in text columns
        if series.dtype == object:
            empty = series.apply(
                lambda x: isinstance(x, str) and x.strip() == ""
            ).sum()
            col_stats["empty_string_count"] = int(empty)
            if empty > 0:
                col_stats["null_count"] += int(empty)
                col_stats["null_pct"] = round(
                    col_stats["null_count"] / max(len(df), 1) * 100, 2
                )
        report.missing_values[col_str] = col_stats["null_count"]
        report.column_report[col_str] = col_stats


    # 3. Duplicate records
    exact_dupes = int(df.duplicated(keep="first").sum())
    report.duplicate_rows = exact_dupes
    if exact_dupes > 0:
        report.warnings.append(f"Found {exact_dupes} exact duplicate rows")

    # Near-duplicates
    near_cols = []
    for c in ["job_title", "company", "location", "posting_date"]:
        for dc in df.columns:
            if str(dc).lower() == c:
                near_cols.append(dc)
    if len(near_cols) == 4:
        near_count = int(df.duplicated(subset=near_cols, keep="first").sum())
        if near_count > exact_dupes:
            report.warnings.append(
                f"Found {near_count} near-duplicate rows"
            )

    # 4. Missing values summary (already collected above)
    for col in df.columns:
        nc = report.column_report[str(col)]["null_count"]
        if nc > 0:
            pct = nc / max(len(df), 1) * 100
            if pct > 50:
                report.warnings.append(
                    f"Column '{col}' has {pct:.1f}% missing values"
                )

    # 5. Invalid dates
    for col in DATE_COLUMNS:
        for dc in df.columns:
            if str(dc).lower() == col:
                parsed = pd.to_datetime(df[dc], errors="coerce")
                invalid = int((parsed.isna() & df[dc].notna()).sum())
                if invalid > 0:
                    report.warnings.append(
                        f"'{dc}': {invalid} invalid date values"
                    )

    # 6. Invalid salary values
    for sc in ["salary_min", "salary_max", "salary"]:
        for dc in df.columns:
            if str(dc).lower() == sc:
                parsed = pd.to_numeric(df[dc], errors="coerce")
                neg = int((parsed < 0).sum())
                if neg > 0:
                    report.warnings.append(
                        f"'{sc}': {neg} negative salary values found"
                    )

    # 7. Invalid experience values
    for ec in ["experience_min", "experience_max"]:
        for dc in df.columns:
            if str(dc).lower() == ec:
                parsed = pd.to_numeric(df[dc], errors="coerce")
                neg = int((parsed < 0).sum())
                if neg > 0:
                    report.warnings.append(
                        f"'{ec}': {neg} negative experience values found"
                    )

    # 8-9. Empty job titles and descriptions
    for dc in df.columns:
        if str(dc).lower() == "job_title":
            empty = int(
                df[dc].isna().sum()
                + df[dc].apply(
                    lambda x: isinstance(x, str) and x.strip() == ""
                ).sum()
            )
            if empty > 0:
                report.warnings.append(
                    f"'job_title': {empty} empty or missing titles"
                )
        if str(dc).lower() in ("job_description", "description"):
            empty = int(
                df[dc].isna().sum()
                + df[dc].apply(
                    lambda x: isinstance(x, str) and x.strip() == ""
                ).sum()
            )
            if empty > 0:
                report.warnings.append(
                    f"'{dc}': {empty} empty or missing descriptions"
                )

    # Summary
    report.valid_rows = report.total_rows - report.invalid_rows
    report.save_json(report_dir / "validation_report.json")
    report.save_csv(report_dir / "validation_report.csv")
    logger.info(
        "Validation complete: %d total, %d duplicates, %d warnings",
        report.total_rows,
        report.duplicate_rows,
        len(report.warnings),
    )
    return report


