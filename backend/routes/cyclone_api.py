from fastapi import APIRouter, BackgroundTasks
import asyncio

from backend.core.cyclone_core.cyclone_engine import Cyclone

router = APIRouter(prefix="/cyclone", tags=["cyclone"])

cyclone = Cyclone()


async def _run(coro):
    await coro


@router.post("/run", status_code=202)
def run_cycle(bg: BackgroundTasks):
    bg.add_task(_run, cyclone.run_cycle())
    return {"status": "cycle started"}


@router.post("/prices", status_code=202)
def run_price_update(bg: BackgroundTasks):
    bg.add_task(_run, cyclone.run_market_updates())
    return {"status": "price update started"}


@router.post("/positions", status_code=202)
def run_position_update(bg: BackgroundTasks):
    bg.add_task(_run, cyclone.run_position_updates())
    return {"status": "position update started"}


@router.delete("/data", status_code=202)
def clear_all_data(bg: BackgroundTasks):
    bg.add_task(_run, cyclone.run_clear_all_data())
    return {"status": "clear started"}
