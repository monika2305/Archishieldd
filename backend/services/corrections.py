import re
import uuid
import ifcopenshell

# Smart suggestions configuration
SMART_RULES = [
    (["solar","photovoltaic","pv panel","solar panel","pv module"],
        "IfcSolarDevice",          "Photovoltaic / solar energy device — best match"),
    (["fireplace","fire place","fire hang","hearth"],
        "IfcSpaceHeater",          "Fireplace / heating appliance → IfcSpaceHeater"),
    (["space heater","radiator"],
        "IfcSpaceHeater",          "Space heater / radiator → IfcSpaceHeater"),
    (["cooktop","cook top","oven","hob","stove"],
        "IfcCookingAppliance",     "Cooking appliance — best IFC class for hobs/ovens"),
    (["microwave","fridge","freezer","refrigerator","dishwasher","dish washer",
       "washing machine","washing","tumble dryer","dryer"],
        "IfcElectricAppliance",    "Electric domestic appliance — best IFC class"),
    (["rangehood","range hood","extractor"],
        "IfcFlowTerminal",         "Rangehood / extraction — IfcFlowTerminal (acceptable)"),
    (["water glass","glass","cup","mug","jug"],
        "IfcFurnishingElement",    "Glassware / tableware → IfcFurnishingElement"),
    (["wall","wand","mur"],        "IfcWall",                "Structural wall element"),
    (["door","tur","porte"],       "IfcDoor",                "Door element"),
    (["window","fenster"],         "IfcWindow",              "Window element"),
    (["slab","floor","dalle"],     "IfcSlab",                "Floor / slab element"),
    (["beam","trager","girder"],   "IfcBeam",                "Structural beam / girder"),
    (["column","col","pillar"],    "IfcColumn",              "Structural column"),
    (["stair","step"],             "IfcStair",               "Stair element"),
    (["roof","dach"],              "IfcRoof",                "Roof element"),
    (["pipe","rohr","drain","plumb"], "IfcPipeSegment",      "Pipe / plumbing segment"),
    (["water"],                    "IfcPipeSegment",         "Water system — pipe assumed (safe default)"),
    (["duct","hvac"],              "IfcFlowSegment",         "HVAC duct segment"),
    (["light","lamp","luminaire"], "IfcLightFixture",        "Lighting fixture"),
    (["electric","switch","socket"],"IfcElectricalElement",  "Electrical device"),
    (["pump","fan","motor","boiler","chiller"], "IfcMechanicalEquipment", "Mechanical equipment"),
    (["heater","cooler","exchanger"],"IfcEnergyConversionDevice","Energy conversion device"),
    (["tree","plant","shrub","bush","hedge"], "IfcPlant",    "Landscape planting element"),
    (["chair","table","desk","sofa","bed","furn","cabinet","shelf","wardrobe"],
        "IfcFurnishingElement",    "Furniture / furnishing element"),
    (["toilet","sink","basin","bath","shower"], "IfcFlowTerminal", "Sanitary terminal"),
    (["terminal","outlet","inlet","diffuser"],  "IfcFlowTerminal", "Flow terminal / endpoint"),
]

