from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

from backend.data.data_locker import DataLocker


def _print_active(session_mgr) -> None:
    active = session_mgr.get_active_session()
    print()
    print("🎯 Session / Goals")
    print("────────────────────────────")

    if active is None:
        print("No active session. You can start one from this console.")
        return

    start_ts = getattr(active, "session_start_time", None)
    start_value = getattr(active, "session_start_value", 0.0)
    current_value = getattr(active, "current_session_value", 0.0)
    goal_value = getattr(active, "session_goal_value", 0.0)
    perf_value = getattr(active, "session_performance_value", 0.0)
    status = getattr(active, "status", "OPEN")
    session_label = getattr(active, "session_label", None)
    goal_mode = getattr(active, "goal_mode", None)
    notes = getattr(active, "notes", None)

    print(f"ID      : {active.id}")
    if session_label:
        print(f"Label   : {session_label}")

    if start_ts is not None:
        try:
            if isinstance(start_ts, str):
                start_str = start_ts
            else:
                start_str = start_ts.isoformat(timespec="seconds")
        except Exception:
            start_str = str(start_ts)
        print(f"Start   : {start_str}")

    print(f"Start $ : {start_value}")
    print(f"Current$: {current_value}")
    print(f"Goal   $: {goal_value}")
    print(f"Perf   $: {perf_value}")
    if goal_mode:
        print(f"Mode    : {goal_mode}")
    print(f"Status  : {status}")
    if notes:
        print(f"Notes   : {notes}")


def _prompt_float(label: str, default: Optional[float]) -> Optional[float]:
    if default is None:
        prompt = f"{label} (blank=skip): "
    else:
        prompt = f"{label} [{default}] (blank=keep): "
    raw = input(prompt).strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return default


def _start_new_session(session_mgr) -> None:
    print("\nStart new session")
    print("-----------------")

    label = input("Session label (optional): ").strip() or None

    # goal mode is optional; default to DELTA if not set / invalid
    raw_mode = input("Goal mode [DELTA/ABSOLUTE] (default DELTA): ").strip().upper()
    if raw_mode not in {"DELTA", "ABSOLUTE"}:
        raw_mode = "DELTA"

    start_value = _prompt_float("Start value", 0.0) or 0.0
    goal_value = _prompt_float("Goal value", 0.0) or 0.0
    notes = input("Notes (optional): ").strip() or None

    # Be tolerant of older signatures (no label / goal_mode)
    try:
        session_mgr.start_session(
            start_value=start_value,
            goal_value=goal_value,
            notes=notes,
            session_label=label,
            goal_mode=raw_mode,
        )
    except TypeError:
        session_mgr.start_session(
            start_value=start_value,
            goal_value=goal_value,
            notes=notes,
        )

    print("\nNew session started.")
    input("Press ENTER to continue…")


