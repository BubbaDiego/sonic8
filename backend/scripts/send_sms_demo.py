from twilio.rest import Client

# ───────────────────────────────────────────────────────────────────
# 🔧 Your provided Twilio credentials (explicitly pasted here)
# ───────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = "ACb606788ada5dccbfeeebed0f440099b3"
TWILIO_AUTH_TOKEN = "e6cbb9c3274d3aff9766e1e51e8b87bc"
TWILIO_PHONE_NUMBER = "+18336913467"  # Twilio verified number

RECIPIENT = "+16199804758"  # ⚠️ CHANGE THIS to your actual phone number!
MESSAGE = "✅ Twilio SMS verification successful."

# ───────────────────────────────────────────────────────────────────
# 🚩 DRY RUN Flag (True = simulate, False = send actual SMS)
# ───────────────────────────────────────────────────────────────────
DRY_RUN = False  # Change to False to actually send SMS!

# ───────────────────────────────────────────────────────────────────
# SMS sending logic (no modification needed below)
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
            to=to
        )
        print(f"✅ SMS sent successfully, SID: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")

if __name__ == "__main__":
    send_sms(
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN,
        TWILIO_PHONE_NUMBER,
        RECIPIENT,
        MESSAGE,
        dry_run=DRY_RUN
    )
