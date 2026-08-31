"""Shared constants for the career-intelligence services.

Pure data only — no Streamlit imports — so tests can use this module
outside a Streamlit runtime.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Application Tracker statuses (FEATURE 8)
# ---------------------------------------------------------------------------
APPLICATION_STATUSES: list[str] = [
    "Saved",
    "Applied",
    "Assessment",
    "Interview",
    "Offer",
    "Rejected",
]

# Metadata used to render status pills consistently across pages.
STATUS_META: dict[str, dict[str, str]] = {
    "Saved": {"color": "#64748b", "bg": "#f1f5f9", "icon": "🔖"},
    "Applied": {"color": "#1d4ed8", "bg": "#dbeafe", "icon": "📤"},
    "Assessment": {"color": "#b45309", "bg": "#fef3c7", "icon": "📝"},
    "Interview": {"color": "#7c3aed", "bg": "#ede9fe", "icon": "🎤"},
    "Offer": {"color": "#15803d", "bg": "#dcfce7", "icon": "🎉"},
    "Rejected": {"color": "#b91c1c", "bg": "#fee2e2", "icon": "✖"},
}

# Experience label -> representative years of experience.
EXPERIENCE_YEARS: dict[str, float] = {
    "Fresher": 0.0,
    "Entry Level": 1.5,
    "Mid Level": 3.5,
    "Senior Level": 7.0,
}

# ---------------------------------------------------------------------------
# ATS scoring weights (FEATURE 1) — must sum to 1.0
# ---------------------------------------------------------------------------
ATS_WEIGHTS: dict[str, float] = {
    "skills_coverage": 0.30,
    "keyword_optimization": 0.25,
    "experience_relevance": 0.20,
    "structure": 0.15,
    "project_strength": 0.10,
}

# ---------------------------------------------------------------------------
# Resume↔Job match weights (FEATURE 2) — must sum to 1.0
# ---------------------------------------------------------------------------
MATCH_WEIGHTS: dict[str, float] = {
    "skills_match": 0.30,
    "keyword_match": 0.20,
    "semantic_match": 0.20,
    "experience_match": 0.15,
    "education_match": 0.10,
    "project_relevance": 0.05,
}

# Hybrid recommendation weights (FEATURE 3) — must sum to 1.0
RECOMMENDATION_WEIGHTS: dict[str, float] = {
    "skill": 0.40,
    "semantic": 0.25,
    "preference": 0.20,
    "demand": 0.15,
}

# Upload constraints for resume files
MAX_RESUME_MB: float = 5.0
SUPPORTED_RESUME_FORMATS: tuple[str, ...] = (".pdf", ".docx", ".txt")

# Interview question counts per session
INTERVIEW_QUESTIONS_PER_SESSION: int = 5

# Standard headings recognised when parsing resumes
RESUME_SECTION_HEADINGS: tuple[str, ...] = (
    "summary", "profile", "objective", "experience", "work experience",
    "employment", "education", "skills", "technical skills", "projects",
    "certifications", "certificates", "achievements", "awards", "courses",
)
