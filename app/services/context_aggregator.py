from typing import List, Dict
from app.models.schemas import Claim, RuleFlags, AnomalyScore, CopilotContextPayload
from app.services.forecasting import calculate_provider_exposure

def build_copilot_context(
    case_id: str,
    provider_npi: str,
    claims: List[Claim],
    rule_map: Dict[str, RuleFlags],
    anomaly_map: Dict[str, AnomalyScore],
    graph_centrality: float,
    composite_risk_score: float,
    policy_snippets: List[str] = None
) -> CopilotContextPayload:
    """
    Feature 3.2 Context Aggregator: Combines claims, rule flags, ML anomaly scores,
    graph centrality, and financial loss forecasts into a single payload for the AI Copilot.
    """
    provider_claims = [c for c in claims if c.provider_npi == provider_npi]
    total_amount = sum(c.claim_amount for c in provider_claims)
    
    all_reasons = []
    for c in provider_claims:
        if c.claim_id in rule_map:
            all_reasons.extend(rule_map[c.claim_id].flag_reasons)
    unique_reasons = list(set(all_reasons))

    max_ml_score = max(
        (anomaly_map[c.claim_id].ml_score for c in provider_claims if c.claim_id in anomaly_map),
        default=0.0
    )

    forecast = calculate_provider_exposure(provider_npi, provider_claims)

    return CopilotContextPayload(
        case_id=case_id,
        provider_npi=provider_npi,
        member_id=provider_claims[0].member_id if provider_claims else "UNKNOWN",
        total_claim_amount=round(total_amount, 2),
        composite_risk_score=composite_risk_score,
        rule_flag_count=len(unique_reasons),
        rule_flag_reasons=unique_reasons,
        ml_anomaly_score=max_ml_score,
        graph_centrality_score=graph_centrality,
        projected_30d_loss=forecast.day_30_exposure,
        projected_90d_loss=forecast.day_90_exposure,
        associated_claim_ids=[c.claim_id for c in provider_claims],
        policy_context_paragraphs=policy_snippets or [
            "NCD 190.3: High-frequency billing across multiple locations without referral triggers immediate SIU review.",
            "FWA Rule 42: Billing amounts exceeding 4x regional benchmark trigger automated payment suspension."
        ]
    )