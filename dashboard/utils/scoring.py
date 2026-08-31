"""Score normalization helpers.

Every score produced by the career-intelligence services MUST pass
through these helpers so the whole app can guarantee ``0 <= score <= 100``.
Pure Python — safe to unit test outside Streamlit.
"""
from __future__ import annotations


def clamp100(value: float) -> float:
    """Clamp any numeric score to the inclusive range [0, 100]."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return round(max(0.0, min(100.0, v)), 1)


def clamp01(value: float) -> float:
    """Clamp any numeric similarity/probability to the range [0, 1]."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return round(max(0.0, min(1.0, v)), 4)


def weighted_score(components: dict[str, float], weights: dict[str, float]) -> float:
    """
    Combine named component scores (0-100) with weights that sum to 1.0.

    Missing components count as 0 so the total can never exceed 100.
    """
    total = 0.0
    for name, weight in weights.items():
        total += clamp100(components.get(name, 0.0)) * weight
    return clamp100(total)


def band_label(score: float) -> str:
    """Map a 0-100 score to a human-friendly band label."""
    s = clamp100(score)
    if s >= 80:
        return "Excellent"
    if s >= 60:
        return "Strong"
    if s >= 40:
        return "Fair"
    return "Needs Work"
