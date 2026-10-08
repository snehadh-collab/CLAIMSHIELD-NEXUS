from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.services.data_service import data_service
from app.services.ml_engine import ml_service
from app.services.graph_service import graph_service
from app.routers import claims, analyze, siu, graph, copilot, cases, dashboard

def init_system():
    print(" Starting CLAIMSHIELD NEXUS Unified System...")
    # 1. Load or generate synthetic claim dataset (Member 1)
    claims = data_service.load_or_generate_dataset(num_claims=5000)
    
    # 2. Fit ML IsolationForest model (Member 2)
    print(" Fitting ML IsolationForest Anomaly Detector...")
    ml_service.fit(claims)
    
    # 3. Build NetworkX claim graph (Member 1)
    print(" Building NetworkX Graph & Computing Degree Centrality...")
    graph_service.build_graph_from_claims(claims)
    
    print(" CLAIMSHIELD NEXUS Engine is ready and online!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_system()
    yield

app = FastAPI(
    title="CLAIMSHIELD NEXUS - Unified Healthcare Fraud Detection & AI Copilot",
    version=settings.VERSION,
    description="Integrated FWA engine combining Rules Engine, ML IsolationForest, NetworkX Graph Analytics, Composite SIU Risk Scoring, Policy RAG, and Gemini AI Copilot.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "total_claims_loaded": len(data_service.claims)
    }

# Register all integrated API routers
app.include_router(claims.router)
app.include_router(analyze.router)
app.include_router(siu.router)
app.include_router(graph.router)
app.include_router(copilot.router)
app.include_router(cases.router)
app.include_router(dashboard.router)