PSET_DEFINITIONS = {
    "IfcWall": {
        "pset_name": "Pset_WallCommon",
        "props": [
            ("IsExternal",           "IFCBOOLEAN(.F.)"),
            ("LoadBearing",          "IFCBOOLEAN(.F.)"),
            ("FireRating",           "IFCLABEL('')"),
            ("AcousticRating",       "IFCLABEL('')"),
            ("ThermalTransmittance", "IFCTHERMALTRANSMITTANCEMEASURE(0)"),
            ("ExtendToStructure",    "IFCBOOLEAN(.F.)"),
        ],
    },
    "IfcDoor": {
        "pset_name": "Pset_DoorCommon",
        "props": [
            ("FireRating",        "IFCLABEL('')"),
            ("AcousticRating",    "IFCLABEL('')"),
            ("IsExternal",        "IFCBOOLEAN(.F.)"),
            ("HandicapAccessible","IFCBOOLEAN(.F.)"),
        ],
    },
    "IfcWindow": {
        "pset_name": "Pset_WindowCommon",
        "props": [
            ("FireRating",           "IFCLABEL('')"),
            ("AcousticRating",       "IFCLABEL('')"),
            ("IsExternal",           "IFCBOOLEAN(.T.)"),
            ("ThermalTransmittance", "IFCTHERMALTRANSMITTANCEMEASURE(0)"),
        ],
    },
    "IfcSlab": {
        "pset_name": "Pset_SlabCommon",
        "props": [
            ("LoadBearing",  "IFCBOOLEAN(.T.)"),
            ("IsExternal",   "IFCBOOLEAN(.F.)"),
            ("FireRating",   "IFCLABEL('')"),
            ("PitchAngle",   "IFCPLANEANGLEMEASURE(0)"),
        ],
    },
    "IfcColumn": {
        "pset_name": "Pset_ColumnCommon",
        "props": [
            ("LoadBearing",  "IFCBOOLEAN(.T.)"),
            ("IsExternal",   "IFCBOOLEAN(.F.)"),
            ("FireRating",   "IFCLABEL('')"),
        ],
    },
    "IfcBeam": {
        "pset_name": "Pset_BeamCommon",
        "props": [
            ("LoadBearing",  "IFCBOOLEAN(.T.)"),
            ("IsExternal",   "IFCBOOLEAN(.F.)"),
            ("FireRating",   "IFCLABEL('')"),
            ("Span",         "IFCPOSITIVELENGTHMEASURE(0)"),
        ],
    },
    "IfcRoof": {
        "pset_name": "Pset_RoofCommon",
        "props": [
            ("FireRating",   "IFCLABEL('')"),
            ("IsExternal",   "IFCBOOLEAN(.T.)"),
        ],
    },
    "IfcStair": {
        "pset_name": "Pset_StairCommon",
        "props": [
            ("FireRating",        "IFCLABEL('')"),
            ("HandicapAccessible","IFCBOOLEAN(.F.)"),
            ("NumberOfRiser",     "IFCINTEGER(0)"),
            ("NumberOfTreads",    "IFCINTEGER(0)"),
        ],
    },
    "IfcRailing": {
        "pset_name": "Pset_RailingCommon",
        "props": [
            ("IsExternal",   "IFCBOOLEAN(.F.)"),
        ],
    },
    "IfcPipeSegment": {
        "pset_name": "Pset_PipeSegmentTypeCommon",
        "props": [
            ("Status",           "IFCLABEL('NEW')"),
            ("NominalDiameter",  "IFCPOSITIVELENGTHMEASURE(0)"),
            ("NominalLength",    "IFCPOSITIVELENGTHMEASURE(0)"),
            ("WorkingPressure",  "IFCPRESSSUREMEASURE(0)"),
        ],
    },
    "IfcPipeFitting": {
        "pset_name": "Pset_PipeFittingTypeCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
            ("NominalDiameter", "IFCPOSITIVELENGTHMEASURE(0)"),
            ("WorkingPressure", "IFCPRESSSUREMEASURE(0)"),
        ],
    },
    "IfcFlowSegment": {
        "pset_name": "Pset_FlowSegmentTypeCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
            ("NominalLength",   "IFCPOSITIVELENGTHMEASURE(0)"),
        ],
    },
    "IfcFlowTerminal": {
        "pset_name": "Pset_FlowTerminalTypeCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
        ],
    },
    "IfcMechanicalEquipment": {
        "pset_name": "Pset_ManufacturerTypeInformation",
        "props": [
            ("Manufacturer",       "IFCLABEL('')"),
            ("ModelLabel",         "IFCLABEL('')"),
            ("ProductionYear",     "IFCLABEL('')"),
            ("NominalPower",       "IFCPOWERMEASURE(0)"),
        ],
    },
    "IfcEnergyConversionDevice": {
        "pset_name": "Pset_EnergyConversionDeviceCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
        ],
    },
    "IfcElectricalElement": {
        "pset_name": "Pset_ElectricalDeviceCommon",
        "props": [
            ("Status",              "IFCLABEL('NEW')"),
            ("NominalVoltage",      "IFCELECTRICVOLTAGEMEASURE(0)"),
            ("NominalFrequency",    "IFCFREQUENCYMEASURE(0)"),
        ],
    },
    "IfcLightFixture": {
        "pset_name": "Pset_LightFixtureTypeCommon",
        "props": [
            ("Status",              "IFCLABEL('NEW')"),
            ("LightFixtureType",    "IFCLABEL('POINTSOURCE')"),
            ("NumberOfSources",     "IFCINTEGER(1)"),
        ],
    },
    "IfcDistributionElement": {
        "pset_name": "Pset_DistributionSystemCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
        ],
    },
    "IfcPlant": {
        "pset_name": "Pset_PlantCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
        ],
    },
    "IfcSite": {
        "pset_name": "Pset_SiteCommon",
        "props": [
            ("BuildableArea",       "IFCAREAMEASURE(0)"),
            ("TotalArea",           "IFCAREAMEASURE(0)"),
            ("SiteLandTitleNumber", "IFCLABEL('')"),
        ],
    },
}

