"""
app/pages/q1_capacity.py
Streamlit page: Which Bundesländer have the most installed
onshore wind capacity, and which are growing fastest?
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from app.utils.db import query, get_latest_snapshot_date

st.set_page_config(page_title="Capacity by State", layout="wide")
st.title("🌬️ Installed Onshore Wind Capacity by Bundesland")

# Get latest year
try:
    latest_year_df = query("""
        SELECT MAX(YEAR(snapshot_date)) as yr FROM snapshots
        WHERE bundesland_code = 'DE'
    """)
    latest_year = int(latest_year_df["yr"].iloc[0]) if not latest_year_df.empty else 2024
except Exception:
    latest_year = 2024
    st.warning("Could not determine latest year. Using 2024.")

# --------------------------------------------------------------------------
# Section 1: National headline metrics
# --------------------------------------------------------------------------

national = query("""
    SELECT total_installed_mw, plant_count
    FROM snapshots
    WHERE bundesland_code = 'DE'
    AND energy_source = 'Wind'
    AND YEAR(snapshot_date) = ?
""", [latest_year])

if not national.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Installed (Germany)",
                f"{national['total_installed_mw'].iloc[0]:,.0f} MW")
    col2.metric("Total Plants",
                f"{national['plant_count'].iloc[0]:,}")
    col3.metric("Data as of", get_latest_snapshot_date())
else:
    st.warning("No national snapshot data found. Run the pipeline first.")

st.divider()

# --------------------------------------------------------------------------
# Section 2: Bundesland filter
# --------------------------------------------------------------------------

states = query("""
    SELECT DISTINCT bundesland FROM snapshots 
    WHERE bundesland_code != 'DE'
    ORDER BY bundesland
""")
state_list = states["bundesland"].tolist() if not states.empty else []

selected = st.selectbox("Filter to a state (optional)",
                         ["All states"] + state_list)

# --------------------------------------------------------------------------
# Section 3: Bar chart - current capacity by state
# --------------------------------------------------------------------------

st.subheader(f"Installed Capacity by Bundesland ({latest_year})")

state_data = query("""
    SELECT bundesland, bundesland_code, total_installed_mw, plant_count
    FROM snapshots
    WHERE bundesland_code != 'DE'
    AND energy_source = 'Wind'
    AND YEAR(snapshot_date) = ?
    ORDER BY total_installed_mw DESC
""", [latest_year])

if not state_data.empty:
    if selected != "All states":
        state_data = state_data[state_data["bundesland"] == selected]

    fig1 = px.bar(
        state_data,
        x="total_installed_mw",
        y="bundesland",
        orientation="h",
        text="total_installed_mw",
        color_discrete_sequence=["#2563EB"],
        labels={"total_installed_mw": "Installed MW", "bundesland": ""},
    )
    fig1.update_traces(texttemplate="%{text:,.0f} MW", textposition="outside")
    fig1.update_layout(height=500, showlegend=False,
                       plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No state data available.")

# --------------------------------------------------------------------------
# Section 4: Line chart - top 5 states over time
# --------------------------------------------------------------------------

st.subheader("Cumulative Installed Capacity Over Time")

if not state_data.empty:
    top5 = state_data.nlargest(5, "total_installed_mw")["bundesland"].tolist()

    if top5:
        placeholders = ",".join(["?" for _ in top5])
        time_data = query(f"""
            SELECT bundesland, YEAR(snapshot_date) as year, total_installed_mw
            FROM snapshots
            WHERE bundesland IN ({placeholders})
            AND energy_source = 'Wind'
            ORDER BY bundesland, year
        """, top5)

        national_time = query("""
            SELECT 'Deutschland' as bundesland, 
                   YEAR(snapshot_date) as year, 
                   total_installed_mw
            FROM snapshots
            WHERE bundesland_code = 'DE'
            AND energy_source = 'Wind'
            ORDER BY year
        """)

        combined = pd.concat([time_data, national_time])

        if not combined.empty:
            fig2 = px.line(
                combined,
                x="year",
                y="total_installed_mw",
                color="bundesland",
                labels={"total_installed_mw": "Cumulative MW", "year": "Year"},
                title="Cumulative Installed Capacity Over Time",
            )
            fig2.update_layout(height=450,
                               plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

# --------------------------------------------------------------------------
# Section 5: Data provenance box
# --------------------------------------------------------------------------

st.divider()
st.caption(
    "**Source:** Marktstammdatenregister (MaStR), "
    "official registry, Bundesnetzagentur · "
    "**Confidence:** Tier 1 — Official · "
    f"**Last updated:** {get_latest_snapshot_date()} · "
    "Capacity shown is cumulative commissioned capacity. "
    "Decommissioned plants are excluded."
)
