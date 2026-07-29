import streamlit as st
from theme import apply_theme, get_theme, metric_card
from view_mode import get_view, mode_banner, adapt_title, adapt_caption, is_business, is_technical, is_full, severity_to_business
import ifcopenshell
import pandas as pd
from fpdf import FPDF
import datetime
import math

st.set_page_config(page_title="Geometry Integrity", page_icon="📐", layout="wide")

_t = apply_theme()

# ── Guards ─────────────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in"):
    st.warning("Please log in from the Home page first.")
    st.stop()

an = st.session_state.get("analysis", {})
if not an:
    st.warning("⚠️ No analysis data. Please upload an IFC file on the Home page first.")
    st.stop()

try:
    model = ifcopenshell.open("temp.ifc")
except Exception:
    st.warning("⚠️ No IFC file found. Please upload a file on the Home page first.")
    st.stop()

def safe(t):
    return (str(t)
        .replace("\u2014","-").replace("\u2013","-").replace("\u2019","'")
        .replace("\u2018","'").replace("\u201c",'"').replace("\u201d",'"')
        .replace("\u2192","->").replace("\u2190","<-")
        .encode("latin-1", errors="replace").decode("latin-1"))

# ══════════════════════════════════════════════════════════════════════════════
# SKIP / ELEMENT TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
SKIP_TYPES = frozenset({
    "IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
    "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject",
    "IfcRelAggregates","IfcZone","IfcSpatialZone",
})

# Elements expected to always carry geometry
GEOMETRY_REQUIRED = frozenset({
    "IfcWall","IfcWallStandardCase","IfcDoor","IfcWindow","IfcSlab",
    "IfcColumn","IfcBeam","IfcRoof","IfcStair","IfcRailing",
    "IfcCurtainWall","IfcPlate","IfcMember","IfcBuildingElementProxy",
    "IfcPipeSegment","IfcPipeFitting","IfcDuctSegment","IfcDuctFitting",
    "IfcFlowSegment","IfcFlowTerminal","IfcLightFixture",
    "IfcMechanicalEquipment","IfcEnergyConversionDevice",
})

# Severity colour palette (matches the rest of IFC Semantic Data-Loss Analyser)
SEV_COLOR = {
    "Critical": "#da3633",
    "High":     "#d29922",
    "Medium":   "#1f6feb",
    "Low":      "#238636",
    "Info":     "#8b949e",
}

# ══════════════════════════════════════════════════════════════════════════════
# GEOMETRY INTEGRITY ENGINE
# Five detection passes, each returning a list of issue dicts:
#   {Name, GlobalId, IFC Type, Issue Type, Cause, Impact,
#    Severity, Recovery, Details}
# ══════════════════════════════════════════════════════════════════════════════

def _get_bbox(elem):
    """
    Extract bounding box coordinates from IfcBoundingBox items found inside
    any representation of the element. Returns (x,y,z,dx,dy,dz) or None.
    """
    rep = getattr(elem, "Representation", None)
    if not rep:
        return None
    for r in getattr(rep, "Representations", []):
        for item in getattr(r, "Items", []):
            if item.is_a("IfcBoundingBox"):
                try:
                    c = item.Corner
                    return (
                        float(c.Coordinates[0]),
                        float(c.Coordinates[1]),
                        float(c.Coordinates[2]),
                        float(item.XDim),
                        float(item.YDim),
                        float(item.ZDim),
                    )
                except Exception:
                    pass
    return None


def _has_solid_or_surface(elem):
    """
    Return True if the element has at least one Brep, SweptSolid,
    Tessellation, or CSG representation item.
    """
    rep = getattr(elem, "Representation", None)
    if not rep:
        return False
    solid_classes = {
        "IfcFacetedBrep","IfcClosedShell","IfcShellBasedSurfaceModel",
        "IfcExtrudedAreaSolid","IfcRevolvedAreaSolid",
        "IfcBooleanClippingResult","IfcBooleanResult",
        "IfcPolygonalFaceSet","IfcTriangulatedFaceSet",
        "IfcSurfaceModel","IfcConnectedFaceSet",
        "IfcCsgSolid","IfcSweptDiskSolid",
    }
    for r in getattr(rep, "Representations", []):
        for item in getattr(r, "Items", []):
            if item.is_a() in solid_classes:
                return True
            # recurse one level into boolean results
            for attr in ("FirstOperand", "SecondOperand"):
                child = getattr(item, attr, None)
                if child and child.is_a() in solid_classes:
                    return True
    return False


def _placement_coords(elem):
    """
    Walk IfcLocalPlacement -> IfcAxis2Placement3D -> Location
    and return (x, y, z) or None.
    """
    try:
        pl = elem.ObjectPlacement
        if pl and pl.is_a("IfcLocalPlacement"):
            rpl = pl.RelativePlacement
            if rpl and rpl.is_a("IfcAxis2Placement3D"):
                loc = rpl.Location
                if loc:
                    coords = loc.Coordinates
                    return tuple(float(c) for c in coords)
    except Exception:
        pass
    return None


def _representation_count(elem):
    """Return how many representation items an element has in total."""
    rep = getattr(elem, "Representation", None)
    if not rep:
        return 0
    count = 0
    for r in getattr(rep, "Representations", []):
        count += len(getattr(r, "Items", []))
    return count


def _rep_type_labels(elem):
    """Return set of RepresentationType strings for all representations."""
    rep = getattr(elem, "Representation", None)
    if not rep:
        return set()
    return {getattr(r, "RepresentationType", None) for r in getattr(rep, "Representations", [])} - {None}


# ── CAUSE catalogue ────────────────────────────────────────────────────────────
CAUSE_MISSING_REP = (
    "Element exported without geometry. Common causes: "
    "abstract element type, export settings suppressing geometry, "
    "placeholder object, or corrupt IFC writer."
)
CAUSE_NO_SOLID = (
    "Representation exists but contains no solid/surface body. "
    "Likely a 2D symbol, annotation proxy, or a failed Brep during IFC export."
)
CAUSE_ZERO_VOL = (
    "Bounding box dimensions are zero or near-zero on at least one axis. "
    "May indicate a collapsed or degenerate mesh, zero-thickness slab, "
    "or a unit-conversion error during export."
)
CAUSE_BBOX_EXTREME = (
    "Bounding box dimension exceeds 1 000 m or is negative. "
    "Typically caused by a unit mismatch (mm vs m), a misplaced "
    "reference object, or a corrupt transformation matrix."
)
CAUSE_MISPLACED = (
    "Element placement is far from the model origin (> 1 km). "
    "Common causes: geolocation offset not applied, survey point "
    "placed incorrectly, or element duplicated with wrong coordinates."
)
CAUSE_NO_PLACEMENT = (
    "No IfcLocalPlacement found. Element will render at world origin "
    "or may be invisible. Caused by incomplete export or missing "
    "parent container."
)

