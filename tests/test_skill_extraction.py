"""Tests for the skill extraction engine."""
import pandas as pd

from src.skill_extractor import (
    extract_skills_from_text,
    extract_skills,
    SKILL_DICTIONARY,
    SKILL_CATEGORIES,
)


def test_skill_extraction_from_text():
    """Skills are extracted from free text."""
    text = "We require Python, SQL, and experience with Power BI."
    skills = extract_skills_from_text(text)
    assert "Python" in skills
    assert "SQL" in skills
    assert "Power BI" in skills


def test_case_insensitive_matching():
    """Matching is case-insensitive."""
    skills = extract_skills_from_text("python PYTHON PyThOn")
    assert skills == ["Python"]


def test_skill_aliases():
    """Aliases map to canonical skill names."""
    # Postgres -> PostgreSQL
    skills = extract_skills_from_text("Experience with Postgres and MS Excel")
    assert "PostgreSQL" in skills
    assert "Excel" in skills

    # PowerBI (no space) -> Power BI
    skills = extract_skills_from_text("pandas numpy matplotlib PowerBI")
    assert "Power BI" in skills
    assert "Pandas" in skills
    assert "NumPy" in skills


def test_skill_dictionary_categories():
    """Every skill in the dictionary has a category."""
    for skill in SKILL_DICTIONARY:
        assert skill in SKILL_CATEGORIES, f"Missing category for {skill}"


def test_extract_skills_dataframe():
    """extract_skills adds an extracted_skills list column."""
    df = pd.DataFrame({
        "job_id": [1, 2],
        "job_title": ["Data Analyst", "Data Scientist"],
        "skills": ["Python, SQL", "Python, TensorFlow"],
        "job_description": [
            "We need python and sql skills.",
            "TensorFlow and python required.",
        ],
    })
    result = extract_skills(df)
    assert "extracted_skills" in result.columns
    assert "skills_count" in result.columns
    # Skills should be deduplicated (python appears twice for job 1).
    # Look up rows by job_id, since extract_skills preserves the
    # original DataFrame index.
    row1 = result.loc[result["job_id"] == 1, "extracted_skills"].iloc[0]
    row2 = result.loc[result["job_id"] == 2, "extracted_skills"].iloc[0]
    assert row1 == ["Python", "SQL"]
    assert row2 == ["Python", "TensorFlow"]


def test_extract_skills_no_duplicates():
    """Extracted skills have no duplicates."""
    df = pd.DataFrame({
        "job_id": [1],
        "job_title": ["Data Analyst"],
        "skills": ["Python, python, PYTHON"],
        "job_description": ["python"],
    })
    result = extract_skills(df)
    skills = result.loc[result["job_id"] == 1, "extracted_skills"].iloc[0]
    assert skills == ["Python"]