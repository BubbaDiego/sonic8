"""Pydantic models exclusively used by the XCom & Monitor routes."""

from __future__ import annotations
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, conint, EmailStr, RootModel  # ✅ RootModel added here

class SMTPConfig(BaseModel):
    """Subset of fields required for SMTP communication."""
    server: str
    port: conint(gt=0, lt=65536)
    username: str
    password: str
    default_recipient: Optional[EmailStr] = None

class ProviderConfig(BaseModel):
    """Generic provider configuration.

    Allows extra fields so Twilio or future providers
    can persist arbitrary credential keys without code changes.
    """
    enabled: bool = True
    smtp: Optional[SMTPConfig] = None

    class Config:
        extra = "allow"

# ✅ Updated for Pydantic v2 compatibility
class ProviderMap(RootModel[Dict[str, ProviderConfig]]):
    pass

class StatusResponse(RootModel[Dict[str, str]]):
    pass

class TestMessageRequest(BaseModel):
    """POST body for `/xcom/test`."""
    mode: Literal["sms", "email", "voice", "sound"]
    recipient: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"

class TestMessageResult(BaseModel):
    """Slim wrapper around XComCore result."""
    success: bool
    results: Dict[str, Any] = Field(default_factory=dict)
