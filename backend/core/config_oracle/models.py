# backend/core/config_oracle/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MonitorNotifications:
    """
    Normalized notification flags for a single monitor.

    This matches the per-monitor JSON blocks like:

        "notifications": {
          "system": true,
          "voice": true,
          "sms":   false,
          "tts":   true
        }
    """

    system: bool = True
    voice: bool = False
    sms: bool = False
    tts: bool = False

    def as_dict(self) -> Dict[str, bool]:
        return {
            "system": bool(self.system),
            "voice": bool(self.voice),
            "sms": bool(self.sms),
            "tts": bool(self.tts),
        }


@dataclass
class MonitorDefinition:
    """
    Canonical view of a single monitor's configuration.

    Fields:
      - name: monitor identifier (e.g. "liquid", "profit", "market").
      - enabled: high-level on/off toggle.
      - notifications: system/voice/sms/tts booleans.
      - snooze_seconds: optional per-monitor snooze window.
      - params: monitor-specific knobs (thresholds, blast, profit levels, etc.).
    """

    name: str
    enabled: bool = True
    notifications: MonitorNotifications = field(default_factory=MonitorNotifications)
    snooze_seconds: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitorGlobalConfig:
    """
    Global monitor engine settings.

    Intended to cover things that are not tied to a specific monitor:
      - loop_seconds: main poll interval.
      - global_snooze_seconds: optional global snooze window.
      - xcom_live: whether external channels (voice/Twilio, etc.) are live.
      - console_clear_each_cycle: if True, clear the console at the start of
        each Sonic Monitor console cycle (for a "live dashboard" UI).
    """

    loop_seconds: int = 30
    global_snooze_seconds: Optional[int] = None
    xcom_live: bool = False
    console_clear_each_cycle: bool = False


@dataclass
class MonitorConfigBundle:
    """
    Full monitor configuration as seen by the Oracle.

    This is the normalized, typed view built from the raw JSON (legacy or new
    structure). Callers should prefer this instead of parsing the JSON
    themselves.
    """

    global_config: MonitorGlobalConfig
    monitors: Dict[str, MonitorDefinition] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None  # where the JSON came from, if known

    def get_monitor(self, name: str) -> Optional[MonitorDefinition]:
        return self.monitors.get(name)

    def list_monitors(self) -> list[str]:
        return sorted(self.monitors.keys())


@dataclass
class XComVoiceConfig:
    """
    XCom voice / call configuration.

    This captures the non-secret knobs that other cores can safely read:
      - default_profile: global default voice profile name.
      - monitor_profiles: optional per-monitor overrides (liquid/profit/…).
      - flow_sid: optional Twilio Studio Flow SID (stub, may be None).
      - voice_cooldown_seconds: default cooldown window between calls.
    """

    default_profile: str = "default"
    monitor_profiles: Dict[str, str] = field(default_factory=dict)
    flow_sid: Optional[str] = None
    voice_cooldown_seconds: int = 180

    def profile_for(self, monitor: Optional[str]) -> str:
        """
        Return the voice profile for a given monitor name, falling back
        to the global default when no explicit override is present.
        """
        mon = (monitor or "").lower()
        if mon and mon in self.monitor_profiles:
            return self.monitor_profiles[mon]
        return self.default_profile


@dataclass
class XComTwilioSecrets:
    """
    Twilio credentials + numbers for XCom.

    This is the *secret* side of XCom voice config and is never persisted
    to JSON or the database. It is resolved from environment variables via
    ConfigOracle and then consumed by XComConfigService / dispatch_voice.
    """

    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    from_phone: Optional[str] = None
    to_phones: list[str] = field(default_factory=list)
    flow_sid: Optional[str] = None

    def is_configured(self) -> bool:
        """Return True when we have enough to attempt a real call."""
        return bool(
            (self.account_sid and self.auth_token)
            and self.from_phone
            and self.to_phones
        )


@dataclass
class XComConfig:
    """
    Aggregate XCom configuration.

    Right now this only exposes voice-related knobs, but can be extended
    later with SMS/email/etc as needed.
    """

    voice: XComVoiceConfig = field(default_factory=XComVoiceConfig)
