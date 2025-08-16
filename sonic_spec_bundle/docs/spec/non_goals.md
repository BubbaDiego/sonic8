# Non-Goals & Red Lines

- Sonic does **not** expose direct DB access over HTTP.
- No implicit retries for non-idempotent writes.
- UI must not call provider APIs directly; always go through API.
- No floating point for money or price types.
