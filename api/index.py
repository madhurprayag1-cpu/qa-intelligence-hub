"""Vercel Serverless Function Entrypoint for QA Intelligence Hub FastAPI.

Bridges the repository structure to Vercel's Python serverless runtime
by adding backend, qa-engine, and ai-engine packages to sys.path.
"""

import sys
from pathlib import Path

# Repo root and working directory resolution
_CWD = Path.cwd()
_FILE_DIR = Path(__file__).resolve().parent
_ROOT = _FILE_DIR.parent if _FILE_DIR.name == "api" else _FILE_DIR

for _base in [_ROOT, _CWD, _FILE_DIR]:
    for _sub in ["", "backend", "domains", "qa-engine", "ai-engine"]:
        _cand = (_base / _sub).resolve() if _sub else _base.resolve()
        _p_str = str(_cand)
        if _cand.exists() and _p_str not in sys.path:
            sys.path.insert(0, _p_str)

try:
    from app.main import app
except Exception as _exc:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    _err_msg = str(_exc)
    _err_type = type(_exc).__name__
    _tb = traceback.format_exc()
    app = FastAPI(title="Diagnostic App")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def _catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error_type": _err_type,
                "error": _err_msg,
                "traceback": _tb,
                "sys_path": sys.path,
                "cwd": str(Path.cwd()),
                "file": str(Path(__file__).resolve()),
            },
        )
