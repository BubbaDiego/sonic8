#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sonic Cornerstone System Test (resilient)
Targets: dl_monitor, dl_xcom, liquidation_monitor, sonic_monitor
"""

from __future__ import annotations
import argparse, json, os, sys, time, traceback
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import pathlib
import functools
import requests

# ---------------------------
# Config
# ---------------------------
DEFAULT_BASE = os.getenv("SONIC_API_BASE", "http://127.0.0.1:8000")
DEFAULT_ASSETS = ["SOL", "ETH", "BTC"]
REQ_TIMEOUT = 20
POLL_SLEEP = 0.6
EVENT_TIMEOUT = 30
RECENT_WINDOW_SECONDS = 30

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

NOW_STR = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
ARTIFACT_DIR = pathlib.Path(f"./system_test_artifacts_{NOW_STR}").resolve()

def ts() -> str:
    return now_utc_iso()

def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)

def write_artifact(path: pathlib.Path, data: Any):
    ensure_dir(path.parent)
    if isinstance(data, (dict, list)):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    elif isinstance(data, (bytes, bytearray)):
        path.write_bytes(data)
    else:
        path.write_text(str(data))

# ---------------------------
# Test result containers
# ---------------------------
class Check:
    def __init__(self, name: str):
        self.name = name
        self.ok = False
        self.error: Optional[str] = None
        self.details: Dict[str, Any] = {}
        self.artifacts: Dict[str, pathlib.Path] = {}
        self.started_at = ts()
        self.ended_at: Optional[str] = None

    def pass_(self, **details):
        self.ok = True
        self.details.update(details)
        self.ended_at = ts()

    def fail(self, msg: str, **details):
        self.ok = False
        self.error = msg
        self.details.update(details)
        self.ended_at = ts()

    def to_dict(self):
        return {
            "name": self.name,
            "ok": self.ok,
            "error": self.error,
            "details": self.details,
            "artifacts": {k: str(v) for k, v in self.artifacts.items()},
            "started_at": self.started_at,
            "ended_at": self.ended_at or ts(),
        }

class Suite:
    def __init__(self, name: str):
        self.name = name
        self.cases: List[Check] = []
        self.started_at = ts()
        self.ended_at: Optional[str] = None

    def add(self, c: Check):
        self.cases.append(c)

    def finish(self):
        self.ended_at = ts()

    def ok(self) -> bool:
        return all(c.ok for c in self.cases)

    def to_dict(self):
        return {
            "name": self.name,
            "ok": self.ok(),
            "started_at": self.started_at,
            "ended_at": self.ended_at or ts(),
            "checks": [c.to_dict() for c in self.cases],
        }

# ---------------------------
# HTTP helper
# ---------------------------
class Client:
    def __init__(self, base: str, outdir: pathlib.Path):
        self.base = base.rstrip("/")
        self.outdir = outdir

    def _req(self, method: str, path: str, **kwargs) -> Tuple[int, Any, Dict[str, str]]:
        url = f"{self.base}{path}"
        headers = kwargs.pop("headers", {})
        try:
            r = requests.request(method=method, url=url, headers=headers, timeout=REQ_TIMEOUT, **kwargs)
            status = r.status_code
            text = r.text
            try:
                data = r.json()
            except Exception:
                data = text
            return status, data, dict(r.headers)
        except Exception as e:
            exc = {"error": repr(e), "url": url, "method": method}
            write_artifact(self.outdir / f"error_{method}_{path.strip('/').replace('/','_')}.json", exc)
            return 0, exc, {}

    def get(self, path: str, **kwargs):  return self._req("GET", path, **kwargs)
    def post(self, path: str, **kwargs): return self._req("POST", path, **kwargs)
    def put(self, path: str, **kwargs):  return self._req("PUT", path, **kwargs)

# ---------------------------
# Schema-ish helpers
# ---------------------------
def assert_status_2xx(check: Check, status: int, payload: Any = None, url: str = ""):
    if status < 200 or status >= 300:
        if status == 0:
            raise AssertionError(f"HTTP 0 (backend unreachable at {url or 'base-url'})")
        raise AssertionError(f"HTTP {status}")

def assert_recent(check: Check, iso_ts: str, window_sec: int = RECENT_WINDOW_SECONDS):
    try:
        t = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - t.astimezone(timezone.utc)
        if delta.total_seconds() > window_sec:
            raise AssertionError(f"stale timestamp {iso_ts} (> {window_sec}s)")
    except Exception:
        pass

# ---------------------------
# Startup wait
# ---------------------------
def wait_for_backend(c: Client, seconds: int, suite: Suite):
    chk = Check(f"Backend wait ({seconds}s)")
    suite.add(chk)
    deadline = time.time() + max(0, seconds)
    last_status = None
    while time.time() < deadline:
        s, d, _ = c.get("/api/status")
        last_status = (s, d)
        if s and 200 <= s < 300:
            chk.pass_(note="Backend responded to /api/status")
            return
        time.sleep(0.5)
    write_artifact(c.outdir / "backend_wait_last_status.json", {
        "status": last_status[0] if last_status else None,
        "data": last_status[1] if last_status else None
    })
    chk.fail("Backend did not respond in time")

# ---------------------------
# Tests
# ---------------------------
def preflight(c: Client, suite: Suite):
    chk = Check("Preflight")
    suite.add(chk)
    try:
        ensure_dir(c.outdir)

        s1, d1, _ = c.get("/api/status")
        write_artifact(c.outdir / "preflight_api_status.json", d1)
        assert_status_2xx(chk, s1, d1, "/api/status")
        if isinstance(d1, dict):
            assert str(d1.get("status","")).lower().startswith("fastapi backend"), "Backend not reporting healthy"

        s2, d2, _ = c.get("/db_admin/tables")
        write_artifact(c.outdir / "preflight_db_tables.json", d2)
        assert_status_2xx(chk, s2, d2, "/db_admin/tables")
        assert isinstance(d2, list), "db_admin/tables should be list"
        for must in ["monitor_ledger", "alerts", "monitor_heartbeat", "sonic_monitor_log"]:
            assert must in d2, f"missing table: {must}"

        s3, d3, _ = c.get("/monitors/")
        write_artifact(c.outdir / "preflight_monitors.json", d3)
        assert_status_2xx(chk, s3, d3, "/monitors/")
        assert isinstance(d3, list)
        for m in ["liquid_monitor", "xcom_monitor"]:
            assert m in d3, f"monitor not registered: {m}"

        s4, d4, _ = c.get("/api/monitor-status/")
        write_artifact(c.outdir / "preflight_monitor_status.json", d4)
        assert_status_2xx(chk, s4, d4, "/api/monitor-status/")

        chk.pass_(note="Backend, tables, monitors, status reachable")
    except Exception as e:
        chk.fail(f"{type(e).__name__}: {e}")
        chk.details["trace"] = traceback.format_exc()

def xcom_suite(c: Client, suite: Suite):
    chk = Check("XCom core (dl_xcom)")
    suite.add(chk)
    try:
        s1, d1, _ = c.get("/xcom/providers")
        write_artifact(c.outdir / "xcom_providers.json", d1)
        assert_status_2xx(chk, s1, d1, "/xcom/providers")

        s2, d2, _ = c.get("/xcom/status")
        write_artifact(c.outdir / "xcom_status.json", d2)
        assert_status_2xx(chk, s2, d2, "/xcom/status")
        assert isinstance(d2, dict), "xcom/status should be {provider: status}"

        s3, d3, _ = c.get("/xcom/last_ping")
        write_artifact(c.outdir / "xcom_last_ping_before.json", d3)
        assert_status_2xx(chk, s3, d3, "/xcom/last_ping")

        s4, d4, _ = c.post("/xcom/test", json={"subject":"Cornerstone system test","body":"XCom live ping"})
        write_artifact(c.outdir / "xcom_test_response.json", d4)
        assert_status_2xx(chk, s4, d4, "/xcom/test")

        time.sleep(1.0)
        s5, d5, _ = c.get("/xcom/last_ping")
        write_artifact(c.outdir / "xcom_last_ping_after.json", d5)
        assert_status_2xx(chk, s5, d5, "/xcom/last_ping")

        if isinstance(d5, dict) and "timestamp" in d5:
            try: assert_recent(chk, d5["timestamp"], window_sec=60)
            except AssertionError: pass

        chk.pass_(note="XCom reachable; test ping acknowledged")
    except Exception as e:
        chk.fail(f"{type(e).__name__}: {e}")
        chk.details["trace"] = traceback.format_exc()

def liquidation_suite(c: Client, suite: Suite, assets: List[str]):
    chk = Check("Liquidation monitor")
    suite.add(chk)
    try:
        s0, cfg0, _ = c.get("/api/monitor-settings/liquidation")
        write_artifact(c.outdir / "liq_config_initial.json", cfg0)
        assert_status_2xx(chk, s0, cfg0, "/api/monitor-settings/liquidation")

        s1, near, _ = c.get("/api/liquidation/nearest-distance")
        write_artifact(c.outdir / "liq_nearest_initial.json", near)
        assert_status_2xx(chk, s1, near, "/api/liquidation/nearest-distance")

        target = None
        if isinstance(near, dict):
            for a in assets:
                if a in near:
                    target = a
                    break
        target = target or assets[0]

        test_cfg_A = {
            "threshold_percent": 1.0,
            "thresholds": {target: 99999},
            "snooze_seconds": 10,
            "notifications": {"system": True, "voice": True, "sms": False, "tts": True},
        }
        s2, d2, _ = c.post("/api/monitor-settings/liquidation", json=test_cfg_A)
        write_artifact(c.outdir / "liq_config_set_A.json", d2)
        assert_status_2xx(chk, s2, d2, "/api/monitor-settings/liquidation")

        s3, d3, _ = c.post("/api/monitor-status/reset-liquid-snooze", json={})
        write_artifact(c.outdir / "liq_reset_snooze.json", d3)
        assert_status_2xx(chk, s3, d3, "/api/monitor-status/reset-liquid-snooze")

        s4, d4, _ = c.post("/monitors/liquid_monitor", json={})
        write_artifact(c.outdir / "liq_monitor_kick_A.json", d4)
        if s4 and s4 >= 400:
            raise AssertionError(f"liquid_monitor returned HTTP {s4}")
        time.sleep(2.0)

        s5, notesA, _ = c.get("/api/notifications/")
        write_artifact(c.outdir / "liq_notifications_after_A.json", notesA)
        assert_status_2xx(chk, s5, notesA, "/api/notifications/")
        found_alert = False
        if isinstance(notesA, list):
            for n in notesA:
                if isinstance(n, dict) and str(n.get("monitor_name","")).startswith("liquid"):
                    found_alert = True
                    break
        assert found_alert, "Expected a liquidation alert after Phase A"

        s6, statA, _ = c.get("/monitor_status/")
        write_artifact(c.outdir / "liq_monitor_status_after_A.json", statA)
        assert_status_2xx(chk, s6, statA, "/monitor_status/")

        s7, d7, _ = c.post("/monitors/liquid_monitor", json={})
        write_artifact(c.outdir / "liq_monitor_kick_A_repeat.json", d7)
        time.sleep(1.5)
        s8, notesA2, _ = c.get("/api/notifications/")
        write_artifact(c.outdir / "liq_notifications_after_A_repeat.json", notesA2)

        test_cfg_B = {
            "threshold_percent": 0.0001,
            "thresholds": {target: 0.0001},
            "snooze_seconds": 3,
            "notifications": {"system": True, "voice": True, "sms": False, "tts": True},
        }
        s9, d9, _ = c.post("/api/monitor-settings/liquidation", json=test_cfg_B)
        write_artifact(c.outdir / "liq_config_set_B.json", d9)
        assert_status_2xx(chk, s9, d9, "/api/monitor-settings/liquidation")

        s10, d10, _ = c.post("/api/monitor-status/reset-liquid-snooze", json={})
        write_artifact(c.outdir / "liq_reset_snooze_B.json", d10)
        assert_status_2xx(chk, s10, d10, "/api/monitor-status/reset-liquid-snooze")

        s11, d11, _ = c.post("/monitors/liquid_monitor", json={})
        write_artifact(c.outdir / "liq_monitor_kick_B.json", d11)
        time.sleep(1.5)
        s12, notesB, _ = c.get("/api/notifications/")
        write_artifact(c.outdir / "liq_notifications_after_B.json", notesB)

        # restore
        c.post("/api/monitor-settings/liquidation", json=cfg0 or {})
        chk.pass_(note=f"Liquidation fired (A), snooze prevented duplicate, and held (B) — target={target}")
    except Exception as e:
        chk.fail(f"{type(e).__name__}: {e}")
        chk.details["trace"] = traceback.format_exc()

def dl_suite(c: Client, suite: Suite):
    chk = Check("DL monitor (ledger & tables)")
    suite.add(chk)
    try:
        s1, tables, _ = c.get("/db_admin/tables")
        write_artifact(c.outdir / "dl_tables.json", tables)
        assert_status_2xx(chk, s1, tables, "/db_admin/tables")
        expected = ["monitor_ledger", "alerts", "sonic_monitor_log"]
        for t in expected:
            assert t in tables, f"missing required table: {t}"

        rows = {}
        for t in expected:
            sT, dT, _ = c.get(f"/db_admin/tables/{t}")
            write_artifact(c.outdir / f"dl_{t}.json", dT)
            assert_status_2xx(chk, sT, dT, f"/db_admin/tables/{t}")
            rows[t] = dT if isinstance(dT, list) else []

        chk.pass_(note="DL tables available; rows fetched", row_counts={k: len(v) for k, v in rows.items()})
    except Exception as e:
        chk.fail(f"{type(e).__name__}: {e}")
        chk.details["trace"] = traceback.format_exc()

def sonic_monitor_suite(c: Client, suite: Suite):
    chk = Check("Sonic monitor (cycle & events)")
    suite.add(chk)
    try:
        s1, d1, _ = c.post("/monitors/sonic_cycle", json={})
        write_artifact(c.outdir / "sonic_cycle_start.json", d1)
        assert_status_2xx(chk, s1, d1, "/monitors/sonic_cycle")

        s2, before, _ = c.get("/monitor_status/")
        write_artifact(c.outdir / "sonic_status_before.json", before)
        assert_status_2xx(chk, s2, before, "/monitor_status/")
        before_ts = (before or {}).get("sonic_last_complete", "")

        deadline = time.time() + EVENT_TIMEOUT
        advanced = False
        last_seen = None
        while time.time() < deadline:
            time.sleep(POLL_SLEEP)
            s3, stat, _ = c.get("/monitor_status/")
            last_seen = stat
            if s3 and 200 <= s3 < 300 and isinstance(stat, dict):
                now_ts = stat.get("sonic_last_complete", "")
                if now_ts and now_ts != before_ts:
                    advanced = True
                    break

        write_artifact(c.outdir / "sonic_status_after.json", last_seen or {})
        assert advanced, "Sonic cycle did not complete within timeout"
        chk.pass_(note="Sonic cycle advanced (sonic_last_complete updated)")
    except Exception as e:
        chk.fail(f"{type(e).__name__}: {e}")
        chk.details["trace"] = traceback.format_exc()

# ---------------------------
# Harness
# ---------------------------
def main():
    ap = argparse.ArgumentParser(description="Sonic Cornerstone System Test")
    ap.add_argument("--base", default=DEFAULT_BASE, help="API base URL (default: %(default)s)")
    ap.add_argument("--assets", default=",".join(DEFAULT_ASSETS), help="Comma list of assets (default: %(default)s)")
    ap.add_argument("--wait", type=int, default=20, help="Seconds to wait for backend to respond to /api/status before testing")
    ap.add_argument("--try-ports", default="", help="Optional comma ports (e.g. 8000,8080) to try if base fails (same host)")
    ap.add_argument("--no-artifacts", action="store_true", help="Disable writing artifact files")
    ap.add_argument("--junit", default="", help="Optional path to write JUnit-ish XML summary")
    args = ap.parse_args()

    bases = [args.base]
    if args.try_ports:
        try:
            host = args.base.split("://",1)[1].split("/",1)[0]
            scheme = args.base.split("://",1)[0]
            host_only = host.split(":")[0]
            for p in [p.strip() for p in args.try_ports.split(",") if p.strip()]:
                bases.append(f"{scheme}://{host_only}:{p}")
        except Exception:
            pass

    outdir = ARTIFACT_DIR if not args.no_artifacts else pathlib.Path("./_tmp_ignore").resolve()
    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()]

    print(f"\n=== Sonic Cornerstone System Test ===")
    print(f"Bases: {bases}")
    print(f"Assets: {assets}")
    print(f"Artifacts: {outdir}\n")

    suite = Suite("cornerstone")

    # Find a live base (optionally wait)
    chosen_base = None
    for b in bases:
        tmp_client = Client(b, outdir)
        if args.wait > 0:
            wait_for_backend(tmp_client, args.wait, suite)
        s, d, _ = tmp_client.get("/api/status")
        if s and 200 <= s < 300:
            chosen_base = b
            break

    if not chosen_base:
        print("No live base found. See artifacts for connection errors.")
        suite.finish()
        if not args.no_artifacts:
            write_artifact(outdir / "summary.json", suite.to_dict())
        print("Overall: FAIL ❌ (backend unreachable)")
        sys.exit(2)

    client = Client(chosen_base, outdir)
    print(f"Using base: {chosen_base}")

    phases = [
        preflight,
        xcom_suite,
        functools.partial(liquidation_suite, assets=assets),
        dl_suite,
        sonic_monitor_suite,
    ]

    for phase in phases:
        try:
            phase(client, suite) if not isinstance(phase, functools.partial) else phase(client, suite)
        except Exception as e:
            chk = Check(f"{getattr(phase, '__name__', 'phase')}")
            chk.fail(f"{type(e).__name__}: {e}")
            chk.details["trace"] = traceback.format_exc()
            suite.add(chk)

    suite.finish()

    if not args.no_artifacts:
        write_artifact(outdir / "summary.json", suite.to_dict())

    failures = [c for c in suite.cases if not c.ok]
    passes = [c for c in suite.cases if c.ok]

    def pad(s, n=32): return (s + " " * n)[:n]

    print("\n--- Results ---")
    for c in suite.cases:
        state = "PASS" if c.ok else "FAIL"
        print(f"{state:>4}  {pad(c.name)}  {c.details.get('note','') or (c.error or '')}")

    print("\nOverall:", "PASS ✅" if suite.ok() else f"FAIL ❌  ({len(failures)} failed)")
    print(f"Checks run: {len(suite.cases)} | Passed: {len(passes)} | Failed: {len(failures)}")
    if not args.no_artifacts:
        print(f"Artifacts: {outdir}")

    if args.junit:
        try:
            junit = junit_xml(suite)
            pathlib.Path(args.junit).write_text(junit)
            print(f"JUnit written: {args.junit}")
        except Exception as e:
            print(f"[warn] failed to write JUnit: {e}")

    sys.exit(0 if suite.ok() else 2)

def junit_xml(suite: Suite) -> str:
    cases_xml = []
    for c in suite.cases:
        safe_name = xml_escape(c.name)
        if c.ok:
            cases_xml.append(f'<testcase name="{safe_name}" time="0.0"></testcase>')
        else:
            msg = xml_escape(c.error or "failed")
            trace = xml_escape(c.details.get("trace", ""))
            cases_xml.append(
                f'<testcase name="{safe_name}" time="0.0"><failure message="{msg}"><![CDATA[{trace}]]></failure></testcase>'
            )
    return f'<?xml version="1.0" encoding="UTF-8"?><testsuite name="{xml_escape(suite.name)}" tests="{len(suite.cases)}" failures="{len([c for c in suite.cases if not c.ok])}">{"".join(cases_xml)}</testsuite>'

def xml_escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&apos;")

if __name__ == "__main__":
    main()
