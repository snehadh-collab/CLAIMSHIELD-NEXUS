"""Read-side builders: case detail, provider profile, knowledge, search, stats, copilot context.

All numbers are derived from the stored claims, rule/ML results, graph centrality and the audit
ledger. Nothing here is hard-coded demo data.
"""
import statistics
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.models.schemas import CopilotContextPayload, SIUCase
from app.services import audit_ledger
from app.services.context_aggregator import build_copilot_context
from app.services.graph_view import build_provider_graph
from app.services.policy_rag import retrieve_policy_passages
from app.services.rules_engine import RULE_LABELS, rule_codes
from app.services.siu_ranking import case_id_for
from app.services.store import CaseStore

STATUS_LABELS = {
    "OPEN": "Open",
    "APPROVED": "Findings Approved",
    "PENDING_RECORDS": "Pending Records",
    "REFERRED_TO_SIU": "Referred to SIU",
    "DISMISSED": "Dismissed (False Positive)",
}

# What the policy corpus should be asked for, per rule category.
POLICY_QUERY = {
    "DUPLICATE_BILLING": "duplicate billing same CPT procedure code same member same provider window",
    "IMPOSSIBLE_GEOGRAPHY": "impossible travel timing same member two geographically distinct facility locations 2-hour window",
    "UPCODING": "upcoding highest-tier evaluation management CPT 99215 exceeding 4x peer group baseline SIU audit",
}


# ---------------------------------------------------------------------------------- helpers
def _claim_row(store: CaseStore, c) -> Dict[str, Any]:
    flags = store.rule_results.get(c.claim_id)
    ml = store.anomaly_results.get(c.claim_id)
    return {
        "claim_id": c.claim_id,
        "timestamp": c.timestamp.isoformat(),
        "cpt_code": c.cpt_code,
        "claim_amount": round(c.claim_amount, 2),
        "member_id": c.member_id,
        "facility_id": c.facility_id,
        "location": c.location,
        "rule_codes": rule_codes(flags) if flags else [],
        "reasons": flags.flag_reasons if flags else [],
        "ml_score": ml.ml_score if ml else 0.0,
        "is_anomalous": bool(ml and ml.is_anomalous),
        "risk": store.claim_risk(c),
        "dataset_label": store.dataset_labels.get(c.claim_id),
    }


def _findings(store: CaseStore, npi: str) -> List[Dict[str, Any]]:
    per_code: Dict[str, Dict[str, Any]] = {}
    for c in store.by_provider[npi]:
        flags = store.rule_results.get(c.claim_id)
        if not flags:
            continue
        for code in rule_codes(flags):
            entry = per_code.setdefault(code, {"code": code, "label": RULE_LABELS[code], "claim_count": 0, "claim_ids": [], "examples": []})
            entry["claim_count"] += 1
            if len(entry["claim_ids"]) < 20:
                entry["claim_ids"].append(c.claim_id)
        for reason in flags.flag_reasons:
            for code in rule_codes(flags):
                ex = per_code[code]["examples"]
                if reason not in ex and len(ex) < 3 and _reason_matches(code, reason):
                    ex.append(reason)
    result = sorted(per_code.values(), key=lambda e: e["claim_count"], reverse=True)
    for e in result:
        e["severity"] = "HIGH" if e["claim_count"] >= 3 else "MEDIUM"
    return result


def _reason_matches(code: str, reason: str) -> bool:
    key = {"DUPLICATE_BILLING": "Duplicate", "IMPOSSIBLE_GEOGRAPHY": "Impossible travel", "UPCODING": "benchmark"}[code]
    return key in reason


def policy_query_for(codes: List[str]) -> str:
    return " ".join(POLICY_QUERY[c] for c in codes if c in POLICY_QUERY)


def _scores(store: CaseStore, case: SIUCase) -> Dict[str, Any]:
    return {
        "composite": case.composite_risk_score,
        "formula": "0.3 × rule categories (of 3) + 0.3 × max claim ML anomaly + 0.4 × graph centrality",
        "components": {
            "rules": {"value": round(min(case.rule_flag_count / 3.0, 1.0), 4), "weight": 0.3, "categories": case.rule_flag_count},
            "ml": {"value": case.ml_anomaly_score, "weight": 0.3},
            "graph": {
                "value": case.graph_centrality,
                "weight": 0.4,
                "raw_centrality": round(store.centrality_raw.get(case.provider_npi, 0.0), 4),
                "graph_risk_color": store.graph_risk_color.get(case.provider_npi),
                "scaling": "raw PageRank/degree blend divided by the largest value in the dataset",
            },
        },
    }


