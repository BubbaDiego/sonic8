import os, re, json

_BAD_PROFILE_FLAG = re.compile(r"^--profile-directory(?:=|\s).*", re.I)


def sanitize_profile_settings(user_data_dir: str, args: list[str]) -> tuple[str, list[str]]:
    """
    Strip trailing '\\User Data' and any '--profile-directory=...' flags.
    """
    udd = (user_data_dir or "").strip().strip('"').strip("'")
    suffix = os.path.join("", "User Data")
    if udd.lower().endswith(suffix.lower()):
        udd = udd[:-len(suffix)].rstrip("\\/")
    clean_args = [a for a in (args or []) if not _BAD_PROFILE_FLAG.match(a)]
    return udd, clean_args


def set_profile_display_name(user_data_dir: str, alias: str) -> None:
    """
    Make Chrome's bubble show the alias (e.g., 'Sonic - Auto').
    Writes Local State: profile.info_cache['Default'].name + last_used.
    """
    os.makedirs(user_data_dir, exist_ok=True)
    path = os.path.join(user_data_dir, "Local State")

    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    prof = data.setdefault("profile", {})
    cache = prof.setdefault("info_cache", {})
    default = cache.setdefault("Default", {})
    default["name"] = alias
    default["is_using_default_name"] = False
    prof["last_used"] = "Default"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mark_last_exit_clean(user_data_dir: str, profile_dir: str = "Default") -> None:
    """
    Wipes crash markers so Chrome won't show the 'Restore pages?' bubble.
    Touches both 'Local State' and '<profile_dir>\\Preferences'.
    Safe to call before *every* launch.
    """
    os.makedirs(user_data_dir, exist_ok=True)

    # Local State
    ls_path = os.path.join(user_data_dir, "Local State")
    ls = {}
    if os.path.exists(ls_path):
        try:
            with open(ls_path, "r", encoding="utf-8") as f:
                ls = json.load(f)
        except Exception:
            ls = {}
    prof = ls.setdefault("profile", {})
    prof["exited_cleanly"] = True
    prof["exit_type"] = "Normal"
    try:
        with open(ls_path, "w", encoding="utf-8") as f:
            json.dump(ls, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # Preferences inside the profile directory
    pref_path = os.path.join(user_data_dir, profile_dir, "Preferences")
    prefs = {}
    if os.path.exists(pref_path):
        try:
            with open(pref_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except Exception:
            prefs = {}
    p = prefs.setdefault("profile", {})
    p["exit_type"] = "Normal"
    p["exited_cleanly"] = True
    try:
        os.makedirs(os.path.dirname(pref_path), exist_ok=True)
        with open(pref_path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
