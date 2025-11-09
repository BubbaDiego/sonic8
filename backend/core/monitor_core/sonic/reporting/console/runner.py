# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable, Optional
import importlib, time, json, os
from pathlib import Path


def _safe_render(mod_name: str, fn_name: str, dl: Any) -> None:
    """Call a classic panel render(dl[, csum]) and ignore failures."""
    try:
        mod = importlib.import_module(mod_name)
        fn: Callable = getattr(mod, fn_name)
        try:
            fn(dl)  # preferred signature
        except TypeError:
            fn(dl, None)  # tolerate old (dl, csum)
    except Exception as e:
        print(f"[REPORT] {mod_name}.{fn_name} failed: {e}")


def _render_footer_panel(footer_ctx: Optional[dict]) -> None:
    """
    Import the new cycle_footer_panel and print its returned lines (list[str]).
    It accepts either render(context_dict) or keyword args; we pass a dict.
    """
    try:
        mod = importlib.import_module(
            "backend.core.reporting_core.sonic_reporting.cycle_footer_panel"
        )
        fn = getattr(mod, "render", None)
        if callable(fn):
            res = fn(footer_ctx or {})
            if isinstance(res, (list, tuple)):
                for line in res:
                    print(line)
            elif isinstance(res, str):
                print(res)
    except Exception as e:
        print(f"[REPORT] cycle_footer_panel.render failed: {e}")


def _load_latest_csum(default_path: str = "reports/sonic_summary.jsonl") -> dict:
    path = Path(os.getenv("SONIC_SUMMARY_PATH", default_path))
    if not path.exists():
        return {}
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            pos = max(0, f.tell() - 8192)
            f.seek(pos)
            tail = f.read().decode("utf-8", errors="ignore")
        lines = [ln.strip() for ln in tail.splitlines() if ln.strip()]
        for ln in reversed(lines):
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
    except Exception:
        pass
    return {}


def _fallback_monitors_enabled() -> dict:
    # sensible defaults so the panel isn’t empty when summaries aren’t ready yet
    return {
        "sonic": True,
        "liquid": True,
        "profit": True,
        "market": True,
        "price": True,
        "xcom": True,
    }


def run_console_reporters(
    dl: Any,
    debug: bool = False,
    *,
    footer_ctx: Optional[dict] = None,
) -> None:
    """
    Final ordering:
      1) Cycle Activity
      2) Prices (reporter stack)
      3) Positions (reporter stack)
      4) Monitors
      5) XCom
      6) Wallets
      7) Cycle footer (always last)
    """
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.cycle_activity_reporter",
        "render",
        dl,
    )

    # Reporter panels (Prices, Positions, XCom, Wallets) now live between Activity and Monitors
    try:
        from backend.core.reporting_core import console_reporter as _cr

        try:
            width = int(os.environ.get("SONIC_CONSOLE_WIDTH", "92"))
        except Exception:
            width = 92

        ctx = {
            "loop_counter": int((footer_ctx or {}).get("loop_counter", 0)),
            "poll_interval_s": int((footer_ctx or {}).get("poll_interval_s", 0)),
            "total_elapsed_s": float((footer_ctx or {}).get("total_elapsed_s", 0.0)),
            "ts": (footer_ctx or {}).get("ts", time.time()),
        }

        _cr.render_panel_stack(ctx=ctx, dl=dl, width=width, writer=print)
    except Exception as exc:
        print(f"[REPORT] panel runner failed: {exc!r}", flush=True)

    # Use new standardized monitors panel with a context dict (not dl)
    try:
        mod = importlib.import_module(
            "backend.core.reporting_core.sonic_reporting.console_panels.monitor_panel"
        )
        fn = getattr(mod, "render", None)
        if callable(fn):
            latest = _load_latest_csum()
            enabled = latest.get("monitors_enabled") or _fallback_monitors_enabled()
            # Monitors panel expects a context dict with the freshest csum attached.
            ctx = {
                "dl": dl,
                "csum": latest,
                "monitors": latest.get("monitors", {}),
                "monitors_enabled": enabled,
                "loop_counter": int((footer_ctx or {}).get("loop_counter", 0)),
                "poll_interval_s": int((footer_ctx or {}).get("poll_interval_s", 0)),
                "total_elapsed_s": float((footer_ctx or {}).get("total_elapsed_s", 0.0)),
                "ts": (footer_ctx or {}).get("ts", time.time()),
            }
            lines = fn(ctx)
            if isinstance(lines, (list, tuple)):
                for ln in lines:
                    print(ln)
            elif isinstance(lines, str):
                print(lines)
    except Exception as e:
        print(f"[REPORT] console_panels.monitor_panel.render failed: {e}")

    _safe_render(
        "backend.core.reporting_core.sonic_reporting.xcom_panel",
        "render",
        dl,
    )
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.wallets_panel",
        "render",
        dl,
    )

    # Footer box at the very end
    _render_footer_panel(footer_ctx)
