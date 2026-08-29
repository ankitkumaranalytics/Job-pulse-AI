"""
Export Power BI-ready CSV files from the processed dataset.

Creates:
- jobs_processed.csv       (main fact table)
- skills_summary.csv       (skill demand)
- company_summary.csv      (company hiring profile)
- location_summary.csv     (location demand)
- salary_summary.csv       (salary by role)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.config import DATA_OUTPUT_DIR, logger
from src.utils import ensure_dir
from src import analytics


def export_powerbi_files(df: pd.DataFrame, output_dir=None) -> dict:
    """
    Export Power BI-ready CSV files from a processed DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Processed job data.
    output_dir : str | None
        Output directory (defaults to data/processed).

    Returns
    -------
    dict
        Mapping of logical file name -> full path.
    """
    if output_dir is None:
        output_dir = DATA_OUTPUT_DIR
    ensure_dir(output_dir)
    out = Path(output_dir)

    exported = {}

    # 1. Main fact table (all processed jobs)
    fact = df.copy()
    # Flatten extracted_skills lists into a comma-separated string for PBI
    if "extracted_skills" in fact.columns:
        fact["extracted_skills_str"] = fact["extracted_skills"].apply(
            lambda x: "; ".join(x) if isinstance(x, (list, set)) else str(x)
        )
        fact = fact.drop(columns=["extracted_skills"])
        fact = fact.rename(columns={"extracted_skills_str": "extracted_skills"})
    jobs_path = out / "jobs_processed.csv"
    fact.to_csv(jobs_path, index=False, encoding="utf-8")
    exported["jobs_processed.csv"] = str(jobs_path)

    # 2. Skills summary
    skills = analytics.get_top_skills(df, n=100)
    skills_path = out / "skills_summary.csv"
    skills.to_csv(skills_path, index=False, encoding="utf-8")
    exported["skills_summary.csv"] = str(skills_path)

    # 3. Company summary
    companies = analytics.get_top_companies(df, n=100)
    companies = companies.rename(columns={"count": "job_count"})
    companies_path = out / "company_summary.csv"
    companies.to_csv(companies_path, index=False, encoding="utf-8")
    exported["company_summary.csv"] = str(companies_path)

    # 4. Location summary
    locations = analytics.get_top_locations(df, n=100)
    locations = locations.rename(columns={"count": "job_count"})
    locations_path = out / "location_summary.csv"
    locations.to_csv(locations_path, index=False, encoding="utf-8")
    exported["location_summary.csv"] = str(locations_path)

    # 5. Salary summary
    salaries = analytics.get_salary_by_role(df)
    salaries_path = out / "salary_summary.csv"
    salaries.to_csv(salaries_path, index=False, encoding="utf-8")
    exported["salary_summary.csv"] = str(salaries_path)

    logger.info("Exported %d Power BI files to %s", len(exported), out)
    return exported


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export Power BI files")
    parser.add_argument("--data", type=str, default=None,
                        help="Path to processed data (default: data/processed/jobs_processed.csv)")
    args = parser.parse_args()

    if args.data:
        data_path = Path(args.data)
    else:
        data_path = Path(DATA_OUTPUT_DIR) / "jobs_processed.csv"

    if not data_path.exists():
        print(f"ERROR: Processed data not found at {data_path}")
        print("Run 'python scripts/run_pipeline.py' first.")
        sys.exit(1)

    df = pd.read_csv(data_path)
    exported = export_powerbi_files(df)
    print("\nPower BI files exported:")
    for name, path in exported.items():
        print(f"  - {name}: {path}")