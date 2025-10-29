# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional

# Import the consolidated (7-arg) reporter and wrap it with a 4-arg facade.
from backend.core.reporting_core.console_reporter import emit_compact_cycle as _emit_compact_cycle7


def emit_compact_cycle(
    summary: Dict[str, Any],
    cfg: Dict[str, Any],
    poll_interval_s: int,
    *,
    enable_color: bool = False,        # accepted for API compatibility, NOT forwarded
    loop_counter: Optional[int] = None,
    total_elapsed: Optional[float] = None,
    sleep_time: Optional[float] = None,
) -> None:
    """Compatibility wrapper: 4-arg call used across Sonic6/7 → 7-arg reporter."""
    summary = summary or {}

    # derive timing safely
    durs = summary.get("durations", {}) or {}
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

    # DO NOT pass enable_color here — the 7-arg reporter doesn’t accept it.
    _emit_compact_cycle7(summary, int(cyc_ms), int(poll_interval_s), int(lc), float(tot), float(slp))
