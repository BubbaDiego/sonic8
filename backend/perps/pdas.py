from __future__ import annotations
from typing import List, Optional, Union
import hashlib

from solders.pubkey import Pubkey
# Use absolute imports to avoid Windows/packaging edge cases
from backend.perps.constants import PERPS_PROGRAM_ID, TOKEN_PROGRAM, ASSOCIATED_TOKEN_PROGRAM

__all__ = [
    "find_program_address",
    "derive_position_request_pda",
    "derive_event_authority",
    "derive_perpetuals_pda",
    "derive_ata",
    "derive_position_pda_v1",
    "derive_position_pda_v2",
    "derive_position_pda_v3",
    "position_pda",
    "position_request_pda",
]

# ---------------------------------------------------------------------------
# Core helper
# ---------------------------------------------------------------------------

def find_program_address(seeds: List[bytes], program_id: Pubkey) -> Pubkey:
    pda, _ = Pubkey.find_program_address(seeds, program_id)
    return pda

# ---------------------------------------------------------------------------
# Legacy / existing helpers (kept intact)
# ---------------------------------------------------------------------------

def derive_position_request_pda(position: Pubkey, counter_u64: int) -> Pubkey:
    """
    Legacy scheme: PDA(["position_request", position, counter_u64])
    Kept for compatibility with any older code paths still importing this.
    """
    return find_program_address(
        [b"position_request", bytes(position), counter_u64.to_bytes(8, "little")],
        PERPS_PROGRAM_ID,
    )

def derive_event_authority() -> Pubkey:
    return find_program_address([b"__event_authority"], PERPS_PROGRAM_ID)

def derive_perpetuals_pda() -> Pubkey:
    return find_program_address([b"perpetuals"], PERPS_PROGRAM_ID)

def derive_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        ASSOCIATED_TOKEN_PROGRAM,
    )

def derive_position_pda_v1(owner: Pubkey, custody: Pubkey, collateral: Pubkey) -> Pubkey:
    return find_program_address(
        [b"position", bytes(owner), bytes(custody), bytes(collateral)],
        PERPS_PROGRAM_ID,
    )

def derive_position_pda_v2(owner: Pubkey, pool: Pubkey, custody: Pubkey, collateral: Pubkey) -> Pubkey:
    return find_program_address(
        [b"position", bytes(owner), bytes(pool), bytes(custody), bytes(collateral)],
        PERPS_PROGRAM_ID,
    )

def derive_position_pda_v3(owner: Pubkey, pool: Pubkey, custody: Pubkey, collateral: Pubkey) -> Pubkey:
    return find_program_address(
        [b"position", bytes(pool), bytes(owner), bytes(custody), bytes(collateral)],
        PERPS_PROGRAM_ID,
    )

# ---------------------------------------------------------------------------
# New robust seeds (never exceed 32B; safe with mint strings or market names)
# ---------------------------------------------------------------------------

Seedish = Union[str, bytes, bytearray, Pubkey]

def _seed32(x: Seedish) -> bytes:
    """
    Return a <=32B seed. Pubkeys -> 32B. If given a non-pubkey string (e.g., 'SOL-PERP'),
    use sha256(name)[:32] so PDA derivation will never panic.
    """
    if isinstance(x, Pubkey):
        return bytes(x)
    if isinstance(x, (bytes, bytearray)):
        if len(x) > 32:
            raise ValueError(f"seed too long ({len(x)}B > 32B)")
        return bytes(x)
    if isinstance(x, str):
        # try base58 pubkey first
        try:
            return bytes(Pubkey.from_string(x))
        except Exception:
            # not a pubkey: hash & trim
            return hashlib.sha256(x.encode("utf-8")).digest()[:32]
    raise TypeError(f"unsupported seed type: {type(x)}")

def position_pda(
    owner: Pubkey,
    market: str,
    program_id: Pubkey,
    market_mint: Optional[Seedish] = None,
) -> Pubkey:
    """
    Canonical resolver:
      1) honour repo-specific helpers if present
      2) attempt known v3/v2/v1 derivations using market metadata
      3) fallback PDA = find_program_address(["position", owner, seed32(market_mint or market)])
    """
    # Prefer any project-specific implementation if present
    for name in ("derive_position_pda_from_idl", "derive_position_pda_v3", "derive_position_pda_v2", "derive_position_pda_v1"):
        try:
            fn = getattr(__import__("backend.perps.pdas", fromlist=[name]), name)  # self import; safe if function exists
            if name == "derive_position_pda_from_idl":
                return fn(owner, market, program_id)  # type: ignore[misc]
            # for v3/v2/v1 we need metadata; best-effort via markets resolver
            try:
                from backend.services.perps.markets import resolve_market  # local import prevents circulars
                info = resolve_market(market)
                pool = Pubkey.from_string(info["pool"])
                base = Pubkey.from_string(info["custody_base"])
                quot = Pubkey.from_string(info["custody_quote"])
                if name == "derive_position_pda_v3":
                    return derive_position_pda_v3(owner, pool, base, quot)
                if name == "derive_position_pda_v2":
                    return derive_position_pda_v2(owner, pool, base, quot)
                if name == "derive_position_pda_v1":
                    return derive_position_pda_v1(owner, base, quot)
            except Exception:
                # if metadata unavailable, skip to fallback
                pass
        except Exception:
            continue

    seed_market = _seed32(market_mint if market_mint is not None else market)
    return Pubkey.find_program_address([b"position", bytes(owner), seed_market], program_id)[0]

def position_request_pda(
    owner: Pubkey,
    market: str,
    program_id: Pubkey,
    market_mint: Optional[Seedish] = None,
) -> Pubkey:
    """
    Robust position-request derivation:
      PDA(["position-request", owner, seed32(market_mint or market)])
    """
    seed_market = _seed32(market_mint if market_mint is not None else market)
    return Pubkey.find_program_address([b"position-request", bytes(owner), seed_market], program_id)[0]
