from __future__ import annotations
import json, os, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "console_width",
    "hr",
    "emit_title_block",
    "want_outer_hr",
    "get_panel_title_config",
    "title_lines",
    "get_panel_layout_config",
    "get_panel_body_config",
    "body_pad_above",
    "body_pad_below",
    "body_indent_lines",
    "color_if_plain",
    "paint_line",
    "get_panel_order",
    "is_panel_enabled",
    "is_enabled",
    "enabled_panel_slugs",
]

# ──────────────────────────────────────────────────────────────────────────────
# Width / rules
# ──────────────────────────────────────────────────────────────────────────────

def console_width(default: int = 92) -> int:
    try:
        return max(60, min(180, int(os.environ.get("SONIC_CONSOLE_WIDTH", default))))
    except Exception:
        return default

def hr(width: Optional[int] = None, ch: str = "─") -> str:
    W = width or console_width()
    return ch * W

# ──────────────────────────────────────────────────────────────────────────────
# ANSI color helpers
# ──────────────────────────────────────────────────────────────────────────────

_USE_COLOR = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0", "false", "no", "off"}
_COLOR = {
    "default": "",
    "cyan": "36;1",
    "yellow": "33;1",
    "blue": "34;1",
    "magenta": "35;1",
    "green": "32;1",
    "red": "31;1",
    "grey50": "90",
    "orange1": "38;5;208",
    "white": "37;1",
}

def _ansi(color_name: str, s: str) -> str:
    code = _COLOR.get(str(color_name or "").lower(), "")
    return f"\x1b[{code}m{s}\x1b[0m" if (_USE_COLOR and code) else s

# detect if string already contains ANSI escapes (so we don't double-paint)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def has_ansi(s: str) -> bool:
    return bool(_ANSI_RE.search(s))

def color_if_plain(s: str, color_name: str) -> str:
    if not color_name or color_name == "default":
        return s
    # If there is already any ANSI in the cell/line, leave it untouched.
    return s if has_ansi(s) else _ansi(color_name, s)

def paint_line(line: str, color_name: str) -> str:
    # Paint entire line regardless (used for totals/header lines).
    return _ansi(color_name, line) if color_name and color_name != "default" else line

# ──────────────────────────────────────────────────────────────────────────────
# Config loader
# ──────────────────────────────────────────────────────────────────────────────

_cfg_cache: Optional[Dict[str, Any]] = None
_cfg_path: Optional[Path] = None
_cfg_mtime: Optional[float] = None


