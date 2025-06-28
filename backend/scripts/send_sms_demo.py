#!/usr/bin/env python3
"""
send_sms_demo.py

A self-contained demo that sends an SMS to yourself via Twilio.
"""

import os
import sys
from twilio.rest import Client
from dotenv import load_dotenv

def main():
    # Load .env if present
    load_dotenv()

    # Grab credentials
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    to_number   = os.getenv("MY_PHONE_NUMBER")

    # Check for missing config
    missing = [var for var in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                               "TWILIO_PHONE_NUMBER", "MY_PHONE_NUMBER")
               if not os.getenv(var)]
    if missing:
        print(f"❌ Missing environment vars: {', '.join(missing)}")
        print("Please set them in your .env or export them before running.")
        sys.exit(1)

    # Initialize Twilio client
    client = Client(account_sid, auth_token)

    # Send the message
    try:
        message = client.messages.create(
            body="💌 Hey there, this is a Twilio demo SMS!",
            from_=from_number,
            to=to_number
        )
        print(f"✅ SMS sent! SID: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
