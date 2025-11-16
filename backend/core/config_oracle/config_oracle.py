# backend/core/config_oracle/config_oracle.py
from __future__ import annotations

from threading import RLock
from typing import Any, Dict, Optional

from backend.core.core_constants import SONIC_MONITOR_CONFIG_PATH
from backend.config import config_loader

from .domains import monitor_limits
from .models import (
    MonitorConfigBundle,
    MonitorDefinition,
    MonitorGlobalConfig,
    MonitorNotifications,
)


class ConfigOracle:
    """
    Central configuration oracle for Sonic.

    For now, this class focuses on Sonic Monitor configuration, using
    backend/config/sonic_monitor_config.json (or SONIC_MONITOR_CONFIG_PATH
    when provided) as the underlying source of truth. 

    Other cores should prefer calling into this Oracle rather than reading
    JSON, environment variables, or DB tables directly. Over time, additional
    domains (perps limits, wallet limits, etc.) can be layered on here.
    """

    def __init__(self, monitor_json_path: Optional[str] = None) -> None:
        # Resolve the monitor JSON path once using core_constants, which already
        # honors the SONIC_MONITOR_CONFIG_PATH environment variable.
        self._monitor_json_path: str = str(
            monitor_json_path or SONIC_MONITOR_CONFIG_PATH
        )

        self._monitor_bundle: Optional[MonitorConfigBundle] = None
        self._monitor_raw: Optional[Dict[str, Any]] = None
        self._monitor_path: Optional[str] = None
        self._lock = RLock()

    # --- Internal loading helpers -------------------------------------------

    def _load_monitor_bundle(self, force: bool = False) -> MonitorConfigBundle:
        """
        Internal: load and parse the monitor config bundle.

        Uses the JSON-only helpers in backend.config.config_loader to avoid
        pulling in DB/env overlays for this specific CONFIG JSON. 
        """
        with self._lock:
            if self._monitor_bundle is not None and not force:
                return self._monitor_bundle

            cfg, path = config_loader.load_monitor_config(
                json_path=self._monitor_json_path
            )
            bundle = monitor_limits.build_monitor_bundle_from_raw(cfg)
            bundle.source_path = str(path)

            self._monitor_raw = cfg
            self._monitor_path = str(path)
            self._monitor_bundle = bundle
            return bundle

    # --- Public monitor API --------------------------------------------------

    def reload_monitors(self) -> MonitorConfigBundle:
        """
        Force a reload of the underlying monitor config JSON.

        Intended for use by admin/console flows; normal runtime callers can
        rely on the lazy-load behavior.
        """
        return self._load_monitor_bundle(force=True)

    def get_monitor_bundle(self) -> MonitorConfigBundle:
        """Return the current MonitorConfigBundle (loading it if needed)."""
        return self._load_monitor_bundle(force=False)

    def get_global_monitor_config(self) -> MonitorGlobalConfig:
        """Return global monitor engine configuration."""
        return self.get_monitor_bundle().global_config

    def list_monitors(self) -> list[str]:
        """Return the list of monitor names known to the Oracle."""
        return self.get_monitor_bundle().list_monitors()

    def get_monitor(self, name: str) -> Optional[MonitorDefinition]:
        """Return the MonitorDefinition for `name`, if known."""
        return self.get_monitor_bundle().get_monitor(name)

    def get_monitor_notifications(self, name: str) -> MonitorNotifications:
        """
        Return notification settings for a specific monitor.

        If the monitor is unknown, return all defaults (system=True, others False)
        instead of raising.
        """
        mon = self.get_monitor(name)
        if mon is None:
            return MonitorNotifications()
        return mon.notifications

    # --- Domain-specific helpers: Sonic Monitor limits ----------------------

    def get_liquid_thresholds(self) -> Dict[str, float]:
        """
        Return liquidation thresholds per asset symbol.

        Output shape: { "BTC": 1.3, "ETH": 1.0, ... }

        Works with both:
          - legacy JSON (liquid.thresholds or liquid_monitor.thresholds), and
          - new normalized layout (monitors.liquid.params.thresholds).
        """
        mon = self.get_monitor("liquid")
        if mon is None:
            return {}

        thresholds = mon.params.get("thresholds") or {}
        if not isinstance(thresholds, dict):
            return {}

        out: Dict[str, float] = {}
        for sym, val in thresholds.items():
            try:
                if val is None:
                    continue
                out[str(sym)] = float(val)
            except Exception:
                continue
        return out

    def get_liquid_blast_map(self) -> Dict[str, int]:
        """
        Return liquidation blast radius per asset symbol.

        Output shape: { "BTC": 5, "ETH": 5, ... }
        """
        mon = self.get_monitor("liquid")
        if mon is None:
            return {}

        blast = mon.params.get("blast") or {}
        if not isinstance(blast, dict):
            return {}

        out: Dict[str, int] = {}
        for sym, val in blast.items():
            try:
                if val is None:
                    continue
                out[str(sym)] = int(float(val))
            except Exception:
                continue
        return out

    def get_profit_thresholds(self) -> Dict[str, float]:
        """
        Return profit thresholds in USD, if configured.

        Keys:
          - position_profit_usd
          - portfolio_profit_usd

        Values are floats, even if the underlying JSON used ints/strings.
        """
        mon = self.get_monitor("profit")
        if mon is None:
            return {}

        out: Dict[str, float] = {}
        for key in ("position_profit_usd", "portfolio_profit_usd"):
            val = mon.params.get(key)
            if val is None:
                continue
            try:
                out[key] = float(val)
            except Exception:
                continue
        return out

    # --- Introspection ------------------------------------------------------

    @property
    def monitor_json_path(self) -> str:
        """Return the effective monitor JSON path in use."""
        return self._monitor_json_path

    @property
    def last_monitor_raw(self) -> Optional[Dict[str, Any]]:
        """
        Return the last raw monitor JSON dict seen by the Oracle, if loaded.

        Useful for debugging/console tooling; callers MUST treat this as
        read-only.
        """
        return self._monitor_raw

    @property
    def last_monitor_source_path(self) -> Optional[str]:
        """
        Return the last monitor JSON path used by the loader, if known.
        """
        return self._monitor_path
