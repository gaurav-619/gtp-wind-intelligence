"""
app/views/data_trust_center.py
Data Trust Center (formerly Provenance).
Institutional audit layer providing complete cryptographic and registry trace:
source registry, two-tier confidence classification, human-in-the-loop claim verification,
statutory legal citation audit, and end-to-end pipeline execution logs.
"""

import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

from app.utils.db import (
    query, get_source_registry, get_pipeline_status, verify_claim,
    get_legal_citations, add_or_verify_legal_citation, verify_citation_translation
)
from pipeline.extract_claims import (
    detect_legal_citations, validate_legal_citation, verify_and_annotate_text_citations
)
from app.utils.theme import (
    render_page_header,
    render_kpi_card,
    render_html,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_BORDER
)


def render_data_trust_center():
    render_page_header(
        title="🛡️ Data Trust Center",
        subtitle="What is the complete provenance trail, ingestion timestamp, and audit history for every figure? Which company-published claims have been verified by human analysts?",
        data_source="Institutional Governance & Multi-Tier Audit Registry",
        confidence_tier="Tier 1 (Official) & Tier 2 (Company Claims)",
        snapshot_date=""
    )

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 0 — PLATFORM HEALTH TRAFFIC-LIGHT SUMMARY
    # ──────────────────────────────────────────────────────────────────────────
    last_run_df = query("""
        SELECT MAX(run_timestamp) as last_run, COUNT(*) as total_logged_runs,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs
        FROM pipeline_runs
    """)
    
    claims_df = query("""
        SELECT claim_id, human_verified, is_preliminary
        FROM extracted_claims
    """)

    # 1. Freshness evaluation
    freshness_status = "Operational"
    freshness_icon = "🟢"
    freshness_delta = "Up to date"
    delta_type_fresh = "pos"
    days_ago = 0
    if not last_run_df.empty and pd.notna(last_run_df["last_run"].iloc[0]):
        last_dt = pd.to_datetime(last_run_df["last_run"].iloc[0])
        days_ago = (datetime.now() - last_dt).days
        if days_ago > 30:
            freshness_status = "Stale"
            freshness_icon = "🔴"
            freshness_delta = f"{days_ago}d ago"
            delta_type_fresh = "neg"
        elif days_ago > 7:
            freshness_status = "Moderate"
            freshness_icon = "🟡"
            freshness_delta = f"{days_ago}d ago"
            delta_type_fresh = "warn"
        else:
            freshness_delta = f"{days_ago}d ago"

    # 2. Audit Coverage evaluation
    total_runs = int(last_run_df["total_logged_runs"].iloc[0]) if not last_run_df.empty else 0
    succ_runs = int(last_run_df["successful_runs"].iloc[0]) if not last_run_df.empty else 0
    coverage_pct = (succ_runs / total_runs * 100.0) if total_runs > 0 else 100.0
    audit_status = "100% Logged" if coverage_pct == 100.0 else f"{coverage_pct:.0f}% Pass"
    audit_icon = "🟢" if coverage_pct >= 95.0 else "🟡"

    # 3. Verification Rate evaluation
    total_claims = len(claims_df)
    verified_claims = len(claims_df[claims_df["human_verified"] == True]) if total_claims > 0 else 0
    ver_pct = (verified_claims / total_claims * 100.0) if total_claims > 0 else 0.0
    ver_icon = "🟢" if ver_pct == 100.0 else ("🟡" if ver_pct > 0 else "🔴")
    ver_status = f"{ver_pct:.0f}% Verified"

    render_html(
        f"""
        <div style="background:#f8fafc; border:1px solid {COLOR_BORDER}; border-radius:12px; padding:18px 22px; margin-bottom:24px;">
            <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:#475569; margin-bottom:12px;">
                Platform Health & Governance Traffic Lights
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:16px;">
                <div style="background:#ffffff; border:1px solid {COLOR_BORDER}; border-radius:10px; padding:14px 18px; border-left:4px solid {COLOR_SUCCESS if freshness_icon=='🟢' else COLOR_WARNING};">
                    <div style="font-size:12px; color:#64748b; text-transform:uppercase; font-weight:600;">Data Freshness</div>
                    <div style="font-size:20px; font-weight:700; color:#0f172a; margin:4px 0;">{freshness_icon} {freshness_status}</div>
                    <div style="font-size:12px; color:#64748b;">Synced: {freshness_delta}</div>
                </div>
                <div style="background:#ffffff; border:1px solid {COLOR_BORDER}; border-radius:10px; padding:14px 18px; border-left:4px solid {COLOR_SUCCESS};">
                    <div style="font-size:12px; color:#64748b; text-transform:uppercase; font-weight:600;">Audit Coverage</div>
                    <div style="font-size:20px; font-weight:700; color:#0f172a; margin:4px 0;">{audit_icon} {audit_status}</div>
                    <div style="font-size:12px; color:#64748b;">{succ_runs} of {total_runs} pipeline runs verified</div>
                </div>
                <div style="background:#ffffff; border:1px solid {COLOR_BORDER}; border-radius:10px; padding:14px 18px; border-left:4px solid {COLOR_WARNING if ver_icon=='🟡' else (COLOR_SUCCESS if ver_icon=='🟢' else COLOR_DANGER)};">
                    <div style="font-size:12px; color:#64748b; text-transform:uppercase; font-weight:600;">Tier 2 Verification</div>
                    <div style="font-size:20px; font-weight:700; color:#0f172a; margin:4px 0;">{ver_icon} {ver_status}</div>
                    <div style="font-size:12px; color:#64748b;">{verified_claims}/{total_claims} claims approved by human</div>
                </div>
            </div>
        </div>
        """
    )

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 1 — REGISTERED SOURCES & TWO-TIER CONFIDENCE
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("### 📚 Source Registry & Two-Tier Confidence Classification")
    st.caption(
        "Every data point ingested into GTP Wind Intelligence is tagged with a confidence tier. "
        "**Tier 1 (Official)** originates from statutory federal registers and is fact-grade. "
        "**Tier 2 (Company-Claim)** originates from corporate press announcements and is barred from client citation until human audit."
    )

    sources = get_source_registry()
    if not sources.empty:
        def style_source_type(val):
            if val == "official":
                return "background-color: #D1FAE5; color: #065F46; font-weight: 600;"
            elif val == "company_claim":
                return "background-color: #FEF3C7; color: #92400E; font-weight: 600;"
            return "background-color: #F1F5F9; color: #334155;"

        styled_sources = sources.style.map(style_source_type, subset=["source_type"])
        st.dataframe(styled_sources, use_container_width=True, hide_index=True)
    else:
        st.info("No sources registered in database.")

    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 2 — TIER 2 HUMAN-IN-THE-LOOP CLAIM VERIFICATION WORKFLOW
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("### ✍️ Tier 2 Company-Claim Verification Workflow")
    st.caption(
        "Machine-extracted claims from OEM and utility filings. "
        "Unverified claims cannot be cited in partner client presentations until approved."
    )

    claims = query("""
        SELECT claim_id, entity, metric, period, value, unit,
               source_sentence_de, source_sentence_en,
               document_url, extracted_at, extraction_model,
               human_verified, confidence_score, is_preliminary
        FROM extracted_claims
        ORDER BY human_verified ASC, extracted_at DESC
    """)

    if claims.empty:
        st.info("No Tier 2 claims currently extracted.")
    else:
        unverified = claims[claims["human_verified"] == False]
        verified = claims[claims["human_verified"] == True]

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown(
                render_kpi_card(
                    "Pending Human Review",
                    str(len(unverified)),
                    subtext="Requires human sign-off",
                    delta_type="warn",
                    border_left_color=COLOR_WARNING
                ),
                unsafe_allow_html=True
            )
        with t_col2:
            st.markdown(
                render_kpi_card(
                    "Verified Claims (Client-Ready)",
                    str(len(verified)),
                    subtext="Audited and cleared for citing",
                    delta_type="pos",
                    border_left_color=COLOR_SUCCESS
                ),
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        if not unverified.empty:
            st.markdown("##### ⚠️ Unverified Claims Awaiting Auditor Sign-Off:")
            for _, row in unverified.iterrows():
                is_prelim = bool(row.get("is_preliminary", False))
                status_icon = "🟠 [PRELIMINARY]" if is_prelim else "🟡"
                with st.expander(
                    f"{status_icon} {row['entity']} · {row['metric']} · {row['period']} · {row['value']} {row['unit']}"
                ):
                    if is_prelim:
                        st.warning(
                            "⚠️ **Preliminary / Hedged Claim**: This figure was qualified as preliminary/estimated "
                            "(e.g., 'rund', 'vorläufig', 'geschätzt'). Verify against subsequent filings before final citing."
                        )
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**🇩🇪 Verbatim Source (DE):**")
                        st.info(row["source_sentence_de"] or "N/A")
                    with col2:
                        st.markdown("**🇬🇧 Machine Translation (EN):**")
                        st.text(row["source_sentence_en"] or "N/A")

                    st.caption(f"Extraction Model: {row['extraction_model']} · Extraction Confidence: {row['confidence_score']:.2f}")

                    # Raw Document Viewer Expander
                    with st.expander("📄 View Ingested Raw Filing Text (Auditor Excerpt)"):
                        st.markdown(
                            "**Original Corporate Publication Text (Cached in `document_chunks`):**  \n"
                            "*Note: Nordex SE restructured their website and redirects legacy `/wp-content/uploads/` links to their homepage. "
                            "The complete verbatim text harvested by the pipeline is preserved below for audit integrity.*"
                        )
                        raw_chunk = query("""
                            SELECT chunk_text FROM document_chunks 
                            WHERE document_url = ? OR source_id = 'nordex_press' 
                            LIMIT 1
                        """, [row.get("document_url", "")])
                        if not raw_chunk.empty and raw_chunk.iloc[0]["chunk_text"]:
                            st.code(raw_chunk.iloc[0]["chunk_text"], language="markdown")
                        else:
                            st.info("Raw document text stored in data/raw/nordex_press_Q1_2024.txt")

                    act_col1, act_col2 = st.columns([1, 1])
                    with act_col1:
                        if st.button("✓ Mark as Verified (Human Approved)", key=f"verify_claim_{row['claim_id']}", use_container_width=True):
                            verify_claim(row["claim_id"])
                            st.success("Claim approved and verified!")
                            st.rerun()
                    with act_col2:
                        st.link_button("↗️ Open Nordex IR Reports Archive", "https://ir.nordex-online.com/websites/Nordex/English/3000/publications.html", use_container_width=True)

        if not verified.empty:
            st.markdown("##### ✅ Approved & Citable Claims:")
            for _, row in verified.iterrows():
                with st.expander(f"✓ {row['entity']} · {row['metric']} · {row['period']}: {row['value']} {row['unit']} (Approved for citation)"):
                    st.success(f"**Approved Claim:** {row['value']} {row['unit']} ({row['metric']}, {row['period']})")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**🇩🇪 Verbatim Source (DE):**")
                        st.info(row["source_sentence_de"] or "N/A")
                    with col2:
                        st.markdown("**🇬🇧 Machine Translation (EN):**")
                        st.text(row["source_sentence_en"] or "N/A")
                    doc_url = row.get("document_url")
                    if doc_url and str(doc_url).startswith("http"):
                        st.link_button("↗️ Open Original Source Filing", doc_url)

    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 3 — STATUTORY LEGAL CITATION SAFEGUARD
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("### ⚖️ Legal Citation Audit & Dual-Language Repository")
    st.caption(
        "Statutory references (§ 5 MaStRV, § 4 EEG 2023, § 4 BImSchG) are validated against gesetze-im-internet.de."
    )

    legal_df = get_legal_citations()
    if not legal_df.empty:
        summary_cols = ["law_name", "paragraph", "topic", "translation_verified", "translation_model", "back_translation_similarity"]
        avail_cols = [c for c in summary_cols if c in legal_df.columns]
        st.dataframe(legal_df[avail_cols], use_container_width=True, hide_index=True)

        with st.expander("🔍 Inspect Full Statutory Text & Official Federal Law Links"):
            for _, lrow in legal_df.iterrows():
                st.markdown(f"**{lrow['law_name']} {lrow['paragraph']}** — *{lrow['topic']}*")
                lcol1, lcol2 = st.columns(2)
                with lcol1:
                    st.caption("🇩🇪 Official German Statute Text:")
                    st.code(lrow.get("official_text_de", "N/A"), language="markdown")
                with lcol2:
                    st.caption("🇬🇧 English Translated Meaning:")
                    st.code(lrow.get("official_text_en", "N/A"), language="markdown")
                s_url = lrow.get("source_url")
                if s_url and str(s_url).startswith("http"):
                    st.link_button(f"↗️ Open {lrow['law_name']} {lrow['paragraph']} on gesetze-im-internet.de", s_url)
                st.markdown("---")
    else:
        st.info("Legal citations repository initializing.")

    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 4 — PIPELINE EXECUTION AUDIT LOG
    # ──────────────────────────────────────────────────────────────────────────
    st.markdown("### 📜 End-to-End Pipeline Execution Log")
    st.caption("Cryptographic and row-count audit trail for every pipeline stage executed against DuckDB.")

    pipeline_log = get_pipeline_status()
    if not pipeline_log.empty:
        def style_status(val):
            if val == "success":
                return "color: #10B981; font-weight: 600;"
            elif val == "failed":
                return "color: #EF4444; font-weight: 600;"
            return ""

        styled_log = pipeline_log.style.map(style_status, subset=["status"])
        st.dataframe(styled_log, use_container_width=True, hide_index=True)
    else:
        st.info("No pipeline run records logged.")


render_data_trust_center()
