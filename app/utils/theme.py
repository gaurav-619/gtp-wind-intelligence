"""
app/utils/theme.py
Design System & Shared Visual Tokens for GTP Wind Intelligence.

Defines:
- Standard color palette with reconciled amber (#F59E0B)
- Unified custom KPI metric card component (HTML/CSS)
- Standardized chart heights and layout CSS
"""

import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# COLOR CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
COLOR_PRIMARY = "#1E3A8A"       # Navy Blue
COLOR_SECONDARY = "#3B82F6"     # Bright Blue
COLOR_SUCCESS = "#10B981"       # Emerald Green
COLOR_WARNING = "#F59E0B"       # Reconciled Amber (Consistent across entire app)
COLOR_DANGER = "#EF4444"        # Crimson Red
COLOR_INFO = "#0284C7"          # Sky Blue

# Neutral Palette
COLOR_TEXT_MAIN = "#0F172A"     # Slate 900
COLOR_TEXT_MUTED = "#64748B"    # Slate 500
COLOR_BG_LIGHT = "#F8FAFC"      # Slate 50
COLOR_CARD_BG = "#FFFFFF"       # White
COLOR_BORDER = "#E2E8F0"        # Slate 200

# Chart Standard Dimensions
CHART_HEIGHT_STANDARD = 420
CHART_HEIGHT_TALL = 520
CHART_HEIGHT_COMPACT = 320


# ──────────────────────────────────────────────────────────────────────────────
# CSS INJECTION
# ──────────────────────────────────────────────────────────────────────────────
def inject_custom_css():
    """Injects core design system styles, standardizing card styling and typography."""
    st.markdown(
        f"""
        <style>
            /* Base font & smoothing */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            
            html, body, [class*="css"] {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            
            /* Responsive KPI Card Container */
            .gtp-kpi-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }}
            
            .gtp-kpi-card {{
                background: {COLOR_CARD_BG};
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
                padding: 18px 20px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.02);
                transition: transform 0.15s ease, box-shadow 0.15s ease;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                min-height: 110px;
            }}
            
            .gtp-kpi-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04);
            }}
            
            .gtp-kpi-label {{
                font-size: 13px;
                font-weight: 600;
                color: {COLOR_TEXT_MUTED};
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 6px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            
            .gtp-kpi-value {{
                font-size: 26px;
                font-weight: 700;
                color: {COLOR_TEXT_MAIN};
                line-height: 1.2;
                margin-bottom: 4px;
            }}
            
            .gtp-kpi-subtext {{
                font-size: 12px;
                color: {COLOR_TEXT_MUTED};
                margin-top: 2px;
            }}
            
            .gtp-kpi-delta-pos {{
                color: {COLOR_SUCCESS};
                font-weight: 600;
                font-size: 12px;
            }}
            
            .gtp-kpi-delta-warn {{
                color: {COLOR_WARNING};
                font-weight: 600;
                font-size: 12px;
            }}
            
            .gtp-kpi-delta-neg {{
                color: {COLOR_DANGER};
                font-weight: 600;
                font-size: 12px;
            }}
            
            /* Banner styles */
            .gtp-banner {{
                background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
                border-left: 5px solid {COLOR_SECONDARY};
                border-radius: 12px;
                padding: 22px 26px;
                margin-bottom: 24px;
                color: #ffffff;
            }}
            
            .gtp-banner-title {{
                color: #93c5fd;
                font-size: 12px;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                font-weight: 700;
                margin: 0 0 6px 0;
            }}
            
            .gtp-banner-body {{
                color: #ffffff;
                font-size: 20px;
                font-weight: 700;
                margin: 0;
                line-height: 1.4;
            }}
            
            .gtp-banner-caption {{
                color: #bfdbfe;
                font-size: 13px;
                margin: 8px 0 0 0;
                line-height: 1.5;
            }}
            
            /* Header section styling */
            .gtp-page-header {{
                margin-bottom: 20px;
            }}
            
            .gtp-page-title {{
                font-size: 28px;
                font-weight: 800;
                color: {COLOR_TEXT_MAIN};
                margin-bottom: 4px;
            }}
            
            .gtp-page-subtitle {{
                font-size: 15px;
                font-weight: 500;
                color: {COLOR_SECONDARY};
                margin-bottom: 8px;
            }}
            
            .gtp-provenance-badge {{
                font-size: 12px;
                color: {COLOR_TEXT_MUTED};
                background: #f1f5f9;
                padding: 4px 10px;
                border-radius: 6px;
                display: inline-block;
                border: 1px solid {COLOR_BORDER};
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
# HTML RENDERING UTILITY
# ──────────────────────────────────────────────────────────────────────────────
def render_html(html_str: str):
    """
    Renders custom HTML in Streamlit safely by stripping leading indentation
    from all lines to prevent CommonMark from parsing indented HTML lines as code blocks.
    """
    clean = "\n".join(line.strip() for line in html_str.strip().splitlines() if line.strip())
    st.markdown(clean, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# UNIFIED KPI METRIC CARD
# ──────────────────────────────────────────────────────────────────────────────
def render_kpi_card(title: str, value: str, subtext: str = "", delta: str = "", delta_type: str = "pos", border_left_color: str = None) -> str:
    """
    Renders a unified custom KPI metric card with consistent styling.
    
    Args:
        title: Card header label
        value: Primary prominent KPI metric
        subtext: Context or secondary descriptive text
        delta: Optional delta or change metric
        delta_type: 'pos' (green), 'warn' (amber), 'neg' (red), 'neutral' (slate)
        border_left_color: Optional hex color for custom left border accent
    """
    delta_class = "gtp-kpi-delta-pos"
    if delta_type == "warn":
        delta_class = "gtp-kpi-delta-warn"
    elif delta_type == "neg":
        delta_class = "gtp-kpi-delta-neg"
    elif delta_type == "neutral":
        delta_class = "gtp-kpi-subtext"
        
    border_style = f"border-left: 4px solid {border_left_color};" if border_left_color else ""
    delta_html = f'<span class="{delta_class}">{delta}</span>' if delta else ""
    subtext_html = f'<div class="gtp-kpi-subtext">{subtext}</div>' if subtext else ""
    
    # Return single-line compact HTML with zero leading indentation or line breaks
    # to guarantee that Streamlit's Markdown parser never interprets it as a code block.
    return (
        f'<div class="gtp-kpi-card" style="{border_style}">'
        f'<div class="gtp-kpi-label"><span>{title}</span>{delta_html}</div>'
        f'<div class="gtp-kpi-value">{value}</div>'
        f'{subtext_html}'
        f'</div>'
    )


def render_page_header(title: str, subtitle: str, data_source: str = "BNetzA Marktstammdatenregister (MaStR)", confidence_tier: str = "Tier 1 — Official Registry", snapshot_date: str = ""):
    """Renders standardized header with purpose-driven title, decision-support subtitle, and provenance metadata."""
    inject_custom_css()
    
    date_str = f" · <b>Snapshot:</b> {snapshot_date}" if snapshot_date else ""
    header_html = (
        f'<div class="gtp-page-header">'
        f'<div class="gtp-page-title">{title}</div>'
        f'<div class="gtp-page-subtitle">{subtitle}</div>'
        f'<div class="gtp-provenance-badge">🏛️ <b>Source:</b> {data_source} &nbsp;|&nbsp; 🛡️ <b>Confidence:</b> {confidence_tier}{date_str}</div>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
