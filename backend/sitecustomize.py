import sys, asyncio

# Ensure Playwright can spawn subprocesses on Windows by forcing the
# Selector event‑loop, which supports subprocess transport.  Placed in
# sitecustomize.py so it is imported *before* any user code.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
