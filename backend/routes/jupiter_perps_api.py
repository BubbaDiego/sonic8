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
from backend.services.perps.position_probe import probe_position, idl_summary

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
        summary = idl_summary()
        names = get_idl_account_names()
        account_count = summary.get("accounts", len(names))
        return {
            "programId": summary.get("programId"),
            "instructions": summary.get("instructions"),
            "accounts": account_count,
            "accountNames": names,
        }
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


@router.get("/positions/raw")
def perps_positions_raw(wallet: str | None = None):
    """
    Fetch raw Jupiter positions JSON for debugging (defaults to server signer).
    """

    try:
        from backend.services.signer_loader import load_signer
        import os, requests
        from backend.core.core_constants import JUPITER_API_BASE

        base = (os.getenv("JUPITER_PERPS_API_BASE", "").strip() or JUPITER_API_BASE).rstrip("/")
        owner = wallet or str(load_signer().pubkey())
        url = f"{base}/v1/positions?walletAddress={owner}&showTpslRequests=true"
        response = requests.get(url, headers={"User-Agent": "Cyclone/PerpsRaw"}, timeout=12)
        response.raise_for_status()
        return {"url": url, "json": response.json()}
    except Exception as exc:
        raise HTTPException(502, f"raw fetch failed: {exc}")


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


# ---- DEBUG / PROBE endpoints (non-breaking additions) ----------------------


@router.get("/position/by-market")
def perps_position_by_market(
    market: str = Query(..., description="e.g., SOL-PERP | BTC-PERP | ETH-PERP"),
    owner: str | None = Query(None, description="override owner; default = server signer pubkey"),
):
    """
    Derives the position PDA for (owner, market) and checks if the account exists.
    Default owner is the server signer (same wallet you see in /api/jupiter/whoami).
    """
    try:
        if not owner:
            w = load_signer()
            owner = str(w.pubkey())
        return probe_position(owner, market)
    except Exception as e:
        raise HTTPException(500, f"position probe failed: {e}")

from fastapi import HTTPException, Query

@router.get("/positions/db")
def perps_positions_from_db(limit: int = 20, only_active: bool = True, wallet: str | None = None):
    """
    Dump positions directly from the DB so we can confirm whether the sync wrote rows.
    - only_active=True filters status='ACTIVE' (what most panels expect)
    - wallet can filter by wallet_name, if you want (e.g., 'Signer')
    """
    try:
        from backend.data.data_locker import DataLocker
        dl = DataLocker()  # uses the same DB path your app already uses
        cur = dl.db.get_cursor()
        if cur is None:
            raise RuntimeError("DB cursor unavailable")

        where = []
        params = {}
        if only_active:
            where.append("status = 'ACTIVE'")
        if wallet:
            where.append("wallet_name = :wallet")
            params["wallet"] = wallet
        clause = "WHERE " + " AND ".join(where) if where else ""
        cur.execute(
            f"""
            SELECT id, asset_type, position_type, size, collateral, status, wallet_name, last_updated
            FROM positions
            {clause}
            ORDER BY last_updated DESC
            LIMIT :limit
            """,
            {**params, "limit": max(1, min(limit, 200))}
        )
        rows = cur.fetchall()
        dl.db.commit()
        cur.close()
        # shape rows for JSON
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append(r)
            else:
                # sqlite3.Row as tuple
                out.append({
                    "id": r[0], "asset_type": r[1], "position_type": r[2],
                    "size": r[3], "collateral": r[4], "status": r[5],
                    "wallet_name": r[6], "last_updated": r[7]
                })
        return {"count": len(out), "items": out}
    except Exception as e:
        raise HTTPException(500, f"DB probe failed: {e}")

# --- Perps Positions: detailed view for the UI -------------------------------
import os
from typing import Optional, Any, Dict, List
import requests
from fastapi import Query, HTTPException
from backend.services.signer_loader import load_signer

def _perps_base() -> str:
    base = (os.getenv("JUPITER_PERPS_API_BASE", "").strip() or os.getenv("JUPITER_API_BASE", "")).rstrip("/")
    if "perps-api" not in base:
        base = "https://perps-api.jup.ag"
    return base

