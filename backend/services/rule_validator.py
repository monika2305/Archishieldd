import ifcopenshell
import re
import os

SKIP_TYPES = {
    "IfcSpace", "IfcOpeningElement", "IfcVirtualElement", "IfcAnnotation",
    "IfcGrid", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcProject",
    "IfcRelAggregates", "IfcZone", "IfcSpatialZone", "IfcRelContainedInSpatialStructure",
}

def get_pset_value(elem, pset_name, prop_name):
    try:
        for defn in getattr(elem, "IsDefinedBy", []):
            if defn.is_a("IfcRelDefinesByProperties"):
                ps = defn.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet") and ps.Name == pset_name:
                    for prop in getattr(ps, "HasProperties", []):
                        if prop.Name == prop_name:
                            val = getattr(prop, "NominalValue", None)
                            if val is not None:
                                return val.wrappedValue
    except Exception:
        pass
    return None

def get_all_psets(elem):
    result = {}
    try:
        for defn in getattr(elem, "IsDefinedBy", []):
            if defn.is_a("IfcRelDefinesByProperties"):
                ps = defn.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet"):
                    props = {}
                    for prop in getattr(ps, "HasProperties", []):
                        val = getattr(prop, "NominalValue", None)
                        props[prop.Name] = val.wrappedValue if val is not None else None
                    result[ps.Name] = props
    except Exception:
        pass
    return result

def has_pset(elem, pset_name):
    return pset_name in get_all_psets(elem)

def elem_name(elem):
    return getattr(elem, "Name", None) or "Unnamed"

def elem_type_name(elem):
    try:
        for rel in getattr(elem, "IsTypedBy", []):
            t = getattr(rel, "RelatingType", None)
            if t:
                return getattr(t, "Name", None) or getattr(t, "is_a", lambda: "")()
    except Exception:
        pass
    return None

