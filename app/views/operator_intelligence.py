"""
app/views/operator_intelligence.py
Operator Intelligence & Repowering Radar (formerly Q3 Operators).
Corporate market concentration analysis, parent utility rollups, and
statutory 20-year EEG merchant repowering exposure screener.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os
from datetime import date

from app.utils.db import query, get_latest_snapshot_date
from app.utils.operators import compute_leaderboards, map_to_parent_company
from app.utils.theme import (
    render_page_header,
    render_kpi_card,
    render_html,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_BORDER,
    CHART_HEIGHT_STANDARD,
    CHART_HEIGHT_TALL
)


def render_operator_intelligence():
    render_page_header(
        title="🏭 Operator Intelligence & Repowering Radar",
        subtitle="Who are the true asset-owning parent utilities behind thousands of project SPVs? Which portfolios face merchant price risk as 20-year EEG tariffs expire?",
        data_source="Marktstammdatenregister (MaStR), Bundesnetzagentur",
        confidence_tier="Tier 1 — Official Registry + Corporate Rollup Heuristics",
        snapshot_date=get_latest_snapshot_date()
    )

    # Load operating wind plants for dynamic evaluation
    df_op = query("""
        SELECT 
            mastr_id,
            operator_name,
            operator_mastr_id,
            operator_name_resolved,
            nettonennleistung_mw,
            bruttoleistung_mw,
            bundesland,
            inbetriebnahmedatum,
            postleitzahl
        FROM wind_plants
        WHERE betriebs_status = 'operating'
    """)

    if df_op.empty:
        st.error("Operating wind plant data unavailable. Please run pipeline sync.")
        return

    # Calculate authoritative resolution stats
    total_operating = len(df_op)
    resolved_operating = int(df_op["operator_name_resolved"].sum())
    res_rate_pct = (resolved_operating / total_operating * 100.0) if total_operating > 0 else 93.0

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 0 — EXECUTIVE SUMMARY & REPOWERING CLIFF
    # ──────────────────────────────────────────────────────────────────────────
    cliff_cutoff_20 = date.today().year - 20
    cliff_plants_20 = df_op[df_op["inbetriebnahmedatum"].dt.year <= cliff_cutoff_20]
    cliff_gw = cliff_plants_20["nettonennleistung_mw"].sum() / 1000.0
    cliff_units = len(cliff_plants_20)

    # 18-20 year watch list
    cliff_plants_18_20 = df_op[
        (df_op["inbetriebnahmedatum"].dt.year > cliff_cutoff_20) & 
        (df_op["inbetriebnahmedatum"].dt.year <= date.today().year - 18)
    ]
    watch_gw = cliff_plants_18_20["nettonennleistung_mw"].sum() / 1000.0
    watch_units = len(cliff_plants_18_20)

    render_html(
        f"""
        <div style="
            background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
            border-left: 5px solid {COLOR_WARNING};
            border-radius: 12px;
            padding: 22px 26px;
            margin-bottom: 24px;
            color: #ffffff;
        ">
            <div style="color:#fde68a; font-size:12px; letter-spacing:1.5px; text-transform:uppercase; font-weight:700; margin-bottom:6px;">
                Executive Due Diligence · Statutory Subsidy Expiration (§ 25 EEG)
            </div>
            <div style="color:#ffffff; font-size:20px; font-weight:700; line-height:1.4; margin-bottom:8px;">
                Germany has <span style="color:#fbbf24;">{cliff_gw:,.1f} GW</span> ({cliff_units:,} turbines)
                fully past their 20-year statutory feed-in tariff, with an additional
                <span style="color:#fbbf24;">{watch_gw:,.1f} GW</span> ({watch_units:,} turbines) approaching expiration within 24 months.
            </div>
            <div style="color:#bfdbfe; font-size:13px; line-height:1.5;">
                Under § 25 EEG, German wind turbines receive guaranteed statutory compensation for exactly 20 calendar years plus the commissioning year.
                Turbines commissioned in {cliff_cutoff_20} or earlier have exhausted this subsidy and operate purely on wholesale market prices or corporate PPAs,
                creating an immediate repowering or acquisition opportunity.
            </div>
        </div>
        """
    )

    # ──────────────────────────────────────────────────────────────────────────
    # UNIFIED KPI METRIC CARDS
    # ──────────────────────────────────────────────────────────────────────────
    total_mw = df_op["nettonennleistung_mw"].sum()
    distinct_operators = df_op["operator_name"].nunique()

    top20_entities, top20_parents, summary_stats = compute_leaderboards(df_op)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            render_kpi_card(
                "Operating Fleet Capacity",
                f"{total_mw / 1000.0:,.1f} GW",
                subtext=f"{total_operating:,} operating wind turbines",
                delta="Tier 1 MaStR",
                delta_type="pos",
                border_left_color=COLOR_PRIMARY
            ),
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            render_kpi_card(
                "Operator Resolution Rate",
                f"{res_rate_pct:.1f}%",
                subtext=f"{resolved_operating:,} of {total_operating:,} operating turbines",
                delta="Reconciled",
                delta_type="pos",
                border_left_color=COLOR_SUCCESS
            ),
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            render_kpi_card(
                "Post-EEG Repowering Pool",
                f"{cliff_gw:,.1f} GW",
                subtext=f"{cliff_units:,} turbines > 20 yrs old",
                delta=f"{(cliff_gw / (total_mw/1000.0))*100:.1f}% of fleet",
                delta_type="warn",
                border_left_color=COLOR_WARNING
            ),
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            render_kpi_card(
                "Distinct Registered Entities",
                f"{distinct_operators:,}",
                subtext="Independent SPVs & operating entities",
                delta="High fragmentation",
                delta_type="neutral",
                border_left_color=COLOR_SECONDARY
            ),
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 1 — VIEW TOGGLE: LEGAL ENTITY VS PARENT ROLLUP
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("### 📊 Market Concentration & Operator Leaderboard")

    col_toggle, col_space = st.columns([2, 1])
    with col_toggle:
        view_mode = st.radio(
            "View by:",
            ["Parent Company Group", "Registered Legal Entity"],
            index=0,  # Default to Parent Company Group as required
            horizontal=True,
            key="operator_view_mode_toggle",
            help="Toggle between consolidated utility parent brand rollups and registered individual project SPV legal entities."
        )

    st.caption(
        "ℹ️ **Methodology & Heuristic Disclosure:** *Parent Company Group* aggregates project-level SPVs "
        "using deterministic substring pattern matching across 28 recognized German utility, IPP, and municipal developer brand names. "
        "It is designed for institutional market concentration screening, not as an authoritative court-registered ownership record. "
        "Unregistered individual farmers/landowners (redacted under BDSG/GDPR) remain tagged as *Unregistered / Private Operator (ABR)*."
    )

    # Market Share Comparison Box
    render_html(
        f"""
        <div style="background:#f8fafc; border:1px solid {COLOR_BORDER}; border-radius:10px; padding:14px 18px; margin: 12px 0 20px 0; font-size:13px; color:#334155;">
            <b>Market Concentration Comparison (Top 5 Share):</b><br>
            • <b>Individual Legal Entities:</b> Top 5 hold <b>{summary_stats['top5_entity_mw']:,.1f} MW</b> ({summary_stats['top5_entity_share_pct']:.2f}% of national operating fleet).<br>
            • <b>Parent Company Groups:</b> Top 5 hold <b>{summary_stats['top5_parent_mw']:,.1f} MW</b> ({summary_stats['top5_parent_share_pct']:.2f}% of national operating fleet).<br>
            • <b>EnBW vs. RWE Structural Impact:</b> Consolidated EnBW Group (<b>{summary_stats['enbw_parent_mw']:,.1f} MW</b> across 5 subsidiaries) 
            <b>exceeds</b> RWE's single largest entity (<b>{summary_stats['rwe_single_mw']:,.1f} MW</b>), 
            but consolidated RWE Group retains the overall #1 market position with <b>{summary_stats['rwe_parent_mw']:,.1f} MW</b> across 11 subsidiaries.
        </div>
        """
    )

    if view_mode == "Parent Company Group":
        display_df = top20_parents.copy()
        fig_bar = px.bar(
            display_df,
            x="total_mw",
            y="parent_group",
            orientation="h",
            text="total_mw",
            color="total_mw",
            color_continuous_scale="Blues",
            labels={"total_mw": "Operating MW", "parent_group": "Parent Utility / Developer Group"},
        )
        fig_bar.update_traces(texttemplate="%{text:,.0f} MW", textposition="outside")
        fig_bar.update_layout(
            height=CHART_HEIGHT_STANDARD,
            margin={"r": 35, "t": 10, "l": 0, "b": 0},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Table display
        table_view = display_df.rename(columns={
            "rank": "Rank",
            "parent_group": "Parent Group",
            "total_mw": "Total Operating MW",
            "unit_count": "Turbines",
            "subsidiary_count": "Mapped SPVs",
            "market_share_pct": "Market Share %",
            "state_count": "States Active"
        })
        table_view["Total Operating MW"] = table_view["Total Operating MW"].apply(lambda x: f"{x:,.1f}")
        table_view["Market Share %"] = table_view["Market Share %"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(
            table_view[["Rank", "Parent Group", "Total Operating MW", "Market Share %", "Turbines", "Mapped SPVs", "States Active"]],
            use_container_width=True,
            hide_index=True
        )

    else:
        display_df = top20_entities.copy()
        fig_bar = px.bar(
            display_df,
            x="total_mw",
            y="operator_display",
            orientation="h",
            text="total_mw",
            color="total_mw",
            color_continuous_scale="Blues",
            labels={"total_mw": "Operating MW", "operator_display": "Registered Operating Legal Entity"},
        )
        fig_bar.update_traces(texttemplate="%{text:,.0f} MW", textposition="outside")
        fig_bar.update_layout(
            height=CHART_HEIGHT_STANDARD,
            margin={"r": 35, "t": 10, "l": 0, "b": 0},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        table_view = display_df.rename(columns={
            "rank": "Rank",
            "operator_display": "Registered Legal Entity",
            "total_mw": "Total Operating MW",
            "unit_count": "Turbines",
            "market_share_pct": "Market Share %",
            "state_count": "States Active"
        })
        table_view["Total Operating MW"] = table_view["Total Operating MW"].apply(lambda x: f"{x:,.1f}")
        table_view["Market Share %"] = table_view["Market Share %"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(
            table_view[["Rank", "Registered Legal Entity", "Total Operating MW", "Market Share %", "Turbines", "States Active"]],
            use_container_width=True,
            hide_index=True
        )

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 2 — SEARCHABLE OPERATOR LOOKUP BOX
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Searchable Operator & Portfolio Due Diligence")
    st.caption("Inspect any individual operator entity or corporate group across Germany:")

    all_operators_sorted = sorted(df_op["operator_name"].dropna().unique().tolist())
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        selected_lookup = st.selectbox(
            "Select or type an Operator Name to inspect:",
            ["RWE Wind Onshore & PV Deutschland GmbH", "EnBW Windkraftprojekte GmbH", "Alterric Deutschland GmbH"] + [o for o in all_operators_sorted if o not in ["RWE Wind Onshore & PV Deutschland GmbH", "EnBW Windkraftprojekte GmbH", "Alterric Deutschland GmbH"]],
            key="operator_lookup_search"
        )

    if selected_lookup:
        op_assets = df_op[df_op["operator_name"] == selected_lookup].copy()
        op_mw = op_assets["nettonennleistung_mw"].sum()
        op_units = len(op_assets)
        op_parent = map_to_parent_company(selected_lookup)
        op_cliff_units = len(op_assets[op_assets["inbetriebnahmedatum"].dt.year <= cliff_cutoff_20])
        op_cliff_mw = op_assets[op_assets["inbetriebnahmedatum"].dt.year <= cliff_cutoff_20]["nettonennleistung_mw"].sum()

        l1, l2, l3, l4 = st.columns(4)
        with l1:
            st.markdown(
                render_kpi_card(
                    "Selected Entity Fleet",
                    f"{op_mw:,.1f} MW",
                    subtext=f"{op_units} operating turbines",
                    border_left_color=COLOR_PRIMARY
                ),
                unsafe_allow_html=True
            )
        with l2:
            st.markdown(
                render_kpi_card(
                    "Heuristic Parent Group",
                    op_parent,
                    subtext="Consolidated ownership rollup",
                    border_left_color=COLOR_SECONDARY
                ),
                unsafe_allow_html=True
            )
        with l3:
            st.markdown(
                render_kpi_card(
                    "Post-EEG Exposure (>20y)",
                    f"{op_cliff_mw:,.1f} MW",
                    subtext=f"{op_cliff_units} turbines past subsidy",
                    delta_type="warn",
                    border_left_color=COLOR_WARNING
                ),
                unsafe_allow_html=True
            )
        with l4:
            states_active = ", ".join(op_assets["bundesland"].unique().tolist())
            st.markdown(
                render_kpi_card(
                    "Operating Geography",
                    f"{op_assets['bundesland'].nunique()} States",
                    subtext=states_active[:40] + ("..." if len(states_active) > 40 else ""),
                    border_left_color=COLOR_SUCCESS
                ),
                unsafe_allow_html=True
            )

        with st.expander(f"📋 View all {op_units} turbine assets for {selected_lookup}"):
            display_assets = op_assets.rename(columns={
                "mastr_id": "MaStR Unit ID",
                "nettonennleistung_mw": "Net MW",
                "bundesland": "State",
                "postleitzahl": "Postal Code",
                "inbetriebnahmedatum": "Commissioning Date"
            })
            st.dataframe(
                display_assets[["MaStR Unit ID", "Net MW", "State", "Postal Code", "Commissioning Date"]],
                use_container_width=True,
                hide_index=True
            )

    # ──────────────────────────────────────────────────────────────────────────
    # EXPORT DATASET
    # ──────────────────────────────────────────────────────────────────────────
    unit_note = "# Unit convention: All *_pct columns are percentages (0.35 = 0.35%), all *_mw columns are megawatts.\n"
    csv_top20 = (unit_note + top20_parents.to_csv(index=False)).encode("utf-8")
    st.download_button(
        label="⬇️ Export Parent Company Rollup Leaderboard (CSV)",
        data=csv_top20,
        file_name=f"gtp_wind_parent_company_rollup_{date.today()}.csv",
        mime="text/csv",
        key="export_parent_company_csv",
        help="Download Top 20 parent company groups and market shares as CSV."
    )


render_operator_intelligence()
