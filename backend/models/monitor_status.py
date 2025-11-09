# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


# -----------------------------
# Enums (public API)
# -----------------------------

class MonitorType(str, Enum):
    """Canonical monitor categories."""
    LIQUID    = "liquid"
    PROFIT    = "profit"
    MARKET    = "market"
    CUSTOM    = "custom"
    PRICES    = "prices"
    POSITIONS = "positions"
    RAYDIUM   = "raydium"
    HEDGES    = "hedges"
    REPORTERS = "reporters"
    HEARTBEAT = "heartbeat"


class MonitorState(str, Enum):
    """Normalized status values for monitors."""
    OK     = "OK"
    WARN   = "WARN"
    BREACH = "BREACH"
    SNOOZE = "SNOOZE"


# Back-compat: some older modules import MonitorHealth
MonitorHealth = MonitorState

_VALID_STATES = {s.value for s in MonitorState}


def _ensure_iso(ts: Any) -> str:
    """Return an ISO-8601 timestamp string (UTC) from iso/epoch/None."""
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    s = str(ts)
    if s.endswith("Z"):
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


# -----------------------------
# Dataclass
# -----------------------------


@dataclass
class MonitorDetail:
    """Detailed information about a single monitor entry."""

    name: str
    enabled: bool
    status: MonitorState
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass
class MonitorStatus:
    """
    Normalized per-item monitor result for a cycle.

    Fields:
      cycle_id  : ID tying rows to a single engine cycle
      ts        : ISO-8601 (UTC) timestamp string
      monitor   : category (see MonitorType)
      label     : human label, e.g. "BTC – Liq"
      state     : OK / WARN / BREACH / SNOOZE (see MonitorState)
      value     : numeric value for the measurement (optional)
      unit      : unit for value ("%","$","bp",""…)
      thr_op    : comparator, e.g. "<", "<=", ">", ">=", "=="
      thr_value : numeric threshold value (optional)
      thr_unit  : unit for threshold (optional)
      source    : short tag of source subsystem ("liq","profit","mkt","feed", …)
      meta      : free-form JSON dict with extra fields
    """
    cycle_id: str
    ts: str
    monitor: str
    label: str
    state: str
    value: Optional[float] = None
    unit: str = ""
    thr_op: Optional[str] = None
    thr_value: Optional[float] = None
    thr_unit: Optional[str] = None
    source: Optional[str] = None
    meta: Dict[str, Any] = None

    def to_row(self) -> Dict[str, Any]:
        d = asdict(self)
        # normalize fields
        d["monitor"] = (d["monitor"] or "").lower()
        st = (d["state"] or "OK").upper()
        d["state"] = st if st in _VALID_STATES else "OK"
        d["ts"] = _ensure_iso(d.get("ts"))
        if d.get("value") is not None:
            try:
                d["value"] = float(d["value"])
            except Exception:
                d["value"] = None
        if d.get("thr_value") is not None:
            try:
                d["thr_value"] = float(d["thr_value"])
            except Exception:
                d["thr_value"] = None
        d["unit"] = d.get("unit") or ""
        d["thr_op"] = d.get("thr_op") or None
        d["thr_unit"] = d.get("thr_unit") or None
        d["source"] = d.get("source") or d["monitor"][:6]
        d["meta"] = d.get("meta") or {}
        return d

    @staticmethod
    def from_status_dict(
        cycle_id: str,
        monitor: str | MonitorType,
        item: Dict[str, Any],
        *,
        default_label: Optional[str] = None,
        now_iso: Optional[str] = None,
        default_source: Optional[str] = None,
    ) -> "MonitorStatus":
        """
        Build a MonitorStatus from a runner item dict. Supports flexible keys:
          - item['state'] or ['status']
          - item['threshold'] or item['meta']['threshold'] -> {op,value,unit}
          - item['unit'] or item['meta']['unit']
          - item['ts'] or item['meta']['ts']
        """
        mon = str(monitor.value if isinstance(monitor, MonitorType) else monitor).lower()
        meta = item.get("meta") or {}
        thr  = item.get("threshold") or meta.get("threshold") or {}
        ts   = item.get("ts") or meta.get("ts") or now_iso

        label = item.get("label") or item.get("name") or default_label or mon
        state = (item.get("state") or item.get("status") or "OK").upper()
        unit  = item.get("unit") or meta.get("unit") or ""
        value = item.get("value")

        thr_op    = thr.get("op") or thr.get("operator")
        thr_value = thr.get("value")
        thr_unit  = thr.get("unit")

        source = meta.get("source") or default_source or mon[:6]

        return MonitorStatus(
            cycle_id=cycle_id,
            ts=_ensure_iso(ts),
            monitor=mon,
            label=str(label),
            state=state if state in _VALID_STATES else "OK",
            value=(float(value) if value is not None else None),
            unit=str(unit),
            thr_op=(str(thr_op) if thr_op else None),
            thr_value=(float(thr_value) if thr_value is not None else None),
            thr_unit=(str(thr_unit) if thr_unit else None),
            source=source,
            meta=(meta if isinstance(meta, dict) else {}),
        )


try:
    __all__
except NameError:
    __all__ = []

for _sym in ("MonitorDetail",):
    if _sym not in __all__:
        __all__.append(_sym)
