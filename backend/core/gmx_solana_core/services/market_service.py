from typing import Any, Dict
from ..clients.solana_rpc_client import SolanaRpcClient

class MarketService:
    def __init__(self, rpc_client: SolanaRpcClient, idl_loader=None):
        self.rpc = rpc_client
        self.idl = idl_loader

    def list_markets_basic(self, store_program_id: str) -> Dict[str, Any]:
        # Light query: no account data payload (offset 0, length 0)
        accs = self.rpc.get_program_accounts(
            store_program_id,
            encoding="base64",
            data_slice={"offset": 0, "length": 0},
            commitment="processed",
        )
        sample = [a.get("pubkey") for a in accs[:10]]
        return {
            "program": store_program_id,
            "account_count": len(accs),
            "sample_pubkeys": sample,
            "note": "Light listing (no data). Use S-2.2 to decode via IDL."
        }
