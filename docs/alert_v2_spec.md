
# Alert V2 – Integration Spec
**Version:** 2025-07-16T21:09:28.905280  
**Scope:** Data/model layer rewrite only – API, services and UI untouched (for now).

---
## 1. Package layout
```txt
alert_v2/
├── __init__.py           # exposes AlertRepo
├── db.py                 # engine + SessionLocal factory
├── models.py             # SQLAlchemy tables + Pydantic DTOs
└── repository.py         # AlertRepo CRUD facade
```
All files are self‑contained – zero runtime deps on the legacy `alert_core` or `data` stack.

## 2. Quick start
```python
from alert_v2 import AlertRepo
from alert_v2.models import AlertConfig, Condition

repo = AlertRepo()
repo.ensure_schema()  # creates tables if they don't exist

cfg = AlertConfig(
    id="alert-001",
    alert_type="PriceThreshold",
    alert_class="Position",
    trigger_value=42000,
    condition=Condition.ABOVE,
)
repo.add_config(cfg)
```

## 3. FastAPI wiring
Register `AlertRepo` as a dependency:

```python
from fastapi import Depends, APIRouter
from alert_v2 import AlertRepo

def get_repo():
    return AlertRepo()

router = APIRouter()

@router.get("/alerts")
def list_states(repo: AlertRepo = Depends(get_repo)):
    return repo.active_states()
```

## 4. DataLocker bridging (optional)
If you still rely on `DataLocker`, create the repo from its session:

```python
locker = get_locker()    # existing factory
repo = AlertRepo(session=locker.db.get_session())
```

## 5. Migrations
A helper to import legacy alerts:

```python
def migrate_legacy(dl_alerts):
    repo = AlertRepo()
    repo.ensure_schema()
    for row in dl_alerts.get_all_alerts():
        cfg = AlertConfig(
            id=row["id"],
            description=row["description"],
            alert_type=row["alert_type"],
            alert_class=row["alert_class"],
            trigger_value=row["trigger_value"],
            condition=row["condition"],
            notification_type=row["notification_type"],
            position_reference_id=row["position_reference_id"],
            created_at=row["created_at"],
        )
        repo.add_config(cfg)
```

## 6. Next steps
* Rewrite `AlertOrchestrator` to consume `AlertRepo` instead of DL managers.
* Add background task that calls `repo.active_states()` and runs evaluation.
* Replace `/alert_thresholds` endpoints with `ThresholdTbl` CRUD via the repo.

---
*Author: Juniper AI – generated for Codex hand‑off.*
