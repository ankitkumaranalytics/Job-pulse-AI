"""
Generate a realistic synthetic job-posting dataset for JobPulse AI.

Generates at least 10,000 job postings covering the Indian market with:
- Realistic job titles across 7 target data roles + others
- Indian cities (Bangalore, Hyderabad, Pune, Mumbai, etc.)
- Realistic company names (clearly marked as synthetic)
- Multiple industries
- Logical salary & experience distributions correlated with role/level
- Skills related to job roles
- Controlled missing values and duplicates
- Reproducible random seed

IMPORTANT: This is SYNTHETIC / SAMPLE data for demonstration purposes.
It does NOT represent real job postings.
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Ensure the project root is importable when running as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import RAW_DATA_DIR, RANDOM_SEED, logger
from src.utils import ensure_dir

DEFAULT_NUM_RECORDS = 10000

COMPANIES = [
    "TechNova Solutions", "DataPulse Inc", "CloudBridge Tech", "AnalyticsHub",
    "Quantum Data Labs", "InfoSphere Systems", "Helix Analytics", "Nimbus Data",
    "Vertex Insights", "Stratum Consulting", "Skyline Digital", "FusionWorks",
    "Meridian Data", "Alpha Analytics", "Orbit Tech Solutions", "Pinnacle Data Corp",
    "Lumina Digital", "Crestwave Systems", "Nexora Data Labs", "Zenith Analytics",
]

INDUSTRIES = [
    "Information Technology", "Banking", "E-commerce", "Healthcare",
    "Consulting", "Finance", "Manufacturing", "Telecommunications",
]

CITIES = [
    "Bangalore", "Chennai", "Hyderabad", "Mumbai", "Pune",
    "Delhi", "Noida", "Gurgaon", "Kolkata", "Ahmedabad", "Kochi",
]

STATES = {
    "Bangalore": "Karnataka", "Chennai": "Tamil Nadu", "Hyderabad": "Telangana",
    "Mumbai": "Maharashtra", "Pune": "Maharashtra", "Delhi": "Delhi",
    "Noida": "Uttar Pradesh", "Gurgaon": "Haryana", "Kolkata": "West Bengal",
    "Ahmedabad": "Gujarat", "Kochi": "Kerala",
}

EMPLOYMENT_TYPES = ["Full-time", "Contract", "Full-time", "Full-time", "Full-time", "Internship"]

ROLES = {
    "Data Analyst": {
        "titles": ["Data Analyst", "Junior Data Analyst", "Senior Data Analyst",
                   "Data Analyst I", "Data Analytics Associate", "Analytics Analyst"],
        "skills": ["SQL", "Excel", "Python", "Power BI", "Tableau", "Data Visualization"],
        "salary_base": 6,
        "exp_range": (0, 5),
    },
    "Business Analyst": {
        "titles": ["Business Analyst", "Junior Business Analyst", "Senior Business Analyst",
                   "Business Analytics Consultant", "BA - Data"],
        "skills": ["SQL", "Excel", "Power BI", "Data Visualization", "Agile", "Statistics"],
        "salary_base": 7,
        "exp_range": (0, 6),
    },
    "Data Scientist": {
        "titles": ["Data Scientist", "Junior Data Scientist", "Senior Data Scientist",
                   "Data Science Specialist", "Applied Data Scientist"],
        "skills": ["Python", "R", "Statistics", "Machine Learning", "Scikit-learn",
                   "TensorFlow", "NumPy", "Pandas"],
        "salary_base": 12,
        "exp_range": (1, 8),
    },
    "Data Engineer": {
        "titles": ["Data Engineer", "Junior Data Engineer", "Senior Data Engineer",
                   "Data Engineer - ETL", "Big Data Engineer"],
        "skills": ["Python", "SQL", "Spark", "Airflow", "Kafka", "AWS", "Hadoop",
                   "Docker", "PostgreSQL"],
        "salary_base": 13,
        "exp_range": (1, 8),
    },
    "Machine Learning Engineer": {
        "titles": ["Machine Learning Engineer", "ML Engineer", "AI Engineer",
                   "Deep Learning Engineer", "Applied ML Engineer"],
        "skills": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Kubernetes",
                   "Spark", "NLP", "Computer Vision"],
        "salary_base": 15,
        "exp_range": (1, 8),
    },
    "BI Analyst": {
        "titles": ["BI Analyst", "Business Intelligence Analyst", "BI Developer",
                   "Power BI Developer", "BI Consultant"],
        "skills": ["SQL", "Power BI", "Tableau", "Excel", "Data Visualization", "Looker"],
        "salary_base": 8,
        "exp_range": (0, 5),
    },
    "Analytics Engineer": {
        "titles": ["Analytics Engineer", "Data Analytics Engineer", "BI Engineer"],
        "skills": ["SQL", "Python", "DBT", "Airflow", "Snowflake", "Git", "Looker"],
        "salary_base": 11,
        "exp_range": (0, 6),
    },
    "Other": {
        "titles": ["Product Manager - Data", "Data Operations Executive",
                   "Software Engineer - Data", "Data QA Engineer",
                   "Database Administrator", "Data Governance Analyst"],
        "skills": ["SQL", "Python", "Excel", "AWS", "Git"],
        "salary_base": 10,
        "exp_range": (0, 7),
    },
}

ROLE_DISTRIBUTION = {
    "Data Analyst": 0.18, "Business Analyst": 0.13, "Data Scientist": 0.15,
    "Data Engineer": 0.15, "Machine Learning Engineer": 0.10, "BI Analyst": 0.10,
    "Analytics Engineer": 0.07, "Other": 0.12,
}
def generate_job_description(role, skills, company):
    """Generate a realistic job description from role, skills, company."""
    skill_text = ", ".join(skills[:-1]) + " and " + skills[-1] if len(skills) > 1 else skills[0]
    return (
        "We are hiring a " + role + " at " + company + " to join our data team in India. "
        "The ideal candidate will have strong experience with " + skill_text + ". "
        "You will work on business-critical data problems, collaborate with engineering "
        "and business teams, and help drive data-informed decisions. Excellent communication "
        "skills and a problem-solving mindset are essential. Familiarity with "
        + ",".join(skills[:3]) + " is required. If you are passionate about data and want "
        "to grow your career, apply today!"
    )


def generate_sample_data(n_records=DEFAULT_NUM_RECORDS, seed=RANDOM_SEED, output_path=None):
    """
    Generate a synthetic job-posting dataset.

    Parameters
    ----------
    n_records : int
        Number of job postings to generate.
    seed : int
        Random seed for reproducibility.
    output_path : str | None
        Output CSV path. Defaults to data/raw/jobs.csv.

    Returns
    -------
    str
        Path where the CSV was saved.
    """
    if n_records < 1000:
        n_records = 1000

    random.seed(seed)
    np.random.seed(seed)
    logger.info("Generating %d synthetic job postings (seed=%d)...", n_records, seed)

    roles = list(ROLE_DISTRIBUTION.keys())
    role_weights = list(ROLE_DISTRIBUTION.values())
    records = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    for i in range(n_records):
        role = random.choices(roles, weights=role_weights)[0]
        role_cfg = ROLES[role]
        job_title = random.choice(role_cfg["titles"])
        if random.random() < 0.15:
            job_title = "Senior " + job_title

        company = random.choice(COMPANIES)
        city = random.choice(CITIES)
        state = STATES[city]
        industry = random.choice(INDUSTRIES)
        employment_type = random.choice(EMPLOYMENT_TYPES)

        exp_min, exp_max = role_cfg["exp_range"]
        if "Senior" in job_title:
            exp_min = max(exp_min, 5)
            exp_max = max(exp_max, 10)
        e_min = random.randint(exp_min, max(exp_min, exp_max - 1))
        e_max = e_min + random.randint(0, 3)

        base_lpa = role_cfg["salary_base"]
        mult = 1 + e_min * 0.15
        if "Senior" in job_title:
            mult *= 1.4
        salary_min_lpa = base_lpa * mult
        salary_max_lpa = salary_min_lpa * (1.2 + random.random() * 0.5)
        salary_min = int(salary_min_lpa * 100000)
        salary_max = int(salary_max_lpa * 100000)
        salary_text = f"{int(salary_min_lpa)} LPA"

        skills = set(random.sample(role_cfg["skills"], random.randint(3, min(len(role_cfg["skills"]), 7))))
        if random.random() < 0.5:
            skills.add("SQL")
        skills_list = sorted(skills)

        posting_date = start_date + timedelta(days=random.randint(0, 365), hours=random.randint(0, 23))
        description = generate_job_description(role, skills_list, company)

        if e_min == 0:
            exp_text = "Fresher" if random.random() < 0.5 else f"0-{e_max} years"
        else:
            exp_text = f"{e_min}-{e_max} years"

        def maybe_missing(val, pct=0.05):
            return np.nan if random.random() < pct else val

        records.append({
            "job_id": f"JOB-{i+1:06d}",
            "job_title": maybe_missing(job_title, 0.02),
            "company": maybe_missing(company, 0.02),
            "location": city,
            "city": maybe_missing(city, 0.03),
            "state": state,
            "country": "India",
            "industry": maybe_missing(industry, 0.05),
            "salary": maybe_missing(salary_text, 0.05),
            "salary_min": maybe_missing(salary_min, 0.05),
            "salary_max": maybe_missing(salary_max, 0.05),
            "currency": "INR",
            "experience": maybe_missing(exp_text, 0.04),
            "experience_min": maybe_missing(e_min, 0.04),
            "experience_max": maybe_missing(e_max, 0.04),
            "employment_type": maybe_missing(employment_type, 0.03),
            "posting_date": maybe_missing(posting_date.strftime("%Y-%m-%d"), 0.03),
            "job_description": maybe_missing(description, 0.05),
            "skills": ", ".join(skills_list),
        })

    df = pd.DataFrame(records)

    # Controlled duplicates (~2%)
    n_dupes = int(n_records * 0.02)
    dup_sample = df.sample(n=n_dupes, random_state=seed, replace=True)
    df = pd.concat([df, dup_sample], ignore_index=True)
    logger.info("Generated %d records (including %d duplicates)", len(df), n_dupes)

    if output_path is None:
        ensure_dir(RAW_DATA_DIR)
        output_path = str(Path(RAW_DATA_DIR) / "jobs.csv")

    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Synthetic dataset saved to %s", output_path)

    notice_path = Path(output_path).parent / "SYNTHETIC_DATA_NOTICE.txt"
    with open(notice_path, "w", encoding="utf-8") as f:
        f.write(
            "WARNING: This dataset is SYNTHETIC/SAMPLE data generated for\n"
            "demonstration and portfolio purposes only. It does not represent\n"
            "real job postings, real companies, or real market data.\n"
        )
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sample job data")
    parser.add_argument("--records", type=int, default=DEFAULT_NUM_RECORDS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    path = generate_sample_data(args.records, args.seed, args.output)
    print(f"\nSample dataset generated: {path}")
    print("NOTE: This is synthetic data for portfolio demonstration purposes only.")