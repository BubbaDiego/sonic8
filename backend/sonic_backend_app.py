import sys
import os
from pathlib import Path
import asyncio



from utils.console_title import set_console_title
set_console_title("Sonic - FastAPI Backend")

# --- WINDOWS EVENT-LOOP PATCH --------------------------------------------- #
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# dotenv (optional)
try:
    from dotenv import load_dotenv
except Exception:  # no dotenv available
    def load_dotenv(*_a, **_k):
        return False

ROOT_DIR = Path(__file__).resolve().parent.parent
if not load_dotenv(ROOT_DIR / ".env"):
    load_dotenv(ROOT_DIR / ".env.example")

from fastapi import FastAPI


def _unique_id(route) -> str:
    """Return a stable, unique operationId for the given route."""

    method = sorted(route.methods)[0].lower() if route.methods else "get"
    name = (route.name or "op").replace(" ", "_")
    path = (
        route.path_format.replace("/", "_")
        .strip("_")
        .replace("{", "")
        .replace("}", "")
    )
    line_no = getattr(getattr(route.endpoint, "__code__", None), "co_firstlineno", 0)
    return f"{name}_{method}_{path}_{line_no}"
from fastapi.middleware.cors import CORSMiddleware
from backend.services.solana_rpc import _RPC_URLS

print(f"[rpc] rotation = {', '.join(_RPC_URLS)}")

# Routers (imports only; include AFTER app = FastAPI)
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
from backend.routes.prices_api import router as prices_router
from backend.routes.solana_api import router as solana_router
from backend.routes.wallet_verify_api import router as wallet_verify_router
from backend.routes.wallet_send import router as wallet_send_router
from backend.routes.wallet_send import send_token_api as _wallet_send_token
from backend.routes.wallet_preflight import preflight_send as _wallet_preflight_send
from backend.routes.liquidation_distance_api import router as liquidation_distance_router
from backend.routes.monitor_api_adapter import router as monitor_router
from backend.routes.auto_core_api import router as auto_core_router  # <-- Auto Core routes
from backend.core.fun_core.fun_router import router as fun_core_router
from backend.routers import jupiter
from backend.routes.jupiter_api import router as jupiter_router
from backend.routes.jupiter_perps_api import router as perps_router
from backend.middleware.response_validator import install_response_validator

# Optional prewarm
try:
    from backend.core.fun_core.monitor import prewarm
except Exception:
    prewarm = None

# --------------------------------------------------------------------------
# Create app FIRST, then include routers
# --------------------------------------------------------------------------
app = FastAPI(
    title="Sonic API",
    version="v1",
    generate_unique_id_function=_unique_id,
)

if prewarm and os.getenv("FUN_CORE_MONITOR") == "1":
    loop = asyncio.get_event_loop()
    loop.create_task(prewarm())

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "*",
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
app.include_router(prices_router)
app.include_router(solana_router)
app.include_router(wallet_verify_router)
app.include_router(wallet_send_router)
app.add_api_route("/api/jupiter/wallet/send", _wallet_send_token, methods=["POST"])
app.add_api_route("/api/jupiter/wallet/preflight-send", _wallet_preflight_send, methods=["POST"])
app.include_router(jupiter_router)
app.include_router(perps_router)

# Jupiter legacy API stays under /api for compatibility
app.include_router(jupiter.router, prefix="/api")

# Monitor status without extra /api prefix (as in your existing setup)
app.include_router(monitor_status_router)

# Temporary alias route for /monitor_status/ (underscore path)
from backend.routes.monitor_status_api import get_status as _monitor_status_get
app.add_api_route("/monitor_status/", _monitor_status_get, methods=["GET"])

# NEW /api/auto-core/* routes (Open/Connect/Status etc.)
app.include_router(monitor_router)
app.include_router(auto_core_router)  # <-- mounted once, after app is defined
app.include_router(fun_core_router)

install_response_validator(app)

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.sonic_backend_app:app", host="0.0.0.0", port=5000, reload=True)
