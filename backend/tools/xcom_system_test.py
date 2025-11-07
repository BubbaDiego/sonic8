# backend/tools/xcom_system_test.py
# Run:  python backend/tools/xcom_system_test.py [--monitor liquid] [--db <path>] [--config <path>] [--live]
# Default: STUB Twilio (no network). Use --live to attempt a real call.

from __future__ import annotations
import argparse, json, os, sys, time, types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

def _ensure_repo_on_path():
    here = Path(__file__).resolve()
    p = here.parent
    for _ in range(8):
        if (p / "backend").exists():
            sys.path.insert(0, str(p))
            return
        p = p.parent
_ensure_repo_on_path()

try:
    from backend.core.core_constants import MOTHER_DB_PATH
    from backend.core.logging import log
    from backend.data.data_locker import DataLocker
    from backend.core.xcom_core.dispatch import dispatch_voice_if_needed as dispatch_notifications
    from backend.core.xcom_core.xcom_config_service import XComConfigService
    from backend.core.reporting_core.sonic_reporting.xcom_extras import (
        xcom_ready,
        set_voice_cooldown,
        read_voice_cooldown_remaining,
        xcom_live_status,
    )
except Exception as exc:
    print(f"[FATAL] import error: {exc}")
    print("Hint: run from repo root or set PYTHONPATH to the repo root.")
    sys.exit(1)

# ---------- util ----------
def _load_json_config(config_path: Optional[str]) -> Dict[str, Any]:
    """
    Load the monitor JSON so readiness/channel checks match runtime.
    Defaults to backend/config/sonic_monitor_config.json if not provided.
    """
    if config_path:
        path = Path(config_path)
    else:
        # repo-root/backend/config/sonic_monitor_config.json
        root = Path(__file__).resolve().parents[2]
        path = root / "backend" / "config" / "sonic_monitor_config.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[WARN] Could not load config at {path}: {exc}")
        return {}

@dataclass
class CheckResult:
    name: str
    ok: bool
    details: Dict[str, Any] = field(default_factory=dict)
    skip: Optional[str] = None
    def line(self) -> str:
        state = "PASS" if self.ok else ("SKIP" if self.skip else "FAIL")
        return f"[{state}] {self.name} :: {self.details or self.skip or ''}"

