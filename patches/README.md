# Sonic‑layout refactor – integration guide

## Files
| Patch file | Target | Purpose |
|------------|--------|---------|
| GlobalSettingCard.patch | `src/components/GlobalSettingCard.jsx` | Renames card to **Sonic Monitor**, removes Threshold % field, and adds 4 monitor‑enable buttons |
| MonitorManager.patch    | `src/pages/MonitorManager.jsx`         | Re‑arranges layout into two rows (Sonic + Liquid) / (Profit + Market) |
| ProfitMonitorCard.patch | `src/components/ProfitMonitorCard.jsx` | Removes individual enable/disable switch (now controlled by Sonic Monitor) |

## Apply
```bash
cd <your‑repo>
git apply sonic_layout_patches/GlobalSettingCard.patch
git apply sonic_layout_patches/MonitorManager.patch
git apply sonic_layout_patches/ProfitMonitorCard.patch
```

or, to apply all at once:

```bash
unzip ./sonic_layout_patches.zip -d /tmp/sonic_layout_patches
git apply /tmp/sonic_layout_patches/*.patch
```

## Notes for backend / Codex
* The **Sonic Monitor** card now toggles which monitors participate in the Sonic loop.  
  Four new boolean fields are written into the same payload as `threshold_percent` previously was (which has been removed):

  | field | default |
  |-------|---------|
  | `enabled_sonic`  | `true` |
  | `enabled_liquid` | `true` |
  | `enabled_profit` | `true` |
  | `enabled_market` | `true` |

* `POST /api/monitor-settings/sonic` should be extended to accept/return these booleans.

* The front‑end continues to send `interval_seconds` alongside the new toggles.

* No other API contracts have changed.

---
Generated 2025-07-29T18:33:09.529008 UTC
