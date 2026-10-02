#!/bin/sh
set -e

echo "[QAH] Applying database schema migrations..."
alembic upgrade head

echo "[QAH] Initializing reference seed data..."
python -m app.db.init_db

echo "[QAH] Launching FastAPI backend server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
