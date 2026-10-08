"""Aggregated endpoint feeding the SIU executive dashboard (frontend)."""
from collections import defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter, Query

from app.models.siu_case import GraphRisk
from app.services.data_service import data_service
from app.services.graph_service import graph_service
from app.services.ml_engine import ml_service
from app.services.policy_rag import get_relevant_policies
from app.services.rules_engine import CPT_BASELINE_BENCHMARK, evaluate_claim_rules
from app.services.scoring_engine import create_siu_case

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

_cache: Dict[str, Any] = {}

FLAG_META = {
    "PHANTOM_BILLING": ("Phantom billing", "SECTION 103 phantom billing & facility fraud"),
    "UPCODING": ("Upcoding", "SECTION 102 unbundling & upcoding anomalies"),
    "IMPOSSIBLE_GEOGRAPHY": ("Impossible geography", "SECTION 101 duplicate billing & timing rules"),
}


def invalidate_dashboard_cache() -> None:
    _cache.clear()


def _detect_flag(rule_flags, dataset_flag: str) -> str:
    if rule_flags.phantom_billing:
        return "PHANTOM_BILLING"
    if rule_flags.impossible_geography:
        return "IMPOSSIBLE_GEOGRAPHY"
    if rule_flags.upcoding_anomaly:
        return "UPCODING"
    if dataset_flag and dataset_flag != "CLEAN":
        return dataset_flag
    return "CLEAN"


def _brief(claim, flag: str, reasons: List[str], ratio: float) -> str:
    who = claim.provider_name or f"NPI {claim.provider_npi}"
    if flag == "CLEAN":
        return (f"Claim {claim.claim_id} by {who} falls within expected cost and utilization "
                f"baselines. No rule violations were triggered.")
    detail = " ".join(reasons) if reasons else "Flagged by the dataset fraud label."
    return (f"{who} billed CPT {claim.cpt_code} for ${claim.claim_amount:,.2f} "
            f"({ratio:.1f}x the benchmark) for member {claim.member_id} in {claim.location}. {detail}")


def _build(limit_clean: int = 15) -> Dict[str, Any]:
    claims = data_service.claims
    by_member = defaultdict(list)
    for c in claims:
        by_member[c.member_id].append(c)

    flagged_cases, clean_cases = [], []
    flagged_exposure = 0.0
    total_exposure = sum(c.claim_amount for c in claims)

    for c in claims:
        rules = evaluate_claim_rules(c, by_member[c.member_id])
        flag = _detect_flag(rules, c.fraud_flag or "CLEAN")
        if flag == "CLEAN" and len(clean_cases) >= limit_clean:
            continue
        anomaly = ml_service.predict(c)
        cent = graph_service.get_node_risk(c.provider_npi)
        case = create_siu_case(c, rules, anomaly, GraphRisk(degree_centrality=round(cent, 6), is_ring_hub=cent > 0.05))
        base = CPT_BASELINE_BENCHMARK.get(c.cpt_code, 150.0)
        ratio = c.claim_amount / base
        policies = get_relevant_policies(f"{flag.replace('_', ' ')} {' '.join(rules.flag_reasons)}", max_results=1)
        label, citation = FLAG_META.get(flag, ("Baseline", "Baseline controls"))
        score = case.composite_risk.composite_score
        item = {
            "id": case.case_id,
            "claim_id": c.claim_id,
            "provider": c.provider_name or f"NPI {c.provider_npi}",
            "npi": c.provider_npi,
            "member": c.member_id,
            "facility": c.facility_id or "UNKNOWN",
            "amount": c.claim_amount,
            "cpt": c.cpt_code,
            "city": c.location,
            "timestamp": c.timestamp.strftime("%Y-%m-%d %H:%M"),
            "flag": flag,
            "score": score,
            "risk_tier": case.composite_risk.risk_tier,
            "confidence": round(min(0.99, 0.5 + score / 2), 3),
            "variance": min(100, round(ratio * 25)),
            "policy": policies[0] if policies else "",
            "citation": citation,
            "brief": _brief(c, flag, rules.flag_reasons, ratio),
            "flag_reasons": rules.flag_reasons,
        }
        if flag == "CLEAN":
            clean_cases.append(item)
        else:
            flagged_cases.append(item)
            flagged_exposure += c.claim_amount

    flagged_cases.sort(key=lambda x: x["score"], reverse=True)
    hubs = graph_service.get_top_centrality(top_n=10)
    return {
        "metrics": {
            "total_analyzed": len(claims),
            "flagged_claims": len(flagged_cases),
            "flagged_exposure": round(flagged_exposure, 2),
            "flagged_exposure_pct": round(100 * flagged_exposure / total_exposure, 1) if total_exposure else 0.0,
            "active_patterns": len({c["flag"] for c in flagged_cases}),
            "high_risk_hubs": sum(1 for h in hubs if h.node_type == "PROVIDER" and h.degree_centrality > 0.01),
        },
        "flagged_cases": flagged_cases,
        "clean_cases": clean_cases,
    }


@router.get("")
@router.get("/")
def get_dashboard(limit: int = Query(25, ge=1, le=200, description="Max cases returned per fraud pattern")) -> Dict[str, Any]:
    """Metrics + prioritized claim queue for the SIU workspace (cached)."""
    key = f"n={len(data_service.claims)}"
    if _cache.get("key") != key:
        _cache["key"] = key
        _cache["data"] = _build()
    d = _cache["data"]
    # Take the top cases *per pattern* so every queue tab is populated
    # (a global top-N would be dominated by the highest-scoring pattern).
    per_flag: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in d["flagged_cases"]:  # already sorted by score desc
        if len(per_flag[c["flag"]]) < limit:
            per_flag[c["flag"]].append(c)
    flagged = sorted((c for v in per_flag.values() for c in v), key=lambda x: x["score"], reverse=True)
    return {"metrics": d["metrics"], "cases": flagged + d["clean_cases"]}
