import datetime
import logging
from typing import Dict, Any, Optional
import httpx

from core.config import get_settings
from services.audit_log import write_audit_entry

logger = logging.getLogger("AutoOps")
settings = get_settings()

def extract_issue_counts(analysis: Dict[str, Any]) -> Dict[str, int]:
    """
    Extracts issue counts grouped by severity ('critical', 'high', 'medium', 'low')
    from the deterministic rule_checks list in the ArchiShield analysis.
    """
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    rule_checks = analysis.get("rule_checks", [])
    if isinstance(rule_checks, list):
        for rule in rule_checks:
            if not isinstance(rule, dict):
                continue
            sev = str(rule.get("severity", "")).strip().lower()
            fails = rule.get("fails", [])
            fail_count = len(fails) if isinstance(fails, list) else 0
            if sev in counts:
                counts[sev] += fail_count
            else:
                counts["medium"] += fail_count
    return counts

def determine_nbc_status(analysis: Dict[str, Any], threshold: float) -> str:
    """
    Deterministically determines NBC compliance status ('PASSED' or 'FAILED').
    First checks explicit rule/check statuses, then compares overall score to threshold.
    n8n and AI models NEVER decide compliance status.
    """
    nbc_results = analysis.get("nbc_results", [])
    if isinstance(nbc_results, list) and nbc_results:
        if any(isinstance(r, dict) and str(r.get("status", "")).strip().lower() == "fail" for r in nbc_results):
            return "FAILED"

    compliance_score = float(analysis.get("nbc_overall_score", 0.0))
    if compliance_score < threshold:
        return "FAILED"

    return "PASSED"

def build_autoops_payload(
    analysis: Dict[str, Any],
    job_id: str,
    model_name: str,
    user: str = "ArchiShield User"
) -> Dict[str, Any]:
    """
    Builds the normalized ArchiShield AutoOps notification payload
    from real, deterministic analysis metrics.
    """
    curr_settings = get_settings()
    threshold = getattr(curr_settings, "NBC_COMPLIANCE_THRESHOLD", 80.0)
    public_base_url = (getattr(curr_settings, "PUBLIC_BASE_URL", "http://127.0.0.1:8000") or "http://127.0.0.1:8000").rstrip("/")

    health_score = float(analysis.get("quality_score", 0.0))
    compliance_score = float(analysis.get("nbc_overall_score", 0.0))
    nbc_status = determine_nbc_status(analysis, threshold)
    severity = str(analysis.get("severity", "LOW")).upper()
    issue_counts = extract_issue_counts(analysis)

    critical_issues = issue_counts.get("critical", 0)
    high_issues = issue_counts.get("high", 0)
    medium_issues = issue_counts.get("medium", 0)
    low_issues = issue_counts.get("low", 0)
    total_issues = critical_issues + high_issues + medium_issues + low_issues

    report_url = f"{public_base_url}/api/analyze/pdf-report"
    bcf_url = f"{public_base_url}/api/analyze/bcf"

    payload = {
        "event": "ANALYSIS_COMPLETED",
        "timestamp": datetime.datetime.now().isoformat(),
        "job_id": job_id,
        "model_name": model_name,
        "user": user,
        "health_score": health_score,
        "compliance_score": compliance_score,
        "compliance_threshold": float(threshold),
        "nbc_status": nbc_status,
        "severity": severity,
        "critical_issues": critical_issues,
        "high_issues": high_issues,
        "medium_issues": medium_issues,
        "low_issues": low_issues,
        "total_issues": total_issues,
        "issue_counts": issue_counts,
        "bcf_url": bcf_url,
        "report_url": report_url
    }
    return payload

async def process_autoops_completion(
    analysis: Dict[str, Any],
    job_id: str,
    model_name: str,
    user: str = "ArchiShield User"
) -> Dict[str, Any]:
    """
    Main AutoOps entrypoint called post-analysis:
    1. Builds normalized payload.
    2. Writes append-only audit log.
    3. Safely posts payload to n8n webhook if configured.
    Guaranteed never to throw exceptions that interrupt core BIM analysis.
    """
    curr_settings = get_settings()
    result = {
        "status": "completed",
        "audit_logged": False,
        "n8n_notified": False,
        "nbc_status": "PASSED"
    }

    try:
        payload = build_autoops_payload(analysis, job_id, model_name, user)
        result["nbc_status"] = payload["nbc_status"]

        # 1. Write Audit Log Event
        audit_success = write_audit_entry(payload)
        result["audit_logged"] = audit_success

        # 2. POST to n8n Webhook Safely
        webhook_url = getattr(curr_settings, "N8N_WEBHOOK_URL", "") or ""
        if webhook_url:
            print(f"[AUTOOPS] Sending result to n8n: {webhook_url}")
            logger.info(f"[AUTOOPS] Sending result to n8n webhook for job '{job_id}'")
            headers = {
                "Content-Type": "application/json",
                "X-N8N-Webhook-Secret": getattr(curr_settings, "N8N_WEBHOOK_SECRET", "")
            }
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    response = await client.post(webhook_url, json=payload, headers=headers)
                    if response.status_code < 400:
                        print(f"[AUTOOPS] n8n notification successful (status {response.status_code})")
                        logger.info(f"[AUTOOPS] n8n notification successful")
                        result["n8n_notified"] = True
                    else:
                        print(f"[AUTOOPS] n8n notification failed with status code {response.status_code}")
                        logger.warning(f"[AUTOOPS] n8n notification failed: status code {response.status_code}")
            except Exception as net_err:
                print(f"[AUTOOPS] n8n notification failed: {net_err}")
                logger.exception(f"[AUTOOPS] n8n notification failed: {net_err}")
        else:
            print("[AUTOOPS] n8n notification skipped: N8N_WEBHOOK_URL is not configured")
            logger.info("[AUTOOPS] n8n notification skipped: URL empty")

    except Exception as top_err:
        print(f"[AUTOOPS] Unexpected error during AutoOps processing: {top_err}")
        logger.exception(f"[AUTOOPS] Unexpected error in process_autoops_completion: {top_err}")

    return result
