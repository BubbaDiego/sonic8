
# ConsoleLogger v3 – Integration Specification

**Version tag**: `v3.0.0` – generated on 2025-06-28T23:56:19

This document describes how to initialise and use the upgraded `console_logger.py`
shipped alongside it.  It supersedes the v2 interface from the original file
(see citation fileciteturn0file0).

---
## 1. Installation

```bash
pip install rich          # optional, for coloured output
```

No hard dependency beyond the Python 3.9–3.12 standard library.
If `rich` is absent the logger falls back to plain ANSI.

---
## 2. Quick‑start

```python
from console_logger import ConsoleLogger as Log

Log.set_level("DEBUG")           # or use ENV:  LOG_LEVEL=DEBUG python sonic_backend_app.py
Log.success("Service started")

Log.add_sink(lambda ev: open("app.log","a").write(json.dumps(ev)+"\n"))

try:
    ...
except Exception as exc:
    Log.exception(exc, "Uncaught error")
```

---
## 3. Environment variables

| Variable          | Purpose                                  | Example  |
|-------------------|------------------------------------------|----------|
| `LOG_LEVEL`       | Default minimum level                    | `INFO`   |
| `LOG_FORMAT`      | Set to `json` for JSON‑only output       | `json`   |
| `LOG_JSON`        | Legacy alias for `LOG_FORMAT=json`       | `1`      |
| `LOG_NO_EMOJI`    | Strip emoji from console output          | `1`      |

---
## 4. Extensibility points

* **Per‑module levels**

  ```python
  Log.set_level("WARNING", module="order_core")
  ```

* **Extra sinks**

  Any callable that accepts an *event* dict can be registered:

  ```python
  def to_kafka(ev): producer.send("logs", ev)
  Log.add_sink(to_kafka)
  ```

* **Rich progress / banners**

  If `rich` is present:

  ```python
  Log.banner("Phase I – Loading")
  ```

---
## 5. Event schema

Each JSON log line contains:

```json
{
  "ts":       "YYYY-MM-DD HH:MM:SS",
  "level":    "INFO",
  "level_no": 20,
  "message":  "...",
  "source":   "module_name",
  "payload":  { ... }      # optional arbitrary dict
}
```

---
## 6. Migration notes

* All previous APIs (`info`, `success`, `warning`, `error`, `debug`, `death`)
  remain unchanged.
* Colour constants and group‑based muting still work.
* `death()` is now an alias of `critical()`.

No code changes are required for existing call‑sites – only the improved
features described above are new.

---
## 7. Changelog

* **v3.0.0**
  * Introduced structured events, Rich formatting, sinks, thread safety.
  * Added standard severity levels and environment configuration.
  * Reimplemented banner / timer utilities atop the new core.
