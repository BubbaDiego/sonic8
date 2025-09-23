r"""
Usage:
  (.venv)\Scripts\python backend\scripts\twilio_voice_smoke_test.py +1AAA5551212 "Sonic voice path OK"

Loads .env automatically (project root or backend/.env).
Required env:
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
Optional:
  TWILIO_TEST_TO or TWILIO_DEFAULT_TO (used if no CLI "to" is provided)
You may also set SONIC_ENV_PATH to point explicitly to your .env file.
"""
import os
import sys
from pathlib import Path
from twilio.rest import Client

def _load_dotenv():
    try:
        from dotenv import load_dotenv, find_dotenv
    except Exception:
        return None

    # 1) Explicit override
    explicit = os.getenv("SONIC_ENV_PATH")
    if explicit and Path(explicit).exists():
        load_dotenv(explicit, override=False)
        print(f"dotenv: loaded {explicit}")
        return explicit

    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / ".env",   # C:\sonic5\.env
        here.parents[1] / ".env",   # C:\sonic5\backend\.env
        Path.cwd() / ".env"         # current working dir
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(p, override=False)
            print(f"dotenv: loaded {p}")
            return str(p)

    found = find_dotenv(usecwd=True)
    if found:
        load_dotenv(found, override=False)
        print(f"dotenv: loaded {found}")
        return found
    print("dotenv: no .env file found")
    return None

def main():
    _load_dotenv()

    # CLI args
    to = None
    if len(sys.argv) > 1 and sys.argv[1].startswith('+'):
        to = sys.argv[1]
    msg = sys.argv[2] if len(sys.argv) > 2 else "Sonic voice path OK"

    # Env
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    tok = os.getenv("TWILIO_AUTH_TOKEN")
    frm = os.getenv("TWILIO_PHONE_NUMBER") or os.getenv("TWILIO_FROM")
    if not to:
        to = os.getenv("TWILIO_TEST_TO") or os.getenv("TWILIO_DEFAULT_TO")

    missing = [k for k, v in {
        "TWILIO_ACCOUNT_SID": sid,
        "TWILIO_AUTH_TOKEN": tok,
        "TWILIO_PHONE_NUMBER/TWILIO_FROM": frm,
        "TO_NUMBER": to
    }.items() if not v]
    if missing:
        print("Missing Twilio settings:", ", ".join(missing))
        print("Tip: ensure they are in your .env or OS env. You can set SONIC_ENV_PATH to your .env explicitly.")
        sys.exit(2)

    client = Client(sid, tok)
    call = client.calls.create(
        to=to,
        from_=frm,
        twiml=f'<Response><Say>Sonic check. {msg}</Say></Response>'
    )
    print(f"✅ Voice call initiated: {call.sid} → {to}")

if __name__ == "__main__":
    main()
