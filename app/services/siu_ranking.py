from typing import List, Dict
from app.models.schemas import Claim, RuleFlags, AnomalyScore, SIUCase
from app.services.forecasting import calculate_provider_exposure

def compute_composite_score(rule_flag_count: int, ml_score: float, graph_centrality: float) -> float:
    """
    Master Formula:
    Composite Risk = (Rule Flags * 0.3) + (ML Anomaly * 0.3) + (Graph Centrality * 0.4)
    """
    # Normalize rule_flag_count (assuming max expected flags = 3)
    normalized_rules = min(rule_flag_count / 3.0, 1.0)
    score = (normalized_rules * 0.3) + (ml_score * 0.3) + (graph_centrality * 0.4)
    return round(min(score, 1.0), 4)

def generate_siu_queue(
    claims: List[Claim],
    rule_map: Dict[str, RuleFlags],
    anomaly_map: Dict[str, AnomalyScore],
    graph_centrality_map: Dict[str, float]  # Ingested from Member 1's Graph Engine
) -> List[SIUCase]:
    
    cases: List[SIUCase] = []
    provider_claims_map: Dict[str, List[Claim]] = {}

    for c in claims:
        provider_claims_map.setdefault(c.provider_npi, []).append(c)

    for npi, p_claims in provider_claims_map.items():
        total_amount = sum(c.claim_amount for c in p_claims)
        
        max_rule_flags = max((rule_map[c.claim_id].flag_count for c in p_claims if c.claim_id in rule_map), default=0)
        max_ml_score = max((anomaly_map[c.claim_id].ml_score for c in p_claims if c.claim_id in anomaly_map), default=0.0)
        
        # Fetch centrality from Member 1 handoff (defaults to 0.1 if unmapped)
        centrality = graph_centrality_map.get(npi, 0.1)
        composite_score = compute_composite_score(max_rule_flags, max_ml_score, centrality)
        forecast = calculate_provider_exposure(npi, p_claims)

        case = SIUCase(
            case_id=f"CASE-{npi[-5:]}",
            provider_npi=npi,
            member_id=p_claims[0].member_id,
            total_claim_amount=round(total_amount, 2),
            rule_flag_count=max_rule_flags,
            ml_anomaly_score=max_ml_score,
            graph_centrality=centrality,
            composite_risk_score=composite_score,
            forecast=forecast
        )
        cases.append(case)

    # Sort queue by composite risk score descending
    cases.sort(key=lambda x: (x.composite_risk_score, x.total_claim_amount), reverse=True)
    return cases