def run_compliance_validation(model_path, selected_builtin_ids, custom_rules):
    if not os.path.exists(model_path):
        return {"error": "Model file not found"}

    try:
        model = ifcopenshell.open(model_path)
    except Exception as e:
        return {"error": f"Failed to open IFC model: {str(e)}"}

    all_products = [e for e in model.by_type("IfcProduct") if e.is_a() not in SKIP_TYPES]
    
    # 1. Built-in rules checklist definition
    builtin_defs = {
        "NM01": {
            "name": "Elements must have a Name", "category": "Naming", "severity": "High", "applies_to": None,
            "check": lambda e: bool(getattr(e, "Name", None) and str(e.Name).strip()),
            "fail_msg": lambda e: "Name is missing or empty"
        },
        "NM02": {
            "name": "No 'Unnamed' placeholders", "category": "Naming", "severity": "Medium", "applies_to": None,
            "check": lambda e: not any(kw in (getattr(e, "Name", "") or "").lower() for kw in ["unnamed", "unknown", "generic", "undefined"]),
            "fail_msg": lambda e: f"Name '{elem_name(e)}' contains placeholder keyword"
        },
        "NM03": {
            "name": "GlobalId must be unique", "category": "Naming", "severity": "Critical", "applies_to": None,
            "check": None, # Handled batch-wise
            "fail_msg": lambda e: "Duplicate GlobalId detected"
        },
        "CL01": {
            "name": "No IfcBuildingElementProxy", "category": "Classification", "severity": "High", "applies_to": "IfcBuildingElementProxy",
            "check": lambda e: False,
            "fail_msg": lambda e: f"'{elem_name(e)}' is an unclassified proxy element"
        },
        "CL02": {
            "name": "Elements must be typed", "category": "Classification", "severity": "Medium", "applies_to": None,
            "check": lambda e: elem_type_name(e) is not None,
            "fail_msg": lambda e: f"'{elem_name(e)}' has no element type assigned"
        },
        "PS01": {
            "name": "Walls must have Pset_WallCommon", "category": "Property Sets", "severity": "High", "applies_to": "IfcWall",
            "check": lambda e: has_pset(e, "Pset_WallCommon"),
            "fail_msg": lambda e: f"Wall '{elem_name(e)}' is missing Pset_WallCommon"
        },
        "PS02": {
            "name": "Doors must have Pset_DoorCommon", "category": "Property Sets", "severity": "High", "applies_to": "IfcDoor",
            "check": lambda e: has_pset(e, "Pset_DoorCommon"),
            "fail_msg": lambda e: f"Door '{elem_name(e)}' is missing Pset_DoorCommon"
        },
        "PS03": {
            "name": "Windows must have Pset_WindowCommon", "category": "Property Sets", "severity": "High", "applies_to": "IfcWindow",
            "check": lambda e: has_pset(e, "Pset_WindowCommon"),
            "fail_msg": lambda e: f"Window '{elem_name(e)}' is missing Pset_WindowCommon"
        },
        "PS04": {
            "name": "Slabs must have Pset_SlabCommon", "category": "Property Sets", "severity": "Medium", "applies_to": "IfcSlab",
            "check": lambda e: has_pset(e, "Pset_SlabCommon"),
            "fail_msg": lambda e: f"Slab '{elem_name(e)}' is missing Pset_SlabCommon"
        },
        "PS05": {
            "name": "Walls: IsExternal must be defined", "category": "Property Sets", "severity": "Medium", "applies_to": "IfcWall",
            "check": lambda e: get_pset_value(e, "Pset_WallCommon", "IsExternal") is not None,
            "fail_msg": lambda e: f"Wall '{elem_name(e)}' — IsExternal not defined in Pset_WallCommon"
        },
        "PS06": {
            "name": "Walls: FireRating must be defined", "category": "Property Sets", "severity": "High", "applies_to": "IfcWall",
            "check": lambda e: get_pset_value(e, "Pset_WallCommon", "FireRating") is not None,
            "fail_msg": lambda e: f"Wall '{elem_name(e)}' — FireRating not set in Pset_WallCommon"
        },
        "PS07": {
            "name": "Columns must have Pset_ColumnCommon", "category": "Property Sets", "severity": "Medium", "applies_to": "IfcColumn",
            "check": lambda e: has_pset(e, "Pset_ColumnCommon"),
            "fail_msg": lambda e: f"Column '{elem_name(e)}' is missing Pset_ColumnCommon"
        },
        "GM01": {
            "name": "Elements must have placement", "category": "Geometry", "severity": "High", "applies_to": None,
            "check": lambda e: getattr(e, "ObjectPlacement", None) is not None,
            "fail_msg": lambda e: f"'{elem_name(e)}' has no ObjectPlacement"
        },
        "GM02": {
            "name": "Elements must have geometry", "category": "Geometry", "severity": "High", "applies_to": None,
            "check": lambda e: getattr(e, "Representation", None) is not None,
            "fail_msg": lambda e: f"'{elem_name(e)}' has no geometric representation"
        },
        "MT01": {
            "name": "Elements must have material assigned", "category": "Materials", "severity": "Medium", "applies_to": None,
            "check": lambda e: any(rel.is_a("IfcRelAssociatesMaterial") for rel in getattr(e, "HasAssociations", [])),
            "fail_msg": lambda e: f"'{elem_name(e)}' has no material assigned"
        },
        "IC01": {
            "name": "No deprecated IfcWallStandardCase", "category": "IFC Compliance", "severity": "Low", "applies_to": "IfcWallStandardCase",
            "check": lambda e: False,
            "fail_msg": lambda e: f"'{elem_name(e)}' uses deprecated IfcWallStandardCase"
        },
        "IC02": {
            "name": "Elements must belong to a storey", "category": "IFC Compliance", "severity": "Medium", "applies_to": None,
            "check": lambda e: any(r.is_a("IfcRelContainedInSpatialStructure") and r.RelatingStructure.is_a("IfcBuildingStorey") for r in getattr(e, "ContainedInStructure", [])),
            "fail_msg": lambda e: f"'{elem_name(e)}' is not assigned to a building storey"
        }
    }

    results = []
    pass_count = 0
    fail_count = 0

    # Batch GlobalId uniqueness check
    gid_seen = {}
    for elem in all_products:
        gid = elem.GlobalId
        if gid:
            gid_seen.setdefault(gid, []).append(elem)

    # 2. Run selected built-in rules
    for rid in selected_builtin_ids:
        rule = builtin_defs.get(rid)
        if not rule:
            continue
        
        if rid == "NM03":
            # Batch check
            for gid, elems in gid_seen.items():
                if len(elems) > 1:
                    for e in elems:
                        results.append({
                            "Rule ID": rid, "Rule": rule["name"], "Category": rule["category"], "Severity": rule["severity"],
                            "Status": "❌ FAIL", "Element": elem_name(e), "IFC Type": e.is_a(), "GlobalId": e.GlobalId,
                            "Message": f"Duplicate GlobalId: {gid}"
                        })
                        fail_count += 1
            # Remaining elements are passes
            pass_count += sum(1 for gid, elems in gid_seen.items() if len(elems) == 1)
            continue

        applies = rule["applies_to"]
        elems_to_check = model.by_type(applies) if applies else all_products

        chk = rule["check"]
        for e in elems_to_check:
            if e.is_a() in SKIP_TYPES:
                continue
            try:
                passed = chk(e)
            except Exception:
                passed = True
            
            if passed:
                pass_count += 1
            else:
                fail_count += 1
                results.append({
                    "Rule ID": rid, "Rule": rule["name"], "Category": rule["category"], "Severity": rule["severity"],
                    "Status": "❌ FAIL", "Element": elem_name(e), "IFC Type": e.is_a(), "GlobalId": e.GlobalId,
                    "Message": rule["fail_msg"](e)
                })

    # 3. Run custom rules
    for rule in custom_rules:
        applies = rule.get("applies_to")
        elems_to_check = model.by_type(applies) if applies else all_products
        pset_req = rule.get("pset")
        prop_req = rule.get("prop")
        val_req = rule.get("value")

        for e in elems_to_check:
            if e.is_a() in SKIP_TYPES:
                continue
            passed = True
            msg = ""
            try:
                if pset_req:
                    if not has_pset(e, pset_req):
                        passed = False
                        msg = f"Missing required Pset: {pset_req}"
                    elif prop_req:
                        val = get_pset_value(e, pset_req, prop_req)
                        if val is None:
                            passed = False
                            msg = f"{pset_req}.{prop_req} not defined"
                        elif val_req:
                            v_str = str(val_req).strip()
                            try:
                                v_float = float(val)
                                if v_str.startswith("<=") and not v_float <= float(v_str[2:]):
                                    passed = False
                                    msg = f"{prop_req}={v_float} but required {v_str}"
                                elif v_str.startswith(">=") and not v_float >= float(v_str[2:]):
                                    passed = False
                                    msg = f"{prop_req}={v_float} but required {v_str}"
                                elif v_str.startswith("<") and not v_float < float(v_str[1:]):
                                    passed = False
                                    msg = f"{prop_req}={v_float} but required {v_str}"
                                elif v_str.startswith(">") and not v_float > float(v_str[1:]):
                                    passed = False
                                    msg = f"{prop_req}={v_float} but required {v_str}"
                                elif v_str.startswith("=") and str(val) != v_str[1:].strip():
                                    passed = False
                                    msg = f"{prop_req}={val} but required {v_str}"
                            except (ValueError, TypeError):
                                if str(val).lower() != v_str.lower():
                                    passed = False
                                    msg = f"{prop_req}='{val}' but expected '{v_str}'"
            except Exception:
                passed = True

            if passed:
                pass_count += 1
            else:
                fail_count += 1
                results.append({
                    "Rule ID": rule["id"], "Rule": rule["name"], "Category": rule["category"], "Severity": rule["severity"],
                    "Status": "❌ FAIL", "Element": elem_name(e), "IFC Type": e.is_a(), "GlobalId": e.GlobalId,
                    "Message": msg or f"Failed custom rule: {rule['name']}"
                })

    return {
        "results": results,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total_checks": pass_count + fail_count
    }
