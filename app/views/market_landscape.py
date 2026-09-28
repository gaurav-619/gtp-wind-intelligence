"""
app/views/market_landscape.py
Market Landscape (formerly Q1 Capacity).
Executive analysis of state-by-state onshore wind capacity distribution,
growth trajectories, and regional density.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import sys
import os

from app.utils.db import query, get_latest_snapshot_date
from app.utils.theme import (
    render_page_header,
    render_kpi_card,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    CHART_HEIGHT_STANDARD,
    CHART_HEIGHT_COMPACT
)


def render_market_landscape():
    render_page_header(
        title="🗺️ Market Landscape",
        subtitle="Which Bundesländer hold the deepest capacity reserves, and where has installation velocity accelerated most?",
        data_source="Marktstammdatenregister (MaStR), Bundesnetzagentur",
        confidence_tier="Tier 1 — Official Registry",
        snapshot_date=get_latest_snapshot_date()
    )

    # ──────────────────────────────────────────────────────────────────────────
    # TIMELINE & REGIONAL CONTROLS
    # ──────────────────────────────────────────────────────────────────────────
    year_bounds = query("""
        SELECT MIN(YEAR(snapshot_date)) as min_yr, MAX(YEAR(snapshot_date)) as max_yr 
        FROM snapshots
        WHERE bundesland_code = 'DE'
    """)

    min_year = int(year_bounds["min_yr"].iloc[0]) if not year_bounds.empty and pd.notna(year_bounds["min_yr"].iloc[0]) else 2000
    max_year = int(year_bounds["max_yr"].iloc[0]) if not year_bounds.empty and pd.notna(year_bounds["max_yr"].iloc[0]) else 2026
    if min_year >= max_year:
        min_year = max_year - 1

    states = query("""
        SELECT DISTINCT bundesland FROM snapshots 
        WHERE bundesland_code != 'DE'
        ORDER BY bundesland
    """)
    state_list = states["bundesland"].tolist() if not states.empty else []

    col_ctrl1, col_ctrl2 = st.columns([2, 1])
    with col_ctrl1:
        selected_year = st.slider(
            "📅 Cumulative Timeline Scrubber (Commissioning Year)",
            min_value=min_year,
            max_value=max_year,
            value=max_year,
            key="market_year_slider",
            help="Scrub through historical years to observe annual cumulative onshore wind capacity across Germany."
        )

    with col_ctrl2:
        selected_state = st.selectbox(
            "📍 Focus Federal State",
            ["All Bundesländer (National)"] + state_list,
            key="market_state_selectbox",
            help="Filter analytics and rankings to a specific state or evaluate national performance."
        )

    # ──────────────────────────────────────────────────────────────────────────
    # UNIFIED KPI METRIC CARDS
    # ──────────────────────────────────────────────────────────────────────────
    is_national = (selected_state == "All Bundesländer (National)")
    if is_national:
        headline_df = query("""
            SELECT total_installed_mw, plant_count
            FROM snapshots
            WHERE bundesland_code = 'DE'
            AND energy_source = 'Wind'
            AND YEAR(snapshot_date) = ?
        """, [selected_year])
        scope_label = "Deutschland (National Total)"
    else:
        headline_df = query("""
            SELECT total_installed_mw, plant_count
            FROM snapshots
            WHERE bundesland = ?
            AND energy_source = 'Wind'
            AND YEAR(snapshot_date) = ?
        """, [selected_state, selected_year])
        scope_label = selected_state

    # Prior year for delta computation
    prior_df = query("""
        SELECT total_installed_mw
        FROM snapshots
        WHERE energy_source = 'Wind'
        AND YEAR(snapshot_date) = ?
        AND {}
    """.format("bundesland_code = 'DE'" if is_national else "bundesland = ?"),
    [selected_year - 1] if is_national else [selected_year - 1, selected_state])

    current_mw = float(headline_df["total_installed_mw"].iloc[0]) if not headline_df.empty and pd.notna(headline_df["total_installed_mw"].iloc[0]) else 0.0
    current_units = int(headline_df["plant_count"].iloc[0]) if not headline_df.empty and pd.notna(headline_df["plant_count"].iloc[0]) else 0
    prior_mw = float(prior_df["total_installed_mw"].iloc[0]) if not prior_df.empty and pd.notna(prior_df["total_installed_mw"].iloc[0]) else 0.0

    delta_str = ""
    delta_type = "pos"
    if prior_mw > 0 and current_mw > 0:
        yoy_growth = ((current_mw - prior_mw) / prior_mw) * 100.0
        delta_str = f"+{yoy_growth:.1f}% YoY" if yoy_growth >= 0 else f"{yoy_growth:.1f}% YoY"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            render_kpi_card(
                "Cumulative Nameplate Capacity",
                f"{current_mw:,.0f} MW",
                subtext=f"{scope_label} as of {selected_year}",
                delta=delta_str,
                delta_type=delta_type,
                border_left_color=COLOR_PRIMARY
            ),
            unsafe_allow_html=True
        )
    with k2:
        st.markdown(
            render_kpi_card(
                "Active Turbine Fleet",
                f"{current_units:,}",
                subtext="Operating turbine units in registry",
                delta="Tier 1 MaStR",
                delta_type="pos",
                border_left_color=COLOR_SECONDARY
            ),
            unsafe_allow_html=True
        )
    with k3:
        avg_rating = (current_mw / current_units) if current_units > 0 else 0.0
        st.markdown(
            render_kpi_card(
                "Average Unit Nameplate",
                f"{avg_rating:.2f} MW",
                subtext="Mean rated capacity per turbine",
                delta="Efficiency index",
                delta_type="neutral",
                border_left_color=COLOR_WARNING
            ),
            unsafe_allow_html=True
        )
    with k4:
        st.markdown(
            render_kpi_card(
                "Analysis Horizon",
                f"{selected_year}",
                subtext=f"Base: 2000 – {max_year}",
                delta="Live scrubber",
                delta_type="pos",
                border_left_color=COLOR_SUCCESS
            ),
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 2 — DENSITY MAP & STATE CAPACITY RANKINGS
    # ──────────────────────────────────────────────────────────────────────────
    state_data = query("""
        SELECT bundesland, bundesland_code, 'DE-' || bundesland_code as iso_code,
               total_installed_mw, plant_count
        FROM snapshots
        WHERE bundesland_code != 'DE'
        AND energy_source = 'Wind'
        AND YEAR(snapshot_date) = ?
        ORDER BY total_installed_mw DESC
    """, [selected_year])

    col_map, col_bar = st.columns([1, 1])

    geojson_path = os.path.join(os.path.dirname(__file__), "..", "utils", "germany_states.geojson")
    geojson_data = None
    if os.path.exists(geojson_path):
        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)
        except Exception as e:
            st.error(f"GeoJSON error: {e}")

    with col_map:
        st.markdown("#### 🗺️ Regional Capacity Density Map")
        if not state_data.empty and geojson_data:
            map_df = state_data.copy()
            fig_map = px.choropleth(
                map_df,
                geojson=geojson_data,
                locations="iso_code",
                featureidkey="properties.id",
                color="total_installed_mw",
                color_continuous_scale="Blues",
                hover_name="bundesland",
                hover_data={"iso_code": False, "total_installed_mw": ":,.0f", "plant_count": ":,"},
                labels={"total_installed_mw": "Installed MW", "plant_count": "Turbines"},
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(
                height=CHART_HEIGHT_STANDARD,
                margin={"r": 0, "t": 10, "l": 0, "b": 0},
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                coloraxis_colorbar=dict(title="MW", thickness=15, len=0.8),
            )
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("Choropleth spatial layer currently loading.")

    with col_bar:
        st.markdown(f"#### 📊 Bundesland Rankings ({selected_year})")
        if not state_data.empty:
            bar_df = state_data.copy()
            if not is_national:
                bar_df["highlight"] = bar_df["bundesland"].apply(lambda b: "Focus State" if b == selected_state else "Other")
                color_map = {"Focus State": COLOR_SECONDARY, "Other": "#CBD5E1"}
                fig_bar = px.bar(
                    bar_df,
                    x="total_installed_mw",
                    y="bundesland",
                    orientation="h",
                    text="total_installed_mw",
                    color="highlight",
                    color_discrete_map=color_map,
                    labels={"total_installed_mw": "Installed MW", "bundesland": ""},
                )
            else:
                fig_bar = px.bar(
                    bar_df,
                    x="total_installed_mw",
                    y="bundesland",
                    orientation="h",
                    text="total_installed_mw",
                    color_discrete_sequence=[COLOR_SECONDARY],
                    labels={"total_installed_mw": "Installed MW", "bundesland": ""},
                )
            fig_bar.update_traces(texttemplate="%{text:,.0f} MW", textposition="outside")
            fig_bar.update_layout(
                height=CHART_HEIGHT_STANDARD,
                showlegend=False,
                margin={"r": 35, "t": 10, "l": 0, "b": 0},
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No comparative state data available.")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 3 — CUMULATIVE GROWTH TRAJECTORY
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"#### 📈 Cumulative Commissioning Trajectory (2000 – {selected_year})")
    
    if not is_national:
        state_time = query("""
            SELECT bundesland, YEAR(snapshot_date) as year, total_installed_mw
            FROM snapshots
            WHERE bundesland = ?
            AND energy_source = 'Wind'
            AND YEAR(snapshot_date) <= ?
            ORDER BY year
        """, [selected_state, selected_year])

        national_time = query("""
            SELECT 'Deutschland (National)' as bundesland, 
                   YEAR(snapshot_date) as year, 
                   total_installed_mw
            FROM snapshots
            WHERE bundesland_code = 'DE'
            AND energy_source = 'Wind'
            AND YEAR(snapshot_date) <= ?
            ORDER BY year
        """, [selected_year])

        combined = pd.concat([state_time, national_time])
    else:
        if not state_data.empty:
            top5 = state_data.nlargest(5, "total_installed_mw")["bundesland"].tolist()
            placeholders = ",".join(["?" for _ in top5])
            time_data = query(f"""
                SELECT bundesland, YEAR(snapshot_date) as year, total_installed_mw
                FROM snapshots
                WHERE bundesland IN ({placeholders})
                AND energy_source = 'Wind'
                AND YEAR(snapshot_date) <= ?
                ORDER BY bundesland, year
            """, top5 + [selected_year])

            national_time = query("""
                SELECT 'Deutschland (National)' as bundesland, 
                       YEAR(snapshot_date) as year, 
                       total_installed_mw
                FROM snapshots
                WHERE bundesland_code = 'DE'
                AND energy_source = 'Wind'
                AND YEAR(snapshot_date) <= ?
                ORDER BY year
            """, [selected_year])

            combined = pd.concat([time_data, national_time])
        else:
            combined = pd.DataFrame()

    if not combined.empty:
        fig_line = px.line(
            combined,
            x="year",
            y="total_installed_mw",
            color="bundesland",
            color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS, COLOR_WARNING, "#8B5CF6", "#64748B"],
            labels={"total_installed_mw": "Cumulative Installed MW", "year": "Commissioning Year", "bundesland": "Jurisdiction"},
        )
        fig_line.update_layout(
            height=CHART_HEIGHT_STANDARD,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickmode="linear", dtick=2),
            margin={"r": 20, "t": 10, "l": 0, "b": 0},
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ──────────────────────────────────────────────────────────────────────────
    # EXPORT DATASET
    # ──────────────────────────────────────────────────────────────────────────
    if not state_data.empty:
        state_export = state_data.copy()
        nat_sum_mw = state_export["total_installed_mw"].sum()
        state_export["share_national_pct"] = (state_export["total_installed_mw"] / nat_sum_mw * 100.0).round(2) if nat_sum_mw > 0 else 0.0
        unit_note = "# Unit convention: All *_pct columns are percentages (0.35 = 0.35%), all *_mw columns are megawatts.\n"
        csv_q1 = (unit_note + state_export.to_csv(index=False)).encode("utf-8")
        st.download_button(
            label=f"⬇️ Export Market Landscape Data ({selected_year}) (CSV)",
            data=csv_q1,
            file_name=f"gtp_wind_market_landscape_{selected_year}.csv",
            mime="text/csv",
            key="market_download_csv",
            help="Download complete state breakdown with national market share as CSV."
        )


render_market_landscape()
