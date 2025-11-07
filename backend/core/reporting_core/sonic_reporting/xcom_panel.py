# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Optional, Dict, List

from rich.console import Console
from rich.table import Table
from rich.text import Text

# -------------------- defensive imports --------------------

try:
    from backend.core.reporting_core.sonic_reporting.config_probe import discover_json_path, parse_json
except Exception:
    def discover_json_path(_): return None
    def parse_json(_): return {}, None, {}

try:
    from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status
except Exception:
    def xcom_live_status(dl: Any, cfg: dict | None = None) -> tuple[bool, str]:
        v = getattr(dl, "xcom_live", None)
        return (bool(v), "RUNTIME") if isinstance(v, bool) else (True, "RUNTIME")

_NEAREST_FROM_SUMMARY = None
try:
    from backend.core.monitor_core.summary_helpers import get_nearest_liquidation_distances as _N1  # type: ignore
    _NEAREST_FROM_SUMMARY = _N1
except Exception:
    pass

_NEAREST_FROM_REPORTING = None
try:
    from backend.core.reporting_core.sonic_reporting.evaluations_table import get_nearest_liquidation_distances as _N2  # type: ignore
    _NEAREST_FROM_REPORTING = _N2
except Exception:
    pass

try:
    from backend.services.xcom_status_service import get_last_attempt
except Exception:
    def get_last_attempt(_): return None


# -------------------- utils --------------------

def _chip_on_off(v: bool) -> Text:
    return Text("🟢  ON", style="bold green") if v else Text("🔴  OFF", style="bold red")

def _cfg_source_label(path: Optional[str]) -> str:
    return f"FILE {path}" if isinstance(path, str) and path else "[-]"

def _is_num(x: Any) -> bool:
    try:
        float(x); return True
    except Exception:
        return False


# -------------------- config + thresholds --------------------

def _load_cfg_from_file() -> tuple[dict, Optional[str]]:
    cfg, path = {}, None
    try:
        path = discover_json_path(None)
        if path:
            obj, err, meta = parse_json(path)
            if isinstance(obj, dict):
                cfg = obj
    except Exception:
        cfg = {}
    return cfg, path

def _extract_thresholds(cfg: Dict) -> Dict[str, float]:
    t = {}
    try:
        t = cfg.get("liquid", {}).get("thresholds", {}) or {}
        if not t:
            t = cfg.get("liquid_monitor", {}).get("thresholds", {}) or {}
    except Exception:
        t = {}
    out: Dict[str, float] = {}
    for k, v in (t or {}).items():
        try:
            out[str(k).upper()] = float(v)
        except Exception:
            pass
    return out


# -------------------- nearest distance lookup --------------------

def _nearest_from_csum(csum: dict) -> Dict[str, float]:
    out: Dict[str, float] = {}
    try:
        rows = (csum.get("positions") or {}).get("rows") or []
        for r in rows:
            if not isinstance(r, dict):
                continue
            sym = str(r.get("asset") or r.get("symbol") or "").upper()
            if not sym:
                continue
            cand = None
            for key in ("liq_dist", "liq_distance", "distance_to_liq", "nearest", "distance"):
                v = r.get(key)
                if _is_num(v):
                    cand = float(v); break
            if cand is None:
                continue
            if sym not in out or cand < out[sym]:
                out[sym] = cand
    except Exception:
        pass
    return out

def _nearest_from_dl(dl: Any) -> Dict[str, float]:
    for key in ("liquid_nearest", "nearest_liquid_distances", "liquid_nearest_by_symbol"):
        v = getattr(dl, key, None)
        if isinstance(v, dict) and v:
            return {str(k).upper(): float(v[k]) for k in v if _is_num(v[k])}
    for key in ("sonic_summary", "summary", "enriched_summary"):
        d = getattr(dl, key, None)
        if isinstance(d, dict):
            liquid = d.get("liquid") or d.get("nearest") or {}
            if isinstance(liquid, dict):
                out: Dict[str, float] = {}
                for k, val in liquid.items():
                    if _is_num(val):
                        out[str(k).upper()] = float(val)
                    elif isinstance(val, dict):
                        for sub in ("distance", "nearest", "value"):
                            vv = val.get(sub)
                            if _is_num(vv):
                                out[str(k).upper()] = float(vv); break
                if out: return out
    return {}