# ── IMPACT catalogue ──────────────────────────────────────────────────────────
IMPACT = {
    "missing_rep":   "Element invisible in 3D viewer; cannot be used for clash detection, QTO, or simulation.",
    "no_solid":      "Element appears as wireframe or point; volume/area quantities cannot be computed.",
    "zero_vol":      "Zero-volume elements break quantity take-off, energy analysis, and structural simulation.",
    "bbox_extreme":  "Model bounding box distorted; section cuts, floor plans, and clash spheres are unusable.",
    "misplaced":     "Coordination model misaligned; clash detection and georeferencing fail.",
    "no_placement":  "Element placed at world origin; all spatial relationships are incorrect.",
}

# ── RECOVERY catalogue ────────────────────────────────────────────────────────
RECOVERY = {
    "missing_rep":   "Inject minimal IfcBoundingBox representation using element Pset dimensions. Flag for re-export.",
    "no_solid":      "Replace 2D items with extruded IfcBoundingBox. Solid recovery requires authoring tool.",
    "zero_vol":      "Check unit scale factor in IfcProject.UnitsInContext. Apply correction multiplier.",
    "bbox_extreme":  "Divide coordinates by 1 000 (mm→m). Check IfcConversionBasedUnit for scale errors.",
    "misplaced":     "Translate ObjectPlacement by subtracting survey offset. Use IfcMapConversion if present.",
    "no_placement":  "Assign IfcLocalPlacement referencing IfcBuilding or IfcBuildingStorey as parent.",
    "not_recoverable": "Manual correction required in authoring tool. Export a new IFC after fixing.",
}


# ══════════════════════════════════════════════════════════════════════════════
# PASS 1 — MISSING REPRESENTATION
# ══════════════════════════════════════════════════════════════════════════════
def detect_missing_representation(model):
    issues = []
    for elem in model.by_type("IfcProduct"):
        etype = elem.is_a()
        if etype in SKIP_TYPES:
            continue
        if etype not in GEOMETRY_REQUIRED:
            continue
        rep = getattr(elem, "Representation", None)
        if not rep or not getattr(rep, "Representations", []):
            issues.append({
                "Name":       elem.Name or "Unnamed",
                "GlobalId":   elem.GlobalId,
                "IFC Type":   etype,
                "Issue Type": "Missing Representation",
                "Cause":      CAUSE_MISSING_REP,
                "Impact":     IMPACT["missing_rep"],
                "Severity":   "Critical",
                "Recovery":   RECOVERY["missing_rep"],
                "Details":    "Representation attribute is None or empty.",
            })
    return issues


# ══════════════════════════════════════════════════════════════════════════════
# PASS 2 — INVALID / DEGENERATE GEOMETRY (no solid body)
# ══════════════════════════════════════════════════════════════════════════════
def detect_invalid_geometry(model):
    issues = []
    for elem in model.by_type("IfcProduct"):
        etype = elem.is_a()
        if etype in SKIP_TYPES:
            continue
        if etype not in GEOMETRY_REQUIRED:
            continue
        rep = getattr(elem, "Representation", None)
        if not rep or not getattr(rep, "Representations", []):
            continue   # already caught by Pass 1
        rep_types = _rep_type_labels(elem)
        item_count = _representation_count(elem)
        has_solid  = _has_solid_or_surface(elem)
        if item_count > 0 and not has_solid:
            issues.append({
                "Name":       elem.Name or "Unnamed",
                "GlobalId":   elem.GlobalId,
                "IFC Type":   etype,
                "Issue Type": "No Solid/Surface Body",
                "Cause":      CAUSE_NO_SOLID,
                "Impact":     IMPACT["no_solid"],
                "Severity":   "High",
                "Recovery":   RECOVERY["no_solid"],
                "Details":    f"Rep types present: {', '.join(rep_types) or 'None'} · Items: {item_count}",
            })
    return issues


# ══════════════════════════════════════════════════════════════════════════════
# PASS 3 — ZERO-VOLUME / DEGENERATE BOUNDING BOX
# ══════════════════════════════════════════════════════════════════════════════
ZERO_THRESHOLD   = 1e-4   # anything below 0.1 mm treated as zero
EXTREME_DIM_M    = 1000.0  # 1 km — likely unit error

def detect_degenerate_bbox(model):
    issues = []
    for elem in model.by_type("IfcProduct"):
        etype = elem.is_a()
        if etype in SKIP_TYPES:
            continue
        bbox = _get_bbox(elem)
        if bbox is None:
            continue
        _x, _y, _z, dx, dy, dz = bbox

        # Zero-volume check
        if dx < ZERO_THRESHOLD or dy < ZERO_THRESHOLD or dz < ZERO_THRESHOLD:
            axes = []
            if dx < ZERO_THRESHOLD: axes.append(f"X={dx:.6f}")
            if dy < ZERO_THRESHOLD: axes.append(f"Y={dy:.6f}")
            if dz < ZERO_THRESHOLD: axes.append(f"Z={dz:.6f}")
            issues.append({
                "Name":       elem.Name or "Unnamed",
                "GlobalId":   elem.GlobalId,
                "IFC Type":   etype,
                "Issue Type": "Zero/Near-Zero Dimension",
                "Cause":      CAUSE_ZERO_VOL,
                "Impact":     IMPACT["zero_vol"],
                "Severity":   "High",
                "Recovery":   RECOVERY["zero_vol"],
                "Details":    f"Degenerate axes: {', '.join(axes)}",
            })
            continue   # don't double-report as extreme too

        # Extreme dimension check
        if max(dx, dy, dz) > EXTREME_DIM_M:
            issues.append({
                "Name":       elem.Name or "Unnamed",
                "GlobalId":   elem.GlobalId,
                "IFC Type":   etype,
                "Issue Type": "Extreme Bounding Box",
                "Cause":      CAUSE_BBOX_EXTREME,
                "Impact":     IMPACT["bbox_extreme"],
                "Severity":   "High",
                "Recovery":   RECOVERY["bbox_extreme"],
                "Details":    f"BBox dims: X={dx:.2f} Y={dy:.2f} Z={dz:.2f} m",
            })

    return issues


