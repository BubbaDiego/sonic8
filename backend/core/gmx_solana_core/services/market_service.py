"""
Market discovery service (Phase S-2).

Will expose:
- list_markets
- get_market_by_addr
- token metadata (decimals, symbol)
"""
class MarketService:
    def __init__(self, rpc_client, idl_loader=None):
        self.rpc = rpc_client
        self.idl = idl_loader
