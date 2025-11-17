# -*-- coding: utf-8  ---*-
from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
from datetime import datetime
from io import StringIO

from rich.console import Console
from rich.table import Table
from rich import box

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
    paint_line,
)

from backend.core.reporting_core.sonic_reporting.xcom_extras import (
    xcom_live_status,
    read_snooze_remaining,
    read_voice_cooldown_remaining,
    get_default_voice_cooldown,
)

try:
    # Width hint for Rich export; theming already uses this
    from .theming import HR_WIDTH  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    HR_WIDTH = 100

PANEL_SLUG = "xcom"
PANEL_NAME = "XCom"


# ───────────────────────── receipts + age helpers ──────────────────────────


def _get_receipt(dl: Any, key: str) -> Optional[Dict[str, Any]]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return None
    try:
        rec = sysmgr.get_var(key)
    except Exception:
        return None
    return rec if isinstance(rec, dict) else None


def _get_history(dl: Any) -> List[Dict[str, Any]]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return []
    try:
        history = sysmgr.get_var("xcom_history")
    except Exception:
        return []
    if not isinstance(history, list):
        return []
    events = [ev for ev in history if isinstance(ev, dict) and "ts" in ev]
    events.sort(key=lambda e: float(e.get("ts", 0) or 0), reverse=True)
    return events


def _compute_age_seconds(rec: Dict[str, Any]) -> int:
    try:
        ts = float(rec.get("ts", 0) or 0)
    except Exception:
        return 0
    age = int(time.time() - ts)
    return age if age >= 0 else 0


def _fmt_age(age_s: int) -> str:
    """Compact age string: 5s, 3m, 2h, 2h3m."""
    if age_s <= 0:
        return "0s"
    if age_s < 90:
        return f"{age_s}s"
    if age_s < 5400:
        return f"{age_s // 60}m"
    h = age_s // 3600
    m = (age_s % 3600) // 60
    return f"{h}h" if m == 0 else f"{h}h{m}m"


def _fmt_time_from_ts(ts_value: Any) -> str:
    """
    Format a timestamp into a short local time string like '2:44pm'.
    Falls back to '--:--' on error.
    """
    try:
        ts = float(ts_value)
        dt = datetime.fromtimestamp(ts)
        # '02:44PM' -> '2:44pm'
        t = dt.strftime("%I:%M%p").lstrip("0").lower()
        return t
    except Exception:
        return "--:--"


# ───────────────────────── attempt formatting ──────────────────────────────


def _target_icon_and_symbol(rec: Dict[str, Any]) -> (str, str):
    """Return (icon, symbol/text) for a monitor + label pair."""
    monitor = (rec.get("monitor") or "").lower()
    label = (rec.get("label") or "").strip()

    symbol = ""
    if label:
        symbol = label.split()[0]

    if monitor == "liquid":
        icon = "💧"
    elif monitor == "price":
        icon = "💲"
    elif monitor == "market":
        icon = "📈"
    else:
        icon = ""

    text = symbol or label or monitor or "?"
    return icon, text


def _channels_from_attempt(ev: Dict[str, Any]) -> str:
    """
    Legacy helper (still used elsewhere): concatenated channel icons.
    The Rich table builds a single cell with the same icon set.
    """
    ch = ev.get("channels") or {}
    if not isinstance(ch, dict):
        ch = {}

    icons: List[str] = []
    if ch.get("system"):
        icons.append("🖥")
    if ch.get("voice"):
        icons.append("📞")
    if ch.get("sms"):
        icons.append("💬")
    if ch.get("tts"):
        icons.append("🔊")

    return " ".join(icons) if icons else "–"


def _extract_value_from_text(text: str) -> Optional[str]:
    """
    Given a body/result string like:
        'SOL - Liq: value=2.60 threshold=… source=…'
    return the '2.60' bit (without units).
    """
    if not isinstance(text, str):
        return None
    s = text
    key = "value="
    if key not in s:
        return None
    tail = s.split(key, 1)[1]
    # stop at the first whitespace / comma / semicolon
    end = len(tail)
    for ch in (" ", ",", ";"):
        idx = tail.find(ch)
        if idx != -1:
            end = min(end, idx)
    value = tail[:end].strip()
    return value or None


