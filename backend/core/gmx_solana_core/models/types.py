from dataclasses import dataclass
from typing import Optional

@dataclass
class Price:
    mark: float
    entry: Optional[float] = None
    liq: Optional[float] = None

@dataclass
class FundingData:
    rate_1h: Optional[float] = None
    paid_to_date: Optional[float] = None

@dataclass
class SolMarket:
    address: str
    symbol: str
    base_token: str
    quote_token: str

@dataclass
class SolPosition:
    account: str
    market_addr: str
    is_long: bool
    size_usd: float
    collateral_token: str
    collateral_amount: float
    price: Price
    funding: FundingData
    opened_at: Optional[int] = None
    updated_at: Optional[int] = None

@dataclass
class NormalizedPosition:
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
