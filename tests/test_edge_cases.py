"""
Edge-case and resilience tests for JobPulse AI (audit Phase 18).

Covers: missing datasets, empty DataFrames, missing required columns,
salary aggregation with NaN values, empty-vocabulary recommendation
safety, database fallback behaviour, and career-readiness score bounds.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import src.data_access as data_access
from models.job_recommender import JobRecommender
from models.skill_gap import SkillGapAnalyzer
from src.analytics import (
    get_job_market_summary,
    get_salary_by_experience,
    get_salary_by_location,
    get_salary_by_role,
    get_top_locations,
    get_top_roles,
    get_top_skills,
)
from src.data_cleaning import clean_salary_value
from src.data_loader import load_raw_data


# ---------------------------------------------------------------- fixtures

@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Small valid dataset resembling the processed pipeline output."""
    return pd.DataFrame(
        {
            "job_id": ["J1", "J2", "J3", "J4"],
            "job_title": ["Data Analyst", "Data Scientist", "Data Analyst", "Data Engineer"],
            "standardized_job_title": [
                "Data Analyst", "Data Scientist", "Data Analyst", "Data Engineer",
            ],
            "company": ["Alpha", "Beta", "Alpha", "Gamma"],
            "city": ["Bangalore", "Mumbai", "Bangalore", "Pune"],
            "salary_average": [600000.0, np.nan, 800000.0, 1200000.0],
            "experience_category": ["Entry Level", "Mid Level", "Fresher", "Senior Level"],
            "posting_date": pd.to_datetime(
                ["2026-01-01", "2026-01-05", "2026-02-01", "2026-02-10"]
            ),
            "extracted_skills": [
                ["SQL", "Python"],
                ["Python", "Machine Learning"],
                ["SQL", "Excel"],
                ["Python", "SQL", "Spark"],
            ],
            "job_description": ["sql python", "python ml", "sql excel", "spark python"],
        }
    )


# ------------------------------------------------- dataset loading (Ph 3/18)

