
import sys
import os
import json
from datetime import datetime, timezone
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

class XComCore:
    def __init__(self, dl_sys_data_manager):
        self.config_service = XComConfigService(dl_sys_data_manager)
        self.log = []

    def send_notification(
        self,
        level: str,
        subject: str,
        body: str,
        recipient: str = "",
        initiator: str = "system",
        mode: str | list[str] | None = None,
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

            # ---------------- EMAIL ---------------------------------------------------
            if "email" in requested:
                results["email"] = EmailService(email_cfg).send(recipient, subject, body)

            # ---------------- SMS -----------------------------------------------------
            if "sms" in requested:
                results["sms"] = SMSService(sms_cfg).send(recipient, body)

            # ---------------- VOICE ---------------------------------------------------
            if "voice" in requested:
                if allow_call:
                    voice_message = (
                        f"New High Priority Alert. "
                        f"Initiated by {initiator}. "
                        f"Subject: {subject}. "
                        f"Details: {body}."
                    )
                    ok, sid = VoiceService(voice_cfg).call(recipient, subject, voice_message)
                    results["voice"] = bool(ok)
                    if ok and sid:
                        results["twilio_sid"] = sid
                    elif sid:
                        results["twilio_error"] = sid
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
                results["tts"] = TTSService(
                    tts_cfg.get("voice"),
                    tts_cfg.get("speed"),
                ).send(recipient, body)

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
