"""Semantic Job Search service (FEATURE 4).

Parses a natural-language query into structured filters (role, skills,
location, experience, job type), then ranks the corpus with a TF-IDF
lexical-semantic engine. A keyword-AND fallback runs when the query has
no usable signal, so search never breaks.
"""
from __future__ import annotations

import re

import pandas as pd

from dashboard.utils.scoring import clamp100, clamp01
from dashboard.utils.text_processing import truncate
from dashboard.utils.validation import ServiceError, validate_query

_EXPERIENCE_PATTERNS = {
    "Fresher": r"fresher|entry[- ]level|graduate|no experience|beginner|student",
    "Entry Level": r"entry level|1[- ]2 years|junior",
    "Mid Level": r"mid[- ]level|3[- ]5 years|experienced",
    "Senior Level": r"senior|lead|principal|5\+ years|7\+ years",
}
_JOB_TYPES = {
    "Internship": r"intern|trainee",
    "Full-time": r"full[- ]time|permanent",
    "Contract": r"contract|freelance|c2h",
}
_SKILL_SPLIT_RE = re.compile(r"[,;/|]+|\band\b", re.IGNORECASE)


def _unique(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns or len(df) == 0:
        return []
    vals = df[column].dropna().astype(str).str.strip()
    vals = vals[vals != ""]
    return sorted(vals.unique().tolist(), key=len, reverse=True)


def parse_query(query: str, df: pd.DataFrame) -> dict:
    """
    Extract structured intent from a natural-language query.

    Returns {role, location, experience_level, job_type, skills, raw}.
    Every field degrades to None/[] when the query does not express it.
    """
    cleaned = validate_query(query)
    lowered = cleaned.lower()

    from src.skill_extractor import extract_skills_from_text

    role = None
    for candidate in _unique(df, "standardized_job_title"):
        if candidate.lower() in lowered:
            role = candidate
            break

    location = None
    for candidate in _unique(df, "city"):
        if re.search(rf"\b{re.escape(candidate.lower())}\b", lowered):
            location = candidate
            break

    experience_level = None
    for level, pattern in _EXPERIENCE_PATTERNS.items():
        if re.search(pattern, lowered):
            experience_level = level
            break

    job_type = None
    for jt, pattern in _JOB_TYPES.items():
        if re.search(pattern, lowered):
            job_type = jt
            break

    skills = extract_skills_from_text(cleaned)
    if not skills:
        # Free-text skill mentions separated by commas, 'and', slashes.
        raw_tokens = [t.strip(" .") for t in _SKILL_SPLIT_RE.split(cleaned) if t.strip(" .")]
        known = {s.lower() for s in _unique_from_skills_column(df)}
        skills = [t.title() for t in raw_tokens if t.lower() in known][:8]

    return {
        "raw": cleaned,
        "role": role,
        "location": location,
        "experience_level": experience_level,
        "job_type": job_type,
        "skills": skills,
    }


def _unique_from_skills_column(df: pd.DataFrame) -> list[str]:
    """Flatten the dataset's skill vocabulary for free-text matching."""
    from src.skill_extractor import get_all_skills

    return get_all_skills()

def _job_document(row: pd.Series) -> str:
    """Flatten a job row into the search corpus document."""
    skills = row.get("extracted_skills")
    skills_text = (
        " ".join(str(s) for s in skills)
        if isinstance(skills, (list, tuple, set)) else str(skills or "")
    )
    return truncate(
        " ".join([
            str(row.get("job_title", "") or ""),
            str(row.get("company", "") or ""),
            str(row.get("city", "") or ""),
            str(row.get("industry", "") or ""),
            skills_text,
        ]),
        600,
    )


def rank_jobs(df: pd.DataFrame, query: str, top_n: int = 20) -> pd.DataFrame:
    """
    Rank the dataset against a natural-language query.

    Pipeline: parse intent → apply structured boosts → TF-IDF semantic
    ranking. When the query yields no skill/role signal, a keyword-AND
    fallback keeps results relevant. Adds ``_search_score`` (0-100) and
    ``_matched_on`` reason columns without mutating the source frame.
    """
    from src.skill_extractor import extract_skills_from_text  # noqa: F401 (warm cache)

    intent = parse_query(query, df)
    if len(df) == 0:
        return df.head(0)

    corpus = df.apply(_job_document, axis=1).tolist()
    scores = [0.0] * len(df)
    method = "keyword"

    if any(t.strip() for t in corpus):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vectorizer = TfidfVectorizer(
                max_features=5000, stop_words="english", ngram_range=(1, 2)
            )
            matrix = vectorizer.fit_transform(corpus)
            query_vec = vectorizer.transform([intent["raw"]])
            raw = cosine_similarity(query_vec, matrix).flatten()
            scores = [clamp100(clamp01(float(s)) * 130) for s in raw]
            method = "semantic"
        except (ValueError, ImportError):
            scores = [0.0] * len(df)

    results = df.copy()
    results["_search_score"] = scores
    reasons: list[str] = []

    # Structured boosts for explicit intent (role/location/exp/type/skills)
    def boost(row: pd.Series, score: float) -> float:
        b = 0.0
        if intent["role"] and str(row.get("standardized_job_title", "")) == intent["role"]:
            b += 25.0
        if intent["location"] and str(row.get("city", "")) == intent["location"]:
            b += 20.0
        if intent["experience_level"] and str(
            row.get("experience_category", "")
        ) == intent["experience_level"]:
            b += 15.0
        if intent["job_type"] == "Internship" and "intern" in str(
            row.get("job_title", "")
        ).lower():
            b += 10.0
        skills = row.get("extracted_skills")
        skill_set = (
            {str(s).lower() for s in skills}
            if isinstance(skills, (list, tuple, set)) else set()
        )
        wanted = [s.lower() for s in intent["skills"]]
        if wanted:
            hit = sum(1 for s in wanted if s in skill_set)
            b += 30.0 * hit / len(wanted)
        return score + b

    if method == "semantic" or intent["skills"] or intent["role"] or intent["location"]:
        results["_search_score"] = [
            clamp100(boost(row, s))
            for row, s in zip(results.to_dict("records"), results["_search_score"])
        ]
        reasons = [f"{method} ranking + intent boosts"]

    # Keyword fallback: pure AND-match on skill tokens when scoring is weak
    if intent["skills"] and float(results["_search_score"].max() or 0) < 40:
        def skill_hit(row) -> bool:
            skills = row.get("extracted_skills")
            skill_set = (
                {str(s).lower() for s in skills}
                if isinstance(skills, (list, tuple, set)) else set()
            )
            return all(s.lower() in skill_set for s in intent["skills"])

        mask = results.apply(skill_hit, axis=1)
        if mask.any():
            results = results[mask]
            results["_search_score"] = 60.0
            reasons = ["keyword AND-match fallback"]

    results["_matched_on"] = "; ".join(
        ([f"role: {intent['role']}"] if intent["role"] else [])
        + ([f"location: {intent['location']}"] if intent["location"] else [])
        + ([f"skills: {', '.join(intent['skills'][:5])}"] if intent["skills"] else [])
        + ([f"level: {intent['experience_level']}"] if intent["experience_level"] else [])
        + ([f"type: {intent['job_type']}"] if intent["job_type"] else [])
        or reasons
        or ["query text similarity"]
    )
    return results.sort_values("_search_score", ascending=False).head(top_n)


def keyword_search(df: pd.DataFrame, tokens: list[str], top_n: int = 20) -> pd.DataFrame:
    """Traditional keyword-AND search fallback (kept for compatibility)."""
    if not tokens or len(df) == 0:
        return df.head(0)
    token_set = {t.lower() for t in tokens}

    def hit(row) -> bool:
        skills = row.get("extracted_skills")
        skill_set = (
            {str(s).lower() for s in skills}
            if isinstance(skills, (list, tuple, set)) else set()
        )
        title = str(row.get("job_title", "")).lower()
        return any(t in skill_set or t in title for t in token_set)

    mask = df.apply(hit, axis=1)
    out = df[mask].copy()
    out["_search_score"] = 50.0
    out["_matched_on"] = f"keyword match: {', '.join(tokens[:5])}"
    return out.head(top_n)
