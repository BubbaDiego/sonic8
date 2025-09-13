# backend/services/txlog.py
from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

TXLOG_DIR = Path(os.getenv("SONIC_DATA_DIR", "backend/data"))
TXLOG_FILE = TXLOG_DIR / "jupiter_txlog.jsonl"


def _ensure_dir() -> None:
    TXLOG_DIR.mkdir(parents=True, exist_ok=True)
    if not TXLOG_FILE.exists():
        TXLOG_FILE.touch()


def _jsonable(obj: Any) -> Any:
    """Convert objects (solders, dataclasses, bytes…) to JSON-serializable primitives."""
    try:
        from solders.signature import Signature as Sig  # type: ignore
        from solders.pubkey import Pubkey  # type: ignore
        if isinstance(obj, Sig) or isinstance(obj, Pubkey):
            return str(obj)
    except Exception:
        pass

    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    return str(obj)


def append(entry: Dict[str, Any]) -> None:
    """Append one entry to JSONL (atomic enough for our usage)."""
    _ensure_dir()
    if "ts" not in entry:
        entry["ts"] = datetime.now(timezone.utc).isoformat()
    line = json.dumps(_jsonable(entry), separators=(",", ":"))
    with open(TXLOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_last(limit: int = 50) -> List[Dict[str, Any]]:
    """Read last N entries (reverse scan)."""
    _ensure_dir()
    try:
        with open(TXLOG_FILE, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            buf = bytearray()
            lines: List[bytes] = []
            i = size - 1
            while i >= 0 and len(lines) < limit:
                f.seek(i)
                b = f.read(1)
                if b == b"\n" and buf:
                    lines.append(bytes(reversed(buf)))
                    buf.clear()
                else:
                    buf.append(b[0])
                i -= 1
            if buf:
                lines.append(bytes(reversed(buf)))
        out: List[Dict[str, Any]] = []
        for raw in reversed(lines):
            try:
                out.append(json.loads(raw.decode("utf-8").strip()))
            except Exception:
                continue
        return out
    except FileNotFoundError:
        return []


def find_by_signature(sig: str) -> Optional[Dict[str, Any]]:
    """Linear scan from end; fine for our typical log sizes."""
    _ensure_dir()
    try:
        with open(TXLOG_FILE, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                try:
                    obj = json.loads(line)
                    if obj.get("execution", {}).get("sig") == sig or obj.get("signature") == sig:
                        return obj
                except Exception:
                    continue
    except FileNotFoundError:
        return None
    return None
