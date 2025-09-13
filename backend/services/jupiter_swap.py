from __future__ import annotations

import os
import base64
import requests
from typing import Dict, Any, Optional, List, Tuple
from time import sleep

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature as Sig
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned

from solana.rpc.api import Client as SolClient
from solana.rpc.types import TxOpts, TokenAccountOpts

from backend.services import txlog  # NEW

# ---------------- RPC URL selection ----------------
def _default_rpc_url() -> str:
    rpc_env = os.getenv("RPC_URL", "").strip()
    if rpc_env:
        return rpc_env
    helius_key = os.getenv("HELIUS_API_KEY", "").strip()
    if helius_key:
        return f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    return "https://api.mainnet-beta.solana.com"

RPC_URL = _default_rpc_url()

# ---------------- Known tokens ----------------
TOKENS: Dict[str, Dict[str, Any]] = {
    "SOL":     {"mint": "So11111111111111111111111111111111111111112", "decimals": 9},
    "USDC":    {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "decimals": 6},
    "mSOL":    {"mint": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  "decimals": 9},
    "JitoSOL": {"mint": "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn", "decimals": 9},
}
MINT_TO_SYM = {v["mint"]: k for k, v in TOKENS.items()}

# ---------------- Jupiter hosts ----------------
JUP_BASE = os.getenv("JUP_BASE_URL", "https://lite-api.jup.ag")
JUP_API_KEY = os.getenv("JUP_API_KEY", "")

def _hdr() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if JUP_API_KEY:
        h["x-api-key"] = JUP_API_KEY
    return h

# ---- resilient endpoints ----
_QUOTE_PATHS: List[str] = ["/swap/v1/quote", "/v6/quote", "/quote/v6"]
_SWAP_TX_PATHS: List[str] = ["/swap/v1/swap", "/swap/v1/transaction", "/swap/v6/transaction", "/v6/swap"]

