
import streamlit as st
from supabase_storage import get_supabase_client, BUCKET_IFC, download_file, delete_file, list_files, upload_ifc


st.set_page_config(page_title="Cloud IFC Library", page_icon="☁️", layout="wide")

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container { background-color: #0d1117 !important; color: #e6edf3 !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background-color: #161b22 !important; border-right: 1px solid #30363d !important; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
h1,h2,h3,h4,p,span,label { color: #e6edf3 !important; }
[data-testid="stMetric"] { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:12px; }
div[data-testid="stButton"] > button { background:#161b22 !important; border:1px solid #30363d !important;
    color:#e6edf3 !important; border-radius:8px !important; }
div[data-testid="stButton"] > button:hover { background:#1c2333 !important; border-color:#58a6ff !important; }
[data-testid="stFileUploadDropzone"] { background:#161b22 !important; border:1px dashed #30363d !important;
    border-radius:8px !important; }
::-webkit-scrollbar { width:6px; } ::-webkit-scrollbar-thumb { background:#30363d; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

st.title("☁️ Cloud IFC Library")
st.caption("Upload, download, and manage all IFC files in your private Supabase bucket.")

# ── Verify client ──────────────────────────────────────────────────────────────
client = get_supabase_client()
if not client:
    st.error("Supabase client unavailable. Check credentials in supabase_storage.py.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# ☁️ UPLOAD SECTION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
padding:16px 20px;margin-bottom:20px;">
  <div style="font-size:13px;font-weight:700;color:#e6edf3;margin-bottom:4px;">
    ⬆️ Upload IFC File to Cloud
  </div>
  <div style="font-size:11px;color:#8b949e;">
    Files are stored privately in Supabase. Max recommended size: 200MB.
  </div>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Choose an IFC file",
    type=["ifc"],
    help="Upload any IFC file directly to cloud storage.",
    label_visibility="collapsed",
)

if uploaded is not None:
    file_size_mb = len(uploaded.getvalue()) / (1024 * 1024)
    uc1, uc2 = st.columns([3, 1])
    with uc1:
        st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;
padding:10px 16px;display:flex;align-items:center;gap:12px;">
  <span style="font-size:20px;">📄</span>
  <div>
    <div style="font-size:13px;font-weight:700;color:#e6edf3;">{uploaded.name}</div>
    <div style="font-size:11px;color:#8b949e;">{file_size_mb:.2f} MB · IFC file</div>
  </div>
</div>""", unsafe_allow_html=True)
    with uc2:
        if st.button("⬆️ Upload Now", use_container_width=True, type="primary"):
            with st.spinner(f"Uploading {uploaded.name}..."):
                ok = upload_ifc(uploaded.getvalue(), uploaded.name)
            if ok:
                st.success(f"✅ {uploaded.name} uploaded successfully!")
                st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 📋 FILE LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
rc1, rc2 = st.columns([1, 5])
with rc1:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

files = list_files()

if not files:
    st.info("No files uploaded yet. Use the uploader above to add your first IFC file.")
    st.stop()

# ── Summary metrics ────────────────────────────────────────────────────────────
total_size = sum((f.get("metadata") or {}).get("size", 0) or 0 for f in files)
total_mb   = total_size / (1024 * 1024)

m1, m2, m3 = st.columns(3)
m1.metric("Total Files",  len(files))
m2.metric("Total Size",   f"{total_mb:.2f} MB")
m3.metric("Bucket",       BUCKET_IFC)

st.markdown("---")

# ── Header row ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:grid;grid-template-columns:4fr 1.5fr 1.5fr 1fr 1fr;
gap:8px;padding:10px 16px;background:#21262d;border-radius:8px 8px 0 0;
font-size:11px;font-weight:700;color:#8b949e;letter-spacing:1px;">
  <div>FILE NAME</div><div>SIZE</div><div>UPLOADED</div>
  <div style="text-align:center;">DOWNLOAD</div>
  <div style="text-align:center;">DELETE</div>
</div>
""", unsafe_allow_html=True)

# ── File rows ──────────────────────────────────────────────────────────────────
for i, file in enumerate(files):
    fname   = file.get("name", "unknown")
    meta    = file.get("metadata") or {}
    size_b  = meta.get("size", 0) or 0
    created = (file.get("created_at") or "")[:16].replace("T", " ")

    if size_b >= 1024 * 1024:
        size_str = f"{size_b/(1024*1024):.2f} MB"
    elif size_b > 0:
        size_str = f"{size_b/1024:.1f} KB"
    else:
        size_str = "—"

    c1, c2, c3, c4, c5 = st.columns([4, 1.5, 1.5, 1, 1])

    with c1:
        st.markdown(
            f"<div style='padding:10px 4px;font-size:13px;color:#e6edf3;"
            f"font-family:monospace;overflow:hidden;text-overflow:ellipsis;"
            f"white-space:nowrap;' title='{fname}'>{fname}</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div style='padding:10px 4px;font-size:12px;color:#8b949e;'>{size_str}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div style='padding:10px 4px;font-size:12px;color:#8b949e;'>{created}</div>",
            unsafe_allow_html=True,
        )
    with c4:
        if st.button("⬇️", key=f"dl_{fname}", use_container_width=True, help=f"Download {fname}"):
            with st.spinner("Downloading..."):
                data = download_file(fname)
            if data:
                st.download_button(
                    label="💾 Save",
                    data=data,
                    file_name=fname,
                    mime="application/octet-stream",
                    key=f"save_{fname}",
                    use_container_width=True,
                )
            else:
                st.error("Download failed.")
    with c5:
        if st.button("🗑️", key=f"del_{fname}", use_container_width=True, help=f"Delete {fname}"):
            ok = delete_file(fname)
            if ok:
                st.success("✅ Deleted")
                st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='padding:10px 16px;background:#161b22;border:1px solid #30363d;"
    f"border-radius:0 0 8px 8px;font-size:11px;color:#8b949e;'>"
    f"☁️ {len(files)} file(s) · bucket: {BUCKET_IFC} · private (authenticated access only)</div>",
    unsafe_allow_html=True,
)
