import os
import argparse

from twilio.rest import Client

# ───────────────────────────────────────────────────────────────────
# 🔧 Load Twilio credentials from environment variables
#     or provide them via command-line arguments.
#
#     Required environment variables:
#       - TWILIO_ACCOUNT_SID
#       - TWILIO_AUTH_TOKEN
#       - TWILIO_PHONE_NUMBER
#       - RECIPIENT (destination phone number)
#
#     Example:
#       export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
#       export TWILIO_AUTH_TOKEN="your_auth_token"
#       export TWILIO_PHONE_NUMBER="+1234567890"
#       export RECIPIENT="+10987654321"
#       python backend/scripts/send_sms_demo.py --dry-run
# ───────────────────────────────────────────────────────────────────


def parse_args():
    """Parse command-line arguments, falling back to environment variables."""
    parser = argparse.ArgumentParser(description="Send a demo SMS using Twilio")
    parser.add_argument(
        "--account-sid",
        default=os.getenv("TWILIO_ACCOUNT_SID"),
        help="Twilio Account SID or set TWILIO_ACCOUNT_SID env var",
    )
    parser.add_argument(
        "--auth-token",
        default=os.getenv("TWILIO_AUTH_TOKEN"),
        help="Twilio Auth Token or set TWILIO_AUTH_TOKEN env var",
    )
    parser.add_argument(
        "--from-number",
        default=os.getenv("TWILIO_PHONE_NUMBER"),
        help="Twilio phone number or set TWILIO_PHONE_NUMBER env var",
    )
    parser.add_argument(
        "--to-number",
        default=os.getenv("RECIPIENT"),
        help="Destination phone number or set RECIPIENT env var",
    )
    parser.add_argument(
        "--message",
        default="✅ Twilio SMS verification successful.",
        help="Message body",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the SMS send without contacting Twilio",
    )
    return parser.parse_args()

# ───────────────────────────────────────────────────────────────────
# SMS sending logic
# ───────────────────────────────────────────────────────────────────
def send_sms(sid, token, from_, to, body, dry_run=True):
    if dry_run:
        print(f"🔍 [DRY RUN] SMS would be sent to {to}: '{body}'")
        return

    client = Client(sid, token)
    try:
        message = client.messages.create(
            body=body,
            from_=from_,
            to=to,
        )
        print(f"✅ SMS sent successfully, SID: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")


if __name__ == "__main__":
    args = parse_args()
    send_sms(
        args.account_sid,
        args.auth_token,
        args.from_number,
        args.to_number,
        args.message,
        dry_run=args.dry_run,
    )