def _nearest_from_positions(dl: Any) -> Dict[str, float]:
    rows = []
    try:
        rows = dl.read_positions() if hasattr(dl, "read_positions") else getattr(dl, "positions", [])
        rows = rows or []
    except Exception:
        rows = []
    best: Dict[str, float] = {}
    for p in rows:
        try:
            sym = str(p.get("asset") or p.get("symbol") or "").upper()
            if not sym: continue
            cand = None
            for key in ("liq_distance", "liq_dist", "distance_to_liq", "nearest", "distance"):
                v = p.get(key)
                if _is_num(v):
                    cand = float(v); break
            if cand is None: continue
            if sym not in best or cand < best[sym]:
                best[sym] = cand
        except Exception:
            continue
    return best

def _get_nearest_map(dl: Any, csum: Optional[dict]) -> Dict[str, float]:
    if isinstance(csum, dict):
        d = _nearest_from_csum(csum)
        if d: return d
    try:
        if _NEAREST_FROM_SUMMARY:
            d = _NEAREST_FROM_SUMMARY(dl)  # type: ignore
            if isinstance(d, dict) and d:
                return {str(k).upper(): float(d[k]) for k in d if _is_num(d[k])}
    except Exception:
        pass
    try:
        if _NEAREST_FROM_REPORTING:
            d = _NEAREST_FROM_REPORTING(dl)  # type: ignore
            if isinstance(d, dict) and d:
                return {str(k).upper(): float(d[k]) for k in d if _is_num(d[k])}
    except Exception:
        pass
    d = _nearest_from_dl(dl)
    if d: return d
    return _nearest_from_positions(dl)


# -------------------- XCOM live resolver (robust) --------------------

def _resolve_xcom_live(dl: Any, file_cfg: dict) -> tuple[bool, str]:
    # try the shared resolver first (with the real file cfg)
    live, src = xcom_live_status(dl, cfg=file_cfg or getattr(dl, "global_config", None))
    if src and src != "—":
        return bool(live), src

    # hard fallback — read file directly
    try:
        v = file_cfg.get("monitor", {}).get("xcom_live", None)
        if isinstance(v, bool):
            return v, "FILE"
    except Exception:
        pass

    # runtime fallback
    v = getattr(dl, "xcom_live", None)
    if isinstance(v, bool):
        return v, "RUNTIME"

    return False, "—"


# -------------------- table builder & render --------------------

