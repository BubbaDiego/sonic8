# Sonic1

This repository contains the code for the Sonic1 project. It is organized into
three main parts:

- **backend/** – a FastAPI application providing the API.
- **frontend/** – a React + Vite application used for the UI.
- **docs/** – documentation and additional resources.

## Getting started

To run the backend locally first create a virtual environment for this
repository and install the requirements. Using an environment from another
clone (e.g. ``sonic2``) can load mismatched modules and cause import errors.

```bash
python backend/scripts/create_virtual_env.py
.venv/bin/pip install -r requirements.txt  # ``.venv\Scripts\pip`` on Windows
uvicorn backend.sonic_backend_app:app --app-dir backend --host 0.0.0.0 --port 5000 --reload
```

The backend expects several JSON configuration files under
`backend/config/`. The repo includes empty placeholders for most of them,
but if any are missing create the following files:

```
backend/config/active_traders.json
backend/config/alert_thresholds.json
backend/config/sonic_config.json
backend/config/sonic_sauce.json
backend/config/comm_config.json
backend/config/theme_config.json
```

`sonic_sauce.json` must contain at least the keys `hedge_modifiers` and
`heat_modifiers` as required by the backend's `JsonManager`.

The API routes access the persistence layer through a `DataLocker` instance.
Each router declares route parameters like `dl: DataLocker = Depends(get_locker)`
so FastAPI injects the locker for every request.  The helper
[`backend.deps.get_locker`](backend/deps.py) fetches the instance from the Flask
context when available, or falls back to the `DataLocker` singleton.

To start the frontend:

```bash
cd frontend
npm install
npm run start
```

The Vite dev server disables the hot module replacement (HMR) error overlay by
default. For local development you can enable it by editing
`frontend/vite.config.mjs` and adding the following block:

```js
server: { hmr: { overlay: true } }
```

Production builds can omit this overlay configuration.

### Tailwind CSS

The frontend uses Tailwind for utility classes. Base directives live in
`frontend/src/tailwind.css` and compile to `tailwind.output.css` during the
`yarn build` step. The generated file is imported in
`frontend/src/index.jsx` so any utilities defined in `tailwind.css` are
available throughout the app.

Feel free to explore each directory for more details.

See [docs/alert_thresholds_api.md](docs/alert_thresholds_api.md) for the alert thresholds API.
See [docs/backend_api_spec.md](docs/backend_api_spec.md) for a complete list of backend routes.
The new alert data layer is documented in [docs/alert_v2_spec.md](docs/alert_v2_spec.md).
The event-oriented extension lives in [docs/alert_v2_hybrid_spec.md](docs/alert_v2_hybrid_spec.md).

The `/portfolio/latest` endpoint will only return data after a portfolio snapshot is
recorded. You can create a snapshot using `POST /positions/snapshot` or by running
`POST /cyclone/run` to execute the full cycle.

## Frontend UI Guide
See [docs/berry_react_guide.md](docs/berry_react_guide.md) for details on the React codebase:
- Overview of the `src/` folder structure.
- State management with context and Redux.
- Supported authentication methods (JWT, Firebase, Auth0, AWS Cognito).
- Routing and theme customization options.

## Liquidation Bars card

The positions view contains a **Liquidation Bars** card that summarizes
liquidation risk for the tracked wallets. When you visit `/positions` and switch
to the liquidation view, this card renders a row of bar graphs for each
position. It now fetches data from the same `/positions/` API endpoint used by
the positions table, so both views display consistent information.

## Icons and thresholds

- Portfolio and positions tables now display wallet and asset icons from
  `frontend/static/images`.
- The **Alert Thresholds** page features an **Add Threshold** dialog for creating
  new records.
- Running `python backend/scripts/initialize_database.py --seed-thresholds`
  seeds default ranges for **Liquidation Distance** and **Profit** alerts.

## Debugging frontend connectivity

If the frontend UI does not show data, verify the backend API by running the
script `backend/scripts/api_breakpoint_test.py` while the server is up:

```bash
python backend/scripts/api_breakpoint_test.py
```

The script pings a couple of API endpoints and reports status codes to help
locate where the data flow is breaking.

## Logging

Backend modules use the `ConsoleLogger` from
[`backend/utils/console_logger.py`](backend/utils/console_logger.py) for
structured console output.  It can be configured programmatically or via
environment variables.

```python
from console_logger import ConsoleLogger as Log

Log.set_level("DEBUG")           # or: LOG_LEVEL=DEBUG python sonic_backend_app.py
Log.success("Service started")

Log.add_sink(lambda ev: open("app.log", "a").write(json.dumps(ev) + "\n"))
```

Environment variables recognised by the logger:

| Variable        | Purpose                               | Example |
|-----------------|---------------------------------------|---------|
| `LOG_LEVEL`     | Default minimum level                 | `INFO`  |
| `LOG_FORMAT`    | Set to `json` for JSON-only output    | `json`  |
| `LOG_JSON`      | Legacy alias for `LOG_FORMAT=json`    | `1`     |
| `LOG_NO_EMOJI`  | Strip emoji from console output       | `1`     |

Cyclone operations are also recorded to `logs/cyclone_log.txt`. The
`/cyclone/cyclone_logs` API endpoint returns the last few lines of this file.

See [CONSOLE_LOGGER_SPEC.md](backend/utils/CONSOLE_LOGGER_SPEC.md) for the full
specification.

## Database path configuration

`MOTHER_BRAIN_DB_PATH` controls where the project's main SQLite database (the
"mother brain") is stored. `backend/utils/startup_service.py` and related
scripts automatically load environment variables from a `.env` file at the
repository root (falling back to `.env.example` when present). Define
`MOTHER_BRAIN_DB_PATH` there or export it in your shell to override the default
`mother.db` in the repo root. `MOTHER_DB_PATH` is still recognised for backward
compatibility.

Both the FastAPI backend and the **Launch Pad** console read this value from the
environment, so they must reference the same database file.

## Maintenance operations

`CycloneMaintenanceService` provides helpers for wiping stored data during tests
or when resetting the environment. `clear_positions()` only removes open
positions and leaves the `positions_totals_history` table intact. Use
`clear_portfolio_history()` if you also want to wipe these snapshots. Running
`clear_all_tables()` clears alerts, prices and positions.
