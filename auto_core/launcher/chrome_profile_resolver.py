import json
import os
from pathlib import Path

class ChromeProfileError(RuntimeError):
    pass

def load_alias_map(config_path: str) -> dict:
    p = Path(config_path)
    if not p.exists():
        raise ChromeProfileError(f"Profile map not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def resolve_profile_dir(wallet_id: str, alias_map: dict) -> str:
    """
    Return the absolute user-data directory to use for this alias.
    The alias_map should contain absolute Windows paths for each alias.
    If the user typed an absolute path directly, allow pass-through.
    """
    if not wallet_id:
        raise ChromeProfileError("Wallet ID is empty.")
    path = alias_map.get(wallet_id) or wallet_id
    if not os.path.isabs(path):
        raise ChromeProfileError(
            f'Expected absolute user data dir for alias "{wallet_id}". Got: {path}'
        )
    os.makedirs(path, exist_ok=True)
    return path
