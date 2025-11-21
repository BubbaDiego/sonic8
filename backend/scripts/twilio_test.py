#!/usr/bin/env python3
"""Twilio test script for authentication and optional voice call.

Used by Sonic Launch Pad's "Verify Twilio" menu. It is intentionally verbose:
it shows where your credentials are loaded from and explains common failures.
"""

import argparse
__test__ = False
import os
import sys
from pathlib import Path
from typing import Optional, List

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv, dotenv_values
except Exception:  # pragma: no cover - fallback if dotenv is missing
    def load_dotenv(*_a, **_k):
        return False

    def dotenv_values(*_a, **_k):
        return {}

ROOT_DIR = Path(__file__).resolve().parents[2]
if not load_dotenv(ROOT_DIR / ".env"):
    load_dotenv(ROOT_DIR / ".env.example")

import requests
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
except Exception:  # pragma: no cover - optional dependency
    Client = None

    class TwilioRestException(Exception):
        pass


# ---------------------------------------------------------------------------
# Helpers: masking + config snapshot
# ---------------------------------------------------------------------------

def _mask(value: str, head: int = 4) -> str:
    """Return a safely masked version of a secret-like string."""
    if not value:
        return "MISSING"
    if len(value) <= head:
        return "*" * len(value)
    return value[:head] + "…" + "*" * (len(value) - head - 1)


def _twilio_config_snapshot(root: Path) -> None:
    """Print where Twilio config is coming from (.env, .env.example, env)."""
    env_path = root / ".env"
    example_path = root / ".env.example"

    try:
        env_vals = dotenv_values(env_path) if env_path.exists() else {}
        example_vals = dotenv_values(example_path) if example_path.exists() else {}
    except Exception:
        env_vals = {}
        example_vals = {}

    def src(name: str) -> str:
        sources = []
        if name in os.environ:
            sources.append("env")
        if name in env_vals:
            sources.append(".env")
        if name in example_vals:
            sources.append(".env.example")
        return ", ".join(sources) or "not set"

    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_phone = (
        os.getenv("TWILIO_FROM_PHONE")
        or os.getenv("TWILIO_PHONE_NUMBER", "")
    )
    to_phone = (
        os.getenv("TWILIO_TO_PHONE")
        or os.getenv("MY_PHONE_NUMBER", "")
    )

    print("──────────────── Twilio config snapshot ────────────────")
    print(f"Repo root       : {root}")
    print(f".env            : {'present' if env_path.exists() else 'missing'}")
    print(f".env.example    : {'present' if example_path.exists() else 'missing'}")
    print()
    print("Twilio credentials (masked):")
    print(f"  TWILIO_ACCOUNT_SID : {_mask(sid)}  [source: {src('TWILIO_ACCOUNT_SID')}]")
    print(f"  TWILIO_AUTH_TOKEN  : {_mask(token)}  [source: {src('TWILIO_AUTH_TOKEN')}]")
    print()
    print("Voice settings (masked):")
    print(f"  FROM phone         : {_mask(from_phone, head=6)}")
    print(f"  TO phone           : {_mask(to_phone, head=6)}")
    print("────────────────────────────────────────────────────────")
    print()


# ---------------------------------------------------------------------------
# Twilio operations
# ---------------------------------------------------------------------------

def authenticate(account_sid: str, auth_token: str) -> Client:
    """Return a Twilio client if credentials are valid, else raise."""
    client = Client(account_sid, auth_token)
    # This will raise TwilioRestException on 401/20003 etc.
    client.api.accounts(account_sid).fetch()
    return client


def place_call(client: Client, from_phone: str, to_phone: str, message: str) -> None:
    """Trigger a simple Programmable Voice call using inline TwiML."""
    twiml = f"<Response><Say>{message}</Say></Response>"
    client.calls.create(from_=from_phone, to=to_phone, twiml=twiml)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Test Twilio credentials and optionally place a voice call",
    )
    parser.add_argument("--sid", help="Twilio Account SID")
    parser.add_argument("--token", help="Twilio Auth Token")
    parser.add_argument("--from-phone", help="From phone number")
    parser.add_argument("--to-phone", help="To phone number")
    parser.add_argument(
        "--message",
        help="Custom message to speak during the test call",
        default="Sonic Twilio test call",
    )
    args = parser.parse_args(argv)

    # Resolve credentials from args or environment.
    sid = args.sid or os.getenv("TWILIO_ACCOUNT_SID", "")
    token = args.token or os.getenv("TWILIO_AUTH_TOKEN", "")

    # Show where config is coming from before we hit Twilio.
    _twilio_config_snapshot(ROOT_DIR)

    if not sid or not token:
        print("❌ TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN are not set.")
        print("   Check your .env / environment – see snapshot above.")
        return 1

    # Authentication check
    try:
        client = authenticate(sid, token)
        print("✅ Authentication succeeded")
    except TwilioRestException as exc:
        print("❌ Authentication failed")
        status = getattr(exc, "status", None)
        code = getattr(exc, "code", None)
        msg = getattr(exc, "msg", str(exc))
        print(f"HTTP Status: {status}")
        print(f"Error Code: {code}")
        print(f"Message: {msg}")
        more_info = getattr(exc, "more_info", None)
        if more_info:
            print(f"More Info: {more_info}")

        # Teaching hints for the classic 401 / 20003 auth failure
        if status == 401 and code == 20003:
            print()
            print("Hint: Twilio error 20003 = 'Authenticate'.")
            print("This almost always means your TWILIO_ACCOUNT_SID and/or")
            print("TWILIO_AUTH_TOKEN are wrong for this account, or you're")
            print("using test credentials where live credentials are required.")
            print("Double-check:")
            print("  • The SID/token shown (masked) in the snapshot above")
            print("  • That they match the LIVE creds in Twilio Console")
            print("  • That .env is the file Sonic is actually loading")
        return 1
    except requests.exceptions.RequestException as exc:
        print("❌ Network error while contacting Twilio")
        print(str(exc))
        return 1
    except Exception as exc:
        print("❌ Unexpected error")
        print(str(exc))
        return 1

    from_phone = args.from_phone or os.getenv("TWILIO_FROM_PHONE") or os.getenv("TWILIO_PHONE_NUMBER")
    to_phone = args.to_phone or os.getenv("TWILIO_TO_PHONE") or os.getenv("MY_PHONE_NUMBER")

    if from_phone and to_phone:
        try:
            place_call(client, from_phone, to_phone, args.message)
            print(f"✅ Call placed from {from_phone} to {to_phone}")
        except TwilioRestException as exc:
            print("❌ Failed to place call")
            status = getattr(exc, "status", None)
            code = getattr(exc, "code", None)
            msg = getattr(exc, "msg", str(exc))
            print(f"HTTP Status: {status}")
            print(f"Error Code: {code}")
            print(f"Message: {msg}")
            more_info = getattr(exc, "more_info", None)
            if more_info:
                print(f"More Info: {more_info}")
            return 1
        except Exception as exc:
            print("❌ Unexpected error placing call")
            print(str(exc))
            return 1
    else:
        print("(Skipping call: provide --from-phone/--to-phone or set TWILIO_FROM_PHONE/TWILIO_TO_PHONE)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
