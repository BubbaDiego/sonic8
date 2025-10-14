# -*- coding: utf-8 -*-
"""Standalone FastAPI app for the XCom core webhook surface.

Run from the repo root (or any directory) with:

    python -m uvicorn backend.core.xcom_core.xcom_standalone_app:app \
        --app-dir /path/to/sonic7 --host 127.0.0.1 --port 5000 --reload

This isolates the lightweight XCom webhook + status endpoints so we can
exercise reply flows without importing the entire Sonic backend stack.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI

# ---------------------------------------------------------------------------
# Bootstrap sys.path / PYTHONPATH so ``import backend`` works regardless of CWD
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
BACKEND_DIR = REPO_ROOT / "backend"

for candidate in (REPO_ROOT, BACKEND_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

existing_py_path = os.environ.get("PYTHONPATH", "")
prefix = os.pathsep.join([str(REPO_ROOT), str(BACKEND_DIR)])
if existing_py_path:
    prefix = os.pathsep.join([prefix, existing_py_path])
os.environ.setdefault("PYTHONPATH", prefix)

# ---------------------------------------------------------------------------
# Load config so env-sensitive routers (e.g., Textbelt) work out of the box
# ---------------------------------------------------------------------------
try:  # pragma: no cover - defensive bootstrap only
    from backend.core.xcom_core.xcom_config_loader import load_xcom_config

    cfg, _ = load_xcom_config(base_dir=BACKEND_DIR)
    helius_key = cfg.get("HELIUS_API_KEY") if isinstance(cfg, dict) else None
    if helius_key and not os.getenv("HELIUS_API_KEY"):
        os.environ["HELIUS_API_KEY"] = helius_key
except Exception:  # pragma: no cover - optional convenience
    pass

app = FastAPI(title="XComCore Standalone API")


@app.get("/api/status")
def status():
    """Basic readiness probe so smoke tests can verify the app booted."""

    return {"status": "ok", "app": "xcom_core_standalone"}


# ---------------------------------------------------------------------------
# Optional routers - we only care about Textbelt reply webhook today.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - router import is optional in dev shells
    from backend.core.xcom_core.textbelt_reply_router import (  # type: ignore
        router as textbelt_router,
    )
except Exception:  # pragma: no cover
    textbelt_router = None  # type: ignore

if textbelt_router is not None:
    app.include_router(
        textbelt_router,
        prefix="/api/xcom/textbelt",
        tags=["xcom-textbelt"],
    )

