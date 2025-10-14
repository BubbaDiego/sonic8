# -*- coding: utf-8 -*-
"""
XCom Console — standalone, menu-driven utility for the XCom_Core domain.

• Runs standalone:   python -m backend.core.xcom_core.xcom_console
• Or from LaunchPad: import and call launch()

Features
  1) 🩺  Status probe (best-effort; uses XCom status service if available)
  2) 🔧  Inspect resolved providers (env + detected)
  3) 📞  Voice test (Twilio)
  4) ⚙️  System test (console)
  5) ✉️  SMS test (placeholder)
  6) 🔊  TTS test (placeholder)
  7) ❤️  Heartbeat (best-effort; calls heartbeat service if present)
  8) 🎙️  Set voice (update Polly voice for console tests)
  9) 🧙  Comms Wizard (guided send/test shortcuts)

Notes
  - We call the same dispatch_notifications() you use in XCom, so channel
    behavior & Twilio creds resolution match backend semantics.  # 📚
    (see xcom_core.py; CHAN_ICON + Twilio-first voice path)                         # noqa
  - Twilio creds are pulled from context→twilio or env (TWILIO_*).                  # noqa
  - Designed to be loud and user-friendly in Windows terminals.

"""

from __future__ import annotations

import os
import sys
import json
import time
import re
import subprocess
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore  # pip install requests
except Exception:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

# Optional slant title (pyfiglet). Degrade gracefully if missing.
try:
    import pyfiglet  # type: ignore
except Exception:  # pragma: no cover - optional enhancement
    pyfiglet = None  # type: ignore

from backend.core.xcom_core.xcom_config_loader import (
    apply_xcom_env,
    load_xcom_config,
    mask_for_log,
)
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.xcom_core.voice_service import VoiceService
from backend.data.data_locker import DataLocker

try:  # Optional dependency for the wizard's SMS shortcut
    from twilio.rest import Client as _TwilioClient  # type: ignore
except Exception:  # pragma: no cover - Twilio often absent in dev shells
    _TwilioClient = None  # type: ignore

# Optional color, degrade gracefully
try:
    from colorama import Fore, Style, init as _colorama_init  # type: ignore
    _colorama_init()
except Exception:
    class _Dummy:
        def __getattr__(self, _): return ""
    Fore = Style = _Dummy()  # type: ignore

# Import your XCom core exactly like the backend does
try:
    # xcom_core.__init__ re-exports dispatch_notifications safely
    from backend.core.xcom_core import dispatch_notifications  # type: ignore
except Exception as e:  # pragma: no cover
    print("⚠️  XCom not importable; some actions will be disabled:", e, flush=True)
    dispatch_notifications = None  # type: ignore

# Best-effort status helpers (module may or may not exist in branch)
def _maybe_import(name: str):
    try:
        return __import__(name, fromlist=["*"])
    except Exception:
        return None

XStatus = _maybe_import("backend.core.xcom_core.xcom_status_service")
XConfig = _maybe_import("backend.core.xcom_core.xcom_config_service")
XHeartbeat = _maybe_import("backend.core.xcom_core.check_twilio_heartbeat_service")

# Icons
ICON = {
    "ok": "🛡",
    "warn": "⚠️",
    "err": "❌",
    "voice": "📞",
    "sms": "✉️",
    "tts": "🔊",
    "sys": "⚙️",
    "status": "🩺",
    "gear": "🔧",
    "hb": "❤️",
    "back": "◀",
    "exit": "⏻",
    "mic": "🎙️",
    "wizard": "🧙",
    "link": "🔗",
    "magnifier": "🔎",
    "scene": "🎬",
    "inbox": "📥",
    "play": "🛰",
    "stop": "⏹",
}

# ---------------- config loader (JSON-first, env fallback) -------------------
_CFG_CACHE: dict | None = None


def _load_cfg() -> dict:
    """Load JSON config once. Lookup order:
       1) XCOM_CONFIG_JSON env path
       2) backend/config/xcom_config.json
       3) config/xcom_config.json
       4) ./xcom_config.json
    """

    global _CFG_CACHE
    if _CFG_CACHE is not None:
        return _CFG_CACHE

    candidates = [
        os.getenv("XCOM_CONFIG_JSON", "").strip(),
        os.path.join(os.getcwd(), "backend", "config", "xcom_config.json"),
        os.path.join(os.getcwd(), "config", "xcom_config.json"),
        os.path.join(os.getcwd(), "xcom_config.json"),
    ]

    for p in [c for c in candidates if c]:
        try:
            with open(p, "r", encoding="utf-8") as f:
                _CFG_CACHE = json.load(f)
                _CFG_CACHE["_path"] = p
                return _CFG_CACHE
        except Exception:
            pass

    _CFG_CACHE = {}
    return _CFG_CACHE


def cfg_get(key: str, default: str | None = None) -> str:
    val = _load_cfg().get(key)
    if isinstance(val, str) and val.strip():
        return val.strip()
    env = os.getenv(key)
    return env.strip() if isinstance(env, str) and env.strip() else (default or "")

# Box banner (no leading newline to avoid extra space under the slant title)
BANNER = (
    " ╔════════════════════════════════════════════════════════╗\n"
    " ║ Cross-Communication Ops & Diagnostics ║\n"
    " ╚════════════════════════════════════════════════════════╝"
)

_IS_TTY = sys.stdout.isatty()


def _clear():
    if not _IS_TTY:
        return
    os.system("cls" if os.name == "nt" else "clear")


def _pause(msg="Press ENTER to continue…"):
    if not _IS_TTY:
        return
    try:
        input(Fore.BLACK + Style.BRIGHT + msg + Style.RESET_ALL)
    except (EOFError, KeyboardInterrupt):
        pass


def _stdin_flush() -> None:
    """Drain pending characters from stdin to avoid double-enter artifacts."""
    try:
        import msvcrt  # type: ignore

        while msvcrt.kbhit():
            msvcrt.getwch()
    except Exception:
        # Non-Windows environments won't have msvcrt; that's fine.
        pass


def _first_env(*names: str) -> str:
    for n in names:
        v = os.getenv(n)
        if v and str(v).strip():
            return str(v).strip()
    return ""


def _compose_sms_cfg() -> dict:
    """Build SMSService config from env (Twilio-first)."""
    return {
        "enabled": True,
        "sid": _first_env("TWILIO_ACCOUNT_SID"),
        "token": _first_env("TWILIO_AUTH_TOKEN"),
        "from_number": _first_env("TWILIO_FROM_PHONE", "TWILIO_PHONE_NUMBER"),
        "default_recipient": _first_env("TWILIO_TO_PHONE", "MY_PHONE_NUMBER"),
        # Optional email-gateway fallback (e.g., "vtext.com", "tmomail.net")
        "carrier_gateway": os.getenv("SMS_CARRIER_GATEWAY", "").strip(),
        # Set to True to log without sending
        "dry_run": os.getenv("SMS_DRY_RUN", "").strip() == "1",
    }


