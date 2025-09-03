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


def resolve_profile_dir(
    wallet_id: str,
    alias_map: dict,
    chrome_user_data_root: str = r"C:\\Users\\bubba\\AppData\\Local\\Google\\Chrome\\User Data"
) -> str:
    """
    Returns the absolute path to the Chrome profile folder to use with Playwright's
    launch_persistent_context (e.g. ...\User Data\Profile 3).
    """
    if not wallet_id:
        raise ChromeProfileError("Wallet ID is empty.")

    folder_name = alias_map.get(wallet_id)
    if not folder_name:
        # allow direct pass-through if user typed the actual folder name
        # (e.g., "Profile 3" or "Default")
        folder_name = wallet_id

    profile_path = os.path.join(chrome_user_data_root, folder_name)
    if not os.path.isdir(profile_path):
        raise ChromeProfileError(
            f'Chrome profile folder not found: "{profile_path}". '
            f'Check chrome_profiles.json or create the profile in Chrome first.'
        )
    return profile_path
