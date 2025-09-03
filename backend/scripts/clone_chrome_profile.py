import os
import json
import shutil
import pathlib
import argparse

IGNORE_PATTERNS = shutil.ignore_patterns(
    "Cache",
    "Code Cache",
    "GPUCache",
    "ShaderCache",
    "Service Worker",
    "Crashpad",
    "GrShaderCache",
    "Offline Pages",
    "OptimizationGuide",
    "DawnCache",
    "Media Cache",
    "VideoDecodeStats",
)


def safe_copytree(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Copy a directory tree ignoring cache-heavy folders."""
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=IGNORE_PATTERNS)


def ensure_local_state(dst_user_data: pathlib.Path, profile_dir_name: str, profile_display_name: str) -> None:
    """Ensure Local State contains an entry for the selected profile."""
    ls_file = dst_user_data / "Local State"
    info = {"profile": {"info_cache": {}}}
    if ls_file.exists():
        try:
            info = json.loads(ls_file.read_text(encoding="utf-8"))
        except Exception:  # pragma: no cover
            pass
    info.setdefault("profile", {}).setdefault("info_cache", {})
    info["profile"]["info_cache"][profile_dir_name] = {
        "name": profile_display_name,
        "active_time": "0",
    }
    ls_file.write_text(json.dumps(info, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Clone a Chrome profile into a dedicated User Data root."
    )
    ap.add_argument(
        "--source-user-data",
        required=True,
        help=r"e.g. %LOCALAPPDATA%\Google\Chrome\User Data",
    )
    ap.add_argument(
        "--profile-dir-name", required=True, help="e.g. Profile 5, Default"
    )
    ap.add_argument("--alias", required=True, help="e.g. lando")
    ap.add_argument(
        "--dest-root",
        default=r"C:\\sonic5\\profiles",
        help="Where to place the clone (a 'User Data' folder will be created inside alias)",
    )
    ap.add_argument(
        "--display-name",
        default=None,
        help="Shown in chrome://version; defaults to 'AutoCore - <alias>'",
    )
    args = ap.parse_args()

    src_user_data = pathlib.Path(os.path.expandvars(args.source_user_data)).resolve()
    src_profile = src_user_data / args.profile_dir_name
    if not src_profile.exists():
        raise SystemExit(f"Profile folder not found: {src_profile}")

    dst_alias_root = pathlib.Path(args.dest_root) / args.alias
    dst_user_data = dst_alias_root / "User Data"

    if dst_alias_root.exists():
        shutil.rmtree(dst_alias_root, ignore_errors=True)
    dst_user_data.mkdir(parents=True, exist_ok=True)

    safe_copytree(src_profile, dst_user_data / args.profile_dir_name)

    src_local_state = src_user_data / "Local State"
    if src_local_state.exists():
        shutil.copy2(src_local_state, dst_user_data / "Local State")
    ensure_local_state(
        dst_user_data,
        args.profile_dir_name,
        args.display_name or f"AutoCore - {args.alias}",
    )

    print("Cloned profile")
    print(" alias:", args.alias)
    print(" dst_user_data:", str(dst_user_data))
    print(" profile_dir_name:", args.profile_dir_name)


if __name__ == "__main__":
    main()
