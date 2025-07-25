import sys
import os
from pathlib import Path

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
from backend.routes.alerts import router as new_alerts_router
from backend.routes.monitor_status_api import router as monitor_status_router
from backend.routes.db_admin_api import router as db_admin_router
from backend.routes.xcom_api import router as xcom_router
from backend.routes.session_api import router as session_router
from backend.routes.notification_api import router as notification_router
from backend.routes.monitor_settings_api import router as monitor_settings_router

# 🔥 NEW ROUTER IMPORT
from backend.routes.monitor_api_adapter import router as monitor_router

app = FastAPI(title="Sonic API")

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
app.include_router(new_alerts_router, tags=["alerts"])
app.include_router(db_admin_router)
app.include_router(alerts_router)
app.include_router(xcom_router)
app.include_router(session_router)
app.include_router(notification_router)
app.include_router(monitor_settings_router)

# 🔥 FIXED HERE: REMOVED EXTRA PREFIX "/api"
app.include_router(monitor_status_router)



# 🔥 REGISTER THE NEW ROUTER
app.include_router(monitor_router)

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.sonic_backend_app:app", host="0.0.0.0", port=5000, reload=True)
