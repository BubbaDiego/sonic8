from __future__ import annotations
"""
cycle_footer_panel.py
Sonic Reporting — footer panel (rendered last).

Layout (inside a solid box):
  1) 🌀  cycle #N
  2) ⏱  poll Xs • finished Ys
  3) 📅  MM/DD • h:mmap/pm
  4) 🎉  {fun_core line}
  + two trailing blank lines for visual padding

Knobs (read from env; Rich default is set in console_reporter):
  SONIC_CONSOLE_WIDTH   -> console width (default 92)
  SONIC_FOOTER_RICH     -> "1"/"true" to use Rich (preferred)
  SONIC_FOOTER_BORDER   -> ANSI color code for fallback border (default "38;5;39")
  SONIC_FOOTER_MARGIN   -> left margin (spaces) OUTSIDE the box (default 2)
"""

import os
import importlib
import datetime as _dt
from typing import Any, Dict, Iterable, List, Optional

PANEL_KEY = "cycle_footer_panel"
PANEL_NAME = "Cycle Footer Panel"


# ─────────────────────────────── utils ───────────────────────────────

def _console_width(default: int = 92) -> int:
    try:
        w = int(os.environ.get("SONIC_CONSOLE_WIDTH", default))
        return max(40, min(180, w))
    except Exception:
        return default

def _left_margin() -> int:
    try:
        return max(0, int(os.environ.get("SONIC_FOOTER_MARGIN", "2")))
    except Exception:
        return 2

def _ansi(code: str, s: str) -> str:
    if not code:
        return s
    return f"\x1b[{code}m{s}\x1b[0m"

def _border_code() -> str:
    return os.environ.get("SONIC_FOOTER_BORDER", "38;5;39")  # bright cyan

def _parse_ts(ts: Any) -> _dt.datetime:
    if ts is None:
        return _dt.datetime.now()
    if isinstance(ts, (int, float)):
        try:
            return _dt.datetime.fromtimestamp(float(ts))
        except Exception:
            return _dt.datetime.now()
    if isinstance(ts, _dt.datetime):
        return ts
    s = str(ts).strip()
    try:
        if s.endswith("Z"):
            return _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
        return _dt.datetime.fromisoformat(s)
    except Exception:
        return _dt.datetime.now()

def _fmt_stamp(ts: Any) -> str:
    t = _parse_ts(ts)
    hour = t.strftime("%I").lstrip("0") or "0"
    return f"{t.strftime('%m/%d')} • {hour}:{t.strftime('%M%p').lower()}"

def _coalesce(*vals, default=None):
    for v in vals:
        if v is not None:
            return v
    return default


# ─────────────────────── fun_core integration ────────────────────────

def _import_fun():
    for m in (
        "backend.core.fun_core.client",   # preferred
        "backend.core.fun_core",          # package re-exports
        "backend.core.fun_core.fun_core"  # legacy
    ):
        try:
            return importlib.import_module(m)
        except Exception:
            continue
    return None

def _resolve_fun_line(loop_counter: int, ctx_fun: Optional[str] = None) -> str:
    # prefer explicit line from ctx if given
    if isinstance(ctx_fun, str) and ctx_fun.strip():
        return ctx_fun.strip()

    mod = _import_fun()
    if not mod:
        return "—"

    # get_fun_line may return (text, meta) | dict | str
    fn = getattr(mod, "get_fun_line", None)
    if callable(fn):
        try:
            res = fn(int(loop_counter))
            if isinstance(res, tuple) and res and isinstance(res[0], str) and res[0].strip():
                return res[0].strip()
            if isinstance(res, dict):
                for k in ("text", "fun_line", "line"):
                    val = res.get(k)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            if isinstance(res, str) and res.strip():
                return res.strip()
        except Exception:
            pass

    # fallback
    for name in ("fun_random_text_sync", "fun_random_text"):
        fn2 = getattr(mod, name, None)
        if callable(fn2):
            try:
                txt = fn2()
                if isinstance(txt, str) and txt.strip():
                    return txt.strip()
            except Exception:
                pass
    return "—"


# ─────────────────────────── renderers ───────────────────────────────

def _make_rows(loop_counter: int, poll_s: int, elapsed_s: float, ts: Any, fun_text: str) -> List[tuple]:
    """
    Build icon/text pairs. Text is plain; columns handled by renderers.
    """
    return [
        ("🌀", f"cycle #{loop_counter}"),
        ("⏱", f"poll {poll_s}s • finished {elapsed_s:.2f}s"),
        ("📅", f"{_fmt_stamp(ts)}"),
        ("🎉", fun_text),
    ]

