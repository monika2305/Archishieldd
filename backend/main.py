import os
import tempfile
import uuid
import datetime
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import io
import httpx

from core.config import get_settings
from models.schemas import (
    LoginRequest,
    QueryRequest,
    ApplyCorrectionsRequest,
    AutomationCallbackRequest,
    AutomationSummaryRequest
)
from services.ifc_parser import parse_ifc_file, get_pset_value, has_pset, classify_proxy
from services.corrections import build_corrected_ifc_text, get_smart_suggestions, get_suggested_type_single, get_confidence_score, is_valid_reference_proxy
from services.pdf_generator import generate_pdf_report
from services.bcf_generator import generate_bcf_zip
from services.ai_assistant import ask_groq_assistant
from services.supabase_service import upload_file_to_cloud, list_cloud_files, delete_cloud_file, download_cloud_file
from services.audit_log import read_audit_entries, write_audit_entry
from services.autoops import process_autoops_completion, build_autoops_payload

import ifcopenshell

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Decoupled API backend for ArchiShield IFC Analysis.",
    version="1.0.0"
)

# CORS setup - Allow all production origins (Vercel, Render, local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"^https?://.*$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory storage (simulating sessions)
class SessionState:
    def __init__(self):
        self.user_context = {}
        self.logged_in = False
        self.analysis = {}
        self.temp_file_path = "/tmp/temp.ifc"
        self.corrected_ifc_bytes = None
        self.corrected_fix_count = 0
        self.corrected_pset_count = 0
        self.user_class_selections = {}
        self.pset_fixes = {}
        self.current_job_id = None
        self.current_file_id = None
        self.jobs = {}
        self.latest_automation = None
        self.automation_results = {}
        self.n8n_last_dispatch_status = "idle"

state = SessionState()

async def trigger_n8n_webhook(job_id: str, file_id: str, quality_score: float, status: str = "completed"):
    """Dispatches lightweight metadata to the n8n webhook asynchronously."""
    if not settings.N8N_ENABLED or not settings.N8N_WEBHOOK_URL:
        state.n8n_last_dispatch_status = "disabled"
        return
    
    payload = {
        "job_id": job_id,
        "file_id": file_id,
        "status": status,
        "quality_score": quality_score,
        "backend_url": settings.BACKEND_INTERNAL_URL.rstrip("/"),
    }
    headers = {
        "Content-Type": "application/json",
        "X-N8N-Webhook-Secret": settings.N8N_WEBHOOK_SECRET,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(settings.N8N_WEBHOOK_URL, json=payload, headers=headers)
            if resp.status_code < 400:
                state.n8n_last_dispatch_status = "dispatched"
                print(f"[n8n] Successfully dispatched webhook for {job_id} -> {resp.status_code}")
            else:
                state.n8n_last_dispatch_status = f"error_{resp.status_code}"
                print(f"[n8n] Webhook endpoint responded with status {resp.status_code}")
    except Exception as e:
        state.n8n_last_dispatch_status = f"failed: {str(e)}"
        print(f"[n8n] Webhook dispatch error: {e}")

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT, "n8n_enabled": settings.N8N_ENABLED}

@app.post("/api/auth/login")
def login(req: LoginRequest):
    state.user_context = {
        "name": req.name,
        "role": req.role,
        "domain": req.domain,
        "purpose": req.purpose
    }
    state.logged_in = True
    return {"status": "success", "context": state.user_context}

@app.get("/api/auth/session")
def get_session():
    return {
        "logged_in": state.logged_in,
        "context": state.user_context
    }

@app.post("/api/auth/logout")
def logout():
    state.logged_in = False
    state.user_context = {}
    state.analysis = {}
    state.corrected_ifc_bytes = None
    state.user_class_selections = {}
    state.pset_fixes = {}
    if os.path.exists(state.temp_file_path):
        try:
            os.remove(state.temp_file_path)
        except Exception:
            pass
    return {"status": "success"}

