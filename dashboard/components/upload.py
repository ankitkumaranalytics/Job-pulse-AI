"""Reusable resume upload component (FEATURE 1 UI).

Wraps validation, parsing and error/empty/loading states so pages never
duplicate upload plumbing. The parsed profile is stored in session state
under ``resume_profile`` / ``resume_text`` for cross-page reuse.
"""
from __future__ import annotations

import logging

import streamlit as st

logger = logging.getLogger("jobpulse.dashboard.upload")


def _reset_resume() -> None:
    st.session_state.pop("resume_profile", None)
    st.session_state.pop("resume_text", None)
    st.session_state.pop("ats_report", None)


def resume_uploader(key: str = "resume_upload") -> None:
    """
    Render the resume uploader and analyse the file on change.

    Side effects (session state): resume_profile, resume_text, ats_report.
    Never raises — all failures become friendly UI errors.
    """
    uploaded = st.file_uploader(
        "Upload your resume",
        type=["pdf", "docx", "txt"],
        key=key,
        help="PDF, DOCX or TXT up to 5 MB. Files are processed in-memory and "
             "never stored on the server.",
    )

    if uploaded is None:
        st.markdown(
            '<div class="empty-state"><div class="es-title">No resume uploaded yet</div>'
            "<p>Upload a PDF, DOCX or TXT resume to unlock your ATS score, "
            "job match engine and personalised roadmap.</p></div>",
            unsafe_allow_html=True,
        )
        return

    current_name = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.get("resume_source") != current_name:
        _reset_resume()

    if st.session_state.get("resume_profile") is None:
        with st.spinner("Analysing your resume…"):
            try:
                data = uploaded.getvalue()
                from dashboard.services.resume_service import analyze_resume

                profile = analyze_resume(uploaded.name, data)
                st.session_state["resume_profile"] = profile
                st.session_state["resume_text"] = profile.text
                st.session_state["resume_source"] = current_name
                logger.info("Parsed resume %s (%d words)", uploaded.name, profile.word_count)
            except Exception as exc:  # noqa: BLE001 - friendly UI errors only
                from dashboard.utils.validation import ResumeParseError

                if isinstance(exc, ResumeParseError):
                    st.error(f"📄 {exc}")
                else:
                    logger.error("Resume parse failed: %s", type(exc).__name__)
                    st.error(
                        "Something went wrong while reading this file. "
                        "Please try a different PDF/DOCX/TXT export."
                    )
                return

    profile = st.session_state["resume_profile"]
    if profile.warnings:
        for warning in profile.warnings[:2]:
            st.warning(f"⚠️ {warning}", icon=None)

    chips = " ".join(
        f'<span class="skill-badge">{label}</span>'
        for label in [
            f"👤 {profile.name}" if profile.name else None,
            f"✉️ {profile.email}" if profile.email else None,
            f"📞 {profile.phone}" if profile.phone else None,
            f"🎓 {profile.education_level}" if profile.education_level else None,
            f"💼 {profile.experience_years:g} yrs" if profile.experience_years is not None else None,
            f"🛠 {len(profile.skills)} skills",
            f"🧩 {len(profile.projects)} projects",
        ]
        if label
    )
    st.markdown(f'<div style="margin:0.4rem 0 0.6rem">{chips}</div>', unsafe_allow_html=True)


def render_profile_sections(profile) -> None:
    """Progressive disclosure of the parsed resume details."""
    with st.expander("📋 View everything extracted from your resume", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Skills detected**")
            if profile.skills:
                st.markdown(
                    "".join(
                        f'<span class="skill-badge badge-have">✓ {s}</span>'
                        for s in profile.skills
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("None detected.")
            st.markdown("**Education**")
            for line in profile.education or ["—"]:
                st.caption(line)
            st.markdown("**Certifications**")
            for line in profile.certifications or ["—"]:
                st.caption(line)
        with col2:
            st.markdown("**Projects**")
            for line in profile.projects or ["—"]:
                st.caption(f"• {line}")
            st.markdown(f"**Sections found:** {', '.join(profile.sections_found)}")
            st.markdown(f"**Word count:** {profile.word_count:,}")