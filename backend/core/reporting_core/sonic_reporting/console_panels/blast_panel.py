from __future__ import annotations

from typing import Any, Dict, List, Optional

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
)

PANEL_SLUG = "blast"
PANEL_NAME = "Blast Radius"


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
    Build a thin bar using the same base glyph as the Risk Snapshot bar.

    enc_pct: 0..100 = how much of the blast radius has been encroached.
    slots:   number of block characters in the bar.

    We use '▰' for the encroached portion and '▱' for the remaining safety
    portion. No emoji, no wrapping.
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

    filled_char = "▰"  # same icon style as Risk
    empty_char = "▱"

    bar = filled_char * filled + empty_char * (total - filled)
    return f"OUT {bar} IN"


# ───────────────────────── render / connector ─────────────────────────


def render(context: Any, width: Optional[int] = None) -> List[str]:
    """
    Render the Blast Radius panel as a Sonic-style panel with title + body.

    Columns:

        🧨 Asset   🎯 Enc%   🎚 Alert%   💧 LDist   🧱 BR   🌪 Travel%   📊 State   Blast Meter
    """
    body_cfg = get_panel_body_config(PANEL_SLUG)
    lines: List[str] = []

    # Panel title rail (same pattern as Risk Snapshot, Market Alerts, etc.)
    lines += emit_title_block(PANEL_SLUG, PANEL_NAME)

    dl = (context or {}).get("dl")
    rows = _get_monitor_rows(dl)
    latest = _latest_by_asset(rows)

    body_lines: List[str] = []
    if not latest:
        body_lines.append("[blast] no blast radius data")
    else:
        header = (
            f"{'🧨 Asset':14} {'🎯 Enc%':>9} {'🎚 Alert%':>10} "
            f"{'💧 LDist':>10} {'🧱 BR':>8} {'🌪 Travel%':>11} {'📊 State':>9}  Blast Meter"
        )
        body_lines.append(header)

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
            body_lines.append(line)

    # Apply body theming (indent + color) in the same way as other panels.
    for raw in body_lines:
        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain(raw, body_cfg.get("body_text_color", "default"))],
        )

    lines += body_pad_below(PANEL_SLUG)
    return lines


def connector(
    dl: Any = None,
    ctx: Optional[Dict[str, Any]] = None,
    width: Optional[int] = None,
) -> List[str]:
    """
    console_reporter prefers connector(dl, ctx, width); delegate into render().
    """
    context: Dict[str, Any] = dict(ctx or {})
    if dl is not None:
        context.setdefault("dl", dl)
    if width is not None:
        context.setdefault("width", width)
    return render(context, width=width)
