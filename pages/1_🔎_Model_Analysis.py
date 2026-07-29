import streamlit as st

from page_runner import run_legacy_page

st.set_page_config(page_title="Model Analysis", page_icon="🔎", layout="wide")

st.title("🔎 Model Analysis")
st.caption("Proxy classification, Pset analysis, and geometry integrity in one place.")

selected_view = st.radio(
    "Choose analysis view",
    ["Proxy Classification", "Pset Analysis", "Geometry Integrity"],
    horizontal=True,
)

if selected_view == "Proxy Classification":
    run_legacy_page("1_🔎_Proxy_Classification.py")
elif selected_view == "Pset Analysis":
    run_legacy_page("2_📦_Pset_Analysis.py")
else:
    run_legacy_page("13_📐_Geometry_Integrity.py")