MATERIAL_DEFAULTS = {
    "IfcWall":       "Concrete",
    "IfcSlab":       "Concrete",
    "IfcColumn":     "Concrete",
    "IfcBeam":       "Steel",
    "IfcRoof":       "Concrete",
    "IfcStair":      "Concrete",
    "IfcDoor":       "Wood",
    "IfcWindow":     "Aluminium",
    "IfcRailing":    "Steel",
    "IfcPipeSegment":"Steel",
    "IfcPipeFitting":"Steel",
    "IfcFlowSegment":"Steel",
    "IfcFlowTerminal":"Aluminium",
    "IfcCookingAppliance":"Steel",
    "IfcElectricAppliance":"Steel",
    "IfcLightFixture":"Aluminium",
    "IfcElectricalElement":"Copper",
    "IfcMechanicalEquipment":"Steel",
    "IfcEnergyConversionDevice":"Steel",
    "IfcDistributionElement":"Steel",
    "IfcPlant":"Organic",
}

VALID_PROXY_KEYWORDS_CS = [
    "rpc", "entourage", "geo", "georeference", "geo-reference", "survey", "origin", "basepoint",
    "car", "vehicle", "truck", "bus", "people", "person", "human", "pedestrian",
    "vase", "bottle", "plate", "decor", "decoration", "ornament", "art", "sculpture",
    "pot", "bowl", "jar", "planter", "flower", "wine",
]

def is_valid_reference_proxy(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in VALID_PROXY_KEYWORDS_CS)

def get_smart_suggestions(name: str, schema_supports_fn) -> list:
    n = (name or "").lower()
    seen = {}
    reasons = {}

    for keywords, cls, reason in SMART_RULES:
        for kw in keywords:
            if kw in n:
                if n == kw or n.startswith(kw + " ") or n.startswith(kw + ":"):
                    score = 97
                elif " " + kw in n or ":" + kw in n:
                    score = 92
                else:
                    score = 78

                current_best = max(seen.values()) if seen else 0
                if score >= current_best and cls not in seen:
                    pass
                elif cls in seen and score <= seen[cls]:
                    continue

                other_best = max((v for c, v in seen.items() if c != cls), default=0)
                if other_best == 97 and score == 97:
                    score = 92

                if score > seen.get(cls, -1):
                    seen[cls] = score
                    reasons[cls] = reason

    ranked = sorted(seen.items(), key=lambda x: -x[1])
    # Filter by schema support
    filtered = []
    for cls, score in ranked:
        if schema_supports_fn(cls):
            filtered.append((cls, score, reasons[cls]))
    return filtered[:5]