def _rank_info(store: CaseStore, case: SIUCase) -> Dict[str, Any]:
    queue = store.queue()
    position = next((i for i, c in enumerate(queue) if c.case_id == case.case_id), 0) + 1
    return {"queue_position": position, "queue_size": len(queue)}


# ---------------------------------------------------------------------------------- case detail
def build_case_detail(store: CaseStore, case: SIUCase) -> Dict[str, Any]:
    npi = case.provider_npi
    claims = sorted(store.by_provider[npi], key=lambda c: c.timestamp, reverse=True)
    rows = [_claim_row(store, c) for c in claims]
    watch = store.watchlist()
    audit = audit_ledger.get_case_audit_history(case.case_id)
    return {
        "case": case.model_dump(),
        "status_label": STATUS_LABELS.get(case.status, case.status),
        "provider": {
            "npi": npi,
            "name": store.provider_names.get(npi),
            "claim_count": len(claims),
            "member_count": len({c.member_id for c in claims}),
            "facility_count": len({c.facility_id for c in claims if c.facility_id}),
            "first_claim_at": min(c.timestamp for c in claims).isoformat(),
            "last_claim_at": max(c.timestamp for c in claims).isoformat(),
            "average_claim": round(sum(c.claim_amount for c in claims) / len(claims), 2),
            "monitored": bool(watch.get(npi, False)),
        },
        "scores": _scores(store, case),
        "rule_findings": _findings(store, npi),
        "claims": rows,
        "forecast": store.exposure(npi).model_dump(),
        "audit_event_count": len(audit),
        **_rank_info(store, case),
    }


# ---------------------------------------------------------------------------------- policies
def build_case_policies(store: CaseStore, case: SIUCase) -> Dict[str, Any]:
    codes = case.rule_flags
    if not codes:
        return {
            "case_id": case.case_id,
            "query": "",
            "passages": [],
            "retrieval": "TF-IDF cosine similarity over the policy corpus (data/synthetic_policies.md)",
            "note": "No rule was triggered for this case, so no policy passage is cited. Risk comes from ML anomaly and graph signals only.",
        }
    passages = []
    seen = set()
    for code in codes:
        for p in retrieve_policy_passages(POLICY_QUERY[code], top_k=2):
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            passages.append({**p, "triggered_by": code, "triggered_by_label": RULE_LABELS[code]})
    return {
        "case_id": case.case_id,
        "query": policy_query_for(codes),
        "passages": passages,
        "retrieval": "TF-IDF cosine similarity over the policy corpus (data/synthetic_policies.md)",
        "note": "Passages are retrieved verbatim from the synthetic policy corpus; they are references, not legal conclusions.",
    }


# ---------------------------------------------------------------------------------- graph
def build_case_graph(store: CaseStore, case: SIUCase) -> Dict[str, Any]:
    provider_risk = {c.provider_npi: c.composite_risk_score for c in store.queue()}
    provider_case_ids = {npi: case_id_for(npi) for npi in store.by_provider}
    return build_provider_graph(
        case.provider_npi,
        case.case_id,
        store.by_provider,
        store.by_member,
        store.rule_results,
        store.provider_names,
        provider_risk,
        provider_case_ids,
    )


