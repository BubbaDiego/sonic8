# 🛰️ Monitor Core Specification

> Version: `v1.3`
> Author: `CoreOps 🥷`
> Scope: Monitor orchestrator and supporting monitors.
> Runs within Cyclone Engine cycles, persisting output to DataLocker and routing notifications through XCom.

---

## 📂 Module Structure
[monitor_core.py](monitor_core.py)
```txt
monitor/
├── monitor_core.py         # 🚦 Registers and runs monitors
├── base_monitor.py         # 🔧 Shared run_cycle/ledger wrapper
├── monitor_registry.py     # 📇 Holds monitor instances
├── price_monitor.py        # 💰 Fetches prices from APIs
├── position_monitor.py     # 📈 Syncs and enriches positions
├── operations_monitor.py   # 🧪 Startup POST tests and health checks
├── xcom_monitor.py        # 📡 Sends a lightweight XCom notification
├── twilio_monitor.py      # 🔔 Verifies Twilio credentials
├── latency_monitor.py      # ⏱️ External API latency checker
├── profit_monitor.py       # 💰 Triggers alerts on accumulated profit
├── risk_monitor.py         # 🔥 Detects high heat index on positions
├── ledger_service.py       # 🧾 JSON ledger utilities
├── monitor_api.py          # 🌐 Flask API endpoints
└── sonic_monitor.py        # ❤️ Background cycle runner
```

### 🚦 MonitorCore
Central controller for executing registered monitors.

```python
MonitorCore(registry: MonitorRegistry | None = None)
```
- If `registry` is not provided, a new one is created and default monitors are registered (`PriceMonitor`, `PositionMonitor`, `OperationsMonitor`, `XComMonitor`, `TwilioMonitor`, `ProfitMonitor`, `RiskMonitor`).
- **RiskMonitor** – monitors heat index and dispatches HIGH level alerts.

**Methods**
- `run_all()` – iterate and run every monitor in the registry, logging success or failure.
- `run_by_name(name)` – run a single monitor by its key if present.

### 🧩 Monitor Implementations
- **BaseMonitor** – provides `run_cycle()` wrapper that records results in the database ledger.
- **PriceMonitor** – fetches BTC/ETH/SOL prices via `MonitorService`.
- **PositionMonitor** – syncs positions from Jupiter and logs summary metrics.
- **OperationsMonitor** – runs POST tests on startup and stores results. The

  default test glob is `test_core/tests/test_*.py` and missing

  files are logged as a warning.
- **XComMonitor** – sends a lightweight XCom notification as a heartbeat.
- **TwilioMonitor** – verifies Twilio credentials and records the status.
- **ProfitMonitor** – tracks accumulated profit and triggers alerts.
- **RiskMonitor** – monitors heat index and dispatches HIGH level alerts.
- **LatencyMonitor** – optional HTTP latency checker for third-party services.

### 🌐 API & Background Runner
- `monitor_api.py` exposes REST endpoints to trigger monitors individually or all at once.
- `sonic_monitor.py` runs periodic cycles using `Cyclone` and records a heartbeat in the database. It also triggers `PriceMonitor`, `ProfitMonitor`, and `RiskMonitor` after each Cyclone cycle.
### ✅ Design Notes
- Monitors write a summary entry to the ledger table via `DataLocker.ledger`.
- Registration through `MonitorRegistry` keeps monitor setup centralized.
- Execution paths include CLI scripts, Flask API, and long‑running background loops.

### 📊 Profit & Risk Thresholds
- **ProfitMonitor** aggregates profit across active positions using `ThresholdService`.
  When either the single-position or portfolio limit is exceeded it updates
  `profit_badge_value` and sends a **HIGH** notification via `XComCore`.
- **RiskMonitor** checks the heat index of active positions. The low threshold
  controls the UI badge while the high threshold triggers a **HIGH** alert
  (SMS, voice call and sound) using `XComCore`.
- A shared *snooze timer* can temporarily suppress Profit and Risk alerts.
  The current duration is adjusted in the Sonic header and persisted via the
  `/api/monitor/snooze` and `/api/monitor/snooze/clear` endpoints.

### 🔔 Notification Levels
`XComCore.send_notification()` loads provider settings and dispatches based on the level:
- **HIGH** – SMS + voice call + optional sound
- **MEDIUM** – SMS only
- **LOW** – email only
