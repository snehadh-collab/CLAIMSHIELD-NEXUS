from fastapi import APIRouter, Query
from typing import List, Optional
from app.models.siu_case import SIUCase, GraphRisk
from app.services.data_service import data_service
from app.services.rules_engine import evaluate_claim_rules
from app.services.ml_engine import ml_service
from app.services.graph_service import graph_service
from app.services.scoring_engine import create_siu_case

router = APIRouter(prefix="/api/v1/siu", tags=["SIU Queue"])

@router.get("/queue", response_model=List[SIUCase])
def get_siu_queue(
    min_score: float = Query(0.1, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=500)
):
    """Retrieve prioritized SIU investigation queue sorted by composite risk score."""
    claims = data_service.claims
    cases = []

    for c in claims:
        # Quick pre-filter if clean claim to save compute
        rule_flags = evaluate_claim_rules(c, claims)
        anomaly_score = ml_service.predict(c)
        degree_cent = graph_service.get_node_risk(c.provider_npi)
        graph_risk = GraphRisk(
            degree_centrality=round(degree_cent, 6),
            is_ring_hub=degree_cent > 0.05
        )

        siu_case = create_siu_case(c, rule_flags, anomaly_score, graph_risk)
        if siu_case.composite_risk.composite_score >= min_score or rule_flags.flag_count > 0:
            cases.append(siu_case)

    # Sort descending by composite risk score
    cases.sort(key=lambda x: x.composite_risk.composite_score, reverse=True)
    return cases[:limit]
