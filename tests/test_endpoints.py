from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_impossible_geography_rule():
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