import httpx
import os

async def send_slack(event):
    url = os.environ["SLACK_WEBHOOK"]
    payload = {
        "text": f"[{event.level}] {event.alert_id}: {event.metric_value} | {event.message}"
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)
