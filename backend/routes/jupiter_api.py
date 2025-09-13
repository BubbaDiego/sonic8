from __future__ import annotations

import os
import time
import requests
from typing import Optional, Literal, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.signer_loader import load_signer, signer_info, diagnose_signer
from backend.services.jupiter_swap import (
    get_quote, build_swap_tx, sign_and_send,
    get_wallet_balance_lamports, estimate_sol_spend_lamports,
    get_portfolio, TOKENS, RPC_URL, project_round_trip, log_swap
)
from backend.services import txlog

# Trigger API (optional)
try:
    from backend.services.jupiter_trigger import (
        MINTS, create_order_and_tx, sign_tx_b64,
        broadcast_via_rpc, broadcast_via_execute, get_orders, cancel_order
    )
    _TRIGGER_AVAILABLE = True
except Exception:
    _TRIGGER_AVAILABLE = False

router = APIRouter(prefix="/api/jupiter", tags=["jupiter"])

# ---------- health / signer / debug ----------
@router.get("/health")
def health():
    return {"ok": True, "triggerApi": _TRIGGER_AVAILABLE, "rpcUrl": RPC_URL}

@router.get("/signer/info")
def api_signer_info():
    try:
        _ = load_signer()
    except Exception:
        pass
    return signer_info()

@router.get("/debug/signer")
def api_debug_signer():
    info = diagnose_signer()
    try:
        kp = load_signer()
        info["load_signer"] = {"ok": True, "pubkey": str(kp.pubkey())}
    except Exception as e:
        info["load_signer"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return info

@router.get("/debug/config")
def api_debug_config():
    return {
        "SONIC_SIGNER_PATH": os.getenv("SONIC_SIGNER_PATH", "signer.txt"),
        "SONIC_MNEMONIC_DERIVE_CMD": os.getenv("SONIC_MNEMONIC_DERIVE_CMD", ""),
        "HELIUS_API_KEY_set": bool(os.getenv("HELIUS_API_KEY")),
        "RPC_URL": os.getenv("RPC_URL", ""),
        "resolvedRpcUrl": RPC_URL,
        "JUP_BASE_URL": os.getenv("JUP_BASE_URL", "https://lite-api.jup.ag"),
        "JUP_API_KEY_set": bool(os.getenv("JUP_API_KEY")),
    }

# ---------- wallet helpers ----------
@router.get("/whoami")
def whoami():
    try:
        w = load_signer()
        return {"pubkey": str(w.pubkey()), "signer": signer_info()}
    except Exception as e:
        raise HTTPException(500, f"Failed to load signer: {e}")

@router.get("/wallet/balance")
def wallet_balance():
    try:
        w = load_signer()
        lamports = get_wallet_balance_lamports(str(w.pubkey()))
        return {"pubkey": str(w.pubkey()), "lamports": lamports, "sol": lamports / 1e9, "signer": signer_info()}
    except Exception as e:
        raise HTTPException(500, f"{e}")

@router.get("/wallet/estimate-sol-spend")
def wallet_estimate_sol_spend(outMint: str):
    try:
        w = load_signer()
        return estimate_sol_spend_lamports(str(w.pubkey()), outMint)
    except Exception as e:
        raise HTTPException(500, f"estimation failed: {e}")

@router.get("/wallet/portfolio")
def wallet_portfolio(mints: Optional[str] = None):
    try:
        w = load_signer()
        lst: Optional[List[str]] = None
        if mints:
            lst = [s.strip() for s in mints.split(",") if s.strip()]
        return get_portfolio(str(w.pubkey()), lst)
    except Exception as e:
        raise HTTPException(500, f"portfolio failed: {e}")

# ---------- price passthrough ----------
@router.get("/price")
def jup_price(id: str, vs: str = "USDC"):
    try:
        r = requests.get("https://price.jup.ag/v6/price",
                         params={"ids": id, "vsToken": vs}, timeout=15)
        r.raise_for_status()
        payload = r.json().get("data", {})
        entry = payload.get(id) or (list(payload.values())[0] if payload else None)
        if not entry or "price" not in entry:
            raise HTTPException(404, f"Price not found for id={id}")
        return {"id": entry.get("id", id), "vs": entry.get("vsToken", vs), "price": float(entry["price"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Price service error: {e}")

# ---------- Trigger API (optional — unchanged other than imports) ----------
class SpotTriggerRequest(BaseModel):
    inputMint: Optional[str] = None
    outputMint: Optional[str] = None
    inputSymbol: Optional[str] = None
    outputSymbol: Optional[str] = None
    amount: float
    stopPrice: float
    slippageBps: Optional[int] = None
    expirySeconds: Optional[int] = None
    sendMode: Literal["execute", "rpc"] = "execute"
    rpcUrl: Optional[str] = None

@router.post("/trigger/create")
def create_trigger(req: SpotTriggerRequest):
    if not _TRIGGER_AVAILABLE:
        raise HTTPException(501, "Trigger API not wired on server.")
    wallet = load_signer()
    if req.amount <= 0 or req.stopPrice <= 0:
        raise HTTPException(400, "amount and stopPrice must be > 0")

    if req.inputMint and req.outputMint:
        in_mint, out_mint = req.inputMint, req.outputMint
        in_dec = 9 if in_mint == TOKENS["SOL"]["mint"] else 6 if in_mint == TOKENS["USDC"]["mint"] else 9
        out_dec = 6 if out_mint == TOKENS["USDC"]["mint"] else 9
    else:
        in_sym = (req.inputSymbol or "SOL").upper()
        out_sym = (req.outputSymbol or "USDC").upper()
        if in_sym not in MINTS or out_sym not in MINTS:
            raise HTTPException(400, "Unsupported symbols; provide inputMint/outputMint explicitly.")
        in_mint, out_mint = MINTS[in_sym]["mint"], MINTS[out_sym]["mint"]
        in_dec, out_dec = MINTS[in_sym]["decimals"], MINTS[out_sym]["decimals"]

    making = int(req.amount * (10 ** in_dec))
    taking = int(req.amount * req.stopPrice * (10 ** out_dec))

    try:
        payload = create_order_and_tx(
            wallet=wallet,
            input_mint=in_mint,
            output_mint=out_mint,
            making_amount=making,
            taking_amount=taking,
            slippage_bps=req.slippageBps,
            expiry_unix=(int(time.time()) + int(req.expirySeconds)) if req.expirySeconds else None,
            wrap_unwrap_sol=True,
        )
        tx_b64 = payload.get("transaction")
        order = payload.get("order")
        request_id = payload.get("requestId")
        if not tx_b64 or not order or not request_id:
            raise HTTPException(500, f"Jupiter returned no transaction/order/requestId: {payload}")

        signed = sign_tx_b64(tx_b64, wallet)
        if req.sendMode == "rpc":
            if not req.rpcUrl:
                raise HTTPException(400, "rpcUrl is required when sendMode=rpc")
            bres = broadcast_via_rpc(signed, req.rpcUrl)
        else:
            bres = broadcast_via_execute(signed, request_id)
        return {"order": order, "requestId": request_id, "broadcast": bres}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Trigger create failed: {e}")

@router.get("/trigger/orders")
def trigger_orders(status: Optional[str] = None, user: Optional[str] = None):
    if not _TRIGGER_AVAILABLE:
        raise HTTPException(501, "Trigger API not wired on server.")
    target = user or str(load_signer().pubkey())
    return get_orders(target, status=status)

class CancelRequest(BaseModel):
    order: str

@router.post("/trigger/cancel")
def trigger_cancel(req: CancelRequest):
    if not _TRIGGER_AVAILABLE:
        raise HTTPException(501, "Trigger API not wired on server.")
    wallet = load_signer()
    try:
        return cancel_order(wallet, req.order)
    except Exception as e:
        raise HTTPException(502, f"Cancel failed: {e}")

# ---------- Swap API with logging ----------
class SwapQuoteReq(BaseModel):
    inputMint: str
    outputMint: str
    amount: int
    slippageBps: int = 50
    swapMode: str = "ExactIn"
    restrictIntermediates: bool = True

@router.post("/swap/quote")
def swap_quote(req: SwapQuoteReq):
    if req.amount <= 0:
        raise HTTPException(400, "Amount must be > 0 (atoms).")
    try:
        return get_quote(
            input_mint=req.inputMint, output_mint=req.outputMint,
            amount=req.amount, swap_mode=req.swapMode,
            slippage_bps=req.slippageBps, restrict_intermediates=req.restrictIntermediates
        )
    except Exception as e:
        raise HTTPException(502, f"Quote failed: {e}")

class SwapExecReq(BaseModel):
    inputMint: Optional[str] = None
    outputMint: Optional[str] = None
    amount: Optional[int] = None
    slippageBps: int = 50
    swapMode: str = "ExactIn"
    restrictIntermediates: bool = True
    quoteResponse: Optional[dict] = None
    dynamicSlippageMaxBps: Optional[int] = None
    jitoTipLamports: Optional[int] = None

@router.post("/swap/execute")
def swap_execute(req: SwapExecReq):
    wallet = load_signer()
    try:
        # Projection (for txlog)
        if req.quoteResponse:
            in_mint = str(req.quoteResponse["inAmount"]["mint"]) if isinstance(req.quoteResponse.get("inAmount", {}), dict) else req.inputMint
            out_mint = req.quoteResponse.get("outMint") or req.outputMint
            amt_atoms = int(req.quoteResponse.get("inAmount", {}).get("amount") or (req.amount or 0))
        else:
            in_mint = req.inputMint; out_mint = req.outputMint; amt_atoms = int(req.amount or 0)

        if not in_mint or not out_mint or not amt_atoms:
            raise HTTPException(400, "Missing inputMint/outputMint/amount for swap.")

        projection = project_round_trip(
            owner_pubkey=str(wallet.pubkey()),
            in_mint=in_mint, out_mint=out_mint,
            amount_atoms=amt_atoms, slippage_bps=req.slippageBps,
            restrict=req.restrictIntermediates
        )

        # Build + send
        qr = req.quoteResponse or get_quote(
            input_mint=in_mint, output_mint=out_mint, amount=amt_atoms,
            swap_mode=req.swapMode, slippage_bps=req.slippageBps,
            restrict_intermediates=req.restrictIntermediates
        )
        tx_resp = build_swap_tx(
            quote_response=qr, user_pubkey=str(wallet.pubkey()),
            dynamic_slippage_max_bps=req.dynamicSlippageMaxBps,
            jito_tip_lamports=req.jitoTipLamports, wrap_unwrap_sol=True
        )
        tx_b64 = tx_resp.get("swapTransaction") or tx_resp.get("transaction")
        if not tx_b64:
            raise HTTPException(500, f"Jupiter returned no transaction: {tx_resp}")
        sent = sign_and_send(tx_b64, wallet)

        # Log actuals
        entry = log_swap(
            owner_pubkey=str(wallet.pubkey()), sig=str(sent["signature"]),
            in_mint=in_mint, out_mint=out_mint, amount_atoms=amt_atoms,
            projection=projection
        )

        return {"signature": sent["signature"], "quote": qr, "txlog": entry}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Swap failed: {e}")

# ---------- txlog endpoints ----------
@router.get("/txlog")
def txlog_list(limit: int = 50):
    try:
        limit = max(1, min(500, limit))
        return {"items": txlog.read_last(limit)}
    except Exception as e:
        raise HTTPException(500, f"txlog error: {e}")

@router.get("/txlog/by-sig")
def txlog_by_sig(sig: str):
    try:
        obj = txlog.find_by_signature(sig)
        if not obj:
            raise HTTPException(404, "not found")
        return obj
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"txlog error: {e}")

@router.get("/txlog/latest")
def txlog_latest():
    try:
        arr = txlog.read_last(1)
        if not arr:
            raise HTTPException(404, "empty")
        return arr[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"txlog error: {e}")