@app.post("/api/analyze/upload")
async def upload_ifc(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        content = await file.read()
        
        # Write to disk
        with open(state.temp_file_path, "wb") as f:
            f.write(content)
        
        # Upload to Supabase
        cloud_uploaded = False
        try:
            cloud_path = upload_file_to_cloud(content, file.filename)
            if cloud_path:
                cloud_uploaded = True
        except Exception as ce:
            print(f"[Supabase] Cloud upload skipped or failed: {ce}")

        # Reset corrections state
        state.corrected_ifc_bytes = None
        state.corrected_fix_count = 0
        state.corrected_pset_count = 0
        state.user_class_selections = {}
        state.pset_fixes = {}

        # Parse file with existing IfcOpenShell analysis
        state.analysis = parse_ifc_file(state.temp_file_path)

        # Register job metadata
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        state.current_job_id = job_id
        state.current_file_id = file.filename
        state.jobs[job_id] = {
            "job_id": job_id,
            "file_id": file.filename,
            "status": "completed",
            "quality_score": state.analysis.get("quality_score", 0),
            "created_at": datetime.datetime.now().isoformat(),
            "analysis": state.analysis
        }

        # Trigger n8n webhook asynchronously in background so IFC upload never blocks or fails
        if settings.N8N_ENABLED and settings.N8N_WEBHOOK_URL:
            background_tasks.add_task(
                trigger_n8n_webhook,
                job_id=job_id,
                file_id=file.filename,
                quality_score=state.analysis.get("quality_score", 0),
                status="completed"
            )

        # ArchiShield AutoOps: Write audit log and POST to n8n alert webhook safely
        background_tasks.add_task(
            process_autoops_completion,
            analysis=state.analysis,
            job_id=job_id,
            model_name=file.filename,
            user=state.user_context.get("name") if state.user_context else "ArchiShield User"
        )

        return {
            "status": "success",
            "job_id": job_id,
            "file_id": file.filename,
            "results": state.analysis,
            "cloud_uploaded": cloud_uploaded,
            "n8n_triggered": settings.N8N_ENABLED,
            "autoops_triggered": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload & parse failed: {str(e)}")

@app.get("/api/analyze/results")
def get_results():
    if not state.analysis:
        raise HTTPException(status_code=400, detail="No analysis results found. Please upload a file first.")
    return state.analysis

@app.get("/api/analyze/results/{job_id}")
def get_results_by_job(job_id: str):
    if job_id in state.jobs:
        return state.jobs[job_id]["analysis"]
    if state.current_job_id == job_id and state.analysis:
        return state.analysis
    if state.analysis:
        return state.analysis
    raise HTTPException(status_code=404, detail=f"No analysis found for job_id '{job_id}'")

# 3D BIM Viewer payload generation helper
def resolve_placement(elem):
    x = y = z = 0.0
    try:
        pl = getattr(elem, "ObjectPlacement", None)
        while pl:
            rel = getattr(pl, "RelativePlacement", None)
            if rel:
                loc = getattr(rel, "Location", None)
                if loc:
                    c = loc.Coordinates
                    x += float(c[0]) if len(c) > 0 else 0.0
                    y += float(c[1]) if len(c) > 1 else 0.0
                    z += float(c[2]) if len(c) > 2 else 0.0
            pl = getattr(pl, "PlacementRelTo", None)
    except Exception:
        pass
    return x, y, z

def get_dims(t):
    t = t.lower()
    if "curtainwall" in t: return ("wall",   6.0, 3.5, 0.08)
    if "wall"        in t: return ("wall",   6.0, 3.0, 0.25)
    if "door"        in t: return ("door",   1.0, 2.2, 0.12)
    if "window"      in t: return ("window", 1.4, 1.2, 0.10)
    if "slab"        in t: return ("slab",   8.0, 0.25,8.0)
    if "floor"       in t: return ("slab",   6.0, 0.20,6.0)
    if "roof"        in t: return ("roof",  10.0, 0.45,10.0)
    if "column"      in t: return ("column", 0.4, 3.5, 0.4)
    if "beam"        in t: return ("beam",   5.0, 0.4, 0.3)
    if "stair"       in t: return ("stair",  2.5, 2.8, 1.6)
    if "ramp"        in t: return ("slab",   4.0, 0.2, 3.0)
    if "railing"     in t: return ("beam",   3.0, 1.0, 0.1)
    if "proxy"       in t: return ("proxy",  1.2, 2.0, 1.2)
    return ("proxy", 1.0, 1.5, 1.0)

@app.get("/api/analyze/3d")
def get_3d_viewer_data():
    if not os.path.exists(state.temp_file_path):
        raise HTTPException(status_code=400, detail="No IFC model loaded.")
    
    try:
        model = ifcopenshell.open(state.temp_file_path)
        proxies = model.by_type("IfcBuildingElementProxy")
        proxy_ids = set(p.GlobalId for p in proxies)

        walls_missing_pset = []
        for wall in model.by_type("IfcWall"):
            has_p = any(
                d.is_a("IfcRelDefinesByProperties") and
                getattr(d, "RelatingPropertyDefinition", None) and
                d.RelatingPropertyDefinition.is_a("IfcPropertySet") and
                d.RelatingPropertyDefinition.Name == "Pset_WallCommon"
                for d in getattr(wall, "IsDefinedBy", [])
            )
            if not has_p:
                walls_missing_pset.append(wall)
        missing_pset_ids = set(w.GlobalId for w in walls_missing_pset)

        raw = []
        SKIP = {"IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
                "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject",
                "IfcRelAggregates","IfcZone","IfcSpatialZone"}

        all_products = list(model.by_type("IfcProduct"))
        # Smart cap at 3000
        if len(all_products) > 3000:
            step = len(all_products) // 3000
            products_to_render = all_products[::step][:3000]
        else:
            products_to_render = all_products

        for elem in products_to_render:
            if elem.is_a() in SKIP:
                continue
            gid = elem.GlobalId
            name = getattr(elem, "Name", None) or "Unnamed"
            dims = get_dims(elem.is_a())
            if not dims:
                continue
            shape, w, h, d = dims
            x, y, z = resolve_placement(elem)

            if gid in proxy_ids:
                cls = classify_proxy(name)
                if cls == "valid":
                    issue, label = "valid", "Non-physical/Reference — no IFC class needed"
                elif cls == "invalid":
                    issue, label = "invalid", "Semantic data loss — must be reclassified"
                else:
                    issue, label = "unknown", "Unknown proxy — review manually"
            elif gid in missing_pset_ids:
                issue, label = "missing_pset", "Missing required property set"
            else:
                issue, label = "ok", "No issues detected"

            raw.append({
                "id": gid, "name": name, "type": elem.is_a(),
                "shape": shape, "x": x, "y": y, "z": z,
                "w": w, "h": h, "d": d, "issue": issue, "issue_label": label
            })

        # Scale mm to m if spread is huge
        if raw:
            xs = [r["x"] for r in raw]
            zs = [r["z"] for r in raw]
            spread = max(max(xs)-min(xs), max(zs)-min(zs)) if xs else 0
            if spread > 500:
                for r in raw:
                    r["x"] /= 1000.0; r["y"] /= 1000.0; r["z"] /= 1000.0
                xs = [r["x"] for r in raw]
                zs = [r["z"] for r in raw]
                spread = max(max(xs)-min(xs), max(zs)-min(zs))
            has_spread = spread > 0.5
        else:
            has_spread = False

        # Procedural building layout fallback
        if not has_spread and raw:
            FH = 3.5
            layout = [
                ("slab",   0,    -0.13, 0,    12.0, 0.25, 8.0),
                ("wall",   0,    0,    -4.0,  12.0, FH,   0.25),
                ("wall",   0,    0,     4.0,  12.0, FH,   0.25),
                ("wall",  -6.0,  0,     0,    0.25, FH,   8.0),
                ("wall",   6.0,  0,     0,    0.25, FH,   8.0),
                ("wall",   0,    0,     0,    0.25, FH,   8.0),
                ("column",-5.5,  0,    -3.5,  0.4,  FH,   0.4),
                ("column", 5.5,  0,    -3.5,  0.4,  FH,   0.4),
                ("column",-5.5,  0,     3.5,  0.4,  FH,   0.4),
                ("column", 5.5,  0,     3.5,  0.4,  FH,   0.4),
                ("column", 0,    0,    -3.5,  0.4,  FH,   0.4),
                ("column", 0,    0,     3.5,  0.4,  FH,   0.4),
                ("beam",   0,    FH-0.35,-3.8, 12.0, 0.4,  0.3),
                ("beam",   0,    FH-0.35, 3.8, 12.0, 0.4,  0.3),
                ("beam",  -5.5,  FH-0.35, 0,   0.3,  0.4,  8.0),
                ("beam",   5.5,  FH-0.35, 0,   0.3,  0.4,  8.0),
                ("door",  -2.5,  0,    -4.0,  0.12, 2.2,  1.0),
                ("door",   2.5,  0,    -4.0,  0.12, 2.2,  1.0),
                ("window",-4.5,  1.1,  -4.0,  0.1,  1.2,  1.4),
                ("window", 4.5,  1.1,  -4.0,  0.1,  1.2,  1.4),
                ("window",-4.5,  1.1,   4.0,  0.1,  1.2,  1.4),
                ("window", 4.5,  1.1,   4.0,  0.1,  1.2,  1.4),
                ("window",-4.5,  1.1,  -6.0,  1.4,  1.2,  0.1),
                ("window", 4.5,  1.1,  -6.0,  1.4,  1.2,  0.1),
                ("stair",  7.5,  0,     0,    2.5,  FH,   1.8),
                ("slab",   0,    FH,    0,    12.0, 0.25, 8.0),
                ("wall",   0,    FH+0.25,-4.0, 12.0, FH,   0.25),
                ("wall",   0,    FH+0.25, 4.0, 12.0, FH,   0.25),
                ("wall",  -6.0,  FH+0.25, 0,   0.25, FH,   8.0),
                ("wall",   6.0,  FH+0.25, 0,   0.25, FH,   8.0),
                ("column",-5.5,  FH+0.25,-3.5, 0.4,  FH,   0.4),
                ("column", 5.5,  FH+0.25,-3.5, 0.4,  FH,   0.4),
                ("column",-5.5,  FH+0.25, 3.5, 0.4,  FH,   0.4),
                ("column", 5.5,  FH+0.25, 3.5, 0.4,  FH,   0.4),
                ("window",-4.5,  FH+1.4, -4.0, 0.1,  1.2,  1.4),
                ("window", 4.5,  FH+1.4, -4.0, 0.1,  1.2,  1.4),
                ("window",-4.5,  FH+1.4,  4.0, 0.1,  1.2,  1.4),
                ("window", 4.5,  FH+1.4,  4.0, 0.1,  1.2,  1.4),
                ("beam",   0,    FH*2-0.35,-3.8,12.0, 0.4,  0.3),
                ("beam",   0,    FH*2-0.35, 3.8,12.0, 0.4,  0.3),
                ("slab",   0,    FH*2,  0,    12.5, 0.25, 8.5),
                ("roof",   0,    FH*2+0.25,0, 12.5, 0.6,  8.5),
            ]
            for idx, r in enumerate(raw):
                if idx < len(layout):
                    s,px,py,pz,pw,ph,pd = layout[idx]
                    r["shape"]=s; r["x"]=px; r["y"]=py; r["z"]=pz
                    r["w"]=pw; r["h"]=ph; r["d"]=pd
                else:
                    col=(idx-len(layout))%8; row=(idx-len(layout))//8
                    r["x"]=col*2.0-7; r["y"]=0; r["z"]=5.5+row*2.0

        return {"has_spread": has_spread, "elements": raw}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"3D extraction failed: {str(e)}")

@app.get("/api/analyze/heatmap")
def get_heatmap_data():
    if not os.path.exists(state.temp_file_path):
        raise HTTPException(status_code=400, detail="No IFC model loaded.")
    
    try:
        model = ifcopenshell.open(state.temp_file_path)
        proxies = model.by_type("IfcBuildingElementProxy")
        proxy_ids = set(p.GlobalId for p in proxies)
        proxy_name_map = {p.GlobalId: (p.Name or "") for p in proxies}

        walls_missing_pset = []
        for wall in model.by_type("IfcWall"):
            has_p = any(
                d.is_a("IfcRelDefinesByProperties") and
                d.RelatingPropertyDefinition and
                d.RelatingPropertyDefinition.is_a("IfcPropertySet") and
                d.RelatingPropertyDefinition.Name == "Pset_WallCommon"
                for d in getattr(wall, "IsDefinedBy", [])
            )
            if not has_p:
                walls_missing_pset.append(wall)
        missing_pset_ids = set(w.GlobalId for w in walls_missing_pset)

        heatmap_elements = []
        for elem in model.by_type("IfcProduct"):
            if hasattr(elem, 'ObjectPlacement') and elem.ObjectPlacement:
                pl = elem.ObjectPlacement
                if hasattr(pl, 'RelativePlacement') and pl.RelativePlacement:
                    rel = pl.RelativePlacement
                    if hasattr(rel, 'Location') and rel.Location:
                        c = rel.Location.Coordinates
                        x = float(c[0])
                        z = float(c[1]) if len(c) > 1 else 0.0
                        if abs(x) > 500 or abs(z) > 500:
                            x /= 1000.0; z /= 1000.0
                        gid = elem.GlobalId
                        
                        if gid in proxy_ids:
                            cls = classify_proxy(proxy_name_map.get(gid, ""))
                            issue = cls
                        elif gid in missing_pset_ids:
                            issue = "missing_pset"
                        else:
                            issue = "ok"

                        storey_name = "Unassigned"
                        for rel_st in getattr(elem, "ContainedInStructure", []):
                            if rel_st.is_a("IfcRelContainedInSpatialStructure"):
                                st_elem = rel_st.RelatingStructure
                                if st_elem.is_a("IfcBuildingStorey"):
                                    storey_name = st_elem.Name or "Unnamed Storey"
                                    break

                        heatmap_elements.append({
                            "x": x, "z": z, "issue": issue,
                            "name": elem.Name or "Unnamed",
                            "type": elem.is_a(),
                            "storey": storey_name,
                        })

        # Cap heatmap size
        MAX_HEATMAP = 5000
        if len(heatmap_elements) > MAX_HEATMAP:
            import random
            issue_elems = [e for e in heatmap_elements if e["issue"] != "ok"]
            clean_elems = [e for e in heatmap_elements if e["issue"] == "ok"]
            sample_clean = random.sample(clean_elems, min(len(clean_elems), MAX_HEATMAP - len(issue_elems)))
            heatmap_elements = issue_elems + sample_clean

        all_storeys = sorted(set(e["storey"] for e in heatmap_elements))

        return {"storeys": all_storeys, "elements": heatmap_elements}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Heatmap generation failed: {str(e)}")

@app.get("/api/analyze/corrections")
def get_corrections_list():
    if not state.analysis:
        raise HTTPException(status_code=400, detail="No analysis results found. Please upload a file first.")
    
    try:
        model = ifcopenshell.open(state.temp_file_path)
        schema_supports_fn = lambda c: hasattr(model, "by_type") and hasattr(model, "schema") and _schema_supports_class(model, c)

        corrections = []
        # 1. Proxies
        for item in state.analysis.get("proxy_list", []):
            name = item["Name"]
            gid = item["GlobalId"]
            if is_valid_reference_proxy(name):
                continue
            
            sug = get_suggested_type_single(name)
            conf = get_confidence_score(name, sug) if sug else 0

            if sug and not schema_supports_fn(sug):
                sug = None
                conf = 0

            smart_list = [{"class": s[0], "confidence": s[1], "reason": s[2]} 
                          for s in get_smart_suggestions(name, schema_supports_fn)]

            corrections.append({
                "GlobalId": gid,
                "ElementName": name,
                "CurrentType": "IfcBuildingElementProxy",
                "SuggestedType": sug or "—",
                "Confidence": conf,
                "Issue": "Generic proxy — semantic type lost",
                "Action": f"Reclassify to {sug}" if sug else "Select IFC class manually",
                "category": "proxy",
                "smart_suggestions": smart_list
            })

        # 2. Psets
        for item in state.analysis.get("missing_pset_list", []):
            name = item.get("Element Name") or "Unnamed"
            gid = item.get("GlobalId", "")
            ifc_type = item.get("IFC Type", "IfcWall")
            req_pset = item.get("Required Pset", "Pset_WallCommon")
            corrections.append({
                "GlobalId": gid,
                "ElementName": name,
                "CurrentType": ifc_type,
                "SuggestedType": ifc_type,
                "Confidence": 100,
                "Issue": f"Missing {req_pset}",
                "Action": f"Add {req_pset}",
                "category": "missing_pset",
                "req_pset": req_pset
            })

        # 3. Quantities
        for item in state.analysis.get("qty_loss_list", []):
            corrections.append({
                "GlobalId": item.get("GlobalId",""),
                "ElementName": item.get("Name","Unnamed"),
                "CurrentType": item.get("IFC Type",""),
                "SuggestedType": item.get("IFC Type",""),
                "Confidence": 100,
                "Issue": item.get("Issue",""),
                "Action": "Add Base Quantities",
                "category": "quantity_loss",
            })

        # 4. Relationships
        for item in state.analysis.get("rel_loss_list", []):
            corrections.append({
                "GlobalId": item.get("GlobalId",""),
                "ElementName": item.get("Name","Unnamed"),
                "CurrentType": item.get("IFC Type",""),
                "SuggestedType": item.get("IFC Type",""),
                "Confidence": 100,
                "Issue": item.get("Issue",""),
                "Action": "Re-establish containment/host",
                "category": "relationship_loss",
            })

        return corrections
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed loading corrections: {str(e)}")

def _schema_supports_class(model, class_name: str) -> bool:
    try:
        model.by_type(class_name)
        return True
    except Exception:
        return False

@app.post("/api/analyze/apply-corrections")
def apply_corrections(req: ApplyCorrectionsRequest):
    if not os.path.exists(state.temp_file_path):
        raise HTTPException(status_code=400, detail="No IFC file loaded.")

    try:
        model = ifcopenshell.open(state.temp_file_path)
        schema_supports_fn = lambda c: _schema_supports_class(model, c)

        selections = req.selections
        pset_fixes = req.pset_fixes or {}

        corrected_text, fix_log, skip_log, pset_fix_log = build_corrected_ifc_text(
            state.temp_file_path, selections, pset_fixes, schema_supports_fn
        )

        state.corrected_ifc_bytes = corrected_text.encode("utf-8")
        state.corrected_fix_count = len(fix_log)
        state.corrected_pset_count = len(pset_fix_log)

        # Build a preview score by parsing the corrected model text
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ifc", encoding="utf-8", delete=False) as tmp:
            tmp.write(corrected_text)
            tmp_path = tmp.name

        corrected_analysis = parse_ifc_file(tmp_path)
        os.unlink(tmp_path)

        return {
            "status": "success",
            "fix_count": len(fix_log),
            "pset_fix_count": len(pset_fix_log),
            "original_score": state.analysis.get("quality_score", 0),
            "improved_score": corrected_analysis.get("quality_score", 0),
            "score_breakdown": corrected_analysis.get("score_breakdown", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apply corrections failed: {str(e)}")

@app.get("/api/analyze/download-corrected")
def download_corrected_ifc():
    if not state.corrected_ifc_bytes:
        raise HTTPException(status_code=400, detail="No corrections have been applied yet.")
    
    return StreamingResponse(
        io.BytesIO(state.corrected_ifc_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=corrected_model.ifc"}
    )

@app.get("/api/analyze/download-sample")
def download_sample_ifc():
    sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_model.ifc")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample model file not found on server.")
    
    return FileResponse(
        sample_path,
        media_type="application/octet-stream",
        filename="sample_model.ifc"
    )

@app.get("/api/analyze/pdf-report")
def download_pdf_report():
    if not state.analysis:
        raise HTTPException(status_code=400, detail="No analysis loaded.")
    
    tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_pdf.close()
    
    try:
        generate_pdf_report(state.analysis, state.user_context, tmp_pdf.name)
        
        # Read file bytes in memory before returning
        with open(tmp_pdf.name, "rb") as f:
            pdf_bytes = f.read()
        os.unlink(tmp_pdf.name)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=IFC_Analysis_Report.pdf"}
        )
    except Exception as e:
        if os.path.exists(tmp_pdf.name):
            os.unlink(tmp_pdf.name)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@app.post("/api/analyze/bcf")
def download_bcf_report(issues: List[dict]):
    try:
        bcf_bytes = generate_bcf_zip(issues)
        return StreamingResponse(
            io.BytesIO(bcf_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=issues.bcfzip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BCF generation failed: {str(e)}")

@app.get("/api/analyze/bcf")
def download_bcf_report_get():
    """
    GET handler for downloading BCF zip issue report directly from browser or email links.
    Extracts current failures from state.analysis and returns a zip stream.
    """
    if not state.analysis:
        raise HTTPException(status_code=400, detail="No IFC model loaded to generate BCF report.")
    
    rule_checks = state.analysis.get("rule_checks", [])
    bcf_issues = []
    for r in rule_checks:
        if isinstance(r, dict):
            for gid in r.get("fails", []):
                bcf_issues.append({
                    "GlobalId": gid,
                    "Rule": r.get("name", "Compliance Violation"),
                    "Severity": r.get("severity", "Medium"),
                    "Category": r.get("category", "General"),
                    "Message": f"Violation of {r.get('name', 'rule')}"
                })
    
    try:
        bcf_bytes = generate_bcf_zip(bcf_issues[:500])
        return StreamingResponse(
            io.BytesIO(bcf_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=issues.bcfzip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BCF generation failed: {str(e)}")

# Version comparison helpers
SKIP_TYPES_COMP = {"IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation","IfcGrid","IfcRelAggregates","IfcZone","IfcSpatialZone"}

def get_project_meta(model):
    projects = model.by_type("IfcProject")
    if projects:
        p = projects[0]
        return (p.Name or "").strip().lower(), (p.GlobalId or "").strip()
    return "", ""

def _valid_gid(gid):
    gid = (gid or "").strip()
    return bool(gid and gid != "$")

def _norm_text(value):
    return (str(value or "").strip().lower())

def get_element_guids(model):
    guids = set()
    for elem in model.by_type("IfcProduct"):
        if elem.is_a() not in SKIP_TYPES_COMP:
            gid = (getattr(elem, "GlobalId", "") or "").strip()
            if _valid_gid(gid):
                guids.add(gid)
    for elem in model.by_type("IfcElement"):
        if elem.is_a() not in SKIP_TYPES_COMP:
            gid = (getattr(elem, "GlobalId", "") or "").strip()
            if _valid_gid(gid):
                guids.add(gid)
    for elem in model.by_type("IfcSpatialStructureElement"):
        if elem.is_a() not in SKIP_TYPES_COMP:
            gid = (getattr(elem, "GlobalId", "") or "").strip()
            if _valid_gid(gid):
                guids.add(gid)
    for elem in model.by_type("IfcRelationship"):
        if elem.is_a() not in SKIP_TYPES_COMP and hasattr(elem, "GlobalId"):
            gid = (getattr(elem, "GlobalId", "") or "").strip()
            if _valid_gid(gid):
                guids.add(gid)
    return guids

def check_same_project(model_a, model_b):
    proj_name_a, proj_guid_a = get_project_meta(model_a)
    proj_name_b, proj_guid_b = get_project_meta(model_b)
    if proj_guid_a and proj_guid_b and proj_guid_a == proj_guid_b:
        return True, "Matched by IfcProject GlobalId", 100.0
    if proj_name_a and proj_name_b and proj_name_a == proj_name_b:
        return True, f"Matched by project name: '{proj_name_a}'", 100.0
    guids_a = get_element_guids(model_a)
    guids_b = get_element_guids(model_b)
    if guids_a and guids_b:
        overlap = len(guids_a & guids_b)
        pct = overlap / min(len(guids_a), len(guids_b)) * 100
        if pct >= 20:
            return True, f"Matched by element overlap ({pct:.1f}% shared GlobalIds)", pct
        reason = f"Only {pct:.1f}% of element GlobalIds overlap. Project names differ: '{proj_name_a}' vs '{proj_name_b}'."
        return False, reason, pct
    return True, "Could not determine project match (no element data)", 0.0

def parse_comparison_model(model):
    elements = {}
    def _parse_elem(elem):
        etype = elem.is_a()
        if etype in SKIP_TYPES_COMP:
            return
        gid = (getattr(elem, "GlobalId", "") or "").strip()
        if _valid_gid(gid) and gid in elements:
            return
        name = elem.Name or "Unnamed"
        psets = {}
        for d in getattr(elem, "IsDefinedBy", []):
            if d.is_a("IfcRelDefinesByProperties"):
                ps = d.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet"):
                    props = {}
                    for p in getattr(ps, "HasProperties", []):
                        val = getattr(getattr(p, "NominalValue", None), "wrappedValue", None)
                        props[p.Name] = str(val) if val is not None else ""
                    psets[ps.Name] = props
        material = None
        for d in getattr(elem, "HasAssociations", []):
            if d.is_a("IfcRelAssociatesMaterial"):
                mat = d.RelatingMaterial
                if mat:
                    material = getattr(mat, "Name", str(mat))
        storey = None
        storey_key = None
        for d in getattr(elem, "ContainedInStructure", []):
            if d.is_a("IfcRelContainedInSpatialStructure"):
                rel_str = d.RelatingStructure
                if rel_str:
                    storey = rel_str.Name or rel_str.GlobalId
                    storey_key = (getattr(rel_str, "GlobalId", "") or "").strip() or _norm_text(rel_str.Name)
        key = gid if _valid_gid(gid) else f"NO_GUID::{etype}::{_norm_text(name)}::{len(elements)}"
        pset_names = sorted(psets.keys())
        match_key = "|".join([
            _norm_text(etype),
            _norm_text(name),
            _norm_text(material),
            _norm_text(storey_key),
            ";".join(_norm_text(p) for p in pset_names),
        ])
        elements[key] = {
            "GlobalId": gid if _valid_gid(gid) else "—",
            "Name": name,
            "Type": etype,
            "Psets": psets,
            "Material": material,
            "Storey": storey,
            "StoreyKey": storey_key,
            "_MatchKey": match_key,
        }

    for elem in model.by_type("IfcProduct"):
        _parse_elem(elem)
    for elem in model.by_type("IfcElement"):
        _parse_elem(elem)
    for elem in model.by_type("IfcSpatialStructureElement"):
        _parse_elem(elem)
    return elements

def diff_models(a, b):
    ids_a, ids_b = set(a), set(b)
    exact_common = ids_a & ids_b
    unmatched_removed = set(ids_a - ids_b)
    unmatched_added = set(ids_b - ids_a)

    added_by_sig = {}
    for bid in unmatched_added:
        sig = b[bid].get("_MatchKey")
        if sig:
            added_by_sig.setdefault(sig, []).append(bid)

    fallback_pairs = []
    for aid in list(unmatched_removed):
        sig = a[aid].get("_MatchKey")
        candidates = added_by_sig.get(sig, [])
        if candidates:
            bid = candidates.pop()
            fallback_pairs.append((aid, bid))
            unmatched_removed.discard(aid)
            unmatched_added.discard(bid)

    common_pairs = [(gid, gid) for gid in exact_common] + fallback_pairs
    changed = []
    unchanged = 0
    for gid_a, gid_b in common_pairs:
        ea, eb = a[gid_a], b[gid_b]
        diffs = []
        if ea["Type"] != eb["Type"]:
            diffs.append({"Field": "IFC Type", "Before": ea["Type"], "After": eb["Type"]})
        if ea["Name"] != eb["Name"]:
            diffs.append({"Field": "Name", "Before": ea["Name"], "After": eb["Name"]})
        if ea["Material"] != eb["Material"]:
            diffs.append({"Field": "Material", "Before": ea["Material"] or "—", "After": eb["Material"] or "—"})
        if ea.get("StoreyKey") != eb.get("StoreyKey"):
            diffs.append({"Field": "Storey", "Before": ea.get("Storey") or "—", "After": eb.get("Storey") or "—"})
        if ea.get("GlobalId") != eb.get("GlobalId"):
            diffs.append({"Field": "GlobalId", "Before": ea.get("GlobalId") or "—", "After": eb.get("GlobalId") or "—"})
        all_psets = set(ea["Psets"]) | set(eb["Psets"])
        for pset in all_psets:
            if pset not in ea["Psets"]:
                diffs.append({"Field": f"Pset Added: {pset}", "Before": "—", "After": "Present"})
            elif pset not in eb["Psets"]:
                diffs.append({"Field": f"Pset Removed: {pset}", "Before": "Present", "After": "—"})
            else:
                for prop in set(ea["Psets"][pset]) | set(eb["Psets"][pset]):
                    va = ea["Psets"][pset].get(prop, "—")
                    vb = eb["Psets"][pset].get(prop, "—")
                    if va != vb:
                        diffs.append({"Field": f"{pset}.{prop}", "Before": va, "After": vb})
        if diffs:
            changed.append({
                "GlobalId": eb.get("GlobalId") if eb.get("GlobalId") != "—" else ea.get("GlobalId"),
                "Name": ea["Name"],
                "Type": ea["Type"],
                "Changes": diffs,
            })
        else:
            unchanged += 1

    return {
        "added": [{"GlobalId": b[gid].get("GlobalId", "—"), "Name": b[gid]["Name"], "Type": b[gid]["Type"]} for gid in unmatched_added],
        "removed": [{"GlobalId": a[gid].get("GlobalId", "—"), "Name": a[gid]["Name"], "Type": a[gid]["Type"]} for gid in unmatched_removed],
        "changed": changed,
        "unchanged": unchanged,
        "total_a": len(a),
        "total_b": len(b),
    }

@app.post("/api/analyze/compare")
async def compare_versions(file_a: Optional[UploadFile] = File(None), file_b: UploadFile = File(...)):
    # Save file_b to temp
    tmp_b = tempfile.NamedTemporaryFile(suffix=".ifc", delete=False)
    tmp_b.write(await file_b.read())
    tmp_b.close()

    try:
        if file_a is not None:
            tmp_a = tempfile.NamedTemporaryFile(suffix=".ifc", delete=False)
            tmp_a.write(await file_a.read())
            tmp_a.close()
            path_a = tmp_a.name
        else:
            if not os.path.exists(state.temp_file_path):
                raise HTTPException(status_code=400, detail="Primary model not uploaded. Provide file_a or upload on Home first.")
            path_a = state.temp_file_path
            tmp_a = None

        model_a = ifcopenshell.open(path_a)
        model_b = ifcopenshell.open(tmp_b.name)

        is_same, reason, overlap_pct = check_same_project(model_a, model_b)
        elements_a = parse_comparison_model(model_a)
        elements_b = parse_comparison_model(model_b)

        # Cleanup tmp files
        os.unlink(tmp_b.name)
        if tmp_a is not None:
            os.unlink(tmp_a.name)

        diff = diff_models(elements_a, elements_b)
        diff["project_match"] = {
            "is_same": is_same,
            "reason": reason,
            "overlap_pct": overlap_pct
        }
        return diff
    except Exception as e:
        if os.path.exists(tmp_b.name):
            os.unlink(tmp_b.name)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")

@app.post("/api/assistant/query")
def query_assistant(req: QueryRequest):
    if not state.analysis:
        raise HTTPException(status_code=400, detail="No IFC file loaded. Please upload a file first.")
    
    # Trim details for Groq token constraints
    storeys_subset = []
    for sname, sdata in state.analysis.get("storey_data", {}).items():
        storeys_subset.append({
            "name": sname,
            "total_elements": sdata["total"],
            "proxy_elements": sdata["proxies"]
        })

    # Prepare compact context (cap list lengths)
    compact_context = {
        "total_elements": state.analysis.get("total_elements", 0),
        "proxy_elements": state.analysis.get("proxy_elements", 0),
        "proxy_pct": state.analysis.get("proxy_pct", 0),
        "semantic_elements": state.analysis.get("semantic_elements", 0),
        "quality_score": state.analysis.get("quality_score", 0),
        "severity": state.analysis.get("severity", "LOW"),
        "data_loss_breakdown": {
            "L1_semantic_loss_pct": state.analysis.get("type_loss_pct", 0),
            "L2_property_loss_pct": state.analysis.get("prop_loss_pct", 0),
            "L3_quantity_loss_pct": state.analysis.get("qty_loss_pct", 0),
            "L4_relationship_loss_pct": state.analysis.get("rel_loss_pct", 0),
            "L5_geometry_loss_pct": state.analysis.get("geo_loss_pct", 0),
        },
        "missing_pset_count": state.analysis.get("missing_pset_count", 0),
        "storeys": storeys_subset[:20],
        "sample_elements": state.analysis.get("proxy_list", [])[:15] + state.analysis.get("missing_pset_list", [])[:15],
    }

    ans = ask_groq_assistant(req.question, compact_context, get_settings().GROQ_API_KEY)
    return {"question": req.question, "answer": ans}

from fastapi.responses import HTMLResponse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

def _find_file_path(filename: str, relative_subpath: str = "legacy_pages") -> Optional[Path]:
    candidates = [
        BASE_DIR / relative_subpath / filename,
        BASE_DIR / filename,
        ROOT_DIR / relative_subpath / filename,
        ROOT_DIR / filename,
        Path(r"c:\Users\Dell\OneDrive\Desktop\BIM6") / relative_subpath / filename,
        Path(r"c:\Users\Dell\OneDrive\Desktop\BIM6") / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

@app.get("/api/visualize/3d", response_class=HTMLResponse)
def get_3d_visualizer():
    target_path = _find_file_path("3_🧊_3D_BIM_Viewer.py", "legacy_pages")
    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail="3D viewer template file not found.")
    
    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_tag = 'HTML = r"""'
    end_tag = '"""'
    start_idx = content.find(start_tag)
    if start_idx == -1:
        start_tag = 'HTML = """'
        start_idx = content.find(start_tag)
    
    if start_idx == -1:
        raise HTTPException(status_code=500, detail="HTML block not found in template.")

    start_idx += len(start_tag)
    end_idx = content.find(end_tag, start_idx)
    html_template = content[start_idx:end_idx]

    # Replace JSON placeholder
    payload = get_3d_viewer_data()
    elements_json = json.dumps(payload["elements"])
    html_content = html_template.replace("ELEMENTS_JSON_PLACEHOLDER", elements_json)

    return HTMLResponse(content=html_content)

@app.get("/api/visualize/heatmap", response_class=HTMLResponse)
def get_heatmap_visualizer():
    target_path = _find_file_path("4_🔥_Issue_Heatmap.py", "legacy_pages")
    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail="Heatmap template file not found.")
    
    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_tag = 'heatmap_html = f"""'
    end_tag = '"""'
    start_idx = content.find(start_tag)
    if start_idx == -1:
        start_tag = 'heatmap_html = """'
        start_idx = content.find(start_tag)
    
    if start_idx == -1:
        raise HTTPException(status_code=500, detail="HTML block not found in heatmap template.")

    start_idx += len(start_tag)
    end_idx = content.find(end_tag, start_idx)
    html_template = content[start_idx:end_idx]

    payload = get_heatmap_data()
    html_content = html_template.replace("{heatmap_json}", json.dumps(payload["elements"]))
    html_content = html_content.replace("{storeys_json}", json.dumps(payload["storeys"]))
    html_content = html_content.replace("{{", "{").replace("}}", "}")

    return HTMLResponse(content=html_content)

from pydantic import BaseModel
class RuleValidationRequest(BaseModel):
    selected_builtin_rule_ids: List[str]
    custom_rules: List[Dict[str, Any]]

from services.rule_validator import run_compliance_validation
from fpdf import FPDF

@app.post("/api/rules/validate")
def validate_rules(req: RuleValidationRequest):
    if not os.path.exists(state.temp_file_path):
        raise HTTPException(status_code=400, detail="No IFC file loaded.")
    
    res = run_compliance_validation(state.temp_file_path, req.selected_builtin_rule_ids, req.custom_rules)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res

@app.post("/api/rules/pdf-report")
def download_rules_pdf_report(req: RuleValidationRequest):
    if not os.path.exists(state.temp_file_path):
        raise HTTPException(status_code=400, detail="No IFC file loaded.")
        
    res = run_compliance_validation(state.temp_file_path, req.selected_builtin_rule_ids, req.custom_rules)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
        
    results = res["results"]
    pass_count = res["pass_count"]
    fail_count = res["fail_count"]
    total_checks = res["total_checks"]
    pass_pct = round(pass_count / total_checks * 100, 1) if total_checks else 0

    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(30, 80, 140)
    pdf.cell(0, 12, "IFC Rule Validation Report", ln=True, align="C")
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
    pdf.ln(6)
    
    # Summary box
    pdf.set_fill_color(240, 245, 255)
    pdf.set_draw_color(100, 150, 220)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(30, 80, 140)
    pdf.cell(0, 8, "Validation Summary", ln=True, fill=True)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(40, 40, 40)
    
    summary_rows = [
        ("Total Checks Run", str(total_checks)),
        ("Checks Passed", f"{pass_count} ({pass_pct}%)"),
        ("Checks Failed", str(fail_count)),
        ("Health Score", f"{pass_pct:.0f}%"),
        ("Critical Failures", str(sum(1 for r in results if r["Severity"] == "Critical"))),
        ("High Failures", str(sum(1 for r in results if r["Severity"] == "High"))),
    ]
    for label, value in summary_rows:
        pdf.cell(80, 7, label, border="B")
        pdf.cell(0, 7, value, ln=True, border="B")
    pdf.ln(8)
    
    # Failures table
    if results:
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(30, 80, 140)
        pdf.cell(0, 8, "Failure Details", ln=True)
        pdf.ln(2)
        
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(220, 230, 245)
        pdf.set_text_color(20, 20, 20)
        cols = [("ID", 12), ("Sev", 16), ("Category", 28), ("Rule", 50), ("Element", 35), ("Message", 57)]
        for h, w in cols:
            pdf.cell(w, 6, h, border=1, fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", "", 7)
        SEV_RGB = {
            "Critical": (218, 54, 51),
            "High": (210, 153, 34),
            "Medium": (31, 111, 235),
            "Low": (35, 134, 54)
        }
        
        def safe_str(val):
            return str(val).encode("latin-1", errors="replace").decode("latin-1")
            
        for i, r in enumerate(results[:2000]):
            fill = i % 2 == 0
            pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
            sr, sg, sb = SEV_RGB.get(r["Severity"], (60, 60, 60))
            pdf.set_text_color(sr, sg, sb)
            pdf.cell(12, 5, safe_str(r["Rule ID"]), border="B", fill=fill)
            pdf.cell(16, 5, safe_str(r["Severity"]), border="B", fill=fill)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(28, 5, safe_str(r["Category"][:18]), border="B", fill=fill)
            pdf.cell(50, 5, safe_str(r["Rule"][:30]), border="B", fill=fill)
            pdf.cell(35, 5, safe_str((r["Element"] or "")[:20]), border="B", fill=fill)
            pdf.cell(57, 5, safe_str((r["Message"] or "")[:38]), border="B", fill=fill, ln=True)
            
        if len(results) > 2000:
            pdf.set_font("Arial", "I", 8)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 6, f"... {len(results) - 2000} more failures not shown.", ln=True)
            
    pdf_bytes = bytes(pdf.output())
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=IFC_Validation_Report.pdf"}
    )

@app.get("/api/library/files")
def get_library_files():
    files = list_cloud_files()
    total_size = sum(f.get("metadata", {}).get("size", 0) for f in files)
    return {
        "status": "success",
        "files": files,
        "total_files": len(files),
        "total_size": total_size,
        "bucket": "innovescence-ifc-files"
    }

@app.get("/api/library/download/{filename:path}")
def download_library_file_endpoint(filename: str):
    content = download_cloud_file(filename)
    if not content:
        raise HTTPException(status_code=404, detail="File not found in cloud storage.")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/library/upload")
async def upload_library_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        path = upload_file_to_cloud(content, file.filename)
        return {"status": "success", "filename": file.filename, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloud upload failed: {str(e)}")

@app.delete("/api/library/files/{filename:path}")
def delete_library_file(filename: str):
    success = delete_cloud_file(filename)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete file from cloud storage")
    return {"status": "success"}

@app.post("/api/library/load")
async def load_library_model(req: Dict[str, str]):
    model_name = req.get("model_name", "")
    filename = req.get("filename", "")
    target_name = filename or model_name
    try:
        if target_name:
            content = download_cloud_file(target_name)
            if not content:
                raise HTTPException(status_code=400, detail="Could not download file from cloud bucket.")
            with open(state.temp_file_path, "wb") as f:
                f.write(content)
        else:
            sample_path = _find_file_path("sample_model.ifc", "")
            if not sample_path or not sample_path.exists():
                raise HTTPException(status_code=400, detail="Sample project file not found on server workspace.")
            import shutil
            shutil.copy(str(sample_path), state.temp_file_path)
            
        state.analysis = parse_ifc_file(state.temp_file_path)
        state.corrected_ifc_bytes = None
        state.corrected_fix_count = 0
        state.corrected_pset_count = 0
        return {
            "status": "success",
            "message": f"Successfully loaded project model: {filename or model_name}",
            "results": state.analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed loading library model: {str(e)}")

# ==========================================
# n8n Automation Layer Endpoints
# ==========================================

@app.post("/api/automation/ai-summary")
def generate_automation_ai_summary(req: AutomationSummaryRequest):
    """
    Generates an executive BIM audit summary using the existing Groq AI model.
    Called by n8n during workflow execution without exposing the Groq API key to n8n or frontend.
    """
    analysis_data = state.analysis
    if req.job_id and req.job_id in state.jobs:
        analysis_data = state.jobs[req.job_id]["analysis"]
    
    if not analysis_data:
        raise HTTPException(status_code=400, detail="No analysis data loaded to generate summary.")

    storeys_subset = []
    for sname, sdata in analysis_data.get("storey_data", {}).items():
        storeys_subset.append({
            "name": sname,
            "total_elements": sdata.get("total", 0),
            "proxies": sdata.get("proxies", 0),
            "score": sdata.get("score", 0)
        })

    compact_context = {
        "total_elements": analysis_data.get("total_elements", 0),
        "proxy_elements": analysis_data.get("proxy_elements", 0),
        "proxy_pct": analysis_data.get("proxy_pct", 0),
        "semantic_elements": analysis_data.get("semantic_elements", 0),
        "quality_score": analysis_data.get("quality_score", 0),
        "severity": analysis_data.get("severity", "LOW"),
        "data_loss_breakdown": {
            "L1_semantic_loss_pct": analysis_data.get("type_loss_pct", 0),
            "L2_property_loss_pct": analysis_data.get("prop_loss_pct", 0),
            "L3_quantity_loss_pct": analysis_data.get("qty_loss_pct", 0),
            "L4_relationship_loss_pct": analysis_data.get("rel_loss_pct", 0),
            "L5_geometry_loss_pct": analysis_data.get("geo_loss_pct", 0),
        },
        "missing_pset_count": analysis_data.get("missing_pset_count", 0),
        "nbc_overall_score": analysis_data.get("nbc_overall_score", 0),
        "rule_fails_count": sum(len(r.get("fails", [])) for r in analysis_data.get("rule_checks", [])),
        "storeys": storeys_subset[:15],
    }

    prompt = (
        req.custom_instructions or
        "Provide an executive BIM quality and compliance audit summary for this IFC model. "
        "Highlight the primary reasons for quality loss, critical NBC non-compliance risks, "
        "and the most urgent 3 actions recommended for the BIM coordination team."
    )

    summary_text = ask_groq_assistant(prompt, compact_context, get_settings().GROQ_API_KEY)
    
    # If Groq returns an error, provide a high-fidelity executive briefing using actual model metrics
    if summary_text.startswith("⚠️ Groq API error") or summary_text.startswith("⚠️ No GROQ_API_KEY"):
        q_score = analysis_data.get("quality_score", 0)
        sev = analysis_data.get("severity", "LOW")
        tot = analysis_data.get("total_elements", 0)
        prx = analysis_data.get("proxy_elements", 0)
        prx_pct = analysis_data.get("proxy_pct", 0)
        nbc = analysis_data.get("nbc_overall_score", 0)
        pset_m = analysis_data.get("missing_pset_count", 0)
        summary_text = (
            f"Executive BIM Quality & Compliance Briefing:\n\n"
            f"• Model Health: Overall Quality Score of {q_score}/100 with {sev} severity risk tier.\n"
            f"• Entity Integrity: {tot} total elements scanned, with {prx} unclassified proxies ({prx_pct:.1f}%).\n"
            f"• NBC Compliance: Overall standard compliance rating of {nbc}% across fire & structural safety checks.\n"
            f"• Priority Actions: Remediate {pset_m} missing property set definitions and classify generic building proxies "
            f"prior to final architectural coordination and BCF issue dispatch."
        )

    return {
        "job_id": req.job_id or state.current_job_id,
        "summary": summary_text,
        "quality_score": analysis_data.get("quality_score", 0),
        "severity": analysis_data.get("severity", "LOW")
    }

@app.get("/api/automation/ping-webhook")
async def ping_n8n_webhook():
    """Checks if the configured n8n webhook URL is reachable."""
    if not settings.N8N_ENABLED or not settings.N8N_WEBHOOK_URL:
        return {"connected": False, "reason": "n8n is disabled or URL not set", "webhook_url": settings.N8N_WEBHOOK_URL}
    
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(
                settings.N8N_WEBHOOK_URL,
                json={"ping": True, "job_id": "ping_check"},
                headers={"X-N8N-Webhook-Secret": settings.N8N_WEBHOOK_SECRET}
            )
            # 200/201/204 or 404 (webhook registered in n8n but waiting for test or active)
            is_connected = resp.status_code < 500
            reason = None
            if resp.status_code == 404:
                reason = "Webhook URL reached but n8n responded 404. Please ensure the workflow is toggled to Active in n8n Cloud."
            elif resp.status_code >= 400:
                reason = f"n8n responded with HTTP {resp.status_code}"
            return {
                "connected": is_connected and resp.status_code < 400,
                "status_code": resp.status_code,
                "webhook_url": settings.N8N_WEBHOOK_URL,
                "reason": reason
            }
    except Exception as e:
        return {"connected": False, "reason": str(e), "webhook_url": settings.N8N_WEBHOOK_URL}

@app.post("/api/automation/callback")
def automation_callback(
    payload: AutomationCallbackRequest,
    x_n8n_webhook_secret: Optional[str] = Header(None, alias="X-N8N-Webhook-Secret")
):
    """
    Receives automated orchestration output from n8n.
    Secured by X-N8N-Webhook-Secret header.
    Stores the result in server state and uploads a persistent artifact to Supabase storage.
    """
    if settings.N8N_WEBHOOK_SECRET and x_n8n_webhook_secret:
        if x_n8n_webhook_secret != settings.N8N_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid n8n webhook secret.")

    data = payload.dict()
    data["received_at"] = datetime.datetime.now().isoformat()
    
    state.latest_automation = data
    state.automation_results[payload.job_id] = data
    state.n8n_last_dispatch_status = "completed"

    # Upload automation summary artifact to Supabase storage
    cloud_saved = False
    try:
        summary_json_bytes = json.dumps(data, indent=2).encode("utf-8")
        cloud_filename = f"automation_{payload.job_id}.json"
        upload_file_to_cloud(summary_json_bytes, cloud_filename)
        cloud_saved = True
    except Exception as ce:
        print(f"[Supabase] Automation summary cloud upload skipped: {ce}")

    data["cloud_saved"] = cloud_saved
    return {"status": "success", "job_id": payload.job_id, "cloud_saved": cloud_saved}

@app.get("/api/automation/status")
def get_automation_status():
    """
    Provides real-time automation and workflow status for the React dashboard.
    """
    curr_settings = get_settings()
    rule_fails = sum(len(r.get("fails", [])) for r in state.analysis.get("rule_checks", [])) if state.analysis else 0
    return {
        "n8n_enabled": curr_settings.N8N_ENABLED,
        "n8n_webhook_configured": bool(curr_settings.N8N_WEBHOOK_URL),
        "n8n_webhook_url": "Configured (Cloud Webhook Active)" if curr_settings.N8N_WEBHOOK_URL else "Not configured",
        "dispatch_status": state.n8n_last_dispatch_status,
        "current_job_id": state.current_job_id,
        "current_file_id": state.current_file_id,
        "latest_automation": state.latest_automation,
        "quality_score": state.analysis.get("quality_score") if state.analysis else None,
        "severity": state.analysis.get("severity") if state.analysis else None,
        "total_elements": state.analysis.get("total_elements", 0) if state.analysis else 0,
        "critical_issues_count": rule_fails,
        "bcf_ready": bool(state.analysis.get("rule_checks") or state.analysis.get("proxy_list")),
        "pdf_ready": bool(state.analysis)
    }

@app.post("/api/automation/trigger")
async def trigger_automation_manually():
    """
    Allows manual triggering of the n8n automation workflow from the React dashboard.
    """
    curr_settings = get_settings()
    if not state.analysis:
        raise HTTPException(status_code=400, detail="No IFC analysis available to trigger automation.")

    job_id = state.current_job_id or f"job_{uuid.uuid4().hex[:8]}"
    file_id = state.current_file_id or "model.ifc"
    
    state.current_job_id = job_id
    if job_id not in state.jobs:
        state.jobs[job_id] = {
            "job_id": job_id,
            "file_id": file_id,
            "status": "completed",
            "quality_score": state.analysis.get("quality_score", 0),
            "created_at": datetime.datetime.now().isoformat(),
            "analysis": state.analysis
        }

    await trigger_n8n_webhook(
        job_id=job_id,
        file_id=file_id,
        quality_score=state.analysis.get("quality_score", 0),
        status="completed"
    )

    return {
        "status": "triggered",
        "job_id": job_id,
        "dispatch_status": state.n8n_last_dispatch_status,
        "n8n_configured": bool(curr_settings.N8N_WEBHOOK_URL)
    }

# =========================================================
# ArchiShield AutoOps API Routes
# =========================================================

@app.get("/api/autoops/status")
def get_autoops_status():
    """
    Returns ArchiShield AutoOps operational status and configuration.
    Never exposes sensitive webhook secrets or full URLs.
    """
    curr_settings = get_settings()
    webhook_url = getattr(curr_settings, "N8N_WEBHOOK_URL", "") or ""
    audit_path = getattr(curr_settings, "AUDIT_LOG_PATH", "data/autoops_audit.jsonl")
    return {
        "enabled": bool(webhook_url or os.path.exists(os.path.dirname(audit_path) or ".")),
        "n8n_configured": bool(webhook_url),
        "groq_configured": bool(getattr(curr_settings, "GROQ_API_KEY", "")),
        "audit_log_enabled": True,
        "nbc_compliance_threshold": getattr(curr_settings, "NBC_COMPLIANCE_THRESHOLD", 80.0),
        "audit_log_path": audit_path,
        "public_base_url": getattr(curr_settings, "PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    }

@app.get("/api/autoops/audit-log")
def get_autoops_audit_log(limit: int = 50):
    """
    Returns recent AutoOps audit events from the append-only JSON Lines audit file.
    Safely handles missing, empty, or malformed logs without throwing exceptions.
    """
    entries = read_audit_entries(limit=limit)
    return {
        "count": len(entries),
        "audit_log_path": getattr(settings, "AUDIT_LOG_PATH", "data/autoops_audit.jsonl"),
        "entries": entries
    }

@app.get("/api/autoops/lifecycle")
def get_autoops_lifecycle():
    """
    Returns the step-by-step pipeline lifecycle sequence for ArchiShield AutoOps.
    """
    return {
        "steps": [
            "IFC Upload",
            "Deterministic BIM Analysis",
            "NBC Compliance Evaluation",
            "AutoOps Audit Log",
            "n8n Automation",
            "Compliance Alert"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    # Get port from env or setting
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
