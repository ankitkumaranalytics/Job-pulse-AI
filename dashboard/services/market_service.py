"""Job Market Intelligence service (FEATURE 7).

Turns raw analytics (``src.analytics``) into actionable, plain-language
insights — e.g. 'SQL appears in 72% of Data Analyst postings...'.
Deterministic only; every sentence cites its numbers.
"""
from __future__ import annotations

import pandas as pd

from src import analytics


def _pct(value: float) -> str:
    return f"{value:.0f}%"


def actionable_insights(df: pd.DataFrame, role: str | None = None) -> list[str]:
    """
    Generate 4-8 data-grounded insight sentences for the given (filtered)
    dataset. Safe on small subsets — returns fewer insights instead of
    fabricating statistics.
    """
    insights: list[str] = []
    if df is None or len(df) == 0:
        return insights

    # 1. Skill demand concentration (per role when one is in focus)
    skills = analytics.get_top_skills(df, n=25)
    if len(skills) > 0:
        total = len(df)
        top = skills.iloc[0]
        insights.append(
            f"**{top['skill']}** appears in {_pct(100 * top['count'] / total)} of the "
            f"{total:,} postings shown — the single highest-priority skill in this segment."
        )
        if len(skills) >= 3:
            trio = ", ".join(skills["skill"].head(3).tolist())
            insights.append(
                f"The top-3 demanded skills here are **{trio}** — prioritise them "
                "in your resume keywords and learning plan."
            )

    # 2. Role-specific skill penetration
    role_name = role or (
        df["standardized_job_title"].mode().iat[0]
        if "standardized_job_title" in df.columns and len(df) else None
    )
    if role_name:
        role_df = df[df["standardized_job_title"] == role_name] if "standardized_job_title" in df.columns else df.iloc[0:0]
        if len(role_df) >= 5:
            role_skills = analytics.get_top_skills(role_df, n=1)
            if len(role_skills) > 0:
                rs = role_skills.iloc[0]
                insights.append(
                    f"For **{role_name}** specifically, **{rs['skill']}** is required in "
                    f"{_pct(100 * rs['count'] / len(role_df))} of postings — treat it as "
                    "non-negotiable for this role."
                )

    # 3. Geographic concentration
    if "city" in df.columns:
        cities = df["city"].dropna()
        if len(cities) > 0:
            top_city = cities.value_counts()
            share = 100.0 * top_city.iloc[0] / len(cities)
            if share >= 20:
                insights.append(
                    f"**{top_city.index[0]}** concentrates {_pct(share)} of this segment's "
                    "postings — target it first for on-site applications."
                )

    # 4. Demand trend direction (first vs last month)
    trend = analytics.get_job_trend_analysis(df)
    if len(trend) >= 3:
        first, last = trend.iloc[0], trend.iloc[-1]
        if last["count"] >= first["count"] * 1.15:
            insights.append(
                f"Demand is trending **up**: {int(last['count']):,} postings in "
                f"{last['year_month']} vs {int(first['count']):,} in {first['year_month']}."
            )
        elif last["count"] <= first["count"] * 0.85:
            insights.append(
                f"Demand is cooling: {int(last['count']):,} postings in "
                f"{last['year_month']} vs {int(first['count']):,} in {first['year_month']} — "
                "highlight differentiating projects to stand out."
            )

    # 5. Salary premium skills (only when salary data is dense enough)
    if "salary_average" in df.columns and len(df) >= 30:
        sal_df = df.dropna(subset=["salary_average"])
        market_avg = sal_df["salary_average"].mean()
        if market_avg and market_avg > 0:
            premiums: list[tuple[str, float]] = []
            for skills_row in skills.head(10)["skill"]:
                mask = sal_df["extracted_skills"].apply(
                    lambda lst: isinstance(lst, (list, tuple, set)) and skills_row in lst
                )
                if mask.sum() >= 8:
                    premium = 100.0 * (
                        sal_df.loc[mask, "salary_average"].mean() - market_avg
                    ) / market_avg
                    premiums.append((skills_row, premium))
            premiums.sort(key=lambda x: -x[1])
            if premiums and premiums[0][1] > 8:
                skill, prem = premiums[0]
                insights.append(
                    f"Postings requiring **{skill}** pay {_pct(prem)} above this segment's "
                    "average salary — the highest salary premium detected."
                )

    # 6. Entry-level friendliness
    if "experience_category" in df.columns and len(df) >= 20:
        exp_counts = df["experience_category"].value_counts()
        fresher = int(exp_counts.get("Fresher", 0))
        if fresher:
            insights.append(
                f"{_pct(100.0 * fresher / len(df))} of these postings target Freshers — "
                "the segment is entry-friendly; emphasise projects over experience."
            )

    return insights[:8]