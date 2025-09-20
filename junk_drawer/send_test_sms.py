#!/usr/bin/env python3
"""
send_test_sms.py — minimal standalone Twilio SMS tester

Usage examples:
  # Using environment variables for credentials and numbers
  export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  export TWILIO_AUTH_TOKEN="your_auth_token"
  export TWILIO_PHONE_NUMBER="+15551234567"
  export MY_PHONE_NUMBER="+15557654321"
  python send_test_sms.py --body "Hello from the standalone tester"

  # Or pass everything via CLI flags (overrides env vars)
  python send_test_sms.py --sid AC... --token ... --from-number +15551234567 --to +15557654321 --body "Ping"

Notes:
  * Trial accounts can only send to verified numbers.
  * Phone numbers must be in E.164 format (e.g., +15551234567).
"""

import os
import sys
import argparse
from typing import Optional

def _exit(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr if code else sys.stdout)
    sys.exit(code)

try:
    from twilio.rest import Client  # type: ignore
except Exception as e:
    _exit(
        "Twilio SDK is not installed. Install it with:\n\n  pip install twilio\n\n"
        f"Import error: {e}",
        code=2,
    )

def send_sms(account_sid: str, auth_token: str, from_number: str, to_number: str, body: str) -> str:
    client = Client(account_sid, auth_token)
    msg = client.messages.create(body=body, from_=from_number, to=to_number)
    return msg.sid

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Send a one-off test SMS via Twilio.")
    p.add_argument("--sid", default=os.getenv("TWILIO_ACCOUNT_SID"), help="Twilio Account SID (or env TWILIO_ACCOUNT_SID)")
    p.add_argument("--token", default=os.getenv("TWILIO_AUTH_TOKEN"), help="Twilio Auth Token (or env TWILIO_AUTH_TOKEN)")
    p.add_argument("--from-number", dest="from_number", default=os.getenv("TWILIO_PHONE_NUMBER"), help="Sender phone (E.164) (or env TWILIO_PHONE_NUMBER)")
    p.add_argument("--to", dest="to_number", default=os.getenv("MY_PHONE_NUMBER"), help="Recipient phone (E.164) (or env MY_PHONE_NUMBER)")
    p.add_argument("--body", default="This is a Twilio test SMS.", help="Message body text")
    p.add_argument("--dry-run", action="store_true", help="Print what would be sent without calling Twilio")
    args = p.parse_args(argv)

    missing = [k for k, v in {
        "--sid": args.sid,
        "--token": args.token,
        "--from-number": args.from_number,
        "--to": args.to_number,
    }.items() if not v]
    if missing:
        p.print_help(sys.stderr)
        _exit("\nMissing required values: " + ", ".join(missing), code=2)

    # Very light validation
    for label, number in (("from", args.from_number), ("to", args.to_number)):
        if not str(number).startswith("+") or not all(ch.isdigit() or ch == "+" for ch in str(number)):
            print(f"[warn] {label} number should be in E.164 format, got: {number}", file=sys.stderr)

    if args.dry_run:
        print("[DRY-RUN] Would send SMS:")
        print(f"  From: {args.from_number}") 
        print(f"  To:   {args.to_number}") 
        print(f"  Body: {args.body}")
        return 0

    try:
        sid = send_sms(args.sid, args.token, args.from_number, args.to_number, args.body)
        print(f"✅ SMS sent. Message SID: {sid}")
        return 0
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
