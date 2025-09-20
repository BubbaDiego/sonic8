# backend/routes/wallet_send.py
"""Wallet send routes."""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.hash import Hash
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price

# Use the centralized signer loader used elsewhere (Jupiter routes, etc.)
from backend.config.rpc import helius_url
from backend.services.signer_loader import load_signer  # <<< unify signer

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

# ------------------------------ ENV / CONFIG ------------------------------

def _rpc_url() -> str:
    override = os.getenv("RPC_URL")
    if override:
        return override
    return helius_url()


RPC_URL = _rpc_url()

# Programs
SYSTEM_PROGRAM        = Pubkey.from_string("11111111111111111111111111111111")
SPL_TOKEN_PROGRAM     = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT_SYSVAR           = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

# “Well-known mints”
SOL_MINT  = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


# After  (safe defaults)
CU_LIMIT  = int(os.getenv("SEND_CU_LIMIT",  "400000"))  # or 800_000; either is fine
CU_PRICE  = int(os.getenv("SEND_CU_PRICE",  "1"))       # 1–5 microLamports/CU is typical


# ------------------------------ Base58 helpers -----------------------------

BASE58_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_SET  = set(BASE58_ALPH)
BASE58_RE   = re.compile(r"^[1-9A-HJ-NP-Za-km-z]+$")
BASE58_FIND = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,}")

def extract_pubkey(s: str) -> str:
    """
    Normalize a value to a candidate pubkey:
      - solana:<pk>?...
      - explorer URLs .../address/<pk>
      - raw text → longest base58 token
    """
    if not s:
        return ""
    s = str(s).strip()

    low = s.lower()
    if low.startswith("solana:"):
        s = s.split(":", 1)[1]
        s = s.split("?", 1)[0]
        return s

    m = re.search(r"address/([1-9A-HJ-NP-Za-km-z]+)", s)
    if m:
        return m.group(1)

    s0 = re.split(r"[?#\s]", s)[0]
    if BASE58_RE.fullmatch(s0 or ""):
        return s0

    hits = BASE58_FIND.findall(s)
    if hits:
        hits.sort(key=len, reverse=True)
        return hits[0]

    return s0

def validate_base58_or_422(label: str, pk: str) -> str:
    """Return pk if valid; otherwise raise 422 with the exact bad char/index."""
    if not pk:
        raise HTTPException(422, f"Missing {label}")
    for i, ch in enumerate(pk):
        if ch not in BASE58_SET:
            raise HTTPException(422, f"Invalid {label}: invalid base58 char '{ch}' at index {i} in '{pk}'")
    return pk

# ------------------------------ RPC helpers --------------------------------

def rpc(method: str, params: Any) -> Any:
    try:
        r = requests.post(RPC_URL, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=25)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(500, f"RPC transport error calling {method}: {e}")

    if data.get("error"):
        # make it obvious which call exploded and with what params
        raise HTTPException(400, f"RPC error in {method}: {data['error']}")
    return data["result"]

def recent_blockhash() -> Hash:
    res = rpc("getLatestBlockhash", [{"commitment":"finalized"}])
    return Hash.from_string(res["value"]["blockhash"])

# ------------------------------ Signer loading -----------------------------

# ------------------------------ ATA helpers --------------------------------

def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    seeds = [bytes(owner), bytes(SPL_TOKEN_PROGRAM), bytes(mint)]
    return Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROG)[0]

def account_exists(pub: Pubkey) -> bool:
    try:
        res = rpc("getAccountInfo", [str(pub), {"encoding":"base64","commitment":"confirmed"}])
        return bool(res.get("value"))
    except Exception:
        return False

def create_ata_ix(payer: Pubkey, owner: Pubkey, mint: Pubkey, ata_addr: Pubkey) -> Instruction:
    metas = [
        AccountMeta(payer, True,  True),
        AccountMeta(ata_addr, False, True),
        AccountMeta(owner,   False, False),
        AccountMeta(mint,    False, False),
        AccountMeta(SYSTEM_PROGRAM, False, False),
        AccountMeta(SPL_TOKEN_PROGRAM, False, False),
        AccountMeta(RENT_SYSVAR, False, False),
    ]
    return Instruction(ASSOCIATED_TOKEN_PROG, b"", metas)

