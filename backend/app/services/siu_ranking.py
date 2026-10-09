from collections import Counter
from typing import Dict, List, Optional
from app.models.schemas import Claim, RuleFlags, AnomalyScore, SIUCase
from app.services.forecasting import calculate_provider_exposure
from app.services.rules_engine import rule_codes, RULE_LABELS

CASE_PREFIX = "CASE-"


def case_id_for(provider_npi: str) -> str:
    """Stable, collision-free case ID: one case per provider NPI."""
    return f"{CASE_PREFIX}{provider_npi}"


def npi_from_case_id(case_id: str) -> Optional[str]:
    if case_id.startswith(CASE_PREFIX) and len(case_id) > len(CASE_PREFIX):
        return case_id[len(CASE_PREFIX):]
    return None


def compute_composite_score(rule_flag_count: int, ml_score: float, graph_centrality: float) -> float:
    """
    Master Formula:
    Composite Risk = (Rule Flags * 0.3) + (ML Anomaly * 0.3) + (Graph Centrality * 0.4)
    rule_flag_count is the number of distinct rule categories triggered (max 3).
    """
    normalized_rules = min(rule_flag_count / 3.0, 1.0)
    score = (normalized_rules * 0.3) + (ml_score * 0.3) + (graph_centrality * 0.4)
    return round(min(max(score, 0.0), 1.0), 4)


def _primary_finding(code_counts: Counter, ml_score: float, centrality: float) -> str:
    if code_counts:
        code, _ = code_counts.most_common(1)[0]
        return RULE_LABELS[code]
    if ml_score >= 0.6:
        return "ML anomaly"
    if centrality >= 0.5:
        return "Network centrality"
    return "No active rule flags"


def summarize_provider(
    npi: str,
    p_claims: List[Claim],
    rule_map: Dict[str, RuleFlags],
    anomaly_map: Dict[str, AnomalyScore],
    graph_centrality_map: Dict[str, float],
):
    """Provider-level roll-up used by both the queue and the case detail."""
    code_counts: Counter = Counter()
    for c in p_claims:
        flags = rule_map.get(c.claim_id)
        if flags:
            code_counts.update(rule_codes(flags))
    max_ml = max((anomaly_map[c.claim_id].ml_score for c in p_claims if c.claim_id in anomaly_map), default=0.0)
    centrality = graph_centrality_map.get(npi, 0.0)
    composite = compute_composite_score(len(code_counts), max_ml, centrality)
    return code_counts, max_ml, centrality, composite


def generate_siu_queue(
    claims: List[Claim],
    rule_map: Dict[str, RuleFlags],
    anomaly_map: Dict[str, AnomalyScore],
    graph_centrality_map: Dict[str, float],
    provider_names: Optional[Dict[str, str]] = None,
    case_states: Optional[Dict[str, Dict]] = None,
    last_actions: Optional[Dict[str, str]] = None,
) -> List[SIUCase]:
    cases: List[SIUCase] = []
    provider_claims_map: Dict[str, List[Claim]] = {}
    provider_names = provider_names or {}
    case_states = case_states or {}
    last_actions = last_actions or {}

    for c in claims:
        provider_claims_map.setdefault(c.provider_npi, []).append(c)

    for npi, p_claims in provider_claims_map.items():
        total_amount = sum(c.claim_amount for c in p_claims)
        code_counts, max_ml, centrality, composite = summarize_provider(
            npi, p_claims, rule_map, anomaly_map, graph_centrality_map
        )
        forecast = calculate_provider_exposure(npi, p_claims)
        case_id = case_id_for(npi)
        state = case_states.get(case_id, {})
        finding = _primary_finding(code_counts, max_ml, centrality)

        cases.append(
            SIUCase(
                case_id=case_id,
                provider_npi=npi,
                member_id=p_claims[0].member_id,
                total_claim_amount=round(total_amount, 2),
                rule_flag_count=len(code_counts),
                ml_anomaly_score=max_ml,
                graph_centrality=round(centrality, 4),
                composite_risk_score=composite,
                status=state.get("status", "OPEN"),
                forecast=forecast,
                provider_name=provider_names.get(npi),
                claim_count=len(p_claims),
                rule_flags=sorted(code_counts.keys()),
                primary_finding=finding,
                title=f"{finding} review" if code_counts else "Provider risk review",
                payment_hold=bool(state.get("payment_hold", False)),
                latest_claim_at=max(c.timestamp for c in p_claims).isoformat(),
                last_action_at=last_actions.get(case_id),
            )
        )

    # Sort queue by composite risk score descending
    cases.sort(key=lambda x: (x.composite_risk_score, x.total_claim_amount), reverse=True)
    return cases
