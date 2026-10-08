from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.models.copilot import AuditAction, AuditTrailResponse
from app.services.audit_service import audit_service
from app.services.data_service import data_service

router = APIRouter(prefix="/api/v1/cases", tags=["Human-in-the-Loop & Audit"])

@router.post("/{case_id}/action", response_model=AuditAction)
def record_case_action(case_id: str, action_data: AuditAction):
    """Record human-in-the-loop audit decision (e.g. PAYMENT_HOLD, AUDIT, DISMISS)."""
    if action_data.case_id != case_id:
        action_data.case_id = case_id
    return audit_service.record_action(action_data)

@router.get("/{case_id}/audit", response_model=AuditTrailResponse)
def get_case_audit_trail(case_id: str):
    """Retrieve full audit history for a specific case."""
    actions = audit_service.get_audit_trail(case_id)
    return AuditTrailResponse(case_id=case_id, actions=actions)

@router.get("/{case_id}/forecast")
def get_case_forecast(case_id: str) -> Dict[str, Any]:
    """Financial exposure & risk forecast for flagged case/provider."""
    clean_id = case_id.replace("CASE-", "")
    claim = data_service.get_claim_by_id(clean_id)
    
    if not claim:
        # Fallback values
        base_amount = 450.00
    else:
        base_amount = claim.claim_amount

    return {
        "case_id": case_id,
        "current_claim_exposure": base_amount,
        "projected_30day_exposure": round(base_amount * 12.5, 2),
        "projected_90day_exposure": round(base_amount * 37.5, 2),
        "recommended_reserve_hold": round(base_amount * 1.5, 2),
        "risk_trajectory": "HIGH_INCREASING" if base_amount > 400 else "STABLE"
    }
