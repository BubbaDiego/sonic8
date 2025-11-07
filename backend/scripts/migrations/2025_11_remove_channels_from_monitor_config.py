"""Migration helper to remove deprecated top-level 'channels' from the monitor config."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "sonic_monitor_config.json"


def main() -> None:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "channels" in data:
        data.pop("channels", None)
        CONFIG_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Removed top-level 'channels' from {CONFIG_PATH}")
    else:
        print("No 'channels' key found; nothing to do.")


if __name__ == "__main__":
    main()
