#!/usr/bin/env python3
"""Data migration helper for per-asset liquidation thresholds and per-monitor channels."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

DEFAULT_ASSETS: Tuple[str, ...] = ("BTC", "ETH", "SOL")
CHANNEL_MONITORS: Tuple[str, ...] = ("liquid", "profit", "market", "price")
CHANNEL_KEYS: Tuple[str, ...] = ("system", "voice", "sms", "tts")
DEFAULT_THRESHOLD = 5.0
DEFAULT_ASSET_THRESHOLDS = {asset: DEFAULT_THRESHOLD for asset in DEFAULT_ASSETS}

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:  # Keep defaults aligned with runtime monitor
    from backend.core.monitor_core.liquidation_monitor import LiquidationMonitor  # type: ignore

    DEFAULT_THRESHOLD = float(getattr(LiquidationMonitor, "DEFAULT_THRESHOLD", DEFAULT_THRESHOLD))
    DEFAULT_ASSET_THRESHOLDS = {
        key: float(value)
        for key, value in getattr(LiquidationMonitor, "DEFAULT_ASSET_THRESHOLDS", DEFAULT_ASSET_THRESHOLDS).items()
    }
    if DEFAULT_ASSET_THRESHOLDS:
        DEFAULT_ASSETS = tuple(DEFAULT_ASSET_THRESHOLDS.keys())
except Exception:  # pragma: no cover - best effort import
    pass
DEFAULT_CONFIG_PATH = ROOT / "backend" / "config" / "sonic_monitor_config.json"
DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_DB_PATH = Path(os.getenv("SONIC_DB_PATH") or (ROOT / "backend" / "mother.db"))


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle) or {}
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[warn] Failed to read JSON {path}: {exc}")
        return {}


def _dump_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=False) + "\n"


def _save_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(_dump_json(data), encoding="utf-8")
    tmp_path.replace(path)


def _normalize_thresholds(thresholds: Dict[str, Any]) -> Dict[str, float]:
    normalized: Dict[str, float] = {}
    for key, value in thresholds.items():
        asset = str(key).upper()
        try:
            normalized[asset] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def _migrate_liquid_section(liquid: Dict[str, Any]) -> bool:
    changed = False
    thresholds = liquid.get("thresholds")
    if isinstance(thresholds, dict):
        normalized = _normalize_thresholds(thresholds)
    else:
        normalized = {}
        if thresholds not in (None, {}):
            changed = True
    if normalized != thresholds:
        liquid["thresholds"] = normalized
        changed = True

    raw_global = liquid.pop("threshold_percent", None)
    global_value: float | None
    if raw_global is None:
        global_value = None
    else:
        changed = True
        try:
            global_value = float(raw_global)
        except (TypeError, ValueError):
            global_value = None

    for asset in DEFAULT_ASSETS:
        default_value = DEFAULT_ASSET_THRESHOLDS.get(asset, DEFAULT_THRESHOLD)
        current = normalized.get(asset)
        if global_value is not None:
            if current is None or abs(current - default_value) < 1e-9:
                if current != global_value:
                    normalized[asset] = global_value
                    changed = True
        else:
            if current is None:
                normalized[asset] = default_value
                changed = True

    liquid["thresholds"] = normalized
    return changed


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _migrate_channels_section(channels: Dict[str, Any]) -> bool:
    changed = False
    global_block = channels.pop("global", None)
    global_copy = {k: _bool(v) for k, v in (global_block or {}).items() if k in CHANNEL_KEYS}
    if global_block is not None:
        changed = True

    for monitor in CHANNEL_MONITORS:
        block = channels.get(monitor)
        if not isinstance(block, dict):
            block = {}
            channels[monitor] = block
            changed = True
        for key in CHANNEL_KEYS:
            if key not in block:
                if key in global_copy:
                    block[key] = global_copy[key]
                    changed = True
            else:
                coerced = _bool(block[key])
                if block[key] is not coerced:
                    block[key] = coerced
                    changed = True

    return changed


def migrate_config(path: Path) -> bool:
    cfg = _load_json(path)
    if not cfg:
        print(f"[info] Config JSON missing or empty at {path}; nothing to migrate")
        return False

    original = _dump_json(cfg)
    liquid = cfg.setdefault("liquid", {}) if isinstance(cfg.get("liquid"), dict) else cfg.setdefault("liquid", {})
    channels = cfg.setdefault("channels", {}) if isinstance(cfg.get("channels"), dict) else cfg.setdefault("channels", {})

    liq_changed = _migrate_liquid_section(liquid)
    ch_changed = _migrate_channels_section(channels)

    if not (liq_changed or ch_changed):
        print("[info] Config JSON already up to date")
        return False

    if _dump_json(cfg) != original:
        _save_json_atomic(path, cfg)
        print(f"[ok] Updated {path}")
        return True

    print("[info] Config JSON had no net changes after migration")
    return False


def migrate_env(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if "LIQ_MON_THRESHOLD_PERCENT" not in text:
        return False
    new_lines: list[str] = []
    changed = False
    for line in text.splitlines():
        if "LIQ_MON_THRESHOLD_PERCENT" in line and not line.strip().startswith("#"):
            new_lines.append("# LIQ_MON_THRESHOLD_PERCENT retired; see scripts/migrate_thresholds_and_channels.py")
            changed = True
        else:
            new_lines.append(line)
    if changed:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"[ok] Commented legacy LIQ_MON_THRESHOLD_PERCENT in {path}")
    return changed


def _load_system_manager(db_path: Path):
    if not db_path.exists():
        return None
    try:
        from backend.data.data_locker import DataLocker  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        print(f"[warn] DataLocker unavailable: {exc}")
        return None
    try:
        locker = DataLocker(str(db_path))
    except Exception as exc:
        print(f"[warn] Unable to open DB at {db_path}: {exc}")
        return None
    return getattr(locker, "system", None)


def migrate_db(db_path: Path) -> bool:
    system_mgr = _load_system_manager(db_path)
    if system_mgr is None:
        return False

    changed = False

    try:
        liquid_cfg = system_mgr.get_var("liquid_monitor") or {}
    except Exception:
        liquid_cfg = {}
    if isinstance(liquid_cfg, dict) and liquid_cfg:
        before = json.loads(json.dumps(liquid_cfg))
        if _migrate_liquid_section(liquid_cfg):
            if liquid_cfg != before:
                system_mgr.set_var("liquid_monitor", liquid_cfg)
                changed = True

    try:
        channels_cfg = system_mgr.get_var("xcom_providers") or {}
        if isinstance(channels_cfg, str):
            channels_cfg = json.loads(channels_cfg)
    except Exception:
        channels_cfg = {}
    if isinstance(channels_cfg, dict) and channels_cfg:
        before = json.loads(json.dumps(channels_cfg))
        if _migrate_channels_section(channels_cfg):
            if channels_cfg != before:
                system_mgr.set_var("xcom_providers", channels_cfg)
                changed = True

    if changed:
        print(f"[ok] Updated system vars in {db_path}")
    else:
        print(f"[info] System vars already up to date in {db_path}")
    return changed


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate liquidation thresholds and notification channels")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to sonic_monitor_config.json")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV_PATH, help="Path to .env file")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to mother.db")
    args = parser.parse_args(list(argv) if argv is not None else None)

    updated = False
    updated |= migrate_config(args.config)
    updated |= migrate_env(args.env)
    updated |= migrate_db(args.db)

    if not updated:
        print("[info] No changes were necessary")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
