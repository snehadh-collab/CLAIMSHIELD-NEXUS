import os
from contextlib import asynccontextmanager
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load environment configuration
load_dotenv()

from app.models.schemas import Claim, ClaimAnalysisResponse, ClaimInput, SIUCase
from app.routers import cases_router, copilot_router, insight_router
from app.services import insights, llm
from app.services.siu_ranking import case_id_for
from app.services.store import get_store

VERSION = "3.5.0"

DEFAULT_CORS_ORIGINS = [
    "http://localhost:8443", "http://127.0.0.1:8443",
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:4173", "http://127.0.0.1:4173",
]
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()] or DEFAULT_CORS_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the claim store (rules, ML, graph centrality) and the precedent index at startup."""
    store = get_store()
    try:
        _ = store.memory
    except Exception as e:  # never block startup on the optional precedent index
        print(f"[Lifespan Notice] Historical memory unavailable: {e}")
    yield


app = FastAPI(
    title="ClaimShield Nexus - Unified Backend Hub",
    description="Unified backend for healthcare fraud detection, graph analytics, and AI copilot.",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Unexpected errors become a JSON 500 that still carries CORS headers, so the browser shows the
    real server error instead of an opaque network failure."""
    headers = {}
    origin = request.headers.get("origin")
    if origin and origin in CORS_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error ({type(exc).__name__})"},
        headers=headers,
    )


app.include_router(cases_router.router)
app.include_router(copilot_router.router)
app.include_router(insight_router.router)


@app.get("/")
def health_check():
    """System health: reports what is actually loaded and whether AI generation is configured."""
    store = get_store()
    return {
        "status": "online",
        "system": "ClaimShield Nexus Backend",
        "version": VERSION,
        "claims_loaded": len(store.claims),
        "cases": len(store.by_provider),
        "ai_configured": llm.get_gemini_client() is not None,
        "ai_model": llm.MODEL_NAME,
        "graph_centrality_available": store.centrality_error is None,
        "modules": [
            "Rules Engine",
            "ML Anomaly Detector",
            "Graph Analytics Engine",
            "SIU Ranking",
            "Policy RAG",
            "AI Copilot",
            "Audit Ledger",
        ],
    }


@app.post("/api/v1/analyze", response_model=ClaimAnalysisResponse)
def analyze_claim(claim: ClaimInput, persist: bool = False):
    """Evaluate rules and ML anomaly scoring for a claim.

    By default this is a dry run: nothing is stored. With `persist=true` the claim is added to the
    claim set (SQLite-backed), becomes part of its provider's case, and the case queue reflects it.
    """
    store = get_store()
    with store.lock:
        if persist and claim.claim_id in store.claims_by_id:
            raise HTTPException(status_code=409, detail=f"Claim {claim.claim_id} already exists")
        result = store.analyze(claim)
        rules, ml, composite = result["rules"], result["ml"], result["composite"]
        if persist:
            store.add_claim(Claim(**claim.model_dump()))
            rules = store.rule_results[claim.claim_id]
            ml = store.anomaly_results[claim.claim_id]
            composite = store.claim_risk(store.claims_by_id[claim.claim_id])
        known = claim.provider_npi in store.by_provider
    return ClaimAnalysisResponse(
        claim_id=claim.claim_id,
        provider_npi=claim.provider_npi,
        rule_flags=rules,
        anomaly_score=ml,
        case_id=case_id_for(claim.provider_npi) if known else None,
        graph_centrality=result["centrality"],
        composite_risk_score=composite,
        persisted=persist,
    )


@app.get("/api/v1/siu/queue", response_model=List[SIUCase])
def get_siu_queue():
    """Prioritized SIU case queue (one case per provider), including live status and payment hold."""
    return get_store().queue()


@app.get("/api/v1/graph/export/{case_id}")
def get_case_graph(case_id: str):
    """Entity-network payload for the case: provider, members, facilities and peer providers."""
    store = get_store()
    npi = store.resolve_provider(case_id)
    case = store.get_case(case_id_for(npi)) if npi else None
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return insights.build_case_graph(store, case)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
