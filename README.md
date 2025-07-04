# Sonic1

This repository contains the code for the Sonic1 project. It is organized into
three main parts:

- **backend/** – a FastAPI application providing the API.
- **frontend/** – a React + Vite application used for the UI.
- **docs/** – documentation and additional resources.

## Getting started

To run the backend locally install the requirements and then start the server:

```bash
pip install -r requirements.txt
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

To start the frontend:

```bash
cd frontend
npm install
npm run start
```

The Vite dev server disables the hot module replacement (HMR) error overlay by
default. You can change this by editing `frontend/vite.config.mjs` and setting
`server.hmr.overlay` to `true`.

Feel free to explore each directory for more details.

## Frontend UI Guide
See [docs/berry_react_guide.md](docs/berry_react_guide.md) for details on the React codebase:
- Overview of the `src/` folder structure.
- State management with context and Redux.
- Supported authentication methods (JWT, Firebase, Auth0, AWS Cognito).
- Routing and theme customization options.

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

See [CONSOLE_LOGGER_SPEC.md](backend/utils/CONSOLE_LOGGER_SPEC.md) for the full
specification.

## Maintenance operations

`CycloneMaintenanceService` provides helpers for wiping stored data during tests
or when resetting the environment. Calling `clear_positions()` now also removes
all records from the `positions_totals_history` table so portfolio charts start
fresh. Running `clear_all_tables()` includes this cleanup in addition to
clearing alerts and prices.
