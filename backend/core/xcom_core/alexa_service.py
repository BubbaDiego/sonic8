import requests
from backend.core.logging import log

class AlexaService:
    def __init__(self, config: dict):
        self.config = config

    def send(self, message: str) -> bool:
        access_code = self.config.get("access_code")
        if not self.config.get("enabled") or not access_code:
            log.warning("Alexa provider disabled or missing access code", source="AlexaService")
            return False

        url = "https://api.notifymyecho.com/v1/NotifyMe"
        headers = {"Content-Type": "application/json"}
        data = {
            "notification": message,
            "accessCode": access_code
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            log.success("✅ Alexa notification sent", source="AlexaService")
            return True
        except Exception as e:
            log.error(f"❌ Alexa notification failed: {e}", source="AlexaService")
            return False
