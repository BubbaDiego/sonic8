from __future__ import annotations
from typing import Any, Dict, List, Optional

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below, body_indent_lines,
    paint_line, color_if_plain,
)

from backend.core.monitor_core.resolver.threshold_resolver import ThresholdResolver

PANEL_SLUG = "preflight"
PANEL_NAME = "Pre-Flight Config"

# column widths
W_SYM = 6
W_KEY = 22
W_RES = 8
W_SRC = 28
W_JSON = 8
W_DB = 8
W_ENV = 8
W_DEF = 8

# color mapping for source tokens
_SRC_COLOR = {"JSON": "cyan", "DB": "yellow", "ENV": "magenta", "DEFAULT": "grey50"}

def _fmt(v: Any) -> str:
    try:
        f = float(v)
        return f"{f:.2f}"
    except Exception:
        return "-" if v in (None, "", {}) else str(v)

def _src_colored(src: str) -> str:
    return color_if_plain(src, _SRC_COLOR.get(src, "default"))

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []
    body = get_panel_body_config(PANEL_SLUG)

    cfg = context.get("cfg") or context.get("config") or {}
    dl = context.get("dl")
    res = ThresholdResolver(cfg, dl, cfg_path_hint=context.get("cfg_path_hint"))

    # title
    out += emit_title_block(PANEL_SLUG, PANEL_NAME)

    # config path line
    cfg_line = f"cfg: {res.cfg_path_hint or '<unknown>'}"
    out += body_indent_lines(PANEL_SLUG, [cfg_line, ""])

    # section: Liquid thresholds
    header_liq = (
        f"{'Sym':<{W_SYM}} "
        f"{'Resolved':>{W_RES}} "
        f"{'Source':<{W_SRC}} "
        f"{'JSON':>{W_JSON}} "
        f"{'DB':>{W_DB}} "
        f"{'ENV':>{W_ENV}} "
        f"{'Default':>{W_DEF}}"
    )
    out += body_indent_lines(PANEL_SLUG, [paint_line("Liquid thresholds", body["column_header_text_color"])])
    out += body_indent_lines(PANEL_SLUG, [paint_line(header_liq, body["column_header_text_color"])])

    syms = set(["BTC", "ETH", "SOL"])
    # include any extra symbols present in JSON
    lm = cfg.get("liquid_monitor", {}) if isinstance(cfg, dict) else {}
    lm_thr = (lm or {}).get("thresholds", {}) if isinstance(lm, dict) else {}
    if isinstance(lm_thr, dict):
        syms |= set(lm_thr.keys())

    for sym in sorted(syms):
        layers = res.inspect_liquid(sym)
        resolved, trace = res.liquid_threshold(sym)
        src_txt = trace.source or ""
        src_colored = _src_colored(src_txt) if src_txt else ""
        if trace.layer and src_colored:
            src_colored = f"{src_colored} · {trace.layer}"
        row = (
            f"{sym:<{W_SYM}} "
            f"{_fmt(resolved):>{W_RES}} "
            f"{src_colored:<{W_SRC}} "
            f"{_fmt(layers.get('json') if layers.get('json') is not None else layers.get('json_legacy')):>{W_JSON}} "
            f"{_fmt(layers.get('db')):>{W_DB}} "
            f"{_fmt(layers.get('env')):>{W_ENV}} "
            f"{_fmt(layers.get('default')):>{W_DEF}}"
        )
        out += body_indent_lines(PANEL_SLUG, [row])

    out += body_indent_lines(PANEL_SLUG, [""])

    # section: Profit monitor
    header_pr = (
        f"{'Key':<{W_KEY}} "
        f"{'Resolved':>{W_RES}} "
        f"{'Source':<{W_SRC}} "
        f"{'JSON':>{W_JSON}} "
        f"{'DB':>{W_DB}} "
        f"{'ENV':>{W_ENV}} "
        f"{'Default':>{W_DEF}}"
    )
    out += body_indent_lines(PANEL_SLUG, [paint_line("Profit monitor", body["column_header_text_color"])])
    out += body_indent_lines(PANEL_SLUG, [paint_line(header_pr, body["column_header_text_color"])])

    for key in ("position_profit_usd", "portfolio_profit_usd"):
        layers = res.inspect_profit(key)
        resolved, trace = res.profit_limit(key)
        src_txt = trace.source or ""
        src_colored = _src_colored(src_txt) if src_txt else ""
        if trace.layer and src_colored:
            src_colored = f"{src_colored} · {trace.layer}"
        row = (
            f"{key:<{W_KEY}} "
            f"{_fmt(resolved):>{W_RES}} "
            f"{src_colored:<{W_SRC}} "
            f"{_fmt(layers.get('json')):>{W_JSON}} "
            f"{_fmt(layers.get('db')):>{W_DB}} "
            f"{_fmt(layers.get('env')):>{W_ENV}} "
            f"{_fmt(layers.get('default')):>{W_DEF}}"
        )
        out += body_indent_lines(PANEL_SLUG, [row])

    out += body_pad_below(PANEL_SLUG)
    return out
