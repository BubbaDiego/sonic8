import os, sys, shutil, argparse, json

EXCLUDE_DIRS = {
    "Cache", "Code Cache", "GPUCache", "DawnCache", "GrShaderCache", "ShaderCache",
    "Service Worker\\CacheStorage", "Service Worker\\ScriptCache", "Media Cache",
    "Safe Browsing", "OptimizationGuide", "First Run"
}
EXCLUDE_FILES = {
    "LOCK", "SingletonCookie", "SingletonLock", "SingletonSocket",
    "Current Tabs", "Current Session", "Last Session", "Last Tabs"
}

def _norm(p: str) -> str:
    return os.path.normpath(p)

def copytree_filtered(src: str, dst: str) -> None:
    src = _norm(src); dst = _norm(dst)
    os.makedirs(dst, exist_ok=True)
    for root, dirs, files in os.walk(src):
        # prune excluded dirs
        pruned = []
        for d in list(dirs):
            rel = os.path.relpath(os.path.join(root, d), src)
            # check each path component against EXCLUDE_DIRS
            components = rel.replace("/", "\\").split("\\")
            if any(part in EXCLUDE_DIRS for part in components):
                pruned.append(d)
        for d in pruned:
            dirs.remove(d)

        # ensure dest dir exists
        rel_root = os.path.relpath(root, src)
        dest_root = os.path.join(dst, rel_root) if rel_root != "." else dst
        os.makedirs(dest_root, exist_ok=True)

        # copy files except excluded
        for name in files:
            if name in EXCLUDE_FILES:
                continue
            src_f = os.path.join(root, name)
            dst_f = os.path.join(dest_root, name)
            try:
                shutil.copy2(src_f, dst_f)
            except Exception:
                # best-effort; skip locked/ephemeral files
                pass

def write_local_state(dst_user_data_dir: str, display_name: str, profile_dir_name: str = "Default"):
    """Create/patch 'Local State' so Chrome shows the alias and uses the cloned profile."""
    os.makedirs(dst_user_data_dir, exist_ok=True)
    local_state = os.path.join(dst_user_data_dir, "Local State")
    data = {}
    if os.path.exists(local_state):
        try:
            with open(local_state, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    prof = data.setdefault("profile", {})
    cache = prof.setdefault("info_cache", {})
    entry = cache.setdefault(profile_dir_name, {})
    entry["name"] = display_name
    entry["is_using_default_name"] = False
    prof["last_used"] = profile_dir_name
    with open(local_state, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser(description="Clone a Chrome profile into an automation alias dir.")
    ap.add_argument("--src-profile", required=True,
                    help=r'Full path to the SOURCE profile dir, e.g. "C:\\Users\\you\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 3"')
    ap.add_argument("--dst-alias", required=True, help=r'Alias name, e.g. "Leia"')
    ap.add_argument("--base-dir", default=r"C:\\sonic5\\profiles",
                    help=r'Base dir for automation profiles (default: C:\\sonic5\\profiles)')
    ap.add_argument("--display-name", default=None, help='Display name to show in bubble (default: alias)')
    args = ap.parse_args()

    src_profile = _norm(args.src_profile)
    if not os.path.isdir(src_profile):
        print(f"[ERROR] src profile not found: {src_profile}", file=sys.stderr)
        sys.exit(2)

    dst_user_data_dir = _norm(os.path.join(args.base_dir, args.dst_alias))
    dst_profile_dir = os.path.join(dst_user_data_dir, "Default")

    # sanity: kill Chrome first
    if os.name == "nt":
        os.system("taskkill /IM chrome.exe /F /T >NUL 2>&1")

    # clean existing destination to avoid mixing
    if os.path.isdir(dst_user_data_dir):
        try:
            shutil.rmtree(dst_user_data_dir)
        except Exception:
            pass
    os.makedirs(dst_profile_dir, exist_ok=True)

    # copy files (profile dir -> Default)
    print(f"[INFO] copying profile:\n  from: {src_profile}\n  to:   {dst_profile_dir}")
    copytree_filtered(src_profile, dst_profile_dir)

    # also copy the top-level 'Local State' from the source tree if present
    src_user_data_root = os.path.normpath(os.path.join(src_profile, ".."))
    src_local_state = os.path.join(src_user_data_root, "Local State")
    if os.path.exists(src_local_state):
        try:
            shutil.copy2(src_local_state, os.path.join(dst_user_data_dir, "Local State"))
        except Exception:
            pass

    # set display name + last_used to Default
    display_name = args.display_name or args.dst_alias
    write_local_state(dst_user_data_dir, display_name, profile_dir_name="Default")

    print("[OK] Migration complete.")
    print(f"  dst user_data_dir: {dst_user_data_dir}")
    print("Next:")
    print(f'  python -m auto_core.launcher.open_jupiter --wallet-id {args.dst_alias}')

if __name__ == "__main__":
    main()
