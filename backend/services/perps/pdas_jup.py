"""Canonical Jupiter Perps PDA helpers used across simulations/tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from solders.pubkey import Pubkey

from backend.perps.constants import (
    ASSOCIATED_TOKEN_PROGRAM,
    PERPS_PROGRAM_ID,
    TOKEN_PROGRAM,
    USDC_MINT,
)


@dataclass(frozen=True)
class MarketIds:
    """Convenience structure for grouped Jupiter market identifiers."""

    perpetuals: Pubkey
    pool: Pubkey
    market_mint: Pubkey


def _find(seeds: List[bytes]) -> Pubkey:
    """Return the PDA for ``seeds`` using the Jupiter Perps program id."""

    return Pubkey.find_program_address(seeds, PERPS_PROGRAM_ID)[0]


def position_pda(owner: Pubkey, market_mint: Pubkey) -> Pubkey:
    """Anchor-style position PDA: seeds = ["position", owner, market_mint]."""

    return _find([b"position", bytes(owner), bytes(market_mint)])


def position_request_pda(owner: Pubkey, market_mint: Pubkey, counter: int) -> Pubkey:
    """Position-request PDA: seeds = ["position-request", owner, market_mint, counter]."""

    counter_bytes = int(counter).to_bytes(4, "little", signed=False)
    return _find([b"position-request", bytes(owner), bytes(market_mint), counter_bytes])


def custody_pda(pool: Pubkey, mint: Pubkey) -> Pubkey:
    """Custody PDA: seeds = ["custody", pool, mint]."""

    return _find([b"custody", bytes(pool), bytes(mint)])


def associated_token_address(owner: Pubkey, mint: Pubkey) -> Pubkey:
    """Derive the SPL associated token account owned by ``owner`` for ``mint``."""

    return Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        ASSOCIATED_TOKEN_PROGRAM,
    )[0]
