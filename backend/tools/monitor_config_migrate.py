"""Utility to migrate legacy Sonic monitor JSON configs to the current schema."""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict

LegacyConfig = Dict[str, Any]
ModernConfig = Dict[str, Any]


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_config(path: pathlib.Path) -> LegacyConfig:
    content = path.read_text(encoding="utf-8")
    return json.loads(content)


def _build_liquid_monitor(data: LegacyConfig) -> Dict[str, Any]:
    liquid = data.get("liquid") or {}
    thresholds_src = liquid.get("thresholds") or liquid.get("thr") or {}
    if not isinstance(thresholds_src, dict):
        thresholds_src = {}

    modern_thresholds: Dict[str, float] = {}
    for legacy_key, modern_key in (("BTC", "BTC"), ("ETH", "ETH"), ("SOL", "SOL")):
        value = _coerce_float(thresholds_src.get(legacy_key))
        if value is not None:
            modern_thresholds[modern_key] = value

    monitor: Dict[str, Any] = {"thresholds": modern_thresholds}

    percent_val = liquid.get("threshold_percent") or liquid.get("percent")
    percent = _coerce_float(percent_val)
    if percent is not None:
        monitor["threshold_percent"] = percent

    return monitor


def _build_profit_monitor(data: LegacyConfig) -> Dict[str, Any]:
    profit = data.get("profit") or {}

    monitor: Dict[str, Any] = {}

    position_val = (
        profit.get("position_profit_usd")
        or profit.get("single_usd")
        or profit.get("pos")
    )
    position = _coerce_float(position_val)
    if position is not None:
        monitor["position_profit_usd"] = position

    portfolio_val = (
        profit.get("portfolio_profit_usd")
        or profit.get("total_usd")
        or profit.get("pf")
    )
    portfolio = _coerce_float(portfolio_val)
    if portfolio is not None:
        monitor["portfolio_profit_usd"] = portfolio

    return monitor


def migrate_config(data: LegacyConfig) -> ModernConfig:
    modern: ModernConfig = {}
    modern["liquid_monitor"] = _build_liquid_monitor(data)
    modern["profit_monitor"] = _build_profit_monitor(data)
    return modern


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python backend/tools/monitor_config_migrate.py <config.json>")
        return 2

    path = pathlib.Path(argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"❌ Config file not found: {path}")
        return 1

    try:
        legacy = _load_config(path)
    except Exception as exc:  # pragma: no cover - I/O guard
        print(f"❌ Failed to read {path}: {exc}")
        return 1

    modern = migrate_config(legacy)

    try:
        path.write_text(json.dumps(modern, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:  # pragma: no cover - I/O guard
        print(f"❌ Failed to write {path}: {exc}")
        return 1

    print(f"✅ Migrated {path} to modern schema")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main(sys.argv))
