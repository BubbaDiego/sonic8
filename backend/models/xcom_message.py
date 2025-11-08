# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class XComProvider(str, Enum):
    TWILIO   = "twilio"
    TEXTBELT = "textbelt"
    WEBHOOK  = "webhook"
    SMTP     = "smtp"
    EMAIL    = "email"
    PUSH     = "push"
    CUSTOM   = "custom"


class XComDirection(str, Enum):
    OUT = "OUT"
    IN  = "IN"


class XComType(str, Enum):
    SMS     = "sms"
    VOICE   = "voice"
    WEBHOOK = "webhook"
    EMAIL   = "email"
    PUSH    = "push"
    OTHER   = "other"


class XComStatus(str, Enum):
    QUEUED    = "QUEUED"
    SENT      = "SENT"
    DELIVERED = "DELIVERED"
    RECEIPT   = "RECEIPT"
    FAILED    = "FAILED"
    RECEIVED  = "RECEIVED"
    PROCESSED = "PROCESSED"
    PENDING   = "PENDING"


def _ensure_iso(ts: Any) -> str:
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    s = str(ts)
    if s.endswith("Z"):
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


@dataclass
class XComMessage:
    ts: str
    provider: str
    direction: str
    message_type: str
    to_addr: Optional[str] = None
    from_addr: Optional[str] = None
    endpoint: Optional[str] = None
    status: str = XComStatus.PENDING.value
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    duration_ms: Optional[int] = None
    cost: Optional[float] = None
    attempt: Optional[int] = None
    retries: Optional[int] = None
    internal_message_id: Optional[str] = None
    external_message_id: Optional[str] = None
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    meta: Dict[str, Any] = None

    def to_row(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ts"] = _ensure_iso(d.get("ts"))
        if d.get("meta") is None:
            d["meta"] = {}
        for num in ("duration_ms", "cost"):
            if d.get(num) is not None:
                try:
                    d[num] = int(d[num]) if num == "duration_ms" else float(d[num])
                except Exception:
                    d[num] = None
        for ival in ("attempt", "retries"):
            if d.get(ival) is not None:
                try:
                    d[ival] = int(d[ival])
                except Exception:
                    d[ival] = None
        d["provider"]     = (d["provider"]     or XComProvider.CUSTOM.value).lower()
        d["direction"]    = (d["direction"]    or XComDirection.OUT.value).upper()
        d["message_type"] = (d["message_type"] or XComType.OTHER.value).lower()
        d["status"]       = (d["status"]       or XComStatus.PENDING.value).upper()
        d["source"]       = d.get("source") or d["provider"]
        return d
