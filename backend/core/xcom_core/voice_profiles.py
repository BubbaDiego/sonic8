from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class VoiceProfile:
    name: str
    engine: str = "twilio"
    twilio_voice: str = "Polly.Joanna"
    twilio_language: str = "en-US"
    tts_voice_name: str = ""
    tts_rate: float = 1.0
    tts_volume: float = 1.0
    prefix: str = ""
    suffix: str = ""

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "VoiceProfile":
        data = dict(data or {})
        return cls(
            name=name,
            engine=data.get("engine", "twilio"),
            twilio_voice=data.get("twilio_voice", "Polly.Joanna"),
            twilio_language=data.get("twilio_language", "en-US"),
            tts_voice_name=data.get("tts_voice_name", ""),
            tts_rate=float(data.get("tts_rate", 1.0)),
            tts_volume=float(data.get("tts_volume", 1.0)),
            prefix=data.get("prefix", ""),
            suffix=data.get("suffix", ""),
        )


def load_voice_profiles(comm_cfg: Dict[str, Any]) -> Dict[str, VoiceProfile]:
    """Build a mapping of profile_name -> VoiceProfile from comm_config.json."""

    raw = (comm_cfg or {}).get("voice_profiles") or {}
    profiles: Dict[str, VoiceProfile] = {}

    for name, data in raw.items():
        profiles[name] = VoiceProfile.from_dict(name, data)

    if not profiles:
        profiles["default"] = VoiceProfile(name="default")

    return profiles


def get_voice_profile(comm_cfg: Dict[str, Any], name: str = "default") -> VoiceProfile:
    """Return the requested profile, or 'default' if the name is unknown."""

    profiles = load_voice_profiles(comm_cfg)
    if name in profiles:
        return profiles[name]
    return profiles.get("default") or VoiceProfile(name="default")
