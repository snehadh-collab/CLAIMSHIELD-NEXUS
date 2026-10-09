from app.services.graph_analytics import detect_coordinated_fraud_rings, export_case_graph_json


def test_siu_queue_ranking(queue):
    assert len(queue) >= 200
    scores = [c["composite_risk_score"] for c in queue]
    assert scores == sorted(scores, reverse=True)


def test_queue_is_built_from_the_real_dataset(queue):
    ids = {c["case_id"] for c in queue}
    assert {"CASE-1999999999", "CASE-1888888888", "CASE-1777777777"} <= ids
    top3 = {c["case_id"] for c in queue[:3]}
    assert top3 == {"CASE-1999999999", "CASE-1888888888", "CASE-1777777777"}
    first = queue[0]
    assert first["provider_name"] and first["claim_count"] > 0 and first["status"] == "OPEN"


def test_financial_forecast_by_npi_and_case_id(client):
    for ident in ("1777777777", "CASE-1777777777"):
        data = client.get(f"/api/v1/cases/{ident}/forecast").json()
        assert data["day_90_exposure"] >= data["day_60_exposure"] >= data["day_30_exposure"] > 0
        assert data["claim_count"] > 0 and data["history"]
    assert client.get("/api/v1/cases/NOPE/forecast").status_code == 404


def test_forecast_does_not_extrapolate_a_one_day_burst(client):
    """Teleport provider: 20 claims inside one hour must not become a six-figure 90-day loss."""
    data = client.get("/api/v1/cases/CASE-1888888888/forecast").json()
    assert data["window_days_used"] >= 30
    assert data["day_90_exposure"] < 3 * data["total_billed"]


def test_graph_cluster_and_fraud_ring_detection():
    G, analysis, rings = detect_coordinated_fraud_rings()
    assert len(rings) > 0
    phantom = analysis["PROV_1999999999"]
    assert phantom["risk_color"] in ["RED", "AMBER"]
    assert phantom["composite_centrality"] > 0.005


def test_case_graph_json_export_structure_legacy():
    G, _, _ = detect_coordinated_fraud_rings()
    payload = export_case_graph_json(G, case_id="CLM-GEO-CHN-0")
    assert payload["nodes"] and payload["edges"] and "color" in payload["nodes"][0]
    assert all(n["label"] != n["id"] for n in payload["nodes"] if n["type"] == "PROVIDER")  # real names, not raw IDs


def test_graph_endpoint_is_case_specific(client):
    a = client.get("/api/v1/graph/export/CASE-1777777777").json()
    b = client.get("/api/v1/graph/export/CASE-1888888888").json()
    target_a = [n for n in a["nodes"] if n["is_target"]][0]
    target_b = [n for n in b["nodes"] if n["is_target"]][0]
    assert target_a["id"] == "PROV_1777777777" and target_b["id"] == "PROV_1888888888"
    assert target_a["label"].startswith("Dr. Synthetic-C")
    assert {n["id"] for n in a["nodes"]} != {n["id"] for n in b["nodes"]}
    assert a["stats"]["flagged_relationships"] > 0
    node_ids = {n["id"] for n in a["nodes"]}
    assert all(e["source"] in node_ids and e["target"] in node_ids for e in a["edges"])


def test_graph_endpoint_accepts_claim_id_and_404s_unknown(client):
    by_claim = client.get("/api/v1/graph/export/CLM-GEO-CHN-0").json()
    assert by_claim["case_id"] == "CASE-1888888888"
    assert client.get("/api/v1/graph/export/does-not-exist").status_code == 404
