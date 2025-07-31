
"""Optional: monitor to pre‑warm cache hourly."""
import asyncio, logging, time
from datetime import timedelta, datetime

from .models import FunType
from .registry import FunRegistry

_log = logging.getLogger("fun_monitor")

async def prewarm(interval_minutes: int = 60):
    """Periodic task that fetches all fun types to populate cache."""
    while True:
        start = datetime.utcnow()
        for t in FunType:
            try:
                await FunRegistry.by_type(t).get_random()
                _log.info("Pre‑warmed %s at %s", t, start.isoformat())
            except Exception as exc:  # noqa: BLE001
                _log.warning("Pre‑warm failed for %s: %s", t, exc)
        await asyncio.sleep(interval_minutes * 60)
