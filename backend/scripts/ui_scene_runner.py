#!/usr/bin/env python3
"""
UI Scene Runner — lightweight renderer for console UI scenes.

Usage:
  python backend/scripts/ui_scene_runner.py --scene tests/ui_scenes/portfolio_panel.scene.yaml
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("Missing dependency 'PyYAML' (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]

def render_scene(meta: dict, data: dict | None) -> int:
    title = meta.get("title") or meta.get("id") or "UI Scene"
    print("\n" + "─" * (len(title) + 2))
    print(f" {title}")
    print("─" * (len(title) + 2))

    # Simple textual preview; Codex can replace this with real rich-based renderers.
    info = {
        "id": meta.get("id"),
        "renderer": meta.get("renderer", "demo.text"),
        "offline_ok": bool(meta.get("offline_ok", True)),
        "requires_api": bool(meta.get("requires_api", False)),
    }
    for k, v in info.items():
        print(f"• {k}: {v}")

    if data is not None:
        sample = json.dumps(data, indent=2)[:2000]
        print("\nData (truncated):\n" + sample)
    else:
        print("\n(no fixture data)")

    print("\n✅ Scene completed.")
    return 0

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, help="Path to *.scene.yaml")
    args = ap.parse_args(argv)

    scene_path = (REPO_ROOT / args.scene).resolve()
    if not scene_path.exists():
        print(f"Scene not found: {scene_path}", file=sys.stderr)
        return 2

    meta = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    fixture = meta.get("fixture")
    data = None
    if fixture:
        fp = (REPO_ROOT / fixture).resolve()
        if fp.exists():
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"⚠️  Failed to parse fixture JSON: {e}", file=sys.stderr)

    return render_scene(meta, data)

if __name__ == "__main__":
    sys.exit(main())
