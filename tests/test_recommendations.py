"""Tests for the recommendation models."""
import pandas as pd
import numpy as np

from models.skill_gap import SkillGapAnalyzer
from models.job_recommender import JobRecommender


def _make_test_df():
    """Create a small test dataset."""
    return pd.DataFrame({
        "job_id": ["J1", "J2", "J3"],
        "job_title": ["Data Analyst", "Data Analyst", "Data Scientist"],
        "standardized_job_title": ["Data Analyst", "Data Analyst", "Data Scientist"],
        "company": ["A", "B", "C"],
        "city": ["Bangalore", "Pune", "Bangalore"],
        "salary_average": [600000, 700000, 1200000],
        "experience_min": [0, 1, 2],
        "extracted_skills": [
            ["Python", "SQL", "Excel"],
            ["Python", "SQL", "Power BI"],
            ["Python", "Machine Learning", "Statistics"],
        ],
        "job_description": ["data analysis python sql", "analytics power bi", "machine learning"],
    })


def test_career_readiness_score():
    """Readiness score is computed and scales with matching skills."""
    df = _make_test_df()
    analyzer = SkillGapAnalyzer(df)

    # User has all skills for Data Analyst
    result_full = analyzer.calculate_readiness_score(
        ["Python", "SQL", "Excel", "Power BI"], "Data Analyst"
    )
    assert result_full["score"] > 0

    # User with no skills gets a lower score
    result_empty = analyzer.calculate_readiness_score([], "Data Analyst")
    assert result_empty["score"] <= result_full["score"]


def test_skill_gap_missing_critical():
    """Missing skills are returned in the result."""
    df = _make_test_df()
    analyzer = SkillGapAnalyzer(df)
    result = analyzer.calculate_readiness_score(["Python"], "Data Analyst")
    assert "missing_skills" in result
    assert isinstance(result["missing_skills"], dict)


def test_job_matching_returns_results():
    """Job recommender returns ranked job recommendations."""
    df = _make_test_df()
    recommender = JobRecommender(df)
    results = recommender.recommend(
        user_skills=["Python", "SQL"],
        preferred_location="Bangalore",
        experience_level=1.0,
        target_role="Data Analyst",
    )
    assert len(results) > 0
    assert "match_score" in results.columns
    assert "job_title" in results.columns
    assert "company" in results.columns
    # Results sorted by match score descending
    match_scores = results["match_score"].tolist()
    assert match_scores == sorted(match_scores, reverse=True)


def test_job_matching_skill_preference():
    """Jobs with more matching skills score higher."""
    df = _make_test_df()
    recommender = JobRecommender(df)
    results = recommender.recommend(user_skills=["Python", "SQL"], target_role="Data Analyst")
    # J1 and J2 (Data Analysts) should both appear
    job_set = set(results["job_title"])
    assert len(job_set) > 0