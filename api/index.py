"""Vercel Serverless Function Entrypoint for QA Intelligence Hub FastAPI.

Bridges the repository structure to the Vercel Python serverless runtime.
Initialization details are logged server-side and never returned to clients.
"""
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger("qahub.bootstrap")

# Top-level ASGI app declaration required by @vercel/python builder AST inspection.
app = FastAPI(title="QA Intelligence Hub API")

_FILE_DIR = Path(__file__).resolve().parent
_ROOT = _FILE_DIR.parent if _FILE_DIR.name == "api" else _FILE_DIR
_CWD = Path.cwd()

for _base in [_ROOT, _CWD, _FILE_DIR]:
    for _sub in ["", "backend", "domains", "qa-engine", "ai-engine"]:
        _cand = (_base / _sub).resolve() if _sub else _base.resolve()
        _p_str = str(_cand)
        if _cand.exists() and _p_str not in sys.path:
            sys.path.insert(0, _p_str)

def _bootstrap_failure_response() -> JSONResponse:
    """Return a generic bootstrap failure without exposing diagnostic internals."""
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Service temporarily unavailable.",
            "error_code": "APP_INITIALIZATION_FAILED",
        },
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
        },
    )


try:
    from app.main import app as _real_app
    app = _real_app
except Exception:
    # Do not expose exception text, stack traces, working directories, import
    # paths, or environment details to unauthenticated production callers.
    logger.exception("FastAPI application initialization failed")

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def _safe_initialization_failure(path: str):
        return _bootstrap_failure_response()
