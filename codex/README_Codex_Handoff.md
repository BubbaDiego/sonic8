# Sonic Labs — Chrome Profile Alias Launch (Codex Handoff)

This patch makes **Open Jupiter & Connect** launch **Google Chrome** with the **alias the user types**
(e.g., `Leia`, `R2`, `Lando`) by using a dedicated **user-data directory per alias**.

## Files

- `auto_core/config/chrome_profiles.json` — alias → absolute user_data_dir
- `auto_core/config/chrome_launcher_config.json` — Chrome exe, channel, Solflare config
- `auto_core/launcher/chrome_profile_resolver.py` — resolves alias → dir
- `auto_core/launcher/open_jupiter.py` — Playwright launcher (persistent context)
- `backend/routers/jupiter.py` — FastAPI endpoints (open/close/status)
- `scripts/test_open_jupiter.ps1` — quick CLI test
- `patch.diff` — include_router hint

## Install

```
pip install playwright fastapi uvicorn pydantic
python -m playwright install chrome
```

Add to `backend/sonic_backend_app.py`:

```python
from backend.routers import jupiter
app.include_router(jupiter.router)
```

## UI Calls

POST `/jupiter/open` → `{ "walletId": "Leia" }`  
POST `/jupiter/close` → `{ "walletId": "Leia" }` or `null` to close all  
GET  `/jupiter/status` → session map
