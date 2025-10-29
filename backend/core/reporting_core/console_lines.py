# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional

# Consolidated (7-arg) compact reporter from console_reporter
from backend.core.reporting_core.console_reporter import emit_compact_cycle as _emit_compact_cycle7

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
    Does NOT print any extra lines (no Sources, no Prices, etc).
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
    _emit_compact_cycle7(summary, int(cyc_ms), int(poll_interval_s), int(lc), float(tot), float(slp))
