import sys
import os
from pathlib import Path
import asyncio

from utils.console_title import set_console_title
set_console_title("Sonic Backend")

# --- WINDOWS EVENT‑LOOP PATCH --------------------------------------------- #

# Only needed on Windows: Playwright requires the selector loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback if dotenv is missing

    def load_dotenv(*_a, **_k):
        return False

# Load environment variables before importing modules that rely on them
ROOT_DIR = Path(__file__).resolve().parent.parent
if not load_dotenv(ROOT_DIR / ".env"):
    load_dotenv(ROOT_DIR / ".env.example")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.positions_api import router as positions_router
from backend.routes.portfolio_api import (
    router as portfolio_router,
    api_router as portfolio_api_router,
)
from backend.routes.cyclone_api import router as cyclone_router
from backend.routes.wallet_api import router as wallet_router
from backend.routes.traders_api import router as traders_router
from backend.routes.alert_thresholds_api import (
    router as threshold_router,
    alerts_router,
)
from backend.routes.monitor_status_api import router as monitor_status_router
from backend.routes.db_admin_api import router as db_admin_router
from backend.routes.xcom_api import router as xcom_router
from backend.routes.session_api import router as session_router
from backend.routes.notification_api import router as notification_router
from backend.routes.monitor_settings_api import router as monitor_settings_router
from backend.routes.market_api import router as market_router

from backend.routes.liquidation_distance_api import router as liquidation_distance_router

# 🔥 NEW ROUTER IMPORT
from backend.routes.monitor_api_adapter import router as monitor_router
from backend.routes.auto_core_api import router as auto_core_router
from backend.core.fun_core.fun_router import router as fun_core_router
try:
    from backend.core.fun_core.monitor import prewarm
except Exception:  # pragma: no cover - optional
    prewarm = None

app = FastAPI(title="Sonic API")

if prewarm and os.getenv("FUN_CORE_MONITOR") == "1":
    loop = asyncio.get_event_loop()
    loop.create_task(prewarm())

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all existing routers
app.include_router(positions_router)
app.include_router(portfolio_router)
app.include_router(portfolio_api_router)
app.include_router(cyclone_router)
app.include_router(wallet_router)
app.include_router(traders_router)
app.include_router(threshold_router)
app.include_router(db_admin_router)
app.include_router(alerts_router)
app.include_router(xcom_router)
app.include_router(session_router)
app.include_router(notification_router)
app.include_router(monitor_settings_router)
app.include_router(liquidation_distance_router)
app.include_router(market_router)

# 🔥 FIXED HERE: REMOVED EXTRA PREFIX "/api"
app.include_router(monitor_status_router)

# ------------------------------------------------------------------ #
# Alias so /monitor_status/ works (underscores, no /api) – temporary
# ------------------------------------------------------------------ #
from backend.routes.monitor_status_api import get_status as _monitor_status_get
app.add_api_route("/monitor_status/", _monitor_status_get, methods=["GET"])



# 🔥 REGISTER THE NEW ROUTER
app.include_router(monitor_router)
app.include_router(auto_core_router)
app.include_router(fun_core_router)

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.sonic_backend_app:app", host="0.0.0.0", port=5000, reload=True)
