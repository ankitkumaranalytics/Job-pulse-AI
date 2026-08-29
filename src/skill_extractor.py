"""
Skill extraction engine for JobPulse AI.

Extracts technical skills from the skills column and job descriptions.
Uses a comprehensive skill dictionary with case-insensitive matching,
skill aliases, and skill categories.
"""
from __future__ import annotations

import re
import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import logger
from .data_cleaning import _find_column
from .utils import normalize_text, ensure_dir


# ---------------------------------------------------------------------------
# Comprehensive Skill Dictionary
# Format: { canonical_name: [aliases] }
# ---------------------------------------------------------------------------
SKILL_DICTIONARY = {
    # Programming Languages
    "Python": ["python", "python3", "python2", "py"],
    "R": ["r language", "rstats", "r programming"],
    "Java": ["java", "core java", "j2ee", "spring"],
    "Scala": ["scala"],
    "SQL": ["sql", "tsql", "pl/sql", "plsql"],
    "JavaScript": ["javascript", "js", "node.js", "nodejs", "react", "angular", "vue"],
    "C++": ["c++", "cpp", "c plus plus"],
    "C#": ["c#", "csharp", ".net", "asp.net"],
    "Go": ["golang", "go language"],
    "Rust": ["rust"],
    "Shell": ["shell", "bash", "sh", "zsh", "powershell"],

    # Databases
    "MySQL": ["mysql", "my sql"],
    "PostgreSQL": ["postgresql", "postgres", "pg", "psql", "redshift"],
    "SQL Server": ["sql server", "mssql", "ms sql", "sqlserver"],
    "MongoDB": ["mongodb", "mongo", "mongo db"],
    "Redis": ["redis"],
    "Cassandra": ["cassandra", "apache cassandra"],
    "Oracle": ["oracle", "oracle db", "oradb"],
    "Elasticsearch": ["elasticsearch", "elastic", "elk"],
    "Snowflake": ["snowflake"],
    "BigQuery": ["bigquery", "big query", "bq"],
    "SQLite": ["sqlite", "sqlite3"],

    # Visualization
    "Power BI": ["power bi", "powerbi", "ms power bi", "pbi"],
    "Tableau": ["tableau", "tableau software"],
    "Excel": ["excel", "ms excel", "microsoft excel", "advanced excel"],
    "Looker": ["looker"],
    "Qlik": ["qlik", "qlikview", "qliksense"],
    "D3.js": ["d3.js", "d3", "d3js"],
    "Matplotlib": ["matplotlib", "mpl"],
        "Seaborn": ["seaborn"],
    "Plotly": ["plotly"],

    # Cloud Platforms
    "AWS": ["aws", "amazon web services", "amazon aws", "ec2", "s3", "lambda"],
    "Azure": ["azure", "microsoft azure", "ms azure", "azure cloud"],
    "GCP": ["gcp", "google cloud", "google cloud platform"],

    # Data Engineering
    "Spark": ["spark", "apache spark", "pyspark", "spark streaming"],
    "Hadoop": ["hadoop", "apache hadoop", "hdfs", "mapreduce"],
    "Airflow": ["airflow", "apache airflow"],
    "Kafka": ["kafka", "apache kafka", "confluent"],
    "NiFi": ["nifi"],
    "DBT": ["dbt", "data build tool"],
    "Fivetran": ["fivetran"],

    # Machine Learning
    "Scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "TensorFlow": ["tensorflow", "tf", "keras"],
    "PyTorch": ["pytorch", "torch"],
    "XGBoost": ["xgboost", "xg boost"],
    "LightGBM": ["lightgbm", "light gbm"],
    "ONNX": ["onnx"],
    "Hugging Face": ["hugging face", "transformers"],
    "NLP": ["nlp", "natural language processing", "nltk", "spacy", "bert"],
    "Computer Vision": ["computer vision", "opencv", "cv2", "yolo"],

    # Data Analysis
    "Pandas": ["pandas", "pd"],
    "NumPy": ["numpy", "np"],
    "Statistics": ["statistics", "statistical analysis", "stats"],
    "Data Cleaning": ["data cleaning", "data cleansing", "data wrangling"],
    "Data Visualization": ["data visualization", "data viz", "visualization"],
    "A/B Testing": ["a/b testing", "ab testing", "split testing"],
    "Time Series": ["time series", "forecasting"],

    # DevOps & Tools
    "Docker": ["docker", "dockerize"],
    "Kubernetes": ["kubernetes", "k8s", "kubectl"],
    "Git": ["git", "github", "gitlab", "bitbucket"],
    "CI/CD": ["ci/cd", "jenkins", "circleci", "github actions"],
    "Terraform": ["terraform"],
    "Ansible": ["ansible"],

    # Other
    "API": ["api", "rest api", "restful", "graphql"],
    "Microservices": ["microservices", "micro services"],
    "Agile": ["agile", "scrum", "kanban", "lean"],
    "JIRA": ["jira", "atlassian"],
    "Confluence": ["confluence"],
    "Hive": ["hive", "apache hive"],
    "Presto": ["presto", "prestodb"],
}



# Reverse lookup: alias -> canonical name
ALIAS_MAP: dict = {}
for canonical, aliases in SKILL_DICTIONARY.items():
    ALIAS_MAP[canonical.lower()] = canonical
    for alias in aliases:
        ALIAS_MAP[alias.lower()] = canonical


