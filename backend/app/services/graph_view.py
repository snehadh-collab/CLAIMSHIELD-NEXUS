"""Case-level entity-network view built directly from the stored claims.

The global graph in graph_analytics collapses repeated member<->provider claims into one edge, so the
per-case view is derived from the claim list instead. Edges therefore carry true claim counts and
billed totals, and any claim submitted through the API appears here too.
"""
from collections import defaultdict
from typing import Dict, List, Optional

from app.models.schemas import Claim, RuleFlags

MAX_MEMBERS = 25
MAX_FACILITIES = 8
MAX_PEERS = 8


def _r(x: float) -> float:
    return round(x, 2)


def build_provider_graph(
    provider_npi: str,
    case_id: str,
    claims_by_provider: Dict[str, List[Claim]],
    claims_by_member: Dict[str, List[Claim]],
    rule_map: Dict[str, RuleFlags],
    provider_names: Dict[str, str],
    provider_risk: Dict[str, float],
    provider_case_ids: Dict[str, str],
) -> Dict:
    own = claims_by_provider.get(provider_npi, [])

    def flagged(c: Claim) -> bool:
        f = rule_map.get(c.claim_id)
        return bool(f and f.flag_count)

    # --- members of this provider --------------------------------------------------
    by_member: Dict[str, List[Claim]] = defaultdict(list)
    for c in own:
        by_member[c.member_id].append(c)

    def member_rank(item):
        mid, mclaims = item
        other_providers = {x.provider_npi for x in claims_by_member.get(mid, []) if x.provider_npi != provider_npi}
        return (
            any(flagged(c) for c in mclaims),
            len(other_providers),
            sum(c.claim_amount for c in mclaims),
        )

    members_sorted = sorted(by_member.items(), key=member_rank, reverse=True)
    shown_members = dict(members_sorted[:MAX_MEMBERS])

    # --- facilities ----------------------------------------------------------------
    by_fac: Dict[str, List[Claim]] = defaultdict(list)
    for c in own:
        if c.facility_id:
            by_fac[c.facility_id].append(c)
    fac_sorted = sorted(by_fac.items(), key=lambda kv: (sum(c.claim_amount for c in kv[1]), len(kv[1])), reverse=True)
    shown_facilities = dict(fac_sorted[:MAX_FACILITIES])

    # --- peer providers reached through shared members ------------------------------
    peer_members: Dict[str, Dict[str, List[Claim]]] = defaultdict(lambda: defaultdict(list))
    all_peer_npis = set()
    for mid in by_member:
        for c in claims_by_member.get(mid, []):
            if c.provider_npi != provider_npi:
                all_peer_npis.add(c.provider_npi)
    for mid in shown_members:
        for c in claims_by_member.get(mid, []):
            if c.provider_npi != provider_npi:
                peer_members[c.provider_npi][mid].append(c)
    peers_sorted = sorted(
        peer_members.items(),
        key=lambda kv: (len(kv[1]), provider_risk.get(kv[0], 0.0)),
        reverse=True,
    )[:MAX_PEERS]
    shown_peers = dict(peers_sorted)

    nodes: List[Dict] = []
    edges: List[Dict] = []

    def prov_node(npi: str, claims: List[Claim], is_target: bool) -> Dict:
        risk = provider_risk.get(npi, 0.0)
        return {
            "id": f"PROV_{npi}",
            "label": provider_names.get(npi) or f"Provider {npi}",
            "type": "PROVIDER",
            "color": "#008751" if is_target else ("#c0392b" if risk >= 0.7 else "#8FA29E"),
            "is_target": is_target,
            "provider_npi": npi,
            "case_id": provider_case_ids.get(npi),
            "claim_count": len(claims),
            "total_billed": _r(sum(c.claim_amount for c in claims)),
            "risk": int(round(risk * 100)),
            "flagged": any(flagged(c) for c in claims),
        }

    nodes.append(prov_node(provider_npi, own, True))

    for mid, mclaims in shown_members.items():
        nodes.append({
            "id": f"MEM_{mid}", "label": mid, "type": "MEMBER", "color": "#8FA29E", "is_target": False,
            "claim_count": len(claims_by_member.get(mid, [])),
            "total_billed": _r(sum(c.claim_amount for c in claims_by_member.get(mid, []))),
            "flagged": any(flagged(c) for c in mclaims),
        })
        edges.append(_edge(f"MEM_{mid}", f"PROV_{provider_npi}", "BILLED_TO", mclaims, flagged))

    for fid, fclaims in shown_facilities.items():
        nodes.append({
            "id": f"FAC_{fid}", "label": fid, "type": "FACILITY", "color": "#13583B", "is_target": False,
            "claim_count": len(fclaims),
            "total_billed": _r(sum(c.claim_amount for c in fclaims)),
            "flagged": any(flagged(c) for c in fclaims),
        })
        edges.append(_edge(f"PROV_{provider_npi}", f"FAC_{fid}", "OPERATES_AT", fclaims, flagged))

    for npi, per_member in shown_peers.items():
        peer_claims = claims_by_provider.get(npi, [])
        nodes.append(prov_node(npi, peer_claims, False))
        for mid, mclaims in per_member.items():
            edges.append(_edge(f"MEM_{mid}", f"PROV_{npi}", "BILLED_TO", mclaims, flagged))

    degree: Dict[str, int] = defaultdict(int)
    for e in edges:
        degree[e["source"]] += 1
        degree[e["target"]] += 1
    for n in nodes:
        n["degree"] = degree[n["id"]]

    suspicious = sum(1 for e in edges if e["flagged"])
    return {
        "case_id": case_id,
        "provider_npi": provider_npi,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "nodes": len(nodes),
            "relationships": len(edges),
            "flagged_relationships": suspicious,
            "members_total": len(by_member),
            "members_shown": len(shown_members),
            "facilities_total": len(by_fac),
            "facilities_shown": len(shown_facilities),
            "peer_providers_total": len(all_peer_npis),
            "peer_providers_shown": len(shown_peers),
            "truncated": len(shown_members) < len(by_member) or len(shown_facilities) < len(by_fac) or len(shown_peers) < len(all_peer_npis),
            "note": "Edges are billing relationships derived from claims. A flagged edge carries at least one claim that triggered a rule; shared members are leads, not proof of collusion.",
        },
    }


def _edge(source: str, target: str, label: str, claims: List[Claim], flagged) -> Dict:
    flagged_claims = [c for c in claims if flagged(c)]
    return {
        "source": source,
        "target": target,
        "label": label,
        "claim_id": (flagged_claims or claims)[-1].claim_id if claims else "",
        "claim_count": len(claims),
        "amount": _r(sum(c.claim_amount for c in claims)),
        "flagged": bool(flagged_claims),
    }
