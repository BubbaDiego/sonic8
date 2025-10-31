"""
GMX Reader/DataStore views (Phase 1 stub).

Phase 2:
- read positions/markets via Reader
- derive execution estimates
- confirm addresses via DataStore/Keys
"""
from typing import Any


class GmxReaderClient:
    def __init__(self, rpc_http: str, reader_addr: str, datastore_addr: str):
        self.rpc_http = rpc_http
        self.reader_addr = reader_addr
        self.datastore_addr = datastore_addr

    def position_view(self, account: str, market_addr: str) -> Any:
        raise NotImplementedError("Phase 2")
