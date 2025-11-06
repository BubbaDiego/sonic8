# -*- coding: utf-8 -*-
from __future__ import annotations
"""Shared helpers for reading monitor thresholds from configuration JSON."""

from typing import Any, Dict, Optional, Tuple


def _get(cfg: Dict[str, Any], dotted: str, default: Any = None) -> Any:
    """Safe nested lookup without raising on missing keys."""
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
        if cur is None:
            return default
    return cur


def resolve_profit_thresholds(cfg: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], str]:
    """
    Return the profit thresholds as ``(single_usd, portfolio_usd, source_tag)``.

    Preferred keys live under ``profit_monitor``. If either threshold is missing
    there, fall back to the legacy ``profit`` block. Missing or malformed values
    yield ``None``. The ``source_tag`` indicates which block contributed the
    values (``JSON:profit_monitor``, ``JSON:profit(legacy)``, or ``EMPTY``).
    """

    single_val: Optional[float] = None
    portf_val: Optional[float] = None
    src = "EMPTY"

    canonical_single = _get(cfg, "profit_monitor.position_profit_usd")
    canonical_portf = _get(cfg, "profit_monitor.portfolio_profit_usd")

    if canonical_single is not None:
        try:
            single_val = float(canonical_single)
        except Exception:
            single_val = None
    if canonical_portf is not None:
        try:
            portf_val = float(canonical_portf)
        except Exception:
            portf_val = None

    if single_val is not None or portf_val is not None:
        src = "JSON:profit_monitor"

    if single_val is None or portf_val is None:
        legacy_single = _get(cfg, "profit.position_profit_usd")
        legacy_portf = _get(cfg, "profit.portfolio_profit_usd")
        if legacy_portf is None:
            legacy_portf = _get(cfg, "profit.portfolio_usd")

        if single_val is None and legacy_single is not None:
            try:
                single_val = float(legacy_single)
                src = "JSON:profit(legacy)"
            except Exception:
                pass
        if portf_val is None and legacy_portf is not None:
            try:
                portf_val = float(legacy_portf)
                src = "JSON:profit(legacy)"
            except Exception:
                pass

    if single_val is None and portf_val is None:
        src = "EMPTY"

    return single_val, portf_val, src


def resolve_liquid_thresholds(cfg: Dict[str, Any]) -> Tuple[Dict[str, Optional[float]], str]:
    """
    Return a mapping ``{"BTC": float|None, ...}`` and a ``source_tag``.

    Prefers ``liquid_monitor.thresholds`` and falls back to the legacy
    ``liquid.thresholds`` block. Missing values become ``None`` and the source
    is reported as ``JSON:liquid_monitor``, ``JSON:liquid(legacy)``, or
    ``EMPTY``.
    """

    thresholds = _get(cfg, "liquid_monitor.thresholds")
    src = "JSON:liquid_monitor" if isinstance(thresholds, dict) and thresholds else "EMPTY"

    if not isinstance(thresholds, dict) or not thresholds:
        thresholds = _get(cfg, "liquid.thresholds")
        if isinstance(thresholds, dict) and thresholds:
            src = "JSON:liquid(legacy)"
        else:
            thresholds = {}
            src = "EMPTY"

    out: Dict[str, Optional[float]] = {}
    for sym in ("BTC", "ETH", "SOL"):
        value = thresholds.get(sym) if isinstance(thresholds, dict) else None
        if value is None:
            out[sym] = None
            continue
        try:
            out[sym] = float(value)
        except Exception:
            out[sym] = None
    return out, src
