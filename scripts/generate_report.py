"""
Generate the business insights report (reports/business_insights.md).

All numbers are calculated from the actual dataset. Where data is
insufficient, statements use placeholders/dynamic values instead of
fabricated figures.
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.config import logger
from src.utils import ensure_dir
from src import analytics


def _fmt_salary(value, currency="INR"):
    """Format a salary value as a readable lakh string."""
    if value is None or pd.isna(value):
        return "N/A"
    lakhs = value / 100000
    return f"₹{lakhs:.1f} LPA"


def generate_business_insights(df: pd.DataFrame, output_path=None) -> str:
    """Generate the business insights Markdown report from actual data."""
    if output_path is None:
        output_path = Path(ROOT) / "reports" / "business_insights.md"
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    total_jobs = len(df)
    n_companies = df["company"].nunique() if "company" in df.columns else 0
    n_locations = df["city"].nunique() if "city" in df.columns else 0

    lines = []
    lines.append("# Business Insights Report")
    lines.append("")
    lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("> **Data source:** Synthetic sample dataset (see data/raw notice).")
    lines.append("> All figures below are computed from the loaded dataset.")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Total job postings analysed:** {total_jobs:,}")
    lines.append(f"- **Total companies represented:** {n_companies:,}")
    lines.append(f"- **Job locations covered:** {n_locations:,}")

    avg_salary = df["salary_average"].mean() if "salary_average" in df.columns and df["salary_average"].notna().any() else None
    if avg_salary:
        lines.append(f"- **Average annual salary (where reported):** {_fmt_salary(avg_salary)}")
    else:
        lines.append("- **Average annual salary:** N/A (insufficient salary data)")
    lines.append("")

    # Key job market trends
    lines.append("## Key Job Market Trends")
    lines.append("")
    top_roles = analytics.get_top_roles(df, n=5)
    if len(top_roles) > 0:
        lines.append("**Most demanded job roles:**")
        for i, row in top_roles.iterrows():
            pct = row["count"] / total_jobs * 100
            lines.append(f"- {row['job_role']}: {row['count']:,} postings ({pct:.1f}%)")
    lines.append("")

    trend = analytics.get_job_trend_analysis(df)
    if len(trend) > 0:
        lines.append("**Job posting trend:**")
        first, last = trend.iloc[0], trend.iloc[-1]
        lines.append(f"- Earliest month: {first['year_month']} ({first['count']} postings)")
        lines.append(f"- Latest month: {last['year_month']} ({last['count']} postings)")
    lines.append("")
# Top skills
    lines.append("## Top Skills")
    lines.append("")
    top_skills = analytics.get_top_skills(df, n=10)
    if len(top_skills) > 0:
        for i, row in top_skills.iterrows():
            pct = row["count"] / total_jobs * 100
            lines.append(f"- {row['skill']}: requested in {row['count']:,} postings ({pct:.1f}%)")
    lines.append("")

    # Top locations
    lines.append("## Top Locations")
    lines.append("")
    top_locs = analytics.get_top_locations(df, n=5)
    if len(top_locs) > 0:
        for _, row in top_locs.iterrows():
            lines.append(f"- {row['location']}: {row['count']:,} postings")
    lines.append("")

    # Salary trends
    lines.append("## Salary Trends")
    lines.append("")
    sal_by_role = analytics.get_salary_by_role(df)
    if len(sal_by_role) > 0:
        lines.append("**Average salary by job role:**")
        for _, row in sal_by_role.iterrows():
            lines.append(f"- {row['job_role']}: {_fmt_salary(row['avg_salary'])} "
                         f"({row['count']:,} salary records)")
    lines.append("")

    # Experience insights
    lines.append("## Experience Insights")
    lines.append("")
    exp_analysis = analytics.get_experience_analysis(df)
    if "distribution" in exp_analysis:
        for category, count in sorted(exp_analysis["distribution"].items(), key=lambda x: -x[1]):
            lines.append(f"- **{category}**: {count:,} postings")
    lines.append("")

    # Company hiring trends
    lines.append("## Company Hiring Trends")
    lines.append("")
    top_companies = analytics.get_top_companies(df, n=5)
    if len(top_companies) > 0:
        for _, row in top_companies.iterrows():
            lines.append(f"- {row['company']}: {row['count']:,} postings")
    lines.append("")

    # Career recommendations
    lines.append("## Career Recommendations")
    lines.append("")
    if len(top_skills) >= 5:
        lines.append("Based on skill demand in this dataset, aspiring candidates should prioritise:")
        for i, row in top_skills.head(5).iterrows():
            lines.append(f"{i+1}. **{row['skill']}** — requested in {row['count']:,} postings")
    lines.append("")
    lines.append(
        "> **Note on salaries:** Salary figures are derived from the sample data and "
        "represent relative ordering, not actual market compensation. "
        "For real-world career decisions, cross-reference with live market sources."
    )

    # Write the report
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Business insights report written to %s", output_path)
    return str(output_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate business insights report")
    parser.add_argument("--data", type=str, default=None)
    args = parser.parse_args()

    if args.data:
        df = pd.read_csv(args.data)
    else:
        data_path = Path(ROOT) / "data" / "processed" / "jobs_processed.csv"
        if not data_path.exists():
            print("ERROR: processed data not found. Run the pipeline first.")
            sys.exit(1)
        df = pd.read_csv(data_path)

    path = generate_business_insights(df)
    print(f"\nReport generated: {path}")