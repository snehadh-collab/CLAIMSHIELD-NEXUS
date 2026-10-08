# CLAIMSHIELD NEXUS — Unified Healthcare Fraud Shield & AI Copilot

CLAIMSHIELD NEXUS is a unified, production-ready Healthcare Fraud, Waste, and Abuse (FWA) detection system integrating three advanced V1 engineering architectures into a single FastAPI engine:

1. **Member 1 (Data & Graph ML):** Synthetic claim generation (5,000+ claims), explicit fraud pattern injection (Phantom Billing, Upcoding, Impossible Travel), NetworkX graph topology modeling, and degree centrality ring detection.
2. **Member 2 (Backend & Scoring):** FastAPI REST backend, canonical Pydantic schemas, rule-based fraud detection, scikit-learn IsolationForest anomaly detection, composite SIU risk scoring, and SIU Queue prioritization.
3. **Member 3 (AI Copilot & Policy RAG):** Policy knowledge base grounding, keyword-based policy retrieval, Google Gemini structured SIU brief generation, interactive copilot chat, and human-in-the-loop audit logging.

---

## 📁 Repository Structure

```
CLAIMSHIELD-NEXUS/
│
├── app/
│   ├── main.py                     # Single Unified FastAPI Application
│   ├── config.py                   # Central Configuration & Environment Settings
│   │
│   ├── models/                     # Canonical Shared Pydantic Schemas
│   │   ├── claim.py                # Unified Claim & Provider/Member models
│   │   ├── siu_case.py             # SIU Case, RuleFlags, AnomalyScore, CompositeRiskScore
│   │   ├── graph.py                # Graph Node/Edge/Payload schemas
│   │   └── copilot.py              # SIUBriefSchema, BriefRequest, AuditAction schemas
│   │
│   ├── routers/                    # Clean Modular API Endpoints
│   │   ├── claims.py               # GET /api/v1/claims/, POST /api/v1/claims/generate
│   │   ├── analyze.py              # POST /api/v1/analyze/
│   │   ├── siu.py                  # GET /api/v1/siu/queue
│   │   ├── graph.py                # GET /api/v1/graph/{id}, /centrality
│   │   ├── dashboard.py            # GET /api/v1/dashboard (metrics + prioritized queue for the UI)
│   │   ├── copilot.py              # GET /api/v1/copilot/context/{id}, /brief, /chat
│   │   └── cases.py                # POST /api/v1/cases/{id}/action, /audit, /forecast
│   │
│   └── services/                   # Business Logic & ML Engines
│       ├── data_service.py         # In-memory claim dataset manager
│       ├── rules_engine.py         # Member 2 rule evaluator (Duplicate, Travel, Upcoding, Phantom)
│       ├── ml_engine.py            # Member 2 IsolationForest anomaly detector
│       ├── graph_service.py        # Member 1 NetworkX graph engine & centrality
│       ├── scoring_engine.py       # Composite Risk Score (30% Rules + 30% ML + 40% Graph)
│       ├── policy_rag.py           # Member 3 policy RAG engine
│       ├── brief_generator.py      # Member 3 Gemini AI brief generator
│       └── audit_service.py        # Human-in-the-loop audit trail tracker
│
├── data/
│   ├── synthetic_claims.csv        # Canonical generated CSV dataset (5,000 claims)
│   ├── synthetic_claims.json       # Canonical generated JSON dataset
│   └── synthetic_policies.md       # Member 3 policy knowledge base
│
├── frontend/                       # React + Vite SIU workspace dashboard (wired to the API)
│   ├── src/App.tsx, src/api.ts
│   └── README.md
│
├── scripts/
│   └── generate_claims.py          # Standalone claim generation script
│
├── tests/
│   ├── test_data_gen.py            # Member 1 unit tests
│   ├── test_endpoints.py           # Member 2 API tests
│   ├── test_rag_and_brief.py       # Member 3 RAG & brief tests
│   └── test_integration_pipeline.py# Comprehensive End-to-End integration test suite
│
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## 🚀 One-Command Start (Backend + Frontend)

* Windows: double-click / run `run.bat`
* macOS/Linux: `./run.sh`

Then open **http://localhost:5173** (UI) and **http://localhost:8000/docs** (API).
Manual steps: backend as below, then `cd frontend && npm install && npm run dev`.

---

## ⚡ Quick Start & Execution Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate / Load Synthetic Data
To generate a fresh synthetic claims dataset of 5,000 claims with injected fraud patterns:
```bash
python scripts/generate_claims.py
```
* The CSV and JSON outputs are stored only in `data/`; the FastAPI backend loads or generates `data/synthetic_claims.csv` on startup. Regenerating data through the API also reloads the dataset and refreshes the ML and graph engines.

### 3. Run FastAPI Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger API documentation will be available at: `http://localhost:8000/docs`

---

## 🧪 Running the Full Test Suite

Execute all unit and end-to-end integration tests:
```bash
pytest -v
```

---

## 📊 Composite SIU Risk Score Formula

The composite SIU risk score combines rule violations, machine learning anomaly detection, and graph network centrality into a single normalized risk metric ($0.0 - 1.0$):

$$\text{Composite Risk} = (RuleScore \times 0.3) + (MLScore \times 0.3) + (GraphScore \times 0.4)$$

* **Rule Score ($30\%$):** Fraction of active rule flags (Duplicate, Impossible Travel, Upcoding, Phantom Billing).
* **ML Score ($30\%$):** IsolationForest decision function score normalized across claims.
* **Graph Score ($40\%$):** NetworkX degree centrality scaled to identify provider fraud rings and high-density hub nodes.

---

## 🛡️ Responsible AI & Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key parameters:
* `GEMINI_API_KEY`: *(Optional)* Google Gemini API key for structured SIU brief generation.
* `GROQ_API_KEY`: *(Optional)* Groq LLM API key fallback.
* `OLLAMA_BASE_URL`: *(Optional)* Local Ollama provider URL (`http://localhost:11434`).

*If no LLM API key is present, the system degrades gracefully and returns a structured fallback SIU brief without crashing.*
