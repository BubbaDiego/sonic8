from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from importlib import import_module
from typing import Any, Dict

from backend.core.auto_core import AutoCore, WebBrowserRequest
from backend.core.auto_core.requests import (
    JupiterConnectRequest,
    CloseBrowserRequest,
    RegisterWalletRequest,
    WebBrowserWithWalletRequest,
    CloseWalletRequest,
)

router = APIRouter(prefix="/api/auto-core", tags=["auto_core"])

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
            url=req.url or "https://example.com",
            wallet_id=req.wallet_id,
            channel=req.channel,
            chrome_profile_directory=req.chrome_profile_directory,
        )
    else:
        request_obj = WebBrowserRequest(
            url=req.url or "https://example.org",
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
