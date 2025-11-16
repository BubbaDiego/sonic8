# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
from datetime import datetime

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_above,
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


def _target_from_rec(rec: Dict[str, Any]) -> str:
    """
    Backwards compatible helper returning "icon symbol" or just text.
    """
    icon, text = _target_icon_and_symbol(rec)
    return f"{icon} {text}" if icon else text


def _channels_from_attempt(ev: Dict[str, Any]) -> str:
    """
    Older helper (still used by other panels): concatenated channel icons.
    For the XCom table we use separate Sys/Voice/SMS/TTS columns instead.
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


def _details_from_attempt(ev: Dict[str, Any]) -> str:
    """
    Short detail string for the Details column.

    Keeps output concise so the table doesn't thrash.
    """
    kind = (ev.get("type") or "").lower()
    raw_result = ev.get("result") or ""
    if not isinstance(raw_result, str):
        raw_result = str(raw_result)

    if kind == "send":
        return "OK" if raw_result.upper() == "OK" or not raw_result else str(raw_result)[:20]
    if kind == "skip":
        if "snooze" in raw_result.lower():
            parts = raw_result.split("remaining=", 1)
            if len(parts) == 2:
                rem = parts[1].split()[0]
                return f"snooze {rem}"
        return "snooze"
    if kind == "error":
        low = raw_result.lower()
        if "auth" in low or "authenticate" in low:
            return "auth error"
        return "error" if not raw_result else str(raw_result)[:20]

    return str(raw_result)[:20] if raw_result else "-"


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
    else:  # "error"
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
    }


def _recent_attempts(
    rec_send: Optional[Dict[str, Any]],
    rec_skip: Optional[Dict[str, Any]],
    rec_err: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build a small list of recent attempts from the last send/skip/error receipts."""
    events: List[Dict[str, Any]] = []
    if rec_send:
        events.append(_build_attempt("send", rec_send))
    if rec_skip:
        events.append(_build_attempt("skip", rec_skip))
    if rec_err:
        events.append(_build_attempt("error", rec_err))
    # Sort by age ascending → newest first
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
        return "global snooze: OFF"

    parts: List[str] = ["global snooze:"]
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
        return f"voice cooldown: ACTIVE (remaining={int(rem)}s / window={default_cd}s)"
    return f"voice cooldown: idle (window={default_cd}s)"


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
        live_on, live_src = xcom_live_status(dl, cfg=cfg_obj)
    except Exception:
        live_on, live_src = False, "—"

    status_label = "🟢 LIVE" if live_on else "🔴 OFF"

    attempts = _recent_attempts(rec_send, rec_skip, rec_err)
    snooze_line = _snooze_summary(dl, rec_skip) if dl else "global snooze: OFF"
    cooldown_line = _cooldown_summary(dl, cfg_obj) if dl else "voice cooldown: idle (window=180s)"

    body_cfg = get_panel_body_config(PANEL_SLUG)
    out: List[str] = []

    # Title
    out += emit_title_block(PANEL_SLUG, PANEL_NAME)

    # Status lines
    status_lines: List[str] = []
    status_lines.append(f"  🛰 Status: {status_label}  [src={live_src}]")
    # No “last attempt / last error” summary line anymore –
    # the recent attempts table is the single source of truth.

    out += body_indent_lines(
        PANEL_SLUG,
        [color_if_plain(ln, body_cfg["body_text_color"]) for ln in status_lines],
    )
    out.append("")

    # Recent attempts table
    out += body_indent_lines(
        PANEL_SLUG,
        [color_if_plain("  📡 Recent XCom attempts (latest first)", body_cfg["column_header_text_color"])],
    )

    if not attempts:
        out += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain("    (no recent send/skip/error receipts)", body_cfg["body_text_color"])],
        )
    else:
        # Draw a thin ASCII table around the values so we can see column boundaries
        border = "    +----+------+--------+---------+-----+--------+------------+-----------------------+"
        header = (
            "    | #  | Age  | Time   | Result  | Tgt | Symbol | Details    | Channels              |"
        )

        out += body_indent_lines(
            PANEL_SLUG,
            [
                color_if_plain(border, body_cfg["column_header_text_color"]),
                color_if_plain(header, body_cfg["column_header_text_color"]),
                color_if_plain(border, body_cfg["column_header_text_color"]),
            ],
        )

        rows: List[str] = []
        base_color = body_cfg["body_text_color"]

        for idx, ev in enumerate(attempts, 1):
            num = f"{idx:<2}"
            age = f"{ev.get('age', '–'):<4}"
            when = f"{ev.get('time', '–'):<6}"
            kind = (ev.get("type") or "").lower()
            result_word = kind or "-"

            # Split target into icon + symbol
            icon, symbol = (
                _target_icon_and_symbol(ev)
                if "_target_icon_and_symbol" in globals()
                else ("", _target_from_rec(ev))
            )
            tgt_icon = icon or ""
            tgt_sym = symbol or ""

            details = _details_from_attempt(ev)

            # Break channels into 4 booleans
            ch_map = ev.get("channels") or {}
            if not isinstance(ch_map, dict):
                ch_map = {}
            sys_on = bool(ch_map.get("system"))
            voice_on = bool(ch_map.get("voice"))
            sms_on = bool(ch_map.get("sms"))
            tts_on = bool(ch_map.get("tts"))

            sys_col = "🖥" if sys_on else ""
            voice_col = "📞" if voice_on else ""
            sms_col = "💬" if sms_on else ""
            tts_col = "🔊" if tts_on else ""

            # Build a single Channels cell with only the enabled icons
            channels_icons = " ".join(
                icon
                for icon in (sys_col, voice_col, sms_col, tts_col)
                if icon
            )
            if not channels_icons:
                channels_icons = ""

            # Color for the result word only
            if kind == "error":
                result_color = "red"
            elif kind == "send":
                result_color = "green"
            else:
                result_color = base_color

            # Build the row pieces — all cells left-justified
            prefix = f"    | {num:<2} | {age:<4} | {when:<6} | "
            suffix = (
                f"| {tgt_icon:<3} | {tgt_sym:<6} | {details:<10} "
                f"| {channels_icons:<21} |"
            )

            colored_result = paint_line(f"{result_word:<7}", result_color)

            full_line = (
                color_if_plain(prefix, base_color)
                + colored_result
                + " "
                + color_if_plain(suffix, base_color)
            )
            rows.append(full_line)

        # Add bottom border
        rows.append(color_if_plain(border, body_cfg["column_header_text_color"]))

        out += body_indent_lines(PANEL_SLUG, rows)

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
