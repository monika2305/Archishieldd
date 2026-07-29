import streamlit as st

from page_runner import run_legacy_page

st.set_page_config(page_title="Visualization & Insights", page_icon="📊", layout="wide")

st.title("📊 Visualization & Insights")
st.caption("3D model exploration, issue heatmap, and storey quality insights.")

selected_view = st.radio(
    "Choose visualization view",
    ["3D BIM Viewer", "Issue Heatmap", "Storey Quality"],
    horizontal=True,
)

if selected_view == "3D BIM Viewer":
    run_legacy_page("3_🧊_3D_BIM_Viewer.py")
elif selected_view == "Issue Heatmap":
    run_legacy_page("4_🔥_Issue_Heatmap.py")
else:
    run_legacy_page("5_🏢_Storey_Quality.py")
