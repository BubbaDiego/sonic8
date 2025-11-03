from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class RaydiumPosition:
    owner: str
    nft_mint: str
    pool_id: str
    tick_lower: int
    tick_upper: int
    liquidity: int
    tokens_owed0: int
    tokens_owed1: int
    # enrichment
    mint0: Optional[str] = None
    mint1: Optional[str] = None
    current_tick: Optional[int] = None
    sqrt_price: Optional[float] = None  # unscaled sqrt(price) if available
    amount0: Optional[float] = None
    amount1: Optional[float] = None
    usd_value: Optional[float] = None


@dataclass
class RaydiumPortfolio:
    owner: str
    positions: List[RaydiumPosition]
    total_usd: float
    prices: Dict[str, float]