def _load_config(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if text.strip() else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _cfg() -> Dict[str, Any]:
    """
    Return the panel config dict.

    This implementation is mtime-aware: if PANEL_CONFIG_PATH changes or the
    config file's modification time changes, we reload it. That allows the
    Panel Manager console (or manual edits) to adjust panels/colors while
    Sonic Monitor is running; the next render cycle will pick up changes.
    """
    global _cfg_cache, _cfg_path, _cfg_mtime

    default_path = Path(__file__).parent / "panel_config.json"
    path = Path(os.getenv("PANEL_CONFIG_PATH", str(default_path)))

    try:
        mtime = path.stat().st_mtime
    except Exception:
        mtime = None

    need_reload = False
    if _cfg_cache is None:
        need_reload = True
    elif _cfg_path is None or _cfg_path != path:
        need_reload = True
    elif _cfg_mtime is not None and mtime is not None and mtime != _cfg_mtime:
        need_reload = True

    if need_reload:
        _cfg_cache = _load_config(path)
        _cfg_path = path
        _cfg_mtime = mtime

    return _cfg_cache or {}

# ──────────────────────────────────────────────────────────────────────────────
# Title config + renderer
# ──────────────────────────────────────────────────────────────────────────────

def get_panel_title_config(slug: str, *, default_string: str) -> Dict[str, Any]:
    cfg = _cfg()
    defaults = (cfg.get("defaults") or {}).get("title") or {}
    panels = cfg.get("panels") or {}
    panel = (panels.get(slug) or {}).get("title") or {}

    def pick(*keys, default=None):
        for k in keys:
            if k in panel and panel[k] not in (None, ""):
                return panel[k]
        for k in keys:
            if k in defaults and defaults[k] not in (None, ""):
                return defaults[k]
        return default

    return {
        "string":       pick("string", default=default_string),
        "icon":         pick("icon", default=""),
        "border_style": str(pick("border_style", default="lines")).lower(),
        "border_color": pick("border_color", default="default"),
        "text_color":   pick("text_color", default="cyan"),
        "align":        str(pick("align", default="center")).lower(),
    }

def _center_piece(piece: str, width: int) -> Tuple[int, int]:
    fill = max(0, width - len(piece))
    left = fill // 2
    right = fill - left
    return left, right

def _align_offsets(piece: str, width: int, align: str) -> Tuple[int, int]:
    """
    Compute left/right padding to place `piece` in a field of `width`
    according to `align` ("left" or "center").
    """
    fill = max(0, width - len(piece))
    align = (align or "center").lower()
    if align == "left":
        return 0, fill
    # default: center
    left = fill // 2
    right = fill - left
    return left, right

def _lines_style(
    title_txt: str,
    *,
    width: int,
    border_color: str,
    text_color: str,
    align: str,
) -> List[str]:
    shown = f"  {title_txt}  "
    L, R = _align_offsets(shown, width, align)
    left = "─" * L
    right = "─" * R
    if border_color and border_color != "default":
        left = _ansi(border_color, left)
        right = _ansi(border_color, right)
    return [f"{left}{_ansi(text_color, shown)}{right}"]

def _rectangle_style(
    title_txt: str,
    *,
    width: int,
    border_color: str,
    text_color: str,
    align: str,
) -> List[str]:
    inner = f" {title_txt} "
    box_w = max(10, width)
    content_w = max(1, box_w - 2)

    align = (align or "center").lower()
    if align == "left":
        inner_line = inner.ljust(content_w)
    else:
        inner_line = inner.center(content_w)

    top = "┌" + "─" * content_w + "┐"
    mid = "│" + inner_line + "│"
    bot = "└" + "─" * content_w + "┘"

    if border_color and border_color != "default":
        top = _ansi(border_color, top)
        mid = _ansi(border_color, mid)
        bot = _ansi(border_color, bot)

    # Caller (emit_title_block) will handle indent; these are already box_w wide
    return [top, _ansi(text_color, mid), bot]

# Rich rounded support
_RICH_ROUNDED: Optional[dict] = None
try:
    from rich.box import ROUNDED as _RB  # type: ignore
    def _rb_get(obj, *names, default=""):
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return default
    _RICH_ROUNDED = dict(
        tl=_rb_get(_RB, "upper_left", "tl", "UL", default="╭"),
        tr=_rb_get(_RB, "upper_right", "tr", "UR", default="╮"),
        bl=_rb_get(_RB, "lower_left", "bl", "LL", default="╰"),
        br=_rb_get(_RB, "lower_right", "br", "LR", default="╯"),
        h=_rb_get(_RB, "horizontal", "h", default="─"),
        v=_rb_get(_RB, "vertical", "v", default="│"),
    )
except Exception:
    _RICH_ROUNDED = dict(tl="╭", tr="╮", bl="╰", br="╯", h="─", v="│")

def _rounded_style(
    title_txt: str,
    *,
    width: int,
    border_color: str,
    text_color: str,
    align: str,
) -> List[str]:
    tl = _RICH_ROUNDED["tl"]; tr = _RICH_ROUNDED["tr"]
    bl = _RICH_ROUNDED["bl"]; br = _RICH_ROUNDED["br"]
    h  = _RICH_ROUNDED["h"];  v  = _RICH_ROUNDED["v"]

    box_w = max(10, width)  # full configured title width
    inner = f" {title_txt} "
    avail = max(0, box_w - 2)
    inner_len = len(inner)
    pad_total = max(0, avail - inner_len)

    align = (align or "center").lower()
    if align == "left":
        pad_left = 0
        pad_right = pad_total
    else:
        pad_left = pad_total // 2
        pad_right = pad_total - pad_left

    top = tl + (h * (box_w - 2)) + tr
    mid = v + (" " * pad_left) + _ansi(text_color, inner) + (" " * pad_right) + v
    bot = bl + (h * (box_w - 2)) + br

    if border_color and border_color != "default":
        top = _ansi(border_color, top)
        mid = _ansi(border_color, mid)
        bot = _ansi(border_color, bot)

    # No centering here: box already spans box_w; emit_title_block will indent
    return [top, mid, bot]

def _none_style(
    title_txt: str,
    *,
    width: int,
    border_color: str,
    align: str,
) -> List[str]:
    shown = title_txt
    L, R = _align_offsets(shown, width, align)
    return [(" " * L) + shown + (" " * R)]

def title_lines(slug: str, default_string: str, *, width: Optional[int] = None) -> List[str]:
    W = width or console_width()
    tcfg = get_panel_title_config(slug, default_string=default_string)
    text = tcfg["string"] or default_string
    if tcfg["icon"]:
        text = f"{tcfg['icon']} {text} {tcfg['icon']}"

    style = tcfg["border_style"]
    align = tcfg.get("align", "center")

    if style == "rectangle":
        return _rectangle_style(
            text,
            width=W,
            border_color=tcfg["border_color"],
            text_color=tcfg["text_color"],
            align=align,
        )
    if style == "rounded":
        return _rounded_style(
            text,
            width=W,
            border_color=tcfg["border_color"],
            text_color=tcfg["text_color"],
            align=align,
        )
    if style == "none":
        return _none_style(
            text,
            width=W,
            border_color=tcfg["border_color"],
            align=align,
        )
    return _lines_style(
        text,
        width=W,
        border_color=tcfg["border_color"],
        text_color=tcfg["text_color"],
        align=align,
    )

# ──────────────────────────────────────────────────────────────────────────────
# Layout config (indent/padding) and title width override
# ──────────────────────────────────────────────────────────────────────────────

def get_panel_layout_config(slug: str) -> Dict[str, int | None]:
    """
    Returns ints (>=0) or None for title_width:
      {
        "title_indent": 0,
        "title_padding_above": 1,
        "title_padding_below": 1,
        "title_width": null,           # if set, use this width when centering the title
        "body_indent": 0,
        "body_padding_above": 1,
        "body_padding_below": 1
      }
    """
    cfg = _cfg()
    defaults = (cfg.get("defaults") or {}).get("layout") or {}
    panels = cfg.get("panels") or {}
    panel = (panels.get(slug) or {}).get("layout") or {}

    def pick_int(key: str, default: int) -> int:
        try:
            val = panel.get(key, defaults.get(key, default))
            val = int(val)
            return max(0, val)
        except Exception:
            return default

    def pick_opt_int(key: str) -> Optional[int]:
        val = panel.get(key, defaults.get(key, None))
        if val in (None, ""):
            return None
        try:
            return max(10, int(val))
        except Exception:
            return None

    return {
        "title_indent":          pick_int("title_indent", 0),
        "title_padding_above":   pick_int("title_padding_above", 1),
        "title_padding_below":   pick_int("title_padding_below", 1),
        "title_width":           pick_opt_int("title_width"),
        "body_indent":           pick_int("body_indent", 0),
        "body_padding_above":    pick_int("body_padding_above", 1),
        "body_padding_below":    pick_int("body_padding_below", 1),
    }


def indent_line(s: str, n: int) -> str:
    return (" " * max(0, n)) + s


def apply_indent(lines: List[str], n: int) -> List[str]:
    if n <= 0:
        return lines
    pad = " " * n
    return [pad + ln if ln else ln for ln in lines]


def want_outer_hr(slug: str, *, default_string: str) -> bool:
    """True => caller should draw hr above/below title block (used for 'lines' style)."""
    tcfg = get_panel_title_config(slug, default_string=default_string)
    style = (tcfg.get("border_style") or "lines").lower()
    return style not in {"rounded", "rectangle"}


def emit_title_block(slug: str, default_string: str) -> List[str]:
    """
    Builds the full title segment including:
      - optional outer hr (for 'lines' style)
      - title padding above/below
      - title indent
      - optional title width override
    """
    lcfg = get_panel_layout_config(slug)
    width_override = lcfg["title_width"]
    W = width_override or console_width()
    wrap = want_outer_hr(slug, default_string=default_string)
    out: List[str] = []
    out += [""] * lcfg["title_padding_above"]
    if wrap:
        out.append(hr(W))
    tlines = title_lines(slug, default_string=default_string, width=W)
    tlines = apply_indent(tlines, lcfg["title_indent"])
    out += tlines
    if wrap:
        out.append(hr(W))
    out += [""] * lcfg["title_padding_below"]
    return out


def body_pad_above(slug: str) -> List[str]:
    return [""] * get_panel_layout_config(slug)["body_padding_above"]


def body_pad_below(slug: str) -> List[str]:
    return [""] * get_panel_layout_config(slug)["body_padding_below"]


def body_indent_lines(slug: str, lines: List[str]) -> List[str]:
    return apply_indent(lines, get_panel_layout_config(slug)["body_indent"])

# ──────────────────────────────────────────────────────────────────────────────
# Body config + helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_panel_body_config(slug: str) -> Dict[str, Any]:
    """
    Returns:
      {
        "column_header_text_color": "...",
        "body_text_color": "...",
        "totals_row_color": "..."
        "table": {"style": "...", "table_justify": "...", "header_justify": "..."}
    All keys optional; defaults fall back to `defaults.body` (and
    `defaults.body.table`) or "default".
    """
    cfg = _cfg()
    defaults = (cfg.get("defaults") or {}).get("body") or {}
    panels = cfg.get("panels") or {}
    panel_body = (panels.get(slug) or {}).get("body") or {}
    defaults_table = (defaults.get("table") or {}) if isinstance(defaults.get("table"), dict) else {}
    panel_table = (panel_body.get("table") or {}) if isinstance(panel_body.get("table"), dict) else {}

    def pick(key: str, default: str = "default") -> str:
        if key in panel_body and panel_body[key] not in (None, ""):
            return str(panel_body[key])
        if key in defaults and defaults[key] not in (None, ""):
            return str(defaults[key])
        return default

    def pick_table(key: str, default: str) -> str:
        if key in panel_table and panel_table[key] not in (None, ""):
            return str(panel_table[key])
        if key in defaults_table and defaults_table[key] not in (None, ""):
            return str(defaults_table[key])
        return default

    table_cfg = {
        "style": pick_table("style", "invisible").lower(),
        "table_justify": pick_table("table_justify", "left").lower(),
        "header_justify": pick_table("header_justify", "left").lower(),
    }

    return {
        "column_header_text_color": pick("column_header_text_color"),
        "body_text_color": pick("body_text_color"),
        "totals_row_color": pick("totals_row_color"),
        "table": table_cfg,
    }


def get_panel_order() -> List[str]:
    cfg = _cfg()
    order = cfg.get("panel_order")
    if not isinstance(order, list):
        return []
    return [str(s) for s in order]


def is_panel_enabled(slug: str) -> bool:
    """
    Return True if the panel is enabled in config.

    If no explicit 'enabled' flag is set for the slug, default to True.
    """
    cfg = _cfg()
    panels = cfg.get("panels") or {}
    pdata = panels.get(slug) or {}
    enabled = pdata.get("enabled")
    if enabled is None:
        return True
    return bool(enabled)


def is_enabled(slug: str) -> bool:
    return is_panel_enabled(slug)


def enabled_panel_slugs() -> List[str]:
    """
    Return a list of panel slugs that are enabled, according to config.

    If the config has no 'panels' section, returns an empty list.
    """
    cfg = _cfg()
    panels = cfg.get("panels") or {}
    out: List[str] = []
    for slug, pdata in panels.items():
        if (pdata or {}).get("enabled") is False:
            continue
        out.append(slug)
    return out
