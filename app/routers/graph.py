from fastapi import APIRouter, Query, HTTPException
from typing import List
from app.models.graph import GraphPayload, CentralityHub
from app.services.graph_service import graph_service

router = APIRouter(prefix="/api/v1/graph", tags=["Graph ML"])

@router.get("/centrality", response_model=List[CentralityHub])
def get_degree_centrality_hubs(top_n: int = Query(10, ge=1, le=100)):
    """Retrieve top degree centrality nodes (fraud rings/hubs)."""
    return graph_service.get_top_centrality(top_n=top_n)

@router.get("/{target_id}", response_model=GraphPayload)
def get_subgraph_for_entity(
    target_id: str,
    radius: int = Query(1, ge=1, le=3)
):
    """Retrieve graph payload (nodes & edges) centered around a claim, provider NPI, or member ID."""
    payload = graph_service.get_subgraph_payload(target_id=target_id, radius=radius)
    if payload.total_nodes == 0:
        raise HTTPException(status_code=404, detail=f"Entity {target_id} not found in claim graph")
    return payload
