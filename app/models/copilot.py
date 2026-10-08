from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SIUBriefSchema(BaseModel):
    case_id: str = Field(description="Unique identifier for the claim or case")
    executive_summary: str = Field(description="Concise summary of why this claim was flagged")
    key_evidence: List[str] = Field(description="Bullet points of key fraudulent indicators")
    policy_citations: List[str] = Field(description="Specific policies or guidelines violated")
    recommended_action: str = Field(description="Action for investigator (e.g., PAYMENT_HOLD, AUDIT, DISMISS)")
    confidence_score: float = Field(description="AI confidence score between 0.0 and 1.0")

class BriefRequest(BaseModel):
    case_id: str
    claim_details: str
    flagged_rules: List[str]

class CopilotContextResponse(BaseModel):
    case_id: str
    claim_summary: str
    flagged_rules: List[str]
    relevant_policies: List[str]

class CopilotChatRequest(BaseModel):
    case_id: str
    user_query: str

class CopilotChatResponse(BaseModel):
    case_id: str
    response: str
    sources: List[str]

class AuditAction(BaseModel):
    case_id: str
    action: str  # PAYMENT_HOLD, AUDIT_REFERRAL, DISMISS, APPROVE
    investigator_id: str = "SIU-ANALYST-01"
    notes: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class AuditTrailResponse(BaseModel):
    case_id: str
    actions: List[AuditAction]
