#!/usr/bin/env bash
# Starts backend (8000) and frontend (5173).
set -e
[ -f .env ] || cp .env.example .env
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
uvicorn app.main:app --reload --port 8000 &
API=$!
trap "kill $API" EXIT
cd frontend
[ -d node_modules ] || npm install
npm run dev
