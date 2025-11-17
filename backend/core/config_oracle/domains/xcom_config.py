# backend/core/config_oracle/domains/xcom_config.py
from __future__ import annotations

from typing import Any, Dict

from ..models import XComConfig, XComVoiceConfig


def _coerce_int(val: Any, default: int) -> int:
    """Loosely coerce a value into a non-negative int, with a default."""
    if val is None:
        return default
    try:
        n = int(float(val))
        return n if n >= 0 else default
    except Exception:
        return default


def build_xcom_config_from_raw(raw: Dict[str, Any]) -> XComConfig:
    """
    Build an XComConfig from the same raw JSON used for monitors.

    Supported layouts (all optional):

      1) New-style XCom section (preferred):

          "xcom": {
            "voice": {
              "default_profile": "default",
              "monitor_profiles": {
                "liquid": "urgent",
                "profit": "calm"
              },
              "flow_sid": null
            },
            "cooldowns": {
              "voice_seconds": 180
            }
          }

      2) Legacy voice cooldown (for backward compatibility):

          "channels": {
            "voice": {
              "cooldown_seconds": 180
            }
          }

    If nothing is configured, sane defaults are returned.
    """
    raw = dict(raw or {})

    # --- Top-level XCom / voice blocks ---

    xroot = raw.get("xcom") or {}
    if not isinstance(xroot, dict):
        xroot = {}

    voice_block = xroot.get("voice") or {}
    if not isinstance(voice_block, dict):
        voice_block = {}

    cooldowns_block = xroot.get("cooldowns") or {}
    if not isinstance(cooldowns_block, dict):
        cooldowns_block = {}

    # --- Voice profile defaults ---

    default_profile = str(voice_block.get("default_profile") or "default")

    monitor_profiles_raw = voice_block.get("monitor_profiles") or {}
    monitor_profiles: Dict[str, str] = {}
    if isinstance(monitor_profiles_raw, dict):
        for name, prof in monitor_profiles_raw.items():
            if prof is None:
                continue
            monitor_profiles[str(name).lower()] = str(prof)

    # --- Flow SID (stub) ---

    flow_sid_raw = voice_block.get("flow_sid")
    flow_sid: str | None
    if flow_sid_raw is None:
        flow_sid = None
    else:
        s = str(flow_sid_raw).strip()
        flow_sid = s or None

    # --- Voice cooldown seconds ---

    # 1) New-style: xcom.cooldowns.voice_seconds
    cooldown_source = cooldowns_block.get("voice_seconds")

    # 2) Legacy: channels.voice.cooldown_seconds
    if cooldown_source is None:
        channels = raw.get("channels") or {}
        if isinstance(channels, dict):
            voice_ch = channels.get("voice") or {}
            if isinstance(voice_ch, dict):
                cooldown_source = voice_ch.get("cooldown_seconds")

    voice_cooldown = _coerce_int(cooldown_source, default=180)

    voice_cfg = XComVoiceConfig(
        default_profile=default_profile,
        monitor_profiles=monitor_profiles,
        flow_sid=flow_sid,
        voice_cooldown_seconds=voice_cooldown,
    )

    return XComConfig(voice=voice_cfg)
