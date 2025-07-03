# Sonic1 Design Specification

## Repository Overview

The project is divided into a Python backend built with FastAPI and a React+Vite frontend. A small test harness (`test_core/`) provides an extended unit test suite. The full file tree is documented in `docs/repo_map.md` and begins with:

```txt
sonic1/
├── backend
│   ├── config
│   │   ├── __init__.py
│   │   ├── active_traders.json
│   │   ├── alert_thresholds.json
│   │   ├── comm_config.json
│   │   ├── config_loader.py
│   │   ├── sonic_config.json
│   │   ├── sonic_sauce.json
│   │   └── theme_config.json
│   ├── console
│   │   ├── __init__.py
│   │   ├── cyclone_console.py
│   │   └── cyclone_console_service.py
│   ├── controllers
│   │   ├── __init__.py
│   │   ├── cyclone_controller.py
│   │   ├── logic.py
│   │   └── monitor_controller.py
```

Frontend assets follow further down the listing ending with:

```txt
│   ├── vite.config.mjs
│   └── yarn.lock
├── .gitignore
├── README.md
├── launch_pad.py
└── requirements.txt
```

---

## Backend Architecture

The FastAPI application is defined in `backend/sonic_backend_app.py`. It registers the API routers and configures CORS:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.positions_api import router as positions_router
from backend.routes.portfolio_api import router as portfolio_router
from backend.routes.cyclone_api import router as cyclone_router

app = FastAPI(title="Sonic API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(positions_router)
app.include_router(portfolio_router)
app.include_router(cyclone_router)

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}
```
```python
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
        ...
```

### Core Modules

The `backend/core/` package houses the primary business logic. Key submodules include:

- **alert_core** – alert orchestration and notification system, described in [`alert_core_spec.md`](../backend/core/alert_core/alert_core_spec.md).
- **calc_core** – numerical utilities and risk calculations.
- **cyclone_core** – the orchestration engine coordinating market updates, enrichment and hedging. Design details are in [`cyclone_core_spec.md`](../backend/core/cyclone_core/cyclone_core_spec.md).
- **hedge_core** – hedge linking and calculations.
- **monitor_core** – runs background monitors. The spec outlines default monitors and the `run_all()` method:

```text
### 🚦 MonitorCore
Central controller for executing registered monitors.

```python
MonitorCore(registry: MonitorRegistry | None = None)
```
- If `registry` is not provided, a new one is created and default monitors are registered (`PriceMonitor`, `PositionMonitor`, `OperationsMonitor`, `XComMonitor`, `TwilioMonitor`, `ProfitMonitor`, `RiskMonitor`).
- **RiskMonitor** – monitors heat index and dispatches HIGH level alerts.

**Methods**
- `run_all()` – iterate and run every monitor in the registry, logging success or failure.
- `run_by_name(name)` – run a single monitor by its key if present.

### 🧩 Monitor Implementations
- **BaseMonitor** – provides `run_cycle()` wrapper that records results in the database ledger.
- **PriceMonitor** – fetches BTC/ETH/SOL prices via `MonitorService`.
- **PositionMonitor** – syncs positions from Jupiter and logs summary metrics.
```
- **positions_core** – CRUD and enrichment of positions.
- **wallet_core** – wallet repository and service layer.
- **trader_core** – persona tracking utilities.
- **oracle_core** – wrappers around external price/oracle services.
- **xcom_core** – lightweight notification dispatch.

All cores rely on `DataLocker` for persistence and share common logging utilities.

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
- Multiple `*_spec.md` files under `backend/core/` provide detailed design notes for each subsystem.
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
