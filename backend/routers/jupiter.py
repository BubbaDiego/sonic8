from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from subprocess import Popen, run, PIPE
import sys, os, json, time, logging

router = APIRouter(prefix="/jupiter", tags=["jupiter"])

# Anchor all paths to the repo root so CWD doesn't matter
REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = (REPO_ROOT / "auto_core" / "launcher" / "open_jupiter.py").resolve()
STEP_CONNECT = (REPO_ROOT / "auto_core" / "steps" / "connect_jupiter.py").resolve()
STATE_DIR = REPO_ROOT / "auto_core" / "state"
SESSIONS_FILE = STATE_DIR / "jupiter_sessions.json"
DEDICATED_ALIAS = os.getenv("SONIC_AUTOPROFILE", "Sonic - Auto")
ENV_BASE = os.environ.copy()
ENV_BASE.setdefault("SONIC_CHROME_PORT", "9230")


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
    walletId: str  # ignored; kept for compatibility
    url: str | None = None
    headless: bool = False


class CloseReq(BaseModel):
    walletId: str | None = None  # None = close all tracked sessions


class ConnectReq(BaseModel):
    url: str | None = None


@router.post("/open")
def open_jupiter(req: OpenReq):
    # Force canonical alias so we never create new folders by accident
    wallet = DEDICATED_ALIAS

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
            # 1) Graceful: signal the launcher loop via flag file
            control_dir = STATE_DIR
            flag = control_dir / f"shutdown__{alias}.flag"
            try:
                control_dir.mkdir(parents=True, exist_ok=True)
                flag.write_text("close", encoding="utf-8")
            except Exception:
                pass

            # Wait up to ~4s for the process to exit cleanly
            import time
            try:
                import psutil  # type: ignore
            except Exception:
                psutil = None
            end = time.time() + 4.0
            exited = False
            if psutil is not None:
                try:
                    while time.time() < end:
                        if not psutil.pid_exists(pid):
                            exited = True
                            break
                        time.sleep(0.2)
                except Exception:
                    pass

            # 2) Fallback: hard kill if still alive
            if not exited:
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


@router.post("/connect")
def connect_jupiter(req: ConnectReq):
    env = ENV_BASE.copy()
    if req.url:
        env["SONIC_JUPITER_URL"] = req.url
    try:
        proc = run(
            [sys.executable or "python", str(STEP_CONNECT)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=PIPE,
            stderr=PIPE,
            timeout=60,
        )
    except Exception as e:
        return {"ok": False, "code": -1, "detail": str(e)}

    ok = proc.returncode == 0
    detail = (
        proc.stdout.decode("utf-8", errors="ignore")
        if ok
        else proc.stderr.decode("utf-8", errors="ignore")
    )
    return {"ok": ok, "code": proc.returncode, "detail": detail}
