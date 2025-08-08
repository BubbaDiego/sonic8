from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv('.env')

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

# simple check to list your Twilio phone numbers:
try:
    incoming_phone_numbers = client.incoming_phone_numbers.list()
    print(f"✅ Authenticated! Found {len(incoming_phone_numbers)} phone number(s):")
    for record in incoming_phone_numbers:
        print(record.phone_number)
except Exception as e:
    print(f"❌ Authentication Error: {e}")
