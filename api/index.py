"""Vercel Serverless Function Entrypoint for QA Intelligence Hub FastAPI.

Bridges the repository structure to Vercel's Python serverless runtime
by adding backend, qa-engine, and ai-engine packages to sys.path.
"""

import sys
from pathlib import Path

# Repo root resolution
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
_QA_ENGINE = _ROOT / "qa-engine"
_AI_ENGINE = _ROOT / "ai-engine"

for _p in [str(_ROOT), str(_BACKEND), str(_QA_ENGINE), str(_AI_ENGINE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.main import app