def get_suggested_type_single(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in ["wall", "wand", "mur", "muur"]):                  return "IfcWall"
    if any(k in n for k in ["door", "tur", "porte", "deur"]):                 return "IfcDoor"
    if any(k in n for k in ["window", "fenster", "fenetre", "raam"]):         return "IfcWindow"
    if any(k in n for k in ["slab", "floor", "dalle", "platte"]):             return "IfcSlab"
    if any(k in n for k in ["column", "col", "stutze", "pilier", "pillar"]):  return "IfcColumn"
    if any(k in n for k in ["beam", "trager", "poutre", "balk", "girder"]):   return "IfcBeam"
    if any(k in n for k in ["stair", "treppe", "escalier", "step"]):          return "IfcStair"
    if any(k in n for k in ["roof", "dach", "toit", "dak"]):                  return "IfcRoof"
    if any(k in n for k in ["rail", "gelander", "garde", "handrail"]):        return "IfcRailing"
    if any(k in n for k in ["solar", "photovoltaic", "pv panel", "solar panel", "pv module"]): return "IfcSolarDevice"
    if any(k in n for k in ["fireplace", "fire place", "fire hang", "hearth", "space heater", "radiator"]): return "IfcSpaceHeater"
    if any(k in n for k in ["pipe", "rohr", "tuyau", "drain", "plumb"]):      return "IfcPipeSegment"
    if "water" in n and not any(k in n for k in ["glass", "cup", "bottle", "jug", "mug"]): return "IfcPipeSegment"
    if any(k in n for k in ["fitting", "elbow", "tee", "coupling"]):          return "IfcPipeFitting"
    if any(k in n for k in ["duct", "kanal", "gaine", "hvac"]):               return "IfcFlowSegment"
    if any(k in n for k in ["cooktop", "cook top", "oven", "hob", "stove"]):  return "IfcCookingAppliance"
    if any(k in n for k in ["microwave", "fridge", "freezer", "refrigerator", "dishwasher", "washing", "dryer"]): return "IfcElectricAppliance"
    if any(k in n for k in ["rangehood", "range hood", "extractor"]):         return "IfcFlowTerminal"
    if any(k in n for k in ["toilet", "sink", "basin", "bath", "shower", "sanit", "terminal", "outlet", "inlet", "diffuser"]): return "IfcFlowTerminal"
    if any(k in n for k in ["light", "lamp", "luminaire", "fixture"]):        return "IfcLightFixture"
    if any(k in n for k in ["electric", "cable", "wire", "switch", "socket", "panel"]): return "IfcElectricalElement"
    if any(k in n for k in ["pump", "fan", "motor", "compressor", "boiler", "chiller"]): return "IfcMechanicalEquipment"
    if any(k in n for k in ["heater", "cooler", "exchanger", "condenser"]):   return "IfcEnergyConversionDevice"
    if any(k in n for k in ["tree", "plant", "shrub", "bush", "hedge", "grass"]): return "IfcPlant"
    if any(k in n for k in ["site", "terrain", "ground", "earth"]):           return "IfcSite"
    if any(k in n for k in ["water glass", "glass", "cup", "mug", "jug"]):    return "IfcFurnishingElement"
    if any(k in n for k in ["chair", "table", "desk", "sofa", "bed", "cabinet", "shelf", "furn", "seat", "bench", "wardrobe"]):  return "IfcFurnishingElement"
    return None

