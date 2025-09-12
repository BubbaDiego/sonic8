from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from importlib import import_module
from typing import Any, Dict
import os, sys, json, time, subprocess, signal, socket
import anyio  # run sync steps on a worker

router = APIRouter(prefix="/api/auto-core", tags=["auto_core"])

# ============ session state (PID/cmd) ========================================
STATE_PATH = Path("auto_core/state/jupiter_sessions.json")
LOG_DIR = STATE_PATH.parent
LOG_DIR.mkdir(parents=True, exist_ok=True)

def _state_read() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _state_write(d: dict) -> None:
    STATE_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")

def _is_listening(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False

def _wait_port(port: int, host: str = "127.0.0.1", deadline_s: float = 8.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        if _is_listening(port, host):
            return True
        time.sleep(0.2)
    return False

def _kill(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass

# ============ wallet alias ↔ address registry ================================
ADDR_REG = Path(".cache/wallet_addresses.json")
BASE58 = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")

def _norm(wid: str | None) -> str | None:
    return None if wid is None else wid.strip().lower().replace(" ", "-")

def _addr_load() -> dict:
    if ADDR_REG.exists():
        try:
            return json.loads(ADDR_REG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _addr_save(d: dict) -> None:
    ADDR_REG.parent.mkdir(parents=True, exist_ok=True)
    ADDR_REG.write_text(json.dumps(d, indent=2), encoding="utf-8")

def _is_base58(s: str) -> bool:
    return 32 <= len(s) <= 44 and all(c in BASE58 for c in s)

class WalletAddressRegisterBody(BaseModel):
    wallet_id: str
    address: str

@router.get("/wallet-address")
async def get_wallet_address(wallet_id: str):
    reg = _addr_load()
    key = _norm(wallet_id)
    addr = reg.get(key)
    if not addr:
        raise HTTPException(status_code=404, detail=f"No address found for wallet_id={wallet_id}")
    return {"wallet_id": wallet_id, "normalized_wallet_id": key, "address": addr}

@router.post("/register-wallet-address")
async def register_wallet_address(body: WalletAddressRegisterBody):
    if not _is_base58(body.address):
        raise HTTPException(status_code=400, detail="address does not look like a valid base58 Solana public key")
    reg = _addr_load()
    key = _norm(body.wallet_id)
    reg[key] = body.address
    _addr_save(reg)
    return {"registered": True, "wallet_id": body.wallet_id, "normalized_wallet_id": key, "address": body.address}

# ============ launcher-backed open / connect / select ========================
DEFAULT_JUP = "https://jup.ag/perps"

class BrowserOpenRequest(BaseModel):
    url: str | None = None
    wallet_id: str | None = None
    channel: str | None = None
    chrome_profile_directory: str | None = None

@router.post("/open-browser")
async def open_browser(req: BrowserOpenRequest):
    """
    Launch the dedicated profile via the launcher and wait briefly for the Chrome
    CDP port to be reachable. If a session (port) is already up, reuse it.
    """
    url = (req.url or DEFAULT_JUP).strip()
    alias = (req.wallet_id or os.getenv("SONIC_AUTOPROFILE", "Sonic - Auto")).strip()
    py = sys.executable
    cdp_port = int(os.getenv("SONIC_CHROME_PORT", "9230"))

    # If the CDP port is already listening, assume session is alive and return.
    if _is_listening(cdp_port):
        st = _state_read()
        meta = st.get(alias.lower(), {})
        return {
            "ok": True, "launched": alias, "pid": meta.get("pid"),
            "url": url, "cmd": meta.get("cmd"), "cdp_port": cdp_port, "port_ready": True,
            "reused": True
        }

    # Do NOT pre-kill here — avoid races that close a fresh Chrome
    cmd = [py, "-m", "auto_core.launcher.open_jupiter", "--wallet-id", alias, "--url", url]
    print(f"[DEBUG] /open-browser launching: {cmd}")

    # Log Chrome/launcher output for post-mortem if it exits
    log_path = LOG_DIR / "launcher.log"
    log_file = open(log_path, "ab", buffering=0)

    try:
        if os.name == "nt":
            # Keep it lightweight: new process group, no DETACHED flag so Windows
            # won’t kill Chrome’s child when the launcher prints and exits unusually.
            p = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                cwd=os.getcwd(),
                stdout=log_file,
                stderr=log_file
            )
        else:
            p = subprocess.Popen(
                cmd,
                start_new_session=True,
                cwd=os.getcwd(),
                stdout=log_file,
                stderr=log_file
            )
    except Exception as e:
        log_file.close()
        raise HTTPException(status_code=500, detail=f"launcher failed: {e}")

    # Record state and wait a moment for CDP
    st = _state_read()
    st[alias.lower()] = {"pid": p.pid, "cmd": cmd, "cwd": os.getcwd(), "started_at": int(time.time()),
                         "log": str(log_path)}
    _state_write(st)

    port_ready = _wait_port(cdp_port, "127.0.0.1", deadline_s=8.0)
    # We intentionally do NOT kill on failure — check launcher.log if needed.
    return {
        "ok": True,
        "launched": alias,
        "pid": p.pid,
        "url": url,
        "cmd": cmd,
        "cdp_port": cdp_port,
        "port_ready": port_ready,
        "log": str(log_path)
    }

# connect step
try:
    from auto_core.steps.connect_jupiter_solflare import main as _do_connect
except Exception as e:
    _do_connect = None
    print(f"[WARN] connect_jupiter_solflare not importable: {e}")

class JupiterParams(BaseModel):
    url: str | None = DEFAULT_JUP

@router.post("/connect-jupiter")
async def connect_jupiter(req: JupiterParams):
    if _do_connect is None:
        raise HTTPException(status_code=501, detail="connect_jupiter_solflare step not available")
    print(f"[DEBUG] /connect-jupiter (url={req.url or DEFAULT_JUP}) → Playwright")
    rc = await anyio.to_thread.run_sync(_do_connect)
    return {"ok": rc == 0, "rc": rc}

# select-asset step
try:
    from auto_core.steps.select_asset import main as _select_asset
except Exception as e:
    _select_asset = None
    print(f"[WARN] select_asset not importable: {e}")

class SelectAssetBody(BaseModel):
    symbol: str

@router.post("/select-asset")
async def select_asset(body: SelectAssetBody):
    if _select_asset is None:
        raise HTTPException(status_code=501, detail="select_asset step not available")
    print(f"[DEBUG] /select-asset symbol={body.symbol}")
    rc = await anyio.to_thread.run_sync(_select_asset, body.symbol)
    return {"ok": rc == 0, "rc": rc}

# ============ Solflare unlock (force-type) ==================================
try:
    from auto_core.steps.solflare_unlock_only import main as _solflare_unlock
except Exception as e:
    _solflare_unlock = None
    print(f"[WARN] solflare_unlock_only not importable: {e}")

@router.post("/solflare-unlock")
async def solflare_unlock():
    if _solflare_unlock is None:
        raise HTTPException(status_code=501, detail="solflare_unlock_only step not available")
    print("[DEBUG] /solflare-unlock → force unlock")
    rc = await anyio.to_thread.run_sync(_solflare_unlock)
    return {"ok": rc == 0, "rc": rc}

# ============ status / close ================================================
@router.get("/jupiter-status")
async def jupiter_status():
    return {"sessions": _state_read()}

@router.post("/close-browser")
async def close_browser():
    st = _state_read()
    closed = []
    for k, v in list(st.items()):
        pid = v.get("pid")
        if isinstance(pid, int) and pid > 0:
            _kill(pid)
            closed.append(pid)
            st.pop(k, None)
    _state_write(st)
    return {"ok": True, "closed_pids": closed}

# ============ optional generic runner (compat) ===============================
class AutoCoreRunRequest(BaseModel):
    request_type: str
    params: Dict[str, Any] | None = None

@router.post("/run-request")
async def run_request(req: AutoCoreRunRequest):
    try:
        mod = import_module("backend.core.auto_core.requests")
        cls = getattr(mod, req.request_type)
    except Exception:
        raise HTTPException(status_code=400, detail="unknown request_type")
    return {"ok": True, "detail": f"placeholder run for {req.request_type}"}
