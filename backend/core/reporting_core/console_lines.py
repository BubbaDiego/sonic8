# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import time
from typing import Any, Dict, Optional

# Consolidated (7-arg) compact reporter from console_reporter
from backend.core.reporting_core.console_reporter import (
    emit_compact_cycle as _emit_compact_cycle7,
    render_panel_stack as _render_panels,
)

def emit_compact_cycle(
    summary: Dict[str, Any],
    cfg: Dict[str, Any],
    poll_interval_s: int,
    *,
    enable_color: bool = False,          # accepted for API compatibility only
    loop_counter: Optional[int] = None,
    total_elapsed: Optional[float] = None,
    sleep_time: Optional[float] = None,
) -> None:
    """
    Compatibility wrapper (Sonic6/7): 4-arg call → 7-arg reporter.
    Does NOT print any extra lines (no Sources, no Prices, no Positions, etc).
    """
    durs = (summary or {}).get("durations", {}) or {}
    elapsed_s = float(summary.get("elapsed_s", 0.0) or 0.0)
    cyc_ms = int(durs.get("cyclone_ms") or durs.get("cycle_ms") or round(elapsed_s * 1000.0))
    if cyc_ms <= 0 and elapsed_s > 0:
        cyc_ms = max(1, int(round(elapsed_s * 1000.0)))

    lc = loop_counter if loop_counter is not None else (
        summary.get("cycle_num")
        or summary.get("loop_counter")
        or (summary.get("loop") or {}).get("n")
        or -1
    )

    tot = float(total_elapsed) if total_elapsed is not None else (elapsed_s if elapsed_s else (cyc_ms / 1000.0))
    slp = float(sleep_time) if sleep_time is not None else max(0.0, float(poll_interval_s or 0) - float(tot or 0))

    # Do not pass enable_color (the 7-arg reporter doesn't accept it)
    width = None
    dl = None
    db_basename = None
    cfg_dict: Optional[Dict[str, Any]] = cfg if isinstance(cfg, dict) else None
    if cfg_dict is not None:
        width = cfg_dict.get("console_width") or cfg_dict.get("width")
        dl = cfg_dict.get("dl")
        db_basename = cfg_dict.get("db_basename")

    _emit_compact_cycle7(
        summary,
        int(cyc_ms),
        int(poll_interval_s),
        int(lc),
        float(tot),
        float(slp),
        db_basename=db_basename,
    )

    ts = summary.get("ts") if isinstance(summary, dict) else None
    if ts is None and isinstance(summary, dict):
        ts = summary.get("timestamp")
        if ts is None:
            ts = (summary.get("time") or {}).get("ts")

    width_value = width
    if width_value is None:
        try:
            width_value = int(os.environ.get("SONIC_CONSOLE_WIDTH", "92"))
        except Exception:
            width_value = None

    ctx: Dict[str, Any] = {
        "dl": dl,
        "cfg": cfg_dict,
        "loop_counter": int(lc),
        "poll_interval_s": int(poll_interval_s),
        "total_elapsed_s": float(tot),
        "ts": ts if ts is not None else time.time(),
        "summary": summary or {},
    }
    if db_basename:
        ctx["db_basename"] = db_basename

    try:
        _render_panels(
            ctx=ctx,
            dl=dl,
            cfg=cfg_dict,
            width=width_value,
        )
    except Exception as exc:
        print(f"[REPORT] panels failed: {exc}", flush=True)