def _edit_active_session(session_mgr) -> None:
    active = session_mgr.get_active_session()
    if active is None:
        print("\nNo active session to edit.")
        input("Press ENTER to continue…")
        return

    print("\nEdit active session")
    print("-------------------")

    # session_start_time
    current_start = getattr(active, "session_start_time", None)
    if current_start is not None:
        if isinstance(current_start, str):
            current_start_str = current_start
        else:
            try:
                current_start_str = current_start.isoformat(timespec="seconds")
            except Exception:
                current_start_str = str(current_start)
    else:
        current_start_str = ""

    new_start_raw = input(
        f"Session start time [{current_start_str}] (ISO, blank=keep): "
    ).strip()

    new_start_value: Any = current_start_str
    if new_start_raw:
        try:
            new_dt = datetime.fromisoformat(new_start_raw)
            new_start_value = new_dt.isoformat(timespec="seconds")
        except Exception:
            new_start_value = current_start_str

    start_val = getattr(active, "session_start_value", 0.0)
    current_val = getattr(active, "current_session_value", 0.0)
    goal_val = getattr(active, "session_goal_value", 0.0)
    perf_val = getattr(active, "session_performance_value", 0.0)
    status = getattr(active, "status", "OPEN")
    notes = getattr(active, "notes", None)

    patch: dict[str, Any] = {"session_start_time": new_start_value}

    maybe = _prompt_float("Start value", start_val)
    if maybe is not None:
        patch["session_start_value"] = maybe

    maybe = _prompt_float("Current value", current_val)
    if maybe is not None:
        patch["current_session_value"] = maybe

    maybe = _prompt_float("Goal value", goal_val)
    if maybe is not None:
        patch["session_goal_value"] = maybe

    maybe = _prompt_float("Performance value", perf_val)
    if maybe is not None:
        patch["session_performance_value"] = maybe

    new_status = input(f"Status [{status}] (blank=keep): ").strip()
    if new_status:
        patch["status"] = new_status

    new_notes = input(
        f"Notes [{notes if notes is not None else ''}] (blank=keep): "
    ).strip()
    if new_notes:
        patch["notes"] = new_notes

    # We keep label/mode editing minimal for now; can be extended later.
    session_mgr.update_session(active.id, patch)
    print("\nActive session updated.")
    input("Press ENTER to continue…")


def _reset_active_session(session_mgr) -> None:
    print("\nResetting active session metrics (if any)…")
    try:
        session_mgr.reset_session()
        print("Active session metrics reset.")
    except Exception as exc:
        print(f"Reset failed: {exc}")
    input("Press ENTER to continue…")


def _close_active_session(session_mgr) -> None:
    print("\nClosing active session (if any)…")
    try:
        session_mgr.close_session()
        print("Active session closed.")
    except Exception as exc:
        print(f"Close failed: {exc}")
    input("Press ENTER to continue…")


def _list_recent_sessions(session_mgr) -> None:
    print("\nRecent sessions")
    print("---------------")
    try:
        sessions = session_mgr.list_sessions(limit=10)
    except Exception as exc:
        print(f"Failed to list sessions: {exc}")
        input("Press ENTER to continue…")
        return

    if not sessions:
        print("No sessions found.")
        input("Press ENTER to continue…")
        return

    for s in sessions:
        start_ts = getattr(s, "session_start_time", None)
        status = getattr(s, "status", "OPEN")
        label = getattr(s, "session_label", None)
        perf = getattr(s, "session_performance_value", 0.0)

        if isinstance(start_ts, str):
            start_str = start_ts
        elif start_ts is not None:
            try:
                start_str = start_ts.isoformat(timespec="seconds")
            except Exception:
                start_str = str(start_ts)
        else:
            start_str = "?"

        label_str = f" [{label}]" if label else ""
        print(f"- {start_str}{label_str}  status={status}  perf={perf}")

    input("Press ENTER to continue…")


def run() -> None:
    """Entry point for the Session / Goals console."""
    try:
        dl = DataLocker.get_instance()
    except Exception as exc:
        print(f"Session/Goals console unavailable: {exc}")
        input("Press ENTER to return…")
        return

    session_mgr = getattr(dl, "session", None)
    if session_mgr is None:
        print("Session manager is not configured on DataLocker.")
        input("Press ENTER to return…")
        return

    while True:
        print("\n🎯 Session / Goals Console")
        print("--------------------------")
        _print_active(session_mgr)

        print()
        print("1. Start new session")
        print("2. Edit active session")
        print("3. Reset active session metrics")
        print("4. Close active session")
        print("5. List recent sessions")
        print("0. Back to LaunchPad")

        try:
            choice = input("→ ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            _start_new_session(session_mgr)
        elif choice == "2":
            _edit_active_session(session_mgr)
        elif choice == "3":
            _reset_active_session(session_mgr)
        elif choice == "4":
            _close_active_session(session_mgr)
        elif choice == "5":
            _list_recent_sessions(session_mgr)
        elif choice == "0":
            break
        else:
            print("Unknown option. Use 0–5.")
            input("Press ENTER to continue…")
