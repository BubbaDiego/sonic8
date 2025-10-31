"""
Event indexer (Phase 1 stub).

Phase 3:
- Subscribe to EventEmitter logs via WS RPC
- Push events → queue → bridge → DL
- On startup, seek from last persisted block
"""
class EventIndexer:
    def __init__(self, rpc_ws: str, event_emitter_addr: str):
        self.rpc_ws = rpc_ws
        self.event_emitter_addr = event_emitter_addr

    def run_forever(self) -> None:
        raise NotImplementedError("Phase 3")
