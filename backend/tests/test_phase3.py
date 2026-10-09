import time
from app.services.historical_memory import HistoricalCaseMemory


def test_copilot_context_payload_and_latency(client, queue):
    target = queue[0]["case_id"]
    client.get(f"/api/v1/copilot/context/{target}")  # warm
    start = time.time()
    res = client.get(f"/api/v1/copilot/context/{target}")
    elapsed_ms = (time.time() - start) * 1000
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == target
    assert data["projected_90d_loss"] > 0
    assert len(data["policy_context_paragraphs"]) >= 1  # retrieved, not hard-coded
    assert data["associated_claim_ids"]
    assert elapsed_ms < 150.0


def test_context_for_unknown_case_is_404_not_another_case(client):
    assert client.get("/api/v1/copilot/context/CASE-DOES-NOT-EXIST").status_code == 404


def test_historical_memory_search_precision():
    memory = HistoricalCaseMemory()
    results = memory.search_similar_precedents("Dr. Synthetic-A Phantom billing", top_k=3)
    assert results and results[0]["match_score"] > 0.1
    assert "Phantom" in results[0]["summary"] or "PHANTOM" in results[0]["summary"]
