from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional, Tuple, Mapping

from backend.core.core_constants import XCOM_PROVIDERS_PATH
from backend.core.reporting_core.sonic_reporting.xcom_extras import append_xcom_history
from backend.core import config_oracle as ConfigOracle

log = logging.getLogger("sonic.engine")


def _load_providers_file() -> dict:
    p = XCOM_PROVIDERS_PATH
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def _mask(val: str | None, *, kind: str = "sid") -> str:
    if not val:
        return "-"
    s = str(val)
    if kind == "sid":
        return s[:2] + "…" + s[-4:] if len(s) > 6 else "…"
    if kind == "phone":
        return s
    return "…" + s[-4:] if len(s) > 4 else "…"


def _coerce_detail(val: Any) -> Optional[str]:
    if val is None:
        return None
    text = str(val).strip()
    return text or None


def _extract_error_detail(result: Any) -> Optional[str]:
    if isinstance(result, dict):
        for key in ("detail", "error", "reason"):
            detail = _coerce_detail(result.get(key))
            if detail:
                return detail

        for bucket in ("voice", "non_voice"):
            section = result.get(bucket)
            if isinstance(section, dict):
                for key in ("error", "reason", "detail"):
                    detail = _coerce_detail(section.get(key))
                    if detail:
                        return detail

        channels = result.get("channels")
        if isinstance(channels, dict):
            voice_chan = channels.get("voice")
            if isinstance(voice_chan, dict):
                for key in ("error", "reason", "skip"):
                    detail = _coerce_detail(voice_chan.get(key))
                    if detail:
                        return detail
    return None


def _channels_from_result(result: Any, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict):
        chan = result.get("channels")
        if isinstance(chan, dict):
            return chan
    return dict(fallback)


def _snapshot_file_voice() -> tuple[dict, list[str]]:
    voice = ((_load_providers_file() or {}).get("voice")) or {}
    missing: list[str] = []
    provider = (voice.get("provider") or "").strip().lower()
    if not provider:
        missing.append("provider")
    if not voice.get("from"):
        missing.append("from")
    if provider == "twilio":
        if not voice.get("account_sid"):
            missing.append("account_sid")
        if not voice.get("auth_token"):
            missing.append("auth_token")
        dest = voice.get("to")
        if not dest or (isinstance(dest, list) and not dest) or (isinstance(dest, str) and not dest.strip()):
            missing.append("to")
    return voice, missing


def _load_aggregator():
    try:
        mod = import_module("backend.core.xcom_core.xcom_core")
        fn  = getattr(mod, "dispatch_notifications", None)
        return fn if callable(fn) else None
    except Exception as e:
        log.info("[xcom] aggregator import failed: %s", e)
        return None


def _load_voice():
    try:
        mod = import_module("backend.core.xcom_core.dispatch")
        fn  = getattr(mod, "dispatch_voice", None)
        return fn if callable(fn) else None
    except Exception as e:
        log.info("[xcom] voice import failed: %s", e)
        return None


def _bind_dispatcher() -> Tuple[Callable[[str, Dict[str, Any], Dict[str, bool], Dict[str, Any]], Dict[str, Any]], str]:
    agg = _load_aggregator()
    voice = _load_voice()

    mode_parts: List[str] = []
    if agg:
        mode_parts.append("agg")
    if voice:
        mode_parts.append("voice")
    if not mode_parts:
        mode_parts.append("noop")

    def _send(mon: str, payload: Dict[str, Any], channels: Dict[str, bool], context: Dict[str, Any]) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        payload_with_channels = {**payload, "channels": channels}
        requested = {k: bool(channels.get(k)) for k in ("system", "sms", "tts", "voice")}
        non_voice_summary: Dict[str, Any] | None = None
        voice_result: Dict[str, Any] | None = None

        if agg:
            non_voice = {
                "system": requested["system"],
                "sms": requested["sms"],
                "tts": requested["tts"],
                "voice": False,
            }
            if any(non_voice.values()):
                agg_result = agg(mon, payload_with_channels, non_voice, context)
                details["non_voice"] = agg_result
                if isinstance(agg_result, dict):
                    non_voice_summary = agg_result

        if voice and requested["voice"]:
            voice_result = voice(payload_with_channels, {"voice": True}, context)
            details["voice"] = voice_result

        channel_status: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []

        non_voice_channels: Dict[str, Any] | None = None
        if isinstance(non_voice_summary, dict):
            candidate = non_voice_summary.get("channels")
            if isinstance(candidate, dict):
                non_voice_channels = candidate

        def _record(name: str, data: Dict[str, Any] | None) -> None:
            if data is None:
                return
            normalized = dict(data)
            normalized["ok"] = bool(normalized.get("ok"))
            if "error" not in normalized and normalized.get("reason"):
                normalized["error"] = normalized.get("reason")
            channel_status[name] = normalized
            if requested.get(name) and not normalized["ok"]:
                reason = normalized.get("error") or normalized.get("reason") or normalized.get("skip")
                errors.append(f"{name}: {reason}" if reason else name)

        if non_voice_channels:
            for name in ("system", "sms", "tts"):
                chan_data = non_voice_channels.get(name)
                if isinstance(chan_data, dict):
                    _record(name, chan_data)

        if voice_result is not None:
            if isinstance(voice_result, dict):
                voice_data = dict(voice_result)
            else:
                voice_data = {"ok": bool(voice_result)}
            if "error" not in voice_data and voice_data.get("reason"):
                voice_data["error"] = voice_data.get("reason")
            _record("voice", voice_data)

        success = len(errors) == 0
        response: Dict[str, Any] = {
            "success": success,
            "ok": success,
            "channels": channel_status,
        }

        if errors:
            response["error"] = "; ".join(errors)

        response.update(details)
        return response

    return _send, "+".join(mode_parts)


