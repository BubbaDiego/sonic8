# backend/routes/jupiter_perps_api.py
from __future__ import annotations

from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator
import anyio

from backend.services.perps.markets import list_markets_sync
from backend.services.perps.positions import list_positions_sync
from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names
from backend.services.perps.config import get_disc, get_account_name
from backend.services.signer_loader import load_signer
from backend.services.perps.positions_request import open_position_request, close_position_request

try:  # optional service (not yet wired everywhere)
    from backend.services.perps.order_submit import submit_increase_request, submit_close_request
    _ORDER_SERVICE_AVAILABLE = True
except Exception:  # pragma: no cover - best effort import guard
    submit_increase_request = submit_close_request = None
    _ORDER_SERVICE_AVAILABLE = False

# tiny base58 encoder (same as service)
_B58_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def _b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    if n == 0:
        res = _B58_ALPH[0]
    else:
        chars = []
        while n:
            n, r = divmod(n, 58)
            chars.append(_B58_ALPH[r])
        res = "".join(reversed(chars))
    leading = 0
    for ch in b:
        if ch == 0: leading += 1
        else: break
    return (_B58_ALPH[0] * leading) + res


router = APIRouter(prefix="/api/perps", tags=["perps"])


class PerpOrderRequest(BaseModel):
    market: str = Field(..., min_length=1)
    side: Literal['long', 'short']
    sizeUsd: float = Field(..., gt=0)
    collateralUsd: float = Field(..., gt=0)
    tp: Optional[float] = None
    sl: Optional[float] = None

    @validator('tp', 'sl')
    def _positive_optional(cls, value):
        if value is not None and value <= 0:
            raise ValueError('must be > 0 when provided')
        return value


class PerpCloseRequest(BaseModel):
    market: str = Field(..., min_length=1)


@router.get("/markets")
async def perps_markets():
    try:
        return await anyio.to_thread.run_sync(list_markets_sync)
    except Exception as e:
        raise HTTPException(502, f"markets fetch failed: {e}")


@router.get("/positions")
async def perps_positions(owner: Optional[str] = Query(None, description="owner pubkey")):
    try:
        return await anyio.to_thread.run_sync(list_positions_sync, owner)
    except Exception as e:
        raise HTTPException(502, f"positions fetch failed: {e}")


@router.post("/order")
async def perps_create_order(req: PerpOrderRequest):
    if not _ORDER_SERVICE_AVAILABLE:
        raise HTTPException(501, "Perps order submission not configured on server.")
    try:
        result = await anyio.to_thread.run_sync(submit_increase_request, req.dict())
        if result is None:
            return {"ok": True}
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"perps order failed: {e}")


@router.post("/close")
async def perps_close_position(req: PerpCloseRequest):
    if not _ORDER_SERVICE_AVAILABLE:
        raise HTTPException(501, "Perps close submission not configured on server.")
    try:
        result = await anyio.to_thread.run_sync(submit_close_request, req.dict())
        if result is None:
            return {"ok": True}
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"perps close failed: {e}")


@router.get("/positions/detailed")
async def perps_positions_detailed(owner: str, limit: int = 50, debug: int = 0):
    """
    Decode fields for owner positions (size, entry, mark, est PnL).
    v2: NEVER throws. Returns JSON with ok/err. Set debug=1 to include traceback.
    """
    import anyio, traceback
    try:
        from backend.services.perps.detail import fetch_positions_detailed_v2
    except Exception as e:
        return {"ok": False, "version": "v2", "error": f"import failed: {type(e).__name__}: {e}"}

    try:
        data = await anyio.to_thread.run_sync(fetch_positions_detailed_v2, owner, limit)
        # ensure version flag is present so we know this path executed
        if isinstance(data, dict):
            data.setdefault("version", "v2")
            return data
        # unexpected non-dict return
        return {"ok": False, "version": "v2", "error": f"unexpected return type: {type(data).__name__}"}
    except Exception as e:
        return {
            "ok": False,
            "version": "v2",
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc() if debug else None
        }


@router.get("/debug/idl")
async def perps_idl_debug():
    try:
        pid = get_program_id()
        names = get_idl_account_names()
        return {"programId": pid, "accounts": names}
    except Exception as e:
        raise HTTPException(500, f"idl debug failed: {e}")


@router.get("/debug/owner-offset")
async def perps_owner_offset(owner: str, start: int = 8, stop: int = 192, step: int = 1, sample: int = 1):
    """
    Probe the correct byte offset of the `owner` field in Position account:
    Tries memcmp(discriminator) AND memcmp(owner@offset) across a small range
    and returns the first offsets that yield results.

    Example: /api/perps/debug/owner-offset?owner=YourPubkey&start=8&stop=192&step=4
    """
    try:
        pid = get_program_id()
        pos_name = get_account_name("position", "Position")
        disc_b58 = _b58encode(get_disc("position", pos_name))

        hits = []
        for off in range(max(0, start), max(0, stop), max(1, step)):
            params = {
                "encoding": "base64",
                "commitment": "confirmed",
                "filters": [
                    {"memcmp": {"offset": 0, "bytes": disc_b58}},
                    {"memcmp": {"offset": off, "bytes": owner}}
                ]
            }
            res = await anyio.to_thread.run_sync(_rpc, "getProgramAccounts", [pid, params])
            count = len(res or [])
            if count > 0:
                hits.append({"offset": off, "count": count})
                if sample == 1:
                    break

        return {
            "programId": pid,
            "positionAccountName": pos_name,
            "owner": owner,
            "hits": hits,
            "note": ("Set PERPS_POSITION_OWNER_OFFSET=<offset> to pin it. "
                     "Then /api/perps/positions will return only your positions.")
        }
    except Exception as e:
        raise HTTPException(500, f"owner offset probe failed: {e}")


# --- APPEND: “real” PositionRequest endpoints -------------------------------
class _OpenReq(BaseModel):
    market: str = Field(..., description="e.g., SOL-PERP | BTC-PERP | ETH-PERP")
    side: Literal["long", "short"]
    sizeUsd: float = Field(..., gt=0)
    collateralUsd: float = Field(..., gt=0)
    tp: Optional[float] = Field(None, description="TP price (optional)")
    sl: Optional[float] = Field(None, description="SL price (optional)")


class _CloseReq(BaseModel):
    market: str = Field(..., description="e.g., SOL-PERP | BTC-PERP | ETH-PERP")


@router.post("/order/open")
def perps_order_open(req: _OpenReq):
    try:
        w = load_signer()
        return open_position_request(
            wallet=w,
            market=req.market,
            side=req.side,
            size_usd=req.sizeUsd,
            collateral_usd=req.collateralUsd,
            tp=req.tp,
            sl=req.sl,
        )
    except Exception as e:
        raise HTTPException(500, f"perps open failed: {type(e).__name__}: {e}")


@router.post("/order/close")
def perps_order_close(req: _CloseReq):
    try:
        w = load_signer()
        return close_position_request(wallet=w, market=req.market)
    except Exception as e:
        raise HTTPException(500, f"perps close failed: {type(e).__name__}: {e}")
