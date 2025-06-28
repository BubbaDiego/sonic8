from datetime import datetime
from flask import url_for
from dashboard.dashboard_service import DEFAULT_WALLET_IMAGE


def short_datetime(value):
    """Format timestamps like '2025-06-03T13:06:03.968905' as '3:06PM 6/3/25'."""
    if not value:
        return ""
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(float(value))
        else:
            try:
                dt = datetime.fromisoformat(str(value))
            except ValueError:
                dt = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        formatted = dt.strftime("%I:%M%p %m/%d/%y")
        if formatted.startswith("0"):
            formatted = formatted[1:]
        formatted = formatted.replace("/0", "/")
        return formatted
    except Exception:
        return value


def resolve_wallet_image(path: str | None) -> str:
    """Return a safe static URL for a wallet image."""
    if not path:
        path = DEFAULT_WALLET_IMAGE
    path = str(path).lstrip('/')
    if path.startswith('http'):
        return path
    if path.startswith('static/') or path.startswith('/static/'):
        return '/' + path.lstrip('/')
    if not path.startswith('images/'):
        path = 'images/' + path
    return url_for('static', filename=path)

