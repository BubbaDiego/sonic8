from __future__ import annotations

import logging
from typing import Any, Dict

from twilio.rest import Client

from backend.core import config_oracle as ConfigOracle
from backend.utils.json_manager import JsonManager, JsonType

from .tts_service import TTSService
from .voice_message_builder import build_xcom_message
from .voice_profiles import get_voice_profile

log = logging.getLogger("sonic.engine")


def _read_providers(dl) -> Dict[str, Any]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return {}
    prov = sysmgr.get_var("xcom_providers") or {}
    if not isinstance(prov, dict):
        return {}
    return prov


def _load_comm_config() -> Dict[str, Any]:
    try:
        manager = JsonManager()
        return manager.load("", JsonType.COMM_CONFIG)
    except Exception:
        return {}


def dispatch_voice(payload: Dict[str, Any],
                   channels: Dict[str, bool],
                   context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a single voice message — POSitional API only:
        dispatch_voice(payload, channels, context)

    payload: { subject, body, label, tts?, ... }
    channels: { voice: True } (others ignored)
    context: { dl: DataLocker, voice: { tts?: str } ... }

    Returns a dict with a lightweight result ({ok: bool, sid?:..., reason?:...}).
    """
    try:
        if not isinstance(context, dict):
            context = {}

        voice_ctx_raw = context.get("voice")
        if isinstance(voice_ctx_raw, dict):
            ctx_voice = dict(voice_ctx_raw)
        else:
            ctx_voice = {}
        context["voice"] = ctx_voice

        dl = context.get("dl")
        if not dl:
            log.info("[xcom.voice] missing DL in context")
            return {"ok": False, "reason": "missing-dl"}
        prov = _read_providers(dl)
        voice_cfg = (prov.get("voice") or {}) if isinstance(prov, dict) else {}
        provider_cfg: Dict[str, Any] = {}
        if isinstance(voice_cfg, dict):
            provider_cfg.update(voice_cfg)

        ctx_provider = ctx_voice.get("provider")
        if isinstance(ctx_provider, dict):
            provider_cfg.update(ctx_provider)

        # Overlay Twilio secrets from ConfigOracle/env so JSON/DB never need
        # to carry SID/token/phone numbers. Oracle/env values win.
        try:
            twilio_secrets = ConfigOracle.get_xcom_twilio_secrets()
        except Exception:
            twilio_secrets = None

        if twilio_secrets is not None:
            if twilio_secrets.account_sid:
                provider_cfg["account_sid"] = twilio_secrets.account_sid
            if twilio_secrets.auth_token:
                provider_cfg["auth_token"] = twilio_secrets.auth_token
            if twilio_secrets.from_phone:
                provider_cfg["from"] = twilio_secrets.from_phone
            if twilio_secrets.to_phones:
                provider_cfg["to"] = list(twilio_secrets.to_phones)

        # Default provider to Twilio when secrets are present
        if twilio_secrets is not None and twilio_secrets.is_configured():
            provider_cfg.setdefault("provider", "twilio")

        enabled = bool(provider_cfg.get("enabled", True))
        if not enabled:
            log.info("[xcom.voice] provider disabled")
            return {"ok": False, "reason": "provider-disabled"}

        provider_name = (provider_cfg.get("provider") or "").lower()
        if provider_name != "twilio":
            log.info("[xcom.voice] unknown provider: %s", provider_name)
            return {"ok": False, "reason": f"unknown-provider:{provider_name}"}

        # Resolve which monitor this event belongs to (if any).
        monitor_name = (payload.get("monitor") or "").strip().lower() or None

        # Oracle-backed voice config (profile, cooldown, etc.)
        try:
            oracle_voice_cfg = ConfigOracle.get_xcom_voice_config()
        except Exception:
            oracle_voice_cfg = None

        # Determine the voice profile to use.
        ctx_voice_profile = ctx_voice.get("profile") or ctx_voice.get("voice_profile")
        explicit_profile = payload.get("voice_profile") or ctx_voice_profile

        oracle_profile_name: str | None = None
        if oracle_voice_cfg is not None:
            oracle_profile_name = oracle_voice_cfg.profile_for(monitor_name)
        else:
            try:
                oracle_profile_name = ConfigOracle.get_xcom_voice_profile_for_monitor(monitor_name)
            except Exception:
                oracle_profile_name = None

        if explicit_profile:
            profile_name = str(explicit_profile)
        elif oracle_profile_name:
            profile_name = oracle_profile_name
        else:
            profile_name = "default"

        # Expose the resolved profile back onto the context for logging/inspection.
        ctx_voice["profile"] = profile_name
        ctx_voice["voice_profile"] = profile_name

        comm_cfg = _load_comm_config()
        profile = get_voice_profile(comm_cfg, str(profile_name))
        tts = build_xcom_message(payload, profile)

        if profile.engine == "local":
            try:
                tts_service = TTSService()
                tts_service.speak(tts, profile=profile)
            except Exception as exc:
                log.info("[xcom.voice] local TTS failed: %s", exc)
                return {
                    "ok": False,
                    "results": [
                        {"mode": "local", "to": "local", "ok": False, "error": str(exc)}
                    ],
                    "error": str(exc),
                }
            return {
                "ok": True,
                "results": [{"mode": "local", "to": "local", "ok": True}],
            }

        sid = provider_cfg.get("account_sid")
        token = provider_cfg.get("auth_token")
        frm = provider_cfg.get("from")
        tos = provider_cfg.get("to") or []

        if isinstance(tos, str):
            tos = [tos]

        if not (sid and token and frm and tos):
            log.info("[xcom.voice] twilio missing config")
            return {"ok": False, "reason": "twilio-missing-config"}

        client = Client(sid, token)

        results = []
        for to in tos:
            try:
                twiml = (
                    f'<Response>'
                    f'<Say voice="{profile.twilio_voice}" language="{profile.twilio_language}">' 
                    f'{tts}'
                    f'</Say>'
                    f'</Response>'
                )
                call = client.calls.create(to=to, from_=frm, twiml=twiml)
                results.append({"to": to, "sid": call.sid, "ok": True, "mode": "twiml"})
                log.info("[xcom.voice] call OK to=%s sid=%s", to, call.sid)
            except Exception as e:
                # Compress noisy Twilio HTTP errors into a short reason
                status = getattr(e, "status", None)
                code = getattr(e, "code", None)
                msg = getattr(e, "msg", None) or getattr(e, "message", None)
                reason_bits = []
                if status is not None:
                    reason_bits.append(f"http={status}")
                if code is not None:
                    reason_bits.append(f"code={code}")
                if msg:
                    reason_bits.append(str(msg))
                reason = "; ".join(reason_bits) or str(e)

                results.append({"to": to, "ok": False, "error": reason})
                log.info("[xcom.voice] call FAIL to=%s reason=%s", to, reason)

        ok = any(item.get("ok") for item in results)
        error_msg = "; ".join(
            str(item.get("error"))
            for item in results
            if not item.get("ok", True) and item.get("error")
        ) or None

        return {
            "ok": ok,
            "results": results,
            "error": error_msg,
        }
    except Exception as e:
        log.info("[xcom.voice] error: %s", e)
        return {"ok": False, "error": str(e)}
