# Conventions

## Naming
- Python: snake_case; classes PascalCase
- React: components PascalCase; hooks use `useX`
- Files: one main public type/module per file

## Time & Money
- Timezones: UTC everywhere, ISO8601 strings on the wire
- Money/Price: Decimal (string on wire), never float

## Errors
- Codes are machine-stable
- HTTP status:
  - 2xx success
  - 4xx validation or domain errors
  - 5xx provider/infra

## Retries & Idempotency
- All write endpoints accept `Idempotency-Key` header
- Client retries only on `RETRYABLE_*` codes

## Testing
- Unit tests in `tests/unit/*`; E2E in `tests/e2e/*`
- Golden tests in `tests/golden/*` with readable comments

## Folder Roles
- `core/*` — pure domain, no I/O
- `infra/*` — adapters only
- `api/*` — transport layer, mapping, DI
- `web/*` — UI; API calls via a single client layer
