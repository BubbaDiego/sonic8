
"""Adapter layer that re‑exports the legacy Flask monitor API through FastAPI."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
import asyncio
from sse_starlette.sse import EventSourceResponse
from backend.core.cyclone_core.cyclone_engine import Cyclone
from backend.core.monitor_core.sonic_monitor import (
    sonic_cycle,
    register_listener,
    unregister_listener,
)
from backend.core.monitor_core.monitor_core import MonitorCore

router = APIRouter(prefix="/monitors", tags=["Monitors"])

_core = MonitorCore()  # default monitors registered
_registry = _core.registry

@router.get("/", response_model=list[str])
def list_monitors():
    """Return sorted list of monitor keys."""
    return sorted(_registry.get_all_monitors())

@router.post("/sonic_cycle", status_code=202)
def run_sonic_cycle(bg: BackgroundTasks):
    """Execute the Sonic monitor cycle asynchronously."""
    cyclone = Cyclone()

    async def _runner():
        await sonic_cycle(0, cyclone)

    bg.add_task(_runner)
    return {"status": "sonic cycle started"}


@router.get("/sonic_events")
async def sonic_events(request: Request):
    """Server-Sent Events stream for Sonic cycle completion."""
    queue: asyncio.Queue[str] = asyncio.Queue()

    async def _push_event():
        await queue.put("done")

    register_listener(_push_event)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await queue.get()
                yield {"event": "sonic_complete", "data": data}
        finally:
            unregister_listener(_push_event)

    return EventSourceResponse(event_generator())


@router.post("/{name}")
def run_monitor(name: str):
    if name not in _registry.get_all_monitors():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Monitor '{name}' not found")
    monitor = _registry.get(name)
    try:
        monitor.run_cycle()
        return {"status": "success", "monitor": name}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
