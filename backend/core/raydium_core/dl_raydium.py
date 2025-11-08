from __future__ import annotations
"""
Import shim for Raydium DataLocker manager.

The Positions panel expects: backend.core.raydium_core.dl_raydium.DLRaydiumManager

This shim tries several candidate modules and re-exports DLRaydiumManager.
If none found, it defines a stub that raises a helpful RuntimeError on use.
"""

import importlib

_CANDIDATES = (
    "backend.core.raydium_core_impl.dl_raydium",  # if you keep impls separate
    "raydium_core.dl_raydium",                    # alt package name
    "dl_raydium",                                 # project-root module
)

DLRaydiumManager = None  # type: ignore

for modname in _CANDIDATES:
    try:
        mod = importlib.import_module(modname)
        DLRaydiumManager = getattr(mod, "DLRaydiumManager", None)
        if DLRaydiumManager:
            break
    except Exception:
        continue

if DLRaydiumManager is None:
    class DLRaydiumManager:  # type: ignore
        def __init__(self, *a, **kw):
            raise RuntimeError(
                "DLRaydiumManager not found. Place your implementation at "
                "'backend/core/raydium_core/dl_raydium.py' or ensure one of "
                f"{_CANDIDATES} is importable."
            )