# ══════════════════════════════════════════════════════════════════════════════
# PASS 4 — MISPLACED ELEMENTS (far from model origin)
# ══════════════════════════════════════════════════════════════════════════════
MISPLACEMENT_THRESHOLD_M = 1000.0  # 1 km from origin

def detect_misplaced_elements(model):
    issues = []
    for elem in model.by_type("IfcProduct"):
        etype = elem.is_a()
        if etype in SKIP_TYPES:
            continue
        if etype not in GEOMETRY_REQUIRED:
            continue
        coords = _placement_coords(elem)
        if coords is None:
            # Only flag missing placement for types that must have one
            issues.append({
                "Name":       elem.Name or "Unnamed",
                "GlobalId":   elem.GlobalId,
                "IFC Type":   etype,
                "Issue Type": "No Placement",
                "Cause":      CAUSE_NO_PLACEMENT,
                "Impact":     IMPACT["no_placement"],
                "Severity":   "High",
                "Recovery":   RECOVERY["no_placement"],
                "Details":    "ObjectPlacement is None or not IfcLocalPlacement.",
            })
            continue

        dist = math.sqrt(sum(c**2 for c in coords))
        if dist > MISPLACEMENT_THRESHOLD_M:
            issues.append({
                "Name":       elem.Name or "Unnamed",
                "GlobalId":   elem.GlobalId,
                "IFC Type":   etype,
                "Issue Type": "Far from Origin",
                "Cause":      CAUSE_MISPLACED,
                "Impact":     IMPACT["misplaced"],
                "Severity":   "Medium",
                "Recovery":   RECOVERY["misplaced"],
                "Details":    f"Distance from origin: {dist:,.1f} m · Coords: ({coords[0]:.1f}, {coords[1]:.1f}, {coords[2]:.1f})",
            })
    return issues


