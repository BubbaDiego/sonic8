from __future__ import annotations

"""
Liquidation Monitor — edge-free + explicit XCOM call

Behavior:
  • Pull active positions (fallback to latest snapshot if needed).
  • Compute per-asset liquidation "distance" by taking the MIN across sides.
  • Compare to JSON thresholds (liquid.thresholds), breach if value <= threshold.
  • If any breach exists: CALL XCOM DISPATCHER (no rising-edge, no extra gates).
  • Channel enablement comes from JSON: liquid.notifications.* only.
  • Provider readiness + global cooldown are enforced inside dispatch path.

Debug:
  • Loud [LM] console prints for config source, channels, thresholds, values, breaches, and call results.
  • Never silent-fails loading JSON or reading channels.

Inputs:
  • dl: DataLocker instance (mother.db already set up by the runner).
  • default_json_path (optional): canonical JSON path; when omitted we’ll try dl.global_config.
  • pos_rows (optional): runner-provided positions (we’ll still validate and print counts).

Return:
  {
    "monitor": "liquid",
    "values": {"BTC": <float|None>, "ETH": <float|None>, "SOL": <float|None>},
    "thresholds": {"BTC": <float|None>, ...},
    "breaches": [{"asset": "SOL", "value": 8.96, "threshold": 11.5}],
    "channels": {"voice": True, "system": True, "sms": False, "tts": False},
    "dispatch": {...} | None,
    "config_source": "GLOBAL" | "FILE" | "EMPTY",
  }
"""

from typing import Any, Mapping

import json
from pathlib import Path

# Core infra
from backend.core.logging import log
from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker

# XCOM consolidated dispatcher (no legacy)
from backend.core.xcom_core import dispatch_notifications


# ---------- Small utils ----------

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def _as_float(x: Any) -> float | None:
    if _is_num(x):
        try:
            return float(x)  # type: ignore[return-value]
        except Exception:
            return None
    return None


def _read_json_config_from_path(path: str | Path) -> dict:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return json.loads(text)


def _discover_json_path(default_json_path: str | None) -> str | None:
    """
    Prefer explicit default_json_path if exists;
    otherwise accept a few common fallbacks. Return None if not found.
    """
    candidates: list[str] = []
    if default_json_path:
        candidates.append(default_json_path)

    # Common in this repo
    candidates += [
        "backend/config/sonic_monitor_config.json",
        "config/sonic_monitor_config.json",
    ]

    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def _load_config(dl: DataLocker, default_json_path: str | None) -> tuple[dict, str]:
    """
    Return (config, source_label) where source_label ∈ {"GLOBAL", "FILE", "EMPTY"}.
    Loud logs; never silent.
    """
    # If runner already hoisted JSON into dl.global_config, use that
    if getattr(dl, "global_config", None):
        cfg = getattr(dl, "global_config")
        if isinstance(cfg, dict) and cfg:
            print("[LM][CFG] ✅ source=GLOBAL keys=%d" % len(cfg.keys()))
            return cfg, "GLOBAL"

    # Else try file discovery
    path = _discover_json_path(default_json_path)
    if path is None:
        print("[LM][CFG] discover_json_path returned None")
    else:
        try:
            cfg = _read_json_config_from_path(path)
            if isinstance(cfg, dict) and cfg:
                print(f"[LM][CFG] ✅ source=FILE path={Path(path).resolve()} keys={len(cfg.keys())}")
                return cfg, "FILE"
        except Exception as exc:
            print(f"[LM][CFG] file load failed: {exc}")

    print("[LM][CFG] ⚠️  no config available; proceeding with EMPTY dict")
    return {}, "EMPTY"


def _channels_from_json(cfg: dict, monitor_name: str) -> dict[str, bool]:
    """
    Only respect monitor-level notifications block:
        cfg["liquid"]["notifications"]
    This intentionally ignores 'channels.voice' global to avoid accidental gating.
    """
    try:
        block = cfg.get(monitor_name, {}).get("notifications", {}) or {}
        voice = bool(block.get("voice", False))
        system = bool(block.get("system", False))
        sms = bool(block.get("sms", False))
        tts = bool(block.get("tts", False))
        return {"voice": voice, "system": system, "sms": sms, "tts": tts}
    except Exception:
        return {"voice": False, "system": False, "sms": False, "tts": False}


def _thresholds_from_json(cfg: dict, monitor_name: str) -> dict[str, float | None]:
    blk = cfg.get(monitor_name, {}) or {}
    thr = blk.get("thresholds", {}) or {}
    out: dict[str, float | None] = {}
    for k in ("BTC", "ETH", "SOL"):
        v = thr.get(k)
        out[k] = _as_float(v)
    return out


def _extract_positions(dl: DataLocker, pos_rows: list[dict] | None) -> list[dict]:
    """
    Try to obtain a list of 'active' positions (dict-like). We keep this defensive and chatty.
    """
    if pos_rows:
        print(f"[LM][POS] runner provided pos_rows count={len(pos_rows)}")
        return pos_rows

    rows: list[dict] = []

    # Typical places on DataLocker to find recent/active positions
    for attr in ("positions", "cache", "portfolio"):
        obj = getattr(dl, attr, None)
        if obj is None:
            continue

        for name in ("active", "active_positions", "positions", "last_positions", "snapshot"):
            got = getattr(obj, name, None)
            if isinstance(got, list) and got:
                rows = [r if isinstance(r, dict) else getattr(r, "__dict__", {}) for r in got]  # type: ignore
                if rows:
                    print(f"[LM][POS] via dl.{attr}.{name} -> {len(rows)} rows")
                    return rows

            # callable getters
            meth = getattr(obj, name, None)
            if callable(meth):
                try:
                    got = meth()
                    if isinstance(got, list) and got:
                        rows = [r if isinstance(r, dict) else getattr(r, "__dict__", {}) for r in got]  # type: ignore
                        if rows:
                            print(f"[LM][POS] via dl.{attr}.{name}() -> {len(rows)} rows")
                            return rows
                except Exception:
                    pass

    print("[LM][POS] ⚠️  no active positions found (will evaluate as no-data)")
    return []


