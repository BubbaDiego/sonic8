#!/usr/bin/env python3
"""
send_test_sms.py — Twilio SMS tester (auto-loads .env; no CLI typing required)

Reads credentials and numbers from a .env file (or process environment) and sends
a one-off SMS via Twilio.

Expected variables in .env (E.164 numbers):
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN=your_auth_token
  TWILIO_PHONE_NUMBER=+15551234567
  MY_PHONE_NUMBER=+15557654321
Optional:
  SMS_TEST_BODY="This is a Twilio test SMS."
  
You can still override with flags if you want in the future, but running with no
arguments works as long as .env is present.
"""

import os
import sys
import argparse
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Load .env automatically (prefer python-dotenv; fall back to local parser)
# ---------------------------------------------------------------------------
def _load_dotenv() -> Tuple[bool, str]:
    """Attempt to load a .env file into os.environ.
    Returns (loaded, path) where 'loaded' indicates if anything was loaded,
    and 'path' is the resolved path attempted.
    """
    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore
        path = find_dotenv(filename=".env", usecwd=True)
        if path:
            load_dotenv(dotenv_path=path, override=False)
            return True, path
        # Fallback search: script dir, then parent dir
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [os.path.join(script_dir, ".env"),
                      os.path.join(os.path.dirname(script_dir), ".env")]
        for p in candidates:
            if os.path.isfile(p):
                load_dotenv(dotenv_path=p, override=False)
                return True, p
        return False, ""
    except Exception:
        # Minimal parser (KEY=VALUE, quotes ok, ignore comments/blank/export)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search = [os.path.join(os.getcwd(), ".env"),
                  os.path.join(script_dir, ".env"),
                  os.path.join(os.path.dirname(script_dir), ".env")]
        for p in search:
            if not os.path.isfile(p):
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.lower().startswith("export "):
                            line = line[7:].strip()
                        if "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        os.environ.setdefault(k, v)
                return True, p
            except Exception:
                continue
        return False, ""

_loaded, _dotenv_path = _load_dotenv()
# You can uncomment next line to see where it loaded from:
# print(f"[info] .env loaded from: {_dotenv_path}" if _loaded else "[info] no .env found")

# ---------------------------------------------------------------------------
# Twilio import
# ---------------------------------------------------------------------------
def _exit(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr if code else sys.stdout)
    sys.exit(code)

try:
    from twilio.rest import Client  # type: ignore
except Exception as e:
    _exit("Twilio SDK not installed. Install it with:\n\n  pip install twilio\n", code=2)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _first_env(*names: str) -> Optional[str]:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None

def resolve_config(args) -> Tuple[str, str, str, str, str]:
    """Resolve all required fields from args or environment/.env."""
    sid = args.sid or _first_env("TWILIO_ACCOUNT_SID", "TWILIO_SID", "ACCOUNT_SID")
    token = args.token or _first_env("TWILIO_AUTH_TOKEN", "TWILIO_TOKEN", "AUTH_TOKEN")
    from_number = args.from_number or _first_env("TWILIO_PHONE_NUMBER", "TWILIO_FROM_NUMBER", "FROM_NUMBER", "DEFAULT_FROM_PHONE")
    to_number = args.to_number or _first_env("MY_PHONE_NUMBER", "TO_NUMBER", "DEFAULT_TO_PHONE")
    body = args.body or os.getenv("SMS_TEST_BODY") or "This is a Twilio test SMS."
    return sid, token, from_number, to_number, body

def send_sms(account_sid: str, auth_token: str, from_number: str, to_number: str, body: str) -> str:
    client = Client(account_sid, auth_token)
    msg = client.messages.create(body=body, from_=from_number, to=to_number)
    return msg.sid

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Send a one-off test SMS via Twilio.")
    # Flags remain optional; env/.env are the default source of truth
    p.add_argument("--sid", default=None, help="Twilio Account SID (or .env TWILIO_ACCOUNT_SID)")
    p.add_argument("--token", default=None, help="Twilio Auth Token (or .env TWILIO_AUTH_TOKEN)")
    p.add_argument("--from-number", dest="from_number", default=None, help="Sender phone (E.164) (or .env TWILIO_PHONE_NUMBER)")
    p.add_argument("--to", dest="to_number", default=None, help="Recipient phone (E.164) (or .env MY_PHONE_NUMBER)")
    p.add_argument("--body", default=None, help="Message body text (or .env SMS_TEST_BODY)")
    p.add_argument("--dry-run", action="store_true", help="Print what would be sent without calling Twilio")
    args = p.parse_args(argv)

    sid, token, from_number, to_number, body = resolve_config(args)
    missing = [name for name, val in {
        "TWILIO_ACCOUNT_SID": sid,
        "TWILIO_AUTH_TOKEN": token,
        "TWILIO_PHONE_NUMBER": from_number,
        "MY_PHONE_NUMBER": to_number,
    }.items() if not val]

    if missing:
        tpl = (
            "Missing required values from .env or environment:\n"
            f"  {', '.join(missing)}\n\n"
            "Example .env:\n"
            "  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"
            "  TWILIO_AUTH_TOKEN=your_auth_token\n"
            "  TWILIO_PHONE_NUMBER=+15551234567\n"
            "  MY_PHONE_NUMBER=+15557654321\n"
        )
        _exit(tpl, code=2)

    # Light validation
    for label, number in (("from", from_number), ("to", to_number)):
        if not str(number).startswith("+") or not all(ch.isdigit() or ch == "+" for ch in str(number)):
            print(f"[warn] {label} number should be in E.164 format, got: {number}", file=sys.stderr)

    if args.dry_run:
        print("[DRY-RUN] Would send SMS:")
        print(f"  From: {from_number}")
        print(f"  To:   {to_number}")
        print(f"  Body: {body}")
        return 0

    try:
        sid_out = send_sms(sid, token, from_number, to_number, body)
        print(f"✅ SMS sent. Message SID: {sid_out}")
        return 0
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
