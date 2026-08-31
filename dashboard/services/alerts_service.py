"""Smart Job Alerts service (FEATURE 11).

Derives in-app notifications from the user's profile, the job corpus and
the application tracker. This is an honest in-app notification system —
Streamlit deployments have no background/push channel, so nothing here
pretends to send emails or push notifications.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from dashboard.models.user_profile import UserProfile

HIGH_MATCH_THRESHOLD = 75.0
_FOLLOWUP_AFTER_DAYS = 7


def _quick_skill_score(job_skills: set[str], user_skills: set[str]) -> float:
    """Cheap coverage score (no TF-IDF) for scanning the whole corpus."""
    if not job_skills:
        return 0.0
    return 100.0 * len(job_skills & user_skills) / len(job_skills)


def generate_alerts(
    df: pd.DataFrame | None,
    profile: UserProfile,
    applications: list[dict] | None = None,
    max_alerts: int = 6,
) -> list[dict]:
    """
    Return a list of alert dicts:
    {kind, icon, title, detail, cta_label, cta_page}.
    """
    alerts: list[dict] = []
    user_set = {s.lower() for s in (profile.skills or [])}

    # ---------------- High-match opportunities ----------------
    if df is not None and len(df) and "extracted_skills" in df.columns and user_set:
        scored: list[tuple[float, pd.Series]] = []
        for _, row in df.iterrows():
            skills = row.get("extracted_skills")
            skill_set = (
                {str(s).lower() for s in skills}
                if isinstance(skills, (list, tuple, set)) else set()
            )
            score = _quick_skill_score(skill_set, user_set)
            if score >= HIGH_MATCH_THRESHOLD:
                scored.append((score, row))
        scored.sort(key=lambda pair: -pair[0])
        for score, row in scored[:3]:
            alerts.append({
                "kind": "high_match",
                "icon": "🔥",
                "title": f"High-match opportunity — {score:.0f}% skill coverage",
                "detail": (
                    f"**{row.get('job_title', 'Job')}** at **{row.get('company', 'Company')}** "
                    f"({row.get('city', '')}) matches {score:.0f}% of your listed skills."
                ),
                "cta_label": "Open Job Search",
                "cta_page": "Job Search",
            })

    # ---------------- Jobs matching missing critical skills ----------------
    if df is not None and len(df) and profile.target_role:
        try:
            from dashboard.services.skill_gap_service import analyze_skill_gap

            gaps = analyze_skill_gap(df, profile.skills, profile.target_role, top_n=8)
            critical_missing = [
                p["skill"] for p in gaps["priorities"]
                if p["importance"] == "Critical"
            ][:2]
            if critical_missing and "extracted_skills" in df.columns:
                target_set = {s.lower() for s in critical_missing}

                def covers(row) -> bool:
                    skills = row.get("extracted_skills")
                    return bool(
                        target_set & {str(s).lower() for s in skills}
                        if isinstance(skills, (list, tuple, set)) else False
                    )

                hits = df[df.apply(covers, axis=1)]
                if len(hits):
                    alerts.append({
                        "kind": "skill_bridge",
                        "icon": "🧩",
                        "title": "Jobs that reward your next skill",
                        "detail": (
                            f"{len(hits)} postings in this dataset require "
                            f"**{critical_missing[0]}** — a high-priority gap for "
                            f"{profile.target_role}. Learning it unlocks these roles."
                        ),
                        "cta_label": "Open AI Career Advisor",
                        "cta_page": "⭐ AI Career Advisor",
                    })
        except Exception:  # noqa: BLE001 - alerts must never break a page
            pass

    # ---------------- Follow-up reminders from the tracker ----------------
    today = datetime.now()
    stale = [
        a for a in (applications or [])
        if a.get("status") == "Applied" and a.get("applied_date")
        and (today - datetime.strptime(a["applied_date"], "%Y-%m-%d")).days
        >= _FOLLOWUP_AFTER_DAYS
    ]
    for app in stale[:2]:
        days = (today - datetime.strptime(app["applied_date"], "%Y-%m-%d")).days
        alerts.append({
            "kind": "followup",
            "icon": "⏰",
            "title": f"Follow up: {app['company']}",
            "detail": (
                f"Your **{app['role']}** application at **{app['company']}** has been "
                f"in 'Applied' for {days} days — a polite follow-up email is due."
            ),
            "cta_label": "Open Application Tracker",
            "cta_page": "Application Tracker",
        })

    # ---------------- Profile completeness nudge ----------------
    completeness = profile.completeness
    if completeness < 80:
        missing_bits = []
        if not profile.skills:
            missing_bits.append("your skills")
        if not profile.target_role:
            missing_bits.append("a target role")
        if not profile.resume_text:
            missing_bits.append("an uploaded resume")
        detail = (
            f"Your profile is {completeness:.0f}% complete. Add "
            + (", ".join(missing_bits) or "more details")
            + " to sharpen every match score."
        )
        alerts.append({
            "kind": "profile",
            "icon": "💡",
            "title": "Strengthen your profile",
            "detail": detail,
            "cta_label": "Open Resume Intelligence",
            "cta_page": "Resume Intelligence",
        })

    return alerts[:max_alerts]