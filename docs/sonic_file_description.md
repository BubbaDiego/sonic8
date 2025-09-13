# Sonic File Descriptions

The notes below summarize the purpose of key files and directories in the repository root.

## Root Level
- **api/** – Lightweight API client with Pydantic models and `openapi.yaml`.
- **backend/** – FastAPI backend application with configs, controllers, routers, services and helper scripts.
- **core/** – Shared domain models used by the API, backend and tests.
- **data/** – Sample SQLite databases and other datasets for development.
- **docs/** – Documentation, specifications and guides (including this file).
- **frontend/** – React + Vite user interface.
- **idl/** – Anchor interface definition files for external programs.
- **patches/** – Patch files applied to vendored upstream components.
- **sonic_spec_bundle/** – Specification bundle with API docs and scripts.
- **test_core/** – Utilities and unit tests for the core spec runner.
- **tests/** – Pytest suite covering backend services, APIs and CLI tools.
- **balances_bulk.py** – Script retrieving token balances for multiple wallets.
- **crypto_console.py** – Interactive CLI for blockchain operations.
- **dump_token_accounts.py** – Helper script for inspecting on-chain token accounts.
- **launch_pad.py** – Helper to start backend and auxiliary services.
- **wallet_cli.py** / **wallet_balances.py** – CLI utilities for wallet management.
- **twilio_run.py** / **twilio_verify.py** – SMS verification scripts.
- Miscellaneous helpers like `send_test_sms.py` for sending test messages.

## backend/
- **config/** – JSON files and loaders for runtime configuration.
- **controllers/** – Business logic for cyclone and monitor features.
- **core/** – Core backend utilities such as message queues and persistence.
- **data/** – Embedded datasets and seed information.
- **models/** – ORM/Pydantic models representing database objects.
- **routers/** / **routes/** – FastAPI route declarations for REST endpoints and WebSocket streams.
- **scripts/** – Maintenance and setup scripts (virtualenv creation, seeding).
- **services/** – Background services including monitors and sound/notification systems.
- **utils/** – Shared helpers (logging, DB setup, scheduling).
- **sonic_backend_app.py** – Entry point for running the FastAPI application.

## frontend/
The React application for the Sonic dashboard. Key areas include:
- **src/** – Application source (components, hooks, views, etc.).
- Build and configuration files such as `vite.config.mjs`, `tailwind.config.js` and `package.json`.
See `frontend_file_description.md` and `frontend_repo_map.md` for detailed frontend information.

## test_core/
Core spec runner with fixtures, reports and tests for automated scenarios.

## tests/
Comprehensive Pytest suite for API routes, monitor logic and CLI interfaces.
