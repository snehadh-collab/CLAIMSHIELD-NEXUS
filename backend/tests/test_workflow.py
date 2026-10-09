"""Investigator actions: Approve, Pause Payment, Refer to SIU, Request Medical Records, Mark False Positive."""
import pytest


def _act(client, case_id, action, notes="Reviewed evidence.", inv="INV-007"):
    return client.post(f"/api/v1/cases/{case_id}/action", json={"action": action, "investigator_id": inv, "notes": notes})


def _case(client, case_id):
    return next(c for c in client.get("/api/v1/siu/queue").json() if c["case_id"] == case_id)


def test_unknown_case_is_404_and_writes_nothing(client):
    assert _act(client, "CASE-NOPE", "APPROVE_SIU").status_code == 404
    assert client.get("/api/v1/cases/CASE-NOPE/audit").status_code == 404


def test_invalid_action_and_blank_reason_rejected(client):
    assert _act(client, "CASE-1000000037", "DELETE_EVERYTHING").status_code == 422
    assert _act(client, "CASE-1000000037", "APPROVE_SIU", notes="   ").status_code == 422
    assert client.post("/api/v1/cases/CASE-1000000037/action", json={"action": "APPROVE_SIU"}).status_code == 422


def test_request_records_sets_pending_status(client):
    cid = "CASE-1000000102"
    res = _act(client, cid, "REQUEST_INFO", "Need itemised statements.")
    assert res.status_code == 200
    assert res.json()["case"]["status"] == "PENDING_RECORDS"
    assert _case(client, cid)["status"] == "PENDING_RECORDS"
    assert _act(client, cid, "REQUEST_INFO").status_code == 409  # already pending


def test_approve_sets_approved_status(client):
    cid = "CASE-1000000125"
    res = _act(client, cid, "APPROVE_SIU", "Evidence supports the findings.")
    assert res.json()["audit_entry"]["new_status"] == "APPROVED"
    assert _case(client, cid)["status"] == "APPROVED"


def test_refer_to_siu_sets_status(client):
    cid = "CASE-1000000168"
    res = _act(client, cid, "REFER_SIU", "Escalating for network review.")
    assert res.status_code == 200
    assert _case(client, cid)["status"] == "REFERRED_TO_SIU"
    assert _act(client, cid, "REFER_SIU").status_code == 409


def test_pause_payment_sets_hold_without_changing_status(client):
    cid = "CASE-1000000028"
    before = _case(client, cid)
    assert before["payment_hold"] is False
    res = _act(client, cid, "PAUSE_PAYMENT", "Hold pending review.")
    assert res.status_code == 200 and res.json()["case"]["payment_hold"] is True
    after = _case(client, cid)
    assert after["payment_hold"] is True and after["status"] == before["status"]
    assert _act(client, cid, "PAUSE_PAYMENT").status_code == 409
    audit = client.get(f"/api/v1/cases/{cid}/audit").json()
    assert audit["payment_hold"] is True
    assert audit["audit_trail"][-1]["action"] == "PAUSE_PAYMENT"


def test_dismiss_is_terminal_and_releases_payment_hold(client):
    cid = "CASE-1888888888"
    assert _act(client, cid, "PAUSE_PAYMENT").status_code == 200
    res = _act(client, cid, "DISMISS", "False positive after review.")
    assert res.json()["case"] == {"case_id": cid, "status": "DISMISSED", "payment_hold": False}
    assert _act(client, cid, "APPROVE_SIU").status_code == 409
    assert _act(client, cid, "PAUSE_PAYMENT").status_code == 409


def test_audit_trail_records_real_actions_in_order(client):
    cid = "CASE-1000000037"
    _act(client, cid, "REQUEST_INFO", "first", inv="INV-A")
    _act(client, cid, "APPROVE_SIU", "second", inv="INV-B")
    trail = client.get(f"/api/v1/cases/{cid}/audit").json()["audit_trail"]
    assert [e["action"] for e in trail] == ["REQUEST_INFO", "APPROVE_SIU"]
    assert [e["investigator_id"] for e in trail] == ["INV-A", "INV-B"]
    assert trail[1]["previous_status"] == "PENDING_RECORDS" and trail[1]["new_status"] == "APPROVED"
    assert trail[0]["audit_id"] != trail[1]["audit_id"]
    recent = client.get("/api/v1/audit?limit=5").json()["audit_trail"]
    assert recent[0]["audit_id"] == trail[1]["audit_id"]  # newest first


def test_ledger_is_append_only():
    import sqlite3
    from app.services import persistence

    with pytest.raises(sqlite3.DatabaseError):
        persistence.execute("DELETE FROM audit_events")
    with pytest.raises(sqlite3.DatabaseError):
        persistence.execute("UPDATE audit_events SET notes='x'")


def test_provider_monitoring_persists_and_is_audited(client):
    npi = "1000000081"
    assert client.get(f"/api/v1/providers/{npi}").json()["monitored"] is False
    res = client.put(f"/api/v1/providers/{npi}/monitoring", json={"enabled": True, "investigator_id": "INV-M"})
    assert res.status_code == 200 and res.json()["monitored"] is True
    assert client.get(f"/api/v1/providers/{npi}").json()["monitored"] is True
    assert client.put(f"/api/v1/providers/{npi}/monitoring", json={"enabled": True}).status_code == 409
    trail = client.get(f"/api/v1/cases/CASE-{npi}/audit").json()["audit_trail"]
    assert trail[-1]["action"] == "MONITOR_PROVIDER"
    assert client.put(f"/api/v1/providers/{npi}/monitoring", json={"enabled": False}).json()["monitored"] is False
    assert client.put("/api/v1/providers/NOPE/monitoring", json={"enabled": True}).status_code == 404
