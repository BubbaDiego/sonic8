
from typing import List
from solders.pubkey import Pubkey
from .constants import PERPS_PROGRAM_ID, TOKEN_PROGRAM, ASSOCIATED_TOKEN_PROGRAM

def find_program_address(seeds: List[bytes], program_id: Pubkey) -> Pubkey:
    pda, _ = Pubkey.find_program_address(seeds, program_id)
    return pda

def derive_position_request_pda(position: Pubkey, counter_u64: int) -> Pubkey:
    return find_program_address([b"position_request", bytes(position), counter_u64.to_bytes(8,"little")], PERPS_PROGRAM_ID)

def derive_event_authority() -> Pubkey:
    return find_program_address([b"__event_authority"], PERPS_PROGRAM_ID)

def derive_perpetuals_pda() -> Pubkey:
    return find_program_address([b"perpetuals"], PERPS_PROGRAM_ID)

def derive_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return find_program_address([bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)], ASSOCIATED_TOKEN_PROGRAM)

def derive_position_pda_v1(owner: Pubkey, custody: Pubkey, collateral: Pubkey) -> Pubkey:
    return find_program_address([b"position", bytes(owner), bytes(custody), bytes(collateral)], PERPS_PROGRAM_ID)

def derive_position_pda_v2(owner: Pubkey, pool: Pubkey, custody: Pubkey, collateral: Pubkey) -> Pubkey:
    return find_program_address([b"position", bytes(owner), bytes(pool), bytes(custody), bytes(collateral)], PERPS_PROGRAM_ID)

def derive_position_pda_v3(owner: Pubkey, pool: Pubkey, custody: Pubkey, collateral: Pubkey) -> Pubkey:
    return find_program_address([b"position", bytes(pool), bytes(owner), bytes(custody), bytes(collateral)], PERPS_PROGRAM_ID)


# --- APPEND: canonical position PDA wrapper ---------------------------------
def position_pda(
    owner: Pubkey,
    market: str,
    program_id: Pubkey,
    market_mint: str | None = None,
) -> Pubkey:
    """
    Canonical resolver:
      1) honour repo-specific helpers if present
      2) attempt known v3/v2/v1 derivations using market metadata
      3) fallback to [b"position", owner, market_mint or market]
    """
    try:
        from backend.perps.pdas import derive_position_pda_from_idl  # type: ignore

        return derive_position_pda_from_idl(owner, market, program_id)
    except Exception:
        pass

    pool = custody_base = collateral = None
    market_mint_value: str | None = market_mint

    try:
        from backend.services.perps.markets import resolve_market

        market_info = resolve_market(market)
        pool = Pubkey.from_string(market_info["pool"])
        custody_base = Pubkey.from_string(market_info["custody_base"])
        collateral = Pubkey.from_string(market_info["custody_quote"])
        market_mint_value = market_info.get("base_mint") or market_mint_value
    except Exception:
        # metadata lookup best-effort; continue to other fallbacks
        pass

    try:
        if pool and custody_base and collateral:
            return derive_position_pda_v3(owner, pool, custody_base, collateral)
    except Exception:
        pass
    try:
        if pool and custody_base and collateral:
            return derive_position_pda_v2(owner, pool, custody_base, collateral)
    except Exception:
        pass
    try:
        if custody_base and collateral:
            return derive_position_pda_v1(owner, custody_base, collateral)
    except Exception:
        pass

    seed_market = market_mint_value or market
    if isinstance(seed_market, Pubkey):
        seed_bytes = bytes(seed_market)
    elif isinstance(seed_market, bytes):
        seed_bytes = seed_market
    else:
        seed_bytes = str(seed_market).encode("utf-8")
    return Pubkey.find_program_address([b"position", bytes(owner), seed_bytes], program_id)[0]


def position_request_pda(
    owner: Pubkey,
    market: str,
    program_id: Pubkey,
    market_mint: str | None = None,
) -> Pubkey:
    seed_market = market_mint or market
    if isinstance(seed_market, Pubkey):
        seed_bytes = bytes(seed_market)
    elif isinstance(seed_market, bytes):
        seed_bytes = seed_market
    else:
        seed_bytes = str(seed_market).encode("utf-8")
    return Pubkey.find_program_address([b"position-request", bytes(owner), seed_bytes], program_id)[0]
