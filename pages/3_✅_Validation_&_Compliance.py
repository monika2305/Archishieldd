import streamlit as st

from page_runner import run_legacy_page

st.set_page_config(page_title="Validation & Compliance", page_icon="✅", layout="wide")

st.title("✅ Validation & Compliance")
st.caption("Rule validation and NBC compliance in a unified workflow.")

selected_view = st.radio(
    "Choose validation view",
    ["Rule Validation", "NBC Compliance"],
    horizontal=True,
)

if selected_view == "Rule Validation":
    run_legacy_page("6_📏_Rule_Validation.py")
else:
    run_legacy_page("7_🏛️_NBC_Compliance.py")
