# 🚨 Alert Core Specification

> Version: `v1.0`
> Author: `CoreOps 🥷`
> Scope: Alert orchestration, enrichment, evaluation and notification.

---

## 📂 Module Structure
```txt
alert_core/
├── __init__.py                   # Exports AlertCore alias
├── alert_controller.py           # High level operations
├── config/
│   └── loader.py                 # JSON config loader
├── domain/
│   └── models.py                 # Pydantic alert models
├── infrastructure/
│   ├── stores.py                 # SQLite stores
│   └── notifiers/
│       ├── base.py               # Notifier base class
│       ├── router.py             # NotificationRouter
│       ├── sms.py                # Twilio SMS notifier
│       └── windows_toast.py      # Windows toast notifier
├── services/
│   ├── orchestration.py          # AlertOrchestrator facade
│   ├── enrichment.py             # Enrichment service
│   └── evaluation.py             # Determine alert level
├── threshold_service.py          # Threshold CRUD wrapper
└── utils.py                      # Helpers and normalizers
```

### 🚨 `AlertOrchestrator`
Central facade that loads stores, enrichment/evaluation services and dispatches notifications.
```python
class AlertOrchestrator:
    def __init__(self, store: AlertStore | None = None) -> None:
        self.store = store or AlertStore()
        self.log_store = AlertLogStore(self.store.db)
        self.enricher = AlertEnrichmentService(self.store.db)
        self.evaluator = AlertEvaluationService()
        self.notifiers = default_router
```
【F:alert_core/services/orchestration.py†L24-L32】
It exposes `create_alert()`, `enrich_all_alerts()` and `process_alerts()` to persist alerts, enrich them, evaluate the level and notify via configured notifiers. Processing also writes a log entry for each phase.【F:alert_core/services/orchestration.py†L34-L109】

### 🧩 `AlertEvaluationService`
Computes the final `AlertLevel` based on the evaluated value and comparison condition.
```python
class AlertEvaluationService:
    def evaluate(self, alert: Alert) -> Alert:
        value = alert.evaluated_value
        if value is None:
            alert.level = AlertLevel.NORMAL
            return alert
        if alert.condition == Condition.ABOVE:
            alert.level = (
                AlertLevel.HIGH if value >= alert.trigger_value else AlertLevel.NORMAL
            )
        elif alert.condition == Condition.BELOW:
            alert.level = (
                AlertLevel.HIGH if value <= alert.trigger_value else AlertLevel.NORMAL
            )
        else:
            alert.level = AlertLevel.NORMAL
        return alert
```
【F:alert_core/services/evaluation.py†L6-L25】

### 🧪 `AlertEnrichmentService`
Placeholder service that injects the latest value for each alert. Currently returns the trigger value as the evaluated value.【F:alert_core/services/enrichment.py†L9-L18】

### 🗄️ `AlertStore` and `AlertLogStore`
SQLite-backed persistence layer used by the orchestrator.
`AlertStore` ensures the `alerts` table and provides `create()`, `list_active()` and `update_level_value()`.【F:alert_core/infrastructure/stores.py†L12-L123】
`AlertLogStore` records processing events to the `alert_log` table and can list entries by alert id.【F:alert_core/infrastructure/stores.py†L126-L173】

### 🔔 Notification System
`NotificationRouter` selects notifier instances for an alert based on its `notification_type` field.【F:alert_core/infrastructure/notifiers/router.py†L9-L38】
Two built-in notifiers are provided:
- **SMSNotifier** sends text messages via Twilio if credentials are available.【F:alert_core/infrastructure/notifiers/sms.py†L10-L26】
- **WindowsToastNotifier** displays a desktop toast on Windows systems using `win10toast`.【F:alert_core/infrastructure/notifiers/windows_toast.py†L11-L23】

### 🔧 Configuration and Thresholds
`load_thresholds()` reads a JSON file and records missing-file errors to the log store.【F:alert_core/config/loader.py†L16-L34】
`ThresholdService` wraps the `DLThresholdManager` from the data layer to manage threshold records.【F:alert_core/threshold_service.py†L7-L56】

### 🛠 Utilities
Helper functions to normalize enum inputs, resolve wallet metadata and load default thresholds.【F:alert_core/utils.py†L8-L137】

### 📦 Dependencies
- `pydantic` for data models
- `sqlite3` from the Python standard library
- `twilio` (optional) for SMS notifications
- `win10toast` (optional) for Windows toast notifications
- Internal packages: `core.locker_factory`, `core.logging`, `data` models and managers, `notifications.twilio_sms_sender`

---
