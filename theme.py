"""
theme.py
─────────────────────────────────────────────────────────────────────────────
Role-based UI theming system.
Every page imports this and calls apply_theme() right after set_page_config.
"""
from __future__ import annotations
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# ROLE THEMES
# ══════════════════════════════════════════════════════════════════════════════
THEMES: dict[str, dict] = {

    "Architect": {
        "primary":      "#8b5cf6",
        "primary_dim":  "#8b5cf620",
        "primary_muted":"#8b5cf640",
        "accent":       "#a78bfa",
        "bg":           "#0a0812",
        "bg2":          "#120d1e",
        "bg3":          "#1a1230",
        "border":       "#2d1f4e",
        "border_bright":"#8b5cf6",
        "text":         "#ede9fe",
        "text_muted":   "#9b8fc0",
        "success":      "#34d399",
        "warning":      "#fbbf24",
        "danger":       "#f87171",
        "tab_active":   "#8b5cf6",
        "metric_bg":    "#120d1e",
        "sidebar_bg":   "#0d0a1a",
        "font":         "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "icon":         "🏛️",
        "label":        "Architect",
        "tagline":      "Design-first · Visual · Spatial",
        "button_style": "border-radius:20px !important;",
    },

    "BIM Manager": {
        "primary":      "#58a6ff",
        "primary_dim":  "#58a6ff20",
        "primary_muted":"#58a6ff40",
        "accent":       "#79c0ff",
        "bg":           "#0d1117",
        "bg2":          "#161b22",
        "bg3":          "#21262d",
        "border":       "#30363d",
        "border_bright":"#58a6ff",
        "text":         "#e6edf3",
        "text_muted":   "#9aa4af",
        "success":      "#238636",
        "warning":      "#d29922",
        "danger":       "#da3633",
        "tab_active":   "#58a6ff",
        "metric_bg":    "#161b22",
        "sidebar_bg":   "#161b22",
        "font":         "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "icon":         "🔧",
        "label":        "BIM Manager",
        "tagline":      "Technical · Data-rich · Complete",
        "button_style": "border-radius:6px !important;",
    },

    "Contractor": {
        "primary":      "#f97316",
        "primary_dim":  "#f9731620",
        "primary_muted":"#f9731640",
        "accent":       "#fb923c",
        "bg":           "#0c0a08",
        "bg2":          "#1a1208",
        "bg3":          "#261a0a",
        "border":       "#3d2a10",
        "border_bright":"#f97316",
        "text":         "#fef3e2",
        "text_muted":   "#b59068",
        "success":      "#4ade80",
        "warning":      "#fbbf24",
        "danger":       "#f87171",
        "tab_active":   "#f97316",
        "metric_bg":    "#1a1208",
        "sidebar_bg":   "#130f06",
        "font":         "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "icon":         "🏗️",
        "label":        "Contractor",
        "tagline":      "Action-first · Bold · Results",
        "button_style": "border-radius:4px !important; font-weight:700 !important; letter-spacing:0.5px !important;",
    },

    "Facility Manager": {
        "primary":      "#22c55e",
        "primary_dim":  "#22c55e20",
        "primary_muted":"#22c55e40",
        "accent":       "#4ade80",
        "bg":           "#080e0a",
        "bg2":          "#0f1a12",
        "bg3":          "#162219",
        "border":       "#1e3a28",
        "border_bright":"#22c55e",
        "text":         "#e0fce8",
        "text_muted":   "#7aab87",
        "success":      "#22c55e",
        "warning":      "#facc15",
        "danger":       "#f87171",
        "tab_active":   "#22c55e",
        "metric_bg":    "#0f1a12",
        "sidebar_bg":   "#0a1210",
        "font":         "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "icon":         "🏢",
        "label":        "Facility Manager",
        "tagline":      "Compliance · Structured · Handover",
        "button_style": "border-radius:8px !important;",
    },

    "Student / Researcher": {
        "primary":      "#06b6d4",
        "primary_dim":  "#06b6d420",
        "primary_muted":"#06b6d440",
        "accent":       "#22d3ee",
        "bg":           "#080c10",
        "bg2":          "#0d1520",
        "bg3":          "#121e30",
        "border":       "#1a3045",
        "border_bright":"#06b6d4",
        "text":         "#e0f7ff",
        "text_muted":   "#6f9bb5",
        "success":      "#34d399",
        "warning":      "#fbbf24",
        "danger":       "#f87171",
        "tab_active":   "#06b6d4",
        "metric_bg":    "#0d1520",
        "sidebar_bg":   "#0a1018",
        "font":         "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "icon":         "🎓",
        "label":        "Student / Researcher",
        "tagline":      "Learn · Explore · Discover",
        "button_style": "border-radius:12px !important;",
    },
}

