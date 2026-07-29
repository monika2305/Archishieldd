import streamlit as st

from page_runner import run_legacy_page

st.set_page_config(page_title="Reports & Export", page_icon="📄", layout="wide")

st.title("📄 Reports & Export")
st.caption("Model scoring, BCF generation, and IFC version comparison.")

selected_view = st.radio(
    "Choose reporting view",
    ["Model Score", "BCF Generator", "Version Comparison"],
    horizontal=True,
)

if selected_view == "Model Score":
    run_legacy_page("9_📊_Model_Score.py")
elif selected_view == "BCF Generator":
    run_legacy_page("10_📋_BCF_Generator.py")
else:
    run_legacy_page("11_🔀_Version_Comparison.py")
