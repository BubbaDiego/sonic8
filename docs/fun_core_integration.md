
# fun_core Integration Instructions for Codex

1. **Backend**
   * Add the following import in `backend/sonic_backend_app.py` after existing routers:
     ```python
     from backend.core.fun_core import fun_router as fun_core_router
     app.include_router(fun_core_router)
     ```
   * Ensure `httpx[http2]` and `cachetools` are present in `requirements.txt`:
     ```
     httpx[http2]>=0.24.0
     cachetools>=5.3.0
     ```
   * Optional: launch the warm‑up monitor by adding in your startup script:
     ```python
     import asyncio
     from backend.core.fun_core.monitor import prewarm
     loop = asyncio.get_event_loop()
     loop.create_task(prewarm())
     ```

2. **Frontend**
   * Copy `frontend/src/ui-component/fun/FunCard.jsx` into the repo.
   * In `SettingsSection.jsx` replace the entire `<Card>` that hosts the DND/Notification switches with:
     ```jsx
     import FunCard from 'ui-component/fun/FunCard';
     ...
     <FunCard />
     ```
   * Run `npm install` if MUI toggle group dependencies are missing.

3. **Testing**
   * Run backend unit tests:
     ```
     pytest tests/test_fun_api.py -q
     ```
   * Start backend (`uvicorn backend.sonic_backend_app:app --reload`) and verify `GET /api/fun/random?type=trivia`.

4. **Deployment**
   * Set `FUN_CORE_MONITOR=1` env var and run `monitor_core` as usual; fun_core will auto‑register.

That's it – plug and play!  Enjoy the laughs 🎉
