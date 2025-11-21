# -*- coding: utf-8 -*-
"""Market Alerts panel – Rich-powered table with configurable style."""
from __future__ import annotations

import json
from datetime import datetime
from io import StringIO
from typing import Any, Dict, Iterable, List, Mapping, Optional

from rich.console import Console
from rich.table import Table
from rich import box

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
)

try:
    # Used to bound the table width consistently with other panels
    from .theming import HR_WIDTH
except Exception:  # fallback
    HR_WIDTH = 100

PANEL_SLUG = "market"
PANEL_NAME = "Market Alerts"


# ───────────────────────── DL + monitor rows ──────────────────────────


def _resolve_dl(ctx: Any) -> Any:
    if ctx is None:
        return None
    if isinstance(ctx, dict):
        dl = ctx.get("dl")
        if dl is not None:
            return dl
    return getattr(ctx, "dl", None)


def _get_monitor_rows(dl: Any) -> List[Dict[str, Any]]:
    """
    Robustly pull monitor rows from dl.monitors / dl_dl_monitors.

    This mirrors the original working logic – don't change behavior here.
    """
    if dl is None:
        return []
    mgr = getattr(dl, "monitors", None) or getattr(dl, "dl_monitors", None)
    if mgr is None:
        return []

    candidates: Iterable[Any] = []
    for name in (
        "select_all",
        "list_all",
        "all",
        "latest",
        "list_latest",
        "latest_rows",
        "get_latest",
    ):
        fn = getattr(mgr, name, None)
        if callable(fn):
            try:
                data = fn()
            except TypeError:
                continue
            if data:
                candidates = data
                break
    else:
        direct = getattr(mgr, "rows", None)
        if direct:
            candidates = direct

    rows: List[Dict[str, Any]] = []
    for row in candidates:
        if isinstance(row, dict):
            rows.append(dict(row))
            continue
        norm: Dict[str, Any] = {}
        for key in (
            "monitor",
            "label",
            "state",
            "value",
            "unit",
            "thr_op",
            "thr_value",
            "thr_unit",
            "source",
            "meta",
        ):
            if hasattr(row, key):
                norm[key] = getattr(row, key)
        rows.append(norm)
    return rows


def _normalize_meta(meta: Any) -> Dict[str, Any]:
    if isinstance(meta, dict):
        return dict(meta)
    if isinstance(meta, str):
        try:
            data = json.loads(meta)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _market_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        monitor = (row.get("monitor") or "").lower()
        if monitor != "market":
            continue
        row = dict(row)
        row["meta"] = _normalize_meta(row.get("meta"))
        out.append(row)
    return out


# ───────────────────────── formatting helpers ─────────────────────────


def _fmt_price(val: Any) -> str:
    if val is None:
        return "–"
    try:
        return f"{float(val):.2f}"
    except Exception:
        return str(val)


def _fmt_move_abs(val: Any) -> str:
    """Signed absolute move in price units."""
    if val is None:
        return "–"
    try:
        v = float(val)
        sign = "+" if v >= 0 else "-"
        return f"{sign}{abs(v):.2f}"
    except Exception:
        return str(val)


def _fmt_pct(val: Any) -> str:
    if val is None:
        return "–"
    try:
        v = float(val)
        sign = "+" if v >= 0 else "-"
        return f"{sign}{abs(v):.2f}%"
    except Exception:
        return str(val)


def _fmt_threshold(meta: Dict[str, Any], thr_value: Any) -> str:
    # Prefer explicit description if present
    desc = meta.get("threshold_desc") or meta.get("desc")
    if isinstance(desc, str) and desc.strip():
        return desc.strip()

    if thr_value is None:
        return "–"

    try:
        v = float(thr_value)
        return f"${v:.2f} move"
    except Exception:
        return str(thr_value)


def _fmt_bar(meta: Dict[str, Any]) -> str:
    try:
        prox = float(meta.get("proximity") or 0.0)
    except Exception:
        prox = 0.0
    prox = max(0.0, min(prox, 1.0))
    filled = int(round(prox * 10))
    filled = max(0, min(filled, 10))
    return "▰" * filled + "▱" * (10 - filled)


