from __future__ import annotations

import os
import html
import re
from typing import Any, Dict, Optional, Tuple

try:
    from twilio.rest import Client
except Exception:  # twilio might not be installed in some test envs
    Client = None  # type: ignore

from backend.core.logging import log


def _twiml_url_from_ctx(dl: Any, ctx: Optional[dict]) -> Optional[str]:
    if ctx and "twiml_url" in ctx:
        return ctx["twiml_url"]
    return getattr(dl, "twiml_url", None)


def place_call(dl: Any, *, to_number: str, from_number: str, ctx: dict) -> Tuple[str, int]:
    """Place a Twilio call and return (sid, http_status)."""

    if Client is None:
        raise RuntimeError("twilio client not available in this environment")

    sid = getattr(dl, "twilio_sid", None) or getattr(dl, "twilio_account_sid", None)
    token = getattr(dl, "twilio_token", None) or getattr(dl, "twilio_auth_token", None)

    if not sid or not token:
        raise RuntimeError("Twilio credentials missing on DataLocker: twilio_sid / twilio_token")

    url = _twiml_url_from_ctx(dl, ctx) or "https://demo.twilio.com/docs/voice.xml"

    client = Client(sid, token)
    call = client.calls.create(to=to_number, from_=from_number, url=url)
    http_status = getattr(getattr(call, "last_response", None), "status_code", 201)
    return call.sid, http_status


# --- tiny dotenv (no deps) ----------------------------------------------------

def _parse_dotenv_guess(root_hint: Optional[str] = None) -> Dict[str, str]:
    """
    Minimal .env reader (KEY=VALUE only). No quoting/escaping. Ignores comments.
    Tries a few likely locations if root_hint not given.
    """
    candidates = []
    if root_hint and os.path.isfile(root_hint):
        candidates.append(root_hint)
    else:
        for p in (".env", "backend/.env", "C:/sonic7/.env", "C:\\sonic7\\.env"):
            if os.path.isfile(p):
                candidates.append(p)
    env: Dict[str, str] = {}
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, v = s.split("=", 1)
                    env[k.strip()] = v.strip()
            if env:
                return env
        except Exception:
            pass
    return {}


def _expand_placeholder(val: Optional[str], dot: Dict[str, str]) -> Optional[str]:
    """
    Expand ${NAME} or $NAME from os.environ or .env dict. If not resolvable, return original.
    """
    if not val:
        return val
    # ${NAME}
    m = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", val)
    if m:
        key = m.group(1)
        return os.environ.get(key) or dot.get(key) or val
    # $NAME
    m = re.fullmatch(r"\$([A-Za-z_][A-Za-z0-9_]*)", val)
    if m:
        key = m.group(1)
        return os.environ.get(key) or dot.get(key) or val
    return val


def _get_env_synonyms(dot: Dict[str, str], names: Tuple[str, ...]) -> Optional[str]:
    """
    Return the first non-empty value among the provided name tuple.
    Expands ${VAR}/$VAR placeholders if encountered.
    """
    for n in names:
        v = os.environ.get(n)
        if v is None and dot:
            v = dot.get(n)
        v = _expand_placeholder(v, dot)
        if v is not None and str(v).strip():
            return v.strip()
    return None


# --- service ------------------------------------------------------------------

class VoiceService:
    """
    Minimal voice dialer over Twilio.

    provider_cfg: dict with provider options. This implementation cares about:
      - 'enabled': bool  (if False -> skip immediately)
      - optional overrides for sid/token/from/to/flow if you ever want to put them in JSON

    Credentials & numbers are resolved with precedence:
      1) provider_cfg overrides if present
      2) os.environ (supports TWILIO_SID/TWILIO_ACCOUNT_SID, TWILIO_FROM/TWILIO_PHONE_NUMBER, TWILIO_TO/MY_PHONE_NUMBER)
      3) minimal .env parser fallback (same shell, no extra deps)

    Returns from call():
      (ok: bool, sid: Optional[str], to_number: Optional[str], from_number: Optional[str], http_status: Optional[int])
    """

    def __init__(self, provider_cfg: Optional[Dict[str, Any]] = None) -> None:
        self.cfg: Dict[str, Any] = dict(provider_cfg or {})

    def _resolve_enabled(self, dl) -> bool:
        # provider flag wins if present
        if "enabled" in self.cfg:
            return bool(self.cfg.get("enabled"))
        # else try system var
        try:
            sysvars = getattr(dl, "system", None)
            if sysvars:
                xpv = (sysvars.get_var("xcom_providers") or {})
                tw = xpv.get("twilio") or {}
                if "enabled" in tw:
                    return bool(tw.get("enabled"))
        except Exception:
            pass
        # default to True so STUB/lab runs aren't blocked
        return True

    def _collect_creds_and_numbers(self, dl) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        dot = _parse_dotenv_guess()
        # Prefer canonical keys first, then Twilio's legacy names
        sid = (
            self.cfg.get("account_sid")
            or _get_env_synonyms(dot, ("TWILIO_SID", "TWILIO_ACCOUNT_SID"))
        )
        tok = (
            self.cfg.get("auth_token")
            or _get_env_synonyms(dot, ("TWILIO_AUTH_TOKEN",))
        )
        from_num = (
            self.cfg.get("from")
            or _get_env_synonyms(dot, ("TWILIO_FROM", "TWILIO_PHONE_NUMBER"))
        )
        to_num = (
            self.cfg.get("to")
            or _get_env_synonyms(dot, ("TWILIO_TO", "MY_PHONE_NUMBER"))
        )
        return sid, tok, from_num, to_num

    def call(
        self,
        template: Any,
        subject: str,
        body: str,
        *,
        dl=None,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str], Optional[int]]:
        # Gate on provider enabled
        if not self._resolve_enabled(dl):
            log.debug("VoiceService: provider disabled -> skipping call", source="voice")
            return False, None, None, None, None

        sid, tok, from_num, to_num = self._collect_creds_and_numbers(dl)

        # Hard requirements
        if not sid or not tok:
            log.debug(
                "VoiceService: creds missing -> skip",
                source="voice",
                payload={"need": "TWILIO_SID/TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN"},
            )
            return False, None, None, None, None

        if not to_num or not from_num:
            log.debug(
                "VoiceService: numbers missing -> skip",
                source="voice",
                payload={"need": "TWILIO_TO/MY_PHONE_NUMBER and TWILIO_FROM/TWILIO_PHONE_NUMBER"},
            )
            return False, None, None, None, None

        # Build simple TwiML from subject/body
        msg = (subject or "").strip()
        if body and body.strip():
            if msg:
                msg += ". "
            msg += body.strip()
        twiml = f"<Response><Say>{html.escape(msg) or 'Alert'}</Say></Response>"

        try:
            if Client is None:
                raise ModuleNotFoundError("twilio client not available in this environment")

            client = Client(sid, tok)
            call = client.calls.create(to=to_num, from_=from_num, twiml=twiml)

            http_status = getattr(getattr(call, "last_response", None), "status_code", 201)
            log.debug(
                "VoiceService: call placed",
                source="voice",
                payload={
                    "sid": getattr(call, "sid", None),
                    "to": to_num,
                    "from": from_num,
                    "http_status": http_status,
                },
            )
            return True, getattr(call, "sid", None), to_num, from_num, int(http_status) if http_status is not None else None

        except ModuleNotFoundError as e:
            log.warning("VoiceService import error", source="voice", payload={"error": str(e)})
            return False, None, None, None, None
        except Exception as e:
            log.warning("VoiceService Twilio error", source="voice", payload={"error": str(e)})
            return False, None, None, None, None
