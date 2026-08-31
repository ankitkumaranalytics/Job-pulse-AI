"""Application Tracker page (FEATURE 8) + Smart Alerts (FEATURE 11).

SQLite persistence (data/jobpulse_tracker.db, override with the
JOBPULSE_TRACKER_DB env var). In-app alerts only — Streamlit has no
background push channel, and nothing here pretends otherwise.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.premium import (
    empty_state,
    insight_card,
    kpi_row,
    page_header,
    section_header,
)
from dashboard.utils.constants import APPLICATION_STATUSES, STATUS_META

AUDIT_NOTE = (
    "💾 Data is stored in a local SQLite database (data/jobpulse_tracker.db). "
    "On Streamlit Community Cloud the filesystem is ephemeral — entries reset "
    "when the app redeploys or restarts."
)


def _pill(status: str) -> str:
    meta = STATUS_META.get(status, {"color": "#334155", "bg": "#f1f5f9", "icon": "•"})
    return (
        f'<span class="pill" style="color:{meta["color"]};background:{meta["bg"]}">'
        f'{meta["icon"]} {status}</span>'
    )


def render(df: pd.DataFrame) -> None:
    """Render the Application Tracker page."""
    page_header(
        "Application Tracker",
        "Save jobs, track every application through the funnel and see your "
        "real response rates — plus smart alerts on what to do next.",
        eyebrow="Organise · Track · Follow up",
    )

    # ---------------- Alerts (FEATURE 11) ----------------
    try:
        from dashboard.models.user_profile import UserProfile
        from dashboard.services.alerts_service import generate_alerts
        from dashboard.services import tracker_service as ts

        applications = ts.list_applications()
        profile = UserProfile(
            skills=(st.session_state.get("career_profile") or {}).get("skills", []),
            target_role=(st.session_state.get("career_profile") or {}).get("role", ""),
        )
        alerts = generate_alerts(df, profile, applications)
    except Exception:  # noqa: BLE001 - alerts are best-effort
        applications, alerts = [], []

    if alerts:
        section_header("🔔 Smart Alerts", kicker="In-app notifications based on your data")
        for alert in alerts:
            st.markdown(
                f'<div class="alert-card"><div class="alert-title">{alert["icon"]} '
                f'{alert["title"]}</div><p>{alert["detail"]}</p></div>',
                unsafe_allow_html=True,
            )
        st.caption("Alerts are generated in-app from your profile, dataset and tracker.")

    # ---------------- Add / log an application ----------------
    st.divider()
    section_header("➕ Log an Application", kicker="Manual entry — takes 10 seconds")
    with st.form("tr_add", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            company = st.text_input("Company *", key="tr_company")
            role = st.text_input("Role", key="tr_role")
        with c2:
            location = st.text_input("Location", key="tr_location")
            status = st.selectbox("Status", APPLICATION_STATUSES, key="tr_status")
        notes = st.text_area("Notes", key="tr_notes", height=70,
                             placeholder="Recruiter name, referral, next steps…")
        submitted = st.form_submit_button("Add to Tracker", type="primary")

    if submitted:
        if not company.strip():
            st.error("Company name is required.")
        else:
            try:
                from dashboard.services import tracker_service as ts

                ts.add_application(
                    company=company, role=role, location=location,
                    status=status, notes=notes,
                )
                st.success(f"Added **{company}** to your tracker.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001 - friendly only
                st.error(str(exc) if str(exc) else "Could not save the application.")

    # ---------------- Analytics + pipeline ----------------
    try:
        from dashboard.services import tracker_service as ts

        applications = ts.list_applications()
        analytics = ts.tracker_analytics(applications)
    except Exception:  # noqa: BLE001 - persistence may be read-only in cloud
        applications, analytics = [], {"total": 0, "by_status": {}, "applied": 0,
                                       "interview_rate": 0.0, "response_rate": 0.0,
                                       "offer_rate": 0.0, "applications_this_week": 0}

    st.divider()
    section_header("📊 Your Pipeline", kicker="Live funnel analytics from your tracker")
    kpi_row([
        {"title": "Total Applications", "value": str(analytics["total"]),
         "sub": f"{analytics['applied']} actually applied", "accent": True},
        {"title": "Interview Rate", "value": f"{analytics['interview_rate']:.0f}%",
         "sub": "interviews ÷ applications"},
        {"title": "Response Rate", "value": f"{analytics['response_rate']:.0f}%",
         "sub": "any response ÷ applications"},
        {"title": "This Week", "value": str(analytics["applications_this_week"]),
         "sub": "applications logged in 7 days"},
    ])

    if analytics["total"] == 0:
        empty_state(
            "No applications tracked yet",
            "Save jobs from Job Search or Job Recommendations, or log one "
            "manually above. Every saved job appears here with its match score.",
        )
    else:
        col_table, col_funnel = st.columns([3, 2])
        with col_table:
            st.markdown("**All applications**")
            for app in applications:
                score = (
                    f"{app['match_score']:.0f}%" if app.get("match_score") else "—"
                )
                with st.expander(f"{_pill(app['status'])} &nbsp; "
                                 f"**{app['company']}** — {app['role']} · match {score}",
                                 expanded=False):
                    st.caption(
                        f"📍 {app['location'] or '—'} · 📅 applied {app['applied_date']} · "
                        f"source: {app['source']}"
                    )
                    new_status = st.selectbox(
                        "Update status",
                        APPLICATION_STATUSES,
                        index=APPLICATION_STATUSES.index(app["status"]),
                        key=f"tr_st_{app['id']}",
                    )
                    if new_status != app["status"]:
                        if st.button("Save status", key=f"tr_save_{app['id']}"):
                            try:
                                ts.update_status(app["id"], new_status)
                                st.rerun()
                            except Exception as exc:  # noqa: BLE001
                                st.error(str(exc))
                    new_note = st.text_area("Notes", value=app["notes"],
                                            key=f"tr_nt_{app['id']}", height=60)
                    c_update, c_delete = st.columns(2)
                    if c_update.button("Save notes", key=f"tr_nts_{app['id']}"):
                        try:
                            ts.update_notes(app["id"], new_note)
                            st.success("Notes saved.")
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
                    if c_delete.button("🗑 Delete", key=f"tr_del_{app['id']}"):
                        try:
                            ts.delete_application(app["id"])
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
        with col_funnel:
            st.markdown("**Status distribution**")
            status_counts = {s: n for s, n in analytics["by_status"].items() if n}
            if status_counts:
                total = analytics["total"]
                for status, count in status_counts.items():
                    meta = STATUS_META.get(status)
                    pct = 100.0 * count / total
                    st.markdown(
                        f'<div class="progress-row"><span class="pill" '
                        f'style="color:{meta["color"]};background:{meta["bg"]}">'
                        f'{meta["icon"]} {status}</span>'
                        f'<span class="progress-track"><span class="progress-fill" '
                        f'style="width:{pct:.0f}%;background:{meta["color"]}"></span></span>'
                        f'<span class="progress-count">{count}</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No statuses yet.")
            st.caption(AUDIT_NOTE)
    if applications:
        insight_card(
            f"You logged **{analytics['applications_this_week']}** application(s) "
            f"this week. Keep the momentum — aim for 5 quality, high-match "
            "applications per week rather than 20 generic ones.",
            label="Coach Tip",
        )
