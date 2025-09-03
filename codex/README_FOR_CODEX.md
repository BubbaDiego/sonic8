# Final: Jupiter Launch with Clean Alias Profile

Use **only** Playwright `user_data_dir=C:\sonic5\profiles\<walletId>` to pick the Chrome profile.
No `--profile-directory`. No `"User Data"` suffix anywhere.

## Files
- auto_core/launcher/open_jupiter.py
- backend/routers/jupiter.py
- scripts/verify_no_profile_flags.ps1 (optional)
- scripts/patch.diff (optional)

## Wire-up
Add to backend/sonic_backend_app.py:
    from backend.routers import jupiter
    app.include_router(jupiter.router)

## UI
POST /jupiter/open with { "walletId": "Leia" }

## CLI test
python auto_core\launcher\open_jupiter.py --wallet-id Leia
Check chrome://version => Profile Path == C:\sonic5\profiles\Leia
