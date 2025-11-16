from __future__ import annotations

import logging
from typing import Any, Dict

from twilio.rest import Client

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
        dl = context.get("dl")
        if not dl:
            log.info("[xcom.voice] missing DL in context")
            return {"ok": False, "reason": "missing-dl"}
        prov = _read_providers(dl)
        voice_cfg = (prov.get("voice") or {}) if isinstance(prov, dict) else {}
        provider_cfg: Dict[str, Any] = {}
        if isinstance(voice_cfg, dict):
            provider_cfg.update(voice_cfg)

        ctx_provider = (context.get("voice") or {}).get("provider")
        if isinstance(ctx_provider, dict):
            provider_cfg.update(ctx_provider)

        enabled = bool(provider_cfg.get("enabled", True))
        if not enabled:
            log.info("[xcom.voice] provider disabled")
            return {"ok": False, "reason": "provider-disabled"}

        provider_name = (provider_cfg.get("provider") or "").lower()
        if provider_name != "twilio":
            log.info("[xcom.voice] unknown provider: %s", provider_name)
            return {"ok": False, "reason": f"unknown-provider:{provider_name}"}

        comm_cfg = _load_comm_config()
        profile_name = (
            payload.get("voice_profile")
            or ((context.get("voice") or {}).get("voice_profile") if isinstance(context, dict) else None)
            or "default"
        )
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
        flow = provider_cfg.get("flow_sid")

        if isinstance(tos, str):
            tos = [tos]

        if not (sid and token and frm and tos):
            log.info("[xcom.voice] twilio missing config")
            return {"ok": False, "reason": "twilio-missing-config"}

        client = Client(sid, token)

        results = []
        for to in tos:
            try:
                if flow:
                    exec_ = client.studio.v2.flows(flow).executions.create(to=to, from_=frm)
                    results.append({"to": to, "sid": exec_.sid, "ok": True, "mode": "studio"})
                    log.info("[xcom.voice] studio OK to=%s sid=%s", to, exec_.sid)
                else:
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
