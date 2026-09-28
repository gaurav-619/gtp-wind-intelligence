"""
app/views/storage_colocation.py
Storage Co-Location Screener (formerly Q4 BESS).
Commercial screening of battery energy storage systems (BESS) co-located
with German onshore wind assets, hybrid project pipelines, and shared-grid connection candidates.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os
from datetime import date

from app.utils.db import query, get_latest_snapshot_date
from app.utils.theme import (
    render_page_header,
    render_kpi_card,
    render_html,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    CHART_HEIGHT_STANDARD
)


def clean_amp(val):
    if val is None or pd.isna(val):
        return ""
    return str(val).replace('\uff06', '&').strip()


def render_storage_colocation():
    render_page_header(
        title="🔋 Storage Co-Location Screener",
        subtitle="Where is battery storage co-deployed with wind generation? Which regional hubs offer the strongest grid-connection capacity for hybrid BESS retrofit?",
        data_source="Marktstammdatenregister (MaStR), Bundesnetzagentur",
        confidence_tier="Tier 1 — Official Registry Proxy Match",
        snapshot_date=get_latest_snapshot_date()
    )

    # Initialize session state for synced state filter
    if "bess_selected_state" not in st.session_state:
        st.session_state["bess_selected_state"] = "All Bundesländer"

    # Query National wind totals
    wind_nat = query("""
        SELECT 
            COALESCE(SUM(nettonennleistung_mw), 0) as total_wind_mw,
            COUNT(*) as wind_plant_count
        FROM wind_plants
        WHERE betriebs_status = 'operating'
          AND bundesland != 'Unbekannt'
    """)
    nat_wind_mw = float(wind_nat["total_wind_mw"].iloc[0]) if not wind_nat.empty else 0.0

    # Co-located BESS operating totals
    bess_coloc_op = query("""
        SELECT 
            COALESCE(SUM(nettonennleistung_mw), 0) as coloc_mw,
            COUNT(*) as coloc_count,
            COALESCE(AVG(nettonennleistung_mw), 0) as avg_mw
        FROM storage_units
        WHERE co_located_wind = TRUE
          AND betriebs_status = 'operating'
    """)
    coloc_op_mw = float(bess_coloc_op["coloc_mw"].iloc[0]) if not bess_coloc_op.empty else 0.0
    coloc_op_count = int(bess_coloc_op["coloc_count"].iloc[0]) if not bess_coloc_op.empty else 0
    avg_bess_mw = float(bess_coloc_op["avg_mw"].iloc[0]) if not bess_coloc_op.empty else 0.0

    # Co-located BESS planned totals
    bess_coloc_pl = query("""
        SELECT 
            COALESCE(SUM(nettonennleistung_mw), 0) as planned_coloc_mw,
            COUNT(*) as planned_coloc_count
        FROM storage_units
        WHERE co_located_wind = TRUE
          AND betriebs_status = 'planned'
    """)
    planned_coloc_mw = float(bess_coloc_pl["planned_coloc_mw"].iloc[0]) if not bess_coloc_pl.empty else 0.0
    planned_coloc_count = int(bess_coloc_pl["planned_coloc_count"].iloc[0]) if not bess_coloc_pl.empty else 0

    coloc_share_pct = (coloc_op_mw / nat_wind_mw * 100.0) if nat_wind_mw > 0 else 0.0

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 0 — EXECUTIVE SUMMARY BANNER
    # ──────────────────────────────────────────────────────────────────────────
    render_html(
        f"""
        <div style="
            background: linear-gradient(135deg, #064e3b 0%, #0f172a 100%);
            border-left: 5px solid {COLOR_SUCCESS};
            border-radius: 12px;
            padding: 22px 26px;
            margin-bottom: 24px;
            color: #ffffff;
        ">
            <div style="color:#6ee7b7; font-size:12px; letter-spacing:1.5px; text-transform:uppercase; font-weight:700; margin-bottom:6px;">
                Executive Takeaway · Co-Location Frontier
            </div>
            <div style="color:#ffffff; font-size:20px; font-weight:700; line-height:1.4; margin-bottom:8px;">
                Germany has <span style="color:#34d399;">{coloc_op_mw:,.1f} MW</span> of battery storage (BESS)
                actively co-located with onshore wind plants, with an additional
                <span style="color:#34d399;">{planned_coloc_mw:,.1f} MW</span> ({planned_coloc_count:,} units)
                currently advancing through planning and development.
            </div>
            <div style="color:#a7f3d0; font-size:13px; line-height:1.5;">
                Co-location penetration sits at <b>{coloc_share_pct:.2f}%</b> of operational wind capacity, indicating an immense early-mover opportunity for grid connection point (Netzanschlusspunkt) optimization and arbitrage co-siting.
            </div>
        </div>
        """
    )

    # ──────────────────────────────────────────────────────────────────────────
    # UNIFIED KPI METRIC CARDS
    # ──────────────────────────────────────────────────────────────────────────
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.markdown(
            render_kpi_card(
                "Operating Co-Located BESS",
                f"{coloc_op_mw:,.1f} MW",
                subtext=f"{coloc_op_count:,} active storage units",
                delta="Tier 1 MaStR",
                delta_type="pos",
                border_left_color=COLOR_SUCCESS
            ),
            unsafe_allow_html=True
        )
    with b2:
        st.markdown(
            render_kpi_card(
                "Co-Location Penetration",
                f"{coloc_share_pct:.2f}%",
                subtext=f"Share of {nat_wind_mw/1000:,.1f} GW wind fleet",
                delta="Early frontier",
                delta_type="neutral",
                border_left_color=COLOR_PRIMARY
            ),
            unsafe_allow_html=True
        )
    with b3:
        st.markdown(
            render_kpi_card(
                "Planned BESS Pipeline",
                f"{planned_coloc_mw:,.1f} MW",
                subtext=f"{planned_coloc_count:,} planned units",
                delta="High expansion",
                delta_type="pos",
                border_left_color=COLOR_SECONDARY
            ),
            unsafe_allow_html=True
        )
    with b4:
        st.markdown(
            render_kpi_card(
                "Average BESS Unit Size",
                f"{avg_bess_mw:,.2f} MW",
                subtext="Mean co-located battery rating",
                delta="Utility/commercial",
                delta_type="neutral",
                border_left_color=COLOR_WARNING
            ),
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 1 — INTERACTIVE SCATTER PLOT & SYNCED STATE SELECTOR
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("### 📊 Regional Hybrid Density & Interactive Co-Location Screener")
    st.caption("💡 **Interactive Filter:** Click any point on the scatter plot below or select from the dropdown to synchronize the asset table.")

    # State level aggregation for scatter plot
    state_agg = query("""
        SELECT 
            w.bundesland,
            ROUND(SUM(w.nettonennleistung_mw), 1) as wind_mw,
            ROUND(COALESCE(b.coloc_mw, 0), 1) as bess_mw,
            COALESCE(b.coloc_units, 0) as bess_units,
            ROUND(COALESCE(b.planned_mw, 0), 1) as planned_bess_mw
        FROM wind_plants w
        LEFT JOIN (
            SELECT 
                bundesland,
                SUM(CASE WHEN betriebs_status = 'operating' THEN nettonennleistung_mw ELSE 0 END) as coloc_mw,
                COUNT(CASE WHEN betriebs_status = 'operating' THEN 1 END) as coloc_units,
                SUM(CASE WHEN betriebs_status = 'planned' THEN nettonennleistung_mw ELSE 0 END) as planned_mw
            FROM storage_units
            WHERE co_located_wind = TRUE
            GROUP BY bundesland
        ) b ON w.bundesland = b.bundesland
        WHERE w.betriebs_status = 'operating'
          AND w.bundesland IS NOT NULL AND w.bundesland != 'Unbekannt'
        GROUP BY w.bundesland, b.coloc_mw, b.coloc_units, b.planned_mw
        ORDER BY bess_mw DESC, wind_mw DESC
    """)

    all_states_bess = ["All Bundesländer"] + state_agg["bundesland"].tolist()
    
    col_sel1, col_sel2 = st.columns([2, 2])
    with col_sel1:
        current_idx = all_states_bess.index(st.session_state["bess_selected_state"]) if st.session_state["bess_selected_state"] in all_states_bess else 0
        chosen_bess_state = st.selectbox(
            "Focus Bundesland Filter:",
            all_states_bess,
            index=current_idx,
            key="bess_state_dropdown"
        )
        if chosen_bess_state != st.session_state["bess_selected_state"]:
            st.session_state["bess_selected_state"] = chosen_bess_state

    # Scatter plot: Wind Capacity vs Co-Located BESS Capacity
    fig_scatter = px.scatter(
        state_agg,
        x="wind_mw",
        y="bess_mw",
        size="bess_units",
        color="bess_mw",
        color_continuous_scale="Viridis",
        hover_name="bundesland",
        hover_data={"wind_mw": ":,.1f", "bess_mw": ":,.1f", "bess_units": True, "planned_bess_mw": ":,.1f"},
        labels={
            "wind_mw": "Operating Wind Capacity (MW)",
            "bess_mw": "Operating Co-Located BESS (MW)",
            "bess_units": "Co-Located Units"
        },
        size_max=35,
    )
    
    # Highlight selected state
    if st.session_state["bess_selected_state"] != "All Bundesländer":
        sel_row = state_agg[state_agg["bundesland"] == st.session_state["bess_selected_state"]]
        if not sel_row.empty:
            fig_scatter.add_trace(go.Scatter(
                x=[sel_row["wind_mw"].iloc[0]],
                y=[sel_row["bess_mw"].iloc[0]],
                mode="markers",
                marker=dict(size=24, color="red", symbol="circle-open", line=dict(width=3, color="red")),
                name="Selected State",
                hoverinfo="skip"
            ))

    fig_scatter.update_layout(
        height=CHART_HEIGHT_STANDARD,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        clickmode="event+select",
        margin={"r": 20, "t": 10, "l": 0, "b": 0},
    )

    chart_event = st.plotly_chart(fig_scatter, use_container_width=True, on_select="rerun", selection_mode="points", key="bess_scatter_chart")
    
    if chart_event and "selection" in chart_event and chart_event["selection"].get("points"):
        pts = chart_event["selection"]["points"]
        if pts and "customdata" in pts[0]:
            # Hover/selection name
            clicked_state = pts[0].get("hovertext") or pts[0].get("text")
            if clicked_state and clicked_state in all_states_bess and clicked_state != st.session_state["bess_selected_state"]:
                st.session_state["bess_selected_state"] = clicked_state
                st.rerun()

    active_bess_state = st.session_state["bess_selected_state"]

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 2 — ASSET-LEVEL SCREENER TABLE (SYNCED)
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"#### 🔎 Co-Located Asset Screener (Filter: **{active_bess_state}**)")

    where_clauses = ["s.co_located_wind = TRUE"]
    params = []

    if active_bess_state != "All Bundesländer":
        where_clauses.append("s.bundesland = ?")
        params.append(active_bess_state)

    assets_query = f"""
        SELECT 
            s.mastr_id as bess_mastr_id,
            s.display_name as bess_name,
            s.operator_name,
            s.bundesland,
            s.postleitzahl as plz,
            s.nettonennleistung_mw as bess_mw,
            s.batterietechnologie as tech,
            s.betriebs_status as status,
            s.inbetriebnahmedatum as comm_date,
            s.matched_wind_mastr_id as wind_ref_id
        FROM storage_units s
        WHERE {" AND ".join(where_clauses)}
        ORDER BY s.nettonennleistung_mw DESC NULLS LAST
        LIMIT 100
    """

    assets_df = query(assets_query, params)

    if not assets_df.empty:
        assets_df["operator_name"] = assets_df["operator_name"].apply(clean_amp)
        assets_df["bess_name"] = assets_df["bess_name"].apply(clean_amp)

        display_table = assets_df.rename(columns={
            "bess_mastr_id": "BESS Unit ID",
            "bess_name": "Battery Facility",
            "operator_name": "Operator Name",
            "bundesland": "State",
            "plz": "Postal Code",
            "bess_mw": "Battery MW",
            "tech": "Technology",
            "status": "Status",
            "comm_date": "Commissioning Date",
            "wind_ref_id": "Matched Wind Unit ID"
        })

        ordered_cols = [
            "BESS Unit ID",
            "Matched Wind Unit ID",
            "Battery Facility",
            "Operator Name",
            "State",
            "Postal Code",
            "Battery MW",
            "Technology",
            "Status",
            "Commissioning Date"
        ]

        st.dataframe(
            display_table[ordered_cols],
            use_container_width=True,
            hide_index=True
        )
        st.caption(f"Showing {len(assets_df)} co-located BESS assets in official MaStR registry.")

        # CSV Export
        unit_note = "# Unit convention: All *_pct columns are percentages (0.35 = 0.35%), all *_mw columns are megawatts.\n"
        csv_bess = (unit_note + assets_df.to_csv(index=False)).encode("utf-8")
        st.download_button(
            label="⬇️ Export Co-Located Assets (CSV)",
            data=csv_bess,
            file_name=f"gtp_bess_colocated_assets_{date.today()}.csv",
            mime="text/csv",
            key="bess_download_csv",
            help="Download co-located BESS asset database as CSV."
        )
    else:
        st.info(f"No co-located BESS assets found for {active_bess_state}.")


render_storage_colocation()
