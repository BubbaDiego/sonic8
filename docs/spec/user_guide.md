Sonic Spec — User Guide

## What this spec gives you
- **Human overview**: `docs/spec/software_spec.md`
- **Machine facts**: `docs/spec/spec.manifest.yaml`
- **Contracts**: JSON Schemas in `docs/spec/schemas/`
- **OpenAPI**: `backend/api/openapi.yaml` (exported by `backend/scripts/export_openapi.py`)

## How to navigate
1. **Start here** → `software_spec.md` Section **0–2** for scope & repo map.
2. **Find a module** → Use **Repo Map** row → open that path in editor.
3. **Find an endpoint** → In `spec.manifest.yaml` under **apis**; each entry has:
   - `method` + `path`
   - `response_schema` → jump to a file in `docs/spec/schemas/…`
4. **Contracts first** → Read the JSON schema (look at `examples`) before coding.
5. **Run locally**
   - API: `uvicorn backend.sonic_backend_app:app --reload` (or your launcher)
   - Web: `cd frontend && npm run dev`[xcom_last_ping.json](schemas/xcom_last_ping.json)
   - Export OpenAPI: `python backend/scripts/export_openapi.py`

## Dev safety nets
- **Response validator (dev)**  
  Enable with `VALIDATE_RESPONSES=1`. Adds headers on responses:
  - `X-Validator-Enabled: 1`
  - `X-Schema-Invalid: …` (first error) or `X-Validator-Skip: no-mapping`
- **Spec CI**  
  Validates schemas/manifest and ensures every API has a `response_schema`.

## Adding/Updating an endpoint
1. Implement the route in FastAPI.
2. Add (or update) the **apis** entry in `spec.manifest.yaml` with:
   - `method`, `path`, `response_schema`
3. Create/adjust the JSON schema in `docs/spec/schemas/…`
   - Include 1 happy-path and 1 edge-case **example**.
4. (Option) Run the sweeper for Repo Map/Inventory:  
   `python backend/scripts/spec_sweeper.py`
5. (Option) Export OpenAPI:  
   `python backend/scripts/export_openapi.py`

## When the validator complains
- Open DevTools → Network → Headers.  
  - If `X-Validator-Skip: no-mapping`, add a `response_schema` entry in the manifest.
  - If `X-Schema-Invalid: …`, adapt the schema to the live payload (or adjust payload).

## Incident quick links
- See **Runbooks** in `software_spec.md` (RB-01/02/03).
- Common toggles:
  - `VALIDATE_RESPONSES=1` (dev validation)
  - `EXPORT_OPENAPI=1` (quiet heavy init during OpenAPI export)

## Conventions & IDs
- Stable IDs: `MOD-*`, `API-*`, `SCHEMA-*`, `EVT-*`, `CFG-*`.  
  Reference IDs, not file paths, inside prose to avoid drift.

## Don’t guess. Look it up.
- Paths/ports/ownership live in the manifest. Treat it as **source of truth**.
