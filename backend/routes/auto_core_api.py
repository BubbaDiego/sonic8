from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from importlib import import_module
from typing import Any, Dict
from pathlib import Path
import json, re

from backend.core.auto_core import AutoCore, WebBrowserRequest
from backend.core.auto_core.requests import (
    JupiterConnectRequest,
    CloseBrowserRequest,
    RegisterWalletRequest,
    WebBrowserWithWalletRequest,
    CloseWalletRequest,
    ListWalletsRequest,
)

router = APIRouter(prefix="/api/auto-core", tags=["auto_core"])

# ---------------- Wallet ID → Address registry ------------------------------
ADDR_REG_PATH = Path(".cache/wallet_addresses.json")
BASE58 = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")

def _norm(wid: str | None) -> str | None:
    if wid is None:
        return None
    return wid.strip().lower().replace(" ", "-")

def _addr_load() -> dict:
    try:
        if ADDR_REG_PATH.exists():
            return json.loads(ADDR_REG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _addr_save(d: dict) -> None:
    ADDR_REG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADDR_REG_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")

def _is_probably_base58(s: str) -> bool:
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
    if not _is_probably_base58(body.address):
        raise HTTPException(status_code=400, detail="address does not look like a valid base58 Solana public key")
    reg = _addr_load()
    key = _norm(body.wallet_id)
    reg[key] = body.address
    _addr_save(reg)
    return {"registered": True, "wallet_id": body.wallet_id, "normalized_wallet_id": key, "address": body.address}

class WalletAddressDeleteBody(BaseModel):
    wallet_id: str

@router.post("/unregister-wallet-address")
async def unregister_wallet_address(body: WalletAddressDeleteBody):
    reg = _addr_load()
    key = _norm(body.wallet_id)
    existed = reg.pop(key, None) is not None
    _addr_save(reg)
    return {"removed": existed, "wallet_id": body.wallet_id, "normalized_wallet_id": key}

class BrowserOpenRequest(BaseModel):
    url: str | None = None
    channel: str | None = None
    wallet_id: str | None = None
    chrome_profile_directory: str | None = None

@router.post("/open-browser")
async def open_browser(req: BrowserOpenRequest):
    """
    Launches Chromium with (optional) Solflare extension and returns page meta.
    """
    core = AutoCore()
    if req.wallet_id:
        request_obj = WebBrowserWithWalletRequest(
            url=req.url or "https://jup.ag/perps",
            wallet_id=req.wallet_id,
            channel=req.channel,
            chrome_profile_directory=req.chrome_profile_directory,
        )
    else:
        request_obj = WebBrowserRequest(
            url=req.url or "https://jup.ag/perps",
            channel=req.channel,
        )
    return await core.run(request_obj)


# --- New: one-click Jupiter connect ----------------------------------------
class JupiterParams(BaseModel):
    url: str | None = "https://jup.ag/perps"
    wallet: str | None = "solflare"
    channel: str | None = None
    wallet_id: str | None = None
    chrome_profile_directory: str | None = None


@router.post("/connect-jupiter")
async def connect_jupiter(req: JupiterParams):
    core = AutoCore()
    req_obj = JupiterConnectRequest(
        url=req.url or "https://jup.ag/perps",
        wallet=req.wallet,
        channel=req.channel,
        wallet_id=req.wallet_id,
        chrome_profile_directory=req.chrome_profile_directory,
    )
    return await core.run(req_obj)


# --- Wallet registry/listing -------------------------------------------------
@router.post("/list-wallets")
async def list_wallets():
    core = AutoCore()
    return await core.run(ListWalletsRequest())


# --- New: close the persistent browser -------------------------------------
@router.post("/close-browser")
async def close_browser():
    core = AutoCore()
    return await core.run(CloseBrowserRequest())

# ---- Wallet mgmt ------------------------------------------------------------
class WalletRegisterBody(BaseModel):
    wallet_id: str
    profile_dir: str | None = None
    channel: str | None = None  # e.g., "chrome"
    chrome_profile_directory: str | None = None  # e.g., "Profile 3"


@router.post("/register-wallet")
async def register_wallet(body: WalletRegisterBody):
    core = AutoCore()
    req = RegisterWalletRequest(
        body.wallet_id,
        body.profile_dir,
        body.channel,
        body.chrome_profile_directory,
    )
    return await core.run(req)


class WalletCloseBody(BaseModel):
    wallet_id: str


@router.post("/close-wallet")
async def close_wallet(body: WalletCloseBody):
    core = AutoCore()
    return await core.run(CloseWalletRequest(body.wallet_id))


class AutoCoreRunRequest(BaseModel):
    request_type: str
    params: Dict[str, Any] | None = None


@router.post("/run-request")
async def run_request(req: AutoCoreRunRequest):
    core = AutoCore()
    try:
        mod = import_module("backend.core.auto_core.requests")
        cls = getattr(mod, req.request_type)
    except Exception:
        raise HTTPException(status_code=400, detail="unknown request_type")

    params = req.params or {}
    try:
        request_obj = cls(**params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await core.run(request_obj)