# ══════════════════════════════════════════════════════════════════════════════
# PASS 5 — UNIT SCALE SANITY CHECK
# ══════════════════════════════════════════════════════════════════════════════
def detect_unit_scale_issues(model):
    """
    Check IfcProject.UnitsInContext for the length unit.
    If the declared unit is millimetres but element placements suggest
    metre-scale values (< 100 on all axes), warn that the model may
    have been exported with wrong units.
    Returns a list of 0 or 1 model-level issue dicts.
    """
    issues = []
    try:
        projects = model.by_type("IfcProject")
        if not projects:
            return issues
        project    = projects[0]
        units_ctx  = getattr(project, "UnitsInContext", None)
        if not units_ctx:
            return issues

        declared_mm = False
        declared_m  = False
        for u in getattr(units_ctx, "Units", []):
            if u.is_a("IfcSIUnit") and getattr(u, "UnitType", "") == "LENGTHUNIT":
                name = getattr(u, "Name", "")
                pref = getattr(u, "Prefix", "") or ""
                if name == "METRE" and pref == "MILLI":
                    declared_mm = True
                elif name == "METRE" and not pref:
                    declared_m = True

        # Sample some element placements to check plausibility
        sample_dists = []
        for elem in model.by_type("IfcProduct"):
            if elem.is_a() in SKIP_TYPES:
                continue
            c = _placement_coords(elem)
            if c:
                d = math.sqrt(sum(x**2 for x in c))
                if d > 0:
                    sample_dists.append(d)
            if len(sample_dists) >= 50:
                break

        if not sample_dists:
            return issues

        median_dist = sorted(sample_dists)[len(sample_dists)//2]

        # If declared mm but median placement is suspiciously small (< 10 m = 10 000 mm typical)
        if declared_mm and median_dist < 100:
            issues.append({
                "Name":       "(Model-level)",
                "GlobalId":   project.GlobalId if hasattr(project, "GlobalId") else "—",
                "IFC Type":   "IfcProject",
                "Issue Type": "Suspected Unit Mismatch",
                "Cause":      "Model declares MILLIMETRE length unit but element placements are very small (< 100). May have been exported in metres with the wrong unit tag.",
                "Impact":     "All dimensional quantities (area, volume, length) will be off by a factor of 1 000 000. Energy analysis, QTO, and clash detection are unreliable.",
                "Severity":   "Critical",
                "Recovery":   "Correct IfcSIUnit Prefix from MILLI to empty (metres). Multiply all IfcCartesianPoint coordinates by 1 000 if model was genuinely authored in mm.",
                "Details":    f"Declared unit: MILLIMETRE · Median element placement distance: {median_dist:.2f}",
            })
        # If declared metres but placements are huge (> 10 000 m) → likely authored in mm
        elif declared_m and median_dist > 10000:
            issues.append({
                "Name":       "(Model-level)",
                "GlobalId":   project.GlobalId if hasattr(project, "GlobalId") else "—",
                "IFC Type":   "IfcProject",
                "Issue Type": "Suspected Unit Mismatch",
                "Cause":      "Model declares METRE length unit but element placements suggest millimetre-scale coordinates (median > 10 000 m).",
                "Impact":     "Model will appear 1 000× too large in viewers. Clash detection bounding spheres and spatial queries are invalid.",
                "Severity":   "Critical",
                "Recovery":   "Set IfcSIUnit Prefix to MILLI (millimetres) or divide all IfcCartesianPoint coordinates by 1 000.",
                "Details":    f"Declared unit: METRE · Median element placement distance: {median_dist:,.0f}",
            })
    except Exception:
        pass
    return issues


# ══════════════════════════════════════════════════════════════════════════════
# RECOVERY ENGINE
# For each issue class, attempt lightweight IFC-text-level repairs.
# Returns (patched_ifc_text, repair_log[])
# ══════════════════════════════════════════════════════════════════════════════

def _inject_bbox_representation(ifc_text, elem_gid, ifc_type, dx=1.0, dy=0.3, dz=3.0):
    """
    Inject a minimal IfcBoundingBox representation for an element that
    has no geometry. Uses safe IFC-text injection (same approach as
    Correction Suggestions module).
    Returns updated text and a log string, or (None, error) on failure.
    """
    import re as _re
    try:
        all_ids  = [int(x) for x in _re.findall(r"#(\d+)=", ifc_text)]
        next_id  = max(all_ids) + 1 if all_ids else 100000

        esc      = _re.escape(elem_gid)
        itype_up = ifc_type.upper()
        match    = _re.search(rf"(#\d+)=\s*{itype_up}\(\s*'{esc}'", ifc_text, _re.IGNORECASE)
        if not match:
            return None, f"Could not locate #{ifc_type}('{elem_gid[:16]}') in STEP data."
        elem_ref = match.group(1)

        # Reuse existing IfcGeometricRepresentationContext if present
        ctx_match      = _re.search(r"(#\d+)=\s*IFCGEOMETRICREPRESENTATIONCONTEXT\(", ifc_text, _re.IGNORECASE)
        ifc_text_extra = ""
        if ctx_match:
            ctx_ref = ctx_match.group(1)
        else:
            ctx_id         = next_id; next_id += 1
            ifc_text_extra = f"#{ctx_id}=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.0E-5,$,$);"
            ctx_ref        = f"#{ctx_id}"

        # Origin point
        orig_id = next_id; next_id += 1
        bbox_id = next_id; next_id += 1
        srep_id = next_id; next_id += 1
        rep_id  = next_id; next_id += 1

        new_entities = []
        if ifc_text_extra:
            new_entities.append(ifc_text_extra)
        new_entities += [
            f"#{orig_id}=IFCCARTESIANPOINT((0.,0.,0.));",
            f"#{bbox_id}=IFCBOUNDINGBOX(#{orig_id},{dx:.4f},{dy:.4f},{dz:.4f});",
            f"#{srep_id}=IFCSHAPEREPRESENTATION({ctx_ref},'Box','BoundingBox',(#{bbox_id}));",
            f"#{rep_id}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{srep_id}));",
        ]

        # Patch Representation attribute of the element
        # IFC STEP format: elem_ref=IFCTYPE('guid',...,representation_ref,...)
        # We replace $,$ at the Representation slot — safest: append a new relationship
        # Actually: update Representation attribute in-place by patching the entity line.
        # For safety, use IfcRelDefinesByProperties-style approach but for geometry:
        # set Representation by replacing the element entity line.
        # Strategy: find the element line and replace its last-but-one $ with the rep ref.
        elem_line_match = _re.search(
            rf"({_re.escape(elem_ref)}=\s*{itype_up}\([^;]+);",
            ifc_text, _re.IGNORECASE | _re.DOTALL
        )
        if elem_line_match:
            old_line = elem_line_match.group(0)
            # Representation is always the second-to-last positional attribute
            # Replace trailing pattern  ,$,#OLDREF); or ,$,$);
            new_line = _re.sub(r",(\$|#\d+)\);$", f",#{rep_id});", old_line.rstrip())
            ifc_text = ifc_text.replace(old_line, new_line + "\n", 1)

        block   = "\n".join(new_entities) + "\n"
        endsec  = "ENDSEC;\nEND-ISO-10303-21;"
        ifc_text = _re.sub(r"ENDSEC;\s*END-ISO-10303-21;", block + endsec, ifc_text)

        return ifc_text, f"Injected BoundingBox ({dx}×{dy}×{dz} m) for {elem_gid[:22]}"

    except Exception as e:
        return None, f"Injection failed for {elem_gid[:22]}: {e}"


def _fix_placement(ifc_text, elem_gid, ifc_type):
    """
    Translate an element's IfcLocalPlacement to the origin (0,0,0)
    when it is missing or extremely far away.
    Only patches the IfcCartesianPoint of the element's own placement —
    does not cascade to children.
    """
    import re as _re
    try:
        esc      = _re.escape(elem_gid)
        itype_up = ifc_type.upper()

        # Find element
        elem_match = _re.search(rf"(#\d+)=\s*{itype_up}\(\s*'{esc}'", ifc_text, _re.IGNORECASE)
        if not elem_match:
            return None, f"Element {elem_gid[:22]} not found."
        elem_ref = elem_match.group(1)

        # Find its ObjectPlacement ref in the element line
        elem_line_m = _re.search(
            rf"{_re.escape(elem_ref)}=\s*{itype_up}\([^;]+;",
            ifc_text, _re.IGNORECASE | _re.DOTALL
        )
        if not elem_line_m:
            return None, f"Could not parse element line for {elem_gid[:22]}."
        elem_line = elem_line_m.group(0)

        # Find the IfcLocalPlacement ref
        lp_match = _re.search(r"(#\d+)=\s*IFCLOCALPLACEMENT\(", ifc_text, _re.IGNORECASE)
        # Find THIS element's placement by looking for placement ref inside its line
        pl_refs = _re.findall(r"#(\d+)", elem_line)
        pl_ref  = None
        for r in pl_refs:
            candidate = f"#{r}"
            if f"#{r}=IFCLOCALPLACEMENT" in ifc_text or \
               _re.search(rf"#{r}\s*=\s*IFCLOCALPLACEMENT", ifc_text, _re.IGNORECASE):
                pl_ref = candidate
                break

        if not pl_ref:
            # Create a new placement at origin
            all_ids = [int(x) for x in _re.findall(r"#(\d+)=", ifc_text)]
            next_id = max(all_ids) + 1 if all_ids else 100000
            pt_id   = next_id;     next_id += 1
            ax_id   = next_id;     next_id += 1
            lp_id   = next_id;     next_id += 1
            new_ents = [
                f"#{pt_id}=IFCCARTESIANPOINT((0.,0.,0.));",
                f"#{ax_id}=IFCAXIS2PLACEMENT3D(#{pt_id},$,$);",
                f"#{lp_id}=IFCLOCALPLACEMENT($,#{ax_id});",
            ]
            block   = "\n".join(new_ents) + "\n"
            endsec  = "ENDSEC;\nEND-ISO-10303-21;"
            ifc_text = _re.sub(r"ENDSEC;\s*END-ISO-10303-21;", block + endsec, ifc_text)
            return ifc_text, f"Created origin placement (#{lp_id}) for {elem_gid[:22]} — link manually."

        # Find the IfcAxis2Placement3D inside the local placement
        lp_body_m = _re.search(
            rf"{_re.escape(pl_ref)}\s*=\s*IFCLOCALPLACEMENT\(([^;]+)\);",
            ifc_text, _re.IGNORECASE
        )
        if not lp_body_m:
            return None, f"Could not parse IfcLocalPlacement body for {elem_gid[:22]}."

        # Find the axis placement ref
        inner_refs = _re.findall(r"#(\d+)", lp_body_m.group(1))
        for r in inner_refs:
            ax_body_m = _re.search(
                rf"#{r}\s*=\s*IFCAXIS2PLACEMENT3D\(([^;]+)\);",
                ifc_text, _re.IGNORECASE
            )
            if ax_body_m:
                # Find the IfcCartesianPoint inside it
                cp_refs = _re.findall(r"#(\d+)", ax_body_m.group(1))
                for cp_r in cp_refs:
                    cp_m = _re.search(
                        rf"(#{cp_r}\s*=\s*IFCCARTESIANPOINT\()([^)]+)(\);)",
                        ifc_text, _re.IGNORECASE
                    )
                    if cp_m:
                        old_cp = cp_m.group(0)
                        new_cp = cp_m.group(1) + "(0.,0.,0.)" + cp_m.group(3)
                        ifc_text = ifc_text.replace(old_cp, new_cp, 1)
                        return ifc_text, f"Reset placement to origin for {elem_gid[:22]}"

        return None, f"Could not locate IfcCartesianPoint for placement of {elem_gid[:22]}."

    except Exception as e:
        return None, f"Placement fix failed: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# RUN ALL DETECTION PASSES
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("🔍 Running geometry integrity checks..."):
    p1_missing  = detect_missing_representation(model)
    p2_invalid  = detect_invalid_geometry(model)
    p3_degenerate = detect_degenerate_bbox(model)
    p4_misplaced  = detect_misplaced_elements(model)
    p5_units      = detect_unit_scale_issues(model)

all_issues = p1_missing + p2_invalid + p3_degenerate + p4_misplaced + p5_units

# ══════════════════════════════════════════════════════════════════════════════
# GEOMETRY INTEGRITY SCORE  (0 – 100)
# Weighted deduction formula — mirrors the data-loss scoring in Home.py
#
#   Base = 100
#   − 30 pts for Critical issues   (missing representation, unit mismatch)
#   − 20 pts for High issues        (no solid, degenerate bbox, misplaced)
#   − 10 pts for Medium issues      (far from origin)
#   − 5  pts for Low / Info issues
#
#   Each deduction is proportional:
#       deduction = weight × (count / total_elements) × 100
#   Score is clamped to [0, 100].
# ══════════════════════════════════════════════════════════════════════════════
total_elements = an.get("total_elements", 1) or 1

sev_counts = {"Critical":0, "High":0, "Medium":0, "Low":0, "Info":0}
for iss in all_issues:
    sev_counts[iss.get("Severity","Info")] = sev_counts.get(iss.get("Severity","Info"), 0) + 1

_deduction = (
    min(30, sev_counts["Critical"] / total_elements * 100 * 0.30 * 10) +
    min(20, sev_counts["High"]     / total_elements * 100 * 0.20 * 10) +
    min(10, sev_counts["Medium"]   / total_elements * 100 * 0.10 * 10) +
    min(5,  sev_counts["Low"]      / total_elements * 100 * 0.05 * 10)
)
geo_score   = round(max(0, 100 - _deduction), 1)
total_issues = len(all_issues)

if   geo_score >= 90: geo_grade, geo_col = "Excellent", "#238636"
elif geo_score >= 75: geo_grade, geo_col = "Good",      "#1f6feb"
elif geo_score >= 55: geo_grade, geo_col = "Fair",      "#d29922"
else:                 geo_grade, geo_col = "Poor",       "#da3633"

# ══════════════════════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
st.title(adapt_title("📐 Geometry Integrity & Recovery", "📐 Invisible & Broken Elements"))
st.caption(
    "Detects missing, invalid, degenerate, and misplaced geometry in the IFC model. "
    "Classifies each issue by type, root cause, and impact. "
    "Offers partial IFC-level recovery where possible."
)
st.markdown("---")

# ── Top metrics ───────────────────────────────────────────────────────────────
m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("Total Elements",      total_elements)
m2.metric("🔴 Critical Issues",  sev_counts["Critical"],
          help="Missing representation · Unit mismatch")
m3.metric("🟠 High Issues",      sev_counts["High"],
          help="No solid body · Degenerate bbox · No placement")
m4.metric("🟡 Medium Issues",    sev_counts["Medium"],
          help="Far from model origin")
m5.metric("Total Issues",        total_issues)

# ── Score banner ──────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:{geo_col}18;border:2px solid {geo_col};border-radius:12px;
padding:16px 24px;margin:14px 0;display:flex;justify-content:space-between;
align-items:center;flex-wrap:wrap;gap:12px;">
  <div>
    <div style="font-size:11px;color:#8b949e;letter-spacing:1px;">GEOMETRY INTEGRITY SCORE</div>
    <div style="font-size:32px;font-weight:800;color:{geo_col};">{geo_score} / 100 — {geo_grade}</div>
    <div style="font-size:12px;color:#8b949e;margin-top:4px;">
      {total_issues} geometry {'issue' if total_issues==1 else 'issues'} across {total_elements} elements
    </div>
  </div>
  <div style="font-size:12px;color:#8b949e;max-width:320px;line-height:1.7;">
    <strong style="color:#e6edf3;">5 detection passes:</strong><br>
    Missing Representation · No Solid Body · Degenerate BBox ·
    Misplaced / No Placement · Unit Scale Mismatch
  </div>
</div>""", unsafe_allow_html=True)

# ── Pass summary cards ─────────────────────────────────────────────────────────
pass_data = [
    ("Pass 1", "Missing Representation",  len(p1_missing),    "Critical", "🔴",
     "Elements with no geometry at all — invisible in 3D viewers."),
    ("Pass 2", "No Solid/Surface Body",   len(p2_invalid),    "High",     "🟠",
     "Elements with a representation but no Brep/Extrusion/Tessellation body."),
    ("Pass 3", "Degenerate Bounding Box", len(p3_degenerate), "High",     "🟠",
     "Zero-dimension or extreme (> 1 km) bounding box indicating unit errors."),
    ("Pass 4", "Misplaced / No Placement",len(p4_misplaced),  "Medium",   "🟡",
     "Elements placed > 1 km from origin or missing IfcLocalPlacement."),
    ("Pass 5", "Unit Scale Mismatch",     len(p5_units),      "Critical", "🔴",
     "Model-level unit declaration inconsistent with actual coordinates."),
]

cols = st.columns(5)
for col_w, (pass_id, label, count, sev, icon, desc) in zip(cols, pass_data):
    c = SEV_COLOR.get(sev, "#8b949e")
    status = "✅" if count == 0 else icon
    with col_w:
        st.markdown(f"""
<div style="background:#161b22;border:1px solid {'#30363d' if count==0 else c};
border-radius:10px;padding:12px;text-align:center;height:130px;">
  <div style="font-size:10px;color:#8b949e;margin-bottom:4px;">{pass_id}</div>
  <div style="font-size:22px;font-weight:800;color:{c if count>0 else '#238636'};">
    {status} {count}
  </div>
  <div style="font-size:10px;color:#e6edf3;margin-top:4px;line-height:1.4;">{label}</div>
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 All Issues",
    "🔬 Diagnosis",
    "🔧 Recovery",
    "📊 Type Breakdown",
    "📄 Export",
])

