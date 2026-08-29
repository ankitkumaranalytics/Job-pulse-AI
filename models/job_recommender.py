"""
Job recommendation engine for JobPulse AI.

Uses TF-IDF + Cosine Similarity to match user profile against
job postings. Considers:
- Skill match (TF-IDF on skills + description)
- Location match
- Role match
- Experience match
"""
from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Optional, List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import logger
from src.data_cleaning import _find_column


class JobRecommender:
    """
    Recommendation system that matches a user profile to job postings
    using TF-IDF and cosine similarity.

    Parameters
    ----------
    df : pd.DataFrame
        Processed job data with 'extracted_skills', 'standardized_job_title',
        'city', 'experience_min', 'experience_max' columns.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._tfidf: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._is_fitted = False

    def _build_skill_text(self, skills) -> str:
        """Convert a skills list into a space-separated string."""
        if isinstance(skills, (list, set)):
            return " ".join(str(s) for s in skills)
        if pd.isna(skills):
            return ""
        return str(skills)

    def _build_combined_text(self, row) -> str:
        """Build a combined text field from skills + job description."""
        skills_text = self._build_skill_text(row.get("extracted_skills", []))
        desc = str(row.get("job_description", "")) if pd.notna(row.get("job_description")) else ""
        # Normalize and combine
        return " ".join([skills_text, desc[:500]])  # Limit desc length

    def fit(self) -> None:
        """Fit the TF-IDF vectorizer on the job data."""
        if "extracted_skills" not in self.df.columns:
            raise ValueError("DataFrame must have 'extracted_skills' column")

        if len(self.df) == 0:
            logger.warning("JobRecommender.fit called with an empty DataFrame")
            self._is_fitted = True
            return

        combined_texts = self.df.apply(self._build_combined_text, axis=1).tolist()

        # Guard against empty vocabulary: if every description/skill string is
        # blank, TfidfVectorizer.fit_transform would raise a confusing
        # ValueError. Disable the TF-IDF component instead and let
        # recommend() fall back to the rule-based score components only.
        if not any(t.strip() for t in combined_texts):
            logger.warning(
                "TF-IDF disabled: job corpus contains no usable text "
                "(all descriptions/skills empty). Rule-based matching only."
            )
            self._tfidf = None
            self._tfidf_matrix = None
        else:
            self._tfidf = TfidfVectorizer(
                max_features=5000,
                stop_words="english",
                ngram_range=(1, 2),
                lowercase=True,
            )
            self._tfidf_matrix = self._tfidf.fit_transform(combined_texts)

        # Pre-extract per-row values once so recommend() avoids slow iloc calls
        self._job_skills = [
            s if isinstance(s, (list, set)) else []
            for s in self.df["extracted_skills"].tolist()
        ]
        self._job_locations = (
            self.df["city"].fillna("").astype(str).tolist()
            if "city" in self.df.columns
            else self.df["location"].fillna("").astype(str).tolist()
            if "location" in self.df.columns
            else [""] * len(self.df)
        )
        self._job_roles = (
            self.df["standardized_job_title"].fillna("").astype(str).tolist()
            if "standardized_job_title" in self.df.columns
            else [""] * len(self.df)
        )
        self._job_exp_min = (
            pd.to_numeric(self.df["experience_min"], errors="coerce").tolist()
            if "experience_min" in self.df.columns
            else [None] * len(self.df)
        )
        self._is_fitted = True
        logger.info("TF-IDF model fitted on %d documents", len(combined_texts))

    def _compute_skill_match(self, user_skills: List[str], job_skills) -> float:
        """Compute the Jaccard similarity of skills between user and job."""
        if isinstance(job_skills, (list, set)):
            job_set = set(str(s).lower().strip() for s in job_skills)
        else:
            job_set = set()
        user_set = set(s.lower().strip() for s in user_skills)
        if not job_set:
            return 0.0
        intersection = user_set & job_set
        union = user_set | job_set
        return len(intersection) / len(union) if union else 0.0

    def _compute_location_match(self, user_location: str, job_location: str) -> float:
        """Compute location match score."""
        if not user_location or not job_location:
            return 0.5  # Neutral if unspecified
        user_loc = user_location.lower().strip()
        job_loc = str(job_location).lower().strip()
        if user_loc == job_loc:
            return 1.0
        if user_loc in job_loc or job_loc in user_loc:
            return 0.8
        return 0.0

    def _compute_role_match(self, target_role: str, job_role: str) -> float:
        """Compute role match score."""
        if not target_role:
            return 1.0  # No preference
        if target_role.lower().strip() == str(job_role).lower().strip():
            return 1.0
        return 0.0

    def _compute_experience_match(self, user_exp: float, job_exp_min, job_exp_max) -> float:
        """Compute experience match score."""
        if user_exp is None or pd.isna(user_exp):
            return 0.5
        if job_exp_min is None or pd.isna(job_exp_min):
            return 0.5
        if user_exp >= job_exp_min:
            return 1.0
        if user_exp >= job_exp_min - 1:
            return 0.7
        return 0.3

    def recommend(self, user_skills: List[str], preferred_location: str = "",
                  experience_level: float = 0, target_role: str = "") -> pd.DataFrame:
        """
        Recommend jobs based on user profile.

        Parameters
        ----------
        user_skills : list[str]
            Skills the user currently has.
        preferred_location : str
            Preferred work location.
        experience_level : float
            User's years of experience.
        target_role : str
            Target job role.

        Returns
        -------
        pd.DataFrame
            Top 10 recommended jobs, sorted by match score.
        """
        if len(self.df) == 0 or "extracted_skills" not in self.df.columns:
            return pd.DataFrame()

        if not self._is_fitted:
            self.fit()

        # Build user skill text for TF-IDF similarity.
        # If the vectorizer was disabled (empty corpus), fall back to a zero
        # similarity vector so the rule-based components still produce results.
        tfidf_sim = np.zeros(len(self.df))
        if self._tfidf is not None and self._tfidf_matrix is not None:
            user_text = " ".join(user_skills)
            user_vector = self._tfidf.transform([user_text])
            tfidf_sim = cosine_similarity(user_vector, self._tfidf_matrix).flatten()

        results = []
        for idx in range(len(self.df)):
            job_skills = self._job_skills[idx]
            job_location = self._job_locations[idx]
            job_role = self._job_roles[idx]
            job_exp_min = self._job_exp_min[idx]

            skill_match = self._compute_skill_match(user_skills, job_skills)
            location_match = self._compute_location_match(preferred_location, job_location)
            role_match = self._compute_role_match(target_role, job_role)
            exp_match = self._compute_experience_match(experience_level, job_exp_min, None)

            # Weighted composite score
            composite = (
                tfidf_sim[idx] * 0.30
                + skill_match * 0.30
                + location_match * 0.15
                + role_match * 0.15
                + exp_match * 0.10
            )

            missing_skills = []
            user_lower = set(s.lower().strip() for s in user_skills)
            missing_skills = [s for s in job_skills if str(s).lower().strip() not in user_lower]

            row = self.df.iloc[idx]
            results.append({
                "job_title": row.get("job_title", ""),
                "company": row.get("company", ""),
                "location": job_location,
                "skills": ", ".join(str(s) for s in job_skills)[:200],
                "match_score": round(composite, 3),
                "skill_match": round(skill_match, 3),
                "missing_skills": ", ".join(str(s) for s in missing_skills[:5]),
                "salary_average": row.get("salary_average", np.nan),
            })

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values("match_score", ascending=False).head(10)
        return results_df

