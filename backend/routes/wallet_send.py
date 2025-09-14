# backend/routes/wallet_send.py
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

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

# ------------------------------ ENV / CONFIG ------------------------------

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
RPC_URL        = os.getenv("RPC_URL", f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}")

# Signer: Solana CLI id.json by default; you can also set SIGNER_BASE58
SIGNER_PATH    = os.getenv("SIGNER_PATH", os.path.join(os.path.dirname(__file__), "..", "signer_id.json"))
SIGNER_BASE58  = os.getenv("SIGNER_BASE58", "").strip()

# Programs
SYSTEM_PROGRAM        = Pubkey.from_string("11111111111111111111111111111111")
SPL_TOKEN_PROGRAM     = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT_SYSVAR           = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

# Magic “mints”
SOL_MINT  = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Compute/priority (microlamports per CU); tweak if needed
CU_LIMIT  = int(os.getenv("SEND_CU_LIMIT",  "800000"))
CU_PRICE  = int(os.getenv("SEND_CU_PRICE",  "100000"))

# ------------------------------ Base58 helpers -----------------------------

BASE58_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_SET  = set(BASE58_ALPH)
BASE58_RE   = re.compile(r"^[1-9A-HJ-NP-Za-km-z]+$")
BASE58_FIND = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,}")

