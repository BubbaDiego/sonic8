from backend.core.gmx_core.services.position_source import GMXPositionSource

class FakeRest:
    def get_tickers(self):
        # tokenSymbol -> { price: ... }
        return {"ETH": {"price": 3500.0}}
    def get_markets_info(self):
        return {"markets": [{"address": "0xabc", "indexToken": {"symbol": "ETH"}}]}

class FakeSubsquid:
    def __init__(self, rows):
        self._rows = rows
    def query(self, q, variables=None):
        return {"data": {"positions": self._rows}}

def test_source_list_and_normalize_basic():
    rows = [{
        "account": "0x111",
        "marketAddress": "0xabc",
        "collateralToken": "0xusdc",
        "isLong": True,
        "sizeUsd": "10000",
        "sizeInTokens": "3.0",
        "collateralAmount": "1000",
        "entryPrice": "3400",
        "liquidationPrice": "2800",
        "createdAt": 123,
        "updatedAt": 456
    }]
    src = GMXPositionSource("arbitrum", rest=FakeRest(), subsquid=FakeSubsquid(rows))
    gmx_positions = src.list_open_positions("0x111")
    assert len(gmx_positions) == 1
    norm = src.normalize(gmx_positions)
    p = norm[0]
    assert p.symbol == "ETH-USD"
    assert p.mark_price == 3500.0
    assert p.entry_price == 3400.0
    assert p.side == "LONG"
    assert p.market_address == "0xabc"
