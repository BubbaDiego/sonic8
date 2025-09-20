from __future__ import annotations
import os, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "githooks" / "pre-commit"
dst = ROOT.parent / ".git" / "hooks" / "pre-commit"
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dst)
os.chmod(dst, 0o755)
print(f"Installed pre-commit hook -> {dst}")

# USAGE:
#   python scripts/install_hooks.py
# Then commit as usual; the hook will run before each commit.
