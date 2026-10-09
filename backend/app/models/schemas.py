from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


# ==========================================
# Member 2: Core Claim & Engine Schemas
# ==========================================

def _to_utc(value: datetime) -> datetime:
    """Normalise to timezone-aware UTC. Naive values are interpreted as UTC.

    Every timestamp in the system goes through this, so naive and aware inputs can
    never be mixed in a comparison or subtraction (previous crash, audit D-01).
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class Claim(BaseModel):
    claim_id: str = Field(..., examples=["CLM-10029"])
    provider_npi: str = Field(..., examples=["1000000081"])
    member_id: str = Field(..., examples=["MEM-44012"])
    facility_id: Optional[str] = Field(None, examples=["FAC-0012"])
    cpt_code: str = Field(..., examples=["99214"])
    claim_amount: float = Field(..., examples=[450.00])
    timestamp: datetime
    location: str = Field(..., examples=["Chennai"])
    # The synthetic dataset carries no diagnosis codes, so stored claims may omit it.
    # Newly submitted claims are validated more strictly by ClaimInput.
    diagnosis_code: Optional[str] = Field(None, examples=["R05"])

    @field_validator("timestamp")
    @classmethod
    def _normalise_timestamp(cls, value: datetime) -> datetime:
        return _to_utc(value)


class ClaimInput(Claim):
    """Request model for newly submitted claims (`POST /analyze`): strict validation."""

    claim_id: str = Field(..., min_length=1, max_length=64, examples=["CLM-10029"])
    provider_npi: str = Field(..., min_length=1, max_length=32, examples=["1000000081"])
    member_id: str = Field(..., min_length=1, max_length=64, examples=["MEM-44012"])
    facility_id: Optional[str] = Field(None, max_length=128, examples=["FAC-0012"])
    cpt_code: str = Field(..., min_length=3, max_length=16, examples=["99214"])
    claim_amount: float = Field(..., gt=0, le=10_000_000, examples=[450.00])
    location: str = Field(..., min_length=1, max_length=128, examples=["Chennai"])
    diagnosis_code: str = Field(..., min_length=1, max_length=16, examples=["R05"])


# Backward compatibility alias
ClaimData = Claim


class RuleFlags(BaseModel):
    is_duplicate: bool = False
    impossible_geography: bool = False
    upcoding_anomaly: bool = False
    flag_count: int = 0
    flag_reasons: List[str] = []


class AnomalyScore(BaseModel):
    ml_score: float = Field(..., ge=0.0, le=1.0, description="Normalized IsolationForest Anomaly Score")
    is_anomalous: bool = False


class ClaimAnalysisResponse(BaseModel):
    claim_id: str
    provider_npi: str
    rule_flags: RuleFlags
    anomaly_score: AnomalyScore
    # Added so the UI can show the same score the queue would use for this claim.
    case_id: Optional[str] = None
    graph_centrality: Optional[float] = None
    composite_risk_score: Optional[float] = None
    persisted: bool = False


class ForecastPoint(BaseModel):
    date: str
    cumulative_billed: float


class ExposureForecast(BaseModel):
    provider_npi: str
    historical_daily_avg_claim: float
    day_30_exposure: float
    day_60_exposure: float
    day_90_exposure: float
    # Transparency fields (all optional, so older consumers keep working).
    claim_count: int = 0
    total_billed: float = 0.0
    observed_days: float = 0.0
    window_days_used: float = 0.0
    method: str = "Linear run-rate: total billed ÷ observed window (minimum 30 days) × horizon"
    history: List[ForecastPoint] = []


CaseStatus = Literal["OPEN", "APPROVED", "PENDING_RECORDS", "REFERRED_TO_SIU", "DISMISSED"]


class SIUCase(BaseModel):
    case_id: str
    provider_npi: str
    member_id: str
    total_claim_amount: float
    rule_flag_count: int
    ml_anomaly_score: float
    graph_centrality: float
    composite_risk_score: float
    status: str = "OPEN"
    forecast: Optional[ExposureForecast] = None
    # Added for the Command Center (all derived from stored data).
    provider_name: Optional[str] = None
    claim_count: int = 0
    rule_flags: List[str] = []
    primary_finding: str = ""
    title: str = ""
    payment_hold: bool = False
    latest_claim_at: Optional[str] = None
    last_action_at: Optional[str] = None


class CopilotContextPayload(BaseModel):
    case_id: str
    provider_npi: str
    member_id: str
    total_claim_amount: float
    composite_risk_score: float
    rule_flag_count: int
    rule_flag_reasons: List[str]
    ml_anomaly_score: float
    graph_centrality_score: float
    projected_30d_loss: float
    projected_90d_loss: float
    associated_claim_ids: List[str]
    policy_context_paragraphs: List[str] = []
    provider_name: Optional[str] = None
    status: str = "OPEN"
    payment_hold: bool = False


# ==========================================
# Member 3: Copilot, RAG, & SIU Brief Schemas
# ==========================================

class SIUBriefAI(BaseModel):
    """The fields we ask Gemini to produce (used as its structured-output schema)."""

    case_id: str = Field(description="Unique identifier for the claim or case")
    executive_summary: str = Field(description="Concise summary of why this claim was flagged")
    key_evidence: List[str] = Field(description="Bullet points of key fraudulent indicators")
    policy_citations: List[str] = Field(description="Specific policies or guidelines violated")
    recommended_action: str = Field(description="Action for investigator (e.g., PAYMENT_HOLD, AUDIT, DISMISS)")
    confidence_score: float = Field(description="AI confidence score between 0.0 and 1.0")


class SIUBriefSchema(SIUBriefAI):
    """API response. The extra fields say truthfully how the brief was produced."""

    source: Literal["GEMINI", "FALLBACK"] = "GEMINI"
    generated_at: Optional[str] = None
    disclaimer: Optional[str] = None
    status: Optional[str] = None
    ai_error: Optional[str] = Field(None, description="Why AI generation was not used (FALLBACK only)")


class BriefRequest(BaseModel):
    case_id: str
    claim_details: str
    flagged_rules: List[str]


CaseAction = Literal["APPROVE_SIU", "REQUEST_INFO", "DISMISS", "REFER_SIU", "PAUSE_PAYMENT"]


class CaseActionRequest(BaseModel):
    action: CaseAction = Field(
        ...,
        description=(
            "APPROVE_SIU: approve the findings · REQUEST_INFO: request medical records · "
            "DISMISS: mark false positive (also releases any payment hold) · "
            "REFER_SIU: refer the case to the SIU · PAUSE_PAYMENT: place a payment hold"
        ),
    )
    investigator_id: str = Field("INV-DEFAULT", min_length=1, max_length=64, description="Investigator ID performing the action")
    notes: str = Field(..., min_length=1, max_length=2000, description="Investigator reason (required for the audit trail)")

    @field_validator("notes")
    @classmethod
    def _notes_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A reason is required for the audit trail")
        return value.strip()


class MonitoringRequest(BaseModel):
    enabled: bool
    investigator_id: str = Field("INV-DEFAULT", min_length=1, max_length=64)
    notes: str = Field("", max_length=2000)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., max_length=4000, description="Message text content")


class CopilotChatRequest(BaseModel):
    case_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    chat_history: Optional[List[ChatMessage]] = Field(default_factory=list, max_length=30)
    case_context: Optional[str] = Field("", max_length=8000)


class CopilotChatResponse(BaseModel):
    case_id: str
    reply: str
    status: str
    confidence_score: Optional[float] = None
    disclaimer: Optional[str] = None
    source: Literal["GEMINI", "FALLBACK", "GUARDRAIL"] = "GEMINI"
    ai_error: Optional[str] = None
    citations: List[str] = []
