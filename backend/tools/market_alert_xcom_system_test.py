# backend/tools/market_alert_xcom_system_test.py
# Run:
#   python backend/tools/market_alert_xcom_system_test.py [--asset SOL] [--db <path>] [--live]
#
# Default: Twilio STUB (no network). Use --live to hit real Twilio if creds are valid.

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import types
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── Path bootstrap (same pattern as xcom_system_test) ──────────────────────────


def _ensure_repo_on_path() -> None:
    here = Path(__file__).resolve()
    p = here.parent
    for _ in range(8):
        if (p / "backend").exists():
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
            return
        p = p.parent


_ensure_repo_on_path()

# ─── Imports from the repo ──────────────────────────────────────────────────────

try:
    from backend.core.core_constants import MOTHER_DB_PATH, SONIC_MONITOR_CONFIG_PATH
    from backend.data.data_locker import DataLocker
    from backend.core.market_core.market_engine import evaluate_market_alerts
    from backend.models.price_alert import PriceAlert
    from backend.models.monitor_status import MonitorStatus
    from backend.core.monitor_core.xcom_bridge import dispatch_breaches_from_dl
    from backend.core.xcom_core.xcom_config_service import XComConfigService
    from backend.core.reporting_core.sonic_reporting.xcom_extras import (
        xcom_ready,
        xcom_live_status,
        set_voice_cooldown,
        read_voice_cooldown_remaining,
    )
    from backend.core.reporting_core.sonic_reporting.console_panels import (
        monitor_panel as monitor_panel_mod,
        market_panel as market_panel_mod,
        xcom_panel as xcom_panel_mod,
    )
except Exception as exc:  # pragma: no cover
    print(f"[FATAL] import error: {exc}")
    print("Hint: run from repo root or ensure PYTHONPATH includes the repo root.")
    sys.exit(1)

# ─── Helpers & dataclasses ──────────────────────────────────────────────────────


def _load_json_config(path: Optional[str]) -> Dict[str, Any]:
    """
    Load sonic_monitor_config.json so XCom and channel resolution match runtime.
    Defaults to backend/config/sonic_monitor_config.json if not provided.
    """
    if path:
        cfg_path = Path(path)
    else:
        cfg_path = SONIC_MONITOR_CONFIG_PATH
    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as exc:
        print(f"[WARN] Could not load monitor config at {cfg_path}: {exc}")
        return {}


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: Dict[str, Any] = field(default_factory=dict)
    skip: Optional[str] = None

    def line(self) -> str:
        state = "PASS" if self.ok else ("SKIP" if self.skip else "FAIL")
        extra = self.skip or self.details or ""
        return f"[{state}] {self.name} :: {extra}"


@dataclass
class MarketTestConfig:
    asset: str = "SOL"
    base_price: float = 100.0
    step: float = 10.0
    threshold: float = 5.0
    recurrence_mode: str = "reset"  # "reset" or "ladder"