def _visible(s: Optional[str]) -> bool:
    return bool(s and str(s).strip())


@dataclass
class TwilioConfig:
    account_sid: str = ""
    auth_token: str = ""
    flow_sid: str = ""
    from_phone: str = ""
    to_phone: str = ""

    @classmethod
    def from_env(cls) -> "TwilioConfig":
        return cls(
            account_sid=_first_env("TWILIO_ACCOUNT_SID", "TWILIO_SID"),
            auth_token=_first_env("TWILIO_AUTH_TOKEN", "TWILIO_TOKEN"),
            flow_sid=_first_env("TWILIO_FLOW_SID", "TWILIO_FLOW_ID", "TWILIO_FLOW"),
            from_phone=_first_env(
                "TWILIO_FROM_PHONE",
                "TWILIO_PHONE_NUMBER",
                "TWILIO_DEFAULT_FROM_PHONE",
                "TWILIO_FROM",
            ),
            to_phone=_first_env(
                "TWILIO_TO_PHONE",
                "TWILIO_DEFAULT_TO_PHONE",
                "MY_PHONE_NUMBER",
                "TWILIO_TO",
            ),
        )

    def present(self) -> Dict[str, bool]:
        return {
            "sid": _visible(self.account_sid),
            "token": _visible(self.auth_token),
            "flow_sid": _visible(self.flow_sid),
            "from": _visible(self.from_phone),
            "to": _visible(self.to_phone),
        }

    def as_context_node(self) -> Dict[str, Any]:
        # include BOTH the names XCom resolves and the UI “default_*” names
        return {
            "sid": self.account_sid,
            "account_sid": self.account_sid,
            "token": self.auth_token,
            "auth_token": self.auth_token,
            "from": self.from_phone,
            "from_phone": self.from_phone,
            "to": self.to_phone,
            "to_phone": [self.to_phone] if self.to_phone else [],
            "default_from_phone": self.from_phone,
            "default_to_phone": self.to_phone,
            "flow": self.flow_sid,
            "flow_sid": self.flow_sid,
            "enabled": True,
        }


SUPPORTED_VOICES: List[str] = [
    "Polly.Amy",     # UK, crisp
    "Polly.Brian",   # UK, male
    "Polly.Emma",    # UK
    "Polly.Joanna",  # US, warm
    "Polly.Matthew", # US, neutral
    "Polly.Kendra",  # US
    "Polly.Kimberly",# US
    "Polly.Salli",   # US
    "Polly.Joey",    # US, male
]


VOICE_FACES = {
    "Polly.Amy": "🙂",
    "Polly.Brian": "😎",
    "Polly.Emma": "😊",
    "Polly.Joanna": "🙂",
    "Polly.Matthew": "😐",
    "Polly.Kendra": "🙂",
    "Polly.Kimberly": "🙂",
    "Polly.Salli": "🙂",
    "Polly.Joey": "😄",
}


def _dl() -> Optional[DataLocker]:
    try:
        return DataLocker.get_instance(str(MOTHER_DB_PATH))
    except Exception:
        return None


def _get_providers() -> Dict[str, Any]:
    locker = _dl()
    if not locker or getattr(locker, "system", None) is None:
        return {}
    try:
        cfg = locker.system.get_var("xcom_providers")  # type: ignore[attr-defined]
    except Exception:
        return {}
    return cfg if isinstance(cfg, dict) else {}


def _set_providers(cfg: Dict[str, Any]) -> bool:
    locker = _dl()
    if not locker or getattr(locker, "system", None) is None:
        return False
    try:
        locker.system.set_var("xcom_providers", cfg or {})  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


def _get_twilio_cfg() -> Dict[str, Any]:
    providers = _get_providers()
    twilio_cfg: Dict[str, Any] = dict(providers.get("twilio") or {})
    voice = str(twilio_cfg.get("voice_name", "")).strip() or "Polly.Amy"
    twilio_cfg["voice_name"] = voice
    twilio_cfg.setdefault("speak_plain", True)
    twilio_cfg.setdefault("use_studio", False)
    twilio_cfg.setdefault("start_delay_ms", 400)
    twilio_cfg.setdefault("end_delay_ms", 250)
    twilio_cfg.setdefault("prosody_rate_pct", 94)
    return twilio_cfg


def _save_twilio_cfg(twilio_cfg: Dict[str, Any], mirror_api: bool = True) -> bool:
    providers = dict(_get_providers())
    providers["twilio"] = dict(twilio_cfg)
    if mirror_api:
        api_cfg: Dict[str, Any] = dict(providers.get("api") or {})
        for key in ("voice_name", "speak_plain", "use_studio", "start_delay_ms", "end_delay_ms", "prosody_rate_pct"):
            if key in twilio_cfg:
                api_cfg[key] = twilio_cfg[key]
        providers["api"] = api_cfg
    return _set_providers(providers)


def _print_voice_settings(prefix: str = "   ") -> None:
    twilio_cfg = _get_twilio_cfg()
    face = VOICE_FACES.get(twilio_cfg.get("voice_name", ""), "🙂")
    print(f"{prefix}Voice: {face}  {twilio_cfg['voice_name']}")
    print(f"{prefix}speak_plain: {twilio_cfg['speak_plain']}")
    print(f"{prefix}use_studio : {twilio_cfg['use_studio']}")
    print(
        f"{prefix}start_delay_ms: {twilio_cfg['start_delay_ms']}  | "
        f"end_delay_ms: {twilio_cfg['end_delay_ms']}"
    )
    print(f"{prefix}prosody_rate_pct: {twilio_cfg['prosody_rate_pct']}")


def _prompt_int(
    label: str,
    default_val: int,
    min_v: Optional[int] = None,
    max_v: Optional[int] = None,
) -> int:
    _stdin_flush()
    raw = input(f"{label} (default: {default_val}): ").strip()
    if not raw:
        return default_val
    try:
        value = int(raw)
    except Exception:
        print("   (invalid number — keeping default)")
        return default_val
    if min_v is not None and value < min_v:
        value = min_v
    if max_v is not None and value > max_v:
        value = max_v
    return value


def _get_voice_name() -> str:
    providers = _get_providers()
    twilio = providers.get("twilio") if isinstance(providers.get("twilio"), dict) else {}
    voice = (twilio or {}).get("voice_name")
    if not voice:
        voice = "Polly.Amy"
    return str(voice)


def _set_voice_name(voice_name: str) -> bool:
    name = (voice_name or "").strip()
    if not name:
        return False
    twilio_cfg = _get_twilio_cfg()
    twilio_cfg["voice_name"] = name
    twilio_cfg["use_studio"] = False
    return _save_twilio_cfg(twilio_cfg)


def _resolve_from() -> str:
    from_number = _first_env("TWILIO_FROM_PHONE", "TWILIO_PHONE_NUMBER")
    if from_number:
        return from_number
    providers = _get_providers().get("twilio") or {}
    return str(providers.get("default_from_phone", "")).strip()


