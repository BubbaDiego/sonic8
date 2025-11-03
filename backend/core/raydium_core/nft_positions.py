"""
Find & decode Raydium CLMM position NFTs held by a wallet.

Approach:
1) getParsedTokenAccountsByOwner(owner, TOKEN) and again for TOKEN_2022
   → filter NFTs (decimals==0 and amount=="1")
2) For each candidate mint, query CLMM program accounts with memcmp on nft_mint
   Layout (Anchor account):
     [0..7]   anchor discriminator (8 bytes)
     [8]      bump: u8
     [9..40]  nft_mint: Pubkey (32)
     [41..72] pool_id: Pubkey (32)
     [73..76] tick_lower_index: i32 (4)
     [77..80] tick_upper_index: i32 (4)
     [81..96] liquidity: u128 (16)
     [..]     (skip fee/reward internals for MVP)
     [..]     tokens_owed_0: u64
     [..]     tokens_owed_1: u64
3) Return parsed positions (without valuation).
"""

from __future__ import annotations

import struct
from base64 import b64decode
from typing import Dict, Iterable, List, Tuple

from .constants import (
    CLMM_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
)
from .rpc import SolanaRPC
from .raydium_schema import RaydiumPosition


def _collect_position_mints(rpc: SolanaRPC, owner: str) -> List[str]:
    mints: List[str] = []

    def scan(program_id: str):
        value = rpc.get_parsed_token_accounts_by_owner(owner, program_id)
        for it in value:
            try:
                info = it["account"]["data"]["parsed"]["info"]
                amount_info = info["tokenAmount"]
                if int(amount_info["amount"]) != 1:
                    continue
                if int(amount_info["decimals"]) != 0:
                    continue  # NFTs only
                mints.append(info["mint"])
            except Exception:
                continue

    scan(TOKEN_PROGRAM_ID)
    scan(TOKEN_2022_PROGRAM_ID)
    # de-dupe preserve order
    seen = set()
    uniq = []
    for m in mints:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def _find_personal_position_accounts(rpc: SolanaRPC, nft_mint: str) -> List[Dict]:
    """
    Query CLMM program for PersonalPositionState by matching nft_mint at offset 9 (after 8-byte Anchor discriminator + 1 byte bump).
    """
    filters = [
        {"memcmp": {"offset": 9, "bytes": nft_mint}},
        # Optional: dataSize filter exists, but not necessary for discovery
    ]
    res = rpc.get_program_accounts(CLMM_PROGRAM_ID, filters=filters, encoding="base64")
    return res or []


def _decode_personal_position(owner: str, nft_mint: str, acct: Dict) -> RaydiumPosition:
    b64, _enc = acct["account"]["data"]
    raw = b64decode(b64)

    # Skip anchor discriminator (8)
    off = 8
    bump = raw[off]
    off += 1

    nft_mint_bytes = raw[off : off + 32]
    off += 32
    pool_id_bytes = raw[off : off + 32]
    off += 32

    tick_lower = struct.unpack_from("<i", raw, off)[0]
    off += 4
    tick_upper = struct.unpack_from("<i", raw, off)[0]
    off += 4

    # u128 little-endian
    liquidity = int.from_bytes(raw[off : off + 16], "little")
    off += 16

    # Skip two u128 fee growth fields (2 * 16)
    off += 32

    # tokens_owed_0: u64
    tokens_owed0 = int.from_bytes(raw[off : off + 8], "little")
    off += 8
    # tokens_owed_1: u64
    tokens_owed1 = int.from_bytes(raw[off : off + 8], "little")
    off += 8

    def _to_pubkey(b: bytes) -> str:
        # We intentionally return base58 via their RPC layering when needed.
        # Here we leave bytes and let the API enrichment resolve pool mapping.
        import base58  # lightweight dep; if not installed user can add to requirements.
        return base58.b58encode(b).decode("utf-8")

    pool_id_b58 = _to_pubkey(pool_id_bytes)

    return RaydiumPosition(
        owner=owner,
        nft_mint=nft_mint,
        pool_id=pool_id_b58,
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        liquidity=liquidity,
        tokens_owed0=tokens_owed0,
        tokens_owed1=tokens_owed1,
    )


def discover_positions(rpc: SolanaRPC, owner: str) -> List[RaydiumPosition]:
    positions: List[RaydiumPosition] = []
    for mint in _collect_position_mints(rpc, owner):
        for acct in _find_personal_position_accounts(rpc, mint):
            try:
                pos = _decode_personal_position(owner, mint, acct)
                positions.append(pos)
            except Exception:
                # Non-Ray/other NFTs that accidentally matched, or layout change.
                continue
    return positions
