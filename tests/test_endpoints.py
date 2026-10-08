from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app
from app.config import settings
from app.services.data_service import data_service
from app.services.graph_service import graph_service

def test_health_check():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "online"

def test_impossible_geography_rule():
    with TestClient(app) as client:
        now = datetime.now()
        c1 = {
            "claim_id": "TEST-1",
            "provider_npi": "NPI-A",
            "member_id": "MEM-IMPOSSIBLE",
            "cpt_code": "99214",
            "claim_amount": 150.00,
            "timestamp": now.isoformat(),
            "location": "Chennai",
            "diagnosis_code": "R05"
        }
        client.post("/api/v1/analyze", json=c1)

        c2 = {
            "claim_id": "TEST-2",
            "provider_npi": "NPI-B",
            "member_id": "MEM-IMPOSSIBLE",
            "cpt_code": "99214",
            "claim_amount": 150.00,
            "timestamp": (now + timedelta(minutes=10)).isoformat(),
            "location": "Delhi",
            "diagnosis_code": "R05"
        }
        res = client.post("/api/v1/analyze", json=c2)
        assert res.status_code == 200
        data = res.json()
        assert data["rule_flags"]["impossible_geography"] is True

def test_dataset_regeneration_refreshes_analytics(tmp_path, monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
        monkeypatch.setattr(settings, "CLAIMS_CSV", str(tmp_path / "synthetic_claims.csv"))
        response = client.post("/api/v1/claims/generate?num_claims=100")

    assert response.status_code == 200
    assert response.json()["analytics_refreshed"] is True
    assert response.json()["loaded_memory_count"] == 100
    assert response.json()["generated_count"] == 100
    expected_nodes = (
        len({claim.provider_npi for claim in data_service.claims})
        + len({claim.member_id for claim in data_service.claims})
        + len({claim.facility_id for claim in data_service.claims})
    )
    assert graph_service.G.number_of_nodes() == expected_nodes
