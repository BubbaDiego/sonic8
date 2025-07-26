# 📡 XCom Core Specification

> Version: `v1.2`
> Author: `CoreOps 🥷`
> Scope: Notification system for email, SMS, voice and sound alerts.
> Serves as the messaging backbone in the Cyclone 2025 architecture, triggered by Monitor and Wallet cores.

---

## 📂 Module Structure
```txt
xcom/
├── xcom_core.py                   # 🚦 Dispatches notifications
├── xcom_config_service.py         # ⚙️ Loads provider settings
├── email_service.py               # 📧 SMTP email sender
├── sms_service.py                 # 💬 SMS via carrier gateway
├── voice_service.py               # 📞 Twilio voice calls
├── sound_service.py               # 🔊 Local audio playback
├── tts_service.py                 # 🗣️ Local text-to-speech
└── check_twilio_heartbeat_service.py  # ❤️ Twilio credential check
```

### 🔧 `XComCore`
Central orchestrator that sends notifications using configured providers.

```python
XComCore(dl_sys_data_manager)
```
- Initializes `XComConfigService` with a DataLocker system manager.
- Maintains an in-memory log of dispatched messages.

**send_notification**
```python
send_notification(level, subject, body, recipient="", initiator="system", mode=None) -> dict
```
- Retrieves provider configs (`email`, `sms`, `api`).
- When `mode` is `None` it fans out based on `level` (`HIGH` => SMS+voice,
  `MEDIUM` => SMS, otherwise email).  Passing a string or list in `mode`
  explicitly selects the channels (`"voice"`, `"sms"`, `"tts"`, etc.).
- Results and errors are logged and written to the `xcom_monitor` ledger.
- Returns a dictionary of results including a `success` flag.

**get_latest_xcom_monitor_entry**
```python
get_latest_xcom_monitor_entry(data_locker) -> dict
```
- Reads the most recent `xcom_monitor` ledger row using the supplied `DataLocker`.
- Parses metadata to determine `comm_type`, `source` and a friendly timestamp.
- Used by the dashboard service to display notification status.

### 🛠️ Support Services
- **EmailService** – sends plaintext mail through an SMTP server.
- **SMSService** – first tries Twilio (`sid`, `token`, `from_number`); if those
  are missing it falls back to the legacy carrier‑gateway email method.  Supports
  `dry_run: true` for testing.
- **VoiceService** – wraps Twilio's client to place a voice call that reads the
  supplied message. The call is skipped if the provider's `enabled` flag is
  `False`. Errors are logged and no death nail is issued unless the provider
  config sets `suppress_death_on_error` to `False`.
- **TTSService** – uses `pyttsx3` to speak text locally when the TTS provider is
  enabled.
- **SoundService** – plays an MP3 file on the local system as an audible alert.
- **CheckTwilioHeartbeatService** – validates Twilio credentials and can trigger
  a test call in non-dry-run mode.

### 🧰 Configuration
`XComConfigService` resolves provider settings from the database or environment
variables. Placeholders like `${SMTP_SERVER}` fall back to corresponding
environment variables. The service returns merged dictionaries for each provider
so that `XComCore` has immediate access to required credentials such as
`SMTP_*` and `TWILIO_*` values.
 If no provider config is stored, defaults are constructed from environment values.

### 🧩 Integrations
- `system_bp` exposes routes to update XCom settings and to send test messages.
- `XComMonitor` periodically calls `send_notification` as a heartbeat.
- `DashboardService` displays the last notification via `get_latest_xcom_monitor_entry`.
- `operations_console.py` uses XComCore for manual operations and testing.
- `DeathNailService` now handles fatal errors locally; XCom escalation is
  disabled to avoid voice calls.
- Wallet and Trader cores publish events via XCom during Cyclone cycles.

### ✅ Design Notes
- Logging goes through `core.logging` with success or error emojis.
- Ledger writes include metadata like initiator, recipient and result status.
- The module keeps service classes small so other parts of the project can reuse
  them without pulling in the entire notification stack.