def _asset_from_row(row: Dict[str, Any]) -> str:
    meta = row.get("meta") or {}
    asset = row.get("asset") or meta.get("asset") or row.get("label") or ""
    asset = str(asset).strip()
    return asset or "—"


def _entry_price(meta: Dict[str, Any]) -> Any:
    """
    Entry (anchor) price:

    We trust Market Core to give us an explicit anchor from PriceAlert:
      • meta["anchor_price"]        (current anchor)
      • meta["original_anchor_price"] as fallback
    """
    anchor = meta.get("anchor_price")
    if anchor is not None:
        return anchor
    origin = meta.get("original_anchor_price")
    if origin is not None:
        return origin
    return None


def _current_price(meta: Dict[str, Any]) -> Any:
    return meta.get("price") or meta.get("current_price")


def _move_abs_value(meta: Dict[str, Any]) -> Any:
    mv = meta.get("move_abs")
    if mv is not None:
        return mv
    price = _current_price(meta)
    anchor = _entry_price(meta)
    try:
        if price is not None and anchor not in (None, 0):
            return float(price) - float(anchor)
    except Exception:
        pass
    return None


def _move_pct_value(meta: Dict[str, Any]) -> Any:
    mv = meta.get("move_pct")
    if mv is not None:
        return mv
    price = _current_price(meta)
    anchor = _entry_price(meta)
    try:
        if price is not None and anchor not in (None, 0):
            return (float(price) - float(anchor)) / float(anchor) * 100.0
    except Exception:
        pass
    return None


def _fmt_move_value(meta: Dict[str, Any]) -> str:
    """
    Generic 'Move' column:

    - If rule_type is percent (e.g. move_pct), show percent.
    - Otherwise, show dollar move.
    """
    rule_type = (meta.get("rule_type") or "").lower()
    if "pct" in rule_type:
        return _fmt_pct(_move_pct_value(meta))
    return _fmt_move_abs(_move_abs_value(meta))


def _format_state_badge(state: str, alert_fired: bool) -> str:
    """
    Render a state cell like:

        🟢 OK
        🔴 BREACH ★
        🟡 RE-ANCHOR
        🟣 COOLDOWN

    If alert_fired=True, append a ★.
    """
    s = (state or "").upper().strip()
    if s in ("BREACH", "ALERT"):
        badge = "🔴 BREACH"
    elif s in ("REANCHOR", "RE-ANCHOR", "ANCHOR"):
        badge = "🟡 RE-ANCHOR"
    elif s in ("COOLDOWN", "COOL", "MUTED"):
        badge = "🟣 COOLDOWN"
    else:
        badge = "🟢 OK"

    if alert_fired:
        badge += " ★"
    return badge


def _fmt_short_time(ts: Optional[float]) -> str:
    """
    Short local time like '7:32pm' for event timestamps.
    """
    if not ts:
        return ""
    try:
        dt = datetime.fromtimestamp(float(ts))
        t = dt.strftime("%I:%M%p").lstrip("0").lower()
        return t
    except Exception:
        return ""


def _get_field(row: Mapping[str, Any], key: str) -> Any:
    if key in row:
        return row.get(key)
    meta = row.get("meta") if isinstance(row.get("meta"), Mapping) else None
    if meta and key in meta:
        return meta.get(key)
    return None


