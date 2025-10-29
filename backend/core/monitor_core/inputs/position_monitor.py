"""Utility helpers for collecting position data during a Sonic cycle."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import datetime as _dt
import logging
import traceback

_LOG = logging.getLogger(__name__)


def _now_iso() -> str:
    return _dt.datetime.utcnow().isoformat()


def _provider_from_dl(dl: Any) -> Any:
    """Return the most specific positions provider exposed by the DataLocker."""
    for attr in ("positions_core_adapter", "positions_core", "positions", "market"):
        prov = getattr(dl, attr, None)
        if prov:
            return prov
    return None


def _as_dict(item: Any, provider_name: str) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item
    for attr in ("model_dump", "dict", "to_dict"):
        fn = getattr(item, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                _LOG.debug(
                    "position provider %s.%s() conversion failed", provider_name, attr, exc_info=True
                )
    return getattr(item, "__dict__", {}) or {}


def collect_positions(dl: Any) -> Tuple[List[Dict[str, Any]], Optional[str], Dict[str, Optional[str]]]:
    """Collect normalized position rows from any available provider on ``dl``.

    Returns a tuple of (rows, error_text, metadata).
    Metadata includes ``provider`` and ``source`` keys describing the source used.
    """

    prov = _provider_from_dl(dl)
    if not prov:
        _LOG.debug("positions collector: no provider found on DataLocker")
        return [], "no positions provider found on DataLocker", {"provider": "None", "source": None}

    provider_cls = getattr(prov, "__class__", type("X", (), {}))
    provider_name = getattr(provider_cls, "__name__", str(provider_cls))

    has_list = any(hasattr(prov, attr) for attr in ("list_positions_sync", "list_positions"))
    has_get = any(hasattr(prov, attr) for attr in ("get_positions", "get_all_positions"))
    _LOG.debug(
        "positions collector: provider=%s list_methods=%s get_methods=%s",
        provider_name,
        has_list,
        has_get,
    )

    rows_raw: List[Any]
    source: Optional[str] = None
    try:
        if hasattr(prov, "list_positions_sync"):
            source = "list_positions_sync"
            rows_raw = prov.list_positions_sync() or []
        elif hasattr(prov, "list_positions"):
            source = "list_positions"
            rows_raw = prov.list_positions() or []
        elif hasattr(prov, "get_positions"):
            source = "get_positions"
            rows_raw = prov.get_positions() or []
        elif hasattr(prov, "get_all_positions"):
            source = "get_all_positions"
            rows_raw = prov.get_all_positions() or []
        else:
            err = f"provider {provider_name} has no list/get methods"
            _LOG.warning("positions collector: %s", err)
            return [], err, {"provider": provider_name, "source": None}

        mapped = [_as_dict(item, provider_name) for item in rows_raw]
        stamp = _now_iso()
        rows: List[Dict[str, Any]] = []
        for item in mapped:
            asset = (item.get("asset") or item.get("asset_type") or item.get("symbol") or "").upper()
            side = (item.get("side") or item.get("position_type") or item.get("dir") or "").upper()
            rows.append(
                {
                    "id": item.get("id") or item.get("position_id"),
                    "asset": asset,
                    "side": side,
                    "size_usd": item.get("size_usd")
                    or item.get("value_usd")
                    or item.get("position_value_usd"),
                    "entry_price": item.get("entry_price")
                    or item.get("avg_entry")
                    or item.get("avg_price"),
                    "avg_price": item.get("avg_price"),
                    "liq_dist": item.get("liq_dist")
                    or item.get("liquidation_distance")
                    or item.get("liq_percent"),
                    "pnl": item.get("pnl_after_fees_usd")
                    or item.get("pnl_usd")
                    or item.get("pnl"),
                    "ts": item.get("ts") or stamp,
                }
            )

        if not rows:
            err = f"provider {provider_name}.{source} returned 0 rows"
            _LOG.warning("positions collector: %s", err)
            return [], err, {"provider": provider_name, "source": source}

        _LOG.debug(
            "positions collector: provider %s.%s returned %d row(s)",
            provider_name,
            source,
            len(rows),
        )
        return rows, None, {"provider": provider_name, "source": source}
    except Exception as exc:
        tb_lines = traceback.format_exc(limit=2).splitlines()
        tail = tb_lines[-1] if tb_lines else ""
        err = f"provider {provider_name} crashed: {type(exc).__name__}: {exc} | {tail}"
        _LOG.exception(
            "positions collector: provider %s failed via %s", provider_name, source or "unknown"
        )
        return [], err, {"provider": provider_name, "source": source}