def get_confidence_score(name: str, suggested: str) -> int:
    if not suggested or suggested in {"IfcDistributionElement", "IfcBuildingElement", "IfcElement"}:
        return 0
    n = (name or "").lower()
    exact_map = {
        "IfcWall":                ["wall","wand","mur"],
        "IfcDoor":                ["door","tur","porte"],
        "IfcWindow":              ["window","fenster"],
        "IfcSlab":                ["slab","floor","dalle"],
        "IfcColumn":              ["column","col","stütze"],
        "IfcBeam":                ["beam","träger","poutre","girder"],
        "IfcStair":               ["stair","treppe"],
        "IfcRoof":                ["roof","dach"],
        "IfcFurnishingElement":   ["chair","table","desk","sofa","bed","furn"],
        "IfcPipeSegment":         ["pipe","water","drain","plumb"],
        "IfcFlowSegment":         ["duct","hvac"],
        "IfcCookingAppliance":    ["cooktop","cook top","oven","hob","stove"],
        "IfcElectricAppliance":   ["microwave","fridge","freezer","refrigerator","dishwasher","washing","dryer"],
        "IfcFlowTerminal":        ["terminal","outlet","rangehood","toilet","sink","basin","bath","shower"],
        "IfcLightFixture":        ["light","lamp","luminaire"],
        "IfcMechanicalEquipment": ["pump","fan","motor","compressor","boiler","chiller"],
    }
    keywords = exact_map.get(suggested, [])
    if any(k in n for k in keywords):
        return 97
    if not n or n in ("unnamed", "generic model", "object", "element", "component", "model"):
        return 20
    return 60

