"""
Plotly chart helper functions for the dashboard.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Consistent color palette
COLOR_SEQUENCE = px.colors.qualitative.Plotly

# Light/dark theme defaults
TEMPLATE = "plotly_white"


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str = "",
              orientation: str = "v", height: int = 400) -> go.Figure:
    """Create a bar chart from a DataFrame."""
    fig = px.bar(
        df, x=x, y=y, title=title, orientation=orientation,
        color_discrete_sequence=COLOR_SEQUENCE, template=TEMPLATE,
        height=height,
    )
    fig.update_layout(
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        title_font_size=16,
    )
    return fig


def horizontal_bar(df: pd.DataFrame, x: str, y: str, title: str = "",
                   height: int = 450) -> go.Figure:
    """Create a horizontal bar chart (best for rankings)."""
    fig = px.bar(
        df.sort_values(x, ascending=True),
        x=x, y=y, title=title, orientation="h",
        color_discrete_sequence=COLOR_SEQUENCE, template=TEMPLATE,
        height=height,
    )
    fig.update_layout(
        margin=dict(l=120, r=20, t=60, b=40),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        title_font_size=16,
    )
    return fig


def line_chart(df: pd.DataFrame, x: str, y: str, title: str = "",
               height: int = 400) -> go.Figure:
    """Create a line/area chart for trends."""
    fig = px.line(
        df, x=x, y=y, title=title, markers=True,
        template=TEMPLATE, height=height,
    )
    fig.update_traces(line=dict(width=3, color="#2563eb"))
    fig.update_layout(
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        title_font_size=16,
    )
    return fig


def donut_chart(labels: list[str], values: list[float], title: str = "",
                height: int = 350) -> go.Figure:
    """Create a donut/pie chart."""
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.5,
        marker=dict(colors=COLOR_SEQUENCE),
    )])
    fig.update_layout(
        title=title, template=TEMPLATE, height=height,
        title_font_size=16,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def scatter_salary(df: pd.DataFrame, x: str, y: str, color: str,
                   title: str = "", height: int = 450) -> go.Figure:
    """Create a scatter plot (e.g., salary vs experience)."""
    fig = px.scatter(
        df, x=x, y=y, color=color, title=title,
        template=TEMPLATE, height=height,
        opacity=0.6, color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_layout(
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
        title_font_size=16,
    )
    return fig