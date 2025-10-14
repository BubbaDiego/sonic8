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
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.core.xcom_core.xcom_config_loader import (
    apply_xcom_env,
    load_xcom_config,
    mask_for_log,
)

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
}

BANNER = r"""
  ╔════════════════════════════════════════════════════════╗
  ║                    X C o m   C o n s o l e            ║
  ║          Cross-Communication Ops & Diagnostics        ║
  ╚════════════════════════════════════════════════════════╝
"""

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


def _read_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _read_env_any(*names: str, default: str = "") -> str:
    for name in names:
        value = _read_env(name)
        if value:
            return value
    return default


def _visible(s: Optional[str]) -> bool:
    return bool(s and str(s).strip())


@dataclass
class TwilioConfig:
    account_sid: str = ""
    auth_token: str = ""
    flow_sid: str = ""
    default_from_phone: str = ""
    default_to_phone: str = ""

    @classmethod
    def from_env(cls) -> "TwilioConfig":
        return cls(
            account_sid=_read_env_any("TWILIO_ACCOUNT_SID", "TWILIO_SID"),
            auth_token=_read_env("TWILIO_AUTH_TOKEN"),
            flow_sid=_read_env("TWILIO_FLOW_SID"),
            default_from_phone=_read_env_any(
                "TWILIO_DEFAULT_FROM_PHONE",
                "TWILIO_PHONE_NUMBER",
                "TWILIO_FROM",
            ),
            default_to_phone=_read_env_any(
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
            "from": _visible(self.default_from_phone),
            "to": _visible(self.default_to_phone),
        }

    def as_context_node(self) -> Dict[str, Any]:
        # Match the structure xcom_core expects for context["twilio"]
        return {
            "enabled": True,
            "account_sid": self.account_sid,
            "auth_token": self.auth_token,
            "flow_sid": self.flow_sid,
            "default_from_phone": self.default_from_phone,
            "default_to_phone": self.default_to_phone,
        }


def _print_header():
    _clear()
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
    _row("  From phone", tw.default_from_phone or "(missing)", tw_map["from"])
    _row("  To phone", tw.default_to_phone or "(missing)", tw_map["to"])

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
        "recipient": tw.default_to_phone or _read_env("MY_PHONE_NUMBER"),
        "twilio": tw.as_context_node(),
        # PREVIEW sugar used by xcom_core debug prints
        "positions": [{"asset": "SOL"}, {"asset": "ETH"}],
    }
    return ctx


def _do_dispatch(label: str, channels: Dict[str, Any], message: str):
    if not _ensure_dispatch():
        return

    result = {
        "breach": True,  # console tests force "notify"
        "level": next((k for k, v in channels.items() if v), "LOW"),
        "message": message,
    }
    try:
        summary = dispatch_notifications(
            monitor_name="xcom_console",
            result=result,
            channels=channels,
            context=_compose_context(message, level=result["level"]),
        )
        print("\nSummary:\n" + json.dumps(summary, indent=2))
    except Exception as e:
        print(f"\n{ICON['err']} dispatch failed: {e}")
    print()
    _pause()


def _voice_test():
    _print_header()
    print(f"{ICON['voice']}  Voice Test (Twilio Studio)\n")
    msg = input("Message (default: 'Console test call'): ").strip() or "Console test call"
    _do_dispatch("voice", {"voice": True}, msg)


def _system_test():
    _print_header()
    print(f"{ICON['sys']}  System Test (console)\n")
    msg = input("Message (default: 'Console system alert'): ").strip() or "Console system alert"
    _do_dispatch("system", {"system": True}, msg)


def _sms_test():
    _print_header()
    print(f"{ICON['sms']}  SMS Test\n")
    msg = input("Message (default: 'Console SMS test'): ").strip() or "Console SMS test"
    _do_dispatch("sms", {"sms": True}, msg)


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
    print(f"  1. {ICON['status']}  Status probe")
    print(f"  2. {ICON['gear']}  Inspect providers")
    print(f"  3. {ICON['voice']}  Voice test")
    print(f"  4. {ICON['sys']}  System test")
    print(f"  5. {ICON['sms']}  SMS test")
    print(f"  6. {ICON['tts']}  TTS test")
    print(f"  7. {ICON['hb']}  Heartbeat")
    print(f"  0. {ICON['exit']}  Exit")
    return input("\n→ ").strip().lower()


def launch():
    while True:
        _print_header()
        choice = _menu()
        if choice in ("0", "q", "quit", "exit"):
            _clear()
            return
        if choice == "1":
            _status_probe()
        elif choice == "2":
            _inspect_providers()
        elif choice == "3":
            _voice_test()
        elif choice == "4":
            _system_test()
        elif choice == "5":
            _sms_test()
        elif choice == "6":
            _tts_test()
        elif choice == "7":
            _heartbeat()
        else:
            print("\nUnknown selection.")
            time.sleep(0.8)


def main() -> None:
    cfg, path = load_xcom_config(base_dir=Path(__file__).parent)
    effective_env = apply_xcom_env(cfg)
    print(
        f"[XCom Config] loaded_from={path or 'N/A'} effective={mask_for_log(effective_env)}"
    )
    launch()


if __name__ == "__main__":
    main()
