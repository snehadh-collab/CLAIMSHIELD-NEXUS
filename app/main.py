from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import datetime

from app.models.schemas import Claim, ClaimAnalysisResponse
from app.services.rules_engine import evaluate_claim_rules
from app.services.ml_engine import ml_service

app = FastAPI(title="ClaimShield Nexus - Backend Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLAIM_DATABASE: List[Claim] = []

@app.on_event("startup")
def startup_event():
    now = datetime.now()
    sample_data = [
        Claim(claim_id="CLM-001", provider_npi="NPI-100", member_id="MEM-200", cpt_code="99214", claim_amount=150.0, timestamp=now, location="Chennai", diagnosis_code="R05"),
        Claim(claim_id="CLM-002", provider_npi="NPI-101", member_id="MEM-201", cpt_code="99213", claim_amount=120.0, timestamp=now, location="Delhi", diagnosis_code="J00"),
        Claim(claim_id="CLM-003", provider_npi="NPI-999", member_id="MEM-666", cpt_code="99215", claim_amount=2000.0, timestamp=now, location="Mumbai", diagnosis_code="Z00"),
    ]
    CLAIM_DATABASE.extend(sample_data)
    ml_service.fit(CLAIM_DATABASE)

@app.get("/")
def health_check():
    return {"status": "online", "system": "ClaimShield Nexus Backend"}

@app.post("/api/v1/analyze", response_model=ClaimAnalysisResponse)
def analyze_claim(claim: Claim):
    rule_results = evaluate_claim_rules(claim, CLAIM_DATABASE)
    anomaly_results = ml_service.predict(claim)
    CLAIM_DATABASE.append(claim)
    
    return ClaimAnalysisResponse(
        claim_id=claim.claim_id,
        provider_npi=claim.provider_npi,
        rule_flags=rule_results,
        anomaly_score=anomaly_results
    )