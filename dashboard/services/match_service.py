"""AI Job Match Engine (FEATURE 2) + Application Strength estimator (FEATURE 10).

Scores a resume against a job description across six explainable
components. Semantic similarity defaults to a TF-IDF lexical-semantic
proxy (word + character n-gram cosine blend) so it runs anywhere with
scikit-learn; if ``JOBPULSE_USE_EMBEDDINGS=true`` and
``sentence-transformers`` are installed, true embeddings are used with
an automatic fallback.

All weights live in ``dashboard.utils.constants.MATCH_WEIGHTS``.
"""
from __future__ import annotations

import os

from dashboard.utils.constants import MATCH_WEIGHTS
from dashboard.utils.scoring import clamp100, clamp01, weighted_score
from dashboard.utils.text_processing import (
    detect_education_level,
    extract_years_experience,
    truncate,
)

_EDU_ORDER = {"Diploma": 0, "Bachelors": 1, "Masters": 2, "Doctorate": 3}


def _tfidf_cosine(text_a: str, text_b: str, analyzer: str, ngram: tuple[int, int]) -> float:
    """Cosine similarity between two documents with a given TF-IDF config."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(
            analyzer=analyzer, ngram_range=ngram, stop_words="english"
            if analyzer == "word" else None,
            max_features=20000,
        )
        matrix = vectorizer.fit_transform([truncate(text_a, 8000), truncate(text_b, 8000)])
        if matrix.shape[1] == 0:
            return 0.0
        return float(cosine_similarity(matrix[0], matrix[1])[0][0])
    except (ValueError, ImportError):  # empty vocab / sklearn missing
        return 0.0


def _embedding_cosine(text_a: str, text_b: str) -> float | None:
    """Optional true-embedding similarity; None when unavailable/disabled."""
    flag = os.getenv("JOBPULSE_USE_EMBEDDINGS", "").strip().lower()
    if flag not in {"1", "true", "yes"}:
        return None
    try:  # pragma: no cover - optional heavy dependency
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity

        model = SentenceTransformer("all-MiniLM-L6-v2")
        vectors = model.encode([truncate(text_a, 6000), truncate(text_b, 6000)])
        return float(cosine_similarity([vectors[0]], [vectors[1]])[0][0])
    except Exception:  # noqa: BLE001 - any failure falls back to TF-IDF
        return None


def semantic_similarity(text_a: str, text_b: str) -> tuple[float, str]:
    """Return (similarity 0-100, method label). Semantic engine with fallback."""
    emb = _embedding_cosine(text_a, text_b)
    if emb is not None:
        return clamp100(clamp01(emb) * 100), "sentence-transformers embeddings"
    word_sim = _tfidf_cosine(text_a, text_b, "word", (1, 2))
    char_sim = _tfidf_cosine(text_a, text_b, "char_wb", (3, 5))
    blended = 0.6 * word_sim + 0.4 * char_sim
    # Calibration (documented heuristic): long resume vs short JD cosine
    # rarely exceeds ~0.35 even for strong topical alignment, so treat
    # blended cosine of 0.33 as perfect alignment; identical documents
    # still saturate at 100. This keeps scores interpretable without
    # overclaiming precision.
    return clamp100(min(clamp01(blended) / 0.33, 1.0) * 100), "TF-IDF lexical-semantic proxy"

def _jd_required_years(jd_text: str) -> float | None:
    """Infer required years from a JD ('3+ years', 'fresher', 'internship')."""
    lowered = jd_text.lower()
    if "intern" in lowered or "fresher" in lowered or "graduate" in lowered:
        if "years" not in lowered:
            return 0.0
    return extract_years_experience(jd_text)


def _experience_match(resume_years: float | None, jd_years: float | None) -> tuple[float, str]:
    if jd_years is None:
        return 60.0, "JD states no explicit experience requirement (neutral baseline)"
    resume = resume_years or 0.0
    if resume >= jd_years:
        return 100.0, f"Your {resume:g}y meets the {jd_years:g}y+ requirement"
    gap = jd_years - resume
    if gap <= 1:
        return 70.0, f"Close: you have {resume:g}y vs {jd_years:g}y requested"
    return max(20.0, 100.0 - 25.0 * gap), f"Gap of {gap:g} year(s) vs the {jd_years:g}y+ requirement"


def _education_match(resume_level: str | None, jd_text: str) -> tuple[float, str]:
    jd_level = detect_education_level(jd_text)
    if jd_level is None:
        return 70.0, "JD states no specific degree requirement (neutral baseline)"
    if resume_level is None:
        return 35.0, f"JD prefers {jd_level}; no degree detected in resume"
    r = _EDU_ORDER.get(resume_level, 1)
    j = _EDU_ORDER.get(jd_level, 1)
    if r >= j:
        return 100.0, f"Your {resume_level} degree satisfies the {jd_level} requirement"
    return 60.0, f"JD prefers {jd_level}; resume shows {resume_level}"


def compute_match(
    resume_text: str,
    resume_skills: list[str],
    jd_text: str,
    experience_years: float | None = None,
    education_level: str | None = None,
    projects_text: str = "",
) -> dict:
    """Score a resume against a job description (all components 0-100)."""
    from src.skill_extractor import extract_skills_from_text
    from dashboard.utils.validation import ServiceError

    resume_text = resume_text or ""
    jd_text = jd_text or ""
    if not jd_text.strip():
        raise ServiceError("Paste a job description to compute the match score.")

    jd_skills = extract_skills_from_text(jd_text)
    resume_lower = resume_text.lower()
    resume_set = {s.lower() for s in resume_skills}

    # --- Skills Match: JD coverage weighted higher than resume breadth ---
    if jd_skills:
        matched = [s for s in jd_skills if s.lower() in resume_set]
        cov_jd = len(matched) / len(jd_skills)
        cov_res = len(matched) / len(resume_set) if resume_set else 0.0
        skills_score = clamp100((0.7 * cov_jd + 0.3 * cov_res) * 100)
    else:
        matched = list(resume_skills)[:6]
        skills_score = 50.0
    missing = [s for s in jd_skills if s not in matched]

    # --- Keyword Match: coverage of the JD's most distinctive TF-IDF terms ---
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(stop_words="english", max_features=15)
        vectorizer.fit([jd_text])
        top_terms = list(vectorizer.get_feature_names_out())
    except (ValueError, ImportError):
        top_terms = []
    present = [t for t in top_terms if t in resume_lower or t in resume_set]
    keyword_score = clamp100(100.0 * len(present) / len(top_terms)) if top_terms else 55.0

    semantic_score, semantic_method = semantic_similarity(resume_text, jd_text)
    exp_score, exp_note = _experience_match(experience_years, _jd_required_years(jd_text))
    edu_score, edu_note = _education_match(education_level, jd_text)

    # --- Project Relevance: do projects exercise the JD's skills? ---
    project_skills = extract_skills_from_text(projects_text) if projects_text else []
    if projects_text and jd_skills:
        overlap = [s for s in jd_skills if s in project_skills]
        project_score = clamp100(
            max(45.0, 100.0 * len(overlap) / max(1, min(len(jd_skills), 10)))
        )
    elif projects_text:
        project_score = 55.0
    else:
        project_score = 25.0

    components = {
        "skills_match": skills_score,
        "keyword_match": keyword_score,
        "semantic_match": semantic_score,
        "experience_match": exp_score,
        "education_match": edu_score,
        "project_relevance": project_score,
    }
    overall = weighted_score(components, MATCH_WEIGHTS)
    factors = {
        "skills_match": [f"{len(matched)}/{len(jd_skills) if jd_skills else len(resume_skills)} JD skills matched"],
        "keyword_match": [f"{len(present)}/{len(top_terms)} distinctive JD terms present"],
        "semantic_match": [f"Method: {semantic_method}"],
        "experience_match": [exp_note],
        "education_match": [edu_note],
        "project_relevance": [
            f"{len(project_skills)} JD-relevant skills appear in projects"
            if projects_text else "No projects section detected"
        ],
    }
    return {
        "overall": overall,
        "components": components,
        "factors": factors,
        "matched_skills": matched,
        "missing_skills": missing,
        "jd_skills": jd_skills,
        "semantic_method": semantic_method,
        "weights": MATCH_WEIGHTS,
        "scoring_basis": (
            "Explainable weighted blend: skill-set overlap, distinctive-keyword "
            "coverage, semantic similarity, experience fit, education fit and "
            "project relevance. Heuristic scoring — not a machine-learned model."
        ),
    }


def estimate_application_strength(
    match: dict,
    profile_completeness: float = 0.0,
    ats_overall: float | None = None,
) -> dict:
    """
    FEATURE 10 — 'Estimated Application Strength' (0-100).

    Deliberately NOT framed as a hiring prediction: it summarises how well
    the profile aligns with one job description.
    """
    components = match.get("components", {})
    parts = {
        "match_alignment": match.get("overall", 0.0) * 0.60,
        "skill_coverage": components.get("skills_match", 0.0) * 0.15,
        "profile_completeness": clamp100(profile_completeness) * 0.15,
        "resume_quality": (
            (clamp100(ats_overall) if ats_overall is not None else 55.0) * 0.10
        ),
    }
    strength = clamp100(sum(parts.values()))
    factors = [
        f"Overall resume–job match: {match.get('overall', 0):.0f}/100 (weight 60%)",
        f"Skill coverage: {components.get('skills_match', 0):.0f}/100 (weight 15%)",
        f"Profile completeness: {clamp100(profile_completeness):.0f}/100 (weight 15%)",
        (
            f"Resume quality (ATS): {ats_overall:.0f}/100 (weight 10%)"
            if ats_overall is not None
            else "Resume quality: neutral baseline — no ATS scan run (weight 10%)"
        ),
    ]
    if strength >= 75:
        verdict = "Strong application — worth prioritising."
    elif strength >= 55:
        verdict = "Reasonable application — close a few gaps first."
    else:
        verdict = "Weak alignment — upskill or tailor your resume before applying."
    return {
        "strength": strength,
        "parts": parts,
        "factors": factors,
        "verdict": verdict,
        "disclaimer": (
            "Estimated application strength based on profile–job alignment. "
            "This is NOT a prediction of interview or hiring outcomes."
        ),
    }
