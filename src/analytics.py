"""
Python analytics module for JobPulse AI.

Provides reusable functions for all dashboard pages. Each function
accepts a processed DataFrame and returns structured results that
can be rendered as charts, tables, or KPI cards.
"""
from __future__ import annotations

import logging
from typing import Optional
from collections import Counter
from itertools import combinations

import pandas as pd
import numpy as np

from .config import logger


def get_job_market_summary(df: pd.DataFrame) -> dict:
    """Return a high-level market summary."""
    return {
        "total_jobs": len(df),
        "total_companies": df["company"].nunique() if "company" in df.columns else 0,
        "total_locations": df["city"].nunique() if "city" in df.columns else 0,
        "avg_salary": float(df["salary_average"].mean()) if "salary_average" in df.columns and df["salary_average"].notna().any() else 0,
        "total_skills": len(_flatten_skills(df)),
    }


def get_top_roles(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return top job roles by count."""
    role_col = "standardized_job_title"
    if role_col not in df.columns:
        return pd.DataFrame()
    counts = df[role_col].value_counts().head(n).reset_index()
    counts.columns = ["job_role", "count"]
    return counts


def get_top_skills(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Return top skills by frequency across all jobs."""
    all_skills = _flatten_skills(df)
    skill_counts = Counter(all_skills)
    top = skill_counts.most_common(n)
    return pd.DataFrame(top, columns=["skill", "count"])


def get_top_locations(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return top locations by job count."""
    loc_col = "city"
    if loc_col not in df.columns:
        return pd.DataFrame()
    counts = df[loc_col].value_counts().head(n).reset_index()
    counts.columns = ["location", "count"]
    return counts


def get_top_companies(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return top hiring companies by job count."""
    comp_col = "company"
    if comp_col not in df.columns:
        return pd.DataFrame()
    counts = df[comp_col].value_counts().head(n).reset_index()
    counts.columns = ["company", "count"]
    return counts


def get_salary_analysis(df: pd.DataFrame) -> dict:
    """Return salary statistics."""
    if "salary_average" not in df.columns:
        return {"error": "No salary data available"}

    salaries = df["salary_average"].dropna()
    if len(salaries) == 0:
        return {"error": "No valid salary data"}

    return {
        "count": int(len(salaries)),
        "mean": float(salaries.mean()),
        "median": float(salaries.median()),
        "min": float(salaries.min()),
        "max": float(salaries.max()),
        "std": float(salaries.std()) if len(salaries) > 1 else 0,
        "q1": float(salaries.quantile(0.25)),
        "q3": float(salaries.quantile(0.75)),
    }


def get_salary_by_role(df: pd.DataFrame) -> pd.DataFrame:
    """Return average salary by job role."""
    if "salary_average" not in df.columns or "standardized_job_title" not in df.columns:
        return pd.DataFrame()
    valid = df.dropna(subset=["salary_average"])
    if len(valid) == 0:
        return pd.DataFrame()
    grouped = valid.groupby("standardized_job_title")["salary_average"].agg(
        ["mean", "min", "max", "count"]
    ).reset_index()
    grouped.columns = ["job_role", "avg_salary", "min_salary", "max_salary", "count"]
    grouped = grouped.sort_values("avg_salary", ascending=False)
    return grouped


def get_salary_by_location(df: pd.DataFrame) -> pd.DataFrame:
    """Return average salary by location."""
    if "salary_average" not in df.columns or "city" not in df.columns:
        return pd.DataFrame()
    valid = df.dropna(subset=["salary_average"])
    if len(valid) == 0:
        return pd.DataFrame()
    grouped = valid.groupby("city")["salary_average"].agg(
        ["mean", "count"]
    ).reset_index()
    grouped.columns = ["location", "avg_salary", "count"]
    grouped = grouped[grouped["count"] >= 3].sort_values("avg_salary", ascending=False)
    return grouped.round(2)


def get_salary_by_experience(df: pd.DataFrame) -> pd.DataFrame:
    """Return average salary by experience category."""
    if "salary_average" not in df.columns or "experience_category" not in df.columns:
        return pd.DataFrame()
    valid = df.dropna(subset=["salary_average"])
    if len(valid) == 0:
        return pd.DataFrame()
    grouped = valid.groupby("experience_category")["salary_average"].agg(
        ["mean", "min", "max", "count"]
    ).reset_index()
    grouped.columns = ["experience", "avg_salary", "min_salary", "max_salary", "count"]
    return grouped.sort_values("avg_salary", ascending=False)


def get_experience_analysis(df: pd.DataFrame) -> dict:
    """Return experience distribution."""
    if "experience_category" not in df.columns:
        return {"error": "No experience data"}
    counts = df["experience_category"].value_counts().to_dict()
    return {"distribution": counts, "total": len(df)}


def get_job_trend_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Return monthly job posting trends."""
    if "posting_date" not in df.columns:
        return pd.DataFrame()
    dates = pd.to_datetime(df["posting_date"], errors="coerce")
    valid = df[dates.notna()].copy()
    valid["posting_date"] = dates[dates.notna()]
    if len(valid) == 0:
        return pd.DataFrame()
    valid["year_month"] = valid["posting_date"].dt.to_period("M")
    trend = valid.groupby("year_month").size().reset_index()
    trend.columns = ["year_month", "count"]
    trend = trend.sort_values("year_month")
    trend["year_month"] = trend["year_month"].astype(str)
    return trend


def get_skill_combinations(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return most frequently requested skill combinations (pairs)."""
    all_skills = _flatten_skills(df)
    # Get skill lists per job
    combo_counter = Counter()
    for skills_list in df["extracted_skills"]:
        if isinstance(skills_list, (list, set)):
            skills = sorted(skills_list)
            for combo in combinations(skills, 2):
                combo_counter[combo] += 1
    top = combo_counter.most_common(n)
    return pd.DataFrame(
        [{"skill_1": c[0][0], "skill_2": c[0][1], "count": c[1]} for c in top]
    )


def get_role_comparison(df: pd.DataFrame, role1: str, role2: str) -> dict:
    """Compare two job roles by skills."""
    role_col = "standardized_job_title"
    if role_col not in df.columns or "extracted_skills" not in df.columns:
        return {"error": "Required columns missing"}

    df1 = df[df[role_col] == role1]
    df2 = df[df[role_col] == role2]

    skills1 = set(_flatten_skills(df1))
    skills2 = set(_flatten_skills(df2))

    return {
        "role1": role1,
        "role2": role2,
        "role1_count": len(df1),
        "role2_count": len(df2),
        "common_skills": sorted(skills1 & skills2),
        "unique_to_role1": sorted(skills1 - skills2),
        "unique_to_role2": sorted(skills2 - skills1),
        "top_skills_role1": Counter(_flatten_skills(df1)).most_common(10),
        "top_skills_role2": Counter(_flatten_skills(df2)).most_common(10),
    }


def get_skills_by_role(df: pd.DataFrame) -> pd.DataFrame:
    """Return top skills for each job role."""
    role_col = "standardized_job_title"
    if role_col not in df.columns or "extracted_skills" not in df.columns:
        return pd.DataFrame()

    results = []
    for role in df[role_col].unique():
        role_df = df[df[role_col] == role]
        skills = _flatten_skills(role_df)
        counts = Counter(skills)
        for skill, count in counts.most_common(10):
            results.append({"job_role": role, "skill": skill, "count": count})
    return pd.DataFrame(results)


def get_industry_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Return job count by industry."""
    if "industry" not in df.columns:
        return pd.DataFrame()
    counts = df["industry"].value_counts().reset_index()
    counts.columns = ["industry", "count"]
    return counts


def get_company_skill_range(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return companies requesting the widest range of skills."""
    if "company" not in df.columns or "skills_count" not in df.columns:
        return pd.DataFrame()
    grouped = df.groupby("company")["skills_count"].mean().reset_index()
    grouped.columns = ["company", "avg_skills_count"]
    grouped = grouped.sort_values("avg_skills_count", ascending=False).head(n)
    return grouped


def _flatten_skills(df: pd.DataFrame) -> list[str]:
    """Flatten the extracted_skills column into a flat list of skill names."""
    skills_col = "extracted_skills"
    if skills_col not in df.columns:
        return []
    all_skills = []
    for val in df[skills_col]:
        if isinstance(val, (list, set)):
            all_skills.extend(val)
        elif isinstance(val, str) and val.strip():
            all_skills.extend(s.strip() for s in val.split(","))
    return all_skills

