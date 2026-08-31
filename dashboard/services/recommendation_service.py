"""AI Job Recommendation Engine (FEATURE 3).

Hybrid, explainable recommendations combining:
* Content-based skill similarity (coverage + Jaccard)
* Semantic similarity (TF-IDF lexical proxy, with the same optional
  embedding upgrade used by the match engine)
* Preference matching (target role, location, experience)
* Demand signal (how in-demand the job's skills are across the market)

Each recommendation ships with a plain-language ``why_recommended``.
Weights: ``dashboard.utils.constants.RECOMMENDATION_WEIGHTS``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from dashboard.models.user_profile import UserProfile
from dashboard.utils.constants import RECOMMENDATION_WEIGHTS
from dashboard.utils.scoring import clamp100, clamp01, weighted_score
from dashboard.utils.text_processing import truncate


class HybridRecommender:
    """Fits once on the job corpus, then scores a profile per rerun."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True).copy()
        self._matrix = None
        self._vectorizer: TfidfVectorizer | None = None
        self._skill_freq: dict[str, float] = {}
        self._fit()

    # ------------------------------------------------------------------ fit
    def _fit(self) -> None:
        df = self.df
        if "extracted_skills" not in df.columns or len(df) == 0:
            self._vectorizer = None
            self._matrix = None
            return

        corpus = []
        for _, row in df.iterrows():
            skills = row.get("extracted_skills")
            skills_text = " ".join(map(str, skills)) if isinstance(skills, (list, tuple, set)) else str(skills or "")
            title = str(row.get("job_title", "") or "")
            corpus.append(truncate(f"{title} {skills_text}", 900))

        if any(t.strip() for t in corpus):
            self._vectorizer = TfidfVectorizer(
                max_features=5000, stop_words="english", ngram_range=(1, 2)
            )
            self._matrix = self._vectorizer.fit_transform(corpus)
        else:  # empty vocabulary — rule-based only
            self._vectorizer = None
            self._matrix = None

        freq: dict[str, int] = {}
        for skills in df["extracted_skills"]:
            if isinstance(skills, (list, tuple, set)):
                for s in skills:
                    freq[str(s)] = freq.get(str(s), 0) + 1
        max_count = max(freq.values()) if freq else 1
        self._skill_freq = {s: c / max_count for s, c in freq.items()}

    # ---------------------------------------------------------------- score
    def recommend(
        self,
        profile: UserProfile,
        top_n: int = 10,
        min_score: float = 0.0,
    ) -> pd.DataFrame:
        """
        Rank jobs for a user profile. Returns a DataFrame whose columns are a
        superset of the legacy ``JobRecommender`` output so existing pages
        keep working: job_title, company, location, skills (str),
        match_score (0-1), skill_match, missing_skills (str), salary_average,
        posting_date, experience_category — plus new explainability columns:
        preference_match, semantic_match, demand_score, why_recommended.
        """
        df = self.df
        if len(df) == 0 or "extracted_skills" not in df.columns:
            return pd.DataFrame()

        user_set = {s.lower() for s in profile.skills}
        profile_text = profile.to_text()

        semantic = np.zeros(len(df))
        if self._vectorizer is not None and self._matrix is not None and profile_text.strip():
            profile_vec = self._vectorizer.transform([profile_text])
            semantic = cosine_similarity(profile_vec, self._matrix).flatten()

        results: list[dict] = []
        for idx, row in df.iterrows():
            skills = row.get("extracted_skills")
            job_skills = [str(s) for s in skills] if isinstance(skills, (list, tuple, set)) else []
            job_set = {s.lower() for s in job_skills}
            matched = [s for s in job_skills if s.lower() in user_set]
            missing = [s for s in job_skills if s.lower() not in user_set]

            # --- skill similarity: coverage of the job's demands + Jaccard ---
            coverage = len(matched) / len(job_skills) if job_skills else 0.0
            union = len(job_set | user_set)
            jaccard = len(job_set & user_set) / union if union else 0.0
            skill_score = 0.7 * coverage + 0.3 * jaccard

            # --- preference match ---
            role = str(row.get("standardized_job_title", "") or "")
            location = str(row.get("city", "") or "")
            role_wanted = (profile.target_role or "").strip().lower()
            loc_wanted = (profile.preferred_location or "").strip().lower()
            role_m = 1.0 if role_wanted and role_wanted in role.lower() else (0.4 if not role_wanted else 0.0)
            loc_m = 1.0 if loc_wanted and loc_wanted.lower() in location.lower() else (0.5 if not loc_wanted else 0.0)
            pref_score = 0.5 * role_m + 0.3 * loc_m + 0.2 * 0.7  # exp neutral (coarse data)

            # --- demand: how in-demand are this job's skills market-wide? ---
            demand = (
                float(np.mean([self._skill_freq.get(s, 0.0) for s in job_skills]))
                if job_skills else 0.0
            )

            composite = weighted_score(
                {
                    "skill": skill_score * 100,
                    "semantic": clamp01(float(semantic[idx])) * 100,
                    "preference": pref_score * 100,
                    "demand": demand * 100,
                },
                RECOMMENDATION_WEIGHTS,
            )
            if composite < min_score:
                continue

            why = self._why(profile, matched, missing, role_m, loc_m, demand)
            results.append({
                "job_title": str(row.get("job_title", "") or ""),
                "company": str(row.get("company", "") or ""),
                "location": location,
                "skills": ", ".join(job_skills)[:200],
                "match_score": round(clamp01(composite / 100.0), 3),
                "skill_match": round(clamp01(skill_score), 3),
                "preference_match": round(clamp01(pref_score), 3),
                "semantic_match": round(clamp01(float(semantic[idx])), 3),
                "demand_score": round(clamp01(demand), 3),
                "matched_skills": ", ".join(matched[:8]),
                "missing_skills": ", ".join(missing[:5]),
                "why_recommended": why,
                "salary_average": row.get("salary_average", np.nan),
                "posting_date": row.get("posting_date", ""),
                "experience_category": row.get("experience_category", ""),
            })

        out = pd.DataFrame(results)
        if len(out) == 0:
            return out
        return out.sort_values("match_score", ascending=False).head(top_n)

    @staticmethod
    def _why(profile: UserProfile, matched, missing, role_m, loc_m, demand) -> str:
        """Plain-language explanation assembled from the top signals."""
        reasons: list[str] = []
        if matched:
            reasons.append(
                f"your profile covers {len(matched)} of the job's skills "
                f"({', '.join(matched[:4])})"
            )
        if role_m == 1.0 and profile.target_role:
            reasons.append(f"it matches your target role ({profile.target_role})")
        if loc_m == 1.0 and profile.preferred_location:
            reasons.append(f"it is located in your preferred city ({profile.preferred_location})")
        if demand >= 0.6:
            reasons.append("the skills it requires are highly in-demand across the market")
        if not reasons:
            if missing:
                reasons.append(f"it could stretch you: missing {', '.join(missing[:3])}")
            else:
                reasons.append("it broadly aligns with your profile")
        return "Recommended because " + "; ".join(reasons) + "."
