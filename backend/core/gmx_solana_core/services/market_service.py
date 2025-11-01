"""
Market discovery service (Phase S-2.1 minimal).

We do a basic getProgramAccounts on the configured Store program and return counts
and a few sample pubkeys. S-2.2 will decode market/GLV accounts via IDL.
"""
from typing import Any, Dict
from ..clients.solana_rpc_client import SolanaRpcClient

class MarketService:
    def __init__(self, rpc_client: SolanaRpcClient, idl_loader=None):
        self.rpc = rpc_client
        self.idl = idl_loader

    def list_markets_basic(self, store_program_id: str) -> Dict[str, Any]:
        accs = self.rpc.get_program_accounts(store_program_id, encoding="base64")
        sample = [a.get("pubkey") for a in accs[:10]]
        return {
            "program": store_program_id,
            "account_count": len(accs),
            "sample_pubkeys": sample,
            "note": "Phase S-2.1 minimal; S-2.2 will decode markets via IDL."
        }
