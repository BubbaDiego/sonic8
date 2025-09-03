import os, re

_BAD_PROFILE_FLAG = re.compile(r"^--profile-directory(?:=|\s).*", re.I)

def sanitize_profile_settings(user_data_dir: str, args: list[str]) -> tuple[str, list[str]]:
    """Strip trailing '\\User Data' and any '--profile-directory=...' flags."""
    udd = (user_data_dir or "").strip().strip('"').strip("'")
    suffix = os.path.join("", "User Data")
    if udd.lower().endswith(suffix.lower()):
        udd = udd[:-len(suffix)].rstrip("\\/")
    clean_args = [a for a in (args or []) if not _BAD_PROFILE_FLAG.match(a)]
    return udd, clean_args
