# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Tuple

from backend.core import config_oracle as ConfigOracle

# Services
# These imports are kept so other callers can still use the helpers directly,
# but Sonic Monitor no longer calls prices/positions as services; Cyclone
# handles those via run_cycle().
from .services.prices_service import sync_prices_service        # noqa: F401
from .services.positions_service import sync_positions_service  # noqa: F401
from .services.raydium_service import sync_raydium_service
from .services.hedges_service import sync_hedges_service

# Monitor runners
from .monitors.liquid_runner import run_liquid_monitors
from .monitors.profit_runner import run_profit_monitors
from .monitors.market_runner import run_market_monitors

Service = Callable[[Any], Dict[str, Any]]
Runner = Callable[[Any], Dict[str, Any]]

# NOTE:
#   Prices & positions are now driven via Cyclone.run_cycle() inside
#   MonitorEngine (engine.py). Sonic Monitor no longer invokes the
#   old sync_prices_service / sync_positions_service in its service loop.
DEFAULT_SERVICES: List[Tuple[str, Service]] = [
    ("raydium", sync_raydium_service),
    ("hedges",  sync_hedges_service),
]

DEFAULT_MONITORS: List[Tuple[str, Runner]] = [
    ("liquid", run_liquid_monitors),
    ("profit", run_profit_monitors),
    ("market", run_market_monitors),
]


def _enabled(names: Iterable[str] | None,
             default: List[Tuple[str, Any]]) -> List[Tuple[str, Any]]:
    """Filter default list by an optional list of enabled names."""
    name_set = {n.strip().lower() for n in (names or [])}
    if not name_set:
        return list(default)
    out: List[Tuple[str, Any]] = []
    for n, fn in default:
        if n in name_set:
            out.append((n, fn))
    return out


def get_enabled_services(cfg: Dict[str, Any]) -> List[Tuple[str, Service]]:
    """
    Resolve which services are enabled for this Sonic Monitor run.

    Config shapes supported:
      - { "services.enabled": ["raydium", "hedges"] }
      - { "services": ["raydium", "hedges"] }
      - if neither key is present → all DEFAULT_SERVICES
    """
    names = cfg.get("services.enabled") or cfg.get("services") or []
    return _enabled(names, DEFAULT_SERVICES)


def get_enabled_monitors(cfg: Dict[str, Any]) -> List[Tuple[str, Runner]]:
    """
    Resolve which monitors should be active.

    Priority:
      1) ConfigOracle MonitorDefinitions (preferred)
      2) Legacy JSON keys:
           - monitor.enabled (list)
           - monitor.monitors (list)
           - monitor.enabled (flat)
           - monitors (flat)
    """
    # --- Oracle-first: use typed MonitorDefinitions ---
    try:
        bundle = ConfigOracle.get_monitor_bundle()
        monitors = getattr(bundle, "monitors", {}) or {}
        if monitors:
            enabled: List[Tuple[str, Runner]] = []
            for name, runner in DEFAULT_MONITORS:
                mon_def = monitors.get(name)
                # Default to "on" for unknown monitors, matching historical behavior
                if mon_def is None or bool(mon_def.enabled):
                    enabled.append((name, runner))
            return enabled
    except Exception:  # pragma: no cover - defensive
        # Keep legacy behavior if Oracle is unavailable
        pass

    # --- Legacy JSON behavior ---
    mon_cfg = cfg.get("monitor") or {}
    names: list[str] = (
        mon_cfg.get("enabled")
        or mon_cfg.get("monitors")
        or cfg.get("monitor.enabled")
        or cfg.get("monitors")
        or []
    )
    return _enabled(names, DEFAULT_MONITORS)