def _channels_for_monitor(cfg: Mapping[str, Any], name: str) -> dict[str, bool]:
    """
    Resolve per-monitor channel flags.

    Oracle-first:
      - ConfigOracle MonitorNotifications for this monitor.

    Legacy fallback:
      - <monitor>_monitor.notifications
      - <monitor>.notifications

    Returns a dict with booleans for:
      - system: internal console / XCom panel
      - voice: Twilio voice calls (further gated by provider "enabled" flag)
      - sms: SMS channel (currently stubbed by the dispatcher)
      - tts: local text-to-speech (pyttsx3, optional)
    """
    monitor_name = str(name).strip()

    # --- Oracle-first ---
    try:
        notifications = ConfigOracle.get_monitor_notifications(monitor_name)
        if notifications is not None:
            notif_dict = notifications.as_dict()
            return {
                "system": bool(notif_dict.get("system", True)),
                "voice": bool(notif_dict.get("voice", False)),
                "sms": bool(notif_dict.get("sms", False)),
                "tts": bool(notif_dict.get("tts", False)),
            }
    except Exception:  # pragma: no cover - defensive
        pass

    # --- Legacy JSON: <monitor>_monitor.notifications or <monitor>.notifications ---
    notif: Mapping[str, Any] | None = None

    monitor_block = cfg.get(f"{monitor_name}_monitor")
    if isinstance(monitor_block, Mapping):
        notif = monitor_block.get("notifications")

    if not isinstance(notif, Mapping):
        base_block = cfg.get(monitor_name)
        if isinstance(base_block, Mapping):
            notif = base_block.get("notifications")

    if not isinstance(notif, Mapping):
        notif = {}

    def _coerce_bool(key: str, default: bool) -> bool:
        val = notif.get(key, default)
        try:
            if isinstance(val, str):
                v = val.strip().lower()
                if v in {"1", "true", "yes", "on", "y"}:
                    return True
                if v in {"0", "false", "no", "off", "n"}:
                    return False
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, bool):
                return val
        except Exception:
            return default
        return default if val is None else bool(val)

    return {
        "system": _coerce_bool("system", True),
        "voice": _coerce_bool("voice", False),
        "sms": _coerce_bool("sms", False),
        "tts": _coerce_bool("tts", False),
    }


def _latest_dl_rows(dl) -> List[Dict[str, Any]]:
    mgr = getattr(dl, "dl_monitors", None) or getattr(dl, "monitors", None)
    if not mgr: return []
    getr = getattr(mgr, "get_rows", None)
    if callable(getr):
        try:
            rows = getr()
            return rows if isinstance(rows, list) else []
        except Exception as e:
            log.info("[xcom] dl_monitors.get_rows error: %s", e)
            return []
    rows = getattr(mgr, "rows", None) or getattr(mgr, "items", None)
    return rows if isinstance(rows, list) else []


