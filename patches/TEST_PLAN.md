
# Alert V2 – Unit‑Test Plan
**Scope:** Data/model layer only (no service / API yet)  
**Tools:** `pytest`, `sqlalchemy` in‑memory SQLite, `pydantic`

---
## 1. Objectives
1. Validate that the ORM schema can be created cleanly against a fresh DB.
2. Ensure `AlertRepo` CRUD operations behave as specified.
3. Stress basic data‑validation rules (Pydantic enums, PositiveFloat, frozen configs).
4. Guard against common regression risks:
   * Duplicate IDs
   * State auto‑creation
   * Enum / condition mismatches
   * Foreign‑key integrity

---
## 2. Test Matrix

| ID | Category | Scenario | Expected |
|----|----------|----------|----------|
| T‑01 | Schema | `ensure_schema()` on empty DB | All four tables exist |
| T‑02 | Config CRUD | `add_config()` then `get_config()` | Returned object matches input |
| T‑03 | State auto stub | After `add_config()`, `active_states()` returns a stub state with `level=NORMAL` | Stub present & fields default |
| T‑04 | State update | `save_state()` with new level/time | Subsequent `active_states()` reflects update |
| T‑05 | Duplicate config | Inserting same `id` twice | Raises `IntegrityError` |
| T‑06 | Threshold CRUD | `add_threshold()` then `thresholds_for()` | Latest threshold row returned |
| T‑07 | Log write | `repo.log()` persists row | Row count + 1 |
| T‑08 | Validation | Negative `trigger_value` in `AlertConfig` | `ValidationError` |
| T‑09 | FK integrity | Log with non‑existent `alert_id` | Persists (optional FK) |
| T‑10 | Enum mismatch | Bad `condition` passed to `Threshold` | `ValidationError` |

---
## 3. Fixtures
* **`engine`** – in‑memory SQLite engine per test session.
* **`session`** – `Session` scope function.
* **`repo`** – `AlertRepo` bound to `session`.

---
## 4. Running
```bash
pip install pytest sqlalchemy pydantic
pytest -q
```

---
## 5. Out‑of‑Scope
* No network / notification code
* No FastAPI endpoints
* No service orchestration
