"""
Event indexer (Phase S-3 planned).

This module will subscribe to on-chain events via Helius/WS (or via webhooks)
and push updates into DL. Phase S-1 leaves as a stub.
"""
class EventIndexer:
    def __init__(self, rpc_http: str):
        self.rpc_http = rpc_http

    def run_forever(self):
        raise NotImplementedError("Implement event subscription in Phase S-3.")
