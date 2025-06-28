from .icons import ICON_MAP


def grade_from_pct(pct: float) -> str:
    if pct >= 97:
        return "A+"
    elif pct >= 94:
        return "A"
    elif pct >= 90:
        return "A-"
    elif pct >= 87:
        return "B+"
    elif pct >= 84:
        return "B"
    elif pct >= 80:
        return "B-"
    elif pct >= 77:
        return "C+"
    elif pct >= 74:
        return "C"
    elif pct >= 70:
        return "C-"
    elif pct >= 67:
        return "D+"
    elif pct >= 64:
        return "D"
    elif pct >= 60:
        return "D-"
    else:
        return "F"


def render_summary(results: dict) -> str:
    passed = results.get("passed", 0)
    failed = results.get("failed", 0)
    skipped = results.get("skipped", 0)
    pct = results.get("pct", 0.0)
    grade = results.get("grade", "N/A")
    grade_icon = ICON_MAP["grade"].get(grade, "")

    return f"✅ {passed} | ❌ {failed} | ⚠️ {skipped}   ({pct:.1f}% -> Grade {grade}{grade_icon})"
