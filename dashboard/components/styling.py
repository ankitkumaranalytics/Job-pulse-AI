"""
Dashboard styling helpers for JobPulse AI.
"""
import streamlit as st


def apply_custom_styles() -> None:
    """Inject custom CSS styling for a modern analytics look."""
    st.markdown(
        """
        <style>
        .main {
            padding-top: 1.5rem;
        }
        .block-container {
            max-width: 1200px;
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3, h4 { letter-spacing: -0.01em; }
        a { text-decoration: none; }
        /* ---------- Design tokens ---------- */
        :root {
            --ink: #0f172a;
            --muted: #64748b;
            --primary: #2563eb;
            --line: #e2e8f0;
            --card: #ffffff;
            --radius: 14px;
            --shadow: 0 1px 3px rgba(15, 23, 42, .06), 0 1px 2px rgba(15, 23, 42, .04);
        }
        /* ---------- KPI cards (premium light) ---------- */
        .kpi-card {
            position: relative;
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 1.05rem 1.1rem 0.95rem;
            box-shadow: var(--shadow);
            color: var(--ink);
            overflow: hidden;
            margin-bottom: 0.5rem;
        }
        .kpi-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #2563eb, #7c3aed);
        }
        .kpi-card.kpi-accent::before {
            background: linear-gradient(90deg, #f59e0b, #ef4444);
        }
        .kpi-card h3 {
            margin: 0 0 0.35rem 0;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
        }
        .kpi-card .value {
            font-size: 1.55rem;
            font-weight: 800;
            margin: 0;
            line-height: 1.15;
        }
        .kpi-card .sub {
            font-size: 0.78rem;
            color: var(--muted);
            margin-top: 0.25rem;
        }
        /* ---------- Page headers ---------- */
        .eyebrow {
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--primary);
            margin-bottom: 0.15rem;
        }
        .page-title {
            color: var(--ink);
            font-size: 1.9rem;
            font-weight: 800;
            margin-bottom: 0.15rem;
        }
        .page-subtitle {
            color: var(--muted);
            font-size: 0.98rem;
            margin-bottom: 1.4rem;
        }
        .section-header { margin: 0.4rem 0 0.6rem; }
        .section-header .kicker {
            display: block;
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--primary);
            margin-bottom: 0.1rem;
        }
        .section-header h3 { margin: 0; font-weight: 700; }
        .info-box {
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 0.8rem 1rem;
            border-radius: 6px;
            margin: 0.8rem 0;
            color: #1e3a8a;
        }
        .warning-box {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 0.8rem 1rem;
            border-radius: 6px;
            margin: 0.8rem 0;
            color: #92400e;
        }
        .tag {
            display: inline-block;
            padding: 0.15rem 0.6rem;
            border-radius: 12px;
            font-size: 0.8rem;
            margin: 0.15rem 0.2rem;
            background: #e0e7ff;
            color: #3730a3;
        }
        .skill-have {
            color: #059669;
            font-weight: 600;
        }
        .skill-missing {
            color: #dc2626;
            font-weight: 600;
        }
        /* ---------- Insight cards (data storytelling) ---------- */
        .insight-card {
            background: linear-gradient(135deg, #eff6ff 0%, #f5f3ff 100%);
            border: 1px solid #dbeafe;
            border-left: 4px solid var(--primary);
            border-radius: 10px;
            padding: 0.9rem 1.1rem;
            margin: 0.7rem 0;
            color: #1e293b;
            font-size: 0.93rem;
            line-height: 1.55;
        }
        .insight-card .insight-title {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--primary);
            margin-bottom: 0.3rem;
        }
        /* ---------- Empty / error states ---------- */
        .empty-state {
            text-align: center;
            padding: 2.2rem 1rem;
            border: 1px dashed var(--line);
            border-radius: var(--radius);
            background: #f8fafc;
            margin: 0.8rem 0;
        }
        .empty-state .icon { font-size: 2rem; margin-bottom: 0.4rem; }
        .empty-state .title { font-weight: 700; color: var(--ink); margin-bottom: 0.25rem; }
        .empty-state .msg { color: var(--muted); font-size: 0.9rem; }
        /* ---------- Skill badges ---------- */
        .skill-badge {
            display: inline-block;
            padding: 0.28rem 0.75rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            margin: 0.18rem 0.22rem 0.18rem 0;
            border: 1px solid transparent;
        }
        .skill-badge.have { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
        .skill-badge.critical { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
        .skill-badge.important { background: #fffbeb; color: #b45309; border-color: #fde68a; }
        .skill-badge.optional { background: #f1f5f9; color: #475569; border-color: #e2e8f0; }
        /* ---------- Roadmap steps ---------- */
        .roadmap-step {
            display: flex;
            gap: 0.9rem;
            align-items: flex-start;
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1rem 1.1rem;
            margin-bottom: 0.7rem;
        }
        .roadmap-step .step-no {
            flex-shrink: 0;
            width: 34px; height: 34px;
            border-radius: 10px;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            color: #fff;
            font-weight: 800;
            font-size: 0.95rem;
            display: flex; align-items: center; justify-content: center;
        }
        .roadmap-step .step-title { font-weight: 700; color: var(--ink); margin: 0.1rem 0 0.2rem; }
        .roadmap-step .step-reason { color: var(--muted); font-size: 0.88rem; margin: 0; }
        .roadmap-step.priority-high .step-no { background: linear-gradient(135deg, #dc2626, #f59e0b); }
        /* ---------- Job recommendation cards ---------- */
        .job-card {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1.05rem 1.15rem;
            margin-bottom: 0.85rem;
        }
        .job-card .jc-head { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }
        .job-card .jc-title { font-size: 1.05rem; font-weight: 750; color: var(--ink); margin: 0; }
        .job-card .jc-company { color: var(--muted); font-size: 0.9rem; margin: 0.1rem 0 0.45rem; }
        .job-card .jc-score {
            flex-shrink: 0;
            font-weight: 800;
            font-size: 1.25rem;
            color: #047857;
        }
        .job-card .jc-score.mid { color: #b45309; }
        .job-card .jc-score.low { color: #b91c1c; }
        .job-card .jc-meta { font-size: 0.85rem; color: var(--muted); margin-bottom: 0.5rem; }
        .job-card .jc-line { font-size: 0.88rem; margin: 0.25rem 0; color: #334155; }
        /* ---------- Career Advisor hero promo (home CTA) ---------- */
        .advisor-promo {
            background: linear-gradient(120deg, #0f172a 0%, #1e3a8a 55%, #312e81 100%);
            border-radius: 18px;
            padding: 2rem 2.2rem;
            color: #f8fafc;
            margin: 1.2rem 0 0.5rem;
        }
        .advisor-promo .ap-kicker {
            font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em;
            text-transform: uppercase; color: #93c5fd; margin-bottom: 0.4rem;
        }
        .advisor-promo .ap-title { font-size: 1.65rem; font-weight: 800; margin: 0 0 0.45rem; }
        .advisor-promo .ap-sub { color: #cbd5e1; font-size: 0.98rem; margin: 0; max-width: 640px; }
        /* ---------- Career report callout ---------- */
        .cta-block {
            background: #f8fafc;
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 1rem 1.15rem;
            margin: 0.9rem 0;
        }
        .gauge-note { text-align: center; color: var(--muted); font-size: 0.85rem; margin-top: -0.4rem; }
        .readiness-band {
            text-align: center; font-weight: 700; font-size: 0.95rem;
            padding: 0.35rem 0.8rem; border-radius: 999px; display: inline-block;
        }
        .readiness-band.b-low { background: #fef2f2; color: #b91c1c; }
        .readiness-band.b-mid { background: #fffbeb; color: #b45309; }
        .readiness-band.b-good { background: #ecfdf5; color: #047857; }
        .readiness-band.b-high { background: #e0f2fe; color: #0369a1; }
        /* ---------- Aliases used by premium.py components ---------- */
        .roadmap-num {
            flex-shrink: 0;
            width: 34px; height: 34px;
            border-radius: 10px;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            color: #fff;
            font-weight: 800;
            font-size: 0.95rem;
            display: flex; align-items: center; justify-content: center;
        }
        .roadmap-level {
            font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.1em; color: var(--primary); margin-bottom: 0.1rem;
        }
        .roadmap-skill { font-weight: 700; color: var(--ink); margin-bottom: 0.15rem; }
        .roadmap-reason { color: var(--muted); font-size: 0.88rem; }
        .job-card .jc-match {
            display: inline-block;
            font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em;
            color: #047857; background: #ecfdf5; border: 1px solid #a7f3d0;
            border-radius: 999px; padding: 0.18rem 0.65rem; margin-bottom: 0.5rem;
        }
        .job-card .jc-label {
            font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.09em; color: var(--muted); margin-top: 0.55rem;
        }
        .skill-badge.badge-have { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
        .skill-badge.badge-missing { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
        /* ---------- Career Advisor (Phases 9-12) ---------- */
        .readiness-badge {
            display: inline-block; font-size: 0.82rem; font-weight: 700;
            letter-spacing: 0.04em; padding: 0.3rem 0.85rem; border-radius: 999px;
            margin: 0.4rem 0 0.8rem;
        }
        .readiness-badge.b-low { background: #fee2e2; color: #b91c1c; }
        .readiness-badge.b-mid { background: #fef3c7; color: #b45309; }
        .readiness-badge.b-good { background: #dbeafe; color: #1d4ed8; }
        .readiness-badge.b-high { background: #dcfce7; color: #15803d; }
        .label-critical { font-size: 0.78rem; font-weight: 700; color: #b91c1c;
            text-transform: uppercase; letter-spacing: 0.06em; margin: 0.5rem 0 0.25rem; }
        .label-important { font-size: 0.78rem; font-weight: 700; color: #b45309;
            text-transform: uppercase; letter-spacing: 0.06em; margin: 0.5rem 0 0.25rem; }
        /* ---------- Home hero (Phase 4) ---------- */
        .hero {
            background: linear-gradient(135deg, #eef2ff 0%, #fdf4ff 100%);
            border: 1px solid #e0e7ff;
            border-radius: 18px;
            padding: 2.2rem 2rem 1.9rem;
            margin-bottom: 1.2rem;
        }
        .hero .hero-eyebrow {
            font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.14em; color: #6d28d9; margin-bottom: 0.3rem;
        }
        .hero .hero-title {
            font-size: 2.3rem; font-weight: 800; color: #1e1b4b;
            letter-spacing: -0.02em; line-height: 1.1;
        }
        .hero .hero-tagline { font-size: 1.05rem; color: #475569; margin-top: 0.45rem; }
        .empty-state .es-title {
            font-weight: 700; color: var(--ink); font-size: 1.05rem; margin-bottom: 0.3rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def synthetic_data_notice() -> None:
    """Display a notice when synthetic/sample data is in use."""
    st.markdown(
        """
        <div class="warning-box">
        ⚠️ <strong>Sample data notice:</strong> This dashboard is currently using
        <strong>synthetic/sample data</strong> generated for demonstration purposes.
        Figures shown do not represent real market data.
        </div>
        """,
        unsafe_allow_html=True,
    )