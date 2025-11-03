# -*- coding: utf-8 -*-
"""
Monitors summary (compact) with consistent left-side icons (same as Prices):
  🟡 BTC • 💧 Liquid
  🔷 ETH • 💧 Liquid
  🟣 SOL • 💧 Liquid

Prints a small list under the main Monitors table; does not replace it.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from backend.core.logging import log

ASSET_ICON = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}
METRIC_ICON = {"liquid": "💧", "profit": "💹"}


def _rows_from_csum(csum: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Try multiple shapes we’ve seen in Sonic. We only need value/threshold/breach + labels.
    """
    rows: List[Dict[str, Any]] = []

    # Preferred: table-shaped blocks from evaluations renderer
    for key in ("monitors", "monitor_results", "results"):
        sec = csum.get(key)
        if isinstance(sec, dict):
            tbl = sec.get("rows") or sec.get("items")
            if isinstance(tbl, list):
                for r in tbl:
                    if isinstance(r, dict):
                        rows.append(r)
                if rows:
                    return rows
        elif isinstance(sec, list):
            for r in sec:
                if isinstance(r, dict):
                    rows.append(r)
            if rows:
                return rows

    # Fallback: LiquidationMonitor summary (details with asset/distance/threshold/breach)
    det = csum.get("details")
    thrmap = csum.get("thresholds", {})
    if isinstance(det, list):
        for d in det:
            if not isinstance(d, dict):
                continue
            rows.append({
                "asset": (d.get("asset") or "—"),
                "metric": "Liquid",
                "value": d.get("distance"),
                "rule": "≤",
                "threshold": d.get("threshold") or (thrmap or {}).get(str(d.get("asset","")).upper()),
                "breach": bool(d.get("breach")),
                "source": "DB / FILE",
            })
    return rows


def _fmt_asset(asset: str | None) -> str:
    if not asset:
        return "◎"
    sym = ASSET_ICON.get(asset.upper(), "◎")
    return f"{sym} {asset.upper()}"


def _fmt_metric(metric: str | None) -> str:
    m = (metric or "Liquid").strip()
    lower = m.lower()
    icon = METRIC_ICON.get(lower, "🖥️")
    return f"{icon} {m}"


def _fmt_value(v: Any) -> str:
    try:
        if v is None:
            return "—"
        f = float(v)
        s = f"{f:.2f}".rstrip("0").rstrip(".")
        return s if s else "0"
    except Exception:
        return str(v) if v is not None else "—"


def _fmt_money(v: Any) -> str:
    try:
        if v is None:
            return "—"
        f = float(v)
        s = f"{f:,.2f}"
        return f"${s}"
    except Exception:
        return str(v) if v is not None else "—"


def _result_glyph(breach: bool, metric: str | None) -> str:
    if (metric or "").lower().startswith("liquid"):
        return "🔴 HIT" if breach else "🟢 OK"
    return "· not met" if not breach else "🟢 OK"


def render(dl, csum: Dict[str, Any], default_json_path: Optional[str] = None) -> None:
    rows = _rows_from_csum(csum)

    print("\n  ---------------------- 🧭  Monitors (summary)  ----------------------")
    if not rows:
        log.debug("Monitors summary: no rows extracted from csum", source="monitor_panel")
        print("  (no rows)")
        return

    print(f"      {'Metric':<22} {'Value':>8}  {'Rule':<2}  {'Threshold':>9}   {'Result':<9}  {'Source (V / T)'}")
    for r in rows:
        asset   = (r.get("asset") or "—")
        metric  = (r.get("metric") or "Liquid")
        value   = r.get("value")
        thr     = r.get("threshold")
        rule    = r.get("rule") or ("≥" if "profit" in metric.lower() else "≤")
        breach  = bool(r.get("breach"))
        source  = r.get("source") or "DB / FILE"

        # First cell (icons on the left), e.g. "🟡 BTC • 💧 Liquid"
        metric_cell = f"{_fmt_asset(asset)} • {_fmt_metric(metric)}"

        # Profit uses money format; Liquid uses number
        if "profit" in metric.lower():
            val_s = _fmt_money(value)
            thr_s = _fmt_money(thr)
        else:
            val_s = _fmt_value(value)
            thr_s = _fmt_value(thr)

        result = _result_glyph(breach, metric)

        print(f"      {metric_cell:<22} {val_s:>8}  {rule:<2}  {thr_s:>9}   {result:<9}  {source}")
