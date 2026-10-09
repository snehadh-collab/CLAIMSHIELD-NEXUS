"""Investigator action workflow: validates a decision, updates persisted case state and appends the
audit entry in a single SQLite transaction.

Action semantics (see integration_audit.md):
  APPROVE_SIU   -> status APPROVED          investigator approves the findings
  REQUEST_INFO  -> status PENDING_RECORDS   medical records requested from the provider
  REFER_SIU     -> status REFERRED_TO_SIU   case referred to the SIU (record only; no external delivery exists)
  DISMISS       -> status DISMISSED         false positive; also releases any payment hold; terminal
  PAUSE_PAYMENT -> payment_hold = true      status unchanged (a hold is independent of the review status)
Payment holds are a recorded decision flag only: no payment system is integrated.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from app.services import audit_ledger, persistence

STATUS_FOR_ACTION = {
    "APPROVE_SIU": "APPROVED",
    "REQUEST_INFO": "PENDING_RECORDS",
    "REFER_SIU": "REFERRED_TO_SIU",
    "DISMISS": "DISMISSED",
}


class WorkflowConflict(Exception):
    """The action is not allowed in the case's current state (HTTP 409)."""


def _current_state(case_id: str) -> Tuple[str, bool]:
    rows = persistence.query("SELECT status, payment_hold FROM case_state WHERE case_id=?", (case_id,))
    if rows:
        return rows[0]["status"], bool(rows[0]["payment_hold"])
    return "OPEN", False


def apply_action(case_id: str, action: str, investigator_id: str, notes: str) -> Dict[str, Any]:
    with persistence._lock:
        status, hold = _current_state(case_id)
        if status == "DISMISSED":
            raise WorkflowConflict("This case was dismissed as a false positive; no further actions are allowed.")

        new_status, new_hold = status, hold
        if action == "PAUSE_PAYMENT":
            if hold:
                raise WorkflowConflict("A payment hold is already active for this case.")
            new_hold = True
        else:
            target = STATUS_FOR_ACTION[action]
            if target == status:
                raise WorkflowConflict(f"This case is already in status {target}.")
            new_status = target
            if action == "DISMISS":
                new_hold = False

        ts = datetime.now(timezone.utc).isoformat()
        db = persistence.get_db()
        cur = db.execute(
            "INSERT INTO audit_events (case_id, action, investigator_id, notes, timestamp, previous_status, new_status, payment_hold) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (case_id, action, investigator_id, notes, ts, status, new_status, int(new_hold)),
        )
        db.execute(
            "INSERT INTO case_state (case_id, status, payment_hold, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(case_id) DO UPDATE SET status=excluded.status, payment_hold=excluded.payment_hold, updated_at=excluded.updated_at",
            (case_id, new_status, int(new_hold), ts),
        )
        db.commit()
        row = persistence.query("SELECT * FROM audit_events WHERE audit_id=?", (cur.lastrowid,))[0]
        return {
            "audit_entry": audit_ledger._row_to_entry(row),
            "case": {"case_id": case_id, "status": new_status, "payment_hold": new_hold},
        }


def set_monitoring(case_id: str, provider_npi: str, enabled: bool, investigator_id: str, notes: str) -> Dict[str, Any]:
    with persistence._lock:
        status, hold = _current_state(case_id)
        existing = persistence.query("SELECT enabled FROM watchlist WHERE provider_npi=?", (provider_npi,))
        if existing and bool(existing[0]["enabled"]) == enabled:
            raise WorkflowConflict("Monitoring is already " + ("enabled" if enabled else "disabled") + " for this provider.")
        if not existing and not enabled:
            raise WorkflowConflict("Monitoring is not enabled for this provider.")
        ts = datetime.now(timezone.utc).isoformat()
        db = persistence.get_db()
        db.execute(
            "INSERT INTO watchlist (provider_npi, enabled, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(provider_npi) DO UPDATE SET enabled=excluded.enabled, updated_at=excluded.updated_at",
            (provider_npi, int(enabled), ts),
        )
        cur = db.execute(
            "INSERT INTO audit_events (case_id, action, investigator_id, notes, timestamp, previous_status, new_status, payment_hold) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (case_id, "MONITOR_PROVIDER" if enabled else "STOP_MONITORING", investigator_id,
             notes or ("Provider added to watchlist" if enabled else "Provider removed from watchlist"), ts, status, status, int(hold)),
        )
        db.commit()
        row = persistence.query("SELECT * FROM audit_events WHERE audit_id=?", (cur.lastrowid,))[0]
        return {"provider_npi": provider_npi, "monitored": enabled, "audit_entry": audit_ledger._row_to_entry(row)}
