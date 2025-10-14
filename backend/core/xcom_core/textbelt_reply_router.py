# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict
import os
import json
import time

try:
    from backend.core.xcom_core import dispatch_notifications  # type: ignore
except Exception:  # pragma: no cover
    dispatch_notifications = None  # type: ignore

router = APIRouter()

LOG_PATH = os.getenv("XCOM_INBOUND_LOG", "backend/logs/xcom_inbound_sms.jsonl")
WEBHOOK_SECRET = os.getenv("TEXTBELT_WEBHOOK_SECRET", "").strip()


class TextbeltReply(BaseModel):
    fromNumber: str = Field(..., alias="fromNumber")
    text: str


def _write_jsonl(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


@router.post("/reply")
async def textbelt_reply(req: Request, body: TextbeltReply):
    q_secret = (req.query_params.get("secret") or "").strip()
    if WEBHOOK_SECRET and q_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    event = {
        "ts": int(time.time()),
        "fromNumber": body.fromNumber,
        "text": body.text,
        "ip": req.client.host if req.client else None,
        "ua": req.headers.get("user-agent"),
        "source": "textbelt",
    }
    _write_jsonl(LOG_PATH, event)

    try:
        if dispatch_notifications:
            dispatch_notifications(
                monitor_name="xcom_inbound_sms",
                result={
                    "breach": True,
                    "level": "system",
                    "message": f"SMS from {body.fromNumber}: {body.text}",
                },
                channels={"system": True},
                context={"inbound_sms": event},
            )
    except Exception:
        pass

    return {"ok": True}
