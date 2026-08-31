"""AI Mock Interview Coach page (FEATURE 9).

Deterministic question generation + heuristic answer evaluation.
Feedback is explicitly labelled AI-guided practice — not a professional
assessment. Session state rules: the Generate/Evaluate buttons write
non-widget keys (ic_questions / ic_feedback) and rerun; all answer
text_areas are keyed per question id.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.premium import (
    empty_state,
    insight_card,
    page_header,
    section_header,
)
from dashboard.utils.scoring import band_label

INTERVIEW_TYPES = ["Technical", "HR", "Behavioral"]


def render(df: pd.DataFrame) -> None:
    """Render the Interview Coach page."""
    page_header(
        "AI Interview Coach",
        "Practise role-specific questions and get structured, honest feedback "
        "on your answers — technical depth, communication, structure and "
        "completeness.",
        eyebrow="Practice · AI Guidance",
    )

    col1, col2, col3 = st.columns(3)
    role_options = ["Any Role"]
    if df is not None and len(df) and "standardized_job_title" in df.columns:
        role_options += sorted(df["standardized_job_title"].dropna().unique().tolist())
    with col1:
        role = st.selectbox("🎯 Target Role", role_options, key="ic_role")
    with col2:
        level = st.selectbox(
            "📅 Experience Level",
            ["Fresher", "Entry Level", "Mid Level", "Senior Level"],
            index=1, key="ic_level",
        )
    with col3:
        interview_type = st.selectbox("🎤 Interview Type", INTERVIEW_TYPES, key="ic_type")

    # Role skills drive technical question selection (when data exists)
    role_skills: list = []
    if role != "Any Role" and df is not None and len(df):
        try:
            from models.skill_gap import SkillGapAnalyzer

            role_skills = SkillGapAnalyzer(df).get_required_skills(role, top_n=8)
        except Exception:  # noqa: BLE001 - fall back to generic questions
            role_skills = []

    if st.button("✨ Generate Mock Interview", key="ic_generate", type="primary"):
        try:
            from dashboard.services.interview_service import generate_interview

            st.session_state["ic_questions"] = generate_interview(
                role_skills, interview_type, level, n_questions=5, seed=42
            )
            st.session_state["ic_feedback"] = {}
        except Exception:  # noqa: BLE001
            st.error("Could not generate questions. Please try again.")
        st.rerun()

    questions = st.session_state.get("ic_questions") or []
    if not questions:
        empty_state(
            "No interview generated yet",
            "Pick a role, experience level and interview type, then click "
            "**Generate Mock Interview**.",
        )
        return

    st.divider()
    section_header("Your Questions", kicker="Answer in your own words — 60-120 words each")
    feedback_map = st.session_state.setdefault("ic_feedback", {})

    for q in questions:
        with st.container(border=True):
            st.markdown(f"**Q{q['id'][1:]} · {q['type']}** — {q['question']}")
            answer = st.text_area(
                "Your answer",
                key=f"ic_ans_{q['id']}",
                height=120,
                placeholder="Use STAR for behavioural questions: Situation → Task → Action → Result…",
                label_visibility="collapsed",
            )
            if st.button("Evaluate this answer", key=f"ic_eval_{q['id']}"):
                try:
                    from dashboard.services.interview_service import evaluate_answer

                    feedback_map[q["id"]] = evaluate_answer(q, answer)
                except Exception:  # noqa: BLE001
                    st.error("Evaluation failed — please try again.")
            feedback = feedback_map.get(q["id"])
            if feedback:
                st.markdown(
                    f"**Score: {feedback['overall']:.0f}/100** ({band_label(feedback['overall'])})"
                )
                st.progress(min(100, max(0, feedback["overall"])) / 100.0)
                comp = feedback["components"]
                st.caption(
                    f"Technical Knowledge {comp['technical_accuracy']:.0f} · "
                    f"Communication {comp['communication']:.0f} · "
                    f"Answer Structure {comp['answer_structure']:.0f} · "
                    f"Completeness {comp['completeness']:.0f}"
                )
                for strength in feedback["strengths"]:
                    st.markdown(f"✅ {strength}")
                for weak in feedback["weak_areas"]:
                    st.markdown(f"⚠️ {weak}")

    answered = [q for q in questions if q["id"] in feedback_map]
    if answered:
        from dashboard.services.interview_service import session_summary

        summary = session_summary([feedback_map[q["id"]] for q in answered])
        st.divider()
        insight_card(
            f"**Overall Interview Score: {summary['overall']:.0f}/100** "
            f"({len(answered)}/{len(questions)} answers evaluated) — "
            f"Technical {summary['components'].get('technical_accuracy', 0):.0f} · "
            f"Communication {summary['components'].get('communication', 0):.0f} · "
            f"Structure {summary['components'].get('answer_structure', 0):.0f} · "
            f"Completeness {summary['components'].get('completeness', 0):.0f}",
            label="Session Scorecard",
        )
        if summary["weak_areas"]:
            st.markdown("**Weak areas**")
            for weak in summary["weak_areas"]:
                st.markdown(f"- ⚠️ {weak}")
        if summary["practice"]:
            st.markdown("**Recommended practice**")
            for item in summary["practice"]:
                st.markdown(f"- 🎯 {item}")

    st.caption(
        "ℹ️ All feedback on this page is AI-generated guidance to support your "
        "practice — it is not an objective or professional assessment of your "
        "interview ability."
    )
