from typing import List, Dict, Optional
from app.models.schemas import Claim, RuleFlags, AnomalyScore, CopilotContextPayload
from app.services.forecasting import calculate_provider_exposure
from app.services.rules_engine import rule_codes

MAX_REASONS = 12


def build_copilot_context(
    case_id: str,
    provider_npi: str,
    claims: List[Claim],
    rule_map: Dict[str, RuleFlags],
    anomaly_map: Dict[str, AnomalyScore],
    graph_centrality: float,
    composite_risk_score: float,
    policy_snippets: Optional[List[str]] = None,
    provider_name: Optional[str] = None,
    status: str = "OPEN",
    payment_hold: bool = False,
) -> CopilotContextPayload:
    """
    Feature 3.2: Aggregates claim history, rule flags, ML anomaly scores,
    graph centrality, and loss forecasts into a unified memory context for the Copilot LLM.

    `rule_flag_count` is the number of distinct rule categories triggered (same meaning as in the
    SIU queue). `rule_flag_reasons` lists up to MAX_REASONS distinct reason strings.
    """
    provider_claims = [c for c in claims if c.provider_npi == provider_npi]
    total_amount = sum(c.claim_amount for c in provider_claims)

    categories = set()
    reasons: List[str] = []
    for c in provider_claims:
        flags = rule_map.get(c.claim_id)
        if flags:
            categories.update(rule_codes(flags))
            for r in flags.flag_reasons:
                if r not in reasons:
                    reasons.append(r)

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
        rule_flag_count=len(categories),
        rule_flag_reasons=reasons[:MAX_REASONS],
        ml_anomaly_score=max_ml_score,
        graph_centrality_score=graph_centrality,
        projected_30d_loss=forecast.day_30_exposure,
        projected_90d_loss=forecast.day_90_exposure,
        associated_claim_ids=[c.claim_id for c in provider_claims],
        policy_context_paragraphs=policy_snippets or [],
        provider_name=provider_name,
        status=status,
        payment_hold=payment_hold,
    )
