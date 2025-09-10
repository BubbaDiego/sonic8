
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
