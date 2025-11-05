#!/usr/bin/env python3
"""Tests Hub — unified test runner for Sonic.

Unifies old menu items:
  - "Run Unit Tests"
  - "Topic Test Runner"

Usage:
  python backend/scripts/tests_hub.py                # interactive
  python backend/scripts/tests_hub.py run -s unit    # run a suite
  python backend/scripts/tests_hub.py run -t wallet,positions
  python backend/scripts/tests_hub.py list topics|suites
  python backend/scripts/tests_hub.py smoke          # quick sanity (alias for suite 'smoke')

Artifacts:
  reports/tests/{junit.xml, coverage.xml, htmlcov/}

Notes:
  - Stays dependency-light: stdlib + subprocess + yaml (PyYAML).
  - Orchestrates pytest/coverage/npm; it does not reimplement them.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Iterable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - dependency notice
    print("Missing dependency 'PyYAML' (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "tests" / "hub.manifest.yaml"


def _echo(box_title: str, body: str) -> None:
    rule = "=" * len(box_title)
    print(f"\n{box_title}\n{rule}\n{body.strip()}\n")


def load_manifest(path: Path) -> dict:
    if not path.exists():
        print(f"Tests Hub manifest not found: {path}", file=sys.stderr)
        sys.exit(2)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def ensure_report_dir(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)


def which_or_warn(bin_name: str) -> bool:
    return shutil.which(bin_name) is not None


def has_module(mod: str) -> bool:
    # robust check for optional deps like 'coverage'
    return importlib.util.find_spec(mod) is not None


def _collect_topic_globs(manifest: dict, topics: Iterable[str]) -> tuple[list[str], list[str]]:
    globs: list[str] = []
    expr_terms: list[str] = []
    topic_defs = manifest.get("topics", {}) or {}

    for topic in topics:
        topic = topic.strip()
        if not topic:
            continue
        tdef = topic_defs.get(topic)
        if not tdef:
            print(f"Unknown topic: '{topic}'", file=sys.stderr)
            sys.exit(2)
        globs.extend(tdef.get("paths", []) or [])
        expr = tdef.get("expr")
        if expr:
            expr_terms.append(f"({expr})")

    return globs, expr_terms


def build_pytest_cmd(manifest: dict, topics: list[str], extra_args: list[str], report_dir: Path) -> list[str]:
    cfg = manifest.get("pytest", {}) or {}
    base_args = list(cfg.get("base_args", []) or [])

    autoload = bool(cfg.get("autoload", False))
    plugins = list(cfg.get("plugins", []) or [])

    paths, expr_terms = _collect_topic_globs(manifest, topics)
    if not paths:
        paths = ["backend/**/tests/**/test_*.py"]

    pytest_args: list[str] = []
    pytest_args.extend(base_args)

    if not autoload:
        for plugin_name in plugins:
            pytest_args.extend(["-p", plugin_name])

    pytest_args.extend(paths)

    if expr_terms:
        pytest_args.extend(["-k", " or ".join(expr_terms)])

    junit_cfg = cfg.get("junit", {}) or {}
    if manifest.get("junit_xml", True):
        ensure_report_dir(report_dir)
        junit_file = junit_cfg.get("file", "junit.xml")
        junit_path = report_dir / junit_file
        pytest_args.extend(["--junitxml", str(junit_path)])

    coverage_enabled = bool(manifest.get("coverage", True))
    use_cov = coverage_enabled and has_module("coverage")
    if coverage_enabled and not use_cov:
        print("⚠️  coverage module not installed; running without coverage.")

    coverage_cfg = cfg.get("coverage", {}) or {}
    cov_prefix: list[str]
    if use_cov:
        cov_prefix = [sys.executable, "-m", "coverage", "run"]
        cov_pkg = coverage_cfg.get("pkg", "backend")
        if cov_pkg:
            cov_prefix.extend(["--source", cov_pkg])
        for omit in coverage_cfg.get("omit", []) or []:
            cov_prefix.extend(["--omit", omit])
        cov_prefix.extend(["-m", "pytest"])
    else:
        cov_prefix = [sys.executable, "-m", "pytest"]

    cmd = cov_prefix + pytest_args + list(extra_args)
    return cmd


def run_cmd(name: str, cmd: list[str], env: dict | None = None, cwd: Path | None = None) -> int:
    _echo(name, " ".join(cmd))
    proc = subprocess.Popen(cmd, env=env or os.environ, cwd=str(cwd or REPO_ROOT))
    proc.communicate()
    return proc.returncode


def summarize_coverage(manifest: dict, coverage_file: Path | None) -> None:
    if not (manifest.get("coverage", True) and has_module("coverage")):
        return

    report_dir = manifest.get("report_dir", "reports/tests") or "reports/tests"
    report_path = Path(report_dir)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    ensure_report_dir(report_path)

    env = os.environ.copy()
    if coverage_file is not None:
        env["COVERAGE_FILE"] = str(coverage_file)

    xml_path = report_path / "coverage.xml"
    html_dir = report_path / "htmlcov"

    subprocess.call([sys.executable, "-m", "coverage", "xml", "-o", str(xml_path)], cwd=str(REPO_ROOT), env=env)
    if manifest.get("coverage_html", True):
        subprocess.call([sys.executable, "-m", "coverage", "html", "-d", str(html_dir)], cwd=str(REPO_ROOT), env=env)
        print(f"Coverage HTML: {html_dir / 'index.html'}")
    subprocess.call([sys.executable, "-m", "coverage", "report", "-m"], cwd=str(REPO_ROOT), env=env)


def list_items(kind: str, manifest: dict) -> int:
    if kind == "topics":
        rows = sorted((manifest.get("topics") or {}).keys())
    elif kind == "suites":
        rows = sorted((manifest.get("suites") or {}).keys())
    else:
        print("Specify 'topics' or 'suites'.", file=sys.stderr)
        return 2
    bullet = "•"
    pretty = "\n".join([f"  {bullet} {row}" for row in rows]) if rows else "  (none)"
    _echo(f"Available {kind}", pretty)
    return 0


def resolve_suite_topics(manifest: dict, suite: str) -> tuple[list[str], list[str]]:
    suites = manifest.get("suites", {}) or {}
    if suite not in suites:
        print(f"Unknown suite: {suite}", file=sys.stderr)
        sys.exit(2)
    sdef = suites.get(suite) or {}
    topics = list(sdef.get("topics", []) or [])
    extra = list(sdef.get("extra_pytest_args", []) or [])
    return topics, extra


def _pick_suite(manifest: dict) -> tuple[str, list[str]]:
    suites = manifest.get("suites", {}) or {}
    keys = list(suites.keys())
    if not keys:
        print("No suites configured.")
        return "", []

    title = "🧪  Suites"
    menu = "\n".join([f"  {idx + 1:>2}. {name}" for idx, name in enumerate(keys)])
    _echo(title, menu + "\n  0. ← Back")

    while True:
        choice = input("Pick a suite #: ").strip()
        if choice == "0":
            return "", []
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            name = keys[int(choice) - 1]
            _, extra = resolve_suite_topics(manifest, name)
            return name, extra
        print("Pick a valid number.")


def _glob_exists(pattern: str) -> bool:
    if any(char in pattern for char in "*?[]"):
        return any(REPO_ROOT.glob(pattern))
    return (REPO_ROOT / pattern).exists()


def do_contracts_probe(manifest: dict) -> int:
    tdef = (manifest.get("topics") or {}).get("schemas", {}) or {}
    patterns = tdef.get("paths", []) or []
    missing = [pattern for pattern in patterns if not _glob_exists(pattern)]
    if missing:
        _echo("Contracts probe", "Missing schema artifacts:\n" + "\n".join(missing))
        return 1
    bundle = REPO_ROOT / "schema_bundle.json"
    if bundle.exists():
        try:
            json.loads(bundle.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            _echo("Contracts probe", f"schema_bundle.json failed to parse: {exc}")
            return 1
    _echo("Contracts probe", "Schema artifacts present.")
    return 0


def interactive(manifest: dict, manifest_path: Path | None = None) -> int:
    manifest_args: list[str] = ["-m", str(manifest_path)] if manifest_path else []

    while True:
        if manifest_path:
            manifest = load_manifest(manifest_path)
        menu = textwrap.dedent(
            """
              ╭────────────────────────────────────────────╮
              │ 🧪  Tests Hub                               │
              │                                            │
              │  1. 🚀 Quick Smoke                          │
              │  2. 📚 Run a Suite                          │
              │  3. 🎯 Run by Topic                         │
              │  4. 🗂️  List Topics                         │
              │  5. 📋 List Suites                          │
              │  6. ⏹️  Exit                                │
              ╰────────────────────────────────────────────╯
            """
        )
        print(menu)
        choice = input("> ").strip()

        if choice == "1":
            rc = main(manifest_args + ["run", "-s", "smoke"])
            if rc != 0:
                print(f"\n↯ Command exited with status {rc}.")
            input("\n↩  Done. Press ENTER to return to Tests Hub… ")
            continue

        if choice == "2":
            name, extra = _pick_suite(manifest)
            if name:
                cmd = manifest_args + ["run", "-s", name]
                if extra:
                    cmd.extend(["--extra"] + extra)
                rc = main(cmd)
                if rc != 0:
                    print(f"\n↯ Command exited with status {rc}.")
                input("\n↩  Done. Press ENTER to return to Tests Hub… ")
            continue

        if choice == "3":
            ts = input("Topics (comma-separated): ").strip()
            if ts:
                rc = main(manifest_args + ["run", "-t", ts])
                if rc != 0:
                    print(f"\n↯ Command exited with status {rc}.")
                input("\n↩  Done. Press ENTER to return to Tests Hub… ")
            continue

        if choice == "4":
            list_items("topics", manifest)
            input("\n↩  Press ENTER… ")
            continue

        if choice == "5":
            list_items("suites", manifest)
            input("\n↩  Press ENTER… ")
            continue

        if choice == "6":
            return 0

        print("Pick 1–6.")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    parser = argparse.ArgumentParser(prog="tests_hub", description="Unified test runner for Sonic")
    parser.add_argument("--manifest", "-m", default=str(DEFAULT_MANIFEST), help="Path to hub.manifest.yaml")
    sub = parser.add_subparsers(dest="cmd")

    s_list = sub.add_parser("list", help="List topics or suites")
    s_list.add_argument("kind", choices=["topics", "suites"])

    s_run = sub.add_parser("run", help="Run by suite or topic(s)")
    s_run.add_argument("-s", "--suite", help="Suite name defined in manifest")
    s_run.add_argument("-t", "--topics", help="Comma-separated topics")
    s_run.add_argument("--extra", nargs=argparse.REMAINDER, help="Extra args passed to pytest")

    sub.add_parser("smoke", help="Quick sanity (alias for suite 'smoke')")

    args = parser.parse_args(argv)
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)

    if args.cmd == "list":
        return list_items(args.kind, manifest)

    if args.cmd == "smoke":
        return main(["-m", str(manifest_path), "run", "-s", "smoke"])

    if args.cmd == "run":
        topics: list[str] = []
        extra: list[str] = []
        if args.suite:
            suite_topics, suite_extra = resolve_suite_topics(manifest, args.suite)
            topics = suite_topics
            extra.extend(suite_extra)
            if args.suite == "contracts":
                return do_contracts_probe(manifest)
        if args.topics:
            topics = [t.strip() for t in args.topics.split(",") if t.strip()]
        if args.extra:
            extras = list(args.extra)
            if extras and extras[0] == "--":
                extras = extras[1:]
            extra.extend(extras)
        if not topics:
            default_suite = manifest.get("default_suite", "unit")
            topics, extra = resolve_suite_topics(manifest, default_suite)

        tools = manifest.get("tools", {}) or {}
        if tools.get("pytest", True) and not which_or_warn("pytest"):
            print("pytest not found on PATH.", file=sys.stderr)
            return 2

        report_dir = manifest.get("report_dir", "reports/tests") or "reports/tests"
        report_path = Path(report_dir)
        if not report_path.is_absolute():
            report_path = REPO_ROOT / report_path
        ensure_report_dir(report_path)

        cmd = build_pytest_cmd(manifest, topics, extra, report_path)

        coverage_file: Path | None = None
        if manifest.get("coverage", True) and has_module("coverage"):
            coverage_file = report_path / ".coverage"

        env = os.environ.copy()
        if coverage_file is not None:
            env["COVERAGE_FILE"] = str(coverage_file)

        pytest_cfg = manifest.get("pytest", {}) or {}
        autoload = bool(pytest_cfg.get("autoload", False))
        if not autoload:
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        else:
            env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)

        rc = run_cmd("pytest", cmd, env=env, cwd=REPO_ROOT)
        try:
            summarize_coverage(manifest, coverage_file)
        except Exception:
            pass
        return rc

    if args.cmd is None:
        return interactive(manifest, manifest_path)

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
