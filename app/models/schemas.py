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