# backend/routes/jupiter_api.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
import time

from backend.services.signer_loader import load_signer
from backend.services.jupiter_trigger import (
    MINTS, compute_amounts, create_order_and_tx, sign_tx_b64,
    broadcast_via_rpc, broadcast_via_execute, get_orders, cancel_order
)
from backend.services.jupiter_swap import get_quote, build_swap_tx, sign_and_send
from backend.services.profit_watcher import WATCHER

router = APIRouter(prefix="/api/jupiter", tags=["jupiter"])

class SpotTriggerRequest(BaseModel):
    inputMint: Optional[str] = None
    outputMint: Optional[str] = None
    inputSymbol: Optional[str] = None
    outputSymbol: Optional[str] = None
    amount: float
    stopPrice: float
    slippageBps: Optional[int] = None
    expirySeconds: Optional[int] = None
    sendMode: Literal['execute', 'rpc'] = 'execute'
    rpcUrl: Optional[str] = None

@router.post('/trigger/create')
def create_trigger(req: SpotTriggerRequest):
    wallet = load_signer()
    # resolve mints
    if req.inputMint and req.outputMint:
        in_mint, out_mint = req.inputMint, req.outputMint
        # naive decimals: infer from known symbols if available (fallback to SOL/USDC when unknown)
        in_dec = 9 if in_mint == MINTS['SOL']['mint'] else 6 if in_mint == MINTS['USDC']['mint'] else 9
        out_dec = 6 if out_mint == MINTS['USDC']['mint'] else 9 if out_mint == MINTS['SOL']['mint'] else 6
    else:
        in_sym = (req.inputSymbol or 'SOL').upper()
        out_sym = (req.outputSymbol or 'USDC').upper()
        if in_sym not in MINTS or out_sym not in MINTS:
            raise HTTPException(400, 'Unsupported symbols; provide inputMint/outputMint explicitly.')
        in_mint, out_mint = MINTS[in_sym]['mint'], MINTS[out_sym]['mint']
        in_dec, out_dec = MINTS[in_sym]['decimals'], MINTS[out_sym]['decimals']

    making, taking = int(req.amount * (10 ** in_dec)), int(req.amount * req.stopPrice * (10 ** out_dec))
    payload = create_order_and_tx(
        wallet=wallet,
        input_mint=in_mint,
        output_mint=out_mint,
        making_amount=making,
        taking_amount=taking,
        slippage_bps=req.slippageBps,
        expiry_unix=(int(time.time()) + req.expirySeconds) if req.expirySeconds else None,
        wrap_unwrap_sol=True
    )
    tx_b64 = payload.get('transaction')
    order = payload.get('order')
    request_id = payload.get('requestId')
    if not tx_b64 or not order or not request_id:
        raise HTTPException(500, f'Unexpected response from Jupiter: {payload}')

    signed = sign_tx_b64(tx_b64, wallet)
    if req.sendMode == 'rpc':
        if not req.rpcUrl:
            raise HTTPException(400, 'rpcUrl is required when sendMode=rpc')
        bres = broadcast_via_rpc(signed, req.rpcUrl)
    else:
        bres = broadcast_via_execute(signed, request_id)

    return {'order': order, 'requestId': request_id, 'broadcast': bres}

@router.get('/trigger/orders')
def trigger_orders(status: Optional[str] = None):
    wallet = load_signer()
    return get_orders(str(wallet.pubkey()), status=status)

class CancelRequest(BaseModel):
    order: str

@router.post('/trigger/cancel')
def trigger_cancel(req: CancelRequest):
    wallet = load_signer()
    return cancel_order(wallet, req.order)

# ---- Perps placeholders ----
class PerpAttachRequest(BaseModel):
    market: str
    side: Literal['long', 'short']
    triggerPrice: float
    direction: Literal['<=', '>='] = '<='
    entirePosition: bool = True

@router.post('/perps/attach-trigger')
def perps_attach_trigger(_req: PerpAttachRequest):
    # Placeholder: to be implemented with Anchor/IDL
    raise HTTPException(501, 'Perps TP/SL not implemented yet.')

@router.get('/perps/positions')
def perps_positions():
    # Placeholder list
    return {'positions': []}

# --- SWAP API (headless) ---
class SwapQuoteReq(BaseModel):
    inputMint: str
    outputMint: str
    amount: int           # atomic units (respect inputMint decimals)
    slippageBps: int = 50
    swapMode: str = "ExactIn"
    restrictIntermediates: bool = True


@router.post('/swap/quote')
def swap_quote(req: SwapQuoteReq):
    return get_quote(
        input_mint=req.inputMint,
        output_mint=req.outputMint,
        amount=req.amount,
        swap_mode=req.swapMode,
        slippage_bps=req.slippageBps,
        restrict_intermediates=req.restrictIntermediates,
    )


class SwapExecReq(BaseModel):
    # Either pass {inputMint, outputMint, amount,...} to auto-quote,
    # or provide a full quoteResponse you obtained earlier.
    inputMint: Optional[str] = None
    outputMint: Optional[str] = None
    amount: Optional[int] = None
    slippageBps: int = 50
    swapMode: str = "ExactIn"
    restrictIntermediates: bool = True
    quoteResponse: Optional[dict] = None
    dynamicSlippageMaxBps: Optional[int] = None
    jitoTipLamports: Optional[int] = None


@router.post('/swap/execute')
def swap_execute(req: SwapExecReq):
    wallet = load_signer()
    qr = req.quoteResponse or get_quote(
        input_mint=req.inputMint, output_mint=req.outputMint, amount=req.amount,
        swap_mode=req.swapMode, slippage_bps=req.slippageBps,
        restrict_intermediates=req.restrictIntermediates,
    )
    tx_resp = build_swap_tx(
        quote_response=qr,
        user_pubkey=str(wallet.pubkey()),
        dynamic_slippage_max_bps=req.dynamicSlippageMaxBps,
        jito_tip_lamports=req.jitoTipLamports,
        wrap_unwrap_sol=True,
    )
    tx_b64 = tx_resp.get('swapTransaction') or tx_resp.get('transaction')
    if not tx_b64:
        raise HTTPException(500, f"Jupiter swap build had no transaction field: {tx_resp}")
    sent = sign_and_send(tx_b64, wallet)
    return {"signature": sent["signature"], "quote": qr, "txMeta": {k: v for k, v in tx_resp.items() if k not in ('swapTransaction', 'transaction')}}


@router.post('/swap/watcher/start')
def watcher_start():
    WATCHER.start()
    return WATCHER.status()


@router.post('/swap/watcher/stop')
def watcher_stop():
    WATCHER.stop()
    return WATCHER.status()


@router.get('/swap/watcher/status')
def watcher_status():
    return WATCHER.status()
