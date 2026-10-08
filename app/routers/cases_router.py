from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.audit_ledger import record_action, get_case_audit_history

router = APIRouter(prefix="/api/v1/cases", tags=["Cases & Audit"])

class CaseActionRequest(BaseModel):
    action: str  # APPROVE_SIU, REQUEST_INFO, DISMISS
    investigator_id: str = "INV-DEFAULT"
    notes: str = ""

@router.post("/{case_id}/action")
def submit_case_action(case_id: str, payload: CaseActionRequest):
    """Endpoint for human investigators to approve, dismiss, or request info on a case."""
    valid_actions = ["APPROVE_SIU", "REQUEST_INFO", "DISMISS"]
    if payload.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of {valid_actions}")
    
    result = record_action(
        case_id=case_id,
        action=payload.action,
        investigator_id=payload.investigator_id,
        notes=payload.notes
    )
    return {"status": "SUCCESS", "audit_entry": result}

@router.get("/{case_id}/audit")
def fetch_case_audit_trail(case_id: str):
    """Endpoint for Member 4's UI to fetch chronological audit trail."""
    history = get_case_audit_history(case_id)
    return {"case_id": case_id, "audit_trail": history}