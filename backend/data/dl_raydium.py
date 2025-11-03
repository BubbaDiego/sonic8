"""
DLRaydium — light data layer facade for Raydium read-only calls.

This mirrors the project’s DataLocker-style modules (e.g., dl_alerts) but keeps
it dependency-free for a first pass. You can wire this into DataLocker later if desired.
"""

from __future__ import annotations

from typing import Dict, List

from backend.core.raydium_core.raydium_core import RaydiumCore
from backend.core.raydium_core.rpc import SolanaRPC
from backend.core.raydium_core.raydium_api import RaydiumApi
from backend.core.raydium_core.raydium_schema import RaydiumPortfolio


class DLRaydium:
    def __init__(self, rpc_url: str | None = None):
        self.core = RaydiumCore(rpc=SolanaRPC(rpc_url), api=RaydiumApi())

    # Simple, synchronous read
    def get_owner_portfolio(self, owner: str) -> RaydiumPortfolio:
        return self.core.load_owner_portfolio(owner)
