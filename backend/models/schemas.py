from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class LoginRequest(BaseModel):
    name: str
    role: str
    domain: str
    purpose: str

class QueryRequest(BaseModel):
    question: str

class CorrectionItem(BaseModel):
    GlobalId: str
    NewType: str

class ApplyCorrectionsRequest(BaseModel):
    selections: Dict[str, str]  # GlobalId -> Suggested Type
    pset_fixes: Optional[Dict[str, Any]] = None  # GlobalId -> Pset details

class AutomationCallbackRequest(BaseModel):
    job_id: str
    file_id: Optional[str] = None
    status: str = "completed"
    quality_score: Optional[float] = None
    severity: Optional[str] = None
    summary: Optional[str] = None
    critical_issues_count: Optional[int] = 0
    requires_immediate_action: Optional[bool] = False
    details: Optional[Dict[str, Any]] = None

class AutomationSummaryRequest(BaseModel):
    job_id: Optional[str] = None
    custom_instructions: Optional[str] = None
