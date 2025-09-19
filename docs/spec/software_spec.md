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
| ID           | Path                 | Role                                           | Owner       | Notes |
|--------------|----------------------|------------------------------------------------|------------|------|
| MOD-API      | `backend/api/`       | FastAPI endpoints                              | @BubbaDiego | `/api/monitor-status/`, `/portfolio`, `/positions` |
| MOD-SVC      | `backend/core/`      | DataLocker, Cyclone, Monitor Core, Alert V2    | @BubbaDiego | Emits SONIC events |
| MOD-DATA     | `backend/core/data/` | Persistence/data helpers                        | @BubbaDiego |  |
| MOD-WALLET   | `backend/wallet_core/` | Wallet ops, signing                           | @BubbaDiego |  |
| MOD-SCRIPTS  | `backend/scripts/`   | CLIs: `perps_open_long.py`, `send_token_standalone.py`, `verify_all_tables_exist.py` | @BubbaDiego |  |
| MOD-AUTO     | `auto_core/`         | Playwright automation (Solflare/Jupiter)        | @BubbaDiego |  |
| MOD-FRONTEND | `frontend/`          | React/Vite/Tailwind web app                     | @BubbaDiego |  |

> Keep IDs stable; referenced by interfaces/schemas/config.

---

## 3) Module Inventory (high level)
### MOD-API
- **Purpose**: HTTP surface for monitors, portfolio, positions, and Jupiter ops.
- **Entry files**: `backend/api/__init__.py`, routers under `backend/api/`.
- **Key deps**: MOD-SVC, MOD-WALLET; external: EXT-JUPITER, EXT-SOLANA.
- **I/O**: Returns `SCHEMA-MONITORSTATUS`, `SCHEMA-PORTFOLIO`, `SCHEMA-POSITIONS`.

### MOD-SVC
- **Purpose**: Core orchestration (DataLocker, Cyclone, Monitor Core, Alert V2, PositionStore).
- **Contracts**: Emits `EVT-SONIC_EVENTS`, idempotent processing; failures surfaced via alerts.

### MOD-WALLET
- **Purpose**: Key management & signing; balance/portfolio helpers.
- **Inputs**: `WALLET_SECRET_BASE64`, `RPC_URL`.

### MOD-AUTO
- **Purpose**: Playwright-controlled Solflare connection & Jupiter flows.
- **Gotchas**: Requires Solflare extension availability; stable browser channel.

### MOD-SCRIPTS
- **CLIs**:
  - `perps_open_long.py --symbol SOL --size-usd 5.0`  
  - `send_token_standalone.py --to <addr> --mint <USDC> --amount <n>`  
  - `verify_all_tables_exist.py` (DB sanity)

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
