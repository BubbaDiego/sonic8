from __future__ import annotations
"""
Import shim for Raydium NFT model.

The Positions panel may import ClmmNFT symbols; this shim forwards to your real model
if present, or defines a minimal placeholder so imports don't crash.
"""

import importlib
from dataclasses import dataclass
from typing import Optional

_CANDIDATES = (
    "backend.core.raydium_core_impl.nft",
    "raydium_core.nft",
    "nft",
)

ClmmNFT = None  # type: ignore

for modname in _CANDIDATES:
    try:
        mod = importlib.import_module(modname)
        ClmmNFT = getattr(mod, "ClmmNFT", None)
        if ClmmNFT:
            break
    except Exception:
        continue

if ClmmNFT is None:
    @dataclass
    class ClmmNFT:  # type: ignore
        mint: str
        usd_total: float = 0.0
        checked_ts: Optional[str] = None
