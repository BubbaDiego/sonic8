# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from backend.models.monitor_status import MonitorStatus, MonitorType, MonitorState


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def _open_positions(dl: Any) -> List[Dict[str, Any]]:
    pmgr = getattr(dl, "positions", None)
    if pmgr:
        for name in ("get_positions", "list", "get_all", "positions"):
            fn = getattr(pmgr, name, None)
            try:
                rows = fn() if callable(fn) else (fn if isinstance(fn, list) else None)
            except TypeError:
                try: rows = fn(None)
                except Exception: rows = None
            except Exception:
                rows = None
            if isinstance(rows, list) and rows:
                out=[]
                for r in rows:
                    d = r if isinstance(r, dict) else (getattr(r,"dict",lambda:{})() or getattr(r,"__dict__",{}) or {})
                    if _is_open(d):
                        out.append(d)
                return out
    # DB fallback
    try:
        cur = dl.db.get_cursor()
        cur.execute("SELECT * FROM positions")
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols,row)) for row in cur.fetchall()]
        return [d for d in rows if _is_open(d)]
    except Exception:
        return []


def _is_open(d: Dict[str, Any]) -> bool:
    st = (d.get("status") or "").lower()
    if st in {"closed", "settled", "exited", "liquidated"}:
        return False
    if isinstance(d.get("is_open"), bool):
        return d["is_open"]
    for k in ("closed","closed_at","exit_ts","exit_price"):
        if d.get(k) not in (None,"",0):
            return False
    return True


def _asset(d: Dict[str, Any]) -> str:
    return str(d.get("asset_type") or d.get("asset") or d.get("symbol") or d.get("token") or "").upper()


def _sum_portfolio_pnl(rows: List[Dict[str, Any]]) -> float:
    s=0.0
    for d in rows:
        s += _safe_float(d.get("pnl_after_fees_usd") or d.get("pnl_usd") or d.get("pnl") or 0.0)
    return s


def _sum_single_pnl(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    by = defaultdict(float)
    for d in rows:
        by[_asset(d)] += _safe_float(d.get("pnl_after_fees_usd") or d.get("pnl_usd") or d.get("pnl") or 0.0)
    return dict(by)


def _resolve_threshold_portfolio(dl: Any) -> Tuple[str, float, str]:
    # system var: thresholds.profit.portfolio_usd (default $40)
    sys = getattr(dl, "system", None)
    if sys and hasattr(sys, "get_var"):
        try:
            v = sys.get_var("thresholds.profit.portfolio_usd")
            if v is not None:
                return (">=", float(v), "$")
        except Exception:
            pass
    return (">=", 40.0, "$")


def _resolve_threshold_single(dl: Any, asset: str) -> Tuple[str, float, str]:
    # thresholds.profit.single_usd or thresholds.profit.<ASSET>_usd
    sys = getattr(dl, "system", None)
    if sys and hasattr(sys, "get_var"):
        try:
            v = sys.get_var(f"thresholds.profit.{asset}_usd")
            if v is not None:
                return (">=", float(v), "$")
        except Exception:
            pass
        try:
            v = sys.get_var("thresholds.profit.single_usd")
            if v is not None:
                return (">=", float(v), "$")
        except Exception:
            pass
    return (">=", 10.0, "$")


def _state_from_comparator(op: str, value: float, thr: float) -> MonitorState:
    if op == ">":
        return MonitorState.OK if value > thr else MonitorState.WARN
    if op == ">=":
        return MonitorState.OK if value >= thr else MonitorState.WARN
    if op == "<":
        return MonitorState.OK if value < thr else MonitorState.WARN
    if op == "<=":
        return MonitorState.OK if value <= thr else MonitorState.WARN
    if op == "==":
        return MonitorState.OK if value == thr else MonitorState.WARN
    return MonitorState.OK


def run_profit_monitors(ctx: Any) -> Dict[str, Any]:
    """
    Emit statuses for portfolio PnL (USD) and each asset's PnL (USD).
    Value/unit/threshold are resolved here; engine just persists.
    """
    dl = ctx.dl
    now_iso = datetime.now(timezone.utc).isoformat()
    pos = _open_positions(dl)

    # Portfolio
    port_pnl = _sum_portfolio_pnl(pos)
    op_p, thr_p, unit_p = _resolve_threshold_portfolio(dl)
    state_p = _state_from_comparator(op_p, port_pnl, thr_p)
    statuses: List[Dict[str, Any]] = [{
        "label": "Portfolio PnL",
        "state": state_p.value,
        "value": port_pnl,
        "unit": unit_p,
        "threshold": {"op": op_p, "value": thr_p, "unit": unit_p},
        "ts": now_iso,
        "meta": {"scope": "portfolio", "source": "profit"},
    }]

    # Singles
    singles = _sum_single_pnl(pos)  # asset -> pnl
    for asset, pnl in sorted(singles.items(), key=lambda kv: abs(kv[1]), reverse=True):
        op_s, thr_s, unit_s = _resolve_threshold_single(dl, asset)
        state_s = _state_from_comparator(op_s, pnl, thr_s)
        statuses.append({
            "label": f"{asset} PnL",
            "state": state_s.value,
            "value": pnl,
            "unit": unit_s,
            "threshold": {"op": op_s, "value": thr_s, "unit": unit_s},
            "ts": now_iso,
            "meta": {"asset": asset, "source": "profit"},
        })

    return {
        "source": "profit",
        "statuses": statuses,
    }
