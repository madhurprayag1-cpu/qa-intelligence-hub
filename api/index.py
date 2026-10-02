"""Vercel Serverless Function Entrypoint for QA Intelligence Hub FastAPI.

Bridges the repository structure to Vercel's Python serverless runtime
by adding backend, qa-engine, and ai-engine packages to sys.path.
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Top-level ASGI app declaration required by @vercel/python builder AST inspection
app = FastAPI(title="QA Intelligence Hub API")

# Repo root and candidate base directories resolution
_FILE_DIR = Path(__file__).resolve().parent
_ROOT = _FILE_DIR.parent if _FILE_DIR.name == "api" else _FILE_DIR
_CWD = Path.cwd()

for _base in [_ROOT, _CWD, _FILE_DIR]:
    for _sub in ["", "backend", "domains", "qa-engine", "ai-engine"]:
        _cand = (_base / _sub).resolve() if _sub else _base.resolve()
        _p_str = str(_cand)
        if _cand.exists() and _p_str not in sys.path:
            sys.path.insert(0, _p_str)

_init_error = None
try:
    from app.main import app as _real_app
    app = _real_app
except Exception as _exc:
    import traceback
    _init_error = {
        "error_type": type(_exc).__name__,
        "error": str(_exc),
        "traceback": traceback.format_exc(),
        "sys_path": sys.path,
        "cwd": str(Path.cwd()),
        "file": str(Path(__file__).resolve()),
    }

if _init_error is not None:
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def _diagnostic_catch_all(path: str):
        return JSONResponse(status_code=500, content=_init_error)
