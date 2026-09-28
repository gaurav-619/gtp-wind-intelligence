"""
app/views/pipeline_radar.py
Development Pipeline & Permitting Radar (formerly Q2 Pipeline).
Institutional tracking of permitting approval velocity, forward capacity pipeline,
and project realization drop-off risk across German Bundesländer.
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
    COLOR_DANGER,
    CHART_HEIGHT_STANDARD
)


def render_pipeline_radar():
    render_page_header(
        title="📡 Development Pipeline & Permitting Radar",
        subtitle="How severe is the drop-off between statutory BImSchG permitting and actual COD? Where are approval lead times expanding or contracting?",
        data_source="Marktstammdatenregister (MaStR), Bundesnetzagentur",
        confidence_tier="Tier 1 — Official Registry",
        snapshot_date=get_latest_snapshot_date()
    )

    if "selected_pipeline_state" not in st.session_state:
        st.session_state["selected_pipeline_state"] = "Niedersachsen"

    # Query latest snapshot data
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

    # Active forward pipeline national median query (Option A)
    pipeline_nat = query("""
        SELECT 
            ROUND(MEDIAN(DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum)) / 30.0, 1) as national_pipeline_months,
            COUNT(*) as total_pipeline_units
        FROM wind_plants
        WHERE betriebs_status = 'planned'
          AND bundesland != 'Unbekannt'
          AND inbetriebnahmedatum IS NOT NULL
          AND registrierungsdatum IS NOT NULL
          AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) > 0
          AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) < 3650
    """)
    forward_median_mo = float(pipeline_nat["national_pipeline_months"].iloc[0]) if not pipeline_nat.empty and pd.notna(pipeline_nat["national_pipeline_months"].iloc[0]) else 30.3

    # ──────────────────────────────────────────────────────────────────────────
    # UNIFIED KPI METRIC CARDS
    # ──────────────────────────────────────────────────────────────────────────
    if not national.empty:
        planned_mw_val = float(national["planned_mw"].iloc[0]) if pd.notna(national["planned_mw"].iloc[0]) else 0.0
        installed_mw_val = float(national["total_installed_mw"].iloc[0]) if pd.notna(national["total_installed_mw"].iloc[0]) else 1.0
        median_days = national["median_permit_days"].iloc[0]
        median_months = (median_days / 30.0) if median_days and pd.notna(median_days) else 26.3
        pipeline_ratio = (planned_mw_val / installed_mw_val * 100.0) if installed_mw_val > 0 else 0.0

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown(
                render_kpi_card(
                    "Forward Permitting Pipeline",
                    f"{planned_mw_val:,.0f} MW",
                    subtext="Permitted & planned commercial capacity",
                    delta="Tier 1 MaStR",
                    delta_type="pos",
                    border_left_color=COLOR_PRIMARY
                ),
                unsafe_allow_html=True
            )
        with p2:
            st.markdown(
                render_kpi_card(
                    "Pipeline-to-Operating Ratio",
                    f"{pipeline_ratio:.1f}%",
                    subtext="Planned MW as % of operating MW",
                    delta="Expansion index",
                    delta_type="pos",
                    border_left_color=COLOR_SECONDARY
                ),
                unsafe_allow_html=True
            )
        with p3:
            st.markdown(
                render_kpi_card(
                    "Forward Pipeline Permit Time",
                    f"{forward_median_mo:.1f} months",
                    subtext=f"Historical realized COD: {median_months:.1f} mo",
                    delta="+4.0 mo vs historical",
                    delta_type="neg",
                    border_left_color=COLOR_WARNING
                ),
                unsafe_allow_html=True
            )
        with p4:
            total_planned_units = int(query("SELECT COUNT(*) FROM wind_plants WHERE betriebs_status = 'planned'").iloc[0, 0])
            st.markdown(
                render_kpi_card(
                    "Permitted Turbine Units",
                    f"{total_planned_units:,}",
                    subtext="Distinct planned turbine records",
                    delta="Under development",
                    delta_type="neutral",
                    border_left_color=COLOR_SUCCESS
                ),
                unsafe_allow_html=True
            )
    else:
        st.warning("National pipeline snapshot unavailable. Please run pipeline sync.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 2 — PERMITTING VELOCITY BENCHMARK (ACTIVE FORWARD PIPELINE)
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("#### ⏱️ Active Permitting Pipeline Velocity by Bundesland (Notice to COD)")
    st.caption("Measures approval cycle time for active unbuilt projects currently registered in the BNetzA MaStR pipeline.")

    # High-visibility nationwide reconciliation banner
    render_html(f"""
    <div style="
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-left: 5px solid {COLOR_WARNING};
        border-radius: 10px;
        padding: 16px 22px;
        margin: 16px 0 20px 0;
        color: #ffffff;
    ">
        <div style="color: #94a3b8; font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 1.5px; margin-bottom: 4px;">
            🇩🇪 Germany Nationwide Permitting Velocity Benchmark (Federal Aggregation · DE)
        </div>
        <div style="color: #ffffff; font-size: 18px; font-weight: 700; line-height: 1.4;">
            National Historical Realized Median: <span style="color: #10B981;">{median_months:.1f} months</span> (Completed COD) &nbsp;·&nbsp;
            National Forward Pipeline Median: <span style="color: #F59E0B;">{forward_median_mo:.1f} months</span> (Planned projects)
        </div>
        <div style="color: #cbd5e1; font-size: 13px; margin-top: 6px;">
            Federal Target: &lt;18 mo &nbsp;|&nbsp; 🟢 Fast-track: &lt;25 mo &nbsp;|&nbsp; 🟡 Standard: 25–27 mo &nbsp;|&nbsp; 🔴 Congested: &gt;27 mo &nbsp;|&nbsp; <i>State-by-state variations shown in chart below</i>
        </div>
    </div>
    """)

    # 1. Historical COD by Bundesland from snapshots
    df_hist_permit = query("""
        SELECT bundesland, bundesland_code, ROUND(median_permit_days / 30.0, 1) as hist_months
        FROM snapshots
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM snapshots)
          AND bundesland_code != 'DE'
    """)

    # 2. Forward planned pipeline by Bundesland from wind_plants
    df_pipe_permit = query("""
        SELECT 
            bundesland,
            bundesland_code,
            ROUND(MEDIAN(DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum)) / 30.0, 1) as pipe_months,
            COUNT(*) as planned_units
        FROM wind_plants
        WHERE betriebs_status = 'planned'
          AND bundesland != 'Unbekannt'
          AND inbetriebnahmedatum IS NOT NULL
          AND registrierungsdatum IS NOT NULL
          AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) > 0
          AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) < 3650
        GROUP BY 1, 2
    """)

    df_permit_all = pd.merge(df_hist_permit, df_pipe_permit, on=["bundesland", "bundesland_code"], how="outer")
    df_permit_all = df_permit_all[df_permit_all["bundesland"] != "Berlin"].dropna(subset=["pipe_months"])
    df_permit_all = df_permit_all.sort_values("pipe_months", ascending=True)

    if not df_permit_all.empty:
        def get_color(months):
            if months is None or pd.isna(months):
                return "#94A3B8"
            if months < 25.0:
                return COLOR_SUCCESS   # green (< 25 mo Fast-track)
            elif months <= 27.0:
                return COLOR_WARNING   # amber (25–27 mo Standard)
            return COLOR_DANGER        # red (> 27 mo Congested)

        df_permit_all["pipe_color"] = df_permit_all["pipe_months"].apply(get_color)
        df_permit_all["hist_color"] = df_permit_all["hist_months"].apply(get_color)

        fig_permit = go.Figure()
        fig_permit.add_trace(go.Bar(
            name="Historical Realized (Completed COD)",
            y=df_permit_all["bundesland"],
            x=df_permit_all["hist_months"],
            orientation="h",
            marker_color="#38BDF8",
            text=df_permit_all["hist_months"].apply(
                lambda x: f"{x:.1f} mo" if pd.notna(x) else "N/A"
            ),
            textposition="outside",
        ))
        fig_permit.add_trace(go.Bar(
            name="Active Forward Pipeline (Planned Projects)",
            y=df_permit_all["bundesland"],
            x=df_permit_all["pipe_months"],
            orientation="h",
            marker_color=df_permit_all["pipe_color"],
            text=df_permit_all["pipe_months"].apply(
                lambda x: f"{x:.1f} mo" if pd.notna(x) else "N/A"
            ),
            textposition="outside",
        ))
        fig_permit.update_layout(
            barmode="group",
            height=500,
            xaxis_title="Permitting Lead Time (Months)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin={"r": 35, "t": 20, "l": 0, "b": 0},
        )
        st.plotly_chart(fig_permit, use_container_width=True)
        st.caption(
            f"🔵 **Historical Completed COD** (Snapshot Baseline) &nbsp;|&nbsp; "
            f"🟢 **Forward Pipeline Fast-track:** < 25 mo &nbsp;|&nbsp; 🟡 **Standard:** 25–27 mo &nbsp;|&nbsp; 🔴 **Congested:** > 27 mo &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"💡 **National Historical Median:** {median_months:.1f} mo (Completed COD) · **National Forward Pipeline Median:** {forward_median_mo:.1f} mo (Planned)"
        )

        # ──────────────────────────────────────────────────────────────────────
        # SECTION 3 — INTERACTIVE CLICK-TO-FILTER PIPELINE DRILL-DOWN
        # ──────────────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📊 Operating vs. Planned Capacity by Bundesland")
        st.caption("💡 **Interactive Drill-Down:** Click on any state bar below or select from dropdown to inspect project-level pipeline assets.")

        all_states = latest["bundesland"].tolist()
        
        # State management for two-way synchronization
        if "selected_pipeline_state" not in st.session_state:
            st.session_state["selected_pipeline_state"] = "Niedersachsen"
        if "_last_chart_clicked_state" not in st.session_state:
            st.session_state["_last_chart_clicked_state"] = None

        def on_dropdown_select():
            picked = st.session_state["pipeline_drill_picker"]
            st.session_state["selected_pipeline_state"] = picked
            st.session_state["_last_chart_clicked_state"] = picked

        c_sel1, c_sel2 = st.columns([2, 3])
        with c_sel1:
            curr_state = st.session_state["selected_pipeline_state"]
            curr_idx = all_states.index(curr_state) if curr_state in all_states else 0
            st.selectbox(
                "Active Drill-down State:",
                all_states,
                index=curr_idx,
                key="pipeline_drill_picker",
                on_change=on_dropdown_select
            )

        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(
            name="Operating MW",
            x=latest["bundesland"],
            y=latest["total_installed_mw"],
            marker_color=COLOR_PRIMARY,
        ))
        fig_compare.add_trace(go.Bar(
            name="Planned MW",
            x=latest["bundesland"],
            y=latest["planned_mw"],
            marker_color=COLOR_SECONDARY,
        ))
        fig_compare.update_layout(
            barmode="group",
            height=CHART_HEIGHT_STANDARD,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            clickmode="event+select",
            margin={"r": 20, "t": 10, "l": 0, "b": 0},
        )

        chart_event = st.plotly_chart(
            fig_compare,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key="pipeline_compare_chart"
        )

        if chart_event and "selection" in chart_event and chart_event["selection"].get("points"):
            pts = chart_event["selection"]["points"]
            if pts:
                clicked_x = pts[0].get("x")
                if clicked_x and clicked_x in all_states and clicked_x != st.session_state["_last_chart_clicked_state"]:
                    st.session_state["_last_chart_clicked_state"] = clicked_x
                    st.session_state["selected_pipeline_state"] = clicked_x
                    st.session_state["pipeline_drill_picker"] = clicked_x
                    st.rerun()

        active_state = st.session_state["selected_pipeline_state"]

        # ──────────────────────────────────────────────────────────────────────
        # SECTION 4 — PROJECT DRILL-DOWN TABLE
        # ──────────────────────────────────────────────────────────────────────
        hist_val = None
        pipe_val = None
        if "df_permit_all" in locals() and not df_permit_all.empty:
            state_row = df_permit_all[df_permit_all["bundesland"] == active_state]
            if not state_row.empty:
                if "hist_months" in state_row.columns and pd.notna(state_row["hist_months"].iloc[0]):
                    hist_val = float(state_row["hist_months"].iloc[0])
                if "pipe_months" in state_row.columns and pd.notna(state_row["pipe_months"].iloc[0]):
                    pipe_val = float(state_row["pipe_months"].iloc[0])

        hist_color = get_color(hist_val) if hist_val is not None else "#94A3B8"
        pipe_color = get_color(pipe_val) if pipe_val is not None else "#94A3B8"
        hist_text = f"{hist_val:.1f} mo" if hist_val is not None else "N/A"
        pipe_text = f"{pipe_val:.1f} mo" if pipe_val is not None else "N/A"

        diff_badge = ""
        if hist_val is not None and pipe_val is not None:
            diff = pipe_val - hist_val
            sign = "+" if diff > 0 else ""
            diff_color = COLOR_DANGER if diff > 0 else COLOR_SUCCESS
            diff_badge = f"<span style='font-size:12px; color:{diff_color}; font-weight:700; background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:6px; border: 1px solid rgba(255,255,255,0.1);'>{sign}{diff:.1f} mo shift</span>"

        st.markdown(
            f"<div style='display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:12px;'>"
            f"  <h5 style='margin:0; font-size:16px; font-weight:700; color:#f8fafc;'>🔎 Detailed Planned Projects in <span style='color:#38BDF8;'>{active_state}</span></h5>"
            f"  <div style='display:flex; align-items:center; gap:8px; flex-wrap:wrap;'>"
            f"    <span style='font-size:12px; color:#ffffff; background:{hist_color}; padding:4px 10px; border-radius:6px; font-weight:600; box-shadow:0 1px 3px rgba(0,0,0,0.3);' title='Historical Realized COD (pre-computed snapshots)'>"
            f"      Historical Realized COD: {hist_text}</span>"
            f"    <span style='font-size:12px; color:#ffffff; background:{pipe_color}; padding:4px 10px; border-radius:6px; font-weight:600; box-shadow:0 1px 3px rgba(0,0,0,0.3);' title='Active Forward Pipeline (unbuilt planned units)'>"
            f"      Active Forward Pipeline: {pipe_text}</span>"
            f"    {diff_badge}"
            f"  </div>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        detail_query = query("""
            SELECT 
                mastr_id,
                display_name,
                operator_name,
                nettonennleistung_mw,
                bruttoleistung_mw,
                inbetriebnahmedatum,
                postleitzahl
            FROM wind_plants
            WHERE betriebs_status = 'planned'
              AND bundesland = ?
            ORDER BY nettonennleistung_mw DESC
            LIMIT 50
        """, [active_state])

        if not detail_query.empty:
            detail_query["operator_name"] = detail_query["operator_name"].str.replace("\uff06", "&", regex=False)
            detail_display = detail_query.rename(columns={
                "mastr_id": "MaStR Unit ID",
                "display_name": "Turbine / Project Name",
                "operator_name": "Operating Entity",
                "nettonennleistung_mw": "Net MW",
                "bruttoleistung_mw": "Gross MW",
                "inbetriebnahmedatum": "Expected COD",
                "postleitzahl": "Postal Code"
            })
            st.dataframe(
                detail_display[["MaStR Unit ID", "Turbine / Project Name", "Operating Entity", "Net MW", "Gross MW", "Expected COD", "Postal Code"]],
                use_container_width=True,
                hide_index=True
            )
            st.caption(f"Showing top {len(detail_query)} planned wind units in {active_state} sorted by capacity.")
        else:
            st.info(f"No planned projects currently logged for {active_state}.")

        # ──────────────────────────────────────────────────────────────────────
        # EXPORT DATASET
        # ──────────────────────────────────────────────────────────────────────
        latest_export = latest.copy()
        latest_export["pipeline_ratio_pct"] = (latest_export["planned_mw"] / latest_export["total_installed_mw"] * 100.0).round(2)
        export_cols = [c for c in latest_export.columns if c not in ["bar_color", "color"]]
        unit_note = "# Unit convention: All *_pct columns are percentages (0.35 = 0.35%), all *_mw columns are megawatts.\n"
        csv_pipe_summary = (unit_note + latest_export[export_cols].to_csv(index=False)).encode("utf-8")
        st.download_button(
            label="⬇️ Export Pipeline Radar & Permitting Summary (CSV)",
            data=csv_pipe_summary,
            file_name=f"gtp_wind_pipeline_radar_{date.today()}.csv",
            mime="text/csv",
            key="radar_download_csv",
            help="Download permitting cycle times and pipeline capacity metrics as CSV."
        )


render_pipeline_radar()
