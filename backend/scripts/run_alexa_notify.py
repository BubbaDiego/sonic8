import requests

def send_alexa_notification(access_code, message):
    url = "https://api.notifymyecho.com/v1/NotifyMe"
    headers = {"Content-Type": "application/json"}
    data = {
        "notification": message,
        "accessCode": access_code
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        print(f"✅ Notification sent successfully! Response: {response.text}")
    except requests.RequestException as e:
        print(f"❌ Error sending notification: {e}")

if __name__ == "__main__":
    access_code = "nmac.P69AH6YUYTFXRTKDQ7SMJTHHIPTCLUAASELIS6Y"
    message = "Hey Geno, your Python-to-Alexa notification integration is working perfectly!"
    send_alexa_notification(access_code, message)