def build_corrected_ifc_text(temp_ifc_path: str, selections: dict, pset_fixes: dict, schema_supports_fn) -> tuple:
    with open(temp_ifc_path, "r", encoding="utf-8", errors="replace") as f:
        ifc_text = f.read()

    # Find OwnerHistory and Entity ID range
    all_ids = re.findall(r"^#(\d+)=", ifc_text, re.MULTILINE)
    next_id = max(int(i) for i in all_ids) + 1 if all_ids else 9000

    def nid():
        nonlocal next_id
        n = next_id
        next_id += 1
        return n

    oh_m = re.search(r"(#\d+)=\s*IFCOWNERHISTORY\(", ifc_text, re.IGNORECASE)
    owner_ref = oh_m.group(1) if oh_m else "$"

    new_entities = []
    fix_log = []
    skip_log = []
    pset_fix_log = []

    def _inject_pset(elem_ref, ifc_type, pset_name_override=None):
        pdef = PSET_DEFINITIONS.get(ifc_type)
        if not pdef:
            return None
        pname = pset_name_override or pdef["pset_name"]

        # Prevent duplicates
        if f"'{pname}'" in ifc_text:
            return None

        prop_refs = []
        for prop_name, prop_val in pdef["props"]:
            pid = nid()
            new_entities.append(f"#{pid}= IFCPROPERTYSINGLEVALUE('{prop_name}',$,{prop_val},$);")
            prop_refs.append(f"#{pid}")
        
        ps_id = nid()
        rel_id = nid()
        pg = uuid.uuid4().hex[:22].upper()
        rg = uuid.uuid4().hex[:22].upper()

        new_entities.append(f"#{ps_id}= IFCPROPERTYSET('{pg}',{owner_ref},'{pname}',$,"
                            f"({','.join(prop_refs)}));")
        new_entities.append(f"#{rel_id}= IFCRELDEFINESBYPROPERTIES('{rg}',{owner_ref},$,$,"
                            f"({elem_ref}),#{ps_id});")
        return pname

    def _inject_material(elem_ref, ifc_type):
        # Check if material exists
        rel_mat_blocks = re.findall(r"IFCRELASSOCIATESMATERIAL\s*\([^;]*?\)\s*;", ifc_text, re.IGNORECASE | re.DOTALL)
        escaped_ref = re.escape(elem_ref)
        for block in rel_mat_blocks:
            if re.search(r'\b' + escaped_ref + r'\b', block, re.IGNORECASE):
                return None

        mat_name = MATERIAL_DEFAULTS.get(ifc_type)
        if not mat_name:
            return None

        mat_id = nid()
        matl_id = nid()
        matg = uuid.uuid4().hex[:22].upper()

        new_entities.append(f"#{mat_id}= IFCMATERIAL('{mat_name}',$,$);")
        new_entities.append(f"#{matl_id}= IFCRELASSOCIATESMATERIAL('{matg}',{owner_ref},$,$,"
                            f"({elem_ref}),#{mat_id});")
        return mat_name

    # Protect spatial and other relationship lines from edits
    PROTECTED_PREFIXES = (
        "IFCRELCONTAINEDINSPATIALSTRUCTURE",
        "IFCRELDEFINESBYPROPERTIES",
        "IFCRELASSOCIATESMATERIAL",
        "IFCRELCONNECTSELEMENTS",
        "IFCRELFILLSELEMENT",
        "IFCRELAGGREGATES",
    )

    # PASS A: Proxy Reclassification
    for gid, new_type in selections.items():
        if not new_type or new_type in ("IfcBuildingElementProxy", "— Select IFC Class —"):
            skip_log.append(f"Skipped (proxy target default): {gid[:22]}")
            continue

        if not schema_supports_fn(new_type):
            skip_log.append(f"Schema unsupported {new_type}: {gid[:22]}")
            continue

        new_upper = new_type.upper()
        escaped = re.escape(gid)
        pat = rf"(#\d+=\s*)IFCBUILDINGELEMENTPROXY(\(\s*'{escaped}')"

        candidate = re.search(pat, ifc_text, re.IGNORECASE)
        if not candidate:
            skip_log.append(f"Not found: {gid[:22]}")
            continue

        matched_line = ifc_text[max(0, candidate.start()-5):candidate.end()+10].upper()
        if any(matched_line.lstrip("#0123456789= ").startswith(p) for p in PROTECTED_PREFIXES):
            skip_log.append(f"Relationship line matching {gid[:22]} skipped")
            continue

        new_txt, n = re.subn(pat, rf"\g<1>{new_upper}\g<2>", ifc_text, flags=re.IGNORECASE)
        if n == 0:
            skip_log.append(f"Regex swap failed: {gid[:22]}")
            continue
        ifc_text = new_txt

        # Find element ref ID
        em = re.search(rf"(#\d+)=\s*{new_upper}\(\s*'{escaped}'", ifc_text, re.IGNORECASE)
        elem_ref = em.group(1) if em else None
        if not elem_ref:
            fix_log.append((gid, new_type, None, None))
            continue

        pset_name = _inject_pset(elem_ref, new_type)
        mat_name = _inject_material(elem_ref, new_type)
        fix_log.append((gid, new_type, pset_name, mat_name))

    # PASS B: Standalone Pset addition
    already_fixed = set(selections.keys())
    for gid, pfix in pset_fixes.items():
        if gid in already_fixed:
            continue
        ifc_type = pfix.get("IFCType", "")
        req_pset = pfix.get("PsetName", "")
        if not ifc_type or not req_pset:
            continue

        escaped = re.escape(gid)
        ifc_upper = ifc_type.upper()
        em = re.search(rf"(#\d+)=\s*{ifc_upper}\(\s*'{escaped}'", ifc_text, re.IGNORECASE)
        if not em:
            continue
        elem_ref = em.group(1)

        pset_name = _inject_pset(elem_ref, ifc_type, pset_name_override=req_pset)
        if pset_name:
            pset_fix_log.append((gid, ifc_type, pset_name))

    # Inject new entities at the end
    if new_entities:
        block = "\n".join(new_entities) + "\n"
        ifc_text = re.sub(r"ENDSEC;\s*END-ISO-10303-21;", block + "ENDSEC;\nEND-ISO-10303-21;", ifc_text)

    return ifc_text, fix_log, skip_log, pset_fix_log
