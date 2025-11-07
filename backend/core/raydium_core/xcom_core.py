from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class RaydiumXCom:
    """
    Small façade that centralizes 'external' for raydium_core:
      • invokes the existing TS valuation/scanner (sdk + jupiter)
      • captures JSON lines for Python services
    """

    def __init__(self, ts_dir: Optional[Path] = None):
        base = Path("backend/core/raydium_core/ts")
        self.ts_dir = (ts_dir or base).resolve()
        self.ts_entry = self.ts_dir / "value_raydium_positions.ts"
        exe = "ts-node.cmd" if os.name == "nt" else "ts-node"
        self.ts_node = self.ts_dir / "node_modules" / ".bin" / exe

    def _run_ts(self, args: List[str]) -> Dict[str, Any]:
        cmd = [str(self.ts_node), "--transpile-only", str(self.ts_entry)] + args
        proc = subprocess.run(
            cmd, cwd=str(self.ts_dir), text=True, capture_output=True
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        details = None
        rows = None
        for line in out.splitlines():
            if line.startswith("__JSON__DETAILS__:"):
                try:
                    payload = json.loads(line.split(":", 1)[1])
                    if isinstance(payload, dict) and isinstance(payload.get("details"), list):
                        details = payload["details"]
                except Exception:
                    pass
            elif line.startswith("__JSON__:"):
                try:
                    payload = json.loads(line.split(":", 1)[1])
                    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
                        rows = payload["rows"]
                except Exception:
                    pass
        return {"rows": rows or [], "details": details or [], "stdout": out, "returncode": proc.returncode}

    def value_nfts(self, owner: str, mints: Optional[List[str]] = None, price_url: Optional[str] = None) -> Dict[str, Any]:
        args = ["--owner", owner]
        if mints:
            args += ["--mints", ",".join(mints)]
        args += ["--emit-json"]
        if price_url:
            args += ["--price-url", price_url]
        return self._run_ts(args)
