from __future__ import annotations
import logging
from typing import Any, Dict

from twilio.rest import Client

log = logging.getLogger("sonic.engine")


def _read_providers(dl) -> Dict[str, Any]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return {}
    prov = sysmgr.get_var("xcom_providers") or {}
    if not isinstance(prov, dict):
        return {}
    return prov


def _tts_from(payload: Dict[str, Any]) -> str:
    # prefer explicit; fall back to body; final fallback: label + subject
    tts = payload.get("tts")
    if tts:
        return str(tts)
    body = payload.get("body")
    if body:
        return str(body)
    subj = payload.get("subject") or ""
    lab = payload.get("label") or ""
    text = f"{lab} {subj}".strip()
    return text or "Alert."


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

        tts = (context.get("voice") or {}).get("tts") or _tts_from(payload)
        results = []
        for to in tos:
            try:
                if flow:
                    exec_ = client.studio.v2.flows(flow).executions.create(to=to, from_=frm)
                    results.append({"to": to, "sid": exec_.sid, "ok": True, "mode": "studio"})
                    log.info("[xcom.voice] studio OK to=%s sid=%s", to, exec_.sid)
                else:
                    twiml = f"<Response><Say>{tts}</Say></Response>"
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

        return {"ok": any(r.get("ok") for r in results), "results": results}
    except Exception as e:
        log.info("[xcom.voice] error: %s", e)
        return {"ok": False, "reason": str(e)}
