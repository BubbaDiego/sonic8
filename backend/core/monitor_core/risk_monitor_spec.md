📈 Risk Monitor Specification
Version: v1.1
Author: CoreOps 🥷
Scope: Risk monitoring, UI integration and notifications
System: Cyclone Engine, Monitor Core, XCom, Front-end Title Bar

🔖 Overview
The `RiskMonitor` component observes active positions to detect when a
position's heat index or travel percent surpasses configured thresholds. When risk is
identified it updates a risk badge in the UI and dispatches a
notification via `XComCore`.

📂 Module Structure
```txt
monitor/
├── risk_monitor.py         # 🆕 Monitors risk and triggers alerts
├── monitor_core.py         # 📝 Registers RiskMonitor
├── base_monitor.py         # 📋 Provides BaseMonitor structure
xcom/
├── xcom_core.py            # 🔔 Sends notifications
frontend/
├── templates/sonic_header.html # 🎨 Displays risk badge
├── static/css/sonic_header.css # 💅 Animates risk badge
├── static/js/sonic_header.js   # 📦 Manages risk badge interactions
```

🚨 Risk Monitor (`risk_monitor.py`)
Responsibilities:
- Fetch active positions from `PositionCore`.
- Evaluate each position's heat index.
- Evaluate each position's travel percent.
- Trigger `XComCore` notifications when the heat index crosses the
  threshold.
- Trigger `XComCore` notifications when the travel percent crosses the
  threshold.
- Persist a `risk_badge_value` using `DataLocker.system.set_var` so that
  the UI stays in sync.
- Persist a `travel_risk_badge_value` for travel percent.

Core Logic:
- **Threshold**: Heat index limit (defaults to 50, configurable via
  `ThresholdService`).
- **Travel Threshold**: Travel percent limit (defaults to 50, configurable via
  `ThresholdService`).
- **Notification Level**: `HIGH` – sends SMS, email and plays a sound.

Integration Points:
- `PositionCore` – source of active positions.
- `DataLocker` – stores the badge value in system vars.
- `XComCore` – dispatches notifications.

📡 XCom Integration (`xcom_core.py`)
`RiskMonitor` calls `send_notification` with level `HIGH` which
triggers SMS, voice and sound alerts when available.

🎨 Frontend Integration
📌 Title Bar HTML (`sonic_header.html`)
```html
{% if risk_badge_value %}
  <span class="risk-badge badge text-bg-danger ms-2">{{ risk_badge_value }}</span>
{% endif %}
```
💅 CSS (`sonic_header.css`)
Adds pulse/glow animations similar to the profit badge.

📦 JavaScript (`sonic_header.js`)
Handles user dismissal by fading out the badge on click and triggers the
animation when the badge appears.

🛠️ Component Interaction Flow
```
RiskMonitor checks positions' heat index
  ├─▶ [heat index ≥ threshold?] ──▶ YES ──▶ Update risk_badge_value (DataLocker)
  │                                  ├─▶ Send notification (XComCore)
  │                                  └─▶ UI updates badge display (Title Bar)
  └─▶ NO ──▶ Clears risk_badge_value
            └─▶ UI removes badge display
```

🗃️ Impacted Files & Components
✅ **New Files**
- `risk_monitor.py` – Risk monitoring logic and alerting.

✅ **Modified Files**
- `monitor_core.py` – Registers the new `RiskMonitor`.
- `xcom_core.py` – Invoked by `RiskMonitor` for notifications.
- `templates/sonic_header.html` – Displays risk badge.
- `static/css/sonic_header.css` – Animates badge display.
- `static/js/sonic_header.js` – Handles badge dismissal.

✅ **Dependent Existing Files**
- `positions/position_core.py` – Provides active position data.
- `data/dl_positions.py` – Holds position heat data.

⚙️ Configuration & Settings
Setting | Type | Default | Description
---|---|---|---
`heat_index_threshold` | Float | 50.0 | Heat index threshold that triggers alerts.
`travel_percent_threshold` | Float | 50.0 | Travel percent threshold that triggers alerts.
`notification_level` | String | HIGH | XCom notification intensity.

🖥️ UI Configuration
Risk threshold values can be modified on the **Alert Thresholds** page in the
new **Risk Monitor** section located just below the Profit Monitor card.

🧪 Testing and Validation
- Confirm the risk badge updates when positions exceed the threshold.
- Confirm the travel percent badge updates when positions exceed the threshold.
- Verify `XComCore` notifications are dispatched.
- Test cases for positions below, at and above the threshold.

✅ Checklist for Final Implementation
- Deploy `risk_monitor.py`.
- Integrate frontend changes (`sonic_header.html`, `sonic_header.css`, `sonic_header.js`).
- Validate notifications and ledger entries.

📌 Final Notes & Recommendations
Move threshold settings into the database via
`DataLocker.system.set_var` for dynamic updates and periodically review
threshold effectiveness.