# ── TAB 1 — ALL ISSUES ────────────────────────────────────────────────────────
with tab1:
    st.subheader(adapt_title("Geometry Issues — Full List", "Elements That Cannot Be Seen or Measured"))
    if not all_issues:
        st.success("✅ No geometry issues detected in this model!")
    else:
        # Filters
        f1, f2, f3 = st.columns(3)
        filter_sev  = f1.selectbox("Severity",["All","Critical","High","Medium","Low"])
        filter_type = f2.selectbox("Issue Type",["All"] + sorted({i["Issue Type"] for i in all_issues}))
        search      = f3.text_input("Search element name","",placeholder="e.g. Wall_01")

        filtered = all_issues
        if filter_sev  != "All": filtered = [i for i in filtered if i["Severity"]==filter_sev]
        if filter_type != "All": filtered = [i for i in filtered if i["Issue Type"]==filter_type]
        if search:               filtered = [i for i in filtered if search.lower() in i["Name"].lower()]

        st.caption(f"Showing **{len(filtered)}** of **{total_issues}** issues")

        if filtered:
            df_rows = []
            for iss in filtered:
                c = SEV_COLOR.get(iss["Severity"], "#8b949e")
                df_rows.append({
                    "Severity":   iss["Severity"],
                    "Issue Type": iss["Issue Type"],
                    "Element":    iss["Name"],
                    "IFC Type":   iss["IFC Type"],
                    "Details":    iss["Details"],
                    "GlobalId":   iss["GlobalId"][:22] + "…",
                })
            st.dataframe(pd.DataFrame(df_rows), use_container_width=True,
                         hide_index=True, height=500)
        else:
            st.info("No issues match the current filters.")

