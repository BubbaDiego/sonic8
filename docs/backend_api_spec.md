# Backend API Specification

This document describes the FastAPI routes defined under `backend/routes/`.
Each module registers an `APIRouter` which is included in
[`backend/sonic_backend_app.py`](../backend/sonic_backend_app.py).  The
endpoints below return JSON responses and use Pydantic models from the
`backend.models` package.

## Cyclone API (`cyclone_api.py`)
**Base path**: `/cyclone`

- `POST /run` – Trigger `Cyclone.run_cycle()` in a background task.
  - **Response**: `{"status": "cycle started"}` (HTTP 202)
- `POST /prices` – Start a background market price update via `Cyclone.run_market_updates()`.
  - **Response**: `{"status": "price update started"}` (HTTP 202)
- `POST /positions` – Launch a background position update using `Cyclone.run_position_updates()`.
  - **Response**: `{"status": "position update started"}` (HTTP 202)
- `DELETE /data` – Run `Cyclone.run_clear_all_data()` in the background to wipe stored data.
  - **Response**: `{"status": "clear started"}` (HTTP 202)

## Portfolio API (`portfolio_api.py`)
**Base path**: `/portfolio`

- `GET /` – Return the entire portfolio history.
  - **Response model**: `list[PortfolioSnapshot]`
- `GET /latest` – Retrieve the most recent `PortfolioSnapshot` or `null` if none exist.
- `GET /api/portfolio/latest_snapshot` – Alias for `/portfolio/latest` returning the same payload.
-  Returns `null` until a snapshot has been recorded. Trigger one via
  `POST /positions/snapshot` or during a full cycle (`POST /cyclone/run`).
- `POST /` – Insert a new snapshot.
  - **Body**: `PortfolioSnapshot`
  - **Response**: `{"status": "created"}` (HTTP 201)
- `PUT /{entry_id}` – Update fields of an existing snapshot by ID.
  - **Body**: arbitrary JSON dict of fields to update
- `DELETE /{entry_id}` – Remove a snapshot by ID.

## Wallet API (`wallet_api.py`)
**Base path**: `/wallets`

- `GET /` – List wallets without forcing a balance refresh.
- `POST /` – Create a wallet.
  - **Body**: `Wallet`
  - **Response**: `{"status": "created"}` (HTTP 201)
- `PUT /{name}` – Update the wallet identified by `name`.
  - **Body**: `Wallet`
- `DELETE /{name}` – Delete the wallet.
- `POST /star_wars` – Insert sample "Star Wars" wallets via `WalletCore.insert_star_wars_wallets()`.
  - **Response**: `{"status": "inserted", "count": <int>}` (HTTP 201)

## Monitor Status API (`monitor_status_api.py`)
**Base path**: `/monitor_status`

- `GET /` – Return a `MonitorStatus` snapshot summarizing all monitors.
- `GET /{monitor_type}` – Retrieve details for a single monitor.
  - **Path parameter**: `monitor_type` (`MonitorType` enum name)
  - **Response model**: `MonitorDetail`
- `POST /{monitor_type}` – Update health metadata for a monitor.
  - **Body**: `{ "status": MonitorHealth, "metadata": Optional[dict] }`
  - **Response model**: `MonitorDetail`

## Positions API (`positions_api.py`)
**Base path**: `/positions`

- `GET /` – List all positions stored in the database.
  - **Response model**: `list[PositionDB]`
- `POST /` – Create a position record.
  - **Body**: `PositionDB`
  - **Response**: `{"status": "created"}` (HTTP 201)
- `DELETE /{pos_id}` – Delete a position by ID.
- `POST /snapshot` – Record a portfolio snapshot of current positions.
- `POST /update` – Run Jupiter position synchronization in the background.
- `POST /enrich` – Enrich all positions with live price data in the background.

## Alert Thresholds API (`alert_thresholds_api.py`)
**Base path**: `/alert_thresholds`

- `GET /` – List all configured alert thresholds.
- `GET /bulk` – Return the entire threshold configuration file.
- `PUT /bulk` – Replace all thresholds and cooldown settings.
  - **Body**: configuration JSON
- `GET /{threshold_id}` – Fetch a single threshold by ID.
- `POST /` – Create a new threshold (generates a UUID when omitted).
  - **Body**: `AlertThreshold`
  - **Response model**: `AlertThreshold` (HTTP 201)
- `PUT /{threshold_id}` – Update an existing threshold.
  - **Body**: JSON dict of fields to change
- `DELETE /{threshold_id}` – Delete a threshold by ID.

### Legacy Alert Endpoints (`alerts_router` in `alert_thresholds_api.py`)
**Base path**: `/alerts`

- `POST /refresh` – Retrieve alerts from storage; returns `{"success": true}` when reachable.
- `POST /create_all` – Load and insert sample alerts from `sample_alerts.json`.
- `POST /delete_all` – Remove all stored alerts.
- `GET /monitor` – Return `{ "alerts": [...] }` with all current alerts.

## XCom API (`xcom_api.py`)
**Base path**: `/xcom`

- `GET /config` – Return the configured notification providers.
  - **Response model**: `dict`
  - Secret fields such as tokens are masked with `***` in the response.
- `PUT /config` – Replace provider settings.
  - **Body**: provider configuration JSON
  - **Response**: `{"status": "updated"}` (HTTP 200)
- `POST /config/validate` – Validate Twilio credentials.
  - **Response**: `{"status": "ok"}` (HTTP 200)
- `GET /status` – Get aggregated status for Twilio, ChatGPT, Jupiter and GitHub.
  - **Response model**: `{"twilio": str, "chatgpt": str, "jupiter": str, "github": str}`
- `GET /check/{provider}` – Check a single provider by name.
  - **Path parameter**: `provider` ("twilio", "chatgpt", etc.)
  - **Response model**: `{"result": bool}`

Usage Notes:
  The XCom API manages notification settings and health checks for SMS, voice,
  email and chat integrations. When retrieving configuration, sensitive values are
  redacted so secrets do not leak through the API. Provide full secrets again
  when updating if they need to change.

---

These routers are included by FastAPI application startup in
`backend/sonic_backend_app.py` and are the primary interface consumed by the
React frontend.
