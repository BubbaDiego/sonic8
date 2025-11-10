# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from backend.models.monitor_status import MonitorState
from backend.core.monitor_core.resolver import ThresholdResolver, ResolutionTrace


def _safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _open_positions(dl: Any) -> List[Dict[str, Any]]:
    """
    Pull open positions from manager first, then DB.
    Returns a list of dict rows.
    """
    # manager first
    pmgr = getattr(dl, "positions", None)
    if pmgr:
        for name in ("get_positions", "list", "get_all", "positions"):
            fn = getattr(pmgr, name, None)
            try:
                rows = fn() if callable(fn) else (fn if isinstance(fn, list) else None)
            except TypeError:
                try:
                    rows = fn(None)
                except Exception:
                    rows = None
            except Exception:
                rows = None
            if isinstance(rows, list) and rows:
                out = []
                for r in rows:
                    d = r if isinstance(r, dict) else (getattr(r, "dict", lambda: {})() or getattr(r, "__dict__", {}) or {})
                    if _is_open(d):
                        out.append(d)
                return out
    # DB fallback
    try:
        cur = dl.db.get_cursor()
        cur.execute("SELECT * FROM positions")
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return [d for d in rows if _is_open(d)]
    except Exception:
        return []


def _is_open(d: Dict[str, Any]) -> bool:
    st = (d.get("status") or "").lower()
    if st in {"closed", "settled", "exited", "liquidated"}:
        return False
    if isinstance(d.get("is_open"), bool):
        return d["is_open"]
    for k in ("closed", "closed_at", "exit_ts", "exit_price"):
        if d.get(k) not in (None, "", 0):
            return False
    return True


def _current_price(d: Dict[str, Any]) -> Optional[float]:
    for k in ("current_price", "mark_price", "price", "now_price"):
        v = _safe_float(d.get(k))
        if v is not None:
            return v
    return None


def _liquid_distance_pct(d: Dict[str, Any]) -> Optional[float]:
    """
    Prefer DB-provided liquidation_distance (already in %).
    Else derive from current_price and liquidation_price.
    """
    # explicit distance
    dist = _safe_float(d.get("liquidation_distance"))
    if dist is not None:
        return dist
    # derive from prices
    liq_px = _safe_float(d.get("liquidation_price"))
    cur_px = _current_price(d)
    if liq_px is None or cur_px is None or cur_px <= 0:
        return None
    return abs(cur_px - liq_px) / cur_px * 100.0


def _asset(d: Dict[str, Any]) -> str:
    return str(d.get("asset_type") or d.get("asset") or d.get("symbol") or d.get("token") or "").upper()


def _ensure_resolver(ctx: Any) -> ThresholdResolver:
    res = getattr(ctx, "resolver", None)
    if isinstance(res, ThresholdResolver):
        return res
    cfg = getattr(ctx, "cfg", {}) or {}
    res = ThresholdResolver(cfg, getattr(ctx, "dl", None))
    setattr(ctx, "resolver", res)
    return res


def _register_trace(ctx: Any, trace: ResolutionTrace) -> None:
    if trace is None:
        return
    trace_dict = asdict(trace)
    adder = getattr(ctx, "add_resolve_traces", None)
    if callable(adder):
        adder([trace_dict])
        return
    bucket = getattr(ctx, "resolve_traces", None)
    if isinstance(bucket, list):
        bucket.append(trace_dict)
    else:
        setattr(ctx, "resolve_traces", [trace_dict])


def _state_from_comparator(op: str, value: Optional[float], thr: float) -> MonitorState:
    if value is None:
        return MonitorState.OK  # no data → don't panic the UI
    if op == "<":
        return MonitorState.BREACH if value < thr else MonitorState.OK
    if op == "<=":
        return MonitorState.BREACH if value <= thr else MonitorState.OK
    if op == ">":
        return MonitorState.BREACH if value > thr else MonitorState.OK
    if op == ">=":
        return MonitorState.BREACH if value >= thr else MonitorState.OK
    if op == "==":
        return MonitorState.BREACH if value == thr else MonitorState.OK
    return MonitorState.OK


def run_liquid_monitors(ctx: Any) -> Dict[str, Any]:
    """
    Emit one status per asset for liquidation risk based on distance-to-liq (%).
    The monitors own the value + threshold resolution; engine just persists.
    """
    dl = ctx.dl
    positions = _open_positions(dl)
    now_iso = datetime.now(timezone.utc).isoformat()

    # group by asset
    by_asset: Dict[str, List[Dict[str, Any]]] = {}
    for d in positions:
        a = _asset(d)
        if not a:
            continue
        by_asset.setdefault(a, []).append(d)

    statuses: List[Dict[str, Any]] = []
    resolver = _ensure_resolver(ctx)
    for asset, items in by_asset.items():
        # pick the worst (smallest) distance % among open positions for that asset
        distances = [x for x in (_liquid_distance_pct(d) for d in items) if x is not None]
        value = min(distances) if distances else None
        thr_value, trace = resolver.liquid_threshold(asset)
        _register_trace(ctx, trace)
        op, thr_unit = "<=", "%"
        state = _state_from_comparator(op, value, thr_value)
        statuses.append({
            "label": f"{asset} – Liq",
            "state": state.value,
            "value": value,
            "unit": "%",
            "threshold": {"op": op, "value": thr_value, "unit": thr_unit},
            "ts": now_iso,
            "meta": {
                "asset": asset,
                "source": "liq",
                "limit_source": trace.source,
                "limit_layer": trace.layer,
                "limit_value": trace.value,
                "limit_evidence": trace.evidence,
            },
        })

    return {
        "source": "liquid",
        "statuses": statuses,
    }
