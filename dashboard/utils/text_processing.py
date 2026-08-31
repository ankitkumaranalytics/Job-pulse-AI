"""Text processing helpers shared by the AI services (pure Python)."""
from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"[ \t]+")
_YEARS_RE = re.compile(r"(\d{1,2})\+?\s*(?:\+)?\s*years?", re.IGNORECASE)
_DEGREE_PATTERNS: list[tuple[str, str]] = [
    (r"ph\.?d|doctorate", "Doctorate"),
    (r"m\.?tech|master of technology|m\.?s\.?c?\b|m\.?e\b(?![a-z])|master(?:'s)?\b(?!.*degree of)"
     r"|mba|m\.?c\.?a\b|m\.?com", "Masters"),
    (r"b\.?tech|bachelor of technology|b\.?e\b(?![a-z])|b\.?s\.?c?\b|b\.?c\.?a\b|b\.?com"
     r"|bachelor(?:'s)?\b|bba", "Bachelors"),
    (r"diploma|associate", "Diploma"),
]
_ACTION_VERBS = {
    "built", "developed", "designed", "automated", "analyzed", "analysed",
    "improved", "reduced", "increased", "created", "led", "implemented",
    "optimized", "optimised", "delivered", "managed", "dashboard", "pipeline",
}


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (except newlines) and strip line edges."""
    if not text:
        return ""
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def dedupe_keep_order(items: list[str]) -> list[str]:
    """Case-insensitive de-duplication that preserves first-seen casing."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = str(item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(str(item).strip())
    return out


def extract_years_experience(text: str) -> float | None:
    """
    Extract the maximum 'N years' mention from resume/JD text.

    Returns None when no explicit experience duration is stated
    (the caller decides what a missing value means).
    """
    if not text:
        return None
    years = [float(m) for m in _YEARS_RE.findall(text)]
    return max(years) if years else None


def detect_education_level(text: str) -> str | None:
    """Return the highest education level mentioned ('Doctorate'…'Diploma')."""
    if not text:
        return None
    lowered = text.lower()
    for pattern, label in _DEGREE_PATTERNS:
        if re.search(pattern, lowered):
            return label
    return None


def has_quantified_achievements(text: str) -> bool:
    """True when the text contains measurable outcomes (%, numbers, ₹/$)."""
    if not text:
        return False
    return bool(re.search(r"\d+\s*%|\b\d{2,}\+?\b|[₹$€]\s?\d", text))


def action_verb_count(text: str) -> int:
    """Count achievement-style action verbs (used by the ATS structure score)."""
    if not text:
        return 0
    lowered = text.lower()
    return sum(1 for verb in _ACTION_VERBS if verb in lowered)


def truncate(text: str, length: int = 400) -> str:
    """Truncate long text for TF-IDF documents and previews."""
    if not text:
        return ""
    return text[:length]
