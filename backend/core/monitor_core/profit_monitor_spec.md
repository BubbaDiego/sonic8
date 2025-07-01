📈 Profit Monitor Specification
Version: v1.1
Author: CoreOps 🥷
Scope: Profit monitoring, UI integration, and notifications
System: Cyclone Engine, Monitor Core, XCom, Front-end Title Bar
Architecture: Runs each cycle within Cyclone 2025 and records events to DataLocker.

🔖 Overview
The ProfitMonitor component monitors accumulated profit across active positions. When accumulated profit exceeds a predefined threshold (currently $50), the system:

Sends a notification via XCom.

Updates the UI profit badge displayed in the application's title bar.

This ensures imme[sonic_dashboard.html](../templates/sonic_dashboard.html)diate and consistent notification of profit harvest opportunities.

📂 Module Structure
bash
Copy
Edit
monitor/
├── profit_monitor.py        # 🆕 Monitors profit and triggers alerts
├── monitor_core.py          # 📝 Registers ProfitMonitor
├── base_monitor.py          # 📋 Provides BaseMonitor structure
xcom/
├── xcom_core.py             # 🔔 Sends notifications
├── voice_service.py         # 📞 Handles voice alerts (Twilio)
frontend/
├── templates/sonic_header.html # 🎨 Displays profit badge
├── static/css/sonic_header.css # 💅 Animates profit badge
├── static/js/sonic_header.js   # 📦 Manages profit badge interactions
🚨 Profit Monitor (profit_monitor.py)
Responsibilities:

Aggregates profits (pnl_after_fees_usd) from all active positions.

Triggers XCom notifications when threshold is surpassed.

Updates backend system vars for UI profit badge synchronization.

Core Logic:

Threshold: $50 (configurable).
Default limits are seeded via `AlertThresholdSeeder`:
  - `Profit` → 10 (low), 25 (medium), 50 (high)
  - `TotalProfit` → 25 (low), 50 (medium), 75 (high)

Notification Level: HIGH (SMS, voice, sound).

Profit data sourced directly from position data (PositionCore via DLPositionManager).

Integration points:

PositionCore: Fetches positions.

DataLocker (DL): Persists `profit_badge_value` in system vars.

XComCore: Sends configured notifications.

📡 XCom Integration (xcom_core.py)
Existing Capabilities:

Sends notifications at configured levels:

HIGH: SMS, voice, sound

MEDIUM: SMS

LOW: Email

Profit Monitor usage:

Current implementation sends HIGH alerts, triggering SMS, voice and sound notifications when profit thresholds are hit.

Uses existing Twilio integration (voice_service.py) if notification level changes.

🎨 Frontend Integration
📌 Header Partial (sonic_header.html)
Displays dynamic profit badge aligned with backend profit state.

html
Copy
Edit
{% if profit_badge_value %}
  <span class="profit-badge badge text-bg-success ms-2">{{ profit_badge_value }}</span>
{% endif %}
Directly pulls the latest value from `DataLocker.system` (profit_badge_value) updated by ProfitMonitor.

💅 CSS (sonic_header.css)
Animates badge clearly (bounce, float, pulse) for attention.

📦 JavaScript (sonic_header.js)
Handles user interactions (dismissal/fade-out) on badge click.

Triggers animation effects (bounceIn, pulseGlow).

🛠️ Component Interaction Flow
Profit Notification Cycle:
scss
Copy
Edit
ProfitMonitor checks accumulated profit 
  ├─▶ [profit >= $50?] ──▶ YES ──▶ Update profit_badge_value (DataLocker.system)
  │                             ├─▶ Send HIGH notification (XComCore)
  │                             └─▶ UI updates badge display (Title Bar)
  └─▶ NO ──▶ Clears profit_badge_value
            └─▶ UI removes badge display
🗃️ Impacted Files & Components
✅ New Files
File	Description
profit_monitor.py	Profit monitoring logic and alerting

✅ Modified Files
File	Impact / Change
monitor_core.py	Registers the new ProfitMonitor
xcom_core.py	Invoked by ProfitMonitor for notifications
voice_service.py	Potentially invoked if notification escalates
sonic_header.html	Displays profit badge
sonic_header.css	Animates badge display
sonic_header.js	Handles badge dismissal

✅ Dependent Existing Files
File	Reason for dependency
position_core.py	Provides active position data
dl_positions.py	Holds position PnL data
dl_portfolio.py	Aggregates and snapshots portfolio data

⚙️ Configuration & Settings
Setting	Type	Default	Description
profit_threshold	Float	$50.00	Profit amount for triggering alerts
notification_level	String	MEDIUM	XCom notification intensity

These settings can be adjusted within profit_monitor.py or moved into dynamic configuration through DataLocker system variables.

🧪 Testing and Validation
Verify profit badge aligns exactly with ProfitMonitor alerts.

Ensure XCom notifications trigger accurately.

Validate threshold logic under different scenarios (below, equal to, and above the threshold).

✅ Checklist for Final Implementation
Deploy profit_monitor.py to production environment.

Ensure frontend (sonic_header.html, sonic_header.css, sonic_header.js) correctly reflects backend states.

Validate notification delivery via XCom integrations (SMS/Voice).

Monitor logs and ledger entries for ProfitMonitor operations.

📌 Final Notes & Recommendations
For dynamic adjustment of thresholds and notification settings, consider moving configuration variables to the database/system settings (DataLocker.system_vars).

Ensure regular monitoring and review of profit threshold effectiveness.

Your implementation is now clearly defined, structured, and integrated across frontend and backend systems.

📂 Files for Check-in:
Ensure the following files are checked in and available:

 monitor/profit_monitor.py

 monitor/monitor_core.py

 xcom/xcom_core.py

 xcom/voice_service.py

 frontend/templates/sonic_header.html

frontend/static/css/sonic_header.css

frontend/static/js/sonic_header.js
 
DataLocker tables store profit snapshots and drive threshold checks each cycle.

