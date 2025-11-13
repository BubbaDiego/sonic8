from __future__ import annotations
import logging
from typing import Any, Dict

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
        enabled = bool(voice_cfg.get("enabled", True))
        if not enabled:
            log.info("[xcom.voice] provider disabled")
            return {"ok": False, "reason": "provider-disabled"}

        # compute text
        tts = (context.get("voice") or {}).get("tts") or _tts_from(payload)

        # Here is where you call your real provider; examples:
        # twilio = voice_cfg.get("twilio", {})
        # sid = _send_with_twilio(tts, twilio, dl)  # implement to your taste
        # For now we just log & return success — Codex can fill the provider call.
        log.info("[xcom.voice] SAY: %s", tts)
        return {"ok": True, "sid": None}
    except Exception as e:
        log.info("[xcom.voice] error: %s", e)
        return {"ok": False, "reason": str(e)}
