import os
import gc
import uuid
import pandas as pd
import ifcopenshell

# Constants
VALID_PROXY_KEYWORDS = {
    "rpc", "entourage", "geo", "georeference", "geo-reference",
    "survey", "origin", "basepoint", "site origin",
    "car", "vehicle", "truck", "bus",
    "people", "person", "human", "pedestrian",
}

INVALID_PROXY_KEYWORDS = {
    "wall", "door", "window", "slab", "floor", "roof",
    "column", "beam", "stair", "railing",
    "pipe", "duct", "cable", "wire",
    "pump", "fan", "boiler", "chiller",
    "light", "fixture",
    "wash", "toilet", "sink", "bath",
    "panel", "board", "frame",
}

ELEM_PSET_MAP = {
    "IfcWall": "Pset_WallCommon",
    "IfcWallStandardCase": "Pset_WallCommon",
    "IfcDoor": "Pset_DoorCommon",
    "IfcWindow": "Pset_WindowCommon",
    "IfcSlab": "Pset_SlabCommon",
    "IfcColumn": "Pset_ColumnCommon",
    "IfcBeam": "Pset_BeamCommon",
    "IfcRoof": "Pset_RoofCommon",
    "IfcStair": "Pset_StairCommon",
    "IfcRailing": "Pset_RailingCommon",
    "IfcPipeSegment": "Pset_PipeSegmentTypeCommon",
    "IfcPipeFitting": "Pset_PipeFittingTypeCommon",
    "IfcFlowSegment": "Pset_FlowSegmentTypeCommon",
    "IfcFlowTerminal": "Pset_FlowTerminalTypeCommon",
    "IfcMechanicalEquipment": "Pset_ManufacturerTypeInformation",
    "IfcEnergyConversionDevice": "Pset_EnergyConversionDeviceCommon",
    "IfcElectricalElement": "Pset_ElectricalDeviceCommon",
    "IfcLightFixture": "Pset_LightFixtureTypeCommon",
    "IfcDistributionElement": "Pset_DistributionSystemCommon",
    "IfcPlant": "Pset_PlantCommon",
}

SKIP_TYPES = frozenset({
    "IfcSpace", "IfcOpeningElement", "IfcVirtualElement", "IfcAnnotation",
    "IfcGrid", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcProject",
    "IfcRelAggregates", "IfcZone", "IfcSpatialZone", "IfcRelContainedInSpatialStructure",
})

GEOMETRY_REQUIRED = frozenset({
    "IfcWall", "IfcWallStandardCase", "IfcDoor", "IfcWindow", "IfcSlab",
    "IfcColumn", "IfcBeam", "IfcRoof", "IfcStair", "IfcRailing",
    "IfcCurtainWall", "IfcPlate", "IfcMember", "IfcBuildingElementProxy",
    "IfcPipeSegment", "IfcPipeFitting", "IfcDuctSegment", "IfcDuctFitting",
    "IfcFlowSegment", "IfcFlowTerminal", "IfcLightFixture",
    "IfcMechanicalEquipment", "IfcEnergyConversionDevice",
})

def classify_proxy(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in VALID_PROXY_KEYWORDS):
        return "valid"
    if any(k in n for k in INVALID_PROXY_KEYWORDS):
        return "invalid"
    return "unknown"

def detect_export_source(model):
    try:
        header = model.header
        desc = str(getattr(header, "file_description", "")).lower()
        name = str(getattr(header, "file_name", "")).lower()
        schema = str(getattr(header, "file_schema", "")).upper()
        combined = desc + " " + name

        if any(k in combined for k in ["revit", "autodesk"]):
            tool = "Autodesk Revit"
            risks = [
                ("⚠️ RPC trees/furniture export as IfcBuildingElementProxy", "High"),
                ("⚠️ FireRating property often missing in Pset_WallCommon", "High"),
                ("⚠️ Material classification may be lost during export", "Medium"),
                ("⚠️ Some custom Psets may not transfer correctly", "Medium"),
                ("⚠️ IfcWallStandardCase may appear instead of IfcWall", "Low"),
            ]
        elif any(k in combined for k in ["archicad", "graphisoft"]):
            tool = "Graphisoft ArchiCAD"
            risks = [
                ("⚠️ Morph elements may export as generic proxies", "High"),
                ("⚠️ Complex roof shapes may lose semantic type", "High"),
                ("⚠️ Object-level Psets may be partially mapped", "Medium"),
                ("⚠️ Stair components may lose sub-element classification", "Low"),
            ]
        elif any(k in combined for k in ["tekla", "trimble"]):
            tool = "Tekla Structures"
            risks = [
                ("⚠️ Custom component assemblies may become proxy objects", "High"),
                ("⚠️ Rebar and reinforcement data may not transfer", "High"),
                ("⚠️ Steel connection details may lose classification", "Medium"),
            ]
        elif any(k in combined for k in ["navisworks", "navis"]):
            tool = "Autodesk Navisworks"
            risks = [
                ("⚠️ Navisworks re-export often strips all Pset data", "Critical"),
                ("⚠️ Nearly all elements may become IfcBuildingElementProxy", "Critical"),
                ("⚠️ GlobalIds may be regenerated — losing element tracking", "High"),
            ]
        elif any(k in combined for k in ["vectorworks"]):
            tool = "Vectorworks"
            risks = [
                ("⚠️ Space objects may not export correctly", "Medium"),
                ("⚠️ Some parametric objects may lose type information", "Medium"),
            ]
        elif any(k in combined for k in ["sketchup", "sketch up"]):
            tool = "SketchUp"
            risks = [
                ("⚠️ Most elements export as generic proxies", "Critical"),
                ("⚠️ No Pset data exported by default", "Critical"),
                ("⚠️ No floor/storey assignment preserved", "High"),
            ]
        elif any(k in combined for k in ["allplan"]):
            tool = "Nemetschek Allplan"
            risks = [
                ("⚠️ Reinforcement elements may lose classification", "Medium"),
                ("⚠️ Some Psets may use non-standard names", "Low"),
            ]
        else:
            tool = "Unknown / Generic IFC Exporter"
            risks = [
                ("ℹ️ Export source not detected from header metadata", "Info"),
                ("ℹ️ Run full validation to identify actual issues", "Info"),
            ]

        ifc_version = "Unknown"
        if "IFC4" in schema:
            ifc_version = "IFC4"
        elif "IFC2X3" in schema:
            ifc_version = "IFC2X3 (Legacy)"
        elif "IFC2" in schema:
            ifc_version = "IFC2.x (Old)"

        return {"tool": tool, "version": ifc_version, "risks": risks}
    except Exception:
        return {
            "tool": "Unknown",
            "version": "Unknown",
            "risks": [("ℹ️ Could not read IFC header metadata", "Info")],
        }

