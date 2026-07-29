"""
supabase_storage.py
───────────────────
Cloud storage helpers for the IFC Analyser app.
Bucket  : innovescence-ifc-files  (private)
Project : https://ufttkgyvhmwvskklaxne.supabase.co
"""

from __future__ import annotations
import datetime
import time
from typing import List, Dict, Optional

import streamlit as st
from supabase import create_client, Client

# ── Credentials ────────────────────────────────────────────────────────────────
SUPABASE_URL = "https://ufttkgyvhmwvskklaxne.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVmdHRrZ3l2aG13dnNra"
    "2xheG5lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwODA4MjksImV"
    "4cCI6MjA5NjY1NjgyOX0"
    ".CXRJJdQn21ouipdmBgoTE37L-d5KKfML1YKlWxZGN1E"
)

# ── Bucket names (keep both so any page can reference either) ──────────────────
BUCKET     = "innovescence-ifc-files"
BUCKET_IFC = BUCKET          # backward-compat alias


# ── Client — cached for the whole session ─────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    """Return (and cache) a Supabase client. Importable by any page."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# keep a private alias so internal code stays clean
def _client() -> Client:
    return get_supabase_client()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _stamped(filename: str) -> str:
    """Prefix filename with UTC timestamp — guarantees unique paths."""
    ts   = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe = filename.replace(" ", "_")
    return f"{ts}_{safe}"


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD  — retries 3 times, 2 s back-off, non-blocking on final failure
# ══════════════════════════════════════════════════════════════════════════════
def upload_ifc(file_bytes: bytes, original_name: str,
               retries: int = 3) -> bool:
    import uuid
    safe = original_name.replace(" ", "_")
    path = f"{str(uuid.uuid4())[:8]}_{safe}"

    for attempt in range(1, retries + 1):
        try:
            _client().storage.from_(BUCKET).upload(
                path=path,
                file=file_bytes,
                file_options={
                    "content-type": "application/octet-stream",
                    "upsert": "true",
                },
            )
            return True
        except Exception as exc:
            err = str(exc).lower()
            if "already exists" in err or "duplicate" in err:
                path = f"{str(uuid.uuid4())[:8]}_{safe}"
                time.sleep(0.5)
                continue
            if attempt < retries:
                time.sleep(2)
            else:
                st.warning(f"☁️ Upload failed after {retries} attempts: {exc}")
    return False


# ══════════════════════════════════════════════════════════════════════════════
# LIST
# ══════════════════════════════════════════════════════════════════════════════
def list_files() -> List[Dict]:
    """Return all files in the bucket. Returns [] on error."""
    try:
        return _client().storage.from_(BUCKET).list() or []
    except Exception as exc:
        st.error(f"☁️ Could not list files: {exc}")
        return []


# ── Backward-compat alias used by old cloud_library page ──────────────────────
def list_user_ifcs() -> List[Dict]:
    return list_files()


# ══════════════════════════════════════════════════════════════════════════════
# DELETE
# ══════════════════════════════════════════════════════════════════════════════
def delete_file(filename: str) -> bool:
    """Delete one file by its stored name. Returns True on success."""
    try:
        _client().storage.from_(BUCKET).remove([filename])
        return True
    except Exception as exc:
        st.error(f"☁️ Delete failed: {exc}")
        return False


# ── Backward-compat alias ──────────────────────────────────────────────────────
def delete_ifc(filename: str) -> bool:
    return delete_file(filename)


# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════
def download_file(filename: str) -> bytes:
    """Download a file by its stored name. Returns b'' on failure."""
    try:
        return _client().storage.from_(BUCKET).download(filename)
    except Exception as exc:
        st.error(f"☁️ Download failed: {exc}")
        return b""


# ── Backward-compat alias ──────────────────────────────────────────────────────
def download_ifc_from_cloud(filename: str) -> bytes:
    return download_file(filename)


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE ALIASES  (snapshot / pdf uploads reuse the same bucket)
# ══════════════════════════════════════════════════════════════════════════════
def upload_snapshot(data: bytes, filename: str) -> bool:
    return upload_ifc(data, filename)


def upload_pdf(data: bytes, filename: str) -> bool:
    return upload_ifc(data, filename)
