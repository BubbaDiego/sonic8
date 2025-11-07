# xcom_bridge.py content (see above block)
from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
from backend.core.logging import log
from backend.data.data_locker import DataLocker
from backend.core.xcom_core.dispatch import dispatch_voice_if_needed as dispatch_notifications
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_ready
def _extract_liquid_hit(csum: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if not isinstance(csum, dict):
        return False, None
    buckets = ("monitors", "monitor_results", "results", "data")
    for bucket in buckets:
        section = csum.get(bucket)
        if not isinstance(section, dict):
            continue
        liquid = section.get("liquid")
        if isinstance(liquid, dict):
            if liquid.get("breach") is True:
                summary = liquid.get("summary") or liquid.get("message") or "Liquid breach detected"
                return True, summary
            for items_key in ("assets", "rows", "items", "symbols"):
                items = liquid.get(items_key)
                if isinstance(items, dict):
                    iterator = items.values()
                elif isinstance(items, list):
                    iterator = items
                else:
                    continue
                for row in iterator:
                    if not isinstance(row, dict):
                        continue
                    if row.get("breach") is True:
                        txt = row.get("summary") or row.get("message")
                        if not txt:
                            asset = row.get("asset") or row.get("symbol") or ""
                            txt = f"{asset} breach"
                        return True, txt
                    v = row.get("value")
                    thr = row.get("threshold")
                    if isinstance(v, (int, float)) and isinstance(thr, (int, float)):
                        if v <= thr:
                            asset = row.get("asset") or row.get("symbol") or ""
                            txt = f"{asset} {v} ≤ {thr}".strip()
                            return True, txt
    return False, None
def bridge_dispatch_from_tables(dl: DataLocker, csum: Dict[str, Any]) -> Dict[str, Any]:
    cfg = XComConfigService(getattr(dl, "system", None))
    voice_enabled_for_liquid = bool(cfg.channels_for("liquid").get("voice", False))
    if not voice_enabled_for_liquid:
        log.debug("XCOM bridge: voice not enabled for 'liquid' per JSON — skipping", source="xcom_bridge")
        return {"ok": False, "skip": "voice-disabled-for-liquid"}
    ok_ready, reason = xcom_ready(dl, cfg=getattr(dl, "global_config", None))
    if not ok_ready:
        log.debug("XCOM bridge: not ready — skipping", source="xcom_bridge", payload={"reason": str(reason)})
        return {"ok": False, "skip": str(reason or "xcom-not-ready")}
    breach, summary = _extract_liquid_hit(csum)
    if not breach:
        return {"ok": False, "skip": "no-breach"}
    subject = f"[liquid] alert"
    body = summary or "Liquid threshold breached"
    out = dispatch_notifications(
        monitor_name="liquid",
        result={"breach": True, "summary": summary or ""},
        channels=None,
        context={"subject": subject, "body": body},
    )
    log.debug("XCOM bridge dispatched", source="xcom_bridge",
      payload={"breach": True, "success": out.get("success"), "channels": out.get("channels", {})})
    return {"ok": bool(out.get("success")), "channels": out.get("channels", {})}