def get_pset_value(elem, pset_name, prop_name):
    try:
        for d in getattr(elem, "IsDefinedBy", []):
            if d.is_a("IfcRelDefinesByProperties"):
                ps = d.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet") and ps.Name == pset_name:
                    for prop in ps.HasProperties:
                        if prop.Name == prop_name:
                            val = getattr(prop, "NominalValue", None)
                            if val:
                                return val.wrappedValue
    except Exception:
        pass
    return None

def has_pset(elem, pset_name):
    try:
        for d in getattr(elem, "IsDefinedBy", []):
            if d.is_a("IfcRelDefinesByProperties"):
                ps = d.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet") and ps.Name == pset_name:
                    return True
    except Exception:
        pass
    return False

def check_step_syntax(model, model_path):
    checks = []
    # Check 1: File Parseable
    if model is not None:
        checks.append({
            "check": "File Parseable",
            "status": "pass",
            "detail": "Opened successfully without parsing errors.",
        })
    else:
        checks.append({
            "check": "File Parseable",
            "status": "fail",
            "detail": "Failed to parse the file structure.",
        })
        return checks

    # Check 2: Schema declared
    try:
        schema = model.schema
        if schema:
            checks.append({"check": "Schema Version Declared", "status": "pass", "detail": f"Schema: {schema}"})
        else:
            checks.append({"check": "Schema Version Declared", "status": "warn", "detail": "Schema string header is empty."})
    except Exception:
        checks.append({"check": "Schema Version Declared", "status": "warn", "detail": "Could not read schema header."})

    # Check 3: IfcProject present
    try:
        projects = model.by_type("IfcProject")
        if projects:
            p_name = getattr(projects[0], "Name", None) or "Unnamed"
            checks.append({"check": "IfcProject Entity Present", "status": "pass", "detail": f"Found IfcProject: '{p_name}'"})
        else:
            checks.append({"check": "IfcProject Entity Present", "status": "fail", "detail": "No IfcProject entity found."})
    except Exception as e:
        checks.append({"check": "IfcProject Entity Present", "status": "fail", "detail": f"Error: {e}"})

    # Check 4: OwnerHistory present
    try:
        oh = model.by_type("IfcOwnerHistory")
        if oh:
            checks.append({"check": "OwnerHistory Present", "status": "pass", "detail": f"{len(oh)} records found."})
        else:
            checks.append({"check": "OwnerHistory Present", "status": "warn", "detail": "No IfcOwnerHistory found."})
    except Exception:
        checks.append({"check": "OwnerHistory Present", "status": "warn", "detail": "Error checking IfcOwnerHistory."})

    # Check 5: Duplicate GlobalIds
    try:
        all_gids = [e.GlobalId for e in model.by_type("IfcRoot") if hasattr(e, "GlobalId")]
        dup_count = len(all_gids) - len(set(all_gids))
        if dup_count == 0:
            checks.append({"check": "GlobalId Uniqueness", "status": "pass", "detail": f"All {len(all_gids)} GlobalIds are unique."})
        else:
            checks.append({"check": "GlobalId Uniqueness", "status": "fail", "detail": f"{dup_count} duplicates detected."})
    except Exception as e:
        checks.append({"check": "GlobalId Uniqueness", "status": "warn", "detail": f"Error: {e}"})

    # Check 6: Unit assignment
    try:
        units = model.by_type("IfcUnitAssignment")
        if units:
            checks.append({"check": "Unit Assignment", "status": "pass", "detail": f"Found {len(getattr(units[0], 'Units', []))} definitions."})
        else:
            checks.append({"check": "Unit Assignment", "status": "warn", "detail": "No UnitAssignment found."})
    except Exception:
        checks.append({"check": "Unit Assignment", "status": "warn", "detail": "Error checking UnitAssignment."})

    # Check 7: Geometry context
    try:
        ctx = model.by_type("IfcGeometricRepresentationContext")
        if ctx:
            checks.append({"check": "Geometry Context", "status": "pass", "detail": f"{len(ctx)} contexts defined."})
        else:
            checks.append({"check": "Geometry Context", "status": "fail", "detail": "No GeometricRepresentationContext."})
    except Exception:
        checks.append({"check": "Geometry Context", "status": "warn", "detail": "Error checking GeometryContext."})

    return checks