# ---------------------------------------------------------------------------------- provider profile
def build_provider_profile(store: CaseStore, case: SIUCase) -> Dict[str, Any]:
    npi = case.provider_npi
    claims = store.by_provider[npi]
    queue = store.queue()
    exposure = store.exposure(npi)
    window = max(exposure.window_days_used, 1.0)

    # Cohort comparison (all providers in the dataset)
    cohort_daily = [c.forecast.historical_daily_avg_claim for c in queue if c.forecast]
    cohort_avg_claim = statistics.mean(c.claim_amount for c in store.claims)
    median_daily = statistics.median(cohort_daily) if cohort_daily else 0.0
    own_daily = exposure.historical_daily_avg_claim
    vs_peer = ((own_daily - median_daily) / median_daily * 100.0) if median_daily else None

    # Relationships: other providers that bill the same members
    members = {c.member_id for c in claims}
    shared: Counter = Counter()
    for mid in members:
        for other in {x.provider_npi for x in store.by_member[mid]}:
            if other != npi:
                shared[other] += 1
    risk_by_npi = {c.provider_npi: c for c in queue}
    relationships = []
    for other, count in sorted(shared.items(), key=lambda kv: (kv[1], risk_by_npi[kv[0]].composite_risk_score), reverse=True)[:8]:
        o = risk_by_npi[other]
        relationships.append({
            "provider_npi": other,
            "provider_name": o.provider_name,
            "case_id": o.case_id,
            "shared_members": count,
            "composite_risk_score": o.composite_risk_score,
            "status": o.status,
        })

    cpt_mix = Counter(c.cpt_code for c in claims)
    watch = store.watchlist()
    decisions = audit_ledger.get_case_audit_history(case.case_id)
    return {
        "case_id": case.case_id,
        "provider_npi": npi,
        "provider_name": store.provider_names.get(npi),
        "status": case.status,
        "status_label": STATUS_LABELS.get(case.status, case.status),
        "payment_hold": case.payment_hold,
        "composite_risk_score": case.composite_risk_score,
        "rule_flags": case.rule_flags,
        "primary_finding": case.primary_finding,
        "monitored": bool(watch.get(npi, False)),
        "metrics": {
            "claim_count": len(claims),
            "total_billed": round(sum(c.claim_amount for c in claims), 2),
            "average_claim": round(sum(c.claim_amount for c in claims) / len(claims), 2),
            "cohort_average_claim": round(cohort_avg_claim, 2),
            "claims_per_day": round(len(claims) / window, 3),
            "billed_per_day": own_daily,
            "cohort_median_billed_per_day": round(median_daily, 2),
            "billed_per_day_vs_peer_pct": round(vs_peer, 1) if vs_peer is not None else None,
            "observation_window_days": exposure.window_days_used,
            "member_count": len(members),
            "facility_count": len({c.facility_id for c in claims if c.facility_id}),
            "cpt_mix": [{"cpt_code": k, "claims": v} for k, v in cpt_mix.most_common(5)],
        },
        "behaviors": _findings(store, npi),
        "forecast": exposure.model_dump(),
        "relationships": relationships,
        "decisions": decisions,
        **_rank_info(store, case),
    }


# ---------------------------------------------------------------------------------- knowledge
def _precedent_query(store: CaseStore, case: SIUCase) -> str:
    claims = store.by_provider[case.provider_npi]
    cpts = " ".join(c for c, _ in Counter(x.cpt_code for x in claims).most_common(2))
    cities = " ".join(c for c, _ in Counter(x.location for x in claims).most_common(1))
    return f"{' '.join(case.rule_flags)} CPT Code {cpts} Location {cities}"


def build_entities(graph: Dict[str, Any], limit: int = 12) -> List[Dict[str, Any]]:
    others = [n for n in graph["nodes"] if not n["is_target"]]
    others.sort(key=lambda n: (n.get("flagged", False), n["type"] == "PROVIDER", n.get("degree", 0), n.get("total_billed", 0)), reverse=True)
    return [
        {
            "id": n["id"], "type": n["type"], "label": n["label"], "claim_count": n["claim_count"],
            "total_billed": n["total_billed"], "flagged": n.get("flagged", False), "case_id": n.get("case_id"),
        }
        for n in others[:limit]
    ]


