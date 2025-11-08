from __future__ import annotations
"""
cycle_footer_panel.py
Sonic Reporting — footer panel (rendered last).

Layout (inside a solid box, left-padded):
  1) 🌀 cycle #N
  2) ⏱ poll Xs • finished Ys
  3) 📅 MM/DD • h:mmap/pm
  4) 🎉 {fun_core line}
  + two trailing blank lines for visual padding

Knobs (read from env; Rich default is set in console_reporter):
  SONIC_CONSOLE_WIDTH     -> console width (default 92)
  SONIC_FOOTER_RICH       -> "1"/"true" to use Rich (preferred)
  SONIC_FOOTER_BORDER     -> ANSI color code for fallback border (default "38;5;39")
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


def _get_from_tree(tree: Dict[str, Any], *keys: str, default=None):
    for key in keys:
        cur = tree
        try:
            for p in key.split("."):
                cur = cur[p]
            return cur
        except Exception:
            continue
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


def _resolve_fun_line(csum: Dict[str, Any], loop_counter: int) -> str:
    # prefer precomputed in the summary
    for k in ("fun_line", "fun", "fun_text"):
        v = csum.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

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

def _box_heavy_ansi(rows: Iterable[str], width: Optional[int] = None, indent: int = 2) -> List[str]:
    """
    Heavy Unicode box with colored rails; left indent inside box.
    Returns list[str] plus two trailing blank lines.
    """
    W = width or _console_width()
    inner = max(0, W - 2)
    color = _border_code()

    top = _ansi(color, "┏" + ("━" * inner) + "┓")
    bot = _ansi(color, "┗" + ("━" * inner) + "┛")

    out: List[str] = [top]
    pad = " " * max(0, indent)
    for raw in rows:
        text = pad + str(raw).replace("\n", " ").strip()
        if len(text) > inner:
            text = (text[: inner - 1] + "…") if inner >= 1 else ""
        out.append(_ansi(color, "┃") + text.ljust(inner, " ") + _ansi(color, "┃"))
    out.append(bot)
    # two extra blank lines for spacing
    out.append("")
    out.append("")
    return out


def _try_rich_box(rows: List[str], width: int) -> Optional[List[str]]:
    """
    Optional rich.Panel rendering with left padding.
    Returns None if disabled/missing.
    """
    use_rich = os.environ.get("SONIC_FOOTER_RICH", "0").lower() in ("1", "true", "yes", "on")
    if not use_rich:
        return None
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich import box as rbox

        console = Console(width=width, record=True, color_system="truecolor")
        body = Text()
        # rows already contain icons; panel adds left indent via padding (0,2)
        body.append(rows[0] + "\n")
        body.append(rows[1] + "\n")
        body.append(rows[2] + "\n")
        body.append(rows[3])

        p = Panel(
            body,
            box=rbox.HEAVY,
            border_style="bright_cyan",
            padding=(0, 2),  # left/right indent inside the box
            expand=False,
        )
        console.print(p)
        ansi = console.export_text(styles=True)
        lines = [ln.rstrip("\n") for ln in ansi.splitlines()]
        # append the two line padding
        lines.append("")
        lines.append("")
        return lines
    except Exception:
        return None


# ───────────────────────── public API ────────────────────────────────

def render(context: Optional[Dict[str, Any]] = None, *args, **kwargs) -> List[str]:
    """
    Accepted:
      render(ctx)
      render(dl, ctx)
      render(ctx, width)
      render(ctx, csum={...})
    """
    ctx: Dict[str, Any] = {}
    if context:
        if isinstance(context, dict):
            ctx.update(context)
        else:
            ctx["dl"] = context  # someone passed DataLocker first

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

    csum: Dict[str, Any] = ctx.get("csum") or ctx.get("summary") or {}

    loop_counter = _coalesce(
        ctx.get("loop_counter"),
        csum.get("loop_counter"),
        _get_from_tree(csum, "cycle.n", "cycle.number", "n"),
        csum.get("cycle_no"), csum.get("loop_no"), default=0
    )
    try:
        loop_counter = int(loop_counter)
    except Exception:
        loop_counter = 0

    poll_interval_s = _coalesce(
        ctx.get("poll_interval_s"),
        ctx.get("poll_seconds"),
        csum.get("poll_seconds"),
        _get_from_tree(csum, "config.poll_seconds"),
        default=0,
    )
    try:
        poll_interval_s = int(poll_interval_s)
    except Exception:
        poll_interval_s = 0

    total_elapsed_s = _coalesce(
        ctx.get("total_elapsed_s"),
        ctx.get("elapsed_s"),
        csum.get("cycle_elapsed_s"),
        csum.get("elapsed_s"),
        _get_from_tree(csum, "timing.elapsed_s"),
        default=0.0,
    )
    try:
        total_elapsed_s = float(total_elapsed_s)
    except Exception:
        total_elapsed_s = 0.0

    ts_value = _coalesce(ctx.get("ts"), csum.get("ts"),
                         _get_from_tree(csum, "time.ts", "timing.ts_iso"), default=None)

    # Build the four content rows (no manual indent here; Rich handles padding, ANSI adds it)
    row1 = f"🌀 cycle #{loop_counter}"
    row2 = f"⏱ poll {poll_interval_s}s • finished {total_elapsed_s:.2f}s"
    row3 = f"📅 {_fmt_stamp(ts_value)}"
    row4 = f"🎉 {_resolve_fun_line(csum, int(loop_counter))}"

    width = ctx.get("width") or _console_width()

    # Try Rich first (padding built-in). Fallback to ANSI heavy box with left indent.
    rich_lines = _try_rich_box([row1, row2, row3, row4], width)
    if rich_lines is not None:
        return rich_lines

    return _box_heavy_ansi([row1, row2, row3, row4], width=width, indent=2)


def connector(*args, **kwargs) -> List[str]:
    return render(*args, **kwargs)


def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    demo_csum = {
        "poll_seconds": 34,
        "cycle_elapsed_s": 0.03,
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "cycle": {"n": 8},
        # leave out fun_line to exercise fun_core fallback
    }
    for ln in render({"csum": demo_csum}):
        print(ln)
