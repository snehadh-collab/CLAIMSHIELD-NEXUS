from fastapi import APIRouter, Query, HTTPException
from typing import List
from app.models.claim import Claim
from app.services.data_service import data_service
from app.services.ml_engine import ml_service
from app.services.graph_service import graph_service
from scripts.generate_claims import generate_synthetic_dataset
from app.config import settings
from app.routers.dashboard import invalidate_dashboard_cache

router = APIRouter(prefix="/api/v1/claims", tags=["Claims"])

@router.get("/", response_model=List[Claim])
def get_claims(
    limit: int = Query(100, ge=1, le=5000),
    skip: int = Query(0, ge=0)
):
    """Retrieve paginated claims from memory/dataset."""
    return data_service.get_claims(limit=limit, skip=skip)

@router.get("/{claim_id}", response_model=Claim)
def get_claim_by_id(claim_id: str):
    """Get specific claim details by ID."""
    claim = data_service.get_claim_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return claim

@router.post("/generate")
def generate_claims_dataset(num_claims: int = Query(5000, ge=100, le=10000)):
    """Trigger synthetic claim dataset generation."""
    df = generate_synthetic_dataset(num_claims=num_claims, output_dir=settings.DATA_DIR)
    loaded_claims = data_service.load_or_generate_dataset(num_claims=num_claims)
    ml_service.fit(loaded_claims)
    graph_service.build_graph_from_claims(loaded_claims)
    invalidate_dashboard_cache()
    return {
        "status": "success",
        "generated_count": len(df),
        "loaded_memory_count": len(loaded_claims),
        "analytics_refreshed": True
    }
