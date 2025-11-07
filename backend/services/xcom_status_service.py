import os
import smtplib
import ssl
from concurrent import futures
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.core.xcom_core.check_twilio_heartbeat_service import (
    CheckTwilioHeartbeatService,
)
from backend.core.xcom_core.sound_service import SoundService


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class XComAttempt:
    ts: str
    channel: str
    intent: str
    to_number: Optional[str] = None
    from_number: Optional[str] = None
    provider: str = "twilio"
    status: str = "unknown"
    sid: Optional[str] = None
    http_status: Optional[int] = None
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    gated_by: Optional[str] = None
    source: str = "monitor"


def _dl_runtime_set(dl: Any, key: str, value: Any) -> None:
    """Persist runtime status in the DataLocker if possible."""

    if hasattr(dl, "runtime_set"):
        dl.runtime_set(key, value)
        return
    if hasattr(dl, "set_kv"):
        dl.set_kv(key, value)
        return
    setattr(dl, key.replace(".", "_"), value)


def _dl_runtime_get(dl: Any, key: str) -> Any:
    """Fetch runtime status from the DataLocker if available."""

    if hasattr(dl, "runtime_get"):
        return dl.runtime_get(key)
    if hasattr(dl, "get_kv"):
        return dl.get_kv(key)
    return getattr(dl, key.replace(".", "_"), None)


def record_attempt(dl: Any, **fields: Any) -> Dict[str, Any]:
    """Unified recorder for XCOM dispatch attempts."""

    payload = asdict(XComAttempt(ts=_utc_now_iso(), **fields))
    _dl_runtime_set(dl, "xcom.last_attempt", payload)
    try:
        key = "xcom.attempts"
        buf: List[Dict[str, Any]] = _dl_runtime_get(dl, key) or getattr(dl, "xcom_attempts", [])
        if not isinstance(buf, list):
            buf = []
        buf = (list(buf) + [payload])[-50:]
        _dl_runtime_set(dl, key, buf)
    except Exception:
        pass
    return payload


def get_last_attempt(dl: Any) -> Optional[Dict[str, Any]]:
    val = _dl_runtime_get(dl, "xcom.last_attempt")
    if val is not None:
        return val
    return getattr(dl, "xcom_last_attempt", None)


class XComStatusService:
    """Probe connectivity for XCom related services."""

    def __init__(self, config: Dict | None = None) -> None:
        self.config = config or {}

    # ------------------------------------------------------------------ #
    # Individual probe helpers                                           #
    # ------------------------------------------------------------------ #
    def probe_smtp(self) -> str:
        """Verify SMTP credentials by performing a login."""
        cfg = self.config.get("smtp", {})
        server = cfg.get("server") or os.getenv("SMTP_SERVER")
        port = cfg.get("port") or os.getenv("SMTP_PORT")
        username = cfg.get("username") or os.getenv("SMTP_USERNAME")
        password = cfg.get("password") or os.getenv("SMTP_PASSWORD")

        try:
            if not all([server, port, username, password]):
                raise Exception("missing smtp config")
            port = int(port)
            ctx = ssl.create_default_context()
            with smtplib.SMTP(server, port, timeout=2) as smtp:
                smtp.starttls(context=ctx)
                smtp.login(username, password)
            return "ok"
        except Exception as exc:  # pragma: no cover - network dependent
            return str(exc)

    def probe_twilio(self) -> str:
        """Use :class:`CheckTwilioHeartbeatService` to validate credentials."""
        cfg = self.config.get("twilio") or self.config.get("api") or {}
        try:
            result = CheckTwilioHeartbeatService(cfg).check(dry_run=True)
            return "ok" if result.get("success") else result.get("error") or "failed"
        except Exception as exc:  # pragma: no cover - network dependent
            return str(exc)

    def probe_sound(self) -> str:
        """Attempt to play a short sound/beep."""
        try:
            played = SoundService().play()
            return "ok" if played else "playback failed"
        except ModuleNotFoundError:
            return "playsound missing"
        except Exception:  # pragma: no cover - platform dependent
            return "playback failed"

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    def probe_all(self, include_sound: bool = False) -> Dict[str, str]:
        """Run all probes concurrently with a 2 second timeout each."""
        probes: Dict[str, Callable[[], str]] = {
            "smtp": self.probe_smtp,
            "twilio": self.probe_twilio,
        }
        if include_sound:
            probes["sound"] = self.probe_sound

        results: Dict[str, str] = {}
        with futures.ThreadPoolExecutor(max_workers=len(probes)) as ex:
            fut_map = {name: ex.submit(fn) for name, fn in probes.items()}
            for name, fut in fut_map.items():
                try:
                    res = fut.result(timeout=2)
                    results[name] = res if isinstance(res, str) else "ok"
                except futures.TimeoutError:
                    results[name] = "timeout"
                except Exception as exc:  # pragma: no cover - shouldn't happen
                    results[name] = str(exc)
        return results
