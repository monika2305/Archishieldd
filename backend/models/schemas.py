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