_DEFAULT = THEMES["BIM Manager"]


def get_theme(role: str | None = None) -> dict:
    if role is None:
        role = st.session_state.get("user_context", {}).get("role", "BIM Manager")
    return THEMES.get(role, _DEFAULT)


def get_css(t: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block');

/* ── Global font override — applies to text elements, but NOT icon fonts ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.stMarkdown, .stText, .stDataFrame, .stTable, .stMetric, .stAlert,
.stButton button, .stTextInput input, .stSelectbox, .stRadio, .stCheckbox, .stSlider,
.stTabs, .stCaption, p, span:not([class*="material"]):not([class*="icon"]),
div:not([class*="material"]):not([class*="icon"]), label,
h1, h2, h3, h4, h5, h6, a, li, td, th {{
    font-family: {t['font']} !important;
}}

/* ── Never override icon fonts — fixes expander arrow / icon glyphs rendering as text ── */
[data-testid="stExpander"] summary svg,
[data-testid="stExpander"] summary [class*="material"],
[data-testid="stIconMaterial"],
[class*="material-icons"],
span[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Outlined", "Material Symbols Rounded", sans-serif !important;
}}

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container {{
    background-color: {t['bg']} !important;
    color: {t['text']} !important;
}}

/* ── Typography scale — clean and consistent ── */
h1 {{ font-weight: 800 !important; letter-spacing: -0.02em !important; color: {t['text']} !important; }}
h2 {{ font-weight: 700 !important; letter-spacing: -0.01em !important; color: {t['text']} !important; }}
h3 {{ font-weight: 600 !important; color: {t['text']} !important; }}
h4, h5, h6 {{ font-weight: 600 !important; color: {t['text']} !important; }}
p {{ font-weight: 400 !important; line-height: 1.6 !important; }}
span:not([class*="material"]):not([data-testid="stIconMaterial"]) {{
    font-weight: 400 !important;
    /* line-height intentionally NOT forced on spans — Streamlit uses
       flex-row spans (e.g. expander summary heading) where a tall
       line-height causes the icon and label text to visually overlap. */
}}
div:not([class*="material"]) {{ line-height: 1.6 !important; }}

[data-testid="stSidebar"], [data-testid="stSidebar"] > div {{
    background-color: {t['sidebar_bg']} !important;
    border-right: 1px solid {t['border']} !important;
}}
[data-testid="stSidebar"] *:not([class*="material"]):not([data-testid="stIconMaterial"]) {{ color: {t['text']} !important; }}

[data-testid="stCaptionContainer"] p {{
    color: {t['text_muted']} !important;
    font-weight: 400 !important;
    font-size: 13px !important;
}}
hr {{ border-color: {t['border']} !important; }}

[data-testid="stMetric"] {{
    background-color: {t['metric_bg']} !important;
    border: 1px solid {t['border']} !important;
    border-top: 2px solid {t['primary']} !important;
    border-radius: 10px !important;
    padding: 16px !important;
}}
[data-testid="stMetric"] label {{
    color: {t['text_muted']} !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}}
[data-testid="stMetricValue"] {{
    color: {t['primary']} !important;
    font-weight: 700 !important;
}}

div[data-testid="stButton"] > button {{
    background: {t['bg2']} !important;
    border: 1px solid {t['primary_muted']} !important;
    color: {t['text']} !important;
    {t['button_style']}
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}}
div[data-testid="stButton"] > button:hover {{
    background: {t['primary_dim']} !important;
    border-color: {t['primary']} !important;
    color: {t['primary']} !important;
    box-shadow: 0 0 12px {t['primary_muted']} !important;
}}
div[data-testid="stButton"] > button[kind="primary"] {{
    background: {t['primary']} !important;
    border-color: {t['primary']} !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}}
