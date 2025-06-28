import hashlib

def hedge_color(uid: str) -> str:
    """Return a hex color code derived from the given UID."""
    digest = hashlib.md5(uid.encode()).hexdigest()
    return f"#{digest[:6]}"