# Skill categories mapping
SKILL_CATEGORIES: dict = {
    "Python": "Programming", "R": "Programming", "Java": "Programming",
    "Scala": "Programming", "SQL": "Programming", "JavaScript": "Programming",
    "C++": "Programming", "C#": "Programming", "Go": "Programming",
    "Rust": "Programming", "Shell": "Programming",
    "MySQL": "Databases", "PostgreSQL": "Databases", "SQL Server": "Databases",
    "MongoDB": "Databases", "Redis": "Databases", "Cassandra": "Databases",
    "Oracle": "Databases", "Elasticsearch": "Databases", "Snowflake": "Databases",
    "BigQuery": "Databases", "SQLite": "Databases",
    "Power BI": "Visualization", "Tableau": "Visualization", "Excel": "Visualization",
    "Looker": "Visualization", "Qlik": "Visualization", "D3.js": "Visualization",
    "Matplotlib": "Visualization", "Seaborn": "Visualization", "Plotly": "Visualization",
    "AWS": "Cloud", "Azure": "Cloud", "GCP": "Cloud",
    "Spark": "Data Engineering", "Hadoop": "Data Engineering",
    "Airflow": "Data Engineering", "Kafka": "Data Engineering",
    "NiFi": "Data Engineering", "DBT": "Data Engineering", "Fivetran": "Data Engineering",
    "Scikit-learn": "Machine Learning", "TensorFlow": "Machine Learning",
    "PyTorch": "Machine Learning", "XGBoost": "Machine Learning",
    "LightGBM": "Machine Learning", "ONNX": "Machine Learning",
    "Hugging Face": "Machine Learning", "NLP": "Machine Learning",
    "Computer Vision": "Machine Learning",
    "Pandas": "Data Analysis", "NumPy": "Data Analysis", "Statistics": "Data Analysis",
    "Data Cleaning": "Data Analysis", "Data Visualization": "Data Analysis",
    "A/B Testing": "Data Analysis", "Time Series": "Data Analysis",
    "Docker": "DevOps", "Kubernetes": "DevOps", "Git": "DevOps",
    "CI/CD": "DevOps", "Terraform": "DevOps", "Ansible": "DevOps",
    "API": "Other", "Microservices": "Other", "Agile": "Other",
        "JIRA": "Other", "Confluence": "Other", "Hive": "Big Data", "Presto": "Big Data",
} 

# ---------------------------------------------------------------------------
# Skill Extraction Functions
# ---------------------------------------------------------------------------

def extract_skills_from_text(text: str) -> list[str]:
    """
    Extract canonical skill names from free text (e.g., job description).

    Uses case-insensitive matching against the skill dictionary and aliases.
    Returns a sorted list of unique canonical skill names.
    """
    if pd.isna(text) or not str(text).strip():
        return []

    text_lower = str(text).lower()
    found = set()

    # Check each canonical skill and its aliases
    for canonical, aliases in SKILL_DICTIONARY.items():
        # Check the canonical name itself
        if re.search(r'\b' + re.escape(canonical.lower()) + r'\b', text_lower):
            found.add(canonical)
            continue
        # Check each alias
        for alias in aliases:
            pattern = re.escape(alias.lower())
            if re.search(r'\b' + pattern + r'\b', text_lower):
                found.add(canonical)
                break

    return sorted(found)


def extract_skills(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract skills from a DataFrame using the skills column and/or
    job_description column.

    Adds an ``extracted_skills`` column (list of skill names) and
    a ``skills_count`` column.
    """
    df = df.copy()
    skills_col = _find_column(df, "skills")
    desc_col = _find_column(df, "job_description")

    extracted = []
    for idx, row in df.iterrows():
        skill_set = set()
        # From skills column
        if skills_col:
            val = row[skills_col]
            if pd.notna(val) and str(val).strip():
                for skill in str(val).split(","):
                    skill = skill.strip()
                    if skill:
                        canonical = ALIAS_MAP.get(skill.lower(), skill)
                        skill_set.add(canonical)

        # From job description
        if desc_col:
            desc = row[desc_col]
            if pd.notna(desc) and str(desc).strip():
                desc_skills = extract_skills_from_text(str(desc))
                skill_set.update(desc_skills)

        extracted.append(sorted(skill_set))

    df["extracted_skills"] = extracted
    df["skills_count"] = df["extracted_skills"].apply(len)
    logger.info("Skills extracted for %d rows", len(df))
    return df


def get_skill_category(skill_name: str) -> str:
    """Return the category for a canonical skill name."""
    return SKILL_CATEGORIES.get(skill_name, "Other")


def get_all_skills() -> list[str]:
    """Return all canonical skill names."""
    return list(SKILL_DICTIONARY.keys())


def get_skills_by_role(df: pd.DataFrame) -> dict:
    """
    Return a mapping of standardized_job_title -> list of skills
    sorted by frequency.
    """
    role_col = "standardized_job_title" if "standardized_job_title" in df.columns else None
    if not role_col:
        return {}

    result = {}
    for role in df[role_col].unique():
        role_df = df[df[role_col] == role]
        skill_counts = {}
        for skills in role_df["extracted_skills"]:
            for s in skills:
                skill_counts[s] = skill_counts.get(s, 0) + 1
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        result[role] = sorted_skills
    return result


def save_skill_dictionary(filepath=None) -> str:
    """Save the skill dictionary as a CSV for Power BI / documentation."""
    from .config import DATA_OUTPUT_DIR
    if filepath is None:
        filepath = Path(DATA_OUTPUT_DIR) / "skill_dictionary.csv"
    else:
        filepath = Path(filepath)

    rows = []
    for canonical, aliases in SKILL_DICTIONARY.items():
        rows.append({
            "skill_name": canonical,
            "skill_category": SKILL_CATEGORIES.get(canonical, "Other"),
            "aliases": "; ".join(aliases),
        })
    pd.DataFrame(rows).to_csv(filepath, index=False, encoding="utf-8")
    logger.info("Skill dictionary saved to %s", filepath)
    return str(filepath)


