import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_copilot_context_payload_and_latency():
    # 1. Fetch active queue case ID
    queue_res = client.get("/api/v1/siu/queue")
    assert queue_res.status_code == 200
    cases = queue_res.json()
    assert len(cases) > 0
    
    target_case_id = cases[0]["case_id"]

    # 2. Measure response time for context aggregation
    start_time = time.time()
    res = client.get(f"/api/v1/copilot/context/{target_case_id}")
    elapsed_ms = (time.time() - start_time) * 1000

    assert res.status_code == 200
    data = res.json()
    
    # 3. Assert payload structure
    assert data["case_id"] == target_case_id
    assert "composite_risk_score" in data
    assert "projected_90d_loss" in data
    assert len(data["policy_context_paragraphs"]) >= 1

    # 4. Assert performance benchmark (< 100ms)
    assert elapsed_ms < 100.0