def _try_get(paths: List[str], params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    last_error = None
    for p in paths:
        url = f"{JUP_BASE}{p}"
        try:
            r = requests.get(url, params=params, timeout=30, headers=_hdr())
            if r.status_code == 404:
                last_error = f"404 on {url}"
                continue
            r.raise_for_status()
            return p, r.json()
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            continue
    raise RuntimeError(f"All quote endpoints failed. Last error: {last_error}")

def _try_post(paths: List[str], body: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    last_error = None
    for p in paths:
        url = f"{JUP_BASE}{p}"
        try:
            r = requests.post(url, json=body, timeout=30, headers=_hdr())
            if r.status_code == 404:
                last_error = f"404 on {url}"
                continue
            r.raise_for_status()
            return p, r.json()
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            continue
    raise RuntimeError(f"All swap tx endpoints failed. Last error: {last_error}")

# ---------------- Quote / Swap ----------------
def get_quote(
    *, input_mint: str, output_mint: str, amount: int,
    swap_mode: str = "ExactIn", slippage_bps: int = 50,
    restrict_intermediates: bool = True,
) -> Dict[str, Any]:
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": str(amount),
        "swapMode": swap_mode,
        "slippageBps": str(slippage_bps),
        "restrictIntermediateTokens": "true" if restrict_intermediates else "false",
    }
    _, payload = _try_get(_QUOTE_PATHS, params)
    return payload

def build_swap_tx(
    *, quote_response: Dict[str, Any], user_pubkey: str,
    dynamic_slippage_max_bps: Optional[int] = None,
    jito_tip_lamports: Optional[int] = None,
    wrap_unwrap_sol: bool = True,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "quoteResponse": quote_response,
        "userPublicKey": user_pubkey,
        "wrapAndUnwrapSol": wrap_unwrap_sol,
        "dynamicComputeUnitLimit": True,
    }
    if dynamic_slippage_max_bps is not None:
        body["dynamicSlippage"] = {"maxBps": int(dynamic_slippage_max_bps)}
    if jito_tip_lamports:
        body["prioritizationFeeLamports"] = {"jitoTipLamports": int(jito_tip_lamports)}
    _, resp = _try_post(_SWAP_TX_PATHS, body)
    return resp

def _sign_bytes(tx_b64: str, wallet: Keypair) -> bytes:
    raw = base64.b64decode(tx_b64)
    vtx = VersionedTransaction.from_bytes(raw)
    msg = to_bytes_versioned(vtx.message)
    sig = wallet.sign_message(msg)
    pub = wallet.pubkey()
    sigs = list(vtx.signatures)
    idx = next((i for i, k in enumerate(vtx.message.account_keys) if k == pub), 0)
    sigs[idx] = sig
    vtx.signatures = sigs
    return bytes(vtx)

def _fetch_prices_usdc(ids: List[str]) -> Dict[str, float]:
    # Prefer price.jup.ag first
    prices: Dict[str, float] = {}
    try:
        if ids:
            r = requests.get("https://price.jup.ag/v6/price",
                             params={"ids": ",".join(ids), "vsToken": "USDC"},
                             timeout=8)
            r.raise_for_status()
            data = r.json().get("data", {})
            for k, v in data.items():
                try:
                    prices[k] = float(v.get("price"))
                except Exception:
                    pass
            # all good?
            if all(k in prices for k in ids):
                return prices
    except Exception:
        pass
    # Fallback: micro-quote 1 token -> USDC
    for mint in ids:
        try:
            dec = 9
            for t in TOKENS.values():
                if t["mint"] == mint:
                    dec = int(t["decimals"]); break
            amount_atoms = 10 ** dec
            params = {"inputMint": mint, "outputMint": TOKENS["USDC"]["mint"],
                      "amount": str(amount_atoms), "swapMode": "ExactIn",
                      "slippageBps": "0", "restrictIntermediateTokens": "true"}
            _, q = _try_get(_QUOTE_PATHS, params)
            out_atoms = float(q.get("outAmount", "0"))
            price = out_atoms / (10 ** TOKENS["USDC"]["decimals"])
            if price > 0:
                prices[mint] = price
        except Exception:
            continue
    return prices

def _sum_token_amount_for_owner(cl: SolClient, owner: Pubkey, mint: Pubkey) -> Tuple[int, int]:
    resp = cl.get_token_accounts_by_owner(owner, TokenAccountOpts(mint=mint))
    accounts = []
    try:
        accounts = [acc.pubkey for acc in resp.value]
    except Exception:
        accounts = [a["pubkey"] for a in resp["result"]["value"]]
    total_raw = 0
    decimals = None
    for pk in accounts:
        pk_obj = pk if isinstance(pk, Pubkey) else Pubkey.from_string(pk)
        bal = cl.get_token_account_balance(pk_obj)
        try:
            val = bal.value
            amt_raw = int(val.amount); dec = int(val.decimals)
        except Exception:
            val = bal["result"]["value"]
            amt_raw = int(val["amount"]); dec = int(val["decimals"])
        total_raw += amt_raw; decimals = dec
    if decimals is None:
        decimals = 9
    return total_raw, decimals

def _parse_actual_b_received_atoms(cl: SolClient, sig: str, owner: Pubkey, out_mint: str) -> Optional[int]:
    """Try to infer B received by summing owner's token balances for B mint pre vs post."""
    try:
        r = cl.get_transaction(sig, commitment="confirmed", max_supported_transaction_version=0)
        meta = r.value.transaction.meta if hasattr(r.value, "transaction") else r["result"]["transaction"]["meta"]
    except Exception:
        try:
            r = cl.get_transaction(sig, commitment="finalized")
            meta = r["result"]["transaction"]["meta"]
        except Exception:
            return None

    try:
        pre = meta["preTokenBalances"]; post = meta["postTokenBalances"]
    except Exception:
        try:
            pre = meta.pre_token_balances; post = meta.post_token_balances  # type: ignore
        except Exception:
            return None

    def _sum(listing):
        total = 0
        for e in listing:
            try:
                if e.get("mint") == out_mint and e.get("owner") == str(owner):
                    total += int(e["uiTokenAmount"]["amount"])
            except Exception:
                try:
                    if e.mint == Pubkey.from_string(out_mint) and e.owner == owner:
                        total += int(e.ui_token_amount.amount)  # type: ignore
                except Exception:
                    continue
        return total

    try:
        pre_sum = _sum(pre); post_sum = _sum(post)
        delta = post_sum - pre_sum
        return delta if delta >= 0 else None
    except Exception:
        return None

def sign_and_send(tx_b64: str, wallet: Keypair) -> Dict[str, Any]:
    signed = _sign_bytes(tx_b64, wallet)
    cl = SolClient(RPC_URL)
    resp = cl.send_raw_transaction(signed, opts=TxOpts(skip_preflight=False, max_retries=2))

    sig_obj: Optional[Sig] = None
    sig_str: Optional[str] = None
    try:
        val = getattr(resp, "value", None)
        if isinstance(val, Sig):
            sig_obj = val; sig_str = str(val)
    except Exception:
        pass
    if sig_obj is None:
        maybe = getattr(resp, "result", None) or getattr(resp, "value", None) or resp
        sig_str = str(maybe); sig_obj = Sig.from_string(sig_str)

    # best-effort confirm
    try:
        for _ in range(20):
            st = cl.get_signature_statuses([sig_obj])
            try:
                if st.value[0]:
                    break
            except Exception:
                if st["result"]["value"][0]:
                    break
            sleep(0.35)
    except Exception:
        pass

    return {"signature": sig_str}

# ---------- portfolio / prices / safe-max (reused by routes) ----------
def get_wallet_balance_lamports(pubkey: str) -> int:
    cl = SolClient(RPC_URL)
    return int(cl.get_balance(Pubkey.from_string(pubkey)).value)

def estimate_sol_spend_lamports(owner_pubkey: str, out_mint: str) -> Dict[str, Any]:
    cl = SolClient(RPC_URL)
    owner = Pubkey.from_string(owner_pubkey)
    balance = int(cl.get_balance(owner).value)

    # token-account rent
    def _rent(size=165):
        resp = cl.get_minimum_balance_for_rent_exemption(size)
        if isinstance(resp, int): return int(resp)
        try: return int(getattr(resp, "value", None) or resp["result"])
        except Exception: return 2039280

    rent_token = _rent()
    rent_wsol = rent_token

    # OUT ATA existence
    need_out_ata = True
    try:
        mint = Pubkey.from_string(out_mint)
        resp = cl.get_token_accounts_by_owner(owner, TokenAccountOpts(mint=mint))
        try: need_out_ata = len(resp.value) == 0
        except Exception: need_out_ata = len(resp["result"]["value"]) == 0
    except Exception:
        need_out_ata = True

    rent_out = rent_token if need_out_ata else 0
    buffer_lamports = 2_000_000

    safe = balance - (rent_wsol + rent_out + buffer_lamports)
    if safe < 0: safe = 0

    return {
        "owner": owner_pubkey, "balanceLamports": balance,
        "rentTokenLamports": rent_token, "needOutAta": need_out_ata,
        "rentWsolLamports": rent_wsol, "rentOutAtaLamports": rent_out,
        "bufferLamports": buffer_lamports, "safeMaxLamports": safe, "safeMaxSol": safe / 1e9
    }

def get_portfolio(owner_pubkey: str, mints: Optional[List[str]] = None) -> Dict[str, Any]:
    cl = SolClient(RPC_URL)
    owner = Pubkey.from_string(owner_pubkey)
    if not mints:
        mints = [TOKENS[k]["mint"] for k in ("SOL", "USDC", "mSOL", "JitoSOL")]

    prices = _fetch_prices_usdc(mints)

    items: List[Dict[str, Any]] = []
    for mint in mints:
        if mint == TOKENS["SOL"]["mint"]:
            lamports = int(cl.get_balance(owner).value)
            amt = lamports / 1e9
            usd = (amt * float(prices.get(mint, 0.0))) if mint in prices else None
            items.append({"sym": "SOL", "mint": mint, "decimals": 9, "amount": amt, "usd": usd})
        else:
            raw, dec = _sum_token_amount_for_owner(cl, owner, Pubkey.from_string(mint))
            amt = raw / (10 ** dec)
            usd = (amt * float(prices.get(mint, 0.0))) if mint in prices else None
            items.append({"sym": MINT_TO_SYM.get(mint, mint[:4]+"…"), "mint": mint, "decimals": dec, "amount": amt, "usd": usd})
    return {"owner": owner_pubkey, "items": items, "prices": prices}

# ---------- projection + execution logging ----------
def project_round_trip(owner_pubkey: str, in_mint: str, out_mint: str,
                       amount_atoms: int, slippage_bps: int, restrict: bool) -> Dict[str, Any]:
    # A->B
    q1 = get_quote(input_mint=in_mint, output_mint=out_mint, amount=amount_atoms,
                   swap_mode="ExactIn", slippage_bps=slippage_bps, restrict_intermediates=restrict)
    b_min_out = int(q1.get("otherAmountThreshold", 0))
    # B->A with b_min_out
    q2 = get_quote(input_mint=out_mint, output_mint=in_mint, amount=b_min_out,
                   swap_mode="ExactIn", slippage_bps=slippage_bps, restrict_intermediates=restrict)
    a_back_min_out = int(q2.get("otherAmountThreshold", 0))
    edge_atoms = a_back_min_out - int(amount_atoms)
    edge_bps = (edge_atoms / float(amount_atoms)) * 10_000 if amount_atoms else 0.0
    # price snapshot
    prices = _fetch_prices_usdc([in_mint, out_mint])
    in_dec = next((v["decimals"] for v in TOKENS.values() if v["mint"] == in_mint), 9)
    edge_usd = (edge_atoms / (10 ** in_dec)) * float(prices.get(in_mint, 0.0)) if amount_atoms else 0.0
    return {
        "a2b": {
            "outAmount": int(q1.get("outAmount", 0)),
            "minOut": b_min_out,
            "priceImpactPct": float(q1.get("priceImpactPct", 0.0))
        },
        "b2a": {
            "minOutA": a_back_min_out
        },
        "edge": {"atoms": int(edge_atoms), "bps": float(edge_bps), "usd": float(edge_usd)},
        "prices": prices
    }

def log_swap(owner_pubkey: str, sig: str, in_mint: str, out_mint: str,
             amount_atoms: int, projection: Dict[str, Any]) -> Dict[str, Any]:
    cl = SolClient(RPC_URL)
    in_dec = next((v["decimals"] for v in TOKENS.values() if v["mint"] == in_mint), 9)
    out_dec = next((v["decimals"] for v in TOKENS.values() if v["mint"] == out_mint), 6)

    # fetch meta + actual received (best effort)
    fee_lamports = None
    b_recv_atoms = _parse_actual_b_received_atoms(cl, sig, Pubkey.from_string(owner_pubkey), out_mint)
    try:
        r = cl.get_transaction(sig, commitment="confirmed")
        meta = r["result"]["transaction"]["meta"]
        fee_lamports = int(meta.get("fee", 0))
    except Exception:
        pass

    # prices at execution time (fallback safe)
    prices = _fetch_prices_usdc([in_mint, out_mint, TOKENS["SOL"]["mint"]])
    price_in = float(prices.get(in_mint, 0.0))
    price_out = float(prices.get(out_mint, 0.0))
    price_sol = float(prices.get(TOKENS["SOL"]["mint"], 0.0))

    value_in_usd = (amount_atoms / (10 ** in_dec)) * price_in if price_in else None
    value_out_usd = (b_recv_atoms / (10 ** out_dec)) * price_out if (price_out and b_recv_atoms is not None) else None
    fees_usd = (fee_lamports / 1e9) * price_sol if (fee_lamports is not None and price_sol) else None

    pnl_usd = None
    if value_in_usd is not None and value_out_usd is not None and fees_usd is not None:
        pnl_usd = value_out_usd - value_in_usd - fees_usd

    # attempt actual edge in A (if reverse was executed we could compute exactly; here it's single-leg)
    actual_edge = None
    if b_recv_atoms is not None:
        # simulate reverse minOut with new quote to estimate actual edge in A terms (approx)
        try:
            back_now = get_quote(input_mint=out_mint, output_mint=in_mint, amount=int(b_recv_atoms),
                                 swap_mode="ExactIn", slippage_bps=0, restrict_intermediates=True)
            a_back_now = int(back_now.get("otherAmountThreshold", 0))
            edge_atoms = a_back_now - int(amount_atoms)
            edge_bps = (edge_atoms / float(amount_atoms)) * 10_000 if amount_atoms else 0.0
            actual_edge = {"atoms": int(edge_atoms), "bps": float(edge_bps),
                           "usd": (edge_atoms / (10 ** in_dec)) * price_in if price_in else None}
        except Exception:
            actual_edge = None

    entry = {
        "pair": {"in": MINT_TO_SYM.get(in_mint, in_mint[:4]+"…"),
                 "out": MINT_TO_SYM.get(out_mint, out_mint[:4]+"…")},
        "mode": "ExactIn",
        "rpc": RPC_URL,
        "amountInAtoms": int(amount_atoms),
        "decIn": in_dec,
        "projection": projection,
        "execution": {"sig": sig, "feeLamports": fee_lamports, "bReceivedAtoms": b_recv_atoms},
        "actual": {"pnlUsd": pnl_usd, "valueInUsd": value_in_usd, "valueOutUsd": value_out_usd,
                   "feesUsd": fees_usd, "edge": actual_edge, "prices": prices},
        "status": "success" if sig else "unknown",
        "notes": "single-leg; round-trip not atomic"
    }
    txlog.append(entry)
    return entry
