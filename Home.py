import streamlit as st
from theme import apply_theme, get_theme, role_banner, metric_card
import ifcopenshell
import pandas as pd
from fpdf import FPDF
import json
import datetime
from supabase_storage import upload_ifc

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IFC Semantic Data-Loss Analyser",
    page_icon="🛡️",
    layout="wide",
)

# ── Session state ──────────────────────────────────────────────────────────────
if "logged_in"    not in st.session_state: st.session_state.logged_in    = False
if "user_context" not in st.session_state: st.session_state.user_context = {}
if "model_loaded" not in st.session_state: st.session_state.model_loaded = False
if "analysis"     not in st.session_state: st.session_state.analysis     = {}
if "last_file_id" not in st.session_state: st.session_state.last_file_id = None
if "cloud_ifc_url"      not in st.session_state: st.session_state.cloud_ifc_url      = None
if "cloud_snapshot_url" not in st.session_state: st.session_state.cloud_snapshot_url = None
if "cloud_pdf_url"      not in st.session_state: st.session_state.cloud_pdf_url      = None

# ── Apply role-based theme — must come before any st.markdown ─────────────────
_t = apply_theme()
_role = st.session_state.get("user_context", {}).get("role", "BIM Manager")

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    st.title("🔍 IFC Semantic Data-Loss Analyser")
    st.markdown("---")
    st.subheader("Login")
    st.caption("Please fill in all fields to continue.")

    name   = st.text_input("Your Name *", placeholder="e.g. Moni")
    role   = st.selectbox("Your Role *", [
        "— Select —", "Architect", "Structural Engineer",
        "BIM Manager", "Contractor", "Facility Manager", "Student / Researcher"
    ])
    domain = st.selectbox("Project Domain *", [
        "— Select —", "Architecture", "Structural",
        "MEP", "Infrastructure", "Facility Management"
    ])
    purpose = st.selectbox("Purpose of IFC *", [
        "— Select —", "Design coordination", "Compliance",
        "Construction", "Handover / FM", "Academic / Research"
    ])

    # Check completeness live
    _name_ok    = bool(name.strip())
    _role_ok    = role    != "— Select —"
    _domain_ok  = domain  != "— Select —"
    _purpose_ok = purpose != "— Select —"
    _all_ok     = _name_ok and _role_ok and _domain_ok and _purpose_ok

    # Show what is still missing
    _missing = []
    if not _name_ok:    _missing.append("Name")
    if not _role_ok:    _missing.append("Role")
    if not _domain_ok:  _missing.append("Project Domain")
    if not _purpose_ok: _missing.append("Purpose of IFC")

    if _missing:
        st.warning(f"⚠️ Please fill in: **{', '.join(_missing)}**")

    if st.button("Continue →", disabled=not _all_ok, type="primary", use_container_width=True):
        if _all_ok:
            st.session_state.user_context = {
                "name": name.strip(), "role": role,
                "domain": domain, "purpose": purpose
            }
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Please fill in all required fields.")

    # ── Sample Model download ──────────────────────────────────────────────────
    # Judges who don't have an IFC file can download the bundled sample,
    # then upload it above to explore all modules.
    st.markdown("---")
    st.caption("👇 Don't have an IFC file? Download our sample model and upload it above.")
    import os
    _SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "sample_model.ifc")
    if os.path.exists(_SAMPLE_PATH):
        with open(_SAMPLE_PATH, "rb") as _sf:
            st.download_button(
                label="⬇️ Download Sample IFC Model",
                data=_sf,
                file_name="sample_model.ifc",
                mime="application/octet-stream",
                use_container_width=True,
            )
    else:
        st.info("Sample model not found. Place `sample_model.ifc` next to `Home.py`.")

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
context = st.session_state.user_context
_role   = context.get("role", "BIM Manager")
_t      = get_theme(_role)
apply_theme()
st.markdown(role_banner(_t), unsafe_allow_html=True)

st.title("🔍 IFC Semantic Data-Loss Analyser")
c1, c2, c3 = st.columns(3)
c1.write(f"**Role:** {context['role']}")
c2.write(f"**Domain:** {context['domain']}")
c3.write(f"**Purpose:** {context['purpose']}")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗂️ Dashboards")
    st.markdown(
        "After uploading your IFC file, use the module pages:\n\n"
        "- **🔎 Model Analysis** — Proxy Classification, Pset Analysis, Geometry Integrity\n"
        "- **📊 Visualization & Insights** — 3D BIM Viewer, Issue Heatmap, Storey Quality\n"
        "- **✅ Validation & Compliance** — Rule Validation, NBC Compliance\n"
        "- **🛠️ Corrections** — Correction Suggestions\n"
        "- **📄 Reports & Export** — Model Score, BCF Generator, Version Comparison\n"
    )
    st.markdown("---")
    if st.session_state.model_loaded:
        st.success("✅ Model loaded — dashboards ready")
    else:
        st.info("Upload an IFC file to enable dashboards")

    # ── Cloud Storage Links ────────────────────────────────────────────────────
    if any([
        st.session_state.get("cloud_ifc_url"),
        st.session_state.get("cloud_snapshot_url"),
        st.session_state.get("cloud_pdf_url"),
    ]):
        st.markdown("---")
        st.markdown("#### ☁️ Cloud Storage")
        if st.session_state.get("cloud_ifc_url"):
            st.markdown(f"[📦 IFC File]({st.session_state['cloud_ifc_url']})")
        if st.session_state.get("cloud_snapshot_url"):
            st.markdown(f"[📊 Analysis JSON]({st.session_state['cloud_snapshot_url']})")
        if st.session_state.get("cloud_pdf_url"):
            st.markdown(f"[📄 PDF Report]({st.session_state['cloud_pdf_url']})")

# ── File upload ────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload IFC file",
    type=["ifc"],
    help="Supports files up to 800 MB. Large files may take 60–120 seconds to process."
)

# ── On fresh upload: parse IFC and store ALL results in session_state ──────────
# Detect new file by comparing file id — forces re-analysis on every new upload
if uploaded_file:
    current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if current_file_id != st.session_state.last_file_id:
        st.session_state.model_loaded = False   # force re-analysis
        st.session_state.last_file_id = current_file_id
        st.session_state.analysis     = {}

if uploaded_file and not st.session_state.model_loaded:
    pass  # processed below

