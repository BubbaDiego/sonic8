# Test Core Subsystem Specification
Generated: 2025-06-21 14:25:10Z

This document mirrors the design agreed upon in chat and describes the initial
directory layout and component responsibilities for `test_core/`.

```
test_core/
├── __init__.py          # Re‑exports public API (TestCoreRunner, ...)
├── __main__.py          # Enables `python -m test_core` launcher
├── icons.py             # Central emoji/icon map
├── formatter.py         # Grade & summary utilities
├── runner.py            # Low‑level pytest glue (TestCoreRunner)
├── console_ui.py        # Pick‑list console UI (Rich TUI pending)
├── failures/            # Cleared each run; one file per failure + ALL_FAILURES.txt
│   └── .gitkeep
├── reports/             # HTML/JSON summaries (preserves history)
│   └── .gitkeep
└── tests/               # All test_*.py files + conftest.py
    ├── conftest.py
    └── test_placeholder.py
```

## Component Notes

| File | Purpose |
|------|---------|
| **icons.py** | Single map with icons for outcomes, grades, menu glyphs, and banner art. |
| **formatter.py** | Converts pass‑rate into letter grade (`A+` – `F`) and renders a concise console summary. |
| **runner.py** | `TestCoreRunner` handles clearing `failures/`, invoking pytest, writing failure files, and producing result dicts. |
| **console_ui.py** | Minimal pick‑list console interface. Future iterations will adopt Rich for colour and tables. |
| **failures/** | Ephemeral; auto‑cleared. Each failed test gets `<name>_fail.txt` and content is aggregated into `ALL_FAILURES.txt`. |
| **reports/** | Persisted; contains JSON + optional HTML summary of the most recent run. |
| **tests/** | Houses `conftest.py` (copied from repo root for isolation) and sample tests. |

## Grading Algorithm
Implemented in `formatter.grade_from_pct(pct)`:

```
if pct == 100:  A+
90 ≤ pct < 100: A
80 ≤ pct < 90:  B
70 ≤ pct < 80:  C
60 ≤ pct < 70:  D
else:           F
```

The icon set in `icons.py` maps these grades to emojis for quick visual feedback.

## Future Work
* Replace built‑in `input()` UI with Rich‑based pick‑list (`TestConsoleUI`).
* Add HTML reporting via `pytest‑html` integration.
* Introduce Slack/email reporters using result dict from `TestCoreRunner`.
* Expand unit tests under `tests/` to cover grading logic and UI helpers.

---  
This scaffold is implementation‑ready for Codex to extend.
