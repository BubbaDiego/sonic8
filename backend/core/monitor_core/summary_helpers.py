from __future__ import annotations

from typing import Any, Dict, List, Optional

# This module is intentionally tolerant. If a value is missing,
# we return empty detail so the console shows ✓ for that monitor.


def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace("%", "")
        return float(s) if s else None
    except Exception:
        return None


def load_monitor_config_snapshot(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort, read-only snapshot of thresholds for rendering purposes.
    Pull from places the current run already knows (summary/prior config),
    since we don't want to reach into DB here.
    """
    cfg = {}

    # Profit thresholds (percent-like numbers the consumer uses).
    # Accept any shape present in summary -> sources/settings -> profit.
    profit_src = (summary.get("sources") or {}).get("profit") or {}
    pos = _as_float(profit_src.get("pos"))
    pf = _as_float(profit_src.get("pf"))

    # If sources were empty, probe a few known summary spots
    if pos is None or pf is None:
        prof_cfg = (summary.get("profit") or {}).get("settings") or {}
        pos = _as_float(prof_cfg.get("pos")) if pos is None else pos
        pf = _as_float(prof_cfg.get("pf")) if pf is None else pf

    cfg["profit"] = {"pos": pos, "pf": pf}

    # Liquid thresholds (per-asset). Try sources first, then settings, then summary.liquid.thresholds
    liquid_src = (summary.get("sources") or {}).get("liquid") or {}
    btc_thr = _as_float(liquid_src.get("btc"))
    eth_thr = _as_float(liquid_src.get("eth"))
    sol_thr = _as_float(liquid_src.get("sol"))

    if btc_thr is None or eth_thr is None or sol_thr is None:
        liq_cfg = (summary.get("liquid") or {}).get("settings") or {}
        thr_map = (
            liq_cfg.get("thresholds")
            or (summary.get("liquid") or {}).get("thresholds")
            or {}
        )
        btc_thr = _as_float(thr_map.get("BTC")) if btc_thr is None else btc_thr
        eth_thr = _as_float(thr_map.get("ETH")) if eth_thr is None else eth_thr
        sol_thr = _as_float(thr_map.get("SOL")) if sol_thr is None else sol_thr

    cfg["liquid"] = {"BTC": btc_thr, "ETH": eth_thr, "SOL": sol_thr}
    return cfg


def build_sources_snapshot(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a minimal 'sources' bag the console can print.
    """
    profit = cfg.get("profit") or {}
    liquid = cfg.get("liquid") or {}
    return {
        "profit": {"pos": profit.get("pos"), "pf": profit.get("pf")},
        "liquid": {
            "btc": liquid.get("BTC"),
            "eth": liquid.get("ETH"),
            "sol": liquid.get("SOL"),
        },
    }


def build_alerts_detail(
    summary: Dict[str, Any], cfg: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build per-monitor detail lines for the console.
    The consumer/monitors may already place detail into summary; if present we keep it.
    Otherwise we synthesize minimal rows when we have enough information.
    """
    alerts = summary.get("alerts") or {}
    detail = alerts.get("detail")
    if isinstance(detail, dict):
        # Respect existing detail provided by monitors; do not overwrite.
        return detail

    out: Dict[str, List[Dict[str, Any]]] = {}
    # Try to synthesize a minimal Profit row if we have current and threshold.
    prof_cur = (summary.get("profit") or {}).get("metrics") or {}
    pf_val = _as_float(prof_cur.get("pf_current"))
    pos_val = _as_float(prof_cur.get("pos_current"))
    pf_thr = _as_float((cfg.get("profit") or {}).get("pf"))
    pos_thr = _as_float((cfg.get("profit") or {}).get("pos"))
    rows: List[Dict[str, Any]] = []
    if pf_val is not None and pf_thr is not None:
        rows.append(
            {
                "metric": "pf",
                "value": pf_val,
                "threshold": pf_thr,
                "severity": "breach" if pf_val >= pf_thr else "ok",
            }
        )
    if pos_val is not None and pos_thr is not None:
        rows.append(
            {
                "metric": "pos",
                "value": pos_val,
                "threshold": pos_thr,
                "severity": "breach" if pos_val >= pos_thr else "ok",
            }
        )
    if rows:
        out["profit"] = rows

    # Liquid: look for per-asset distances in summary, otherwise skip.
    liq_cur = (summary.get("liquid") or {}).get("assets") or {}
    # assets shape expected: {"BTC": {"distance": 8.7}, ...}
    liq_cfg = cfg.get("liquid") or {}
    lrows: List[Dict[str, Any]] = []
    for asset in ("BTC", "ETH", "SOL"):
        cur = liq_cur.get(asset) or {}
        dist = _as_float(cur.get("distance"))
        thr = _as_float(liq_cfg.get(asset))
        if dist is None or thr is None:
            continue
        sev = "breach" if dist <= thr else "ok"  # closer is worse
        lrows.append(
            {
                "asset": asset,
                "distance": dist,
                "threshold": thr,
                "severity": sev,
            }
        )
    if lrows:
        out["liquid"] = lrows

    return out
