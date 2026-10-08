from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Claim(BaseModel):
    claim_id: str = Field(..., example="CLM-10029")
    provider_npi: str = Field(..., example="NPI-99201")
    member_id: str = Field(..., example="MEM-44012")
    facility_id: Optional[str] = Field(None, example="FAC-0012")
    cpt_code: str = Field(..., example="99214")
    claim_amount: float = Field(..., example="450.00")
    timestamp: datetime
    location: str = Field(..., example="Chennai")
    diagnosis_code: str = Field(..., example="R05")

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
    # Append to app/models/schemas.py

class ExposureForecast(BaseModel):
    provider_npi: str
    historical_daily_avg_claim: float
    day_30_exposure: float
    day_60_exposure: float
    day_90_exposure: float

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