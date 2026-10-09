from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import MonitoringRequest
from app.services import audit_ledger, case_workflow, insights
from app.services.siu_ranking import case_id_for
from app.services.store import get_store

router = APIRouter(prefix="/api/v1", tags=["Insights, Providers & Search"])


@router.get("/stats")
def get_stats():
    """Dashboard KPIs computed from the stored claims and cases."""
    return insights.build_stats(get_store())


@router.get("/search")
def search(q: str = Query("", max_length=200)):
    """Global search over cases/providers, claims, policy passages (RAG) and historical precedents."""
    return insights.global_search(get_store(), q)


@router.get("/audit")
def recent_audit(limit: int = Query(20, ge=1, le=200)):
    """Most recent investigator actions across all cases (newest first)."""
    return {"audit_trail": audit_ledger.get_recent_audit_events(limit)}


@router.get("/providers/{provider_npi}")
def get_provider(provider_npi: str):
    store = get_store()
    npi = store.resolve_provider(provider_npi)
    case = store.get_case(case_id_for(npi)) if npi else None
    if case is None:
        raise HTTPException(status_code=404, detail=f"Provider {provider_npi} not found")
    return insights.build_provider_profile(store, case)


@router.put("/providers/{provider_npi}/monitoring")
def set_provider_monitoring(provider_npi: str, payload: MonitoringRequest):
    """Add or remove a provider from the monitoring watchlist (persisted, audited).

    Recording the watchlist entry is all this does: no alert delivery exists yet.
    """
    store = get_store()
    npi = store.resolve_provider(provider_npi)
    if npi is None:
        raise HTTPException(status_code=404, detail=f"Provider {provider_npi} not found")
    try:
        with store.lock:
            result = case_workflow.set_monitoring(case_id_for(npi), npi, payload.enabled, payload.investigator_id, payload.notes)
            store.invalidate()
    except case_workflow.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return result
