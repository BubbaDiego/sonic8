from __future__ import annotations

"""
cycle_footer_panel.py
Sonic Reporting — footer panel rendered last in the cycle output.

Design B (requested):
  A solid heavy-box with two rows:
    1) 🌀 cycle #N • poll Xs • finished Ys • MM/DD • h:mm(am|pm)
    2) 🎉 {fun_line}  (from fun_core or the cycle summary)

This module is dependency-light and resilient to different monitor contexts.
It accepts either a single "context" dict (preferred by the Sonic sequencer)
or keyword args. It returns a list[str] of console lines to print.
"""

import os
import importlib
import datetime as _dt
from typing import Any, Dict, Iterable, List, Optional

PANEL_KEY = "cycle_footer_panel"   # used by some sequencers
PANEL_NAME = "Cycle Footer Panel"  # human label


# --------- utilities ---------

def _console_width(default: int = 92) -> int:
    """Read expected console width from env or fall back."""
    try:
        w = int(os.environ.get("SONIC_CONSOLE_WIDTH", default))
        return max(40, min(180, w))
    except Exception:
        return default


def _box_heavy(lines: Iterable[str], width: Optional[int] = None) -> List[str]:
    """Wrap lines in a heavy Unicode box. No colors for reliability."""
    W = width or _console_width()
    inner = max(0, W - 2)
    top = "┏" + ("━" * inner) + "┓"
    bot = "┗" + ("━" * inner) + "┛"
    out: List[str] = [top]
    for raw in lines:
        # ensure single-line, trim hard, then pad
        text = str(raw).replace("\n", " ").strip()
        if len(text) > inner:
            text = text[: inner - 1] + "…" if inner >= 1 else ""
        out.append("┃" + text.ljust(inner, " ") + "┃")
    out.append(bot)
    return out


def _parse_ts(ts: Any) -> _dt.datetime:
    """Best-effort parse of a timestamp input to a local datetime."""
    if ts is None:
        return _dt.datetime.now()
    if isinstance(ts, (int, float)):
        try:
            return _dt.datetime.fromtimestamp(float(ts))
        except Exception:
            return _dt.datetime.now()
    if isinstance(ts, _dt.datetime):
        return ts
    if isinstance(ts, str):
        s = ts.strip()
        try:
            if s.endswith("Z"):
                return _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
            return _dt.datetime.fromisoformat(s)
        except Exception:
            return _dt.datetime.now()
    return _dt.datetime.now()


def _fmt_stamp(ts: Any) -> str:
    """Format as 'MM/DD • h:mmpm' (lowercased AM/PM)."""
    t = _parse_ts(ts)
    hour = t.strftime("%I").lstrip("0") or "0"  # cross-platform
    return f"{t.strftime('%m/%d')} • {hour}:{t.strftime('%M%p').lower()}"


def _coalesce(*vals, default=None):
    for v in vals:
        if v is not None:
            return v
    return default


def _get_from_tree(tree: Dict[str, Any], *keys: str, default=None):
    """Try multiple dotted paths in a dict-of-dicts tree."""
    for key in keys:
        cur = tree
        try:
            parts = key.split(".")
            for p in parts:
                cur = cur[p]
            return cur
        except Exception:
            continue
    return default


# --------- fun_core integration ---------

def _import_fun_core():
    """Try to import backend.core.fun_core.* in a few common shapes."""
    mods = [
        "backend.core.fun_core",
        "backend.core.fun_core.fun_core",
        "backend.core.fun_core.__init__",
    ]
    for m in mods:
        try:
            return importlib.import_module(m)
        except Exception:
            continue
    return None


