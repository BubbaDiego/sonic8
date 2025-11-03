# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Sonic Reporting Sequencer (LEAN • NO SHIMS • CORRECT PATHS)

Expected panels & signatures:
  - banner_panel    : render(dl, default_json_path=None)
  - sync_panel      : render(dl, csum, default_json_path=None)
  - price_panel     : render(dl, csum, default_json_path=None)
  - positions_panel : render(dl, csum, default_json_path=None)
  - raydium_panel   : render(dl, csum, default_json_path=None)  # right after Positions
  - xcom_panel      : render(dl, csum, default_json_path=None)
  - wallets_panel   : render(dl, csum, default_json_path=None)

Monitor summary has been removed per your instruction.
"""

from typing import Any, Dict, Optional
import importlib, traceback

# one enable flag per panel (defaults ON)
ENABLE_BANNER       = True
ENABLE_SYNC         = True
ENABLE_PRICE        = True
ENABLE_POSITIONS    = True
ENABLE_RAYDIUM      = True
ENABLE_XCOM         = True
ENABLE_WALLETS      = True

DEBUG_SEQUENCER     = True


def _dbg(msg: str) -> None:
    if DEBUG_SEQUENCER:
        print(f"[SEQ] {msg}")


def _import(qualname: str):
    try:
        return importlib.import_module(qualname)
    except Exception as e:
        _dbg(f"import skip: {qualname} -> {e}")
        return None


def _call_banner(panel_mod: str, *, dl, default_json_path: Optional[str]) -> bool:
    fq = f"backend.core.reporting_core.sonic_reporting.{panel_mod}"
    mod = _import(fq)
    if not mod:
        _dbg(f"skip: {fq} (module not found)")
        return False
    fn = getattr(mod, "render", None)
    if not callable(fn):
        _dbg(f"skip: {fq} (no callable `render`)")
        return False
    try:
        fn(dl, default_json_path)     # banner contract
        _dbg(f"ok: {fq}")
        return True
    except Exception as exc:
        _dbg(f"{fq} raised: {exc.__class__.__name__}: {exc}")
        for line in traceback.format_exc(limit=3).rstrip().splitlines():
            _dbg(f"  {line}")
        return False


def _call_panel(panel_mod: str, *, dl, csum: Dict[str, Any], default_json_path: Optional[str]) -> bool:
    fq = f"backend.core.reporting_core.sonic_reporting.{panel_mod}"
    mod = _import(fq)
    if not mod:
        _dbg(f"skip: {fq} (module not found)")
        return False
    fn = getattr(mod, "render", None)
    if not callable(fn):
        _dbg(f"skip: {fq} (no callable `render`)")
        return False
    try:
        fn(dl, csum)                  # standard panel contract (no default_json_path)
        _dbg(f"ok: {fq}")
        return True
    except TypeError:
        # Panel already adopts the 3-arg contract (dl, csum, default_json_path); try that once.
        try:
            fn(dl, csum, default_json_path)
            _dbg(f"ok: {fq} (3-arg)")
            return True
        except Exception as exc:
            _dbg(f"{fq} raised: {exc.__class__.__name__}: {exc}")
            for line in traceback.format_exc(limit=3).rstrip().splitlines():
                _dbg(f"  {line}")
            return False
    except Exception as exc:
        _dbg(f"{fq} raised: {exc.__class__.__name__}: {exc}")
        for line in traceback.format_exc(limit=3).rstrip().splitlines():
            _dbg(f"  {line}")
        return False


# Public API

def render_startup_banner(dl, default_json_path: Optional[str] = None, **_: Any) -> None:
    if not ENABLE_BANNER:
        _dbg("banner disabled")
        return
    _call_banner("banner_panel", dl=dl, default_json_path=default_json_path)


def render_cycle(
    dl,
    csum: Dict[str, Any] | None,
    *,
    default_json_path: Optional[str] = None,
    **_: Any,
) -> None:
    csum = csum or {}

    # 1) Sync
    if ENABLE_SYNC:
        _call_panel("sync_panel", dl=dl, csum=csum, default_json_path=default_json_path)

    # 2) Price
    if ENABLE_PRICE:
        _call_panel("price_panel", dl=dl, csum=csum, default_json_path=default_json_path)

    # 3) Positions
    if ENABLE_POSITIONS:
        _call_panel("positions_panel", dl=dl, csum=csum, default_json_path=default_json_path)

    # 4) Raydium (right after Positions)
    if ENABLE_RAYDIUM:
        _call_panel("raydium_panel", dl=dl, csum=csum, default_json_path=default_json_path)

    # 5) XCOM check
    if ENABLE_XCOM:
        _call_panel("xcom_panel", dl=dl, csum=csum, default_json_path=default_json_path)

    # 6) Wallets
    if ENABLE_WALLETS:
        _call_panel("wallets_panel", dl=dl, csum=csum, default_json_path=default_json_path)