div[data-testid="stButton"] > button[kind="primary"]:hover {{
    background: {t['accent']} !important;
    border-color: {t['accent']} !important;
    box-shadow: 0 0 16px {t['primary_muted']} !important;
}}

input, textarea {{
    background-color: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    color: {t['text']} !important;
    border-radius: 6px !important;
    font-weight: 400 !important;
}}
input:focus, textarea:focus {{
    border-color: {t['primary']} !important;
    box-shadow: 0 0 0 2px {t['primary_dim']} !important;
}}
[data-baseweb="select"] > div:first-child {{
    background-color: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    color: {t['text']} !important;
}}

[data-testid="stExpander"] {{
    background-color: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
}}
[data-testid="stExpander"] summary p {{
    font-weight: 500 !important;
    font-family: {t['font']} !important;
}}

[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background-color: {t['bg2']} !important;
    border-bottom: 2px solid {t['border']} !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background-color: transparent !important;
    color: {t['text_muted']} !important;
    font-weight: 500 !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
    color: {t['primary']} !important;
    border-bottom: 2px solid {t['primary']} !important;
}}

[data-testid="stDataFrame"], [data-testid="stDataFrame"] > div {{
    background-color: {t['bg2']} !important;
}}
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] [role="columnheader"] {{
    background-color: {t['bg3']} !important;
    color: {t['primary']} !important;
    font-weight: 600 !important;
}}
[data-testid="stDataFrame"] td,
[data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] [role="gridcell"] * {{
    color: {t['text']} !important;
    background-color: {t['bg2']} !important;
    font-weight: 400 !important;
}}

[data-testid="stFileUploadDropzone"] {{
    background: {t['bg2']} !important;
    border: 1px dashed {t['border']} !important;
    border-radius: 8px !important;
}}