def _resolve_to_from() -> Tuple[str, str]:
    to_number = _first_env("TWILIO_TO_PHONE", "MY_PHONE_NUMBER")
    from_number = _resolve_from()
    if to_number and from_number:
        return to_number, from_number

    providers = _get_providers().get("twilio") or {}
    if not to_number:
        to_number = str(providers.get("default_to_phone", "")).strip()
    if not from_number:
        from_number = str(providers.get("default_from_phone", "")).strip()

    if not to_number or not from_number:
        raise RuntimeError(
            "Missing to/from numbers. Set environment variables or update xcom_providers."
        )
    return to_number, from_number


def _prompt_phone(label: str, default_value: str) -> str:
    _stdin_flush()
    raw = input(f"{label} (default: {default_value or 'unset'}): ").strip()
    return raw or default_value


def _send_sms_direct(to_number: str, from_number: str, body: str) -> Tuple[bool, Optional[str]]:
    if not _TwilioClient:
        print("   ⚠ Twilio client not available in this environment.")
        return False, None

    sid = _first_env("TWILIO_ACCOUNT_SID")
    token = _first_env("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        print("   ⚠ Missing TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN.")
        return False, None

    try:
        client = _TwilioClient(sid, token)
        message = client.messages.create(to=to_number, from_=from_number, body=body)
        return True, getattr(message, "sid", None)
    except Exception as exc:  # pragma: no cover - network call
        print(f"   ❌ SMS error: {exc}")
        return False, None


def _print_header():
    _clear()

    title = "XCom Console"
    if pyfiglet is not None:
        try:
            slant = pyfiglet.figlet_format(title, font="slant")
        except Exception:
            slant = ""
        else:
            slant = slant.rstrip("\n")
    else:
        slant = ""

    if not slant:
        slant = (
            "   _  ________                   ______                       __   \n"
            "  | |/ / ____/___  ____ ___     / ____/___  ____  _________  / /__ \n"
            "  |   / /   / __ \\ / __ `__ \\   / /   / __ \\/ __ \\/ ___/ __ \\/ / _ \\\n"
            " /   / /___/ /_/ / / / / / /  / /___/ /_/ / / / (__  ) /_/ / /  __/\n"
            "/_/|_|\\____/\\____/_/ /_/ /_/   \\____/\\____/_/ /_/____/\\____/_/\\___/"
        )

    # Render bold cyan slant title, then the box with NO blank line in-between
    print(Style.BRIGHT + Fore.CYAN + slant + Style.RESET_ALL)
    print(BANNER)


def _row(k: str, v: str, ok: Optional[bool] = None):
    if ok is True:
        badge = f"{ICON['ok']} "
        color = Fore.GREEN
    elif ok is False:
        badge = f"{ICON['err']} "
        color = Fore.RED
    else:
        badge = "  "
        color = ""
    print(f"{badge}{Style.BRIGHT}{k:<22}{Style.RESET_ALL} {color}{v}{Style.RESET_ALL}")


def _status_probe():
    _print_header()
    print(f"{ICON['status']}  Status Probe\n")

    status: Dict[str, Any] = {}
    # Prefer service if available
    try:
        if XStatus and hasattr(XStatus, "get_status"):
            status = XStatus.get_status()  # type: ignore
        elif XStatus and hasattr(XStatus, "status"):
            status = XStatus.status()  # type: ignore
    except Exception as e:
        status = {"error": str(e)}

    # Fallback: infer from env if service is missing
    tw = TwilioConfig.from_env()
    inferred = {
        "twilio": "ok" if all(tw.present().values()) else "missing creds",
        "smtp": "unknown",
        "sound": "ok",
    }
    if not status:
        status = inferred

    # Render
    for k, v in (status.items() if isinstance(status, dict) else [("status", status)]):
        val = str(v)
        key = k.upper()
        ok = val.lower() in ("ok", "healthy", "true")
        warn = any(t in val.lower() for t in ("warn", "issue", "retry"))
        _row(key, val, ok if not warn else None)

    print()
    _pause()

    print("---------- Backend health ----------")
    print()

    try:
        hb = _probe_backend()

        print("• Backend")
        _row("  Local", hb["local"]["label"], hb["local"]["ok"])

        if hb["public"]["checked"]:
            _row("  Public", hb["public"]["label"], hb["public"]["ok"])

        last_ts = _inbox_last_ts()
        if last_ts:
            _row("  Last inbound SMS", last_ts)

    except Exception as _e:
        _row("BACKEND", f"probe error: {_e}", False)

    print()
    _pause()

    print("---------- Textbelt probe (JSON config first, env fallback) ----------")
    print()

    try:
        tb = _probe_textbelt()

        print("\n• Textbelt")
        _row("  Key", "present" if tb["key_ok"] else "(missing)", tb["key_ok"])
        _row("  Endpoint", tb["endpoint"] or "(missing)")
        _row("  Default To", tb["default_to"] or "(missing)", tb["to_ok"])

        if tb["reachable"] is True:
            _row("  Reachable", "ok", True)
        elif tb["reachable"] is False:
            _row("  Reachable", "error", False)
        else:
            _row("  Reachable", "skipped (no requests)")

        if tb.get("quota") is not None:
            _row("  Quota Remaining", str(tb["quota"]))

    except Exception as _e:
        _row("TEXTBELT", f"probe error: {_e}", False)

    print()
    _pause()


def _probe_backend() -> Dict[str, Any]:
    """Probe the backend health endpoints."""

    result: Dict[str, Any] = {
        "local": {"ok": False, "label": "offline"},
        "public": {"ok": False, "label": "skipped", "checked": False},
    }

    base_local = _local_api_base()

    try:
        if requests is not None:
            resp = requests.get(f"{base_local}/api/status", timeout=3)
            is_ok = 200 <= resp.status_code < 500
            result["local"]["ok"] = is_ok
            result["local"]["label"] = "live" if is_ok else f"error {resp.status_code}"
        else:
            result["local"]["ok"] = None
            result["local"]["label"] = "unknown (no requests)"
    except Exception:
        result["local"]["ok"] = False
        result["local"]["label"] = "offline"

    base_public = cfg_get("PUBLIC_BASE_URL", "").rstrip("/")

    if base_public:
        result["public"]["checked"] = True
        try:
            if requests is not None:
                resp = requests.get(f"{base_public}/api/status", timeout=3)
                is_ok = 200 <= resp.status_code < 500
                result["public"]["ok"] = is_ok
                result["public"]["label"] = "live" if is_ok else f"error {resp.status_code}"
            else:
                result["public"]["ok"] = None
                result["public"]["label"] = "unknown (no requests)"
        except Exception:
            result["public"]["ok"] = False
            result["public"]["label"] = "offline"

    return result


def _inbox_last_ts() -> str | None:
    """Return the formatted timestamp of the last inbound SMS if available."""

    path = _inbound_log_path()
    file_path = Path(path)

    if not file_path.exists() or file_path.stat().st_size == 0:
        return None

    try:
        with file_path.open("r", encoding="utf-8") as handle:
            dq = deque(handle, maxlen=1)

        if not dq:
            return None

        payload = json.loads(dq[0])
        ts_val = float(payload.get("ts", 0))
        if ts_val:
            return (
                datetime.fromtimestamp(ts_val, tz=timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S")
            )
    except Exception:
        return None

    return None


def _probe_textbelt() -> Dict[str, Any]:
    """
    Best-effort health probe for Textbelt.

    Returns: {
        key_ok: bool, to_ok: bool, reachable: bool|None, quota: int|None,
        endpoint: str, default_to: str
    }
    """

    base = (cfg_get("TEXTBELT_ENDPOINT", "https://textbelt.com").rstrip("/"))
    key = cfg_get("TEXTBELT_KEY", "")
    default_to = _default_sms_to()

    key_ok = bool(key)
    to_ok = bool(default_to and _E164.match(default_to))

    reachable: Optional[bool] = None
    quota_val: Optional[int] = None

    if requests is not None:
        try:
            if key_ok:
                # Try quota endpoint if available; ignore if not supported
                r = requests.get(f"{base}/quota/{key}", timeout=4)
                reachable = r.status_code < 500
                try:
                    j = r.json()
                    quota_val = j.get("quotaRemaining") or j.get("quota_remaining")
                except Exception:
                    quota_val = None
            else:
                r = requests.get(base, timeout=4)
                reachable = r.status_code < 500
        except Exception:
            reachable = False
    else:
        reachable = None

    overall_ok = key_ok and to_ok and (reachable in (True, None))

    return {
        "ok": overall_ok,
        "key_ok": key_ok,
        "to_ok": to_ok,
        "reachable": reachable,
        "quota": quota_val,
        "endpoint": base,
        "default_to": default_to,
    }


def _inspect_providers():
    _print_header()
    print(f"{ICON['gear']}  Providers (resolved)\n")

    # Try to fetch from config service if present; else env
    config = {}
    try:
        if XConfig and hasattr(XConfig, "get_providers_resolved"):
            config = XConfig.get_providers_resolved()  # type: ignore
    except Exception:
        config = {}

    tw = TwilioConfig.from_env()
    tw_map = tw.present()

    print("• Twilio")
    _row("  Account SID", tw.account_sid or "(missing)", tw_map["sid"])
    _row("  Auth token", "[hidden]" if tw_map["token"] else "(missing)", tw_map["token"])
    _row("  Flow SID", tw.flow_sid or "(missing)", tw_map["flow_sid"])
    _row("  From phone", tw.from_phone or "(missing)", tw_map["from"])
    _row("  To phone", tw.to_phone or "(missing)", tw_map["to"])

    if config:
        print("\n• Backend Resolved (snapshot)")
        print(json.dumps(config, indent=2)[:2000])

    print()
    _pause()


def _ensure_dispatch():
    if dispatch_notifications is None:
        _print_header()
        print("XCom dispatch is unavailable in this environment.\n")
        _pause()
        return False
    return True


def _compose_context(message: str, level: str = "LOW") -> Dict[str, Any]:
    tw = TwilioConfig.from_env()
    ctx: Dict[str, Any] = {
        "level": level,
        "subject": f"[XCom Test] {level}",
        "body": message,
        "initiator": "xcom_console",
        "recipient": tw.to_phone
        or _first_env("MY_PHONE_NUMBER", "TWILIO_TO_PHONE", "TWILIO_DEFAULT_TO_PHONE", "TWILIO_TO"),
        "twilio": tw.as_context_node(),
        # PREVIEW sugar used by xcom_core debug prints
        "positions": [{"asset": "SOL"}, {"asset": "ETH"}],
    }
    return ctx


def _do_dispatch(
    label: str,
    channels: Dict[str, Any],
    message: str,
    extra_ctx: Optional[Dict[str, Any]] = None,
):
    if not _ensure_dispatch():
        return

    result = {
        "breach": True,  # console tests force "notify"
        "level": next((k for k, v in channels.items() if v), "LOW"),
        "message": message,
    }
    ctx = _compose_context(message, level=result["level"])
    if isinstance(extra_ctx, dict):
        try:
            merged = dict(ctx)
            merged.update(extra_ctx)
            ctx = merged
        except Exception:
            pass
    try:
        summary = dispatch_notifications(
            monitor_name="xcom_console",
            result=result,
            channels=channels,
            context=ctx,
        )
        print("\nSummary:\n" + json.dumps(summary, indent=2))
    except Exception as e:
        print(f"\n{ICON['err']} dispatch failed: {e}")
    print()
    _pause()


def _voice_test():
    _print_header()
    print(f"{ICON['voice']}  Voice Test (Direct TwiML)\n")
    default_msg = "Console test call"
    _stdin_flush()
    msg = input(f"Message (default: '{default_msg}'): ").strip()
    if not msg:
        msg = default_msg

    try:
        to_number, from_number = _resolve_to_from()
    except Exception as exc:
        print(f"{ICON['err']}  {exc}\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    providers = _get_providers()
    cfg = dict(providers.get("twilio") or {})
    cfg.setdefault("enabled", True)
    if not cfg.get("voice_name"):
        cfg["voice_name"] = _get_voice_name()
    cfg["speak_plain"] = True
    cfg["use_studio"] = False
    for legacy_flag in ("picker", "voice_picker", "interactive_voice_select", "show_spinner"):
        if legacy_flag in cfg:
            cfg.pop(legacy_flag, None)

    print(f"   → Using voice: {cfg.get('voice_name')} (direct TwiML)\n")

    try:
        ok, sid, to_resolved, from_resolved = VoiceService(cfg).call(
            to_number=to_number,
            subject="[XCom Test] voice",
            body=msg,
        )
    except Exception as exc:
        print(f"{ICON['err']}  Error while placing call: {exc}\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    if ok:
        print(
            "  ✅ Twilio call created — "
            f"SID={sid or 'n/a'} to={to_resolved or to_number} from={from_resolved or from_number}\n"
        )
    else:
        print("  ❌ Call failed.\n")
    time.sleep(0.2)
    _stdin_flush()


def voice_test():
    """Backward-compatible alias that routes to the direct TwiML path."""
    return _voice_test()


def _set_voice_menu():
    _print_header()
    current = _get_voice_name()
    print(f"{ICON['mic']}  Set Voice\n")
    print(f"   Current: {current}")
    print("   Choose a voice by number or type a custom Polly voice (e.g., Polly.Amy).")
    for index, name in enumerate(SUPPORTED_VOICES, start=1):
        face = VOICE_FACES.get(name, "🙂")
        print(f"   {index}. {face}  {name}")
    print("   0. Cancel")

    _stdin_flush()
    choice = input("\n→ ").strip()
    if choice == "0":
        print("   (no changes)\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    selected: Optional[str] = None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(SUPPORTED_VOICES):
            selected = SUPPORTED_VOICES[idx]
    if not selected and choice:
        selected = choice

    if not selected:
        print("   (no input) — keeping existing voice.\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    if _set_voice_name(selected):
        print(f"   ✅ Voice set to {selected}\n")
    else:
        print(f"   ❌ Failed to persist voice '{selected}'.\n")
    time.sleep(0.2)
    _stdin_flush()


def _voice_options_menu():
    while True:
        _print_header()
        print("🎚️  Voice Options\n")
        _print_voice_settings()
        print(
            """
   1) 🎤 Select voice
   2) 🗣  Toggle speak_plain
   3) 🧩 Toggle use_studio
   4) ⏱  Set start_delay_ms
   5) ⏱  Set end_delay_ms
   6) 🎼 Set prosody_rate_pct
   7) ♻️  Reset to defaults
   0) ◀ Back
"""
        )
        _stdin_flush()
        choice = input("→ ").strip()
        if choice == "0":
            print("   (back)\n")
            time.sleep(0.2)
            _stdin_flush()
            return

        twilio_cfg = _get_twilio_cfg()

        if choice == "1":
            print("\n🎙️  Voice Selection")
            for index, name in enumerate(SUPPORTED_VOICES, start=1):
                face = VOICE_FACES.get(name, "🙂")
                print(f"   {index}. {face}  {name}")
            print("   0. Cancel")
            _stdin_flush()
            selection = input("\n→ ").strip()
            if selection == "0":
                continue
            selected: Optional[str] = None
            if selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(SUPPORTED_VOICES):
                    selected = SUPPORTED_VOICES[idx]
            if not selected and selection:
                selected = selection.strip()
            if not selected:
                print("   (no change)\n")
                time.sleep(0.2)
                _stdin_flush()
                continue
            twilio_cfg["voice_name"] = selected
            twilio_cfg["use_studio"] = False
            if _save_twilio_cfg(twilio_cfg):
                print(f"   ✅ Voice set to {selected}\n")
            else:
                print("   ❌ Failed to save voice change.\n")
            time.sleep(0.2)
            _stdin_flush()
            continue

        if choice == "2":
            twilio_cfg["speak_plain"] = not bool(twilio_cfg.get("speak_plain", True))
            if _save_twilio_cfg(twilio_cfg):
                print(f"   ✅ speak_plain → {twilio_cfg['speak_plain']}\n")
            else:
                print("   ❌ Failed to update speak_plain.\n")
            time.sleep(0.2)
            _stdin_flush()
            continue

        if choice == "3":
            twilio_cfg["use_studio"] = not bool(twilio_cfg.get("use_studio", False))
            if _save_twilio_cfg(twilio_cfg):
                print(f"   ✅ use_studio  → {twilio_cfg['use_studio']}\n")
            else:
                print("   ❌ Failed to update use_studio.\n")
            time.sleep(0.2)
            _stdin_flush()
            continue

        if choice == "4":
            twilio_cfg["start_delay_ms"] = _prompt_int(
                "start_delay_ms",
                int(twilio_cfg.get("start_delay_ms", 400)),
                0,
                3000,
            )
            if _save_twilio_cfg(twilio_cfg):
                print("   ✅ updated\n")
            else:
                print("   ❌ Failed to update start_delay_ms.\n")
            time.sleep(0.2)
            _stdin_flush()
            continue

        if choice == "5":
            twilio_cfg["end_delay_ms"] = _prompt_int(
                "end_delay_ms",
                int(twilio_cfg.get("end_delay_ms", 250)),
                0,
                3000,
            )
            if _save_twilio_cfg(twilio_cfg):
                print("   ✅ updated\n")
            else:
                print("   ❌ Failed to update end_delay_ms.\n")
            time.sleep(0.2)
            _stdin_flush()
            continue

        if choice == "6":
            twilio_cfg["prosody_rate_pct"] = _prompt_int(
                "prosody_rate_pct",
                int(twilio_cfg.get("prosody_rate_pct", 94)),
                70,
                120,
            )
            if _save_twilio_cfg(twilio_cfg):
                print("   ✅ updated\n")
            else:
                print("   ❌ Failed to update prosody_rate_pct.\n")
            time.sleep(0.2)
            _stdin_flush()
            continue

        if choice == "7":
            defaults = {
                "voice_name": "Polly.Amy",
                "speak_plain": True,
                "use_studio": False,
                "start_delay_ms": 400,
                "end_delay_ms": 250,
                "prosody_rate_pct": 94,
            }
            if _save_twilio_cfg(defaults):
                print("   ♻️  Reset to defaults.\n")
            else:
                print("   ❌ Failed to reset voice settings.\n")
            time.sleep(0.2)
            _stdin_flush()
            continue

        print("   (invalid)\n")
        time.sleep(0.2)
        _stdin_flush()


def _wizard_pick_comm_type() -> str:
    print("\n🧙  Comms Test Wizard\n")
    print("   Choose a communication type:")
    print("   1) 📞 Voice call")
    print("   2) ✉️  SMS")
    print("   3) 🔊 TTS")
    print("   4) 🛡 System (local sound)")
    print("   0) Cancel")
    _stdin_flush()
    return input("\n→ ").strip()


def _wizard_pick_voice(current: Optional[str] = None) -> str:
    selected = current or _get_voice_name()
    print("\n🎙️  Voice Selection")
    print(f"   Current: {selected}")
    print("   Pick a voice (faces hint at vibe), or type a custom Polly voice.")
    for index, name in enumerate(SUPPORTED_VOICES, start=1):
        face = VOICE_FACES.get(name, "🙂")
        print(f"   {index}. {face}  {name}")
    print("   0. Keep current")
    _stdin_flush()
    choice = input("\n→ ").strip()
    if choice == "0":
        return selected
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(SUPPORTED_VOICES):
            return SUPPORTED_VOICES[idx]
    if choice:
        return choice
    return selected


def _wizard_message(default_msg: str = "Test message") -> str:
    _stdin_flush()
    msg = input(f"\n📝  Message (default: '{default_msg}'): ").strip()
    return msg or default_msg


def _comms_wizard():
    _print_header()
    choice = _wizard_pick_comm_type()
    if choice == "0":
        print("   (canceled)\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    to_number = ""
    from_number = ""
    if choice in {"1", "2"}:
        try:
            default_to, default_from = _resolve_to_from()
        except Exception:
            default_to, default_from = "", _resolve_from()
        if choice == "2":
            tb_default = cfg_get("TEXTBELT_DEFAULT_TO") or default_to
            print("\n☎️  Numbers (Textbelt path — FROM not required)")
            to_number = _prompt_phone("   To", tb_default or "+1XXXXXXXXXX")
        else:
            print("\n☎️  Numbers")
            to_number = _prompt_phone("   To", default_to or "+1XXXXXXXXXX")

    voice_name: Optional[str] = None
    if choice == "1":
        voice_name = _wizard_pick_voice()
        if _set_voice_name(voice_name):
            print(f"\n   ✅ Voice set to {voice_name}")
        else:
            print(f"\n   ⚠ Could not persist voice '{voice_name}', using transient value.")

    message = _wizard_message()

    print("\n🚀  Running test…\n")
    if choice == "1":
        try:
            if not to_number:
                to_number = _resolve_to_from()[0]
        except Exception as exc:
            print(f"   ❌ {exc}\n")
            time.sleep(0.2)
            _stdin_flush()
            return

        cfg = dict(_get_providers().get("twilio") or {})
        cfg.setdefault("enabled", True)
        cfg["speak_plain"] = True
        cfg["use_studio"] = False
        cfg.setdefault("start_delay_ms", 400)
        cfg.setdefault("end_delay_ms", 250)
        if voice_name:
            cfg["voice_name"] = voice_name
        elif not cfg.get("voice_name"):
            cfg["voice_name"] = _get_voice_name()

        try:
            ok, sid, to_resolved, from_resolved = VoiceService(cfg).call(
                to_number=to_number,
                subject="[Wizard] voice",
                body=message,
            )
        except Exception as exc:
            print(f"   ❌ Voice error: {exc}\n")
            time.sleep(0.2)
            _stdin_flush()
            return

        if ok:
            print(
                "   ✅ Voice call placed — "
                f"SID={sid or 'n/a'} to={to_resolved or to_number} from={from_resolved or _resolve_from()}\n"
            )
        else:
            print("   ❌ Voice call failed.\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    if choice == "2":
        # === Textbelt path (Twilio SMS disabled) ===========================
        # Old Twilio direct send kept for reference:
        # ok, sid = _send_sms_direct(to_number, _resolve_from(), message)
        # -------------------------------------------------------------------
        if not to_number:
            try:
                to_number = _resolve_to_from()[0]
            except Exception:
                to_number = cfg_get("TEXTBELT_DEFAULT_TO") or "+1XXXXXXXXXX"
        ok, text_id, resp = _textbelt_send_core(to_number, message)
        if ok:
            print(f"   ✅ Textbelt queued — textId={text_id or 'n/a'} to={to_number}\n")
        else:
            err = (resp or {}).get("error") if isinstance(resp, dict) else None
            print(f"   ❌ Textbelt send failed. {('Reason: ' + err) if err else ''}\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    if choice == "3":
        try:
            if "tts_test" in globals():  # type: ignore
                func = globals()["tts_test"]  # type: ignore[index]
                try:
                    func(message)  # type: ignore[misc]
                except TypeError:
                    print("   (tts_test helper expects no args; echoing message)")
                    print(f"   🔊 {message}\n")
            else:
                print(f"   🔊 {message}\n")
        except Exception as exc:
            print(f"   ❌ TTS error: {exc}\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    if choice == "4":
        try:
            import winsound  # type: ignore

            winsound.Beep(880, 220)
            time.sleep(0.1)
            winsound.Beep(988, 220)
            print("   🛡 System chime played.\n")
        except Exception:
            print("   (system sound not available on this platform)\n")
        time.sleep(0.2)
        _stdin_flush()
        return

    print("   (no action taken)\n")
    time.sleep(0.2)
    _stdin_flush()


def _system_test():
    _print_header()
    print(f"{ICON['sys']}  System Test (console)\n")
    msg = input("Message (default: 'Console system alert'): ").strip() or "Console system alert"
    _do_dispatch("system", {"system": True}, msg)


def _sms_test():
    """Legacy Twilio SMS test replaced by Textbelt helper."""

    _textbelt_sms_send()


def _tts_test():
    _print_header()
    print(f"{ICON['tts']}  TTS Test\n")
    msg = input("Message (default: 'Console TTS test'): ").strip() or "Console TTS test"
    _do_dispatch("tts", {"tts": True}, msg)


def _heartbeat():
    _print_header()
    print(f"{ICON['hb']}  Heartbeat\n")
    tried = False
    try:
        if XHeartbeat and hasattr(XHeartbeat, "run"):
            tried = True
            res = XHeartbeat.run()  # type: ignore
            print("Heartbeat result:", res)
    except Exception as e:
        print("Heartbeat error:", e)

    if not tried:
        # Fallback: do a lightweight system dispatch as a ping
        _do_dispatch("system", {"system": True}, "heartbeat ping from console")
        return
    print()
    _pause()


def _menu() -> str:
    print("Main Menu\n")
    print(f"  1. {ICON['wizard']}  Comms Wizard")
    print(f"  2. {ICON['status']}  Status probe")
    print(f"  3. {ICON['gear']}  Inspect providers")
    print(f"  4. {ICON['voice']}  Voice test")
    print(f"  5. {ICON['sys']}  System test")
    print(f"  6. {ICON['sms']}  SMS test (Textbelt)")
    print(f"  7. {ICON['tts']}  TTS test")
    print(f"  8. {ICON['hb']}  Heartbeat")
    print("  9. 🎚️  Voice options")
    print(f" 10. {ICON['link']}  Textbelt SMS (no registration)")
    print(f" 11. {ICON['magnifier']}  Textbelt status (by textId)")
    print(f" 12. {ICON['scene']}  Canned Scenarios")
    print(f" 13. {ICON['inbox']}  Inbox (Textbelt replies)")
    print(f" 14. {ICON['play']}  Start reply webhook server")
    print(f" 15. {ICON['stop']}  Stop reply webhook server")
    print(f"  0. {ICON['exit']}  Exit")
    _stdin_flush()
    return input("\n→ ").strip().lower()


def launch():
    while True:
        _print_header()
        choice = _menu()
        if choice in ("0", "q", "quit", "exit"):
            _clear()
            return
        if choice == "1":
            _comms_wizard()
        elif choice == "2":
            _status_probe()
        elif choice == "3":
            _inspect_providers()
        elif choice == "4":
            _voice_test()
        elif choice == "5":
            _system_test()
        elif choice == "6":
            _sms_test()
        elif choice == "7":
            _tts_test()
        elif choice == "8":
            _heartbeat()
        elif choice == "9":
            _voice_options_menu()
        elif choice == "10":
            _textbelt_sms_send()
        elif choice == "11":
            _textbelt_status_check()
        elif choice == "12":
            _canned_scenarios()
        elif choice == "13":
            _inbox_view()
        elif choice == "14":
            _reply_server_start()
        elif choice == "15":
            _reply_server_stop()
        else:
            print("\nUnknown selection.")
            time.sleep(0.8)


# -------------------- Textbelt integration (quick, no 10DLC) ----------------
_E164 = re.compile(r"^\+\d{8,15}$")
_LAST_TEXTBELT_ID: str = ""
_REPLY_SERVER_PROC: Optional[subprocess.Popen] = None


def _inbound_log_path() -> str:
    return cfg_get("XCOM_INBOUND_LOG", "backend/logs/xcom_inbound_sms.jsonl")


def _local_api_base() -> str:
    """Return the local base URL for backend API probes."""

    return cfg_get("LOCAL_API_BASE", "http://127.0.0.1:5000").rstrip("/")


def _reply_port() -> int:
    try:
        return int(cfg_get("XCOM_REPLY_PORT", "5000"))
    except Exception:
        return 5000


def _fmt_ts(ts: int | float | None) -> str:
    try:
        return (
            datetime.fromtimestamp(float(ts), tz=timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception:
        return "n/a"


def _inbox_view():
    _print_header()
    print(f"{ICON['inbox']}  Inbox (Textbelt replies)\n")

    path = _inbound_log_path()
    if not Path(path).exists():
        print(f"No inbox file found yet at:\n  {path}\n")
        print(
            "Tip: Start the reply server (14) and send yourself a Textbelt SMS with a replyWebhookUrl."
        )
        _pause()
        return

    try:
        n_in = input("How many recent messages? (default 10): ").strip()
        n = max(1, int(n_in)) if n_in else 10
    except Exception:
        n = 10

    filt = input("Filter by From (E.164, optional): ").strip()
    lines: list[dict[str, Any]] = []

    try:
        with open(path, "r", encoding="utf-8") as fh:
            dq = deque(fh, maxlen=n)
        for ln in dq:
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            if filt and obj.get("fromNumber") != filt:
                continue
            lines.append(obj)
    except Exception as exc:
        print("Failed to read inbox:", exc)
        _pause()
        return

    if not lines:
        print("No matching messages.")
        _pause()
        return

    for idx, message in enumerate(lines, 1):
        print(f"— #{idx} —")
        print("  time :", _fmt_ts(message.get("ts")))
        print("  from :", message.get("fromNumber"))
        print("  text :", message.get("text"))
        if message.get("ip"):
            print("  ip   :", message.get("ip"))
        print()

    _pause()


def _reply_server_start():
    _print_header()
    print(f"{ICON['play']}  Start reply webhook server\n")

    global _REPLY_SERVER_PROC
    if _REPLY_SERVER_PROC and _REPLY_SERVER_PROC.poll() is None:
        print("Server already running.")
        print()
        _pause()
        return

    port = _reply_port()
    py = sys.executable
    args = [
        py,
        "-m",
        "uvicorn",
        "backend.sonic_backend_app:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]

    flags = 0
    if os.name == "nt":
        # CREATE_NO_WINDOW
        flags = 0x08000000

    try:
        _REPLY_SERVER_PROC = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
        print(f"Started uvicorn on port {port}.")
        base = cfg_get("PUBLIC_BASE_URL", "")
        if base:
            print(f"Webhook URL: {base.rstrip('/')}/api/xcom/textbelt/reply")
        else:
            print(
                "Set PUBLIC_BASE_URL in config to advertise a public webhook (e.g., ngrok HTTPS URL)."
            )
    except Exception as exc:
        print("Failed to start uvicorn:", exc)

    print()
    _pause()


def _reply_server_stop():
    _print_header()
    print(f"{ICON['stop']}  Stop reply webhook server\n")

    global _REPLY_SERVER_PROC
    if not _REPLY_SERVER_PROC:
        print("No server process tracked.")
        print()
        _pause()
        return

    if _REPLY_SERVER_PROC.poll() is not None:
        print("Server is not running.")
        print()
        _pause()
        _REPLY_SERVER_PROC = None
        return

    try:
        _REPLY_SERVER_PROC.terminate()
        time.sleep(0.5)
        if _REPLY_SERVER_PROC.poll() is None:
            _REPLY_SERVER_PROC.kill()
        print("Server stopped.")
    except Exception as exc:
        print("Failed to stop server:", exc)

    _REPLY_SERVER_PROC = None

    print()
    _pause()


def build_canned_alert_sms() -> str:
    """Build the canned multi-line alert SMS.

    Values can be overridden via config:
      ALERT_ROOM (default "Room 55")
      ALERT_PATIENT (default "Mr Rogers")
      ALERT_DEVICE_SN (default "SN:12345678")
      ALERT_DRUG (default "Epinephrine")
    """

    room = cfg_get("ALERT_ROOM", "Room 55")
    patient = cfg_get("ALERT_PATIENT", "Mr Rogers")  # avoid "Mr." to dodge URL heuristics
    device_sn = cfg_get("ALERT_DEVICE_SN", "SN:12345678")
    drug = cfg_get("ALERT_DRUG", "Epinephrine")

    # Compose with exact line order and icons
    text = (
        "🔴 HIGH\n"
        f"🚨 Air-in-Line alarm\n"
        f"💧 {drug}\n"
        f"🏥 {room}\n"
        f"👤 {patient}\n"
        f"📟 {device_sn}"
    )

    # Reuse sanitizer to avoid accidental URL flags
    return _sanitize_for_textbelt(text)


def _sanitize_for_textbelt(msg: str) -> str:
    """Lightly scrub SMS content to dodge Textbelt's URL heuristics."""

    scrubbed = re.sub(r"https?://\S+", "[link]", msg, flags=re.I)
    scrubbed = re.sub(r"\b(www)\.", r"\1•", scrubbed, flags=re.I)
    scrubbed = re.sub(r"\b(Mr|Mrs|Ms|Dr|St|No|Vs)\.(?=\s)", r"\1", scrubbed)
    return scrubbed


def _default_sms_to() -> str:
    """Prefer Textbelt default, then Twilio defaults, then blank."""

    return (
        cfg_get("TEXTBELT_DEFAULT_TO")
        or cfg_get("TWILIO_TO_PHONE")
        or cfg_get("MY_PHONE_NUMBER")
        or ""
    )


def _textbelt_send_core(to: str, msg: str):
    """Core Textbelt sender used by both SMS Test and Wizard.

    Returns (ok: bool, text_id: str | None, resp_json: dict | None)
    """

    if requests is None:
        return False, None, {"error": "requests not installed"}

    key = cfg_get("TEXTBELT_KEY", "")
    if not key:
        return False, None, {"error": "TEXTBELT_KEY missing in config/env"}

    base = (cfg_get("TEXTBELT_ENDPOINT", "https://textbelt.com").rstrip("/"))
    reply = cfg_get("TEXTBELT_REPLY_WEBHOOK_URL", "")
    if not reply:
        pub = cfg_get("PUBLIC_BASE_URL", "")
        if pub:
            reply = pub.rstrip("/") + "/api/xcom/textbelt/reply"
    secret = cfg_get("TEXTBELT_WEBHOOK_SECRET", "")
    if reply and secret and "secret=" not in reply:
        sep = "&" if "?" in reply else "?"
        reply = f"{reply}{sep}secret={secret}"

    try:
        payload = {"phone": to, "message": msg, "key": key}
        if reply:
            payload["replyWebhookUrl"] = reply
        r = requests.post(  # type: ignore[misc]
            f"{base}/text",
            data=payload,
            timeout=20,
        )
        resp = r.json()
        ok = bool(resp.get("success"))
        tid = resp.get("textId") or resp.get("id") or ""
        if ok and tid:
            global _LAST_TEXTBELT_ID
            _LAST_TEXTBELT_ID = str(tid)
        return ok, tid, resp

    except Exception as e:  # pragma: no cover
        return False, None, {"error": str(e)}


def _textbelt_key() -> str:
    """Resolve TEXTBELT_KEY from config/env or prompt once."""

    key = cfg_get("TEXTBELT_KEY", "")
    if key:
        return key

    print("TEXTBELT_KEY not found in config/env.")
    key = input("Enter your Textbelt key (or leave blank to cancel): ").strip()
    return key


def _textbelt_sms_send() -> None:
    _print_header()
    print(f"{ICON['link']}  Textbelt SMS (no registration)\n")

    if requests is None:
        print("requests not available. Run: pip install requests")
        _pause()
        return

    key = _textbelt_key()
    if not key:
        print("Cancelled.")
        _pause()
        return

    # Persist key to env/cache so shared sender can reuse it
    if not cfg_get("TEXTBELT_KEY"):
        os.environ["TEXTBELT_KEY"] = key
        if _CFG_CACHE is not None:
            _CFG_CACHE["TEXTBELT_KEY"] = key

    default_to = _default_sms_to()
    to = input(f"Send to (E.164, default={default_to or 'unset'}): ").strip() or default_to
    if not _E164.match(to):
        print("Invalid E.164 number. Use +1… for US.")
        _pause()
        return

    raw = input("Message (default: 'Console SMS test'): ").strip() or "Console SMS test"
    msg = _sanitize_for_textbelt(raw)

    ok, text_id, resp_json = _textbelt_send_core(to, msg)

    if isinstance(resp_json, dict):
        print("\nResponse:\n" + json.dumps(resp_json, indent=2))

    if ok:
        quota = resp_json.get("quotaRemaining") if isinstance(resp_json, dict) else "n/a"
        print(
            f"\n✅ Queued via Textbelt — textId={text_id or 'n/a'}  (quotaRemaining={quota})"
        )
    else:
        err = resp_json.get("error") if isinstance(resp_json, dict) else None
        print("\n❌ Not sent." + (f" Reason: {err}" if err else ""))

    print()
    _pause()


# -------------------- Canned Scenarios --------------------------------------
def _canned_scenarios():
    while True:
        _print_header()

        print(f"{ICON['scene']}  Canned Scenarios\n")
        print("  1) Alert Demo - SMS")
        print("  2) Alert Demo - Voice")
        print(f"  0) {ICON['back']} Back")

        sel = (input("\n→ ").strip() or "").lower()

        if sel in {"0", "b", "back"}:
            return
        elif sel == "1":
            # ---- Alert Demo - SMS (Textbelt) ----
            msg = build_canned_alert_sms()

            # allow user to override number, default to configured
            def_to = _default_sms_to()
            prompt = f"Send to (E.164, default={def_to or 'unset'}): "
            to_in = input(prompt).strip()
            to = (to_in or def_to)

            if not to or not _E164.match(to):
                print("Invalid E.164 number.")
                time.sleep(0.9)
                continue

            # optional delay
            d_in = input("Delay seconds (default 0): ").strip()
            try:
                delay = max(0, int(d_in)) if d_in else 0
            except Exception:
                delay = 0

            if delay:
                print(f"⏳ Delaying {delay}s…")
                time.sleep(delay)

            ok, text_id, resp = _textbelt_send_core(to, msg)
            if isinstance(resp, dict):
                print("\nResponse:\n" + json.dumps(resp, indent=2))
            if ok:
                print(f"\n✅ Queued via Textbelt — textId={text_id or 'n/a'} to={to}")
            else:
                err = resp.get("error") if isinstance(resp, dict) else None
                print(
                    f"\n❌ Textbelt send failed. {('Reason: ' + err) if err else ''}"
                )
            _pause()
        elif sel == "2":
            # ---- Alert Demo - Voice (Twilio voice path) ----
            vmsg = " Air-in-line alarm detected in room 55 — patient is Mr Rogers"

            # allow user to override call target; default to config
            from copy import deepcopy

            tw = TwilioConfig.from_env()
            def_to = (
                tw.to_phone
                or cfg_get("TWILIO_TO_PHONE")
                or cfg_get("MY_PHONE_NUMBER")
            )
            to_in = input(f"Call to (E.164, default={def_to or 'unset'}): ").strip()
            to = (to_in or def_to)

            if not to or not _E164.match(to):
                print("Invalid E.164 number.")
                time.sleep(0.9)
                continue

            d_in = input("Delay seconds (default 0): ").strip()
            try:
                delay = max(0, int(d_in)) if d_in else 0
            except Exception:
                delay = 0

            if delay:
                print(f"⏳ Delaying {delay}s…")
                time.sleep(delay)

            # Override recipient in context so voice targets the chosen number
            twc = deepcopy(tw.as_context_node())
            twc["default_to_phone"] = to
            extra_ctx = {"recipient": to, "twilio": twc}

            _do_dispatch("voice", {"voice": True}, vmsg, extra_ctx)
        else:
            print("Unknown selection.")
            time.sleep(0.7)


def _textbelt_status_check() -> None:
    _print_header()
    print(f"{ICON['magnifier']}  Textbelt status (by textId)\n")

    if requests is None:
        print("requests not available. Run: pip install requests")
        _pause()
        return

    tid = input(f"textId (default={_LAST_TEXTBELT_ID or 'none'}): ").strip() or _LAST_TEXTBELT_ID
    if not tid:
        print("No textId yet — send a Textbelt SMS first.")
        _pause()
        return

    try:
        base = (cfg_get("TEXTBELT_ENDPOINT", "https://textbelt.com").rstrip("/"))
        response = requests.get(  # type: ignore[misc]
            f"{base}/status/{tid}",
            timeout=15,
        )
        resp_json = response.json()
        print("\nStatus:\n" + json.dumps(resp_json, indent=2))

        delivered = resp_json.get("status") == "DELIVERED" or bool(resp_json.get("delivered"))
        print("\n📬 Delivered" if delivered else "\n⏳ Not delivered yet / unknown")

    except Exception as exc:  # pragma: no cover - network call
        print("❌ Status lookup failed:", exc)

    print()
    _pause()


def main() -> None:
    cfg, path = load_xcom_config(base_dir=Path(__file__).parent)
    effective_env = apply_xcom_env(cfg)
    print(
        f"[XCom Config] loaded_from={path or 'N/A'} effective={mask_for_log(effective_env)}"
    )
    launch()


if __name__ == "__main__":
    main()
