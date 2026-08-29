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
            padding-top: 2rem;
        }
        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
        }
        .kpi-card {
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
            border-radius: 12px;
            padding: 1.2rem 1rem;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 0.5rem;
        }
        .kpi-card h3 {
            margin: 0 0 0.3rem 0;
            font-size: 0.85rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            opacity: 0.8;
        }
        .kpi-card .value {
            font-size: 1.7rem;
            font-weight: 700;
            margin: 0;
        }
        .kpi-card .sub {
            font-size: 0.8rem;
            opacity: 0.7;
            margin-top: 0.2rem;
        }
        .page-title {
            color: #0f172a;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .page-subtitle {
            color: #64748b;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }
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