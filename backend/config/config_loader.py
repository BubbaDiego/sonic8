"""Configuration loader logic placeholder."""

import json
from pathlib import Path


def load_config(path: Path) -> dict:
    """Load configuration from a JSON file."""
    if not path.exists():
        return {}
    with path.open() as cfg:
        return json.load(cfg)
