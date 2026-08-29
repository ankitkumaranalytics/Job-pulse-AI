"""
Skill gap analysis module for JobPulse AI.

Calculates a career readiness score based on:
- User's current skills
- Target job role
- Market demand for skills (from dataset)
"""
from __future__ import annotations

import logging
from typing import Optional
from collections import Counter

import pandas as pd
import numpy as np

from src.config import logger


class SkillGapAnalyzer:
    """
    Analyze the skill gap between a user's current skills and
    the skills demanded in the job market for a target role.

    Parameters
    ----------
    df : pd.DataFrame
        Processed job data with 'extracted_skills' and
        'standardized_job_title' columns.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self._skills_by_role_cache: Optional[dict] = None

    def _get_skills_by_role(self, role: str) -> Counter:
        """Get skill frequency for a specific role."""
        if "standardized_job_title" not in self.df.columns:
            return Counter()
        role_df = self.df[self.df["standardized_job_title"] == role]
        if len(role_df) == 0:
            return Counter()
        all_skills = []
        for skills in role_df.get("extracted_skills", []):
            if isinstance(skills, (list, set)):
                all_skills.extend(skills)
            elif isinstance(skills, str) and skills.strip():
                all_skills.extend(s.strip() for s in skills.split(","))
        return Counter(all_skills)

    def get_required_skills(self, role: str, top_n: int = 15) -> list:
        """
        Return the top skills for a role, classified as
        Critical / Important / Optional.

        - Critical: appears in >= 50% of jobs for this role
        - Important: 25-50%
        - Optional: < 25%
        """
        skill_counts = self._get_skills_by_role(role)
        role_df = self.df[self.df["standardized_job_title"] == role]
        total_jobs = len(role_df)
        if total_jobs == 0:
            return []

        result = []
        for skill, count in skill_counts.most_common(top_n):
            pct = count / total_jobs
            if pct >= 0.50:
                level = "Critical"
            elif pct >= 0.25:
                level = "Important"
            else:
                level = "Optional"
            result.append((skill, count, level))
        return result


    def calculate_readiness_score(self, user_skills: list[str], target_role: str) -> dict:
        """
        Calculate a career readiness score for a user targeting a specific role.

        Score = (matched_critical*3 + matched_important*2 + matched_optional*1)
                / (total_critical*3 + total_important*2 + total_optional*1) * 100
        """
        required = self.get_required_skills(target_role, top_n=20)
        if len(required) == 0:
            return {
                "score": 0,
                "error": f"No data for role '{target_role}'. Try a different role.",
                "matched_skills": [],
                "missing_skills": [],
                "recommendations": [],
                "skill_match_pct": 0,
            }

        user_skills_lower = set(s.lower().strip() for s in user_skills)
        critical_skills = [s for s, _, lvl in required if lvl == "Critical"]
        important_skills = [s for s, _, lvl in required if lvl == "Important"]
        optional_skills = [s for s, _, lvl in required if lvl == "Optional"]

        matched_critical = [s for s in critical_skills if s.lower() in user_skills_lower]
        matched_important = [s for s in important_skills if s.lower() in user_skills_lower]
        matched_optional = [s for s in optional_skills if s.lower() in user_skills_lower]

        missing_critical = [s for s in critical_skills if s.lower() not in user_skills_lower]
        missing_important = [s for s in important_skills if s.lower() not in user_skills_lower]
        missing_optional = [s for s in optional_skills if s.lower() not in user_skills_lower]

        max_score = len(critical_skills) * 3 + len(important_skills) * 2 + len(optional_skills)
        earned = len(matched_critical) * 3 + len(matched_important) * 2 + len(matched_optional)
        score = round((earned / max_score * 100), 1) if max_score > 0 else 0

        total_required = len(critical_skills) + len(important_skills) + len(optional_skills)
        total_matched = len(matched_critical) + len(matched_important) + len(matched_optional)
        skill_match_pct = round((total_matched / total_required * 100), 1) if total_required > 0 else 0

        recommendations = missing_critical + missing_important + missing_optional

        return {
            "score": score,
            "skill_match_pct": skill_match_pct,
            "matched_skills": matched_critical + matched_important + matched_optional,
            "missing_skills": {
                "critical": missing_critical,
                "important": missing_important,
                "optional": missing_optional,
            },
            "recommendations": recommendations,
            "total_required": total_required,
            "total_matched": total_matched,
            "skill_breakdown": {
                "critical": {"required": len(critical_skills), "matched": len(matched_critical)},
                "important": {"required": len(important_skills), "matched": len(matched_important)},
                "optional": {"required": len(optional_skills), "matched": len(matched_optional)},
            },
        }

    def get_available_roles(self) -> list[str]:
        """Return list of job roles available in the dataset."""
        if "standardized_job_title" not in self.df.columns:
            return []
        return sorted(self.df["standardized_job_title"].unique().tolist())

    def get_missing_critical_skills(self, user_skills: list[str], target_role: str) -> list[str]:
        """Return only missing critical skills."""
        result = self.calculate_readiness_score(user_skills, target_role)
        return result["missing_skills"]["critical"]

    def get_learning_recommendations(self, user_skills: list[str], target_role: str, top_n: int = 5) -> list[str]:
        """Return top learning recommendations."""
        result = self.calculate_readiness_score(user_skills, target_role)
        return result["recommendations"][:top_n]
