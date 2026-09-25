"""
app/main.py
GTP Wind Intelligence - Main landing page.
Question-driven navigation to analysis pages.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.utils.db import get_latest_snapshot_date, query

st.set_page_config(
    page_title="GTP Wind Intelligence",
    page_icon="🌬️",
    layout="wide",
)

st.title("🌬️ GTP Wind Intelligence")
st.subheader("Internal market data platform · Onshore wind Germany")
st.caption(f"Data as of: {get_latest_snapshot_date()}")

st.divider()

# --------------------------------------------------------------------------
# Question cards
# --------------------------------------------------------------------------

questions = [
    {
        "q": "Which Bundesländer have the most installed onshore wind "
             "capacity, and which are growing fastest?",
        "tag": "MaStR · Tier 1 Official · Updated monthly",
        "page": "pages/q1_capacity.py",
        "built": True,
    },
    {
        "q": "How healthy is Germany's onshore wind development pipeline, "
             "and how fast are projects being approved?",
        "tag": "MaStR · Tier 1 Official · Derived metric",
        "page": "pages/q2_pipeline.py",
        "built": True,
    },
    {
        "q": "Who are the dominant operators and where are they? "
             "(transaction due diligence)",
        "tag": "MaStR · Tier 1 · Available to build",
        "page": None,
        "built": False,
    },
    {
        "q": "How is BESS being deployed alongside wind?",
        "tag": "MaStR BESS · Tier 1 · Available to build",
        "page": None,
        "built": False,
    },
    {
        "q": "How does a specific region or operator compare "
             "to the national benchmark?",
        "tag": "MaStR + Press releases · Tier 1 + Tier 2",
        "page": None,
        "built": False,
    },
]

for i, q in enumerate(questions):
    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            if q["built"]:
                st.markdown(f"**{q['q']}**")
            else:
                st.markdown(f"*{q['q']}*")
            st.caption(q["tag"])
        with col2:
            if q["built"]:
                st.page_link(q["page"], label="Open →")
            else:
                st.caption("Coming soon")
    st.divider()

# --------------------------------------------------------------------------
# Provenance link
# --------------------------------------------------------------------------

st.page_link("pages/provenance.py", label="📋 View Data Provenance →")

st.divider()

# --------------------------------------------------------------------------
# Bottom provenance note
# --------------------------------------------------------------------------

st.caption(
    "All data in this platform is sourced from official or named sources. "
    "Every number carries a confidence tier. "
    "Tier 1 = official registry data. "
    "Tier 2 = company-published claims, require human verification. "
    "See the Data Provenance page for full source details."
)
