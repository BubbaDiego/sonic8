import requests

def trigger_alexa_alert(webhook_url, message):
    data = {"value1": message}
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        print("✅ Alexa test notification sent!")
    except requests.RequestException as e:
        print(f"❌ Error triggering Alexa alert: {e}")

if __name__ == "__main__":
    webhook_url = "https://maker.ifttt.com/trigger/sonic_to_alexa/json/with/key/bHORdpagr8q2NTXBRCxnmo"
    message = "Hey Geno, this is a standalone test from Python!"
    trigger_alexa_alert(webhook_url, message)