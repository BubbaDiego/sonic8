# Market Movement Patch — Codex Integration Guide

**Date:** 2025-07-28

## Repository layout assumed

```
backend/
  core/monitor_core/market_monitor.py
  services/price_sync_service.py
  routes/market.py
frontend/
  src/pages/MonitorManager.jsx
  src/components/
tests/monitor/
```

## How to apply inside Codex

1. **Checkout latest `main`** in your Codex workspace:
   ```bash
   git checkout main && git pull
   ```

2. **Apply patches**:
   ```bash
   git apply backend/core/monitor_core/market_monitor.patch
   git apply backend/services/price_sync_service.patch
   git apply backend/routes/market_latest.patch
   git apply frontend/src/patch_monitor_manager.patch
   ```

   For the new component and test file use `git add`:
   ```bash
   git add frontend/src/components/MarketMovementCard.jsx
   git add tests/monitor/test_market_movement.py
   ```

3. **Install new dependency** (Yahoo Finance):
   ```bash
   pip install yfinance
   ```

4. **Run unit tests**:
   ```bash
   pytest tests/monitor/test_market_movement.py
   ```

5. **Start dev servers** and verify:
   * Back‑end: `flask run`
   * Front‑end: `npm run dev`
   * Navigate to the dashboard and confirm the **Market Monitor (intra‑day)** card appears and live %‑moves update.

6. **Commit & push** as a new feature branch:
   ```bash
   git checkout -b feat/market-movement-monitor
   git commit -am "Add intra‑day price movement monitoring"
   git push origin feat/market-movement-monitor
   ```

7. **Open a PR** per your normal Codex workflow.

---
### Optional clean‑up

* Add a secrets entry for Yahoo Finance proxy if outbound calls are restricted.
* Configure Twilio/SMS in `market_monitor._do_work` if you need real‑time mobile alerts.