def _monitor_title(mon: str) -> str:
    m = (mon or "").lower()
    if m in ("liquid", "liq"):
        return "Liquid"
    if m == "profit":
        return "Profit"
    if m == "market":
        return "Market"
    if m == "price":
        return "Price"
    return m.title() or "Alert"


def _details_from_attempt(ev: Dict[str, Any]) -> str:
    """
    Short detail string for the Details column.

    Keeps output concise so the table doesn't thrash.
    """
    kind = (ev.get("type") or "").lower()
    raw_result = ev.get("result") or ""
    if not isinstance(raw_result, str):
        raw_result = str(raw_result)

    # SEND → "Value=2.6" when we can parse the body
    if kind == "send":
        # Prefer explicit detail if it looks like a body; otherwise fall back to result
        src_text = ""
        detail_field = ev.get("detail")
        if isinstance(detail_field, str) and "value=" in detail_field:
            src_text = detail_field
        else:
            src_text = raw_result

        value_str = _extract_value_from_text(src_text) if src_text else None
        if value_str:
            return f"Value={value_str}"

        # Fallback: preserve old behavior but a bit more generous in width
        return "OK" if raw_result.upper() == "OK" or not raw_result else raw_result[:40]

    # SKIP → "Snooze 897s" style based on remaining seconds
    if kind == "skip":
        low = raw_result.lower()
        if "remaining=" in low:
            parts = low.split("remaining=", 1)
            if len(parts) == 2:
                rem = parts[1].split()[0]
                return f"Snooze {rem}"
        return "Snooze"

    # ERROR → compact, user-facing error label
    if kind == "error":
        detail = ev.get("detail") or ev.get("error") or raw_result
        if not isinstance(detail, str):
            detail = str(detail)
        low = detail.lower()
        if "twilio" in low and ("20003" in low or "authenticate" in low):
            return "twilio auth error"
        return detail[:40] if detail else "error"

    # Anything else: just show a truncated result string
    return str(raw_result)[:40] if raw_result else "-"


def _result_for_send(rec: Dict[str, Any]) -> str:
    summary = rec.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    res = rec.get("result")
    if isinstance(res, dict):
        if res.get("success") is False:
            return "FAIL"
        if res.get("success") is True:
            return "OK"
    return "OK"


def _result_for_skip(rec: Dict[str, Any]) -> str:
    reason = (rec.get("reason") or "-").upper()
    remaining = rec.get("remaining_seconds")
    minimum = rec.get("min_seconds")
    parts: List[str] = [reason]
    if remaining is not None:
        parts.append(f"remaining={int(remaining)}s")
    if minimum is not None:
        parts.append(f"min={int(minimum)}s")
    return " ".join(parts)


def _result_for_error(rec: Dict[str, Any]) -> str:
    reason = (rec.get("reason") or "-").upper()
    missing = rec.get("missing")
    if missing:
        try:
            detail = "missing=" + ", ".join(missing)
        except Exception:
            detail = f"missing={missing}"
    else:
        detail = str(rec.get("detail") or "").strip()
    return f"{reason} {detail}".strip()