def _build_last_event_label(row: Mapping[str, Any]) -> str:
    """
    Build the 'Last' column text for a single market alert row.

    Expected fields on row (best-effort, all optional):
      - last_event_type: 'anchor' | 'breach' | 'recover' | None
      - last_event_ts:   epoch seconds
      - last_anchor_ts:  epoch seconds
      - last_breach_ts:  epoch seconds
      - alerts_window_count: int
      - alerts_window_seconds: int
      - move_abs: float (absolute move at last event)
      - threshold_abs: float (absolute threshold)

    Codex should map these to whatever existing names make sense in the
    actual snapshot structure.
    """
    etype = str(_get_field(row, "last_event_type") or "").lower().strip()
    ev_ts = _get_field(row, "last_event_ts")
    anchor_ts = _get_field(row, "last_anchor_ts")
    breach_ts = _get_field(row, "last_breach_ts")

    alerts_count = _get_field(row, "alerts_window_count") or 0
    window_s = _get_field(row, "alerts_window_seconds") or 600

    move_abs = _get_field(row, "last_event_move_abs") or _get_field(row, "move_abs")
    thr_abs = _get_field(row, "last_event_threshold") or _get_field(row, "threshold_abs")

    # Normalize
    try:
        alerts_count = int(alerts_count)
    except Exception:
        alerts_count = 0
    try:
        window_s = int(window_s)
    except Exception:
        window_s = 600

    window_min = max(1, window_s // 60)

    # If we have no useful history, fall back to a simple label.
    if not etype and not ev_ts and alerts_count == 0:
        return "no recent events"

    if etype == "anchor" or (not etype and anchor_ts and not breach_ts):
        ts_label = _fmt_short_time(anchor_ts or ev_ts)
        if not ts_label:
            return f"Anchored (alerts: {alerts_count}/{window_min}m)"
        return f"Anchored @ {ts_label} (alerts: {alerts_count}/{window_min}m)"

    if etype == "breach" or (breach_ts and (not etype or etype == "alert")):
        ts_label = _fmt_short_time(breach_ts or ev_ts)
        parts = ["BREACH"]
        if move_abs is not None and thr_abs is not None:
            try:
                parts.append(f"{float(move_abs):+.2f} vs {float(thr_abs):.2f}")
            except Exception:
                pass
        if ts_label:
            parts.append(f"@ {ts_label}")
        parts.append(f"(alerts: {alerts_count}/{window_min}m)")
        return " ".join(parts)

    if etype == "recover":
        ts_label = _fmt_short_time(ev_ts)
        base = f"Recovered within band @ {ts_label}" if ts_label else "Recovered within band"
        if breach_ts:
            last_breach_label = _fmt_short_time(breach_ts)
            if last_breach_label:
                base += f" (last breach {last_breach_label}, {alerts_count}/{window_min}m)"
        return base

    # Default catch-all
    ts_label = _fmt_short_time(ev_ts)
    if ts_label:
        return f"{etype or 'event'} @ {ts_label} (alerts: {alerts_count}/{window_min}m)"
    return f"{etype or 'event'} (alerts: {alerts_count}/{window_min}m)"


# ───────────────────────── table config helpers ───────────────────────


def _resolve_table_cfg(body_cfg: Dict[str, Any]) -> Dict[str, Any]:
    raw = body_cfg.get("table") or {}
    if not isinstance(raw, dict):
        raw = {}
    style = (raw.get("style") or "invisible").lower()
    table_justify = (raw.get("table_justify") or "left").lower()
    header_justify = (raw.get("header_justify") or "left").lower()
    return {
        "style": style,
        "table_justify": table_justify,
        "header_justify": header_justify,
    }


def _style_to_box(style: str) -> (Any, bool):
    """Map table_style  → (rich.box, show_lines)."""
    style = (style or "invisible").lower()
    if style == "thin":
        return box.SIMPLE_HEAD, False
    if style == "thick":
        return box.HEAVY_HEAD, True
    # invisible / default
    return None, False


def _justify_lines(lines: List[str], justify: str, width: int) -> List[str]:
    """Apply table-level justification to already-rendered lines."""
    justify = (justify or "left").lower()
    if justify not in ("center", "right"):
        return lines
    if not lines:
        return lines

    out: List[str] = []
    for line in lines:
        s = line.rstrip("\n")
        pad = width - len(s)
        if pad <= 0:
            out.append(s)
        else:
            if justify == "center":
                left = pad // 2
            else:  # right
                left = pad
            out.append(" " * left + s)
    return out


# ───────────────────────── Rich table builder ─────────────────────────


def _build_rich_table(rows: List[Dict[str, Any]], table_cfg: Dict[str, Any]) -> List[str]:
    """
    Build a real Rich Table and export it as plain text lines.
    """
    box_style, show_lines = _style_to_box(table_cfg.get("style"))

    table = Table(
        show_header=True,
        header_style="",   # we colorize via color_if_plain
        show_lines=show_lines,
        box=box_style,
        show_edge=False,   # hide outer left/right borders
        pad_edge=False,
        expand=False,
    )

    # Headers with icons on the left of the labels; Rich handles wcwidth.
    table.add_column("🪙 Asset", justify="left", no_wrap=True)
    table.add_column("💵 Entry", justify="right")
    table.add_column("💹 Current", justify="right")
    table.add_column("📊 Move", justify="right")
    table.add_column("🎯 Thr", justify="left")
    table.add_column("🔋 Prox", justify="left", no_wrap=True)
    table.add_column("📶 State", justify="left")
    table.add_column("📝 Last", justify="left")

    for row in rows:
        meta = row.get("meta") or {}
        asset = _asset_from_row(row)
        entry = _fmt_price(_entry_price(meta))
        current = _fmt_price(_current_price(meta))
        move_str = _fmt_move_value(meta)
        thr_str = _fmt_threshold(meta, row.get("thr_value"))
        bar = _fmt_bar(meta)
        state = str(row.get("state") or "").upper()

        state_cell = _format_state_badge(state, bool(_get_field(row, "alert_fired_this_cycle")))
        last_cell = _build_last_event_label(row)

        table.add_row(
            asset,
            entry,
            current,
            move_str,
            thr_str,
            bar,
            state_cell,
            last_cell,
        )

    # IMPORTANT: render into a buffer, not to real stdout
    buf = StringIO()
    console = Console(record=True, width=HR_WIDTH, file=buf, force_terminal=True)
    console.print(table)

    text = console.export_text().rstrip("\n")
    lines = text.splitlines() if text else []

    # Apply  table-level justify at the string level
    lines = _justify_lines(lines, table_cfg.get("table_justify"), HR_WIDTH)
    return lines


# ───────────────────────── panel API ─────────────────────────


def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    dl = _resolve_dl(context)
    body_cfg = get_panel_body_config(PANEL_SLUG)
    table_cfg = _resolve_table_cfg(body_cfg)
    lines: List[str] = []

    # Title
    lines += emit_title_block(PANEL_SLUG, PANEL_NAME)

    if dl is None:
        note = color_if_plain(
            "  (no DataLocker context)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    rows = _market_rows(_get_monitor_rows(dl))

    if not rows:
        # Simple header line when there are no rows
        header = (
            "🪙 Asset   💵 Entry      💹 Current   📊 Move      🎯 Thr           🔋 Prox      📶 State   📝 Last"
        )
        header_colored = color_if_plain(
            "  " + header,
            body_cfg["column_header_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [header_colored])

        note = color_if_plain(
            "  (no active market alerts)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    # Build the Rich table and export as plain text lines
    table_lines = _build_rich_table(rows, table_cfg)

    # First line is header, color it with header color; others with body color
    if table_lines:
        header_line = table_lines[0]
        data_lines = table_lines[1:]
        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain(header_line, body_cfg["column_header_text_color"])],
        )
        for ln in data_lines:
            lines += body_indent_lines(
                PANEL_SLUG,
                [color_if_plain(ln, body_cfg["body_text_color"])],
            )
    else:
        note = color_if_plain(
            "  (no market data to display)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])

    lines += body_pad_below(PANEL_SLUG)
    return lines


def connector(
    dl: Any = None,
    ctx: Optional[Dict[str, Any]] = None,
    width: Optional[int] = None,
) -> List[str]:
    context: Dict[str, Any] = dict(ctx or {})
    if dl is not None:
        context.setdefault("dl", dl)
    return render(context, width=width)
