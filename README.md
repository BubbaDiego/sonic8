# 🦔 Sonic

![Spec CI](https://github.com/BubbaDiego/sonic5/actions/workflows/spec-ci.yml/badge.svg)

> Crypto automation & monitoring for Solana/Jupiter — wallet ops, swaps/perps, alerts, and dashboards.

<!-- LAST_UPDATED:BEGIN -->
_Last updated: (pending — auto-stamped by CI)_
<!-- LAST_UPDATED:END -->

- Backend: **FastAPI + service cores** (DataLocker, Cyclone, Alert V2, PositionStore)
- Frontend: **React + Vite + Tailwind**
- Automation: **Playwright** (Solflare/Jupiter flows)
- Contracts: **OpenAPI + JSON Schemas**
- Spec: human + machine docs kept in `docs/spec/`

---

## 📑 Sonic Spec

- **User Guide:** [`docs/spec/user_guide.md`](docs/spec/user_guide.md)  
- **Human (overview):** [`docs/spec/software_spec.md`](docs/spec/software_spec.md)  
- **Machine (manifest):** [`docs/spec/spec.manifest.yaml`](docs/spec/spec.manifest.yaml)
- **OpenAPI:** [`backend/api/openapi.yaml`](backend/api/openapi.yaml)

> **Spec CI status:** Check the badge at the top of this README.  
> For full logs: **Actions → Spec CI**. If it fails, run `make spec-validate` locally
> to see which schema/manifest path or response_schema mapping needs fixing.

> Tip: in dev, enable the response validator with `VALIDATE_RESPONSES=1` to get per-route schema checks (adds headers like `X-Validator-Enabled`).

---

## 🛠️ Developer workflow cheat-sheet

> Dependency management for Node.js packages occurs entirely inside **`frontend/`**.  
> The repository root does not use `npm` or `yarn` directly.

Common automation lives in the project **Makefile**. These shortcuts wrap Python and Node tooling:

| Target              | What it does                                           |
|--------------------|---------------------------------------------------------|
| `make install`     | Install Python requirements + frontend deps             |
| `make dev-api`     | Start FastAPI with auto-reload                          |
| `make dev-web`     | Launch the Vite development server                      |
| `make openapi`     | Regenerate `backend/api/openapi.yaml`                   |
| `make spec-validate` | Validate schemas + manifest + response_schema coverage|
| `make spec-ci`     | Run the same validation routine used in CI              |

---

## 🚀 Quickstart (Dev)

### Backend
```bash
python backend/scripts/create_virtual_env.py
.venv/bin/pip install -r requirements.txt       # Windows: .venv\Scripts\pip install -r requirements.txt
.venv/bin/playwright install                    # browsers for AutoCore / Playwright tests
uvicorn backend.sonic_backend_app:app --host 0.0.0.0 --port 5000 --reload
```

The backend expects JSON configuration files under `backend/config/`. Create these if missing:

```
backend/config/active_traders.json
backend/config/alert_thresholds.json
backend/config/sonic_config.json
backend/config/sonic_sauce.json   # must include hedge_modifiers + heat_modifiers
backend/config/comm_config.json   # supports ${VAR} env expansion
backend/config/theme_config.json
```

Provider entries in `comm_config.json` merge into `xcom_providers` on startup; only specified keys overwrite existing ones.

### Frontend
```bash
cd frontend
npm install
npm run dev
# Optional:
# npm run build:css    # if your UI uses a build step for Tailwind / SCSS
```

### Optional: HMR overlay

Enable in `frontend/vite.config.mjs`:

```
server: { hmr: { overlay: true } }
```

### Serve from a sub-directory

If hosting under a subpath (e.g. `/ui/`), set `VITE_APP_BASE_NAME` in `frontend/.env`.

### Tailwind CSS

Base directives live in `frontend/src/tailwind.css` and compile during the build step (e.g. `npm run build`).

### 🗺️ Repo map (high level)
```
backend/
  api/                # FastAPI routes & API layer
  core/               # Cyclone, monitors, alerting, services
  wallet_core/        # Wallet ops & signing
  scripts/            # CLIs and spec tools (openapi export, sweeper, validators)
frontend/             # React/Vite/Tailwind UI
docs/
  spec/               # Spec (human + machine) and JSON Schemas
```

See the detailed table in `docs/spec/software_spec.md` → Section 2.

### 📦 Config & Secrets

| Key | Required | Used by | Notes |
| --- | --- | --- | --- |
| `RPC_URL` | yes | MOD-AUTO, MOD-SVC | Solana RPC (Helius/official) |
| `HELIUS_RPC_URL` | no | MOD-SVC | Optional override |
| `WALLET_SECRET_BASE64` | yes | MOD-WALLET | Base64 keypair |
| `JUPITER_API_BASE` | no | MOD-API, MOD-AUTO | Optional custom base |
| `REDIS_URL` | no | MOD-SVC | Optional cache/bus |
| `VALIDATE_RESPONSES` | no | MOD-API (dev) | `1` enables schema validator headers |
| `EXPORT_OPENAPI` | no | exporter (dev) | `1` to quiet heavy init on OpenAPI export |
| `MOTHER_BRAIN_DB_PATH` | no | backend + Launch Pad | Overrides default `mother.db` in repo root |
| `LIQ_MON_SMS_ALERT` | no | Liquidation Monitor | Enable SMS notifications |
| `SOLFLARE_CRX` | no | AutoCore (Playwright) | Path to Solflare extension `.crx` |

Secrets live in environment variables / `.env` — never in the repo.

### 🔊 TTS & audio (optional)

- `playsound` — MP3 alert sounds (fallback is ASCII bell if missing)
- `pyttsx3` — local text-to-speech
  - Install: `pip install playsound pyttsx3`
  - Enable a TTS provider in `comm_config.json`:

```
"tts": { "enabled": true, "voice": "Zira", "speed": 140 }
```

### 🔌 API & data notes

- `/portfolio/latest` returns data only after a portfolio snapshot exists. Create a snapshot with `POST /positions/snapshot` or run `POST /cyclone/run`.
- Routers use DataLocker via DI in `backend/deps.py` (`dl: DataLocker = Depends(get_locker)`).
- Debugging connectivity:
  - Run `python backend/scripts/api_breakpoint_test.py` while the server is up to ping core endpoints.

### 💹 UI details

- Liquidation Bars card under `/positions` summarizes liquidation risk; powered by the same `/positions/` API as the table for consistency.
- Icons for wallets/assets are served from `frontend/static/images`.
- Thresholds UI at `/alert-thresholds`. Seed defaults via:

```bash
python backend/scripts/initialize_database.py --seed-thresholds
```

### 🧪 Tests

**Frontend — Jest + React Testing Library:**

```bash
cd frontend
npm install
npm test
```

**Backend — Pytest:**

```bash
python backend/scripts/create_virtual_env.py
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install
.venv/bin/pip install -r requirements-dev.txt
pytest
```

### 📈 Observability (quick)

- Logs: “CYCLONE ENGINE STARTUP”, “Loaded N positions :: [PositionStore] …”
- Metrics (proposed): `request_latency_ms`, `monitor_events_processed_total`, `perps_order_failures_total`, `wallet_rpc_errors_total`
- Tracing: HTTP → service → external (RPC/Jupiter)
- Runbooks (RPC exhausted, Perps order failing, Solflare connect fails) live in `docs/spec/software_spec.md`.

### 📚 More docs

- Alert Thresholds API — `docs/alert_thresholds_api.md`
- Backend routes list — `docs/backend_api_spec.md`
- Frontend UI guide — `docs/berry_react_guide.md`

### 🧰 Spec Tooling (local helpers)

```bash
# Map any newly added FastAPI routes into the manifest (method/path)
python backend/scripts/spec_api_mapper.py

# Sample live responses and auto-draft JSON Schemas
python backend/scripts/spec_schema_sampler.py

# Refresh Repo Map & Module Inventory in the human spec
python backend/scripts/spec_sweeper.py
```

---[software_spec.md](docs/spec/software_spec.md)

## 📝 License

Proprietary. All rights reserved. (Adjust if you plan to open-source.)

## Hybrid TS → Python account oracle (perps)

We vend canonical accounts for `createIncreasePositionMarketRequest` from TypeScript helpers aligned with the upstream Jupiter repo.

### One-time setup

```bash
npm install
npm install --save-dev ts-node typescript
```

### Test the CLI directly

```bash
node --loader ts-node/esm perps_accounts.ts \
  --market SOL-PERP \
  --side long \
  --size-usd 11 \
  --collateral-usd 11 \
  --owner <YOUR_WALLET_PUBKEY> \
  --rpc "https://rpc.helius.xyz/?api-key=$HELIUS_API_KEY"
```

### Python integration

`open_position_request` calls the CLI, receives JSON `{ accounts, remainingAccounts }`, and builds the instruction from that mapping (no more seed guessing).
