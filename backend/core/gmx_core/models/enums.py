from enum import Enum, IntEnum


class ChainKey(str, Enum):
    ARBITRUM = "arbitrum"
    AVALANCHE = "avalanche"


class OrderSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class OrderType(IntEnum):
    # Align with GMX V2 (placeholder numeric values; confirm in Phase 2)
    MARKET_INCREASE = 2
    LIMIT_INCREASE = 3
    MARKET_DECREASE = 4
    LIMIT_DECREASE = 5
    STOP_LOSS_DECREASE = 6


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"
