from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from subprocess import Popen
import sys, os, json, time, logging

router = APIRouter(prefix="/jupiter", tags=["jupiter"])

# Anchor all paths to the repo root so CWD doesn't matter
REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER  = (REPO_ROOT / "auto_core" / "launcher" / "open_jupiter.py").resolve()
STATE_DIR = REPO_ROOT / "auto_core" / "state"
SESSIONS_FILE = STATE_DIR / "jupiter_sessions.json"


def _load_sessions() -> dict:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if SESSIONS_FILE.exists():
            return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_sessions(s: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")


class OpenReq(BaseModel):
    walletId: str
    url: str | None = None
    headless: bool = False


class CloseReq(BaseModel):
    walletId: str | None = None  # None = close all tracked sessions


@router.post("/open")
def open_jupiter(req: OpenReq):
    wallet = (req.walletId or "").strip()
    if not wallet:
        raise HTTPException(status_code=400, detail="walletId is required")

    if not LAUNCHER.exists():
        raise HTTPException(status_code=500, detail=f"launcher not found at {LAUNCHER}")

    cmd = [sys.executable or "python", str(LAUNCHER), "--wallet-id", wallet]
    if req.url:
        cmd += ["--url", req.url]
    if req.headless:
        cmd += ["--headless"]

    try:
        # Use repo root as working dir to stabilize relative imports/paths
        proc = Popen(cmd, cwd=str(REPO_ROOT))
    except Exception as e:
        logging.exception("failed to launch jupiter")
        raise HTTPException(status_code=500, detail=f"failed to launch: {e}") from e

    sessions = _load_sessions()
    sessions[wallet.lower()] = {
        "pid": proc.pid,
        "cmd": cmd,
        "cwd": str(REPO_ROOT),
        "started_at": int(time.time()),
    }
    _save_sessions(sessions)
    return {"ok": True, "launched": wallet, "pid": proc.pid}


@router.post("/close")
def close_jupiter(req: CloseReq):
    sessions = _load_sessions()
    targets = list(sessions.items()) if not req.walletId else [(req.walletId.lower(), sessions.get(req.walletId.lower()))]
    targets = [(a, e) for a, e in targets if e]

    failed = []
    for alias, entry in targets:
        pid = entry.get("pid")
        try:
            if os.name == "nt":
                os.system(f"taskkill /PID {pid} /T /F >NUL 2>&1")
            else:
                os.kill(pid, 9)
            sessions.pop(alias, None)
        except Exception as e:
            failed.append({"alias": alias, "error": str(e)})
    _save_sessions(sessions)
    return {"ok": not failed, "closed": [a for a, _ in targets], "failed": failed}


@router.get("/status")
def status():
    return _load_sessions()


@router.get("/debug-paths")
def debug_paths():
    return {
        "repo_root": str(REPO_ROOT),
        "launcher": str(LAUNCHER),
        "launcher_exists": LAUNCHER.exists(),
        "sessions_file": str(SESSIONS_FILE),
    }
