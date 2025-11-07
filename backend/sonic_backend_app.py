
# --- logging hygiene guard (keep at the very top) ---
import sys, importlib
import logging as _stdlib_logging
# If some code replaced the logging module, restore the stdlib one
if not hasattr(_stdlib_logging, "getLogger"):
    # remove bad injected module and import the real stdlib logging
    sys.modules.pop("logging", None)
    _stdlib_logging = importlib.import_module("logging")
# make sure the name 'logging' in THIS module refers to stdlib logging
logging = _stdlib_logging
# ----------------------------------------------------


import sys
import os
from pathlib import Path
import asyncio

from backend.core.xcom_core.xcom_config_loader import (
    load_xcom_config,
    apply_xcom_env,
    mask_for_log,
)
try:
    from dotenv import load_dotenv, find_dotenv
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(*_args, **_kwargs):
        return False

    def find_dotenv(*_args, **_kwargs):
        return ""

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent

try:
    _found_env = find_dotenv(usecwd=True)
except Exception:  # pragma: no cover - fallback if find_dotenv misbehaves
    _found_env = ""

if _found_env:
    load_dotenv(_found_env, override=False)
else:
    for candidate in (ROOT_DIR / ".env", BACKEND_DIR / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)
            break

_example_env = ROOT_DIR / ".env.example"
if _example_env.exists():
    load_dotenv(_example_env, override=False)

# Load XCom config before app/providers initialize
_xcom_logger = logging.getLogger("xcom.init")
try:
    _xcom_base = Path(__file__).parent / "core" / "xcom_core"
    _cfg, _cfg_path = load_xcom_config(base_dir=_xcom_base)
    if _cfg:
        helius_key = (_cfg.get("HELIUS_API_KEY") or "").strip()
        if helius_key and not os.getenv("HELIUS_API_KEY"):
            os.environ["HELIUS_API_KEY"] = helius_key
        _effective = apply_xcom_env(_cfg)
        _xcom_logger.info(
            "XCom env loaded from %s → %s",
            str(_cfg_path) if _cfg_path else "N/A",
            mask_for_log(_effective),
        )
    else:
        _xcom_logger.warning(
            "No xcom_config.json found in %s; Twilio may be unresolved in this process.",
            _xcom_base,
        )
except Exception as _xcom_exc:
    _xcom_logger.exception("Failed to load XCom env at API startup: %s", _xcom_exc)

from utils.console_title import set_console_title
set_console_title("Sonic - FastAPI Backend")

# --- WINDOWS EVENT-LOOP PATCH --------------------------------------------- #
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
try:
    from backend.core.xcom_core.textbelt_reply_router import (
        router as textbelt_router,
    )
except Exception:
    textbelt_router = None


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
from backend.routes.monitor_bootstrap_api import router as monitor_bootstrap_router
from backend.routes.profit_settings_api import router as profit_settings_router
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
from backend.routers import jupiter, monitor_manager
from backend.routes.jupiter_api import router as jupiter_router
from backend.routes.jupiter_perps_api import router as perps_router
from backend.api.routes_perps import router as perps_cli_router
from backend.api.debug_market_api import router as debug_market_router
from backend.api.raydium_router import router as raydium_router
from backend.routes.raydium_api import router as raydium_api_router
from backend.api.liquid_settings_api import router as liquid_settings_router
from backend.middleware.response_validator import install_response_validator, schema_map_router
from backend.routes import positions_snapshot_api

# Optional prewarm
try:
    from backend.core.fun_core.monitor import prewarm
except Exception:
    prewarm = None

# --------------------------------------------------------------------------
# 1) Instantiate the FastAPI application before wiring any routers
# --------------------------------------------------------------------------
app = FastAPI(
    title="Sonic API",
    version="v1",
    generate_unique_id_function=_unique_id,
)

if prewarm and os.getenv("FUN_CORE_MONITOR") == "1":
    loop = asyncio.get_event_loop()
    loop.create_task(prewarm())

# --------------------------------------------------------------------------
# 2) Configure middleware / lifecycle hooks (optional)
# --------------------------------------------------------------------------
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

# --------------------------------------------------------------------------
# 3) Include routers only after the app has been created
# --------------------------------------------------------------------------
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
if textbelt_router:
    app.include_router(
        textbelt_router, prefix="/api/xcom/textbelt", tags=["xcom-textbelt"]
    )
app.include_router(session_router)
app.include_router(notification_router)
app.include_router(monitor_settings_router)
app.include_router(monitor_bootstrap_router)
app.include_router(liquid_settings_router)
app.include_router(debug_market_router)
app.include_router(profit_settings_router)
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
app.include_router(perps_cli_router)
app.include_router(raydium_router)
app.include_router(raydium_api_router)
app.include_router(positions_snapshot_api.router)

# Jupiter legacy API stays under /api for compatibility
app.include_router(jupiter.router, prefix="/api")

# Monitor status without extra /api prefix (as in your existing setup)
app.include_router(monitor_status_router)

# Monitor configuration management
app.include_router(monitor_manager.router)

# Temporary alias route for /monitor_status/ (underscore path)
from backend.routes.monitor_status_api import get_status as _monitor_status_get
app.add_api_route("/monitor_status/", _monitor_status_get, methods=["GET"])

# NEW /api/auto-core/* routes (Open/Connect/Status etc.)
app.include_router(monitor_router)
app.include_router(auto_core_router)  # <-- mounted once, after app is defined
app.include_router(fun_core_router)

install_response_validator(app)

if os.getenv("VALIDATE_RESPONSES") == "1":
    app.include_router(schema_map_router())

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.sonic_backend_app:app", host="127.0.0.1", port=5000, reload=True)
