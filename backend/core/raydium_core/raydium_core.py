from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from backend.data.dl_raydium import RaydiumDataLayer
from backend.core.raydium_core.raydium_schema import WalletBalances, TokenInfo


class RaydiumCore:
    """
    Service layer for Raydium reads.

    - Wallet balances via Solana RPC (no browser wallet).
    - Raydium public API: token list, pools.

    All network IO lives in RaydiumDataLayer.
    """

    def __init__(self, rpc_url: Optional[str] = None, raydium_api_base: Optional[str] = None):
        self.dl = RaydiumDataLayer(rpc_url=rpc_url, raydium_api_base=raydium_api_base)

    # ---- Wallet ----
    def get_wallet_balances(self, owner: str, include_zero: bool = False, enrich_meta: bool = True) -> WalletBalances:
        raw = self.dl.get_wallet_balances(owner, include_zero=include_zero)
        if enrich_meta:
            raw = self.dl.enrich_token_metadata(raw)
        return WalletBalances(**raw)

    # ---- Tokens / Pools (Raydium API) ----
    def get_token_list(self) -> list[TokenInfo]:
        data = self.dl.get_token_list()
        return [TokenInfo(**t) for t in data]

    def get_pool_list(self, **params) -> Dict[str, Any]:
        return self.dl.get_pool_list(**params)

    def fetch_pool_by_id(self, ids: Iterable[str]) -> Dict[str, Any]:
        return self.dl.fetch_pool_by_id(ids)

    def fetch_pool_by_mints(self, mint1: str, mint2: Optional[str] = None, **params) -> Dict[str, Any]:
        return self.dl.fetch_pool_by_mints(mint1, mint2, **params)
