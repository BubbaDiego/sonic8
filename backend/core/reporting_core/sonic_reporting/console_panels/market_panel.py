# -*- coding: utf-8 -*-
"""
Market panel (stub)

Sonic8 currently has Market Core work in progress in another branch. To keep
the main Sonic Monitor UI clean, this panel renders a simple stub instead of
attempting to query DLMonitorsManager in ways that may not exist yet.

This avoids noisy:
    [REPORT] ... market_panel.render failed: 'DLMonitorsManager' object has no attribute 'select_all'
lines, while keeping the wiring in place for a future full market panel.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.core.reporting_core.sonic_reporting.console_panels.panel_utils import (
    emit_panel,
    body_indent_lines,
)


PANEL_KEY = "market_panel"
PANEL_NAME = "Market"
PANEL_SLUG = "market"


def render(ctx: Any) -> List[str]:
    """
    Render a stubbed Market panel.

    If you later wire up a real Market Core, this function can be replaced
    with a full implementation that inspects market-related monitors.
    For now we just show a short 'disabled' message.
    """
    lines = [
        "Market panel is currently disabled (market core stubbed in this branch).",
    ]
    body = body_indent_lines(PANEL_SLUG, lines)
    return emit_panel(PANEL_SLUG, PANEL_NAME, body)
