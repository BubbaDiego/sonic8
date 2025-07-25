# Sonic1 Design Specification
**Updated:** 2025-07-25


## Repository Overview

The project combines a Python backend and a React + Vite frontend.  A dedicated
pytest harness lives under `test_core/` and the full layout is captured in
`docs/repo_map.md`.  Top‑level directories include:

```txt
sonic1/
├── backend/          # FastAPI application
├── frontend/         # React client
├── test_core/        # custom pytest runner
├── tests/            # API test suite
├── data/             # SQLite databases
├── patches/          # integration bundles
├── docs/             # design specs
├── reports/          # generated HTML summaries
├── launch_pad.py     # dev helper script
└── requirements.txt  # Python dependencies
```
(See `docs/repo_map.md` for the complete tree.)

---

## Backend Architecture

The FastAPI application is defined in `backend/sonic_backend_app.py`. It registers the API routers and configures CORS:

```python
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
from backend.routes.monitor_api_adapter import router as monitor_router

app = FastAPI(title="Sonic API")

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
app.include_router(monitor_status_router)
app.include_router(monitor_router)

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.sonic_backend_app:app", host="0.0.0.0", port=5000, reload=True)
```

The core persistence layer is the `DataLocker` singleton. It provides unified access to alerts, prices, positions, wallets and more:

```python
class DataLocker:
    """Singleton-style access point for all data managers."""
    _instance = None

    def __init__(self, db_path: str):
        self.db = DatabaseManager(db_path)
        self.alerts = DLAlertManager(self.db)
        self.prices = DLPriceManager(self.db)
        self.positions = DLPositionManager(self.db)
        self.hedges = DLHedgeManager(self.db) if DLHedgeManager else None
        self.wallets = DLWalletManager(self.db)
        self.portfolio = DLPortfolioManager(self.db)
        self.session = DLSessionManager(self.db)
        self.traders = DLTraderManager(self.db) if DLTraderManager else None
        self.system = DLSystemDataManager(self.db) if DLSystemDataManager else None
        self.ledger = DLMonitorLedgerManager(self.db)
        self.modifiers = DLModifierManager(self.db)
        ...
```[cyclone_core](../backend/core/cyclone_core)

### Core Modules

The `backend/core/` package houses the primary business logic. Key submodules include:

- **alert_core** – alert orchestration and notification system, described in [`alert_core_spec.md`](../backend/core/alert_core/alert_core_spec.md).
- **calc_core** – numerical utilities and risk calculations.
- **cyclone_core** – the orchestration engine coordinating market updates, enrichment and hedging. Design details are in [`cyclone_core_spec.md`](../backend/core/cyclone_core/cyclone_core_spec.md).
- **hedge_core** – hedge linking and calculations.
- **monitor_core** – runs background monitors. The spec outlines default monitors and the `run_all()` method:

### 🚦 MonitorCore
Central controller for executing registered monitors.

```python
MonitorCore(registry: MonitorRegistry | None = None)
```
- If `registry` is not provided, a new one is created and default monitors are registered (`PriceMonitor`, `PositionMonitor`, `OperationsMonitor`, `XComMonitor`, `TwilioMonitor`, `ProfitMonitor`, `RiskMonitor`, `LiquidationMonitor`).
- **RiskMonitor** – monitors heat index and dispatches HIGH level alerts.

**Methods**
- `run_all()` – iterate and run every monitor in the registry, logging success or failure.
- `run_by_name(name)` – run a single monitor by its key if present.

### 🧩 Monitor Implementations
- **BaseMonitor** – provides `run_cycle()` wrapper that records results in the database ledger.
- **PriceMonitor** – fetches BTC/ETH/SOL prices and the S&P 500 index via `MonitorService`.
- **PositionMonitor** – syncs positions from Jupiter and logs summary metrics.
- **positions_core** – CRUD and enrichment of positions.
- **wallet_core** – wallet repository and service layer.
- **trader_core** – persona tracking utilities.
- **oracle_core** – wrappers around external price/oracle services.
- **xcom_core** – lightweight notification dispatch.

All cores rely on `DataLocker` for persistence and use the
[`ConsoleLogger`](../backend/utils/console_logger.py) for structured logging.
See [CONSOLE_LOGGER_SPEC.md](../backend/utils/CONSOLE_LOGGER_SPEC.md) for
configuration options.

---

## Frontend Architecture

The React application is located under `frontend/` and documented in `docs/frontend_repo_map.md and docs/frontend_file_description.md`.
The Vite entry point mounts the Redux provider and root component:

```javascript
const container = document.getElementById('root');
const root = createRoot(container);
root.render(
  <Provider store={store}>
    <PersistGate loading={null} persistor={persister}>
      <ConfigProvider>
        <SonicReactApp />
      </ConfigProvider>
    </PersistGate>
  </Provider>
);
serviceWorker.unregister();
reportWebVitals();
```

### Docs and Scripts

- `README.md` contains setup instructions including backend and frontend launch commands.
- `launch_pad.py` starts both services for local development.
- Multiple `*_spec.md` files under `backend/core/` provide detailed design notes for each subsystem. Additional docs such as `docs/alert_v2_spec.md` and `docs/alert_v2_hybrid_spec.md` describe the evolving alert data model.
- `docs/repo_map.md` enumerates the complete repository tree for reference.

### Test Harness

The repo bundles a lightweight test subsystem under `test_core/`:

```txt
test_core/
├── __init__.py          # Re-exports TestCoreRunner
├── __main__.py          # Allows `python -m test_core`
├── formatter.py         # Grade & summary utilities
├── runner.py            # Low-level pytest glue
├── console_ui.py        # Simple pick-list interface
├── failures/            # One file per failing test
├── reports/             # HTML/JSON summaries
└── tests/               # Sample tests and conftest.py
```

The small `tests/` folder contains example pytest cases for the backend API.
Both `tests` and `test_core/tests` rely on a temporary SQLite database provided by the `dl_tmp` fixture in `tests/conftest.py`.

This document provides an architectural snapshot of the entire project. Individual subsystem specs offer additional implementation notes.
