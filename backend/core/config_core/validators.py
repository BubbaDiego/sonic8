from __future__ import annotations
from typing import Dict, List, Tuple, Any

def validate_sonic_monitor(cfg: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Lightweight structural/type checks for sonic_monitor.
    Returns (errors, warnings). Keep it fast; console shows these inline.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(cfg, dict):
        return (["config must be an object"], warnings)

    # monitor
    mon = cfg.get("monitor", {})
    if not isinstance(mon, dict):
        errors.append("monitor must be an object")
    else:
        if not isinstance(mon.get("loop_seconds", 30), (int, float)):
            errors.append("monitor.loop_seconds must be a number")
        en = mon.get("enabled", {})
        if not isinstance(en, dict):
            errors.append("monitor.enabled must be an object")

    # notifications helper
    def _check_notifs(prefix: str, obj: Any):
        if not isinstance(obj, dict):
            errors.append(f"{prefix} must be an object")
            return
        for k in ("system", "voice", "sms", "tts"):
            if k in obj and not isinstance(obj[k], bool):
                errors.append(f"{prefix}.{k} must be boolean")

    for sec in ("liquid", "profit", "market", "price"):
        section = cfg.get(sec, {})
        if isinstance(section, dict) and "notifications" in section:
            _check_notifs(f"{sec}.notifications", section.get("notifications", {}))

    # liquid_monitor.thresholds numbers
    lm = cfg.get("liquid_monitor", {})
    if isinstance(lm, dict):
        th = lm.get("thresholds", {})
        if isinstance(th, dict):
            for k, v in th.items():
                if not isinstance(v, (int, float)):
                    errors.append(f"liquid_monitor.thresholds.{k} must be a number")
        else:
            errors.append("liquid_monitor.thresholds must be an object")

    # profit_monitor.snooze_seconds number if present
    pm = cfg.get("profit_monitor", {})
    if isinstance(pm, dict) and "snooze_seconds" in pm:
        if not isinstance(pm.get("snooze_seconds"), (int, float)):
            errors.append("profit_monitor.snooze_seconds must be a number")

    return errors, warnings
