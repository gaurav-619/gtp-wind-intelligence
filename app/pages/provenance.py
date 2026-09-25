"""
app/pages/provenance.py
Data provenance page: source registry, Tier 2 claims with
verify button, pipeline run log, and data gaps.
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from app.utils.db import query, get_source_registry, get_pipeline_status, verify_claim

st.set_page_config(page_title="Data Provenance", layout="wide")
st.title("📋 Data Provenance")
st.caption(
    "Every number in this platform traces to a named source. "
    "This page shows what data exists, where it came from, "
    "and what still needs to be built."
)

# --------------------------------------------------------------------------
# Section 1: Source registry
# --------------------------------------------------------------------------

st.subheader("Source Registry")
sources = get_source_registry()

if not sources.empty:
    def style_source_type(val):
        if val == "official":
            return "background-color: #D1FAE5; color: #065F46"
        elif val == "company_claim":
            return "background-color: #FEF3C7; color: #92400E"
        return "background-color: #F3F4F6; color: #374151"

    styled = sources.style.map(style_source_type, subset=["source_type"])
    st.dataframe(styled, use_container_width=True)
else:
    st.info("No sources registered. Run the pipeline first.")

st.divider()

# --------------------------------------------------------------------------
# Section 2: Tier 2 extracted claims
# --------------------------------------------------------------------------

st.subheader("Extracted Claims (Tier 2 — Company Sources)")
st.caption(
    "Values extracted from German company press releases. "
    "All require human verification before citing in client work."
)

claims = query("""
    SELECT claim_id, entity, metric, period, value, unit,
           source_sentence_de, source_sentence_en,
           document_url, extracted_at, extraction_model,
           human_verified, confidence_score
    FROM extracted_claims
    ORDER BY human_verified ASC, extracted_at DESC
""")

if claims.empty:
    st.info(
        "No Tier 2 claims extracted yet. "
        "Run the Tier 2 pipeline to process press releases."
    )
else:
    unverified = claims[claims["human_verified"] == False]
    verified = claims[claims["human_verified"] == True]

    col1, col2 = st.columns(2)
    col1.metric("Unverified claims", len(unverified),
                delta="Need review", delta_color="inverse")
    col2.metric("Verified claims", len(verified),
                delta="Ready to cite", delta_color="normal")

    if not unverified.empty:
        st.markdown("**Unverified claims — review before citing:**")

        for _, row in unverified.iterrows():
            with st.expander(
                f"🟡 {row['entity']} · {row['metric']} · "
                f"{row['period']} · {row['value']} {row['unit']}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🇩🇪 Original German:**")
                    st.text(row["source_sentence_de"] or "N/A")
                with col2:
                    st.markdown("**🇬🇧 English translation:**")
                    st.text(row["source_sentence_en"] or "N/A")

                st.caption(f"Source: {row['document_url']}")
                confidence = row['confidence_score'] if row['confidence_score'] else 0
                st.caption(
                    f"Model: {row['extraction_model']} · "
                    f"Confidence: {confidence:.2f}"
                )

                if st.button("✓ Mark as verified",
                             key=f"verify_{row['claim_id']}"):
                    verify_claim(row["claim_id"])
                    st.success("Marked as verified")
                    st.rerun()

    if not verified.empty:
        st.markdown("**Verified claims — cleared for use:**")
        for _, row in verified.iterrows():
            st.success(
                f"✓ {row['entity']} · {row['metric']} · "
                f"{row['period']}: {row['value']} {row['unit']}"
            )

st.divider()

# --------------------------------------------------------------------------
# Section 3: Pipeline run log
# --------------------------------------------------------------------------

st.subheader("Pipeline Run Log")
pipeline_log = get_pipeline_status()

if not pipeline_log.empty:
    def style_status(val):
        if val == "success":
            return "color: green"
        elif val == "failed":
            return "color: red"
        return ""

    styled_log = pipeline_log.style.map(style_status, subset=["status"])
    st.dataframe(styled_log, use_container_width=True)
else:
    st.info("No pipeline runs logged yet.")

st.divider()

# --------------------------------------------------------------------------
# Section 4: Data gaps
# --------------------------------------------------------------------------

st.subheader("What is not yet in this platform")
st.markdown("""
| Missing data | What it would add | Source needed | Status |
|---|---|---|---|
| OEM order intake (live) | Quarterly order intake for Vestas, Enercon | Tier 2 company press releases | Nordex only for now |
| BESS co-location with wind | Which wind sites have battery storage | MaStR BESS data | Available to build |
| Operator portfolio analysis | Who owns what and where | MaStR Anlagenbetreiber | Available to build |
| Project-level financials | Transaction values, equity/debt split | Licensed data (Wood Mackenzie, Bloomberg NEF) | Requires data purchase |
| Competitor benchmarking | Client vs market comparison | MaStR + Tier 2 combined | Available to build |
""")
