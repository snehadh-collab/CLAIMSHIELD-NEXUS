@echo off
REM Starts backend (port 8000) and frontend (port 5173) in separate windows.
if not exist .env copy .env.example .env
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate
pip install -r requirements.txt
start "ClaimShield API" cmd /k "call .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
cd frontend
if not exist node_modules ( call npm install )
start "ClaimShield UI" cmd /k "npm run dev"
echo Open http://localhost:5173  (API docs: http://localhost:8000/docs)
