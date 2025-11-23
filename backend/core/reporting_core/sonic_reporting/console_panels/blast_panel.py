from __future__ import annotations

from typing import Any, Dict, List


# ───────────────────────── helpers ─────────────────────────


def _get_monitor_rows(dl: Any) -> List[Dict[str, Any]]:
    """
    Extract raw monitor rows from the DataLocker.

    Mirrors other panels: prefer dl.monitors.rows, but fall back to
    dl.monitors.latest()/to_row() when necessary.
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


def _build_meter(enc_pct: float, slots: int = 28) -> str:
    """
    Build a narrow continuous bar similar in spirit to the Risk Snapshot bar.

    enc_pct: 0..100 = how much of the blast radius has been encroached.
    slots:   number of block characters in the bar.

    We use a single block glyph ('▮') so the theme can color it like the
    rest of Sonic; no big emoji squares, no wrapping.

        OUT ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮ IN
    """
    try:
        enc = float(enc_pct)
    except Exception:
        enc = 0.0

    enc = max(0.0, min(100.0, enc))
    total = max(4, int(slots))

    filled = int(round((enc / 100.0) * total))
    if filled < 0:
        filled = 0
    if filled > total:
        filled = total

    bar = "▮" * filled + "▮" * (total - filled)
    # Labels echo the SHORT/LONG concept: outside vs inside blast
    return f"OUT {bar} IN"


# ───────────────────────── render ─────────────────────────


def render(ctx: Dict[str, Any], width: int = 92) -> List[str]:
    """
    Render the Blast Radius panel as a Sonic-style table + Blast Meter.

    Columns:

        🧨 Asset   🎯 Enc%   🎚 Alert%   💧 LDist   🧱 BR   🌪 Travel%   📊 State   Blast Meter
    """
    dl = (ctx or {}).get("dl")
    rows = _get_monitor_rows(dl)

    latest = _latest_by_asset(rows)
    if not latest:
        return ["[blast] no blast radius data"]

    # Header row with icons, same pattern as your other panels.
    header = (
        f"{'🧨 Asset':14} {'🎯 Enc%':>9} {'🎚 Alert%':>10} "
        f"{'💧 LDist':>10} {'🧱 BR':>8} {'🌪 Travel%':>11} {'📊 State':>9}  Blast Meter"
    )

    lines: List[str] = []
    lines.append(header)
    # NOTE: no dashed separator line here – you asked to remove it.

    # Sort assets for stable output (SOL - BLAST, BTC - BLAST, etc.)
    for asset in sorted(latest.keys()):
        row = latest[asset]
        meta = row.get("meta") or {}

        enc_val = row.get("value", meta.get("encroached_pct"))
        alert_val = row.get("threshold", meta.get("alert_pct"))

        ld = meta.get("liq_distance")
        br = meta.get("blast_radius")
        travel = meta.get("travel_pct")
        state = str(row.get("state") or "").upper() or "-"

        enc_str = _fmt_float(enc_val, places=2, suffix="%")
        alert_str = _fmt_float(alert_val, places=2, suffix="%")
        ld_str = _fmt_float(ld, places=2)
        br_str = _fmt_float(br, places=2)
        travel_str = _fmt_float(travel, places=2, suffix="%")

        try:
            enc_float = float(enc_val) if enc_val is not None else 0.0
        except Exception:
            enc_float = 0.0

        meter = _build_meter(enc_float, slots=28)

        line = (
            f"{asset:14} {enc_str:>9} {alert_str:>10} "
            f"{ld_str:>10} {br_str:>8} {travel_str:>11} {state:>9}  {meter}"
        )
        lines.append(line)

    return lines
