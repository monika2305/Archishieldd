import datetime
import uuid
from typing import List, Dict
from supabase import create_client, Client

SUPABASE_URL = "https://ufttkgyvhmwvskklaxne.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVmdHRrZ3l2aG13dnNra"
    "2xheG5lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwODA4MjksImV"
    "4cCI6MjA5NjY1NjgyOX0"
    ".CXRJJdQn21ouipdmBgoTE37L-d5KKfML1YKlWxZGN1E"
)
BUCKET = "innovescence-ifc-files"

def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_file_to_cloud(file_bytes: bytes, filename: str) -> str:
    client = get_client()
    safe_name = filename.replace(" ", "_")
    path = f"{str(uuid.uuid4())[:8]}_{safe_name}"
    
    client.storage.from_(BUCKET).upload(
        path=path,
        file=file_bytes,
        file_options={
            "content-type": "application/octet-stream",
            "upsert": "true",
        }
    )
    return path

def list_cloud_files() -> List[Dict]:
    client = get_client()
    try:
        return client.storage.from_(BUCKET).list() or []
    except Exception:
        return []

def delete_cloud_file(filename: str) -> bool:
    client = get_client()
    try:
        client.storage.from_(BUCKET).remove([filename])
        return True
    except Exception:
        return False

def download_cloud_file(filename: str) -> bytes:
    client = get_client()
    try:
        return client.storage.from_(BUCKET).download(filename)
    except Exception:
        return b""
