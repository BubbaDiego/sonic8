# Software Specification — Sonic (v1)

> Canonical spec lives in `docs/spec/`. Machine facts: `spec.manifest.yaml`.

## 0) Cover & Quickstart
- **Project**: Sonic
- **Purpose**: Crypto automation & monitoring for Solana/Jupiter (wallet ops, swaps/perps, alerts, dashboards).
- **Elevator pitch**
  - Automate Solflare/Jupiter flows (swaps/perps).
  - Monitor balances/positions and trigger alerts.
  - Beautiful React dashboards to operate it all.
- **Entrypoints**
  - CLI: `python backend/scripts/unified_jupiter_console.py`
  - API base: `http://localhost:8000/`
  - Frontend: `frontend/` (Vite dev server)
- **Run (dev)**
  1. `python -m venv .venv && . .venv/Scripts/activate` (Windows) or `source .venv/bin/activate` (Unix)
  2. `pip install -r requirements.txt`
  3. `cd frontend && npm install && cd ..`
  4. API: `uvicorn backend.main:app --reload`
  5. Web: `cd frontend && npm run dev`
- **Run (prod)**: Define `RPC_URL`, `WALLET_SECRET_BASE64`, deploy API via your ASGI server; serve frontend build via static host.
- **Spec Map**: see `spec.manifest.yaml` for IDs/paths.

---

## 1) Architecture Overview
- **Context**: Python backend (FastAPI + service cores), React frontend, Playwright automation for Solflare/Jupiter, Solana wallet ops.
- **Runtime topology**: API ↔ Service Core ↔ Wallet Core; optional Redis; external: Solana RPC (Helius/official), Jupiter API, browser automation.
- **Request data flow (portfolio)**: `GET /portfolio/latest` → API queries PositionStore/Wallet → returns `SCHEMA-PORTFOLIO`.
- **Authoritative paths**: listed in Repo Map/Manifest; backend is the SoT for business logic.

---

## 2) Repo Map
<!-- REPO_MAP:BEGIN -->
| ID | Path | Role | Notes |
|---|---|---|---|
| MOD-API | `backend/api/` | FastAPI endpoints for monitors, portfolio, Jupiter ops. |  |
| MOD-SVC | `backend/core/` | Service layer: DataLocker, Cyclone, Monitor Core, Alert V2, PositionStore. |  |
| MOD-DATA | `backend/data/` | Persistence utilities and data models. |  |
| MOD-WALLET | `backend/core/wallet_core/` | Wallet operations, key derivation/management, signing. |  |
| MOD-SCRIPTS | `backend/scripts/` | Operational CLIs (perps_open_long, send_token_standalone, verify_all_tables_exist). |  |
| MOD-AUTO | `auto_core/` | Playwright automation (Solflare connect, Jupiter flows). |  |
| MOD-FRONTEND | `frontend/` | React/Vite/Tailwind UI (Sonic Dashboard, Monitor Manager, Trader Shop). |  |
<!-- REPO_MAP:END -->

> Keep IDs stable; referenced by interfaces/schemas/config.

---

## 3) Module Inventory (high level)
<!-- MODULE_INVENTORY:BEGIN -->
### MOD-API
- **Path**: `backend/api/`
- **Purpose**: FastAPI endpoints for monitors, portfolio, Jupiter ops.
- **Key files**
  - _(none found)_
- **Public interfaces (signatures)**
  - _(no public signatures detected)_

### MOD-SVC
- **Path**: `backend/core/`
- **Purpose**: Service layer: DataLocker, Cyclone, Monitor Core, Alert V2, PositionStore.
- **Key files**
  - `backend/core/__init__.py`
  - `backend/core/alert_core/__init__.py`
  - `backend/core/auto_core/__init__.py`
  - `backend/core/calc_core/__init__.py`
  - `backend/core/core_constants.py`
  - `backend/core/cyclone_core/__init__.py`
- **Public interfaces (signatures)**
  - _(no public signatures detected)_

### MOD-DATA
- **Path**: `backend/data/`
- **Purpose**: Persistence utilities and data models.
- **Key files**
  - `backend/data/__init__.py`
  - `backend/data/data_locker.py`
  - `backend/data/database.py`
  - `backend/data/dl_alerts.py`
  - `backend/data/dl_hedges.py`
  - `backend/data/dl_modifiers.py`
- **Public interfaces (signatures)**
  - **data_locker.py**: class DataLocker
  - **database.py**: class DatabaseManager
  - **dl_alerts.py**: class DLAlertManager

### MOD-WALLET
- **Path**: `backend/core/wallet_core/`
- **Purpose**: Wallet operations, key derivation/management, signing.
- **Key files**
  - `backend/core/wallet_core/__init__.py`
  - `backend/core/wallet_core/encryption.py`
  - `backend/core/wallet_core/wallet_controller.py`
  - `backend/core/wallet_core/wallet_core.py`
  - `backend/core/wallet_core/wallet_repository.py`
  - `backend/core/wallet_core/wallet_schema.py`
- **Public interfaces (signatures)**
  - **encryption.py**: def encrypt_key(plain); def decrypt_key(enc)
  - **wallet_controller.py**: def list_wallets(); def add_wallet(); def delete_wallet(name); def export_wallets()
  - **wallet_core.py**: class WalletCore

