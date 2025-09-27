"""FastAPI router exposing XCom CRUD + utility endpoints."""

from __future__ import annotations

import os

from copy import deepcopy
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.xcom_models import (
    ProviderMap,
    TestMessageRequest,
    TestMessageResult,
)
from backend.core.xcom_core.xcom_status_service import XComStatusService
from backend.core.xcom_core.xcom_core import XComCore, get_latest_xcom_monitor_entry
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.data.data_locker import DataLocker
from backend.deps import get_locker

router = APIRouter(prefix="/xcom", tags=["XCom"])

@router.get("/providers", response_model=ProviderMap)
def read_providers(dl: DataLocker = Depends(get_locker)):
    cfg = deepcopy(dl.system.get_var("xcom_providers") or {})
    # Mask secrets before returning
    for provider in cfg.values():
        if isinstance(provider, dict):
            if "password" in provider:
                provider["password"] = "********"
            if "auth_token" in provider:
                provider["auth_token"] = "********"
            if (smtp := provider.get("smtp")) and isinstance(smtp, dict) and "password" in smtp:
                smtp["password"] = "********"
    return ProviderMap(__root__=cfg)


@router.get("/providers/resolved", response_model=ProviderMap)
def read_providers_resolved(dl: DataLocker = Depends(get_locker)):
    """Return env-resolved provider configs with secrets masked."""

    svc = XComConfigService(dl.system)
    names = list((dl.system.get_var("xcom_providers") or {}).keys())
    if "twilio" not in names:
        names.append("twilio")

    out: dict[str, dict] = {}
    for name in names:
        source_name = "twilio" if name == "api" else name
        raw_provider = svc.get_provider(source_name)
        if isinstance(raw_provider, dict):
            provider = deepcopy(raw_provider)
        elif name in ("twilio", "api"):
            provider = {}
        else:
            provider = raw_provider

        if isinstance(provider, dict):
            if name in ("twilio", "api"):
                from_candidates = [
                    provider.get("default_from_phone"),
                    provider.get("from_phone"),
                    os.getenv("TWILIO_FROM_PHONE"),
                    os.getenv("TWILIO_PHONE_NUMBER"),
                ]
                to_candidates = [
                    provider.get("default_to_phone"),
                    provider.get("to_phone"),
                    os.getenv("TWILIO_TO_PHONE"),
                    os.getenv("MY_PHONE_NUMBER"),
                ]
                provider["default_from_phone"] = next((v for v in from_candidates if v), "")
                provider["default_to_phone"] = next((v for v in to_candidates if v), "")
            if "password" in provider:
                provider["password"] = "********"
            if "auth_token" in provider:
                provider["auth_token"] = "********"
            if isinstance(provider.get("smtp"), dict) and "password" in provider["smtp"]:
                provider["smtp"]["password"] = "********"
        out[name] = provider
    return ProviderMap(__root__=out)

@router.put("/providers")
def write_providers(cfg: ProviderMap, dl: DataLocker = Depends(get_locker)):
    dl.system.set_var("xcom_providers", cfg.root)
    return {"status": "saved"}

@router.get("/status", response_model=Dict[str, str])
async def check_status(dl: DataLocker = Depends(get_locker)):
    service = XComStatusService(dl.system.get_var("xcom_providers") or {})
    return await service.probe_all()

@router.post("/test", response_model=TestMessageResult)
def run_test(req: TestMessageRequest, dl: DataLocker = Depends(get_locker)):
    xcom = XComCore(dl.system)
    result = xcom.send_notification(
        level=req.level,
        subject=req.subject or f"Test {req.mode.upper()} Message",
        body=req.body or "XCom test payload",
        recipient=req.recipient or "",
        initiator="api_test"
    )
    # Only keep minimal fields
    return TestMessageResult(success=result.get("success"), results=result)

@router.get("/last_ping")
def last_ping(dl: DataLocker = Depends(get_locker)):
    return get_latest_xcom_monitor_entry(dl)
