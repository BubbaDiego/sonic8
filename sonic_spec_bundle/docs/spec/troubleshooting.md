# Troubleshooting

## Common: OpenAPI missing or stale
- Run: `make openapi` (ensure `api/main.py` exposes `app`)

## React dev server can’t reach API
- Check `.env` for `VITE_API_BASE_URL`
- CORS settings in `api/main.py` → `CORSMiddleware` origins

## Decimal validation errors
- Ensure price/qty sent as quoted strings in JSON payload

## Idempotency conflict
- Change `Idempotency-Key` when request body changes
