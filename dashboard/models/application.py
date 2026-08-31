"""Application entity for the Job Application Tracker (FEATURE 8)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from dashboard.utils.constants import APPLICATION_STATUSES

STATUSES = APPLICATION_STATUSES


@dataclass
class Application:
    """One tracked job application."""

    id: int | None = None
    company: str = ""
    role: str = ""
    location: str = ""
    status: str = "Saved"
    applied_date: str = ""  # ISO date string (YYYY-MM-DD)
    notes: str = ""
    match_score: float | None = None  # 0-100 profile-job alignment
    source: str = "manual"
    updated_at: str = ""

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            self.status = "Saved"
        if not self.applied_date:
            self.applied_date = date.today().isoformat()

    def to_row(self) -> dict:
        """Flatten for SQLite insert/update."""
        return {
            "company": self.company,
            "role": self.role,
            "location": self.location,
            "status": self.status,
            "applied_date": self.applied_date,
            "notes": self.notes,
            "match_score": self.match_score,
            "source": self.source,
            "updated_at": self.updated_at or datetime.now().isoformat(timespec="seconds"),
        }

    @classmethod
    def from_row(cls, row) -> "Application":
        """Build from a SQLite row mapping."""
        score = row.get("match_score")
        return cls(
            id=row.get("id"),
            company=row.get("company", "") or "",
            role=row.get("role", "") or "",
            location=row.get("location", "") or "",
            status=row.get("status", "Saved") or "Saved",
            applied_date=row.get("applied_date", "") or "",
            notes=row.get("notes", "") or "",
            match_score=float(score) if score is not None else None,
            source=row.get("source", "manual") or "manual",
            updated_at=row.get("updated_at", "") or "",
        )
