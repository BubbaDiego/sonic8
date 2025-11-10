from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class ResolutionTrace:
    monitor: str
    key: str
    value: float
    source: str
    layer: str
    evidence: str


class ThresholdResolver:
    """Centralized resolver for monitor thresholds with trace logging."""

    def __init__(self, cfg: Dict[str, Any], dl: Any, logger: Optional[logging.Logger] = None) -> None:
        self.cfg = cfg or {}
        self.dl = dl
        self.logger = logger or logging.getLogger("sonic.resolver")

    # --------- helpers
    def _file_obj(self, path: Tuple[str, ...]) -> Optional[Any]:
        cur: Any = self.cfg
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        return cur

    def _db_alert_thresholds(self) -> Dict[str, Any]:
        """Best-effort read of DB alert thresholds JSON (if present)."""
        try:
            cur = getattr(getattr(self.dl, "db", None), "get_cursor", None)
            if callable(cur):
                c = cur()
                c.execute(
                    "SELECT payload FROM alert_thresholds ORDER BY rowid DESC LIMIT 1"
                )
                row = c.fetchone()
                if row and row[0]:
                    return json.loads(row[0])
        except Exception:
            pass
        return {}

    def _emit(self, trace: ResolutionTrace) -> ResolutionTrace:
        try:
            if self.logger:
                self.logger.info(
                    "[resolve] %s %s -> %s (%s %s)",
                    trace.monitor,
                    trace.key,
                    trace.value,
                    trace.source,
                    trace.layer,
                )
        except Exception:
            pass
        return trace

    # --------- public API
    def liquid_threshold(self, sym: str) -> Tuple[float, ResolutionTrace]:
        # 1) FILE (preferred)
        v = self._file_obj(("liquid_monitor", "thresholds")) or {}
        if isinstance(v, dict) and sym in v:
            val = float(v[sym])
            trace = ResolutionTrace(
                "liquid",
                sym,
                val,
                "FILE",
                f"liquid_monitor.thresholds.{sym}",
                "panel_config.json or main config",
            )
            return val, self._emit(trace)

        # 2) FILE (legacy branch)
        v = self._file_obj(("liquid", "thresholds")) or {}
        if isinstance(v, dict) and sym in v:
            val = float(v[sym])
            trace = ResolutionTrace(
                "liquid",
                sym,
                val,
                "FILE",
                f"liquid.thresholds.{sym}",
                "panel_config.json or main config",
            )
            return val, self._emit(trace)

        # 3) DB alert_thresholds
        dbt = self._db_alert_thresholds()
        t = (dbt.get("thresholds") or {}).get(sym)
        if t is not None:
            val = float(t)
            trace = ResolutionTrace(
                "liquid",
                sym,
                val,
                "DB",
                f"alert_thresholds.thresholds.{sym}",
                "DB: alert_thresholds",
            )
            return val, self._emit(trace)

        # 4) ENV (explicit overrides only)
        env = os.getenv(f"LIQ_{sym}_THRESH")
        if env:
            val = float(env)
            trace = ResolutionTrace(
                "liquid",
                sym,
                val,
                "ENV",
                f"LIQ_{sym}_THRESH",
                "process env",
            )
            return val, self._emit(trace)

        # 5) DEFAULT
        defaults = {"BTC": 5.3, "ETH": 111.0, "SOL": 11.5}
        val = float(defaults.get(sym, 1.0))
        trace = ResolutionTrace(
            "liquid",
            sym,
            val,
            "DEFAULT",
            f"default.{sym}",
            "coded default",
        )
        return val, self._emit(trace)

    def profit_limit(self, key: str) -> Tuple[float, ResolutionTrace]:
        # keys: "position_profit_usd" | "portfolio_profit_usd"
        # 1) FILE
        v = self._file_obj(("profit_monitor", key))
        if v is not None:
            val = float(v)
            trace = ResolutionTrace(
                "profit",
                key,
                val,
                "FILE",
                f"profit_monitor.{key}",
                "panel_config.json or main config",
            )
            return val, self._emit(trace)

        # 2) DB alert_thresholds
        dbt = self._db_alert_thresholds()
        t = (dbt.get("profit") or {}).get(key)
        if t is not None:
            val = float(t)
            trace = ResolutionTrace(
                "profit",
                key,
                val,
                "DB",
                f"alert_thresholds.profit.{key}",
                "DB: alert_thresholds",
            )
            return val, self._emit(trace)

        # 3) ENV
        env = os.getenv(f"PROFIT_{key}".upper())
        if env:
            val = float(env)
            trace = ResolutionTrace(
                "profit",
                key,
                val,
                "ENV",
                f"PROFIT_{key}".upper(),
                "process env",
            )
            return val, self._emit(trace)

        # 4) DEFAULTS
        defaults = {"position_profit_usd": 10.0, "portfolio_profit_usd": 40.0}
        val = float(defaults[key])
        trace = ResolutionTrace(
            "profit",
            key,
            val,
            "DEFAULT",
            f"default.{key}",
            "coded default",
        )
        return val, self._emit(trace)