if uploaded_file:
    file_size_mb = 0

    # ── Size warning ──────────────────────────────────────────────────────────
    if file_size_mb > 400:
        st.info(f"📦 Large file detected ({file_size_mb:.1f} MB) — using optimised streaming parser. Please wait...")
    elif file_size_mb > 100:
        st.info(f"📂 File size: {file_size_mb:.1f} MB — processing with chunked writer.")

    prog_bar = st.progress(0, text=f"📥 Receiving {file_size_mb:.1f} MB...")

    # ── Stream directly to disk — never loads full file into RAM ──────────────
    CHUNK = 16 * 1024 * 1024  # 16 MB chunks
    bytes_written = 0
    total_bytes   = uploaded_file.size

    with open("temp.ifc", "wb") as f:
        # getbuffer() gives a memoryview — slice without copying
        buf = uploaded_file.getbuffer()
        for i in range(0, total_bytes, CHUNK):
            f.write(buf[i : i + CHUNK])
            bytes_written = min(i + CHUNK, total_bytes)
            pct = int(bytes_written / total_bytes * 35)
            mb_done = bytes_written / (1024 * 1024)
            prog_bar.progress(pct, text=f"📥 Writing {mb_done:.0f} / {file_size_mb:.0f} MB...")
        del buf   # free memoryview immediately

    # ── Upload IFC to Supabase cloud storage ──────────────────────────────────
    try:
        with open("temp.ifc", "rb") as _cf:
            _ifc_bytes = _cf.read()
        _orig_name = uploaded_file.name
        uploaded_ok = upload_ifc(_ifc_bytes, _orig_name)
        if uploaded_ok:
            st.success("☁️ IFC file uploaded to cloud storage successfully!")
    except Exception as _ue:
        st.warning(f"⚠️ Cloud upload skipped: {_ue}")

    # ── Open with ifcopenshell — it reads from disk, not RAM ──────────────────
    import gc
    gc.collect()   # free any leftover memory before parsing
    model = ifcopenshell.open("temp.ifc")
    prog_bar = st.progress(0)

    prog_bar.progress(40, text="🔍 Detecting IFC export source...")

    # ── Export Source Risk Prediction ─────────────────────────────────────────
    def detect_export_source(ifc_model):
        """Read IFC header metadata to identify the exporting software."""
        try:
            header = ifc_model.header
            desc   = str(getattr(header, "file_description", "")).lower()
            name   = str(getattr(header, "file_name",        "")).lower()
            schema = str(getattr(header, "file_schema",      "")).upper()

            combined = desc + " " + name

            if any(k in combined for k in ["revit", "autodesk"]):
                tool = "Autodesk Revit"
                risks = [
                    ("⚠️ RPC trees/furniture export as IfcBuildingElementProxy",   "High"),
                    ("⚠️ FireRating property often missing in Pset_WallCommon",     "High"),
                    ("⚠️ Material classification may be lost during export",        "Medium"),
                    ("⚠️ Some custom Psets may not transfer correctly",             "Medium"),
                    ("⚠️ IfcWallStandardCase may appear instead of IfcWall",        "Low"),
                ]
            elif any(k in combined for k in ["archicad", "graphisoft"]):
                tool = "Graphisoft ArchiCAD"
                risks = [
                    ("⚠️ Morph elements may export as generic proxies",            "High"),
                    ("⚠️ Complex roof shapes may lose semantic type",              "High"),
                    ("⚠️ Object-level Psets may be partially mapped",             "Medium"),
                    ("⚠️ Stair components may lose sub-element classification",   "Low"),
                ]
            elif any(k in combined for k in ["tekla", "trimble"]):
                tool = "Tekla Structures"
                risks = [
                    ("⚠️ Custom component assemblies may become proxy objects",    "High"),
                    ("⚠️ Rebar and reinforcement data may not transfer",          "High"),
                    ("⚠️ Steel connection details may lose classification",        "Medium"),
                ]
            elif any(k in combined for k in ["navisworks", "navis"]):
                tool = "Autodesk Navisworks"
                risks = [
                    ("⚠️ Navisworks re-export often strips all Pset data",        "Critical"),
                    ("⚠️ Nearly all elements may become IfcBuildingElementProxy", "Critical"),
                    ("⚠️ GlobalIds may be regenerated — losing element tracking", "High"),
                ]
            elif any(k in combined for k in ["vectorworks"]):
                tool = "Vectorworks"
                risks = [
                    ("⚠️ Space objects may not export correctly",                 "Medium"),
                    ("⚠️ Some parametric objects may lose type information",      "Medium"),
                ]
            elif any(k in combined for k in ["sketchup", "sketch up"]):
                tool = "SketchUp"
                risks = [
                    ("⚠️ Most elements export as generic proxies",               "Critical"),
                    ("⚠️ No Pset data exported by default",                      "Critical"),
                    ("⚠️ No floor/storey assignment preserved",                  "High"),
                ]
            elif any(k in combined for k in ["allplan"]):
                tool = "Nemetschek Allplan"
                risks = [
                    ("⚠️ Reinforcement elements may lose classification",         "Medium"),
                    ("⚠️ Some Psets may use non-standard names",                  "Low"),
                ]
            else:
                tool = "Unknown / Generic IFC Exporter"
                risks = [
                    ("ℹ️ Export source not detected from header metadata",        "Info"),
                    ("ℹ️ Run full validation to identify actual issues",          "Info"),
                ]

            # Extract IFC schema version
            ifc_version = "Unknown"
            if "IFC4" in schema:   ifc_version = "IFC4"
            elif "IFC2X3" in schema: ifc_version = "IFC2X3 (Legacy)"
            elif "IFC2" in schema:   ifc_version = "IFC2.x (Old)"

            return tool, ifc_version, risks
        except Exception:
            return "Unknown", "Unknown", [("ℹ️ Could not read IFC header metadata", "Info")]

    export_tool, ifc_version, export_risks = detect_export_source(model)
    st.session_state["export_source"] = {
        "tool":    export_tool,
        "version": ifc_version,
        "risks":   export_risks,
    }

    prog_bar.progress(42, text="📊 Scanning elements (optimised for large files)...")

    # ── Single pass — collect everything at once ──────────────────────────────
    # Use frozenset for O(1) lookup — critical for 500 MB files with 50k+ elements
    SKIP_TYPES = frozenset({
        "IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
        "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject",
        "IfcRelAggregates","IfcZone","IfcSpatialZone","IfcRelContainedInSpatialStructure",
    })
    walls          = []
    standard_walls = []
    doors          = []
    windows        = []
    proxies        = []
    all_elements   = []

    # Count total for progress
    all_products = model.by_type("IfcProduct")
    total_products = len(all_products)
    UPDATE_EVERY = max(1, total_products // 20)   # update bar every 5%

    for idx, elem in enumerate(all_products):
        t = elem.is_a()
        if t in SKIP_TYPES:
            continue
        all_elements.append(elem)
        if   t == "IfcWall":                    walls.append(elem)
        elif t == "IfcWallStandardCase":        standard_walls.append(elem)
        elif t == "IfcDoor":                    doors.append(elem)
        elif t == "IfcWindow":                  windows.append(elem)
        elif t == "IfcBuildingElementProxy":    proxies.append(elem)

        # Update progress bar every 5% to avoid UI overhead
        if idx % UPDATE_EVERY == 0:
            pct = 42 + int(idx / total_products * 25)
            prog_bar.progress(pct, text=f"📊 Scanning elements... {idx:,} / {total_products:,}")

    del all_products   # free list reference

    total_elements    = len(all_elements)
    total_walls       = len(walls) + len(standard_walls)
    proxy_elements    = len(proxies)
    # Semantic = ALL typed elements that are NOT proxy
    # This means after reclassification, score improves correctly
    semantic_elements = total_elements - proxy_elements
    other_semantic    = max(semantic_elements - total_walls - len(doors) - len(windows), 0)
    # Each category is a separate slice — all must add to 100%
    # Walls + Doors + Windows + Proxy + Other = Total  →  sum = 100%
    walls_pct  = (total_walls          / total_elements) * 100 if total_elements else 0
    doors_pct  = (len(doors)           / total_elements) * 100 if total_elements else 0
    windows_pct= (len(windows)         / total_elements) * 100 if total_elements else 0
    proxy_pct  = (proxy_elements       / total_elements) * 100 if total_elements else 0
    other_pct  = (other_semantic       / total_elements) * 100 if total_elements else 0
    # semantic_pct = everything except proxy (used for score formula)
    semantic_pct = 100 - proxy_pct if total_elements else 0

    if proxy_pct <= 10:  severity = "LOW"
    elif proxy_pct < 20: severity = "MEDIUM"
    elif proxy_pct < 50: severity = "HIGH"
    else:                severity = "CRITICAL"

    # ── Model Quality Score (0–100) ────────────────────────────────────────────
    prog_bar.progress(68, text="📋 Checking property sets...")

    # Check Psets for ALL element types — not just walls
    # Any IfcPropertySet counts — covers Wall, Door, Pipe, Light etc.
    STANDARD_PSETS = {
        "Pset_WallCommon", "Pset_DoorCommon", "Pset_WindowCommon",
        "Pset_SlabCommon", "Pset_ColumnCommon", "Pset_BeamCommon",
        "Pset_RoofCommon", "Pset_StairCommon", "Pset_RailingCommon",
        "Pset_PipeSegmentTypeCommon", "Pset_PipeFittingTypeCommon",
        "Pset_FlowSegmentTypeCommon", "Pset_FlowTerminalTypeCommon",
        "Pset_LightFixtureTypeCommon", "Pset_ElectricalDeviceCommon",
        "Pset_EnergyConversionDeviceCommon", "Pset_ManufacturerTypeInformation",
        "Pset_DistributionSystemCommon", "Pset_PlantCommon",
        "Pset_BuildingElementCommon",
    }

    _total_walls_q   = len(walls) + len(standard_walls)

    # ── Pset requirement map — every type that should have a Pset ────────────
    ELEM_PSET_MAP = {
        "IfcWall":                  "Pset_WallCommon",
        "IfcWallStandardCase":      "Pset_WallCommon",
        "IfcDoor":                  "Pset_DoorCommon",
        "IfcWindow":                "Pset_WindowCommon",
        "IfcSlab":                  "Pset_SlabCommon",
        "IfcColumn":                "Pset_ColumnCommon",
        "IfcBeam":                  "Pset_BeamCommon",
        "IfcRoof":                  "Pset_RoofCommon",
        "IfcStair":                 "Pset_StairCommon",
        "IfcRailing":               "Pset_RailingCommon",
        "IfcPipeSegment":           "Pset_PipeSegmentTypeCommon",
        "IfcPipeFitting":           "Pset_PipeFittingTypeCommon",
        "IfcFlowSegment":           "Pset_FlowSegmentTypeCommon",
        "IfcFlowTerminal":          "Pset_FlowTerminalTypeCommon",
        "IfcMechanicalEquipment":   "Pset_ManufacturerTypeInformation",
        "IfcEnergyConversionDevice":"Pset_EnergyConversionDeviceCommon",
        "IfcElectricalElement":     "Pset_ElectricalDeviceCommon",
        "IfcLightFixture":          "Pset_LightFixtureTypeCommon",
        "IfcDistributionElement":   "Pset_DistributionSystemCommon",
        "IfcPlant":                 "Pset_PlantCommon",
    }

    _walls_with_pset = 0
    walls_missing_pset_set = set()
    missing_pset_all = []   # all elements missing their required pset

    # Count walls missing Pset_WallCommon (backward compat)
    for _w in walls:
        _has = False
        for _d in getattr(_w, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcPropertySet") and _ps.Name == "Pset_WallCommon":
                    _has = True; break
        if _has:
            _walls_with_pset += 1
        else:
            walls_missing_pset_set.add(_w.GlobalId)

    # Check ALL elements for their required Pset
    _elems_with_pset = 0
    for _elem in all_elements:
        _etype    = _elem.is_a()
        _req_pset = ELEM_PSET_MAP.get(_etype)
        _has_any  = False
        _has_req  = False
        for _d in getattr(_elem, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcPropertySet"):
                    _has_any = True
                    if _req_pset and _ps.Name == _req_pset:
                        _has_req = True; break
        if _req_pset:
            if _has_req:
                _elems_with_pset += 1
            else:
                missing_pset_all.append({
                    "Element Name": _elem.Name or "Unnamed",
                    "GlobalId":     _elem.GlobalId,
                    "IFC Type":     _etype,
                    "Required Pset":_req_pset,
                    "Issue":        f"Missing {_req_pset}",
                })
        else:
            # Type has no standard pset requirement — count as ok
            _elems_with_pset += 1



    # Score uses pset coverage among elements that REQUIRE a pset
    _elems_requiring_pset = _elems_with_pset + len(missing_pset_all)
    _pset_score  = (_elems_with_pset / _elems_requiring_pset * 40) if _elems_requiring_pset else 40
    _pset_pct    = round(_elems_with_pset / _elems_requiring_pset * 100, 1) if _elems_requiring_pset else 100
    # Note: _sem_score, _proxy_score, quality_score calculated after 4-level detection below

    # ── 4-Level Data Loss Detection ──────────────────────────────────────────
    prog_bar.progress(75, text="🔗 Checking relationships and geometry...")

    # Level 1 — Type Loss (proxy)
    _type_loss_count  = proxy_elements
    _type_loss_pct    = round(proxy_pct, 1)

    # Level 2 — Property Loss (missing psets)
    _prop_loss_count  = len(missing_pset_all)
    _prop_loss_pct    = round(_prop_loss_count / _elems_requiring_pset * 100, 1) if _elems_requiring_pset else 0

    # Level 3 — Relationship Loss
    _rel_loss = []
    for _elem in all_elements:
        _etype = _elem.is_a()
        if _etype in ("IfcBuildingElementProxy",): continue
        # Check storey assignment
        _in_storey = any(
            r.is_a("IfcRelContainedInSpatialStructure") and
            getattr(r, "RelatingStructure", None) and
            r.RelatingStructure.is_a("IfcBuildingStorey")
            for r in getattr(_elem, "ContainedInStructure", [])
        )
        if not _in_storey:
            _rel_loss.append({"Name": _elem.Name or "Unnamed", "GlobalId": _elem.GlobalId,
                               "IFC Type": _etype, "Issue": "Not assigned to any storey"})
        # Check door/window hosted in wall
        if _etype in ("IfcDoor", "IfcWindow"):
            _hosted = any(r.is_a("IfcRelFillsElement")
                          for r in getattr(_elem, "FillsVoids", []))
            if not _hosted:
                _rel_loss.append({"Name": _elem.Name or "Unnamed", "GlobalId": _elem.GlobalId,
                                   "IFC Type": _etype, "Issue": "Not hosted in any wall opening"})
    _rel_loss_count = len(_rel_loss)
    _rel_loss_pct   = round(_rel_loss_count / max(total_elements, 1) * 100, 1)

    # Level 4 — Geometry Loss
    _geo_loss = []
    for _elem in all_elements:
        if not getattr(_elem, "Representation", None):
            _geo_loss.append({"Name": _elem.Name or "Unnamed", "GlobalId": _elem.GlobalId,
                               "IFC Type": _elem.is_a(), "Issue": "No geometry representation"})
    _geo_loss_count = len(_geo_loss)
    _geo_loss_pct   = round(_geo_loss_count / max(total_elements, 1) * 100, 1)

    # Level 5 — Quantity Loss (missing IfcElementQuantity / BaseQuantities)
    _qty_loss = []
    QTY_TYPES = {"IfcWall","IfcWallStandardCase","IfcSlab","IfcColumn","IfcBeam",
                 "IfcRoof","IfcDoor","IfcWindow","IfcStair"}
    for _elem in all_elements:
        _etype = _elem.is_a()
        if _etype not in QTY_TYPES:
            continue
        _has_qty = False
        for _d in getattr(_elem, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcElementQuantity"):
                    _has_qty = True; break
        if not _has_qty:
            _qty_loss.append({
                "Name":     _elem.Name or "Unnamed",
                "GlobalId": _elem.GlobalId,
                "IFC Type": _etype,
                "Issue":    "Missing IfcElementQuantity (no area/volume/length data)",
            })
    _qty_loss_count = len(_qty_loss)
    _qty_loss_pct   = round(_qty_loss_count / max(total_elements, 1) * 100, 1)

    # Relationship summary for dashboard + PDF report
    _relationship_catalog = [
        ("IfcRelContainedInSpatialStructure", "Element -> Storey assignment"),
        ("IfcRelDefinesByProperties",         "Element -> Property Sets (Psets)"),
        ("IfcRelAssociatesMaterial",          "Element -> Material"),
        ("IfcRelConnectsElements",            "Element <-> Element connection"),
        ("IfcRelFillsElement",                "Door/Window -> Wall opening"),
        ("IfcRelAggregates",                  "Element -> Parent assembly"),
        ("IfcRelAssociatesClassification",    "Element -> Classification system"),
    ]
    _relationship_summary = []
    for _rel_type, _meaning in _relationship_catalog:
        try:
            _count = len(model.by_type(_rel_type))
        except Exception:
            _count = 0
        if _count > 0:
            _relationship_summary.append({
                "Relationship": _rel_type,
                "Meaning": _meaning,
                "Count": _count,
            })

    # ── Weighted 5-level data loss score (new formula) ──────────────────────
    # Total Loss % = (0.30 × Semantic) + (0.20 × Property) + (0.15 × Quantity)
    #              + (0.25 × Relationship) + (0.10 × Geometry)
    _data_loss_score = round(
        (_type_loss_pct  / 100) * 30 +
        (_prop_loss_pct  / 100) * 20 +
        (_qty_loss_pct   / 100) * 15 +
        (_rel_loss_pct   / 100) * 25 +
        (_geo_loss_pct   / 100) * 10,
    1)
    _data_integrity = round(100 - _data_loss_score, 1)

    # ── Quality score (calculated BEFORE score_breakdown) ────────────────────
    _sem_score   = semantic_pct / 100 * 60
    _proxy_score = (proxy_pct / 100) * 30
    quality_score = round(min(100, max(0, _sem_score - _proxy_score + _pset_score)), 1)
    if   quality_score >= 85: quality_grade, quality_color = "Excellent", "#238636"
    elif quality_score >= 70: quality_grade, quality_color = "Good",      "#58a6ff"
    elif quality_score >= 50: quality_grade, quality_color = "Fair",      "#3ab8d9"
    else:                     quality_grade, quality_color = "Poor",      "#ff7070"
    if   proxy_pct <= 10: severity = "LOW"
    elif proxy_pct < 20:  severity = "MEDIUM"
    elif proxy_pct < 50:  severity = "HIGH"
    else:                 severity = "CRITICAL"

    _score_breakdown = {
        "sem_score":      round(_sem_score, 1),
        "proxy_score":    round(_proxy_score, 1),
        "pset_score":     round(_pset_score, 1),
        "sem_pct":        round(semantic_pct, 1),
        "proxy_pct":      round(proxy_pct, 1),
        "pset_pct":       _pset_pct,
        "elems_requiring_pset": _elems_requiring_pset,
        "walls_total":    _total_walls_q,
        "walls_with_pset":_walls_with_pset,
        "elems_with_pset":_elems_with_pset,
    }
    if   quality_score >= 85: quality_grade, quality_color = "Excellent", "#238636"
    elif quality_score >= 70: quality_grade, quality_color = "Good",      "#58a6ff"
    elif quality_score >= 50: quality_grade, quality_color = "Fair",      "#3ab8d9"
    else:                     quality_grade, quality_color = "Poor",      "#ff7070"

    prog_bar.progress(85, text="🧮 Building analysis data...")
    # walls_missing_pset already computed above in single pass
    walls_missing_pset = [w for w in walls if w.GlobalId in walls_missing_pset_set]
    # missing_pset_all already built in pset loop above

    # Store everything — persists across page switches
    prog_bar.progress(98, text="✅ Almost done...")
    st.session_state.model_loaded = True
    st.session_state.analysis = {
        "total_elements":    total_elements,
        "total_walls":       total_walls,
        "doors":             len(doors),
        "windows":           len(windows),
        "proxy_elements":    proxy_elements,
        "other_semantic":    other_semantic,
        "semantic_elements": semantic_elements,
        "semantic_pct":      semantic_pct,
        "proxy_pct":         proxy_pct,
        "other_pct":         other_pct,
        "walls_pct":         walls_pct,
        "doors_pct":         doors_pct,
        "windows_pct":       windows_pct,
        "severity":          severity,
        "quality_score":     quality_score,
        "quality_grade":     quality_grade,
        "quality_color":     quality_color,
        "score_breakdown":   _score_breakdown,
        # Cap at 500 entries for large models — show count always
        "proxy_list": [{
            "Name":     p.Name or "Unnamed",
            "GlobalId": p.GlobalId,
            "IFC Type": p.is_a(),
            "Issue":    "Semantic meaning lost (generic proxy)",
        } for p in proxies[:500]],
        "proxy_list_total":   len(proxies),
        "missing_pset_list":     missing_pset_all[:500],
        "missing_pset_count":    len(missing_pset_all),
        "rel_loss_list":         _rel_loss[:500],
        "rel_loss_count":        _rel_loss_count,
        "rel_loss_pct":          _rel_loss_pct,
        "geo_loss_list":         _geo_loss[:500],
        "geo_loss_count":        _geo_loss_count,
        "geo_loss_pct":          _geo_loss_pct,
        "qty_loss_list":         _qty_loss[:500],
        "qty_loss_count":        _qty_loss_count,
        "qty_loss_pct":          _qty_loss_pct,
        "type_loss_count":       _type_loss_count,
        "prop_loss_count":       _prop_loss_count,
        "prop_loss_pct":         _prop_loss_pct,
        "rel_loss_count":        _rel_loss_count,
        "rel_loss_pct":          _rel_loss_pct,
        "geo_loss_count":        _geo_loss_count,
        "geo_loss_pct":          _geo_loss_pct,
        "data_loss_score":       _data_loss_score,
        "data_integrity":        _data_integrity,
        "relationship_summary":  _relationship_summary,
        "type_loss_pct":         _type_loss_pct,
        "prop_loss_count":       _prop_loss_count,
        "prop_loss_pct":         _prop_loss_pct,
        "walls_missing_pset":    [{"Wall Name": w.Name or "Unnamed",
                                   "GlobalId": w.GlobalId,
                                   "Issue": "Pset_WallCommon missing"}
                                   for w in walls_missing_pset[:500]],
    }
    file_size_mb = 0
    prog_bar.progress(100, text=f"✅ Done! {total_elements} elements loaded from {file_size_mb:.1f} MB file.")
    st.success(f"✅ IFC file analysed — {total_elements} elements, {proxy_elements} proxies")

# ══════════════════════════════════════════════════════════════════════════════
# RENDER ANALYSIS — Adaptive per view mode
# ══════════════════════════════════════════════════════════════════════════════
an   = st.session_state.analysis
_view = st.session_state.get("view_mode", "Full")

# ── Mode toggle bar — visible on every page load ───────────────────────────────
if an:
    st.markdown("---")
    _mc = {"Technical":"#58a6ff","Business":"#f0a500","Full":"#238636"}[_view]
    _tog1, _tog2, _tog3, _tog_info = st.columns([1,1,1,4])
    if _tog1.button("🔬 Technical", use_container_width=True,
                    type="primary" if _view=="Technical" else "secondary", key="hm_tech"):
        st.session_state.view_mode = "Technical"; st.rerun()
    if _tog2.button("💼 Business", use_container_width=True,
                    type="primary" if _view=="Business" else "secondary", key="hm_biz"):
        st.session_state.view_mode = "Business"; st.rerun()
    if _tog3.button("📊 Full", use_container_width=True,
                    type="primary" if _view=="Full" else "secondary", key="hm_full"):
        st.session_state.view_mode = "Full"; st.rerun()
    _tog_info.markdown(f"""
<div style="background:{_mc}12;border:1px solid {_mc}40;border-radius:8px;
padding:8px 16px;display:flex;align-items:center;gap:10px;height:38px;">
  <span style="font-size:16px;">{"🔬" if _view=="Technical" else "💼" if _view=="Business" else "📊"}</span>
  <span style="font-size:13px;font-weight:700;color:{_mc};">{_view} Mode</span>
  <span style="font-size:11px;color:#8b949e;">·
    {"IFC classes · GlobalIds · Psets · Schema · Relationships"
     if _view=="Technical" else
     "Cost impact · Delay risk · Project readiness · Plain English"
     if _view=="Business" else
     "Complete view — Technical + Business combined"}
  </span>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 💼 BUSINESS MODE — completely different layout
# ══════════════════════════════════════════════════════════════════════════════
if an and _view == "Business":
    total_e   = an["total_elements"]
    sem_count = an["semantic_elements"]
    prx_count = an["proxy_elements"]
    prx_pct   = an["proxy_pct"]
    sem_pct   = round(sem_count / total_e * 100, 1) if total_e else 0
    q_score   = an.get("quality_score", 0)
    severity  = an.get("severity", "LOW")

    delay     = "High" if prx_pct > 30 else "Medium" if prx_pct > 10 else "Low"
    delay_col = "#da3633" if delay=="High" else "#d29922" if delay=="Medium" else "#238636"
    readiness = "Not Ready" if q_score < 50 else "Needs Work" if q_score < 75 else "Ready"
    ready_col = "#da3633" if q_score < 50 else "#d29922" if q_score < 75 else "#238636"
    usability = f"{sem_pct:.0f}%"

    # ── Big readiness score ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"""
<div style="background:{ready_col}10;border:2px solid {ready_col};border-radius:16px;
padding:24px 32px;display:flex;justify-content:space-between;align-items:center;
flex-wrap:wrap;gap:20px;margin-bottom:20px;">
  <div>
    <div style="font-size:11px;color:#8b949e;letter-spacing:2px;margin-bottom:6px;">
      MODEL READINESS SCORE
    </div>
    <div style="font-size:56px;font-weight:900;color:{ready_col};line-height:1;">
      {q_score}<span style="font-size:24px;color:#8b949e;">/100</span>
    </div>
    <div style="font-size:16px;font-weight:700;color:{ready_col};margin-top:4px;">
      {readiness}
    </div>
    <div style="font-size:12px;color:#8b949e;margin-top:4px;">
      {"Model needs significant fixes before use in costing or compliance."
       if q_score < 50 else
       "Model has some issues — fix before sharing with consultants."
       if q_score < 75 else
       "Model is ready for downstream use."}
    </div>
  </div>
  <div style="display:flex;gap:20px;flex-wrap:wrap;">
    <div style="text-align:center;background:#161b22;border-radius:12px;
    padding:16px 24px;min-width:110px;">
      <div style="font-size:11px;color:#8b949e;letter-spacing:1px;margin-bottom:6px;">
        DELAY RISK
      </div>
      <div style="font-size:28px;font-weight:900;color:{delay_col};">{delay}</div>
      <div style="font-size:10px;color:#8b949e;margin-top:4px;">{prx_count} elements need fixing</div>
    </div>
    <div style="text-align:center;background:#161b22;border-radius:12px;
    padding:16px 24px;min-width:110px;">
      <div style="font-size:11px;color:#8b949e;letter-spacing:1px;margin-bottom:6px;">
        USABLE FOR COSTING
      </div>
      <div style="font-size:28px;font-weight:900;color:#58a6ff;">{usability}</div>
      <div style="font-size:10px;color:#8b949e;margin-top:4px;">{sem_count} of {total_e} elements</div>
    </div>
    <div style="text-align:center;background:#161b22;border-radius:12px;
    padding:16px 24px;min-width:110px;">
      <div style="font-size:11px;color:#8b949e;letter-spacing:1px;margin-bottom:6px;">
        TOTAL ELEMENTS
      </div>
      <div style="font-size:28px;font-weight:900;color:#e6edf3;">{total_e}</div>
      <div style="font-size:10px;color:#8b949e;margin-top:4px;">in this model</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── What's wrong — plain English issue list ────────────────────────────────
    l1c = an.get("type_loss_count",  prx_count)
    l2c = an.get("prop_loss_count",  an.get("missing_pset_count", 0))
    l3c = an.get("qty_loss_count",   0)
    l4c = an.get("rel_loss_count",   0)
    l5c = an.get("geo_loss_count",   0)
    l1  = an.get("type_loss_pct",    prx_pct)
    l2  = an.get("prop_loss_pct",    0)
    l3  = an.get("qty_loss_pct",     0)
    l4  = an.get("rel_loss_pct",     0)
    l5  = an.get("geo_loss_pct",     0)

    issues_list = [
        (l1c, l1, "🔴", "Elements have no type",
         "Cannot be used for quantity takeoffs, clash detection, or scheduling.",
         "Go to Corrections page to reclassify them.", "#da3633"),
        (l2c, l2, "🟡", "Elements missing required properties",
         "Incomplete data means wrong quantities and unreliable cost estimates.",
         "Go to Model Analysis → Pset Analysis to see which elements.", "#d29922"),
        (l4c, l4, "🔵", "Elements not assigned to any floor",
         "Space analysis and floor-by-floor reporting will be incomplete.",
         "Go to Visualization → Storey Quality to review.", "#58a6ff"),
        (l5c, l5, "🟣", "Elements are invisible (no geometry)",
         "These elements cannot be seen in any viewer or clash-checked.",
         "Go to Model Analysis → Geometry Integrity to fix.", "#c084fc"),
        (l3c, l3, "🟠", "Elements missing area/volume data",
         "Cost estimation and material take-offs will be inaccurate.",
         "Check element properties in your BIM authoring tool.", "#ff7c2a"),
    ]

    has_issues = any(c > 0 for c, *_ in issues_list)
    st.markdown(f"""
<div style="font-size:14px;font-weight:700;color:#e6edf3;margin-bottom:12px;">
  {"⚠️ Issues Found — Action Required" if has_issues else "✅ No Issues Found"}
</div>
""", unsafe_allow_html=True)

    if has_issues:
        for count, pct, icon, title, impact, action, color in issues_list:
            if count == 0:
                continue
            st.markdown(f"""
<div style="background:#161b22;border:1px solid {color}30;border-left:4px solid {color};
border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:10px;
display:flex;gap:16px;align-items:flex-start;">
  <div style="font-size:24px;flex-shrink:0;">{icon}</div>
  <div style="flex:1;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
      <div style="font-size:14px;font-weight:700;color:#e6edf3;">{count} {title}</div>
      <div style="background:{color}20;color:{color};border:1px solid {color}40;
      border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700;">{pct:.1f}%</div>
    </div>
    <div style="font-size:12px;color:#8b949e;margin-top:6px;">
      <strong style="color:#e6edf3;">Impact:</strong> {impact}
    </div>
    <div style="font-size:11px;color:{color};margin-top:4px;">
      ➜ {action}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.success("✅ All checks passed — model is clean and ready for downstream use.")

    # ── Quick action buttons ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
<div style="font-size:13px;font-weight:700;color:#e6edf3;margin-bottom:12px;">
  🚀 Quick Actions
</div>
""", unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)
    qa1.page_link("pages/4_🛠️_Corrections.py",              label="🛠️ Fix Elements",    use_container_width=True)
    qa2.page_link("pages/3_✅_Validation_&_Compliance.py",   label="✅ Check Compliance", use_container_width=True)
    qa3.page_link("pages/5_📄_Reports_&_Export.py",          label="📄 Get Report",       use_container_width=True)
    qa4.page_link("pages/2_📊_Visualization_&_Insights.py",  label="📊 View Model",       use_container_width=True)

    # ── Export Source (simplified) ─────────────────────────────────────────────
    _src = st.session_state.get("export_source", {})
    if _src:
        st.markdown("---")
        st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
padding:14px 20px;display:flex;gap:24px;flex-wrap:wrap;align-items:center;">
  <div>
    <div style="font-size:10px;color:#8b949e;letter-spacing:1px;">MODEL CREATED WITH</div>
    <div style="font-size:16px;font-weight:700;color:#e6edf3;">🏗️ {_src.get("tool","Unknown")}</div>
  </div>
  <div>
    <div style="font-size:10px;color:#8b949e;letter-spacing:1px;">FILE FORMAT</div>
    <div style="font-size:16px;font-weight:700;color:#58a6ff;">{_src.get("version","Unknown")}</div>
  </div>
  <div style="flex:1;font-size:12px;color:#8b949e;">
    {"⚠️ This tool is known to produce proxy elements during export. Use Corrections to fix."
     if any(sev in ("Critical","High") for _,sev in _src.get("risks",[]))
     else "✅ Export tool has low risk of data loss."}
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔬 TECHNICAL MODE + 📊 FULL MODE — original detailed dashboard
# ══════════════════════════════════════════════════════════════════════════════
if an and _view in ("Technical", "Full"):
    # ── Export Source Risk Prediction (shown FIRST) ───────────────────────────
    src = st.session_state.get("export_source", {})
    if src:
        st.markdown("---")
        st.subheader("🔍 IFC Export Source Analysis")
        tool    = src.get("tool", "Unknown")
        version = src.get("version", "Unknown")
        risks   = src.get("risks", [])

        sev_color = {"Critical":"#ff7070","High":"#3ab8d9","Medium":"#58a6ff","Low":"#238636","Info":"#8b949e"}

        tc1, tc2 = st.columns([1, 2])
        with tc1:
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:16px;">
  <div style="font-size:11px;color:#8b949e;letter-spacing:1px;margin-bottom:8px;">EXPORT TOOL DETECTED</div>
  <div style="font-size:16px;font-weight:800;color:#f0f4f8;margin-bottom:8px;">🏗️ {tool}</div>
  <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">IFC Schema Version</div>
  <div style="font-size:13px;font-weight:700;color:#58a6ff;">{version}</div>
</div>""", unsafe_allow_html=True)

        with tc2:
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:16px;">
  <div style="font-size:11px;color:#8b949e;letter-spacing:1px;margin-bottom:10px;">PREDICTED SEMANTIC LOSS RISKS</div>
""" + "".join([
    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">'
    f'<span style="background:{sev_color.get(sev,"#8b949e")}22;color:{sev_color.get(sev,"#8b949e")};'
    f'border:1px solid {sev_color.get(sev,"#8b949e")};border-radius:4px;padding:1px 7px;'
    f'font-size:10px;font-weight:700;flex-shrink:0;">{sev}</span>'
    f'<span style="font-size:12px;color:#f0f4f8;">{risk}</span></div>'
    for risk, sev in risks
]) + "</div>", unsafe_allow_html=True)

        # Prediction vs Reality
        actual_issues = an.get("proxy_elements", 0) + an.get("missing_pset_count", 0)
        high_risk_count = sum(1 for _, sev in risks if sev in ("Critical","High"))
        match_color = "#238636" if high_risk_count > 0 and actual_issues > 0 else "#8b949e"
        st.markdown(f"""
<div style="background:{match_color}18;border:1px solid {match_color};border-radius:8px;
padding:10px 16px;margin-top:8px;display:flex;gap:24px;flex-wrap:wrap;">
  <div><span style="color:#8b949e;font-size:11px;">PREDICTED RISKS</span><br>
  <strong style="color:{match_color};font-size:16px;">{high_risk_count} High/Critical</strong></div>
  <div><span style="color:#8b949e;font-size:11px;">ACTUAL ISSUES DETECTED</span><br>
  <strong style="color:{match_color};font-size:16px;">{actual_issues} Issues Found</strong></div>
  <div style="flex:1;min-width:180px;"><span style="color:#8b949e;font-size:11px;">VERDICT</span><br>
  <strong style="color:{match_color};font-size:13px;">
  {"✅ Prediction confirmed — issues match known risks for " + tool
   if high_risk_count > 0 and actual_issues > 0
   else "✅ Model is cleaner than typical " + tool + " exports"
   if actual_issues == 0
   else "ℹ️ Issues detected — check validation results"}</strong></div>
</div>""", unsafe_allow_html=True)

    # ── Summary metrics — 3 clean cards ────────────────────────────────────────
    st.markdown("---")
    st.header("📊 Summary Metrics")

    # Always use original upload data — corrections do not update Summary Metrics
    total_e   = an["total_elements"]
    sem_count = an["semantic_elements"]
    prx_count = an["proxy_elements"]
    prx_pct   = an["proxy_pct"]
    sem_pct   = round(sem_count / total_e * 100, 1) if total_e else 0

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("📦 Total Elements",   total_e,
               help="All IfcProduct entities excluding spaces, openings and annotations")
    mc2.metric("✅ Semantic",         f"{sem_count}  ({sem_pct:.1f}%)",
               help="Correctly typed elements — walls, doors, columns, pipes etc. (not proxy)")
    mc3.metric("🔴 Proxy",            f"{prx_count}  ({prx_pct:.1f}%)",
               help="IfcBuildingElementProxy — lost semantic type during export")

    # ── STEP Syntax Validation ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔎 STEP Syntax Validation")
    st.caption("Verifies that the IFC file is a structurally valid STEP/P21 file at the parsing level.")

    # Always validate the original upload — corrections are not reflected here
    _step_model_label = "original upload"
    try:
        _step_model = ifcopenshell.open("temp.ifc")
    except Exception:
        _step_model = None
        _step_model_label = "unavailable (original model could not be read)"

    # Run validation checks against the chosen model
    _step_checks = []

    # Check 1 — File parseable
    if _step_model is not None:
        _step_checks.append({
            "check":   "File Parseable",
            "status":  "pass",
            "detail":  f"ifcopenshell opened the {_step_model_label} without errors — STEP/P21 syntax is valid.",
        })
    else:
        _step_checks.append({
            "check":   "File Parseable",
            "status":  "fail",
            "detail":  "Could not open the original IFC model for STEP validation.",
        })

    # Check 2 — Schema version declared
    try:
        _schema = _step_model.schema
        if _schema:
            _step_checks.append({
                "check":  "Schema Version Declared",
                "status": "pass",
                "detail": f"Schema: {_schema}",
            })
        else:
            _step_checks.append({
                "check":  "Schema Version Declared",
                "status": "warn",
                "detail": "Schema string is empty or None in file header.",
            })
    except Exception:
        _step_checks.append({
            "check":  "Schema Version Declared",
            "status": "warn",
            "detail": "Could not read schema from model header.",
        })

    # Check 3 — IfcProject entity present (mandatory root entity)
    try:
        _projects = _step_model.by_type("IfcProject")
        if _projects:
            _proj_name = getattr(_projects[0], "Name", None) or "Unnamed"
            _step_checks.append({
                "check":  "IfcProject Entity Present",
                "status": "pass",
                "detail": f"Found IfcProject: '{_proj_name}'",
            })
        else:
            _step_checks.append({
                "check":  "IfcProject Entity Present",
                "status": "fail",
                "detail": "No IfcProject entity found — file may be a partial/fragment export.",
            })
    except Exception as _e:
        _step_checks.append({
            "check":  "IfcProject Entity Present",
            "status": "fail",
            "detail": f"Error checking IfcProject: {_e}",
        })

    # Check 4 — OwnerHistory present (traceability)
    try:
        _oh = _step_model.by_type("IfcOwnerHistory")
        if _oh:
            _step_checks.append({
                "check":  "OwnerHistory Present",
                "status": "pass",
                "detail": f"{len(_oh)} IfcOwnerHistory record(s) — authorship metadata intact.",
            })
        else:
            _step_checks.append({
                "check":  "OwnerHistory Present",
                "status": "warn",
                "detail": "No IfcOwnerHistory found — file traceability is missing.",
            })
    except Exception:
        _step_checks.append({
            "check":  "OwnerHistory Present",
            "status": "warn",
            "detail": "Could not check IfcOwnerHistory.",
        })

    # Check 5 — No duplicate GlobalIds
    try:
        _all_gids = [e.GlobalId for e in _step_model.by_type("IfcRoot") if hasattr(e, "GlobalId")]
        _dup_count = len(_all_gids) - len(set(_all_gids))
        if _dup_count == 0:
            _step_checks.append({
                "check":  "GlobalId Uniqueness",
                "status": "pass",
                "detail": f"All {len(_all_gids)} GlobalIds are unique.",
            })
        else:
            _step_checks.append({
                "check":  "GlobalId Uniqueness",
                "status": "fail",
                "detail": f"{_dup_count} duplicate GlobalId(s) detected — element tracking will be unreliable.",
            })
    except Exception as _e:
        _step_checks.append({
            "check":  "GlobalId Uniqueness",
            "status": "warn",
            "detail": f"Could not verify GlobalIds: {_e}",
        })

    # Check 6 — IfcUnits / unit assignment
    try:
        _units = _step_model.by_type("IfcUnitAssignment")
        if _units:
            _step_checks.append({
                "check":  "Unit Assignment",
                "status": "pass",
                "detail": f"IfcUnitAssignment found with {len(getattr(_units[0], 'Units', []))} unit(s) defined.",
            })
        else:
            _step_checks.append({
                "check":  "Unit Assignment",
                "status": "warn",
                "detail": "No IfcUnitAssignment — unit interpretation (mm/m/ft) is ambiguous.",
            })
    except Exception:
        _step_checks.append({
            "check":  "Unit Assignment",
            "status": "warn",
            "detail": "Could not check IfcUnitAssignment.",
        })

    # Check 7 — At least one geometric representation context
    try:
        _ctx = _step_model.by_type("IfcGeometricRepresentationContext")
        if _ctx:
            _step_checks.append({
                "check":  "Geometry Context",
                "status": "pass",
                "detail": f"{len(_ctx)} IfcGeometricRepresentationContext(s) — coordinate system defined.",
            })
        else:
            _step_checks.append({
                "check":  "Geometry Context",
                "status": "fail",
                "detail": "No IfcGeometricRepresentationContext — all geometry placements may be invalid.",
            })
    except Exception:
        _step_checks.append({
            "check":  "Geometry Context",
            "status": "warn",
            "detail": "Could not check geometry context.",
        })

    # ── Render results ─────────────────────────────────────────────────────────
    _pass  = sum(1 for c in _step_checks if c["status"] == "pass")
    _warn  = sum(1 for c in _step_checks if c["status"] == "warn")
    _fail  = sum(1 for c in _step_checks if c["status"] == "fail")
    _total = len(_step_checks)

    # Overall verdict banner
    if _fail == 0 and _warn == 0:
        _verdict_col, _verdict_icon, _verdict_text = "#238636", "✅", "STEP Valid — All checks passed"
    elif _fail == 0:
        _verdict_col, _verdict_icon, _verdict_text = "#d29922", "⚠️", f"STEP Valid with {_warn} warning(s)"
    else:
        _verdict_col, _verdict_icon, _verdict_text = "#da3633", "❌", f"STEP Issues — {_fail} check(s) failed"

    st.markdown(f"""
<div style="background:{_verdict_col}18;border:2px solid {_verdict_col};border-radius:10px;
padding:12px 20px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
  <div>
    <span style="font-size:18px;font-weight:800;color:{_verdict_col};">{_verdict_icon} {_verdict_text}</span>
    <div style="font-size:12px;color:#8b949e;margin-top:3px;">
      {_pass} passed · {_warn} warnings · {_fail} failed · {_total} checks total
    </div>
  </div>
  <div style="display:flex;gap:16px;">
    <div style="text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#238636;">{_pass}</div>
      <div style="font-size:10px;color:#8b949e;">PASS</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#d29922;">{_warn}</div>
      <div style="font-size:10px;color:#8b949e;">WARN</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#da3633;">{_fail}</div>
      <div style="font-size:10px;color:#8b949e;">FAIL</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # Per-check rows — inside a dropdown
    _STATUS_CFG = {
        "pass": ("#238636", "✅", "PASS"),
        "warn": ("#d29922", "⚠️", "WARN"),
        "fail": ("#da3633", "❌", "FAIL"),
    }
    _expander_label = f"View {_total} checks — {_pass} passed · {_warn} warnings · {_fail} failed"
    with st.expander(_expander_label, expanded=False):
        for _c in _step_checks:
            _col, _ico, _lbl = _STATUS_CFG[_c["status"]]
            st.markdown(f"""
<div style="background:#161b22;border:1px solid {'#30363d' if _c['status']=='pass' else _col};
border-radius:8px;padding:10px 16px;margin-bottom:6px;
display:flex;align-items:center;gap:14px;">
  <span style="background:{_col}22;color:{_col};border:1px solid {_col};
  border-radius:4px;padding:2px 10px;font-size:11px;font-weight:700;white-space:nowrap;">
    {_ico} {_lbl}
  </span>
  <div style="flex:1;">
    <div style="font-size:13px;font-weight:700;color:#e6edf3;">{_c['check']}</div>
    <div style="font-size:11px;color:#8b949e;margin-top:2px;">{_c['detail']}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── 5-Level Data Loss Dashboard ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔬 5-Level Data Loss Analysis")
    st.caption("Semantic · Property · Quantity · Relationship · Geometry — all 5 levels of IFC data integrity.")

    l1  = an.get("type_loss_pct",   prx_pct)
    l2  = an.get("prop_loss_pct",   0)
    l3  = an.get("qty_loss_pct",    0)
    l4  = an.get("rel_loss_pct",    0)
    l5  = an.get("geo_loss_pct",    0)
    l1c = an.get("type_loss_count", prx_count)
    l2c = an.get("prop_loss_count", an.get("missing_pset_count",0))
    l3c = an.get("qty_loss_count",  0)
    l4c = an.get("rel_loss_count",  0)
    l5c = an.get("geo_loss_count",  0)

    def loss_col(pct):
        if pct == 0:    return "#238636"
        if pct <= 10:   return "#d29922"
        if pct <= 30:   return "#ff7070"
        return "#da3633"

    lc1, lc2, lc3, lc4, lc5 = st.columns(5)
    for col, lvl, label, pct, cnt, sub, weight in [
        (lc1,"L1","Semantic Loss",    l1, l1c, "IfcBuildingElementProxy","30%"),
        (lc2,"L2","Property Loss",    l2, l2c, "Missing Psets",          "20%"),
        (lc3,"L3","Quantity Loss",    l3, l3c, "No area/vol/length",     "15%"),
        (lc4,"L4","Relationship Loss",l4, l4c, "No storey/wall host",    "25%"),
        (lc5,"L5","Geometry Loss",    l5, l5c, "Invisible in viewer",    "10%"),
    ]:
        c = loss_col(pct)
        col.markdown(f"""
<div style="background:#161b22;border:1px solid {c};border-radius:10px;padding:12px;text-align:center;">
  <div style="font-size:9px;color:#8b949e;letter-spacing:1px;margin-bottom:2px;">{lvl} · Weight {weight}</div>
  <div style="font-size:11px;color:#e6edf3;font-weight:700;margin-bottom:6px;">{label}</div>
  <div style="font-size:22px;font-weight:800;color:{c};">{pct:.1f}%</div>
  <div style="font-size:11px;color:#8b949e;">{cnt} elements</div>
  <div style="font-size:10px;color:#8b949e;margin-top:4px;">{sub}</div>
</div>""", unsafe_allow_html=True)

    # ── Total Loss % and Model Score ──────────────────────────────────────────
    _total_loss_pct = round(
        (l1/100)*30 + (l2/100)*20 + (l3/100)*15 + (l4/100)*25 + (l5/100)*10, 1
    )
    _model_score = round(100 - _total_loss_pct * 100 / 100, 1)  # same as 100 - total_loss_pct (already a %)
    _model_score = max(0, min(100, round(100 - _total_loss_pct, 1)))
    _ms_col = "#238636" if _model_score>=85 else "#58a6ff" if _model_score>=70 else "#d29922" if _model_score>=50 else "#da3633"
    _ms_grade = "Excellent" if _model_score>=85 else "Good" if _model_score>=70 else "Fair" if _model_score>=50 else "Poor"

    st.markdown(f"""
<div style="background:#161b22;border:2px solid {_ms_col};border-radius:12px;
padding:16px 24px;margin-top:12px;display:flex;justify-content:space-between;
align-items:center;flex-wrap:wrap;gap:12px;">
  <div>
    <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:4px;">MODEL INTEGRITY SCORE</div>
    <div style="font-size:32px;font-weight:900;color:{_ms_col};">{_model_score}/100 — {_ms_grade}</div>
    <div style="font-size:12px;color:#8b949e;margin-top:4px;">
      Score = 100 − Total Loss% &nbsp;|&nbsp;
      Total Loss = 0.30×Semantic + 0.20×Property + 0.15×Quantity + 0.25×Relationship + 0.10×Geometry
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">Total Loss %</div>
    <div style="font-size:24px;font-weight:800;color:{_ms_col};">{_total_loss_pct}%</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("🧠 Automated Conclusion")
    if an["proxy_pct"] <= 10:
        st.success("The IFC model preserves semantic representation across all analyzed elements. No semantic degradation detected.")
    elif an["proxy_pct"] < 20:
        st.info("The IFC model largely preserves semantic meaning, with minor semantic degradation observed in a small subset of elements.")
    elif an["proxy_pct"] < 50:
        st.warning("The IFC model exhibits mixed semantic representation. Several building components are represented as proxy elements.")
    else:
        st.error("The IFC model shows significant semantic degradation. A large portion of elements are represented as generic proxy objects.")

    # Score moved to dedicated Model Score page
    q_col   = an.get("quality_color", "#8b949e")
    q_score = an.get("quality_score", "—")
    q_grade = an.get("quality_grade", "—")
    st.markdown(f"""
<div style="background:{q_col}18;border:1.5px solid {q_col};border-radius:10px;
padding:12px 20px;display:flex;justify-content:space-between;align-items:center;margin-top:10px;">
  <div>
    <span style="font-size:24px;font-weight:800;color:{q_col};">{q_score}/100</span>
    <span style="font-size:14px;color:{q_col};font-weight:700;margin-left:8px;">{q_grade}</span>
  </div>
  <div style="font-size:12px;color:#8b949e;">See full score breakdown in <strong style="color:{q_col};">📊 Model Score</strong> page</div>
</div>""", unsafe_allow_html=True)

    # ── Proxy element tracing ──────────────────────────────────────────────────
    st.subheader("🔍 Element‑Level Tracing (Proxy Elements)")
    proxy_total = an.get("proxy_list_total", len(an.get("proxy_list",[])))
    if an["proxy_list"]:
        if proxy_total > 500:
            st.warning(f"⚠️ Large model — showing first 500 of {proxy_total} proxy elements.")
        st.dataframe(pd.DataFrame(an["proxy_list"]), use_container_width=True)
    else:
        st.markdown('<p style="color:#8b949e">No proxy elements detected.</p>', unsafe_allow_html=True)

    # ── IFC Relationships ──────────────────────────────────────────────────────
    st.subheader("🔗 IFC Relationships")
    _rel_rows = an.get("relationship_summary", [])
    if not _rel_rows:
        try:
            _m = ifcopenshell.open("temp.ifc")
            _fallback_catalog = [
                ("IfcRelContainedInSpatialStructure", "Element -> Storey assignment"),
                ("IfcRelDefinesByProperties",         "Element -> Property Sets (Psets)"),
                ("IfcRelAssociatesMaterial",          "Element -> Material"),
                ("IfcRelConnectsElements",            "Element <-> Element connection"),
                ("IfcRelFillsElement",                "Door/Window -> Wall opening"),
                ("IfcRelAggregates",                  "Element -> Parent assembly"),
                ("IfcRelAssociatesClassification",    "Element -> Classification system"),
            ]
            for _rel_type, _meaning in _fallback_catalog:
                try:
                    _count = len(_m.by_type(_rel_type))
                except Exception:
                    _count = 0
                if _count > 0:
                    _rel_rows.append({
                        "Relationship": _rel_type,
                        "Meaning": _meaning,
                        "Count": _count,
                    })
        except Exception:
            _rel_rows = []

    if _rel_rows:
        st.dataframe(pd.DataFrame(_rel_rows), use_container_width=True, hide_index=True)
        st.caption(f"{len(_rel_rows)} relationship types found in this model.")
    else:
        st.info("No relationships found in this IFC model.")




    # ── PDF report ─────────────────────────────────────────────────────────────
    st.markdown("---")
    def generate_pdf(file_path="IFC_Analysis_Report.pdf"):
        def _safe(text):
            """FPDF default font is latin-1; replace unsupported chars."""
            return str(text).encode("latin-1", "replace").decode("latin-1")

        def _line(pdf_obj, text, h=7):
            pdf_obj.multi_cell(0, h, _safe(text))

        def _section(pdf_obj, title):
            pdf_obj.ln(3)
            pdf_obj.set_font("Arial", "B", 12)
            _line(pdf_obj, title, 8)
            pdf_obj.set_font("Arial", size=11)

        _total_loss_pct = an.get("data_loss_score", 0)
        _model_score = an.get("data_integrity", max(0, round(100 - _total_loss_pct, 1)))

        _l1 = an.get("type_loss_pct", an.get("proxy_pct", 0))
        _l2 = an.get("prop_loss_pct", 0)
        _l3 = an.get("qty_loss_pct", 0)
        _l4 = an.get("rel_loss_pct", 0)
        _l5 = an.get("geo_loss_pct", 0)

        _l1c = an.get("type_loss_count", an.get("proxy_elements", 0))
        _l2c = an.get("prop_loss_count", an.get("missing_pset_count", 0))
        _l3c = an.get("qty_loss_count", 0)
        _l4c = an.get("rel_loss_count", 0)
        _l5c = an.get("geo_loss_count", 0)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        _line(pdf, "IFC Home Dashboard Report", 10)
        pdf.set_font("Arial", size=11)
        _line(pdf, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        _line(pdf, f"User Name: {context.get('name', 'N/A')}")
        _line(pdf, f"Role: {context.get('role', 'N/A')} | Domain: {context.get('domain', 'N/A')} | Purpose: {context.get('purpose', 'N/A')}")

        _section(pdf, "1) Summary Metrics")
        _line(pdf, f"Total Elements: {an.get('total_elements', 0)}")
        _line(pdf, f"Semantic Elements: {an.get('semantic_elements', 0)} ({an.get('semantic_pct', 0):.1f}%)")
        _line(pdf, f"Proxy Elements: {an.get('proxy_elements', 0)} ({an.get('proxy_pct', 0):.1f}%)")
        _line(pdf, f"Other Semantic Elements: {an.get('other_semantic', 0)} ({an.get('other_pct', 0):.1f}%)")
        _line(pdf, f"Severity Level: {an.get('severity', 'N/A')}")

        _section(pdf, "2) 5-Level Data Loss Analysis + Model Score")
        _line(pdf, f"L1 Semantic Loss (30%): {_l1:.1f}% | {_l1c} elements")
        _line(pdf, f"L2 Property Loss (20%): {_l2:.1f}% | {_l2c} elements")
        _line(pdf, f"L3 Quantity Loss (15%): {_l3:.1f}% | {_l3c} elements")
        _line(pdf, f"L4 Relationship Loss (25%): {_l4:.1f}% | {_l4c} elements")
        _line(pdf, f"L5 Geometry Loss (10%): {_l5:.1f}% | {_l5c} elements")
        _line(pdf, f"Total Loss: {_total_loss_pct:.1f}%")
        _line(pdf, f"Model Integrity Score: {_model_score:.1f}/100")

        _section(pdf, "3) Element-Level Tracking")
        _proxy_rows = an.get("proxy_list", [])
        _line(pdf, f"Proxy tracking: showing {min(len(_proxy_rows), 50)} of {an.get('proxy_list_total', len(_proxy_rows))} entries")
        for i, p in enumerate(_proxy_rows[:50], 1):
            _line(pdf, f"{i}. {p.get('Name', 'Unnamed')} | {p.get('IFC Type', 'N/A')} | {p.get('GlobalId', 'N/A')}")

        _missing_rows = an.get("missing_pset_list", [])
        _line(pdf, "")
        _line(pdf, f"Missing Pset tracking: showing {min(len(_missing_rows), 50)} of {an.get('missing_pset_count', len(_missing_rows))} entries")
        for i, r in enumerate(_missing_rows[:50], 1):
            _line(pdf, f"{i}. {r.get('Element Name', 'Unnamed')} | {r.get('IFC Type', 'N/A')} | {r.get('GlobalId', 'N/A')} | {r.get('Issue', 'N/A')}")

        _section(pdf, "4) IFC Relationships")
        _rel_rows = an.get("relationship_summary", [])
        if not _rel_rows:
            try:
                _m = ifcopenshell.open("temp.ifc")
                _fallback_catalog = [
                    ("IfcRelContainedInSpatialStructure", "Element -> Storey assignment"),
                    ("IfcRelDefinesByProperties",         "Element -> Property Sets (Psets)"),
                    ("IfcRelAssociatesMaterial",          "Element -> Material"),
                    ("IfcRelConnectsElements",            "Element <-> Element connection"),
                    ("IfcRelFillsElement",                "Door/Window -> Wall opening"),
                    ("IfcRelAggregates",                  "Element -> Parent assembly"),
                    ("IfcRelAssociatesClassification",    "Element -> Classification system"),
                ]
                for _rel_type, _meaning in _fallback_catalog:
                    try:
                        _count = len(_m.by_type(_rel_type))
                    except Exception:
                        _count = 0
                    if _count > 0:
                        _rel_rows.append({
                            "Relationship": _rel_type,
                            "Meaning": _meaning,
                            "Count": _count,
                        })
            except Exception:
                _rel_rows = []
        if _rel_rows:
            for r in _rel_rows:
                _line(pdf, f"{r.get('Relationship', 'N/A')}: {r.get('Count', 0)} ({r.get('Meaning', 'N/A')})")
        else:
            _line(pdf, "No IFC relationships found in this model.")

        _section(pdf, "5) Additional Scores")
        _line(pdf, f"Model Quality Score: {an.get('quality_score', 'N/A')} / 100 ({an.get('quality_grade', 'N/A')})")
        pdf.output(file_path)
        return file_path

    if st.button("📄 Download PDF Report"):
        pdf_path = generate_pdf()
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        st.download_button(
            label="⬇️ Click to download PDF",
            data=pdf_bytes,
            file_name="IFC_Analysis_Report.pdf",
            mime="application/pdf",
        )
        # ── Upload PDF to Supabase ─────────────────────────────────────────────
        try:
            _pdf_fname = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            _pdf_url = upload_pdf(pdf_bytes, filename=_pdf_fname)
            if _pdf_url:
                st.session_state["cloud_pdf_url"] = _pdf_url
                st.caption(f"☁️ PDF saved to cloud — [download]({_pdf_url})")
        except Exception as _pe:
            st.caption(f"⚠️ Cloud PDF upload skipped: {_pe}")

    
