# Hand-off to Codex (Implementation Guide)

Codex, your task is to **fill in blanks** and wire this spec to the existing Sonic repo (Python/React/FastAPI).

## Objectives
1) Replace TODOs in `/docs/spec/*` with Sonic domain specifics (perps, collateral, liquidation distance, TP/SL, etc.).  
2) Ensure `api/openapi.yaml` builds from the real FastAPI app.  
3) Export JSON Schemas for all public payloads used by the UI and strategies.  
4) Keep the docs up-to-date via `make spec-sync`.

## Steps
1. **Clone + Setup**
   - Place this bundle at the **repo root**.
   - Ensure Python 3.10+ and Node 18+ are installed.

2. **OpenAPI generation**
   - Point `api/generate_openapi.py` import to the real FastAPI `app` symbol if it isn’t `api.main:app`.
   - Run: `make openapi`. Verify `api/openapi.yaml` is created.

3. **Spec sync**
   - Run: `make spec-sync`. Verify `docs/spec/codebase_map.md` is populated.

4. **Fill domain details**
   - `docs/spec/domain_glossary.md`: define **Account, Position, Order, Signal, Strategy, Alert** precisely and link to canonical types.
   - `docs/spec/workflows.md`: add end-to-end examples (UI → API → core → infra). Include invariants and failure modes for collateral adjust, liquidation alerts, TP/SL automation.
   - `docs/spec/ui_contracts.md`: document route map, API client surface, and error surfaces used in Sonic’s React app.

5. **Data Contracts**
   - Expand `/docs/schemas/*.json` to cover all entities (account, position, instrument, strategy config, alert).
   - Ensure the **wire types** (JSON Schema) match Pydantic models (source of truth).

6. **Validation**
   - Run: `make spec-validate` to ensure required docs exist.
   - Add **golden tests** `tests/golden/*` (small, readable). Reference them from workflows.

7. **Nice-to-Have**
   - Add `/docs/diagrams/architecture.png` and sequence diagrams for 2–3 critical flows.
   - Consider a `docs/site/` (MkDocs) to publish as a small docs site with stable anchors.

## Guardrails for Codex
- **Never invent endpoints.** Only document routes that exist in `openapi.yaml`.
- **Decimals on the wire as strings.** No floats for money/price.
- **Prefer core use-cases.** API should call `core/*` rather than infra directly.
- **Idempotency required** for writes. Surface `Idempotency-Key` in client.

## Deliverables back to the user
- Updated docs with no TODOs.
- `api/openapi.yaml` generated successfully.
- Expanded JSON Schemas covering all public payloads.
- Short CHANGELOG added to `docs/spec/master.md` with your edits.
