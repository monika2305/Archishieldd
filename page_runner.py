import runpy
from pathlib import Path

import streamlit as st


LEGACY_PAGES_DIR = Path(__file__).resolve().parent / "legacy_pages"


def run_legacy_page(script_name: str) -> None:
    """Execute a legacy page script from the legacy_pages folder."""
    script_path = LEGACY_PAGES_DIR / script_name
    if not script_path.exists():
        st.error(f"Missing legacy page: {script_name}")
        return

    original_set_page_config = st.set_page_config

    # Legacy pages call set_page_config at top-level; suppress duplicates here.
    def _safe_set_page_config(*_args, **_kwargs):
        return None

    st.set_page_config = _safe_set_page_config
    try:
        runpy.run_path(str(script_path), run_name=f"__legacy_{script_path.stem}__")
    finally:
        st.set_page_config = original_set_page_config
