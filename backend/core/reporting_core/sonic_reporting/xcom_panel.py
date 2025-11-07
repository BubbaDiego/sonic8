from __future__ import annotations

from typing import Any, Optional, Sequence

try:
    from rich.table import Table
    from rich.text import Text
except Exception:  # pragma: no cover - optional dependency
    Table = None  # type: ignore
    Text = None  # type: ignore

try:
    from backend.core.reporting_core.sonic_reporting.config_probe import discover_json_path, parse_json
except Exception:  # pragma: no cover - defensive fallback
    def discover_json_path(_):  # type: ignore
        return None

    def parse_json(_):  # type: ignore
        return {}, None, {}

try:
    from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status
except Exception:  # pragma: no cover - optional dependency
    def xcom_live_status(dl: Any, cfg: dict | None = None) -> tuple[bool, str]:
        val = getattr(dl, "xcom_live", None)
        if isinstance(val, bool):
            return val, "RUNTIME"
        return True, "RUNTIME"

try:
    from backend.services.xcom_status_service import get_last_attempt
except Exception:  # pragma: no cover - optional dependency
    def get_last_attempt(_):
        return None


def _text(val: str, *, style: Optional[str] = None):
    if Text is None:
        return val
    return Text(val, style=style) if style else Text(val)


def _chip_on_off(v: bool):
    return _text("🟢  ON", style="bold green") if v else _text("🔴  OFF", style="bold red")


def _cfg_source_label(path: Optional[str]) -> str:
    return f"FILE {path}" if path else "[-]"


def _resolve_cfg(default_json_path: Optional[str]) -> tuple[dict, Optional[str]]:
    cfg = {}
    path = None
    try:
        path = default_json_path or discover_json_path(None)
        if path:
            obj, _err, _meta = parse_json(path)
            if isinstance(obj, dict):
                cfg = obj
    except Exception:
        cfg = {}
    return cfg, path


def _voice_enabled(cfg: dict, dl: Any) -> bool:
    v = cfg.get("liquid", {}).get("notifications", {}).get("voice", None)
    if isinstance(v, bool):
        return v
    rv = getattr(dl, "voice_enabled", None)
    if isinstance(rv, bool):
        return rv
    return True


def _provider_cooldown_ok(dl: Any) -> tuple[bool, str]:
    status = getattr(dl, "xcom_provider_state", None) or getattr(dl, "provider_state", None) or "idle"
    ok = getattr(dl, "xcom_provider_cooldown_ok", None)
    if isinstance(ok, bool):
        return ok, str(status)
    ok2 = getattr(dl, "provider_cooldown_ok", None)
    if isinstance(ok2, bool):
        return ok2, str(status)
    return True, str(status)


def _is_snoozed(dl: Any) -> bool:
    v = getattr(dl, "monitor_snoozed", 0)
    try:
        return bool(v) and float(v) > 0
    except Exception:
        return bool(v)


def _format_rows(rows: Sequence[tuple[str, Any, Any]]):
    if Table is None or Text is None:
        return rows
    table = Table(title="🧪  XCOM Check", show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status", justify="center")
    table.add_column("Details")
    for check, status, details in rows:
        if isinstance(status, Text):
            status_cell = status
        else:
            status_cell = _text(str(status))
        if isinstance(details, Text):
            detail_cell = details
        else:
            detail_cell = _text(str(details))
        table.add_row(check, status_cell, detail_cell)
    return table


def render_xcom_check(dl: Any, default_json_path: Optional[str] = None):
    cfg, cfg_path = _resolve_cfg(default_json_path)
    rows: list[tuple[str, Any, Any]] = []

    rows.append(("cfg source", _text("✅"), _text(_cfg_source_label(cfg_path))))

    live, live_src = xcom_live_status(dl, cfg=cfg or getattr(dl, "global_config", None))
    rows.append(("📡  XCOM Live", _chip_on_off(bool(live)), _text(f"[{live_src}]")))

    notif = cfg.get("liquid", {}).get("notifications", {}) if isinstance(cfg, dict) else {}
    ph = "📞 " + ("✅" if notif.get("voice", True) else "❌")
    ui = "🖥️ " + ("✅" if notif.get("system", True) else "❌")
    sp = "🔊 " + ("✅" if notif.get("tts", True) else "❌")
    sm = "💬 " + ("✅" if notif.get("sms", False) else "❌")
    rows.append(("channels(liquid)", _text("✅"), _text(f"{ph}  {ui}  {sp}  {sm}")))

    ok_cd, cd_state = _provider_cooldown_ok(dl)
    rows.append(("provider cooldown", _text("✅" if ok_cd else "❌"), _text(str(cd_state))))

    breaches = getattr(dl, "breaches", None) or getattr(dl, "breaches_count", 0)
    try:
        breaches = int(breaches)
    except Exception:
        breaches = 0
    rows.append(("breaches", _text("✅" if breaches else "—"), _text(str(breaches or "—"))))
    if hasattr(dl, "breach_symbol") and hasattr(dl, "breach_distance_text"):
        rows.append((
            "  • " + str(getattr(dl, "breach_symbol")),
            _text("—"),
            _text(str(getattr(dl, "breach_distance_text"))),
        ))

    voice_on = _voice_enabled(cfg, dl)
    snoozed = _is_snoozed(dl)
    armed = bool(live) and voice_on and ok_cd and (not snoozed) and (breaches > 0)
    why = " • ".join([
        f"Live {'✓' if live else '✗'}",
        f"Voice {'✓' if voice_on else '✗'}",
        f"Cooldown {'✓' if ok_cd else '✗'}",
        f"Snoozed {'✓' if not snoozed else '✗'}",
        f"Breach {'✓' if breaches > 0 else '✗'}",
    ])
    rows.append(("dispatch.armed", _text("✅" if armed else "❌"), _text(why)))

    last = get_last_attempt(dl) or {}
    if last:
        status = last.get("status")
        label_map = {"success": "🟢 success", "fail": "🔴 fail", "skipped": "⚪ skipped"}
        label = label_map.get(status, status or "—")
        who = f"{last.get('provider', 'twilio')}/{last.get('channel', 'voice')} → {last.get('to_number', '—')}"
        sid = last.get("sid") or "—"
        src = last.get("source", "monitor")
        rows.append(("last attempt", _text(label), _text(f"{last.get('ts', '—')} • {who} • sid={sid} [{src}]")))
        if status == "fail":
            code = last.get("error_code") or "—"
            http = last.get("http_status") or "—"
            msg = (last.get("error_msg") or "—")[:120]
            rows.append(("   provider error", _text("details"), _text(f"HTTP {http} • code {code} — {msg}")))
        if status == "skipped" and last.get("gated_by"):
            rows.append(("   skipped by", _text("gate"), _text(str(last.get("gated_by")))))
    else:
        rows.append(("last attempt", _text("—"), _text("no attempts recorded")))

    return _format_rows(rows)


def render(dl: Any, _csum: Optional[dict], default_json_path: Optional[str] = None) -> None:
    panel = render_xcom_check(dl, default_json_path=default_json_path)
    if Table is not None and isinstance(panel, Table):
        try:
            from rich.console import Console

            Console().print(panel)
            return
        except Exception:
            pass

    # Fallback textual rendering when Rich is unavailable
    rows: Sequence[tuple[str, Any, Any]]
    if Table is not None and isinstance(panel, Table):  # pragma: no cover - guard in case Console import failed
        rows = []
    else:
        rows = panel  # type: ignore[assignment]

    print("XCOM Check")
    for check, status, details in rows:
        print(f"- {check}: {status} :: {details}")
