# 🛰️ Monitor Core Specification
Version: **v2.0–draft**  
Generated: 2025-07-25T03:56:28.233996 UTC  

> **Scope** – Complete functional and technical documentation for the *Monitor Core* subsystem, including its orchestrator (`MonitorCore`), background runner (`sonic_monitor`), individual monitors, data‑layer helpers, public API, CLI console, persistence models, configuration schemes, and alerting pipelines.

---
## Table of Contents
1. [High‑Level Architecture](#architecture)
2. [Database & Persistence Models](#db)
3. [Core Controller – `MonitorCore`](#monitorcore)
4. [Heartbeat & Orchestration – `sonic_monitor`](#sonic)
5. [Monitor Catalogue](#monitors)
6. [Supporting Utilities](#utils)
7. [Execution Interfaces (API & CLI)](#interfaces)
8. [Configuration & Scheduling](#config)
9. [Alerting & Notification Flow](#alerting)
10. [Ledger & Health Reporting](#ledger)
11. [Security & Resilience Notes](#resilience)
12. [Potential Improvements](#improvements)

---
<a name="architecture"></a>
## 1  High‑Level Architecture

```text
┌───────────────┐
│  API Server   │  /monitor/<name>  ─┐
└───────────────┘                   │
                                    │
┌───────────────┐                   │
│  CLI Console  │  monitor_core.run │
└───────────────┘                   │
                                    ▼
                           ┌──────────────────┐
                           │  MonitorCore     │
                           │  (Registry +     │
                           │   Controller)    │
                           └──────────────────┘
            ┌───────────────────────────────────────────────────┐
            │               Registered Monitors                │
            │  price | position | risk | profit | … | sonic    │
            └───────────────────────────────────────────────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │   DataLocker     │
                           │  (SQLite DB)     │
                           └──────────────────┘
               │ DB tables │        │ JSON Ledgers │
               ▼                       ▼
      monitor_ledger, …        *.json (legacy)
```

* **MonitorCore** is the synchronous orchestrator; it enumerates monitors from a `MonitorRegistry`, executes them, and writes results to `monitor_ledger`. fileciteturn0file26  
* **sonic_monitor** is an **async** daemon that *wraps* a full *Cyclone* data‑pipeline pass and then runs select monitors every *N* seconds, where *N* is live‑tunable via the `monitor_heartbeat` table. citeturn0file15

---
<a name="db"></a>
## 2  Database & Persistence Models

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `monitor_ledger` | Canonical log of every monitor run. | `id` (PK), `monitor_name`, `timestamp`, `status`, `metadata` | fileciteturn0file18 |
| `monitor_heartbeat` | Live cadence & liveness tracker for `sonic_monitor`. | `monitor_name`(PK), `last_run`, `interval_seconds` | citeturn0file15 |
| `positions` | Active trading positions & metadata. | `id`(PK), `asset_type`, `size`, `leverage`, … | fileciteturn0file0 |
| `prices` | Latest spot prices per asset. | `asset_type`, `current_price`, `last_update_time` | fileciteturn0file1 |
| `alert_thresholds` | Per‑metric threshold triples (low/med/high). | `alert_type`, `alert_class`, `condition` | fileciteturn0file2 |
| `system_vars` | Global KV store for UI & engine state; MarketMonitor configuration persists here. | `theme_mode`, `…` | fileciteturn0file3 |

> **JSON Ledgers** (`<monitor>_ledger.json`) are still produced for back‑compat but are **non‑authoritative** – migration to DB ledger is ongoing.

---
<a name="monitorcore"></a>
## 3  Core Controller – `MonitorCore`

* *Auto‑registration* – when instantiated without an explicit registry the class registers **eight** default monitors plus profit, risk and liquidation. fileciteturn0file26  
* `run_all()` iterates sequentially; `run_by_name()` provides targeted execution.  
* The method `get_status_snapshot()` hydra‑reads the ledger via `DLMonitorLedgerManager` and emits a `MonitorStatus` payload for dashboards. citeturn0file18

Lifecycle:

1. Console/API/daemon invokes `run_*`  
2. Each `BaseMonitor.run_cycle()` wraps `_do_work()`, captures exceptions, determines `Success|Error` heuristically, and pushes a ledger row. fileciteturn0file72  
3. Dashboards poll `/status` (GraphQL not yet implemented) and translate the `MonitorStatus` model into UI badges.

---
<a name="sonic"></a>
## 4  Heartbeat & Orchestration – `sonic_monitor`

| Feature | Detail |
|---------|--------|
| **Execution** | Infinite `while True` loop (+ graceful `KeyboardInterrupt`) running inside its own event loop. |
| **Interval** | Pulled fresh from `monitor_heartbeat.interval_seconds` *each* cycle; default 60 s. |
| **Pipeline** | `Cyclone.run_cycle()` ⇒ `price_monitor` ⇒ `profit_monitor` ⇒ `liquid_monitor` (risk monitor optional toggle). |
| **Alert V2** | (disabled) classic monitors only – no `AlertOrchestrator` invocation. |
| **Ledger & HB** | Writes success/error to `monitor_ledger` and updates heartbeat row every loop. |

This design makes **Sonic Monitor** the single source of truth for:

* Cyclone‑trigger cadence.  
* Monitor health baseline (every loop prints a heartbeat row).  
* Alert evaluation latency.

---
<a name="monitors"></a>
## 5  Monitor Catalogue

| Key | Class | Core Logic | Threshold/Badge | Notifications |
|-----|-------|-----------|-----------------|---------------|
| `price_monitor` | `PriceMonitor` | CoinGecko + Yahoo Finance fetch, persists to `prices`. fileciteturn0file12 | N/A | None |
| `position_monitor` | `PositionMonitor` | Syncs Jupiter positions via `PositionCore`. fileciteturn0file63 | Badge: active count | None |
| `profit_monitor` | `ProfitMonitor` | Aggregates realised PnL, compares versus `ThresholdService`. fileciteturn0file13 | yes | XCom (HIGH) |
| `risk_monitor` | `RiskMonitor` | Heat index & travel %, env snooze. fileciteturn0file14 | yes | XCom + sound |
| `liquid_monitor` | `LiquidationMonitor` | Per‑asset % distance → alert, nested notifications map. fileciteturn0file75 | yes | voice/SMS/system sound |
| `market_monitor` | `MarketMonitor` | Price %‑move triggers + blast‑radius calc. |  | Ledger only |
| `operations_monitor` | `OperationsMonitor` | POST tests + ChatGPT/Twilio ping. fileciteturn0file62 |  ‑ | Ledger only |
| `latency_monitor` | `LatencyMonitor` | Simple HTTP ping to CoinGecko/Jupiter. fileciteturn0file73 |  ‑ | Ledger only |
| `xcom_monitor` | `XComMonitor` | Sends low‑level ping via XComCore. fileciteturn0file68 |  ‑ | XCom (LOW) |
| `twilio_monitor` | `TwilioMonitor` | Verifies provider creds. fileciteturn0file69 |  ‑ | Ledger only |
| `market_monitor` | `MarketMonitor` | Price %‑move triggers + blast‑radius calc. |  | Ledger only |
| `sonic_monitor` | (see §4) | Orchestrator loop. | HB Row | Slack via MonitorCore |

---
<a name="utils"></a>
## 6  Supporting Utilities

* **DL Managers** – typed CRUD helpers for positions, prices, thresholds, etc. These enforce schema and emit helpful debug logs. Examples: `DLPositionManager`, `DLPriceManager`. citeturn0file0turn0file1  
* **TimerConfig** – lightweight JSON config with optimistic‑lock retry wrapper. fileciteturn0file9  
* **LedgerService (JSON)** – legacy append‑only text ledgers kept for ops audit. fileciteturn0file74  
* **MonitorService** – shared helpers for S&P fetch, POST tests. citeturn0file28  

---
<a name="interfaces"></a>
## 7  Execution Interfaces

### 7.1  Flask API – `monitor_api.py`
* `GET /monitors` – list registered keys.  
* `POST /monitor/<name>` – run one monitor.  
* `POST /monitor/all` – run registry sequentially. fileciteturn0file24  

### 7.2  CLI Console – `monitor_console.py`
Interactive curses‑style TUI offering run/select/all, ledger freshness, and test suite trigger. fileciteturn0file77  

---
<a name="config"></a>
## 8  Configuration & Scheduling

| Mechanism | Use | Example |
|-----------|-----|---------|
| **TimerConfig JSON** | Centralised per‑monitor interval overrides. | `config/timer_config.json` |
| **Environment vars** | Quick overrides (e.g., `LIQ_MON_THRESHOLD_PERCENT`). citeturn0file75 | `export LIQ_MON_SNOOZE_SECONDS=900` |
| **system_vars** table | UI theme, snooze timers, badge values. | `risk_badge_value`, `profit_badge_value` |

---
<a name="alerting"></a>
## 9  Alerting & Notification Flow

```
Monitor → (Threshold Hit) → XComCore → ProviderMap → Twilio/SMTP
                                         ↘
                      AlertOrchestrator (v2) ← metric adaptor ← Sonic loop
```
* **Legacy flow** – monitors call `XComCore.send_notification(level, …)` which fans out to provider drivers based on the level map (LOW=Email, HIGH=SMS+Voice). fileciteturn0file13  
* **Alert V2** – rule‑based engine evaluated inside Sonic each cycle; outputs Slack events today, with provider hooks pluggable. citeturn0file15  

---
<a name="ledger"></a>
## 10  Ledger & Health Reporting

* **DLMonitorLedgerManager** is the authoritative writer/reader for `monitor_ledger`. It can derive a `MonitorStatus` snapshot used by dashboards for coloured health badges. fileciteturn0file18  
* `monitor_status.py` defines enum types (`MonitorHealth`) so downstream services avoid magic strings. fileciteturn0file56  

---
<a name="resilience"></a>
## 11  Security & Resilience Notes

* Every `BaseMonitor` catch‑all logs exceptions and still records an **Error** row, preventing silent failures. citeturn0file72  
* `sonic_monitor` continues looping after any downstream exception; it also prints live monitor status to the log for tailing. citeturn0file15  
* DB corruption detection & self‑healing implemented in `DLPositionManager.get_all_positions()`. citeturn0file0  

---
<a name="improvements"></a>
## 12  Potential Improvements
[market_core_spec.md](../market_core/market_core_spec.md)
1. **Namespace Consolidation** – deprecate the flat `monitor.*` package and keep only `backend.core.monitor_core.*` to eliminate duplicate classes and import confusion.  
2. **Unified Ledger** – remove `LedgerService` once all dashboards migrate to DB‑backed `monitor_ledger`; write a migration script to backfill legacy JSON lines.  
3. **Snooze Strategy Mixin** – extract duplicated `should_notify()` logic (profit & risk) into a reusable mix‑in with auto‑expiry persisted to `system_vars`.  
4. **Plugin‑Based Monitor Loading** – adopt `entry_points` or YAML manifest so new monitors can be added without code changes or registry edits.  
5. **Cyclone Back‑pressure** – add a semaphore/lock so `sonic_monitor` delays if the previous Cyclone run exceeds its interval instead of overlapping.  
6. **Alert V2 Expansion** – move all monitor thresholds into V2 rules to consolidate alert logic; gradually retire XCom‑level hard‑wiring.  
7. **Schema‑first Docs** – auto‑generate sections from `pydantic` models and jsonschema (e.g., `alert_thresholds`) to keep docs consistent.  
8. **Test Coverage** – integrate `pytest` coverage artifact into OperationsMonitor POST suite and fail the CI when < 85%.  
9. **Container Healthcheck** – create a `/healthz` Flask route that runs `get_status_snapshot()` for K8s readiness probes.  
10. **CI‑driven DB Migrations** – formalise DDL in Alembic and run migrations in start‑up script rather than ad‑hoc `CREATE TABLE IF NOT EXISTS` scattered in code.

---
**End of Spec**
