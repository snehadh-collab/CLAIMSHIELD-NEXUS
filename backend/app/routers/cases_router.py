from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    BriefRequest,
    CaseActionRequest,
    CopilotContextPayload,
    ExposureForecast,
    MonitoringRequest,
    SIUBriefSchema,
)
from app.services import audit_ledger, case_workflow, insights
from app.services.brief_generator import generate_siu_brief
from app.services.store import get_store

router = APIRouter(prefix="/api/v1/cases", tags=["Cases & Audit"])


def _case_or_404(case_id: str):
    case = get_store().get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case


@router.get("/{case_id}")
def get_case_detail(case_id: str):
    """Everything the Case Investigation page needs: scores, rule findings, linked claims, forecast."""
    case = _case_or_404(case_id)
    return insights.build_case_detail(get_store(), case)


@router.get("/{case_id}/policies")
def get_case_policies(case_id: str):
    """Policy passages retrieved (RAG retrieval, no generation) for the rules this case triggered."""
    case = _case_or_404(case_id)
    return insights.build_case_policies(get_store(), case)


@router.get("/{case_id}/knowledge")
def get_case_knowledge(case_id: str):
    """Deep-Dive Workspace payload: findings, policies, entities, claims, precedents, decisions."""
    case = _case_or_404(case_id)
    return insights.build_knowledge(get_store(), case)


@router.get("/{provider_npi}/forecast", response_model=ExposureForecast)
def get_case_forecast(provider_npi: str):
    """Financial exposure forecast. Accepts a provider NPI (legacy) or a case ID."""
    store = get_store()
    npi = store.resolve_provider(provider_npi)
    if npi is None:
        raise HTTPException(status_code=404, detail=f"Provider NPI {provider_npi} not found")
    return store.exposure(npi)


@router.post("/{case_id}/action")
def submit_case_action(case_id: str, payload: CaseActionRequest):
    """Investigator decision. Validates the case and the transition, updates status, writes the ledger."""
    case = _case_or_404(case_id)
    store = get_store()
    try:
        with store.lock:
            result = case_workflow.apply_action(case.case_id, payload.action, payload.investigator_id, payload.notes)
            store.invalidate()
    except case_workflow.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"status": "SUCCESS", "audit_entry": result["audit_entry"], "case": result["case"]}


@router.get("/{case_id}/audit")
def fetch_case_audit_trail(case_id: str):
    """Chronological audit trail of investigator actions for the case (oldest first)."""
    case = _case_or_404(case_id)
    return {
        "case_id": case.case_id,
        "current_status": case.status,
        "payment_hold": case.payment_hold,
        "audit_trail": audit_ledger.get_case_audit_history(case.case_id),
    }


@router.post("/{case_id}/brief", response_model=SIUBriefSchema)
def create_case_brief(case_id: str, payload: Optional[BriefRequest] = None):
    """Executive brief for the case, grounded in real case facts and retrieved policy passages."""
    case = _case_or_404(case_id)
    store = get_store()
    ctx = insights.build_context(store, case)
    policies = insights.build_case_policies(store, case)["passages"]
    if payload:
        details, flags = payload.claim_details, payload.flagged_rules
    else:
        details = insights.fact_sheet(ctx)
        flags = list(case.rule_flags)
    return generate_siu_brief(
        case_id=case.case_id, claim_details=details, flagged_rules=flags, ctx=ctx, policy_passages=policies
    )
