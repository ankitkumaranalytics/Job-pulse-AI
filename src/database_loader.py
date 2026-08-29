"""
Database loader module for JobPulse AI.

Provides SQLAlchemy models and functions to:
- Create tables in PostgreSQL
- Load processed data into the database
- Query data back for analytics
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import (
    create_engine, text, MetaData, Table, Column, Integer, String,
    Float, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import Engine

from .config import (
    DATABASE_URL, DB_HOST, DB_PORT, DB_NAME, DB_USER, is_db_configured, logger
)

Base = declarative_base()
metadata = MetaData()


# ---------------------------------------------------------------------------
# Table Definitions
# ---------------------------------------------------------------------------
jobs_table = Table(
    "jobs", metadata,
    Column("job_id", String(50), primary_key=True),
    Column("job_title", Text),
    Column("standardized_job_title", String(100)),
    Column("company", String(200)),
    Column("location", String(100)),
    Column("city", String(100)),
    Column("state", String(100)),
    Column("country", String(50)),
    Column("industry", String(100)),
    Column("salary_min", Float),
    Column("salary_max", Float),
    Column("salary_average", Float),
    Column("currency", String(10)),
    Column("experience_min", Float),
    Column("experience_max", Float),
    Column("experience_category", String(50)),
    Column("employment_type", String(50)),
    Column("posting_date", DateTime),
    Column("job_description", Text),
    Column("created_at", DateTime, default=pd.Timestamp.now),
    Index("idx_jobs_title", "standardized_job_title"),
    Index("idx_jobs_company", "company"),
    Index("idx_jobs_location", "location"),
    Index("idx_jobs_salary", "salary_average"),
)

skills_table = Table(
    "skills", metadata,
    Column("skill_id", String(100), primary_key=True),
    Column("skill_name", String(200), unique=True),
    Column("skill_category", String(100)),
)

job_skills_table = Table(
    "job_skills", metadata,
    Column("job_id", String(50), ForeignKey("jobs.job_id"), primary_key=True),
    Column("skill_id", String(100), ForeignKey("skills.skill_id"), primary_key=True),
    Index("idx_job_skills_skill", "skill_id"),
)


def get_engine(database_url: str = None) -> Engine:
    """
    Create and return a SQLAlchemy engine.

    Raises
    ------
    RuntimeError
        If no database URL is provided and no credentials are configured.
    """
    if database_url is None:
        if not is_db_configured():
            raise RuntimeError(
                "Database is not configured: set DB_PASSWORD (and optionally "
                "DB_HOST/DB_PORT/DB_NAME/DB_USER) via environment variables, "
                ".env, or Streamlit secrets. The dashboard falls back to "
                "processed CSV data automatically."
            )
        database_url = DATABASE_URL
    try:
        engine = create_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            # Fail fast (5s) instead of hanging when the host is unreachable
            # (e.g. localhost referenced from Streamlit Community Cloud).
            connect_args={"connect_timeout": 5}
            if database_url.startswith("postgresql") else {},
        )
        host = DB_HOST if database_url == DATABASE_URL else "(custom)"
        logger.info("Database engine created for host=%s db=%s", host, DB_NAME)
        return engine
    except Exception as e:
        logger.error("Failed to create database engine: %s", e)
        raise


def test_connection(database_url: str = None) -> bool:
    """Test database connection. Returns True on success."""
    try:
        engine = get_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        return False


def create_tables(database_url: str = None) -> None:
    """Create all tables in the database."""
    engine = get_engine(database_url)
    metadata.create_all(engine)
    logger.info("All tables created successfully")


def load_jobs_to_db(df: pd.DataFrame, database_url: str = None, if_exists="replace") -> int:
    """
    Load job data into the jobs table.

    Returns the number of rows inserted.
    """
    engine = get_engine(database_url)
    # Prepare columns for the jobs table
    jobs_df = df.copy()
    # Ensure column names match table schema
    rename_map = {}
    for col in jobs_df.columns:
        if col.lower() == "job_id":
            rename_map[col] = "job_id"
    jobs_df = jobs_df.rename(columns=rename_map)

    # Select only columns that exist in the table
    table_columns = {c.name for c in jobs_table.columns}
    df_cols = {str(c) for c in jobs_df.columns}
    common_cols = table_columns.intersection(df_cols)
    jobs_df = jobs_df[[c for c in jobs_df.columns if str(c) in common_cols]]

    # Ensure posting_date is datetime
    if "posting_date" in jobs_df.columns:
        jobs_df["posting_date"] = pd.to_datetime(jobs_df["posting_date"], errors="coerce")

    count = len(jobs_df)
    jobs_df.to_sql("jobs", engine, if_exists=if_exists, index=False, method="multi")
    logger.info("Loaded %d jobs into database", count)
    return count


def load_skills_to_db(df: pd.DataFrame, database_url: str = None, if_exists="replace") -> int:
    """
    Load extracted skills into skills and job_skills tables.

    Expected columns: job_id, extracted_skills (list of skill names)
    """
    engine = get_engine(database_url)

    # Build unique skill list
    all_skills = set()
    for skills_list in df["extracted_skills"]:
        if isinstance(skills_list, (list, set)):
            all_skills.update(skills_list)
        elif isinstance(skills_list, str) and skills_list.strip():
            all_skills.update(s.strip() for s in skills_list.split(","))

    from .skill_extractor import SKILL_CATEGORIES, SKILL_DICTIONARY
    skill_rows = []
    for skill in sorted(all_skills):
        skill_rows.append({
            "skill_id": skill,
            "skill_name": skill,
            "skill_category": SKILL_CATEGORIES.get(skill, "Other"),
        })
    skills_df = pd.DataFrame(skill_rows)
    skills_df.to_sql("skills", engine, if_exists=if_exists, index=False, method="multi")
    logger.info("Loaded %d unique skills", len(skills_df))

    # Build job_skills mapping
    js_rows = []
    for _, row in df.iterrows():
        job_id = str(row["job_id"])
        skills = row["extracted_skills"]
        if isinstance(skills, (list, set)):
            for s in skills:
                js_rows.append({"job_id": job_id, "skill_id": s})
        elif isinstance(skills, str) and skills.strip():
            for s in skills.split(","):
                s = s.strip()
                if s:
                    js_rows.append({"job_id": job_id, "skill_id": s})

    js_df = pd.DataFrame(js_rows)
    js_df.to_sql("job_skills", engine, if_exists=if_exists, index=False, method="multi")
    logger.info("Loaded %d job-skill mappings", len(js_df))
    return len(skills_df)


def load_all_data(df: pd.DataFrame, database_url: str = None) -> dict:
    """
    Load all processed data into the database.

    Returns a summary dict with counts.
    """
    jobs_count = load_jobs_to_db(df, database_url)
    skills_count = load_skills_to_db(df, database_url)

    return {
        "jobs_loaded": jobs_count,
        "skills_loaded": skills_count,
    }


def execute_query(query: str, database_url: str = None, params: dict = None) -> pd.DataFrame:
    """Execute a SQL query and return results as a DataFrame."""
    engine = get_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        rows = result.fetchall()
        cols = result.keys()
    return pd.DataFrame(rows, columns=cols)