def _global_snooze_seconds(cfg: Mapping[str, Any]) -> int:
    """
    Global snooze window (seconds) shared by monitors.

    Oracle-first:
      - ConfigOracle MonitorGlobalConfig.global_snooze_seconds

    Legacy fallback:
      - cfg["monitor"]["global_snooze_seconds"] if present, else 0
    """
    # --- Oracle-first ---
    try:
        global_cfg = ConfigOracle.get_global_monitor_config()
        if global_cfg and global_cfg.global_snooze_seconds is not None:
            return int(global_cfg.global_snooze_seconds)
    except Exception:  # pragma: no cover - defensive
        pass

    # --- Legacy JSON ---
    mon_cfg = cfg.get("monitor") or {}
    try:
        return int(mon_cfg.get("global_snooze_seconds") or 0)
    except (TypeError, ValueError):
        return 0


def _now_ts() -> float: return time.time()
def _to_iso(ts: float) -> str: return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _get_last_sent_ts(dl) -> Optional[float]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"): return None
    v = sysmgr.get_var("xcom_last_sent_ts")
    if isinstance(v, (int,float)): return float(v)
    if isinstance(v, str):
        try: return float(v)
        except Exception: return None
    return None


def _set_last_sent_ts(dl, ts: float) -> None:
    sysmgr = getattr(dl, "system", None)
    if sysmgr and hasattr(sysmgr, "set_var"):
        sysmgr.set_var("xcom_last_sent_ts", ts)


def _compose_text(row: Dict[str, Any]) -> Tuple[str, str, str]:
    mon  = (row.get("monitor") or "").lower()
    lab  = row.get("label","")
    val  = row.get("value")
    thrv = row.get("thr_value")
    thro = row.get("thr_op") or ""
    src  = (row.get("meta") or {}).get("limit_source") or row.get("source") or mon
    vtxt = f"{val:.2f}" if isinstance(val,(int,float)) else str(val or "-")
    ttxt = f"{thro} {thrv:.2f}" if isinstance(thrv,(int,float)) else "-"
    subj = f"[{mon.upper()}] {lab} BREACH"
    body = f"{lab}: value={vtxt} threshold={ttxt} source={src}"
    tts  = f"{lab} breach. Value {vtxt} vs threshold {ttxt}."
    return subj, body, tts


def _pick_event(breaches: List[Dict[str, Any]]) -> Dict[str, Any]:
    priority = {"liquid": 0, "profit": 1, "market": 2, "price": 3}
    return sorted(breaches, key=lambda r: (priority.get((r.get("monitor") or "").lower(), 99)))[0]


