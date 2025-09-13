from __future__ import annotations
import os, base64, requests
from typing import Any, Dict, Optional
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from solana.rpc.api import Client as SolClient
from solana.rpc.types import TxOpts

JUP_BASE = os.getenv("JUP_BASE_URL", "https://lite-api.jup.ag")  # free tier host
JUP_API_KEY = os.getenv("JUP_API_KEY", "")                       # optional (Pro/Ultra)
RPC_URL = os.getenv("RPC_URL", f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY','')}")

def _jup_headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if JUP_API_KEY:
        h["x-api-key"] = JUP_API_KEY
    return h

def get_quote(*, input_mint: str, output_mint: str, amount: int,
              swap_mode: str = "ExactIn", slippage_bps: int = 50,
              restrict_intermediates: bool = True) -> Dict[str, Any]:
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": str(amount),
        "swapMode": swap_mode,
        "slippageBps": str(slippage_bps),
        "restrictIntermediateTokens": "true" if restrict_intermediates else "false",
    }
    r = requests.get(f"{JUP_BASE}/v6/quote", params=params, timeout=30, headers=_jup_headers())
    r.raise_for_status()
    return r.json()

def build_swap_tx(*, quote_response: Dict[str, Any], user_pubkey: str,
                  dynamic_slippage_max_bps: Optional[int] = None,
                  jito_tip_lamports: Optional[int] = None,
                  wrap_unwrap_sol: bool = True) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "quoteResponse": quote_response,
        "userPublicKey": user_pubkey,
        "wrapAndUnwrapSol": wrap_unwrap_sol,
        "dynamicComputeUnitLimit": True,   # ask Jupiter to size CUs
    }
    if dynamic_slippage_max_bps is not None:
        body["dynamicSlippage"] = {"maxBps": int(dynamic_slippage_max_bps)}
    if jito_tip_lamports:
        body["prioritizationFeeLamports"] = {"jitoTipLamports": int(jito_tip_lamports)}

    r = requests.post(f"{JUP_BASE}/swap/v6/transaction", json=body, timeout=30, headers=_jup_headers())
    r.raise_for_status()
    return r.json()  # contains base64 serialized VersionedTransaction, e.g. {"swapTransaction": "..."} or {"transaction": "..."}

def _sign_tx_b64(tx_b64: str, wallet: Keypair) -> bytes:
    raw = base64.b64decode(tx_b64)
    vtx = VersionedTransaction.from_bytes(raw)
    msg = to_bytes_versioned(vtx.message)
    sig = wallet.sign_message(msg)

    # put our signature into the right slot
    pub = wallet.pubkey()
    sigs = list(vtx.signatures)
    idx = None
    for i, k in enumerate(vtx.message.account_keys):
        if k == pub:
            idx = i; break
    if idx is None:
        if len(sigs) == 1: idx = 0
        else: raise RuntimeError("signer pubkey not found in account_keys")
    sigs[idx] = sig
    vtx.signatures = sigs
    return bytes(vtx)

def sign_and_send(tx_b64: str, wallet: Keypair) -> Dict[str, Any]:
    signed = _sign_tx_b64(tx_b64, wallet)
    cl = SolClient(RPC_URL)
    sig = cl.send_raw_transaction(signed, opts=TxOpts(skip_preflight=True, max_retries=2)).value
    conf = cl.confirm_transaction(sig, commitment="finalized")
    return {"signature": sig, "confirmation": conf}
