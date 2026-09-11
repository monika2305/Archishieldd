import os
import json
import logging
from typing import List, Dict, Any
from core.config import get_settings

logger = logging.getLogger("AutoOps")
settings = get_settings()

def get_resolved_audit_path() -> str:
    """Returns the absolute or resolved relative path to the audit log file."""
    path = settings.AUDIT_LOG_PATH or "data/autoops_audit.jsonl"
    if not os.path.isabs(path):
        # Resolve relative to project backend root
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(backend_dir, path)
    return path

def write_audit_entry(entry: Dict[str, Any]) -> bool:
    """
    Appends a single audit event as a JSON line to the audit log.
    Ensures parent directories exist and catches all I/O exceptions so
    audit logging never interrupts core BIM analysis execution.
    """
    try:
        file_path = get_resolved_audit_path()
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        json_line = json.dumps(entry, ensure_ascii=False)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json_line + "\n")
            
        print(f"[AUTOOPS] Analysis event logged: {entry.get('model_name', 'model.ifc')} -> nbc_status={entry.get('nbc_status')}")
        logger.info(f"[AUTOOPS] Analysis event logged for job '{entry.get('job_id')}'")
        return True
    except Exception as e:
        print(f"[AUTOOPS] Failed to write audit log safely: {e}")
        logger.exception(f"[AUTOOPS] Failed to write audit log entry: {e}")
        return False

def read_audit_entries(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Reads recent audit events from the JSON Lines file.
    Safely handles nonexistent file, empty file, or malformed individual lines.
    """
    file_path = get_resolved_audit_path()
    if not os.path.exists(file_path):
        return []

    entries: List[Dict[str, Any]] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Parse from newest to oldest up to limit
        for line in reversed(lines):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                if isinstance(data, dict):
                    entries.append(data)
                if len(entries) >= limit:
                    break
            except Exception as parse_err:
                logger.warning(f"[AUTOOPS] Skipped malformed log line: {parse_err}")
                continue
                
    except Exception as e:
        print(f"[AUTOOPS] Error reading audit log: {e}")
        logger.exception(f"[AUTOOPS] Error reading audit log: {e}")

    return entries