def get_mint_decimals(mint_str: str) -> int:
    if mint_str == USDC_MINT:
        return 6
    try:
        res = rpc("getAccountInfo", [mint_str, {"encoding":"jsonParsed","commitment":"confirmed"}])
        v = res.get("value") or {}
        parsed = (v.get("data") or {}).get("parsed") or {}
        info = parsed.get("info") or {}
        d = info.get("decimals")
        return int(d) if d is not None else 9
    except Exception:
        return 9

# ------------------------------ Request model ------------------------------

class SendReq(BaseModel):
    mint: str = Field(..., description="Mint address or 'SOL'/'USDC'")
    to:   str = Field(..., description="Recipient owner (base58)")
    amountAtoms: int = Field(..., gt=0, description="Amount in atoms")

    @field_validator("mint")
    @classmethod
    def _norm_mint(cls, v: str) -> str:
        v = extract_pubkey(v)
        u = (v or "").upper()
        if u == "SOL":  return SOL_MINT
        if u == "USDC": return USDC_MINT
        return v

    @field_validator("to")
    @classmethod
    def _norm_to(cls, v: str) -> str:
        return extract_pubkey(v)

# ------------------------------ Route --------------------------------------

@router.post("/send")
def send_token_api(req: SendReq):
    try:
        # Normalize + validate strictly (no RPC if invalid)
        raw_mint = req.mint
        raw_to   = req.to

        mint_str = raw_mint if raw_mint == SOL_MINT else validate_base58_or_422("mint", raw_mint)
        to_norm  = validate_base58_or_422("recipient", raw_to)

        # Debug line so you can see what the server actually received vs normalized
        print(f"[wallet_send] RAW to='{req.to}' RAW mint='{req.mint}' → NORM to='{to_norm}' mint='{mint_str}'")

        kp = load_signer()  # unified signer (same as /api/jupiter/*)
        payer = kp.pubkey()
        print(f"[wallet_send] fee payer: {payer}")  # helps catch signer mismatches
        to_owner = Pubkey.from_string(to_norm)

        # Build ixs
        ixs: list[Instruction] = []
        ixs.append(set_compute_unit_limit(CU_LIMIT))
        ixs.append(set_compute_unit_price(CU_PRICE))

        if mint_str == SOL_MINT:
            # SystemProgram::Transfer uses a 4-byte LE tag (u32=2) + u64 lamports
            lamports = int(req.amountAtoms)
            data = (2).to_bytes(4, "little") + lamports.to_bytes(8, "little")
            ixs.append(Instruction(SYSTEM_PROGRAM, data, [
                AccountMeta(payer, True, True),   # from (signer, writable)
                AccountMeta(to_owner, False, True)  # to (writable)
            ]))
        else:
            mint = Pubkey.from_string(mint_str)
            src_ata  = ata(payer, mint)
            dest_ata = ata(to_owner, mint)

            if not account_exists(src_ata):
                ixs.append(create_ata_ix(payer, payer, mint, src_ata))
            if not account_exists(dest_ata):
                ixs.append(create_ata_ix(payer, to_owner, mint, dest_ata))

            decimals = get_mint_decimals(mint_str)
            # SPL Token TransferChecked (tag 12): [u64 amount LE, u8 decimals]
            data = bytes([12]) + int(req.amountAtoms).to_bytes(8, "little") + bytes([decimals])
            ixs.append(Instruction(SPL_TOKEN_PROGRAM, data, [
                AccountMeta(src_ata,  False, True),
                AccountMeta(mint,     False, False),
                AccountMeta(dest_ata, False, True),
                AccountMeta(payer,    True,  False)
            ]))

        # Compile & send
        bh  = recent_blockhash()
        msg = MessageV0.try_compile(
            payer=payer,
            instructions=ixs,
            address_lookup_table_accounts=[],   # correct kw for many solders versions
            recent_blockhash=bh
        )
        tx  = VersionedTransaction(msg, [kp])
        raw = base64.b64encode(bytes(tx)).decode()

        sig = rpc("sendTransaction", [raw, {"encoding":"base64", "skipPreflight": False, "maxRetries": 3}])
        return {"signature": sig}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"send failed: {e}")


@router.get("/debug")
def wallet_debug():
    try:
        kp = load_signer()
        bal = rpc("getBalance", [str(kp.pubkey())]).get("value", 0)
        return {"rpcUrl": RPC_URL, "pubkey": str(kp.pubkey()), "lamports": bal}
    except Exception as e:
        raise HTTPException(500, f"wallet debug failed: {e}")
