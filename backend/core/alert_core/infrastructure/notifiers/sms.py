from __future__ import annotations

import os

#from notifications.twilio_sms_sender import TwilioSMSSender

from .base import BaseNotifier


class SMSNotifier(BaseNotifier):
    """Send SMS via Twilio if configured."""

    def __init__(self) -> None:
        super().__init__()
        try:
            self.sender = TwilioSMSSender()
        except Exception:
            self.sender = None

    def send(self, alert) -> bool:
        message = f"[{alert.level}] {alert.description}"
        number = os.getenv("ALERT_SMS_NUMBER", "0000000000")
        if self.sender and getattr(self.sender, "client", None):
            self.sender.send_sms(number, message)
            return True
        print(f"\N{mobile phone} [SMS Fallback] {number}: {message}")
        return False
