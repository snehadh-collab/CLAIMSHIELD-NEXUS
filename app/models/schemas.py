from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Base Claim Schema ---
class Claim(BaseModel):
    claim_id: str = Field(..., json_schema_extra={"example": "CLM-10029"})
    provider_npi: str = Field(..., json_schema_extra={"example": "NPI-99201"})
    member_id: str = Field(..., json_schema_extra={"example": "MEM-44012"})
    facility_id: Optional[str] = Field(None, json_schema_extra={"example": "FAC-0012"})
    cpt_code: str = Field(..., json_schema_extra={"example": "99214"})
    claim_amount: float = Field(..., json_schema_extra={"example": 450.00})
    timestamp: datetime
    location: str = Field(..., json_schema_extra={"example": "Chennai"})
    diagnosis_code: str = Field(..., json_schema_extra={"example": "R05"})

# --- Detection & Analysis Schemas ---
class RuleFlags(BaseModel):
    is_duplicate: bool = False
    impossible_geography: bool = False
    upcoding_flag: bool = False
    flag_reasons: List[str] = []

class AnomalyScore(BaseModel):
    ml_score: float = Field(..., ge=0.0, le=1.0)
    is_anomaly: bool = False

class ClaimAnalysisResponse(BaseModel):
    claim_id: str
    provider_npi: str
    rule_flags: RuleFlags
    anomaly_score: AnomalyScore

# --- SIU Queue & Forecasting Schemas ---
class SIUCase(BaseModel):
    case_id: str
    provider_npi: str
    composite_risk_score: float
    total_flagged_amount: float
    claim_count: int
    primary_flag_reason: str
    graph_centrality: float = 0.0

class ExposureForecast(BaseModel):
    provider_npi: str
    daily_velocity: float
    day_30_exposure: float
    day_60_exposure: float
    day_90_exposure: float

# --- Copilot & Context Aggregator Schemas ---
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