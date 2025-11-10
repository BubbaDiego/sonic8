from __future__ import annotations

import inspect
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


logger = logging.getLogger("sonic.engine")


@dataclass
class ResolutionTrace:
    monitor: str     # "liquid" | "profit" | ...
    key: str         # e.g. "SOL", "portfolio_profit_usd"
    value: float
    source: str      # "JSON" | "DB" | "ENV" | "DEFAULT"
    layer: str       # exact path: "liquid_monitor.thresholds.SOL"
    evidence: str    # file path / env var / table


def _is_dict(x: Any) -> bool:
    return isinstance(x, dict)


def _maybe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


class ThresholdResolver:
    """
    Single place to resolve monitor limits with a full audit trail.
    JSON -> DB -> ENV -> DEFAULT, with logging and a ResolutionTrace.
    """

    def __init__(self, cfg: Dict[str, Any] | Any, dl: Any, *, cfg_path_hint: Optional[str] = None):
        self.cfg = cfg or {}
        self.dl = dl
        self.cfg_path_hint = cfg_path_hint or self._find_cfg_path(self.cfg)

    # ------------------ JSON helpers ------------------

    def _cfg_get(self, *path: str) -> Optional[Any]:
        """
        Traverse dict-like or attribute-like config structures.
        Returns value or None. Also logs what we tried.
        """
        cursor = self.cfg
        tried = ["cfg"]
        for p in path:
            if _is_dict(cursor) and p in cursor:
                cursor = cursor[p]
                tried.append(p)
                continue
            # attribute-style access
            if hasattr(cursor, p):
                cursor = getattr(cursor, p)
                tried.append(f".{p}")
                continue
            logger.debug("[resolve] JSON path missing at %s -> %s", " -> ".join(path), " / ".join(tried))
            return None
        logger.debug("[resolve] JSON hit   at %s (%s)", " -> ".join(path), self.cfg_path_hint or "<unknown file>")
        return cursor

    def _find_cfg_path(self, cfg: Any) -> Optional[str]:
        """
        Try to infer the config file path for audit purposes.
        Looks at env and common attributes/fields.
        """
        # strong hints first
        for env in ("SONIC_CONFIG_PATH", "CONFIG_PATH", "APP_CONFIG_PATH"):
            if os.getenv(env):
                return os.getenv(env)

        # metadata on cfg (dict)
        if _is_dict(cfg):
            for k in ("config_path", "config_file", "__file__", "file", "path"):
                v = cfg.get(k)
                if isinstance(v, str) and v:
                    return v
            meta = cfg.get("meta") or {}
            v = meta.get("config_path") or meta.get("file")
            if isinstance(v, str) and v:
                return v

        # attribute style
        for k in ("config_path", "config_file", "__file__", "file", "path"):
            if hasattr(cfg, k):
                v = getattr(cfg, k)
                if isinstance(v, str) and v:
                    return v

        # fallback: where this caller lives
        try:
            frm = inspect.getframeinfo(inspect.stack()[2][0])
            return frm.filename
        except Exception:
            return None

    # ------------------ DB helpers ------------------

    def _db_alert_thresholds(self) -> Dict[str, Any]:
        """Load last alert_thresholds payload from DB (if present)."""
        try:
            cur_fn: Optional[Callable] = getattr(getattr(self.dl, "db", None), "get_cursor", None)
            if callable(cur_fn):
                cur = cur_fn()
                cur.execute("SELECT payload FROM alert_thresholds ORDER BY rowid DESC LIMIT 1")
                row = cur.fetchone()
                if row and row[0]:
                    return json.loads(row[0])
        except Exception as e:
            logger.debug("[resolve] DB alert_thresholds read failed: %s", e)
        return {}

    # ------------------ Liquid ------------------

    def liquid_threshold(self, sym: str) -> Tuple[float, ResolutionTrace]:
        # 1) JSON (preferred): liquid_monitor.thresholds.SOL
        v = self._cfg_get("liquid_monitor", "thresholds")
        if _is_dict(v) and sym in v and _maybe_float(v[sym]) is not None:
            val = float(v[sym])
            tr = ResolutionTrace("liquid", sym, val, "JSON",
                                 f"liquid_monitor.thresholds.{sym}",
                                 self.cfg_path_hint or "<unknown json>")
            self._log_trace(tr)
            return val, tr

        # 2) JSON (legacy): liquid.thresholds.SOL
        v = self._cfg_get("liquid", "thresholds")
        if _is_dict(v) and sym in v and _maybe_float(v[sym]) is not None:
            val = float(v[sym])
            tr = ResolutionTrace("liquid", sym, val, "JSON",
                                 f"liquid.thresholds.{sym}",
                                 self.cfg_path_hint or "<unknown json>")
            self._log_trace(tr)
            return val, tr

        # 3) DB alert_thresholds.thresholds.SOL
        dbt = self._db_alert_thresholds()
        t = (dbt.get("thresholds") or {}).get(sym)
        if _maybe_float(t) is not None:
            val = float(t)
            tr = ResolutionTrace("liquid", sym, val, "DB",
                                 f"alert_thresholds.thresholds.{sym}", "DB: alert_thresholds")
            self._log_trace(tr)
            return val, tr

        # 4) ENV LIQ_SOL_THRESH
        env = os.getenv(f"LIQ_{sym}_THRESH")
        if _maybe_float(env) is not None:
            val = float(env)
            tr = ResolutionTrace("liquid", sym, val, "ENV",
                                 f"LIQ_{sym}_THRESH", "process env")
            self._log_trace(tr)
            return val, tr

        # 5) DEFAULT (last resort only)
        defaults = {"BTC": 5.3, "ETH": 111.0, "SOL": 11.5}
        val = float(defaults.get(sym, 1.0))
        tr = ResolutionTrace("liquid", sym, val, "DEFAULT", f"default.{sym}", "coded default")
        self._log_trace(tr)
        return val, tr

    # ------------------ Profit ------------------

    def profit_limit(self, key: str) -> Tuple[float, ResolutionTrace]:
        # 1) JSON profit_monitor.<key>
        v = self._cfg_get("profit_monitor", key)
        if _maybe_float(v) is not None:
            val = float(v)
            tr = ResolutionTrace("profit", key, val, "JSON",
                                 f"profit_monitor.{key}", self.cfg_path_hint or "<unknown json>")
            self._log_trace(tr)
            return val, tr

        # 2) DB alert_thresholds.profit.<key>
        dbt = self._db_alert_thresholds()
        t = (dbt.get("profit") or {}).get(key)
        if _maybe_float(t) is not None:
            val = float(t)
            tr = ResolutionTrace("profit", key, val, "DB",
                                 f"alert_thresholds.profit.{key}", "DB: alert_thresholds")
            self._log_trace(tr)
            return val, tr

        # 3) ENV PROFIT_<KEY>
        env = os.getenv(f"PROFIT_{key}".upper())
        if _maybe_float(env) is not None:
            val = float(env)
            tr = ResolutionTrace("profit", key, val, "ENV",
                                 f"PROFIT_{key}".upper(), "process env")
            self._log_trace(tr)
            return val, tr

        # 4) DEFAULT
        defaults = {"position_profit_usd": 10.0, "portfolio_profit_usd": 40.0}
        val = float(defaults[key])
        tr = ResolutionTrace("profit", key, val, "DEFAULT", f"default.{key}", "coded default")
        self._log_trace(tr)
        return val, tr

    # ------------------ inspectors (for UI) ------------------

    def inspect_liquid(self, sym: str) -> Dict[str, Optional[float]]:
        layers: Dict[str, Optional[float]] = {"json": None, "json_legacy": None, "db": None, "env": None, "default": None}
        v = self._cfg_get("liquid_monitor", "thresholds")
        if _is_dict(v) and sym in v:
            layers["json"] = _maybe_float(v[sym])
        v = self._cfg_get("liquid", "thresholds")
        if _is_dict(v) and sym in v:
            layers["json_legacy"] = _maybe_float(v[sym])
        dbt = self._db_alert_thresholds()
        layers["db"] = _maybe_float((dbt.get("thresholds") or {}).get(sym))
        env = os.getenv(f"LIQ_{sym}_THRESH")
        layers["env"] = _maybe_float(env)
        defaults = {"BTC": 5.3, "ETH": 111.0, "SOL": 11.5}
        layers["default"] = _maybe_float(defaults.get(sym))
        return layers

    def inspect_profit(self, key: str) -> Dict[str, Optional[float]]:
        layers: Dict[str, Optional[float]] = {"json": None, "db": None, "env": None, "default": None}
        v = self._cfg_get("profit_monitor", key)
        layers["json"] = _maybe_float(v)
        dbt = self._db_alert_thresholds()
        layers["db"] = _maybe_float((dbt.get("profit") or {}).get(key))
        env = os.getenv(f"PROFIT_{key}".upper())
        layers["env"] = _maybe_float(env)
        defaults = {"position_profit_usd": 10.0, "portfolio_profit_usd": 40.0}
        layers["default"] = _maybe_float(defaults.get(key))
        return layers

    # ------------------ logging ------------------

    def _log_trace(self, tr: ResolutionTrace) -> None:
        logger.info("[resolve] %s %s -> %.2f (%s %s) cfg=%s",
                    tr.monitor, tr.key, tr.value, tr.source, tr.layer,
                    self.cfg_path_hint or "<unknown>")
