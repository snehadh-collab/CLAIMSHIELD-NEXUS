from app.models.claim import Claim
from app.models.siu_case import RuleFlags, AnomalyScore, GraphRisk, CompositeRiskScore, SIUCase

def calculate_composite_risk(
    rule_flags: RuleFlags,
    anomaly_score: AnomalyScore,
    graph_risk: GraphRisk
) -> CompositeRiskScore:
    # Rule component score (normalized 0.0 to 1.0)
    rule_component = min(rule_flags.flag_count / 3.0, 1.0)
    
    # ML component score (0.0 to 1.0)
    ml_component = anomaly_score.ml_score
    
    # Graph component score (scaled centrality score 0.0 to 1.0)
    graph_component = min(graph_risk.degree_centrality * 10.0, 1.0)
    
    # Weighted composite formula: 30% Rules + 30% ML + 40% Graph
    composite = (rule_component * 0.3) + (ml_component * 0.3) + (graph_component * 0.4)
    composite = round(min(max(composite, 0.0), 1.0), 4)

    # Risk Tier classification
    if composite >= 0.70:
        tier = "CRITICAL"
    elif composite >= 0.45:
        tier = "HIGH"
    elif composite >= 0.25:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return CompositeRiskScore(
        composite_score=composite,
        risk_tier=tier,
        rule_score=round(rule_component, 4),
        ml_score=round(ml_component, 4),
        graph_score=round(graph_component, 4)
    )

def create_siu_case(
    claim: Claim,
    rule_flags: RuleFlags,
    anomaly_score: AnomalyScore,
    graph_risk: GraphRisk
) -> SIUCase:
    composite_risk = calculate_composite_risk(rule_flags, anomaly_score, graph_risk)
    
    # Determine initial status
    status = "UNDER_INVESTIGATION" if composite_risk.composite_score >= 0.45 else "PENDING"
    
    return SIUCase(
        case_id=f"CASE-{claim.claim_id}",
        claim=claim,
        rule_flags=rule_flags,
        anomaly_score=anomaly_score,
        graph_risk=graph_risk,
        composite_risk=composite_risk,
        status=status
    )