class XComSystemTest:
    def __init__(self, monitor_name: str, db_path: Optional[str], config_path: Optional[str], live: bool):
        self.monitor_name = monitor_name
        self.db_path = db_path or MOTHER_DB_PATH
        self.live = live

        # DataLocker + load JSON into dl.global_config so probes reflect file state
        self.dl: DataLocker = DataLocker.get_instance(self.db_path)
        self.dl.global_config = _load_json_config(config_path)

        self.cfg = XComConfigService(getattr(self.dl, "system", None))
        self.stub_calls_count = 0
        self._twilio_stubbed = False

    # ---- Twilio stub ----
    def _install_twilio_stub(self):
        if self.live:
            return
        def _inc(*a, **k):
            self.stub_calls_count += 1
            return types.SimpleNamespace(sid="SIM-STUB")
        class _StubCalls:
            def create(self, *a, **k): return _inc(*a, **k)
        class _StubClient:
            def __init__(self, *a, **k): self.calls = _StubCalls()
        sys.modules["twilio"] = types.SimpleNamespace(rest=types.SimpleNamespace(Client=_StubClient))
        sys.modules["twilio.rest"] = sys.modules["twilio"].rest
        os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC_test")
        os.environ.setdefault("TWILIO_AUTH_TOKEN", "auth_test")
        os.environ.setdefault("TWILIO_PHONE_NUMBER", "+15550000001")
        os.environ.setdefault("MY_PHONE_NUMBER", "+15550000002")
        self._twilio_stubbed = True

    def _channels_for_monitor(self) -> Dict[str, bool]:
        ch = self.cfg.channels_for(self.monitor_name)
        for k in ("voice", "system", "sms", "tts"):
            ch.setdefault(k, False)
        return ch

    # ---- checks ----
    def check_config_sources(self) -> CheckResult:
        live, src = xcom_live_status(self.dl, getattr(self.dl, "global_config", None))
        ch = self._channels_for_monitor()
        details = {"xcom_live": bool(live), "source": src, "channels_for_monitor": ch}
        if not ch.get("voice", False):
            return CheckResult("Config: XCOM live + channels/monitor", ok=False, details=details,
                               skip="voice-disabled-for-monitor")
        return CheckResult("Config: XCOM live + channels/monitor", ok=bool(live), details=details)

    def check_readiness(self) -> CheckResult:
        ok, reason = xcom_ready(self.dl, cfg=getattr(self.dl, "global_config", None))  # <- fixed call
        return CheckResult("Readiness: xcom_ready()", ok=bool(ok), details={"reason": reason})

    def check_cooldown_idle(self) -> CheckResult:
        rem, src = read_voice_cooldown_remaining(self.dl)
        idle = (rem or 0) <= 1
        return CheckResult("Cooldown: idle", ok=idle, details={"remaining_s": rem, "source": src})

    def test_near_does_not_dispatch(self) -> CheckResult:
        self._install_twilio_stub()
        before = self.stub_calls_count
        out = dispatch_notifications(
            monitor_name=self.monitor_name,
            result={"breach": False, "summary": "near test"},
            channels=None,
            context={"subject": "[ut] near state", "body": "no call expected"},
        )
        v = (out.get("channels") or {}).get("voice", {})
        after = self.stub_calls_count
        ok = (v.get("ok") is False) and (after == before)
        return CheckResult("Near-state: no voice dispatch", ok=ok,
                           details={"channels": out.get("channels"), "stub_calls": {"before": before, "after": after}})

    def test_breach_dispatch(self) -> CheckResult:
        self._install_twilio_stub()
        try:
            set_voice_cooldown(self.dl, 0)
            time.sleep(0.05)
        except Exception:
            pass
        before = self.stub_calls_count
        out = dispatch_notifications(
            monitor_name=self.monitor_name,
            result={"breach": True, "summary": "breach: system test"},
            channels=None,
            context={"subject": "[ut] breach", "body": "system test"},
        )
        v = (out.get("channels") or {}).get("voice", {})
        after = self.stub_calls_count
        ok = ((after - before) == 1) if not self.live else bool(v.get("ok") is True)
        return CheckResult("Breach-state: voice dispatch", ok=ok,
                           details={"channels": out.get("channels"), "stub_calls": {"before": before, "after": after},
                                    "live": self.live})

    def test_cooldown_blocks_redial(self) -> CheckResult:
        self._install_twilio_stub()
        try:
            set_voice_cooldown(self.dl, 120)
            time.sleep(0.05)
        except Exception:
            return CheckResult("Cooldown: blocks re-dial", ok=False, skip="set_voice_cooldown-not-available")
        before = self.stub_calls_count
        out = dispatch_notifications(
            monitor_name=self.monitor_name,
            result={"breach": True, "summary": "cooldown test"},
            channels=None,
            context={"subject": "[ut] cooldown", "body": "no call expected"},
        )
        after = self.stub_calls_count
        v = (out.get("channels") or {}).get("voice", {})
        ok = (after == before) and (v.get("ok") is False)
        try:
            set_voice_cooldown(self.dl, 0)
        except Exception:
            pass
        return CheckResult("Cooldown: blocks re-dial", ok=ok,
                           details={"channels": out.get("channels"), "stub_calls": {"before": before, "after": after}})

    # ---- run ----
    def run(self) -> int:
        results: list[CheckResult] = []

        live, src = xcom_live_status(self.dl, getattr(self.dl, "global_config", None))
        print("=== XCOM System Test ===")
        print(f"Monitor         : {self.monitor_name}")
        print(f"DB path         : {self.db_path}")
        print(f"XCOM live       : {bool(live)} [{src}]")
        print(f"Mode            : {'LIVE (real Twilio)' if self.live else 'STUB (no network)'}")
        print("")

        r = self.check_config_sources(); results.append(r); print(r.line())
        if r.skip == "voice-disabled-for-monitor":
            print("  -> Voice disabled for this monitor in JSON. Enable channels.<monitor>.voice to test dispatch.")

        r = self.check_readiness(); results.append(r); print(r.line())
        r = self.check_cooldown_idle(); results.append(r); print(r.line())
        r = self.test_near_does_not_dispatch(); results.append(r); print(r.line())
        r = self.test_breach_dispatch(); results.append(r); print(r.line())
        r = self.test_cooldown_blocks_redial(); results.append(r); print(r.line())

        failures = [x for x in results if not x.ok and not x.skip]
        print("\n=== Summary ===")
        for x in results:
            print(" -", x.line())

        if failures:
            print("\n=== Detailed Failures ===")
            for x in failures:
                print(f"\n[{x.name}]")
                for k, v in (x.details or {"reason": "no details"}).items():
                    print(f"  {k}: {v}")

        return 1 if failures else 0

def main():
    ap = argparse.ArgumentParser(description="Standalone XCOM system test")
    ap.add_argument("--monitor", default="liquid", help="Monitor name to test (default: liquid)")
    ap.add_argument("--db", default=None, help="Path to mother DB (default: MOTHER_DB_PATH)")
    ap.add_argument("--config", default=None, help="Path to JSON (default: backend/config/sonic_monitor_config.json)")
    ap.add_argument("--live", action="store_true", help="Use real Twilio (no stub) if creds present")
    args = ap.parse_args()

    test = XComSystemTest(monitor_name=args.monitor, db_path=args.db, config_path=args.config, live=args.live)
    code = test.run()
    sys.exit(code)

if __name__ == "__main__":
    main()
