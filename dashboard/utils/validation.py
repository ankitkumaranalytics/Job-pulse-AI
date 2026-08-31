"""Validation helpers and user-facing service errors.

Errors raised here are safe to show in the UI: they contain friendly
messages only — never stack traces, credentials, or environment details.
"""
from __future__ import annotations

from dashboard.utils.constants import MAX_RESUME_MB, SUPPORTED_RESUME_FORMATS


class ServiceError(Exception):
    """A predictable service failure with a user-safe message."""


class ResumeParseError(ServiceError):
    """Raised when a resume file cannot be read or parsed."""


def validate_upload(filename: str | None, data: bytes | None) -> str:
    """
    Validate an uploaded resume file. Returns the lower-cased extension.

    Raises ResumeParseError (with a friendly message) when the upload is
    empty, unsupported, or too large. Never logs file contents.
    """
    if not filename:
        raise ResumeParseError("No file was provided. Please choose a file to upload.")
    if data is None or len(data) == 0:
        raise ResumeParseError("The uploaded file is empty. Please upload a valid resume.")

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_RESUME_FORMATS:
        supported = ", ".join(fmt.upper().lstrip(".") for fmt in SUPPORTED_RESUME_FORMATS)
        raise ResumeParseError(
            f"Unsupported file type '{ext or 'unknown'}'. "
            f"Please upload one of: {supported}."
        )

    max_bytes = int(MAX_RESUME_MB * 1024 * 1024)
    if len(data) > max_bytes:
        raise ResumeParseError(
            f"The file is too large ({len(data) / (1024 * 1024):.1f} MB). "
            f"Maximum supported size is {MAX_RESUME_MB:.0f} MB."
        )
    return ext


def validate_query(query: str | None, min_length: int = 2) -> str:
    """Normalise and validate a natural-language search query."""
    cleaned = (query or "").strip()
    if len(cleaned) < min_length:
        raise ServiceError(
            "Please enter a longer search query (at least "
            f"{min_length} characters) describing the job you want."
        )
    if len(cleaned) > 500:
        cleaned = cleaned[:500]
    return cleaned


def require_dataframe(df, required_columns: list[str], feature: str):
    """Raise ServiceError when the dataset is unusable for a feature."""
    import pandas as pd  # deferred: keeps this module import-light

    if df is None or not isinstance(df, pd.DataFrame) or len(df) == 0:
        raise ServiceError(
            f"{feature} needs job data to work. Please load a dataset first."
        )
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ServiceError(
            f"{feature} cannot run: the loaded dataset is missing the "
            f"'{missing[0]}' column. Run the data pipeline to regenerate it."
        )
