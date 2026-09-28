"""
app/main.py
GTP Wind Intelligence - Application Entrypoint.

Migrated to Streamlit atomic navigation via st.navigation + st.Page.
Features persistent top-bar navigation (position="top") with zero sidebar conflicts.
"""

import streamlit as st
import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Centralized page config - called strictly once here
st.set_page_config(
    page_title="GTP Wind Intelligence",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Atomic navigation definition using client-facing names and clean url slugs
pages = [
    st.Page("views/overview.py", title="Executive Overview", icon="🏠", url_path="overview", default=True),
    st.Page("views/market_landscape.py", title="Market Landscape", icon="🗺️", url_path="market_landscape"),
    st.Page("views/pipeline_radar.py", title="Development Pipeline & Permitting Radar", icon="📡", url_path="pipeline_radar"),
    st.Page("views/operator_intelligence.py", title="Operator Intelligence & Repowering Radar", icon="🏭", url_path="operator_intelligence"),
    st.Page("views/storage_colocation.py", title="Storage Co-Location Screener", icon="🔋", url_path="storage_colocation"),
    st.Page("views/data_trust_center.py", title="Data Trust Center", icon="🛡️", url_path="data_trust_center"),
]

# Initialize top navigation bar
nav = st.navigation(pages, position="top")

# Execute active page once per rerun
nav.run()
