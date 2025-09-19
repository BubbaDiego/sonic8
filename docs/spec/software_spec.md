# Software Specification — TEMPLATE

> Place this folder at the **repo root** as `/SPEC/`. Keep IDs stable.

## 0) Cover & Quickstart
- **Project name**: <fill>
- **Purpose (one line)**: <fill>
- **Elevator pitch**:
  - <bullet 1>
  - <bullet 2>
  - <bullet 3>
- **Primary entrypoints**
  - CLI: <path or command>
  - API base URL: <url or localhost:port>
  - Key scripts: <paths>
- **Run (dev)**
  1. `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`)
  2. `pip install -r requirements.txt`
  3. <start command>
- **Run (prod)**: <fill>
- **Spec map**: see `spec.manifest.yaml` and sections below.

## 1) Architecture Overview
- **Context**: <one paragraph>
- **Runtime topology**: services, queues, DBs, external APIs
- **Data flow (one request)**: step-by-step bullets
- **Authoritative repos/paths**: list canonical sources of truth

## 2) Repo Map
| ID | Path | Role | Owner | Notes |
|---|---|---|---|---|
| MOD-<ID> | `path/` | <role> | <@owner> | <notes> |

## 3) Module Inventory
### MOD-<ID>
- **Purpose**: <fill>
- **Entry files**: <files>
- **Key classes/functions**: <signatures>
- **Dependencies**: internal + external
- **Inputs/Outputs**: link to schemas
- **Contracts & invariants**: <fill>
- **Gotchas**: <fill>

## 4) Public Interfaces
### HTTP/WS APIs
- Link or embed OpenAPI fragment
- Example requests/responses

### CLIs & Scripts
- Synopsis, examples, exit codes

### Background Jobs
- Trigger/schedule, inputs/outputs, idempotency

### Events
- Topic names, producers, consumers

## 5) Data Contracts (Schemas)
- Put machine-readable schemas in `/SPEC/schemas/`. See `schemas/Position.json` example.

## 6) Configuration & Secrets
| Key | Type | Default | Required | Source | Used by |
|-----|------|---------|----------|--------|---------|
| CFG-<KEY> | string | — | yes | `.env` | [MOD-<ID>] |

- Secrets location & handling policy
- Per-env diffs (dev/stage/prod)

## 7) Observability
- Logging format/levels/correlation
- Metrics (name, unit, expected cardinality)
- Tracing boundaries
- Dashboards/alerts

## 8) Reliability & Performance
- SLOs/SLAs
- Perf budgets (P95 targets)
- Backpressure & retries
- Idempotency

## 9) Security & Compliance
- AuthN/Z model
- Data classification
- Threat model (top 3 risks + mitigations)

## 10) Build, Deploy, Runbooks
- Build commands
- Deploy steps (CI/CD)
- Rollback plan
- Common incidents + one-page runbooks

## 11) Test Strategy
- Test pyramid
- How to run tests locally/CI
- Golden vectors

## 12) Roadmap & Known Gaps
- Limitations
- Next 3 milestones (DOR/DoD)

## 13) Glossary & IDs
- Short definitions + ID list (MOD-, API-, EVT-, SCHEMA-, CFG-)

## 14) Do/Don’t for GPTs
- **Do**: Trust `spec.manifest.yaml` for paths/ports.
- **Don’t**: Infer wallet derivation or hidden config—read `CFG-*` keys first.

## 15) Changelog
- `v1`: initial scaffold.
