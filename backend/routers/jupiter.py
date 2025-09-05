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
DEDICATED_ALIAS = os.getenv("SONIC_AUTOPROFILE", "Sonic - Auto")


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

from playwright.sync_api import sync_playwright
import re


@router.post("/connect/solflare")
def connect_solfare():
    """Attach to the running Chrome via CDP and connect Solflare on jup.ag."""
    # Read CDP port published by the launcher
    cdp_path = REPO_ROOT / "auto_core" / "state" / "jupiter_cdp.json"
    if not cdp_path.exists():
        raise HTTPException(status_code=409, detail="Browser not running. Open it first.")
    try:
        info = json.loads(cdp_path.read_text(encoding="utf-8"))
        port = int(info.get("port", 0))
        if not port:
            raise ValueError("missing port")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid CDP info: {e}")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        # Use the first context (persistent)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = None
        # Prefer an existing jup.ag tab
        for pg in ctx.pages:
            if "jup.ag" in (pg.url or ""):
                page = pg
                break
        if not page:
            page = ctx.new_page()
            page.goto("https://jup.ag", wait_until="domcontentloaded")

        def already_connected() -> bool:
            try:
                # If a "Connect" button is visible, not connected.
                if page.get_by_role("button", name=re.compile("connect", re.I)).first.is_visible(timeout=500):
                    return False
            except Exception:
                pass
            # Heuristic: wallet chip / avatar present, or Disconnect entry exists
            try:
                page.get_by_text(re.compile("Disconnect", re.I)).first  # might throw if not found
                return True
            except Exception:
                # Fallback: no "Connect" button visible implies connected
                return True

        if already_connected():
            return {"ok": True, "alreadyConnected": True}

        # Click "Connect" (header or modal)
        try:
            page.get_by_role("button", name=re.compile("connect", re.I)).first.click(timeout=3000)
        except Exception:
            # Alternate selector
            page.locator("text=Connect").first.click(timeout=3000)

        # Choose Solflare in wallet list
        try:
            page.get_by_role("button", name=re.compile("solflare", re.I)).first.click(timeout=3000)
        except Exception:
            page.locator("text=Solflare").first.click(timeout=3000)

        # Handle Solflare extension popup (new page)
        solflare_id = os.getenv("SOLFLARE_ID", "bhhhlbepdkbapadjdnnojkbgioiodbic")
        ext_page = None

        def _on_page(p):
            nonlocal ext_page
            try:
                if p.url.startswith(f"chrome-extension://{solflare_id}"):
                    ext_page = p
            except Exception:
                pass

        browser.on("page", _on_page)
        ctx.on("page", _on_page)

        # Wait up to ~8s for popup
        for _ in range(32):
            if ext_page:
                break
            page.wait_for_timeout(250)

        if not ext_page:
            # Some flows connect silently if already approved once
            if already_connected():
                return {"ok": True, "alreadyConnected": True, "popup": "none"}
            raise HTTPException(status_code=504, detail="Solflare popup did not appear")

        # In the Solflare popup, approve/next/connect
        try:
            # common buttons across versions
            for label in ["Connect", "Approve", "Next", "Continue", "Confirm"]:
                try:
                    ext_page.get_by_role("button", name=re.compile(f"^{label}$", re.I)).first.click(timeout=1200)
                except Exception:
                    pass
            # If there is a permissions list, accept
            try:
                ext_page.get_by_role("button", name=re.compile("Allow|Approve", re.I)).first.click(timeout=1200)
            except Exception:
                pass
        except Exception:
            # ignore; popup may auto-close
            pass

        # Wait a moment for jup.ag to reflect connection
        page.bring_to_front()
        page.wait_for_timeout(1000)

        if not already_connected():
            raise HTTPException(status_code=500, detail="Wallet still not connected")

        return {"ok": True, "connected": True}
