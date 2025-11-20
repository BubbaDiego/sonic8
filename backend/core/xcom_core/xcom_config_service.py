from __future__ import annotations

from typing import Any, Dict, Mapping

import backend.core.config_core.sonic_config_bridge as C
from backend.utils.env_utils import _resolve_env

from backend.core import config_oracle as ConfigOracle


def _ensure_bool_map(m: Mapping[str, Any] | None) -> dict[str, bool]:
    out = {"voice": False, "system": False, "sms": False, "tts": False}
    if not isinstance(m, Mapping):
        return out
    for k in ("voice", "system", "sms", "tts"):
        v = m.get(k)
        out[k] = bool(v)
    return out


def _resolve_env_values(val: Any) -> Any:
    if isinstance(val, Mapping):
        return {k: _resolve_env_values(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_resolve_env_values(v) for v in val]
    if isinstance(val, tuple):
        return tuple(_resolve_env_values(v) for v in val)
    if isinstance(val, str):
        return _resolve_env(val, None)
    return val


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
        for candidate in (system, getattr(system, "system", None)):
            getter = getattr(candidate, "get_var", None)
            if callable(getter):
                cfg = getter("xcom_providers")
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

    def _get_provider_map(self) -> Mapping[str, Any]:
        for candidate in (self.system, getattr(self.system, "system", None)):
            getter = getattr(candidate, "get_var", None)
            if callable(getter):
                try:
                    cfg = getter("xcom_providers")
                    if isinstance(cfg, Mapping):
                        return cfg
                except Exception:
                    continue
        cfg = self.config or {}
        if cfg:
            return cfg
        return {}

    # ---------------- public ----------------

    def _channels_for_legacy(self, monitor_name: str) -> dict[str, bool]:
        """
        Legacy channel resolution: reads notification flags directly from the
        raw config mapping (self.config) using the historical rules:
          - <monitor>.notifications.{system,voice,sms,tts}
          - channels.<monitor> fallbacks
          - channels.voice.enabled as global voice fallback
        """
        cfg = self._get_provider_map() or {}
        mkey = str(monitor_name).strip()

        # 1) <monitor>.notifications
        sect = cfg.get(mkey)
        if isinstance(sect, Mapping):
            notif = sect.get("notifications")
            if isinstance(notif, Mapping):
                return _ensure_bool_map(notif)
            return _ensure_bool_map(sect)

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

    def channels_for(self, monitor_name: str) -> dict[str, bool]:
        """
        Resolve notification channels for a monitor.

        Oracle-first:
          • Ask ConfigOracle for MonitorNotifications (typed, from sonic_monitor_config.json).
          • If Oracle returns a value, convert it to the canonical dict:
                {"system": bool, "voice": bool, "sms": bool, "tts": bool}
          • If Oracle is unavailable or returns nothing, fall back to the
            legacy JSON logic via _channels_for_legacy().

        This keeps ConfigOracle as the single hub for monitor notification
        policy while preserving the old behavior as a safety net.
        The returned mapping also includes "live" when available to mirror
        legacy behavior for callers that gate voice/tts on that flag.
        """
        name = (monitor_name or "").strip()
        if not name:
            # Degenerate case: no monitor name, use legacy behavior.
            return self._channels_for_legacy(monitor_name)

        notif = None
        try:
            # ConfigOracle.get_monitor_notifications() returns a MonitorNotifications
            # dataclass (or similar) for known monitors.
            notif = ConfigOracle.get_monitor_notifications(name)
        except Exception:
            # If Oracle is not initialized or throws, we silently fall back.
            notif = None

        if notif is not None:
            # Prefer an as_dict() helper if available on the dataclass.
            if hasattr(notif, "as_dict"):
                data = notif.as_dict()  # type: ignore[assignment]
            else:
                data = {
                    "system": getattr(notif, "system", False),
                    "voice": getattr(notif, "voice", False),
                    "sms": getattr(notif, "sms", False),
                    "tts": getattr(notif, "tts", False),
                }

            # Normalize to pure bools and ensure all keys are present.
            data = {
                "system": bool(data.get("system")),
                "voice": bool(data.get("voice")),
                "sms": bool(data.get("sms")),
                "tts": bool(data.get("tts")),
            }
        else:
            # Oracle had no opinion (unknown monitor, missing config, or error).
            # Fall back to the old config mapping behavior.
            data = self._channels_for_legacy(monitor_name)

        try:
            data["live"] = bool(C.get_xcom_live())
        except Exception:
            data["live"] = False

        if data.get("live") is False:
            data["voice"] = False
            data["tts"] = False

        try:
            legacy_channels = self._channels_for_legacy(monitor_name)
            for key in ("system", "voice", "sms", "tts"):
                if legacy_channels.get(key):
                    data[key] = True
        except Exception:
            pass

        return data

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
        cfg = self._get_provider_map() or {}

        # Prefer explicit providers section
        providers = cfg.get("providers")
        if not isinstance(providers, Mapping):
            providers = cfg if isinstance(cfg, Mapping) else {}

        if isinstance(providers, Mapping):
            merged = self._merge_voice_from_env(dict(providers))
            alias_map = {"api": "twilio"}
            target = merged.get(name)
            if target is None:
                target = merged.get(alias_map.get(name, ""))
            if isinstance(target, Mapping):
                return _resolve_env_values(dict(target))

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
