from __future__ import annotations

from typing import List


def build_red_green_bar(
    left_label: str,
    right_label: str,
    left_ratio: float,
    slots: int = 32,
) -> str:
    """
    Build a one-line red/green bar like the Risk Snapshot SHORT/LONG bar.

    left_ratio: fraction (0..1) of the bar shown as "left" (red side).
    The remaining portion is "right" (green side).
    """
    ratio = max(0.0, min(1.0, float(left_ratio)))
    total = max(4, int(slots))
    red_slots = int(round(ratio * total))

    chars: List[str] = []
    for i in range(total):
        if i < red_slots:
            chars.append("🟥")
        else:
            chars.append("🟩")

    bar = "".join(chars)
    return f"{left_label} {bar} {right_label}"
