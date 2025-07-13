
"""Async helper that probes the underlying communication providers.

Usage:
    service = XComStatusService(cfg_dict)
    results = await service.probe_all()
"""
from __future__ import annotations
import asyncio, smtplib
from typing import Dict
from backend.core.xcom_core.check_twilio_heartbeat_service import CheckTwilioHeartbeatService

class XComStatusService:
    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.smtp_cfg = self.cfg.get("email", {}).get("smtp", {}) if self.cfg else {}
        self.twilio_cfg = self.cfg.get("api") or self.cfg.get("twilio") or {}

    # --------------------------- probes ---------------------------------- #

    async def _probe_smtp(self) -> tuple[str, str]:
        host = self.smtp_cfg.get("server")
        port = self.smtp_cfg.get("port") or 25
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._smtp_blocking_probe, host, port)
            return ("smtp", "ok")
        except Exception as exc:  # pragma: no cover
            return ("smtp", str(exc))

    def _smtp_blocking_probe(self, host, port):
        with smtplib.SMTP(host, port, timeout=2) as client:
            client.noop()

    async def _probe_twilio(self) -> tuple[str, str]:
        service = CheckTwilioHeartbeatService(self.twilio_cfg)
        try:
            ok = await asyncio.get_running_loop().run_in_executor(None, service.check, True)
            if ok.get("success") is True or ok.get("status") == "ok":
                return ("twilio", "ok")
            return ("twilio", ok)
        except Exception as exc:  # pragma: no cover
            return ("twilio", str(exc))

    # --------------------------------------------------------------------- #

    async def probe_all(self) -> Dict[str, str]:
        tasks = [self._probe_smtp(), self._probe_twilio()]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return {name: status for name, status in results}
