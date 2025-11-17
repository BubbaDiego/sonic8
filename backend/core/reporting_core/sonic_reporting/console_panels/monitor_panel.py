# backend/core/reporting_core/sonic_reporting/console_panels/monitor_panel.py
from __future__ import annotations

import logging
from io import StringIO
from typing import Any, Dict, Iterable, List, Mapping, Optional

from rich.console import Console
from rich.table import Table
from rich import box

from backend.core.reporting_core.sonic_reporting.console_panels import data_access
from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
    paint_line,
)

try:
    # Width hint for Rich export; theming already uses this
    from .theming import HR_WIDTH
except Exception:  # pragma: no cover
    HR_WIDTH = 100

log = logging.getLogger(__name__)

PANEL_SLUG = "monitors"
PANEL_NAME = "Monitors"

# Icons keyed by normalized monitor type (from dl_monitors rows["monitor"])
MON_ICON: Dict[str, str] = {
    "liquid": "💧",
    "liq": "💧",
    "profit": "💹",
    "market": "📈",
    "prices": "💵",
    "positions": "📊",
    "raydium": "🪙",
    "hedges": "🪶",
    "heart": "💓",
    "heartbeat": "💓",
    "xcom": "✉️",
    "custom": "🧪",
}


# ──────────────────────────────────────────────────────────────────────────────
# Data access helpers
# ──────────────────────────────────────────────────────────────────────────────


def _resolve_dl(context: Any) -> Any:
    """Tolerant resolver for DataLocker from context or global singleton."""
    try:
        return data_access.dl_or_context(context)
    except Exception:
        try:
            from backend.data.data_locker import DataLocker  # type: ignore

            return DataLocker.get_instance() if hasattr(DataLocker, "get_instance") else DataLocker()
        except Exception:
            return None


def _get_monitor_rows(context: Any) -> List[Mapping[str, Any]]:
    dl = _resolve_dl(context)
    if dl is None:
        return []

    try:
        mgr = getattr(dl, "monitors", None)
        if mgr is None:
            return []
        rows: Iterable[Mapping[str, Any]] = getattr(mgr, "rows", []) or []
        return list(rows)
    except Exception:
        log.exception("monitor_panel: failed to read monitors from DataLocker")
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Normalization & formatting
# ──────────────────────────────────────────────────────────────────────────────


