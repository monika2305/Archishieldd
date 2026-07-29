import streamlit as st

from page_runner import run_legacy_page

st.set_page_config(page_title="Ask Your Model", page_icon="💬", layout="wide")

run_legacy_page("14_NLQ.py")
