from typing import Dict, List, Optional
from app.models.copilot import AuditAction

class AuditService:
    def __init__(self):
        self._audit_store: Dict[str, List[AuditAction]] = {}

    def record_action(self, action: AuditAction) -> AuditAction:
        if action.case_id not in self._audit_store:
            self._audit_store[action.case_id] = []
        self._audit_store[action.case_id].append(action)
        return action

    def get_audit_trail(self, case_id: str) -> List[AuditAction]:
        return self._audit_store.get(case_id, [])

audit_service = AuditService()
