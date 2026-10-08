from fastapi import APIRouter
from app.models.claim import Claim
from app.models.siu_case import ClaimAnalysisResponse, GraphRisk
from app.services.rules_engine import evaluate_claim_rules
from app.services.ml_engine import ml_service
from app.services.graph_service import graph_service
from app.services.scoring_engine import calculate_composite_risk
from app.services.data_service import data_service

router = APIRouter(prefix="/api/v1/analyze", tags=["Analysis"])

@router.post("/", response_model=ClaimAnalysisResponse)
@router.post("", response_model=ClaimAnalysisResponse)
def analyze_claim(claim: Claim):
    """Evaluates a claim through Rule Engine, ML Anomaly Detection,

    Graph Centrality Engine, and Composite Risk Scoring.
    """
    recent_claims = data_service.claims
    rule_results = evaluate_claim_rules(claim, recent_claims)
    anomaly_results = ml_service.predict(claim)
    
    degree_cent = graph_service.get_node_risk(claim.provider_npi)
    graph_risk = GraphRisk(
        degree_centrality=round(degree_cent, 6),
        is_ring_hub=degree_cent > 0.05
    )

    composite_risk = calculate_composite_risk(rule_results, anomaly_results, graph_risk)

    data_service.add_claim(claim)

    return ClaimAnalysisResponse(
        claim_id=claim.claim_id,
        provider_npi=claim.provider_npi,
        rule_flags=rule_results,
        anomaly_score=anomaly_results,
        graph_risk=graph_risk,
        composite_risk=composite_risk
    )
