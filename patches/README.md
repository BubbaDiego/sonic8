# 2×2 Layout — width tweak & disabled‑state visuals

## Summary
* **First column width reduced by 25 %** (`600 → 450 px`) via `COLUMN_A_WIDTH` constant in *MonitorManager.jsx*.
* Removed per‑card enable/disable switches from **Liquidation** and **Profit** cards.
* Cards now receive a `disabled` prop; when `true` they render at 40 % opacity and ignore pointer events (gives a greyed‑out look).
* `MonitorManager.jsx` passes the correct disabled flags derived from the Sonic Monitor toggles.

## Patches
| Patch | Target |
|-------|--------|
| MonitorManager.patch | `src/pages/MonitorManager.jsx` |
| LiquidationMonitorCard.patch | `src/components/LiquidationMonitorCard.jsx` |
| ProfitMonitorCard.patch | `src/components/ProfitMonitorCard.jsx` |
| MarketMonitorCard.patch | `src/components/MarketMonitorCard.jsx` |

## Apply
```bash
unzip sonic_disable_visuals.zip -d /tmp/patches
cd <repo>
git apply /tmp/patches/*.patch
```

Adjust `COLUMN_A_WIDTH` anytime to fine‑tune the left‑hand column size.

Generated 2025-07-29 23:20 UTC
