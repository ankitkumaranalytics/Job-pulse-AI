"""
Job Recommendation page - uses TF-IDF + skill matching.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.job_recommender import JobRecommender
from src.skill_extractor import get_all_skills
from src.utils import unique_options


@st.cache_resource(show_spinner="Fitting TF-IDF recommendation model…")
def get_recommender(df: pd.DataFrame) -> JobRecommender:
    """
    Build and fit the job recommender (Phase 15 performance fix).

    ``st.cache_resource`` keeps a single fitted TF-IDF model alive across
    reruns and users, instead of refitting on every widget interaction.
    The cache key is the dataframe itself, so a new dataset invalidates it.
    """
    recommender = JobRecommender(df)
    recommender.fit()
    return recommender


def render(df: pd.DataFrame) -> None:
    """Render the Job Recommendations page."""
    st.markdown('<div class="page-title">📋 Job Recommendations</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Get personalised job recommendations based on '
        'your skills, location, experience, and target role.</div>',
        unsafe_allow_html=True,
    )

    if "extracted_skills" not in df.columns:
        st.error("Skill data is missing. Run the data pipeline first.")
        return

    # ---------------- User inputs ----------------
    st.markdown("### 👤 Your Profile")

    col1, col2 = st.columns(2)

    with col1:
        target_role = st.selectbox(
            "🎯 Target Role",
            ["Any"] + unique_options(df, "standardized_job_title"),
        )
        st.selectbox(
            "📅 Experience Level",
            ["Fresher", "Entry Level", "Mid Level", "Senior Level"],
            key="reco_exp_level",
        )

    with col2:
        locs = ["Any"] + unique_options(df, "city")
        preferred_location = st.selectbox("📍 Preferred Location", locs)
        user_skills = st.multiselect(
            "🧠 Your Skills",
            options=get_all_skills(),
            help="Select your current skills. These will be used to match jobs.",
        )

    if not user_skills:
        st.info("Select at least one skill to get job recommendations.")
        return

    # Map experience level to years
    exp_map = {
        "Fresher": 0, "Entry Level": 1.5, "Mid Level": 3.5, "Senior Level": 7,
    }
    exp_years = exp_map.get(st.session_state.get("reco_exp_level", "Entry Level"), 1.5)

    # ---------------- Generate recommendations ----------------
    st.divider()
    st.markdown("### 🎯 Recommended Jobs")

    with st.spinner("Computing recommendations using TF-IDF + cosine similarity..."):
        try:
            recommender = get_recommender(df)  # cached: fits only once
            results = recommender.recommend(
                user_skills=user_skills,
                preferred_location=preferred_location if preferred_location != "Any" else "",
                experience_level=exp_years,
                target_role=target_role if target_role != "Any" else "",
            )
        except ValueError as e:
            st.error(f"Recommendation engine error: {e}")
            return
        except Exception as e:
            st.error(f"Unexpected error computing recommendations: {e}")
            return

    if results is None or len(results) == 0:
        st.warning("No matching jobs found. Try broadening your skills or removing location.")
        return

    results = results.reset_index(drop=True)
    results["match_pct"] = (results["match_score"] * 100).round(0).astype(int)

    for i, row in results.iterrows():
        with st.container():
            st.markdown(f"### {i+1}. {row['job_title']}")
            st.markdown(
                f"**🏢 {row['company']}** &nbsp;|&nbsp; 📍 {row['location']} "
                f"&nbsp;|&nbsp; 🔗 Match: **{row['match_pct']}%**"
            )
            st.markdown(f"**Skills required:** {row['skills']}" if row["skills"] else "Skills: N/A")

            if "salary_average" in row.index and pd.notna(row.get("salary_average")):
                st.markdown(f"**💰 Salary:** ₹{row['salary_average']/100000:.1f} LPA")
            else:
                st.markdown("**💰 Salary:** Not specified")

            if row.get("missing_skills"):
                st.markdown(f"**⚠️ Missing skills:** {row['missing_skills']}")
            else:
                st.markdown("**✅ You have all the required skills for this role!**")

            st.divider()

    # Methodology note
    with st.expander("ℹ️ How recommendations are computed"):
        st.markdown(
            """
            The recommendation engine combines:
            - **TF-IDF + Cosine Similarity** on the job description and skills text (30%)
            - **Skill matching** (Jaccard similarity of skills, 30%)
            - **Location matching** (15%)
            - **Role matching** (15%)
            - **Experience matching** (10%)

            Jobs with incomplete data are clearly marked and are compared
            conservatively to avoid misleading recommendations.
            """
        )