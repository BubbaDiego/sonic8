"""
Thin Solana RPC wrapper for Phase S-2.

Phase S-1: keep lightweight and optional. Phase S-2 will use anchorpy or solana-py.
"""
from typing import Any, Dict, List, Optional

class SolanaRpcClient:
    def __init__(self, rpc_http: str, timeout: float = 10.0):
        self.rpc_http = rpc_http
        self.timeout = timeout

    def get_multiple_accounts(self, pubkeys: List[str]) -> List[Dict[str, Any]]:
        """
        Placeholder: implement via solana-py / anchorpy in Phase S-2.
        For now, raise an informative error to indicate it's not wired.
        """
        raise NotImplementedError("Solana RPC methods will be implemented in Phase S-2 (anchorpy/solana-py).")
