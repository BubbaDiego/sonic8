# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


VALID_STATES = {"OK", "WARN", "BREACH", "SNOOZE"}


@dataclass
class MonitorStatus:
    cycle_id: str
    ts: str                         # ISO-8601 string
    monitor: str                    # 'liquid' | 'profit' | 'market' | 'custom' | ...
    label: str                      # human name e.g., 'BTC – Liq'
    state: str                      # OK/WARN/BREACH/SNOOZE
    value: Optional[float] = None
    unit: str = ""                  # '%', '$', 'bp', etc.
    thr_op: Optional[str] = None    # '<','<=','>=','>','=='
    thr_value: Optional[float] = None
    thr_unit: Optional[str] = None
    source: Optional[str] = None    # short code: 'liq','profit','mkt','feed'
    meta: Dict[str, Any] = None

    def to_row(self) -> Dict[str, Any]:
        d = asdict(self)
        # enforce state, coerce ts
        st = (d["state"] or "OK").upper()
        d["state"] = st if st in VALID_STATES else "OK"
        if not d.get("ts"):
            d["ts"] = datetime.now(timezone.utc).isoformat()
        if d.get("meta") is None:
            d["meta"] = {}
        return d

    @staticmethod
    def from_status_dict(
        cycle_id: str,
        monitor: str,
        item: Dict[str, Any],
        default_label: Optional[str] = None,
        now_iso: Optional[str] = None,
        default_source: Optional[str] = None,
    ) -> "MonitorStatus":
        meta = item.get("meta") or {}
        thr = item.get("threshold") or meta.get("threshold") or {}
        ts = (
            item.get("ts")
            or meta.get("ts")
            or now_iso
            or datetime.now(timezone.utc).isoformat()
        )
        label = item.get("label") or item.get("name") or default_label or monitor
        unit = item.get("unit") or meta.get("unit") or ""
        state = (item.get("state") or item.get("status") or "OK").upper()
        value = item.get("value")
        # resolve threshold parts
        thr_op = thr.get("op") or thr.get("operator")
        thr_value = thr.get("value")
        thr_unit = thr.get("unit")
        source = meta.get("source") or default_source or monitor[:6]
        return MonitorStatus(
            cycle_id=cycle_id,
            ts=str(ts),
            monitor=str(monitor).lower(),
            label=str(label),
            state=state if state in VALID_STATES else "OK",
            value=(float(value) if value is not None else None),
            unit=str(unit),
            thr_op=(str(thr_op) if thr_op else None),
            thr_value=(float(thr_value) if thr_value is not None else None),
            thr_unit=(str(thr_unit) if thr_unit else None),
            source=source,
            meta=(meta if isinstance(meta, dict) else {}),
        )
