from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.claim import Claim

class RuleFlags(BaseModel):
    is_duplicate: bool = False
    impossible_geography: bool = False
    upcoding_anomaly: bool = False
    phantom_billing: bool = False
    flag_count: int = 0
    flag_reasons: List[str] = []

class AnomalyScore(BaseModel):
    ml_score: float = Field(..., ge=0.0, le=1.0, description="Normalized IsolationForest Anomaly Score")
    is_anomalous: bool = False

class GraphRisk(BaseModel):
    degree_centrality: float = 0.0
    is_ring_hub: bool = False

class CompositeRiskScore(BaseModel):
    composite_score: float = Field(..., ge=0.0, le=1.0, description="Weighted composite risk score: 0.3*Rules + 0.3*ML + 0.4*Graph")
    risk_tier: str = Field(..., json_schema_extra={"example": "HIGH"})  # CRITICAL, HIGH, MEDIUM, LOW
    rule_score: float
    ml_score: float
    graph_score: float

class ClaimAnalysisResponse(BaseModel):
    claim_id: str
    provider_npi: str
    rule_flags: RuleFlags
    anomaly_score: AnomalyScore
    graph_risk: Optional[GraphRisk] = None
    composite_risk: Optional[CompositeRiskScore] = None

class SIUCase(BaseModel):
    case_id: str
    claim: Claim
    rule_flags: RuleFlags
    anomaly_score: AnomalyScore
    graph_risk: GraphRisk
    composite_risk: CompositeRiskScore
    status: str = Field("PENDING", json_schema_extra={"example": "PENDING"})  # PENDING, UNDER_INVESTIGATION, HOLD, AUDIT, DISMISSED
    created_at: datetime = Field(default_factory=datetime.now)
