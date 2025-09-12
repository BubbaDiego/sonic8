# backend/services/jupiter_trigger.py
from __future__ import annotations
import time, math, base64, requests
from typing import Optional, Dict, Any, Tuple
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from solana.rpc.api import Client as SolClient
from solana.rpc.types import TxOpts

API_BASE = 'https://api.jup.ag'  # consider 'https://lite-api.jup.ag' if needed

MINTS = {
    'SOL':  {'mint': 'So11111111111111111111111111111111111111112', 'decimals': 9},
    'USDC': {'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'decimals': 6},
}

def to_atomic(amount: float, decimals: int) -> int:
    return int(math.floor(amount * (10 ** decimals)))

def compute_amounts(input_sym: str, output_sym: str, amount_in: float, stop_price: float) -> Tuple[int, int]:
    in_dec = MINTS[input_sym]['decimals']
    out_dec = MINTS[output_sym]['decimals']
    making_amount = to_atomic(amount_in, in_dec)
    taking_amount = to_atomic(amount_in * stop_price, out_dec)
    return making_amount, taking_amount

def create_order_and_tx(
    wallet: Keypair,
    input_mint: str,
    output_mint: str,
    making_amount: int,
    taking_amount: int,
    slippage_bps: Optional[int] = None,
    expiry_unix: Optional[int] = None,
    wrap_unwrap_sol: bool = True
) -> Dict[str, Any]:
    payload = {
        'inputMint': input_mint,
        'outputMint': output_mint,
        'maker': str(wallet.pubkey()),
        'payer': str(wallet.pubkey()),
        'params': {
            'makingAmount': str(making_amount),
            'takingAmount': str(taking_amount),
        },
        'computeUnitPrice': 'auto',
        'wrapAndUnwrapSol': wrap_unwrap_sol,
    }
    if slippage_bps is not None:
        payload['params']['slippageBps'] = str(slippage_bps)
    if expiry_unix is not None:
        payload['params']['expiredAt'] = str(expiry_unix)
    r = requests.post(f"{API_BASE}/trigger/v1/createOrder", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def sign_tx_b64(tx_b64: str, wallet: Keypair) -> bytes:
    raw = base64.b64decode(tx_b64)
    vtx = VersionedTransaction.from_bytes(raw)
    msg = to_bytes_versioned(vtx.message)
    sig = wallet.sign_message(msg)
    # mount signature in correct slot
    pub = wallet.pubkey()
    sigs = list(vtx.signatures)
    # find signer index
    idx = None
    for i, k in enumerate(vtx.message.account_keys):
        if k == pub:
            idx = i
            break
    if idx is None:
        # conservative: if only 1 signature, put it at 0
        if len(sigs) == 1:
            idx = 0
        else:
            raise RuntimeError('Signer pubkey not found in account_keys')
    sigs[idx] = sig
    vtx.signatures = sigs
    return bytes(vtx)

def broadcast_via_rpc(signed_tx: bytes, rpc_url: str) -> Dict[str, Any]:
    cl = SolClient(rpc_url)
    sig = cl.send_raw_transaction(signed_tx, opts=TxOpts(skip_preflight=True, max_retries=2)).value
    conf = cl.confirm_transaction(sig, commitment='finalized')
    return {'signature': sig, 'confirmation': conf}

def broadcast_via_execute(signed_tx: bytes, request_id: str) -> Dict[str, Any]:
    tx_b64 = base64.b64encode(signed_tx).decode()
    r = requests.post(f"{API_BASE}/trigger/v1/execute", json={'signedTransaction': tx_b64, 'requestId': request_id}, timeout=30)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {'raw': r.text}

def get_orders(user_pubkey: str, status: Optional[str] = None) -> Dict[str, Any]:
    params = {'user': user_pubkey}
    if status:
        params['orderStatus'] = status
    r = requests.get(f"{API_BASE}/trigger/v1/getTriggerOrders", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def cancel_order(wallet: Keypair, order: str) -> Dict[str, Any]:
    payload = {
        'maker': str(wallet.pubkey()),
        'computeUnitPrice': 'auto',
        'order': order
    }
    r = requests.post(f"{API_BASE}/trigger/v1/cancelOrder", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