def _resolve_fun_line(csum: Dict[str, Any], loop_counter: int) -> str:
    # Prefer a line already carried by the monitor summary
    for k in ("fun_line", "fun", "fun_text"):
        v = csum.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    fc = _import_fun_core()
    if fc:
        # 1) get_fun_line(loop_counter) -> str or dict
        fn = getattr(fc, "get_fun_line", None)
        if callable(fn):
            try:
                res = fn(loop_counter)
                if isinstance(res, dict):
                    for k in ("text", "fun_line", "line"):
                        val = res.get(k)
                        if isinstance(val, str) and val.strip():
                            return val.strip()
                elif isinstance(res, str) and res.strip():
                    return res.strip()
            except Exception:
                pass
        # 2) fun_random_text_sync() -> str (fallback)
        for name in ("fun_random_text_sync", "random_line", "get_fun", "get_fun_text"):
            fn2 = getattr(fc, name, None)
            if callable(fn2):
                try:
                    res = fn2()
                    if isinstance(res, str) and res.strip():
                        return res.strip()
                except Exception:
                    pass

    return "—"


# --------- main render ---------

def render(
    _dl: Any = None,
    csum: Optional[Dict[str, Any]] = None,
    _default_json_path: Optional[str] = None,
    *,
    context: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> List[str]:
    """
    Returns a list of console lines containing the footer box.
    Accepts either:
      - a context dict as the first positional argument or via `context`
      - keyword args (csum=..., loop_counter=..., poll_interval_s=..., total_elapsed_s=...)
      - the sequencer-style `(dl, csum, default_json_path)` call signature
    """
    inferred_context: Optional[Dict[str, Any]] = None
    if isinstance(_dl, dict) and csum is None and context is None:
        inferred_context = _dl

    ctx: Dict[str, Any] = {}
    if inferred_context:
        ctx.update(inferred_context)
    if context:
        ctx.update(context)
    if kwargs:
        ctx.update(kwargs)

    if csum is not None:
        ctx.setdefault("csum", csum)
    else:
        ctx.setdefault("csum", {})

    csum_dict: Dict[str, Any] = ctx.get("csum") or {}

    # Loop number: try several common keys
    loop_counter = _coalesce(
        ctx.get("loop_counter"),
        csum_dict.get("loop_counter"),
        _get_from_tree(csum_dict, "cycle.n", "cycle.number", "n"),
        csum_dict.get("cycle_no"),
        csum_dict.get("loop_no"),
        default=0,
    )
    try:
        loop_counter = int(loop_counter)
    except Exception:
        loop_counter = 0

    poll_interval_s = _coalesce(
        ctx.get("poll_interval_s"),
        ctx.get("poll_seconds"),
        csum_dict.get("poll_seconds"),
        _get_from_tree(csum_dict, "config.poll_seconds"),
        default=0,
    )
    try:
        poll_interval_s = int(poll_interval_s)
    except Exception:
        poll_interval_s = 0

    total_elapsed_s = _coalesce(
        ctx.get("total_elapsed_s"),
        ctx.get("elapsed_s"),
        csum_dict.get("cycle_elapsed_s"),
        csum_dict.get("elapsed_s"),
        _get_from_tree(csum_dict, "timing.elapsed_s"),
        default=0.0,
    )
    try:
        total_elapsed_s = float(total_elapsed_s)
    except Exception:
        total_elapsed_s = 0.0

    ts_value = _coalesce(
        ctx.get("ts"),
        csum_dict.get("ts"),
        _get_from_tree(csum_dict, "time.ts", "timing.ts_iso"),
        default=None,
    )

    header = f"🌀 cycle #{loop_counter} • poll {poll_interval_s}s • finished {total_elapsed_s:.2f}s • {_fmt_stamp(ts_value)}"
    fun_line = _resolve_fun_line(csum_dict, loop_counter)

    width = ctx.get("width") or _console_width()
    body = [header, f"🎉 {fun_line}"]
    return _box_heavy(body, width=width)


# Some sequencers may do a duck-typed `.name()` check
def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    # manual preview
    demo_csum = {
        "poll_seconds": 30,
        "cycle_elapsed_s": 0.62,
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "cycle": {"n": 12},
        "fun_line": "In code we trust; in logs we verify.",
    }
    for ln in render({"csum": demo_csum, "loop_counter": 12}):
        print(ln)
