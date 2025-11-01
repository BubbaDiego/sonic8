
import sys
import os
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.xcom_core.email_service import EmailService
from backend.core.xcom_core.sms_service import SMSService
from backend.core.xcom_core.voice_service import VoiceService
from backend.core.xcom_core.sound_service import SoundService
from backend.core.xcom_core.tts_service import TTSService
from backend.core.xcom_core.alexa_service import AlexaService
from backend.data.data_locker import DataLocker
from core.core_constants import MOTHER_DB_PATH
from data.dl_monitor_ledger import DLMonitorLedgerManager
from backend.core.logging import log


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_mode(mode: Mapping[str, Any] | Sequence[str] | str | None) -> dict[str, bool]:
    """Normalise ``mode`` inputs into a consistent channel map."""

    normalized = {"voice": False, "system": False, "sms": False, "tts": False}
    if mode is None:
        return normalized

    if isinstance(mode, Mapping):
        for key, value in mode.items():
            key_lower = str(key).lower()
            if key_lower in normalized:
                normalized[key_lower] = bool(value)
        return normalized

    if isinstance(mode, str):
        items = [part.strip().lower() for part in mode.split(",") if part.strip()]
    else:
        items = [str(part).strip().lower() for part in mode if str(part).strip()]

    for name in normalized:
        normalized[name] = name in items
    return normalized


def _derive_level(explicit_level: str | None, requested_channels: Sequence[str]) -> str:
    if explicit_level:
        level = explicit_level.strip().upper()
        if level in {"LOW", "MEDIUM", "HIGH"}:
            return level

    requested = {channel.lower() for channel in requested_channels}
    if "voice" in requested:
        return "HIGH"
    if "sms" in requested:
        return "MEDIUM"
    return "LOW"


def _mode_sequence(channel_map: Mapping[str, bool]) -> list[str] | None:
    order = ("voice", "sms", "tts", "system")
    sequence = [name for name in order if channel_map.get(name, False)]
    return sequence or None


def _build_channel_summary(
    channel_map: Mapping[str, bool],
    results: Mapping[str, Any],
    voice_block_reason: str | None,
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}

    voice_enabled = channel_map.get("voice", False)
    if voice_block_reason and not voice_enabled:
        summary["voice"] = {"ok": False, "skip": voice_block_reason}
    elif voice_enabled:
        ok = bool(results.get("voice")) or bool(results.get("voice_ok", False))
        entry: dict[str, Any] = {"ok": ok}
        if not ok:
            suppressed = results.get("voice_suppressed")
            if isinstance(suppressed, Mapping):
                entry["skip"] = suppressed.get("reason", "suppressed")
            elif suppressed:
                entry["skip"] = "suppressed"
            elif results.get("twilio_error"):
                entry["skip"] = "twilio_error"
        summary["voice"] = entry
    else:
        summary["voice"] = {"ok": False, "skip": "disabled"}

    system_enabled = channel_map.get("system", False)
    summary["system"] = {"ok": True} if system_enabled else {"ok": False, "skip": "disabled"}

    for name in ("sms", "tts"):
        if channel_map.get(name, False):
            summary[name] = {"ok": bool(results.get(name))}
        else:
            summary[name] = {"ok": False, "skip": "disabled"}

    return summary


def _requested_channels(channel_map: Mapping[str, bool]) -> list[str]:
    return [name for name, enabled in channel_map.items() if enabled]


def dispatch_notifications(
    *,
    monitor_name: str,
    result: Mapping[str, Any] | None = None,
    channels: Mapping[str, Any] | Sequence[str] | str | None = None,
    context: Mapping[str, Any] | None = None,
    db_path: str | None = None,
    core: "XComCore" | None = None,
) -> dict[str, Any]:
    """Consolidated dispatcher shared by the console and legacy core."""

    context = dict(context or {})
    result = dict(result or {})

    channel_map = _normalize_mode(channels)
    breach = bool(result.get("breach", False))
    voice_requested = channel_map.get("voice", False)
    voice_block_reason = None
    if voice_requested and not breach:
        channel_map["voice"] = False
        voice_block_reason = "breach_gate"

    requested = _requested_channels(channel_map)
    level = _derive_level(result.get("level") or context.get("level"), requested)

    subject = context.get("subject") or f"[{monitor_name}] {level.title()} alert"
    body = context.get("body") or result.get("message") or ""
    recipient = context.get("recipient") or ""
    initiator = context.get("initiator") or monitor_name
    ignore_cooldown = bool(context.get("ignore_cooldown", False))

    locker = DataLocker.get_instance(str(db_path or MOTHER_DB_PATH))
    xcom = core if core is not None else XComCore(locker.system)

    log.debug(
        "Dispatching XCom notification",
        source="dispatch_notifications",
        payload={
            "monitor": monitor_name,
            "level": level,
            "channels": requested or ["auto"],
            "breach": breach,
        },
    )

    mode = _mode_sequence(channel_map)
    results = xcom._legacy_send_notification(
        level=level,
        subject=subject,
        body=body,
        recipient=recipient,
        initiator=initiator,
        mode=mode,
        ignore_cooldown=ignore_cooldown,
        breach=breach,
    )

    if voice_block_reason and voice_requested:
        results.setdefault("voice_suppressed", {"reason": voice_block_reason})

    summary = {
        "monitor": monitor_name,
        "breach": breach,
        "requested_channels": requested,
        "level": level,
        "subject": subject,
        "success": bool(results.get("success")),
        "results": results,
        "context": context,
        "result": result,
    }
    summary["channels"] = _build_channel_summary(channel_map, results, voice_block_reason)

    log.debug(
        "XCom dispatch completed",
        source="dispatch_notifications",
        payload={"monitor": monitor_name, "success": summary["success"]},
    )

    return summary

