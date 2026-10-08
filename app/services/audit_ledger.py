from datetime import datetime

# In-memory audit trail storage
AUDIT_LEDGER = []

def record_action(case_id: str, action: str, investigator_id: str, notes: str) -> dict:
    """Appends an immutable audit log entry for a case action decision."""
    entry = {
        "case_id": case_id,
        "action": action,  # APPROVE_SIU, REQUEST_INFO, DISMISS
        "investigator_id": investigator_id,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    AUDIT_LEDGER.append(entry)
    return entry

def get_case_audit_history(case_id: str) -> list[dict]:
    """Retrieves all chronological audit logs for a given case."""
    return [entry for entry in AUDIT_LEDGER if entry["case_id"] == case_id]

# Test Audit Ledger locally
if __name__ == "__main__":
    record_action("CLAIM-9042", "APPROVE_SIU", "INV-007", "High severity duplicate billing confirmed.")
    record_action("CLAIM-9042", "REQUEST_INFO", "INV-007", "Requested medical records from provider.")
    
    print("--- Audit History for CLAIM-9042 ---")
    print(get_case_audit_history("CLAIM-9042"))