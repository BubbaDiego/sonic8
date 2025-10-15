# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from typing import Any, Dict
from pathlib import Path
import os
import json
import time

try:
    from backend.core.xcom_core import dispatch_notifications  # type: ignore
except Exception:  # pragma: no cover
    dispatch_notifications = None  # type: ignore

router = APIRouter()

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOG_DEFAULT_REL = Path("backend") / "core" / "xcom_core" / "logs" / "xcom_inbound_sms.jsonl"
_cfg_raw = os.getenv("XCOM_INBOUND_LOG", str(_LOG_DEFAULT_REL))
_cfg_path = Path(_cfg_raw)
LOG_PATH = str(_cfg_path if _cfg_path.is_absolute() else (_REPO_ROOT / _cfg_path).resolve())
WEBHOOK_SECRET = os.getenv("TEXTBELT_WEBHOOK_SECRET", "").strip()


def _write_jsonl(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


@router.post("/reply")
async def textbelt_reply(req: Request):
    q_secret = (req.query_params.get("secret") or "").strip()
    if WEBHOOK_SECRET and q_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    payload: Dict[str, Any] = {}

    try:
        if req.headers.get("content-type", "").lower().startswith("application/json"):
            payload = await req.json()
        else:
            form = await req.form()
            payload = dict(form) if form else {}
    except Exception:
        payload = {}

    from_number = (payload.get("fromNumber") or payload.get("from_number") or "").strip()
    text_body = (payload.get("text") or payload.get("message") or "").strip()

    if not from_number or not text_body:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "type": "missing",
                    "loc": ["body"],
                    "msg": "Field required",
                    "input": None,
                }
            ],
        )

    event = {
        "ts": int(time.time()),
        "fromNumber": from_number,
        "text": text_body,
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
                    "message": f"SMS from {from_number}: {text_body}",
                },
                channels={"system": True},
                context={"inbound_sms": event},
            )
    except Exception:
        pass

    return {"ok": True}
