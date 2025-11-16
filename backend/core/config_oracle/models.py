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
    """

    loop_seconds: int = 30
    global_snooze_seconds: Optional[int] = None
    xcom_live: bool = False


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
