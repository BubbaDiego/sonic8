

from datetime import datetime
from zoneinfo import ZoneInfo

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


def iso_utc_now() -> str:
    """Return current UTC time as an ISO 8601 string without microseconds."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def normalize_iso_timestamp(value: str) -> str:
    """Return ``value`` stripped to second precision if parseable."""
    try:
        if value.endswith("Z"):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(value)
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return value


def now_pst() -> datetime:
    """Return the current time in the Pacific timezone."""
    return datetime.now(PACIFIC_TZ)


def to_pst(dt: datetime) -> datetime:
    """Convert a timezone-aware ``datetime`` to Pacific time."""
    if dt.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware")
    return dt.astimezone(PACIFIC_TZ)


def format_pst(dt: datetime) -> str:
    """Format a ``datetime`` for dashboard display in Pacific time."""
    pacific = to_pst(dt)
    hour = pacific.strftime("%I").lstrip("0") or "0"
    minute = pacific.strftime("%M")
    ampm = pacific.strftime("%p")
    month = str(pacific.month)
    day = str(pacific.day)
    return f"{hour}:{minute} {ampm}\n{month}/{day}"


