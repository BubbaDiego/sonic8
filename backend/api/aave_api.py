from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.aave_core.aave_config import AaveConfig
from backend.core.aave_core.aave_service import (
    get_market,
    get_user_positions,
    make_portfolio_payload,
    make_positions_payload,
)
from backend.core.aave_core import aave_actions as act

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/aave", tags=["aave"])


def _cfg() -> AaveConfig:
    return AaveConfig.from_env()


# ---------------- reads ----------------

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


# ---------------- writes ----------------

class TxRequestModel(BaseModel):
    user: str = Field(..., description="Sender/position owner, 0x…")
    reserve: str = Field(..., description="Underlying asset address, 0x…")
    amount: str = Field(..., description="Human value, e.g. '100.0'")
    market: Optional[str] = Field(None, description="Pool address; if omitted, uses config.pool")

class TxResult(BaseModel):
    chainId: int
    txs: List[str]


def _ok(cfg: AaveConfig, txs: List[str]) -> Dict[str, Any]:
    return TxResult(chainId=cfg.chain_id, txs=txs).model_dump()


@router.post("/supply", response_model=TxResult)
def api_supply(req: TxRequestModel, cfg: AaveConfig = Depends(_cfg)) -> Dict[str, Any]:
    try:
        txs = act.supply(cfg, user=req.user, reserve=req.reserve, amount=req.amount, market=req.market)
        return _ok(cfg, txs)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/withdraw", response_model=TxResult)
def api_withdraw(req: TxRequestModel, cfg: AaveConfig = Depends(_cfg)) -> Dict[str, Any]:
    try:
        txs = act.withdraw(cfg, user=req.user, reserve=req.reserve, amount=req.amount, market=req.market)
        return _ok(cfg, txs)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/borrow", response_model=TxResult)
def api_borrow(req: TxRequestModel, cfg: AaveConfig = Depends(_cfg)) -> Dict[str, Any]:
    try:
        txs = act.borrow(cfg, user=req.user, reserve=req.reserve, amount=req.amount, market=req.market)
        return _ok(cfg, txs)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/repay", response_model=TxResult)
def api_repay(req: TxRequestModel, cfg: AaveConfig = Depends(_cfg)) -> Dict[str, Any]:
    try:
        txs = act.repay(cfg, user=req.user, reserve=req.reserve, amount=req.amount, market=req.market)
        return _ok(cfg, txs)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