class XComCore:
    def __init__(self, dl_sys_data_manager):
        self.config_service = XComConfigService(dl_sys_data_manager)
        self.log = []

    def _legacy_send_notification(
        self,
        level: str,
        subject: str,
        body: str,
        recipient: str = "",
        initiator: str = "system",
        mode: str | list[str] | None = None,
        ignore_cooldown: bool = False,
        **kwargs,
    ):
        email_cfg = self.config_service.get_provider("email") or {}
        sms_cfg = self.config_service.get_provider("sms") or {}
        voice_cfg = self.config_service.get_provider("api") or {}
        tts_cfg = self.config_service.get_provider("tts") or {}
        alexa_cfg = self.config_service.get_provider("alexa") or {}

        results = {
            "email": False,
            "sms": False,
            "voice": False,
            "sound": None,
            "tts": False,
            "alexa": False,
        }
        error_msg = None

        # ------------------------------------------------------------------ #
        # Determine which channels the caller wants
        # ------------------------------------------------------------------ #

        if mode is None:
            # Legacy fan-out behaviour based purely on *level*
            if level == "HIGH":
                requested = {"sms", "voice"}
            elif level == "MEDIUM":
                requested = {"sms"}
            else:
                requested = {"email"}
        else:
            # Caller specified exactly which channel(s) to use
            requested = (
                {mode.lower()} if isinstance(mode, str) else {m.lower() for m in mode}
            )

        dl_instance = None

        try:
            system_mgr = self.config_service.dl_sys
            relax_seconds = 0
            last_call = None
            if hasattr(system_mgr, "get_var"):
                try:
                    val = system_mgr.get_var("phone_relax_period")
                    relax_seconds = int(val) if val is not None else 0
                except Exception:
                    relax_seconds = 0
                last_call = system_mgr.get_var("phone_last_call")

            allow_call = True
            if last_call and relax_seconds > 0:
                try:
                    last_dt = datetime.fromisoformat(last_call)
                    if (datetime.utcnow() - last_dt).total_seconds() < relax_seconds:
                        allow_call = False
                except Exception:
                    allow_call = True

            if (
                level == "HIGH"
                and not allow_call
                and initiator == "api_test"
                and ignore_cooldown
            ):
                allow_call = True

            # ---------------- EMAIL ---------------------------------------------------
            if "email" in requested:
                results["email"] = EmailService(email_cfg).send(recipient, subject, body)

            # ---------------- SMS -----------------------------------------------------
            if "sms" in requested:
                results["sms"] = SMSService(sms_cfg).send(recipient, body)

            # ---------------- VOICE ---------------------------------------------------
            if "voice" in requested:
                if allow_call:
                    # If the provider says to speak plain, or we're running a direct console/API test,
                    # skip the pre-roll and speak exactly the user-supplied body.
                    speak_plain = _as_bool(voice_cfg.get("speak_plain")) or initiator in {"xcom_console", "api_test"}
                    voice_message = (
                        (body or subject or "")
                        if speak_plain
                        else (
                            f"New High Priority Alert. "
                            f"Initiated by {initiator}. "
                            f"Subject: {subject}. "
                            f"Details: {body}."
                        )
                    )
                    if dl_instance is None:
                        try:
                            dl_instance = DataLocker.get_instance()
                        except Exception:
                            dl_instance = None
                    ok, sid, to_num, from_num = VoiceService(voice_cfg).call(
                        recipient,
                        subject,
                        voice_message,
                        dl=dl_instance,
                    )
                    results["voice"] = bool(ok)
                    if ok and sid:
                        results["twilio_sid"] = sid
                    elif sid:
                        results["twilio_error"] = sid
                    if to_num:
                        results["to_number"] = to_num
                    if from_num:
                        results["from_number"] = from_num
                    if results["voice"] and hasattr(system_mgr, "set_var"):
                        try:
                            system_mgr.set_var(
                                "phone_last_call", datetime.utcnow().isoformat()
                            )
                        except Exception:
                            pass
                    if results["voice"]:
                        try:
                            dl = DataLocker.get_instance()
                            cfg = dl.system.get_var("liquid_monitor") or {}
                            cfg["_last_alert_ts"] = datetime.now(timezone.utc).timestamp()
                            dl.system.set_var("liquid_monitor", cfg)
                        except Exception:
                            pass
                else:
                    log.info(
                        "Voice call suppressed by phone relax period",
                        source="XComCore",
                    )

            # ---------------- TTS  ----------------------------------------------------
            if "tts" in requested and tts_cfg.get("enabled", False):
                if dl_instance is None:
                    try:
                        dl_instance = DataLocker.get_instance()
                    except Exception:
                        dl_instance = None
                results["tts"] = TTSService(
                    tts_cfg.get("voice"),
                    tts_cfg.get("speed"),
                ).send(recipient, body, dl=dl_instance)

            if "alexa" in requested:
                alexa_message = f"{subject}. {body}"
                results["alexa"] = AlexaService(alexa_cfg).send(alexa_message)

            log.success(f"✅ Notification dispatched [{level}]", source="XComCore", payload=results)

        except Exception as e:
            error_msg = str(e)
            results["error"] = error_msg
            log.error(f"❌ Failed to send XCom notification: {e}", source="XComCore")

        self.log.append({
            "level": level,
            "subject": subject,
            "initiator": initiator,
            "recipient": recipient,
            "body": body,
            "results": results
        })

        # ------------------------------------------------------------------ #
        # Persist a row even if no provider succeeds
        # ------------------------------------------------------------------ #
        success_channels = [
            bool(results.get("email")),
            bool(results.get("sms")),
            bool(results.get("voice")),
            bool(results.get("sound")),
            bool(results.get("tts")),
            bool(results.get("alexa")),
        ]
        success = error_msg is None and any(success_channels)

        comm_type = ",".join(
            [k for k in ("email", "sms", "voice", "sound", "tts", "alexa") if results.get(k)]
        ) or "system"

        dl = DataLocker.get_instance()
        try:
            dl.notifications.insert(
                monitor="xcom_monitor",
                level=level,
                subject=subject,
                body=body,
                metadata={"initiator": initiator, "comm_type": comm_type},
            )
        except Exception as e:
            log.error(f"🧨 Failed to write notification: {e}", source="XComCore")

        try:
            ledger = DLMonitorLedgerManager(dl.db)
            
            metadata = {
                "level": level,
                "subject": subject,
                "initiator": initiator,
                "recipient": recipient,
                "results": results
            }
            ledger.insert_ledger_entry(
                "xcom_monitor",
                "Success" if success else "Error",
                metadata,
            )

        except Exception as e:
            log.error(f"🧨 Failed to write xcom_monitor ledger: {e}", source="XComCore")

        results["success"] = success
        return results

    def send_notification(
        self,
        level: str,
        subject: str,
        body: str,
        recipient: str = "",
        initiator: str = "system",
        mode: str | list[str] | None = None,
        ignore_cooldown: bool = False,
        **kwargs,
    ):
        channels = _normalize_mode(mode)
        breach = bool(kwargs.get("breach", channels.get("voice", False)))
        monitor_name = str(kwargs.get("monitor", "console"))

        context = dict(kwargs.get("context") or {})
        context.setdefault("subject", subject)
        context.setdefault("body", body)
        context.setdefault("initiator", initiator)
        context.setdefault("recipient", recipient)
        if ignore_cooldown:
            context.setdefault("ignore_cooldown", True)

        summary = dispatch_notifications(
            monitor_name=monitor_name,
            result={"breach": breach, "level": level, "message": body},
            channels=channels,
            context=context,
            db_path=kwargs.get("db_path"),
            core=self,
        )

        return summary.get("results", {})

