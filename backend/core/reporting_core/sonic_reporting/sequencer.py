# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional
import importlib, traceback

# toggles
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
        _dbg(f"skip: {fq} (module not found)"); return False
    fn = getattr(mod, "render", None)
    if not callable(fn):
        _dbg(f"skip: {fq} (no callable `render`)"); return False
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
        _dbg(f"skip: {fq} (module not found)"); return False
    fn = getattr(mod, "render", None)
    if not callable(fn):
        _dbg(f"skip: {fq} (no callable `render`)"); return False
    try:
        fn(dl, csum, default_json_path)    # standard panel contract
        _dbg(f"ok: {fq}")
        return True
    except TypeError:
        # if the panel hasn't added the optional 3rd param yet, try 2-arg once
        try:
            fn(dl, csum)
            _dbg(f"ok: {fq} (2-arg)")
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

def render_startup_banner(dl, default_json_path: Optional[str] = None, **_: Any) -> None:
    if not ENABLE_BANNER:
        _dbg("banner disabled"); return
    _call_banner("banner_panel", dl=dl, default_json_path=default_json_path)

def render_cycle(dl, csum: Dict[str, Any] | None, *, default_json_path: Optional[str] = None, **_: Any) -> None:
    csum = csum or {}
    if ENABLE_SYNC:      _call_panel("sync_panel",      dl=dl, csum=csum, default_json_path=default_json_path)
    if ENABLE_PRICE:     _call_panel("price_panel",     dl=dl, csum=csum, default_json_path=default_json_path)
    if ENABLE_POSITIONS: _call_panel("positions_panel", dl=dl, csum=csum, default_json_path=default_json_path)
    if ENABLE_RAYDIUM:   _call_panel("raydium_panel",   dl=dl, csum=csum, default_json_path=default_json_path)
    if ENABLE_XCOM:      _call_panel("xcom_panel",      dl=dl, csum=csum, default_json_path=default_json_path)
    if ENABLE_WALLETS:   _call_panel("wallets_panel",   dl=dl, csum=csum, default_json_path=default_json_path)
