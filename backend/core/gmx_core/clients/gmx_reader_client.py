class ReaderNotReady(RuntimeError): pass

class GmxReaderClient:
    def __init__(self, rpc_http: str, reader_addr: str, datastore_addr: str):
        self.rpc_http = rpc_http
        self.reader_addr = reader_addr
        self.datastore_addr = datastore_addr

    def get_account_positions(self, account: str, start: int = 0, end: int = 1000):
        raise ReaderNotReady("Reader integration will be enabled in Phase 2.1 once ABI + web3 are wired.")

    # Future: get_account_position_info_list(...), get_position_info(...)


Reader contract methods for V2 (e.g., getAccountPositions, getAccountPositionInfoList, getPositionInfo) are documented here; we’ll include minimal ABI when we turn this on. 
gmx-docs.io
