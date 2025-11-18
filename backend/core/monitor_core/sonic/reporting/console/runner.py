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
    cfg: Optional[dict] = None,
) -> None:
    """
    Final ordering:
      1) Cycle Activity
      2) Reporter stack (Prices, Positions, Risk, Monitors, Market, XCom)
      3) Wallets
      4) Session / Goals
      5) Cycle footer (always last)
    """
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.cycle_activity_reporter",
        "render",
        dl,
    )

    panel_ctx: Optional[dict] = None
    panel_width: Optional[int] = None

    # Reporter panels (Prices, Positions, Risk, Monitors, Market, XCom) now live
    # between Activity and Wallets
    try:
        from backend.core.reporting_core import console_reporter as _cr

        try:
            width = int(os.environ.get("SONIC_CONSOLE_WIDTH", "92"))
        except Exception:
            width = 92
        panel_width = width

        cfg_obj: Optional[dict]
        if isinstance(cfg, dict):
            cfg_obj = cfg
        else:
            gc = getattr(dl, "global_config", None)
            cfg_obj = gc if isinstance(gc, dict) else None
        ctx = {
            "dl": dl,
            "cfg": cfg_obj,
            "loop_counter": int((footer_ctx or {}).get("loop_counter", 0)),
            "poll_interval_s": int((footer_ctx or {}).get("poll_interval_s", 0)),
            "total_elapsed_s": float((footer_ctx or {}).get("total_elapsed_s", 0.0)),
            "ts": (footer_ctx or {}).get("ts", time.time()),
        }
        panel_ctx = ctx

        _cr.render_panel_stack(ctx=ctx, dl=dl, cfg=cfg_obj, width=width, writer=print)
    except Exception as exc:
        print(f"[REPORT] panel runner failed: {exc!r}", flush=True)

    _safe_render(
        "backend.core.reporting_core.sonic_reporting.console_panels.wallets_panel",
        "render",
        dl,
    )

    # Session / Goals panel: render after Wallets for better grouping with balances.
    try:
        from backend.core.reporting_core.sonic_reporting.console_panels import (
            session_panel as _session_panel,
        )

        # If the reporter stack failed before building ctx, reconstruct a minimal one.
        if panel_ctx is None:
            cfg_obj: Optional[dict]
            if isinstance(cfg, dict):
                cfg_obj = cfg
            else:
                gc = getattr(dl, "global_config", None)
                cfg_obj = gc if isinstance(gc, dict) else None
            panel_ctx = {
                "dl": dl,
                "cfg": cfg_obj,
                "loop_counter": int((footer_ctx or {}).get("loop_counter", 0)),
                "poll_interval_s": int((footer_ctx or {}).get("poll_interval_s", 0)),
                "total_elapsed_s": float((footer_ctx or {}).get("total_elapsed_s", 0.0)),
                "ts": (footer_ctx or {}).get("ts", time.time()),
            }

        if panel_width is None:
            try:
                panel_width = int(os.environ.get("SONIC_CONSOLE_WIDTH", "92"))
            except Exception:
                panel_width = 92

        lines_obj = _session_panel.connector(dl=dl, ctx=panel_ctx, width=panel_width)
        if isinstance(lines_obj, (list, tuple)):
            for ln in lines_obj:
                print(ln)
        elif isinstance(lines_obj, str):
            print(lines_obj)
    except Exception as exc:
        print(f"[REPORT] session_panel.connector failed: {exc!r}", flush=True)

    # Footer box at the very end
    _render_footer_panel(footer_ctx)
