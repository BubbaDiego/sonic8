import requests
from backend.core.logging import log

class AlexaService:
    def __init__(self, config: dict):
        self.config = config

    def send(self, message: str) -> bool:
        webhook_url = self.config.get("webhook_url")
        if not self.config.get("enabled") or not webhook_url:
            log.warning("Alexa provider disabled or missing webhook URL", source="AlexaService")
            return False

        data = {
            "value1": message
        }

        try:
            response = requests.post(webhook_url, json=data)
            response.raise_for_status()
            log.success("✅ Alexa notification via IFTTT sent", source="AlexaService")
            return True
        except Exception as e:
            log.error(f"❌ Alexa notification failed: {e}", source="AlexaService")
            return False