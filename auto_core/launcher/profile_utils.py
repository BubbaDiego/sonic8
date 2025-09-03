import os, re, json

_BAD_PROFILE_FLAG = re.compile(r"^--profile-directory(?:=|\s).*", re.I)

def sanitize_profile_settings(user_data_dir: str, args: list[str]) -> tuple[str, list[str]]:
    """Strip trailing '\\User Data' and any '--profile-directory=...' flags."""
    udd = (user_data_dir or "").strip().strip('"').strip("'")
    suffix = os.path.join("", "User Data")
    if udd.lower().endswith(suffix.lower()):
        udd = udd[:-len(suffix)].rstrip("\\/")
    clean_args = [a for a in (args or []) if not _BAD_PROFILE_FLAG.match(a)]
    return udd, clean_args


def set_profile_display_name(user_data_dir: str, display_name: str) -> None:
    """Update the Chrome profile's display name if possible."""
    try:
        path = os.path.join(user_data_dir, "Local State")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        profile = state.setdefault("profile", {})
        profile["name"] = display_name
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except Exception:
        pass
