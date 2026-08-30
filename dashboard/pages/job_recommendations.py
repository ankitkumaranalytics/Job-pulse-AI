"""
Job Recommendations page — "Which jobs should I apply for?" (Phase 13).

Premium job cards with sorting, profile handoff from the AI Career
Advisor (Phase 12) and safe handling of missing data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.metrics import fmt_lpa
from dashboard.components.premium import (
    cta_block,
    empty_state,
    insight_card,
    job_card,
    page_header,
)
from models.job_recommender import JobRecommender
from src.skill_extractor import get_all_skills
from src.utils import unique_options

EXP_YEARS = {"Fresher": 0.0, "Entry Level": 1.5, "Mid Level": 3.5, "Senior Level": 7.0}
SORT_OPTIONS = ["Highest Match", "Newest Posting", "Location (A-Z)"]


@st.cache_resource(show_spinner="Fitting TF-IDF recommendation model…")
def get_recommender(df: pd.DataFrame) -> JobRecommender:
    """Fit the TF-IDF recommender once and cache it across reruns (Phase 19)."""
    recommender = JobRecommender(df)
    recommender.fit()
    return recommender


def render(df: pd.DataFrame) -> None:
    """Render the Job Recommendations page."""
    page_header(
        "Job Recommendations",
        "Your best-matching jobs based on skills, target role, experience and "
        "preferred location — scored with TF-IDF + weighted matching.",
        eyebrow="06 · Job Recommendations",
    )

    if "extracted_skills" not in df.columns:
        empty_state(
            "Skill Data Missing",
            "This dataset has no skill information. Run the data pipeline to "
            "enable job recommendations.",
        )
        return

    # ---------- Profile handoff from Career Advisor (Phase 12) ----------
    profile = st.session_state.get("career_profile") or {}
    if profile.get("skills"):
        st.success(
            f"✨ Profile loaded from the ⭐ AI Career Advisor — "
            f"**{profile.get('role', 'Any Role')}** · "
            f"{len(profile['skills'])} skills · "
            f"{profile.get('location', 'Any Location')}. "
            "Adjust anything below if needed."
        )

    # ---------------- Inputs ----------------
    st.markdown("#### Your Search Profile")
    role_options = ["Any Role"] + unique_options(df, "standardized_job_title")
    loc_options = ["Any Location"] + unique_options(df, "city")
    exp_options = list(EXP_YEARS.keys())

    default_role = profile.get("role", "Any Role")
    default_loc = profile.get("location", "Any Location")
    default_exp = profile.get("exp_level", "Entry Level")
    default_skills = [s for s in profile.get("skills", []) if s in get_all_skills()]

    col1, col2 = st.columns(2)
    with col1:
        target_role = st.selectbox(
            "🎯 Target Role",
            role_options,
            index=role_options.index(default_role) if default_role in role_options else 0,
            key="jr_role",
        )
        experience = st.selectbox(
            "📅 Experience Level",
            exp_options,
            index=exp_options.index(default_exp) if default_exp in exp_options else 1,
            key="jr_exp",
        )
    with col2:
        preferred_location = st.selectbox(
            "📍 Preferred Location",
            loc_options,
            index=loc_options.index(default_loc) if default_loc in loc_options else 0,
            key="jr_loc",
        )
        user_skills = st.multiselect(
            "🧠 Your Skills",
            options=get_all_skills(),
            default=default_skills,
            help="Select your current skills — these drive the match score.",
            key="jr_skills",
        )

    sort_by = st.radio(
        "Sort results by", SORT_OPTIONS, horizontal=True, key="jr_sort"
    )

    if not user_skills:
        st.info("Select at least one skill to get job recommendations.")
        return

    exp_years = EXP_YEARS.get(experience, 1.5)

    # ---------------- Recommendations (Phase 17 loading state) ----------
    st.divider()
    st.markdown("#### 🎯 Your Best Matches")
    with st.spinner("Finding your best job matches…"):
        try:
            recommender = get_recommender(df)
            results = recommender.recommend(
                user_skills=user_skills,
                preferred_location=(
                    preferred_location if preferred_location != "Any Location" else ""
                ),
                experience_level=exp_years,
                target_role=target_role if target_role != "Any Role" else "",
            )
        except ValueError as e:
            st.error(f"Recommendation engine error: {e}")
            return
        except Exception:  # noqa: BLE001 - never expose internals
            st.error(
                "Something went wrong while computing recommendations. "
                "Please adjust your profile and try again."
            )
            return

    if results is None or len(results) == 0:
        empty_state(
            "No Suitable Jobs Found",
            "No suitable job matches were found for the selected profile. "
            "Try broadening your skills or clearing the location/role filters.",
        )
        return

    # ---------------- Sort + display job cards ----------------
    results = results.copy()

    if sort_by == "Highest Match":
        results = results.sort_values("match_score", ascending=False)
    elif sort_by == "Newest Posting":
        results = results.sort_values("posting_date", ascending=False, na_position="last")
    elif sort_by == "Location (A-Z)":
        results = results.sort_values("location", ascending=True, na_position="last")

    # Summary insight
    top = results.iloc[0]
    insight_card(
        f"**{len(results)} jobs** matched your profile. Top match: "
        f"**{top['job_title']}** at **{top['company']}** "
        f"({top['match_score'] * 100:.0f}% match)."
    )

    st.divider()

    # Render each job as a premium card
    for rank, (_, row) in enumerate(results.iterrows(), start=1):
        match_pct = int(round(row["match_score"] * 100))

        # Parse matched/missing skills
        matched = [s.strip() for s in str(row.get("skills", "")).split(",") if s.strip()]
        missing = [s.strip() for s in str(row.get("missing_skills", "")).split(",") if s.strip()]

        salary_str = fmt_lpa(row["salary_average"]) if pd.notna(row.get("salary_average")) else None
        exp_str = str(row["experience_category"]) if row.get("experience_category") else None

        job_card(
            rank=rank,
            title=str(row["job_title"]),
            company=str(row["company"]),
            location=str(row["location"]),
            match_pct=match_pct,
            matched=matched,
            missing=missing,
            salary=salary_str,
            experience=exp_str,
        )