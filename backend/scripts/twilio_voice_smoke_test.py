"""
Usage:
  .venv\Scripts\python backend\scripts\twilio_voice_smoke_test.py +1AAA5551212 "Sonic voice path OK"
Requires:
  pip install twilio
Env needed:
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
Optional:
  If no 'to' is provided on CLI, will use TWILIO_TEST_TO or TWILIO_DEFAULT_TO.
"""
import os
import sys

from twilio.rest import Client


def main():
    to = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith('+') else os.getenv("TWILIO_TEST_TO") or os.getenv("TWILIO_DEFAULT_TO")
    msg = sys.argv[2] if len(sys.argv) > 2 else "Sonic voice path OK"
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    tok = os.getenv("TWILIO_AUTH_TOKEN")
    frm = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([sid, tok, frm, to]):
        print("Missing Twilio env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, and TWILIO_TEST_TO/TWILIO_DEFAULT_TO")
        sys.exit(2)

    client = Client(sid, tok)
    call = client.calls.create(
        to=to,
        from_=frm,
        twiml=f'<Response><Say>Sonic check. {msg}</Say></Response>'
    )
    print(f"✅ Voice call initiated: {call.sid}")


if __name__ == "__main__":
    main()
