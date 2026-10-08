from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from datetime import datetime

from app.models.schemas import Claim, ClaimAnalysisResponse, SIUCase, ExposureForecast
from app.services.rules_engine import evaluate_claim_rules
from app.services.ml_engine import ml_service
from app.services.siu_ranking import generate_siu_queue
from app.services.forecasting import calculate_provider_exposure

app = FastAPI(title="ClaimShield Nexus - Backend Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLAIM_DATABASE: List[Claim] = []
RULE_RESULTS_MAP: Dict[str, any] = {}
ANOMALY_RESULTS_MAP: Dict[str, any] = {}

# Mock Graph Centrality Map (Simulating Member 1's Handoff)
GRAPH_CENTRALITY_MAP: Dict[str, float] = {
    "NPI-999": 0.85,  # High centrality (Fraud Ring)
    "NPI-100": 0.20,
    "NPI-101": 0.10
}

@app.on_event("startup")
def startup_event():
    now = datetime.now()
    sample_data = [
        Claim(claim_id="CLM-001", provider_npi="NPI-100", member_id="MEM-200", cpt_code="99214", claim_amount=150.0, timestamp=now, location="Chennai", diagnosis_code="R05"),
        Claim(claim_id="CLM-002", provider_npi="NPI-101", member_id="MEM-201", cpt_code="99213", claim_amount=120.0, timestamp=now, location="Delhi", diagnosis_code="J00"),
        Claim(claim_id="CLM-003", provider_npi="NPI-999", member_id="MEM-666", cpt_code="99215", claim_amount=5000.0, timestamp=now, location="Mumbai", diagnosis_code="Z00"),
    ]
    CLAIM_DATABASE.extend(sample_data)
    ml_service.fit(CLAIM_DATABASE)

    for c in CLAIM_DATABASE:
        r = evaluate_claim_rules(c, CLAIM_DATABASE)
        a = ml_service.predict(c)
        RULE_RESULTS_MAP[c.claim_id] = r
        ANOMALY_RESULTS_MAP[c.claim_id] = a

@app.get("/")
def health_check():
    return {"status": "online", "system": "ClaimShield Nexus Backend", "version": "2.0.0"}

@app.post("/api/v1/analyze", response_model=ClaimAnalysisResponse)
def analyze_claim(claim: Claim):
    rule_results = evaluate_claim_rules(claim, CLAIM_DATABASE)
    anomaly_results = ml_service.predict(claim)
    
    CLAIM_DATABASE.append(claim)
    RULE_RESULTS_MAP[claim.claim_id] = rule_results
    ANOMALY_RESULTS_MAP[claim.claim_id] = anomaly_results
    
    return ClaimAnalysisResponse(
        claim_id=claim.claim_id,
        provider_npi=claim.provider_npi,
        rule_flags=rule_results,
        anomaly_score=anomaly_results
    )

# Feature 2.3: SIU Queue Endpoint
@app.get("/api/v1/siu/queue", response_model=List[SIUCase])
def get_siu_queue():
    """Returns cases ranked by Composite Risk Score."""
    return generate_siu_queue(
        CLAIM_DATABASE,
        RULE_RESULTS_MAP,
        ANOMALY_RESULTS_MAP,
        GRAPH_CENTRALITY_MAP
    )

# Feature 2.4: Exposure Forecast Endpoint
@app.get("/api/v1/cases/{provider_npi}/forecast", response_model=ExposureForecast)
def get_case_forecast(provider_npi: str):
    """Calculates 30/60/90 day projected financial loss for a provider."""
    provider_claims = [c for c in CLAIM_DATABASE if c.provider_npi == provider_npi]
    if not provider_claims:
        raise HTTPException(status_code=404, detail=f"Provider NPI {provider_npi} not found")
    return calculate_provider_exposure(provider_npi, provider_claims)