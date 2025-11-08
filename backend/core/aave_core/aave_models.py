from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Reserve:
    symbol: str
    address: str
    decimals: int
    supply_apy: float | None = None
    variable_borrow_apy: float | None = None
    ltv: float | None = None
    liquidation_threshold: float | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Market:
    chain_id: int
    reserves: list[Reserve]

    def to_dict(self) -> Dict[str, Any]:
        return {"chain_id": self.chain_id, "reserves": [r.to_dict() for r in self.reserves]}


@dataclass
class UserReserve:
    symbol: str
    underlying: str
    supplied: float  # in underlying units or normalized
    borrowed: float  # in underlying units or normalized
    supplied_usd: float | None = None
    borrowed_usd: float | None = None
    use_as_collateral: bool | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Health:
    total_collateral_usd: float
    total_debt_usd: float
    health_factor: float | None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserPositions:
    chain_id: int
    address: str
    reserves: list[UserReserve]
    health: Optional[Health] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "chain_id": self.chain_id,
            "address": self.address,
            "reserves": [r.to_dict() for r in self.reserves],
        }
        if self.health:
            d["health"] = self.health.to_dict()
        return d

    # ——— Helpers to emit Sonic-shaped payloads ———
    def to_sonic_positions(self) -> Dict[str, Any]:
        """
        Map Aave supplies/borrows into Sonic's SCHEMA-POSITIONS.
        NOTE: We encode 'supply' as 'long' and 'borrow' as 'short' to reuse visuals.
        'entryPrice' is not meaningful here; 0.0 is used as a neutral value.
        """
        items = []
        for r in self.reserves:
            if r.supplied_usd and r.supplied_usd > 0:
                items.append(
                    {"symbol": r.symbol, "side": "long", "sizeUsd": float(r.supplied_usd), "entryPrice": 0.0}
                )
            if r.borrowed_usd and r.borrowed_usd > 0:
                items.append(
                    {"symbol": r.symbol, "side": "short", "sizeUsd": float(r.borrowed_usd), "entryPrice": 0.0}
                )
        return {"items": items, "count": len(items)}

    def to_sonic_portfolio(self) -> Dict[str, Any]:
        """
        Emit a minimal SCHEMA-PORTFOLIO-compatible object: balances (empty) + positions.
        """
        return {"balances": [], "positions": self.to_sonic_positions()}
