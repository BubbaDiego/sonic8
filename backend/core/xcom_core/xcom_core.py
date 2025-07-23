
import sys
import os
import json
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.xcom_core.email_service import EmailService
from backend.core.xcom_core.sms_service import SMSService
from backend.core.xcom_core.voice_service import VoiceService
from backend.core.xcom_core.sound_service import SoundService
from backend.data.data_locker import DataLocker
from backend.core.logging import log
from backend.core.notification_service import NotificationService

class XComCore:
    def __init__(self, dl_sys_data_manager):
        self.config_service = XComConfigService(dl_sys_data_manager)
        self.log = []

    def send_notification(
            self, level: str, subject: str, body: str, recipient: str = "",
            initiator: str = "system"
    ):
        email_cfg = self.config_service.get_provider("email") or {}
        sms_cfg = self.config_service.get_provider("sms") or {}
        voice_cfg = self.config_service.get_provider("api") or {}

        results = {"email": False, "sms": False, "voice": False, "sound": None}
        error_msg = None

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

            if level == "HIGH":
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                voice_message = (
                    f"New High Priority Alert received at {timestamp}. "
                    f"Initiated by {initiator}. "
                    f"Subject: {subject}. "
                    f"Details: {body}."
                )
                results["sms"] = SMSService(sms_cfg).send(recipient, body)
                if allow_call:
                    results["voice"] = VoiceService(voice_cfg).call(recipient, voice_message)
                    if results["voice"] and hasattr(system_mgr, "set_var"):
                        try:
                            system_mgr.set_var("phone_last_call", datetime.utcnow().isoformat())
                        except Exception:
                            pass
                else:
                    log.info("Voice call suppressed by phone relax period", source="XComCore")
            elif level == "MEDIUM":
                results["sms"] = SMSService(sms_cfg).send(recipient, body)
            else:
                results["email"] = EmailService(email_cfg).send(recipient, subject, body)

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

        success = any(v is True for v in results.values()) and error_msg is None

        if success:
            try:
                dl = DataLocker.get_instance()
                comm_type = ",".join(
                    [k for k in ("email", "sms", "voice", "sound") if results.get(k)]
                )
                NotificationService(dl.db).insert(
                    level=level,
                    subject=subject,
                    body=body,
                    initiator=initiator,
                    comm_type=comm_type,
                )
            except Exception as e:  # pragma: no cover - best effort
                log.error(f"🧨 Failed to write notification: {e}", source="XComCore")

        try:
            from data.data_locker import DataLocker
            from core.constants import MOTHER_DB_PATH
            from data.dl_monitor_ledger import DLMonitorLedgerManager

            dl = DataLocker(MOTHER_DB_PATH)
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
    comm_types = [("sms", "sms"), ("voice", "voice"), ("email", "email"), ("sound", "sound")]
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
