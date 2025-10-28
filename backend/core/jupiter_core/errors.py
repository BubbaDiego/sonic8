"""Custom exceptions for Jupiter core services."""


class JupiterHTTPError(RuntimeError):
    """Raised when the Jupiter HTTP API returns a non-success status."""

    def __init__(self, status_code: int, message: str, body: str | None = None) -> None:
        super().__init__(f"[HTTP {status_code}] {message}")
        self.status_code = status_code
        self.body = body


class JupiterSigningError(RuntimeError):
    """Raised when we fail to sign a base64 transaction."""

    pass
