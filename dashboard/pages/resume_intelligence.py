"""Resume Intelligence page (FEATURE 1 + 2 + 10).

One flow: upload resume → transparent ATS report → (optional) match
against a pasted job description → application-strength estimate.
All scoring is deterministic and every component shows its factors.
"""
from __future__ import annotations

import sys
from pathlib import Path

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
from dashboard.components.upload import render_profile_sections, resume_uploader
from dashboard.utils.scoring import band_label


def _component_bar(label: str, score: float, factors: list[str]) -> None:
    st.markdown(f"**{label} — {score:.0f}/100** ({band_label(score)})")
    st.progress(min(100, max(0, score)) / 100.0)
    for factor in factors:
        st.caption(f"• {factor}")


def render(df) -> None:
    """Render the Resume Intelligence page."""
    page_header(
        "Resume Intelligence",
        "Upload your resume for a transparent ATS-style audit, then match it "
        "against any job description — every score shows exactly how it was "
        "computed.",
        eyebrow="AI Resume · ATS · Match",
    )

    resume_uploader()
    profile = st.session_state.get("resume_profile")
    if profile is None:
        return

    render_profile_sections(profile)
    st.divider()

    # ---------------- ATS report ----------------
    role = st.session_state.get("career_profile", {}).get("role") \
        or st.session_state.get("resume_target_role")
    role_requirements = None
    if role and df is not None and len(df):
        try:
            from models.skill_gap import SkillGapAnalyzer

            role_requirements = SkillGapAnalyzer(df).get_required_skills(role, top_n=20)
        except Exception:  # noqa: BLE001 - fall back to neutral scoring
            role_requirements = None

    if st.session_state.get("ats_report") is None:
        try:
            from dashboard.services.ats_service import score_resume

            st.session_state["ats_report"] = score_resume(profile, role_requirements)
        except Exception:  # noqa: BLE001
            st.error("Could not score this resume. Please try a different file.")
            return

    report = st.session_state["ats_report"]
    section_header(
        "Your ATS Score",
        kicker="Deterministic audit · not an official ATS vendor score",
    )
    col_score, col_band = st.columns([1, 2])
    with col_score:
        st.markdown(
            f'<div class="kpi-card kpi-accent"><h3>Overall ATS Score</h3>'
            f'<div class="value">{report["overall"]:.0f}/100</div>'
            f'<div class="sub">{band_label(report["overall"])}</div></div>',
            unsafe_allow_html=True,
        )
    with col_band:
        st.caption(report["scoring_basis"])
        if report["missing_keywords"]:
            st.markdown("**Missing high-frequency keywords**")
            st.markdown(
                "".join(
                    f'<span class="skill-badge badge-missing">✗ {k}</span>'
                    for k in report["missing_keywords"][:10]
                ),
                unsafe_allow_html=True,
            )

    labels = {
        "skills_coverage": "Skills Coverage",
        "keyword_optimization": "Keyword Optimization",
        "experience_relevance": "Experience Relevance",
        "structure": "Resume Structure",
        "project_strength": "Project Strength",
    }
    with st.expander("📊 Score breakdown — what moved each category", expanded=True):
        for key, label in labels.items():
            comp = report["components"][key]
            _component_bar(label, comp["score"], comp["factors"])

    if report["recommendations"]:
        st.markdown("#### 🛠 Recommended improvements")
        for rec in report["recommendations"][:7]:
            st.markdown(f"- {rec}")

    # ---------------- Job description match (FEATURE 2) ----------------
    st.divider()
    section_header(
        "Match Against a Job Description",
        kicker="Paste any posting — get six explainable scores",
    )
    jd_text = st.text_area(
        "Job description",
        key="ri_jd",
        height=180,
        placeholder="Paste the full job description here…",
    )
    if st.button("Compute Match", key="ri_match_btn", type="primary"):
        try:
            from dashboard.services.match_service import compute_match

            st.session_state["ri_match"] = compute_match(
                resume_text=profile.text,
                resume_skills=profile.skills,
                jd_text=jd_text,
                experience_years=profile.experience_years,
                education_level=profile.education_level,
                projects_text="\n".join(profile.projects),
            )
        except Exception as exc:  # noqa: BLE001 - friendly only
            from dashboard.utils.validation import ServiceError

            msg = str(exc) if isinstance(exc, ServiceError) else (
                "Match computation failed. Check the job description text and try again."
            )
            st.error(msg)

    match = st.session_state.get("ri_match")
    if match:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(
                f'<div class="kpi-card"><h3>Overall Match Score</h3>'
                f'<div class="value">{match["overall"]:.0f}%</div>'
                f'<div class="sub">{band_label(match["overall"])}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.caption(match["scoring_basis"])
        labels = {
            "skills_match": "Skills Match",
            "keyword_match": "Keyword Match",
            "semantic_match": "Semantic Match",
            "experience_match": "Experience Match",
            "education_match": "Education Match",
            "project_relevance": "Project Relevance",
        }
        for key, label in labels.items():
            comp = match["components"][key]
            _component_bar(label, comp, match["factors"][key])

        colA, colB = st.columns(2)
        with colA:
            st.markdown("**Matched skills**")
            if match["matched_skills"]:
                st.markdown(
                    "".join(
                        f'<span class="skill-badge badge-have">✓ {s}</span>'
                        for s in match["matched_skills"][:12]
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("None detected in the job description.")
        with colB:
            st.markdown("**Missing skills**")
            if match["missing_skills"]:
                st.markdown(
                    "".join(
                        f'<span class="skill-badge badge-missing">✗ {s}</span>'
                        for s in match["missing_skills"][:12]
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("You cover every skill detected in this posting! 🎉")

        # ---------------- Application strength (FEATURE 10) ----------------
        from dashboard.services.match_service import estimate_application_strength

        strength = estimate_application_strength(
            match,
            profile_completeness=85.0 if profile.contact_complete else 65.0,
            ats_overall=report["overall"],
        )
        insight_card(
            f"**Estimated Application Strength: {strength['strength']:.0f}/100** — "
            f"{strength['verdict']} "
            + " ".join(strength["factors"]),
            label="Application Strength (alignment, not a hiring prediction)",
        )
        st.caption(strength["disclaimer"])
    elif not jd_text:
        st.info("Paste a job description above to unlock the match engine.")
