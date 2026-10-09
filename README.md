# A Health | ClaimShield Nexus

**Enterprise-Grade Fraud, Waste, and Abuse (FWA) Detection & SIU Investigation Platform**

> *"BUILD TO CARE"*

A Health (ClaimShield Nexus) is a high-density, real-time Special Investigation Unit (SIU) copilot built for healthcare claim analysis. It combines deterministic rule evaluation, unsupervised machine learning anomaly scoring, graph neural network analysis, and AI policy retrieval into an executive dashboard designed to prevent healthcare fraud leakage before claims are paid.

---

## Key Capabilities

* **Tri-Engine Composite Scoring:** Calculates composite risk through balanced weighted factors:
  $$\text{Risk Score} = 0.30(\text{Rules Engine}) + 0.30(\text{ML Anomaly}) + 0.40(\text{Graph Network Analysis})$$
* **Sub-100ms Copilot Context Assembly:** Aggregates provider history, graph rings, and policy violations for instant decision-making.
* **Coordinated Network Ring Analysis:** Interactive graph network renderer tracking hidden relationships between providers, claimants, and billing entities.
* **Institutional Knowledge Vault (Karpathy "Second Brain"):** Auto-compiles markdown intelligence summaries (`/data/wiki/providers/NPI_xxx.md`) with interlinked backlinks (`[[Fraud Ring]]`, `[[Policy Rule]]`).
* **Interactive "What-If" Mitigation Simulator:** Models real-time dollar savings against custom audit threshold cutoffs.
* **Policy RAG Vault:** Cites federal policy rules and national coverage determinations (NCDs) against incoming billing patterns.
* **1-Click PDF Brief Generation:** Generates branded, executive-ready SIU investigation briefs on demand.

---

## System Architecture

```text
CLAIMSHIELD-NEXUS-integrated/
├── app/                        # FastAPI Backend Application
│   ├── main.py                 # Core API Router & Lifespan Configuration
│   ├── models/                 # Pydantic Schemas & Data Contracts
│   ├── routers/                # REST Endpoints (SIU Queue, Copilot, Graph, Forecast)
│   └── services/               # Core Intelligence Services
│       ├── audit_ledger.py     # Immutable Action Tracking
│       ├── brief_generator.py  # Executive Brief Generation
│       ├── forecasting.py      # 30/60/90-Day Loss Velocity Engine
│       ├── graph_engine.py     # Coordinated Ring Analytics
│       ├── ml_engine.py        # Anomaly Detection Pipeline
│       ├── policy_rag.py       # Federal Policy Citation Engine
│       └── rules_engine.py     # Deterministic Billing Rules
├── frontend/                   # React + Vite + Tailwind CSS Dashboard
│   ├── src/
│   │   ├── components/         # Navigation, KPI Cards, Toasts, PDF Exporter
│   │   ├── services/           # Axios API Client
│   │   └── views/              # SIU Queue, Case Workspace, Forecast, Sandbox
├── data/                       # Synthetic Claims Data & Policy Sources
└── tests/                      # Pytest Backend Unit & Integration Tests

Live Interface Breakdown
1. Executive SIU Command Queue
Displays real-time claim exposure, high-risk cases ranked by composite score, and rapid action drawers (APPROVE, PAUSE_PAYMENT, FLAG_FOR_SIU).

2. Deep-Dive Case Workspace & Institutional Brain
A 3-column triage center featuring:

Evidence Matrix: Triggered deterministic rules, ML anomaly scores, and federal policy citations.

Network & Brain Hub: React Flow coordinated ring visualization alongside Karpathy-style interlinked provider wikis.

Copilot & Executive Brief Drawer: Interactive assistant connected to Gemini with one-click branded PDF export.

3. Financial Forecast & "What-If" ROI Analysis
Tracks 30/60/90-day projected dollar losses using interactive Recharts area visualizations, featuring a real-time slider to model payment hold thresholds.

4. Real-Time Claim Sandbox
A testing suite supporting custom JSON claim payloads and 1-click test scenario triggers (Upcoding Violation, Impossible Geography, Duplicate Billing).

**Prerequisites**
Python: 3.10+
Node.js: 18.0+
Package Manager: npm or pnpm

**Backend API Specification**
GET / — System health check and service diagnostics
GET /api/v1/siu/queue — Ranked SIU case list sorted by composite risk
POST /api/v1/analyze — Real-time claim scoring across Rules + ML layers
GET /api/v1/cases/{npi}/forecast — 90-day cumulative financial loss projections.
GET /api/v1/copilot/context/{case_id} — Sub-100ms aggregated case context payload
GET /api/v1/graph/export/{case_id} — Subgraph export for node-edge graph visualization
POST /api/v1/cases/{case_id}/action — Logs investigator actions (APPROVE, PAUSE_PAYMENT, FLAG_FOR_SIU)
GET /api/v1/cases/{case_id}/audit — Immutable chronological case audit trail
POST /api/v1/cases/{case_id}/brief — Generates structured markdown executive briefs
POST /api/v1/copilot/chat — Multi-turn conversational copilot assistant

**Backend Setup**
Navigate to root directory:
Bash
cd CLAIMSHIELD-NEXUS-integrated

Create and activate a virtual environment:
Bash
python -m venv .venv
source .venv/bin/activate        # On Linux/macOS
# .venv\Scripts\activate          # On Windows

Install dependencies:
Bash
pip install -r requirements.txt

Launch the FastAPI application:
Bash
uvicorn app.main:app --reload --port 8000
The backend server runs at http://127.0.0.1:8000.

**Frontend Setup**
Navigate to frontend directory:
Bash
cd frontend

Install node packages:
Bash
npm install

Run development server:
Bash
npm run dev
The React interface runs at http://localhost:5173.

**Running Verification Tests**
To run the complete unit and integration test suite across the backend services:
Bash
pytest tests/ -v

**Tech Stack**
Backend Framework: FastAPI, Pydantic, Uvicorn
Data Processing & ML: NumPy, Pandas, Scikit-learn (Isolation Forest)
Graph Engine: NetworkX
Frontend Framework: React (Vite), TypeScript / JavaScript
Styling & Icons: Tailwind CSS, Lucide React
Data Visualization & Graphs: Recharts, React Flow
Document Generation: @react-pdf/renderer

**License** Internal Enterprise Distribution — All Rights Reserved.
