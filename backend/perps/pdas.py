
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
def position_pda(owner: Pubkey, market: str, program_id: Pubkey) -> Pubkey:
    """
    Canonical 'position' PDA resolver for the current deployment.
    Priority:
      1) If this repo defines an IDL-driven derivation for 'position', prefer it.
      2) Otherwise, attempt v3 -> v2 -> v1 consistently (without probing chain).
    """
    try:
        from backend.perps.pdas import derive_position_pda_from_idl  # optional; ok if missing
        return derive_position_pda_from_idl(owner, market, program_id)
    except Exception:
        pass

    # Fallback sequence; keep deterministic order
    try:
        from backend.perps.pdas import derive_position_pda_v3
    except Exception:
        derive_position_pda_v3 = None  # type: ignore
    try:
        from backend.perps.pdas import derive_position_pda_v2
    except Exception:
        derive_position_pda_v2 = None  # type: ignore
    try:
        from backend.perps.pdas import derive_position_pda_v1
    except Exception:
        derive_position_pda_v1 = None  # type: ignore

    pool = custody_base = collateral = None
    try:
        from backend.services.perps.markets import resolve_market

        market_info = resolve_market(market)
        pool = Pubkey.from_string(market_info["pool"])
        custody_base = Pubkey.from_string(market_info["custody_base"])
        collateral = Pubkey.from_string(market_info["custody_quote"])
    except Exception:
        # leave fallbacks to raise below if derivations fail
        pass

    if derive_position_pda_v3 and pool and custody_base and collateral:
        try:
            return derive_position_pda_v3(owner, pool, custody_base, collateral)
        except Exception:
            pass
    if derive_position_pda_v2 and pool and custody_base and collateral:
        try:
            return derive_position_pda_v2(owner, pool, custody_base, collateral)
        except Exception:
            pass
    if derive_position_pda_v1 and custody_base and collateral:
        try:
            return derive_position_pda_v1(owner, custody_base, collateral)
        except Exception:
            pass

    raise RuntimeError("Unable to derive position PDA; ensure market metadata is configured")
