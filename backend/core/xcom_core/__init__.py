from .xcom_core import dispatch_notifications   # multi-channel aggregator (system/sms/tts/…)
from .dispatch import dispatch_voice            # explicit voice-only function (positional API)

__all__ = ["dispatch_notifications", "dispatch_voice"]