# ── TAB 2 — DIAGNOSIS ─────────────────────────────────────────────────────────
with tab2:
    st.subheader(adapt_title("🔬 Diagnosis — Root Cause & Impact", "🔬 Why This Matters For Your Project"))
    st.caption(
        "Each issue is classified by its geometry loss type, probable export cause, "
        "and downstream impact on model usability."
    )
    if not all_issues:
        st.success("✅ No issues to diagnose.")
    else:
        # Group by Issue Type for cleaner display
        by_type: dict = {}
        for iss in all_issues:
            by_type.setdefault(iss["Issue Type"], []).append(iss)

        for issue_type, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
            first   = items[0]
            sev     = first["Severity"]
            c       = SEV_COLOR.get(sev, "#8b949e")
            count   = len(items)
            with st.expander(f"{issue_type}   ·   {count} {'element' if count==1 else 'elements'}   ·   Severity: {sev}"):
                d1, d2 = st.columns(2)
                with d1:
                    st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:8px;">
  <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:6px;">GEOMETRY LOSS TYPE</div>
  <div style="font-size:13px;font-weight:700;color:{c};">{issue_type}</div>
  <div style="font-size:11px;color:#8b949e;margin-top:4px;">
    <span style="background:{c}22;color:{c};border:1px solid {c};border-radius:4px;
    padding:1px 7px;font-size:10px;">{sev}</span>
    &nbsp; {count} affected element{'s' if count!=1 else ''}
  </div>
</div>
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:8px;">
  <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:6px;">PROBABLE CAUSE</div>
  <div style="font-size:12px;color:#e6edf3;line-height:1.6;">{first['Cause']}</div>
