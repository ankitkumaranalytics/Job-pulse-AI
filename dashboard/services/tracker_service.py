"""Application Tracker service (FEATURE 8).

SQLite-backed persistence for saved jobs and applications, plus funnel
analytics. Uses the Python standard library (sqlite3) so it adds zero
dependencies and works identically locally and on small VMs.

HONEST LIMITATION: Streamlit Community Cloud has an ephemeral filesystem,
so the SQLite file resets on redeploy/restart there. For durable cloud
storage, point ``JOBPULSE_TRACKER_DB`` at a mounted volume or swap the
engine for PostgreSQL (documented in the README).
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from dashboard.models.application import Application, STATUSES
from dashboard.utils.validation import ServiceError

from src.config import BASE_DIR  # project import style

DEFAULT_DB_PATH = Path(BASE_DIR) / "data" / "jobpulse_tracker.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    location TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Saved',
    applied_date TEXT NOT NULL,
    notes TEXT DEFAULT '',
    match_score REAL,
    source TEXT DEFAULT 'manual',
    updated_at TEXT DEFAULT ''
);
"""


def _resolve_path() -> Path:
    import os

    override = os.getenv("JOBPULSE_TRACKER_DB", "").strip()
    return Path(override) if override else DEFAULT_DB_PATH


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else _resolve_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def _safe_company(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ServiceError("Company name is required to track an application.")
    if len(cleaned) > 120:
        raise ServiceError("Company name is too long (max 120 characters).")
    return cleaned

def add_application(
    company: str,
    role: str,
    location: str = "",
    status: str = "Saved",
    applied_date: str | None = None,
    notes: str = "",
    match_score: float | None = None,
    source: str = "manual",
    db_path: str | Path | None = None,
) -> int:
    """Insert one application; returns its new id."""
    app = Application(
        company=_safe_company(company),
        role=(role or "").strip() or "Unspecified Role",
        location=(location or "").strip(),
        status=status if status in STATUSES else "Saved",
        applied_date=applied_date or date.today().isoformat(),
        notes=(notes or "").strip()[:2000],
        match_score=match_score,
        source=source,
    )
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO applications (company, role, location, status, applied_date,"
            " notes, match_score, source, updated_at) VALUES (:company, :role,"
            " :location, :status, :applied_date, :notes, :match_score, :source,"
            " :updated_at)",
            app.to_row(),
        )
        return int(cursor.lastrowid)


def list_applications(db_path: str | Path | None = None) -> list[dict]:
    """Return all tracked applications, newest activity first."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    return [Application.from_row(dict(r)).__dict__ for r in rows]


def update_status(app_id: int, status: str, db_path: str | Path | None = None) -> None:
    if status not in STATUSES:
        raise ServiceError(f"Invalid status '{status}'.")
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(timespec="seconds"), app_id),
        )
        if cursor.rowcount == 0:
            raise ServiceError("Application not found — it may have been deleted.")


def update_notes(app_id: int, notes: str, db_path: str | Path | None = None) -> None:
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE applications SET notes = ?, updated_at = ? WHERE id = ?",
            ((notes or "").strip()[:2000],
             datetime.now().isoformat(timespec="seconds"), app_id),
        )
        if cursor.rowcount == 0:
            raise ServiceError("Application not found — it may have been deleted.")


def delete_application(app_id: int, db_path: str | Path | None = None) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))


def tracker_analytics(applications: list[dict]) -> dict:
    """Funnel analytics (rates are honest percentages of the real counts)."""
    total = len(applications)
    by_status = {s: 0 for s in STATUSES}
    for app in applications:
        by_status[app["status"]] = by_status.get(app["status"], 0) + 1

    applied = sum(
        by_status[s] for s in ("Applied", "Assessment", "Interview", "Offer", "Rejected")
    )
    responded = sum(
        by_status[s] for s in ("Assessment", "Interview", "Offer", "Rejected")
    )
    interviews = by_status["Interview"] + by_status["Offer"]
    offers = by_status["Offer"]

    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    this_week = sum(1 for a in applications if (a.get("applied_date") or "") >= week_ago)

    def rate(part: int, whole: int) -> float:
        return round(100.0 * part / whole, 1) if whole else 0.0

    return {
        "total": total,
        "by_status": by_status,
        "applied": applied,
        "interview_rate": rate(interviews, applied),
        "response_rate": rate(responded, applied),
        "offer_rate": rate(offers, applied),
        "applications_this_week": this_week,
    }