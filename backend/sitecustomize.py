import sys, asyncio

# Ensure Playwright uses the Proactor event-loop on Windows. Placed in
# sitecustomize.py so it is imported *before* any user code.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
