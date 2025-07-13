try:
    from pydantic import BaseModel, Field
    if not hasattr(BaseModel, "__fields__"):
        raise ImportError("stub")
except Exception:  # pragma: no cover - optional dependency or stub detected
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self) -> dict:  # type: ignore[override]
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default

class ProviderConfig(BaseModel):
    """Configuration for a single communication provider."""

    enabled: bool | None = True

    class Config:
        extra = "allow"

class ProviderMap(BaseModel):
    """Mapping of provider name to configuration."""

    providers: dict[str, ProviderConfig] = Field(default_factory=dict)

class StatusResponse(BaseModel):
    """Status details for various external integrations."""

    twilio: str
    chatgpt: str
    jupiter: str
    github: str

class TestMessageRequest(BaseModel):
    """Request payload for sending a test XCom message."""

    level: str = "LOW"
    subject: str
    body: str
    recipient: str | None = None

class TestMessageResult(BaseModel):
    """Result of a test XCom message dispatch."""

    success: bool
    results: dict

