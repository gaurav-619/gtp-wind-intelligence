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
from app.utils.db import (
    query, get_source_registry, get_pipeline_status, verify_claim,
    get_legal_citations, add_or_verify_legal_citation
)
from pipeline.extract_claims import (
    detect_legal_citations, validate_legal_citation, verify_and_annotate_text_citations
)

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
# Section 3: Legal & Regulatory Citation Audit
# --------------------------------------------------------------------------

st.subheader("⚖️ Legal Citation Audit (Statutory Safeguard Layer)")
st.caption(
    "Specific statutory citations (e.g. § 3 MaStRV, § 4 EEG 2023, § 4 BImSchG) "
    "are treated like Tier 2 claims. Only paragraphs verified against "
    "gesetze-im-internet.de are cleared as fact; unmatched references are flagged."
)

legal_df = get_legal_citations()

col_l1, col_l2 = st.columns([1, 1])
with col_l1:
    st.metric("Verified Statutory Provisions", len(legal_df),
              help="Provisions loaded from official government sources (gesetze-im-internet.de)")
with col_l2:
    st.metric("Source Authority", "gesetze-im-internet.de",
              help="Federal Ministry of Justice official portal")

with st.expander("📚 View All Authoritative Statutory Provisions in Database", expanded=False):
    if not legal_df.empty:
        st.dataframe(
            legal_df[["law_name", "paragraph", "topic", "source_url", "verified_at"]],
            use_container_width=True
        )
    else:
        st.warning("No legal citations seeded. Run pipeline.load to initialize.")

# Interactive Text Scanner
st.markdown("##### Scan Text for Legal Citations")
sample_default = (
    "Gemäß § 4 EEG 2023 soll der Ausbaupfad für Windenergie an Land 115 GW im Jahr 2030 erreichen. "
    "Für die Genehmigung gilt § 4 BImSchG sowie § 16b BImSchG für Repowering. "
    "Die Registrierung erfolgt nach § 3 MaStRV. "
    "Dagegen ist § 99 FantasieGesetz eine nicht verifizierte Norm."
)
input_text = st.text_area(
    "Paste report excerpt or claim to verify legal citations:",
    value=sample_default,
    height=100
)

if st.button("🔍 Scan & Verify Legal Citations"):
    annotated, scan_results, n_unverified = verify_and_annotate_text_citations(input_text)
    
    if not scan_results:
        st.info("No legal citations detected in this text.")
    else:
        st.markdown(f"**Found {len(scan_results)} citations ({n_unverified} unverified):**")
        
        for item in scan_results:
            cit_txt = item["citation_text"]
            if item["is_verified"]:
                rec = item["matched_record"]
                st.success(
                    f"🟢 **[VERIFIED]** `{cit_txt}` $\\rightarrow$ **{rec['law_name']} {rec['paragraph']}** "
                    f"(*{rec['topic']}*) · [Official Law Text]({rec['source_url']}) (Verified: {rec['verified_at']})"
                )
            else:
                st.error(
                    f"🔴 **[UNVERIFIED - NOT FOUND]** `{cit_txt}` — Not found in legal_citations table! "
                    "Must be human-verified before citing in client materials."
                )

        if n_unverified > 0:
            st.markdown("**Annotated Text with Safeguard Flags:**")
            st.code(annotated, language="markdown")

st.markdown("##### Manual Legal Citation Verification (Human-in-the-Loop)")
with st.expander("➕ Review & Add Confirmed Legal Citation to Database", expanded=False):
    st.caption("Reviewers must confirm the statutory paragraph and paste the verified source_url from gesetze-im-internet.de.")
    with st.form("add_legal_citation_form"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            form_law = st.text_input("Law Name (e.g. MaStRV, EEG 2023, BImSchG, WindBG)")
            form_para = st.text_input("Paragraph (e.g. § 16b, § 5)")
            form_topic = st.text_input("Topic / Headline (e.g. Repowering Genehmigung)")
        with col_f2:
            form_url = st.text_input("Confirmed Source URL (Required from gesetze-im-internet.de)",
                                     placeholder="https://www.gesetze-im-internet.de/...")
            form_text = st.text_area("Official German Text (Verbatim)", height=95)

        submit_cit = st.form_submit_button("✓ Confirm & Save to legal_citations")
        if submit_cit:
            if not form_law or not form_para or not form_url.strip():
                st.error("Law name, paragraph, and confirmed source_url are required.")
            elif not form_url.startswith("http"):
                st.error("Please provide a valid source URL starting with https://")
            else:
                cit_id = f"{form_law.lower().replace(' ', '_')}_{form_para.lower().replace('§', 'p').replace(' ', '').replace('.', '')}"
                add_or_verify_legal_citation(
                    cit_id, form_law.strip(), form_para.strip(),
                    form_topic.strip() or "Gesetzliche Regelung",
                    form_text.strip() or "Vorschrift bestätigt.",
                    form_url.strip()
                )
                st.success(f"✓ Saved and verified: {form_law} {form_para}")
                st.rerun()

st.divider()

# --------------------------------------------------------------------------
# Section 4: Pipeline run log
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
