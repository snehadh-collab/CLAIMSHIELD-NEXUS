"""SQLite persistence for investigator state: audit ledger, case status, watchlist, submitted claims.

Everything the investigators *do* is stored here so it survives a restart. The claim dataset itself
stays in `data/synthetic_claims.csv`. Standard library only (no new dependency).

Location: `CLAIMSHIELD_DB` env var, default `backend/data/claimshield.db`. Use `:memory:` for tests.
"""
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "claimshield.db")

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None
_conn_path: Optional[str] = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    audit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id         TEXT NOT NULL,
    action          TEXT NOT NULL,
    investigator_id TEXT NOT NULL,
    notes           TEXT NOT NULL DEFAULT '',
    timestamp       TEXT NOT NULL,
    previous_status TEXT,
    new_status      TEXT,
    payment_hold    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_events(case_id);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;

CREATE TABLE IF NOT EXISTS case_state (
    case_id      TEXT PRIMARY KEY,
    status       TEXT NOT NULL,
    payment_hold INTEGER NOT NULL DEFAULT 0,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    provider_npi TEXT PRIMARY KEY,
    enabled      INTEGER NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submitted_claims (
    claim_id TEXT PRIMARY KEY,
    payload  TEXT NOT NULL
);
"""


def get_db() -> sqlite3.Connection:
    """Return the shared connection, (re)opening it if `CLAIMSHIELD_DB` changed."""
    global _conn, _conn_path
    path = os.environ.get("CLAIMSHIELD_DB") or DEFAULT_DB_PATH
    with _lock:
        if _conn is None or _conn_path != path:
            if _conn is not None:
                _conn.close()
            if path != ":memory:":
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            _conn = sqlite3.connect(path, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.executescript(SCHEMA)
            _conn.commit()
            _conn_path = path
        return _conn


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    with _lock:
        db = get_db()
        cur = db.execute(sql, params)
        db.commit()
        return cur


def query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with _lock:
        return [dict(r) for r in get_db().execute(sql, params).fetchall()]


def reset_for_tests() -> None:
    """Drop the connection so the next call re-opens whatever `CLAIMSHIELD_DB` points at."""
    global _conn, _conn_path
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn, _conn_path = None, None