def build_synthesis(store: CaseStore, case: SIUCase, detail: Dict[str, Any], graph: Dict[str, Any]) -> str:
    name = store.provider_names.get(case.provider_npi) or f"Provider {case.provider_npi}"
    p = detail["provider"]
    if case.rule_flags:
        labels = ", ".join(RULE_LABELS[c].lower() for c in case.rule_flags)
        flagged = sum(1 for r in detail["claims"] if r["rule_codes"])
        body = f"{name} has {flagged} of {p['claim_count']} claims triggering rules ({labels})."
    else:
        body = f"{name} has no claims triggering a rule across {p['claim_count']} claims."
    s = graph["stats"]
    return (
        f"{body} Composite risk is {round(case.composite_risk_score * 100)}% (max claim ML anomaly "
        f"{round(case.ml_anomaly_score * 100)}%, graph centrality {round(case.graph_centrality * 100)}%). "
        f"The provider bills {p['member_count']} members at {p['facility_count']} facilities and shares members with "
        f"{s['peer_providers_total']} other providers. Current status: {STATUS_LABELS.get(case.status, case.status)}."
    )


def build_knowledge(store: CaseStore, case: SIUCase) -> Dict[str, Any]:
    detail = build_case_detail(store, case)
    graph = build_case_graph(store, case)
    policies = build_case_policies(store, case)
    precedents: List[Dict[str, Any]] = []
    precedent_note = None
    memory = store.memory
    if not case.rule_flags:
        precedent_note = "No rule was triggered, so there is no pattern to match against historical cases."
    elif memory is None:
        precedent_note = f"Historical case memory is unavailable ({store._memory_error})."
    else:
        own = {c.claim_id for c in store.by_provider[case.provider_npi]}
        per_provider: Dict[str, Dict[str, Any]] = {}
        for hit in memory.search_similar_precedents(_precedent_query(store, case), top_k=400):
            claim = store.claims_by_id.get(hit["case_id"])
            if not claim or hit["case_id"] in own or hit["match_score"] <= 0:
                continue
            if claim.provider_npi in per_provider:
                continue
            per_provider[claim.provider_npi] = {
                "case_id": case_id_for(claim.provider_npi),
                "provider_npi": claim.provider_npi,
                "provider_name": store.provider_names.get(claim.provider_npi),
                "example_claim_id": claim.claim_id,
                "match_score": hit["match_score"],
                "summary": hit["summary"],
                "dataset_label": store.dataset_labels.get(claim.claim_id),
            }
        precedents = list(per_provider.values())[:5]
    return {
        "case_id": case.case_id,
        "synthesis": {
            "text": build_synthesis(store, case, detail, graph),
            "source": "CASE_DATA",
            "note": "Assembled from this case's stored data. It is not LLM output; use the Copilot or the Executive Brief for AI-generated text.",
        },
        "findings": detail["rule_findings"],
        "policies": policies,
        "entities": build_entities(graph),
        "graph_stats": graph["stats"],
        "claims": detail["claims"][:50],
        "claim_count": detail["provider"]["claim_count"],
        "precedents": precedents,
        "precedent_note": precedent_note,
        "decisions": audit_ledger.get_case_audit_history(case.case_id),
    }


# ---------------------------------------------------------------------------------- search
def global_search(store: CaseStore, q: str, limit: int = 8) -> Dict[str, Any]:
    needle = (q or "").strip().lower()
    out: Dict[str, Any] = {"query": q, "cases": [], "claims": [], "policies": [], "precedents": []}
    if len(needle) < 2:
        return out
    queue = store.queue()
    for c in queue:
        hay = f"{c.case_id} {c.provider_npi} {c.provider_name or ''}".lower()
        if needle in hay:
            out["cases"].append(c.model_dump(exclude={"forecast"}))
            if len(out["cases"]) >= limit:
                break
    if len(needle) >= 3:
        for claim in store.claims:
            if needle in claim.claim_id.lower() or needle in claim.member_id.lower():
                out["claims"].append({
                    "claim_id": claim.claim_id, "member_id": claim.member_id, "provider_npi": claim.provider_npi,
                    "provider_name": store.provider_names.get(claim.provider_npi), "case_id": case_id_for(claim.provider_npi),
                    "cpt_code": claim.cpt_code, "claim_amount": round(claim.claim_amount, 2), "timestamp": claim.timestamp.isoformat(),
                })
                if len(out["claims"]) >= limit:
                    break
        out["policies"] = retrieve_policy_passages(q, top_k=3, min_score=0.12)
        memory = store.memory
        if memory is not None:
            seen = set()
            for hit in memory.search_similar_precedents(q, top_k=10):
                claim = store.claims_by_id.get(hit["case_id"])
                if hit["match_score"] >= 0.15 and claim and claim.provider_npi not in seen:
                    seen.add(claim.provider_npi)
                    out["precedents"].append({
                        "case_id": case_id_for(claim.provider_npi), "provider_name": store.provider_names.get(claim.provider_npi),
                        "example_claim_id": claim.claim_id, "match_score": hit["match_score"], "summary": hit["summary"],
                    })
                if len(out["precedents"]) >= 3:
                    break
    return out


