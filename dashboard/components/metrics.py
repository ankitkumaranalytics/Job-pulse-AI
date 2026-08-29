"""
KPI metric cards for the dashboard.
"""
import streamlit as st


def render_kpi_card(title: str, value: str, subtitle: str = "") -> None:
    """Render a KPI card with title, value, and optional subtitle."""
    st.markdown(
        f"""
        <div class="kpi-card">
            <h3>{title}</h3>
            <div class="value">{value}</div>
            <div class="sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fmt_lpa(value) -> str:
    """Format a salary value as LPA."""
    if value is None or value != value:  # NaN check
        return "N/A"
    lakhs = value / 100000
    if lakhs >= 10:
        return f"₹{lakhs:.0f} LPA"
    return f"₹{lakhs:.1f} LPA"


def fmt_number(value) -> str:
    """Format a number with thousands separator."""
    if value is None:
        return "0"
    return f"{int(value):,}"