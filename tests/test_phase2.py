from fastapi.testclient import TestClient
from datetime import datetime
from app.main import app

client = TestClient(app)

def test_siu_queue_ranking():
    response = client.get("/api/v1/siu/queue")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) > 0
    
    first_score = cases[0]["composite_risk_score"]
    second_score = cases[1]["composite_risk_score"]
    assert first_score >= second_score

def test_financial_forecast():
    # 1. Post a test claim to guarantee NPI-999 exists in memory
    test_claim = {
        "claim_id": "CLM-FORECAST-001",
        "provider_npi": "NPI-999",
        "member_id": "MEM-666",
        "cpt_code": "99215",
        "claim_amount": 5000.0,
        "timestamp": datetime.now().isoformat(),
        "location": "Mumbai",
        "diagnosis_code": "Z00"
    }
    post_res = client.post("/api/v1/analyze", json=test_claim)
    assert post_res.status_code == 200

    # 2. Test forecast endpoint
    response = client.get("/api/v1/cases/NPI-999/forecast")
    assert response.status_code == 200
    data = response.json()
    assert "day_30_exposure" in data
    assert "day_60_exposure" in data
    assert "day_90_exposure" in data
    assert data["day_90_exposure"] >= data["day_30_exposure"]