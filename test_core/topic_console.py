import argparse
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import sys
import shlex
import os

from .topic_query import plan

try:
    import yaml  # optional for topics.yaml (PyYAML)
except Exception:  # pragma: no cover
    yaml = None


def _load_topics_yaml() -> Dict[str, Any]:
    yml = Path(__file__).parent / "topics.yaml"
    if not yml.exists() or yaml is None:
        return {}
    data = yaml.safe_load(yml.read_text()) or {}
    data.setdefault("synonyms", {})
    data.setdefault("bundles", {})
    return data


def _stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _parse_junit(junit_path: Path) -> Dict[str, Any]:
    if not junit_path.exists():
        return {"stats": {}, "failures": [], "slow": []}

    tree = ET.parse(junit_path)
    root = tree.getroot()

    # Handle <testsuite> or <testsuites>
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    stats = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time_s": 0.0, "passed": 0}
    failures, slow = [], []

    for s in suites:
        tests = int(s.attrib.get("tests", 0))
        fails = int(s.attrib.get("failures", 0))
        errs = int(s.attrib.get("errors", 0))
        skipped = int(s.attrib.get("skipped", 0))
        time_s = float(s.attrib.get("time", 0.0))
        stats["tests"] += tests
        stats["failures"] += fails
        stats["errors"] += errs
        stats["skipped"] += skipped
        stats["time_s"] += time_s

        for tc in s.findall("testcase"):
            name = tc.attrib.get("name", "")
            cls = tc.attrib.get("classname", "")
            dur = float(tc.attrib.get("time", 0.0))
            nodeid = f"{cls}::{name}" if cls else name
            slow.append({"nodeid": nodeid, "duration_s": dur})

            for tag in ("failure", "error"):
                el = tc.find(tag)
                if el is not None:
                    msg = el.attrib.get("message") or (el.text or "").strip()
                    failures.append({"nodeid": nodeid, "type": tag, "message": msg})

    stats["passed"] = max(0, stats["tests"] - stats["failures"] - stats["errors"] - stats["skipped"])
    slow = sorted(slow, key=lambda x: x["duration_s"], reverse=True)[:10]
    return {"stats": stats, "failures": failures, "slow": slow}


def _write_md(md_path: Path, topic_args: List[str], k_expr: str, results: Dict[str, Any], cmd: List[str]) -> None:
    md = []
    md.append(f"# Topic Test Run\n")
    md.append(f"- **Topics:** {', '.join(topic_args) if topic_args else '(none)'}")
    md.append(f"- **-k:** `{k_expr}`")
    md.append(f"- **Command:** `{shlex.join(cmd)}`\n")

    s = results.get("stats", {})
    md.append("## Summary\n")
    md.append("| Total | Passed | Failed | Errors | Skipped | Time (s) |")
    md.append("|------:|------:|------:|------:|-------:|--------:|")
    md.append(f"| {s.get('tests',0)} | {s.get('passed',0)} | {s.get('failures',0)} | {s.get('errors',0)} | {s.get('skipped',0)} | {s.get('time_s',0.0):.2f} |")
    md.append("")

    fails = results.get("failures", [])
    if fails:
        md.append("## Failures\n")
        for f in fails:
            first = (f.get("message") or "").splitlines()[0]
            md.append(f"- `{f['nodeid']}` — {first}")

    slow = results.get("slow", [])
    if slow:
        md.append("\n## Slowest tests\n")
        for s in slow:
            md.append(f"- `{s['nodeid']}` — {s['duration_s']:.3f}s")

    md_path.write_text("\n".join(md), encoding="utf-8")