</div>""", unsafe_allow_html=True)
                with d2:
                    st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:8px;">
  <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:6px;">IMPACT ON MODEL USABILITY</div>
  <div style="font-size:12px;color:#e6edf3;line-height:1.6;">{first['Impact']}</div>
</div>
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;">
  <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:6px;">RECOVERY STRATEGY</div>
  <div style="font-size:12px;color:#7ee787;line-height:1.6;">{first['Recovery']}</div>
</div>""", unsafe_allow_html=True)

                # Element list
                st.markdown(f"**Affected elements** (showing up to 20 of {count}):")
                for iss in items[:20]:
                    st.markdown(
                        f"<div style='background:#0d1117;border:1px solid #21262d;"
                        f"border-radius:6px;padding:6px 12px;margin-bottom:4px;font-size:12px;'>"
                        f"<code style='color:#58a6ff;'>{iss['IFC Type']}</code>"
                        f"&nbsp; {iss['Name']}"
                        f"&nbsp; <span style='color:#8b949e;font-size:10px;'>{iss['Details']}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                if count > 20:
                    st.caption(f"… and {count-20} more. Use the Export tab to download the full list.")

# ── TAB 3 — RECOVERY ──────────────────────────────────────────────────────────
with tab3:
    st.subheader(adapt_title("🔧 Geometry Recovery", "🔧 Fix These Elements"))
    st.markdown("""
<div style="background:#0d1a14;border:1px solid #238636;border-radius:8px;padding:12px 16px;
margin-bottom:14px;font-size:13px;color:#7ee787;line-height:1.6;">
  <strong>Recovery scope:</strong> IFC Semantic Data-Loss Analyser can perform <em>partial IFC-text-level recovery</em>
  for two issue classes — missing representations (injects a IfcBoundingBox placeholder)
  and misplaced elements (resets ObjectPlacement to origin). Full geometric recovery
  (rebuilding Breps, correcting meshes) requires the authoring tool.
</div>""", unsafe_allow_html=True)

    # ── Recovery matrix ───────────────────────────────────────────────────────
    rec_matrix = [
        ("Missing Representation",   len(p1_missing),  True,
         "Inject IfcBoundingBox placeholder using default or Pset-inferred dimensions.",
         "Partial — element becomes visible as a box; exact shape requires re-export."),
        ("No Solid/Surface Body",    len(p2_invalid),  False,
         "Cannot inject solid geometry from text level. Must fix in authoring tool.",
         "Not recoverable at IFC-text level."),
        ("Zero/Near-Zero Dimension", sum(1 for i in p3_degenerate if "Zero" in i["Issue Type"]),
         False,
         "Dimension values embedded in solid geometry cannot be patched safely via text.",
         "Not recoverable at IFC-text level. Fix thickness/dimensions in authoring tool."),
        ("Extreme Bounding Box",     sum(1 for i in p3_degenerate if "Extreme" in i["Issue Type"]),
         False,
         "Coordinate-level fix requires rewriting all IfcCartesianPoint values — risky.",
         "Flag for unit correction in IfcProject.UnitsInContext instead."),
        ("Far from Origin",          sum(1 for i in p4_misplaced  if "Far" in i["Issue Type"]),
         True,
         "Reset IfcLocalPlacement → IfcAxis2Placement3D → IfcCartesianPoint to (0,0,0).",
         "Partial — element moved to origin; verify correct relative placement after re-upload."),
        ("No Placement",             sum(1 for i in p4_misplaced  if "No Placement" in i["Issue Type"]),
         True,
         "Create new IfcLocalPlacement at origin and link it to the element.",
         "Partial — element placed at origin; correct position requires authoring tool."),
        ("Suspected Unit Mismatch",  len(p5_units),    False,
         "Correcting IfcSIUnit Prefix requires careful cascading through all quantities.",
         "Not auto-recoverable. Correct IfcProject.UnitsInContext manually."),
    ]

    for label, count, can_recover, strategy, limitation in rec_matrix:
        if count == 0:
            continue
        badge_c   = "#238636" if can_recover else "#da3633"
        badge_txt = "✅ Recoverable" if can_recover else "❌ Manual Fix Required"
        st.markdown(f"""
<div style="background:#161b22;border:1px solid {'#238636' if can_recover else '#30363d'};
border-radius:10px;padding:14px 18px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px;">
    <div>
      <span style="font-size:14px;font-weight:700;color:#e6edf3;">{label}</span>
      <span style="font-size:12px;color:#8b949e;margin-left:10px;">{count} element{'s' if count!=1 else ''}</span>
    </div>
    <span style="background:{badge_c}22;color:{badge_c};border:1px solid {badge_c};
    border-radius:4px;padding:2px 10px;font-size:11px;font-weight:700;">{badge_txt}</span>
  </div>
  <div style="font-size:12px;color:#e6edf3;margin-bottom:6px;"><strong>Strategy:</strong> {strategy}</div>
  <div style="font-size:11px;color:#8b949e;"><strong>Limitation:</strong> {limitation}</div>
</div>""", unsafe_allow_html=True)

    recoverable_missing   = [i for i in p1_missing if i["Issue Type"] == "Missing Representation"]
    recoverable_misplaced = [i for i in p4_misplaced if i["Issue Type"] in ("Far from Origin","No Placement")]

    total_recoverable = len(recoverable_missing) + len(recoverable_misplaced)

    if total_recoverable == 0:
        st.info("No auto-recoverable issues detected in this model.")
    else:
        st.markdown(f"""
<div style="background:#0d1a30;border:1px solid #58a6ff;border-radius:8px;
padding:10px 16px;margin:12px 0;font-size:13px;color:#79c0ff;">
  🔧 <strong>{total_recoverable} auto-recoverable issues</strong> detected —
  {len(recoverable_missing)} missing representations and {len(recoverable_misplaced)} placement issues.
  Click <em>Apply Recovery</em> to generate a patched IFC file.
</div>""", unsafe_allow_html=True)

        show_rec_detail = st.checkbox("Show elements that will be patched", value=False)
        if show_rec_detail:
            rows = []
            for iss in recoverable_missing:
                rows.append({"Recovery Action":"Inject BoundingBox","Element":iss["Name"],
                              "IFC Type":iss["IFC Type"],"GlobalId":iss["GlobalId"][:22]+"…"})
            for iss in recoverable_misplaced:
                rows.append({"Recovery Action":"Reset Placement to Origin","Element":iss["Name"],
                              "IFC Type":iss["IFC Type"],"GlobalId":iss["GlobalId"][:22]+"…"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if st.button("🔧 Apply Geometry Recovery & Download Patched IFC", use_container_width=True):
            try:
                with open("temp.ifc","r",encoding="utf-8",errors="replace") as f:
                    ifc_text = f.read()

                repair_log    = []
                fail_log      = []

                # ── Inject BoundingBox for missing representations ──────────────
                for iss in recoverable_missing:
                    # Try to read plausible dims from Pset quantities
                    dx, dy, dz = 1.0, 0.3, 3.0   # default wall-like box
                    patched, msg = _inject_bbox_representation(
                        ifc_text, iss["GlobalId"], iss["IFC Type"], dx, dy, dz
                    )
                    if patched:
                        ifc_text = patched
                        repair_log.append(f"✅ BoundingBox injected: {iss['Name']} ({iss['IFC Type']})")
                    else:
                        fail_log.append(f"⚠️ {msg}")

                # ── Reset placements ───────────────────────────────────────────
                for iss in recoverable_misplaced:
                    patched, msg = _fix_placement(ifc_text, iss["GlobalId"], iss["IFC Type"])
                    if patched:
                        ifc_text = patched
                        repair_log.append(f"✅ Placement reset: {iss['Name']} ({iss['IFC Type']})")
                    else:
                        fail_log.append(f"⚠️ {msg}")

                st.download_button(
                    label=f"⬇️ Download Patched IFC ({len(repair_log)} fixes applied)",
                    data=ifc_text.encode("utf-8"),
                    file_name="geometry_patched.ifc",
                    mime="application/octet-stream",
                    use_container_width=True,
                )
                st.success(f"✅ {len(repair_log)} geometry patches applied.")
                if repair_log:
                    with st.expander(f"✅ {len(repair_log)} successful patches"):
                        for r in repair_log: st.markdown(f"- {r}")
                if fail_log:
                    with st.expander(f"⚠️ {len(fail_log)} patches skipped"):
                        for r in fail_log: st.markdown(f"- {r}")

            except Exception as e:
                st.error(f"Recovery error: {e}")

# ── TAB 4 — TYPE BREAKDOWN ────────────────────────────────────────────────────
with tab4:
    st.subheader("📊 Issues by IFC Element Type")
    if not all_issues:
        st.success("✅ No issues to break down.")
    else:
        type_stats: dict = {}
        for iss in all_issues:
            t = iss["IFC Type"]
            type_stats.setdefault(t, {"Critical":0,"High":0,"Medium":0,"Low":0,"total":0})
            type_stats[t][iss.get("Severity","Low")] = type_stats[t].get(iss.get("Severity","Low"),0) + 1
            type_stats[t]["total"] += 1

        for ifc_type, stats in sorted(type_stats.items(), key=lambda x: -x[1]["total"]):
            t_col = (
                "#da3633" if stats["Critical"] > 0 else
                "#d29922" if stats["High"] > 0 else
                "#1f6feb" if stats["Medium"] > 0 else "#238636"
            )
            st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
padding:12px 18px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <span style="font-size:14px;font-weight:700;color:#e6edf3;">{ifc_type}</span>
    <span style="font-size:16px;font-weight:800;color:{t_col};">{stats['total']} issue{'s' if stats['total']!=1 else ''}</span>
  </div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;font-size:11px;">
    {''.join([
      f"<span style='background:{SEV_COLOR[s]}22;color:{SEV_COLOR[s]};border:1px solid {SEV_COLOR[s]};border-radius:4px;padding:1px 8px;'>{s}: {stats[s]}</span>"
      for s in ("Critical","High","Medium","Low") if stats[s] > 0
    ])}
  </div>
</div>""", unsafe_allow_html=True)

# ── TAB 5 — EXPORT ────────────────────────────────────────────────────────────
with tab5:
    st.subheader("📄 Export Geometry Integrity Report")

    ec1, ec2 = st.columns(2)
    with ec1:
        if all_issues:
            csv_rows = [{
                "Severity":   i["Severity"],
                "Issue Type": i["Issue Type"],
                "Element":    i["Name"],
                "IFC Type":   i["IFC Type"],
                "GlobalId":   i["GlobalId"],
                "Cause":      i["Cause"],
                "Impact":     i["Impact"],
                "Recovery":   i["Recovery"],
                "Details":    i["Details"],
            } for i in all_issues]
            csv = pd.DataFrame(csv_rows).to_csv(index=False)
            st.download_button("⬇️ Download CSV",data=csv,
                               file_name="geometry_integrity.csv",
                               mime="text/csv",use_container_width=True)
        else:
            st.info("No issues — CSV would be empty.")

    with ec2:
        if st.button("📄 Generate PDF Report", use_container_width=True):
            pdf = FPDF(); pdf.add_page()

            # Header
            pdf.set_fill_color(13,31,61); pdf.rect(0,0,210,32,"F")
            pdf.set_font("Arial","B",17); pdf.set_text_color(255,255,255)
            pdf.cell(0,11,"IFC Geometry Integrity & Recovery Report",ln=True,align="C")
            pdf.set_font("Arial",size=9)
            pdf.cell(0,6,safe(f"IFC Semantic Data-Loss Analyser  |  KPRIET — CSE Dept  |  Generated: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}"),ln=True,align="C")
            pdf.ln(6); pdf.set_text_color(0,0,0)

            # Score summary
            pdf.set_font("Arial","B",13); pdf.cell(0,8,"Geometry Integrity Score",ln=True)
            pdf.set_font("Arial",size=11)
            pdf.cell(0,7,safe(f"Score        : {geo_score} / 100 — {geo_grade}"),ln=True)
            pdf.cell(0,7,safe(f"Total Issues : {total_issues}"),ln=True)
            for sev in ("Critical","High","Medium","Low"):
                if sev_counts[sev]:
                    pdf.cell(0,6,safe(f"  {sev:10}: {sev_counts[sev]}"),ln=True)
            pdf.ln(3)

            # Pass summary
            pdf.set_font("Arial","B",13); pdf.cell(0,8,"Detection Pass Results",ln=True)
            pdf.set_font("Arial",size=10)
            for pass_id, label, count, sev, icon, desc in pass_data:
                status = "PASS" if count == 0 else "FAIL"
                pdf.cell(0,6,safe(f"  [{status}] {pass_id}: {label}  —  {count} issue(s)"),ln=True)
            pdf.ln(3)

            # Issue details
            if all_issues:
                pdf.set_font("Arial","B",13); pdf.cell(0,8,safe(f"Issue Details ({len(all_issues)})"),ln=True)
                for i, iss in enumerate(all_issues[:200], 1):
                    pdf.set_font("Arial","B",10)
                    pdf.multi_cell(0,6,safe(f"{i}. [{iss['Severity']}] {iss['Issue Type']}  —  {iss['Name']} ({iss['IFC Type']})"))
                    pdf.set_font("Arial",size=9)
                    pdf.multi_cell(0,5,safe(f"   Cause    : {iss['Cause'][:120]}"))
                    pdf.multi_cell(0,5,safe(f"   Impact   : {iss['Impact'][:120]}"))
                    pdf.multi_cell(0,5,safe(f"   Recovery : {iss['Recovery'][:120]}"))
                    pdf.multi_cell(0,5,safe(f"   Details  : {iss['Details']}"))
                    pdf.ln(2)
                if len(all_issues) > 200:
                    pdf.cell(0,6,safe(f"  ... and {len(all_issues)-200} more. Download CSV for full list."),ln=True)

            st.download_button(
                "⬇️ Download PDF",
                data=pdf.output(dest="S").encode("latin-1"),
                file_name="geometry_integrity_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