# ---------------------------------------------------------------------------------- stats
def build_stats(store: CaseStore) -> Dict[str, Any]:
    queue = store.queue()
    flagged_claims = [c for c in store.claims if (store.rule_results.get(c.claim_id) and store.rule_results[c.claim_id].flag_count)]
    latest = max(c.timestamp for c in store.claims)
    earliest = min(c.timestamp for c in store.claims)
    w_start, p_start = latest - timedelta(days=30), latest - timedelta(days=60)

    def trend(selected) -> Dict[str, Any]:
        cur = sum(1 for c in selected if c.timestamp > w_start)
        prev = sum(1 for c in selected if p_start < c.timestamp <= w_start)
        pct = round((cur - prev) / prev * 100.0, 1) if prev else None
        return {"current": cur, "previous": prev, "change_pct": pct}

    critical = [c for c in queue if c.composite_risk_score >= 0.7]
    statuses = Counter(c.status for c in queue)
    return {
        "total_claims": len(store.claims),
        "total_cases": len(queue),
        "flagged_claims": len(flagged_claims),
        "critical_cases": len(critical),
        "elevated_cases": sum(1 for c in queue if 0.4 <= c.composite_risk_score < 0.7),
        "projected_90d_exposure_critical": round(sum(c.forecast.day_90_exposure for c in critical if c.forecast), 2),
        "projected_90d_exposure_all": round(sum(c.forecast.day_90_exposure for c in queue if c.forecast), 2),
        "active_payment_holds": sum(1 for c in queue if c.payment_hold),
        "status_counts": dict(statuses),
        "claims_trend": trend(store.claims),
        "flagged_claims_trend": trend(flagged_claims),
        "data_window": {"start": earliest.isoformat(), "end": latest.isoformat()},
        "trend_basis": "last 30 days of the dataset vs the 30 days before",
    }


# ---------------------------------------------------------------------------------- copilot context
def build_context(store: CaseStore, case: SIUCase) -> CopilotContextPayload:
    passages = build_case_policies(store, case)["passages"]
    return build_copilot_context(
        case_id=case.case_id,
        provider_npi=case.provider_npi,
        claims=store.claims,
        rule_map=store.rule_results,
        anomaly_map=store.anomaly_results,
        graph_centrality=case.graph_centrality,
        composite_risk_score=case.composite_risk_score,
        policy_snippets=[f"{p['id']} ({p['section_title']}): {p['text']}" for p in passages],
        provider_name=store.provider_names.get(case.provider_npi),
        status=case.status,
        payment_hold=case.payment_hold,
    )


def fact_sheet(ctx: CopilotContextPayload) -> str:
    """Plain-text case facts handed to the LLM (and used by the offline fallback)."""
    reasons = "; ".join(ctx.rule_flag_reasons[:8]) or "none"
    return (
        f"Case {ctx.case_id} · provider {ctx.provider_name or ctx.provider_npi} (NPI {ctx.provider_npi}) · "
        f"status {ctx.status}{' · payment hold ACTIVE' if ctx.payment_hold else ''}. "
        f"Total billed ${ctx.total_claim_amount:,.2f} across {len(ctx.associated_claim_ids)} claims. "
        f"Composite risk {ctx.composite_risk_score:.2f} (max claim ML anomaly {ctx.ml_anomaly_score:.2f}, graph centrality {ctx.graph_centrality_score:.2f}). "
        f"Rule categories triggered: {ctx.rule_flag_count}. Rule findings: {reasons}. "
        f"Projected 30-day billing ${ctx.projected_30d_loss:,.0f}, 90-day ${ctx.projected_90d_loss:,.0f} (linear run-rate)."
    )
