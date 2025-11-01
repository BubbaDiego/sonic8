"""
Positions source (Phase S-2.1 minimal).

We filter program accounts by owner using a memcmp offset (provided via flag).
This yields a count + sample keys to prove the flow. S-2.2 will decode accounts.
"""
from typing import Any, Dict, List, Optional
from ..clients.solana_rpc_client import SolanaRpcClient

class SolanaPositionSource:
    def __init__(self, rpc_client: SolanaRpcClient):
        self.rpc = rpc_client

    def list_open_positions_basic(self, store_program: str, wallet_b58: str, owner_offset: int) -> Dict[str, Any]:
        # memcmp expects base58 data; providing the wallet base58 is valid for Solana memcmp.
        mem = [{"offset": owner_offset, "bytes": wallet_b58}]
        accs = self.rpc.get_program_accounts(store_program, encoding="base64", memcmp=mem)
        sample = [a.get("pubkey") for a in accs[:10]]
        return {
            "program": store_program,
            "wallet": wallet_b58,
            "owner_offset": owner_offset,
            "matched_account_count": len(accs),
            "sample_pubkeys": sample,
            "note": "Phase S-2.1 uses memcmp; S-2.2 will decode and print structured positions."
        }
