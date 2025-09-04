from __future__ import annotations

import json
import os
import signal
from datetime import datetime
from pathlib import Path
from subprocess import Popen
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/jupiter", tags=["jupiter"])

SESSIONS_FILE = Path("auto_core/state/jupiter_sessions.json")


def _load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        try:
            return json.loads(SESSIONS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_sessions(data: dict) -> None:
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_FILE.write_text(json.dumps(data, indent=2))


class OpenReq(BaseModel):
    walletId: str
    url: str | None = None
    headless: bool = False


class CloseReq(BaseModel):
    walletId: str | None = None


@router.post("/open")
def open_jupiter(req: OpenReq):
    launcher = Path("auto_core/launcher/open_jupiter.py").resolve()
    if not launcher.exists():
        raise HTTPException(status_code=500, detail="launcher not found")
    cmd = [sys.executable or "python", str(launcher), "--wallet-id", req.walletId]
    if req.url:
        cmd += ["--url", req.url]
    if req.headless:
        cmd += ["--headless"]
    proc = Popen(cmd)
    sessions = _load_sessions()
    sessions[req.walletId] = {
        "pid": proc.pid,
        "command": " ".join(cmd),
        "start": datetime.utcnow().isoformat(),
    }
    _save_sessions(sessions)
    return {"ok": True, "launched": req.walletId, "pid": proc.pid}


@router.post("/close")
def close_jupiter(req: CloseReq):
    sessions = _load_sessions()
    results = {}
    targets = [req.walletId] if req.walletId else list(sessions.keys())
    for wid in targets:
        meta = sessions.get(wid)
        if not meta:
            results[wid] = {"success": False, "error": "not running"}
            continue
        pid = meta.get("pid")
        try:
            os.kill(pid, signal.SIGTERM)
            results[wid] = {"success": True}
            del sessions[wid]
        except Exception as e:  # pragma: no cover - best effort
            results[wid] = {"success": False, "error": str(e)}
    _save_sessions(sessions)
    return {"results": results}


@router.get("/status")
def jupiter_status():
    return _load_sessions()
