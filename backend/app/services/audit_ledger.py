"""Append-only audit ledger of investigator decisions, persisted in SQLite."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services import persistence


def _row_to_entry(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "audit_id": f"AUD-{row['audit_id']:06d}",
        "case_id": row["case_id"],
        "action": row["action"],
        "investigator_id": row["investigator_id"],
        "notes": row["notes"],
        "timestamp": row["timestamp"],
        "previous_status": row["previous_status"],
        "new_status": row["new_status"],
        "payment_hold": bool(row["payment_hold"]),
    }


def record_action(
    case_id: str,
    action: str,
    investigator_id: str,
    notes: str,
    previous_status: Optional[str] = None,
    new_status: Optional[str] = None,
    payment_hold: bool = False,
) -> Dict[str, Any]:
    """Appends an audit log entry for a case action decision and returns it."""
    ts = datetime.now(timezone.utc).isoformat()
    cur = persistence.execute(
        "INSERT INTO audit_events (case_id, action, investigator_id, notes, timestamp, previous_status, new_status, payment_hold) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (case_id, action, investigator_id, notes, ts, previous_status, new_status, int(payment_hold)),
    )
    row = persistence.query("SELECT * FROM audit_events WHERE audit_id=?", (cur.lastrowid,))[0]
    return _row_to_entry(row)


def get_case_audit_history(case_id: str) -> List[Dict[str, Any]]:
    """All audit entries for a case, oldest first."""
    rows = persistence.query("SELECT * FROM audit_events WHERE case_id=? ORDER BY audit_id ASC", (case_id,))
    return [_row_to_entry(r) for r in rows]


def get_recent_audit_events(limit: int = 20) -> List[Dict[str, Any]]:
    """Most recent audit entries across all cases, newest first."""
    rows = persistence.query("SELECT * FROM audit_events ORDER BY audit_id DESC LIMIT ?", (int(limit),))
    return [_row_to_entry(r) for r in rows]
