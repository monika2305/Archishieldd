"""
view_mode.py
─────────────────────────────────────────────────────────────────────────────
Shared adaptive UI helpers for all pages.
Import at the top of any page:
    from view_mode import get_view, mode_banner, adapt_title, adapt_caption, adapt_metric_label
"""
from __future__ import annotations
import streamlit as st

# ── Constants ─────────────────────────────────────────────────────────────────
MODE_COLOR  = {"Technical": "#58a6ff", "Business": "#f0a500", "Full": "#238636"}
MODE_ICON   = {"Technical": "🔬",      "Business": "💼",       "Full": "📊"}
MODE_DESC   = {
    "Technical": "IFC classes · GlobalIds · Psets · Schema",
    "Business":  "Cost impact · Delay risk · Plain English",
    "Full":      "All metrics — Technical + Business",
}

# ── Core helper ────────────────────────────────────────────────────────────────
def get_view() -> str:
    """Return current view mode. Defaults to Full if not set."""
    return st.session_state.get("view_mode", "Full")


def mode_banner(compact: bool = False) -> None:
    """
    Render a small mode indicator bar at the top of the page.
    compact=True → single line. compact=False → with toggle buttons.
    """
    _view = get_view()
    _c    = MODE_COLOR[_view]
    _role = st.session_state.get("user_context", {}).get("role", "")

    if compact:
        st.markdown(f"""
<div style="background:{_c}10;border:1px solid {_c}30;border-radius:6px;
padding:6px 14px;margin-bottom:12px;display:flex;align-items:center;gap:10px;">
  <span style="font-size:13px;">{MODE_ICON[_view]}</span>
  <span style="font-size:11px;color:{_c};font-weight:600;">{_view} Mode</span>
  <span style="font-size:11px;color:#4a6a8a;">· {MODE_DESC[_view]}</span>
  <span style="font-size:10px;color:#4a6a8a;margin-left:auto;">
    Change mode on the Home page
  </span>
</div>""", unsafe_allow_html=True)
    else:
        _b1, _b2, _b3, _info = st.columns([1, 1, 1, 4])
        if _b1.button("🔬 Technical", use_container_width=True,
                      type="primary" if _view == "Technical" else "secondary",
                      key=f"vm_tech_{__import__('uuid').uuid4().hex[:6]}"):
            st.session_state.view_mode = "Technical"
            st.rerun()
        if _b2.button("💼 Business", use_container_width=True,
                      type="primary" if _view == "Business" else "secondary",
                      key=f"vm_biz_{__import__('uuid').uuid4().hex[:6]}"):
            st.session_state.view_mode = "Business"
            st.rerun()
        if _b3.button("📊 Full", use_container_width=True,
                      type="primary" if _view == "Full" else "secondary",
                      key=f"vm_full_{__import__('uuid').uuid4().hex[:6]}"):
            st.session_state.view_mode = "Full"
            st.rerun()
        _info.markdown(f"""
<div style="background:{_c}10;border:1px solid {_c}30;border-radius:6px;
padding:6px 14px;display:flex;align-items:center;gap:8px;">
  <span style="font-size:13px;">{MODE_ICON[_view]}</span>
  <span style="font-size:12px;color:{_c};font-weight:600;">{_view} Mode</span>
  <span style="font-size:11px;color:#4a6a8a;">· {MODE_DESC[_view]}</span>
  {f'<span style="font-size:10px;color:#4a6a8a;margin-left:4px;">· {_role}</span>' if _role else ''}
</div>""", unsafe_allow_html=True)


# ── Text adapters ─────────────────────────────────────────────────────────────
def adapt_title(technical: str, business: str, full: str | None = None) -> str:
    """Return the right title string for the current view mode."""
    _view = get_view()
    if _view == "Technical": return technical
    if _view == "Business":  return business
    return full or technical


def adapt_caption(technical: str, business: str, full: str | None = None) -> str:
    """Return the right caption for the current view mode."""
    _view = get_view()
    if _view == "Technical": return technical
    if _view == "Business":  return business
    return full or technical


def adapt_metric_label(technical: str, business: str) -> str:
    """Return technical or business label depending on mode."""
    return technical if get_view() == "Technical" else business


def is_technical() -> bool:
    return get_view() == "Technical"

def is_business() -> bool:
    return get_view() == "Business"

def is_full() -> bool:
    return get_view() == "Full"


# ── Severity helpers ──────────────────────────────────────────────────────────
def severity_to_business(pct: float) -> tuple[str, str]:
    """Convert a loss % to a business risk label + color."""
    if pct == 0:    return "None",   "#238636"
    if pct <= 10:   return "Low",    "#58a6ff"
    if pct <= 30:   return "Medium", "#d29922"
    if pct <= 50:   return "High",   "#ff7c2a"
    return             "Critical",   "#da3633"


def impact_card(label_tech: str, label_biz: str,
                value_tech: str, value_biz: str,
                color: str, sub: str = "") -> str:
    """Return HTML for a single adaptive metric card."""
    _view  = get_view()
    _label = label_tech if _view != "Business" else label_biz
    _value = value_tech if _view != "Business" else value_biz
    return f"""
<div style="background:#161b22;border:1px solid {color}30;
border-top:3px solid {color};border-radius:0 0 8px 8px;padding:14px;text-align:center;">
  <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">{_label}</div>
  <div style="font-size:22px;font-weight:800;color:{color};">{_value}</div>
  {f'<div style="font-size:10px;color:#8b949e;margin-top:4px;">{sub}</div>' if sub else ''}
</div>"""
