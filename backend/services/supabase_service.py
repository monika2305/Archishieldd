import datetime
import json
import os
import uuid
from typing import List, Dict, Optional
from supabase import create_client, Client
from core.config import get_settings

settings = get_settings()

SUPABASE_URL = getattr(settings, "SUPABASE_URL", None) or os.getenv("SUPABASE_URL", "https://ufttkgyvhmwvskklaxne.supabase.co")
SUPABASE_KEY = getattr(settings, "SUPABASE_KEY", None) or os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVmdHRrZ3l2aG13dnNra"
    "2xheG5lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwODA4MjksImV"
    "4cCI6MjA5NjY1MjgyOX0"
    ".CXRJJdQn21ouipdmBgoTE37L-d5KKfML1YKlWxZGN1E"
)
BUCKET = getattr(settings, "SUPABASE_BUCKET", None) or os.getenv("SUPABASE_BUCKET", "innovescence-ifc-files")

# Persistent local mirror directory for backend reliability
LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "supabase_storage_local")
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
META_FILE = os.path.join(LOCAL_STORAGE_DIR, "_metadata.json")

_client_instance = None

def get_client() -> Optional[Client]:
    global _client_instance
    if _client_instance is not None:
        return _client_instance
    try:
        _client_instance = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _client_instance
    except Exception as e:
        print(f"[Supabase] Client creation warning: {e}")
        return None

def _load_local_meta() -> Dict:
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_local_meta(meta: Dict):
    try:
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
    except Exception as e:
        print(f"[Supabase Local] Metadata save warning: {e}")

def upload_file_to_cloud(file_bytes: bytes, filename: str) -> Optional[str]:
    """
    Uploads file_bytes to private Supabase Storage bucket ('innovescence-ifc-files').
    Guarantees unique storage path while maintaining local persistent mirror.
    Returns the storage path on success.
    """
    safe_name = filename.replace(" ", "_")
    unique_id = str(uuid.uuid4())[:8]
    path = f"{unique_id}_{safe_name}"

    # Always persist to local mirror to prevent data loss during network outages
    local_path = os.path.join(LOCAL_STORAGE_DIR, path)
    try:
        with open(local_path, "wb") as f:
            f.write(file_bytes)

        meta = _load_local_meta()
        meta[path] = {
            "name": path,
            "original_filename": filename,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "size": len(file_bytes),
                "mimetype": "application/octet-stream"
            }
        }
        _save_local_meta(meta)
    except Exception as le:
        print(f"[Supabase Local] Cache write warning: {le}")

    # Attempt upload to real Supabase bucket
    client = get_client()
    if client:
        try:
            client.storage.from_(BUCKET).upload(
                path=path,
                file=file_bytes,
                file_options={
                    "content-type": "application/octet-stream",
                    "upsert": "true",
                }
            )
            print(f"[Supabase] File '{filename}' successfully uploaded to cloud bucket '{BUCKET}' as '{path}'")
        except Exception as e:
            # Catch storage3 and httpx connection errors without raising UnboundLocalError
            print(f"[Supabase] Cloud storage upload warning: {e}")

    return path

def list_cloud_files() -> List[Dict]:
    """
    Returns list of files in the private Supabase bucket.
    Includes files from cloud storage and local persistent mirror.
    """
    file_map = {}
    
    # 1. Load local mirror files first
    local_meta = _load_local_meta()
    for key, info in local_meta.items():
        local_file_path = os.path.join(LOCAL_STORAGE_DIR, key)
        if os.path.exists(local_file_path):
            file_map[key] = info

    # 2. Attempt fetching from real Supabase bucket
    client = get_client()
    if client:
        try:
            res = client.storage.from_(BUCKET).list()
            if res and isinstance(res, list):
                for item in res:
                    if isinstance(item, dict):
                        cname = item.get("name")
                        if cname and cname != ".emptyFolderPlaceholder":
                            size = item.get("metadata", {}).get("size", 0) if item.get("metadata") else 0
                            created = item.get("created_at") or datetime.datetime.utcnow().isoformat() + "Z"
                            file_map[cname] = {
                                "name": cname,
                                "created_at": created,
                                "metadata": {"size": size, "mimetype": "application/octet-stream"}
                            }
        except Exception as e:
            print(f"[Supabase] Cloud list_files warning: {e}")

    return list(file_map.values())

def delete_cloud_file(filename: str) -> bool:
    """
    Deletes file from Supabase bucket and local storage mirror.
    """
    deleted_any = False
    client = get_client()
    if client:
        try:
            client.storage.from_(BUCKET).remove([filename])
            deleted_any = True
        except Exception as e:
            print(f"[Supabase] Cloud delete warning: {e}")

    local_path = os.path.join(LOCAL_STORAGE_DIR, filename)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
            deleted_any = True
        except Exception:
            pass

    meta = _load_local_meta()
    if filename in meta:
        del meta[filename]
        _save_local_meta(meta)
        deleted_any = True

    return deleted_any

def download_cloud_file(filename: str) -> bytes:
    """
    Downloads file content from Supabase bucket or local persistent mirror.
    """
    client = get_client()
    if client:
        try:
            data = client.storage.from_(BUCKET).download(filename)
            if data and len(data) > 0:
                return data
        except Exception as e:
            print(f"[Supabase] Cloud download warning: {e}")

    local_path = os.path.join(LOCAL_STORAGE_DIR, filename)
    if os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                return f.read()
        except Exception as le:
            print(f"[Supabase Local] Read failed: {le}")

    return b""
