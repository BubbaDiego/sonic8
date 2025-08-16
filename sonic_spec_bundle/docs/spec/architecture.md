# Architecture

## Services
- **API (FastAPI)** — request validation, auth, orchestration; routers in `api/routers/*`, deps in `api/deps.py`.
- **Core (Python)** — pure domain logic; deterministic, side-effect free; `core/*`.
- **Infra (Adapters)** — DB, cache, queues, providers; `infra/*`.
- **Web (React)** — UI; `web/src/*`.

## Data Flow (happy path)
1. Web/Client calls API endpoint (`api/routers/...`).
2. FastAPI validates payload (Pydantic), resolves deps (auth/ctx).
3. Handler calls `core.*` use case (no I/O inside core).
4. Infra adapters perform I/O (db/external API) as injected deps.
5. Response mapped to transport model and returned.

## Error Model
- All errors mapped to `{error: {code, message}}`.  
- Retryable errors use `code=RETRYABLE_*`; non-retryable use `VALIDATION_*` or `DOMAIN_*`.

## Observability
- **Logging:** structured; keys: `event`, `entity`, `entity_id`, `correlation_id`.
- **Tracing:** optional OpenTelemetry; propagates through API→Infra.
- **Metrics:** counters for orders placed, positions opened, errors by code.

## Diagrams
- System: `docs/diagrams/architecture.png` (add)
- Sequences: `docs/diagrams/seq_*.png` (add)
