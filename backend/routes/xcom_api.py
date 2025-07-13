from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker
from backend.core.xcom_core.xcom_core import XComCore
from backend.core.xcom_core.check_twilio_heartbeat_service import CheckTwilioHeartbeatService
from backend.models.xcom_models import (
    ProviderMap,
    StatusResponse,
    TestMessageRequest,
    TestMessageResult,
)
import os
import requests

router = APIRouter(prefix="/xcom", tags=["xcom"])


def _dl() -> DataLocker:
    return DataLocker.get_instance()


SENSITIVE_KEYS = {
    "auth_token",
    "password",
    "account_sid",
    "flow_sid",
    "default_from_phone",
    "default_to_phone",
    "username",
    "api_key",
    "token",
}


def _mask(data):
    if isinstance(data, dict):
        return {k: ("***" if k in SENSITIVE_KEYS and data[k] else _mask(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_mask(v) for v in data]
    return data


@router.get("/providers", response_model=ProviderMap)
def get_providers(dl: DataLocker = Depends(_dl)):
    cfg = dl.system.get_var("xcom_providers") or {}
    return ProviderMap(providers=_mask(cfg))


@router.put("/providers")
def set_providers(map: ProviderMap, dl: DataLocker = Depends(_dl)):
    data = map.model_dump()["providers"] if hasattr(map, "model_dump") else map.providers
    dl.system.set_var("xcom_providers", data)
    return {"status": "updated"}


@router.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    twilio_r = CheckTwilioHeartbeatService({}).check(dry_run=True)
    twilio = "ok" if twilio_r.get("success") else f"error: {twilio_r.get('error')}" if twilio_r.get("error") else "error"

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
    if not api_key:
        chatgpt = "missing api key"
    else:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "ping"}])
            chatgpt = "ok"
        except Exception as exc:  # pragma: no cover - network dependent
            chatgpt = f"error: {exc}"

    try:
        requests.get("https://quote-api.jup.ag/v6/health", timeout=3).raise_for_status()
        jupiter = "ok"
    except Exception as exc:  # pragma: no cover - network dependent
        jupiter = f"error: {exc}"

    try:
        requests.get("https://api.github.com", timeout=3).raise_for_status()
        github = "ok"
    except Exception as exc:  # pragma: no cover - network dependent
        github = f"error: {exc}"

    return StatusResponse(twilio=twilio, chatgpt=chatgpt, jupiter=jupiter, github=github)


@router.post("/test", response_model=TestMessageResult)
def send_test(msg: TestMessageRequest, dl: DataLocker = Depends(_dl)) -> TestMessageResult:
    xcom = XComCore(dl.system)
    result = xcom.send_notification(msg.level, msg.subject, msg.body, msg.recipient or "", initiator="api")
    return TestMessageResult(success=bool(result.get("success")), results=result)


__all__ = ["router"]