def _build_table(dl: Any, csum: Optional[dict]) -> Table:
    t = Table(title="🧪  XCOM Check", show_header=True, header_style="bold")
    t.add_column("Check")
    t.add_column("Status", justify="center")
    t.add_column("Details")

    # 1) Config (always from real file; do NOT use csum here)
    file_cfg, cfg_path = _load_cfg_from_file()
    t.add_row("cfg source", Text("✅"), Text(_cfg_source_label(cfg_path)))
    thresholds = _extract_thresholds(file_cfg)

    # 2) XCOM Live (robust)
    live, live_src = _resolve_xcom_live(dl, file_cfg)
    t.add_row("📡  XCOM Live", _chip_on_off(bool(live)), Text(f"[{live_src}]"))

    # 3) notifications (liquid)
    notif = file_cfg.get("liquid", {}).get("notifications", {})
    ph = "📞 " + ("✅" if notif.get("voice", True) else "❌")
    ui = "🖥️ " + ("✅" if notif.get("system", True) else "❌")
    sp = "🔊 " + ("✅" if notif.get("tts", True) else "❌")
    sm = "💬 " + ("✅" if notif.get("sms", False) else "❌")
    t.add_row("channels(liquid)", Text("✅"), Text(f"{ph}  {ui}  {sp}  {sm}"))

    # 4) provider cooldown
    state = getattr(dl, "xcom_provider_state", None) or getattr(dl, "provider_state", None) or "idle"
    ok_cd = getattr(dl, "xcom_provider_cooldown_ok", None)
    if not isinstance(ok_cd, bool):
        ok_cd = getattr(dl, "provider_cooldown_ok", True)
    t.add_row("provider cooldown", Text("✅" if ok_cd else "❌"), Text(str(state)))

    # 5) Published breach (what XCOM gates on)
    pub_count = getattr(dl, "breaches", None) or getattr(dl, "breaches_count", None)
    try:
        pub_count = int(pub_count)
    except Exception:
        pub_count = None
    pub_sym = getattr(dl, "breach_symbol", None)
    pub_dist = getattr(dl, "breach_distance", None)
    pub_thr  = getattr(dl, "breach_threshold", None)
    t.add_row("breaches (published)",
              Text("✅" if pub_count and pub_count > 0 else "—"),
              Text(f"{pub_count or '—'} • {pub_sym or '—'} • {pub_dist or '—'} ≤ {pub_thr or '—'}"))

    # 6) Recompute breach (same logic as monitor panel; prefers csum)
    nearest = _get_nearest_map(dl, csum)
    calc_breached: List[str] = []
    for sym, thr in thresholds.items():
        val = nearest.get(sym)
        if _is_num(val) and float(val) <= float(thr):
            calc_breached.append(sym)
    calc_ok = bool(calc_breached)
    t.add_row("breaches (recalc)",
              Text("✅" if calc_ok else "—"),
              Text(f"{len(calc_breached)} • {', '.join(calc_breached) or '—'}"))

    # 7) mismatch diag
    diag = "match" if ((pub_count or 0) > 0) == calc_ok else "MISMATCH — publish vs calc"
    t.add_row("breach diag", Text("✅" if diag == "match" else "❌"), Text(diag))

    # 8) Armed summary (uses *published* breach)
    voice_on = bool(notif.get("voice", True))
    snoozed  = False
    for key in ("monitor_snoozed", "liquid_snoozed", "liquid_snooze"):
        v = getattr(dl, key, 0)
        try:
            if float(v) > 0: snoozed = True
        except Exception:
            if isinstance(v, bool) and v: snoozed = True
    armed = bool(live) and voice_on and ok_cd and (not snoozed) and bool(pub_count and pub_count > 0)
    why = " • ".join([
        f"Live {'✓' if live else '✗'}",
        f"Voice {'✓' if voice_on else '✗'}",
        f"Cooldown {'✓' if ok_cd else '✗'}",
        f"Snoozed {'✓' if not snoozed else '✗'}",
        f"Breach {'✓' if (pub_count and pub_count > 0) else '✗'}",
    ])
    t.add_row("dispatch.armed", Text("✅" if armed else "❌"), Text(why))

    # 9) last attempt (dispatcher telemetry)
    last = get_last_attempt(dl) or {}
    if last:
        status = last.get("status")
        label = {"success":"🟢 success","fail":"🔴 fail","skipped":"⚪ skipped"}.get(status, status or "—")
        who = f"{last.get('provider','twilio')}/{last.get('channel','voice')} → {last.get('to_number','—')}"
        sid = last.get("sid") or "—"
        src = last.get("source", "monitor")
        t.add_row("last attempt", Text(label), Text(f"{last.get('ts','—')} • {who} • sid={sid} [{src}]"))
        if status == "fail":
            code = last.get("error_code") or "—"
            http = last.get("http_status") or "—"
            msg  = (last.get("error_msg") or "—")[:120]
            t.add_row("   provider error", Text("details"), Text(f"HTTP {http} • code {code} — {msg}"))
        if status == "skipped" and last.get("gated_by"):
            t.add_row("   skipped by", Text("gate"), Text(str(last.get("gated_by"))))
    else:
        t.add_row("last attempt", Text("—"), Text("no attempts recorded"))

    return t


def render(dl: Any, csum: Optional[dict] = None) -> None:
    """
    Sequencer entrypoint. Note: csum is a cycle summary dict; we DO NOT use it
    for loading config, only to help recalc nearest distances.
    """
    console = Console()
    table = _build_table(dl, csum if isinstance(csum, dict) else None)
    console.print(table)