def _try_rich_box(rows: List[tuple], width: int, margin: int) -> Optional[List[str]]:
    """
    Optional rich.Panel(Table) with a left margin wrapper.
    Returns None if disabled/missing.
    """
    use_rich = os.environ.get("SONIC_FOOTER_RICH", "0").lower() in ("1", "true", "yes", "on")
    if not use_rich:
        return None
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.padding import Padding
        from rich import box as rbox

        console = Console(width=width + margin, record=True, color_system="truecolor")

        tbl = Table.grid(padding=(0, 1))   # (row_pad, col_pad); gives a fixed gap between icon & text
        tbl.add_column(justify="left", no_wrap=True)   # icon col
        tbl.add_column(justify="left", no_wrap=False)  # text col (flex)
        for icon, text in rows:
            tbl.add_row(icon, text)

        panel = Panel(
            tbl,
            box=rbox.HEAVY,
            border_style="bright_cyan",
            padding=(0, 2),  # internal left/right indent
            expand=False,
        )

        renderable = panel if margin <= 0 else Padding(panel, (0, 0, 0, margin))
        console.print(renderable)

        ansi = console.export_text(styles=True)
        lines = [ln.rstrip("\n") for ln in ansi.splitlines()]
        # append the two line padding
        lines.append("")
        lines.append("")
        return lines
    except Exception:
        return None

def _box_heavy_ansi(rows: List[tuple], width: int, margin: int, inner_indent: int = 0, icon_col: int = 2, gap: int = 1) -> List[str]:
    """
    ANSI fallback with colored rails and external left margin.
    Two columns: icon (fixed width) + gap + text (fills).
    """
    color = _border_code()
    # account for drawing the box at a given margin (spaces before every line)
    left = " " * max(0, margin)

    inner = max(0, width - 2)  # content width inside ┃ ┃
    top = left + _ansi(color, "┏" + ("━" * inner) + "┓")
    bot = left + _ansi(color, "┗" + ("━" * inner) + "┛")

    out: List[str] = [top]
    pad = " " * max(0, inner_indent)

    # icon column width measured in characters; emojis render ~2 cells in most fonts,
    # but length() = 1. This keeps alignment visually acceptable for our use.
    for icon, text in rows:
        icon_s = (icon or "")[:1]
        col = (icon_s + " " * max(0, icon_col - 1))  # ensure a fixed column for text start
        raw = pad + col + (" " * gap) + (text or "")
        # truncate to inner width
        if len(raw) > inner:
            raw = raw[: inner - 1] + "…"
        out.append(left + _ansi(color, "┃") + raw.ljust(inner, " ") + _ansi(color, "┃"))

    out.append(bot)
    # two extra blank lines for spacing
    out.append("")
    out.append("")
    return out


# ───────────────────────── public API ────────────────────────────────

def render(context: Optional[Dict[str, Any]] = None, *args, **kwargs) -> List[str]:
    """
    Accepted:
      render(ctx)
      render(dl, ctx)
      render(ctx, width)
      render(ctx, loop_counter=..., poll_interval_s=..., total_elapsed_s=..., ts=...)
    """
    ctx: Dict[str, Any] = {}
    if context:
        if isinstance(context, dict):
            ctx.update(context)
        else:
            ctx["dl"] = context  # if someone passes DataLocker first

    # absorb optional positionals
    if len(args) >= 1:
        a0 = args[0]
        if isinstance(a0, dict):
            ctx.update(a0)
        else:
            ctx["dl"] = a0
    if len(args) >= 2:
        a1 = args[1]
        if isinstance(a1, dict):
            ctx.update(a1)
        elif isinstance(a1, (int, float)):
            kwargs.setdefault("width", int(a1))
    if kwargs:
        ctx.update(kwargs)

    # minimal context (no csum)
    loop_counter = int(_coalesce(ctx.get("loop_counter"), 0) or 0)
    poll_s       = int(_coalesce(ctx.get("poll_interval_s"), 0) or 0)
    elapsed_s    = float(_coalesce(ctx.get("total_elapsed_s"), 0.0) or 0.0)
    ts_value     = _coalesce(ctx.get("ts"), None)

    width  = int(ctx.get("width") or _console_width())
    margin = _left_margin()

    fun_text = _resolve_fun_line(loop_counter, ctx_fun=ctx.get("fun_line"))
    rows = _make_rows(loop_counter, poll_s, elapsed_s, ts_value, fun_text)

    # Prefer Rich panel with a left margin; fallback to ANSI box.
    rich_lines = _try_rich_box(rows, width=width, margin=margin)
    if rich_lines is not None:
        return rich_lines

    return _box_heavy_ansi(rows, width=width, margin=margin, inner_indent=0, icon_col=2, gap=1)


def connector(*args, **kwargs) -> List[str]:
    return render(*args, **kwargs)


def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    demo_ctx = {
        "loop_counter": 1,
        "poll_interval_s": 34,
        "total_elapsed_s": 0.11,
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        # "fun_line": "In code we trust; in logs we verify.",  # optional override
        "width": 92,
    }
    for ln in render(demo_ctx):
        print(ln)
