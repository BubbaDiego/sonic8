# Learning Data Subsystem — Specification v0.3

**Author:** CoreOps 🥷

**Updated:** 2025-06-17

**Applies to:** Cyclone Engine, PositionCore, HedgeManager, PriceMonitor, AlertCore, TraderCore

---

## 1. Goal

Build an isolated, append-only SQLite database (`learning.db`) recording detailed telemetry for positions, hedges, market prices, alerts, and trader snapshots. Data fuels analytics to identify patterns preceding costly liquidations and hedge failures without impacting production performance.

---

## 2. Rationale

* Prevent costly liquidations/hedge errors.
* Production DB optimized for live trading, not analytics.
* Separate telemetry DB minimizes latency and supports analytics.

---

## 3. Non-functional Requirements

| Item                 | Specification                                              |
| -------------------- | ---------------------------------------------------------- |
| **Sampling cadence** | Configurable, default = **60 s** (`LEARNING_SAMPLING_SEC`) |
| **Isolation**        | Default path: `~/.app/learning.db` (`LEARNING_DB_PATH`) |
| **Retention**        | Indefinite (no TTL policy for v0.2)                        |
| **Prod impact**      | ≤ 3 ms per insert (WAL mode)                               |
| **Thread safety**    | Singleton (`check_same_thread=False`)                      |
| **Schema evolution** | Allow non-breaking migrations (`ALTER TABLE … ADD COLUMN`) |

---

## 4. Schema Definition

Maintained and executed by `LearningDataLocker.initialize_database()`:

```sql
CREATE TABLE IF NOT EXISTS position_events (
    event_id TEXT PRIMARY KEY,
    position_id TEXT,
    trader_name TEXT,
    ts TEXT,
    state TEXT,
    travel_percent REAL,
    liquidation_distance REAL,
    heat_index REAL,
    value REAL,
    leverage REAL,
    pnl_after_fees REAL,
    is_hedged INTEGER,
    alert_level TEXT
);

CREATE TABLE IF NOT EXISTS hedge_events (
    event_id TEXT PRIMARY KEY,
    hedge_id TEXT,
    trader_name TEXT,
    ts TEXT,
    total_long_sz REAL,
    total_short_sz REAL,
    hedge_ratio REAL,
    delta REAL,
    total_heat_index REAL
);

CREATE TABLE IF NOT EXISTS price_ticks (
    tick_id TEXT PRIMARY KEY,
    asset_type TEXT,
    ts TEXT,
    price REAL
);

CREATE TABLE IF NOT EXISTS alert_events (
    event_id TEXT PRIMARY KEY,
    alert_id TEXT,
    trader_name TEXT,
    ts TEXT,
    alert_type TEXT,
    level TEXT,
    evaluated_value REAL
);

CREATE TABLE IF NOT EXISTS trader_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    trader_name TEXT,
    ts TEXT,
    wallet_balance REAL,
    portfolio_value REAL,
    heat_index REAL,
    mood TEXT,
    strategy_json TEXT
);

CREATE TABLE IF NOT EXISTS transaction_events (
    event_id           TEXT PRIMARY KEY,
    order_id           TEXT,
    position_id        TEXT,
    trader_name        TEXT,
    ts                 TEXT,
    asset_type         TEXT,
    side               TEXT,
    size               REAL,
    price              REAL,
    fees               REAL,
    pnl_estimated      REAL,
    classification     TEXT,
    pre_value          REAL,
    post_value         REAL,
    delta_value        REAL,
    notes              TEXT
);

-- Placeholder: future `trader_profiles` table may aggregate statistics per trader.
```

*ISO 8601 timestamps; Boolean values stored as integers (0/1).*

---

## 5. Configuration

Explicit database paths via `.env`:

```ini
MOTHER_DB_PATH = C:\alpha4\data\mother_brain.db
LEARNING_DB_PATH = ~/.app/learning.db
LEARNING_SAMPLING_SEC = 60
```

---

## 6. Core Classes

### 6.1 LearningDataLocker

* Singleton database manager pointing explicitly to `LEARNING_DB_PATH`.
* Method: `initialize_database()` to execute DDL schema setup.

### 6.2 LearningEventLogger

* Function:

```python
log_learning_event(table: str, payload: dict) -> None
```

* Writes events to database with graceful error logging.

---

## 7. Integration Points

* `PositionEnrichmentService.enrich()` (`state="ENRICH"`)
* `PositionSyncService.update_jupiter_positions()` (`state="IMPORT"`)
* `HedgeManager.get_hedges()` (Hedge data)
* `PriceSyncService.run_full_price_sync()` (Price ticks)
* `AlertEvaluationService.evaluate()` (Alerts)
* `CycloneEngine.run_cycle()` (Trader snapshots)

Integration example:

```python
from learning_database.learning_event_logger import log_learning_event
log_learning_event("position_events", payload_dict)
```

---

## 8. Database User Interface

A Flask-based web UI is provided:

### Endpoints

* `GET /sonic_labs/position_events`
* `GET /api/metrics/profit`
* `GET /api/metrics/heat_series`
* `GET /api/transaction_events`
* `GET /api/trader_performance`

### Features

* Displays the latest 50 `position_events` and recent `transaction_events`.
* Sortable columns: Timestamp, Trader, State, Value, Leverage, Heat Index, Liquidation Distance, Hedged status, Alert Level.
* Charts for profit and heat metrics (updated via WebSocket).
* Extendable to future analytics visualization and filtering enhancements.

---

## 9. Console Management Application

Interactive Python CLI (`learning_db_app.py`) for direct DB management:

### Features

* Initialize database schema
* Populate test data
* Clear database contents
* View contents of database tables
* Reconstruct transactions from position history

### Usage

```bash
python learning_database/learning_db_app.py
```

You can also launch this tool from the **Database Utilities** menu in
`launch_pad.py`.

---

## 10. Error Handling

* Errors are logged (`logs/learning_db_failed_inserts.log`)
* Never interrupts critical trading workflows

---

## 11. Test Plan (v0.2)

1. **Unit Tests:**

   * SQLite in-memory database.
2. **Integration Tests:**

   * Verify data persistence via Flask UI.
3. **Load Tests:**

   * Verify high-throughput WAL performance.

---

## 12. Deliverables

* Updated files:
[launch_pad.py](../../launch_pad.py)
  * `learning_database/SPEC.md`
  * `learning_database/learning_data_locker.py`
  * `learning_event_logger.py`
  * Flask Blueprint (`sonic_labs_bp.py`)
  * Console app (`learning_db_app.py`)

---

## 13. Future Enhancements

* Automated export to Parquet
* Configurable retention and pruning policies
* PostgreSQL compatibility for analytics clusters
* Advanced visualization dashboards for real-time analytics
* Trader profile data analysis (placeholder for future design)

---
