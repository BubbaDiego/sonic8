import os
import smtplib
import ssl
from concurrent import futures
from typing import Dict, Callable

from backend.core.xcom_core.check_twilio_heartbeat_service import (
    CheckTwilioHeartbeatService,
)
from backend.core.xcom_core.sound_service import SoundService


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
            SoundService().play()
            return "ok"
        except Exception as exc:  # pragma: no cover - platform dependent
            return str(exc)

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
