from typing import Any, Dict, List
from ..clients.solana_rpc_client import SolanaRpcClient, RpcError


def _normalize_gpa_result(obj) -> List[dict]:
    """
    Helius getProgramAccountsV2 returns a dict (paged).
    Some nodes return a list for the legacy GPA.
    Normalize to a list of account dicts.
    """
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("value", "accounts", "result", "items"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
    return []


class MarketService:
    def __init__(self, rpc_client: SolanaRpcClient, idl_loader=None):
        self.rpc = rpc_client
        self.idl = idl_loader

    def list_markets_basic(self, store_program_id: str, limit: int = 100, page: int = 1) -> Dict[str, Any]:
        # Prefer Helius GPA-v2 (paged), fallback to lightweight legacy GPA.
        try:
            raw = self.rpc.get_program_accounts_v2(
                store_program_id,
                limit=limit,
                page=page,
                encoding="base64",
                data_slice={"offset": 0, "length": 0},
                commitment="processed",
            )
        except RpcError:
            raw = self.rpc.get_program_accounts(
                store_program_id,
                encoding="base64",
                data_slice={"offset": 0, "length": 0},
                commitment="processed",
            )

        accs = _normalize_gpa_result(raw)
        sample = [a.get("pubkey") for a in accs[:10] if isinstance(a, dict)]

        return {
            "program": store_program_id,
            "page": page,
            "limit": limit,
            "account_count_page": len(accs),
            "sample_pubkeys": sample,
            "note": "Paged listing via GPA-v2; S-2.2 will decode via IDL."
        }
