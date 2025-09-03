import os
import json
import pathlib


def main():
    """List Chrome profile names and folder identifiers."""
    local_state = pathlib.Path(
        os.path.expandvars(r"%LOCALAPPDATA%/Google/Chrome/User Data/Local State")
    )
    data = json.loads(local_state.read_text(encoding="utf-8"))
    pairs = [
        (v.get("name", ""), k)
        for k, v in data.get("profile", {}).get("info_cache", {}).items()
    ]
    for name, folder in sorted(pairs):
        print(f"{name} -> {folder}")


if __name__ == "__main__":
    main()
