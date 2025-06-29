# Sonic1

This repository contains the code for the Sonic1 project. It is organized into
three main parts:

- **backend/** – a FastAPI application providing the API.
- **frontend/** – a React + Vite application used for the UI.
- **docs/** – documentation and additional resources.

## Getting started

To run the backend locally:[app.py](backend/app.py)

```bash
python backend/app.py
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
npm run dev
```

Feel free to explore each directory for more details.

## Debugging frontend connectivity

If the frontend UI does not show data, verify the backend API by running the
script `backend/scripts/api_breakpoint_test.py` while the server is up:

```bash
python backend/scripts/api_breakpoint_test.py
```

The script pings a couple of API endpoints and reports status codes to help
locate where the data flow is breaking.