def dispatch_breaches_from_dl(dl, cfg: dict) -> List[Dict[str, Any]]:
    """
    DL-first XCom bridge.
    - Reads dl_monitors latest rows
    - Triggers on BREACH
    - Uses JSON channels
    - Enforces per-monitor snooze
    - Validates provider config; if missing, writes error + emits system notification
    - Uses multi-channel dispatcher via _bind_dispatcher()
    """
    send, mode = _bind_dispatcher()
    log.debug("[xcom] dispatcher mode=%s", mode)

    rows = _latest_dl_rows(dl)
    log.debug("[xcom] bridge starting; dl_rows=%d", len(rows))

    try:
        voice_file, file_missing = _snapshot_file_voice()
    except FileNotFoundError:
        log.error("[xcom] voice provider file missing: %s", XCOM_PROVIDERS_PATH)
        voice_file, file_missing = {}, ["file-missing"]
    except json.JSONDecodeError as e:
        log.error("[xcom] voice provider file invalid (%s): %s", XCOM_PROVIDERS_PATH, e)
        voice_file, file_missing = {}, ["file-invalid"]
    except Exception as e:
        log.error("[xcom] voice provider file error (%s): %s", XCOM_PROVIDERS_PATH, e)
        voice_file, file_missing = {}, ["file-error"]

    log.debug(
        "[xcom] voice(FILE %s) enabled=%s provider=%s from=%s to=%s sid=%s flow=%s missing=%s",
        str(XCOM_PROVIDERS_PATH),
        bool(voice_file.get("enabled", True)),
        (voice_file.get("provider") or "-"),
        _mask(voice_file.get("from"), kind="phone"),
        voice_file.get("to") or [],
        _mask(voice_file.get("account_sid"), kind="sid"),
        (voice_file.get("flow_sid") or "-"),
        file_missing or [],
    )

    sysmgr = getattr(dl, "system", None)
    if sysmgr and hasattr(sysmgr, "set_var"):
        try:
            sysmgr.set_var("xcom_providers", {"voice": voice_file})
        except Exception:
            pass

    _body_cfg = cfg.get("liquid_monitor", {})
    out: List[Dict[str, Any]] = []

    breaches = [r for r in (rows or []) if str(r.get("state", "")).upper() == "BREACH"]
    log.debug("[xcom] breaches=%d", len(breaches))

    for r in breaches:
        mon = (r.get("monitor") or "").lower()
        label = r.get("label") or ""
        symbol = (r.get("symbol") or label or "").upper()
        if mon not in ("liquid", "profit", "market", "price"):
            continue

        channels = _channels_for_monitor(cfg, mon)
        if not any(channels.values()):
            continue

        snooze_cfg = (cfg.get(f"{mon}_monitor") or cfg.get(mon) or {})

        # Global default from Oracle / legacy JSON
        global_default = _global_snooze_seconds(cfg)
        hard_default = 600 if mon != "profit" else 1200
        default_snooze = global_default or hard_default

        # Oracle per-monitor snooze wins over generic defaults if present
        try:
            oracle_mon = ConfigOracle.get_monitor(mon)
        except Exception:  # pragma: no cover - defensive
            oracle_mon = None

        if oracle_mon is not None and oracle_mon.snooze_seconds is not None:
            try:
                default_snooze = max(0, int(oracle_mon.snooze_seconds))
            except (TypeError, ValueError):
                # leave default_snooze as-is on bad input
                pass

        try:
            snooze_s = _global_saturation = int(
                snooze_cfg.get("snooze_seconds", default_snooze)
            )
        except (TypeError, ValueError):
            snooze_s = _global_saturation = default_snooze
        sysmgr = getattr(dl, "system", None)
        ledger_raw = sysmgr.get_var("xcom_snooze") if sysmgr and hasattr(sysmgr, "get_var") else {}
        ledger = ledger_raw if isinstance(ledger_raw, dict) else {}
        last_raw = ledger.get(f"{mon}|{label}", 0)
        try:
            last_ts = float(last_raw)
        except (TypeError, ValueError):
            last_ts = 0.0
        now_ts = time.time()
        min_seconds = max(0, _global_saturation)
        elapsed = now_ts - last_ts
        if elapsed < min_seconds:
            if sysmgr and hasattr(sysmgr, "set_var"):
                remaining = int(max(0, min_seconds - elapsed))
                skip_detail = f"remaining={remaining}s"
                sysmgr.set_var(
                    "xcom_last_skip",
                    {
                        "monitor": mon,
                        "label": label,
                        "ts": now_ts,
                        "reason": "global-snooze",
                        "remaining_seconds": remaining,
                        "min_seconds": int(min_seconds),
                        "detail": skip_detail,
                    },
                )
                append_xcom_history(
                    dl,
                    {
                        "type": "skip",
                        "ts": now_ts,
                        "monitor": mon,
                        "label": label,
                        "result": f"global-snooze remaining={remaining}s",
                        "channels": {},
                        "detail": skip_detail,
                    },
                )
            log.info(
                "[xcom] skip %s %s due to snooze (remaining=%ss)",
                mon,
                label,
                int(max(0, min_seconds - elapsed)),
            )
            continue

        subj, body, tts = _compose_text(r)

        voice_needed = bool(channels.get("voice")) and bool(voice_file.get("enabled", True))
        if bool(channels.get("voice")) != voice_needed:
            channels = {**channels, "voice": voice_needed}

        voice_cfg: Dict[str, Any] = {}
        if voice_needed:
            try:
                voice_cfg, missing = _snapshot_file_voice()
            except FileNotFoundError:
                voice_cfg, missing = {}, ["file-missing"]
            except json.JSONDecodeError:
                voice_cfg, missing = {}, ["file-invalid"]
            except Exception:
                voice_cfg, missing = {}, ["file-error"]

            if missing:
                msg = f"voice provider missing keys (file): {', '.join(missing)} @ {XCOM_PROVIDERS_PATH}"
                log.error("[xcom] %s", msg)

                sysmgr = getattr(dl, "system", None)
                now = time.time()
                if sysmgr and hasattr(sysmgr, "set_var"):
                    sysmgr.set_var(
                        "xcom_last_error",
                        {
                            "ts": now,
                            "monitor": mon,
                            "label": label,
                            "reason": "provider-missing-file",
                            "missing": sorted(set(missing)),
                            "path": str(XCOM_PROVIDERS_PATH),
                            "detail": msg,
                        },
                    )
                    append_xcom_history(
                        dl,
                        {
                            "type": "error",
                            "ts": now,
                            "monitor": mon,
                            "label": label,
                            "result": "ERROR",
                            "channels": {},
                            "detail": msg,
                        },
                    )

                try:
                    payload_err = {
                        "breach": True,
                        "monitor": mon,
                        "label": label,
                        "value": r.get("value"),
                        "threshold": {"op": r.get("thr_op"), "value": r.get("thr_value")},
                        "source": (r.get("meta") or {}).get("limit_source") or r.get("source"),
                        "cycle_id": r.get("cycle_id"),
                        "error": msg,
                    }
                    send(mon, payload_err, {"system": True, "voice": False, "sms": False, "tts": False}, {"dl": dl})
                except Exception:
                    pass

                continue

        payload = {
            "breach": True,
            "monitor": mon,
            "label": label,
            "symbol": symbol,
            "value": r.get("value"),
            "threshold": {"op": r.get("thr_op"), "value": r.get("thr_value")},
            "source": (r.get("meta") or {}).get("limit_source") or r.get("source"),
            "cycle_id": r.get("cycle_id"),
            "subject": subj,
            "body": body,
            "summary": tts,
            "channels": {
                "system": channels.get("system"),
                "sms": channels.get("sms"),
                "tts": channels.get("tts"),
                "voice": False,
            },
        }
        context = {"voice": {"tts": tts, "provider": voice_cfg}, "dl": dl}

        try:
            result = send(mon, payload, channels, context)
            out.append({"monitor": mon, "label": label, "channels": channels, "result": result})
            log.info("[xcom] dispatched %s %s -> %s", mon, label, json.dumps(channels))
            success = bool(result.get("success", False)) if isinstance(result, dict) else bool(result)
            result_channels = _channels_from_result(result, channels)
            if sysmgr and hasattr(sysmgr, "set_var"):
                now_ts = time.time()
                if success:
                    ledger = ledger or {}
                    ledger[f"{mon}|{label}"] = now_ts
                    sysmgr.set_var("xcom_snooze", ledger)
                    sysmgr.set_var(
                        "xcom_last_sent",
                        {
                            "ts": now_ts,
                            "monitor": mon,
                            "label": label,
                            "channels": result_channels,
                            "result": result,
                            "subject": subj,
                            "success": True,
                            "detail": None,
                        },
                    )
                    summary_text = (payload.get("body") or payload.get("subject") or "OK")
                    append_xcom_history(
                        dl,
                        {
                            "type": "send",
                            "ts": now_ts,
                            "monitor": mon,
                            "label": label,
                            "result": str(summary_text).strip() or "OK",
                            "channels": result_channels,
                            "detail": None,
                        },
                    )
                else:
                    error_detail = _extract_error_detail(result)
                    sysmgr.set_var(
                        "xcom_last_error",
                        {
                            "ts": now_ts,
                            "monitor": mon,
                            "label": label,
                            "channels": result_channels,
                            "result": result,
                            "subject": subj,
                            "success": False,
                            "detail": error_detail,
                        },
                    )
                    append_xcom_history(
                        dl,
                        {
                            "type": "error",
                            "ts": now_ts,
                            "monitor": mon,
                            "label": label,
                            "result": "ERROR",
                            "channels": result_channels,
                            "detail": error_detail,
                        },
                    )
        except Exception as e:
            log.error("[xcom] dispatch error for %s %s: %s", mon, label, e)
            if sysmgr and hasattr(sysmgr, "set_var"):
                err_ts = time.time()
                sysmgr.set_var(
                    "xcom_last_error",
                    {
                        "monitor": mon,
                        "label": label,
                        "ts": err_ts,
                        "reason": f"dispatch-exception: {e}",
                        "detail": str(e),
                    },
                )
                append_xcom_history(
                    dl,
                    {
                        "type": "error",
                        "ts": err_ts,
                        "monitor": mon,
                        "label": label,
                        "result": "ERROR",
                        "channels": {},
                        "detail": str(e),
                    },
                )
            try:
                send(mon, {**payload, "error": str(e)}, {"system": True, "voice": False, "sms": False, "tts": False}, {"dl": dl})
            except Exception:
                pass

    log.debug("[xcom] sent %d notifications (including error notifies)", len(out))
    return out
