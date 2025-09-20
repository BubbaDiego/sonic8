from __future__ import annotations
from pathlib import Path
import yaml, sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"

def find_auto_core(root: Path) -> Path | None:
    # common spots: repo root, backend/, apps/
    candidates = [root/"auto_core", root/"backend"/"auto_core", root/"apps"/"auto_core"]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    # fallback: search shallow (depth 2)
    for p in root.iterdir():
        if p.is_dir():
            ac = p/"auto_core"
            if ac.exists() and ac.is_dir():
                return ac
    return None

def main():
    if not MANIFEST.exists():
        print("ERR: manifest not found:", MANIFEST)
        sys.exit(1)
    m = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    mods = m.get("modules") or []
    idx = next((i for i,x in enumerate(mods) if x.get("id")=="MOD-AUTO"), None)
    if idx is None:
        print("OK: MOD-AUTO not listed; nothing to do.")
        return
    ac = find_auto_core(ROOT)
    if ac:
        rel = ac.relative_to(ROOT).as_posix() + "/"
        mods[idx]["path"] = rel
        print("OK: MOD-AUTO.path ->", rel)
    else:
        # remove module if directory truly doesn't exist
        removed = mods.pop(idx)
        print("OK: removed MOD-AUTO; path not found on disk.")
    m["modules"] = mods
    MANIFEST.write_text(yaml.safe_dump(m, sort_keys=False), encoding="utf-8")
    print("OK: manifest updated:", MANIFEST)

if __name__ == "__main__":
    main()
