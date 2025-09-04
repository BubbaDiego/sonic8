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
    Make Chrome's profile bubble display the alias (e.g., 'Leia') by updating
    'Local State' → profile.info_cache['Default'].name and last_used.
    Safe to call repeatedly.
    """
    os.makedirs(user_data_dir, exist_ok=True)
    state_path = os.path.join(user_data_dir, "Local State")

    data = {}
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    profile = data.setdefault("profile", {})
    info_cache = profile.setdefault("info_cache", {})
    default = info_cache.setdefault("Default", {})
    default["name"] = alias
    default["is_using_default_name"] = False
    profile["last_used"] = "Default"

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