def _symbol_of(row: Mapping[str, Any]) -> str | None:
    for k in ("asset", "symbol", "coin", "ticker"):
        v = row.get(k)
        if isinstance(v, str) and v:
            return v.strip().upper()
    return None


def _liq_of(row: Mapping[str, Any]) -> float | None:
    # try canonical names first
    for k in ("liq", "liq_dist", "liquidation", "liquidation_distance", "liq_pct"):
        if k in row:
            v = _as_float(row.get(k))
            if v is not None:
                return v
    # sometimes nested
    d = row.get("risk") or row.get("meta") or {}
    if isinstance(d, Mapping):
        for k in ("liq", "liq_dist", "liquidation"):
            v = _as_float(d.get(k))
            if v is not None:
                return v
    return None


def _compute_liq_values(rows: list[dict]) -> dict[str, float | None]:
    """
    Reduce to the MIN liquidation distance per asset symbol (BTC/ETH/SOL).
    """
    if not rows:
        return {"BTC": None, "ETH": None, "SOL": None}

    mins: dict[str, float] = {}
    for r in rows:
        sym = _symbol_of(r)
        liq = _liq_of(r)
        if sym is None or liq is None:
            continue
        prev = mins.get(sym)
        if prev is None or liq < prev:
            mins[sym] = liq

    out: dict[str, float | None] = {}
    for k in ("BTC", "ETH", "SOL"):
        out[k] = mins.get(k)
    return out


# ---------- Public entry ----------

def run(
    dl: DataLocker,
    *,
    default_json_path: str | None = None,
    pos_rows: list[dict] | None = None,
) -> dict:
    """
    Runner calls this once per cycle. We will always:
      1) Load config (GLOBAL -> FILE -> EMPTY).
      2) Read channels + thresholds.
      3) Extract positions and compute current liq values.
      4) If any breach: CALL XCOM dispatcher (no edge gate).
      5) Return a structured summary.
    """
    print("[LM] loaded LM/no-edge v2")

    # 1) Load config
    cfg, cfg_src = _load_config(dl, default_json_path)

    # 2) Channels + thresholds
    channels = _channels_from_json(cfg, "liquid")
    thresholds = _thresholds_from_json(cfg, "liquid")
    print(f"[LM][CHAN] voice={channels['voice']} system={channels['system']} "
          f"tts={channels['tts']} sms={channels['sms']} (cfg_src={cfg_src})")

    # 3) Positions -> values
    rows = _extract_positions(dl, pos_rows)
    values = _compute_liq_values(rows)
    print(f"[LM][VAL] values={values} thresholds={thresholds}")

    # 4) Evaluate breaches (value <= threshold)
    breaches: list[dict[str, Any]] = []
    for asset in ("BTC", "ETH", "SOL"):
        v = values.get(asset)
        t = thresholds.get(asset)
        if v is None or t is None:
            continue
        if v <= t:
            breaches.append({"asset": asset, "value": v, "threshold": t})

    if breaches:
        btxt = ", ".join(f"{b['asset']} {b['value']:.2f} ≤ {b['threshold']:.2f}" for b in breaches)
        print(f"[LM][BREACH] {len(breaches)} hit → {btxt}")
    else:
        print("[LM][BREACH] none")

    # 5) If breach and voice enabled -> call XCOM dispatcher
    dispatch_result: dict[str, Any] | None = None
    if breaches and channels.get("voice", False):
        subject = "[liquid] breach"
        # Compact body: list assets + value <= thr
        body = "Liquidation distance breach:\n" + "\n".join(
            f" • {b['asset']}: {b['value']:.2f} ≤ {b['threshold']:.2f}" for b in breaches
        )
        result_payload = {
            "breach": True,
            "summary": body,
            "breaches": breaches,
        }
        try:
            print("[LM][XCOM] dispatching voice…")
            dispatch_result = dispatch_notifications(
                monitor_name="liquid",
                result=result_payload,
                channels=None,              # use JSON monitor defaults
                context={"subject": subject, "body": body},
                db_path=str(getattr(dl, "path", MOTHER_DB_PATH)),
            )
            # Show the key outcome
            vch = (dispatch_result or {}).get("channels", {}).get("voice", {})
            ok = vch.get("ok")
            sid = vch.get("sid") or vch.get("call_sid") or ""
            skip = vch.get("skip") or vch.get("error") or ""
            if ok:
                print(f"[LM][VOICE] ✅ call sid={sid}")
            else:
                print(f"[LM][VOICE] ❌ {skip}")
        except Exception as exc:
            print(f"[LM][XCOM] ❌ dispatch error: {exc}")
            dispatch_result = {"error": str(exc)}

    else:
        if not breaches:
            print("[LM][XCOM] no call: no breaches")
        elif not channels.get("voice", False):
            print("[LM][XCOM] no call: channel.voice=False in JSON")

    summary = {
        "monitor": "liquid",
        "values": values,
        "thresholds": thresholds,
        "breaches": breaches,
        "channels": channels,
        "dispatch": dispatch_result,
        "config_source": cfg_src,
    }

    # (Optional) debug into structured log
    try:
        log.debug(
            "Liquidation monitor summary",
            source="liquidation_monitor",
            payload={
                "breaches": breaches,
                "voice_enabled": channels.get("voice", False),
                "config_source": cfg_src,
            },
        )
    except Exception:
        pass

    return summary