def get_latest_xcom_monitor_entry(data_locker):
    ledger_mgr = data_locker.monitor_ledger if hasattr(data_locker, "monitor_ledger") else data_locker.ledger
    entry = ledger_mgr.get_last_entry("xcom_monitor")
    if not entry:
        return {
            "comm_type": "system",
            "source": "system",
            "timestamp": "—"
        }
    meta = entry.get("metadata")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    results = meta.get("results", {}) or {}
    comm_types = [("sms", "sms"), ("voice", "voice"), ("email", "email"), ("sound", "sound"), ("tts", "tts"), ("alexa", "alexa")]
    comm_type = "system"
    for key, value in comm_types:
        if results.get(key):
            comm_type = key
            break
    if comm_type == "system" and meta.get("level", "").lower() == "high":
        comm_type = "alert"
    subject = (meta.get("subject") or "").lower()
    if "alert" in subject:
        source = "alert"
    elif "user" in subject:
        source = "user"
    elif "operations" in subject or "op" in subject:
        source = "operations"
    else:
        source = "system"
    ts = entry.get("timestamp")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
        if dt:
            ts = dt.strftime("%-I:%M %p").replace(" 0", " ")  # e.g. "3:58 PM"
    except Exception:
        pass
    return {
        "comm_type": comm_type,
        "source": source,
        "timestamp": ts or "—"
    }
