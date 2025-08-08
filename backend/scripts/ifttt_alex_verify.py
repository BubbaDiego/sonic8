import requests

def trigger_voicemonkey_alert(token, device_id, message, voice="Matthew"):
    payload = {
        "token": token,
        "device": device_id,
        "text": message,
        "voice": voice,
        "chime": ""  # suppress announcement tone
    }
    try:
        response = requests.post("https://api-v2.voicemonkey.io/announcement", json=payload)
        response.raise_for_status()
        print("✅ Voice Monkey notification sent!")
    except requests.RequestException as e:
        print(f"❌ Error triggering Voice Monkey alert: {e}")

if __name__ == "__main__":
    token = "2a996bfc1ffc44e4ace15f54d99b914f_a28d1035f40002c28ee6b1bdaec81e36"
    device_id = "office"
    message = "Hey Geno, this is a standalone Voice Monkey test from Python!"
    trigger_voicemonkey_alert(token, device_id, message)
