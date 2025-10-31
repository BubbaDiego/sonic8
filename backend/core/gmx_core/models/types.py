from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class Price:
    """Simple price container (USD with 1e30 fixed-point in Phase 2)."""
    mark: float
    entry: Optional[float] = None
    liq: Optional[float] = None


@dataclass
class FundingData:
    rate_1h: Optional[float] = None
    rate_8h: Optional[float] = None
    paid_to_date: Optional[float] = None


@dataclass
class GMXMarket:
    chain: str
    market_addr: str
    symbol: str
    base_token: str
    quote_token: str


@dataclass
class GMXPosition:
    chain: str
    account: str
    market_addr: str
    is_long: bool
    size_usd: float
    collateral_token: str
    collateral_amount: float
    price: Price
    funding: FundingData
    status: str
    opened_at: Optional[int] = None
    updated_at: Optional[int] = None


@dataclass
class NormalizedPosition:
    """Shape consumed by Positions Core + DL writers."""
    protocol: str
    chain: str
    market: str
    account: str
    side: str
    size_usd: float
    collateral_token: str
    collateral_amount: float
    entry_price: Optional[float]
    mark_price: float
    liq_price: Optional[float]
    leverage: Optional[float]
    pnl_unrealized: Optional[float]
    funding_paid: Optional[float]
    status: str
    opened_at: Optional[int]
    updated_at: Optional[int]
