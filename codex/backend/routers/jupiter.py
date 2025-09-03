from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from subprocess import Popen
import sys
import json
import os
import time

router = APIRouter(prefix="/jupiter", tags=["jupiter"])

SESSIONS_FILE = Path("auto_core/state/jupiter_sessions.json")

def _load_sessions():
    if not SESSIONS_FILE.exists():
        return {}
    try:
        return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_sessions(s):
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")

class OpenReq(BaseModel):
    walletId: str
    url: str | None = None
    headless: bool = False

class CloseReq(BaseModel):
    walletId: str | None = None  # if None, close all known sessions

@router.post("/open")
def open_jupiter(req: OpenReq):
    launcher = Path("auto_core/launcher/open_jupiter.py").resolve()
    if not launcher.exists():
        raise HTTPException(status_code=500, detail="Launcher not found.")

    python_exe = sys.executable or "python"
    cmd = [python_exe, str(launcher), "--wallet-id", req.walletId]
    if req.url:
        cmd += ["--url", req.url]
    if req.headless:
        cmd += ["--headless"]

    try:
        proc = Popen(cmd)  # detached; FastAPI returns immediately
        sessions = _load_sessions()
        sessions[req.walletId] = {
            "pid": proc.pid,
            "cmd": cmd,
            "started_at": int(time.time())
        }
        _save_sessions(sessions)
        return {"ok": True, "launched": req.walletId, "pid": proc.pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Launch failed: {e}")

@router.post("/close")
def close_jupiter(req: CloseReq):
    sessions = _load_sessions()
    targets = []
    if req.walletId:
        entry = sessions.get(req.walletId)
        if not entry:
            raise HTTPException(status_code=404, detail=f"No session tracked for walletId '{req.walletId}'.")
        targets = [(req.walletId, entry)]
    else:
        targets = list(sessions.items())

    failed = []
    for alias, entry in targets:
        pid = entry.get("pid")
        if not pid:
            failed.append({"alias": alias, "error": "missing pid"})
            continue
        try:
            if os.name == "nt":
                os.system(f"taskkill /PID {pid} /T /F >NUL 2>&1")
            else:
                os.kill(pid, 9)
            sessions.pop(alias, None)
        except Exception as e:
            failed.append({"alias": alias, "error": str(e)})
    _save_sessions(sessions)

    if failed:
        return {"ok": False, "failed": failed}
    return {"ok": True, "closed": [a for a, _ in targets]}

@router.get("/status")
def status():
    return _load_sessions()