def extract_pubkey(s: str) -> str:
    """
    Normalize any recipient/mint string:
      - supports solana:<pk>?...
      - supports explorer URLs .../address/<pk>
      - otherwise: strip trailing ?/#/spaces, or pick the longest base58 token
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
        hits.sort(key=len, reverse=True)  # prefer the longest candidate
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
    r = requests.post(RPC_URL, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=25)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise HTTPException(400, str(data["error"]))
    return data["result"]

def recent_blockhash() -> Hash:
    res = rpc("getLatestBlockhash", [{"commitment":"finalized"}])
    return Hash.from_string(res["value"]["blockhash"])

# ------------------------------ Signer loading -----------------------------

def _b58decode(s: str) -> bytes:
    idx = {ch:i for i,ch in enumerate(BASE58_ALPH)}
    n = 0
    for ch in s.strip():
        if ch not in idx:
            raise ValueError(f"invalid base58 char: {ch}")
        n = n * 58 + idx[ch]
    full = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b"\x00"
    lead = sum(1 for ch in s if ch == "1")
    return b"\x00" * lead + full.lstrip(b"\x00")

def load_signer() -> Keypair:
    # Priority: SIGNER_BASE58 (env), then SIGNER_PATH (id.json)
    if SIGNER_BASE58:
        raw = _b58decode(SIGNER_BASE58)
        if len(raw) == 64:
            return Keypair.from_bytes(raw)
        if len(raw) == 32:
            try:
                return Keypair.from_seed(raw)
            except Exception:
                import nacl.signing as ns
                sk = ns.SigningKey(raw)
                sec64 = sk.encode() + sk.verify_key.encode()
                return Keypair.from_bytes(sec64)
        raise HTTPException(500, f"SIGNER_BASE58 decoded length {len(raw)} not 32/64")
    if not os.path.exists(SIGNER_PATH):
        raise HTTPException(500, f"Signer file not found: {SIGNER_PATH}")
    try:
        obj = json.load(open(SIGNER_PATH, "r", encoding="utf-8"))
        if isinstance(obj, list):  # Solana CLI id.json
            return Keypair.from_bytes(bytes(obj))
        if isinstance(obj, dict) and "secretKey" in obj:
            return Keypair.from_bytes(bytes(obj["secretKey"]))
    except Exception as e:
        raise HTTPException(500, f"Failed to parse signer: {e}")
    raise HTTPException(500, "Unsupported signer format: expected Solana CLI id.json or SIGNER_BASE58")

# ------------------------------ ATA helpers --------------------------------

def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    # SPL Associated Token Account PDA
    seeds = [bytes(owner), bytes(SPL_TOKEN_PROGRAM), bytes(mint)]
    return Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROG)[0]

def account_exists(pub: Pubkey) -> bool:
    try:
        res = rpc("getAccountInfo", [str(pub), {"encoding":"base64","commitment":"confirmed"}])
        return bool(res.get("value"))
    except Exception:
        return False

def create_ata_ix(payer: Pubkey, owner: Pubkey, mint: Pubkey, ata_addr: Pubkey) -> Instruction:
    # Associated Token Program: CreateAssociatedTokenAccount
    metas = [
        AccountMeta(payer, True,  True),    # payer (signer, writable)
        AccountMeta(ata_addr, False, True), # ATA (writable)
        AccountMeta(owner,   False, False), # token owner
        AccountMeta(mint,    False, False), # mint
        AccountMeta(SYSTEM_PROGRAM, False, False),
        AccountMeta(SPL_TOKEN_PROGRAM, False, False),
        AccountMeta(RENT_SYSVAR, False, False),  # ignored by new program but harmless
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
    mint: str = Field(..., description="Mint address or 'SOL'")
    to:   str = Field(..., description="Recipient owner (base58)")
    amountAtoms: int = Field(..., gt=0, description="Amount in atoms (lamports for SOL; decimals-based for SPL)")

    @field_validator("mint")
    @classmethod
    def _norm_mint(cls, v: str) -> str:
        v = extract_pubkey(v)
        return SOL_MINT if (v or "").upper() == "SOL" else v

    @field_validator("to")
    @classmethod
    def _norm_to(cls, v: str) -> str:
        return extract_pubkey(v)

# ------------------------------ Route --------------------------------------

@router.post("/send")
def send_token_api(req: SendReq):
    try:
        # normalize + validate (return 422 before hitting RPC)
        mint_str = req.mint if req.mint == SOL_MINT else validate_base58_or_422("mint", req.mint)
        to_norm  = validate_base58_or_422("recipient", req.to)

        kp = load_signer()
        payer = kp.pubkey()
        to_owner = Pubkey.from_string(to_norm)

        ixs: list[Instruction] = []
        # small compute/priority bump
        ixs.append(set_compute_unit_limit(CU_LIMIT))
        ixs.append(set_compute_unit_price(CU_PRICE))

        if mint_str == SOL_MINT:
            # SystemProgram::Transfer — tag 2, amount u64 LE
            lamports = int(req.amountAtoms)
            data = b"\x02" + lamports.to_bytes(8, "little")
            ixs.append(
                Instruction(
                    SYSTEM_PROGRAM,
                    data,
                    [AccountMeta(payer, True, True), AccountMeta(to_owner, False, True)],
                )
            )
        else:
            mint = Pubkey.from_string(mint_str)

            # Ensure source ATA exists (rarely missing, but robust)
            src_ata  = ata(payer, mint)
            if not account_exists(src_ata):
                ixs.append(create_ata_ix(payer, payer, mint, src_ata))

            # Ensure destination ATA exists (allow-unfunded-recipient)
            dest_ata = ata(to_owner, mint)
            if not account_exists(dest_ata):
                ixs.append(create_ata_ix(payer, to_owner, mint, dest_ata))

            # SPL Token TransferChecked (tag 12): [amount u64, decimals u8]
            decimals = get_mint_decimals(mint_str)
            amount   = int(req.amountAtoms)
            data = bytes([12]) + amount.to_bytes(8, "little") + bytes([decimals])
            ixs.append(
                Instruction(
                    SPL_TOKEN_PROGRAM,
                    data,
                    [
                        AccountMeta(src_ata,  False, True),   # source
                        AccountMeta(mint,     False, False),  # mint
                        AccountMeta(dest_ata, False, True),   # destination
                        AccountMeta(payer,    True,  False),  # authority
                    ],
                )
            )

        bh  = recent_blockhash()
        # NOTE: your solders version expects 'address_lookup_table_accounts'
        msg = MessageV0.try_compile(
            payer=payer,
            instructions=ixs,
            address_lookup_table_accounts=[],   # not 'address_lookup_tables'
            recent_blockhash=bh,
        )
        tx  = VersionedTransaction(msg, [kp])
        raw = base64.b64encode(bytes(tx)).decode()
        sig = rpc("sendTransaction", [raw, {"skipPreflight": False, "maxRetries": 3}])
        return {"signature": sig}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"send failed: {e}")
