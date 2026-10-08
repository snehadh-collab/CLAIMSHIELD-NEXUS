from fastapi import FastAPI
from app.routers import cases_router, copilot_router

app = FastAPI(
    title="ClaimShield Nexus - AI Copilot & SIU Engine",
    description="24-Hour Hackathon Backend Engine for Healthcare Fraud Detection",
    version="1.0.0"
)

# Include Routers
app.include_router(cases_router.router)
app.include_router(copilot_router.router)

@app.get("/")
def root_status():
    return {
        "status": "ONLINE",
        "system": "ClaimShield Nexus AI Engine",
        "member_3_services": ["Policy RAG", "Brief Generator", "Audit Ledger", "Copilot Chat"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)