"""
High-level service that:
- discovers Raydium CLMM positions for an owner
- enriches with pool info (mints, tick current)
- computes token amounts from liquidity & ticks
- values positions in USD via Raydium mint/price API
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, getcontext
from typing import Dict, Iterable, List, Tuple

from .rpc import SolanaRPC
from .raydium_api import RaydiumApi
from .raydium_schema import RaydiumPortfolio, RaydiumPosition
from . import nft_positions


# Use high precision for tick/price math
getcontext().prec = 60


def _tick_to_sqrt_price(tick: int) -> Decimal:
    """
    Convert tick index -> sqrt(price). Raydium CLMM uses Uniswap-style ticks (1.0001^tick).
    sqrt(price) = (1.0001)^(tick / 2)
    """
    base = Decimal("1.0001")
    return (base ** Decimal(tick)).sqrt()


def _amounts_from_L(L: Decimal, sqrtP: Decimal, sqrtA: Decimal, sqrtB: Decimal) -> Tuple[Decimal, Decimal]:
    """
    Uniswap-style piecewise:
      if sqrtP <= sqrtA:           amt0 = L * (sqrtB - sqrtA) / (sqrtB * sqrtA); amt1 = 0
      if sqrtA < sqrtP < sqrtB:    amt0 = L * (sqrtB - sqrtP) / (sqrtB * sqrtP); amt1 = L * (sqrtP - sqrtA)
      if sqrtP >= sqrtB:           amt0 = 0;                                   amt1 = L * (sqrtB - sqrtA)
    """
    if sqrtP <= sqrtA:
        amt0 = L * (sqrtB - sqrtA) / (sqrtB * sqrtA)
        amt1 = Decimal(0)
    elif sqrtP >= sqrtB:
        amt0 = Decimal(0)
        amt1 = L * (sqrtB - sqrtA)
    else:
        amt0 = L * (sqrtB - sqrtP) / (sqrtB * sqrtP)
        amt1 = L * (sqrtP - sqrtA)
    return (amt0, amt1)


class RaydiumCore:
    def __init__(self, rpc: SolanaRPC | None = None, api: RaydiumApi | None = None):
        self.rpc = rpc or SolanaRPC()
        self.api = api or RaydiumApi()

    def load_owner_portfolio(self, owner: str) -> RaydiumPortfolio:
        # 1) Discover on-chain
        raw_positions = nft_positions.discover_positions(self.rpc, owner)

        if not raw_positions:
            return RaydiumPortfolio(owner=owner, positions=[], total_usd=0.0, prices={})

        # 2) Pull pool info from Raydium API
        pool_ids = sorted({p.pool_id for p in raw_positions})
        pool_map = self.api.pools_by_ids(pool_ids)

        # For valuation, gather mint0/mint1 and current tick/sqrt price if available
        enriched: List[RaydiumPosition] = []
        mint_set: set[str] = set()
        for p in raw_positions:
            meta = pool_map.get(p.pool_id) or {}
            # In API, fields vary slightly; normalize common keys
            mint0 = meta.get("mintA") or meta.get("mint0") or meta.get("mint_a") or meta.get("baseMint")
            mint1 = meta.get("mintB") or meta.get("mint1") or meta.get("mint_b") or meta.get("quoteMint")
            tick_cur = meta.get("tickCurrent") or meta.get("currentTick") or meta.get("tick")
            sqrt_x64 = meta.get("sqrtPriceX64") or meta.get("sqrtPrice")  # may be None on some endpoints

            if mint0:
                mint_set.add(mint0)
            if mint1:
                mint_set.add(mint1)

            ep = replace(
                p,
                mint0=mint0,
                mint1=mint1,
                current_tick=int(tick_cur) if tick_cur is not None else None,
            )
            enriched.append(ep)

        # 3) Price map for mints
        mint_prices = self.api.mint_prices(sorted(mint_set)) if mint_set else {}

        # 4) Compute amounts & USD value per position
        final_positions: List[RaydiumPosition] = []
        total_usd = Decimal(0)

        for p in enriched:
            if p.current_tick is None or p.mint0 is None or p.mint1 is None:
                final_positions.append(p)
                continue

            sqrtP = _tick_to_sqrt_price(p.current_tick)
            sqrtA = _tick_to_sqrt_price(p.tick_lower)
            sqrtB = _tick_to_sqrt_price(p.tick_upper)
            L = Decimal(p.liquidity)

            amt0, amt1 = _amounts_from_L(L, sqrtP, sqrtA, sqrtB)

            price0 = Decimal(str(mint_prices.get(p.mint0, 0.0)))
            price1 = Decimal(str(mint_prices.get(p.mint1, 0.0)))
            usd_val = (amt0 * price0) + (amt1 * price1)

            fp = replace(p, amount0=float(amt0), amount1=float(amt1), usd_value=float(usd_val))
            final_positions.append(fp)
            total_usd += usd_val

        return RaydiumPortfolio(
            owner=owner,
            positions=final_positions,
            total_usd=float(total_usd),
            prices=mint_prices,
        )