class MarketXComSystemTest:
    """
    End-to-end system test:

      PriceAlert (Market) → evaluate_market_alerts →
      MonitorStatus/monitors + dl_monitors →
      XCom bridge → xcom_history/xcom_last_sent →
      console panels (Monitors, Market Alerts, XCom)
    """

    def __init__(
        self,
        *,
        asset: str,
        db_path: Optional[str],
        config_path: Optional[str],
        live: bool,
    ) -> None:
        self.cfg = MarketTestConfig(asset=asset)
        self.db_path = db_path or str(MOTHER_DB_PATH)
        self.live = bool(live)

        # DataLocker singleton, share DB with the rest of Sonic
        self.dl: DataLocker = DataLocker.get_instance(self.db_path)
        self.dl.global_config = _load_json_config(config_path)

        # XCom config service (for channels_for("market"))
        self.xcfg = XComConfigService(getattr(self.dl, "system", None))
        self.stub_calls_count = 0
        self._twilio_stubbed = False

    # ── Twilio stub (borrowed from xcom_system_test) ────────────────────────────

    def _install_twilio_stub(self) -> None:
        if self.live or self._twilio_stubbed:
            return

        def _inc(*_a, **_k):
            self.stub_calls_count += 1
            return types.SimpleNamespace(sid="SIM-STUB")

        class _StubCalls:
            def create(self, *a, **k):
                return _inc(*a, **k)

        class _StubClient:
            def __init__(self, *a, **k):
                self.calls = _StubCalls()

        # Patch twilio client modules
        sys.modules["twilio"] = types.SimpleNamespace(
            rest=types.SimpleNamespace(Client=_StubClient)
        )
        sys.modules["twilio.rest"] = sys.modules["twilio"].rest

        # Seed env so ConfigOracle.get_xcom_twilio_secrets() sees something.
        os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC_test")
        os.environ.setdefault("TWILIO_AUTH_TOKEN", "auth_test")
        os.environ.setdefault("TWILIO_PHONE_NUMBER", "+15550000001")
        os.environ.setdefault("MY_PHONE_NUMBER", "+15550000002")

        self._twilio_stubbed = True

    # ── Small helpers ──────────────────────────────────────────────────────────

    def _channels_for_market(self) -> Dict[str, bool]:
        ch = self.xcfg.channels_for("market")
        for k in ("system", "voice", "sms", "tts"):
            ch.setdefault(k, False)
        return ch

    def _ensure_market_alert(self) -> None:
        """Delete any existing alerts for this asset and create a fresh re-arming alert."""
        alerts = self.dl.price_alerts.list_alerts(self.cfg.asset)
        for a in alerts:
            if a.id is not None:
                self.dl.price_alerts.delete_alert(a.id)

        alert = PriceAlert(
            asset=self.cfg.asset,
            label=f"{self.cfg.asset} system-test",
            rule_type="move_abs",
            direction="both",
            base_threshold_value=self.cfg.threshold,
            recurrence_mode=self.cfg.recurrence_mode,
            enabled=True,
        )
        self.dl.price_alerts.save_alert(alert)

    def _set_price(self, price: float, source: str = "market-system-test") -> None:
        """Insert/overwrite a price row for the test asset."""
        self.dl.insert_or_update_price(self.cfg.asset, price, source=source)

    def _run_market_eval(self, price: float) -> Dict[str, Any]:
        out = evaluate_market_alerts(self.dl, {self.cfg.asset: price})
        return out

    def _update_monitors_bus(self, statuses: List[Dict[str, Any]], cycle_tag: str) -> None:
        """
        Mimic the Sonic engine's monitor-status behavior enough for panels + XCom:
          - Persist MonitorStatus rows to DB.
          - Expose an in-memory `rows` bus for dl.monitors (for the Monitors panel).
        """
        if not statuses:
            setattr(self.dl.monitors, "rows", [])
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        ms_rows: List[MonitorStatus] = []
        bus_rows: List[Dict[str, Any]] = []

        for item in statuses:
            if not isinstance(item, dict):
                continue
            ms = MonitorStatus.from_status_dict(
                cycle_id=cycle_tag,
                monitor="market",
                item=item,
                default_label="market",
                now_iso=now_iso,
                default_source=item.get("source") or "market_core",
            )
            ms_rows.append(ms)
            bus_rows.append(ms.to_row())

        if ms_rows:
            self.dl.monitors.append_many(ms_rows)
        setattr(self.dl.monitors, "rows", bus_rows)

    def _render_panels(self) -> None:
        """Render the three panels to stdout for visual confirmation."""
        ctx = {"dl": self.dl, "cfg": getattr(self.dl, "global_config", None)}

        def _print_panel(name: str, mod, width: int = 92):
            print()
            print(f"──── {name} ───────────────────────────────────────────────")
            try:
                lines_obj = mod.render(ctx, width=width)
            except TypeError:
                # Some panels accept (dl, ctx, width)
                lines_obj = mod.render(ctx)
            if isinstance(lines_obj, (list, tuple)):
                for ln in lines_obj:
                    print(ln)
            elif isinstance(lines_obj, str):
                print(lines_obj)

        _print_panel("Monitors", monitor_panel_mod)
        _print_panel("Market Alerts", market_panel_mod)
        _print_panel("XCom", xcom_panel_mod)

    # ── Checks ─────────────────────────────────────────────────────────────────

    def check_config_and_channels(self) -> CheckResult:
        live, src = xcom_live_status(self.dl, getattr(self.dl, "global_config", None))
        ch = self._channels_for_market()
        details = {"xcom_live": bool(live), "source": src, "channels_for_market": ch}
        if not any(ch.values()):
            return CheckResult(
                "Config: market notifications enabled",
                ok=False,
                details=details,
                skip="no-channels-enabled-for-market",
            )
        return CheckResult("Config: market notifications enabled", ok=True, details=details)

    def check_xcom_readiness(self) -> CheckResult:
        ok, reason = xcom_ready(self.dl, cfg=getattr(self.dl, "global_config", None))
        return CheckResult(
            "Readiness: xcom_ready()",
            ok=bool(ok),
            details={"reason": str(reason or "")},
        )

    def check_voice_cooldown_idle(self) -> CheckResult:
        rem, src = read_voice_cooldown_remaining(self.dl)
        idle = (rem or 0) <= 1
        return CheckResult(
            "Cooldown: idle before test",
            ok=idle,
            details={"remaining_s": rem, "source": src},
        )

    def run_sequence(self) -> List[CheckResult]:
        results: List[CheckResult] = []

        # Twilio stub unless explicitly --live
        self._install_twilio_stub()

        # Ensure cooldown does not block our BREACH call
        try:
            set_voice_cooldown(self.dl, 0)
            time.sleep(0.05)
        except Exception:
            pass

        # 0) Config + readiness
        r = self.check_config_and_channels()
        results.append(r)
        print(r.line())
        if r.skip == "no-channels-enabled-for-market":
            print("  -> Enable market.notifications.{system,voice,tts} in sonic_monitor_config.json.")
            return results

        r = self.check_xcom_readiness()
        results.append(r)
        print(r.line())

        r = self.check_voice_cooldown_idle()
        results.append(r)
        print(r.line())

        # 1) Create alert + seed anchor
        self._ensure_market_alert()
        self._set_price(self.cfg.base_price)
        out0 = self._run_market_eval(self.cfg.base_price)
        statuses0 = out0.get("statuses") or []
        self._update_monitors_bus(statuses0, cycle_tag="T0")

        # Expect OK state after seeding
        ok0 = True
        if statuses0:
            s0 = statuses0[0]
            ok0 = (s0.get("state") == "OK")
        results.append(
            CheckResult(
                "Phase 1: seed anchor (OK state)",
                ok=ok0,
                details={"statuses": statuses0},
            )
        )
        print(results[-1].line())

        # 2) BREACH by moving step dollars from anchor
        breach_price = self.cfg.base_price + self.cfg.step
        self._set_price(breach_price)
        out1 = self._run_market_eval(breach_price)
        statuses1 = out1.get("statuses") or []
        self._update_monitors_bus(statuses1, cycle_tag="T1")

        state1 = statuses1[0]["state"] if statuses1 else None
        results.append(
            CheckResult(
                "Phase 2: breach from anchor",
                ok=(state1 == "BREACH"),
                details={"statuses": statuses1},
            )
        )
        print(results[-1].line())

        # 3) Dispatch XCom from BREACH
        before_stub = self.stub_calls_count
        mon_cfg = getattr(self.dl, "global_config", None) or {}
        xres = dispatch_breaches_from_dl(self.dl, mon_cfg)
        after_stub = self.stub_calls_count

        # Look for a result row for monitor="market"
        market_rows = [r for r in (xres or []) if r.get("monitor") == "market"]
        ok_send = bool(market_rows)
        if market_rows:
            res0 = market_rows[0].get("result") or {}
            if isinstance(res0, dict):
                ok_send = bool(res0.get("success", ok_send))

        details_send = {
            "results": xres,
            "stub_calls_before": before_stub,
            "stub_calls_after": after_stub,
            "live": self.live,
        }
        results.append(
            CheckResult(
                "Phase 3: XCom dispatch from market BREACH",
                ok=ok_send,
                details=details_send,
            )
        )
        print(results[-1].line())

        # 4) Re-arm behavior check (reset recurrence)
        alerts = self.dl.price_alerts.list_alerts(self.cfg.asset)
        alert = alerts[0] if alerts else None
        ok_rearm = False
        if alert is not None:
            ok_rearm = (
                bool(alert.armed)
                and abs(float(alert.current_anchor_price or 0.0) - breach_price) < 1e-6
                and int(alert.fired_count or 0) == 1
            )
        results.append(
            CheckResult(
                "Phase 4: alert re-armed after breach",
                ok=ok_rearm,
                details={
                    "armed": getattr(alert, "armed", None),
                    "current_anchor_price": getattr(alert, "current_anchor_price", None),
                    "fired_count": getattr(alert, "fired_count", None),
                },
            )
        )
        print(results[-1].line())

        # 5) Second breach from new anchor (110 -> 120)
        second_price = breach_price + self.cfg.step
        self._set_price(second_price)
        out2 = self._run_market_eval(second_price)
        statuses2 = out2.get("statuses") or []

        alerts2 = self.dl.price_alerts.list_alerts(self.cfg.asset)
        alert2 = alerts2[0] if alerts2 else None
        ok_second_breach = False
        if alert2 is not None and statuses2:
            ok_second_breach = (
                statuses2[0].get("state") == "BREACH"
                and int(alert2.fired_count or 0) >= 2
            )

        results.append(
            CheckResult(
                "Phase 5: second breach after re-arm",
                ok=ok_second_breach,
                details={
                    "statuses": statuses2,
                    "fired_count": getattr(alert2, "fired_count", None),
                    "current_anchor_price": getattr(alert2, "current_anchor_price", None),
                },
            )
        )
        print(results[-1].line())

        # 6) Optional: dump panels so you can visually confirm
        print("\n--- Panel snapshots after second BREACH ---")
        self._render_panels()

        return results

    # ── Public entrypoint ──────────────────────────────────────────────────────

    def run(self) -> int:
        live, src = xcom_live_status(self.dl, getattr(self.dl, "global_config", None))
        print("=== Market ↔ XCom System Test ===")
        print(f"Asset           : {self.cfg.asset}")
        print(f"DB path         : {self.db_path}")
        print(f"XCom live       : {bool(live)} [{src}]")
        print(f"Mode            : {'LIVE (real Twilio)' if self.live else 'STUB (no network)'}")
        print(f"Threshold       : {self.cfg.threshold} (move_abs)")
        print(f"Recurrence      : {self.cfg.recurrence_mode}")
        print("")

        results = self.run_sequence()

        failures = [r for r in results if not r.ok and not r.skip]

        print("\n=== Summary ===")
        for r in results:
            print(" -", r.line())

        if failures:
            print("\n=== Detailed Failures ===")
            for r in failures:
                print(f"\n[{r.name}]")
                for k, v in (r.details or {"reason": "no details"}).items():
                    print(f"  {k}: {v}")

        return 1 if failures else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Standalone Market ↔ XCom system test")
    ap.add_argument("--asset", default="SOL", help="Asset symbol to test (default: SOL)")
    ap.add_argument("--db", default=None, help="Path to mother DB (default: MOTHER_DB_PATH)")
    ap.add_argument(
        "--config",
        default=None,
        help="Path to JSON monitor config (default: backend/config/sonic_monitor_config.json)",
    )
    ap.add_argument(
        "--live",
        action="store_true",
        help="Use real Twilio (no stub) if creds present",
    )
    args = ap.parse_args()

    test = MarketXComSystemTest(
        asset=args.asset,
        db_path=args.db,
        config_path=args.config,
        live=args.live,
    )
    code = test.run()
    sys.exit(code)


if __name__ == "__main__":
    main()
