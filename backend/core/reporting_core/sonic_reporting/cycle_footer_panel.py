from __future__ import annotations

"""
cycle_footer_panel.py
Sonic Reporting — footer panel rendered last.

Design B:
  Heavy single box with two rows:
    1) 🌀 cycle #N • poll Xs • finished Ys • MM/DD • h:mma/pm
    2) 🎉 {fun_line}

This file is tolerant of different call signatures and includes a
connector(...) alias for sequencer convenience.
"""

import os
import importlib
import datetime as _dt
from typing import Any, Dict, Iterable, List, Optional, Tuple

PANEL_KEY = "cycle_footer_panel"
PANEL_NAME = "Cycle Footer Panel"


# ── utils ───────────────────────────────────────────────────────────────────────

def _console_width(default: int = 92) -> int:
    try:
        w = int(os.environ.get("SONIC_CONSOLE_WIDTH", default))
        return max(40, min(180, w))
    except Exception:
        return default


def _box_heavy(lines: Iterable[str], width: Optional[int] = None) -> List[str]:
    W = width or _console_width()
    inner = max(0, W - 2)
    top = "┏" + ("━" * inner) + "┓"
    bot = "┗" + ("━" * inner) + "┛"
    out: List[str] = [top]
    for raw in lines:
        text = str(raw).replace("\n", " ").strip()
        if len(text) > inner:
            text = (text[: inner - 1] + "…") if inner >= 1 else ""
        out.append("┃" + text.ljust(inner, " ") + "┃")
    out.append(bot)
    return out


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


# ── fun_core integration ────────────────────────────────────────────────────────

def _import_fun_client():
    """
    Resolve the fun client in a few shapes.
    Primary target is backend.core.fun_core.client (sonic6/sonic7 style).
    """
    for m in (
        "backend.core.fun_core.client",
        "backend.core.fun_core",               # package may re-export
        "backend.core.fun_core.fun_core",      # older naming
    ):
        try:
            return importlib.import_module(m)
        except Exception:
            continue
    return None


def _resolve_fun_line(csum: Dict[str, Any], loop_counter: int) -> str:
    # Prefer precomputed summary
    for k in ("fun_line", "fun", "fun_text"):
        v = csum.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    mod = _import_fun_client()
    if not mod:
        return "—"

    # get_fun_line(loop_counter) may return (text, meta) or dict or str
    fn = getattr(mod, "get_fun_line", None)
    if callable(fn):
        try:
            res = fn(int(loop_counter))
            if isinstance(res, tuple) and res and isinstance(res[0], str):
                return res[0].strip() or "—"
            if isinstance(res, dict):
                for k in ("text", "fun_line", "line"):
                    if isinstance(res.get(k), str) and res[k].strip():
                        return res[k].strip()
            if isinstance(res, str) and res.strip():
                return res.strip()
        except Exception:
            pass

    # fallback: fun_random_text_sync()
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


# ── main render (positional-args tolerant) ──────────────────────────────────────

def render(context: Optional[Dict[str, Any]] = None, *args, **kwargs) -> List[str]:
    """
    Accepted shapes:
      render(ctx)
      render(ctx, width)
      render(dl, ctx)
      render(ctx, csum={...})
      render(..., width=92)
    """
    ctx: Dict[str, Any] = {}
    if context:
        ctx.update(context)

    if len(args) >= 1:
        a0 = args[0]
        if isinstance(a0, dict):
            ctx.update(a0)
        else:
            ctx.setdefault("dl", a0)
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

    header = f"🌀 cycle #{loop_counter} • poll {poll_interval_s}s • finished {total_elapsed_s:.2f}s • {_fmt_stamp(ts_value)}"
    fun_line = _resolve_fun_line(csum, int(loop_counter))

    width = ctx.get("width") or _console_width()
    body = [header, f"🎉 {fun_line}"]
    return _box_heavy(body, width=width)


def connector(*args, **kwargs) -> List[str]:
    """Sequencer-friendly entrypoint; simply delegates to render."""
    return render(*args, **kwargs)


def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    demo_csum = {
        "poll_seconds": 34,
        "cycle_elapsed_s": 0.28,
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "cycle": {"n": 1},
        # leave out fun_line to verify fun_core fallback
    }
    for ln in render({"csum": demo_csum}):
        print(ln)
