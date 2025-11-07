# Database Console (Sonic)

This drop-in adds a **Database Console** for SQLite (mother.db), with exploration, DataLocker helpers, maintenance, wizards, backups, and exports.

## Files
- `backend/console/db_console_service.py` — full console implementation
- `backend/console/db_console.py` — thin wrapper for `-m backend.console.db_console`

## Run

```
python -m backend.console.db_console
```

Always show details

## Add to LaunchPad
Import and add a menu entry:
```python
# at top
from backend.console.db_console import run_console as run_db_console
# ...
elif choice == "17":
    run_db_console()
```

## Safety

Read-only by default. Write operations (VACUUM/ANALYZE/REINDEX, WAL/foreign_keys toggle, restore) require Settings → Danger mode ON and a typed confirmation.

Snapshots are stored in reports/db_backups/. Exports land in reports/db_console/.

Uses SQLite backup API to copy/restore to avoid partial file writes.

Always show details

