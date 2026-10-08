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
    upcoding_anomaly: bool = False
    flag_count: int = 0
    flag_reasons: List[str] = []

class AnomalyScore(BaseModel):
    ml_score: float = Field(..., ge=0.0, le=1.0)
    is_anomaly: bool = False

class ClaimAnalysisResponse(BaseModel):
    claim_id: str
    provider_npi: str
    rule_flags: RuleFlags
    anomaly_score: AnomalyScore

# --- Exposure Forecast Schema (Defined FIRST so SIUCase can reference it) ---
class ExposureForecast(BaseModel):
    provider_npi: str
    daily_velocity: float = 0.0
    historical_daily_avg_claim: float = 0.0
    day_30_exposure: float
    day_60_exposure: float
    day_90_exposure: float

# --- SIU Queue Case Schema ---
class SIUCase(BaseModel):
    case_id: str
    provider_npi: str
    composite_risk_score: float
    total_flagged_amount: float = 0.0
    total_claim_amount: float = 0.0
    claim_count: int = 1
    primary_flag_reason: str = "Automated Anomaly Detection"
    rule_flag_count: int = 0
    ml_anomaly_score: float = 0.0
    graph_centrality: float = 0.0
    member_id: Optional[str] = None
    forecast: Optional[ExposureForecast] = None

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