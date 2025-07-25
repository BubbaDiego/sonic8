# 💹 Market Core Specification

> Version: `v1.0`
> Author: `CoreOps 🥷`
> Scope: Synchronize market data and expose services for other cores.

---

## 📂 Module Structure
```txt
market_core/
├── price_sync_service.py  # 🔄 Fetches prices from external APIs
```

### 🔄 `PriceSyncService`
Central utility responsible for pulling current prices and storing them in the database.

```python
PriceSyncService(data_locker)
```
- `data_locker` – instance of `DataLocker` used for database writes.

#### `run_full_price_sync()`
```python
run_full_price_sync(source="user") -> dict
```
- Fetches BTC, ETH and SOL prices via `MonitorService.fetch_prices()`.
- Inserts each price using `DataLocker.insert_or_update_price`.
- Records a ledger entry through `DLMonitorLedgerManager`.
- Returns a result dictionary including `fetched_count`, `assets`, `success` and `timestamp`.
- On failure, `error` is populated and the ledger entry status is `Error`.

### 🧩 Interactions
- **MonitorCore** – `PriceMonitor` invokes this service during monitor cycles.
- **CycloneEngine** – `run_market_updates()` offloads execution to this service.
- **Learning DB** – price ticks are logged via `log_learning_event` when available.
- **PositionsC[monitor_api_adapter.py](../../routes/monitor_api_adapter.py)ore** – enrichment services rely on the stored prices for calculations.

### ↔️ Expected Inputs & Outputs
- **Input**: a `DataLocker` instance and optional `source` string.
- **Output**: dictionary showing fetch count, list of assets and success status, e.g.
  ```json
  {
      "fetched_count": 3,
      "assets": ["BTC", "ETH", "SOL"],
      "success": true,
      "timestamp": "2025-06-17T12:00:00Z"
  }
  ```

### ✅ Design Notes
- Uses `MonitorService` to reach out to CoinGecko and therefore depends on network availability.
- Ledger writes ensure monitor history persists even when price updates fail.
- Other cores query the latest prices via `DataLocker.prices`.
