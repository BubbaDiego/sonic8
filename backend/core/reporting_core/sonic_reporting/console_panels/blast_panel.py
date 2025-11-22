from __future__ import annotations

from typing import Any, Dict, List


def _get_monitor_rows(dl: Any) -> List[Dict[str, Any]]:
    """
    Extract raw monitor rows from the DataLocker.

    This mirrors the pattern used by other panels (e.g. monitors_panel),
    relying on dl.monitors.rows when available.
    """
    if dl is None or not hasattr(dl, "monitors"):
        return []

    rows = getattr(dl.monitors, "rows", None)
    if rows is None:
        # Some environments expose a .latest() or similar; be defensive.
        latest = getattr(dl.monitors, "latest", None)
        if callable(latest):
            rows = latest()
    if rows is None:
        return []

    # Ensure it's a list of dict-ish objects.
    out: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
        else:
            # MonitorStatus and similar often expose .to_row()
            to_row = getattr(row, "to_row", None)
            if callable(to_row):
                try:
                    r = to_row()
                    if isinstance(r, dict):
                        out.append(r)
                except Exception:
                    continue
    return out


def _is_blast_row(row: Dict[str, Any]) -> bool:
    """
    Determine whether this monitor row belongs to the Blast monitor.

    We treat a row as Blast if:
      • monitor == 'blast' (case-insensitive), OR
      • source == 'blast' (case-insensitive).

    This matches the Monitors panel behavior you see in the screenshot,
    where the Blast row shows Source='blast'.
    """
    mon = str(row.get("monitor") or "").strip().lower()
    src = str(row.get("source") or "").strip().lower()
    if mon == "blast":
        return True
    if src == "blast":
        return True
    return False


def _latest_by_asset(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Reduce a list of Blast rows to the last row per asset symbol.

    We don't depend on timestamps here; we assume the rows are in
    insertion order (latest last), which is how the monitor engine
    appends them.
    """
    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not _is_blast_row(row):
            continue
        asset = (row.get("asset") or row.get("label") or "-").strip().upper()
        latest[asset] = row
    return latest


def _fmt_float(val: Any, places: int = 2) -> str:
    try:
        f = float(val)
    except Exception:
        return "-"
    fmt = f"{{:.{places}f}}"
    return fmt.format(f)


def render(ctx: Dict[str, Any], width: int = 92) -> List[str]:
    """
    Render the Blast Radius panel as a list of text lines.

    Columns:
      Asset   Enc%   Alert%   LDist   BR     Travel%   State
    """
    dl = (ctx or {}).get("dl")
    rows = _get_monitor_rows(dl)

    blast_rows = _latest_by_asset(rows)
    if not blast_rows:
        return ["[blast] no blast radius data"]

    # Header
    header = f"{'Asset':6} {'Enc%':>7} {'Alert%':>7} {'LDist':>8} {'BR':>8} {'Travel%':>9} {'State':>8}"
    sep = "-" * len(header)
    lines: List[str] = [header, sep]

    # Sort assets for stable output
    for asset in sorted(blast_rows.keys()):
        row = blast_rows[asset]
        meta = row.get("meta") or {}

        # value/threshold are treated as encroached% and alert% by design
        enc = _fmt_float(row.get("value"))
        thr = _fmt_float(row.get("threshold"))

        ld = _fmt_float(meta.get("liq_distance"))
        br = _fmt_float(meta.get("blast_radius"))
        travel = _fmt_float(meta.get("travel_pct"))
        state = str(row.get("state") or "").upper() or "-"

        lines.append(
            f"{asset:6} {enc:>7} {thr:>7} {ld:>8} {br:>8} {travel:>9} {state:>8}"
        )

    return lines
