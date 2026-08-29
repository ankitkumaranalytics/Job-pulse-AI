"""Tests for the data cleaning module."""
import pandas as pd
import numpy as np

from src.data_cleaning import (
    standardize_job_title,
    standardize_location,
    clean_salary_value,
    parse_experience,
    remove_duplicates,
    clean_data,
)


def test_standardize_job_title_common():
    """Common job titles map to canonical categories."""
    assert standardize_job_title("Data Analyst") == "Data Analyst"
    assert standardize_job_title("Junior Data Analyst") == "Data Analyst"
    assert standardize_job_title("Data Analyst I") == "Data Analyst"
    assert standardize_job_title("Business Analyst") == "Business Analyst"
    assert standardize_job_title("Data Scientist") == "Data Scientist"
    assert standardize_job_title("Data Engineer") == "Data Engineer"
    assert standardize_job_title("Machine Learning Engineer") == "Machine Learning Engineer"


def test_standardize_job_title_unknown():
    """Unknown titles map to 'Other'."""
    assert standardize_job_title("Cube Manager") == "Other"
    assert standardize_job_title("") == "Other"
    assert standardize_job_title(np.nan) == "Other"


def test_standardize_location():
    """Common location variations map to canonical cities."""
    assert standardize_location("Bengaluru") == "Bangalore"
    assert standardize_location("Gurugram") == "Gurgaon"
    assert standardize_location("New Delhi") == "Delhi"
    assert standardize_location("Mumbai Metropolitan Region") == "Mumbai"


def test_clean_salary_value():
    """Salary strings parse correctly."""
    assert clean_salary_value("5 LPA") == 500000
    assert clean_salary_value("10 lakhs") == 1000000
    assert clean_salary_value("50K") == 50000
    assert clean_salary_value("500000") == 500000
    assert clean_salary_value(np.nan) is None
    assert clean_salary_value("") is None


def test_parse_experience():
    """Experience text parses into (min, max)."""
    assert parse_experience("0-2 years") == (0.0, 2.0)
    assert parse_experience("1 to 3 years") == (1.0, 3.0)
    assert parse_experience("Fresher") == (0.0, 0.0)
    assert parse_experience("5+ years") == (5.0, None)
    assert parse_experience("2 years") == (2.0, 2.0)


def test_remove_duplicates_exact():
    """Exact duplicate rows are removed."""
    df = pd.DataFrame({
        "job_title": ["Data Analyst", "Data Analyst", "Data Scientist"],
        "company": ["A", "A", "B"],
        "location": ["Bangalore", "Bangalore", "Pune"],
        "posting_date": ["2024-01-01", "2024-01-01", "2024-01-02"],
    })
    cleaned = remove_duplicates(df)
    assert len(cleaned) == 2


def test_clean_data_missing_values():
    """Missing values are handled with defaults."""
    df = pd.DataFrame({
        "job_id": [1, 2],
        "job_title": ["Data Analyst", "Data Scientist"],
        "company": ["A", "B"],
        "location": ["Bengaluru", "Pune"],
        "industry": [np.nan, "IT"],
        "experience": ["0-2 years", "3 years"],
        "salary": ["5 LPA", "12 LPA"],
    })
    cleaned = clean_data(df)
    # industry NaN -> Other
    assert cleaned.loc[0, "industry"] == "Other"
    # Location standardized
    assert cleaned.loc[0, "normalized_location"] == "Bangalore"
    # Salary parsed
    assert cleaned.loc[0, "salary_min"] == 500000


def test_clean_data_missing_columns_graceful():
    """Clean data works even when many optional columns are absent."""
    df = pd.DataFrame({
        "job_title": ["Data Analyst"],
        "company": ["A"],
    })
    cleaned = clean_data(df)
    assert "standardized_job_title" in cleaned.columns
    assert cleaned.loc[0, "standardized_job_title"] == "Data Analyst"
    assert "job_id" in cleaned.columns