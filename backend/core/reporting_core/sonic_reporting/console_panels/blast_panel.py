from __future__ import annotations

from typing import Any, Dict, List


# ───────────────────────── helpers ─────────────────────────


def _get_monitor_rows(dl: Any) -> List[Dict[str, Any]]:
    """
    Extract raw monitor rows from the DataLocker.

    Mirrors the pattern used by other panels: prefer dl.monitors.rows,
    but fall back to dl.monitors.latest()/to_row() when necessary.
    """
    if dl is None or not hasattr(dl, "monitors"):
        return []

    rows = getattr(dl.monitors, "rows", None)
    if rows is None:
        latest = getattr(dl.monitors, "latest", None)
        if callable(latest):
            try:
                rows = latest()
            except Exception:
                rows = None

    if rows is None:
        return []

    out: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
        else:
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
    A row belongs to the Blast monitor if:
      • monitor == 'blast' (case-insensitive), or
      • source  == 'blast' (case-insensitive).
    """
    mon = str(row.get("monitor") or "").strip().lower()
    src = str(row.get("source") or "").strip().lower()
    return mon == "blast" or src == "blast"


def _latest_by_asset(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Reduce a list of Blast rows to the last row per asset symbol.
    """
    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not _is_blast_row(row):
            continue
        asset = (row.get("asset") or row.get("label") or "-").strip().upper()
        latest[asset] = row
    return latest


def _fmt_float(val: Any, places: int = 2, suffix: str = "") -> str:
    if val is None or val == "":
        return "-"
    try:
        f = float(val)
    except Exception:
        return "-"
    fmt = f"{{:.{places}f}}"
    text = fmt.format(f)
    return text + suffix


def _color_state(state: str) -> str:
    s = (state or "").upper()
    if s == "BREACH":
        return f"[bold red]{s}[/bold red]"
    if s == "WARN":
        return f"[bold yellow]{s}[/bold yellow]"
    if s == "OK":
        return f"[bold green]{s}[/bold green]"
    return s or "-"


def _build_meter(enc_pct: float, alert_pct: float, state: str, slots: int = 24) -> str:
    """
    Build a 0–100% bar showing encroached% vs alert%.

    We fill from left to right with blocks up to enc_pct, dashed beyond that,
    and mark the alert threshold with "|" inside the bar.

    Bar color:
      • green  when enc < alert
      • yellow when enc is close to alert (within 10%)
      • red    when enc >= alert
    """
    try:
        enc = float(enc_pct)
    except Exception:
        enc = 0.0
    try:
        thr = float(alert_pct)
    except Exception:
        thr = 0.0

    enc = max(0.0, min(100.0, enc))
    thr = max(0.0, min(100.0, thr))

    total = max(8, int(slots))
    filled_slots = int(round((enc / 100.0) * total))

    # choose bar color based on where we are vs alert
    if enc >= thr:
        color_tag = "bold red"
    elif enc >= max(0.0, thr - 10.0):
        color_tag = "bold yellow"
    else:
        color_tag = "bold green"

    bar_chars: List[str] = []
    for i in range(total):
        if i < filled_slots:
            bar_chars.append("█")
        else:
            bar_chars.append("░")

    if thr > 0:
        marker_index = int(round((thr / 100.0) * total))
        if marker_index < 0:
            marker_index = 0
        if marker_index >= total:
            marker_index = total - 1
        bar_chars[marker_index] = "|"

    bar = "".join(bar_chars)
    return f"[{color_tag}][{bar}][/{color_tag}]"


# ───────────────────────── render ─────────────────────────


def render(ctx: Dict[str, Any], width: int = 92) -> List[str]:
    """
    Render the Blast Radius panel using a table + per-row gauge bar.

    Columns:

        Asset  Enc%  Alert%  LDist  BR   Travel%  State  Meter
    """
    dl = (ctx or {}).get("dl")
    rows = _get_monitor_rows(dl)

    latest = _latest_by_asset(rows)
    if not latest:
        return ["[blast] no blast radius data"]

    # Header styled similarly to other panels: bold cyan labels.
    header = (
        f"[bold cyan]{'Asset':10} {'Enc%':>7} {'Alert%':>7} "
        f"{'LDist':>8} {'BR':>8} {'Travel%':>9} {'State':>8}  Meter[/bold cyan]"
    )
    sep = "[cyan]" + ("─" * (len("Asset") + len("Enc%") + len("Alert%") +
                              len("LDist") + len("BR") + len("Travel%") +
                              len("State") + 26)) + "[/cyan]"

    lines: List[str] = []
    lines.append(header)
    lines.append(sep)

    # Sort assets for stable output
    for asset in sorted(latest.keys()):
        row = latest[asset]
        meta = row.get("meta") or {}

        # encroached% / alert% are stored as value/threshold by design,
        # but we also support meta.encroached_pct / meta.alert_pct as a fallback.
        enc_val = row.get("value", meta.get("encroached_pct"))
        alert_val = row.get("threshold", meta.get("alert_pct"))

        ld = meta.get("liq_distance")
        br = meta.get("blast_radius")
        travel = meta.get("travel_pct")

        state_raw = str(row.get("state") or "").upper() or "-"
        state_colored = _color_state(state_raw)

        enc_str = _fmt_float(enc_val, places=2, suffix="%")
        alert_str = _fmt_float(alert_val, places=2, suffix="%")
        ld_str = _fmt_float(ld, places=2)
        br_str = _fmt_float(br, places=2)
        travel_str = _fmt_float(travel, places=2, suffix="%")

        try:
            enc_float = float(enc_val) if enc_val is not None else 0.0
        except Exception:
            enc_float = 0.0
        try:
            alert_float = float(alert_val) if alert_val is not None else 0.0
        except Exception:
            alert_float = 0.0

        meter = _build_meter(enc_float, alert_float, state_raw, slots=24)

        line = (
            f"{asset:10} {enc_str:>7} {alert_str:>7} "
            f"{ld_str:>8} {br_str:>8} {travel_str:>9} {state_colored:>8}  {meter}"
        )
        lines.append(line)

    return lines