### MOD-SCRIPTS
- **Path**: `backend/scripts/`
- **Purpose**: Operational CLIs (perps_open_long, send_token_standalone, verify_all_tables_exist).
- **Key files**
  - `backend/scripts/__init__.py`
  - `backend/scripts/api_breakpoint_test.py`
  - `backend/scripts/backfill_price_history.py`
  - `backend/scripts/create_virtual_env.py`
  - `backend/scripts/diagnose_market_monitor.py`
  - `backend/scripts/env_load_test.py`
- **Public interfaces (signatures)**
  - **api_breakpoint_test.py**: def check_endpoint(base, path); def main(argv)
  - **backfill_price_history.py**: def get_price_at(asset, ts)
  - **create_virtual_env.py**: def run(cmd, cwd); def venv_python(); def create_venv(); def main()

### MOD-AUTO
- **Path**: `auto_core/`
- **Purpose**: Playwright automation (Solflare connect, Jupiter flows).
- **Key files**
  - _(none found)_
- **Public interfaces (signatures)**
  - _(no public signatures detected)_

### MOD-FRONTEND
- **Path**: `frontend/`
- **Purpose**: React/Vite/Tailwind UI (Sonic Dashboard, Monitor Manager, Trader Shop).
- **Key files**
  - _(none found)_
- **Public interfaces (signatures)**
  - _(no public signatures detected)_
<!-- MODULE_INVENTORY:END -->

---

## 4) Public Interfaces
### HTTP APIs
- `GET /api/monitor-status/` → `SCHEMA-MONITORSTATUS`
- `GET /portfolio/latest` → `SCHEMA-PORTFOLIO`
- `GET /positions/` → `SCHEMA-POSITIONS`

### CLIs
- `python backend/scripts/unified_jupiter_console.py` → interactive console
- `python backend/scripts/perps_open_long.py --symbol SOL --size-usd 5.0`
- `python backend/scripts/send_token_standalone.py --to … --mint … --amount …`

### Background
- Monitors/jobs inside MOD-SVC; ensure idempotency and backoff on RPC/Jupiter errors.

---

## 5) Data Contracts (Schemas)
Machine-readable JSON Schemas live in `docs/spec/schemas/`:
- `Position.json` (single position)
- `Positions.json` (array wrapper)
- `Portfolio.json` (balances + positions)
- `Alert.json` (generic alert envelope)
- `MonitorStatus.json` (aggregate health)

Include example objects in each schema.

---

## 6) Configuration & Secrets
| Key                  | Type   | Default | Required | Source | Used by                |
|----------------------|--------|---------|----------|--------|------------------------|
| RPC_URL              | string | —       | yes      | `.env` | MOD-AUTO, MOD-SVC      |
| HELIUS_RPC_URL       | string | —       | no       | `.env` | MOD-SVC                |
| WALLET_SECRET_BASE64 | string | —       | yes      | `.env` | MOD-WALLET             |
| JUPITER_API_BASE     | string | —       | no       | `.env` | MOD-API, MOD-AUTO      |
| REDIS_URL            | string | —       | no       | `.env` | MOD-SVC                |

Secrets never live in the repo. Prefer `.env` + OS keychain/secret store in prod.

---

## 7) Observability
- **Logging**: structured; include correlation IDs; notable lines: “CYCLONE ENGINE STARTUP”, “Loaded N positions :: [PositionStore]”.
- **Metrics**:
  - `request_latency_ms` (histogram, API)
  - `monitor_events_processed_total` (counter, SVC)
  - `perps_order_failures_total` (counter, SCRIPTS)
- **Tracing**: span around external calls (Solana RPC, Jupiter).

---

## 8) Reliability & Performance
- **SLOs**: HTTP P95 ≤ 300ms; CLI order success ≥ 99%.
- **Retries**: exponential backoff + jitter to RPC/Jupiter; idempotent client order IDs.
- **Backpressure**: cap concurrent external calls; queue or drop non-critical.

---

## 9) Security
- **AuthN/Z**: bearer/service tokens in prod; none in dev.
- **Data class**: no PII; wallet secrets are high sensitivity.
- **Threat model**: key leakage, RPC spoofing, automation browser hijack.

---

## 10) Build/Deploy/Runbooks
- **Build**: `pip install -r requirements.txt`; `npm install` in `frontend/`.
- **Deploy**: ASGI for API, static host for web; inject configs via env.
- **Rollback**: previous image/release; db migrations are forward-only (document exceptions).
- **Runbooks**: “RPC exhausted”, “Perps order failing”, “Solflare connect fails” (symptoms → steps → verify).

---

## 11) Test Strategy
- **Unit**: core utils, wallet ops (mocked RPC).
- **Integration**: API routers with local services.
- **E2E (optional)**: Playwright automation flows in a contained profile.

---

## 12) Roadmap & Gaps
- Stabilize OpenAPI export & schema coverage.
- Finish perps long/short UI flow.
- Observability dashboard + alerts.

---

## 13) Glossary & IDs
- **IDs**: `MOD-*`, `API-*`, `EVT-*`, `SCHEMA-*`.
- **EVT-SONIC_EVENTS**: internal bus topic for monitor events.

---

## 14) Do / Don’t for GPTs
- **Do**: Treat `spec.manifest.yaml` as the source of truth for paths/IDs.
- **Don’t**: Guess wallet derivation; always read `RPC_URL`/`WALLET_SECRET_BASE64`.

## 15) Changelog
- v1: initial filled spec.
