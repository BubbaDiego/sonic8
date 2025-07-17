
# Alert V2 Hybrid – Integration Spec
**Generated:** 2025-07-17T17:57:12.044663

This spec extends the previously delivered Alert V2 by adding **event streaming** while keeping a small `alert_state` table.

## New components
| File | Role |
|------|------|
| `models.AlertEventTbl` / `AlertEvent` | Append‑only event rows. |
| `repository.add_event()` | Persist events and query history. |
| `services/evaluation.py` | Pure function compares metric vs thresholds and returns `(state, event)`. |
| `orchestrator.py` | Runs every cycle: read → evaluate → save state → write event → notify. |

## Database change
```sql
CREATE TABLE alert_event (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL REFERENCES alert_config(id),
    level TEXT NOT NULL,
    metric_value REAL NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE alert_state
  ADD COLUMN last_event_id TEXT,
  ADD COLUMN last_level TEXT DEFAULT 'NORMAL',
  ADD COLUMN last_value REAL;
```

Run `AlertRepo.ensure_schema()` to auto‑create / migrate in dev; use Alembic for prod rollout.

## Orchestrator wiring
```python
from alert_v2_hybrid import AlertRepo
from alert_v2_hybrid.orchestrator import AlertOrchestrator, MetricFeedAdapter, NotificationRouter

repo = AlertRepo()
metrics = MetricFeedAdapter(metric_fn=my_metric_resolver)
router = NotificationRouter(send_fn=my_notifier)

orch = AlertOrchestrator(repo, metrics, router)

async def sonic_cycle():
    ...
    await asyncio.to_thread(orch.run_cycle)
```

## Test impact
* Add unit test that `evaluate()` emits an event when level flips.
* Add integration test that orchestrator writes both `alert_state` and `alert_event`.

---
*Author: Juniper AI*
