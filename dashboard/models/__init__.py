"""Typed entities shared across the career-intelligence services.

These are deliberately small dataclasses (no ORM, no pydantic) so the
services stay dependency-light and fully unit-testable.
"""
from dashboard.models.application import Application, STATUSES
from dashboard.models.job import Job
from dashboard.models.resume import ResumeProfile
from dashboard.models.user_profile import UserProfile

__all__ = ["Application", "STATUSES", "Job", "ResumeProfile", "UserProfile"]