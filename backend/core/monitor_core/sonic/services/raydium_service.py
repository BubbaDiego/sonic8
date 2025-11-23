# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Dict, List, Optional


def _resolve_active_owner(dl: Any) -> Optional[str]:
    """
    Best-effort helper to resolve the active wallet public key from DataLocker.
    """

    wmgr = getattr(dl, "wallets", None)
    if not wmgr:
        return None

    # 1) dedicated helper
    try:
        get_active = getattr(wmgr, "get_active_wallet", None)
        if callable(get_active):
            w = get_active()
            if isinstance(w, dict):
                return w.get("public_address") or w.get("pubkey")
    except Exception:
        pass

    # 2) scan wallet list
    try:
        ws = wmgr.get_wallets() or []
    except Exception:
        ws = []

    owner: Optional[str] = None
    for w in ws:
        if not isinstance(w, dict):
            continue
        if w.get("is_active"):
            owner = w.get("public_address") or w.get("pubkey")
            if owner:
                break

    # 3) fallback: first wallet
    if not owner and ws:
        w0 = ws[0]
        if isinstance(w0, dict):
            owner = w0.get("public_address") or w0.get("pubkey")

    return owner or None


def _load_positions_from_db(dl: Any, owner: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch Raydium positions from the DB and normalize to panel payload shape."""

    try:
        mgr = getattr(dl, "raydium", None)
        if mgr is None:
            return None
        rows: List[Dict[str, Any]] = []
        if owner:
            rows = mgr.get_by_owner(owner) or []
        else:
            rows = mgr.get_positions() or []
        if not rows:
            return None
        normed: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            normed.append(
                {
                    "pool_id": row.get("pool_id") or row.get("pool") or row.get("name"),
                    "mint": row.get("nft_mint") or row.get("mint"),
                    "owner": row.get("owner"),
                    "token_a_symbol": row.get("token_a")
                    or row.get("token_a_symbol")
                    or row.get("token_a_mint"),
                    "token_b_symbol": row.get("token_b")
                    or row.get("token_b_symbol")
                    or row.get("token_b_mint"),
                    "usd_value": row.get("usd_total"),
                    "apr": row.get("apr") or row.get("apy"),
                }
            )
        return {"rows": normed}
    except Exception:
        return None


def sync_raydium_service(ctx: Any) -> Dict[str, Any]:
    """
    Sonic service adapter for Raydium CL valuation.

    - Resolve owner wallet
    - Call `value_owner_nfts(owner)`
    - Persist payload into dl.system["raydium_positions"]
    - Return a dict with ok/source/count for Cycle Activity.
    """

    dl = getattr(ctx, "dl", None)
    if dl is None:
        return {"ok": True, "source": "noop", "result": None}

    owner = _resolve_active_owner(dl)

    try:
        mod = import_module("backend.core.raydium_core.services.nft_valuation")
        fn = getattr(mod, "value_owner_nfts", None)
        if not callable(fn):
            return {"ok": True, "source": "noop", "result": None}

        res = fn(owner) if owner else fn(None)

        payload: Optional[Any] = res if isinstance(res, (dict, list)) else None
        count: Optional[int] = None

        # Persist into system data for the Raydium panel
        try:
            sys_mgr = getattr(dl, "system", None)
            if sys_mgr is not None:
                if payload is None:
                    payload = _load_positions_from_db(dl, owner)
                setter = getattr(sys_mgr, "set_var", None)
                if callable(setter):
                    setter("raydium_positions", payload if payload is not None else res)

            # Derive count using the same helper the panel uses
            try:
                tmod = import_module("backend.core.raydium_core.console.raydium_console")
                conv = getattr(tmod, "raydium_cl_positions_from_payload", None)
                if callable(conv):
                    positions = conv(payload) if payload is not None else []
                    if isinstance(positions, list):
                        count = len(positions)
            except Exception:
                if isinstance(res, int):
                    count = res
                else:
                    count = None
        except Exception:
            # system data failure is non-fatal; Sonic should keep running
            pass

        details: Dict[str, Any] = {
            "ok": True,
            "source": "raydium.valuation",
            "result": res,
        }
        if count is not None:
            details["count"] = count

        try:
            details["checked_ts"] = datetime.now(timezone.utc).isoformat()
        except Exception:
            pass

        return details

    except Exception as exc:
        # Non-critical: mark as warn, not a hard error for the whole cycle.
        return {
            "ok": False,
            "severity": "warn",
            "source": "raydium.valuation.error",
            "error_note": f"Raydium valuation failed: {exc!r}",
        }
