"""
app/utils/charts.py
Shared chart styling and helper functions for Plotly charts.
"""

import plotly.graph_objects as go
import plotly.express as px


# GTP brand colours
COLORS = {
    "primary": "#2563EB",
    "primary_light": "#93C5FD",
    "secondary": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "grey": "#6B7280",
    "bg_dark": "#1F2937",
    "bg_light": "#F9FAFB",
}

# Chart layout defaults
LAYOUT_DEFAULTS = dict(
    font=dict(family="Inter, sans-serif", size=12),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=40, b=20),
)


def apply_layout(fig, **kwargs):
    """Apply consistent chart styling."""
    fig.update_layout(**LAYOUT_DEFAULTS, **kwargs)
    return fig
