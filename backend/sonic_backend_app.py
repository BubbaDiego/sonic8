import sys
import os

# Adds the parent of 'backend' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.positions_api import router as positions_router
from backend.routes.portfolio_api import router as portfolio_router
from backend.routes.cyclone_api import router as cyclone_router
from backend.routes.wallet_api import router as wallet_router
from backend.routes.traders_api import router as traders_router
from backend.routes.alert_thresholds_api import (
    router as threshold_router,
    alerts_router,
)
from backend.routes.monitor_status_api import router as monitor_status_router
from backend.routes.db_admin_api import router as db_admin_router

app = FastAPI(title="Sonic API")

# Clearly Updated CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3006",  # Clearly match your frontend app origin
        "http://localhost:3000",
        "*",  # Or "*" to allow all clearly (simpler during development)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(positions_router)
app.include_router(portfolio_router)
app.include_router(cyclone_router)
app.include_router(wallet_router)
app.include_router(traders_router)
app.include_router(threshold_router)
app.include_router(monitor_status_router)
app.include_router(db_admin_router)
app.include_router(alerts_router)


@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.sonic_backend_app:app", host="0.0.0.0", port=5000, reload=True)
