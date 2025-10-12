# Thin shim so Launch Pad’s legacy probe also succeeds.
from .cyclone_console import main

if __name__ == "__main__":
    raise SystemExit(main())

