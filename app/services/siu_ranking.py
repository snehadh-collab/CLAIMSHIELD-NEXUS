from typing import List, Dict
from app.models.schemas import Claim, RuleFlags, AnomalyScore, SIUCase
from app.services.forecasting import calculate_provider_exposure

def compute_composite_score(rule_flags_count: int, ml_anomaly_score: float, graph_centrality: float) -> float:
    """
    Weighted scoring algorithm combining rules (40%), ML score (40%), and network graph centrality (20%).
    """
    rule_score = min(rule_flags_count / 3.0, 1.0)
    composite = (rule_score * 0.40) + (ml_anomaly_score * 0.40) + (graph_centrality * 0.20)
    return round(composite, 4)

def generate_siu_queue(
    claims: List[Claim],
    rule_map: Dict[str, RuleFlags],
    anomaly_map: Dict[str, AnomalyScore],
    graph_centrality_map: Dict[str, float]
) -> List[SIUCase]:
    
    cases: List[SIUCase] = []
    provider_claims_map: Dict[str, List[Claim]] = {}

    for c in claims:
        provider_claims_map.setdefault(c.provider_npi, []).append(c)

    for npi, p_claims in provider_claims_map.items():
        total_amount = sum(c.claim_amount for c in p_claims)
        
        max_rule_flags = max((rule_map[c.claim_id].flag_count for c in p_claims if c.claim_id in rule_map), default=0)
        max_ml_score = max((anomaly_map[c.claim_id].ml_score for c in p_claims if c.claim_id in anomaly_map), default=0.0)
        
        reasons = []
        for c in p_claims:
            if c.claim_id in rule_map:
                reasons.extend(rule_map[c.claim_id].flag_reasons)
        primary_reason = reasons[0] if reasons else "ML Anomaly Score Flag"

        centrality = graph_centrality_map.get(npi, 0.1)
        composite_score = compute_composite_score(max_rule_flags, max_ml_score, centrality)
        forecast = calculate_provider_exposure(npi, p_claims)

        case = SIUCase(
            case_id=f"CASE-{npi[-5:] if len(npi) >= 5 else npi}",
            provider_npi=npi,
            member_id=p_claims[0].member_id if p_claims else None,
            total_flagged_amount=round(total_amount, 2),
            total_claim_amount=round(total_amount, 2),
            claim_count=len(p_claims),
            primary_flag_reason=primary_reason,
            rule_flag_count=max_rule_flags,
            ml_anomaly_score=max_ml_score,
            graph_centrality=centrality,
            composite_risk_score=composite_score,
            forecast=forecast
        )
        cases.append(case)

    # Sort queue descending by composite risk score
    cases.sort(key=lambda x: x.composite_risk_score, reverse=True)
    return cases