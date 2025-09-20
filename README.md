# ---------------------------------------------------------
# 🦔 Sonic

Crypto automation & monitoring for Solana/Jupiter — wallet ops, swaps/perps, alerts, and dashboards.

- Backend: **FastAPI + service cores** (DataLocker, Cyclone, Alert V2, PositionStore)
- Frontend: **React + Vite + Tailwind**
- Automation: **Playwright** (Solflare/Jupiter flows)
- Contracts: **OpenAPI + JSON Schemas**
- Spec: human + machine docs kept in `docs/spec/`

---

## 📑 Spec

- **User Guide:** [`docs/spec/user_guide.md`](docs/spec/user_guide.md)  
- **Human (overview):** [`docs/spec/software_spec.md`](docs/spec/software_spec.md)  
- **Machine (manifest):** [`docs/spec/spec.manifest.yaml`](docs/spec/spec.manifest.yaml)  
- **OpenAPI:** [`backend/api/openapi.yaml`](backend/api/openapi.yaml)

> Tip: in dev, enable the response validator with `VALIDATE_RESPONSES=1` to get per-route schema checks (adds headers like `X-Validator-Enabled`).

---

## 🚀 Quickstart (Dev)

### Backend
```bash
# Windows PowerShell
$env:VALIDATE_RESPONSES="1"   # optional: enable schema validation
uvicorn backend.sonic_backend_app:app --reload --port 5000

Frontend
cd frontend
npm install
npm run dev

Export OpenAPI (dev tool)
python backend/scripts/export_openapi.py
# writes backend/api/openapi.yaml

🗺️ Repo Map (high level)
backend/
  api/                # FastAPI routes & API layer
  core/               # Cyclone, monitors, alerting, services
  wallet_core/        # Wallet ops & signing
  scripts/            # CLIs and tooling (openapi export, spec tools)
frontend/             # React/Vite/Tailwind UI
docs/
  spec/               # Spec (human + machine) and JSON Schemas


See the full table in docs/spec/software_spec.md → Section 2 (Repo Map).

⚙️ Config
KeyRequiredUsed byNotes
RPC_URLyesMOD-AUTO, MOD-SVCSolana RPC (Helius/official)
HELIUS_RPC_URLnoMOD-SVCOptional override
WALLET_SECRET_BASE64yesMOD-WALLETBase64 keypair
JUPITER_API_BASEnoMOD-API, MOD-AUTOOptional custom base
REDIS_URLnoMOD-SVCOptional cache/bus
VALIDATE_RESPONSESnoMOD-API (dev)1 enables schema validator
EXPORT_OPENAPInoexporter (dev)1 to quiet heavy init on export

Secrets live in environment variables / .env — never in the repo.

✅ Dev Safety Nets

Response Validator (dev)
VALIDATE_RESPONSES=1 adds:

X-Validator-Enabled: 1

X-Schema-Invalid: <reason> (if payload doesn’t match the schema)

X-Validator-Skip: no-mapping (add a response_schema in the manifest)

Spec CI
GitHub Action validates JSON Schemas and manifest paths and ensures every API has a response_schema.

🧰 Spec Tooling
# Map any newly added FastAPI routes into the manifest (method/path)
python backend/scripts/spec_api_mapper.py

# Sample live responses and auto-draft JSON Schemas (SPEC_BASE_URL optional)
python backend/scripts/spec_schema_sampler.py

# Refresh Repo Map & Module Inventory in the human spec
python backend/scripts/spec_sweeper.py

📈 Observability & Runbooks

Logging: “CYCLONE ENGINE STARTUP”, “Loaded N positions :: [PositionStore] …”

Metrics (proposed): request_latency_ms, monitor_events_processed_total, perps_order_failures_total, wallet_rpc_errors_total

Tracing: HTTP → service → external (RPC/Jupiter)

Runbooks: see docs/spec/software_spec.md → Section 10 (RB-01/02/03)

🧪 Test / Validate
# Schemas valid?
python - <<'PY'
import json, glob
from jsonschema.validators import Draft202012Validator as V
for p in glob.glob('docs/spec/schemas/*.json'):
    V.check_schema(json.load(open(p, encoding='utf-8')))
print("Schemas OK")
PY

🤝 Contributing

Implement the route.

Add/confirm apis[].response_schema in spec.manifest.yaml.

Write/update the JSON Schema with examples under docs/spec/schemas/.

(Optional) run the sweeper; export OpenAPI.

Ensure Spec CI is green.

📝 License

Proprietary. All rights reserved. (Adjust if you plan to open-source.)

---------------------------------------------------------
🔚 **END CODEX**