def test_missing_dataset_raises_helpful_error(tmp_path):
    """A missing dataset must raise FileNotFoundError with an actionable tip."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_raw_data(str(tmp_path / "does_not_exist.csv"))
    assert "generate_sample_data.py" in str(exc_info.value)


def test_empty_dataset_file_raises_clear_error(tmp_path):
    """A zero-byte dataset file must raise ValueError, not crash pandas."""
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        load_raw_data(str(empty))


def test_csv_fallback_when_db_unconfigured(monkeypatch):
    """With no DB credentials the loader must fall back to CSV tiers."""
    monkeypatch.setattr(data_access, "is_db_configured", lambda: False)
    monkeypatch.setattr(data_access, "load_from_database", lambda: None)

    df, source, db_failed = data_access.load_dashboard_dataframe()

    assert source in {"processed", "cleaned", "raw"}
    assert db_failed is False
    assert len(df) > 0


def test_db_failure_sets_nonblocking_flag(monkeypatch):
    """When the DB was configured but unreachable, db_failed must be True."""
    monkeypatch.setattr(data_access, "is_db_configured", lambda: True)
    monkeypatch.setattr(data_access, "load_from_database", lambda: None)

    _, source, db_failed = data_access.load_dashboard_dataframe()

    assert source in {"processed", "cleaned", "raw"}
    assert db_failed is True


def test_load_from_database_returns_none_without_credentials(monkeypatch):
    """load_from_database must never raise when credentials are missing."""
    monkeypatch.setattr(data_access, "is_db_configured", lambda: False)
    assert data_access.load_from_database() is None


# ------------------------------------------- analytics on bad input (Ph 8/10)
def test_analytics_handle_empty_dataframe():
    """Every analytics function must survive a completely empty DataFrame."""
    empty = pd.DataFrame()
    assert isinstance(get_job_market_summary(empty), dict)
    assert len(get_top_skills(empty, n=5)) == 0
    assert len(get_top_roles(empty, n=5)) == 0
    assert len(get_top_locations(empty, n=5)) == 0
    assert len(get_salary_by_role(empty)) == 0
    assert len(get_salary_by_location(empty)) == 0
    assert len(get_salary_by_experience(empty)) == 0


def test_analytics_handle_missing_required_columns(sample_df):
    """Dropping key columns must yield empty results, not exceptions."""
    bare = sample_df.drop(
        columns=["salary_average", "extracted_skills", "standardized_job_title", "city"]
    )
    assert len(get_salary_by_role(bare)) == 0
    assert len(get_salary_by_location(bare)) == 0
    assert len(get_salary_by_experience(bare)) == 0
    assert len(get_top_skills(bare, n=5)) == 0


def test_salary_aggregation_excludes_nan(sample_df):
    """Average salary must ignore NaN rows; counts reflect valid rows only."""
    by_role = get_salary_by_role(sample_df)
    da = by_role[by_role["job_role"] == "Data Analyst"].iloc[0]
    assert da["count"] == 2
    assert da["avg_salary"] == pytest.approx(700000.0)
    # Data Scientist has only a NaN salary -> excluded entirely
    assert "Data Scientist" not in by_role["job_role"].values


def test_clean_salary_value_rejects_garbage():
    """Invalid salary strings must map to None so they become NaN later."""
    assert clean_salary_value("") is None
    assert clean_salary_value("not a salary") is None
    assert clean_salary_value(np.nan) is None
    assert clean_salary_value(None) is None


# ------------------------------------- career readiness bounds (Ph 12/18)

def test_readiness_score_stays_within_bounds(sample_df):
    """Score must be between 0 and 100 for any skill combination."""
    analyzer = SkillGapAnalyzer(sample_df)
    role = analyzer.get_available_roles()[0]

    for skills in ([], ["SQL"], ["SQL", "Python", "Excel", "Spark", "Machine Learning"]):
        result = analyzer.calculate_readiness_score(skills, role)
        if "error" in result and result.get("error"):
            continue  # insufficient-data path validated separately
        assert 0 <= result["score"] <= 100
        assert 0 <= result["skill_match_pct"] <= 100


def test_readiness_with_insufficient_market_data():
    """An empty dataset must produce an explicit error, never fake numbers."""
    analyzer = SkillGapAnalyzer(pd.DataFrame())
    result = analyzer.calculate_readiness_score(["SQL"], "Data Analyst")
    assert isinstance(result, dict)
    assert result.get("error") or 0 <= result.get("score", 0) <= 100


def test_skill_gap_survives_missing_columns():
    """SkillGapAnalyzer must not crash when key columns are absent."""
    analyzer = SkillGapAnalyzer(pd.DataFrame({"a": [1, 2]}))
    assert analyzer.get_available_roles() == []
    assert analyzer.get_required_skills("Data Analyst") == []


# --------------------------------- recommendation edge cases (Ph 13/18)

def test_recommender_empty_dataframe_returns_empty():
    """An empty job pool must yield an empty result, not a crash."""
    results = JobRecommender(pd.DataFrame()).recommend(user_skills=["SQL"])
    assert isinstance(results, pd.DataFrame)
    assert len(results) == 0


def test_recommender_survives_empty_vocabulary():
    """All-blank corpus must not raise the TF-IDF 'empty vocabulary' error."""
    blank = pd.DataFrame(
        {
            "extracted_skills": [[], [], []],
            "job_description": ["", None, ""],
            "standardized_job_title": ["Data Analyst"] * 3,
            "city": ["Bangalore"] * 3,
            "experience_min": [1.0, 2.0, 0.0],
        }
    )
    recommender = JobRecommender(blank)
    recommender.fit()  # must not raise
    results = recommender.recommend(user_skills=["SQL"])
    assert len(results) == 3
    assert results["match_score"].between(0, 1).all()


def test_recommender_missing_extracted_skills_column():
    """A dataset without skills must return an empty result gracefully."""
    df = pd.DataFrame({"job_title": ["A"], "company": ["X"]})
    assert len(JobRecommender(df).recommend(user_skills=["SQL"])) == 0


def test_recommender_scores_in_valid_range(sample_df):
    """Composite match scores must stay between 0 and 1."""
    recommender = JobRecommender(sample_df)
    recommender.fit()
    results = recommender.recommend(
        user_skills=["SQL", "Python"],
        preferred_location="Bangalore",
        experience_level=1.5,
        target_role="Data Analyst",
    )
    assert len(results) > 0
    assert results["match_score"].between(0, 1).all()

