# backend/core/config_oracle/__init__.py
from __future__ import annotations

from typing import Dict, Optional

from .config_oracle import ConfigOracle
from .models import (
    MonitorConfigBundle,
    MonitorDefinition,
    MonitorGlobalConfig,
    MonitorNotifications,
    XComConfig,
    XComVoiceConfig,
    XComTwilioSecrets,
)

# Soft singleton backing the public API for callers.
# Import pattern (recommended):
#   import backend.core.config_oracle as ConfigOracle
#   profit_cfg = ConfigOracle.get_monitor("profit")
#
# This keeps the "ConfigOracle::" vibe without hard-coding a global instance
# inside the class itself.
_default_oracle: Optional[ConfigOracle] = None


def get_oracle() -> ConfigOracle:
    """Return the process-wide ConfigOracle instance (creating it lazily)."""
    global _default_oracle
    if _default_oracle is None:
        _default_oracle = ConfigOracle()
    return _default_oracle


# --- Monitor-config convenience wrappers ------------------------------------


def reload_monitors() -> MonitorConfigBundle:
    """
    Force a reload of the monitor config JSON and return the new bundle.

    Safe to call from a console/CLI or admin path; read-only callers should
    usually stick to get_monitor_bundle().
    """
    return get_oracle().reload_monitors()


def get_monitor_bundle(force_reload: bool = False) -> MonitorConfigBundle:
    """
    Return the parsed monitor config bundle.

    If force_reload is True, re-read the underlying JSON first.
    """
    if force_reload:
        return get_oracle().reload_monitors()
    return get_oracle().get_monitor_bundle()


def get_global_monitor_config() -> MonitorGlobalConfig:
    """Return global monitor engine settings (loop, global snooze, etc.)."""
    return get_oracle().get_global_monitor_config()


def should_clear_console_each_cycle() -> bool:
    """
    Return whether the Sonic Monitor console should clear the screen at the
    start of each cycle.

    This is driven by monitor.console.clear_each_cycle in the monitor config,
    via ConfigOracle's MonitorGlobalConfig.
    """
    try:
        g = get_global_monitor_config()
        return bool(getattr(g, "console_clear_each_cycle", False))
    except Exception:
        return False


def list_monitors() -> list[str]:
    """Return the list of monitor names known to the Oracle."""
    return get_oracle().list_monitors()


def get_monitor(name: str) -> Optional[MonitorDefinition]:
    """Return the MonitorDefinition for a given monitor name, if present."""
    return get_oracle().get_monitor(name)


def get_monitor_notifications(name: str) -> MonitorNotifications:
    """
    Return the notification settings for a given monitor.

    If the monitor is unknown, this returns defaults:
        system=True, voice=False, sms=False, tts=False.
    """
    return get_oracle().get_monitor_notifications(name)


def get_liquid_thresholds() -> Dict[str, float]:
    """
    Return liquidation thresholds per symbol, as {symbol: threshold_float}.

    The oracle normalizes both the legacy JSON layout and the newer
    "monitors.liquid.params.thresholds" layout into this view.
    """
    return get_oracle().get_liquid_thresholds()


def get_liquid_blast_map() -> Dict[str, int]:
    """
    Return liquidation blast radius per symbol, as {symbol: blast_int}.
    """
    return get_oracle().get_liquid_blast_map()


def get_profit_thresholds() -> Dict[str, float]:
    """
    Return profit thresholds, e.g.:

        {
          "position_profit_usd": 10.0,
          "portfolio_profit_usd": 40.0,
        }
    """
    return get_oracle().get_profit_thresholds()


def get_xcom_config() -> XComConfig:
    """
    Return the normalized XCom configuration.

    This includes voice profiles, flow SID (stub), and default
    voice cooldown window.
    """
    return get_oracle().get_xcom_config()


def get_xcom_voice_config() -> XComVoiceConfig:
    """
    Return the voice-related portion of XCom configuration.
    """
    return get_oracle().get_xcom_voice_config()


def get_xcom_flow_sid() -> Optional[str]:
    """
    Return the configured Twilio Flow SID for XCom voice calls, if any.

    When this returns None, the voice dispatcher should fall back to
    plain TwiML-based calls instead of a Studio Flow.
    """
    return get_oracle().get_xcom_flow_sid()


def get_xcom_voice_profile_for_monitor(monitor: str | None) -> str:
    """
    Return the configured voice profile for a given monitor.

    This respects per-monitor overrides and falls back to the global
    default profile name.
    """
    voice_cfg = get_oracle().get_xcom_voice_config()
    return voice_cfg.profile_for(monitor)


def get_xcom_twilio_secrets() -> XComTwilioSecrets:
    """
    Return Twilio credentials/numbers for XCom, resolved from environment.

    Callers MUST treat this as read-only and avoid persisting it.
    """
    return get_oracle().get_xcom_twilio_secrets()


__all__ = [
    "ConfigOracle",
    "get_oracle",
    "reload_monitors",
    "get_monitor_bundle",
    "get_global_monitor_config",
    "should_clear_console_each_cycle",
    "list_monitors",
    "get_monitor",
    "get_monitor_notifications",
    "get_liquid_thresholds",
    "get_liquid_blast_map",
    "get_profit_thresholds",
    "get_xcom_config",
    "get_xcom_voice_config",
    "get_xcom_flow_sid",
    "get_xcom_voice_profile_for_monitor",
    "get_xcom_twilio_secrets",
    "MonitorConfigBundle",
    "MonitorDefinition",
    "MonitorGlobalConfig",
    "MonitorNotifications",
    "XComConfig",
    "XComVoiceConfig",
    "XComTwilioSecrets",
]
