from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from backend.core.core_constants import (
    ALERT_THRESHOLDS_PATH,
    SONIC_MONITOR_CONFIG_PATH,
)
from backend.models.alert import AlertLog

logger = logging.getLogger("sonic.engine")


class ConfigError(Exception):
    pass


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _map_monitor_json_to_legacy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Map ``sonic_monitor_config.json`` into Cyclone's legacy shape."""

    liq = cfg.get("liquid_monitor") or {}
    thr = (liq.get("thresholds") or {}) if isinstance(liq, dict) else {}

    prof_cfg = cfg.get("profit_monitor") or {}
    pos_usd = prof_cfg.get("position_profit_usd", 10.0)
    port_usd = prof_cfg.get("portfolio_profit_usd", 40.0)

    try:
        pos_usd = float(pos_usd)
    except Exception:
        pos_usd = 10.0

    try:
        port_usd = float(port_usd)
    except Exception:
        port_usd = 40.0

    if not isinstance(thr, dict):
        thr = {}

    return {
        "thresholds": thr,
        "profit": {
            "position_profit_usd": pos_usd,
            "portfolio_profit_usd": port_usd,
        },
    }


def _append_missing_log(
    log_store: Optional[Any],
    path: Path,
) -> None:
    if not log_store:
        return

    log_store.append(
        AlertLog(
            id=str(datetime.utcnow().timestamp()),
            alert_id=None,
            phase="CONFIG",
            level="ERROR",
            message=f"missing config {path}",
            payload=None,
            timestamp=datetime.utcnow(),
        )
    )


def load_thresholds(
    path: Path | str = ALERT_THRESHOLDS_PATH,
    log_store: Optional[Any] = None,
) -> Dict[str, Any]:
    """Load Cyclone thresholds with legacy + monitor-config fallback."""

    legacy_path = Path(path)

    if legacy_path.exists():
        try:
            data = _read_json(legacy_path)
            logger.info("[cyclone] thresholds: loaded legacy file: %s", str(legacy_path))
            data.setdefault("thresholds", {})
            data.setdefault("profit", {})
            return data
        except Exception as exc:  # pragma: no cover - best-effort logging
            logger.info(
                "[cyclone] thresholds: legacy read failed (%s), trying monitor config",
                exc,
            )

    monitor_path = SONIC_MONITOR_CONFIG_PATH
    if monitor_path.exists():
        try:
            cfg = _read_json(monitor_path)
            mapped = _map_monitor_json_to_legacy(cfg)
            logger.info(
                "[cyclone] thresholds: mapped from monitor config: %s",
                str(monitor_path),
            )
            return mapped
        except Exception as exc:  # pragma: no cover - best-effort logging
            logger.info(
                "[cyclone] thresholds: monitor-config read failed: %s",
                exc,
            )

    _append_missing_log(log_store, legacy_path)
    raise ConfigError(str(legacy_path))


__all__ = ["ConfigError", "load_thresholds"]
