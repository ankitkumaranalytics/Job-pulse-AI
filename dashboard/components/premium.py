"""
Premium UI component library for JobPulse AI.

Reusable, presentation-only building blocks (Phase 15) so pages never
duplicate HTML/CSS: page headers, KPI cards, dynamic insight cards,
section headers, empty states, skill badges, the career readiness
gauge, learning-roadmap steps, and job recommendation cards.

Components never fabricate numbers — every value is passed in by the
caller and must be computed from the loaded dataset.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Navigation (Phase 3): canonical order, hero feature starred.
# app.py builds its sidebar radio from this list; CTA buttons navigate
# via go_to() so the whole app shares one source of truth.
# ---------------------------------------------------------------------------
NAV_LABELS: list[str] = [
    "Overview",
    "Job Search",
    "Job Recommendations",
    "⭐ AI Career Advisor",
    "Resume Intelligence",
    "Interview Coach",
    "Application Tracker",
    "Market Insights",
    "Skills Intelligence",
    "Salary Explorer",
    "Company Intelligence",
]

PAGE_KEYS: dict[str, str] = {
    "Overview": "home",
    "Job Search": "job_search",
    "Job Recommendations": "job_recommendations",
    "⭐ AI Career Advisor": "career_advisor",
    "Resume Intelligence": "resume_intelligence",
    "Interview Coach": "interview_coach",
    "Application Tracker": "application_tracker",
    "Market Insights": "market_insights",
    "Skills Intelligence": "skills_intelligence",
    "Salary Explorer": "salary_explorer",
    "Company Intelligence": "company_insights",
}


def go_to(nav_label: str) -> None:
    """Queue ``nav_label`` as the next page and trigger a rerun.

    Never writes ``st.session_state["nav_selection"]`` directly: that key
    backs the sidebar radio widget, and Streamlit raises StreamlitAPIException
    if a widget-backed key is written after the widget has been instantiated
    in the current run. Instead the request is stored under the non-widget
    key ``requested_navigation``; app.py consumes it at the start of the next
    run, BEFORE the radio is created.
    """
    st.session_state["requested_navigation"] = nav_label
    st.rerun()


def page_header(title: str, subtitle: str, eyebrow: str | None = None) -> None:
    """Consistent page header with optional small uppercase eyebrow."""
    if eyebrow:
        st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def section_header(title: str, kicker: str = "") -> None:
    """Section heading with a thin rule; ``kicker`` is a small overline."""
    kick = f'<span class="kicker">{kicker}</span>' if kicker else ""
    st.markdown(
        f'<div class="section-header">{kick}<h3>{title}</h3></div>',
        unsafe_allow_html=True,
    )


def kpi_card(title: str, value: str, sub: str = "", accent: bool = False) -> None:
    """One premium KPI card (call inside st.columns; or use kpi_row)."""
    cls = "kpi-card kpi-accent" if accent else "kpi-card"
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="{cls}"><h3>{title}</h3>'
        f'<div class="value">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def kpi_row(cards: list[dict]) -> None:
    """Render an evenly-spaced row of KPI cards.

    Each item: {"title": str, "value": str, "sub": str (optional),
    "accent": bool (optional)}.
    """
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            kpi_card(
                card.get("title", ""),
                card.get("value", ""),
                card.get("sub", ""),
                card.get("accent", False),
            )


def insight_card(text: str, label: str = "Market Insight") -> None:
    """Dynamic, data-driven insight callout (Phase 16)."""
    st.markdown(
        f'<div class="insight-card"><span class="insight-label">💡 {label}</span>'
        f"<p>{text}</p></div>",
        unsafe_allow_html=True,
    )


def empty_state(title: str = "No Data Available", message: str = "") -> None:
    """Professional empty state instead of a broken chart (Phase 18)."""
    msg = message or (
        "No records match your current selection. Try adjusting your filters."
    )
    st.markdown(
        f'<div class="empty-state"><div class="es-title">{title}</div>'
        f"<p>{msg}</p></div>",
        unsafe_allow_html=True,
    )


def skill_badges(skills: list[str], kind: str = "have") -> None:
    """
    Render skill badges inline.

    ``kind``: ``'have'`` (green ✓), ``'missing'`` (red ✗) or ``'neutral'``.
    Renders nothing for an empty list.
    """
    if not skills:
        return
    cls = {
        "have": "skill-badge badge-have",
        "missing": "skill-badge badge-missing",
    }.get(kind, "skill-badge")
    mark = "✓" if kind == "have" else ("✗" if kind == "missing" else "•")
    st.markdown(
        "".join(f'<span class="{cls}">{mark} {s}</span>' for s in skills),
        unsafe_allow_html=True,
    )


def readiness_classification(score: float) -> str:
    """Map a 0-100 readiness score to its classification label."""
    score = max(0.0, min(float(score), 100.0))
    if score >= 80:
        return "Highly Competitive"
    if score >= 60:
        return "Job Ready"
    if score >= 40:
        return "Building Foundation"
    return "Needs Development"


def readiness_gauge(score: float) -> None:
    """
    Premium Plotly gauge for the Career Readiness Score (Phase 9).

    Bands: 0-40 red, 40-60 amber, 60-80 blue, 80-100 green.
    Score is clamped to [0, 100]; never fabricates a value.
    """
    score = max(0.0, min(float(score), 100.0))
    if score >= 80:
        color = "#16a34a"
    elif score >= 60:
        color = "#2563eb"
    elif score >= 40:
        color = "#f59e0b"
    else:
        color = "#dc2626"
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 46, "color": "#0f172a"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
                "bar": {"color": color, "thickness": 0.26},
                "bgcolor": "white",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "#fee2e2"},
                    {"range": [40, 60], "color": "#fef3c7"},
                    {"range": [60, 80], "color": "#dbeafe"},
                    {"range": [80, 100], "color": "#dcfce7"},
                ],
            },
        )
    )
    fig.update_layout(
        height=235,
        margin=dict(l=28, r=28, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def roadmap_card(step: int, level: str, skill: str, reason: str) -> None:
    """One learning-roadmap step (Phase 10). ``reason`` must be data-driven."""
    st.markdown(
        f'<div class="roadmap-step"><div class="roadmap-num">{step}</div>'
        f"<div><div class=\"roadmap-level\">{level}</div>"
        f"<div class=\"roadmap-skill\">{skill}</div>"
        f"<div class=\"roadmap-reason\">{reason}</div></div></div>",
        unsafe_allow_html=True,
    )


def job_card(
    rank: int,
    title: str,
    company: str,
    location: str,
    match_pct: int,
    matched: list[str],
    missing: list[str],
    salary: str | None = None,
    experience: str | None = None,
    why: str | None = None,
) -> None:
    """Premium job recommendation card (Phase 13)."""
    salary_html = f" &nbsp;·&nbsp; 💰 {salary}" if salary else ""
    exp_html = f" &nbsp;·&nbsp; 📅 {experience}" if experience else ""
    matched_html = "".join(
        f'<span class="skill-badge badge-have">✓ {s}</span>' for s in matched[:6]
    )
    missing_html = (
        "".join(f'<span class="skill-badge badge-missing">✗ {s}</span>' for s in missing[:4])
        or '<span class="skill-badge badge-have">✓ All required skills matched</span>'
    )
    why_html = (
        f'<div class="why-line">🤖 {why}</div>' if why else ""
    )
    st.markdown(
        f'<div class="job-card"><span class="jc-match">{match_pct}% match</span>'
        f'<div class="jc-title">{rank}. {title}</div>'
        f'<div class="jc-meta">🏢 {company} &nbsp;·&nbsp; 📍 {location}{exp_html}{salary_html}</div>'
        f'{why_html}'
        f'<div class="jc-label">Matched skills</div>{matched_html}'
        f'<div class="jc-label">Missing skills</div>{missing_html}</div>',
        unsafe_allow_html=True,
    )


def cta_block(title: str, message: str, button_label: str, nav_label: str, key: str) -> None:
    """Call-to-action banner whose button navigates via the sidebar radio."""
    st.markdown(
        f'<div class="cta-block"><div class="cta-title">{title}</div>'
        f'<div class="cta-text">{message}</div></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1.4, 1.4, 1.4])
    with c2:
        if st.button(button_label, key=key, type="primary", use_container_width=True):
            go_to(nav_label)
