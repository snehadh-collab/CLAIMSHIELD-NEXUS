from fastapi.testclient import TestClient
from app.main import app

def test_full_integration_pipeline():
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/")
        assert res.status_code == 200
        assert res.json()["status"] == "online"

        # 2. Claims list
        res = client.get("/api/v1/claims/?limit=10")
        assert res.status_code == 200
        claims = res.json()
        assert len(claims) > 0
        sample_claim = claims[0]

        # 3. Analyze claim
        res = client.post("/api/v1/analyze/", json=sample_claim)
        assert res.status_code == 200
        analysis = res.json()
        assert "composite_risk" in analysis
        assert "rule_flags" in analysis
        assert "anomaly_score" in analysis

        # 4. SIU Queue
        res = client.get("/api/v1/siu/queue?limit=10")
        assert res.status_code == 200
        queue = res.json()
        assert len(queue) > 0
        top_case = queue[0]
        case_id = top_case["case_id"]

        # 5. Graph Centrality Hubs
        res = client.get("/api/v1/graph/centrality?top_n=5")
        assert res.status_code == 200
        hubs = res.json()
        assert len(hubs) > 0

        # 6. Graph Subgraph for Provider
        provider_npi = top_case["claim"]["provider_npi"]
        res = client.get(f"/api/v1/graph/{provider_npi}")
        assert res.status_code == 200
        graph_data = res.json()
        assert graph_data["total_nodes"] > 0

        # 7. Financial Exposure Forecast
        res = client.get(f"/api/v1/cases/{case_id}/forecast")
        assert res.status_code == 200
        forecast = res.json()
        assert "projected_30day_exposure" in forecast

        # 8. Copilot Context
        res = client.get(f"/api/v1/copilot/context/{case_id}")
        assert res.status_code == 200
        context = res.json()
        assert "relevant_policies" in context

        # 9. Copilot Brief Generation
        brief_req = {
            "case_id": case_id,
            "claim_details": context["claim_summary"],
            "flagged_rules": context["flagged_rules"]
        }
        res = client.post("/api/v1/copilot/brief", json=brief_req)
        assert res.status_code == 200
        brief = res.json()
        assert brief["case_id"] == case_id

        # 10. Copilot Chat
        chat_req = {
            "case_id": case_id,
            "user_query": "Why was this claim flagged for upcoding?"
        }
        res = client.post("/api/v1/copilot/chat", json=chat_req)
        assert res.status_code == 200
        chat = res.json()
        assert "response" in chat

        # 11. Record Human-in-the-loop Audit Action
        action_req = {
            "case_id": case_id,
            "action": "PAYMENT_HOLD",
            "investigator_id": "SIU-LEAD-01",
            "notes": "Verified phantom provider NPI pattern. Flagged for payment block."
        }
        res = client.post(f"/api/v1/cases/{case_id}/action", json=action_req)
        assert res.status_code == 200
        rec_action = res.json()
        assert rec_action["action"] == "PAYMENT_HOLD"

        # 12. Audit Trail
        res = client.get(f"/api/v1/cases/{case_id}/audit")
        assert res.status_code == 200
        audit = res.json()
        assert len(audit["actions"]) >= 1
        assert audit["actions"][0]["action"] == "PAYMENT_HOLD"
