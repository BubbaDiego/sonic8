from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.aave_core.aave_config import AaveConfig
from backend.core.aave_core.aave_service import (
    get_market,
    get_user_positions,
    make_portfolio_payload,
    make_positions_payload,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/aave", tags=["aave"])


def _cfg() -> AaveConfig:
    return AaveConfig.from_env()


@router.get("/markets")
def api_markets(cfg: AaveConfig = Depends(_cfg)) -> Dict[str, Any]:
    market = get_market(cfg).to_dict()
    return market


@router.get("/positions")
def api_positions(
    user: str = Query(..., description="EVM address 0x…"),
    cfg: AaveConfig = Depends(_cfg),
) -> Dict[str, Any]:
    up = get_user_positions(cfg, user)
    return make_positions_payload(up)


@router.get("/portfolio")
def api_portfolio(
    user: str = Query(..., description="EVM address 0x…"),
    cfg: AaveConfig = Depends(_cfg),
) -> Dict[str, Any]:
    up = get_user_positions(cfg, user)
    return make_portfolio_payload(up)


@router.get("/health")
def api_health(
    user: str = Query(..., description="EVM address 0x…"),
    cfg: AaveConfig = Depends(_cfg),
) -> Dict[str, Any]:
    up = get_user_positions(cfg, user)
    if not up.health:
        raise HTTPException(status_code=502, detail="No health data returned")
    return up.health.to_dict()
