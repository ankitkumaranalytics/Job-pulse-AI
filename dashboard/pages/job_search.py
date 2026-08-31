"""Job Search page — natural-language semantic job discovery (FEATURE 4).

Example query handled end-to-end:
"I am a fresher with Python, SQL and Power BI skills looking for a Data
Analyst internship in Chennai."

Streamlit state rules respected: preset-query buttons write
``js_query_preset`` which is consumed BEFORE the text_input widget with
key="js_query" is created (same pattern as requested_navigation).
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
from dashboard.components.premium import empty_state, insight_card, page_header
from dashboard.components.premium import job_card
from dashboard.utils.validation import ServiceError

EXAMPLE_QUERIES = [
    "I am a fresher with Python, SQL and Power BI skills looking for a Data Analyst internship in Chennai",
    "Experienced Power BI developer roles in Bangalore",
    "Entry level data analyst jobs requiring SQL and Excel",
]


def render(df: pd.DataFrame) -> None:
    """Render the Job Search page."""
    page_header(
        "Job Search",
        "Describe what you want in plain English — the search engine extracts "
        "your role, skills, location and experience, then ranks real postings.",
        eyebrow="Discover · Semantic Search",
    )

    if df is None or len(df) == 0:
        empty_state("No Data Available", "No job market data is loaded.")
        return

    # ---------- preset chips: consume BEFORE the query text widget ----------
    chip_clicked = None
    chip_cols = st.columns(len(EXAMPLE_QUERIES))
    for col, example in zip(chip_cols, EXAMPLE_QUERIES):
        if col.button(example.split(" with ")[0][:34] + "…", key=f"js_chip_{abs(hash(example)) % 9999}",
                      help=example):
            chip_clicked = example

    if chip_clicked is not None:
        st.session_state["js_query_preset"] = chip_clicked
    if "js_query_preset" in st.session_state:
        st.session_state["js_query"] = st.session_state.pop("js_query_preset")

    query = st.text_input(
        "🔍 Describe your ideal job",
        value="",
        key="js_query",
        placeholder="e.g. fresher data analyst internship in Chennai with Python and SQL",
    )

    run_search = st.button("Search Jobs", key="js_run", type="primary")
    if not query and not run_search:
        st.info(
            "Type a natural-language query above, or click an example chip, "
            "then press **Search Jobs**."
        )
        return

    try:
        from dashboard.services.search_service import parse_query, rank_jobs

        with st.spinner("Parsing your query and ranking postings…"):
            intent = parse_query(query, df)
            results = rank_jobs(df, query, top_n=20)
    except ServiceError as exc:
        st.error(f"🔎 {exc}")
        return
    except Exception:  # noqa: BLE001 - never expose internals
        st.error("Search failed unexpectedly. Please try a simpler query.")
        return

    # ---------------- Parsed intent ----------------
    chips = []
    if intent["role"]:
        chips.append(f"**Role:** {intent['role']}")
    if intent["location"]:
        chips.append(f"**Location:** {intent['location']}")
    if intent["experience_level"]:
        chips.append(f"**Level:** {intent['experience_level']}")
    if intent["job_type"]:
        chips.append(f"**Type:** {intent['job_type']}")
    if intent["skills"]:
        chips.append("**Skills:** " + ", ".join(intent["skills"]))
    if chips:
        st.markdown("#### 🧠 What I understood from your query")
        st.markdown(" · ".join(chips))

    if len(results) == 0:
        empty_state(
            "No Matching Jobs",
            "Nothing in the dataset matched that query. Try removing the city "
            "or naming different skills.",
        )
        return

    insight_card(
        f"**{len(results)} postings** ranked for your query (semantic ranking "
        "with structured intent boosts). Top match: "
        f"**{results.iloc[0]['job_title']}** at **{results.iloc[0]['company']}**."
    )

    st.divider()
    for rank, (_, row) in enumerate(results.iterrows(), start=1):
        skills_list = (
            [str(s) for s in row.get("extracted_skills", [])]
            if isinstance(row.get("extracted_skills"), (list, tuple, set)) else []
        )
        user_skills = {s.lower() for s in intent["skills"]}
        matched = [s for s in skills_list if s.lower() in user_skills] or skills_list[:4]
        missing = [s for s in skills_list if s.lower() not in user_skills][:4]

        col_card, col_save = st.columns([4, 1])
        with col_card:
            job_card(
                rank=rank,
                title=str(row.get("job_title", "")),
                company=str(row.get("company", "")),
                location=str(row.get("city", "")),
                match_pct=int(round(float(row.get("_search_score", 0)))),
                matched=matched,
                missing=missing,
                salary=(
                    fmt_lpa(row.get("salary_average"))
                    if pd.notna(row.get("salary_average")) else None
                ),
                experience=str(row.get("experience_category", "")) or None,
            )
            st.caption(f"🎯 Matched on: {row.get('_matched_on', '')}")
        with col_save:
            if st.button("🔖 Save", key=f"js_save_{rank}", use_container_width=True):
                try:
                    from dashboard.services import tracker_service

                    tracker_service.add_application(
                        company=str(row.get("company", "")),
                        role=str(row.get("job_title", "")),
                        location=str(row.get("city", "")),
                        status="Saved",
                        source="job_search",
                        match_score=float(row.get("_search_score", 0)),
                    )
                    st.success("Saved to tracker")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not save: {exc}")
