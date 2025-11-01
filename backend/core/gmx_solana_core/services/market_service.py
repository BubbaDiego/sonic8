from typing import Any, Dict
from ..clients.solana_rpc_client import SolanaRpcClient, RpcError

class MarketService:
    def __init__(self, rpc_client: SolanaRpcClient, idl_loader=None):
        self.rpc = rpc_client
        self.idl = idl_loader

    def list_markets_basic(self, store_program_id: str, limit: int = 100, page: int = 1) -> Dict[str, Any]:
        # Try Helius GPA-v2 first (paged), fallback to light GPA if node doesn't support it.
        try:
            accs = self.rpc.get_program_accounts_v2(
                store_program_id,
                limit=limit,
                page=page,
                encoding="base64",
                data_slice={"offset": 0, "length": 0},
                commitment="processed",
            )
        except RpcError:
            accs = self.rpc.get_program_accounts(
                store_program_id,
                encoding="base64",
                data_slice={"offset": 0, "length": 0},
                commitment="processed",
            )
        sample = [a.get("pubkey") for a in accs[:10]]
        return {
            "program": store_program_id,
            "page": page,
            "limit": limit,
            "account_count_page": len(accs),
            "sample_pubkeys": sample,
            "note": "Paged listing via Helius getProgramAccountsV2; S-2.2 will decode via IDL."
        }
