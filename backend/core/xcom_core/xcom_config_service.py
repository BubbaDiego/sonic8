from __future__ import annotations

from typing import Any, Dict, Mapping

from backend.core import config_oracle as ConfigOracle


def _ensure_bool_map(m: Mapping[str, Any] | None) -> dict[str, bool]:
    out = {"voice": False, "system": False, "sms": False, "tts": False}
    if not isinstance(m, Mapping):
        return out
    for k in ("voice", "system", "sms", "tts"):
        v = m.get(k)
        out[k] = bool(v)
    return out


class XComConfigService:
    """
    Resolve effective XCOM settings from loaded JSON config with user rule:

        • If a per-monitor mapping exists (channels.<monitor> or <monitor>.notifications),
          IGNORE the global channels.voice toggle completely.
        • Only when there is NO per-monitor mapping do we consider channels.voice.enabled.

    Also exposes get_provider(name) to retrieve provider configuration. VoiceService
    will still respect environment variables, so returning {} is acceptable.
    """

    def __init__(self, system: Any | None = None, *, config: Mapping[str, Any] | None = None) -> None:
        self.system = system
        self.config: Mapping[str, Any] = (
            config if isinstance(config, Mapping) else self._extract_cfg_from_system(system)
        ) or {}

    # ---------------- internal ----------------

    @staticmethod
    def _extract_cfg_from_system(system: Any | None) -> Mapping[str, Any] | None:
        if system is None:
            return None
        # common places to find the loaded JSON
        for attr in ("global_config", "config"):
            cfg = getattr(system, attr, None)
            if isinstance(cfg, Mapping):
                return cfg
        # try to walk to DataLocker
        for dl_attr in ("dl", "locker", "data_locker"):
            dl = getattr(system, dl_attr, None)
            if dl is None:
                continue
            cfg = getattr(dl, "global_config", None)
            if isinstance(cfg, Mapping):
                return cfg
        return None

    # ---------------- public ----------------

    def channels_for(self, monitor_name: str) -> dict[str, bool]:
        """
        Return effective per-monitor channel booleans with keys:
            {"voice": bool, "system": bool, "sms": bool, "tts": bool}

        Priority (highest to lowest):
          1) <monitor>.notifications (e.g., config["liquid"]["notifications"])
          2) channels.<monitor> (e.g., config["channels"]["liquid"])
          3) channels.voice.enabled — ONLY IF 1) and 2) are both absent
          4) default all False
        """
        cfg = self.config or {}
        mkey = str(monitor_name).strip()

        # 1) <monitor>.notifications
        sect = cfg.get(mkey)
        if isinstance(sect, Mapping):
            notif = sect.get("notifications")
            if isinstance(notif, Mapping):
                return _ensure_bool_map(notif)

        # 2) channels.<monitor>
        channels = cfg.get("channels")
        if isinstance(channels, Mapping):
            per = channels.get(mkey)
            if isinstance(per, Mapping):
                return _ensure_bool_map(per)

            # Only if there is NO per-monitor mapping do we consider global channels.voice
            v = channels.get("voice")
            if isinstance(v, Mapping) and ("enabled" in v):
                return _ensure_bool_map({"voice": bool(v.get("enabled"))})

        # 3) fall back: nothing configured -> all False
        return {"voice": False, "system": False, "sms": False, "tts": False}

    def _merge_voice_from_env(self, providers: Dict[str, Any]) -> Dict[str, Any]:
        """Overlay Twilio voice config with secrets from ConfigOracle/env.

        This keeps all TWILIO_* resolution in one place (ConfigOracle) so
        callers don't need to know the specific env variable names.
        """
        voice = providers.get("voice")
        if not isinstance(voice, dict):
            if voice is None:
                voice = {}
            elif isinstance(voice, Mapping):
                voice = dict(voice)
            else:
                voice = {}
        providers["voice"] = voice

        # Ask ConfigOracle for Twilio secrets (env-backed).
        try:
            secrets = ConfigOracle.get_xcom_twilio_secrets()
        except Exception:
            secrets = None

        if secrets is not None:
            if secrets.account_sid:
                voice["account_sid"] = secrets.account_sid
            if secrets.auth_token:
                voice["auth_token"] = secrets.auth_token
            if secrets.from_phone:
                voice["from"] = secrets.from_phone
            if secrets.to_phones:
                # Always treat 'to' as a list; use Oracle/env as canonical.
                voice["to"] = list(secrets.to_phones)
            if secrets.flow_sid:
                voice["flow_sid"] = secrets.flow_sid

        providers["voice"] = voice
        return providers

    def get_provider(self, name: str) -> dict[str, Any]:
        """
        Return provider config for 'twilio' or 'api' if present in config.
        VoiceService will still respect environment variables, so {} is acceptable here.
        """
        cfg = self.config or {}

        # Prefer explicit providers section
        providers = cfg.get("providers")
        if isinstance(providers, Mapping):
            merged = self._merge_voice_from_env(dict(providers))
            p = merged.get(name)
            if isinstance(p, Mapping):
                return dict(p)

        # Legacy: some configs tuck the voice provider under channels.voice.provider
        ch = cfg.get("channels")
        if isinstance(ch, Mapping):
            voice = ch.get("voice")
            if isinstance(voice, Mapping):
                if str(voice.get("provider", "")).strip().lower() == name.lower():
                    # merge any 'config' dict under voice into provider data
                    data = dict(voice.get("config") or {})
                    data["enabled"] = bool(voice.get("enabled", True))
                    if name == "voice":
                        data = self._merge_voice_from_env({"voice": data}).get("voice", data)
                    return data

        return {}
