from typing import Optional
from .types import SolPosition, NormalizedPosition

def leverage_from(pos: SolPosition) -> Optional[float]:
    try:
        if pos.collateral_amount and pos.size_usd:
            return max(pos.size_usd / float(pos.collateral_amount), 0.0)
    except Exception:
        pass
    return None

def to_normalized_position(pos: SolPosition) -> NormalizedPosition:
    return NormalizedPosition(
        protocol="gmx_sol",
        chain="solana",
        market=pos.market_addr,
        account=pos.account,
        side="long" if pos.is_long else "short",
        size_usd=pos.size_usd,
        collateral_token=pos.collateral_token,
        collateral_amount=pos.collateral_amount,
        entry_price=pos.price.entry,
        mark_price=pos.price.mark,
        liq_price=pos.price.liq,
        leverage=leverage_from(pos),
        pnl_unrealized=None,
        funding_paid=pos.funding.paid_to_date,
        status="open",
        opened_at=pos.opened_at,
        updated_at=pos.updated_at,
    )
