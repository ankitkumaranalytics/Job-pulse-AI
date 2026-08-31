"""AI service layer for JobPulse AI.

Business + AI logic lives here — Streamlit pages stay thin and only
render results. All scoring is deterministic and explainable; any
heuristic (vs. a learned model) is explicitly labelled in its output.

Pure cores are unit-testable without a Streamlit runtime; cached
wrappers (``@st.cache_data`` / ``@st.cache_resource``) live beside them.
"""
from dashboard.services.match_service import compute_match, estimate_application_strength
from dashboard.services.resume_service import ResumeParseError, analyze_resume, extract_text, parse_resume

__all__ = [
    "ResumeParseError",
    "analyze_resume",
    "compute_match",
    "estimate_application_strength",
    "extract_text",
    "parse_resume",
]