def _normalized_rows(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize monitor rows into a small, stable schema for the panel."""
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            d = dict(r)
        except Exception:
            continue

        mon = str(d.get("monitor") or d.get("mon") or "").lower().strip()
        label = str(d.get("label") or d.get("name") or "").strip() or None
        value = d.get("value")
        state = str(d.get("state") or "").upper().strip() or "OK"
        source = str(d.get("source") or d.get("src") or "").strip() or "-"

        meta = d.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}

        # Prefer explicit threshold dict if present, otherwise reconstruct from thr_* fields.
        thresh = d.get("threshold")
        if thresh is None:
            thr_value = d.get("thr_value")
            thr_op = d.get("thr_op") or ""
            thr_unit = d.get("thr_unit") or ""
            if thr_value not in (None, ""):
                thresh = {
                    "op": thr_op,
                    "value": thr_value,
                    "unit": thr_unit,
                }

        out.append(
            {
                "monitor": mon,
                "label": label,
                "threshold": thresh,
                "value": value,
                "state": state,
                "source": source,
                "meta": meta,
                "thr_op": d.get("thr_op"),
                "thr_value": d.get("thr_value"),
                "thr_unit": d.get("thr_unit"),
            }
        )
    return out


def _asset_from_meta_or_label(row: Mapping[str, Any]) -> str:
    """Best-effort extraction of the asset symbol for the Asset column."""
    meta = row.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}

    # Prefer explicit asset-ish fields from meta first
    for key in ("asset", "asset_type", "symbol", "token", "base"):
        val = meta.get(key)
        if val:
            return str(val).upper()

    # Fallback: infer from label prefix (e.g. "SOL - Liq", "SOL PnL", "SOL")
    label = str(row.get("label") or "").strip()
    if label:
        first = label.split()[0]  # "SOL", "SOL-PnL", "Portfolio"
        if "-" in first:
            first = first.split("-")[0]
        first = first.strip("–-•").strip()
        if first:
            return first.upper()

    return "–"


def _fmt_monitor_name(row: Mapping[str, Any]) -> str:
    """Canonical monitor label (type-centric, not asset-centric)."""
    mon = str(row.get("monitor") or "").lower().strip()

    # Type-driven names for the main monitors
    if mon in {"liquid", "liq"}:
        return "💧 Liquidation"
    if mon == "prices" or mon == "price":
        # green dollar icon + label
        return "[green]💵[/] Price"
    if mon == "market":
        return "📊 Market"
    if mon == "profit":
        return "💹 Profit"

    # Fallback: original behavior (icon + label)
    label = str(row.get("label") or "").strip()
    base = label or (mon.title() if mon else "–")
    icon = MON_ICON.get(mon, "🧪")
    return f"{icon} {base}"


def _fmt_threshold(row: Mapping[str, Any]) -> str:
    t = row.get("threshold")
    if t is None or t == "":
        return "—"

    # Dict form: {"op": "<=", "value": 5.0, "unit": "%"}
    if isinstance(t, dict):
        op = str(t.get("op") or "").strip()
        val = t.get("value")
        unit = str(t.get("unit") or "").strip()

        if val in (None, ""):
            return "—"

        try:
            if isinstance(val, (int, float)):
                val_txt = f"{float(val):.2f}"
            else:
                val_txt = str(val)
        except Exception:
            val_txt = str(val)

        parts = [p for p in (op, val_txt, unit) if p]
        return " ".join(parts) if parts else "—"

    # Primitive numeric/string fallback
    try:
        if isinstance(t, (int, float)):
            return f"{float(t):.2f}"
        return str(t)
    except Exception:
        return str(t)


def _fmt_value(row: Mapping[str, Any]) -> str:
    v = row.get("value")
    if v is None or v == "":
        return "0"
    try:
        if isinstance(v, (int, float)):
            return f"{v:.2f}"
        return str(v)
    except Exception:
        return str(v)


def _fmt_state(row: Mapping[str, Any]) -> str:
    s = str(row.get("state") or "").upper()
    if s == "BREACH":
        return "[red]BREACH[/]"
    if s == "WARN":
        return "[yellow]WARN[/]"
    if s == "OK":
        return "[green]OK[/]"
    return s or "OK"


def _fmt_source(row: Mapping[str, Any]) -> str:
    meta = row.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}

    limit_src = str(meta.get("limit_source") or "").upper().strip()

    # If the limit was resolved via ConfigOracle (ResolutionTrace.source == "ORACLE"),
    # render a wizard icon and label.
    if limit_src == "ORACLE":
        return "🧙 Oracle"

    # Existing behavior for non-Oracle rows.
    src = str(row.get("source") or "").strip()
    return src or "-"


# ──────────────────────────────────────────────────────────────────────────────
# Rich table plumbing
# ──────────────────────────────────────────────────────────────────────────────


def _resolve_table_cfg(body_cfg: Dict[str, Any]) -> Dict[str, Any]:
    tcfg = (body_cfg or {}).get("table") or {}
    style = str(tcfg.get("style") or "invisible").lower().strip()
    table_justify = str(tcfg.get("table_justify") or "left").lower().strip()
    header_justify = str(tcfg.get("header_justify") or "left").lower().strip()
    return {
        "style": style,
        "table_justify": table_justify,
        "header_justify": header_justify,
    }


def _style_to_box(style: str):
    style = (style or "").lower()
    if style == "thin":
        return box.SIMPLE_HEAD, False
    if style == "thick":
        return box.HEAVY_HEAD, True
    # "invisible" or unknown → no borders
    return None, False


def _justify_lines(lines: List[str], justify: str, width: int) -> List[str]:
    justify = (justify or "left").lower()
    out: List[str] = []
    for line in lines:
        s = line.rstrip("\n")
        pad = max(0, width - len(s))
        if justify == "right":
            out.append(" " * pad + s)
        elif justify == "center":
            left = pad // 2
            out.append(" " * left + s)
        else:
            out.append(s)
    return out


def _build_rich_table(rows: List[Dict[str, Any]], body_cfg: Dict[str, Any]) -> List[str]:
    table_cfg = _resolve_table_cfg(body_cfg)
    box_style, show_lines = _style_to_box(table_cfg["style"])

    table = Table(
        show_header=True,
        header_style="",
        show_lines=show_lines,
        box=box_style,
        pad_edge=False,
        expand=False,
    )

    # Header labels with icons
    table.add_column("🔎 Monitor", justify="left", no_wrap=True)
    table.add_column("🪙 Asset", justify="left", no_wrap=True)
    table.add_column("🎯 Thresh", justify="left")
    table.add_column("📊 Value", justify="right")
    table.add_column("🧾 State", justify="left")
    table.add_column("📚 Source", justify="left")

    for r in rows:
        table.add_row(
            _fmt_monitor_name(r),
            _asset_from_meta_or_label(r),
            _fmt_threshold(r),
            _fmt_value(r),
            _fmt_state(r),
            _fmt_source(r),
        )

    buf = StringIO()
    console = Console(record=True, width=HR_WIDTH, file=buf, force_terminal=True)
    console.print(table)
    # IMPORTANT: keep styles so BREACH/WARN/OK (and green 💵) stay colored
    text = console.export_text(styles=True).rstrip("\n")
    if not text:
        return []
    raw_lines = text.splitlines()
    return _justify_lines(raw_lines, table_cfg["table_justify"], HR_WIDTH)


# ──────────────────────────────────────────────────────────────────────────────
# Public render entrypoint
# ──────────────────────────────────────────────────────────────────────────────


def render(context: Any, width: Optional[int] = None) -> List[str]:
    body_cfg = get_panel_body_config(PANEL_SLUG)
    title_block = emit_title_block(PANEL_SLUG, PANEL_NAME)

    rows_raw = _get_monitor_rows(context)
    rows = _normalized_rows(rows_raw)

    lines: List[str] = []
    lines.extend(title_block)

    if not rows:
        # Empty state: just headers + message
        header = "🔎 Monitor  🪙 Asset   🎯 Thresh   📊 Value   🧾 State   📚 Source"
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [
                    paint_line(header, body_cfg.get("column_header_text_color", "")),
                    "(no monitor data)",
                ],
            )
        )
        lines.extend(body_pad_below(PANEL_SLUG))
        return lines

    table_lines = _build_rich_table(rows, body_cfg)

    if table_lines:
        header_line = table_lines[0]
        data_lines = table_lines[1:]

        # Header explicitly tinted like other panels
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [paint_line(header_line, body_cfg.get("column_header_text_color", ""))],
            )
        )
        # Body uses normal body_text_color (and respects inline markup like [red])
        for ln in data_lines:
            lines.extend(
                body_indent_lines(
                    PANEL_SLUG,
                    [color_if_plain(ln, body_cfg.get("body_text_color", ""))],
                )
            )
    else:
        lines.extend(body_indent_lines(PANEL_SLUG, ["(no monitor data)"]))

    lines.extend(body_pad_below(PANEL_SLUG))
    return lines
