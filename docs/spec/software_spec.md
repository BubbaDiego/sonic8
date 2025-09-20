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
| MOD-AUTO | `tests/auto_core/` | Playwright automation (Solflare connect, Jupiter flows). |  |
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
- **Path**: `tests/auto_core/`
- **Purpose**: Playwright automation (Solflare connect, Jupiter flows).
- **Key files**
  - `tests/auto_core/test_jupiter_connect.py`
  - `tests/auto_core/test_playwright_extension.py`
  - `tests/auto_core/test_web_browser_request.py`
- **Public interfaces (signatures)**
  - **test_jupiter_connect.py**: def dummy_sync_playwright(); def test_jupiter_connect(monkeypatch, tmp_path)
  - **test_playwright_extension.py**: class DummyLog; class FakeBrowser; class FakeChromium; class FakePlaywright
  - **test_web_browser_request.py**: def test_web_browser_request(); def test_open_browser_missing_browsers(monkeypatch)

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

<!-- CONFIG_SECRETS:BEGIN -->
### 6) Configuration & Secrets

> Secrets live in environment/.env; **never** committed to the repo.

| Key                  | Type   | Default | Required | Source | Used by                | Notes |
|----------------------|--------|---------|----------|--------|------------------------|-------|
| `RPC_URL`            | string | —       | yes      | `.env` | MOD-AUTO, MOD-SVC      | Solana RPC endpoint (Helius/official) |
| `HELIUS_RPC_URL`     | string | —       | no       | `.env` | MOD-SVC                | Optional override for Helius |
| `WALLET_SECRET_BASE64` | string | —     | yes      | `.env` | MOD-WALLET             | Base64 keypair |
| `JUPITER_API_BASE`   | string | —       | no       | `.env` | MOD-API, MOD-AUTO      | Custom Jupiter base if needed |
| `REDIS_URL`          | string | —       | no       | `.env` | MOD-SVC                | Optional cache/bus |
| `VALIDATE_RESPONSES` | bool   | `0`     | no       | `.env` | MOD-API (dev)          | Enable schema validator |
| `EXPORT_OPENAPI`     | bool   | `0`     | no       | `.env` | exporter (dev)         | Skip heavy init when exporting |

**Per-env**
- **dev**: console logs, validator on (`VALIDATE_RESPONSES=1`), no auth.
- **prod**: JSON logs, validator off, service tokens for auth, dashboards+alerts enabled.
<!-- CONFIG_SECRETS:END -->

---

<!-- OBSERVABILITY:BEGIN -->
### 7) Observability

**Logging (structured)**
- Key lines you already emit:
  - `CYCLONE ENGINE STARTUP`
  - `Loaded N positions :: [PositionStore] @ {timestamp}`
  - `Failed to import solana/solders: No module named 'solana.keypair' :: [WalletCore]`
- Correlation: include `req_id` (uuid4) on inbound HTTP; propagate to service logs.
- Format: JSON-per-line in prod; readable console in dev.

**Metrics (proposed)**
| Name                         | Type       | Owner      | Notes |
|-----------------------------|------------|------------|-------|
| `request_latency_ms`        | histogram  | MOD-API    | P50/P95/P99 per route |
| `monitor_events_processed_total` | counter | MOD-SVC    | Increment per event |
| `perps_order_failures_total`| counter    | MOD-SCRIPTS| Label by `reason` |
| `wallet_rpc_errors_total`   | counter    | MOD-WALLET | Label by `provider` |
| `openapi_export_ms`         | histogram  | MOD-API    | From exporter script |

**Tracing**
- Span boundaries: HTTP request → service call → external (Solana RPC / Jupiter).
- Tags: `rpc.endpoint`, `market`, `side`, `sizeUsd`.

**Dashboards & Alerts**
- API: latency P95, error rate, top 5 endpoints by traffic.
- Perps: order success rate, failure reasons.
- Wallet: RPC error rate per provider; SOL fee balance low.
<!-- OBSERVABILITY:END -->

---

<!-- RELIABILITY_SLOS:BEGIN -->
### 8) Reliability & Performance

**SLOs**
- API success rate ≥ **99.0%** rolling 7d
- API latency P95 ≤ **300 ms**
- Perps order success ≥ **99%** (excluding upstream outages)

**Backoff/Retry Policy**
- External RPC (Solana/Jupiter): **exponential backoff with jitter**, max 5 attempts, cap 8s.
- Idempotency: use client IDs when submitting orders; safe to retry on network/timeouts.
- Concurrency: cap concurrent external calls; shed non-critical work on overload.

**Perf Budgets**
- Memory: API ≤ 300MB steady-state; CPU ≤ 0.5 core avg.
- Export OpenAPI: ≤ 2s (dev), non-blocking in CI.

**Data Integrity**
- Position snapshots and alerts are append-only; on failure, emit a structured error event.
<!-- RELIABILITY_SLOS:END -->

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

<!-- RUNBOOKS:BEGIN -->
### 10) Runbooks

#### RB-01 — RPC exhausted / upstream errors
**Symptoms**
- 5xx from API endpoints calling Solana/Jupiter
- Logs: `wallet_rpc_errors_total` spikes; messages containing `429`, `timeout`, `upstream error`.

**Likely causes**
- Provider rate limits; regional outage; misconfigured `RPC_URL`.

**Quick checks**
1. Check status page of provider; rotate to backup endpoint.
2. Verify `RPC_URL`/`HELIUS_RPC_URL` env is set and reachable (`curl $RPC_URL`).
3. Inspect recent deployment/env changes.

**Remediation**
- Flip to backup RPC in env; restart API.
- Lower concurrency (temp) and increase backoff.
- If provider outage: degrade gracefully (read-only, queue writes).

**Validation**
- P95 latency and error rate return to baseline within 5 minutes.
- `wallet_rpc_errors_total` flatlines.

---

#### RB-02 — Perps order failing
**Symptoms**
- CLI/API returns 500 with program errors (e.g., `ConstraintSeeds`, `InvalidProgramId`, slippage).
- Validator headers may indicate schema mismatch only for read APIs (not order path).

**Likely causes**
- Mismatched PDAs; stale position/ATA; price slippage > tolerance; fee balance too low.

**Quick checks**
1. Enable simulation path; parse “Right:” PDA and adopt.
2. Confirm SOL fee balance ≥ 0.01.
3. Verify market params (size, slippage, min out).

**Remediation**
- Re-derive PDAs consistently (no hard-coded position PDA).
- Retry with adopted PDAs; widen slippage conservatively.
- Top up fee account if needed.

**Validation**
- Order success rate ≥ 99% over last 50 attempts.
- No new `perps_order_failures_total` increments for 15 minutes.

---

#### RB-03 — Solflare connect fails (automation)
**Symptoms**
- Playwright step: `connect failed` or blank extension handshake.
- UI not detecting the wallet; Jupiter flow blocked.

**Likely causes**
- Extension not loaded for the Playwright profile; wrong browser channel; Solflare update prompts.

**Quick checks**
1. Confirm extension CRX path and profile.
2. Try alternate Chromium channel.
3. Look for modal/prompt selectors that changed.

**Remediation**
- Reinstall Solflare extension; pin version if unstable.
- Update selectors and add waits for prompts.
- Fallback to manual connect once to seed permissions.

**Validation**
- `openapi`/monitor flows resume; automation completes connect step reliably.
<!-- RUNBOOKS:END -->

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
