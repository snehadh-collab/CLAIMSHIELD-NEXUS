from pydantic import BaseModel, Field
from typing import List, Optional

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