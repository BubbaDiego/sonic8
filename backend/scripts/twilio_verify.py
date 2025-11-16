#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from dotenv import load_dotenv
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


# --------------------------------------------------------------------------------------
# Paths / config
# --------------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CONFIG_DIR = BACKEND / "config"
XCOM_PROVIDERS_PATH = CONFIG_DIR / "xcom_providers.json"

ENV_CANDIDATES = [
    ROOT / ".env",
    BACKEND / ".env",
]


def load_env() -> None:
    """Best-effort load of .env files (root + backend)."""
    for path in ENV_CANDIDATES:
        if path.exists():
            load_dotenv(path, override=False)


def mask(s: str, keep: int = 4) -> str:
    """Mask secrets for display: ABCD…WXYZ."""
    s = str(s)
    if len(s) <= keep * 2:
        return "…" * len(s)
    return f"{s[:keep]}…{s[-keep:]}"


def load_voice_provider() -> Tuple[Dict[str, Any], List[str]]:
    """
    Load the 'voice' Twilio provider block from xcom_providers.json.

    Returns (voice_config, issues)

    issues is a list of strings explaining config problems:
      - 'providers-file:...'
      - 'providers-json'
      - 'voice-block-missing'
      - 'provider!=twilio'
      - missing keys like 'account_sid', 'auth_token', ...
    """
    issues: List[str] = []

    if not XCOM_PROVIDERS_PATH.exists():
        issues.append(f"providers-file:{XCOM_PROVIDERS_PATH} (missing)")
        return {}, issues

    try:
        data = json.loads(XCOM_PROVIDERS_PATH.read_text(encoding="utf-8") or "{}")
    except Exception as exc:
        issues.append(f"providers-json: {exc}")
        return {}, issues

    if not isinstance(data, dict):
        issues.append("providers-json: root is not an object")
        return {}, issues

    voice = data.get("voice") or {}
    if not isinstance(voice, dict):
        issues.append("voice-block-missing")
        return {}, issues

    provider = str(voice.get("provider") or "").lower()
    if provider != "twilio":
        issues.append(f"provider!=twilio (got {provider!r})")

    for key in ("account_sid", "auth_token", "from", "to", "flow_sid"):
        if not voice.get(key):
            issues.append(f"missing:{key}")

    return voice, issues


# --------------------------------------------------------------------------------------
# Twilio helpers
# --------------------------------------------------------------------------------------

def print_config_snapshot(voice_cfg: Dict[str, Any], issues: List[str]) -> None:
    """Print where we loaded config from and what we see (masked)."""
    print("════════ Twilio config snapshot ════════")
    print(f"📄 Providers file : {XCOM_PROVIDERS_PATH}")
    print(f"📦 Loaded .env    : {[str(p) for p in ENV_CANDIDATES if p.exists()] or 'none'}")

    if not voice_cfg:
        print("⚠️  No usable 'voice' provider config loaded.")
    else:
        print("🔊 Voice provider : twilio")
        print(f"   account_sid    : {mask(voice_cfg.get('account_sid', ''))}")
        print(f"   auth_token     : {mask(voice_cfg.get('auth_token', ''))}")
        print(f"   from           : {voice_cfg.get('from')!r}")
        print(f"   to             : {voice_cfg.get('to')!r}")
        print(f"   flow_sid       : {mask(voice_cfg.get('flow_sid', ''))}")

    if issues:
        print("\n⚠️  Config issues detected:")
        for item in issues:
            print(f"   - {item}")
        print("   (fix these before worrying about Twilio’s 401s)\n")


def explain_twilio_error(exc: TwilioRestException) -> None:
    """Add some human-level explanation for common Twilio errors."""
    print(f"❌ Authentication failed against Twilio")
    print(f"   HTTP Status : {exc.status}")
    print(f"   Error Code  : {exc.code}")
    print(f"   Message     : {exc.msg}")
    if getattr(exc, "more_info", None):
        print(f"   more_info   : {exc.more_info}")

    # 20003 = Permission Denied / Authenticate – usually bad SID/token
    if exc.code == 20003:
        print("\n📚 Hint for 20003 (Permission Denied / Authenticate):")
        print("   • Most often: Account SID + Auth Token combo is wrong.")
        print("   • Or using test credentials against a live account.")
        print("   • Or the account is suspended / closed.")
        print("   • Double-check the SID/token shown above against Twilio Console.")
        print("   • Make sure you aren’t mixing sub-account creds with master account.")


def get_client(account_sid: str, auth_token: str) -> Client:
    """Create a Twilio client *and* sanity-check credentials via Accounts API."""
    client = Client(account_sid, auth_token)
    try:
        acct = client.api.accounts(account_sid).fetch()
    except TwilioRestException as exc:
        explain_twilio_error(exc)
        raise
    else:
        name = getattr(acct, "friendly_name", "") or "<unnamed>"
        print(f"\n✅ Auth OK: {name} ({acct.sid})")
    return client


def pick_first_to(to_value: Any) -> str:
    """Handle 'to' being either a string or list in providers file."""
    if isinstance(to_value, str):
        return to_value
    if isinstance(to_value, (list, tuple)) and to_value:
        return str(to_value[0])
    return ""


# --------------------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------------------

def verify_auth_only() -> int:
    """Mode: just verify SID/token with Twilio; no call."""
    load_env()
    voice_cfg, issues = load_voice_provider()
    print_config_snapshot(voice_cfg, issues)

    if issues:
        # Config is clearly broken – don’t even hit Twilio.
        return 2

    sid = str(voice_cfg["account_sid"])
    token = str(voice_cfg["auth_token"])

    try:
        get_client(sid, token)
    except TwilioRestException:
        return 1

    return 0


def verify_with_call() -> int:
    """Mode: verify auth and trigger the Studio Flow call."""
    load_env()
    voice_cfg, issues = load_voice_provider()
    print_config_snapshot(voice_cfg, issues)

    if issues:
        return 2

    sid = str(voice_cfg["account_sid"])
    token = str(voice_cfg["auth_token"])
    flow_sid = str(voice_cfg["flow_sid"])
    from_phone = str(voice_cfg["from"])
    to_phone = pick_first_to(voice_cfg.get("to"))

    if not to_phone:
        print("❌ 'to' number missing or empty in xcom_providers.json")
        return 2

    try:
        client = get_client(sid, token)
    except TwilioRestException:
        return 1

    print(f"\n📞 Triggering Studio Flow {flow_sid}")
    print(f"   from {from_phone} → {to_phone}")

    try:
        execution = client.studio.v2.flows(flow_sid).executions.create(
            to=to_phone,
            from_=from_phone,
            parameters={"origin": "sonic-twilio-verify"},
        )
    except TwilioRestException as exc:
        print("\n❌ Flow execution failed")
        print(f"   HTTP Status : {exc.status}")
        print(f"   Error Code  : {exc.code}")
        print(f"   Message     : {exc.msg}")
        if getattr(exc, "more_info", None):
            print(f"   more_info   : {exc.more_info}")
        return 1

    print(f"\n✅ Call queued; execution SID={execution.sid}")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sonic Twilio verification helper (auth-only or auth+call)."
    )
    parser.add_argument(
        "--mode",
        choices=["auth", "call"],
        default="auth",
        help="auth=verify credentials only, call=also trigger Studio Flow call",
    )
    args = parser.parse_args(argv)

    if args.mode == "auth":
        return verify_auth_only()
    return verify_with_call()


if __name__ == "__main__":
    raise SystemExit(main())