def parse_ifc_file(file_path: str) -> dict:
    gc.collect()
    model = ifcopenshell.open(file_path)

    # 1. Export Source Analysis
    exp_source = detect_export_source(model)

    # 2. STEP Syntax checks
    step_checks = check_step_syntax(model, file_path)
    pass_cnt = sum(1 for c in step_checks if c["status"] == "pass")
    warn_cnt = sum(1 for c in step_checks if c["status"] == "warn")
    fail_cnt = sum(1 for c in step_checks if c["status"] == "fail")
    step_verdict = {
        "pass": pass_cnt,
        "warn": warn_cnt,
        "fail": fail_cnt,
        "total": len(step_checks),
        "checks": step_checks
    }

    # 3. Elements scan
    walls = []
    standard_walls = []
    doors = []
    windows = []
    proxies = []
    all_elements = []

    all_products = model.by_type("IfcProduct")
    for elem in all_products:
        t = elem.is_a()
        if t in SKIP_TYPES:
            continue
        all_elements.append(elem)
        if t == "IfcWall":
            walls.append(elem)
        elif t == "IfcWallStandardCase":
            standard_walls.append(elem)
        elif t == "IfcDoor":
            doors.append(elem)
        elif t == "IfcWindow":
            windows.append(elem)
        elif t == "IfcBuildingElementProxy":
            proxies.append(elem)

    total_elements = len(all_elements)
    total_walls = len(walls) + len(standard_walls)
    proxy_elements = len(proxies)
    semantic_elements = total_elements - proxy_elements

    walls_pct = (total_walls / total_elements * 100) if total_elements else 0
    doors_pct = (len(doors) / total_elements * 100) if total_elements else 0
    windows_pct = (len(windows) / total_elements * 100) if total_elements else 0
    proxy_pct = (proxy_elements / total_elements * 100) if total_elements else 0
    other_semantic = max(semantic_elements - total_walls - len(doors) - len(windows), 0)
    other_pct = (other_semantic / total_elements * 100) if total_elements else 0
    semantic_pct = 100 - proxy_pct if total_elements else 0

    if proxy_pct <= 10:
        severity = "LOW"
    elif proxy_pct < 20:
        severity = "MEDIUM"
    elif proxy_pct < 50:
        severity = "HIGH"
    else:
        severity = "CRITICAL"

    # 4. Property Sets (Psets) check
    walls_missing_pset_set = set()
    missing_pset_all = []
    _walls_with_pset = 0

    for _w in walls + standard_walls:
        _has = False
        for _d in getattr(_w, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcPropertySet") and _ps.Name == "Pset_WallCommon":
                    _has = True
                    break
        if _has:
            _walls_with_pset += 1
        else:
            walls_missing_pset_set.add(_w.GlobalId)

    _elems_with_pset = 0
    for _elem in all_elements:
        _etype = _elem.is_a()
        _req_pset = ELEM_PSET_MAP.get(_etype)
        _has_req = False
        for _d in getattr(_elem, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcPropertySet"):
                    if _req_pset and _ps.Name == _req_pset:
                        _has_req = True
                        break
        if _req_pset:
            if _has_req:
                _elems_with_pset += 1
            else:
                missing_pset_all.append({
                    "Element Name": _elem.Name or "Unnamed",
                    "GlobalId": _elem.GlobalId,
                    "IFC Type": _etype,
                    "Required Pset": _req_pset,
                    "Issue": f"Missing {_req_pset}",
                })
        else:
            _elems_with_pset += 1

    _elems_requiring_pset = _elems_with_pset + len(missing_pset_all)
    _pset_score = (_elems_with_pset / _elems_requiring_pset * 40) if _elems_requiring_pset else 40
    _pset_pct = round(_elems_with_pset / _elems_requiring_pset * 100, 1) if _elems_requiring_pset else 100

    # 5. Data Loss metrics
    # Level 1 — Type Loss (proxy)
    _type_loss_count = proxy_elements
    _type_loss_pct = round(proxy_pct, 1)

    # Level 2 — Property Loss (missing required psets)
    _prop_loss_count = len(missing_pset_all)
    _prop_loss_pct = round(_prop_loss_count / _elems_requiring_pset * 100, 1) if _elems_requiring_pset else 0

    # Level 3 — Relationship Loss
    _rel_loss = []
    for _elem in all_elements:
        _etype = _elem.is_a()
        if _etype in ("IfcBuildingElementProxy",):
            continue
        _in_storey = any(
            r.is_a("IfcRelContainedInSpatialStructure") and
            getattr(r, "RelatingStructure", None) and
            r.RelatingStructure.is_a("IfcBuildingStorey")
            for r in getattr(_elem, "ContainedInStructure", [])
        )
        if not _in_storey:
            _rel_loss.append({
                "Name": _elem.Name or "Unnamed",
                "GlobalId": _elem.GlobalId,
                "IFC Type": _etype,
                "Issue": "Not assigned to any storey"
            })
        if _etype in ("IfcDoor", "IfcWindow"):
            _hosted = any(r.is_a("IfcRelFillsElement") for r in getattr(_elem, "FillsVoids", []))
            if not _hosted:
                _rel_loss.append({
                    "Name": _elem.Name or "Unnamed",
                    "GlobalId": _elem.GlobalId,
                    "IFC Type": _etype,
                    "Issue": "Not hosted in any wall opening"
                })
    _rel_loss_count = len(_rel_loss)
    _rel_loss_pct = round(_rel_loss_count / max(total_elements, 1) * 100, 1)

    # Level 4 — Geometry Loss
    _geo_loss = []
    for _elem in all_elements:
        if not getattr(_elem, "Representation", None):
            _geo_loss.append({
                "Name": _elem.Name or "Unnamed",
                "GlobalId": _elem.GlobalId,
                "IFC Type": _elem.is_a(),
                "Issue": "No geometry representation"
            })
    _geo_loss_count = len(_geo_loss)
    _geo_loss_pct = round(_geo_loss_count / max(total_elements, 1) * 100, 1)

    # Level 5 — Quantity Loss
    _qty_loss = []
    QTY_TYPES = {"IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcColumn", "IfcBeam", "IfcRoof", "IfcDoor", "IfcWindow", "IfcStair"}
    for _elem in all_elements:
        _etype = _elem.is_a()
        if _etype not in QTY_TYPES:
            continue
        _has_qty = False
        for _d in getattr(_elem, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcElementQuantity"):
                    _has_qty = True
                    break
        if not _has_qty:
            _qty_loss.append({
                "Name": _elem.Name or "Unnamed",
                "GlobalId": _elem.GlobalId,
                "IFC Type": _etype,
                "Issue": "Missing IfcElementQuantity (no area/volume/length data)",
            })
    _qty_loss_count = len(_qty_loss)
    _qty_loss_pct = round(_qty_loss_count / max(total_elements, 1) * 100, 1)

    # Relationships summary
    _relationship_catalog = [
        ("IfcRelContainedInSpatialStructure", "Element -> Storey assignment"),
        ("IfcRelDefinesByProperties", "Element -> Property Sets (Psets)"),
        ("IfcRelAssociatesMaterial", "Element -> Material"),
        ("IfcRelConnectsElements", "Element <-> Element connection"),
        ("IfcRelFillsElement", "Door/Window -> Wall opening"),
        ("IfcRelAggregates", "Element -> Parent assembly"),
        ("IfcRelAssociatesClassification", "Element -> Classification system"),
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

    # Weighted Data Loss Integrity
    _data_loss_score = round(
        (_type_loss_pct / 100) * 30 +
        (_prop_loss_pct / 100) * 20 +
        (_qty_loss_pct / 100) * 15 +
        (_rel_loss_pct / 100) * 25 +
        (_geo_loss_pct / 100) * 10,
        1
    )
    _data_integrity = round(100 - _data_loss_score, 1)

    # Quality Score (0 - 100)
    _sem_score = semantic_pct / 100 * 60
    _proxy_score = (proxy_pct / 100) * 30
    quality_score = round(min(100, max(0, _sem_score - _proxy_score + _pset_score)), 1)
    if quality_score >= 85:
        quality_grade, quality_color = "Excellent", "#238636"
    elif quality_score >= 70:
        quality_grade, quality_color = "Good", "#58a6ff"
    elif quality_score >= 50:
        quality_grade, quality_color = "Fair", "#3ab8d9"
    else:
        quality_grade, quality_color = "Poor", "#ff7070"

    _score_breakdown = {
        "sem_score": round(_sem_score, 1),
        "proxy_score": round(_proxy_score, 1),
        "pset_score": round(_pset_score, 1),
        "sem_pct": round(semantic_pct, 1),
        "proxy_pct": round(proxy_pct, 1),
        "pset_pct": _pset_pct,
        "elems_requiring_pset": _elems_requiring_pset,
        "walls_total": total_walls,
        "walls_with_pset": _walls_with_pset,
        "elems_with_pset": _elems_with_pset,
    }

    # BCF / Corrections prep lists (caps applied where appropriate)
    proxy_list = []
    valid_proxies_count = 0
    invalid_proxies_count = 0
    unknown_proxies_count = 0
    for p in proxies:
        pname = p.Name or ""
        status = classify_proxy(pname)
        if status == "valid":
            valid_proxies_count += 1
            issue = "Non-physical/Reference — no IFC class needed"
        elif status == "invalid":
            invalid_proxies_count += 1
            issue = "Semantic data loss — must be reclassified"
        else:
            unknown_proxies_count += 1
            issue = "Unknown proxy — review manually"
        proxy_list.append({
            "Name": pname or "Unnamed",
            "GlobalId": p.GlobalId,
            "IFC Type": p.is_a(),
            "Status": status,
            "Issue": issue,
        })

    walls_missing_pset = [{"Wall Name": w.Name or "Unnamed",
                           "GlobalId": w.GlobalId,
                           "Issue": "Pset_WallCommon missing"}
                          for w in walls if w.GlobalId in walls_missing_pset_set]

    # Rule Validation list
    builtin_rules = []
    # NM01
    nm01_fails = [e.GlobalId for e in all_elements if not (getattr(e, "Name", None) and str(elem.Name).strip())]
    # NM02
    nm02_fails = [e.GlobalId for e in all_elements if any(kw in (getattr(e, "Name", "") or "").lower() for kw in ["unnamed", "unknown", "generic", "undefined"])]
    # NM03 (GlobalId unique)
    nm03_fails = []
    seen_gids = set()
    for e in model.by_type("IfcRoot"):
        if hasattr(e, "GlobalId"):
            if e.GlobalId in seen_gids:
                nm03_fails.append(e.GlobalId)
            seen_gids.add(e.GlobalId)
    # CL01
    cl01_fails = [p.GlobalId for p in proxies]
    # CL02 (Typed)
    cl02_fails = []
    for e in all_elements:
        has_type = False
        try:
            for rel in getattr(e, "IsTypedBy", []):
                if getattr(rel, "RelatingType", None):
                    has_type = True
                    break
        except Exception:
            pass
        if not has_type:
            cl02_fails.append(e.GlobalId)
    # PS01 (Wall Common)
    ps01_fails = list(walls_missing_pset_set)
    # PS02 (Door Common)
    ps02_fails = [e.GlobalId for e in doors if not has_pset(e, "Pset_DoorCommon")]
    # PS03 (Window Common)
    ps03_fails = [e.GlobalId for e in windows if not has_pset(e, "Pset_WindowCommon")]
    # PS04 (Slab Common)
    ps04_fails = [e.GlobalId for e in model.by_type("IfcSlab") if not has_pset(e, "Pset_SlabCommon")]
    # PS05 (IsExternal defined on walls)
    ps05_fails = [e.GlobalId for e in walls + standard_walls if get_pset_value(e, "Pset_WallCommon", "IsExternal") is None]
    # PS06 (FireRating defined on walls)
    ps06_fails = [e.GlobalId for e in walls + standard_walls if get_pset_value(e, "Pset_WallCommon", "FireRating") is None]
    # PS07 (Column Common)
    ps07_fails = [e.GlobalId for e in model.by_type("IfcColumn") if not has_pset(e, "Pset_ColumnCommon")]
    # GM01 (Placement)
    gm01_fails = [e.GlobalId for e in all_elements if not getattr(e, "ObjectPlacement", None)]
    # GM02 (Geometry Representation)
    gm02_fails = [e.GlobalId for e in all_elements if not getattr(e, "Representation", None)]
    # MT01 (Material assigned)
    mt01_fails = []
    for e in all_elements:
        has_mat = any(rel.is_a("IfcRelAssociatesMaterial") for rel in getattr(e, "HasAssociations", []))
        if not has_mat:
            mt01_fails.append(e.GlobalId)
    # IC01 (Deprecated Standard Case)
    ic01_fails = [e.GlobalId for e in standard_walls]
    # IC02 (Belong to storey)
    ic02_fails = []
    for e in all_elements:
        in_st = any(r.is_a("IfcRelContainedInSpatialStructure") and r.RelatingStructure.is_a("IfcBuildingStorey") for r in getattr(e, "ContainedInStructure", []))
        if not in_st:
            ic02_fails.append(e.GlobalId)

    rule_checks = [
        {"id": "NM01", "name": "Elements must have a Name", "category": "Naming", "severity": "High", "fails": nm01_fails},
        {"id": "NM02", "name": "No 'Unnamed' placeholders", "category": "Naming", "severity": "Medium", "fails": nm02_fails},
        {"id": "NM03", "name": "GlobalId must be unique", "category": "Naming", "severity": "Critical", "fails": nm03_fails},
        {"id": "CL01", "name": "No IfcBuildingElementProxy", "category": "Classification", "severity": "High", "fails": cl01_fails},
        {"id": "CL02", "name": "Elements must be typed", "category": "Classification", "severity": "Medium", "fails": cl02_fails},
        {"id": "PS01", "name": "Walls must have Pset_WallCommon", "category": "Property Sets", "severity": "High", "fails": ps01_fails},
        {"id": "PS02", "name": "Doors must have Pset_DoorCommon", "category": "Property Sets", "severity": "High", "fails": ps02_fails},
        {"id": "PS03", "name": "Windows must have Pset_WindowCommon", "category": "Property Sets", "severity": "High", "fails": ps03_fails},
        {"id": "PS04", "name": "Slabs must have Pset_SlabCommon", "category": "Property Sets", "severity": "Medium", "fails": ps04_fails},
        {"id": "PS05", "name": "Walls: IsExternal must be defined", "category": "Property Sets", "severity": "Medium", "fails": ps05_fails},
        {"id": "PS06", "name": "Walls: FireRating must be defined", "category": "Property Sets", "severity": "High", "fails": ps06_fails},
        {"id": "PS07", "name": "Columns must have Pset_ColumnCommon", "category": "Property Sets", "severity": "Medium", "fails": ps07_fails},
        {"id": "GM01", "name": "Elements must have placement", "category": "Geometry", "severity": "High", "fails": gm01_fails},
        {"id": "GM02", "name": "Elements must have geometry", "category": "Geometry", "severity": "High", "fails": gm02_fails},
        {"id": "MT01", "name": "Elements must have material assigned", "category": "Materials", "severity": "Medium", "fails": mt01_fails},
        {"id": "IC01", "name": "No deprecated IfcWallStandardCase", "category": "IFC Compliance", "severity": "Low", "fails": ic01_fails},
        {"id": "IC02", "name": "Elements must belong to a storey", "category": "IFC Compliance", "severity": "Medium", "fails": ic02_fails},
    ]

    # 6. NBC Compliance Checks
    nbc_results = []
    # Part 4 Wall Fire rating
    fire_pct = round((total_walls - len(ps06_fails)) / total_walls * 100, 1) if total_walls else 100
    nbc_results.append({
        "section": "Part 4 — Fire Safety", "check": "Walls must have FireRating defined",
        "standard": "NBC 2016 Cl. 4.3.2", "total": total_walls, "passed": total_walls - len(ps06_fails),
        "failed": len(ps06_fails), "score": fire_pct, "status": "Pass" if fire_pct >= 80 else "Fail",
        "severity": "Critical", "failed_samples": [w.Name or "Unnamed" for w in (walls + standard_walls) if w.GlobalId in ps06_fails][:20]
    })
    # Part 6 Column Pset ColumnCommon
    cols_total = len(model.by_type("IfcColumn"))
    col_pct = round((cols_total - len(ps07_fails)) / cols_total * 100, 1) if cols_total else 100
    nbc_results.append({
        "section": "Part 6 — Structural Design", "check": "Columns must have Pset_ColumnCommon",
        "standard": "NBC 2016 Cl. 6.1.1", "total": cols_total, "passed": cols_total - len(ps07_fails),
        "failed": len(ps07_fails), "score": col_pct, "status": "Pass" if col_pct >= 80 else "Fail",
        "severity": "Critical", "failed_samples": [c.Name or "Unnamed" for c in model.by_type("IfcColumn") if c.GlobalId in ps07_fails][:20]
    })
    # Load Bearing status
    lb_pct = round((total_walls - len(ps05_fails)) / total_walls * 100, 1) if total_walls else 100
    nbc_results.append({
        "section": "Part 6 — Structural Design", "check": "Walls must have LoadBearing status defined",
        "standard": "NBC 2016 Cl. 6.2.3", "total": total_walls, "passed": total_walls - len(ps05_fails),
        "failed": len(ps05_fails), "score": lb_pct, "status": "Pass" if lb_pct >= 80 else "Fail",
        "severity": "High", "failed_samples": [w.Name or "Unnamed" for w in (walls + standard_walls) if w.GlobalId in ps05_fails][:20]
    })
    # Part 8 Doors Common (accessibility)
    doors_total = len(doors)
    door_pct = round((doors_total - len(ps02_fails)) / doors_total * 100, 1) if doors_total else 100
    nbc_results.append({
        "section": "Part 8 — Accessibility", "check": "Doors must have Pset_DoorCommon (width, height)",
        "standard": "NBC 2016 Cl. 8.2.1", "total": doors_total, "passed": doors_total - len(ps02_fails),
        "failed": len(ps02_fails), "score": door_pct, "status": "Pass" if door_pct >= 80 else "Fail",
        "severity": "High", "failed_samples": [d.Name or "Unnamed" for d in doors if d.GlobalId in ps02_fails][:20]
    })
    # Part 11 Envelope IsExternal
    ext_pct = round((total_walls - len(ps05_fails)) / total_walls * 100, 1) if total_walls else 100
    nbc_results.append({
        "section": "Part 11 — Approach to Sustainability", "check": "Walls must define IsExternal for thermal analysis",
        "standard": "NBC 2016 Cl. 11.2", "total": total_walls, "passed": total_walls - len(ps05_fails),
        "failed": len(ps05_fails), "score": ext_pct, "status": "Pass" if ext_pct >= 80 else "Fail",
        "severity": "Medium", "failed_samples": [w.Name or "Unnamed" for w in (walls + standard_walls) if w.GlobalId in ps05_fails][:20]
    })
    # BIM Addendum (No proxies)
    bim_pass_pct = round((total_elements - len(proxies)) / total_elements * 100, 1) if total_elements else 100
    nbc_results.append({
        "section": "BIM Addendum — Data Integrity", "check": "No IfcBuildingElementProxy objects (semantic data loss)",
        "standard": "NBC 2016 BIM Addendum Cl. 3.1", "total": total_elements, "passed": total_elements - len(proxies),
        "failed": len(proxies), "score": bim_pass_pct, "status": "Pass" if len(proxies) == 0 else "Fail",
        "severity": "Critical", "failed_samples": [p.Name or "Unnamed" for p in proxies][:20]
    })
    # Part 8 Windows daylighting
    wins_total = len(windows)
    win_pct = round((wins_total - len(ps03_fails)) / wins_total * 100, 1) if wins_total else 100
    nbc_results.append({
        "section": "Part 8 — Daylighting & Ventilation", "check": "Windows must have Pset_WindowCommon",
        "standard": "NBC 2016 Cl. 8.3.1", "total": wins_total, "passed": wins_total - len(ps03_fails),
        "failed": len(ps03_fails), "score": win_pct, "status": "Pass" if win_pct >= 80 else "Fail",
        "severity": "Medium", "failed_samples": [w.Name or "Unnamed" for w in windows if w.GlobalId in ps03_fails][:20]
    })
    # Floor Slabs
    slabs_total = len(model.by_type("IfcSlab"))
    slab_pct = round((slabs_total - len(ps04_fails)) / slabs_total * 100, 1) if slabs_total else 100
    nbc_results.append({
        "section": "Part 6 — Floor Slabs", "check": "Slabs must have Pset_SlabCommon",
        "standard": "NBC 2016 Cl. 6.4.1", "total": slabs_total, "passed": slabs_total - len(ps04_fails),
        "failed": len(ps04_fails), "score": slab_pct, "status": "Pass" if slab_pct >= 80 else "Fail",
        "severity": "Medium", "failed_samples": [s.Name or "Unnamed" for s in model.by_type("IfcSlab") if s.GlobalId in ps04_fails][:20]
    })

    nbc_overall_score = round(sum(r["score"] for r in nbc_results) / len(nbc_results), 1)

    # 7. Storey Quality Analysis
    storeys = model.by_type("IfcBuildingStorey")
    proxy_ids = set(p.GlobalId for p in proxies)
    missing_pset_gids = set(p["GlobalId"] for p in missing_pset_all)
    assigned_gids = set()
    storey_data = {}

    for st_entity in storeys:
        sname = st_entity.Name or f"Storey {st_entity.GlobalId[:8]}"
        elevation = round(float(st_entity.Elevation or 0), 2) if st_entity.Elevation else 0
        elems_in_st = []
        for rel in getattr(st_entity, "ContainsElements", []):
            if rel.is_a("IfcRelContainedInSpatialStructure"):
                for elem in rel.RelatedElements:
                    if elem.is_a() in SKIP_TYPES:
                        continue
                    gid = elem.GlobalId
                    assigned_gids.add(gid)
                    if gid in proxy_ids:
                        issue = "proxy"
                    elif gid in missing_pset_gids:
                        issue = "missing_pset"
                    else:
                        issue = "ok"
                    elems_in_st.append({
                        "name": elem.Name or "Unnamed",
                        "type": elem.is_a(),
                        "issue": issue,
                        "gid": gid
                    })
        st_total = len(elems_in_st)
        st_proxies = sum(1 for e in elems_in_st if e["issue"] == "proxy")
        st_pset_m = sum(1 for e in elems_in_st if e["issue"] == "missing_pset")
        st_ok = sum(1 for e in elems_in_st if e["issue"] == "ok")

        if st_total == 0:
            st_score = 100.0
        else:
            sem_val = st_ok / st_total * 100
            prx_val = st_proxies / st_total * 100
            pset_val = st_pset_m / st_total * 100
            st_score = max(0.0, min(100.0, round((sem_val / 100) * 60 - (prx_val / 100) * 30 + (1 - pset_val / 100) * 40, 1)))

        if st_score >= 85:
            grade, col = "Excellent", "#238636"
        elif st_score >= 70:
            grade, col = "Good", "#58a6ff"
        elif st_score >= 50:
            grade, col = "Fair", "#3ab8d9"
        else:
            grade, col = "Poor", "#ff7070"

        storey_data[sname] = {
            "elevation": elevation, "total": st_total, "proxies": st_proxies,
            "missing_pset": st_pset_m, "ok": st_ok, "score": st_score,
            "grade": grade, "color": col, "elements": elems_in_st
        }

    # Unassigned elements
    unassigned = []
    for elem in all_elements:
        gid = elem.GlobalId
        if gid not in assigned_gids:
            if gid in proxy_ids:
                issue = "proxy"
            elif gid in missing_pset_gids:
                issue = "missing_pset"
            else:
                issue = "ok"
            unassigned.append({
                "name": elem.Name or "Unnamed", "type": elem.is_a(), "issue": issue, "gid": gid
            })
    if unassigned:
        u_total = len(unassigned)
        u_proxies = sum(1 for e in unassigned if e["issue"] == "proxy")
        u_pset_m = sum(1 for e in unassigned if e["issue"] == "missing_pset")
        u_ok = sum(1 for e in unassigned if e["issue"] == "ok")
        u_score = max(0.0, min(100.0, round((u_ok / u_total) * 60 - (u_proxies / u_total) * 30 + (1 - u_pset_m / u_total) * 40, 1)))

        if u_score >= 85:
            u_grade, u_col = "Excellent", "#238636"
        elif u_score >= 70:
            u_grade, u_col = "Good", "#58a6ff"
        elif u_score >= 50:
            u_grade, u_col = "Fair", "#3ab8d9"
        else:
            u_grade, u_col = "Poor", "#ff7070"

        storey_data["⚠️ Unassigned (no storey)"] = {
            "elevation": -9999, "total": u_total, "proxies": u_proxies,
            "missing_pset": u_pset_m, "ok": u_ok, "score": u_score,
            "grade": u_grade, "color": u_col, "elements": unassigned
        }

    # Bbox/Geometry Integrity Checks
    geo_integrity_issues = (
        detect_missing_representation(model) +
        detect_invalid_geometry(model) +
        detect_degenerate_bbox(model)
    )

    return {
        "export_source": exp_source,
        "step_verdict": step_verdict,
        "total_elements": total_elements,
        "total_walls": total_walls,
        "doors": len(doors),
        "windows": len(windows),
        "proxy_elements": proxy_elements,
        "valid_proxies_count": valid_proxies_count,
        "invalid_proxies_count": invalid_proxies_count,
        "unknown_proxies_count": unknown_proxies_count,
        "other_semantic": other_semantic,
        "semantic_elements": semantic_elements,
        "semantic_pct": semantic_pct,
        "proxy_pct": proxy_pct,
        "other_pct": other_pct,
        "walls_pct": walls_pct,
        "doors_pct": doors_pct,
        "windows_pct": windows_pct,
        "severity": severity,
        "quality_score": quality_score,
        "quality_grade": quality_grade,
        "quality_color": quality_color,
        "score_breakdown": _score_breakdown,
        "proxy_list": proxy_list[:500],
        "proxy_list_total": len(proxy_list),
        "missing_pset_list": missing_pset_all[:500],
        "missing_pset_count": len(missing_pset_all),
        "rel_loss_list": _rel_loss[:500],
        "rel_loss_count": _rel_loss_count,
        "rel_loss_pct": _rel_loss_pct,
        "geo_loss_list": _geo_loss[:500],
        "geo_loss_count": _geo_loss_count,
        "geo_loss_pct": _geo_loss_pct,
        "qty_loss_list": _qty_loss[:500],
        "qty_loss_count": _qty_loss_count,
        "qty_loss_pct": _qty_loss_pct,
        "type_loss_count": _type_loss_count,
        "prop_loss_count": _prop_loss_count,
        "prop_loss_pct": _prop_loss_pct,
        "data_loss_score": _data_loss_score,
        "data_integrity": _data_integrity,
        "relationship_summary": _relationship_summary,
        "type_loss_pct": _type_loss_pct,
        "walls_missing_pset": walls_missing_pset[:500],
        "nbc_results": nbc_results,
        "nbc_overall_score": nbc_overall_score,
        "storey_data": storey_data,
        "rule_checks": rule_checks,
        "geo_integrity_issues": geo_integrity_issues[:500],
        "geo_integrity_count": len(geo_integrity_issues),
    }

def detect_missing_representation(model):
    issues = []
    for elem in model.by_type("IfcProduct"):
        etype = elem.is_a()
        if etype in SKIP_TYPES or etype not in GEOMETRY_REQUIRED:
            continue
        rep = getattr(elem, "Representation", None)
        if not rep or not getattr(rep, "Representations", []):
            issues.append({
                "Name": elem.Name or "Unnamed", "GlobalId": elem.GlobalId,
                "IFC Type": etype, "Issue Type": "Missing Representation",
                "Cause": "Element exported without geometry.",
                "Impact": "Element invisible in 3D viewer; cannot be used for clash detection, QTO, or simulation.",
                "Severity": "Critical", "Recovery": "Flag for re-export or link bounding box.",
                "Details": "Representation attribute is None or empty."
            })
    return issues

def _representation_count(elem):
    rep = getattr(elem, "Representation", None)
    if not rep:
        return 0
    count = 0
    for r in getattr(rep, "Representations", []):
        count += len(getattr(r, "Items", []))
    return count

def _rep_type_labels(elem):
    rep = getattr(elem, "Representation", None)
    if not rep:
        return set()
    return {getattr(r, "RepresentationType", None) for r in getattr(rep, "Representations", [])} - {None}

def _has_solid_or_surface(elem):
    rep = getattr(elem, "Representation", None)
    if not rep:
        return False
    solid_classes = {
        "IfcFacetedBrep", "IfcClosedShell", "IfcShellBasedSurfaceModel",
        "IfcExtrudedAreaSolid", "IfcRevolvedAreaSolid",
        "IfcBooleanClippingResult", "IfcBooleanResult",
        "IfcPolygonalFaceSet", "IfcTriangulatedFaceSet",
        "IfcSurfaceModel", "IfcConnectedFaceSet",
        "IfcCsgSolid", "IfcSweptDiskSolid",
    }
    for r in getattr(rep, "Representations", []):
        for item in getattr(r, "Items", []):
            if item.is_a() in solid_classes:
                return True
            for attr in ("FirstOperand", "SecondOperand"):
                child = getattr(item, attr, None)
                if child and child.is_a() in solid_classes:
                    return True
    return False

def detect_invalid_geometry(model):
    issues = []
    for elem in model.by_type("IfcProduct"):
        etype = elem.is_a()
        if etype in SKIP_TYPES or etype not in GEOMETRY_REQUIRED:
            continue
        rep = getattr(elem, "Representation", None)
        if not rep or not getattr(rep, "Representations", []):
            continue
        rep_types = _rep_type_labels(elem)
        item_count = _representation_count(elem)
        has_solid = _has_solid_or_surface(elem)
        if item_count > 0 and not has_solid:
            issues.append({
                "Name": elem.Name or "Unnamed", "GlobalId": elem.GlobalId,
                "IFC Type": etype, "Issue Type": "No Solid/Surface Body",
                "Cause": "Representation exists but contains no solid/surface body.",
                "Impact": "Element appears as wireframe or point; volume/area quantities cannot be computed.",
                "Severity": "High", "Recovery": "Solid recovery requires authoring tool or extrusion wrapper.",
                "Details": f"Rep types: {', '.join(rep_types) or 'None'} · Items: {item_count}"
            })
    return issues

def _get_bbox(elem):
    rep = getattr(elem, "Representation", None)
    if not rep:
        return None
    for r in getattr(rep, "Representations", []):
        for item in getattr(r, "Items", []):
            if item.is_a("IfcBoundingBox"):
                try:
                    c = item.Corner
                    return (
                        float(c.Coordinates[0]), float(c.Coordinates[1]), float(c.Coordinates[2]),
                        float(item.XDim), float(item.YDim), float(item.ZDim)
                    )
                except Exception:
                    pass
    return None

def detect_degenerate_bbox(model):
    issues = []
    ZERO_THRESHOLD = 1e-4
    EXTREME_DIM_M = 1000.0
    for elem in model.by_type("IfcProduct"):
        etype = elem.is_a()
        if etype in SKIP_TYPES:
            continue
        bbox = _get_bbox(elem)
        if bbox is None:
            continue
        _x, _y, _z, dx, dy, dz = bbox
        if dx < ZERO_THRESHOLD or dy < ZERO_THRESHOLD or dz < ZERO_THRESHOLD:
            issues.append({
                "Name": elem.Name or "Unnamed", "GlobalId": elem.GlobalId,
                "IFC Type": etype, "Issue Type": "Zero Bounding Box",
                "Cause": "Bounding box dimensions are zero or near-zero on at least one axis.",
                "Impact": "Zero-volume elements break quantity take-off, energy analysis, and structural simulation.",
                "Severity": "High", "Recovery": "Check unit scale factor in IfcProject.UnitsInContext.",
                "Details": f"Dim: ({dx:.4f}, {dy:.4f}, {dz:.4f})"
            })
        elif dx > EXTREME_DIM_M or dy > EXTREME_DIM_M or dz > EXTREME_DIM_M:
            issues.append({
                "Name": elem.Name or "Unnamed", "GlobalId": elem.GlobalId,
                "IFC Type": etype, "Issue Type": "Extreme Bounding Box",
                "Cause": "Bounding box dimension exceeds 1,000 m.",
                "Impact": "Model bounding box distorted; section cuts, plans, and clash spheres are unusable.",
                "Severity": "High", "Recovery": "Divide coordinates by 1000 (mm -> m). Check unit scale factor.",
                "Details": f"Dim: ({dx:.1f}, {dy:.1f}, {dz:.1f})"
            })
    return issues