def main(argv: List[str] = None) -> int:
    p = argparse.ArgumentParser(prog="topic-console", description="Run pytest by topic keywords with nifty reports.")
    # make --topic optional (works if --bundle is supplied)
    p.add_argument("--topic", action="append", help="Topic keyword; repeatable.")
    p.add_argument("--bundle", action="append", default=[], help="Bundle name from topics.yaml; repeatable.")
    # default discovery to test_core/tests
    p.add_argument("--path", action="append", default=["test_core/tests"], help="Discovery roots; default=test_core/tests")
    p.add_argument("--fuzzy", type=int, default=75, help="Fuzzy threshold (0-100). 0 = substring only.")
    p.add_argument("--exclude", action="append", default=[], help="Exclude keywords joined with 'or' in a NOT clause.")
    p.add_argument("--parallel", type=int, default=0, help="pytest-xdist workers; 0 disables.")
    p.add_argument("--maxfail", type=int, default=1, help="Abort after N failures (pytest --maxfail).")
    p.add_argument("--show", action="store_true", help="Show selected nodeids before running.")
    p.add_argument("--dry-run", action="store_true", help="Collect and show selection, then exit without running.")
    p.add_argument("--quiet", action="store_true", help="Pass -q to pytest.")
    p.add_argument("--junit-prefix", default="topic", help="Prefix for JUnit XML filename.")
    args = p.parse_args(argv)

    topics_meta = _load_topics_yaml()

    # Merge bundles into topics, even if --topic wasn't provided
    if topics_meta.get("bundles") and args.bundle:
        if args.topic is None:
            args.topic = []
        for b in args.bundle:
            args.topic.extend(topics_meta["bundles"].get(b, []))

    # Validate: at least one topic (possibly via bundle)
    if not args.topic:
        p.error("Provide at least one --topic or --bundle")

    # Plan selection
    paths, k_expr, hits = plan(args.topic, args.fuzzy, topics_meta, args.path)

    if args.show or args.dry_run:
        print(f"Selected tests: {len(hits)}")
        for h in hits:
            print("  ", h)
        if args.dry_run:
            return 0

    # Build pytest command
    reports_dir = Path("test_core/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    junit_path = reports_dir / f"{stamp}_{args.junit_prefix}.xml"

    cmd = ["pytest"]
    # Forward discovery paths (default includes test_core/tests)
    if args.path:
        cmd += sorted(set(args.path))

    if k_expr:
        if args.exclude:
            not_expr = " or ".join(args.exclude)
            cmd += ["-k", f"({k_expr}) and not ({not_expr})"]
        else:
            cmd += ["-k", k_expr]
    if args.parallel > 0:
        cmd += ["-n", str(args.parallel)]
    if args.maxfail:
        cmd += [f"--maxfail={args.maxfail}"]
    cmd += ["--junitxml", str(junit_path)]
    if args.quiet:
        cmd += ["-q"]

    # Inject clean PYTHONPATH for imports (repo root + backend)
    env = os.environ.copy()
    repo_root = str(Path(__file__).resolve().parents[1])  # .../sonic7
    backend = str(Path(repo_root) / "backend")
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = os.pathsep.join([repo_root, backend, env["PYTHONPATH"]])
    else:
        env["PYTHONPATH"] = os.pathsep.join([repo_root, backend])

    print("Running:", " ".join(shlex.quote(c) for c in cmd))
    rc = subprocess.call(cmd, env=env)

    # Parse junit -> json + md
    results = _parse_junit(junit_path)
    json_path = reports_dir / f"{stamp}_topic={'_'.join(args.topic)}.json"
    json_path.write_text(json.dumps({
        "run_id": stamp,
        "topics": args.topic,
        "selection": {"paths": paths, "k_expr": k_expr, "hits": hits},
        "stats": results.get("stats", {}),
        "failures": results.get("failures", []),
        "slow": results.get("slow", [])
    }, indent=2), encoding="utf-8")

    md_path = reports_dir / f"{stamp}_topic={'_'.join(args.topic)}.md"
    _write_md(md_path, args.topic, k_expr, results, cmd)

    s = results.get("stats", {})
    print(f"\nSummary: {s.get('passed',0)}/{s.get('tests',0)} passed, "
          f"{s.get('failures',0)} failed, {s.get('errors',0)} errors, "
          f"{s.get('skipped',0)} skipped in {s.get('time_s',0.0):.2f}s")
    print(f"Artifacts: {json_path}  |  {md_path}  |  {junit_path}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