def _build_attempt(kind: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    age_s = _compute_age_seconds(rec)
    when = _fmt_time_from_ts(rec.get("ts"))

    if kind == "send":
        result = _result_for_send(rec)
        ch_map = rec.get("channels") if isinstance(rec.get("channels"), dict) else {}
    elif kind == "skip":
        result = _result_for_skip(rec)
        ch_map = {}
    else:  # "error" or anything else
        result = _result_for_error(rec)
        ch_map = {}

    return {
        "type": kind,
        "age_s": age_s,
        "age": _fmt_age(age_s),
        "time": when,
        "result": result,
        "channels": ch_map,
        "monitor": rec.get("monitor"),
        "label": rec.get("label"),
        "detail": rec.get("detail"),
    }


def _recent_attempts_from_history(history: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for ev in history[:limit]:
        kind = (ev.get("type") or "").lower()
        age_s = _compute_age_seconds(ev)
        when = _fmt_time_from_ts(ev.get("ts"))
        events.append(
            {
                "type": kind,
                "age_s": age_s,
                "age": _fmt_age(age_s),
                "time": when,
                "result": ev.get("result"),
                "channels": ev.get("channels") or {},
                "monitor": ev.get("monitor"),
                "label": ev.get("label"),
                "detail": ev.get("detail"),
            }
        )
    return events


def _recent_attempts(
    rec_send: Optional[Dict[str, Any]],
    rec_skip: Optional[Dict[str, Any]],
    rec_err: Optional[Dict[str, Any]],
    dl: Any,
) -> List[Dict[str, Any]]:
    history = _get_history(dl) if dl else []
    if history:
        return _recent_attempts_from_history(history, limit=5)

    # Fallback to old behavior if history isn't present yet
    events: List[Dict[str, Any]] = []
    if rec_send:
        events.append(_build_attempt("send", rec_send))
    if rec_skip:
        events.append(_build_attempt("skip", rec_skip))
    if rec_err:
        events.append(_build_attempt("error", rec_err))
    events.sort(key=lambda e: e["age_s"])
    return events


# ───────────────────────── snooze / cooldown summaries ─────────────────────


def _snooze_summary(dl: Any, rec_skip: Optional[Dict[str, Any]]) -> str:
    remaining = None
    minimum = None

    if isinstance(rec_skip, dict):
        remaining = rec_skip.get("remaining_seconds")
        minimum = rec_skip.get("min_seconds")

    if remaining is None:
        try:
            rem, _ = read_snooze_remaining(dl)
            if rem > 0:
                remaining = rem
        except Exception:
            pass

    if remaining is None and minimum is None:
        return "Global Snooze: OFF"

    parts: List[str] = ["Global Snooze:"]
    if remaining is not None:
        parts.append(f"remaining={int(remaining)}s")
    if minimum is not None:
        parts.append(f"min={int(minimum)}s")
    return " ".join(parts)


def _cooldown_summary(dl: Any, cfg: Optional[Dict[str, Any]]) -> str:
    try:
        rem, _ = read_voice_cooldown_remaining(dl)
    except Exception:
        rem = 0

    try:
        default_cd = int(get_default_voice_cooldown(cfg or {}))
    except Exception:
        default_cd = 180

    if rem > 0:
        return f"Voice Cooldown: ACTIVE (remaining={int(rem)}s / window={default_cd}s)"
    return f"Voice Cooldown: idle (window={default_cd}s)"


# ───────────────────────── Rich table plumbing ─────────────────────────────


def _resolve_table_cfg(body_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve Rich table settings for the XCom panel.

    Defaults:
      • style: "thin" (SIMPLE_HEAD)
      • table/header justification: left
    """
    tcfg = (body_cfg or {}).get("table") or {}
    style = str(tcfg.get("style") or "").lower().strip() or "thin"
    table_justify = str(tcfg.get("table_justify") or "left").lower().strip()
    header_justify = str(tcfg.get("header_justify") or "left").lower().strip()
    return {
        "style": style,
        "table_justify": table_justify,
        "header_justify": header_justify,
    }


def _style_to_box(style: str):
    style = (style or "").lower()
    if style == "thin":
        return box.SIMPLE_HEAD, False
    if style == "thick":
        return box.HEAVY_HEAD, True
    # "invisible" or unknown → no borders
    return None, False


def _justify_lines(lines: List[str], justify: str, width: int) -> List[str]:
    """Apply table-level justification to rendered text lines."""
    justify = (justify or "left").lower()
    out: List[str] = []
    for line in lines:
        s = line.rstrip("\n")
        pad = max(0, width - len(s))
        if justify == "right":
            out.append(" " * pad + s)
        elif justify == "center":
            left = pad // 2
            out.append(" " * left + s)
        else:
            out.append(s)
    return out


def _is_rule_line(line: str) -> bool:
    """
    Return True if a line is just box-drawing/horizontal rule characters.

    Used so we can drop the header underline that Rich adds by default.
    """
    stripped = line.strip()
    if not stripped:
        return False
    chars = set(stripped)
    rule_chars = set("┌┐└┘├┤┬┴┼─━═╭╮╯╰╴╶╷╵╸╹╺╻╼╽╾╿+|")
    return chars <= rule_chars


def _build_attempts_table(attempts: List[Dict[str, Any]], body_cfg: Dict[str, Any]) -> List[str]:
    """
    Build a Rich table representing recent XCom attempts and export as text.

    We strip the header underline so only the header row + data rows remain.
    """
    table_cfg = _resolve_table_cfg(body_cfg)
    box_style, show_lines = _style_to_box(table_cfg["style"])

    table = Table(
        show_header=True,
        header_style="",
        show_lines=show_lines,
        box=box_style,
        pad_edge=False,
        expand=False,
    )

    # Column headers — no icons except '#'
    table.add_column("#", justify="right", no_wrap=True)
    table.add_column("Age", justify="right", no_wrap=True)
    table.add_column("Time", justify="left", no_wrap=True)
    table.add_column("Result", justify="left", no_wrap=True)
    table.add_column("Tgt", justify="left", no_wrap=True)
    table.add_column("Asset", justify="left", no_wrap=True)
    table.add_column("Details", justify="left")
    table.add_column("Channels", justify="left", no_wrap=True)

    for idx, ev in enumerate(attempts, 1):
        kind = (ev.get("type") or "").lower()
        # Normalized uppercase token for any non-send/skip types
        result_word = (kind or "-").upper()

        # Color the Result cell:
        #   SEND  → green
        #   SKIP  → yellow
        #   OTHER → red
        if kind == "send":
            result_cell = "[green]SEND[/]"
        elif kind == "skip":
            result_cell = "[yellow]SKIP[/]"
        else:
            result_cell = f"[red]{result_word or 'ERROR'}[/]"

        icon, symbol = _target_icon_and_symbol(ev)
        tgt_icon = icon or ""
        tgt_sym = symbol or ""

        details = _details_from_attempt(ev)

        ch_map = ev.get("channels") or {}
        if not isinstance(ch_map, dict):
            ch_map = {}
        sys_on = bool(ch_map.get("system"))
        voice_on = bool(ch_map.get("voice"))
        chan_data = (ch_map.get("sms") or {})
        if isinstance(chan_data, dict):
            sms_on = bool(chan_data.get("ok"))
        else:
            sms_on = bool(chan_data)
        tts_on = bool(ch_map.get("tts"))

        sys_col = "🖥" if sys_on else ""
        voice_col = "📞" if voice_on else ""
        sms_col = "💬" if sms_on else ""
        tts_col = "🔊" if tts_on else ""
        channels_icons = " ".join(icon for icon in (sys_col, voice_col, sms_col, tts_col) if icon)

        table.add_row(
            str(idx),
            str(ev.get("age", "–")),
            str(ev.get("time", "–")),
            result_cell,
            tgt_icon,
            tgt_sym,
            details,
            channels_icons,
        )

    buf = StringIO()
    console = Console(record=True, width=HR_WIDTH, file=buf, force_terminal=True)
    console.print(table)
    # IMPORTANT: keep styles so green/yellow/red survive
    text = console.export_text(styles=True).rstrip("\n")
    if not text:
        return []

    raw_lines = text.splitlines()

    # Drop leading/trailing blanks
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()

    # Remove pure rule lines (header underline, borders, if any)
    cleaned = [ln for ln in raw_lines if not _is_rule_line(ln)]

    return _justify_lines(cleaned, table_cfg["table_justify"], HR_WIDTH)


# ───────────────────────── render (console_panels style) ───────────────────


def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    """
    Accepted:
      render(ctx)
      render(dl, ctx)
      render(ctx, width)
    Returns a list of lines; console_reporter will print them.
    """
    # Normalize context to always have a dict with dl + cfg
    ctx: Dict[str, Any] = {}
    if isinstance(context, dict):
        ctx.update(context)
    else:
        ctx["dl"] = context

    dl = ctx.get("dl")
    cfg_obj = ctx.get("cfg") or ctx.get("config") or getattr(dl, "global_config", None)
    if not isinstance(cfg_obj, dict):
        cfg_obj = {}

    rec_send = _get_receipt(dl, "xcom_last_sent") if dl else None
    rec_skip = _get_receipt(dl, "xcom_last_skip") if dl else None
    rec_err = _get_receipt(dl, "xcom_last_error") if dl else None

    try:
        # cfg_obj is still passed so tests can inject their own FILE cfg; xcom_live_status
        # itself now prefers Oracle (source="ORACLE") for runtime.
        live_on, live_src = xcom_live_status(dl, cfg=cfg_obj)
    except Exception:
        live_on, live_src = False, "—"

    status_label = "🟢 LIVE" if live_on else "🔴 OFF"

    live_src_norm = (live_src or "").upper().strip()
    if live_src_norm == "ORACLE":
        src_display = "🧙 Oracle"
    else:
        src_display = live_src or "—"

    attempts = _recent_attempts(rec_send, rec_skip, rec_err, dl)
    snooze_line = _snooze_summary(dl, rec_skip) if dl else "Global Snooze: OFF"
    if dl:
        cooldown_line = _cooldown_summary(dl, cfg_obj)
    else:
        default_cd = get_default_voice_cooldown(cfg_obj)
        cooldown_line = f"Voice Cooldown: idle (window={int(default_cd)}s)"

    body_cfg = get_panel_body_config(PANEL_SLUG)
    out: List[str] = []

    # Title
    out += emit_title_block(PANEL_SLUG, PANEL_NAME)

    # Status line
    status_lines: List[str] = [
        f"  🛰 Status: {status_label}  [src={src_display}]",
    ]
    out += body_indent_lines(
        PANEL_SLUG,
        [color_if_plain(ln, body_cfg["body_text_color"]) for ln in status_lines],
    )
    out.append("")

    # Recent attempts table title (centered)
    header_text = "📡 Recent XCom Attempts"
    centered_title = _justify_lines([header_text], "center", HR_WIDTH)[0]
    out += body_indent_lines(
        PANEL_SLUG,
        [color_if_plain(centered_title, body_cfg["column_header_text_color"])],
    )

    if not attempts:
        out += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain("    (no recent send/skip/error receipts)", body_cfg["body_text_color"])],
        )
    else:
        table_lines = _build_attempts_table(attempts, body_cfg)
        if table_lines:
            header_line = table_lines[0]
            data_lines = table_lines[1:]

            # Header tinted with column_header_text_color
            out += body_indent_lines(
                PANEL_SLUG,
                [paint_line(header_line, body_cfg["column_header_text_color"])],
            )

            # Body lines with normal body_text_color (respecting inline ANSI)
            for ln in data_lines:
                out += body_indent_lines(
                    PANEL_SLUG,
                    [color_if_plain(ln, body_cfg["body_text_color"])],
                )
        else:
            out += body_indent_lines(
                PANEL_SLUG,
                [color_if_plain("    (no recent send/skip/error receipts)", body_cfg["body_text_color"])],
            )

    out.append("")

    # Snooze / cooldown block
    out += body_indent_lines(
        PANEL_SLUG,
        [color_if_plain("  🔕 Snooze / cooldown", body_cfg["column_header_text_color"])],
    )
    out += body_indent_lines(
        PANEL_SLUG,
        [
            color_if_plain(f"    {snooze_line}", body_cfg["body_text_color"]),
            color_if_plain(f"    {cooldown_line}", body_cfg["body_text_color"]),
        ],
    )

    out += body_pad_below(PANEL_SLUG)
    return out


def connector(*args, **kwargs) -> List[str]:
    """console_reporter prefers connector(); delegate to render()."""
    return render(*args, **kwargs)
