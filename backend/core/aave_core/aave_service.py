from __future__ import annotations

import logging
from typing import Any, Dict, List

from .aave_client import AaveGraphQLClient
from .aave_config import AaveConfig
from .aave_models import Health, Market, Reserve, UserPositions, UserReserve

log = logging.getLogger(__name__)


def _safe_num(x) -> float | None:
    try:
        return float(x) if x is not None else None
    except Exception:  # noqa: BLE001
        return None


def get_market(cfg: AaveConfig) -> Market:
    """Return Market (reserves + basic risk params) for cfg.chain_id."""
    client = AaveGraphQLClient(cfg)
    data = client.fetch_market()
    reserves: List[Reserve] = []
    for r in data.get("market", {}).get("reserves", []) or []:
        reserves.append(
            Reserve(
                symbol=r.get("symbol"),
                address=r.get("underlyingAddress"),
                decimals=int(r.get("decimals", 18)),
                supply_apy=_safe_num(r.get("supplyApy")),
                variable_borrow_apy=_safe_num(r.get("variableBorrowApy")),
                ltv=_safe_num(r.get("ltv")),
                liquidation_threshold=_safe_num(r.get("liquidationThreshold")),
            )
        )
    return Market(chain_id=cfg.chain_id, reserves=reserves)


def get_user_positions(cfg: AaveConfig, user_address: str) -> UserPositions:
    """Return normalized user reserves + health."""
    client = AaveGraphQLClient(cfg)
    data = client.fetch_user_positions(user_address)
    user = (data.get("market") or {}).get("user") or {}
    reserves: List[UserReserve] = []
    for ur in user.get("reserves", []) or []:
        r = ur.get("reserve") or {}
        reserves.append(
            UserReserve(
                symbol=r.get("symbol"),
                underlying=r.get("underlyingAddress"),
                supplied=_safe_num(ur.get("supplied")) or 0.0,
                borrowed=_safe_num(ur.get("borrowed")) or 0.0,
                supplied_usd=_safe_num(ur.get("suppliedUsd")) or 0.0,
                borrowed_usd=_safe_num(ur.get("borrowedUsd")) or 0.0,
                use_as_collateral=bool(ur.get("usageAsCollateralEnabledOnUser")),
            )
        )

    ad = user.get("accountData") or {}
    health = Health(
        total_collateral_usd=_safe_num(ad.get("totalCollateralUsd")) or 0.0,
        total_debt_usd=_safe_num(ad.get("totalDebtUsd")) or 0.0,
        health_factor=_safe_num(ad.get("healthFactor")),
    )
    return UserPositions(chain_id=cfg.chain_id, address=user_address, reserves=reserves, health=health)


# ——— Sonic schema mapping helpers ———

def make_positions_payload(up: UserPositions) -> Dict[str, Any]:
    """SCHEMA-POSITIONS (drop-in for existing panels)."""
    return up.to_sonic_positions()


def make_portfolio_payload(up: UserPositions) -> Dict[str, Any]:
    """SCHEMA-PORTFOLIO (balances intentionally empty for now)."""
    return up.to_sonic_portfolio()
