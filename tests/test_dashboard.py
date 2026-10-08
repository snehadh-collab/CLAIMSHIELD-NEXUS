from fastapi.testclient import TestClient
from app.main import app


def test_dashboard_endpoint():
    with TestClient(app) as client:
        r = client.get("/api/v1/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert data["metrics"]["total_analyzed"] >= 1000
        assert data["metrics"]["flagged_claims"] > 0
        assert any(c["flag"] != "CLEAN" for c in data["cases"])
        first = data["cases"][0]
        for k in ("id", "provider", "npi", "member", "facility", "amount", "flag", "score", "brief", "policy"):
            assert k in first


def test_every_pattern_tab_is_populated():
    with TestClient(app) as client:
        flags = {c["flag"] for c in client.get("/api/v1/dashboard").json()["cases"]}
        assert {"PHANTOM_BILLING", "UPCODING", "IMPOSSIBLE_GEOGRAPHY", "CLEAN"} <= flags
