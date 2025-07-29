# Auto Core v1 Integration Guide

Welcome, Codex friends 👋.

This brief file explains how to plug the new **Auto Core** subsystem into the
existing Sonic‑1 backend.

---

## 1. File drop‑in

The entire package lives under `backend/core/auto_core/` and is completely
self‑contained.  Add the directory to your repository (or apply the patch
contained in `auto_core_v1.zip`) and ensure it is included in your Python
import path.

```
backend/
└─ core/
   └─ auto_core/
      ├─ __init__.py
      ├─ auto_core.py
      ├─ playwright_helper.py
      └─ requests/
         ├─ __init__.py
         ├─ base.py
         └─ web_browser.py
```

Unit tests ship in `tests/auto_core/`.

---

## 2. Requirements

Append the following packages to `requirements.txt` (or your Poetry
`pyproject.toml`):

```
playwright>=1.44,<2
pytest-asyncio>=0.23
```

Then install Playwright’s browser binaries **once**:

```bash
python -m playwright install chromium
```

---

## 3. Basic usage

```python
from backend.core.auto_core import AutoCore, WebBrowserRequest

core   = AutoCore()
result = await core.run(
    WebBrowserRequest(
        url="https://example.org",
        steps=["wait:1000"]  # totally optional
    )
)
print(result["title"])
```

Behind the scenes this:

1. Boots a *persistent* Chromium profile so the Solflare extension remains
   logged‑in across runs.
2. Loads the URL and executes any extra “steps”.
3. Returns a dict (`url`, `title`, `steps_ran`) that the caller can persist,
   transform, or forward elsewhere.

---

## 4. Wiring into Cyclone / Monitor cores (optional)

Nothing *needs* to change; `AutoCore` is orthogonal to the existing cores.
However you might:

* **Expose an HTTP endpoint**  
  Create a FastAPI route that receives JSON, constructs the appropriate
  `AutoRequest`, and returns the response.  Hook that into the existing
  `backend/routes/` folder.

* **Schedule via MonitorCore**  
  Register a new `AutoMonitor` that wraps a WebBrowserRequest for smoke‑testing
  exchange dashboards or wallet UIs.

---

## 5. Secrets & first‑run wallet onboarding

`PlaywrightHelper` intentionally leaves the Solflare onboarding flow as **TODO**
because teams differ in secret‑management preferences.  Pick one:

* `.env` with `SOLFLARE_SEED` & `SOLFLARE_PASSWORD`
* HashiCorp Vault
* Your existing `DLSystemDataManager`

Add the automated onboarding logic inside `PlaywrightHelper.__aenter__` the
**first** time the profile directory is empty.

---

## 6. Extending Auto Core

Create a new subclass of `AutoRequest`, drop it in
`backend/core/auto_core/requests/`, and Auto Core will happily execute it:

```python
class DiscordMessageRequest(AutoRequest):
    ...
```

Future ideas: email parsers, Slack bots, REST fetchers, on‑chain transactions.

---

Happy hacking ‑ let us know once you have this wired in!