[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {{
    background-color: {t['primary']} !important;
}}

[data-testid="stAlert"] {{
    background-color: {t['bg2']} !important;
    border-color: {t['border']} !important;
    font-weight: 400 !important;
}}

::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {t['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {t['border']}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {t['primary_muted']}; }}

[data-testid="stRadio"] label {{ color: {t['text']} !important; font-weight: 400 !important; }}
[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {{
    border-color: {t['primary']} !important;
    background-color: {t['primary_dim']} !important;
}}

/* ══════════════════════════════════════════════════════════════════════════
   GUARANTEED FIX — Icon glyph text overlapping with labels.
   Brute-force approach: hide the literal icon text completely via
   text-indent (pushes text off-screen, no font/ligature dependency at all)
   while keeping the icon's box dimensions for layout spacing.
   ══════════════════════════════════════════════════════════════════════════ */
[data-testid="stIconMaterial"] {{
    text-indent: -9999px !important;
    overflow: hidden !important;
    display: inline-block !important;
    width: 1.2rem !important;
    height: 1.2rem !important;
    white-space: nowrap !important;
    position: relative !important;
    vertical-align: middle !important;
    flex-shrink: 0 !important;
}}
/* Draw a simple, reliable triangle arrow with pure CSS (no font needed) */
[data-testid="stIconMaterial"]::after {{
    content: "" !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    width: 0 !important;
    height: 0 !important;
    border-top: 5px solid transparent !important;
    border-bottom: 5px solid transparent !important;
    border-left: 6px solid currentColor !important;
    transform: translate(-50%, -50%) !important;
    text-indent: 0 !important;
    color: {t['text_muted']} !important;
}}
[data-testid="stExpander"][aria-expanded="true"] [data-testid="stIconMaterial"]::after,
[data-testid="stExpander"] summary[aria-expanded="true"] [data-testid="stIconMaterial"]::after {{
    transform: translate(-50%, -50%) rotate(90deg) !important;
}}
/* Ensure the icon box never sits on top of the label text */
[data-testid="stExpander"] summary span,
[data-testid="stSidebarNavLink"] {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
}}

code, pre, .stCodeBlock, [data-testid="stCodeBlock"] {{
    font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace !important;
}}

/* ══════════════════════════════════════════════════════════════════════════
   HARD FINAL OVERRIDE — Material Symbols icons
   Must be the LAST rules in this stylesheet so they always win.
   Covers: expander arrows, sidebar nav icons, any Streamlit icon glyph.
   Streamlit renders these as <span data-testid="stIconMaterial"> with the
   actual icon name (e.g. "keyboard_arrow_right") as literal text content,
   then uses an icon font to turn that text into a glyph. If our font
   override reaches this span, the text shows literally instead of an icon.
   ══════════════════════════════════════════════════════════════════════════ */
html body span[data-testid="stIconMaterial"],
html body [data-testid="stIconMaterial"],
html body [data-testid="stExpanderToggleIcon"],
html body section[data-testid="stSidebarNav"] span[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Outlined", "Material Symbols Rounded",
                  "Material Icons", "Material Icons Outlined", sans-serif !important;
    font-weight: normal !important;
    font-style: normal !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-smoothing: antialiased !important;
    text-rendering: optimizeLegibility !important;
    -moz-osx-font-smoothing: grayscale !important;
    font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24 !important;
    font-feature-settings: "liga" 1 !important;
    -webkit-font-feature-settings: "liga" 1 !important;
    font-size: 1.25rem !important;
    line-height: 1 !important;
}}

span[data-testid="stIconMaterial"],
[data-testid="stExpanderToggleIcon"],
[data-testid="stIconMaterial"] *,
i.material-icons,
i.material-icons-outlined,
i.material-icons-round,
[class^="material-icons"],
[class*=" material-icons"],
[data-testid="stSidebarNavLink"] span,
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"],
section[data-testid="stSidebarNav"] span[class*="eyebrow"],
section[data-testid="stSidebarNav"] svg,
section[data-testid="stSidebarNav"] [data-testid="stIconMaterial"],
[data-testid="stSidebarNavItems"] span[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Outlined", "Material Symbols Rounded",
                  "Material Icons", "Material Icons Outlined", sans-serif !important;
    font-weight: normal !important;
    font-style: normal !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-smoothing: antialiased !important;
    text-rendering: optimizeLegibility !important;
    -moz-osx-font-smoothing: grayscale !important;
    font-feature-settings: "liga" !important;
}}
</style>
"""


def role_banner(t: dict | None = None) -> str:
    if t is None:
        t = get_theme()
    role = st.session_state.get("user_context", {}).get("role", "")
    return f"""
<div style="background:{t['primary_dim']};border:1px solid {t['primary_muted']};
border-radius:8px;padding:8px 16px;margin-bottom:16px;
display:flex;align-items:center;gap:10px;">
  <span style="font-size:18px;">{t['icon']}</span>
  <div>
    <span style="font-size:13px;font-weight:700;color:{t['primary']};">{t['label']}</span>
    <span style="font-size:11px;color:{t['text_muted']};margin-left:8px;">· {t['tagline']}</span>
  </div>
</div>"""


def apply_theme(show_banner: bool = False) -> dict:
    t = get_theme()
    st.markdown(get_css(t), unsafe_allow_html=True)
    if show_banner:
        st.markdown(role_banner(t), unsafe_allow_html=True)
    return t


def card(content: str, t: dict | None = None, border_color: str | None = None,
         padding: str = "14px 18px", radius: str = "10px") -> str:
    if t is None:
        t = get_theme()
    bc = border_color or t["border"]
    return (f'<div style="background:{t["bg2"]};border:1px solid {bc};'
            f'border-radius:{radius};padding:{padding};">{content}</div>')


def metric_card(label: str, value: str, sub: str = "",
                color: str | None = None, t: dict | None = None) -> str:
    if t is None:
        t = get_theme()
    c = color or t["primary"]
    return f"""
<div style="background:{t['metric_bg']};border:1px solid {t['border']};
border-top:3px solid {c};border-radius:10px;padding:14px;text-align:center;">
  <div style="font-size:11px;color:{t['text_muted']};letter-spacing:1px;
  margin-bottom:6px;text-transform:uppercase;font-weight:600;">{label}</div>
  <div style="font-size:26px;font-weight:700;color:{c};">{value}</div>
  {f'<div style="font-size:11px;color:{t["text_muted"]};margin-top:4px;">{sub}</div>' if sub else ''}
</div>"""
