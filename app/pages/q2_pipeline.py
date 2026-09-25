"""
app/pages/q2_pipeline.py
Streamlit page: How healthy is Germany's onshore wind development
pipeline, and how fast are projects being approved?
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from app.utils.db import query, get_latest_snapshot_date

st.set_page_config(page_title="Pipeline Health", layout="wide")
st.title("🏗️ Onshore Wind Development Pipeline")

# Get latest year data
latest = query("""
    SELECT bundesland, bundesland_code,
           total_installed_mw, plant_count,
           planned_mw, planned_count,
           median_permit_days
    FROM snapshots
    WHERE bundesland_code != 'DE'
    AND energy_source = 'Wind'
    AND YEAR(snapshot_date) = (
        SELECT MAX(YEAR(snapshot_date)) FROM snapshots
        WHERE bundesland_code = 'DE'
    )
    ORDER BY total_installed_mw DESC
""")

national = query("""
    SELECT total_installed_mw, planned_mw, median_permit_days
    FROM snapshots
    WHERE bundesland_code = 'DE'
    AND energy_source = 'Wind'
    AND YEAR(snapshot_date) = (
        SELECT MAX(YEAR(snapshot_date)) FROM snapshots
        WHERE bundesland_code = 'DE'
    )
""")

# --------------------------------------------------------------------------
# Section 1: Headline metrics
# --------------------------------------------------------------------------

if not national.empty:
    col1, col2, col3 = st.columns(3)

    planned_mw_val = national["planned_mw"].iloc[0] if national["planned_mw"].iloc[0] else 0
    installed_mw_val = national["total_installed_mw"].iloc[0] if national["total_installed_mw"].iloc[0] else 1
    median_days = national["median_permit_days"].iloc[0]

    col1.metric("Planned Pipeline (Germany)",
                f"{planned_mw_val:,.0f} MW")

    if median_days and not pd.isna(median_days):
        median_months = median_days / 30
        col2.metric("Median Permitting Time",
                    f"{median_months:.1f} months")
    else:
        col2.metric("Median Permitting Time", "N/A")

    ratio = (planned_mw_val / installed_mw_val * 100) if installed_mw_val > 0 else 0
    col3.metric("Pipeline Ratio", f"{ratio:.1f}%",
                help="Planned MW as percentage of installed MW")
else:
    st.warning("No national data found. Run the pipeline first.")

st.divider()

# --------------------------------------------------------------------------
# Section 2: Permitting speed bar chart (colour coded)
# --------------------------------------------------------------------------

if not latest.empty:
    st.subheader("Median Permitting Speed by Bundesland")

    latest["permit_months"] = latest["median_permit_days"] / 30

    def get_color(months):
        if months is None or pd.isna(months):
            return "grey"
        if months < 12:
            return "#10B981"   # green
        elif months < 24:
            return "#F59E0B"   # amber
        return "#EF4444"       # red

    latest["color"] = latest["permit_months"].apply(get_color)
    latest_sorted = latest.sort_values("permit_months", na_position="last")

    fig1 = go.Figure(go.Bar(
        x=latest_sorted["permit_months"],
        y=latest_sorted["bundesland"],
        orientation="h",
        marker_color=latest_sorted["color"],
        text=latest_sorted["permit_months"].apply(
            lambda x: f"{x:.1f} mo" if pd.notna(x) else "N/A"
        ),
        textposition="outside",
    ))
    fig1.update_layout(
        title="Median Permitting Speed by Bundesland",
        xaxis_title="Months (registration to commissioning)",
        height=500,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("🟢 Green < 12 months · 🟡 Amber 12–24 months · 🔴 Red > 24 months")

    st.divider()

    # --------------------------------------------------------------------------
    # Section 3: Planned vs installed grouped bar chart
    # --------------------------------------------------------------------------

    st.subheader("Installed vs Planned Capacity by Bundesland")

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        name="Installed MW",
        x=latest["bundesland"],
        y=latest["total_installed_mw"],
        marker_color="#2563EB",
    ))
    fig2.add_trace(go.Bar(
        name="Planned MW",
        x=latest["bundesland"],
        y=latest["planned_mw"],
        marker_color="#93C5FD",
    ))
    fig2.update_layout(
        barmode="group",
        title="Installed vs Planned Capacity by Bundesland",
        height=450,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig2, use_container_width=True)

# --------------------------------------------------------------------------
# Section 4: Provenance
# --------------------------------------------------------------------------

st.divider()
st.caption(
    "**Source:** MaStR official registry · "
    "**Confidence:** Tier 1 — Official (permitting speed is derived) · "
    f"**Last updated:** {get_latest_snapshot_date()} · "
    "Permitting speed = median days from MaStR registration to commissioning. "
    "May undercount if projects were registered before MaStR launched in 2019."
)