def _to_float(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

def _extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    # common shapes from perps-api
    for k in ("dataList", "data", "positions", "items", "result"):
        v = payload.get(k)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for kk in ("items", "data", "list"):
                vv = v.get(kk)
                if isinstance(vv, list):
                    return vv
    # single object fallback
    if any(k in payload for k in ("positionPubkey", "id", "position")):
        return [payload]
    return []

@router.get("/positions/detailed")
def perps_positions_detailed(
    owner: Optional[str] = Query(None, description="Wallet pubkey; defaults to server signer"),
    limit: int = Query(50, ge=1, le=500)
):
    """
    Return positions in the exact shape expected by the Perps PositionsPanel:
    {
      "count": N,
      "items": [
        { "pubkey", "side", "size", "entry", "mark", "pnlUsd" }, ...
      ]
    }
    """
    try:
        if not owner:
            owner = str(load_signer().pubkey())
        base = _perps_base()
        url = f"{base}/v1/positions?walletAddress={owner}&showTpslRequests=true"
        r = requests.get(url, headers={"User-Agent": "Cyclone/PerpsDetailed"}, timeout=12)
        r.raise_for_status()
        payload = r.json() or {}
    except Exception as e:
        raise HTTPException(502, f"perps-api fetch failed: {e}")

    raw_items = _extract_items(payload)
    out: List[Dict[str, Any]] = []
    for it in raw_items[:limit]:
        pubkey = it.get("positionPubkey") or it.get("position") or it.get("id")
        side   = it.get("side")
        size   = _to_float(it.get("size"))
        entry  = _to_float(it.get("entryPrice") or it.get("entry"))
        mark   = _to_float(it.get("markPrice") or it.get("mark"))
        pnlUsd = _to_float(it.get("pnlAfterFeesUsd") or it.get("pnlAfterFees") or it.get("pnl"), 0.0)
        out.append({
            "pubkey": pubkey,
            "side": side,
            "size": size,
            "entry": entry,
            "mark": mark,
            "pnlUsd": pnlUsd
        })

    return {"count": len(out), "items": out}

# ──────────────────────────────────────────────────────────────────────────────
# 🔧 Perps Positions — DEBUG+Health endpoints (console logging)
# ──────────────────────────────────────────────────────────────────────────────
import os, json, time, requests
from typing import Optional, Any, Dict, List
from fastapi import Query, HTTPException, Request
from backend.services.signer_loader import load_signer

def _perps_base() -> str:
    base = (os.getenv("JUPITER_PERPS_API_BASE", "").strip() or os.getenv("JUPITER_API_BASE", "")).rstrip("/")
    if "perps-api" not in base:
        base = "https://perps-api.jup.ag"
    return base

def _to_float(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

def _extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Accept common shapes from perps-api
    if not isinstance(payload, dict):
        return []
    for k in ("dataList", "data", "positions", "items", "result"):
        v = payload.get(k)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for kk in ("items", "data", "list"):
                vv = v.get(kk)
                if isinstance(vv, list):
                    return vv
    if any(k in payload for k in ("positionPubkey", "id", "position")):
        return [payload]
    return []

@router.get("/positions/health")
def perps_positions_health():
    """Small probe to confirm signer, perps base, and raw count."""
    try:
        owner = str(load_signer().pubkey())
        base = _perps_base()
        url = f"{base}/v1/positions?walletAddress={owner}&showTpslRequests=true"
        r = requests.get(url, headers={"User-Agent":"Cyclone/PerpsHealth"}, timeout=12)
        r.raise_for_status()
        payload = r.json() or {}
        items = _extract_items(payload)
        return {"owner": owner, "base": base, "url": url, "count": len(items)}
    except Exception as e:
        raise HTTPException(502, f"health failed: {e}")

@router.get("/positions/detailed")
def perps_positions_detailed(
    request: Request,
    owner: Optional[str] = Query(None, description="Wallet pubkey; defaults to server signer"),
    limit: int = Query(50, ge=1, le=500),
    debug: int = Query(0, description="Set to 1 to print loud server logs and echo raw")
):
    """
    Returns exactly what the Perps PositionsPanel expects:
      { "count": N, "items": [ { pubkey, side, size, entry, mark, pnlUsd }, ... ] }
    """
    t0 = time.time()
    try:
        if not owner:
            owner = str(load_signer().pubkey())
        base = _perps_base()
        url = f"{base}/v1/positions?walletAddress={owner}&showTpslRequests=true"
        r = requests.get(url, headers={"User-Agent":"Cyclone/PerpsDetailed"}, timeout=12)
        r.raise_for_status()
        payload = r.json() or {}
    except Exception as e:
        print(f"[PerpsDetailed][{time.strftime('%H:%M:%S')}] ERROR fetch → {type(e).__name__}: {e}")
        raise HTTPException(502, f"perps-api fetch failed: {e}")

    raw_items = _extract_items(payload)
    out: List[Dict[str, Any]] = []
    for it in raw_items[:limit]:
        pubkey = it.get("positionPubkey") or it.get("position") or it.get("id")
        side   = it.get("side")
        size   = _to_float(it.get("size"))
        entry  = _to_float(it.get("entryPrice") or it.get("entry"))
        mark   = _to_float(it.get("markPrice") or it.get("mark"))
        pnlUsd = _to_float(it.get("pnlAfterFeesUsd") or it.get("pnlAfterFees") or it.get("pnl"), 0.0)
        out.append({"pubkey": pubkey, "side": side, "size": size, "entry": entry, "mark": mark, "pnlUsd": pnlUsd})

    dt = (time.time() - t0) * 1000
    if debug:
        ua = request.headers.get("user-agent", "")
        sample = (raw_items[0] if raw_items else {})
        print(
            f"[PerpsDetailed][{time.strftime('%H:%M:%S')}] "
            f"owner={owner} base={base} ua='{ua[:60]}'\n"
            f"→ url={url}\n"
            f"→ raw.count={len(raw_items)} sample.pubkey={sample.get('positionPubkey')}\n"
            f"→ shaped.count={len(out)} in {dt:.1f} ms\n"
        )
        # also echo the raw back to caller so you can diff client-side quickly
        return {"count": len(out), "items": out, "debug": {"url": url, "rawCount": len(raw_items), "raw": raw_items[:5]}}

    print(f"[PerpsDetailed][{time.strftime('%H:%M:%S')}] owner={owner} shaped.count={len(out)} in {dt:.1f} ms")
    return {"count": len(out), "items": out}
