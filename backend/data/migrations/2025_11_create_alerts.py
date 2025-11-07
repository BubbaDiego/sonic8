# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from backend.data import dl_alerts  # noqa: F401

def main() -> int:
    # We don't need args; schema creation is idempotent.
    try:
        # Create a minimal DL shim so dl_alerts can guess the db path.
        class _Shim:
            pass
        dl_alerts.ensure_schema(_Shim())
        print("✅ alerts schema ensured")
        return 0
    except Exception as e:
        print("❌ alerts schema failed:", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
