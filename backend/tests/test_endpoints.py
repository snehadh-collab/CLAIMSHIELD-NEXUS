import uuid
from datetime import datetime, timedelta, timezone


def _claim(**over):
    base = {
        "claim_id": f"T-{uuid.uuid4().hex[:8]}",
        "provider_npi": "1000000081",
        "member_id": f"MEM-T-{uuid.uuid4().hex[:6]}",
        "cpt_code": "99214",
        "claim_amount": 150.0,
        "timestamp": "2026-07-01T10:00:00Z",
        "location": "Chennai",
        "diagnosis_code": "R05",
    }
    base.update(over)
    return base


def test_health_reports_real_state(client):
    body = client.get("/").json()
    assert body["status"] == "online"
    assert body["claims_loaded"] >= 4950
    assert body["cases"] >= 200
    assert body["ai_configured"] is False  # tests run without a key


def test_analyze_is_dry_run_by_default(client):
    claim = _claim()
    res = client.post("/api/v1/analyze", json=claim)
    assert res.status_code == 200
    data = res.json()
    assert data["persisted"] is False
    assert 0.0 <= data["composite_risk_score"] <= 1.0
    assert data["case_id"] == "CASE-1000000081"
    # not stored: persisting the same ID afterwards still works
    assert client.post("/api/v1/analyze?persist=true", json=claim).status_code == 200


def test_impossible_geography_rule_with_persisted_claim(client):
    member = f"MEM-GEO-{uuid.uuid4().hex[:6]}"
    t = datetime(2026, 7, 2, 9, 0, tzinfo=timezone.utc)
    c1 = _claim(member_id=member, timestamp=t.isoformat(), location="Chennai")
    c2 = _claim(member_id=member, timestamp=(t + timedelta(minutes=10)).isoformat(), location="Delhi", provider_npi="1000000194")
    assert client.post("/api/v1/analyze?persist=true", json=c1).status_code == 200
    res = client.post("/api/v1/analyze", json=c2)
    assert res.status_code == 200
    assert res.json()["rule_flags"]["impossible_geography"] is True


def test_upcoding_rule(client):
    res = client.post("/api/v1/analyze", json=_claim(cpt_code="99215", claim_amount=1200.0))
    assert res.json()["rule_flags"]["upcoding_anomaly"] is True


def test_mixed_naive_and_aware_timestamps_do_not_crash_the_backend(client):
    """Regression for audit D-01: one aware timestamp used to poison the queue permanently."""
    member = f"MEM-TZ-{uuid.uuid4().hex[:6]}"
    aware = _claim(member_id=member, timestamp="2026-07-03T00:00:00Z")
    naive = _claim(member_id=member, timestamp="2026-07-03T00:01:00")
    assert client.post("/api/v1/analyze?persist=true", json=aware).status_code == 200
    assert client.post("/api/v1/analyze?persist=true", json=naive).status_code == 200
    assert client.get("/api/v1/siu/queue").status_code == 200
    assert client.get("/api/v1/cases/CASE-1000000081/forecast").status_code == 200
    assert client.get("/api/v1/copilot/context/CASE-1000000081").status_code == 200


def test_analyze_validation(client):
    assert client.post("/api/v1/analyze", json=_claim(claim_amount=-5)).status_code == 422
    assert client.post("/api/v1/analyze", json=_claim(claim_amount=0)).status_code == 422
    assert client.post("/api/v1/analyze", json=_claim(cpt_code="")).status_code == 422
    assert client.post("/api/v1/analyze", json=_claim(diagnosis_code="")).status_code == 422
    bad = _claim(); del bad["location"]
    assert client.post("/api/v1/analyze", json=bad).status_code == 422


def test_persist_duplicate_claim_id_conflicts(client):
    claim = _claim()
    assert client.post("/api/v1/analyze?persist=true", json=claim).status_code == 200
    assert client.post("/api/v1/analyze?persist=true", json=claim).status_code == 409


def test_persisted_claim_for_new_provider_creates_a_case(client):
    npi = f"9{uuid.uuid4().int % 10**9:09d}"
    assert client.post("/api/v1/analyze?persist=true", json=_claim(provider_npi=npi)).json()["case_id"] == f"CASE-{npi}"
    assert any(c["case_id"] == f"CASE-{npi}" for c in client.get("/api/v1/siu/queue").json())
