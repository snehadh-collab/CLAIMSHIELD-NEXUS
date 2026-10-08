from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from datetime import datetime

from app.models.schemas import Claim, ClaimAnalysisResponse, SIUCase, ExposureForecast, CopilotContextPayload
from app.services.rules_engine import evaluate_claim_rules
from app.services.ml_engine import ml_service
from app.services.siu_ranking import generate_siu_queue
from app.services.forecasting import calculate_provider_exposure
from app.services.context_aggregator import build_copilot_context

app = FastAPI(title="ClaimShield Nexus - Backend Engine", version="3.0.0")

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

GRAPH_CENTRALITY_MAP: Dict[str, float] = {
    "NPI-999": 0.85,
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
        RULE_RESULTS_MAP[c.claim_id] = evaluate_claim_rules(c, CLAIM_DATABASE)
        ANOMALY_RESULTS_MAP[c.claim_id] = ml_service.predict(c)

@app.get("/")
def health_check():
    return {"status": "online", "system": "ClaimShield Nexus Backend", "version": "3.0.0"}

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

@app.get("/api/v1/siu/queue", response_model=List[SIUCase])
def get_siu_queue():
    return generate_siu_queue(
        CLAIM_DATABASE,
        RULE_RESULTS_MAP,
        ANOMALY_RESULTS_MAP,
        GRAPH_CENTRALITY_MAP
    )

@app.get("/api/v1/cases/{provider_npi}/forecast", response_model=ExposureForecast)
def get_case_forecast(provider_npi: str):
    provider_claims = [c for c in CLAIM_DATABASE if c.provider_npi == provider_npi]
    if not provider_claims:
        raise HTTPException(status_code=404, detail=f"Provider NPI {provider_npi} not found")
    return calculate_provider_exposure(provider_npi, provider_claims)

@app.get("/api/v1/copilot/context/{case_id}", response_model=CopilotContextPayload)
def get_copilot_context(case_id: str):
    siu_queue = generate_siu_queue(
        CLAIM_DATABASE,
        RULE_RESULTS_MAP,
        ANOMALY_RESULTS_MAP,
        GRAPH_CENTRALITY_MAP
    )
    
    target_case = next((c for c in siu_queue if c.case_id == case_id), None)
    if not target_case:
        if siu_queue:
            target_case = siu_queue[0]
        else:
            raise HTTPException(status_code=404, detail=f"Case ID {case_id} not found")

    return build_copilot_context(
        case_id=target_case.case_id,
        provider_npi=target_case.provider_npi,
        claims=CLAIM_DATABASE,
        rule_map=RULE_RESULTS_MAP,
        anomaly_map=ANOMALY_RESULTS_MAP,
        graph_centrality=target_case.graph_centrality,
        composite_risk_score=target_case.composite_risk_score
    )