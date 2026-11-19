#!/usr/bin/env bash
# One-command launcher: sets up the backend venv, builds the frontend, serves everything on :8000
set -e
cd "$(dirname "$0")"
[ -d backend/.venv ] || python3 -m venv backend/.venv
backend/.venv/bin/pip install -q -r backend/requirements.txt
[ -f backend/data/movies.csv ] || backend/.venv/bin/python backend/data/build_dataset.py
(cd backend && [ -f models/recommender.pkl ] || .venv/bin/python -m app.ml.train)
(cd frontend && npm install --no-audit --no-fund && npm run build)
echo "CineMind running at http://localhost:8000   (demo login: demo@cinemind.dev / demo1234)"
cd backend && exec .venv/bin/python -m uvicorn app.main:app --port 8000
