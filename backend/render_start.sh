#!/bin/sh
set -e

echo "[QAH] Preparing Python module search paths..."
export PYTHONPATH=".:../qa-engine:../ai-engine:$PYTHONPATH"

echo "[QAH] Entering backend directory..."
cd backend

echo "[QAH] Executing Alembic database schema migrations..."
alembic upgrade head

echo "[QAH] Initializing reference seed data (airlines, airports, flights)..."
python -m app.db.init_db

echo "[QAH] Starting FastAPI ASGI server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
